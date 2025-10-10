"""
Streaming Dashboard Routes and API Endpoints
Sprint 33 Phase 5: Real-time streaming integration

Provides routes for streaming dashboard and API endpoints for historical data.
"""

import logging
from datetime import datetime, timedelta
from flask import Blueprint, render_template, jsonify, request, current_app
from flask_login import login_required, current_user
from typing import Dict, Any, List, Optional
import json

logger = logging.getLogger(__name__)

# Create blueprint
streaming_bp = Blueprint('streaming', __name__, url_prefix='/streaming')

# @streaming_bp.route('/')
# @login_required
# def streaming_dashboard():
#     """
#     DISABLED: This route conflicts with sidebar navigation (SPA model).
#     Live Streaming is now accessed via sidebar JavaScript, not a Flask route.
#
#     The streaming dashboard is rendered by StreamingDashboardService (JavaScript)
#     when user clicks "Live Streaming" in the sidebar navigation.
#     See: web/static/js/services/streaming-dashboard.js
#          web/static/js/components/sidebar-navigation-controller.js (lines 53-60)
#     """
#     pass

@streaming_bp.route('/api/status')
@login_required
def streaming_status():
    """
    Get current streaming session status.

    Returns:
        JSON with session info, health metrics, and connection status
    """
    try:
        # Get Redis subscriber instance from current Flask app
        redis_subscriber = getattr(current_app, 'redis_subscriber', None)
        if not redis_subscriber:
            return jsonify({
                'status': 'offline',
                'message': 'Streaming service not available'
            })

        # Get current streaming session info
        session_info = getattr(redis_subscriber, 'current_streaming_session', None)
        health_info = getattr(redis_subscriber, 'latest_streaming_health', {})

        response = {
            'status': 'online' if session_info else 'idle',
            'session': session_info,
            'health': health_info,
            'subscriber_stats': redis_subscriber.get_stats() if hasattr(redis_subscriber, 'get_stats') else {}
        }

        return jsonify(response)

    except Exception as e:
        logger.error(f"STREAMING-API-ERROR: Status endpoint failed: {e}")
        return jsonify({'error': 'Failed to get streaming status'}), 500

@streaming_bp.route('/api/patterns/<symbol>')
@login_required
def get_streaming_patterns(symbol: str):
    """
    Get recent streaming patterns for a specific symbol.

    Args:
        symbol: Stock symbol to query

    Query Parameters:
        hours: Number of hours to look back (default: 1)

    Returns:
        JSON array of pattern detections from intraday_patterns table
    """
    try:
        hours = request.args.get('hours', 1, type=int)
        hours = min(24, max(1, hours))  # Clamp between 1 and 24 hours

        from src.infrastructure.database.connection import get_db_connection

        query = """
            SELECT
                pattern_type,
                symbol,
                detected_at as timestamp,
                confidence,
                parameters,
                timeframe
            FROM intraday_patterns
            WHERE symbol = %s
            AND detected_at > NOW() - INTERVAL '%s hours'
            ORDER BY detected_at DESC
            LIMIT 100
        """

        with get_db_connection(read_only=True) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (symbol, hours))
                columns = [desc[0] for desc in cursor.description]
                results = []

                for row in cursor.fetchall():
                    pattern = dict(zip(columns, row))
                    # Convert datetime to ISO format
                    if pattern.get('timestamp'):
                        pattern['timestamp'] = pattern['timestamp'].isoformat()
                    # Parse parameters JSON if string
                    if pattern.get('parameters') and isinstance(pattern['parameters'], str):
                        try:
                            pattern['parameters'] = json.loads(pattern['parameters'])
                        except:
                            pass
                    results.append(pattern)

        logger.info(f"STREAMING-API: Found {len(results)} patterns for {symbol} in last {hours} hours")
        return jsonify(results)

    except Exception as e:
        logger.error(f"STREAMING-API-ERROR: Pattern query failed for {symbol}: {e}")
        return jsonify({'error': f'Failed to get patterns for {symbol}'}), 500

@streaming_bp.route('/api/indicators/<symbol>')
@login_required
def get_streaming_indicators(symbol: str):
    """
    Get recent streaming indicator calculations for a specific symbol.

    Args:
        symbol: Stock symbol to query

    Query Parameters:
        hours: Number of hours to look back (default: 1)
        indicator: Specific indicator type filter (optional)

    Returns:
        JSON array of indicator calculations from intraday_indicators table
    """
    try:
        hours = request.args.get('hours', 1, type=int)
        hours = min(24, max(1, hours))
        indicator_type = request.args.get('indicator', None)

        from src.infrastructure.database.connection import get_db_connection

        base_query = """
            SELECT
                indicator_type,
                symbol,
                calculated_at as timestamp,
                value,
                parameters,
                timeframe
            FROM intraday_indicators
            WHERE symbol = %s
            AND calculated_at > NOW() - INTERVAL '%s hours'
        """

        if indicator_type:
            base_query += " AND indicator_type = %s"
            params = (symbol, hours, indicator_type)
        else:
            params = (symbol, hours)

        base_query += " ORDER BY calculated_at DESC LIMIT 200"

        with get_db_connection(read_only=True) as conn:
            with conn.cursor() as cursor:
                cursor.execute(base_query, params)
                columns = [desc[0] for desc in cursor.description]
                results = []

                for row in cursor.fetchall():
                    indicator = dict(zip(columns, row))
                    # Convert datetime to ISO format
                    if indicator.get('timestamp'):
                        indicator['timestamp'] = indicator['timestamp'].isoformat()
                    # Parse parameters JSON if string
                    if indicator.get('parameters') and isinstance(indicator['parameters'], str):
                        try:
                            indicator['parameters'] = json.loads(indicator['parameters'])
                        except:
                            pass
                    results.append(indicator)

        logger.info(f"STREAMING-API: Found {len(results)} indicators for {symbol} in last {hours} hours")
        return jsonify(results)

    except Exception as e:
        logger.error(f"STREAMING-API-ERROR: Indicator query failed for {symbol}: {e}")
        return jsonify({'error': f'Failed to get indicators for {symbol}'}), 500

@streaming_bp.route('/api/alerts')
@login_required
def get_indicator_alerts():
    """
    Get recent indicator alerts across all symbols.

    Query Parameters:
        hours: Number of hours to look back (default: 1)
        alert_type: Specific alert type filter (optional)
        limit: Maximum results (default: 100)

    Returns:
        JSON array of indicator alerts
    """
    try:
        hours = request.args.get('hours', 1, type=int)
        hours = min(24, max(1, hours))
        alert_type = request.args.get('alert_type', None)
        limit = request.args.get('limit', 100, type=int)
        limit = min(500, max(10, limit))

        from src.infrastructure.database.connection import get_db_connection

        # Query app_indicator_alerts table if it exists, otherwise use indicators
        query = """
            SELECT
                symbol,
                indicator_type as alert_type,
                calculated_at as timestamp,
                value,
                parameters as alert_data,
                timeframe
            FROM intraday_indicators
            WHERE calculated_at > NOW() - INTERVAL '%s hours'
            AND (
                (indicator_type = 'RSI' AND (value > 70 OR value < 30)) OR
                (indicator_type = 'MACD' AND parameters IS NOT NULL)
            )
        """

        params = [hours]
        if alert_type:
            query += " AND indicator_type = %s"
            params.append(alert_type)

        query += f" ORDER BY calculated_at DESC LIMIT {limit}"

        with get_db_connection(read_only=True) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                columns = [desc[0] for desc in cursor.description]
                results = []

                for row in cursor.fetchall():
                    alert = dict(zip(columns, row))
                    # Convert datetime to ISO format
                    if alert.get('timestamp'):
                        alert['timestamp'] = alert['timestamp'].isoformat()

                    # Determine alert type based on indicator values
                    if alert['alert_type'] == 'RSI':
                        if alert['value'] > 70:
                            alert['alert_type'] = 'RSI_OVERBOUGHT'
                        elif alert['value'] < 30:
                            alert['alert_type'] = 'RSI_OVERSOLD'

                    results.append(alert)

        logger.info(f"STREAMING-API: Found {len(results)} alerts in last {hours} hours")
        return jsonify(results)

    except Exception as e:
        logger.error(f"STREAMING-API-ERROR: Alert query failed: {e}")
        return jsonify({'error': 'Failed to get alerts'}), 500

@streaming_bp.route('/api/summary')
@login_required
def get_streaming_summary():
    """
    Get summary statistics for current streaming session.

    Returns:
        JSON with pattern counts, top symbols, alert distribution
    """
    try:
        from src.infrastructure.database.connection import get_db_connection

        summary = {}

        with get_db_connection(read_only=True) as conn:
            with conn.cursor() as cursor:
                # Pattern counts by type (last hour)
                cursor.execute("""
                    SELECT pattern_type, COUNT(*) as count
                    FROM intraday_patterns
                    WHERE detected_at > NOW() - INTERVAL '1 hour'
                    GROUP BY pattern_type
                    ORDER BY count DESC
                """)
                summary['pattern_distribution'] = dict(cursor.fetchall())

                # Top active symbols
                cursor.execute("""
                    SELECT symbol, COUNT(*) as event_count
                    FROM (
                        SELECT symbol FROM intraday_patterns
                        WHERE detected_at > NOW() - INTERVAL '1 hour'
                        UNION ALL
                        SELECT symbol FROM intraday_indicators
                        WHERE calculated_at > NOW() - INTERVAL '1 hour'
                    ) combined
                    GROUP BY symbol
                    ORDER BY event_count DESC
                    LIMIT 10
                """)
                summary['top_symbols'] = [
                    {'symbol': row[0], 'events': row[1]}
                    for row in cursor.fetchall()
                ]

                # Total counts
                cursor.execute("""
                    SELECT
                        (SELECT COUNT(*) FROM intraday_patterns
                         WHERE detected_at > NOW() - INTERVAL '1 hour') as patterns,
                        (SELECT COUNT(*) FROM intraday_indicators
                         WHERE calculated_at > NOW() - INTERVAL '1 hour') as indicators
                """)
                counts = cursor.fetchone()
                summary['total_patterns'] = counts[0] if counts else 0
                summary['total_indicators'] = counts[1] if counts else 0

        return jsonify(summary)

    except Exception as e:
        logger.error(f"STREAMING-API-ERROR: Summary query failed: {e}")
        return jsonify({'error': 'Failed to get summary'}), 500