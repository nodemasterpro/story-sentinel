#!/bin/bash

# Story Sentinel Cleanup Script
# Removes previous installation for fresh reinstall

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

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
if [[ $EUID -ne 0 ]]; then
    print_error "This script must be run as root"
    exit 1
fi

print_info "Story Sentinel Cleanup Script"
print_info "============================="

# Stop and disable services
print_info "Stopping services..."
systemctl stop story-sentinel 2>/dev/null || true
systemctl stop story-sentinel-api 2>/dev/null || true
systemctl disable story-sentinel 2>/dev/null || true
systemctl disable story-sentinel-api 2>/dev/null || true

# Remove systemd services
print_info "Removing systemd services..."
rm -f /etc/systemd/system/story-sentinel.service
rm -f /etc/systemd/system/story-sentinel-api.service
rm -f /etc/systemd/system/story-sentinel-check.service
rm -f /etc/systemd/system/story-sentinel-check.timer
systemctl daemon-reload

# Remove symlink
print_info "Removing symlink..."
rm -f /usr/local/bin/story-sentinel

# Remove installation directory
print_info "Removing installation directory..."
rm -rf /opt/story-sentinel

# Remove user (but keep home directory for configs)
print_info "Removing user..."
userdel story-sentinel 2>/dev/null || true

print_info "Cleanup completed!"
print_info "Configuration files in /etc/story-sentinel and logs in /var/log/story-sentinel were preserved"
print_info "You can now run ./install.sh again"