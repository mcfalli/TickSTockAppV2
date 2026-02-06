"""Threshold Bars API - Sprint 64

Provides threshold bar calculations for market sentiment visualization.
Supports both Diverging Threshold Bar and Simple Diverging Bar types.

Endpoints:
- GET /api/threshold-bars - Calculate threshold bar segments
"""

import logging

from flask import Blueprint, jsonify, request
from flask_login import login_required
from pydantic import ValidationError

from src.core.models.threshold_bar_models import (
    ThresholdBarErrorResponse,
    ThresholdBarRequest,
    ThresholdBarResponse,
)
from src.core.services.threshold_bar_service import ThresholdBarService

logger = logging.getLogger(__name__)

threshold_bars_bp = Blueprint("threshold_bars", __name__)


@threshold_bars_bp.route("/api/threshold-bars", methods=["GET"])
# NOTE: Authentication can be added later if needed
# @login_required
def get_threshold_bars():
    """Calculate threshold bar segments for given parameters.

    Query Parameters:
        data_source (str): Universe key (e.g., 'sp500'), ETF symbol (e.g., 'SPY'),
                          or multi-universe join (e.g., 'sp500:nasdaq100')
        bar_type (str): 'DivergingThresholdBar' or 'SimpleDivergingBar'
                       (default: 'DivergingThresholdBar')
        timeframe (str): '1min', 'hourly', 'daily', 'weekly', or 'monthly'
                        (default: 'daily')
        threshold (float): Threshold value between 0.0 and 1.0
                          (default: 0.10 = 10%)
        period_days (int): Number of days to look back (1-365)
                          (default: 1)

    Returns:
        JSON response with structure:
        {
            "metadata": {
                "data_source": str,
                "bar_type": str,
                "timeframe": str,
                "threshold": float,
                "period_days": int,
                "symbol_count": int,
                "calculated_at": str (ISO timestamp)
            },
            "segments": {
                "significant_decline": float,
                "minor_decline": float,
                "minor_advance": float,
                "significant_advance": float
            }
        }

        For SimpleDivergingBar, segments only contains:
        {
            "decline": float,
            "advance": float
        }

    Error Responses:
        400: Invalid request parameters (validation failed)
        500: Server error during calculation
    """
    try:
        # Extract and validate query parameters
        request_data = ThresholdBarRequest(
            data_source=request.args.get("data_source", ""),
            bar_type=request.args.get("bar_type", "DivergingThresholdBar"),
            timeframe=request.args.get("timeframe", "daily"),
            threshold=float(request.args.get("threshold", 0.10)),
            period_days=int(request.args.get("period_days", 1)),
        )

        logger.info(
            f"Threshold bar request: {request_data.data_source} "
            f"(type={request_data.bar_type}, timeframe={request_data.timeframe})"
        )

        # Calculate threshold bars
        service = ThresholdBarService()
        result = service.calculate_threshold_bars(
            data_source=request_data.data_source,
            bar_type=request_data.bar_type,
            timeframe=request_data.timeframe,
            threshold=request_data.threshold,
            period_days=request_data.period_days,
        )

        # Validate response
        response = ThresholdBarResponse.from_service_response(result)

        logger.info(
            f"Threshold bar calculated: {request_data.data_source} "
            f"({result['metadata']['symbol_count']} symbols)"
        )

        return jsonify(response.model_dump()), 200

    except ValidationError as e:
        # Pydantic validation errors (invalid parameters)
        logger.warning(f"Threshold bar validation error: {e}")
        error_response = ThresholdBarErrorResponse.create(
            error="ValidationError",
            message="Invalid request parameters",
            details={"validation_errors": e.errors()},
        )
        return jsonify(error_response.model_dump()), 400

    except ValueError as e:
        # Service-level validation errors (e.g., invalid data_source)
        logger.warning(f"Threshold bar value error: {e}")
        error_response = ThresholdBarErrorResponse.create(error="ValueError", message=str(e))
        return jsonify(error_response.model_dump()), 400

    except RuntimeError as e:
        # Service-level runtime errors (e.g., no symbols found, no data)
        logger.error(f"Threshold bar runtime error: {e}")
        error_response = ThresholdBarErrorResponse.create(error="RuntimeError", message=str(e))
        return jsonify(error_response.model_dump()), 500

    except Exception as e:
        # Unexpected errors
        logger.error(f"Unexpected error in threshold bars endpoint: {e}", exc_info=True)
        error_response = ThresholdBarErrorResponse.create(
            error="ServerError", message="An unexpected error occurred"
        )
        return jsonify(error_response.model_dump()), 500
