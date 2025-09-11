# Docker Deployment for Kiro Project

This directory contains a **simplified Docker deployment system** that cleanly separates build and deployment phases.

## 🚀 New Simplified Workflow

### Build Phase (Separate)
- **Local Build**: `./build/build-local.sh` → Creates `local-rag-file-processor` image
- **CI Build**: `./build/build-ci.sh` → Creates `rag-file-processor` image

### Deploy Phase (Universal)  
- **Single Script**: `./deploy/deploy.sh [image-name] [env-file]`
- **No Dependencies**: Only Docker required (NO Python/uv)
- **User Controls**: Provide your own `.env` file

## 📁 Directory Structure

```
docker_deployment/
├── build/                       # Build Scripts (Separate Phase)
│   ├── build-local.sh              # Local build + push to registry
│   ├── build-local.bat             # Windows local build
│   ├── build-ci.sh                 # CI build + push to registry  
│   └── build-ci.bat                # Windows CI build
├── deploy/                      # Deployment Scripts (Universal)
│   ├── deploy.sh                    # Universal deployment (Unix/Mac)
│   ├── deploy.bat                   # Universal deployment (Windows)
│   └── docker-compose.yml           # Simplified compose file
├── shared/                      # Shared Resources
│   └── Dockerfile                   # Single Dockerfile for all builds
├── config/                      # Configuration Files
│   ├── unix_paths.json              # Default folder paths (Unix/Mac)
│   └── windows_paths.json           # Default folder paths (Windows)  
└── data/                        # Persistent Data
    ├── chroma_db/                   # ChromaDB storage
    └── logs/                        # Application logs
```

## 🚀 Quick Start Guide

### Step 1: Build Phase

**Local Build** (for development):
```bash
# Unix/Mac
./docker_deployment/build/build-local.sh [registry]

# Windows  
docker_deployment\build\build-local.bat [registry]

# Examples:
./build/build-local.sh                    # Uses ghcr.io/rwuniard (GitHub Container Registry)
./build/build-local.sh docker.io/myorg   # Uses Docker Hub
```

**CI Build** (for production):
```bash
# Unix/Mac
./docker_deployment/build/build-ci.sh [registry]

# Windows
docker_deployment\build\build-ci.bat [registry]

# Examples:
./build/build-ci.sh                     # Uses ghcr.io/rwuniard
./build/build-ci.sh docker.io/myorg     # Custom registry

# Version is automatically determined from pyproject.toml + git SHA
# Example: 0.1.1-a1b2c3d4 (base version from pyproject.toml + git commit)
```

### Step 2: Deployment Phase

**Create Your Environment File** (e.g., `.env.production`):
```env
# Required - Basic file processing
SOURCE_FOLDER=/path/to/source
SAVED_FOLDER=/path/to/saved  
ERROR_FOLDER=/path/to/error

# Required - Document processing with RAG
ENABLE_DOCUMENT_PROCESSING=true
DOCUMENT_PROCESSOR_TYPE=rag_store
MODEL_VENDOR=google
GOOGLE_API_KEY=your_google_key_here

# Optional - File monitoring (defaults work for Docker)
FILE_MONITORING_MODE=auto
POLLING_INTERVAL=2.0
DOCKER_VOLUME_MODE=true

# Optional - ChromaDB configuration  
CHROMA_DB_PATH=./data/chroma_db
CHROMA_CLIENT_MODE=client_server
```

**Deploy Any Image**:
```bash
# Unix/Mac
./docker_deployment/deploy/deploy.sh [image-name] [env-file]

# Windows
docker_deployment\deploy\deploy.bat [image-name] [env-file]

# Examples:
./deploy/deploy.sh local-rag-file-processor:latest .env.development
./deploy/deploy.sh rag-file-processor:latest .env.production
./deploy/deploy.sh ghcr.io/myorg/custom:v1.0.0 .env.custom
```

## 🔧 Complete Workflow Examples

### Development Workflow
```bash
# 1. Build locally
./docker_deployment/build/build-local.sh

# 2. Deploy locally built image
./docker_deployment/deploy/deploy.sh local-rag-file-processor:latest .env.development

# 3. Monitor
cd docker_deployment/deploy
docker-compose logs -f
```

### Production Workflow  
```bash
# 1. Build for production (typically in CI)
./docker_deployment/build/build-ci.sh ghcr.io/myorg

# 2. Deploy production image (version automatically determined)
./docker_deployment/deploy/deploy.sh ghcr.io/myorg/rag-file-processor:0.1.1-a1b2c3d4 .env.production
# Or use latest tag
./docker_deployment/deploy/deploy.sh ghcr.io/myorg/rag-file-processor:latest .env.production

# 3. Monitor
cd docker_deployment/deploy
docker-compose logs -f
```

## 🔢 Automatic Versioning

**CI builds automatically determine version numbers** - no manual specification required!

### Version Format
- **Base Version**: Read from `pyproject.toml` (currently: `0.1.1`)
- **Git Commit**: Short SHA of current commit (e.g., `a1b2c3d4`)
- **Final Version**: `{base}-{sha}` (e.g., `0.1.1-a1b2c3d4`)

### Example Build Output
```bash
./build/build-ci.sh
# Output:
#   Base version: 0.1.1 (from pyproject.toml)
#   Git SHA: a1b2c3d4  
#   Full version: 0.1.1-a1b2c3d4
#   Built image: ghcr.io/rwuniard/rag-file-processor:0.1.1-a1b2c3d4
```

### Benefits
✅ **No manual versioning errors**  
✅ **Automatic traceability** to git commits  
✅ **Consistent with project version** in pyproject.toml  
✅ **CI/CD friendly** - works in any environment  

## 🛠️ Configuration

### Environment File Structure

Your `.env` file should contain all the configuration needed:

```env
# === Required Settings ===
SOURCE_FOLDER=~/tmp/rag_store/source
SAVED_FOLDER=~/tmp/rag_store/saved
ERROR_FOLDER=~/tmp/rag_store/error
ENABLE_DOCUMENT_PROCESSING=true
DOCUMENT_PROCESSOR_TYPE=rag_store
MODEL_VENDOR=google                     # or openai
GOOGLE_API_KEY=your_key_here           # if using Google
OPENAI_API_KEY=your_key_here           # if using OpenAI

# === Optional Settings ===
LOG_LEVEL=INFO
FILE_MONITORING_MODE=auto
POLLING_INTERVAL=2.0
DOCKER_VOLUME_MODE=true
CHROMA_DB_PATH=./data/chroma_db
CHROMA_CLIENT_MODE=client_server
CHROMA_COLLECTION_NAME=rag-kb
```

### Default Folder Paths

If not specified in your `.env` file, defaults are read from:

**Unix/Mac**: `config/unix_paths.json`
```json
{
  "source_folder": "~/tmp/rag_store/source",
  "saved_folder": "~/tmp/rag_store/saved", 
  "error_folder": "~/tmp/rag_store/error"
}
```

**Windows**: `config/windows_paths.json`
```json
{
  "source_folder": "C:\\temp\\rag_store\\source",
  "saved_folder": "C:\\temp\\rag_store\\saved",
  "error_folder": "C:\\temp\\rag_store\\error"
}
```

## 🔧 Container Management

### Basic Operations
```bash
# Navigate to deploy directory first
cd docker_deployment/deploy

# Container operations
docker-compose ps                          # View status
docker-compose logs -f                     # Monitor logs  
docker-compose restart                     # Restart services
docker-compose down                        # Stop containers
docker-compose exec rag-file-processor bash # Access container

# Resource monitoring
docker stats rag-file-processor
```

### File Processing Test
```bash
# 1. Drop test files into source folder
cp test.pdf ~/tmp/rag_store/source/
cp document.docx ~/tmp/rag_store/source/

# 2. Monitor processing
docker-compose logs -f

# 3. Check results
ls -la ~/tmp/rag_store/saved/    # Successfully processed
ls -la ~/tmp/rag_store/error/    # Failed files + .log files
```

## 🚀 Key Benefits

✅ **Clean Separation**: Build and deployment are completely separate phases  
✅ **No Python Dependencies**: Deployment only needs Docker + shell scripts  
✅ **Universal Deployment**: Single script works for any image source  
✅ **User Control**: Complete control over environment via `.env` files  
✅ **Registry Flexible**: Works with Docker Hub, GHCR, or any registry  
✅ **Cross-Platform**: Full Windows and Unix/Mac support

## 🔧 Troubleshooting

### Build Issues
```bash
# Check Docker
docker --version

# Local build troubleshooting
./build/build-local.sh docker.io/test

# CI build troubleshooting  
./build/build-ci.sh docker.io/test
# Version automatically determined from pyproject.toml + git
```

### Deployment Issues
```bash
# Check environment file
cat .env.production

# Test deployment
./deploy/deploy.sh test-image:latest .env.production

# Check logs
cd deploy && docker-compose logs -f
```

### Registry Issues
```bash
# Login to registry
docker login docker.io          # Docker Hub
docker login ghcr.io           # GitHub Container Registry

# Test image pull
docker pull your-image:latest
```

## 📚 Migration from Old System

| Old Approach | New Approach |
|-------------|--------------|
| Complex CI/local paths | Simple build + deploy separation |
| Python/uv dependencies | Docker-only deployment |
| Generated .env files | User-provided .env files |
| Mixed build/deploy | Clean phase separation |

See `REQUIREMENTS.md` for detailed implementation requirements.