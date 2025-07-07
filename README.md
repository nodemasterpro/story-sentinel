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

## Quick Start 🚀

**Prerequisites**: 
- Docker (20.10+) and Docker Compose (2.0+) installed
- Story Protocol node running and accessible
- `curl` for downloading configuration files

**Install Docker & Docker Compose** (if needed):
```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh
sudo usermod -aG docker $USER
# Log out and back in for group changes

# Verify installation
docker --version && docker compose version
```

1. **Setup files**:
```bash
# Download configuration template and docker-compose
curl -O https://raw.githubusercontent.com/nodemasterpro/story-sentinel/main/.env.docker
curl -O https://raw.githubusercontent.com/nodemasterpro/story-sentinel/main/docker-compose.yml
mv .env.docker .env
```

2. **Configure your setup** (edit `.env`):

**REQUIRED - Check your actual values:**
```bash
# Find your service names
systemctl list-units --type=service | grep -E '(story|geth)'

# Find your binary paths  
which story && which geth

# Find your RPC ports
netstat -tlnp | grep LISTEN | grep -E '(story|geth)'
```

**Then edit `.env`:**
```bash
# Your Story node RPC endpoints
SENTINEL_STORY_RPC=http://127.0.0.1:22657
SENTINEL_STORY_GETH_RPC=http://127.0.0.1:2245

# Your actual service names (CRITICAL - must match your installation)
SENTINEL_STORY_SERVICE=story-node
SENTINEL_GETH_SERVICE=geth-node

# Your actual binary paths
SENTINEL_STORY_BINARY=/root/go/bin/story
SENTINEL_GETH_BINARY=/root/go/bin/geth

# Choose one notification method
DISCORD_WEBHOOK=https://discord.com/api/webhooks/YOUR_WEBHOOK
# OR
TG_BOT_TOKEN=YOUR_BOT_TOKEN
TG_CHAT_ID=YOUR_CHAT_ID
```

3. **Start Story Sentinel**:
```bash
docker-compose up -d
```

4. **Verify it's working**:
```bash
# Health check
curl http://localhost:8080/health

# View status
docker-compose exec story-sentinel story-sentinel status
```

5. **Import calendar** (optional):
```bash
# Download upgrade calendar for your calendar app
curl http://localhost:8080/next-upgrade.ics -o story-upgrades.ics
# Import this file in Google Calendar, Outlook, Apple Calendar, etc.
```

### CLI Commands
```bash
# Check node status
docker-compose exec story-sentinel story-sentinel status

# Check for updates
docker-compose exec story-sentinel story-sentinel check-updates

# View scheduled upgrades
docker-compose exec story-sentinel story-sentinel schedule

# View logs
docker-compose logs -f story-sentinel
```

### Management Commands
```bash
# Stop
docker-compose down

# Update to latest version
docker-compose pull && docker-compose up -d

# View persistent data
docker volume inspect sentinel-data
```

## Custom Docker Build

If you want to build a custom image:

```bash
# Clone the repository
git clone https://github.com/nodemasterpro/story-sentinel.git
cd story-sentinel

# Build custom image
docker build -t my-story-sentinel:latest .

# Update docker-compose.yml to use your custom image
# Change: image: nodemasterpro/story-sentinel:latest
# To:     image: my-story-sentinel:latest

# Start with custom image
docker-compose up -d
```

## Configuration

### Configuration Files

With Docker, all configuration is managed through:
- `.env` - Environment variables (main configuration)
- `config.yaml` - Optional advanced configuration (auto-generated in Docker volume)
- Persistent data stored in `sentinel-data` Docker volume

**Configuration Priority**: Environment variables (`.env`) > `config.yaml` > auto-detection

### Essential Environment Variables (.env)

**Required variables:**
```env
# Story node RPC endpoints (replace with your node's IP/ports)
SENTINEL_STORY_RPC=http://10.0.0.100:22657
SENTINEL_STORY_GETH_RPC=http://10.0.0.100:2245

# Notifications (choose at least one)
DISCORD_WEBHOOK=https://discord.com/api/webhooks/YOUR_WEBHOOK
# OR
TG_BOT_TOKEN=YOUR_BOT_TOKEN
TG_CHAT_ID=YOUR_CHAT_ID

# Operation mode
MODE=manual  # or 'auto' for automatic patch updates
```

**Optional variables** (see `.env.docker` template for complete list):
```env
# Monitoring thresholds
SENTINEL_HEIGHT_GAP=20
SENTINEL_MIN_PEERS=5
SENTINEL_MEMORY_LIMIT_GB=8.0

# API configuration
SENTINEL_API_PORT=8080
SENTINEL_LOG_LEVEL=INFO
```

### Finding Your Node Endpoints

To find your Story node RPC ports:
```bash
# Check listening ports
netstat -tlnp | grep LISTEN | grep -E '(story|geth)'

# Common configurations:
# Story RPC: port 22657 or 26657
# Story-Geth RPC: port 2245 or 8545
```

### Common Port Configurations

| Installation Type | Story RPC | Story-Geth RPC |
|-------------------|-----------|----------------|
| Standard | `26657` | `8545` |
| NodeMaster/Custom | `22657` | `2245` |

**Use the correct ports for your setup in `SENTINEL_STORY_RPC` and `SENTINEL_STORY_GETH_RPC`**

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

## Advanced Usage

### Command Line Interface (via Docker)

All Story Sentinel commands are executed through the Docker container:

```bash
# Check node status
docker-compose exec story-sentinel story-sentinel status

# Check for available updates
docker-compose exec story-sentinel story-sentinel check-updates

# View upgrade schedule
docker-compose exec story-sentinel story-sentinel schedule

# Schedule an upgrade (manual mode only)
docker-compose exec story-sentinel story-sentinel schedule-upgrade story v1.3.0 --time "2024-01-15 02:00"

# Perform manual upgrade
docker-compose exec story-sentinel story-sentinel upgrade story v1.3.0

# View upgrade history
docker-compose exec story-sentinel story-sentinel history

# Initialize/reconfigure (if needed)
docker-compose exec story-sentinel story-sentinel init
```

**Note**: Configuration is automatically initialized on first start. Manual `init` is only needed for reconfiguration.

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

