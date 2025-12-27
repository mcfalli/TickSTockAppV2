"""
Tier-Specific Pattern API Endpoints - Real Database Integration
Provides REST API endpoints for tier-specific pattern data from actual database tables.
"""

import logging
import time
from datetime import datetime, timedelta

from flask import Blueprint, current_app, jsonify, request

from src.infrastructure.database.tickstock_db import TickStockDatabase

logger = logging.getLogger(__name__)

# Create blueprint for tier pattern endpoints
tier_patterns_bp = Blueprint('tier_patterns', __name__, url_prefix='/api/patterns')

def _is_pattern_library_enabled() -> bool:
    """Check if pattern library is enabled via configuration."""
    try:
        from src.core.services.config_manager import get_config
        config = get_config()
        enabled = config.get('PATTERN_LIBRARY_ENABLED', True)
        if not enabled:
            logger.info("TIER-PATTERNS-API: Pattern library is disabled via configuration (PATTERN_LIBRARY_ENABLED=false)")
        return enabled
    except Exception as e:
        logger.error(f"TIER-PATTERNS-API: Error checking pattern library config: {e}")
        return True  # Default to enabled on error

def init_tier_patterns_api():
    """Initialize tier patterns API with database connection."""
    try:
        logger.info("TIER-PATTERNS-API: Tier patterns API initialized with database integration")
        return True
    except Exception as e:
        logger.error(f"TIER-PATTERNS-API: Failed to initialize API: {e}")
        return False

@tier_patterns_bp.route('/daily', methods=['GET'])
def get_daily_patterns():
    """
    Get daily tier patterns from daily_patterns table.
    
    Query Parameters:
        symbols: Comma-separated list of symbols (optional)
        confidence_min: Minimum confidence threshold (default: 0.6)
        limit: Maximum number of patterns to return (default: 50)
    
    Returns:
        JSON response with daily patterns
    """
    start_time = time.time()

    try:
        # Parse query parameters
        symbols = request.args.get('symbols', '').split(',') if request.args.get('symbols') else []
        symbols = [s.strip().upper() for s in symbols if s.strip()]
        confidence_min = float(request.args.get('confidence_min', 0.6))
        limit = int(request.args.get('limit', 50))

        # Validate parameters
        confidence_min = max(0.0, min(1.0, confidence_min))
        limit = max(1, min(200, limit))

        # Build SQL query for daily patterns
        query = """
        SELECT 
            id,
            symbol,
            pattern_type,
            confidence,
            pattern_data,
            detection_timestamp,
            expiration_date,
            levels,
            metadata
        FROM daily_patterns 
        WHERE confidence >= %s 
        AND detection_timestamp > %s
        """

        params = [confidence_min, datetime.now() - timedelta(days=7)]

        # Add symbol filtering if specified
        if symbols:
            placeholders = ','.join(['%s'] * len(symbols))
            query += f" AND symbol IN ({placeholders})"
            params.extend(symbols)

        # Order by confidence and limit
        query += " ORDER BY confidence DESC, detection_timestamp DESC LIMIT %s"
        params.append(limit)

        # Execute query
        db = TickStockDatabase(current_app.config)
        results = db.execute_query(query, params)

        # Format results for frontend
        patterns = []
        for row in results:
            pattern = {
                'id': str(row[0]),
                'symbol': row[1],
                'pattern_type': row[2],
                'confidence': float(row[3]),
                'pattern_data': row[4],
                'detection_timestamp': row[5].isoformat() if row[5] else None,
                'expiration_date': row[6].isoformat() if row[6] else None,
                'levels': row[7] if row[7] else [],
                'metadata': row[8] if row[8] else {},
                'tier': 'daily',
                'priority': _calculate_priority(float(row[3]))
            }
            patterns.append(pattern)

        response_time = (time.time() - start_time) * 1000

        response = {
            'patterns': patterns,
            'metadata': {
                'count': len(patterns),
                'tier': 'daily',
                'confidence_min': confidence_min,
                'symbols_filter': symbols if symbols else 'all',
                'response_time_ms': round(response_time, 2)
            }
        }

        logger.info(f"TIER-PATTERNS-API: Returned {len(patterns)} daily patterns in {response_time:.2f}ms")
        return jsonify(response)

    except Exception as e:
        logger.error(f"TIER-PATTERNS-API: Daily patterns error: {e}")
        return jsonify({'error': 'Failed to fetch daily patterns'}), 500

@tier_patterns_bp.route('/intraday', methods=['GET'])
def get_intraday_patterns():
    """
    Get intraday tier patterns from intraday_patterns table.
    """
    start_time = time.time()

    try:
        # Parse query parameters
        symbols = request.args.get('symbols', '').split(',') if request.args.get('symbols') else []
        symbols = [s.strip().upper() for s in symbols if s.strip()]
        confidence_min = float(request.args.get('confidence_min', 0.6))
        limit = int(request.args.get('limit', 75))

        # Validate parameters
        confidence_min = max(0.0, min(1.0, confidence_min))
        limit = max(1, min(200, limit))

        # Build SQL query for intraday patterns
        query = """
        SELECT 
            id,
            symbol,
            pattern_type,
            confidence,
            pattern_data,
            detection_timestamp,
            expiration_timestamp,
            levels,
            metadata
        FROM intraday_patterns 
        WHERE confidence >= %s 
        AND detection_timestamp > %s
        """

        params = [confidence_min, datetime.now() - timedelta(hours=24)]

        # Add symbol filtering if specified
        if symbols:
            placeholders = ','.join(['%s'] * len(symbols))
            query += f" AND symbol IN ({placeholders})"
            params.extend(symbols)

        # Order by confidence and limit
        query += " ORDER BY confidence DESC, detection_timestamp DESC LIMIT %s"
        params.append(limit)

        # Execute query
        db = TickStockDatabase(current_app.config)
        results = db.execute_query(query, params)

        # Format results for frontend
        patterns = []
        for row in results:
            pattern = {
                'id': str(row[0]),
                'symbol': row[1],
                'pattern_type': row[2],
                'confidence': float(row[3]),
                'pattern_data': row[4],
                'detection_timestamp': row[5].isoformat() if row[5] else None,
                'expiration_timestamp': row[6].isoformat() if row[6] else None,
                'levels': row[7] if row[7] else [],
                'metadata': row[8] if row[8] else {},
                'tier': 'intraday',
                'priority': _calculate_priority(float(row[3]))
            }
            patterns.append(pattern)

        response_time = (time.time() - start_time) * 1000

        response = {
            'patterns': patterns,
            'metadata': {
                'count': len(patterns),
                'tier': 'intraday',
                'confidence_min': confidence_min,
                'symbols_filter': symbols if symbols else 'all',
                'response_time_ms': round(response_time, 2)
            }
        }

        logger.info(f"TIER-PATTERNS-API: Returned {len(patterns)} intraday patterns in {response_time:.2f}ms")
        return jsonify(response)

    except Exception as e:
        logger.error(f"TIER-PATTERNS-API: Intraday patterns error: {e}")
        return jsonify({'error': 'Failed to fetch intraday patterns'}), 500

@tier_patterns_bp.route('/combo', methods=['GET'])
def get_combo_patterns():
    """
    Get combo tier patterns from pattern_detections table with pattern definitions.
    """
    start_time = time.time()

    # Check if pattern library is enabled
    if not _is_pattern_library_enabled():
        return jsonify({
            'patterns': [],
            'metadata': {
                'count': 0,
                'tier': 'combo',
                'confidence_min': 0.6,
                'symbols_filter': 'all',
                'response_time_ms': round((time.time() - start_time) * 1000, 2),
                'disabled': True,
                'message': 'Pattern library is disabled'
            }
        })

    try:
        # Parse query parameters
        symbols = request.args.get('symbols', '').split(',') if request.args.get('symbols') else []
        symbols = [s.strip().upper() for s in symbols if s.strip()]
        confidence_min = float(request.args.get('confidence_min', 0.6))
        limit = int(request.args.get('limit', 25))

        # Validate parameters
        confidence_min = max(0.0, min(1.0, confidence_min))
        limit = max(1, min(200, limit))

        # Build SQL query for combo patterns (using pattern_detections + definitions)
        query = """
        SELECT 
            pd.id,
            pd.symbol,
            pdef.name as pattern_type,
            pd.confidence,
            pd.pattern_data,
            pd.detected_at as detection_timestamp,
            pd.price_at_detection,
            pd.volume_at_detection,
            pd.outcome_1d,
            pd.outcome_5d,
            pdef.category,
            pdef.risk_level
        FROM pattern_detections pd
        JOIN pattern_definitions pdef ON pd.pattern_id = pdef.id
        WHERE pd.confidence >= %s 
        AND pd.detected_at > %s
        AND pdef.enabled = true
        """

        params = [confidence_min, datetime.now() - timedelta(days=3)]

        # Add symbol filtering if specified
        if symbols:
            placeholders = ','.join(['%s'] * len(symbols))
            query += f" AND pd.symbol IN ({placeholders})"
            params.extend(symbols)

        # Order by confidence and limit
        query += " ORDER BY pd.confidence DESC, pd.detected_at DESC LIMIT %s"
        params.append(limit)

        # Execute query
        db = TickStockDatabase(current_app.config)
        results = db.execute_query(query, params)

        # Format results for frontend
        patterns = []
        for row in results:
            pattern = {
                'id': str(row[0]),
                'symbol': row[1],
                'pattern_type': row[2],
                'confidence': float(row[3]),
                'pattern_data': row[4] if row[4] else {},
                'detection_timestamp': row[5].isoformat() if row[5] else None,
                'price_at_detection': float(row[6]) if row[6] else None,
                'volume_at_detection': int(row[7]) if row[7] else None,
                'outcome_1d': float(row[8]) if row[8] else None,
                'outcome_5d': float(row[9]) if row[9] else None,
                'category': row[10],
                'risk_level': row[11],
                'tier': 'combo',
                'priority': _calculate_priority_combo(float(row[3]), row[11])
            }
            patterns.append(pattern)

        response_time = (time.time() - start_time) * 1000

        response = {
            'patterns': patterns,
            'metadata': {
                'count': len(patterns),
                'tier': 'combo',
                'confidence_min': confidence_min,
                'symbols_filter': symbols if symbols else 'all',
                'response_time_ms': round(response_time, 2)
            }
        }

        logger.info(f"TIER-PATTERNS-API: Returned {len(patterns)} combo patterns in {response_time:.2f}ms")
        return jsonify(response)

    except Exception as e:
        logger.error(f"TIER-PATTERNS-API: Combo patterns error: {e}")
        return jsonify({'error': 'Failed to fetch combo patterns'}), 500

def _calculate_priority(confidence: float) -> str:
    """Calculate priority based on confidence level."""
    if confidence >= 0.9:
        return 'CRITICAL'
    if confidence >= 0.8:
        return 'HIGH'
    if confidence >= 0.7:
        return 'MEDIUM'
    return 'LOW'

def _calculate_priority_combo(confidence: float, risk_level: str) -> str:
    """Calculate priority for combo patterns based on confidence and risk."""
    base_priority = _calculate_priority(confidence)

    # Adjust based on risk level
    if risk_level == 'high' and confidence >= 0.8:
        return 'CRITICAL'
    if risk_level == 'low' and base_priority == 'CRITICAL':
        return 'HIGH'

    return base_priority

@tier_patterns_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for tier patterns API."""
    try:
        # Simple database connectivity test
        db = TickStockDatabase(current_app.config)
        result = db.execute_query("SELECT 1", [])

        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"TIER-PATTERNS-API: Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@tier_patterns_bp.route('/hourly', methods=['GET'])
def get_hourly_patterns():
    """
    Get hourly tier patterns from hourly_patterns table.

    Query Parameters:
        symbols: Comma-separated list of symbols (optional)
        confidence_min: Minimum confidence threshold (default: 0.6)
        limit: Maximum number of patterns to return (default: 50)

    Returns:
        JSON response with hourly patterns
    """
    start_time = time.time()

    try:
        # Parse query parameters
        symbols = request.args.get('symbols', '').split(',') if request.args.get('symbols') else []
        symbols = [s.strip().upper() for s in symbols if s.strip()]
        confidence_min = float(request.args.get('confidence_min', 0.6))
        limit = int(request.args.get('limit', 50))

        # Validate parameters
        confidence_min = max(0.0, min(1.0, confidence_min))
        limit = max(1, min(200, limit))

        # Build SQL query for hourly patterns (1 hour window)
        query = """
        SELECT
            id,
            symbol,
            pattern_type,
            confidence,
            pattern_data,
            detection_timestamp,
            expiration_timestamp,
            levels,
            metadata
        FROM hourly_patterns
        WHERE confidence >= %s
        AND detection_timestamp > NOW() - INTERVAL '1 hour'
        """

        params = [confidence_min]

        # Add symbol filtering if specified
        if symbols:
            placeholders = ','.join(['%s'] * len(symbols))
            query += f" AND symbol IN ({placeholders})"
            params.extend(symbols)

        # Order by confidence and limit
        query += " ORDER BY confidence DESC, detection_timestamp DESC LIMIT %s"
        params.append(limit)

        # Execute query
        db = TickStockDatabase(current_app.config)
        results = db.execute_query(query, params)

        # Format results for frontend
        patterns = []
        for row in results:
            pattern = {
                'id': str(row[0]),
                'symbol': row[1],
                'pattern_type': row[2],
                'confidence': float(row[3]),
                'pattern_data': row[4],
                'detection_timestamp': row[5].isoformat() if row[5] else None,
                'expiration_timestamp': row[6].isoformat() if row[6] else None,
                'levels': row[7] if row[7] else [],
                'metadata': row[8] if row[8] else {},
                'tier': 'hourly',
                'priority': _calculate_priority(float(row[3]))
            }
            patterns.append(pattern)

        response_time = (time.time() - start_time) * 1000

        response = {
            'patterns': patterns,
            'metadata': {
                'count': len(patterns),
                'tier': 'hourly',
                'confidence_min': confidence_min,
                'symbols_filter': symbols if symbols else 'all',
                'response_time_ms': round(response_time, 2)
            }
        }

        logger.info(f"TIER-PATTERNS-API: Returned {len(patterns)} hourly patterns in {response_time:.2f}ms")
        return jsonify(response)

    except Exception as e:
        logger.error(f"TIER-PATTERNS-API: Hourly patterns error: {e}")
        return jsonify({'error': 'Failed to fetch hourly patterns'}), 500

@tier_patterns_bp.route('/weekly', methods=['GET'])
def get_weekly_patterns():
    """
    Get weekly tier patterns from weekly_patterns table.

    Query Parameters:
        symbols: Comma-separated list of symbols (optional)
        confidence_min: Minimum confidence threshold (default: 0.6)
        limit: Maximum number of patterns to return (default: 50)

    Returns:
        JSON response with weekly patterns
    """
    start_time = time.time()

    try:
        # Parse query parameters
        symbols = request.args.get('symbols', '').split(',') if request.args.get('symbols') else []
        symbols = [s.strip().upper() for s in symbols if s.strip()]
        confidence_min = float(request.args.get('confidence_min', 0.6))
        limit = int(request.args.get('limit', 50))

        # Validate parameters
        confidence_min = max(0.0, min(1.0, confidence_min))
        limit = max(1, min(200, limit))

        # Build SQL query for weekly patterns (this week since Monday)
        query = """
        SELECT
            id,
            symbol,
            pattern_type,
            confidence,
            pattern_data,
            detection_timestamp,
            expiration_date,
            levels,
            metadata
        FROM weekly_patterns
        WHERE confidence >= %s
        AND detection_timestamp >= date_trunc('week', NOW())
        """

        params = [confidence_min]

        # Add symbol filtering if specified
        if symbols:
            placeholders = ','.join(['%s'] * len(symbols))
            query += f" AND symbol IN ({placeholders})"
            params.extend(symbols)

        # Order by confidence and limit
        query += " ORDER BY confidence DESC, detection_timestamp DESC LIMIT %s"
        params.append(limit)

        # Execute query
        db = TickStockDatabase(current_app.config)
        results = db.execute_query(query, params)

        # Format results for frontend
        patterns = []
        for row in results:
            pattern = {
                'id': str(row[0]),
                'symbol': row[1],
                'pattern_type': row[2],
                'confidence': float(row[3]),
                'pattern_data': row[4],
                'detection_timestamp': row[5].isoformat() if row[5] else None,
                'expiration_date': row[6].isoformat() if row[6] else None,
                'levels': row[7] if row[7] else [],
                'metadata': row[8] if row[8] else {},
                'tier': 'weekly',
                'priority': _calculate_priority(float(row[3]))
            }
            patterns.append(pattern)

        response_time = (time.time() - start_time) * 1000

        response = {
            'patterns': patterns,
            'metadata': {
                'count': len(patterns),
                'tier': 'weekly',
                'confidence_min': confidence_min,
                'symbols_filter': symbols if symbols else 'all',
                'response_time_ms': round(response_time, 2)
            }
        }

        logger.info(f"TIER-PATTERNS-API: Returned {len(patterns)} weekly patterns in {response_time:.2f}ms")
        return jsonify(response)

    except Exception as e:
        logger.error(f"TIER-PATTERNS-API: Weekly patterns error: {e}")
        return jsonify({'error': 'Failed to fetch weekly patterns'}), 500

@tier_patterns_bp.route('/monthly', methods=['GET'])
def get_monthly_patterns():
    """
    Get monthly tier patterns from monthly_patterns table.

    Query Parameters:
        symbols: Comma-separated list of symbols (optional)
        confidence_min: Minimum confidence threshold (default: 0.6)
        limit: Maximum number of patterns to return (default: 50)

    Returns:
        JSON response with monthly patterns
    """
    start_time = time.time()

    try:
        # Parse query parameters
        symbols = request.args.get('symbols', '').split(',') if request.args.get('symbols') else []
        symbols = [s.strip().upper() for s in symbols if s.strip()]
        confidence_min = float(request.args.get('confidence_min', 0.6))
        limit = int(request.args.get('limit', 50))

        # Validate parameters
        confidence_min = max(0.0, min(1.0, confidence_min))
        limit = max(1, min(200, limit))

        # Build SQL query for monthly patterns (this month since 1st)
        query = """
        SELECT
            id,
            symbol,
            pattern_type,
            confidence,
            pattern_data,
            detection_timestamp,
            expiration_date,
            levels,
            metadata
        FROM monthly_patterns
        WHERE confidence >= %s
        AND detection_timestamp >= date_trunc('month', NOW())
        """

        params = [confidence_min]

        # Add symbol filtering if specified
        if symbols:
            placeholders = ','.join(['%s'] * len(symbols))
            query += f" AND symbol IN ({placeholders})"
            params.extend(symbols)

        # Order by confidence and limit
        query += " ORDER BY confidence DESC, detection_timestamp DESC LIMIT %s"
        params.append(limit)

        # Execute query
        db = TickStockDatabase(current_app.config)
        results = db.execute_query(query, params)

        # Format results for frontend
        patterns = []
        for row in results:
            pattern = {
                'id': str(row[0]),
                'symbol': row[1],
                'pattern_type': row[2],
                'confidence': float(row[3]),
                'pattern_data': row[4],
                'detection_timestamp': row[5].isoformat() if row[5] else None,
                'expiration_date': row[6].isoformat() if row[6] else None,
                'levels': row[7] if row[7] else [],
                'metadata': row[8] if row[8] else {},
                'tier': 'monthly',
                'priority': _calculate_priority(float(row[3]))
            }
            patterns.append(pattern)

        response_time = (time.time() - start_time) * 1000

        response = {
            'patterns': patterns,
            'metadata': {
                'count': len(patterns),
                'tier': 'monthly',
                'confidence_min': confidence_min,
                'symbols_filter': symbols if symbols else 'all',
                'response_time_ms': round(response_time, 2)
            }
        }

        logger.info(f"TIER-PATTERNS-API: Returned {len(patterns)} monthly patterns in {response_time:.2f}ms")
        return jsonify(response)

    except Exception as e:
        logger.error(f"TIER-PATTERNS-API: Monthly patterns error: {e}")
        return jsonify({'error': 'Failed to fetch monthly patterns'}), 500

@tier_patterns_bp.route('/daily_intraday', methods=['GET'])
def get_daily_intraday_patterns():
    """
    Get daily-intraday combo patterns from daily_intraday_patterns table.

    Query Parameters:
        symbols: Comma-separated list of symbols (optional)
        confidence_min: Minimum confidence threshold (default: 0.6)
        limit: Maximum number of patterns to return (default: 50)

    Returns:
        JSON response with daily-intraday combo patterns
    """
    start_time = time.time()

    try:
        # Parse query parameters
        symbols = request.args.get('symbols', '').split(',') if request.args.get('symbols') else []
        symbols = [s.strip().upper() for s in symbols if s.strip()]
        confidence_min = float(request.args.get('confidence_min', 0.6))
        limit = int(request.args.get('limit', 50))

        # Validate parameters
        confidence_min = max(0.0, min(1.0, confidence_min))
        limit = max(1, min(200, limit))

        # Build SQL query for daily_intraday patterns (30 minutes window, includes intraday_signal)
        query = """
        SELECT
            id,
            symbol,
            pattern_type,
            confidence,
            pattern_data,
            detection_timestamp,
            expiration_timestamp,
            levels,
            metadata,
            intraday_signal
        FROM daily_intraday_patterns
        WHERE confidence >= %s
        AND detection_timestamp > NOW() - INTERVAL '30 minutes'
        """

        params = [confidence_min]

        # Add symbol filtering if specified
        if symbols:
            placeholders = ','.join(['%s'] * len(symbols))
            query += f" AND symbol IN ({placeholders})"
            params.extend(symbols)

        # Order by confidence and limit
        query += " ORDER BY confidence DESC, detection_timestamp DESC LIMIT %s"
        params.append(limit)

        # Execute query
        db = TickStockDatabase(current_app.config)
        results = db.execute_query(query, params)

        # Format results for frontend
        patterns = []
        for row in results:
            pattern = {
                'id': str(row[0]),
                'symbol': row[1],
                'pattern_type': row[2],
                'confidence': float(row[3]),
                'pattern_data': row[4],
                'detection_timestamp': row[5].isoformat() if row[5] else None,
                'expiration_timestamp': row[6].isoformat() if row[6] else None,
                'levels': row[7] if row[7] else [],
                'metadata': row[8] if row[8] else {},
                'intraday_signal': row[9] if row[9] else {},
                'tier': 'daily_intraday',
                'priority': _calculate_priority(float(row[3]))
            }
            patterns.append(pattern)

        response_time = (time.time() - start_time) * 1000

        response = {
            'patterns': patterns,
            'metadata': {
                'count': len(patterns),
                'tier': 'daily_intraday',
                'confidence_min': confidence_min,
                'symbols_filter': symbols if symbols else 'all',
                'response_time_ms': round(response_time, 2)
            }
        }

        logger.info(f"TIER-PATTERNS-API: Returned {len(patterns)} daily_intraday patterns in {response_time:.2f}ms")
        return jsonify(response)

    except Exception as e:
        logger.error(f"TIER-PATTERNS-API: Daily-intraday patterns error: {e}")
        return jsonify({'error': 'Failed to fetch daily_intraday patterns'}), 500

@tier_patterns_bp.route('/indicators/latest', methods=['GET'])
def get_latest_indicators():
    """
    Get latest indicator calculations from intraday_indicators table.

    Query Parameters:
        symbols: Comma-separated list of symbols (optional)
        timeframes: Comma-separated timeframe list (optional: 1min,5min,hourly,daily)
        indicator_types: Comma-separated indicator types (optional)
        limit: Maximum number of indicators to return (default: 30, max: 100)

    Returns:
        JSON response with latest indicators across all timeframes
    """
    start_time = time.time()

    try:
        # Parse query parameters
        symbols = request.args.get('symbols', '').split(',') if request.args.get('symbols') else []
        symbols = [s.strip().upper() for s in symbols if s.strip()]

        timeframes = request.args.get('timeframes', '').split(',') if request.args.get('timeframes') else []
        timeframes = [t.strip() for t in timeframes if t.strip()]

        indicator_types = request.args.get('indicator_types', '').split(',') if request.args.get('indicator_types') else []
        indicator_types = [i.strip() for i in indicator_types if i.strip()]

        limit = int(request.args.get('limit', 30))

        # Validate parameters
        limit = max(1, min(100, limit))

        # Build SQL query for indicators (30 minutes window)
        query = """
        SELECT
            id,
            symbol,
            indicator_type,
            value,
            value_data,
            calculation_timestamp,
            timeframe,
            metadata
        FROM intraday_indicators
        WHERE calculation_timestamp > NOW() - INTERVAL '30 minutes'
        AND expiration_timestamp > NOW()
        """

        params = []

        # Add optional filters
        if symbols:
            placeholders = ','.join(['%s'] * len(symbols))
            query += f" AND symbol IN ({placeholders})"
            params.extend(symbols)

        if timeframes:
            placeholders = ','.join(['%s'] * len(timeframes))
            query += f" AND timeframe IN ({placeholders})"
            params.extend(timeframes)

        if indicator_types:
            placeholders = ','.join(['%s'] * len(indicator_types))
            query += f" AND indicator_type IN ({placeholders})"
            params.extend(indicator_types)

        # Order by calculation timestamp and limit
        query += " ORDER BY calculation_timestamp DESC LIMIT %s"
        params.append(limit)

        # Execute query
        db = TickStockDatabase(current_app.config)
        results = db.execute_query(query, params)

        # Format results for frontend
        indicators = []
        for row in results:
            indicator = {
                'id': str(row[0]),
                'symbol': row[1],
                'indicator_type': row[2],
                'value': float(row[3]) if row[3] else None,
                'value_data': row[4] if row[4] else {},
                'calculation_timestamp': row[5].isoformat() if row[5] else None,
                'timeframe': row[6],
                'metadata': row[7] if row[7] else {}
            }
            indicators.append(indicator)

        response_time = (time.time() - start_time) * 1000

        # Get unique timeframes for metadata
        timeframes_included = list(set([ind['timeframe'] for ind in indicators])) if indicators else []

        response = {
            'indicators': indicators,
            'metadata': {
                'count': len(indicators),
                'response_time_ms': round(response_time, 2),
                'timeframes_included': timeframes_included,
                'symbols_filter': symbols if symbols else 'all'
            }
        }

        logger.info(f"TIER-PATTERNS-API: Returned {len(indicators)} indicators in {response_time:.2f}ms")
        return jsonify(response)

    except Exception as e:
        logger.error(f"TIER-PATTERNS-API: Indicators error: {e}")
        return jsonify({'error': 'Failed to fetch indicators'}), 500
