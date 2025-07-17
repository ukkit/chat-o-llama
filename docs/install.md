# 📦 Complete Installation Guide

This guide provides both automatic and manual installation methods for chat-o-llama.

## ⚡ Prerequisites for Fastest Setup

**For quickest installation (< 2 minutes), have these ready:**
- **Python 3.10+** with uv package manager (automatically installed if missing)
- **AI Backend** (choose one or both):
  - **Ollama** running with at least one model downloaded
  - **GGUF models** for llama.cpp local inference (use built-in download utility)
- **git** (usually pre-installed on most systems)
- **Sufficient RAM** - 4GB minimum, 8GB+ recommended for larger models

**Quick prerequisite check:**
```bash
python3 --version          # Should show 3.10 or higher
uv --version               # Should show uv version (auto-installed if missing)

# For Ollama backend:
ollama --version           # Should show Ollama version
ollama list                # Should show at least one model

# For llama.cpp backend (optional):
ls llama_models/*.gguf     # Should show GGUF model files

git --version              # Should show git version
```

**Installation time estimates:**
- **✅ With all prerequisites:** ~2 minutes
- **⏳ Missing some prerequisites:** ~5-10 minutes
- **📥 Fresh system (nothing installed):** ~10-20 minutes

---

## 🚀 Method 1: Automatic Installation (Recommended)

### One-Command Installation

**The easiest way to install chat-o-llama:**

```bash
curl -fsSL https://github.com/ukkit/chat-o-llama/raw/main/install.sh | bash
```

**Alternative methods:**
```bash
# Using wget
wget -O- https://github.com/ukkit/chat-o-llama/raw/main/install.sh | sh

# Download and inspect first (recommended for security)
curl -O https://github.com/ukkit/chat-o-llama/raw/main/install.sh
cat install.sh  # Review the script
chmod +x install.sh
./install.sh
```

### What the Auto-Installer Does

**✅ Smart Detection & Installation:**
- **Checks for Python 3.10+** - Installs if missing or too old
- **Installs uv package manager** - Modern, fast Python package manager
- **Checks for Ollama** - Downloads and installs if not found
- **Checks for git** - Installs if missing
- **Validates all tools** - Ensures everything works before proceeding

**✅ Efficient Setup:**
- **Downloads chat-o-llama** from GitHub (lightweight)
- **Creates virtual environment** using uv (faster than venv)
- **Installs dependencies** using uv (Flask, requests, llama-cpp-python)
- **Compiles llama.cpp** (automatic compilation for your platform)
- **Sets up permissions** (makes scripts executable)

**✅ Model Management:**
- **Checks existing models** - Uses what you already have
- **Recommends qwen2.5:0.5b** (~380MB, fastest)
- **Provides alternatives** if download fails
- **Skips download** if you prefer to install models later

**✅ Service Launch:**
- **Starts automatically** on available port (default: 3113)
- **Provides access URL** and management commands
- **Shows next steps** and usage instructions

### Installation Time Breakdown

**With Prerequisites Present:**
```
Downloading chat-o-llama     : 10-30 seconds
Setting up environment       : 15-30 seconds (uv is faster)
Installing Python packages   : 30-90 seconds (uv is much faster)
Compiling llama.cpp bindings : 2-5 minutes (first time only)
Starting application         : 5-10 seconds
Total                        : ~3-6 minutes
```

**Installing Prerequisites:**
```
Installing Python (if needed): 2-5 minutes
Installing uv (if needed)    : 30-60 seconds
Installing Ollama (if needed): 1-3 minutes
Downloading model (if needed) : 2-10 minutes (depends on model size)
Setting up chat-o-llama      : 3-6 minutes (includes compilation)
Total                        : 8-25 minutes
```

**⚠️ Note:** llama-cpp-python compilation time varies significantly by hardware:
- **Fast modern CPU**: 2-3 minutes
- **Older/slower CPU**: 5-10 minutes
- **With GPU support**: 3-8 minutes (includes CUDA/OpenCL setup)

### Expected Output

**With Prerequisites:**
```
╔══════════════════════════════════════╗
║           chat-o-llama 🦙            ║
║        Auto Installer Script        ║
╚══════════════════════════════════════╝

✓ Python 3.11.2 found at /usr/bin/python3
✓ Ollama found at /usr/local/bin/ollama
✓ Ollama service is running
✓ Found existing models: qwen2.5:0.5b
✓ chat-o-llama downloaded successfully
✓ Virtual environment created
✓ Dependencies installed successfully
✓ chat-o-llama started successfully!

🎉 Installation Complete! 🎉
Access at: http://localhost:3113
```

**Without Prerequisites:**
```
╔══════════════════════════════════════╗
║           chat-o-llama 🦙            ║
║        Auto Installer Script        ║
╚══════════════════════════════════════╝

⚠ Python 3.8+ not found, installing...
✓ Python 3.11.2 installed successfully
⚠ Ollama not found, installing...
✓ Ollama installed successfully
⚠ No models found, downloading qwen2.5:0.5b...
✓ Model downloaded successfully (~380MB)
✓ chat-o-llama downloaded successfully
✓ Virtual environment created
✓ Dependencies installed successfully
✓ chat-o-llama started successfully!

🎉 Installation Complete! 🎉
Access at: http://localhost:3113
```

### Post-Installation

After automatic installation, you can manage the service with:

```bash
cd ~/chat-o-llama
source venv/bin/activate
./chat-manager.sh status    # Check status
./chat-manager.sh stop      # Stop service
./chat-manager.sh restart   # Restart service
./chat-manager.sh logs      # View logs
```

---

## 📥 GGUF Model Download Utility

Chat-O-Llama includes a built-in utility for downloading GGUF models from HuggingFace:

### Quick Usage

```bash
# Download a single model
./download-gguf.sh download https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf

# Download multiple models from curated list
./download-gguf.sh batch models.txt

# Check model directory and configuration
./download-gguf.sh info

# List all downloaded models
./download-gguf.sh list
```

### Features

- **Automatic model directory detection** from `config.json`
- **URL validation** for HuggingFace repositories
- **File integrity verification** (GGUF magic bytes, size checks)
- **Progress tracking** with colored output
- **Batch downloads** from URL lists
- **Custom filename** support
- **Comprehensive error handling**

### Curated Model List

The `models.txt` file includes pre-selected GGUF models:

```bash
# Small models (< 1GB) - uncommented by default
https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf

# Medium models (1-5GB) - commented out, uncomment to use
# https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf

# Large models (5GB+) - commented out, uncomment to use
# https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf
```

### Advanced Usage

```bash
# Download with custom filename
./download-gguf.sh download https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf my-model.gguf

# Create custom URL list with filenames
echo "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf|qwen-small.gguf" > my-models.txt
./download-gguf.sh batch my-models.txt

# Override config file location
CONFIG_FILE=/path/to/config.json ./download-gguf.sh info
```

---

## 🔧 Method 2: Manual Installation

### Prerequisites Installation

**If you want the fastest setup, install these first:**

#### Ubuntu/Debian
```bash
# Install Python 3.8+ with essential modules
sudo apt update
sudo apt install python3 python3-pip python3-venv git curl

# Verify Python version (should be 3.8+)
python3 --version

# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Download a model for immediate use
ollama pull qwen2.5:0.5b  # ~380MB, recommended starter
```

#### CentOS/RHEL/Fedora
```bash
# Install Python 3.8+ and tools
sudo yum install python3 python3-pip git curl
# OR for newer versions
sudo dnf install python3 python3-pip git curl

# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Download a model
ollama pull qwen2.5:0.5b
```

#### macOS
```bash
# Install Homebrew if not installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python and git
brew install python3 git

# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh
# OR download from https://ollama.ai/download

# Download a model
ollama pull qwen2.5:0.5b
```

#### Windows (WSL2 recommended)
```bash
# Enable WSL2 and install Ubuntu
# Then follow Ubuntu instructions above
```

### Quick Setup (With Prerequisites Ready)

**Time estimate: ~3-7 minutes** ⭐ *Updated*

```bash
# 1. Download chat-o-llama
git clone https://github.com/ukkit/chat-o-llama.git
cd chat-o-llama

# 2. Create and activate virtual environment using uv
uv venv venv
source venv/bin/activate

# 3. Install dependencies using uv (includes llama-cpp-python compilation)
uv sync

# ⚠️ Note: llama-cpp-python will compile during installation
# This may take 2-5 minutes depending on your CPU

# 4. Make script executable and start
chmod +x chat-manager.sh
./chat-manager.sh start

# 5. Access the application
# Open browser to http://localhost:3113
```

### Complete Manual Installation (Fresh System)

**Time estimate: ~15-30 minutes** ⭐ *Updated for compilation*

#### Step 1: Install Python 3.8+

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv git curl
python3 --version  # Verify 3.8+
```

**CentOS/RHEL:**
```bash
sudo yum install python3 python3-pip git curl
python3 --version  # Verify 3.8+
```

**macOS:**
```bash
brew install python3 git
python3 --version  # Verify 3.8+
```

#### Step 2: Install Ollama and Model

```bash
# Install Ollama (all platforms)
curl -fsSL https://ollama.ai/install.sh | sh

# Start Ollama service
ollama serve &

# Verify Ollama is running
ollama list

# Download recommended model (~380MB)
ollama pull qwen2.5:0.5b

# Verify model downloaded
ollama list  # Should show qwen2.5:0.5b
```

#### Step 2B: Setup llama.cpp Models (Alternative/Additional)

**Option 1: Use Built-in GGUF Download Utility (Recommended)**

```bash
# Download single GGUF model
./download-gguf.sh download https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf

# Download multiple models from curated list
./download-gguf.sh batch models.txt

# Check where models are stored
./download-gguf.sh info

# List downloaded models
./download-gguf.sh list

# Show available commands
./download-gguf.sh help
```

**Option 2: Manual Download**

```bash
# Create models directory
mkdir -p llama_models

# Download GGUF models manually
wget -O llama_models/qwen2.5-0.5b-instruct-q4_k_m.gguf \
  "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf"

# Or copy existing GGUF files
cp /path/to/your/model.gguf llama_models/

# Verify models are accessible
ls -la llama_models/*.gguf
```

**Popular GGUF Model Sources:**
- [Hugging Face GGUF models](https://huggingface.co/models?search=gguf)
- [TheBloke quantized models](https://huggingface.co/TheBloke)
- [Qwen GGUF models](https://huggingface.co/Qwen) - Recommended starter models
- Convert your own models using llama.cpp tools

**Curated Models in models.txt:**
The project includes a `models.txt` file with pre-selected GGUF models:
- **Small Models (< 1GB)**: Qwen2.5-0.5B-Instruct-GGUF
- **Medium Models (1-5GB)**: Qwen2.5-1.5B-Instruct-GGUF
- **Large Models (5GB+)**: Qwen2.5-3B/7B models (commented out)

**Model Size Guidelines:**
- **Q4_0 models**: Good balance of speed and quality
- **Q5_1 models**: Better quality, larger size
- **Q2_K models**: Fastest, lowest quality
- **For 8GB RAM**: Use Q4_0 models up to 7B parameters
- **For 16GB+ RAM**: Use Q5_1 models or larger models

#### Step 3: Install chat-o-llama

```bash
# Clone repository
git clone https://github.com/ukkit/chat-o-llama.git
cd chat-o-llama

# Create virtual environment using uv
uv venv venv
source venv/bin/activate

# Install dependencies using uv
uv sync

# Make scripts executable
chmod +x chat-manager.sh

# Start application
./chat-manager.sh start
```

#### Step 4: Verify Installation

```bash
# Check if application is running
./chat-manager.sh status

# Test API
curl http://localhost:3113/api/models

# Open in browser
# http://localhost:3113
```

---

## ⚡ Speed Optimization Tips

### For 2-Minute Setup
```bash
# 1. Pre-install everything first
sudo apt update && sudo apt install python3 python3-pip python3-venv git
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull qwen2.5:0.5b

# 2. Then run installer (will be super fast)
curl -fsSL https://github.com/ukkit/chat-o-llama/raw/main/install.sh | sh
```

### Model Download Time Estimates
| Model | Size | Download Time* | Performance |
|-------|------|----------------|-------------|
| qwen2.5:0.5b | ~380MB | 1-3 minutes | Fast, good quality |
| tinyllama | ~637MB | 2-5 minutes | Ultra lightweight |
| llama3.2:1b | ~1.3GB | 3-8 minutes | Better quality |
| phi3:mini | ~2.3GB | 5-15 minutes | Excellent balance |

*Depends on internet speed

### Internet Connection Impact
- **Fast connection (50+ Mbps):** Full setup in 5-10 minutes
- **Medium connection (10-50 Mbps):** Full setup in 10-15 minutes
- **Slow connection (<10 Mbps):** Consider pre-downloading models

### Hardware Performance Tips
```bash
# For systems with limited resources
ollama pull qwen2.5:0.5b  # Use smallest model
cp speed_config.json config.json  # Use speed-optimized config

# For powerful systems
ollama pull phi3:mini  # Use higher quality model
# Keep default config.json for best quality
```

---

## 🔍 Troubleshooting Installation

### Common Issues and Solutions

#### Python Issues
```bash
# Python command not found
sudo apt install python3  # Ubuntu/Debian
brew install python3      # macOS

# uv not found or installation failed
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.cargo/bin:$PATH"

# uv command not available after installation
source ~/.bashrc  # or restart terminal
export PATH="$HOME/.cargo/bin:$PATH"
```

#### Ollama Issues
```bash
# Ollama command not found
curl -fsSL https://ollama.ai/install.sh | sh

# Ollama service not running
ollama serve  # Manual start
sudo systemctl start ollama  # Systemd

# Connection refused
netstat -tulpn | grep 11434  # Check if port is open
curl http://localhost:11434/api/tags  # Test connection
```

#### Permission Issues
```bash
# Script not executable
chmod +x chat-manager.sh install.sh

# Directory permissions
sudo chown -R $USER:$USER ~/chat-o-llama
```

#### Port Issues
```bash
# Port already in use
./chat-manager.sh start 3113  # Use different port
sudo lsof -i :3113  # Check what's using port 3113
```

#### Memory Issues
```bash
# For low-memory systems, use smaller models
ollama pull qwen2.5:0.5b  # Only ~380MB

# Use speed config for less memory
cp speed_config.json config.json
./chat-manager.sh restart
```

#### llama-cpp-python Compilation Issues ⭐ *New*
```bash
# Compilation failed during pip install
pip install --upgrade pip setuptools wheel
pip install llama-cpp-python --no-cache-dir

# For systems with limited resources
export CMAKE_ARGS="-DLLAMA_BLAS=OFF -DLLAMA_CUBLAS=OFF"
pip install llama-cpp-python --no-cache-dir

# For GPU support (NVIDIA)
export CMAKE_ARGS="-DLLAMA_CUBLAS=ON"
pip install llama-cpp-python --no-cache-dir

# If compilation is too slow, use pre-built wheels
pip install --index-url https://abetlen.github.io/llama-cpp-python/whl/cpu llama-cpp-python
```

#### GGUF Model Issues ⭐ *New*
```bash
# Model not found
ls -la llama_models/  # Check if .gguf files exist
chmod 644 llama_models/*.gguf  # Fix permissions

# Model loading errors
# Check model path in config.json
grep -A 5 "llamacpp" config.json

# Test model compatibility
python3 -c "from llama_cpp import Llama; print('llama-cpp-python works')"
```

### Debug Mode

```bash
# Enable debug logging
export DEBUG=true
./chat-manager.sh start

# View detailed logs
./chat-manager.sh logs
tail -f logs/chat-o-llama_*.log
```

### Reinstall/Reset

```bash
# Complete reinstall
rm -rf ~/chat-o-llama
curl -fsSL https://github.com/ukkit/chat-o-llama/raw/main/install.sh | sh

# Reset only database
./chat-manager.sh stop
rm -f data/chat-o-llama.db
./chat-manager.sh start

# Reset only virtual environment
rm -rf venv
uv venv venv
source venv/bin/activate
uv sync
```

---

## 📋 Verification Checklist

After installation, verify everything works:

- [ ] **Python**: `python --version` shows 3.8+
- [ ] **Ollama**: `ollama list` shows available models
- [ ] **Service**: `./chat-manager.sh status` shows running
- [ ] **Web Interface**: http://localhost:3113 loads
- [ ] **API**: `curl http://localhost:3113/api/models` returns models
- [ ] **Chat**: Can select model and send test message

---

## 🔄 Updates and Maintenance

### Update chat-o-llama

```bash
cd ~/chat-o-llama
git pull origin main
source venv/bin/activate
uv sync
./chat-manager.sh restart
```

### Update Ollama Models

```bash
# Update existing models
ollama pull qwen2.5:0.5b
ollama pull llama3.2:1b

# Add new models
ollama pull phi3:mini
```

### Update GGUF Models

```bash
# Update models using download utility
./download-gguf.sh download https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf

# Batch update from models.txt
./download-gguf.sh batch models.txt

# Check current models
./download-gguf.sh list
```

### Backup Data

```bash
# Backup conversation database
cp data/chat-o-llama.db ~/chat-o-llama-backup.db

# Backup configuration
cp config.json ~/config-backup.json
```

---

## 🆘 Getting Help

If you encounter issues:

1. **Check the troubleshooting section above**
2. **View logs**: `./chat-manager.sh logs`
3. **Check GitHub Issues**: https://github.com/ukkit/chat-o-llama/issues
4. **Enable debug mode**: `DEBUG=true ./chat-manager.sh start`
5. **Verify system requirements** are met

**Community Support:**
- GitHub Issues: Report bugs and feature requests
- Discussions: Share tips and configurations
- Documentation: Check docs/ folder for detailed guides

**System Information for Bug Reports:**
```bash
# Collect system info for bug reports
echo "OS: $(uname -a)"
echo "Python: $(python --version)"
echo "Ollama: $(ollama --version)"
echo "Models: $(ollama list)"
./chat-manager.sh status
```

Happy chatting with Ollama! 🦙