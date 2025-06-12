"""
Backend package for chat-o-llama.

This package provides a unified interface for different LLM backends,
including Ollama and llama.cpp servers.

Example usage:
    from backends import BackendManager
    
    config = {
        'backends': {
            'ollama': {
                'type': 'ollama',
                'url': 'http://localhost:11434',
                'enabled': True
            }
        }
    }
    
    manager = BackendManager(config)
    await manager.initialize()
    models = await manager.get_all_models()
"""

from .base import (
    LLMBackend,
    BackendType,
    BackendStatus,
    BackendHealth,
    ModelInfo,
    GenerationResponse,
    BackendError,
    BackendTimeoutError,
    BackendConnectionError,
    ModelNotFoundError
)

from .ollama import OllamaBackend, OllamaAPI
from .llama_cpp import LlamaCppBackend
from .manager import BackendManager, BackendManagerSync
from .models import (
    ConversationMessage,
    GenerationMetrics,
    ResponseNormalizer,
    ConfigValidator
)

__version__ = "1.0.0"

__all__ = [
    # Base classes and types
    'LLMBackend',
    'BackendType',
    'BackendStatus', 
    'BackendHealth',
    'ModelInfo',
    'GenerationResponse',
    
    # Exceptions
    'BackendError',
    'BackendTimeoutError',
    'BackendConnectionError',
    'ModelNotFoundError',
    
    # Backend implementations
    'OllamaBackend',
    'LlamaCppBackend',
    'OllamaAPI',  # For backward compatibility
    
    # Manager classes
    'BackendManager',
    'BackendManagerSync',
    
    # Utility classes
    'ConversationMessage',
    'GenerationMetrics',
    'ResponseNormalizer',
    'ConfigValidator',
]

# Package metadata
__author__ = "chat-o-llama developers"
__description__ = "Backend abstraction layer for chat-o-llama"
