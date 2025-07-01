#!/bin/bash

# Story Sentinel Runner Script
# Bash wrapper for upgrade execution with safety checks

set -euo pipefail

# Configuration
STORY_HOME="${STORY_HOME:-$HOME/.story}"
BACKUP_DIR="${BACKUP_DIR:-/var/lib/story-sentinel/backups}"
LOG_FILE="${LOG_FILE:-/var/log/story-sentinel/runner.log}"
STORY_SERVICE="${STORY_SERVICE:-story}"
STORY_GETH_SERVICE="${STORY_GETH_SERVICE:-story-geth}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Check if running as appropriate user
check_user() {
    if [[ $EUID -eq 0 ]]; then
        log_warn "Running as root - this is not recommended"
    fi
}

# Create backup of current installation
create_backup() {
    local component=$1
    local backup_name="${component}_$(date +%Y%m%d_%H%M%S)"
    local backup_path="$BACKUP_DIR/$backup_name"
    
    log_info "Creating backup: $backup_path"
    
    mkdir -p "$backup_path"
    
    # Backup binary
    if [[ "$component" == "story" ]]; then
        cp -p /usr/local/bin/story "$backup_path/" 2>/dev/null || true
        # Backup config
        if [[ -d "$STORY_HOME/story/config" ]]; then
            cp -r "$STORY_HOME/story/config" "$backup_path/"
        fi
    elif [[ "$component" == "story_geth" ]]; then
        cp -p /usr/local/bin/story-geth "$backup_path/" 2>/dev/null || true
    fi
    
    # Save metadata
    cat > "$backup_path/metadata.json" <<EOF
{
    "component": "$component",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "version": "$(/usr/local/bin/$component version 2>/dev/null || echo 'unknown')"
}
EOF
    
    echo "$backup_path"
}

# Download and verify binary
download_binary() {
    local component=$1
    local version=$2
    local download_url=$3
    local temp_dir=$(mktemp -d)
    
    log_info "Downloading $component version $version"
    
    # Download
    if ! curl -L -o "$temp_dir/archive.tar.gz" "$download_url"; then
        log_error "Failed to download binary"
        rm -rf "$temp_dir"
        return 1
    fi
    
    # Extract
    if ! tar -xzf "$temp_dir/archive.tar.gz" -C "$temp_dir"; then
        log_error "Failed to extract archive"
        rm -rf "$temp_dir"
        return 1
    fi
    
    # Find binary
    local binary_name="story"
    if [[ "$component" == "story_geth" ]]; then
        binary_name="geth"
    fi
    
    local binary_path=$(find "$temp_dir" -name "$binary_name" -type f | head -1)
    if [[ -z "$binary_path" ]]; then
        log_error "Binary not found in archive"
        rm -rf "$temp_dir"
        return 1
    fi
    
    # Make executable
    chmod +x "$binary_path"
    
    # Verify binary
    if ! "$binary_path" version &>/dev/null; then
        log_error "Binary verification failed"
        rm -rf "$temp_dir"
        return 1
    fi
    
    echo "$binary_path"
}

# Stop service safely
stop_service() {
    local service=$1
    
    log_info "Stopping $service"
    
    if systemctl is-active --quiet "$service"; then
        systemctl stop "$service"
        
        # Wait for service to stop
        local count=0
        while systemctl is-active --quiet "$service" && [[ $count -lt 30 ]]; do
            sleep 1
            ((count++))
        done
        
        if systemctl is-active --quiet "$service"; then
            log_error "Service $service failed to stop"
            return 1
        fi
    else
        log_warn "Service $service is not running"
    fi
    
    return 0
}

# Start service
start_service() {
    local service=$1
    
    log_info "Starting $service"
    
    systemctl start "$service"
    
    # Wait for service to start
    sleep 5
    
    if ! systemctl is-active --quiet "$service"; then
        log_error "Service $service failed to start"
        return 1
    fi
    
    return 0
}

# Replace binary
replace_binary() {
    local component=$1
    local new_binary=$2
    local target="/usr/local/bin/$component"
    
    if [[ "$component" == "story_geth" ]]; then
        target="/usr/local/bin/story-geth"
    fi
    
    log_info "Replacing binary at $target"
    
    # Copy new binary
    cp -f "$new_binary" "$target"
    chmod 755 "$target"
    
    return 0
}

# Rollback to backup
rollback() {
    local component=$1
    local backup_path=$2
    
    log_warn "Rolling back $component from $backup_path"
    
    # Stop service
    local service="$STORY_SERVICE"
    if [[ "$component" == "story_geth" ]]; then
        service="$STORY_GETH_SERVICE"
    fi
    
    stop_service "$service" || true
    
    # Restore binary
    local binary_name="$component"
    if [[ "$component" == "story_geth" ]]; then
        binary_name="story-geth"
    fi
    
    if [[ -f "$backup_path/$binary_name" ]]; then
        cp -f "$backup_path/$binary_name" "/usr/local/bin/$binary_name"
        chmod 755 "/usr/local/bin/$binary_name"
    fi
    
    # Start service
    start_service "$service"
    
    log_info "Rollback completed"
}

# Verify upgrade
verify_upgrade() {
    local component=$1
    local expected_version=$2
    
    log_info "Verifying upgrade for $component"
    
    # Check version
    local actual_version
    if [[ "$component" == "story" ]]; then
        actual_version=$(story version 2>/dev/null || echo "error")
    else
        actual_version=$(story-geth version 2>/dev/null || echo "error")
    fi
    
    if [[ "$actual_version" == "error" ]]; then
        log_error "Failed to get version"
        return 1
    fi
    
    # Check if version matches (partial match)
    if [[ "$actual_version" == *"$expected_version"* ]]; then
        log_info "Version verified: $actual_version"
        return 0
    else
        log_error "Version mismatch. Expected: $expected_version, Got: $actual_version"
        return 1
    fi
}

# Main upgrade function
perform_upgrade() {
    local component=$1
    local version=$2
    local download_url=$3
    
    log_info "Starting upgrade: $component to version $version"
    
    # Create backup
    local backup_path=$(create_backup "$component")
    
    # Download new binary
    local new_binary=$(download_binary "$component" "$version" "$download_url")
    if [[ -z "$new_binary" ]]; then
        log_error "Failed to download binary"
        exit 1
    fi
    
    # Determine service name
    local service="$STORY_SERVICE"
    if [[ "$component" == "story_geth" ]]; then
        service="$STORY_GETH_SERVICE"
    fi
    
    # Stop service
    if ! stop_service "$service"; then
        log_error "Failed to stop service"
        rm -f "$new_binary"
        exit 1
    fi
    
    # Replace binary
    if ! replace_binary "$component" "$new_binary"; then
        log_error "Failed to replace binary"
        rollback "$component" "$backup_path"
        rm -f "$new_binary"
        exit 1
    fi
    
    # Clean up temp binary
    rm -f "$new_binary"
    
    # Start service
    if ! start_service "$service"; then
        log_error "Failed to start service after upgrade"
        rollback "$component" "$backup_path"
        exit 1
    fi
    
    # Wait for service to stabilize
    sleep 10
    
    # Verify upgrade
    if ! verify_upgrade "$component" "$version"; then
        log_error "Upgrade verification failed"
        rollback "$component" "$backup_path"
        exit 1
    fi
    
    log_info "Upgrade completed successfully"
}

# Health check function
health_check() {
    local component=$1
    
    if [[ "$component" == "story" ]]; then
        # Check Story RPC
        if curl -s http://localhost:26657/status >/dev/null 2>&1; then
            log_info "Story RPC is responsive"
            return 0
        else
            log_error "Story RPC is not responsive"
            return 1
        fi
    elif [[ "$component" == "story_geth" ]]; then
        # Check Geth RPC
        if curl -s -X POST -H "Content-Type: application/json" \
            --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' \
            http://localhost:8545 >/dev/null 2>&1; then
            log_info "Story Geth RPC is responsive"
            return 0
        else
            log_error "Story Geth RPC is not responsive"
            return 1
        fi
    fi
}

# Parse command line arguments
main() {
    local command=${1:-help}
    
    case "$command" in
        upgrade)
            if [[ $# -lt 4 ]]; then
                echo "Usage: $0 upgrade <component> <version> <download_url>"
                exit 1
            fi
            check_user
            perform_upgrade "$2" "$3" "$4"
            ;;
        backup)
            if [[ $# -lt 2 ]]; then
                echo "Usage: $0 backup <component>"
                exit 1
            fi
            create_backup "$2"
            ;;
        health)
            if [[ $# -lt 2 ]]; then
                echo "Usage: $0 health <component>"
                exit 1
            fi
            health_check "$2"
            ;;
        rollback)
            if [[ $# -lt 3 ]]; then
                echo "Usage: $0 rollback <component> <backup_path>"
                exit 1
            fi
            rollback "$2" "$3"
            ;;
        help|*)
            echo "Story Sentinel Runner Script"
            echo ""
            echo "Usage: $0 <command> [arguments]"
            echo ""
            echo "Commands:"
            echo "  upgrade <component> <version> <download_url>  - Perform upgrade"
            echo "  backup <component>                            - Create backup"
            echo "  health <component>                            - Check health"
            echo "  rollback <component> <backup_path>            - Rollback to backup"
            echo "  help                                          - Show this help"
            echo ""
            echo "Components: story, story_geth"
            ;;
    esac
}

# Create log directory if needed
mkdir -p "$(dirname "$LOG_FILE")"

# Run main function
main "$@"