# chat-o-llama 🦙

A lightweight web interface for [Ollama](https://ollama.ai/) with persistent chat history, conversation management, and advanced configuration options.

![Ollama Chat Interface](https://img.shields.io/badge/Interface-Web%20Based-blue) ![Python](https://img.shields.io/badge/Python-3.8%2B-green) ![License](https://img.shields.io/badge/License-MIT-yellow)

## ✨ Features

- 💬 **Multiple Conversations** - Create, manage, and rename chat sessions
- 📚 **Persistent History** - SQLite database storage with search functionality
- 🤖 **Model Selection** - Choose from available Ollama models
- ⚙️ **Advanced Configuration** - JSON-based configuration with performance optimization
- 📱 **Responsive Design** - Works on desktop and mobile
- 🚀 **Lightweight** - Minimal resource usage for local development
- 🎯 **Process Management** - Easy start/stop with background service management


![chat-o-llama - Select model](screenshot_1.png)
select Model from drop-down

![chat-o-llama - Start new chat ](screenshot_2.png)
Started a new chat

![chat-ol-llama - Generate response](screenshot_3.png)
waiting for response from ollama

## 🚀 Quick Start

### Prerequisites

- Python 3.8+, [Ollama](https://ollama.ai/) installed with at least one model downloaded

### Installation & Setup

```bash
# Clone and setup
git clone https://github.com/ukkit/chat-o-llama.git
cd chat-o-llama
python3 -m venv chat-o-llama
source bin/activate
pip install -r requirements.txt
chmod +x chat-manager.sh

# Start the application
./chat-manager.sh start

# Access at http://localhost:3000
```

## 📋 Usage

**⚠️ Important: Always activate virtual environment first: `source bin/activate`**

### Process Management

```bash
./chat-manager.sh start [port]    # Start (default port 3000)
./chat-manager.sh status          # Check status
./chat-manager.sh stop           # Stop gracefully
./chat-manager.sh force-stop     # Force kill
./chat-manager.sh restart        # Restart
./chat-manager.sh logs           # View logs
./chat-manager.sh help           # Show help
```

### First Time Setup

```bash
# Start Ollama and download a model
ollama serve
ollama pull phi3:mini      # 3.8GB - recommended balance
ollama pull gemma2:2b      # 1.6GB - smaller option
ollama pull tinyllama      # 637MB - ultra lightweight
```

## 🔧 Configuration

### JSON Configuration File

Chat-o-llama supports advanced configuration through a `config.json` file. The application will automatically create a default configuration or load your custom settings.

#### Quick Performance Setup

The default `config.json` is precision optimized for CPU-only systems:

```json
{
  "timeouts": {
    "ollama_timeout": 600,
    "ollama_connect_timeout": 45
  },
  "model_options": {
    "temperature": 0.1,
    "top_p": 0.95,
    "top_k": 50,
    "min_p": 0.01,
    "typical_p": 0.95,
    "num_predict": 4096,
    "num_ctx": 8192,
    "repeat_penalty": 1.15,
    "repeat_last_n": 64,
    "presence_penalty": 0.0,
    "frequency_penalty": 0.0,
    "penalize_newline": false,
    "stop": ["\n\nHuman:", "\n\nUser:"],
    "seed": null
  },
  "performance": {
    "context_history_limit": 15,
    "num_thread": -1,
    "num_gpu": 0,
    "main_gpu": 0,
    "num_batch": 1,
    "num_keep": 10,

  },
  "system_prompt": "You are Dost, a knowledgeable and thoughtful AI assistant. Take time to provide detailed, accurate, and well-reasoned responses. Consider multiple perspectives and provide comprehensive information when helpful.",
  "response_optimization": {
    "stream": false,
    "keep_alive": "10m",
    "low_vram": false,
    "f16_kv": false,

  }
}
```

#### Configuration API

Access current configuration via API:

```bash
curl http://localhost:3000/api/config
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `3000` | Web server port |
| `OLLAMA_API_URL` | `http://localhost:11434` | Ollama server URL |
| `DATABASE_PATH` | `chat-o-llama.db` | SQLite database path |
| `DEBUG` | `False` | Debug mode |

### Custom Configuration

```bash
# Use different port or remote Ollama
PORT=8080 ./chat-manager.sh start
export OLLAMA_API_URL="http://192.168.1.100:11434"
```

## ⚡ Performance Optimization

### For CPU-Only Systems (Recommended)

The default `config.json` is perfomance optimized for CPU-only systems like the Dell Optiplex series.

For faster response, you can use `speed_config.json` file:

**Key Optimizations:**
- **Faster Sampling**: Uses `min_p` + `typical_p` instead of `top_p`/`top_k` for 10-20% speed improvement
- **Reduced Context**: `num_ctx: 2048` and `num_predict: 1024` for faster responses
- **CPU Optimization**: `low_vram: true`, `num_batch: 2` for better multi-core utilization
- **Memory Efficient**: `context_history_limit: 5` for faster processing

### For GPU Systems

Modify `config.json` for GPU acceleration:
```json
{
  "performance": {
    "num_gpu": 1,
    "main_gpu": 0,
    "low_vram": false
  },
  "model_options": {
    "num_ctx": 4096,
    "num_predict": 2048
  }
}
```

### Traditional Ollama Environment Variables

**For low-resource systems:**
```bash
export OLLAMA_NUM_PARALLEL=1
export OLLAMA_MAX_LOADED_MODELS=1
export OLLAMA_KEEP_ALIVE=5m
```

## 🛠️ API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/models` | Available models |
| GET | `/api/config` | Current configuration |
| GET/POST | `/api/conversations` | List/create conversations |
| GET/DELETE | `/api/conversations/{id}` | Get/delete conversation |
| POST | `/api/chat` | Send message |
| GET | `/api/search?q={query}` | Search conversations |

## 🔍 Troubleshooting

| Issue | Solution |
|-------|----------|
| Port in use | `./chat-manager.sh start 8080` |
| Process won't stop | `./chat-manager.sh force-stop` |
| Ollama not responding | `curl http://localhost:11434/api/tags` |
| No models | `ollama pull phi3:mini` |
| Permission denied | `chmod +x chat-manager.sh` |
| Dependencies missing | `pip install -r requirements.txt` |
| Slow responses | Create optimized `config.json` (see Configuration) |
| Config errors | Check JSON syntax with `python -m json.tool config.json` |

### Debug Mode

```bash
source bin/activate
DEBUG=true ./chat-manager.sh start
./chat-manager.sh logs
```

### Reset Database

```bash
./chat-manager.sh stop
rm -f data/chat-o-llama.db
./chat-manager.sh start
```

## 📁 Project Structure

```
chat-o-llama/
├── chat-manager.sh             # Process manager
├── app.py                      # Flask application
├── config.json                 # Default Configuration file
├── speed_config.json           # Configuration file for speed over precision
├── requirements.txt            # Dependencies
├── templates/index.html        # Web interface
├── docs/configuration.md       # Ollama configuration variables
├── docs/config_comparison.md   # Comparison of different ollama configurations
├── data/                       # Database (auto-created)
└── logs/                       # Logs direcotry (auto created)
```

## 🎛️ Configuration Reference

- For detailed configuration explanations, see the [Configuration Guide](docs/configuration.md).

- For detailed comparision between default config.json and speed_config.json, see the [Configuration Comparision Guide](docs/config_comparison_guide.md)

## 📄 License

MIT License - see [LICENSE](LICENSE) file.

## 🙏 Acknowledgments

- [Ollama](https://ollama.ai/) - Local AI platform
- [Flask](https://flask.palletsprojects.com/) - Web framework

**Made with ❤️ for the AI community**

> ⭐ Star this project if you find it helpful!