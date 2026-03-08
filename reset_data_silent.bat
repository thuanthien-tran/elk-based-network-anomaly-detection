@echo off
REM Reset du lieu ELKShield - KHONG hoi (dung cho app/GUI). In ra tung buoc de co output.
cd /d "%~dp0"

echo ========================================
echo RESET DATA - ELKShield (silent)
echo ========================================
echo.

echo [1/4] Xoa index test-logs-*...
curl -s -X DELETE "http://127.0.0.1:9200/test-logs-*"
echo.
echo [OK] test-logs-* da gui lenh xoa.
echo.

echo [2/4] Xoa index ml-alerts-*...
curl -s -X DELETE "http://127.0.0.1:9200/ml-alerts-*"
echo.
echo [OK] ml-alerts-* da gui lenh xoa.
echo.

echo [3/4] Xoa registry Filebeat (config\filebeat\data)...
if exist "config\filebeat\data" (
    rmdir /s /q "config\filebeat\data"
    echo [OK] config\filebeat\data da xoa.
) else (
    echo [SKIP] config\filebeat\data khong ton tai.
)
echo.

echo [4/4] Kiem tra indices sau khi xoa...
curl -s "http://127.0.0.1:9200/_cat/indices?v" 2>nul
echo.

echo ========================================
echo Reset hoan tat.
echo ========================================
exit /b 0
