"""
Tests for Docker deployment configuration and environment generation.

This module tests the Docker deployment scripts and configuration to ensure
the new hybrid file monitoring settings are properly integrated.
"""

import os
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, mock_open

import pytest

# Import the environment generator
import sys
docker_deployment_path = Path(__file__).parent.parent / "docker_deployment"
sys.path.insert(0, str(docker_deployment_path))

#from scripts.generate_env import EnvironmentGenerator
from docker_deployment.shared.scripts.generate_env import EnvironmentGenerator


class TestEnvironmentGenerator:
    """Tests for the Docker environment generator."""
    
    @pytest.fixture
    def temp_project_root(self):
        """Create temporary project structure for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create docker_deployment structure
            docker_deployment_dir = temp_path / "docker_deployment"
            docker_deployment_dir.mkdir()
            
            config_dir = docker_deployment_dir / "config"
            config_dir.mkdir()
            
            # Create test configuration files
            unix_paths = {
                "source_folder": "~/tmp/test/source",
                "saved_folder": "~/tmp/test/saved", 
                "error_folder": "~/tmp/test/error"
            }
            
            windows_paths = {
                "source_folder": "C:\\tmp\\test\\source",
                "saved_folder": "C:\\tmp\\test\\saved",
                "error_folder": "C:\\tmp\\test\\error"
            }
            
            dev_chroma = {
                "chroma_client_mode": "embedded",
                "chroma_server_host": "localhost",
                "chroma_server_port": 8000,
                "chroma_collection_name": "test-collection"
            }
            
            # Write config files
            with open(config_dir / "unix_paths.json", 'w') as f:
                json.dump(unix_paths, f)
                
            with open(config_dir / "windows_paths.json", 'w') as f:
                json.dump(windows_paths, f)
                
            with open(config_dir / "dev_chroma_settings.json", 'w') as f:
                json.dump(dev_chroma, f)
            
            # Create template file
            template_content = """# Test template
SOURCE_FOLDER={{SOURCE_FOLDER}}
SAVED_FOLDER={{SAVED_FOLDER}}
ERROR_FOLDER={{ERROR_FOLDER}}
MODEL_VENDOR={{MODEL_VENDOR}}
FILE_MONITORING_MODE={{FILE_MONITORING_MODE}}
POLLING_INTERVAL={{POLLING_INTERVAL}}
DOCKER_VOLUME_MODE={{DOCKER_VOLUME_MODE}}
CHROMA_CLIENT_MODE={{CHROMA_CLIENT_MODE}}
"""
            
            template_file = docker_deployment_dir / ".env.template"
            template_file.write_text(template_content)
            
            yield temp_path
    
    def test_environment_generator_initialization(self, temp_project_root):
        """Test EnvironmentGenerator initialization."""
        generator = EnvironmentGenerator(temp_project_root)
        
        assert generator.project_root == temp_project_root
        assert generator.docker_deployment_dir == temp_project_root / "docker_deployment"
        assert generator.config_dir == temp_project_root / "docker_deployment" / "config"
    
    def test_load_platform_paths_unix(self, temp_project_root):
        """Test loading Unix platform paths."""
        generator = EnvironmentGenerator(temp_project_root)
        paths = generator.get_platform_paths("unix")
        
        assert paths["source_folder"] == "~/tmp/test/source"
        assert paths["saved_folder"] == "~/tmp/test/saved"
        assert paths["error_folder"] == "~/tmp/test/error"
    
    def test_load_platform_paths_windows(self, temp_project_root):
        """Test loading Windows platform paths."""
        generator = EnvironmentGenerator(temp_project_root)
        paths = generator.get_platform_paths("windows")
        
        assert paths["source_folder"] == "C:\\tmp\\test\\source"
        assert paths["saved_folder"] == "C:\\tmp\\test\\saved"
        assert paths["error_folder"] == "C:\\tmp\\test\\error"
    
    def test_file_monitoring_settings(self, temp_project_root):
        """Test file monitoring settings for Docker deployment."""
        generator = EnvironmentGenerator(temp_project_root)
        settings = generator.get_file_monitoring_settings("development")
        
        assert settings["FILE_MONITORING_MODE"] == "auto"
        assert settings["POLLING_INTERVAL"] == "2.0"
        assert settings["DOCKER_VOLUME_MODE"] == "true"
    
    def test_chroma_settings(self, temp_project_root):
        """Test ChromaDB settings loading."""
        generator = EnvironmentGenerator(temp_project_root)
        settings = generator.get_chroma_settings("development")
        
        assert settings["CHROMA_CLIENT_MODE"] == "embedded"
        assert settings["CHROMA_SERVER_HOST"] == "localhost"
        assert settings["CHROMA_SERVER_PORT"] == "8000"
        assert settings["CHROMA_COLLECTION_NAME"] == "test-collection"
    
    @patch.dict(os.environ, {"GOOGLE_API_KEY": "test-google-key"})
    def test_api_keys_development(self, temp_project_root):
        """Test API key handling in development mode."""
        generator = EnvironmentGenerator(temp_project_root)
        api_keys = generator.get_api_keys("development")
        
        assert api_keys.get("GOOGLE_API_KEY") == "test-google-key"
    
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-openai-key"})
    def test_generate_env_file_unix_openai(self, temp_project_root):
        """Test complete environment file generation for Unix with OpenAI."""
        generator = EnvironmentGenerator(temp_project_root)
        
        success = generator.generate_env_file(
            environment="development",
            platform="unix", 
            model_vendor="openai"
        )
        
        assert success is True
        assert generator.output_file.exists()
        
        # Read and verify generated content
        content = generator.output_file.read_text()
        
        assert "SOURCE_FOLDER=~/tmp/test/source" in content
        assert "MODEL_VENDOR=openai" in content
        assert "FILE_MONITORING_MODE=auto" in content
        assert "POLLING_INTERVAL=2.0" in content
        assert "DOCKER_VOLUME_MODE=true" in content
    
    @patch.dict(os.environ, {"GOOGLE_API_KEY": "test-google-key"})
    def test_generate_env_file_windows_google(self, temp_project_root):
        """Test complete environment file generation for Windows with Google."""
        generator = EnvironmentGenerator(temp_project_root)
        
        success = generator.generate_env_file(
            environment="development",
            platform="windows",
            model_vendor="google"
        )
        
        assert success is True
        assert generator.output_file.exists()
        
        # Read and verify generated content  
        content = generator.output_file.read_text()
        
        assert "SOURCE_FOLDER=C:\\tmp\\test\\source" in content
        assert "MODEL_VENDOR=google" in content
        assert "FILE_MONITORING_MODE=auto" in content
        assert "POLLING_INTERVAL=2.0" in content
        assert "DOCKER_VOLUME_MODE=true" in content
    
    def test_generate_env_file_missing_paths(self, temp_project_root):
        """Test environment generation with missing path configuration."""
        # Remove path configuration files
        (temp_project_root / "docker_deployment" / "config" / "unix_paths.json").unlink()
        
        generator = EnvironmentGenerator(temp_project_root)
        
        success = generator.generate_env_file(
            environment="development",
            platform="unix",
            model_vendor="openai"
        )
        
        # Should fail due to missing required paths
        assert success is False


class TestDockerDeploymentIntegration:
    """Integration tests for Docker deployment configuration."""
    
    def test_template_has_monitoring_placeholders(self):
        """Test that the .env.template includes file monitoring placeholders."""
        template_path = Path(__file__).parent.parent / "docker_deployment" / ".env.template"
        
        if template_path.exists():
            content = template_path.read_text()
            
            assert "{{FILE_MONITORING_MODE}}" in content
            assert "{{POLLING_INTERVAL}}" in content  
            assert "{{DOCKER_VOLUME_MODE}}" in content
    
    def test_deployment_script_integration(self):
        """Test that deployment scripts have been updated."""
        scripts_dir = Path(__file__).parent.parent / "docker_deployment"
        
        unix_script = scripts_dir / "deploy-local.sh"
        windows_script = scripts_dir / "deploy-local.bat"
        
        if unix_script.exists():
            content = unix_script.read_text()
            assert "Hybrid (Docker-optimized)" in content or "File Monitoring" in content
        
        if windows_script.exists():
            content = windows_script.read_text()
            assert "Hybrid (Docker-optimized)" in content or "File Monitoring" in content


class TestDockerConfigurationValues:
    """Test specific Docker configuration values and settings."""
    
    def test_docker_optimized_settings(self):
        """Test that Docker-optimized settings are appropriate."""
        # Create a minimal generator to test settings
        from scripts.generate_env import EnvironmentGenerator
        
        # Mock the project root since we just need the method
        generator = EnvironmentGenerator(Path("/tmp"))
        settings = generator.get_file_monitoring_settings("development")
        
        # Verify Docker-optimized values
        assert settings["FILE_MONITORING_MODE"] == "auto"  # Auto-detect Docker
        assert float(settings["POLLING_INTERVAL"]) <= 3.0  # Fast enough for Docker
        assert settings["DOCKER_VOLUME_MODE"] == "true"    # Docker optimizations enabled
    
    def test_polling_interval_range(self):
        """Test that polling interval is in reasonable range for Docker."""
        from scripts.generate_env import EnvironmentGenerator
        
        generator = EnvironmentGenerator(Path("/tmp"))
        settings = generator.get_file_monitoring_settings("development")
        
        interval = float(settings["POLLING_INTERVAL"])
        assert 0.5 <= interval <= 5.0  # Reasonable range for Docker volumes
    
    def test_monitoring_mode_options(self):
        """Test that monitoring mode is set to auto for Docker detection."""
        from scripts.generate_env import EnvironmentGenerator
        
        generator = EnvironmentGenerator(Path("/tmp"))
        settings = generator.get_file_monitoring_settings("development")
        
        mode = settings["FILE_MONITORING_MODE"]
        assert mode in ["auto", "events", "polling"]
        assert mode == "auto"  # Should use auto-detection for Docker deployment


@pytest.fixture
def cleanup_generated_files():
    """Cleanup any generated .env files after tests."""
    yield
    
    # Cleanup
    docker_deployment_path = Path(__file__).parent.parent / "docker_deployment"
    generated_file = docker_deployment_path / ".env.generated"
    
    try:
        if generated_file.exists():
            generated_file.unlink()
    except OSError:
        pass  # Ignore cleanup errors