#!/bin/bash

# Test script to debug installation issues
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Story Sentinel Installation Debug     ${NC}"
echo -e "${BLUE}========================================${NC}"
echo

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}This script must be run as root${NC}" 
   exit 1
fi

# Step 1: OS Detection
echo -e "${YELLOW}Step 1: OS Detection${NC}"
if [[ -f /etc/os-release ]]; then
    . /etc/os-release
    OS=$NAME
    VER=$VERSION_ID
    echo -e "${GREEN}✓${NC} Detected OS: $OS $VER"
else
    echo -e "${RED}Cannot detect OS${NC}"
    exit 1
fi

# Step 2: Test package installation
echo -e "${YELLOW}Step 2: Testing Package Installation${NC}"
echo "Updating package list..."
apt-get update -qq 2>/dev/null
echo -e "${GREEN}✓${NC} Package list updated"

# Test installing a simple package
echo "Testing package installation (python3)..."
if apt-get install -y python3 > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Package installation works"
else
    echo -e "${RED}✗${NC} Package installation failed"
    exit 1
fi

# Step 3: Test Story detection
echo -e "${YELLOW}Step 3: Story Detection Test${NC}"

# Check for Story binaries
echo "Checking for Story binaries..."
STORY_FOUND=""
for path in "/usr/local/bin/story" "/root/go/bin/story" "/home/*/go/bin/story"; do
    if [[ -x "$path" ]]; then
        STORY_FOUND="$path"
        echo -e "${GREEN}✓${NC} Found Story binary: $STORY_FOUND"
        break
    fi
done

if [[ -z "$STORY_FOUND" ]]; then
    echo -e "${YELLOW}⚠${NC} No Story binary found - this is normal for testing"
fi

# Check for services
echo "Checking for systemd services..."
if command -v systemctl >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} systemctl is available"
    systemctl list-units --type=service | grep -E '(story|geth)' || echo "No Story services found"
else
    echo -e "${YELLOW}⚠${NC} systemctl not available"
fi

# Step 4: Test directory creation
echo -e "${YELLOW}Step 4: Directory Creation Test${NC}"
TEST_DIR="/tmp/story-sentinel-test"
mkdir -p "$TEST_DIR"
if [[ -d "$TEST_DIR" ]]; then
    echo -e "${GREEN}✓${NC} Directory creation works"
    rm -rf "$TEST_DIR"
else
    echo -e "${RED}✗${NC} Directory creation failed"
fi

# Step 5: Test Python environment
echo -e "${YELLOW}Step 5: Python Environment Test${NC}"
cd /tmp
python3 -m venv test_venv
if [[ -d "test_venv" ]]; then
    echo -e "${GREEN}✓${NC} Python virtual environment creation works"
    rm -rf test_venv
else
    echo -e "${RED}✗${NC} Python virtual environment creation failed"
fi

echo
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Debug Test Complete!                  ${NC}"
echo -e "${GREEN}========================================${NC}"
echo
echo "All basic components seem to be working."
echo "The installation script should be able to proceed."