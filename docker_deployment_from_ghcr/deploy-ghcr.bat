@echo off
REM Windows deployment script for Kiro Project GHCR Docker deployment
REM This script deploys pre-built Docker images from GitHub Container Registry

setlocal enabledelayedexpansion

echo ============================================
echo   Kiro Project - GHCR Docker Deployment
echo   Platform: Windows
echo   Source: GitHub Container Registry
echo ============================================
echo.

REM Change to script directory for relative path resolution
cd /d "%~dp0"

echo [1/6] Checking prerequisites...

REM Check if Docker is available
docker --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker is not installed or not running
    echo Please install Docker Desktop and ensure it's running
    exit /b 1
)

REM Check if docker-compose is available
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: docker-compose is not installed or not in PATH
    echo Please install docker-compose and try again
    exit /b 1
)

REM Check if required files exist
if not exist "config\windows_paths.json" (
    echo ERROR: config\windows_paths.json not found
    echo Please ensure the configuration file exists
    exit /b 1
)

REM Set default values (can be overridden by command line arguments)
set IMAGE_TAG=%1
if "%IMAGE_TAG%"=="" set IMAGE_TAG=latest

set MODEL_VENDOR=%2
if "%MODEL_VENDOR%"=="" set MODEL_VENDOR=google

set GHCR_REPO=%3
if "%GHCR_REPO%"=="" set GHCR_REPO=ghcr.io/rwuniard/rag-file-processor

echo   Docker image: %GHCR_REPO%:%IMAGE_TAG%
echo   Model vendor: %MODEL_VENDOR%
echo.

echo [2/6] Creating local directories...

REM Read paths from Windows configuration file using PowerShell
for /f "tokens=2 delims=:" %%i in ('powershell -Command "& {$json = Get-Content 'config\windows_paths.json' | ConvertFrom-Json; $json.source_folder}"') do set SOURCE_PATH=%%i
for /f "tokens=2 delims=:" %%i in ('powershell -Command "& {$json = Get-Content 'config\windows_paths.json' | ConvertFrom-Json; $json.saved_folder}"') do set SAVED_PATH=%%i  
for /f "tokens=2 delims=:" %%i in ('powershell -Command "& {$json = Get-Content 'config\windows_paths.json' | ConvertFrom-Json; $json.error_folder}"') do set ERROR_PATH=%%i

REM Clean up the paths (remove extra characters)
set SOURCE_PATH=%SOURCE_PATH: =%
set SAVED_PATH=%SAVED_PATH: =%
set ERROR_PATH=%ERROR_PATH: =%

REM Create local directories if they don't exist
if not exist "%SOURCE_PATH%" mkdir "%SOURCE_PATH%"
if not exist "%SAVED_PATH%" mkdir "%SAVED_PATH%"
if not exist "%ERROR_PATH%" mkdir "%ERROR_PATH%"

REM Create Docker data directories
if not exist "data\chroma_db" mkdir "data\chroma_db"
if not exist "logs" mkdir "logs"

echo   Created: %SOURCE_PATH%
echo   Created: %SAVED_PATH%
echo   Created: %ERROR_PATH%

echo [3/6] Setting up temporary directory permissions...

REM Create temporary directory for document processing
set TEMP_DIR=C:\temp\file-processor-unstructured
if not exist "%TEMP_DIR%" mkdir "%TEMP_DIR%"

echo   Created: %TEMP_DIR%

echo [4/6] Pulling Docker image from GHCR...

REM Pull the latest image from GHCR
echo   Pulling %GHCR_REPO%:%IMAGE_TAG%...
docker pull "%GHCR_REPO%:%IMAGE_TAG%"

if errorlevel 1 (
    echo ERROR: Failed to pull Docker image from GHCR
    echo Please ensure:
    echo   1. The image exists in the registry
    echo   2. You have access to the repository
    echo   3. You are logged in to GHCR (docker login ghcr.io)
    exit /b 1
)

echo [5/6] Generating environment configuration...

REM Check if .env.local exists for API keys
if not exist "..\..\env.local" (
    echo WARNING: .env.local not found in project root
    echo Please create .env.local with your API keys:
    echo   OPENAI_API_KEY=your_openai_key_here
    echo   GOOGLE_API_KEY=your_google_key_here
    echo.
)

REM Generate environment variables for docker-compose
echo # Generated environment file for GHCR deployment > .env
echo # Generated on: %date% %time% >> .env
echo. >> .env
echo # Docker image configuration >> .env
echo DOCKER_IMAGE=%GHCR_REPO%:%IMAGE_TAG% >> .env
echo. >> .env
echo # Local folder mappings >> .env
echo SOURCE_FOLDER=%SOURCE_PATH% >> .env
echo SAVED_FOLDER=%SAVED_PATH% >> .env
echo ERROR_FOLDER=%ERROR_PATH% >> .env
echo. >> .env
echo # Document processing configuration >> .env
echo ENABLE_DOCUMENT_PROCESSING=true >> .env
echo DOCUMENT_PROCESSOR_TYPE=rag_store >> .env
echo MODEL_VENDOR=%MODEL_VENDOR% >> .env
echo. >> .env
echo # ChromaDB configuration >> .env
echo CHROMA_CLIENT_MODE=embedded >> .env
echo CHROMA_DB_PATH=./data/chroma_db >> .env
echo CHROMA_COLLECTION_NAME=rag-kb >> .env
echo. >> .env
echo # File monitoring configuration (Docker-optimized) >> .env
echo FILE_MONITORING_MODE=auto >> .env
echo POLLING_INTERVAL=2.0 >> .env
echo DOCKER_VOLUME_MODE=true >> .env
echo. >> .env
echo # Logging configuration >> .env
echo LOG_LEVEL=INFO >> .env

REM Append API keys from .env.local if it exists
if exist "..\..\env.local" (
    echo   Loading API keys from .env.local...
    for /f "tokens=1,2 delims==" %%a in ('type "..\..\env.local"') do (
        if "%%a"=="OPENAI_API_KEY" echo OPENAI_API_KEY=%%b >> .env
        if "%%a"=="GOOGLE_API_KEY" echo GOOGLE_API_KEY=%%b >> .env
    )
)

echo   Environment file ready: .env

echo [6/6] Starting Docker containers...

REM Start the containers using the pulled image
echo   Starting containers...
docker-compose up -d

if errorlevel 1 (
    echo ERROR: Failed to start containers
    exit /b 1
)

REM Wait a moment for containers to initialize
timeout /t 5 /nobreak >nul

echo.
echo ============================================
echo   GHCR Deployment Successful!
echo ============================================
echo.
echo   Docker image:   %GHCR_REPO%:%IMAGE_TAG%
echo   Source folder:  %SOURCE_PATH%
echo   Saved folder:   %SAVED_PATH%
echo   Error folder:   %ERROR_PATH%
echo   Temp directory: %TEMP_DIR%
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
echo.

REM Display current image info
echo   Current image info:
docker images "%GHCR_REPO%" --format "table {{.Repository}}\t{{.Tag}}\t{{.CreatedAt}}\t{{.Size}}"
echo.

pause