# Story Sentinel v1.2

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

Story Sentinel is a production-ready automated monitoring and upgrade system for Story Protocol validator nodes. It provides comprehensive health monitoring, automated version tracking, scheduled upgrades, and real-time alerting.

## Features

- **🔍 Health Monitoring**: Continuous monitoring of Story and Story-Geth nodes
- **📦 Version Tracking**: Automatic detection of new releases on GitHub
- **🔄 Automated Upgrades**: Safe, automated upgrade process with rollback capability
- **📅 Scheduling**: Plan upgrades with ICS calendar integration
- **🔔 Notifications**: Discord and Telegram alerts for important events
- **🛡️ Safety Features**: Pre-upgrade checks, backups, and automatic rollback
- **📊 Metrics**: Prometheus-compatible metrics endpoint
- **🔐 Security**: Binary verification, secure configuration, minimal privileges

## Architecture

Story Sentinel monitors both components of a Story Protocol node:
- **Story**: The consensus layer (Tendermint-based)
- **Story-Geth**: The execution layer (modified Ethereum client)

## Quick Start 🚀

### Prerequisites

- **Ubuntu/Debian server** with Story Protocol installed and running
- **Root access** for installation
- **Story services** operational: `story` and `story-geth` (or variants)

### One-Command Installation

```bash
# Download and run quick installation (requires root/sudo)
curl -sSL https://raw.githubusercontent.com/nodemasterpro/story-sentinel/main/quick-start.sh | sudo bash
```

The installer automatically detects:
- ✅ Story binaries (`/usr/local/bin/story`, `/root/go/bin/story`)
- ✅ Systemd services (`story`, `story-node`, `story-geth`)
- ✅ RPC ports (26657, 22657 for Story / 8545, 2245 for Geth)
- ✅ Story home directory (`/root/.story`)

### Manual Installation

```bash
# Clone repository
git clone https://github.com/nodemasterpro/story-sentinel.git
cd story-sentinel

# Run installer
sudo bash install.sh

# Configure notifications
sudo nano /etc/story-sentinel/.env

# Start service
sudo systemctl start story-sentinel
```

## Configuration

### Notification Setup

Edit `/etc/story-sentinel/.env` to configure notifications:

```bash
# Discord Webhook
DISCORD_WEBHOOK=https://discord.com/api/webhooks/YOUR_WEBHOOK

# OR Telegram Bot
TG_BOT_TOKEN=123456789:ABC-DEFGHIJKLMNOPQRSTUVWXYZabcdefghijk
TG_CHAT_ID=-1001234567890

# Operation mode
MODE=manual  # or 'auto' for automatic patch updates
```

### Service Configuration

Story Sentinel automatically detects your installation, but you can override settings:

```bash
# Story Node Configuration
STORY_BINARY_PATH=/usr/local/bin/story
STORY_SERVICE_NAME=story
STORY_RPC_PORT=26657

# Story-Geth Configuration  
STORY_GETH_BINARY_PATH=/usr/local/bin/story-geth
STORY_GETH_SERVICE_NAME=story-geth
STORY_GETH_RPC_PORT=8545
```

### Finding Your Configuration

```bash
# Check your Story services
systemctl list-units --type=service | grep -E '(story|geth)'

# Check RPC ports
netstat -tlnp | grep -E '(story|geth|26657|22657|8545|2245)'

# Check binary locations
which story && which story-geth
```

## Usage

### CLI Commands

```bash
# Check node status
story-sentinel status

# Check for available updates
story-sentinel check-updates

# Perform manual upgrade (version without 'v' prefix)
story-sentinel upgrade story 1.2.1
story-sentinel upgrade story_geth 1.1.1

# View upgrade history
story-sentinel history

# Schedule an upgrade
story-sentinel schedule-upgrade story 1.2.1 --time "2025-01-15 02:00"

# View scheduled upgrades
story-sentinel schedule

# Cancel a scheduled upgrade (by index number)
story-sentinel cancel-upgrade 1

# Test notifications
story-sentinel test-notifications
```

### Service Management

```bash
# Control the service
sudo systemctl start|stop|restart|status story-sentinel

# View logs in real-time
sudo journalctl -u story-sentinel -f

# View API logs
sudo journalctl -u story-sentinel-api -f

# Reload configuration
sudo systemctl reload story-sentinel
```

### API Endpoints

The monitoring API is available on `http://localhost:8080` (via `story-sentinel-api` service):

```bash
# General health
curl http://localhost:8080/health

# Detailed status
curl http://localhost:8080/status

# Upgrade calendar (iCS)
curl http://localhost:8080/next-upgrade.ics

# Prometheus metrics
curl http://localhost:8080/metrics
```

## Upgrade Process

### Safety and Verification

1. **Pre-Upgrade Checks**:
   - System health (CPU, RAM, disk)
   - Node synchronization status
   - Available resources

2. **Automatic Backup**:
   - Current binary copies
   - Version metadata
   - Timestamped for traceability

3. **Download and Verification**:
   - Download from GitHub releases
   - Integrity verification
   - Execution testing

4. **Secure Upgrade**:
   - Graceful service shutdown
   - Binary replacement
   - Controlled restart

5. **Post-Upgrade Verification**:
   - Functionality testing
   - Version verification
   - Automatic rollback on failure

### Operation Modes

#### Manual Mode (Recommended)
- Notifications of available updates
- Upgrades on explicit command
- Full administrator control

#### Automatic Mode
- Automatic patch updates
- Pre/post notifications
- Automatic rollback on issues

### Rollback Management

```bash
# View available backups
ls /var/lib/story-sentinel/backups/

# Manual rollback to a backup
story-sentinel rollback story backup_20241201_120000

# Automatic rollback triggers on upgrade failure
```

## Notification Setup

### Discord Webhook

1. Go to: Server Settings → Integrations → Webhooks
2. Create New Webhook → Choose channel → Copy Webhook URL
3. Add to `/etc/story-sentinel/.env`: `DISCORD_WEBHOOK=https://discord.com/api/webhooks/...`

### Telegram Bot

1. Message [@BotFather](https://t.me/botfather) → `/newbot` → Choose name
2. Get your bot token and start a chat with your bot
3. Get your chat ID: Message [@userinfobot](https://t.me/userinfobot)
4. Configure in `/etc/story-sentinel/.env`

### Testing Notifications

After configuring Discord/Telegram, test your setup:

```bash
# Test both Discord and Telegram notifications
story-sentinel test-notifications
```

This will send a test message to verify your configuration is working correctly.

## Calendar Integration

Story Sentinel generates iCS calendar files compatible with:

- **Google Calendar**: Add by URL
- **Outlook**: Subscribe to calendar (full compatibility with UID and UTC timestamps)
- **Apple Calendar**: Calendar subscription
- **Any RFC 5545 compliant calendar application**

### Calendar File Locations

```bash
# Local calendar file
/var/log/story-sentinel/upgrade_calendar.ics

# HTTP endpoint
http://your-server:8080/next-upgrade.ics

# Download calendar file
curl -o story-upgrades.ics http://localhost:8080/next-upgrade.ics
```

## Monitoring and Alerts

### Monitored Metrics

| Component | Metrics | Thresholds |
|-----------|---------|------------|
| **Story** | Block height, peers, sync | > 5 peers, sync OK |
| **Story-Geth** | Block number, peers, sync | > 5 peers, sync OK |
| **System** | CPU, RAM, disk | < 90% CPU, > 2GB RAM |

### Alert Types

- 🔴 **Critical**: Service stopped, fatal error
- 🟡 **Warning**: Low peers, limited resources
- 🟢 **Info**: Update available, successful upgrade

## Configuration Files

| File | Description |
|------|-------------|
| `/etc/story-sentinel/config.yaml` | Main configuration (auto-generated) |
| `/etc/story-sentinel/.env` | Environment variables |
| `/etc/systemd/system/story-sentinel.service` | Systemd service |

## Advanced Configuration

### Environment Variables

```bash
# Operation mode
MODE=manual              # or 'auto' for automatic upgrades

# Check intervals (seconds)
CHECK_INTERVAL=300       # Health check
UPDATE_CHECK_INTERVAL=3600  # Update check

# Alert thresholds
MIN_PEERS=5              # Minimum peer count
MEMORY_LIMIT_GB=8.0      # Memory limit
DISK_SPACE_MIN_GB=10.0   # Minimum disk space

# API configuration
API_HOST=0.0.0.0         # Listen interface
API_PORT=8080            # API port
```

## Troubleshooting

### Common Issues

1. **Service won't start**:
```bash
# Check logs for both services
sudo journalctl -u story-sentinel -f
sudo journalctl -u story-sentinel-api -f

# Verify configuration
story-sentinel status

# Fix timestamp parsing errors
sudo bash repair-server.sh
```

2. **Auto-detection failed**:
```bash
# Check Story services
sudo systemctl list-units --type=service | grep -E '(story|geth)'

# Manually edit configuration
sudo nano /etc/story-sentinel/.env
```

3. **Upgrade fails**:
```bash
# Check disk space
df -h

# Check GitHub connectivity
curl -I https://github.com/piplabs/story/releases

# View detailed logs
tail -f /var/log/story-sentinel/upgrade.log
```

4. **Permission issues**:
```bash
# Fix file permissions
sudo chown -R root:root /opt/story-sentinel
sudo chmod +x /opt/story-sentinel/scripts/upgrade-runner.sh
```

### Logs and Diagnostics

```bash
# Main logs
sudo journalctl -u story-sentinel -f

# Upgrade logs
tail -f /var/log/story-sentinel/upgrade.log

# Application logs
tail -f /var/log/story-sentinel/sentinel.log

# Detailed system status
story-sentinel status --verbose
```

## Testing Installation

```bash
# Run installation tests
sudo bash test-installation.sh

# Test individual components
story-sentinel status
curl http://localhost:8080/health
```

## Uninstall

### Complete Uninstallation

Use our uninstall script for a complete and clean removal:

```bash
# Download and run uninstall script
curl -sSL https://raw.githubusercontent.com/nodemasterpro/story-sentinel/main/uninstall.sh | sudo bash
```

Or if you have the repository cloned:

```bash
sudo bash uninstall.sh
```

The uninstaller will:
- ✅ Stop and disable all Story Sentinel services
- ✅ Remove application files from `/opt/story-sentinel`
- ✅ Optionally preserve configuration, backups, and logs
- ✅ Clean up systemd services and CLI wrapper
- ✅ **NOT affect your Story or Story-Geth nodes**

### Manual Uninstallation

If you prefer to uninstall manually:

```bash
# Stop and disable services
sudo systemctl stop story-sentinel story-sentinel-api
sudo systemctl disable story-sentinel story-sentinel-api

# Remove files
sudo rm -rf /opt/story-sentinel
sudo rm -rf /etc/story-sentinel
sudo rm -rf /var/lib/story-sentinel
sudo rm -rf /var/log/story-sentinel
sudo rm /etc/systemd/system/story-sentinel.service
sudo rm /etc/systemd/system/story-sentinel-api.service
sudo rm /usr/local/bin/story-sentinel

# Reload systemd
sudo systemctl daemon-reload
```

## Security

### Best Practices

- ✅ Service runs as root (required for systemctl)
- ✅ Protected configuration files (644/600)
- ✅ Binary integrity verification
- ✅ Automatic backups before upgrades
- ✅ Automatic rollback on failure
- ✅ Detailed logging of all operations

### File Permissions

```bash
# Secure secrets
sudo chmod 600 /etc/story-sentinel/.env

# Read-only configuration
sudo chmod 644 /etc/story-sentinel/config.yaml
```

## Development

### Project Structure

```
story-sentinel/
├── sentinel/            # Main application
│   ├── __main__.py     # CLI entry point
│   ├── config.py       # Configuration management
│   ├── health.py       # Health monitoring
│   ├── watcher.py      # Version tracking
│   ├── scheduler.py    # Upgrade scheduling
│   ├── runner.py       # Upgrade execution
│   └── api.py          # HTTP endpoints
├── scripts/
│   └── upgrade-runner.sh # System upgrade script
├── install.sh          # Installation script
├── quick-start.sh      # Quick installation
└── test-installation.sh # Installation tests
```

### Running Tests

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/

# Run with coverage
pytest --cov=sentinel tests/
```

## Support

- **Issues**: [GitHub Issues](https://github.com/nodemasterpro/story-sentinel/issues)
- **Discussions**: [GitHub Discussions](https://github.com/nodemasterpro/story-sentinel/discussions)
- **Documentation**: [Project Wiki](https://github.com/nodemasterpro/story-sentinel/wiki)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Story Protocol team for the blockchain platform
- Contributors and testers
- Open source community

---

**🚀 Story Sentinel - Automated Monitoring and Upgrade System for Story Protocol**