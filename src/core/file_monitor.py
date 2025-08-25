"""
File Monitor module for file system event monitoring.

This module contains the FileMonitor class that uses the watchdog library
to monitor file system events and trigger file processing when new files are created.
"""

import os
import time
import threading
from pathlib import Path
from typing import Optional, Set
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent

from src.services.logger_service import LoggerService
from src.core.file_processor import FileProcessor


class FileEventHandler(FileSystemEventHandler):
    """
    Event handler for file system events with resilience and error handling.
    
    Handles file creation events and triggers processing through FileProcessor.
    Includes duplicate event filtering and graceful error handling.
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
        
        # Track recently processed files to avoid duplicates
        self._recent_files: Set[str] = set()
        self._recent_files_lock = threading.Lock()
        
        # Statistics
        self.stats = {
            'events_received': 0,
            'files_processed': 0,
            'duplicate_events_filtered': 0,
            'processing_errors': 0
        }
    
    def on_created(self, event):
        """
        Handle file creation events with comprehensive error handling.
        
        Args:
            event: FileSystemEvent representing the file creation
        """
        self.stats['events_received'] += 1
        
        # Only process file creation events, not directory creation
        if event.is_directory:
            return
        
        file_path = event.src_path
        
        try:
            # Filter duplicate events
            if self._is_duplicate_event(file_path):
                self.stats['duplicate_events_filtered'] += 1
                return
            
            # Log the file creation event
            self.logger.log_info(f"New file detected: {file_path}")
            
            # Process the file with resilience
            self._process_file_with_resilience(file_path)
            
        except Exception as e:
            self.stats['processing_errors'] += 1
            error_msg = f"Critical error in event handler for file {file_path}: {str(e)}"
            self.logger.log_error(error_msg, e)
            # Continue processing other files despite this error
    
    def _is_duplicate_event(self, file_path: str) -> bool:
        """
        Check if this file was recently processed to avoid duplicate processing.
        
        Args:
            file_path: Path to check
            
        Returns:
            bool: True if this is a duplicate event
        """
        with self._recent_files_lock:
            if file_path in self._recent_files:
                return True
            
            # Add to recent files and clean up old entries
            self._recent_files.add(file_path)
            
            # Keep only recent entries (simple cleanup)
            if len(self._recent_files) > 100:
                # Remove oldest entries (simplified approach)
                self._recent_files = set(list(self._recent_files)[-50:])
            
            return False
    
    def _process_file_with_resilience(self, file_path: str) -> None:
        """
        Process a file with resilience and stability checks.
        
        Args:
            file_path: Path to the file to process
        """
        max_stability_checks = 5
        stability_delay = 0.2
        
        # Wait for file to be stable (fully written)
        for check in range(max_stability_checks):
            if not self._wait_for_file_stability(file_path, stability_delay):
                self.logger.log_error(f"File stability check failed: {file_path}")
                return
            
            # Verify file still exists and is accessible
            if not self._validate_file_ready(file_path):
                return
            
            try:
                # Process the file
                result = self.file_processor.process_file(file_path)
                self.stats['files_processed'] += 1
                
                if result.success:
                    self.logger.log_info(f"File processing completed successfully: {file_path}")
                else:
                    self.logger.log_error(f"File processing failed: {result.error_message}")
                
                # Remove from recent files after successful processing
                with self._recent_files_lock:
                    self._recent_files.discard(file_path)
                
                return
                
            except Exception as e:
                if check == max_stability_checks - 1:
                    # Final attempt failed
                    error_msg = f"File processing failed after {max_stability_checks} attempts: {file_path}: {str(e)}"
                    self.logger.log_error(error_msg, e)
                    self.stats['processing_errors'] += 1
                else:
                    # Retry after brief delay
                    self.logger.log_error(f"File processing attempt {check + 1} failed, retrying: {e}")
                    time.sleep(stability_delay * (check + 1))
    
    def _wait_for_file_stability(self, file_path: str, delay: float) -> bool:
        """
        Wait for file to become stable (fully written).
        
        Args:
            file_path: Path to check
            delay: Delay between checks
            
        Returns:
            bool: True if file appears stable
        """
        try:
            if not os.path.exists(file_path):
                return False
            
            # Get initial file size
            initial_size = os.path.getsize(file_path)
            time.sleep(delay)
            
            # Check if size changed
            if not os.path.exists(file_path):
                return False
            
            final_size = os.path.getsize(file_path)
            return initial_size == final_size
            
        except OSError:
            return False
    
    def _validate_file_ready(self, file_path: str) -> bool:
        """
        Validate that file exists and is ready for processing.
        
        Args:
            file_path: Path to validate
            
        Returns:
            bool: True if file is ready
        """
        try:
            if not os.path.exists(file_path):
                self.logger.log_error(f"File no longer exists: {file_path}")
                return False
            
            if not os.path.isfile(file_path):
                self.logger.log_error(f"Path is not a file: {file_path}")
                return False
            
            # Test basic read access
            with open(file_path, 'rb') as f:
                f.read(1)  # Try to read one byte
            
            return True
            
        except (OSError, PermissionError) as e:
            self.logger.log_error(f"File not ready for processing: {file_path}: {e}")
            return False
    
    def get_stats(self) -> dict:
        """Get event handler statistics."""
        return self.stats.copy()


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
        Start file system event monitoring with resilience.
        
        Sets up recursive monitoring of the source folder and starts the observer.
        Includes validation and error recovery mechanisms.
        
        Raises:
            RuntimeError: If monitoring fails to start after retries
        """
        max_attempts = 3
        base_delay = 1.0
        
        for attempt in range(max_attempts):
            try:
                if self.observer is None:
                    raise RuntimeError("Observer not initialized")
                
                # Validate source folder is still accessible
                if not self.source_folder.exists():
                    raise RuntimeError(f"Source folder no longer exists: {self.source_folder}")
                
                if not self.source_folder.is_dir():
                    raise RuntimeError(f"Source path is not a directory: {self.source_folder}")
                
                # Test read access to source folder
                if not os.access(self.source_folder, os.R_OK):
                    raise PermissionError(f"No read access to source folder: {self.source_folder}")
                
                # Schedule recursive monitoring of the source folder
                self.observer.schedule(
                    self.event_handler,
                    str(self.source_folder),
                    recursive=True
                )
                
                # Start the observer
                self.observer.start()
                
                # Verify observer started successfully
                time.sleep(0.1)  # Brief delay to let observer initialize
                if not self.observer.is_alive():
                    raise RuntimeError("Observer failed to start properly")
                
                self.logger.log_info(f"Started monitoring folder: {self.source_folder}")
                return
                
            except Exception as e:
                if attempt == max_attempts - 1:
                    error_msg = f"Failed to start file system monitoring after {max_attempts} attempts: {str(e)}"
                    self.logger.log_error(error_msg, e)
                    raise RuntimeError(error_msg) from e
                else:
                    self.logger.log_error(f"Monitoring start attempt {attempt + 1} failed, retrying: {e}")
                    time.sleep(base_delay * (attempt + 1))
                    
                    # Recreate observer for retry
                    if self.observer:
                        try:
                            self.observer.stop()
                        except Exception:
                            pass
                    self.observer = Observer()
    
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
        Check if monitoring is currently active with health validation.
        
        Returns:
            bool: True if monitoring is active and healthy, False otherwise
        """
        if self.observer is None:
            return False
        
        if not self.observer.is_alive():
            return False
        
        # Additional health checks
        try:
            # Verify source folder is still accessible
            if not self.source_folder.exists() or not self.source_folder.is_dir():
                self.logger.log_error(f"Source folder is no longer accessible: {self.source_folder}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.log_error(f"Health check failed for file monitor: {e}")
            return False
    
    def get_monitoring_stats(self) -> dict:
        """
        Get comprehensive monitoring statistics.
        
        Returns:
            dict: Statistics about monitoring and processing
        """
        stats = {
            'is_monitoring': self.is_monitoring(),
            'source_folder': str(self.source_folder),
            'observer_alive': self.observer.is_alive() if self.observer else False
        }
        
        # Add event handler stats if available
        if self.event_handler:
            stats.update(self.event_handler.get_stats())
        
        return stats
    
    def __enter__(self):
        """Context manager entry."""
        self.start_monitoring()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop_monitoring()