"""
Fixed comprehensive test suite for backend abstraction layer.

This module contains unit tests and integration tests for all backend
implementations, the backend manager, and response normalization.
"""

import pytest
import asyncio
import json
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, List

# Import the modules we're testing
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backends.base import (
    BackendType, BackendStatus, BackendHealth, ModelInfo, GenerationResponse,
    LLMBackend, BackendError, BackendTimeoutError, BackendConnectionError, ModelNotFoundError
)
from backends.ollama import OllamaBackend, OllamaAPI
from backends.llama_cpp import LlamaCppBackend
from backends.manager import BackendManager, BackendManagerSync
from backends.models import ResponseNormalizer, ConfigValidator, ConversationMessage


class TestBackendBase:
    """Test cases for base backend functionality."""
    
    def test_backend_types(self):
        """Test backend type enumeration."""
        assert BackendType.OLLAMA.value == "ollama"
        assert BackendType.LLAMA_CPP.value == "llama_cpp"
        assert BackendType.UNKNOWN.value == "unknown"
    
    def test_backend_status(self):
        """Test backend status enumeration."""
        assert BackendStatus.HEALTHY.value == "healthy"
        assert BackendStatus.UNHEALTHY.value == "unhealthy"
        assert BackendStatus.TIMEOUT.value == "timeout"
        assert BackendStatus.UNREACHABLE.value == "unreachable"
    
    def test_backend_health(self):
        """Test backend health dataclass."""
        health = BackendHealth(
            status=BackendStatus.HEALTHY,
            response_time_ms=100,
            models_available=5
        )
        
        assert health.is_healthy is True
        assert health.response_time_ms == 100
        assert health.models_available == 5
        
        unhealthy = BackendHealth(status=BackendStatus.UNHEALTHY)
        assert unhealthy.is_healthy is False
    
    def test_model_info(self):
        """Test model info dataclass."""
        model = ModelInfo(
            name="test-model",
            backend_type=BackendType.OLLAMA,
            backend_id="test-backend",
            size_bytes=1000000
        )
        
        assert model.display_name == "test-model (ollama)"
        assert model.name == "test-model"
        assert model.backend_type == BackendType.OLLAMA
    
    def test_generation_response(self):
        """Test generation response dataclass."""
        response = GenerationResponse(
            content="Test response",
            model="test-model",
            backend_type=BackendType.OLLAMA,
            backend_id="test-backend",
            response_time_ms=1500,
            estimated_tokens=100,
            actual_tokens=95
        )
        
        assert response.content == "Test response"
        assert response.tokens_per_second_calculated == 95 / 1.5
        assert response.response_time_ms == 1500


class TestConfigValidator:
    """Test cases for configuration validation."""
    
    def test_valid_ollama_config(self):
        """Test validation of valid Ollama configuration."""
        config = {
            'url': 'http://localhost:11434',
            'timeout': 180,
            'connect_timeout': 15
        }
        
        errors = ConfigValidator.validate_ollama_config(config)
        assert len(errors) == 0
    
    def test_invalid_ollama_config(self):
        """Test validation of invalid Ollama configuration."""
        config = {
            'url': 'invalid-url',
            'timeout': -1,
            'connect_timeout': 'not-a-number'
        }
        
        errors = ConfigValidator.validate_ollama_config(config)
        assert 'url' in errors
        assert 'timeout' in errors
        assert 'connect_timeout' in errors
    
    def test_valid_llamacpp_config(self):
        """Test validation of valid llama.cpp configuration."""
        config = {
            'url': 'http://localhost:8080',
            'timeout': 180,
            'api_key': 'test-key'
        }
        
        errors = ConfigValidator.validate_llamacpp_config(config)
        assert len(errors) == 0
    
    def test_missing_url_config(self):
        """Test validation with missing URL."""
        config = {'timeout': 180}
        
        ollama_errors = ConfigValidator.validate_ollama_config(config)
        llamacpp_errors = ConfigValidator.validate_llamacpp_config(config)
        
        assert 'url' in ollama_errors
        assert 'url' in llamacpp_errors


class TestResponseNormalizer:
    """Test cases for response normalization."""
    
    def test_normalize_ollama_response(self):
        """Test normalization of Ollama API response."""
        raw_response = {
            'response': 'Hello, world!',
            'eval_count': 50,
            'prompt_eval_count': 20,
            'eval_duration': 1500000000,  # 1.5 seconds in nanoseconds
            'prompt_eval_duration': 500000000,  # 0.5 seconds in nanoseconds
            'load_duration': 100000000,  # 0.1 seconds in nanoseconds
            'total_duration': 2100000000  # 2.1 seconds in nanoseconds
        }
        
        start_time_ms = int(time.time() * 1000) - 2000  # 2 seconds ago
        
        response = ResponseNormalizer.normalize_ollama_response(
            raw_response, 'test-model', 'test-backend', start_time_ms
        )
        
        assert response.content == 'Hello, world!'
        assert response.model == 'test-model'
        assert response.backend_type == BackendType.OLLAMA
        assert response.backend_id == 'test-backend'
        assert response.actual_tokens == 50
        assert response.prompt_tokens == 20
        assert response.raw_response == raw_response
    
    def test_normalize_llamacpp_response(self):
        """Test normalization of llama.cpp API response."""
        raw_response = {
            'choices': [{
                'message': {
                    'content': 'Hello from llama.cpp!'
                }
            }],
            'usage': {
                'prompt_tokens': 15,
                'completion_tokens': 25,
                'total_tokens': 40
            }
        }
        
        start_time_ms = int(time.time() * 1000) - 1000  # 1 second ago
        
        response = ResponseNormalizer.normalize_llamacpp_response(
            raw_response, 'test-model', 'test-backend', start_time_ms
        )
        
        assert response.content == 'Hello from llama.cpp!'
        assert response.model == 'test-model'
        assert response.backend_type == BackendType.LLAMA_CPP
        assert response.backend_id == 'test-backend'
        assert response.actual_tokens == 25
        assert response.prompt_tokens == 15


class MockAsyncContextManager:
    """Helper class for mocking async context managers."""
    
    def __init__(self, mock_response):
        self.mock_response = mock_response
    
    async def __aenter__(self):
        return self.mock_response
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return False


class TestOllamaBackend:
    """Test cases for Ollama backend implementation."""
    
    @pytest.fixture
    def ollama_config(self):
        """Test configuration for Ollama backend."""
        return {
            'url': 'http://localhost:11434',
            'timeout': 180,
            'connect_timeout': 15,
            'system_prompt': 'You are a helpful assistant.',
            'model_options': {
                'temperature': 0.7,
                'top_p': 0.9
            }
        }
    
    @pytest.fixture
    def ollama_backend(self, ollama_config):
        """Create Ollama backend instance for testing."""
        return OllamaBackend('test-ollama', ollama_config)
    
    def test_ollama_backend_init(self, ollama_backend):
        """Test Ollama backend initialization."""
        assert ollama_backend.backend_id == 'test-ollama'
        assert ollama_backend.backend_type == BackendType.OLLAMA
        assert ollama_backend.api_url == 'http://localhost:11434/api'
    
    @pytest.mark.asyncio
    async def test_ollama_get_models_success(self, ollama_backend):
        """Test successful model retrieval from Ollama."""
        mock_response_data = {
            'models': [
                {
                    'name': 'llama3.2:1b',
                    'size': 1000000,
                    'modified_at': '2024-01-01T00:00:00Z',
                    'digest': 'abc123',
                    'details': {'family': 'llama'}
                },
                {
                    'name': 'phi3:mini',
                    'size': 2000000,
                    'modified_at': '2024-01-01T00:00:00Z'
                }
            ]
        }
        
        # Create mock response
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_response_data)
        
        # Create mock session
        mock_session = Mock()
        mock_session.get = Mock(return_value=MockAsyncContextManager(mock_response))
        
        with patch.object(ollama_backend, '_get_session') as mock_get_session:
            mock_get_session.return_value = mock_session
            
            models = await ollama_backend.get_models()
            
            assert len(models) == 2
            assert models[0].name == 'llama3.2:1b'
            assert models[0].backend_type == BackendType.OLLAMA
            assert models[0].backend_id == 'test-ollama'
            assert models[0].size_bytes == 1000000
            assert models[1].name == 'phi3:mini'
    
    @pytest.mark.asyncio
    async def test_ollama_get_models_error(self, ollama_backend):
        """Test error handling in model retrieval."""
        mock_response = Mock()
        mock_response.status = 500
        mock_response.text = AsyncMock(return_value="Internal Server Error")
        
        mock_session = Mock()
        mock_session.get = Mock(return_value=MockAsyncContextManager(mock_response))
        
        with patch.object(ollama_backend, '_get_session') as mock_get_session:
            mock_get_session.return_value = mock_session
            
            with pytest.raises(BackendError) as exc_info:
                await ollama_backend.get_models()
            
            assert "HTTP 500" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_ollama_generate_response_success(self, ollama_backend):
        """Test successful response generation."""
        mock_response_data = {
            'response': 'Hello! How can I help you today?',
            'eval_count': 30,
            'prompt_eval_count': 10,
            'eval_duration': 1000000000,  # 1 second in nanoseconds
            'prompt_eval_duration': 200000000  # 0.2 seconds in nanoseconds
        }
        
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_response_data)
        
        mock_session = Mock()
        mock_session.post = Mock(return_value=MockAsyncContextManager(mock_response))
        
        with patch.object(ollama_backend, '_get_session') as mock_get_session:
            mock_get_session.return_value = mock_session
            
            response = await ollama_backend.generate_response(
                'test-model', 'Hello!', []
            )
            
            assert response.content == 'Hello! How can I help you today?'
            assert response.model == 'test-model'
            assert response.backend_type == BackendType.OLLAMA
            assert response.actual_tokens == 30
            assert response.prompt_tokens == 10
    
    @pytest.mark.asyncio
    async def test_ollama_generate_response_model_not_found(self, ollama_backend):
        """Test model not found error."""
        mock_response = Mock()
        mock_response.status = 404
        mock_response.text = AsyncMock(return_value="Model not found")
        
        mock_session = Mock()
        mock_session.post = Mock(return_value=MockAsyncContextManager(mock_response))
        
        with patch.object(ollama_backend, '_get_session') as mock_get_session:
            mock_get_session.return_value = mock_session
            
            with pytest.raises(ModelNotFoundError) as exc_info:
                await ollama_backend.generate_response('nonexistent-model', 'Hello!', [])
            
            assert "not found" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_ollama_is_available_success(self, ollama_backend):
        """Test availability check success."""
        mock_response = Mock()
        mock_response.status = 200
        
        mock_session = Mock()
        mock_session.get = Mock(return_value=MockAsyncContextManager(mock_response))
        
        with patch.object(ollama_backend, '_get_session') as mock_get_session:
            mock_get_session.return_value = mock_session
            
            is_available = await ollama_backend.is_available()
            assert is_available is True
    
    @pytest.mark.asyncio
    async def test_ollama_is_available_failure(self, ollama_backend):
        """Test availability check failure."""
        with patch.object(ollama_backend, '_get_session', side_effect=Exception("Connection failed")):
            is_available = await ollama_backend.is_available()
            assert is_available is False


class TestLlamaCppBackend:
    """Test cases for llama.cpp backend implementation."""
    
    @pytest.fixture
    def llamacpp_config(self):
        """Test configuration for llama.cpp backend."""
        return {
            'url': 'http://localhost:8080',
            'timeout': 180,
            'connect_timeout': 15,
            'api_key': 'test-api-key',
            'system_prompt': 'You are a helpful assistant.',
            'model_options': {
                'temperature': 0.7,
                'max_tokens': 1000
            }
        }
    
    @pytest.fixture
    def llamacpp_backend(self, llamacpp_config):
        """Create llama.cpp backend instance for testing."""
        return LlamaCppBackend('test-llamacpp', llamacpp_config)
    
    def test_llamacpp_backend_init(self, llamacpp_backend):
        """Test llama.cpp backend initialization."""
        assert llamacpp_backend.backend_id == 'test-llamacpp'
        assert llamacpp_backend.backend_type == BackendType.LLAMA_CPP
        assert llamacpp_backend.api_url == 'http://localhost:8080/v1'
        assert llamacpp_backend.api_key == 'test-api-key'
    
    @pytest.mark.asyncio
    async def test_llamacpp_get_models_success(self, llamacpp_backend):
        """Test successful model retrieval from llama.cpp."""
        mock_response_data = {
            'data': [
                {
                    'id': 'gpt-3.5-turbo',
                    'object': 'model',
                    'created': 1677610602,
                    'owned_by': 'openai'
                },
                {
                    'id': 'llama-2-7b',
                    'object': 'model',
                    'created': 1677610602,
                    'owned_by': 'meta'
                }
            ]
        }
        
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_response_data)
        
        mock_session = Mock()
        mock_session.get = Mock(return_value=MockAsyncContextManager(mock_response))
        
        with patch.object(llamacpp_backend, '_get_session') as mock_get_session:
            mock_get_session.return_value = mock_session
            
            models = await llamacpp_backend.get_models()
            
            assert len(models) == 2
            assert models[0].name == 'gpt-3.5-turbo'
            assert models[0].backend_type == BackendType.LLAMA_CPP
            assert models[0].backend_id == 'test-llamacpp'
            assert models[1].name == 'llama-2-7b'
    
    @pytest.mark.asyncio
    async def test_llamacpp_generate_response_success(self, llamacpp_backend):
        """Test successful response generation."""
        mock_response_data = {
            'choices': [{
                'message': {
                    'content': 'Hello! How can I assist you today?'
                }
            }],
            'usage': {
                'prompt_tokens': 8,
                'completion_tokens': 12,
                'total_tokens': 20
            }
        }
        
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_response_data)
        
        mock_session = Mock()
        mock_session.post = Mock(return_value=MockAsyncContextManager(mock_response))
        
        with patch.object(llamacpp_backend, '_get_session') as mock_get_session:
            mock_get_session.return_value = mock_session
            
            response = await llamacpp_backend.generate_response(
                'test-model', 'Hello!', []
            )
            
            assert response.content == 'Hello! How can I assist you today?'
            assert response.model == 'test-model'
            assert response.backend_type == BackendType.LLAMA_CPP
            assert response.actual_tokens == 12
            assert response.prompt_tokens == 8
    
    @pytest.mark.asyncio
    async def test_llamacpp_build_messages(self, llamacpp_backend):
        """Test message building for OpenAI format."""
        conversation_history = [
            {'role': 'user', 'content': 'Hi there!'},
            {'role': 'assistant', 'content': 'Hello! How can I help?'},
            {'role': 'user', 'content': 'What is AI?'}
        ]
        
        messages = llamacpp_backend._build_messages(conversation_history, 'Tell me more')
        
        # Should include system prompt + history + current prompt
        assert len(messages) >= 4  # system + 3 history + current
        assert messages[0]['role'] == 'system'
        assert messages[0]['content'] == 'You are a helpful assistant.'
        assert messages[-1]['role'] == 'user'
        assert messages[-1]['content'] == 'Tell me more'


class TestBackendManager:
    """Test cases for backend manager."""
    
    @pytest.fixture
    def manager_config(self):
        """Test configuration for backend manager."""
        return {
            'backends': {
                'ollama': {
                    'type': 'ollama',
                    'url': 'http://localhost:11434',
                    'enabled': True,
                    'timeout': 180
                },
                'llamacpp': {
                    'type': 'llama_cpp',
                    'url': 'http://localhost:8080',
                    'enabled': True,
                    'timeout': 180,
                    'api_key': 'test-key'
                },
                'disabled': {
                    'type': 'ollama',
                    'url': 'http://localhost:11435',
                    'enabled': False
                }
            }
        }
    
    @pytest.fixture
    def backend_manager(self, manager_config):
        """Create backend manager instance for testing."""
        return BackendManager(manager_config)
    
    @pytest.mark.asyncio
    async def test_manager_initialization(self, backend_manager):
        """Test backend manager initialization."""
        with patch('backends.manager.OllamaBackend') as mock_ollama, \
             patch('backends.manager.LlamaCppBackend') as mock_llamacpp:
            
            # Mock backend instances
            mock_ollama_instance = Mock()
            mock_ollama_instance.get_health = AsyncMock(return_value=BackendHealth(BackendStatus.HEALTHY))
            mock_ollama.return_value = mock_ollama_instance
            
            mock_llamacpp_instance = Mock()
            mock_llamacpp_instance.get_health = AsyncMock(return_value=BackendHealth(BackendStatus.HEALTHY))
            mock_llamacpp.return_value = mock_llamacpp_instance
            
            await backend_manager.initialize()
            
            # Should initialize 2 backends (disabled one should be skipped)
            assert len(backend_manager.backends) == 2
            assert 'ollama' in backend_manager.backends
            assert 'llamacpp' in backend_manager.backends
            assert 'disabled' not in backend_manager.backends


class TestBackwardCompatibility:
    """Test cases for backward compatibility wrappers."""
    
    def test_ollama_api_wrapper(self):
        """Test OllamaAPI synchronous wrapper."""
        config = {
            'url': 'http://localhost:11434',
            'timeout': 180
        }
        
        api = OllamaAPI(config)
        assert api.config == config
        assert api.backend.backend_id == 'ollama-default'
    
    def test_backend_manager_sync_wrapper(self):
        """Test BackendManagerSync wrapper."""
        config = {
            'backends': {
                'ollama': {
                    'type': 'ollama',
                    'url': 'http://localhost:11434',
                    'enabled': True
                }
            }
        }
        
        manager = BackendManagerSync(config)
        assert manager.config == config
        assert isinstance(manager.manager, BackendManager)


@pytest.mark.integration
class TestIntegration:
    """Integration tests for the complete backend system."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self):
        """Test complete workflow from manager initialization to response generation."""
        config = {
            'backends': {
                'mock-ollama': {
                    'type': 'ollama',
                    'url': 'http://localhost:11434',
                    'enabled': True
                }
            }
        }
        
        # Create test model info
        test_model = ModelInfo('test-model', BackendType.OLLAMA, 'mock-ollama')
        test_response = GenerationResponse(
            content='Integration test response',
            model='test-model',
            backend_type=BackendType.OLLAMA,
            backend_id='mock-ollama',
            response_time_ms=1200,
            estimated_tokens=75
        )
        
        # Mock the entire backend
        with patch('backends.manager.OllamaBackend') as mock_backend_class:
            mock_backend = Mock()
            mock_backend.backend_id = 'mock-ollama'
            mock_backend.backend_type = BackendType.OLLAMA
            mock_backend.get_health = AsyncMock(return_value=BackendHealth(BackendStatus.HEALTHY))
            mock_backend.get_models = AsyncMock(return_value=[test_model])
            mock_backend.generate_response = AsyncMock(return_value=test_response)
            mock_backend.close = AsyncMock()
            mock_backend_class.return_value = mock_backend
            
            # Test the complete workflow
            manager = BackendManager(config)
            await manager.initialize()
            
            # Check initialization
            assert len(manager.backends) == 1
            assert 'mock-ollama' in manager.backends
            
            # Manually set backend health for testing
            manager.backend_health['mock-ollama'] = BackendHealth(BackendStatus.HEALTHY)
            
            # Get models
            models = await manager.get_all_models()
            assert len(models) == 1
            assert models[0].name == 'test-model'
            
            # Generate response - mock the internal methods
            with patch.object(manager, '_find_model_backends', return_value=['mock-ollama']):
                response = await manager.generate_response(
                    'test-model', 
                    'Test prompt',
                    [{'role': 'user', 'content': 'Previous message'}]
                )
                
                assert response.content == 'Integration test response'
                assert response.response_time_ms == 1200
                assert response.estimated_tokens == 75
            
            # Test backend status
            status = await manager.get_backend_status()
            assert 'mock-ollama' in status
            
            # Cleanup
            await manager.shutdown()
    
    @pytest.mark.asyncio 
    async def test_manager_with_multiple_backends(self):
        """Test manager with multiple backend types."""
        config = {
            'backends': {
                'ollama-1': {
                    'type': 'ollama',
                    'url': 'http://localhost:11434',
                    'enabled': True
                },
                'llamacpp-1': {
                    'type': 'llama_cpp',
                    'url': 'http://localhost:8080',
                    'enabled': True
                }
            }
        }
        
        with patch('backends.manager.OllamaBackend') as mock_ollama, \
             patch('backends.manager.LlamaCppBackend') as mock_llamacpp:
            
            # Setup mock backends
            mock_ollama_backend = Mock()
            mock_ollama_backend.get_health = AsyncMock(return_value=BackendHealth(BackendStatus.HEALTHY))
            mock_ollama_backend.close = AsyncMock()
            mock_ollama.return_value = mock_ollama_backend
            
            mock_llamacpp_backend = Mock()
            mock_llamacpp_backend.get_health = AsyncMock(return_value=BackendHealth(BackendStatus.HEALTHY))
            mock_llamacpp_backend.close = AsyncMock()
            mock_llamacpp.return_value = mock_llamacpp_backend
            
            manager = BackendManager(config)
            await manager.initialize()
            
            # Should have both backends
            assert len(manager.backends) == 2
            assert 'ollama-1' in manager.backends
            assert 'llamacpp-1' in manager.backends
            
            await manager.shutdown()
    
    def test_synchronous_wrapper_compatibility(self):
        """Test that synchronous wrappers work for backward compatibility."""
        # Test OllamaAPI wrapper
        ollama_config = {
            'url': 'http://localhost:11434',
            'timeout': 180
        }
        
        api = OllamaAPI(ollama_config)
        assert api.backend.backend_id == 'ollama-default'
        assert api.backend.backend_type == BackendType.OLLAMA
        
        # Test BackendManagerSync wrapper
        manager_config = {
            'backends': {
                'test': {
                    'type': 'ollama',
                    'url': 'http://localhost:11434',
                    'enabled': True
                }
            }
        }
        
        sync_manager = BackendManagerSync(manager_config)
        assert isinstance(sync_manager.manager, BackendManager)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
