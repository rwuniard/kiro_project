"""
File Monitor module for file system event monitoring.

This module contains the FileMonitor class that uses the watchdog library
to monitor file system events and trigger file processing when new files are created.
"""

import os
import time
import threading
from pathlib import Path
from typing import Optional, Set, List
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
        Handle file and directory creation events with comprehensive error handling.
        
        Args:
            event: FileSystemEvent representing the file or directory creation
        """
        self.stats['events_received'] += 1
        
        event_path = event.src_path
        
        try:
            # Debug: Log event details
            self.logger.log_info(f"Event received: {event_path} (is_directory: {event.is_directory})")
            
            # Check if it's actually a directory (secondary check for Docker volume issues)
            is_actually_directory = os.path.isdir(event_path)
            
            # Handle directory creation - recursively process all files within
            if event.is_directory or is_actually_directory:
                if is_actually_directory and not event.is_directory:
                    self.logger.log_info(f"Directory detected via filesystem check (event.is_directory was False): {event_path}")
                else:
                    self.logger.log_info(f"New directory detected: {event_path}")
                self._process_directory_recursively(event_path)
                return
            
            # Handle file creation
            # Filter duplicate events
            if self._is_duplicate_event(event_path):
                self.stats['duplicate_events_filtered'] += 1
                return
            
            # Check if file should be ignored (import FileProcessor for the check)
            from src.core.file_processor import FileProcessor
            if FileProcessor.should_ignore_file(event_path):
                filename = os.path.basename(event_path)
                
                # Check if this is a system file that should be automatically deleted
                if FileProcessor.should_delete_system_file(event_path):
                    try:
                        os.remove(event_path)
                        self.logger.log_info(f"Automatically deleted system file: {filename}")
                    except Exception as e:
                        self.logger.log_error(f"Failed to delete system file {filename}: {str(e)}")
                else:
                    self.logger.log_info(f"Ignoring system/temporary file: {filename}")
                return
            
            # Log the file creation event
            self.logger.log_info(f"New file detected: {event_path}")
            
            # Process the file with resilience
            self._process_file_with_resilience(event_path)
            
        except Exception as e:
            self.stats['processing_errors'] += 1
            error_msg = f"Critical error in event handler for {event_path}: {str(e)}"
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
                # If it's a directory, handle it with recursive processing
                if os.path.isdir(file_path):
                    self.logger.log_info(f"Directory found during file validation, processing recursively: {file_path}")
                    self._process_directory_recursively(file_path)
                    return False  # Don't continue with file processing
                else:
                    self.logger.log_error(f"Path is not a file: {file_path}")
                    return False
            
            # Test basic read access
            with open(file_path, 'rb') as f:
                f.read(1)  # Try to read one byte
            
            return True
            
        except (OSError, PermissionError) as e:
            self.logger.log_error(f"File not ready for processing: {file_path}: {e}")
            return False
    
    def _process_directory_recursively(self, directory_path: str) -> None:
        """
        Process all files in a directory recursively.
        
        This method is called when a new directory is detected and will
        find and process all files within the directory and subdirectories.
        
        Args:
            directory_path: Path to the directory to process
        """
        try:
            from pathlib import Path
            dir_path = Path(directory_path)
            
            self.logger.log_info(f"Starting recursive processing of directory: {directory_path}")
            
            if not dir_path.exists():
                self.logger.log_error(f"Directory no longer exists: {directory_path}")
                return
                
            if not dir_path.is_dir():
                self.logger.log_error(f"Path is not a directory: {directory_path}")
                return
            
            processed_count = 0
            found_files = []
            
            # Retry mechanism for Docker volumes where files may still be copying
            max_retries = 3
            retry_delay = 0.5  # 500ms between retries
            
            for attempt in range(max_retries):
                found_files.clear()
                
                # Scan directory contents
                self.logger.log_info(f"Scanning directory contents (attempt {attempt + 1}): {directory_path}")
                for item in dir_path.rglob('*'):
                    if item.is_file():
                        found_files.append(item)
                        self.logger.log_info(f"Found file: {item.relative_to(dir_path)}")
                    elif item.is_dir():
                        self.logger.log_info(f"Found subdirectory: {item.relative_to(dir_path)}")
                
                self.logger.log_info(f"Files found on attempt {attempt + 1}: {len(found_files)}")
                
                # If we found files, break out of retry loop
                if found_files:
                    break
                    
                # If this isn't the last attempt, wait before retrying
                if attempt < max_retries - 1:
                    self.logger.log_info(f"No files found, waiting {retry_delay}s before retry...")
                    import time
                    time.sleep(retry_delay)
                    retry_delay *= 1.5  # Exponential backoff
            
            self.logger.log_info(f"Total files found in directory after {max_retries} attempts: {len(found_files)}")
            
            # Now process each file
            for file_path in found_files:
                try:
                    file_path_str = str(file_path)
                    
                    # Skip duplicate processing
                    if self._is_duplicate_event(file_path_str):
                        self.stats['duplicate_events_filtered'] += 1
                        self.logger.log_info(f"Skipping duplicate: {file_path.relative_to(dir_path)}")
                        continue
                    
                    # Check if file should be ignored
                    from src.core.file_processor import FileProcessor
                    if FileProcessor.should_ignore_file(file_path_str):
                        relative_path = file_path.relative_to(dir_path)
                        
                        # Check if this is a system file that should be automatically deleted
                        if FileProcessor.should_delete_system_file(file_path_str):
                            try:
                                os.remove(file_path_str)
                                self.logger.log_info(f"Automatically deleted system file: {relative_path}")
                            except Exception as e:
                                self.logger.log_error(f"Failed to delete system file {relative_path}: {str(e)}")
                        else:
                            self.logger.log_info(f"Ignoring system/temporary file: {relative_path}")
                        continue
                    
                    relative_path = file_path.relative_to(dir_path)
                    self.logger.log_info(f"Processing file from directory: {relative_path}")
                    
                    # Process the file
                    self._process_file_with_resilience(file_path_str)
                    processed_count += 1
                    
                except Exception as e:
                    self.logger.log_error(f"Error processing file {file_path} from directory: {e}")
                    self.stats['processing_errors'] += 1
            
            if processed_count > 0:
                self.logger.log_info(f"Successfully processed {processed_count} files from directory: {directory_path}")
            else:
                self.logger.log_error(f"No files were processed from directory: {directory_path} (found {len(found_files)} files)")
                
        except Exception as e:
            self.logger.log_error(f"Error processing directory {directory_path}: {e}")
            self.stats['processing_errors'] += 1
    
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
                
                # Perform initial scans
                self._perform_initial_file_scan()
                self._perform_initial_empty_folder_scan()
                
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
                        except Exception as stop_error:
                            self.logger_service.log_warning(f"Failed to stop observer during retry: {stop_error}")
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
    
    def scan_for_empty_folders(self) -> List[str]:
        """
        Scan the source folder for completely empty folders.
        
        Returns:
            List[str]: List of paths to completely empty folders found
        """
        empty_folders = []
        
        try:
            # Get FileManager instance from FileProcessor
            file_manager = getattr(self.file_processor, 'file_manager', None)
            if not file_manager:
                self.logger.log_error("FileManager not available for empty folder detection")
                return empty_folders
            
            # Recursively scan for empty folders
            for root, dirs, files in os.walk(self.source_folder):
                # Check each directory
                for dir_name in dirs:
                    dir_path = os.path.join(root, dir_name)
                    if file_manager.should_process_as_empty_folder(dir_path):
                        empty_folders.append(dir_path)
                        self.logger.log_info(f"Found completely empty folder: {dir_path}")
            
        except Exception as e:
            self.logger.log_error(f"Error scanning for empty folders: {e}")
        
        return empty_folders
    
    def handle_empty_folders(self) -> int:
        """
        Detect and handle completely empty folders in the source directory.
        
        Returns:
            int: Number of empty folders processed
        """
        processed_count = 0
        
        try:
            empty_folders = self.scan_for_empty_folders()
            
            for folder_path in empty_folders:
                try:
                    # Process the empty folder through FileProcessor
                    result = self.file_processor.process_empty_folder(folder_path)
                    if result.success:
                        processed_count += 1
                        self.logger.log_info(f"Successfully processed empty folder: {folder_path}")
                    else:
                        self.logger.log_error(f"Failed to process empty folder: {result.error_message}")
                        
                except Exception as e:
                    self.logger.log_error(f"Error processing empty folder {folder_path}: {e}")
            
        except Exception as e:
            self.logger.log_error(f"Error in empty folder handling: {e}")
        
        return processed_count
    
    def _perform_initial_empty_folder_scan(self) -> None:
        """
        Perform initial scan for empty folders when monitoring starts.
        
        This ensures that any empty folders present when monitoring begins
        are detected and handled appropriately.
        """
        try:
            self.logger.log_info("Performing initial scan for completely empty folders")
            processed_count = self.handle_empty_folders()
            
            if processed_count > 0:
                self.logger.log_info(f"Initial scan processed {processed_count} completely empty folders")
            else:
                self.logger.log_info("Initial scan found no completely empty folders")
                
        except Exception as e:
            self.logger.log_error(f"Error during initial empty folder scan: {e}")
            # Don't fail monitoring startup due to empty folder scan issues
    
    def _perform_initial_file_scan(self) -> None:
        """
        Perform initial scan for existing files when monitoring starts.
        
        This ensures that any files present when monitoring begins are processed
        immediately, not just files created after the application starts.
        """
        try:
            self.logger.log_info("Performing initial scan for existing files")
            processed_count = self._process_existing_files()
            
            if processed_count > 0:
                self.logger.log_info(f"Initial scan processed {processed_count} existing files")
            else:
                self.logger.log_info("Initial scan found no files to process")
                
        except Exception as e:
            self.logger.log_error(f"Error during initial file scan: {e}")
            # Don't fail monitoring startup due to initial file scan issues
    
    def _process_existing_files(self) -> int:
        """
        Recursively scan source folder and process all existing files.
        
        Returns:
            int: Number of files processed
        """
        processed_count = 0
        
        try:
            source_path = Path(self.source_folder)
            
            if not source_path.exists():
                self.logger.log_error(f"Source folder does not exist: {self.source_folder}")
                return 0
            
            # Recursively find all files in source directory
            for file_path in source_path.rglob('*'):
                if file_path.is_file():
                    try:
                        file_path_str = str(file_path)
                        
                        # Check if file should be ignored
                        from src.core.file_processor import FileProcessor
                        if FileProcessor.should_ignore_file(file_path_str):
                            relative_path = file_path.relative_to(source_path)
                            
                            # Check if this is a system file that should be automatically deleted
                            if FileProcessor.should_delete_system_file(file_path_str):
                                try:
                                    os.remove(file_path_str)
                                    self.logger.log_info(f"Automatically deleted system file during scan: {relative_path}")
                                except Exception as e:
                                    self.logger.log_error(f"Failed to delete system file {relative_path} during scan: {str(e)}")
                            else:
                                self.logger.log_info(f"Ignoring system/temporary file during scan: {relative_path}")
                            continue
                        
                        self.logger.log_info(f"Processing existing file: {file_path.relative_to(source_path)}")
                        
                        # Process the file using the same logic as file events
                        self.file_processor.process_file(file_path_str)
                        processed_count += 1
                        
                    except Exception as e:
                        self.logger.log_error(f"Error processing existing file {file_path}: {e}")
                        # Continue processing other files even if one fails
            
        except Exception as e:
            self.logger.log_error(f"Error scanning existing files: {e}")
        
        return processed_count
    
    def trigger_existing_files_scan(self) -> int:
        """
        Manually trigger a scan and processing of existing files.
        
        This can be called on demand to process files that may have been missed
        or to reprocess files in the source directory.
        
        Returns:
            int: Number of files processed
        """
        try:
            self.logger.log_info("Manual existing files scan triggered")
            processed_count = self._process_existing_files()
            
            if processed_count > 0:
                self.logger.log_info(f"Manual scan processed {processed_count} existing files")
            
            return processed_count
            
        except Exception as e:
            self.logger.log_error(f"Error during manual existing files scan: {e}")
            return 0
    
    def trigger_empty_folder_check(self) -> int:
        """
        Manually trigger a check for empty folders.
        
        This can be called periodically or on demand to ensure empty folders
        are detected and handled even if they weren't caught by file events.
        
        Returns:
            int: Number of empty folders processed
        """
        try:
            self.logger.log_info("Manual empty folder check triggered")
            processed_count = self.handle_empty_folders()
            
            if processed_count > 0:
                self.logger.log_info(f"Manual check processed {processed_count} completely empty folders")
            
            return processed_count
            
        except Exception as e:
            self.logger.log_error(f"Error during manual empty folder check: {e}")
            return 0