"""
Pattern Discovery Service - Sprint 19 Phase 1
Service integration layer for Pattern Discovery UI Dashboard backend components.

Architecture:
- Service orchestration: Coordinates Redis pattern cache, database, and API services
- Consumer role: Integrates TickStockPL event consumption with Flask application
- Performance monitoring: Ensures <50ms API response targets are maintained
- Health management: Provides centralized health monitoring for all components
"""

import logging
import time
import threading
from typing import Dict, Any, Optional
from flask import Flask
import redis

from src.infrastructure.cache.redis_pattern_cache import RedisPatternCache
from src.infrastructure.database.tickstock_db import TickStockDatabase
from src.infrastructure.cache.cache_control import CacheControl
from src.infrastructure.redis.redis_connection_manager import RedisConnectionManager, RedisConnectionConfig
from src.core.services.redis_event_subscriber import RedisEventSubscriber, TickStockEvent, EventType

logger = logging.getLogger(__name__)

class PatternDiscoveryService:
    """
    Pattern Discovery Service orchestrates all backend components for the UI Dashboard.
    
    Components:
    - Redis Pattern Cache: Caches TickStockPL pattern events for fast API access
    - TickStock Database: Read-only access to symbols and user data
    - Cache Control: Universe and configuration data management
    - Redis Event Subscriber: Consumes TickStockPL events and forwards to cache
    """
    
    def __init__(self, app: Flask, config: Dict[str, Any]):
        """Initialize Pattern Discovery Service."""
        self.app = app
        self.config = config
        
        # Service components
        self.redis_manager: Optional[RedisConnectionManager] = None
        self.redis_client: Optional[redis.Redis] = None
        self.pattern_cache: Optional[RedisPatternCache] = None
        self.tickstock_db: Optional[TickStockDatabase] = None
        self.cache_control: Optional[CacheControl] = None
        self.event_subscriber: Optional[RedisEventSubscriber] = None
        
        # Service state
        self.initialized = False
        self.services_healthy = False
        
        # Performance tracking
        self.service_stats = {
            'start_time': time.time(),
            'requests_processed': 0,
            'average_response_time': 0.0,
            'last_health_check': None
        }
        
        logger.info("PATTERN-DISCOVERY: Service initialized with config keys: %s", 
                   list(config.keys()))
    
    def initialize(self) -> bool:
        """Initialize all service components."""
        try:
            logger.info("PATTERN-DISCOVERY: Initializing service components...")
            
            # Initialize Redis connection manager
            if not self._initialize_redis():
                return False
            
            # Initialize pattern cache
            if not self._initialize_pattern_cache():
                return False
            
            # Initialize database services
            if not self._initialize_database():
                return False
            
            # Initialize cache control
            if not self._initialize_cache_control():
                return False
            
            # Initialize event subscriber
            if not self._initialize_event_subscriber():
                return False
            
            # Register with Flask app
            self._register_with_app()
            
            # Start background services
            self._start_background_services()
            
            self.initialized = True
            self.services_healthy = True
            
            logger.info("PATTERN-DISCOVERY: All service components initialized successfully")
            return True
            
        except Exception as e:
            logger.error("PATTERN-DISCOVERY: Service initialization failed: %s", e)
            self.shutdown()
            return False
    
    def _initialize_redis(self) -> bool:
        """Initialize Redis connection manager."""
        try:
            # Build Redis configuration
            redis_config = RedisConnectionConfig(
                host=self.config.get('redis_host', 'localhost'),
                port=int(self.config.get('redis_port', 6379)),
                db=int(self.config.get('redis_db', 0)),
                password=self.config.get('redis_password'),
                max_connections=int(self.config.get('redis_max_connections', 20)),
                socket_timeout=2.0,  # Optimized for real-time
                socket_connect_timeout=1.0,
                health_check_interval=15,
                decode_responses=True
            )
            
            # Create and initialize Redis manager
            self.redis_manager = RedisConnectionManager(redis_config)
            
            if not self.redis_manager.initialize():
                logger.error("PATTERN-DISCOVERY: Redis manager initialization failed")
                return False
            
            # Apply real-time optimizations
            self.redis_manager.optimize_for_realtime()
            
            # Get Redis client
            with self.redis_manager.get_connection() as client:
                self.redis_client = client
            
            # Create direct Redis client for pattern cache
            self.redis_client = redis.Redis(
                host=redis_config.host,
                port=redis_config.port,
                db=redis_config.db,
                password=redis_config.password,
                decode_responses=True,
                socket_timeout=2,
                socket_connect_timeout=1
            )
            
            logger.info("PATTERN-DISCOVERY: Redis connection manager initialized")
            return True
            
        except Exception as e:
            logger.error("PATTERN-DISCOVERY: Redis initialization error: %s", e)
            return False
    
    def _initialize_pattern_cache(self) -> bool:
        """Initialize Redis pattern cache manager."""
        try:
            cache_config = {
                'pattern_cache_ttl': self.config.get('pattern_cache_ttl', 3600),
                'api_response_cache_ttl': self.config.get('api_response_cache_ttl', 30),
                'index_cache_ttl': self.config.get('index_cache_ttl', 3600)
            }
            
            self.pattern_cache = RedisPatternCache(self.redis_client, cache_config)
            
            logger.info("PATTERN-DISCOVERY: Pattern cache manager initialized")
            return True
            
        except Exception as e:
            logger.error("PATTERN-DISCOVERY: Pattern cache initialization error: %s", e)
            return False
    
    def _initialize_database(self) -> bool:
        """Initialize TickStock database service."""
        try:
            db_config = {
                'host': self.config.get('database_host'),
                'port': self.config.get('database_port'),
                'database': self.config.get('database_name'),
                'user': self.config.get('database_user'),
                'password': self.config.get('database_password')
            }
            
            self.tickstock_db = TickStockDatabase(db_config)
            
            logger.info("PATTERN-DISCOVERY: TickStock database service initialized")
            return True
            
        except Exception as e:
            logger.error("PATTERN-DISCOVERY: Database initialization error: %s", e)
            return False
    
    def _initialize_cache_control(self) -> bool:
        """Initialize cache control service."""
        try:
            self.cache_control = CacheControl()
            self.cache_control.initialize(environment='PRODUCTION')
            
            logger.info("PATTERN-DISCOVERY: Cache control service initialized")
            return True
            
        except Exception as e:
            logger.error("PATTERN-DISCOVERY: Cache control initialization error: %s", e)
            return False
    
    def _initialize_event_subscriber(self) -> bool:
        """Initialize Redis event subscriber for TickStockPL integration."""
        try:
            subscriber_config = {
                'channels': self.config.get('tickstock_channels', [
                    'tickstock.events.patterns',
                    'tickstock.events.backtesting.progress',
                    'tickstock.events.backtesting.results'
                ])
            }
            
            # Create event subscriber (without SocketIO for now)
            self.event_subscriber = RedisEventSubscriber(
                self.redis_client, 
                None,  # SocketIO will be set later
                subscriber_config
            )
            
            # Add pattern event handler
            self.event_subscriber.add_event_handler(
                EventType.PATTERN_DETECTED,
                self._handle_pattern_event
            )
            
            logger.info("PATTERN-DISCOVERY: Event subscriber initialized")
            return True
            
        except Exception as e:
            logger.error("PATTERN-DISCOVERY: Event subscriber initialization error: %s", e)
            return False
    
    def _register_with_app(self):
        """Register services with Flask app context."""
        try:
            # Make services available to Flask routes
            self.app.pattern_cache = self.pattern_cache
            self.app.tickstock_db = self.tickstock_db
            self.app.cache_control = self.cache_control
            self.app.pattern_discovery_service = self
            
            logger.info("PATTERN-DISCOVERY: Services registered with Flask app")
            
        except Exception as e:
            logger.error("PATTERN-DISCOVERY: Flask registration error: %s", e)
    
    def _start_background_services(self):
        """Start background services."""
        try:
            # Start pattern cache cleanup
            if self.pattern_cache:
                self.pattern_cache.start_background_cleanup()
            
            # Start Redis event subscriber
            if self.event_subscriber:
                self.event_subscriber.start()
            
            logger.info("PATTERN-DISCOVERY: Background services started")
            
        except Exception as e:
            logger.error("PATTERN-DISCOVERY: Background service startup error: %s", e)
    
    def _handle_pattern_event(self, event: TickStockEvent):
        """Handle pattern detection events from TickStockPL."""
        try:
            if self.pattern_cache:
                # Process event in pattern cache
                success = self.pattern_cache.process_pattern_event(event.data)
                
                if success:
                    logger.debug("PATTERN-DISCOVERY: Pattern event processed - %s on %s", 
                               event.data.get('pattern'), event.data.get('symbol'))
                else:
                    logger.warning("PATTERN-DISCOVERY: Failed to process pattern event")
            
        except Exception as e:
            logger.error("PATTERN-DISCOVERY: Error handling pattern event: %s", e)
    
    def set_socketio(self, socketio):
        """Set SocketIO instance for event subscriber."""
        if self.event_subscriber:
            self.event_subscriber.socketio = socketio
            logger.info("PATTERN-DISCOVERY: SocketIO integration enabled")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status of all service components."""
        try:
            # Component health checks
            redis_healthy = self._check_redis_health()
            cache_healthy = self._check_cache_health()
            database_healthy = self._check_database_health()
            subscriber_healthy = self._check_subscriber_health()
            
            # Overall health determination
            components_healthy = redis_healthy and cache_healthy and database_healthy
            
            if subscriber_healthy:
                overall_status = 'healthy' if components_healthy else 'degraded'
            else:
                overall_status = 'warning' if components_healthy else 'error'
            
            health_status = {
                'status': overall_status,
                'healthy': components_healthy and subscriber_healthy,
                'components': {
                    'redis_manager': 'healthy' if redis_healthy else 'error',
                    'pattern_cache': 'healthy' if cache_healthy else 'error',
                    'tickstock_database': 'healthy' if database_healthy else 'error',
                    'event_subscriber': 'healthy' if subscriber_healthy else 'warning'
                },
                'performance': self._get_performance_metrics(),
                'last_check': time.time()
            }
            
            self.service_stats['last_health_check'] = time.time()
            return health_status
            
        except Exception as e:
            logger.error("PATTERN-DISCOVERY: Health check error: %s", e)
            return {
                'status': 'error',
                'healthy': False,
                'error': str(e),
                'last_check': time.time()
            }
    
    def _check_redis_health(self) -> bool:
        """Check Redis connection health."""
        try:
            if not self.redis_manager:
                return False
            health = self.redis_manager.get_health_status()
            return health.get('status') == 'healthy'
        except Exception:
            return False
    
    def _check_cache_health(self) -> bool:
        """Check pattern cache health."""
        try:
            if not self.pattern_cache:
                return False
            stats = self.pattern_cache.get_cache_stats()
            return stats.get('cached_patterns', 0) >= 0  # Basic health check
        except Exception:
            return False
    
    def _check_database_health(self) -> bool:
        """Check database health."""
        try:
            if not self.tickstock_db:
                return False
            health = self.tickstock_db.health_check()
            return health.get('status') in ['healthy', 'degraded']
        except Exception:
            return False
    
    def _check_subscriber_health(self) -> bool:
        """Check event subscriber health."""
        try:
            if not self.event_subscriber:
                return False
            return self.event_subscriber.is_running
        except Exception:
            return False
    
    def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get service performance metrics."""
        runtime = time.time() - self.service_stats['start_time']
        
        return {
            'runtime_seconds': round(runtime, 1),
            'requests_processed': self.service_stats['requests_processed'],
            'average_response_time_ms': self.service_stats['average_response_time'],
            'redis_performance': self.redis_manager.get_performance_metrics() if self.redis_manager else {},
            'pattern_cache_stats': self.pattern_cache.get_cache_stats() if self.pattern_cache else {}
        }
    
    def shutdown(self):
        """Gracefully shutdown all service components."""
        try:
            logger.info("PATTERN-DISCOVERY: Shutting down service components...")
            
            # Stop background services
            if self.pattern_cache:
                self.pattern_cache.stop_background_cleanup()
            
            if self.event_subscriber:
                self.event_subscriber.stop()
            
            # Close database connections
            if self.tickstock_db:
                self.tickstock_db.close()
            
            # Shutdown Redis manager
            if self.redis_manager:
                self.redis_manager.shutdown()
            
            self.initialized = False
            self.services_healthy = False
            
            logger.info("PATTERN-DISCOVERY: Service shutdown complete")
            
        except Exception as e:
            logger.error("PATTERN-DISCOVERY: Error during shutdown: %s", e)

# Global service instance
_global_pattern_discovery_service: Optional[PatternDiscoveryService] = None

def get_pattern_discovery_service() -> Optional[PatternDiscoveryService]:
    """Get global pattern discovery service instance."""
    return _global_pattern_discovery_service

def initialize_pattern_discovery_service(app: Flask, config: Dict[str, Any]) -> bool:
    """Initialize global pattern discovery service."""
    global _global_pattern_discovery_service
    
    if _global_pattern_discovery_service is None:
        _global_pattern_discovery_service = PatternDiscoveryService(app, config)
        success = _global_pattern_discovery_service.initialize()
        
        if success:
            logger.info("PATTERN-DISCOVERY: Global service initialized successfully")
            return True
        else:
            _global_pattern_discovery_service = None
            logger.error("PATTERN-DISCOVERY: Global service initialization failed")
            return False
    else:
        logger.info("PATTERN-DISCOVERY: Global service already initialized")
        return True

def shutdown_pattern_discovery_service():
    """Shutdown global pattern discovery service."""
    global _global_pattern_discovery_service
    
    if _global_pattern_discovery_service:
        _global_pattern_discovery_service.shutdown()
        _global_pattern_discovery_service = None
        logger.info("PATTERN-DISCOVERY: Global service shutdown complete")