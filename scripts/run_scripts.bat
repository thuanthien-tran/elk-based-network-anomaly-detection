@echo off
REM Batch script to run Python scripts from scripts directory
REM Usage: run_scripts.bat [script_name] [arguments]

if "%1"=="" (
    echo Usage: run_scripts.bat [script_name] [arguments]
    echo.
    echo Examples:
    echo   run_scripts.bat data_extraction.py --index ssh-logs-* --output ../data/raw/ssh_logs.csv
    echo   run_scripts.bat ml_detector.py --input ../data/processed/logs.csv --train
    exit /b 1
)

python %*
