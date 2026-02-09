"""
Average True Range (ATR) indicator implementation.

Sprint 70: Indicator Library Extension
Measures market volatility using exponentially smoothed true range.
"""

from dataclasses import dataclass
from typing import Any

import pandas as pd

from .base_indicator import BaseIndicator, IndicatorParams
from ..exceptions import IndicatorError


@dataclass
class ATRParams(IndicatorParams):
    """Parameters for ATR calculation."""

    use_sma: bool = False  # Use SMA instead of EMA for smoothing

    def __post_init__(self):
        """Validate ATR-specific parameters."""
        super().__post_init__()
        # ATR doesn't use 'source' parameter but inherits it from IndicatorParams


class ATR(BaseIndicator):
    """
    Average True Range (ATR) indicator implementation.

    Volatility indicator measuring the average range of price movement.
    True Range accounts for gaps by considering previous close.

    Features:
    - Wilder's smoothing (exponential weighted average) by default
    - Optional SMA smoothing
    - Multi-timeframe support (daily, weekly, hourly, intraday)
    - Database-ready JSONB formatting
    - Measures absolute volatility (not directional)
    """

    def __init__(self, params: dict[str, Any] | None = None):
        """
        Initialize ATR indicator with parameters.

        Args:
            params: Dictionary containing:
                - period: ATR period (default: 14)
                - use_sma: Use SMA instead of EMA (default: False)
        """
        if params is None:
            params = {"period": 14}

        super().__init__(params)
        self.name = "ATR"
        self.indicator_type = "volatility"

    def _validate_params(self, params: dict[str, Any]) -> ATRParams:
        """
        Validate and parse ATR parameters.

        Args:
            params: Raw parameter dictionary

        Returns:
            Validated ATRParams instance
        """
        # Extract parameters with defaults
        period = params.get("period", 14)
        use_sma = params.get("use_sma", False)

        return ATRParams(period=period, source="close", use_sma=use_sma)

    def calculate(
        self, data: pd.DataFrame, symbol: str = None, timeframe: str = "daily"
    ) -> dict[str, Any]:
        """
        Calculate ATR values for given data.

        Args:
            data: DataFrame with OHLCV columns
            symbol: Stock symbol (optional)
            timeframe: Timeframe for calculation (default: 'daily')

        Returns:
            Dictionary formatted for database storage with:
                - indicator_type: 'atr'
                - value: ATR value (primary metric)
                - value_data: Dict with atr_14, volatility_signal
                - calculation_timestamp: Latest data timestamp
                - timeframe: Timeframe used
                - metadata: Calculation details

        Raises:
            IndicatorError: If calculation fails
        """
        # Validate timeframe
        valid_timeframes = ["daily", "weekly", "hourly", "intraday", "monthly", "1min"]
        if timeframe not in valid_timeframes:
            return self._empty_result(timeframe, data, symbol)

        # Check minimum data requirements (need prev close, so period + 1)
        if len(data) < self.params.period + 1:
            return self._empty_result(timeframe, data, symbol, "insufficient_data")

        # Validate data
        try:
            self._validate_data_format(data)
        except IndicatorError:
            return self._empty_result(timeframe, data, symbol, "invalid_data_format")

        # Calculate ATR
        atr_value = self._calculate_atr(data)

        # Determine volatility signal (relative to average)
        volatility_signal = "normal"
        if atr_value is not None and len(data) >= 50:
            # Compare current ATR to 50-period average
            atr_series = self.calculate_series(data)
            avg_atr = atr_series.iloc[-50:].mean()

            if atr_value > avg_atr * 1.5:
                volatility_signal = "high"
            elif atr_value < avg_atr * 0.5:
                volatility_signal = "low"

        # Calculate true range components for diagnostics
        tr_series = self._calculate_true_range(data)
        current_tr = float(tr_series.iloc[-1]) if len(tr_series) > 0 else None

        return {
            "indicator_type": "atr",
            "symbol": symbol or "UNKNOWN",
            "timeframe": timeframe,
            "value": float(atr_value) if atr_value is not None else None,  # Primary value
            "value_data": {
                f"atr_{self.params.period}": float(atr_value) if atr_value is not None else None,
                "volatility_signal": volatility_signal,
                "current_true_range": round(current_tr, 4) if current_tr is not None else None,
                "period": self.params.period,
            },
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
            "metadata": {
                "volatility_signal": volatility_signal,
                "calculation_method": "sma" if self.params.use_sma else "wilder",
                "min_bars_required": self.params.period + 1,
            },
        }

    def calculate_series(self, data: pd.DataFrame) -> pd.Series:
        """
        Calculate full ATR series for charting and analysis.

        Args:
            data: DataFrame with OHLCV columns

        Returns:
            Series with ATR values
        """
        # Calculate True Range
        tr = self._calculate_true_range(data)

        # Calculate ATR using smoothing method
        if self.params.use_sma:
            # Simple moving average
            atr = tr.rolling(window=self.params.period, min_periods=self.params.period).mean()
        else:
            # Wilder's smoothing (exponential weighted with alpha=1/period)
            # CRITICAL: Use alpha=1/period and adjust=False for correct Wilder's method
            atr = tr.ewm(
                alpha=1 / self.params.period, min_periods=self.params.period, adjust=False
            ).mean()

        return atr

    def _calculate_true_range(self, data: pd.DataFrame) -> pd.Series:
        """
        Calculate True Range series.

        True Range = max(high-low, abs(high-prev_close), abs(low-prev_close))

        Args:
            data: DataFrame with OHLCV columns

        Returns:
            Series with True Range values
        """
        # Get OHLC data
        high = data["high"]
        low = data["low"]
        close = data["close"]

        # Calculate previous close (shifted by 1)
        prev_close = close.shift(1)

        # Calculate three ranges
        range1 = high - low  # High - Low
        range2 = (high - prev_close).abs()  # abs(High - Previous Close)
        range3 = (low - prev_close).abs()  # abs(Low - Previous Close)

        # True Range is the maximum of the three ranges
        # Use pandas concat and max across axis=1 for vectorized operation
        tr = pd.concat([range1, range2, range3], axis=1).max(axis=1)

        # First bar has no previous close, so TR is just high-low
        tr.iloc[0] = high.iloc[0] - low.iloc[0]

        return tr

    def _calculate_atr(self, data: pd.DataFrame) -> float | None:
        """
        Calculate single ATR value.

        Args:
            data: DataFrame with OHLCV columns

        Returns:
            Latest ATR value or None if calculation fails
        """
        if len(data) < self.params.period + 1:
            return None

        # Calculate full series
        atr_series = self.calculate_series(data)

        # Return latest non-NaN value
        latest = atr_series.iloc[-1]
        return float(latest) if not pd.isna(latest) else None

    def get_minimum_periods(self) -> int:
        """
        Get minimum number of periods required for calculation.

        Returns:
            Period + 1 for ATR calculation (need previous close)
        """
        return self.params.period + 1

    def _empty_result(
        self, timeframe: str, data: pd.DataFrame, symbol: str = None, reason: str = None
    ) -> dict[str, Any]:
        """
        Generate empty result for invalid inputs.

        Args:
            timeframe: Timeframe attempted
            data: Input data
            symbol: Stock symbol
            reason: Reason for empty result

        Returns:
            Empty result dictionary
        """
        return {
            "indicator_type": "atr",
            "symbol": symbol or "UNKNOWN",
            "timeframe": timeframe,
            "value": None,  # Primary value (convention)
            "value_data": {f"atr_{self.params.period}": None},
            "calculation_timestamp": (
                data["timestamp"].iloc[-1].isoformat() if "timestamp" in data.columns else None
            )
            if len(data) > 0
            else None,
            "metadata": {
                "volatility_signal": "invalid",
                "error": reason or "Invalid timeframe or insufficient data",
            },
        }
