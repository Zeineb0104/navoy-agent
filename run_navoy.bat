@echo off
title Navoy - Setup and Run

echo ================================================
echo   Navoy Travel Recommendation System
echo   Checking Python installation...
echo ================================================
echo.

REM Check if python is properly installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo.
    echo Please install Python first:
    echo   1. Go to: https://www.python.org/downloads/
    echo   2. Download Python 3.12 (Windows installer)
    echo   3. Run the installer
    echo   4  CHECK "Add Python to PATH" on the first screen!
    echo   5. Then double-click this file again.
    echo.
    pause
    exit /b 1
)

echo [OK] Python found:
python --version
echo.

REM Change to the script's directory
cd /d "%~dp0"
echo [INFO] Working directory: %cd%
echo.

REM Check if streamlit is already installed
streamlit --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Installing dependencies (this takes 1-2 minutes)...
    echo.
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo.
        echo [ERROR] Failed to install dependencies.
        echo Try running manually: pip install -r requirements.txt
        pause
        exit /b 1
    )
    echo.
    echo [OK] Dependencies installed successfully!
) else (
    echo [OK] Dependencies already installed.
)

echo.
echo ================================================
echo   Launching Navoy at http://localhost:8501
echo   Press Ctrl+C in this window to stop the app.
echo ================================================
echo.

streamlit run app.py --server.headless false --browser.gatherUsageStats false
pause
