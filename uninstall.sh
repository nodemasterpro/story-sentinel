#!/bin/bash

# Story Sentinel - Complete Uninstallation Script
# This script completely removes Story Sentinel from your system

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Story Sentinel Uninstallation         ${NC}"
echo -e "${BLUE}========================================${NC}"
echo

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}This script must be run as root${NC}" 
   exit 1
fi

echo -e "${YELLOW}This will completely remove Story Sentinel from your system.${NC}"
echo -e "${YELLOW}Your Story and Story-Geth nodes will NOT be affected.${NC}"
echo
read -p "Are you sure you want to continue? (yes/no): " -r REPLY
echo

if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "Uninstallation cancelled."
    exit 0
fi

# Stop services
echo -e "${YELLOW}Stopping Story Sentinel services...${NC}"
systemctl stop story-sentinel 2>/dev/null || true
systemctl stop story-sentinel-api 2>/dev/null || true
echo -e "${GREEN}✓${NC} Services stopped"

# Disable services
echo -e "${YELLOW}Disabling services...${NC}"
systemctl disable story-sentinel 2>/dev/null || true
systemctl disable story-sentinel-api 2>/dev/null || true
echo -e "${GREEN}✓${NC} Services disabled"

# Remove systemd service files
echo -e "${YELLOW}Removing systemd service files...${NC}"
rm -f /etc/systemd/system/story-sentinel.service
rm -f /etc/systemd/system/story-sentinel-api.service
systemctl daemon-reload
echo -e "${GREEN}✓${NC} Service files removed"

# Remove application directory
echo -e "${YELLOW}Removing application files...${NC}"
if [[ -d "/opt/story-sentinel" ]]; then
    rm -rf /opt/story-sentinel
    echo -e "${GREEN}✓${NC} Application directory removed"
else
    echo -e "${YELLOW}⚠${NC} Application directory not found"
fi

# Remove configuration directory
echo -e "${YELLOW}Removing configuration files...${NC}"
if [[ -d "/etc/story-sentinel" ]]; then
    # Check if user wants to keep configuration
    read -p "Do you want to keep your configuration files? (yes/no): " -r KEEP_CONFIG
    if [[ $KEEP_CONFIG =~ ^[Yy][Ee][Ss]$ ]]; then
        echo -e "${BLUE}ℹ${NC} Configuration files preserved in /etc/story-sentinel"
    else
        rm -rf /etc/story-sentinel
        echo -e "${GREEN}✓${NC} Configuration directory removed"
    fi
else
    echo -e "${YELLOW}⚠${NC} Configuration directory not found"
fi

# Remove data directories
echo -e "${YELLOW}Removing data directories...${NC}"

# Remove backup directory
if [[ -d "/var/lib/story-sentinel" ]]; then
    read -p "Do you want to keep backup files? (yes/no): " -r KEEP_BACKUPS
    if [[ $KEEP_BACKUPS =~ ^[Yy][Ee][Ss]$ ]]; then
        echo -e "${BLUE}ℹ${NC} Backup files preserved in /var/lib/story-sentinel"
    else
        rm -rf /var/lib/story-sentinel
        echo -e "${GREEN}✓${NC} Backup directory removed"
    fi
else
    echo -e "${YELLOW}⚠${NC} Backup directory not found"
fi

# Remove log directory
if [[ -d "/var/log/story-sentinel" ]]; then
    read -p "Do you want to keep log files? (yes/no): " -r KEEP_LOGS
    if [[ $KEEP_LOGS =~ ^[Yy][Ee][Ss]$ ]]; then
        echo -e "${BLUE}ℹ${NC} Log files preserved in /var/log/story-sentinel"
    else
        rm -rf /var/log/story-sentinel
        echo -e "${GREEN}✓${NC} Log directory removed"
    fi
else
    echo -e "${YELLOW}⚠${NC} Log directory not found"
fi

# Remove CLI wrapper
echo -e "${YELLOW}Removing CLI wrapper...${NC}"
if [[ -f "/usr/local/bin/story-sentinel" ]]; then
    rm -f /usr/local/bin/story-sentinel
    echo -e "${GREEN}✓${NC} CLI wrapper removed"
else
    echo -e "${YELLOW}⚠${NC} CLI wrapper not found"
fi

# Remove any remaining journal logs
echo -e "${YELLOW}Cleaning journal logs...${NC}"
journalctl --vacuum-time=1s 2>/dev/null || true
echo -e "${GREEN}✓${NC} Journal logs cleaned"

# Check for any remaining files
echo -e "${YELLOW}Checking for remaining files...${NC}"
remaining_files=()

# Check common locations
for path in "/opt/story-sentinel" "/etc/story-sentinel" "/var/lib/story-sentinel" "/var/log/story-sentinel" "/usr/local/bin/story-sentinel"; do
    if [[ -e "$path" ]]; then
        remaining_files+=("$path")
    fi
done

if [[ ${#remaining_files[@]} -eq 0 ]]; then
    echo -e "${GREEN}✓${NC} All Story Sentinel files have been removed"
else
    echo -e "${YELLOW}⚠${NC} The following files/directories still exist:"
    for file in "${remaining_files[@]}"; do
        echo "   - $file"
    done
fi

echo
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Uninstallation Complete!              ${NC}"
echo -e "${GREEN}========================================${NC}"
echo
echo "Story Sentinel has been removed from your system."
echo "Your Story and Story-Geth nodes were not affected."
echo
echo "To reinstall Story Sentinel, run:"
echo "  curl -sSL https://raw.githubusercontent.com/nodemasterpro/story-sentinel/main/quick-start.sh | sudo bash"
echo