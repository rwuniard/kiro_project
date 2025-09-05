"""
Polling-based file monitor for environments where file system events don't work reliably.

This module provides a polling-based alternative to the watchdog-based FileMonitor
for Docker volumes and other environments where file system events aren't properly
propagated.
"""

import os
import time
import threading
from pathlib import Path
from typing import Dict, Set, Optional, List
from dataclasses import dataclass

from src.services.logger_service import LoggerService
from src.core.file_processor import FileProcessor


@dataclass
class FileState:
    """Represents the state of a file for polling comparison."""
    path: str
    mtime: float
    size: int
    
    @classmethod
    def from_file(cls, file_path: str) -> Optional['FileState']:
        """Create FileState from a file path, returns None if file doesn't exist."""
        try:
            stat = os.stat(file_path)
            return cls(
                path=file_path,
                mtime=stat.st_mtime,
                size=stat.st_size
            )
        except (OSError, FileNotFoundError):
            return None
    
    def has_changed(self, other: Optional['FileState']) -> bool:
        """Check if this file state represents a change from another state."""
        if other is None:
            return True  # New file
        return self.mtime != other.mtime or self.size != other.size


class PollingFileMonitor:
    """
    Polling-based file monitor for Docker volumes and other environments 
    where file system events don't work reliably.
    
    Uses periodic directory scanning to detect new and modified files,
    providing the same interface as the watchdog-based FileMonitor.
    """
    
    def __init__(self, source_folder: str, file_processor: FileProcessor, 
                 logger_service: LoggerService, polling_interval: float = 3.0,
                 docker_optimized: bool = False):
        """
        Initialize PollingFileMonitor.
        
        Args:
            source_folder: Path to the folder to monitor
            file_processor: FileProcessor instance for processing files
            logger_service: LoggerService instance for logging
            polling_interval: Seconds between polls (default: 3.0)
            docker_optimized: Enable Docker-specific optimizations
            
        Raises:
            ValueError: If source folder doesn't exist or is not a directory
        """
        self.source_folder = Path(source_folder).resolve()
        self.file_processor = file_processor
        self.logger = logger_service
        self.polling_interval = max(0.5, polling_interval)  # Minimum 0.5 seconds
        self.docker_optimized = docker_optimized
        
        # Validate source folder
        if not self.source_folder.exists():
            raise ValueError(f"Source folder does not exist: {self.source_folder}")
        
        if not self.source_folder.is_dir():
            raise ValueError(f"Source path is not a directory: {self.source_folder}")
        
        # Monitoring state
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # Track files currently being processed to avoid double-processing
        self._processing_files: Set[str] = set()
        self._processing_lock = threading.Lock()
        
        # Statistics
        self.stats = {
            'polling_cycles': 0,
            'files_scanned': 0,
            'new_files_detected': 0,
            'modified_files_detected': 0,
            'files_processed': 0,
            'processing_errors': 0,
            'polling_errors': 0,
            'last_poll_time': 0.0,
            'last_poll_duration': 0.0
        }
        
        # Docker optimizations
        if self.docker_optimized:
            # Reduce polling interval for Docker volumes (more responsive)
            self.polling_interval = max(1.0, self.polling_interval * 0.8)
            self.logger.log_info(f"Docker optimizations enabled, polling interval: {self.polling_interval}s")
    
    def start_monitoring(self) -> None:
        """
        Start polling-based file monitoring.
        
        Creates and starts the monitoring thread that will poll the source
        folder at regular intervals.
        
        Raises:
            RuntimeError: If monitoring is already active or fails to start
        """
        if self._monitoring:
            raise RuntimeError("Monitoring is already active")
        
        try:
            # Validate source folder is still accessible
            if not self.source_folder.exists():
                raise RuntimeError(f"Source folder no longer exists: {self.source_folder}")
            
            if not self.source_folder.is_dir():
                raise RuntimeError(f"Source path is not a directory: {self.source_folder}")
            
            # Test read access to source folder
            if not os.access(self.source_folder, os.R_OK):
                raise PermissionError(f"No read access to source folder: {self.source_folder}")
            
            # Clear stop event and start monitoring
            self._stop_event.clear()
            self._monitoring = True
            
            # Create and start monitoring thread
            self._monitor_thread = threading.Thread(
                target=self._monitoring_loop,
                name="PollingFileMonitor",
                daemon=True
            )
            self._monitor_thread.start()
            
            self.logger.log_info(f"Started polling file monitor on: {self.source_folder} "
                               f"(interval: {self.polling_interval}s, docker_optimized: {self.docker_optimized})")
            
            self.logger.log_info("Polling monitor started successfully")
            
        except Exception as e:
            self._monitoring = False
            error_msg = f"Failed to start polling file monitor: {str(e)}"
            self.logger.log_error(error_msg, e)
            raise RuntimeError(error_msg) from e
    
    def stop_monitoring(self) -> None:
        """
        Stop polling-based file monitoring.
        
        Signals the monitoring thread to stop and waits for it to finish.
        """
        if not self._monitoring:
            return
        
        try:
            # Signal stop and wait for thread
            self._stop_event.set()
            self._monitoring = False
            
            if self._monitor_thread and self._monitor_thread.is_alive():
                self._monitor_thread.join(timeout=self.polling_interval * 2)
                
                if self._monitor_thread.is_alive():
                    self.logger.log_error("Monitoring thread did not stop gracefully within timeout")
                else:
                    self.logger.log_info("Polling file monitoring stopped")
            
        except Exception as e:
            error_msg = f"Error stopping polling file monitor: {str(e)}"
            self.logger.log_error(error_msg, e)
    
    def is_monitoring(self) -> bool:
        """
        Check if monitoring is currently active.
        
        Returns:
            bool: True if monitoring is active, False otherwise
        """
        if not self._monitoring:
            return False
        
        if not self._monitor_thread or not self._monitor_thread.is_alive():
            return False
        
        # Additional health checks
        try:
            # Verify source folder is still accessible
            if not self.source_folder.exists() or not self.source_folder.is_dir():
                self.logger.log_error(f"Source folder is no longer accessible: {self.source_folder}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.log_error(f"Health check failed for polling monitor: {e}")
            return False
    
    def get_monitoring_stats(self) -> dict:
        """
        Get comprehensive monitoring statistics.
        
        Returns:
            dict: Statistics about monitoring and processing
        """
        stats = self.stats.copy()
        stats.update({
            'is_monitoring': self.is_monitoring(),
            'source_folder': str(self.source_folder),
            'polling_interval': self.polling_interval,
            'docker_optimized': self.docker_optimized,
            'thread_alive': self._monitor_thread.is_alive() if self._monitor_thread else False,
            'files_being_processed': len(self._processing_files)
        })
        
        return stats
    
    def _monitoring_loop(self) -> None:
        """Main monitoring loop that runs in a separate thread."""
        self.logger.log_info("Polling monitoring loop started")
        
        while not self._stop_event.is_set():
            try:
                poll_start = time.time()
                
                # Perform polling cycle
                self._poll_directory()
                
                poll_end = time.time()
                self.stats['last_poll_time'] = poll_end
                self.stats['last_poll_duration'] = poll_end - poll_start
                self.stats['polling_cycles'] += 1
                
                # Wait for next polling interval or stop signal
                self._stop_event.wait(self.polling_interval)
                
            except Exception as e:
                self.stats['polling_errors'] += 1
                self.logger.log_error(f"Error in polling monitoring loop: {e}")
                
                # Brief pause before continuing to avoid tight error loops
                self._stop_event.wait(min(1.0, self.polling_interval))
        
        self.logger.log_info("Polling monitoring loop stopped")
    
    def _poll_directory(self) -> None:
        """Poll the source directory for file changes."""
        try:
            files_to_process = []
            
            # Scan directory recursively - process ALL files found
            # Since processed files are moved out, any file in source needs processing
            # But skip files currently being processed
            for file_path in self.source_folder.rglob('*'):
                if file_path.is_file():
                    file_path_str = str(file_path)
                    self.stats['files_scanned'] += 1
                    
                    # Check if file should be ignored (system/temp files)
                    if FileProcessor.should_ignore_file(file_path_str):
                        self.logger.log_info(f"Ignoring system/temporary file: {file_path.relative_to(self.source_folder)}")
                        continue
                    
                    # Skip files currently being processed
                    with self._processing_lock:
                        if file_path_str in self._processing_files:
                            self.logger.log_info(f"File already being processed, skipping: {file_path.relative_to(self.source_folder)}")
                            continue
                    
                    files_to_process.append(file_path_str)
                    self.logger.log_info(f"Found file to process: {file_path.relative_to(self.source_folder)}")
            
            # Process all files found
            if files_to_process:
                self.stats['new_files_detected'] += len(files_to_process)
                
                if self.docker_optimized and len(files_to_process) > 1:
                    # Docker optimization: process files in batches
                    self._process_files_batch(files_to_process)
                else:
                    # Process files individually
                    for file_path in files_to_process:
                        self._process_file(file_path)
            
        except Exception as e:
            self.stats['polling_errors'] += 1
            self.logger.log_error(f"Error during directory polling: {e}")
    
    def _process_file(self, file_path: str) -> None:
        """Process a single file through the file processor."""
        try:
            # Mark file as being processed
            with self._processing_lock:
                self._processing_files.add(file_path)
            
            try:
                # Wait for file stability (similar to watchdog monitor)
                if not self._wait_for_file_stability(file_path):
                    return
                
                # Process the file
                result = self.file_processor.process_file(file_path)
                self.stats['files_processed'] += 1
                
                if result.success:
                    self.logger.log_info(f"File processing completed: {Path(file_path).relative_to(self.source_folder)}")
                else:
                    self.logger.log_error(f"File processing failed: {result.error_message}")
            
            finally:
                # Always remove file from processing set when done
                with self._processing_lock:
                    self._processing_files.discard(file_path)
            
        except Exception as e:
            self.stats['processing_errors'] += 1
            self.logger.log_error(f"Error processing file {file_path}: {e}")
            # Ensure we remove from processing set even on error
            with self._processing_lock:
                self._processing_files.discard(file_path)
    
    def _process_files_batch(self, file_paths: List[str]) -> None:
        """Process multiple files in a batch (Docker optimization)."""
        if not file_paths:
            return
        
        self.logger.log_info(f"Processing batch of {len(file_paths)} files")
        
        # Mark all files as being processed
        with self._processing_lock:
            for file_path in file_paths:
                self._processing_files.add(file_path)
        
        try:
            # Wait for all files to be stable
            stable_files = []
            for file_path in file_paths:
                if self._wait_for_file_stability(file_path):
                    stable_files.append(file_path)
            
            # Process stable files
            for file_path in stable_files:
                try:
                    result = self.file_processor.process_file(file_path)
                    self.stats['files_processed'] += 1
                    
                    if result.success:
                        self.logger.log_info(f"Batch file processed: {Path(file_path).relative_to(self.source_folder)}")
                    else:
                        self.logger.log_error(f"Batch file processing failed: {result.error_message}")
                    
                except Exception as e:
                    self.stats['processing_errors'] += 1
                    self.logger.log_error(f"Error in batch processing file {file_path}: {e}")
        
        finally:
            # Always remove all files from processing set when done
            with self._processing_lock:
                for file_path in file_paths:
                    self._processing_files.discard(file_path)
    
    def _wait_for_file_stability(self, file_path: str, stability_delay: float = 0.5) -> bool:
        """
        Wait for file to become stable (fully written).
        
        Args:
            file_path: Path to check
            stability_delay: Delay between stability checks
            
        Returns:
            bool: True if file appears stable
        """
        try:
            if not os.path.exists(file_path):
                return False
            
            # Get initial file size
            initial_size = os.path.getsize(file_path)
            time.sleep(stability_delay)
            
            # Check if size changed
            if not os.path.exists(file_path):
                return False
            
            final_size = os.path.getsize(file_path)
            return initial_size == final_size
            
        except OSError:
            return False
    
    def trigger_manual_scan(self) -> int:
        """
        Manually trigger a scan for new files (similar to existing FileMonitor API).
        
        This processes any files that are currently in the source directory,
        regardless of their previous state.
        
        Returns:
            int: Number of files processed
        """
        try:
            self.logger.log_info("Manual scan triggered")
            processed_count = 0
            
            for file_path in self.source_folder.rglob('*'):
                if file_path.is_file():
                    try:
                        file_path_str = str(file_path)
                        
                        # Check if file should be ignored (system/temp files)
                        if FileProcessor.should_ignore_file(file_path_str):
                            self.logger.log_info(f"Ignoring system/temporary file during manual scan: {file_path.relative_to(self.source_folder)}")
                            continue
                        
                        self.logger.log_info(f"Processing existing file: {file_path.relative_to(self.source_folder)}")
                        
                        result = self.file_processor.process_file(file_path_str)
                        if result.success:
                            processed_count += 1
                        
                    except Exception as e:
                        self.logger.log_error(f"Error in manual scan processing {file_path}: {e}")
            
            self.logger.log_info(f"Manual scan processed {processed_count} files")
            return processed_count
            
        except Exception as e:
            self.logger.log_error(f"Error during manual scan: {e}")
            return 0
    
    def __enter__(self):
        """Context manager entry."""
        self.start_monitoring()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop_monitoring()