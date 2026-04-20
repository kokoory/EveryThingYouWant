@echo off
chcp 65001 > nul
setlocal

echo ====================================================
echo   Requirements Graph Manager - Windows Setup
echo   (Python 3.12)
echo ====================================================
echo.

REM Check Python
python --version 2>nul
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.12 from https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Check Python version is 3.12
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo Detected Python: %PYVER%
echo %PYVER% | findstr /B "3.12" > nul
if errorlevel 1 (
    echo [WARNING] Python 3.12 is recommended. Current: %PYVER%
    echo Continue anyway? (Y/N)
    set /p CONT=
    if /i not "%CONT%"=="Y" exit /b 1
)

REM Move to project root
cd /d "%~dp0\.."

REM Create virtual environment
if not exist venv (
    echo.
    echo [1/3] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
) else (
    echo [1/3] Virtual environment already exists. Skipping.
)

REM Activate venv
echo.
echo [2/3] Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo.
echo [3/3] Installing dependencies...

REM Try offline first using bundled wheels
if exist setup\wheels\windows (
    echo Using offline wheel cache...
    python -m pip install --no-index --find-links=setup\wheels\windows -r setup\requirements.txt
    if errorlevel 1 (
        echo [WARNING] Offline install failed, trying online...
        python -m pip install --upgrade pip
        python -m pip install -r setup\requirements.txt
    )
) else (
    python -m pip install --upgrade pip
    python -m pip install -r setup\requirements.txt
)

if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
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
