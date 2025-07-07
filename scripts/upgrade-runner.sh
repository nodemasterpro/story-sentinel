#!/bin/bash

# Story Sentinel Upgrade Runner
# Handles actual upgrade process with proper service management

set -e

# Configuration
LOG_FILE="/var/log/story-sentinel/upgrade.log"
BACKUP_DIR="/var/lib/story-sentinel/backups"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] SUCCESS: $1${NC}" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}" | tee -a "$LOG_FILE"
}

# Help function
show_help() {
    cat << EOF
Story Sentinel Upgrade Runner

Usage: $0 <command> <service> <version> [options]

Commands:
  upgrade    <service> <version>     Upgrade a service to specified version
  rollback   <service> <backup_id>   Rollback to a previous backup
  backup     <service>               Create backup of service
  verify     <service>               Verify service installation

Services:
  story      Story consensus node
  story_geth Story-Geth execution node

Examples:
  $0 upgrade story v1.2.1
  $0 upgrade story_geth v1.1.1
  $0 rollback story backup_20241201_120000
  $0 backup story

EOF
}

# Function to create backup
create_backup() {
    local service="$1"
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local backup_id="backup_${timestamp}"
    local backup_path="$BACKUP_DIR/${service}/${backup_id}"
    
    mkdir -p "$backup_path"
    
    log "Creating backup for $service..."
    
    case "$service" in
        "story")
            local binary_path="$STORY_BINARY"
            local service_name="$STORY_SERVICE"
            ;;
        "story_geth")
            local binary_path="$STORY_GETH_BINARY"
            local service_name="$STORY_GETH_SERVICE"
            ;;
        *)
            log_error "Unknown service: $service"
            exit 1
            ;;
    esac
    
    # Backup binary
    if [[ -f "$binary_path" ]]; then
        cp "$binary_path" "$backup_path/binary"
        log "Binary backed up: $binary_path"
    else
        log_error "Binary not found: $binary_path"
        exit 1
    fi
    
    # Get current version
    local current_version
    case "$service" in
        "story")
            current_version=$("$binary_path" version 2>/dev/null || echo "unknown")
            ;;
        "story_geth")
            current_version=$("$binary_path" version 2>/dev/null | grep -oP 'Version: \K[^,]+' || echo "unknown")
            ;;
    esac
    
    # Save metadata
    cat > "$backup_path/metadata.json" <<EOF
{
    "service": "$service",
    "binary_path": "$binary_path",
    "service_name": "$service_name",
    "version": "$current_version",
    "timestamp": "$timestamp",
    "backup_id": "$backup_id"
}
EOF
    
    log_success "Backup created: $backup_id"
    echo "$backup_id"
}

# Function to download binary
download_binary() {
    local service="$1"
    local version="$2"
    local temp_dir="/tmp/story-sentinel-upgrade-$$"
    
    mkdir -p "$temp_dir"
    
    case "$service" in
        "story")
            local url="https://github.com/piplabs/story/releases/download/${version}/story-linux-amd64"
            local binary_name="story"
            ;;
        "story_geth")
            local url="https://github.com/piplabs/story-geth/releases/download/${version}/geth-linux-amd64"
            local binary_name="geth"
            ;;
        *)
            log_error "Unknown service: $service"
            exit 1
            ;;
    esac
    
    log "Downloading $service $version from $url..."
    
    if curl -L -o "$temp_dir/$binary_name" "$url"; then
        chmod +x "$temp_dir/$binary_name"
        
        # Verify download
        if [[ -x "$temp_dir/$binary_name" ]]; then
            log_success "Download successful"
            echo "$temp_dir/$binary_name"
        else
            log_error "Downloaded binary is not executable"
            exit 1
        fi
    else
        log_error "Failed to download from $url"
        exit 1
    fi
}

# Function to perform upgrade
perform_upgrade() {
    local service="$1"
    local version="$2"
    
    log "Starting upgrade of $service to $version"
    
    # Load service configuration
    case "$service" in
        "story")
            local binary_path="$STORY_BINARY"
            local service_name="$STORY_SERVICE"
            ;;
        "story_geth")
            local binary_path="$STORY_GETH_BINARY"
            local service_name="$STORY_GETH_SERVICE"
            ;;
        *)
            log_error "Unknown service: $service"
            exit 1
            ;;
    esac
    
    # Create backup
    local backup_id
    backup_id=$(create_backup "$service")
    
    # Download new binary
    local new_binary
    new_binary=$(download_binary "$service" "$version")
    
    # Stop service
    log "Stopping $service_name service..."
    if systemctl stop "$service_name"; then
        log "Service stopped successfully"
    else
        log_error "Failed to stop service"
        exit 1
    fi
    
    # Replace binary
    log "Replacing binary..."
    if cp "$new_binary" "$binary_path"; then
        chmod +x "$binary_path"
        log "Binary replaced successfully"
    else
        log_error "Failed to replace binary"
        # Attempt rollback
        log "Attempting rollback..."
        cp "$BACKUP_DIR/${service}/${backup_id}/binary" "$binary_path"
        exit 1
    fi
    
    # Start service
    log "Starting $service_name service..."
    if systemctl start "$service_name"; then
        log "Service started successfully"
    else
        log_error "Failed to start service - attempting rollback"
        # Rollback
        cp "$BACKUP_DIR/${service}/${backup_id}/binary" "$binary_path"
        systemctl start "$service_name" || log_error "Rollback failed!"
        exit 1
    fi
    
    # Wait for service to be ready
    log "Waiting for service to be ready..."
    sleep 10
    
    # Verify upgrade
    if systemctl is-active --quiet "$service_name"; then
        # Verify version
        local new_version
        case "$service" in
            "story")
                new_version=$("$binary_path" version 2>/dev/null || echo "unknown")
                ;;
            "story_geth")
                new_version=$("$binary_path" version 2>/dev/null | grep -oP 'Version: \K[^,]+' || echo "unknown")
                ;;
        esac
        
        log_success "Upgrade completed successfully"
        log "New version: $new_version"
        log "Backup available: $backup_id"
        
        # Cleanup
        rm -rf "/tmp/story-sentinel-upgrade-$$"
        
    else
        log_error "Service is not running after upgrade - performing rollback"
        perform_rollback "$service" "$backup_id"
        exit 1
    fi
}

# Function to perform rollback
perform_rollback() {
    local service="$1"
    local backup_id="$2"
    local backup_path="$BACKUP_DIR/${service}/${backup_id}"
    
    log "Starting rollback of $service to $backup_id"
    
    if [[ ! -d "$backup_path" ]]; then
        log_error "Backup not found: $backup_path"
        exit 1
    fi
    
    # Load backup metadata
    if [[ -f "$backup_path/metadata.json" ]]; then
        local binary_path=$(grep -oP '"binary_path": "\K[^"]+' "$backup_path/metadata.json")
        local service_name=$(grep -oP '"service_name": "\K[^"]+' "$backup_path/metadata.json")
    else
        log_error "Backup metadata not found"
        exit 1
    fi
    
    # Stop service
    log "Stopping $service_name service..."
    systemctl stop "$service_name" || log_warning "Service may already be stopped"
    
    # Restore binary
    log "Restoring binary from backup..."
    if cp "$backup_path/binary" "$binary_path"; then
        chmod +x "$binary_path"
        log "Binary restored successfully"
    else
        log_error "Failed to restore binary"
        exit 1
    fi
    
    # Start service
    log "Starting $service_name service..."
    if systemctl start "$service_name"; then
        log_success "Rollback completed successfully"
    else
        log_error "Failed to start service after rollback"
        exit 1
    fi
}

# Function to verify installation
verify_installation() {
    local service="$1"
    
    case "$service" in
        "story")
            local binary_path="$STORY_BINARY"
            local service_name="$STORY_SERVICE"
            ;;
        "story_geth")
            local binary_path="$STORY_GETH_BINARY"
            local service_name="$STORY_GETH_SERVICE"
            ;;
        *)
            log_error "Unknown service: $service"
            exit 1
            ;;
    esac
    
    log "Verifying $service installation..."
    
    # Check binary exists and is executable
    if [[ -x "$binary_path" ]]; then
        log "✓ Binary found: $binary_path"
    else
        log_error "✗ Binary not found or not executable: $binary_path"
        exit 1
    fi
    
    # Check service status
    if systemctl is-active --quiet "$service_name"; then
        log "✓ Service is running: $service_name"
    else
        log_warning "✗ Service is not running: $service_name"
    fi
    
    # Check version
    local version
    case "$service" in
        "story")
            version=$("$binary_path" version 2>/dev/null || echo "unknown")
            ;;
        "story_geth")
            version=$("$binary_path" version 2>/dev/null | grep -oP 'Version: \K[^,]+' || echo "unknown")
            ;;
    esac
    
    log "✓ Current version: $version"
    log_success "Verification completed"
}

# Main execution
main() {
    # Ensure log directory exists
    mkdir -p "$(dirname "$LOG_FILE")"
    mkdir -p "$BACKUP_DIR"
    
    # Load environment variables from Story Sentinel config
    if [[ -f "/etc/story-sentinel/.env" ]]; then
        source "/etc/story-sentinel/.env"
    fi
    
    # Load configuration (these should be set by the calling Python script)
    if [[ -z "$STORY_BINARY" ]] || [[ -z "$STORY_GETH_BINARY" ]]; then
        log_error "Story binaries not configured. Please run through story-sentinel CLI."
        exit 1
    fi
    
    case "$1" in
        "upgrade")
            if [[ $# -lt 3 ]]; then
                log_error "Usage: $0 upgrade <service> <version>"
                exit 1
            fi
            perform_upgrade "$2" "$3"
            ;;
        "rollback")
            if [[ $# -lt 3 ]]; then
                log_error "Usage: $0 rollback <service> <backup_id>"
                exit 1
            fi
            perform_rollback "$2" "$3"
            ;;
        "backup")
            if [[ $# -lt 2 ]]; then
                log_error "Usage: $0 backup <service>"
                exit 1
            fi
            create_backup "$2"
            ;;
        "verify")
            if [[ $# -lt 2 ]]; then
                log_error "Usage: $0 verify <service>"
                exit 1
            fi
            verify_installation "$2"
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            log_error "Unknown command: $1"
            show_help
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"