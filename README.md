# Folder File Processor

A Python application that monitors a configurable source folder for new files, processes them, and moves them to appropriate destination folders based on processing results. The application uses file system events for real-time monitoring and maintains folder structure preservation during file operations.

## Features

- **Real-time File Monitoring**: Uses file system events to detect new files immediately
- **Configurable Folders**: Source, saved, and error folders configurable via environment variables
- **Folder Structure Preservation**: Maintains original directory structure when moving files
- **Automatic Folder Cleanup**: Removes empty folders after successful file processing
- **Comprehensive Error Handling**: Graceful error handling with detailed logging
- **Retry Logic**: Automatic retry for transient file system errors
- **Detailed Logging**: Both console and file logging with configurable levels
- **Graceful Shutdown**: Proper cleanup and shutdown handling

## Requirements

- **Python**: 3.12 or higher
- **Operating System**: Cross-platform (Windows, macOS, Linux)
- **Dependencies**: See `pyproject.toml` for complete list

### Core Dependencies

- `watchdog==3.0.0` - Cross-platform file system event monitoring
- `python-dotenv==1.0.0` - Environment variable management from .env files

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
# Source folder to monitor for new files
SOURCE_FOLDER=/path/to/your/source/folder

# Destination folder for successfully processed files
SAVED_FOLDER=/path/to/your/saved/folder

# Destination folder for files that failed processing
ERROR_FOLDER=/path/to/your/error/folder
```

**Important Notes:**
- Use absolute paths for all folder configurations
- Ensure all specified folders exist or the application will create them
- The application user must have read/write permissions for all folders

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
3. Start monitoring the source folder
4. Process files as they are detected
5. Continue running until stopped with Ctrl+C

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

### Stopping the Application

Press `Ctrl+C` to gracefully stop the application. The system will:
1. Stop file monitoring
2. Complete any ongoing file operations
3. Clean up resources
4. Exit with appropriate status code

## Testing

### Running Tests

Run the complete test suite:

```bash
# Using uv (recommended):
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/test_file_processor.py

# Run with coverage report
uv run pytest --cov=src --cov-report=html

# Alternative (if virtual environment is activated):
pytest
pytest -v
pytest tests/test_file_processor.py
pytest --cov=src --cov-report=html
```

### Expected Test Output

```
================================ test session starts ================================
platform darwin -- Python 3.12.0, pytest-8.0.0, pluggy-1.3.0
rootdir: /path/to/folder-file-processor
plugins: cov-6.2.1
collected 45 items

tests/test_app_integration.py .................... [ 44%]
tests/test_config_manager.py .......... [ 66%]
tests/test_error_handler.py ........ [ 84%]
tests/test_file_manager.py .......... [ 95%]
tests/test_file_monitor.py .... [100%]

================================ 45 passed in 2.34s ================================
```

### Coverage Report

Generate HTML coverage report:

```bash
# Using uv:
uv run pytest --cov=src --cov-report=html

# Or with activated virtual environment:
pytest --cov=src --cov-report=html
```

Open `htmlcov/index.html` in your browser to view detailed coverage information.

### Test Categories

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test complete application workflows
- **Error Scenario Tests**: Test error handling and recovery mechanisms
- **Configuration Tests**: Test environment variable handling and validation

## Project Structure

```
folder-file-processor/
├── .env.example              # Example environment configuration
├── .gitignore               # Git ignore patterns
├── LICENSE                  # Project license
├── README.md               # This documentation
├── main.py                 # Application entry point
├── pyproject.toml          # Project configuration and dependencies
├── uv.lock                 # Dependency lock file
├── logs/                   # Application log files
│   └── application.log     # Main application log
├── src/                    # Source code
│   ├── __init__.py
│   ├── app.py              # Main application orchestrator
│   ├── config/             # Configuration management
│   │   ├── __init__.py
│   │   └── config_manager.py
│   ├── core/               # Core business logic
│   │   ├── __init__.py
│   │   ├── file_manager.py    # File operations
│   │   ├── file_monitor.py    # File system monitoring
│   │   └── file_processor.py  # File processing logic
│   └── services/           # Supporting services
│       ├── __init__.py
│       ├── error_handler.py   # Error handling and logging
│       └── logger_service.py  # Centralized logging
└── tests/                  # Test suite
    ├── __init__.py
    ├── test_app_integration.py
    ├── test_config_manager.py
    ├── test_error_handler.py
    ├── test_file_manager.py
    ├── test_file_monitor.py
    ├── test_file_processor.py
    └── test_logger_service.py
```

## Component Descriptions

### Core Components

- **ConfigManager** (`src/config/config_manager.py`): Handles environment variable loading and validation
- **FileMonitor** (`src/core/file_monitor.py`): Monitors file system events using the watchdog library
- **FileProcessor** (`src/core/file_processor.py`): Contains core business logic for file processing
- **FileManager** (`src/core/file_manager.py`): Handles file operations with folder structure preservation
- **ErrorHandler** (`src/services/error_handler.py`): Creates error log files and manages error reporting
- **LoggerService** (`src/services/logger_service.py`): Provides centralized logging functionality

### Main Application

- **FolderFileProcessorApp** (`src/app.py`): Main orchestrator that coordinates all components
- **main.py**: Application entry point with command-line interface

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