"""Backend factory for LLM implementations in Chat-O-Llama."""

import logging
import time
from typing import Dict, Any, Optional, List
from enum import Enum

from config import get_config
from .llm_interface import LLMInterface
from .ollama_client import OllamaAPI
from .llamacpp_client import LlamaCppClient

logger = logging.getLogger(__name__)


class BackendType(Enum):
    """Enumeration of supported backend types."""
    OLLAMA = "ollama"
    LLAMACPP = "llamacpp"


class BackendStatus(Enum):
    """Enumeration of backend status states."""
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    ERROR = "error"
    INITIALIZING = "initializing"


class LLMFactory:
    """
    Factory class for creating and managing LLM backend instances.
    
    This factory provides:
    - Configuration-based backend instantiation
    - Backend health checking
    - Runtime backend switching
    - Fallback mechanism when primary backend fails
    """
    
    def __init__(self):
        """Initialize the LLM factory."""
        self._config = get_config()
        self._backends: Dict[str, LLMInterface] = {}
        self._backend_status: Dict[str, BackendStatus] = {}
        self._last_health_check: Dict[str, float] = {}
        self._active_backend: Optional[str] = self._config.get('backend', {}).get('active', 'ollama')
        
        logger.info(f"LLMFactory initialized with active backend: {self._active_backend}")
    
    def get_backend(self, backend_type: Optional[str] = None) -> LLMInterface:
        """
        Get a backend instance based on configuration or specified type.
        
        Args:
            backend_type (Optional[str]): Specific backend type to get.
                If None, uses the current active backend from runtime state.
        
        Returns:
            LLMInterface: Backend instance
            
        Raises:
            ValueError: If backend type is invalid or unavailable
            RuntimeError: If no backends are available
        """
        if backend_type is None:
            # Use the current runtime active backend, not the config file
            backend_type = self._active_backend or self._config.get('backend', {}).get('active', 'ollama')
        
        # Validate backend type
        if backend_type not in [bt.value for bt in BackendType]:
            raise ValueError(f"Invalid backend type: {backend_type}")
        
        # Try to get or create backend instance
        try:
            backend = self._get_or_create_backend(backend_type)
            
            # Check if backend is healthy
            if not self._is_backend_healthy(backend_type):
                raise RuntimeError(f"Backend {backend_type} failed health check")
                
        except Exception as e:
            # Backend creation or health check failed
            logger.warning(f"Backend {backend_type} failed: {e}")
            
            if self._config.get('backend', {}).get('auto_fallback', True):
                fallback_backend = self._get_fallback_backend(backend_type)
                if fallback_backend:
                    logger.warning(f"Backend {backend_type} unavailable, falling back to {fallback_backend}")
                    try:
                        fallback_backend_instance = self._get_or_create_backend(fallback_backend)
                        if self._is_backend_healthy(fallback_backend):
                            self._active_backend = fallback_backend
                            return fallback_backend_instance
                        else:
                            raise RuntimeError(f"Fallback backend {fallback_backend} is also unhealthy")
                    except Exception as fallback_error:
                        logger.error(f"Fallback to {fallback_backend} also failed: {fallback_error}")
                        raise RuntimeError(f"Both primary backend {backend_type} and fallback {fallback_backend} failed")
            
            raise RuntimeError(f"Backend {backend_type} is not available and no fallback found")
        
        self._active_backend = backend_type
        return backend
    
    def switch_backend(self, new_backend_type: str) -> bool:
        """
        Switch to a different backend at runtime.
        
        Args:
            new_backend_type (str): The backend type to switch to
            
        Returns:
            bool: True if switch was successful, False otherwise
        """
        try:
            # Validate new backend type
            if new_backend_type not in [bt.value for bt in BackendType]:
                logger.error(f"Invalid backend type for switching: {new_backend_type}")
                return False
            
            # Try to get the new backend
            new_backend = self._get_or_create_backend(new_backend_type)
            
            # Check if new backend is healthy
            if not self._is_backend_healthy(new_backend_type):
                logger.error(f"Cannot switch to unhealthy backend: {new_backend_type}")
                return False
            
            # Update active backend
            old_backend = self._active_backend
            self._active_backend = new_backend_type
            
            logger.info(f"Successfully switched backend from {old_backend} to {new_backend_type}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to switch backend to {new_backend_type}: {e}")
            return False
    
    def get_active_backend_type(self) -> Optional[str]:
        """
        Get the currently active backend type.
        
        Returns:
            Optional[str]: Active backend type or None if not set
        """
        return self._active_backend
    
    def get_backend_status(self, backend_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Get status information for a specific backend or all backends.
        
        Args:
            backend_type (Optional[str]): Specific backend to check. If None, returns all.
            
        Returns:
            Dict[str, Any]: Status information
        """
        if backend_type:
            return self._get_single_backend_status(backend_type)
        
        # Return status for all backends
        status = {}
        for bt in BackendType:
            status[bt.value] = self._get_single_backend_status(bt.value)
        
        return {
            'backends': status,
            'active_backend': self._active_backend,
            'auto_fallback': self._config.get('backend', {}).get('auto_fallback', True)
        }
    
    def health_check(self, backend_type: Optional[str] = None) -> Dict[str, bool]:
        """
        Perform health check on backends.
        
        Args:
            backend_type (Optional[str]): Specific backend to check. If None, checks all.
            
        Returns:
            Dict[str, bool]: Health status for each backend
        """
        results = {}
        
        if backend_type:
            results[backend_type] = self._is_backend_healthy(backend_type)
        else:
            for bt in BackendType:
                results[bt.value] = self._is_backend_healthy(bt.value)
        
        return results
    
    def get_available_models(self, backend_type: Optional[str] = None) -> Dict[str, List[str]]:
        """
        Get available models from specified backend or all backends.
        
        Args:
            backend_type (Optional[str]): Specific backend to query. If None, queries all.
            
        Returns:
            Dict[str, List[str]]: Models available for each backend
        """
        results = {}
        
        if backend_type:
            try:
                backend = self._get_or_create_backend(backend_type)
                results[backend_type] = backend.get_models()
            except Exception as e:
                logger.error(f"Failed to get models from {backend_type}: {e}")
                results[backend_type] = []
        else:
            for bt in BackendType:
                try:
                    backend = self._get_or_create_backend(bt.value)
                    results[bt.value] = backend.get_models()
                except Exception as e:
                    logger.error(f"Failed to get models from {bt.value}: {e}")
                    results[bt.value] = []
        
        return results
    
    def _get_or_create_backend(self, backend_type: str) -> LLMInterface:
        """
        Get existing backend instance or create a new one.
        
        Args:
            backend_type (str): Backend type to get or create
            
        Returns:
            LLMInterface: Backend instance
            
        Raises:
            ValueError: If backend type is not supported
        """
        if backend_type in self._backends:
            return self._backends[backend_type]
        
        # Create new backend instance
        if backend_type == BackendType.OLLAMA.value:
            backend = OllamaAPI()
        elif backend_type == BackendType.LLAMACPP.value:
            backend = LlamaCppClient()
        else:
            raise ValueError(f"Unsupported backend type: {backend_type}")
        
        self._backends[backend_type] = backend
        self._backend_status[backend_type] = BackendStatus.INITIALIZING
        
        logger.info(f"Created new backend instance: {backend_type}")
        return backend
    
    def _is_backend_healthy(self, backend_type: str) -> bool:
        """
        Check if a backend is healthy, using cached result if recent.
        
        Args:
            backend_type (str): Backend type to check
            
        Returns:
            bool: True if backend is healthy, False otherwise
        """
        current_time = time.time()
        health_check_interval = self._config.get('backend', {}).get('health_check_interval', 30)
        
        # Check if we have a recent health check result
        if (backend_type in self._last_health_check and 
            current_time - self._last_health_check[backend_type] < health_check_interval):
            return self._backend_status.get(backend_type) == BackendStatus.AVAILABLE
        
        # Perform fresh health check
        return self._perform_health_check(backend_type)
    
    def _perform_health_check(self, backend_type: str) -> bool:
        """
        Perform actual health check on a backend.
        
        Args:
            backend_type (str): Backend type to check
            
        Returns:
            bool: True if backend is healthy, False otherwise
        """
        try:
            backend = self._get_or_create_backend(backend_type)
            backend_info = backend.get_backend_info()
            
            is_healthy = backend_info.get('health_check', False)
            status = BackendStatus.AVAILABLE if is_healthy else BackendStatus.UNAVAILABLE
            
            self._backend_status[backend_type] = status
            self._last_health_check[backend_type] = time.time()
            
            logger.debug(f"Health check for {backend_type}: {'healthy' if is_healthy else 'unhealthy'}")
            return is_healthy
            
        except Exception as e:
            logger.error(f"Health check failed for {backend_type}: {e}")
            self._backend_status[backend_type] = BackendStatus.ERROR
            self._last_health_check[backend_type] = time.time()
            return False
    
    def _get_fallback_backend(self, failed_backend: str) -> Optional[str]:
        """
        Get fallback backend when primary backend fails.
        
        Args:
            failed_backend (str): Backend that failed
            
        Returns:
            Optional[str]: Fallback backend type or None if no fallback available
        """
        # Define fallback order
        fallback_order = {
            BackendType.OLLAMA.value: [BackendType.LLAMACPP.value],
            BackendType.LLAMACPP.value: [BackendType.OLLAMA.value]
        }
        
        potential_fallbacks = fallback_order.get(failed_backend, [])
        
        for fallback in potential_fallbacks:
            try:
                if self._perform_health_check(fallback):
                    return fallback
            except Exception as e:
                logger.debug(f"Fallback {fallback} also failed: {e}")
                continue
        
        return None
    
    def _get_single_backend_status(self, backend_type: str) -> Dict[str, Any]:
        """
        Get detailed status for a single backend.
        
        Args:
            backend_type (str): Backend type to get status for
            
        Returns:
            Dict[str, Any]: Detailed status information
        """
        try:
            backend = self._get_or_create_backend(backend_type)
            backend_info = backend.get_backend_info()
            
            return {
                'type': backend_type,
                'status': self._backend_status.get(backend_type, BackendStatus.UNAVAILABLE).value,
                'last_health_check': self._last_health_check.get(backend_type, 0),
                'backend_info': backend_info,
                'is_active': backend_type == self._active_backend
            }
            
        except Exception as e:
            logger.error(f"Failed to get status for {backend_type}: {e}")
            return {
                'type': backend_type,
                'status': BackendStatus.ERROR.value,
                'last_health_check': self._last_health_check.get(backend_type, 0),
                'backend_info': {},
                'is_active': False,
                'error': str(e)
            }


# Global factory instance
_factory_instance: Optional[LLMFactory] = None


def get_llm_factory() -> LLMFactory:
    """
    Get the global LLM factory instance (singleton pattern).
    
    Returns:
        LLMFactory: Global factory instance
    """
    global _factory_instance
    if _factory_instance is None:
        _factory_instance = LLMFactory()
    return _factory_instance


def get_active_backend() -> LLMInterface:
    """
    Convenience function to get the currently active backend.
    
    Returns:
        LLMInterface: Active backend instance
    """
    factory = get_llm_factory()
    return factory.get_backend()