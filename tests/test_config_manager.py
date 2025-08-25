"""Unit tests for ConfigManager class."""

import os
import tempfile
import pytest
from unittest.mock import patch, mock_open
from src.config.config_manager import ConfigManager, AppConfig


class TestAppConfig:
    """Test cases for AppConfig data model."""
    
    def test_validate_valid_config(self):
        """Test validation with valid configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = AppConfig(
                source_folder=temp_dir,
                saved_folder="/path/to/saved",
                error_folder="/path/to/error"
            )
            errors = config.validate()
            assert errors == []
    
    def test_validate_missing_source_folder(self):
        """Test validation with missing source folder."""
        config = AppConfig(
            source_folder="",
            saved_folder="/path/to/saved",
            error_folder="/path/to/error"
        )
        errors = config.validate()
        assert "SOURCE_FOLDER is required but not provided" in errors
    
    def test_validate_nonexistent_source_folder(self):
        """Test validation with non-existent source folder."""
        config = AppConfig(
            source_folder="/nonexistent/path",
            saved_folder="/path/to/saved",
            error_folder="/path/to/error"
        )
        errors = config.validate()
        assert any("SOURCE_FOLDER path does not exist" in error for error in errors)
    
    def test_validate_source_folder_not_directory(self):
        """Test validation when source folder is not a directory."""
        with tempfile.NamedTemporaryFile() as temp_file:
            config = AppConfig(
                source_folder=temp_file.name,
                saved_folder="/path/to/saved",
                error_folder="/path/to/error"
            )
            errors = config.validate()
            assert any("SOURCE_FOLDER is not a directory" in error for error in errors)
    
    def test_validate_missing_saved_folder(self):
        """Test validation with missing saved folder."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = AppConfig(
                source_folder=temp_dir,
                saved_folder="",
                error_folder="/path/to/error"
            )
            errors = config.validate()
            assert "SAVED_FOLDER is required but not provided" in errors
    
    def test_validate_missing_error_folder(self):
        """Test validation with missing error folder."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = AppConfig(
                source_folder=temp_dir,
                saved_folder="/path/to/saved",
                error_folder=""
            )
            errors = config.validate()
            assert "ERROR_FOLDER is required but not provided" in errors


class TestConfigManager:
    """Test cases for ConfigManager class."""
    
    def test_init_default_env_file(self):
        """Test ConfigManager initialization with default .env file."""
        manager = ConfigManager()
        assert manager.env_file == '.env'
        assert manager._config is None
    
    def test_init_custom_env_file(self):
        """Test ConfigManager initialization with custom .env file."""
        manager = ConfigManager(env_file='custom.env')
        assert manager.env_file == 'custom.env'
    
    @patch.dict(os.environ, {
        'SOURCE_FOLDER': '/source',
        'SAVED_FOLDER': '/saved',
        'ERROR_FOLDER': '/error'
    })
    def test_load_config_from_environment(self):
        """Test loading configuration from environment variables."""
        manager = ConfigManager(env_file=None)
        config = manager.load_config()
        
        assert config['SOURCE_FOLDER'] == '/source'
        assert config['SAVED_FOLDER'] == '/saved'
        assert config['ERROR_FOLDER'] == '/error'
    
    @patch('src.config.config_manager.load_dotenv')
    @patch('os.path.exists')
    @patch.dict(os.environ, {
        'SOURCE_FOLDER': '/source',
        'SAVED_FOLDER': '/saved',
        'ERROR_FOLDER': '/error'
    })
    def test_load_config_from_env_file(self, mock_exists, mock_load_dotenv):
        """Test loading configuration from .env file."""
        mock_exists.return_value = True
        
        manager = ConfigManager(env_file='.env')
        config = manager.load_config()
        
        mock_load_dotenv.assert_called_once_with('.env')
        assert config['SOURCE_FOLDER'] == '/source'
        assert config['SAVED_FOLDER'] == '/saved'
        assert config['ERROR_FOLDER'] == '/error'
    
    @patch.dict(os.environ, {}, clear=True)
    def test_load_config_missing_variables(self):
        """Test loading configuration with missing environment variables."""
        manager = ConfigManager(env_file=None)
        config = manager.load_config()
        
        assert config['SOURCE_FOLDER'] == ""
        assert config['SAVED_FOLDER'] == ""
        assert config['ERROR_FOLDER'] == ""
    
    def test_validate_config_success(self):
        """Test successful configuration validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigManager()
            config = {
                'SOURCE_FOLDER': temp_dir,
                'SAVED_FOLDER': '/saved',
                'ERROR_FOLDER': '/error'
            }
            
            result = manager.validate_config(config)
            assert result is True
            assert manager._config is not None
            assert manager._config.source_folder == temp_dir
    
    def test_validate_config_failure(self):
        """Test configuration validation failure."""
        manager = ConfigManager()
        config = {
            'SOURCE_FOLDER': '',
            'SAVED_FOLDER': '',
            'ERROR_FOLDER': ''
        }
        
        with pytest.raises(ValueError) as exc_info:
            manager.validate_config(config)
        
        error_message = str(exc_info.value)
        assert "Configuration validation failed:" in error_message
        assert "SOURCE_FOLDER is required but not provided" in error_message
        assert "SAVED_FOLDER is required but not provided" in error_message
        assert "ERROR_FOLDER is required but not provided" in error_message
    
    def test_get_folders_without_config(self):
        """Test getting folder paths without loading configuration first."""
        manager = ConfigManager()
        
        with pytest.raises(RuntimeError) as exc_info:
            manager.get_source_folder()
        assert "Configuration not loaded" in str(exc_info.value)
        
        with pytest.raises(RuntimeError) as exc_info:
            manager.get_saved_folder()
        assert "Configuration not loaded" in str(exc_info.value)
        
        with pytest.raises(RuntimeError) as exc_info:
            manager.get_error_folder()
        assert "Configuration not loaded" in str(exc_info.value)
    
    def test_get_folders_with_config(self):
        """Test getting folder paths after loading configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigManager()
            config = {
                'SOURCE_FOLDER': temp_dir,
                'SAVED_FOLDER': '/saved',
                'ERROR_FOLDER': '/error'
            }
            
            manager.validate_config(config)
            
            assert manager.get_source_folder() == temp_dir
            assert manager.get_saved_folder() == '/saved'
            assert manager.get_error_folder() == '/error'
    
    @patch.dict(os.environ, {
        'SOURCE_FOLDER': '/source',
        'SAVED_FOLDER': '/saved',
        'ERROR_FOLDER': '/error'
    })
    def test_initialize_success(self):
        """Test successful initialization (load and validate in one step)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Override the SOURCE_FOLDER to use a real directory for validation
            with patch.dict(os.environ, {'SOURCE_FOLDER': temp_dir}):
                manager = ConfigManager(env_file=None)
                config = manager.initialize()
                
                assert config is not None
                assert config.source_folder == temp_dir
                assert config.saved_folder == '/saved'
                assert config.error_folder == '/error'
    
    def test_initialize_failure(self):
        """Test initialization failure due to validation errors."""
        with patch.dict(os.environ, {}, clear=True):
            manager = ConfigManager(env_file=None)
            
            with pytest.raises(ValueError) as exc_info:
                manager.initialize()
            
            assert "Configuration validation failed:" in str(exc_info.value)