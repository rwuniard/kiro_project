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