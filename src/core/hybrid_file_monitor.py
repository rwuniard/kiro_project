"""
Hybrid file monitor that automatically selects between event-based and polling-based monitoring.

This module provides intelligent file monitoring that works reliably in both native 
environments and Docker containers with volume mounts. It automatically detects the 
environment and chooses the optimal monitoring strategy.
"""

import os
import time
import threading
from typing import Optional, Dict, Any
from pathlib import Path

from src.services.logger_service import LoggerService
from src.core.file_processor import FileProcessor
from src.core.file_monitor import FileMonitor
from src.core.polling_file_monitor import PollingFileMonitor


class EnvironmentDetector:
    """Detects the runtime environment and recommends optimal monitoring strategy."""
    
    @staticmethod
    def is_docker_environment() -> bool:
        """
        Detect if running inside a Docker container.
        
        Returns:
            bool: True if running in Docker, False otherwise
        """
        # Check for Docker-specific files and environment variables
        docker_indicators = [
            # Docker creates this file in containers
            Path('/.dockerenv').exists(),
            
            # Docker sets this environment variable
            os.getenv('DOCKER_CONTAINER') is not None,
            
            # Check if we're in a container via cgroup
            EnvironmentDetector._check_cgroup_docker(),
            
            # Check for Docker-specific init process
            EnvironmentDetector._check_docker_init(),
        ]
        
        return any(docker_indicators)
    
    @staticmethod
    def _check_cgroup_docker() -> bool:
        """Check if cgroup indicates Docker container."""
        try:
            with open('/proc/1/cgroup', 'r') as f:
                content = f.read()
                return 'docker' in content or 'containerd' in content
        except (FileNotFoundError, PermissionError, OSError):
            return False
    
    @staticmethod
    def _check_docker_init() -> bool:
        """Check if init process indicates Docker."""
        try:
            with open('/proc/1/comm', 'r') as f:
                init_process = f.read().strip()
                # Common Docker init processes
                docker_inits = ['docker-init', 'tini', 'dumb-init', 'su-exec']
                return init_process in docker_inits
        except (FileNotFoundError, PermissionError, OSError):
            return False
    
    @staticmethod
    def test_file_events_work(source_folder: str, timeout: float = 5.0) -> bool:
        """
        Test if file system events work properly in the given folder.
        
        This creates a temporary file and checks if watchdog can detect it.
        
        Args:
            source_folder: Path to test
            timeout: Timeout for the test in seconds
            
        Returns:
            bool: True if events work, False otherwise
        """
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
        
        try:
            source_path = Path(source_folder)
            if not source_path.exists() or not source_path.is_dir():
                return False
            
            # Test file for event detection
            test_file = source_path / f'.hybrid_monitor_test_{int(time.time())}.tmp'
            event_detected = threading.Event()
            
            class TestHandler(FileSystemEventHandler):
                def on_created(self, event):
                    if not event.is_directory and event.src_path == str(test_file):
                        event_detected.set()
            
            # Set up observer
            observer = Observer()
            handler = TestHandler()
            observer.schedule(handler, str(source_path), recursive=False)
            observer.start()
            
            try:
                # Brief delay to ensure observer is ready
                time.sleep(0.1)
                
                # Create test file
                test_file.touch()
                
                # Wait for event detection
                event_was_detected = event_detected.wait(timeout)
                
                return event_was_detected
                
            finally:
                observer.stop()
                observer.join(timeout=2.0)
                
                # Clean up test file
                try:
                    if test_file.exists():
                        test_file.unlink()
                except OSError:
                    pass
                    
        except Exception:
            return False
    
    @classmethod
    def recommend_monitoring_mode(cls, source_folder: str, user_preference: str = "auto") -> str:
        """
        Recommend optimal monitoring mode based on environment detection.
        
        Args:
            source_folder: Path to monitor
            user_preference: User's preferred mode ("auto", "events", "polling")
            
        Returns:
            str: Recommended mode ("events" or "polling")
        """
        if user_preference in ["events", "polling"]:
            return user_preference
        
        # Auto-detection logic
        if cls.is_docker_environment():
            # In Docker environments, always use polling for reliability
            # Docker volumes often have issues with directory events and file system event propagation
            return "polling"
        else:
            # Native environment, prefer events with fallback
            if cls.test_file_events_work(source_folder, timeout=2.0):
                return "events"
            else:
                return "polling"


class HybridFileMonitor:
    """
    Hybrid file monitor that automatically selects the optimal monitoring strategy.
    
    Provides a unified interface that automatically chooses between watchdog-based
    event monitoring and polling-based monitoring based on the environment and
    what actually works.
    """
    
    def __init__(self, source_folder: str, file_processor: FileProcessor,
                 logger_service: LoggerService, monitoring_mode: str = "auto",
                 polling_interval: float = 3.0, docker_volume_mode: bool = False):
        """
        Initialize HybridFileMonitor.
        
        Args:
            source_folder: Path to the folder to monitor
            file_processor: FileProcessor instance for processing files
            logger_service: LoggerService instance for logging
            monitoring_mode: "auto", "events", or "polling"
            polling_interval: Polling interval if using polling mode
            docker_volume_mode: Enable Docker volume optimizations
        """
        self.source_folder = source_folder
        self.file_processor = file_processor
        self.logger = logger_service
        self.monitoring_mode = monitoring_mode
        self.polling_interval = polling_interval
        self.docker_volume_mode = docker_volume_mode
        
        # Active monitor instance
        self._active_monitor: Optional[FileMonitor | PollingFileMonitor] = None
        self._selected_mode: Optional[str] = None
        
        # Environment detection
        self._is_docker = EnvironmentDetector.is_docker_environment()
        
        # Monitor health checking
        self._health_check_interval = 30.0  # seconds
        self._health_thread: Optional[threading.Thread] = None
        self._health_stop_event = threading.Event()
        self._fallback_attempted = False
    
    def start_monitoring(self) -> None:
        """
        Start hybrid file monitoring.
        
        Automatically selects and starts the optimal monitoring strategy
        based on environment detection and configuration.
        
        Raises:
            RuntimeError: If monitoring fails to start
        """
        try:
            # Determine monitoring mode
            self._selected_mode = EnvironmentDetector.recommend_monitoring_mode(
                self.source_folder, 
                self.monitoring_mode
            )
            
            self.logger.log_info(f"Hybrid monitor selected mode: {self._selected_mode} "
                               f"(docker: {self._is_docker}, user_pref: {self.monitoring_mode})")
            
            # Create and start appropriate monitor
            self._start_selected_monitor()
            
            # Start health monitoring
            self._start_health_monitoring()
            
        except Exception as e:
            error_msg = f"Failed to start hybrid file monitoring: {str(e)}"
            self.logger.log_error(error_msg, e)
            raise RuntimeError(error_msg) from e
    
    def stop_monitoring(self) -> None:
        """Stop hybrid file monitoring and cleanup resources."""
        try:
            # Stop health monitoring
            self._stop_health_monitoring()
            
            # Stop active monitor
            if self._active_monitor:
                self._active_monitor.stop_monitoring()
                self._active_monitor = None
            
            self.logger.log_info("Hybrid file monitoring stopped")
            
        except Exception as e:
            error_msg = f"Error stopping hybrid file monitoring: {str(e)}"
            self.logger.log_error(error_msg, e)
    
    def is_monitoring(self) -> bool:
        """
        Check if monitoring is currently active and healthy.
        
        Returns:
            bool: True if monitoring is active and healthy
        """
        if self._active_monitor is None:
            return False
        
        return self._active_monitor.is_monitoring()
    
    def get_monitoring_stats(self) -> dict:
        """
        Get comprehensive monitoring statistics.
        
        Returns:
            dict: Statistics about monitoring and processing
        """
        base_stats = {
            'hybrid_mode': True,
            'selected_mode': self._selected_mode,
            'is_docker_environment': self._is_docker,
            'docker_volume_mode': self.docker_volume_mode,
            'fallback_attempted': self._fallback_attempted,
            'source_folder': self.source_folder
        }
        
        if self._active_monitor:
            monitor_stats = self._active_monitor.get_monitoring_stats()
            base_stats.update(monitor_stats)
        
        return base_stats
    
    def trigger_manual_scan(self) -> int:
        """
        Manually trigger a scan for existing files.
        
        Returns:
            int: Number of files processed
        """
        if self._active_monitor is None:
            return 0
        
        if hasattr(self._active_monitor, 'trigger_manual_scan'):
            return self._active_monitor.trigger_manual_scan()
        elif hasattr(self._active_monitor, 'trigger_existing_files_scan'):
            return self._active_monitor.trigger_existing_files_scan()
        
        return 0
    
    def _start_selected_monitor(self) -> None:
        """Start the monitor based on selected mode."""
        if self._selected_mode == "events":
            self._active_monitor = FileMonitor(
                self.source_folder,
                self.file_processor,
                self.logger
            )
        elif self._selected_mode == "polling":
            self._active_monitor = PollingFileMonitor(
                self.source_folder,
                self.file_processor,
                self.logger,
                polling_interval=self.polling_interval,
                docker_optimized=self.docker_volume_mode
            )
        else:
            raise ValueError(f"Invalid monitoring mode: {self._selected_mode}")
        
        self._active_monitor.start_monitoring()
        
        self.logger.log_info(f"Started {self._selected_mode} monitor successfully")
    
    def _start_health_monitoring(self) -> None:
        """Start health monitoring thread."""
        self._health_stop_event.clear()
        self._health_thread = threading.Thread(
            target=self._health_monitoring_loop,
            name="HybridMonitorHealth",
            daemon=True
        )
        self._health_thread.start()
    
    def _stop_health_monitoring(self) -> None:
        """Stop health monitoring thread."""
        self._health_stop_event.set()
        if self._health_thread and self._health_thread.is_alive():
            self._health_thread.join(timeout=5.0)
    
    def _health_monitoring_loop(self) -> None:
        """Health monitoring loop that runs in a separate thread."""
        self.logger.log_info("Hybrid monitor health checking started")
        
        while not self._health_stop_event.wait(self._health_check_interval):
            try:
                self._perform_health_check()
            except Exception as e:
                self.logger.log_error(f"Error in health monitoring loop: {e}")
        
        self.logger.log_info("Hybrid monitor health checking stopped")
    
    def _perform_health_check(self) -> None:
        """Perform health check and attempt recovery if needed."""
        if not self._active_monitor:
            return
        
        # Check if monitor is healthy
        is_healthy = self._active_monitor.is_monitoring()
        
        if not is_healthy:
            self.logger.log_error(f"Monitor health check failed for {self._selected_mode} mode")
            
            # Attempt recovery
            self._attempt_monitor_recovery()
    
    def _attempt_monitor_recovery(self) -> None:
        """Attempt to recover from monitor failure."""
        if self._fallback_attempted:
            self.logger.log_error("Monitor recovery already attempted, not retrying")
            return
        
        self.logger.log_info("Attempting monitor recovery...")
        
        try:
            # Stop current monitor
            if self._active_monitor:
                self._active_monitor.stop_monitoring()
                self._active_monitor = None
            
            # Try fallback mode
            if self._selected_mode == "events":
                self.logger.log_info("Falling back from events to polling mode")
                self._selected_mode = "polling"
            else:
                self.logger.log_info("Attempting to restart polling mode")
            
            # Restart with fallback mode
            self._start_selected_monitor()
            self._fallback_attempted = True
            
            self.logger.log_info(f"Monitor recovery successful, now using {self._selected_mode} mode")
            
        except Exception as e:
            self.logger.log_error(f"Monitor recovery failed: {e}")
            # Don't attempt recovery again
            self._fallback_attempted = True
    
    def __enter__(self):
        """Context manager entry."""
        self.start_monitoring()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop_monitoring()


def create_file_monitor(source_folder: str, file_processor: FileProcessor,
                       logger_service: LoggerService, config: Dict[str, Any]) -> HybridFileMonitor:
    """
    Factory function to create a file monitor based on configuration.
    
    This provides a simple interface for creating the appropriate monitor type
    based on configuration settings.
    
    Args:
        source_folder: Path to monitor
        file_processor: FileProcessor instance
        logger_service: LoggerService instance
        config: Configuration dictionary with monitoring settings
        
    Returns:
        HybridFileMonitor: Configured hybrid file monitor
    """
    return HybridFileMonitor(
        source_folder=source_folder,
        file_processor=file_processor,
        logger_service=logger_service,
        monitoring_mode=config.get('file_monitoring_mode', 'auto'),
        polling_interval=config.get('polling_interval', 3.0),
        docker_volume_mode=config.get('docker_volume_mode', False)
    )