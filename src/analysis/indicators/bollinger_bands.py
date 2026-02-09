"""
Bollinger Bands indicator implementation.

Sprint 70: Indicator Library Extension
Volatility bands based on standard deviations from moving average.
"""

from dataclasses import dataclass
from typing import Any

import pandas as pd

from .base_indicator import BaseIndicator, IndicatorParams
from ..exceptions import IndicatorError


@dataclass
class BollingerBandsParams(IndicatorParams):
    """Parameters for Bollinger Bands calculation."""

    num_std_dev: float = 2.0  # Number of standard deviations for bands

    def __post_init__(self):
        """Validate Bollinger Bands-specific parameters."""
        super().__post_init__()

        if self.num_std_dev <= 0:
            raise ValueError(f"num_std_dev must be positive, got {self.num_std_dev}")


class BollingerBands(BaseIndicator):
    """
    Bollinger Bands indicator implementation.

    Volatility bands consisting of:
    - Middle band: Simple Moving Average
    - Upper band: Middle + (num_std_dev * standard deviation)
    - Lower band: Middle - (num_std_dev * standard deviation)
    - %B: Price position within bands (0-1 range)
    - Bandwidth: Measure of band width (volatility)

    Features:
    - Configurable period and standard deviations
    - %B (Percent B) position indicator
    - Bandwidth volatility measure
    - Multi-timeframe support
    - Database-ready JSONB formatting
    - Squeeze and expansion detection
    """

    def __init__(self, params: dict[str, Any] | None = None):
        """
        Initialize Bollinger Bands indicator with parameters.

        Args:
            params: Dictionary containing:
                - period: SMA period (default: 20)
                - num_std_dev: Standard deviations for bands (default: 2.0)
                - source: Column to use (default: 'close')
        """
        if params is None:
            params = {"period": 20, "num_std_dev": 2.0, "source": "close"}

        super().__init__(params)
        self.name = "BollingerBands"
        self.indicator_type = "volatility"

    def _validate_params(self, params: dict[str, Any]) -> BollingerBandsParams:
        """
        Validate and parse Bollinger Bands parameters.

        Args:
            params: Raw parameter dictionary

        Returns:
            Validated BollingerBandsParams instance
        """
        # Extract parameters with defaults
        period = params.get("period", 20)
        num_std_dev = params.get("num_std_dev", 2.0)
        source = params.get("source", "close")

        return BollingerBandsParams(period=period, num_std_dev=num_std_dev, source=source)

    def calculate(
        self, data: pd.DataFrame, symbol: str = None, timeframe: str = "daily"
    ) -> dict[str, Any]:
        """
        Calculate Bollinger Bands values for given data.

        Args:
            data: DataFrame with OHLCV columns
            symbol: Stock symbol (optional)
            timeframe: Timeframe for calculation (default: 'daily')

        Returns:
            Dictionary formatted for database storage with:
                - indicator_type: 'bollinger_bands'
                - value: %B (price position within bands)
                - value_data: Dict with upper, middle, lower, percent_b, bandwidth
                - calculation_timestamp: Latest data timestamp
                - timeframe: Timeframe used
                - metadata: Band position and squeeze detection

        Raises:
            IndicatorError: If calculation fails
        """
        # Validate timeframe
        valid_timeframes = ["daily", "weekly", "hourly", "intraday", "monthly", "1min"]
        if timeframe not in valid_timeframes:
            return self._empty_result(timeframe, data, symbol)

        # Check minimum data requirements
        if len(data) < self.params.period:
            return self._empty_result(timeframe, data, symbol, "insufficient_data")

        # Validate data
        try:
            self._validate_data_format(data)
        except IndicatorError:
            return self._empty_result(timeframe, data, symbol, "invalid_data_format")

        # Get source values
        source_values = self._get_source_values(data)
        current_price = float(source_values.iloc[-1])

        # Calculate middle band (SMA)
        middle_band = source_values.rolling(window=self.params.period, min_periods=self.params.period).mean()
        middle_value = float(middle_band.iloc[-1]) if not pd.isna(middle_band.iloc[-1]) else None

        if middle_value is None:
            return self._empty_result(timeframe, data, symbol, "calculation_failed")

        # Calculate standard deviation
        std_dev = source_values.rolling(window=self.params.period, min_periods=self.params.period).std()
        std_value = float(std_dev.iloc[-1]) if not pd.isna(std_dev.iloc[-1]) else None

        if std_value is None:
            return self._empty_result(timeframe, data, symbol, "calculation_failed")

        # Calculate upper and lower bands
        upper_band = middle_value + (self.params.num_std_dev * std_value)
        lower_band = middle_value - (self.params.num_std_dev * std_value)

        # Calculate %B (Percent B): where price is within the bands
        # %B = (Price - Lower) / (Upper - Lower)
        # Values: >1 = above upper, 0.5 = middle, <0 = below lower
        band_range = upper_band - lower_band
        if band_range > 0:
            percent_b = (current_price - lower_band) / band_range
        else:
            percent_b = 0.5  # Default to middle if bands are flat

        # Calculate bandwidth: (Upper - Lower) / Middle * 100
        # Measures volatility - low values indicate squeeze
        bandwidth = (band_range / middle_value) * 100 if middle_value > 0 else 0.0

        # Determine position signal
        position_signal = "middle"
        if percent_b > 1.0:
            position_signal = "above_upper"
        elif percent_b > 0.8:
            position_signal = "near_upper"
        elif percent_b < 0.0:
            position_signal = "below_lower"
        elif percent_b < 0.2:
            position_signal = "near_lower"

        # Detect squeeze (low volatility) - bandwidth < 10% considered squeeze
        squeeze_detected = bandwidth < 10.0

        # Detect expansion (high volatility) - compare current to 50-bar average
        expansion_detected = False
        if len(data) >= 50:
            # Calculate historical bandwidth
            hist_middle = source_values.rolling(window=self.params.period, min_periods=self.params.period).mean()
            hist_std = source_values.rolling(window=self.params.period, min_periods=self.params.period).std()
            hist_bandwidth = ((hist_std * self.params.num_std_dev * 2) / hist_middle) * 100
            avg_bandwidth = hist_bandwidth.iloc[-50:].mean()

            if bandwidth > avg_bandwidth * 1.5:
                expansion_detected = True

        return {
            "indicator_type": "bollinger_bands",
            "symbol": symbol or "UNKNOWN",
            "timeframe": timeframe,
            "value": round(percent_b, 4),  # Primary value: %B
            "value_data": {
                "upper_band": round(upper_band, 4),
                "middle_band": round(middle_value, 4),
                "lower_band": round(lower_band, 4),
                "percent_b": round(percent_b, 4),
                "bandwidth": round(bandwidth, 4),
                "current_price": round(current_price, 4),
                "std_dev": round(std_value, 4),
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
                "position_signal": position_signal,
                "squeeze_detected": squeeze_detected,
                "expansion_detected": expansion_detected,
                "period": self.params.period,
                "num_std_dev": self.params.num_std_dev,
            },
        }

    def calculate_series(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate full Bollinger Bands series for charting and analysis.

        Args:
            data: DataFrame with OHLCV columns

        Returns:
            DataFrame with upper_band, middle_band, lower_band, percent_b columns
        """
        # Get source values
        source_values = self._get_source_values(data)

        # Calculate middle band (SMA)
        middle_band = source_values.rolling(window=self.params.period, min_periods=self.params.period).mean()

        # Calculate standard deviation
        std_dev = source_values.rolling(window=self.params.period, min_periods=self.params.period).std()

        # Calculate upper and lower bands
        upper_band = middle_band + (self.params.num_std_dev * std_dev)
        lower_band = middle_band - (self.params.num_std_dev * std_dev)

        # Calculate %B
        band_range = upper_band - lower_band
        percent_b = (source_values - lower_band) / band_range
        percent_b = percent_b.fillna(0.5)  # Default to middle if bands are flat

        # Calculate bandwidth
        bandwidth = (band_range / middle_band) * 100
        bandwidth = bandwidth.fillna(0.0)

        # Create result DataFrame
        result = pd.DataFrame(
            {
                "upper_band": upper_band,
                "middle_band": middle_band,
                "lower_band": lower_band,
                "percent_b": percent_b,
                "bandwidth": bandwidth,
            },
            index=data.index,
        )

        return result

    def get_minimum_periods(self) -> int:
        """
        Get minimum number of periods required for calculation.

        Returns:
            Period for SMA calculation
        """
        return self.params.period

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
            "indicator_type": "bollinger_bands",
            "symbol": symbol or "UNKNOWN",
            "timeframe": timeframe,
            "value": None,  # Primary value (convention)
            "value_data": {
                "upper_band": None,
                "middle_band": None,
                "lower_band": None,
                "percent_b": None,
                "bandwidth": None,
            },
            "calculation_timestamp": (
                data["timestamp"].iloc[-1].isoformat() if "timestamp" in data.columns else None
            )
            if len(data) > 0
            else None,
            "metadata": {
                "position_signal": "invalid",
                "error": reason or "Invalid timeframe or insufficient data",
            },
        }
