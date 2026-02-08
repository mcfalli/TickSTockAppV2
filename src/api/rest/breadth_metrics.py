"""Breadth Metrics API - Sprint 66

Provides market breadth calculations for participation analysis.
Supports 12 metrics across time periods and moving averages for any universe.

Endpoints:
- GET /api/breadth-metrics - Calculate breadth metrics for universe
"""

import logging

from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from src.core.models.breadth_metrics_models import (
    BreadthMetricsErrorResponse,
    BreadthMetricsRequest,
    BreadthMetricsResponse,
)
from src.core.services.breadth_metrics_service import BreadthMetricsService

logger = logging.getLogger(__name__)

breadth_metrics_bp = Blueprint("breadth_metrics", __name__)


@breadth_metrics_bp.route("/api/breadth-metrics", methods=["GET"])
# NOTE: Authentication can be added later if needed
# @login_required
def get_breadth_metrics():
    """Calculate market breadth metrics for given universe.

    Query Parameters:
        universe (str): Universe key (e.g., 'SPY', 'QQQ', 'dow30', 'nasdaq100')
                       (default: 'SPY')

    Returns:
        JSON response with structure:
        {
            "metrics": {
                "day_change": {"up": 345, "down": 159, "unchanged": 0, "pct_up": 68.5},
                "open_change": {...},
                "week": {...},
                "month": {...},
                "quarter": {...},
                "half_year": {...},
                "year": {...},
                "price_to_ema10": {...},
                "price_to_ema20": {...},
                "price_to_sma50": {...},
                "price_to_sma200": {...}
            },
            "metadata": {
                "universe": "SPY",
                "symbol_count": 504,
                "calculation_time_ms": 42.3,
                "calculated_at": "2026-02-07T14:45:00.123456"
            }
        }

    Error Responses:
        400: Invalid request parameters (validation failed)
        500: Server error during calculation

    Example:
        GET /api/breadth-metrics?universe=SPY
    """
    try:
        # Extract and validate query parameters
        request_data = BreadthMetricsRequest(universe=request.args.get("universe", "SPY"))

        logger.info(f"Breadth metrics request: {request_data.universe}")

        # Calculate metrics
        service = BreadthMetricsService()
        result = service.calculate_breadth_metrics(universe=request_data.universe)

        # Validate response
        response = BreadthMetricsResponse.from_service_response(result)

        return jsonify(response.model_dump()), 200

    except ValidationError as e:
        # Pydantic validation errors (invalid parameters)
        logger.warning(f"Breadth metrics validation error: {e}")
        error_response = BreadthMetricsErrorResponse.create(
            error="ValidationError",
            message="Invalid request parameters",
            details={"validation_errors": e.errors()},
        )
        return jsonify(error_response.model_dump()), 400

    except ValueError as e:
        # Service-level validation errors
        logger.warning(f"Breadth metrics value error: {e}")
        error_response = BreadthMetricsErrorResponse.create(
            error="ValueError",
            message=str(e),
        )
        return jsonify(error_response.model_dump()), 400

    except RuntimeError as e:
        # Service-level runtime errors (no data, query failure)
        logger.error(f"Breadth metrics runtime error: {e}")
        error_response = BreadthMetricsErrorResponse.create(
            error="RuntimeError",
            message=str(e),
        )
        return jsonify(error_response.model_dump()), 500

    except Exception as e:
        # Unexpected errors
        logger.error(f"Unexpected error in breadth metrics endpoint: {e}", exc_info=True)
        error_response = BreadthMetricsErrorResponse.create(
            error="ServerError",
            message="An unexpected error occurred",
        )
        return jsonify(error_response.model_dump()), 500
