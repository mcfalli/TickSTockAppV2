"""
Enhanced API and Utility Routes with Database Persistence
Handles API endpoints, debug routes, universe management, and utility functions.
"""
import logging
from datetime import datetime, timezone
import time

from flask import current_app, jsonify, request, session
from flask_mail import Message
from flask_login import login_required, current_user

from src.shared.utils.app_utils import generate_test_events
from src.infrastructure.database import User, db, Subscription
from src.core.services.user_settings_service import UserSettingsService
from config.logging_config import get_domain_logger, LogDomain

from src.core.services.user_filters_service import UserFiltersService
from src.monitoring.tracer import tracer, TraceLevel, normalize_event_type, ensure_int
from src.presentation.websocket.publisher import WebSocketPublisher


logger = logging.getLogger(__name__)
api_logger = get_domain_logger(LogDomain.USER_SETTINGS, 'api_routes')


def register_api_routes(app, extensions, cache_control, config):
    """Register all API and utility routes with enhanced universe management."""
    
    # Get instances from extensions
    mail = extensions['mail']
    
    # Initialize the user settings service
    user_settings_service = UserSettingsService(cache_control)
        
    @app.route('/api/cache', methods=['GET'])
    def get_cache_contents():
        """Debug endpoint to view cache contents."""
        if not config.get('APP_DEBUG', False):
            return jsonify({"error": "Debug endpoint disabled in non-debug mode"}), 403
        return jsonify(cache_control.get_cache_contents())

    @app.route('/api/cache/reset', methods=['POST'])
    def reset_cache():
        """Debug endpoint to reset cache."""
        try:
            cache_control.reset_cache()
            return jsonify({"status": "Cache reset successfully"})
        except Exception as e:
            logger.error("Error resetting cache: %s", str(e))
            return jsonify({"error": str(e)}), 500

    @app.route('/api/metrics', methods=['GET'])
    def get_metrics():
        """Get enhanced application metrics with universe tracking."""
        try:
            # Get market service from Flask app context if available
            market_service = getattr(app, 'market_service', None)
            
            if not market_service:
                return jsonify({"error": "Market service not initialized"}), 500
            
            # Basic metrics
            metrics = {
                "event_counts": {
                    "processed_events": getattr(market_service, 'total_events_processed', 0),
                    "unique_highs": len(getattr(market_service, 'sent_high_events', {})),
                    "unique_lows": len(getattr(market_service, 'sent_low_events', {})),
                    "total_events": len(getattr(market_service, 'sent_high_events', {})) + 
                                   len(getattr(market_service, 'sent_low_events', {}))
                },
                "performance": {
                    "event_queue_size": market_service.event_queue.qsize() if hasattr(market_service, 'event_queue') else 0,
                    "worker_queue_sizes": [q.qsize() for q in market_service.worker_queues] if hasattr(market_service, 'worker_queues') else [],
                    "circuit_breaker_triggers": getattr(market_service, 'circuit_breaker_triggers', 0)
                },
                "session": {
                    "current_session": getattr(market_service, 'current_session', 'unknown'),
                    "connected_clients": market_service.websocket_mgr.get_client_count() if hasattr(market_service, 'websocket_mgr') and market_service.websocket_mgr else 0
                },
                "timestamp": datetime.now().isoformat()
            }
            
            # Add universe tracking metrics
            if hasattr(market_service, 'universe_stats'):
                metrics["universe_tracking"] = {
                    "current_user_universes": getattr(market_service, 'current_user_universes', {}),
                    "processing_stats": market_service.universe_stats.get('processing_stats', {}),
                    "subscription_stats": {
                        "last_subscription_count": market_service.universe_stats.get('last_subscription_count', 0),
                        "last_universe_count": market_service.universe_stats.get('last_universe_count', 0),
                        "last_overlap_count": market_service.universe_stats.get('last_overlap_count', 0),
                        "last_coverage_percentage": market_service.universe_stats.get('last_coverage_percentage', 0)
                    }
                }
            
            # Add tracker metrics
            if hasattr(market_service, 'buysell_market_tracker'):
                market_tracker_info = market_service.buysell_market_tracker.get_universe_info()
                metrics["tracker_info"] = {
                    "market_tracker": market_tracker_info
                }
            
            return jsonify(metrics)
        except Exception as e:
            logger.error(f"Error getting metrics: {e}")
            return jsonify({"error": "Failed to get metrics"}), 500
  
    '''
    @app.route('/test_email')
    def test_email():
        """Test email functionality."""
        try:
            msg = Message(
                subject="Test Email",
                recipients=["test@example.com"],
                body="This is a test email from TickStock.",
                sender=app.config['MAIL_DEFAULT_SENDER']
            )
            mail.send(msg)
            return jsonify({"status": "Test email sent"})
        except Exception as e:
            logger.error("Test email failed: %s", str(e), exc_info=True)
            return jsonify({"error": str(e)}), 500
    '''
    @app.route('/api/test_events')
    def api_test_events():
        """Generate test events for debugging."""
        try:
            # Get market service from Flask app context if available
            market_service = getattr(app, 'market_service', None)
            
            if not market_service:
                # Return basic test events without market service
                test_events = {
                    "highs": [{"ticker": "AAPL", "price": 175.5, "time": datetime.now().strftime("%H:%M:%S"), 
                             "market_status": "test", "count": 1, "label": "Test high"}],
                    "lows": [{"ticker": "MSFT", "price": 350.25, "time": datetime.now().strftime("%H:%M:%S"), 
                            "market_status": "test", "count": 1, "label": "Test low"}],
                    "counts": {"highs": 1, "lows": 1, "total_highs": 1, "total_lows": 1},
                    "market_status": "test",
                    "source": "Test Events",
                    "is_synthetic": True
                }
            else:
                test_events = generate_test_events(market_service)
            
            return jsonify(test_events)
        except Exception as e:
            logger.error(f"Error generating test events: {e}")
            return jsonify({"error": "Failed to generate test events"}), 500

    @app.route('/api/health')
    def health_check():
        """Enhanced health check endpoint with universe tracking status."""
        try:
            # Basic health checks
            health_status = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "version": "1.0.0",
                "environment": config.get('APP_ENVIRONMENT', 'unknown'),
                "checks": {
                    "database": "unknown",
                    "cache": "unknown",
                    "redis": "unknown",
                    "universe_tracking": "unknown"
                }
            }
            
            # Test database connection
            try:
                db.session.execute("SELECT 1")
                health_status["checks"]["database"] = "healthy"
            except Exception as e:
                health_status["checks"]["database"] = f"unhealthy: {str(e)}"
                health_status["status"] = "degraded"
            
            # Test cache
            try:
                cache_contents = cache_control.get_cache_contents()
                if cache_contents:
                    health_status["checks"]["cache"] = "healthy"
                else:
                    health_status["checks"]["cache"] = "empty"
                    health_status["status"] = "degraded"
            except Exception as e:
                health_status["checks"]["cache"] = f"unhealthy: {str(e)}"
                health_status["status"] = "degraded"
            
            # Test Redis (if configured)
            try:
                app_settings = cache_control.get_cache('app_settings') or {}
                redis_url = app_settings.get('REDIS_URL')
                if redis_url:
                    import redis
                    test_client = redis.Redis.from_url(redis_url)
                    test_client.ping()
                    health_status["checks"]["redis"] = "healthy"
                else:
                    health_status["checks"]["redis"] = "not_configured"
            except Exception as e:
                health_status["checks"]["redis"] = f"unhealthy: {str(e)}"
            
            # Test universe tracking
            try:
                universes = cache_control.get_available_universes()
                if universes and len(universes) > 0:
                    health_status["checks"]["universe_tracking"] = f"healthy ({len(universes)} universes available)"
                else:
                    health_status["checks"]["universe_tracking"] = "no universes available"
                    health_status["status"] = "degraded"
            except Exception as e:
                health_status["checks"]["universe_tracking"] = f"unhealthy: {str(e)}"
                health_status["status"] = "degraded"
            
            return jsonify(health_status)
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return jsonify({
                "status": "unhealthy",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }), 500


    @app.route('/api/analytics/summary')
    @login_required
    def analytics_summary():
        """Get analytics summary for current session."""
        try:
            market_service = app.market_service
            summary = market_service.market_analytics_manager.get_session_summary()
            
            return jsonify({
                'success': True,
                'summary': summary,
                'timestamp': time.time()
            })
        except Exception as e:
            logger.error(f"Error getting analytics summary: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/analytics/pressure-data')
    @login_required 
    def analytics_pressure_data():
        """Get pressure bar visualization data."""
        try:
            market_service = app.market_service
            limit = request.args.get('limit', 50, type=int)
            
            pressure_data = market_service.market_analytics_manager.get_analytics_for_visualization(limit=limit)
            
            return jsonify({
                'success': True,
                'pressure_data': pressure_data,
                'timestamp': time.time()
            })
        except Exception as e:
            logger.error(f"Error getting pressure data: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/analytics/performance')
    @login_required
    def analytics_performance():
        """Get analytics performance report."""
        try:
            market_service = app.market_service
            performance_report = market_service.market_analytics_manager.get_performance_report()
            
            return jsonify({
                'success': True,
                'performance': performance_report,
                'timestamp': time.time()
            })
        except Exception as e:
            logger.error(f"Error getting analytics performance: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500





    # Register enhanced universe API routes
    register_universe_api_routes(app, cache_control, user_settings_service, config)


def register_universe_api_routes(app, cache_control, user_settings_service, config):
    """
    Register enhanced universe-related API routes with database persistence
    
    Args:
        app: Flask application instance
        cache_control: CacheControl instance for accessing universe data
        user_settings_service: UserSettingsService for database operations
    """
    
    @app.route('/api/universes', methods=['GET'])
    @login_required
    def get_available_universes():
        """Get all available universes with metadata"""
        try:
            # Initialize cache_control if needed
            if not hasattr(cache_control, '_initialized') or not cache_control._initialized:
                cache_control.initialize()
            
            # Get universe data from cache
            universes = cache_control.get_available_universes()
            
            return jsonify(universes)
            
        except Exception as e:
            api_logger.error(f"Error fetching universes: {e}", exc_info=True)
            logger.error(f"Error fetching universes: {e}", exc_info=True)
            
            # Return fallback data
            fallback_universes = {
                'DEFAULT_UNIVERSE': {
                    'count': 762, 
                    'description': 'Balanced selection across market caps and sectors'
                },
                'MARKET_CAP_LARGE_UNIVERSE': {
                    'count': 545, 
                    'description': 'Large capitalization stocks with high liquidity'
                },
                'MARKET_CAP_MID_UNIVERSE': {
                    'count': 1000, 
                    'description': 'Mid capitalization stocks with growth potential'
                },
                'LEADER_UNIVERSE': {
                    'count': 500, 
                    'description': 'Industry leaders and market-moving stocks'
                }
            }
            return jsonify(fallback_universes)

    @app.route('/api/universes/select', methods=['POST']) 
    @login_required
    def select_universes():
        """Save user's selected universes for a specific tracker to database with cache invalidation"""
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            
            tracker = data.get('tracker')
            universes = data.get('universes', [])
            
            if not tracker:
                return jsonify({'error': 'Tracker not specified'}), 400
            
            if not universes:
                return jsonify({'error': 'No universes selected'}), 400
            
            # Validate tracker type
            if tracker not in ['market', 'highlow']:
                return jsonify({'error': 'Invalid tracker type'}), 400
            
            # Validate universe keys
            available_universes = cache_control.get_available_universes()
            invalid_universes = [u for u in universes if u not in available_universes]
            if invalid_universes:
                return jsonify({'error': f'Invalid universes: {invalid_universes}'}), 400
            
            # 🔧 FIX: Get OLD state from src.infrastructure.database BEFORE any changes
            old_selections = user_settings_service.get_universe_selections(current_user.id)
            old_universes = old_selections.get(tracker, []).copy()  # Make a copy!
            
            # Update the specific tracker
            current_selections = old_selections.copy()
            current_selections[tracker] = universes
            
            # Save to database
            success = user_settings_service.save_universe_selections(current_user.id, current_selections)
            
            if not success:
                api_logger.error(f"Failed to save universe selections for user {current_user.username}")
                return jsonify({'error': 'Failed to save universe selections'}), 500
            
            # Cache invalidation (existing code continues...)
            cache_invalidation_success = False
            try:
                # Invalidate the user's universe cache
                if hasattr(app, 'market_service') and app.market_service:
                    # Method 1: Direct invalidation via market service
                    cache_invalidation_success = app.market_service.universe_coordinator.invalidate_user_universe_cache(current_user.id)
                    
                    if cache_invalidation_success:
                        #api_logger.info(f"UNIVERSE_CACHE_INVALIDATE: Successfully invalidated cache for user {current_user.id}")
                        
                        # Update the market service with new universe selections
                        app.market_service.universe_coordinator.update_user_universe_selections(current_user.id, tracker, universes)

                        # Method 2: Direct websocket publisher cache invalidation (backup)
                        if hasattr(app.market_service, 'websocket_publisher'):
                            app.market_service.websocket_publisher.universe_cache.invalidate_cache(current_user.id)
                            #api_logger.debug(f"WEBSOCKET_CACHE_INVALIDATE: Backup cache invalidation for user {current_user.id}")
                    #else:
                    #    api_logger.warning(f"Failed to invalidate universe cache for user {current_user.id}")
                
                # Method 3: Direct websocket publisher access (if market_service unavailable)
                elif hasattr(app, 'websocket_publisher'):
                    cache_invalidation_success = app.websocket_publisher.universe_cache.invalidate_cache(current_user.id)
                    api_logger.info(f"DIRECT_CACHE_INVALIDATE: Cache invalidation via websocket_publisher for user {current_user.id}")
                
            except Exception as cache_error:
                api_logger.error(f"Error invalidating universe cache for user {current_user.id}: {cache_error}")
                cache_invalidation_success = False
            
            # Migrate session data if it exists (for backward compatibility)
            if 'universe_selections' in session:
                api_logger.info(f"Migrating session data to database for user {current_user.username}")
                user_settings_service.migrate_session_to_database(current_user.id, session)
                # Clear session data after migration
                session.pop('universe_selections', None)
            
            api_logger.info(f"User {current_user.username} selected universes for {tracker}: {universes}")
            logger.info(f"User {current_user.username} selected universes for {tracker}: {universes}")
            
            return jsonify({
                'status': 'success', 
                'tracker': tracker, 
                'universes': universes,
                'message': f'Universe selection updated for {tracker} tracker',
                'storage': 'database',  # Indicate database storage
                'cache_invalidated': cache_invalidation_success,  # NEW: Report cache invalidation status
                'user_id': current_user.id  # NEW: Include user ID for debugging
            })
            
        except Exception as e:
            api_logger.error(f"Error saving universe selection: {e}", exc_info=True)
            logger.error(f"Error saving universe selection: {e}", exc_info=True)
            return jsonify({'error': 'Internal server error'}), 500

    # 🆕 CHUNK 4: NEW ENDPOINT - Get user's universe cache status for debugging
    @app.route('/api/user/universe-cache-status', methods=['GET'])
    @login_required
    def get_user_universe_cache_status():
        """Get universe cache status for current user - debugging endpoint"""
        try:
            cache_status = {'user_id': current_user.id, 'cache_found': False}
            
            # Try to get cache status from market service
            if hasattr(app, 'market_service') and app.market_service:
                if hasattr(app.market_service, 'websocket_publisher'):
                    # Get overall cache status
                    overall_cache = app.market_service.websocket_publisher.get_universe_cache_status()
                    cache_status.update(overall_cache)
                    
                    # Check if this user is cached
                    cached_users = cache_status.get('cached_users', [])
                    cache_status['cache_found'] = current_user.id in cached_users
                    
                    # Get user's specific universe info if available
                    if hasattr(app.market_service, 'get_user_universe_info'):
                        user_universe_info = app.market_service.get_user_universe_info(current_user.id)
                        cache_status['user_universe_info'] = user_universe_info
                    
            return jsonify(cache_status)
            
        except Exception as e:
            api_logger.error(f"Error getting universe cache status: {e}")
            return jsonify({'error': str(e), 'user_id': current_user.id}), 500

    # 🆕 CHUNK 4: NEW ENDPOINT - Manual cache invalidation for testing
    @app.route('/api/user/universe-cache/invalidate', methods=['POST'])
    @login_required
    def invalidate_user_universe_cache_endpoint():
        """Manually invalidate current user's universe cache - for testing/debugging"""
        try:
            success = False
            
            if hasattr(app, 'market_service') and app.market_service:
                success = app.market_service.universe_coordinator.invalidate_user_universe_cache(current_user.id)
            elif hasattr(app, 'websocket_publisher'):
                success = app.websocket_publisher.universe_cache.invalidate_cache(current_user.id)
            
            if success:
                api_logger.info(f"MANUAL_CACHE_INVALIDATE: Successfully invalidated cache for user {current_user.id}")
                return jsonify({
                    'success': True,
                    'message': f'Universe cache invalidated for user {current_user.id}',
                    'user_id': current_user.id
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Failed to invalidate cache',
                    'user_id': current_user.id
                }), 500
                
        except Exception as e:
            api_logger.error(f"Error in manual cache invalidation: {e}")
            return jsonify({'error': str(e), 'user_id': current_user.id}), 500

    @app.route('/api/user/settings', methods=['GET'])
    @login_required
    def get_user_settings():
        """Get all user settings from src.infrastructure.database"""
        try:
            settings = user_settings_service.get_all_user_settings(current_user.id)
            
            return jsonify({
                'settings': settings,
                'user_id': current_user.id,
                'storage': 'database'
            })
            
        except Exception as e:
            api_logger.error(f"Error getting user settings: {e}", exc_info=True)
            return jsonify({'error': 'Internal server error'}), 500

    @app.route('/api/user/settings', methods=['POST']) 
    @login_required
    def update_user_settings():
        """Update user settings in database"""
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            
            setting_key = data.get('key')
            setting_value = data.get('value')
            
            if not setting_key:
                return jsonify({'error': 'Setting key required'}), 400
            
            success = user_settings_service.set_user_setting(current_user.id, setting_key, setting_value)
            
            if success:
                api_logger.info(f"Updated setting {setting_key} for user {current_user.username}")
                return jsonify({
                    'status': 'success',
                    'key': setting_key,
                    'message': f'Setting {setting_key} updated successfully',
                    'storage': 'database'
                })
            else:
                return jsonify({'error': 'Failed to update setting'}), 500
                
        except Exception as e:
            api_logger.error(f"Error updating user settings: {e}", exc_info=True)
            return jsonify({'error': 'Internal server error'}), 500

    
    

    @app.route('/api/user/settings/<setting_key>', methods=['GET'])
    @login_required
    def get_user_setting(setting_key):
        """Get a specific user setting"""
        try:
            # The service should handle the database query
            setting_data = user_settings_service.get_user_setting(current_user.id, setting_key)
            
            api_logger.info(f"Raw setting data for {setting_key}: {setting_data}")
            
            if setting_data is not None:
                # Log the type and structure
                api_logger.info(f"Setting data type: {type(setting_data)}")
                if isinstance(setting_data, dict):
                    api_logger.info(f"Setting data keys: {list(setting_data.keys())}")
                
                return jsonify({
                    'success': True,
                    'setting_value': setting_data,
                    'updated_at': datetime.now(timezone.utc).isoformat()  # Temp timestamp
                })
            else:
                api_logger.info(f"No setting found for {setting_key} for user {current_user.username}")
                return jsonify({
                    'success': True,
                    'setting_value': None,
                    'updated_at': None
                })
                
        except Exception as e:
            api_logger.error(f"Error getting user setting {setting_key}: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/user/settings/<setting_key>', methods=['POST'])
    @login_required
    def save_user_setting(setting_key):
        """Save or update a specific user setting"""
        try:
            data = request.get_json()
            setting_value = data.get('setting_value')
            
            if setting_value is None:
                return jsonify({'error': 'No setting value provided'}), 400
            
            success = user_settings_service.set_user_setting(
                current_user.id, 
                setting_key, 
                setting_value
            )
            
            if success:
                api_logger.info(f"Saved setting {setting_key} for user {current_user.username}")
                return jsonify({
                    'success': True,
                    'message': f'Setting {setting_key} saved successfully',
                    'updated_at': datetime.now(timezone.utc).isoformat()
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Failed to save setting'
                }), 500
            
        except Exception as e:
            api_logger.error(f"Error saving user setting {setting_key}: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500



    @app.route('/api/user/universe-selections', methods=['GET'])
    @login_required
    def get_user_universe_selections():
        """Get user's current universe selections from src.infrastructure.database"""
        try:
            # Migrate session data if it exists
            if 'universe_selections' in session:
                api_logger.info(f"Auto-migrating session data for user {current_user.username}")
                user_settings_service.migrate_session_to_database(current_user.id, session)
                session.pop('universe_selections', None)
            
            # Get selections from src.infrastructure.database
            selections = user_settings_service.get_universe_selections(current_user.id)
            

            # Get ticker counts for each selection
            enhanced_selections = {}
            
            for tracker, universes in selections.items():
                all_tickers = set()
                universe_details = {}
                
                for universe_key in universes:
                    try:
                        tickers = cache_control.get_universe_tickers(universe_key)
                        all_tickers.update(tickers)
                        
                        metadata = cache_control.get_universe_metadata(universe_key)
                        universe_details[universe_key] = {
                            'count': len(tickers),
                            'description': metadata.get('description', ''),
                            'criteria': metadata.get('criteria', '')
                        }
                    except Exception as e:
                        api_logger.warning(f"Could not get details for universe {universe_key}: {e}")
                        universe_details[universe_key] = {
                            'count': 0,
                            'description': 'Error loading universe',
                            'error': str(e)
                        }
                
                enhanced_selections[tracker] = {
                    'universes': universes,
                    'total_unique_tickers': len(all_tickers),
                    'universe_details': universe_details
                }
            
            
            return jsonify({
                'selections': enhanced_selections,
                'storage': 'database',
                'user_id': current_user.id
            })
            
        except Exception as e:
            api_logger.error(f"Error getting current selections: {e}", exc_info=True)
            # Return safe defaults on error
            return jsonify({
                'selections': {
                    'market': {
                        'universes': ['DEFAULT_UNIVERSE'], 
                        'total_unique_tickers': 762,
                        'universe_details': {
                            'DEFAULT_UNIVERSE': {
                                'count': 762,
                                'description': 'Default balanced universe'
                            }
                        }
                    },
                    'highlow': {
                        'universes': ['DEFAULT_UNIVERSE'], 
                        'total_unique_tickers': 762,
                        'universe_details': {
                            'DEFAULT_UNIVERSE': {
                                'count': 762,
                                'description': 'Default balanced universe'
                            }
                        }
                    }
                },
                'storage': 'database',
                'error': 'Using fallback data'
            })

    @app.route('/api/universes/tickers', methods=['POST'])
    @login_required
    def get_universe_tickers():
        """Get combined ticker list from selected universes"""
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            
            universes = data.get('universes', [])
            
            if not universes:
                return jsonify({'error': 'No universes specified'}), 400
            
            # Get all tickers for the specified universes
            all_tickers = set()
            universe_details = {}
            
            for universe_key in universes:
                try:
                    tickers = cache_control.get_universe_tickers(universe_key)
                    all_tickers.update(tickers)
                    
                    metadata = cache_control.get_universe_metadata(universe_key)
                    universe_details[universe_key] = {
                        'count': len(tickers),
                        'tickers': tickers,
                        'description': metadata.get('description', ''),
                        'criteria': metadata.get('criteria', '')
                    }
                except Exception as e:
                    api_logger.warning(f"Could not get tickers for universe {universe_key}: {e}")
                    universe_details[universe_key] = {
                        'count': 0,
                        'tickers': [],
                        'error': str(e)
                    }
            
            # Convert set to sorted list
            combined_tickers = sorted(list(all_tickers))
            
            result = {
                'universes_requested': universes,
                'total_unique_tickers': len(combined_tickers),
                'tickers': combined_tickers,
                'universe_breakdown': universe_details,
                'storage': 'database'
            }
            
            
            return jsonify(result)
            
        except Exception as e:
            api_logger.error(f"Error getting universe tickers: {e}", exc_info=True)
            return jsonify({'error': 'Internal server error'}), 500

    @app.route('/api/universes/current', methods=['GET'])
    @login_required  
    def get_current_selections():
        """Legacy endpoint - redirects to /api/user/universe-selections"""
        api_logger.info("Legacy endpoint accessed, redirecting to database-backed endpoint")
        return get_user_universe_selections()

    # New endpoints for database management
    
    @app.route('/api/user/settings/migrate', methods=['POST'])
    @login_required
    def migrate_user_settings():
        """Manually trigger migration from session to database"""
        try:
            session_data = {}
            if 'universe_selections' in session:
                session_data['universe_selections'] = session['universe_selections']
            
            if session_data:
                success = user_settings_service.migrate_session_to_database(current_user.id, session_data)
                
                if success:
                    # Clear session data after successful migration
                    session.pop('universe_selections', None)
                    
                    api_logger.info(f"Manual migration successful for user {current_user.username}")
                    
                    return jsonify({
                        'status': 'success',
                        'message': 'Settings migrated to database successfully',
                        'migrated_data': list(session_data.keys())
                    })
                else:
                    return jsonify({'error': 'Migration failed'}), 500
            else:
                return jsonify({
                    'status': 'success',
                    'message': 'No session data to migrate'
                })
                
        except Exception as e:
            api_logger.error(f"Error during manual migration: {e}", exc_info=True)
            return jsonify({'error': 'Migration failed'}), 500

    @app.route('/api/user/settings/<setting_key>', methods=['DELETE'])
    @login_required
    def delete_user_setting(setting_key):
        """Delete a specific user setting"""
        try:
            success = user_settings_service.delete_user_setting(current_user.id, setting_key)
            
            if success:
                api_logger.info(f"Deleted setting {setting_key} for user {current_user.username}")
                return jsonify({
                    'status': 'success',
                    'message': f'Setting {setting_key} deleted successfully'
                })
            else:
                return jsonify({'error': 'Failed to delete setting'}), 500
                
        except Exception as e:
            api_logger.error(f"Error deleting setting {setting_key}: {e}", exc_info=True)
            return jsonify({'error': 'Internal server error'}), 500
        
    #-----------------------------------------------------

    @app.route('/api/user-filters', methods=['GET'])
    @login_required
    def get_user_filters():
        """
        🔧 SPRINT 1D.3: ADDED - Missing GET route for user filters.
        """
        try:
            # Initialize the user filter service
            user_filters_service = UserFiltersService()
            
            filter_name = request.args.get('filter_name', 'default')
            
            # Load filters using the service
            filter_data = user_filters_service.load_user_filters(current_user.id, filter_name)
            
            logger.info(f"FILTER_API_GET: Loaded filters for user {current_user.id}: {filter_data}")

            return jsonify({
                'success': True,
                'filter_data': filter_data,
                'user_id': current_user.id,
                'filter_name': filter_name
            })
                
        except Exception as e:
            logger.error(f"FILTER_API_GET: Error loading user filters: {e}", exc_info=True)
           
            return jsonify({
                'success': False, 
                'error': 'Failed to load filters'
            }), 500

    @app.route('/api/user-filters', methods=['POST'])
    @login_required
    def save_user_filters():
        """
        🔧 SPRINT 1D.3: FIXED - Handle correct frontend data structure.
        """
        try:
            # Initialize the user filter service
            user_filters_service = UserFiltersService()
            
            # Get request data
            request_data = request.get_json()
            logger.info(f"FILTER_API_SAVE: Received request data: {request_data}")
            
            if not request_data:
                return jsonify({'success': False, 'error': 'No data provided'}), 400
            
            # 🔧 CRITICAL FIX: Handle the exact structure the frontend sends
            if 'filter_data' in request_data:
                # Frontend sends: {filter_data: {filters: {...}, version: "1.0"}, filter_name: "default"}
                filter_data = request_data['filter_data']
                filter_name = request_data.get('filter_name', 'default')
            else:
                # Direct filter data: {filters: {...}, version: "1.0"}
                filter_data = request_data
                filter_name = 'default'
            
            logger.info(f"FILTER_API_SAVE: Processing filter_data: {filter_data}")
            logger.info(f"FILTER_API_SAVE: Has 'filters' key: {'filters' in filter_data}")
            logger.info(f"FILTER_API_SAVE: Filter structure keys: {list(filter_data.get('filters', {}).keys())}")
            
            # Validate filter structure - the validation is working based on logs
            if not user_filters_service.validate_filter_data(filter_data):
                logger.error(f"FILTER_API_SAVE: Validation failed for filter_data: {filter_data}")
                return jsonify({
                    'success': False, 
                    'error': 'Invalid filter data structure',
                    'debug_info': {
                        'has_filters_key': 'filters' in filter_data,
                        'filter_data_keys': list(filter_data.keys()),
                        'filters_content': filter_data.get('filters', 'NO_FILTERS_KEY')
                    }
                }), 400
            
            # Save to database
            success = user_filters_service.save_user_filters(current_user.id, filter_data, filter_name)
            
            if success:
                
                # Update cache (Sprint 1D.3 functionality)
                cache_updated = False
                try:
                    if hasattr(current_app, 'websocket_publisher'):
                        current_app.websocket_publisher.filter_cache.update_cache(current_user.id, filter_data)
                        cache_updated = True
                    elif hasattr(current_app, 'market_service') and hasattr(current_app.market_service, 'websocket_publisher'):
                        current_app.market_service.websocket_publisher.filter_cache.update_cache(current_user.id, filter_data)
                        cache_updated = True
                        
                    logger.info(f"FILTER_API_SAVE: Cache update result: {cache_updated}")
                    
                except Exception as cache_error:
                    logger.error(f"FILTER_API_SAVE: Cache update error: {cache_error}")
                    cache_updated = False
                
                return jsonify({
                    'success': True,
                    'message': 'Filters saved successfully',
                    'cache_updated': cache_updated,
                    'user_id': current_user.id
                })
            else:
                return jsonify({
                    'success': False, 
                    'error': 'Failed to save filters to database'
                }), 500
                
        except Exception as e:
            logger.error(f"FILTER_API_SAVE: Unexpected error: {e}", exc_info=True)
            return jsonify({
                'success': False, 
                'error': 'Internal server error',
                'details': str(e)
            }), 500

    @app.route('/api/user-filters/cache-status', methods=['GET'])
    @login_required
    def get_user_filter_cache_status():
        """
        🆕 SPRINT 1D.3: Get user filter cache status for debugging.
        """
        try:
            from flask import jsonify, current_app
            from flask_login import current_user
            
            if not hasattr(current_app, 'websocket_publisher'):
                return jsonify({'error': 'WebSocket publisher not available'}), 500
            
            # Get user-specific cache status
            user_cached = current_user.id in getattr(current_app.websocket_publisher, 'current_user_filters', {})
            
            # Get overall cache statistics
            cache_stats = {}
            if hasattr(current_app.websocket_publisher, 'get_multi_user_filter_stats'):
                try:
                    cache_stats = current_app.websocket_publisher.get_multi_user_filter_stats()
                except Exception as stats_error:
                    logger.error(f"Error getting filter stats: {stats_error}")
                    cache_stats = {'error': str(stats_error)}
            
            # Get user's specific filter info
            user_filter_info = None
            if user_cached:
                try:
                    user_filters = current_app.websocket_publisher.current_user_filters[current_user.id]
                    user_filter_info = {
                        'has_filters': bool(user_filters.get('filters')),
                        'filter_categories': list(user_filters.get('filters', {}).keys()),
                        'version': user_filters.get('version'),
                        'timestamp': user_filters.get('timestamp')
                    }
                except Exception as user_info_error:
                    logger.error(f"Error getting user filter info: {user_info_error}")
                    user_filter_info = {'error': str(user_info_error)}
            
            return jsonify({
                'user_id': current_user.id,
                'user_cached': user_cached,
                'user_filter_info': user_filter_info,
                'overall_cache_stats': cache_stats,
                'sprint_version': '1D.3',
                'timestamp': time.time()
            })
            
        except Exception as e:
            logger.error(f"Error getting filter cache status: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/multi-user-stats', methods=['GET'])
    @login_required  # You might want admin-only access for this
    def get_multi_user_system_stats():
        """
        🆕 SPRINT 1D.3: Get comprehensive multi-user system statistics.
        """
        try:
            from flask import jsonify, current_app
            
            if not hasattr(current_app, 'market_service'):
                return jsonify({'error': 'Market service not available'}), 500
            
            # Get WebSocket connection stats
            ws_stats = {}
            try:
                if hasattr(current_app.market_service.websocket_mgr, 'get_user_connection_stats'):
                    ws_stats = current_app.market_service.websocket_mgr.get_user_connection_stats()
            except Exception as ws_error:
                ws_stats = {'error': str(ws_error)}
            
            # Get filter stats
            filter_stats = {}
            try:
                if hasattr(current_app.websocket_publisher, 'get_multi_user_filter_stats'):
                    filter_stats = current_app.websocket_publisher.get_multi_user_filter_stats()
            except Exception as filter_error:
                filter_stats = {'error': str(filter_error)}
            
            # Get per-user emission stats
            emission_stats = {}
            try:
                if hasattr(current_app.websocket_publisher, 'get_per_user_emission_stats'):
                    emission_stats = current_app.websocket_publisher.get_per_user_emission_stats()
            except Exception as emission_error:
                emission_stats = {'error': str(emission_error)}
            
            return jsonify({
                'websocket_connections': ws_stats,
                'filter_system': filter_stats,
                'emission_system': emission_stats,
                'overall_status': 'operational',
                'sprint_version': '1D.3',
                'timestamp': time.time()
            })
            
        except Exception as e:
            logger.error(f"Error getting multi-user system stats: {e}")
            return jsonify({'error': str(e)}), 500
        
    @app.route('/api/user-filters/invalidate-cache', methods=['POST'])
    @login_required
    def invalidate_user_filter_cache():
        """
        🆕 SPRINT 1D.3: Manually invalidate user's filter cache for testing/debugging.
        """
        try:
            from flask import jsonify, current_app
            from flask_login import current_user
            
            if not hasattr(current_app, 'websocket_publisher'):
                return jsonify({'error': 'WebSocket publisher not available'}), 500
            
            # Invalidate cache for current user
            success = False
            if hasattr(current_app.websocket_publisher, 'filter_cache'):
                success = current_app.websocket_publisher.filter_cache.invalidate_cache(current_user.id)
            
            return jsonify({
                'success': success,
                'user_id': current_user.id,
                'message': 'Cache invalidated successfully' if success else 'Cache invalidation failed',
                'timestamp': time.time()
            })
            
        except Exception as e:
            logger.error(f"Error invalidating user filter cache: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/user-filters/cache/refresh', methods=['POST'])
    @login_required
    def refresh_filter_cache():
        """🆕 SPRINT 1D.3: Manually refresh filter cache for current user."""
        try:
            from flask import current_app
            
            websocket_publisher = None
            
            # Try multiple access paths
            if hasattr(current_app, 'websocket_publisher'):
                websocket_publisher = current_app.websocket_publisher
            elif hasattr(current_app, 'market_service') and current_app.market_service:
                websocket_publisher = current_app.market_service.websocket_publisher
                
            if websocket_publisher:
                # Clear cache for current user and reload
                if hasattr(websocket_publisher, 'filter_cache'):
                    websocket_publisher.filter_cache.invalidate_cache(current_user.id)

                # Reload filters for this user
                if websocket_publisher and websocket_publisher.filter_cache:
                    user_filters = websocket_publisher.filter_cache.get_or_load_user_filters(current_user.id)
                    success = user_filters is not None
                    
                    return jsonify({
                        'success': success,
                        'message': 'Filter cache refreshed' if success else 'Failed to refresh cache',
                        'user_id': current_user.id
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': 'Filter refresh methods not available'
                    }), 503
            else:
                return jsonify({
                    'success': False,
                    'error': 'WebSocket publisher not available'
                }), 503
                
        except Exception as e:
            logger.error(f"Error refreshing filter cache: {e}")
            return jsonify({'success': False, 'error': 'Internal server error'}), 500
        

    #-------------------------------------------------------------------------------------
    # TRACE TRACING
    #-------------------------------------------------------------------------------------
    @app.route('/api/trace/status', methods=['GET'])
    @login_required
    def get_trace_status():
        """Get current trace status and configuration."""
        try:
            
            status = {
                'enabled': tracer.enabled,
                'traced_tickers': list(tracer.traced_tickers),
                'trace_level': tracer.trace_level.name,
                'active_traces': {}
            }
            
            # Get summary for each traced ticker
            for ticker in tracer.traced_tickers:
                summary = tracer.get_trace_summary(ticker)
                if summary:
                    # Pass the full summary to the frontend - let it handle the structure
                    status['active_traces'][ticker] = {'summary': summary}
                
            return jsonify(status)
            
        except Exception as e:
            logger.error(f"Error getting trace status: {e}")
            return jsonify({'error': str(e)}), 500
    @app.route('/api/trace/enable', methods=['POST'])
    @login_required
    def enable_trace():
        """Enable tracing for specific tickers."""
        try:
            
            data = request.get_json()
            tickers = data.get('tickers', [])
            level = data.get('level', 'NORMAL')
            
            if not tickers:
                return jsonify({'error': 'No tickers specified'}), 400
            
            # Convert level string to enum
            trace_level = TraceLevel.NORMAL
            if level == 'CRITICAL':
                trace_level = TraceLevel.CRITICAL
            elif level == 'VERBOSE':
                trace_level = TraceLevel.VERBOSE
            
            tracer.enable_for_tickers(tickers, trace_level)
            
            return jsonify({
                'status': 'success',
                'message': f'Tracing enabled for {len(tickers)} tickers at level {level}',
                'tickers': tickers
            })
            
        except Exception as e:
            logger.error(f"Error enabling trace: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/trace/disable', methods=['POST'])
    @login_required
    def disable_trace():
        """Disable tracing."""
        try:
            
            # Export any active traces before disabling
            for ticker in list(tracer.traced_tickers):
                tracer.export_trace(ticker)
            
            tracer.enabled = False
            tracer.traced_tickers.clear()
            
            return jsonify({
                'status': 'success',
                'message': 'Tracing disabled'
            })
            
        except Exception as e:
            logger.error(f"Error disabling trace: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/trace/export/<ticker>', methods=['POST'])
    @login_required
    def export_trace(ticker):
        """Export trace for a specific ticker."""
        try:
            if ticker not in tracer.traced_tickers:
                return jsonify({'error': f'Ticker {ticker} is not being traced'}), 400
            
            # Call export and get result
            result = tracer.export_trace(ticker)
            
            if result['success']:
                return jsonify({
                    'status': 'success',
                    'message': f'Trace exported for {ticker}',
                    'filepath': result['filepath'],
                    'file_size': result['file_size'],
                    'trace_steps': result['trace_steps'],
                    'emission_traces': result['emission_traces']
                })
            else:
                return jsonify({
                    'status': 'error',
                    'error': result['error'],
                    'available_traces': result.get('available_traces', [])
                }), 500
                
        except Exception as e:
            logger.error(f"Error in export endpoint: {e}")
            return jsonify({'error': str(e)}), 500
        
    @app.route('/api/trace/export/all', methods=['POST'])
    @login_required
    def export_alltrace():
        """Export trace for a specific ticker."""
        try:
            # Call export and get result
            result = tracer.export_all("trace_all")
            
            if result['success']:
                return jsonify({
                    'status': 'success',
                    'message': f'Trace exported for all',
                    'filepath': result['filepath'],
                    'file_size': result['file_size'],
                    'trace_steps': result['trace_steps'],
                    'emission_traces': result['emission_traces']
                })
            else:
                return jsonify({
                    'status': 'error',
                    'error': result['error'],
                    'available_traces': result.get('available_traces', [])
                }), 500
                
        except Exception as e:
            logger.error(f"Error in export endpoint: {e}")
            return jsonify({'error': str(e)}), 500

    #-------------------------------------------------------------------------------------
    # TRACE QUALITY TRACING
    #-------------------------------------------------------------------------------------
    @app.route('/api/quality/metrics/<ticker>')
    @login_required
    def get_ticker_quality_metrics(ticker: str):
        """Get quality metrics for a specific ticker"""
        if not tracer.enabled:
            return jsonify({'error': 'Tracer not enabled'}), 503
        
        metrics = tracer.get_quality_metrics(ticker.upper())
        return jsonify(metrics)

    @app.route('/api/quality/validate/<ticker>')
    @login_required
    def validate_ticker_trace(ticker: str):
        """Validate trace accuracy for a ticker"""
        if not tracer.enabled:
            return jsonify({'error': 'Tracer not enabled'}), 503
        
        validation = tracer.validate_trace_accuracy(ticker.upper())
        return jsonify(validation)

    @app.route('/api/quality/stage-transition/<ticker>')
    @login_required
    def check_stage_transition(ticker: str):
        """Check efficiency between pipeline stages"""
        from_stage = request.args.get('from', 'detected')
        to_stage = request.args.get('to', 'emitted')
        
        if not tracer.enabled:
            return jsonify({'error': 'Tracer not enabled'}), 503
        
        result = tracer.verify_stage_transition(from_stage, to_stage, ticker.upper())
        return jsonify(result)

    @app.route('/api/quality/event-journey')
    @login_required
    def trace_event_journey():
        """Trace a specific event through the pipeline"""
        ticker = request.args.get('ticker', '').upper()
        event_type = request.args.get('event_type', '')
        price = float(request.args.get('price', 0))
        
        if not all([ticker, event_type, price]):
            return jsonify({'error': 'Missing required parameters'}), 400
        
        if not tracer.enabled:
            return jsonify({'error': 'Tracer not enabled'}), 503
        
        journey = tracer.trace_event_journey(ticker, event_type, price)
        return jsonify({
            'ticker': ticker,
            'event_type': event_type,
            'price': price,
            'journey': journey,
            'stages_found': len(journey)
        })

    @app.route('/api/quality/summary')
    @login_required
    def get_quality_summary():
        """Get quality summary for all traced tickers"""
        if not tracer.enabled:
            return jsonify({'error': 'Tracer not enabled'}), 503
        
        summary = {
            'timestamp': time.time(),
            'tickers': {}
        }
        
        for ticker in tracer.get_all_active_traces():
            if ticker != 'SYSTEM':
                metrics = tracer.get_quality_metrics(ticker)
                flow = tracer.get_flow_summary(ticker)
                
                summary['tickers'][ticker] = {
                    'quality_score': metrics.get('overall_quality_score', 0),
                    'issues_count': len(metrics.get('issues', [])),
                    'overall_efficiency': flow.get('overall_efficiency', 0),
                    'events_detected': flow.get('events_detected', 0),
                    'events_emitted': flow.get('events_emitted', 0),
                    'by_type': flow.get('by_type', {})
                }
        
        # Calculate overall system quality
        if summary['tickers']:
            avg_quality = sum(t['quality_score'] for t in summary['tickers'].values()) / len(summary['tickers'])
            summary['overall_quality_score'] = avg_quality
            summary['status'] = 'healthy' if avg_quality >= 90 else 'degraded' if avg_quality >= 70 else 'unhealthy'
        else:
            summary['overall_quality_score'] = 0
            summary['status'] = 'no_data'
        
        return jsonify(summary)

    @app.route('/api/quality/diagnose/<ticker>')
    @login_required
    def diagnose_ticker_issues(ticker: str):
        """Get detailed diagnosis of issues for a ticker"""
        if not tracer.enabled:
            return jsonify({'error': 'Tracer not enabled'}), 503
        
        diagnosis = {
            'ticker': ticker.upper(),
            'timestamp': time.time(),
            'event_loss': tracer.diagnose_event_loss(ticker.upper()),
            'quality_metrics': tracer.get_quality_metrics(ticker.upper()),
            'flow_summary': tracer.get_flow_summary(ticker.upper()),
            'recommendations': []
        }
        
        # Generate specific recommendations based on diagnosis
        quality = diagnosis['quality_metrics']
        flow = diagnosis['flow_summary']
        
        # Check for double counting
        for event_type, data in flow.get('by_type', {}).items():
            if data['detected'] > 0 and data['emitted'] > data['detected'] * 1.05:
                diagnosis['recommendations'].append({
                    'issue': 'double_counting',
                    'event_type': event_type,
                    'severity': 'high',
                    'action': f'Review {event_type} event emission logic for duplicate tracking'
                })
        
        # Check for high loss rates
        for loss_point in diagnosis['event_loss']['event_loss_points']:
            if loss_point['efficiency'] < 70:
                diagnosis['recommendations'].append({
                    'issue': 'high_loss_rate',
                    'stage': loss_point['stage'],
                    'severity': 'high',
                    'action': f"Investigate {loss_point['stage']} stage - losing {loss_point['loss_count']} events"
                })
        
        # Check for empty collections
        empty_rate = (flow.get('empty_collections', 0) / 
                    (flow.get('empty_collections', 0) + flow.get('non_empty_collections', 0)) * 100) if (
                        flow.get('empty_collections', 0) + flow.get('non_empty_collections', 0)) > 0 else 0
        
        if empty_rate > 90:
            diagnosis['recommendations'].append({
                'issue': 'high_empty_collections',
                'rate': empty_rate,
                'severity': 'medium',
                'action': 'Consider increasing collection interval or adjusting event generation thresholds'
            })
        
        return jsonify(diagnosis)