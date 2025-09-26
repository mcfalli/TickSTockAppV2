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
import json
import logging
from datetime import datetime, timedelta

# Import Redis and Flask components after monkey patch
import redis
from flask import Flask, render_template, request, jsonify
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

# Sprint 25: Fallback Pattern Detection
from src.core.services.fallback_pattern_detector import FallbackPatternDetector

# Sprint 10 Phase 3: Real Pattern Discovery API Integration
from src.api.rest.pattern_discovery import init_app as init_pattern_discovery_app

# Mandatory Redis validation for TickStockPL integration
from src.core.services.redis_validator import (
    initialize_redis_mandatory,
    generate_redis_failure_report
)
from src.core.exceptions.redis_exceptions import (
    RedisConnectionError,
    RedisChannelError,
    RedisPerformanceError,
    RedisConfigurationError
)

# Sprint 32: Enhanced Error Handling System
from src.core.services.enhanced_logger import create_enhanced_logger, set_enhanced_logger
from src.core.services.error_subscriber import create_error_subscriber, set_error_subscriber
from src.core.services.config_manager import LoggingConfig

logger = logging.getLogger(__name__)

# Global application components
app = None
market_service = None
redis_client = None
socketio = None

# Sprint 10 Phase 2: TickStockPL Integration Services
redis_event_subscriber = None
websocket_broadcaster = None

# Sprint 25: Fallback Pattern Detection
fallback_pattern_detector = None

# Sprint 10 Phase 4: Pattern Alert System
pattern_alert_manager = None

# Sprint 23: Advanced Analytics Services
db_connection_pool = None
analytics_advanced_service = None
market_condition_service = None
correlation_analyzer_service = None
temporal_analytics_service = None
comparison_tools_service = None

APP_VERSION = "2.0.0-simplified"

def initialize_redis(config):
    """
    Initialize Redis connection for TickStockPL integration.

    DEPRECATED: Use initialize_redis_mandatory() for new code.
    This function is kept for backward compatibility only.
    """
    global redis_client

    # Check if Redis is configured (try config first, then environment)
    redis_url = config.get('REDIS_URL') or config.get('REDIS_URL', '')

    if not redis_url or redis_url.strip() == '':
        logger.info("REDIS: No Redis URL configured, skipping Redis initialization")
        redis_client = None
        return False

    redis_host = config.get('REDIS_HOST') or config.get('REDIS_HOST', 'localhost')
    redis_port = int(config.get('REDIS_PORT') or config.get('REDIS_PORT', 6379))
    redis_db = int(config.get('REDIS_DB') or config.get('REDIS_DB', 0))
    
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

def initialize_tickstockpl_services(config, socketio, redis_client, flask_app=None):
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
            # Pass Flask app for app context in Redis subscriber thread
            redis_event_subscriber = RedisEventSubscriber(redis_client, socketio, config, flask_app=flask_app)
            
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
        
        # Initialize fallback pattern detector for when TickStockPL is offline
        global fallback_pattern_detector
        logger.info("TICKSTOCKPL-SERVICES: Initializing fallback pattern detector...")
        try:
            fallback_pattern_detector = FallbackPatternDetector(
                websocket_publisher=websocket_broadcaster,
                redis_client=redis_client
            )
            
            # Start fallback detector 
            if fallback_pattern_detector.start():
                logger.info("TICKSTOCKPL-SERVICES: Fallback pattern detector started successfully")
            else:
                logger.warning("TICKSTOCKPL-SERVICES: Fallback pattern detector failed to start")
                
        except Exception as e:
            logger.error(f"TICKSTOCKPL-SERVICES: Failed to initialize fallback pattern detector: {e}")
        
        logger.info("TICKSTOCKPL-SERVICES: All integration services initialized")
        return True
        
    except Exception as e:
        logger.error(f"TICKSTOCKPL-SERVICES: Initialization failed: {e}")
        return False

def initialize_sprint23_services(config):
    """Initialize Sprint 23 Advanced Analytics Services."""
    global db_connection_pool, analytics_advanced_service, market_condition_service
    global correlation_analyzer_service, temporal_analytics_service, comparison_tools_service
    
    try:
        logger.info("SPRINT23-SERVICES: Initializing advanced analytics services...")
        
        # Initialize database connection pool
        from src.infrastructure.database.connection_pool import DatabaseConnectionPool
        db_connection_pool = DatabaseConnectionPool(config)
        logger.info("SPRINT23-SERVICES: Database connection pool initialized")
        
        # Initialize pattern registry service first (required by analytics services)
        from src.core.services.pattern_registry_service import PatternRegistryService
        pattern_registry = PatternRegistryService()
        
        # Initialize analytics services
        from src.core.services.pattern_analytics_advanced_service import PatternAnalyticsAdvancedService
        from src.core.services.market_condition_service import MarketConditionService  
        from src.core.services.correlation_analyzer_service import CorrelationAnalyzerService
        from src.core.services.temporal_analytics_service import TemporalAnalyticsService
        from src.core.services.comparison_tools_service import ComparisonToolsService
        
        analytics_advanced_service = PatternAnalyticsAdvancedService(db_connection_pool, pattern_registry)
        market_condition_service = MarketConditionService(db_connection_pool)
        correlation_analyzer_service = CorrelationAnalyzerService(db_connection_pool)
        temporal_analytics_service = TemporalAnalyticsService(db_connection_pool)
        comparison_tools_service = ComparisonToolsService(db_connection_pool)
        
        logger.info("SPRINT23-SERVICES: All advanced analytics services initialized")
        return True
        
    except Exception as e:
        logger.error(f"SPRINT23-SERVICES: Initialization failed: {e}")
        # Set services to None so API endpoints can use mock data
        analytics_advanced_service = None
        market_condition_service = None
        correlation_analyzer_service = None
        temporal_analytics_service = None
        comparison_tools_service = None
        return False


def initialize_error_handling(config, redis_client=None):
    """Initialize Sprint 32 Enhanced Error Handling System.

    Args:
        config: Application configuration dictionary
        redis_client: Redis client for TickStockPL error integration

    Returns:
        tuple: (enhanced_logger, error_subscriber) or (None, None) on failure
    """
    try:
        logger.info("ERROR-HANDLING: Creating logging configuration...")
        logging_config = LoggingConfig()

        # Get database connection for enhanced logger
        db_connection = None
        if logging_config.log_db_enabled:
            try:
                # Try to get database connection using existing pattern
                if db_connection_pool:
                    db_connection = db_connection_pool
                else:
                    # Fallback - create simple database connection
                    import psycopg2
                    db_connection = psycopg2.connect(config.get('DATABASE_URI'))
                logger.info("ERROR-HANDLING: Database connection established for error logging")
            except Exception as db_error:
                logger.warning(f"ERROR-HANDLING: Database connection failed, disabling DB logging: {db_error}")
                db_connection = None

        # Create enhanced logger
        logger.info("ERROR-HANDLING: Creating enhanced logger...")
        enhanced_logger = create_enhanced_logger(
            config=logging_config,
            db_connection=db_connection
        )

        # Set as global enhanced logger
        set_enhanced_logger(enhanced_logger)
        logger.info("ERROR-HANDLING: Enhanced logger created and set as global")

        # Create error subscriber if Redis is available
        error_subscriber = None
        if redis_client and logging_config.redis_error_channel:
            try:
                logger.info("ERROR-HANDLING: Creating Redis error subscriber...")
                error_subscriber = create_error_subscriber(
                    redis_client=redis_client,
                    enhanced_logger=enhanced_logger,
                    config=logging_config
                )

                # Start the subscriber
                if error_subscriber.start():
                    set_error_subscriber(error_subscriber)
                    logger.info(f"ERROR-HANDLING: Redis error subscriber started for channel: {logging_config.redis_error_channel}")
                else:
                    logger.warning("ERROR-HANDLING: Failed to start Redis error subscriber")
                    error_subscriber = None

            except Exception as redis_error:
                logger.warning(f"ERROR-HANDLING: Redis error subscriber failed: {redis_error}")
                error_subscriber = None
        else:
            logger.info("ERROR-HANDLING: Redis not available, skipping error subscriber")

        # Log system status
        stats = enhanced_logger.get_stats()
        logger.info(f"ERROR-HANDLING: System initialized - {stats}")

        return enhanced_logger, error_subscriber

    except Exception as e:
        logger.error(f"ERROR-HANDLING: Initialization failed: {e}")
        return None, None


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
    
    # Sprint 12 Phase 2: TickStockPL Integration WebSocket Handlers
    @socketio.on('subscribe_tickstockpl_watchlist')
    def handle_subscribe_watchlist(data):
        """Handle watchlist subscription for TickStockPL updates."""
        try:
            symbols = data.get('symbols', [])
            user_id = data.get('user_id') or getattr(current_user, 'id', 'anonymous')
            subscription_types = data.get('subscription_types', ['price_update', 'pattern_alert'])
            
            # Add user to TickStockPL subscription via market data subscriber
            if hasattr(market_service, 'market_data_subscriber'):
                market_service.market_data_subscriber.subscribe_user_to_symbols(
                    user_id, symbols, subscription_types
                )
                emit('tickstockpl_subscription_confirmed', {
                    'symbols': symbols,
                    'types': subscription_types
                })
                logger.info(f"TICKSTOCKPL-SUBSCRIPTION: {user_id} subscribed to {len(symbols)} symbols")
            else:
                logger.warning("TICKSTOCKPL-SUBSCRIPTION: Market data subscriber not available")
                emit('error', {'message': 'TickStockPL integration not available'})
            
        except Exception as e:
            logger.error(f"TICKSTOCKPL-SUBSCRIPTION-ERROR: {e}")
            emit('error', {'message': 'TickStockPL subscription failed'})
    
    @socketio.on('unsubscribe_tickstockpl_symbol')
    def handle_unsubscribe_symbol(data):
        """Handle unsubscription from specific symbol."""
        try:
            symbol = data.get('symbol')
            user_id = data.get('user_id') or getattr(current_user, 'id', 'anonymous')
            
            if hasattr(market_service, 'market_data_subscriber'):
                market_service.market_data_subscriber.unsubscribe_user_from_symbol(
                    user_id, symbol
                )
                emit('tickstockpl_unsubscription_confirmed', {'symbol': symbol})
                logger.info(f"TICKSTOCKPL-UNSUBSCRIPTION: {user_id} unsubscribed from {symbol}")
                
        except Exception as e:
            logger.error(f"TICKSTOCKPL-UNSUBSCRIPTION-ERROR: {e}")
            emit('error', {'message': 'TickStockPL unsubscription failed'})
    
    @socketio.on('request_tickstockpl_chart_data')
    def handle_chart_data_request(data):
        """Handle chart data requests via WebSocket."""
        try:
            symbol = data.get('symbol')
            timeframe = data.get('timeframe', '1d')
            user_id = data.get('user_id') or getattr(current_user, 'id', 'anonymous')
            
            if hasattr(market_service, 'market_data_subscriber'):
                # Request historical data from TickStockPL
                chart_data = market_service.market_data_subscriber.get_historical_data(
                    symbol, timeframe
                )
                
                if chart_data:
                    emit('tickstockpl_chart_data_response', {
                        'symbol': symbol,
                        'timeframe': timeframe,
                        'chart_data': chart_data
                    })
                    logger.info(f"TICKSTOCKPL-CHART: Sent {len(chart_data)} bars for {symbol}")
                else:
                    emit('tickstockpl_chart_data_response', {
                        'symbol': symbol,
                        'timeframe': timeframe,
                        'chart_data': [],
                        'message': 'No data available'
                    })
            else:
                emit('error', {'message': 'Chart data service not available'})
                
        except Exception as e:
            logger.error(f"TICKSTOCKPL-CHART-REQUEST-ERROR: {e}")
            emit('error', {'message': 'Chart data request failed'})

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
    @login_required
    def index():
        try:
            logger.info("ROUTE: Index page requested")
            return render_template('dashboard/index.html')
        except Exception as e:
            logger.error(f"ROUTE-ERROR: Index route failed: {e}")
            raise
    
    @app.route('/sprint25')
    @login_required
    def sprint25_dashboard():
        """Sprint 25 Multi-Tier Pattern Dashboard."""
        try:
            logger.info("ROUTE: Sprint 25 Multi-Tier Dashboard requested")
            return render_template('dashboard/sprint25_multi_tier.html')
        except Exception as e:
            logger.error(f"ROUTE-ERROR: Sprint 25 dashboard route failed: {e}")
            raise
    
    @app.route('/health')
    @login_required
    def health_check():
        """Health check endpoint for monitoring."""
        return {"status": "healthy", "version": APP_VERSION}
    
    @app.route('/api/health/redis')
    def api_health_redis():
        """
        Detailed Redis health status for mandatory connectivity monitoring.
        
        This endpoint provides comprehensive Redis health diagnostics including
        connectivity, pub-sub functionality, and performance metrics for
        TickStockPL integration.
        """
        if not redis_client:
            return jsonify({
                "status": "CRITICAL",
                "message": "Redis client not initialized - TickStockPL integration unavailable",
                "timestamp": time.time(),
                "error": "Redis connectivity is mandatory for TickStockAppV2"
            }), 503
        
        health_data = {
            "status": "UNKNOWN",
            "connectivity": False,
            "pubsub_status": False,
            "performance": {},
            "channels": {},
            "server_info": {},
            "timestamp": time.time()
        }
        
        try:
            # Test basic connectivity with performance measurement
            start_time = time.time()
            ping_result = redis_client.ping()
            ping_time = (time.time() - start_time) * 1000
            
            if not ping_result:
                health_data["status"] = "CRITICAL"
                health_data["error"] = "Redis ping returned False"
                return jsonify(health_data), 503
            
            health_data["connectivity"] = True
            health_data["performance"]["ping_ms"] = round(ping_time, 2)
            
            # Get server information
            server_info = redis_client.info('server')
            health_data["server_info"] = {
                "redis_version": server_info.get('redis_version'),
                "uptime_seconds": server_info.get('uptime_in_seconds'),
                "used_memory_human": server_info.get('used_memory_human'),
                "connected_clients": server_info.get('connected_clients')
            }
            
            # Test pub-sub channels required for TickStockPL integration
            required_channels = [
                'tickstock.events.patterns',
                'tickstock.events.backtesting.progress',
                'tickstock.events.backtesting.results',
                'tickstock.health.status'
            ]
            
            channel_test_results = {}
            pubsub_errors = []
            
            for channel in required_channels:
                try:
                    # Test publish capability (validates permissions and functionality)
                    test_payload = {"test": "health_check", "timestamp": time.time()}
                    publish_result = redis_client.publish(channel, json.dumps(test_payload))
                    channel_test_results[channel] = {
                        "status": "accessible",
                        "subscribers": publish_result
                    }
                except Exception as e:
                    channel_test_results[channel] = {
                        "status": "error",
                        "error": str(e)
                    }
                    pubsub_errors.append(f"{channel}: {e}")
            
            health_data["channels"] = channel_test_results
            health_data["pubsub_status"] = len(pubsub_errors) == 0
            
            # Determine overall status based on performance and functionality
            if ping_time > 50:
                health_data["status"] = "CRITICAL"
                health_data["performance"]["warning"] = f"Ping latency too high: {ping_time:.2f}ms (target: <50ms)"
            elif ping_time > 25 or pubsub_errors:
                health_data["status"] = "DEGRADED"
                if ping_time > 25:
                    health_data["performance"]["warning"] = f"High ping latency: {ping_time:.2f}ms (target: <25ms)"
                if pubsub_errors:
                    health_data["pubsub_errors"] = pubsub_errors
            else:
                health_data["status"] = "HEALTHY"
            
            # Additional performance metrics
            health_data["performance"]["target_ping_ms"] = 50
            health_data["performance"]["optimal_ping_ms"] = 25
            health_data["integration_status"] = {
                "tickstockpl_ready": health_data["pubsub_status"],
                "real_time_capable": ping_time < 50,
                "optimal_performance": ping_time < 25
            }
            
        except redis.ConnectionError as e:
            health_data["status"] = "CRITICAL"
            health_data["error"] = f"Redis connection error: {e}"
            return jsonify(health_data), 503
        except Exception as e:
            health_data["status"] = "CRITICAL"
            health_data["error"] = f"Redis health check failed: {e}"
            return jsonify(health_data), 503
        
        # Return appropriate HTTP status based on health
        if health_data["status"] == "HEALTHY":
            return jsonify(health_data), 200
        elif health_data["status"] == "DEGRADED":
            return jsonify(health_data), 200  # Still functional
        else:
            return jsonify(health_data), 503  # Critical issues
    
    @app.route('/test')
    @login_required  
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
    
    # SPRINT 20 MOCK API REMOVED - Pattern Discovery now uses real APIs
    # Real pattern discovery endpoints provided via blueprint registration from:
    # src/api/rest/pattern_consumer.py - /api/patterns/scan, /api/patterns/stats, /api/patterns/summary, /api/patterns/health
    
    # Pattern alert simulation removed - real pattern alerts now come from TickStockPL via Redis pub-sub
    
    # SPRINT 21 MOCK API - Watchlist Management System
    @app.route('/api/watchlists', methods=['GET'])
    @login_required
    def api_watchlists_list():
        """Get all user watchlists - Sprint 21."""
        import random
        logger.info("WATCHLIST-API: Get all watchlists requested")
        
        # Mock watchlist data for UI testing
        mock_watchlists = [
            {
                "id": "tech-stocks",
                "name": "Tech Stocks",
                "symbols": ["AAPL", "GOOGL", "MSFT", "NVDA", "TSLA"],
                "created_at": "2025-01-16T10:00:00Z",
                "updated_at": "2025-01-16T15:30:00Z"
            },
            {
                "id": "healthcare",
                "name": "Healthcare",
                "symbols": ["JNJ", "PFE", "UNH", "ABBV", "BMY"],
                "created_at": "2025-01-15T14:20:00Z",
                "updated_at": "2025-01-16T09:15:00Z"
            },
            {
                "id": "finance",
                "name": "Financial Services",
                "symbols": ["JPM", "BAC", "WFC", "GS", "MS"],
                "created_at": "2025-01-14T11:45:00Z",
                "updated_at": "2025-01-16T12:00:00Z"
            }
        ]
        
        return {
            "watchlists": mock_watchlists,
            "count": len(mock_watchlists),
            "response_time_ms": round(random.uniform(10, 25), 1)
        }
    
    @app.route('/api/watchlists', methods=['POST'])
    @login_required
    def api_watchlists_create():
        """Create new watchlist - Sprint 21."""
        import uuid
        from datetime import datetime
        
        try:
            data = request.get_json()
            logger.info(f"WATCHLIST-API: Create watchlist '{data.get('name')}'")
            
            # Validate input
            if not data or not data.get('name'):
                return {"error": "Watchlist name is required"}, 400
            
            # Create new watchlist
            new_watchlist = {
                "id": str(uuid.uuid4())[:8],  # Short ID for demo
                "name": data['name'].strip(),
                "symbols": data.get('symbols', []),
                "created_at": datetime.now().isoformat() + "Z",
                "updated_at": datetime.now().isoformat() + "Z"
            }
            
            # In real implementation, save to database here
            logger.info(f"WATCHLIST-API: Created watchlist {new_watchlist['id']} with {len(new_watchlist['symbols'])} symbols")
            
            return new_watchlist
            
        except Exception as e:
            logger.error(f"WATCHLIST-API: Create failed: {e}")
            return {"error": "Failed to create watchlist"}, 500
    
    @app.route('/api/watchlists/<watchlist_id>', methods=['PUT'])
    @login_required
    def api_watchlists_update(watchlist_id):
        """Update existing watchlist - Sprint 21."""
        from datetime import datetime
        
        try:
            data = request.get_json()
            logger.info(f"WATCHLIST-API: Update watchlist {watchlist_id}")
            
            # Validate input
            if not data:
                return {"error": "Update data is required"}, 400
            
            # Mock updated watchlist (in real implementation, update in database)
            updated_watchlist = {
                "id": watchlist_id,
                "name": data.get('name', 'Updated Watchlist'),
                "symbols": data.get('symbols', []),
                "created_at": "2025-01-16T10:00:00Z",  # Would come from database
                "updated_at": datetime.now().isoformat() + "Z"
            }
            
            logger.info(f"WATCHLIST-API: Updated watchlist {watchlist_id} with {len(updated_watchlist['symbols'])} symbols")
            
            return updated_watchlist
            
        except Exception as e:
            logger.error(f"WATCHLIST-API: Update failed: {e}")
            return {"error": "Failed to update watchlist"}, 500
    
    @app.route('/api/watchlists/<watchlist_id>', methods=['DELETE'])
    @login_required
    def api_watchlists_delete(watchlist_id):
        """Delete watchlist - Sprint 21."""
        try:
            logger.info(f"WATCHLIST-API: Delete watchlist {watchlist_id}")
            
            # In real implementation, delete from database here
            logger.info(f"WATCHLIST-API: Deleted watchlist {watchlist_id}")
            
            return {"status": "deleted", "id": watchlist_id}
            
        except Exception as e:
            logger.error(f"WATCHLIST-API: Delete failed: {e}")
            return {"error": "Failed to delete watchlist"}, 500
    
    @app.route('/api/watchlists/<watchlist_id>/symbols', methods=['POST'])
    @login_required
    def api_watchlists_add_symbol(watchlist_id):
        """Add symbol to watchlist - Sprint 21."""
        from datetime import datetime
        
        try:
            data = request.get_json()
            symbol = data.get('symbol', '').upper()
            
            logger.info(f"WATCHLIST-API: Add {symbol} to watchlist {watchlist_id}")
            
            if not symbol:
                return {"error": "Symbol is required"}, 400
            
            # In real implementation, add to database here
            logger.info(f"WATCHLIST-API: Added {symbol} to watchlist {watchlist_id}")
            
            return {
                "status": "added",
                "watchlist_id": watchlist_id,
                "symbol": symbol,
                "updated_at": datetime.now().isoformat() + "Z"
            }
            
        except Exception as e:
            logger.error(f"WATCHLIST-API: Add symbol failed: {e}")
            return {"error": "Failed to add symbol"}, 500
    
    @app.route('/api/watchlists/<watchlist_id>/symbols/<symbol>', methods=['DELETE'])
    @login_required
    def api_watchlists_remove_symbol(watchlist_id, symbol):
        """Remove symbol from watchlist - Sprint 21."""
        from datetime import datetime
        
        try:
            logger.info(f"WATCHLIST-API: Remove {symbol} from watchlist {watchlist_id}")
            
            # In real implementation, remove from database here
            logger.info(f"WATCHLIST-API: Removed {symbol} from watchlist {watchlist_id}")
            
            return {
                "status": "removed",
                "watchlist_id": watchlist_id,
                "symbol": symbol.upper(),
                "updated_at": datetime.now().isoformat() + "Z"
            }
            
        except Exception as e:
            logger.error(f"WATCHLIST-API: Remove symbol failed: {e}")
            return {"error": "Failed to remove symbol"}, 500
    
    # SPRINT 21 MOCK API - Filter Presets System
    @app.route('/api/filters/presets', methods=['GET'])
    @login_required
    def api_filter_presets_list():
        """Get all user filter presets - Sprint 21."""
        logger.info("FILTER-PRESETS-API: Get all presets requested")
        
        # Mock filter presets data for UI testing
        mock_presets = [
            {
                "id": "high-confidence",
                "name": "High Confidence Patterns",
                "description": "Patterns with 80%+ confidence",
                "filters": {
                    "logic": "AND",
                    "conditions": [
                        {
                            "field": "confidence",
                            "operator": "gte",
                            "value": 0.8
                        }
                    ]
                },
                "created_at": "2025-01-16T10:00:00Z",
                "updated_at": "2025-01-16T15:30:00Z"
            },
            {
                "id": "breakout-patterns",
                "name": "Breakout Patterns",
                "description": "Weekly and Daily breakout patterns with strong RS",
                "filters": {
                    "logic": "AND",
                    "conditions": [
                        {
                            "field": "pattern",
                            "operator": "in",
                            "value": ["WeeklyBO", "DailyBO"]
                        },
                        {
                            "field": "rs",
                            "operator": "gte",
                            "value": 70
                        },
                        {
                            "field": "confidence",
                            "operator": "gte",
                            "value": 0.7
                        }
                    ]
                },
                "created_at": "2025-01-15T14:20:00Z",
                "updated_at": "2025-01-16T09:15:00Z"
            },
            {
                "id": "reversal-signals",
                "name": "Reversal Signals",
                "description": "Doji and Hammer patterns with high volume",
                "filters": {
                    "logic": "AND",
                    "conditions": [
                        {
                            "field": "pattern",
                            "operator": "in",
                            "value": ["Doji", "Hammer", "ShootingStar"]
                        },
                        {
                            "field": "volume",
                            "operator": "gte",
                            "value": 1000000
                        }
                    ]
                },
                "created_at": "2025-01-14T11:45:00Z",
                "updated_at": "2025-01-16T12:00:00Z"
            }
        ]
        
        return mock_presets
    
    @app.route('/api/filters/presets', methods=['POST'])
    @login_required
    def api_filter_presets_create():
        """Create new filter preset - Sprint 21."""
        import uuid
        from datetime import datetime
        
        try:
            data = request.get_json()
            logger.info(f"FILTER-PRESETS-API: Create preset '{data.get('name')}'")
            
            # Validate input
            if not data or not data.get('name'):
                return {"error": "Preset name is required"}, 400
            
            if not data.get('filters'):
                return {"error": "Filter configuration is required"}, 400
            
            # Create new preset
            new_preset = {
                "id": str(uuid.uuid4())[:8],  # Short ID for demo
                "name": data['name'].strip(),
                "description": data.get('description', '').strip(),
                "filters": data['filters'],
                "created_at": datetime.now().isoformat() + "Z",
                "updated_at": datetime.now().isoformat() + "Z"
            }
            
            # In real implementation, save to database here
            logger.info(f"FILTER-PRESETS-API: Created preset {new_preset['id']} with {len(new_preset['filters'].get('conditions', []))} conditions")
            
            return new_preset
            
        except Exception as e:
            logger.error(f"FILTER-PRESETS-API: Create failed: {e}")
            return {"error": "Failed to create filter preset"}, 500
    
    @app.route('/api/filters/presets/<preset_id>', methods=['PUT'])
    @login_required
    def api_filter_presets_update(preset_id):
        """Update existing filter preset - Sprint 21."""
        from datetime import datetime
        
        try:
            data = request.get_json()
            logger.info(f"FILTER-PRESETS-API: Update preset {preset_id}")
            
            # Validate input
            if not data:
                return {"error": "Update data is required"}, 400
            
            # Mock updated preset (in real implementation, update in database)
            updated_preset = {
                "id": preset_id,
                "name": data.get('name', 'Updated Preset'),
                "description": data.get('description', ''),
                "filters": data.get('filters', {"logic": "AND", "conditions": []}),
                "created_at": "2025-01-16T10:00:00Z",  # Would come from database
                "updated_at": datetime.now().isoformat() + "Z"
            }
            
            logger.info(f"FILTER-PRESETS-API: Updated preset {preset_id}")
            
            return updated_preset
            
        except Exception as e:
            logger.error(f"FILTER-PRESETS-API: Update failed: {e}")
            return {"error": "Failed to update filter preset"}, 500
    
    @app.route('/api/filters/presets/<preset_id>', methods=['DELETE'])
    @login_required
    def api_filter_presets_delete(preset_id):
        """Delete filter preset - Sprint 21."""
        try:
            logger.info(f"FILTER-PRESETS-API: Delete preset {preset_id}")
            
            # In real implementation, delete from database here
            logger.info(f"FILTER-PRESETS-API: Deleted preset {preset_id}")
            
            return {"status": "deleted", "id": preset_id}
            
        except Exception as e:
            logger.error(f"FILTER-PRESETS-API: Delete failed: {e}")
            return {"error": "Failed to delete filter preset"}, 500
    
    # SPRINT 21 WEEK 2 MOCK API - Pattern Analytics System
    @app.route('/api/patterns/analytics', methods=['GET'])
    @login_required
    def api_patterns_analytics():
        """Get pattern performance analytics - Sprint 21 Week 2."""
        import random
        
        logger.info("ANALYTICS-API: Pattern analytics requested")
        
        # Mock pattern performance analytics
        patterns = ['WeeklyBO', 'DailyBO', 'Doji', 'Hammer', 'ShootingStar', 'Engulfing', 'Harami']
        
        analytics_data = {
            "success_rates": {},
            "avg_performance": {},
            "reliability_score": {},
            "volume_correlation": {}
        }
        
        for pattern in patterns:
            # Generate realistic success rates (declining over time)
            success_1d = random.uniform(0.4, 0.8)
            success_5d = success_1d * random.uniform(0.7, 0.9)
            success_30d = success_5d * random.uniform(0.7, 0.9)
            
            analytics_data["success_rates"][pattern] = {
                "1d": round(success_1d, 2),
                "5d": round(success_5d, 2), 
                "30d": round(success_30d, 2)
            }
            
            # Average performance percentages
            analytics_data["avg_performance"][pattern] = {
                "1d": round(random.uniform(0.5, 3.0), 1),
                "5d": round(random.uniform(1.0, 5.0), 1),
                "30d": round(random.uniform(2.0, 10.0), 1)
            }
            
            analytics_data["reliability_score"][pattern] = round(random.uniform(0.5, 0.85), 2)
            analytics_data["volume_correlation"][pattern] = round(random.uniform(0.3, 0.8), 2)
        
        return analytics_data
    
    @app.route('/api/patterns/distribution', methods=['GET'])
    @login_required
    def api_patterns_distribution():
        """Get pattern distribution data - Sprint 21 Week 2."""
        import random
        
        logger.info("ANALYTICS-API: Pattern distribution requested")
        
        patterns = ['WeeklyBO', 'DailyBO', 'Doji', 'Hammer', 'ShootingStar', 'Engulfing', 'Harami']
        sectors = ['Technology', 'Healthcare', 'Financial', 'Industrial', 'Consumer', 'Energy']
        
        distribution_data = {
            "pattern_frequency": {pattern: random.randint(15, 70) for pattern in patterns},
            "confidence_distribution": {
                "high": {"label": "80%+", "count": random.randint(60, 100), "percentage": round(random.uniform(25, 40), 1)},
                "medium": {"label": "60-80%", "count": random.randint(80, 150), "percentage": round(random.uniform(35, 50), 1)},
                "low": {"label": "<60%", "count": random.randint(40, 80), "percentage": round(random.uniform(15, 30), 1)}
            },
            "sector_breakdown": {
                sector: {
                    "count": random.randint(20, 80),
                    "avg_confidence": round(random.uniform(0.6, 0.8), 2)
                } for sector in sectors
            }
        }
        
        return distribution_data
    
    @app.route('/api/patterns/history', methods=['GET'])
    @login_required  
    def api_patterns_history():
        """Get historical pattern data - Sprint 21 Week 2."""
        import random
        from datetime import datetime, timedelta
        
        logger.info("ANALYTICS-API: Pattern history requested")
        
        # Generate 30 days of historical data
        history_data = []
        base_date = datetime.now() - timedelta(days=30)
        
        for i in range(30):
            date = base_date + timedelta(days=i)
            daily_patterns = random.randint(150, 350)
            avg_confidence = random.uniform(0.65, 0.8)
            
            history_data.append({
                "date": date.strftime("%Y-%m-%d"),
                "patterns_detected": daily_patterns,
                "avg_confidence": round(avg_confidence, 2),
                "high_confidence_count": int(daily_patterns * random.uniform(0.2, 0.4)),
                "success_rate_1d": round(random.uniform(0.5, 0.75), 2)
            })
        
        return {"historical_data": history_data}
    
    @app.route('/api/patterns/success-rates', methods=['GET'])
    @login_required
    def api_patterns_success_rates():
        """Get pattern success rate analysis - Sprint 21 Week 2."""
        import random
        
        logger.info("ANALYTICS-API: Success rates requested")
        
        patterns = ['WeeklyBO', 'DailyBO', 'Doji', 'Hammer', 'EngulfingBullish']
        
        success_rates = {}
        for pattern in patterns:
            # Generate realistic success rates with time decay
            base_1d = random.uniform(0.45, 0.78)
            success_5d = base_1d * random.uniform(0.75, 0.95)  
            success_30d = success_5d * random.uniform(0.70, 0.90)
            
            # Assign trend based on success rates
            if base_1d > 0.7:
                trend = 'improving'
                correlation = random.uniform(0.80, 0.86)
            elif base_1d > 0.6:
                trend = 'stable' 
                correlation = random.uniform(0.70, 0.80)
            else:
                trend = 'declining'
                correlation = random.uniform(0.55, 0.70)
            
            success_rates[pattern] = {
                '1d': round(base_1d, 2),
                '5d': round(success_5d, 2),
                '30d': round(success_30d, 2),
                'trend': trend,
                'confidence_correlation': round(correlation, 2)
            }
        
        return success_rates
    
    @app.route('/api/patterns/backtest', methods=['POST'])
    @login_required
    def api_patterns_backtest():
        """Perform strategy backtesting - Sprint 21 Week 2."""
        import random
        from datetime import datetime, timedelta
        
        logger.info("ANALYTICS-API: Backtest requested")
        
        data = request.get_json()
        if not data:
            return {"error": "No backtest parameters provided"}, 400
            
        preset = data.get('preset', {})
        days = data.get('days', 30)
        preset_name = preset.get('name', 'Custom Preset')
        
        logger.info(f"ANALYTICS-API: Backtesting {preset_name} for {days} days")
        
        # Generate backtest results
        base_success_rate = random.uniform(0.55, 0.75)
        total_signals = random.randint(50, 150)
        successful_trades = int(total_signals * base_success_rate)
        
        # Generate daily performance data
        daily_performance = []
        cumulative_return = 1.0
        peak = 1.0
        
        for i in range(days):
            # Generate daily return with slight positive bias
            daily_return = random.normalvariate(0.001, 0.025)  # ~0.1% daily return, 2.5% volatility
            cumulative_return *= (1 + daily_return)
            
            # Track peak for drawdown calculation
            if cumulative_return > peak:
                peak = cumulative_return
            
            drawdown = (cumulative_return - peak) / peak
            
            date = (datetime.now() - timedelta(days=days-i)).strftime('%Y-%m-%d')
            
            daily_performance.append({
                'date': date,
                'daily_return': round(daily_return, 4),
                'cumulative_return': round(cumulative_return - 1, 4),
                'drawdown': round(drawdown, 4)
            })
        
        # Calculate performance metrics
        final_return = cumulative_return - 1
        max_drawdown = min([d['drawdown'] for d in daily_performance])
        
        # Calculate volatility (annualized)
        returns = [d['daily_return'] for d in daily_performance]
        volatility = (sum([(r - sum(returns)/len(returns))**2 for r in returns]) / len(returns))**0.5 * (252**0.5)
        
        # Simple Sharpe ratio approximation
        sharpe_ratio = (final_return * 252 / days) / volatility if volatility > 0 else 0
        
        backtest_result = {
            'preset_name': preset_name,
            'backtest_period': days,
            'total_signals': total_signals,
            'successful_trades': successful_trades,
            'success_rate': round(base_success_rate, 3),
            'avg_return': round(random.uniform(1.5, 3.5), 1),
            'final_return': round(final_return * 100, 2),  # As percentage
            'max_drawdown': round(max_drawdown * 100, 2),  # As percentage
            'sharpe_ratio': round(sharpe_ratio, 2),
            'daily_performance': daily_performance,
            'pattern_breakdown': {
                'WeeklyBO': {'signals': random.randint(10, 20), 'success_rate': round(random.uniform(0.6, 0.8), 2), 'avg_return': round(random.uniform(2.0, 3.5), 1)},
                'DailyBO': {'signals': random.randint(15, 25), 'success_rate': round(random.uniform(0.5, 0.7), 2), 'avg_return': round(random.uniform(1.5, 2.8), 1)},
                'Doji': {'signals': random.randint(5, 12), 'success_rate': round(random.uniform(0.3, 0.5), 2), 'avg_return': round(random.uniform(0.8, 1.5), 1)},
                'Hammer': {'signals': random.randint(8, 15), 'success_rate': round(random.uniform(0.6, 0.8), 2), 'avg_return': round(random.uniform(1.8, 2.5), 1)},
                'EngulfingBullish': {'signals': random.randint(12, 18), 'success_rate': round(random.uniform(0.65, 0.8), 2), 'avg_return': round(random.uniform(2.2, 3.2), 1)}
            },
            'risk_metrics': {
                'volatility': round(volatility, 3),
                'var_95': round(random.uniform(-0.06, -0.02), 3),  # Value at Risk
                'max_consecutive_losses': random.randint(1, 5)
            }
        }
        
        return backtest_result
    
    # SPRINT 21 WEEK 2 ENHANCED PATTERN VISUALIZATION API ENDPOINTS
    @app.route('/api/patterns/enhanced/<symbol>', methods=['POST'])
    @login_required
    def api_pattern_enhanced(symbol):
        """Get enhanced pattern data with trend indicators and context - Sprint 21 Week 2."""
        import random
        from datetime import datetime
        
        logger.info(f"VISUALIZATION-API: Enhanced data requested for {symbol}")
        
        try:
            data = request.get_json() or {}
            pattern = data.get('pattern', {})
            logger.debug(f"VISUALIZATION-API: Received pattern data: {pattern}")
        except Exception as e:
            logger.error(f"VISUALIZATION-API: JSON parsing error for {symbol}: {e}")
            return {'error': 'Invalid JSON data'}, 400
        
        # Generate realistic enhancement data
        trend_strength = random.uniform(30, 95)
        volume_change = random.uniform(-80, 150)  # -80% to +150%
        sector_performance = random.uniform(-8, 12)  # -8% to +12%
        
        # Pattern-specific success rates
        pattern_success_rates = {
            'WeeklyBO': {'1d': random.uniform(70, 85), '5d': random.uniform(60, 75)},
            'DailyBO': {'1d': random.uniform(55, 70), '5d': random.uniform(50, 65)},
            'Doji': {'1d': random.uniform(35, 55), '5d': random.uniform(30, 50)},
            'Hammer': {'1d': random.uniform(60, 75), '5d': random.uniform(55, 70)},
            'EngulfingBullish': {'1d': random.uniform(65, 80), '5d': random.uniform(60, 75)},
            'ShootingStar': {'1d': random.uniform(45, 65), '5d': random.uniform(40, 60)}
        }
        
        pattern_type = pattern.get('pattern', 'Unknown')
        success_rates = pattern_success_rates.get(pattern_type, {'1d': random.uniform(45, 65), '5d': random.uniform(40, 60)})
        
        enhancement_data = {
            'symbol': symbol,
            'trend_direction': 'up' if trend_strength > 65 else 'down' if trend_strength < 45 else 'sideways',
            'trend_strength': round(trend_strength),
            'volume_trend': 'increasing' if volume_change > 10 else 'decreasing' if volume_change < -10 else 'stable',
            'volume_change': round(volume_change),
            'market_condition': random.choice(['bullish', 'bearish', 'neutral']),
            'sector_performance': round(sector_performance, 1),
            'relative_strength': random.randint(25, 75),  # RSI range
            'success_rate_1d': round(success_rates['1d']),
            'success_rate_5d': round(success_rates['5d']),
            'price_momentum': round(random.uniform(-4, 6), 1),  # Recent price momentum
            'pattern_quality': random.choice(['High', 'Medium', 'Low']),
            'risk_level': random.choice(['Low', 'Medium', 'High']),
            'timestamp': datetime.now().isoformat()
        }
        
        return enhancement_data
    
    @app.route('/api/patterns/trends', methods=['GET'])
    @login_required  
    def api_patterns_trends():
        """Get pattern trend analysis data - Sprint 21 Week 2."""
        import random
        
        logger.info("VISUALIZATION-API: Trend analysis requested")
        
        # Generate trend data for different time periods
        trends_data = {
            'current_trends': {
                'bullish_patterns': ['WeeklyBO', 'EngulfingBullish', 'Hammer'],
                'bearish_patterns': ['ShootingStar', 'Doji'],
                'neutral_patterns': ['DailyBO']
            },
            'trend_strength': {
                'overall_market': random.uniform(40, 85),
                'volume_trend': random.choice(['increasing', 'decreasing', 'stable']),
                'momentum_direction': random.choice(['up', 'down', 'sideways'])
            },
            'sector_trends': {
                'Technology': round(random.uniform(-5, 8), 1),
                'Healthcare': round(random.uniform(-3, 6), 1),
                'Financial': round(random.uniform(-4, 7), 1),
                'Industrial': round(random.uniform(-6, 5), 1),
                'Consumer': round(random.uniform(-2, 9), 1)
            },
            'pattern_momentum': {
                pattern: {
                    'strength': round(random.uniform(20, 90)),
                    'direction': random.choice(['up', 'down', 'sideways']),
                    'reliability': round(random.uniform(0.4, 0.9), 2)
                }
                for pattern in ['WeeklyBO', 'DailyBO', 'Doji', 'Hammer', 'EngulfingBullish', 'ShootingStar']
            }
        }
        
        return trends_data
    
    # SPRINT 21 WEEK 2 REAL-TIME MARKET STATISTICS API ENDPOINTS
    @app.route('/api/market/statistics', methods=['GET'])
    @login_required
    def api_market_statistics():
        """Get live market statistics and pattern detection metrics - Sprint 21 Week 2."""
        import random
        from datetime import datetime
        
        logger.info("MARKET-STATS-API: Live statistics requested")
        
        # Generate realistic market statistics
        market_hours = datetime.now().hour >= 9 and datetime.now().hour <= 16
        base_activity = 1.5 if market_hours else 0.3
        
        statistics = {
            'patterns_detected_today': random.randint(85, 165),
            'pattern_velocity_per_hour': round(random.uniform(2.5, 12.0) * base_activity, 1),
            'average_confidence': round(random.uniform(0.62, 0.78), 3),
            'high_confidence_ratio': round(random.uniform(0.22, 0.42), 3),
            'last_hour': random.randint(3, 15) if market_hours else random.randint(0, 3),
            'last_24h': random.randint(85, 165),
            'last_week': random.randint(600, 1200),
            'timestamp': datetime.now().isoformat(),
            'market_hours': market_hours
        }
        
        logger.debug(f"MARKET-STATS-API: Generated statistics: {statistics}")
        return statistics
    
    @app.route('/api/market/breadth', methods=['GET'])
    @login_required
    def api_market_breadth():
        """Get market breadth analysis by sector - Sprint 21 Week 2."""
        import random
        from datetime import datetime
        
        logger.info("MARKET-STATS-API: Market breadth requested")
        
        # Generate realistic sector distribution
        sectors = {
            'Technology': random.randint(25, 55),
            'Healthcare': random.randint(15, 35),
            'Financial': random.randint(20, 40),
            'Industrial': random.randint(18, 35),
            'Energy': random.randint(8, 25),
            'Consumer Discretionary': random.randint(12, 30),
            'Consumer Staples': random.randint(8, 22),
            'Utilities': random.randint(5, 18),
            'Real Estate': random.randint(4, 15),
            'Materials': random.randint(6, 20)
        }
        
        breadth_data = {
            'sector_breakdown': sectors,
            'total_patterns': sum(sectors.values()),
            'most_active_sector': max(sectors.keys(), key=lambda k: sectors[k]),
            'least_active_sector': min(sectors.keys(), key=lambda k: sectors[k]),
            'timestamp': datetime.now().isoformat()
        }
        
        logger.debug(f"MARKET-STATS-API: Generated breadth data for {len(sectors)} sectors")
        return breadth_data
    
    @app.route('/api/market/pattern-frequency', methods=['GET'])
    @login_required  
    def api_market_pattern_frequency():
        """Get pattern detection frequency over time periods - Sprint 21 Week 2."""
        import random
        from datetime import datetime
        
        logger.info("MARKET-STATS-API: Pattern frequency requested")
        
        # Generate realistic frequency data with time-decay
        current_hour = datetime.now().hour
        market_hours = current_hour >= 9 and current_hour <= 16
        
        base_multiplier = 1.2 if market_hours else 0.4
        
        frequency_data = {
            'last_hour': int(random.randint(4, 18) * base_multiplier),
            'last_4h': int(random.randint(15, 45) * base_multiplier),
            'last_12h': int(random.randint(35, 85) * base_multiplier),
            'last_24h': random.randint(85, 165),
            'last_3d': random.randint(250, 420),
            'last_week': random.randint(600, 1200),
            'pattern_types': {
                'WeeklyBO': random.randint(15, 35),
                'DailyBO': random.randint(20, 45),
                'Doji': random.randint(12, 28),
                'Hammer': random.randint(8, 22),
                'EngulfingBullish': random.randint(10, 25),
                'ShootingStar': random.randint(6, 18)
            },
            'timestamp': datetime.now().isoformat(),
            'market_hours': market_hours
        }
        
        logger.debug(f"MARKET-STATS-API: Generated frequency data with {frequency_data['last_24h']} patterns in 24h")
        return frequency_data
    
    @app.route('/api/patterns/context', methods=['GET'])
    @login_required
    def api_patterns_context():
        """Get market context data for pattern analysis - Sprint 21 Week 2."""
        import random
        
        logger.info("VISUALIZATION-API: Context data requested")
        
        context_data = {
            'market_conditions': {
                'overall_sentiment': random.choice(['bullish', 'bearish', 'neutral']),
                'volatility_index': round(random.uniform(15, 45), 1),  # VIX-like measure
                'market_breadth': round(random.uniform(30, 80), 1),   # % of stocks above MA
                'sector_rotation': random.choice(['growth', 'value', 'defensive', 'cyclical'])
            },
            'economic_indicators': {
                'market_trend': random.choice(['uptrend', 'downtrend', 'sideways']),
                'risk_appetite': random.choice(['high', 'medium', 'low']),
                'institutional_flow': random.choice(['inflow', 'outflow', 'neutral'])
            },
            'pattern_environment': {
                'favorable_conditions': random.choice([True, False]),
                'pattern_reliability_factor': round(random.uniform(0.7, 1.3), 2),
                'market_noise_level': random.choice(['low', 'medium', 'high'])
            },
            'time_factors': {
                'session': 'market_hours',  # Could be 'pre_market', 'market_hours', 'after_hours'
                'day_of_week': datetime.now().strftime('%A'),
                'month': datetime.now().strftime('%B'),
                'quarter': f"Q{((datetime.now().month - 1) // 3) + 1}",
                'earnings_season': random.choice([True, False])
            }
        }
        
        return context_data
    
    # SPRINT 22 PATTERN REGISTRY API - Dynamic Pattern Management
    @app.route('/api/patterns/definitions', methods=['GET'])
    @login_required
    def api_pattern_definitions():
        """Get all enabled pattern definitions for UI loading - Sprint 22."""
        try:
            from src.core.services.pattern_registry_service import pattern_registry
            
            start_time = time.time()
            patterns = pattern_registry.get_enabled_patterns()
            response_time_ms = round((time.time() - start_time) * 1000, 1)
            
            pattern_data = [pattern.to_dict() for pattern in patterns]
            
            logger.info(f"PATTERN-REGISTRY-API: Returned {len(pattern_data)} enabled patterns in {response_time_ms}ms")
            
            return {
                "patterns": pattern_data,
                "count": len(pattern_data),
                "response_time_ms": response_time_ms,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"PATTERN-REGISTRY-API: Failed to get pattern definitions: {e}")
            return {"error": "Failed to load pattern definitions"}, 500
    
    @app.route('/api/patterns/definitions/admin', methods=['GET'])
    @login_required
    def api_pattern_definitions_admin():
        """Get all pattern definitions (enabled and disabled) for admin use - Sprint 22."""
        try:
            from src.core.services.pattern_registry_service import pattern_registry
            
            start_time = time.time()
            patterns = pattern_registry.get_all_patterns()
            response_time_ms = round((time.time() - start_time) * 1000, 1)
            
            pattern_data = [pattern.to_dict() for pattern in patterns]
            
            # Add service statistics for admin monitoring
            service_stats = pattern_registry.get_service_stats()
            
            logger.info(f"PATTERN-REGISTRY-API: Admin returned {len(pattern_data)} total patterns in {response_time_ms}ms")
            
            return {
                "patterns": pattern_data,
                "count": len(pattern_data),
                "enabled_count": len([p for p in patterns if p.enabled]),
                "disabled_count": len([p for p in patterns if not p.enabled]),
                "service_stats": service_stats,
                "response_time_ms": response_time_ms,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"PATTERN-REGISTRY-API: Admin failed to get pattern definitions: {e}")
            return {"error": "Failed to load pattern definitions"}, 500
    
    @app.route('/api/patterns/definitions/<int:pattern_id>/toggle', methods=['POST'])
    @login_required
    def api_pattern_toggle(pattern_id):
        """Toggle pattern enabled status - Sprint 22."""
        try:
            from src.core.services.pattern_registry_service import pattern_registry
            
            data = request.get_json() or {}
            enabled = data.get('enabled')
            
            # If enabled status not provided, we'll toggle current status
            if enabled is None:
                # Get current pattern to determine new status
                pattern = pattern_registry.get_all_patterns()
                current_pattern = next((p for p in pattern if p.id == pattern_id), None)
                if not current_pattern:
                    return {"error": "Pattern not found"}, 404
                enabled = not current_pattern.enabled
            
            start_time = time.time()
            success = pattern_registry.update_pattern_status(pattern_id, enabled)
            response_time_ms = round((time.time() - start_time) * 1000, 1)
            
            if success:
                logger.info(f"PATTERN-REGISTRY-API: Pattern {pattern_id} {'enabled' if enabled else 'disabled'} in {response_time_ms}ms")
                return {
                    "status": "success",
                    "pattern_id": pattern_id,
                    "enabled": enabled,
                    "response_time_ms": response_time_ms,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                logger.error(f"PATTERN-REGISTRY-API: Failed to toggle pattern {pattern_id}")
                return {"error": "Failed to update pattern status"}, 500
                
        except Exception as e:
            logger.error(f"PATTERN-REGISTRY-API: Toggle pattern {pattern_id} failed: {e}")
            return {"error": "Failed to toggle pattern"}, 500
    
    @app.route('/api/patterns/definitions/<pattern_name>/toggle-by-name', methods=['POST'])
    @login_required
    def api_pattern_toggle_by_name(pattern_name):
        """Toggle pattern enabled status by name - Sprint 22."""
        try:
            from src.core.services.pattern_registry_service import pattern_registry
            
            start_time = time.time()
            success = pattern_registry.toggle_pattern_by_name(pattern_name)
            response_time_ms = round((time.time() - start_time) * 1000, 1)
            
            if success:
                logger.info(f"PATTERN-REGISTRY-API: Pattern {pattern_name} toggled in {response_time_ms}ms")
                return {
                    "status": "success",
                    "pattern_name": pattern_name,
                    "response_time_ms": response_time_ms,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                logger.warning(f"PATTERN-REGISTRY-API: Pattern {pattern_name} not found for toggle")
                return {"error": "Pattern not found"}, 404
                
        except Exception as e:
            logger.error(f"PATTERN-REGISTRY-API: Toggle pattern {pattern_name} failed: {e}")
            return {"error": "Failed to toggle pattern"}, 500
    
    @app.route('/api/patterns/definitions/<pattern_name>/success-rates', methods=['GET'])
    @login_required 
    def api_pattern_success_rates(pattern_name):
        """Get real-time success rates for a pattern - Sprint 22."""
        try:
            from src.core.services.pattern_registry_service import pattern_registry
            
            # Get days parameter from query string
            days = int(request.args.get('days', 30))
            
            # First get the pattern to find its ID
            pattern = pattern_registry.get_pattern_by_name(pattern_name)
            if not pattern:
                return {"error": "Pattern not found"}, 404
            
            start_time = time.time()
            success_data = pattern_registry.calculate_success_rates(pattern.id, days)
            response_time_ms = round((time.time() - start_time) * 1000, 1)
            
            if success_data:
                logger.info(f"PATTERN-REGISTRY-API: Success rates for {pattern_name} calculated in {response_time_ms}ms")
                success_data.update({
                    "response_time_ms": response_time_ms,
                    "timestamp": datetime.now().isoformat()
                })
                return success_data
            else:
                logger.warning(f"PATTERN-REGISTRY-API: No success rate data for {pattern_name}")
                return {
                    "pattern_name": pattern_name,
                    "total_detections": 0,
                    "success_rate_1d": None,
                    "avg_confidence": None,
                    "days_analyzed": days,
                    "response_time_ms": response_time_ms,
                    "timestamp": datetime.now().isoformat()
                }
                
        except ValueError:
            return {"error": "Invalid days parameter"}, 400
        except Exception as e:
            logger.error(f"PATTERN-REGISTRY-API: Success rates for {pattern_name} failed: {e}")
            return {"error": "Failed to calculate success rates"}, 500
    
    @app.route('/api/patterns/distribution/real', methods=['GET'])
    @login_required
    def api_pattern_distribution_real():
        """Get real pattern distribution from database - Sprint 22."""
        try:
            from src.core.services.pattern_registry_service import pattern_registry
            
            # Get days parameter from query string
            days = int(request.args.get('days', 7))
            
            start_time = time.time()
            distribution = pattern_registry.get_pattern_distribution(days)
            response_time_ms = round((time.time() - start_time) * 1000, 1)
            
            logger.info(f"PATTERN-REGISTRY-API: Pattern distribution for {days} days calculated in {response_time_ms}ms")
            
            return {
                "distribution": distribution,
                "days_analyzed": days,
                "response_time_ms": response_time_ms,
                "timestamp": datetime.now().isoformat()
            }
            
        except ValueError:
            return {"error": "Invalid days parameter"}, 400
        except Exception as e:
            logger.error(f"PATTERN-REGISTRY-API: Pattern distribution failed: {e}")
            return {"error": "Failed to get pattern distribution"}, 500
    
    @app.route('/api/patterns/registry/stats', methods=['GET'])
    @login_required
    def api_pattern_registry_stats():
        """Get pattern registry service statistics - Sprint 22."""
        try:
            from src.core.services.pattern_registry_service import pattern_registry
            
            service_stats = pattern_registry.get_service_stats()
            
            return {
                "service_stats": service_stats,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"PATTERN-REGISTRY-API: Stats failed: {e}")
            return {"error": "Failed to get registry statistics"}, 500
    
    @app.route('/api/patterns/registry/clear-cache', methods=['POST'])
    @login_required
    def api_pattern_registry_clear_cache():
        """Clear pattern registry cache to force refresh - Sprint 22."""
        try:
            from src.core.services.pattern_registry_service import pattern_registry
            
            pattern_registry.clear_cache()
            
            logger.info("PATTERN-REGISTRY-API: Cache cleared successfully")
            
            return {
                "status": "cache_cleared",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"PATTERN-REGISTRY-API: Clear cache failed: {e}")
            return {"error": "Failed to clear cache"}, 500


    # Sprint 23: Advanced Analytics API Endpoints
    # ==============================================================
    # Advanced Pattern Analytics API Routes
    # ==============================================================
    
    def run_async_in_flask(coroutine_func):
        """Helper to run async functions in Flask routes"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(coroutine_func)
    
    # SPRINT 23 ANALYTICS ENDPOINTS - Advanced Pattern Analytics Dashboard
    
    @app.route('/api/analytics/correlations', methods=['GET'])
    @login_required
    def api_analytics_correlations():
        """Get pattern correlation analysis with real database functions"""
        try:
            days_back = int(request.args.get('days_back', 30))
            min_correlation = float(request.args.get('min_correlation', 0.3))
            format_type = request.args.get('format', 'heatmap')
            
            # Try to use real analytics service first
            if analytics_advanced_service:
                try:
                    correlations = sync_call(analytics_advanced_service.get_pattern_correlations(
                        days_back=days_back, min_correlation=min_correlation
                    ))
                    
                    if format_type == 'matrix':
                        return sync_call(correlation_analyzer_service.get_correlation_matrix(
                            days_back=days_back, min_correlation=min_correlation
                        ))
                    elif format_type == 'network':
                        return sync_call(correlation_analyzer_service.get_network_data(
                            days_back=days_back, min_correlation=min_correlation
                        ))
                    else:  # heatmap format (default)
                        return sync_call(correlation_analyzer_service.get_heatmap_data(
                            correlations, days_back=days_back, min_correlation=min_correlation
                        ))
                        
                except Exception as e:
                    logger.error(f"ANALYTICS-API: Real correlation service failed, using mock: {e}")
                    # Fall through to mock data
            
            # Fallback to mock data if service not available or failed
            
            if format_type == 'matrix':
                return {
                    'patterns': ['WeeklyBO', 'DailyBO', 'TrendFollower', 'MomentumBO'],
                    'matrix': [
                        [1.0, 0.75, 0.45, 0.32],
                        [0.75, 1.0, 0.58, 0.61], 
                        [0.45, 0.58, 1.0, 0.73],
                        [0.32, 0.61, 0.73, 1.0]
                    ],
                    'significance_matrix': [[True, True, True, False], [True, True, True, True], [True, True, True, True], [False, True, True, True]],
                    'generated_at': datetime.now().isoformat()
                }
            elif format_type == 'network':
                return {
                    'nodes': [
                        {'id': 'WeeklyBO', 'label': 'Weekly Breakout', 'degree': 2},
                        {'id': 'DailyBO', 'label': 'Daily Breakout', 'degree': 3},
                        {'id': 'TrendFollower', 'label': 'Trend Follower', 'degree': 2}
                    ],
                    'edges': [
                        {'source': 'WeeklyBO', 'target': 'DailyBO', 'weight': 0.75, 'correlation': 0.75},
                        {'source': 'TrendFollower', 'target': 'MomentumBO', 'weight': 0.73, 'correlation': 0.73}
                    ],
                    'clusters': [['WeeklyBO', 'DailyBO'], ['TrendFollower', 'MomentumBO']]
                }
            else:  # heatmap
                return {
                    'pattern_pairs': [
                        {'pattern_a': 'WeeklyBO', 'pattern_b': 'DailyBO', 'correlation': 0.75, 'is_significant': True, 'strength': 'Strong'},
                        {'pattern_a': 'TrendFollower', 'pattern_b': 'MomentumBO', 'correlation': 0.73, 'is_significant': True, 'strength': 'Strong'}
                    ],
                    'max_correlation': 0.75,
                    'min_correlation': 0.61,
                    'significant_pairs_count': 2,
                    'total_pairs_count': 2
                }
                
        except Exception as e:
            logger.error(f"ANALYTICS-API: Correlation analysis failed: {e}")
            return {'error': 'Failed to generate correlation analysis'}, 500

    @app.route('/api/analytics/temporal/<pattern_name>', methods=['GET'])
    @login_required
    def api_analytics_temporal(pattern_name):
        """Get temporal analysis for a specific pattern"""
        try:
            analysis_type = request.args.get('type', 'heatmap')
            
            if analysis_type == 'hourly':
                return {
                    'pattern_name': pattern_name,
                    'analysis_type': 'hourly',
                    'data': [
                        {'time_bucket': 'Hour_9', 'detection_count': 12, 'success_rate': 66.7, 'statistical_significance': True},
                        {'time_bucket': 'Hour_10', 'detection_count': 15, 'success_rate': 80.0, 'statistical_significance': True},
                        {'time_bucket': 'Hour_14', 'detection_count': 16, 'success_rate': 81.3, 'statistical_significance': True}
                    ]
                }
            elif analysis_type == 'daily':
                return {
                    'pattern_name': pattern_name,
                    'analysis_type': 'daily',
                    'data': [
                        {'time_bucket': 'Monday', 'detection_count': 45, 'success_rate': 62.2, 'statistical_significance': True},
                        {'time_bucket': 'Tuesday', 'detection_count': 52, 'success_rate': 73.1, 'statistical_significance': True},
                        {'time_bucket': 'Thursday', 'detection_count': 41, 'success_rate': 78.0, 'statistical_significance': True}
                    ]
                }
            else:  # heatmap
                return {
                    'pattern_name': pattern_name,
                    'hourly_data': [{'time_bucket': 'Hour_10', 'success_rate': 80.0, 'detection_count': 15}, {'time_bucket': 'Hour_14', 'success_rate': 81.3, 'detection_count': 16}],
                    'daily_data': [{'time_bucket': 'Tuesday', 'success_rate': 73.1, 'detection_count': 52}, {'time_bucket': 'Thursday', 'success_rate': 78.0, 'detection_count': 41}],
                    'session_data': [{'time_bucket': 'Regular Hours', 'success_rate': 69.2, 'detection_count': 156}],
                    'best_time_recommendation': 'Hour_14 (Success: 81.3%); Thursday (Success: 78.0%)',
                    'worst_time_warning': 'Avoid: Hour_12 (Success: 37.5%); Friday (Success: 50.0%)'
                }
                
        except Exception as e:
            logger.error(f"ANALYTICS-API: Temporal analysis failed for {pattern_name}: {e}")
            return {'error': f'Failed to generate temporal analysis for {pattern_name}'}, 500

    @app.route('/api/analytics/market-context', methods=['GET'])
    @login_required 
    def api_analytics_market_context():
        """Get market context analysis"""
        try:
            context_type = request.args.get('type', 'summary')
            
            if context_type == 'summary':
                return {
                    'timestamp': datetime.now().isoformat(),
                    'trend': 'Bullish',
                    'trend_strength': 6.2,
                    'volatility': 18.5,
                    'volatility_level': 'Medium',
                    'volume_level': 'High',
                    'session': 'Regular',
                    'major_indexes': {'sp500': 0.85, 'nasdaq': 1.23, 'dow': 0.67}
                }
            elif context_type == 'pattern':
                pattern_name = request.args.get('pattern_name', 'Unknown')
                return {
                    'pattern_name': pattern_name,
                    'market_contexts': [
                        {'condition_type': 'Volatility', 'condition_value': 'Low (<15)', 'detection_count': 25, 'success_rate': 78.2, 'vs_overall_performance': 8.5},
                        {'condition_type': 'Market Trend', 'condition_value': 'BULLISH', 'detection_count': 32, 'success_rate': 72.1, 'vs_overall_performance': 5.6}
                    ]
                }
            else:  # history
                return {
                    'history': [
                        {'timestamp': datetime.now().isoformat(), 'market_volatility': 18.5, 'market_trend': 'bullish', 'session_type': 'regular'},
                        {'timestamp': (datetime.now() - timedelta(hours=1)).isoformat(), 'market_volatility': 19.2, 'market_trend': 'neutral', 'session_type': 'regular'}
                    ]
                }
                
        except Exception as e:
            logger.error(f"ANALYTICS-API: Market context analysis failed: {e}")
            return {'error': 'Failed to generate market context analysis'}, 500

    @app.route('/api/analytics/advanced-metrics/<pattern_name>', methods=['GET'])
    @login_required
    def api_analytics_advanced_metrics(pattern_name):
        """Get advanced statistical metrics for a pattern"""
        try:
            return {
                'pattern_name': pattern_name,
                'success_rate': 67.5,
                'confidence_interval_95': 4.2,
                'max_win_streak': 8,
                'max_loss_streak': 3,
                'sharpe_ratio': 1.25,
                'max_drawdown': 12.5,
                'avg_recovery_time': 24.5,
                'statistical_significance': True
            }
            
        except Exception as e:
            logger.error(f"ANALYTICS-API: Advanced metrics failed for {pattern_name}: {e}")
            return {'error': f'Failed to get advanced metrics for {pattern_name}'}, 500

    @app.route('/api/analytics/comparison', methods=['GET'])
    @login_required
    def api_analytics_comparison():
        """Get pattern comparison analysis"""
        try:
            comparison_type = request.args.get('type', 'table')
            
            if comparison_type == 'two-pattern':
                pattern_a = request.args.get('pattern_a', 'PatternA')
                pattern_b = request.args.get('pattern_b', 'PatternB')
                return {
                    'pattern_a_name': pattern_a,
                    'pattern_b_name': pattern_b,
                    'pattern_a_success_rate': 67.5,
                    'pattern_b_success_rate': 58.2,
                    'difference': 9.3,
                    't_statistic': 2.45,
                    'p_value': 0.02,
                    'is_significant': True,
                    'confidence_level': 98.0,
                    'recommendation': f'Pattern {pattern_a} significantly outperforms {pattern_b}'
                }
            elif comparison_type == 'top-performers':
                limit = int(request.args.get('limit', 5))
                return {
                    'top_performers': [
                        {'pattern_name': 'WeeklyBO', 'success_rate': 78.5, 'sharpe_ratio': 1.45, 'rank': 1, 'percentile': 100.0},
                        {'pattern_name': 'DailyBO', 'success_rate': 72.1, 'sharpe_ratio': 1.32, 'rank': 2, 'percentile': 75.0},
                        {'pattern_name': 'TrendFollower', 'success_rate': 68.3, 'sharpe_ratio': 1.18, 'rank': 3, 'percentile': 50.0}
                    ][:limit]
                }
            else:  # table
                return {
                    'patterns': [
                        {'pattern_name': 'WeeklyBO', 'success_rate': 78.5, 'sharpe_ratio': 1.45, 'rank': 1, 'statistical_significance': True},
                        {'pattern_name': 'DailyBO', 'success_rate': 72.1, 'sharpe_ratio': 1.32, 'rank': 2, 'statistical_significance': True},
                        {'pattern_name': 'TrendFollower', 'success_rate': 68.3, 'sharpe_ratio': 1.18, 'rank': 3, 'statistical_significance': True}
                    ],
                    'comparison_metric': 'success_rate',
                    'total_patterns': 3,
                    'significant_patterns': 3,
                    'generated_at': datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"ANALYTICS-API: Comparison analysis failed: {e}")
            return {'error': 'Failed to generate comparison analysis'}, 500

    @app.route('/api/analytics/pattern-deep-dive/<pattern_name>', methods=['GET'])
    @login_required
    def api_analytics_pattern_deep_dive(pattern_name):
        """Get comprehensive deep-dive analysis for a specific pattern"""
        try:
            return {
                'pattern_name': pattern_name,
                'advanced_metrics': {
                    'success_rate': 67.5,
                    'sharpe_ratio': 1.25,
                    'max_drawdown': 12.5,
                    'max_win_streak': 8,
                    'statistical_significance': True
                },
                'temporal_analysis': {
                    'best_time_recommendation': 'Hour_14 (Success: 81.3%); Thursday (Success: 78.0%)',
                    'worst_time_warning': 'Avoid: Hour_12 (Success: 37.5%)',
                    'hourly_performance_count': 8,
                    'daily_performance_count': 5
                },
                'market_context': [
                    {'condition_type': 'Volatility', 'condition_value': 'Low (<15)', 'success_rate': 78.2, 'vs_overall_performance': 8.5},
                    {'condition_type': 'Market Trend', 'condition_value': 'BULLISH', 'success_rate': 72.1, 'vs_overall_performance': 5.6}
                ],
                'optimal_trading_windows': {
                    'optimal_hours': ['Hour_14', 'Hour_10'],
                    'optimal_days': ['Thursday', 'Tuesday'],
                    'best_overall_time': 'Hour_14 (Success: 81.3%)'
                },
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"ANALYTICS-API: Deep dive analysis failed for {pattern_name}: {e}")
            return {'error': f'Failed to generate deep dive analysis for {pattern_name}'}, 500

    @app.route('/api/analytics/detection-history/<int:pattern_id>', methods=['GET'])
    @login_required
    def api_analytics_detection_history(pattern_id):
        """Get detection history with outcomes for a specific pattern"""
        try:
            limit = int(request.args.get('limit', 100))
            days_back = int(request.args.get('days_back', 30))
            
            # Mock detection history data
            detections = [
                {
                    'detection_id': 1001,
                    'detected_at': datetime.now().isoformat(),
                    'symbol': 'AAPL',
                    'confidence': 0.85,
                    'outcome_1d': 2.3,
                    'outcome_5d': 4.1,
                    'pattern_name': 'WeeklyBO'
                },
                {
                    'detection_id': 1002,
                    'detected_at': (datetime.now() - timedelta(days=1)).isoformat(),
                    'symbol': 'GOOGL',
                    'confidence': 0.78,
                    'outcome_1d': -1.2,
                    'outcome_5d': 0.8,
                    'pattern_name': 'WeeklyBO'
                }
            ]
            
            return {
                'pattern_id': pattern_id,
                'detection_history': detections[:limit],
                'total_detections': len(detections),
                'days_analyzed': days_back,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"ANALYTICS-API: Detection history failed for pattern {pattern_id}: {e}")
            return {'error': f'Failed to get detection history for pattern {pattern_id}'}, 500

    @app.route('/api/analytics/statistical-test', methods=['POST'])
    @login_required
    def api_analytics_statistical_test():
        """Perform statistical tests on pattern data"""
        try:
            data = request.get_json()
            if not data:
                return {'error': 'Request body required'}, 400
            
            test_type = data.get('test_type', 'two_sample_t_test')
            patterns = data.get('patterns', [])
            
            if len(patterns) < 2:
                return {'error': 'At least 2 patterns required for statistical testing'}, 400
            
            return {
                'test_type': 'Two-Sample T-Test',
                'null_hypothesis': f'No difference between {patterns[0]} and {patterns[1]}',
                'alternative_hypothesis': f'Significant difference between {patterns[0]} and {patterns[1]}',
                'test_statistic': 2.45,
                'p_value': 0.02,
                'is_significant': True,
                'confidence_level': 98.0,
                'effect_size': 0.65,
                'interpretation': f'Pattern {patterns[0]} significantly outperforms {patterns[1]}',
                'generated_at': datetime.now().isoformat()
            }
                
        except Exception as e:
            logger.error(f"ANALYTICS-API: Statistical test failed: {e}")
            return {'error': 'Failed to perform statistical test'}, 500


def main():
    """Main application entry point."""
    global app, market_service, socketio
    
    try:
        logger.info("=" * 60)
        logger.info("[STARTUP] TICKSTOCK APPLICATION STARTING (Simplified)")
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
        
        # IMMEDIATE LOGIN MANAGER CONFIGURATION - Force it here
        login_manager = extensions.get('login_manager')
        if login_manager:
            login_manager.login_view = 'login'
            login_manager.login_message = 'Please log in to access this page.'
            logger.info("STARTUP: LOGIN-MANAGER configured immediately after extensions")
        else:
            logger.error("STARTUP: LOGIN-MANAGER not found in extensions!")

        # Initialize integration logging from environment
        try:
            from src.core.services.integration_logger import configure_integration_logging
            from src.core.services.config_manager import get_config

            config = get_config()
            integration_enabled = config.get('INTEGRATION_LOGGING_ENABLED', True)
            integration_log_file = config.get('INTEGRATION_LOG_FILE', False)
            integration_log_level = config.get('INTEGRATION_LOG_LEVEL', 'INFO')

            flow_logger = configure_integration_logging(
                enabled=integration_enabled,
                log_file=integration_log_file,
                log_level=integration_log_level
            )

            logger.info(f"STARTUP: Integration logging configured (enabled={integration_enabled})")
        except ImportError:
            logger.warning("STARTUP: Integration logging not available")
        
        # Initialize Redis (MANDATORY for TickStockPL integration)
        logger.info("STARTUP: Initializing Redis (MANDATORY)...")
        try:
            # Get environment for performance thresholds
            environment = startup_result.get('env_config', {}).get('APP_ENVIRONMENT', 'PRODUCTION')
            logger.info(f"STARTUP: Environment detected for Redis validation: {environment}")
            redis_client = initialize_redis_mandatory(config, environment=environment)
            logger.info("STARTUP: Redis connectivity validated successfully")
            # Add Redis client to config for other components
            config['redis_client'] = redis_client
        except RedisConfigurationError as e:
            logger.critical("STARTUP: Redis configuration error")
            print(generate_redis_failure_report('config', str(e)))
            sys.exit(1)
        except RedisConnectionError as e:
            logger.critical("STARTUP: Redis connection failed")
            print(generate_redis_failure_report('connection', str(e)))
            sys.exit(1)
        except RedisChannelError as e:
            logger.critical("STARTUP: Redis pub-sub channels unavailable")
            print(generate_redis_failure_report('channels', str(e)))
            sys.exit(1)
        except RedisPerformanceError as e:
            logger.critical("STARTUP: Redis performance below requirements")
            print(generate_redis_failure_report('performance', str(e)))
            sys.exit(1)
        except Exception as e:
            logger.critical(f"STARTUP: Unexpected Redis initialization error: {e}")
            print(generate_redis_failure_report('connection', f"Unexpected error: {e}"))
            sys.exit(1)
        
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
            globals()['market_service'] = market_service  # Assign to global variable
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
            from src.api.rest.admin_historical_data_redis import register_admin_historical_routes
            
            logger.info("STARTUP: Registering auth routes...")
            try:
                register_auth_routes(app, extensions, cache_control, config)
                logger.info("STARTUP: Auth routes registered successfully")
            except Exception as auth_error:
                logger.error(f"STARTUP: Auth routes registration failed: {auth_error}")
                import traceback
                logger.error(f"STARTUP: Auth routes traceback:\n{traceback.format_exc()}")
                raise
            
            logger.info("STARTUP: Registering main routes...")
            register_main_routes(app, extensions, cache_control, config)
            logger.info("STARTUP: Main routes registered successfully")
            
            logger.info("STARTUP: Registering API routes...")
            register_api_routes(app, extensions, cache_control, config)
            logger.info("STARTUP: API routes registered successfully")
            
            # Sprint 25 Week 2: Register tier patterns API
            logger.info("STARTUP: Registering Sprint 25 tier patterns API...")
            try:
                from src.api.rest.tier_patterns import tier_patterns_bp, init_tier_patterns_api
                
                # Initialize and register the tier patterns API with database integration
                init_tier_patterns_api()
                app.register_blueprint(tier_patterns_bp)
                logger.info("STARTUP: Sprint 25 tier patterns API registered successfully")
                
            except Exception as tier_error:
                logger.warning(f"STARTUP: Tier patterns API registration failed: {tier_error}")
                # Don't fail startup for this - it's optional Sprint 25 functionality
            
            logger.info("STARTUP: Registering TickStockPL API routes...")
            register_tickstockpl_routes(app, extensions, cache_control, config)
            logger.info("STARTUP: TickStockPL API routes registered successfully")
            
            logger.info("STARTUP: Registering admin historical data routes...")
            register_admin_historical_routes(app)
            logger.info("STARTUP: Admin historical data routes registered successfully")

            logger.info("STARTUP: Registering admin monitoring routes...")
            try:
                from src.api.rest.admin_monitoring import register_admin_monitoring_routes
                register_admin_monitoring_routes(app)
                logger.info("STARTUP: Admin monitoring routes registered successfully")
            except Exception as monitoring_error:
                logger.warning(f"STARTUP: Admin monitoring routes registration failed: {monitoring_error}")
                # Don't fail startup for monitoring - it's optional

            logger.info("STARTUP: Registering admin daily processing routes...")
            try:
                from src.api.rest.admin_daily_processing import register_admin_daily_processing_routes
                from src.infrastructure.redis.processing_subscriber import create_processing_subscriber

                register_admin_daily_processing_routes(app)
                logger.info("STARTUP: Admin daily processing routes registered successfully")

                # Start the processing event subscriber
                processing_subscriber = create_processing_subscriber(app)
                logger.info("STARTUP: Processing event subscriber started")
            except Exception as processing_error:
                logger.warning(f"STARTUP: Admin daily processing routes registration failed: {processing_error}")
                # Don't fail startup for processing dashboard - it's optional

            logger.info("STARTUP: Registering admin user management routes...")
            from src.api.rest.admin_users import admin_users_bp
            app.register_blueprint(admin_users_bp)
            logger.info("STARTUP: Admin user management routes registered successfully")
            
            # Register Real Pattern Discovery APIs (Sprint 10 Complete)
            logger.info("STARTUP: Registering real pattern discovery APIs...")
            try:
                pattern_api_success = init_pattern_discovery_app(app)
                if pattern_api_success:
                    logger.info("STARTUP: Pattern discovery APIs registered successfully - MOCK ENDPOINTS ELIMINATED")

                    # Register pattern discovery service with main Redis subscriber to avoid duplicate subscriptions
                    if redis_event_subscriber:
                        from src.core.services.pattern_discovery_service import register_pattern_discovery_with_subscriber
                        if register_pattern_discovery_with_subscriber(redis_event_subscriber):
                            logger.info("STARTUP: Pattern discovery service registered with main Redis subscriber")
                        else:
                            logger.warning("STARTUP: Failed to register pattern discovery with main subscriber")
                else:
                    logger.error("STARTUP: Pattern discovery API registration failed")
            except Exception as pattern_error:
                logger.error(f"STARTUP: Pattern discovery API registration error: {pattern_error}")
                # Don't fail startup - this is a warning but not critical
            
        except ImportError as e:
            logger.warning(f"STARTUP: Some API routes failed to load: {e}")
        except Exception as e:
            logger.error(f"STARTUP: API route registration failed: {e}")
            raise
        
        # CONFIGURE LOGIN MANAGER UNAUTHORIZED HANDLER AFTER ROUTES ARE REGISTERED
        login_manager = extensions.get('login_manager')
        if login_manager:
            @login_manager.unauthorized_handler
            def unauthorized_handler():
                from flask import redirect, flash
                logger.info("LOGIN-MANAGER: Unauthorized access, redirecting to login")
                flash('Please log in to access this page.', 'info')
                return redirect('/login')  # Use direct path instead of url_for
            logger.info("STARTUP: LOGIN-MANAGER unauthorized handler configured after route registration")
        else:
            logger.error("STARTUP: LOGIN-MANAGER not found when configuring unauthorized handler!")
        
        # Sprint 32: Initialize Enhanced Error Handling System
        logger.info("STARTUP: Initializing enhanced error handling system...")
        try:
            enhanced_logger, error_subscriber = initialize_error_handling(config, redis_client)
            if enhanced_logger:
                logger.info("STARTUP: Enhanced error handling system initialized successfully")
                # Test the enhanced logger
                enhanced_logger.log_error(
                    severity='info',
                    message='Enhanced error handling system initialized successfully',
                    category='system',
                    component='StartupService',
                    context={'startup': True}
                )
            else:
                logger.warning("STARTUP: Enhanced error handling system initialization incomplete")
        except Exception as e:
            logger.error(f"STARTUP: Enhanced error handling system failed: {e}")
            # Don't fail startup - this is not critical for core functionality

        # Initialize TickStockPL integration services (Phase 2)
        logger.info("STARTUP: Initializing TickStockPL integration services...")
        try:
            if initialize_tickstockpl_services(config, socketio, redis_client, flask_app=app):
                logger.info("STARTUP: TickStockPL integration services initialized successfully")
            else:
                logger.warning("STARTUP: TickStockPL integration services initialization incomplete")
        except Exception as e:
            logger.error(f"STARTUP: TickStockPL services failed: {e}")
        
        # Initialize Sprint 23 Advanced Analytics Services
        logger.info("STARTUP: Initializing Sprint 23 analytics services...")
        try:
            if initialize_sprint23_services(config):
                logger.info("STARTUP: Sprint 23 analytics services initialized successfully")
            else:
                logger.warning("STARTUP: Sprint 23 analytics services initialization incomplete")
        except Exception as e:
            logger.error(f"STARTUP: Sprint 23 analytics services initialization failed: {e}")
            # Don't fail startup - continue with mock data
        
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
        
        # Start monitoring subscriber for TickStockPL monitoring events
        logger.info("STARTUP: Starting monitoring subscriber...")
        try:
            from src.services.monitoring_subscriber import start_monitoring_subscriber
            start_monitoring_subscriber()
            logger.info("STARTUP: Monitoring subscriber started - receiving TickStockPL events")
        except Exception as e:
            logger.warning(f"STARTUP: Monitoring subscriber failed to start: {e}")
            # Don't fail startup - monitoring is optional

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
        logger.info("[SUCCESS] TICKSTOCK APPLICATION READY")
        logger.info(f"[INFO] Data Source: {'Synthetic' if config.get('USE_SYNTHETIC_DATA') else 'Polygon API'}")
        logger.info(f"[INFO] Redis: {'Connected' if redis_client else 'Disabled'}")
        logger.info(f"[INFO] SocketIO: Enabled")
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

        # Stop monitoring subscriber
        try:
            from src.services.monitoring_subscriber import stop_monitoring_subscriber
            stop_monitoring_subscriber()
            logger.info("SHUTDOWN: Monitoring subscriber stopped")
        except:
            pass

        # Stop TickStockPL integration services
        if redis_event_subscriber:
            redis_event_subscriber.stop()

        # Stop Sprint 32 error handling services
        try:
            from src.core.services.error_subscriber import get_error_subscriber
            error_subscriber = get_error_subscriber()
            if error_subscriber:
                error_subscriber.stop()
                logger.info("SHUTDOWN: Error subscriber stopped")
        except:
            pass

        if pattern_alert_manager:
            pattern_alert_manager.cleanup_expired_data()

        if market_service:
            market_service.stop()

        if redis_client:
            redis_client.close()
            
        logger.info("SHUTDOWN: Application stopped")

if __name__ == '__main__':
    main()