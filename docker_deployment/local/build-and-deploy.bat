@echo off
REM Windows deployment script for local build and deployment
REM This script builds images locally using shared Dockerfile and deploys

setlocal EnableDelayedExpansion

echo ============================================
echo   Kiro Project - Local Build Deployment
echo   Platform: Windows
echo   Build: Local using shared Dockerfile
echo ============================================
echo.

REM Change to script directory for relative path resolution
cd /d "%~dp0"

echo [1/7] Checking prerequisites...

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

if not exist "..\shared\Dockerfile" (
    echo ERROR: ..\shared\Dockerfile not found
    exit /b 1
)

echo [2/7] Creating local directories...

REM Read paths from Windows configuration file using PowerShell (shared location)
for /f "delims=" %%i in ('powershell -Command "& {$json = Get-Content '..\shared\config\windows_paths.json' | ConvertFrom-Json; $json.source_folder}"') do set SOURCE_PATH=%%i
for /f "delims=" %%i in ('powershell -Command "& {$json = Get-Content '..\shared\config\windows_paths.json' | ConvertFrom-Json; $json.saved_folder}"') do set SAVED_PATH=%%i  
for /f "delims=" %%i in ('powershell -Command "& {$json = Get-Content '..\shared\config\windows_paths.json' | ConvertFrom-Json; $json.error_folder}"') do set ERROR_PATH=%%i

REM Create local directories if they don't exist
if not exist "%SOURCE_PATH%" mkdir "%SOURCE_PATH%"
if not exist "%SAVED_PATH%" mkdir "%SAVED_PATH%"
if not exist "%ERROR_PATH%" mkdir "%ERROR_PATH%"

REM Create Docker data directories (relative to local directory)
if not exist "..\data\chroma_db" mkdir "..\data\chroma_db"
if not exist "..\logs" mkdir "..\logs"

echo   Created: %SOURCE_PATH%
echo   Created: %SAVED_PATH%
echo   Created: %ERROR_PATH%

echo [3/7] Setting up temporary directory permissions...

REM Create temporary directory for document processing
set TEMP_DIR=C:\temp\file-processor-unstructured
if not exist "%TEMP_DIR%" mkdir "%TEMP_DIR%"

echo   Created: %TEMP_DIR%

echo [4/7] Generating environment configuration...

REM Set default model vendor (can be overridden by command line argument)
set MODEL_VENDOR=%1
if "%MODEL_VENDOR%"=="" set MODEL_VENDOR=google

echo   Model vendor: %MODEL_VENDOR%
echo   Build mode: Local (using shared Dockerfile)

REM Generate .env file using shared Python script
cd "..\shared\scripts"
uv run python generate_env.py --environment development --platform windows --model-vendor %MODEL_VENDOR%

if errorlevel 1 (
    echo ERROR: Failed to generate environment configuration
    exit /b 1
)

REM Return to local directory
cd "%~dp0"

echo [5/7] Copying environment file...

REM Copy generated file to .env for docker-compose
if exist "..\.env.generated" (
    copy "..\.env.generated" ".env" >nul
    echo   Environment file ready: .env
) else (
    echo ERROR: Failed to generate .env file
    exit /b 1
)

echo [6/7] Building Docker image locally...

REM Create Docker network if it doesn't exist
docker network create mcp-network >nul 2>&1

REM Build the image using shared Dockerfile
echo   Building image using shared Dockerfile...
docker-compose build --no-cache

if errorlevel 1 (
    echo ERROR: Docker build failed
    echo Check the shared Dockerfile and project dependencies
    exit /b 1
)

echo [7/7] Starting containers...

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
echo   Local Build Deployment Successful!
echo ============================================
echo.
echo   Build mode:     Local using shared Dockerfile
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
echo   To rebuild:      docker-compose build --no-cache ^&^& docker-compose up -d
echo.
echo   Drop files into the source folder to start processing!
echo.

pause