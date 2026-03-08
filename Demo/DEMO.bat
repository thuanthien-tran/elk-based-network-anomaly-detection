@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
title ELKShield - Demo

REM Chuyển về thư mục gốc dự án (cha của Demo)
cd /d "%~dp0"
cd ..
REM Đảm bảo đúng thư mục (có scripts\data_extraction.py)
if not exist "scripts\data_extraction.py" (
    echo  [LOI] Khong tim thay thu muc du an. Dang o: %CD%
    echo  Chay DEMO.bat tu trong thu muc Demo.
    pause
    exit /b 1
)

REM Buoc setup + ELK Stack chay tu dong khi mo DEMO.bat
echo.
echo  [Khoi dong] Dang chay setup...
set RUN_BY_GUI=1
call setup.bat
echo.
echo  Setup xong. Dang khoi dong ELK Stack (Docker)...
cd docker
docker-compose up -d
cd ..
echo  ELK Stack da khoi dong. Do 1-2 phut co the kiem tra: docker ps
echo  Kibana: http://localhost:5601
echo.
timeout /t 3 >nul
goto menu

:menu
cls
echo.
echo  ============================================
echo   ELKShield Demo - Tu dong hoa
echo  ============================================
echo.
echo  --- He thong (ELK) ---
echo   [1] Reset du lieu (xoa index cu)
echo   [2] Chay Filebeat (doc test.log, gui len ELK)
echo   [3] Kiem tra index / Mo Kibana
echo.
echo  --- Tao log mau (cho test detection) ---
echo   [4] Tao log mau - nhap so dong (Desktop + Documents)
echo   [5] Tao log mau mac dinh (2 normal + 5 attack)
echo.
echo  --- Train model (offline) ---
echo   [6] Train model (menu con: gop dataset / train tung dataset)
echo.
echo  --- Detection (realtime) ---
echo   [7] Detection online (test.log -^> model -^> ml-alerts -^> Kibana)
echo       Can da train [6]-[1] va bat [2] Filebeat.
echo.
echo  --- Demo ---
echo   [8] Demo nhanh (chi Python, khong ELK)
echo   [9] Chay nhanh: tao log -^> pipeline -^> Kibana
echo.
echo   [0] Thoat
echo.
echo  Thu tu goi y: [5] tao log -^> [2] Filebeat -^> [6] train [1] unified -^> [7] Detection online
echo  ============================================
set /p choice="  Chon (0-9): "

if "%choice%"=="1" goto reset
if "%choice%"=="2" goto filebeat
if "%choice%"=="3" goto kibana
if "%choice%"=="4" goto samplelog
if "%choice%"=="5" goto samplelog_default
if "%choice%"=="6" goto train_menu
if "%choice%"=="7" goto pipeline_detection
if "%choice%"=="8" goto demo_quick
if "%choice%"=="9" goto quick_full
if "%choice%"=="0" goto end
echo  Lua chon khong hop le.
timeout /t 2 >nul
goto menu

:train_menu
cls
echo.
echo  ============================================
echo   Train model (offline)
echo  ============================================
echo.
echo  --- Gop dataset (tich hop) ---
echo   [1] Train UNIFIED (Synthetic + Russell + Kaggle -^> ssh_attack_model.joblib)
echo       Can da chay [2] roi [3][4] de co file processed. Sau do dung [7] Detection online.
echo.
echo   [2] Chuan bi dataset Synthetic (sinh ~8000 dong -^> data/processed/logs.csv)
echo       Chi tao du lieu, khong train. Dung cho [1] unified.
echo.
echo  --- Train theo tung dataset ---
echo   [3] Train tu Russell Mitchell (auth.log -^> CSV -^> train -^> ghi ES)
echo       Can thu muc data\russellmitchell\gather
echo.
echo   [4] Train tu file CSV co san (A: Russell CSV, B: Kaggle, C: File bat ky)
echo.
echo   [0] Quay lai menu chinh
echo.
set /p dchoice="  Chon (0-4): "
if "%dchoice%"=="0" goto menu
if "%dchoice%"=="1" goto train_unified
if "%dchoice%"=="2" goto dataset_improved
if "%dchoice%"=="3" goto pipeline_russellmitchell
if "%dchoice%"=="4" goto pipeline_csv_menu
echo  Khong hop le.
timeout /t 2 >nul
goto train_menu

:reset
echo.
echo  [1] Reset du lieu...
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
echo  [2] Mo cua so Filebeat (doc Documents\test.log, gui len ELK)...
if not exist "%USERPROFILE%\Documents\test.log" (
    echo  [Canh bao] File chua ton tai: Documents\test.log
    echo  Chon [5] tao log truoc roi chay [2] lai.
    echo.
    pause
    goto menu
)
set "ROOT=%~dp0.."
start "Filebeat" cmd /k "cd /d %ROOT%\config\filebeat && Chay_Filebeat.bat"
echo  Cua so Filebeat da mo. Thu tu: [5] tao log -^> [2] Filebeat -^> doi 20s -^> [7] Detection online.
echo.
pause
goto menu

:samplelog
echo.
echo  [4] Tao file log mau (Desktop + Documents) - nhap so dong
set "log1=%USERPROFILE%\Desktop\test.log"
set "log2=%USERPROFILE%\Documents\test.log"
echo  Duong dan: %log2%  va  %log1%
set /p normal_count="  Nhap so dong binh thuong (mac dinh 2): "
if "%normal_count%"=="" set normal_count=2
set /p attack_count="  Nhap so dong tan cong (mac dinh 5): "
if "%attack_count%"=="" set attack_count=5
REM Loai khoang trang thua
set "normal_count=!normal_count: =!"
set "attack_count=!attack_count: =!"
if "!normal_count!"=="" set normal_count=2
if "!attack_count!"=="" set attack_count=5
echo.
echo  Xoa noi dung cu trong test.log, ghi lai !normal_count! dong binh thuong + !attack_count! dong tan cong...
type nul > "%log1%"
type nul > "%log2%"
for /L %%i in (1,1,!normal_count!) do (
  set "n=00%%i"
  echo Jan 19 10:00:!n:~-2! localhost sshd[10!n:~-2!]: Accepted password for user%%i from 192.168.1.%%i port 22 ssh2>> "%log1%"
  echo Jan 19 10:00:!n:~-2! localhost sshd[10!n:~-2!]: Accepted password for user%%i from 192.168.1.%%i port 22 ssh2>> "%log2%"
)
for /L %%j in (1,1,!attack_count!) do (
  set "m=00%%j"
  echo Jan 19 10:01:!m:~-2! localhost sshd[20!m:~-2!]: Failed password for invalid user admin from 10.10.10.10 port 22 ssh2>> "%log1%"
  echo Jan 19 10:01:!m:~-2! localhost sshd[20!m:~-2!]: Failed password for invalid user admin from 10.10.10.10 port 22 ssh2>> "%log2%"
)
echo  Da xoa cu, ghi moi !normal_count!+!attack_count! dong. File: %log2% (va Desktop\test.log)
echo  QUAN TRONG: Neu chua chay Filebeat, chon [2] truoc. Giu cua so Filebeat mo, doi 15 giay roi chon [7] Detection online.
echo.
pause
goto menu

:pipeline_detection
cd /d "%~dp0"
cd ..
echo.
echo  Detection online: extract -^> preprocess -^> load model -^> predict -^> ml-alerts...
if not exist "data\models" mkdir data\models
call python scripts/run_pipeline_detection.py
if errorlevel 1 (
    echo.
    echo  [Loi] Pipeline dung lai. Chay [6] roi [1] train unified truoc, hoac [2] Filebeat.
    set /p open_fb="  Nhan Y de mo Filebeat, phim khac de quay menu: "
    if /i "!open_fb!"=="Y" goto filebeat
)
echo.
pause
goto menu

:train_unified
cd /d "%~dp0"
cd ..
echo.
echo  Train unified model (Synthetic + Russell + Kaggle -^> data/models/ssh_attack_model.joblib)...
if not exist "data\models" mkdir data\models
if not exist "data\training" mkdir data\training
call python scripts/train_model.py
if errorlevel 1 (
    echo  [Loi] Train that bai. Kiem tra da co 3 file processed: logs.csv, russellmitchell_processed.csv, pipeline_ssh_processed.csv
    pause
    goto menu
)
echo  Thanh cong. Sau do chon [7] Detection online de chay voi model nay.
pause
goto menu

:kibana
echo.
echo  [3] Kiem tra index va mo Kibana...
curl -s http://127.0.0.1:9200/_cat/indices?v 2>nul
echo.
echo  Mo trinh duyet: http://localhost:5601
echo  Index pattern: ml-alerts-*  , filter: ml_anomaly: true
start "" "http://localhost:5601"
echo.
pause
goto menu

:demo_quick
echo.
echo  [8] Demo nhanh (chi Python, khong can ELK/Filebeat)...
python scripts/demo_quick.py
echo.
pause
goto menu

:quick_full
echo.
echo  [9] Chay nhanh: tao log -^> pipeline -^> Kibana (can ELK + Filebeat dang chay)...
set "log1=%USERPROFILE%\Desktop\test.log"
set "log2=%USERPROFILE%\Documents\test.log"
(
echo Jan 19 10:00:01 localhost sshd[1001]: Accepted password for user1 from 192.168.1.10 port 22 ssh2
echo Jan 19 10:01:01 localhost sshd[2001]: Failed password for invalid user admin from 10.10.10.10 port 22 ssh2
echo Jan 19 10:01:02 localhost sshd[2002]: Failed password for invalid user admin from 10.10.10.10 port 22 ssh2
) >> "%log1%"
(
echo Jan 19 10:00:01 localhost sshd[1001]: Accepted password for user1 from 192.168.1.10 port 22 ssh2
echo Jan 19 10:01:01 localhost sshd[2001]: Failed password for invalid user admin from 10.10.10.10 port 22 ssh2
echo Jan 19 10:01:02 localhost sshd[2002]: Failed password for invalid user admin from 10.10.10.10 port 22 ssh2
) >> "%log2%"
echo  Da ghi log mau vao Desktop\test.log va Documents\test.log
echo  (Filebeat phai doc dung 1 trong 2 file - xem config\filebeat\filebeat-test-simple.yml)
echo  Doi 15 giay de Filebeat gui log vao Elasticsearch...
timeout /t 15 /nobreak >nul
if not exist "data\models" mkdir data\models
call python scripts/data_extraction.py --index "test-logs-*,ssh-logs-*" --output data/raw/logs.csv --hours 8760 --host 127.0.0.1 --port 9200
if errorlevel 1 (
    echo. & echo  [Loi] Extract. Kiem tra Filebeat, Logstash; path: C:/Users/thuan/Documents/test.log
    echo  Nhan phim bat ky de quay lai menu...
    pause >nul
    goto menu
)
call python scripts/data_preprocessing.py --input data/raw/logs.csv --output data/processed/logs.csv --clean --extract-time --extract-ip --extract-attack
if errorlevel 1 (
    echo. & echo  [Loi] Khong co du lieu. Chay [4] hoac [5] tao log, doi 15s, roi thu lai [9].
    echo  Nhan phim bat ky de quay lai menu...
    pause >nul
    goto menu
)
call python scripts/ml_detector.py --input data/processed/logs.csv --train --model-type isolation_forest --model-file data/models/rf_ssh_isolation_forest.joblib --output data/predictions.csv
if errorlevel 1 (
    echo. & echo  [Loi] ML that bai. Nhan phim bat ky de quay lai menu...
    pause >nul
    goto menu
)
call python scripts/elasticsearch_writer.py --input data/predictions.csv --index ml-alerts --host 127.0.0.1 --port 9200 --model-name synthetic
echo  Mo Kibana...
start "" "http://localhost:5601"
echo  Xong. Index pattern: ml-alerts-*
echo  Nhan phim bat ky de quay lai menu...
pause >nul
goto menu

:samplelog_default
echo.
echo  [5] Tao log mau mac dinh (2 dong binh thuong + 5 dong tan cong)...
set "log1=%USERPROFILE%\Desktop\test.log"
set "log2=%USERPROFILE%\Documents\test.log"
(
echo Jan 19 10:00:01 localhost sshd[1001]: Accepted password for user1 from 192.168.1.10 port 22 ssh2
echo Jan 19 10:00:02 localhost sshd[1002]: Accepted password for user2 from 192.168.1.11 port 22 ssh2
echo Jan 19 10:01:01 localhost sshd[2001]: Failed password for invalid user admin from 10.10.10.10 port 22 ssh2
echo Jan 19 10:01:02 localhost sshd[2002]: Failed password for invalid user admin from 10.10.10.10 port 22 ssh2
echo Jan 19 10:01:03 localhost sshd[2003]: Failed password for invalid user admin from 10.10.10.10 port 22 ssh2
echo Jan 19 10:01:04 localhost sshd[2004]: Failed password for invalid user admin from 10.10.10.10 port 22 ssh2
echo Jan 19 10:01:05 localhost sshd[2005]: Failed password for invalid user admin from 10.10.10.10 port 22 ssh2
) >> "%log1%"
(
echo Jan 19 10:00:01 localhost sshd[1001]: Accepted password for user1 from 192.168.1.10 port 22 ssh2
echo Jan 19 10:00:02 localhost sshd[1002]: Accepted password for user2 from 192.168.1.11 port 22 ssh2
echo Jan 19 10:01:01 localhost sshd[2001]: Failed password for invalid user admin from 10.10.10.10 port 22 ssh2
echo Jan 19 10:01:02 localhost sshd[2002]: Failed password for invalid user admin from 10.10.10.10 port 22 ssh2
echo Jan 19 10:01:03 localhost sshd[2003]: Failed password for invalid user admin from 10.10.10.10 port 22 ssh2
echo Jan 19 10:01:04 localhost sshd[2004]: Failed password for invalid user admin from 10.10.10.10 port 22 ssh2
echo Jan 19 10:01:05 localhost sshd[2005]: Failed password for invalid user admin from 10.10.10.10 port 22 ssh2
) >> "%log2%"
echo  Da ghi vao Desktop\test.log va Documents\test.log.
echo  Neu chua chay Filebeat: chon [2], doi 15 giay, roi chon [7] Detection online.
echo.
pause
goto menu

:pipeline_russellmitchell
echo.
echo  Dataset Russell Mitchell (auth.log -^> CSV -^> preprocess -^> train -^> ghi ES)...
if not exist "data\russellmitchell\gather" (
    echo  Thu muc data\russellmitchell\gather khong ton tai. Dat dataset russellmitchell vao data\russellmitchell
    pause
    goto menu
)
if not exist "data\models" mkdir data\models
if not exist "data\raw" mkdir data\raw
if not exist "data\processed" mkdir data\processed
echo  Buoc 1/4: Chuyen auth.log thanh CSV...
python scripts/russellmitchell_auth_to_csv.py --data-dir data/russellmitchell --output data/raw/russellmitchell_auth.csv --with-labels
if errorlevel 1 ( echo  Loi convert. & pause & goto menu )
echo  Buoc 2/4: Tien xu ly...
python scripts/data_preprocessing.py --input data/raw/russellmitchell_auth.csv --output data/processed/russellmitchell_processed.csv --clean --extract-time --extract-ip --extract-attack --log-type ssh
if errorlevel 1 ( echo  Loi preprocessing. & pause & goto menu )
echo  Buoc 3/4: Train ML...
python scripts/ml_detector.py --input data/processed/russellmitchell_processed.csv --train --model-type random_forest --model-file data/models/rf_russellmitchell.joblib --output data/processed/russellmitchell_predictions.csv --handle-imbalance
if errorlevel 1 ( echo  Loi ML. & pause & goto menu )
echo  Buoc 4/4: Ghi vao Elasticsearch (neu ELK dang chay)...
call python scripts/elasticsearch_writer.py --input data/processed/russellmitchell_predictions.csv --index ml-alerts --host 127.0.0.1 --port 9200 --model-name russellmitchell
if errorlevel 1 ( echo  Khong ghi duoc ES - xem loi tren. Ket qua da luu CSV. ) else ( echo  Da ghi ml-alerts. Chon [3] xem Kibana. )
echo.
echo  Hoan tat. Model: data\models\rf_russellmitchell.joblib
echo.
pause
goto menu

:pipeline_csv_menu
echo.
echo  Dataset tu file CSV co san
echo    A - Russell Mitchell CSV (data\raw\russellmitchell_auth.csv)
echo    B - SSH Kaggle (data\ssh_anomaly_dataset.csv, convert -^> train)
echo    C - File CSV bat ky (ban nhap duong dan)
echo    X - Quay lai menu chinh
set /p sub="  Chon (A/B/C/X): "
if /i "%sub%"=="A" goto pipeline_csv_russellmitchell
if /i "%sub%"=="B" goto pipeline_csv_kaggle
if /i "%sub%"=="C" goto pipeline_csv_custom
if /i "%sub%"=="X" goto menu
echo  Khong hop le.
timeout /t 2 >nul
goto pipeline_csv_menu

:pipeline_csv_russellmitchell
echo.
echo  Chay pipeline tu data\raw\russellmitchell_auth.csv ...
if not exist "data\raw\russellmitchell_auth.csv" (
    echo  Chua co file. Chon [6] roi [3] truoc de train tu Russell Mitchell.
    pause
    goto menu
)
if not exist "data\models" mkdir data\models
if not exist "data\processed" mkdir data\processed
python scripts/data_preprocessing.py --input data/raw/russellmitchell_auth.csv --output data/processed/russellmitchell_processed.csv --clean --extract-time --extract-ip --extract-attack --log-type ssh
if errorlevel 1 ( echo  Loi preprocessing. & pause & goto menu )
python scripts/ml_detector.py --input data/processed/russellmitchell_processed.csv --train --model-type random_forest --model-file data/models/rf_russellmitchell.joblib --output data/processed/russellmitchell_predictions.csv --handle-imbalance
if errorlevel 1 ( echo  Loi ML. & pause & goto menu )
python scripts/elasticsearch_writer.py --input data/processed/russellmitchell_predictions.csv --index ml-alerts --host 127.0.0.1 --port 9200 --model-name russellmitchell 2>nul
echo  Xong. Chon [3] xem Kibana.
pause
goto menu

:pipeline_csv_kaggle
echo.
echo  Chay pipeline tu data\ssh_anomaly_dataset.csv (Kaggle)...
if not exist "data\ssh_anomaly_dataset.csv" (
    echo  Chua co file data\ssh_anomaly_dataset.csv. Hay dat file vao thu muc data\
    pause
    goto menu
)
if not exist "data\models" mkdir data\models
python scripts/run_pipeline_ssh.py --input data/ssh_anomaly_dataset.csv --kaggle --output-dir data --model-type random_forest
if errorlevel 1 ( echo  Loi pipeline. & pause & goto menu )
echo  Xong. Model va predictions trong data\models va data\processed
pause
goto menu

:pipeline_csv_custom
echo.
set /p custom_csv="  Nhap duong dan file CSV (vd: data/raw/my.csv): "
if "%custom_csv%"=="" ( echo  Bo qua. & pause & goto menu )
if not exist "%custom_csv%" ( echo  File khong ton tai. & pause & goto menu )
if not exist "data\models" mkdir data\models
echo  Preprocess + Train...
python scripts/data_preprocessing.py --input "%custom_csv%" --output data/processed/custom_processed.csv --clean --extract-time --extract-ip --extract-attack --log-type ssh
if errorlevel 1 ( echo  Loi preprocessing. & pause & goto menu )
python scripts/ml_detector.py --input data/processed/custom_processed.csv --train --model-type random_forest --model-file data/models/rf_custom.joblib --output data/processed/custom_predictions.csv --handle-imbalance
if errorlevel 1 ( echo  Loi ML. & pause & goto menu )
set /p write_es="  Ghi vao Elasticsearch? (y/n): "
if /i "!write_es!"=="y" python scripts/elasticsearch_writer.py --input data/processed/custom_predictions.csv --index ml-alerts --host 127.0.0.1 --port 9200 --model-name csv
echo  Xong.
pause
goto menu

:dataset_improved
echo.
echo  Dataset Synthetic cai tien (sinh 8000 dong -^> data/raw/logs.csv -^> data/processed/logs.csv)
if not exist "data\raw" mkdir data\raw
if not exist "data\processed" mkdir data\processed
echo  Buoc 1/2: Sinh CSV raw (8000 dong, 14 ngay, 85%% normal, nhieu IP/user tan cong)...
python scripts/generate_synthetic_logs.py --total 8000 --normal-ratio 0.85 --days 14 --replace-logs
if errorlevel 1 ( echo  Loi sinh dataset. & pause & goto menu )
echo  Buoc 2/2: Tien xu ly -^> data/processed/logs.csv...
python scripts/data_preprocessing.py --input data/raw/logs.csv --output data/processed/logs.csv --clean --extract-time --extract-ip --extract-attack
if errorlevel 1 ( echo  Loi preprocessing. & pause & goto menu )
echo  Xong. Dataset da cap nhat. Chon [6]-[1] train unified, hoac [8] demo nhanh.
echo.
pause
goto menu

:end
echo  Thoat.
exit /b 0
