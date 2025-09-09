# Docker Deployment for Kiro Project

This directory contains **two distinct Docker deployment paths** for the Kiro Project, each optimized for different use cases:

## 🚀 Deployment Paths

### CI Deployment (`ci/`)
**Pull pre-built images from GitHub Container Registry**
- **Quick Start**: Deploy in ~2 minutes
- **Use Cases**: Testing, demos, production-like environments
- **Requirements**: Internet connection, Docker login to GHCR

### Local Development (`local/`)
**Build images locally from source**
- **Full Control**: Build and modify locally
- **Use Cases**: Development, debugging, offline work
- **Requirements**: Full build environment, longer initial setup

## 📁 New Directory Structure

```
docker_deployment/
├── ci/                          # CI Deployment (pre-built images)
│   ├── deploy-from-ghcr.sh          # Unix/Mac CI deployment
│   ├── deploy-from-ghcr.bat         # Windows CI deployment
│   └── docker-compose.yml           # CI container configuration
├── local/                       # Local Development (build from source)
│   ├── build-and-deploy.sh          # Unix/Mac local build
│   ├── build-and-deploy.bat         # Windows local build
│   └── docker-compose.yml           # Local build configuration
├── shared/                      # Shared Infrastructure
│   ├── config/                       # Platform-specific configurations
│   │   ├── windows_paths.json            # Windows folder paths
│   │   └── unix_paths.json               # Unix/Mac folder paths
│   ├── scripts/
│   │   └── generate_env.py               # Environment generator (uv-based)
│   ├── Dockerfile                    # Single source of truth for builds
│   ├── docker-compose.base.yml      # Common container configuration
│   └── .env.template                # Environment template
└── data/                        # Persistent data
    ├── chroma_db/                    # ChromaDB storage
    └── logs/                         # Application logs
```

## 🚀 Quick Start Guide

### Option 1: CI Deployment (Recommended)

```bash
# 1. Configure folder paths
edit docker_deployment/shared/config/unix_paths.json     # Mac/Linux
edit docker_deployment/shared/config/windows_paths.json  # Windows

# 2. Set API keys in project root
cat > .env.local << EOF
OPENAI_API_KEY=your_openai_key_here
GOOGLE_API_KEY=your_google_key_here
EOF

# 3. Login to GitHub Container Registry
docker login ghcr.io

# 4. Deploy using CI scripts
./docker_deployment/ci/deploy-from-ghcr.sh              # Unix/Mac
docker_deployment\ci\deploy-from-ghcr.bat               # Windows
```

### Option 2: Local Development

```bash
# 1-2. Same configuration and API key setup as above

# 3. Build and deploy locally
./docker_deployment/local/build-and-deploy.sh           # Unix/Mac  
docker_deployment\local\build-and-deploy.bat            # Windows
```

## 🔧 Development Workflow

### CI Deployment Workflow
```bash
# Deploy latest version
./docker_deployment/ci/deploy-from-ghcr.sh

# Monitor and manage
cd docker_deployment/ci
docker-compose logs -f
docker-compose restart
docker-compose down
```

### Local Development Workflow
```bash
# Build and deploy
./docker_deployment/local/build-and-deploy.sh

# Development cycle
cd docker_deployment/local
docker-compose logs -f          # Monitor logs
# Make code changes...
cd .. && ./local/build-and-deploy.sh  # Rebuild with changes
```

## 📊 Deployment Comparison

| Feature | CI Deployment | Local Development |
|---------|---------------|-------------------|
| **Setup Time** | ⚡ ~2 minutes | 🔧 ~5-10 minutes |
| **Internet Required** | ✅ For initial pull | ❌ After setup |
| **Build Time** | ❌ No build needed | ⏱️ 3-5 minutes |
| **Code Changes** | 🔄 Need new image | ⚡ Immediate rebuild |
| **Debugging** | 🔍 Container logs | 🛠️ Full IDE access |
| **Disk Usage** | 💾 Lower | 💾 Higher (build cache) |
| **Best For** | Testing, demos | Development, debugging |

## 🛠️ Configuration

### Folder Path Configuration

Edit the appropriate configuration file for your platform:

**Unix/Mac**: `shared/config/unix_paths.json`
```json
{
  "source_folder": "~/tmp/rag_store/source",
  "saved_folder": "~/tmp/rag_store/saved",
  "error_folder": "~/tmp/rag_store/error"
}
```

**Windows**: `shared/config/windows_paths.json`
```json
{
  "source_folder": "C:\\temp\\rag_store\\source",
  "saved_folder": "C:\\temp\\rag_store\\saved",
  "error_folder": "C:\\temp\\rag_store\\error"
}
```

### API Key Configuration

Create `.env.local` in the **project root** (not in docker_deployment):
```env
# Required: Choose one or both
OPENAI_API_KEY=your_openai_key_here
GOOGLE_API_KEY=your_google_key_here

# Optional: ChromaDB configuration (defaults to client_server mode)
# CHROMA_CLIENT_MODE=embedded
# CHROMA_SERVER_HOST=localhost
# CHROMA_SERVER_PORT=8000
```

## 🧪 Testing Your Deployment

### Test File Processing
```bash
# 1. Start your chosen deployment
# 2. Copy test files to source folder:
cp test.pdf ~/tmp/rag_store/source/
cp document.docx ~/tmp/rag_store/source/

# 3. Monitor processing
cd docker_deployment/[ci|local]
docker-compose logs -f

# 4. Check results
ls -la ~/tmp/rag_store/saved/    # Successfully processed
ls -la ~/tmp/rag_store/error/    # Failed files + .log files
```

## 🔧 Common Operations

### Container Management (both deployment types)
```bash
# Navigate to deployment directory first
cd docker_deployment/ci          # or docker_deployment/local

# Container operations
docker-compose ps                 # View status
docker-compose logs -f            # Monitor logs
docker-compose restart            # Restart services
docker-compose down               # Stop all containers
docker-compose exec rag-file-processor bash  # Access container

# Resource monitoring
docker stats rag-file-processor
```

### Troubleshooting
```bash
# Check Docker installation
docker info && docker version

# CI Deployment issues
docker login ghcr.io             # Ensure GHCR access
docker pull ghcr.io/rwuniard/rag-file-processor:latest

# Local Build issues
docker-compose build --no-cache  # Clean rebuild
docker system prune              # Clean up Docker resources

# Application debugging
docker-compose logs rag-file-processor
docker-compose exec rag-file-processor python -c "from src.app import FolderFileProcessorApp; print('OK')"
```

### Environment Generation (Advanced)
```bash
# Manual environment generation
cd docker_deployment/shared/scripts

# Development environment
uv run python generate_env.py --environment development --platform unix --model-vendor google

# Production environment  
uv run python generate_env.py --environment production --platform windows --model-vendor openai
```

## 🚀 Migration from Old Scripts

If you were using the old deployment scripts:

| Old Script | New Equivalent |
|------------|----------------|
| `deploy-local.sh` | `local/build-and-deploy.sh` |
| `deploy-local.bat` | `local/build-and-deploy.bat` |
| `docker_deployment_from_ghcr/deploy-ghcr.sh` | `ci/deploy-from-ghcr.sh` |

**Benefits of New Structure**:
- ✅ Clear separation between CI and local deployment
- ✅ Shared infrastructure reduces duplication
- ✅ Better organization and maintainability  
- ✅ Identical container behavior across deployment types
- ✅ Enhanced documentation and guidance

## 📚 Additional Resources

- **Main Documentation**: See `../CLAUDE.md` for comprehensive Docker guide
- **Migration Notes**: See `MIGRATION_NOTES.md` for technical migration details
- **Troubleshooting**: Refer to CLAUDE.md Docker Troubleshooting section
- **System Dependencies**: LibreOffice, Tesseract OCR (pre-installed in containers)