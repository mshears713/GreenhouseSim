#!/bin/bash
# Greenhouse Control System - Linux/WSL/macOS Startup Script
# This script launches the Streamlit dashboard

set -e  # Exit on error

echo "========================================"
echo " Greenhouse Control System"
echo " Starting Dashboard..."
echo "========================================"
echo

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.8+ using your package manager:"
    echo "  Ubuntu/Debian: sudo apt install python3 python3-pip python3-venv"
    echo "  Fedora/RHEL:   sudo dnf install python3 python3-pip"
    echo "  Arch:          sudo pacman -S python python-pip"
    echo "  macOS:         brew install python3"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Check if requirements are installed
if ! python -c "import streamlit" &> /dev/null; then
    echo "Installing dependencies (this may take a few minutes)..."
    python -m pip install --upgrade pip
    pip install -r requirements.txt
fi

# Check for Arduino
echo
echo "Checking for Arduino connection..."
python -c "
from python.communication.serial_interface import ArduinoInterface
ports = ArduinoInterface.list_available_ports()
if ports:
    print('Available serial ports:')
    for p in ports:
        print(f'  - {p}')
else:
    print('No serial ports detected')
    print('Running in simulation-only mode')
"

# Check if running in WSL
if grep -qi microsoft /proc/version 2>/dev/null; then
    echo
    echo "WSL detected! Dashboard will be accessible from Windows browser"
fi

echo
echo "========================================"
echo " Dashboard will open at:"
echo " http://localhost:8501"
echo
echo " Press Ctrl+C to stop the server"
echo "========================================"
echo

# Start Streamlit
streamlit run python/ui/app.py --server.port=8501 --server.address=0.0.0.0
