# Greenhouse Control System - Deployment Guide

## Table of Contents

1. [Quick Start](#quick-start)
2. [Docker Deployment](#docker-deployment)
3. [Windows Deployment](#windows-deployment)
4. [WSL Deployment](#wsl-deployment)
5. [Linux Deployment](#linux-deployment)
6. [Arduino USB Configuration](#arduino-usb-configuration)
7. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Option 1: Docker (Recommended)

```bash
# Clone repository
git clone https://github.com/yourusername/GreenhouseSim.git
cd GreenhouseSim

# Build and run with docker-compose
docker-compose up -d

# Access UI at http://localhost:8501
```

### Option 2: Python (Direct)

```bash
# Install dependencies
pip install -r requirements.txt

# Run dashboard
streamlit run python/ui/app.py
```

---

## Docker Deployment

### Prerequisites

- **Docker Desktop** (Windows/Mac) or **Docker Engine** (Linux)
- **Docker Compose** v2.0+
- **4GB RAM** minimum
- **10GB disk space**

### Installation Steps

#### 1. Install Docker

**Windows:**
```powershell
# Download Docker Desktop from https://www.docker.com/products/docker-desktop
# Run installer and restart computer
# Open Docker Desktop and wait for it to start
```

**WSL 2:**
```bash
# Install Docker in WSL
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

**Linux:**
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

#### 2. Build the Container

```bash
# Navigate to project directory
cd GreenhouseSim

# Build Docker image
docker-compose build

# Or build directly with Docker
docker build -t greenhouse-control .
```

#### 3. Run the Application

```bash
# Start container in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop container
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

#### 4. Access the Dashboard

Open your browser and navigate to:
```
http://localhost:8501
```

### Docker Commands Reference

```bash
# View running containers
docker ps

# View all containers
docker ps -a

# Stop container
docker stop greenhouse-control

# Start container
docker start greenhouse-control

# Restart container
docker restart greenhouse-control

# View logs
docker logs greenhouse-control

# Follow logs in real-time
docker logs -f greenhouse-control

# Execute command in container
docker exec -it greenhouse-control bash

# Remove container
docker rm greenhouse-control

# Remove image
docker rmi greenhouse-control
```

---

## Windows Deployment

### Native Python Installation

#### Prerequisites

- **Windows 10/11**
- **Python 3.8+** from [python.org](https://www.python.org/downloads/)
- **Git for Windows** (optional)

#### Installation Steps

1. **Install Python:**
   ```powershell
   # Download from https://www.python.org/downloads/
   # During installation, check "Add Python to PATH"
   # Verify installation
   python --version
   pip --version
   ```

2. **Clone Repository:**
   ```powershell
   # Using Git
   git clone https://github.com/yourusername/GreenhouseSim.git
   cd GreenhouseSim

   # Or download ZIP from GitHub and extract
   ```

3. **Create Virtual Environment:**
   ```powershell
   # Create venv
   python -m venv venv

   # Activate venv
   .\venv\Scripts\activate

   # Verify activation (should show (venv) in prompt)
   ```

4. **Install Dependencies:**
   ```powershell
   # Upgrade pip
   python -m pip install --upgrade pip

   # Install requirements
   pip install -r requirements.txt
   ```

5. **Configure Serial Port:**
   ```powershell
   # Find Arduino COM port in Device Manager
   # Update config.ini with correct port (e.g., COM3)
   notepad config.ini
   ```

6. **Run Application:**
   ```powershell
   # Start Streamlit dashboard
   streamlit run python/ui/app.py

   # Or use startup script
   .\run.bat
   ```

### Windows Startup Script

Create `run.bat` in project root:

```batch
@echo off
echo Starting Greenhouse Control System...
echo.

REM Activate virtual environment
call venv\Scripts\activate

REM Check if Arduino is connected
echo Checking for Arduino...
python -c "from python.communication.serial_interface import ArduinoInterface; print('Available ports:'); [print(f'  - {p}') for p in ArduinoInterface.list_available_ports()]"
echo.

REM Start Streamlit
echo Launching dashboard at http://localhost:8501
echo Press Ctrl+C to stop
echo.
streamlit run python/ui/app.py

pause
```

Make executable:
```powershell
# No additional steps needed for .bat files
```

---

## WSL Deployment

### Prerequisites

- **Windows 10/11** with WSL 2 enabled
- **Ubuntu 20.04/22.04** (or other Linux distro) in WSL

### Installation Steps

#### 1. Install WSL 2

```powershell
# In PowerShell (Administrator)
wsl --install

# Restart computer
```

#### 2. Set Up Linux Environment

```bash
# In WSL terminal
# Update packages
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
sudo apt install -y python3 python3-pip python3-venv git

# Install USB/IP tools for USB passthrough (optional)
sudo apt install -y linux-tools-virtual hwdata
sudo update-alternatives --install /usr/local/bin/usbip usbip /usr/lib/linux-tools/*/usbip 20
```

#### 3. Clone and Setup Project

```bash
# Clone repository
git clone https://github.com/yourusername/GreenhouseSim.git
cd GreenhouseSim

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### 4. USB Device Access (For Arduino)

**Method 1: USB/IP (Recommended for WSL)**

On Windows (PowerShell as Administrator):
```powershell
# Install usbipd-win
winget install --interactive --exact dorssel.usbipd-win

# List USB devices
usbipd wsl list

# Attach Arduino to WSL (replace BUSID with your device)
usbipd wsl attach --busid 1-4

# Verify in WSL
wsl
lsusb
```

On WSL:
```bash
# Check device
ls -l /dev/ttyACM* /dev/ttyUSB*

# Add user to dialout group for serial access
sudo usermod -aG dialout $USER

# Restart WSL for group changes to take effect
```

**Method 2: Docker with Device Mapping**

```bash
# In WSL, run with device mapping
docker-compose up -d

# Or with explicit device
docker run -d \
  --device=/dev/ttyACM0 \
  -p 8501:8501 \
  greenhouse-control
```

#### 5. Run Application

```bash
# Activate venv
source venv/bin/activate

# Run Streamlit
streamlit run python/ui/app.py
```

#### 6. Access from Windows Browser

```
http://localhost:8501
```

### WSL Startup Script

Create `run-wsl.sh`:

```bash
#!/bin/bash
echo "Starting Greenhouse Control System in WSL..."
echo

# Activate virtual environment
source venv/bin/activate

# Check Arduino connection
echo "Checking for Arduino..."
python -c "from python.communication.serial_interface import ArduinoInterface; ports = ArduinoInterface.list_available_ports(); print('Available ports:'); [print(f'  - {p}') for p in ports] if ports else print('  No serial ports found')"
echo

# Set display for GUI (if needed)
export DISPLAY=:0

# Start Streamlit
echo "Launching dashboard at http://localhost:8501"
echo "Press Ctrl+C to stop"
echo
streamlit run python/ui/app.py --server.port=8501 --server.address=0.0.0.0
```

Make executable:
```bash
chmod +x run-wsl.sh
./run-wsl.sh
```

---

## Linux Deployment

### Ubuntu/Debian

```bash
# Install dependencies
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git

# Clone repository
git clone https://github.com/yourusername/GreenhouseSim.git
cd GreenhouseSim

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python packages
pip install -r requirements.txt

# Add user to dialout group for serial access
sudo usermod -aG dialout $USER

# Log out and back in for group changes to take effect
# Or use: newgrp dialout

# Run application
streamlit run python/ui/app.py
```

### Arch Linux

```bash
# Install dependencies
sudo pacman -S python python-pip git

# Continue with same steps as Ubuntu
```

### Fedora/RHEL

```bash
# Install dependencies
sudo dnf install python3 python3-pip git

# Continue with same steps as Ubuntu
```

---

## Arduino USB Configuration

### Finding the Arduino Port

**Windows:**
1. Open Device Manager (Win+X → Device Manager)
2. Expand "Ports (COM & LPT)"
3. Look for "Arduino" or "USB Serial Device"
4. Note the COM port (e.g., COM3)

**Linux/WSL:**
```bash
# List serial devices
ls -l /dev/ttyACM* /dev/ttyUSB*

# Or with detailed info
dmesg | grep tty

# Or using Python
python3 -c "from python.communication.serial_interface import ArduinoInterface; [print(p) for p in ArduinoInterface.list_available_ports()]"
```

**macOS:**
```bash
ls -l /dev/cu.* /dev/tty.*
```

### Configuring the Port

Edit `config.ini`:

```ini
[Arduino]
# Windows
port = COM3

# Linux/WSL
# port = /dev/ttyACM0

# macOS
# port = /dev/cu.usbmodem14101

baud_rate = 9600
timeout = 2.0
```

### Docker USB Access

#### Linux

Edit `docker-compose.yml`:

```yaml
services:
  greenhouse:
    devices:
      - /dev/ttyACM0:/dev/ttyACM0  # Add your Arduino port
```

#### Windows (WSL 2 Backend)

1. Attach USB device to WSL (see WSL section)
2. Modify `docker-compose.yml` with device mapping
3. Run `docker-compose up`

#### Windows (Hyper-V Backend)

USB passthrough is limited. Options:
1. Use native Python installation (not Docker)
2. Use simulation mode without Arduino
3. Use USB over network solutions

### Permissions (Linux/WSL)

```bash
# Add user to dialout group
sudo usermod -aG dialout $USER

# Apply changes (choose one)
newgrp dialout           # Temporary for current session
# OR
# Log out and log back in  # Permanent

# Verify group membership
groups | grep dialout

# Check device permissions
ls -l /dev/ttyACM0

# If still no access, temporarily change permissions (NOT recommended for production)
sudo chmod 666 /dev/ttyACM0
```

---

## Troubleshooting

### Container Won't Start

**Issue:** `docker-compose up` fails

**Solutions:**
```bash
# Check Docker is running
docker ps

# View logs
docker-compose logs

# Rebuild image
docker-compose build --no-cache
docker-compose up
```

### Port 8501 Already in Use

**Issue:** "Port 8501 is already allocated"

**Solutions:**
```bash
# Find process using port
# Windows
netstat -ano | findstr :8501

# Linux
lsof -i :8501

# Kill process or change port in docker-compose.yml
ports:
  - "8502:8501"  # Use different external port
```

### Arduino Not Detected

**Issue:** "No serial ports found"

**Solutions:**

1. **Check USB Connection:**
   - Unplug and replug Arduino
   - Try different USB cable
   - Try different USB port

2. **Check Permissions (Linux):**
   ```bash
   sudo usermod -aG dialout $USER
   newgrp dialout
   ```

3. **Check Device Manager (Windows):**
   - Look for "Unknown Device"
   - Install Arduino drivers if needed

4. **Check Docker Device Mapping:**
   ```bash
   # Verify device exists
   ls -l /dev/ttyACM0

   # Update docker-compose.yml
   ```

### Slow Performance

**Issue:** UI is laggy or unresponsive

**Solutions:**

1. **Check Resource Usage:**
   ```bash
   docker stats greenhouse-control
   ```

2. **Increase Resource Limits:**
   Edit `docker-compose.yml`:
   ```yaml
   deploy:
     resources:
       limits:
         cpus: '4.0'      # Increase CPUs
         memory: 4G       # Increase memory
   ```

3. **Optimize Simulation:**
   Edit `simulation_config.yaml`:
   ```yaml
   simulation:
     target_update_rate: 5.0  # Reduce from 10.0
   ```

### WSL USB Issues

**Issue:** Arduino not accessible in WSL

**Solutions:**

1. **Install usbipd:**
   ```powershell
   # Windows (PowerShell as Admin)
   winget install --interactive --exact dorssel.usbipd-win
   ```

2. **Attach Device:**
   ```powershell
   # List devices
   usbipd wsl list

   # Attach (replace BUSID)
   usbipd wsl attach --busid 1-4
   ```

3. **Verify in WSL:**
   ```bash
   lsusb
   ls -l /dev/ttyACM*
   ```

### Browser Can't Access UI

**Issue:** http://localhost:8501 doesn't load

**Solutions:**

1. **Check Container Status:**
   ```bash
   docker ps
   docker logs greenhouse-control
   ```

2. **Check Firewall:**
   - Windows: Allow port 8501 in Windows Firewall
   - Linux: Check ufw or iptables rules

3. **Try Different Address:**
   ```
   http://127.0.0.1:8501
   http://[your-ip]:8501
   ```

4. **Check Port Mapping:**
   ```bash
   docker port greenhouse-control
   ```

### Data Not Persisting

**Issue:** Logs disappear after restart

**Solutions:**

1. **Check Volume Mounts:**
   ```bash
   docker inspect greenhouse-control | grep Mounts -A 20
   ```

2. **Verify Volumes:**
   ```bash
   docker volume ls
   docker volume inspect greenhouse-logs
   ```

3. **Use Bind Mounts:**
   Edit `docker-compose.yml`:
   ```yaml
   volumes:
     - ./data:/app/data  # Use local directory
   ```

---

## Environment Variables

### Supported Variables

```bash
# Streamlit Configuration
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=0.0.0.0
STREAMLIT_SERVER_HEADLESS=true
STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Python Configuration
PYTHONUNBUFFERED=1

# Application Configuration
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
```

### Setting Variables

**Docker Compose:**
```yaml
environment:
  - LOG_LEVEL=DEBUG
```

**Docker Run:**
```bash
docker run -e LOG_LEVEL=DEBUG greenhouse-control
```

**Native Python:**
```bash
# Linux/WSL
export LOG_LEVEL=DEBUG
streamlit run python/ui/app.py

# Windows PowerShell
$env:LOG_LEVEL="DEBUG"
streamlit run python/ui/app.py
```

---

## Production Deployment

### Security Considerations

1. **Remove Privileged Mode:**
   - Use device mapping instead of `privileged: true`
   - Limit container capabilities

2. **Use Environment Files:**
   ```bash
   # Create .env file
   echo "ARDUINO_PORT=/dev/ttyACM0" > .env

   # Reference in docker-compose.yml
   env_file:
     - .env
   ```

3. **Enable TLS:**
   ```yaml
   environment:
     - STREAMLIT_SERVER_ENABLE_CORS=false
     - STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=true
   ```

4. **Network Isolation:**
   ```yaml
   networks:
     greenhouse-net:
       driver: bridge
       internal: true  # No external access
   ```

### Monitoring

```bash
# View container stats
docker stats greenhouse-control

# Export logs
docker logs greenhouse-control > app.log 2>&1

# Set up log rotation
# Add to docker-compose.yml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

---

## Next Steps

- [Hardware Setup Guide](HARDWARE_GUIDE.md)
- [Testing Guide](TESTING_GUIDE.md)
- [API Reference](../README.md)
- [Troubleshooting](TROUBLESHOOTING.md)

---

**Last Updated:** 2025-01-19
**Version:** 1.0.0
