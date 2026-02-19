@echo off
REM Script to remove large filebeat.exe from git history

echo ========================================
echo Removing large file from git history
echo ========================================
echo.

echo Step 1: Removing filebeat.exe from git tracking...
git rm --cached config/filebeat/filebeat.exe 2>nul
git rm --cached "config/filebeat/filebeat.exe" 2>nul

echo Step 2: Removing from git history using filter-branch...
git filter-branch --force --index-filter "git rm --cached --ignore-unmatch config/filebeat/filebeat.exe" --prune-empty --tag-name-filter cat -- --all

if errorlevel 1 (
    echo.
    echo [WARNING] filter-branch failed, trying alternative method...
    echo.
    echo Step 3: Using git filter-repo (if installed)...
    git filter-repo --path config/filebeat/filebeat.exe --invert-paths 2>nul
    if errorlevel 1 (
        echo.
        echo [INFO] filter-repo not available, using manual method...
        echo.
        echo Step 4: Creating new branch without large file...
        git checkout --orphan temp_branch
        git add .
        git commit -m "ELKShield Network Security Monitoring System - Clean history"
        git branch -D main
        git branch -m main
        echo.
        echo [INFO] Created clean branch. Ready to force push.
        echo Run: git push -f origin main
        pause
        exit /b 0
    )
)

echo.
echo Step 5: Cleaning up...
git for-each-ref --format="delete %(refname)" refs/original | git update-ref --stdin
git reflog expire --expire=now --all
git gc --prune=now --aggressive

echo.
echo [SUCCESS] Large file removed from history!
echo.
echo Now you can push:
echo   git push -f origin main
echo.
pause
