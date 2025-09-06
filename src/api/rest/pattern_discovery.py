"""
Pattern Discovery API Integration
Flask blueprint registration and service integration for Pattern Discovery UI Dashboard.

Architecture:
- Blueprint registration: Pattern consumer API, user universe API
- Service initialization: Pattern discovery service, Redis cache, database
- Performance monitoring: API performance tracking and health endpoints
- Error handling: Consistent error responses across all endpoints
"""

import logging
import os
from typing import Dict, Any
from flask import Flask, jsonify

from src.api.rest.pattern_consumer import pattern_consumer_bp
from src.api.rest.user_universe import user_universe_bp
from src.core.services.pattern_discovery_service import (
    initialize_pattern_discovery_service,
    shutdown_pattern_discovery_service,
    get_pattern_discovery_service
)

logger = logging.getLogger(__name__)

def register_pattern_discovery_apis(app: Flask) -> bool:
    """
    Register Pattern Discovery API blueprints and initialize backend services.
    
    Args:
        app: Flask application instance
        
    Returns:
        bool: True if initialization successful, False otherwise
    """
    try:
        logger.info("PATTERN-DISCOVERY-API: Initializing Pattern Discovery APIs...")
        
        # Load configuration
        config = _load_pattern_discovery_config()
        
        # Initialize Pattern Discovery Service
        if not initialize_pattern_discovery_service(app, config):
            logger.error("PATTERN-DISCOVERY-API: Failed to initialize pattern discovery service")
            return False
        
        # Register API blueprints
        app.register_blueprint(pattern_consumer_bp, url_prefix='')
        app.register_blueprint(user_universe_bp, url_prefix='')
        
        # Register health endpoint
        _register_health_endpoints(app)
        
        # Register error handlers
        _register_error_handlers(app)
        
        logger.info("PATTERN-DISCOVERY-API: Pattern Discovery APIs initialized successfully")
        return True
        
    except Exception as e:
        logger.error("PATTERN-DISCOVERY-API: Initialization error: %s", e)
        return False

def _load_pattern_discovery_config() -> Dict[str, Any]:
    """Load configuration for Pattern Discovery components."""
    return {
        # Redis configuration
        'redis_host': os.getenv('REDIS_HOST', 'localhost'),
        'redis_port': int(os.getenv('REDIS_PORT', 6379)),
        'redis_db': int(os.getenv('REDIS_DB', 0)),
        'redis_password': os.getenv('REDIS_PASSWORD'),
        'redis_max_connections': int(os.getenv('REDIS_MAX_CONNECTIONS', 20)),
        
        # Pattern cache configuration
        'pattern_cache_ttl': int(os.getenv('PATTERN_CACHE_TTL', 3600)),  # 1 hour
        'api_response_cache_ttl': int(os.getenv('API_RESPONSE_CACHE_TTL', 30)),  # 30 seconds
        'index_cache_ttl': int(os.getenv('INDEX_CACHE_TTL', 3600)),  # 1 hour
        
        # Database configuration (from existing environment)
        'database_host': os.getenv('TICKSTOCK_DB_HOST', 'localhost'),
        'database_port': int(os.getenv('TICKSTOCK_DB_PORT', 5433)),
        'database_name': 'tickstock',
        'database_user': os.getenv('TICKSTOCK_DB_USER', 'app_readwrite'),
        'database_password': os.getenv('TICKSTOCK_DB_PASSWORD', 'LJI48rUEkUpe6e'),
        
        # TickStockPL integration channels
        'tickstock_channels': [
            'tickstock.events.patterns',
            'tickstock.events.backtesting.progress', 
            'tickstock.events.backtesting.results',
            'tickstock.health.status'
        ],
        
        # Performance targets
        'api_response_target_ms': 50,
        'websocket_latency_target_ms': 100,
        'cache_hit_ratio_target': 0.7
    }

def _register_health_endpoints(app: Flask):
    """Register centralized health endpoints for Pattern Discovery components."""
    
    @app.route('/api/pattern-discovery/health', methods=['GET'])
    def pattern_discovery_health():
        """
        Comprehensive health check for all Pattern Discovery components.
        
        Returns:
            JSON response with health status of all services
        """
        try:
            # Get pattern discovery service
            service = get_pattern_discovery_service()
            if not service:
                return jsonify({
                    'status': 'error',
                    'healthy': False,
                    'message': 'Pattern discovery service not initialized',
                    'components': {}
                }), 503
            
            # Get comprehensive health status
            health_status = service.get_health_status()
            
            # Determine HTTP status code
            if health_status['status'] == 'healthy':
                status_code = 200
            elif health_status['status'] in ['degraded', 'warning']:
                status_code = 200  # Still operational
            else:
                status_code = 503  # Service unavailable
            
            return jsonify(health_status), status_code
            
        except Exception as e:
            logger.error("PATTERN-DISCOVERY-API: Health check error: %s", e)
            return jsonify({
                'status': 'error',
                'healthy': False,
                'message': f'Health check failed: {str(e)}'
            }), 500
    
    @app.route('/api/pattern-discovery/performance', methods=['GET'])
    def pattern_discovery_performance():
        """
        Performance metrics for all Pattern Discovery components.
        
        Returns:
            JSON response with performance metrics
        """
        try:
            service = get_pattern_discovery_service()
            if not service:
                return jsonify({
                    'error': 'Pattern discovery service not available'
                }), 503
            
            health_status = service.get_health_status()
            performance_metrics = health_status.get('performance', {})
            
            # Add performance targets for comparison
            performance_metrics['targets'] = {
                'api_response_time_ms': 50,
                'websocket_latency_ms': 100,
                'cache_hit_ratio': 0.7
            }
            
            return jsonify({
                'performance': performance_metrics,
                'status': 'healthy' if health_status.get('healthy') else 'degraded'
            })
            
        except Exception as e:
            logger.error("PATTERN-DISCOVERY-API: Performance check error: %s", e)
            return jsonify({
                'error': f'Performance check failed: {str(e)}'
            }), 500

def _register_error_handlers(app: Flask):
    """Register consistent error handlers for Pattern Discovery APIs."""
    
    @app.errorhandler(429)  # Rate limiting
    def rate_limit_handler(e):
        return jsonify({
            'error': 'Rate limit exceeded',
            'message': 'Too many requests. Please slow down.',
            'retry_after': getattr(e, 'retry_after', 60)
        }), 429
    
    @app.errorhandler(503)  # Service unavailable
    def service_unavailable_handler(e):
        return jsonify({
            'error': 'Service temporarily unavailable',
            'message': 'The service is currently under maintenance or experiencing issues. Please try again later.',
        }), 503

def setup_pattern_discovery_socketio(socketio):
    """
    Set up SocketIO integration for real-time pattern updates.
    
    Args:
        socketio: Flask-SocketIO instance
    """
    try:
        # Get pattern discovery service
        service = get_pattern_discovery_service()
        if service:
            service.set_socketio(socketio)
            logger.info("PATTERN-DISCOVERY-API: SocketIO integration configured")
        else:
            logger.warning("PATTERN-DISCOVERY-API: Pattern discovery service not available for SocketIO integration")
            
    except Exception as e:
        logger.error("PATTERN-DISCOVERY-API: SocketIO integration error: %s", e)

def cleanup_pattern_discovery_services():
    """Clean up Pattern Discovery services on application shutdown."""
    try:
        logger.info("PATTERN-DISCOVERY-API: Cleaning up Pattern Discovery services...")
        shutdown_pattern_discovery_service()
        logger.info("PATTERN-DISCOVERY-API: Pattern Discovery cleanup complete")
        
    except Exception as e:
        logger.error("PATTERN-DISCOVERY-API: Cleanup error: %s", e)

# Flask application lifecycle integration
def init_app(app: Flask) -> bool:
    """Initialize Pattern Discovery components with Flask app."""
    
    # Register APIs and services
    success = register_pattern_discovery_apis(app)
    
    if success:
        logger.info("PATTERN-DISCOVERY-API: Pattern Discovery integration successful")
        
        # Register cleanup handler
        import atexit
        atexit.register(cleanup_pattern_discovery_services)
        
    else:
        logger.error("PATTERN-DISCOVERY-API: Pattern Discovery integration failed")
    
    return success