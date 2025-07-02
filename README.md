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

### Prerequisites

- Ubuntu 22.04 LTS
- Python 3.10+
- systemd
- Story Protocol node already installed
- sudo access for service management

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/story-sentinel.git
cd story-sentinel
```

2. Run the installation script:
```bash
cd scripts
sudo ./install.sh
```

3. Configure Story Sentinel:
```bash
# Copy and edit the configuration
sudo cp /etc/story-sentinel/.env.example /etc/story-sentinel/.env
sudo nano /etc/story-sentinel/.env
```

4. Start the service:
```bash
sudo systemctl start story-sentinel
sudo systemctl enable story-sentinel
```

## Configuration

### Environment Variables (.env)

```env
# Notifications
DISCORD_WEBHOOK=https://discord.com/api/webhooks/...
TG_BOT_TOKEN=123456:ABC-DEF...
TG_CHAT_ID=-1001234567890

# Operation mode
MODE=manual  # or 'auto' for automatic patch updates

# Paths (usually auto-detected)
STORY_HOME=/home/story/.story
```

### Configuration File (config.yaml)

```yaml
story:
  binary_path: /usr/local/bin/story
  service_name: story
  rpc_port: 26657
  
story_geth:
  binary_path: /usr/local/bin/story-geth
  service_name: story-geth
  rpc_port: 8545
  
thresholds:
  height_gap: 20
  min_peers: 5
  disk_space_min_gb: 10.0
```

## Usage

### Command Line Interface

```bash
# Check node status
story-sentinel status

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
   
   # Verify configuration
   sudo -u story-sentinel story-sentinel status
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
   # Fix permissions
   sudo chown -R story-sentinel:story-sentinel /opt/story-sentinel
   sudo chown -R story-sentinel:story-sentinel /var/log/story-sentinel
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

- Run with minimal privileges (dedicated user)
- Secure configuration files (chmod 600)
- Use environment variables for secrets
- Enable systemd security features
- Regular backup retention cleanup
- Binary signature verification

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

Made with ❤️ for the Story Protocol validator community