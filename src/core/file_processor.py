"""
File Processor module for handling file processing logic.

This module contains the core business logic for reading and processing files,
integrating with FileManager for file movement and ErrorHandler for error handling.
"""

import os
import time
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from src.services.logger_service import LoggerService
from src.core.file_manager import FileManager
from src.services.error_handler import ErrorHandler


class ErrorType(Enum):
    """Classification of error types for retry logic."""
    TRANSIENT = "transient"  # Temporary errors that might resolve with retry
    PERMANENT = "permanent"  # Errors that won't resolve with retry
    UNKNOWN = "unknown"     # Unclassified errors


class RetryConfig:
    """Configuration for retry logic."""
    
    def __init__(self, max_attempts: int = 3, base_delay: float = 1.0, 
                 max_delay: float = 10.0, backoff_multiplier: float = 2.0):
        """
        Initialize retry configuration.
        
        Args:
            max_attempts: Maximum number of retry attempts
            base_delay: Initial delay between retries in seconds
            max_delay: Maximum delay between retries in seconds
            backoff_multiplier: Multiplier for exponential backoff
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_multiplier = backoff_multiplier


@dataclass
class ProcessingResult:
    """Result of file processing operation."""
    success: bool
    file_path: str
    error_message: Optional[str] = None
    processing_time: float = 0.0
    cleaned_folders: List[str] = None
    
    def __post_init__(self):
        """Initialize cleaned_folders as empty list if None."""
        if self.cleaned_folders is None:
            self.cleaned_folders = []


class FileProcessor:
    """
    Contains the core business logic for file processing.
    
    Handles file reading, processing, and coordination with FileManager
    and ErrorHandler for appropriate file movement and error logging.
    Includes comprehensive error handling with retry logic for transient errors.
    """
    
    def __init__(self, file_manager: FileManager, error_handler: ErrorHandler, 
                 logger_service: LoggerService, retry_config: Optional[RetryConfig] = None):
        """
        Initialize FileProcessor with required services.
        
        Args:
            file_manager: FileManager instance for file operations
            error_handler: ErrorHandler instance for error logging
            logger_service: LoggerService instance for application logging
            retry_config: Optional retry configuration for transient errors
        """
        self.file_manager = file_manager
        self.error_handler = error_handler
        self.logger = logger_service
        self.retry_config = retry_config or RetryConfig()
        
        # Track processing statistics
        self.stats = {
            'total_processed': 0,
            'successful': 0,
            'failed_permanent': 0,
            'failed_after_retry': 0,
            'retries_attempted': 0
        }
        
    def process_file(self, file_path: str) -> ProcessingResult:
        """
        Process a single file with comprehensive error handling and retry logic.
        
        Args:
            file_path: Absolute path to the file to process
            
        Returns:
            ProcessingResult: Result of the processing operation
        """
        start_time = datetime.now()
        self.stats['total_processed'] += 1
        
        try:
            # Validate file exists and is accessible (with retry for transient issues)
            self._execute_with_retry(
                self._validate_file_access, 
                "File validation", 
                file_path
            )
            
            # Read file content with retry logic
            content = self._execute_with_retry(
                self._read_file_content, 
                "File reading", 
                file_path
            )
            
            # Perform processing with retry logic
            self._execute_with_retry(
                self._perform_processing, 
                "File processing", 
                content, file_path
            )
            
            # Move to saved folder on success with retry logic
            cleaned_folders = self._execute_with_retry(
                self._move_to_saved_with_validation, 
                "File movement to saved folder", 
                file_path
            )
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Update statistics
            self.stats['successful'] += 1
            
            # Log success
            relative_path = self.file_manager.get_relative_path(file_path) or os.path.basename(file_path)
            self.logger.log_info(f"Successfully processed file: {relative_path}")
            
            # Log folder cleanup if any folders were removed
            if cleaned_folders:
                for folder in cleaned_folders:
                    folder_relative = self.file_manager.get_relative_path(folder) or os.path.basename(folder)
                    self.logger.log_info(f"Cleaned up empty folder: {folder_relative}")
            
            # Print to screen as required
            print(f"Processed file: {relative_path}")
            
            return ProcessingResult(
                success=True,
                file_path=file_path,
                processing_time=processing_time,
                cleaned_folders=cleaned_folders
            )
            
        except Exception as e:
            # Calculate processing time even for failures
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Classify error for statistics
            error_type = self._classify_error(e)
            if error_type == ErrorType.PERMANENT:
                self.stats['failed_permanent'] += 1
            else:
                self.stats['failed_after_retry'] += 1
            
            error_message = f"Failed to process file {file_path}: {str(e)}"
            
            # Log the error with classification
            self.logger.log_error(f"{error_message} (Error type: {error_type.value})", e)
            
            # Create error log file (with retry for transient file system issues)
            try:
                self._execute_with_retry(
                    self.error_handler.create_error_log,
                    "Error log creation",
                    file_path, str(e), e
                )
            except Exception as log_error:
                self.logger.log_error(f"Failed to create error log: {log_error}")
            
            # Move to error folder (with retry for transient file system issues)
            try:
                self._execute_with_retry(
                    self._move_to_error_with_validation,
                    "File movement to error folder",
                    file_path
                )
            except Exception as move_error:
                # If we can't move to error folder after retries, log but continue
                self.logger.log_error(f"Failed to move file to error folder after retries: {move_error}")
            
            return ProcessingResult(
                success=False,
                file_path=file_path,
                error_message=error_message,
                processing_time=processing_time
            )
    
    def _validate_file_access(self, file_path: str) -> None:
        """
        Validate that a file exists and is accessible.
        
        Args:
            file_path: Path to validate
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If path is not a file
            PermissionError: If file is not accessible
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if not os.path.isfile(file_path):
            raise ValueError(f"Path is not a file: {file_path}")
        
        # Test read access
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # Just test that we can open the file
                pass
        except PermissionError as e:
            raise PermissionError(f"Cannot access file: {e}")
    
    def _move_to_saved_with_validation(self, file_path: str) -> List[str]:
        """
        Move file to saved folder with validation and cleanup empty folders.
        
        Args:
            file_path: Path to file to move
            
        Returns:
            List[str]: List of cleaned folder paths
            
        Raises:
            RuntimeError: If move operation fails
        """
        move_success = self.file_manager.move_to_saved(file_path)
        if not move_success:
            raise RuntimeError("Failed to move file to saved folder")
        
        # Cleanup empty folders after successful move
        cleaned_folders = self.file_manager.cleanup_empty_folders(file_path)
        return cleaned_folders
    
    def _move_to_error_with_validation(self, file_path: str) -> None:
        """
        Move file to error folder with validation.
        
        Args:
            file_path: Path to file to move
            
        Raises:
            RuntimeError: If move operation fails
        """
        move_success = self.file_manager.move_to_error(file_path)
        if not move_success:
            raise RuntimeError("Failed to move file to error folder")
    
    def _read_file_content(self, file_path: str) -> str:
        """
        Read the content of a file with proper error handling.
        
        Args:
            file_path: Path to the file to read
            
        Returns:
            str: Content of the file
            
        Raises:
            Various exceptions for file reading issues
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                return content
                
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                with open(file_path, 'r', encoding='latin-1') as file:
                    content = file.read()
                    return content
            except Exception as e:
                raise UnicodeDecodeError(
                    'utf-8', b'', 0, 1, 
                    f"Failed to decode file with UTF-8 or Latin-1 encoding: {str(e)}"
                )
                
        except PermissionError as e:
            raise PermissionError(f"Permission denied when reading file: {str(e)}")
            
        except OSError as e:
            raise OSError(f"OS error when reading file: {str(e)}")
            
        except Exception as e:
            raise RuntimeError(f"Unexpected error reading file: {str(e)}")
    
    def _perform_processing(self, content: str, file_path: str) -> None:
        """
        Perform the actual file processing logic.
        
        Currently implements basic processing (validation and logging).
        This method can be extended with more complex processing logic.
        
        Args:
            content: Content of the file to process
            file_path: Path to the file being processed
        """
        # Basic processing: validate content is not empty
        if not content.strip():
            raise ValueError("File is empty or contains only whitespace")
        
        # Basic processing: log file information
        file_size = len(content)
        line_count = len(content.splitlines())
        
        self.logger.log_info(
            f"Processing file {os.path.basename(file_path)}: "
            f"{file_size} bytes, {line_count} lines"
        )
        
        # Additional processing logic can be added here
        # For now, we just validate the file was readable and has content
    
    def _classify_error(self, exception: Exception) -> ErrorType:
        """
        Classify an error to determine if it's worth retrying.
        
        Args:
            exception: The exception to classify
            
        Returns:
            ErrorType: Classification of the error
        """
        # Transient errors that might resolve with retry
        transient_errors = (
            OSError,  # Temporary file system issues
            PermissionError,  # Might be temporary file locks
            FileNotFoundError,  # File might appear after brief delay
        )
        
        # Permanent errors that won't resolve with retry
        permanent_errors = (
            UnicodeDecodeError,  # File encoding issues
            ValueError,  # Business logic validation errors
        )
        
        if isinstance(exception, transient_errors):
            # Additional checks for specific transient conditions
            if isinstance(exception, PermissionError):
                # Some permission errors might be temporary (file locks)
                return ErrorType.TRANSIENT
            elif isinstance(exception, OSError):
                # Check specific OS error codes
                if hasattr(exception, 'errno'):
                    # Common transient OS errors
                    transient_errno = [2, 5, 11, 13, 16, 26]  # ENOENT, EIO, EAGAIN, EACCES, EBUSY, ETXTBSY
                    if exception.errno in transient_errno:
                        return ErrorType.TRANSIENT
                return ErrorType.TRANSIENT
            elif isinstance(exception, FileNotFoundError):
                return ErrorType.TRANSIENT
        
        if isinstance(exception, permanent_errors):
            return ErrorType.PERMANENT
        
        # Default to unknown for unclassified errors
        return ErrorType.UNKNOWN
    
    def _execute_with_retry(self, operation: Callable, operation_name: str, 
                           *args, **kwargs) -> Any:
        """
        Execute an operation with retry logic for transient errors.
        
        Args:
            operation: The operation to execute
            operation_name: Name of the operation for logging
            *args: Arguments to pass to the operation
            **kwargs: Keyword arguments to pass to the operation
            
        Returns:
            Result of the operation
            
        Raises:
            Exception: The last exception if all retries fail
        """
        last_exception = None
        delay = self.retry_config.base_delay
        
        for attempt in range(self.retry_config.max_attempts):
            try:
                return operation(*args, **kwargs)
                
            except Exception as e:
                last_exception = e
                error_type = self._classify_error(e)
                
                # Don't retry permanent errors
                if error_type == ErrorType.PERMANENT:
                    self.logger.log_error(
                        f"{operation_name} failed with permanent error on attempt {attempt + 1}: {str(e)}"
                    )
                    raise e
                
                # Don't retry on the last attempt
                if attempt == self.retry_config.max_attempts - 1:
                    self.logger.log_error(
                        f"{operation_name} failed after {self.retry_config.max_attempts} attempts: {str(e)}"
                    )
                    break
                
                # Log retry attempt
                self.stats['retries_attempted'] += 1
                self.logger.log_info(
                    f"{operation_name} failed on attempt {attempt + 1} ({error_type.value} error), "
                    f"retrying in {delay:.1f}s: {str(e)}"
                )
                
                # Wait before retry with exponential backoff
                time.sleep(delay)
                delay = min(delay * self.retry_config.backoff_multiplier, self.retry_config.max_delay)
        
        # All retries exhausted
        if last_exception:
            raise last_exception
    
    def process_empty_folder(self, folder_path: str) -> ProcessingResult:
        """
        Process a completely empty folder by moving it to error folder with log creation.
        
        Args:
            folder_path: Path to the completely empty folder
            
        Returns:
            ProcessingResult: Result of the processing operation
        """
        start_time = datetime.now()
        
        try:
            # Validate it's actually a completely empty folder
            if not self.file_manager.is_completely_empty_folder(folder_path):
                error_message = f"Folder is not completely empty: {folder_path}"
                self.logger.log_error(error_message)
                return ProcessingResult(
                    success=False,
                    file_path=folder_path,
                    error_message=error_message,
                    processing_time=(datetime.now() - start_time).total_seconds()
                )
            
            # Move empty folder to error folder
            move_success = self.file_manager.move_empty_folder_to_error(folder_path)
            if not move_success:
                error_message = f"Failed to move empty folder to error folder: {folder_path}"
                self.logger.log_error(error_message)
                return ProcessingResult(
                    success=False,
                    file_path=folder_path,
                    error_message=error_message,
                    processing_time=(datetime.now() - start_time).total_seconds()
                )
            
            # Create empty folder log
            try:
                self.error_handler.create_empty_folder_log(folder_path)
            except Exception as log_error:
                self.logger.log_error(f"Failed to create empty folder log: {log_error}")
                # Don't fail the whole operation if log creation fails
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Log success
            relative_path = self.file_manager.get_relative_path(folder_path) or os.path.basename(folder_path)
            self.logger.log_info(f"Successfully processed completely empty folder: {relative_path}")
            
            return ProcessingResult(
                success=True,
                file_path=folder_path,
                processing_time=processing_time
            )
            
        except Exception as e:
            error_message = f"Failed to process empty folder {folder_path}: {str(e)}"
            self.logger.log_error(error_message, e)
            
            return ProcessingResult(
                success=False,
                file_path=folder_path,
                error_message=error_message,
                processing_time=(datetime.now() - start_time).total_seconds()
            )
    
    def get_processing_stats(self) -> Dict[str, int]:
        """
        Get processing statistics.
        
        Returns:
            Dictionary containing processing statistics
        """
        return self.stats.copy()