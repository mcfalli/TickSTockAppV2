"""
Admin Monitoring Dashboard Routes
Real-time monitoring of TickStockPL system health via Redis pub/sub
Sprint 31 Implementation
"""

import json
import redis
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from src.core.services.config_manager import get_config
from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
# Note: CSRF exemption handled differently in newer Flask-WTF
from src.utils.auth_decorators import admin_required

logger = logging.getLogger(__name__)

# Initialize Redis client for monitoring
def get_monitoring_redis():
    """Get Redis client for monitoring channel"""
    config = get_config()
    return redis.Redis(
        host=config.get('REDIS_HOST', 'localhost'),
        port=config.get('REDIS_PORT', 6379),
        db=config.get('REDIS_DB', 0),
        decode_responses=True
    )

def register_admin_monitoring_routes(app):
    """Register admin monitoring dashboard routes with the Flask app"""

    redis_client = get_monitoring_redis()

    # Store for recent metrics and alerts (in-memory for simplicity)
    monitoring_data = {
        'latest_metrics': {},
        'active_alerts': [],
        'alert_history': [],
        'health_status': {},
        'performance_history': []
    }

    # Get CSRF protection object to exempt internal endpoint
    csrf = app.extensions.get('csrf')

    @app.route('/admin/monitoring')
    @login_required
    @admin_required
    def admin_monitoring_dashboard():
        """Main monitoring dashboard for TickStockPL health"""
        try:
            # Test Redis connection
            try:
                redis_client.ping()
                redis_connected = True
            except redis.ConnectionError:
                redis_connected = False

            # Get latest stored metrics
            latest_metrics = monitoring_data.get('latest_metrics', {})
            active_alerts = monitoring_data.get('active_alerts', [])
            health_status = monitoring_data.get('health_status', {})

            return render_template('admin/monitoring_dashboard.html',
                                 redis_connected=redis_connected,
                                 latest_metrics=latest_metrics,
                                 active_alerts=active_alerts,
                                 health_status=health_status,
                                 monitoring_channel='tickstock:monitoring')
        except Exception as e:
            logger.error(f"Error loading monitoring dashboard: {str(e)}")
            flash(f'Error loading dashboard: {str(e)}', 'danger')
            return render_template('admin/monitoring_dashboard.html',
                                 redis_connected=False,
                                 latest_metrics={},
                                 active_alerts=[],
                                 health_status={})

    @app.route('/api/admin/monitoring/health-check', methods=['POST'])
    @login_required
    @admin_required
    def force_health_check():
        """Force immediate health check on TickStockPL"""
        try:
            # Publish health check request to TickStockPL
            request_data = {
                'action': 'FORCE_HEALTH_CHECK',
                'requested_by': current_user.username if current_user.is_authenticated else 'admin',
                'timestamp': datetime.now().isoformat()
            }

            redis_client.publish('tickstock:monitoring:control', json.dumps(request_data))

            return jsonify({
                'success': True,
                'message': 'Health check requested'
            })
        except Exception as e:
            logger.error(f"Error requesting health check: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/admin/monitoring/alerts/<alert_id>/resolve', methods=['POST'])
    @login_required
    @admin_required
    def resolve_alert(alert_id):
        """Resolve a specific alert"""
        try:
            data = request.json or {}
            notes = data.get('notes', '')

            # Update alert status
            for alert in monitoring_data['active_alerts']:
                if alert.get('id') == alert_id:
                    alert['resolved'] = True
                    alert['resolved_by'] = current_user.username if current_user.is_authenticated else 'admin'
                    alert['resolved_at'] = datetime.now().isoformat()
                    alert['resolution_notes'] = notes

                    # Move to history
                    monitoring_data['alert_history'].append(alert)
                    monitoring_data['active_alerts'].remove(alert)

                    # Publish resolution event
                    resolution_event = {
                        'action': 'ALERT_RESOLVED',
                        'alert_id': alert_id,
                        'resolved_by': alert['resolved_by'],
                        'notes': notes,
                        'timestamp': datetime.now().isoformat()
                    }
                    redis_client.publish('tickstock:monitoring:control', json.dumps(resolution_event))

                    return jsonify({
                        'success': True,
                        'message': f'Alert {alert_id} resolved'
                    })

            return jsonify({
                'success': False,
                'message': 'Alert not found'
            }), 404

        except Exception as e:
            logger.error(f"Error resolving alert: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/admin/monitoring/alerts/<alert_id>/acknowledge', methods=['POST'])
    @login_required
    @admin_required
    def acknowledge_alert(alert_id):
        """Acknowledge an alert"""
        try:
            # Find and update alert
            for alert in monitoring_data['active_alerts']:
                if alert.get('id') == alert_id:
                    alert['acknowledged'] = True
                    alert['acknowledged_by'] = current_user.username if current_user.is_authenticated else 'admin'
                    alert['acknowledged_at'] = datetime.now().isoformat()

                    return jsonify({
                        'success': True,
                        'message': f'Alert {alert_id} acknowledged'
                    })

            return jsonify({
                'success': False,
                'message': 'Alert not found'
            }), 404

        except Exception as e:
            logger.error(f"Error acknowledging alert: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/admin/monitoring/metrics/historical')
    @login_required
    @admin_required
    def get_historical_metrics():
        """Get historical metrics data"""
        try:
            hours = int(request.args.get('hours', 24))

            # For now, return stored performance history
            # In production, this would query a time-series database
            return jsonify({
                'success': True,
                'data': monitoring_data.get('performance_history', [])[-100:]  # Last 100 entries
            })

        except Exception as e:
            logger.error(f"Error fetching historical metrics: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/admin/monitoring/alerts/history')
    @login_required
    @admin_required
    def get_alert_history():
        """Get alert history"""
        try:
            hours = int(request.args.get('hours', 24))

            # Filter alerts within time range
            cutoff = datetime.now() - timedelta(hours=hours)
            recent_alerts = []

            for alert in monitoring_data['alert_history']:
                alert_time = datetime.fromisoformat(alert.get('timestamp', datetime.now().isoformat()))
                if alert_time > cutoff:
                    recent_alerts.append(alert)

            return jsonify({
                'success': True,
                'alerts': recent_alerts
            })

        except Exception as e:
            logger.error(f"Error fetching alert history: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/admin/monitoring/status')
    @login_required
    def get_monitoring_status():
        """Get current monitoring status"""
        try:
            # Test Redis connection
            try:
                redis_client.ping()
                redis_status = 'connected'
            except:
                redis_status = 'disconnected'

            return jsonify({
                'success': True,
                'redis': redis_status,
                'latest_update': monitoring_data.get('latest_metrics', {}).get('timestamp'),
                'active_alerts': len(monitoring_data.get('active_alerts', [])),
                'health_score': monitoring_data.get('health_status', {}).get('overall_score', 0),
                'latest_metrics': monitoring_data.get('latest_metrics', {}),
                'health_status': monitoring_data.get('health_status', {})
            })

        except Exception as e:
            logger.error(f"Error fetching monitoring status: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/admin/monitoring/components/enable', methods=['POST'])
    @login_required
    @admin_required
    def enable_component():
        """Re-enable a disabled component"""
        try:
            data = request.json or {}
            component_type = data.get('type')
            component_name = data.get('name')

            # Publish enable request to TickStockPL
            enable_request = {
                'action': 'ENABLE_COMPONENT',
                'type': component_type,
                'name': component_name,
                'requested_by': current_user.username if current_user.is_authenticated else 'admin',
                'timestamp': datetime.now().isoformat()
            }

            redis_client.publish('tickstock:monitoring:control', json.dumps(enable_request))

            return jsonify({
                'success': True,
                'message': f'Component {component_name} enable requested'
            })

        except Exception as e:
            logger.error(f"Error enabling component: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/admin/monitoring/actions/<action>', methods=['POST'])
    @login_required
    @admin_required
    def trigger_action(action):
        """Trigger manual monitoring action"""
        try:
            valid_actions = ['clear_cache', 'force_gc', 'restart_workers', 'reload_patterns']

            if action not in valid_actions:
                return jsonify({
                    'success': False,
                    'message': f'Invalid action: {action}'
                }), 400

            # Publish action request to TickStockPL
            action_request = {
                'action': action.upper(),
                'requested_by': current_user.username if current_user.is_authenticated else 'admin',
                'timestamp': datetime.now().isoformat()
            }

            redis_client.publish('tickstock:monitoring:control', json.dumps(action_request))

            return jsonify({
                'success': True,
                'message': f'Action {action} triggered'
            })

        except Exception as e:
            logger.error(f"Error triggering action: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    # Store monitoring events received from Redis (called by background subscriber)
    @app.route('/api/admin/monitoring/store-event', methods=['POST'])
    @csrf.exempt  # Exempt from CSRF since it's an internal endpoint
    def store_monitoring_event():
        """Internal endpoint to store monitoring events from Redis subscriber"""
        try:
            event = request.json

            if not event:
                return jsonify({'success': False, 'message': 'No event data'}), 400

            event_type = event.get('event_type')

            if event_type == 'METRIC_UPDATE':
                monitoring_data['latest_metrics'] = event
                # Add to history
                monitoring_data['performance_history'].append({
                    'timestamp': event.get('timestamp'),
                    'metrics': event.get('metrics'),
                    'health_score': event.get('health_score')
                })
                # Keep only last 1000 entries
                if len(monitoring_data['performance_history']) > 1000:
                    monitoring_data['performance_history'] = monitoring_data['performance_history'][-1000:]

            elif event_type == 'ALERT_TRIGGERED':
                alert = event.get('alert', {})
                alert['timestamp'] = event.get('timestamp')
                monitoring_data['active_alerts'].append(alert)

            elif event_type == 'ALERT_RESOLVED':
                alert_id = event.get('alert_id')
                monitoring_data['active_alerts'] = [
                    a for a in monitoring_data['active_alerts']
                    if a.get('id') != alert_id
                ]

            elif event_type == 'HEALTH_CHECK':
                monitoring_data['health_status'] = event.get('health', {})

            elif event_type == 'SYSTEM_STATUS':
                monitoring_data['system_status'] = event.get('status')

            return jsonify({'success': True})

        except Exception as e:
            logger.error(f"Error storing monitoring event: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    return app