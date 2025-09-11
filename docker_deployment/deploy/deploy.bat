@echo off
REM Universal deployment script for Kiro Project (Windows)
REM Deploys any Docker image with user-provided environment configuration
REM No Python/uv dependencies - only Docker required

setlocal EnableDelayedExpansion

echo ============================================
echo   Kiro Project - Universal Deployment
echo ============================================
echo.

REM Change to script directory for relative path resolution
cd /d "%~dp0"

REM Check command line arguments
if "%2"=="" (
    echo Usage: %0 ^<image-name^> ^<env-file-path^>
    echo.
    echo Examples:
    echo   %0 local-rag-file-processor:latest .env.development
    echo   %0 rag-file-processor:latest .env.production
    echo   %0 ghcr.io/rwuniard/rag-file-processor:v1.0.0 .env.custom
    echo.
    exit /b 1
)

set IMAGE_NAME=%1
set ENV_FILE=%2

echo   Image: %IMAGE_NAME%
echo   Environment file: %ENV_FILE%
echo.

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

REM Check if environment file exists
if not exist "%ENV_FILE%" (
    echo ERROR: Environment file '%ENV_FILE%' not found
    echo Please provide a valid .env file path
    exit /b 1
)

echo [2/6] Loading environment configuration...

REM Create a temporary .env file for docker-compose
copy "%ENV_FILE%" .env.deploy >nul

REM Read folder paths from environment file or use defaults
set SOURCE_FOLDER=
set SAVED_FOLDER=
set ERROR_FOLDER=

REM Extract folder paths from env file (using findstr and for loop)
for /f "tokens=2 delims==" %%i in ('findstr "^SOURCE_FOLDER=" "%ENV_FILE%" 2^>nul') do set SOURCE_FOLDER=%%i
for /f "tokens=2 delims==" %%i in ('findstr "^SAVED_FOLDER=" "%ENV_FILE%" 2^>nul') do set SAVED_FOLDER=%%i
for /f "tokens=2 delims==" %%i in ('findstr "^ERROR_FOLDER=" "%ENV_FILE%" 2^>nul') do set ERROR_FOLDER=%%i

REM Remove quotes if present
set SOURCE_FOLDER=%SOURCE_FOLDER:"=%
set SAVED_FOLDER=%SAVED_FOLDER:"=%
set ERROR_FOLDER=%ERROR_FOLDER:"=%

REM If not found in env file, try to get from config files
if "%SOURCE_FOLDER%"=="" (
    if exist "..\config\windows_paths.json" (
        echo   Using default paths from config file...
        for /f "delims=" %%i in ('powershell -Command "& {$json = Get-Content '..\\config\\windows_paths.json' | ConvertFrom-Json; $json.source_folder}"') do set SOURCE_FOLDER=%%i
        for /f "delims=" %%i in ('powershell -Command "& {$json = Get-Content '..\\config\\windows_paths.json' | ConvertFrom-Json; $json.saved_folder}"') do set SAVED_FOLDER=%%i
        for /f "delims=" %%i in ('powershell -Command "& {$json = Get-Content '..\\config\\windows_paths.json' | ConvertFrom-Json; $json.error_folder}"') do set ERROR_FOLDER=%%i
    )
)

REM Use fallback defaults if still empty
if "%SOURCE_FOLDER%"=="" set SOURCE_FOLDER=C:\temp\rag_store\source
if "%SAVED_FOLDER%"=="" set SAVED_FOLDER=C:\temp\rag_store\saved
if "%ERROR_FOLDER%"=="" set ERROR_FOLDER=C:\temp\rag_store\error

echo   Source folder: %SOURCE_FOLDER%
echo   Saved folder: %SAVED_FOLDER%
echo   Error folder: %ERROR_FOLDER%

REM Add folder paths to deployment env file
echo. >> .env.deploy
echo # Host folder paths for volume mounting >> .env.deploy
echo SOURCE_FOLDER=%SOURCE_FOLDER% >> .env.deploy
echo SAVED_FOLDER=%SAVED_FOLDER% >> .env.deploy
echo ERROR_FOLDER=%ERROR_FOLDER% >> .env.deploy

REM Add Docker image configuration
echo. >> .env.deploy
echo # Docker image configuration >> .env.deploy
echo DOCKER_IMAGE=%IMAGE_NAME% >> .env.deploy

echo [3/6] Creating local directories...

REM Create local directories if they don't exist
if not exist "%SOURCE_FOLDER%" mkdir "%SOURCE_FOLDER%"
if not exist "%SAVED_FOLDER%" mkdir "%SAVED_FOLDER%"
if not exist "%ERROR_FOLDER%" mkdir "%ERROR_FOLDER%"

REM Create Docker data directories (relative to deploy directory)
if not exist "..\data\chroma_db" mkdir "..\data\chroma_db"
if not exist "..\logs" mkdir "..\logs"

echo   Created: %SOURCE_FOLDER%
echo   Created: %SAVED_FOLDER%
echo   Created: %ERROR_FOLDER%

echo [4/6] Setting up temporary directory permissions...

REM Create temporary directory for document processing
set TEMP_DIR=C:\temp\file-processor-unstructured
if not exist "%TEMP_DIR%" mkdir "%TEMP_DIR%"

echo   Created: %TEMP_DIR%

echo [5/6] Pulling Docker image...

REM Pull the image
echo   Pulling image: %IMAGE_NAME%
docker pull "%IMAGE_NAME%"

if errorlevel 1 (
    echo ERROR: Failed to pull image '%IMAGE_NAME%'
    echo Make sure the image exists and you have access to it
    exit /b 1
)

echo [6/6] Starting containers...

REM Create Docker network if it doesn't exist
docker network create mcp-network >nul 2>&1

REM Use the deployment env file
echo   Starting containers with image: %IMAGE_NAME%
docker-compose --env-file .env.deploy up -d

if errorlevel 1 (
    echo ERROR: Failed to start containers
    exit /b 1
)

REM Wait a moment for containers to initialize
timeout /t 5 /nobreak >nul

echo.
echo ============================================
echo   Deployment Successful!
echo ============================================
echo.
echo   Docker image:   %IMAGE_NAME%
echo   Environment:    %ENV_FILE%
echo   Source folder:  %SOURCE_FOLDER%
echo   Saved folder:   %SAVED_FOLDER%
echo   Error folder:   %ERROR_FOLDER%
echo   Temp directory: %TEMP_DIR%
echo.
echo   Container status:
docker-compose --env-file .env.deploy ps

echo.
echo   To monitor logs: docker-compose --env-file .env.deploy logs -f
echo   To stop:         docker-compose --env-file .env.deploy down
echo   To restart:      docker-compose --env-file .env.deploy restart
echo.
echo   Drop files into the source folder to start processing!
echo.

REM Clean up temporary deployment env file
del .env.deploy >nul 2>&1

pause