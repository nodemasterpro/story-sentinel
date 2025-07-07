"""Configuration management for Story Sentinel."""

import os
import yaml
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

@dataclass
class ServiceConfig:
    """Configuration for a single service (Story or Story-Geth)."""
    binary_path: str
    service_name: str
    rpc_port: int
    version_command: str = "--version"
    github_repo: str = ""
    current_version: Optional[str] = None

@dataclass
class ThresholdConfig:
    """Threshold configuration for health checks."""
    height_gap: int = 20
    min_peers: int = 5
    block_time_variance: int = 10
    memory_limit_gb: float = 8.0
    disk_space_min_gb: float = 10.0

@dataclass
class NotificationConfig:
    """Notification configuration."""
    discord_webhook: Optional[str] = None
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    
class Config:
    """Main configuration class for Story Sentinel."""
    
    DEFAULT_CONFIG_PATH = Path.home() / ".story-sentinel" / "config.yaml"
    DEFAULT_ENV_PATH = Path.home() / ".story-sentinel" / ".env"
    
    def __init__(self, config_path: Optional[Path] = None, env_path: Optional[Path] = None):
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self.env_path = env_path or self.DEFAULT_ENV_PATH
        
        # Load environment variables
        if self.env_path.exists():
            load_dotenv(self.env_path)
        
        # Initialize configurations with environment priority
        self.story: ServiceConfig = ServiceConfig(
            binary_path=os.getenv("STORY_BINARY_PATH", "/usr/local/bin/story"),
            service_name=os.getenv("STORY_SERVICE_NAME", "story"),
            rpc_port=int(os.getenv("STORY_RPC_PORT", "26657")),
            github_repo="piplabs/story"
        )
        
        self.story_geth: ServiceConfig = ServiceConfig(
            binary_path=os.getenv("STORY_GETH_BINARY_PATH", "/usr/local/bin/story-geth"),
            service_name=os.getenv("STORY_GETH_SERVICE_NAME", "story-geth"),
            rpc_port=int(os.getenv("STORY_GETH_RPC_PORT", "8545")),
            version_command="version",
            github_repo="piplabs/story-geth"
        )
        
        self.thresholds = ThresholdConfig(
            height_gap=int(os.getenv("SENTINEL_HEIGHT_GAP", "20")),
            min_peers=int(os.getenv("SENTINEL_MIN_PEERS", "5")),
            block_time_variance=int(os.getenv("SENTINEL_BLOCK_TIME_VARIANCE", "10")),
            memory_limit_gb=float(os.getenv("SENTINEL_MEMORY_LIMIT_GB", "8.0")),
            disk_space_min_gb=float(os.getenv("SENTINEL_DISK_SPACE_MIN_GB", "10.0"))
        )
        self.notifications = NotificationConfig(
            discord_webhook=os.getenv("DISCORD_WEBHOOK"),
            telegram_bot_token=os.getenv("TG_BOT_TOKEN"),
            telegram_chat_id=os.getenv("TG_CHAT_ID")
        )
        
        # General settings with environment priority
        self.mode = os.getenv("MODE", "manual")  # auto|manual
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.backup_retention_days = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))
        self.max_upgrade_duration = int(os.getenv("MAX_UPGRADE_DURATION", "600"))
        self.check_interval = int(os.getenv("CHECK_INTERVAL", "300"))
        self.update_check_interval = int(os.getenv("UPDATE_CHECK_INTERVAL", "3600"))
        self.api_host = os.getenv("API_HOST", "0.0.0.0")
        self.api_port = int(os.getenv("API_PORT", "8080"))
        self.calendar_name = os.getenv("CALENDAR_NAME", "Story Sentinel Upgrades")
        
        # Paths configuration
        data_dir = Path(os.getenv("DATA_DIR", Path.home() / ".story-sentinel"))
        self.story_home = Path(os.getenv("STORY_HOME", Path.home() / ".story"))
        self.backup_dir = Path(os.getenv("BACKUP_DIR", "/var/lib/story-sentinel/backups"))
        self.log_dir = Path(os.getenv("LOG_DIR", "/var/log/story-sentinel"))
        self.db_path = Path(os.getenv("DB_PATH", data_dir / "sentinel.db"))
        
        # RPC endpoints
        self.story_rpc_endpoint = f"http://localhost:{self.story.rpc_port}"
        self.story_geth_rpc_endpoint = f"http://localhost:{self.story_geth.rpc_port}"
        
        # Load YAML config if exists
        if self.config_path.exists():
            self.load_yaml_config()
            
    def load_yaml_config(self):
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, 'r') as f:
                data = yaml.safe_load(f)
                
            # Update Story configuration (only if not overridden by environment)
            if 'story' in data:
                story_data = data['story']
                if not os.getenv("SENTINEL_STORY_BINARY"):
                    self.story.binary_path = story_data.get('binary_path', self.story.binary_path)
                if not os.getenv("SENTINEL_STORY_SERVICE"):
                    self.story.service_name = story_data.get('service_name', self.story.service_name)
                if not os.getenv("SENTINEL_STORY_RPC_PORT"):
                    self.story.rpc_port = story_data.get('rpc_port', self.story.rpc_port)
                self.story.github_repo = story_data.get('github_repo', self.story.github_repo)
                
            # Update Story-Geth configuration (only if not overridden by environment)
            if 'story_geth' in data:
                geth_data = data['story_geth']
                if not os.getenv("SENTINEL_GETH_BINARY"):
                    self.story_geth.binary_path = geth_data.get('binary_path', self.story_geth.binary_path)
                if not os.getenv("SENTINEL_GETH_SERVICE"):
                    self.story_geth.service_name = geth_data.get('service_name', self.story_geth.service_name)
                if not os.getenv("SENTINEL_GETH_RPC_PORT"):
                    self.story_geth.rpc_port = geth_data.get('rpc_port', self.story_geth.rpc_port)
                self.story_geth.github_repo = geth_data.get('github_repo', self.story_geth.github_repo)
                
            # Update thresholds (only if not overridden by environment)
            if 'thresholds' in data:
                thresh_data = data['thresholds']
                if not os.getenv("SENTINEL_HEIGHT_GAP"):
                    self.thresholds.height_gap = thresh_data.get('height_gap', self.thresholds.height_gap)
                if not os.getenv("SENTINEL_MIN_PEERS"):
                    self.thresholds.min_peers = thresh_data.get('min_peers', self.thresholds.min_peers)
                if not os.getenv("SENTINEL_BLOCK_TIME_VARIANCE"):
                    self.thresholds.block_time_variance = thresh_data.get('block_time_variance', 
                                                                         self.thresholds.block_time_variance)
                if not os.getenv("SENTINEL_MEMORY_LIMIT_GB"):
                    self.thresholds.memory_limit_gb = thresh_data.get('memory_limit_gb', 
                                                                      self.thresholds.memory_limit_gb)
                if not os.getenv("SENTINEL_DISK_SPACE_MIN_GB"):
                    self.thresholds.disk_space_min_gb = thresh_data.get('disk_space_min_gb',
                                                                        self.thresholds.disk_space_min_gb)
                
            logger.info(f"Loaded configuration from {self.config_path}")
            
        except Exception as e:
            logger.error(f"Failed to load YAML config: {e}")
            
    def save_yaml_config(self):
        """Save current configuration to YAML file."""
        config_data = {
            'story': {
                'binary_path': self.story.binary_path,
                'service_name': self.story.service_name,
                'rpc_port': self.story.rpc_port,
                'github_repo': self.story.github_repo,
            },
            'story_geth': {
                'binary_path': self.story_geth.binary_path,
                'service_name': self.story_geth.service_name,
                'rpc_port': self.story_geth.rpc_port,
                'github_repo': self.story_geth.github_repo,
            },
            'thresholds': {
                'height_gap': self.thresholds.height_gap,
                'min_peers': self.thresholds.min_peers,
                'block_time_variance': self.thresholds.block_time_variance,
                'memory_limit_gb': self.thresholds.memory_limit_gb,
                'disk_space_min_gb': self.thresholds.disk_space_min_gb,
            }
        }
        
        # Create directory if needed
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save with atomic write
        temp_path = self.config_path.with_suffix('.tmp')
        try:
            with open(temp_path, 'w') as f:
                yaml.dump(config_data, f, default_flow_style=False)
            temp_path.replace(self.config_path)
            logger.info(f"Saved configuration to {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            if temp_path.exists():
                temp_path.unlink()
                
    def get_current_versions(self) -> Dict[str, str]:
        """Get current installed versions of Story components."""
        versions = {}
        
        # Get Story version
        try:
            result = os.popen(f"{self.story.binary_path} version 2>/dev/null").read().strip()
            self.story.current_version = result
            versions['story'] = result
        except Exception as e:
            logger.error(f"Failed to get Story version: {e}")
            versions['story'] = "unknown"
            
        # Get Story-Geth version
        try:
            result = os.popen(f"{self.story_geth.binary_path} version 2>/dev/null").read().strip()
            # Parse geth version output
            if "Version:" in result:
                version_line = [l for l in result.split('\n') if 'Version:' in l][0]
                self.story_geth.current_version = version_line.split('Version:')[1].strip()
            else:
                self.story_geth.current_version = result
            versions['story_geth'] = self.story_geth.current_version
        except Exception as e:
            logger.error(f"Failed to get Story-Geth version: {e}")
            versions['story_geth'] = "unknown"
            
        return versions
    
    def validate(self) -> bool:
        """Validate configuration."""
        errors = []
        
        # Check binary paths
        if not Path(self.story.binary_path).exists():
            errors.append(f"Story binary not found at {self.story.binary_path}")
        if not Path(self.story_geth.binary_path).exists():
            errors.append(f"Story-Geth binary not found at {self.story_geth.binary_path}")
            
        # Check Story home directory
        if not self.story_home.exists():
            errors.append(f"Story home directory not found at {self.story_home}")
            
        # Validate mode
        if self.mode not in ['auto', 'manual']:
            errors.append(f"Invalid mode: {self.mode} (must be 'auto' or 'manual')")
            
        # Log errors
        if errors:
            for error in errors:
                logger.error(error)
            return False
            
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'story': {
                'binary_path': self.story.binary_path,
                'service_name': self.story.service_name,
                'rpc_port': self.story.rpc_port,
                'current_version': self.story.current_version,
            },
            'story_geth': {
                'binary_path': self.story_geth.binary_path,
                'service_name': self.story_geth.service_name,
                'rpc_port': self.story_geth.rpc_port,
                'current_version': self.story_geth.current_version,
            },
            'thresholds': {
                'height_gap': self.thresholds.height_gap,
                'min_peers': self.thresholds.min_peers,
                'block_time_variance': self.thresholds.block_time_variance,
                'memory_limit_gb': self.thresholds.memory_limit_gb,
                'disk_space_min_gb': self.thresholds.disk_space_min_gb,
            },
            'mode': self.mode,
            'log_level': self.log_level,
            'backup_retention_days': self.backup_retention_days,
            'max_upgrade_duration': self.max_upgrade_duration,
        }