@echo off
cd /d "%~dp0"
call .venv\Scripts\python.exe main.py
if errorlevel 1 pause
