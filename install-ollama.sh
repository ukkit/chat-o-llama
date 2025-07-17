#!/bin/bash

# Ollama Installer for Chat-O-Llama
# Usage: curl -fsSL https://github.com/ukkit/chat-o-llama/raw/main/install-ollama.sh | bash
# Or: wget -O- https://github.com/ukkit/chat-o-llama/raw/main/install-ollama.sh | bash

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
RECOMMENDED_MODEL="${CHAT_OLLAMA_MODEL:-qwen2.5:0.5b}"
FALLBACK_MODEL="tinyllama"

# Non-interactive configuration (environment variables)
AUTO_DOWNLOAD_MODEL="${CHAT_OLLAMA_DOWNLOAD_MODEL:-Y}"

# Function to print colored output
print_header() {
    echo -e "${PURPLE}╔══════════════════════════════════════╗${NC}"
    echo -e "${PURPLE}║        Ollama Installer              ║${NC}"
    echo -e "${PURPLE}║      for Chat-O-Llama Project       ║${NC}"
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

# Function to test Ollama installation
test_ollama() {
    print_step "Testing Ollama installation..."

    # Check if Ollama is responsive
    if ollama list >/dev/null 2>&1; then
        print_success "Ollama connectivity verified"
    else
        print_error "Ollama connectivity issue"
        return 1
    fi

    return 0
}

# Function to show final instructions
show_final_instructions() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════${NC}"
    echo -e "${CYAN}      🚀 Ollama Installation Complete!${NC}"
    echo -e "${CYAN}═══════════════════════════════════════${NC}"
    echo ""
    echo -e "${YELLOW}Ollama Service:${NC} Running and ready"
    echo -e "${YELLOW}Models Available:${NC}"
    
    # List installed models
    local models=$(ollama list 2>/dev/null | grep -v "NAME" | awk '{print $1}' | grep -v "^$" || echo "")
    if [ -n "$models" ]; then
        echo "$models" | while read -r model; do
            if [ -n "$model" ]; then
                echo -e "  • $model"
            fi
        done
    else
        echo -e "  • No models installed yet"
    fi
    
    echo ""
    echo -e "${YELLOW}Customization (set before running installer):${NC}"
    echo -e "  export CHAT_OLLAMA_MODEL=llama3.2:1b"
    echo -e "  export CHAT_OLLAMA_DOWNLOAD_MODEL=false"
    echo ""
    echo -e "${YELLOW}To add more models:${NC}"
    echo -e "  ollama pull llama3.2:1b     # 1.3GB, good quality"
    echo -e "  ollama pull phi3:mini       # 2.3GB, excellent"
    echo -e "  ollama pull gemma2:2b       # 1.6GB, Google's model"
    echo ""
    echo -e "${YELLOW}To manage Ollama:${NC}"
    echo -e "  ollama list                 # Show installed models"
    echo -e "  ollama pull <model>         # Download a model"
    echo -e "  ollama rm <model>           # Remove a model"
    echo -e "  ollama serve                # Start Ollama service manually"
    echo ""
    echo -e "${YELLOW}Next step:${NC}"
    echo -e "  Install Chat-O-Llama with: curl -fsSL https://github.com/ukkit/chat-o-llama/raw/main/install.sh | bash"
    echo ""
    echo -e "${GREEN}Support:${NC} https://github.com/ukkit/chat-o-llama"
}

# Function to cleanup on error (POSIX compatible)
cleanup_on_error() {
    local exit_code=$?
    if [ $exit_code -ne 0 ]; then
        print_error "Ollama installation failed with exit code $exit_code"
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

    print_info "Ollama installation starting..."
    print_info "Recommended model: $RECOMMENDED_MODEL"
    print_info "Auto-download model: $AUTO_DOWNLOAD_MODEL"
    echo ""
    print_info "Customize with environment variables (see final instructions)"
    echo ""

    # Start installation automatically
    print_info "Starting Ollama installation..."
    echo ""

    # Run installation steps with error handling
    check_ollama || handle_error
    check_ollama_models || handle_error

    # Test installation
    if test_ollama; then
        show_final_instructions
    else
        print_error "Ollama installation test failed"
        print_info "You may need to troubleshoot manually"
        handle_error
    fi
}

# Check if running as root (warn but don't prevent)
if [ "$EUID" -eq 0 ]; then
    print_warning "Running as root is not recommended"
    print_info "Consider running as a regular user for better security"
    echo ""
fi

# Run main installation
main "$@"