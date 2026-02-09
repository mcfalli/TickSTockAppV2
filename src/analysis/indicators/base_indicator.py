"""
BaseIndicator abstract class for consistent indicator implementations.

Provides standardized interface and validation for all indicator calculations
with performance optimization patterns and memory-efficient operations.

Sprint 68: Core Analysis Migration from TickStockPL
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

from ..exceptions import IndicatorError


@dataclass
class IndicatorParams:
    """Base parameter configuration for indicators."""

    period: int
    source: str = "close"  # OHLCV column to use

    def __post_init__(self):
        """Validate parameters after initialization."""
        if self.period <= 0:
            raise ValueError("Period must be positive")

        valid_sources = ["open", "high", "low", "close", "volume"]
        if self.source not in valid_sources:
            raise ValueError(f"Source must be one of: {valid_sources}")


class BaseIndicator(ABC):
    """
    Abstract base class for all indicator implementations.

    Provides standardized interface for indicator calculations with:
    - Consistent parameter validation and error handling
    - Memory-efficient DataFrame operations
    - Performance optimization patterns for streaming calculations
    - Common utility methods for sliding window operations

    Performance Requirements:
    - <500ms calculation time for 250 bars
    - Memory-efficient vectorized operations
    - Support for streaming updates with minimal computation

    Return Format Convention (for database storage):
        {
            'indicator_type': str,              # Indicator name (e.g., 'rsi', 'sma')
            'symbol': str,                      # Stock symbol
            'timeframe': str,                   # Timeframe ('daily', 'hourly', etc.)
            'value': float,                     # Primary indicator value (latest)
            'value_data': dict,                 # All calculated values
            'calculation_timestamp': str,       # ISO timestamp
            'metadata': dict                    # Additional metadata
        }
    """

    def __init__(self, params: dict[str, Any]):
        """
        Initialize indicator with validated parameters.

        Args:
            params: Dictionary of indicator parameters

        Raises:
            IndicatorError: If parameter validation fails
        """
        try:
            self.params = self._validate_params(params)
            self.indicator_name = self.__class__.__name__
        except Exception as e:
            raise IndicatorError(
                f"Parameter validation failed for {self.__class__.__name__}: {e}",
                indicator_name=self.__class__.__name__,
            )

    @abstractmethod
    def calculate(
        self, data: pd.DataFrame, symbol: str = None, timeframe: str = "daily"
    ) -> dict[str, Any]:
        """
        Calculate indicator values for given data.

        CRITICAL: Must return dict with standardized format for database storage:
        {
            'indicator_type': 'indicator_name',
            'symbol': symbol,
            'timeframe': timeframe,
            'value': float (primary metric),
            'value_data': dict (all calculated values),
            'calculation_timestamp': ISO timestamp,
            'metadata': dict (signals, thresholds, etc.)
        }

        Args:
            data: DataFrame with OHLCV columns
            symbol: Stock symbol (optional)
            timeframe: Timeframe for calculation (default: 'daily')

        Returns:
            Dictionary with standardized format

        Raises:
            IndicatorError: If calculation fails
        """
        pass

    @abstractmethod
    def _validate_params(self, params: dict[str, Any]) -> IndicatorParams:
        """
        Validate and parse indicator parameters.

        Args:
            params: Raw parameter dictionary

        Returns:
            Validated IndicatorParams instance

        Raises:
            ValueError: If validation fails
        """
        pass

    def get_minimum_periods(self) -> int:
        """
        Get minimum number of periods required for calculation.

        Returns:
            Minimum periods required
        """
        return getattr(self.params, "period", 1)

    def can_calculate(self, data: pd.DataFrame) -> bool:
        """
        Check if indicator can be calculated with given data.

        Args:
            data: DataFrame to check

        Returns:
            True if calculation is possible
        """
        try:
            self._validate_data_format(data)
            return len(data) >= self.get_minimum_periods()
        except Exception:
            return False

    def _validate_data_format(self, data: pd.DataFrame) -> None:
        """
        Validate DataFrame format for indicator calculation.

        Args:
            data: DataFrame to validate

        Raises:
            IndicatorError: If data format is invalid
        """
        if data.empty:
            raise IndicatorError("Data cannot be empty", indicator_name=self.indicator_name)

        required_columns = ["open", "high", "low", "close", "volume"]
        missing_columns = [col for col in required_columns if col not in data.columns]

        if missing_columns:
            raise IndicatorError(
                f"Missing required columns: {missing_columns}",
                indicator_name=self.indicator_name,
            )

        # Check for sufficient data
        if len(data) < self.get_minimum_periods():
            raise IndicatorError(
                f"Insufficient data: need {self.get_minimum_periods()}, got {len(data)}",
                indicator_name=self.indicator_name,
                data_length=len(data),
                required_length=self.get_minimum_periods(),
            )

    def _get_source_values(self, data: pd.DataFrame) -> pd.Series:
        """
        Get values from specified source column.

        Args:
            data: DataFrame with OHLCV data

        Returns:
            Series with source values

        Raises:
            IndicatorError: If source column not found
        """
        if self.params.source not in data.columns:
            raise IndicatorError(
                f"Source column '{self.params.source}' not found",
                indicator_name=self.indicator_name,
            )

        return data[self.params.source]

    def _safe_divide(
        self,
        numerator: pd.Series | np.ndarray | float,
        denominator: pd.Series | np.ndarray | float,
        default: float = 0.0,
    ) -> pd.Series | np.ndarray | float:
        """
        Perform safe division avoiding division by zero.

        CRITICAL: Always use this for ratio calculations to prevent NaN/Inf values.

        Args:
            numerator: Numerator values
            denominator: Denominator values
            default: Default value for division by zero

        Returns:
            Division result with safe handling
        """
        if isinstance(denominator, (pd.Series, np.ndarray)):
            return np.where(denominator != 0, numerator / denominator, default)
        return numerator / denominator if denominator != 0 else default

    def _rolling_calculation(
        self, data: pd.Series, window: int, func_name: str, **kwargs
    ) -> pd.Series:
        """
        Perform rolling window calculation with error handling.

        Args:
            data: Series to calculate on
            window: Rolling window size
            func_name: Name of pandas rolling function ('mean', 'std', 'min', 'max', etc.)
            **kwargs: Additional arguments for rolling function

        Returns:
            Series with rolling calculation results

        Raises:
            IndicatorError: If calculation fails
        """
        try:
            rolling_obj = data.rolling(window, **kwargs)
            func = getattr(rolling_obj, func_name)
            return func()
        except Exception as e:
            raise IndicatorError(
                f"Rolling {func_name} calculation failed: {e}",
                indicator_name=self.indicator_name,
            )

    def _exponential_smoothing(self, data: pd.Series, alpha: float) -> pd.Series:
        """
        Apply exponential smoothing to data series.

        CRITICAL: For Wilder's smoothing (RSI), use alpha=1/period.
                  For standard EMA, use span parameter instead.

        Args:
            data: Series to smooth
            alpha: Smoothing factor (0 < alpha <= 1)

        Returns:
            Exponentially smoothed series
        """
        if not 0 < alpha <= 1:
            raise IndicatorError(
                f"Alpha must be between 0 and 1, got {alpha}",
                indicator_name=self.indicator_name,
            )

        return data.ewm(alpha=alpha, adjust=False).mean()

    def _true_range(self, data: pd.DataFrame) -> pd.Series:
        """
        Calculate True Range for volatility-based indicators (ATR, etc.).

        True Range = max(high-low, |high-prev_close|, |low-prev_close|)

        Args:
            data: DataFrame with OHLC data

        Returns:
            Series with True Range values
        """
        high_low = data["high"] - data["low"]
        high_close_prev = np.abs(data["high"] - data["close"].shift(1))
        low_close_prev = np.abs(data["low"] - data["close"].shift(1))

        return np.maximum(high_low, np.maximum(high_close_prev, low_close_prev))

    def _empty_result(
        self, timeframe: str, data: pd.DataFrame, symbol: str = None, reason: str = None
    ) -> dict[str, Any]:
        """
        Generate empty result dictionary when calculation cannot proceed.

        Args:
            timeframe: Timeframe being calculated
            data: Input data
            symbol: Stock symbol
            reason: Reason for empty result

        Returns:
            Empty result dictionary with standardized format
        """
        return {
            "indicator_type": self.indicator_name.lower(),
            "symbol": symbol,
            "timeframe": timeframe,
            "value": None,
            "value_data": {},
            "calculation_timestamp": (
                data["timestamp"].iloc[-1].isoformat() if not data.empty else None
            ),
            "metadata": {"reason": reason or "insufficient_data", "data_length": len(data)},
        }

    def get_indicator_metadata(self) -> dict[str, Any]:
        """
        Get metadata about indicator configuration.

        Returns:
            Dictionary with indicator metadata
        """
        return {
            "indicator_name": self.indicator_name,
            "parameters": self.params.__dict__ if hasattr(self.params, "__dict__") else {},
            "minimum_periods": self.get_minimum_periods(),
            "source_column": getattr(self.params, "source", "close"),
        }

    def __str__(self) -> str:
        """String representation of indicator."""
        return f"{self.indicator_name}({self.params})"

    def __repr__(self) -> str:
        """Detailed string representation."""
        return f"{self.__class__.__name__}(params={self.params})"
