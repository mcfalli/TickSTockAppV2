"""
Pydantic models for analysis API endpoints.

Sprint 71: REST API Endpoints
Request/response validation models using Pydantic v2.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, ConfigDict, field_validator


class SymbolAnalysisRequest(BaseModel):
    """Request model for single symbol analysis."""

    symbol: str = Field(..., min_length=1, max_length=10, description="Stock symbol to analyze")
    timeframe: str = Field(
        default="daily",
        pattern="^(daily|weekly|hourly|intraday|monthly|1min)$",
        description="Timeframe for analysis"
    )
    indicators: list[str] | None = Field(
        default=None,
        description="List of indicator names to calculate (None = all)"
    )
    patterns: list[str] | None = Field(
        default=None,
        description="List of pattern names to detect (None = all)"
    )
    calculate_all: bool = Field(
        default=False,
        description="If True, calculate all indicators and patterns"
    )

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator('symbol')
    @classmethod
    def symbol_uppercase(cls, v: str) -> str:
        """Convert symbol to uppercase."""
        return v.upper()


class SymbolAnalysisResponse(BaseModel):
    """Response model for single symbol analysis."""

    symbol: str
    timeframe: str
    timestamp: datetime
    indicators: dict[str, Any] = Field(description="Calculated indicator values")
    patterns: dict[str, Any] = Field(description="Detected pattern results")
    metadata: dict[str, Any] = Field(description="Analysis metadata")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "symbol": "AAPL",
                "timeframe": "daily",
                "timestamp": "2026-02-09T12:00:00",
                "indicators": {
                    "sma": {"value": 150.5, "value_data": {"sma_20": 150.5}},
                    "rsi": {"value": 65.3, "value_data": {"rsi_14": 65.3}}
                },
                "patterns": {
                    "doji": {"detected": True, "confidence": 0.85}
                },
                "metadata": {
                    "calculation_time_ms": 12.5,
                    "data_points": 100,
                    "indicators_calculated": 2,
                    "patterns_detected": 1
                }
            }
        }
    )


class UniverseAnalysisRequest(BaseModel):
    """Request model for universe batch analysis."""

    universe_key: str = Field(..., min_length=1, description="Universe key (nasdaq100, SPY, etc.)")
    timeframe: str = Field(default="daily", pattern="^(daily|weekly|hourly|intraday|monthly|1min)$")
    indicators: list[str] | None = None
    patterns: list[str] | None = None
    max_symbols: int | None = Field(default=None, ge=1, le=1000, description="Limit number of symbols")
    calculate_all: bool = False

    model_config = ConfigDict(str_strip_whitespace=True)


class UniverseAnalysisResponse(BaseModel):
    """Response model for universe batch analysis."""

    universe_key: str
    timeframe: str
    timestamp: datetime
    symbols_analyzed: int
    results: dict[str, dict[str, Any]] = Field(description="Analysis results per symbol")
    summary: dict[str, Any] = Field(description="Aggregate statistics")
    metadata: dict[str, Any]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "universe_key": "nasdaq100",
                "timeframe": "daily",
                "timestamp": "2026-02-09T12:00:00",
                "symbols_analyzed": 102,
                "results": {
                    "AAPL": {"indicators": {}, "patterns": {}},
                    "MSFT": {"indicators": {}, "patterns": {}}
                },
                "summary": {
                    "avg_rsi": 58.5,
                    "patterns_detected": 25,
                    "overbought_count": 10,
                    "oversold_count": 5
                },
                "metadata": {
                    "calculation_time_ms": 1850.5,
                    "cache_hits": 95,
                    "cache_misses": 7
                }
            }
        }
    )


class DataValidationRequest(BaseModel):
    """Request model for OHLCV data validation."""

    data: str = Field(..., min_length=1, description="CSV or JSON data string")
    format: str = Field(default="csv", pattern="^(csv|json)$", description="Data format")

    model_config = ConfigDict(str_strip_whitespace=True)


class DataValidationResponse(BaseModel):
    """Response model for data validation."""

    is_valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    data_points: int = 0
    columns_found: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "is_valid": True,
                "errors": [],
                "warnings": ["Volume column missing for 5 rows"],
                "data_points": 100,
                "columns_found": ["timestamp", "open", "high", "low", "close", "volume"],
                "metadata": {
                    "ohlc_consistency": True,
                    "nan_count": 0,
                    "date_range": "2025-01-01 to 2025-04-10"
                }
            }
        }
    )


class IndicatorsListResponse(BaseModel):
    """Response model for available indicators list."""

    indicators: dict[str, list[str]] = Field(description="Indicators grouped by category")
    total_count: int
    categories: list[str]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "indicators": {
                    "trend": ["sma", "ema", "adx"],
                    "momentum": ["rsi", "macd", "stochastic"],
                    "volatility": ["atr", "bollinger_bands"]
                },
                "total_count": 8,
                "categories": ["trend", "momentum", "volatility"]
            }
        }
    )


class PatternsListResponse(BaseModel):
    """Response model for available patterns list."""

    patterns: dict[str, list[str]] = Field(description="Patterns grouped by category")
    total_count: int
    categories: list[str]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "patterns": {
                    "candlestick": ["doji", "hammer", "engulfing", "shooting_star", "hanging_man", "harami", "morning_star", "evening_star"]
                },
                "total_count": 8,
                "categories": ["candlestick"]
            }
        }
    )


class CapabilitiesResponse(BaseModel):
    """Response model for analysis system capabilities."""

    version: str
    indicators: dict[str, int] = Field(description="Indicator counts by category")
    patterns: dict[str, int] = Field(description="Pattern counts by category")
    supported_timeframes: list[str]
    performance_stats: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "version": "2.0.0",
                "indicators": {
                    "trend": 3,
                    "momentum": 3,
                    "volatility": 2
                },
                "patterns": {
                    "candlestick": 8
                },
                "supported_timeframes": ["daily", "weekly", "hourly", "intraday", "monthly", "1min"],
                "performance_stats": {
                    "avg_indicator_time_ms": 5.2,
                    "avg_pattern_time_ms": 8.1,
                    "cache_hit_rate": 0.92
                }
            }
        }
    )


class ErrorResponse(BaseModel):
    """Standard error response model."""

    error: str
    message: str
    details: dict[str, Any] | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": "ValidationError",
                "message": "Invalid timeframe provided",
                "details": {
                    "field": "timeframe",
                    "value": "invalid",
                    "allowed": ["daily", "weekly", "hourly", "intraday", "monthly", "1min"]
                },
                "timestamp": "2026-02-09T12:00:00"
            }
        }
    )
