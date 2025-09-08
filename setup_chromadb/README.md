# ChromaDB Server Setup

This directory contains scripts and configuration for running a standalone ChromaDB server using Docker. The ChromaDB server provides vector database capabilities that can be used by the RAG file processor and other applications.

## Files

- `chromadb-server.sh` - Unix/Mac management script
- `chromadb-server.bat` - Windows management script  
- `docker-compose.yml` - Docker Compose configuration
- `README.md` - This documentation

## Quick Start

### Unix/Mac
```bash
# Make script executable (first time only)
chmod +x chromadb-server.sh

# Start the server
./chromadb-server.sh start

# Check health
./chromadb-server.sh health
```

### Windows
```batch
# Start the server
chromadb-server.bat start

# Check health
chromadb-server.bat health
```

## Available Commands

Both scripts support the same commands:

| Command | Description |
|---------|-------------|
| `start` | Start ChromaDB server and create network |
| `stop` | Stop ChromaDB server |
| `restart` | Restart ChromaDB server |
| `status` | Show server container status |
| `logs` | Show server logs (follow mode) |
| `health` | Check server health via HTTP |
| `clean` | **DANGEROUS** - Stop server and delete all data |

## Server Details

**Network Configuration:**
- **Port**: 8000 (HTTP API)
- **Host**: localhost
- **Network**: mcp-network (Docker bridge network)
- **Container Name**: chromadb

**API Endpoints:**
- **Health Check**: `http://localhost:8000/api/v1/heartbeat`  
- **Version Info**: `http://localhost:8000/api/v2/version`
- **API Documentation**: `http://localhost:8000/docs` (if available)

**Data Persistence:**
- **Host Path**: `./data/chroma_data/`
- **Container Path**: `/data`
- **Backup**: Copy `./data/chroma_data/` to backup ChromaDB data

## Docker Network

The scripts automatically create an external Docker network called `mcp-network`. This allows the ChromaDB server to be accessible from other Docker containers using the hostname `chromadb`.

**Network Details:**
- **Name**: mcp-network
- **Type**: Bridge network
- **External**: Yes (shared across compose projects)

## Configuration

The server is configured via environment variables in `docker-compose.yml`:

```yaml
environment:
  - CHROMA_SERVER_HOST=0.0.0.0          # Listen on all interfaces
  - CHROMA_SERVER_HTTP_PORT=8000        # HTTP API port
  - CHROMA_SERVER_GRPC_PORT=8001        # gRPC port (internal)
  - CHROMA_SERVER_CORS_ALLOW_ORIGINS=["*"]  # CORS settings
```

## Health Monitoring

The container includes built-in health checks:
- **Check Interval**: Every 30 seconds
- **Timeout**: 10 seconds  
- **Retries**: 3 attempts
- **Start Period**: 40 seconds (initial startup time)

## Usage Examples

### Basic Server Management
```bash
# Unix/Mac
./chromadb-server.sh start
./chromadb-server.sh health
./chromadb-server.sh logs
./chromadb-server.sh stop
```

```batch
REM Windows
chromadb-server.bat start
chromadb-server.bat health  
chromadb-server.bat logs
chromadb-server.bat stop
```

### Integration with Applications

**Python Client (localhost):**
```python
import chromadb

# Connect to local server
client = chromadb.HttpClient(host="localhost", port=8000)
collection = client.get_or_create_collection("my-collection")
```

**Docker Container (same network):**
```python
import chromadb

# Connect from another container on mcp-network
client = chromadb.HttpClient(host="chromadb", port=8000)
collection = client.get_or_create_collection("my-collection")
```

**Environment Variables:**
```bash
# For applications connecting to this server
export CHROMA_HOST=localhost       # or 'chromadb' from Docker
export CHROMA_PORT=8000
export CHROMA_HTTP_URL=http://localhost:8000
```

## Troubleshooting

### Server Won't Start
```bash
# Check Docker is running
docker --version

# Check if port 8000 is in use
netstat -an | grep 8000      # Unix/Mac
netstat -an | findstr 8000   # Windows

# Check container logs
./chromadb-server.sh logs    # Unix/Mac
chromadb-server.bat logs     # Windows
```

### Network Issues
```bash
# Recreate the network
docker network rm mcp-network
./chromadb-server.sh start   # Will recreate network
```

### Data Issues
```bash
# Check data directory permissions
ls -la data/chroma_data/     # Unix/Mac
dir data\chroma_data\        # Windows

# Clean and restart (WARNING: deletes all data)
./chromadb-server.sh clean   # Unix/Mac
chromadb-server.bat clean    # Windows
```

### Health Check Failures
```bash
# Manual health check
curl http://localhost:8000/api/v1/heartbeat

# Or using PowerShell (Windows)
Invoke-WebRequest -Uri http://localhost:8000/api/v1/heartbeat
```

## Data Backup and Restore

### Backup
```bash
# Stop server first
./chromadb-server.sh stop

# Copy data directory  
cp -r data/chroma_data backup/chroma_data_$(date +%Y%m%d)   # Unix/Mac
robocopy data\chroma_data backup\chroma_data_%date:~-4,4%%date:~-10,2%%date:~-7,2% /E   # Windows
```

### Restore
```bash
# Stop server and clean
./chromadb-server.sh clean

# Restore data
cp -r backup/chroma_data_20240308/* data/chroma_data/   # Unix/Mac
robocopy backup\chroma_data_20240308 data\chroma_data /E   # Windows

# Start server
./chromadb-server.sh start
```

## Security Considerations

⚠️ **Production Deployment Notes:**
- This setup is intended for **development and testing**
- CORS is set to allow all origins (`["*"]`)
- No authentication is configured
- Server listens on all interfaces (`0.0.0.0`)

**For production use, consider:**
- Configuring authentication
- Restricting CORS origins
- Using HTTPS/TLS
- Implementing access controls
- Regular data backups
- Network security (firewall rules)

## Version Information

- **ChromaDB Version**: 1.0.20
- **Docker Image**: `chromadb/chroma:1.0.20`
- **Restart Policy**: unless-stopped
- **Network Mode**: Bridge (mcp-network)