"""Stock Groups API - Sprint 65

Provides filterable list of stock groups (ETFs, sectors, themes, universes)
from definition_groups table. Supports search and type filtering for
dynamic UI population.

Endpoints:
- GET /api/stock-groups - Get filterable stock groups list
"""

import logging
from datetime import datetime

from flask import Blueprint, jsonify, request
from flask_login import login_required
from pydantic import BaseModel, Field, ValidationError

from src.core.services.relationship_cache import get_relationship_cache

logger = logging.getLogger(__name__)

stock_groups_bp = Blueprint("stock_groups", __name__)


# Pydantic Models
class StockGroupMetadata(BaseModel):
    """Metadata for a single stock group."""

    name: str = Field(..., description="Group name (e.g., 'SPY', 'information_technology')")
    type: str = Field(..., description="Group type: ETF, SECTOR, THEME, UNIVERSE")
    description: str | None = Field(None, description="Human-readable description")
    member_count: int = Field(..., description="Number of stocks in group")
    environment: str = Field(..., description="Environment: DEFAULT, TEST, UAT, PROD")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    # Optional metadata (not in database, computed if needed)
    avg_market_cap: str | None = Field(None, description="Average market cap (future)")
    ytd_performance: str | None = Field(None, description="YTD performance (future)")
    volatility: str | None = Field(None, description="Volatility level (future)")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class StockGroupsResponse(BaseModel):
    """API response for /api/stock-groups endpoint."""

    groups: list[StockGroupMetadata]
    total_count: int
    types: list[str]  # Unique types in response
    environment: str

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


@stock_groups_bp.route("/api/stock-groups", methods=["GET"])
# NOTE: Authentication can be added later if needed
# @login_required
def get_stock_groups():
    """Get filterable list of stock groups (ETFs, sectors, themes, universes).

    Query Parameters:
        types (str): Comma-separated list (default: 'ETF,SECTOR,THEME,UNIVERSE')
        search (str): Search term for name/description (optional)

    Returns:
        JSON response with structure:
        {
            "groups": [
                {
                    "name": str,
                    "type": str,
                    "description": str,
                    "member_count": int,
                    "environment": str,
                    "created_at": str (ISO timestamp),
                    "updated_at": str (ISO timestamp)
                },
                ...
            ],
            "total_count": int,
            "types": [str, ...],
            "environment": str
        }

    Error Responses:
        400: Invalid type parameter (validation failed)
        500: Server error during data retrieval
    """
    try:
        # Parse query parameters
        types_param = request.args.get("types", "ETF,SECTOR,THEME,UNIVERSE")
        search_term = request.args.get("search", None)

        # Convert comma-separated types to list
        types_list = [t.strip().upper() for t in types_param.split(",") if t.strip()]

        # Validate types
        valid_types = {"ETF", "SECTOR", "THEME", "UNIVERSE", "SEGMENT", "CUSTOM"}
        if not all(t in valid_types for t in types_list):
            return (
                jsonify(
                    {
                        "error": "Invalid type parameter",
                        "valid_types": list(valid_types),
                    }
                ),
                400,
            )

        # Get data from RelationshipCache
        cache = get_relationship_cache()
        groups_data = cache.get_available_universes(types=types_list)

        # Apply search filter (server-side, case-insensitive)
        if search_term:
            search_lower = search_term.lower()
            groups_data = [
                g
                for g in groups_data
                if search_lower in g["name"].lower()
                or (g.get("description") and search_lower in g["description"].lower())
                or search_lower in g["type"].lower()
            ]

        # Build response
        response = StockGroupsResponse(
            groups=[StockGroupMetadata(**g) for g in groups_data],
            total_count=len(groups_data),
            types=types_list,
            environment="DEFAULT",
        )

        # Use mode='json' to apply json_encoders (converts datetime to ISO format)
        return jsonify(response.model_dump(mode="json")), 200

    except ValidationError as e:
        logger.error(f"Validation error in get_stock_groups: {e}")
        return jsonify({"error": "Validation error", "details": str(e)}), 400

    except Exception as e:
        logger.error(f"Error in get_stock_groups: {e}", exc_info=True)
        return jsonify({"error": "Internal server error", "message": str(e)}), 500
