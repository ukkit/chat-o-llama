# chat-o-llama 🦙 Configuration Guide

Complete configuration reference for customizing your chat-o-llama installation.

## 📋 **Quick Reference**

| Configuration Type | File/Method | Purpose |
|-------------------|------------|---------|
| **Runtime Settings** | `config.json` | Model parameters, timeouts, performance, multi-backend config ⭐ *Enhanced* |
| **Environment** | Environment Variables | Server URLs, paths, debugging |
| **Database** | `DATABASE_PATH` | SQLite database location |
| **Ollama Backend** | `OLLAMA_API_URL` | Ollama server connection |
| **llama.cpp Backend** | `config.json` | Local GGUF models, inference settings ⭐ *New* |
| **Backend Management** | `config.json` | Active backend, fallback, health checks ⭐ *New* |

---

## 🔧 **Runtime Configuration (config.json)**

Create a `config.json` file in your project root to customize application behavior.

### **Complete Multi-Backend Configuration Example** ⭐ *Updated*

```json
{
  "backend": {
    "active": "ollama",
    "auto_fallback": true,
    "health_check_interval": 30
  },
  "ollama": {
    "base_url": "http://localhost:11434",
    "timeout": 600,
    "connect_timeout": 45,
    "verify_ssl": true,
    "max_retries": 3
  },
  "llamacpp": {
    "model_path": "./llama_models",
    "n_ctx": 4096,
    "n_batch": 128,
    "n_threads": 8,
    "n_gpu_layers": 0,
    "use_mmap": true,
    "use_mlock": false,
    "verbose": false,
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
    "stop": ["\n\nHuman:", "\n\nUser:"]
  },
  "performance": {
    "context_history_limit": 10,
    "batch_size": 1,
    "use_mlock": true,
    "use_mmap": true,
    "num_thread": -1,
    "num_gpu": 0
  },
  "compression": {
    "enabled": true,
    "strategy": "hybrid",
    "trigger_threshold": 0.8,
    "preserve_recent_messages": 5,
    "cache_ttl": 3600,
    "quality_threshold": 0.7
  },
  "system_prompt": "Your name is Bhaai, a helpful, friendly, and knowledgeable AI assistant. You have a warm personality and enjoy helping users solve problems. You're curious about technology and always try to provide practical, actionable advice. You occasionally use light humor when appropriate, but remain professional and focused on being genuinely helpful.",
  "response_optimization": {
    "stream": false,
    "keep_alive": "5m",
    "low_vram": false,
    "f16_kv": true,
    "logits_all": false,
    "vocab_only": false,
    "use_mmap": true,
    "use_mlock": false,
    "embedding_only": false,
    "numa": false
  }
}
```

---

## 🔄 **Multi-Backend Configuration** ⭐ *New*

Configure and manage multiple AI backends for maximum flexibility and reliability.

### **Backend Selection**

```json
{
  "backend": {
    "active": "ollama",
    "auto_fallback": true,
    "health_check_interval": 30
  }
}
```

| Parameter | Options | Default | Description |
|-----------|---------|---------|-------------|
| `active` | `"ollama"`, `"llamacpp"` | `"ollama"` | Primary backend to use |
| `auto_fallback` | `true`, `false` | `true` | Switch to backup backend if primary fails |
| `health_check_interval` | Integer (seconds) | `30` | How often to check backend health |

### **Ollama Backend Configuration**

```json
{
  "ollama": {
    "base_url": "http://localhost:11434",
    "timeout": 600,
    "connect_timeout": 45,
    "verify_ssl": true,
    "max_retries": 3
  }
}
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `base_url` | `"http://localhost:11434"` | Ollama server base URL |
| `timeout` | `600` | Request timeout in seconds |
| `connect_timeout` | `45` | Connection timeout in seconds |
| `verify_ssl` | `true` | Verify SSL certificates for HTTPS |
| `max_retries` | `3` | Maximum retry attempts for failed requests |

### **llama.cpp Backend Configuration** ⭐ *New*

```json
{
  "llamacpp": {
    "model_path": "./llama_models",
    "n_ctx": 4096,
    "n_batch": 128,
    "n_threads": 8,
    "n_gpu_layers": 0,
    "use_mmap": true,
    "use_mlock": false,
    "verbose": false,
    "rope_scaling_type": "none",
    "rope_freq_base": 10000.0,
    "rope_freq_scale": 1.0
  }
}
```

#### **Core Parameters**

| Parameter | Default | Description |
|-----------|---------|-------------|
| `model_path` | `"./llama_models"` | Directory containing GGUF model files |
| `n_ctx` | `4096` | Context window size (tokens) |
| `n_batch` | `128` | Batch size for processing |
| `n_threads` | `8` | CPU threads to use |
| `n_gpu_layers` | `0` | GPU layers to offload (0 = CPU only) |
| `verbose` | `false` | Enable verbose logging |

#### **Memory Management**

| Parameter | Default | Description |
|-----------|---------|-------------|
| `use_mmap` | `true` | Use memory mapping for model files |
| `use_mlock` | `false` | Lock memory pages (prevents swapping) |

#### **Model-Specific Settings**

| Parameter | Default | Description |
|-----------|---------|-------------|
| `rope_scaling_type` | `"none"` | RoPE scaling type for position encoding |
| `rope_freq_base` | `10000.0` | RoPE frequency base for position encoding |
| `rope_freq_scale` | `1.0` | RoPE frequency scaling factor |

### **Backend Use Cases**

#### **Ollama Backend - Best For:**
- **Cloud/Server Deployments** - Connect to remote Ollama instances
- **Model Management** - Easy model downloading and switching
- **API Compatibility** - Standard REST API interface
- **Multi-User Environments** - Shared model server
- **Development** - Quick prototyping and testing

#### **llama.cpp Backend - Best For:**
- **Local/Offline Use** - No internet connection required
- **Privacy** - All processing happens locally
- **Custom Models** - Use any GGUF quantized model
- **Resource Control** - Fine-tune memory and CPU usage
- **Edge Deployments** - Embedded or resource-constrained systems

### **Configuration Examples**

#### **Ollama Primary with llama.cpp Fallback**
```json
{
  "backend": {
    "active": "ollama",
    "auto_fallback": true,
    "health_check_interval": 30
  },
  "ollama": {
    "base_url": "http://localhost:11434",
    "timeout": 300,
    "connect_timeout": 30
  },
  "llamacpp": {
    "model_path": "./llama_models",
    "n_ctx": 2048,
    "n_batch": 64,
    "n_gpu_layers": 0
  }
}
```

#### **llama.cpp Primary (Offline Setup)**
```json
{
  "backend": {
    "active": "llamacpp",
    "auto_fallback": false,
    "health_check_interval": 60
  },
  "llamacpp": {
    "model_path": "./llama_models",
    "n_ctx": 4096,
    "n_batch": 128,
    "n_threads": 8,
    "n_gpu_layers": 32,
    "use_mmap": true,
    "use_mlock": true
  }
}
```

#### **High-Performance GPU Setup**
```json
{
  "backend": {
    "active": "llamacpp",
    "auto_fallback": true
  },
  "llamacpp": {
    "model_path": "./llama_models",
    "n_ctx": 8192,
    "n_batch": 256,
    "n_threads": 16,
    "n_gpu_layers": 40,
    "use_mmap": true,
    "use_mlock": true
  }
}
```

---

## 🗜️ **Context Compression Configuration** ⭐ *New*

Configure intelligent conversation compression for optimal performance.

### **Compression Settings**

```json
{
  "compression": {
    "enabled": true,
    "strategy": "hybrid",
    "trigger_threshold": 0.8,
    "preserve_recent_messages": 5,
    "cache_ttl": 3600,
    "quality_threshold": 0.7
  }
}
```

| Parameter | Options | Default | Description |
|-----------|---------|---------|-------------|
| `enabled` | `true`, `false` | `true` | Enable automatic compression |
| `strategy` | `"rolling_window"`, `"intelligent_summary"`, `"hybrid"` | `"hybrid"` | Compression algorithm |
| `trigger_threshold` | `0.1-1.0` | `0.8` | Context usage ratio to trigger compression |
| `preserve_recent_messages` | Integer | `5` | Always keep N recent messages |
| `cache_ttl` | Integer (seconds) | `3600` | Compression cache lifetime |
| `quality_threshold` | `0.0-1.0` | `0.7` | Minimum compression quality score |

### **Compression Strategies**

#### **Rolling Window Strategy**
- **Best for:** Long conversations with consistent importance
- **Method:** Keeps recent messages, removes older ones
- **Settings:** `preserve_recent_messages`, importance thresholds

#### **Intelligent Summary Strategy**
- **Best for:** Conversations with key information scattered throughout
- **Method:** Uses AI to summarize less important sections
- **Settings:** `quality_threshold`, summary ratios

#### **Hybrid Strategy (Recommended)**
- **Best for:** Most use cases
- **Method:** Combines rolling window + intelligent summarization
- **Settings:** All compression parameters apply

---

## ⏱️ **Timeout Configuration**

Controls connection and response timing behavior.

### **Settings**

```json
{
  "timeouts": {
    "ollama_timeout": 180,
    "ollama_connect_timeout": 15
  }
}
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `ollama_timeout` | `180` | Maximum seconds to wait for AI response |
| `ollama_connect_timeout` | `15` | Maximum seconds to wait for connection |

### **Recommendations**

- **Fast responses**: Set `ollama_timeout` to `60-120` seconds
- **Complex queries**: Use `180-300` seconds
- **Slow networks**: Increase `ollama_connect_timeout` to `30`
- **Local setup**: Keep defaults or reduce timeouts

---

## 🤖 **Model Options**

Fine-tune AI model behavior and response characteristics.

### **Core Parameters**

```json
{
  "model_options": {
    "temperature": 0.5,
    "top_p": 0.8,
    "top_k": 30,
    "num_predict": 2048,
    "num_ctx": 4096,
    "repeat_penalty": 1.1,
    "stop": ["\n\nHuman:", "\n\nUser:"]
  }
}
```

### **Parameter Details**

| Parameter | Range | Default | Description |
|-----------|-------|---------|-------------|
| `temperature` | 0.0-2.0 | `0.5` | Response creativity (0=deterministic, 2=very creative) |
| `top_p` | 0.0-1.0 | `0.8` | Nucleus sampling threshold |
| `top_k` | 1-100 | `30` | Consider top K probable next tokens |
| `num_predict` | 1-8192 | `2048` | Maximum tokens to generate |
| `num_ctx` | 512-32768 | `4096` | Context window size |
| `repeat_penalty` | 0.5-2.0 | `1.1` | Penalty for repeating tokens |
| `stop` | Array | `["\n\nHuman:", "\n\nUser:"]` | Stop generation sequences |

### **Use Case Presets**

#### **Creative Writing**
```json
{
  "temperature": 0.8,
  "top_p": 0.9,
  "top_k": 50
}
```

#### **Code Generation**
```json
{
  "temperature": 0.2,
  "top_p": 0.7,
  "top_k": 20
}
```

#### **Analytical Tasks**
```json
{
  "temperature": 0.3,
  "top_p": 0.8,
  "top_k": 25
}
```

#### **Conversational Chat**
```json
{
  "temperature": 0.5,
  "top_p": 0.8,
  "top_k": 30
}
```

---

## ⚡ **Performance Configuration**

Optimize memory usage and processing speed.

### **Settings**

```json
{
  "performance": {
    "context_history_limit": 10,
    "batch_size": 1,
    "use_mlock": true,
    "use_mmap": true,
    "num_thread": -1,
    "num_gpu": 0
  }
}
```

### **Parameter Details**

| Parameter | Default | Description |
|-----------|---------|-------------|
| `context_history_limit` | `10` | Number of previous messages to include |
| `batch_size` | `1` | Batch processing size |
| `use_mlock` | `true` | Lock memory pages (prevents swapping) |
| `use_mmap` | `true` | Use memory mapping for efficiency |
| `num_thread` | `-1` | CPU threads (-1 = auto-detect) |
| `num_gpu` | `0` | GPU layers to offload (0 = CPU only) |

### **Memory Optimization**

#### **Low Memory Systems (<8GB RAM)**
```json
{
  "context_history_limit": 5,
  "use_mlock": false,
  "use_mmap": true,
  "num_thread": 2
}
```

#### **High Memory Systems (>16GB RAM)**
```json
{
  "context_history_limit": 20,
  "use_mlock": true,
  "use_mmap": true,
  "num_thread": -1
}
```

#### **GPU Acceleration**
```json
{
  "num_gpu": 32,
  "use_mlock": true,
  "num_thread": 8
}
```

---

## 🎭 **System Prompt Customization**

Define your AI assistant's personality and behavior.

### **Default System Prompt**
```json
{
  "system_prompt": "Your name is Bhaai, a helpful, friendly, and knowledgeable AI assistant. You have a warm personality and enjoy helping users solve problems. You're curious about technology and always try to provide practical, actionable advice. You occasionally use light humor when appropriate, but remain professional and focused on being genuinely helpful."
}
```

### **Custom Prompt Examples**

#### **Technical Expert**
```json
{
  "system_prompt": "You are a senior software architect with expertise in Python, web development, and system design. Provide detailed technical explanations with code examples when helpful. Focus on best practices, performance, and maintainability."
}
```

#### **Creative Writer**
```json
{
  "system_prompt": "You are a creative writing assistant specializing in storytelling, character development, and narrative structure. Help users develop compelling stories with vivid descriptions and engaging dialogue."
}
```

#### **Educational Tutor**
```json
{
  "system_prompt": "You are a patient and encouraging tutor. Break down complex concepts into digestible steps, provide examples, and ask clarifying questions to ensure understanding. Adapt your teaching style to the student's level."
}
```

---

## 🔄 **Response Optimization**

Control how responses are generated and delivered.

### **Settings**

```json
{
  "response_optimization": {
    "stream": false,
    "keep_alive": "5m",
    "low_vram": false,
    "f16_kv": true,
    "logits_all": false,
    "vocab_only": false,
    "use_mmap": true,
    "use_mlock": false,
    "embedding_only": false,
    "numa": false
  }
}
```

### **Parameter Details**

| Parameter | Default | Description |
|-----------|---------|-------------|
| `stream` | `false` | Stream response tokens (not implemented in UI) |
| `keep_alive` | `"5m"` | Keep model loaded in memory |
| `low_vram` | `false` | Optimize for low VRAM systems |
| `f16_kv` | `true` | Use 16-bit key-value cache |
| `logits_all` | `false` | Return logits for all tokens |
| `vocab_only` | `false` | Only load vocabulary |
| `use_mmap` | `true` | Use memory mapping |
| `use_mlock` | `false` | Lock model memory |
| `embedding_only` | `false` | Only generate embeddings |
| `numa` | `false` | NUMA optimization |

---

## 🌍 **Environment Variables**

Configure application runtime through environment variables.

### **Core Variables**

```bash
# Ollama Configuration
OLLAMA_API_URL=http://localhost:11434

# Database Configuration  
DATABASE_PATH=ollama_chat.db

# Flask Configuration
PORT=3113
DEBUG=false
SECRET_KEY=your-secret-key-change-this
```

### **Advanced Variables**

```bash
# Threading Configuration
FLASK_THREADED=true

# Security
FLASK_SECRET_KEY=your-production-secret-key

# Logging
LOG_LEVEL=INFO
LOG_FILE=chat-o-llama.log

# Development
FLASK_ENV=production
FLASK_DEBUG=false
```

### **Environment Setup Methods**

#### **Option 1: .env File**
Create a `.env` file in your project root:
```bash
OLLAMA_API_URL=http://localhost:11434
DATABASE_PATH=./data/ollama_chat.db
PORT=3113
DEBUG=false
```

#### **Option 2: System Environment**
```bash
export OLLAMA_API_URL=http://localhost:11434
export DATABASE_PATH=/path/to/database.db
export PORT=3113
```

#### **Option 3: Docker Environment**
```dockerfile
ENV OLLAMA_API_URL=http://ollama:11434
ENV DATABASE_PATH=/app/data/chat.db
ENV PORT=3113
```

---

## 🗄️ **Database Configuration**

Configure SQLite database settings and location.

### **Database Path Options**

```bash
# Relative path (default)
DATABASE_PATH=ollama_chat.db

# Absolute path
DATABASE_PATH=/var/lib/chat-o-llama/database.db

# Memory database (testing only)
DATABASE_PATH=:memory:
```

### **Database Optimization**

#### **Production Settings**
```python
# SQLite optimization settings (in app.py)
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA cache_size=10000;
PRAGMA temp_store=memory;
```

#### **Development Settings**
```python
PRAGMA journal_mode=DELETE;
PRAGMA synchronous=FULL;
```

---

## 🚀 **Deployment Configurations**

### **Development Setup**
```json
{
  "timeouts": {
    "ollama_timeout": 60,
    "ollama_connect_timeout": 10
  },
  "performance": {
    "context_history_limit": 5,
    "use_mlock": false
  },
  "model_options": {
    "temperature": 0.7,
    "num_predict": 1024
  }
}
```

### **Production Setup**
```json
{
  "timeouts": {
    "ollama_timeout": 180,
    "ollama_connect_timeout": 15
  },
  "performance": {
    "context_history_limit": 15,
    "use_mlock": true,
    "use_mmap": true
  },
  "model_options": {
    "temperature": 0.5,
    "num_predict": 2048,
    "num_ctx": 4096
  }
}
```

### **High-Performance Setup**
```json
{
  "timeouts": {
    "ollama_timeout": 300,
    "ollama_connect_timeout": 20
  },
  "performance": {
    "context_history_limit": 25,
    "use_mlock": true,
    "use_mmap": true,
    "num_thread": -1,
    "num_gpu": 32
  },
  "model_options": {
    "temperature": 0.5,
    "num_predict": 4096,
    "num_ctx": 8192
  }
}
```

---

## 🛠️ **Configuration Validation**

### **Testing Your Configuration**

```bash
# Test Ollama connection
curl http://localhost:11434/api/tags

# Test Flask app
python -c "from app import init_db; init_db()"

# Validate config.json
python -c "import json; print(json.load(open('config.json')))"
```

### **Common Configuration Issues**

| Issue | Symptom | Solution |
|-------|---------|----------|
| **Model not loading** | "No models available" | Check `OLLAMA_API_URL` and Ollama status |
| **Slow responses** | Timeouts or delays | Increase `ollama_timeout`, reduce `num_predict` |
| **Memory issues** | System slowdown | Reduce `context_history_limit`, disable `use_mlock` |
| **JSON errors** | Config not loading | Validate JSON syntax in `config.json` |
| **Database errors** | Conversation not saving | Check `DATABASE_PATH` permissions |

### **Performance Tuning**

#### **CPU-Optimized**
```json
{
  "performance": {
    "num_thread": -1,
    "num_gpu": 0,
    "use_mmap": true,
    "use_mlock": false
  }
}
```

#### **GPU-Optimized**
```json
{
  "performance": {
    "num_gpu": 32,
    "num_thread": 4,
    "use_mlock": true
  }
}
```

#### **Memory-Constrained**
```json
{
  "performance": {
    "context_history_limit": 3,
    "use_mlock": false,
    "low_vram": true
  },
  "model_options": {
    "num_ctx": 2048,
    "num_predict": 1024
  }
}
```

---

## 📝 **Configuration Templates**

### **Minimal Configuration**
```json
{
  "model_options": {
    "temperature": 0.5
  }
}
```

### **Balanced Configuration**
```json
{
  "timeouts": {
    "ollama_timeout": 120
  },
  "model_options": {
    "temperature": 0.5,
    "num_predict": 2048
  },
  "performance": {
    "context_history_limit": 10
  }
}
```

### **Maximum Configuration**
```json
{
  "timeouts": {
    "ollama_timeout": 300,
    "ollama_connect_timeout": 20
  },
  "model_options": {
    "temperature": 0.5,
    "top_p": 0.8,
    "top_k": 30,
    "num_predict": 4096,
    "num_ctx": 8192,
    "repeat_penalty": 1.1,
    "stop": ["\n\nHuman:", "\n\nUser:", "\n\nAssistant:"]
  },
  "performance": {
    "context_history_limit": 20,
    "batch_size": 1,
    "use_mlock": true,
    "use_mmap": true,
    "num_thread": -1,
    "num_gpu": 32
  },
  "system_prompt": "You are an expert AI assistant with deep knowledge across multiple domains. Provide detailed, accurate, and helpful responses.",
  "response_optimization": {
    "stream": false,
    "keep_alive": "10m",
    "low_vram": false,
    "f16_kv": true,
    "use_mmap": true,
    "use_mlock": true
  }
}
```

---

*For more information about Ollama model parameters, visit the [Ollama documentation](https://github.com/ollama/ollama/blob/main/docs/modelfile.md#parameter).*