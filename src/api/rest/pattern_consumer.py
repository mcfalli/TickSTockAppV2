"""
Pattern Consumer API - Sprint 19 Phase 1
Redis-consuming API endpoints for pattern data with <50ms response targets.

Architecture:
- Consumer role: Consumes cached pattern data from Redis (populated by TickStockPL)
- Zero database queries: All pattern data served from Redis cache
- Performance: Multi-layer caching for <50ms API response times
- Filtering: Advanced pattern filtering through Redis sorted set operations
"""

import logging
import time
from typing import Dict, Any, List, Optional
from flask import Blueprint, request, jsonify, current_app
from werkzeug.exceptions import BadRequest
import json

logger = logging.getLogger(__name__)

# Create Blueprint
pattern_consumer_bp = Blueprint('pattern_consumer', __name__)

def get_pattern_cache():
    """Get pattern cache manager from Flask app context."""
    return getattr(current_app, 'pattern_cache', None)

def validate_scan_parameters(args: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and parse pattern scan parameters."""
    try:
        # Parse pattern types
        pattern_types = []
        if 'pattern_types' in args:
            pattern_types = args.getlist('pattern_types')
        
        # Parse numeric parameters with defaults
        rs_min = float(args.get('rs_min', 0))
        vol_min = float(args.get('vol_min', 0))
        confidence_min = float(args.get('confidence_min', 0.5))
        
        # Parse RSI range
        rsi_range_str = args.get('rsi_range', '0,100')
        try:
            rsi_parts = rsi_range_str.split(',')
            rsi_min = float(rsi_parts[0])
            rsi_max = float(rsi_parts[1]) if len(rsi_parts) > 1 else 100.0
        except (ValueError, IndexError):
            rsi_min, rsi_max = 0.0, 100.0
        
        # Parse symbols
        symbols = []
        if 'symbols' in args:
            symbols = args.getlist('symbols')
        
        # Parse sectors (for future use)
        sectors = []
        if 'sectors' in args:
            sectors = args.getlist('sectors')
        
        # Parse pagination
        page = max(int(args.get('page', 1)), 1)
        per_page = max(min(int(args.get('per_page', 30)), 100), 1)
        
        # Parse sorting
        sort_by = args.get('sort_by', 'confidence')
        valid_sort_fields = ['confidence', 'detected_at', 'symbol', 'rs', 'volume']
        if sort_by not in valid_sort_fields:
            sort_by = 'confidence'
        
        sort_order = args.get('sort_order', 'desc')
        if sort_order not in ['asc', 'desc']:
            sort_order = 'desc'
        
        # Parse timeframe filter
        timeframe = args.get('timeframe', 'All')
        valid_timeframes = ['All', 'Daily', 'Intraday', 'Combo']
        if timeframe not in valid_timeframes:
            timeframe = 'All'
        
        # Validate ranges
        if rs_min < 0:
            rs_min = 0
        if vol_min < 0:
            vol_min = 0
        if confidence_min < 0 or confidence_min > 1:
            confidence_min = 0.5
        if rsi_min < 0 or rsi_min > 100:
            rsi_min = 0
        if rsi_max < 0 or rsi_max > 100:
            rsi_max = 100
        if rsi_min > rsi_max:
            rsi_min, rsi_max = rsi_max, rsi_min
        
        return {
            'pattern_types': pattern_types,
            'rs_min': rs_min,
            'vol_min': vol_min,
            'rsi_range': [rsi_min, rsi_max],
            'confidence_min': confidence_min,
            'symbols': symbols,
            'sectors': sectors,
            'page': page,
            'per_page': per_page,
            'sort_by': sort_by,
            'sort_order': sort_order,
            'timeframe': timeframe
        }
        
    except (ValueError, TypeError) as e:
        logger.error("PATTERN-API: Parameter validation error: %s", e)
        raise BadRequest(f"Invalid parameter: {str(e)}")

@pattern_consumer_bp.route('/api/patterns/scan', methods=['GET'])
def scan_patterns():
    """
    Unified pattern scanning across all timeframes with advanced filtering.
    
    Consumes cached pattern data from Redis (populated by TickStockPL events).
    Performance target: <50ms response time for 95th percentile.
    
    Query Parameters:
    - pattern_types: List of pattern types (Breakout, Volume, etc.)
    - rs_min: Minimum relative strength (default: 0)
    - vol_min: Minimum volume multiple (default: 0)
    - rsi_range: RSI range as "min,max" (default: "0,100")
    - timeframe: All|Daily|Intraday|Combo (default: All)
    - confidence_min: Minimum confidence (default: 0.5)
    - symbols: Specific symbols to filter
    - sectors: Sector filters (future feature)
    - page: Page number (default: 1)
    - per_page: Results per page (default: 30, max: 100)
    - sort_by: confidence|detected_at|symbol|rs|volume
    - sort_order: asc|desc (default: desc)
    
    Returns:
        JSON response with patterns and pagination info
    """
    try:
        start_time = time.time()
        
        # Get pattern cache manager
        pattern_cache = get_pattern_cache()
        if not pattern_cache:
            logger.error("PATTERN-API: Pattern cache not available")
            return jsonify({
                'error': 'Pattern cache service unavailable',
                'patterns': [],
                'pagination': {'page': 1, 'per_page': 30, 'total': 0, 'pages': 0}
            }), 503
        
        # Validate and parse parameters
        filters = validate_scan_parameters(request.args)
        
        logger.debug("PATTERN-API: Scan request - filters: %s", filters)
        
        # Query patterns from Redis cache
        response = pattern_cache.scan_patterns(filters)
        
        # Add performance metrics
        response_time = (time.time() - start_time) * 1000
        response.setdefault('performance', {})
        response['performance']['api_response_time_ms'] = round(response_time, 2)
        response['performance']['source'] = 'redis_cache'
        
        # Log performance
        if response_time > 50:  # Above 50ms target
            logger.warning("PATTERN-API: Slow response - %.2f ms for %d patterns", 
                          response_time, len(response.get('patterns', [])))
        else:
            logger.debug("PATTERN-API: Response completed - %.2f ms for %d patterns",
                        response_time, len(response.get('patterns', [])))
        
        return jsonify(response)
        
    except BadRequest as e:
        return jsonify({
            'error': str(e),
            'patterns': [],
            'pagination': {'page': 1, 'per_page': 30, 'total': 0, 'pages': 0}
        }), 400
        
    except Exception as e:
        logger.error("PATTERN-API: Unexpected error in pattern scan: %s", e)
        return jsonify({
            'error': 'Internal server error',
            'patterns': [],
            'pagination': {'page': 1, 'per_page': 30, 'total': 0, 'pages': 0}
        }), 500

@pattern_consumer_bp.route('/api/patterns/stats', methods=['GET'])
def get_pattern_stats():
    """
    Get pattern cache statistics and performance metrics.
    
    Returns:
        JSON response with cache statistics
    """
    try:
        start_time = time.time()
        
        # Get pattern cache manager
        pattern_cache = get_pattern_cache()
        if not pattern_cache:
            return jsonify({
                'error': 'Pattern cache service unavailable',
                'stats': {}
            }), 503
        
        # Get cache statistics
        stats = pattern_cache.get_cache_stats()
        
        # Add API performance info
        response_time = (time.time() - start_time) * 1000
        stats['api_response_time_ms'] = round(response_time, 2)
        
        return jsonify({
            'stats': stats,
            'status': 'healthy' if stats.get('cached_patterns', 0) > 0 else 'no_data'
        })
        
    except Exception as e:
        logger.error("PATTERN-API: Error getting pattern stats: %s", e)
        return jsonify({
            'error': 'Failed to retrieve statistics',
            'stats': {}
        }), 500

@pattern_consumer_bp.route('/api/patterns/summary', methods=['GET'])
def get_pattern_summary():
    """
    Get high-level pattern summary for dashboard display.
    
    Returns:
        JSON response with pattern summary metrics
    """
    try:
        start_time = time.time()
        
        # Get pattern cache manager
        pattern_cache = get_pattern_cache()
        if not pattern_cache:
            return jsonify({
                'error': 'Pattern cache service unavailable'
            }), 503
        
        # Get recent patterns (high confidence, last hour)
        current_time = time.time()
        recent_filters = {
            'confidence_min': 0.7,
            'per_page': 100,
            'sort_by': 'confidence',
            'sort_order': 'desc'
        }
        
        recent_response = pattern_cache.scan_patterns(recent_filters)
        recent_patterns = recent_response.get('patterns', [])
        
        # Calculate summary metrics
        total_patterns = len(recent_patterns)
        high_confidence_count = len([p for p in recent_patterns if float(p['conf']) > 0.8])
        
        # Pattern type distribution
        pattern_type_counts = {}
        symbol_counts = {}
        
        for pattern in recent_patterns:
            pattern_type = pattern['pattern']
            symbol = pattern['symbol']
            
            pattern_type_counts[pattern_type] = pattern_type_counts.get(pattern_type, 0) + 1
            symbol_counts[symbol] = symbol_counts.get(symbol, 0) + 1
        
        # Top patterns and symbols
        top_patterns = sorted(pattern_type_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        top_symbols = sorted(symbol_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Get cache stats
        cache_stats = pattern_cache.get_cache_stats()
        
        summary = {
            'total_patterns': total_patterns,
            'high_confidence_patterns': high_confidence_count,
            'pattern_types': {
                'distribution': pattern_type_counts,
                'top_patterns': [{'pattern': p[0], 'count': p[1]} for p in top_patterns]
            },
            'symbols': {
                'active_symbols': len(symbol_counts),
                'top_symbols': [{'symbol': s[0], 'count': s[1]} for s in top_symbols]
            },
            'cache_performance': {
                'hit_ratio': cache_stats.get('cache_hit_ratio', 0),
                'cached_patterns': cache_stats.get('cached_patterns', 0),
                'last_event_time': cache_stats.get('last_event_time'),
            },
            'performance': {
                'api_response_time_ms': round((time.time() - start_time) * 1000, 2),
                'source': 'redis_cache'
            }
        }
        
        return jsonify(summary)
        
    except Exception as e:
        logger.error("PATTERN-API: Error getting pattern summary: %s", e)
        return jsonify({
            'error': 'Failed to retrieve summary'
        }), 500

@pattern_consumer_bp.route('/api/patterns/health', methods=['GET'])
def get_pattern_health():
    """
    Health check endpoint for pattern cache service.
    
    Returns:
        JSON response with health status
    """
    try:
        start_time = time.time()
        
        # Get pattern cache manager
        pattern_cache = get_pattern_cache()
        if not pattern_cache:
            return jsonify({
                'status': 'error',
                'message': 'Pattern cache service unavailable',
                'healthy': False
            }), 503
        
        # Get cache statistics
        stats = pattern_cache.get_cache_stats()
        
        # Determine health status
        cached_patterns = stats.get('cached_patterns', 0)
        hit_ratio = stats.get('cache_hit_ratio', 0)
        last_event_time = stats.get('last_event_time')
        
        # Health criteria
        healthy = True
        status = 'healthy'
        messages = []
        
        if cached_patterns == 0:
            healthy = False
            status = 'warning'
            messages.append('No patterns in cache')
        
        if hit_ratio < 0.5:  # <50% hit ratio
            status = 'degraded' if healthy else status
            messages.append(f'Low cache hit ratio: {hit_ratio:.1%}')
        
        if last_event_time and (time.time() - last_event_time) > 300:  # No events in 5 minutes
            status = 'warning' if healthy else status
            messages.append('No recent pattern events')
        
        response_time = (time.time() - start_time) * 1000
        
        health_info = {
            'status': status,
            'healthy': healthy,
            'message': '; '.join(messages) if messages else 'Pattern cache operating normally',
            'metrics': {
                'cached_patterns': cached_patterns,
                'cache_hit_ratio': hit_ratio,
                'events_processed': stats.get('events_processed', 0),
                'last_event_time': last_event_time,
                'response_time_ms': round(response_time, 2)
            },
            'last_check': time.time()
        }
        
        return jsonify(health_info)
        
    except Exception as e:
        logger.error("PATTERN-API: Health check error: %s", e)
        return jsonify({
            'status': 'error',
            'healthy': False,
            'message': f'Health check failed: {str(e)}',
            'last_check': time.time()
        }), 500

# Performance monitoring decorator
def log_performance(f):
    """Decorator to log API performance metrics."""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = f(*args, **kwargs)
            response_time = (time.time() - start_time) * 1000
            
            # Log performance metrics
            endpoint = request.endpoint
            method = request.method
            
            if response_time > 50:  # Above target
                logger.warning("PATTERN-API: SLOW %s %s - %.2f ms", method, endpoint, response_time)
            else:
                logger.debug("PATTERN-API: %s %s - %.2f ms", method, endpoint, response_time)
            
            return result
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            logger.error("PATTERN-API: ERROR %s %s - %.2f ms: %s", 
                        request.method, request.endpoint, response_time, str(e))
            raise
    
    wrapper.__name__ = f.__name__
    return wrapper

# Apply performance monitoring to all endpoints
for rule in pattern_consumer_bp.url_map.iter_rules():
    if rule.endpoint != 'static':
        view_func = pattern_consumer_bp.view_functions.get(rule.endpoint)
        if view_func:
            pattern_consumer_bp.view_functions[rule.endpoint] = log_performance(view_func)

# Blueprint error handlers
@pattern_consumer_bp.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Endpoint not found',
        'message': 'The requested pattern API endpoint does not exist'
    }), 404

@pattern_consumer_bp.errorhandler(500)
def internal_error(error):
    logger.error("PATTERN-API: Internal error: %s", str(error))
    return jsonify({
        'error': 'Internal server error',
        'message': 'An unexpected error occurred in the pattern API'
    }), 500