"""
Llama.cpp backend implementation for chat-o-llama.

This module provides the LlamaCppBackend class that implements the LLMBackend
interface for communicating with llama.cpp server using OpenAI-compatible API.
"""

import time
import logging
from typing import Dict, List, Optional, Any
import aiohttp
import asyncio

from .base import (
    LLMBackend, BackendType, ModelInfo, GenerationResponse,
    BackendError, BackendTimeoutError, BackendConnectionError, ModelNotFoundError
)
from .models import ResponseNormalizer, ConversationMessage

logger = logging.getLogger(__name__)


class LlamaCppBackend(LLMBackend):
    """
    Llama.cpp backend implementation.
    
    This class implements the LLMBackend interface for llama.cpp server
    using the OpenAI-compatible API endpoints. It handles model discovery,
    response generation, and health checking for llama.cpp instances.
    
    Example:
        config = {
            'url': 'http://localhost:8080',
            'timeout': 180,
            'connect_timeout': 15,
            'api_key': 'optional-api-key'
        }
        backend = LlamaCppBackend('llama-cpp-local', config)
        models = await backend.get_models()
        response = await backend.generate_response('model', 'Hello!')
    """
    
    def __init__(self, backend_id: str, config: Dict[str, Any]):
        """
        Initialize llama.cpp backend.
        
        Args:
            backend_id: Unique identifier for this backend instance
            config: Configuration dictionary with llama.cpp-specific settings
        """
        super().__init__(backend_id, config)
        
        # Llama.cpp-specific configuration
        self.api_url = f"{self.base_url.rstrip('/')}/v1"
        self.api_key = config.get('api_key')
        
        # Create aiohttp session with appropriate timeouts and headers
        self._session: Optional[aiohttp.ClientSession] = None
        
        logger.info(f"Llama.cpp backend initialized: {backend_id} at {self.api_url}")
    
    @property
    def backend_type(self) -> BackendType:
        """Get the backend type."""
        return BackendType.LLAMA_CPP
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session with proper headers."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(
                total=self.timeout,
                connect=self.connect_timeout
            )
            
            headers = {
                'Content-Type': 'application/json'
            }
            
            # Add API key if configured
            if self.api_key:
                headers['Authorization'] = f'Bearer {self.api_key}'
            
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers=headers
            )
        return self._session
    
    async def close(self):
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def get_models(self) -> List[ModelInfo]:
        """
        Get list of available models from llama.cpp server.
        
        Returns:
            List of ModelInfo objects representing available models
            
        Raises:
            BackendError: If unable to retrieve models
        """
        try:
            session = await self._get_session()
            
            async with session.get(f"{self.api_url}/models") as response:
                if response.status == 200:
                    data = await response.json()
                    models_data = data.get('data', [])
                    
                    models = []
                    for model_data in models_data:
                        model_info = ModelInfo(
                            name=model_data.get('id', ''),
                            backend_type=self.backend_type,
                            backend_id=self.backend_id,
                            details={
                                'object': model_data.get('object'),
                                'created': model_data.get('created'),
                                'owned_by': model_data.get('owned_by')
                            }
                        )
                        models.append(model_info)
                    
                    logger.debug(f"Retrieved {len(models)} models from {self.backend_id}")
                    return models
                else:
                    error_text = await response.text()
                    raise BackendError(
                        f"HTTP {response.status}: {error_text}",
                        backend_id=self.backend_id
                    )
                    
        except asyncio.TimeoutError as e:
            raise BackendTimeoutError(
                f"Timeout getting models from {self.backend_id}",
                backend_id=self.backend_id,
                cause=e
            )
        except aiohttp.ClientConnectionError as e:
            raise BackendConnectionError(
                f"Connection error getting models from {self.backend_id}: {str(e)}",
                backend_id=self.backend_id,
                cause=e
            )
        except Exception as e:
            raise BackendError(
                f"Unexpected error getting models from {self.backend_id}: {str(e)}",
                backend_id=self.backend_id,
                cause=e
            )
    
    async def generate_response(
        self,
        model: str,
        prompt: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ) -> GenerationResponse:
        """
        Generate a response using llama.cpp OpenAI-compatible API.
        
        Args:
            model: Name of the model to use
            prompt: Input prompt for generation
            conversation_history: Previous messages in conversation
            **kwargs: Additional generation parameters
            
        Returns:
            GenerationResponse object with normalized response data
            
        Raises:
            BackendError: If generation fails
            ModelNotFoundError: If specified model is not available
        """
        start_time = time.time()
        start_time_ms = int(start_time * 1000)
        
        try:
            # Build messages array from conversation history and current prompt
            messages = self._build_messages(conversation_history, prompt)
            
            # Build payload with configuration options
            payload = {
                "model": model,
                "messages": messages,
                "stream": False,
                **self._get_generation_options(**kwargs)
            }
            
            session = await self._get_session()
            
            async with session.post(f"{self.api_url}/chat/completions", json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Normalize response using ResponseNormalizer
                    return ResponseNormalizer.normalize_llamacpp_response(
                        data, model, self.backend_id, start_time_ms
                    )
                elif response.status == 404:
                    raise ModelNotFoundError(
                        f"Model '{model}' not found in {self.backend_id}",
                        backend_id=self.backend_id
                    )
                else:
                    error_text = await response.text()
                    raise BackendError(
                        f"HTTP {response.status}: {error_text}",
                        backend_id=self.backend_id
                    )
                    
        except asyncio.TimeoutError as e:
            raise BackendTimeoutError(
                f"Timeout generating response from {self.backend_id} with model {model}",
                backend_id=self.backend_id,
                cause=e
            )
        except aiohttp.ClientConnectionError as e:
            raise BackendConnectionError(
                f"Connection error generating response from {self.backend_id}: {str(e)}",
                backend_id=self.backend_id,
                cause=e
            )
        except (ModelNotFoundError, BackendTimeoutError, BackendConnectionError):
            # Re-raise these specific exceptions
            raise
        except Exception as e:
            raise BackendError(
                f"Unexpected error generating response from {self.backend_id}: {str(e)}",
                backend_id=self.backend_id,
                cause=e
            )
    
    async def is_available(self) -> bool:
        """
        Check if llama.cpp backend is available and responsive.
        
        Returns:
            True if backend is available, False otherwise
        """
        try:
            session = await self._get_session()
            
            # Use the models endpoint to check availability
            async with session.get(f"{self.api_url}/models") as response:
                return response.status == 200
                
        except Exception as e:
            logger.debug(f"Availability check failed for {self.backend_id}: {e}")
            return False
    
    def _build_messages(
        self, 
        conversation_history: Optional[List[Dict[str, str]]] = None,
        current_prompt: str = ""
    ) -> List[Dict[str, str]]:
        """
        Build OpenAI-compatible messages array from conversation history.
        
        Args:
            conversation_history: List of previous messages
            current_prompt: Current user prompt
            
        Returns:
            List of message dictionaries in OpenAI format
        """
        messages = []
        
        # Add system prompt if configured
        system_prompt = self.config.get('system_prompt')
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        # Add conversation history
        if conversation_history:
            # Use configurable history limit
            history_limit = self.config.get('context_history_limit', 10)
            recent_history = conversation_history[-history_limit:] if history_limit > 0 else conversation_history
            
            for msg in recent_history:
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                
                # Convert role names if needed
                if role == 'assistant':
                    role = 'assistant'
                elif role == 'user':
                    role = 'user'
                
                messages.append({
                    "role": role,
                    "content": content
                })
        
        # Add current prompt
        if current_prompt:
            messages.append({
                "role": "user",
                "content": current_prompt
            })
        
        return messages
    
    def _get_generation_options(self, **kwargs) -> Dict[str, Any]:
        """
        Get generation options for llama.cpp API.
        
        Maps chat-o-llama configuration to OpenAI-compatible parameters.
        
        Args:
            **kwargs: Override options
            
        Returns:
            Dictionary of generation options compatible with OpenAI API
        """
        options = {}
        
        # Map model options from config
        model_config = self.config.get('model_options', {})
        
        # Direct mappings
        if 'temperature' in model_config:
            options['temperature'] = model_config['temperature']
        if 'top_p' in model_config:
            options['top_p'] = model_config['top_p']
        if 'num_predict' in model_config:
            options['max_tokens'] = model_config['num_predict']
        if 'frequency_penalty' in model_config:
            options['frequency_penalty'] = model_config['frequency_penalty']
        if 'presence_penalty' in model_config:
            options['presence_penalty'] = model_config['presence_penalty']
        if 'stop' in model_config:
            options['stop'] = model_config['stop']
        if 'seed' in model_config and model_config['seed'] is not None:
            options['seed'] = model_config['seed']
        
        # Llama.cpp specific options (if supported)
        performance_config = self.config.get('performance', {})
        if 'num_ctx' in model_config:
            # Some llama.cpp implementations support context length
            options['max_context_length'] = model_config['num_ctx']
        
        # Override with any provided kwargs
        options.update(kwargs)
        
        return options
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
