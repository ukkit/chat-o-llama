"""
Response models and utilities for backend normalization.

This module contains shared data models and utility functions used
by all backend implementations to ensure consistent response formats.
"""

from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class ConversationMessage:
    """Represents a single message in a conversation."""
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: Optional[datetime] = None
    model: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        result = {
            'role': self.role,
            'content': self.content
        }
        if self.timestamp:
            result['timestamp'] = self.timestamp.isoformat()
        if self.model:
            result['model'] = self.model
        if self.metadata:
            result['metadata'] = self.metadata
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationMessage':
        """Create from dictionary format."""
        timestamp = None
        if 'timestamp' in data:
            timestamp = datetime.fromisoformat(data['timestamp'])
        
        return cls(
            role=data['role'],
            content=data['content'],
            timestamp=timestamp,
            model=data.get('model'),
            metadata=data.get('metadata')
        )


@dataclass
class GenerationMetrics:
    """Detailed metrics for response generation."""
    # Timing metrics (all in milliseconds)
    total_time_ms: int
    prompt_eval_time_ms: Optional[int] = None
    generation_time_ms: Optional[int] = None
    load_time_ms: Optional[int] = None
    
    # Token metrics
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    
    # Performance metrics
    tokens_per_second: Optional[float] = None
    prompt_tokens_per_second: Optional[float] = None
    
    # Backend-specific metrics
    backend_metrics: Dict[str, Any] = field(default_factory=dict)
    
    def calculate_derived_metrics(self):
        """Calculate derived metrics from available data."""
        # Calculate total tokens if components available
        if self.prompt_tokens and self.completion_tokens and not self.total_tokens:
            self.total_tokens = self.prompt_tokens + self.completion_tokens
        
        # Calculate tokens per second if not provided
        if not self.tokens_per_second and self.completion_tokens and self.generation_time_ms:
            self.tokens_per_second = self.completion_tokens / (self.generation_time_ms / 1000.0)
        
        # Calculate prompt tokens per second
        if not self.prompt_tokens_per_second and self.prompt_tokens and self.prompt_eval_time_ms:
            self.prompt_tokens_per_second = self.prompt_tokens / (self.prompt_eval_time_ms / 1000.0)


class ResponseNormalizer:
    """Utility class for normalizing responses from different backends."""
    
    @staticmethod
    def normalize_ollama_response(
        response_data: Dict[str, Any],
        model: str,
        backend_id: str,
        start_time_ms: int
    ) -> 'GenerationResponse':
        """
        Normalize Ollama API response to standard format.
        
        Args:
            response_data: Raw response from Ollama API
            model: Model name used for generation
            backend_id: ID of the backend instance
            start_time_ms: Timestamp when request started
            
        Returns:
            Normalized GenerationResponse object
        """
        from .base import GenerationResponse, BackendType
        
        # Extract response content
        content = response_data.get('response', '')
        
        # Calculate timing
        current_time_ms = int(time.time() * 1000)
        response_time_ms = current_time_ms - start_time_ms
        
        # Extract token information
        eval_count = response_data.get('eval_count')
        prompt_eval_count = response_data.get('prompt_eval_count')
        
        # Build metrics
        metrics = GenerationMetrics(
            total_time_ms=response_time_ms,
            prompt_eval_time_ms=ResponseNormalizer._nanoseconds_to_ms(
                response_data.get('prompt_eval_duration')
            ),
            generation_time_ms=ResponseNormalizer._nanoseconds_to_ms(
                response_data.get('eval_duration')
            ),
            load_time_ms=ResponseNormalizer._nanoseconds_to_ms(
                response_data.get('load_duration')
            ),
            prompt_tokens=prompt_eval_count,
            completion_tokens=eval_count,
            backend_metrics={
                'total_duration': response_data.get('total_duration'),
                'context_length': response_data.get('context', 0)
            }
        )
        
        metrics.calculate_derived_metrics()
        
        # Estimate tokens if not available
        estimated_tokens = eval_count or len(content) // 4
        
        return GenerationResponse(
            content=content,
            model=model,
            backend_type=BackendType.OLLAMA,
            backend_id=backend_id,
            response_time_ms=response_time_ms,
            estimated_tokens=estimated_tokens,
            actual_tokens=eval_count,
            tokens_per_second=metrics.tokens_per_second,
            prompt_tokens=prompt_eval_count,
            completion_tokens=eval_count,
            raw_response=response_data
        )
    
    @staticmethod
    def normalize_llamacpp_response(
        response_data: Dict[str, Any],
        model: str,
        backend_id: str,
        start_time_ms: int
    ) -> 'GenerationResponse':
        """
        Normalize llama.cpp OpenAI-compatible response to standard format.
        
        Args:
            response_data: Raw response from llama.cpp API
            model: Model name used for generation
            backend_id: ID of the backend instance
            start_time_ms: Timestamp when request started
            
        Returns:
            Normalized GenerationResponse object
        """
        from .base import GenerationResponse, BackendType
        
        # Calculate timing
        current_time_ms = int(time.time() * 1000)
        response_time_ms = current_time_ms - start_time_ms
        
        # Extract content from OpenAI format
        content = ""
        prompt_tokens = None
        completion_tokens = None
        
        if 'choices' in response_data and response_data['choices']:
            choice = response_data['choices'][0]
            if 'text' in choice:
                content = choice['text']
            elif 'message' in choice and 'content' in choice['message']:
                content = choice['message']['content']
        
        # Extract token usage
        usage = response_data.get('usage', {})
        prompt_tokens = usage.get('prompt_tokens')
        completion_tokens = usage.get('completion_tokens')
        total_tokens = usage.get('total_tokens')
        
        # Build metrics
        metrics = GenerationMetrics(
            total_time_ms=response_time_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            backend_metrics=response_data.get('usage', {})
        )
        
        metrics.calculate_derived_metrics()
        
        # Estimate tokens if not available
        estimated_tokens = completion_tokens or len(content) // 4
        
        return GenerationResponse(
            content=content,
            model=model,
            backend_type=BackendType.LLAMA_CPP,
            backend_id=backend_id,
            response_time_ms=response_time_ms,
            estimated_tokens=estimated_tokens,
            actual_tokens=completion_tokens,
            tokens_per_second=metrics.tokens_per_second,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            raw_response=response_data
        )
    
    @staticmethod
    def _nanoseconds_to_ms(nanoseconds: Optional[int]) -> Optional[int]:
        """Convert nanoseconds to milliseconds."""
        if nanoseconds is None:
            return None
        return int(nanoseconds / 1_000_000)


class ConfigValidator:
    """Utility class for validating backend configurations."""
    
    @staticmethod
    def validate_ollama_config(config: Dict[str, Any]) -> Dict[str, str]:
        """
        Validate Ollama backend configuration.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Dictionary of validation errors (empty if valid)
        """
        errors = {}
        
        # Check required fields
        if 'url' not in config:
            errors['url'] = "URL is required for Ollama backend"
        
        # Validate URL format
        url = config.get('url', '')
        if url and not (url.startswith('http://') or url.startswith('https://')):
            errors['url'] = "URL must start with http:// or https://"
        
        # Validate timeout values
        timeout = config.get('timeout')
        if timeout is not None and (not isinstance(timeout, (int, float)) or timeout <= 0):
            errors['timeout'] = "Timeout must be a positive number"
        
        connect_timeout = config.get('connect_timeout')
        if connect_timeout is not None and (not isinstance(connect_timeout, (int, float)) or connect_timeout <= 0):
            errors['connect_timeout'] = "Connect timeout must be a positive number"
        
        return errors
    
    @staticmethod
    def validate_llamacpp_config(config: Dict[str, Any]) -> Dict[str, str]:
        """
        Validate llama.cpp backend configuration.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Dictionary of validation errors (empty if valid)
        """
        errors = {}
        
        # Check required fields
        if 'url' not in config:
            errors['url'] = "URL is required for llama.cpp backend"
        
        # Validate URL format
        url = config.get('url', '')
        if url and not (url.startswith('http://') or url.startswith('https://')):
            errors['url'] = "URL must start with http:// or https://"
        
        # Validate timeout values
        timeout = config.get('timeout')
        if timeout is not None and (not isinstance(timeout, (int, float)) or timeout <= 0):
            errors['timeout'] = "Timeout must be a positive number"
        
        connect_timeout = config.get('connect_timeout')
        if connect_timeout is not None and (not isinstance(connect_timeout, (int, float)) or connect_timeout <= 0):
            errors['connect_timeout'] = "Connect timeout must be a positive number"
        
        # Validate API key if provided
        api_key = config.get('api_key')
        if api_key is not None and not isinstance(api_key, str):
            errors['api_key'] = "API key must be a string"
        
        return errors


# Import time at module level for use in functions
import time
