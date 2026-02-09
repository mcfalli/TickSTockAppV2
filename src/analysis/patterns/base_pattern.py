"""
Base pattern class for all TickStock pattern implementations with Sprint 17 enhancements.

Sprint 68: Core Analysis Migration from TickStockPL
"""

from abc import ABC, abstractmethod
from typing import Any

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field, field_validator

from ..exceptions import PatternDetectionError


class PatternParams(BaseModel):
    """Base parameter model for pattern configuration."""

    timeframe: str = Field(default="daily")

    @field_validator("timeframe")
    @classmethod
    def validate_timeframe(cls, value):
        valid_timeframes = ["1min", "5min", "15min", "30min", "1hour", "4hour", "daily", "weekly", "monthly"]
        if value not in valid_timeframes:
            raise ValueError(f"Timeframe must be one of: {valid_timeframes}")
        return value


class BasePattern(ABC):
    """
    Abstract base class for all pattern implementations with Sprint 17 enhancements.

    ENHANCED FOR SPRINT 17:
    - Pattern registry integration for metadata and configuration
    - Confidence scoring support for threshold enforcement
    - Pattern ID mapping for detection result tracking
    - Enhanced event metadata with pattern registry information

    Enforces consistent interface and parameter handling across all patterns.
    Supports multi-timeframe detection with parameter validation.

    CRITICAL: detect() MUST return pd.Series (boolean), NOT dict or custom object.
    """

    def __init__(self, params: dict[str, Any] | None = None):
        """
        Initialize pattern with validated parameters and Sprint 17 enhancements.

        Args:
            params: Dictionary of pattern-specific parameters

        Raises:
            ValueError: If parameters fail validation
        """
        self.params = self._validate_and_parse_params(params or {})
        self.pattern_name = self.__class__.__name__
        self.timeframe = self.params.timeframe

        # Sprint 17: Pattern registry integration
        self._pattern_id: int | None = None
        self._confidence_threshold: float | None = None
        self._registry_metadata: dict[str, Any] | None = None
        self._supports_confidence_scoring: bool = False

    @abstractmethod
    def detect(self, data: pd.DataFrame) -> pd.Series:
        """
        Detect pattern occurrences in OHLCV data.

        CRITICAL: MUST return pd.Series (boolean indexed by timestamp), NOT dict!

        Args:
            data: DataFrame with columns ['timestamp', 'open', 'high', 'low', 'close', 'volume']
                 Indexed by timestamp, sorted ascending

        Returns:
            Boolean Series indexed by timestamp indicating pattern detection

        Raises:
            ValueError: If data format is invalid
            PatternDetectionError: If detection logic fails
        """
        pass

    def get_minimum_bars(self) -> int:
        """
        Get minimum number of bars required for pattern detection.

        Returns:
            Minimum bars required (default: 1 for single-bar patterns)
        """
        return 1

    def requires_multi_bar(self) -> bool:
        """
        Check if pattern requires multi-bar analysis.

        Returns:
            True if pattern needs multiple bars for detection
        """
        return self.get_minimum_bars() > 1

    def _validate_and_parse_params(self, params: dict[str, Any]) -> PatternParams:
        """
        Validate and parse pattern parameters using Pydantic.

        Args:
            params: Raw parameter dictionary

        Returns:
            Validated PatternParams instance

        Raises:
            ValueError: If parameter validation fails
        """
        try:
            return PatternParams(**params)
        except Exception as e:
            raise ValueError(f"Parameter validation failed for {self.__class__.__name__}: {e}")

    def _validate_data_format(self, data: pd.DataFrame) -> None:
        """
        Validate OHLCV data format and structure.

        Args:
            data: Input DataFrame to validate

        Raises:
            ValueError: If data format is invalid
        """
        required_columns = ["timestamp", "open", "high", "low", "close", "volume"]
        missing_columns = [col for col in required_columns if col not in data.columns]

        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")

        if data.empty:
            raise ValueError("Input data is empty")

        if not pd.api.types.is_datetime64_any_dtype(data["timestamp"]):
            raise ValueError("Timestamp column must be datetime type")

    def get_event_metadata(
        self, symbol: str, timestamp: str, price: float, **kwargs
    ) -> dict[str, Any]:
        """
        Generate standardized event metadata for pattern detection with Sprint 17 enhancements.

        ENHANCED FOR SPRINT 17:
        - Includes pattern_id from registry mapping
        - Adds confidence threshold information
        - Enhanced metadata with registry information

        Args:
            symbol: Stock symbol (e.g., "AAPL")
            timestamp: Detection timestamp (ISO format)
            price: Detection price
            **kwargs: Additional pattern-specific metadata

        Returns:
            Standardized event metadata dictionary with Sprint 17 enhancements
        """
        base_metadata = {
            "pattern": self.pattern_name,
            "symbol": symbol,
            "timestamp": timestamp,
            "price": price,
            "timeframe": self.timeframe,
            "metadata": {"params": self.params.model_dump(), **kwargs},
        }

        # Sprint 17: Add pattern registry enhancements
        if self._pattern_id is not None:
            base_metadata["pattern_id"] = self._pattern_id

        if self._confidence_threshold is not None:
            base_metadata["confidence_threshold"] = self._confidence_threshold

        if self._registry_metadata:
            base_metadata["registry_metadata"] = self._registry_metadata.copy()

        base_metadata["supports_confidence_scoring"] = self._supports_confidence_scoring

        return base_metadata

    # =============================================================================
    # Sprint 17 Pattern Registry Integration Methods
    # =============================================================================

    def set_pattern_registry_info(
        self, pattern_id: int, confidence_threshold: float, metadata: dict[str, Any] | None = None
    ) -> None:
        """
        Set pattern registry information for Sprint 17 integration.

        Args:
            pattern_id: Pattern ID from pattern_definitions table
            confidence_threshold: Minimum confidence threshold for detections
            metadata: Additional registry metadata
        """
        self._pattern_id = pattern_id
        self._confidence_threshold = confidence_threshold
        self._registry_metadata = metadata or {}

    def get_pattern_id(self) -> int | None:
        """Get pattern ID from registry integration."""
        return self._pattern_id

    def get_confidence_threshold(self) -> float | None:
        """Get confidence threshold from registry integration."""
        return self._confidence_threshold

    def supports_confidence_scoring(self) -> bool:
        """
        Check if pattern supports confidence scoring for threshold enforcement.

        Returns:
            True if pattern can provide confidence scores
        """
        return self._supports_confidence_scoring

    def enable_confidence_scoring(self) -> None:
        """
        Enable confidence scoring support for this pattern.
        Should be called by pattern implementations that support confidence scoring.
        """
        self._supports_confidence_scoring = True

    def calculate_confidence(
        self, data: pd.DataFrame, detection_indices: pd.Index
    ) -> dict[Any, float]:
        """
        Calculate confidence scores for detected patterns.

        This is a default implementation that returns 1.0 for all detections.
        Pattern implementations should override this method to provide meaningful confidence scores.

        Args:
            data: OHLCV DataFrame
            detection_indices: Indices where patterns were detected

        Returns:
            Dictionary mapping detection indices to confidence scores (0.0 to 1.0)
        """
        # Default implementation - patterns can override this
        return dict.fromkeys(detection_indices, 1.0)

    def filter_by_confidence(self, detections: pd.Series, data: pd.DataFrame) -> pd.Series:
        """
        Filter detections by confidence threshold if supported.

        Args:
            detections: Raw detection results
            data: OHLCV DataFrame

        Returns:
            Filtered detection results based on confidence threshold
        """
        if not self._supports_confidence_scoring or self._confidence_threshold is None:
            # No confidence scoring or threshold - return all detections
            return detections

        # Get detection indices
        detection_indices = detections[detections].index
        if len(detection_indices) == 0:
            return detections

        # Calculate confidence scores
        confidence_scores = self.calculate_confidence(data, detection_indices)

        # Filter by threshold
        filtered_detections = detections.copy()
        for idx in detection_indices:
            confidence = confidence_scores.get(idx, 0.0)
            if confidence < self._confidence_threshold:
                filtered_detections.loc[idx] = False

        return filtered_detections

    # =============================================================================
    # Utility Methods for Pattern Detection
    # =============================================================================

    def calculate_body_size(self, data: pd.DataFrame) -> pd.Series:
        """
        Calculate candlestick body size (abs(close - open)).

        Args:
            data: DataFrame with open and close columns

        Returns:
            Series with body sizes
        """
        return np.abs(data["close"] - data["open"])

    def calculate_candle_range(self, data: pd.DataFrame) -> pd.Series:
        """
        Calculate full candle range (high - low).

        Args:
            data: DataFrame with high and low columns

        Returns:
            Series with candle ranges
        """
        return data["high"] - data["low"]

    def is_bullish_candle(self, data: pd.DataFrame) -> pd.Series:
        """
        Check if candles are bullish (close > open).

        Args:
            data: DataFrame with open and close columns

        Returns:
            Boolean Series indicating bullish candles
        """
        return data["close"] > data["open"]

    def is_bearish_candle(self, data: pd.DataFrame) -> pd.Series:
        """
        Check if candles are bearish (close < open).

        Args:
            data: DataFrame with open and close columns

        Returns:
            Boolean Series indicating bearish candles
        """
        return data["close"] < data["open"]
