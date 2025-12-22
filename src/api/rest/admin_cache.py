"""
Admin Cache Management API - Sprint 60 Phase 2.2

Endpoints for managing the RelationshipCache:
- GET  /admin/cache/stats - Cache statistics
- POST /admin/cache/refresh - Invalidate and refresh cache
- POST /admin/cache/warm - Pre-populate cache with common queries
"""

from flask import Blueprint, jsonify, request
from src.utils.auth_decorators import admin_required
from src.core.services.relationship_cache import get_relationship_cache
import logging

logger = logging.getLogger(__name__)

admin_cache_bp = Blueprint('admin_cache', __name__)


@admin_cache_bp.route('/admin/cache/stats', methods=['GET'])
@admin_required
def get_cache_stats():
    """
    Get cache statistics

    Returns:
        JSON with cache hit/miss rates, sizes, etc.
    """
    try:
        cache = get_relationship_cache()
        stats = cache.get_stats()

        return jsonify({
            'success': True,
            'stats': stats
        }), 200

    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_cache_bp.route('/admin/cache/refresh', methods=['POST'])
@admin_required
def refresh_cache():
    """
    Invalidate cache and optionally refresh

    Request body (optional):
        {
            "cache_type": "etf|sector|theme|universe|all",
            "key": "specific_key",
            "warm": true
        }

    Returns:
        JSON with success status
    """
    try:
        cache = get_relationship_cache()
        data = request.get_json() or {}

        cache_type = data.get('cache_type', 'all')
        key = data.get('key')
        warm = data.get('warm', False)

        # Invalidate cache
        cache.invalidate(cache_type=cache_type, key=key)

        # Optionally warm cache
        if warm and cache_type == 'all':
            cache.warm_cache()

        return jsonify({
            'success': True,
            'message': f"Cache refreshed: {cache_type}/{key or 'all'}",
            'warmed': warm
        }), 200

    except Exception as e:
        logger.error(f"Error refreshing cache: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_cache_bp.route('/admin/cache/warm', methods=['POST'])
@admin_required
def warm_cache():
    """
    Pre-populate cache with common queries

    Returns:
        JSON with success status and warm time
    """
    try:
        cache = get_relationship_cache()

        import time
        start_time = time.time()
        cache.warm_cache()
        elapsed = time.time() - start_time

        stats = cache.get_stats()

        return jsonify({
            'success': True,
            'message': 'Cache warmed successfully',
            'elapsed_seconds': round(elapsed, 2),
            'stats': stats
        }), 200

    except Exception as e:
        logger.error(f"Error warming cache: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_cache_bp.route('/admin/cache/test', methods=['GET'])
@admin_required
def test_cache():
    """
    Test cache performance with sample queries

    Returns:
        JSON with performance test results
    """
    try:
        cache = get_relationship_cache()
        import time

        results = {}

        # Test ETF holdings
        start = time.time()
        holdings = cache.get_etf_holdings('SPY')
        elapsed_ms = (time.time() - start) * 1000
        results['etf_holdings'] = {
            'query': 'SPY holdings',
            'count': len(holdings),
            'elapsed_ms': round(elapsed_ms, 2),
            'cached': False
        }

        # Test cached query
        start = time.time()
        holdings2 = cache.get_etf_holdings('SPY')
        elapsed_ms = (time.time() - start) * 1000
        results['etf_holdings_cached'] = {
            'query': 'SPY holdings (cached)',
            'count': len(holdings2),
            'elapsed_ms': round(elapsed_ms, 2),
            'cached': True
        }

        # Test stock sector
        start = time.time()
        sector = cache.get_stock_sector('AAPL')
        elapsed_ms = (time.time() - start) * 1000
        results['stock_sector'] = {
            'query': 'AAPL sector',
            'result': sector,
            'elapsed_ms': round(elapsed_ms, 2)
        }

        # Test all ETFs
        start = time.time()
        etfs = cache.get_all_etfs()
        elapsed_ms = (time.time() - start) * 1000
        results['all_etfs'] = {
            'query': 'All ETFs',
            'count': len(etfs),
            'elapsed_ms': round(elapsed_ms, 2)
        }

        stats = cache.get_stats()

        return jsonify({
            'success': True,
            'results': results,
            'stats': stats
        }), 200

    except Exception as e:
        logger.error(f"Error testing cache: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
