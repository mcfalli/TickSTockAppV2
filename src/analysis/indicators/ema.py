"""
Exponential Moving Average (EMA) indicator implementation.

Sprint 70: Indicator Library Extension
Exponential smoothing gives more weight to recent prices.
"""

from dataclasses import dataclass
from typing import Any

import pandas as pd

from .base_indicator import BaseIndicator, IndicatorParams
from ..exceptions import IndicatorError


@dataclass
class EMAParams(IndicatorParams):
    """Parameters for EMA calculation."""

    periods: list[int] | None = None  # Multiple periods for multi-EMA calculation

    def __post_init__(self):
        """Validate EMA-specific parameters."""
        super().__post_init__()

        # If periods is provided, validate each period
        if self.periods:
            if not isinstance(self.periods, list):
                self.periods = [self.periods]

            for p in self.periods:
                if not isinstance(p, int) or p <= 0:
                    raise ValueError(f"All periods must be positive integers, got {p}")


class EMA(BaseIndicator):
    """
    Exponential Moving Average indicator implementation.

    Calculates exponentially weighted mean giving more weight to recent prices.
    Uses smoothing factor: alpha = 2 / (period + 1)

    Features:
    - Single and multiple period calculation
    - Multi-timeframe support (daily, weekly, hourly, intraday)
    - Database-ready JSONB formatting
    - Vectorized operations for efficiency
    - EMA crossover detection capability
    """

    def __init__(self, params: dict[str, Any] | None = None):
        """
        Initialize EMA indicator with parameters.

        Args:
            params: Dictionary containing:
                - period: Single EMA period (default: 20)
                - periods: List of periods for multiple EMAs
                - source: Column to use (default: 'close')
        """
        if params is None:
            params = {"period": 20, "source": "close"}

        super().__init__(params)
        self.name = "EMA"
        self.indicator_type = "trend"

    def _validate_params(self, params: dict[str, Any]) -> EMAParams:
        """
        Validate and parse EMA parameters.

        Args:
            params: Raw parameter dictionary

        Returns:
            Validated EMAParams instance
        """
        # Extract parameters with defaults
        period = params.get("period", 20)
        periods = params.get("periods")
        source = params.get("source", "close")

        return EMAParams(period=period, periods=periods, source=source)

    def calculate(
        self, data: pd.DataFrame, symbol: str = None, timeframe: str = "daily"
    ) -> dict[str, Any]:
        """
        Calculate EMA values for given data.

        Args:
            data: DataFrame with OHLCV columns
            symbol: Stock symbol (optional)
            timeframe: Timeframe for calculation (default: 'daily')

        Returns:
            Dictionary formatted for database storage with:
                - indicator_type: 'ema'
                - value: Primary EMA value (first period)
                - value_data: Dict of EMA values (ema_20, ema_50, etc.)
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

        # Calculate EMAs
        result_data = {}
        metadata = {"periods_calculated": [], "crossovers": []}

        for period in periods_to_calc:
            if len(data) < period:
                result_data[f"ema_{period}"] = None
            else:
                # CRITICAL: Use pandas ewm with span=period for exponential smoothing
                # min_periods=period ensures we wait for full window before calculating
                ema_series = source_values.ewm(span=period, adjust=False, min_periods=period).mean()
                latest_value = ema_series.iloc[-1]
                result_data[f"ema_{period}"] = (
                    float(latest_value) if not pd.isna(latest_value) else None
                )
                metadata["periods_calculated"].append(period)

        # Check for EMA crossovers if we have both 12 and 26 period EMAs (common MACD setup)
        if "ema_12" in result_data and "ema_26" in result_data:
            if result_data["ema_12"] and result_data["ema_26"]:
                if len(data) >= 2:
                    # Calculate previous values
                    ema12_prev = (
                        source_values.ewm(span=12, adjust=False, min_periods=12).mean().iloc[-2]
                        if len(data) > 26
                        else None
                    )
                    ema26_prev = (
                        source_values.ewm(span=26, adjust=False, min_periods=26).mean().iloc[-2]
                        if len(data) > 26
                        else None
                    )

                    if ema12_prev and ema26_prev:
                        # Bullish crossover: 12 crosses above 26
                        if (
                            ema12_prev <= ema26_prev
                            and result_data["ema_12"] > result_data["ema_26"]
                        ):
                            metadata["crossovers"].append(
                                {
                                    "type": "bullish_crossover",
                                    "timestamp": data.index[-1].isoformat()
                                    if hasattr(data.index[-1], "isoformat")
                                    else str(data.index[-1]),
                                }
                            )
                        # Bearish crossover: 12 crosses below 26
                        elif (
                            ema12_prev >= ema26_prev
                            and result_data["ema_12"] < result_data["ema_26"]
                        ):
                            metadata["crossovers"].append(
                                {
                                    "type": "bearish_crossover",
                                    "timestamp": data.index[-1].isoformat()
                                    if hasattr(data.index[-1], "isoformat")
                                    else str(data.index[-1]),
                                }
                            )

        # Primary value = first calculated period (convention)
        primary_value = None
        for period in periods_to_calc:
            if f"ema_{period}" in result_data and result_data[f"ema_{period}"] is not None:
                primary_value = result_data[f"ema_{period}"]
                break

        return {
            "indicator_type": "ema",
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
        Calculate EMA series for charting and analysis.

        Args:
            data: DataFrame with OHLCV columns
            periods: List of periods to calculate (uses params if not provided)

        Returns:
            DataFrame with EMA columns (ema_20, ema_50, etc.)
        """
        # Get source values
        source_values = self._get_source_values(data)

        # Determine periods
        if periods is None:
            periods = self.params.periods if self.params.periods else [self.params.period]

        # Calculate all EMAs
        result = pd.DataFrame(index=data.index)
        for period in periods:
            result[f"ema_{period}"] = source_values.ewm(
                span=period, adjust=False, min_periods=period
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
        result_data = {f"ema_{p}": None for p in periods}

        return {
            "indicator_type": "ema",
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
