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
from src.core.document_processing import DocumentProcessingInterface


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
                 logger_service: LoggerService, document_processor: Optional[DocumentProcessingInterface] = None,
                 retry_config: Optional[RetryConfig] = None):
        """
        Initialize FileProcessor with required services.
        
        Args:
            file_manager: FileManager instance for file operations
            error_handler: ErrorHandler instance for error logging
            logger_service: LoggerService instance for application logging
            document_processor: Optional DocumentProcessingInterface instance for document processing
            retry_config: Optional retry configuration for transient errors
        """
        self.file_manager = file_manager
        self.error_handler = error_handler
        self.logger = logger_service
        self.document_processor = document_processor
        self.retry_config = retry_config or RetryConfig()
        
        # Validate that document processor is properly initialized if provided
        if self.document_processor is not None:
            self._validate_document_processor()
        
        # Track processing statistics
        self.stats = {
            'total_processed': 0,
            'successful': 0,
            'failed_permanent': 0,
            'failed_after_retry': 0,
            'retries_attempted': 0
        }
    
    def _validate_document_processor(self) -> None:
        """
        Validate that the document processor is properly initialized.
        
        Raises:
            ValueError: If document processor is not properly initialized
            RuntimeError: If document processor initialization check fails
        """
        try:
            # Check if processor has required methods (interface compliance)
            required_methods = ['initialize', 'is_supported_file', 'process_document', 
                              'get_supported_extensions', 'cleanup']
            
            for method_name in required_methods:
                if not hasattr(self.document_processor, method_name):
                    raise ValueError(
                        f"Document processor missing required method: {method_name}"
                    )
                
                method = getattr(self.document_processor, method_name)
                if not callable(method):
                    raise ValueError(
                        f"Document processor method {method_name} is not callable"
                    )
            
            # Test basic functionality by getting supported extensions
            try:
                extensions = self.document_processor.get_supported_extensions()
                if not isinstance(extensions, set):
                    raise ValueError(
                        "Document processor get_supported_extensions() must return a set"
                    )
            except Exception as e:
                raise RuntimeError(
                    f"Document processor failed basic functionality test: {str(e)}"
                )
            
            self.logger.log_info(
                f"Document processor validation successful: {self.document_processor.get_processor_name()}"
            )
            
        except Exception as e:
            error_msg = f"Document processor validation failed: {str(e)}"
            self.logger.log_error(error_msg)
            raise ValueError(error_msg) from e
    
    @staticmethod
    def should_ignore_file(file_path: str) -> bool:
        """
        Determine if a file should be ignored from processing.
        
        Ignores system files that are automatically generated by the OS
        and shouldn't be processed as documents.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            bool: True if the file should be ignored, False if it should be processed
        """
        filename = os.path.basename(file_path).lower()
        
        # System files to ignore
        ignored_files = {
            '.ds_store',           # macOS Finder metadata
            'desktop.ini',         # Windows folder customization
            '.spotlightv100',      # macOS Spotlight index
            '.fseventsd',          # macOS file system events
            '.documentrevisions-v100',  # macOS document revisions
            '.trash',              # Trash folder
            '$recycle.bin',        # Windows recycle bin
            'pagefile.sys',        # Windows virtual memory
            'hiberfil.sys',        # Windows hibernation file
        }
        
        # Check if filename matches any ignored files
        if filename in ignored_files:
            return True
        
        # Ignore hidden files starting with dot (except some known document types)
        if filename.startswith('.') and not filename.endswith(('.txt', '.md', '.pdf', '.doc', '.docx')):
            return True
        
        # Ignore temporary files (but not Office temp files which might be legitimate)
        temp_patterns = [
            '.tmp',    # Generic temporary files
            '.temp',   # Generic temporary files
            '.swp',    # Vim swap files
            '.lock',   # Lock files
        ]
        
        for pattern in temp_patterns:
            if filename.endswith(pattern):
                return True
        
        return False
        
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
        
        # Check if file should be ignored (early exit to avoid processing system files)
        if self.should_ignore_file(file_path):
            processing_time = (datetime.now() - start_time).total_seconds()
            relative_path = self.file_manager.get_relative_path(file_path) or os.path.basename(file_path)
            self.logger.log_info(f"Ignoring system/temporary file: {relative_path}")
            
            return ProcessingResult(
                success=True,
                file_path=file_path,
                error_message=None,
                processing_time=processing_time,
                cleaned_folders=[]
            )
        
        try:
            # Validate file exists and is accessible (with retry for transient issues)
            self._execute_with_retry(
                self._validate_file_access, 
                "File validation", 
                file_path
            )
            
            # Perform processing with retry logic
            self._execute_with_retry(
                self._perform_processing, 
                "File processing", 
                file_path
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
                # Check if we have a DocumentProcessingError to pass along
                doc_error = self._extract_document_processing_error(e)
                if doc_error:
                    self._execute_with_retry(
                        self.error_handler.create_document_processing_error_log,
                        "Document processing error log creation",
                        file_path, str(e), e, doc_error
                    )
                else:
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
    
    def _perform_processing(self, file_path: str) -> None:
        """
        Perform document processing using the configured DocumentProcessingInterface.
        
        This method processes the file through the document processing system
        and handles the ProcessingResult appropriately. If no document processor
        is configured, performs basic file validation.
        
        Args:
            file_path: Path to the file being processed
            
        Raises:
            Exception: If document processing fails or file validation fails
        """
        # If no document processor is configured, perform basic file processing
        if self.document_processor is None:
            self._perform_basic_processing(file_path)
            return
        
        from .document_processing import DocumentProcessingError
        
        # Convert to Path object for document processor
        path_obj = Path(file_path)
        
        # Process document through the document processing interface
        result = self.document_processor.process_document(path_obj)
        
        # Handle processing result
        if not result.success:
            # Create appropriate exception based on error type
            error_msg = result.error_message or "Document processing failed"
            
            # Check if we have a DocumentProcessingError in metadata
            processing_error = result.metadata.get('processing_error') if result.metadata else None
            
            if processing_error and isinstance(processing_error, DocumentProcessingError):
                # Create exception with DocumentProcessingError in metadata for enhanced error handling
                exception = RuntimeError(f"Document processing failed: {error_msg}")
                exception.metadata = {'processing_error': processing_error}
                raise exception
            else:
                # Raise with basic error information
                if result.error_type == "unsupported_file_type":
                    raise ValueError(f"Unsupported file type: {error_msg}")
                elif result.error_type == "empty_document":
                    raise ValueError(f"Empty document: {error_msg}")
                elif result.error_type == "initialization_error":
                    raise RuntimeError(f"Processor not initialized: {error_msg}")
                else:
                    raise RuntimeError(f"Document processing failed: {error_msg}")
        
        # Log successful processing with detailed information
        relative_path = self.file_manager.get_relative_path(file_path) or os.path.basename(file_path)
        
        # Extract metadata for logging
        metadata = result.metadata or {}
        processor_name = metadata.get('document_processor', 'unknown')
        file_size = metadata.get('file_size', 0)
        model_vendor = metadata.get('model_vendor', 'unknown')
        
        self.logger.log_info(
            f"Document processing completed for {relative_path}: "
            f"processor={processor_name}, chunks={result.chunks_created}, "
            f"time={result.processing_time:.2f}s, size={file_size} bytes, "
            f"model={model_vendor}"
        )
    
    def _perform_basic_processing(self, file_path: str) -> None:
        """
        Perform basic file processing when document processing is not available.
        
        This method performs basic file validation and logging without
        advanced document processing features.
        
        Args:
            file_path: Path to the file being processed
            
        Raises:
            ValueError: If file validation fails
        """
        # Basic file validation
        path_obj = Path(file_path)
        
        if not path_obj.exists():
            raise ValueError(f"File does not exist: {file_path}")
        
        if path_obj.stat().st_size == 0:
            raise ValueError(f"File is empty: {file_path}")
        
        # Try to read file to ensure it's accessible
        try:
            with open(file_path, 'rb') as f:
                # Read first few bytes to ensure file is readable
                f.read(1024)
        except Exception as e:
            raise ValueError(f"File is not readable: {str(e)}")
        
        # Log successful basic processing
        relative_path = self.file_manager.get_relative_path(file_path) or os.path.basename(file_path)
        file_size = path_obj.stat().st_size
        
        self.logger.log_info(
            f"Basic file processing completed for {relative_path}: "
            f"size={file_size} bytes (document processing disabled)"
        )
    
    def _classify_error(self, exception: Exception) -> ErrorType:
        """
        Classify an error to determine if it's worth retrying.
        
        Args:
            exception: The exception to classify
            
        Returns:
            ErrorType: Classification of the error
        """
        from .document_processing import DocumentProcessingError
        
        # Check for DocumentProcessingError first (highest priority)
        if hasattr(exception, '__cause__') and isinstance(exception.__cause__, DocumentProcessingError):
            # Extract DocumentProcessingError from exception chain
            doc_error = exception.__cause__
            return self._classify_document_processing_error(doc_error)
        
        # Check if exception contains DocumentProcessingError information
        error_message = str(exception).lower()
        
        # Document processing permanent errors (don't retry)
        if any(keyword in error_message for keyword in [
            'unsupported file type',
            'empty document', 
            'processor not initialized',
            'invalid file format',
            'corrupted file',
            'file too large',
            'invalid document structure',
            'malformed content'
        ]):
            return ErrorType.PERMANENT
        
        # Document processing transient errors (retry possible)
        if any(keyword in error_message for keyword in [
            'api rate limit',
            'connection timeout',
            'network error',
            'temporary unavailable',
            'service unavailable',
            'chromadb',
            'embedding generation failed',
            'rate limit exceeded',
            'quota exceeded',
            'server overloaded',
            'deadline exceeded',
            '504 deadline exceeded',
            'timeout',
            'googlegenerativeaierror'
        ]):
            return ErrorType.TRANSIENT
        
        # Traditional file system errors
        # Transient errors that might resolve with retry
        transient_errors = (
            OSError,  # Temporary file system issues
            PermissionError,  # Might be temporary file locks
            FileNotFoundError,  # File might appear after brief delay
        )
        
        # Permanent errors that won't resolve with retry
        permanent_errors = (
            UnicodeDecodeError,  # File encoding issues
            ValueError,  # Business logic validation errors (including document processing)
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
            # For ValueError, check if it's document processing related
            if isinstance(exception, ValueError):
                # Document processing ValueErrors are typically permanent
                if any(keyword in error_message for keyword in [
                    'document processing',
                    'unsupported file',
                    'empty document',
                    'invalid format'
                ]):
                    return ErrorType.PERMANENT
            return ErrorType.PERMANENT
        
        # RuntimeError classification based on content
        if isinstance(exception, RuntimeError):
            # Some RuntimeErrors from document processing might be transient
            if any(keyword in error_message for keyword in [
                'api rate limit',
                'connection',
                'timeout',
                'network',
                'temporary',
                'quota',
                'overloaded',
                'deadline exceeded',
                '504 deadline exceeded',
                'googlegenerativeaierror'
            ]):
                return ErrorType.TRANSIENT
            else:
                # Check if it's a document processing related RuntimeError
                if any(keyword in error_message for keyword in [
                    'document processing',
                    'processor not initialized',
                    'processing failed'
                ]):
                    return ErrorType.PERMANENT
                else:
                    # Other RuntimeErrors are unknown
                    return ErrorType.UNKNOWN
        
        # Default to unknown for unclassified errors
        return ErrorType.UNKNOWN
    
    def _classify_document_processing_error(self, doc_error: 'DocumentProcessingError') -> ErrorType:
        """
        Classify a DocumentProcessingError to determine retry behavior.
        
        Args:
            doc_error: DocumentProcessingError instance to classify
            
        Returns:
            ErrorType: Classification of the document processing error
        """
        error_type = doc_error.error_type.lower()
        error_message = doc_error.error_message.lower()
        
        # Permanent document processing errors (don't retry)
        permanent_error_types = {
            'unsupported_file_type',
            'empty_document',
            'invalid_file_format',
            'corrupted_file',
            'file_too_large',
            'initialization_error',
            'configuration_error',
            'invalid_document_structure',
            'malformed_content',
            'encoding_error'
        }
        
        if error_type in permanent_error_types:
            return ErrorType.PERMANENT
        
        # Transient document processing errors (retry possible)
        transient_error_types = {
            'api_rate_limit',
            'connection_timeout',
            'network_error',
            'service_unavailable',
            'temporary_failure',
            'quota_exceeded',
            'server_overloaded',
            'chromadb_error',
            'embedding_generation_failed'
        }
        
        if error_type in transient_error_types:
            return ErrorType.TRANSIENT
        
        # Check error message for additional classification hints
        if any(keyword in error_message for keyword in [
            'rate limit',
            'quota exceeded',
            'connection',
            'timeout',
            'network',
            'temporary',
            'unavailable',
            'overloaded',
            'chromadb'
        ]):
            return ErrorType.TRANSIENT
        
        if any(keyword in error_message for keyword in [
            'unsupported',
            'invalid format',
            'corrupted',
            'empty',
            'malformed',
            'encoding'
        ]):
            return ErrorType.PERMANENT
        
        # Default to permanent for unknown document processing errors
        # to avoid infinite retries on unclassified errors
        return ErrorType.PERMANENT
    
    def _extract_document_processing_error(self, exception: Exception) -> Optional['DocumentProcessingError']:
        """
        Extract DocumentProcessingError from exception or exception metadata.
        
        Args:
            exception: Exception to examine for DocumentProcessingError
            
        Returns:
            DocumentProcessingError if found, None otherwise
        """
        from .document_processing import DocumentProcessingError
        
        # Check if exception has a DocumentProcessingError as cause
        if hasattr(exception, '__cause__') and isinstance(exception.__cause__, DocumentProcessingError):
            return exception.__cause__
        
        # Check if exception has DocumentProcessingError in args
        if hasattr(exception, 'args') and exception.args:
            for arg in exception.args:
                if isinstance(arg, DocumentProcessingError):
                    return arg
        
        # Check if exception has a metadata attribute with DocumentProcessingError
        if hasattr(exception, 'metadata') and isinstance(exception.metadata, dict):
            doc_error = exception.metadata.get('processing_error')
            if isinstance(doc_error, DocumentProcessingError):
                return doc_error
        
        return None
    
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
            # Validate it's actually a completely empty folder that should be processed
            if not self.file_manager.should_process_as_empty_folder(folder_path):
                error_message = f"Folder should not be processed as empty (may have had processed files): {folder_path}"
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