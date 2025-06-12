#!/bin/bash

# Llama.cpp Setup Script for Testing Environment (Updated for CMake)
# This script installs and configures llama.cpp server for testing using the latest CMake build system

set -e

echo "🦙 Setting up llama.cpp for testing environment (using CMake)..."

# Configuration
LLAMA_CPP_DIR="$HOME/llama.cpp"
MODELS_DIR="$HOME/llama_models"
SERVER_PORT=8120
SERVER_HOST="0.0.0.0"
BUILD_DIR="$LLAMA_CPP_DIR/build"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if llama.cpp server is running
check_server_running() {
    curl -s http://localhost:$SERVER_PORT/v1/models >/dev/null 2>&1
}

# Function to check CPU features
check_cpu_features() {
    echo "🔍 Checking CPU features..."
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if command_exists lscpu; then
            echo "CPU info:"
            lscpu | grep -E "(Model name|Flags)" || true

            # Check for specific instruction sets
            if grep -q "avx2" /proc/cpuinfo; then
                echo "✅ AVX2 support detected"
                AVX2_SUPPORT=true
            else
                echo "⚠️  AVX2 not detected"
                AVX2_SUPPORT=false
            fi

            if grep -q "avx512" /proc/cpuinfo; then
                echo "✅ AVX512 support detected"
                AVX512_SUPPORT=true
            else
                echo "⚠️  AVX512 not detected"
                AVX512_SUPPORT=false
            fi
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "CPU info:"
        sysctl -n machdep.cpu.brand_string

        # Check for Apple Silicon
        if sysctl -n machdep.cpu.brand_string | grep -q "Apple"; then
            echo "✅ Apple Silicon detected - Metal support will be enabled"
            APPLE_SILICON=true
        else
            echo "ℹ️  Intel Mac detected"
            APPLE_SILICON=false
        fi
    fi
}

# Create models directory
mkdir -p "$MODELS_DIR"

# Check CPU features first
check_cpu_features

# Install dependencies based on OS
echo "📦 Installing dependencies..."
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    if command_exists apt; then
        sudo apt update
        sudo apt install -y build-essential cmake git wget curl python3 python3-pip

        # Install additional build tools
        sudo apt install -y pkg-config libssl-dev ccache libcurl4-openssl-dev

        # Optional: Install OpenBLAS for better CPU performance
        sudo apt install -y libopenblas-dev

    elif command_exists yum; then
        sudo yum groupinstall -y "Development Tools"
        sudo yum install -y cmake git wget curl python3 python3-pip
        sudo yum install -y openssl-devel openblas-devel

    elif command_exists pacman; then
        sudo pacman -S --noconfirm base-devel cmake git wget curl python3 python3-pip
        sudo pacman -S --noconfirm openssl openblas

    elif command_exists dnf; then
        sudo dnf groupinstall -y "Development Tools"
        sudo dnf install -y cmake git wget curl python3 python3-pip
        sudo dnf install -y openssl-devel openblas-devel
    fi

elif [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    if ! command_exists brew; then
        echo "Please install Homebrew first: https://brew.sh"
        exit 1
    fi

    # Install Xcode command line tools if not present
    if ! xcode-select -p &> /dev/null; then
        echo "Installing Xcode command line tools..."
        xcode-select --install
        echo "Please complete the Xcode installation and run this script again."
        exit 1
    fi

    brew install cmake git wget curl python3

    # Optional: Install OpenBLAS for better CPU performance (if not Apple Silicon)
    if [[ "$APPLE_SILICON" != true ]]; then
        brew install openblas
    fi
fi

# Verify cmake installation
if ! command_exists cmake; then
    echo "❌ CMake installation failed"
    exit 1
fi

CMAKE_VERSION=$(cmake --version | head -n1 | cut -d' ' -f3)
echo "✅ CMake $CMAKE_VERSION installed"

# Clone llama.cpp if not exists
if [[ ! -d "$LLAMA_CPP_DIR" ]]; then
    echo "📥 Cloning llama.cpp repository..."
    git clone https://github.com/ggerganov/llama.cpp.git "$LLAMA_CPP_DIR"
else
    echo "✅ llama.cpp directory already exists"
    cd "$LLAMA_CPP_DIR"
    echo "📥 Updating llama.cpp repository..."
    git pull
fi

cd "$LLAMA_CPP_DIR"

# Determine CMake build options
echo "🔧 Configuring CMake build options..."
CMAKE_OPTIONS=()

# Basic options
CMAKE_OPTIONS+=("-DCMAKE_BUILD_TYPE=Release")
CMAKE_OPTIONS+=("-DGGML_NATIVE=ON")  # Enable native optimizations

# Platform-specific options
if [[ "$OSTYPE" == "darwin"* ]]; then
    if [[ "$APPLE_SILICON" == true ]]; then
        echo "🚀 Configuring for Apple Silicon with Metal support..."
        CMAKE_OPTIONS+=("-DGGML_METAL=ON")
    else
        echo "🚀 Configuring for Intel Mac..."
        CMAKE_OPTIONS+=("-DGGML_METAL=OFF")
        # Enable OpenBLAS for Intel Macs
        if brew list openblas &>/dev/null; then
            CMAKE_OPTIONS+=("-DGGML_BLAS=ON")
            CMAKE_OPTIONS+=("-DGGML_BLAS_VENDOR=OpenBLAS")
        fi
    fi
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "🚀 Configuring for Linux..."

    # Check for NVIDIA GPU
    if command_exists nvidia-smi && nvidia-smi &>/dev/null; then
        echo "🎮 NVIDIA GPU detected, enabling CUDA support..."
        CMAKE_OPTIONS+=("-DGGML_CUDA=ON")
    else
        echo "🖥️  No NVIDIA GPU detected, using CPU optimizations..."

        # Enable OpenBLAS if available
        if dpkg -l | grep -q libopenblas || rpm -qa | grep -q openblas; then
            CMAKE_OPTIONS+=("-DGGML_BLAS=ON")
            CMAKE_OPTIONS+=("-DGGML_BLAS_VENDOR=OpenBLAS")
        fi
    fi

    # Enable additional CPU optimizations
    if [[ "$AVX2_SUPPORT" == true ]]; then
        CMAKE_OPTIONS+=("-DGGML_AVX2=ON")
    fi

    if [[ "$AVX512_SUPPORT" == true ]]; then
        CMAKE_OPTIONS+=("-DGGML_AVX512=ON")
    fi
fi

# Always enable server build
CMAKE_OPTIONS+=("-DLLAMA_SERVER=ON")
CMAKE_OPTIONS+=("-DLLAMA_CURL=ON")  # Enable curl support for server

echo "CMake options: ${CMAKE_OPTIONS[*]}"

# Clean and build llama.cpp using CMake
echo "🔨 Building llama.cpp with CMake..."
if [[ -d "$BUILD_DIR" ]]; then
    echo "Cleaning previous build..."
    rm -rf "$BUILD_DIR"
fi

# Configure with CMake
echo "Configuring build..."
cmake -B "$BUILD_DIR" "${CMAKE_OPTIONS[@]}" .

if [[ $? -ne 0 ]]; then
    echo "❌ CMake configuration failed"
    exit 1
fi

# Build the project
echo "Building (this may take several minutes)..."
CORES=$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)
cmake --build "$BUILD_DIR" --config Release --parallel "$CORES"

if [[ $? -ne 0 ]]; then
    echo "❌ Build failed"
    exit 1
fi

# Verify build
SERVER_BINARY="$BUILD_DIR/bin/llama-server"
if [[ ! -f "$SERVER_BINARY" ]]; then
    echo "❌ Build failed - llama-server not found at $SERVER_BINARY"
    ls -la "$BUILD_DIR"/bin/ || echo "Build directory contents not found"
    exit 1
fi

echo "✅ Build successful - llama-server found at $SERVER_BINARY"

# Make server binary executable
chmod +x "$SERVER_BINARY"

# Download test models
echo "📥 Downloading test models..."

# Download small GGUF models for testing
TEST_MODELS=(
    "https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4_k_m.gguf|phi-3-mini-4k.gguf"
    "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf|qwen2.5-0.5b.gguf"
    "https://huggingface.co/bartowski/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q4_K_M.gguf|llama-3.2-1b.gguf"
)

for model_info in "${TEST_MODELS[@]}"; do
    IFS='|' read -r url filename <<< "$model_info"
    model_path="$MODELS_DIR/$filename"

    if [[ -f "$model_path" ]]; then
        echo "✅ $filename already downloaded"
    else
        echo "Downloading $filename..."
        if wget --progress=bar:force -O "$model_path" "$url"; then
            echo "✅ Downloaded $filename"
        else
            echo "⚠️  Failed to download $filename, continuing..."
            rm -f "$model_path"  # Remove partial download
            continue
        fi
    fi
done

# Find the first available model
FIRST_MODEL=""
for model_file in "$MODELS_DIR"/*.gguf; do
    if [[ -f "$model_file" ]]; then
        FIRST_MODEL="$model_file"
        break
    fi
done

if [[ -z "$FIRST_MODEL" ]]; then
    echo "❌ No models available for testing"
    echo "You can manually download a GGUF model to $MODELS_DIR"
    exit 1
fi

echo "🚀 Starting llama.cpp server..."

# Kill existing server if running
pkill -f "llama-server" 2>/dev/null || true
sleep 2

# Start server in background with optimized settings
echo "Starting server with model: $(basename "$FIRST_MODEL")"

# Determine optimal settings
THREADS=$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)
CONTEXT_SIZE=4096
BATCH_SIZE=512

# Additional server arguments based on platform
SERVER_ARGS=(
    "--model" "$FIRST_MODEL"
    "--host" "$SERVER_HOST"
    "--port" "$SERVER_PORT"
    "--ctx-size" "$CONTEXT_SIZE"
    "--batch-size" "$BATCH_SIZE"
    "--threads" "$THREADS"
    "--log-format" "text"
    "--verbose"
)

# Platform-specific optimizations
if [[ "$OSTYPE" == "darwin"* ]] && [[ "$APPLE_SILICON" == true ]]; then
    # Enable GPU layers for Apple Silicon
    SERVER_ARGS+=("--n-gpu-layers" "32")
elif command_exists nvidia-smi && nvidia-smi &>/dev/null; then
    # Enable GPU layers for NVIDIA
    SERVER_ARGS+=("--n-gpu-layers" "32")
fi

nohup "$SERVER_BINARY" "${SERVER_ARGS[@]}" > llama_server.log 2>&1 &
SERVER_PID=$!

echo "Server PID: $SERVER_PID"

# Wait for server to be ready
echo "⏳ Waiting for llama.cpp server to be ready..."
for i in {1..30}; do
    if check_server_running; then
        echo "✅ llama.cpp server is ready!"
        break
    fi
    if ! kill -0 $SERVER_PID 2>/dev/null; then
        echo "❌ Server process died. Check logs:"
        tail -20 llama_server.log
        exit 1
    fi
    echo "Waiting... ($i/30)"
    sleep 2
done

if ! check_server_running; then
    echo "❌ Failed to start llama.cpp server. Check logs:"
    tail -20 llama_server.log
    exit 1
fi

# Test llama.cpp API
echo "🧪 Testing llama.cpp API..."

# Test models endpoint
echo "Testing /v1/models endpoint..."
MODELS_RESPONSE=$(curl -s http://localhost:$SERVER_PORT/v1/models)
if [[ $? -eq 0 ]]; then
    echo "✅ Models endpoint working"
    echo "Available models:"
    echo "$MODELS_RESPONSE" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    for model in data.get('data', []):
        print(f\"  - {model['id']}\")
except Exception as e:
    print(f'Error parsing models response: {e}')
    " 2>/dev/null || echo "  - Response received but parsing failed"
else
    echo "❌ Models endpoint failed"
fi

# Test chat completions
echo "Testing /v1/chat/completions endpoint..."
CHAT_RESPONSE=$(curl -s -X POST http://localhost:$SERVER_PORT/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{
        "model": "test",
        "messages": [
            {"role": "user", "content": "Hello, world! Please respond with just a greeting."}
        ],
        "max_tokens": 20,
        "temperature": 0.1
    }')

if [[ $? -eq 0 ]]; then
    echo "✅ Chat completions test successful"
    echo "Response preview:"
    echo "$CHAT_RESPONSE" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    content = data['choices'][0]['message']['content']
    print(f'  Generated: {content[:100]}...' if len(content) > 100 else f'  Generated: {content}')
except Exception as e:
    print(f'  Error parsing response: {e}')
    " 2>/dev/null || echo "  - Response received but parsing failed"
else
    echo "❌ Chat completions test failed"
fi

# Test health endpoint
echo "Testing /health endpoint..."
HEALTH_RESPONSE=$(curl -s http://localhost:$SERVER_PORT/health || echo "No health endpoint")
if [[ "$HEALTH_RESPONSE" != "No health endpoint" ]]; then
    echo "✅ Health endpoint working"
else
    echo "ℹ️  Health endpoint not available (expected for some versions)"
fi

echo ""
echo "🎉 llama.cpp setup complete!"
echo "📊 Service status:"
echo "  - URL: http://localhost:$SERVER_PORT"
echo "  - Models endpoint: http://localhost:$SERVER_PORT/v1/models"
echo "  - Chat endpoint: http://localhost:$SERVER_PORT/v1/chat/completions"
echo "  - Server binary: $SERVER_BINARY"
echo "  - Build directory: $BUILD_DIR"
echo "  - Available models in $MODELS_DIR:"
ls -la "$MODELS_DIR"/*.gguf 2>/dev/null | awk '{print "    - " $9 " (" $5 " bytes)"}' || echo "    - No models found"

echo ""
echo "🔧 Build Configuration:"
echo "  - CMake options: ${CMAKE_OPTIONS[*]}"
echo "  - Threads used: $THREADS"
echo "  - Context size: $CONTEXT_SIZE"
echo "  - Batch size: $BATCH_SIZE"

echo ""
echo "💡 Useful commands:"
echo "  - View server logs: tail -f $LLAMA_CPP_DIR/llama_server.log"
echo "  - Stop server: kill $SERVER_PID  # or pkill -f llama-server"
echo "  - Server status: curl http://localhost:$SERVER_PORT/v1/models"
echo "  - Restart server: cd $LLAMA_CPP_DIR && $SERVER_BINARY --model <model-path> --host $SERVER_HOST --port $SERVER_PORT"
echo "  - List built binaries: ls -la $BUILD_DIR/bin/"
echo ""
echo "🔗 Integration ready! Your llama.cpp server is compatible with OpenAI API format."