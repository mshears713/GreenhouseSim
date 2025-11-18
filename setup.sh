#!/bin/bash
# Setup script for Smart Mini Greenhouse Control System
# This script sets up the Python virtual environment and installs dependencies

echo "========================================"
echo "Greenhouse Control System - Setup"
echo "========================================"
echo ""

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed!"
    echo "Please install Python 3.8 or newer and try again."
    exit 1
fi

echo "Python 3 found: $(python3 --version)"
echo ""

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "ERROR: Virtual environment creation failed!"
    exit 1
fi

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo ""
echo "Installing dependencies from requirements.txt..."
pip install -r requirements.txt

# Create necessary directories
echo ""
echo "Creating data directories..."
mkdir -p data/logs
mkdir -p arduino/tests

# Set permissions for serial port (Linux only)
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo ""
    echo "Note: On Linux, you may need to add your user to the 'dialout' group"
    echo "to access the Arduino serial port. Run:"
    echo "  sudo usermod -a -G dialout $USER"
    echo "Then log out and log back in."
fi

echo ""
echo "========================================"
echo "Setup complete!"
echo "========================================"
echo ""
echo "To activate the virtual environment:"
echo "  source venv/bin/activate  (Linux/macOS)"
echo "  venv\\Scripts\\activate     (Windows)"
echo ""
echo "To run the Streamlit UI:"
echo "  streamlit run python/app.py"
echo ""
echo "To run tests:"
echo "  pytest python/tests/"
echo ""
