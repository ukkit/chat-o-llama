#!/bin/bash

# Chat-O-Llama Process Manager with Multi-Backend Support
# Usage: ./chat-manager.sh [start|stop|status|restart|backend] [port|backend_name]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/process.pid"
CONFIG_FILE="${CONFIG_FILE:-$SCRIPT_DIR/config.json}"

# Create log directory if it doesn't exist
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"

# Generate log file with current datetime
CURRENT_DATETIME=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/chat-o-llama_$CURRENT_DATETIME.log"

DEFAULT_PORT=3113

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[DEBUG]${NC} $1"
}

# Backend detection and management functions
get_config_value() {
    local key=$1
    if [ -f "$CONFIG_FILE" ]; then
        python3 -c "
import json
import sys
try:
    with open('$CONFIG_FILE', 'r') as f:
        config = json.load(f)
    
    keys = '$key'.split('.')
    value = config
    for k in keys:
        value = value.get(k, None)
        if value is None:
            break
    
    if value is not None:
        print(value)
    else:
        sys.exit(1)
except Exception:
    sys.exit(1)
" 2>/dev/null
    else
        return 1
    fi
}

get_active_backend() {
    get_config_value "backend.active"
}

check_ollama_health() {
    local base_url=$(get_config_value "ollama.base_url")
    if [ -z "$base_url" ]; then
        base_url="http://localhost:11434"
    fi
    
    if command -v curl &> /dev/null; then
        curl -s --connect-timeout 5 --max-time 10 "$base_url/api/tags" > /dev/null 2>&1
        return $?
    else
        # Fallback using python
        python3 -c "
import urllib.request
import urllib.error
try:
    urllib.request.urlopen('$base_url/api/tags', timeout=5)
    exit(0)
except:
    exit(1)
" 2>/dev/null
        return $?
    fi
}

check_llamacpp_requirements() {
    # Check if llama-cpp-python is available
    python3 -c "import llama_cpp" 2>/dev/null
    local python_check=$?
    
    # Check if model directory exists and has GGUF files
    local model_path=$(get_config_value "llamacpp.model_path")
    if [ -z "$model_path" ]; then
        model_path="./models"
    fi
    
    local model_dir_check=1
    if [ -d "$SCRIPT_DIR/$model_path" ]; then
        if find "$SCRIPT_DIR/$model_path" -name "*.gguf" -type f | head -1 | grep -q .; then
            model_dir_check=0
        fi
    fi
    
    return $((python_check + model_dir_check))
}

check_backend_health() {
    local backend=${1:-$(get_active_backend)}
    
    case "$backend" in
        "ollama")
            check_ollama_health
            return $?
            ;;
        "llamacpp")
            check_llamacpp_requirements
            return $?
            ;;
        *)
            print_error "Unknown backend: $backend"
            return 1
            ;;
    esac
}

get_backend_status() {
    local backend=${1:-$(get_active_backend)}
    
    case "$backend" in
        "ollama")
            if check_ollama_health; then
                echo "healthy"
            else
                echo "unhealthy"
            fi
            ;;
        "llamacpp")
            if check_llamacpp_requirements; then
                echo "healthy"
            else
                echo "unhealthy"
            fi
            ;;
        *)
            echo "unknown"
            ;;
    esac
}

list_available_backends() {
    echo "Available backends:"
    
    # Check Ollama
    local ollama_status=$(get_backend_status "ollama")
    local ollama_icon=""
    case "$ollama_status" in
        "healthy") ollama_icon="${GREEN}✓${NC}" ;;
        "unhealthy") ollama_icon="${RED}✗${NC}" ;;
        *) ollama_icon="${YELLOW}?${NC}" ;;
    esac
    echo -e "  ollama   $ollama_icon $ollama_status"
    
    # Check LlamaCpp
    local llamacpp_status=$(get_backend_status "llamacpp")
    local llamacpp_icon=""
    case "$llamacpp_status" in
        "healthy") llamacpp_icon="${GREEN}✓${NC}" ;;
        "unhealthy") llamacpp_icon="${RED}✗${NC}" ;;
        *) llamacpp_icon="${YELLOW}?${NC}" ;;
    esac
    echo -e "  llamacpp $llamacpp_icon $llamacpp_status"
    
    echo ""
    local active_backend=$(get_active_backend)
    if [ -n "$active_backend" ]; then
        echo -e "Active backend: ${BLUE}$active_backend${NC}"
    else
        print_warning "No active backend configured"
    fi
}

switch_backend() {
    local new_backend=$1
    
    if [ -z "$new_backend" ]; then
        print_error "Backend name required"
        echo "Available backends: ollama, llamacpp"
        return 1
    fi
    
    case "$new_backend" in
        "ollama"|"llamacpp")
            # Check if backend is available
            local status=$(get_backend_status "$new_backend")
            if [ "$status" != "healthy" ]; then
                print_warning "Backend '$new_backend' is not healthy ($status)"
                print_info "Continuing anyway - backend may become available during runtime"
            fi
            
            # Update config file
            python3 -c "
import json
try:
    with open('$CONFIG_FILE', 'r') as f:
        config = json.load(f)
    
    config['backend']['active'] = '$new_backend'
    
    with open('$CONFIG_FILE', 'w') as f:
        json.dump(config, f, indent=2)
    
    print('Backend switched to: $new_backend')
except Exception as e:
    print(f'Error updating config: {e}')
    exit(1)
"
            if [ $? -eq 0 ]; then
                print_status "Backend switched to: $new_backend"
                print_info "Restart the application for changes to take effect"
            else
                print_error "Failed to switch backend"
                return 1
            fi
            ;;
        *)
            print_error "Unknown backend: $new_backend"
            print_info "Available backends: ollama, llamacpp"
            return 1
            ;;
    esac
}

# Function to check if port is in use
check_port() {
    local port=$1
    if lsof -i :$port > /dev/null 2>&1; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Function to get PID by port
get_pid_by_port() {
    local port=$1
    lsof -ti :$port 2>/dev/null
}

# Function to start the application
start_app() {
    local port=${1:-$DEFAULT_PORT}

    print_info "Starting Chat-O-Llama on port $port..."
    
    # Check backend configuration and health
    local active_backend=$(get_active_backend)
    if [ -n "$active_backend" ]; then
        print_info "Active backend: $active_backend"
        local backend_status=$(get_backend_status "$active_backend")
        case "$backend_status" in
            "healthy")
                print_status "Backend '$active_backend' is healthy ✓"
                ;;
            "unhealthy")
                print_warning "Backend '$active_backend' is not healthy - some features may not work"
                print_info "Check backend status with: $0 backend status"
                ;;
            *)
                print_warning "Backend '$active_backend' status unknown"
                ;;
        esac
    else
        print_warning "No active backend configured in config.json"
        print_info "Use: $0 backend switch <backend_name> to set a backend"
    fi

    # Check if already running
    if [ -f "$PID_FILE" ]; then
        local existing_pid=$(cat "$PID_FILE")
        if ps -p $existing_pid > /dev/null 2>&1; then
            print_warning "chat-o-llama is already running with PID $existing_pid"
            local running_port=$(lsof -p $existing_pid -i -a | grep LISTEN | awk '{print $9}' | cut -d: -f2)
            if [ -n "$running_port" ]; then
                print_info "Running on port: $running_port"
                print_info "Access at: http://localhost:$running_port"
            fi
            return 1
        else
            print_warning "Stale PID file found, removing..."
            rm -f "$PID_FILE"
        fi
    fi

    # Check if port is already in use
    if check_port $port; then
        local existing_pid=$(get_pid_by_port $port)
        print_error "Port $port is already in use by PID $existing_pid"
        print_info "Use 'lsof -i :$port' to see what's using it"
        print_info "Or try a different port: $0 start <port_number>"
        return 1
    fi

    # Check if app.py exists
    if [ ! -f "$SCRIPT_DIR/app.py" ]; then
        print_error "app.py not found in $SCRIPT_DIR"
        return 1
    fi

    # Check if virtual environment is activated, try to activate if not
    if [ -z "$VIRTUAL_ENV" ]; then
        print_warning "Virtual environment not activated, attempting to activate..."
        
        # Look for virtual environment in common locations
        if [ -f "$SCRIPT_DIR/venv/bin/activate" ]; then
            print_info "Found virtual environment at $SCRIPT_DIR/venv/"
            source "$SCRIPT_DIR/venv/bin/activate"
            if [ -n "$VIRTUAL_ENV" ]; then
                print_status "Successfully activated virtual environment: $VIRTUAL_ENV"
            else
                print_error "Failed to activate virtual environment at $SCRIPT_DIR/venv/"
                print_info "Please activate your virtual environment manually:"
                print_info "  source venv/bin/activate"
                print_info "  $0 start"
                return 1
            fi
        elif [ -f "$SCRIPT_DIR/.venv/bin/activate" ]; then
            print_info "Found virtual environment at $SCRIPT_DIR/.venv/"
            source "$SCRIPT_DIR/.venv/bin/activate"
            if [ -n "$VIRTUAL_ENV" ]; then
                print_status "Successfully activated virtual environment: $VIRTUAL_ENV"
            else
                print_error "Failed to activate virtual environment at $SCRIPT_DIR/.venv/"
                print_info "Please activate your virtual environment manually:"
                print_info "  source .venv/bin/activate"
                print_info "  $0 start"
                return 1
            fi
        else
            print_error "No virtual environment found!"
            print_info "Please create and activate a virtual environment first:"
            print_info "  uv venv venv (or python3 -m venv venv)"
            print_info "  source venv/bin/activate"
            print_info "  uv sync (or pip install -r requirements.txt)"
            print_info "  $0 start"
            return 1
        fi
    fi

    print_info "Using virtual environment: $VIRTUAL_ENV"

    # Check if Flask is installed
    if ! python -c "import flask" 2>/dev/null; then
        print_error "Flask not found in current environment"
        print_info "Install requirements with uv: uv sync"
        print_info "Or with pip: pip install flask requests"
        return 1
    fi

    # Detect Python command
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        print_error "Neither python nor python3 command found"
        return 1
    fi

    # Start the application in background
    print_status "Starting Chat-O-Llama..."
    nohup bash -c "
        cd '$SCRIPT_DIR'
        PORT=$port $PYTHON_CMD app.py
    " > "$LOG_FILE" 2>&1 &

    local app_pid=$!
    echo $app_pid > "$PID_FILE"

    # Wait a moment and check if it started successfully
    sleep 2
    if ps -p $app_pid > /dev/null 2>&1; then
        print_status "Chat-O-Llama started successfully!"
        print_info "PID: $app_pid"
        print_info "Port: $port"
        print_info "Log file: $LOG_FILE"
        print_info "Access at: http://localhost:$port"
        print_info ""
        print_info "To stop: $0 stop"
        print_info "To check status: $0 status"
        print_info "To view logs: tail -f $LOG_FILE"
    else
        print_error "Failed to start Chat-O-Llama"
        print_info "Check log file: $LOG_FILE"
        rm -f "$PID_FILE"
        return 1
    fi
}

# Function to stop the application
stop_app() {
    print_info "Stopping Chat-O-Llama..."

    local stopped_any=false

    # Method 1: Try to stop using PID file
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        print_info "Found PID file with PID: $pid"

        if ps -p $pid > /dev/null 2>&1; then
            print_info "Stopping process $pid..."

            # Get the port this process is using
            local port=$(lsof -p $pid -i -a 2>/dev/null | grep LISTEN | awk '{print $9}' | cut -d: -f2)
            if [ -n "$port" ]; then
                print_info "Process was running on port: $port"
            fi

            # Try graceful shutdown first
            kill $pid 2>/dev/null

            # Wait for graceful shutdown
            local count=0
            while ps -p $pid > /dev/null 2>&1 && [ $count -lt 10 ]; do
                sleep 1
                count=$((count + 1))
                printf "."
            done
            echo

            # Force kill if still running
            if ps -p $pid > /dev/null 2>&1; then
                print_warning "Process didn't stop gracefully, force killing..."
                kill -9 $pid 2>/dev/null
                sleep 1
            fi

            if ps -p $pid > /dev/null 2>&1; then
                print_error "Failed to stop process $pid"
            else
                print_status "Process $pid stopped successfully"
                stopped_any=true
            fi
        else
            print_warning "Process $pid from PID file is not running"
        fi

        rm -f "$PID_FILE"
    fi

    # Method 2: Find and kill any remaining Python processes running app.py
    print_info "Checking for any remaining Python processes..."
    local remaining_pids=$(pgrep -f "python.*app.py" | tr '\n' ' ')

    if [ -n "$remaining_pids" ]; then
        print_warning "Found remaining Python processes: $remaining_pids"
        for pid in $remaining_pids; do
            if ps -p $pid > /dev/null 2>&1; then
                local port=$(lsof -p $pid -i -a 2>/dev/null | grep LISTEN | awk '{print $9}' | cut -d: -f2)
                print_info "Killing Python process $pid (port: ${port:-unknown})"
                kill -9 $pid 2>/dev/null
                stopped_any=true
            fi
        done
        sleep 2
    fi

    # Method 3: Check specific ports and kill processes using them
    for port in 3113 3000 8080 5000 8000; do
        local port_pid=$(lsof -ti :$port 2>/dev/null)
        if [ -n "$port_pid" ]; then
            # Check if it's a Python process
            local cmd=$(ps -p $port_pid -o comm= 2>/dev/null)
            if [[ "$cmd" == "python"* ]]; then
                print_warning "Found Python process $port_pid still using port $port"
                kill -9 $port_pid 2>/dev/null
                stopped_any=true
            fi
        fi
    done

    # Final verification
    sleep 1
    local final_check=$(pgrep -f "python.*app.py" | tr '\n' ' ')
    if [ -n "$final_check" ]; then
        print_error "Some Python processes may still be running: $final_check"
        print_info "You may need to manually kill them:"
        for pid in $final_check; do
            local port=$(lsof -p $pid -i -a 2>/dev/null | grep LISTEN | awk '{print $9}' | cut -d: -f2)
            print_info "  kill -9 $pid  # (port: ${port:-unknown})"
        done
    else
        if [ "$stopped_any" = true ]; then
            print_status "All Chat-O-Llama processes stopped successfully"
        else
            print_info "No Chat-O-Llama processes were running"
        fi
    fi
}

# Function to force stop all related processes
force_stop() {
    print_warning "Force stopping all chat-o-llama processes..."

    # Kill all Python processes running app.py
    local pids=$(pgrep -f "python.*app.py")
    if [ -n "$pids" ]; then
        print_info "Force killing Python processes: $pids"
        for pid in $pids; do
            kill -9 $pid 2>/dev/null
        done
    fi

    # Kill processes on common ports
    for port in 3113 3000 8080 5000 8000 9000; do
        local port_pid=$(lsof -ti :$port 2>/dev/null)
        if [ -n "$port_pid" ]; then
            local cmd=$(ps -p $port_pid -o comm= 2>/dev/null)
            if [[ "$cmd" == "python"* ]] || [[ "$cmd" == *"flask"* ]]; then
                print_info "Force killing process $port_pid on port $port"
                kill -9 $port_pid 2>/dev/null
            fi
        fi
    done

    # Clean up PID file
    rm -f "$PID_FILE"

    print_status "Force stop completed"
}

# Function to restart the application
restart_app() {
    local port=${1:-$DEFAULT_PORT}
    print_info "Restarting Chat-O-Llama..."
    stop_app
    sleep 2
    start_app $port
}

# Function to check status
check_status() {
    print_info "=== Application Status ==="
    
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if ps -p $pid > /dev/null 2>&1; then
            local port=$(lsof -p $pid -i -a | grep LISTEN | awk '{print $9}' | cut -d: -f2)
            print_status "Chat-O-Llama is running"
            print_info "PID: $pid"
            print_info "Port: $port"
            print_info "Access at: http://localhost:$port"

            # Find the most recent log file for this session
            local latest_log=$(ls -t "$LOG_DIR"/chat-o-llama_*.log 2>/dev/null | head -n1)
            if [ -n "$latest_log" ]; then
                print_info "Current log file: $latest_log"
                print_info "Recent log entries:"
                tail -5 "$latest_log" | while read line; do
                    echo "  $line"
                done
            fi
        else
            print_warning "PID file exists but process $pid is not running"
            rm -f "$PID_FILE"
        fi
    else
        print_info "Chat-O-Llama is not running"

        # Check for orphaned processes
        local pids=$(pgrep -f "python.*app.py")
        if [ -n "$pids" ]; then
            print_warning "Found orphaned processes: $pids"
            for pid in $pids; do
                local port=$(lsof -p $pid -i -a | grep LISTEN | awk '{print $9}' | cut -d: -f2)
                print_info "PID $pid running on port $port"
            done
        fi
    fi
    
    echo ""
    print_info "=== Backend Status ==="
    list_available_backends
}

# Function to handle backend management commands
handle_backend_command() {
    local subcommand=$1
    local backend_name=$2
    
    case "$subcommand" in
        "status")
            list_available_backends
            ;;
        "switch")
            switch_backend "$backend_name"
            ;;
        "list")
            list_available_backends
            ;;
        "health")
            local backend=${backend_name:-$(get_active_backend)}
            if [ -n "$backend" ]; then
                print_info "Checking health of backend: $backend"
                if check_backend_health "$backend"; then
                    print_status "Backend '$backend' is healthy ✓"
                else
                    print_error "Backend '$backend' is not healthy ✗"
                    case "$backend" in
                        "ollama")
                            print_info "Make sure Ollama is running and accessible"
                            local base_url=$(get_config_value "ollama.base_url")
                            if [ -n "$base_url" ]; then
                                print_info "Configured URL: $base_url"
                            fi
                            ;;
                        "llamacpp")
                            print_info "Check if llama-cpp-python is installed and GGUF models are available"
                            local model_path=$(get_config_value "llamacpp.model_path")
                            if [ -n "$model_path" ]; then
                                print_info "Model path: $SCRIPT_DIR/$model_path"
                            fi
                            ;;
                    esac
                fi
            else
                print_error "No backend specified and no active backend configured"
            fi
            ;;
        *)
            print_error "Unknown backend command: $subcommand"
            echo ""
            echo "Backend management commands:"
            echo "  $0 backend status        - Show status of all backends"
            echo "  $0 backend list          - List all available backends"
            echo "  $0 backend switch <name> - Switch to a different backend"
            echo "  $0 backend health [name] - Check health of specific backend"
            echo ""
            echo "Available backends: ollama, llamacpp"
            return 1
            ;;
    esac
}

# Function to show usage
show_usage() {
    echo "Chat-O-Llama Process Manager with Multi-Backend Support"
    echo ""
    echo "Usage: $0 [command] [options]"
    echo ""
    echo "Prerequisites:"
    echo "  - Virtual environment must be created manually: uv venv venv (or python3 -m venv venv)"
    echo "  - Dependencies must be installed: uv sync (or pip install flask requests)"
    echo "  - Virtual environment must be activated before running: source venv/bin/activate"
    echo ""
    echo "Application Commands:"
    echo "  start [port]     - Start Chat-O-Llama (default port: $DEFAULT_PORT)"
    echo "  stop             - Stop Chat-O-Llama gracefully"
    echo "  force-stop       - Force kill all Chat-O-Llama processes"
    echo "  restart [port]   - Restart Chat-O-Llama"
    echo "  status           - Check application and backend status"
    echo "  logs             - Show recent logs"
    echo "  help             - Show this help message"
    echo ""
    echo "Backend Management Commands:"
    echo "  backend status        - Show status of all backends"
    echo "  backend list          - List all available backends"
    echo "  backend switch <name> - Switch to a different backend (ollama|llamacpp)"
    echo "  backend health [name] - Check health of specific backend"
    echo ""
    echo "Examples:"
    echo "  # Application management"
    echo "  source venv/bin/activate"
    echo "  $0 start         - Start on port $DEFAULT_PORT"
    echo "  $0 start 8080    - Start on port 8080"
    echo "  $0 stop          - Stop the service"
    echo "  $0 status        - Check status"
    echo ""
    echo "  # Backend management"
    echo "  $0 backend status           - Show all backend status"
    echo "  $0 backend switch ollama    - Switch to Ollama backend"
    echo "  $0 backend switch llamacpp  - Switch to llama.cpp backend"
    echo "  $0 backend health           - Check active backend health"
    echo ""
    echo "Setup (with uv - recommended):"
    echo "  1. uv venv venv"
    echo "  2. source venv/bin/activate"
    echo "  3. uv sync"
    echo "  4. $0 backend status  # Check backend availability"
    echo "  5. $0 start"
    echo ""
    echo "Setup (with pip - fallback):"
    echo "  1. python3 -m venv venv"
    echo "  2. source venv/bin/activate"
    echo "  3. pip install -r requirements.txt"
    echo "  4. $0 backend status  # Check backend availability"
    echo "  5. $0 start"
    echo ""
    echo "Files:"
    echo "  PID file: $PID_FILE"
    echo "  Config file: $CONFIG_FILE"
    echo "  Log directory: $LOG_DIR"
    echo "  Current log: chat-o-llama_YYYYMMDD_HHMMSS.log"
}

# Function to show logs
show_logs() {
    # Find the most recent log file
    local latest_log=$(ls -t "$LOG_DIR"/chat-o-llama_*.log 2>/dev/null | head -n1)

    if [ -n "$latest_log" ]; then
        print_info "Showing logs from: $latest_log (press Ctrl+C to exit):"
        tail -f "$latest_log"
    else
        print_warning "No log files found in: $LOG_DIR"
        print_info "Log files are created when you start the application with: $0 start"
    fi
}

# Main script logic
case "${1:-help}" in
    start)
        start_app $2
        ;;
    stop)
        stop_app
        ;;
    force-stop)
        force_stop
        ;;
    restart)
        restart_app $2
        ;;
    status)
        check_status
        ;;
    logs)
        show_logs
        ;;
    backend)
        handle_backend_command $2 $3
        ;;
    help|--help|-h)
        show_usage
        ;;
    *)
        print_error "Unknown command: $1"
        echo ""
        show_usage
        exit 1
        ;;
esac