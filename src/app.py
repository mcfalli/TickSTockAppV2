"""
TickStock Main Application Entry Point
Coordinates startup sequence and runs the application.
TickStock Rock
"""
import eventlet
eventlet.monkey_patch()

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


# Import all major modules to prevent orphaning
from src.api.rest import *
from src.auth import AuthenticationManager, RegistrationManager
from src.core.domain.events import *
from src.core.services import *
from src.infrastructure.data_sources import DataProviderFactory
from src.presentation.websocket import WebSocketManager, WebSocketPublisher
from src.processing.detectors import EventDetectionManager


import os
import time
import logging
import threading
import requests
from datetime import datetime

from flask import request, render_template
from flask_login import login_required
from flask_login import current_user

# Import application modules
from src.core.services.startup_service import run_startup_sequence
from config.app_config import create_flask_app, initialize_flask_extensions, initialize_socketio
from config.logging_config import get_domain_logger, LogDomain, get_session_id, configure_logging
from src.presentation.websocket.manager import WebSocketManager
from src.core.services.market_data_service import MarketDataService
from src.processing.detectors.manager import EventDetectionManager

from src.infrastructure.database import MarketAnalytics

from src.infrastructure.data_sources.factory import DataProviderFactory
from src.infrastructure.messaging.sms_service import SMSManager
from src.monitoring.system_monitor import system_monitor

#TRACE TRACING
from src.monitoring.tracer import tracer, TraceLevel, normalize_event_type, ensure_int

logger = get_domain_logger(LogDomain.CORE, 'app')

# Global variables for application components
app = None
market_service = None

APP_VERSION = "X.x.x"

def healthcheck_polygon_api(config):
    """Test Polygon API connectivity."""
    try:
        response = requests.get('https://api.polygon.io/v1/marketstatus/now', 
                              headers={'Authorization': f"Bearer {config.get('POLYGON_API_KEY')}"})
        response.raise_for_status()
        logger.debug(f"Polygon API test from app.py: {response.status_code}, {response.json()}")
        return True
    except Exception as e:
        logger.error(f"Polygon API test failed: {e}")
        return False


def initialize_market_services(config, cache_control, ws_manager):
    """Initialize market data services with retry logic."""
    
    logger.info("initialize_market_services: Initializing market data services")
    
    # Initialize components
    event_manager = EventDetectionManager(config, cache_control)

    
    # Initialize data provider with retry logic
    retries = 3
    data_provider = None
    
    for attempt in range(retries):
        try:
            data_provider = DataProviderFactory.get_provider(config)
            logger.info(f"Important: Selected data provider: {data_provider.__class__.__name__}")
            
            # Test Polygon API if using it
            if data_provider.__class__.__name__ == 'PolygonDataProvider' and not healthcheck_polygon_api(config):
                raise Exception("Polygon API unavailable")
            break
            
        except Exception as e:
            logger.error(f"Provider init failed (attempt {attempt+1}/{retries}): {e}")
            if attempt == retries - 1:
                logger.error("All provider attempts failed—falling back to SimulatedDataProvider")
                data_provider = DataProviderFactory.get_default_provider(config)
            time.sleep(5)
    
    # Create market service
    market_service = MarketDataService(
        config=config,
        data_provider=data_provider,
        event_manager=event_manager,
        websocket_mgr=ws_manager,
        cache_control=cache_control
    )


    return event_manager, data_provider, market_service

#TRACE TRACING    
def initialize_tracer(config):
    """Initialize the debug tracer based on configuration."""
    if not config.get('TRACE_ENABLED', False):
        logger.info("Debug tracer is disabled")
        return
    
    # Get configuration
    trace_tickers = config.get('TRACE_TICKERS', [])
    trace_level_str = config.get('TRACE_LEVEL', 'NORMAL')
    trace_output_dir = config.get('TRACE_OUTPUT_DIR', './logs/trace')
    
    # Convert string level to enum
    trace_level = TraceLevel.NORMAL
    if trace_level_str == 'CRITICAL':
        trace_level = TraceLevel.CRITICAL
    elif trace_level_str == 'VERBOSE':
        trace_level = TraceLevel.VERBOSE
    
    # Configure tracer
    tracer.trace_output_dir = trace_output_dir
    tracer.auto_export_interval = config.get('TRACE_AUTO_EXPORT_INTERVAL', 300)
    tracer.max_trace_size_mb = config.get('TRACE_MAX_SIZE_MB', 50)
    
    # Enable tracing for specified tickers
    if trace_tickers:
        tracer.enable_for_tickers(trace_tickers, trace_level)
        logger.info(f"Debug tracer enabled for tickers: {', '.join(trace_tickers)} at level {trace_level_str}")
    else:
        logger.warning("TRACE_ENABLED is True but no tickers specified in TRACE_TICKERS")



def setup_websocket_connection(market_service, config, cache_control):
    """Setup WebSocket connection with retry logic."""
    
    if not config.get('USE_POLYGON_API') or config.get('USE_SYNTHETIC_DATA'):
        return
    
    logger.info("Setting up WebSocket connection")
    
    retries = 3
    for attempt in range(retries):
        try:
            if market_service.real_time_adapter.connect(cache_control.get_default_universe()):
                logger.info("WebSocket connection established successfully")
                market_service.handle_websocket_status('connected')
                break
            else:
                raise Exception("WebSocket connection failed")
        except Exception as e:
            logger.warning(f"WebSocket attempt {attempt+1}/{retries} failed: {e}")
            if attempt == retries - 1:
                logger.error("All WebSocket attempts failed—proceeding with available data")
            time.sleep(5)


def setup_query_debug_middleware(app, config):  
    """Setup query parameter debug middleware."""
    
    debug_filter = configure_logging(config)
    
    @app.before_request
    def before_request():
        debug_filter.set_enabled('debug' in request.args)
    
    @app.after_request
    def after_request(response):
        debug_filter.set_enabled(False)
        return response
    
    return debug_filter

def setup_debug_error_logging(app):
    """
    Setup global error logging for debug.
    Captures all unhandled exceptions.
    """
    import traceback
    from flask import request
    
    @app.errorhandler(Exception)
    def handle_exception(e):
        """Global exception handler that logs to debug"""
        try:
            logger.error(f"Unhandled exception: {type(e).__name__}: {str(e)}")
        
        except Exception as logging_error:
            # If debug logging fails, don't crash the error handler
            logger.error(f"Failed to log error: {logging_error}")
        
        # Continue with normal Flask error handling
        # Check if we have a specific error handler for this exception type
        if hasattr(e, 'code'):
            # HTTP exceptions (404, 500, etc)
            if e.code == 404:
                return render_template('error.html', error="Page not found"), 404
            elif e.code == 500:
                return render_template('error.html', error="Internal server error"), 500
            else:
                return render_template('error.html', error=f"Error {e.code}: {str(e)}"), e.code
        else:
            # Non-HTTP exceptions
            logger.error(f"Unhandled exception: {type(e).__name__}: {str(e)}")
            logger.error(traceback.format_exc())
            return render_template('error.html', error="An unexpected error occurred"), 500
    
    logger.info("Global debug error logging handler registered")


def register_socketio_handlers(socketio, ws_manager, market_service):
    """Register SocketIO event handlers with authentication support."""
    
    @socketio.on('connect')
    def handle_connect(auth=None):
        """
        🆕 SPRINT 1D.3: Enhanced connect handler with filter loading.
        """
        from flask_socketio import disconnect, emit
        
        client_id = request.sid
        
        try:
            # 🆕 SPRINT 1D.3: Get authenticated user
            if current_user.is_authenticated:
                user_id = current_user.id
                username = current_user.username
                
                logger.info(f"Authenticated user {username} (ID: {user_id}) connected: {client_id}")
                
                # Register user connection with enhanced tracking
                ws_manager.register_user_connection(user_id, client_id)
                ws_manager.register_client(client_id)  # Keep legacy tracking
                
                # 🆕 SPRINT 1D.3: Load user filters on connect
                filter_load_success = False
                filter_error = None
                
                if hasattr(market_service, 'websocket_publisher'):
                    try:
                        filter_load_success = on_user_websocket_connect(
                            market_service.websocket_publisher, 
                            user_id
                        )
                        
                        if filter_load_success:
                            logger.debug(f"USER_CONNECT_COMPLETE: User {user_id} filters loaded successfully")
                        else:
                            logger.debug(f"USER_CONNECT_WARNING: User {user_id} filter loading failed")
                    except Exception as e:
                        logger.error(f"Error loading filters for user {user_id}: {str(e)}")
                        filter_error = str(e)
                
                # Send personalized welcome message
                welcome_data = {
                    'message': f'Welcome {username}! Your personalized filters are active.',
                    'user_id': user_id,
                    'authenticated': True,
                    'connection_id': client_id,
                    'filters_loaded': filter_load_success,
                    'personalized_experience': True,
                    'timestamp': datetime.now().isoformat()
                }
                
                if filter_error:
                    welcome_data['filter_warning'] = 'Some filters may not be active'
                    
                emit('test_event', welcome_data)
                
                logger.info(f"📱 Client {client_id} connected to WebSocket (User: {username})")
                
                # Send initial status update
                if hasattr(market_service, 'websocket_publisher'):
                    try:
                        market_service.websocket_publisher.send_status_update(
                            'connected' if market_service.processing_active else 'disconnected',
                            {
                                'client_id': client_id,
                                'user_id': user_id,
                                'provider': market_service.data_source
                            },
                            user_id=user_id
                        )
                    except Exception as e:
                        logger.error(f"Error sending initial status for user {user_id}: {str(e)}")
                
                # Log connection statistics
                stats = ws_manager.get_user_connection_stats()
                logger.debug(f"Connection stats: {stats['total_authenticated_users']} users, "
                            f"{stats['total_user_connections']} total connections")
                
                return True  # Accept connection
                
            else:
                # 🚨 SPRINT 1D.3: Reject unauthenticated connections
                logger.warning(f"UNAUTHENTICATED_CONNECTION_REJECTED: {client_id}")
                
                # Send clear rejection message before disconnecting
                emit('error', {
                    'message': 'Authentication required. Please log in to access personalized real-time data.',
                    'authenticated': False,
                    'action_required': 'login',
                    'timestamp': datetime.now().isoformat()
                })
                
                # Disconnect the client
                disconnect()
                return False  # Reject connection
                
        except Exception as e:
            logger.error(f"Critical error in handle_connect for {client_id}: {str(e)}", exc_info=True)
            emit('error', {
                'message': 'Connection failed due to server error',
                'timestamp': datetime.now().isoformat()
            })
            disconnect()
            return False

    # Keep your existing disconnect, error, ping, and other handlers unchanged...
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """
        🆕 SPRINT 1D.3: Enhanced disconnect handler with user context cleanup.
        """
        client_id = request.sid if hasattr(request, 'sid') else 'unknown'
        
        # Get user info before cleanup
        user_id = ws_manager.get_connection_user_id(client_id)
        
        if user_id:
            logger.info(f"Authenticated user {user_id} disconnected: {client_id}")
            
            # Check remaining connections before cleanup
            connections_before = ws_manager.get_user_connection_count(user_id)
            
            # Unregister user connection first
            ws_manager.unregister_user_connection(client_id)
            
            # Check if user still has connections
            connections_after = ws_manager.get_user_connection_count(user_id)
            
            if connections_after == 0:
                logger.info(f"User {user_id} has no remaining connections")
                # 🆕 SPRINT 1D.3: Could optionally clear filter cache here if desired
                # market_service.websocket_publisher.invalidate_user_filter_cache(user_id)
            else:
                logger.debug(f"User {user_id} still has {connections_after} connections")
        else:
            logger.info(f"Unauthenticated client disconnected: {client_id}")
        
        # Clean up generic client tracking
        ws_manager.unregister_client(client_id)
        
        # Log updated connection statistics
        stats = ws_manager.get_user_connection_stats()
        logger.debug(f"After disconnect - {stats['total_authenticated_users']} users, "
                    f"{stats['total_user_connections']} total connections")

    @socketio.on('error')
    def handle_error(error):
        """Handle SocketIO errors with user context."""
        client_id = request.sid if hasattr(request, 'sid') else 'unknown'
        user_id = ws_manager.get_connection_user_id(client_id)
        
        if user_id:
            logger.error(f"SocketIO error for user {user_id} (connection {client_id}): {error}")
        else:
            logger.error(f"SocketIO error for unauthenticated client {client_id}: {error}")

    @socketio.on('ping')
    def handle_ping(data=None):
        """
        Handle ping requests with user context logging.
        """
        client_id = request.sid
        user_id = ws_manager.get_connection_user_id(client_id)
        
        timestamp = datetime.now().isoformat()
        
        if user_id:
            logger.info(f"Received ping from user {user_id} (connection {client_id}) at {timestamp}")
        else:
            logger.warning(f"Received ping from unauthenticated client {client_id} at {timestamp}")
        
        # Send pong response
        socketio.emit('pong', {
            'time': timestamp,
            'user_id': user_id,
            'authenticated': user_id is not None
        }, room=client_id)

    @socketio.on('user_status_request')
    def handle_user_status_request():
        """
        🆕 SPRINT 1D.1: New handler for user status requests.
        Provides connection and authentication status.
        """
        client_id = request.sid
        user_id = ws_manager.get_connection_user_id(client_id)
        
        if user_id:
            user_connections = ws_manager.get_user_connection_count(user_id)
            stats = ws_manager.get_user_connection_stats()
            
            status_response = {
                'authenticated': True,
                'user_id': user_id,
                'connection_id': client_id,
                'user_connections': user_connections,
                'total_authenticated_users': stats['total_authenticated_users'],
                'timestamp': datetime.now().isoformat()
            }
        else:
            status_response = {
                'authenticated': False,
                'connection_id': client_id,
                'message': 'Not authenticated',
                'timestamp': datetime.now().isoformat()
            }
        
        socketio.emit('user_status_response', status_response, room=client_id)

def register_error_handlers(app):
    """Register application error handlers."""
    
    # These specific handlers will be called before the global Exception handler
    @app.errorhandler(404)
    def page_not_found(e):
        if request.path != '/favicon.ico':
            logger.debug(f"404 error: {str(e)}")
        return render_template('error.html', error="Page not found"), 404

    @app.errorhandler(500)
    def server_error(e):
        logger.error(f"Server error: {e}")
        return render_template('error.html', error="Internal server error"), 500


def register_basic_routes(app, config):
    """Register basic application routes."""
    
    @app.route('/')
    @login_required
    def index():
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Rendering index page")
        return render_template('index.html', 
                             config=config, 
                             session_id=get_session_id(), 
                             username=current_user.username)

    @app.route('/favicon.ico')
    def favicon():
        from flask import send_from_directory
        return send_from_directory(app.static_folder, 'favicon.ico')


def run_update_loop(market_service, config):
    """Run the market data update loop."""
    
    logger.info("Starting data update loop")
    market_service.start_processing()
    
    while True:
        eventlet.sleep(config.get('UPDATE_INTERVAL', 0.5))

def initialize_filter_cache(app, market_service):
    """
    🆕 SPRINT 1C: ENHANCED - Initialize user filter cache during startup.
    """
    try:
        with app.app_context():
            # Make websocket_publisher accessible for API routes
            app.websocket_publisher = market_service.websocket_publisher
            #app.market_service = market_service  # Ensure this is also set
            registration_result = market_service.register_with_app(app)
            if not registration_result.success:
                logger.error(f"Failed to register market service: {registration_result.errors}")

            logger.info("✅ WebSocket publisher registered with Flask app for route access")
            
            # Initialize filter cache if the publisher supports it
            if hasattr(market_service.websocket_publisher, 'initialize_filter_cache_safely'):
                cache_initialized = market_service.websocket_publisher.initialize_filter_cache_safely()
                if cache_initialized:
                    logger.info("STARTUP: User filter cache initialized successfully")
                else:
                    logger.info("STARTUP: No user filters found to cache at startup")
                    
                # Ensure cache structure is ready even if no filters exist
                if not hasattr(market_service.websocket_publisher, 'current_user_filters'):
                    market_service.websocket_publisher.current_user_filters = {}
                if not hasattr(market_service.websocket_publisher, 'filter_cache_initialized'):
                    market_service.websocket_publisher.filter_cache_initialized = False
                    
                logger.info("STARTUP: Filter cache structure initialized")
            else:
                logger.warning("STARTUP: WebSocket publisher does not support filter caching")
                
    except Exception as e:
        logger.error(f"Error initializing filter cache during startup: {e}")
        import traceback
        logger.error(f"Filter cache initialization traceback: {traceback.format_exc()}")
# ============================================================================
# FIXED: Database Sync Scheduler (with proper variable scope)
# ============================================================================

def schedule_database_sync(app, market_service):
    """
    🆕 ENHANCED: Scheduled database sync with filter cache refresh.
    """
    try:
        with app.app_context():
            # Existing session accumulation sync
            memory_handler = market_service.session_accumulation_manager.get_memory_handler()
            session_totals = memory_handler.get_session_totals()
            should_sync = market_service.session_accumulation_manager.should_sync_to_database()
            
            # PHASE 1.4: Analytics manager sync
            should_sync_analytics = market_service.market_analytics_manager.should_sync_to_database()
            
            # 🆕 SPRINT 1C: Periodic filter cache refresh (every ~5 minutes)
            should_refresh_filters = False
            if hasattr(market_service.websocket_publisher, 'last_filter_cache_update'):
                import time
                time_since_cache_update = time.time() - market_service.websocket_publisher.last_filter_cache_update
                should_refresh_filters = time_since_cache_update > 300  # 5 minutes
            
            logger.debug(f"SYNC_CHECK: Session events: {session_totals.get('total_events', 0)}, "
                        f"Should sync session: {should_sync}, Should sync analytics: {should_sync_analytics}, "
                        f"Should refresh filters: {should_refresh_filters}")
            
            # Sync session accumulation (existing)
            if should_sync:
                dirty_data = memory_handler.get_dirty_data_for_sync()
                dirty_count = len(dirty_data)
                logger.info(f"SESSION_SYNC_STARTING: {dirty_count} dirty records to sync")
                
                sync_result = market_service.session_accumulation_manager.sync_to_database()
                if sync_result.get('success', False):
                    records_synced = sync_result.get('records_synced', 0)
                    if records_synced > 0:
                        logger.info(f"SESSION_SYNC_SUCCESS: {records_synced} records synced")
                else:
                    logger.error(f"SESSION_SYNC_FAILED: {sync_result.get('error', 'Unknown error')}")
            
            # PHASE 1.4: Sync analytics data
            if should_sync_analytics:
                analytics_sync_result = market_service.market_analytics_manager.sync_to_database()
                
                if analytics_sync_result.get('success', False):
                    analytics_synced = analytics_sync_result.get('records_synced', 0)
                    if analytics_synced > 0:
                        logger.info(f"ANALYTICS_SYNC_SUCCESS: {analytics_synced} analytics records synced")
                        
                        # Verify analytics in database
                        analytics_count = MarketAnalytics.query.filter(
                            MarketAnalytics.session_date == datetime.now().date()
                        ).count()
                        logger.debug(f"ANALYTICS_VERIFICATION: {analytics_count} analytics records in database for today")
                else:
                    error_msg = analytics_sync_result.get('error', 'Unknown analytics sync error')
                    logger.error(f"ANALYTICS_SYNC_FAILED: {error_msg}")
            
            # 🆕 SPRINT 1C: Refresh filter cache periodically
            if should_refresh_filters:
                try:
                    if hasattr(market_service.websocket_publisher, 'initialize_filter_cache_safely'):
                        cache_refreshed = market_service.websocket_publisher.initialize_filter_cache_safely()
                        if cache_refreshed:
                            logger.debug("FILTER_CACHE_REFRESH: Successfully refreshed filter cache")
                        else:
                            logger.debug("FILTER_CACHE_REFRESH: No filters to refresh")
                except Exception as cache_error:
                    logger.error(f"FILTER_CACHE_REFRESH_ERROR: {cache_error}")
            
            # Periodic status report
            import random
            if random.random() < 0.1:  # 10% of the time
                # Get analytics summary
                analytics_summary = market_service.market_analytics_manager.get_session_summary()
                
                # Get filter cache status
                filter_status = "N/A"
                if hasattr(market_service.websocket_publisher, 'get_filter_cache_status'):
                    try:
                        cache_status = market_service.websocket_publisher.get_filter_cache_status()
                        filters_applied = cache_status.get('filters_applied', 0)
                        cache_hits = cache_status.get('cache_hits', 0)
                        filter_status = f"{filters_applied} applied, {cache_hits} cache hits"
                    except:
                        filter_status = "Error"
                
                logger.debug(f"ANALYTICS_STATUS: {analytics_summary.get('record_count', 0)} analytics records, "
                           f"avg_net_score={analytics_summary.get('avg_net_score', 0):.2f}, "
                           f"filters: {filter_status}")
                    
    except Exception as e:
        logger.error(f"Error in enhanced database sync: {e}")
        import traceback
        logger.error(f"Enhanced sync error traceback: {traceback.format_exc()}")

def start_enhanced_database_sync_scheduler(app, market_service, config):
    """ENHANCED: Start database sync scheduler with comprehensive monitoring."""
    import threading
    import time
    
    def enhanced_sync_loop():
        """Enhanced background loop for database sync with diagnostics."""
        # Wait for initial startup
        time.sleep(5)  # Let the app fully initialize first
        
        sync_count = 0
        last_memory_check = 0
        
        logger.info("SCHEDULER_STARTED: Enhanced database sync scheduler active")
        
        while True:
            try:
                # Sleep between sync attempts
                time.sleep(config.get('DATABASE_SYNCH_AGGREGATE_SECONDS', 60)) 
                sync_count += 1
                
                
                # Call enhanced sync function
                schedule_database_sync(app, market_service)
                
                # Periodic memory status check (every 6 cycles = ~1 minute)
                if sync_count % 6 == 0:
                    try:
                        with app.app_context():
                            memory_handler = market_service.session_accumulation_manager.get_memory_handler()
                            totals = memory_handler.get_session_totals()
                            stats = memory_handler.get_stats()
                            
                            # Only log if there's significant activity
                            total_events = totals.get('total_events', 0)
                            if total_events > last_memory_check:
                                logger.info(f"MEMORY_STATUS: {total_events} total events, "
                                          f"{totals.get('active_tickers', 0)} active tickers, "
                                          f"{stats.get('db_sync_count', 0)} syncs completed")
                                last_memory_check = total_events
                                
                    except Exception as memory_error:
                        logger.error(f"Error in memory status check: {memory_error}")
                    
            except Exception as e:
                logger.error(f"Error in enhanced sync loop: {e}")
                time.sleep(60)  # Wait longer on error
    
    # Start background thread for scheduling
    sync_thread = threading.Thread(target=enhanced_sync_loop, daemon=True, name="enhanced-database-sync")
    sync_thread.start()
    logger.info("Enhanced database sync scheduler started - will sync every 10 seconds with full diagnostics")



def start_database_sync_scheduler_example(app, market_service):
    """FIXED: Start the database sync scheduler with proper context handling."""
    import threading
    import time
    
    def sync_loop():
        """Background loop for database sync with proper Flask context."""
        # Wait for initial startup
        time.sleep(5)  # Let the app fully initialize first
        
        while True:
            try:
                # Sleep between sync attempts
                time.sleep(30)  # Sync every 30 seconds
                
                # Call sync function which creates its own app context
                schedule_database_sync(app, market_service)
                    
            except Exception as e:
                logger.error(f"Error in sync loop: {e}")
                time.sleep(60)  # Wait longer on error
    
    # Start background thread for scheduling
    sync_thread = threading.Thread(target=sync_loop, daemon=True, name="database-sync-scheduler")
    sync_thread.start()
    logger.info("Database sync scheduler started - will sync every 30 seconds")

def initialize_multi_user_filter_cache(app, market_service):
    """
    🆕 SPRINT 1D.3: Initialize multi-user filter cache during startup.
    Replaces single-user initialization with multi-user architecture.
    """
    try:
        with app.app_context():
            # Make websocket_publisher accessible for API routes
            app.websocket_publisher = market_service.websocket_publisher
            #app.market_service = market_service  # Ensure this is also set
            registration_result = market_service.register_with_app(app)
            if not registration_result.success:
                logger.error(f"Failed to register market service: {registration_result.errors}")


            
            logger.info("✅ Multi-user WebSocket publisher registered with Flask app for route access")
            
            # Initialize multi-user filter cache system
            if hasattr(market_service.websocket_publisher, 'initialize_filter_cache_for_all_users'):
                # Initialize cache structure (users will be loaded when they connect)
                if not hasattr(market_service.websocket_publisher, 'current_user_filters'):
                    market_service.websocket_publisher.current_user_filters = {}
                if not hasattr(market_service.websocket_publisher, 'filter_cache_initialized'):
                    market_service.websocket_publisher.filter_cache_initialized = False
                
                logger.info("STARTUP: Multi-user filter cache system initialized")
                logger.info("STARTUP: User filters will be loaded when users connect to WebSocket")
                
                # Initialize filter statistics
                if not hasattr(market_service.websocket_publisher, 'results_filter_stats'):
                    market_service.websocket_publisher.results_filter_stats = {}
                
                # Initialize multi-user filter statistics
                market_service.websocket_publisher.results_filter_stats.update({
                    'user_filters_applied': 0,
                    'user_filters_cache_hits': 0,
                    'user_filters_cache_misses': 0,
                    'multi_user_emissions': 0,
                    'total_users_processed': 0,
                    'successful_user_emissions': 0,
                    'failed_user_emissions': 0
                })
                
                logger.info("STARTUP: Multi-user filter statistics initialized")
                return True
                
            else:
                logger.warning("STARTUP: WebSocket publisher does not support multi-user filter caching")
                return False
                
    except Exception as e:
        logger.error(f"Error initializing multi-user filter cache during startup: {e}")
        import traceback
        logger.error(f"Multi-user filter cache initialization traceback: {traceback.format_exc()}")
        return False

def on_user_websocket_connect(websocket_publisher, user_id):
    """
    🆕 SPRINT 1D.3: Called when a user connects to WebSocket to load their filters.
    
    Args:
        websocket_publisher: WebSocketPublisher instance
        user_id: User ID that just connected
    """
    try:
        logger.info(f"USER_CONNECT_FILTER_LOAD: Loading filters for user {user_id}")
        
        # Load filters for this specific user
        user_filters = websocket_publisher.filter_cache.get_or_load_user_filters(user_id)
        
        if user_filters:
            filter_summary = "Active filters loaded"
            try:
                if websocket_publisher.user_filters_service:
                    filter_summary = websocket_publisher.user_filters_service._get_filter_summary(user_filters)
            except Exception:
                pass
            logger.info(f"USER_CONNECT_FILTERS_{user_id}: {filter_summary}")
        else:
            logger.info(f"USER_CONNECT_FILTERS_{user_id}: No saved filters, will use defaults")
        
        return True
        
    except Exception as e:
        logger.error(f"Error loading filters for user {user_id} on connect: {e}")
        return False

def get_multi_user_system_status(market_service):
    """
    🆕 SPRINT 1D.3: Get comprehensive multi-user system status.
    
    Returns:
        dict: Multi-user system status and statistics
    """
    try:
        # Get WebSocket connection stats
        ws_stats = {}
        if hasattr(market_service.websocket_mgr, 'get_user_connection_stats'):
            ws_stats = market_service.websocket_mgr.get_user_connection_stats()
        
        # Get filter stats
        filter_stats = {}
        if hasattr(market_service.websocket_publisher, 'get_multi_user_filter_stats'):
            filter_stats = market_service.websocket_publisher.get_multi_user_filter_stats()
        
        # Get per-user emission stats
        emission_stats = {}
        if hasattr(market_service.websocket_publisher, 'get_per_user_emission_stats'):
            emission_stats = market_service.websocket_publisher.get_per_user_emission_stats()
        
        return {
            'websocket_connections': ws_stats,
            'filter_system': filter_stats,
            'emission_system': emission_stats,
            'overall_status': 'operational',
            'sprint_version': '1D.3',
            'timestamp': time.time()
        }
        
    except Exception as e:
        logger.error(f"Error getting multi-user system status: {e}")
        return {
            'error': str(e),
            'overall_status': 'error',
            'timestamp': time.time()
        }
    
#TRACE TRACING
def start_trace_auto_export(app, config):
    """Start background task for auto-exporting traces."""
    import threading
    import time
    
    def auto_export_loop():
        """Background loop for auto-exporting traces."""
        export_interval = config.get('TRACE_AUTO_EXPORT_INTERVAL', 300)
        
        while True:
            try:
                time.sleep(export_interval)
                
                if tracer.enabled and tracer.traced_tickers:
                    with app.app_context():
                        for ticker in list(tracer.traced_tickers):
                            try:
                                # Check trace size
                                trace = tracer._get_or_create_trace(ticker)
                                if len(trace.steps) > 1000:  # Export if getting large
                                    tracer.export_trace(ticker)
                                    logger.info(f"Auto-exported trace for {ticker}")
                            except Exception as e:
                                logger.error(f"Error auto-exporting trace for {ticker}: {e}")
                                
            except Exception as e:
                logger.error(f"Error in trace auto-export loop: {e}")
                time.sleep(60)
    
    if config.get('TRACE_ENABLED', False):
        export_thread = threading.Thread(target=auto_export_loop, daemon=True, name="trace-auto-export")
        export_thread.start()
        logger.info("Trace auto-export scheduler started")


# ============================================================================
# MAIN APPLICATION EXECUTION
# ============================================================================

if __name__ == '__main__':
    
    
    # Execute startup sequence
    startup_result = run_startup_sequence()
    env_config = startup_result['env_config']
    cache_control = startup_result['cache_control']
    config_manager = startup_result['config_manager']
    config = startup_result['config']
    
    # Create and configure Flask application
    logger = get_domain_logger(LogDomain.CORE, 'app') 
    app = create_flask_app(env_config, cache_control, config)
    extensions = initialize_flask_extensions(app)
    
    # Initialize additional services
    sms_manager = SMSManager(app)
    debug_filter = setup_query_debug_middleware(app, config)

    # Initialize SocketIO
    socketio = initialize_socketio(app, cache_control, config)
    
    # Initialize WebSocket manager
    ws_manager = WebSocketManager(socketio, config)
    
    # Initialize market services with proper order
    event_manager, data_provider, market_service = initialize_market_services(config, cache_control, ws_manager)
    
    #TRACE TRACING
    initialize_tracer(config)
    # Start trace auto-export
    start_trace_auto_export(app, config)
    
    setup_debug_error_logging(app)

    # Setup WebSocket connection
    setup_websocket_connection(market_service, config, cache_control)
    
    # Register handlers and routes
    register_socketio_handlers(socketio, ws_manager, market_service)
    register_error_handlers(app)
    register_basic_routes(app, config)
    
    # Store market_service in app context for API routes
    #app.market_service = market_service  # Ensure this is also set
    registration_result = market_service.register_with_app(app)
    if not registration_result.success:
        logger.error(f"Failed to register market service: {registration_result.errors}")
    
    market_service.websocket_publisher.user_settings_service.app = app
    logger.info("✅ UserSettingsService app reference updated for context management")

    user_universe_manager = market_service.universe_coordinator.user_universe_manager
    user_universe_manager.user_settings_service.app = app
    logger.info("✅ UserUniverseManager's UserSettingsService app reference updated")


    # 🆕 SPRINT 1C: Initialize filter cache AFTER market_service is ready
    initialize_multi_user_filter_cache(app, market_service)

    # FIXED: Start database sync scheduler AFTER market_service is properly initialized
    # IMPORTANT: Database Sync Logic (here and market_data_service.py-publish_stock_data)
    #start_database_sync_scheduler_example(app, market_service)
    start_enhanced_database_sync_scheduler(app, market_service, config)
 
    # Import and register route modules
    from src.api.rest.auth import register_auth_routes
    from src.api.rest.main import register_main_routes  
    from src.api.rest.api import register_api_routes
    
    register_auth_routes(app, extensions, cache_control, config)
    register_main_routes(app, extensions, cache_control, config)
    register_api_routes(app, extensions, cache_control, config)
    
    logger.debug(f"Starting TickStock application with session ID: {get_session_id()}")
    logger.info(f"Data mode: {'Synthetic' if config.get('USE_SYNTHETIC_DATA') else 'Real-time Polygon' if config.get('USE_POLYGON_API') else 'Simulated'}")
    logger.info("Ticker data will be initialized on first data receipt")
    
    # Start market data processing loop
    eventlet.spawn(run_update_loop, market_service, config)
    
    # TRACE DIAGNOSTICS MONITORING
    # TRACE DIAGNOSTICS MONITORING
    # Start the monitor thread
    # TRACE DIAGNOSTICS MONITORING
    if config.get('TRACE_ENABLED', False):
        # Import monitoring components
        from src.monitoring.system_monitor import system_monitor, SystemMonitor, MonitoringConfig
        
        # Enable tracer for specific tickers
        trace_tickers = config.get('TRACE_TICKERS', ['AAPL', 'GOOGL', 'MSFT'])
        tracer.enable_for_tickers(trace_tickers)
        
        # Configure monitoring with custom settings if needed
        monitor_config = MonitoringConfig(
            write_diagnostics_file=True,  # Explicitly enable
            diagnostic_dump_interval=60,  # Customize intervals if desired
            collection_interval=25
        )
        
        # Update the global system_monitor instance with config
        system_monitor.config = monitor_config
        
        # Set services (assuming market_service and data_publisher exist at this point)
        system_monitor.set_services(
            market_service=market_service,
            data_publisher=market_service.data_publisher,
            websocket_publisher=market_service.websocket_publisher
        )
        
        # Start monitoring
        system_monitor.start_monitoring()
        logger.info(f"🔍 Monitoring enabled for: {', '.join(trace_tickers)}")
    # TRACE DIAGNOSTICS MONITORING
    # TRACE DIAGNOSTICS MONITORING
    # TRACE DIAGNOSTICS MONITORING


    # Run the application
    socketio.run(
        app,
        debug=env_config['APP_DEBUG'],
        host=env_config['APP_HOST'],
        port=env_config['APP_PORT'],
        use_reloader=False
    )