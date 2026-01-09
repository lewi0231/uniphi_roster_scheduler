@echo off
REM Quick start script for Windows
echo Starting Roster Scheduler with Docker Compose...
echo.

REM Check if Docker is installed
docker --version >nul 2>&1
if errorlevel 1 (
    echo Docker is not installed. Please install Docker Desktop:
    echo https://www.docker.com/products/docker-desktop/
    pause
    exit /b 1
)

REM Build and start containers
echo Building and starting containers...
docker-compose up --build

pause
