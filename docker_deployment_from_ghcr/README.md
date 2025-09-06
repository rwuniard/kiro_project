# Docker Deployment from GHCR

Deploy pre-built Kiro Project Docker images from GitHub Container Registry (GHCR) that were built by CI/CD processes.

## Quick Start

### Unix/Mac Deployment

```bash
# Deploy latest image with Google AI (default)
./deploy-ghcr.sh

# Deploy specific tag with OpenAI
./deploy-ghcr.sh v1.2.3 openai

# Deploy with custom repository
./deploy-ghcr.sh latest google ghcr.io/your-org/kiro-project
```

### Windows Deployment

```cmd
# Deploy latest image with Google AI (default)
deploy-ghcr.bat

# Deploy specific tag with OpenAI
deploy-ghcr.bat v1.2.3 openai

# Deploy with custom repository
deploy-ghcr.bat latest google ghcr.io/your-org/kiro-project
```

## Prerequisites

### Docker Requirements
- Docker Desktop or Docker Engine installed and running
- Docker Compose available in PATH
- Access to GitHub Container Registry (GHCR)

### Authentication
Login to GHCR if accessing private repositories:
```bash
docker login ghcr.io
# Username: your-github-username
# Password: your-personal-access-token
```

### API Keys Setup
Create `.env.local` in the project root with your API keys:
```env
OPENAI_API_KEY=your_openai_key_here
GOOGLE_API_KEY=your_google_key_here
```

## Configuration

### Directory Configuration
Edit the appropriate configuration file:
- **Unix/Mac**: `config/unix_paths.json`
- **Windows**: `config/windows_paths.json`

Example configuration:
```json
{
  "source_folder": "~/kiro-ghcr/source",
  "saved_folder": "~/kiro-ghcr/saved",
  "error_folder": "~/kiro-ghcr/error"
}
```

## Deployment Process

The deployment script performs these steps:

1. **Prerequisites Check**: Verifies Docker and docker-compose availability
2. **Directory Setup**: Creates local directories and temporary folders
3. **Permission Setup**: Configures proper permissions for document processing
4. **Image Pull**: Downloads the specified image from GHCR
5. **Environment Generation**: Creates .env file with configuration and API keys
6. **Container Start**: Launches the containerized application

## Container Management

### Monitor Logs
```bash
docker-compose logs -f
```

### Check Status
```bash
docker-compose ps
```

### Stop Containers
```bash
docker-compose down
```

### Restart Containers
```bash
docker-compose restart
```

### Update to Latest Image
```bash
# Stop current containers
docker-compose down

# Deploy new version
./deploy-ghcr.sh latest google

# Or deploy specific version
./deploy-ghcr.sh v1.3.0 google
```

## Environment Variables

The deployment automatically configures these environment variables:

### Core Configuration
- `DOCKER_IMAGE`: Full image name with tag (e.g., `ghcr.io/ronsonw/kiro-project:latest`)
- `SOURCE_FOLDER`: Local source directory path
- `SAVED_FOLDER`: Local saved files directory path  
- `ERROR_FOLDER`: Local error files directory path

### Document Processing
- `ENABLE_DOCUMENT_PROCESSING`: Enable RAG document processing (default: `true`)
- `DOCUMENT_PROCESSOR_TYPE`: Processor type (default: `rag_store`)
- `MODEL_VENDOR`: AI model provider (`openai` or `google`)

### File Monitoring (Docker-optimized)
- `FILE_MONITORING_MODE`: Monitoring mode (`auto`, `events`, `polling`)
- `POLLING_INTERVAL`: Polling interval in seconds (default: `2.0`)
- `DOCKER_VOLUME_MODE`: Enable Docker volume optimizations (default: `true`)

### ChromaDB Configuration
- `CHROMA_CLIENT_MODE`: ChromaDB client mode (default: `embedded`)
- `CHROMA_DB_PATH`: Database storage path (default: `./data/chroma_db`)
- `CHROMA_COLLECTION_NAME`: Collection name (default: `rag-kb`)

## Volumes and Data Persistence

### Volume Mappings
- `${SOURCE_FOLDER} → /app/data/source`: Files to process
- `${SAVED_FOLDER} → /app/data/saved`: Successfully processed files
- `${ERROR_FOLDER} → /app/data/error`: Failed files with error logs
- `./data/chroma_db → /app/data/chroma_db`: Persistent ChromaDB storage
- `./logs → /app/logs`: Application logs
- `/tmp/file-processor-unstructured → /tmp/unstructured`: Temporary processing files

### Data Persistence
- **ChromaDB data** is persisted in the local `data/chroma_db` directory
- **Application logs** are persisted in the local `logs` directory
- **Processed files** are moved to configured saved/error directories

## Differences from Local Build Deployment

### Key Differences
- **No Build Process**: Uses pre-built images from GHCR instead of building locally
- **Image Source**: Downloads from GitHub Container Registry
- **Version Control**: Supports deploying specific tagged versions
- **CI/CD Integration**: Designed for images built by automated CI/CD pipelines
- **Repository Flexibility**: Supports custom GHCR repositories

### Advantages
✅ **Faster Deployment**: No build time, just download and run  
✅ **Consistent Images**: Uses identical images across environments  
✅ **Version Control**: Easy rollback to previous versions  
✅ **CI/CD Ready**: Integrates with automated build pipelines  
✅ **Bandwidth Efficient**: Docker layer caching reduces download sizes  

### Use Cases
- **Production Deployments**: Deploy stable, tested images
- **Staging Environments**: Test specific release candidates
- **Quick Setup**: Rapid deployment without local build requirements
- **Team Collaboration**: Ensure all team members use identical images
- **Rollback Scenarios**: Quick deployment of previous working versions

## Troubleshooting

### Image Pull Issues
```bash
# Check if you can access the registry
docker login ghcr.io

# Verify image exists
docker search ghcr.io/ronsonw/kiro-project

# Check image details
docker manifest inspect ghcr.io/ronsonw/kiro-project:latest
```

### Permission Issues
The deployment script automatically creates temporary directories with proper permissions. If you encounter permission errors:

```bash
# Unix/Mac: Check temporary directory permissions
ls -ld /tmp/file-processor-unstructured

# Windows: Ensure temp directory exists
dir C:\temp\file-processor-unstructured
```

### Container Health Issues
```bash
# Check container health
docker-compose ps

# View detailed logs
docker-compose logs rag-file-processor-ghcr

# Inspect container
docker inspect rag-file-processor-ghcr
```

### Environment Issues
```bash
# Check generated environment file
cat .env

# Verify API keys are loaded
docker-compose exec rag-file-processor-ghcr env | grep API_KEY
```

## Security Considerations

### API Keys
- Store API keys in `.env.local` (excluded from version control)
- Use environment-specific keys for different deployments
- Rotate keys regularly and update deployments

### Image Security
- Verify image signatures when possible
- Use specific version tags instead of `latest` for production
- Regularly update to newer versions for security patches

### Network Security
- Images run on isolated Docker networks
- Only required ports are exposed
- Consider firewall rules for production deployments

## Integration with CI/CD

This deployment method is designed to work with CI/CD pipelines that:

1. **Build images** in automated CI processes
2. **Push images** to GHCR with version tags
3. **Deploy images** using these scripts in target environments
4. **Support rollback** by deploying previous versions

Example CI/CD workflow integration:
```yaml
# In your CI/CD pipeline
- name: Deploy to Production
  run: |
    ./docker_deployment_from_ghcr/deploy-ghcr.sh ${{ github.sha }} google
```