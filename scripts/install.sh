#!/bin/bash

# Story Sentinel Installation Script
# This script installs Story Sentinel with all dependencies

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Installation paths
INSTALL_DIR="/opt/story-sentinel"
SERVICE_USER="story-sentinel"
VENV_DIR="$INSTALL_DIR/venv"
CONFIG_DIR="/etc/story-sentinel"
LOG_DIR="/var/log/story-sentinel"
BACKUP_DIR="/var/lib/story-sentinel/backups"

# Print colored messages
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "This script must be run as root"
        exit 1
    fi
}

# Check system requirements
check_requirements() {
    print_info "Checking system requirements..."
    
    # Check OS
    if [[ ! -f /etc/os-release ]]; then
        print_error "Cannot determine OS version"
        exit 1
    fi
    
    . /etc/os-release
    if [[ "$ID" != "ubuntu" ]] || [[ ! "$VERSION_ID" =~ ^(22\.04|24\.04)$ ]]; then
        print_warn "This script is designed for Ubuntu 22.04/24.04 LTS"
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    # Check Python version
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    if [[ $(echo "$PYTHON_VERSION < 3.10" | bc) -eq 1 ]]; then
        print_error "Python 3.10 or higher is required (found $PYTHON_VERSION)"
        exit 1
    fi
    
    # Check systemd
    if ! command -v systemctl &> /dev/null; then
        print_error "systemd is not available"
        exit 1
    fi
    
    # Check required commands
    local required_cmds=("jq" "curl" "tar" "git")
    local missing_cmds=()
    
    for cmd in "${required_cmds[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            missing_cmds+=("$cmd")
        fi
    done
    
    if [[ ${#missing_cmds[@]} -gt 0 ]]; then
        print_warn "Missing required commands: ${missing_cmds[*]}"
        print_info "Installing missing dependencies..."
        apt-get update
        apt-get install -y "${missing_cmds[@]}" python3-pip python3-venv
    fi
    
    print_info "All requirements satisfied"
}

# Create service user
create_user() {
    print_info "Creating service user..."
    
    if id "$SERVICE_USER" &>/dev/null; then
        print_warn "User $SERVICE_USER already exists"
    else
        useradd --system --home-dir "$INSTALL_DIR" --shell /bin/bash "$SERVICE_USER"
        print_info "Created user $SERVICE_USER"
    fi
}

# Install Story Sentinel
install_sentinel() {
    print_info "Installing Story Sentinel..."
    
    # Create directories
    mkdir -p "$INSTALL_DIR" "$CONFIG_DIR" "$LOG_DIR" "$BACKUP_DIR"
    
    # Copy source files
    if [[ -d "../sentinel" ]]; then
        # Installing from source
        cp -r ../sentinel "$INSTALL_DIR/"
        cp -r ../scripts "$INSTALL_DIR/"
        if [[ -f "../requirements.txt" ]]; then
            cp ../requirements.txt "$INSTALL_DIR/"
        fi
        if [[ -f "../setup.py" ]]; then
            cp ../setup.py "$INSTALL_DIR/"
        fi
    else
        print_error "Source files not found. Please run from the scripts directory."
        exit 1
    fi
    
    # Create virtual environment
    print_info "Creating Python virtual environment..."
    python3 -m venv "$VENV_DIR"
    
    # Install Python dependencies
    print_info "Installing Python dependencies..."
    
    # Create requirements.txt if not exists
    if [[ ! -f "$INSTALL_DIR/requirements.txt" ]]; then
        cat > "$INSTALL_DIR/requirements.txt" <<EOF
requests>=2.28.0
PyYAML>=6.0
python-dotenv>=1.0.0
psutil>=5.9.0
click>=8.1.0
icalendar>=5.0.0
pytz>=2023.3
prometheus-client>=0.17.0
aiohttp>=3.8.0
EOF
    fi
    
    "$VENV_DIR/bin/pip" install --upgrade pip
    "$VENV_DIR/bin/pip" install -r "$INSTALL_DIR/requirements.txt"
    
    # Create setup.py if not exists
    if [[ ! -f "$INSTALL_DIR/setup.py" ]]; then
        cat > "$INSTALL_DIR/setup.py" <<EOF
from setuptools import setup, find_packages

setup(
    name="story-sentinel",
    version="1.1.0",
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'story-sentinel=sentinel.__main__:cli',
        ],
    },
)
EOF
    fi
    
    # Install package
    cd "$INSTALL_DIR"
    "$VENV_DIR/bin/pip" install -e .
    
    # Create symlink
    ln -sf "$VENV_DIR/bin/story-sentinel" /usr/local/bin/story-sentinel
    
    print_info "Story Sentinel installed successfully"
}

# Install systemd services
install_services() {
    print_info "Installing systemd services..."
    
    # Create main service
    cat > /etc/systemd/system/story-sentinel.service <<EOF
[Unit]
Description=Story Sentinel - Automated monitoring and upgrade system
After=network-online.target
Wants=network-online.target

[Service]
Type=exec
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$VENV_DIR/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=$VENV_DIR/bin/story-sentinel monitor
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=story-sentinel

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$LOG_DIR $BACKUP_DIR $CONFIG_DIR

[Install]
WantedBy=multi-user.target
EOF

    # Create timer for periodic checks (alternative to internal monitoring)
    cat > /etc/systemd/system/story-sentinel-check.service <<EOF
[Unit]
Description=Story Sentinel periodic check
After=network-online.target

[Service]
Type=oneshot
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$VENV_DIR/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=$VENV_DIR/bin/story-sentinel check-updates
EOF

    cat > /etc/systemd/system/story-sentinel-check.timer <<EOF
[Unit]
Description=Run Story Sentinel check every 5 minutes
Requires=story-sentinel-check.service

[Timer]
OnBootSec=5min
OnUnitActiveSec=5min

[Install]
WantedBy=timers.target
EOF

    # Create health check service
    cat > /etc/systemd/system/story-sentinel-health.service <<EOF
[Unit]
Description=Story Sentinel Health API
After=network-online.target
Wants=network-online.target

[Service]
Type=exec
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$VENV_DIR/bin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=$VENV_DIR/bin/python -m sentinel.api
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd
    systemctl daemon-reload
    
    print_info "Systemd services installed"
}

# Configure Story Sentinel
configure_sentinel() {
    print_info "Configuring Story Sentinel..."
    
    # Initialize configuration (skip validation during install)
    sudo -u "$SERVICE_USER" "$VENV_DIR/bin/story-sentinel" init || print_warn "Configuration init completed with warnings"
    
    # Copy example configs
    if [[ -f "$CONFIG_DIR/config.yaml" ]]; then
        print_warn "Configuration already exists, skipping"
    else
        # Create default config
        cat > "$CONFIG_DIR/config.yaml" <<EOF
story:
  binary_path: /usr/local/bin/story
  service_name: story
  rpc_port: 26657
  github_repo: piplabs/story
story_geth:
  binary_path: /usr/local/bin/story-geth
  service_name: story-geth
  rpc_port: 8545
  github_repo: piplabs/story-geth
thresholds:
  height_gap: 20
  min_peers: 5
  block_time_variance: 10
  memory_limit_gb: 8.0
  disk_space_min_gb: 10.0
EOF
    fi
    
    # Create .env template
    if [[ ! -f "$CONFIG_DIR/.env" ]]; then
        cp "$HOME/.story-sentinel/.env.example" "$CONFIG_DIR/.env.example" 2>/dev/null || true
        touch "$CONFIG_DIR/.env"
        chmod 600 "$CONFIG_DIR/.env"
    fi
    
    # Set permissions
    chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR" "$CONFIG_DIR" "$LOG_DIR" "$BACKUP_DIR"
    chmod 750 "$CONFIG_DIR"
    chmod 640 "$CONFIG_DIR"/*
    
    print_info "Configuration completed"
}

# Verify installation
verify_installation() {
    print_info "Verifying installation..."
    
    # Check if command works
    if story-sentinel --version &>/dev/null; then
        print_info "CLI command verified"
    else
        print_error "CLI command not working"
        return 1
    fi
    
    # Check configuration (non-blocking)
    if sudo -u "$SERVICE_USER" story-sentinel --version &>/dev/null; then
        print_info "Story Sentinel CLI verified"
        
        # Try to check status but don't fail if Story nodes aren't installed
        if sudo -u "$SERVICE_USER" story-sentinel status &>/dev/null; then
            print_info "Configuration and nodes verified"
        else
            print_warn "Story Sentinel installed but Story nodes not detected"
            print_warn "Please install Story Protocol nodes before starting the service"
        fi
    else
        print_error "Story Sentinel CLI not working properly"
        return 1
    fi
    
    return 0
}

# Main installation
main() {
    print_info "Story Sentinel Installation Script v1.1"
    print_info "======================================"
    
    check_root
    check_requirements
    create_user
    install_sentinel
    install_services
    configure_sentinel
    
    if verify_installation; then
        print_info ""
        print_info "Installation completed successfully!"
        print_info ""
        print_info "Next steps:"
        print_info "1. Install Story Protocol nodes if not already done"
        print_info "2. Edit configuration: $CONFIG_DIR/.env"
        print_info "3. Update binary paths in: $CONFIG_DIR/config.yaml"
        print_info "4. Test configuration: story-sentinel status"
        print_info "5. Start the service: systemctl start story-sentinel"
        print_info "6. Enable auto-start: systemctl enable story-sentinel"
        print_info "7. Check status: systemctl status story-sentinel"
        print_info "8. View logs: journalctl -u story-sentinel -f"
        print_info ""
        print_info "Commands:"
        print_info "  story-sentinel status       - Check node health"
        print_info "  story-sentinel check-updates - Check for updates"
        print_info "  story-sentinel schedule     - View upgrade schedule"
        print_info "  story-sentinel --help       - Show all commands"
    else
        print_error "Installation verification failed"
        exit 1
    fi
}

# Run main function
main "$@"