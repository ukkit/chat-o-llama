"""Llama.cpp client implementation for Chat-O-Llama."""

import os
import time
import logging
import glob
import threading
from typing import List, Dict, Any, Optional, Union
from pathlib import Path

from config import get_config
from utils.token_estimation import estimate_tokens
from .llm_interface import LLMInterface

try:
    from llama_cpp import Llama
    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False
    Llama = None

logger = logging.getLogger(__name__)


class LlamaCppClient(LLMInterface):
    """
    Llama.cpp client implementation using llama-cpp-python.
    
    This client provides local model inference using GGUF model files.
    It implements the LLMInterface to ensure consistency with other backends.
    """

    def __init__(self):
        """Initialize the LlamaCpp client."""
        self._model = None
        self._current_model_name = None
        self._config = get_config()
        self._active_generations = {}  # Track active generation threads
        self._generations_lock = threading.Lock()
        
        if not LLAMA_CPP_AVAILABLE:
            logger.error("llama-cpp-python is not installed. Please install it to use the llama.cpp backend.")
            raise ImportError("llama-cpp-python package is required for LlamaCppClient")
        
        logger.info("LlamaCppClient initialized successfully")

    def _track_generation(self, request_id: str, generation_info: Dict[str, Any]) -> None:
        """Track an active generation for cancellation."""
        with self._generations_lock:
            self._active_generations[request_id] = generation_info

    def _untrack_generation(self, request_id: str) -> None:
        """Remove a generation from tracking."""
        with self._generations_lock:
            self._active_generations.pop(request_id, None)

    def _cancel_generation(self, request_id: str) -> bool:
        """Cancel an active generation if it exists."""
        with self._generations_lock:
            generation_info = self._active_generations.get(request_id)
            if generation_info:
                try:
                    # Set cancellation flag
                    generation_info['cancelled'] = True
                    logger.info(f"Marked LlamaCpp generation {request_id} for cancellation")
                    return True
                except Exception as e:
                    logger.warning(f"Error cancelling generation {request_id}: {e}")
                    return False
            return False

    def get_models(self) -> List[str]:
        """
        Get list of available GGUF models from the configured model directory.
        
        Scans the configured model directory recursively for .gguf files,
        extracts metadata from filenames, and returns standardized model names.
        
        Returns:
            List[str]: List of available model names. Returns empty list if
                      directory doesn't exist or on access errors.
        
        Raises:
            None: All exceptions are caught and logged, returning empty list.
        """
        try:
            llamacpp_config = self._config.get('llamacpp', {})
            model_path = llamacpp_config.get('model_path', './models')
            
            # Validate model path exists and is accessible
            if not self._validate_model_directory(model_path):
                return []
            
            # Search for GGUF files with recursive scanning
            model_files = self._discover_gguf_files(model_path)
            
            # Extract model names with metadata parsing
            model_names = self._extract_model_names(model_files)
            
            logger.info(f"Found {len(model_names)} GGUF models in {model_path}")
            if model_names:
                logger.debug(f"Available models: {model_names}")
            
            return sorted(model_names)
            
        except PermissionError as e:
            logger.error(f"Permission denied accessing model directory: {e}")
            return []
        except OSError as e:
            logger.error(f"OS error accessing model directory: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error scanning for GGUF models: {e}")
            return []

    def _validate_model_directory(self, model_path: str) -> bool:
        """
        Validate that the model directory exists and is accessible.
        
        Args:
            model_path (str): Path to the model directory
            
        Returns:
            bool: True if directory is valid and accessible, False otherwise
        """
        try:
            if not os.path.exists(model_path):
                logger.warning(f"Model directory does not exist: {model_path}")
                return False
                
            if not os.path.isdir(model_path):
                logger.warning(f"Model path is not a directory: {model_path}")
                return False
                
            if not os.access(model_path, os.R_OK):
                logger.warning(f"Model directory is not readable: {model_path}")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error validating model directory {model_path}: {e}")
            return False

    def _discover_gguf_files(self, model_path: str) -> List[str]:
        """
        Discover GGUF files in the model directory with recursive scanning.
        
        Args:
            model_path (str): Path to the model directory
            
        Returns:
            List[str]: List of full file paths to GGUF files
        """
        model_files = []
        
        try:
            # Use pathlib for more robust path handling
            model_dir = Path(model_path)
            
            # Recursive search for .gguf files
            gguf_files = list(model_dir.rglob("*.gguf"))
            
            # Convert to strings and validate each file
            for file_path in gguf_files:
                try:
                    # Check if file is accessible and has valid size
                    if file_path.is_file() and file_path.stat().st_size > 0:
                        model_files.append(str(file_path))
                    else:
                        logger.debug(f"Skipping invalid GGUF file: {file_path}")
                except (OSError, PermissionError) as e:
                    logger.debug(f"Cannot access GGUF file {file_path}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error discovering GGUF files in {model_path}: {e}")
            
        return model_files

    def _extract_model_names(self, model_files: List[str]) -> List[str]:
        """
        Extract standardized model names from GGUF file paths with metadata parsing.
        
        Args:
            model_files (List[str]): List of full file paths to GGUF files
            
        Returns:
            List[str]: List of standardized model names
        """
        model_names = []
        
        for file_path in model_files:
            try:
                filename = os.path.basename(file_path)
                
                # Remove .gguf extension
                model_name = filename[:-5] if filename.endswith('.gguf') else filename
                
                # Extract metadata for logging/debugging
                metadata = self._parse_gguf_metadata(filename)
                if metadata:
                    logger.debug(f"Model {model_name}: {metadata}")
                
                # Avoid duplicates
                if model_name not in model_names:
                    model_names.append(model_name)
                    
            except Exception as e:
                logger.warning(f"Error processing model file {file_path}: {e}")
                # Still include the filename even if metadata parsing fails
                filename = os.path.basename(file_path)
                if filename not in model_names:
                    model_names.append(filename)
                    
        return model_names

    def _parse_gguf_metadata(self, filename: str) -> Optional[Dict[str, Any]]:
        """
        Parse metadata from GGUF filename.
        
        Common GGUF filename patterns:
        - model-name-size-variant.quantization.gguf
        - llama-2-7b-chat.Q4_0.gguf
        - mistral-7b-instruct.Q5_K_M.gguf
        
        Args:
            filename (str): GGUF filename
            
        Returns:
            Optional[Dict[str, Any]]: Extracted metadata or None if parsing fails
        """
        try:
            # Remove .gguf extension
            name_part = filename[:-5] if filename.endswith('.gguf') else filename
            
            metadata = {}
            
            # Extract quantization (common patterns: Q4_0, Q5_K_M, Q8_0, etc.)
            import re
            # Look for quantization pattern: Q followed by digits, underscores, and letters
            quant_match = re.search(r'\.([Qq]\d+[_\d]*[_K]*[_M]*[_S]*[_L]*[_XS]*)$', name_part)
            if quant_match:
                metadata['quantization'] = quant_match.group(1).upper()
                # Remove quantization from name for further parsing
                name_part = name_part[:quant_match.start()]
            
            # Extract model size (7b, 13b, 70b, etc.)
            size_match = re.search(r'(\d+[bB])', name_part)
            if size_match:
                metadata['size'] = size_match.group(1).lower()
            
            # Extract model variant/type (chat, instruct, code, etc.)
            # Common variants after size
            variant_patterns = [
                r'(chat)', r'(instruct)', r'(code)', r'(uncensored)', 
                r'(orca)', r'(alpaca)', r'(vicuna)', r'(wizard)'
            ]
            for pattern in variant_patterns:
                variant_match = re.search(pattern, name_part, re.IGNORECASE)
                if variant_match:
                    metadata['variant'] = variant_match.group(1).lower()
                    break
            
            # Extract base model name (everything before size)
            base_match = re.match(r'^([^-]+(?:-[^-]+)*)', name_part)
            if base_match:
                base_name = base_match.group(1)
                # Clean up common prefixes/suffixes
                base_name = re.sub(r'^(.*?)(?:-\d+[bB].*)?$', r'\1', base_name)
                metadata['base_model'] = base_name
            
            return metadata if metadata else None
            
        except Exception as e:
            logger.debug(f"Failed to parse metadata from filename {filename}: {e}")
            return None

    def _load_model(self, model: str) -> bool:
        """
        Load a GGUF model file.
        
        Args:
            model (str): Model filename or path
            
        Returns:
            bool: True if model loaded successfully, False otherwise
        """
        try:
            # If model is already loaded, skip reloading
            if self._model is not None and self._current_model_name == model:
                return True
            
            # Unload current model if any
            if self._model is not None:
                del self._model
                self._model = None
                self._current_model_name = None
            
            llamacpp_config = self._config.get('llamacpp', {})
            model_path = llamacpp_config.get('model_path', './models')
            
            # Construct full model path
            if os.path.isabs(model):
                model_file_path = model
            else:
                # Try direct path first
                model_file_path = os.path.join(model_path, model)
                if not os.path.exists(model_file_path):
                    # Try with .gguf extension if not present
                    if not model.endswith('.gguf'):
                        model_file_path = os.path.join(model_path, model + '.gguf')
                    
                    if not os.path.exists(model_file_path):
                        # Search recursively for the model name
                        search_pattern = os.path.join(model_path, "**", model)
                        matches = glob.glob(search_pattern, recursive=True)
                        if not matches and not model.endswith('.gguf'):
                            # Try searching with .gguf extension
                            search_pattern = os.path.join(model_path, "**", model + '.gguf')
                            matches = glob.glob(search_pattern, recursive=True)
                        
                        if matches:
                            model_file_path = matches[0]
                        else:
                            logger.error(f"Model file not found: {model}")
                            return False
            
            if not os.path.exists(model_file_path):
                logger.error(f"Model file does not exist: {model_file_path}")
                return False
            
            logger.info(f"Loading model: {model_file_path}")
            
            # Load model with configuration
            # Note: rope_scaling_type should be an integer enum, not a string
            # For now, we'll skip rope_scaling_type to avoid parameter type issues
            self._model = Llama(
                model_path=model_file_path,
                n_ctx=llamacpp_config.get('n_ctx', 4096),
                n_batch=llamacpp_config.get('n_batch', 512),
                n_threads=llamacpp_config.get('n_threads', -1),
                n_gpu_layers=llamacpp_config.get('n_gpu_layers', 0),
                use_mmap=llamacpp_config.get('use_mmap', True),
                use_mlock=llamacpp_config.get('use_mlock', False),
                verbose=llamacpp_config.get('verbose', False),
                rope_freq_base=llamacpp_config.get('rope_freq_base', 10000.0),
                rope_freq_scale=llamacpp_config.get('rope_freq_scale', 1.0),
            )
            
            self._current_model_name = model
            logger.info(f"Model loaded successfully: {model}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load model {model}: {e}")
            self._model = None
            self._current_model_name = None
            return False

    def generate_response(
        self,
        model: str,
        prompt: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate response using llama.cpp.
        
        Args:
            model (str): Model filename to use
            prompt (str): Input prompt
            conversation_history (Optional[List[Dict]]): Previous conversation context
            **kwargs: Additional parameters (temperature, max_tokens, stream, etc.)
                - cancellation_token (threading.Event): Token to check for cancellation
        
        Returns:
            Dict[str, Any]: Response dictionary with standardized format matching Ollama
        """
        start_time = time.time()
        
        # Extract cancellation token from kwargs
        cancellation_token = kwargs.get('cancellation_token')
        request_id = kwargs.get('request_id', f"llamacpp_req_{int(time.time() * 1000)}")
        
        # Check for cancellation before starting
        if cancellation_token and cancellation_token.is_set():
            logger.info("Request cancelled before processing")
            response_time = int((time.time() - start_time) * 1000)
            return {
                'response': "Request was cancelled by user",
                'response_time_ms': response_time,
                'estimated_tokens': 0,
                'backend_type': 'llamacpp',
                'model': model,
                'error': True,
                'cancelled': True
            }
        
        try:
            # Load model if needed
            if not self._load_model(model):
                response_time = int((time.time() - start_time) * 1000)
                return self.get_standard_error_response(
                    f"Failed to load model: {model}",
                    response_time,
                    model
                )
            
            # Check for cancellation after model loading
            if cancellation_token and cancellation_token.is_set():
                logger.info("Request cancelled after model loading")
                response_time = int((time.time() - start_time) * 1000)
                return {
                    'response': "Request was cancelled by user",
                    'response_time_ms': response_time,
                    'estimated_tokens': 0,
                    'backend_type': 'llamacpp',
                    'model': model,
                    'error': True,
                    'cancelled': True
                }
            
            # Build context from conversation history
            full_prompt = self._build_prompt_with_history(prompt, conversation_history)
            
            # Extract generation parameters from config and kwargs
            generation_params = self._extract_generation_parameters(kwargs)
            
            # Check if streaming is requested
            stream = kwargs.get('stream', self._config.get('response_optimization', {}).get('stream', False))
            
            logger.debug(f"Generating response with prompt length: {len(full_prompt)} characters, stream={stream}")
            
            if stream:
                return self._generate_streaming_response(full_prompt, generation_params, model, start_time, cancellation_token, request_id)
            else:
                return self._generate_non_streaming_response(full_prompt, generation_params, model, start_time, cancellation_token, request_id)
            
        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            logger.error(f"Error generating response with llama.cpp: {e}")
            return self.get_standard_error_response(
                f"Generation error: {str(e)}",
                response_time,
                model
            )
    
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

    def _generate_with_cancellation_checks(
        self, 
        full_prompt: str, 
        generation_params: Dict[str, Any], 
        cancellation_token, 
        generation_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate response with cancellation checks.
        
        Args:
            full_prompt: The complete prompt to generate from
            generation_params: Generation parameters
            cancellation_token: Token to check for cancellation
            generation_info: Information about the generation request
            
        Returns:
            Dict[str, Any]: Response from the model
        """
        # For now, we'll use the synchronous approach but with frequent cancellation checks
        # In a future enhancement, we could implement true asynchronous generation
        
        # Check for cancellation before starting
        if cancellation_token and cancellation_token.is_set():
            return {
                'choices': [{'text': 'Request was cancelled by user'}],
                'usage': {'completion_tokens': 0, 'prompt_tokens': 0, 'total_tokens': 0},
                'cancelled': True
            }
        
        # Generate response - this is the blocking call
        response = self._model(
            prompt=full_prompt,
            max_tokens=generation_params['max_tokens'],
            temperature=generation_params['temperature'],
            top_p=generation_params['top_p'],
            top_k=generation_params['top_k'],
            repeat_penalty=generation_params['repeat_penalty'],
            stop=generation_params['stop'],
            echo=False,
        )
        
        # Check for cancellation after generation
        if cancellation_token and cancellation_token.is_set():
            return {
                'choices': [{'text': 'Request was cancelled by user'}],
                'usage': {'completion_tokens': 0, 'prompt_tokens': 0, 'total_tokens': 0},
                'cancelled': True
            }
            
        return response

    def _build_prompt_with_history(self, prompt: str, conversation_history: Optional[List[Dict[str, Any]]]) -> str:
        """
        Build full prompt including system prompt and conversation history.
        
        Args:
            prompt (str): Current user prompt
            conversation_history (Optional[List[Dict]]): Previous conversation context
            
        Returns:
            str: Complete formatted prompt
        """
        # Build context from conversation history
        system_prompt = self._config.get('system_prompt', '')
        context = f"{system_prompt}\n\n" if system_prompt else ""
        
        if conversation_history:
            # Use configurable history limit and filter out duplicate patterns
            history_limit = self._config['performance']['context_history_limit']
            recent_history = conversation_history[-history_limit:]
            
            # Only include unique conversation turns to prevent repetition
            seen_content = set()
            for msg in recent_history:
                content = msg['content'].strip()
                if content and content not in seen_content:
                    role = "Human" if msg['role'] == 'user' else "Assistant"
                    context += f"{role}: {content}\n"
                    seen_content.add(content)
        
        return f"{context}Human: {prompt}\nAssistant:"

    def _extract_generation_parameters(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract and validate generation parameters from config and kwargs.
        
        Args:
            kwargs (Dict[str, Any]): Additional parameters passed to generate_response
            
        Returns:
            Dict[str, Any]: Validated generation parameters
        """
        model_options = self._config.get('model_options', {})
        
        return {
            'max_tokens': kwargs.get('max_tokens', model_options.get('num_predict', 2048)),
            'temperature': kwargs.get('temperature', model_options.get('temperature', 0.5)),
            'top_p': kwargs.get('top_p', model_options.get('top_p', 0.8)),
            'top_k': kwargs.get('top_k', model_options.get('top_k', 30)),
            'repeat_penalty': kwargs.get('repeat_penalty', model_options.get('repeat_penalty', 1.1)),
            'stop': kwargs.get('stop', model_options.get('stop', ["\n\nHuman:", "\n\nUser:"]))
        }

    def _generate_non_streaming_response(
        self, 
        full_prompt: str, 
        generation_params: Dict[str, Any], 
        model: str, 
        start_time: float,
        cancellation_token=None,
        request_id: str = None
    ) -> Dict[str, Any]:
        """
        Generate a non-streaming response.
        
        Args:
            full_prompt (str): Complete formatted prompt
            generation_params (Dict[str, Any]): Generation parameters
            model (str): Model name
            start_time (float): Request start time
            cancellation_token (threading.Event): Optional cancellation token
            
        Returns:
            Dict[str, Any]: Response dictionary matching Ollama format
        """
        # Check for cancellation before generation
        if cancellation_token and cancellation_token.is_set():
            logger.info("Request cancelled before generation")
            response_time = int((time.time() - start_time) * 1000)
            return self.get_standard_error_response(
                "Request was cancelled",
                response_time,
                model
            )
        
        # Track this generation request
        generation_info = {
            'start_time': start_time,
            'model': model,
            'cancelled': False,
            'request_id': request_id
        }
        
        if request_id:
            self._track_generation(request_id, generation_info)
            
        try:
            # Generate response with cancellation checks
            response = self._generate_with_cancellation_checks(
                full_prompt, 
                generation_params, 
                cancellation_token, 
                generation_info
            )
            
            # Check for cancellation after generation
            if cancellation_token and cancellation_token.is_set():
                logger.info("Request cancelled after generation")
                response_time = int((time.time() - start_time) * 1000)
                return {
                    'response': "Request was cancelled by user",
                    'response_time_ms': response_time,
                    'estimated_tokens': 0,
                    'backend_type': 'llamacpp',
                    'model': model,
                    'error': True,
                    'cancelled': True
                }
        
        finally:
            # Clean up generation tracking
            if request_id:
                self._untrack_generation(request_id)
        
        # Check if response indicates cancellation
        if response.get('cancelled'):
            response_time = int((time.time() - start_time) * 1000)
            return {
                'response': "Request was cancelled by user",
                'response_time_ms': response_time,
                'estimated_tokens': 0,
                'backend_type': 'llamacpp',
                'model': model,
                'error': True,
                'cancelled': True
            }
        
        response_time = int((time.time() - start_time) * 1000)
        response_text = response['choices'][0]['text'].strip()
        
        # Clean up any leaked Human/User prefixes from the response
        response_text = self._clean_response_text(response_text)
        
        # Get token information from response
        usage = response.get('usage', {})
        completion_tokens = usage.get('completion_tokens', 0)
        prompt_tokens = usage.get('prompt_tokens', 0)
        total_tokens = usage.get('total_tokens', 0)
        
        # Fallback to estimation if usage data not available
        if completion_tokens == 0:
            completion_tokens = estimate_tokens(response_text)
        if prompt_tokens == 0:
            prompt_tokens = estimate_tokens(full_prompt)
        if total_tokens == 0:
            total_tokens = prompt_tokens + completion_tokens
        
        logger.info(f"Response generated in {response_time}ms, {completion_tokens} tokens")
        
        # Return response in Ollama-compatible format
        return {
            'response': response_text,
            'response_time_ms': response_time,
            'estimated_tokens': completion_tokens,
            'backend_type': 'llamacpp',
            'model': model,
            # Ollama-compatible fields
            'eval_count': completion_tokens,
            'eval_duration': response_time * 1000000,  # Convert to nanoseconds
            'load_duration': 0,  # Model already loaded
            'prompt_eval_count': prompt_tokens,
            'prompt_eval_duration': 0,  # Not tracked separately
            'total_duration': response_time * 1000000,  # Convert to nanoseconds
            # Additional llama.cpp specific fields
            'prompt_tokens': prompt_tokens,
            'completion_tokens': completion_tokens,
            'total_tokens': total_tokens,
            'finish_reason': response['choices'][0].get('finish_reason', 'stop')
        }

    def _generate_streaming_response(
        self, 
        full_prompt: str, 
        generation_params: Dict[str, Any], 
        model: str, 
        start_time: float,
        cancellation_token=None,
        request_id: str = None
    ) -> Dict[str, Any]:
        """
        Generate a streaming response.
        
        Args:
            full_prompt (str): Complete formatted prompt
            generation_params (Dict[str, Any]): Generation parameters
            model (str): Model name
            start_time (float): Request start time
            cancellation_token (threading.Event): Optional cancellation token
            
        Returns:
            Dict[str, Any]: Response dictionary with streaming data
        """
        try:
            # Check for cancellation before streaming
            if cancellation_token and cancellation_token.is_set():
                logger.info("Request cancelled before streaming")
                response_time = int((time.time() - start_time) * 1000)
                return self.get_standard_error_response(
                    "Request was cancelled",
                    response_time,
                    model
                )
            
            # Track this generation request
            generation_info = {
                'start_time': start_time,
                'model': model,
                'cancelled': False,
                'request_id': request_id,
                'streaming': True
            }
            
            if request_id:
                self._track_generation(request_id, generation_info)
                
            try:
                # For streaming, we collect all tokens and return complete response
                # Note: llama-cpp-python streaming would require different implementation
                # For now, we simulate streaming by generating normally but indicating it's streamed
                response_parts = []
                total_response = ""
                
                # Generate with streaming enabled (if supported by llama-cpp-python)
                stream_response = self._model(
                    prompt=full_prompt,
                    max_tokens=generation_params['max_tokens'],
                    temperature=generation_params['temperature'],
                    top_p=generation_params['top_p'],
                    top_k=generation_params['top_k'],
                    repeat_penalty=generation_params['repeat_penalty'],
                    stop=generation_params['stop'],
                    echo=False,
                    stream=True,  # Enable streaming in llama-cpp-python
                )
                
                # Collect streaming tokens with cancellation checks
                for token_data in stream_response:
                    # Check for cancellation during streaming
                    if cancellation_token and cancellation_token.is_set():
                        logger.info("Request cancelled during streaming")
                        response_time = int((time.time() - start_time) * 1000)
                        return self.get_standard_error_response(
                            "Request was cancelled",
                            response_time,
                            model
                        )
                    
                    if 'choices' in token_data and len(token_data['choices']) > 0:
                        token_text = token_data['choices'][0].get('text', '')
                        if token_text:
                            total_response += token_text
                            response_parts.append(token_text)
                            
            finally:
                # Clean up generation tracking
                if request_id:
                    self._untrack_generation(request_id)
            
            response_time = int((time.time() - start_time) * 1000)
            
            # Calculate token counts
            completion_tokens = estimate_tokens(total_response)
            prompt_tokens = estimate_tokens(full_prompt)
            total_tokens = prompt_tokens + completion_tokens
            
            logger.info(f"Streaming response generated in {response_time}ms, {completion_tokens} tokens")
            
            # Return streaming response in Ollama-compatible format
            return {
                'response': total_response.strip(),
                'response_time_ms': response_time,
                'estimated_tokens': completion_tokens,
                'backend_type': 'llamacpp',
                'model': model,
                'stream': True,
                'stream_parts': response_parts,
                # Ollama-compatible fields
                'eval_count': completion_tokens,
                'eval_duration': response_time * 1000000,
                'load_duration': 0,
                'prompt_eval_count': prompt_tokens,
                'prompt_eval_duration': 0,
                'total_duration': response_time * 1000000,
                # Additional fields
                'prompt_tokens': prompt_tokens,
                'completion_tokens': completion_tokens,
                'total_tokens': total_tokens,
                'finish_reason': 'stop'
            }
            
        except Exception as e:
            logger.warning(f"Streaming failed, falling back to non-streaming: {e}")
            # Fallback to non-streaming if streaming fails
            return self._generate_non_streaming_response(full_prompt, generation_params, model, start_time, cancellation_token, request_id)

    def get_backend_info(self) -> Dict[str, Any]:
        """
        Get information about the llama.cpp backend.
        
        Returns:
            Dict[str, Any]: Backend information
        """
        try:
            # Check if llama-cpp-python is available
            if not LLAMA_CPP_AVAILABLE:
                return {
                    'backend_type': 'llamacpp',
                    'version': 'unknown',
                    'status': 'unavailable',
                    'capabilities': [],
                    'health_check': False,
                    'error': 'llama-cpp-python not installed'
                }
            
            # Try to get version information
            try:
                import llama_cpp
                version = getattr(llama_cpp, '__version__', 'unknown')
            except:
                version = 'unknown'
            
            # Check if models directory exists
            llamacpp_config = self._config.get('llamacpp', {})
            model_path = llamacpp_config.get('model_path', './models')
            models_available = len(self.get_models()) > 0
            
            status = 'available' if os.path.exists(model_path) else 'unavailable'
            health_check = LLAMA_CPP_AVAILABLE and os.path.exists(model_path)
            
            capabilities = ['local_inference', 'gguf_models']
            if models_available:
                capabilities.append('models_found')
            
            return {
                'backend_type': 'llamacpp',
                'version': version,
                'status': status,
                'capabilities': capabilities,
                'health_check': health_check,
                'model_path': model_path,
                'models_available': models_available,
                'current_model': self._current_model_name
            }
            
        except Exception as e:
            logger.error(f"Error getting backend info: {e}")
            return {
                'backend_type': 'llamacpp',
                'version': 'unknown',
                'status': 'error',
                'capabilities': [],
                'health_check': False,
                'error': str(e)
            }
    
    def cleanup(self):
        """Clean up any active generations and resources."""
        with self._generations_lock:
            for request_id, generation_info in self._active_generations.items():
                try:
                    logger.info(f"Cleaning up active generation {request_id}")
                    generation_info['cancelled'] = True
                except Exception as e:
                    logger.debug(f"Error cleaning up generation {request_id}: {e}")
            self._active_generations.clear()
        
        # Clean up model
        if self._model is not None:
            try:
                del self._model
            except:
                pass
            self._model = None
            self._current_model_name = None

    def __del__(self):
        """Cleanup when client is destroyed."""
        try:
            self.cleanup()
        except:
            pass