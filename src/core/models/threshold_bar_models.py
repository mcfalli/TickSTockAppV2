"""Sprint 64: Threshold Bar Models

Pydantic models for request/response validation in the threshold bars API.
Supports both Diverging Threshold Bar and Simple Diverging Bar visualizations.

Created: 2025-12-28
Purpose: Type-safe request/response models for threshold bar calculations
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

BarType = Literal["DivergingThresholdBar", "SimpleDivergingBar"]
Timeframe = Literal["1min", "hourly", "daily", "weekly", "monthly"]


class ThresholdBarRequest(BaseModel):
    """Request model for threshold bar calculation.

    Validates input parameters for the /api/threshold-bars endpoint.
    """

    data_source: str = Field(
        ...,
        description=(
            "Data source identifier: universe key (e.g., 'sp500'), "
            "ETF symbol (e.g., 'SPY'), or multi-universe join (e.g., 'sp500:nasdaq100')"
        ),
        min_length=1,
        max_length=200,
    )

    bar_type: BarType = Field(
        default="DivergingThresholdBar",
        description=(
            "Type of threshold bar: 'DivergingThresholdBar' (4 segments) or "
            "'SimpleDivergingBar' (2 segments)"
        ),
    )

    timeframe: Timeframe = Field(
        default="daily",
        description="OHLCV data timeframe: '1min', 'hourly', 'daily', 'weekly', or 'monthly'",
    )

    threshold: float = Field(
        default=0.10,
        description="Sensitivity threshold for significant moves (0.0-1.0). Default 0.10 = 10%",
        ge=0.0,
        le=1.0,
    )

    period_days: int = Field(
        default=1,
        description="Number of days to look back for percentage change calculation",
        ge=1,
        le=365,
    )

    @field_validator("data_source")
    @classmethod
    def validate_data_source(cls, v: str) -> str:
        """Validate data_source is not empty or whitespace-only."""
        if not v or not v.strip():
            raise ValueError("data_source cannot be empty or whitespace")
        return v.strip()


class ThresholdBarMetadata(BaseModel):
    """Metadata about the threshold bar calculation."""

    data_source: str = Field(..., description="Data source used for calculation")
    bar_type: BarType = Field(..., description="Type of threshold bar calculated")
    timeframe: Timeframe = Field(..., description="OHLCV timeframe used")
    threshold: float = Field(..., description="Threshold value used (0.0-1.0)")
    period_days: int = Field(..., description="Period in days for calculation")
    symbol_count: int = Field(..., description="Number of symbols included in calculation")
    calculated_at: str = Field(..., description="ISO timestamp of calculation")


class DivergingThresholdBarSegments(BaseModel):
    """Segment percentages for Diverging Threshold Bar (4 segments).

    Percentages represent distribution of symbols across 4 threshold zones.
    Sum of all percentages must equal 100.0.
    """

    significant_decline: float = Field(
        ...,
        description="Percentage of symbols with x < -threshold",
        ge=0.0,
        le=100.0,
    )

    minor_decline: float = Field(
        ...,
        description="Percentage of symbols with -threshold <= x < 0",
        ge=0.0,
        le=100.0,
    )

    minor_advance: float = Field(
        ...,
        description="Percentage of symbols with 0 <= x < threshold",
        ge=0.0,
        le=100.0,
    )

    significant_advance: float = Field(
        ...,
        description="Percentage of symbols with x >= threshold",
        ge=0.0,
        le=100.0,
    )

    @field_validator("*", mode="after")
    @classmethod
    def validate_percentage_range(cls, v: float) -> float:
        """Ensure percentage is in valid range [0, 100]."""
        if not 0.0 <= v <= 100.0:
            raise ValueError(f"Percentage must be between 0 and 100, got {v}")
        return v

    def validate_sum(self) -> bool:
        """Validate that all percentages sum to 100%.

        Returns:
            bool: True if sum is 100% (within 0.01% tolerance)
        """
        total = (
            self.significant_decline
            + self.minor_decline
            + self.minor_advance
            + self.significant_advance
        )
        return abs(total - 100.0) < 0.01


class SimpleDivergingBarSegments(BaseModel):
    """Segment percentages for Simple Diverging Bar (2 segments).

    Percentages represent distribution of symbols across positive/negative zones.
    Sum of all percentages must equal 100.0.
    """

    decline: float = Field(
        ...,
        description="Percentage of symbols with x < 0 (negative change)",
        ge=0.0,
        le=100.0,
    )

    advance: float = Field(
        ...,
        description="Percentage of symbols with x >= 0 (positive change)",
        ge=0.0,
        le=100.0,
    )

    @field_validator("*", mode="after")
    @classmethod
    def validate_percentage_range(cls, v: float) -> float:
        """Ensure percentage is in valid range [0, 100]."""
        if not 0.0 <= v <= 100.0:
            raise ValueError(f"Percentage must be between 0 and 100, got {v}")
        return v

    def validate_sum(self) -> bool:
        """Validate that all percentages sum to 100%.

        Returns:
            bool: True if sum is 100% (within 0.01% tolerance)
        """
        total = self.decline + self.advance
        return abs(total - 100.0) < 0.01


class ThresholdBarResponse(BaseModel):
    """Response model for threshold bar calculation.

    Returns metadata and segment percentages.
    Segment structure varies based on bar_type.
    """

    metadata: ThresholdBarMetadata = Field(..., description="Calculation metadata")
    segments: dict[str, float] = Field(..., description="Segment percentages (sum = 100%)")

    @field_validator("segments")
    @classmethod
    def validate_segments_sum(cls, v: dict[str, float]) -> dict[str, float]:
        """Validate that segment percentages sum to 100%."""
        total = sum(v.values())
        if abs(total - 100.0) > 0.01:
            raise ValueError(f"Segment percentages must sum to 100%, got {total:.2f}%")
        return v

    @classmethod
    def from_service_response(cls, service_data: dict[str, Any]) -> "ThresholdBarResponse":
        """Create ThresholdBarResponse from service layer dict.

        Args:
            service_data: Dictionary from ThresholdBarService.calculate_threshold_bars()

        Returns:
            ThresholdBarResponse: Validated response model

        Raises:
            ValidationError: If service_data is invalid
        """
        return cls(
            metadata=ThresholdBarMetadata(**service_data["metadata"]),
            segments=service_data["segments"],
        )


class ThresholdBarErrorResponse(BaseModel):
    """Error response model for threshold bar API failures."""

    error: str = Field(..., description="Error type identifier")
    message: str = Field(..., description="Human-readable error message")
    details: dict[str, Any] | None = Field(None, description="Additional error context")
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="ISO timestamp of error",
    )

    @classmethod
    def create(
        cls, error: str, message: str, details: dict[str, Any] | None = None
    ) -> "ThresholdBarErrorResponse":
        """Create error response with auto-generated timestamp.

        Args:
            error: Error type identifier (e.g., 'ValueError', 'DatabaseError')
            message: Human-readable error message
            details: Optional additional error context

        Returns:
            ThresholdBarErrorResponse: Error response model
        """
        return cls(error=error, message=message, details=details)


# Validation helpers
def validate_bar_type(bar_type: str) -> bool:
    """Validate if bar_type is one of the supported types.

    Args:
        bar_type: Bar type string to validate

    Returns:
        bool: True if valid bar type
    """
    return bar_type in ["DivergingThresholdBar", "SimpleDivergingBar"]


def validate_timeframe(timeframe: str) -> bool:
    """Validate if timeframe is one of the supported timeframes.

    Args:
        timeframe: Timeframe string to validate

    Returns:
        bool: True if valid timeframe
    """
    return timeframe in ["1min", "hourly", "daily", "weekly", "monthly"]
