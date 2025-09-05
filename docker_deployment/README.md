# Docker Deployment for Kiro Project

This directory contains all Docker deployment configurations and scripts for the Kiro Project. It provides a complete, isolated environment with all system dependencies pre-installed.

## 📁 Directory Structure

```
docker_deployment/
├── config/                    # Environment-specific configuration files
│   ├── dev_chroma_settings.json     # Development ChromaDB configuration
│   ├── prod_chroma_settings.json    # Production ChromaDB configuration
│   ├── windows_paths.json           # Windows folder paths
│   └── unix_paths.json              # Unix/Mac folder paths
├── scripts/
│   └── generate_env.py              # Environment configuration generator
├── Dockerfile                      # Multi-stage Docker build configuration
├── docker-compose.yml             # Main container configuration
├── docker-compose.override.yml    # Development-specific overrides
├── .dockerignore                  # Docker build context exclusions
├── .env.template                  # Environment template with placeholders
├── deploy-local.bat               # Windows deployment script
├── deploy-local.sh                # Unix/Mac deployment script
└── README.md                      # This file
```

## 🚀 Quick Start

### Prerequisites

- **Docker** and **docker-compose** installed and running
- **Python 3.8+** (for configuration scripts)
- **API Keys**: OpenAI and/or Google API keys

### Windows Deployment

1. **Configure Paths**: Edit `config/windows_paths.json`:
   ```json
   {
     "source_folder": "C:\\temp\\kiro\\source",
     "saved_folder": "C:\\temp\\kiro\\saved", 
     "error_folder": "C:\\temp\\kiro\\error"
   }
   ```

2. **Set API Keys**: Create `.env.local` in project root (parent directory):
   ```env
   OPENAI_API_KEY=your_openai_key_here
   GOOGLE_API_KEY=your_google_key_here
   ```

3. **Deploy** (from project root):
   ```cmd
   docker_deployment\deploy-local.bat
   docker_deployment\deploy-local.bat google
   ```

### Unix/Mac Deployment

1. **Configure Paths**: Edit `config/unix_paths.json`:
   ```json
   {
     "source_folder": "/tmp/kiro/source",
     "saved_folder": "/tmp/kiro/saved",
     "error_folder": "/tmp/kiro/error"
   }
   ```

2. **Set API Keys**: Create `.env.local` in project root (parent directory):
   ```env
   OPENAI_API_KEY=your_openai_key_here
   GOOGLE_API_KEY=your_google_key_here
   ```

3. **Deploy** (from project root):
   ```bash
   ./docker_deployment/deploy-local.sh
   ./docker_deployment/deploy-local.sh google
   ```

## 🔧 Configuration Files

### ChromaDB Settings

Both development and production use **client_server** mode by default, connecting to a ChromaDB container named `chromadb` in the `mcp-network`.

#### `config/dev_chroma_settings.json`
```json
{
  "chroma_client_mode": "client_server",
  "chroma_server_host": "chromadb",
  "chroma_server_port": 8000,
  "chroma_collection_name": "rag-kb-dev"
}
```

#### `config/prod_chroma_settings.json` 
```json
{
  "chroma_client_mode": "client_server", 
  "chroma_server_host": "chromadb",
  "chroma_server_port": 8000,
  "chroma_collection_name": "rag-kb-prod"
}
```

**ChromaDB Mode Options:**
- `"client_server"`: Uses external ChromaDB server (recommended)
  - ✅ Better performance and data persistence
  - ✅ Concurrent access support
- `"embedded"`: Uses local file-based storage
  - ✅ Simpler setup, no external dependencies
  - To use: Uncomment `_chroma_db_path` field and change mode

### Folder Path Settings

Configure where Docker will map local folders for file processing.

#### `config/windows_paths.json`
```json
{
  "source_folder": "C:\\temp\\kiro\\source",
  "saved_folder": "C:\\temp\\kiro\\saved",
  "error_folder": "C:\\temp\\kiro\\error",
  "description": "Windows folder paths - modify for your local setup"
}
```

#### `config/unix_paths.json`
```json
{
  "source_folder": "/tmp/kiro/source", 
  "saved_folder": "/tmp/kiro/saved",
  "error_folder": "/tmp/kiro/error",
  "description": "Unix/Mac folder paths - modify for your local setup"
}
```

## 🛠️ Scripts

### `deploy-local.bat` / `deploy-local.sh`

**Purpose**: Complete deployment automation for local development

**Usage**:
```bash
# Use OpenAI (default)
./deploy-local.sh

# Use Google AI
./deploy-local.sh google
```

**What it does**:
1. ✅ Validates prerequisites (Docker, Python, required files)
2. ✅ Creates local directories from path configuration
3. ✅ Generates `.env` file from templates and settings
4. ✅ Builds Docker image with all dependencies
5. ✅ Starts container with volume mapping

### `scripts/generate_env.py`

**Purpose**: Environment configuration generator that merges templates with settings

**Usage**:
```bash
python scripts/generate_env.py --environment development --platform unix --model-vendor openai
```

**Options**:
- `--environment`: `development` or `production`
- `--platform`: `unix` or `windows` 
- `--model-vendor`: `openai` or `google`

**What it does**:
- Reads `.env.template` and replaces placeholders
- Loads ChromaDB settings from `config/*.json`
- Loads folder paths from platform-specific config
- Injects API keys from `.env.local` (dev) or environment variables (prod)
- Generates `.env.generated` file for Docker container

## 🐳 Docker Configuration

### Container Architecture

The deployment creates a container named `rag-file-processor` that:
- ✅ Connects to `mcp-network` for ChromaDB communication
- ✅ Maps local folders for file processing
- ✅ Persists ChromaDB data and application logs
- ✅ Includes all system dependencies (Tesseract, LibreOffice)

### Volume Mapping

```yaml
Local Path              → Container Path
${SOURCE_FOLDER}        → /app/data/source    # Files to process
${SAVED_FOLDER}         → /app/data/saved     # Successfully processed  
${ERROR_FOLDER}         → /app/data/error     # Failed files with logs
./data/chroma_db        → /app/data/chroma_db # ChromaDB storage
./logs                  → /app/logs           # Application logs
```

### Network Configuration

The container joins the external `mcp-network` to communicate with:
- **ChromaDB container** (`chromadb:8000`)
- **Other MCP services** as needed

## 📋 Container Management

### Basic Operations
```bash
# View container status
docker-compose ps

# Monitor application logs
docker-compose logs -f rag-file-processor

# Start containers
docker-compose up -d

# Stop containers  
docker-compose down

# Restart containers
docker-compose restart

# View resource usage
docker stats rag-file-processor
```

### Development Operations
```bash
# Execute commands inside container
docker-compose exec rag-file-processor bash

# Run tests inside container
docker-compose exec rag-file-processor uv run pytest

# Check Python version
docker-compose exec rag-file-processor python --version

# Rebuild after code changes
docker-compose down
docker-compose up --build -d
```

## 🔍 Troubleshooting

### Common Issues

**Docker Build Fails**:
```bash
# Check Docker is running
docker info

# Clean up if needed  
docker system prune

# Rebuild without cache
docker-compose build --no-cache
```

**Container Won't Start**:
```bash
# Check container logs
docker-compose logs rag-file-processor

# Validate configuration
python scripts/generate_env.py --environment development --platform unix
```

**Volume Mapping Issues**:
- ✅ Verify folder paths in `config/*.json` exist
- ✅ Check folder permissions (readable/writable)
- ✅ Ensure proper path format (Windows: `C:\path`, Unix: `/path`)

**ChromaDB Connection Issues**:
```bash
# Verify mcp-network exists
docker network ls | grep mcp-network

# Check if ChromaDB container is running
docker ps | grep chromadb

# Test network connectivity
docker-compose exec rag-file-processor ping chromadb
```

**API Keys Not Working**:
- ✅ Verify `.env.local` exists in project root (not docker_deployment folder)
- ✅ Check keys don't have extra spaces or quotes
- ✅ Confirm model vendor matches available API key

### Debug Mode

**Manual Environment Generation**:
```bash
# Test configuration generation
python scripts/generate_env.py --help
python scripts/generate_env.py --environment development --platform unix

# View generated configuration
cat .env.generated
```

**Container Inspection**:
```bash
# View container filesystem
docker-compose exec rag-file-processor ls -la /app

# Check environment variables
docker-compose exec rag-file-processor env | grep CHROMA

# Test Python imports
docker-compose exec rag-file-processor python -c "from src.app import FolderFileProcessorApp; print('Import successful')"
```

## 📊 Usage Workflow

### Daily Development Cycle

1. **Start Monitoring**:
   ```bash
   docker-compose logs -f rag-file-processor
   ```

2. **Process Files**:
   - Drop files into your configured `source_folder`
   - Monitor logs for processing status
   - Check results in `saved_folder` or `error_folder`

3. **Stop When Done**:
   ```bash
   docker-compose down
   ```

### File Processing Results

- **✅ Success**: Files moved to `saved_folder` with preserved directory structure
- **❌ Failure**: Files moved to `error_folder` with detailed `.log` files
- **📊 Data**: ChromaDB vector storage persisted in `./data/chroma_db`
- **📝 Logs**: Application logs available in `./logs`

## 🏭 Production Deployment

For production deployment, the GitHub Actions workflow:
1. Reads API keys from repository secrets
2. Uses `prod_chroma_settings.json` configuration  
3. Builds optimized Docker image
4. Provides deployment artifacts

See `.github/workflows/deploy.yml` for complete CI/CD configuration.

---

## 💡 Tips

- **🔄 Iterative Development**: Use `docker-compose restart` after configuration changes
- **📁 Organize Files**: Use subdirectories in source folder - structure is preserved
- **🔍 Monitor Progress**: Keep logs open with `docker-compose logs -f`  
- **🧹 Clean Up**: Use `docker-compose down -v` to remove volumes (⚠️ deletes ChromaDB data)
- **⚡ Performance**: ChromaDB client_server mode provides better performance than embedded mode

## 🆘 Support

- **Documentation**: Check main project README.md for detailed application information
- **Logs**: Always check `docker-compose logs rag-file-processor` for error details
- **Configuration**: Use `generate_env.py --help` for configuration options
- **Testing**: Run container tests with `docker-compose exec rag-file-processor uv run pytest`