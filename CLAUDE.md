# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Package Management
This project uses `uv` for dependency management:

```bash
# Install dependencies
uv sync

# Install with development dependencies
uv sync --group dev

# Run commands in the virtual environment
uv run python main.py
uv run pytest
```

### Running the Application

```bash
# Run the main application
uv run python main.py

# Alternative if virtual environment is activated
python main.py
```

### Testing

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/test_file_processor.py

# Run with coverage report
uv run pytest --cov=src --cov-report=html

# Run integration tests specifically
uv run pytest tests/test_rag_integration_comprehensive/
```

### Docker Development Commands

This project supports **two distinct Docker deployment paths** to meet different development and deployment needs:

## Deployment Path Choice

### 🚀 CI Deployment (Recommended for Quick Start)
**Pull pre-built images from GitHub Container Registry**
- **When to use**: Quick start, production-like testing, minimal setup
- **Benefits**: Fast deployment, no local build requirements, consistent images
- **Requirements**: Internet connection, Docker login to GHCR

### 🔧 Local Development Deployment  
**Build images locally from source**
- **When to use**: Active development, debugging, offline work, custom modifications
- **Benefits**: Full control over build process, immediate code changes, offline capability
- **Requirements**: Local build environment, longer initial setup

---

## CI Deployment (Pre-built Images)

### Quick Start - CI Deployment

```bash
# Windows (from project root)
docker_deployment\ci\deploy-from-ghcr.bat                # Deploy latest (Google AI default)
docker_deployment\ci\deploy-from-ghcr.bat latest openai  # Deploy with OpenAI
docker_deployment\ci\deploy-from-ghcr.bat v1.0.0 google  # Deploy specific version

# Unix/Mac (from project root) 
./docker_deployment/ci/deploy-from-ghcr.sh                # Deploy latest (Google AI default)
./docker_deployment/ci/deploy-from-ghcr.sh latest openai  # Deploy with OpenAI
./docker_deployment/ci/deploy-from-ghcr.sh v1.0.0 google  # Deploy specific version
```

### CI Deployment Configuration

```bash
# One-time setup for CI deployment
1. Edit docker_deployment/shared/config/unix_paths.json (Mac/Linux) or windows_paths.json (Windows)
2. Create .env.local with API keys in project root
3. Login to GitHub Container Registry: docker login ghcr.io
4. Run CI deployment script

# Available images at: ghcr.io/rwuniard/rag-file-processor
# Tags: latest, v1.0.0, v1.1.0, etc.
```

---

## Local Development Deployment (Build from Source)

### Local Build and Deploy

```bash
# Windows (from project root)
docker_deployment\local\build-and-deploy.bat                # Build and deploy (Google AI default)
docker_deployment\local\build-and-deploy.bat openai        # Build with OpenAI
docker_deployment\local\build-and-deploy.bat google        # Build with Google AI

# Unix/Mac (from project root)
./docker_deployment/local/build-and-deploy.sh               # Build and deploy (Google AI default)
./docker_deployment/local/build-and-deploy.sh openai       # Build with OpenAI
./docker_deployment/local/build-and-deploy.sh google       # Build with Google AI
```

### Local Development Workflow

```bash
# Initial setup (one time)
1. Edit docker_deployment/shared/config/unix_paths.json (Mac/Linux) or windows_paths.json (Windows)
2. Create .env.local with API keys in project root
3. Run local build script: ./docker_deployment/local/build-and-deploy.sh

# Development cycle
docker compose logs -f          # Monitor application (from docker_deployment/local/)
# Drop test files into source folder (including .docx/.doc files)
docker compose restart          # Restart if needed
docker compose down             # Stop when done

# Rebuilding after code changes
./docker_deployment/local/build-and-deploy.sh  # Rebuild and redeploy
```

---

## Common Docker Operations

Both deployment paths support the same container management commands:

```bash
# Container Management (run from deployment directory: ci/ or local/)
docker compose ps               # View container status
docker compose logs -f          # Monitor real-time logs
docker compose logs -f rag-file-processor  # Monitor specific service
docker compose up -d            # Start in background
docker compose down             # Stop containers
docker compose restart          # Restart containers
docker stats rag-file-processor # View resource usage

# Container Debugging
docker compose exec rag-file-processor bash
docker compose exec rag-file-processor python --version
docker compose exec rag-file-processor uv run pytest

# For local builds only
docker compose up --build       # Force rebuild
```

### Environment Configuration

Both deployment paths use shared configuration management:

```bash
# Manual environment generation (if needed)
cd docker_deployment/shared/scripts
uv run python generate_env.py --environment production --platform unix --model-vendor google
uv run python generate_env.py --environment development --platform windows --model-vendor openai
```

### Docker Volume Structure

Both deployment paths use identical volume mapping:

```bash
# Local Folder Structure (configurable via shared/config/*.json)
source/          → /app/data/source     (files to process)
saved/           → /app/data/saved      (successfully processed files)  
error/           → /app/data/error      (failed files with .log files)
./data/chroma_db → /app/data/chroma_db  (persistent ChromaDB storage)
./logs           → /app/logs            (application logs)

# Temporary Directories (automatically created by deployment scripts)
/tmp/file-processor-unstructured → /tmp/unstructured  (Unix/Mac)
C:\temp\file-processor-unstructured → /tmp/unstructured  (Windows)
```

### Docker Troubleshooting

```bash
# General Docker issues
docker info && docker version   # Check Docker installation
docker system prune            # Clean up unused resources

# CI Deployment troubleshooting
docker login ghcr.io           # Ensure GHCR access
docker pull ghcr.io/rwuniard/rag-file-processor:latest  # Test image access

# Local Build troubleshooting  
docker compose build --no-cache # Force clean rebuild
docker compose logs rag-file-processor  # Check container logs

# Container debugging (both paths)
docker compose exec rag-file-processor ls -la /app
docker compose exec rag-file-processor python -c "from src.app import FolderFileProcessorApp; print('Import successful')"

# Clean up (WARNING: deletes ChromaDB data)
docker compose down -v
```

### Docker Volume File Monitoring

**Important**: Docker volume mounts have known issues with file system events on Windows and macOS. This application automatically detects Docker environments and uses polling-based monitoring for reliable file detection.

**Monitoring Modes**:
- **`auto` (recommended)**: Automatically detects Docker environment and chooses optimal mode
- **`events`**: Uses file system events (watchdog) - fastest but doesn't work in Docker volumes
- **`polling`**: Scans directory periodically - works reliably in Docker volumes

**Docker-Specific Configuration**:
```env
FILE_MONITORING_MODE=auto        # Let system choose best mode
POLLING_INTERVAL=2.0            # Faster polling for Docker (default: 3.0)
DOCKER_VOLUME_MODE=true         # Enable Docker optimizations
```

**Troubleshooting Docker File Detection**:
- If files aren't being processed: Set `FILE_MONITORING_MODE=polling`
- For faster response: Reduce `POLLING_INTERVAL` to 1.0-2.0 seconds
- For batch processing: Enable `DOCKER_VOLUME_MODE=true`

### Deployment Path Comparison

| Aspect | CI Deployment | Local Development |
|--------|---------------|-------------------|
| **Setup Time** | ⚡ Very Fast (~2 min) | 🔧 Moderate (~5-10 min) |
| **Internet Required** | ✅ Yes (for pull) | ❌ No (after initial setup) |
| **Build Requirements** | ❌ None | ✅ Full build environment |
| **Code Changes** | 🔄 Need new image push | ⚡ Immediate rebuild |
| **Debugging** | 🔍 Container logs only | 🔧 Full development access |
| **Disk Usage** | 💾 Lower (no build cache) | 💾 Higher (build cache) |
| **Use Cases** | Quick start, testing, demos | Development, debugging, offline |

**Migration from Old Scripts**:
- Old `deploy-local.sh` → New `local/build-and-deploy.sh`
- No direct old equivalent → New `ci/deploy-from-ghcr.sh`

## Recent Updates and Fixes

The project has been recently updated with significant improvements to the test suite, Docker deployment, and overall reliability:

### Docker Deployment Improvements ✅
- **Fixed Office Document Processing**: Resolved permission denied errors when processing .docx/.doc files in Docker containers
- **Automated Permission Setup**: Deployment scripts now automatically create and configure temporary directories with proper permissions
- **Enhanced Dockerfile**: Added proper user permissions and temporary directory setup for document processing
- **Cross-Platform Support**: Updated both Unix/Mac and Windows deployment scripts with automatic temp directory management
- **Environment Variable Configuration**: Added TMPDIR, TEMP, TMP, and HOME environment variables for proper temp file handling

### Test Suite Improvements ✅
- **Fixed all failing tests** across comprehensive integration test files
- **Resolved ProcessingResult attribute issues** by adding proper `hasattr` checks
- **Fixed API key validation issues** by updating test keys to meet strict requirements
- **Corrected mock processor behavior** to respect test fixture expectations
- **Improved test isolation** with better environment variable management
- **Fixed file monitoring test assertions** for proper integration testing
- **Resolved processor initialization failure tests** with correct error scenarios

### Test Files Fixed
- `test_comprehensive_integration.py` - All 9 tests now passing
- `test_end_to_end_workflow.py` - All 9 tests now passing  
- `test_performance_stress.py` - All 11 tests now passing
- `test_regression.py` - All 15 tests now passing

### Recent Technical Improvements
- **PDF Processing Stability**: Maintains PyMuPDF as primary PDF processor with full OCR capabilities
- **Test Suite Reliability**: All 450+ tests passing with improved error handling and mock behavior
- **Python 3.12 Compatibility**: Optimized for modern Python versions with stable dependencies
- **OCR Processing**: Enhanced OCR capabilities for image-based PDFs with Tesseract integration

### Current Status
- **Total Tests**: 450+ tests
- **Status**: All tests passing ✅
- **Coverage**: Comprehensive test coverage maintained
- **Integration**: Full end-to-end workflow testing working
- **Stability**: PDF processing using stable PyMuPDF with full OCR support ✅

## Project Architecture

This is a sophisticated Python file monitoring and processing application with pluggable RAG (Retrieval Augmented Generation) document processing capabilities. The architecture follows a modular design with clear separation of concerns and supports both basic file processing and advanced document processing with vector embeddings.

### Core Architecture Components

**Application Orchestration (`src/app.py`)**:
- `FolderFileProcessorApp`: Main orchestrator managing complete application lifecycle
- 8-step initialization sequence with dependency validation and health monitoring
- Periodic health checks (30s intervals) and statistics reporting (5-minute intervals)
- Graceful shutdown with signal handling and resource cleanup
- Supports conditional document processing with graceful degradation

**Configuration Management (`src/config/`)**:
- `ConfigManager`: Environment variable loading with comprehensive validation
- `AppConfig`: Main configuration dataclass with validation methods
- `DocumentProcessingConfig`: RAG-specific configuration with API key validation
- Runtime configuration validation including dependency checks and ChromaDB accessibility

**Real-time Monitoring (`src/core/file_monitor.py`)**:
- Cross-platform file system event monitoring using watchdog library
- Recursive monitoring of source folder and all subdirectories
- Event filtering and deduplication to handle rapid file system changes
- Integration with file processor for immediate processing dispatch

**Processing Engine (`src/core/file_processor.py`)**:
- Orchestrates file processing with exponential backoff retry logic (max 3 attempts)
- Error classification system for transient vs. permanent failures
- Processing statistics tracking and reporting
- Integration with pluggable document processing interface

**File Management (`src/core/file_manager.py`)**:
- Atomic file operations with folder structure preservation
- Recursive empty folder cleanup after successful processing
- Safe file movement with destination directory creation
- Handles both regular files and completely empty folders

**Document Processing Interface (`src/core/document_processing.py`)**:
- Abstract interface for pluggable document processing systems
- Standardized `ProcessingResult` and `DocumentProcessingError` data classes
- File validation methods and resource cleanup contracts
- Designed for extensibility beyond RAG to other processing systems

**RAG Store Processor (`src/core/rag_store_processor.py`)**:
- Concrete implementation using existing RAG store components
- Integration with ProcessorRegistry for multi-format document support
- ChromaDB vector storage with configurable embedding providers
- Processing result tracking with chunks created and metadata

**Services Layer**:
- `LoggerService`: Centralized structured logging with file and console output
- `ErrorHandler`: Enhanced error log creation with filename preservation and detailed context

**RAG Store Components (`src/rag_store/`)**:
- `ProcessorRegistry`: Multi-format document processor factory with automatic file type routing
- **Office Processor**: Unified processor for Microsoft Office (Word, PowerPoint, Excel), OpenDocument formats (ODT, ODP, ODS), RTF, and eBooks using `unstructured[all-docs]`
- **MHT Processor**: Dedicated processor for MHT/MHTML web archives with MIME multipart parsing and BeautifulSoup HTML extraction
- **PDF Processor**: PyMuPDF with OCR support for image-based PDFs using Tesseract
- **Text Processor**: Plain text and Markdown document processing
- **Smart Content Detection**: RTF content detection in .doc files with automatic processor routing
- **ChromaDB Integration**: Vector storage with collection management and embedding provider support
- **Embedding Providers**: OpenAI and Google embedding model support
- **Standalone CLI**: Direct document processing interface

### Data Flow Architecture

```
File System Event → FileMonitor → FileProcessor → DocumentProcessingInterface
                                      ↓
                          ProcessingResult ← RAGStoreProcessor → ProcessorRegistry
                                      ↓                              ↓
                            FileManager ←                    ChromaDB Storage
                                      ↓
                  Success: SAVED_FOLDER | Failure: ERROR_FOLDER + Enhanced Error Log
                                      ↓
                         Recursive Empty Folder Cleanup
```

**Detailed Processing Flow**:
1. **Event Detection**: Cross-platform file system events trigger immediate processing
2. **File Validation**: Path validation and accessibility checks before processing
3. **Processing Dispatch**: Route to appropriate document processor based on file extension
4. **RAG Pipeline**: Document parsing → Text chunking → Embedding generation → ChromaDB storage
5. **Result Handling**: Successful files moved to saved folder, failures moved to error folder
6. **Enhanced Error Logging**: Failed files get detailed `.log` files with processing context
7. **Cleanup Operations**: Recursive empty folder removal maintaining folder structure integrity

### Key Design Patterns

**Pluggable Architecture**: Document processing via abstract interface supports multiple processors

**Error Classification**: Sophisticated retry logic distinguishing transient from permanent failures

**Graceful Degradation**: Application continues functioning when document processing is unavailable

**Resource Safety**: Comprehensive cleanup with health monitoring and timeout handling

**Configuration Validation**: Runtime validation of dependencies, API keys, and storage accessibility

**Structured Logging**: Enhanced error context including processor type, file metadata, and processing statistics

## Configuration Requirements

The application requires a `.env` file with the following structure:

```env
# Required - Basic file processing
SOURCE_FOLDER=/path/to/source
SAVED_FOLDER=/path/to/saved
ERROR_FOLDER=/path/to/error

# Optional - File monitoring configuration for Docker volumes
FILE_MONITORING_MODE=auto  # auto, events, polling
POLLING_INTERVAL=3.0       # seconds (for polling mode)
DOCKER_VOLUME_MODE=false   # Docker volume optimizations

# Optional - Document processing with RAG
ENABLE_DOCUMENT_PROCESSING=true
DOCUMENT_PROCESSOR_TYPE=rag_store
MODEL_VENDOR=openai  # or google
CHROMA_DB_PATH=./data/chroma_db_openai
OPENAI_API_KEY=your_key_here  # if using OpenAI
GOOGLE_API_KEY=your_key_here  # if using Google
```

## System Requirements

### Document Processing Dependencies

The application requires the following system dependencies for full document processing capabilities:

#### Office Document Processing
Comprehensive support for Microsoft Office, OpenDocument, and related formats.
**macOS (using Homebrew):**
```bash
brew install --cask libreoffice
```

**Ubuntu/Debian:**
```bash
sudo apt-get install libreoffice
```

**Windows:**
- Download from https://www.libreoffice.org/download/download-libreoffice/
- Or use chocolatey: `choco install libreoffice`

#### OCR Processing (PDF image extraction)
**macOS (using Homebrew):**
```bash
brew install tesseract
```

**Ubuntu/Debian:**
```bash
sudo apt-get install tesseract-ocr
```

**Windows:**
- Download from [GitHub releases](https://github.com/UB-Mannheim/tesseract/wiki)
- Or use chocolatey: `choco install tesseract`

**Verify Installation:**
```bash
pandoc --version
libreoffice --version
tesseract --version
```

### Smart File Processing Features
- **RTF Detection**: Automatically detects RTF content in files with `.doc` extensions and routes to unified office processor
- **Format-Specific Optimization**: Unified office processor applies format-specific chunking strategies (Word: 1000/150, PowerPoint: 800/120, Excel: 1200/180, etc.)
- **Comprehensive Office Support**: Unified processor handles Word, PowerPoint, Excel, OpenDocument, RTF, and eBooks
- **Dedicated MHT Processing**: Specialized processor for MHT/MHTML web archives with MIME parsing
- **OCR Processing**: Automatically applies OCR to PDF pages with no text content when tesseract is available
- **System File Filtering**: Automatically ignores system files (.DS_Store, Thumbs.db, desktop.ini) and temporary files (.tmp, .temp, .swp) to prevent error folder clutter

## Development Notes

### Testing Strategy
The project uses a comprehensive multi-tier testing approach:

- **Unit tests**: Component isolation with mocks (`tests/test_*.py`)
- **Integration tests**: Real component interaction (`tests/test_*_integration.py`)
- **RAG Integration**: End-to-end document processing pipeline (`tests/test_rag_integration_comprehensive/`)
- **Performance/stress tests**: High-volume and memory validation with various file sizes
- **Regression tests**: Ensure existing functionality remains unbroken after RAG integration

### Implementation Architecture Decisions

**Modular Document Processing**:
- Abstract `DocumentProcessingInterface` enables pluggable processors beyond RAG
- RAG integration is completely optional via `ENABLE_DOCUMENT_PROCESSING=false`
- Graceful degradation when dependencies unavailable or initialization fails
- Full backward compatibility with original file processing behavior

**Error Resilience Strategy**:
- **Classification-based retry**: Exponential backoff for transient errors, immediate failure for permanent
- **Enhanced error logging**: Context-rich `.log` files with processor type, file metadata, processing statistics
- **Structure preservation**: Error logs maintain original directory hierarchy for easy navigation
- **Health monitoring**: 30-second component health checks with statistics reporting every 5 minutes

### Key Development Patterns

**Initialization Sequence**: 8-step startup with dependency validation, configuration loading, and component initialization

**Resource Management**: Context managers, cleanup handlers, and graceful shutdown with signal handling

**File System Safety**: Atomic operations, folder structure preservation, recursive empty folder cleanup

**Configuration-Driven**: All behavior controlled through validated environment variables with runtime dependency checks

## File Processing Filtering and Automatic System File Cleanup

The application includes intelligent file filtering with **automatic system file deletion** to prevent system files and temporary files from causing repeated processing attempts and cluttering the source folder.

### Automatically Deleted System Files

The application automatically deletes these system files when detected (no user action required):

**macOS System Files**:
- `.DS_Store` - Finder metadata files (automatically deleted)
- `.spotlightv100` - Spotlight index files (automatically deleted)
- `.fseventsd` - File system event files (automatically deleted)
- `.documentrevisions-v100` - Document revision files (automatically deleted)

**Windows System Files**:
- `Thumbs.db` - Thumbnail cache files (automatically deleted)
- `desktop.ini` - Folder customization files (automatically deleted)

**Temporary Files**:
- Files ending with `.tmp`, `.temp` - Generic temporary files (automatically deleted)
- Files ending with `.swp` - Vim swap files (automatically deleted)

### System Files Ignored (Not Deleted)

These system files are ignored but not deleted for safety:
- `.trash`, `$recycle.bin` - System trash directories
- `pagefile.sys`, `hiberfil.sys` - Windows system files
- Files ending with `.lock` - Lock files (may be in use by other processes)

### Hidden Files Behavior

- **Hidden files starting with `.`**: Most are ignored (not processed)
- **Hidden document files**: Files like `.important.txt`, `.document.pdf` are processed due to their document extensions
- **Office temporary files**: Files starting with `~$` (like `~$document.docx`) are processed as they may be legitimate user files

### Regular Document Processing

These files are processed normally:
- **Document files**: PDF, DOC, DOCX, TXT, MD, RTF, MHT, etc.
- **Office files**: Word, Excel, PowerPoint documents and their OpenDocument equivalents
- **All other files**: Any file not identified as a system file or temporary file

### Benefits of Automatic Deletion

🧹 **Prevents Repeated Processing**: System files like `.DS_Store` and `Thumbs.db` won't cause repeated polling cycles  
📝 **Cleaner Logs**: Reduces log noise from repeatedly detecting the same system files  
⚡ **Better Performance**: Eliminates unnecessary file operations and processing overhead  
🔧 **Maintenance-Free**: No manual cleanup required - system files are removed automatically

### Implementation

The automatic system file deletion is implemented at multiple levels:
- **FileProcessor**: `should_ignore_file()` and `should_delete_system_file()` methods
- **Event-based monitoring**: Automatic deletion in `file_monitor.py`
- **Polling-based monitoring**: Automatic deletion in `polling_file_monitor.py`  
- **Directory scanning**: Automatic deletion during recursive processing
- **Manual scan**: Automatic deletion during existing file detection

All deletion attempts are logged for transparency, and the system gracefully handles deletion failures (continues processing normally).

This ensures consistent system file cleanup across all monitoring modes (auto, events, polling) and both Docker and native environments.