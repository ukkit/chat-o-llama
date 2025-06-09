# chat-o-llama 🦙 Configuration Guide

Complete configuration reference for customizing your chat-o-llama installation.

## 📋 **Quick Reference**

| Configuration Type | File/Method | Purpose |
|-------------------|------------|---------|
| **Runtime Settings** | `config.json` | Model parameters, timeouts, performance |
| **Environment** | Environment Variables | Server URLs, paths, debugging |
| **Database** | `DATABASE_PATH` | SQLite database location |
| **Ollama** | `OLLAMA_API_URL` | Ollama server connection |

---

## 🔧 **Runtime Configuration (config.json)**

Create a `config.json` file in your project root to customize application behavior.

### **Complete Configuration Example**

```json
{
  "timeouts": {
    "ollama_timeout": 180,
    "ollama_connect_timeout": 15
  },
  "model_options": {
    "temperature": 0.5,
    "top_p": 0.8,
    "top_k": 30,
    "num_predict": 2048,
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
PORT=8080
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
PORT=8080
DEBUG=false
```

#### **Option 2: System Environment**
```bash
export OLLAMA_API_URL=http://localhost:11434
export DATABASE_PATH=/path/to/database.db
export PORT=8080
```

#### **Option 3: Docker Environment**
```dockerfile
ENV OLLAMA_API_URL=http://ollama:11434
ENV DATABASE_PATH=/app/data/chat.db
ENV PORT=8080
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