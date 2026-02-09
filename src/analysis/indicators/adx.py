"""
Average Directional Index (ADX) indicator implementation.

Sprint 70: Indicator Library Extension
Trend strength indicator using directional movement.
"""

from dataclasses import dataclass
from typing import Any

import pandas as pd

from .base_indicator import BaseIndicator, IndicatorParams
from ..exceptions import IndicatorError


@dataclass
class ADXParams(IndicatorParams):
    """Parameters for ADX calculation."""

    use_sma: bool = False  # Use SMA instead of EMA for smoothing

    def __post_init__(self):
        """Validate ADX-specific parameters."""
        super().__post_init__()


class ADX(BaseIndicator):
    """
    Average Directional Index (ADX) indicator implementation.

    Trend strength indicator measuring the strength of a trend (not direction).
    Consists of three lines:
    - ADX: Strength of trend (0-100 scale)
    - +DI (Plus Directional Indicator): Upward movement strength
    - -DI (Minus Directional Indicator): Downward movement strength

    Features:
    - ADX, +DI, -DI calculation
    - Trend strength classification (weak/moderate/strong/very strong)
    - Directional movement analysis
    - Wilder's smoothing by default
    - Multi-timeframe support
    - Database-ready JSONB formatting
    """

    def __init__(self, params: dict[str, Any] | None = None):
        """
        Initialize ADX indicator with parameters.

        Args:
            params: Dictionary containing:
                - period: ADX period (default: 14)
                - use_sma: Use SMA instead of EMA (default: False)
        """
        if params is None:
            params = {"period": 14}

        super().__init__(params)
        self.name = "ADX"
        self.indicator_type = "trend"

    def _validate_params(self, params: dict[str, Any]) -> ADXParams:
        """
        Validate and parse ADX parameters.

        Args:
            params: Raw parameter dictionary

        Returns:
            Validated ADXParams instance
        """
        # Extract parameters with defaults
        period = params.get("period", 14)
        use_sma = params.get("use_sma", False)

        return ADXParams(period=period, source="close", use_sma=use_sma)

    def calculate(
        self, data: pd.DataFrame, symbol: str = None, timeframe: str = "daily"
    ) -> dict[str, Any]:
        """
        Calculate ADX values for given data.

        Args:
            data: DataFrame with OHLCV columns
            symbol: Stock symbol (optional)
            timeframe: Timeframe for calculation (default: 'daily')

        Returns:
            Dictionary formatted for database storage with:
                - indicator_type: 'adx'
                - value: ADX value (primary metric)
                - value_data: Dict with adx, plus_di, minus_di, trend_strength
                - calculation_timestamp: Latest data timestamp
                - timeframe: Timeframe used
                - metadata: Trend strength and direction

        Raises:
            IndicatorError: If calculation fails
        """
        # Validate timeframe
        valid_timeframes = ["daily", "weekly", "hourly", "intraday", "monthly", "1min"]
        if timeframe not in valid_timeframes:
            return self._empty_result(timeframe, data, symbol)

        # Check minimum data requirements (need period * 2 for smoothing)
        min_required = self.params.period * 2 + 1
        if len(data) < min_required:
            return self._empty_result(timeframe, data, symbol, "insufficient_data")

        # Validate data
        try:
            self._validate_data_format(data)
        except IndicatorError:
            return self._empty_result(timeframe, data, symbol, "invalid_data_format")

        # Calculate ADX, +DI, -DI
        series_df = self.calculate_series(data)
        adx_value = float(series_df["adx"].iloc[-1])
        plus_di = float(series_df["plus_di"].iloc[-1])
        minus_di = float(series_df["minus_di"].iloc[-1])

        if pd.isna(adx_value) or pd.isna(plus_di) or pd.isna(minus_di):
            return self._empty_result(timeframe, data, symbol, "calculation_failed")

        # Determine trend strength (ADX thresholds)
        if adx_value < 20:
            trend_strength = "weak"
        elif adx_value < 40:
            trend_strength = "moderate"
        elif adx_value < 60:
            trend_strength = "strong"
        else:
            trend_strength = "very_strong"

        # Determine trend direction based on +DI vs -DI
        if plus_di > minus_di:
            trend_direction = "uptrend"
        elif minus_di > plus_di:
            trend_direction = "downtrend"
        else:
            trend_direction = "neutral"

        return {
            "indicator_type": "adx",
            "symbol": symbol or "UNKNOWN",
            "timeframe": timeframe,
            "value": round(adx_value, 4),  # Primary value: ADX
            "value_data": {
                f"adx_{self.params.period}": round(adx_value, 4),
                "plus_di": round(plus_di, 4),
                "minus_di": round(minus_di, 4),
                "trend_strength": trend_strength,
                "trend_direction": trend_direction,
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
                "trend_strength": trend_strength,
                "trend_direction": trend_direction,
                "period": self.params.period,
                "calculation_method": "sma" if self.params.use_sma else "wilder",
            },
        }

    def calculate_series(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate full ADX series for charting and analysis.

        Args:
            data: DataFrame with OHLCV columns

        Returns:
            DataFrame with adx, plus_di, minus_di columns
        """
        # Get OHLC data
        high = data["high"]
        low = data["low"]
        close = data["close"]

        # Calculate True Range (same as ATR)
        prev_close = close.shift(1)
        tr = pd.concat([
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs()
        ], axis=1).max(axis=1)

        # Calculate directional movement
        # +DM = high - prev_high (if positive and > -DM, else 0)
        # -DM = prev_low - low (if positive and > +DM, else 0)
        high_diff = high.diff()
        low_diff = -low.diff()

        plus_dm = high_diff.copy()
        minus_dm = low_diff.copy()

        # Set to 0 where conditions not met
        plus_dm[(plus_dm < 0) | (plus_dm < low_diff)] = 0
        minus_dm[(minus_dm < 0) | (minus_dm < high_diff)] = 0

        # Smooth TR, +DM, -DM using Wilder's smoothing
        if self.params.use_sma:
            # Simple moving average
            tr_smooth = tr.rolling(window=self.params.period, min_periods=self.params.period).mean()
            plus_dm_smooth = plus_dm.rolling(window=self.params.period, min_periods=self.params.period).mean()
            minus_dm_smooth = minus_dm.rolling(window=self.params.period, min_periods=self.params.period).mean()
        else:
            # Wilder's smoothing (exponential weighted with alpha=1/period)
            tr_smooth = tr.ewm(alpha=1 / self.params.period, min_periods=self.params.period, adjust=False).mean()
            plus_dm_smooth = plus_dm.ewm(alpha=1 / self.params.period, min_periods=self.params.period, adjust=False).mean()
            minus_dm_smooth = minus_dm.ewm(alpha=1 / self.params.period, min_periods=self.params.period, adjust=False).mean()

        # Calculate +DI and -DI
        # +DI = (+DM / TR) * 100
        # -DI = (-DM / TR) * 100
        plus_di = (plus_dm_smooth / tr_smooth) * 100
        minus_di = (minus_dm_smooth / tr_smooth) * 100

        # Handle division by zero
        plus_di = plus_di.fillna(0.0)
        minus_di = minus_di.fillna(0.0)

        # Calculate DX (Directional Movement Index)
        # DX = (abs(+DI - -DI) / (+DI + -DI)) * 100
        di_sum = plus_di + minus_di
        di_diff = (plus_di - minus_di).abs()
        dx = (di_diff / di_sum) * 100

        # Handle division by zero
        dx = dx.fillna(0.0)

        # Calculate ADX (smoothed DX)
        if self.params.use_sma:
            adx = dx.rolling(window=self.params.period, min_periods=self.params.period).mean()
        else:
            adx = dx.ewm(alpha=1 / self.params.period, min_periods=self.params.period, adjust=False).mean()

        # Create result DataFrame
        result = pd.DataFrame(
            {
                "adx": adx,
                "plus_di": plus_di,
                "minus_di": minus_di,
                "dx": dx,
            },
            index=data.index,
        )

        return result

    def get_minimum_periods(self) -> int:
        """
        Get minimum number of periods required for calculation.

        Returns:
            Period * 2 + 1 for ADX calculation (needs double smoothing)
        """
        return self.params.period * 2 + 1

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
            "indicator_type": "adx",
            "symbol": symbol or "UNKNOWN",
            "timeframe": timeframe,
            "value": None,  # Primary value (convention)
            "value_data": {
                f"adx_{self.params.period}": None,
                "plus_di": None,
                "minus_di": None,
                "trend_strength": "invalid",
            },
            "calculation_timestamp": (
                data["timestamp"].iloc[-1].isoformat() if "timestamp" in data.columns else None
            )
            if len(data) > 0
            else None,
            "metadata": {
                "trend_strength": "invalid",
                "error": reason or "Invalid timeframe or insufficient data",
            },
        }
