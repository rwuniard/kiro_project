#!/bin/bash

# Universal deployment script for Kiro Project
# Deploys any Docker image with user-provided environment configuration
# No Python/uv dependencies - only Docker required

set -e  # Exit on any error

echo "============================================"
echo "  Kiro Project - Universal Deployment"
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

# Check command line arguments
if [ $# -lt 2 ]; then
    echo "Usage: $0 <image-name> <env-file-path>"
    echo
    echo "Examples:"
    echo "  $0 local-rag-file-processor:latest .env.development"
    echo "  $0 rag-file-processor:latest .env.production"
    echo "  $0 ghcr.io/rwuniard/rag-file-processor:v1.0.0 .env.custom"
    echo
    exit 1
fi

IMAGE_NAME="$1"
ENV_FILE="$2"

echo "  Image: $IMAGE_NAME"
echo "  Environment file: $ENV_FILE"
echo

echo "[1/6] Checking prerequisites..."

# Check if Docker is available
if ! command_exists docker; then
    echo "ERROR: Docker is not installed or not running"
    echo "Please install Docker and ensure it's running"
    exit 1
fi

# Check if docker compose is available
if ! docker compose version >/dev/null 2>&1; then
    echo "ERROR: docker compose is not available"
    echo "Please install Docker with Compose V2 support and try again"
    exit 1
fi

# Check if environment file exists
if [ ! -f "$ENV_FILE" ]; then
    echo "ERROR: Environment file '$ENV_FILE' not found"
    echo "Please provide a valid .env file path"
    exit 1
fi

echo "[2/6] Loading environment configuration..."

# Create a temporary .env file for docker compose
cp "$ENV_FILE" .env.deploy

# Read folder paths from environment file or use defaults
SOURCE_FOLDER=$(grep "^SOURCE_FOLDER=" "$ENV_FILE" | cut -d= -f2- | tr -d '"' || echo "")
SAVED_FOLDER=$(grep "^SAVED_FOLDER=" "$ENV_FILE" | cut -d= -f2- | tr -d '"' || echo "")
ERROR_FOLDER=$(grep "^ERROR_FOLDER=" "$ENV_FILE" | cut -d= -f2- | tr -d '"' || echo "")

# If not found in env file, use sensible defaults
if [ -z "$SOURCE_FOLDER" ] || [ -z "$SAVED_FOLDER" ] || [ -z "$ERROR_FOLDER" ]; then
    echo "  Using default paths (~/tmp/rag_store/...)..."
    SOURCE_FOLDER="${SOURCE_FOLDER:-~/tmp/rag_store/source}"
    SAVED_FOLDER="${SAVED_FOLDER:-~/tmp/rag_store/saved}"
    ERROR_FOLDER="${ERROR_FOLDER:-~/tmp/rag_store/error}"
fi

# Expand tilde if present
SOURCE_FOLDER="${SOURCE_FOLDER/#\~/$HOME}"
SAVED_FOLDER="${SAVED_FOLDER/#\~/$HOME}"
ERROR_FOLDER="${ERROR_FOLDER/#\~/$HOME}"

# Use fallback defaults if still empty
SOURCE_FOLDER="${SOURCE_FOLDER:-$HOME/tmp/rag_store/source}"
SAVED_FOLDER="${SAVED_FOLDER:-$HOME/tmp/rag_store/saved}"
ERROR_FOLDER="${ERROR_FOLDER:-$HOME/tmp/rag_store/error}"

echo "  Source folder: $SOURCE_FOLDER"
echo "  Saved folder: $SAVED_FOLDER"
echo "  Error folder: $ERROR_FOLDER"

# Add folder paths to deployment env file
echo "" >> .env.deploy
echo "# Host folder paths for volume mounting" >> .env.deploy
echo "SOURCE_FOLDER=$SOURCE_FOLDER" >> .env.deploy
echo "SAVED_FOLDER=$SAVED_FOLDER" >> .env.deploy
echo "ERROR_FOLDER=$ERROR_FOLDER" >> .env.deploy

# Add Docker image configuration
echo "" >> .env.deploy
echo "# Docker image configuration" >> .env.deploy
echo "DOCKER_IMAGE=$IMAGE_NAME" >> .env.deploy

echo "[3/6] Creating local directories..."

# Create local directories if they don't exist
mkdir -p "$SOURCE_FOLDER"
mkdir -p "$SAVED_FOLDER"
mkdir -p "$ERROR_FOLDER"

# Create Docker data directories (relative to deploy directory)
mkdir -p "../data/chroma_db"
mkdir -p "../logs"

echo "  Created: $SOURCE_FOLDER"
echo "  Created: $SAVED_FOLDER"
echo "  Created: $ERROR_FOLDER"

echo "[4/6] Setting up temporary directory permissions..."

# Create temporary directory for document processing
mkdir -p /tmp/file-processor-unstructured

# Set proper permissions (readable/writable by all users)
chmod 777 /tmp/file-processor-unstructured

echo "  Created: /tmp/file-processor-unstructured"
echo "  Permissions set: $(ls -ld /tmp/file-processor-unstructured)"

echo "[5/6] Pulling Docker image..."

# Pull the image
echo "  Pulling image: $IMAGE_NAME"
docker pull "$IMAGE_NAME"

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to pull image '$IMAGE_NAME'"
    echo "Make sure the image exists and you have access to it"
    exit 1
fi

echo "[6/6] Starting containers..."

# Create Docker network if it doesn't exist
docker network create mcp-network 2>/dev/null || true

# Use the deployment env file
export COMPOSE_FILE=docker-compose.yml
echo "  Starting containers with image: $IMAGE_NAME"
docker compose --env-file .env.deploy up -d

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to start containers"
    exit 1
fi

# Wait a moment for containers to initialize
sleep 5

echo
echo "============================================"
echo "  Deployment Successful!"
echo "============================================"
echo
echo "  Docker image:   $IMAGE_NAME"
echo "  Environment:    $ENV_FILE"
echo "  Source folder:  $SOURCE_FOLDER"
echo "  Saved folder:   $SAVED_FOLDER"  
echo "  Error folder:   $ERROR_FOLDER"
echo "  Temp directory: /tmp/file-processor-unstructured"
echo
echo "  Container status:"
docker compose --env-file .env.deploy ps

echo
echo "  To monitor logs: docker compose --env-file .env.deploy logs -f"
echo "  To stop:         docker compose --env-file .env.deploy down"
echo "  To restart:      docker compose --env-file .env.deploy restart"
echo
echo "  Drop files into the source folder to start processing!"
echo

# Clean up temporary deployment env file
rm -f .env.deploy