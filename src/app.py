"""TickStock Application - Simplified for TickStockPL integration.

PHASE 9 CLEANUP: Simplified to essential Flask/SocketIO application with:
- Basic Flask application setup
- Redis initialization for TickStockPL
- Simplified market data service
- Essential WebSocket support
- Clean startup sequence

Removed: EventDetectionManager, complex initialization, extensive error handling.
"""

# CRITICAL: eventlet monkey patch must be FIRST before any other imports
import eventlet
eventlet.monkey_patch(
    os=True, 
    select=True, 
    socket=True, 
    thread=True, 
    time=True
)

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
import time
import logging

# Import Redis and Flask components after monkey patch
import redis
from flask import Flask, render_template, request
from flask_login import login_required, current_user
from flask_socketio import SocketIO, emit, disconnect

# Core application imports
from config.app_config import create_flask_app, initialize_flask_extensions, initialize_socketio
from config.logging_config import configure_logging
from src.core.services.startup_service import run_startup_sequence
from src.core.services.market_data_service import MarketDataService
from src.presentation.websocket.manager import WebSocketManager

# Sprint 10 Phase 2: Enhanced Redis Event Consumption
from src.core.services.redis_event_subscriber import RedisEventSubscriber
from src.core.services.websocket_broadcaster import WebSocketBroadcaster

logger = logging.getLogger(__name__)

# Global application components
app = None
market_service = None
redis_client = None
socketio = None

# Sprint 10 Phase 2: TickStockPL Integration Services
redis_event_subscriber = None
websocket_broadcaster = None

# Sprint 10 Phase 4: Pattern Alert System
pattern_alert_manager = None

APP_VERSION = "2.0.0-simplified"

def initialize_redis(config):
    """Initialize Redis connection for TickStockPL integration."""
    global redis_client
    
    # Check if Redis is configured (try config first, then environment)
    redis_url = config.get('REDIS_URL') or os.getenv('REDIS_URL', '')
    
    if not redis_url or redis_url.strip() == '':
        logger.info("REDIS: No Redis URL configured, skipping Redis initialization")
        redis_client = None
        return False
    
    redis_host = config.get('REDIS_HOST') or os.getenv('REDIS_HOST', 'localhost')
    redis_port = int(config.get('REDIS_PORT') or os.getenv('REDIS_PORT', 6379))
    redis_db = int(config.get('REDIS_DB') or os.getenv('REDIS_DB', 0))
    
    logger.info(f"REDIS: Attempting to connect to {redis_host}:{redis_port} db={redis_db}")
    
    try:
        redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            decode_responses=True,
            socket_timeout=2,
            socket_connect_timeout=2,
            health_check_interval=30
        )
        
        # Test connection with timeout
        redis_client.ping()
        logger.info(f"REDIS: Connected successfully to {redis_host}:{redis_port} db={redis_db}")
        
        # Add Redis client to config for other components
        config['redis_client'] = redis_client
        return True
        
    except Exception as e:
        logger.warning(f"REDIS: Connection failed: {e}")
        redis_client = None
        return False

def initialize_market_service(config, socketio):
    """Initialize simplified market data service."""
    try:
        logger.info("MARKET-SERVICE: Initializing simplified market data service")
        
        # Create market service with SocketIO
        market_service = MarketDataService(config, socketio)
        
        logger.info("MARKET-SERVICE: Service initialized successfully")
        return market_service
        
    except Exception as e:
        logger.error(f"MARKET-SERVICE: Initialization failed: {e}")
        raise

def initialize_tickstockpl_services(config, socketio, redis_client):
    """Initialize TickStockPL integration services for Phase 2-4."""
    global redis_event_subscriber, websocket_broadcaster, pattern_alert_manager
    
    try:
        logger.info("TICKSTOCKPL-SERVICES: Initializing integration services...")
        
        # Initialize WebSocket broadcaster
        websocket_broadcaster = WebSocketBroadcaster(socketio, redis_client)
        logger.info("TICKSTOCKPL-SERVICES: WebSocket broadcaster initialized")
        
        # Initialize Pattern Alert Manager (Phase 4)
        if redis_client:
            from src.core.services.pattern_alert_manager import PatternAlertManager
            pattern_alert_manager = PatternAlertManager(redis_client, config)
            logger.info("TICKSTOCKPL-SERVICES: Pattern alert manager initialized")
        
        # Initialize Redis event subscriber if Redis is available
        if redis_client:
            # The backtest manager will be injected later when the API routes are registered
            redis_event_subscriber = RedisEventSubscriber(redis_client, socketio, config)
            
            # Connect event subscriber to broadcaster
            from src.core.services.redis_event_subscriber import EventType
            
            # Register broadcaster handlers with subscriber
            redis_event_subscriber.add_event_handler(
                EventType.PATTERN_DETECTED, 
                lambda event: websocket_broadcaster.broadcast_pattern_alert(event.to_websocket_dict())
            )
            redis_event_subscriber.add_event_handler(
                EventType.BACKTEST_PROGRESS,
                lambda event: websocket_broadcaster.broadcast_backtest_progress(event.to_websocket_dict())
            )
            redis_event_subscriber.add_event_handler(
                EventType.BACKTEST_RESULT,
                lambda event: websocket_broadcaster.broadcast_backtest_result(event.to_websocket_dict())
            )
            redis_event_subscriber.add_event_handler(
                EventType.SYSTEM_HEALTH,
                lambda event: websocket_broadcaster.broadcast_system_health(event.to_websocket_dict())
            )
            
            # Start subscriber
            if redis_event_subscriber.start():
                logger.info("TICKSTOCKPL-SERVICES: Redis event subscriber started successfully")
            else:
                logger.warning("TICKSTOCKPL-SERVICES: Redis event subscriber failed to start")
        else:
            logger.warning("TICKSTOCKPL-SERVICES: Redis not available - event subscriber disabled")
        
        logger.info("TICKSTOCKPL-SERVICES: All integration services initialized")
        return True
        
    except Exception as e:
        logger.error(f"TICKSTOCKPL-SERVICES: Initialization failed: {e}")
        return False

def register_socketio_handlers(socketio, market_service):
    """Register essential SocketIO event handlers."""
    
    @socketio.on('connect')
    def handle_connect():
        logger.info(f"CLIENT-CONNECT: User connected")
        if hasattr(market_service, 'websocket_publisher'):
            user_id = getattr(current_user, 'id', 'anonymous')
            market_service.websocket_publisher.add_user(user_id, request.sid)
    
    @socketio.on('disconnect')
    def handle_disconnect():
        logger.info(f"CLIENT-DISCONNECT: User disconnected")
        if hasattr(market_service, 'websocket_publisher'):
            user_id = getattr(current_user, 'id', 'anonymous')
            market_service.websocket_publisher.remove_user(user_id)
    
    @socketio.on('subscribe_tickers')
    def handle_subscribe_tickers(data):
        """Handle ticker subscription requests."""
        try:
            tickers = data.get('tickers', [])
            user_id = getattr(current_user, 'id', 'anonymous')
            
            if hasattr(market_service, 'websocket_publisher'):
                market_service.websocket_publisher.update_user_subscriptions(user_id, tickers)
                emit('subscription_updated', {'tickers': tickers})
                logger.info(f"USER-SUBSCRIPTION: Updated for {user_id}: {len(tickers)} tickers")
            
        except Exception as e:
            logger.error(f"SUBSCRIPTION-ERROR: {e}")
            emit('error', {'message': 'Subscription failed'})

def register_basic_routes(app):
    """Register essential application routes."""
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"FLASK-ERROR-500: {error}")
        logger.error(f"FLASK-ERROR-500: Exception details: {error.__dict__ if hasattr(error, '__dict__') else 'No details available'}")
        return {"error": "Internal server error", "message": str(error)}, 500
    
    @app.errorhandler(404)
    def not_found(error):
        logger.warning(f"FLASK-ERROR-404: {error}")
        return {"error": "Not found", "message": str(error)}, 404
    
    @app.route('/')
    def index():
        try:
            logger.info("ROUTE: Index page requested")
            return render_template('dashboard/index.html')
        except Exception as e:
            logger.error(f"ROUTE-ERROR: Index route failed: {e}")
            raise
    
    @app.route('/health')
    def health_check():
        """Health check endpoint for monitoring."""
        return {"status": "healthy", "version": APP_VERSION}
    
    @app.route('/test')  
    def test_route():
        """Simple test route to verify routing works."""
        return "TickStock Test Route - Working!"
    
    @app.route('/stats')
    @login_required
    def stats():
        """Statistics endpoint for administrators."""
        stats_data = {
            'app_version': APP_VERSION,
            'redis_connected': redis_client is not None,
        }
        
        if market_service:
            stats_data['market_service'] = market_service.get_stats()
        
        return stats_data

def main():
    """Main application entry point."""
    global app, market_service, socketio
    
    try:
        logger.info("=" * 60)
        logger.info("🚀 TICKSTOCK APPLICATION STARTING (Simplified)")
        logger.info("=" * 60)
        
        # Run startup sequence
        logger.info("STARTUP: Running startup sequence...")
        startup_result = run_startup_sequence()
        config = startup_result['config']
        cache_control = startup_result['cache_control']
        
        # Configure logging with the loaded config
        logger.info("STARTUP: Configuring logging...")
        configure_logging(config)
        logger.info("STARTUP: Logging configured successfully")
        
        # Create Flask application
        logger.info("STARTUP: Creating Flask application...")
        app = create_flask_app(startup_result['env_config'], cache_control, config)
        extensions = initialize_flask_extensions(app)
        
        # Initialize Redis
        logger.info("STARTUP: Initializing Redis...")
        redis_success = initialize_redis(config)
        if not redis_success:
            logger.warning("STARTUP: Redis connection failed - continuing without Redis")
        
        # Initialize SocketIO
        logger.info("STARTUP: Initializing SocketIO...")
        socketio = initialize_socketio(app, cache_control, config)
        
        # Initialize WebSocket manager
        logger.info("STARTUP: Initializing WebSocket manager...")
        try:
            ws_manager = WebSocketManager(socketio, config)
            logger.info("STARTUP: WebSocket manager initialized successfully")
        except Exception as e:
            logger.error(f"STARTUP: WebSocket manager initialization failed: {e}")
            raise
        
        # Initialize market data service
        logger.info("STARTUP: Initializing market data service...")
        try:
            market_service = initialize_market_service(config, socketio)
            logger.info("STARTUP: Market data service initialized successfully")
        except Exception as e:
            logger.error(f"STARTUP: Market data service initialization failed: {e}")
            raise
        
        # Register handlers and routes
        logger.info("STARTUP: Registering SocketIO handlers...")
        try:
            register_socketio_handlers(socketio, market_service)
            logger.info("STARTUP: SocketIO handlers registered successfully")
        except Exception as e:
            logger.error(f"STARTUP: SocketIO handler registration failed: {e}")
            raise
        
        # Routes are registered in the following functions
            
        logger.info("STARTUP: Registering basic routes...")
        try:
            register_basic_routes(app)
            logger.info("STARTUP: Basic routes registered successfully")
        except Exception as e:
            logger.error(f"STARTUP: Basic route registration failed: {e}")
            raise
        
        # Import and register API routes
        logger.info("STARTUP: Registering API routes...")
        try:
            from src.api.rest.auth import register_auth_routes
            from src.api.rest.main import register_main_routes
            from src.api.rest.api import register_api_routes
            from src.api.rest.tickstockpl_api import register_tickstockpl_routes
            
            logger.info("STARTUP: Registering auth routes...")
            register_auth_routes(app, extensions, cache_control, config)
            logger.info("STARTUP: Auth routes registered successfully")
            
            logger.info("STARTUP: Registering main routes...")
            register_main_routes(app, extensions, cache_control, config)
            logger.info("STARTUP: Main routes registered successfully")
            
            logger.info("STARTUP: Registering API routes...")
            register_api_routes(app, extensions, cache_control, config)
            logger.info("STARTUP: API routes registered successfully")
            
            logger.info("STARTUP: Registering TickStockPL API routes...")
            register_tickstockpl_routes(app, extensions, cache_control, config)
            logger.info("STARTUP: TickStockPL API routes registered successfully")
            
        except ImportError as e:
            logger.warning(f"STARTUP: Some API routes failed to load: {e}")
        except Exception as e:
            logger.error(f"STARTUP: API route registration failed: {e}")
            raise
        
        # Initialize TickStockPL integration services (Phase 2)
        logger.info("STARTUP: Initializing TickStockPL integration services...")
        try:
            if initialize_tickstockpl_services(config, socketio, redis_client):
                logger.info("STARTUP: TickStockPL integration services initialized successfully")
            else:
                logger.warning("STARTUP: TickStockPL integration services initialization incomplete")
        except Exception as e:
            logger.error(f"STARTUP: TickStockPL services initialization failed: {e}")
            # Don't fail startup - continue without TickStockPL integration
        
        # After API routes are registered, connect backtest manager to redis subscriber
        try:
            if redis_event_subscriber and hasattr(app, 'backtest_manager'):
                redis_event_subscriber.set_backtest_manager(app.backtest_manager)
                logger.info("STARTUP: Backtest manager connected to Redis subscriber")
        except Exception as e:
            logger.error(f"STARTUP: Failed to connect backtest manager: {e}")
        
        # Make pattern alert manager available to Flask app context
        if pattern_alert_manager:
            app.pattern_alert_manager = pattern_alert_manager
            logger.info("STARTUP: Pattern alert manager attached to Flask app")
        
        # Start market data service
        logger.info("STARTUP: Starting market data service...")
        try:
            if market_service.start():
                logger.info("STARTUP: Market data service started successfully")
            else:
                logger.error("STARTUP: Failed to start market data service")
                return
        except Exception as e:
            logger.error(f"STARTUP: Market data service start failed: {e}")
            raise
        
        logger.info("=" * 60)
        logger.info("✅ TICKSTOCK APPLICATION READY")
        logger.info(f"📊 Data Source: {'Synthetic' if config.get('USE_SYNTHETIC_DATA') else 'Polygon API'}")
        logger.info(f"🔧 Redis: {'Connected' if redis_client else 'Disabled'}")
        logger.info(f"🌐 SocketIO: Enabled")
        logger.info("=" * 60)
        
        # Start the application
        host = config.get('APP_HOST', '0.0.0.0')
        port = config.get('APP_PORT', 5000)
        debug = config.get('APP_DEBUG', False)
        
        logger.info(f"STARTUP: Starting server on {host}:{port} (debug={debug})")
        # Use SocketIO server (required for WebSocket functionality)
        socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)
        
    except KeyboardInterrupt:
        logger.info("SHUTDOWN: Application interrupted by user")
    except Exception as e:
        logger.error(f"STARTUP-ERROR: {e}")
        raise
    finally:
        # Cleanup
        logger.info("SHUTDOWN: Cleaning up...")
        
        # Stop TickStockPL integration services
        if redis_event_subscriber:
            redis_event_subscriber.stop()
        
        if pattern_alert_manager:
            pattern_alert_manager.cleanup_expired_data()
        
        if market_service:
            market_service.stop()
            
        if redis_client:
            redis_client.close()
            
        logger.info("SHUTDOWN: Application stopped")

if __name__ == '__main__':
    main()