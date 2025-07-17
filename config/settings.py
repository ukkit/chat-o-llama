"""Configuration management for Chat-O-Llama."""

import os
import json
import logging
from typing import Dict, Any
from .defaults import get_default_config
from .validation import validate_config, is_config_valid

logger = logging.getLogger(__name__)

# Global configuration instance
_config = None


def load_config():
    """Load configuration from config.json file."""
    config_path = os.environ.get('CONFIG_FILE', os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json'))
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Validate loaded configuration
        errors = validate_config(config)
        if errors:
            logger.error(f"Configuration validation errors: {'; '.join(errors)}")
            logger.warning("Using default configuration due to validation errors")
            return get_default_config()
        
        # Merge with defaults to ensure all required keys are present
        default_config = get_default_config()
        merged_config = _merge_configs(default_config, config)
        
        logger.info("Configuration loaded and validated from config.json")
        return merged_config
        
    except FileNotFoundError:
        logger.warning(f"Config file not found at {config_path}, using defaults")
        return get_default_config()
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in config file: {e}, using defaults")
        return get_default_config()


def _merge_configs(default: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge user configuration with defaults."""
    merged = default.copy()
    
    for key, value in user.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _merge_configs(merged[key], value)
        else:
            merged[key] = value
    
    return merged


def get_config():
    """Get the current configuration, loading it if necessary."""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reload_config():
    """Reload configuration from file."""
    global _config
    _config = load_config()
    return _config