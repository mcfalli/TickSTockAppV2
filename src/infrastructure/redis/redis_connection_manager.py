"""
Redis Connection Manager - Sprint 12 Phase 2
High-performance Redis connection management for TickStockPL integration.

Provides connection pooling, failover, health monitoring, and performance optimization
specifically designed for real-time market data streaming with <100ms targets.
"""

import logging
import time
import threading
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from contextlib import contextmanager
import redis
import redis.connection
from redis.retry import Retry
from redis.backoff import ExponentialBackoff

logger = logging.getLogger(__name__)

@dataclass
class RedisConnectionConfig:
    """Redis connection configuration with performance tuning."""
    host: str = 'localhost'
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    max_connections: int = 20
    max_connections_per_pool: int = 50
    socket_timeout: float = 5.0
    socket_connect_timeout: float = 5.0
    socket_keepalive: bool = True
    socket_keepalive_options: Dict[str, int] = None
    health_check_interval: int = 30
    retry_on_timeout: bool = True
    retry_on_error: List = None
    decode_responses: bool = True
    
    def __post_init__(self):
        """Set default values for complex fields."""
        if self.socket_keepalive_options is None:
            self.socket_keepalive_options = {}
        if self.retry_on_error is None:
            self.retry_on_error = [redis.ConnectionError, redis.TimeoutError]

@dataclass
class ConnectionPoolStats:
    """Statistics for Redis connection pool monitoring."""
    pool_id: str
    created_connections: int = 0
    available_connections: int = 0
    in_use_connections: int = 0
    max_connections: int = 0
    total_commands: int = 0
    failed_commands: int = 0
    avg_response_time_ms: float = 0.0
    last_health_check: Optional[float] = None
    health_status: str = 'unknown'
    error_count: int = 0
    reconnection_count: int = 0

class RedisConnectionManager:
    """
    High-performance Redis connection manager for TickStockPL integration.
    
    Features:
    - Connection pooling with performance optimization
    - Automatic failover and reconnection
    - Health monitoring and metrics
    - Circuit breaker pattern for resilience
    - Performance tracking for <100ms targets
    """
    
    def __init__(self, config: RedisConnectionConfig):
        """Initialize Redis connection manager."""
        self.config = config
        self._primary_pool: Optional[redis.ConnectionPool] = None
        self._client: Optional[redis.Redis] = None
        self._pool_stats = ConnectionPoolStats(pool_id="primary")
        
        # Health monitoring
        self._health_check_thread: Optional[threading.Thread] = None
        self._health_check_running = False
        self._last_ping_time = 0
        self._consecutive_failures = 0
        
        # Performance tracking
        self._command_times: List[float] = []
        self._max_tracked_commands = 1000
        
        # Circuit breaker
        self._circuit_breaker_open = False
        self._circuit_breaker_failures = 0
        self._circuit_breaker_threshold = 5
        self._circuit_breaker_reset_timeout = 30
        self._circuit_breaker_last_failure = 0
        
        # Thread safety
        self._lock = threading.RLock()
        
        logger.info("RedisConnectionManager initialized with config: %s", 
                   {k: v for k, v in asdict(config).items() if k != 'password'})
    
    def initialize(self) -> bool:
        """Initialize Redis connection and start health monitoring."""
        try:
            with self._lock:
                logger.info("REDIS-MANAGER: Initializing connection pool...")
                
                # Create connection pool
                self._primary_pool = self._create_connection_pool()
                
                # Create Redis client
                self._client = redis.Redis(
                    connection_pool=self._primary_pool,
                    decode_responses=self.config.decode_responses
                )
                
                # Test connection
                if not self._test_connection():
                    logger.error("REDIS-MANAGER: Initial connection test failed")
                    return False
                
                # Start health monitoring
                self._start_health_monitoring()
                
                # Update stats
                self._pool_stats.max_connections = self.config.max_connections
                self._pool_stats.health_status = 'healthy'
                self._pool_stats.last_health_check = time.time()
                
                logger.info("REDIS-MANAGER: Successfully initialized")
                return True
                
        except Exception as e:
            logger.error("REDIS-MANAGER: Initialization failed: %s", e)
            return False
    
    def _create_connection_pool(self) -> redis.ConnectionPool:
        """Create optimized Redis connection pool."""
        pool_kwargs = {
            'host': self.config.host,
            'port': self.config.port,
            'db': self.config.db,
            'password': self.config.password,
            'max_connections': self.config.max_connections,
            'socket_timeout': self.config.socket_timeout,
            'socket_connect_timeout': self.config.socket_connect_timeout,
            'socket_keepalive': self.config.socket_keepalive,
            'socket_keepalive_options': self.config.socket_keepalive_options,
            'health_check_interval': self.config.health_check_interval,
            'retry_on_timeout': self.config.retry_on_timeout,
            'retry_on_error': self.config.retry_on_error,
            'retry': Retry(ExponentialBackoff(), retries=3)
        }
        
        return redis.ConnectionPool(**pool_kwargs)
    
    def _test_connection(self) -> bool:
        """Test Redis connection with timeout."""
        try:
            start_time = time.time()
            result = self._client.ping()
            response_time = (time.time() - start_time) * 1000
            
            logger.debug("REDIS-MANAGER: Ping successful - %s ms", response_time)
            
            # Track performance
            self._record_command_time(response_time)
            
            return result
            
        except Exception as e:
            logger.error("REDIS-MANAGER: Connection test failed: %s", e)
            self._consecutive_failures += 1
            return False
    
    def _start_health_monitoring(self):
        """Start background health monitoring thread."""
        if self._health_check_running:
            return
            
        self._health_check_running = True
        self._health_check_thread = threading.Thread(
            target=self._health_check_loop,
            name="RedisHealthMonitor",
            daemon=True
        )
        self._health_check_thread.start()
        logger.info("REDIS-MANAGER: Health monitoring started")
    
    def _health_check_loop(self):
        """Background health check loop."""
        while self._health_check_running:
            try:
                # Health check
                if self._test_connection():
                    self._pool_stats.health_status = 'healthy'
                    self._consecutive_failures = 0
                    
                    # Reset circuit breaker if healthy
                    if self._circuit_breaker_open:
                        self._try_reset_circuit_breaker()
                else:
                    self._consecutive_failures += 1
                    
                    if self._consecutive_failures >= 3:
                        self._pool_stats.health_status = 'degraded'
                        self._open_circuit_breaker()
                    elif self._consecutive_failures >= 5:
                        self._pool_stats.health_status = 'error'
                
                # Update pool statistics
                self._update_pool_stats()
                self._pool_stats.last_health_check = time.time()
                
                # Sleep until next check
                time.sleep(self.config.health_check_interval)
                
            except Exception as e:
                logger.error("REDIS-MANAGER: Health check error: %s", e)
                time.sleep(5)  # Shorter sleep on error
    
    def _update_pool_stats(self):
        """Update connection pool statistics."""
        try:
            if self._primary_pool:
                self._pool_stats.created_connections = self._primary_pool.created_connections
                self._pool_stats.available_connections = len(self._primary_pool._available_connections)
                self._pool_stats.in_use_connections = (
                    self._primary_pool.created_connections - 
                    len(self._primary_pool._available_connections)
                )
                
                # Calculate average response time
                if self._command_times:
                    self._pool_stats.avg_response_time_ms = sum(self._command_times) / len(self._command_times)
                
        except Exception as e:
            logger.debug("REDIS-MANAGER: Error updating pool stats: %s", e)
    
    def _record_command_time(self, response_time_ms: float):
        """Record command response time for performance tracking."""
        with self._lock:
            self._command_times.append(response_time_ms)
            
            # Keep only recent command times
            if len(self._command_times) > self._max_tracked_commands:
                self._command_times = self._command_times[-self._max_tracked_commands // 2:]
            
            self._pool_stats.total_commands += 1
            
            # Log slow commands
            if response_time_ms > 100:  # >100ms is concerning for real-time
                logger.warning("REDIS-MANAGER: Slow command - %s ms", response_time_ms)
    
    def _open_circuit_breaker(self):
        """Open circuit breaker to prevent cascade failures."""
        if not self._circuit_breaker_open:
            self._circuit_breaker_open = True
            self._circuit_breaker_last_failure = time.time()
            logger.warning("REDIS-MANAGER: Circuit breaker opened due to consecutive failures")
    
    def _try_reset_circuit_breaker(self):
        """Try to reset circuit breaker if enough time has passed."""
        if (self._circuit_breaker_open and 
            time.time() - self._circuit_breaker_last_failure > self._circuit_breaker_reset_timeout):
            
            self._circuit_breaker_open = False
            self._circuit_breaker_failures = 0
            logger.info("REDIS-MANAGER: Circuit breaker reset - resuming normal operations")
    
    @contextmanager
    def get_connection(self):
        """Get Redis connection with automatic error handling."""
        if self._circuit_breaker_open:
            raise redis.ConnectionError("Redis circuit breaker is open")
        
        connection = None
        start_time = time.time()
        
        try:
            connection = self._client
            yield connection
            
            # Record successful command
            response_time = (time.time() - start_time) * 1000
            self._record_command_time(response_time)
            
        except Exception as e:
            self._pool_stats.failed_commands += 1
            self._circuit_breaker_failures += 1
            
            if self._circuit_breaker_failures >= self._circuit_breaker_threshold:
                self._open_circuit_breaker()
            
            logger.error("REDIS-MANAGER: Command failed: %s", e)
            raise
    
    def execute_command(self, command: str, *args, **kwargs) -> Any:
        """Execute Redis command with performance tracking."""
        start_time = time.time()
        
        try:
            with self.get_connection() as client:
                result = getattr(client, command)(*args, **kwargs)
                
                response_time = (time.time() - start_time) * 1000
                self._record_command_time(response_time)
                
                return result
                
        except Exception as e:
            logger.error("REDIS-MANAGER: Command '%s' failed: %s", command, e)
            raise
    
    def publish_message(self, channel: str, message: Any) -> bool:
        """Publish message with performance tracking."""
        try:
            if isinstance(message, dict):
                message = json.dumps(message)
            
            result = self.execute_command('publish', channel, message)
            return result > 0
            
        except Exception as e:
            logger.error("REDIS-MANAGER: Publish failed for channel '%s': %s", channel, e)
            return False
    
    def create_subscriber(self, channels: List[str]) -> redis.client.PubSub:
        """Create PubSub subscriber with optimal configuration."""
        try:
            with self.get_connection() as client:
                pubsub = client.pubsub()
                pubsub.subscribe(channels)
                
                logger.info("REDIS-MANAGER: Created subscriber for %s channels", len(channels))
                return pubsub
                
        except Exception as e:
            logger.error("REDIS-MANAGER: Failed to create subscriber: %s", e)
            raise
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status."""
        return {
            'status': self._pool_stats.health_status,
            'connected': not self._circuit_breaker_open,
            'consecutive_failures': self._consecutive_failures,
            'circuit_breaker_open': self._circuit_breaker_open,
            'pool_stats': asdict(self._pool_stats),
            'performance': {
                'avg_response_time_ms': self._pool_stats.avg_response_time_ms,
                'total_commands': self._pool_stats.total_commands,
                'failed_commands': self._pool_stats.failed_commands,
                'success_rate': self._calculate_success_rate(),
                'commands_per_second': self._calculate_commands_per_second()
            },
            'config': {
                'host': self.config.host,
                'port': self.config.port,
                'db': self.config.db,
                'max_connections': self.config.max_connections
            },
            'last_check': self._pool_stats.last_health_check
        }
    
    def _calculate_success_rate(self) -> float:
        """Calculate command success rate."""
        total = self._pool_stats.total_commands
        if total == 0:
            return 1.0
        
        failed = self._pool_stats.failed_commands
        return (total - failed) / total
    
    def _calculate_commands_per_second(self) -> float:
        """Calculate approximate commands per second."""
        if not self._command_times or len(self._command_times) < 2:
            return 0.0
        
        # Simple approximation based on recent command volume
        recent_commands = min(100, len(self._command_times))
        return recent_commands / 60.0  # Rough estimate
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get detailed performance metrics."""
        with self._lock:
            command_times = self._command_times.copy()
        
        if not command_times:
            return {
                'total_commands': 0,
                'avg_response_time_ms': 0,
                'median_response_time_ms': 0,
                'p95_response_time_ms': 0,
                'p99_response_time_ms': 0,
                'slow_commands': 0
            }
        
        command_times.sort()
        count = len(command_times)
        
        return {
            'total_commands': self._pool_stats.total_commands,
            'recent_sample_size': count,
            'avg_response_time_ms': sum(command_times) / count,
            'median_response_time_ms': command_times[count // 2],
            'p95_response_time_ms': command_times[int(count * 0.95)],
            'p99_response_time_ms': command_times[int(count * 0.99)],
            'min_response_time_ms': command_times[0],
            'max_response_time_ms': command_times[-1],
            'slow_commands': len([t for t in command_times if t > 100]),
            'very_slow_commands': len([t for t in command_times if t > 500])
        }
    
    def optimize_for_realtime(self):
        """Apply real-time optimization settings."""
        try:
            logger.info("REDIS-MANAGER: Applying real-time optimizations...")
            
            # Reduce timeouts for faster failure detection
            self.config.socket_timeout = 2.0
            self.config.socket_connect_timeout = 1.0
            
            # Enable keepalive for stable connections
            self.config.socket_keepalive = True
            self.config.socket_keepalive_options = {
                'TCP_KEEPIDLE': 1,
                'TCP_KEEPINTVL': 1,
                'TCP_KEEPCNT': 3
            }
            
            # Increase connection pool for high throughput
            if self.config.max_connections < 50:
                self.config.max_connections = 50
            
            # More aggressive health checking
            self.config.health_check_interval = 15
            
            # Recreate pool with new settings
            if self._primary_pool:
                self._primary_pool.disconnect()
                self._primary_pool = self._create_connection_pool()
                self._client = redis.Redis(
                    connection_pool=self._primary_pool,
                    decode_responses=self.config.decode_responses
                )
            
            logger.info("REDIS-MANAGER: Real-time optimizations applied")
            
        except Exception as e:
            logger.error("REDIS-MANAGER: Failed to apply real-time optimizations: %s", e)
    
    def shutdown(self):
        """Gracefully shutdown connection manager."""
        logger.info("REDIS-MANAGER: Shutting down...")
        
        # Stop health monitoring
        self._health_check_running = False
        if self._health_check_thread and self._health_check_thread.is_alive():
            self._health_check_thread.join(timeout=5)
        
        # Close connections
        if self._primary_pool:
            try:
                self._primary_pool.disconnect()
            except Exception as e:
                logger.error("REDIS-MANAGER: Error disconnecting pool: %s", e)
        
        self._client = None
        self._primary_pool = None
        
        logger.info("REDIS-MANAGER: Shutdown complete")

# Global connection manager instance
_global_redis_manager: Optional[RedisConnectionManager] = None
_manager_lock = threading.Lock()

def get_redis_manager() -> Optional[RedisConnectionManager]:
    """Get global Redis connection manager instance."""
    return _global_redis_manager

def initialize_global_redis_manager(config: RedisConnectionConfig) -> bool:
    """Initialize global Redis connection manager."""
    global _global_redis_manager
    
    with _manager_lock:
        if _global_redis_manager is None:
            _global_redis_manager = RedisConnectionManager(config)
            success = _global_redis_manager.initialize()
            
            if success:
                # Apply real-time optimizations for TickStockPL integration
                _global_redis_manager.optimize_for_realtime()
                logger.info("Global Redis connection manager initialized successfully")
                return True
            else:
                _global_redis_manager = None
                logger.error("Failed to initialize global Redis connection manager")
                return False
        else:
            logger.info("Global Redis connection manager already initialized")
            return True

def shutdown_global_redis_manager():
    """Shutdown global Redis connection manager."""
    global _global_redis_manager
    
    with _manager_lock:
        if _global_redis_manager:
            _global_redis_manager.shutdown()
            _global_redis_manager = None
            logger.info("Global Redis connection manager shutdown complete")