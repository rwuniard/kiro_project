# Docker Deployment for Kiro Project

This directory contains a **simplified Docker deployment system** that cleanly separates build and deployment phases.

## 🚀 New Simplified Workflow

### Build Phase (Separate)
- **Local Build**: `./build/build-local.sh` → Creates `local-rag-file-processor` image
- **CI Build**: `./build/build-ci.sh` → Creates `rag-file-processor-{version}-{sha}` image

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
│   ├── docker-compose.yml           # Simplified compose file
│   └── .env.development             # Template for easy setup
└── shared/                      # Shared Resources
    └── Dockerfile                   # Single Dockerfile for all builds
```

## 🚀 Quick Start Guide

### Step 1: Build Phase

**Local Build** (for development):
```bash
# Unix/Mac
./build/build-local.sh

# Windows  
build\build-local.bat

# Both create: ghcr.io/rwuniard/kiro_project:local-rag-file-processor
```

**CI Build** (for production):
```bash
# Unix/Mac
./build/build-ci.sh

# Windows
build\build-ci.bat

# Creates: ghcr.io/rwuniard/kiro_project:rag-file-processor-{version}-{sha}
# Example: ghcr.io/rwuniard/kiro_project:rag-file-processor-0.1.1-a1b2c3d4
# Version automatically determined from pyproject.toml + git SHA
```

### Step 2: Environment Setup

**Copy the development template**:
```bash
cd deploy/
cp .env.development .env.local
```

**Edit `.env.local` with your settings**:
```env
# === Required Settings ===

# Folder paths for file processing (customize these paths)
SOURCE_FOLDER=~/tmp/rag_store/source
SAVED_FOLDER=~/tmp/rag_store/saved
ERROR_FOLDER=~/tmp/rag_store/error

# Document processing configuration
ENABLE_DOCUMENT_PROCESSING=true
DOCUMENT_PROCESSOR_TYPE=rag_store

# AI Model vendor (choose one: google or openai)
MODEL_VENDOR=google

# API Keys (provide the key for your chosen vendor)
GOOGLE_API_KEY=your_google_key_here
# OPENAI_API_KEY=your_openai_key_here

# === Optional Settings ===

# Application logging (DEBUG for development, INFO for production)
LOG_LEVEL=DEBUG

# File monitoring configuration (optimized for Docker)
FILE_MONITORING_MODE=auto               # Options: auto, events, polling
POLLING_INTERVAL=2.0                    # Seconds (for polling mode)
DOCKER_VOLUME_MODE=true                 # Enable Docker volume optimizations

# ChromaDB mode. The client_server or embedded.
CHROMA_CLIENT_MODE=client_server        # Options: client_server, embedded

# ChromaDB server settings (if using client_server mode)
CHROMA_SERVER_HOST=chromadb
CHROMA_SERVER_PORT=8000

# ChromaDB vector storage configuration for embedded mode.
#CHROMA_DB_PATH=./data/chroma_db_dev     # Development database path
#CHROMA_COLLECTION_NAME=rag-kb           # Collection name for documents
```

### Step 3: Deployment Phase

**Deploy Local Build**:
```bash
# Unix/Mac
./deploy/deploy.sh ghcr.io/rwuniard/kiro_project:local-rag-file-processor .env.local

# Windows
deploy\deploy.bat ghcr.io/rwuniard/kiro_project:local-rag-file-processor .env.local
```

**Deploy CI Build**:
```bash
# Unix/Mac
./deploy/deploy.sh ghcr.io/rwuniard/kiro_project:rag-file-processor-latest .env.local

# Windows  
deploy\deploy.bat ghcr.io/rwuniard/kiro_project:rag-file-processor-latest .env.local
```

**Deploy Specific Version**:
```bash
./deploy/deploy.sh ghcr.io/rwuniard/kiro_project:rag-file-processor-0.1.1-a1b2c3d4 .env.local
```

## 🔧 Prerequisites

### Required
- **Docker**: Container runtime
- **Docker login**: `docker login ghcr.io` (for pulling images)

### For ChromaDB Client-Server Mode
If using `CHROMA_CLIENT_MODE=client_server`, ensure ChromaDB is running:
```bash
# Start ChromaDB server (if using setup_chromadb)
cd ../setup_chromadb
docker compose up -d
```

## 📂 Volume Mapping

The deployment automatically creates and maps these directories:

| Host Directory | Container Directory | Purpose |
|---------------|-------------------|---------|
| `${SOURCE_FOLDER}` | `/app/data/source` | Files to process |
| `${SAVED_FOLDER}` | `/app/data/saved` | Successfully processed files |
| `${ERROR_FOLDER}` | `/app/data/error` | Failed files + error logs |
| `../data/chroma_db` | `/app/data/chroma_db` | ChromaDB storage |
| `../logs` | `/app/logs` | Application logs |

## 🛠️ Management Commands

**View Container Status**:
```bash
cd deploy/
docker compose ps
```

**Monitor Logs**:
```bash
docker compose logs -f
```

**Stop Deployment**:
```bash
docker compose down
```

**Restart Container**:
```bash
docker compose restart
```

## 🗂️ Available Images

| Image Type | Registry Path | Use Case |
|-----------|---------------|----------|
| **Local Development** | `ghcr.io/rwuniard/kiro_project:local-rag-file-processor` | Development builds |
| **CI/Production** | `ghcr.io/rwuniard/kiro_project:rag-file-processor-latest` | Latest CI build |
| **Specific Version** | `ghcr.io/rwuniard/kiro_project:rag-file-processor-{version}-{sha}` | Specific version |

## 🔍 Troubleshooting

### Container Won't Start
1. Check if ChromaDB is running (if using client_server mode)
2. Verify API keys are set correctly
3. Check container logs: `docker compose logs`

### File Processing Issues
1. Ensure source/saved/error directories exist and have proper permissions
2. Check if files are being detected: `docker compose logs -f`
3. Verify Docker volume mounts are working

### Network Issues
1. Ensure mcp-network exists: `docker network ls | grep mcp-network`
2. If using ChromaDB client_server mode, verify both containers are on same network

### Permission Issues
1. Check file permissions in mounted directories
2. Ensure Docker has access to the specified paths

## 🚀 Quick Development Workflow

```bash
# 1. Build local image
./build/build-local.sh

# 2. Setup environment (first time only)
cd deploy/
cp .env.development .env.local
# Edit .env.local with your API keys and paths

# 3. Deploy
./deploy.sh ghcr.io/rwuniard/kiro_project:local-rag-file-processor .env.local

# 4. Test by dropping files in SOURCE_FOLDER
# 5. Monitor logs
docker compose logs -f

# 6. Stop when done
docker compose down
```

This simplified system provides clean separation between building and deploying, with no Python dependencies for deployment!