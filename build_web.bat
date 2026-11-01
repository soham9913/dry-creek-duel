@echo off
REM Builds the browser version for itch.io: release\dry-creek-duel-web.zip
REM Add "--serve" to play it locally first:  build_web.bat --serve  (then open http://localhost:8000)
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
    py -3 -m venv .venv 2>nul || python -m venv .venv
)
.venv\Scripts\python.exe -m pip install --quiet -r requirements.txt pygbag
.venv\Scripts\python.exe tools\build_web.py %*
pause
