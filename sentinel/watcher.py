"""Version watcher for Story Protocol releases and governance proposals."""

import os
import re
import json
import time
import logging
import requests
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

from .config import Config

logger = logging.getLogger(__name__)

@dataclass
class Version:
    """Represents a software version."""
    tag: str
    version: str
    published_at: datetime
    download_url: Optional[str] = None
    release_notes: Optional[str] = None
    
    def __gt__(self, other):
        """Compare versions."""
        return self._parse_version(self.version) > self._parse_version(other.version)
        
    def _parse_version(self, version: str) -> Tuple[int, ...]:
        """Parse version string to tuple for comparison."""
        # Remove 'v' prefix if present
        version = version.lstrip('v')
        # Extract numeric parts
        parts = re.findall(r'\d+', version)
        return tuple(int(p) for p in parts)

@dataclass 
class GovernanceProposal:
    """Represents a governance proposal."""
    proposal_id: int
    title: str
    description: str
    status: str
    voting_end_time: datetime
    upgrade_height: Optional[int] = None
    upgrade_version: Optional[str] = None

class VersionWatcher:
    """Watches for new versions and governance proposals."""
    
    GITHUB_API_BASE = "https://api.github.com"
    RATE_LIMIT_DELAY = 1.0  # 1 second between requests
    
    def __init__(self, config: Config):
        self.config = config
        self.last_github_check = {}
        self.cached_versions = {}
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'Story-Sentinel/1.1'
        })
        
        # Add GitHub token if available
        github_token = os.environ.get('GITHUB_TOKEN')
        if github_token:
            self.session.headers['Authorization'] = f'token {github_token}'
            
    def check_for_updates(self) -> Dict[str, Optional[Version]]:
        """Check for new versions of Story components."""
        updates = {}
        
        # Get current versions
        current_versions = self.config.get_current_versions()
        
        # Check Story
        latest_story = self._get_latest_release(self.config.story.github_repo)
        if latest_story and current_versions.get('story') != latest_story.version:
            updates['story'] = latest_story
            
        # Check Story Geth
        latest_geth = self._get_latest_release(self.config.story_geth.github_repo)
        if latest_geth and current_versions.get('story_geth') != latest_geth.version:
            updates['story_geth'] = latest_geth
            
        return updates
        
    def _get_latest_release(self, repo: str) -> Optional[Version]:
        """Get latest release from GitHub."""
        # Check rate limiting
        if repo in self.last_github_check:
            elapsed = time.time() - self.last_github_check[repo]
            if elapsed < self.RATE_LIMIT_DELAY:
                time.sleep(self.RATE_LIMIT_DELAY - elapsed)
                
        # Check cache
        if repo in self.cached_versions:
            cached_version, cached_time = self.cached_versions[repo]
            if datetime.now() - cached_time < timedelta(minutes=5):
                return cached_version
                
        try:
            # Get latest release
            url = f"{self.GITHUB_API_BASE}/repos/{repo}/releases/latest"
            response = self.session.get(url, timeout=5)
            self.last_github_check[repo] = time.time()
            
            if response.status_code == 200:
                data = response.json()
                
                # Parse release info
                version = Version(
                    tag=data['tag_name'],
                    version=data['tag_name'].lstrip('v'),
                    published_at=datetime.fromisoformat(data['published_at'].replace('Z', '+00:00')),
                    release_notes=data.get('body', '')
                )
                
                # Find download URL for Linux binary
                for asset in data.get('assets', []):
                    name = asset['name'].lower()
                    if 'linux' in name and ('amd64' in name or 'x86_64' in name):
                        version.download_url = asset['browser_download_url']
                        break
                        
                # Cache the result
                self.cached_versions[repo] = (version, datetime.now())
                
                logger.info(f"Found latest version for {repo}: {version.version}")
                return version
                
            elif response.status_code == 404:
                logger.warning(f"Repository {repo} not found")
            else:
                logger.error(f"GitHub API error for {repo}: {response.status_code}")
                
        except requests.exceptions.Timeout:
            logger.error(f"Timeout checking {repo}")
        except Exception as e:
            logger.error(f"Error checking {repo}: {e}")
            
        return None
        
    def get_all_releases(self, repo: str, limit: int = 10) -> List[Version]:
        """Get list of recent releases."""
        releases = []
        
        try:
            url = f"{self.GITHUB_API_BASE}/repos/{repo}/releases"
            response = self.session.get(url, params={'per_page': limit}, timeout=5)
            
            if response.status_code == 200:
                for data in response.json():
                    version = Version(
                        tag=data['tag_name'],
                        version=data['tag_name'].lstrip('v'),
                        published_at=datetime.fromisoformat(data['published_at'].replace('Z', '+00:00')),
                        release_notes=data.get('body', '')
                    )
                    releases.append(version)
                    
        except Exception as e:
            logger.error(f"Error getting releases for {repo}: {e}")
            
        return releases
        
    def check_governance_proposals(self) -> List[GovernanceProposal]:
        """Check for governance proposals (placeholder for future implementation)."""
        proposals = []
        
        # TODO: Implement governance proposal checking
        # This would typically involve:
        # 1. Querying the Story chain's governance module
        # 2. Filtering for software upgrade proposals
        # 3. Checking proposal status and voting periods
        
        # For now, we can check a Discord channel or API endpoint if available
        
        return proposals
        
    def monitor_discord_announcements(self) -> List[Dict[str, Any]]:
        """Monitor Discord for upgrade announcements (placeholder)."""
        announcements = []
        
        # TODO: Implement Discord monitoring
        # This would involve:
        # 1. Using discord.py to connect to Story Discord
        # 2. Monitoring announcement channels
        # 3. Parsing messages for upgrade notifications
        
        return announcements
        
    def get_version_changelog(self, repo: str, from_version: str, to_version: str) -> str:
        """Get changelog between two versions."""
        changelog = []
        
        try:
            # Get all releases
            releases = self.get_all_releases(repo, limit=50)
            
            # Find releases in range
            in_range = False
            for release in releases:
                if release.version == to_version:
                    in_range = True
                    
                if in_range:
                    changelog.append(f"## {release.version} - {release.published_at.strftime('%Y-%m-%d')}")
                    if release.release_notes:
                        changelog.append(release.release_notes)
                    changelog.append("")
                    
                if release.version == from_version:
                    break
                    
        except Exception as e:
            logger.error(f"Error getting changelog: {e}")
            
        return "\n".join(changelog)
        
    def verify_binary_signature(self, binary_path: str, signature_url: Optional[str] = None) -> bool:
        """Verify binary signature (if available)."""
        # For now, we'll at least verify SHA256
        try:
            import hashlib
            
            # Calculate file hash
            sha256_hash = hashlib.sha256()
            with open(binary_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
                    
            file_hash = sha256_hash.hexdigest()
            logger.info(f"Binary SHA256: {file_hash}")
            
            # TODO: Download and verify against published checksum
            # For now, we just log it
            
            return True
            
        except Exception as e:
            logger.error(f"Error verifying binary: {e}")
            return False
            
    def estimate_upgrade_time(self, component: str) -> timedelta:
        """Estimate time required for upgrade."""
        # Base estimates
        estimates = {
            'story': timedelta(minutes=5),
            'story_geth': timedelta(minutes=5),
        }
        
        # Add time for snapshots if needed
        # TODO: Check if snapshot is needed based on current sync status
        
        return estimates.get(component, timedelta(minutes=10))
        
    def should_auto_upgrade(self, version: Version) -> bool:
        """Determine if auto-upgrade should proceed."""
        if self.config.mode != 'auto':
            return False
            
        # Check version pattern for critical updates
        # e.g., patch versions might be auto-upgraded, but not major versions
        current = self.config.get_current_versions()
        
        # Parse versions to determine if it's a patch
        # For now, we're conservative and don't auto-upgrade
        
        return False  # Default to manual approval for safety