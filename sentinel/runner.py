"""Upgrade runner module for executing Story node upgrades."""

import os
import shutil
import time
import json
import logging
import subprocess
import tempfile
import requests
from pathlib import Path
from typing import Dict, Optional, Tuple, List
from datetime import datetime, timedelta

from .config import Config
from .health import HealthChecker
from .watcher import Version

logger = logging.getLogger(__name__)

# Path to the upgrade runner script
UPGRADE_SCRIPT = "/opt/story-sentinel/scripts/upgrade-runner.sh"

class UpgradeRunner:
    """Executes upgrades for Story Protocol nodes."""
    
    def __init__(self, config: Config):
        self.config = config
        self.health_checker = HealthChecker(config)
        self.upgrade_log_file = config.log_dir / "upgrade_history.json"
        self.upgrade_history = self._load_upgrade_history()
        
    def _load_upgrade_history(self) -> List[Dict]:
        """Load upgrade history from file."""
        if self.upgrade_log_file.exists():
            try:
                with open(self.upgrade_log_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load upgrade history: {e}")
        return []
        
    def _save_upgrade_history(self):
        """Save upgrade history to file."""
        try:
            self.upgrade_log_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.upgrade_log_file, 'w') as f:
                json.dump(self.upgrade_history, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save upgrade history: {e}")
            
    def perform_upgrade(self, component: str, target_version: Version, 
                       dry_run: bool = False) -> Tuple[bool, str]:
        """Perform upgrade for specified component using native system upgrade."""
        upgrade_record = {
            'component': component,
            'from_version': self.config.get_current_versions().get(component, 'unknown'),
            'to_version': target_version.version,
            'start_time': datetime.now().isoformat(),
            'dry_run': dry_run,
            'success': False,
            'error': None
        }
        
        try:
            logger.info(f"Starting {'dry-run ' if dry_run else ''}upgrade of {component} to {target_version.version}")
            
            # Pre-upgrade checks
            if not self._pre_upgrade_checks(component):
                raise Exception("Pre-upgrade checks failed")
                
            if dry_run:
                logger.info("Dry run mode - skipping actual upgrade")
                upgrade_record['success'] = True
                return True, "Dry run completed successfully"
            
                
            # Use external upgrade script for native installation
            if os.path.exists(UPGRADE_SCRIPT):
                success, message = self._run_native_upgrade(component, target_version.version)
                if success:
                    upgrade_record['success'] = True
                    upgrade_record['end_time'] = datetime.now().isoformat()
                    logger.info(f"Successfully upgraded {component} to {target_version.version}")
                    return True, f"Successfully upgraded {component} to {target_version.version}"
                else:
                    raise Exception(message)
            else:
                # Fallback to built-in upgrade process (legacy)
                return self._perform_legacy_upgrade(component, target_version, upgrade_record)
                
        except Exception as e:
            upgrade_record['success'] = False
            upgrade_record['error'] = str(e)
            upgrade_record['end_time'] = datetime.now().isoformat()
            
            logger.error(f"Upgrade failed: {e}")
            return False, f"Upgrade failed: {e}"
            
        finally:
            # Save upgrade record
            self.upgrade_history.append(upgrade_record)
            self._save_upgrade_history()
            
    def _run_native_upgrade(self, component: str, version: str) -> Tuple[bool, str]:
        """Run upgrade using the native upgrade script."""
        try:
            # Set environment variables for the script
            env = os.environ.copy()
            env.update({
                'STORY_BINARY': self.config.story.binary_path,
                'STORY_GETH_BINARY': self.config.story_geth.binary_path,
                'STORY_SERVICE': self.config.story.service_name,
                'STORY_GETH_SERVICE': self.config.story_geth.service_name,
            })
            
            # Run the upgrade script
            logger.info(f"Executing native upgrade: {UPGRADE_SCRIPT} upgrade {component} {version}")
            result = subprocess.run(
                [UPGRADE_SCRIPT, 'upgrade', component, version],
                capture_output=True,
                text=True,
                env=env,
                timeout=1800  # 30 minutes timeout
            )
            
            if result.returncode == 0:
                logger.info(f"Native upgrade completed successfully: {result.stdout}")
                return True, "Upgrade completed successfully"
            else:
                logger.error(f"Native upgrade failed: {result.stderr}")
                return False, result.stderr or "Upgrade script failed"
                
        except subprocess.TimeoutExpired:
            logger.error("Upgrade script timed out")
            return False, "Upgrade timed out after 30 minutes"
        except Exception as e:
            logger.error(f"Failed to execute upgrade script: {e}")
            return False, f"Failed to execute upgrade script: {e}"
            
    def _pre_upgrade_checks(self, component: str) -> bool:
        """Perform pre-upgrade health checks."""
        logger.info(f"Running pre-upgrade checks for {component}")
        
        # Check system resources
        health_status = self.health_checker.check_all()
        system_health = health_status.get('system')
        
        if not system_health or not system_health.healthy:
            logger.error("System health check failed")
            return False
            
        # Check disk space
        if system_health.checks['disk_free_gb'] < 5.0:
            logger.error(f"Insufficient disk space: {system_health.checks['disk_free_gb']:.1f}GB")
            return False
            
        # Check if node is synced
        if component == 'story':
            story_health = health_status.get('story')
            if story_health and story_health.checks.get('catching_up', True):
                logger.warning("Story node is still syncing")
                # Allow upgrade anyway, but warn
                
        elif component == 'story_geth':
            geth_health = health_status.get('story_geth')
            if geth_health and geth_health.checks.get('syncing', True):
                logger.warning("Story Geth is still syncing")
                # Allow upgrade anyway, but warn
                
        return True
        
    def _perform_legacy_upgrade(self, component: str, target_version: Version, upgrade_record: dict) -> Tuple[bool, str]:
        """Legacy upgrade method for backward compatibility."""
        logger.warning("Using legacy upgrade method - consider using native installation for better reliability")
        
        try:
            # Create backup
            backup_path = self._create_backup(component)
            upgrade_record['backup_path'] = str(backup_path)
            
            # Download new binary
            binary_path = self._download_binary(component, target_version)
            if not binary_path:
                raise Exception("Failed to download binary")
                
            # Verify binary
            if not self._verify_binary(binary_path):
                raise Exception("Binary verification failed")
                
            # Stop service
            if not self._stop_service(component):
                raise Exception("Failed to stop service")
                
            # Replace binary
            if not self._replace_binary(component, binary_path):
                raise Exception("Failed to replace binary")
                
            # Start service
            if not self._start_service(component):
                # Attempt rollback
                logger.error("Failed to start service, attempting rollback")
                self._rollback(component, backup_path)
                raise Exception("Failed to start service after upgrade")
                
            # Post-upgrade verification
            if not self._post_upgrade_verification(component, target_version.version):
                logger.error("Post-upgrade verification failed, attempting rollback")
                self._rollback(component, backup_path)
                raise Exception("Post-upgrade verification failed")
                
            # Success
            upgrade_record['success'] = True
            upgrade_record['end_time'] = datetime.now().isoformat()
            
            return True, f"Successfully upgraded {component} to {target_version.version}"
            
        except Exception as e:
            return False, str(e)
        
    def _create_backup(self, component: str) -> Path:
        """Create backup of current binary and configuration."""
        logger.info(f"Creating backup for {component}")
        
        # Create backup directory
        backup_dir = self.config.backup_dir / f"{component}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Backup binary
        if component == 'story':
            binary_path = Path(self.config.story.binary_path)
        else:
            binary_path = Path(self.config.story_geth.binary_path)
            
        if binary_path.exists():
            shutil.copy2(binary_path, backup_dir / binary_path.name)
            
        # Backup configuration (for Story)
        if component == 'story':
            config_dir = self.config.story_home / 'story' / 'config'
            if config_dir.exists():
                shutil.copytree(config_dir, backup_dir / 'config')
                
        # Record backup metadata
        metadata = {
            'component': component,
            'timestamp': datetime.now().isoformat(),
            'version': self.config.get_current_versions().get(component, 'unknown')
        }
        
        with open(backup_dir / 'metadata.json', 'w') as f:
            json.dump(metadata, f, indent=2)
            
        logger.info(f"Backup created at {backup_dir}")
        return backup_dir
        
    def _download_binary(self, component: str, version: Version) -> Optional[Path]:
        """Download new binary."""
        logger.info(f"Downloading {component} version {version.version}")
        
        # Determine architecture
        arch = subprocess.run(['uname', '-m'], capture_output=True, text=True).stdout.strip()
        if arch == 'x86_64':
            arch = 'amd64'
        elif arch == 'aarch64':
            arch = 'arm64'
            
        # Construct download URL if not provided
        if not version.download_url:
            if component == 'story':
                version.download_url = f"https://github.com/piplabs/story/releases/download/{version.tag}/story_v{version.version}_linux_{arch}.tar.gz"
            else:
                version.download_url = f"https://github.com/piplabs/story-geth/releases/download/{version.tag}/geth_v{version.version}_linux_{arch}.tar.gz"
                
        try:
            # Download to temp directory
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                download_file = temp_path / f"{component}_{version.version}.tar.gz"
                
                # Download with progress
                response = requests.get(version.download_url, stream=True, timeout=30)
                response.raise_for_status()
                
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                
                with open(download_file, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                progress = (downloaded / total_size) * 100
                                logger.debug(f"Download progress: {progress:.1f}%")
                                
                # Extract binary
                extract_dir = temp_path / 'extracted'
                extract_dir.mkdir()
                
                subprocess.run(
                    ['tar', '-xzf', str(download_file), '-C', str(extract_dir)],
                    check=True
                )
                
                # Find the binary
                binary_name = 'story' if component == 'story' else 'geth'
                for root, dirs, files in os.walk(extract_dir):
                    if binary_name in files:
                        binary_path = Path(root) / binary_name
                        # Copy to a known location
                        final_path = temp_path / binary_name
                        shutil.copy2(binary_path, final_path)
                        # Make executable
                        final_path.chmod(0o755)
                        return final_path
                        
                logger.error(f"Binary {binary_name} not found in archive")
                return None
                
        except Exception as e:
            logger.error(f"Failed to download binary: {e}")
            
            # Fallback: try to build from source
            if component == 'story':
                return self._build_from_source(component, version)
            
            return None
            
    def _build_from_source(self, component: str, version: Version) -> Optional[Path]:
        """Build binary from source as fallback."""
        logger.info(f"Attempting to build {component} from source")
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Clone repository
                repo_url = f"https://github.com/{self.config.story.github_repo if component == 'story' else self.config.story_geth.github_repo}.git"
                
                subprocess.run(
                    ['git', 'clone', '--depth', '1', '--branch', version.tag, repo_url, str(temp_path / 'source')],
                    check=True,
                    timeout=300
                )
                
                # Build
                os.chdir(temp_path / 'source')
                
                if component == 'story':
                    subprocess.run(['go', 'build', '-o', 'story', './client'], check=True, timeout=600)
                    binary_path = temp_path / 'source' / 'story'
                else:
                    subprocess.run(['make', 'geth'], check=True, timeout=600)
                    binary_path = temp_path / 'source' / 'build' / 'bin' / 'geth'
                    
                if binary_path.exists():
                    # Copy to final location
                    final_path = temp_path / binary_path.name
                    shutil.copy2(binary_path, final_path)
                    final_path.chmod(0o755)
                    return final_path
                    
        except Exception as e:
            logger.error(f"Failed to build from source: {e}")
            
        return None
        
    def _verify_binary(self, binary_path: Path) -> bool:
        """Verify the downloaded binary."""
        logger.info("Verifying binary")
        
        try:
            # Check if binary is executable
            if not os.access(binary_path, os.X_OK):
                logger.error("Binary is not executable")
                return False
                
            # Try to get version
            result = subprocess.run(
                [str(binary_path), 'version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode != 0:
                logger.error(f"Binary version check failed: {result.stderr}")
                return False
                
            logger.info(f"Binary version output: {result.stdout}")
            
            # TODO: Verify SHA256 checksum if available
            
            return True
            
        except Exception as e:
            logger.error(f"Binary verification failed: {e}")
            return False
            
    def _stop_service(self, component: str) -> bool:
        """Stop the service."""
        service_name = self.config.story.service_name if component == 'story' else self.config.story_geth.service_name
        logger.info(f"Stopping service: {service_name}")
        
        try:
            # Stop service
            result = subprocess.run(
                ['sudo', 'systemctl', 'stop', service_name],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                logger.error(f"Failed to stop service: {result.stderr}")
                return False
                
            # Wait for service to fully stop
            time.sleep(5)
            
            # Verify it's stopped
            result = subprocess.run(
                ['systemctl', 'is-active', service_name],
                capture_output=True,
                text=True
            )
            
            if result.stdout.strip() == 'inactive':
                logger.info(f"Service {service_name} stopped successfully")
                return True
            else:
                logger.error(f"Service {service_name} is still active")
                return False
                
        except Exception as e:
            logger.error(f"Failed to stop service: {e}")
            return False
            
    def _replace_binary(self, component: str, new_binary_path: Path) -> bool:
        """Replace the old binary with the new one."""
        logger.info(f"Replacing {component} binary")
        
        try:
            if component == 'story':
                target_path = Path(self.config.story.binary_path)
            else:
                target_path = Path(self.config.story_geth.binary_path)
                
            # Create backup of current binary (additional safety)
            if target_path.exists():
                backup_path = target_path.with_suffix('.backup')
                shutil.copy2(target_path, backup_path)
                
            # Replace binary
            shutil.copy2(new_binary_path, target_path)
            
            # Ensure correct permissions
            target_path.chmod(0o755)
            
            logger.info(f"Binary replaced successfully at {target_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to replace binary: {e}")
            return False
            
    def _start_service(self, component: str) -> bool:
        """Start the service."""
        service_name = self.config.story.service_name if component == 'story' else self.config.story_geth.service_name
        logger.info(f"Starting service: {service_name}")
        
        try:
            # Start service
            result = subprocess.run(
                ['sudo', 'systemctl', 'start', service_name],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                logger.error(f"Failed to start service: {result.stderr}")
                return False
                
            # Wait for service to start
            time.sleep(10)
            
            # Verify it's running
            result = subprocess.run(
                ['systemctl', 'is-active', service_name],
                capture_output=True,
                text=True
            )
            
            if result.stdout.strip() == 'active':
                logger.info(f"Service {service_name} started successfully")
                return True
            else:
                logger.error(f"Service {service_name} is not active")
                return False
                
        except Exception as e:
            logger.error(f"Failed to start service: {e}")
            return False
            
    def _post_upgrade_verification(self, component: str, expected_version: str) -> bool:
        """Verify the upgrade was successful."""
        logger.info("Running post-upgrade verification")
        
        # Wait a bit for service to stabilize
        time.sleep(20)
        
        # Check version
        current_versions = self.config.get_current_versions()
        actual_version = current_versions.get(component, 'unknown')
        
        if expected_version not in actual_version:
            logger.error(f"Version mismatch: expected {expected_version}, got {actual_version}")
            return False
            
        # Check health
        health_status = self.health_checker.check_all()
        
        if component == 'story':
            component_health = health_status.get('story')
        else:
            component_health = health_status.get('story_geth')
            
        if not component_health:
            logger.error(f"No health data for {component}")
            return False
            
        # Allow some time for sync to catch up
        if not component_health.healthy:
            logger.warning(f"{component} not healthy yet, waiting...")
            time.sleep(30)
            
            # Check again
            health_status = self.health_checker.check_all()
            component_health = health_status.get(component)
            
        if component_health and component_health.checks.get('service_running'):
            logger.info(f"{component} is running with version {actual_version}")
            return True
        else:
            logger.error(f"{component} health check failed")
            return False
            
    def _rollback(self, component: str, backup_path: Path) -> bool:
        """Rollback to previous version."""
        logger.info(f"Attempting rollback for {component}")
        
        try:
            # Stop service
            self._stop_service(component)
            
            # Restore binary
            if component == 'story':
                target_path = Path(self.config.story.binary_path)
            else:
                target_path = Path(self.config.story_geth.binary_path)
                
            backup_binary = backup_path / target_path.name
            if backup_binary.exists():
                shutil.copy2(backup_binary, target_path)
                target_path.chmod(0o755)
                
            # Start service
            if self._start_service(component):
                logger.info("Rollback completed successfully")
                return True
            else:
                logger.error("Failed to start service after rollback")
                return False
                
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False
            
    def cleanup_old_backups(self, days: int = None):
        """Clean up old backup directories."""
        if days is None:
            days = self.config.backup_retention_days
            
        cutoff = datetime.now() - timedelta(days=days)
        
        try:
            for backup_dir in self.config.backup_dir.iterdir():
                if backup_dir.is_dir():
                    # Check metadata
                    metadata_file = backup_dir / 'metadata.json'
                    if metadata_file.exists():
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)
                        timestamp = datetime.fromisoformat(metadata['timestamp'])
                        
                        if timestamp < cutoff:
                            logger.info(f"Removing old backup: {backup_dir}")
                            shutil.rmtree(backup_dir)
                            
        except Exception as e:
            logger.error(f"Failed to cleanup backups: {e}")
            
    def get_upgrade_history(self, limit: int = 10) -> List[Dict]:
        """Get recent upgrade history."""
        return self.upgrade_history[-limit:]