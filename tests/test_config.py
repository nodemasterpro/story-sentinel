"""Tests for configuration module."""

import os
import tempfile
import pytest
from pathlib import Path
import yaml

from sentinel.config import Config, ServiceConfig, ThresholdConfig


class TestConfig:
    """Test configuration management."""
    
    def test_default_initialization(self):
        """Test default configuration values."""
        config = Config()
        
        assert config.story.service_name == "story"
        assert config.story.rpc_port == 26657
        assert config.story_geth.service_name == "story-geth"
        assert config.story_geth.rpc_port == 8545
        assert config.mode == "manual"
        assert config.log_level == "INFO"
        
    def test_env_override(self, monkeypatch):
        """Test environment variable overrides."""
        monkeypatch.setenv("MODE", "auto")
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("STORY_BINARY_PATH", "/custom/path/story")
        
        config = Config()
        
        assert config.mode == "auto"
        assert config.log_level == "DEBUG"
        assert config.story.binary_path == "/custom/path/story"
        
    def test_yaml_loading(self):
        """Test loading configuration from YAML."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml_content = """
story:
  binary_path: /test/story
  rpc_port: 26658
story_geth:
  binary_path: /test/geth
  rpc_port: 8546
thresholds:
  height_gap: 50
  min_peers: 10
"""
            f.write(yaml_content)
            f.flush()
            
            config = Config(config_path=Path(f.name))
            
            assert config.story.binary_path == "/test/story"
            assert config.story.rpc_port == 26658
            assert config.story_geth.binary_path == "/test/geth"
            assert config.story_geth.rpc_port == 8546
            assert config.thresholds.height_gap == 50
            assert config.thresholds.min_peers == 10
            
            os.unlink(f.name)
            
    def test_save_yaml_config(self):
        """Test saving configuration to YAML."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            config = Config(config_path=config_path)
            
            # Modify config
            config.story.rpc_port = 26659
            config.thresholds.min_peers = 15
            
            # Save
            config.save_yaml_config()
            
            # Verify file exists
            assert config_path.exists()
            
            # Load and verify
            with open(config_path, 'r') as f:
                data = yaml.safe_load(f)
                
            assert data['story']['rpc_port'] == 26659
            assert data['thresholds']['min_peers'] == 15
            
    def test_validation_missing_binaries(self, monkeypatch):
        """Test validation with missing binaries."""
        monkeypatch.setenv("STORY_BINARY_PATH", "/nonexistent/story")
        config = Config()
        
        assert not config.validate()
        
    def test_get_current_versions(self, monkeypatch):
        """Test getting current versions."""
        # Mock the popen calls
        def mock_popen(cmd):
            class MockResult:
                def read(self):
                    if 'story version' in cmd:
                        return "v1.2.3"
                    elif 'story-geth version' in cmd:
                        return "Version: 1.1.0"
                    return ""
                    
            return MockResult()
            
        monkeypatch.setattr(os, 'popen', mock_popen)
        
        config = Config()
        versions = config.get_current_versions()
        
        assert versions['story'] == "v1.2.3"
        assert '1.1.0' in versions['story_geth']
        
    def test_service_config_dataclass(self):
        """Test ServiceConfig dataclass."""
        service = ServiceConfig(
            binary_path="/usr/bin/test",
            service_name="test-service",
            rpc_port=8080,
            github_repo="test/repo"
        )
        
        assert service.binary_path == "/usr/bin/test"
        assert service.service_name == "test-service"
        assert service.rpc_port == 8080
        assert service.version_command == "--version"
        assert service.current_version is None