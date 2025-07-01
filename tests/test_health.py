"""Tests for health checking module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import psutil

from sentinel.config import Config
from sentinel.health import HealthChecker, HealthStatus


class TestHealthChecker:
    """Test health checking functionality."""
    
    @pytest.fixture
    def config(self):
        """Create test config."""
        return Config()
        
    @pytest.fixture
    def health_checker(self, config):
        """Create health checker instance."""
        return HealthChecker(config)
        
    def test_health_status_dataclass(self):
        """Test HealthStatus dataclass."""
        status = HealthStatus(
            healthy=True,
            service_name="test",
            checks={"check1": True},
            timestamp=datetime.now(),
            message="All good"
        )
        
        assert status.healthy is True
        assert status.service_name == "test"
        assert "check1" in status.checks
        assert status.message == "All good"
        
        # Test to_dict
        data = status.to_dict()
        assert data['healthy'] is True
        assert data['service_name'] == "test"
        assert isinstance(data['timestamp'], str)
        
    @patch('subprocess.run')
    @patch('requests.get')
    @patch('psutil.process_iter')
    def test_check_story_healthy(self, mock_process_iter, mock_requests, mock_subprocess):
        """Test Story health check when healthy."""
        # Mock systemctl check
        mock_subprocess.return_value = MagicMock(
            stdout='active',
            stderr='',
            returncode=0
        )
        
        # Mock RPC response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'result': {
                'sync_info': {
                    'catching_up': False,
                    'latest_block_height': '12345',
                    'latest_block_time': '2024-01-01T00:00:00Z'
                },
                'validator_info': {
                    'voting_power': '1000000'
                }
            }
        }
        mock_requests.return_value = mock_response
        
        # Mock process memory
        mock_process = MagicMock()
        mock_process.info = {
            'name': 'story',
            'memory_info': MagicMock(rss=1024*1024*1024)  # 1GB
        }
        mock_process_iter.return_value = [mock_process]
        
        config = Config()
        checker = HealthChecker(config)
        
        status = checker._check_story()
        
        assert status.healthy is True
        assert status.checks['service_running'] is True
        assert status.checks['rpc_responsive'] is True
        assert status.checks['catching_up'] is False
        assert status.checks['latest_block_height'] == 12345
        
    @patch('subprocess.run')
    @patch('requests.post')
    @patch('psutil.process_iter')
    def test_check_story_geth_syncing(self, mock_process_iter, mock_requests, mock_subprocess):
        """Test Story Geth health check when syncing."""
        # Mock systemctl check
        mock_subprocess.return_value = MagicMock(
            stdout='active',
            stderr='',
            returncode=0
        )
        
        # Mock RPC response - syncing
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'result': {
                'currentBlock': '0x1000',
                'highestBlock': '0x2000'
            }
        }
        mock_requests.return_value = mock_response
        
        # Mock process memory
        mock_process = MagicMock()
        mock_process.info = {
            'name': 'story-geth',
            'memory_info': MagicMock(rss=2*1024*1024*1024)  # 2GB
        }
        mock_process_iter.return_value = [mock_process]
        
        config = Config()
        checker = HealthChecker(config)
        
        status = checker._check_story_geth()
        
        assert status.healthy is False  # Not healthy while syncing
        assert status.checks['service_running'] is True
        assert status.checks['syncing'] is True
        assert status.checks['block_number'] == 0x1000
        assert "syncing" in status.message.lower()
        
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    def test_check_system_resources(self, mock_disk, mock_memory, mock_cpu):
        """Test system resource checking."""
        # Mock system metrics
        mock_cpu.return_value = 50.0
        mock_memory.return_value = MagicMock(
            percent=60.0,
            available=4*1024*1024*1024  # 4GB
        )
        mock_disk.return_value = MagicMock(
            percent=70.0,
            free=20*1024*1024*1024  # 20GB
        )
        
        config = Config()
        checker = HealthChecker(config)
        
        status = checker._check_system_resources()
        
        assert status.healthy is True
        assert status.checks['cpu_percent'] == 50.0
        assert status.checks['memory_percent'] == 60.0
        assert status.checks['memory_available_gb'] == 4.0
        assert status.checks['disk_free_gb'] == 20.0
        
    @patch('psutil.disk_usage')
    def test_check_system_low_disk(self, mock_disk):
        """Test system check with low disk space."""
        mock_disk.return_value = MagicMock(
            percent=95.0,
            free=5*1024*1024*1024  # 5GB
        )
        
        config = Config()
        config.thresholds.disk_space_min_gb = 10.0
        checker = HealthChecker(config)
        
        status = checker._check_system_resources()
        
        assert status.healthy is False
        assert "disk space" in status.message.lower()
        
    @patch('subprocess.run')
    def test_detect_app_hash_issues(self, mock_subprocess):
        """Test detection of app hash errors."""
        # Mock journal output with app hash error
        mock_subprocess.return_value = MagicMock(
            stdout='ERROR app hash mismatch detected',
            stderr='',
            returncode=0
        )
        
        config = Config()
        checker = HealthChecker(config)
        
        issues = checker.detect_issues()
        
        assert issues['app_hash_mismatch'] is True
        
    @patch('requests.post')
    @patch('requests.get')
    def test_get_sync_progress(self, mock_get, mock_post):
        """Test getting sync progress."""
        # Mock Geth response - synced
        geth_response = MagicMock()
        geth_response.json.return_value = {'result': False}  # Not syncing
        mock_post.return_value = geth_response
        
        # Mock Story response - catching up
        story_response = MagicMock()
        story_response.json.return_value = {
            'result': {
                'sync_info': {
                    'catching_up': True,
                    'earliest_block_height': '1000',
                    'latest_block_height': '5000'
                }
            }
        }
        mock_get.return_value = story_response
        
        config = Config()
        checker = HealthChecker(config)
        
        progress = checker.get_sync_progress()
        
        assert progress['story_geth']['synced'] is True
        assert progress['story_geth']['progress'] == 100.0
        assert progress['story']['synced'] is False
        assert progress['story']['progress'] < 100.0