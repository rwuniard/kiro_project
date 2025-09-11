#!/bin/bash

# CI build script for Kiro Project
# Builds Docker image for CI/production and pushes to registry as 'rag-file-processor'

set -e  # Exit on any error

echo "============================================"
echo "  Kiro Project - CI Build"
echo "  Building and pushing: rag-file-processor"
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
REGISTRY="${1:-ghcr.io/rwuniard}"  # Default to GitHub Container Registry
REPO_NAME="kiro_project"  # GitHub repository name

# Auto-determine version from pyproject.toml + git metadata
BASE_VERSION=$(grep '^version = ' "$PROJECT_ROOT/pyproject.toml" | sed 's/version = "\(.*\)"/\1/')
GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
TAG="rag-file-processor-$BASE_VERSION-$GIT_SHA"
FULL_IMAGE_NAME="$REGISTRY/$REPO_NAME:$TAG"

echo "  Registry: $REGISTRY"
echo "  Repository: $REPO_NAME"
echo "  Base version: $BASE_VERSION (from pyproject.toml)"
echo "  Git SHA: $GIT_SHA"
echo "  Tag: $TAG"
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

# Also tag with convenience tags
docker tag "$FULL_IMAGE_NAME" "$REPO_NAME:$TAG"
docker tag "$FULL_IMAGE_NAME" "$REPO_NAME:rag-file-processor-latest"
docker tag "$FULL_IMAGE_NAME" "$REGISTRY/$REPO_NAME:rag-file-processor-latest"

echo "  Tagged as: $REPO_NAME:$TAG"
echo "  Tagged as: $REPO_NAME:rag-file-processor-latest"
echo "  Tagged as: $REGISTRY/$REPO_NAME:rag-file-processor-latest"
echo "  Tagged as: $FULL_IMAGE_NAME"

echo "[4/4] Pushing to registry..."

# Push to registry
echo "  Pushing to $REGISTRY..."
docker push "$FULL_IMAGE_NAME"
docker push "$REGISTRY/$REPO_NAME:rag-file-processor-latest"

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to push image to registry"
    echo "Make sure you are logged in to the registry:"
    if [[ "$REGISTRY" == *"ghcr.io"* ]]; then
        echo "  docker login ghcr.io"
    else
        echo "  docker login $REGISTRY"
    fi
    exit 1
fi

echo
echo "============================================"
echo "  CI Build Successful!"
echo "============================================"
echo
echo "  Built image: $FULL_IMAGE_NAME"
echo "  Also tagged: $REGISTRY/$REPO_NAME:rag-file-processor-latest"
echo "  Local tag:   $REPO_NAME:$TAG"
echo "  Base version: $BASE_VERSION (from pyproject.toml)"
echo "  Git commit:   $GIT_SHA"
echo
echo "  Image is ready for deployment using:"
echo "  ../deploy/deploy.sh $FULL_IMAGE_NAME [env-file]"
echo "  or"
echo "  ../deploy/deploy.sh $REGISTRY/$REPO_NAME:rag-file-processor-latest [env-file]"
echo
echo "  To view image: docker images $REPO_NAME"
echo