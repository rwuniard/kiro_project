@echo off
REM ChromaDB Server Management Script - Windows Version

setlocal enabledelayedexpansion

REM Get project root directory (parent of setup_chromadb)
set SETUP_DIR=%~dp0
for %%i in ("%SETUP_DIR%\..") do set PROJECT_ROOT=%%~fi
cd /d "%PROJECT_ROOT%"

if "%1"=="" goto :no_command
if "%1"=="start" goto :start_server
if "%1"=="stop" goto :stop_server
if "%1"=="restart" goto :restart_server
if "%1"=="status" goto :show_status
if "%1"=="logs" goto :show_logs
if "%1"=="health" goto :check_health
if "%1"=="clean" goto :clean_data
if "%1"=="help" goto :show_help
if "%1"=="--help" goto :show_help
if "%1"=="-h" goto :show_help
goto :unknown_command

:show_help
echo ChromaDB Server Management
echo.
echo Usage: %0 [COMMAND]
echo.
echo Commands:
echo   start     Start ChromaDB server
echo   stop      Stop ChromaDB server
echo   restart   Restart ChromaDB server
echo   status    Show server status
echo   logs      Show server logs
echo   health    Check server health
echo   clean     Stop server and remove data (DANGEROUS)
echo.
goto :eof

:start_server
echo 🚀 Starting ChromaDB server...

REM Create network if it doesn't exist
docker network ls | findstr "mcp-network" >nul
if errorlevel 1 (
    echo 🔧 Creating mcp-network...
    docker network create mcp-network
    if errorlevel 1 (
        echo ❌ Failed to create network
        exit /b 1
    )
    echo ✅ Network created
) else (
    echo ✅ Network mcp-network already exists
)

REM Create data directory
if not exist "data\chroma_data" mkdir "data\chroma_data"

REM Start ChromaDB with docker compose
docker compose -f "%SETUP_DIR%docker-compose.yml" up -d chromadb
if errorlevel 1 (
    echo ❌ Failed to start ChromaDB server
    exit /b 1
)

echo ✅ ChromaDB server started on http://localhost:8000
echo 🌐 Container name: chromadb (accessible from mcp-network)
echo 💡 Run '%0 health' to check server status
goto :eof

:stop_server
echo 🛑 Stopping ChromaDB server...
docker compose -f "%SETUP_DIR%docker-compose.yml" down
if errorlevel 1 (
    echo ❌ Failed to stop ChromaDB server
    exit /b 1
)
echo ✅ ChromaDB server stopped
goto :eof

:restart_server
echo 🔄 Restarting ChromaDB server...
call :stop_server
timeout /t 2 /nobreak >nul
call :start_server
goto :eof

:show_status
echo 📊 ChromaDB server status:
docker compose -f "%SETUP_DIR%docker-compose.yml" ps chromadb
goto :eof

:show_logs
echo 📋 ChromaDB server logs:
docker compose -f "%SETUP_DIR%docker-compose.yml" logs -f chromadb
goto :eof

:check_health
echo 🏥 Checking ChromaDB server health...

REM Check if curl is available, use PowerShell as fallback
curl --version >nul 2>&1
if errorlevel 1 (
    REM Use PowerShell for HTTP request
    powershell -Command "try { $response = Invoke-WebRequest -Uri 'http://localhost:8000/api/v2/heartbeat' -TimeoutSec 5; exit 0 } catch { exit 1 }" >nul 2>&1
) else (
    REM Use curl
    curl -f http://localhost:8000/api/v2/heartbeat >nul 2>&1
)

if errorlevel 1 (
    echo ❌ ChromaDB server is not healthy
    echo 💡 Run '%0 logs' to check for errors
    exit /b 1
) else (
    echo ✅ ChromaDB server is healthy
    echo 🌐 Server URL: http://localhost:8000
    echo 📊 Admin UI: http://localhost:8000 (if available)
    
    REM Try to get version info using PowerShell
    echo 📦 Server info:
    powershell -Command "try { $response = Invoke-WebRequest -Uri 'http://localhost:8000/api/v2/version' -TimeoutSec 5; $response.Content | ConvertFrom-Json | ConvertTo-Json } catch { Write-Host 'Version info not available' }" 2>nul
)
goto :eof

:clean_data
echo ⚠️  WARNING: This will delete all ChromaDB data!
set /p confirm=Are you sure? Type 'yes' to confirm: 
if "%confirm%"=="yes" (
    echo 🧹 Cleaning ChromaDB data...
    call :stop_server
    if exist "data\chroma_data" (
        rmdir /s /q "data\chroma_data" >nul 2>&1
        mkdir "data\chroma_data"
    )
    echo ✅ ChromaDB data cleaned
    echo 💡 Run '%0 start' to start fresh server
) else (
    echo ❌ Clean operation cancelled
)
goto :eof

:no_command
echo ❌ No command provided
echo.
goto :show_help

:unknown_command
echo ❌ Unknown command: %1
echo.
goto :show_help