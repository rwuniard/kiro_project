@echo off
REM Windows deployment script for CI deployment using pre-built GHCR images
REM This script pulls pre-built images from GitHub Container Registry and deploys locally

setlocal EnableDelayedExpansion

echo ============================================
echo   Kiro Project - CI Deployment (GHCR Pull)
echo   Platform: Windows
echo   Image: ghcr.io/rwuniard/rag-file-processor:latest
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

REM Check if uv is available for environment generation
uv --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: uv is not installed or not in PATH
    echo Please install uv and try again
    exit /b 1
)

REM Check if required shared files exist
if not exist "..\shared\scripts\generate_env.py" (
    echo ERROR: ..\shared\scripts\generate_env.py not found
    exit /b 1
)

if not exist "..\shared\config\windows_paths.json" (
    echo ERROR: ..\shared\config\windows_paths.json not found
    exit /b 1
)

if not exist "..\shared\.env.template" (
    echo ERROR: ..\shared\.env.template not found
    exit /b 1
)

echo [2/6] Creating local directories...

REM Read paths from Windows configuration file using PowerShell (shared location)
for /f "delims=" %%i in ('powershell -Command "& {$json = Get-Content '..\shared\config\windows_paths.json' | ConvertFrom-Json; $json.source_folder}"') do set SOURCE_PATH=%%i
for /f "delims=" %%i in ('powershell -Command "& {$json = Get-Content '..\shared\config\windows_paths.json' | ConvertFrom-Json; $json.saved_folder}"') do set SAVED_PATH=%%i  
for /f "delims=" %%i in ('powershell -Command "& {$json = Get-Content '..\shared\config\windows_paths.json' | ConvertFrom-Json; $json.error_folder}"') do set ERROR_PATH=%%i

REM Create local directories if they don't exist
if not exist "%SOURCE_PATH%" mkdir "%SOURCE_PATH%"
if not exist "%SAVED_PATH%" mkdir "%SAVED_PATH%"
if not exist "%ERROR_PATH%" mkdir "%ERROR_PATH%"

REM Create Docker data directories (relative to CI directory)
if not exist "..\data\chroma_db" mkdir "..\data\chroma_db"
if not exist "..\logs" mkdir "..\logs"

echo   Created: %SOURCE_PATH%
echo   Created: %SAVED_PATH%
echo   Created: %ERROR_PATH%

echo [3/6] Setting up temporary directory permissions...

REM Create temporary directory for document processing
set TEMP_DIR=C:\temp\file-processor-unstructured
if not exist "%TEMP_DIR%" mkdir "%TEMP_DIR%"

echo   Created: %TEMP_DIR%

echo [4/6] Generating environment configuration...

REM Set default values (can be overridden by command line arguments)
set IMAGE_TAG=%1
if "%IMAGE_TAG%"=="" set IMAGE_TAG=latest

set MODEL_VENDOR=%2
if "%MODEL_VENDOR%"=="" set MODEL_VENDOR=google

set GHCR_REPO=%3
if "%GHCR_REPO%"=="" set GHCR_REPO=ghcr.io/rwuniard/rag-file-processor

echo   Docker image: %GHCR_REPO%:%IMAGE_TAG%
echo   Model vendor: %MODEL_VENDOR%

REM Generate .env file using shared Python script
cd "..\shared\scripts"
uv run python generate_env.py --environment production --platform windows --model-vendor %MODEL_VENDOR%

if errorlevel 1 (
    echo ERROR: Failed to generate environment configuration
    exit /b 1
)

REM Return to CI directory
cd "%~dp0"

echo [5/6] Copying environment file and adding Docker image config...

REM Copy generated file to .env for docker-compose
if exist "..\.env.generated" (
    REM Copy .env but exclude folder paths (they're hardcoded in docker-compose.yml)
    findstr /v "^SOURCE_FOLDER= ^SAVED_FOLDER= ^ERROR_FOLDER=" "..\.env.generated" > ".env"
    
    REM Add host paths from Windows configuration for volume mounting
    for /f "delims=" %%i in ('powershell -Command "& {$json = Get-Content '..\\shared\\config\\windows_paths.json' | ConvertFrom-Json; $json.source_folder}"') do set SOURCE_PATH=%%i
    for /f "delims=" %%i in ('powershell -Command "& {$json = Get-Content '..\\shared\\config\\windows_paths.json' | ConvertFrom-Json; $json.saved_folder}"') do set SAVED_PATH=%%i  
    for /f "delims=" %%i in ('powershell -Command "& {$json = Get-Content '..\\shared\\config\\windows_paths.json' | ConvertFrom-Json; $json.error_folder}"') do set ERROR_PATH=%%i
    
    REM Add host paths for docker-compose volume mounting
    echo. >> .env
    echo # Host folder paths for volume mounting (not used by application) >> .env
    echo SOURCE_FOLDER=%SOURCE_PATH% >> .env
    echo SAVED_FOLDER=%SAVED_PATH% >> .env
    echo ERROR_FOLDER=%ERROR_PATH% >> .env
    
    REM Add Docker image configuration for CI deployment
    echo. >> .env
    echo # Docker image configuration for CI deployment >> .env
    echo DOCKER_IMAGE=%GHCR_REPO%:%IMAGE_TAG% >> .env
    
    echo   Environment file ready: .env
) else (
    echo ERROR: Failed to generate .env file
    exit /b 1
)

echo [6/6] Pulling image and starting containers...

REM Create Docker network if it doesn't exist
docker network create mcp-network >nul 2>&1

REM Pull the latest image from GHCR
echo   Pulling image from GHCR...
docker pull "%GHCR_REPO%:%IMAGE_TAG%"

if errorlevel 1 (
    echo ERROR: Failed to pull image from GHCR
    echo Make sure you have access to the repository and are logged in:
    echo   docker login ghcr.io
    exit /b 1
)

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
echo   CI Deployment Successful!
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
echo   To update:       docker-compose pull ^&^& docker-compose up -d
echo.
echo   Drop files into the source folder to start processing!
echo.

REM Display current image info
echo   Current image info:
docker images "%GHCR_REPO%" --format "table {{.Repository}}\t{{.Tag}}\t{{.CreatedAt}}\t{{.Size}}"
echo.

pause