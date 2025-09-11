# Docker Deployment Requirements

## Overview
Simplify the current Docker deployment system into a clean separation of build and deployment phases with minimal dependencies.

## Current Problems
- Complex deployment scripts with Python/uv dependencies
- Mixed build and deployment logic
- Inflexible environment configuration
- Separate CI and local deployment paths

## New Requirements

### Build Phase (Separate from Deployment)

#### Local Build
- **Script**: `build/build-local.sh` (Unix/Mac) and `build/build-local.bat` (Windows)
- **Action**: Build Docker image locally
- **Output**: Push image to registry as `local-rag-file-processor`
- **Dependencies**: Docker only

#### CI Build
- **Script**: `build/build-ci.sh` (Unix/Mac) and `build/build-ci.bat` (Windows) 
- **Action**: Build Docker image in CI environment
- **Output**: Push image to registry as `rag-file-processor`
- **Dependencies**: Docker only

### Deployment Phase (Unified)

#### Universal Deployment
- **Script**: `deploy/deploy.sh` (Unix/Mac) and `deploy/deploy.bat` (Windows)
- **Parameters**: 
  1. Image name (e.g., `local-rag-file-processor` or `rag-file-processor`)
  2. Environment file path (e.g., `.env.development`, `.env.production`)
- **Action**: Pull specified image and deploy with provided environment configuration
- **Dependencies**: Docker only (NO Python, NO uv required)

## Usage Examples

### Build Examples
```bash
# Local build and push
./build/build-local.sh

# CI build and push  
./build/build-ci.sh
```

### Deployment Examples
```bash
# Deploy local build with development config
./deploy/deploy.sh local-rag-file-processor .env.development

# Deploy CI build with production config
./deploy/deploy.sh rag-file-processor .env.production

# Deploy any custom image
./deploy/deploy.sh custom-registry.com/my-app:v1.0 .env.custom
```

## Key Simplifications

1. **No Python Dependencies for Deployment**: Deployment scripts only require Docker and shell/batch scripts
2. **Clear Separation**: Build and deployment are completely separate phases
3. **User-Provided Environment**: Users provide complete `.env` files instead of generated configurations
4. **Universal Deployment**: Single deployment script works for any image source
5. **Minimal Dependencies**: Only Docker required for both build and deployment

## Directory Structure (New)
```
docker_deployment/
├── build/
│   ├── build-local.sh              # Local build script (Unix/Mac)
│   ├── build-local.bat             # Local build script (Windows)
│   ├── build-ci.sh                 # CI build script (Unix/Mac)
│   └── build-ci.bat                # CI build script (Windows)
├── deploy/
│   ├── deploy.sh                   # Universal deployment (Unix/Mac)
│   ├── deploy.bat                  # Universal deployment (Windows)
│   └── docker-compose.yml          # Simplified compose file
├── shared/
│   └── Dockerfile                  # Shared Dockerfile
└── config/
    ├── unix_paths.json            # Default folder paths (Unix/Mac)
    └── windows_paths.json         # Default folder paths (Windows)
```

## Implementation Tasks

1. **Directory Restructure**: Create new build/ and deploy/ directories
2. **Build Scripts**: Create 4 build scripts (local + CI, Unix + Windows)
3. **Deployment Scripts**: Create 2 deployment scripts (Unix + Windows) + compose file
4. **Configuration**: Move and simplify config files
5. **Documentation**: Update README and usage guides
6. **Testing**: Validate both build and deployment workflows

## Success Criteria

- ✅ Build phase creates and pushes images with correct names
- ✅ Deployment phase works with any image name and user-provided .env file
- ✅ No Python/uv dependencies required for deployment
- ✅ Scripts work on both Unix/Mac and Windows
- ✅ Backwards compatibility maintained where possible
- ✅ Clear separation between build and deployment phases