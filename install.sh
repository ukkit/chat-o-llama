#!/bin/bash

# chat-o-llama Auto Installer (Non-Interactive Version)
# Usage: curl -fsSL https://github.com/ukkit/chat-o-llama/raw/main/install.sh | bash
# Or: wget -O- https://github.com/ukkit/chat-o-llama/raw/main/install.sh | bash

# For better compatibility, try to use bash if available
if command -v bash >/dev/null 2>&1; then
    if [ -z "$BASH_VERSION" ]; then
        # Re-execute with bash if we're not already running in bash
        exec bash "$0" "$@"
    fi
fi

# Exit on any error
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration with environment variable overrides
REPO_URL="https://github.com/ukkit/chat-o-llama.git"
INSTALL_DIR="${CHAT_OLLAMA_INSTALL_DIR:-$HOME/chat-o-llama}"
DEFAULT_PORT="${CHAT_OLLAMA_PORT:-3000}"
RECOMMENDED_MODEL="${CHAT_OLLAMA_MODEL:-qwen2.5:0.5b}"
FALLBACK_MODEL="tinyllama"
MIN_PYTHON_VERSION="3.8"

# Non-interactive configuration (environment variables)
AUTO_CONFIRM="${CHAT_OLLAMA_AUTO_CONFIRM:-Y}"
AUTO_DOWNLOAD_MODEL="${CHAT_OLLAMA_DOWNLOAD_MODEL:-Y}"
HANDLE_EXISTING="${CHAT_OLLAMA_HANDLE_EXISTING:-1}"  # 1=remove, 2=update, 3=cancel
AUTO_START="${CHAT_OLLAMA_AUTO_START:-true}"
FORCE_REINSTALL="${CHAT_OLLAMA_FORCE_REINSTALL:-true}"

# Function to print colored output
print_header() {
    echo -e "${PURPLE}╔══════════════════════════════════════╗${NC}"
    echo -e "${PURPLE}║           chat-o-llama 🦙            ║${NC}"
    echo -e "${PURPLE}║     Non-Interactive Installer       ║${NC}"
    echo -e "${PURPLE}╚══════════════════════════════════════╝${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

print_step() {
    echo -e "${CYAN}▶ $1${NC}"
}

# Function to check if command exists (POSIX compatible)
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to compare version numbers (POSIX compatible)
version_ge() {
    # Returns 0 (true) if version $1 >= $2
    # Simple version comparison without requiring sort -V
    local ver1="$1"
    local ver2="$2"

    # Convert versions to comparable numbers
    local ver1_major=$(echo "$ver1" | cut -d. -f1)
    local ver1_minor=$(echo "$ver1" | cut -d. -f2 2>/dev/null || echo "0")
    local ver2_major=$(echo "$ver2" | cut -d. -f1)
    local ver2_minor=$(echo "$ver2" | cut -d. -f2 2>/dev/null || echo "0")

    if [ "$ver1_major" -gt "$ver2_major" ]; then
        return 0
    elif [ "$ver1_major" -eq "$ver2_major" ] && [ "$ver1_minor" -ge "$ver2_minor" ]; then
        return 0
    else
        return 1
    fi
}

# Function to get Python version
get_python_version() {
    local python_cmd="$1"
    if command_exists "$python_cmd"; then
        "$python_cmd" -c "import sys; print('.'.join(map(str, sys.version_info[:2])))" 2>/dev/null || echo "0.0"
    else
        echo "0.0"
    fi
}

# Function to check Python installation
check_python() {
    print_step "Checking Python installation..."

    local python_cmd=""
    local python_version=""

    # Try different Python commands
    for cmd in python3 python python3.11 python3.10 python3.9 python3.8; do
        if command_exists "$cmd"; then
            local version=$(get_python_version "$cmd")
            if version_ge "$version" "$MIN_PYTHON_VERSION"; then
                python_cmd="$cmd"
                python_version="$version"
                break
            fi
        fi
    done

    if [ -z "$python_cmd" ]; then
        print_error "Python $MIN_PYTHON_VERSION or higher not found!"
        print_info "Installing Python automatically..."
        
        if command_exists apt-get; then
            sudo apt update >/dev/null 2>&1 && sudo apt install -y python3 python3-pip python3-venv >/dev/null 2>&1
        elif command_exists yum; then
            sudo yum install -y python3 python3-pip >/dev/null 2>&1
        elif command_exists brew; then
            brew install python3 >/dev/null 2>&1
        else
            print_error "Cannot install Python automatically."
            print_info "Please install Python $MIN_PYTHON_VERSION+ manually:"
            print_info "• Ubuntu/Debian: sudo apt update && sudo apt install python3 python3-pip python3-venv"
            print_info "• CentOS/RHEL: sudo yum install python3 python3-pip"
            print_info "• macOS: brew install python3"
            exit 1
        fi
        
        # Re-check after installation
        python_cmd="python3"
        python_version=$(get_python_version "$python_cmd")
        
        if [ "$python_version" = "0.0" ]; then
            print_error "Python installation failed"
            exit 1
        fi
    fi

    print_success "Python $python_version found at $(command -v "$python_cmd")"
    echo "PYTHON_CMD=$python_cmd" > /tmp/chat_ollama_env

    # Check if pip is available
    if ! "$python_cmd" -m pip --version >/dev/null 2>&1; then
        print_info "Installing pip..."
        if command_exists apt-get; then
            sudo apt-get update >/dev/null 2>&1 && sudo apt-get install -y python3-pip >/dev/null 2>&1
        elif command_exists yum; then
            sudo yum install -y python3-pip >/dev/null 2>&1
        else
            print_error "pip not found and cannot auto-install. Please install pip manually."
            exit 1
        fi
    fi

    # Check if venv module is available
    if ! "$python_cmd" -m venv --help >/dev/null 2>&1; then
        print_info "Installing venv module..."
        if command_exists apt-get; then
            sudo apt-get install -y python3-venv >/dev/null 2>&1
        else
            print_error "venv module not available. Please install python3-venv package."
            exit 1
        fi
    fi
}

# Function to check Ollama installation
check_ollama() {
    print_step "Checking Ollama installation..."

    if ! command_exists ollama; then
        print_info "Installing Ollama..."
        
        # Install Ollama using their non-interactive installer
        if curl -fsSL https://ollama.com/install.sh | sh >/dev/null 2>&1; then
            print_success "Ollama installed successfully!"
        else
            print_error "Failed to install Ollama automatically."
            print_info "Please install Ollama manually from: https://ollama.com"
            exit 1
        fi
    else
        print_success "Ollama found at $(command -v ollama)"
    fi

    # Check if Ollama service is running
    if ! ollama list >/dev/null 2>&1; then
        print_info "Starting Ollama service..."

        # Try to start Ollama service in background
        if command_exists systemctl; then
            # Try systemd service
            if systemctl is-enabled ollama >/dev/null 2>&1; then
                sudo systemctl start ollama >/dev/null 2>&1
                sleep 3
            fi
        fi

        # If still not working, start manually in background
        if ! ollama list >/dev/null 2>&1; then
            print_info "Starting Ollama service in background..."
            nohup ollama serve >/dev/null 2>&1 &
            sleep 5

            # Check again
            if ! ollama list >/dev/null 2>&1; then
                print_error "Could not start Ollama service."
                print_info "Please start Ollama manually with: ollama serve"
                print_info "Then run this installer again."
                exit 1
            fi
        fi
    fi

    print_success "Ollama service is running"
}

# Function to check if directory exists and handle it (NON-INTERACTIVE)
check_install_directory() {
    print_step "Checking installation directory..."

    if [ -d "$INSTALL_DIR" ]; then
        print_warning "Directory $INSTALL_DIR already exists"
        
        # Use environment variable or default behavior
        local choice="$HANDLE_EXISTING"
        
        case $choice in
            1)
                print_info "Removing existing directory for clean installation..."
                rm -rf "$INSTALL_DIR"
                ;;
            2)
                print_info "Updating existing installation..."
                cd "$INSTALL_DIR"
                if [ -d ".git" ]; then
                    if git pull origin main >/dev/null 2>&1; then
                        print_success "Updated successfully"
                        return 0
                    else
                        print_warning "Update failed, doing clean installation..."
                        cd ..
                        rm -rf "$INSTALL_DIR"
                    fi
                else
                    print_warning "Not a git repository, doing clean installation..."
                    cd ..
                    rm -rf "$INSTALL_DIR"
                fi
                ;;
            3)
                print_info "Installation cancelled by configuration."
                exit 0
                ;;
            *)
                print_info "Using default: removing existing directory..."
                rm -rf "$INSTALL_DIR"
                ;;
        esac
    fi
}

# Function to download chat-o-llama
download_project() {
    print_step "Downloading chat-o-llama from GitHub..."

    if ! command_exists git; then
        print_info "Installing git..."

        if command_exists apt-get; then
            sudo apt-get update >/dev/null 2>&1 && sudo apt-get install -y git >/dev/null 2>&1
        elif command_exists yum; then
            sudo yum install -y git >/dev/null 2>&1
        elif command_exists brew; then
            brew install git >/dev/null 2>&1
        else
            print_error "Cannot install git automatically. Please install git manually."
            exit 1
        fi
    fi

    # Clone the repository
    if git clone "$REPO_URL" "$INSTALL_DIR" >/dev/null 2>&1; then
        print_success "chat-o-llama downloaded successfully"
    else
        print_error "Failed to download chat-o-llama"
        print_info "You can manually download from: $REPO_URL"
        exit 1
    fi

    cd "$INSTALL_DIR"
}

# Function to create virtual environment
create_virtual_env() {
    print_step "Creating Python virtual environment..."

    # Source Python command from temp file
    source /tmp/chat_ollama_env

    if [ -d "venv" ]; then
        print_info "Removing existing virtual environment..."
        rm -rf venv
    fi

    # Create virtual environment
    if "$PYTHON_CMD" -m venv venv >/dev/null 2>&1; then
        print_success "Virtual environment created"
    else
        print_error "Failed to create virtual environment"
        exit 1
    fi

    # Activate virtual environment
    source venv/bin/activate

    # Upgrade pip
    print_info "Upgrading pip..."
    pip install --upgrade pip >/dev/null 2>&1

    # Install requirements
    print_info "Installing Python dependencies..."
    if [ -f "requirements.txt" ]; then
        if pip install -r requirements.txt >/dev/null 2>&1; then
            print_success "Dependencies installed successfully"
        else
            print_error "Failed to install dependencies"
            exit 1
        fi
    else
        # Fallback installation
        print_warning "requirements.txt not found, installing basic dependencies..."
        pip install Flask==3.0.0 requests==2.31.0 >/dev/null 2>&1
    fi
}

# Function to check and download Ollama models (NON-INTERACTIVE)
check_ollama_models() {
    print_step "Checking available Ollama models..."

    # Get list of installed models
    local models=$(ollama list 2>/dev/null | grep -v "NAME" | awk '{print $1}' | grep -v "^$" || echo "")

    if [ -z "$models" ]; then
        print_warning "No Ollama models found!"
        print_info "Recommended models for chat-o-llama:"
        print_info "• $RECOMMENDED_MODEL (smallest, ~380MB, good performance)"
        print_info "• $FALLBACK_MODEL (~637MB, ultra lightweight)"
        print_info "• llama3.2:1b (~1.3GB, better quality)"
        print_info "• phi3:mini (~2.3GB, excellent balance)"
        echo ""

        # Use environment variable for auto-download decision
        local download_choice="$AUTO_DOWNLOAD_MODEL"

        case "$download_choice" in
            [Yy]*|""|"true"|"1")  # Y, y, Yes, yes, true, 1, or empty (default)
                print_info "Downloading $RECOMMENDED_MODEL (this may take a few minutes)..."

                if ollama pull "$RECOMMENDED_MODEL" >/dev/null 2>&1; then
                    print_success "Model $RECOMMENDED_MODEL downloaded successfully!"
                else
                    print_warning "Failed to download $RECOMMENDED_MODEL, trying fallback..."

                    if ollama pull "$FALLBACK_MODEL" >/dev/null 2>&1; then
                        print_success "Fallback model $FALLBACK_MODEL downloaded successfully!"
                    else
                        print_warning "Failed to download any model."
                        print_info "You can download models later with:"
                        print_info "  ollama pull $RECOMMENDED_MODEL"
                        print_info "  ollama pull $FALLBACK_MODEL"
                    fi
                fi
                ;;
            *)
                print_info "Skipping model download. You can download models later with:"
                print_info "  ollama pull $RECOMMENDED_MODEL"
                print_info "  ollama pull $FALLBACK_MODEL"
                ;;
        esac
    else
        print_success "Found existing models:"
        echo "$models" | while read -r model; do
            if [ -n "$model" ]; then
                print_info "  • $model"
            fi
        done
    fi
}

# Function to make scripts executable
setup_permissions() {
    print_step "Setting up permissions..."

    if [ -f "chat-manager.sh" ]; then
        chmod +x chat-manager.sh
        print_success "Made chat-manager.sh executable"
    fi
}

# Function to test installation
test_installation() {
    print_step "Testing installation..."

    # Activate virtual environment
    source venv/bin/activate

    # Check if we can import required modules
    if python -c "import flask, requests; print('Dependencies OK')" >/dev/null 2>&1; then
        print_success "Python dependencies verified"
    else
        print_error "Python dependencies verification failed"
        return 1
    fi

    # Check if Ollama is responsive
    if ollama list >/dev/null 2>&1; then
        print_success "Ollama connectivity verified"
    else
        print_warning "Ollama connectivity issue"
        return 1
    fi

    return 0
}

# Function to start the application (OPTIONAL AUTO-START)
start_application() {
    if [ "$AUTO_START" != "true" ]; then
        print_info "Auto-start disabled. Use './chat-manager.sh start' to start the service."
        return 0
    fi

    print_step "Starting chat-o-llama..."

    # Activate virtual environment
    source venv/bin/activate

    # Find available port
    local port=$DEFAULT_PORT
    while netstat -ln 2>/dev/null | grep -q ":$port "; do
        port=$((port + 1))
    done

    if [ "$port" != "$DEFAULT_PORT" ]; then
        print_warning "Port $DEFAULT_PORT is in use, using port $port instead"
    fi

    # Start the application
    if [ -f "chat-manager.sh" ]; then
        print_info "Starting with chat-manager.sh..."
        ./chat-manager.sh start "$port" >/dev/null 2>&1 &
    else
        print_info "Starting manually..."
        mkdir -p logs
        nohup python app.py > logs/chat-o-llama.log 2>&1 &
        echo $! > process.pid
        sleep 3
    fi

    print_info "Waiting for service to start..."
    local max_attempts=10
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if curl -s "http://localhost:$port" >/dev/null 2>&1; then
            print_success "chat-o-llama started successfully at http://localhost:$port"
            break
        fi

        sleep 2
        attempt=$((attempt + 1))
    done

    if [ $attempt -gt $max_attempts ]; then
        print_warning "Service may still be starting. Check manually with: ./chat-manager.sh status"
    fi
}

# Function to show final instructions
show_final_instructions() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════${NC}"
    echo -e "${CYAN}       🚀 Installation Complete! 🚀${NC}"
    echo -e "${CYAN}═══════════════════════════════════════${NC}"
    echo ""
    echo -e "${YELLOW}Installation Directory:${NC} $INSTALL_DIR"
    if [ "$AUTO_START" = "true" ]; then
        echo -e "${YELLOW}Service URL:${NC} http://localhost:$DEFAULT_PORT"
    fi
    echo ""
    echo -e "${YELLOW}Customization (set before running installer):${NC}"
    echo -e "  export CHAT_OLLAMA_INSTALL_DIR=/custom/path"
    echo -e "  export CHAT_OLLAMA_MODEL=llama3.2:1b"
    echo -e "  export CHAT_OLLAMA_AUTO_START=false"
    echo -e "  export CHAT_OLLAMA_DOWNLOAD_MODEL=false"
    echo -e "  export CHAT_OLLAMA_HANDLE_EXISTING=2  # 1=remove, 2=update"
    echo ""
    echo -e "${YELLOW}To manage the service:${NC}"
    echo -e "  cd $INSTALL_DIR"
    echo -e "  source venv/bin/activate"
    echo -e "  ./chat-manager.sh [start|stop|status|restart]"
    echo ""
    echo -e "${YELLOW}To update chat-o-llama:${NC}"
    echo -e "  cd $INSTALL_DIR"
    echo -e "  git pull origin main"
    echo -e "  source venv/bin/activate"
    echo -e "  pip install -r requirements.txt"
    echo -e "  ./chat-manager.sh restart"
    echo ""
    echo -e "${YELLOW}To add more Ollama models:${NC}"
    echo -e "  ollama pull llama3.2:1b     # 1.3GB, good quality"
    echo -e "  ollama pull phi3:mini       # 2.3GB, excellent"
    echo -e "  ollama pull gemma2:2b       # 1.6GB, Google's model"
    echo ""
    echo -e "${GREEN}Support:${NC} https://github.com/ukkit/chat-o-llama"
}

# Function to cleanup on error (POSIX compatible)
cleanup_on_error() {
    local exit_code=$?
    if [ $exit_code -ne 0 ]; then
        print_error "Installation failed with exit code $exit_code. Cleaning up..."

        # Remove temp files
        rm -f /tmp/chat_ollama_env

        # Auto-cleanup partial installation (non-interactive)
        if [ -d "$INSTALL_DIR" ] && [ ! -f "$INSTALL_DIR/.git/config" ]; then
            print_info "Removing partial installation directory..."
            rm -rf "$INSTALL_DIR"
            print_info "Partial installation removed"
        fi
    fi
    exit $exit_code
}

# Set up error handling (POSIX compatible)
handle_error() {
    cleanup_on_error
}

# Main installation function (NON-INTERACTIVE)
main() {
    # Clear screen and show header
    clear
    print_header

    print_info "Non-interactive installation starting..."
    print_info "Installation directory: $INSTALL_DIR"
    print_info "Auto-start: $AUTO_START"
    print_info "Download model: $AUTO_DOWNLOAD_MODEL"
    echo ""
    print_info "Customize with environment variables (see final instructions)"
    echo ""

    # NO USER CONFIRMATION - just start installation
    print_info "Starting installation automatically..."
    echo ""

    # Run installation steps with error handling
    check_python || handle_error
    check_ollama || handle_error
    check_install_directory || handle_error

    # Only download if not updating
    if [ ! -d "$INSTALL_DIR" ]; then
        download_project || handle_error
    fi

    cd "$INSTALL_DIR" || handle_error
    create_virtual_env || handle_error
    check_ollama_models || handle_error
    setup_permissions || handle_error

    # Test installation
    if test_installation; then
        start_application || handle_error
        show_final_instructions
    else
        print_error "Installation test failed"
        print_info "You may need to troubleshoot manually"
        handle_error
    fi

    # Cleanup temp files
    rm -f /tmp/chat_ollama_env
}

# Check if running as root (warn but don't prevent)
if [ "$EUID" -eq 0 ]; then
    print_warning "Running as root is not recommended"
    print_info "Consider running as a regular user for better security"
    echo ""
fi

# Run main installation
main "$@"