# 📦 Complete Installation Guide

This guide provides both automatic and manual installation methods for chat-o-llama.

## ⚡ Prerequisites for Fastest Setup

**For quickest installation (< 2 minutes), have these ready:**
- **Python 3.8+** with pip and venv modules
- **Ollama** running with at least one model downloaded
- **git** (usually pre-installed on most systems)

**Quick prerequisite check:**
```bash
python3 --version          # Should show 3.8 or higher
python3 -m pip --version   # Should work without errors
python3 -m venv --help     # Should show venv help
ollama --version           # Should show Ollama version
ollama list                # Should show at least one model
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
- **Checks for Python 3.8+** - Installs if missing or too old
- **Checks for Ollama** - Downloads and installs if not found
- **Checks for git** - Installs if missing
- **Validates all tools** - Ensures everything works before proceeding

**✅ Efficient Setup:**
- **Downloads chat-o-llama** from GitHub (lightweight)
- **Creates virtual environment** (isolated Python environment)
- **Installs dependencies** (Flask, requests - minimal requirements)
- **Sets up permissions** (makes scripts executable)

**✅ Model Management:**
- **Checks existing models** - Uses what you already have
- **Recommends qwen2.5:0.5b** (~380MB, fastest)
- **Provides alternatives** if download fails
- **Skips download** if you prefer to install models later

**✅ Service Launch:**
- **Starts automatically** on available port (default: 3000)
- **Provides access URL** and management commands
- **Shows next steps** and usage instructions

### Installation Time Breakdown

**With Prerequisites Present:**
```
Downloading chat-o-llama     : 10-30 seconds
Setting up environment       : 30-60 seconds
Installing Python packages   : 30-60 seconds
Starting application         : 5-10 seconds
Total                        : ~2 minutes
```

**Installing Prerequisites:**
```
Installing Python (if needed): 2-5 minutes
Installing Ollama (if needed): 1-3 minutes
Downloading model (if needed) : 2-10 minutes (depends on model size)
Setting up chat-o-llama      : 2 minutes
Total                        : 5-20 minutes
```

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
Access at: http://localhost:3000
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
Access at: http://localhost:3000
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

**Time estimate: ~2 minutes**

```bash
# 1. Download chat-o-llama
git clone https://github.com/ukkit/chat-o-llama.git
cd chat-o-llama

# 2. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Make script executable and start
chmod +x chat-manager.sh
./chat-manager.sh start

# 5. Access the application
# Open browser to http://localhost:3000
```

### Complete Manual Installation (Fresh System)

**Time estimate: ~10-20 minutes**

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

#### Step 3: Install chat-o-llama

```bash
# Clone repository
git clone https://github.com/ukkit/chat-o-llama.git
cd chat-o-llama

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

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
curl http://localhost:3000/api/models

# Open in browser
# http://localhost:3000
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

# pip not found
sudo apt install python3-pip  # Ubuntu/Debian

# venv module not found
sudo apt install python3-venv  # Ubuntu/Debian
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
./chat-manager.sh start 8080  # Use different port
sudo lsof -i :3000  # Check what's using port 3000
```

#### Memory Issues
```bash
# For low-memory systems, use smaller models
ollama pull qwen2.5:0.5b  # Only ~380MB

# Use speed config for less memory
cp speed_config.json config.json
./chat-manager.sh restart
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
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## 📋 Verification Checklist

After installation, verify everything works:

- [ ] **Python**: `python --version` shows 3.8+
- [ ] **Ollama**: `ollama list` shows available models
- [ ] **Service**: `./chat-manager.sh status` shows running
- [ ] **Web Interface**: http://localhost:3000 loads
- [ ] **API**: `curl http://localhost:3000/api/models` returns models
- [ ] **Chat**: Can select model and send test message

---

## 🔄 Updates and Maintenance

### Update chat-o-llama

```bash
cd ~/chat-o-llama
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
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