#!/bin/bash

# Fix Story Sentinel service configuration

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Fixing Story Sentinel Service...${NC}"

# Stop the service if running
echo "Stopping service..."
systemctl stop story-sentinel || true

# Update the systemd service file
echo "Updating systemd service..."
cat > /etc/systemd/system/story-sentinel.service <<'EOF'
[Unit]
Description=Story Sentinel - Automated monitoring and upgrade system for Story Protocol nodes
Documentation=https://github.com/nodemasterpro/story-sentinel
After=network.target story-node.service geth-node.service
Wants=story-node.service geth-node.service

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/opt/story-sentinel
Environment=PATH=/opt/story-sentinel/venv/bin:/usr/local/bin:/usr/bin:/bin
Environment=PYTHONPATH=/opt/story-sentinel
EnvironmentFile=/etc/story-sentinel/.env
ExecStart=/opt/story-sentinel/venv/bin/python -m sentinel monitor
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=10

# Security settings
NoNewPrivileges=false
ProtectSystem=false
ProtectHome=false
PrivateTmp=true
PrivateDevices=false

# Resource limits
LimitNOFILE=65536
LimitNPROC=4096

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=story-sentinel

[Install]
WantedBy=multi-user.target
EOF

# Update the CLI wrapper
echo "Updating CLI wrapper..."
cat > /usr/local/bin/story-sentinel <<'EOF'
#!/bin/bash
# Story Sentinel CLI wrapper

cd "/opt/story-sentinel"
source venv/bin/activate
export STORY_SENTINEL_CONFIG="/etc/story-sentinel/config.yaml"
exec python -m sentinel "$@"
EOF

chmod +x /usr/local/bin/story-sentinel

# Reload systemd
echo "Reloading systemd..."
systemctl daemon-reload

# Start the API service separately
echo "Creating API service..."
cat > /etc/systemd/system/story-sentinel-api.service <<'EOF'
[Unit]
Description=Story Sentinel API Service
Documentation=https://github.com/nodemasterpro/story-sentinel
After=network.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/opt/story-sentinel
Environment=PATH=/opt/story-sentinel/venv/bin:/usr/local/bin:/usr/bin:/bin
Environment=PYTHONPATH=/opt/story-sentinel
EnvironmentFile=/etc/story-sentinel/.env
ExecStart=/opt/story-sentinel/venv/bin/python -m sentinel.api
Restart=always
RestartSec=10

# Security settings
NoNewPrivileges=false
ProtectSystem=false
ProtectHome=false
PrivateTmp=true
PrivateDevices=false

# Resource limits
LimitNOFILE=65536
LimitNPROC=4096

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=story-sentinel-api

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable story-sentinel-api

echo -e "${GREEN}✓${NC} Service configuration fixed"
echo
echo "Next steps:"
echo "1. Start the monitoring service: systemctl start story-sentinel"
echo "2. Start the API service: systemctl start story-sentinel-api"
echo "3. Check status: systemctl status story-sentinel story-sentinel-api"
echo "4. Check API: curl http://localhost:8080/health"