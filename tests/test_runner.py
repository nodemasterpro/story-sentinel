"""Tests for upgrade runner module."""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path
import tempfile
import shutil

from sentinel.config import Config
from sentinel.runner import UpgradeRunner
from sentinel.watcher import Version
from datetime import datetime


class TestUpgradeRunner:
    """Test upgrade execution functionality."""
    
    @pytest.fixture
    def config(self):
        """Create test config."""
        config = Config()
        # Use temp directories
        with tempfile.TemporaryDirectory() as tmpdir:
            config.backup_dir = Path(tmpdir) / "backups"
            config.log_dir = Path(tmpdir) / "logs"
            config.backup_dir.mkdir(parents=True)
            config.log_dir.mkdir(parents=True)
            yield config
            
    @pytest.fixture
    def runner(self, config):
        """Create runner instance."""
        return UpgradeRunner(config)
        
    @patch('sentinel.runner.UpgradeRunner._pre_upgrade_checks')
    @patch('sentinel.runner.UpgradeRunner._create_backup')
    @patch('sentinel.runner.UpgradeRunner._download_binary')
    @patch('sentinel.runner.UpgradeRunner._verify_binary')
    @patch('sentinel.runner.UpgradeRunner._stop_service')
    @patch('sentinel.runner.UpgradeRunner._replace_binary')
    @patch('sentinel.runner.UpgradeRunner._start_service')
    @patch('sentinel.runner.UpgradeRunner._post_upgrade_verification')
    def test_perform_upgrade_success(self, mock_post_verify, mock_start, mock_replace,
                                   mock_stop, mock_verify, mock_download, 
                                   mock_backup, mock_pre_check, config):
        """Test successful upgrade flow."""
        # Setup mocks
        mock_pre_check.return_value = True
        mock_backup.return_value = Path("/backup/path")
        mock_download.return_value = Path("/tmp/new_binary")
        mock_verify.return_value = True
        mock_stop.return_value = True
        mock_replace.return_value = True
        mock_start.return_value = True
        mock_post_verify.return_value = True
        
        runner = UpgradeRunner(config)
        version = Version('v1.3.0', '1.3.0', datetime.now())
        
        success, message = runner.perform_upgrade('story', version)
        
        assert success is True
        assert "Successfully upgraded" in message
        
        # Verify all steps were called
        mock_pre_check.assert_called_once_with('story')
        mock_backup.assert_called_once_with('story')
        mock_download.assert_called_once_with('story', version)
        mock_verify.assert_called_once()
        mock_stop.assert_called_once_with('story')
        mock_replace.assert_called_once()
        mock_start.assert_called_once_with('story')
        mock_post_verify.assert_called_once()
        
    @patch('sentinel.runner.UpgradeRunner._pre_upgrade_checks')
    def test_perform_upgrade_pre_check_fail(self, mock_pre_check, config):
        """Test upgrade failure at pre-check stage."""
        mock_pre_check.return_value = False
        
        runner = UpgradeRunner(config)
        version = Version('v1.3.0', '1.3.0', datetime.now())
        
        success, message = runner.perform_upgrade('story', version)
        
        assert success is False
        assert "Pre-upgrade checks failed" in message
        
    @patch('sentinel.runner.UpgradeRunner._pre_upgrade_checks')
    @patch('sentinel.runner.UpgradeRunner._create_backup')
    def test_perform_upgrade_dry_run(self, mock_backup, mock_pre_check, config):
        """Test dry run mode."""
        mock_pre_check.return_value = True
        mock_backup.return_value = Path("/backup/path")
        
        runner = UpgradeRunner(config)
        version = Version('v1.3.0', '1.3.0', datetime.now())
        
        success, message = runner.perform_upgrade('story', version, dry_run=True)
        
        assert success is True
        assert "Dry run completed" in message
        
    @patch('psutil.disk_usage')
    @patch('sentinel.health.HealthChecker.check_all')
    def test_pre_upgrade_checks(self, mock_health_check, mock_disk, config):
        """Test pre-upgrade health checks."""
        # Mock healthy system
        mock_disk.return_value = MagicMock(free=20*1024*1024*1024)  # 20GB
        
        system_health = MagicMock()
        system_health.healthy = True
        system_health.checks = {'disk_free_gb': 20.0}
        
        mock_health_check.return_value = {'system': system_health}
        
        runner = UpgradeRunner(config)
        result = runner._pre_upgrade_checks('story')
        
        assert result is True
        
    @patch('shutil.copy2')
    @patch('shutil.copytree')
    def test_create_backup(self, mock_copytree, mock_copy2, config):
        """Test backup creation."""
        # Create a fake binary
        fake_binary = config.backup_dir / "story"
        fake_binary.touch()
        config.story.binary_path = str(fake_binary)
        
        runner = UpgradeRunner(config)
        
        with patch('pathlib.Path.exists', return_value=True):
            backup_path = runner._create_backup('story')
            
        assert backup_path.exists()
        assert backup_path.is_dir()
        assert (backup_path / 'metadata.json').exists()
        
    @patch('requests.get')
    @patch('subprocess.run')
    @patch('tempfile.TemporaryDirectory')
    def test_download_binary(self, mock_tempdir, mock_subprocess, mock_requests, config):
        """Test binary download."""
        # Mock temp directory
        temp_path = Path("/tmp/test")
        mock_tempdir.return_value.__enter__.return_value = str(temp_path)
        
        # Mock download
        mock_response = MagicMock()
        mock_response.headers = {'content-length': '1000'}
        mock_response.iter_content.return_value = [b'data'] * 10
        mock_response.raise_for_status.return_value = None
        mock_requests.return_value = mock_response
        
        # Mock extraction
        mock_subprocess.return_value = MagicMock(returncode=0)
        
        # Mock finding binary
        with patch('os.walk') as mock_walk:
            mock_walk.return_value = [
                (str(temp_path / 'extracted'), [], ['story'])
            ]
            
            with patch('shutil.copy2'), patch('pathlib.Path.chmod'):
                runner = UpgradeRunner(config)
                version = Version('v1.3.0', '1.3.0', datetime.now(),
                                download_url='https://example.com/story.tar.gz')
                
                result = runner._download_binary('story', version)
                
                # Should return path to binary
                assert result is not None
                
    @patch('subprocess.run')
    def test_stop_service(self, mock_subprocess, config):
        """Test service stopping."""
        # Mock successful stop
        mock_subprocess.side_effect = [
            MagicMock(returncode=0, stdout='', stderr=''),  # stop command
            MagicMock(returncode=0, stdout='inactive', stderr='')  # status check
        ]
        
        runner = UpgradeRunner(config)
        result = runner._stop_service('story')
        
        assert result is True
        assert mock_subprocess.call_count == 2
        
    @patch('subprocess.run')
    def test_start_service(self, mock_subprocess, config):
        """Test service starting."""
        # Mock successful start
        mock_subprocess.side_effect = [
            MagicMock(returncode=0, stdout='', stderr=''),  # start command
            MagicMock(returncode=0, stdout='active', stderr='')  # status check
        ]
        
        runner = UpgradeRunner(config)
        result = runner._start_service('story')
        
        assert result is True
        assert mock_subprocess.call_count == 2
        
    @patch('shutil.copy2')
    def test_replace_binary(self, mock_copy, config):
        """Test binary replacement."""
        runner = UpgradeRunner(config)
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.chmod'):
            result = runner._replace_binary('story', Path('/tmp/new_binary'))
            
        assert result is True
        mock_copy.assert_called()
        
    @patch('sentinel.runner.UpgradeRunner._stop_service')
    @patch('sentinel.runner.UpgradeRunner._start_service')
    @patch('shutil.copy2')
    def test_rollback(self, mock_copy, mock_start, mock_stop, config):
        """Test rollback functionality."""
        mock_stop.return_value = True
        mock_start.return_value = True
        
        runner = UpgradeRunner(config)
        
        # Create fake backup
        backup_path = config.backup_dir / "test_backup"
        backup_path.mkdir()
        (backup_path / "story").touch()
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.chmod'):
            result = runner._rollback('story', backup_path)
            
        assert result is True
        mock_stop.assert_called_once()
        mock_start.assert_called_once()
        mock_copy.assert_called()
        
    def test_cleanup_old_backups(self, config):
        """Test backup cleanup."""
        runner = UpgradeRunner(config)
        
        # Create old and new backups
        old_backup = config.backup_dir / "old_backup"
        old_backup.mkdir()
        metadata = {
            'component': 'story',
            'timestamp': '2020-01-01T00:00:00'
        }
        
        import json
        with open(old_backup / 'metadata.json', 'w') as f:
            json.dump(metadata, f)
            
        new_backup = config.backup_dir / "new_backup"
        new_backup.mkdir()
        metadata['timestamp'] = datetime.now().isoformat()
        with open(new_backup / 'metadata.json', 'w') as f:
            json.dump(metadata, f)
            
        # Run cleanup
        runner.cleanup_old_backups(days=30)
        
        # Old backup should be removed
        assert not old_backup.exists()
        assert new_backup.exists()