@echo off
REM Windows deployment script for Kiro Project local Docker deployment
REM This script reads Windows-specific paths and generates the environment file

setlocal EnableDelayedExpansion

echo ============================================
echo   Kiro Project - Local Docker Deployment
echo   Platform: Windows
echo   File Monitoring: Hybrid (Docker-optimized)
echo ============================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ and try again
    pause
    exit /b 1
)

REM Check if Docker is available
docker --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker is not installed or not running
    echo Please install Docker Desktop and ensure it's running
    pause
    exit /b 1
)

REM Check if docker-compose is available
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: docker-compose is not installed or not in PATH
    echo Please install docker-compose and try again
    pause
    exit /b 1
)

REM Change to script directory for relative path resolution
cd /d "%~dp0"

echo [1/5] Checking required files...

REM Check if required files exist
if not exist "scripts\generate_env.py" (
    echo ERROR: scripts\generate_env.py not found
    pause
    exit /b 1
)

if not exist "config\windows_paths.json" (
    echo ERROR: config\windows_paths.json not found
    pause
    exit /b 1
)

if not exist ".env.template" (
    echo ERROR: .env.template not found
    pause
    exit /b 1
)

echo [2/5] Creating local directories...

REM Read paths from Windows configuration file
for /f "tokens=2 delims=:," %%a in ('type config\windows_paths.json ^| findstr "source_folder"') do (
    set SOURCE_PATH=%%a
    set SOURCE_PATH=!SOURCE_PATH:"=!
    set SOURCE_PATH=!SOURCE_PATH: =!
)

for /f "tokens=2 delims=:," %%a in ('type config\windows_paths.json ^| findstr "saved_folder"') do (
    set SAVED_PATH=%%a
    set SAVED_PATH=!SAVED_PATH:"=!
    set SAVED_PATH=!SAVED_PATH: =!
)

for /f "tokens=2 delims=:," %%a in ('type config\windows_paths.json ^| findstr "error_folder"') do (
    set ERROR_PATH=%%a
    set ERROR_PATH=!ERROR_PATH:"=!
    set ERROR_PATH=!ERROR_PATH: =!
)

REM Create local directories if they don't exist
if not exist "!SOURCE_PATH!" mkdir "!SOURCE_PATH!"
if not exist "!SAVED_PATH!" mkdir "!SAVED_PATH!"
if not exist "!ERROR_PATH!" mkdir "!ERROR_PATH!"

REM Create Docker data directories
if not exist "data\chroma_db" mkdir "data\chroma_db"
if not exist "logs" mkdir "logs"

echo   Created: !SOURCE_PATH!
echo   Created: !SAVED_PATH!
echo   Created: !ERROR_PATH!

echo [3/5] Generating environment configuration...

REM Set default model vendor (can be overridden by command line argument)
set MODEL_VENDOR=openai
if not "%1"=="" set MODEL_VENDOR=%1

REM Generate .env file using Python script
python scripts\generate_env.py --environment development --platform windows --model-vendor %MODEL_VENDOR%
if errorlevel 1 (
    echo ERROR: Failed to generate environment configuration
    pause
    exit /b 1
)

echo [4/5] Copying environment file...

REM Copy generated file to .env for docker-compose
if exist ".env.generated" (
    copy ".env.generated" ".env" >nul
    echo   Environment file ready: .env
) else (
    echo ERROR: Failed to generate .env file
    pause
    exit /b 1
)

echo [5/5] Starting Docker containers...

REM Build and start the containers
echo   Building Docker image...
docker-compose build

if errorlevel 1 (
    echo ERROR: Docker build failed
    pause
    exit /b 1
)

echo   Starting containers...
docker-compose up -d

if errorlevel 1 (
    echo ERROR: Failed to start containers
    pause
    exit /b 1
)

echo.
echo ============================================
echo   Deployment Successful!
echo ============================================
echo.
echo   Source folder:  !SOURCE_PATH!
echo   Saved folder:   !SAVED_PATH!
echo   Error folder:   !ERROR_PATH!
echo   Model vendor:   %MODEL_VENDOR%
echo.
echo   Container status:
docker-compose ps

echo.
echo   To monitor logs: docker-compose logs -f
echo   To stop:         docker-compose down
echo   To restart:      docker-compose restart
echo.
echo   Drop files into the source folder to start processing!

pause