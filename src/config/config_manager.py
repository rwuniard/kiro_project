"""Configuration management for the folder file processor application."""

import os
from typing import Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv


class ConfigurationValidationError(Exception):
    """Exception raised when configuration validation fails."""
    
    def __init__(self, message: str, critical_errors: List[str], warning_errors: List[str]):
        super().__init__(message)
        self.critical_errors = critical_errors
        self.warning_errors = warning_errors
        self.has_critical_errors = len(critical_errors) > 0
        self.has_warnings = len(warning_errors) > 0


@dataclass
class DocumentProcessingConfig:
    """Configuration for document processing system."""
    processor_type: str = "rag_store"
    enable_processing: bool = True
    google_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    chroma_db_path: Optional[str] = None
    model_vendor: str = "google"
    # ChromaDB client-server configuration
    chroma_client_mode: str = "embedded"  # "embedded" or "client_server"
    chroma_server_host: str = "localhost"
    chroma_server_port: int = 8000
    chroma_collection_name: Optional[str] = None
    
    def validate(self) -> List[str]:
        """Validate document processing configuration and return list of validation errors."""
        errors = []
        
        if not self.enable_processing:
            # If processing is disabled, no validation needed
            return errors
        
        # Validate processor type
        valid_processor_types = ["rag_store"]
        if self.processor_type not in valid_processor_types:
            errors.append(f"Invalid processor_type '{self.processor_type}'. Must be one of: {valid_processor_types}")
        
        # Validate model vendor
        valid_model_vendors = ["google", "openai"]
        if self.model_vendor not in valid_model_vendors:
            errors.append(f"Invalid model_vendor '{self.model_vendor}'. Must be one of: {valid_model_vendors}")
        
        # Validate API keys based on model vendor
        if self.model_vendor == "google":
            if not self.google_api_key:
                errors.append("GOOGLE_API_KEY is required when model_vendor is 'google'")
            else:
                # Validate Google API key format (basic validation)
                if not self._is_valid_google_api_key(self.google_api_key):
                    errors.append("GOOGLE_API_KEY format appears invalid (should start with 'AIza' and be 39 characters)")
        elif self.model_vendor == "openai":
            if not self.openai_api_key:
                errors.append("OPENAI_API_KEY is required when model_vendor is 'openai'")
            else:
                # Validate OpenAI API key format (basic validation)
                if not self._is_valid_openai_api_key(self.openai_api_key):
                    errors.append("OPENAI_API_KEY format appears invalid (should start with 'sk-' and be at least 20 characters)")
        
        # Validate ChromaDB configuration based on client mode
        chroma_mode_errors = self._validate_chroma_configuration()
        errors.extend(chroma_mode_errors)
        
        # Validate embedding model configuration
        embedding_errors = self._validate_embedding_model_config()
        errors.extend(embedding_errors)
        
        return errors
    
    def _is_valid_google_api_key(self, api_key: str) -> bool:
        """Validate Google API key format."""
        if not api_key:
            return False
        # Google API keys typically start with 'AIza' and are 39 characters long
        return api_key.startswith('AIza') and len(api_key) == 39
    
    def _is_valid_openai_api_key(self, api_key: str) -> bool:
        """Validate OpenAI API key format."""
        if not api_key:
            return False
        # OpenAI API keys start with 'sk-' and are typically longer than 20 characters
        return api_key.startswith('sk-') and len(api_key) >= 20
    
    def _validate_embedding_model_config(self) -> List[str]:
        """Validate embedding model configuration based on vendor."""
        errors = []
        
        if self.model_vendor == "google":
            # Validate Google embedding model configuration
            # Google uses text-embedding-004 or text-embedding-gecko models
            # No specific model name validation needed as it's handled by the API
            pass
        elif self.model_vendor == "openai":
            # Validate OpenAI embedding model configuration
            # OpenAI uses text-embedding-ada-002 or text-embedding-3-small/large
            # No specific model name validation needed as it's handled by the API
            pass
        
        return errors
    
    def _validate_chroma_configuration(self) -> List[str]:
        """Validate ChromaDB configuration based on client mode."""
        errors = []
        
        # Validate client mode
        valid_modes = ["embedded", "client_server"]
        if self.chroma_client_mode not in valid_modes:
            errors.append(f"Invalid chroma_client_mode '{self.chroma_client_mode}'. Must be one of: {valid_modes}")
            return errors  # Skip further validation if mode is invalid
        
        if self.chroma_client_mode == "embedded":
            # Validate ChromaDB path for embedded mode
            if self.chroma_db_path:
                chroma_path = Path(self.chroma_db_path)
                try:
                    # Check if parent directory exists and is writable
                    parent_dir = chroma_path.parent
                    if not parent_dir.exists():
                        errors.append(f"ChromaDB parent directory does not exist: {parent_dir}")
                    elif not os.access(parent_dir, os.W_OK):
                        errors.append(f"ChromaDB parent directory is not writable: {parent_dir}")
                    
                    # Check if ChromaDB path itself exists and validate it
                    if chroma_path.exists():
                        if not chroma_path.is_dir():
                            errors.append(f"ChromaDB path exists but is not a directory: {chroma_path}")
                        elif not os.access(chroma_path, os.R_OK | os.W_OK):
                            errors.append(f"ChromaDB directory is not readable/writable: {chroma_path}")
                except (OSError, ValueError) as e:
                    errors.append(f"Invalid ChromaDB path '{self.chroma_db_path}': {str(e)}")
            else:
                # ChromaDB path is required for embedded mode
                errors.append("CHROMA_DB_PATH is required when using embedded mode")
        
        elif self.chroma_client_mode == "client_server":
            # Validate server connection details for client-server mode
            if not self.chroma_server_host:
                errors.append("CHROMA_SERVER_HOST is required when using client_server mode")
            
            if not isinstance(self.chroma_server_port, int) or not (1 <= self.chroma_server_port <= 65535):
                errors.append(f"CHROMA_SERVER_PORT must be a valid port number (1-65535), got: {self.chroma_server_port}")
        
        return errors
    
    @classmethod
    def from_environment(cls) -> 'DocumentProcessingConfig':
        """Create DocumentProcessingConfig from environment variables."""
        # Parse port with error handling
        try:
            chroma_port = int(os.getenv("CHROMA_SERVER_PORT", "8000"))
        except ValueError:
            chroma_port = 8000
        
        return cls(
            processor_type=os.getenv("DOCUMENT_PROCESSOR_TYPE", "rag_store"),
            enable_processing=os.getenv("ENABLE_DOCUMENT_PROCESSING", "true").lower() in ("true", "1", "yes", "on"),
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            chroma_db_path=os.getenv("CHROMA_DB_PATH"),
            model_vendor=os.getenv("MODEL_VENDOR", "google").lower(),
            chroma_client_mode=os.getenv("CHROMA_CLIENT_MODE", "embedded").lower(),
            chroma_server_host=os.getenv("CHROMA_SERVER_HOST", "localhost"),
            chroma_server_port=chroma_port,
            chroma_collection_name=os.getenv("CHROMA_COLLECTION_NAME")
        )
    
    @classmethod
    def from_config_dict(cls, config: Dict[str, str]) -> 'DocumentProcessingConfig':
        """Create DocumentProcessingConfig from configuration dictionary."""
        # Parse port with error handling
        try:
            chroma_port = int(config.get("CHROMA_SERVER_PORT", "8000"))
        except ValueError:
            chroma_port = 8000
        
        return cls(
            processor_type=config.get("DOCUMENT_PROCESSOR_TYPE", "rag_store"),
            enable_processing=config.get("ENABLE_DOCUMENT_PROCESSING", "true").lower() in ("true", "1", "yes", "on"),
            google_api_key=config.get("GOOGLE_API_KEY"),
            openai_api_key=config.get("OPENAI_API_KEY"),
            chroma_db_path=config.get("CHROMA_DB_PATH"),
            model_vendor=config.get("MODEL_VENDOR", "google").lower(),
            chroma_client_mode=config.get("CHROMA_CLIENT_MODE", "embedded").lower(),
            chroma_server_host=config.get("CHROMA_SERVER_HOST", "localhost"),
            chroma_server_port=chroma_port,
            chroma_collection_name=config.get("CHROMA_COLLECTION_NAME")
        )
    
    def get_api_key_for_vendor(self) -> Optional[str]:
        """Get the appropriate API key for the configured model vendor."""
        if self.model_vendor == "google":
            return self.google_api_key
        elif self.model_vendor == "openai":
            return self.openai_api_key
        return None
    
    def to_processor_config(self) -> Dict[str, str]:
        """Convert to configuration dictionary for document processor initialization."""
        config = {
            "model_vendor": self.model_vendor,
            "processor_type": self.processor_type
        }
        
        # Add API keys
        if self.google_api_key:
            config["google_api_key"] = self.google_api_key
        if self.openai_api_key:
            config["openai_api_key"] = self.openai_api_key
        
        # Add ChromaDB configuration
        config["chroma_client_mode"] = self.chroma_client_mode
        config["chroma_server_host"] = self.chroma_server_host
        config["chroma_server_port"] = self.chroma_server_port
        
        if self.chroma_db_path:
            config["chroma_db_path"] = self.chroma_db_path
        if self.chroma_collection_name:
            config["chroma_collection_name"] = self.chroma_collection_name
        
        return config


@dataclass
class AppConfig:
    """Configuration data model for the application."""
    source_folder: str
    saved_folder: str
    error_folder: str
    document_processing: DocumentProcessingConfig
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of validation errors."""
        errors = []
        
        if not self.source_folder:
            errors.append("SOURCE_FOLDER is required but not provided")
        elif not os.path.exists(self.source_folder):
            errors.append(f"SOURCE_FOLDER path does not exist: {self.source_folder}")
        elif not os.path.isdir(self.source_folder):
            errors.append(f"SOURCE_FOLDER is not a directory: {self.source_folder}")
            
        if not self.saved_folder:
            errors.append("SAVED_FOLDER is required but not provided")
            
        if not self.error_folder:
            errors.append("ERROR_FOLDER is required but not provided")
        
        # Validate document processing configuration
        doc_processing_errors = self.document_processing.validate()
        errors.extend(doc_processing_errors)
            
        return errors


class ConfigManager:
    """Manages application configuration from environment variables."""
    
    REQUIRED_ENV_VARS = ['SOURCE_FOLDER', 'SAVED_FOLDER', 'ERROR_FOLDER']
    DOCUMENT_PROCESSING_ENV_VARS = [
        'DOCUMENT_PROCESSOR_TYPE', 'ENABLE_DOCUMENT_PROCESSING', 
        'GOOGLE_API_KEY', 'OPENAI_API_KEY', 'CHROMA_DB_PATH', 'MODEL_VENDOR'
    ]
    
    def __init__(self, env_file: Optional[str] = '.env'):
        """Initialize ConfigManager with optional .env file path."""
        self.env_file = env_file
        self._config: Optional[AppConfig] = None
    
    def load_config(self) -> Dict[str, str]:
        """Load configuration from environment variables and .env file."""
        # Load .env file if it exists
        if self.env_file and os.path.exists(self.env_file):
            load_dotenv(self.env_file)
        
        config = {}
        
        # Load required environment variables
        for var in self.REQUIRED_ENV_VARS:
            value = os.getenv(var)
            if value:
                # Expand user home directory (~) and environment variables
                config[var] = os.path.expanduser(os.path.expandvars(value))
            else:
                config[var] = ""
        
        # Load document processing environment variables
        for var in self.DOCUMENT_PROCESSING_ENV_VARS:
            value = os.getenv(var)
            if value:
                # Expand paths for path-related variables
                if 'PATH' in var:
                    config[var] = os.path.expanduser(os.path.expandvars(value))
                else:
                    config[var] = value
            else:
                config[var] = ""
        
        return config
    
    def validate_config(self, config: Dict[str, str]) -> bool:
        """Validate configuration dictionary and return True if valid."""
        try:
            # Create document processing config from provided config dictionary
            doc_processing_config = DocumentProcessingConfig.from_config_dict(config)
            
            app_config = AppConfig(
                source_folder=config.get('SOURCE_FOLDER', ''),
                saved_folder=config.get('SAVED_FOLDER', ''),
                error_folder=config.get('ERROR_FOLDER', ''),
                document_processing=doc_processing_config
            )
            
            errors = app_config.validate()
            if errors:
                # Categorize errors for better error handling
                critical_errors = []
                warning_errors = []
                
                for error in errors:
                    if any(keyword in error.lower() for keyword in ['required', 'missing', 'not provided', 'does not exist']):
                        critical_errors.append(error)
                    else:
                        warning_errors.append(error)
                
                error_message = "Configuration validation failed:"
                if critical_errors:
                    error_message += "\n\nCritical errors (must be fixed):"
                    error_message += "\n" + "\n".join(f"- {error}" for error in critical_errors)
                if warning_errors:
                    error_message += "\n\nWarnings (should be reviewed):"
                    error_message += "\n" + "\n".join(f"- {error}" for error in warning_errors)
                
                raise ConfigurationValidationError(error_message, critical_errors, warning_errors)
            
            self._config = app_config
            return True
            
        except Exception as e:
            if isinstance(e, ConfigurationValidationError):
                raise
            # Wrap unexpected errors in a configuration error
            raise ConfigurationValidationError(
                f"Unexpected error during configuration validation: {str(e)}",
                [str(e)],
                []
            ) from e
    
    def get_source_folder(self) -> str:
        """Get the source folder path."""
        if not self._config:
            raise RuntimeError("Configuration not loaded. Call load_config() and validate_config() first.")
        return self._config.source_folder
    
    def get_saved_folder(self) -> str:
        """Get the saved folder path."""
        if not self._config:
            raise RuntimeError("Configuration not loaded. Call load_config() and validate_config() first.")
        return self._config.saved_folder
    
    def get_error_folder(self) -> str:
        """Get the error folder path."""
        if not self._config:
            raise RuntimeError("Configuration not loaded. Call load_config() and validate_config() first.")
        return self._config.error_folder
    
    def get_document_processing_config(self) -> DocumentProcessingConfig:
        """Get the document processing configuration."""
        if not self._config:
            raise RuntimeError("Configuration not loaded. Call load_config() and validate_config() first.")
        return self._config.document_processing
    
    def is_document_processing_enabled(self) -> bool:
        """Check if document processing is enabled."""
        if not self._config:
            raise RuntimeError("Configuration not loaded. Call load_config() and validate_config() first.")
        return self._config.document_processing.enable_processing
    
    def validate_dependencies(self) -> List[str]:
        """Validate that required dependencies are available for document processing."""
        if not self._config:
            raise RuntimeError("Configuration not loaded. Call load_config() and validate_config() first.")
        
        errors = []
        
        if not self._config.document_processing.enable_processing:
            return errors
        
        # Check if ChromaDB can be imported
        try:
            import chromadb
        except ImportError:
            errors.append("ChromaDB package is not installed. Install with: pip install chromadb")
        
        # Check if required embedding libraries are available based on vendor
        if self._config.document_processing.model_vendor == "google":
            try:
                import google.generativeai
            except ImportError:
                errors.append("Google Generative AI package is not installed. Install with: pip install google-generativeai")
        elif self._config.document_processing.model_vendor == "openai":
            try:
                import openai
            except ImportError:
                errors.append("OpenAI package is not installed. Install with: pip install openai")
        
        # Check if document processing libraries are available
        try:
            import pypdf
        except ImportError:
            errors.append("PDF processing library is not installed. Install with: pip install pypdf")
        
        try:
            import python_docx
        except ImportError:
            try:
                import docx
            except ImportError:
                errors.append("DOCX processing library is not installed. Install with: pip install python-docx")
        
        return errors
    
    def initialize(self) -> AppConfig:
        """Load and validate configuration in one step."""
        config_dict = self.load_config()
        self.validate_config(config_dict)
        
        # Validate dependencies if document processing is enabled
        if self._config.document_processing.enable_processing:
            dependency_errors = self.validate_dependencies()
            if dependency_errors:
                error_message = "Required dependencies are missing:\n" + "\n".join(f"- {error}" for error in dependency_errors)
                raise ConfigurationValidationError(error_message, dependency_errors, [])
        
        return self._config