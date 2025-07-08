#!/bin/bash

# Story Sentinel - Verbose Installation Script (for debugging)
# This is a debug version with more verbose output

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Story Sentinel Verbose Installation   ${NC}"
echo -e "${BLUE}========================================${NC}"
echo

# Check if running as root
echo "Checking root privileges..."
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}This script must be run as root${NC}" 
   exit 1
fi
echo -e "${GREEN}✓${NC} Running as root"

# Detect OS
echo "Detecting operating system..."
if [[ -f /etc/os-release ]]; then
    . /etc/os-release
    OS=$NAME
    VER=$VERSION_ID
    echo -e "${GREEN}✓${NC} Detected OS: $OS $VER"
else
    echo -e "${RED}Cannot detect OS. This script supports Ubuntu/Debian.${NC}"
    exit 1
fi

# Install system dependencies
echo -e "${YELLOW}Installing system dependencies...${NC}"

# Update package list
echo "Updating package list..."
apt-get update -qq
echo -e "${GREEN}✓${NC} Package list updated"

# Test basic package installation
echo "Testing basic package installation..."
packages="python3 python3-pip python3-venv"
for package in $packages; do
    echo -n "Checking/installing $package... "
    if dpkg -l | grep -q "^ii  $package "; then
        echo "already installed ✓"
    else
        apt-get install -y "$package"
        echo "installed ✓"
    fi
done

echo -e "${GREEN}✓${NC} System dependencies installed"

# Story detection
echo -e "${YELLOW}Running Story Protocol detection...${NC}"

echo "Searching for Story binaries..."
STORY_BINARY=""
for path in "/usr/local/bin/story" "/root/go/bin/story"; do
    echo "  Checking: $path"
    if [[ -x "$path" ]]; then
        STORY_BINARY="$path"
        echo -e "${GREEN}✓${NC} Found Story binary: $STORY_BINARY"
        break
    fi
done

if [[ -z "$STORY_BINARY" ]]; then
    echo -e "${YELLOW}⚠${NC} Story binary not found (will use default)"
    STORY_BINARY="/usr/local/bin/story"
fi

echo "Searching for systemd services..."
if command -v systemctl >/dev/null 2>&1; then
    echo "  systemctl is available"
    services_found=$(systemctl list-units --type=service | grep -E '(story|geth)' | wc -l)
    echo "  Found $services_found Story-related services"
else
    echo -e "${YELLOW}⚠${NC} systemctl not available"
fi

echo -e "${GREEN}✓${NC} Story detection complete"

# Test directory creation
echo -e "${YELLOW}Testing directory creation...${NC}"
INSTALL_DIR="/opt/story-sentinel"
CONFIG_DIR="/etc/story-sentinel"

echo "Creating installation directories..."
mkdir -p "$INSTALL_DIR"
mkdir -p "$CONFIG_DIR" 
mkdir -p "/var/log/story-sentinel"

if [[ -d "$INSTALL_DIR" ]] && [[ -d "$CONFIG_DIR" ]]; then
    echo -e "${GREEN}✓${NC} Directories created successfully"
else
    echo -e "${RED}✗${NC} Directory creation failed"
    exit 1
fi

# Test Python environment
echo -e "${YELLOW}Testing Python environment...${NC}"
cd "$INSTALL_DIR"

echo "Creating Python virtual environment..."
python3 -m venv venv
if [[ -d "venv" ]]; then
    echo -e "${GREEN}✓${NC} Virtual environment created"
else
    echo -e "${RED}✗${NC} Virtual environment creation failed"
    exit 1
fi

echo "Activating virtual environment..."
source venv/bin/activate
echo -e "${GREEN}✓${NC} Virtual environment activated"

echo
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Verbose Installation Test Complete!   ${NC}"
echo -e "${GREEN}========================================${NC}"
echo
echo "Key findings:"
echo "  Story binary: $STORY_BINARY"
echo "  Install directory: $INSTALL_DIR"
echo "  Config directory: $CONFIG_DIR"
echo "  Python version: $(python3 --version)"
echo
echo "The installation environment appears to be working correctly."
echo "You can now run the full install.sh script."