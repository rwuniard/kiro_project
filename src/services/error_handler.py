"""
Error Handler Service

This module provides error handling functionality for the folder file processor,
including error log file creation and detailed error information logging.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import traceback


class ErrorHandler:
    """
    Handles error logging and error file management for failed file processing.
    
    Creates detailed error log files with timestamps and error information
    when files fail to process.
    """
    
    def __init__(self, error_folder: str):
        """
        Initialize the ErrorHandler with the error folder path.
        
        Args:
            error_folder: Path to the folder where error logs will be stored
        """
        self.error_folder = Path(error_folder)
    
    def create_error_log(self, file_path: str, error_message: str, 
                        exception: Optional[Exception] = None) -> None:
        """
        Create an error log file for a failed file processing operation.
        
        Args:
            file_path: Path to the file that failed processing
            error_message: Description of the error that occurred
            exception: Optional exception object for additional details
        """
        try:
            error_log_path = self._get_error_log_path(file_path)
            error_info = self._build_error_info(file_path, error_message, exception)
            self._write_error_log(error_log_path, error_info)
        except Exception as e:
            # If we can't write the error log, at least try to log to console
            print(f"Failed to create error log for {file_path}: {str(e)}")
    
    def _get_error_log_path(self, file_path: str) -> Path:
        """
        Generate the error log file path based on the original file path.
        
        Args:
            file_path: Original file path that failed processing
            
        Returns:
            Path object for the error log file with .log extension
        """
        original_path = Path(file_path)
        # Create log file with same name but .log extension
        log_filename = f"{original_path.stem}.log"
        
        # Place error log in the error folder
        # For now, put all logs directly in error folder for simplicity
        # This can be enhanced later to preserve folder structure if needed
        error_log_dir = self.error_folder
        
        # Ensure the directory exists
        error_log_dir.mkdir(parents=True, exist_ok=True)
        
        return error_log_dir / log_filename
    
    def _build_error_info(self, file_path: str, error_message: str, 
                         exception: Optional[Exception] = None) -> Dict[str, Any]:
        """
        Build comprehensive error information dictionary.
        
        Args:
            file_path: Path to the file that failed
            error_message: Error description
            exception: Optional exception for stack trace
            
        Returns:
            Dictionary containing all error information
        """
        error_info = {
            'timestamp': datetime.now().isoformat(),
            'file_path': file_path,
            'error_message': error_message
        }
        
        # Add file information if file exists
        try:
            file_stat = os.stat(file_path)
            error_info['file_size'] = file_stat.st_size
            error_info['last_modified'] = datetime.fromtimestamp(file_stat.st_mtime).isoformat()
        except (OSError, FileNotFoundError):
            error_info['file_size'] = 'Unknown'
            error_info['last_modified'] = 'Unknown'
        
        # Add stack trace if exception provided
        if exception:
            error_info['exception_type'] = type(exception).__name__
            error_info['stack_trace'] = traceback.format_exception(
                type(exception), exception, exception.__traceback__
            )
        
        return error_info
    
    def _write_error_log(self, log_path: Path, error_info: Dict[str, Any]) -> None:
        """
        Write the error information to the log file.
        
        Args:
            log_path: Path where the error log should be written
            error_info: Dictionary containing error details
        """
        with open(log_path, 'w', encoding='utf-8') as log_file:
            log_file.write("=" * 50 + "\n")
            log_file.write("FILE PROCESSING ERROR LOG\n")
            log_file.write("=" * 50 + "\n\n")
            
            log_file.write(f"Timestamp: {error_info['timestamp']}\n")
            log_file.write(f"File: {error_info['file_path']}\n")
            log_file.write(f"Error: {error_info['error_message']}\n\n")
            
            log_file.write("File Information:\n")
            log_file.write(f"  Size: {error_info['file_size']} bytes\n")
            log_file.write(f"  Last Modified: {error_info['last_modified']}\n\n")
            
            if 'exception_type' in error_info:
                log_file.write(f"Exception Type: {error_info['exception_type']}\n\n")
            
            if 'stack_trace' in error_info:
                log_file.write("Stack Trace:\n")
                for line in error_info['stack_trace']:
                    log_file.write(line)
                log_file.write("\n")
            
            log_file.write("=" * 50 + "\n")