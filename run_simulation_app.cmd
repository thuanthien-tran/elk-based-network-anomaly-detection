@echo off
cd /d "%~dp0"
REM Chay ung dung desktop ELKShield (PySide6). Cai dat: py -m pip install PySide6
py run_simulation_app.py 2>nul || python run_simulation_app.py
if errorlevel 1 pause
