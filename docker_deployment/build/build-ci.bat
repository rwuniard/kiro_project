@echo off
REM CI build script for Kiro Project (Windows)
REM Builds Docker image for CI/production and pushes to registry as 'rag-file-processor'

setlocal EnableDelayedExpansion

echo ============================================
echo   Kiro Project - CI Build
echo   Building and pushing: rag-file-processor
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
set REPO_NAME=kiro_project

REM Auto-determine version from pyproject.toml + git metadata
for /f "tokens=3 delims= =" %%i in ('findstr "^version = " "pyproject.toml"') do set BASE_VERSION=%%i
set BASE_VERSION=%BASE_VERSION:"=%
for /f %%i in ('git rev-parse --short HEAD 2^>nul') do set GIT_SHA=%%i
if "%GIT_SHA%"=="" set GIT_SHA=unknown
set TAG=rag-file-processor-%BASE_VERSION%-%GIT_SHA%
set FULL_IMAGE_NAME=%REGISTRY%/%REPO_NAME%:%TAG%

echo   Registry: %REGISTRY%
echo   Repository: %REPO_NAME%
echo   Base version: %BASE_VERSION% (from pyproject.toml)
echo   Git SHA: %GIT_SHA%
echo   Tag: %TAG%
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

REM Also tag with convenience tags
docker tag "%FULL_IMAGE_NAME%" "%REPO_NAME%:%TAG%"
docker tag "%FULL_IMAGE_NAME%" "%REPO_NAME%:rag-file-processor-latest"
docker tag "%FULL_IMAGE_NAME%" "%REGISTRY%/%REPO_NAME%:rag-file-processor-latest"

echo   Tagged as: %REPO_NAME%:%TAG%
echo   Tagged as: %REPO_NAME%:rag-file-processor-latest
echo   Tagged as: %REGISTRY%/%REPO_NAME%:rag-file-processor-latest
echo   Tagged as: %FULL_IMAGE_NAME%

echo [4/4] Pushing to registry...

REM Push to registry
echo   Pushing to %REGISTRY%...
docker push "%FULL_IMAGE_NAME%"
docker push "%REGISTRY%/%REPO_NAME%:rag-file-processor-latest"

if errorlevel 1 (
    echo ERROR: Failed to push image to registry
    echo Make sure you are logged in to the registry:
    echo %REGISTRY% | findstr "ghcr.io" >nul
    if not errorlevel 1 (
        echo   docker login ghcr.io
    ) else (
        echo   docker login %REGISTRY%
    )
    exit /b 1
)

echo.
echo ============================================
echo   CI Build Successful!
echo ============================================
echo.
echo   Built image: %FULL_IMAGE_NAME%
echo   Also tagged: %REGISTRY%/%REPO_NAME%:rag-file-processor-latest
echo   Local tag:   %REPO_NAME%:%TAG%
echo   Base version: %BASE_VERSION% (from pyproject.toml)
echo   Git commit:   %GIT_SHA%
echo.
echo   Image is ready for deployment using:
echo   ..\deploy\deploy.bat %FULL_IMAGE_NAME% [env-file]
echo   or
echo   ..\deploy\deploy.bat %REGISTRY%/%REPO_NAME%:rag-file-processor-latest [env-file]
echo.
echo   To view image: docker images %REPO_NAME%
echo.

pause