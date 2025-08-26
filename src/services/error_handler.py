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
    
    def __init__(self, error_folder: str, source_folder: Optional[str] = None):
        """
        Initialize the ErrorHandler with the error folder path.
        
        Args:
            error_folder: Path to the folder where error logs will be stored
            source_folder: Optional path to source folder for structure preservation
        """
        self.error_folder = Path(error_folder)
        self.source_folder = Path(source_folder) if source_folder else None
    
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
        
        Creates log files with format: [filename].[extension].log
        Examples: 
        - document.pdf → document.pdf.log
        - data.csv → data.csv.log  
        - backup.tar.gz → backup.tar.gz.log
        - file_without_extension → file_without_extension.log
        
        The error log is placed in the same folder as the failed file within
        the error folder structure, preserving the original folder hierarchy.
        
        Args:
            file_path: Original file path that failed processing
            
        Returns:
            Path object for the error log file with enhanced naming format
        """
        original_path = Path(file_path)
        
        # Create log file with format: [filename].[extension].log
        # Use the full filename (including all extensions) + .log
        log_filename = f"{original_path.name}.log"
        
        # Determine the error log directory with structure preservation
        if self.source_folder:
            # Preserve folder structure relative to source folder
            try:
                # Get relative path from source folder to the file
                relative_path = original_path.resolve().relative_to(self.source_folder.resolve())
                # Place log in the same folder as the failed file within error structure
                error_log_dir = self.error_folder / relative_path.parent
            except ValueError:
                # File is not under source folder - use just the error folder root
                error_log_dir = self.error_folder
        else:
            # No source folder specified, use error folder root
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
    
    def create_empty_folder_log(self, folder_path: str) -> None:
        """
        Create a log file for a completely empty folder that was moved to error folder.
        
        Creates "empty_folder.log" file inside the moved empty folder with timestamp,
        original path, and reason for the move.
        
        Args:
            folder_path: Original path to the empty folder that was moved
        """
        try:
            # Calculate where the folder was moved to in error folder
            original_path = Path(folder_path)
            
            # Determine the error log directory with structure preservation
            if self.source_folder:
                try:
                    # Get relative path from source folder to the folder
                    relative_path = original_path.resolve().relative_to(self.source_folder.resolve())
                    # The folder is now in the error folder with preserved structure
                    moved_folder_path = self.error_folder / relative_path
                except ValueError:
                    # Folder is not under source folder - use just the error folder root
                    moved_folder_path = self.error_folder / original_path.name
            else:
                # No source folder specified, use error folder root
                moved_folder_path = self.error_folder / original_path.name
            
            # Create the log file inside the moved folder
            log_file_path = moved_folder_path / "empty_folder.log"
            
            # Build log information
            log_info = {
                'timestamp': datetime.now().isoformat(),
                'original_path': str(folder_path),
                'moved_to': str(moved_folder_path),
                'reason': 'Completely empty folder detected (no files, no subfolders) and moved to error folder'
            }
            
            # Write the log file
            self._write_empty_folder_log(log_file_path, log_info)
            
        except Exception as e:
            # If we can't write the empty folder log, at least try to log to console
            print(f"Failed to create empty folder log for {folder_path}: {str(e)}")
    
    def _write_empty_folder_log(self, log_path: Path, log_info: Dict[str, Any]) -> None:
        """
        Write the empty folder information to the log file.
        
        Args:
            log_path: Path where the empty folder log should be written
            log_info: Dictionary containing empty folder details
        """
        with open(log_path, 'w', encoding='utf-8') as log_file:
            log_file.write("=" * 50 + "\n")
            log_file.write("EMPTY FOLDER LOG\n")
            log_file.write("=" * 50 + "\n\n")
            
            log_file.write(f"Timestamp: {log_info['timestamp']}\n")
            log_file.write(f"Folder: {log_info['original_path']}\n")
            log_file.write(f"Reason: {log_info['reason']}\n")
            log_file.write(f"Original Path: {log_info['original_path']}\n")
            log_file.write(f"Moved To: {log_info['moved_to']}\n\n")
            
            log_file.write("=" * 50 + "\n")