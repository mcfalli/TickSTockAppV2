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
