# 🔧 Troubleshooting Guide

Complete troubleshooting guide for chat-o-llama installation, configuration, and runtime issues.

## 📋 Table of Contents

- [Quick Fixes](#quick-fixes)
- [Installation Issues](#installation-issues)
- [Runtime Issues](#runtime-issues)
- [Performance Issues](#performance-issues)
- [Configuration Issues](#configuration-issues)
- [Ollama Issues](#ollama-issues)
- [llama.cpp Issues](#llamacpp-issues) ⭐ *New*
- [Multi-Backend Issues](#multi-backend-issues) ⭐ *New*
- [Network Issues](#network-issues)
- [Database Issues](#database-issues)
- [Debug Mode](#debug-mode)
- [System Information](#system-information)
- [Getting Help](#getting-help)

---

## Quick Fixes

### Most Common Issues

| Issue | Quick Fix |
|-------|-----------|
| Port in use | `./chat-manager.sh start 3113` |
| Process won't stop | `./chat-manager.sh force-stop` |
| Ollama not responding | `curl http://localhost:11434/api/tags` |
| No models available | `ollama pull qwen2.5:0.5b` |
| llama.cpp compilation failed | `pip install llama-cpp-python --no-cache-dir` ⭐ *New* |
| GGUF model not found | `ls models/*.gguf` ⭐ *New* |
| Backend switching failed | `curl http://localhost:3113/api/backend/status` ⭐ *New* |
| Permission denied | `chmod +x chat-manager.sh` |
| Dependencies missing | `pip install -r requirements.txt` |
| Virtual env not activated | `source venv/bin/activate` |

### Emergency Reset

```bash
# Stop everything
./chat-manager.sh force-stop

# Reset virtual environment
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Reset database (loses chat history)
rm -f data/chat-o-llama.db

# Start fresh
./chat-manager.sh start
```

---

## Installation Issues

### Auto-Installer Problems

#### Installation Script Fails to Download
```bash
# Error: curl/wget not found
sudo apt install curl wget  # Ubuntu/Debian
sudo yum install curl wget  # CentOS/RHEL
brew install curl wget      # macOS

# Error: Permission denied
chmod +x install.sh
./install.sh

# Error: Script exits unexpectedly
bash -x install.sh  # Run with debug output
```

#### Python Installation Issues
```bash
# Python not found
sudo apt update && sudo apt install python3 python3-pip python3-venv  # Ubuntu/Debian
sudo yum install python3 python3-pip  # CentOS/RHEL
brew install python3  # macOS

# Python version too old
python3 --version  # Should be 3.8+
# Install newer Python from deadsnakes PPA (Ubuntu)
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-pip

# pip not found
sudo apt install python3-pip  # Ubuntu/Debian
curl https://bootstrap.pypa.io/get-pip.py | python3  # Manual install

# venv module not found
sudo apt install python3-venv  # Ubuntu/Debian
python3 -m pip install virtualenv  # Alternative
```

#### Git Installation Issues
```bash
# git not found
sudo apt install git  # Ubuntu/Debian
sudo yum install git  # CentOS/RHEL
brew install git      # macOS

# Git clone fails
git clone https://github.com/ukkit/chat-o-llama.git --depth 1  # Shallow clone
# OR download ZIP manually
wget https://github.com/ukkit/chat-o-llama/archive/main.zip
unzip main.zip
mv chat-o-llama-main chat-o-llama
```

### Manual Installation Problems

#### Virtual Environment Issues
```bash
# venv creation fails
python3 -m venv venv --without-pip
wget https://bootstrap.pypa.io/get-pip.py
venv/bin/python get-pip.py

# Activation fails
source venv/bin/activate
# OR on some systems
. venv/bin/activate

# Wrong Python in venv
rm -rf venv
python3.11 -m venv venv  # Use specific Python version
```

#### Dependency Installation Issues
```bash
# pip install fails
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt --no-cache-dir

# Network issues
pip install -r requirements.txt --trusted-host pypi.org --trusted-host pypi.python.org

# Permission issues
pip install -r requirements.txt --user

# Specific package fails
pip install Flask==3.0.0 requests==2.31.0  # Install individually
```

---

## Runtime Issues

### Application Won't Start

#### Port Already in Use
```bash
# Check what's using the port
sudo lsof -i :3113
netstat -tulpn | grep 3113

# Kill process using port
sudo kill -9 $(lsof -ti :3113)

# Use different port
./chat-manager.sh start 3113
PORT=3113 python app.py
```

#### Process Management Issues
```bash
# PID file exists but process not running
rm -f process.pid
./chat-manager.sh start

# Multiple processes running
./chat-manager.sh force-stop
ps aux | grep python | grep app.py
kill -9 $(pgrep -f "python.*app.py")

# Process won't stop gracefully
./chat-manager.sh force-stop
sudo killall -9 python3
```

#### Import/Module Errors
```bash
# Flask not found
source venv/bin/activate  # Make sure venv is activated
pip install Flask==3.0.0

# requests module not found
pip install requests==2.31.0

# Other import errors
pip install -r requirements.txt --force-reinstall
```

### Application Crashes

#### Memory Issues
```bash
# Monitor memory usage
top -p $(pgrep -f "python.*app.py")
htop

# Use speed config for less memory
cp speed_config.json config.json
./chat-manager.sh restart

# Reduce model context
# Edit config.json:
{
  "model_options": {
    "num_ctx": 1024,
    "num_predict": 512
  }
}
```

#### Unexpected Exits
```bash
# Check logs for errors
./chat-manager.sh logs
tail -f logs/chat-o-llama_*.log

# Run in foreground for debugging
source venv/bin/activate
python app.py

# Check system resources
df -h  # Disk space
free -h  # Memory
```

---

## Performance Issues

### Slow Response Times

#### Ollama Performance
```bash
# Check Ollama status
ollama ps
ollama list

# Restart Ollama
sudo systemctl restart ollama
# OR
pkill ollama && ollama serve

# Use smaller model
ollama pull qwen2.5:0.5b  # ~380MB
ollama pull tinyllama     # ~637MB
```

#### Configuration Optimization
```bash
# Use speed configuration
cp speed_config.json config.json
./chat-manager.sh restart

# Reduce context for speed
# Edit config.json:
{
  "model_options": {
    "num_ctx": 2048,
    "num_predict": 1024,
    "temperature": 0.3
  },
  "performance": {
    "context_history_limit": 5
  }
}
```

#### System Resource Issues
```bash
# Check CPU usage
top
htop

# Check disk I/O
iostat -x 1

# Check memory pressure
free -h
cat /proc/meminfo | grep Available

# Optimize for low memory
export OLLAMA_MAX_LOADED_MODELS=1
export OLLAMA_NUM_PARALLEL=1
```

### High Memory Usage

#### Memory Optimization
```bash
# Use low VRAM config
# Edit config.json:
{
  "response_optimization": {
    "low_vram": true,
    "f16_kv": true,
    "use_mmap": true
  },
  "performance": {
    "use_mlock": false
  }
}

# Monitor memory usage
watch -n 1 'free -h && ps aux | grep -E "(ollama|python)" | grep -v grep'
```

---

## Configuration Issues

### JSON Configuration Errors

#### Syntax Errors
```bash
# Validate JSON syntax
python -m json.tool config.json

# Common fixes
# Remove trailing commas
# Check quotes and brackets
# Use proper escaping

# Reset to default config
rm config.json
./chat-manager.sh restart  # Will create default config
```

#### Invalid Configuration Values
```bash
# Check configuration via API
curl http://localhost:3113/api/config

# Common value ranges:
# temperature: 0.0-2.0
# top_p: 0.0-1.0
# top_k: 1-100
# num_ctx: 256-32768
# num_predict: 64-8192
```

### Environment Variable Issues
```bash
# Check current environment
env | grep -E "(OLLAMA|PORT|DEBUG)"

# Reset environment
unset OLLAMA_API_URL
unset PORT
unset DEBUG

# Set proper values
export OLLAMA_API_URL="http://localhost:11434"
export PORT="3113"
```

---

## Ollama Issues

### Ollama Not Running

#### Service Management
```bash
# Check if Ollama is running
pgrep ollama
ps aux | grep ollama

# Start Ollama service
ollama serve &

# OR as systemd service (Linux)
sudo systemctl start ollama
sudo systemctl enable ollama  # Auto-start on boot

# Check Ollama logs
journalctl -u ollama -f  # systemd logs
```

#### Connection Issues
```bash
# Test Ollama connectivity
curl http://localhost:11434/api/tags
curl http://localhost:11434/api/version

# Check Ollama port
netstat -tulpn | grep 11434
lsof -i :11434

# Restart Ollama with specific settings
OLLAMA_HOST=0.0.0.0:11434 ollama serve
```

### Model Issues

#### No Models Available
```bash
# List installed models
ollama list

# Download recommended models
ollama pull qwen2.5:0.5b  # Smallest, fast
ollama pull tinyllama     # Ultra lightweight
ollama pull llama3.2:1b   # Better quality

# Remove corrupted models
ollama rm model_name
ollama pull model_name    # Re-download
```

#### Model Loading Errors
```bash
# Check model status
ollama ps

# Unload and reload model
ollama stop model_name
ollama run model_name "test"  # Force load

# Clear model cache
rm -rf ~/.ollama/models/blobs/*  # WARNING: Will need to re-download
```

#### Out of Memory Errors
```bash
# Use smaller models
ollama pull qwen2.5:0.5b

# Set memory limits
export OLLAMA_MAX_LOADED_MODELS=1
export OLLAMA_NUM_PARALLEL=1

# Check available memory
free -h
```

---

## llama.cpp Issues ⭐ *New*

### Installation and Compilation Problems

#### llama-cpp-python Compilation Fails
```bash
# Update build tools first
pip install --upgrade pip setuptools wheel cmake

# Clear pip cache and reinstall
pip uninstall llama-cpp-python -y
pip install llama-cpp-python --no-cache-dir --verbose

# For systems with limited resources
export CMAKE_ARGS="-DLLAMA_BLAS=OFF -DLLAMA_CUBLAS=OFF"
pip install llama-cpp-python --no-cache-dir

# For GPU support (NVIDIA)
export CMAKE_ARGS="-DLLAMA_CUBLAS=ON"
pip install llama-cpp-python --no-cache-dir

# For Apple Silicon (M1/M2)
export CMAKE_ARGS="-DLLAMA_METAL=ON"
pip install llama-cpp-python --no-cache-dir

# Use pre-built wheels if compilation fails
pip install --index-url https://abetlen.github.io/llama-cpp-python/whl/cpu llama-cpp-python
```

#### Missing System Dependencies
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install build-essential cmake pkg-config

# CentOS/RHEL
sudo yum groupinstall "Development Tools"
sudo yum install cmake

# macOS
xcode-select --install
brew install cmake
```

### GGUF Model Issues

#### Model Not Found
```bash
# Check models directory (using correct path from config.json)
ls -la llama_models/
find . -name "*.gguf" -type f

# Create models directory if missing
mkdir -p llama_models

# Check model path in config
grep -A 10 "llamacpp" config.json

# Fix permissions
chmod 644 llama_models/*.gguf
chown $USER:$USER llama_models/*.gguf
```

#### Model Loading Errors
```bash
# Test model loading manually
python3 -c "
from llama_cpp import Llama
try:
    llm = Llama(model_path='llama_models/your-model.gguf', n_ctx=512)
    print('Model loaded successfully')
except Exception as e:
    print(f'Model loading failed: {e}')
"

# Check model file integrity
file llama_models/*.gguf  # Should show 'data'
ls -lh llama_models/*.gguf  # Check file sizes

# Verify GGUF format
python3 -c "
import struct
with open('llama_models/your-model.gguf', 'rb') as f:
    magic = f.read(4)
    print(f'Magic bytes: {magic}')
    print('Valid GGUF' if magic == b'GGUF' else 'Invalid format')
"
```

#### Memory Issues with Local Models
```bash
# Current config.json settings are already optimized:
# n_ctx: 4096, n_batch: 128, use_mmap: true, use_mlock: false

# For very large models, reduce context further:
{
  "llamacpp": {
    "n_ctx": 2048,
    "n_batch": 64,
    "use_mmap": true,
    "use_mlock": false
  }
}

# Monitor memory usage
watch -n 1 'ps aux | grep python | grep -v grep; free -h'
```

### Performance Issues

#### Slow Model Loading
```bash
# Current config already enables memory mapping
# Model path: ./llama_models (as configured)
# use_mmap: true, use_mlock: false

# Check if models are in correct directory
ls -la llama_models/
```

#### Slow Inference
```bash
# Current config optimizations:
# n_threads: 8 (configured in config.json)
# n_batch: 128
# n_gpu_layers: 0 (CPU only by default)

# For GPU acceleration (if available):
{
  "llamacpp": {
    "n_gpu_layers": 32,  # Adjust based on GPU memory
    "n_threads": 4       # Reduce CPU threads when using GPU
  }
}
```

---

## Multi-Backend Issues ⭐ *New*

### Backend Switching Problems

#### Backend Not Responding
```bash
# Check backend status (using correct port 3113)
curl http://localhost:3113/api/backend/status

# Test individual backends
curl http://localhost:3113/api/backend/info

# Force health check
curl -X POST http://localhost:3113/api/backend/health

# Check backend configuration (correct structure)
grep -A 20 "backend" config.json
```

#### Failed Backend Switch
```bash
# Check available backends
curl http://localhost:3113/api/backend/status | jq '.backends'

# Try switching manually
curl -X POST http://localhost:3113/api/backend/switch \
  -H "Content-Type: application/json" \
  -d '{"backend_type": "llamacpp"}'

# Check switch error details
./chat-manager.sh logs | grep -i "backend\|switch"
```

#### Models Not Showing from Correct Backend
```bash
# Check which backend is active
curl http://localhost:3113/api/models | jq '.active_backend'

# List models from all backends
curl http://localhost:3113/api/backend/models

# Force model refresh
./chat-manager.sh restart
```

### Configuration Conflicts

#### Backend Configuration Errors
```bash
# Validate backend configuration (correct structure from config.json)
python3 -c "
import json
with open('config.json') as f:
    config = json.load(f)
    
backends = ['ollama', 'llamacpp']
for backend in backends:
    if backend in config:
        print(f'{backend} config: OK')
    else:
        print(f'{backend} config: MISSING')
        
if 'backend' in config:
    print(f'Active backend: {config[\"backend\"].get(\"active\", \"NOT SET\")}')
"

# Check correct configuration structure:
{
  "backend": {
    "active": "ollama",
    "auto_fallback": true,
    "health_check_interval": 30
  },
  "ollama": {
    "base_url": "http://localhost:11434"
  },
  "llamacpp": {
    "model_path": "./llama_models"
  }
}
```

#### Conflicting Backend Settings
```bash
# Check for port conflicts (correct ports)
netstat -tulpn | grep -E "(11434|3113)"

# Ensure only one backend is active
curl http://localhost:3113/api/backend/status | jq '.active_backend'

# Verify Ollama connection
curl http://localhost:11434/api/tags

# Verify llama.cpp models
ls -la llama_models/*.gguf
```

### Health Check Issues

#### Backend Health Checks Failing
```bash
# Manual health check
curl -X POST http://localhost:3113/api/backend/health

# Check health check interval (current config: 30 seconds)
grep -A 5 "health_check_interval" config.json

# Disable health checks temporarily
{
  "backend": {
    "health_check_interval": 0
  }
}

# Check backend connectivity manually
# For Ollama (correct URL):
curl http://localhost:11434/api/tags

# For llama.cpp (correct path):
ls -la llama_models/*.gguf
python3 -c "from llama_cpp import Llama; print('llama-cpp-python works')"
```

#### Automatic Fallback Not Working
```bash
# Check fallback configuration (current setting: true)
curl http://localhost:3113/api/backend/status | jq '.auto_fallback'

# Test fallback manually
# 1. Stop primary backend (Ollama)
sudo systemctl stop ollama

# 2. Send a chat message
curl -X POST http://localhost:3113/api/chat \
  -H "Content-Type: application/json" \
  -d '{"conversation_id": 1, "message": "test", "model": "any"}'

# 3. Check if it switched to secondary backend
curl http://localhost:3113/api/backend/info
```

### Model Compatibility Issues

#### Models Not Loading Across Backends
```bash
# Check model format compatibility
# Ollama models: Use Ollama format
ollama list

# llama.cpp models: Must be GGUF format in llama_models directory
file llama_models/*.gguf

# Model naming conflicts
curl http://localhost:3113/api/backend/models | jq '.models_by_backend'
```

#### Cross-Backend Model Switching
```bash
# List models with backend prefixes
curl http://localhost:3113/api/models

# Switch model and backend in chat
curl -X POST http://localhost:3113/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": 1, 
    "message": "test",
    "model": "llamacpp:your-model.gguf"
  }'

# Check if backend switched automatically
curl http://localhost:3113/api/backend/info
```

---

## Network Issues

### Connection Timeouts

#### Ollama Connectivity
```bash
# Test connection with longer timeout
curl -m 60 http://localhost:11434/api/tags

# Check firewall
sudo ufw status  # Ubuntu
sudo firewall-cmd --list-all  # CentOS/RHEL

# Increase timeouts in config.json
{
  "timeouts": {
    "ollama_timeout": 1200,
    "ollama_connect_timeout": 60
  }
}
```

#### Remote Ollama Setup
```bash
# Configure remote Ollama
export OLLAMA_API_URL="http://remote-server:11434"

# Test remote connection
curl http://remote-server:11434/api/tags

# Update config for remote use
{
  "timeouts": {
    "ollama_timeout": 1800,
    "ollama_connect_timeout": 120
  }
}
```

### DNS/Hostname Issues
```bash
# Use IP address instead of hostname
export OLLAMA_API_URL="http://192.168.1.100:11434"

# Check DNS resolution
nslookup hostname
dig hostname

# Add to /etc/hosts if needed
echo "192.168.1.100 ollama-server" | sudo tee -a /etc/hosts
```

---

## Database Issues

### SQLite Database Problems

#### Database Corruption
```bash
# Check database integrity
sqlite3 data/chat-o-llama.db "PRAGMA integrity_check;"

# Backup current database
cp data/chat-o-llama.db data/backup-$(date +%Y%m%d).db

# Reset database (loses chat history)
./chat-manager.sh stop
rm -f data/chat-o-llama.db
./chat-manager.sh start
```

#### Permission Issues
```bash
# Fix database permissions
chmod 644 data/chat-o-llama.db
chown $USER:$USER data/chat-o-llama.db

# Fix directory permissions
mkdir -p data
chmod 755 data
```

#### Disk Space Issues
```bash
# Check disk space
df -h

# Clean up old logs
find logs/ -name "*.log" -mtime +7 -delete

# Compact database
sqlite3 data/chat-o-llama.db "VACUUM;"
```

---

## Debug Mode

### Enable Debug Logging

#### Application Debug Mode
```bash
# Start with debug enabled
DEBUG=true ./chat-manager.sh start

# View debug logs
./chat-manager.sh logs
tail -f logs/chat-o-llama_*.log

# Python debug mode
source venv/bin/activate
FLASK_DEBUG=1 python app.py
```

#### Ollama Debug Mode
```bash
# Start Ollama with debug logging
OLLAMA_DEBUG=1 ollama serve

# View Ollama logs
journalctl -u ollama -f
```

#### Verbose Installation
```bash
# Run installer with debug output
bash -x install.sh > install-debug.log 2>&1

# Manual installation with verbose pip
pip install -r requirements.txt -v
```

### Debug Scripts

#### Health Check Script
```bash
#!/bin/bash
# health-check.sh

echo "=== Chat-O-Llama Health Check ==="

# Check Python
echo "Python version:"
python3 --version

# Check virtual environment
echo "Virtual environment:"
which python
echo $VIRTUAL_ENV

# Check Ollama
echo "Ollama status:"
if command -v ollama &> /dev/null; then
    ollama --version
    ollama list 2>/dev/null || echo "Ollama not responding"
else
    echo "Ollama not installed"
fi

# Check processes
echo "Running processes:"
ps aux | grep -E "(python|ollama)" | grep -v grep

# Check ports
echo "Port usage:"
lsof -i :3113 2>/dev/null || echo "Port 3113 free"
lsof -i :11434 2>/dev/null || echo "Port 11434 free"

# Check disk space
echo "Disk space:"
df -h .

# Check memory
echo "Memory usage:"
free -h

echo "=== Health Check Complete ==="
```

#### API Test Script
```bash
#!/bin/bash
# api-test.sh

BASE_URL="http://localhost:3113/api"

echo "=== API Testing ==="

# Test models endpoint
echo "Testing /api/models:"
curl -s -w "\nHTTP %{http_code}\n" "$BASE_URL/models" || echo "FAILED"

# Test config endpoint
echo -e "\nTesting /api/config:"
curl -s -w "\nHTTP %{http_code}\n" "$BASE_URL/config" || echo "FAILED"

# Test conversations endpoint
echo -e "\nTesting /api/conversations:"
curl -s -w "\nHTTP %{http_code}\n" "$BASE_URL/conversations" || echo "FAILED"

echo "=== API Testing Complete ==="
```

---

## System Information

### Collect System Info for Bug Reports

#### System Information Script
```bash
#!/bin/bash
# system-info.sh

echo "=== System Information ==="
echo "Date: $(date)"
echo "OS: $(uname -a)"
echo "Distribution: $(lsb_release -d 2>/dev/null || cat /etc/os-release | grep PRETTY_NAME)"
echo ""

echo "=== Python Information ==="
python3 --version
which python3
echo "Pip version: $(pip --version)"
echo ""

echo "=== Ollama Information ==="
if command -v ollama &> /dev/null; then
    ollama --version
    echo "Ollama models:"
    ollama list
else
    echo "Ollama not found"
fi
echo ""

echo "=== Chat-O-Llama Status ==="
if [ -f "chat-manager.sh" ]; then
    ./chat-manager.sh status
else
    echo "chat-manager.sh not found"
fi
echo ""

echo "=== Configuration ==="
if [ -f "config.json" ]; then
    echo "Config file exists"
    python3 -m json.tool config.json > /dev/null && echo "Config syntax OK" || echo "Config syntax ERROR"
else
    echo "No config.json file"
fi
echo ""

echo "=== Resource Usage ==="
echo "Memory:"
free -h
echo "Disk space:"
df -h .
echo "Load average:"
uptime
```

### Performance Monitoring

#### Resource Monitor Script
```bash
#!/bin/bash
# monitor.sh

echo "=== Real-time Monitoring ==="
echo "Press Ctrl+C to stop"

while true; do
    clear
    echo "=== $(date) ==="
    
    # Memory usage
    echo "Memory Usage:"
    free -h | grep -E "(Mem|Swap)"
    
    # Process info
    echo -e "\nChat-O-Llama Processes:"
    ps aux | grep -E "(python.*app.py|ollama)" | grep -v grep
    
    # Port status
    echo -e "\nPort Status:"
    lsof -i :3113 2>/dev/null && echo "Port 3113: IN USE" || echo "Port 3113: FREE"
    lsof -i :11434 2>/dev/null && echo "Port 11434: IN USE" || echo "Port 11434: FREE"
    
    # Recent logs
    echo -e "\nRecent Logs:"
    if [ -f logs/chat-o-llama_*.log ]; then
        tail -n 3 logs/chat-o-llama_*.log 2>/dev/null
    fi
    
    sleep 5
done
```

---

## Getting Help

### Before Reporting Issues

1. **Check this troubleshooting guide** for common solutions
2. **Run debug mode** to get detailed error information
3. **Collect system information** using the scripts above
4. **Search existing issues** on GitHub

### Information to Include in Bug Reports

```
**System Information:**
- OS: [Ubuntu 20.04, macOS 13, etc.]
- Python version: [3.9.2]
- Ollama version: [0.1.26]
- Chat-o-llama version: [commit hash or release]

**Installation Method:**
- [ ] Automatic installer
- [ ] Manual installation
- [ ] Docker
- [ ] Other: ___

**Issue Description:**
[Describe the problem clearly]

**Steps to Reproduce:**
1. [First step]
2. [Second step]
3. [etc.]

**Expected Behavior:**
[What should happen]

**Actual Behavior:**
[What actually happens]

**Error Messages:**
```
[Include full error messages and logs]
```

**Configuration:**
[Include relevant config.json sections]

**Additional Context:**
[Any other relevant information]
```

### Support Channels

- **GitHub Issues**: https://github.com/ukkit/chat-o-llama/issues
- **Discussions**: https://github.com/ukkit/chat-o-llama/discussions
- **Documentation**: Check README.md, INSTALL.md, and docs/ folder

### Self-Help Resources

1. **Enable debug mode** and check logs
2. **Use the health check script** to identify issues
3. **Try the emergency reset** procedure
4. **Check Ollama documentation** for model-specific issues
5. **Review configuration examples** in docs/ folder

---

## Emergency Procedures

### Complete Reset
```bash
# Nuclear option - completely reset everything
./chat-manager.sh force-stop
rm -rf venv data logs *.pid *.log
git clean -fdx
git reset --hard HEAD

# Reinstall
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
./chat-manager.sh start
```

### Recovery from Corrupted Installation
```bash
# Backup any important data
cp data/chat-o-llama.db ~/backup-chat.db 2>/dev/null || true
cp config.json ~/backup-config.json 2>/dev/null || true

# Remove and reinstall
cd ..
rm -rf chat-o-llama
curl -fsSL https://github.com/ukkit/chat-o-llama/raw/main/install.sh | sh

# Restore data if needed
cp ~/backup-chat.db ~/chat-o-llama/data/chat-o-llama.db 2>/dev/null || true
cp ~/backup-config.json ~/chat-o-llama/config.json 2>/dev/null || true
```

Remember: Most issues can be resolved by carefully following the steps in this guide. If you're still having problems, don't hesitate to ask for help on GitHub!