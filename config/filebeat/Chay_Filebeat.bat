@echo off
chcp 65001 >nul
title Filebeat - ELKShield
cd /d "%~dp0"
set "LOGFILE=%USERPROFILE%\Documents\test.log"
set "LOGFILE_YML=%LOGFILE:\=/%"
REM Tao file config tam voi duong dan dung (thay the path trong yml)
powershell -NoProfile -Command "$yml='%~dp0filebeat-test-simple.yml'; $out='%~dp0filebeat-test-simple-generated.yml'; $path='%LOGFILE_YML%'; (Get-Content $yml -Raw) -replace 'C:/Users/[^/]+/Documents/test\\.log', $path | Set-Content $out -Encoding UTF8"
if exist "%~dp0filebeat-test-simple-generated.yml" (
    set "CONFIG=%~dp0filebeat-test-simple-generated.yml"
) else (
    set "CONFIG=%~dp0filebeat-test-simple.yml"
)

echo.
echo  Filebeat: doc %LOGFILE% --^> Logstash :5044 --^> Elasticsearch
echo  Giu cua so nay MO. Dong cua so = dung Filebeat.
echo.
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "RUN_TS=%%i"
set "FB_DATA=%~dp0data-runs\%RUN_TS%"
set "FB_LOGS=%~dp0logs"
if not exist "%FB_DATA%" mkdir "%FB_DATA%" >nul 2>&1
if not exist "%FB_LOGS%" mkdir "%FB_LOGS%" >nul 2>&1
echo  Filebeat data path: %FB_DATA%
echo  Filebeat logs path: %FB_LOGS%
echo  Run ID: %RUN_TS%
echo.

REM Restart-safe: kill any stale Filebeat process that may keep registry lock.
taskkill /IM filebeat.exe /F >nul 2>&1
timeout /t 1 /nobreak >nul

REM Kiem tra file log ton tai
if not exist "%LOGFILE%" (
    echo  [Canh bao] File chua ton tai: %LOGFILE%
    echo  Trong DEMO.bat chon [5] tao log truoc roi chay [2] lai.
    echo.
    pause
    exit /b 1
)
echo  File log: %LOGFILE%
echo.

REM Kiem tra Logstash (port 5044) da mo chua
powershell -NoProfile -Command "$t=New-Object Net.Sockets.TcpClient; try { $t.Connect('127.0.0.1',5044); $t.Close(); exit 0 } catch { exit 1 }" >nul 2>&1
if errorlevel 1 (
    echo  [Canh bao] Logstash chua mo port 5044. Chay [2] ELK truoc roi thu lai [4].
    echo.
)

where filebeat >nul 2>&1
if %errorlevel% equ 0 (
    echo  Dang khoi dong Filebeat...
    filebeat run -e -c "%CONFIG%" --path.data "%FB_DATA%" --path.logs "%FB_LOGS%"
    goto :done
)
where filebeat.exe >nul 2>&1
if %errorlevel% equ 0 (
    echo  Dang khoi dong Filebeat...
    filebeat.exe run -e -c "%CONFIG%" --path.data "%FB_DATA%" --path.logs "%FB_LOGS%"
    goto :done
)
if exist "%~dp0filebeat.exe" (
    echo  Dang khoi dong Filebeat...
    "%~dp0filebeat.exe" run -e -c "%CONFIG%" --path.data "%FB_DATA%" --path.logs "%FB_LOGS%"
    goto :done
)

echo  [LOI] Khong tim thay filebeat / filebeat.exe
echo.
echo  Cai dat Filebeat:
echo  1. Tai: https://www.elastic.co/downloads/beats/filebeat
echo  2. Giai nen (vd: C:\Filebeat)
echo  3. Them vao PATH HOAC copy 2 file nay vao thu muc Filebeat:
echo     - Chay_Filebeat.bat
echo     - filebeat-test-simple.yml
echo     roi double-click Chay_Filebeat.bat trong thu muc Filebeat
echo.
pause
:done
