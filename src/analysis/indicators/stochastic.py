"""
Stochastic Oscillator indicator implementation.

Sprint 70: Indicator Library Extension
Momentum indicator showing price position relative to high-low range.
"""

from dataclasses import dataclass
from typing import Any

import pandas as pd

from .base_indicator import BaseIndicator, IndicatorParams
from ..exceptions import IndicatorError


@dataclass
class StochasticParams(IndicatorParams):
    """Parameters for Stochastic Oscillator calculation."""

    k_period: int = 14  # %K period (lookback for high/low)
    d_period: int = 3  # %D period (SMA of %K)
    overbought: float = 80.0  # Overbought threshold
    oversold: float = 20.0  # Oversold threshold

    def __post_init__(self):
        """Validate Stochastic-specific parameters."""
        # Skip base class validation since we use k_period instead of period
        if self.k_period <= 0:
            raise ValueError(f"k_period must be positive, got {self.k_period}")

        if self.d_period <= 0:
            raise ValueError(f"d_period must be positive, got {self.d_period}")

        if not 0 < self.overbought <= 100:
            raise ValueError(f"Overbought must be between 0 and 100, got {self.overbought}")

        if not 0 <= self.oversold < 100:
            raise ValueError(f"Oversold must be between 0 and 100, got {self.oversold}")

        if self.oversold >= self.overbought:
            raise ValueError("Oversold must be less than overbought")


class Stochastic(BaseIndicator):
    """
    Stochastic Oscillator indicator implementation.

    Momentum indicator comparing current close to high-low range.
    Consists of two lines:
    - %K: (Close - Lowest Low) / (Highest High - Lowest Low) * 100
    - %D: SMA of %K (signal line)

    Features:
    - %K and %D line calculation
    - Overbought/oversold level detection
    - Crossover detection (%K crosses %D)
    - Multi-timeframe support
    - Database-ready JSONB formatting
    - Divergence detection capability
    """

    def __init__(self, params: dict[str, Any] | None = None):
        """
        Initialize Stochastic indicator with parameters.

        Args:
            params: Dictionary containing:
                - k_period: %K lookback period (default: 14)
                - d_period: %D SMA period (default: 3)
                - overbought: Overbought threshold (default: 80)
                - oversold: Oversold threshold (default: 20)
        """
        if params is None:
            params = {"k_period": 14, "d_period": 3}

        # Convert to use 'period' for base class compatibility
        if "k_period" in params:
            params["period"] = params["k_period"]

        super().__init__(params)
        self.name = "Stochastic"
        self.indicator_type = "momentum"

    def _validate_params(self, params: dict[str, Any]) -> StochasticParams:
        """
        Validate and parse Stochastic parameters.

        Args:
            params: Raw parameter dictionary

        Returns:
            Validated StochasticParams instance
        """
        # Extract parameters with defaults
        k_period = params.get("k_period", params.get("period", 14))
        d_period = params.get("d_period", 3)
        overbought = params.get("overbought", 80.0)
        oversold = params.get("oversold", 20.0)

        return StochasticParams(
            period=k_period,  # For base class
            source="close",  # Not used but required by base
            k_period=k_period,
            d_period=d_period,
            overbought=overbought,
            oversold=oversold,
        )

    def calculate(
        self, data: pd.DataFrame, symbol: str = None, timeframe: str = "daily"
    ) -> dict[str, Any]:
        """
        Calculate Stochastic Oscillator values for given data.

        Args:
            data: DataFrame with OHLCV columns
            symbol: Stock symbol (optional)
            timeframe: Timeframe for calculation (default: 'daily')

        Returns:
            Dictionary formatted for database storage with:
                - indicator_type: 'stochastic'
                - value: %K value (primary metric)
                - value_data: Dict with percent_k, percent_d, signal
                - calculation_timestamp: Latest data timestamp
                - timeframe: Timeframe used
                - metadata: Signal status and thresholds

        Raises:
            IndicatorError: If calculation fails
        """
        # Validate timeframe
        valid_timeframes = ["daily", "weekly", "hourly", "intraday", "monthly", "1min"]
        if timeframe not in valid_timeframes:
            return self._empty_result(timeframe, data, symbol)

        # Check minimum data requirements
        min_required = self.params.k_period + self.params.d_period - 1
        if len(data) < min_required:
            return self._empty_result(timeframe, data, symbol, "insufficient_data")

        # Validate data
        try:
            self._validate_data_format(data)
        except IndicatorError:
            return self._empty_result(timeframe, data, symbol, "invalid_data_format")

        # Calculate %K and %D
        series_df = self.calculate_series(data)
        percent_k = float(series_df["percent_k"].iloc[-1])
        percent_d = float(series_df["percent_d"].iloc[-1])

        if pd.isna(percent_k) or pd.isna(percent_d):
            return self._empty_result(timeframe, data, symbol, "calculation_failed")

        # Determine signal
        signal = "neutral"
        overbought_flag = False
        oversold_flag = False
        confidence = 0.70  # Base confidence

        if percent_k >= self.params.overbought:
            signal = "overbought"
            overbought_flag = True
            confidence = 0.80
        elif percent_k <= self.params.oversold:
            signal = "oversold"
            oversold_flag = True
            confidence = 0.80

        # Detect crossovers
        crossover_type = None
        if len(data) >= 2:
            prev_k = series_df["percent_k"].iloc[-2]
            prev_d = series_df["percent_d"].iloc[-2]

            if not pd.isna(prev_k) and not pd.isna(prev_d):
                # Bullish crossover: %K crosses above %D
                if prev_k <= prev_d and percent_k > percent_d:
                    crossover_type = "bullish"
                    if percent_k < self.params.oversold:
                        confidence = 0.90  # Strong signal if in oversold zone
                # Bearish crossover: %K crosses below %D
                elif prev_k >= prev_d and percent_k < percent_d:
                    crossover_type = "bearish"
                    if percent_k > self.params.overbought:
                        confidence = 0.90  # Strong signal if in overbought zone

        return {
            "indicator_type": "stochastic",
            "symbol": symbol or "UNKNOWN",
            "timeframe": timeframe,
            "value": round(percent_k, 4),  # Primary value: %K
            "value_data": {
                "percent_k": round(percent_k, 4),
                "percent_d": round(percent_d, 4),
                "signal": signal,
                "overbought": overbought_flag,
                "oversold": oversold_flag,
                "crossover": crossover_type,
                "confidence": round(confidence, 2),
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
                "signal": signal,
                "overbought_threshold": self.params.overbought,
                "oversold_threshold": self.params.oversold,
                "crossover": crossover_type,
                "k_period": self.params.k_period,
                "d_period": self.params.d_period,
            },
        }

    def calculate_series(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate full Stochastic series for charting and analysis.

        Args:
            data: DataFrame with OHLCV columns

        Returns:
            DataFrame with percent_k and percent_d columns
        """
        # Get high, low, close
        high = data["high"]
        low = data["low"]
        close = data["close"]

        # Calculate %K: (Close - Lowest Low) / (Highest High - Lowest Low) * 100
        lowest_low = low.rolling(window=self.params.k_period, min_periods=self.params.k_period).min()
        highest_high = high.rolling(window=self.params.k_period, min_periods=self.params.k_period).max()

        # Calculate %K
        stoch_range = highest_high - lowest_low
        percent_k = ((close - lowest_low) / stoch_range) * 100

        # Handle division by zero (flat range)
        percent_k = percent_k.fillna(50.0)  # Default to middle if range is zero

        # Calculate %D: SMA of %K
        percent_d = percent_k.rolling(window=self.params.d_period, min_periods=self.params.d_period).mean()

        # Create result DataFrame
        result = pd.DataFrame(
            {
                "percent_k": percent_k,
                "percent_d": percent_d,
            },
            index=data.index,
        )

        return result

    def get_minimum_periods(self) -> int:
        """
        Get minimum number of periods required for calculation.

        Returns:
            k_period + d_period - 1 (need enough data for both calculations)
        """
        return self.params.k_period + self.params.d_period - 1

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
            "indicator_type": "stochastic",
            "symbol": symbol or "UNKNOWN",
            "timeframe": timeframe,
            "value": None,  # Primary value (convention)
            "value_data": {
                "percent_k": None,
                "percent_d": None,
                "signal": "invalid",
            },
            "calculation_timestamp": (
                data["timestamp"].iloc[-1].isoformat() if "timestamp" in data.columns else None
            )
            if len(data) > 0
            else None,
            "metadata": {
                "signal": "invalid",
                "overbought_threshold": self.params.overbought,
                "oversold_threshold": self.params.oversold,
                "error": reason or "Invalid timeframe or insufficient data",
            },
        }
