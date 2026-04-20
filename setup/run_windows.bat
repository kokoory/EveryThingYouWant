@echo off
chcp 65001 > nul
setlocal

cd /d "%~dp0\.."

if not exist venv (
    echo [ERROR] Virtual environment not found.
    echo Please run setup\install_windows.bat first.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

echo ====================================================
echo   Requirements Graph Manager
echo   Server starting at http://localhost:8000
echo   Press Ctrl+C to stop
echo ====================================================
echo.

python run.py
