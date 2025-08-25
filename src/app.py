"""
Main Application Orchestrator for Folder File Processor.

This module contains the main application class that coordinates all components,
handles startup sequence, graceful shutdown, and error handling for monitoring failures.
"""

import signal
import sys
import time
from pathlib import Path
from typing import Optional

from config.config_manager import ConfigManager, AppConfig
from services.logger_service import LoggerService
from services.error_handler import ErrorHandler
from core.file_manager import FileManager
from core.file_processor import FileProcessor
from core.file_monitor import FileMonitor


class FolderFileProcessorApp:
    """
    Main application orchestrator that coordinates all components.
    
    Handles application startup sequence with configuration loading,
    graceful shutdown handling, and error handling for monitoring failures.
    """
    
    def __init__(self, env_file: Optional[str] = '.env', log_file: Optional[str] = None):
        """
        Initialize the application with configuration and logging setup.
        
        Args:
            env_file: Path to .env file for configuration (default: '.env')
            log_file: Optional path to log file (default: None for console only)
        """
        self.env_file = env_file
        self.log_file = log_file
        
        # Component instances
        self.config_manager: Optional[ConfigManager] = None
        self.logger_service: Optional[LoggerService] = None
        self.error_handler: Optional[ErrorHandler] = None
        self.file_manager: Optional[FileManager] = None
        self.file_processor: Optional[FileProcessor] = None
        self.file_monitor: Optional[FileMonitor] = None
        
        # Application state
        self.config: Optional[AppConfig] = None
        self.is_running = False
        self.shutdown_requested = False
        
        # Setup signal handlers for graceful shutdown
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        print(f"\nReceived signal {signum}. Initiating graceful shutdown...")
        self.shutdown_requested = True
    
    def initialize(self) -> bool:
        """
        Initialize all application components in proper sequence.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            # Step 1: Initialize configuration manager and load config
            print("Loading configuration...")
            self.config_manager = ConfigManager(self.env_file)
            self.config = self.config_manager.initialize()
            print(f"Configuration loaded successfully:")
            print(f"  Source folder: {self.config.source_folder}")
            print(f"  Saved folder: {self.config.saved_folder}")
            print(f"  Error folder: {self.config.error_folder}")
            
            # Step 2: Initialize logging service
            print("Setting up logging...")
            self.logger_service = LoggerService.setup_logger(
                log_file_path=self.log_file,
                logger_name="folder_file_processor"
            )
            self.logger_service.log_info("Application initialization started")
            
            # Step 3: Initialize error handler
            print("Initializing error handler...")
            self.error_handler = ErrorHandler(self.config.error_folder)
            
            # Step 4: Initialize file manager
            print("Initializing file manager...")
            self.file_manager = FileManager(
                source_folder=self.config.source_folder,
                saved_folder=self.config.saved_folder,
                error_folder=self.config.error_folder
            )
            
            # Step 5: Initialize file processor
            print("Initializing file processor...")
            self.file_processor = FileProcessor(
                file_manager=self.file_manager,
                error_handler=self.error_handler,
                logger_service=self.logger_service
            )
            
            # Step 6: Initialize file monitor
            print("Initializing file monitor...")
            self.file_monitor = FileMonitor(
                source_folder=self.config.source_folder,
                file_processor=self.file_processor,
                logger_service=self.logger_service
            )
            
            self.logger_service.log_info("All components initialized successfully")
            print("Application initialization complete.")
            return True
            
        except Exception as e:
            error_msg = f"Failed to initialize application: {str(e)}"
            print(f"ERROR: {error_msg}")
            
            if self.logger_service:
                self.logger_service.log_error(error_msg, e)
            
            return False
    
    def start(self) -> None:
        """
        Start the application and begin file monitoring.
        
        Raises:
            RuntimeError: If application is not properly initialized or monitoring fails
        """
        if not self._validate_initialization():
            raise RuntimeError("Application not properly initialized. Call initialize() first.")
        
        try:
            print("Starting file system monitoring...")
            self.file_monitor.start_monitoring()
            self.is_running = True
            
            self.logger_service.log_info("Application started successfully")
            print(f"Monitoring folder: {self.config.source_folder}")
            print("Application is running. Press Ctrl+C to stop.")
            
            # Main application loop
            self._run_main_loop()
            
        except Exception as e:
            error_msg = f"Failed to start file monitoring: {str(e)}"
            self.logger_service.log_error(error_msg, e)
            raise RuntimeError(error_msg) from e
    
    def _validate_initialization(self) -> bool:
        """Validate that all required components are initialized."""
        required_components = [
            self.config_manager, self.logger_service, self.error_handler,
            self.file_manager, self.file_processor, self.file_monitor, self.config
        ]
        return all(component is not None for component in required_components)
    
    def _run_main_loop(self) -> None:
        """
        Main application loop that keeps the application running.
        
        Monitors for shutdown requests and handles monitoring failures.
        """
        try:
            while self.is_running and not self.shutdown_requested:
                # Check if monitoring is still active
                if not self.file_monitor.is_monitoring():
                    error_msg = "File monitoring stopped unexpectedly"
                    self.logger_service.log_error(error_msg)
                    print(f"ERROR: {error_msg}")
                    break
                
                # Sleep briefly to avoid busy waiting
                time.sleep(0.5)
                
        except KeyboardInterrupt:
            print("\nShutdown requested by user.")
        except Exception as e:
            error_msg = f"Unexpected error in main loop: {str(e)}"
            self.logger_service.log_error(error_msg, e)
            print(f"ERROR: {error_msg}")
        finally:
            self.shutdown()
    
    def shutdown(self) -> None:
        """
        Perform graceful shutdown of all application components.
        """
        print("Shutting down application...")
        
        try:
            # Stop file monitoring
            if self.file_monitor:
                print("Stopping file monitor...")
                self.file_monitor.stop_monitoring()
            
            # Log shutdown
            if self.logger_service:
                self.logger_service.log_info("Application shutdown completed")
            
            self.is_running = False
            print("Application shutdown complete.")
            
        except Exception as e:
            error_msg = f"Error during shutdown: {str(e)}"
            print(f"WARNING: {error_msg}")
            
            if self.logger_service:
                self.logger_service.log_error(error_msg, e)
    
    def run(self) -> int:
        """
        Complete application lifecycle: initialize, start, and handle shutdown.
        
        Returns:
            int: Exit code (0 for success, 1 for error)
        """
        try:
            # Initialize application
            if not self.initialize():
                return 1
            
            # Start monitoring
            self.start()
            
            return 0
            
        except Exception as e:
            error_msg = f"Application failed: {str(e)}"
            print(f"FATAL ERROR: {error_msg}")
            
            if self.logger_service:
                self.logger_service.log_error(error_msg, e)
            
            return 1
        
        finally:
            # Ensure cleanup happens
            if self.is_running:
                self.shutdown()


def create_app(env_file: Optional[str] = '.env', log_file: Optional[str] = None) -> FolderFileProcessorApp:
    """
    Factory function to create a configured application instance.
    
    Args:
        env_file: Path to .env file for configuration
        log_file: Optional path to log file
        
    Returns:
        FolderFileProcessorApp: Configured application instance
    """
    return FolderFileProcessorApp(env_file=env_file, log_file=log_file)