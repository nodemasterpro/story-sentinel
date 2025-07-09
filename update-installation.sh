#!/bin/bash

# Update Story Sentinel installation with latest fixes

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Story Sentinel Update & Fix Script    ${NC}"
echo -e "${BLUE}========================================${NC}"
echo

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}This script must be run as root${NC}" 
   exit 1
fi

# Stop services
echo -e "${YELLOW}Stopping services...${NC}"
systemctl stop story-sentinel || true
systemctl stop story-sentinel-api || true

# Update Python code
echo -e "${YELLOW}Updating Python code...${NC}"
cd /opt/story-sentinel

# Download latest fixes
if [[ -d "sentinel" ]]; then
    echo "Updating from local source..."
    SOURCE_DIR="$(dirname "$(readlink -f "$0")")"
    cp -r "$SOURCE_DIR/sentinel" .
    cp "$SOURCE_DIR/setup.py" .
    cp "$SOURCE_DIR/requirements.txt" .
else
    echo "Downloading from GitHub..."
    wget -q https://github.com/nodemasterpro/story-sentinel/archive/main.zip
    unzip -q main.zip
    cp -r story-sentinel-main/sentinel .
    cp story-sentinel-main/setup.py .
    cp story-sentinel-main/requirements.txt .
    rm -rf story-sentinel-main main.zip
fi

# Reinstall in virtual environment
source venv/bin/activate
pip install -e . > /dev/null 2>&1
echo -e "${GREEN}✓${NC} Python code updated"

# Update systemd services
echo -e "${YELLOW}Updating systemd services...${NC}"

# Main monitoring service
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

# API service
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

# Update CLI wrapper
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
systemctl daemon-reload
systemctl enable story-sentinel story-sentinel-api

echo -e "${GREEN}✓${NC} Services updated"

# Verify configuration
echo -e "${YELLOW}Verifying configuration...${NC}"
if [[ -f /etc/story-sentinel/.env ]]; then
    source /etc/story-sentinel/.env
    
    # Check if binary paths exist
    if [[ ! -x "$STORY_BINARY_PATH" ]]; then
        echo -e "${YELLOW}⚠ Story binary not found at: $STORY_BINARY_PATH${NC}"
    else
        echo -e "${GREEN}✓${NC} Story binary found: $STORY_BINARY_PATH"
    fi
    
    if [[ ! -x "$STORY_GETH_BINARY_PATH" ]]; then
        echo -e "${YELLOW}⚠ Story-Geth binary not found at: $STORY_GETH_BINARY_PATH${NC}"
    else
        echo -e "${GREEN}✓${NC} Story-Geth binary found: $STORY_GETH_BINARY_PATH"
    fi
fi

# Start services
echo -e "${YELLOW}Starting services...${NC}"
systemctl start story-sentinel
systemctl start story-sentinel-api

# Wait for services to start
sleep 3

# Check status
echo -e "${YELLOW}Checking service status...${NC}"
if systemctl is-active --quiet story-sentinel; then
    echo -e "${GREEN}✓${NC} story-sentinel is running"
else
    echo -e "${RED}✗${NC} story-sentinel failed to start"
    echo "Check logs: journalctl -u story-sentinel -n 50"
fi

if systemctl is-active --quiet story-sentinel-api; then
    echo -e "${GREEN}✓${NC} story-sentinel-api is running"
else
    echo -e "${RED}✗${NC} story-sentinel-api failed to start"
    echo "Check logs: journalctl -u story-sentinel-api -n 50"
fi

# Test API
echo -e "${YELLOW}Testing API...${NC}"
if curl -s http://localhost:8080/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} API is responding"
    echo
    echo "API endpoints available:"
    echo "  http://localhost:8080/health  - Health status"
    echo "  http://localhost:8080/status  - Detailed node status"
    echo "  http://localhost:8080/metrics - Prometheus metrics"
else
    echo -e "${YELLOW}⚠${NC} API not responding yet (may still be starting)"
fi

echo
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Update Complete!                      ${NC}"
echo -e "${GREEN}========================================${NC}"
echo
echo "Next steps:"
echo "1. Check service logs: journalctl -u story-sentinel -f"
echo "2. Check API logs: journalctl -u story-sentinel-api -f"
echo "3. Test CLI: story-sentinel status"
echo "4. View API: curl http://localhost:8080/health"