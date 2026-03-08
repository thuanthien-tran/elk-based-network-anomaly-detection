@echo off
cd /d "%~dp0"
REM Dung "py" (Windows launcher) hoac "python" - cai streamlit bang cung lenh do: py -m pip install streamlit
py run_simulation.py 2>nul || python run_simulation.py
if errorlevel 1 pause
