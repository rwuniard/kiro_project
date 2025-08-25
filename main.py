#!/usr/bin/env python3
"""
Folder File Processor - Main Application Entry Point

This application monitors a configurable source folder for new files,
processes them, and moves them to appropriate destination folders based
on processing results.
"""

import sys
import os
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from app import create_app


def main():
    """Main application entry point."""
    print("Folder File Processor starting...")
    
    # Create application instance
    app = create_app(env_file='.env', log_file='logs/application.log')
    
    # Run the application
    exit_code = app.run()
    
    return exit_code


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nApplication stopped by user.")
        sys.exit(0)
    except Exception as e:
        print(f"Application failed to start: {e}")
        sys.exit(1)