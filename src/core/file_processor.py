"""
File Processor module for handling file processing logic.

This module contains the core business logic for reading and processing files,
integrating with FileManager for file movement and ErrorHandler for error handling.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

from services.logger_service import LoggerService
from core.file_manager import FileManager
from services.error_handler import ErrorHandler


@dataclass
class ProcessingResult:
    """Result of file processing operation."""
    success: bool
    file_path: str
    error_message: Optional[str] = None
    processing_time: float = 0.0


class FileProcessor:
    """
    Contains the core business logic for file processing.
    
    Handles file reading, processing, and coordination with FileManager
    and ErrorHandler for appropriate file movement and error logging.
    """
    
    def __init__(self, file_manager: FileManager, error_handler: ErrorHandler, 
                 logger_service: LoggerService):
        """
        Initialize FileProcessor with required services.
        
        Args:
            file_manager: FileManager instance for file operations
            error_handler: ErrorHandler instance for error logging
            logger_service: LoggerService instance for application logging
        """
        self.file_manager = file_manager
        self.error_handler = error_handler
        self.logger = logger_service
        
    def process_file(self, file_path: str) -> ProcessingResult:
        """
        Process a single file with error handling and appropriate file movement.
        
        Args:
            file_path: Absolute path to the file to process
            
        Returns:
            ProcessingResult: Result of the processing operation
        """
        start_time = datetime.now()
        
        try:
            # Validate file exists and is accessible
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
            
            if not os.path.isfile(file_path):
                raise ValueError(f"Path is not a file: {file_path}")
            
            # Read file content
            content = self._read_file_content(file_path)
            
            # Perform processing
            self._perform_processing(content, file_path)
            
            # Move to saved folder on success
            move_success = self.file_manager.move_to_saved(file_path)
            if not move_success:
                raise RuntimeError("Failed to move file to saved folder")
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Log success
            relative_path = self.file_manager.get_relative_path(file_path) or os.path.basename(file_path)
            self.logger.log_info(f"Successfully processed file: {relative_path}")
            
            # Print to screen as required
            print(f"Processed file: {relative_path}")
            
            return ProcessingResult(
                success=True,
                file_path=file_path,
                processing_time=processing_time
            )
            
        except Exception as e:
            # Calculate processing time even for failures
            processing_time = (datetime.now() - start_time).total_seconds()
            
            error_message = f"Failed to process file {file_path}: {str(e)}"
            
            # Log the error
            self.logger.log_error(error_message, e)
            
            # Create error log file
            self.error_handler.create_error_log(file_path, str(e), e)
            
            # Move to error folder
            try:
                self.file_manager.move_to_error(file_path)
            except Exception as move_error:
                # If we can't move to error folder, log but don't fail completely
                self.logger.log_error(f"Failed to move file to error folder: {move_error}")
            
            return ProcessingResult(
                success=False,
                file_path=file_path,
                error_message=error_message,
                processing_time=processing_time
            )
    
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