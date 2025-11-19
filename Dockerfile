# Greenhouse Control System - Docker Container
# Multi-stage build for optimized image size

# Stage 1: Base image with dependencies
FROM python:3.9-slim as base

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    libusb-1.0-0 \
    udev \
    && rm -rf /var/lib/apt/lists/*

# Stage 2: Dependencies installation
FROM base as dependencies

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Stage 3: Final application image
FROM dependencies as application

# Copy application code
COPY python/ /app/python/
COPY arduino/ /app/arduino/
COPY docs/ /app/docs/
COPY simulation_config.yaml /app/
COPY config.ini /app/
COPY README.md /app/
COPY claude.md /app/

# Create data directories
RUN mkdir -p /app/data/logs

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Expose Streamlit port
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Add curl for healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Set permissions
RUN chmod +x /app/python/ui/app.py || true

# Default command - run Streamlit dashboard
CMD ["streamlit", "run", "/app/python/ui/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
