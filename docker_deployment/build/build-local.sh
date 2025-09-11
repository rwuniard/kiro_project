#!/bin/bash

# Local build script for Kiro Project
# Builds Docker image locally and pushes to registry as 'local-rag-file-processor'

set -e  # Exit on any error

echo "============================================"
echo "  Kiro Project - Local Build"
echo "  Building and pushing: local-rag-file-processor"
echo "============================================"
echo

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Change to script directory for relative path resolution
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
cd "$PROJECT_ROOT"

echo "[1/4] Checking prerequisites..."

# Check if Docker is available
if ! command_exists docker; then
    echo "ERROR: Docker is not installed or not running"
    echo "Please install Docker and ensure it's running"
    exit 1
fi

# Check if Dockerfile exists
if [ ! -f "docker_deployment/shared/Dockerfile" ]; then
    echo "ERROR: docker_deployment/shared/Dockerfile not found"
    exit 1
fi

echo "[2/4] Building Docker image..."

# Set default registry and image name
REGISTRY="${1:-ghcr.io/rwuniard}"  # Default to GitHub Container Registry (same as CI)
IMAGE_NAME="local-rag-file-processor"
FULL_IMAGE_NAME="$REGISTRY/$IMAGE_NAME:latest"

echo "  Registry: $REGISTRY"
echo "  Image name: $IMAGE_NAME"
echo "  Full image: $FULL_IMAGE_NAME"

# Build the image
echo "  Building image..."
docker build -f docker_deployment/shared/Dockerfile -t "$FULL_IMAGE_NAME" .

if [ $? -ne 0 ]; then
    echo "ERROR: Docker build failed"
    echo "Check the Dockerfile and project dependencies"
    exit 1
fi

echo "[3/4] Tagging image..."

# Also tag with local name for convenience
docker tag "$FULL_IMAGE_NAME" "$IMAGE_NAME:latest"

echo "  Tagged as: $IMAGE_NAME:latest"
echo "  Tagged as: $FULL_IMAGE_NAME"

echo "[4/4] Pushing to registry..."

# Push to registry
echo "  Pushing to $REGISTRY..."
docker push "$FULL_IMAGE_NAME"

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to push image to registry"
    echo "Make sure you are logged in to the registry:"
    echo "  docker login $REGISTRY"
    exit 1
fi

echo
echo "============================================"
echo "  Local Build Successful!"
echo "============================================"
echo
echo "  Built image: $FULL_IMAGE_NAME"
echo "  Local tag:   $IMAGE_NAME:latest"
echo
echo "  Image is ready for deployment using:"
echo "  ../deploy/deploy.sh $FULL_IMAGE_NAME [env-file]"
echo "  or"
echo "  ../deploy/deploy.sh $IMAGE_NAME:latest [env-file]"
echo
echo "  To view image: docker images $IMAGE_NAME"
echo