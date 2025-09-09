#!/bin/bash

# Unix/Mac deployment script for CI deployment using pre-built GHCR images
# This script pulls pre-built images from GitHub Container Registry and deploys locally

set -e  # Exit on any error

echo "============================================"
echo "  Kiro Project - CI Deployment (GHCR Pull)"
echo "  Platform: Unix/Mac"
echo "  Image: ghcr.io/rwuniard/rag-file-processor:latest"
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

echo "[1/6] Checking prerequisites..."

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

# Check if uv is available for environment generation
if ! command_exists uv; then
    echo "ERROR: uv is not installed or not in PATH"
    echo "Please install uv and try again"
    exit 1
fi

# Check if required shared files exist
if [ ! -f "../shared/scripts/generate_env.py" ]; then
    echo "ERROR: ../shared/scripts/generate_env.py not found"
    exit 1
fi

if [ ! -f "../shared/config/unix_paths.json" ]; then
    echo "ERROR: ../shared/config/unix_paths.json not found"
    exit 1
fi

if [ ! -f "../shared/.env.template" ]; then
    echo "ERROR: ../shared/.env.template not found"
    exit 1
fi

echo "[2/6] Creating local directories..."

# Read paths from Unix configuration file (shared location)
SOURCE_PATH=$(extract_json_value "../shared/config/unix_paths.json" "source_folder")
SAVED_PATH=$(extract_json_value "../shared/config/unix_paths.json" "saved_folder")
ERROR_PATH=$(extract_json_value "../shared/config/unix_paths.json" "error_folder")

# Expand tilde if present
SOURCE_PATH="${SOURCE_PATH/#\~/$HOME}"
SAVED_PATH="${SAVED_PATH/#\~/$HOME}"
ERROR_PATH="${ERROR_PATH/#\~/$HOME}"

# Create local directories if they don't exist
mkdir -p "$SOURCE_PATH"
mkdir -p "$SAVED_PATH"
mkdir -p "$ERROR_PATH"

# Create Docker data directories (relative to CI directory)
mkdir -p "../data/chroma_db"
mkdir -p "../logs"

echo "  Created: $SOURCE_PATH"
echo "  Created: $SAVED_PATH"
echo "  Created: $ERROR_PATH"

echo "[3/6] Setting up temporary directory permissions..."

# Create temporary directory for document processing
mkdir -p /tmp/file-processor-unstructured

# Set proper permissions (readable/writable by all users)
chmod 777 /tmp/file-processor-unstructured

echo "  Created: /tmp/file-processor-unstructured"
echo "  Permissions set: $(ls -ld /tmp/file-processor-unstructured)"

echo "[4/6] Generating environment configuration..."

# Set default values (can be overridden by command line arguments)
IMAGE_TAG="${1:-latest}"
MODEL_VENDOR="${2:-google}"
GHCR_REPO="${3:-ghcr.io/rwuniard/rag-file-processor}"

echo "  Docker image: $GHCR_REPO:$IMAGE_TAG"
echo "  Model vendor: $MODEL_VENDOR"

# Generate .env file using shared Python script
cd "../shared/scripts"
uv run python generate_env.py \
    --environment production \
    --platform unix \
    --model-vendor "$MODEL_VENDOR"

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to generate environment configuration"
    exit 1
fi

# Return to CI directory
cd "$SCRIPT_DIR"

echo "[5/6] Copying environment file and adding Docker image config..."

# Copy generated file to .env for docker-compose
if [ -f "../.env.generated" ]; then
    cp "../.env.generated" ".env"
    
    # Add Docker image configuration for CI deployment
    echo "" >> .env
    echo "# Docker image configuration for CI deployment" >> .env
    echo "DOCKER_IMAGE=$GHCR_REPO:$IMAGE_TAG" >> .env
    
    echo "  Environment file ready: .env"
else
    echo "ERROR: Failed to generate .env file"
    exit 1
fi

echo "[6/6] Pulling image and starting containers..."

# Create Docker network if it doesn't exist
docker network create mcp-network 2>/dev/null || true

# Pull the latest image from GHCR
echo "  Pulling image from GHCR..."
docker pull "$GHCR_REPO:$IMAGE_TAG"

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to pull image from GHCR"
    echo "Make sure you have access to the repository and are logged in:"
    echo "  docker login ghcr.io"
    exit 1
fi

echo "  Starting containers..."
docker-compose up -d

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to start containers"
    exit 1
fi

# Wait a moment for containers to initialize
sleep 5

echo
echo "============================================"
echo "  CI Deployment Successful!"
echo "============================================"
echo
echo "  Docker image:   $GHCR_REPO:$IMAGE_TAG"
echo "  Source folder:  $SOURCE_PATH"
echo "  Saved folder:   $SAVED_PATH"  
echo "  Error folder:   $ERROR_PATH"
echo "  Temp directory: /tmp/file-processor-unstructured"
echo "  Model vendor:   $MODEL_VENDOR"
echo
echo "  Container status:"
docker-compose ps

echo
echo "  To monitor logs: docker-compose logs -f"
echo "  To stop:         docker-compose down"
echo "  To restart:      docker-compose restart"
echo "  To update:       docker-compose pull && docker-compose up -d"
echo
echo "  Drop files into the source folder to start processing!"
echo

# Display current image info
echo "  Current image info:"
docker images "$GHCR_REPO" --format "table {{.Repository}}\t{{.Tag}}\t{{.CreatedAt}}\t{{.Size}}"
echo