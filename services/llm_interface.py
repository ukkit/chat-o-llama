"""Abstract base class for LLM backend implementations."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union


class LLMInterface(ABC):
    """
    Abstract base class for LLM backend implementations.
    
    This interface defines the common methods that all LLM backends must implement
    to ensure consistency across different backend implementations (Ollama, llama.cpp, etc.).
    
    Standard Response Format:
    All generate_response() implementations must return a dictionary with these keys:
    - response (str): The generated text response
    - response_time_ms (int): Response time in milliseconds
    - estimated_tokens (int): Estimated number of tokens in response
    - backend_type (str): Backend identifier ('ollama', 'llamacpp', etc.)
    - model (str): Model name used for generation
    
    Optional keys may include backend-specific metrics.
    """

    @abstractmethod
    def get_models(self) -> List[str]:
        """
        Get list of available models from the backend.
        
        Returns:
            List[str]: List of available model names. Empty list if none available
                      or if backend is unreachable.
        
        Example:
            >>> backend = SomeBackend()
            >>> models = backend.get_models()
            >>> print(models)
            ['llama2:7b', 'mistral:7b', 'codellama:13b']
        """
        pass

    @abstractmethod
    def generate_response(
        self,
        model: str,
        prompt: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate a response using the specified model and prompt.
        
        Args:
            model (str): Name of the model to use for generation
            prompt (str): Input prompt for the model
            conversation_history (Optional[List[Dict]]): Previous conversation context.
                Each dict should have 'role' and 'content' keys.
            **kwargs: Additional backend-specific parameters
        
        Returns:
            Dict[str, Any]: Response dictionary containing at minimum:
                - response (str): Generated text
                - response_time_ms (int): Time taken in milliseconds
                - estimated_tokens (int): Token count estimate
                - backend_type (str): Backend identifier
                - model (str): Model name used
        
        Example:
            >>> backend = SomeBackend()
            >>> history = [{"role": "user", "content": "Hello"}]
            >>> result = backend.generate_response(
            ...     model="llama2:7b",
            ...     prompt="How are you?",
            ...     conversation_history=history
            ... )
            >>> print(result['response'])
            "I'm doing well, thank you for asking!"
        """
        pass

    @abstractmethod
    def get_backend_info(self) -> Dict[str, Any]:
        """
        Get information about the backend implementation.
        
        Returns:
            Dict[str, Any]: Backend information including:
                - backend_type (str): Backend identifier
                - version (str): Backend version if available
                - status (str): Current status ('available', 'unavailable', 'error')
                - capabilities (List[str]): List of supported features
                - health_check (bool): Whether backend is healthy/reachable
        
        Example:
            >>> backend = SomeBackend()
            >>> info = backend.get_backend_info()
            >>> print(info)
            {
                'backend_type': 'ollama',
                'version': '0.1.17',
                'status': 'available',
                'capabilities': ['streaming', 'embeddings'],
                'health_check': True
            }
        """
        pass

    def validate_model(self, model: str) -> bool:
        """
        Validate if a model is available in this backend.
        
        Args:
            model (str): Model name to validate
            
        Returns:
            bool: True if model is available, False otherwise
        """
        available_models = self.get_models()
        return model in available_models

    def get_standard_error_response(
        self,
        error_message: str,
        response_time_ms: int = 0,
        model: str = "unknown"
    ) -> Dict[str, Any]:
        """
        Generate a standardized error response.
        
        Args:
            error_message (str): Error description
            response_time_ms (int): Time taken before error occurred
            model (str): Model name that was being used
            
        Returns:
            Dict[str, Any]: Standardized error response
        """
        return {
            'response': f"Error: {error_message}",
            'response_time_ms': response_time_ms,
            'estimated_tokens': 0,
            'backend_type': self.get_backend_info().get('backend_type', 'unknown'),
            'model': model,
            'error': True
        }

    def cleanup(self):
        """
        Clean up any active resources, requests, or threads.
        
        This method should be implemented by backends that need to perform
        cleanup operations, such as cancelling active requests, closing
        connections, or releasing resources.
        
        Default implementation does nothing.
        """
        pass