"""
Ollama backend implementation for chat-o-llama.

This module provides the OllamaBackend class that implements the LLMBackend
interface for communicating with Ollama API endpoints.
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


class OllamaBackend(LLMBackend):
    """
    Ollama backend implementation.
    
    This class implements the LLMBackend interface for Ollama API endpoints.
    It handles model discovery, response generation, and health checking
    for Ollama instances.
    
    Example:
        config = {
            'url': 'http://localhost:11434',
            'timeout': 180,
            'connect_timeout': 15
        }
        backend = OllamaBackend('ollama-local', config)
        models = await backend.get_models()
        response = await backend.generate_response('llama3.2', 'Hello!')
    """
    
    def __init__(self, backend_id: str, config: Dict[str, Any]):
        """
        Initialize Ollama backend.
        
        Args:
            backend_id: Unique identifier for this backend instance
            config: Configuration dictionary with Ollama-specific settings
        """
        super().__init__(backend_id, config)
        
        # Ollama-specific configuration
        self.api_url = f"{self.base_url.rstrip('/')}/api"
        
        # Create aiohttp session with appropriate timeouts
        self._session: Optional[aiohttp.ClientSession] = None
        
        logger.info(f"Ollama backend initialized: {backend_id} at {self.api_url}")
    
    @property
    def backend_type(self) -> BackendType:
        """Get the backend type."""
        return BackendType.OLLAMA
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(
                total=self.timeout,
                connect=self.connect_timeout
            )
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session
    
    async def close(self):
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def get_models(self) -> List[ModelInfo]:
        """
        Get list of available models from Ollama.
        
        Returns:
            List of ModelInfo objects representing available models
            
        Raises:
            BackendError: If unable to retrieve models
        """
        try:
            session = await self._get_session()
            
            async with session.get(f"{self.api_url}/tags") as response:
                if response.status == 200:
                    data = await response.json()
                    models_data = data.get('models', [])
                    
                    models = []
                    for model_data in models_data:
                        model_info = ModelInfo(
                            name=model_data.get('name', ''),
                            backend_type=self.backend_type,
                            backend_id=self.backend_id,
                            size_bytes=model_data.get('size'),
                            modified_time=model_data.get('modified_at'),
                            digest=model_data.get('digest'),
                            details=model_data.get('details', {})
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
        Generate a response using Ollama API.
        
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
            # Build context from conversation history
            context = self._build_context(conversation_history)
            full_prompt = f"{context}Human: {prompt}\nAssistant:"
            
            # Build payload with configuration options
            payload = {
                "model": model,
                "prompt": full_prompt,
                "stream": False,
                "options": self._get_generation_options(**kwargs),
                "keep_alive": self.config.get('keep_alive', '5m')
            }
            
            session = await self._get_session()
            
            async with session.post(f"{self.api_url}/generate", json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Normalize response using ResponseNormalizer
                    return ResponseNormalizer.normalize_ollama_response(
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
        Check if Ollama backend is available and responsive.
        
        Returns:
            True if backend is available, False otherwise
        """
        try:
            session = await self._get_session()
            
            # Use a simple endpoint to check availability
            async with session.get(f"{self.api_url}/tags") as response:
                return response.status == 200
                
        except Exception as e:
            logger.debug(f"Availability check failed for {self.backend_id}: {e}")
            return False
    
    def _build_context(self, conversation_history: Optional[List[Dict[str, str]]] = None) -> str:
        """
        Build context string from conversation history.
        
        Args:
            conversation_history: List of previous messages
            
        Returns:
            Formatted context string
        """
        if not conversation_history:
            return self.config.get('system_prompt', '') + "\n\n"
        
        context = self.config.get('system_prompt', '') + "\n\n"
        
        # Use configurable history limit
        history_limit = self.config.get('context_history_limit', 10)
        recent_history = conversation_history[-history_limit:] if history_limit > 0 else conversation_history
        
        for msg in recent_history:
            role = "Human" if msg.get('role') == 'user' else "Assistant"
            content = msg.get('content', '')
            context += f"{role}: {content}\n"
        
        return context
    
    def _get_generation_options(self, **kwargs) -> Dict[str, Any]:
        """
        Get generation options merged from config and kwargs.
        
        Args:
            **kwargs: Override options
            
        Returns:
            Dictionary of generation options
        """
        # Start with default options from config
        options = self.config.get('model_options', {}).copy()
        
        # Add performance options
        performance_config = self.config.get('performance', {})
        for key in ['num_thread', 'num_gpu', 'use_mlock', 'use_mmap']:
            if key in performance_config:
                options[key] = performance_config[key]
        
        # Add response optimization options
        response_config = self.config.get('response_optimization', {})
        for key in ['f16_kv', 'logits_all', 'vocab_only', 'embedding_only', 'numa']:
            if key in response_config:
                options[key] = response_config[key]
        
        # Override with any provided kwargs
        options.update(kwargs)
        
        return options
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


# Synchronous wrapper for backward compatibility
class OllamaAPI:
    """
    Synchronous wrapper for OllamaBackend to maintain backward compatibility.
    
    This class provides the same interface as the original OllamaAPI class
    but uses the new OllamaBackend implementation internally.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize with configuration."""
        self.config = config
        self.backend = OllamaBackend('ollama-default', config)
        self._loop = None
    
    def _get_loop(self):
        """Get or create event loop."""
        try:
            return asyncio.get_running_loop()
        except RuntimeError:
            if self._loop is None:
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
            return self._loop
    
    def _run_async(self, coro):
        """Run async coroutine in sync context."""
        loop = self._get_loop()
        if loop.is_running():
            # If we're already in an event loop, create a new task
            # This shouldn't happen in normal Flask usage
            task = asyncio.create_task(coro)
            return loop.run_until_complete(task)
        else:
            return loop.run_until_complete(coro)
    
    def get_models(self) -> List[str]:
        """Get list of model names (synchronous)."""
        try:
            models = self._run_async(self.backend.get_models())
            return [model.name for model in models]
        except Exception as e:
            logger.error(f"Error getting models: {e}")
            return []
    
    def generate_response(
        self,
        model: str,
        prompt: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """Generate response (synchronous)."""
        try:
            response = self._run_async(
                self.backend.generate_response(model, prompt, conversation_history)
            )
            
            # Convert to format expected by original API
            return {
                'response': response.content,
                'response_time_ms': response.response_time_ms,
                'estimated_tokens': response.estimated_tokens,
                'eval_count': response.actual_tokens,
                'eval_duration': response.raw_response.get('eval_duration') if response.raw_response else None,
                'load_duration': response.raw_response.get('load_duration') if response.raw_response else None,
                'prompt_eval_count': response.prompt_tokens,
                'prompt_eval_duration': response.raw_response.get('prompt_eval_duration') if response.raw_response else None,
                'total_duration': response.raw_response.get('total_duration') if response.raw_response else None
            }
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return {
                'response': f"Error: {str(e)}",
                'response_time_ms': 0,
                'estimated_tokens': 0
            }
    
    def __del__(self):
        """Cleanup on deletion."""
        if self._loop and not self._loop.is_closed():
            # Schedule cleanup of the backend
            if self.backend._session and not self.backend._session.closed:
                self._loop.create_task(self.backend.close())