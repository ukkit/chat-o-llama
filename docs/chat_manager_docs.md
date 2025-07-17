# Chat-O-Llama Process Manager Documentation

## Overview

The Chat-O-Llama Process Manager (`chat-manager.sh`) is a comprehensive shell script designed to manage the lifecycle of the Chat-O-Llama Flask application with **multi-backend support**. It provides robust process management, backend switching, health monitoring, logging, error handling, and monitoring capabilities for production and development environments.

**New in v2.0**: Full multi-backend support for both **Ollama** and **llama.cpp** backends with seamless switching and health monitoring.

## Core Features

### 1. Multi-Backend Support (NEW)
- **Backend Detection**: Automatic detection of Ollama and llama.cpp availability
- **Backend Switching**: Seamless switching between Ollama and llama.cpp backends
- **Health Monitoring**: Real-time health checks for all available backends
- **Status Reporting**: Comprehensive backend status and capability information
- **Configuration Management**: Automatic config.json updates for backend changes

### 2. Process Management
- **Graceful startup and shutdown** of Flask applications
- **PID-based process tracking** with file persistence
- **Port conflict detection** and resolution
- **Orphaned process cleanup** and management
- **Force-kill capabilities** for stuck processes

### 3. Environment Management
- **Virtual environment validation** before startup
- **Dependency checking** (Flask, requests, llama-cpp-python)
- **Python version detection** (python3/python)
- **Port availability verification**
- **Backend requirements validation**

### 4. Logging System
- **Timestamped log files** with datetime naming convention
- **Centralized log directory** structure
- **Real-time log monitoring** capabilities
- **Log file rotation** and management

## File Structure

```
project-root/
├── chat-manager.sh           # Main process manager script with multi-backend support
├── app.py                   # Flask application
├── config.json              # Configuration file with backend settings
├── process.pid              # PID file (created at runtime)
├── logs/                    # Log directory
│   └── chat-o-llama_YYYYMMDD_HHMMSS.log
├── models/                  # GGUF model directory (for llama.cpp)
└── venv/                    # Virtual environment
```

## Commands Reference

### Backend Management Commands (NEW)

#### Check Backend Status
```bash
./chat-manager.sh backend status
# or
./chat-manager.sh backend list
```
- Shows status of all available backends (Ollama and llama.cpp)
- Displays health indicators: ✓ healthy, ✗ unhealthy, ? unknown
- Shows currently active backend
- Reports backend capabilities and configuration

#### Switch Backend
```bash
./chat-manager.sh backend switch <backend_name>
```
**Examples:**
```bash
./chat-manager.sh backend switch ollama     # Switch to Ollama backend
./chat-manager.sh backend switch llamacpp   # Switch to llama.cpp backend
```
- Updates config.json with new active backend
- Validates backend availability before switching
- Provides warnings for unhealthy backends
- Requires application restart to take effect

#### Check Backend Health
```bash
./chat-manager.sh backend health [backend_name]
```
**Examples:**
```bash
./chat-manager.sh backend health           # Check active backend
./chat-manager.sh backend health ollama    # Check Ollama specifically
./chat-manager.sh backend health llamacpp  # Check llama.cpp specifically
```
- **Ollama**: Tests HTTP connectivity to Ollama API
- **llama.cpp**: Validates Python package and GGUF model availability
- Provides troubleshooting guidance for failed health checks

### Basic Operations

#### Start Application
```bash
./chat-manager.sh start [port]
```
- **Default port**: 3113
- **Custom port**: `./chat-manager.sh start 3113`
- **Prerequisites**: Virtual environment activated, dependencies installed

#### Stop Application
```bash
./chat-manager.sh stop
```
- Attempts graceful shutdown first (SIGTERM)
- Falls back to force kill (SIGKILL) if needed
- Cleans up PID files and orphaned processes

#### Force Stop
```bash
./chat-manager.sh force-stop
```
- Immediately kills all related Python processes
- Cleans up processes on common ports (3113, 5000, 8000, 9000)
- Emergency shutdown for stuck processes

#### Restart Application
```bash
./chat-manager.sh restart [port]
```
- Combines stop and start operations
- Includes 2-second delay for cleanup
- Maintains same port unless specified

#### Check Status
```bash
./chat-manager.sh status
```
- Shows running status and process information
- Displays current port and PID
- Shows recent log entries
- Detects orphaned processes
- **NEW**: Shows comprehensive backend status and health information
- **NEW**: Displays active backend and available alternatives

#### View Logs
```bash
./chat-manager.sh logs
```
- Displays real-time log output (`tail -f`)
- Shows most recent log file
- Press Ctrl+C to exit log viewing

### Help and Usage
```bash
./chat-manager.sh help
# or
./chat-manager.sh --help
# or
./chat-manager.sh -h
```

## Process Management Details

### Startup Process
1. **Environment Validation**
   - Check for virtual environment activation
   - Verify Flask installation
   - Validate app.py existence
   - Test port availability

2. **Backend Validation (NEW)**
   - Check active backend configuration
   - Perform backend health checks
   - Display backend status and warnings
   - Validate backend-specific requirements

3. **Process Creation**
   - Start Flask app in background using `nohup`
   - Capture process PID
   - Create PID file for tracking
   - Generate timestamped log file

4. **Verification**
   - Wait 2 seconds for startup
   - Verify process is running
   - Display access information

### Shutdown Process
1. **Graceful Shutdown**
   - Send SIGTERM to main process
   - Wait up to 10 seconds for graceful exit
   - Display progress indicators

2. **Force Cleanup**
   - Send SIGKILL if graceful shutdown fails
   - Search for orphaned Python processes
   - Kill processes on common ports
   - Remove PID files

3. **Verification**
   - Confirm all processes stopped
   - Report any remaining processes
   - Provide manual cleanup instructions if needed

### Port Management
- **Default Ports**: 3113 (primary), 5000, 8000, 9000
- **Conflict Detection**: Uses `lsof` to check port usage
- **Multi-Port Cleanup**: Checks and cleans multiple ports during shutdown

## Logging System

### Log File Naming
```
chat-o-llama_YYYYMMDD_HHMMSS.log
```
Example: `chat-o-llama_20250608_143022.log`

### Log Directory Structure
```
logs/
├── chat-o-llama_20250608_143022.log  # Current session
├── chat-o-llama_20250608_120000.log  # Previous session
└── chat-o-llama_20250607_180000.log  # Older session
```

### Log Content
- **Application output**: stdout and stderr from Flask app
- **Startup messages**: Initialization and configuration
- **Error messages**: Exceptions and error conditions
- **Access logs**: HTTP requests and responses (if configured)

### Log Monitoring
```bash
# Real-time log viewing
./chat-manager.sh logs

# Manual log viewing
tail -f logs/chat-o-llama_*.log

# View specific log file
tail -f logs/chat-o-llama_20250608_143022.log
```

## Multi-Backend System (NEW)

### Supported Backends

#### 1. Ollama Backend
- **Description**: HTTP API-based backend for Ollama AI models
- **Requirements**: 
  - Ollama service running and accessible
  - Network connectivity to Ollama API endpoint
- **Health Check**: HTTP request to `/api/tags` endpoint
- **Configuration**: `config.json` → `ollama` section
- **Default URL**: `http://localhost:11434`

#### 2. llama.cpp Backend  
- **Description**: Local inference using llama.cpp Python bindings
- **Requirements**:
  - `llama-cpp-python` package installed
  - GGUF model files in configured model directory
- **Health Check**: Python import test + model file detection
- **Configuration**: `config.json` → `llamacpp` section
- **Default Model Path**: `./models`

### Backend Configuration

The script reads backend configuration from `config.json`:

```json
{
  "backend": {
    "active": "ollama",           # Currently active backend
    "auto_fallback": true,        # Enable automatic fallback
    "health_check_interval": 30   # Health check frequency
  },
  "ollama": {
    "base_url": "http://localhost:11434",
    "timeout": 600,
    "connect_timeout": 45
  },
  "llamacpp": {
    "model_path": "./models",
    "n_ctx": 8192,
    "n_batch": 512,
    "n_threads": -1
  }
}
```

### Backend Health Monitoring

#### Ollama Health Check
```bash
# Tests connectivity to Ollama API
curl -s --connect-timeout 5 --max-time 10 "http://localhost:11434/api/tags"
```

#### llama.cpp Health Check
```bash
# Validates Python package availability
python3 -c "import llama_cpp"

# Checks for GGUF model files
find ./models -name "*.gguf" -type f
```

### Backend Switching Workflow

1. **Check Current Backend**
   ```bash
   ./chat-manager.sh backend status
   ```

2. **Validate New Backend**
   ```bash
   ./chat-manager.sh backend health llamacpp
   ```

3. **Switch Backend**
   ```bash
   ./chat-manager.sh backend switch llamacpp
   ```

4. **Restart Application**
   ```bash
   ./chat-manager.sh restart
   ```

### Environment Variables

The script supports environment variable overrides:

```bash
# Override config file location
export CONFIG_FILE="/path/to/custom/config.json"
./chat-manager.sh backend status

# Use different model directory for testing
export CONFIG_FILE="/tmp/test-config.json"
./chat-manager.sh backend switch llamacpp
```

## Error Handling

### Common Issues and Solutions

#### 1. Port Already in Use
```
[ERROR] Port 3113 is already in use by PID 12345
```
**Solutions**:
- Use different port: `./chat-manager.sh start 3113`
- Stop conflicting process: `kill 12345`
- Force stop all: `./chat-manager.sh force-stop`

#### 2. Virtual Environment Not Activated
```
[ERROR] Virtual environment not activated!
```
**Solution**:
```bash
source venv/bin/activate
./chat-manager.sh start
```

#### 3. Flask Not Installed
```
[ERROR] Flask not found in current environment
```
**Solution**:
```bash
pip install flask requests
# or
pip install -r requirements.txt
```

#### 4. app.py Not Found
```
[ERROR] app.py not found in /path/to/project
```
**Solution**: Ensure you're running the script from the correct directory

#### 5. Backend Health Issues (NEW)

##### Ollama Backend Unhealthy
```
[WARNING] Backend 'ollama' is not healthy - some features may not work
```
**Solutions**:
- Check if Ollama is running: `ollama serve`
- Verify API accessibility: `curl http://localhost:11434/api/tags`
- Check Ollama configuration in config.json
- Ensure network connectivity

##### llama.cpp Backend Unhealthy
```
[WARNING] Backend 'llamacpp' is not healthy - some features may not work
```
**Solutions**:
- Install llama.cpp Python package: `pip install llama-cpp-python`
- Download GGUF models to the models directory
- Check model path configuration in config.json
- Verify model file permissions

#### 6. Backend Switching Issues (NEW)

##### Unknown Backend
```
[ERROR] Unknown backend: invalid_backend
```
**Solution**: Use valid backend names: `ollama` or `llamacpp`

##### Config File Issues
```
[ERROR] Failed to switch backend
```
**Solutions**:
- Check config.json file permissions
- Validate JSON syntax in config.json
- Ensure config.json exists in project directory

### Error Recovery
- **Orphaned Processes**: Automatically detected and cleaned up
- **Stale PID Files**: Automatically removed if process is dead
- **Failed Startup**: Cleanup performed, error logged
- **Stuck Processes**: Force-stop available as fallback

## Security Considerations

### Process Isolation
- Runs within virtual environment constraints
- PID-based process tracking prevents interference
- Port-specific process management

### File Permissions
- PID file created with user permissions
- Log files created with appropriate access rights
- Script requires execution permissions

### Signal Handling
- Graceful shutdown using SIGTERM
- Force shutdown using SIGKILL
- Proper signal propagation to child processes

## Performance Optimization

### Memory Management
- Automatic cleanup of orphaned processes
- Log file rotation (manual - old files not auto-deleted)
- PID file cleanup on shutdown

### Resource Monitoring
- Port usage detection
- Process status verification
- System resource availability checking

## Troubleshooting Guide

### Check Process Status
```bash
# Using manager
./chat-manager.sh status

# Manual check
ps aux | grep "python.*app.py"
lsof -i :3113
```

### Debug Startup Issues
```bash
# Check recent logs
./chat-manager.sh logs

# Manual startup for debugging
source venv/bin/activate
python app.py
```

### Backend Troubleshooting (NEW)

#### Check All Backend Status
```bash
# Comprehensive backend status
./chat-manager.sh backend status

# Check specific backend health
./chat-manager.sh backend health ollama
./chat-manager.sh backend health llamacpp
```

#### Debug Ollama Issues
```bash
# Test Ollama connectivity
curl -v http://localhost:11434/api/tags

# Check Ollama service status
ollama list
ollama serve --help

# Check Ollama configuration
cat config.json | grep -A 10 '"ollama"'
```

#### Debug llama.cpp Issues
```bash
# Test Python package
python3 -c "import llama_cpp; print('✓ llama-cpp-python available')"

# Check model files
find ./models -name "*.gguf" -ls

# Check model directory permissions
ls -la ./models/

# Test model loading (if models exist)
python3 -c "
from llama_cpp import Llama
import os
models_dir = './models'
if os.path.exists(models_dir):
    gguf_files = [f for f in os.listdir(models_dir) if f.endswith('.gguf')]
    print(f'Found {len(gguf_files)} GGUF models: {gguf_files}')
else:
    print('Models directory not found')
"
```

#### Debug Configuration Issues
```bash
# Validate JSON syntax
python3 -c "import json; json.load(open('config.json')); print('✓ Valid JSON')"

# Check current backend configuration
python3 -c "
import json
config = json.load(open('config.json'))
print(f'Active backend: {config[\"backend\"][\"active\"]}')
print(f'Auto fallback: {config[\"backend\"][\"auto_fallback\"]}')
"

# Reset to default backend
./chat-manager.sh backend switch ollama
```

### Clean Restart
```bash
./chat-manager.sh force-stop
./chat-manager.sh start
```

### System Resource Check
```bash
# Check memory usage
free -h

# Check disk space
df -h

# Check port usage
netstat -tlnp | grep :3113
```

### Backend Performance Check
```bash
# Check backend response times
time ./chat-manager.sh backend health ollama
time ./chat-manager.sh backend health llamacpp

# Monitor backend switching performance
time ./chat-manager.sh backend switch llamacpp
time ./chat-manager.sh backend switch ollama
```

## Best Practices

### Development Workflow
1. Always activate virtual environment first
2. Use `status` command to check before starting
3. Use `logs` command for debugging
4. Use `restart` for quick iteration
5. **NEW**: Check backend status before development sessions
6. **NEW**: Test backend switching in development environment

### Multi-Backend Development (NEW)
1. **Backend Validation**: Always check backend health before switching
   ```bash
   ./chat-manager.sh backend health llamacpp
   ./chat-manager.sh backend switch llamacpp
   ```

2. **Testing Both Backends**: Regularly test with both backends
   ```bash
   # Test with Ollama
   ./chat-manager.sh backend switch ollama && ./chat-manager.sh restart
   
   # Test with llama.cpp
   ./chat-manager.sh backend switch llamacpp && ./chat-manager.sh restart
   ```

3. **Configuration Management**: Keep backend configurations updated
   - Ollama: Verify API endpoints and timeouts
   - llama.cpp: Keep model directory and parameters current

4. **Model Management**: For llama.cpp development
   - Keep GGUF models in the configured directory
   - Test with different model sizes for performance
   - Monitor disk space usage for large models

### Production Deployment
1. Set up log rotation for long-running instances
2. Monitor log files for errors
3. Use `force-stop` only in emergencies
4. Regular status checks for health monitoring
5. **NEW**: Implement backend health monitoring in production
6. **NEW**: Set up alerts for backend failures
7. **NEW**: Document backend switching procedures for operations team

### Backend Production Monitoring (NEW)
```bash
# Add to cron for regular health checks
*/5 * * * * /path/to/chat-manager.sh backend health >/dev/null || echo "Backend unhealthy" | logger

# Monitor backend status in production
./chat-manager.sh backend status >> /var/log/backend-status.log
```

### Maintenance
1. Regular cleanup of old log files
2. Monitor disk space usage in logs directory
3. Keep virtual environment updated
4. Backup configuration and log files
5. **NEW**: Regularly update backend dependencies
6. **NEW**: Keep GGUF models updated for llama.cpp
7. **NEW**: Monitor Ollama service health and updates
8. **NEW**: Test backend failover procedures periodically

## Integration with Flask Application

### Environment Variables
The manager sets the `PORT` environment variable:
```python
# In app.py
import os
port = int(os.environ.get('PORT', 3113))
```

### Application Configuration
Recommended Flask configuration for use with the manager:
```python
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3113))
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False,
        threaded=True  # As per your performance recommendations
    )
```

### Health Check Endpoint
Consider adding a health check endpoint:
```python
@app.route('/health')
def health_check():
    return {'status': 'healthy', 'timestamp': datetime.now().isoformat()}
```

## Multi-Backend Feature Summary (v2.0)

### New Commands Added
| Command | Description |
|---------|-------------|
| `./chat-manager.sh backend status` | Show all backend status with health indicators |
| `./chat-manager.sh backend list` | List available backends (alias for status) |
| `./chat-manager.sh backend switch <name>` | Switch between ollama and llamacpp backends |
| `./chat-manager.sh backend health [name]` | Check specific backend health |

### Key Benefits
- **🔄 Seamless Switching**: Switch between Ollama and llama.cpp without manual config editing
- **🩺 Health Monitoring**: Real-time health checks for both backends
- **⚡ Quick Setup**: Automated backend validation and configuration
- **🛡️ Error Prevention**: Health warnings before switching to unhealthy backends
- **📊 Status Visibility**: Clear indicators for backend availability and configuration

### Upgrade Notes
- **Backward Compatible**: All existing functionality preserved
- **Configuration Enhanced**: Existing config.json automatically supported
- **New Dependencies**: Optional llama-cpp-python for local inference
- **Model Directory**: ./models directory for GGUF files (auto-created)

This documentation provides comprehensive coverage of the Chat-O-Llama Process Manager's capabilities, operations, and best practices for effective use in both development and production environments with full multi-backend support.