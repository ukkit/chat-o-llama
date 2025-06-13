import json
import os
import logging
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse
import requests
from dataclasses import dataclass
from enum import Enum

class BackendType(Enum):
    OLLAMA = "ollama"
    LLAMA_CPP = "llama_cpp"

@dataclass
class BackendConfig:
    """Configuration for a specific backend."""
    enabled: bool
    url: str
    timeout: int
    max_retries: int
    health_check_interval: int
    api_key: Optional[str] = None

@dataclass
class LlamaCppConfig(BackendConfig):
    """Extended configuration for llama.cpp backend."""
    openai_compatible: bool = True
    chat_endpoint: str = "/v1/chat/completions"
    models_endpoint: str = "/v1/models"

class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing."""
    pass

class ConfigManager:
    """Manages application configuration with validation and environment variable support."""
    
    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.config = {}
        self.logger = logging.getLogger(__name__)
        self._load_config()
        self._apply_environment_overrides()
        self._validate_config()
    
    def _load_config(self) -> None:
        """Load configuration from JSON file."""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    self.config = json.load(f)
                self.logger.info(f"Configuration loaded from {self.config_path}")
            else:
                self.logger.warning(f"Configuration file {self.config_path} not found, using defaults")
                self._create_default_config()
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Invalid JSON in configuration file: {e}")
        except Exception as e:
            raise ConfigurationError(f"Error loading configuration: {e}")
    
    def _create_default_config(self) -> None:
        """Create default configuration structure."""
        self.config = {
            "app": {
                "host": "0.0.0.0",
                "port": 5000,
                "debug": False
            },
            "backends": {
                "default": "ollama",
                "enabled": ["ollama"],
                "ollama": {
                    "enabled": True,
                    "url": "http://localhost:11434",
                    "timeout": 30,
                    "max_retries": 3,
                    "health_check_interval": 60
                }
            }
        }
    
    def _apply_environment_overrides(self) -> None:
        """Apply environment variable overrides with precedence."""
        env_mappings = {
            # App settings
            "CHAT_APP_HOST": ("app", "host"),
            "CHAT_APP_PORT": ("app", "port"),
            "CHAT_APP_DEBUG": ("app", "debug"),
            "CHAT_SECRET_KEY": ("app", "secret_key"),
            
            # Ollama settings
            "OLLAMA_URL": ("backends", "ollama", "url"),
            "OLLAMA_TIMEOUT": ("backends", "ollama", "timeout"),
            "OLLAMA_API_KEY": ("backends", "ollama", "api_key"),
            "OLLAMA_ENABLED": ("backends", "ollama", "enabled"),
            
            # Llama.cpp settings
            "LLAMA_CPP_URL": ("backends", "llama_cpp", "url"),
            "LLAMA_CPP_TIMEOUT": ("backends", "llama_cpp", "timeout"),
            "LLAMA_CPP_API_KEY": ("backends", "llama_cpp", "api_key"),
            "LLAMA_CPP_ENABLED": ("backends", "llama_cpp", "enabled"),
            "LLAMA_CPP_CHAT_ENDPOINT": ("backends", "llama_cpp", "chat_endpoint"),
            "LLAMA_CPP_MODELS_ENDPOINT": ("backends", "llama_cpp", "models_endpoint"),
            
            # Database settings
            "DATABASE_PATH": ("database", "path"),
            
            # Performance settings
            "MAX_CONCURRENT_REQUESTS": ("performance", "max_concurrent_requests"),
            "MODEL_CACHE_TTL": ("performance", "model_cache_ttl"),
        }
        
        for env_var, config_path in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                self._set_nested_config(config_path, self._convert_env_value(value))
                self.logger.info(f"Applied environment override: {env_var}")
    
    def _convert_env_value(self, value: str) -> Any:
        """Convert string environment variable to appropriate type."""
        # Boolean conversion
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # Integer conversion
        try:
            return int(value)
        except ValueError:
            pass
        
        # Float conversion
        try:
            return float(value)
        except ValueError:
            pass
        
        # String (default)
        return value
    
    def _set_nested_config(self, path: tuple, value: Any) -> None:
        """Set a nested configuration value."""
        current = self.config
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[path[-1]] = value
    
    def _validate_config(self) -> None:
        """Validate the complete configuration."""
        errors = []
        
        # Validate app configuration
        errors.extend(self._validate_app_config())
        
        # Validate backend configurations
        errors.extend(self._validate_backends_config())
        
        # Validate database configuration
        errors.extend(self._validate_database_config())
        
        if errors:
            raise ConfigurationError(f"Configuration validation failed:\n" + "\n".join(errors))
        
        self.logger.info("Configuration validation successful")
    
    def _validate_app_config(self) -> List[str]:
        """Validate app-specific configuration."""
        errors = []
        app_config = self.config.get("app", {})
        
        # Validate port
        port = app_config.get("port", 5000)
        if not isinstance(port, int) or port < 1 or port > 65535:
            errors.append("App port must be an integer between 1 and 65535")
        
        # Validate host
        host = app_config.get("host", "0.0.0.0")
        if not isinstance(host, str) or not host.strip():
            errors.append("App host must be a non-empty string")
        
        return errors
    
    def _validate_backends_config(self) -> List[str]:
        """Validate backend configurations - Updated for flexible schema."""
        errors = []
        backends = self.config.get("backends", {})
        
        # Check for default backend in multiple locations
        default_backend = None
        if "default_backend" in self.config:
            default_backend = self.config["default_backend"]
        elif "default" in backends:
            default_backend = backends["default"]
        
        if not default_backend:
            errors.append("Default backend must be specified (use 'default_backend' at root level or 'backends.default')")
        
        # Get enabled backends - check both formats
        enabled_backends = []
        
        # Format 1: Check "enabled" array in backends section
        if "enabled" in backends and isinstance(backends["enabled"], list):
            for backend_name in backends["enabled"]:
                backend_config = backends.get(backend_name, {})
                if isinstance(backend_config, dict) and backend_config.get("enabled", False):
                    enabled_backends.append(backend_name)
        
        # Format 2: Check individual backend enabled flags
        for backend_name, backend_config in backends.items():
            if (backend_name not in ["default", "enabled", "default_backend"] and 
                isinstance(backend_config, dict) and 
                backend_config.get("enabled", False)):
                if backend_name not in enabled_backends:
                    enabled_backends.append(backend_name)
        
        if not enabled_backends:
            errors.append("At least one backend must be enabled (set 'enabled': true in backend config)")
        
        # Validate individual backend configurations
        for backend_name in enabled_backends:
            backend_config = backends.get(backend_name, {})
            backend_errors = self._validate_backend_config(backend_name, backend_config)
            errors.extend(backend_errors)
        
        # Validate that default backend is among enabled backends
        if default_backend and default_backend not in enabled_backends:
            errors.append(f"Default backend '{default_backend}' must be enabled")
        
        return errors
    
    def _validate_backend_config(self, name: str, config: Dict[str, Any]) -> List[str]:
        """Validate individual backend configuration."""
        errors = []
        
        # Check if backend is enabled
        if not config.get("enabled", False):
            return errors  # Skip validation for disabled backends
        
        # Validate URL
        url = config.get("url")
        if not url:
            errors.append(f"Backend '{name}': URL is required")
        else:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                errors.append(f"Backend '{name}': Invalid URL format")
        
        # Validate timeout
        timeout = config.get("timeout", 30)
        if not isinstance(timeout, int) or timeout <= 0:
            errors.append(f"Backend '{name}': Timeout must be a positive integer")
        
        # Validate max_retries
        max_retries = config.get("max_retries", 3)
        if not isinstance(max_retries, int) or max_retries < 0:
            errors.append(f"Backend '{name}': Max retries must be a non-negative integer")
        
        return errors
    
    def _validate_database_config(self) -> List[str]:
        """Validate database configuration - Updated for flexible schema."""
        errors = []
        
        # Check for database path in multiple locations
        db_path = None
        if "database" in self.config:
            db_config = self.config["database"]
            if isinstance(db_config, dict):
                db_path = db_config.get("path")
            elif isinstance(db_config, str):
                db_path = db_config
        elif "database_path" in self.config:
            db_path = self.config["database_path"]
        
        if not db_path:
            errors.append("Database path must be specified (use 'database.path' or 'database_path')")
        elif not isinstance(db_path, str):
            errors.append("Database path must be a string")
        
        return errors
    
    def test_backend_connectivity(self, backend_name: str) -> tuple[bool, str]:
        """Test connectivity to a specific backend."""
        backend_config = self.get_backend_config(backend_name)
        if not backend_config or not backend_config.enabled:
            return False, f"Backend '{backend_name}' is not enabled"
        
        try:
            # Determine the health check endpoint
            if backend_name == "ollama":
                health_url = f"{backend_config.url}/api/tags"
            elif backend_name == "llama_cpp":
                if hasattr(backend_config, 'models_endpoint'):
                    health_url = f"{backend_config.url}{backend_config.models_endpoint}"
                else:
                    health_url = f"{backend_config.url}/v1/models"
            else:
                return False, f"Unknown backend type: {backend_name}"
            
            # Prepare headers
            headers = {}
            if backend_config.api_key:
                headers["Authorization"] = f"Bearer {backend_config.api_key}"
            
            # Make the request
            response = requests.get(
                health_url,
                timeout=min(backend_config.timeout, 10),  # Use shorter timeout for health checks
                headers=headers
            )
            
            if response.status_code == 200:
                return True, f"Backend '{backend_name}' is reachable"
            else:
                return False, f"Backend '{backend_name}' returned status {response.status_code}"
                
        except requests.exceptions.ConnectionError:
            return False, f"Cannot connect to backend '{backend_name}' at {backend_config.url}"
        except requests.exceptions.Timeout:
            return False, f"Backend '{backend_name}' connection timed out"
        except Exception as e:
            return False, f"Backend '{backend_name}' health check failed: {str(e)}"
    
    def get_backend_config(self, backend_name: str) -> Optional[BackendConfig]:
        """Get configuration for a specific backend."""
        backends = self.config.get("backends", {})
        config = backends.get(backend_name)
        
        if not config:
            return None
        
        if backend_name == "llama_cpp":
            return LlamaCppConfig(
                enabled=config.get("enabled", False),
                url=config.get("url", ""),
                timeout=config.get("timeout", 45),
                max_retries=config.get("max_retries", 3),
                health_check_interval=config.get("health_check_interval", 60),
                api_key=config.get("api_key"),
                openai_compatible=config.get("openai_compatible", True),
                chat_endpoint=config.get("chat_endpoint", "/v1/chat/completions"),
                models_endpoint=config.get("models_endpoint", "/v1/models")
            )
        else:
            return BackendConfig(
                enabled=config.get("enabled", False),
                url=config.get("url", ""),
                timeout=config.get("timeout", 30),
                max_retries=config.get("max_retries", 3),
                health_check_interval=config.get("health_check_interval", 60),
                api_key=config.get("api_key")
            )
    
    def get_enabled_backends(self) -> List[str]:
        """Get list of enabled backend names - Updated for flexible schema."""
        backends = self.config.get("backends", {})
        enabled = []
        
        # Check both the "enabled" array and individual backend flags
        enabled_list = backends.get("enabled", [])
        
        for backend_name in enabled_list:
            backend_config = backends.get(backend_name, {})
            if isinstance(backend_config, dict) and backend_config.get("enabled", False):
                enabled.append(backend_name)
        
        # Also check for backends with enabled=true that might not be in the enabled list
        for backend_name, backend_config in backends.items():
            if (backend_name not in ["default", "enabled", "default_backend"] and
                isinstance(backend_config, dict) and
                backend_config.get("enabled", False) and
                backend_name not in enabled):
                enabled.append(backend_name)
        
        return enabled
    
    def get_default_backend(self) -> str:
        """Get the default backend name - Updated for flexible schema."""
        # Check root level first
        if "default_backend" in self.config:
            return self.config["default_backend"]
        
        # Check backends.default
        return self.config.get("backends", {}).get("default", "ollama")
    
    def get(self, *path, default=None) -> Any:
        """Get a configuration value using dot notation."""
        current = self.config
        for key in path:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current
    
    def save_config(self) -> None:
        """Save current configuration to file."""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            self.logger.info(f"Configuration saved to {self.config_path}")
        except Exception as e:
            raise ConfigurationError(f"Error saving configuration: {e}")
    
    def update_backend_config(self, backend_name: str, updates: Dict[str, Any]) -> None:
        """Update configuration for a specific backend."""
        if "backends" not in self.config:
            self.config["backends"] = {}
        
        if backend_name not in self.config["backends"]:
            self.config["backends"][backend_name] = {}
        
        self.config["backends"][backend_name].update(updates)
        
        # Re-validate after update
        self._validate_config()
        
        self.logger.info(f"Updated configuration for backend '{backend_name}'")


# Global configuration instance
config_manager = None

def get_config_manager(config_path: str = "config.json") -> ConfigManager:
    """Get or create the global configuration manager instance."""
    global config_manager
    if config_manager is None:
        config_manager = ConfigManager(config_path)
    return config_manager

def init_config(config_path: str = "config.json") -> ConfigManager:
    """Initialize the configuration manager."""
    global config_manager
    config_manager = ConfigManager(config_path)
    return config_manager