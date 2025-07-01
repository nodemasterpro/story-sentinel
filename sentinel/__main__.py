"""CLI entry point for Story Sentinel."""

import os
import sys
import json
import logging
import asyncio
import signal
from pathlib import Path
from typing import Optional
import click
from datetime import datetime, timedelta

from . import __version__
from .config import Config
from .health import HealthChecker
from .watcher import VersionWatcher
from .runner import UpgradeRunner
from .scheduler import UpgradeScheduler

# Setup logging
def setup_logging(log_level: str, log_file: Optional[Path] = None):
    """Setup logging configuration."""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    handlers = [logging.StreamHandler(sys.stdout)]
    
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=handlers
    )

@click.group()
@click.version_option(version=__version__)
@click.option('--config', '-c', type=click.Path(exists=False), help='Config file path')
@click.option('--log-level', '-l', default='INFO', help='Log level')
@click.pass_context
def cli(ctx, config, log_level):
    """Story Sentinel - Automated monitoring and upgrade system for Story Protocol nodes."""
    # Setup logging
    setup_logging(log_level)
    
    # Load config
    config_path = Path(config) if config else None
    ctx.obj = Config(config_path=config_path)
    
    # Only validate config for commands that need it
    if ctx.invoked_subcommand not in ['init', 'version']:
        if not ctx.obj.validate():
            click.echo("Configuration validation failed", err=True)
            click.echo("Run 'story-sentinel init' to initialize configuration", err=True)
            sys.exit(1)

@cli.command()
@click.pass_obj
def status(config: Config):
    """Check current status of Story nodes."""
    health_checker = HealthChecker(config)
    
    click.echo("Story Sentinel Status")
    click.echo("=" * 80)
    
    # Get current versions
    versions = config.get_current_versions()
    click.echo(f"Story Version: {versions.get('story', 'unknown')}")
    click.echo(f"Story-Geth Version: {versions.get('story_geth', 'unknown')}")
    click.echo()
    
    # Check health
    health_status = health_checker.check_all()
    
    for service_name, status in health_status.items():
        icon = "✅" if status.healthy else "❌"
        click.echo(f"{icon} {service_name}: {'Healthy' if status.healthy else 'Unhealthy'}")
        
        if not status.healthy and status.message:
            click.echo(f"   Issue: {status.message}")
            
        # Show key metrics
        if service_name == 'story':
            click.echo(f"   Block Height: {status.checks.get('latest_block_height', 'N/A')}")
            click.echo(f"   Catching Up: {status.checks.get('catching_up', 'N/A')}")
            click.echo(f"   Peers: {status.checks.get('peer_count', 0)}")
        elif service_name == 'story_geth':
            click.echo(f"   Block Number: {status.checks.get('block_number', 'N/A')}")
            click.echo(f"   Syncing: {status.checks.get('syncing', 'N/A')}")
            click.echo(f"   Peers: {status.checks.get('peer_count', 0)}")
        elif service_name == 'system':
            click.echo(f"   CPU: {status.checks.get('cpu_percent', 0):.1f}%")
            click.echo(f"   Memory: {status.checks.get('memory_percent', 0):.1f}%")
            click.echo(f"   Disk Free: {status.checks.get('disk_free_gb', 0):.1f}GB")
            
        click.echo()
    
    # Check for issues
    issues = health_checker.detect_issues()
    if any(issues.values()):
        click.echo("⚠️  Detected Issues:")
        for issue, detected in issues.items():
            if detected:
                click.echo(f"   - {issue.replace('_', ' ').title()}")

@cli.command()
@click.pass_obj
def check_updates(config: Config):
    """Check for available updates."""
    watcher = VersionWatcher(config)
    
    click.echo("Checking for updates...")
    updates = watcher.check_for_updates()
    
    if not updates:
        click.echo("✅ All components are up to date!")
    else:
        click.echo("📦 Updates available:")
        for component, version in updates.items():
            current = config.get_current_versions().get(component, 'unknown')
            click.echo(f"\n{component}:")
            click.echo(f"  Current: {current}")
            click.echo(f"  Latest: {version.version}")
            click.echo(f"  Released: {version.published_at.strftime('%Y-%m-%d %H:%M UTC')}")
            if version.download_url:
                click.echo(f"  Download: {version.download_url}")

@cli.command()
@click.argument('component', type=click.Choice(['story', 'story_geth']))
@click.argument('version')
@click.option('--dry-run', is_flag=True, help='Simulate upgrade without making changes')
@click.option('--force', is_flag=True, help='Force upgrade even if checks fail')
@click.pass_obj
def upgrade(config: Config, component: str, version: str, dry_run: bool, force: bool):
    """Perform manual upgrade of a component."""
    runner = UpgradeRunner(config)
    watcher = VersionWatcher(config)
    
    # Get version info
    releases = watcher.get_all_releases(
        config.story.github_repo if component == 'story' else config.story_geth.github_repo
    )
    
    target_version = None
    for release in releases:
        if release.version == version or release.tag == version:
            target_version = release
            break
            
    if not target_version:
        click.echo(f"❌ Version {version} not found", err=True)
        return
        
    click.echo(f"Preparing to upgrade {component} to {target_version.version}")
    
    if not force:
        click.confirm("Do you want to proceed?", abort=True)
        
    # Perform upgrade
    success, message = runner.perform_upgrade(component, target_version, dry_run=dry_run)
    
    if success:
        click.echo(f"✅ {message}")
    else:
        click.echo(f"❌ {message}", err=True)
        sys.exit(1)

@cli.command()
@click.pass_obj
def schedule(config: Config):
    """View and manage upgrade schedule."""
    scheduler = UpgradeScheduler(config)
    
    click.echo(scheduler.get_schedule_summary())
    
    # Show calendar file location
    if scheduler.calendar_file.exists():
        click.echo(f"\n📅 Calendar file: {scheduler.calendar_file}")

@cli.command()
@click.argument('component', type=click.Choice(['story', 'story_geth']))
@click.argument('version')
@click.option('--time', help='Schedule time (YYYY-MM-DD HH:MM)')
@click.option('--auto-approve', is_flag=True, help='Auto-approve the upgrade')
@click.pass_obj
def schedule_upgrade(config: Config, component: str, version: str, time: Optional[str], auto_approve: bool):
    """Schedule an upgrade for later."""
    scheduler = UpgradeScheduler(config)
    watcher = VersionWatcher(config)
    
    # Get version info
    releases = watcher.get_all_releases(
        config.story.github_repo if component == 'story' else config.story_geth.github_repo
    )
    
    target_version = None
    for release in releases:
        if release.version == version or release.tag == version:
            target_version = release
            break
            
    if not target_version:
        click.echo(f"❌ Version {version} not found", err=True)
        return
        
    # Parse time
    scheduled_time = None
    if time:
        try:
            scheduled_time = datetime.strptime(time, "%Y-%m-%d %H:%M")
        except ValueError:
            click.echo("❌ Invalid time format. Use YYYY-MM-DD HH:MM", err=True)
            return
            
    # Schedule upgrade
    upgrade = scheduler.schedule_upgrade(component, target_version, scheduled_time, auto_approve)
    
    click.echo(f"✅ Scheduled {component} upgrade to {target_version.version}")
    click.echo(f"   Time: {upgrade.scheduled_time.strftime('%Y-%m-%d %H:%M UTC')}")
    click.echo(f"   Status: {upgrade.status}")

@cli.command()
@click.pass_obj
@click.option('--interval', '-i', default=300, help='Check interval in seconds')
@click.option('--once', is_flag=True, help='Run once and exit')
def monitor(config: Config, interval: int, once: bool):
    """Run continuous monitoring."""
    health_checker = HealthChecker(config)
    watcher = VersionWatcher(config)
    scheduler = UpgradeScheduler(config)
    runner = UpgradeRunner(config)
    
    async def monitoring_loop():
        """Main monitoring loop."""
        while True:
            try:
                # Check health
                health_status = health_checker.check_all()
                
                # Log any issues
                for service_name, status in health_status.items():
                    if not status.healthy:
                        logging.warning(f"{service_name} is unhealthy: {status.message}")
                        
                # Check for updates
                updates = watcher.check_for_updates()
                if updates:
                    for component, version in updates.items():
                        logging.info(f"Update available for {component}: {version.version}")
                        
                        # Auto-schedule if configured
                        if config.mode == 'auto' and watcher.should_auto_upgrade(version):
                            scheduler.schedule_upgrade(component, version, auto_approve=True)
                            
                # Check scheduled upgrades
                upcoming = scheduler.get_upcoming_upgrades(hours=1)
                for upgrade in upcoming:
                    if upgrade.status == 'approved' and upgrade.scheduled_time <= datetime.now():
                        logging.info(f"Executing scheduled upgrade: {upgrade.component} to {upgrade.target_version}")
                        
                        # Get version object
                        # TODO: Store version object in scheduled upgrade
                        
                        # Mark as completed
                        scheduler.mark_completed(upgrade.component, upgrade.target_version)
                        
                # Cleanup old backups
                runner.cleanup_old_backups()
                
                if once:
                    break
                    
                await asyncio.sleep(interval)
                
            except Exception as e:
                logging.error(f"Monitoring error: {e}")
                if once:
                    raise
                await asyncio.sleep(interval)
    
    # Setup signal handlers
    def signal_handler(sig, frame):
        logging.info("Received shutdown signal")
        sys.exit(0)
        
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run monitoring
    click.echo(f"Starting Story Sentinel monitoring (interval: {interval}s)")
    asyncio.run(monitoring_loop())

@cli.command()
@click.pass_obj
def init(config: Config):
    """Initialize Story Sentinel configuration."""
    click.echo("Initializing Story Sentinel...")
    
    # Create directories
    config.config_path.parent.mkdir(parents=True, exist_ok=True)
    config.backup_dir.mkdir(parents=True, exist_ok=True)
    config.log_dir.mkdir(parents=True, exist_ok=True)
    
    # Save default config
    config.save_yaml_config()
    
    # Create example env file
    env_example = """# Story Sentinel Configuration

# Discord webhook for notifications
DISCORD_WEBHOOK=https://discord.com/api/webhooks/...

# Telegram bot credentials
TG_BOT_TOKEN=123456:ABC-DEF...
TG_CHAT_ID=-1001234567890

# Operation mode: auto or manual
MODE=manual

# Log level: DEBUG, INFO, WARNING, ERROR
LOG_LEVEL=INFO

# Backup retention in days
BACKUP_RETENTION_DAYS=30

# Maximum upgrade duration in seconds
MAX_UPGRADE_DURATION=600

# Check interval in seconds
CHECK_INTERVAL=300

# Binary paths (optional, defaults to standard locations)
# STORY_BINARY_PATH=/usr/local/bin/story
# STORY_GETH_BINARY_PATH=/usr/local/bin/story-geth

# Story home directory
# STORY_HOME=/home/user/.story

# GitHub token for API rate limits (optional)
# GITHUB_TOKEN=ghp_...
"""
    
    env_example_path = config.env_path.with_suffix('.example')
    with open(env_example_path, 'w') as f:
        f.write(env_example)
        
    click.echo(f"✅ Created configuration directory: {config.config_path.parent}")
    click.echo(f"✅ Created config file: {config.config_path}")
    click.echo(f"✅ Created example env file: {env_example_path}")
    click.echo(f"\nNext steps:")
    click.echo(f"1. Copy {env_example_path} to {config.env_path}")
    click.echo(f"2. Edit {config.env_path} with your settings")
    click.echo(f"3. Run 'story-sentinel status' to check node health")

@cli.command()
@click.pass_obj
@click.option('--format', type=click.Choice(['json', 'text']), default='text')
def history(config: Config, format: str):
    """View upgrade history."""
    runner = UpgradeRunner(config)
    history = runner.get_upgrade_history(limit=20)
    
    if format == 'json':
        click.echo(json.dumps(history, indent=2))
    else:
        click.echo("Upgrade History")
        click.echo("=" * 80)
        
        if not history:
            click.echo("No upgrades recorded")
        else:
            for record in reversed(history):
                icon = "✅" if record['success'] else "❌"
                click.echo(f"\n{icon} {record['component']} upgrade on {record['start_time']}")
                click.echo(f"   From: {record['from_version']} → To: {record['to_version']}")
                if record.get('dry_run'):
                    click.echo("   Type: Dry Run")
                if not record['success'] and record.get('error'):
                    click.echo(f"   Error: {record['error']}")

if __name__ == '__main__':
    cli()