@echo off
REM Script to push ELKShield project to GitHub
REM Repository: https://github.com/thuanthien-tran/elk-based-network-anomaly-detection

echo ========================================
echo Pushing ELKShield Project to GitHub
echo ========================================
echo.

REM Check if git is installed
git --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Git is not installed!
    echo Please install Git from: https://git-scm.com/download/win
    pause
    exit /b 1
)

echo [OK] Git found
echo.

REM Check if already a git repository
if exist ".git" (
    echo [INFO] Git repository already initialized
) else (
    echo [INFO] Initializing git repository...
    git init
    if errorlevel 1 (
        echo [ERROR] Failed to initialize git repository
        pause
        exit /b 1
    )
    echo [OK] Git repository initialized
)

echo.

REM Check remote
echo Checking remote repository...
git remote -v | findstr "elk-based-network-anomaly-detection" >nul
if errorlevel 1 (
    echo [INFO] Adding remote repository...
    git remote add origin https://github.com/thuanthien-tran/elk-based-network-anomaly-detection.git
    if errorlevel 1 (
        echo [WARNING] Remote might already exist, trying to set URL...
        git remote set-url origin https://github.com/thuanthien-tran/elk-based-network-anomaly-detection.git
    )
    echo [OK] Remote repository added
) else (
    echo [OK] Remote repository already configured
)

echo.

REM Add all files
echo Adding files to git...
git add .
if errorlevel 1 (
    echo [ERROR] Failed to add files
    pause
    exit /b 1
)

REM Check if there are changes to commit
git diff --cached --quiet
if errorlevel 1 (
    echo [INFO] Files staged for commit
) else (
    echo [INFO] No changes to commit
    echo Checking if we need to push...
    git log origin/main..HEAD --oneline >nul 2>&1
    if errorlevel 1 (
        echo [INFO] Everything is up to date!
        pause
        exit /b 0
    )
)

echo.

REM Commit
echo Committing changes...
set /p commit_msg="Enter commit message (or press Enter for default): "
if "!commit_msg!"=="" set commit_msg=Update ELKShield project code and documentation

git commit -m "%commit_msg%"
if errorlevel 1 (
    echo [WARNING] Commit failed or no changes to commit
)

echo.

REM Push to GitHub
echo Pushing to GitHub...
echo [INFO] This may require GitHub credentials
echo.

REM Try main branch first
git branch --show-current | findstr "main" >nul
if errorlevel 1 (
    git branch --show-current | findstr "master" >nul
    if errorlevel 1 (
        echo [INFO] Current branch is not main/master, checking out main...
        git checkout -b main 2>nul
        if errorlevel 1 (
            git checkout main 2>nul
        )
    )
)

git push -u origin main
if errorlevel 1 (
    echo [WARNING] Push to main failed, trying master...
    git push -u origin master
    if errorlevel 1 (
        echo [ERROR] Failed to push to GitHub
        echo.
        echo Possible reasons:
        echo 1. Not authenticated with GitHub
        echo 2. Repository doesn't exist or you don't have access
        echo 3. Network issues
        echo.
        echo Solutions:
        echo 1. Setup GitHub authentication:
        echo    git config --global user.name "Your Name"
        echo    git config --global user.email "your.email@example.com"
        echo.
        echo 2. Use GitHub Desktop or GitHub CLI for easier authentication
        echo.
        pause
        exit /b 1
    )
)

echo.
echo ========================================
echo [SUCCESS] Project pushed to GitHub!
echo ========================================
echo.
echo Repository URL: https://github.com/thuanthien-tran/elk-based-network-anomaly-detection
echo.
pause
