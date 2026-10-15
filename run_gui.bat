@echo off
rem MarkForge - launch the desktop app (GUI) from source
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
start "" pythonw -m markforge gui
