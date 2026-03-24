@echo off
REM Reset du lieu ELKShield - KHONG hoi (dung cho app/GUI). In ra tung buoc de co output.
cd /d "%~dp0"
setlocal EnableExtensions EnableDelayedExpansion

echo ========================================
echo RESET DATA - ELKShield (silent)
echo ========================================
echo.

echo [1/4] Xoa index nguon + alert (test/ssh/filebeat/logstash/logs/ml-alerts)...
set "ANY_DELETED=0"
for /f "usebackq delims=" %%I in (`curl -s "http://127.0.0.1:9200/_cat/indices?h=index" ^| findstr /r /i "^test-logs- ^ssh-logs- ^filebeat- ^logstash- ^logs- ^ml-alerts-"`) do (
    set "IDX=%%I"
    if not "!IDX!"=="" (
        echo   Deleting index: !IDX!
        curl -s -X DELETE "http://127.0.0.1:9200/!IDX!" >nul
        set "ANY_DELETED=1"
    )
)
if "!ANY_DELETED!"=="1" (
    echo [OK] Da xoa cac index khop pattern.
) else (
    echo [SKIP] Khong co index nao khop pattern can xoa.
)
echo.

echo [2/4] Xoa registry Filebeat (config\filebeat\data)...
if exist "config\filebeat\data" (
    rmdir /s /q "config\filebeat\data"
    echo [OK] config\filebeat\data da xoa.
) else (
    echo [SKIP] config\filebeat\data khong ton tai.
)
echo.

echo [3/4] Kiem tra indices sau khi xoa...
curl -s "http://127.0.0.1:9200/_cat/indices?v" 2>nul
echo.

echo [4/4] Hoan tat reset.
echo.

echo ========================================
echo Reset hoan tat.
echo ========================================
exit /b 0
