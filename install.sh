#!/bin/bash

# Chat-O-Llama Auto Installer (Non-Interactive Version)
# Usage: curl -fsSL https://github.com/ukkit/chat-o-llama/raw/main/install.sh | bash
# Or: wget -O- https://github.com/ukkit/chat-o-llama/raw/main/install.sh | bash
# 
# Note: This installs Chat-O-Llama. For Ollama installation, use install-ollama.sh first.

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
MIN_PYTHON_VERSION="3.10"

# Non-interactive configuration (environment variables)
AUTO_CONFIRM="${CHAT_OLLAMA_AUTO_CONFIRM:-Y}"
HANDLE_EXISTING="${CHAT_OLLAMA_HANDLE_EXISTING:-1}"  # 1=remove, 2=update, 3=cancel
AUTO_START="${CHAT_OLLAMA_AUTO_START:-true}"
FORCE_REINSTALL="${CHAT_OLLAMA_FORCE_REINSTALL:-true}"

# Function to print colored output
print_header() {
    echo -e "${PURPLE}╔══════════════════════════════════════╗${NC}"
    echo -e "${PURPLE}║        Chat-O-Llama                  ║${NC}"
    echo -e "${PURPLE}║     Application Installer           ║${NC}"
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

    # Try different Python commands (only 3.10+)
    for cmd in python3 python python3.12 python3.11 python3.10; do
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
            print_info "• Ubuntu/Debian: sudo apt update && sudo apt install python3.10 python3.10-pip python3.10-venv"
            print_info "• CentOS/RHEL: sudo yum install python3.10 python3.10-pip"
            print_info "• macOS: brew install python@3.10"
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

    # Check if uv is available, install if not found
    if ! command_exists uv; then
        print_info "Installing uv..."
        if curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null 2>&1; then
            # Add uv to PATH for current session
            export PATH="$HOME/.cargo/bin:$PATH"
            print_success "uv installed successfully"
        else
            print_error "Failed to install uv. Please install manually."
            print_info "Run: curl -LsSf https://astral.sh/uv/install.sh | sh"
            exit 1
        fi
    else
        print_success "uv found at $(command -v uv)"
    fi

    # Ensure uv is available in PATH for the rest of the script
    if ! command_exists uv; then
        export PATH="$HOME/.cargo/bin:$PATH"
        if ! command_exists uv; then
            print_error "uv installation failed. Please install manually."
            exit 1
        fi
    fi
}

# Function to check Ollama dependency
check_ollama_dependency() {
    print_step "Checking Ollama dependency..."

    if ! command_exists ollama; then
        print_error "Ollama not found!"
        print_info "Chat-O-Llama requires Ollama to be installed first."
        print_info ""
        print_info "Please install Ollama first using one of these methods:"
        print_info "• Run: curl -fsSL https://github.com/ukkit/chat-o-llama/raw/main/install-ollama.sh | bash"
        print_info "• Or visit: https://ollama.com"
        print_info ""
        print_info "After installing Ollama, run this installer again."
        exit 1
    else
        print_success "Ollama found at $(command -v ollama)"
    fi

    # Check if Ollama service is running
    if ! ollama list >/dev/null 2>&1; then
        print_error "Ollama service is not running!"
        print_info "Please start Ollama service first:"
        print_info "• Try: ollama serve"
        print_info "• Or run: curl -fsSL https://github.com/ukkit/chat-o-llama/raw/main/install-ollama.sh | bash"
        print_info ""
        print_info "After starting Ollama, run this installer again."
        exit 1
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

    # Ensure uv is available in PATH
    if ! command_exists uv; then
        export PATH="$HOME/.cargo/bin:$PATH"
    fi

    print_info "Using uv for environment and dependency management..."
    
    # Create virtual environment with uv
    if uv venv venv >/dev/null 2>&1; then
        print_success "Virtual environment created with uv"
    else
        print_error "Failed to create virtual environment with uv"
        exit 1
    fi

    # Activate virtual environment
    source venv/bin/activate

    # Install dependencies with uv
    print_info "Installing Python dependencies with uv..."
    if [ -f "pyproject.toml" ]; then
        if uv sync >/dev/null 2>&1; then
            print_success "Dependencies installed successfully with uv"
        else
            print_error "Failed to install dependencies with uv"
            exit 1
        fi
    elif [ -f "requirements.txt" ]; then
        if uv pip install -r requirements.txt >/dev/null 2>&1; then
            print_success "Dependencies installed successfully with uv"
        else
            print_error "Failed to install dependencies with uv"
            exit 1
        fi
    else
        # Fallback installation with uv
        print_warning "No pyproject.toml or requirements.txt found, installing basic dependencies..."
        uv pip install Flask==3.0.0 requests==2.31.0 "mcp[cli]==1.1.0" >/dev/null 2>&1
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

    # Ollama connectivity is already verified in check_ollama_dependency()
    print_success "Installation verification complete"
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
    echo -e "${CYAN}    🚀 Chat-O-Llama Installation Complete! 🚀${NC}"
    echo -e "${CYAN}═══════════════════════════════════════${NC}"
    echo ""
    echo -e "${YELLOW}Installation Directory:${NC} $INSTALL_DIR"
    if [ "$AUTO_START" = "true" ]; then
        echo -e "${YELLOW}Service URL:${NC} http://localhost:$DEFAULT_PORT"
    fi
    echo ""
    echo -e "${YELLOW}Customization (set before running installer):${NC}"
    echo -e "  export CHAT_OLLAMA_INSTALL_DIR=/custom/path"
    echo -e "  export CHAT_OLLAMA_AUTO_START=false"
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
    echo -e "  uv sync"
    echo -e "  ./chat-manager.sh restart"
    echo ""
    echo -e "${YELLOW}Backend Management:${NC}"
    echo -e "  • Ollama: ./install-ollama.sh           # Install/manage Ollama"
    echo -e "  • Models: ollama pull <model>           # Add models"
    echo -e "  • Future: ./install-llamacpp.sh        # llama.cpp support"
    echo ""
    echo -e "${YELLOW}Available Models:${NC}"
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

    print_info "Chat-O-Llama installation starting..."
    print_info "Installation directory: $INSTALL_DIR"
    print_info "Auto-start: $AUTO_START"
    print_info "Requires: Ollama (checked during installation)"
    echo ""
    print_info "Customize with environment variables (see final instructions)"
    echo ""

    # NO USER CONFIRMATION - just start installation
    print_info "Starting installation automatically..."
    echo ""

    # Run installation steps with error handling
    check_python || handle_error
    check_ollama_dependency || handle_error
    check_install_directory || handle_error

    # Only download if not updating
    if [ ! -d "$INSTALL_DIR" ]; then
        download_project || handle_error
    fi

    cd "$INSTALL_DIR" || handle_error
    create_virtual_env || handle_error
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