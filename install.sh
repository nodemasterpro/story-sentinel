#!/bin/bash

# Story Sentinel - Native Installation Script
# This script installs Story Sentinel directly on your Story Protocol server

set -e

# Function to handle errors
error_exit() {
    echo -e "${RED}Error: $1${NC}" >&2
    exit 1
}

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

# Update package list
echo -n "Updating package list... "
if apt-get update -qq > /dev/null 2>&1; then
    echo "✓"
else
    echo "⚠ (warning, but continuing)"
fi

# Install packages individually to handle errors better
packages="python3 python3-pip python3-venv git curl wget sqlite3"
failed_packages=""

for package in $packages; do
    if ! dpkg -l | grep -q "^ii  $package "; then
        echo -n "Installing $package... "
        # Disable exit on error temporarily for package installation
        set +e
        apt-get install -y "$package" > /dev/null 2>&1
        result=$?
        set -e
        
        if [[ $result -eq 0 ]]; then
            echo "✓"
        else
            echo "⚠ (failed - may need manual installation)"
            failed_packages="$failed_packages $package"
        fi
    else
        echo "$package already installed ✓"
    fi
done

# Show warning for failed packages but continue
if [[ -n "$failed_packages" ]]; then
    echo -e "${YELLOW}⚠ Some packages failed to install:$failed_packages${NC}"
    echo -e "${YELLOW}  Installation will continue, but you may need to install these manually${NC}"
fi

# Try to install systemctl package (not critical)
set +e
apt-get install -y systemctl > /dev/null 2>&1
set -e

echo -e "${GREEN}✓${NC} System dependencies ready"

# Add debug checkpoint
echo -e "${BLUE}[DEBUG]${NC} Dependency installation complete, proceeding to Story detection..."

# Detect Story Protocol installation
echo -e "${YELLOW}Detecting Story Protocol installation...${NC}"

STORY_BINARY=""
STORY_GETH_BINARY=""
STORY_SERVICE=""
STORY_GETH_SERVICE=""
STORY_HOME=""

# Find Story binary
echo -e "${BLUE}[DEBUG]${NC} Searching for Story binary..."
for path in "/usr/local/bin/story" "/root/go/bin/story"; do
    if [[ -x "$path" ]]; then
        STORY_BINARY="$path"
        echo -e "${GREEN}✓${NC} Found Story binary: $STORY_BINARY"
        break
    fi
done

# Check home directories manually 
for home_dir in /home/*; do
    if [[ -d "$home_dir" ]] && [[ -x "$home_dir/go/bin/story" ]]; then
        STORY_BINARY="$home_dir/go/bin/story"
        echo -e "${GREEN}✓${NC} Found Story binary: $STORY_BINARY"
        break
    fi
done

# Check which command
if [[ -z "$STORY_BINARY" ]]; then
    which_result="$(which story 2>/dev/null || true)"
    if [[ -n "$which_result" ]] && [[ -x "$which_result" ]]; then
        STORY_BINARY="$which_result"
        echo -e "${GREEN}✓${NC} Found Story binary: $STORY_BINARY"
    fi
fi

# Find Story-Geth binary
echo -e "${BLUE}[DEBUG]${NC} Searching for Story-Geth binary..."
for path in "/usr/local/bin/story-geth" "/usr/local/bin/geth" "/root/go/bin/geth"; do
    if [[ -x "$path" ]]; then
        STORY_GETH_BINARY="$path"
        echo -e "${GREEN}✓${NC} Found Story-Geth binary: $STORY_GETH_BINARY"
        break
    fi
done

# Check home directories manually 
for home_dir in /home/*; do
    if [[ -d "$home_dir" ]] && [[ -x "$home_dir/go/bin/geth" ]]; then
        STORY_GETH_BINARY="$home_dir/go/bin/geth"
        echo -e "${GREEN}✓${NC} Found Story-Geth binary: $STORY_GETH_BINARY"
        break
    fi
done

# Check which command
if [[ -z "$STORY_GETH_BINARY" ]]; then
    which_result="$(which geth 2>/dev/null || true)"
    if [[ -n "$which_result" ]] && [[ -x "$which_result" ]]; then
        STORY_GETH_BINARY="$which_result"
        echo -e "${GREEN}✓${NC} Found Story-Geth binary: $STORY_GETH_BINARY"
    fi
fi

# Find Story services
echo -e "${BLUE}[DEBUG]${NC} Searching for Story services..."
for service in "story" "story-node" "story-testnet"; do
    if systemctl list-units --all --type=service | grep -q "$service.service"; then
        STORY_SERVICE="$service"
        echo -e "${GREEN}✓${NC} Found Story service: $STORY_SERVICE"
        break
    fi
done

echo -e "${BLUE}[DEBUG]${NC} Searching for Story-Geth services..."
for service in "story-geth" "geth" "geth-node"; do
    if systemctl list-units --all --type=service | grep -q "$service.service"; then
        STORY_GETH_SERVICE="$service"
        echo -e "${GREEN}✓${NC} Found Story-Geth service: $STORY_GETH_SERVICE"
        break
    fi
done

# Find Story home directory
echo -e "${BLUE}[DEBUG]${NC} Searching for Story home directory..."
if [[ -d "/root/.story" ]]; then
    STORY_HOME="/root/.story"
    echo -e "${GREEN}✓${NC} Found Story home: $STORY_HOME"
else
    # Check home directories manually
    for home_dir in /home/*; do
        if [[ -d "$home_dir" ]] && [[ -d "$home_dir/.story" ]]; then
            STORY_HOME="$home_dir/.story"
            echo -e "${GREEN}✓${NC} Found Story home: $STORY_HOME"
            break
        fi
    done
fi

# Set defaults if not found
if [[ -z "$STORY_BINARY" ]]; then
    STORY_BINARY="/usr/local/bin/story"
    echo -e "${YELLOW}⚠${NC} Story binary not found, using default: $STORY_BINARY"
fi

if [[ -z "$STORY_GETH_BINARY" ]]; then
    STORY_GETH_BINARY="/usr/local/bin/story-geth"
    echo -e "${YELLOW}⚠${NC} Story-Geth binary not found, using default: $STORY_GETH_BINARY"
fi

if [[ -z "$STORY_SERVICE" ]]; then
    STORY_SERVICE="story"
    echo -e "${YELLOW}⚠${NC} Story service not found, using default: $STORY_SERVICE"
fi

if [[ -z "$STORY_GETH_SERVICE" ]]; then
    STORY_GETH_SERVICE="story-geth"
    echo -e "${YELLOW}⚠${NC} Story-Geth service not found, using default: $STORY_GETH_SERVICE"
fi

# Detect RPC ports
echo -e "${BLUE}[DEBUG]${NC} Detection phase complete, moving to RPC ports..."
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

echo -e "${GREEN}✓${NC} Configuration detected/configured:"
echo "  Story binary: $STORY_BINARY"
echo "  Story service: $STORY_SERVICE" 
echo "  Story RPC: http://localhost:$STORY_RPC_PORT"
echo "  Story-Geth binary: $STORY_GETH_BINARY"
echo "  Story-Geth service: $STORY_GETH_SERVICE"
echo "  Story-Geth RPC: http://localhost:$STORY_GETH_RPC_PORT"
echo "  Story Home: $STORY_HOME"
echo
echo -e "${BLUE}Note: If your configuration differs, you can edit /etc/story-sentinel/.env after installation.${NC}"
echo

# Add debug checkpoint
echo -e "${BLUE}[DEBUG]${NC} Configuration detection complete, proceeding to installation..."

# Create installation directory
echo -e "${YELLOW}Creating installation directories...${NC}"
mkdir -p "$INSTALL_DIR"
mkdir -p "$CONFIG_DIR"
mkdir -p "/var/log/story-sentinel"
echo -e "${GREEN}✓${NC} Directories created"

# Install Python application
echo -e "${YELLOW}Installing Story Sentinel application...${NC}"

# Save current directory
SOURCE_DIR="$(cd "$(dirname "$0")" && pwd)"

# Check if we're in the source directory
if [[ -f "$SOURCE_DIR/sentinel/__init__.py" ]]; then
    echo "Installing from source directory: $SOURCE_DIR"
    cd "$INSTALL_DIR"
    cp -r "$SOURCE_DIR/sentinel" .
    cp "$SOURCE_DIR/setup.py" .
    cp "$SOURCE_DIR/requirements.txt" .
    if [[ -d "$SOURCE_DIR/scripts" ]]; then
        cp -r "$SOURCE_DIR/scripts" .
    fi
    echo -e "${GREEN}✓${NC} Source files copied"
else
    # Download from GitHub if not running from source
    echo -e "${YELLOW}Downloading from GitHub...${NC}"
    cd "$INSTALL_DIR"
    git clone https://github.com/nodemasterpro/story-sentinel.git temp_download
    cp -r temp_download/sentinel .
    cp temp_download/setup.py .
    cp temp_download/requirements.txt .
    if [[ -d "temp_download/scripts" ]]; then
        cp -r temp_download/scripts .
    fi
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

# Add debug checkpoint
echo -e "${BLUE}[DEBUG]${NC} Python environment setup complete, generating configuration..."

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
ExecStart=$INSTALL_DIR/venv/bin/python -m sentinel monitor
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
export STORY_SENTINEL_CONFIG="$CONFIG_DIR/config.yaml"
exec python -m sentinel "\$@"
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