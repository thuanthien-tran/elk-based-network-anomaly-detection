@echo off
REM Script to reset all data for fresh attack simulation
REM This will delete old indices and prepare for new test

echo ========================================
echo RESET DATA - ELKShield Project
echo ========================================
echo.
echo [WARNING] This will delete source + alert indices:
echo           test-logs-*, ssh-logs-*, filebeat-*, logstash-*, logs-*, ml-alerts-*
echo.

set /p confirm="Are you sure? (yes/no): "
if /i not "%confirm%"=="yes" (
    echo Cancelled.
    pause
    exit /b
)

echo.
echo [1/6] Listing current indices...
curl -s http://127.0.0.1:9200/_cat/indices?v | findstr /i "test-logs ssh-logs filebeat logstash logs ml-alerts"
echo.

echo [2/6] Deleting indices by patterns...
setlocal EnableDelayedExpansion
set "ANY_DELETED=0"
for /f "usebackq delims=" %%I in (`curl -s "http://127.0.0.1:9200/_cat/indices?h=index" ^| findstr /r /i "^test-logs- ^ssh-logs- ^filebeat- ^logstash- ^logs- ^ml-alerts-"`) do (
    set "IDX=%%I"
    if not "!IDX!"=="" (
        echo   Deleting index: !IDX!
        curl -s -X DELETE "http://127.0.0.1:9200/!IDX!" >nul 2>&1
        set "ANY_DELETED=1"
    )
)
if "!ANY_DELETED!"=="1" (
    echo [OK] Matching indices deleted
) else (
    echo [SKIP] No matching indices found
)
echo.

echo [3/6] Verifying deletion...
timeout /t 2 /nobreak >nul
curl -s http://127.0.0.1:9200/_cat/indices?v | findstr /i "test-logs ssh-logs filebeat logstash logs ml-alerts"
if %ERRORLEVEL% EQU 0 (
    echo [WARNING] Some indices still exist!
) else (
    echo [OK] All matching source + alert indices deleted
)
echo.

echo [4/6] Cleaning old CSV files...
if exist "data\raw\logs.csv" del /q "data\raw\logs.csv"
if exist "data\processed\logs.csv" del /q "data\processed\logs.csv"
if exist "data\predictions.csv" del /q "data\predictions.csv"
if exist "data\processed\predictions_demo.csv" del /q "data\processed\predictions_demo.csv"
if exist "data\processed\logs_with_ml.csv" del /q "data\processed\logs_with_ml.csv"
echo [OK] CSV files cleaned
echo.

echo [5/6] Xoa registry Filebeat (config\filebeat\data)...
if exist "config\filebeat\data" (
    rmdir /s /q "config\filebeat\data"
    echo [OK] config\filebeat\data deleted
) else (
    echo [SKIP] config\filebeat\data not found
)
echo.

echo [6/6] ML model (data\models\*.joblib, ml_models\*.pkl)...
set /p del_model="Xoa model cu de train lai tu dau? (yes/no): "
if /i "%del_model%"=="yes" (
    if exist "data\models\*.joblib" (
        del /q "data\models\*.joblib"
        echo [OK] data\models\*.joblib deleted
    )
    if exist "ml_models\model.pkl" (
        del /q "ml_models\model.pkl"
        echo [OK] ml_models\model.pkl deleted
    )
) else (
    echo [SKIP] Model giu nguyen (pipeline [6] se ghi de khi train lai)
)
echo.

echo ========================================
echo Reset completed!
echo ========================================
echo.
echo Final index status:
curl -s http://127.0.0.1:9200/_cat/indices?v
echo.
echo Next steps:
echo 1. Create new test.log file with attack logs
echo 2. Restart Filebeat: cd config\filebeat ^&^& filebeat.exe -c filebeat-test-simple.yml -e
echo 3. Run ML pipeline again
echo.
pause
