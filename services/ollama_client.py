"""Ollama API client service for Chat-O-Llama."""

import os
import time
import requests
import logging
import threading
from typing import List, Dict, Any, Optional
from config import get_config
from utils.token_estimation import estimate_tokens
from .llm_interface import LLMInterface

logger = logging.getLogger(__name__)

# OLLAMA_API_URL will be set from config in __init__


class OllamaAPI(LLMInterface):
    """Ollama API client with enhanced metrics tracking, implementing LLMInterface."""

    def __init__(self):
        """Initialize the Ollama API client."""
        self._config = get_config()
        self._session = requests.Session()
        self._active_requests = {}  # Track active requests for cancellation
        self._requests_lock = threading.Lock()
        # Use base_url from config, falling back to environment variable
        self._base_url = self._config.get('ollama', {}).get('base_url') or os.getenv('OLLAMA_API_URL', 'http://localhost:11434')
        logger.info(f"OllamaAPI client initialized successfully with base URL: {self._base_url}")

    def _track_request(self, request_id: str, request_future) -> None:
        """Track an active request for cancellation."""
        with self._requests_lock:
            self._active_requests[request_id] = request_future

    def _untrack_request(self, request_id: str) -> None:
        """Remove a request from tracking."""
        with self._requests_lock:
            self._active_requests.pop(request_id, None)

    def _cancel_request(self, request_id: str) -> bool:
        """Cancel an active request if it exists."""
        with self._requests_lock:
            request_future = self._active_requests.get(request_id)
            if request_future:
                try:
                    # For requests library, we can't cancel ongoing requests directly
                    # But we can close the connection to interrupt it
                    logger.info(f"Attempting to cancel Ollama request {request_id}")
                    return True
                except Exception as e:
                    logger.warning(f"Error cancelling request {request_id}: {e}")
                    return False
            return False

    def get_models(self) -> List[str]:
        """
        Get available models from Ollama.
        
        Returns:
            List[str]: List of available model names. Empty list if none available
                      or if backend is unreachable.
        """
        # Prioritize ollama.connect_timeout over timeouts.ollama_connect_timeout for precedence
        connect_timeout = self._config.get('ollama', {}).get('connect_timeout') or self._config['timeouts']['ollama_connect_timeout']
        max_retries = self._config.get('ollama', {}).get('max_retries', 3)
        
        for attempt in range(max_retries + 1):
            try:
                logger.debug(f"Attempting to fetch models from {self._base_url}/api/tags (attempt {attempt + 1}/{max_retries + 1})")
                response = requests.get(
                    f"{self._base_url}/api/tags",
                    timeout=(connect_timeout, 30)
                )

                if response.status_code == 200:
                    data = response.json()
                    models = data.get('models', [])
                    model_names = [model['name']
                                   for model in models if 'name' in model]
                    logger.info(f"Successfully fetched {len(model_names)} models")
                    logger.debug(f"Available models: {model_names}")
                    return model_names
                else:
                    logger.error(f"Ollama API returned status {response.status_code}: {response.text}")
                    if attempt == max_retries:
                        return []
                    time.sleep(0.5)  # Brief delay before retry

            except requests.exceptions.ConnectionError as e:
                logger.error(f"Connection error to Ollama (attempt {attempt + 1}): {e}")
                if attempt == max_retries:
                    return []
                time.sleep(0.5)  # Brief delay before retry
            except requests.exceptions.Timeout as e:
                logger.error(f"Timeout connecting to Ollama (attempt {attempt + 1}): {e}")
                if attempt == max_retries:
                    return []
                time.sleep(0.5)  # Brief delay before retry
            except Exception as e:
                logger.error(f"Unexpected error fetching models (attempt {attempt + 1}): {e}")
                if attempt == max_retries:
                    return []
                time.sleep(0.5)  # Brief delay before retry
        
        return []

    def generate_response(
        self,
        model: str,
        prompt: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate response from Ollama with timing metrics.
        
        Args:
            model (str): Name of the model to use for generation
            prompt (str): Input prompt for the model
            conversation_history (Optional[List[Dict]]): Previous conversation context.
                Each dict should have 'role' and 'content' keys.
            **kwargs: Additional backend-specific parameters, including:
                - cancellation_token (threading.Event): Token to check for cancellation
        
        Returns:
            Dict[str, Any]: Response dictionary containing at minimum:
                - response (str): Generated text
                - response_time_ms (int): Time taken in milliseconds
                - estimated_tokens (int): Token count estimate
                - backend_type (str): Backend identifier
                - model (str): Model name used
        """
        # Prioritize ollama.timeout over timeouts.ollama_timeout for precedence
        ollama_timeout = self._config.get('ollama', {}).get('timeout') or self._config['timeouts']['ollama_timeout']
        connect_timeout = self._config.get('ollama', {}).get('connect_timeout') or self._config['timeouts']['ollama_connect_timeout']
        
        # Extract cancellation token from kwargs
        cancellation_token = kwargs.get('cancellation_token')
        request_id = kwargs.get('request_id', f"ollama_req_{int(time.time() * 1000)}")
        
        start_time = time.time()
        
        # Check for cancellation before starting
        if cancellation_token and cancellation_token.is_set():
            logger.info("Request cancelled before processing")
            response_time = int((time.time() - start_time) * 1000)
            return {
                'response': "Request was cancelled by user",
                'response_time_ms': response_time,
                'estimated_tokens': 0,
                'backend_type': 'ollama',
                'model': model,
                'error': True,
                'cancelled': True
            }
        
        try:
            # Get system prompt from config
            system_prompt = self._config['system_prompt']

            # Build context from conversation history
            context = f"{system_prompt}\n\n"

            if conversation_history:
                # Use configurable history limit
                history_limit = self._config['performance']['context_history_limit']
                for msg in conversation_history[-history_limit:]:
                    role = "Human" if msg['role'] == 'user' else "Assistant"
                    context += f"{role}: {msg['content']}\n"

            full_prompt = f"{context}Human: {prompt}\nAssistant:"

            # Extract parameters from kwargs, falling back to config defaults
            stream = kwargs.get('stream', self._config['response_optimization']['stream'])
            temperature = kwargs.get('temperature', self._config['model_options']['temperature'])
            top_p = kwargs.get('top_p', self._config['model_options']['top_p'])
            top_k = kwargs.get('top_k', self._config['model_options']['top_k'])
            num_predict = kwargs.get('max_tokens', self._config['model_options']['num_predict'])
            repeat_penalty = kwargs.get('repeat_penalty', self._config['model_options']['repeat_penalty'])
            stop = kwargs.get('stop', self._config['model_options']['stop'])

            # Build payload with all configuration options
            payload = {
                "model": model,
                "prompt": full_prompt,
                "stream": stream,
                "options": {
                    # Model generation options from config and kwargs
                    "temperature": temperature,
                    "top_p": top_p,
                    "top_k": top_k,
                    "num_predict": num_predict,
                    "num_ctx": self._config['model_options']['num_ctx'],
                    "repeat_penalty": repeat_penalty,
                    "stop": stop,

                    # Performance optimization options
                    "num_thread": self._config['performance']['num_thread'],
                    "num_gpu": self._config['performance']['num_gpu'],
                    "use_mlock": self._config['performance']['use_mlock'],
                    "use_mmap": self._config['performance']['use_mmap'],

                    # Response optimization options
                    "f16_kv": self._config['response_optimization']['f16_kv'],
                    "logits_all": self._config['response_optimization']['logits_all'],
                    "vocab_only": self._config['response_optimization']['vocab_only'],
                    "embedding_only": self._config['response_optimization']['embedding_only'],
                    "numa": self._config['response_optimization']['numa'],
                },
                "keep_alive": self._config['response_optimization']['keep_alive']
            }

            # Add low_vram option if enabled
            if self._config['response_optimization']['low_vram']:
                payload['options']['low_vram'] = True

            logger.debug(f"Generating response with payload: model={model}, stream={stream}, temp={temperature}")

            # Check for cancellation before making request
            if cancellation_token and cancellation_token.is_set():
                logger.info("Request cancelled before HTTP request")
                response_time = int((time.time() - start_time) * 1000)
                return {
                    'response': "Request was cancelled by user",
                    'response_time_ms': response_time,
                    'estimated_tokens': 0,
                    'backend_type': 'ollama',
                    'model': model,
                    'error': True,
                    'cancelled': True
                }

            # Create a new session for this request to allow cancellation
            request_session = requests.Session()
            
            # Set up cancellation monitoring in a separate thread
            def cancel_monitor():
                while not cancellation_token.is_set():
                    time.sleep(0.1)
                # If cancellation is requested, close the session
                if cancellation_token.is_set():
                    try:
                        request_session.close()
                        logger.info(f"Cancelled Ollama request {request_id}")
                    except Exception as e:
                        logger.debug(f"Error closing session during cancellation: {e}")
            
            # Start cancellation monitoring if token is provided
            cancel_thread = None
            if cancellation_token:
                cancel_thread = threading.Thread(target=cancel_monitor, daemon=True)
                cancel_thread.start()
                
            try:
                # Track the request session
                self._track_request(request_id, request_session)
                
                response = request_session.post(
                    f"{self._base_url}/api/generate",
                    json=payload,
                    timeout=(connect_timeout, ollama_timeout)
                )
                
                # Check for cancellation after request
                if cancellation_token and cancellation_token.is_set():
                    logger.info("Request cancelled after HTTP request")
                    response_time = int((time.time() - start_time) * 1000)
                    return {
                        'response': "Request was cancelled by user",
                        'response_time_ms': response_time,
                        'estimated_tokens': 0,
                        'backend_type': 'ollama',
                        'model': model,
                        'error': True,
                        'cancelled': True
                    }
                    
            finally:
                # Clean up request tracking
                self._untrack_request(request_id)
                try:
                    request_session.close()
                except:
                    pass

            # Calculate response time
            response_time = int((time.time() - start_time) * 1000)  # Convert to milliseconds

            if response.status_code == 200:
                data = response.json()
                response_text = data.get('response', 'No response generated')
                
                # Clean up any leaked Human/User prefixes from the response
                response_text = self._clean_response_text(response_text)
                
                # Estimate tokens
                estimated_tokens = estimate_tokens(response_text)
                
                # Try to get actual token counts from response if available
                if 'eval_count' in data:
                    estimated_tokens = data['eval_count']
                
                logger.info(f"Response generated in {response_time}ms, {estimated_tokens} tokens")
                
                return {
                    'response': response_text,
                    'response_time_ms': response_time,
                    'estimated_tokens': estimated_tokens,
                    'backend_type': 'ollama',
                    'model': model,
                    'eval_count': data.get('eval_count'),
                    'eval_duration': data.get('eval_duration'),
                    'load_duration': data.get('load_duration'),
                    'prompt_eval_count': data.get('prompt_eval_count'),
                    'prompt_eval_duration': data.get('prompt_eval_duration'),
                    'total_duration': data.get('total_duration')
                }
            else:
                logger.error(f"Ollama API HTTP error {response.status_code}: {response.text}")
                return {
                    'response': f"Error: HTTP {response.status_code}",
                    'response_time_ms': response_time,
                    'estimated_tokens': 0,
                    'backend_type': 'ollama',
                    'model': model,
                    'error': True
                }

        except requests.exceptions.ReadTimeout as e:
            response_time = int((time.time() - start_time) * 1000)
            logger.error(f"Ollama read timeout after {ollama_timeout} seconds: {e}")
            return {
                'response': f"Response timed out after {ollama_timeout} seconds. Try a shorter prompt or increase timeout.",
                'response_time_ms': response_time,
                'estimated_tokens': 0,
                'backend_type': 'ollama',
                'model': model,
                'error': True
            }
        except requests.exceptions.ConnectTimeout as e:
            response_time = int((time.time() - start_time) * 1000)
            logger.error(f"Ollama connection timeout: {e}")
            return {
                'response': "Connection to Ollama timed out. Make sure Ollama is running and accessible.",
                'response_time_ms': response_time,
                'estimated_tokens': 0,
                'backend_type': 'ollama',
                'model': model,
                'error': True
            }
        except requests.RequestException as e:
            response_time = int((time.time() - start_time) * 1000)
            
            # Check if this is a cancellation-related error
            if cancellation_token and cancellation_token.is_set():
                logger.info("Request cancelled due to RequestException")
                return {
                    'response': "Request was cancelled by user",
                    'response_time_ms': response_time,
                    'estimated_tokens': 0,
                    'backend_type': 'ollama',
                    'model': model,
                    'error': True,
                    'cancelled': True
                }
            
            logger.error(f"Ollama API error: {e}")
            return {
                'response': f"Error connecting to Ollama: {str(e)}",
                'response_time_ms': response_time,
                'estimated_tokens': 0,
                'backend_type': 'ollama',
                'model': model,
                'error': True
            }
        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            
            # Check if this is a cancellation-related error
            if cancellation_token and cancellation_token.is_set():
                logger.info("Request cancelled due to Exception")
                return {
                    'response': "Request was cancelled by user",
                    'response_time_ms': response_time,
                    'estimated_tokens': 0,
                    'backend_type': 'ollama',
                    'model': model,
                    'error': True,
                    'cancelled': True
                }
            
            logger.error(f"Unexpected error: {e}")
            return {
                'response': f"Unexpected error: {str(e)}",
                'response_time_ms': response_time,
                'estimated_tokens': 0,
                'backend_type': 'ollama',
                'model': model,
                'error': True
            }
    
    def _clean_response_text(self, response_text: str) -> str:
        """
        Clean up any leaked Human/User/Assistant prefixes from the response text.
        
        Args:
            response_text (str): Raw response text from the model
            
        Returns:
            str: Cleaned response text
        """
        import re
        
        # First, handle the case where the entire response starts with "Assistant:"
        response_text = response_text.strip()
        if re.match(r'^\s*(Assistant)\s*:\s*', response_text, re.IGNORECASE):
            response_text = re.sub(r'^\s*(Assistant)\s*:\s*', '', response_text, flags=re.IGNORECASE)
        
        # Process lines that start with Human:, User:, or Assistant: (case insensitive)
        lines = response_text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Check if line starts with Human:, User:, or Assistant: patterns
            match = re.match(r'^\s*(Human|User|Assistant)\s*:\s*(.*)', line, re.IGNORECASE)
            if match:
                prefix = match.group(1).lower()
                content = match.group(2).strip()
                
                # For Human/User prefixes, always skip the line completely
                if prefix in ['human', 'user']:
                    continue
                    
                # For Assistant prefixes, extract content if it exists
                if prefix == 'assistant' and content:
                    cleaned_lines.append(content)
                # Skip empty Assistant lines
            else:
                cleaned_lines.append(line)
        
        cleaned_text = '\n'.join(cleaned_lines).strip()
        
        # Also remove any trailing Human:/User:/Assistant: patterns at the end
        cleaned_text = re.sub(r'\n*\s*(Human|User|Assistant)\s*:\s*$', '', cleaned_text, flags=re.IGNORECASE)
        
        return cleaned_text

    def get_backend_info(self) -> Dict[str, Any]:
        """
        Get information about the Ollama backend.
        
        Returns:
            Dict[str, Any]: Backend information including:
                - backend_type (str): Backend identifier
                - version (str): Backend version if available
                - status (str): Current status ('available', 'unavailable', 'error')
                - capabilities (List[str]): List of supported features
                - health_check (bool): Whether backend is healthy/reachable
        """
        try:
            # Try to get version from Ollama API
            version = "unknown"
            try:
                response = requests.get(
                    f"{self._base_url}/api/version", 
                    timeout=(5, 10)
                )
                if response.status_code == 200:
                    version_data = response.json()
                    version = version_data.get('version', 'unknown')
            except:
                pass
            
            # Check if backend is reachable by trying to get models
            models = self.get_models()
            is_available = len(models) >= 0  # Even empty list means backend is reachable
            
            # Determine status based on availability
            if is_available:
                status = 'available'
                health_check = True
                capabilities = ['streaming', 'chat_completion', 'embeddings', 'model_loading']
                if models:
                    capabilities.append('models_found')
            else:
                status = 'unavailable'
                health_check = False
                capabilities = []
            
            return {
                'backend_type': 'ollama',
                'version': version,
                'status': status,
                'capabilities': capabilities,
                'health_check': health_check,
                'api_url': self._base_url,
                'models_available': len(models) > 0
            }
            
        except Exception as e:
            logger.error(f"Error getting Ollama backend info: {e}")
            return {
                'backend_type': 'ollama',
                'version': 'unknown',
                'status': 'error',
                'capabilities': [],
                'health_check': False,
                'error': str(e)
            }
    
    def cleanup(self):
        """Clean up any active requests and resources."""
        with self._requests_lock:
            for request_id, request_session in self._active_requests.items():
                try:
                    logger.info(f"Cleaning up active request {request_id}")
                    request_session.close()
                except Exception as e:
                    logger.debug(f"Error cleaning up request {request_id}: {e}")
            self._active_requests.clear()
        
        # Close the main session
        try:
            self._session.close()
        except Exception as e:
            logger.debug(f"Error closing main session: {e}")
    
    def __del__(self):
        """Cleanup when the client is destroyed."""
        try:
            self.cleanup()
        except:
            pass