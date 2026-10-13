@echo off
setlocal
cd /d "%~dp0"
title Cannelloni SD Installer

REM Check for standalone compiled executable
if exist "Cannelloni-Installer.exe" (
    start "" "Cannelloni-Installer.exe"
    exit /b
)

REM Fallback to python
where python >nul 2>&1
if %ERRORLEVEL% equ 0 (
    python "%~dp0cannelloni_installer.py"
    exit /b
)

where py >nul 2>&1
if %ERRORLEVEL% equ 0 (
    py -3 "%~dp0cannelloni_installer.py"
    exit /b
)

echo Python is required to run the script version.
echo Please install Python 3 or use Cannelloni-Installer.exe.
pause
