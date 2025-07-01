"""Tests for version watcher module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import requests

from sentinel.config import Config
from sentinel.watcher import VersionWatcher, Version


class TestVersionWatcher:
    """Test version watching functionality."""
    
    @pytest.fixture
    def config(self):
        """Create test config."""
        return Config()
        
    @pytest.fixture
    def watcher(self, config):
        """Create watcher instance."""
        return VersionWatcher(config)
        
    def test_version_dataclass(self):
        """Test Version dataclass."""
        v1 = Version(
            tag="v1.2.3",
            version="1.2.3",
            published_at=datetime.now(),
            download_url="https://example.com/download"
        )
        
        v2 = Version(
            tag="v1.2.2",
            version="1.2.2",
            published_at=datetime.now()
        )
        
        # Test comparison
        assert v1 > v2
        
        # Test version parsing
        v3 = Version(tag="v1.10.0", version="1.10.0", published_at=datetime.now())
        v4 = Version(tag="v1.9.0", version="1.9.0", published_at=datetime.now())
        assert v3 > v4
        
    @patch('requests.Session.get')
    def test_get_latest_release(self, mock_get):
        """Test getting latest release from GitHub."""
        # Mock GitHub API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'tag_name': 'v1.3.0',
            'published_at': '2024-01-01T00:00:00Z',
            'body': 'Release notes here',
            'assets': [
                {
                    'name': 'story_v1.3.0_linux_amd64.tar.gz',
                    'browser_download_url': 'https://github.com/download/story_v1.3.0_linux_amd64.tar.gz'
                }
            ]
        }
        mock_get.return_value = mock_response
        
        config = Config()
        watcher = VersionWatcher(config)
        
        version = watcher._get_latest_release('piplabs/story')
        
        assert version is not None
        assert version.version == '1.3.0'
        assert version.tag == 'v1.3.0'
        assert version.download_url is not None
        assert 'linux_amd64' in version.download_url
        
    @patch('requests.Session.get')
    def test_get_latest_release_rate_limit(self, mock_get):
        """Test rate limiting for GitHub API."""
        config = Config()
        watcher = VersionWatcher(config)
        
        # First call
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'tag_name': 'v1.0.0',
            'published_at': '2024-01-01T00:00:00Z',
            'assets': []
        }
        mock_get.return_value = mock_response
        
        import time
        start = time.time()
        
        # Make two rapid calls
        watcher._get_latest_release('test/repo1')
        watcher._get_latest_release('test/repo1')
        
        elapsed = time.time() - start
        
        # Should have rate limiting delay
        assert elapsed >= watcher.RATE_LIMIT_DELAY
        
    @patch('sentinel.watcher.VersionWatcher._get_latest_release')
    def test_check_for_updates(self, mock_get_release):
        """Test checking for updates."""
        # Mock current versions
        config = Config()
        config.story.current_version = "1.2.0"
        config.story_geth.current_version = "1.0.0"
        
        # Mock latest releases
        story_version = Version(
            tag="v1.3.0",
            version="1.3.0",
            published_at=datetime.now()
        )
        geth_version = Version(
            tag="v1.1.0",
            version="1.1.0",
            published_at=datetime.now()
        )
        
        def side_effect(repo):
            if 'story-geth' in repo:
                return geth_version
            return story_version
            
        mock_get_release.side_effect = side_effect
        
        watcher = VersionWatcher(config)
        updates = watcher.check_for_updates()
        
        assert 'story' in updates
        assert 'story_geth' in updates
        assert updates['story'].version == "1.3.0"
        assert updates['story_geth'].version == "1.1.0"
        
    @patch('requests.Session.get')
    def test_get_all_releases(self, mock_get):
        """Test getting multiple releases."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                'tag_name': 'v1.3.0',
                'published_at': '2024-01-03T00:00:00Z',
                'body': 'Latest release'
            },
            {
                'tag_name': 'v1.2.0',
                'published_at': '2024-01-02T00:00:00Z',
                'body': 'Previous release'
            },
            {
                'tag_name': 'v1.1.0',
                'published_at': '2024-01-01T00:00:00Z',
                'body': 'Older release'
            }
        ]
        mock_get.return_value = mock_response
        
        config = Config()
        watcher = VersionWatcher(config)
        
        releases = watcher.get_all_releases('test/repo', limit=3)
        
        assert len(releases) == 3
        assert releases[0].version == '1.3.0'
        assert releases[1].version == '1.2.0'
        assert releases[2].version == '1.1.0'
        
    def test_get_version_changelog(self):
        """Test getting changelog between versions."""
        config = Config()
        watcher = VersionWatcher(config)
        
        # Mock get_all_releases
        releases = [
            Version('v1.3.0', '1.3.0', datetime.now(), release_notes='Fix critical bug'),
            Version('v1.2.0', '1.2.0', datetime.now() - timedelta(days=1), release_notes='Add feature X'),
            Version('v1.1.0', '1.1.0', datetime.now() - timedelta(days=2), release_notes='Initial release')
        ]
        
        with patch.object(watcher, 'get_all_releases', return_value=releases):
            changelog = watcher.get_version_changelog('test/repo', '1.1.0', '1.3.0')
            
            assert '1.3.0' in changelog
            assert '1.2.0' in changelog
            assert 'Fix critical bug' in changelog
            assert 'Add feature X' in changelog
            
    @patch('builtins.open', create=True)
    @patch('os.path.exists')
    def test_verify_binary_signature(self, mock_exists, mock_open):
        """Test binary signature verification."""
        mock_exists.return_value = True
        mock_open.return_value.__enter__.return_value.read.return_value = b'test binary content'
        
        config = Config()
        watcher = VersionWatcher(config)
        
        result = watcher.verify_binary_signature('/path/to/binary')
        
        assert result is True  # Currently just returns True
        
    def test_estimate_upgrade_time(self):
        """Test upgrade time estimation."""
        config = Config()
        watcher = VersionWatcher(config)
        
        story_time = watcher.estimate_upgrade_time('story')
        geth_time = watcher.estimate_upgrade_time('story_geth')
        unknown_time = watcher.estimate_upgrade_time('unknown')
        
        assert story_time == timedelta(minutes=5)
        assert geth_time == timedelta(minutes=5)
        assert unknown_time == timedelta(minutes=10)
        
    def test_should_auto_upgrade(self):
        """Test auto-upgrade decision logic."""
        config = Config()
        watcher = VersionWatcher(config)
        
        version = Version('v1.2.1', '1.2.1', datetime.now())
        
        # Manual mode - should not auto-upgrade
        config.mode = 'manual'
        assert watcher.should_auto_upgrade(version) is False
        
        # Auto mode - currently conservative
        config.mode = 'auto'
        assert watcher.should_auto_upgrade(version) is False  # Currently always False