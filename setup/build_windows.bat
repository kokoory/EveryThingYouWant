@echo off
chcp 65001 > nul
setlocal

echo ====================================================
echo   Requirements Graph Manager - Portable Build
echo   (Windows x64)
echo ====================================================
echo.

cd /d "%~dp0\.."

REM Check venv
if not exist venv (
    echo [ERROR] Run setup\install_windows.bat first.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

REM Install PyInstaller
echo [1/3] Installing PyInstaller...
pip install pyinstaller
if errorlevel 1 (
    echo [ERROR] Failed to install PyInstaller.
    pause
    exit /b 1
)

REM Clean previous build
echo.
echo [2/3] Cleaning previous build...
if exist dist\RequirementsGraphManager rmdir /s /q dist\RequirementsGraphManager
if exist build rmdir /s /q build

REM Build
echo.
echo [3/3] Building portable executable...
pyinstaller build_portable.spec --noconfirm
if errorlevel 1 (
    echo [ERROR] Build failed.
    pause
    exit /b 1
)

REM Create launch script in dist folder
echo @echo off > dist\RequirementsGraphManager\Start.bat
echo chcp 65001 ^> nul >> dist\RequirementsGraphManager\Start.bat
echo cd /d "%%~dp0" >> dist\RequirementsGraphManager\Start.bat
echo RequirementsGraphManager.exe >> dist\RequirementsGraphManager\Start.bat
echo pause >> dist\RequirementsGraphManager\Start.bat

echo.
echo ====================================================
echo   Build complete!
echo ====================================================
echo.
echo   Output folder: dist\RequirementsGraphManager\
echo   Run:           dist\RequirementsGraphManager\Start.bat
echo.
echo   You can copy the entire folder to any Windows PC
echo   and run Start.bat without installing Python!
echo.
pause
