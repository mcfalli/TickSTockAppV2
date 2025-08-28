"""
Health Monitoring Service
Monitors TickStockPL connectivity, database health, and system status for Sprint 10.

Provides real-time health information for the dashboard and system monitoring.
"""

import logging
import time
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
import redis
from src.infrastructure.database.tickstock_db import TickStockDatabase

logger = logging.getLogger(__name__)

@dataclass
class HealthStatus:
    """Health status for a system component."""
    status: str  # 'healthy', 'degraded', 'error', 'unknown'
    response_time_ms: Optional[float] = None
    last_check: Optional[float] = None
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

class HealthMonitor:
    """Comprehensive health monitoring for TickStockAppV2 and TickStockPL integration."""
    
    def __init__(self, config: Dict[str, Any], redis_client: Optional[redis.Redis] = None):
        """Initialize health monitoring service."""
        self.config = config
        self.redis_client = redis_client
        self.tickstock_db = None
        
        # Initialize TickStock database connection
        try:
            self.tickstock_db = TickStockDatabase(config)
            logger.info("HEALTH-MONITOR: TickStock database connection initialized")
        except Exception as e:
            logger.warning(f"HEALTH-MONITOR: Failed to initialize TickStock DB connection: {e}")
    
    def get_overall_health(self) -> Dict[str, Any]:
        """Get comprehensive system health status."""
        health_data = {
            'timestamp': time.time(),
            'overall_status': 'healthy',
            'components': {},
            'summary': {
                'healthy': 0,
                'degraded': 0,
                'error': 0,
                'unknown': 0
            }
        }
        
        # Check all components
        health_data['components']['database'] = self._check_database_health()
        health_data['components']['redis'] = self._check_redis_health()
        health_data['components']['tickstockpl_connectivity'] = self._check_tickstockpl_connectivity()
        
        # Calculate summary and overall status
        for component_name, component_health in health_data['components'].items():
            status = component_health.status
            health_data['summary'][status] = health_data['summary'].get(status, 0) + 1
        
        # Determine overall status
        if health_data['summary']['error'] > 0:
            health_data['overall_status'] = 'error'
        elif health_data['summary']['degraded'] > 0:
            health_data['overall_status'] = 'degraded'
        elif health_data['summary']['unknown'] > 0:
            health_data['overall_status'] = 'unknown'
        else:
            health_data['overall_status'] = 'healthy'
        
        logger.debug(f"HEALTH-MONITOR: Overall system status: {health_data['overall_status']}")
        return health_data
    
    def _check_database_health(self) -> HealthStatus:
        """Check TickStock database health and performance."""
        if not self.tickstock_db:
            return HealthStatus(
                status='error',
                message='TickStock database not initialized',
                last_check=time.time()
            )
        
        try:
            start_time = time.time()
            db_health = self.tickstock_db.health_check()
            response_time = (time.time() - start_time) * 1000
            
            return HealthStatus(
                status=db_health['status'],
                response_time_ms=round(response_time, 2),
                last_check=time.time(),
                message=db_health.get('error') or db_health.get('warning'),
                details={
                    'tables_accessible': db_health.get('tables_accessible', []),
                    'query_performance_ms': db_health.get('query_performance'),
                    'connection_pool': db_health.get('connection_pool')
                }
            )
            
        except Exception as e:
            logger.error(f"HEALTH-MONITOR: Database health check failed: {e}")
            return HealthStatus(
                status='error',
                message=f"Database check failed: {str(e)}",
                last_check=time.time()
            )
    
    def _check_redis_health(self) -> HealthStatus:
        """Check Redis connectivity and performance."""
        if not self.redis_client:
            return HealthStatus(
                status='unknown',
                message='Redis client not configured',
                last_check=time.time()
            )
        
        try:
            start_time = time.time()
            
            # Test basic connectivity
            ping_result = self.redis_client.ping()
            if not ping_result:
                return HealthStatus(
                    status='error',
                    message='Redis ping failed',
                    last_check=time.time()
                )
            
            # Test basic operations
            test_key = 'health_check_test'
            self.redis_client.set(test_key, 'test_value', ex=5)
            test_value = self.redis_client.get(test_key)
            self.redis_client.delete(test_key)
            
            response_time = (time.time() - start_time) * 1000
            
            if test_value != 'test_value':
                return HealthStatus(
                    status='error',
                    response_time_ms=round(response_time, 2),
                    message='Redis operations test failed',
                    last_check=time.time()
                )
            
            # Check if response time is acceptable
            status = 'healthy'
            if response_time > 50:  # >50ms is slow for Redis
                status = 'degraded'
            
            # Get Redis info
            redis_info = self.redis_client.info()
            
            return HealthStatus(
                status=status,
                response_time_ms=round(response_time, 2),
                last_check=time.time(),
                details={
                    'connected_clients': redis_info.get('connected_clients'),
                    'used_memory_human': redis_info.get('used_memory_human'),
                    'redis_version': redis_info.get('redis_version'),
                    'uptime_in_seconds': redis_info.get('uptime_in_seconds')
                }
            )
            
        except Exception as e:
            logger.error(f"HEALTH-MONITOR: Redis health check failed: {e}")
            return HealthStatus(
                status='error',
                message=f"Redis check failed: {str(e)}",
                last_check=time.time()
            )
    
    def _check_tickstockpl_connectivity(self) -> HealthStatus:
        """Check TickStockPL service connectivity through Redis channels."""
        if not self.redis_client:
            return HealthStatus(
                status='unknown',
                message='Cannot check TickStockPL - Redis not available',
                last_check=time.time()
            )
        
        try:
            start_time = time.time()
            
            # Check if TickStockPL channels exist and have subscribers
            expected_channels = [
                'tickstock.events.patterns',
                'tickstock.events.backtesting.progress',
                'tickstock.events.backtesting.results'
            ]
            
            channel_info = {}
            total_subscribers = 0
            
            for channel in expected_channels:
                try:
                    # Check if channel has any subscribers (indicating TickStockPL is listening)
                    subscribers = self.redis_client.pubsub_numsub(channel)[0][1]
                    channel_info[channel] = subscribers
                    total_subscribers += subscribers
                except Exception as e:
                    logger.debug(f"HEALTH-MONITOR: Could not check channel {channel}: {e}")
                    channel_info[channel] = 0
            
            response_time = (time.time() - start_time) * 1000
            
            # Determine status based on channel activity
            if total_subscribers > 0:
                status = 'healthy'
                message = f"TickStockPL detected with {total_subscribers} active subscriptions"
            else:
                # Check if we can at least publish (Redis is working)
                try:
                    test_message = json.dumps({
                        'type': 'health_check',
                        'timestamp': time.time(),
                        'source': 'tickstock_appv2'
                    })
                    self.redis_client.publish('tickstock.health.check', test_message)
                    status = 'unknown'
                    message = 'TickStockPL services not detected (no active subscriptions)'
                except Exception:
                    status = 'error'
                    message = 'Cannot communicate with TickStockPL (Redis publish failed)'
            
            return HealthStatus(
                status=status,
                response_time_ms=round(response_time, 2),
                message=message,
                last_check=time.time(),
                details={
                    'expected_channels': expected_channels,
                    'channel_subscribers': channel_info,
                    'total_subscribers': total_subscribers
                }
            )
            
        except Exception as e:
            logger.error(f"HEALTH-MONITOR: TickStockPL connectivity check failed: {e}")
            return HealthStatus(
                status='error',
                message=f"TickStockPL check failed: {str(e)}",
                last_check=time.time()
            )
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get formatted data for health monitoring dashboard."""
        health = self.get_overall_health()
        
        # Get additional dashboard-specific data
        dashboard_data = {
            'health': health,
            'quick_stats': {},
            'alerts': []
        }
        
        # Get database stats if available
        if self.tickstock_db:
            try:
                stats = self.tickstock_db.get_basic_dashboard_stats()
                dashboard_data['quick_stats'] = stats
            except Exception as e:
                logger.debug(f"HEALTH-MONITOR: Could not get dashboard stats: {e}")
                dashboard_data['quick_stats'] = {'error': 'Stats unavailable'}
        
        # Generate alerts based on health status
        for component_name, component_health in health['components'].items():
            if component_health.status in ['error', 'degraded']:
                dashboard_data['alerts'].append({
                    'component': component_name,
                    'status': component_health.status,
                    'message': component_health.message or f"{component_name} is {component_health.status}",
                    'timestamp': component_health.last_check
                })
        
        return dashboard_data
    
    def close(self):
        """Cleanup health monitoring resources."""
        if self.tickstock_db:
            self.tickstock_db.close()
            logger.info("HEALTH-MONITOR: Resources cleaned up")