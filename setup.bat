@echo off
REM Setup script for ELKShield project
REM Creates necessary directories and checks dependencies

echo ========================================
echo ELKShield Project Setup
echo ========================================
echo.

REM Create directories
echo Creating directories...
if not exist "data\raw" mkdir "data\raw"
if not exist "data\processed" mkdir "data\processed"
if not exist "ml_models" mkdir "ml_models"
if not exist "reports" mkdir "reports"
echo [OK] Directories created
echo.

REM Check Python
echo Checking Python...
python --version
if errorlevel 1 (
    echo [ERROR] Python not found!
    pause
    exit /b 1
)
echo [OK] Python found
echo.

REM Check Docker
echo Checking Docker...
docker --version
if errorlevel 1 (
    echo [WARNING] Docker not found. You need Docker to run ELK Stack.
    echo Install Docker Desktop from: https://www.docker.com/products/docker-desktop
) else (
    echo [OK] Docker found
)
echo.

REM Install Python dependencies
echo Installing Python dependencies...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)
echo [OK] Dependencies installed
echo.

echo ========================================
echo Setup completed!
echo ========================================
echo.
echo Next steps:
echo 1. Start ELK Stack: cd docker ^&^& docker-compose up -d
echo 2. Read: HUONG_DAN_CHAY_DU_AN.md
echo.
REM Khi chay tu DEMO.bat hoac RUN_BY_GUI=1 thi khong pause
if not defined RUN_BY_GUI pause
