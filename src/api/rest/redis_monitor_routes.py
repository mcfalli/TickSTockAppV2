"""
Redis Monitor API Routes
Sprint 43: Debug Redis communication

Provides API endpoints for accessing Redis message monitoring data.
"""

import logging
from flask import Blueprint, jsonify, request, render_template
from flask_login import login_required

logger = logging.getLogger(__name__)

# Create blueprint
redis_monitor_bp = Blueprint('redis_monitor', __name__, url_prefix='/redis-monitor')


@redis_monitor_bp.route('/')
@login_required
def monitor_dashboard():
    """Render Redis monitoring dashboard."""
    return render_template('redis_monitor.html')


@redis_monitor_bp.route('/api/messages', methods=['GET'])
@login_required
def get_messages():
    """
    Get recent Redis messages.

    Query Parameters:
        limit: Number of messages to return (default: 50, max: 500)
        channel: Filter by channel name (partial match)
        type: Filter by event type

    Returns:
        JSON with messages list
    """
    try:
        from src.app import app

        # Get Redis subscriber from app context
        subscriber = getattr(app, 'redis_subscriber', None)
        if not subscriber or not hasattr(subscriber, 'redis_monitor'):
            return jsonify({
                'error': 'Redis monitor not available',
                'messages': []
            }), 503

        # Get query parameters
        limit = min(int(request.args.get('limit', 50)), 500)
        channel_filter = request.args.get('channel')
        type_filter = request.args.get('type')

        # Get messages from monitor
        messages = subscriber.redis_monitor.get_recent_messages(
            limit=limit,
            channel_filter=channel_filter,
            type_filter=type_filter
        )

        return jsonify({
            'messages': messages,
            'count': len(messages),
            'filters': {
                'channel': channel_filter,
                'type': type_filter,
                'limit': limit
            }
        })

    except Exception as e:
        logger.error(f"Error getting Redis messages: {e}")
        return jsonify({'error': str(e)}), 500


@redis_monitor_bp.route('/api/stats', methods=['GET'])
@login_required
def get_stats():
    """
    Get Redis monitoring statistics.

    Returns:
        JSON with monitoring stats
    """
    try:
        from src.app import app

        subscriber = getattr(app, 'redis_subscriber', None)
        if not subscriber or not hasattr(subscriber, 'redis_monitor'):
            return jsonify({'error': 'Redis monitor not available'}), 503

        stats = subscriber.redis_monitor.get_stats()

        return jsonify(stats)

    except Exception as e:
        logger.error(f"Error getting Redis stats: {e}")
        return jsonify({'error': str(e)}), 500


@redis_monitor_bp.route('/api/field-names', methods=['GET'])
@login_required
def get_field_names():
    """
    Get field name analysis report.

    Returns:
        JSON with field naming consistency report
    """
    try:
        from src.app import app

        subscriber = getattr(app, 'redis_subscriber', None)
        if not subscriber or not hasattr(subscriber, 'redis_monitor'):
            return jsonify({'error': 'Redis monitor not available'}), 503

        report = subscriber.redis_monitor.get_field_name_report()

        return jsonify(report)

    except Exception as e:
        logger.error(f"Error getting field name report: {e}")
        return jsonify({'error': str(e)}), 500


@redis_monitor_bp.route('/api/clear', methods=['POST'])
@login_required
def clear_monitor():
    """
    Clear all captured messages and reset stats.

    Returns:
        JSON with success status
    """
    try:
        from src.app import app

        subscriber = getattr(app, 'redis_subscriber', None)
        if not subscriber or not hasattr(subscriber, 'redis_monitor'):
            return jsonify({'error': 'Redis monitor not available'}), 503

        subscriber.redis_monitor.clear()

        return jsonify({
            'success': True,
            'message': 'Redis monitor cleared'
        })

    except Exception as e:
        logger.error(f"Error clearing Redis monitor: {e}")
        return jsonify({'error': str(e)}), 500
