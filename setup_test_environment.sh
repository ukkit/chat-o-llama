#!/bin/bash

# Complete Testing Environment Setup Script (Updated for CMake)
# This script sets up both Ollama and llama.cpp for testing the multi-backend configuration

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"
VENV_DIR="$PROJECT_DIR/venv"
REQUIREMENTS_FILE="$PROJECT_DIR/requirements.txt"

print_header() {
    echo -e "\n${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${WHITE}$(printf "%*s" $(((58-${#1})/2)) "")$1$(printf "%*s" $(((58-${#1})/2)) "")${BLUE}║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}\n"
}

print_step() {
    echo -e "${CYAN}🚀 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

check_command() {
    if command -v "$1" >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Function to check if a service is running
check_service_running() {
    local url=$1
    curl -s "$url" >/dev/null 2>&1
}

# Function to check system capabilities
check_system_capabilities() {
    echo -e "${WHITE}System Information:${NC}"

    # OS Detection
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS_TYPE="Linux"
        if command -v lsb_release >/dev/null 2>&1; then
            OS_VERSION=$(lsb_release -d | cut -f2-)
        elif [[ -f /etc/os-release ]]; then
            OS_VERSION=$(grep PRETTY_NAME /etc/os-release | cut -d'"' -f2)
        else
            OS_VERSION="Unknown Linux"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS_TYPE="macOS"
        OS_VERSION=$(sw_vers -productVersion)
    else
        OS_TYPE="Unknown"
        OS_VERSION="Unknown"
    fi

    echo -e "  • ${CYAN}Operating System:${NC} $OS_TYPE $OS_VERSION"

    # CPU Detection
    if [[ "$OS_TYPE" == "Linux" ]]; then
        CPU_INFO=$(grep "model name" /proc/cpuinfo | head -1 | cut -d':' -f2 | xargs)
        CPU_CORES=$(nproc)
    elif [[ "$OS_TYPE" == "macOS" ]]; then
        CPU_INFO=$(sysctl -n machdep.cpu.brand_string)
        CPU_CORES=$(sysctl -n hw.ncpu)
    fi

    echo -e "  • ${CYAN}CPU:${NC} $CPU_INFO ($CPU_CORES cores)"

    # Memory Detection
    if [[ "$OS_TYPE" == "Linux" ]]; then
        MEMORY_GB=$(free -g | awk '/^Mem:/{print $2}')
    elif [[ "$OS_TYPE" == "macOS" ]]; then
        MEMORY_BYTES=$(sysctl -n hw.memsize)
        MEMORY_GB=$((MEMORY_BYTES / 1024 / 1024 / 1024))
    fi

    echo -e "  • ${CYAN}Memory:${NC} ${MEMORY_GB}GB"

    # GPU Detection
    GPU_INFO="None detected"
    if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi >/dev/null 2>&1; then
        GPU_INFO=$(nvidia-smi --query-gpu=name --format=csv,noheader,nounits | head -1)
        NVIDIA_GPU=true
    elif [[ "$OS_TYPE" == "macOS" ]] && sysctl -n machdep.cpu.brand_string | grep -q "Apple"; then
        GPU_INFO="Apple Silicon GPU (Metal)"
        APPLE_SILICON=true
    fi

    echo -e "  • ${CYAN}GPU:${NC} $GPU_INFO"
    echo ""
}

print_header "Multi-Backend Testing Environment Setup (Updated)"

check_system_capabilities

echo -e "${WHITE}This script will set up a complete testing environment for:${NC}"
echo -e "  • ${CYAN}Python Environment${NC} - Flask application dependencies"
echo -e "  • ${CYAN}Ollama${NC} - Local LLM serving"
echo -e "  • ${CYAN}llama.cpp${NC} - C++ LLM inference engine (CMake build)"
echo -e "  • ${CYAN}Configuration System${NC} - Multi-backend configuration files"
echo -e "  • ${CYAN}Testing Suite${NC} - Comprehensive validation tests"
echo ""

read -p "Continue with setup? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Setup cancelled."
    exit 0
fi

# Step 1: Setup Python environment
print_header "Python Environment Setup"

print_step "Checking Python installation..."
if check_command python3; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    print_success "Python $PYTHON_VERSION found"
else
    print_error "Python 3 is required but not found"
    exit 1
fi

print_step "Creating virtual environment..."
if [[ ! -d "$VENV_DIR" ]]; then
    python3 -m venv "$VENV_DIR"
    print_success "Virtual environment created"
else
    print_warning "Virtual environment already exists"
fi

print_step "Activating virtual environment..."
source "$VENV_DIR/bin/activate"
print_success "Virtual environment activated"

print_step "Creating requirements.txt..."
cat > "$REQUIREMENTS_FILE" << 'EOF'
# Flask web framework and dependencies
Flask==3.0.0
Werkzeug==3.0.1

# HTTP client for backend communication
requests==2.31.0
urllib3==2.1.0

# Configuration and utilities
python-dotenv==1.0.0

# Testing framework
pytest==7.4.3
pytest-flask==1.3.0

# Enhanced logging and output
colorama==0.4.6

# Performance monitoring
psutil==5.9.6

# JSON handling and validation
jsonschema==4.20.0

# Optional: Better error handling
rich==13.7.0

# Development tools
black==23.11.0
flake8==6.1.0
EOF

print_step "Installing Python dependencies..."
pip install --upgrade pip
pip install -r "$REQUIREMENTS_FILE"
print_success "Python dependencies installed"

# Step 2: Setup Ollama
print_header "Ollama Setup"

print_step "Checking if Ollama is installed..."
if check_command ollama; then
    print_success "Ollama is already installed"

    print_step "Checking if Ollama service is running..."
    if check_service_running "http://localhost:11434/api/tags"; then
        print_success "Ollama service is running"
    else
        print_step "Starting Ollama service..."
        if [[ "$OS_TYPE" == "macOS" ]]; then
            # macOS
            nohup ollama serve > ollama.log 2>&1 &
        else
            # Linux
            if systemctl is-active --quiet ollama 2>/dev/null; then
                print_success "Ollama service already running via systemd"
            else
                sudo systemctl start ollama 2>/dev/null || {
                    print_step "Starting Ollama manually..."
                    nohup ollama serve > ollama.log 2>&1 &
                }
            fi
        fi

        # Wait for service to start
        echo -n "Waiting for Ollama to start..."
        for i in {1..15}; do
            if check_service_running "http://localhost:11434/api/tags"; then
                echo ""
                print_success "Ollama service started"
                break
            fi
            echo -n "."
            sleep 2
        done

        if ! check_service_running "http://localhost:11434/api/tags"; then
            print_warning "Ollama may not have started properly. Check ollama.log"
        fi
    fi
else
    print_step "Installing Ollama..."
    if [[ "$OS_TYPE" == "Linux" ]]; then
        curl -fsSL https://ollama.ai/install.sh | sh
    elif [[ "$OS_TYPE" == "macOS" ]]; then
        if check_command brew; then
            brew install ollama
        else
            print_error "Please install Homebrew first or download Ollama from https://ollama.ai"
            exit 1
        fi
    else
        print_error "Please install Ollama manually from https://ollama.ai"
        exit 1
    fi

    print_step "Starting Ollama service..."
    nohup ollama serve > ollama.log 2>&1 &
    sleep 5

    # Wait for Ollama to be ready
    echo -n "Waiting for Ollama to be ready..."
    for i in {1..30}; do
        if check_service_running "http://localhost:11434/api/tags"; then
            echo ""
            print_success "Ollama is ready!"
            break
        fi
        echo -n "."
        sleep 2
    done
fi

print_step "Downloading test models for Ollama..."
TEST_MODELS=("llama3.2:1b" "qwen2.5:0.5b" "phi3:mini")

for model in "${TEST_MODELS[@]}"; do
    print_step "Checking model: $model"
    if ollama list | grep -q "$model"; then
        print_success "$model is already available"
    else
        print_step "Downloading $model (this may take a few minutes)..."
        if ollama pull "$model"; then
            print_success "Downloaded $model"
        else
            print_warning "Failed to download $model, continuing..."
            continue
        fi
    fi
done

# Step 3: Setup llama.cpp (Updated for CMake)
print_header "llama.cpp Setup (CMake Build)"

LLAMA_CPP_DIR="$PROJECT_DIR/llama.cpp"
MODELS_DIR="$PROJECT_DIR/llama_models"
BUILD_DIR="$LLAMA_CPP_DIR/build"

print_step "Creating models directory..."
mkdir -p "$MODELS_DIR"

print_step "Checking for llama.cpp..."
if [[ -d "$LLAMA_CPP_DIR" && -f "$BUILD_DIR/bin/llama-server" ]]; then
    print_success "llama.cpp is already built"
else
    print_step "Installing build dependencies..."
    if [[ "$OS_TYPE" == "Linux" ]]; then
        if check_command apt; then
            sudo apt update && sudo apt install -y build-essential cmake git wget pkg-config libssl-dev
            # Optional: Install OpenBLAS for better CPU performance
            sudo apt install -y libopenblas-dev || print_warning "OpenBLAS not available"
        elif check_command yum; then
            sudo yum groupinstall -y "Development Tools"
            sudo yum install -y cmake git wget openssl-devel
            sudo yum install -y openblas-devel || print_warning "OpenBLAS not available"
        elif check_command dnf; then
            sudo dnf groupinstall -y "Development Tools"
            sudo dnf install -y cmake git wget openssl-devel
            sudo dnf install -y openblas-devel || print_warning "OpenBLAS not available"
        elif check_command pacman; then
            sudo pacman -S --noconfirm base-devel cmake git wget openssl
            sudo pacman -S --noconfirm openblas || print_warning "OpenBLAS not available"
        fi
    elif [[ "$OS_TYPE" == "macOS" ]]; then
        if check_command brew; then
            brew install cmake git wget
            # Install Xcode command line tools if needed
            if ! xcode-select -p &> /dev/null; then
                print_step "Installing Xcode command line tools..."
                xcode-select --install
                echo "Please complete Xcode installation and re-run this script."
                exit 1
            fi
            # Optional: Install OpenBLAS for Intel Macs
            if ! sysctl -n machdep.cpu.brand_string | grep -q "Apple"; then
                brew install openblas || print_warning "OpenBLAS not available"
            fi
        fi
    fi

    # Verify cmake installation
    if ! check_command cmake; then
        print_error "CMake installation failed"
        exit 1
    fi

    CMAKE_VERSION=$(cmake --version | head -n1 | cut -d' ' -f3)
    print_success "CMake $CMAKE_VERSION installed"

    print_step "Cloning llama.cpp repository..."
    if [[ ! -d "$LLAMA_CPP_DIR" ]]; then
        git clone https://github.com/ggerganov/llama.cpp.git "$LLAMA_CPP_DIR"
    else
        cd "$LLAMA_CPP_DIR"
        git pull
    fi

    print_step "Building llama.cpp with CMake (this may take several minutes)..."
    cd "$LLAMA_CPP_DIR"

    # Configure CMake options based on system capabilities
    CMAKE_OPTIONS=(
        "-DCMAKE_BUILD_TYPE=Release"
        "-DGGML_NATIVE=ON"
        "-DLLAMA_SERVER=ON"
        "-DLLAMA_CURL=ON"
    )

    # Platform-specific optimizations
    if [[ "$OS_TYPE" == "macOS" ]]; then
        # Check for Apple Silicon
        if sysctl -n machdep.cpu.brand_string | grep -q "Apple"; then
            print_step "Detected Apple Silicon - enabling Metal support..."
            CMAKE_OPTIONS+=("-DGGML_METAL=ON")
        else
            print_step "Detected Intel Mac - using CPU optimizations..."
            if brew list openblas &>/dev/null; then
                CMAKE_OPTIONS+=("-DGGML_BLAS=ON" "-DGGML_BLAS_VENDOR=OpenBLAS")
            fi
        fi
    elif [[ "$OS_TYPE" == "Linux" ]]; then
        # Check for NVIDIA GPU
        if [[ "$NVIDIA_GPU" == true ]]; then
            print_step "NVIDIA GPU detected - enabling CUDA support..."
            CMAKE_OPTIONS+=("-DGGML_CUDA=ON")
        else
            print_step "Using CPU optimizations..."
            # Enable OpenBLAS if available
            if dpkg -l | grep -q libopenblas 2>/dev/null || rpm -qa | grep -q openblas 2>/dev/null; then
                CMAKE_OPTIONS+=("-DGGML_BLAS=ON" "-DGGML_BLAS_VENDOR=OpenBLAS")
            fi

            # Enable CPU instruction set optimizations
            if grep -q "avx2" /proc/cpuinfo 2>/dev/null; then
                CMAKE_OPTIONS+=("-DGGML_AVX2=ON")
            fi
            if grep -q "avx512" /proc/cpuinfo 2>/dev/null; then
                CMAKE_OPTIONS+=("-DGGML_AVX512=ON")
            fi
        fi
    fi

    echo "CMake options: ${CMAKE_OPTIONS[*]}"

    # Clean previous build
    rm -rf "$BUILD_DIR"

    # Configure and build
    if ! cmake -B "$BUILD_DIR" "${CMAKE_OPTIONS[@]}" .; then
        print_error "CMake configuration failed"
        exit 1
    fi

    # Build with parallel jobs
    CORES=$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)
    if ! cmake --build "$BUILD_DIR" --config Release --parallel "$CORES"; then
        print_error "Build failed"
        exit 1
    fi

    # Verify build
    SERVER_BINARY="$BUILD_DIR/bin/llama-server"
    if [[ -f "$SERVER_BINARY" ]]; then
        print_success "llama.cpp built successfully"
        chmod +x "$SERVER_BINARY"
    else
        print_error "Build failed - llama-server not found"
        ls -la "$BUILD_DIR"/bin/ 2>/dev/null || echo "Build directory not found"
        exit 1
    fi

    cd "$PROJECT_DIR"
fi

print_step "Downloading test models for llama.cpp..."
TEST_GGUF_MODELS=(
    "https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4_k_m.gguf|phi-3-mini-4k.gguf"
    "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf|qwen2.5-0.5b.gguf"
    "https://huggingface.co/bartowski/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q4_K_M.gguf|llama-3.2-1b.gguf"
)

for model_info in "${TEST_GGUF_MODELS[@]}"; do
    IFS='|' read -r url filename <<< "$model_info"
    model_path="$MODELS_DIR/$filename"

    if [[ -f "$model_path" ]]; then
        print_success "$filename already downloaded"
    else
        print_step "Downloading $filename..."
        if wget --progress=bar:force -O "$model_path" "$url"; then
            print_success "Downloaded $filename"
        else
            print_warning "Failed to download $filename, continuing..."
            rm -f "$model_path"  # Remove partial download
            continue
        fi
    fi
done

# Find first available model for testing
FIRST_MODEL=""
for model_file in "$MODELS_DIR"/*.gguf; do
    if [[ -f "$model_file" ]]; then
        FIRST_MODEL="$model_file"
        break
    fi
done

if [[ -n "$FIRST_MODEL" ]]; then
    print_step "Starting llama.cpp server..."

    # Kill existing server
    pkill -f "llama-server" 2>/dev/null || true
    sleep 2

    # Start new server
    SERVER_BINARY="$LLAMA_CPP_DIR/build/bin/llama-server"
    cd "$LLAMA_CPP_DIR"

    # Determine optimal settings
    THREADS=$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)

    # Build server arguments
    SERVER_ARGS=(
        "--model" "$FIRST_MODEL"
        "--host" "0.0.0.0"
        "--port" "8120"
        "--ctx-size" "4096"
        "--batch-size" "512"
        "--threads" "$THREADS"
        "--log-format" "text"
    )

    # Add GPU layers if supported
    if [[ "$APPLE_SILICON" == true ]] || [[ "$NVIDIA_GPU" == true ]]; then
        SERVER_ARGS+=("--n-gpu-layers" "32")
    fi

    nohup "$SERVER_BINARY" "${SERVER_ARGS[@]}" > llama_server.log 2>&1 &

    # Wait for server to start
    echo -n "Waiting for llama.cpp server to start..."
    for i in {1..20}; do
        if check_service_running "http://localhost:8120/v1/models"; then
            echo ""
            print_success "llama.cpp server started"
            break
        fi
        echo -n "."
        sleep 2
    done

    if ! check_service_running "http://localhost:8120/v1/models"; then
        print_warning "llama.cpp server may not have started properly. Check llama_server.log"
    fi

    cd "$PROJECT_DIR"
else
    print_warning "No GGUF models available - llama.cpp server not started"
fi

# Step 4: Create configuration files
print_header "Configuration Setup"

print_step "Creating test configuration..."
cat > "$PROJECT_DIR/test_config.json" << 'EOF'
{
  "app": {
    "host": "0.0.0.0",
    "port": 5000,
    "debug": true,
    "secret_key": "test-secret-key-for-development"
  },
  "database": {
    "path": "test_chat_database.db",
    "backup_enabled": true,
    "backup_interval_hours": 1
  },
  "backends": {
    "default": "ollama",
    "enabled": ["ollama", "llama_cpp"],
    "ollama": {
      "enabled": true,
      "url": "http://localhost:11434",
      "timeout": 10,
      "max_retries": 2,
      "health_check_interval": 30,
      "api_key": null
    },
    "llama_cpp": {
      "enabled": true,
      "url": "http://localhost:8120",
      "timeout": 15,
      "max_retries": 2,
      "health_check_interval": 30,
      "api_key": null,
      "openai_compatible": true,
      "chat_endpoint": "/v1/chat/completions",
      "models_endpoint": "/v1/models"
    }
  },
  "performance": {
    "model_cache_ttl": 60,
    "response_cache_enabled": false,
    "response_cache_ttl": 30,
    "max_concurrent_requests": 5
  },
  "ui": {
    "theme": "auto",
    "show_backend_indicators": true,
    "default_model_filter": "all",
    "enable_model_switching": true
  },
  "logging": {
    "level": "DEBUG",
    "file": "test_app.log",
    "max_size_mb": 5,
    "backup_count": 2
  },
  "security": {
    "rate_limit_per_minute": 30,
    "enable_cors": true,
    "allowed_origins": ["http://localhost:3000", "http://127.0.0.1:3000"]
  }
}
EOF

print_step "Creating environment file template..."
cat > "$PROJECT_DIR/.env.example" << 'EOF'
# Application Configuration
CHAT_APP_HOST=0.0.0.0
CHAT_APP_PORT=5000
CHAT_APP_DEBUG=true
CHAT_SECRET_KEY=development-secret-key

# Ollama Configuration
OLLAMA_URL=http://localhost:11434
OLLAMA_TIMEOUT=30
OLLAMA_ENABLED=true
# OLLAMA_API_KEY=your-api-key-here

# Llama.cpp Configuration
LLAMA_CPP_URL=http://localhost:8120
LLAMA_CPP_TIMEOUT=45
LLAMA_CPP_ENABLED=true
# LLAMA_CPP_API_KEY=your-api-key-here

# Database Configuration
DATABASE_PATH=test_chat_database.db

# Performance Configuration
MAX_CONCURRENT_REQUESTS=5
MODEL_CACHE_TTL=60
EOF

print_success "Configuration files created"

# Step 5: Run basic connectivity tests
print_header "Environment Testing"

print_step "Running basic connectivity tests..."

# Test Ollama
if check_service_running "http://localhost:11434/api/tags"; then
    print_success "Ollama connectivity test passed"

    # Test Ollama models
    OLLAMA_MODELS=$(curl -s http://localhost:11434/api/tags | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    models = [model['name'] for model in data.get('models', [])]
    print(f'{len(models)} models available: {', '.join(models[:3])}{'...' if len(models) > 3 else ''}')
except:
    print('Error parsing models')
" 2>/dev/null || echo "Models endpoint accessible")
    echo "  - $OLLAMA_MODELS"
else
    print_warning "Ollama connectivity test failed"
fi

# Test llama.cpp
if check_service_running "http://localhost:8120/v1/models"; then
    print_success "llama.cpp connectivity test passed"

    # Test llama.cpp models
    LLAMA_MODELS=$(curl -s http://localhost:8120/v1/models | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    models = [model['id'] for model in data.get('data', [])]
    print(f'{len(models)} models available: {', '.join(models[:3])}{'...' if len(models) > 3 else ''}')
except:
    print('Error parsing models')
" 2>/dev/null || echo "Models endpoint accessible")
    echo "  - $LLAMA_MODELS"
else
    print_warning "llama.cpp connectivity test failed"
fi

# Test configuration system
print_step "Testing configuration system..."
if python3 -c "
import sys
sys.path.append('.')
try:
    from config_manager import ConfigManager
    config = ConfigManager('test_config.json')
    enabled = config.get_enabled_backends()
    print(f'Configuration system working. Enabled backends: {', '.join(enabled)}')
except Exception as e:
    print(f'Configuration system error: {e}')
    sys.exit(1)
"; then
    print_success "Configuration system test passed"
else
    print_warning "Configuration system test failed - ensure config_manager.py exists"
fi

# Step 6: Print summary
print_header "Setup Complete"

echo -e "${WHITE}Your multi-backend testing environment is ready!${NC}\n"

echo -e "${CYAN}🔧 Services Status:${NC}"
if check_service_running "http://localhost:11434/api/tags"; then
    echo -e "  ✅ ${GREEN}Ollama${NC} - http://localhost:11434"
else
    echo -e "  ❌ ${RED}Ollama${NC} - Not running (check ollama.log)"
fi

if check_service_running "http://localhost:8120/v1/models"; then
    echo -e "  ✅ ${GREEN}llama.cpp${NC} - http://localhost:8120"
else
    echo -e "  ❌ ${RED}llama.cpp${NC} - Not running (check llama_server.log)"
fi

echo -e "\n${CYAN}🖥️  System Configuration:${NC}"
echo -e "  • ${WHITE}OS:${NC} $OS_TYPE $OS_VERSION"
echo -e "  • ${WHITE}CPU:${NC} $CPU_CORES cores"
echo -e "  • ${WHITE}Memory:${NC} ${MEMORY_GB}GB"
echo -e "  • ${WHITE}GPU:${NC} $GPU_INFO"

echo -e "\n${CYAN}📁 Project Structure:${NC}"
echo -e "  • ${WHITE}config_manager.py${NC} - Configuration management system"
echo -e "  • ${WHITE}test_config.json${NC} - Testing configuration"
echo -e "  • ${WHITE}test_environment.py${NC} - Comprehensive test suite"
echo -e "  • ${WHITE}app.py${NC} - Flask application (update with new config system)"
echo -e "  • ${WHITE}venv/${NC} - Python virtual environment"
echo -e "  • ${WHITE}llama.cpp/${NC} - llama.cpp installation (CMake build)"
echo -e "  • ${WHITE}llama_models/${NC} - GGUF model files"

echo -e "\n${CYAN}🚀 Next Steps:${NC}"
echo -e "  1. ${WHITE}Test the environment:${NC} python3 test_environment.py"
echo -e "  2. ${WHITE}Start your Flask app:${NC} python3 app.py"
echo -e "  3. ${WHITE}Check backend status:${NC} curl http://localhost:5000/api/config/status"
echo -e "  4. ${WHITE}Run configuration tests:${NC} python3 -c \"from config_manager import ConfigManager; ConfigManager('test_config.json')\""

echo -e "\n${CYAN}📋 Useful Commands:${NC}"
echo -e "  • ${WHITE}Activate environment:${NC} source venv/bin/activate"
echo -e "  • ${WHITE}Check Ollama models:${NC} ollama list"
echo -e "  • ${WHITE}View Ollama logs:${NC} tail -f ollama.log"
echo -e "  • ${WHITE}View llama.cpp logs:${NC} tail -f llama.cpp/llama_server.log"
echo -e "  • ${WHITE}Stop llama.cpp:${NC} pkill -f llama-server"
echo -e "  • ${WHITE}Test backends:${NC} curl http://localhost:11434/api/tags && curl http://localhost:8120/v1/models"

echo -e "\n${CYAN}🔍 Troubleshooting:${NC}"
echo -e "  • If services don't start, check the respective log files"
echo -e "  • For llama.cpp build issues, ensure all dependencies are installed"
echo -e "  • For Ollama issues, try: ${WHITE}ollama serve${NC} manually"
echo -e "  • For permission issues, ensure scripts are executable: ${WHITE}chmod +x *.sh${NC}"

echo -e "\n${GREEN}✨ Happy coding! Your multi-backend environment is ready for development.${NC}"
echo -e "${YELLOW}💡 Don't forget to activate your virtual environment: ${WHITE}source venv/bin/activate${NC}"