"""
Backend manager for chat-o-llama.

This module provides the BackendManager class that orchestrates multiple
LLM backends, handles backend discovery, health checking, and provides
a unified interface for model operations.
"""

import asyncio
import logging
import os
from typing import Dict, List, Optional, Any, Union
from collections import defaultdict
import time

from .base import (
    LLMBackend, BackendType, ModelInfo, GenerationResponse, BackendHealth,
    BackendError, BackendTimeoutError, BackendConnectionError, ModelNotFoundError
)
from .ollama import OllamaBackend
from .llama_cpp import LlamaCppBackend
from .models import ConfigValidator

logger = logging.getLogger(__name__)


class BackendManager:
    """
    Manages multiple LLM backends and provides a unified interface.
    
    The BackendManager handles:
    - Backend discovery and initialization
    - Health monitoring and status tracking  
    - Model discovery across all backends
    - Request routing to appropriate backends
    - Error handling and fallback logic
    
    Example:
        config = {
            'backends': {
                'ollama': {
                    'type': 'ollama',
                    'url': 'http://localhost:11434',
                    'enabled': True
                },
                'llama_cpp': {
                    'type': 'llama_cpp', 
                    'url': 'http://localhost:8080',
                    'enabled': True
                }
            }
        }
        manager = BackendManager(config)
        await manager.initialize()
        models = await manager.get_all_models()
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the backend manager.
        
        Args:
            config: Configuration dictionary with backend definitions
        """
        self.config = config
        self.backends: Dict[str, LLMBackend] = {}
        self.backend_health: Dict[str, BackendHealth] = {}
        self._initialized = False
        self._health_check_task: Optional[asyncio.Task] = None
        self._health_check_interval = 30  # seconds
        
        logger.info("BackendManager initialized")
    
    async def initialize(self) -> None:
        """
        Initialize all configured backends.
        
        This method discovers and initializes all enabled backends from
        the configuration, validates their settings, and starts health monitoring.
        """
        if self._initialized:
            logger.warning("BackendManager already initialized")
            return
        
        backend_configs = self.config.get('backends', {})
        
        if not backend_configs:
            logger.warning("No backends configured")
            return
        
        # Initialize each configured backend
        for backend_id, backend_config in backend_configs.items():
            if not backend_config.get('enabled', True):
                logger.info(f"Backend {backend_id} is disabled, skipping")
                continue
            
            try:
                backend = await self._create_backend(backend_id, backend_config)
                if backend:
                    self.backends[backend_id] = backend
                    logger.info(f"Initialized backend: {backend_id}")
                else:
                    logger.error(f"Failed to create backend: {backend_id}")
            except Exception as e:
                logger.error(f"Error initializing backend {backend_id}: {e}")
        
        if not self.backends:
            logger.error("No backends successfully initialized")
        else:
            logger.info(f"Initialized {len(self.backends)} backends: {list(self.backends.keys())}")
        
        # Start health monitoring
        await self._start_health_monitoring()
        
        self._initialized = True
    
    async def _create_backend(self, backend_id: str, config: Dict[str, Any]) -> Optional[LLMBackend]:
        """
        Create a backend instance from configuration.
        
        Args:
            backend_id: Unique identifier for the backend
            config: Backend configuration dictionary
            
        Returns:
            LLMBackend instance or None if creation failed
        """
        backend_type = config.get('type', '').lower()
        
        # Apply environment variable overrides
        config = self._apply_env_overrides(backend_id, config)
        
        # Validate configuration
        validation_errors = self._validate_backend_config(backend_type, config)
        if validation_errors:
            logger.error(f"Configuration validation failed for {backend_id}: {validation_errors}")
            return None
        
        try:
            if backend_type == 'ollama':
                return OllamaBackend(backend_id, config)
            elif backend_type == 'llama_cpp':
                return LlamaCppBackend(backend_id, config)
            else:
                logger.error(f"Unknown backend type: {backend_type}")
                return None
        except Exception as e:
            logger.error(f"Error creating {backend_type} backend {backend_id}: {e}")
            return None
    
    def _apply_env_overrides(self, backend_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply environment variable overrides to backend configuration.
        
        Args:
            backend_id: Backend identifier
            config: Original configuration
            
        Returns:
            Configuration with environment overrides applied
        """
        config = config.copy()
        backend_type = config.get('type', '').upper()
        
        # Common environment variables
        url_env = f"{backend_type}_URL"
        timeout_env = f"{backend_type}_TIMEOUT"
        api_key_env = f"{backend_type}_API_KEY"
        
        # Apply overrides if environment variables exist
        if url_env in os.environ:
            config['url'] = os.environ[url_env]
            logger.info(f"Applied {url_env} override for {backend_id}")
        
        if timeout_env in os.environ:
            try:
                config['timeout'] = int(os.environ[timeout_env])
                logger.info(f"Applied {timeout_env} override for {backend_id}")
            except ValueError:
                logger.warning(f"Invalid timeout value in {timeout_env}")
        
        if api_key_env in os.environ:
            config['api_key'] = os.environ[api_key_env]
            logger.info(f"Applied {api_key_env} override for {backend_id}")
        
        return config
    
    def _validate_backend_config(self, backend_type: str, config: Dict[str, Any]) -> Dict[str, str]:
        """
        Validate backend configuration.
        
        Args:
            backend_type: Type of backend
            config: Configuration to validate
            
        Returns:
            Dictionary of validation errors (empty if valid)
        """
        if backend_type == 'ollama':
            return ConfigValidator.validate_ollama_config(config)
        elif backend_type == 'llama_cpp':
            return ConfigValidator.validate_llamacpp_config(config)
        else:
            return {'type': f"Unknown backend type: {backend_type}"}
    
    async def _start_health_monitoring(self) -> None:
        """Start background health monitoring task."""
        if self._health_check_task:
            self._health_check_task.cancel()
        
        self._health_check_task = asyncio.create_task(self._health_monitor_loop())
        logger.info("Started health monitoring")
    
    async def _health_monitor_loop(self) -> None:
        """Background loop for monitoring backend health."""
        while True:
            try:
                await self._check_all_backends_health()
                await asyncio.sleep(self._health_check_interval)
            except asyncio.CancelledError:
                logger.info("Health monitoring cancelled")
                break
            except Exception as e:
                logger.error(f"Error in health monitoring: {e}")
                await asyncio.sleep(5)  # Short delay before retry
    
    async def _check_all_backends_health(self) -> None:
        """Check health of all backends."""
        if not self.backends:
            return
        
        health_tasks = [
            self._check_backend_health(backend_id, backend)
            for backend_id, backend in self.backends.items()
        ]
        
        await asyncio.gather(*health_tasks, return_exceptions=True)
    
    async def _check_backend_health(self, backend_id: str, backend: LLMBackend) -> None:
        """Check health of a specific backend."""
        try:
            health = await backend.get_health()
            self.backend_health[backend_id] = health
            
            if health.is_healthy:
                logger.debug(f"Backend {backend_id} is healthy ({health.response_time_ms}ms)")
            else:
                logger.warning(f"Backend {backend_id} is unhealthy: {health.error_message}")
        except Exception as e:
            logger.error(f"Error checking health for {backend_id}: {e}")
    
    async def get_all_models(self) -> List[ModelInfo]:
        """
        Get all available models from all healthy backends.
        
        Returns:
            List of ModelInfo objects from all backends
        """
        if not self._initialized:
            await self.initialize()
        
        all_models = []
        model_tasks = []
        
        for backend_id, backend in self.backends.items():
            # Only query healthy backends
            health = self.backend_health.get(backend_id)
            if health and health.is_healthy:
                task = self._get_backend_models(backend_id, backend)
                model_tasks.append(task)
        
        if model_tasks:
            results = await asyncio.gather(*model_tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, list):
                    all_models.extend(result)
                elif isinstance(result, Exception):
                    logger.error(f"Error getting models: {result}")
        
        logger.debug(f"Retrieved {len(all_models)} total models from {len(model_tasks)} backends")
        return all_models
    
    async def _get_backend_models(self, backend_id: str, backend: LLMBackend) -> List[ModelInfo]:
        """Get models from a specific backend with error handling."""
        try:
            return await backend.get_models()
        except Exception as e:
            logger.error(f"Error getting models from {backend_id}: {e}")
            return []
    
    async def generate_response(
        self,
        model: str,
        prompt: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        preferred_backend: Optional[str] = None,
        **kwargs
    ) -> GenerationResponse:
        """
        Generate a response using the specified model.
        
        Args:
            model: Name of the model to use
            prompt: Input prompt for generation
            conversation_history: Previous messages in conversation
            preferred_backend: Preferred backend ID (optional)
            **kwargs: Additional generation parameters
            
        Returns:
            GenerationResponse object
            
        Raises:
            ModelNotFoundError: If model is not available on any backend
            BackendError: If all backends fail
        """
        if not self._initialized:
            await self.initialize()
        
        # Find backends that have the requested model
        available_backends = await self._find_model_backends(model)
        
        if not available_backends:
            raise ModelNotFoundError(f"Model '{model}' not found on any backend")
        
        # Sort backends by preference and health
        sorted_backends = self._sort_backends_by_preference(
            available_backends, preferred_backend
        )
        
        # Try each backend until one succeeds
        last_error = None
        for backend_id in sorted_backends:
            backend = self.backends[backend_id]
            
            try:
                response = await backend.generate_response(
                    model, prompt, conversation_history, **kwargs
                )
                logger.debug(f"Successfully generated response using {backend_id}")
                return response
                
            except (BackendTimeoutError, BackendConnectionError) as e:
                logger.warning(f"Backend {backend_id} failed: {e}")
                last_error = e
                # Mark backend as unhealthy and try next one
                await self._check_backend_health(backend_id, backend)
                continue
            except Exception as e:
                logger.error(f"Unexpected error from {backend_id}: {e}")
                last_error = e
                continue
        
        # All backends failed
        if last_error:
            raise last_error
        else:
            raise BackendError("All backends failed to generate response")
    
    async def _find_model_backends(self, model_name: str) -> List[str]:
        """
        Find backends that have the specified model.
        
        Args:
            model_name: Name of the model to find
            
        Returns:
            List of backend IDs that have the model
        """
        available_backends = []
        
        for backend_id, backend in self.backends.items():
            # Check if backend is healthy
            health = self.backend_health.get(backend_id)
            if not health or not health.is_healthy:
                continue
            
            try:
                models = await backend.get_models()
                model_names = [model.name for model in models]
                
                if model_name in model_names:
                    available_backends.append(backend_id)
                    
            except Exception as e:
                logger.warning(f"Error checking models for {backend_id}: {e}")
        
        return available_backends
    
    def _sort_backends_by_preference(
        self, 
        backend_ids: List[str], 
        preferred_backend: Optional[str] = None
    ) -> List[str]:
        """
        Sort backends by preference and health status.
        
        Args:
            backend_ids: List of available backend IDs
            preferred_backend: Preferred backend ID if any
            
        Returns:
            Sorted list of backend IDs
        """
        def backend_priority(backend_id: str) -> tuple:
            # Higher priority = lower tuple values
            health = self.backend_health.get(backend_id)
            
            # Preferred backend gets highest priority
            if backend_id == preferred_backend:
                preference_score = 0
            else:
                preference_score = 1
            
            # Healthy backends get priority over unhealthy
            if health and health.is_healthy:
                health_score = 0
                response_time = health.response_time_ms or 9999
            else:
                health_score = 1
                response_time = 9999
            
            return (preference_score, health_score, response_time)
        
        return sorted(backend_ids, key=backend_priority)
    
    async def get_backend_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get status information for all backends.
        
        Returns:
            Dictionary mapping backend IDs to their status information
        """
        if not self._initialized:
            await self.initialize()
        
        status = {}
        
        for backend_id, backend in self.backends.items():
            health = self.backend_health.get(backend_id)
            
            backend_status = {
                'info': backend.get_info(),
                'health': {
                    'status': health.status.value if health else 'unknown',
                    'response_time_ms': health.response_time_ms if health else None,
                    'error_message': health.error_message if health else None,
                    'last_checked': health.last_checked if health else None,
                    'models_available': health.models_available if health else 0
                }
            }
            
            status[backend_id] = backend_status
        
        return status
    
    async def refresh_backend_health(self, backend_id: Optional[str] = None) -> None:
        """
        Force refresh health status for backends.
        
        Args:
            backend_id: Specific backend to refresh, or None for all backends
        """
        if backend_id:
            if backend_id in self.backends:
                await self._check_backend_health(backend_id, self.backends[backend_id])
        else:
            await self._check_all_backends_health()
    
    def get_healthy_backends(self) -> List[str]:
        """
        Get list of currently healthy backend IDs.
        
        Returns:
            List of backend IDs that are currently healthy
        """
        healthy = []
        for backend_id, health in self.backend_health.items():
            if health and health.is_healthy:
                healthy.append(backend_id)
        return healthy
    
    def get_models_by_backend(self) -> Dict[str, List[str]]:
        """
        Get models grouped by backend (synchronous version for compatibility).
        
        Returns:
            Dictionary mapping backend IDs to lists of model names
        """
        # This is a synchronous method for backward compatibility
        # In practice, you should use get_all_models() which is async
        models_by_backend = defaultdict(list)
        
        # Return cached model information if available
        for backend_id, health in self.backend_health.items():
            if health and health.is_healthy:
                # This is a simplified version - in practice you'd want
                # to cache model lists from the async get_all_models() call
                models_by_backend[backend_id] = []
        
        return dict(models_by_backend)
    
    async def shutdown(self) -> None:
        """Shutdown the backend manager and clean up resources."""
        logger.info("Shutting down BackendManager")
        
        # Cancel health monitoring
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        # Close all backend sessions
        for backend_id, backend in self.backends.items():
            try:
                await backend.close()
                logger.debug(f"Closed backend: {backend_id}")
            except Exception as e:
                logger.error(f"Error closing backend {backend_id}: {e}")
        
        self.backends.clear()
        self.backend_health.clear()
        self._initialized = False
        
        logger.info("BackendManager shutdown complete")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.shutdown()


# Synchronous wrapper for backward compatibility
class BackendManagerSync:
    """
    Synchronous wrapper for BackendManager to maintain backward compatibility.
    
    This class provides a synchronous interface that matches the original
    OllamaAPI class behavior while using the new BackendManager internally.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize with configuration."""
        self.config = config
        self.manager = BackendManager(config)
        self._loop = None
        self._initialized = False
    
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
            task = asyncio.create_task(coro)
            return loop.run_until_complete(task)
        else:
            return loop.run_until_complete(coro)
    
    def _ensure_initialized(self):
        """Ensure the manager is initialized."""
        if not self._initialized:
            self._run_async(self.manager.initialize())
            self._initialized = True
    
    def get_models(self) -> List[str]:
        """Get list of all model names (synchronous)."""
        try:
            self._ensure_initialized()
            models = self._run_async(self.manager.get_all_models())
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
            self._ensure_initialized()
            response = self._run_async(
                self.manager.generate_response(model, prompt, conversation_history)
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
    
    def get_backend_status(self) -> Dict[str, Any]:
        """Get backend status information (synchronous)."""
        try:
            self._ensure_initialized()
            return self._run_async(self.manager.get_backend_status())
        except Exception as e:
            logger.error(f"Error getting backend status: {e}")
            return {}
    
    def __del__(self):
        """Cleanup on deletion."""
        if self._initialized:
            try:
                self._run_async(self.manager.shutdown())
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")
