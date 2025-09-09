#!/usr/bin/env python3
"""
Environment configuration generator for Kiro Project Docker deployment.

This script generates the final .env file by merging:
1. .env.template (base template)
2. Environment-specific settings (config/*.json)
3. API keys from various sources (GitHub secrets, local files)
4. Platform-specific folder paths
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional


class EnvironmentGenerator:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.docker_deployment_dir = project_root / "docker_deployment"
        self.shared_dir = self.docker_deployment_dir / "shared"
        self.config_dir = self.shared_dir / "config"
        self.template_file = self.shared_dir / ".env.template"
        self.output_file = self.docker_deployment_dir / ".env.generated"
        
    def load_json_config(self, filename: str) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        config_path = self.config_dir / filename
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Warning: {config_path} not found")
            return {}
        except json.JSONDecodeError as e:
            print(f"Error parsing {config_path}: {e}")
            return {}
    
    def load_template(self) -> str:
        """Load the .env.template file."""
        try:
            with open(self.template_file, 'r') as f:
                return f.read()
        except FileNotFoundError:
            print(f"Error: Template file {self.template_file} not found")
            sys.exit(1)
    
    def get_api_keys(self, environment: str) -> Dict[str, str]:
        """Get API keys based on environment (production vs development)."""
        api_keys = {}
        
        if environment == "production":
            # In production, read from environment variables (GitHub secrets)
            api_keys["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "")
            api_keys["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY", "")
        else:
            # In development, try local .env.local file first, then environment
            local_env_file = self.project_root / ".env.local"
            if local_env_file.exists():
                with open(local_env_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            if key in ["OPENAI_API_KEY", "GOOGLE_API_KEY"]:
                                api_keys[key] = value.strip('"\'')
            
            # Fallback to environment variables
            if not api_keys.get("OPENAI_API_KEY"):
                api_keys["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "")
            if not api_keys.get("GOOGLE_API_KEY"):
                api_keys["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY", "")
        
        return api_keys
    
    def get_platform_paths(self, platform: str) -> Dict[str, str]:
        """Get platform-specific folder paths."""
        if platform.lower() == "windows":
            return self.load_json_config("windows_paths.json")
        else:
            return self.load_json_config("unix_paths.json")
    
    def get_chroma_settings(self, environment: str) -> Dict[str, str]:
        """Get ChromaDB settings based on environment."""
        if environment == "production":
            config = self.load_json_config("prod_chroma_settings.json")
        else:
            config = self.load_json_config("dev_chroma_settings.json")
        
        # Convert values to strings and handle null values
        chroma_settings = {}
        for key, value in config.items():
            if key.startswith("chroma_"):
                env_key = key.upper()
                chroma_settings[env_key] = str(value) if value is not None else ""
        
        return chroma_settings
    
    def get_file_monitoring_settings(self, environment: str) -> Dict[str, str]:
        """Get file monitoring settings optimized for Docker deployment."""
        # Docker deployment should use polling mode with optimizations
        return {
            "FILE_MONITORING_MODE": "auto",  # Auto-detect Docker environment
            "POLLING_INTERVAL": "2.0",       # Faster polling for Docker
            "DOCKER_VOLUME_MODE": "true"     # Enable Docker optimizations
        }
    
    def generate_env_file(self, environment: str = "development", 
                         platform: str = "unix", 
                         model_vendor: str = "openai") -> bool:
        """Generate the final .env file."""
        print(f"Generating .env file for {environment} environment on {platform} platform")
        
        # Load template
        template_content = self.load_template()
        
        # Gather all configuration values
        replacements = {}
        
        # Get platform-specific paths
        path_config = self.get_platform_paths(platform)
        if path_config:
            replacements["SOURCE_FOLDER"] = path_config.get("source_folder", "/tmp/kiro/source")
            replacements["SAVED_FOLDER"] = path_config.get("saved_folder", "/tmp/kiro/saved")
            replacements["ERROR_FOLDER"] = path_config.get("error_folder", "/tmp/kiro/error")
        
        # Get API keys
        api_keys = self.get_api_keys(environment)
        
        # Only include the API key for the selected model vendor
        if model_vendor == "google":
            replacements["GOOGLE_API_KEY"] = api_keys.get("GOOGLE_API_KEY", "")
            replacements["OPENAI_API_KEY"] = ""  # Set empty to avoid undefined variable
        elif model_vendor == "openai":
            replacements["OPENAI_API_KEY"] = api_keys.get("OPENAI_API_KEY", "")
            replacements["GOOGLE_API_KEY"] = ""  # Set empty to avoid undefined variable
        else:
            # Include both if vendor is unrecognized (fallback)
            replacements.update(api_keys)
        
        # Get ChromaDB settings
        chroma_settings = self.get_chroma_settings(environment)
        replacements.update(chroma_settings)
        
        # Get file monitoring settings
        file_monitoring_settings = self.get_file_monitoring_settings(environment)
        replacements.update(file_monitoring_settings)
        
        # Set model vendor
        replacements["MODEL_VENDOR"] = model_vendor
        
        # Validate required values
        required_keys = ["SOURCE_FOLDER", "SAVED_FOLDER", "ERROR_FOLDER"]
        missing_keys = [key for key in required_keys if not replacements.get(key)]
        
        if missing_keys:
            print(f"Error: Missing required configuration values: {missing_keys}")
            return False
        
        # Validate API keys based on selected vendor
        if model_vendor == "google" and not replacements.get("GOOGLE_API_KEY"):
            print("Warning: No Google API key found. Document processing may not work.")
        elif model_vendor == "openai" and not replacements.get("OPENAI_API_KEY"):
            print("Warning: No OpenAI API key found. Document processing may not work.")
        
        # Replace placeholders in template
        env_content = template_content
        for key, value in replacements.items():
            placeholder = f"{{{{{key}}}}}"
            env_content = env_content.replace(placeholder, str(value))
        
        # Write the generated .env file
        try:
            with open(self.output_file, 'w') as f:
                f.write(env_content)
            print(f"Successfully generated {self.output_file}")
            
            # Show configuration summary
            print("\nConfiguration Summary:")
            print(f"  Environment: {environment}")
            print(f"  Platform: {platform}")
            print(f"  Model Vendor: {model_vendor}")
            print(f"  Source Folder: {replacements.get('SOURCE_FOLDER')}")
            print(f"  Saved Folder: {replacements.get('SAVED_FOLDER')}")
            print(f"  Error Folder: {replacements.get('ERROR_FOLDER')}")
            print(f"  File Monitoring: {replacements.get('FILE_MONITORING_MODE')} mode")
            print(f"  Polling Interval: {replacements.get('POLLING_INTERVAL')}s")
            print(f"  Docker Optimized: {replacements.get('DOCKER_VOLUME_MODE')}")
            print(f"  OpenAI API Key: {'✓' if replacements.get('OPENAI_API_KEY') else '✗'}")
            print(f"  Google API Key: {'✓' if replacements.get('GOOGLE_API_KEY') else '✗'}")
            
            return True
            
        except Exception as e:
            print(f"Error writing {self.output_file}: {e}")
            return False


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate environment configuration for Kiro Project")
    parser.add_argument("--environment", "-e", 
                       choices=["development", "production"], 
                       default="development",
                       help="Target environment (default: development)")
    parser.add_argument("--platform", "-p",
                       choices=["windows", "unix"],
                       default="unix", 
                       help="Target platform (default: unix)")
    parser.add_argument("--model-vendor", "-m",
                       choices=["openai", "google"],
                       default="google",
                       help="AI model vendor (default: google)")
    
    args = parser.parse_args()
    
    # Get project root (parent of docker_deployment directory)
    # Script is now in docker_deployment/shared/scripts/, so go up 3 levels
    project_root = Path(__file__).parent.parent.parent.parent.absolute()
    
    # Generate environment file
    generator = EnvironmentGenerator(project_root)
    success = generator.generate_env_file(
        environment=args.environment,
        platform=args.platform,
        model_vendor=args.model_vendor
    )
    
    if not success:
        sys.exit(1)
    
    print(f"\nNext steps:")
    print(f"1. Review the generated .env.generated file")
    print(f"2. Copy to .env: cp .env.generated .env")
    print(f"3. Run Docker: docker-compose up --build")


if __name__ == "__main__":
    main()