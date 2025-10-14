"""
User Universe Management API - Sprint 19 Phase 1
User watchlist and preferences management with read-only Consumer database access.

Architecture:
- Consumer role: Read-only access to user data tables and symbols table
- User data management: Watchlists, filter presets, universe selections
- Symbol data: Dropdown population from TickStockPL shared database
- Performance: <50ms response times for user data operations
"""

import logging
import time

from flask import Blueprint, current_app, jsonify, request
from werkzeug.exceptions import BadRequest

logger = logging.getLogger(__name__)

# Create Blueprint
user_universe_bp = Blueprint('user_universe', __name__)

def get_tickstock_db():
    """Get TickStock database service from Flask app context."""
    return getattr(current_app, 'tickstock_db', None)

def get_cache_control():
    """Get cache control service from Flask app context."""
    return getattr(current_app, 'cache_control', None)

def get_current_user_id():
    """Get current user ID from session/auth context."""
    # TODO: Implement proper authentication
    # For now, return a default user ID for development
    return request.headers.get('X-User-ID', 'default_user')

@user_universe_bp.route('/api/symbols', methods=['GET'])
def get_symbols():
    """
    Get all active symbols with metadata for UI dropdown population.
    Consumer database access: Read-only symbols table queries.
    
    Query Parameters:
    - market: Filter by market (stocks, crypto, forex)
    - search: Search symbols/names by text
    - limit: Maximum symbols to return (default: 1000)
    
    Returns:
        JSON response with symbol list
    """
    try:
        start_time = time.time()

        # Get database service
        tickstock_db = get_tickstock_db()
        if not tickstock_db:
            logger.error("UNIVERSE-API: TickStock database not available")
            return jsonify({
                'error': 'Database service unavailable',
                'symbols': []
            }), 503

        # Parse query parameters
        market = request.args.get('market')
        search_term = request.args.get('search', '').strip()
        limit = min(int(request.args.get('limit', 1000)), 5000)

        # Get symbols from database (read-only)
        symbols = tickstock_db.get_symbols_for_dropdown()

        # Apply filters
        filtered_symbols = symbols

        if market:
            filtered_symbols = [s for s in filtered_symbols if s.get('market') == market]

        if search_term:
            search_lower = search_term.lower()
            filtered_symbols = [
                s for s in filtered_symbols
                if search_lower in s['symbol'].lower() or
                   search_lower in s.get('name', '').lower()
            ]

        # Apply limit
        filtered_symbols = filtered_symbols[:limit]

        # Performance metrics
        response_time = (time.time() - start_time) * 1000

        response = {
            'symbols': filtered_symbols,
            'count': len(filtered_symbols),
            'filters': {
                'market': market,
                'search': search_term,
                'limit': limit
            },
            'performance': {
                'api_response_time_ms': round(response_time, 2),
                'source': 'tickstock_database'
            }
        }

        # Log performance
        if response_time > 50:
            logger.warning("UNIVERSE-API: Slow symbols query - %.2f ms for %d symbols",
                          response_time, len(filtered_symbols))
        else:
            logger.debug("UNIVERSE-API: Symbols query completed - %.2f ms for %d symbols",
                        response_time, len(filtered_symbols))

        return jsonify(response)

    except Exception as e:
        logger.error("UNIVERSE-API: Error getting symbols: %s", e)
        return jsonify({
            'error': 'Failed to retrieve symbols',
            'symbols': []
        }), 500

@user_universe_bp.route('/api/symbols/<symbol>', methods=['GET'])
def get_symbol_details(symbol: str):
    """
    Get detailed information for a specific symbol.
    
    Args:
        symbol: Stock symbol to get details for
        
    Returns:
        JSON response with symbol details
    """
    try:
        start_time = time.time()

        # Get database service
        tickstock_db = get_tickstock_db()
        if not tickstock_db:
            return jsonify({'error': 'Database service unavailable'}), 503

        # Get symbol details
        symbol_data = tickstock_db.get_symbol_details(symbol.upper())

        if not symbol_data:
            return jsonify({'error': f'Symbol {symbol} not found'}), 404

        response_time = (time.time() - start_time) * 1000
        symbol_data['performance'] = {
            'api_response_time_ms': round(response_time, 2),
            'source': 'tickstock_database'
        }

        return jsonify(symbol_data)

    except Exception as e:
        logger.error("UNIVERSE-API: Error getting symbol details for %s: %s", symbol, e)
        return jsonify({'error': 'Failed to retrieve symbol details'}), 500

@user_universe_bp.route('/api/users/universe', methods=['GET'])
def get_user_universes():
    """
    Get available universe selections for current user.
    Uses cached universe data from CacheControl.
    
    Returns:
        JSON response with available universes
    """
    try:
        start_time = time.time()

        # Get cache control service
        cache_control = get_cache_control()
        if not cache_control:
            logger.error("UNIVERSE-API: Cache control not available")
            return jsonify({
                'error': 'Cache service unavailable',
                'universes': {}
            }), 503

        # Get available universes
        universes_metadata = cache_control.get_available_universes()

        # Format for API response
        formatted_universes = []
        for universe_key, metadata in universes_metadata.items():
            formatted_universes.append({
                'key': universe_key,
                'description': metadata.get('description', universe_key),
                'criteria': metadata.get('criteria', ''),
                'count': metadata.get('count', 0),
                'category': universe_key.split('_')[0] if '_' in universe_key else 'unknown'
            })

        # Sort by category and count
        formatted_universes.sort(key=lambda u: (u['category'], -u['count']))

        response_time = (time.time() - start_time) * 1000

        response = {
            'universes': formatted_universes,
            'total_universes': len(formatted_universes),
            'performance': {
                'api_response_time_ms': round(response_time, 2),
                'source': 'cache_control'
            }
        }

        logger.debug("UNIVERSE-API: Retrieved %d universes - %.2f ms",
                    len(formatted_universes), response_time)

        return jsonify(response)

    except Exception as e:
        logger.error("UNIVERSE-API: Error getting universes: %s", e)
        return jsonify({
            'error': 'Failed to retrieve universes',
            'universes': []
        }), 500

@user_universe_bp.route('/api/users/universe/<universe_key>', methods=['GET'])
def get_universe_tickers(universe_key: str):
    """
    Get ticker list for a specific universe.
    
    Args:
        universe_key: Universe identifier
        
    Returns:
        JSON response with universe tickers
    """
    try:
        start_time = time.time()

        # Get cache control service
        cache_control = get_cache_control()
        if not cache_control:
            return jsonify({'error': 'Cache service unavailable'}), 503

        # Get universe tickers
        tickers = cache_control.get_universe_tickers(universe_key)
        metadata = cache_control.get_universe_metadata(universe_key)

        if not tickers:
            return jsonify({'error': f'Universe {universe_key} not found'}), 404

        response_time = (time.time() - start_time) * 1000

        response = {
            'universe_key': universe_key,
            'tickers': tickers,
            'count': len(tickers),
            'metadata': metadata,
            'performance': {
                'api_response_time_ms': round(response_time, 2),
                'source': 'cache_control'
            }
        }

        return jsonify(response)

    except Exception as e:
        logger.error("UNIVERSE-API: Error getting universe tickers for %s: %s", universe_key, e)
        return jsonify({'error': 'Failed to retrieve universe tickers'}), 500

@user_universe_bp.route('/api/users/watchlists', methods=['GET'])
def get_user_watchlists():
    """
    Get user's personal watchlists.
    TODO: Implement user watchlist storage in database.
    
    Returns:
        JSON response with user watchlists
    """
    try:
        user_id = get_current_user_id()

        # TODO: Query user watchlists from database
        # For now, return sample data
        sample_watchlists = [
            {
                'id': 1,
                'name': 'Tech Stocks',
                'symbols': ['AAPL', 'GOOGL', 'MSFT', 'TSLA'],
                'created_at': time.time() - 86400,  # 1 day ago
                'updated_at': time.time() - 3600    # 1 hour ago
            },
            {
                'id': 2,
                'name': 'High Momentum',
                'symbols': ['GME', 'AMC', 'NVDA'],
                'created_at': time.time() - 172800, # 2 days ago
                'updated_at': time.time() - 1800    # 30 minutes ago
            }
        ]

        return jsonify({
            'watchlists': sample_watchlists,
            'user_id': user_id,
            'count': len(sample_watchlists)
        })

    except Exception as e:
        logger.error("UNIVERSE-API: Error getting user watchlists: %s", e)
        return jsonify({'error': 'Failed to retrieve watchlists'}), 500

@user_universe_bp.route('/api/users/watchlists', methods=['POST'])
def create_user_watchlist():
    """
    Create new user watchlist.
    TODO: Implement user watchlist creation in database.
    
    Returns:
        JSON response with created watchlist
    """
    try:
        user_id = get_current_user_id()

        # Parse request data
        data = request.get_json()
        if not data:
            raise BadRequest("Request body is required")

        name = data.get('name', '').strip()
        symbols = data.get('symbols', [])

        if not name:
            raise BadRequest("Watchlist name is required")

        if not isinstance(symbols, list):
            raise BadRequest("Symbols must be a list")

        # Validate symbols (basic validation)
        symbols = [s.upper().strip() for s in symbols if s.strip()]

        # TODO: Store watchlist in database
        # For now, return sample response
        new_watchlist = {
            'id': int(time.time()),  # Simple ID generation
            'name': name,
            'symbols': symbols,
            'user_id': user_id,
            'created_at': time.time(),
            'updated_at': time.time()
        }

        return jsonify({
            'watchlist': new_watchlist,
            'message': f'Watchlist "{name}" created successfully'
        }), 201

    except BadRequest as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error("UNIVERSE-API: Error creating watchlist: %s", e)
        return jsonify({'error': 'Failed to create watchlist'}), 500

@user_universe_bp.route('/api/users/filter-presets', methods=['GET'])
def get_user_filter_presets():
    """
    Get user's saved filter presets for pattern scanning.
    TODO: Implement user filter preset storage in database.
    
    Returns:
        JSON response with user filter presets
    """
    try:
        user_id = get_current_user_id()

        # TODO: Query user filter presets from database
        # For now, return sample presets
        sample_presets = [
            {
                'id': 1,
                'name': 'High Confidence Breakouts',
                'filters': {
                    'pattern_types': ['Weekly_Breakout', 'Resistance_Break'],
                    'confidence_min': 0.8,
                    'rs_min': 1.2,
                    'vol_min': 1.5
                },
                'is_default': True,
                'created_at': time.time() - 86400
            },
            {
                'id': 2,
                'name': 'Volume Plays',
                'filters': {
                    'pattern_types': ['Volume_Spike'],
                    'confidence_min': 0.6,
                    'vol_min': 3.0
                },
                'is_default': False,
                'created_at': time.time() - 172800
            }
        ]

        return jsonify({
            'presets': sample_presets,
            'user_id': user_id,
            'count': len(sample_presets)
        })

    except Exception as e:
        logger.error("UNIVERSE-API: Error getting filter presets: %s", e)
        return jsonify({'error': 'Failed to retrieve filter presets'}), 500

@user_universe_bp.route('/api/users/filter-presets', methods=['POST'])
def create_user_filter_preset():
    """
    Create new user filter preset.
    TODO: Implement user filter preset creation in database.
    
    Returns:
        JSON response with created preset
    """
    try:
        user_id = get_current_user_id()

        # Parse request data
        data = request.get_json()
        if not data:
            raise BadRequest("Request body is required")

        name = data.get('name', '').strip()
        filters = data.get('filters', {})
        is_default = bool(data.get('is_default', False))

        if not name:
            raise BadRequest("Preset name is required")

        if not isinstance(filters, dict):
            raise BadRequest("Filters must be an object")

        # TODO: Store filter preset in database
        # For now, return sample response
        new_preset = {
            'id': int(time.time()),  # Simple ID generation
            'name': name,
            'filters': filters,
            'is_default': is_default,
            'user_id': user_id,
            'created_at': time.time()
        }

        return jsonify({
            'preset': new_preset,
            'message': f'Filter preset "{name}" created successfully'
        }), 201

    except BadRequest as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error("UNIVERSE-API: Error creating filter preset: %s", e)
        return jsonify({'error': 'Failed to create filter preset'}), 500

@user_universe_bp.route('/api/dashboard/stats', methods=['GET'])
def get_dashboard_stats():
    """
    Get basic statistics for dashboard display.
    Consumer database access: Read-only queries for UI metrics.
    
    Returns:
        JSON response with dashboard statistics
    """
    try:
        start_time = time.time()

        # Get database service
        tickstock_db = get_tickstock_db()
        if not tickstock_db:
            return jsonify({'error': 'Database service unavailable'}), 503

        # Get basic dashboard stats
        stats = tickstock_db.get_basic_dashboard_stats()

        response_time = (time.time() - start_time) * 1000
        stats['performance'] = {
            'api_response_time_ms': round(response_time, 2),
            'source': 'tickstock_database'
        }

        return jsonify(stats)

    except Exception as e:
        logger.error("UNIVERSE-API: Error getting dashboard stats: %s", e)
        return jsonify({'error': 'Failed to retrieve dashboard statistics'}), 500

@user_universe_bp.route('/api/health', methods=['GET'])
def get_api_health():
    """
    Health check endpoint for user universe API.
    
    Returns:
        JSON response with API health status
    """
    try:
        start_time = time.time()

        # Check database service
        tickstock_db = get_tickstock_db()
        db_healthy = tickstock_db is not None

        if db_healthy:
            try:
                # Quick database health check
                db_health = tickstock_db.health_check()
                db_healthy = db_health.get('status') == 'healthy'
            except Exception:
                db_healthy = False

        # Check cache service
        cache_control = get_cache_control()
        cache_healthy = cache_control is not None and cache_control._initialized

        # Determine overall health
        healthy = db_healthy and cache_healthy
        status = 'healthy' if healthy else 'degraded'

        response_time = (time.time() - start_time) * 1000

        health_info = {
            'status': status,
            'healthy': healthy,
            'services': {
                'tickstock_database': 'healthy' if db_healthy else 'error',
                'cache_control': 'healthy' if cache_healthy else 'error'
            },
            'performance': {
                'api_response_time_ms': round(response_time, 2)
            },
            'last_check': time.time()
        }

        return jsonify(health_info)

    except Exception as e:
        logger.error("UNIVERSE-API: Health check error: %s", e)
        return jsonify({
            'status': 'error',
            'healthy': False,
            'message': f'Health check failed: {str(e)}',
            'last_check': time.time()
        }), 500

# Blueprint error handlers
@user_universe_bp.errorhandler(400)
def bad_request(error):
    return jsonify({
        'error': 'Bad request',
        'message': str(error.description) if hasattr(error, 'description') else 'Invalid request'
    }), 400

@user_universe_bp.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Not found',
        'message': 'The requested resource does not exist'
    }), 404

@user_universe_bp.errorhandler(500)
def internal_error(error):
    logger.error("UNIVERSE-API: Internal error: %s", str(error))
    return jsonify({
        'error': 'Internal server error',
        'message': 'An unexpected error occurred'
    }), 500
