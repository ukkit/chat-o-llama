"""
Abstract base class for LLM backends in chat-o-llama.

This module defines the interface that all LLM backends must implement,
ensuring consistent behavior across different model providers (Ollama, llama.cpp, etc.).
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass
from enum import Enum
import time
import logging

logger = logging.getLogger(__name__)


class BackendType(Enum):
    """Enumeration of supported backend types."""
    OLLAMA = "ollama"
    LLAMA_CPP = "llama_cpp"
    UNKNOWN = "unknown"


class BackendStatus(Enum):
    """Enumeration of backend health status."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    TIMEOUT = "timeout"
    UNREACHABLE = "unreachable"


@dataclass
class BackendHealth:
    """Backend health information."""
    status: BackendStatus
    response_time_ms: Optional[int] = None
    error_message: Optional[str] = None
    last_checked: Optional[float] = None
    models_available: int = 0
    
    @property
    def is_healthy(self) -> bool:
        """Check if backend is in a healthy state."""
        return self.status == BackendStatus.HEALTHY


@dataclass  
class ModelInfo:
    """Information about a model available in a backend."""
    name: str
    backend_type: BackendType
    backend_id: str
    size_bytes: Optional[int] = None
    modified_time: Optional[str] = None
    digest: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    
    @property
    def display_name(self) -> str:
        """Get display name with backend identifier."""
        return f"{self.name} ({self.backend_type.value})"


@dataclass
class GenerationResponse:
    """Normalized response from model generation."""
    content: str
    model: str
    backend_type: BackendType
    backend_id: str
    
    # Performance metrics
    response_time_ms: int
    estimated_tokens: int
    
    # Optional detailed metrics (if available from backend)
    actual_tokens: Optional[int] = None
    tokens_per_second: Optional[float] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    
    # Raw backend response for debugging
    raw_response: Optional[Dict[str, Any]] = None
    
    @property
    def tokens_per_second_calculated(self) -> Optional[float]:
        """Calculate tokens per second from available data."""
        tokens = self.actual_tokens or self.estimated_tokens
        if tokens and self.response_time_ms:
            return tokens / (self.response_time_ms / 1000.0)
        return None


class LLMBackend(ABC):
    """
    Abstract base class for LLM backends.
    
    All backend implementations must inherit from this class and implement
    the required abstract methods. This ensures consistent behavior and
    makes it easy to add new backend types.
    
    Attributes:
        backend_id: Unique identifier for this backend instance
        backend_type: Type of backend (ollama, llama_cpp, etc.)
        config: Configuration dictionary for this backend
        base_url: Base URL for the backend API
    """
    
    def __init__(self, backend_id: str, config: Dict[str, Any]):
        """
        Initialize the backend.
        
        Args:
            backend_id: Unique identifier for this backend instance
            config: Configuration dictionary containing backend-specific settings
        """
        self.backend_id = backend_id
        self.config = config
        self.base_url = config.get('url', 'http://localhost:11434')
        self.timeout = config.get('timeout', 180)
        self.connect_timeout = config.get('connect_timeout', 15)
        
        # Health tracking
        self._last_health_check: Optional[float] = None
        self._cached_health: Optional[BackendHealth] = None
        self._health_cache_ttl = 30  # seconds
        
        logger.info(f"Initialized {self.backend_type.value} backend: {backend_id}")
    
    @property
    @abstractmethod
    def backend_type(self) -> BackendType:
        """Get the type of this backend."""
        pass
    
    @abstractmethod
    async def get_models(self) -> List[ModelInfo]:
        """
        Get list of available models from this backend.
        
        Returns:
            List of ModelInfo objects representing available models
            
        Raises:
            BackendError: If unable to retrieve models
        """
        pass
    
    @abstractmethod
    async def generate_response(
        self,
        model: str,
        prompt: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ) -> GenerationResponse:
        """
        Generate a response from the specified model.
        
        Args:
            model: Name of the model to use
            prompt: Input prompt for generation
            conversation_history: Previous messages in conversation
            **kwargs: Additional generation parameters
            
        Returns:
            GenerationResponse object with normalized response data
            
        Raises:
            BackendError: If generation fails
        """
        pass
    
    @abstractmethod
    async def is_available(self) -> bool:
        """
        Check if the backend is available and responsive.
        
        Returns:
            True if backend is available, False otherwise
        """
        pass
    
    async def get_health(self, force_check: bool = False) -> BackendHealth:
        """
        Get health status of the backend with caching.
        
        Args:
            force_check: If True, skip cache and perform fresh health check
            
        Returns:
            BackendHealth object with current health status
        """
        now = time.time()
        
        # Return cached health if valid and not forcing check
        if (not force_check and 
            self._cached_health and 
            self._last_health_check and
            (now - self._last_health_check) < self._health_cache_ttl):
            return self._cached_health
        
        # Perform health check
        start_time = time.time()
        try:
            is_healthy = await self.is_available()
            response_time_ms = int((time.time() - start_time) * 1000)
            
            if is_healthy:
                # Try to get model count
                models_count = 0
                try:
                    models = await self.get_models()
                    models_count = len(models)
                except Exception:
                    # Don't fail health check just because models can't be retrieved
                    pass
                
                health = BackendHealth(
                    status=BackendStatus.HEALTHY,
                    response_time_ms=response_time_ms,
                    last_checked=now,
                    models_available=models_count
                )
            else:
                health = BackendHealth(
                    status=BackendStatus.UNHEALTHY,
                    response_time_ms=response_time_ms,
                    last_checked=now,
                    error_message="Backend is not responsive"
                )
                
        except Exception as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Health check failed for {self.backend_id}: {e}")
            
            health = BackendHealth(
                status=BackendStatus.UNREACHABLE,
                response_time_ms=response_time_ms,
                last_checked=now,
                error_message=str(e)
            )
        
        # Cache the result
        self._cached_health = health
        self._last_health_check = now
        
        return health
    
    def get_info(self) -> Dict[str, Any]:
        """
        Get basic information about this backend.
        
        Returns:
            Dictionary with backend information
        """
        return {
            'backend_id': self.backend_id,
            'backend_type': self.backend_type.value,
            'base_url': self.base_url,
            'timeout': self.timeout,
            'connect_timeout': self.connect_timeout
        }
    
    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for given text.
        
        This is a rough estimation used as fallback when actual
        token counts are not available from the backend.
        
        Args:
            text: Text to estimate tokens for
            
        Returns:
            Estimated number of tokens
        """
        # Rough estimation: ~4 characters per token for English text
        return max(1, len(text) // 4)
    
    def __str__(self) -> str:
        """String representation of the backend."""
        return f"{self.backend_type.value}:{self.backend_id}"
    
    def __repr__(self) -> str:
        """Detailed string representation."""
        return f"<{self.__class__.__name__}(id='{self.backend_id}', url='{self.base_url}')>"


class BackendError(Exception):
    """Base exception for backend-related errors."""
    
    def __init__(self, message: str, backend_id: str = None, cause: Exception = None):
        self.backend_id = backend_id
        self.cause = cause
        super().__init__(message)


class BackendTimeoutError(BackendError):
    """Exception raised when backend operations timeout."""
    pass


class BackendConnectionError(BackendError):
    """Exception raised when unable to connect to backend."""
    pass


class ModelNotFoundError(BackendError):
    """Exception raised when requested model is not available."""
    pass
