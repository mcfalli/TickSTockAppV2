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

from src.core.services.user_filters_service import UserFiltersService
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

    # User Filters Endpoints  
    @app.route('/api/user-filters', methods=['GET'])
    @login_required
    def get_user_filters():
        """Get user filter settings."""
        try:
            user_filters_service = UserFiltersService()
            filters = user_filters_service.get_filters(current_user.id)
            
            return jsonify({
                "success": True,
                "filter_data": filters,
                "user_id": current_user.id
            })
        except Exception as e:
            logger.error("Error getting user filters: %s", str(e))
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route('/api/user-filters', methods=['POST'])
    @login_required
    def save_user_filters():
        """Save user filter settings."""
        try:
            filter_data = request.get_json()
            if not filter_data:
                return jsonify({
                    "success": False,
                    "error": "No filter data provided"
                }), 400

            user_filters_service = UserFiltersService()
            success = user_filters_service.save_filters(current_user.id, filter_data)
            
            if success:
                return jsonify({
                    "success": True,
                    "message": "Filters saved successfully", 
                    "user_id": current_user.id,
                    "cache_invalidated": True
                })
            else:
                return jsonify({
                    "success": False,
                    "error": "Failed to save filters"
                }), 500
                
        except Exception as e:
            logger.error("Error saving user filters: %s", str(e))
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    # Universe Management Endpoints
    @app.route('/api/user/universe-selections', methods=['GET'])
    @login_required
    def get_user_universe_selections():
        """Get current user's universe selections."""
        try:
            # Get user's universe selections from settings
            settings = user_settings_service.get_user_settings(current_user.id)
            universe_selections = settings.get('universe_selections', {})
            
            return jsonify({
                "success": True,
                "selections": universe_selections,
                "user_id": current_user.id
            })
        except Exception as e:
            logger.error("Error getting universe selections: %s", str(e))
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route('/api/universes/select', methods=['POST']) 
    @login_required
    def select_universe():
        """Update user's universe selections."""
        try:
            data = request.get_json()
            if not data or 'tracker' not in data or 'universes' not in data:
                return jsonify({
                    "success": False,
                    "error": "Missing required fields: tracker, universes"
                }), 400

            tracker = data['tracker']
            universes = data['universes']
            
            # Get current settings
            current_settings = user_settings_service.get_user_settings(current_user.id)
            
            # Update universe selections
            if 'universe_selections' not in current_settings:
                current_settings['universe_selections'] = {}
            current_settings['universe_selections'][tracker] = universes
            
            # Save updated settings
            success = user_settings_service.save_user_settings(
                current_user.id, 
                current_settings
            )
            
            if success:
                return jsonify({
                    "status": "success",
                    "tracker": tracker,
                    "universes": universes,
                    "cache_invalidated": True,
                    "user_id": current_user.id
                })
            else:
                return jsonify({
                    "status": "error",
                    "error": "Failed to save universe selection"
                }), 500
                
        except Exception as e:
            logger.error("Error selecting universe: %s", str(e))
            return jsonify({
                "status": "error",
                "error": str(e)
            }), 500