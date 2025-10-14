"""
TickStockPL Integration API
Provides endpoints for TickStockAppV2 to interact with TickStockPL services.

Sprint 10 Phase 1: Database Integration & Health Monitoring
- Health monitoring endpoints
- Database query endpoints for UI
- System status and connectivity checks
"""

import logging
import time

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from src.core.services.backtest_job_manager import BacktestJobConfig, BacktestJobManager
from src.core.services.health_monitor import HealthMonitor
from src.core.services.pattern_alert_manager import (
    AlertThreshold,
    NotificationType,
    PatternAlertManager,
    PatternSubscription,
    UserAlertPreferences,
)
from src.infrastructure.database.tickstock_db import TickStockDatabase

logger = logging.getLogger(__name__)

def register_tickstockpl_routes(app, extensions, cache_control, config):
    """Register TickStockPL integration API routes."""

    tickstockpl_bp = Blueprint('tickstockpl', __name__, url_prefix='/api/tickstockpl')

    # Initialize services
    health_monitor = None
    tickstock_db = None
    backtest_manager = None
    alert_manager = None

    try:
        # Get Redis client from config if available
        redis_client = config.get('redis_client')
        health_monitor = HealthMonitor(config, redis_client)
        tickstock_db = TickStockDatabase(config)

        # Initialize backtest job manager
        if redis_client and tickstock_db:
            backtest_manager = BacktestJobManager(redis_client, tickstock_db)
            # Store in app context for Redis subscriber access
            app.backtest_manager = backtest_manager

        # Initialize pattern alert manager
        if redis_client:
            alert_manager = PatternAlertManager(redis_client, tickstock_db)
            app.alert_manager = alert_manager

        logger.info("TICKSTOCKPL-API: Services initialized successfully")
    except Exception as e:
        logger.warning(f"TICKSTOCKPL-API: Service initialization partial failure: {e}")

    @tickstockpl_bp.route('/health', methods=['GET'])
    def get_health_status():
        """Get comprehensive system health status."""
        try:
            if not health_monitor:
                return jsonify({
                    'error': 'Health monitoring service not available',
                    'status': 'error'
                }), 503

            health_data = health_monitor.get_overall_health()
            return jsonify(health_data)

        except Exception as e:
            logger.error(f"TICKSTOCKPL-API: Health check failed: {e}")
            return jsonify({
                'error': 'Health check failed',
                'message': str(e),
                'status': 'error',
                'timestamp': time.time()
            }), 500

    @tickstockpl_bp.route('/dashboard', methods=['GET'])
    @login_required
    def get_dashboard_data():
        """Get dashboard data including health and quick stats."""
        try:
            if not health_monitor:
                return jsonify({
                    'error': 'Health monitoring service not available'
                }), 503

            dashboard_data = health_monitor.get_dashboard_data()
            return jsonify(dashboard_data)

        except Exception as e:
            logger.error(f"TICKSTOCKPL-API: Dashboard data request failed: {e}")
            return jsonify({
                'error': 'Dashboard data unavailable',
                'message': str(e)
            }), 500

    @tickstockpl_bp.route('/symbols', methods=['GET'])
    @login_required
    def get_symbols():
        """Get symbols for dropdown population."""
        try:
            if not tickstock_db:
                return jsonify({
                    'error': 'Database service not available'
                }), 503

            symbols = tickstock_db.get_symbols_for_dropdown()
            return jsonify({
                'symbols': symbols,
                'count': len(symbols),
                'timestamp': time.time()
            })

        except Exception as e:
            logger.error(f"TICKSTOCKPL-API: Symbols request failed: {e}")
            return jsonify({
                'error': 'Failed to retrieve symbols',
                'message': str(e)
            }), 500

    @tickstockpl_bp.route('/stats/basic', methods=['GET'])
    @login_required
    def get_basic_stats():
        """Get basic statistics for dashboard."""
        try:
            if not tickstock_db:
                return jsonify({
                    'error': 'Database service not available'
                }), 503

            stats = tickstock_db.get_basic_dashboard_stats()
            return jsonify(stats)

        except Exception as e:
            logger.error(f"TICKSTOCKPL-API: Basic stats request failed: {e}")
            return jsonify({
                'error': 'Failed to retrieve stats',
                'message': str(e)
            }), 500

    @tickstockpl_bp.route('/alerts/history', methods=['GET'])
    @login_required
    def get_user_alerts():
        """Get user's alert history."""
        try:
            if not tickstock_db:
                return jsonify({
                    'error': 'Database service not available'
                }), 503

            # Get query parameters
            limit = request.args.get('limit', 50, type=int)
            limit = min(max(limit, 1), 100)  # Clamp between 1 and 100

            user_id = str(current_user.id) if current_user and hasattr(current_user, 'id') else 'anonymous'
            alerts = tickstock_db.get_user_alert_history(user_id, limit)

            return jsonify({
                'alerts': alerts,
                'count': len(alerts),
                'user_id': user_id,
                'limit': limit,
                'timestamp': time.time()
            })

        except Exception as e:
            logger.error(f"TICKSTOCKPL-API: User alerts request failed: {e}")
            return jsonify({
                'error': 'Failed to retrieve alerts',
                'message': str(e)
            }), 500

    @tickstockpl_bp.route('/patterns/performance', methods=['GET'])
    @login_required
    def get_pattern_performance():
        """Get pattern performance statistics."""
        try:
            if not tickstock_db:
                return jsonify({
                    'error': 'Database service not available'
                }), 503

            pattern_name = request.args.get('pattern')  # Optional filter
            performance_data = tickstock_db.get_pattern_performance(pattern_name)

            return jsonify({
                'patterns': performance_data,
                'count': len(performance_data),
                'filter': pattern_name,
                'timestamp': time.time()
            })

        except Exception as e:
            logger.error(f"TICKSTOCKPL-API: Pattern performance request failed: {e}")
            return jsonify({
                'error': 'Failed to retrieve pattern performance',
                'message': str(e)
            }), 500

    # =============================================================================
    # BACKTESTING ENDPOINTS - Phase 3
    # =============================================================================

    @tickstockpl_bp.route('/backtest/config', methods=['GET'])
    @login_required
    def get_backtest_config():
        """Get available symbols and patterns for backtesting configuration."""
        try:
            if not backtest_manager:
                return jsonify({
                    'error': 'Backtest service not available'
                }), 503

            symbols = backtest_manager.get_available_symbols()
            patterns = backtest_manager.get_available_patterns()

            return jsonify({
                'symbols': symbols,
                'patterns': patterns,
                'default_config': {
                    'initial_capital': 100000.0,
                    'commission_rate': 0.001,
                    'slippage_rate': 0.0005,
                    'max_position_size': 0.1,
                    'stop_loss_pct': 0.05,
                    'take_profit_pct': 0.10
                },
                'timestamp': time.time()
            })

        except Exception as e:
            logger.error(f"TICKSTOCKPL-API: Backtest config request failed: {e}")
            return jsonify({
                'error': 'Failed to get backtest configuration',
                'message': str(e)
            }), 500

    @tickstockpl_bp.route('/backtest/submit', methods=['POST'])
    @login_required
    def submit_backtest():
        """Submit a new backtest job."""
        try:
            if not backtest_manager:
                return jsonify({
                    'error': 'Backtest service not available'
                }), 503

            # Get request data
            data = request.get_json()
            if not data:
                return jsonify({
                    'error': 'Invalid request',
                    'message': 'JSON data required'
                }), 400

            # Extract configuration
            try:
                config = BacktestJobConfig(
                    symbols=data.get('symbols', []),
                    start_date=data.get('start_date', ''),
                    end_date=data.get('end_date', ''),
                    patterns=data.get('patterns', []),
                    initial_capital=data.get('initial_capital', 100000.0),
                    commission_rate=data.get('commission_rate', 0.001),
                    slippage_rate=data.get('slippage_rate', 0.0005),
                    max_position_size=data.get('max_position_size', 0.1),
                    stop_loss_pct=data.get('stop_loss_pct', 0.05),
                    take_profit_pct=data.get('take_profit_pct', 0.10)
                )
            except TypeError as e:
                return jsonify({
                    'error': 'Invalid configuration',
                    'message': f'Configuration error: {str(e)}'
                }), 400

            # Submit job
            user_id = str(current_user.id) if current_user and hasattr(current_user, 'id') else 'anonymous'
            success, message, job_id = backtest_manager.submit_job(user_id, config)

            if success:
                return jsonify({
                    'success': True,
                    'message': message,
                    'job_id': job_id,
                    'timestamp': time.time()
                }), 201
            return jsonify({
                'success': False,
                'error': message
            }), 400

        except Exception as e:
            logger.error(f"TICKSTOCKPL-API: Backtest submission failed: {e}")
            return jsonify({
                'error': 'Failed to submit backtest',
                'message': str(e)
            }), 500

    @tickstockpl_bp.route('/backtest/jobs', methods=['GET'])
    @login_required
    def get_user_jobs():
        """Get backtest jobs for the current user."""
        try:
            if not backtest_manager:
                return jsonify({
                    'error': 'Backtest service not available'
                }), 503

            user_id = str(current_user.id) if current_user and hasattr(current_user, 'id') else 'anonymous'
            limit = request.args.get('limit', 50, type=int)
            limit = min(max(limit, 1), 100)  # Clamp between 1 and 100

            jobs = backtest_manager.get_user_jobs(user_id, limit)
            jobs_data = [job.to_dict() for job in jobs]

            return jsonify({
                'jobs': jobs_data,
                'count': len(jobs_data),
                'user_id': user_id,
                'timestamp': time.time()
            })

        except Exception as e:
            logger.error(f"TICKSTOCKPL-API: Get user jobs failed: {e}")
            return jsonify({
                'error': 'Failed to retrieve jobs',
                'message': str(e)
            }), 500

    @tickstockpl_bp.route('/backtest/job/<job_id>', methods=['GET'])
    @login_required
    def get_job_details(job_id):
        """Get details for a specific backtest job."""
        try:
            if not backtest_manager:
                return jsonify({
                    'error': 'Backtest service not available'
                }), 503

            job = backtest_manager.get_job(job_id)
            if not job:
                return jsonify({
                    'error': 'Job not found'
                }), 404

            # Check user permission
            user_id = str(current_user.id) if current_user and hasattr(current_user, 'id') else 'anonymous'
            if job.user_id != user_id:
                return jsonify({
                    'error': 'Permission denied'
                }), 403

            return jsonify({
                'job': job.to_dict(),
                'timestamp': time.time()
            })

        except Exception as e:
            logger.error(f"TICKSTOCKPL-API: Get job details failed: {e}")
            return jsonify({
                'error': 'Failed to retrieve job details',
                'message': str(e)
            }), 500

    @tickstockpl_bp.route('/backtest/job/<job_id>/cancel', methods=['POST'])
    @login_required
    def cancel_job(job_id):
        """Cancel a backtest job."""
        try:
            if not backtest_manager:
                return jsonify({
                    'error': 'Backtest service not available'
                }), 503

            user_id = str(current_user.id) if current_user and hasattr(current_user, 'id') else 'anonymous'
            success, message = backtest_manager.cancel_job(job_id, user_id)

            if success:
                return jsonify({
                    'success': True,
                    'message': message,
                    'timestamp': time.time()
                })
            return jsonify({
                'success': False,
                'error': message
            }), 400

        except Exception as e:
            logger.error(f"TICKSTOCKPL-API: Job cancellation failed: {e}")
            return jsonify({
                'error': 'Failed to cancel job',
                'message': str(e)
            }), 500

    @tickstockpl_bp.route('/backtest/stats', methods=['GET'])
    @login_required
    def get_backtest_stats():
        """Get backtest service statistics."""
        try:
            if not backtest_manager:
                return jsonify({
                    'error': 'Backtest service not available'
                }), 503

            stats = backtest_manager.get_stats()

            return jsonify({
                'stats': stats,
                'timestamp': time.time()
            })

        except Exception as e:
            logger.error(f"TICKSTOCKPL-API: Get backtest stats failed: {e}")
            return jsonify({
                'error': 'Failed to retrieve backtest statistics',
                'message': str(e)
            }), 500

    # =============================================================================
    # PATTERN ALERT ENDPOINTS - Phase 4
    # =============================================================================

    @tickstockpl_bp.route('/alerts/preferences', methods=['GET'])
    @login_required
    def get_alert_preferences():
        """Get user's alert preferences."""
        try:
            if not alert_manager:
                return jsonify({
                    'error': 'Alert service not available'
                }), 503

            user_id = str(current_user.id) if current_user and hasattr(current_user, 'id') else 'anonymous'
            preferences = alert_manager.get_user_preferences(user_id)

            return jsonify({
                'preferences': preferences.to_dict(),
                'timestamp': time.time()
            })

        except Exception as e:
            logger.error(f"TICKSTOCKPL-API: Get alert preferences failed: {e}")
            return jsonify({
                'error': 'Failed to get alert preferences',
                'message': str(e)
            }), 500

    @tickstockpl_bp.route('/alerts/preferences', methods=['POST'])
    @login_required
    def update_alert_preferences():
        """Update user's alert preferences."""
        try:
            if not alert_manager:
                return jsonify({
                    'error': 'Alert service not available'
                }), 503

            data = request.get_json()
            if not data:
                return jsonify({
                    'error': 'Invalid request',
                    'message': 'JSON data required'
                }), 400

            user_id = str(current_user.id) if current_user and hasattr(current_user, 'id') else 'anonymous'

            # Create preferences object
            try:
                preferences = UserAlertPreferences.from_dict({
                    **data,
                    'user_id': user_id
                })
            except Exception as e:
                return jsonify({
                    'error': 'Invalid preferences data',
                    'message': str(e)
                }), 400

            success = alert_manager.update_user_preferences(user_id, preferences)

            if success:
                return jsonify({
                    'success': True,
                    'message': 'Alert preferences updated successfully',
                    'timestamp': time.time()
                })
            return jsonify({
                'success': False,
                'error': 'Failed to update preferences'
            }), 500

        except Exception as e:
            logger.error(f"TICKSTOCKPL-API: Update alert preferences failed: {e}")
            return jsonify({
                'error': 'Failed to update alert preferences',
                'message': str(e)
            }), 500

    @tickstockpl_bp.route('/alerts/subscriptions', methods=['GET'])
    @login_required
    def get_alert_subscriptions():
        """Get user's pattern subscriptions."""
        try:
            if not alert_manager:
                return jsonify({
                    'error': 'Alert service not available'
                }), 503

            user_id = str(current_user.id) if current_user and hasattr(current_user, 'id') else 'anonymous'
            subscriptions = alert_manager.get_user_subscriptions(user_id)

            subscriptions_dict = {pattern: sub.to_dict() for pattern, sub in subscriptions.items()}

            return jsonify({
                'subscriptions': subscriptions_dict,
                'available_patterns': alert_manager.get_available_patterns(),
                'timestamp': time.time()
            })

        except Exception as e:
            logger.error(f"TICKSTOCKPL-API: Get alert subscriptions failed: {e}")
            return jsonify({
                'error': 'Failed to get alert subscriptions',
                'message': str(e)
            }), 500

    @tickstockpl_bp.route('/alerts/subscriptions', methods=['POST'])
    @login_required
    def update_alert_subscriptions():
        """Update user's pattern subscriptions."""
        try:
            if not alert_manager:
                return jsonify({
                    'error': 'Alert service not available'
                }), 503

            data = request.get_json()
            if not data or 'subscriptions' not in data:
                return jsonify({
                    'error': 'Invalid request',
                    'message': 'Subscriptions data required'
                }), 400

            user_id = str(current_user.id) if current_user and hasattr(current_user, 'id') else 'anonymous'

            # Parse subscriptions
            try:
                subscriptions = {}
                for pattern, sub_data in data['subscriptions'].items():
                    subscriptions[pattern] = PatternSubscription.from_dict(sub_data)
            except Exception as e:
                return jsonify({
                    'error': 'Invalid subscription data',
                    'message': str(e)
                }), 400

            success = alert_manager.update_user_subscriptions(user_id, subscriptions)

            if success:
                return jsonify({
                    'success': True,
                    'message': 'Alert subscriptions updated successfully',
                    'timestamp': time.time()
                })
            return jsonify({
                'success': False,
                'error': 'Failed to update subscriptions'
            }), 500

        except Exception as e:
            logger.error(f"TICKSTOCKPL-API: Update alert subscriptions failed: {e}")
            return jsonify({
                'error': 'Failed to update alert subscriptions',
                'message': str(e)
            }), 500

    @tickstockpl_bp.route('/alerts/subscribe/<pattern>', methods=['POST'])
    @login_required
    def subscribe_to_pattern(pattern):
        """Subscribe to a specific pattern."""
        try:
            if not alert_manager:
                return jsonify({
                    'error': 'Alert service not available'
                }), 503

            data = request.get_json() or {}
            user_id = str(current_user.id) if current_user and hasattr(current_user, 'id') else 'anonymous'

            # Parse notification types
            notification_types = set()
            for nt_value in data.get('notification_types', ['in_app']):
                try:
                    notification_types.add(NotificationType(nt_value))
                except ValueError:
                    logger.warning(f"Invalid notification type: {nt_value}")

            if not notification_types:
                notification_types = {NotificationType.IN_APP}

            # Parse symbols filter
            symbols = None
            if data.get('symbols'):
                symbols = set(data['symbols'])

            success = alert_manager.subscribe_to_pattern(
                user_id=user_id,
                pattern=pattern,
                confidence_threshold=data.get('confidence_threshold', AlertThreshold.MEDIUM.value),
                notification_types=notification_types,
                symbols=symbols
            )

            if success:
                return jsonify({
                    'success': True,
                    'message': f'Subscribed to {pattern} pattern',
                    'timestamp': time.time()
                })
            return jsonify({
                'success': False,
                'error': 'Failed to subscribe to pattern'
            }), 500

        except Exception as e:
            logger.error(f"TICKSTOCKPL-API: Pattern subscription failed: {e}")
            return jsonify({
                'error': 'Failed to subscribe to pattern',
                'message': str(e)
            }), 500

    @tickstockpl_bp.route('/alerts/unsubscribe/<pattern>', methods=['POST'])
    @login_required
    def unsubscribe_from_pattern(pattern):
        """Unsubscribe from a specific pattern."""
        try:
            if not alert_manager:
                return jsonify({
                    'error': 'Alert service not available'
                }), 503

            user_id = str(current_user.id) if current_user and hasattr(current_user, 'id') else 'anonymous'

            success = alert_manager.unsubscribe_from_pattern(user_id, pattern)

            if success:
                return jsonify({
                    'success': True,
                    'message': f'Unsubscribed from {pattern} pattern',
                    'timestamp': time.time()
                })
            return jsonify({
                'success': False,
                'error': 'Failed to unsubscribe from pattern'
            }), 500

        except Exception as e:
            logger.error(f"TICKSTOCKPL-API: Pattern unsubscription failed: {e}")
            return jsonify({
                'error': 'Failed to unsubscribe from pattern',
                'message': str(e)
            }), 500

    @tickstockpl_bp.route('/alerts/history', methods=['GET'])
    @login_required
    def get_alert_history():
        """Get user's alert history."""
        try:
            if not alert_manager:
                return jsonify({
                    'error': 'Alert service not available'
                }), 503

            user_id = str(current_user.id) if current_user and hasattr(current_user, 'id') else 'anonymous'
            limit = request.args.get('limit', 50, type=int)
            limit = min(max(limit, 1), 200)  # Clamp between 1 and 200

            history = alert_manager.get_user_alert_history(user_id, limit)

            return jsonify({
                'alerts': history,
                'count': len(history),
                'limit': limit,
                'timestamp': time.time()
            })

        except Exception as e:
            logger.error(f"TICKSTOCKPL-API: Get alert history failed: {e}")
            return jsonify({
                'error': 'Failed to get alert history',
                'message': str(e)
            }), 500

    @tickstockpl_bp.route('/alerts/patterns/performance', methods=['GET'])
    @login_required
    def get_pattern_alert_performance():
        """Get pattern performance data for alerts."""
        try:
            if not alert_manager:
                return jsonify({
                    'error': 'Alert service not available'
                }), 503

            pattern = request.args.get('pattern')
            performance_data = alert_manager.get_pattern_performance(pattern)

            return jsonify({
                'patterns': performance_data,
                'count': len(performance_data),
                'filter': pattern,
                'available_patterns': alert_manager.get_available_patterns(),
                'timestamp': time.time()
            })

        except Exception as e:
            logger.error(f"TICKSTOCKPL-API: Get pattern performance failed: {e}")
            return jsonify({
                'error': 'Failed to get pattern performance',
                'message': str(e)
            }), 500

    @tickstockpl_bp.route('/alerts/stats', methods=['GET'])
    @login_required
    def get_alert_stats():
        """Get alert service statistics."""
        try:
            if not alert_manager:
                return jsonify({
                    'error': 'Alert service not available'
                }), 503

            stats = alert_manager.get_stats()

            return jsonify({
                'stats': stats,
                'timestamp': time.time()
            })

        except Exception as e:
            logger.error(f"TICKSTOCKPL-API: Get alert stats failed: {e}")
            return jsonify({
                'error': 'Failed to get alert statistics',
                'message': str(e)
            }), 500

    @tickstockpl_bp.route('/connectivity/test', methods=['POST'])
    @login_required
    def test_connectivity():
        """Test connectivity to TickStockPL services."""
        try:
            if not health_monitor:
                return jsonify({
                    'error': 'Health monitoring service not available'
                }), 503

            # Get detailed connectivity status
            health_data = health_monitor.get_overall_health()

            connectivity_result = {
                'database': health_data['components']['database'],
                'redis': health_data['components']['redis'],
                'tickstockpl': health_data['components']['tickstockpl_connectivity'],
                'overall_status': health_data['overall_status'],
                'test_timestamp': time.time()
            }

            return jsonify(connectivity_result)

        except Exception as e:
            logger.error(f"TICKSTOCKPL-API: Connectivity test failed: {e}")
            return jsonify({
                'error': 'Connectivity test failed',
                'message': str(e)
            }), 500

    # Error handlers for this blueprint
    @tickstockpl_bp.errorhandler(404)
    def api_not_found(error):
        return jsonify({
            'error': 'API endpoint not found',
            'message': 'The requested TickStockPL API endpoint does not exist'
        }), 404

    @tickstockpl_bp.errorhandler(500)
    def api_internal_error(error):
        logger.error(f"TICKSTOCKPL-API: Internal error: {error}")
        return jsonify({
            'error': 'Internal API error',
            'message': 'An unexpected error occurred in the TickStockPL API'
        }), 500

    # Register blueprint
    app.register_blueprint(tickstockpl_bp)
    logger.info("TICKSTOCKPL-API: Routes registered successfully")

    # Store services in app context for cleanup
    app.tickstockpl_health_monitor = health_monitor
    app.tickstockpl_database = tickstock_db

    return tickstockpl_bp
