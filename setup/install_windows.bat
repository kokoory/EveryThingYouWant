@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

echo ====================================================
echo   Requirements Graph Manager - Windows Setup
echo   REQUIRES Python 3.12
echo ====================================================
echo.

REM ── Find Python 3.12 ──

REM Try 'py -3.12' launcher first (recommended Windows Python launcher)
set PYCMD=
py -3.12 --version >nul 2>&1
if not errorlevel 1 (
    set PYCMD=py -3.12
    goto :pyfound
)

REM Try 'python' and check version
python --version >nul 2>&1
if not errorlevel 1 (
    for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
    echo !PYVER! | findstr "3.12" >nul
    if not errorlevel 1 (
        set PYCMD=python
        goto :pyfound
    )
)

REM Try 'python3.12'
python3.12 --version >nul 2>&1
if not errorlevel 1 (
    set PYCMD=python3.12
    goto :pyfound
)

REM Not found
echo [ERROR] Python 3.12 was not found.
echo.
echo Please install Python 3.12 from:
echo   https://www.python.org/downloads/release/python-3127/
echo.
echo During installation, make sure to check:
echo   [x] Add python.exe to PATH
echo.
pause
exit /b 1

:pyfound
for /f "tokens=*" %%v in ('%PYCMD% --version 2^>^&1') do echo Detected: %%v

REM ── Move to project root ──
cd /d "%~dp0\.."

REM ── Create virtual environment ──
if not exist venv (
    echo.
    echo [1/3] Creating virtual environment...
    %PYCMD% -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
) else (
    echo [1/3] Virtual environment already exists. Skipping.
)

REM ── Activate ──
echo.
echo [2/3] Activating virtual environment...
call venv\Scripts\activate.bat

REM ── Install from offline wheels ──
echo.
echo [3/3] Installing dependencies...

if exist setup\wheels\windows (
    echo Using offline wheel cache...
    python -m pip install --no-index --find-links=setup\wheels\windows -r setup\requirements.txt
    if errorlevel 1 (
        echo.
        echo [ERROR] Offline install failed.
        echo Please check that Python 3.12 is being used.
        echo Bundled wheels are for Python 3.12 only.
        pause
        exit /b 1
    )
) else (
    echo No offline wheels found, installing from internet...
    python -m pip install -r setup\requirements.txt
    if errorlevel 1 (
        echo [ERROR] Online install failed.
        pause
        exit /b 1
    )
)

echo.
echo ====================================================
echo   Installation complete!
echo ====================================================
echo.
echo To start the server, run:  setup\run_windows.bat
echo Then open browser at:      http://localhost:8000
echo.
pause
