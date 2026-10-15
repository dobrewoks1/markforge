@echo off
rem MarkForge - install Python dependencies (run once)
chcp 65001 >nul
cd /d "%~dp0"
echo Installing MarkForge dependencies...
python -m pip install -r requirements.txt
echo.
echo Done. Now run run_gui.bat to start the app.
echo (For best quality also install pandoc: https://pandoc.org/installing.html)
pause
