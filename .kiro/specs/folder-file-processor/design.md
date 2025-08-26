# Design Document

## Overview

The Folder File Processor is a Python application that monitors a configurable source directory for new files using file system events, processes them, and moves them to appropriate destination folders based on processing results. The application maintains folder structure preservation and provides comprehensive logging for both successful operations and error handling.

## Architecture

The application follows a modular architecture with clear separation of concerns:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   File Monitor  │───▶│  File Processor │───▶│  File Manager   │
│   (watchdog)    │    │   (business     │    │  (move/copy)    │
│                 │    │    logic)       │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Config        │    │   Logger        │    │   Error Handler │
│   Manager       │    │   Service       │    │   Service       │
│   (.env)        │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Components and Interfaces

### 1. Configuration Manager
**Purpose:** Handles environment variable loading and validation
**Interface:**
```python
class ConfigManager:
    def load_config() -> Dict[str, str]
    def validate_config(config: Dict[str, str]) -> bool
    def get_source_folder() -> str
    def get_saved_folder() -> str  
    def get_error_folder() -> str
```

### 2. File Monitor
**Purpose:** Monitors file system events using the `watchdog` library
**Interface:**
```python
class FileMonitor:
    def __init__(self, source_folder: str, processor: FileProcessor)
    def start_monitoring() -> None
    def stop_monitoring() -> None
    def on_created(self, event) -> None
```

### 3. File Processor
**Purpose:** Contains the core business logic for file processing
**Interface:**
```python
class FileProcessor:
    def __init__(self, config: Dict[str, str])
    def process_file(self, file_path: str) -> bool
    def _read_file_content(self, file_path: str) -> str
    def _perform_processing(self, content: str, file_path: str) -> None
```

### 4. File Manager
**Purpose:** Handles file operations (move, copy) with folder structure preservation and empty folder cleanup
**Interface:**
```python
class FileManager:
    def __init__(self, source_folder: str, saved_folder: str, error_folder: str)
    def move_to_saved(self, file_path: str) -> bool
    def move_to_error(self, file_path: str) -> bool
    def move_empty_folder_to_error(self, folder_path: str) -> bool
    def cleanup_empty_folders(self, file_path: str) -> None
    def _preserve_folder_structure(self, source_path: str, dest_base: str) -> str
    def _ensure_directory_exists(self, directory: str) -> None
    def _is_folder_empty(self, folder_path: str) -> bool
    def _remove_empty_folder_recursive(self, folder_path: str) -> None
```

### 5. Error Handler Service
**Purpose:** Creates error log files and manages error reporting
**Interface:**
```python
class ErrorHandler:
    def create_error_log(self, file_path: str, error_message: str) -> None
    def create_empty_folder_log(self, folder_path: str) -> None
    def _get_error_log_path(self, file_path: str) -> str
    def _write_error_log(self, log_path: str, error_info: Dict) -> None
```

### 6. Logger Service
**Purpose:** Provides centralized logging functionality
**Interface:**
```python
class LoggerService:
    def setup_logger() -> logging.Logger
    def log_info(self, message: str) -> None
    def log_error(self, message: str, exception: Exception = None) -> None
```

## Data Models

### Configuration Model
```python
@dataclass
class AppConfig:
    source_folder: str
    saved_folder: str
    error_folder: str
    
    def validate(self) -> List[str]:
        """Returns list of validation errors"""
```

### File Processing Result
```python
@dataclass
class ProcessingResult:
    success: bool
    file_path: str
    error_message: Optional[str] = None
    processing_time: float = 0.0
    folders_cleaned: List[str] = field(default_factory=list)
```

### Error Log Entry
```python
@dataclass
class ErrorLogEntry:
    timestamp: datetime
    file_path: str
    error_message: str
    stack_trace: Optional[str] = None
```

## Error Handling

### Error Categories
1. **Configuration Errors:** Missing or invalid environment variables
2. **File System Errors:** Permission issues, file not found, disk space
3. **Processing Errors:** File corruption, encoding issues, business logic failures
4. **Monitoring Errors:** File system event monitoring failures
5. **Folder Cleanup Errors:** Permission issues when removing empty folders

### Error Handling Strategy
- **Graceful Degradation:** Continue processing other files when one fails
- **Comprehensive Logging:** Log all errors at ERROR level with full context
- **Error File Management:** Move failed files to error folder with detailed logs
- **Recovery Mechanisms:** Retry logic for transient failures

### Error Log Format

#### File Processing Error Log
**Filename Format:** `[original_filename].[original_extension].log`
**Examples:** 
- `document.pdf` → `document.pdf.log`
- `data.csv` → `data.csv.log`
- `backup.tar.gz` → `backup.tar.gz.log`

**Content Format:**
```
Timestamp: 2025-01-23 10:30:45
File: /source/subfolder/document.txt
Error: Permission denied when reading file
Stack Trace: [if applicable]
Additional Context: File size: 1024 bytes, Last modified: 2025-01-23 10:29:12
```

#### Empty Folder Log
**Filename:** `empty_folder.log`
**Content Format:**
```
Timestamp: 2025-01-23 10:30:45
Folder: /source/subfolder/empty_directory
Reason: Completely empty folder detected (no files, no subfolders) and moved to error folder
Original Path: /source/subfolder/empty_directory
Moved To: /error/subfolder/empty_directory
```

## Testing Strategy

### Unit Testing Approach
1. **Component Isolation:** Test each component independently with mocks
2. **Configuration Testing:** Validate environment variable handling and validation
3. **File Operations Testing:** Test file movement and folder structure preservation
4. **Error Scenarios:** Test all error conditions and recovery mechanisms
5. **Event Handling:** Test file system event processing with simulated events

### Test Categories
- **Configuration Tests:** Environment variable loading, validation, error handling
- **File Monitor Tests:** Event detection, recursive monitoring, error handling
- **File Processor Tests:** Content reading, processing logic, error scenarios
- **File Manager Tests:** File movement, folder creation, structure preservation, empty folder cleanup
- **Error Handler Tests:** Log file creation with correct filename format, error message formatting, empty folder log creation
- **Empty Folder Tests:** Empty folder detection, movement to error folder, log file creation
- **Folder Cleanup Tests:** Empty folder detection, recursive cleanup, permission handling
- **Integration Tests:** End-to-end workflow testing with temporary directories

### Test Data Strategy
- Use temporary directories for all file system operations
- Create test files with various content types and sizes
- Simulate permission errors and file system failures
- Test with nested folder structures to verify preservation logic

## Performance Considerations

### Memory Management
- Stream large files instead of loading entirely into memory
- Use context managers for file operations to ensure proper cleanup
- Implement file size limits to prevent memory exhaustion

### Concurrency
- Single-threaded processing to avoid file system race conditions
- Queue-based processing for high-volume scenarios (future enhancement)
- Atomic file operations to prevent partial processing

### Monitoring Efficiency
- Use native file system events (inotify on Linux, FSEvents on macOS)
- Recursive monitoring setup to handle nested directories
- Efficient event filtering to process only relevant file events

## Folder Cleanup Design

### Empty Folder Detection Algorithm
The folder cleanup functionality ensures that empty directories are automatically removed after file processing to maintain a clean source folder structure.

#### Cleanup Process Flow
```
File Successfully Moved
         │
         ▼
Extract Current Folder Path (where file was located)
         │
         ▼
Check if Current Folder is Empty
    │           │
    ▼ (Yes)     ▼ (No)
Remove Folder   Stop Cleanup
    │
    ▼
Move to Parent Folder
    │
    ▼
Check if Parent Folder is Empty
    │           │
    ▼ (Yes)     ▼ (No)
Remove Parent   Stop Cleanup
    │
    ▼
Continue Recursively Until Non-Empty or Source Root
```

#### Empty Folder Criteria
A folder is considered empty when:
1. Contains no files (regular files, not directories)
2. Contains no subdirectories with files
3. May contain empty subdirectories (which will also be removed)

#### Recursive Cleanup Logic
```python
def cleanup_empty_folders(self, original_file_path: str) -> List[str]:
    """
    Recursively removes empty folders starting from the file's original directory
    up to the source folder root, stopping when a non-empty folder is encountered.
    
    Returns list of removed folder paths for logging purposes.
    """
    removed_folders = []
    # Start with the folder that contained the file
    current_folder = Path(original_file_path).parent
    
    while current_folder != Path(self.source_folder) and current_folder != current_folder.parent:
        if self._is_folder_empty(current_folder):
            try:
                current_folder.rmdir()
                removed_folders.append(str(current_folder))
                # Move to parent folder for next iteration
                current_folder = current_folder.parent
            except (OSError, PermissionError) as e:
                # Log warning and stop cleanup
                self.logger.warning(f"Could not remove empty folder {current_folder}: {e}")
                break
        else:
            # Folder not empty, stop cleanup
            break
    
    return removed_folders
```

#### Safety Measures
- **Never remove source root:** Cleanup stops at the configured source folder
- **Permission handling:** Gracefully handle permission errors without stopping processing
- **Atomic operations:** Each folder removal is atomic to prevent partial cleanup
- **Logging:** All folder removals and errors are logged for audit purposes

## Dependencies

### Core Dependencies
- **watchdog:** Cross-platform file system event monitoring
- **python-dotenv:** Environment variable management from .env files
- **pathlib:** Modern path handling (built-in)
- **logging:** Comprehensive logging functionality (built-in)
- **shutil:** File operations and directory management (built-in)

### Development Dependencies
- **pytest:** Unit testing framework
- **pytest-mock:** Mocking support for tests
- **pytest-cov:** Code coverage reporting
- **black:** Code formatting
- **flake8:** Code linting