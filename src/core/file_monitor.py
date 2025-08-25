"""
File Monitor module for file system event monitoring.

This module contains the FileMonitor class that uses the watchdog library
to monitor file system events and trigger file processing when new files are created.
"""

import os
import time
from pathlib import Path
from typing import Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent

from ..services.logger_service import LoggerService
from .file_processor import FileProcessor


class FileEventHandler(FileSystemEventHandler):
    """
    Event handler for file system events.
    
    Handles file creation events and triggers processing through FileProcessor.
    """
    
    def __init__(self, file_processor: FileProcessor, logger_service: LoggerService):
        """
        Initialize the event handler.
        
        Args:
            file_processor: FileProcessor instance for processing files
            logger_service: LoggerService instance for logging
        """
        super().__init__()
        self.file_processor = file_processor
        self.logger = logger_service
    
    def on_created(self, event):
        """
        Handle file creation events.
        
        Args:
            event: FileSystemEvent representing the file creation
        """
        # Only process file creation events, not directory creation
        if not event.is_directory:
            file_path = event.src_path
            
            # Log the file creation event
            self.logger.log_info(f"New file detected: {file_path}")
            
            # Wait a brief moment to ensure file is fully written
            # This helps avoid processing partially written files
            time.sleep(0.1)
            
            # Verify file still exists and is accessible before processing
            if os.path.exists(file_path) and os.path.isfile(file_path):
                try:
                    # Process the file
                    result = self.file_processor.process_file(file_path)
                    
                    if result.success:
                        self.logger.log_info(f"File processing completed successfully: {file_path}")
                    else:
                        self.logger.log_error(f"File processing failed: {result.error_message}")
                        
                except Exception as e:
                    error_msg = f"Unexpected error processing file {file_path}: {str(e)}"
                    self.logger.log_error(error_msg, e)
            else:
                self.logger.log_error(f"File no longer exists or is not accessible: {file_path}")


class FileMonitor:
    """
    Monitors file system events using the watchdog library.
    
    Sets up recursive monitoring of a source folder and triggers file processing
    when new files are created.
    """
    
    def __init__(self, source_folder: str, file_processor: FileProcessor, 
                 logger_service: LoggerService):
        """
        Initialize FileMonitor with source folder and processor.
        
        Args:
            source_folder: Path to the folder to monitor
            file_processor: FileProcessor instance for processing files
            logger_service: LoggerService instance for logging
            
        Raises:
            ValueError: If source folder doesn't exist or is not a directory
        """
        self.source_folder = Path(source_folder).resolve()
        self.file_processor = file_processor
        self.logger = logger_service
        self.observer: Optional[Observer] = None
        self.event_handler: Optional[FileEventHandler] = None
        
        # Validate source folder
        if not self.source_folder.exists():
            raise ValueError(f"Source folder does not exist: {self.source_folder}")
        
        if not self.source_folder.is_dir():
            raise ValueError(f"Source path is not a directory: {self.source_folder}")
        
        # Create event handler
        self.event_handler = FileEventHandler(file_processor, logger_service)
        
        # Create observer
        self.observer = Observer()
    
    def start_monitoring(self) -> None:
        """
        Start file system event monitoring.
        
        Sets up recursive monitoring of the source folder and starts the observer.
        
        Raises:
            RuntimeError: If monitoring fails to start
        """
        try:
            if self.observer is None:
                raise RuntimeError("Observer not initialized")
            
            # Schedule recursive monitoring of the source folder
            self.observer.schedule(
                self.event_handler,
                str(self.source_folder),
                recursive=True
            )
            
            # Start the observer
            self.observer.start()
            
            self.logger.log_info(f"Started monitoring folder: {self.source_folder}")
            
        except Exception as e:
            error_msg = f"Failed to start file system monitoring: {str(e)}"
            self.logger.log_error(error_msg, e)
            raise RuntimeError(error_msg) from e
    
    def stop_monitoring(self) -> None:
        """
        Stop file system event monitoring.
        
        Stops the observer and waits for it to finish gracefully.
        """
        try:
            if self.observer and self.observer.is_alive():
                self.observer.stop()
                self.observer.join(timeout=5.0)  # Wait up to 5 seconds for graceful shutdown
                
                if self.observer.is_alive():
                    self.logger.log_error("Observer did not stop gracefully within timeout")
                else:
                    self.logger.log_info("File system monitoring stopped")
            
        except Exception as e:
            error_msg = f"Error stopping file system monitoring: {str(e)}"
            self.logger.log_error(error_msg, e)
    
    def is_monitoring(self) -> bool:
        """
        Check if monitoring is currently active.
        
        Returns:
            bool: True if monitoring is active, False otherwise
        """
        return self.observer is not None and self.observer.is_alive()
    
    def __enter__(self):
        """Context manager entry."""
        self.start_monitoring()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop_monitoring()