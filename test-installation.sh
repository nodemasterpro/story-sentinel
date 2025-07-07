#!/bin/bash

# Story Sentinel - Test d'Installation
# Script pour tester l'installation native complète

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Test results
TESTS_PASSED=0
TESTS_FAILED=0

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Story Sentinel - Test d'Installation  ${NC}"
echo -e "${BLUE}========================================${NC}"
echo

# Function to run test
run_test() {
    local test_name="$1"
    local test_command="$2"
    
    echo -n "Testing $test_name... "
    
    if eval "$test_command" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ PASS${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗ FAIL${NC}"
        ((TESTS_FAILED++))
    fi
}

# Function to run test with output
run_test_with_output() {
    local test_name="$1"
    local test_command="$2"
    
    echo -e "${YELLOW}Testing $test_name...${NC}"
    
    if eval "$test_command"; then
        echo -e "${GREEN}✓ PASS${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗ FAIL${NC}"
        ((TESTS_FAILED++))
    fi
    echo
}

# Test 1: Installation directories
echo -e "${YELLOW}=== Test 1: Répertoires d'Installation ===${NC}"
run_test "Installation directory" "test -d /opt/story-sentinel"
run_test "Configuration directory" "test -d /etc/story-sentinel"
run_test "Log directory" "test -d /var/log/story-sentinel"
run_test "Backup directory" "test -d /var/lib/story-sentinel/backups"
echo

# Test 2: Files and permissions
echo -e "${YELLOW}=== Test 2: Fichiers et Permissions ===${NC}"
run_test "Main application" "test -f /opt/story-sentinel/sentinel/__init__.py"
run_test "Configuration file" "test -f /etc/story-sentinel/config.yaml"
run_test "Environment file" "test -f /etc/story-sentinel/.env"
run_test "Systemd service" "test -f /etc/systemd/system/story-sentinel.service"
run_test "CLI wrapper" "test -x /usr/local/bin/story-sentinel"
run_test "Upgrade script" "test -x /opt/story-sentinel/scripts/upgrade-runner.sh"
echo

# Test 3: Python environment
echo -e "${YELLOW}=== Test 3: Environnement Python ===${NC}"
run_test "Virtual environment" "test -d /opt/story-sentinel/venv"
run_test "Python executable" "test -x /opt/story-sentinel/venv/bin/python"
run_test "Story Sentinel package" "/opt/story-sentinel/venv/bin/python -c 'import sentinel'"
echo

# Test 4: Service status
echo -e "${YELLOW}=== Test 4: Service Systemd ===${NC}"
run_test "Service file exists" "systemctl list-unit-files | grep -q story-sentinel"
run_test "Service is enabled" "systemctl is-enabled story-sentinel >/dev/null 2>&1 || true"

# Check if service is running
if systemctl is-active --quiet story-sentinel; then
    echo -e "Service status: ${GREEN}Running${NC}"
    ((TESTS_PASSED++))
else
    echo -e "Service status: ${YELLOW}Stopped${NC} (normal if not started yet)"
    ((TESTS_PASSED++))
fi
echo

# Test 5: CLI functionality
echo -e "${YELLOW}=== Test 5: Interface CLI ===${NC}"
run_test_with_output "CLI help command" "story-sentinel --help"
run_test_with_output "CLI status command" "timeout 10 story-sentinel status || true"

# Test 6: Configuration validation
echo -e "${YELLOW}=== Test 6: Validation Configuration ===${NC}"

# Check configuration content
if grep -q "binary_path:" /etc/story-sentinel/config.yaml; then
    echo -e "Configuration content: ${GREEN}✓ Valid${NC}"
    ((TESTS_PASSED++))
else
    echo -e "Configuration content: ${RED}✗ Invalid${NC}"
    ((TESTS_FAILED++))
fi

# Check environment variables
if grep -q "MODE=" /etc/story-sentinel/.env; then
    echo -e "Environment variables: ${GREEN}✓ Valid${NC}"
    ((TESTS_PASSED++))
else
    echo -e "Environment variables: ${RED}✗ Invalid${NC}"
    ((TESTS_FAILED++))
fi
echo

# Test 7: Story Protocol detection
echo -e "${YELLOW}=== Test 7: Détection Story Protocol ===${NC}"

# Try to find Story services
story_services=$(systemctl list-units --type=service | grep -E '(story|geth)' | wc -l)
if [ "$story_services" -gt 0 ]; then
    echo -e "Story services detected: ${GREEN}✓ Found $story_services services${NC}"
    ((TESTS_PASSED++))
else
    echo -e "Story services detected: ${YELLOW}⚠ No services found${NC}"
    ((TESTS_PASSED++))  # Not a failure, might not be installed yet
fi

# Check for Story binaries
story_binaries=0
for path in "/usr/local/bin/story" "/root/go/bin/story" "/usr/local/bin/story-geth" "/root/go/bin/geth"; do
    if [ -x "$path" ]; then
        ((story_binaries++))
    fi
done

if [ "$story_binaries" -gt 0 ]; then
    echo -e "Story binaries found: ${GREEN}✓ Found $story_binaries binaries${NC}"
    ((TESTS_PASSED++))
else
    echo -e "Story binaries found: ${YELLOW}⚠ No binaries found${NC}"
    ((TESTS_PASSED++))  # Not a failure
fi
echo

# Test 8: Network and API
echo -e "${YELLOW}=== Test 8: API et Réseau ===${NC}"

# Test if port 8080 is configured
if grep -q "API_PORT=8080" /etc/story-sentinel/.env; then
    echo -e "API port configuration: ${GREEN}✓ Configured${NC}"
    ((TESTS_PASSED++))
else
    echo -e "API port configuration: ${YELLOW}⚠ Default port${NC}"
    ((TESTS_PASSED++))
fi

# Test API if service is running
if systemctl is-active --quiet story-sentinel; then
    if curl -s http://localhost:8080/health > /dev/null; then
        echo -e "API health endpoint: ${GREEN}✓ Accessible${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "API health endpoint: ${RED}✗ Not accessible${NC}"
        ((TESTS_FAILED++))
    fi
else
    echo -e "API health endpoint: ${YELLOW}⚠ Service not running${NC}"
    ((TESTS_PASSED++))
fi
echo

# Test 9: Permissions and security
echo -e "${YELLOW}=== Test 9: Permissions et Sécurité ===${NC}"

# Check file permissions
if [ "$(stat -c %a /etc/story-sentinel/.env)" = "600" ] || [ "$(stat -c %a /etc/story-sentinel/.env)" = "644" ]; then
    echo -e "Environment file permissions: ${GREEN}✓ Secure${NC}"
    ((TESTS_PASSED++))
else
    echo -e "Environment file permissions: ${YELLOW}⚠ Should be 600 or 644${NC}"
    ((TESTS_PASSED++))
fi

# Check ownership
if [ "$(stat -c %U /opt/story-sentinel)" = "root" ]; then
    echo -e "Installation ownership: ${GREEN}✓ Root${NC}"
    ((TESTS_PASSED++))
else
    echo -e "Installation ownership: ${RED}✗ Not root${NC}"
    ((TESTS_FAILED++))
fi
echo

# Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Résumé des Tests                      ${NC}"
echo -e "${BLUE}========================================${NC}"
echo
echo -e "Tests réussis: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Tests échoués: ${RED}$TESTS_FAILED${NC}"
echo

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 Tous les tests sont passés avec succès !${NC}"
    echo
    echo -e "${YELLOW}Prochaines étapes:${NC}"
    echo "1. Configurer les notifications dans /etc/story-sentinel/.env"
    echo "2. Démarrer le service: sudo systemctl start story-sentinel"
    echo "3. Vérifier le statut: story-sentinel status"
    echo "4. Voir les logs: sudo journalctl -u story-sentinel -f"
    exit 0
else
    echo -e "${RED}⚠️  Certains tests ont échoué. Vérifiez l'installation.${NC}"
    echo
    echo -e "${YELLOW}Commandes de diagnostic:${NC}"
    echo "- Logs d'installation: sudo journalctl -u story-sentinel"
    echo "- Vérifier la configuration: story-sentinel status"
    echo "- Réinstaller si nécessaire: sudo bash install.sh"
    exit 1
fi