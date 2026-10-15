@echo off
rem MarkForge - HTTP service (bridge for a future mobile app). Open http://127.0.0.1:8000
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
python -m markforge serve --host 127.0.0.1 --port 8000
pause
