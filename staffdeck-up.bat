@echo off
setlocal
REM StaffDeck launcher - pinned to port 8100 (5173/5174 IPv6 are taken by other local apps)
set APP_PORT=8100
cd /d "%~dp0"
"%~dp0backend\.venv\Scripts\python.exe" "%~dp0scripts\dev.py" up --detach
