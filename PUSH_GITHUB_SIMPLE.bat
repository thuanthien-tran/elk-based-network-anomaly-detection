@echo off
chcp 65001 >nul
REM Script push len GitHub - chay tu thu muc goc du an

cd /d "%~dp0"

echo.
echo  ========================================
echo   PUSH LEN GITHUB - ELKShield
echo  ========================================
echo   Repository: elk-based-network-anomaly-detection
echo  ========================================
echo.

if not exist ".git" (
    echo  [ERROR] Chua khoi tao Git.
    echo   Chay: git init
    echo   Sau do: git remote add origin https://github.com/thuanthien-tran/elk-based-network-anomaly-detection.git
    echo.
    pause
    exit /b 1
)

echo  [1/5] Trang thai Git...
git status -s
echo.

echo  [2/5] Bo qua dataset (data/) - khong day len...
git rm -r --cached data/ 2>nul
echo    Dataset giu lai o may, khong push.
echo.

echo  [3/5] Add file (tuan thu .gitignore, bo data/)...
git add .
git reset -- data/ 2>nul
echo.

git diff --staged --quiet 2>nul
if %ERRORLEVEL% EQU 0 (
    echo  [INFO] Khong co thay doi de commit.
    echo   Neu muon push ban commit truoc: git push origin main
    echo.
    pause
    exit /b 0
)

echo  [4/5] Commit...
set /p MSG="  Nhap commit message (Enter = mac dinh): "
if "%MSG%"=="" set "MSG=Update ELKShield project"
git commit -m "%MSG%"
if %ERRORLEVEL% NEQ 0 (
    echo  [ERROR] Commit that bai.
    pause
    exit /b 1
)
echo.

echo  [5/5] Push len origin main...
git push origin main

if %ERRORLEVEL% EQU 0 (
    echo.
    echo  [SUCCESS] Da push len GitHub.
    echo   Xem tai: https://github.com/thuanthien-tran/elk-based-network-anomaly-detection
) else (
    echo.
    echo  [ERROR] Push that bai.
    echo   Kiem tra:
    echo   - Dang nhap GitHub (Personal Access Token hoac SSH)
    echo   - Mang internet
    echo   - Nhanh remote: git remote -v
    echo   - Thu: git push -u origin main
)
echo.
pause
