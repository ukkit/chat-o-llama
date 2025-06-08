# 📦 Complete Installation Guide

This guide provides both automatic and manual installation methods for chat-o-llama.

## 🚀 Method 1: Automatic Installation (Recommended)

### One-Command Installation

The easiest way to install chat-o-llama with all dependencies:

```bash
curl -fsSL https://github.com/ukkit/chat-o-llama/raw/main/install.sh | bash
```

**Alternative methods:**
```bash
# Using wget
wget -O- https://github.com/ukkit/chat-o-llama/raw/main/install.sh | bash

# Download and inspect first (recommended for security)
curl -O https://github.com/ukkit/chat-o-llama/raw/main/install.sh
cat install.sh  # Review the script
chmod +x install.sh
bash install.sh
```

### What the Auto-Installer Does

✅ **Prerequisites Check:**
- Verifies Python 3.8+ installation
- Checks for Ollama and installs if missing
- Validates pip and venv availability
- Auto-installs git if needed

✅ **Smart Setup:**
- Downloads chat-o-llama from GitHub
- Creates Python virtual environment
- Installs all required dependencies
- Sets up proper permissions

✅ **Model Management:**
- Checks for existing Ollama models
- Recommends qwen2.5:0.5b (~380MB, fastest)
- Falls back to tinyllama if needed
- Provides download options

✅ **Service Launch:**
- Starts the application automatically
- Finds available port (default: 3000)
- Provides access URL and commands
- Shows management instructions

### Expected Output

```
╔══════════════════════════════════════╗
║           chat-o-llama 🦙            ║
║        Auto Installer Script        ║
╚══════════════════════════════════════╝

✓ Python 3.11.2 found at /usr/bin/python3
✓ Ollama found at /usr/local/bin/ollama
✓ Ollama service is running
✓ chat-o-llama downloaded successfully
✓ Virtual environment created
✓ Dependencies installed successfully
✓ Model qwen2.5:0.5b downloaded successfully!
✓ chat-o-llama started successfully!

🎉 Installation Complete! 🎉

Access your chat interface at:
  👉 http://localhost:3000
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

### Prerequisites

**Required:**
- Python 3.8 or higher
- git
- curl or wget

**Install prerequisites:**

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv git curl
```

#### CentOS/RHEL/Fedora
```bash
sudo yum install python3 python3-pip git curl
# OR for newer versions
sudo dnf install python3 python3-pip git curl
```

#### macOS
```bash
# Install Homebrew if not installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install dependencies
brew install python3 git
```

#### Windows (WSL recommended)
```bash
# Enable WSL2 and install Ubuntu
# Then follow Ubuntu instructions above
```

### Step 1: Install Ollama

#### Linux/macOS (Recommended)
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

#### Manual Ollama Installation
```bash
# Download from https://ollama.ai/download
# Follow platform-specific instructions
```

#### Start Ollama Service
```bash
# Start Ollama (will run in background)
ollama serve

# OR as systemd service (Linux)
sudo systemctl enable ollama
sudo systemctl start ollama
```

#### Verify Ollama Installation
```bash
ollama --version
ollama list  # Should connect without errors
```

### Step 2: Download Ollama Models

**Recommended models (choose one or more):**

```bash
# Smallest and fastest (recommended for low-resource systems)
ollama pull qwen2.5:0.5b     # ~380MB

# Ultra lightweight alternative
ollama pull tinyllama        # ~637MB

# Better quality options
ollama pull llama3.2:1b      # ~1.3GB
ollama pull phi3:mini        # ~2.3GB
ollama pull gemma2:2b        # ~1.6GB
```

**For CPU-only systems, start with:**
```bash
ollama pull qwen2.5:0.5b
```

### Step 3: Download chat-o-llama

```bash
# Clone the repository
git clone https://github.com/ukkit/chat-o-llama.git

# Navigate to directory
cd chat-o-llama
```

### Step 4: Set Up Python Environment

#### Create Virtual Environment
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Verify activation (should show venv path)
which python
```

#### Install Dependencies
```bash
# Upgrade pip
pip install --upgrade pip

# Install requirements
pip install -r requirements.txt

# Verify installation
python -c "import flask, requests; print('Dependencies installed successfully')"
```

### Step 5: Configure and Start

#### Make Scripts Executable
```bash
chmod +x chat-manager.sh
```

#### Start the Application
```bash
# Start with default settings
./chat-manager.sh start

# OR start on specific port
./chat-manager.sh start 8080

# OR start manually
python app.py
```

#### Verify Installation
```bash
# Check status
./chat-manager.sh status

# Test API endpoints
curl http://localhost:3000/api/models
curl http://localhost:3000/api/config
```

### Step 6: Access the Application

Open your browser and navigate to:
- **Default:** http://localhost:3000
- **Custom port:** http://localhost:8080 (if you specified port 8080)

---

## 🔧 Advanced Installation Options

### Installing in Custom Directory

```bash
# Clone to custom location
git clone https://github.com/ukkit/chat-o-llama.git /opt/chat-o-llama
cd /opt/chat-o-llama

# Follow steps 4-6 above
```

### Installing with Docker (Community Option)

```bash
# Clone repository
git clone https://github.com/ukkit/chat-o-llama.git
cd chat-o-llama

# Create Dockerfile (community contribution)
cat > Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 3000

CMD ["python", "app.py"]
EOF

# Build and run
docker build -t chat-o-llama .
docker run -p 3000:3000 -v ollama_data:/data chat-o-llama
```

### Installing on Remote Server

```bash
# On remote server
git clone https://github.com/ukkit/chat-o-llama.git
cd chat-o-llama

# Follow manual installation steps

# Configure for remote access
export OLLAMA_API_URL="http://localhost:11434"
./chat-manager.sh start 3000

# Access from remote client
# http://your-server-ip:3000
```

### Installing with GPU Support

```bash
# Install NVIDIA drivers and CUDA first
# Follow Ollama GPU setup: https://ollama.ai/docs/gpu

# Modify config.json for GPU
cat > config.json << 'EOF'
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
EOF

# Restart with GPU config
./chat-manager.sh restart
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