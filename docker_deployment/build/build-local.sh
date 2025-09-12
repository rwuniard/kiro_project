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
REGISTRY="${1:-ghcr.io/rwuniard/kiro_project}"  # Default to GitHub Container Registry with repo path
IMAGE_NAME="local-rag-file-processor"  # Local build package name
TAG="latest"  # Local build tag
FULL_IMAGE_NAME="$REGISTRY/$IMAGE_NAME:$TAG"

# Generate version tag with short SHA (consistent with CI format)
BASE_VERSION=$(python3 -c "
import tomllib
with open('pyproject.toml', 'rb') as f:
    data = tomllib.load(f)
    print(data['project']['version'])
" 2>/dev/null || echo "0.1.1")
SHORT_SHA=$(git rev-parse --short=7 HEAD 2>/dev/null || echo "local")
VERSION_TAG="${BASE_VERSION}.${SHORT_SHA}"
VERSIONED_IMAGE_NAME="$REGISTRY/$IMAGE_NAME:$VERSION_TAG"

echo "  Registry: $REGISTRY"
echo "  Repository: $IMAGE_NAME"
echo "  Tag: $TAG"
echo "  Full image: $FULL_IMAGE_NAME"

# Build the image
echo "  Building image..."
docker build -f docker_deployment/shared/Dockerfile -t "$FULL_IMAGE_NAME" -t "$VERSIONED_IMAGE_NAME" .

if [ $? -ne 0 ]; then
    echo "ERROR: Docker build failed"
    echo "Check the Dockerfile and project dependencies"
    exit 1
fi

echo "[3/4] Tagging image..."

# Also tag with local name for convenience
docker tag "$FULL_IMAGE_NAME" "$IMAGE_NAME:$TAG"
docker tag "$VERSIONED_IMAGE_NAME" "$IMAGE_NAME:$VERSION_TAG"

echo "  Tagged as: $IMAGE_NAME:$TAG"
echo "  Tagged as: $IMAGE_NAME:$VERSION_TAG"
echo "  Tagged as: $FULL_IMAGE_NAME"
echo "  Tagged as: $VERSIONED_IMAGE_NAME"

echo "[4/4] Pushing to registry..."

# Push both tags to registry
echo "  Pushing latest tag to $REGISTRY..."
docker push "$FULL_IMAGE_NAME"

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to push latest tag to registry"
    echo "Make sure you are logged in to the registry:"
    echo "  docker login $REGISTRY"
    exit 1
fi

echo "  Pushing version tag to $REGISTRY..."
docker push "$VERSIONED_IMAGE_NAME"

if [ $? -ne 0 ]; then
    echo "WARNING: Failed to push version tag to registry"
    echo "Latest tag was pushed successfully"
fi

echo
echo "============================================"
echo "  Local Build Successful!"
echo "============================================"
echo
echo "  Built images:"
echo "    Latest: $FULL_IMAGE_NAME"
echo "    Version: $VERSIONED_IMAGE_NAME"
echo "  Local tags:"
echo "    $IMAGE_NAME:$TAG"
echo "    $IMAGE_NAME:$VERSION_TAG"
echo
echo "  Image is ready for deployment using:"
echo "  ../deploy/deploy.sh $FULL_IMAGE_NAME [env-file]"
echo "  ../deploy/deploy.sh $VERSIONED_IMAGE_NAME [env-file]"
echo "  or with local tags:"
echo "  ../deploy/deploy.sh $IMAGE_NAME:$TAG [env-file]"
echo "  ../deploy/deploy.sh $IMAGE_NAME:$VERSION_TAG [env-file]"
echo
echo "  To view images: docker images $IMAGE_NAME"
echo