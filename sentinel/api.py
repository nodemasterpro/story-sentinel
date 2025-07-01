"""HTTP API endpoints for monitoring and metrics."""

import json
import logging
from datetime import datetime
from pathlib import Path
from aiohttp import web
from prometheus_client import Counter, Gauge, Histogram, generate_latest
import asyncio

from .config import Config
from .health import HealthChecker
from .watcher import VersionWatcher
from .scheduler import UpgradeScheduler

logger = logging.getLogger(__name__)

# Prometheus metrics
health_check_total = Counter('story_sentinel_health_checks_total', 'Total health checks performed')
health_check_failures = Counter('story_sentinel_health_check_failures_total', 'Failed health checks', ['service'])
upgrade_total = Counter('story_sentinel_upgrades_total', 'Total upgrades attempted', ['component', 'status'])
node_block_height = Gauge('story_sentinel_node_block_height', 'Current block height', ['node_type'])
node_peer_count = Gauge('story_sentinel_node_peer_count', 'Current peer count', ['node_type'])
node_sync_status = Gauge('story_sentinel_node_sync_status', 'Node sync status (1=synced, 0=syncing)', ['node_type'])
system_disk_free_gb = Gauge('story_sentinel_system_disk_free_gb', 'Free disk space in GB')
system_memory_free_gb = Gauge('story_sentinel_system_memory_free_gb', 'Free memory in GB')

class HealthAPI:
    """HTTP API for health checks and metrics."""
    
    def __init__(self, config: Config, host: str = '0.0.0.0', port: int = 8080):
        self.config = config
        self.host = host
        self.port = port
        self.app = web.Application()
        self.health_checker = HealthChecker(config)
        self.watcher = VersionWatcher(config)
        self.scheduler = UpgradeScheduler(config)
        self.setup_routes()
        
    def setup_routes(self):
        """Setup HTTP routes."""
        self.app.router.add_get('/health', self.health_handler)
        self.app.router.add_get('/metrics', self.metrics_handler)
        self.app.router.add_get('/status', self.status_handler)
        self.app.router.add_get('/schedule', self.schedule_handler)
        self.app.router.add_get('/version', self.version_handler)
        
    async def health_handler(self, request):
        """Health check endpoint."""
        try:
            # Run health checks
            health_status = self.health_checker.check_all()
            health_check_total.inc()
            
            # Update failure metrics
            for service_name, status in health_status.items():
                if not status.healthy:
                    health_check_failures.labels(service=service_name).inc()
                    
            # Determine overall health
            all_healthy = all(status.healthy for status in health_status.values())
            
            # Format response
            response_data = {
                'healthy': all_healthy,
                'timestamp': datetime.now().isoformat(),
                'services': {}
            }
            
            for service_name, status in health_status.items():
                response_data['services'][service_name] = {
                    'healthy': status.healthy,
                    'message': status.message,
                    'checks': status.checks
                }
                
            return web.json_response(
                response_data,
                status=200 if all_healthy else 503
            )
            
        except Exception as e:
            logger.error(f"Health check error: {e}")
            return web.json_response(
                {'error': str(e), 'healthy': False},
                status=500
            )
            
    async def metrics_handler(self, request):
        """Prometheus metrics endpoint."""
        try:
            # Update metrics with current values
            health_status = self.health_checker.check_all()
            
            # Story metrics
            if 'story' in health_status:
                story_status = health_status['story']
                if story_status.checks.get('latest_block_height'):
                    node_block_height.labels(node_type='story').set(
                        story_status.checks['latest_block_height']
                    )
                if story_status.checks.get('peer_count') is not None:
                    node_peer_count.labels(node_type='story').set(
                        story_status.checks['peer_count']
                    )
                sync_status = 0 if story_status.checks.get('catching_up', True) else 1
                node_sync_status.labels(node_type='story').set(sync_status)
                
            # Story Geth metrics
            if 'story_geth' in health_status:
                geth_status = health_status['story_geth']
                if geth_status.checks.get('block_number'):
                    node_block_height.labels(node_type='story_geth').set(
                        geth_status.checks['block_number']
                    )
                if geth_status.checks.get('peer_count') is not None:
                    node_peer_count.labels(node_type='story_geth').set(
                        geth_status.checks['peer_count']
                    )
                sync_status = 0 if geth_status.checks.get('syncing', True) else 1
                node_sync_status.labels(node_type='story_geth').set(sync_status)
                
            # System metrics
            if 'system' in health_status:
                system_status = health_status['system']
                if system_status.checks.get('disk_free_gb'):
                    system_disk_free_gb.set(system_status.checks['disk_free_gb'])
                if system_status.checks.get('memory_available_gb'):
                    system_memory_free_gb.set(system_status.checks['memory_available_gb'])
                    
            # Generate Prometheus format
            metrics = generate_latest()
            
            return web.Response(
                body=metrics,
                content_type='text/plain; version=0.0.4'
            )
            
        except Exception as e:
            logger.error(f"Metrics generation error: {e}")
            return web.Response(text=f"# Error generating metrics: {e}\n", status=500)
            
    async def status_handler(self, request):
        """Detailed status endpoint."""
        try:
            # Get current versions
            versions = self.config.get_current_versions()
            
            # Check for updates
            updates = self.watcher.check_for_updates()
            
            # Get health status
            health_status = self.health_checker.check_all()
            
            # Get sync progress
            sync_progress = self.health_checker.get_sync_progress()
            
            # Detect issues
            issues = self.health_checker.detect_issues()
            
            response_data = {
                'timestamp': datetime.now().isoformat(),
                'versions': versions,
                'updates_available': {k: v.version for k, v in updates.items()} if updates else {},
                'health': {
                    name: {
                        'healthy': status.healthy,
                        'message': status.message
                    }
                    for name, status in health_status.items()
                },
                'sync_progress': sync_progress,
                'detected_issues': [k for k, v in issues.items() if v],
                'mode': self.config.mode,
                'check_interval': self.config.check_interval
            }
            
            return web.json_response(response_data)
            
        except Exception as e:
            logger.error(f"Status check error: {e}")
            return web.json_response({'error': str(e)}, status=500)
            
    async def schedule_handler(self, request):
        """Upgrade schedule endpoint."""
        try:
            # Get scheduled upgrades
            scheduled = self.scheduler.scheduled_upgrades
            upcoming = self.scheduler.get_upcoming_upgrades(hours=24*7)  # Next week
            
            response_data = {
                'timestamp': datetime.now().isoformat(),
                'total_scheduled': len(scheduled),
                'upcoming_count': len(upcoming),
                'upgrades': [
                    {
                        'component': u.component,
                        'current_version': u.current_version,
                        'target_version': u.target_version,
                        'scheduled_time': u.scheduled_time.isoformat(),
                        'status': u.status,
                        'notes': u.notes
                    }
                    for u in upcoming
                ],
                'calendar_url': f'/schedule.ics'  # Could serve ICS file
            }
            
            return web.json_response(response_data)
            
        except Exception as e:
            logger.error(f"Schedule check error: {e}")
            return web.json_response({'error': str(e)}, status=500)
            
    async def version_handler(self, request):
        """Version information endpoint."""
        from sentinel import __version__
        
        return web.json_response({
            'name': 'Story Sentinel',
            'version': __version__,
            'api_version': '1.0.0'
        })
        
    async def start(self):
        """Start the API server."""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        
        logger.info(f"Health API started on http://{self.host}:{self.port}")
        
        # Keep running
        await asyncio.Event().wait()

def main():
    """Run the API server."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Load config
    config = Config()
    
    # Get host and port from environment
    import os
    host = os.getenv('API_HOST', '0.0.0.0')
    port = int(os.getenv('API_PORT', '8080'))
    
    # Create and start API
    api = HealthAPI(config, host=host, port=port)
    
    try:
        asyncio.run(api.start())
    except KeyboardInterrupt:
        logger.info("API server stopped")

if __name__ == '__main__':
    main()