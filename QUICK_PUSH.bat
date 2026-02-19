@echo off
REM Quick push script for GitHub
REM Repository: https://github.com/thuanthien-tran/elk-based-network-anomaly-detection

echo ========================================
echo Quick Push to GitHub
echo ========================================
echo.

REM Check git
git --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Git not found!
    pause
    exit /b 1
)

REM Check if remote exists
git remote get-url origin >nul 2>&1
if errorlevel 1 (
    echo [INFO] Adding remote repository...
    git remote add origin https://github.com/thuanthien-tran/elk-based-network-anomaly-detection.git
)

REM Add all files
echo Adding files...
git add .

REM Commit
echo Committing...
git commit -m "Update ELKShield project: code, documentation, and evaluation reports"

REM Push
echo Pushing to GitHub...
git push -u origin main
if errorlevel 1 (
    echo.
    echo [ERROR] Push failed!
    echo.
    echo Please check:
    echo 1. GitHub authentication (use Personal Access Token)
    echo 2. Repository exists: https://github.com/thuanthien-tran/elk-based-network-anomaly-detection
    echo.
    echo See: HUONG_DAN_PUSH_GITHUB.md for detailed instructions
    pause
    exit /b 1
)

echo.
echo [SUCCESS] Pushed to GitHub!
echo Repository: https://github.com/thuanthien-tran/elk-based-network-anomaly-detection
echo.
pause
