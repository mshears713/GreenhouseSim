@echo off
REM Greenhouse Control System - Windows Startup Script
REM This script launches the Streamlit dashboard on Windows

echo ========================================
echo  Greenhouse Control System
echo  Starting Dashboard...
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Check if requirements are installed
python -c "import streamlit" >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies (this may take a few minutes)...
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies
        pause
        exit /b 1
    )
)

REM Check for Arduino
echo.
echo Checking for Arduino connection...
python -c "from python.communication.serial_interface import ArduinoInterface; ports = ArduinoInterface.list_available_ports(); print('Available serial ports:') if ports else print('No serial ports detected'); [print(f'  - {p}') for p in ports]"

echo.
echo ========================================
echo  Dashboard will open at:
echo  http://localhost:8501
echo.
echo  Press Ctrl+C to stop the server
echo ========================================
echo.

REM Start Streamlit
streamlit run python/ui/app.py --server.port=8501

pause
