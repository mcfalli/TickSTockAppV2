"""
Relative Strength Index (RSI) indicator implementation.

Sprint 68: Core Analysis Migration from TickStockPL
Migrated from TickStockPL with TickStockAppV2 architecture adaptations.
"""

from dataclasses import dataclass
from typing import Any

import pandas as pd

from .base_indicator import BaseIndicator, IndicatorParams
from ..exceptions import IndicatorError


@dataclass
class RSIParams(IndicatorParams):
    """Parameters for RSI calculation."""

    overbought: float = 70.0  # Overbought threshold
    oversold: float = 30.0  # Oversold threshold
    use_sma: bool = False  # Use SMA instead of EMA for smoothing

    def __post_init__(self):
        """Validate RSI-specific parameters."""
        super().__post_init__()

        if not 0 < self.overbought <= 100:
            raise ValueError(f"Overbought must be between 0 and 100, got {self.overbought}")

        if not 0 <= self.oversold < 100:
            raise ValueError(f"Oversold must be between 0 and 100, got {self.oversold}")

        if self.oversold >= self.overbought:
            raise ValueError("Oversold must be less than overbought")


class RSI(BaseIndicator):
    """
    Relative Strength Index (RSI) indicator implementation.

    Momentum oscillator measuring the speed and magnitude of price changes.
    Uses Wilder's smoothing method (exponential weighted average) by default.

    Features:
    - Wilder's smoothing (exponential weighted moving average)
    - Overbought/oversold level detection
    - Multi-timeframe support (daily, weekly, hourly, intraday)
    - Database-ready JSONB formatting
    - Divergence detection capability
    """

    def __init__(self, params: dict[str, Any] | None = None):
        """
        Initialize RSI indicator with parameters.

        Args:
            params: Dictionary containing:
                - period: RSI period (default: 14)
                - source: Column to use (default: 'close')
                - overbought: Overbought threshold (default: 70)
                - oversold: Oversold threshold (default: 30)
                - use_sma: Use SMA instead of EMA (default: False)
        """
        if params is None:
            params = {"period": 14, "source": "close"}

        super().__init__(params)
        self.name = "RSI"
        self.indicator_type = "momentum"

    def _validate_params(self, params: dict[str, Any]) -> RSIParams:
        """
        Validate and parse RSI parameters.

        Args:
            params: Raw parameter dictionary

        Returns:
            Validated RSIParams instance
        """
        # Extract parameters with defaults
        period = params.get("period", 14)
        source = params.get("source", "close")
        overbought = params.get("overbought", 70.0)
        oversold = params.get("oversold", 30.0)
        use_sma = params.get("use_sma", False)

        return RSIParams(
            period=period, source=source, overbought=overbought, oversold=oversold, use_sma=use_sma
        )

    def calculate(
        self, data: pd.DataFrame, symbol: str = None, timeframe: str = "daily"
    ) -> dict[str, Any]:
        """
        Calculate RSI values for given data.

        Args:
            data: DataFrame with OHLCV columns
            symbol: Stock symbol (optional)
            timeframe: Timeframe for calculation (default: 'daily')

        Returns:
            Dictionary formatted for database storage with:
                - indicator_type: 'rsi'
                - value: RSI value (primary metric)
                - value_data: Dict with rsi_14, signal, thresholds
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
        if len(data) < self.params.period + 1:
            return self._empty_result(timeframe, data, symbol, "insufficient_data")

        # Validate data
        try:
            self._validate_data_format(data)
        except IndicatorError:
            return self._empty_result(timeframe, data, symbol, "invalid_data_format")

        # Get source values
        source_values = self._get_source_values(data)

        # Calculate RSI
        rsi_value = self._calculate_rsi(source_values)

        # Determine signal
        signal = "neutral"
        overbought_flag = False
        oversold_flag = False
        confidence = 0.70  # Base confidence

        if rsi_value is not None:
            if rsi_value >= self.params.overbought:
                signal = "overbought"
                overbought_flag = True
                confidence = 0.80
            elif rsi_value <= self.params.oversold:
                signal = "oversold"
                oversold_flag = True
                confidence = 0.80

        # Check for divergence if we have enough data
        divergence = None
        if len(data) >= 20 and rsi_value is not None:
            divergence = self._check_divergence(source_values, rsi_value)

        # Calculate average gain/loss for diagnostics
        delta = source_values.diff()
        gains = delta.where(delta > 0, 0)
        losses = -delta.where(delta < 0, 0)

        # CRITICAL: Wilder's smoothing uses alpha=1/period, NOT span=period
        avg_gain = gains.ewm(
            alpha=1 / self.params.period, min_periods=self.params.period, adjust=False
        ).mean()
        avg_loss = losses.ewm(
            alpha=1 / self.params.period, min_periods=self.params.period, adjust=False
        ).mean()

        return {
            "indicator_type": "rsi",
            "symbol": symbol or "UNKNOWN",
            "timeframe": timeframe,
            "value": float(rsi_value) if rsi_value is not None else None,  # Primary value
            "value_data": {
                f"rsi_{self.params.period}": float(rsi_value) if rsi_value is not None else None,
                "signal": signal,
                "overbought": overbought_flag,
                "oversold": oversold_flag,
                "overbought_threshold": self.params.overbought,
                "oversold_threshold": self.params.oversold,
                "confidence": confidence,
                "avg_gain": round(float(avg_gain.iloc[-1]), 4) if len(avg_gain) > 0 else None,
                "avg_loss": round(float(avg_loss.iloc[-1]), 4) if len(avg_loss) > 0 else None,
                "period": self.params.period,
                "divergence": divergence,
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
                "divergence": divergence,
                "calculation_method": "sma" if self.params.use_sma else "wilder",
                "min_bars_required": self.params.period,
            },
        }

    def calculate_series(self, data: pd.DataFrame) -> pd.Series:
        """
        Calculate full RSI series for charting and analysis.

        Args:
            data: DataFrame with OHLCV columns

        Returns:
            Series with RSI values
        """
        # Get source values
        source_values = self._get_source_values(data)

        # Calculate price changes
        delta = source_values.diff()

        # Separate gains and losses
        gains = delta.where(delta > 0, 0.0)
        losses = -delta.where(delta < 0, 0.0)

        # Calculate average gains and losses
        if self.params.use_sma:
            # Simple moving average
            avg_gains = gains.rolling(
                window=self.params.period, min_periods=self.params.period
            ).mean()
            avg_losses = losses.rolling(
                window=self.params.period, min_periods=self.params.period
            ).mean()
        else:
            # Wilder's smoothing (exponential weighted with alpha=1/period)
            # CRITICAL: Use alpha=1/period and adjust=False for correct Wilder's method
            avg_gains = gains.ewm(
                alpha=1 / self.params.period, min_periods=self.params.period, adjust=False
            ).mean()
            avg_losses = losses.ewm(
                alpha=1 / self.params.period, min_periods=self.params.period, adjust=False
            ).mean()

        # Calculate RS and RSI
        # Use pandas division which handles division by zero gracefully
        rs = avg_gains / avg_losses
        rsi = 100 - (100 / (1 + rs))

        # Handle edge cases
        rsi = rsi.fillna(100.0)  # If all losses are 0, RSI is 100
        rsi[avg_gains == 0] = 0.0  # If all gains are 0, RSI is 0

        return rsi

    def _calculate_rsi(self, source_values: pd.Series) -> float | None:
        """
        Calculate single RSI value.

        Args:
            source_values: Series of price values

        Returns:
            Latest RSI value or None if calculation fails
        """
        if len(source_values) < self.params.period + 1:
            return None

        # Calculate full series
        rsi_series = self.calculate_series(pd.DataFrame({self.params.source: source_values}))

        # Return latest non-NaN value
        latest = rsi_series.iloc[-1]
        return float(latest) if not pd.isna(latest) else None

    def _check_divergence(self, prices: pd.Series, current_rsi: float) -> str | None:
        """
        Check for bullish or bearish divergence.

        Args:
            prices: Price series
            current_rsi: Current RSI value

        Returns:
            'bullish', 'bearish', or None
        """
        # Get recent peaks and troughs (simplified)
        lookback = min(50, len(prices) - 1)
        recent_prices = prices.iloc[-lookback:]
        rsi_series = self.calculate_series(pd.DataFrame({self.params.source: prices}))
        recent_rsi = rsi_series.iloc[-lookback:]

        # Find local extrema (simplified approach)
        price_min_idx = recent_prices.idxmin()
        price_max_idx = recent_prices.idxmax()
        rsi_at_price_min = recent_rsi.loc[price_min_idx]
        rsi_at_price_max = recent_rsi.loc[price_max_idx]

        # Bullish divergence: price makes lower low, RSI makes higher low
        if prices.iloc[-1] < recent_prices.min() * 1.01 and current_rsi > rsi_at_price_min:
            return "bullish"

        # Bearish divergence: price makes higher high, RSI makes lower high
        if prices.iloc[-1] > recent_prices.max() * 0.99 and current_rsi < rsi_at_price_max:
            return "bearish"

        return None

    def get_minimum_periods(self) -> int:
        """
        Get minimum number of periods required for calculation.

        Returns:
            Period + 1 for RSI calculation
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
            "indicator_type": "rsi",
            "symbol": symbol or "UNKNOWN",
            "timeframe": timeframe,
            "value": None,  # Primary value (convention)
            "value_data": {f"rsi_{self.params.period}": None},
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
