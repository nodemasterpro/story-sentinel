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
# Create config if not exists\n\
if [ ! -f /data/config.yaml ]; then\n\
    echo "Initializing configuration..."\n\
    story-sentinel --data-dir /data init\n\
fi\n\
\n\
# Start API server in background\n\
story-sentinel --data-dir /data api &\n\
\n\
# Start monitoring\n\
exec story-sentinel --data-dir /data monitor\n\
' > /entrypoint.sh && chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]