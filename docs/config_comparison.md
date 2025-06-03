# Configuration Comparison Guide 🎯

## Speed vs Precision: Choose Your Configuration

Chat-o-llama now supports different configuration profiles optimized for different use cases. Here's how to choose:

## 🚀 Speed Configuration (config-performance.json)
**Best for:** Quick responses, casual chat, limited hardware

```json
{
  "timeouts": { "ollama_timeout": 120 },
  "model_options": {
    "temperature": 0.3,
    "num_predict": 1024,
    "num_ctx": 2048,
    "min_p": 0.05,
    "typical_p": 0.8
  },
  "performance": {
    "context_history_limit": 5,
    "num_batch": 2
  }
}
```

**Trade-offs:**
- ✅ 2-3x faster responses
- ✅ Lower memory usage
- ✅ Better for CPU-only systems
- ❌ Shorter responses
- ❌ Less context awareness
- ❌ May miss nuanced details

---

## 🎯 Precision Configuration (config-precision.json)
**Best for:** Research, complex questions, detailed analysis

```json
{
  "timeouts": { "ollama_timeout": 600 },
  "model_options": {
    "temperature": 0.1,
    "num_predict": 4096,
    "num_ctx": 8192,
    "min_p": 0.01,
    "typical_p": 0.95
  },
  "performance": {
    "context_history_limit": 15,
    "num_batch": 1
  }
}
```

**Trade-offs:**
- ✅ More accurate responses
- ✅ Better reasoning and analysis
- ✅ Longer, detailed answers
- ✅ Better context retention
- ❌ 3-5x slower responses
- ❌ Higher memory usage
- ❌ May require more powerful hardware

---

## 📊 Parameter Comparison

| Parameter | Speed Config | Precision Config | Impact |
|-----------|--------------|------------------|---------|
| **Response Time** | ~10-30 sec | ~30-120 sec | Response speed |
| **Memory Usage** | ~2-4 GB | ~4-8 GB | RAM requirements |
| **Context Length** | 2048 tokens | 8192 tokens | Conversation memory |
| **Response Length** | ~500 words | ~2000 words | Answer detail |
| **Temperature** | 0.3 | 0.1 | Creativity vs accuracy |
| **History Limit** | 5 messages | 15 messages | Context awareness |

---

## 🔧 How to Switch Configurations

### Method 1: Replace config.json
```bash
# For speed (default)
cp config-performance.json config.json

# For precision
cp config-precision.json config.json

# Restart application
./chat-manager.sh restart
```

### Method 2: Rename files
```bash
# Current: config.json (speed)
# Switch to precision:
mv config.json config-speed-backup.json
mv config-precision.json config.json
./chat-manager.sh restart
```

---

## 💡 Usage Recommendations

### Use Speed Configuration When:
- 🏃 Quick questions and casual chat
- 💻 Running on older/limited hardware (Dell Optiplex, etc.)
- ⚡ You need immediate responses
- 📱 Mobile or low-bandwidth environments
- 🔄 High-frequency interactions

### Use Precision Configuration When:
- 🔬 Research and analysis tasks
- 📝 Writing and content creation
- 🧮 Complex problem solving
- 📚 Educational and learning purposes
- 🎯 When accuracy is more important than speed

---

## 🔍 Fine-Tuning Your Configuration

### For Balanced Performance:
```json
{
  "model_options": {
    "temperature": 0.2,
    "num_predict": 2048,
    "num_ctx": 4096
  },
  "performance": {
    "context_history_limit": 8
  }
}
```

### For Specific Hardware:

**8GB RAM Systems:**
- Use speed config with `num_ctx: 3072`

**16GB+ RAM Systems:**
- Use precision config safely

**GPU Available:**
```json
{
  "performance": {
    "num_gpu": 1,
    "low_vram": false
  }
}
```

---

## ⚙️ Configuration Validation

Test your configuration:
```bash
# Validate JSON syntax
python -m json.tool config.json

# Test with API
curl http://localhost:3000/api/config

# Monitor performance
./chat-manager.sh logs | grep "duration"
```

Choose the configuration that best matches your hardware capabilities and use case requirements!