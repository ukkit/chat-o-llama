"""Configuration validation for Chat-O-Llama."""

import os
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


def validate_backend_config(config: Dict[str, Any]) -> List[str]:
    """Validate backend configuration and return list of errors."""
    errors = []
    
    # Validate backend section
    if 'backend' not in config:
        errors.append("Missing 'backend' section in configuration")
        return errors
    
    backend_config = config['backend']
    
    # Validate active backend
    if 'active' not in backend_config:
        errors.append("Missing 'active' backend setting")
    elif backend_config['active'] not in ['ollama', 'llamacpp']:
        errors.append(f"Invalid active backend: {backend_config['active']}. Must be 'ollama' or 'llamacpp'")
    
    # Validate auto_fallback
    if 'auto_fallback' in backend_config and not isinstance(backend_config['auto_fallback'], bool):
        errors.append("'auto_fallback' must be a boolean value")
    
    # Validate health_check_interval
    if 'health_check_interval' in backend_config:
        if not isinstance(backend_config['health_check_interval'], (int, float)) or backend_config['health_check_interval'] <= 0:
            errors.append("'health_check_interval' must be a positive number")
    
    return errors


def validate_ollama_config(config: Dict[str, Any]) -> List[str]:
    """Validate Ollama-specific configuration and return list of errors."""
    errors = []
    
    if 'ollama' not in config:
        return errors  # Optional if not using Ollama
    
    ollama_config = config['ollama']
    
    # Validate base_url
    if 'base_url' in ollama_config:
        if not isinstance(ollama_config['base_url'], str) or not ollama_config['base_url'].startswith(('http://', 'https://')):
            errors.append("'ollama.base_url' must be a valid HTTP URL")
    
    # Validate timeouts
    for timeout_key in ['timeout', 'connect_timeout']:
        if timeout_key in ollama_config:
            if not isinstance(ollama_config[timeout_key], (int, float)) or ollama_config[timeout_key] <= 0:
                errors.append(f"'ollama.{timeout_key}' must be a positive number")
    
    # Validate max_retries
    if 'max_retries' in ollama_config:
        if not isinstance(ollama_config['max_retries'], int) or ollama_config['max_retries'] < 0:
            errors.append("'ollama.max_retries' must be a non-negative integer")
    
    # Validate verify_ssl
    if 'verify_ssl' in ollama_config and not isinstance(ollama_config['verify_ssl'], bool):
        errors.append("'ollama.verify_ssl' must be a boolean value")
    
    return errors


def validate_llamacpp_config(config: Dict[str, Any]) -> List[str]:
    """Validate llama.cpp-specific configuration and return list of errors."""
    errors = []
    
    if 'llamacpp' not in config:
        return errors  # Optional if not using llama.cpp
    
    llamacpp_config = config['llamacpp']
    
    # Validate model_path
    if 'model_path' in llamacpp_config:
        model_path = llamacpp_config['model_path']
        if not isinstance(model_path, str):
            errors.append("'llamacpp.model_path' must be a string")
        elif not os.path.exists(model_path):
            logger.warning(f"Model path does not exist: {model_path}")
    
    # Validate integer parameters
    int_params = ['n_ctx', 'n_batch', 'n_threads', 'n_gpu_layers']
    for param in int_params:
        if param in llamacpp_config:
            value = llamacpp_config[param]
            if not isinstance(value, int):
                errors.append(f"'llamacpp.{param}' must be an integer")
            elif param in ['n_ctx', 'n_batch'] and value <= 0:
                errors.append(f"'llamacpp.{param}' must be a positive integer")
            elif param == 'n_gpu_layers' and value < 0:
                errors.append(f"'llamacpp.{param}' must be non-negative")
    
    # Validate boolean parameters
    bool_params = ['use_mmap', 'use_mlock', 'verbose']
    for param in bool_params:
        if param in llamacpp_config and not isinstance(llamacpp_config[param], bool):
            errors.append(f"'llamacpp.{param}' must be a boolean value")
    
    # Validate float parameters
    float_params = ['rope_freq_base', 'rope_freq_scale']
    for param in float_params:
        if param in llamacpp_config:
            value = llamacpp_config[param]
            if not isinstance(value, (int, float)) or value <= 0:
                errors.append(f"'llamacpp.{param}' must be a positive number")
    
    # Validate rope_scaling_type
    if 'rope_scaling_type' in llamacpp_config:
        valid_types = ['none', 'linear', 'yarn']
        if llamacpp_config['rope_scaling_type'] not in valid_types:
            errors.append(f"'llamacpp.rope_scaling_type' must be one of: {', '.join(valid_types)}")
    
    return errors


def validate_compression_config(config: Dict[str, Any]) -> List[str]:
    """Validate compression configuration and return list of errors."""
    errors = []
    
    if 'compression' not in config:
        return errors  # Optional compression configuration
    
    compression_config = config['compression']
    
    # Validate enabled flag
    if 'enabled' in compression_config and not isinstance(compression_config['enabled'], bool):
        errors.append("'compression.enabled' must be a boolean value")
    
    # Validate trigger thresholds
    threshold_params = ['trigger_token_threshold', 'trigger_message_count']
    for param in threshold_params:
        if param in compression_config:
            value = compression_config[param]
            if not isinstance(value, int) or value <= 0:
                errors.append(f"'compression.{param}' must be a positive integer")
    
    # Validate trigger_utilization_percent
    if 'trigger_utilization_percent' in compression_config:
        value = compression_config['trigger_utilization_percent']
        if not isinstance(value, (int, float)) or not (0 < value <= 100):
            errors.append("'compression.trigger_utilization_percent' must be a number between 0 and 100")
    
    # Validate strategy
    if 'strategy' in compression_config:
        valid_strategies = ['rolling_window', 'intelligent_summary', 'hybrid']
        if compression_config['strategy'] not in valid_strategies:
            errors.append(f"'compression.strategy' must be one of: {', '.join(valid_strategies)}")
    
    # Validate preserve_recent_messages
    if 'preserve_recent_messages' in compression_config:
        value = compression_config['preserve_recent_messages']
        if not isinstance(value, int) or value < 0:
            errors.append("'compression.preserve_recent_messages' must be a non-negative integer")
    
    # Validate compression_ratio_target
    if 'compression_ratio_target' in compression_config:
        value = compression_config['compression_ratio_target']
        if not isinstance(value, (int, float)) or not (0 < value <= 1):
            errors.append("'compression.compression_ratio_target' must be a number between 0 and 1")
    
    # Validate cache settings
    if 'cache_compressed_contexts' in compression_config:
        if not isinstance(compression_config['cache_compressed_contexts'], bool):
            errors.append("'compression.cache_compressed_contexts' must be a boolean value")
    
    if 'cache_expiry_minutes' in compression_config:
        value = compression_config['cache_expiry_minutes']
        if not isinstance(value, int) or value <= 0:
            errors.append("'compression.cache_expiry_minutes' must be a positive integer")
    
    # Validate strategies section
    if 'strategies' in compression_config:
        errors.extend(_validate_compression_strategies(compression_config['strategies']))
    
    # Validate performance section
    if 'performance' in compression_config:
        errors.extend(_validate_compression_performance(compression_config['performance']))
    
    # Validate preservation_rules section
    if 'preservation_rules' in compression_config:
        errors.extend(_validate_preservation_rules(compression_config['preservation_rules']))
    
    # Validate analytics section
    if 'analytics' in compression_config:
        errors.extend(_validate_compression_analytics(compression_config['analytics']))
    
    return errors


def _validate_compression_strategies(strategies_config: Dict[str, Any]) -> List[str]:
    """Validate compression strategies configuration."""
    errors = []
    
    # Validate rolling_window strategy
    if 'rolling_window' in strategies_config:
        rw_config = strategies_config['rolling_window']
        
        if 'enabled' in rw_config and not isinstance(rw_config['enabled'], bool):
            errors.append("'compression.strategies.rolling_window.enabled' must be a boolean")
        
        if 'window_size' in rw_config:
            value = rw_config['window_size']
            if not isinstance(value, int) or value <= 0:
                errors.append("'compression.strategies.rolling_window.window_size' must be a positive integer")
        
        for bool_param in ['preserve_system_prompt', 'preserve_important_messages']:
            if bool_param in rw_config and not isinstance(rw_config[bool_param], bool):
                errors.append(f"'compression.strategies.rolling_window.{bool_param}' must be a boolean")
        
        if 'importance_threshold' in rw_config:
            value = rw_config['importance_threshold']
            if not isinstance(value, (int, float)) or not (0 <= value <= 1):
                errors.append("'compression.strategies.rolling_window.importance_threshold' must be between 0 and 1")
    
    # Validate intelligent_summary strategy
    if 'intelligent_summary' in strategies_config:
        is_config = strategies_config['intelligent_summary']
        
        if 'enabled' in is_config and not isinstance(is_config['enabled'], bool):
            errors.append("'compression.strategies.intelligent_summary.enabled' must be a boolean")
        
        if 'summarization_model' in is_config and not isinstance(is_config['summarization_model'], str):
            errors.append("'compression.strategies.intelligent_summary.summarization_model' must be a string")
        
        if 'summary_length_ratio' in is_config:
            value = is_config['summary_length_ratio']
            if not isinstance(value, (int, float)) or not (0 < value <= 1):
                errors.append("'compression.strategies.intelligent_summary.summary_length_ratio' must be between 0 and 1")
        
        for bool_param in ['preserve_code_blocks', 'preserve_technical_content']:
            if bool_param in is_config and not isinstance(is_config[bool_param], bool):
                errors.append(f"'compression.strategies.intelligent_summary.{bool_param}' must be a boolean")
        
        if 'min_messages_to_summarize' in is_config:
            value = is_config['min_messages_to_summarize']
            if not isinstance(value, int) or value <= 0:
                errors.append("'compression.strategies.intelligent_summary.min_messages_to_summarize' must be a positive integer")
    
    # Validate hybrid strategy
    if 'hybrid' in strategies_config:
        hybrid_config = strategies_config['hybrid']
        
        if 'enabled' in hybrid_config and not isinstance(hybrid_config['enabled'], bool):
            errors.append("'compression.strategies.hybrid.enabled' must be a boolean")
        
        for int_param in ['tier1_messages', 'tier2_messages']:
            if int_param in hybrid_config:
                value = hybrid_config[int_param]
                if not isinstance(value, int) or value <= 0:
                    errors.append(f"'compression.strategies.hybrid.{int_param}' must be a positive integer")
        
        if 'tier3_summary_ratio' in hybrid_config:
            value = hybrid_config['tier3_summary_ratio']
            if not isinstance(value, (int, float)) or not (0 < value <= 1):
                errors.append("'compression.strategies.hybrid.tier3_summary_ratio' must be between 0 and 1")
        
        if 'dynamic_tier_adjustment' in hybrid_config:
            if not isinstance(hybrid_config['dynamic_tier_adjustment'], bool):
                errors.append("'compression.strategies.hybrid.dynamic_tier_adjustment' must be a boolean")
    
    return errors


def _validate_compression_performance(performance_config: Dict[str, Any]) -> List[str]:
    """Validate compression performance configuration."""
    errors = []
    
    if 'max_compression_time_ms' in performance_config:
        value = performance_config['max_compression_time_ms']
        if not isinstance(value, int) or value <= 0:
            errors.append("'compression.performance.max_compression_time_ms' must be a positive integer")
    
    for bool_param in ['async_compression', 'fallback_on_failure', 'monitor_compression_effectiveness']:
        if bool_param in performance_config:
            if not isinstance(performance_config[bool_param], bool):
                errors.append(f"'compression.performance.{bool_param}' must be a boolean")
    
    if 'compression_quality_threshold' in performance_config:
        value = performance_config['compression_quality_threshold']
        if not isinstance(value, (int, float)) or not (0 <= value <= 1):
            errors.append("'compression.performance.compression_quality_threshold' must be between 0 and 1")
    
    return errors


def _validate_preservation_rules(preservation_config: Dict[str, Any]) -> List[str]:
    """Validate preservation rules configuration."""
    errors = []
    
    if 'always_preserve' in preservation_config:
        value = preservation_config['always_preserve']
        if not isinstance(value, list):
            errors.append("'compression.preservation_rules.always_preserve' must be a list")
        elif not all(isinstance(item, str) for item in value):
            errors.append("'compression.preservation_rules.always_preserve' must be a list of strings")
    
    if 'content_importance_weights' in preservation_config:
        weights = preservation_config['content_importance_weights']
        if not isinstance(weights, dict):
            errors.append("'compression.preservation_rules.content_importance_weights' must be a dictionary")
        else:
            for key, value in weights.items():
                if not isinstance(key, str):
                    errors.append(f"'compression.preservation_rules.content_importance_weights' key '{key}' must be a string")
                if not isinstance(value, (int, float)) or not (0 <= value <= 1):
                    errors.append(f"'compression.preservation_rules.content_importance_weights.{key}' must be between 0 and 1")
    
    for bool_param in ['preserve_conversation_context', 'maintain_chronological_order']:
        if bool_param in preservation_config:
            if not isinstance(preservation_config[bool_param], bool):
                errors.append(f"'compression.preservation_rules.{bool_param}' must be a boolean")
    
    return errors


def _validate_compression_analytics(analytics_config: Dict[str, Any]) -> List[str]:
    """Validate compression analytics configuration."""
    errors = []
    
    for bool_param in ['track_compression_metrics', 'log_compression_decisions', 
                       'report_token_savings', 'monitor_response_quality']:
        if bool_param in analytics_config:
            if not isinstance(analytics_config[bool_param], bool):
                errors.append(f"'compression.analytics.{bool_param}' must be a boolean")
    
    if 'compression_effectiveness_threshold' in analytics_config:
        value = analytics_config['compression_effectiveness_threshold']
        if not isinstance(value, (int, float)) or not (0 <= value <= 1):
            errors.append("'compression.analytics.compression_effectiveness_threshold' must be between 0 and 1")
    
    return errors


def validate_config(config: Dict[str, Any]) -> List[str]:
    """Validate complete configuration and return list of errors."""
    errors = []
    
    # Validate backend configuration
    errors.extend(validate_backend_config(config))
    
    # Validate backend-specific configurations
    errors.extend(validate_ollama_config(config))
    errors.extend(validate_llamacpp_config(config))
    
    # Validate compression configuration
    errors.extend(validate_compression_config(config))
    
    return errors


def is_config_valid(config: Dict[str, Any]) -> bool:
    """Check if configuration is valid (has no errors)."""
    return len(validate_config(config)) == 0