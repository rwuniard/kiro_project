#!/bin/bash

# Unix/Mac deployment script for Kiro Project local Docker deployment
# This script reads Unix-specific paths and generates the environment file

set -e  # Exit on any error

echo "============================================"
echo "  Kiro Project - Local Docker Deployment"
echo "  Platform: Unix/Mac"
echo "============================================"
echo

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to extract JSON values (simple extraction)
extract_json_value() {
    local file="$1"
    local key="$2"
    grep "\"$key\"" "$file" | head -1 | sed 's/.*": *"\([^"]*\)".*/\1/'
}

# Change to script directory for relative path resolution
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

echo "[1/5] Checking prerequisites..."

# Check if Python is available
if ! command_exists python3; then
    echo "ERROR: Python 3 is not installed or not in PATH"
    echo "Please install Python 3.8+ and try again"
    exit 1
fi

# Check if Docker is available
if ! command_exists docker; then
    echo "ERROR: Docker is not installed or not running"
    echo "Please install Docker and ensure it's running"
    exit 1
fi

# Check if docker-compose is available
if ! command_exists docker-compose; then
    echo "ERROR: docker-compose is not installed or not in PATH"
    echo "Please install docker-compose and try again"
    exit 1
fi

# Check if required files exist
if [ ! -f "scripts/generate_env.py" ]; then
    echo "ERROR: scripts/generate_env.py not found"
    exit 1
fi

if [ ! -f "config/unix_paths.json" ]; then
    echo "ERROR: config/unix_paths.json not found"
    exit 1
fi

if [ ! -f ".env.template" ]; then
    echo "ERROR: .env.template not found"
    exit 1
fi

echo "[2/5] Creating local directories..."

# Read paths from Unix configuration file
SOURCE_PATH=$(extract_json_value "config/unix_paths.json" "source_folder")
SAVED_PATH=$(extract_json_value "config/unix_paths.json" "saved_folder")
ERROR_PATH=$(extract_json_value "config/unix_paths.json" "error_folder")

# Expand tilde if present
SOURCE_PATH="${SOURCE_PATH/#\~/$HOME}"
SAVED_PATH="${SAVED_PATH/#\~/$HOME}"
ERROR_PATH="${ERROR_PATH/#\~/$HOME}"

# Create local directories if they don't exist
mkdir -p "$SOURCE_PATH"
mkdir -p "$SAVED_PATH"
mkdir -p "$ERROR_PATH"

# Create Docker data directories
mkdir -p "data/chroma_db"
mkdir -p "logs"

echo "  Created: $SOURCE_PATH"
echo "  Created: $SAVED_PATH"
echo "  Created: $ERROR_PATH"

echo "[3/5] Generating environment configuration..."

# Set default model vendor (can be overridden by command line argument)
MODEL_VENDOR="${1:-google}"

# Generate .env file using Python script
python3 scripts/generate_env.py \
    --environment development \
    --platform unix \
    --model-vendor "$MODEL_VENDOR"

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to generate environment configuration"
    exit 1
fi

echo "[4/5] Copying environment file..."

# Copy generated file to .env for docker-compose
if [ -f ".env.generated" ]; then
    cp ".env.generated" ".env"
    echo "  Environment file ready: .env"
else
    echo "ERROR: Failed to generate .env file"
    exit 1
fi

echo "[5/5] Starting Docker containers..."

# Build and start the containers
echo "  Building Docker image..."
docker-compose build

if [ $? -ne 0 ]; then
    echo "ERROR: Docker build failed"
    exit 1
fi

echo "  Starting containers..."
docker-compose up -d

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to start containers"
    exit 1
fi

echo
echo "============================================"
echo "  Deployment Successful!"
echo "============================================"
echo
echo "  Source folder:  $SOURCE_PATH"
echo "  Saved folder:   $SAVED_PATH"  
echo "  Error folder:   $ERROR_PATH"
echo "  Model vendor:   $MODEL_VENDOR"
echo
echo "  Container status:"
docker-compose ps

echo
echo "  To monitor logs: docker-compose logs -f"
echo "  To stop:         docker-compose down"
echo "  To restart:      docker-compose restart"
echo
echo "  Drop files into the source folder to start processing!"
echo