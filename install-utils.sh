#!/bin/bash

# Shared utilities for Chat-O-Llama installation scripts
# This file provides common functions used by install.sh and install-ollama.sh

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to print colored output
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

# Function to cleanup on error (POSIX compatible)
cleanup_on_error() {
    local exit_code=$?
    if [ $exit_code -ne 0 ]; then
        print_error "Installation failed with exit code $exit_code"
        
        # Remove temp files if they exist
        rm -f /tmp/chat_ollama_env 2>/dev/null || true
    fi
    exit $exit_code
}

# Set up error handling (POSIX compatible)
handle_error() {
    cleanup_on_error
}

# Check if running as root (warn but don't prevent)
check_root_warning() {
    if [ "$EUID" -eq 0 ]; then
        print_warning "Running as root is not recommended"
        print_info "Consider running as a regular user for better security"
        echo ""
    fi
}

# Function to clear screen and show a generic header
show_generic_header() {
    local title="$1"
    local subtitle="$2"
    
    clear
    echo -e "${PURPLE}╔══════════════════════════════════════╗${NC}"
    echo -e "${PURPLE}║$(printf "%38s" "$title")║${NC}"
    echo -e "${PURPLE}║$(printf "%38s" "$subtitle")║${NC}"
    echo -e "${PURPLE}╚══════════════════════════════════════╝${NC}"
    echo ""
}

# Function to show installation customization info
show_customization_info() {
    echo -e "${YELLOW}Customization (set before running installer):${NC}"
    echo -e "  export CHAT_OLLAMA_INSTALL_DIR=/custom/path"
    echo -e "  export CHAT_OLLAMA_MODEL=llama3.2:1b"
    echo -e "  export CHAT_OLLAMA_AUTO_START=false"
    echo -e "  export CHAT_OLLAMA_DOWNLOAD_MODEL=false"
    echo -e "  export CHAT_OLLAMA_HANDLE_EXISTING=2  # 1=remove, 2=update"
    echo ""
}

# Function to show support information
show_support_info() {
    echo -e "${GREEN}Support:${NC} https://github.com/ukkit/chat-o-llama"
}

# Function to detect package manager and install packages
install_system_package() {
    local package_name="$1"
    local apt_package="${2:-$package_name}"
    local yum_package="${3:-$package_name}"
    local brew_package="${4:-$package_name}"
    
    print_info "Installing $package_name..."
    
    if command_exists apt-get; then
        sudo apt-get update >/dev/null 2>&1 && sudo apt-get install -y "$apt_package" >/dev/null 2>&1
    elif command_exists yum; then
        sudo yum install -y "$yum_package" >/dev/null 2>&1
    elif command_exists brew; then
        brew install "$brew_package" >/dev/null 2>&1
    else
        print_error "Cannot install $package_name automatically."
        print_info "Please install $package_name manually:"
        print_info "• Ubuntu/Debian: sudo apt update && sudo apt install $apt_package"
        print_info "• CentOS/RHEL: sudo yum install $yum_package"
        print_info "• macOS: brew install $brew_package"
        return 1
    fi
    
    return 0
}

# Export functions for use in other scripts
export -f print_success print_error print_warning print_info print_step
export -f command_exists version_ge get_python_version
export -f cleanup_on_error handle_error check_root_warning
export -f show_generic_header show_customization_info show_support_info
export -f install_system_package