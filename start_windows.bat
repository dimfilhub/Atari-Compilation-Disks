@echo off
setlocal
cd /d "%~dp0"

rem 1. Python
set "PY="
py -3 -c "import sys" >nul 2>&1 && set "PY=py -3"
if not defined PY (
    python -c "import sys" >nul 2>&1 && set "PY=python"
)
if not defined PY (
    echo Python was not found. Trying to install it with winget...
    winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements
    echo.
    echo If the installation succeeded, close this window and run start_windows.bat again.
    echo Otherwise install Python from https://www.python.org/downloads/ ^(tick "Add python.exe to PATH"^).
    pause
    exit /b 1
)

rem 2. Virtual environment
if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    %PY% -m venv .venv || goto :fail
)

rem 3. Requirements (only when requirements.txt changed since last install)
set "STAMP=.venv\requirements.installed"
fc /b requirements.txt "%STAMP%" >nul 2>&1
if errorlevel 1 (
    echo Installing requirements...
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt || goto :fail
    copy /y requirements.txt "%STAMP%" >nul
)

rem 4. Start the app
start "" ".venv\Scripts\pythonw.exe" comp_disks_player.py
exit /b 0

:fail
echo.
echo Setup failed. See the messages above.
pause
exit /b 1
