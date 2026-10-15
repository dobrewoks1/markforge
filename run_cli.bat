@echo off
rem MarkForge - command line. Example: run_cli.bat convert book.md -t epub
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
python -m markforge %*
