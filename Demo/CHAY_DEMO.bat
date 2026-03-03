@echo off
chcp 65001 >nul
title ELKShield - Demo

REM Chuyển về thư mục gốc dự án (cha của Demo)
cd /d "%~dp0"
cd ..

:menu
cls
echo.
echo  ============================================
echo   ELKShield - HUONG DAN CHAY DEMO
echo  ============================================
echo.
echo   Thu tu goi y: 1 -^> 2 -^> 3 -^> 4 -^> 5 -^> 6 -^> 7
echo.
echo   [1] Cai dat lan dau (setup)
echo   [2] Khoi dong ELK Stack (Docker)
echo   [3] Reset du lieu (xoa index cu)
echo   [4] Chay Filebeat (mo cua so moi - giu mo)
echo   [5] Tao file log mau (Desktop\test.log)
echo   [6] Chay pipeline ML (extract + preprocess + train + ghi ES)
echo   [7] Kiem tra index / Mo Kibana
echo   [0] Thoat
echo.
echo  ============================================
set /p choice="  Chon (0-7): "

if "%choice%"=="1" goto setup
if "%choice%"=="2" goto elk
if "%choice%"=="3" goto reset
if "%choice%"=="4" goto filebeat
if "%choice%"=="5" goto samplelog
if "%choice%"=="6" goto pipeline
if "%choice%"=="7" goto kibana
if "%choice%"=="0" goto end
echo  Lua chon khong hop le.
timeout /t 2 >nul
goto menu

:setup
echo.
echo  [1] Dang chay setup...
call setup.bat
echo.
pause
goto menu

:elk
echo.
echo  [2] Dang khoi dong ELK Stack...
cd docker
docker-compose up -d
cd ..
echo.
echo  Do 1-2 phut roi kiem tra: docker ps
echo  Kibana: http://localhost:5601
echo.
pause
goto menu

:reset
echo.
echo  [3] Reset du lieu...
if exist "reset_data.bat" (
    call reset_data.bat
) else (
    echo  Xoa index thu cong: curl -X DELETE http://127.0.0.1:9200/test-logs-*
    echo  Xoa index thu cong: curl -X DELETE http://127.0.0.1:9200/ml-alerts-*
    echo  Xoa registry Filebeat: rmdir /s /q config\filebeat\data
    set /p do="  Ban co muon xoa config\filebeat\data ngay? (y/n): "
    if /i "%do%"=="y" rmdir /s /q config\filebeat\data 2>nul
)
echo.
pause
goto menu

:filebeat
echo.
echo  [4] Mo cua so Filebeat (dong cua so nay se dung Filebeat)...
set "ROOT=%~dp0.."
start "Filebeat" cmd /k "cd /d %ROOT% && cd config\filebeat && echo Dang chay Filebeat - hay giu cua so nay mo. && echo Sau do chon [5] de tao log mau. && echo. && filebeat.exe -c filebeat-test-simple.yml -e"
echo  Cua so Filebeat da mo. Quay lai menu va chon [5] de tao log mau.
echo.
pause
goto menu

:samplelog
echo.
echo  [5] Tao file log mau tai Desktop\test.log
set "logfile=%USERPROFILE%\Desktop\test.log"
echo  Duong dan: %logfile%
(
echo Jan 19 10:00:01 localhost sshd[1001]: Accepted password for user1 from 192.168.1.10 port 22 ssh2
echo Jan 19 10:00:05 localhost sshd[1002]: Accepted password for user2 from 192.168.1.11 port 22 ssh2
echo Jan 19 10:01:01 localhost sshd[2001]: Failed password for invalid user admin from 10.10.10.10 port 22 ssh2
echo Jan 19 10:01:02 localhost sshd[2002]: Failed password for invalid user admin from 10.10.10.10 port 22 ssh2
echo Jan 19 10:01:03 localhost sshd[2003]: Failed password for invalid user admin from 10.10.10.10 port 22 ssh2
echo Jan 19 10:01:04 localhost sshd[2004]: Failed password for invalid user admin from 10.10.10.10 port 22 ssh2
echo Jan 19 10:02:01 localhost sshd[1004]: Accepted password for user4 from 192.168.1.13 port 22 ssh2
) >> "%logfile%"
echo  Da ghi mau vao file. Neu Filebeat dang chay, doi vai giay roi chon [6].
echo  Luu y: Sua paths trong config\filebeat\filebeat-test-simple.yml neu Desktop khac.
echo.
pause
goto menu

:pipeline
echo.
echo  [6] Chay pipeline ML (extract -^> preprocess -^> train -^> ghi ES)...
python scripts/data_extraction.py --index test-* --output data/raw/logs.csv --hours 999 --host 127.0.0.1 --port 9200
if errorlevel 1 ( echo  Loi extract. Kiem tra ELK va Filebeat. & pause & goto menu )
python scripts/data_preprocessing.py --input data/raw/logs.csv --output data/processed/logs.csv --clean --extract-time --extract-ip --extract-attack
if errorlevel 1 ( echo  Loi preprocessing. & pause & goto menu )
python scripts/ml_detector.py --input data/processed/logs.csv --train --model-type isolation_forest --model-file ml_models/model.pkl --output data/predictions.csv
if errorlevel 1 ( echo  Loi ML. & pause & goto menu )
python scripts/elasticsearch_writer.py --input data/predictions.csv --index ml-alerts --host 127.0.0.1 --port 9200
echo.
echo  Pipeline hoan tat. Chon [7] de mo Kibana va xem ml-alerts-*
echo.
pause
goto menu

:kibana
echo.
echo  [7] Kiem tra index va mo Kibana...
curl -s http://127.0.0.1:9200/_cat/indices?v 2>nul
echo.
echo  Mo trinh duyet: http://localhost:5601
echo  Index pattern: ml-alerts-*  , filter: ml_anomaly: true
start "" "http://localhost:5601"
echo.
pause
goto menu

:end
echo  Thoat.
exit /b 0
