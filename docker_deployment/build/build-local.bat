@echo off
REM Local build script for Kiro Project (Windows)
REM Builds Docker image locally and pushes to registry as 'local-rag-file-processor'

setlocal EnableDelayedExpansion

echo ============================================
echo   Kiro Project - Local Build
echo   Building and pushing: local-rag-file-processor
echo ============================================
echo.

REM Change to script directory for relative path resolution
cd /d "%~dp0"

REM Navigate to project root (two levels up from build directory)
cd ..\..

echo [1/4] Checking prerequisites...

REM Check if Docker is available
docker --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker is not installed or not running
    echo Please install Docker Desktop and ensure it's running
    exit /b 1
)

REM Check if Dockerfile exists
if not exist "docker_deployment\shared\Dockerfile" (
    echo ERROR: docker_deployment\shared\Dockerfile not found
    exit /b 1
)

echo [2/4] Building Docker image...

REM Set default registry and image name
set REGISTRY=%1
if "%REGISTRY%"=="" set REGISTRY=ghcr.io/rwuniard
set IMAGE_NAME=local-rag-file-processor
set FULL_IMAGE_NAME=%REGISTRY%/%IMAGE_NAME%:latest

echo   Registry: %REGISTRY%
echo   Image name: %IMAGE_NAME%
echo   Full image: %FULL_IMAGE_NAME%

REM Build the image
echo   Building image...
docker build -f docker_deployment\shared\Dockerfile -t "%FULL_IMAGE_NAME%" .

if errorlevel 1 (
    echo ERROR: Docker build failed
    echo Check the Dockerfile and project dependencies
    exit /b 1
)

echo [3/4] Tagging image...

REM Also tag with local name for convenience
docker tag "%FULL_IMAGE_NAME%" "%IMAGE_NAME%:latest"

echo   Tagged as: %IMAGE_NAME%:latest
echo   Tagged as: %FULL_IMAGE_NAME%

echo [4/4] Pushing to registry...

REM Push to registry
echo   Pushing to %REGISTRY%...
docker push "%FULL_IMAGE_NAME%"

if errorlevel 1 (
    echo ERROR: Failed to push image to registry
    echo Make sure you are logged in to the registry:
    echo   docker login %REGISTRY%
    exit /b 1
)

echo.
echo ============================================
echo   Local Build Successful!
echo ============================================
echo.
echo   Built image: %FULL_IMAGE_NAME%
echo   Local tag:   %IMAGE_NAME%:latest
echo.
echo   Image is ready for deployment using:
echo   ..\deploy\deploy.bat %FULL_IMAGE_NAME% [env-file]
echo   or
echo   ..\deploy\deploy.bat %IMAGE_NAME%:latest [env-file]
echo.
echo   To view image: docker images %IMAGE_NAME%
echo.

pause