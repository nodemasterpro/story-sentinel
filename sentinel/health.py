"""Health check module for Story Protocol nodes."""

import os
import json
import time
import psutil
import logging
import requests
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

from .config import Config

logger = logging.getLogger(__name__)

@dataclass
class HealthStatus:
    """Health status for a service."""
    healthy: bool
    service_name: str
    checks: Dict[str, Any]
    timestamp: datetime
    message: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'healthy': self.healthy,
            'service_name': self.service_name,
            'checks': self.checks,
            'timestamp': self.timestamp.isoformat(),
            'message': self.message
        }

class HealthChecker:
    """Health checker for Story Protocol nodes."""
    
    def __init__(self, config: Config):
        self.config = config
        self.last_block_times = {}
        self.consecutive_failures = {}
        
    def check_all(self) -> Dict[str, HealthStatus]:
        """Run all health checks and return status."""
        statuses = {}
        
        # Check Story Geth first (dependency)
        statuses['story_geth'] = self._check_story_geth()
        
        # Check Story consensus
        statuses['story'] = self._check_story()
        
        # Check system resources
        statuses['system'] = self._check_system_resources()
        
        return statuses
        
    def _check_story_geth(self) -> HealthStatus:
        """Check Story Geth health."""
        checks = {
            'service_running': False,
            'rpc_responsive': False,
            'syncing': None,
            'peer_count': 0,
            'block_number': 0,
            'memory_usage_mb': 0
        }
        
        service_name = self.config.story_geth.service_name
        
        # Check if service is running (skip in Docker mode)
        docker_mode = os.getenv('DOCKER_MODE')
        if not docker_mode:
            try:
                result = subprocess.run(
                    ['systemctl', 'is-active', service_name],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                checks['service_running'] = result.stdout.strip() == 'active'
            except Exception as e:
                logger.error(f"Failed to check {service_name} service status: {e}")
        else:
            # In Docker mode, assume service is running if RPC responds
            checks['service_running'] = True
            
        # Check RPC endpoint
        if checks['service_running']:
            try:
                # Get sync status
                response = requests.post(
                    self.config.story_geth_rpc_endpoint,
                    json={"jsonrpc": "2.0", "method": "eth_syncing", "params": [], "id": 1},
                    timeout=5
                )
                data = response.json()
                
                if 'result' in data:
                    checks['rpc_responsive'] = True
                    if isinstance(data['result'], dict):
                        checks['syncing'] = True
                        checks['block_number'] = int(data['result'].get('currentBlock', '0x0'), 16)
                    else:
                        checks['syncing'] = False
                        # Get current block
                        block_resp = requests.post(
                            self.config.story_geth_rpc_endpoint,
                            json={"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1},
                            timeout=5
                        )
                        block_data = block_resp.json()
                        if 'result' in block_data:
                            checks['block_number'] = int(block_data['result'], 16)
                            
                # Get peer count
                peer_resp = requests.post(
                    self.config.story_geth_rpc_endpoint,
                    json={"jsonrpc": "2.0", "method": "net_peerCount", "params": [], "id": 1},
                    timeout=5
                )
                peer_data = peer_resp.json()
                if 'result' in peer_data:
                    checks['peer_count'] = int(peer_data['result'], 16)
                    
            except Exception as e:
                logger.error(f"Failed to check Story Geth RPC: {e}")
                
        # Get memory usage
        try:
            for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
                if service_name in proc.info['name']:
                    checks['memory_usage_mb'] = proc.info['memory_info'].rss / 1024 / 1024
                    break
        except Exception as e:
            logger.error(f"Failed to check memory usage: {e}")
            
        # Determine overall health
        healthy = (
            checks['service_running'] and
            checks['rpc_responsive'] and
            checks['peer_count'] >= self.config.thresholds.min_peers and
            not checks['syncing']  # Not healthy if still syncing
        )
        
        message = ""
        if not checks['service_running']:
            message = f"{service_name} service is not running"
        elif not checks['rpc_responsive']:
            message = f"{service_name} RPC is not responsive"
        elif checks['syncing']:
            message = f"{service_name} is still syncing (block {checks['block_number']})"
        elif checks['peer_count'] < self.config.thresholds.min_peers:
            message = f"{service_name} has low peer count: {checks['peer_count']}"
            
        return HealthStatus(
            healthy=healthy,
            service_name=service_name,
            checks=checks,
            timestamp=datetime.now(),
            message=message
        )
        
    def _check_story(self) -> HealthStatus:
        """Check Story consensus health."""
        checks = {
            'service_running': False,
            'rpc_responsive': False,
            'catching_up': None,
            'latest_block_height': 0,
            'latest_block_time': None,
            'voting_power': 0,
            'peer_count': 0,
            'memory_usage_mb': 0,
            'app_hash_errors': 0
        }
        
        service_name = self.config.story.service_name
        
        # Check if service is running (skip in Docker mode)
        docker_mode = os.getenv('DOCKER_MODE')
        if not docker_mode:
            try:
                result = subprocess.run(
                    ['systemctl', 'is-active', service_name],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                checks['service_running'] = result.stdout.strip() == 'active'
            except Exception as e:
                logger.error(f"Failed to check {service_name} service status: {e}")
        else:
            # In Docker mode, assume service is running if RPC responds
            checks['service_running'] = True
            
        # Check RPC endpoint
        if checks['service_running']:
            try:
                # Get status
                response = requests.get(
                    f"{self.config.story_rpc_endpoint}/status",
                    timeout=5
                )
                data = response.json()
                
                if 'result' in data:
                    checks['rpc_responsive'] = True
                    result = data['result']
                    
                    # Extract key metrics
                    checks['catching_up'] = result['sync_info']['catching_up']
                    checks['latest_block_height'] = int(result['sync_info']['latest_block_height'])
                    checks['latest_block_time'] = result['sync_info']['latest_block_time']
                    
                    # Check if we have voting power (validator)
                    if 'validator_info' in result:
                        checks['voting_power'] = int(result['validator_info']['voting_power'])
                        
                # Get net info for peer count
                net_resp = requests.get(
                    f"{self.config.story_rpc_endpoint}/net_info",
                    timeout=5
                )
                net_data = net_resp.json()
                if 'result' in net_data:
                    checks['peer_count'] = len(net_data['result']['peers'])
                    
            except Exception as e:
                logger.error(f"Failed to check Story RPC: {e}")
                
        # Check for app hash errors in logs
        try:
            # Check last 100 lines of journal for app hash errors
            result = subprocess.run(
                ['journalctl', '-u', service_name, '-n', '100', '--no-pager'],
                capture_output=True,
                text=True,
                timeout=5
            )
            checks['app_hash_errors'] = result.stdout.count('app hash')
        except Exception as e:
            logger.error(f"Failed to check logs: {e}")
            
        # Get memory usage
        try:
            for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
                if 'story' in proc.info['name'] and 'geth' not in proc.info['name']:
                    checks['memory_usage_mb'] = proc.info['memory_info'].rss / 1024 / 1024
                    break
        except Exception as e:
            logger.error(f"Failed to check memory usage: {e}")
            
        # Check block production rate
        block_time_healthy = True
        if checks['latest_block_time'] and service_name in self.last_block_times:
            last_time = self.last_block_times[service_name]
            current_time = datetime.fromisoformat(checks['latest_block_time'].replace('Z', '+00:00'))
            time_diff = (current_time - last_time).total_seconds()
            
            if time_diff > self.config.thresholds.block_time_variance:
                block_time_healthy = False
                
        # Update last block time
        if checks['latest_block_time']:
            self.last_block_times[service_name] = datetime.fromisoformat(
                checks['latest_block_time'].replace('Z', '+00:00')
            )
            
        # Determine overall health
        healthy = (
            checks['service_running'] and
            checks['rpc_responsive'] and
            not checks['catching_up'] and
            checks['peer_count'] >= self.config.thresholds.min_peers and
            checks['app_hash_errors'] == 0 and
            block_time_healthy
        )
        
        message = ""
        if not checks['service_running']:
            message = f"{service_name} service is not running"
        elif not checks['rpc_responsive']:
            message = f"{service_name} RPC is not responsive"
        elif checks['catching_up']:
            message = f"{service_name} is catching up (height {checks['latest_block_height']})"
        elif checks['peer_count'] < self.config.thresholds.min_peers:
            message = f"{service_name} has low peer count: {checks['peer_count']}"
        elif checks['app_hash_errors'] > 0:
            message = f"{service_name} has app hash errors"
        elif not block_time_healthy:
            message = f"{service_name} has slow block production"
            
        return HealthStatus(
            healthy=healthy,
            service_name=service_name,
            checks=checks,
            timestamp=datetime.now(),
            message=message
        )
        
    def _check_system_resources(self) -> HealthStatus:
        """Check system resources."""
        checks = {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'memory_available_gb': psutil.virtual_memory().available / 1024 / 1024 / 1024,
            'disk_usage_percent': 0,
            'disk_free_gb': 0,
            'load_average': os.getloadavg()
        }
        
        # Check disk usage for Story home
        try:
            disk_usage = psutil.disk_usage(str(self.config.story_home))
            checks['disk_usage_percent'] = disk_usage.percent
            checks['disk_free_gb'] = disk_usage.free / 1024 / 1024 / 1024
        except Exception as e:
            logger.error(f"Failed to check disk usage: {e}")
            
        # Determine health
        healthy = (
            checks['memory_available_gb'] > 2.0 and  # At least 2GB free
            checks['disk_free_gb'] > self.config.thresholds.disk_space_min_gb and
            checks['cpu_percent'] < 90.0
        )
        
        message = ""
        if checks['memory_available_gb'] < 2.0:
            message = f"Low memory: {checks['memory_available_gb']:.1f}GB available"
        elif checks['disk_free_gb'] < self.config.thresholds.disk_space_min_gb:
            message = f"Low disk space: {checks['disk_free_gb']:.1f}GB free"
        elif checks['cpu_percent'] > 90.0:
            message = f"High CPU usage: {checks['cpu_percent']:.1f}%"
            
        return HealthStatus(
            healthy=healthy,
            service_name='system',
            checks=checks,
            timestamp=datetime.now(),
            message=message
        )
        
    def get_sync_progress(self) -> Dict[str, Any]:
        """Get sync progress for both services."""
        progress = {
            'story_geth': {'synced': False, 'progress': 0.0},
            'story': {'synced': False, 'progress': 0.0}
        }
        
        # Check Story Geth sync
        try:
            response = requests.post(
                self.config.story_geth_rpc_endpoint,
                json={"jsonrpc": "2.0", "method": "eth_syncing", "params": [], "id": 1},
                timeout=5
            )
            data = response.json()
            
            if 'result' in data:
                if isinstance(data['result'], dict):
                    current = int(data['result'].get('currentBlock', '0x0'), 16)
                    highest = int(data['result'].get('highestBlock', '0x0'), 16)
                    if highest > 0:
                        progress['story_geth']['progress'] = (current / highest) * 100
                else:
                    progress['story_geth']['synced'] = True
                    progress['story_geth']['progress'] = 100.0
        except Exception as e:
            logger.error(f"Failed to check Story Geth sync: {e}")
            
        # Check Story sync
        try:
            response = requests.get(
                f"{self.config.story_rpc_endpoint}/status",
                timeout=5
            )
            data = response.json()
            
            if 'result' in data:
                catching_up = data['result']['sync_info']['catching_up']
                progress['story']['synced'] = not catching_up
                progress['story']['progress'] = 0.0 if catching_up else 100.0
                
                # Try to estimate progress if catching up
                if catching_up:
                    earliest = int(data['result']['sync_info'].get('earliest_block_height', 0))
                    latest = int(data['result']['sync_info'].get('latest_block_height', 0))
                    # This is a rough estimate
                    if latest > earliest:
                        progress['story']['progress'] = min(99.0, (latest - earliest) / 1000000 * 100)
                        
        except Exception as e:
            logger.error(f"Failed to check Story sync: {e}")
            
        return progress
        
    def detect_issues(self) -> Dict[str, Any]:
        """Detect common issues that might require intervention."""
        issues = {
            'app_hash_mismatch': False,
            'state_corruption': False,
            'peer_isolation': False,
            'memory_leak': False,
            'disk_space_critical': False
        }
        
        # Check for app hash mismatch
        try:
            result = subprocess.run(
                ['journalctl', '-u', self.config.story.service_name, '-n', '1000', '--no-pager'],
                capture_output=True,
                text=True,
                timeout=5
            )
            log_content = result.stdout
            
            # Look for app hash errors
            if 'app hash' in log_content or 'AppHash' in log_content:
                issues['app_hash_mismatch'] = True
                
            # Look for state corruption indicators
            if 'panic' in log_content or 'corruption' in log_content:
                issues['state_corruption'] = True
                
        except Exception as e:
            logger.error(f"Failed to check logs for issues: {e}")
            
        # Check for peer isolation
        statuses = self.check_all()
        if 'story' in statuses:
            peer_count = statuses['story'].checks.get('peer_count', 0)
            if peer_count < 3:
                issues['peer_isolation'] = True
                
        # Check for memory leak
        for service in ['story', 'story_geth']:
            status = statuses.get(service)
            if status:
                memory_mb = status.checks.get('memory_usage_mb', 0)
                if memory_mb > self.config.thresholds.memory_limit_gb * 1024:
                    issues['memory_leak'] = True
                    break
                    
        # Check disk space
        system_status = statuses.get('system')
        if system_status:
            disk_free = system_status.checks.get('disk_free_gb', 0)
            if disk_free < 5.0:  # Less than 5GB is critical
                issues['disk_space_critical'] = True
                
        return issues