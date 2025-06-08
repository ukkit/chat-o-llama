# Chat-O-Llama Process Manager Documentation

## Overview

The Chat-O-Llama Process Manager (`chat-manager.sh`) is a comprehensive shell script designed to manage the lifecycle of the Chat-O-Llama Flask application. It provides robust process management, logging, error handling, and monitoring capabilities for production and development environments.

## Core Features

### 1. Process Management
- **Graceful startup and shutdown** of Flask applications
- **PID-based process tracking** with file persistence
- **Port conflict detection** and resolution
- **Orphaned process cleanup** and management
- **Force-kill capabilities** for stuck processes

### 2. Environment Management
- **Virtual environment validation** before startup
- **Dependency checking** (Flask, requests)
- **Python version detection** (python3/python)
- **Port availability verification**

### 3. Logging System
- **Timestamped log files** with datetime naming convention
- **Centralized log directory** structure
- **Real-time log monitoring** capabilities
- **Log file rotation** and management

## File Structure

```
project-root/
├── chat-manager.sh           # Main process manager script
├── app.py                   # Flask application
├── process.pid              # PID file (created at runtime)
├── logs/                    # Log directory
│   └── chat-o-llama_YYYYMMDD_HHMMSS.log
└── venv/                    # Virtual environment
```

## Commands Reference

### Basic Operations

#### Start Application
```bash
./chat-manager.sh start [port]
```
- **Default port**: 3000
- **Custom port**: `./chat-manager.sh start 8080`
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
- Cleans up processes on common ports (3000, 8080, 5000, 8000, 9000)
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

2. **Process Creation**
   - Start Flask app in background using `nohup`
   - Capture process PID
   - Create PID file for tracking
   - Generate timestamped log file

3. **Verification**
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
- **Default Ports**: 3000 (primary), 8080, 5000, 8000, 9000
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

## Error Handling

### Common Issues and Solutions

#### 1. Port Already in Use
```
[ERROR] Port 3000 is already in use by PID 12345
```
**Solutions**:
- Use different port: `./chat-manager.sh start 8080`
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
lsof -i :3000
```

### Debug Startup Issues
```bash
# Check recent logs
./chat-manager.sh logs

# Manual startup for debugging
source venv/bin/activate
python app.py
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
netstat -tlnp | grep :3000
```

## Best Practices

### Development Workflow
1. Always activate virtual environment first
2. Use `status` command to check before starting
3. Use `logs` command for debugging
4. Use `restart` for quick iteration

### Production Deployment
1. Set up log rotation for long-running instances
2. Monitor log files for errors
3. Use `force-stop` only in emergencies
4. Regular status checks for health monitoring

### Maintenance
1. Regular cleanup of old log files
2. Monitor disk space usage in logs directory
3. Keep virtual environment updated
4. Backup configuration and log files

## Integration with Flask Application

### Environment Variables
The manager sets the `PORT` environment variable:
```python
# In app.py
import os
port = int(os.environ.get('PORT', 3000))
```

### Application Configuration
Recommended Flask configuration for use with the manager:
```python
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
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

This documentation provides comprehensive coverage of the Chat-O-Llama Process Manager's capabilities, operations, and best practices for effective use in both development and production environments.