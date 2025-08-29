# Folder File Processor

A Python application that monitors a configurable source folder for new files, processes them, and moves them to appropriate destination folders based on processing results. The application uses file system events for real-time monitoring and maintains folder structure preservation during file operations.

## Features

- **Real-time File Monitoring**: Uses file system events to detect new files immediately
- **Existing Files Processing**: Automatically processes files already present in source folder on startup
- **Configurable Folders**: Source, saved, and error folders configurable via environment variables
- **Folder Structure Preservation**: Maintains original directory structure when moving files
- **Automatic Folder Cleanup**: Removes empty folders after successful file processing
- **Comprehensive Error Handling**: Graceful error handling with detailed logging
- **Intelligent Retry Logic**: Exponential backoff retry for transient errors including API timeouts, network issues, and file system errors
- **Detailed Logging**: Both console and file logging with configurable levels
- **Graceful Shutdown**: Proper cleanup and shutdown handling

## Requirements

- **Python**: 3.12 or higher
- **Operating System**: Cross-platform (Windows, macOS, Linux)
- **Dependencies**: See `pyproject.toml` for complete list

### Core Dependencies

- `watchdog==3.0.0` - Cross-platform file system event monitoring
- `python-dotenv==1.0.0` - Environment variable management from .env files

### Document Processing Dependencies (Optional)

For advanced document processing with RAG (Retrieval Augmented Generation) capabilities and OCR support:

#### Supported Document Types

The document processing system supports the following file formats:

- **PDF Documents** (`.pdf`) - With full OCR support for image-based PDFs
- **Microsoft Word Documents** - Both legacy (`.doc`) and modern (`.docx`) formats using UnstructuredLoader
- **Rich Text Format** (`.rtf`) - RTF documents with smart detection for RTF content in `.doc` files
- **Text Files** (`.txt`, `.md`, `.text`) - Plain text and Markdown documents
- **Web Archive Files** (`.mht`, `.mhtml`) - MHTML web archive documents

#### System Requirements

- **Tesseract OCR Engine** - Required for OCR functionality on image-based PDFs
  - **macOS**: `brew install tesseract`
  - **Ubuntu/Debian**: `sudo apt-get install tesseract-ocr`
  - **Windows**: Download from [GitHub releases](https://github.com/UB-Mannheim/tesseract/wiki) or use `choco install tesseract`

- **Pandoc** - Required for RTF document processing
  - **macOS**: `brew install pandoc`
  - **Ubuntu/Debian**: `sudo apt-get install pandoc`
  - **Windows**: Download from [pandoc.org](https://pandoc.org/installing.html) or use `choco install pandoc`

- **LibreOffice** - Required for legacy Microsoft Word (`.doc`) file processing
  - **macOS**: `brew install --cask libreoffice`
  - **Ubuntu/Debian**: `sudo apt-get install libreoffice`
  - **Windows**: Download from [LibreOffice.org](https://www.libreoffice.org/download/download-libreoffice/) or use `choco install libreoffice`

- **libmagic** (Optional) - Enhanced file type detection
  - **macOS**: `brew install libmagic`
  - **Ubuntu/Debian**: `sudo apt-get install libmagic1`
  - **Windows**: Not readily available, but file processing continues without it

**Python Dependencies** (installed automatically):
- `pytesseract>=0.3.13` - Python wrapper for Tesseract OCR
- `PyMuPDF>=1.23.0` - PDF processing with OCR support
- `unstructured>=0.18.14` - Document parsing with LibreOffice backend
- `python-magic>=0.4.27` - File type detection using libmagic

**Notes**: 
- Without Tesseract: PDFs process but no OCR on image-based content
- Without Pandoc: RTF files will fail to process
- Without LibreOffice: Legacy .doc files will fail (modern .docx still works)
- Without libmagic: File type detection relies on extensions, may show warnings

### Development Dependencies

- `pytest>=8.0.0` - Unit testing framework
- `pytest-cov>=6.2.1` - Code coverage reporting

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd folder-file-processor
```

### 2. Install Dependencies (Recommended: uv)

Using `uv` (automatically creates virtual environment and installs dependencies):

```bash
# Install uv if not already installed
# On macOS/Linux:
curl -LsSf https://astral.sh/uv/install.sh | sh
# On Windows:
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Install all dependencies (creates .venv automatically)
uv sync

# Install with development dependencies
uv sync --group dev
```

### Alternative: Manual Virtual Environment Setup

If you prefer to use pip or don't have `uv` installed:

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -e .
# Or with development dependencies:
pip install -e .[dev]
```

### 3. Environment Configuration

Create a `.env` file in the project root directory:

```bash
cp .env.example .env
```

Edit the `.env` file with your specific folder paths:

```env
# Required - Basic file processing
SOURCE_FOLDER=/path/to/your/source/folder
SAVED_FOLDER=/path/to/your/saved/folder
ERROR_FOLDER=/path/to/your/error/folder

# Optional - Advanced Document Processing with RAG
ENABLE_DOCUMENT_PROCESSING=true
DOCUMENT_PROCESSOR_TYPE=rag_store
MODEL_VENDOR=openai  # or google

# Required if using document processing
OPENAI_API_KEY=your_openai_api_key_here  # if MODEL_VENDOR=openai
GOOGLE_API_KEY=your_google_api_key_here  # if MODEL_VENDOR=google

# ChromaDB Configuration (choose embedded or client_server mode)
CHROMA_CLIENT_MODE=embedded  # or client_server
# For embedded mode:
CHROMA_DB_PATH=./data/chroma_db_openai
# For client_server mode:
CHROMA_SERVER_HOST=localhost
CHROMA_SERVER_PORT=8000
# Optional - Custom collection name for organizing documents
CHROMA_COLLECTION_NAME=my_documents

# Optional - OCR Investigation (for debugging OCR issues)
# OCR_INVESTIGATE=false
# OCR_INVESTIGATE_DIR=./ocr_debug
```

**Important Notes:**
- Use absolute paths for all folder configurations
- Ensure all specified folders exist or the application will create them
- The application user must have read/write permissions for all folders
- **Document Processing**: Requires API keys (OpenAI or Google) and optionally Tesseract OCR for image-based PDFs
- **OCR Investigation**: When enabled, saves OCR debug files to specified directory for troubleshooting
- **ChromaDB Modes**: Choose between embedded (file-based) or client_server (Docker-based) modes

### ChromaDB Server Setup (Optional)

For better performance and data persistence across application restarts, you can run ChromaDB as a server using Docker. The project includes convenient scripts for this.

#### Starting ChromaDB Server

```bash
# Navigate to project root and start the ChromaDB server
./setup_chromadb/chromadb-server.sh start

# Check server health
./setup_chromadb/chromadb-server.sh health

# View server logs
./setup_chromadb/chromadb-server.sh logs
```

#### Configuration for Client-Server Mode

Update your `.env` file to use client-server mode:

```env
CHROMA_CLIENT_MODE=client_server
CHROMA_SERVER_HOST=localhost
CHROMA_SERVER_PORT=8000
```

#### Server Management Commands

```bash
./setup_chromadb/chromadb-server.sh start      # Start server
./setup_chromadb/chromadb-server.sh stop       # Stop server
./setup_chromadb/chromadb-server.sh restart    # Restart server
./setup_chromadb/chromadb-server.sh status     # Show status
./setup_chromadb/chromadb-server.sh health     # Check health
./setup_chromadb/chromadb-server.sh logs       # View logs
./setup_chromadb/chromadb-server.sh clean      # Clean all data (DANGEROUS)
```

**Benefits of Client-Server Mode:**
- **Persistent Data**: Data survives application restarts
- **Better Performance**: Dedicated ChromaDB server process  
- **Concurrent Access**: Multiple applications can use the same ChromaDB instance
- **Real-time Updates**: Changes are immediately visible across all clients
- **Server Management**: Easy start/stop/restart of the database server

## Usage

### Running the Application

```bash
# If using uv:
uv run python main.py

# Or activate virtual environment first:
# On Windows: .venv\Scripts\activate
# On macOS/Linux: source .venv/bin/activate
python main.py
```

The application will:
1. Load configuration from `.env` file
2. Initialize all components (logging, file manager, processor, monitor)
3. **Process any existing files** already present in the source folder
4. Start monitoring the source folder for new files
5. Process files as they are detected
6. Continue running until stopped with Ctrl+C

### Application Output

When running, you'll see output similar to:

```
Folder File Processor starting...
Loading configuration...
Configuration loaded successfully:
  Source folder: /path/to/source
  Saved folder: /path/to/saved
  Error folder: /path/to/error
Setting up logging...
Initializing error handler...
Initializing file manager...
Initializing file processor...
Initializing file monitor...
Application initialization complete.
Starting file system monitoring...
Performing initial scan for existing files
Processing existing file: document.txt
Processing existing file: reports/report.pdf
Initial scan processed 2 existing files
Monitoring folder: /path/to/source
Application is running. Press Ctrl+C to stop.
```

### Processing Output Examples

When files are processed, you'll see console output and log entries:

**Successful Processing with Folder Cleanup:**
```
Processed file: project1/data/document.txt
2025-01-15 10:30:15 - INFO - Successfully processed file: project1/data/document.txt
2025-01-15 10:30:15 - INFO - Cleaned up empty folder: project1/data
2025-01-15 10:30:15 - INFO - Cleaned up empty folder: project1
```

**Processing with Cleanup Warning:**
```
Processed file: shared/temp/file.txt
2025-01-15 10:30:20 - INFO - Successfully processed file: shared/temp/file.txt
2025-01-15 10:30:20 - WARNING - Could not remove empty folder /path/to/source/shared/temp: Permission denied
```

### File Processing Behavior

- **Successful Processing**: Files are moved to the `SAVED_FOLDER` with preserved directory structure
- **Failed Processing**: Files are moved to the `ERROR_FOLDER` with an accompanying `.log` file containing error details
- **Directory Structure**: Original folder hierarchy is maintained in both saved and error destinations
- **Automatic Cleanup**: Empty folders are automatically removed after successful file processing

#### Enhanced Error Logging

When files fail to process, the application creates detailed error log files with enhanced naming conventions:

**Error Log Filename Format**: `[original_filename].[original_extension].log`

**Examples of Error Log Naming:**
- `document.pdf` → `document.pdf.log`
- `data.csv` → `data.csv.log`
- `backup.tar.gz` → `backup.tar.gz.log`
- `report.xlsx` → `report.xlsx.log`
- `config.json` → `config.json.log`
- `script.py` → `script.py.log`
- `archive.zip` → `archive.zip.log`

**Error Log Placement:**
Error log files are placed in the same folder as the failed file within the error folder structure, maintaining the original directory hierarchy:

```
Error Folder Structure Example:
error/
├── project1/
│   ├── data/
│   │   ├── corrupted_file.txt      # Failed file
│   │   └── corrupted_file.txt.log  # Error log
│   └── reports/
│       ├── broken_report.pdf
│       └── broken_report.pdf.log
└── project2/
    ├── config.json
    └── config.json.log
```

**Error Log Content Format:**
```
Timestamp: 2025-01-23 10:30:45
File: /source/project1/data/corrupted_file.txt
Error: Permission denied when reading file
Stack Trace: [if applicable]
Additional Context: File size: 1024 bytes, Last modified: 2025-01-23 10:29:12
```

This enhanced error logging system ensures that:
- Each failed file has a uniquely identifiable error log
- Error logs are co-located with their corresponding failed files
- The original folder structure is preserved for easy navigation
- Detailed error information is captured for effective troubleshooting

#### Empty Folder Handling

The application automatically detects and handles completely empty folders found in the source directory:

**Empty Folder Detection Criteria:**
A folder is considered "completely empty" when it contains:
- **No files** (no regular files of any type)
- **No subfolders** (no subdirectories, empty or otherwise)

**Important**: Folders that contain empty subfolders are NOT considered completely empty and will not be moved.

**Empty Folder Processing Behavior:**
1. **Detection**: During monitoring, completely empty folders are identified
2. **Movement**: Empty folders are moved to the error folder with preserved directory structure
3. **Logging**: An `empty_folder.log` file is created inside the moved folder
4. **Integration**: Empty folder handling runs alongside regular file processing without interference

**Empty Folder Log Format:**
**Filename**: `empty_folder.log`
**Content Example**:
```
Timestamp: 2025-01-23 10:30:45
Folder: /source/project1/empty_directory
Reason: Completely empty folder detected (no files, no subfolders) and moved to error folder
Original Path: /source/project1/empty_directory
Moved To: /error/project1/empty_directory
```

**Empty Folder Structure Example:**
```
Before Processing:
source/
├── project1/
│   ├── data/
│   │   └── file.txt
│   ├── completely_empty/     # Will be moved (no files, no subfolders)
│   └── has_empty_subfolder/  # Will NOT be moved (contains subfolder)
│       └── empty_sub/
└── project2/
    └── another_empty/        # Will be moved (no files, no subfolders)

After Processing:
source/
├── project1/
│   └── has_empty_subfolder/  # Remains (not completely empty)
│       └── empty_sub/
└── # project2/ removed by cleanup (became empty after processing)

error/
├── project1/
│   └── completely_empty/
│       └── empty_folder.log
└── project2/
    └── another_empty/
        └empty_folder.log

saved/
└── project1/
    └── data/
        └── file.txt
```

**Integration with Regular Processing:**
- Empty folder detection runs during the initial source folder scan
- Does not interfere with file processing operations
- Operates independently of the automatic folder cleanup feature
- Logged at INFO level in the application log: `"Moved empty folder to error: /path/to/folder"`

#### Folder Cleanup Details

The application automatically cleans up empty folders after successfully processing files:

- **Empty Folder Detection**: Checks if folders contain no files or only empty subfolders
- **Recursive Cleanup**: Removes empty parent folders up to the source root
- **Safety Measures**: Never removes the source root folder, even if empty
- **Error Handling**: Gracefully handles permission errors during folder removal
- **Logging**: All folder cleanup operations are logged at INFO level

**Example Cleanup Behavior:**
```
Source structure before processing:
source/
├── project1/
│   ├── data/
│   │   └── file.txt
│   └── empty_folder/
└── project2/
    └── archive/
        └── old_file.txt

After processing file.txt and old_file.txt:
source/
├── project1/
│   └── empty_folder/  # Not removed (was already empty)
└── # project2/ removed (became empty after processing)
```

#### Race Condition Prevention

**Problem Resolved**: Previously, folders could be incorrectly flagged as "empty" when they became temporarily empty due to file processing, leading to spurious `empty_folder.log` files appearing alongside actual processed files.

**Solution Implemented**: The application now uses intelligent empty folder detection that prevents race conditions:

**Enhanced Empty Folder Logic:**
1. **Physical Emptiness Check**: First verifies the folder is actually empty
2. **Processing History Check**: Examines both saved and error folders for files that were previously processed from this location
3. **Smart Decision Making**: Only processes folders as "originally empty" if no processed files exist at equivalent paths

**Race Condition Scenarios Handled:**
- **Successful Processing**: If files were moved to the saved folder, the now-empty source folder is NOT treated as originally empty
- **Failed Processing**: If files were moved to the error folder, the now-empty source folder is NOT treated as originally empty  
- **Mixed Processing**: Handles combinations of successful and failed files from the same folder
- **Edge Cases**: Correctly ignores existing `empty_folder.log` files when making decisions

**Before Fix (Race Condition):**
```
1. Citation.doc fails processing → moved to error/Federal Law/TCPA/1992 FCC Order/
2. Source folder Federal Law/TCPA/1992 FCC Order/ becomes empty
3. Empty folder scanner detects "empty" folder → moves it to error folder
4. Result: Both Citation.doc AND empty_folder.log in same error location ❌
```

**After Fix (Race Condition Prevented):**
```
1. Citation.doc fails processing → moved to error/Federal Law/TCPA/1992 FCC Order/
2. Source folder Federal Law/TCPA/1992 FCC Order/ becomes empty  
3. Empty folder scanner detects empty folder BUT finds Citation.doc in error location
4. Result: Folder not processed as empty, no spurious empty_folder.log created ✅
```

**Technical Implementation:**
- `should_process_as_empty_folder()` method replaces simple emptiness checks
- Checks both `SAVED_FOLDER` and `ERROR_FOLDER` for processed files
- Preserves all existing functionality for truly empty folders
- Zero performance impact on normal file processing

### Stopping the Application

Press `Ctrl+C` to gracefully stop the application. The system will:
1. Stop file monitoring
2. Complete any ongoing file operations
3. Clean up resources
4. Exit with appropriate status code

## Testing

The project includes a comprehensive test suite organized by component structure with over 450 unit and integration tests.

### Test Organization

Tests are organized to mirror the source code structure:

```
tests/
├── test_config/              # Tests for src/config/
│   ├── test_config_manager.py
│   ├── test_document_processing_config.py
│   └── test_configuration_validation_error_scenarios.py
├── test_core/                # Tests for src/core/
│   ├── test_document_processing.py
│   ├── test_file_manager.py
│   ├── test_file_monitor.py
│   ├── test_file_processor.py
│   ├── test_rag_store_processor.py
│   └── test_document_processing_workflow.py
├── test_services/            # Tests for src/services/
│   ├── test_error_handler.py
│   └── test_logger_service.py
├── test_rag_store/           # Tests for src/rag_store/
│   ├── test_document_processor.py
│   ├── test_pdf_processor.py
│   ├── test_word_processor.py
│   ├── test_rtf_processor.py
│   └── [... other RAG store component tests]
└── test_rag_integration_comprehensive/  # Integration tests
    ├── test_comprehensive_integration.py
    ├── test_end_to_end_workflow.py
    └── test_performance_stress.py
```

### Running Tests

Run the complete test suite:

```bash
# Using uv with convenient scripts (recommended):
uv run test                    # Run all tests
uv run test-cov               # Run all tests with HTML coverage report

# Using uv with full pytest commands:
uv run pytest                # Run all tests
uv run pytest -v             # Run with verbose output

# Run tests by category:
uv run pytest tests/test_config/           # Configuration tests only
uv run pytest tests/test_core/             # Core functionality tests
uv run pytest tests/test_services/         # Service layer tests
uv run pytest tests/test_rag_store/        # RAG store component tests

# Run specific test files:
uv run pytest tests/test_core/test_file_processor.py  # Specific test file
uv run pytest tests/test_config/test_document_processing_config.py  # Config tests

# Run with coverage report:
uv run pytest --cov=src --cov-report=html   # Generate HTML coverage report

# Alternative (if virtual environment is activated):
pytest
pytest -v
pytest tests/test_core/test_file_processor.py
pytest --cov=src --cov-report=html
```

The `uv run test-cov` command will generate an HTML coverage report in the `htmlcov/` directory. Open `htmlcov/index.html` in your browser to view detailed coverage information.

### Expected Test Output

```
================================ test session starts ================================
platform darwin -- Python 3.12.8, pytest-8.4.1, pluggy-1.6.0
rootdir: /path/to/kiro-project
plugins: cov-6.2.1
collected 451 items

tests/test_config/test_config_manager.py ................. [  3%]
tests/test_config/test_document_processing_config.py ................... [ 10%]
tests/test_core/test_file_manager.py ............................. [ 24%]
tests/test_core/test_file_processor.py ............................ [ 40%]
tests/test_core/test_rag_store_processor.py ................... [ 55%]
tests/test_services/test_logger_service.py ................. [ 65%]
tests/test_rag_store/test_document_processor.py ............... [ 80%]
[... additional test files ...]

================================ 451 passed in 50.89s ===============================
```

### Coverage Report

Generate HTML coverage report:

```bash
# Using convenient script (recommended):
uv run test-cov

# Or using full pytest command:
uv run pytest --cov=src --cov-report=html

# Alternative (if virtual environment is activated):
pytest --cov=src --cov-report=html
```

The coverage report will be generated in the `htmlcov/` directory. Open `htmlcov/index.html` in your browser to view detailed coverage information including:
- Line-by-line coverage visualization
- Coverage percentages by module
- Missing coverage highlights
- Branch coverage analysis

### Test Categories

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test complete application workflows
- **Error Scenario Tests**: Test error handling and recovery mechanisms
- **Configuration Tests**: Test environment variable handling and validation

## Project Structure

```
kiro-project/
├── .env.example              # Example environment configuration
├── .gitignore               # Git ignore patterns
├── CLAUDE.md                # Claude Code development instructions
├── LICENSE                  # Project license
├── README.md               # This documentation
├── main.py                 # Application entry point
├── pyproject.toml          # Project configuration and dependencies
├── uv.lock                 # Dependency lock file
├── logs/                   # Application log files
│   └── application.log     # Main application log
├── setup_chromadb/         # ChromaDB server setup
│   ├── docker-compose.yml  # Docker configuration for ChromaDB server
│   └── chromadb-server.sh  # Server management script
├── src/                    # Source code
│   ├── __init__.py
│   ├── app.py              # Main application orchestrator
│   ├── config/             # Configuration management
│   │   ├── __init__.py
│   │   └── config_manager.py  # Environment config with ChromaDB support
│   ├── core/               # Core business logic
│   │   ├── __init__.py
│   │   ├── document_processing.py     # Document processing interface
│   │   ├── file_manager.py           # File operations with path mapping
│   │   ├── file_monitor.py           # File system monitoring
│   │   ├── file_processor.py         # File processing orchestration
│   │   └── rag_store_processor.py    # RAG document processing implementation
│   ├── rag_store/          # RAG document processing components
│   │   ├── __init__.py
│   │   ├── cli.py          # Command-line interface
│   │   ├── document_processor.py     # Document processor registry
│   │   ├── file_detection.py        # Smart file type detection
│   │   ├── logging_config.py        # RAG-specific logging
│   │   ├── pdf_processor.py         # PDF processing with OCR
│   │   ├── rtf_processor.py         # RTF document processing
│   │   ├── store_embeddings.py      # ChromaDB integration with client-server support
│   │   ├── text_processor.py        # Text and Markdown processing
│   │   ├── word_processor.py        # Word document processing (.doc/.docx)
│   │   └── mht_processor.py         # MHTML web archive processing
│   └── services/           # Supporting services
│       ├── __init__.py
│       ├── error_handler.py          # Enhanced error handling and logging
│       └── logger_service.py         # Centralized logging service
└── tests/                  # Comprehensive test suite (450+ tests)
    ├── __init__.py
    ├── test_app_integration.py       # Application-level integration tests
    ├── test_rag_integration.py       # RAG integration tests
    ├── test_config/                  # Configuration tests
    │   ├── __init__.py
    │   ├── test_config_manager.py
    │   ├── test_document_processing_config.py
    │   └── test_configuration_validation_error_scenarios.py
    ├── test_core/                    # Core functionality tests
    │   ├── __init__.py
    │   ├── test_document_processing.py
    │   ├── test_document_processing_error_handling.py
    │   ├── test_document_processing_workflow.py
    │   ├── test_file_manager.py
    │   ├── test_file_monitor.py
    │   ├── test_file_processor.py
    │   └── test_rag_store_processor.py
    ├── test_services/                # Service layer tests
    │   ├── __init__.py
    │   ├── test_error_handler.py
    │   └── test_logger_service.py
    ├── test_rag_store/               # RAG component tests
    │   ├── __init__.py
    │   ├── test_cli.py
    │   ├── test_document_processor.py
    │   ├── test_file_detection.py
    │   ├── test_pdf_processor.py
    │   ├── test_rtf_processor.py
    │   ├── test_store_embeddings.py
    │   ├── test_text_processor.py
    │   ├── test_word_processor.py
    │   └── test_mht_processor.py
    └── test_rag_integration_comprehensive/  # Comprehensive integration tests
        ├── __init__.py
        ├── base_test_classes.py
        ├── test_comprehensive_integration.py
        ├── test_end_to_end_workflow.py
        ├── test_performance_stress.py
        └── test_regression.py
```

## Component Descriptions

### Configuration Layer

- **ConfigManager** (`src/config/config_manager.py`): Comprehensive environment variable loading and validation with ChromaDB client-server support
- **DocumentProcessingConfig**: Advanced document processing configuration with API key validation, ChromaDB mode selection, and collection name management

### Core Business Logic

- **FileMonitor** (`src/core/file_monitor.py`): Cross-platform file system event monitoring using the watchdog library
- **FileProcessor** (`src/core/file_processor.py`): Orchestrates file processing with intelligent retry logic and error classification
- **FileManager** (`src/core/file_manager.py`): Advanced file operations with folder structure preservation and destination path mapping
- **DocumentProcessingInterface** (`src/core/document_processing.py`): Abstract interface for pluggable document processing systems
- **RAGStoreProcessor** (`src/core/rag_store_processor.py`): Concrete RAG implementation with ChromaDB integration and metadata path correction

### RAG Document Processing

- **ProcessorRegistry** (`src/rag_store/document_processor.py`): Multi-format document processor factory with smart file detection
- **PDF Processor** (`src/rag_store/pdf_processor.py`): PDF processing with OCR support for image-based documents
- **Word Processor** (`src/rag_store/word_processor.py`): Microsoft Word document processing (.doc/.docx) with legacy format support
- **RTF Processor** (`src/rag_store/rtf_processor.py`): Rich Text Format processing with smart content detection
- **Text Processor** (`src/rag_store/text_processor.py`): Plain text and Markdown document processing
- **MHT Processor** (`src/rag_store/mht_processor.py`): MHTML web archive processing
- **ChromaDB Integration** (`src/rag_store/store_embeddings.py`): Vector storage with embedded and client-server mode support

### Service Layer

- **ErrorHandler** (`src/services/error_handler.py`): Enhanced error log creation with filename preservation and detailed context
- **LoggerService** (`src/services/logger_service.py`): Centralized structured logging with file and console output

### Application Orchestration

- **FolderFileProcessorApp** (`src/app.py`): Main orchestrator with 8-step initialization, health monitoring, and graceful shutdown
- **main.py**: Application entry point with command-line interface and signal handling

## Troubleshooting

### Common Setup Issues

#### 1. Python Version Error
```
ERROR: This package requires Python >=3.12
```
**Solution**: Ensure you're using Python 3.12 or higher:
```bash
python --version
# If needed, install Python 3.12+ or use pyenv/conda
```

#### 2. Missing .env File
```
ERROR: Configuration validation failed: Missing required environment variables
```
**Solution**: Create `.env` file from example:
```bash
cp .env.example .env
# Edit .env with your actual folder paths
```

#### 3. Permission Denied Errors
```
ERROR: Permission denied when accessing folder: /path/to/folder
```
**Solution**: Ensure the application has read/write permissions:
```bash
# Check permissions
ls -la /path/to/folder
# Fix permissions if needed
chmod 755 /path/to/folder
```

#### 4. Folder Not Found Errors
```
ERROR: Source folder does not exist: /path/to/source
```
**Solution**: Create the required folders:
```bash
mkdir -p /path/to/source /path/to/saved /path/to/error
```

#### 5. OCR/Tesseract Installation Issues
```
ERROR: TesseractNotFoundError: tesseract is not installed or it's not in your PATH
```
**Solution**: Install Tesseract OCR engine:
```bash
# macOS
brew install tesseract

# Ubuntu/Debian
sudo apt-get update
sudo apt-get install tesseract-ocr

# Windows (using Chocolatey)
choco install tesseract

# Or download Windows installer from:
# https://github.com/UB-Mannheim/tesseract/wiki
```

**Verify Installation**:
```bash
# Check if Tesseract is properly installed
tesseract --version

# Should output something like: tesseract 5.x.x
```

#### 6. Document Processing Configuration Issues
```
ERROR: Document processor validation failed
```
**Common solutions**:
- **Missing API Keys**: Ensure `OPENAI_API_KEY` or `GOOGLE_API_KEY` is set in `.env`
- **Invalid Model Vendor**: Set `MODEL_VENDOR=openai` or `MODEL_VENDOR=google`
- **ChromaDB Path Issues**: Ensure `CHROMA_DB_PATH` directory is writable
- **OCR Dependencies**: Install pytesseract and Pillow: `pip install pytesseract Pillow`

### Common Runtime Issues

#### 1. File Processing Failures
- **Check logs**: Look in `logs/application.log` for detailed error information
- **Check error folder**: Failed files are moved to `ERROR_FOLDER` with `.log` files containing details
- **Verify permissions**: Ensure files are readable and folders are writable

#### 2. Monitoring Not Working
- **Check source folder**: Ensure the source folder exists and is accessible
- **Check file system events**: Some network drives may not support file system events
- **Restart application**: Stop with Ctrl+C and restart

#### 3. High Memory Usage
- **Large files**: The application loads files into memory for processing
- **Many files**: Processing many files simultaneously can increase memory usage
- **Solution**: Monitor file sizes and consider implementing streaming for large files

#### 4. Folder Cleanup Issues
- **Permission Errors**: If folder cleanup fails due to permissions, check folder ownership and access rights
- **Folders Not Removed**: Only empty folders are removed; folders with hidden files or system files will remain
- **Network Drives**: Folder cleanup may behave differently on network-mounted drives
- **Check Logs**: Folder cleanup operations and any errors are logged at INFO/WARNING levels

**Folder Cleanup Log Messages:**
```
INFO - Cleaned up empty folder: project1/data
WARNING - Could not remove empty folder /path/to/folder: Permission denied
```

#### 5. Empty Folder Handling Issues

**Empty Folders Not Being Moved:**
- **Check Criteria**: Ensure folders are completely empty (no files AND no subfolders)
- **Hidden Files**: Folders with hidden files (like `.DS_Store` on macOS) are not considered empty
- **System Files**: Folders containing system files or metadata will not be moved
- **Permissions**: Verify the application has read access to check folder contents

**Empty Folder Movement Failures:**
```
ERROR: Failed to move empty folder: Permission denied
```
**Solutions:**
- Check folder permissions and ownership
- Ensure the error folder is writable
- Verify no processes are using the folder

**Missing empty_folder.log Files:**
- **Check Error Folder**: Log files are created inside the moved empty folders
- **Permission Issues**: Verify write permissions in the error folder
- **Check Application Logs**: Look for error messages about log file creation

**Empty Folder Detection Confusion:**
```
Expected empty folder to be moved but it wasn't:
folder/
├── subfolder/  # Even if empty, parent is not "completely empty"
```
**Understanding**: Only folders with absolutely no contents (no files, no subfolders) are moved.

**Empty Folder Log Messages:**
```
INFO - Moved empty folder to error: /source/project1/empty_dir
INFO - Created empty folder log: /error/project1/empty_dir/empty_folder.log
WARNING - Failed to move empty folder /source/folder: Permission denied
```

#### 6. OCR and Document Processing Issues

**OCR Not Working on Image-based PDFs:**
```
INFO - Page 1 has minimal text (0 chars), attempting enhanced extraction
WARNING - Page 1 has no text and OCR not available. Install pytesseract and Tesseract for image OCR
```
**Solutions**:
- Install Tesseract OCR engine (see installation instructions above)
- Install Python dependencies: `pip install pytesseract Pillow`
- Verify Tesseract is in your system PATH: `tesseract --version`

**OCR Investigation Mode:**
Enable OCR debugging to troubleshoot OCR issues:
```env
# In .env file
OCR_INVESTIGATE=true
OCR_INVESTIGATE_DIR=./ocr_debug
```
This creates debug files showing OCR extraction results for each page processed.

**Word Document Processing:**
```
INFO - Document processing started: WordProcessor for /path/to/document.doc
convert /path/to/document.doc as a Writer document -> /tmp/document.docx using filter: MS Word 2007 XML
```
- **Legacy .doc Support**: UnstructuredLoader automatically converts .doc files to .docx format for processing
- **Metadata Cleaning**: Complex metadata from UnstructuredLoader is filtered for ChromaDB compatibility
- **Both Formats**: Supports both .doc (Word 97-2003) and .docx (Word 2007+) formats seamlessly

**Retry Mechanism and Error Recovery:**
The application includes intelligent retry logic for transient errors, particularly API timeouts:

```
INFO - File processing failed on attempt 1 (transient error), retrying in 1.0s: Error embedding content: 504 Deadline Exceeded
INFO - File processing failed on attempt 2 (transient error), retrying in 2.0s: Error embedding content: 504 Deadline Exceeded
INFO - File processing completed successfully on attempt 3
```

**Retry Configuration:**
- **Max Attempts**: 3 retries per file
- **Exponential Backoff**: 1s → 2s → 4s → 8s delays (capped at 10s maximum)
- **Smart Classification**: Distinguishes between permanent errors (no retry) and transient errors (retry with backoff)
- **Automatic Retry**: Google API timeouts (504 Deadline Exceeded), network errors, rate limits, and temporary service issues

**Transient Errors (Will Retry):**
- API rate limits and quota exceeded
- Connection timeouts and network errors
- Google embedding API timeouts (504 Deadline Exceeded)
- ChromaDB temporary issues
- Service unavailable errors

**Permanent Errors (No Retry):**
- Unsupported file types
- Corrupted or malformed files
- Invalid document structure
- Authentication/API key issues

**Document Processing Performance Issues:**
- **Large PDFs**: OCR processing can be slow for large image-based PDFs  
- **API Timeouts**: Large documents may timeout during embedding generation (automatically retried up to 3 times)
- **Word Document Conversion**: Legacy .doc files require temporary conversion which may take extra time
- **High Memory Usage**: OCR operations use significant memory for image processing
- **Solutions**: 
  - Process files in smaller batches
  - Increase available system memory
  - Monitor `logs/application.log` for processing times and retry attempts
  - Large files may take up to ~3-4 minutes total with retries

**ChromaDB Connection Issues:**
```
ERROR: Could not initialize ChromaDB at path: ./data/chroma_db_openai
```
**Solutions**:
- Ensure `CHROMA_DB_PATH` directory exists and is writable
- Check disk space availability
- Verify no other processes are using the database

**ChromaDB Client-Server Mode Issues:**
```
ERROR: Failed to connect to ChromaDB server at localhost:8000
```
**Solutions**:
- Ensure ChromaDB server is running: `./setup_chromadb/chromadb-server.sh status`
- Start the server if stopped: `./setup_chromadb/chromadb-server.sh start`
- Check server health: `./setup_chromadb/chromadb-server.sh health`
- Verify `CHROMA_CLIENT_MODE=client_server` in `.env`
- Confirm correct host and port in `.env` file

**ChromaDB Collection Configuration:**
- **Collection Name**: Use `CHROMA_COLLECTION_NAME` to organize documents by project or category
- **Multiple Collections**: Different applications can use different collection names on the same server
- **Collection Persistence**: Collections in client-server mode survive application restarts
- **Collection Access**: Verify collection name matches between configuration and expectations

### Getting Help

1. **Check logs**: Always check `logs/application.log` for detailed error information
2. **Run tests**: Execute the test suite to verify system functionality
3. **Verify configuration**: Ensure `.env` file has correct paths and permissions
4. **Check dependencies**: Verify all required packages are installed

### Debug Mode

For additional debugging information, you can modify the logging level in the application:

```python
# In src/services/logger_service.py, change logging level to DEBUG
logging.basicConfig(level=logging.DEBUG)
```

This will provide more detailed information about file operations and system events.

## License

This project is licensed under the terms specified in the LICENSE file.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## Development

### Code Style

The project follows Python best practices:
- PEP 8 style guidelines
- Type hints where appropriate
- Comprehensive docstrings
- Modular architecture with clear separation of concerns

### Adding New Features

1. Update requirements in `requirements.md` if needed
2. Update design in `design.md` if architecture changes
3. Implement the feature with appropriate tests
4. Update documentation as needed

### Performance Considerations

- The application is designed for moderate file volumes
- For high-volume scenarios, consider implementing queue-based processing
- Memory usage scales with file sizes being processed
- File system event monitoring is efficient but may have platform-specific limitations