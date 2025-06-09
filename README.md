# chat-o-llama 🦙

**Your private, local AI chatbot**

*No GPU? No cloud? No problem!*

![Interface-Local GUI-blue](https://img.shields.io/badge/Interface-Local_GUI-blue) ![Python](https://img.shields.io/badge/Python-3.8%2B-green) ![License](https://img.shields.io/badge/License-MIT-yellow) ![Offline-Capable](https://img.shields.io/badge/Offline-100%25-brightgreen)

A lightweight **PyQt GUI** for running Ollama/llama.cpp models **completely offline**. Perfect for privacy-focused users and low-end hardware.

## ✨ Why Choose chat-o-llama?

| Feature | chat-o-llama | Alternatives |
|---------|-------------|--------------|
| 🔒 **Privacy** | All data stays on your machine | Often cloud-dependent |
| 💻 **Lightweight** | Runs on CPUs with ~8GB RAM | Heavy Electron apps |
| 🚫 **No Internet** | Works 100% offline | Needs web connection |

## 🚀 30-Second Quick Start

**For most users (auto-install):**

```bash
curl -fsSL https://github.com/ukkit/chat-o-llama/raw/main/install.sh | bash
```

What happens?
- Installs Python/Ollama if missing (takes time)
- Downloads recommended model (~380MB)
- Installs chat-o-llama
Access at: ```http://localhost:3000```

<details> <summary><b>🔧 Advanced Setup (Manual Install)</b></summary>

For detailed manual installation steps, see **[install.md](./docs/install.md)**

```bash
git clone https://github.com/ukkit/chat-o-llama.git
cd chat-o-llama
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
./chat-manager.sh start
```

</details>

## 🌐 100% Offline Usage

1. Download models beforehand:

```bash
  ollama pull tinyllama
  Start in offline mode:
  ```

2. Start in offline mode

  ```bash
  OLLAMA_HOST=0.0.0.0 ollama serve
  Launch chat-o-llama:
  ```

3. Activate python virtual environment

  ```bash
  source /venv/bin/activate
  ```

4. Launch chat-o-llama

  ```bash
  ./chat-manager.sh start
```

## 🛠️ Need Help?

Quick Fixes:

- Port in use? → ./chat-manager.sh start 8080
- No models? → ollama pull tinyllama

## 📚 Documentation Links

| Document | Description |
|---------|-------------|
| [Installation Guide](./docks/install.md) | Installation Guide |
| [Startup & Process Guide](./docks/chat_manager_docs.md) | Startup & Process Management via chat-manager.sh |
| [Config Guide](./docs/config.md) | Configuration Guide |
| [Config Comparison](./docs/config_comparison.md) | Compare different configs |
| [API Guide](./docs/api.md) | API Guide |
| [Troubleshooting Guide](./docs/troubleshooting.md) | Troubleshooting Guide |

## ✔️ Tested On (Hardware)

| Device | CPU | RAM | OS |
|---------|-------------|---------|-------------|
| Raspberry Pi 4 Model B Rev 1.4 | ARM Cortex-A72 | 8GB | Raspberry Pi OS |
| Dell Optiplex 3070 | i3-9100T | 8GB | Debian 12 |
| Nokia Purebook X14 | i5-10210U | 16 GB | Windows 11 Home |


## 🙏 Acknowledgments

- [Ollama](https://ollama.ai/) - Local AI platform
- [Flask](https://flask.palletsprojects.com/) - Web framework

**Made with ❤️ for the AI community**

> ⭐ Star this project if you find it helpful!

---

MIT License - see [LICENSE](LICENSE) file.