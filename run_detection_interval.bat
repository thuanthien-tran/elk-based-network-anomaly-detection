@echo off
REM Chay Detection online 1 lan. Dat lich chay file nay moi 5-15 phut (Task Scheduler) de gan real-time.
cd /d "%~dp0"
python scripts/run_pipeline_detection.py
exit /b %errorlevel%
