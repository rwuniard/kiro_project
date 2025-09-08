#!/bin/bash

# Unix/Mac deployment script for Kiro Project GHCR Docker deployment
# This script deploys pre-built Docker images from GitHub Container Registry

set -e  # Exit on any error

echo "============================================"
echo "  Kiro Project - GHCR Docker Deployment"
echo "  Platform: Unix/Mac"
echo "  Source: GitHub Container Registry"
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

# Check if required files exist
if [ ! -f "config/unix_paths.json" ]; then
    echo "ERROR: config/unix_paths.json not found"
    echo "Please ensure the configuration file exists"
    exit 1
fi

# Set default values (can be overridden by command line arguments)
IMAGE_TAG="${1:-latest}"
MODEL_VENDOR="${2:-google}"
GHCR_REPO="${3:-ghcr.io/rwuniard/rag-file-processor}"

echo "  Docker image: $GHCR_REPO:$IMAGE_TAG"
echo "  Model vendor: $MODEL_VENDOR"
echo

echo "[2/6] Creating local directories..."

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

echo "[3/6] Setting up temporary directory permissions..."

# Create temporary directory for document processing
mkdir -p /tmp/file-processor-unstructured

# Set proper permissions (readable/writable by all users)
chmod 777 /tmp/file-processor-unstructured

echo "  Created: /tmp/file-processor-unstructured"
echo "  Permissions set: $(ls -ld /tmp/file-processor-unstructured)"

echo "[4/6] Pulling Docker image from GHCR..."

# Pull the latest image from GHCR
echo "  Pulling $GHCR_REPO:$IMAGE_TAG..."
docker pull "$GHCR_REPO:$IMAGE_TAG"

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to pull Docker image from GHCR"
    echo "Please ensure:"
    echo "  1. The image exists in the registry"
    echo "  2. You have access to the repository"
    echo "  3. You are logged in to GHCR (docker login ghcr.io)"
    exit 1
fi

echo "[5/6] Generating environment configuration..."

# Check if .env.local exists for API keys
if [ ! -f "../../.env.local" ]; then
    echo "WARNING: .env.local not found in project root"
    echo "Please create .env.local with your API keys:"
    echo "  OPENAI_API_KEY=your_openai_key_here"
    echo "  GOOGLE_API_KEY=your_google_key_here"
    echo
fi

# Generate environment variables for docker-compose
cat > .env <<EOF
# Generated environment file for GHCR deployment
# Generated on: $(date)

# Docker image configuration
DOCKER_IMAGE=$GHCR_REPO:$IMAGE_TAG

# Local folder mappings
SOURCE_FOLDER=$SOURCE_PATH
SAVED_FOLDER=$SAVED_PATH
ERROR_FOLDER=$ERROR_PATH

# Document processing configuration
ENABLE_DOCUMENT_PROCESSING=true
DOCUMENT_PROCESSOR_TYPE=rag_store
MODEL_VENDOR=$MODEL_VENDOR

# ChromaDB configuration
CHROMA_CLIENT_MODE=embedded
CHROMA_DB_PATH=./data/chroma_db
CHROMA_COLLECTION_NAME=rag-kb

# File monitoring configuration (Docker-optimized)
FILE_MONITORING_MODE=auto
POLLING_INTERVAL=2.0
DOCKER_VOLUME_MODE=true

# Logging configuration
LOG_LEVEL=INFO
EOF

# Source API keys from .env.local if it exists
if [ -f "../../.env.local" ]; then
    echo "  Loading API keys from .env.local..."
    source "../../.env.local"
    
    # Append API keys to .env file
    if [ ! -z "$OPENAI_API_KEY" ]; then
        echo "OPENAI_API_KEY=$OPENAI_API_KEY" >> .env
    fi
    
    if [ ! -z "$GOOGLE_API_KEY" ]; then
        echo "GOOGLE_API_KEY=$GOOGLE_API_KEY" >> .env
    fi
fi

echo "  Environment file ready: .env"

echo "[6/6] Starting Docker containers..."

# Start the containers using the pulled image
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
echo "  GHCR Deployment Successful!"
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
echo
echo "  Drop files into the source folder to start processing!"
echo

# Display current image info
echo "  Current image info:"
docker images "$GHCR_REPO" --format "table {{.Repository}}\t{{.Tag}}\t{{.CreatedAt}}\t{{.Size}}"
echo