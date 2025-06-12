"""
Shared test fixtures and configuration for backend tests.
"""
import pytest
import asyncio
import sys
import os

# Add project root to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "asyncio: marks tests as async tests that require asyncio"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "performance: marks tests as performance benchmarks"
    )


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture
def sample_config():
    """Sample configuration for testing."""
    return {
        'backends': {
            'test-ollama': {
                'type': 'ollama',
                'url': 'http://localhost:11434',
                'enabled': True,
                'timeout': 180,
                'connect_timeout': 15
            },
            'test-llamacpp': {
                'type': 'llama_cpp',
                'url': 'http://localhost:8080',
                'enabled': True,
                'timeout': 180,
                'connect_timeout': 15,
                'api_key': 'test-key'
            },
            'test-disabled': {
                'type': 'ollama',
                'url': 'http://localhost:11435',
                'enabled': False
            }
        },
        'model_options': {
            'temperature': 0.7,
            'top_p': 0.9,
            'num_predict': 1000,
            'num_ctx': 4096
        },
        'performance': {
            'num_thread': 4,
            'num_gpu': 0,
            'use_mlock': True,
            'use_mmap': True
        },
        'system_prompt': 'You are a helpful assistant.',
        'response_optimization': {
            'stream': False,
            'keep_alive': '5m'
        }
    }


@pytest.fixture
def ollama_config():
    """Ollama-specific test configuration."""
    return {
        'url': 'http://localhost:11434',
        'timeout': 180,
        'connect_timeout': 15,
        'system_prompt': 'You are a helpful assistant.',
        'model_options': {
            'temperature': 0.7,
            'top_p': 0.9
        },
        'performance': {
            'num_thread': 4,
            'use_mlock': True
        }
    }


@pytest.fixture
def llamacpp_config():
    """Llama.cpp-specific test configuration."""
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
def mock_ollama_response():
    """Mock response data for Ollama API."""
    return {
        'response': 'Hello! How can I help you today?',
        'eval_count': 30,
        'prompt_eval_count': 10,
        'eval_duration': 1000000000,  # 1 second in nanoseconds
        'prompt_eval_duration': 200000000,  # 0.2 seconds
        'load_duration': 100000000,  # 0.1 seconds
        'total_duration': 1300000000  # 1.3 seconds
    }


@pytest.fixture
def mock_llamacpp_response():
    """Mock response data for llama.cpp API."""
    return {
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


@pytest.fixture
def mock_models_ollama():
    """Mock models data for Ollama."""
    return {
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
                'modified_at': '2024-01-01T00:00:00Z',
                'digest': 'def456'
            }
        ]
    }


@pytest.fixture
def mock_models_llamacpp():
    """Mock models data for llama.cpp."""
    return {
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


# Pytest collection customization
def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically."""
    for item in items:
        # Mark async tests (only if the function is actually async)
        if asyncio.iscoroutinefunction(item.function):
            item.add_marker(pytest.mark.asyncio)
        
        # Mark integration tests
        if "integration" in item.name.lower() or "end_to_end" in item.name.lower():
            item.add_marker(pytest.mark.integration)
        
        # Mark unit tests (default for most tests)
        if not any(marker.name in ['integration', 'performance'] for marker in item.iter_markers()):
            item.add_marker(pytest.mark.unit)


# Custom pytest fixtures for async testing
@pytest.fixture
async def async_mock_session():
    """Mock aiohttp session for testing."""
    from unittest.mock import AsyncMock, MagicMock
    
    session = AsyncMock()
    response = AsyncMock()
    
    # Configure mock response
    response.status = 200
    response.json = AsyncMock()
    response.text = AsyncMock()
    
    # Configure mock session
    session.get.return_value.__aenter__.return_value = response
    session.post.return_value.__aenter__.return_value = response
    session.closed = False
    session.close = AsyncMock()
    
    return session, response
