"""TickStock Application - Simplified for TickStockPL integration.

PHASE 9 CLEANUP: Simplified to essential Flask/SocketIO application with:
- Basic Flask application setup
- Redis initialization for TickStockPL
- Simplified market data service
- Essential WebSocket support
- Clean startup sequence

Removed: EventDetectionManager, complex initialization, extensive error handling.
"""

import eventlet
eventlet.monkey_patch()

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
import time
import redis
from flask import Flask, render_template, request
from flask_login import login_required, current_user
from flask_socketio import SocketIO, emit, disconnect

# Core application imports
from config.app_config import create_flask_app, initialize_flask_extensions, initialize_socketio
from config.logging_config import configure_logging
import logging
from src.core.services.startup_service import run_startup_sequence
from src.core.services.market_data_service import MarketDataService
from src.presentation.websocket.manager import WebSocketManager

logger = logging.getLogger(__name__)

# Global application components
app = None
market_service = None
redis_client = None
socketio = None

APP_VERSION = "2.0.0-simplified"

def initialize_redis(config):
    """Initialize Redis connection for TickStockPL integration."""
    global redis_client
    
    redis_host = config.get('REDIS_HOST', 'localhost')
    redis_port = config.get('REDIS_PORT', 6379)
    redis_db = config.get('REDIS_DB', 0)
    
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
        logger.info(f"REDIS: Connected to {redis_host}:{redis_port} db={redis_db}")
        
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
    
    @app.route('/')
    def index():
        return render_template('index.html')
    
    @app.route('/health')
    def health_check():
        """Health check endpoint for monitoring."""
        health_data = {
            'status': 'healthy',
            'timestamp': time.time(),
            'redis_connected': redis_client is not None,
            'market_service_running': market_service.is_running() if market_service else False,
            'version': APP_VERSION
        }
        
        if market_service:
            health_data.update(market_service.get_health_status())
        
        return health_data
    
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
        ws_manager = WebSocketManager(socketio, config)
        
        # Initialize market data service
        logger.info("STARTUP: Initializing market data service...")
        market_service = initialize_market_service(config, socketio)
        
        # Register handlers and routes
        logger.info("STARTUP: Registering handlers and routes...")
        register_socketio_handlers(socketio, market_service)
        register_basic_routes(app)
        
        # Import and register API routes
        try:
            from src.api.rest.auth import register_auth_routes
            from src.api.rest.main import register_main_routes
            from src.api.rest.api import register_api_routes
            
            register_auth_routes(app, extensions, cache_control, config)
            register_main_routes(app, extensions, cache_control, config)
            register_api_routes(app, extensions, cache_control, config)
            
            logger.info("STARTUP: API routes registered successfully")
        except ImportError as e:
            logger.warning(f"STARTUP: Some API routes failed to load: {e}")
        
        # Start market data service
        logger.info("STARTUP: Starting market data service...")
        if market_service.start():
            logger.info("STARTUP: Market data service started successfully")
        else:
            logger.error("STARTUP: Failed to start market data service")
            return
        
        logger.info("=" * 60)
        logger.info("✅ TICKSTOCK APPLICATION READY")
        logger.info(f"📊 Data Source: {'Synthetic' if config.get('USE_SYNTHETIC_DATA') else 'Polygon API'}")
        logger.info(f"🔧 Redis: {'Connected' if redis_client else 'Disabled'}")
        logger.info(f"🌐 SocketIO: Enabled")
        logger.info("=" * 60)
        
        # Start the application
        host = config.get('HOST', '0.0.0.0')
        port = config.get('PORT', 5000)
        debug = config.get('DEBUG', False)
        
        logger.info(f"STARTUP: Starting server on {host}:{port} (debug={debug})")
        socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)
        
    except KeyboardInterrupt:
        logger.info("SHUTDOWN: Application interrupted by user")
    except Exception as e:
        logger.error(f"STARTUP-ERROR: {e}")
        raise
    finally:
        # Cleanup
        logger.info("SHUTDOWN: Cleaning up...")
        if market_service:
            market_service.stop()
        if redis_client:
            redis_client.close()
        logger.info("SHUTDOWN: Application stopped")

if __name__ == '__main__':
    main()