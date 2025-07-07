# Story Sentinel v1.1

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

Story Sentinel is a production-ready automated monitoring and upgrade system for Story Protocol validator nodes. It provides health monitoring, automated version tracking, scheduled upgrades, and comprehensive alerting.

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

## Quick Start

### Option 1: Docker (Recommended) 🐳

**Prerequisites**: Docker installed and Story node running

1. **Download and setup**:
```bash
curl -O https://raw.githubusercontent.com/nodemasterpro/story-sentinel/main/.env.docker
mv .env.docker .env
```

2. **Configure essentials** (edit `.env`):
```bash
# Your Story node RPC endpoints (replace IP with your node)
SENTINEL_STORY_RPC=http://10.0.0.100:22657
SENTINEL_STORY_GETH_RPC=http://10.0.0.100:2245

# Choose one notification method
DISCORD_WEBHOOK=https://discord.com/api/webhooks/YOUR_WEBHOOK
# OR
TG_BOT_TOKEN=YOUR_BOT_TOKEN
TG_CHAT_ID=YOUR_CHAT_ID
```

3. **Run Story Sentinel**:
```bash
docker run -d --name story-sentinel \
  --env-file .env \
  -p 8080:8080 \
  -v sentinel-data:/data \
  --restart unless-stopped \
  nodemasterpro/story-sentinel:latest
```

4. **Health check**:
```bash
curl http://localhost:8080/health
```

5. **Import calendar** (upgrades in your calendar app):
```bash
curl http://localhost:8080/next-upgrade.ics -o story-upgrades.ics
# Import this file in Google Calendar, Outlook, etc.
```

**CLI commands via Docker**:
```bash
# Check status
docker exec story-sentinel story-sentinel status

# Check for updates
docker exec story-sentinel story-sentinel check-updates

# View upgrade schedule
docker exec story-sentinel story-sentinel schedule
```

### Option 2: Native Installation

**Prerequisites**: Ubuntu 22.04 LTS, Python 3.10+, systemd, sudo access

1. Clone and install:
```bash
git clone https://github.com/nodemasterpro/story-sentinel.git
cd story-sentinel && cd scripts && sudo ./install.sh
```

2. Configure:
```bash
story-sentinel init  # Auto-detect your setup
sudo nano /etc/story-sentinel/config.yaml  # Fine-tune if needed
sudo nano /etc/story-sentinel/.env  # Add Discord/Telegram
```

3. Start service:
```bash
sudo systemctl start story-sentinel && sudo systemctl enable story-sentinel
```

## Configuration

### Configuration Locations

Story Sentinel stores configuration files in `/etc/story-sentinel/`:
- `config.yaml` - Main configuration file
- `.env` - Environment variables and secrets

**Note**: Use `story-sentinel init` to automatically detect your node setup and create the initial configuration.

### Environment Variables (.env)

```env
# Notifications
DISCORD_WEBHOOK=https://discord.com/api/webhooks/...
TG_BOT_TOKEN=123456:ABC-DEF...
TG_CHAT_ID=-1001234567890

# Operation mode
MODE=manual  # or 'auto' for automatic patch updates

# Paths (auto-detected by init command)
STORY_HOME=/root/.story
```

### Configuration File (config.yaml)

**Important**: Service names and binary paths vary depending on your installation method. Use `story-sentinel init` for automatic detection, or manually adjust based on your setup:

```yaml
story:
  binary_path: /usr/local/bin/story  # or /root/go/bin/story
  service_name: story-node           # or 'story' depending on setup
  rpc_port: 22657                   # Story RPC port (check with netstat)
  home: /root/.story                 # Story data directory
  github_repo: piplabs/story
  
story_geth:
  binary_path: /usr/local/bin/geth   # or /root/go/bin/geth
  service_name: geth-node            # or 'story-geth' depending on setup
  rpc_port: 2245                    # Story-Geth RPC port
  github_repo: piplabs/story-geth
  
thresholds:
  height_gap: 20
  min_peers: 5
  block_time_variance: 10
  memory_limit_gb: 8.0
  disk_space_min_gb: 10.0
```

#### Finding Your Service Names

To check your actual service names:
```bash
systemctl list-units --type=service | grep -E '(story|geth)'
```

#### Finding Your RPC Ports

To check which ports your nodes are listening on:
```bash
netstat -tlnp | grep LISTEN | grep -E '(story|geth)'
```

### Common Configuration Variations

Different Story node installation methods result in different configurations:

#### Standard Installation
```yaml
story:
  service_name: story
  rpc_port: 26657
story_geth:
  service_name: story-geth
  rpc_port: 8545
```

#### NodeMaster/Custom Installation
```yaml
story:
  service_name: story-node
  rpc_port: 22657
story_geth:
  service_name: geth-node
  rpc_port: 2245
```

**Always run `story-sentinel init` to auto-detect your specific setup.**

## Notifications Setup 🔔

### Discord Webhook
1. Go to your Discord server → Server Settings → Integrations → Webhooks
2. Create New Webhook → Choose channel → Copy Webhook URL
3. Add to `.env`: `DISCORD_WEBHOOK=https://discord.com/api/webhooks/...`

### Telegram Bot
1. Message [@BotFather](https://t.me/botfather) → `/newbot` → Choose name
2. Get your bot token and start a chat with your bot
3. Get your chat ID: Message [@userinfobot](https://t.me/userinfobot) or check `https://api.telegram.org/bot<TOKEN>/getUpdates`
4. Add to `.env`:
   ```
   TG_BOT_TOKEN=123456789:ABC-DEFGHIJKLMNOPQRSTUVWXYZabcdefghijk
   TG_CHAT_ID=-1001234567890
   ```

### Calendar Integration (iCS)
Story Sentinel generates calendar files for upgrade scheduling:
- **URL**: `http://your-server:8080/next-upgrade.ics`
- **Google Calendar**: Add by URL in "Other calendars"
- **Outlook**: Subscribe to calendar → From web
- **Apple Calendar**: File → New Calendar Subscription

## Docker Compose (Alternative) 📋

Create `docker-compose.yml`:
```yaml
version: '3.8'
services:
  story-sentinel:
    image: nodemasterpro/story-sentinel:latest
    container_name: story-sentinel
    restart: unless-stopped
    env_file: .env
    volumes:
      - sentinel-data:/data
    ports:
      - "8080:8080"
    network_mode: host

volumes:
  sentinel-data:
```

Run with: `docker-compose up -d`

## Usage

### Command Line Interface

```bash
# Initialize configuration (run once after installation)
story-sentinel init

# Check node status
story-sentinel status
# Or with specific config file:
story-sentinel --config /etc/story-sentinel/config.yaml status

# Check for updates
story-sentinel check-updates

# View upgrade schedule
story-sentinel schedule

# Schedule an upgrade
story-sentinel schedule-upgrade story v1.3.0 --time "2024-01-15 02:00"

# Perform manual upgrade
story-sentinel upgrade story v1.3.0

# View upgrade history
story-sentinel history

# Run monitoring (usually done by systemd)
story-sentinel monitor
```

### Monitoring Endpoints

- **Health Check**: `http://localhost:8080/health`
- **Node Status**: `http://localhost:8080/status`
- **Upgrade Schedule**: `http://localhost:8080/schedule`
- **Calendar (ICS)**: `http://localhost:8080/next-upgrade.ics`
- **Prometheus Metrics**: `http://localhost:8080/metrics`

## Upgrade Process

1. **Pre-upgrade Checks**:
   - System resources (CPU, memory, disk)
   - Node sync status
   - Service health

2. **Backup Creation**:
   - Current binary backup
   - Configuration backup
   - Metadata recording

3. **Binary Download**:
   - Download from GitHub releases
   - Fallback to source compilation
   - SHA256 verification

4. **Service Management**:
   - Graceful service stop
   - Binary replacement
   - Service restart

5. **Post-upgrade Verification**:
   - Version verification
   - Service health check
   - Automatic rollback on failure

## Safety Features

- **Automatic Backups**: Before each upgrade
- **Health Checks**: Pre and post upgrade verification
- **Rollback**: Automatic rollback on upgrade failure
- **Rate Limiting**: GitHub API rate limiting
- **Notification**: Real-time alerts for issues

## Troubleshooting

### Common Issues

1. **Service won't start**:
   ```bash
   # Check logs
   sudo journalctl -u story-sentinel -f
   
   # Verify configuration is loaded correctly
   story-sentinel --config /etc/story-sentinel/config.yaml status
   
   # Check if service is using correct config file
   cat /etc/systemd/system/story-sentinel.service | grep ExecStart
   ```

2. **Configuration validation errors**:
   ```bash
   # Re-run init to detect current setup
   story-sentinel init
   
   # Check service names
   systemctl list-units --type=service | grep -E '(story|geth)'
   
   # Check RPC ports
   netstat -tlnp | grep LISTEN | grep -E '(story|geth)'
   
   # Verify binary paths
   which story && which geth
   ```

2. **Upgrade failures**:
   ```bash
   # Check upgrade history
   story-sentinel history
   
   # Manual rollback if needed
   sudo /opt/story-sentinel/scripts/runner.sh rollback story /path/to/backup
   ```

3. **Calendar integration**:
   ```bash
   # Download calendar file for external apps
   curl http://localhost:8080/next-upgrade.ics -o story-upgrades.ics
   
   # Or serve via Nginx for team access
   # Add to nginx config:
   # location /story-calendar.ics {
   #     proxy_pass http://localhost:8080/next-upgrade.ics;
   # }
   ```

4. **Permission issues**:
   ```bash
   # The service runs as root to access node directories
   # Ensure config files are readable
   sudo chmod 644 /etc/story-sentinel/config.yaml
   sudo chmod 600 /etc/story-sentinel/.env  # Keep secrets private
   
   # For systemd service access to /root directory:
   # The service uses ProtectHome=false to access /root/.story
   ```

5. **SystemD service configuration**:
   ```bash
   # Ensure the service uses the correct config file
   sudo systemctl edit story-sentinel --full
   # Verify ExecStart line includes: --config /etc/story-sentinel/config.yaml
   
   # Reload systemd after changes
   sudo systemctl daemon-reload
   sudo systemctl restart story-sentinel
   ```

### Logs

- **Main service**: `sudo journalctl -u story-sentinel -f`
- **Upgrade logs**: `/var/log/story-sentinel/runner.log`
- **Application logs**: `/var/log/story-sentinel/sentinel.log`

## Development

### Project Structure

```
story-sentinel/
├── sentinel/
│   ├── __init__.py
│   ├── __main__.py      # CLI entry point
│   ├── config.py        # Configuration management
│   ├── health.py        # Health monitoring
│   ├── watcher.py       # Version tracking
│   ├── scheduler.py     # Upgrade scheduling
│   ├── runner.py        # Upgrade execution
│   └── api.py          # HTTP endpoints
├── scripts/
│   ├── install.sh       # Installation script
│   ├── runner.sh        # Bash upgrade wrapper
│   └── systemd/         # Service definitions
├── config/
│   ├── config.yaml.example
│   └── .env.example
├── tests/
└── docs/
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

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## Security Considerations

- Service runs as root to access node data directories
- Secure configuration files (chmod 644 for config.yaml, 600 for .env)
- Use environment variables for secrets (.env file)
- SystemD security features enabled (except ProtectHome=false for /root access)
- Regular backup retention cleanup
- Binary signature verification
- Configuration stored in system directory (/etc/story-sentinel/)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Story Protocol team for the blockchain platform
- Contributors and testers
- Open source dependencies

## Support

- **Issues**: [GitHub Issues](https://github.com/nodemasterpro/story-sentinel/issues)
- **Discussions**: [GitHub Discussions](https://github.com/nodemasterpro/story-sentinel/discussions)
- **Security**: security@nodesforall.com

---

