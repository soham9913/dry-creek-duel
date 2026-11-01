@echo off
REM ---------------------------------------------------------------------------
REM  Builds the Windows download for itch.io:  release\DryCreekDuel-windows.zip
REM  Double-click this file (or run it from a terminal) on a Windows PC.
REM  Players then unzip it and run DryCreekDuel.exe - no Python needed.
REM ---------------------------------------------------------------------------
setlocal
cd /d "%~dp0"

if not exist .venv\Scripts\python.exe (
    echo Creating a virtual environment...
    py -3 -m venv .venv 2>nul || python -m venv .venv
    if errorlevel 1 goto :fail
)
set PY=.venv\Scripts\python.exe

echo Installing build tools...
%PY% -m pip install --quiet --upgrade pip
%PY% -m pip install --quiet -r requirements.txt pyinstaller pillow
if errorlevel 1 goto :fail

echo Making the icon...
%PY% tools\make_icons.py
if errorlevel 1 goto :fail

echo Building DryCreekDuel.exe ...
REM Absolute paths: PyInstaller resolves relative --add-data/--icon paths from the spec folder.
set HERE=%~dp0
%PY% -m PyInstaller --noconfirm --clean --windowed --name DryCreekDuel ^
    --icon "%HERE%assets\icon.ico" ^
    --add-data "%HERE%assets\fonts;assets\fonts" ^
    --add-data "%HERE%assets\sounds;assets\sounds" ^
    --distpath "%HERE%build\dist" --workpath "%HERE%build\pyinstaller" --specpath "%HERE%build" ^
    "%HERE%main.py"
if errorlevel 1 goto :fail

copy /y README-PLAYERS.txt build\dist\DryCreekDuel\ >nul
if not exist release mkdir release
powershell -NoProfile -Command "Compress-Archive -Force -Path 'build\dist\DryCreekDuel' -DestinationPath 'release\DryCreekDuel-windows.zip'"
if errorlevel 1 goto :fail

echo.
echo Done!  Upload this file to itch.io:  release\DryCreekDuel-windows.zip
echo Test it first: build\dist\DryCreekDuel\DryCreekDuel.exe
pause
exit /b 0

:fail
echo.
echo Something went wrong - read the messages above.
pause
exit /b 1
