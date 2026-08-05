@echo off
setlocal
set APP_PORT=8100
cd /d "%~dp0"
"%~dp0backend\.venv\Scripts\python.exe" "%~dp0scripts\dev.py" down
