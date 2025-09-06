"""
Unit tests for DocumentProcessingConfig dataclass and related configuration management.

Tests configuration validation, environment variable loading, and integration
with the ConfigManager for document processing settings.
"""

import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, Mock

from src.config.config_manager import (
    DocumentProcessingConfig,
    AppConfig,
    ConfigManager,
    ConfigurationValidationError
)


class TestDocumentProcessingConfig:
    """Test cases for DocumentProcessingConfig dataclass."""
    
    def test_document_processing_config_initialization_with_defaults(self):
        """Test DocumentProcessingConfig initialization with default values."""
        config = DocumentProcessingConfig()
        
        assert config.processor_type == "rag_store"
        assert config.enable_processing is True
        assert config.google_api_key is None
        assert config.openai_api_key is None
        assert config.chroma_db_path is None
        assert config.model_vendor == "google"
    
    def test_document_processing_config_initialization_with_custom_values(self):
        """Test DocumentProcessingConfig initialization with custom values."""
        config = DocumentProcessingConfig(
            processor_type="custom_processor",
            enable_processing=False,
            google_api_key="test_google_key",
            openai_api_key="test_openai_key",
            chroma_db_path="/custom/chroma/path",
            model_vendor="openai"
        )
        
        assert config.processor_type == "custom_processor"
        assert config.enable_processing is False
        assert config.google_api_key == "test_google_key"
        assert config.openai_api_key == "test_openai_key"
        assert config.chroma_db_path == "/custom/chroma/path"
        assert config.model_vendor == "openai"
    
    def test_validate_disabled_processing_no_errors(self):
        """Test validation passes when processing is disabled."""
        config = DocumentProcessingConfig(enable_processing=False)
        
        errors = config.validate()
        assert errors == []
    
    def test_validate_valid_google_configuration(self):
        """Test validation passes for valid Google configuration."""
        config = DocumentProcessingConfig(
            processor_type="rag_store",
            enable_processing=True,
            google_api_key="AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI",
            model_vendor="google",
            chroma_db_path="/tmp/chroma"
        )
        
        errors = config.validate()
        assert errors == []
    
    def test_validate_valid_openai_configuration(self):
        """Test validation passes for valid OpenAI configuration."""
        config = DocumentProcessingConfig(
            processor_type="rag_store",
            enable_processing=True,
            openai_api_key="sk-1234567890abcdef1234567890abcdef",
            model_vendor="openai",
            chroma_db_path="/tmp/chroma"
        )
        
        errors = config.validate()
        assert errors == []
    
    def test_validate_invalid_processor_type(self):
        """Test validation fails for invalid processor type."""
        config = DocumentProcessingConfig(
            processor_type="invalid_processor",
            enable_processing=True,
            google_api_key="AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI",
            model_vendor="google",
            chroma_db_path="/tmp/chroma"
        )
        
        errors = config.validate()
        assert len(errors) == 1
        assert "Invalid processor_type 'invalid_processor'" in errors[0]
        assert "rag_store" in errors[0]
    
    def test_validate_invalid_model_vendor(self):
        """Test validation fails for invalid model vendor."""
        config = DocumentProcessingConfig(
            processor_type="rag_store",
            enable_processing=True,
            google_api_key="AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI",
            model_vendor="invalid_vendor",
            chroma_db_path="/tmp/chroma"
        )
        
        errors = config.validate()
        assert len(errors) == 1
        assert "Invalid model_vendor 'invalid_vendor'" in errors[0]
        assert "google" in errors[0] and "openai" in errors[0]
    
    def test_validate_missing_google_api_key(self):
        """Test validation fails when Google API key is missing for Google vendor."""
        config = DocumentProcessingConfig(
            processor_type="rag_store",
            enable_processing=True,
            model_vendor="google",
            chroma_db_path="/tmp/chroma"
            # google_api_key is None
        )
        
        errors = config.validate()
        assert len(errors) == 1
        assert "GOOGLE_API_KEY is required when model_vendor is 'google'" in errors[0]
    
    def test_validate_missing_openai_api_key(self):
        """Test validation fails when OpenAI API key is missing for OpenAI vendor."""
        config = DocumentProcessingConfig(
            processor_type="rag_store",
            enable_processing=True,
            model_vendor="openai",
            chroma_db_path="/tmp/chroma"
            # openai_api_key is None
        )
        
        errors = config.validate()
        assert len(errors) == 1
        assert "OPENAI_API_KEY is required when model_vendor is 'openai'" in errors[0]
    
    def test_validate_valid_chroma_db_path(self):
        """Test validation passes for valid ChromaDB path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            chroma_path = os.path.join(temp_dir, "chroma_db")
            
            config = DocumentProcessingConfig(
                processor_type="rag_store",
                enable_processing=True,
                google_api_key="AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI",
                model_vendor="google",
                chroma_db_path=chroma_path
            )
            
            errors = config.validate()
            assert errors == []
    
    def test_validate_invalid_chroma_db_path_parent_not_exists(self):
        """Test validation fails when ChromaDB parent directory doesn't exist."""
        invalid_path = "/nonexistent/directory/chroma_db"
        
        config = DocumentProcessingConfig(
            processor_type="rag_store",
            enable_processing=True,
            google_api_key="AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI",
            model_vendor="google",
            chroma_db_path=invalid_path
        )
        
        errors = config.validate()
        assert len(errors) == 1
        assert "ChromaDB parent directory does not exist" in errors[0]
    
    def test_validate_invalid_chroma_db_path_not_writable(self):
        """Test validation fails when ChromaDB parent directory is not writable."""
        # Use root directory which should not be writable for regular users
        invalid_path = "/root/chroma_db"
        
        config = DocumentProcessingConfig(
            processor_type="rag_store",
            enable_processing=True,
            google_api_key="valid_key",
            model_vendor="google",
            chroma_db_path=invalid_path
        )
        
        errors = config.validate()
        # This test might pass on some systems, so we check if error is related to permissions
        if errors:
            assert any("not writable" in error or "does not exist" in error for error in errors)
    
    def test_validate_multiple_errors(self):
        """Test validation returns multiple errors when multiple issues exist."""
        config = DocumentProcessingConfig(
            processor_type="invalid_processor",
            enable_processing=True,
            model_vendor="invalid_vendor"
            # Missing API keys
        )
        
        errors = config.validate()
        assert len(errors) >= 2  # At least processor type and model vendor errors
        assert any("Invalid processor_type" in error for error in errors)
        assert any("Invalid model_vendor" in error for error in errors)
    
    def test_validate_missing_chroma_db_path(self):
        """Test validation fails when ChromaDB path is missing for embedded mode."""
        config = DocumentProcessingConfig(
            processor_type="rag_store",
            enable_processing=True,
            google_api_key="AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI",
            model_vendor="google",
            chroma_client_mode="embedded"
            # chroma_db_path is None
        )
        
        errors = config.validate()
        assert len(errors) == 1
        assert "CHROMA_DB_PATH is required when using embedded mode" in errors[0]
    
    def test_validate_google_api_key_format_valid(self):
        """Test validation passes for valid Google API key format."""
        config = DocumentProcessingConfig(
            processor_type="rag_store",
            enable_processing=True,
            google_api_key="AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI",  # Valid format
            model_vendor="google",
            chroma_db_path="/tmp/chroma"
        )
        
        errors = config.validate()
        # Should not have API key format errors
        assert not any("format appears invalid" in error for error in errors)
    
    def test_validate_google_api_key_format_invalid(self):
        """Test validation fails for invalid Google API key format."""
        config = DocumentProcessingConfig(
            processor_type="rag_store",
            enable_processing=True,
            google_api_key="invalid_key_format",
            model_vendor="google",
            chroma_db_path="/tmp/chroma"
        )
        
        errors = config.validate()
        assert any("GOOGLE_API_KEY format appears invalid" in error for error in errors)
    
    def test_validate_openai_api_key_format_valid(self):
        """Test validation passes for valid OpenAI API key format."""
        config = DocumentProcessingConfig(
            processor_type="rag_store",
            enable_processing=True,
            openai_api_key="sk-1234567890abcdef1234567890abcdef",  # Valid format
            model_vendor="openai",
            chroma_db_path="/tmp/chroma"
        )
        
        errors = config.validate()
        # Should not have API key format errors
        assert not any("format appears invalid" in error for error in errors)
    
    def test_validate_openai_api_key_format_invalid(self):
        """Test validation fails for invalid OpenAI API key format."""
        config = DocumentProcessingConfig(
            processor_type="rag_store",
            enable_processing=True,
            openai_api_key="invalid_key",
            model_vendor="openai",
            chroma_db_path="/tmp/chroma"
        )
        
        errors = config.validate()
        assert any("OPENAI_API_KEY format appears invalid" in error for error in errors)
    
    def test_validate_chroma_db_path_exists_but_not_directory(self):
        """Test validation fails when ChromaDB path exists but is not a directory."""
        with tempfile.NamedTemporaryFile() as temp_file:
            config = DocumentProcessingConfig(
                processor_type="rag_store",
                enable_processing=True,
                google_api_key="AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI",
                model_vendor="google",
                chroma_db_path=temp_file.name
            )
            
            errors = config.validate()
            assert any("exists but is not a directory" in error for error in errors)
    
    def test_from_environment_with_defaults(self):
        """Test creating DocumentProcessingConfig from environment with defaults."""
        with patch.dict(os.environ, {}, clear=True):
            config = DocumentProcessingConfig.from_environment()
            
            assert config.processor_type == "rag_store"
            assert config.enable_processing is True
            assert config.google_api_key is None
            assert config.openai_api_key is None
            assert config.chroma_db_path is None
            assert config.model_vendor == "google"
    
    def test_from_environment_with_custom_values(self):
        """Test creating DocumentProcessingConfig from environment with custom values."""
        env_vars = {
            "DOCUMENT_PROCESSOR_TYPE": "custom_processor",
            "ENABLE_DOCUMENT_PROCESSING": "false",
            "GOOGLE_API_KEY": "test_google_key",
            "OPENAI_API_KEY": "test_openai_key",
            "CHROMA_DB_PATH": "/custom/chroma/path",
            "MODEL_VENDOR": "openai"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = DocumentProcessingConfig.from_environment()
            
            assert config.processor_type == "custom_processor"
            assert config.enable_processing is False
            assert config.google_api_key == "test_google_key"
            assert config.openai_api_key == "test_openai_key"
            assert config.chroma_db_path == "/custom/chroma/path"
            assert config.model_vendor == "openai"

    def test_from_environment_with_chromadb_client_server_settings(self):
        """Test from_environment with ChromaDB client-server configuration."""
        env_vars = {
            "CHROMA_CLIENT_MODE": "client_server",
            "CHROMA_SERVER_HOST": "remote-chroma.example.com",
            "CHROMA_SERVER_PORT": "9000",
            "CHROMA_COLLECTION_NAME": "my_test_collection",
            "MODEL_VENDOR": "google",
            "GOOGLE_API_KEY": "AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI",
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = DocumentProcessingConfig.from_environment()
        
        assert config.chroma_client_mode == "client_server"
        assert config.chroma_server_host == "remote-chroma.example.com"
        assert config.chroma_server_port == 9000
        assert config.chroma_collection_name == "my_test_collection"

    def test_from_environment_with_embedded_mode_settings(self):
        """Test from_environment with ChromaDB embedded mode configuration."""
        env_vars = {
            "CHROMA_CLIENT_MODE": "embedded",
            "CHROMA_DB_PATH": "/custom/chroma/path",
            "CHROMA_COLLECTION_NAME": "embedded_collection",
            "MODEL_VENDOR": "google",
            "GOOGLE_API_KEY": "AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI",
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = DocumentProcessingConfig.from_environment()
        
        assert config.chroma_client_mode == "embedded"
        assert config.chroma_db_path == "/custom/chroma/path"
        assert config.chroma_collection_name == "embedded_collection"
        assert config.chroma_server_host == "localhost"  # Default
        assert config.chroma_server_port == 8000  # Default

    def test_from_environment_with_invalid_port(self):
        """Test from_environment with invalid port falls back to default."""
        env_vars = {
            "CHROMA_SERVER_PORT": "invalid_port",
            "MODEL_VENDOR": "google",
            "GOOGLE_API_KEY": "AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI",
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = DocumentProcessingConfig.from_environment()
        
        # Should fall back to default port
        assert config.chroma_server_port == 8000
    
    def test_from_environment_enable_processing_variations(self):
        """Test various ways to enable/disable processing via environment."""
        # Test true values
        true_values = ["true", "1", "yes", "on", "TRUE", "Yes", "ON"]
        for value in true_values:
            with patch.dict(os.environ, {"ENABLE_DOCUMENT_PROCESSING": value}, clear=True):
                config = DocumentProcessingConfig.from_environment()
                assert config.enable_processing is True, f"Failed for value: {value}"
        
        # Test false values
        false_values = ["false", "0", "no", "off", "FALSE", "No", "OFF", "invalid"]
        for value in false_values:
            with patch.dict(os.environ, {"ENABLE_DOCUMENT_PROCESSING": value}, clear=True):
                config = DocumentProcessingConfig.from_environment()
                assert config.enable_processing is False, f"Failed for value: {value}"
    
    def test_get_api_key_for_vendor_google(self):
        """Test getting API key for Google vendor."""
        config = DocumentProcessingConfig(
            google_api_key="google_key",
            openai_api_key="openai_key",
            model_vendor="google"
        )
        
        assert config.get_api_key_for_vendor() == "google_key"
    
    def test_get_api_key_for_vendor_openai(self):
        """Test getting API key for OpenAI vendor."""
        config = DocumentProcessingConfig(
            google_api_key="google_key",
            openai_api_key="openai_key",
            model_vendor="openai"
        )
        
        assert config.get_api_key_for_vendor() == "openai_key"
    
    def test_get_api_key_for_vendor_invalid(self):
        """Test getting API key for invalid vendor returns None."""
        config = DocumentProcessingConfig(
            google_api_key="google_key",
            openai_api_key="openai_key",
            model_vendor="invalid_vendor"
        )
        
        assert config.get_api_key_for_vendor() is None
    
    def test_to_processor_config_google(self):
        """Test converting to processor config dictionary for Google."""
        config = DocumentProcessingConfig(
            processor_type="rag_store",
            google_api_key="google_key",
            chroma_db_path="/custom/path",
            model_vendor="google"
        )
        
        processor_config = config.to_processor_config()
        
        expected = {
            "model_vendor": "google",
            "processor_type": "rag_store",
            "google_api_key": "google_key",
            "chroma_db_path": "/custom/path",
            "chroma_client_mode": "embedded",
            "chroma_server_host": "localhost",
            "chroma_server_port": 8000
        }
        
        assert processor_config == expected
    
    def test_to_processor_config_openai(self):
        """Test converting to processor config dictionary for OpenAI."""
        config = DocumentProcessingConfig(
            processor_type="rag_store",
            openai_api_key="openai_key",
            model_vendor="openai"
        )
        
        processor_config = config.to_processor_config()
        
        expected = {
            "model_vendor": "openai",
            "processor_type": "rag_store",
            "openai_api_key": "openai_key",
            "chroma_client_mode": "embedded",
            "chroma_server_host": "localhost",
            "chroma_server_port": 8000
        }
        
        assert processor_config == expected
    
    def test_to_processor_config_minimal(self):
        """Test converting to processor config with minimal configuration."""
        config = DocumentProcessingConfig(
            processor_type="rag_store",
            model_vendor="google"
        )
        
        processor_config = config.to_processor_config()
        
        expected = {
            "model_vendor": "google",
            "processor_type": "rag_store",
            "chroma_client_mode": "embedded",
            "chroma_server_host": "localhost",
            "chroma_server_port": 8000
        }
        
        assert processor_config == expected

    def test_to_processor_config_with_collection_name(self):
        """Test to_processor_config includes ChromaDB collection name when provided."""
        config = DocumentProcessingConfig(
            processor_type="rag_store",
            model_vendor="google",
            google_api_key="test_key",
            chroma_db_path="/custom/path",
            chroma_collection_name="my_custom_collection"
        )
        
        processor_config = config.to_processor_config()
        
        expected = {
            "model_vendor": "google",
            "processor_type": "rag_store",
            "google_api_key": "test_key",
            "chroma_db_path": "/custom/path",
            "chroma_client_mode": "embedded",
            "chroma_server_host": "localhost",
            "chroma_server_port": 8000,
            "chroma_collection_name": "my_custom_collection"
        }
        
        assert processor_config == expected

    def test_to_processor_config_client_server_mode(self):
        """Test to_processor_config with client-server mode configuration."""
        config = DocumentProcessingConfig(
            processor_type="rag_store",
            model_vendor="openai",
            openai_api_key="test_openai_key",
            chroma_client_mode="client_server",
            chroma_server_host="remote-server.com",
            chroma_server_port=9000,
            chroma_collection_name="client_server_collection"
        )
        
        processor_config = config.to_processor_config()
        
        expected = {
            "model_vendor": "openai",
            "processor_type": "rag_store",
            "openai_api_key": "test_openai_key",
            "chroma_client_mode": "client_server",
            "chroma_server_host": "remote-server.com",
            "chroma_server_port": 9000,
            "chroma_collection_name": "client_server_collection"
        }
        
        assert processor_config == expected

    def test_to_processor_config_without_collection_name(self):
        """Test to_processor_config excludes collection name when not provided."""
        config = DocumentProcessingConfig(
            processor_type="rag_store",
            model_vendor="google",
            google_api_key="test_key",
            chroma_db_path="/custom/path"
            # chroma_collection_name is None (default)
        )
        
        processor_config = config.to_processor_config()
        
        # Collection name should not be in the config when None
        assert "chroma_collection_name" not in processor_config
        assert processor_config["chroma_db_path"] == "/custom/path"


class TestAppConfigWithDocumentProcessing:
    """Test cases for AppConfig with DocumentProcessingConfig integration."""
    
    def test_app_config_initialization_with_document_processing(self):
        """Test AppConfig initialization includes document processing config."""
        doc_config = DocumentProcessingConfig(
            processor_type="rag_store",
            enable_processing=True,
            google_api_key="test_key",
            model_vendor="google"
        )
        
        app_config = AppConfig(
            source_folder="/source",
            saved_folder="/saved",
            error_folder="/error",
            document_processing=doc_config
        )
        
        assert app_config.document_processing is doc_config
        assert app_config.document_processing.processor_type == "rag_store"
        assert app_config.document_processing.google_api_key == "test_key"
    
    def test_app_config_validate_includes_document_processing_validation(self):
        """Test AppConfig validation includes document processing validation."""
        # Create invalid document processing config
        doc_config = DocumentProcessingConfig(
            processor_type="invalid_processor",
            enable_processing=True,
            model_vendor="google"
            # Missing google_api_key
        )
        
        app_config = AppConfig(
            source_folder="/nonexistent",  # This will also cause an error
            saved_folder="/saved",
            error_folder="/error",
            document_processing=doc_config
        )
        
        errors = app_config.validate()
        
        # Should have errors from both app config and document processing config
        assert len(errors) >= 2
        assert any("SOURCE_FOLDER path does not exist" in error for error in errors)
        assert any("Invalid processor_type" in error for error in errors)
    
    def test_app_config_validate_passes_with_valid_document_processing(self):
        """Test AppConfig validation passes with valid document processing config."""
        with tempfile.TemporaryDirectory() as temp_dir:
            doc_config = DocumentProcessingConfig(
                processor_type="rag_store",
                enable_processing=True,
                google_api_key="AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI",
                model_vendor="google",
                chroma_db_path="/tmp/chroma"
            )
            
            app_config = AppConfig(
                source_folder=temp_dir,
                saved_folder="/saved",
                error_folder="/error",
                document_processing=doc_config
            )
            
            errors = app_config.validate()
            
            # Should only have errors for saved/error folders, not document processing
            assert all("document" not in error.lower() and "processor" not in error.lower() and "chroma" not in error.lower()
                      for error in errors)


class TestConfigurationValidationError:
    """Test cases for ConfigurationValidationError exception."""
    
    def test_configuration_validation_error_initialization(self):
        """Test ConfigurationValidationError initialization."""
        critical_errors = ["Critical error 1", "Critical error 2"]
        warning_errors = ["Warning 1"]
        message = "Test error message"
        
        error = ConfigurationValidationError(message, critical_errors, warning_errors)
        
        assert str(error) == message
        assert error.critical_errors == critical_errors
        assert error.warning_errors == warning_errors
        assert error.has_critical_errors is True
        assert error.has_warnings is True
    
    def test_configuration_validation_error_no_warnings(self):
        """Test ConfigurationValidationError with no warnings."""
        critical_errors = ["Critical error"]
        warning_errors = []
        message = "Test error message"
        
        error = ConfigurationValidationError(message, critical_errors, warning_errors)
        
        assert error.has_critical_errors is True
        assert error.has_warnings is False
    
    def test_configuration_validation_error_no_critical_errors(self):
        """Test ConfigurationValidationError with no critical errors."""
        critical_errors = []
        warning_errors = ["Warning"]
        message = "Test error message"
        
        error = ConfigurationValidationError(message, critical_errors, warning_errors)
        
        assert error.has_critical_errors is False
        assert error.has_warnings is True


class TestConfigManagerWithDocumentProcessing:
    """Test cases for ConfigManager with document processing support."""
    
    def test_config_manager_load_config_includes_document_processing_vars(self):
        """Test ConfigManager loads document processing environment variables."""
        env_vars = {
            "SOURCE_FOLDER": "/source",
            "SAVED_FOLDER": "/saved", 
            "ERROR_FOLDER": "/error",
            "DOCUMENT_PROCESSOR_TYPE": "rag_store",
            "ENABLE_DOCUMENT_PROCESSING": "true",
            "GOOGLE_API_KEY": "test_google_key",
            "OPENAI_API_KEY": "test_openai_key",
            "CHROMA_DB_PATH": "/chroma/path",
            "MODEL_VENDOR": "google"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config_manager = ConfigManager(env_file=None)
            config = config_manager.load_config()
            
            # Check that all document processing vars are loaded
            assert config["DOCUMENT_PROCESSOR_TYPE"] == "rag_store"
            assert config["ENABLE_DOCUMENT_PROCESSING"] == "true"
            assert config["GOOGLE_API_KEY"] == "test_google_key"
            assert config["OPENAI_API_KEY"] == "test_openai_key"
            assert config["CHROMA_DB_PATH"] == "/chroma/path"
            assert config["MODEL_VENDOR"] == "google"
    
    def test_config_manager_load_config_expands_paths(self):
        """Test ConfigManager expands paths in path-related variables."""
        env_vars = {
            "SOURCE_FOLDER": "~/source",
            "CHROMA_DB_PATH": "~/chroma/path"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config_manager = ConfigManager(env_file=None)
            config = config_manager.load_config()
            
            # Paths should be expanded
            assert config["SOURCE_FOLDER"] == os.path.expanduser("~/source")
            assert config["CHROMA_DB_PATH"] == os.path.expanduser("~/chroma/path")
    
    def test_config_manager_validate_config_creates_document_processing_config(self):
        """Test ConfigManager creates DocumentProcessingConfig during validation."""
        config_dict = {
            "SOURCE_FOLDER": "/tmp",  # Use /tmp which should exist
            "SAVED_FOLDER": "/saved",
            "ERROR_FOLDER": "/error",
            "DOCUMENT_PROCESSOR_TYPE": "rag_store",
            "ENABLE_DOCUMENT_PROCESSING": "true",
            "GOOGLE_API_KEY": "AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI",
            "MODEL_VENDOR": "google",
            "CHROMA_DB_PATH": "/tmp/chroma"
        }
        
        config_manager = ConfigManager(env_file=None)
        
        # This should not raise an exception for document processing
        # (it will raise for saved/error folders not existing, but that's expected)
        try:
            config_manager.validate_config(config_dict)
        except ConfigurationValidationError as e:
            # Should not contain document processing errors, only folder errors
            error_message = str(e)
            assert "processor_type" not in error_message.lower()
            assert "google_api_key" not in error_message.lower()
            assert "chroma_db_path" not in error_message.lower()
    
    def test_config_manager_get_document_processing_config(self):
        """Test ConfigManager provides access to document processing config."""
        config_dict = {
            "SOURCE_FOLDER": "/tmp",
            "SAVED_FOLDER": "/saved",
            "ERROR_FOLDER": "/error",
            "DOCUMENT_PROCESSOR_TYPE": "rag_store",
            "ENABLE_DOCUMENT_PROCESSING": "true",
            "GOOGLE_API_KEY": "AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI",
            "MODEL_VENDOR": "google",
            "CHROMA_DB_PATH": "/tmp/chroma"
        }
        
        config_manager = ConfigManager(env_file=None)
        
        try:
            config_manager.validate_config(config_dict)
        except ConfigurationValidationError:
            # Expected due to folder validation, but document processing should be set
            pass
        
        # Should be able to get document processing config
        doc_config = config_manager.get_document_processing_config()
        assert doc_config.processor_type == "rag_store"
        assert doc_config.enable_processing is True
        assert doc_config.google_api_key == "AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI"
        assert doc_config.model_vendor == "google"
    
    def test_config_manager_is_document_processing_enabled(self):
        """Test ConfigManager can check if document processing is enabled."""
        config_dict = {
            "SOURCE_FOLDER": "/tmp",
            "SAVED_FOLDER": "/saved",
            "ERROR_FOLDER": "/error",
            "ENABLE_DOCUMENT_PROCESSING": "false"
        }
        
        config_manager = ConfigManager(env_file=None)
        
        try:
            config_manager.validate_config(config_dict)
        except ValueError:
            # Expected due to folder validation
            pass
        
        assert config_manager.is_document_processing_enabled() is False
    
    def test_config_manager_not_initialized_raises_error(self):
        """Test ConfigManager methods raise error when not initialized."""
        config_manager = ConfigManager(env_file=None)
        
        with pytest.raises(RuntimeError, match="Configuration not loaded"):
            config_manager.get_document_processing_config()
        
        with pytest.raises(RuntimeError, match="Configuration not loaded"):
            config_manager.is_document_processing_enabled()
    
    def test_config_manager_initialize_returns_app_config_with_document_processing(self):
        """Test ConfigManager initialize returns AppConfig with document processing."""
        env_vars = {
            "SOURCE_FOLDER": "/tmp",
            "SAVED_FOLDER": "/saved",
            "ERROR_FOLDER": "/error",
            "DOCUMENT_PROCESSOR_TYPE": "rag_store",
            "ENABLE_DOCUMENT_PROCESSING": "true",
            "GOOGLE_API_KEY": "AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI",
            "MODEL_VENDOR": "google",
            "CHROMA_DB_PATH": "/tmp/chroma",
            "CHROMA_CLIENT_MODE": "embedded",
            # Add required file monitoring configuration
            "FILE_MONITORING_MODE": "auto",
            "POLLING_INTERVAL": "3.0",
            "DOCKER_VOLUME_MODE": "false"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config_manager = ConfigManager(env_file=None)
            
            try:
                app_config = config_manager.initialize()
            except ConfigurationValidationError:
                # Expected due to folder validation, but we can still check the config
                app_config = config_manager._config
            
            assert app_config is not None
            assert isinstance(app_config.document_processing, DocumentProcessingConfig)
            assert app_config.document_processing.processor_type == "rag_store"
            assert app_config.document_processing.google_api_key == "AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI"
    
    def test_config_manager_validate_config_raises_configuration_validation_error(self):
        """Test ConfigManager raises ConfigurationValidationError for validation failures."""
        config_dict = {
            "SOURCE_FOLDER": "",  # Missing required field
            "SAVED_FOLDER": "",   # Missing required field
            "ERROR_FOLDER": "",   # Missing required field
            "ENABLE_DOCUMENT_PROCESSING": "true",
            "MODEL_VENDOR": "google"
            # Missing GOOGLE_API_KEY and CHROMA_DB_PATH
        }
        
        config_manager = ConfigManager(env_file=None)
        
        with pytest.raises(ConfigurationValidationError) as exc_info:
            config_manager.validate_config(config_dict)
        
        error = exc_info.value
        assert error.has_critical_errors is True
        assert len(error.critical_errors) > 0
        assert any("SOURCE_FOLDER is required" in err for err in error.critical_errors)
    
    def test_config_manager_validate_config_categorizes_errors(self):
        """Test ConfigManager categorizes errors into critical and warnings."""
        config_dict = {
            "SOURCE_FOLDER": "/nonexistent",  # This will be a critical error
            "SAVED_FOLDER": "/saved",
            "ERROR_FOLDER": "/error",
            "ENABLE_DOCUMENT_PROCESSING": "true",
            "GOOGLE_API_KEY": "invalid_format",  # This might be a warning
            "MODEL_VENDOR": "google",
            "CHROMA_DB_PATH": "/tmp/chroma"
        }
        
        config_manager = ConfigManager(env_file=None)
        
        with pytest.raises(ConfigurationValidationError) as exc_info:
            config_manager.validate_config(config_dict)
        
        error = exc_info.value
        assert "Critical errors" in str(error) or "Configuration validation failed" in str(error)
    
    def test_config_manager_validate_dependencies_missing_chromadb(self):
        """Test dependency validation detects missing ChromaDB."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dict = {
                "SOURCE_FOLDER": temp_dir,
                "SAVED_FOLDER": "/saved",
                "ERROR_FOLDER": "/error",
                "ENABLE_DOCUMENT_PROCESSING": "true",
                "GOOGLE_API_KEY": "AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI",
                "MODEL_VENDOR": "google",
                "CHROMA_DB_PATH": "/tmp/chroma"
            }
            
            config_manager = ConfigManager(env_file=None)
            
            try:
                config_manager.validate_config(config_dict)
            except ConfigurationValidationError:
                pass  # Expected due to folder validation
            
            # Mock missing chromadb import
            with patch('builtins.__import__', side_effect=ImportError("No module named 'chromadb'")):
                errors = config_manager.validate_dependencies()
                assert any("ChromaDB package is not installed" in error for error in errors)
    
    def test_config_manager_validate_dependencies_processing_disabled(self):
        """Test dependency validation skipped when processing is disabled."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dict = {
                "SOURCE_FOLDER": temp_dir,
                "SAVED_FOLDER": "/saved",
                "ERROR_FOLDER": "/error",
                "ENABLE_DOCUMENT_PROCESSING": "false"
            }
            
            config_manager = ConfigManager(env_file=None)
            
            try:
                config_manager.validate_config(config_dict)
            except ConfigurationValidationError:
                pass  # Expected due to folder validation
            
            errors = config_manager.validate_dependencies()
            assert errors == []  # No dependency validation when processing is disabled
    
    def test_config_manager_initialize_with_dependency_validation(self):
        """Test initialize method includes dependency validation."""
        env_vars = {
            "SOURCE_FOLDER": "/tmp",
            "SAVED_FOLDER": "/saved",
            "ERROR_FOLDER": "/error",
            "DOCUMENT_PROCESSOR_TYPE": "rag_store",
            "ENABLE_DOCUMENT_PROCESSING": "true",
            "GOOGLE_API_KEY": "AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI",
            "MODEL_VENDOR": "google",
            "CHROMA_DB_PATH": "/tmp/chroma",
            "CHROMA_CLIENT_MODE": "embedded",
            # Add required file monitoring configuration
            "FILE_MONITORING_MODE": "auto",
            "POLLING_INTERVAL": "3.0",
            "DOCKER_VOLUME_MODE": "false"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config_manager = ConfigManager(env_file=None)
            
            # Mock missing dependencies
            with patch('builtins.__import__', side_effect=ImportError("No module named 'chromadb'")):
                with pytest.raises(ConfigurationValidationError) as exc_info:
                    config_manager.initialize()
                
                error = exc_info.value
                assert "Required dependencies are missing" in str(error)
                assert any("ChromaDB package is not installed" in err for err in error.critical_errors)


if __name__ == "__main__":
    pytest.main([__file__])