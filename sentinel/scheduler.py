"""Upgrade scheduler with ICS calendar generation."""

import os
import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict
from icalendar import Calendar, Event, Alarm
import pytz

from .config import Config
from .watcher import Version, GovernanceProposal

logger = logging.getLogger(__name__)

@dataclass
class ScheduledUpgrade:
    """Represents a scheduled upgrade."""
    component: str  # 'story' or 'story_geth'
    current_version: str
    target_version: str
    scheduled_time: datetime
    estimated_duration: timedelta
    status: str = 'pending'  # pending, approved, completed, cancelled
    approval_required: bool = True
    notes: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data['scheduled_time'] = self.scheduled_time.isoformat()
        data['estimated_duration'] = str(self.estimated_duration)
        return data
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScheduledUpgrade':
        """Create from dictionary."""
        data['scheduled_time'] = datetime.fromisoformat(data['scheduled_time'])
        # Parse duration string back to timedelta
        duration_str = data['estimated_duration']
        if ':' in duration_str:
            hours, minutes, seconds = map(int, duration_str.split(':'))
            data['estimated_duration'] = timedelta(hours=hours, minutes=minutes, seconds=seconds)
        else:
            data['estimated_duration'] = timedelta(seconds=0)
        return cls(**data)

class UpgradeScheduler:
    """Manages upgrade scheduling and calendar generation."""
    
    def __init__(self, config: Config):
        self.config = config
        self.schedule_file = config.log_dir / "upgrade_schedule.json"
        self.calendar_file = config.log_dir / "upgrade_calendar.ics"
        self.scheduled_upgrades: List[ScheduledUpgrade] = []
        self.load_schedule()
        
    def load_schedule(self):
        """Load scheduled upgrades from file."""
        if self.schedule_file.exists():
            try:
                with open(self.schedule_file, 'r') as f:
                    data = json.load(f)
                    self.scheduled_upgrades = [
                        ScheduledUpgrade.from_dict(item) for item in data
                    ]
                logger.info(f"Loaded {len(self.scheduled_upgrades)} scheduled upgrades")
            except Exception as e:
                logger.error(f"Failed to load schedule: {e}")
                
    def save_schedule(self):
        """Save scheduled upgrades to file."""
        try:
            # Ensure directory exists
            self.schedule_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Save with atomic write
            temp_file = self.schedule_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                data = [upgrade.to_dict() for upgrade in self.scheduled_upgrades]
                json.dump(data, f, indent=2)
            temp_file.replace(self.schedule_file)
            
            # Update calendar
            self.generate_ics_calendar()
            
            logger.info("Schedule saved successfully")
        except Exception as e:
            logger.error(f"Failed to save schedule: {e}")
            
    def schedule_upgrade(self, component: str, target_version: Version, 
                        scheduled_time: Optional[datetime] = None,
                        auto_approve: bool = False) -> ScheduledUpgrade:
        """Schedule an upgrade."""
        # Get current version
        current_versions = self.config.get_current_versions()
        current_version = current_versions.get(component, 'unknown')
        
        # Default to next maintenance window if no time specified
        if scheduled_time is None:
            scheduled_time = self.get_next_maintenance_window()
            
        # Estimate duration
        base_duration = timedelta(minutes=10)
        if component == 'story':
            base_duration = timedelta(minutes=15)  # Story takes longer
            
        # Create scheduled upgrade
        upgrade = ScheduledUpgrade(
            component=component,
            current_version=current_version,
            target_version=target_version.version,
            scheduled_time=scheduled_time,
            estimated_duration=base_duration,
            status='approved' if auto_approve else 'pending',
            approval_required=not auto_approve,
            notes=f"Upgrade from {current_version} to {target_version.version}"
        )
        
        # Add to schedule
        self.scheduled_upgrades.append(upgrade)
        self.scheduled_upgrades.sort(key=lambda x: x.scheduled_time)
        
        # Save
        self.save_schedule()
        
        logger.info(f"Scheduled {component} upgrade to {target_version.version} at {scheduled_time}")
        return upgrade
        
    def schedule_governance_upgrade(self, proposal: GovernanceProposal) -> Optional[ScheduledUpgrade]:
        """Schedule upgrade based on governance proposal."""
        if not proposal.upgrade_height or not proposal.upgrade_version:
            return None
            
        # Calculate estimated time based on block height
        # Assuming ~5 second block time
        current_height = self._get_current_block_height()
        if current_height:
            blocks_until_upgrade = proposal.upgrade_height - current_height
            estimated_time = datetime.now() + timedelta(seconds=blocks_until_upgrade * 5)
            
            # Schedule with some buffer time
            scheduled_time = estimated_time - timedelta(minutes=30)
            
            upgrade = ScheduledUpgrade(
                component='story',  # Governance upgrades are typically for consensus
                current_version=self.config.story.current_version or 'unknown',
                target_version=proposal.upgrade_version,
                scheduled_time=scheduled_time,
                estimated_duration=timedelta(minutes=30),
                status='approved',  # Governance approved
                approval_required=False,
                notes=f"Governance proposal #{proposal.proposal_id}: {proposal.title}"
            )
            
            self.scheduled_upgrades.append(upgrade)
            self.save_schedule()
            
            return upgrade
            
        return None
        
    def get_next_maintenance_window(self) -> datetime:
        """Get next available maintenance window."""
        # Default to 2 AM UTC next day
        now = datetime.now(pytz.UTC)
        next_window = now.replace(hour=2, minute=0, second=0, microsecond=0)
        
        # If it's already past 2 AM, move to next day
        if now.hour >= 2:
            next_window += timedelta(days=1)
            
        # Check if there are conflicts
        for upgrade in self.scheduled_upgrades:
            if upgrade.status in ['pending', 'approved']:
                upgrade_end = upgrade.scheduled_time + upgrade.estimated_duration
                if upgrade.scheduled_time <= next_window <= upgrade_end:
                    # Conflict, move to after this upgrade
                    next_window = upgrade_end + timedelta(minutes=30)
                    
        return next_window
        
    def get_pending_upgrades(self) -> List[ScheduledUpgrade]:
        """Get list of pending upgrades."""
        return [u for u in self.scheduled_upgrades if u.status == 'pending']
        
    def get_upcoming_upgrades(self, hours: int = 24) -> List[ScheduledUpgrade]:
        """Get upgrades scheduled in the next N hours."""
        cutoff = datetime.now() + timedelta(hours=hours)
        return [
            u for u in self.scheduled_upgrades 
            if u.status in ['pending', 'approved'] and u.scheduled_time <= cutoff
        ]
        
    def approve_upgrade(self, upgrade_index: int) -> bool:
        """Approve a pending upgrade."""
        if 0 <= upgrade_index < len(self.scheduled_upgrades):
            upgrade = self.scheduled_upgrades[upgrade_index]
            if upgrade.status == 'pending':
                upgrade.status = 'approved'
                self.save_schedule()
                logger.info(f"Approved upgrade: {upgrade.component} to {upgrade.target_version}")
                return True
        return False
        
    def cancel_upgrade(self, upgrade_index: int) -> bool:
        """Cancel a scheduled upgrade."""
        if 0 <= upgrade_index < len(self.scheduled_upgrades):
            upgrade = self.scheduled_upgrades[upgrade_index]
            if upgrade.status in ['pending', 'approved']:
                upgrade.status = 'cancelled'
                self.save_schedule()
                logger.info(f"Cancelled upgrade: {upgrade.component} to {upgrade.target_version}")
                return True
        return False
        
    def mark_completed(self, component: str, version: str):
        """Mark an upgrade as completed."""
        for upgrade in self.scheduled_upgrades:
            if (upgrade.component == component and 
                upgrade.target_version == version and
                upgrade.status == 'approved'):
                upgrade.status = 'completed'
                self.save_schedule()
                logger.info(f"Marked upgrade as completed: {component} to {version}")
                break
                
    def generate_ics_calendar(self):
        """Generate ICS calendar file for scheduled upgrades."""
        try:
            cal = Calendar()
            cal.add('prodid', '-//Story Sentinel//Upgrade Calendar//EN')
            cal.add('version', '2.0')
            cal.add('name', 'Story Node Upgrades')
            cal.add('x-wr-calname', 'Story Node Upgrades')
            
            for upgrade in self.scheduled_upgrades:
                if upgrade.status in ['pending', 'approved']:
                    event = Event()
                    event.add('summary', f'Story Upgrade: {upgrade.component} to {upgrade.target_version}')
                    event.add('dtstart', upgrade.scheduled_time)
                    event.add('dtend', upgrade.scheduled_time + upgrade.estimated_duration)
                    event.add('description', f'''Component: {upgrade.component}
Current Version: {upgrade.current_version}
Target Version: {upgrade.target_version}
Status: {upgrade.status}
Approval Required: {upgrade.approval_required}
Notes: {upgrade.notes or "No additional notes"}''')
                    
                    # Add alarm 30 minutes before
                    alarm = Alarm()
                    alarm.add('action', 'DISPLAY')
                    alarm.add('trigger', timedelta(minutes=-30))
                    alarm.add('description', f'Story upgrade starting in 30 minutes: {upgrade.component}')
                    event.add_component(alarm)
                    
                    cal.add_component(event)
                    
            # Save calendar
            self.calendar_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.calendar_file, 'wb') as f:
                f.write(cal.to_ical())
                
            logger.info(f"Generated ICS calendar at {self.calendar_file}")
            
        except Exception as e:
            logger.error(f"Failed to generate calendar: {e}")
            
    def get_schedule_summary(self) -> str:
        """Get a summary of scheduled upgrades."""
        lines = ["Scheduled Upgrades:"]
        lines.append("-" * 80)
        
        if not self.scheduled_upgrades:
            lines.append("No upgrades scheduled")
        else:
            for i, upgrade in enumerate(self.scheduled_upgrades):
                status_icon = {
                    'pending': '⏳',
                    'approved': '✅',
                    'completed': '✓',
                    'cancelled': '❌'
                }.get(upgrade.status, '?')
                
                lines.append(f"{i+1}. {status_icon} {upgrade.component} → {upgrade.target_version}")
                lines.append(f"   Scheduled: {upgrade.scheduled_time.strftime('%Y-%m-%d %H:%M UTC')}")
                lines.append(f"   Current: {upgrade.current_version}")
                lines.append(f"   Duration: {upgrade.estimated_duration}")
                if upgrade.notes:
                    lines.append(f"   Notes: {upgrade.notes}")
                lines.append("")
                
        return "\n".join(lines)
        
    def _get_current_block_height(self) -> Optional[int]:
        """Get current block height from Story node."""
        try:
            import requests
            response = requests.get(
                f"http://localhost:{self.config.story.rpc_port}/status",
                timeout=5
            )
            data = response.json()
            if 'result' in data:
                return int(data['result']['sync_info']['latest_block_height'])
        except Exception as e:
            logger.error(f"Failed to get block height: {e}")
        return None
        
    def cleanup_old_upgrades(self, days: int = 30):
        """Remove completed/cancelled upgrades older than N days."""
        cutoff = datetime.now() - timedelta(days=days)
        
        self.scheduled_upgrades = [
            u for u in self.scheduled_upgrades
            if u.status in ['pending', 'approved'] or u.scheduled_time > cutoff
        ]
        
        self.save_schedule()