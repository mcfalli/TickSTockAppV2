"""
Moving Average Convergence Divergence (MACD) indicator implementation.

Sprint 68: Core Analysis Migration from TickStockPL
Migrated from TickStockPL with TickStockAppV2 architecture adaptations.
"""

from dataclasses import dataclass
from typing import Any

import pandas as pd

from .base_indicator import BaseIndicator, IndicatorParams
from ..exceptions import IndicatorError


@dataclass
class MACDParams(IndicatorParams):
    """Parameters for MACD calculation."""

    fast_period: int = 12
    slow_period: int = 26
    signal_period: int = 9

    def __post_init__(self):
        """Validate MACD-specific parameters."""
        super().__post_init__()

        if self.fast_period <= 0:
            raise ValueError(f"Fast period must be positive, got {self.fast_period}")

        if self.slow_period <= 0:
            raise ValueError(f"Slow period must be positive, got {self.slow_period}")

        if self.signal_period <= 0:
            raise ValueError(f"Signal period must be positive, got {self.signal_period}")

        if self.fast_period >= self.slow_period:
            raise ValueError(
                f"Fast period ({self.fast_period}) must be < slow period ({self.slow_period})"
            )


class MACD(BaseIndicator):
    """
    Moving Average Convergence Divergence (MACD) indicator implementation.

    Trend-following momentum indicator showing relationship between two EMAs.

    Components:
    - MACD Line: EMA(fast) - EMA(slow)
    - Signal Line: EMA of MACD Line (signal_period)
    - Histogram: MACD Line - Signal Line

    Signals:
    - Bullish: MACD crosses above Signal (histogram > 0)
    - Bearish: MACD crosses below Signal (histogram < 0)

    Features:
    - EMA-based calculation (12, 26, 9 default periods)
    - Crossover detection (bullish/bearish signals)
    - Multi-timeframe support (daily, weekly, monthly, intraday)
    - Database-ready JSONB formatting
    - Convention-compliant return format (value = MACD line, NOT histogram)
    """

    def __init__(self, params: dict[str, Any] | None = None):
        """
        Initialize MACD indicator with parameters.

        Args:
            params: Dictionary containing:
                - fast_period: Fast EMA period (default: 12)
                - slow_period: Slow EMA period (default: 26)
                - signal_period: Signal line period (default: 9)
                - source: Column to use (default: 'close')
                - period: For BaseIndicator compatibility (default: slow_period)
        """
        if params is None:
            params = {"period": 26, "fast_period": 12, "slow_period": 26, "signal_period": 9}

        super().__init__(params)
        self.name = "MACD"
        self.indicator_type = "trend"

    def _validate_params(self, params: dict[str, Any]) -> MACDParams:
        """
        Validate and parse MACD parameters.

        Args:
            params: Raw parameter dictionary

        Returns:
            Validated MACDParams instance
        """
        # Extract parameters with defaults
        # Support both 'fast_period' and 'fast' for flexibility
        fast = params.get("fast_period", params.get("fast", 12))
        slow = params.get("slow_period", params.get("slow", 26))
        signal = params.get("signal_period", params.get("signal", 9))
        source = params.get("source", "close")

        # period is max of slow_period for BaseIndicator compatibility
        period = params.get("period", slow)

        return MACDParams(
            period=period, source=source, fast_period=fast, slow_period=slow, signal_period=signal
        )

    def calculate(
        self, data: pd.DataFrame, symbol: str = None, timeframe: str = "daily"
    ) -> dict[str, Any]:
        """
        Calculate MACD values for given data.

        Args:
            data: DataFrame with OHLCV columns
            symbol: Stock symbol (optional)
            timeframe: Timeframe for calculation (default: 'daily')

        Returns:
            Dictionary formatted for database storage with:
                - indicator_type: 'macd'
                - value: MACD line value (primary component - NOT histogram)
                - value_data: Dict with macd, signal, histogram, macd_signal
                - calculation_timestamp: Latest data timestamp
                - timeframe: Timeframe used
                - metadata: Calculation parameters and signal status

        Raises:
            IndicatorError: If calculation fails
        """
        # Validate timeframe
        valid_timeframes = ["daily", "weekly", "hourly", "intraday", "monthly", "1min"]
        if timeframe not in valid_timeframes:
            return self._empty_result(symbol, timeframe, "invalid_timeframe")

        # Check minimum data requirements
        # Need slow_period + signal_period bars minimum for signal line
        min_bars = self.params.slow_period + self.params.signal_period
        if len(data) < min_bars:
            return self._empty_result(symbol, timeframe, "insufficient_data")

        # Validate data
        try:
            self._validate_data_format(data)
        except IndicatorError:
            return self._empty_result(symbol, timeframe, "invalid_data_format")

        # Get source values
        source_values = self._get_source_values(data)

        # Check for NaN in source data
        if source_values.isna().any():
            return self._empty_result(symbol, timeframe, "nan_in_source_data")

        # Calculate EMAs (vectorized operations)
        # CRITICAL: Use adjust=False for standard EMA (NOT Wilder's smoothing)
        ema_fast = source_values.ewm(span=self.params.fast_period, adjust=False).mean()
        ema_slow = source_values.ewm(span=self.params.slow_period, adjust=False).mean()

        # MACD Line = Fast EMA - Slow EMA
        macd_line = ema_fast - ema_slow

        # Signal Line = EMA of MACD Line
        signal_line = macd_line.ewm(span=self.params.signal_period, adjust=False).mean()

        # Histogram = MACD Line - Signal Line
        histogram = macd_line - signal_line

        # Detect crossovers
        macd_signal = self._detect_crossover(macd_line, signal_line, histogram)

        # Get latest values
        current_macd = float(macd_line.iloc[-1])
        current_signal = float(signal_line.iloc[-1])
        current_histogram = float(histogram.iloc[-1])

        # Determine confidence based on signal strength
        confidence = 0.70  # Base confidence
        if macd_signal in ["bullish_crossover", "bearish_crossover"]:
            confidence = 0.85  # Higher confidence on crossovers
        elif abs(current_histogram) > abs(current_macd) * 0.1:
            confidence = 0.80  # Strong divergence from signal

        # CONVENTION-COMPLIANT return format
        # CRITICAL: Primary value = MACD line (NOT histogram)
        return {
            "indicator_type": "macd",
            "symbol": symbol or "UNKNOWN",
            "timeframe": timeframe,
            "value": current_macd,  # PRIMARY VALUE = MACD line (convention)
            "value_data": {
                "macd": current_macd,
                "signal": current_signal,
                "histogram": current_histogram,
                "macd_signal": macd_signal,
                "confidence": confidence,
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
                "fast_period": self.params.fast_period,
                "slow_period": self.params.slow_period,
                "signal_period": self.params.signal_period,
                "crossover": macd_signal,
                "calculation_method": "ema",
                "min_bars_required": self.params.slow_period + self.params.signal_period,
            },
        }

    def calculate_series(self, data: pd.DataFrame) -> dict[str, pd.Series]:
        """
        Calculate full MACD series for charting and analysis.

        Args:
            data: DataFrame with OHLCV columns

        Returns:
            Dictionary with 'macd', 'signal', and 'histogram' Series
        """
        # Get source values
        source_values = self._get_source_values(data)

        # Calculate EMAs
        ema_fast = source_values.ewm(span=self.params.fast_period, adjust=False).mean()
        ema_slow = source_values.ewm(span=self.params.slow_period, adjust=False).mean()

        # MACD components
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=self.params.signal_period, adjust=False).mean()
        histogram = macd_line - signal_line

        return {"macd": macd_line, "signal": signal_line, "histogram": histogram}

    def _detect_crossover(
        self, macd_line: pd.Series, signal_line: pd.Series, histogram: pd.Series
    ) -> str:
        """
        Detect MACD crossover signals.

        Args:
            macd_line: MACD line series
            signal_line: Signal line series
            histogram: Histogram series (MACD - Signal)

        Returns:
            Signal status: 'bullish_crossover', 'bearish_crossover',
            'bullish', 'bearish', or 'neutral'
        """
        # Need at least 2 histogram values to detect crossover
        if len(histogram) < 2:
            return "neutral"

        prev_histogram = histogram.iloc[-2]
        current_histogram = histogram.iloc[-1]

        # Bullish crossover: MACD crosses above Signal (histogram goes from <= 0 to > 0)
        if current_histogram > 0 and prev_histogram <= 0:
            return "bullish_crossover"

        # Bearish crossover: MACD crosses below Signal (histogram goes from >= 0 to < 0)
        if current_histogram < 0 and prev_histogram >= 0:
            return "bearish_crossover"

        # Continuation signals (no crossover)
        if current_histogram > 0:
            return "bullish"
        if current_histogram < 0:
            return "bearish"
        return "neutral"

    def get_minimum_periods(self) -> int:
        """
        Get minimum number of periods required for calculation.

        Returns:
            slow_period + signal_period for full MACD calculation
        """
        return self.params.slow_period + self.params.signal_period

    def _empty_result(self, symbol: str, timeframe: str, reason: str) -> dict[str, Any]:
        """
        Generate empty result for invalid inputs.

        Args:
            symbol: Stock symbol
            timeframe: Timeframe attempted
            reason: Reason for empty result

        Returns:
            Empty result dictionary with convention-compliant format
        """
        return {
            "indicator_type": "macd",
            "symbol": symbol or "UNKNOWN",
            "timeframe": timeframe,
            "value": None,  # Primary value (convention)
            "value_data": {
                "macd": None,
                "signal": None,
                "histogram": None,
                "macd_signal": None,
                "reason": reason,
            },
            "calculation_timestamp": None,
            "metadata": {
                "error": reason,
                "fast_period": self.params.fast_period,
                "slow_period": self.params.slow_period,
                "signal_period": self.params.signal_period,
            },
        }
