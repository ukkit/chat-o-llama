#!/bin/bash

# GGUF Model Download Utility for Chat-O-Llama
# Downloads GGUF files from HuggingFace and moves them to the configured model directory

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${CONFIG_FILE:-$SCRIPT_DIR/config.json}"
DEFAULT_MODEL_DIR="./llama_models"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
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

print_progress() {
    echo -e "${CYAN}[PROGRESS]${NC} $1"
}

# Function to get configuration value from config.json
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

# Function to get model directory from config
get_model_directory() {
    local model_dir=$(get_config_value "llamacpp.model_path")
    if [ -z "$model_dir" ]; then
        model_dir="$DEFAULT_MODEL_DIR"
    fi
    
    # Convert relative path to absolute
    if [[ "$model_dir" != /* ]]; then
        model_dir="$SCRIPT_DIR/$model_dir"
    fi
    
    echo "$model_dir"
}

# Function to validate HuggingFace URL
validate_huggingface_url() {
    local url=$1
    
    # Check if it's a HuggingFace URL
    if [[ ! "$url" =~ ^https://huggingface\.co/ ]]; then
        print_error "URL must be from HuggingFace (https://huggingface.co/)"
        return 1
    fi
    
    # Check if it's a resolve URL (direct file link)
    if [[ "$url" =~ /resolve/main/.*\.gguf$ ]]; then
        print_info "Direct GGUF file URL detected"
        return 0
    fi
    
    # Check if it's a model page URL that we can convert
    if [[ "$url" =~ ^https://huggingface\.co/[^/]+/[^/]+/?$ ]]; then
        print_info "Model page URL detected - you'll need to specify the exact .gguf file"
        print_info "Example: https://huggingface.co/model/repo/resolve/main/model.gguf"
        return 1
    fi
    
    print_error "Invalid HuggingFace URL format"
    print_info "Expected format: https://huggingface.co/USER/REPO/resolve/main/FILE.gguf"
    return 1
}

# Function to extract filename from URL
extract_filename() {
    local url=$1
    local filename=$(basename "$url")
    
    # Ensure it has .gguf extension
    if [[ ! "$filename" =~ \.gguf$ ]]; then
        print_error "File must have .gguf extension"
        return 1
    fi
    
    echo "$filename"
}

# Function to download file with progress
download_file() {
    local url=$1
    local output_path=$2
    local filename=$(basename "$output_path")
    
    print_progress "Downloading $filename..."
    print_info "URL: $url"
    print_info "Destination: $output_path"
    
    # Check if file already exists
    if [ -f "$output_path" ]; then
        print_warning "File already exists: $output_path"
        read -p "Overwrite? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_info "Download cancelled"
            return 1
        fi
        rm -f "$output_path"
    fi
    
    # Create temporary download path
    local temp_path="${output_path}.tmp"
    
    # Download with progress bar
    if command -v wget &> /dev/null; then
        print_info "Using wget for download..."
        if wget --progress=bar:force --timeout=30 --tries=3 -O "$temp_path" "$url"; then
            mv "$temp_path" "$output_path"
            print_status "Download completed successfully"
            return 0
        else
            print_error "wget download failed"
            rm -f "$temp_path"
            return 1
        fi
    elif command -v curl &> /dev/null; then
        print_info "Using curl for download..."
        if curl -L --progress-bar --max-time 1800 --retry 3 -o "$temp_path" "$url"; then
            mv "$temp_path" "$output_path"
            print_status "Download completed successfully"
            return 0
        else
            print_error "curl download failed"
            rm -f "$temp_path"
            return 1
        fi
    else
        print_error "Neither wget nor curl is available"
        print_info "Please install wget or curl to download files"
        return 1
    fi
}

# Function to verify GGUF file integrity
verify_gguf_file() {
    local file_path=$1
    local filename=$(basename "$file_path")
    
    print_info "Verifying GGUF file integrity..."
    
    # Check file size (should be > 1MB for any valid GGUF)
    local file_size=$(stat -c%s "$file_path" 2>/dev/null || stat -f%z "$file_path" 2>/dev/null || echo "0")
    if [ "$file_size" -lt 1048576 ]; then
        print_error "File size too small ($file_size bytes) - likely corrupted"
        return 1
    fi
    
    # Check GGUF magic bytes (first 4 bytes should be "GGUF")
    local magic_bytes=$(head -c 4 "$file_path" 2>/dev/null || echo "")
    if [ "$magic_bytes" != "GGUF" ]; then
        print_warning "File doesn't start with GGUF magic bytes - may not be a valid GGUF file"
        print_info "Continuing anyway..."
    fi
    
    print_status "File verification completed"
    print_info "File size: $(numfmt --to=iec $file_size)"
    
    return 0
}

# Function to show model directory info
show_model_info() {
    local model_dir=$(get_model_directory)
    
    print_info "Model directory configuration:"
    print_info "  Directory: $model_dir"
    print_info "  Config source: $CONFIG_FILE"
    
    if [ -d "$model_dir" ]; then
        print_info "  Status: Directory exists"
        local model_count=$(find "$model_dir" -name "*.gguf" -type f | wc -l)
        print_info "  Current models: $model_count GGUF files"
        
        if [ "$model_count" -gt 0 ]; then
            print_info "  Existing models:"
            find "$model_dir" -name "*.gguf" -type f | while read -r model; do
                local size=$(stat -c%s "$model" 2>/dev/null || stat -f%z "$model" 2>/dev/null || echo "0")
                local formatted_size=$(numfmt --to=iec "$size")
                print_info "    - $(basename "$model") ($formatted_size)"
            done
        fi
    else
        print_warning "  Status: Directory does not exist (will be created)"
    fi
}

# Function to download multiple files from a list
download_batch() {
    local url_file=$1
    
    if [ ! -f "$url_file" ]; then
        print_error "URL file not found: $url_file"
        return 1
    fi
    
    local model_dir=$(get_model_directory)
    mkdir -p "$model_dir"
    
    print_status "Starting batch download from $url_file"
    print_info "Target directory: $model_dir"
    
    local line_num=0
    local success_count=0
    local error_count=0
    
    while IFS= read -r line || [ -n "$line" ]; do
        line_num=$((line_num + 1))
        
        # Skip empty lines and comments
        if [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]]; then
            continue
        fi
        
        # Parse URL and optional filename
        local url filename
        if [[ "$line" =~ \| ]]; then
            url=$(echo "$line" | cut -d'|' -f1 | xargs)
            filename=$(echo "$line" | cut -d'|' -f2 | xargs)
        else
            url=$(echo "$line" | xargs)
            filename=$(extract_filename "$url")
        fi
        
        print_progress "Processing line $line_num: $filename"
        
        # Validate URL
        if ! validate_huggingface_url "$url"; then
            print_error "Invalid URL on line $line_num: $url"
            error_count=$((error_count + 1))
            continue
        fi
        
        # Download file
        local output_path="$model_dir/$filename"
        if download_file "$url" "$output_path"; then
            if verify_gguf_file "$output_path"; then
                success_count=$((success_count + 1))
                print_status "Successfully downloaded: $filename"
            else
                print_error "File verification failed: $filename"
                error_count=$((error_count + 1))
            fi
        else
            error_count=$((error_count + 1))
        fi
        
        echo ""
    done < "$url_file"
    
    print_status "Batch download completed"
    print_info "Success: $success_count files"
    print_info "Errors: $error_count files"
    
    return 0
}

# Function to show usage
show_usage() {
    echo "GGUF Model Download Utility for Chat-O-Llama"
    echo ""
    echo "Usage: $0 [command] [options]"
    echo ""
    echo "Commands:"
    echo "  download <url> [filename]    - Download single GGUF file from HuggingFace"
    echo "  batch <file>                 - Download multiple files from URL list"
    echo "  info                         - Show model directory information"
    echo "  list                         - List downloaded models"
    echo "  help                         - Show this help message"
    echo ""
    echo "Options:"
    echo "  <url>                        - HuggingFace GGUF file URL"
    echo "  [filename]                   - Optional custom filename (defaults to URL filename)"
    echo "  <file>                       - Text file with URLs (one per line)"
    echo ""
    echo "URL Format:"
    echo "  https://huggingface.co/USER/REPO/resolve/main/FILE.gguf"
    echo ""
    echo "Batch File Format:"
    echo "  # Comments start with #"
    echo "  https://huggingface.co/user/repo/resolve/main/model1.gguf"
    echo "  https://huggingface.co/user/repo/resolve/main/model2.gguf|custom-name.gguf"
    echo ""
    echo "Examples:"
    echo "  # Download single file"
    echo "  $0 download https://huggingface.co/microsoft/DialoGPT-medium/resolve/main/model.gguf"
    echo ""
    echo "  # Download with custom filename"
    echo "  $0 download https://huggingface.co/user/repo/resolve/main/model.gguf my-model.gguf"
    echo ""
    echo "  # Batch download"
    echo "  $0 batch models.txt"
    echo ""
    echo "  # Show model directory info"
    echo "  $0 info"
    echo ""
    echo "Configuration:"
    echo "  Model directory: $(get_model_directory)"
    echo "  Config file: $CONFIG_FILE"
    echo "  Override with: CONFIG_FILE=/path/to/config.json $0 command"
}

# Function to list downloaded models
list_models() {
    local model_dir=$(get_model_directory)
    
    print_info "Models in $model_dir:"
    
    if [ ! -d "$model_dir" ]; then
        print_warning "Model directory does not exist"
        return 1
    fi
    
    local models=($(find "$model_dir" -name "*.gguf" -type f | sort))
    
    if [ ${#models[@]} -eq 0 ]; then
        print_info "No GGUF models found"
        return 0
    fi
    
    printf "%-40s %-15s %-20s\n" "Model Name" "Size" "Modified"
    printf "%-40s %-15s %-20s\n" "$(printf '%*s' 40 '' | tr ' ' '-')" "$(printf '%*s' 15 '' | tr ' ' '-')" "$(printf '%*s' 20 '' | tr ' ' '-')"
    
    for model in "${models[@]}"; do
        local basename_model=$(basename "$model")
        local size=$(stat -c%s "$model" 2>/dev/null || stat -f%z "$model" 2>/dev/null || echo "0")
        local formatted_size=$(numfmt --to=iec "$size")
        local modified=$(stat -c%y "$model" 2>/dev/null | cut -d' ' -f1 || stat -f%Sm -t%Y-%m-%d "$model" 2>/dev/null || echo "unknown")
        
        printf "%-40s %-15s %-20s\n" "$basename_model" "$formatted_size" "$modified"
    done
    
    echo ""
    print_info "Total models: ${#models[@]}"
}

# Main script logic
case "${1:-help}" in
    download)
        if [ -z "$2" ]; then
            print_error "URL required"
            echo ""
            show_usage
            exit 1
        fi
        
        url="$2"
        custom_filename="$3"
        
        # Validate URL
        if ! validate_huggingface_url "$url"; then
            exit 1
        fi
        
        # Get filename
        if [ -n "$custom_filename" ]; then
            if [[ ! "$custom_filename" =~ \.gguf$ ]]; then
                print_error "Custom filename must have .gguf extension"
                exit 1
            fi
            filename="$custom_filename"
        else
            filename=$(extract_filename "$url")
            if [ $? -ne 0 ]; then
                exit 1
            fi
        fi
        
        # Get model directory and create if needed
        model_dir=$(get_model_directory)
        mkdir -p "$model_dir"
        
        # Download file
        output_path="$model_dir/$filename"
        if download_file "$url" "$output_path"; then
            if verify_gguf_file "$output_path"; then
                print_status "Model downloaded successfully: $filename"
                print_info "Location: $output_path"
                print_info "Use with Chat-O-Llama by switching to llamacpp backend"
            else
                print_error "Download verification failed"
                exit 1
            fi
        else
            print_error "Download failed"
            exit 1
        fi
        ;;
    
    batch)
        if [ -z "$2" ]; then
            print_error "URL file required"
            echo ""
            show_usage
            exit 1
        fi
        
        download_batch "$2"
        ;;
    
    info)
        show_model_info
        ;;
    
    list)
        list_models
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