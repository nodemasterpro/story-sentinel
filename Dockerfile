FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    systemctl \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY sentinel/ ./sentinel/
COPY setup.py .

# Install the application
RUN pip install -e .

# Create data directory for persistent storage
RUN mkdir -p /data/logs /data/backups

# Set environment variables
ENV PYTHONPATH=/app
ENV SENTINEL_DATA_DIR=/data

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Expose API port
EXPOSE 8080

# Create entrypoint script
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
# Set data directory environment variables\n\
export SENTINEL_CONFIG_DIR=/data\n\
export SENTINEL_DATA_DIR=/data\n\
export BACKUP_DIR=/data/backups\n\
export LOG_DIR=/data/logs\n\
\n\
# Skip config.yaml generation - we use environment variables\n\
echo "Using environment-based configuration..."\n\
\n\
# Start API server in background\n\
python -m sentinel.api &\n\
API_PID=$!\n\
\n\
# Function to cleanup on exit\n\
cleanup() {\n\
    echo "Shutting down..."\n\
    kill $API_PID 2>/dev/null || true\n\
    exit 0\n\
}\n\
\n\
# Set up signal handlers\n\
trap cleanup SIGTERM SIGINT\n\
\n\
# Start monitoring (skip validation for Docker mode)\n\
echo "Starting Story Sentinel monitoring..."\n\
export DOCKER_MODE=1\n\
story-sentinel monitor &\n\
MONITOR_PID=$!\n\
\n\
# Wait for processes\n\
wait $MONITOR_PID\n\
' > /entrypoint.sh && chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]