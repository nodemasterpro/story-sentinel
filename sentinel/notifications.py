"""Notification system for Discord and Telegram."""

import logging
import requests
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class NotificationManager:
    """Manages notifications to Discord and Telegram."""
    
    def __init__(self, discord_webhook: Optional[str] = None, 
                 telegram_bot_token: Optional[str] = None,
                 telegram_chat_id: Optional[str] = None):
        self.discord_webhook = discord_webhook
        self.telegram_bot_token = telegram_bot_token
        self.telegram_chat_id = telegram_chat_id
        
    def send_startup_notification(self, health_status=None, updates_available=None):
        """Send startup notification with current status and updates."""
        message = f"🚀 **Story Sentinel Started**\n\n" \
                 f"✅ Monitoring service started successfully\n" \
                 f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
        
        # Add health status
        if health_status:
            message += "**📊 Current Node Status:**\n"
            for service_name, status in health_status.items():
                emoji = "✅" if status.healthy else "❌"
                message += f"{emoji} {service_name}: {'Healthy' if status.healthy else 'Unhealthy'}\n"
                if not status.healthy and status.message:
                    message += f"   └─ {status.message}\n"
            message += "\n"
        
        # Add update information
        if updates_available:
            message += "**📦 Updates Available:**\n"
            for component, version in updates_available.items():
                message += f"🔔 {component}: {version.version}\n"
                message += f"   └─ Released: {version.published_at.strftime('%Y-%m-%d')}\n"
            message += "\n⚠️ **Important:** Check Story Protocol Discord for timing requirements before upgrading!\n\n"
        else:
            message += "✅ **All components up to date**\n\n"
            
        message += "📊 Ready to monitor Story Protocol nodes"
        
        self._send_notification("Story Sentinel - Service Started", message)
        
    def send_restart_notification(self):
        """Send restart notification to configured channels."""
        message = f"🔄 **Story Sentinel Restarted**\n\n" \
                 f"✅ Monitoring service restarted successfully\n" \
                 f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n" \
                 f"📊 Resuming node monitoring"
        
        self._send_notification("Story Sentinel - Service Restarted", message)
        
    def send_health_alert(self, service: str, status: str, message: str):
        """Send health alert notification."""
        emoji = "❌" if "unhealthy" in status.lower() else "✅"
        alert_message = f"{emoji} **Story Sentinel Alert**\n\n" \
                       f"🔧 Service: {service}\n" \
                       f"📊 Status: {status}\n" \
                       f"📝 Details: {message}\n" \
                       f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}"
        
        self._send_notification(f"Story Sentinel - {service} Alert", alert_message)
        
    def send_upgrade_notification(self, component: str, from_version: str, to_version: str, success: bool):
        """Send upgrade notification."""
        emoji = "✅" if success else "❌"
        status = "Completed" if success else "Failed"
        
        message = f"{emoji} **Story Sentinel Upgrade {status}**\n\n" \
                 f"🔧 Component: {component}\n" \
                 f"📊 From: {from_version} → To: {to_version}\n" \
                 f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}"
        
        self._send_notification(f"Story Sentinel - Upgrade {status}", message)
        
    def send_update_detected(self, component: str, current_version: str, new_version: str, release_date: str):
        """Send notification when new update is detected."""
        message = f"🔔 **New Update Detected**\n\n" \
                 f"📦 Component: {component}\n" \
                 f"📊 Current: {current_version}\n" \
                 f"🆕 Available: {new_version}\n" \
                 f"📅 Released: {release_date}\n\n" \
                 f"⚠️ **Important:** Check Story Protocol Discord for upgrade timing requirements!\n" \
                 f"🔗 Discord: https://discord.gg/storyprotocol\n\n" \
                 f"Use: `story-sentinel upgrade {component} {new_version}`"
        
        self._send_notification(f"Story Sentinel - Update Available", message)
        
    def send_upgrade_scheduled(self, component: str, version: str, scheduled_time: str):
        """Send notification when upgrade is scheduled."""
        message = f"📅 **Upgrade Scheduled**\n\n" \
                 f"📦 Component: {component}\n" \
                 f"🆕 Version: {version}\n" \
                 f"⏰ Scheduled: {scheduled_time}\n\n" \
                 f"The upgrade will be executed automatically at the scheduled time."
        
        self._send_notification(f"Story Sentinel - Upgrade Scheduled", message)
        
    def send_periodic_status(self, health_status, updates_available=None):
        """Send periodic status notification (for critical issues)."""
        unhealthy_services = [name for name, status in health_status.items() if not status.healthy]
        
        if not unhealthy_services and not updates_available:
            return  # Don't spam if everything is fine
            
        message = f"📊 **Story Sentinel Status Report**\n\n"
        message += f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
        
        if unhealthy_services:
            message += "❌ **Issues Detected:**\n"
            for service_name in unhealthy_services:
                status = health_status[service_name]
                message += f"• {service_name}: {status.message}\n"
            message += "\n"
        
        if updates_available:
            message += "📦 **Pending Updates:**\n"
            for component, version in updates_available.items():
                message += f"• {component}: {version.version}\n"
            message += "\n⚠️ Check Story Discord for timing!\n"
        
        self._send_notification("Story Sentinel - Status Report", message)
        
    def _send_notification(self, title: str, message: str):
        """Send notification to all configured channels."""
        if self.discord_webhook:
            self._send_discord(title, message)
            
        if self.telegram_bot_token and self.telegram_chat_id:
            self._send_telegram(title, message)
            
    def _send_discord(self, title: str, message: str):
        """Send notification to Discord webhook."""
        try:
            payload = {
                "embeds": [{
                    "title": title,
                    "description": message,
                    "color": 3447003,  # Blue color
                    "timestamp": datetime.now().isoformat()
                }]
            }
            
            response = requests.post(
                self.discord_webhook,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 204:
                logger.info("Discord notification sent successfully")
            else:
                logger.warning(f"Discord notification failed: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Failed to send Discord notification: {e}")
            
    def _send_telegram(self, title: str, message: str):
        """Send notification to Telegram chat."""
        try:
            # Format message for Telegram (Markdown)
            telegram_message = f"*{title}*\n\n{message}"
            
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            payload = {
                "chat_id": self.telegram_chat_id,
                "text": telegram_message,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                logger.info("Telegram notification sent successfully")
            else:
                logger.warning(f"Telegram notification failed: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")
            
    def test_notifications(self):
        """Test both notification channels."""
        test_message = f"🧪 **Story Sentinel Test**\n\n" \
                      f"✅ Notification system is working correctly\n" \
                      f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}"
        
        self._send_notification("Story Sentinel - Test Notification", test_message)
        logger.info("Test notifications sent")