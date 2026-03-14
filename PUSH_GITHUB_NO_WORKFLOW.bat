@echo off
chcp 65001 >nul
REM Push len GitHub khi token CHUA co quyen "workflow" - tam bo file .github/workflows de push duoc

cd /d "%~dp0"

echo.
echo  Push (tam bo workflow file) - ELKShield
echo.

git rm --cached .github/workflows/test.yml 2>nul
git add .
git reset -- data/ 2>nul
git status -s

set /p MSG="Commit message (Enter = Push without workflow): "
if "%MSG%"=="" set "MSG=Push without workflow file - add workflow scope to token to push workflow later"
git add -A
git commit -m "%MSG%" 2>nul
git push origin main
echo.
pause
