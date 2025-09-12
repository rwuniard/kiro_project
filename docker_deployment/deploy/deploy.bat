@echo off
REM Working deployment script - based on deploy_simple.bat but reads paths from .env
setlocal

echo ============================================
echo   Kiro Project - Universal Deployment
echo ============================================
echo.

REM Check command line arguments
if "%2"=="" (
    echo Usage: %0 ^<image-name^> ^<env-file-path^>
    exit /b 1
)

set IMAGE_NAME=%1
set ENV_FILE=%2

echo   Image: %IMAGE_NAME%
echo   Environment file: %ENV_FILE%
echo.

echo [1/3] Checking prerequisites...

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

echo [2/3] Setting up deployment environment...

REM Create a deployment env file by copying the source env file
copy "%ENV_FILE%" .env.deploy >nul

REM Extract folder paths using simple method
REM Default values first
set SOURCE_FOLDER=C:\tmp\rag_store\source
set SAVED_FOLDER=C:\tmp\rag_store\saved
set ERROR_FOLDER=C:\tmp\rag_store\error

REM Try to read from .env file (simple approach)
for /f "usebackq tokens=1,2 delims==" %%i in ("%ENV_FILE%") do (
    if "%%i"=="SOURCE_FOLDER" set "SOURCE_FOLDER=%%j"
    if "%%i"=="SAVED_FOLDER" set "SAVED_FOLDER=%%j"
    if "%%i"=="ERROR_FOLDER" set "ERROR_FOLDER=%%j"
)

REM Remove quotes
set SOURCE_FOLDER=%SOURCE_FOLDER:"=%
set SAVED_FOLDER=%SAVED_FOLDER:"=%
set ERROR_FOLDER=%ERROR_FOLDER:"=%

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

REM Create local directories if they don't exist
if not exist "%SOURCE_FOLDER%" mkdir "%SOURCE_FOLDER%"
if not exist "%SAVED_FOLDER%" mkdir "%SAVED_FOLDER%"
if not exist "%ERROR_FOLDER%" mkdir "%ERROR_FOLDER%"

REM Create Docker data directories (relative to deploy directory)
if not exist "..\data\chroma_db" mkdir "..\data\chroma_db"
if not exist "..\logs" mkdir "..\logs"

REM Create temporary directory for document processing
if not exist "C:\temp\file-processor-unstructured" mkdir "C:\temp\file-processor-unstructured"

echo   Created directories successfully
echo   Source folder: %SOURCE_FOLDER%
echo   Saved folder: %SAVED_FOLDER%
echo   Error folder: %ERROR_FOLDER%

echo [3/3] Starting deployment...

REM Create Docker network if it doesn't exist
docker network create mcp-network >nul 2>&1

REM Pull the image
echo   Pulling image: %IMAGE_NAME%
docker pull "%IMAGE_NAME%"

if errorlevel 1 (
    echo ERROR: Failed to pull image '%IMAGE_NAME%'
    echo Make sure the image exists and you have access to it
    exit /b 1
)

REM Use the deployment env file
echo   Starting containers...
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
echo   Container status:
docker-compose --env-file .env.deploy ps

echo.
echo   To monitor logs: docker-compose --env-file .env.deploy logs -f
echo   To stop:         docker-compose --env-file .env.deploy down
echo   Drop files into %SOURCE_FOLDER% to start processing!

REM Clean up temporary deployment env file
del .env.deploy >nul 2>&1

pause
