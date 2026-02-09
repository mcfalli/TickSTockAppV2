"""
Discovery API routes.

Sprint 71: REST API Endpoints
Endpoints for discovering available indicators, patterns, and capabilities.
"""

from datetime import datetime

from flask import Blueprint, jsonify

from src.api.models.analysis_models import (
    IndicatorsListResponse,
    PatternsListResponse,
    CapabilitiesResponse,
    ErrorResponse,
)
from src.analysis.indicators.loader import IndicatorLoader
from src.analysis.patterns.pattern_detection_service import PatternDetectionService

# Create blueprint
discovery_bp = Blueprint('discovery', __name__, url_prefix='/api')


@discovery_bp.route('/indicators/available', methods=['GET'])
def list_indicators():
    """
    List all available indicators grouped by category.

    GET /api/indicators/available

    Returns:
        200: IndicatorsListResponse
        {
            "indicators": {
                "trend": ["sma", "ema", "adx"],
                "momentum": ["rsi", "macd", "stochastic"],
                "volatility": ["atr", "bollinger_bands"]
            },
            "total_count": 8,
            "categories": ["trend", "momentum", "volatility"]
        }
    """
    try:
        # Get indicator loader
        loader = IndicatorLoader()

        # Get all registered indicators
        all_indicators = loader.get_available_indicators()

        # Group by category
        indicators_by_category = {}
        for ind_name, ind_info in all_indicators.items():
            category = ind_info.get('category', 'other')
            if category not in indicators_by_category:
                indicators_by_category[category] = []
            indicators_by_category[category].append(ind_name)

        # Sort categories and indicators
        for category in indicators_by_category:
            indicators_by_category[category].sort()

        # Build response
        response = IndicatorsListResponse(
            indicators=indicators_by_category,
            total_count=len(all_indicators),
            categories=sorted(indicators_by_category.keys())
        )

        return jsonify(response.model_dump()), 200

    except Exception as e:
        return jsonify(ErrorResponse(
            error="InternalServerError",
            message=f"Failed to list indicators: {str(e)}"
        ).model_dump()), 500


@discovery_bp.route('/patterns/available', methods=['GET'])
def list_patterns():
    """
    List all available patterns grouped by category.

    GET /api/patterns/available

    Returns:
        200: PatternsListResponse
        {
            "patterns": {
                "candlestick": ["doji", "hammer", "engulfing", ...]
            },
            "total_count": 8,
            "categories": ["candlestick"]
        }
    """
    try:
        # Get pattern detection service
        service = PatternDetectionService()

        # Get all registered patterns
        all_patterns = service.get_available_patterns()

        # Group by category (most patterns are candlestick for now)
        patterns_by_category = {
            'candlestick': []
        }

        for pattern_name in all_patterns.keys():
            # All current patterns are candlestick patterns
            # In future, could check pattern metadata for category
            patterns_by_category['candlestick'].append(pattern_name)

        # Sort patterns
        for category in patterns_by_category:
            patterns_by_category[category].sort()

        # Build response
        response = PatternsListResponse(
            patterns=patterns_by_category,
            total_count=len(all_patterns),
            categories=sorted(patterns_by_category.keys())
        )

        return jsonify(response.model_dump()), 200

    except Exception as e:
        return jsonify(ErrorResponse(
            error="InternalServerError",
            message=f"Failed to list patterns: {str(e)}"
        ).model_dump()), 500


@discovery_bp.route('/analysis/capabilities', methods=['GET'])
def get_capabilities():
    """
    Get analysis system capabilities and metadata.

    GET /api/analysis/capabilities

    Returns:
        200: CapabilitiesResponse
        {
            "version": "2.0.0",
            "indicators": {"trend": 3, "momentum": 3, "volatility": 2},
            "patterns": {"candlestick": 8},
            "supported_timeframes": [...],
            "performance_stats": {...}
        }
    """
    try:
        # Get indicator counts
        loader = IndicatorLoader()
        all_indicators = loader.get_available_indicators()

        indicator_counts = {}
        for ind_name, ind_info in all_indicators.items():
            category = ind_info.get('category', 'other')
            indicator_counts[category] = indicator_counts.get(category, 0) + 1

        # Get pattern counts
        service = PatternDetectionService()
        all_patterns = service.get_available_patterns()

        pattern_counts = {
            'candlestick': len(all_patterns)  # All patterns are candlestick for now
        }

        # Supported timeframes
        supported_timeframes = [
            'daily',
            'weekly',
            'hourly',
            'intraday',
            'monthly',
            '1min'
        ]

        # Performance stats (placeholder - would come from monitoring in production)
        performance_stats = {
            'avg_indicator_time_ms': 5.2,
            'avg_pattern_time_ms': 8.1,
            'cache_hit_rate': 0.92,
            'last_updated': datetime.utcnow().isoformat()
        }

        # Build response
        response = CapabilitiesResponse(
            version='2.0.0',  # TickStockAppV2 version
            indicators=indicator_counts,
            patterns=pattern_counts,
            supported_timeframes=supported_timeframes,
            performance_stats=performance_stats
        )

        return jsonify(response.model_dump()), 200

    except Exception as e:
        return jsonify(ErrorResponse(
            error="InternalServerError",
            message=f"Failed to get capabilities: {str(e)}"
        ).model_dump()), 500


# Health check endpoint
@discovery_bp.route('/discovery/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for discovery API.

    GET /api/discovery/health

    Returns:
        200: {"status": "healthy", "timestamp": "..."}
    """
    return jsonify({
        'status': 'healthy',
        'service': 'discovery',
        'timestamp': datetime.utcnow().isoformat()
    }), 200
