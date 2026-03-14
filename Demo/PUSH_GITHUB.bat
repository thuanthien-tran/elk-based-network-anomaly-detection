@echo off
chcp 65001 >nul
title ELKShield - Push len GitHub (bo qua data)

:: Chuyen ve thu muc goc du an (cha cua Demo)
cd /d "%~dp0.."

echo.
echo ========================================
echo   ELKShield - Push len GitHub
echo ========================================
echo.
echo   Thu muc data/ KHONG duoc day len (da nam trong .gitignore).
echo   Chi code, config, docs, Demo duoc commit.
echo.

git status
if errorlevel 1 (
    echo.
    echo   Chua co Git hoac chua "git init". Hay chay "git init" trong thu muc du an truoc.
    pause
    exit /b 1
)

echo.
set /p MSG="Nhap commit message (Enter = 'Update ELKShield'): "
if "%MSG%"=="" set MSG=Update ELKShield

git add .
echo.
echo   Da add cac file (tru data/, venv/, ... theo .gitignore)
echo.
git status
echo.
set /p CONFIRM="Commit va push? (Y/N): "
if /i not "%CONFIRM%"=="Y" (
    echo   Huy.
    pause
    exit /b 0
)

git commit -m "%MSG%"
if errorlevel 1 (
    echo.
    echo   Khong co thay doi de commit, hoac loi commit.
    pause
    exit /b 1
)

git push
if errorlevel 1 (
    echo.
    echo   Loi push. Kiem tra remote "origin" va mang.
    echo   Lan dau: git remote add origin https://github.com/USER/REPO.git
    pause
    exit /b 1
)

echo.
echo   Xong. Da day len GitHub (khong ke data).
pause
