#!/bin/bash

# Fix permissions script for Docker container
# This script ensures proper permissions for the temporary directory

echo "Setting up temporary directory for document processing..."

# Create temporary directory on host if it doesn't exist
mkdir -p /tmp/file-processor-unstructured

# Set proper permissions (readable/writable by all users)
chmod 777 /tmp/file-processor-unstructured

echo "Temporary directory created: /tmp/file-processor-unstructured"
echo "Permissions set: $(ls -ld /tmp/file-processor-unstructured)"

echo "You can now rebuild and run your Docker container:"
echo "docker-compose down"
echo "docker-compose build --no-cache"
echo "docker-compose up"
