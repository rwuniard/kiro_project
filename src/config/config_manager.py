"""Configuration management for the folder file processor application."""

import os
from typing import Dict, List, Optional
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass
class AppConfig:
    """Configuration data model for the application."""
    source_folder: str
    saved_folder: str
    error_folder: str
    
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
            
        return errors


class ConfigManager:
    """Manages application configuration from environment variables."""
    
    REQUIRED_ENV_VARS = ['SOURCE_FOLDER', 'SAVED_FOLDER', 'ERROR_FOLDER']
    
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
        for var in self.REQUIRED_ENV_VARS:
            value = os.getenv(var)
            if value:
                config[var] = value
            else:
                config[var] = ""
        
        return config
    
    def validate_config(self, config: Dict[str, str]) -> bool:
        """Validate configuration dictionary and return True if valid."""
        app_config = AppConfig(
            source_folder=config.get('SOURCE_FOLDER', ''),
            saved_folder=config.get('SAVED_FOLDER', ''),
            error_folder=config.get('ERROR_FOLDER', '')
        )
        
        errors = app_config.validate()
        if errors:
            error_message = "Configuration validation failed:\n" + "\n".join(f"- {error}" for error in errors)
            raise ValueError(error_message)
        
        self._config = app_config
        return True
    
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
    
    def initialize(self) -> AppConfig:
        """Load and validate configuration in one step."""
        config_dict = self.load_config()
        self.validate_config(config_dict)
        return self._config