"""
Unit tests for configuration validation error scenarios.

Tests various error conditions and edge cases for document processing
configuration validation and error handling.
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


class TestConfigurationValidationErrorScenarios:
    """Test cases for various configuration validation error scenarios."""
    
    def test_missing_all_required_environment_variables(self):
        """Test error handling when all required environment variables are missing."""
        with patch.dict(os.environ, {}, clear=True):
            config_manager = ConfigManager(env_file=None)
            
            with pytest.raises(ConfigurationValidationError) as exc_info:
                config_manager.initialize()
            
            error = exc_info.value
            assert error.has_critical_errors is True
            assert len(error.critical_errors) >= 3  # SOURCE_FOLDER, SAVED_FOLDER, ERROR_FOLDER
            assert any("SOURCE_FOLDER is required" in err for err in error.critical_errors)
            assert any("SAVED_FOLDER is required" in err for err in error.critical_errors)
            assert any("ERROR_FOLDER is required" in err for err in error.critical_errors)
    
    def test_invalid_api_key_formats_for_both_vendors(self):
        """Test error handling for invalid API key formats for both vendors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dict = {
                "SOURCE_FOLDER": temp_dir,
                "SAVED_FOLDER": "/saved",
                "ERROR_FOLDER": "/error",
                "ENABLE_DOCUMENT_PROCESSING": "true",
                "GOOGLE_API_KEY": "invalid_google_key",
                "OPENAI_API_KEY": "invalid_openai_key",
                "MODEL_VENDOR": "google",
                "CHROMA_DB_PATH": "/tmp/chroma"
            }
            
            config_manager = ConfigManager(env_file=None)
            
            with pytest.raises(ConfigurationValidationError) as exc_info:
                config_manager.validate_config(config_dict)
            
            error_message = str(exc_info.value)
            assert "GOOGLE_API_KEY format appears invalid" in error_message
    
    def test_chroma_db_path_permission_errors(self):
        """Test error handling for ChromaDB path permission issues."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a directory with restricted permissions
            restricted_dir = os.path.join(temp_dir, "restricted")
            os.makedirs(restricted_dir)
            os.chmod(restricted_dir, 0o444)  # Read-only
            
            chroma_path = os.path.join(restricted_dir, "chroma_db")
            
            config = DocumentProcessingConfig(
                processor_type="rag_store",
                enable_processing=True,
                google_api_key="AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI",
                model_vendor="google",
                chroma_db_path=chroma_path
            )
            
            errors = config.validate()
            # Should detect permission issues
            assert any("not writable" in error for error in errors)
            
            # Restore permissions for cleanup
            os.chmod(restricted_dir, 0o755)
    
    def test_chroma_db_path_invalid_characters(self):
        """Test error handling for ChromaDB path with invalid characters."""
        # Use a path that will definitely cause an OSError
        config = DocumentProcessingConfig(
            processor_type="rag_store",
            enable_processing=True,
            google_api_key="AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI",
            model_vendor="google",
            chroma_db_path=""  # Empty path should cause an error
        )
        
        errors = config.validate()
        assert any("CHROMA_DB_PATH is required" in error for error in errors)
    
    def test_configuration_with_mixed_error_types(self):
        """Test configuration validation with both critical and warning errors."""
        config_dict = {
            "SOURCE_FOLDER": "/nonexistent/path",  # Critical: path doesn't exist
            "SAVED_FOLDER": "",  # Critical: required but empty
            "ERROR_FOLDER": "/error",
            "ENABLE_DOCUMENT_PROCESSING": "true",
            "GOOGLE_API_KEY": "invalid_format",  # Warning: invalid format
            "MODEL_VENDOR": "google",
            "CHROMA_DB_PATH": "/tmp/chroma"
        }
        
        config_manager = ConfigManager(env_file=None)
        
        with pytest.raises(ConfigurationValidationError) as exc_info:
            config_manager.validate_config(config_dict)
        
        error = exc_info.value
        assert error.has_critical_errors is True
        assert len(error.critical_errors) >= 1
        
        error_message = str(error)
        assert "Critical errors" in error_message
    
    def test_dependency_validation_multiple_missing_packages(self):
        """Test dependency validation with multiple missing packages."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create saved and error directories for the test
            saved_dir = Path(temp_dir) / "saved"
            error_dir = Path(temp_dir) / "error"
            saved_dir.mkdir(exist_ok=True)
            error_dir.mkdir(exist_ok=True)
            
            config_dict = {
                "SOURCE_FOLDER": temp_dir,
                "SAVED_FOLDER": str(saved_dir),
                "ERROR_FOLDER": str(error_dir),
                "ENABLE_DOCUMENT_PROCESSING": "true",
                "GOOGLE_API_KEY": "AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI",
                "MODEL_VENDOR": "google",
                "CHROMA_DB_PATH": "/tmp/chroma"
            }
            
            config_manager = ConfigManager(env_file=None)
            
            # Validate config successfully first
            result = config_manager.validate_config(config_dict)
            assert result is True
            
            # Mock multiple missing imports
            original_import = __builtins__['__import__']
            def mock_import(name, *args, **kwargs):
                if name in ['chromadb', 'google.generativeai', 'pypdf', 'python_docx', 'docx']:
                    raise ImportError(f"No module named '{name}'")
                return original_import(name, *args, **kwargs)
            
            with patch('builtins.__import__', side_effect=mock_import):
                errors = config_manager.validate_dependencies()
                
                assert len(errors) >= 3  # ChromaDB, Google AI, PDF/DOCX processors
                assert any("ChromaDB package is not installed" in error for error in errors)
                assert any("Google Generative AI package is not installed" in error for error in errors)
                assert any("PDF processing library is not installed" in error for error in errors)
    
    def test_openai_vendor_missing_dependencies(self):
        """Test dependency validation for OpenAI vendor with missing packages."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create saved and error directories for the test
            saved_dir = Path(temp_dir) / "saved"
            error_dir = Path(temp_dir) / "error"
            saved_dir.mkdir(exist_ok=True)
            error_dir.mkdir(exist_ok=True)
            
            config_dict = {
                "SOURCE_FOLDER": temp_dir,
                "SAVED_FOLDER": str(saved_dir),
                "ERROR_FOLDER": str(error_dir),
                "ENABLE_DOCUMENT_PROCESSING": "true",
                "OPENAI_API_KEY": "sk-1234567890abcdef1234567890abcdef",
                "MODEL_VENDOR": "openai",
                "CHROMA_DB_PATH": "/tmp/chroma"
            }
            
            config_manager = ConfigManager(env_file=None)
            
            # Validate config successfully first
            result = config_manager.validate_config(config_dict)
            assert result is True
            
            # Mock missing OpenAI import
            original_import = __builtins__['__import__']
            def mock_import(name, *args, **kwargs):
                if name == 'openai':
                    raise ImportError("No module named 'openai'")
                return original_import(name, *args, **kwargs)
            
            with patch('builtins.__import__', side_effect=mock_import):
                errors = config_manager.validate_dependencies()
                assert any("OpenAI package is not installed" in error for error in errors)
    
    def test_configuration_validation_unexpected_exception(self):
        """Test handling of unexpected exceptions during configuration validation."""
        config_manager = ConfigManager(env_file=None)
        
        # Mock an unexpected exception during validation
        with patch.object(DocumentProcessingConfig, 'validate', side_effect=RuntimeError("Unexpected error")):
            config_dict = {
                "SOURCE_FOLDER": "/tmp",
                "SAVED_FOLDER": "/saved",
                "ERROR_FOLDER": "/error"
            }
            
            with pytest.raises(ConfigurationValidationError) as exc_info:
                config_manager.validate_config(config_dict)
            
            error = exc_info.value
            assert "Unexpected error during configuration validation" in str(error)
            assert error.has_critical_errors is True
    
    def test_api_key_validation_edge_cases(self):
        """Test API key validation with edge cases."""
        # Test empty string API key
        config = DocumentProcessingConfig(
            processor_type="rag_store",
            enable_processing=True,
            google_api_key="",  # Empty string
            model_vendor="google",
            chroma_db_path="/tmp/chroma"
        )
        
        errors = config.validate()
        assert any("GOOGLE_API_KEY is required" in error for error in errors)
        
        # Test None API key (should be handled the same way)
        config.google_api_key = None
        errors = config.validate()
        assert any("GOOGLE_API_KEY is required" in error for error in errors)
        
        # Test API key that's too short
        config.google_api_key = "AIza123"  # Too short
        errors = config.validate()
        assert any("GOOGLE_API_KEY format appears invalid" in error for error in errors)
        
        # Test API key with wrong prefix
        config.google_api_key = "WRONG_PREFIX_1234567890123456789012345"
        errors = config.validate()
        assert any("GOOGLE_API_KEY format appears invalid" in error for error in errors)
    
    def test_chroma_db_path_edge_cases(self):
        """Test ChromaDB path validation with edge cases."""
        # Test relative path
        config = DocumentProcessingConfig(
            processor_type="rag_store",
            enable_processing=True,
            google_api_key="AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI",
            model_vendor="google",
            chroma_db_path="./relative/path"
        )
        
        errors = config.validate()
        # Should handle relative paths (may or may not be valid depending on current directory)
        
        # Test empty string path
        config.chroma_db_path = ""
        errors = config.validate()
        assert any("CHROMA_DB_PATH is required" in error for error in errors)
        
        # Test path with spaces
        with tempfile.TemporaryDirectory() as temp_dir:
            spaced_path = os.path.join(temp_dir, "path with spaces", "chroma")
            config.chroma_db_path = spaced_path
            errors = config.validate()
            # Should be valid if parent directory exists
    
    def test_model_vendor_case_sensitivity(self):
        """Test model vendor validation with different cases."""
        config = DocumentProcessingConfig(
            processor_type="rag_store",
            enable_processing=True,
            google_api_key="AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI",
            model_vendor="GOOGLE",  # Uppercase
            chroma_db_path="/tmp/chroma"
        )
        
        errors = config.validate()
        assert any("Invalid model_vendor 'GOOGLE'" in error for error in errors)
        
        # Test mixed case
        config.model_vendor = "Google"
        errors = config.validate()
        assert any("Invalid model_vendor 'Google'" in error for error in errors)
    
    def test_processor_type_validation_edge_cases(self):
        """Test processor type validation with edge cases."""
        config = DocumentProcessingConfig(
            processor_type="",  # Empty string
            enable_processing=True,
            google_api_key="AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI",
            model_vendor="google",
            chroma_db_path="/tmp/chroma"
        )
        
        errors = config.validate()
        assert any("Invalid processor_type ''" in error for error in errors)
        
        # Test None processor type
        config.processor_type = None
        errors = config.validate()
        assert any("Invalid processor_type 'None'" in error for error in errors)


if __name__ == "__main__":
    pytest.main([__file__])