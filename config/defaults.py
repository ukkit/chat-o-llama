"""Default configuration values for Chat-O-Llama."""


def get_default_config():
    """Get default configuration if config.json is not available."""
    return {
        "backend": {
            "active": "ollama",
            "auto_fallback": True,
            "health_check_interval": 30
        },
        "ollama": {
            "base_url": "http://localhost:11434",
            "timeout": 180,
            "connect_timeout": 15,
            "verify_ssl": True,
            "max_retries": 3
        },
        "llamacpp": {
            "model_path": "./models",
            "n_ctx": 4096,
            "n_batch": 512,
            "n_threads": -1,
            "n_gpu_layers": 0,
            "use_mmap": True,
            "use_mlock": False,
            "verbose": False,
            "rope_scaling_type": "none",
            "rope_freq_base": 10000.0,
            "rope_freq_scale": 1.0
        },
        "timeouts": {
            "ollama_timeout": 180,
            "ollama_connect_timeout": 15
        },
        "model_options": {
            "temperature": 0.5,
            "top_p": 0.8,
            "top_k": 30,
            "num_predict": 4096,
            "num_ctx": 4096,
            "repeat_penalty": 1.1,
            "stop": ["\n\nHuman:", "\n\nUser:", "\nHuman:", "\nUser:", "Human:", "User:"]
        },
        "performance": {
            "context_history_limit": 10,
            "batch_size": 1,
            "use_mlock": True,
            "use_mmap": True,
            "num_thread": -1,
            "num_gpu": 0
        },
        "system_prompt": "Your name is Bhaai, a helpful, friendly, and knowledgeable AI assistant. You have a warm personality and enjoy helping users solve problems. You're curious about technology and always try to provide practical, actionable advice. You occasionally use light humor when appropriate, but remain professional and focused on being genuinely helpful.",
        "response_optimization": {
            "stream": False,
            "keep_alive": "5m",
            "low_vram": False,
            "f16_kv": True,
            "logits_all": False,
            "vocab_only": False,
            "use_mmap": True,
            "use_mlock": False,
            "embedding_only": False,
            "numa": False
        },
        "compression": {
            "enabled": False,
            "trigger_token_threshold": 3000,
            "trigger_message_count": 20,
            "trigger_utilization_percent": 80.0,
            "strategy": "rolling_window",
            "preserve_recent_messages": 10,
            "compression_ratio_target": 0.3,
            "cache_compressed_contexts": True,
            "cache_expiry_minutes": 30,
            "strategies": {
                "rolling_window": {
                    "enabled": True,
                    "window_size": 10,
                    "preserve_system_prompt": True,
                    "preserve_important_messages": True,
                    "importance_threshold": 0.6
                },
                "intelligent_summary": {
                    "enabled": False,
                    "summarization_model": "llama3.2:1b",
                    "summary_length_ratio": 0.2,
                    "preserve_code_blocks": True,
                    "preserve_technical_content": True,
                    "min_messages_to_summarize": 5
                },
                "hybrid": {
                    "enabled": False,
                    "tier1_messages": 5,
                    "tier2_messages": 10,
                    "tier3_summary_ratio": 0.15,
                    "dynamic_tier_adjustment": True
                }
            },
            "performance": {
                "max_compression_time_ms": 1000,
                "async_compression": True,
                "compression_quality_threshold": 0.8,
                "fallback_on_failure": True,
                "monitor_compression_effectiveness": True
            },
            "preservation_rules": {
                "always_preserve": [
                    "system_prompts",
                    "recent_messages",
                    "code_blocks",
                    "error_messages",
                    "user_questions"
                ],
                "content_importance_weights": {
                    "user_questions": 1.0,
                    "code_content": 0.9,
                    "error_messages": 0.9,
                    "technical_discussions": 0.8,
                    "decisions_and_conclusions": 0.8,
                    "general_conversation": 0.3
                },
                "preserve_conversation_context": True,
                "maintain_chronological_order": True
            },
            "analytics": {
                "track_compression_metrics": True,
                "log_compression_decisions": False,
                "report_token_savings": True,
                "monitor_response_quality": True,
                "compression_effectiveness_threshold": 0.5
            }
        }
    }