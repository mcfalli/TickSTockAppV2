"""
Analysis API routes.

Sprint 71: REST API Endpoints
Sprint 72: Database Integration
Endpoints for single symbol and universe batch analysis.
"""

import logging
import time
from datetime import datetime
from io import StringIO

import pandas as pd
from flask import Blueprint, request, jsonify
from pydantic import ValidationError

logger = logging.getLogger(__name__)

from src.api.models.analysis_models import (
    SymbolAnalysisRequest,
    SymbolAnalysisResponse,
    UniverseAnalysisRequest,
    UniverseAnalysisResponse,
    DataValidationRequest,
    DataValidationResponse,
    ErrorResponse,
)
from src.analysis.services.analysis_service import AnalysisService
from src.analysis.data.ohlcv_data_service import OHLCVDataService
from src.core.services.relationship_cache import get_relationship_cache
from src.analysis.exceptions import IndicatorError, PatternDetectionError, DataValidationError

# Create blueprint
analysis_bp = Blueprint('analysis', __name__, url_prefix='/api/analysis')


@analysis_bp.route('/symbol', methods=['POST'])
def analyze_symbol():
    """
    Analyze a single symbol with specified indicators and patterns.

    POST /api/analysis/symbol
    {
        "symbol": "AAPL",
        "timeframe": "daily",
        "indicators": ["sma", "rsi"],  # Optional, None = all
        "patterns": ["doji", "hammer"],  # Optional, None = all
        "calculate_all": false
    }

    Returns:
        200: SymbolAnalysisResponse
        400: ValidationError
        404: Symbol not found
        500: Analysis error
    """
    try:
        # Parse and validate request
        request_data = SymbolAnalysisRequest(**request.get_json())
    except ValidationError as e:
        return jsonify(ErrorResponse(
            error="ValidationError",
            message="Invalid request data",
            details={"validation_errors": e.errors()}
        ).model_dump()), 400

    start_time = time.time()

    try:
        # Get services
        analysis_service = AnalysisService()
        data_service = OHLCVDataService()

        # Fetch OHLCV data from database (last 200 bars for indicators)
        try:
            data = data_service.get_ohlcv_data(
                symbol=request_data.symbol,
                timeframe=request_data.timeframe,
                limit=250  # Extra bars for indicator warm-up
            )
        except ValueError as e:
            # Invalid timeframe
            return jsonify(ErrorResponse(
                error="ValidationError",
                message=str(e),
                details={'symbol': request_data.symbol, 'timeframe': request_data.timeframe}
            ).model_dump()), 400
        except RuntimeError as e:
            # Database error
            return jsonify(ErrorResponse(
                error="DatabaseError",
                message=f"Failed to fetch data: {str(e)}",
                details={'symbol': request_data.symbol}
            ).model_dump()), 500

        # Check if data exists
        if data.empty:
            return jsonify(ErrorResponse(
                error="NotFoundError",
                message=f"No data found for symbol '{request_data.symbol}' ({request_data.timeframe})",
                details={
                    'symbol': request_data.symbol,
                    'timeframe': request_data.timeframe,
                    'suggestion': 'Check if symbol exists or try a different timeframe'
                }
            ).model_dump()), 404

        # Determine which indicators/patterns to calculate
        if request_data.calculate_all:
            indicators_to_calc = None  # None = all
            patterns_to_calc = None
        else:
            indicators_to_calc = request_data.indicators
            patterns_to_calc = request_data.patterns

        # Perform analysis
        analysis_result = analysis_service.analyze_symbol(
            data=data,
            symbol=request_data.symbol,
            timeframe=request_data.timeframe,
            indicators=indicators_to_calc,
            patterns=patterns_to_calc
        )

        # Calculate metadata
        calculation_time_ms = (time.time() - start_time) * 1000

        # Build response
        response = SymbolAnalysisResponse(
            symbol=request_data.symbol,
            timeframe=request_data.timeframe,
            timestamp=datetime.utcnow(),
            indicators=analysis_result.get('indicators', {}),
            patterns=analysis_result.get('patterns', {}),
            metadata={
                'calculation_time_ms': round(calculation_time_ms, 2),
                'data_points': len(data),
                'indicators_calculated': len(analysis_result.get('indicators', {})),
                'patterns_detected': len(analysis_result.get('patterns', {})),
            }
        )

        return jsonify(response.model_dump()), 200

    except (IndicatorError, PatternDetectionError) as e:
        return jsonify(ErrorResponse(
            error="AnalysisError",
            message=f"Analysis failed: {str(e)}",
            details={'symbol': request_data.symbol}
        ).model_dump()), 500
    except Exception as e:
        return jsonify(ErrorResponse(
            error="InternalServerError",
            message=f"Unexpected error: {str(e)}",
            details={'symbol': request_data.symbol}
        ).model_dump()), 500


@analysis_bp.route('/universe', methods=['POST'])
def analyze_universe():
    """
    Analyze all symbols in a universe (batch analysis).

    POST /api/analysis/universe
    {
        "universe_key": "nasdaq100",
        "timeframe": "daily",
        "indicators": ["sma", "rsi"],
        "patterns": ["doji"],
        "max_symbols": 100,
        "calculate_all": false
    }

    Returns:
        200: UniverseAnalysisResponse
        400: ValidationError
        404: Universe not found
        500: Analysis error
    """
    try:
        # Parse and validate request
        request_data = UniverseAnalysisRequest(**request.get_json())
    except ValidationError as e:
        return jsonify(ErrorResponse(
            error="ValidationError",
            message="Invalid request data",
            details={"validation_errors": e.errors()}
        ).model_dump()), 400

    start_time = time.time()

    try:
        # Get universe symbols from RelationshipCache
        cache = get_relationship_cache()
        symbols = cache.get_universe_symbols(request_data.universe_key)

        if not symbols:
            return jsonify(ErrorResponse(
                error="NotFoundError",
                message=f"Universe '{request_data.universe_key}' not found or empty",
                details={'universe_key': request_data.universe_key}
            ).model_dump()), 404

        # Apply max_symbols limit
        if request_data.max_symbols:
            symbols = symbols[:request_data.max_symbols]

        # Get services
        analysis_service = AnalysisService()
        data_service = OHLCVDataService()

        # Batch fetch OHLCV data for all symbols (efficient single query)
        try:
            universe_data = data_service.get_universe_ohlcv_data(
                symbols=symbols,
                timeframe=request_data.timeframe,
                limit=250
            )
        except RuntimeError as e:
            return jsonify(ErrorResponse(
                error="DatabaseError",
                message=f"Failed to fetch universe data: {str(e)}",
                details={'universe_key': request_data.universe_key}
            ).model_dump()), 500

        # Batch analyze symbols
        results = {}
        cache_hits = 0
        cache_misses = 0

        # Summary statistics
        total_patterns = 0
        indicator_sums = {}

        for symbol in symbols:
            try:
                # Get data for this symbol
                data = universe_data.get(symbol)

                # Skip if no data available for symbol
                if data is None or data.empty:
                    logger.warning(f"No data for symbol {symbol}, skipping")
                    continue

                # Determine which indicators/patterns to calculate
                if request_data.calculate_all:
                    indicators_to_calc = None
                    patterns_to_calc = None
                else:
                    indicators_to_calc = request_data.indicators
                    patterns_to_calc = request_data.patterns

                # Analyze symbol
                analysis_result = analysis_service.analyze_symbol(
                    data=data,
                    symbol=symbol,
                    timeframe=request_data.timeframe,
                    indicators=indicators_to_calc,
                    patterns=patterns_to_calc
                )

                results[symbol] = {
                    'indicators': analysis_result.get('indicators', {}),
                    'patterns': analysis_result.get('patterns', {})
                }

                # Update summary statistics
                total_patterns += len(analysis_result.get('patterns', {}))

                # Aggregate indicator values
                for ind_name, ind_data in analysis_result.get('indicators', {}).items():
                    if ind_name not in indicator_sums:
                        indicator_sums[ind_name] = []
                    if 'value' in ind_data and ind_data['value'] is not None:
                        indicator_sums[ind_name].append(ind_data['value'])

                cache_hits += 1

            except Exception as e:
                # Log error but continue with other symbols
                results[symbol] = {
                    'error': str(e),
                    'indicators': {},
                    'patterns': {}
                }
                cache_misses += 1

        # Calculate summary statistics
        summary = {
            'total_patterns_detected': total_patterns,
            'symbols_with_errors': cache_misses,
        }

        # Add average indicator values
        for ind_name, values in indicator_sums.items():
            if values:
                summary[f'avg_{ind_name}'] = round(sum(values) / len(values), 2)

        # Calculate metadata
        calculation_time_ms = (time.time() - start_time) * 1000

        # Build response
        response = UniverseAnalysisResponse(
            universe_key=request_data.universe_key,
            timeframe=request_data.timeframe,
            timestamp=datetime.utcnow(),
            symbols_analyzed=len(symbols),
            results=results,
            summary=summary,
            metadata={
                'calculation_time_ms': round(calculation_time_ms, 2),
                'cache_hits': cache_hits,
                'cache_misses': cache_misses,
                'total_symbols': len(symbols)
            }
        )

        return jsonify(response.model_dump()), 200

    except Exception as e:
        return jsonify(ErrorResponse(
            error="InternalServerError",
            message=f"Universe analysis failed: {str(e)}",
            details={'universe_key': request_data.universe_key}
        ).model_dump()), 500


@analysis_bp.route('/validate-data', methods=['POST'])
def validate_data():
    """
    Validate OHLCV data format and consistency.

    POST /api/analysis/validate-data
    {
        "data": "timestamp,open,high,low,close,volume\\n...",
        "format": "csv"  # or "json"
    }

    Returns:
        200: DataValidationResponse
        400: ValidationError
    """
    try:
        # Parse and validate request
        request_data = DataValidationRequest(**request.get_json())
    except ValidationError as e:
        return jsonify(ErrorResponse(
            error="ValidationError",
            message="Invalid request data",
            details={"validation_errors": e.errors()}
        ).model_dump()), 400

    try:
        # Use AnalysisService to validate data
        analysis_service = AnalysisService()
        validation_result = analysis_service.validate_data(
            data_str=request_data.data,
            data_format=request_data.format,
        )

        # Build response
        response = DataValidationResponse(**validation_result)

        return jsonify(response.model_dump()), 200

    except Exception as e:
        return jsonify(ErrorResponse(
            error="ValidationError",
            message=f"Data validation failed: {str(e)}",
            details={'format': request_data.format}
        ).model_dump()), 400


# Health check endpoint
@analysis_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for analysis API.

    GET /api/analysis/health

    Returns:
        200: {"status": "healthy", "timestamp": "..."}
    """
    return jsonify({
        'status': 'healthy',
        'service': 'analysis',
        'timestamp': datetime.utcnow().isoformat()
    }), 200
