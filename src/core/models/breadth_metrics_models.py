"""Sprint 66: Breadth Metrics Models

Pydantic v2 models for request/response validation in the breadth metrics API.
Supports market breadth calculations across 12 metrics for any stock universe.

Created: 2026-02-07
Purpose: Type-safe request/response models for breadth metrics calculations
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

# Type aliases
UniverseKey = str  # 'SPY', 'QQQ', 'dow30', 'sp500', etc.


class BreadthMetricsRequest(BaseModel):
    """Request model for breadth metrics calculation.

    Validates query parameters from Flask request.args.
    """

    universe: UniverseKey = Field(
        default="SPY",
        description="Universe key (e.g., 'SPY', 'QQQ', 'dow30', 'nasdaq100')",
        min_length=1,
        max_length=50,
    )

    @field_validator("universe")
    @classmethod
    def validate_universe(cls, v: str) -> str:
        """Validate universe is not empty or whitespace."""
        if not v or not v.strip():
            raise ValueError("universe cannot be empty or whitespace")
        return v.strip().upper()


class MetricData(BaseModel):
    """Single breadth metric data (up/down counts + percentage).

    Example: Day Change metric shows 345 up, 159 down, 68.5% up.
    """

    up: int = Field(ge=0, description="Count of stocks up/above")
    down: int = Field(ge=0, description="Count of stocks down/below")
    unchanged: int = Field(ge=0, description="Count of stocks unchanged")
    pct_up: float = Field(ge=0.0, le=100.0, description="Percentage up/above")

    @field_validator("pct_up")
    @classmethod
    def validate_percentage(cls, v: float) -> float:
        """Ensure percentage is within valid range."""
        if not (0.0 <= v <= 100.0):
            raise ValueError(f"pct_up must be 0-100, got {v}")
        return round(v, 2)


class BreadthMetricsMetadata(BaseModel):
    """Metadata for breadth metrics response.

    Enables client validation, debugging, and display formatting.
    """

    universe: UniverseKey
    symbol_count: int = Field(ge=0, description="Number of symbols analyzed")
    calculation_time_ms: float = Field(ge=0.0, description="Calculation duration in milliseconds")
    calculated_at: str = Field(description="ISO 8601 timestamp")

    @field_validator("calculated_at")
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        """Validate ISO 8601 timestamp format."""
        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
            return v
        except ValueError as e:
            raise ValueError(f"Invalid ISO 8601 timestamp: {v}") from e


class BreadthMetricsResponse(BaseModel):
    """Complete breadth metrics API response.

    Structure:
    {
        "metrics": {
            "day_change": {"up": 345, "down": 159, "unchanged": 0, "pct_up": 68.5},
            "week": {"up": 390, "down": 114, "unchanged": 0, "pct_up": 77.4},
            ...
        },
        "metadata": {
            "universe": "SPY",
            "symbol_count": 504,
            "calculation_time_ms": 42.3,
            "calculated_at": "2026-02-07T14:45:00.123456"
        }
    }
    """

    metrics: dict[str, MetricData]
    metadata: BreadthMetricsMetadata

    @field_validator("metrics")
    @classmethod
    def validate_metrics_keys(cls, v: dict[str, MetricData]) -> dict[str, MetricData]:
        """Validate all expected metrics present."""
        expected_keys = {
            "day_change",
            "open_change",
            "week",
            "month",
            "quarter",
            "half_year",
            "year",
            "price_to_ema10",
            "price_to_ema20",
            "price_to_sma50",
            "price_to_sma200",
        }
        missing_keys = expected_keys - set(v.keys())
        if missing_keys:
            raise ValueError(f"Missing metrics: {missing_keys}")
        return v

    @classmethod
    def from_service_response(cls, service_data: dict[str, Any]) -> "BreadthMetricsResponse":
        """Factory method to create response from service layer dict.

        Args:
            service_data: Dictionary from BreadthMetricsService.calculate_breadth_metrics()

        Returns:
            Validated BreadthMetricsResponse instance
        """
        return cls(
            metrics=service_data["metrics"],
            metadata=BreadthMetricsMetadata(**service_data["metadata"]),
        )


class BreadthMetricsErrorResponse(BaseModel):
    """Standardized error response model.

    Used for 400 (validation errors) and 500 (server errors).
    """

    error: str = Field(
        description="Error type (ValidationError, ValueError, RuntimeError, ServerError)"
    )
    message: str = Field(description="Human-readable error message")
    details: dict[str, Any] | None = Field(default=None, description="Additional error context")

    @classmethod
    def create(
        cls, error: str, message: str, details: dict[str, Any] | None = None
    ) -> "BreadthMetricsErrorResponse":
        """Factory method for creating error responses."""
        return cls(error=error, message=message, details=details or {})
