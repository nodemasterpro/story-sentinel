#!/bin/bash

# Story Sentinel - Native Installation Script
# This script installs Story Sentinel directly on your Story Protocol server

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="/opt/story-sentinel"
CONFIG_DIR="/etc/story-sentinel"
SERVICE_USER="root"
SERVICE_NAME="story-sentinel"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Story Sentinel Native Installation    ${NC}"
echo -e "${BLUE}========================================${NC}"
echo

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}This script must be run as root${NC}" 
   exit 1
fi

# Detect OS
if [[ -f /etc/os-release ]]; then
    . /etc/os-release
    OS=$NAME
    VER=$VERSION_ID
else
    echo -e "${RED}Cannot detect OS. This script supports Ubuntu/Debian.${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} Detected OS: $OS $VER"

# Install system dependencies
echo -e "${YELLOW}Installing system dependencies...${NC}"
apt-get update -qq
apt-get install -y python3 python3-pip python3-venv git curl wget systemctl sqlite3 > /dev/null 2>&1
echo -e "${GREEN}✓${NC} System dependencies installed"

# Detect Story Protocol installation
echo -e "${YELLOW}Detecting Story Protocol installation...${NC}"

STORY_BINARY=""
STORY_GETH_BINARY=""
STORY_SERVICE=""
STORY_GETH_SERVICE=""
STORY_HOME=""

# Find Story binary
for path in "/usr/local/bin/story" "/root/go/bin/story" "/home/*/go/bin/story" "$(which story 2>/dev/null)"; do
    if [[ -x "$path" ]]; then
        STORY_BINARY="$path"
        echo -e "${GREEN}✓${NC} Found Story binary: $STORY_BINARY"
        break
    fi
done

# Find Story-Geth binary  
for path in "/usr/local/bin/story-geth" "/usr/local/bin/geth" "/root/go/bin/geth" "/home/*/go/bin/geth" "$(which geth 2>/dev/null)"; do
    if [[ -x "$path" ]]; then
        STORY_GETH_BINARY="$path"
        echo -e "${GREEN}✓${NC} Found Story-Geth binary: $STORY_GETH_BINARY"
        break
    fi
done

# Find Story services
for service in "story" "story-node" "story-testnet"; do
    if systemctl list-units --all --type=service | grep -q "$service.service"; then
        STORY_SERVICE="$service"
        echo -e "${GREEN}✓${NC} Found Story service: $STORY_SERVICE"
        break
    fi
done

for service in "story-geth" "geth" "geth-node"; do
    if systemctl list-units --all --type=service | grep -q "$service.service"; then
        STORY_GETH_SERVICE="$service"
        echo -e "${GREEN}✓${NC} Found Story-Geth service: $STORY_GETH_SERVICE"
        break
    fi
done

# Find Story home directory
for path in "/root/.story" "/home/*/.story"; do
    if [[ -d "$path" ]]; then
        STORY_HOME="$path"
        echo -e "${GREEN}✓${NC} Found Story home: $STORY_HOME"
        break
    fi
done

# Verify critical components
if [[ -z "$STORY_BINARY" ]] || [[ -z "$STORY_GETH_BINARY" ]] || [[ -z "$STORY_SERVICE" ]] || [[ -z "$STORY_GETH_SERVICE" ]]; then
    echo -e "${RED}❌ Could not detect complete Story Protocol installation${NC}"
    echo "Please ensure Story Protocol is properly installed and running."
    echo "Found:"
    echo "  Story binary: ${STORY_BINARY:-'Not found'}"
    echo "  Story-Geth binary: ${STORY_GETH_BINARY:-'Not found'}"
    echo "  Story service: ${STORY_SERVICE:-'Not found'}"  
    echo "  Story-Geth service: ${STORY_GETH_SERVICE:-'Not found'}"
    exit 1
fi

# Detect RPC ports
echo -e "${YELLOW}Detecting RPC ports...${NC}"
STORY_RPC_PORT=""
STORY_GETH_RPC_PORT=""

# Check common Story RPC ports
for port in 26657 22657; do
    if netstat -tlnp 2>/dev/null | grep -q ":$port " || ss -tlnp 2>/dev/null | grep -q ":$port "; then
        STORY_RPC_PORT="$port"
        echo -e "${GREEN}✓${NC} Found Story RPC on port: $STORY_RPC_PORT"
        break
    fi
done

# Check common Geth RPC ports  
for port in 8545 2245; do
    if netstat -tlnp 2>/dev/null | grep -q ":$port " || ss -tlnp 2>/dev/null | grep -q ":$port "; then
        STORY_GETH_RPC_PORT="$port"
        echo -e "${GREEN}✓${NC} Found Story-Geth RPC on port: $STORY_GETH_RPC_PORT"
        break
    fi
done

# Default ports if not detected
STORY_RPC_PORT="${STORY_RPC_PORT:-26657}"
STORY_GETH_RPC_PORT="${STORY_GETH_RPC_PORT:-8545}"
STORY_HOME="${STORY_HOME:-/root/.story}"

echo -e "${GREEN}✓${NC} Configuration detected:"
echo "  Story RPC: http://localhost:$STORY_RPC_PORT"
echo "  Story-Geth RPC: http://localhost:$STORY_GETH_RPC_PORT"
echo "  Story Home: $STORY_HOME"

# Create installation directory
echo -e "${YELLOW}Creating installation directories...${NC}"
mkdir -p "$INSTALL_DIR"
mkdir -p "$CONFIG_DIR"
mkdir -p "/var/log/story-sentinel"
echo -e "${GREEN}✓${NC} Directories created"

# Install Python application
echo -e "${YELLOW}Installing Story Sentinel application...${NC}"
cd "$INSTALL_DIR"

# Copy source files (assuming we're running from the source directory)
if [[ -f "$(dirname "$0")/sentinel/__init__.py" ]]; then
    cp -r "$(dirname "$0")"/sentinel .
    cp "$(dirname "$0")/setup.py" .
    cp "$(dirname "$0")/requirements.txt" .
    echo -e "${GREEN}✓${NC} Source files copied"
else
    # Download from GitHub if not running from source
    echo -e "${YELLOW}Downloading from GitHub...${NC}"
    git clone https://github.com/nodemasterpro/story-sentinel.git temp_download
    cp -r temp_download/sentinel .
    cp temp_download/setup.py .
    cp temp_download/requirements.txt .
    rm -rf temp_download
    echo -e "${GREEN}✓${NC} Source downloaded from GitHub"
fi

# Create virtual environment
echo -e "${YELLOW}Setting up Python environment...${NC}"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt > /dev/null 2>&1
pip install -e . > /dev/null 2>&1
echo -e "${GREEN}✓${NC} Python environment ready"

# Generate configuration file
echo -e "${YELLOW}Generating configuration...${NC}"
cat > "$CONFIG_DIR/config.yaml" <<EOF
# Story Sentinel Configuration
# Auto-generated on $(date)

story:
  binary_path: "$STORY_BINARY"
  service_name: "$STORY_SERVICE"
  rpc_port: $STORY_RPC_PORT
  github_repo: "piplabs/story"

story_geth:
  binary_path: "$STORY_GETH_BINARY"
  service_name: "$STORY_GETH_SERVICE"
  rpc_port: $STORY_GETH_RPC_PORT
  github_repo: "piplabs/story-geth"

thresholds:
  height_gap: 20
  min_peers: 5
  block_time_variance: 10
  memory_limit_gb: 8.0
  disk_space_min_gb: 10.0
EOF

# Generate environment file template
cat > "$CONFIG_DIR/.env" <<EOF
# Story Sentinel Environment Configuration
# Auto-generated on $(date)

# Operation mode: 'manual' or 'auto' for automatic patch updates
MODE=manual

# Logging level
LOG_LEVEL=INFO

# Monitoring intervals (seconds)
CHECK_INTERVAL=300
UPDATE_CHECK_INTERVAL=3600

# API Configuration
API_HOST=0.0.0.0
API_PORT=8080

# Story Node Configuration (auto-detected, modify if needed)
STORY_BINARY_PATH=$STORY_BINARY
STORY_SERVICE_NAME=$STORY_SERVICE
STORY_RPC_PORT=$STORY_RPC_PORT

# Story-Geth Configuration (auto-detected, modify if needed) 
STORY_GETH_BINARY_PATH=$STORY_GETH_BINARY
STORY_GETH_SERVICE_NAME=$STORY_GETH_SERVICE
STORY_GETH_RPC_PORT=$STORY_GETH_RPC_PORT

# Paths (auto-detected)
STORY_HOME=$STORY_HOME
BACKUP_DIR=/var/lib/story-sentinel/backups
LOG_DIR=/var/log/story-sentinel

# Notification Configuration (CONFIGURE THESE)
# Discord webhook URL
DISCORD_WEBHOOK=

# Telegram bot configuration  
TG_BOT_TOKEN=
TG_CHAT_ID=

# GitHub token for higher API rate limits (optional)
GITHUB_TOKEN=
EOF

echo -e "${GREEN}✓${NC} Configuration files created"

# Create systemd service
echo -e "${YELLOW}Creating systemd service...${NC}"
cat > "/etc/systemd/system/$SERVICE_NAME.service" <<EOF
[Unit]
Description=Story Sentinel - Automated monitoring and upgrade system for Story Protocol nodes
Documentation=https://github.com/nodemasterpro/story-sentinel
After=network.target $STORY_SERVICE.service $STORY_GETH_SERVICE.service
Wants=$STORY_SERVICE.service $STORY_GETH_SERVICE.service

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
Environment=PATH=$INSTALL_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin
Environment=PYTHONPATH=$INSTALL_DIR
EnvironmentFile=$CONFIG_DIR/.env
ExecStart=$INSTALL_DIR/venv/bin/python -m sentinel monitor --config $CONFIG_DIR/config.yaml
ExecReload=/bin/kill -HUP \$MAINPID
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
SyslogIdentifier=$SERVICE_NAME

[Install]
WantedBy=multi-user.target
EOF

# Create CLI wrapper script
cat > "/usr/local/bin/story-sentinel" <<EOF
#!/bin/bash
# Story Sentinel CLI wrapper

cd "$INSTALL_DIR"
source venv/bin/activate
exec python -m sentinel "\$@" --config "$CONFIG_DIR/config.yaml"
EOF

chmod +x "/usr/local/bin/story-sentinel"

echo -e "${GREEN}✓${NC} Systemd service created"

# Enable and start service
echo -e "${YELLOW}Enabling service...${NC}"
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"

echo -e "${GREEN}✓${NC} Service enabled"

# Create backup and log directories
mkdir -p "/var/lib/story-sentinel/backups"
mkdir -p "/var/log/story-sentinel"
chown -R "$SERVICE_USER:$SERVICE_USER" "/var/lib/story-sentinel"
chown -R "$SERVICE_USER:$SERVICE_USER" "/var/log/story-sentinel"

echo
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Installation Complete!                ${NC}"
echo -e "${GREEN}========================================${NC}"
echo
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Configure notifications in: $CONFIG_DIR/.env"
echo "2. Start the service: systemctl start $SERVICE_NAME"
echo "3. Check status: story-sentinel status"
echo "4. View logs: journalctl -u $SERVICE_NAME -f"
echo
echo -e "${YELLOW}Commands available:${NC}"
echo "  story-sentinel status          # Check node status"
echo "  story-sentinel check-updates   # Check for updates"
echo "  story-sentinel upgrade story v1.2.1  # Manual upgrade"
echo "  systemctl status $SERVICE_NAME # Service status"
echo
echo -e "${YELLOW}Configuration files:${NC}"
echo "  Main config: $CONFIG_DIR/config.yaml"
echo "  Environment: $CONFIG_DIR/.env"
echo "  Service: /etc/systemd/system/$SERVICE_NAME.service"
echo
echo -e "${BLUE}API will be available at: http://localhost:8080${NC}"
echo -e "${BLUE}Health endpoint: http://localhost:8080/health${NC}"
echo