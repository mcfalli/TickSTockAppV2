"""
Simple Moving Average (SMA) indicator implementation.

Sprint 68: Core Analysis Migration from TickStockPL
Migrated from TickStockPL with TickStockAppV2 architecture adaptations.
"""

from dataclasses import dataclass
from typing import Any

import pandas as pd

from .base_indicator import BaseIndicator, IndicatorParams
from ..exceptions import IndicatorError


@dataclass
class SMAParams(IndicatorParams):
    """Parameters for SMA calculation."""

    periods: list[int] | None = None  # Multiple periods for multi-SMA calculation

    def __post_init__(self):
        """Validate SMA-specific parameters."""
        super().__post_init__()

        # If periods is provided, validate each period
        if self.periods:
            if not isinstance(self.periods, list):
                self.periods = [self.periods]

            for p in self.periods:
                if not isinstance(p, int) or p <= 0:
                    raise ValueError(f"All periods must be positive integers, got {p}")


class SMA(BaseIndicator):
    """
    Simple Moving Average indicator implementation.

    Calculates the arithmetic mean of prices over a specified period.
    Supports multiple periods for simultaneous calculation.

    Features:
    - Single and multiple period calculation
    - Multi-timeframe support (daily, weekly, hourly, intraday)
    - Database-ready JSONB formatting
    - Vectorized operations for efficiency
    - Golden/Death cross detection capability
    """

    def __init__(self, params: dict[str, Any] | None = None):
        """
        Initialize SMA indicator with parameters.

        Args:
            params: Dictionary containing:
                - period: Single SMA period (default: 20)
                - periods: List of periods for multiple SMAs
                - source: Column to use (default: 'close')
        """
        if params is None:
            params = {"period": 20, "source": "close"}

        super().__init__(params)
        self.name = "SMA"
        self.indicator_type = "trend"

    def _validate_params(self, params: dict[str, Any]) -> SMAParams:
        """
        Validate and parse SMA parameters.

        Args:
            params: Raw parameter dictionary

        Returns:
            Validated SMAParams instance
        """
        # Extract parameters with defaults
        period = params.get("period", 20)
        periods = params.get("periods")
        source = params.get("source", "close")

        return SMAParams(period=period, periods=periods, source=source)

    def calculate(
        self, data: pd.DataFrame, symbol: str = None, timeframe: str = "daily"
    ) -> dict[str, Any]:
        """
        Calculate SMA values for given data.

        Args:
            data: DataFrame with OHLCV columns
            symbol: Stock symbol (optional)
            timeframe: Timeframe for calculation (default: 'daily')

        Returns:
            Dictionary formatted for database storage with:
                - indicator_type: 'sma'
                - value: Primary SMA value (first period)
                - value_data: Dict of SMA values (sma_20, sma_50, etc.)
                - calculation_timestamp: Latest data timestamp
                - timeframe: Timeframe used
                - metadata: Additional calculation details

        Raises:
            IndicatorError: If calculation fails
        """
        # Validate timeframe
        valid_timeframes = ["daily", "weekly", "hourly", "intraday", "monthly", "1min"]
        if timeframe not in valid_timeframes:
            return self._empty_result(timeframe, data, symbol)

        # Validate data format
        try:
            self._validate_data_format(data)
        except IndicatorError:
            return self._empty_result(timeframe, data, symbol)

        # Get source values
        source_values = self._get_source_values(data)

        # Determine periods to calculate
        if self.params.periods:
            periods_to_calc = self.params.periods
        else:
            periods_to_calc = [self.params.period]

        # Calculate SMAs
        result_data = {}
        metadata = {"periods_calculated": [], "crossovers": []}

        for period in periods_to_calc:
            if len(data) < period:
                result_data[f"sma_{period}"] = None
            else:
                # CRITICAL: min_periods prevents partial window calculations
                sma_series = source_values.rolling(window=period, min_periods=period).mean()
                latest_value = sma_series.iloc[-1]
                result_data[f"sma_{period}"] = (
                    float(latest_value) if not pd.isna(latest_value) else None
                )
                metadata["periods_calculated"].append(period)

        # Check for golden/death crosses if we have both 50 and 200 period SMAs
        if "sma_50" in result_data and "sma_200" in result_data:
            if result_data["sma_50"] and result_data["sma_200"]:
                if len(data) >= 2:
                    # Calculate previous values
                    sma50_prev = (
                        source_values.rolling(window=50, min_periods=50).mean().iloc[-2]
                        if len(data) > 200
                        else None
                    )
                    sma200_prev = (
                        source_values.rolling(window=200, min_periods=200).mean().iloc[-2]
                        if len(data) > 200
                        else None
                    )

                    if sma50_prev and sma200_prev:
                        # Golden cross: 50 crosses above 200
                        if (
                            sma50_prev <= sma200_prev
                            and result_data["sma_50"] > result_data["sma_200"]
                        ):
                            metadata["crossovers"].append(
                                {
                                    "type": "golden_cross",
                                    "timestamp": data.index[-1].isoformat()
                                    if hasattr(data.index[-1], "isoformat")
                                    else str(data.index[-1]),
                                }
                            )
                        # Death cross: 50 crosses below 200
                        elif (
                            sma50_prev >= sma200_prev
                            and result_data["sma_50"] < result_data["sma_200"]
                        ):
                            metadata["crossovers"].append(
                                {
                                    "type": "death_cross",
                                    "timestamp": data.index[-1].isoformat()
                                    if hasattr(data.index[-1], "isoformat")
                                    else str(data.index[-1]),
                                }
                            )

        # Primary value = first calculated period (convention)
        primary_value = None
        for period in periods_to_calc:
            if f"sma_{period}" in result_data and result_data[f"sma_{period}"] is not None:
                primary_value = result_data[f"sma_{period}"]
                break

        return {
            "indicator_type": "sma",
            "symbol": symbol or "UNKNOWN",
            "timeframe": timeframe,
            "value": primary_value,  # Primary value (convention)
            "value_data": result_data,
            "calculation_timestamp": (
                data["timestamp"].iloc[-1].isoformat()
                if "timestamp" in data.columns
                else (
                    data.index[-1].isoformat()
                    if hasattr(data.index[-1], "isoformat")
                    else str(data.index[-1])
                )
            )
            if len(data) > 0
            else None,
            "metadata": metadata,
        }

    def calculate_series(
        self, data: pd.DataFrame, periods: list[int] | None = None
    ) -> pd.DataFrame:
        """
        Calculate SMA series for charting and analysis.

        Args:
            data: DataFrame with OHLCV columns
            periods: List of periods to calculate (uses params if not provided)

        Returns:
            DataFrame with SMA columns (sma_20, sma_50, etc.)
        """
        # Get source values
        source_values = self._get_source_values(data)

        # Determine periods
        if periods is None:
            periods = self.params.periods if self.params.periods else [self.params.period]

        # Calculate all SMAs
        result = pd.DataFrame(index=data.index)
        for period in periods:
            result[f"sma_{period}"] = source_values.rolling(
                window=period, min_periods=period
            ).mean()

        return result

    def get_minimum_periods(self) -> int:
        """
        Get minimum number of periods required for calculation.

        Returns:
            Maximum period from all configured periods
        """
        if self.params.periods:
            return max(self.params.periods)
        return self.params.period

    def _empty_result(
        self, timeframe: str, data: pd.DataFrame, symbol: str = None
    ) -> dict[str, Any]:
        """
        Generate empty result for invalid inputs.

        Args:
            timeframe: Timeframe attempted
            data: Input data
            symbol: Stock symbol

        Returns:
            Empty result dictionary
        """
        periods = self.params.periods if self.params.periods else [self.params.period]
        result_data = {f"sma_{p}": None for p in periods}

        return {
            "indicator_type": "sma",
            "symbol": symbol or "UNKNOWN",
            "timeframe": timeframe,
            "value": None,  # Primary value (convention)
            "value_data": result_data,
            "calculation_timestamp": (
                data["timestamp"].iloc[-1].isoformat() if "timestamp" in data.columns else None
            )
            if len(data) > 0
            else None,
            "metadata": {"error": "Invalid timeframe or insufficient data"},
        }
