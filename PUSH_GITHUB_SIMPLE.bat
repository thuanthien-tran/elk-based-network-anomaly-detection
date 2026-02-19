@echo off
REM Simple script to push to GitHub
REM Run this script to push your project to GitHub

echo.
echo ========================================
echo Pushing to GitHub
echo Repository: elk-based-network-anomaly-detection
echo ========================================
echo.

REM Add all files
git add .

REM Commit
git commit -m "Update ELKShield project: code, documentation, and evaluation"

REM Push
git push origin main

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [SUCCESS] Pushed to GitHub!
    echo.
    echo View your repository at:
    echo https://github.com/thuanthien-tran/elk-based-network-anomaly-detection
) else (
    echo.
    echo [ERROR] Push failed!
    echo.
    echo Please check:
    echo 1. GitHub authentication
    echo 2. Internet connection
    echo 3. Repository exists on GitHub
    echo.
    echo For detailed help, see: README_COMPLETE.md
)

echo.
pause
