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

from src.config.config_manager import ConfigManager, AppConfig
from src.services.logger_service import LoggerService
from src.services.error_handler import ErrorHandler
from src.core.file_manager import FileManager
from src.core.file_processor import FileProcessor, RetryConfig
from src.core.file_monitor import FileMonitor
from src.core.hybrid_file_monitor import HybridFileMonitor, create_file_monitor

# Import document processing components with graceful fallback
try:
    from src.core.rag_store_processor import RAGStoreProcessor
    from src.core.document_processing import DocumentProcessingInterface
    DOCUMENT_PROCESSING_AVAILABLE = True
except ImportError as e:
    # Document processing dependencies not available
    RAGStoreProcessor = None
    DocumentProcessingInterface = None
    DOCUMENT_PROCESSING_AVAILABLE = False


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
        self.file_monitor: Optional[HybridFileMonitor] = None
        self.document_processor: Optional[DocumentProcessingInterface] = None
        
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
            
            # Step 1.1: Validate document processing configuration
            if self.config.document_processing.enable_processing:
                print("Validating document processing configuration...")
                try:
                    # Validate dependencies if document processing is enabled
                    dependency_errors = self.config_manager.validate_dependencies()
                    if dependency_errors:
                        error_msg = "Document processing dependencies validation failed:\n" + "\n".join(f"- {error}" for error in dependency_errors)
                        print(f"ERROR: {error_msg}")
                        raise RuntimeError(error_msg)
                    
                    print(f"Document processing configuration validated:")
                    print(f"  Processor type: {self.config.document_processing.processor_type}")
                    print(f"  Model vendor: {self.config.document_processing.model_vendor}")
                    print(f"  ChromaDB path: {self.config.document_processing.chroma_db_path}")
                    
                except Exception as e:
                    error_msg = f"Document processing configuration validation failed: {str(e)}"
                    print(f"ERROR: {error_msg}")
                    raise RuntimeError(error_msg) from e
            else:
                print("Document processing is disabled - skipping validation")
            
            # Step 2: Initialize logging service
            print("Setting up logging...")
            self.logger_service = LoggerService.setup_logger(
                log_file_path=self.log_file,
                logger_name="folder_file_processor"
            )
            
            # Log initialization start with configuration details
            doc_processing_status = "enabled" if self.config.document_processing.enable_processing else "disabled"
            self.logger_service.log_info(f"Application initialization started - Document processing: {doc_processing_status}")
            
            if self.config.document_processing.enable_processing:
                self.logger_service.log_info(f"Document processing config - Vendor: {self.config.document_processing.model_vendor}, "
                                           f"Processor: {self.config.document_processing.processor_type}, "
                                           f"ChromaDB: {self.config.document_processing.chroma_db_path}")
            
            # Step 3: Initialize error handler
            print("Initializing error handler...")
            self.error_handler = ErrorHandler(
                error_folder=self.config.error_folder,
                source_folder=self.config.source_folder
            )
            
            # Step 4: Initialize file manager
            print("Initializing file manager...")
            self.file_manager = FileManager(
                source_folder=self.config.source_folder,
                saved_folder=self.config.saved_folder,
                error_folder=self.config.error_folder
            )
            
            # Step 5: Initialize document processor if document processing is enabled
            if self.config.document_processing.enable_processing:
                if not DOCUMENT_PROCESSING_AVAILABLE:
                    error_msg = "Document processing is enabled but required dependencies are not available. Please install RAG store dependencies."
                    print(f"ERROR: {error_msg}")
                    if self.logger_service:
                        self.logger_service.log_error(error_msg)
                    raise RuntimeError(error_msg)
                
                print("Initializing document processor...")
                try:
                    self.document_processor = RAGStoreProcessor(file_manager=self.file_manager)
                    processor_config = self.config.document_processing.to_processor_config()
                    self.document_processor.initialize(processor_config)
                    print(f"Document processing enabled with {self.config.document_processing.model_vendor} embeddings")
                    self.logger_service.log_info(f"Document processor initialized successfully with {self.config.document_processing.model_vendor} vendor")
                except Exception as e:
                    error_msg = f"Failed to initialize document processor: {str(e)}"
                    print(f"ERROR: {error_msg}")
                    if self.logger_service:
                        self.logger_service.log_error(error_msg, e)
                    raise RuntimeError(error_msg) from e
            else:
                print("Document processing disabled in configuration")
                self.logger_service.log_info("Document processing disabled - files will be processed without RAG integration")
            
            # Step 6: Initialize file processor with retry configuration
            print("Initializing file processor...")
            retry_config = RetryConfig(
                max_attempts=3,
                base_delay=1.0,
                max_delay=10.0,
                backoff_multiplier=2.0
            )
            self.file_processor = FileProcessor(
                file_manager=self.file_manager,
                error_handler=self.error_handler,
                logger_service=self.logger_service,
                retry_config=retry_config,
                document_processor=self.document_processor
            )
            
            # Step 7: Initialize hybrid file monitor
            print("Initializing hybrid file monitor...")
            config_dict = {
                'file_monitoring_mode': self.config.file_monitoring_mode,
                'polling_interval': self.config.polling_interval,
                'docker_volume_mode': self.config.docker_volume_mode
            }
            self.file_monitor = create_file_monitor(
                source_folder=self.config.source_folder,
                file_processor=self.file_processor,
                logger_service=self.logger_service,
                config=config_dict
            )
            
            self.logger_service.log_info("All components initialized successfully")
            print("Application initialization complete.")
            return True
            
        except RuntimeError as e:
            # RuntimeError exceptions (like dependency failures) should propagate
            # to allow callers to handle them appropriately
            error_msg = f"Failed to initialize application: {str(e)}"
            print(f"ERROR: {error_msg}")
            
            if self.logger_service:
                self.logger_service.log_error(error_msg, e)
            
            # Ensure proper cleanup on initialization failure
            self._cleanup_on_failure()
            raise  # Re-raise the RuntimeError
            
        except Exception as e:
            error_msg = f"Failed to initialize application: {str(e)}"
            print(f"ERROR: {error_msg}")
            
            if self.logger_service:
                self.logger_service.log_error(error_msg, e)
            else:
                # If logger service is not available, try to create a basic one for error logging
                try:
                    temp_logger = LoggerService.setup_logger(
                        log_file_path=self.log_file,
                        logger_name="folder_file_processor_error"
                    )
                    temp_logger.log_error(error_msg, e)
                except Exception as logger_error:
                    # If we can't create logger, print both errors but don't fail silently
                    print(f"WARNING: Failed to create emergency logger: {logger_error}")
                    print("Original error has been printed above - continuing without logging")
            
            # Ensure proper cleanup on initialization failure
            self._cleanup_on_failure()
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
    
    def _cleanup_on_failure(self) -> None:
        """Cleanup partially initialized components on initialization failure."""
        try:
            if self.document_processor:
                self.document_processor.cleanup()
        except Exception as e:
            print(f"Warning: Error during cleanup: {e}")
    
    def _validate_initialization(self) -> bool:
        """Validate that all required components are initialized."""
        required_components = [
            self.config_manager, self.logger_service, self.error_handler,
            self.file_manager, self.file_processor, self.file_monitor, self.config
        ]
        
        # Document processor is only required if document processing is enabled
        if self.config and self.config.document_processing.enable_processing:
            required_components.append(self.document_processor)
        
        return all(component is not None for component in required_components)
    
    def _run_main_loop(self) -> None:
        """
        Main application loop with enhanced monitoring and error handling.
        
        Monitors for shutdown requests, handles monitoring failures,
        and provides periodic health checks and statistics.
        """
        health_check_interval = 30  # seconds
        stats_report_interval = 300  # 5 minutes
        last_health_check = time.time()
        last_stats_report = time.time()
        
        try:
            while self.is_running and not self.shutdown_requested:
                current_time = time.time()
                
                # Periodic health check
                if current_time - last_health_check >= health_check_interval:
                    if not self._perform_health_check():
                        break
                    last_health_check = current_time
                
                # Periodic statistics report
                if current_time - last_stats_report >= stats_report_interval:
                    self._report_statistics()
                    last_stats_report = current_time
                
                # Sleep briefly to avoid busy waiting
                time.sleep(1.0)
                
        except KeyboardInterrupt:
            print("\nShutdown requested by user.")
        except Exception as e:
            error_msg = f"Unexpected error in main loop: {str(e)}"
            self.logger_service.log_error(error_msg, e)
            print(f"ERROR: {error_msg}")
        finally:
            self.shutdown()
    
    def _perform_health_check(self) -> bool:
        """
        Perform comprehensive health check of all components.
        
        Returns:
            bool: True if all components are healthy, False otherwise
        """
        try:
            # Check file monitoring health
            if not self.file_monitor.is_monitoring():
                error_msg = "File monitoring stopped unexpectedly"
                self.logger_service.log_error(error_msg)
                print(f"ERROR: {error_msg}")
                return False
            
            # Check if source folder is still accessible
            if not Path(self.config.source_folder).exists():
                error_msg = f"Source folder no longer exists: {self.config.source_folder}"
                self.logger_service.log_error(error_msg)
                print(f"ERROR: {error_msg}")
                return False
            
            # Check document processing health if enabled
            if self.config.document_processing.enable_processing and self.document_processor:
                if not self._check_document_processor_health():
                    return False
            
            # Log health check success
            self.logger_service.log_info("Health check passed - all components operational")
            return True
            
        except Exception as e:
            error_msg = f"Health check failed: {str(e)}"
            self.logger_service.log_error(error_msg, e)
            print(f"ERROR: {error_msg}")
            return False
    
    def _check_document_processor_health(self) -> bool:
        """
        Check document processor health including ChromaDB connectivity and embedding model availability.
        
        Returns:
            bool: True if document processor is healthy, False otherwise
        """
        try:
            # Only check ChromaDB path for embedded mode
            if self.config.document_processing.chroma_client_mode == "embedded":
                # Check if ChromaDB path is still accessible
                if self.config.document_processing.chroma_db_path:
                    chroma_path = Path(self.config.document_processing.chroma_db_path)
                    if not chroma_path.parent.exists():
                        error_msg = f"ChromaDB parent directory no longer exists: {chroma_path.parent}"
                        self.logger_service.log_error(error_msg)
                        print(f"ERROR: {error_msg}")
                        return False
                    
                    # Check if ChromaDB path is writable
                    import os
                    if not os.access(chroma_path.parent, os.W_OK):
                        error_msg = f"ChromaDB parent directory is not writable: {chroma_path.parent}"
                        self.logger_service.log_error(error_msg)
                        print(f"ERROR: {error_msg}")
                        return False
                else:
                    error_msg = "ChromaDB path is not configured for embedded mode"
                    self.logger_service.log_error(error_msg)
                    print(f"ERROR: {error_msg}")
                    return False
            # For client_server mode, we don't need to check local paths
            
            # Test document processor functionality with a simple health check
            # This will verify that the processor is still properly initialized
            try:
                # Check if processor can report supported extensions (basic functionality test)
                supported_extensions = self.document_processor.get_supported_extensions()
                if not supported_extensions:
                    error_msg = "Document processor reports no supported file extensions"
                    self.logger_service.log_error(error_msg)
                    print(f"WARNING: {error_msg}")
                    # This is a warning, not a failure - continue monitoring
                
            except Exception as e:
                error_msg = f"Document processor health check failed: {str(e)}"
                self.logger_service.log_error(error_msg, e)
                print(f"ERROR: {error_msg}")
                return False
            
            return True
            
        except Exception as e:
            error_msg = f"Document processor health check error: {str(e)}"
            self.logger_service.log_error(error_msg, e)
            print(f"ERROR: {error_msg}")
            return False
    
    def _report_statistics(self) -> None:
        """Report processing and monitoring statistics."""
        try:
            # Get processing statistics
            processing_stats = self.file_processor.get_processing_stats()
            
            # Get monitoring statistics
            monitoring_stats = self.file_monitor.get_monitoring_stats()
            
            # Build base statistics message
            stats_msg = (
                f"Application Statistics - "
                f"Total processed: {processing_stats['total_processed']}, "
                f"Successful: {processing_stats['successful']}, "
                f"Failed (permanent): {processing_stats['failed_permanent']}, "
                f"Failed (after retry): {processing_stats['failed_after_retry']}, "
                f"Retries attempted: {processing_stats['retries_attempted']}, "
                f"Events received: {monitoring_stats.get('events_received', 0)}, "
                f"Duplicate events filtered: {monitoring_stats.get('duplicate_events_filtered', 0)}"
            )
            
            # Add document processing statistics if enabled
            if self.config.document_processing.enable_processing and self.document_processor:
                doc_stats = self._get_document_processing_stats()
                if doc_stats:
                    stats_msg += f", Document processing - {doc_stats}"
            
            self.logger_service.log_info(stats_msg)
            
        except Exception as e:
            self.logger_service.log_error(f"Failed to report statistics: {e}")
    
    def _get_document_processing_stats(self) -> str:
        """
        Get document processing performance and error statistics.
        
        Returns:
            str: Formatted document processing statistics
        """
        try:
            # Get document processing specific statistics from the processor
            # Note: This would need to be implemented in the RAGStoreProcessor
            # For now, we'll provide basic status information
            
            stats_parts = []
            
            # Add processor status
            stats_parts.append(f"Processor: {self.config.document_processing.processor_type}")
            stats_parts.append(f"Vendor: {self.config.document_processing.model_vendor}")
            
            # Add ChromaDB status
            chroma_path = Path(self.config.document_processing.chroma_db_path)
            if chroma_path.exists():
                stats_parts.append("ChromaDB: accessible")
            else:
                stats_parts.append("ChromaDB: not created yet")
            
            return ", ".join(stats_parts)
            
        except Exception as e:
            self.logger_service.log_error(f"Failed to get document processing stats: {e}")
            return "Document processing stats unavailable"
    
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
            
            # Cleanup document processor
            if self.document_processor:
                print("Cleaning up document processor...")
                try:
                    self.document_processor.cleanup()
                except Exception as e:
                    print(f"Warning: Error during document processor cleanup: {e}")
                    if self.logger_service:
                        self.logger_service.log_error(f"Document processor cleanup error: {e}")
            
            # Reset signal handlers to default
            signal.signal(signal.SIGINT, signal.SIG_DFL)
            signal.signal(signal.SIGTERM, signal.SIG_DFL)
            
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