"""
Simplified API Routes - Post-Cleanup
Essential API endpoints for the simplified TickStock architecture.
"""
import logging
from datetime import datetime, timezone

from flask import current_app, jsonify, request, session
from flask_login import login_required, current_user

from src.infrastructure.database import User, db, Subscription
from src.core.services.user_settings_service import UserSettingsService

from src.presentation.websocket.publisher import WebSocketPublisher


logger = logging.getLogger(__name__)
api_logger = logging.getLogger(__name__)


def register_api_routes(app, extensions, cache_control, config):
    """Register simplified API routes for essential functionality."""
    
    # Get instances from extensions
    mail = extensions.get('mail')
    
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
            return jsonify({"error": "Failed to reset cache"}), 500

    @app.route('/api/health')
    @login_required
    def api_health():
        """API health check endpoint."""
        try:
            # Basic health checks
            db_healthy = True
            try:
                db.session.execute('SELECT 1')
            except Exception as e:
                logger.error("Database health check failed: %s", str(e))
                db_healthy = False

            return jsonify({
                "status": "healthy" if db_healthy else "unhealthy",
                "components": {
                    "database": "healthy" if db_healthy else "unhealthy",
                    "api": "healthy"
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        except Exception as e:
            logger.error("Health check failed: %s", str(e))
            return jsonify({
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }), 500

    # User Settings Endpoints
    @app.route('/api/user/settings', methods=['GET'])
    @login_required
    def get_user_settings():
        """Get user settings."""
        try:
            settings = user_settings_service.get_user_settings(current_user.id)
            return jsonify({
                "success": True,
                "settings": settings,
                "user_id": current_user.id
            })
        except Exception as e:
            logger.error("Error getting user settings: %s", str(e))
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route('/api/user/settings', methods=['POST']) 
    @login_required
    def save_user_settings():
        """Save user settings."""
        try:
            settings_data = request.get_json()
            if not settings_data:
                return jsonify({
                    "success": False,
                    "error": "No settings data provided"
                }), 400

            success = user_settings_service.save_user_settings(
                current_user.id, 
                settings_data
            )
            
            if success:
                return jsonify({
                    "success": True,
                    "message": "Settings saved successfully",
                    "user_id": current_user.id
                })
            else:
                return jsonify({
                    "success": False,
                    "error": "Failed to save settings"
                }), 500
                
        except Exception as e:
            logger.error("Error saving user settings: %s", str(e))
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    # Removed: User Filters endpoints (post-button cleanup)


    # Removed: Universe Management endpoints (post-button cleanup)

    # TickStockPL Integration - Pattern Alerts API Endpoints
    @app.route('/api/tickstockpl/alerts/subscriptions', methods=['GET'])
    @login_required
    def get_pattern_subscriptions():
        """Get user pattern subscriptions."""
        try:
            # For now, return empty subscriptions - this will be connected to Redis later
            return jsonify({
                "success": True,
                "subscriptions": []
            })
        except Exception as e:
            logger.error("Error getting pattern subscriptions: %s", str(e))
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route('/api/tickstockpl/alerts/preferences', methods=['GET'])
    @login_required
    def get_pattern_preferences():
        """Get user pattern alert preferences."""
        try:
            # Default preferences for now
            return jsonify({
                "success": True,
                "preferences": {
                    "notifications_enabled": True,
                    "email_alerts": False,
                    "sound_alerts": True,
                    "min_confidence": 0.7
                }
            })
        except Exception as e:
            logger.error("Error getting pattern preferences: %s", str(e))
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route('/api/tickstockpl/alerts/preferences', methods=['POST', 'PUT'])
    @login_required
    def save_pattern_preferences():
        """Save user pattern alert preferences."""
        try:
            preferences_data = request.get_json()
            if not preferences_data:
                return jsonify({
                    "success": False,
                    "error": "No preferences data provided"
                }), 400

            # For now, just acknowledge the save - will implement Redis storage later
            return jsonify({
                "success": True,
                "message": "Preferences saved successfully"
            })
        except Exception as e:
            logger.error("Error saving pattern preferences: %s", str(e))
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route('/api/tickstockpl/alerts/performance', methods=['GET'])
    @login_required
    def get_pattern_performance():
        """Get pattern performance data."""
        try:
            timeframe = request.args.get('timeframe', '1d')
            
            # Mock performance data for now - JavaScript expects 'performance' array
            return jsonify({
                "success": True,
                "performance": []  # Empty for now, will be populated with TickStockPL integration
            })
        except Exception as e:
            logger.error("Error getting pattern performance: %s", str(e))
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route('/api/tickstockpl/alerts/history', methods=['GET'])
    @login_required
    def get_pattern_history():
        """Get pattern alert history."""
        try:
            limit = int(request.args.get('limit', 50))
            offset = int(request.args.get('offset', 0))
            
            # Mock history data for now
            return jsonify({
                "success": True,
                "alerts": [],  # JavaScript expects 'alerts', not 'history'
                "total": 0,
                "limit": limit,
                "offset": offset
            })
        except Exception as e:
            logger.error("Error getting pattern history: %s", str(e))
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route('/api/tickstockpl/alerts/subscribe', methods=['POST'])
    @login_required
    def subscribe_to_patterns():
        """Subscribe to pattern alerts."""
        try:
            subscription_data = request.get_json()
            if not subscription_data:
                return jsonify({
                    "success": False,
                    "error": "No subscription data provided"
                }), 400

            # For now, just acknowledge the subscription - will implement Redis later
            return jsonify({
                "success": True,
                "message": "Subscribed successfully"
            })
        except Exception as e:
            logger.error("Error subscribing to patterns: %s", str(e))
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route('/api/tickstockpl/alerts/subscribe/<pattern_name>', methods=['PUT'])
    @login_required
    def update_pattern_subscription(pattern_name):
        """Update a pattern subscription (toggle active state)."""
        try:
            update_data = request.get_json()
            if not update_data:
                return jsonify({
                    "success": False,
                    "error": "No update data provided"
                }), 400

            # For now, just acknowledge the update - will implement Redis later
            return jsonify({
                "success": True,
                "message": f"Pattern {pattern_name} updated successfully"
            })
        except Exception as e:
            logger.error("Error updating pattern subscription %s: %s", pattern_name, str(e))
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route('/api/tickstockpl/alerts/subscribe/<pattern_name>', methods=['DELETE'])
    @login_required
    def unsubscribe_from_pattern(pattern_name):
        """Unsubscribe from a specific pattern."""
        try:
            # For now, just acknowledge the unsubscription - will implement Redis later
            return jsonify({
                "success": True,
                "message": f"Unsubscribed from {pattern_name}"
            })
        except Exception as e:
            logger.error("Error unsubscribing from pattern %s: %s", pattern_name, str(e))
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    # TickStockPL Integration - Backtest API Endpoints
    @app.route('/api/tickstockpl/backtest/config', methods=['GET'])
    @login_required
    def get_backtest_config():
        """Get backtest configuration options."""
        try:
            # Mock configuration data for now
            return jsonify({
                "success": True,
                "symbols": ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "NFLX"],
                "patterns": ["bullish_engulfing", "bearish_engulfing", "hammer", "doji", "morning_star", "evening_star"]
            })
        except Exception as e:
            logger.error("Error getting backtest config: %s", str(e))
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route('/api/tickstockpl/backtest/submit', methods=['POST'])
    @login_required
    def submit_backtest():
        """Submit a new backtest job."""
        try:
            backtest_data = request.get_json()
            if not backtest_data:
                return jsonify({
                    "success": False,
                    "error": "No backtest data provided"
                }), 400

            # For now, just acknowledge the submission - will implement TickStockPL integration later
            return jsonify({
                "success": True,
                "message": "Backtest submitted successfully",
                "job_id": "mock_job_123"
            })
        except Exception as e:
            logger.error("Error submitting backtest: %s", str(e))
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route('/api/tickstockpl/backtest/jobs', methods=['GET'])
    @login_required
    def get_backtest_jobs():
        """Get user's backtest jobs."""
        try:
            # Mock job data for now
            return jsonify({
                "success": True,
                "jobs": []  # Empty for now, will be populated with TickStockPL integration
            })
        except Exception as e:
            logger.error("Error getting backtest jobs: %s", str(e))
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route('/api/tickstockpl/backtest/job/<job_id>', methods=['GET'])
    @login_required
    def get_backtest_job(job_id):
        """Get specific backtest job details."""
        try:
            # Mock job data for now
            return jsonify({
                "success": True,
                "job": {
                    "job_id": job_id,
                    "status": "completed",
                    "results": None  # No results for mock data
                }
            })
        except Exception as e:
            logger.error("Error getting backtest job %s: %s", job_id, str(e))
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route('/api/tickstockpl/backtest/job/<job_id>/cancel', methods=['POST'])
    @login_required
    def cancel_backtest_job(job_id):
        """Cancel a running backtest job."""
        try:
            # For now, just acknowledge the cancellation - will implement TickStockPL integration later
            return jsonify({
                "success": True,
                "message": f"Backtest job {job_id} cancelled"
            })
        except Exception as e:
            logger.error("Error cancelling backtest job %s: %s", job_id, str(e))
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

