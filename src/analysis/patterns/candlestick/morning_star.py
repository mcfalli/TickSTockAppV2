"""
Morning Star candlestick pattern detection.

Sprint 69: Pattern Library Extension
Three-bar bullish reversal pattern (downtrend → small body → uptrend).
"""

from typing import Any

import pandas as pd
from pydantic import Field, field_validator

from ..base_pattern import BasePattern, PatternParams
from ...exceptions import PatternDetectionError


class MorningStarParams(PatternParams):
    """Parameters for Morning Star pattern detection."""

    min_gap_ratio: float = Field(default=0.1, description="Min gap size ratio of first candle range")
    body_size_threshold: float = Field(default=0.3, description="Middle candle max body ratio (indecision)")
    min_reversal_close: float = Field(default=0.5, description="Third candle must close >= this ratio into first body")
    min_range: float = Field(default=0.001, description="Min candle range")

    @field_validator("min_gap_ratio", "body_size_threshold", "min_reversal_close")
    @classmethod
    def validate_ratio_range(cls, value):
        if not 0 < value < 1:
            raise ValueError(f"Ratio must be between 0 and 1, got {value}")
        return value

    @field_validator("min_range")
    @classmethod
    def validate_min_range(cls, value):
        if value <= 0:
            raise ValueError(f"min_range must be positive, got {value}")
        return value


class MorningStar(BasePattern):
    """
    Morning Star candlestick pattern detector.

    A Morning Star is a three-bar bullish reversal pattern that appears at the
    bottom of a downtrend, signaling potential upward reversal.

    Pattern Structure:
    - Bar 1: Long bearish (downtrend continuation)
    - Bar 2: Small body (indecision), ideally gaps down from Bar 1
    - Bar 3: Long bullish candle closing well into Bar 1's body

    Characteristics:
    - Three-bar pattern
    - Bar 2 can be bullish or bearish (small body indicates indecision)
    - Gap down between Bar 1 and Bar 2 strengthens pattern (optional)
    - Bar 3 must show strong bullish conviction

    Features:
    - Three-bar pattern (minimum 3 bars required)
    - Sprint 17 confidence scoring support
    - Vectorized detection for efficiency
    - OHLC-consistent validation
    - Gap detection logic
    """

    def __init__(self, params: dict[str, Any] | None = None):
        """
        Initialize Morning Star pattern detector.

        Args:
            params: Dictionary containing:
                - min_gap_ratio: Min gap size ratio (default: 0.1)
                - body_size_threshold: Max middle body ratio (default: 0.3)
                - min_reversal_close: Min close into first body (default: 0.5)
                - min_range: Min candle range (default: 0.001)
                - timeframe: Detection timeframe (default: 'daily')
        """
        super().__init__(params)
        self.enable_confidence_scoring()

    def _validate_and_parse_params(self, params: dict[str, Any]) -> MorningStarParams:
        """Validate and parse Morning Star parameters."""
        return MorningStarParams(**params)

    def detect(self, data: pd.DataFrame) -> pd.Series:
        """
        Detect Morning Star patterns in OHLCV data.

        Args:
            data: DataFrame with columns ['timestamp', 'open', 'high', 'low', 'close', 'volume']

        Returns:
            Boolean Series indexed by timestamp indicating Morning Star detection
            (detection marked at the third/reversal candle)

        Raises:
            ValueError: If data format is invalid
            PatternDetectionError: If detection logic fails
        """
        try:
            self._validate_data_format(data)

            if len(data) < 3:
                # Need at least 3 bars for morning star pattern
                return pd.Series(False, index=data.index)

            # Calculate metrics
            body_size = self.calculate_body_size(data)
            candle_range = self.calculate_candle_range(data)

            # Calculate body top/bottom
            body_top = data[["open", "close"]].max(axis=1)
            body_bottom = data[["open", "close"]].min(axis=1)

            # Get previous bars (shift forward)
            prev1_body_size = body_size.shift(1)  # Bar -1 (middle)
            prev2_body_size = body_size.shift(2)  # Bar -2 (first)

            prev1_body_top = body_top.shift(1)
            prev1_body_bottom = body_bottom.shift(1)
            prev2_body_top = body_top.shift(2)
            prev2_body_bottom = body_bottom.shift(2)

            prev2_range = candle_range.shift(2)

            # Check candle types
            is_bearish = self.is_bearish_candle(data)
            prev2_is_bearish = is_bearish.shift(2)

            # Filter valid range
            valid_range = candle_range >= self.params.min_range

            # Morning Star criteria:
            # 1. First candle (bar -2): Bearish with significant body
            first_bearish = prev2_is_bearish

            # 2. Middle candle (bar -1): Small body (indecision)
            middle_small_body = (prev1_body_size <= self.params.body_size_threshold * prev2_range)

            # 3. Third candle (current): Bullish, closes well into first candle's body
            third_bullish = self.is_bullish_candle(data)

            # Calculate how far third candle closes into first candle's body
            first_body_midpoint = (prev2_body_top + prev2_body_bottom) / 2
            closes_into_first_body = data["close"] >= first_body_midpoint

            # Optional: Check for gap down between first and middle candle
            # Gap down: middle candle's high < first candle's low
            prev1_high = data["high"].shift(1)
            prev2_low = data["low"].shift(2)
            gap_down = prev1_high < prev2_low

            # Morning Star detection
            morning_star_detected = (
                valid_range
                & first_bearish
                & middle_small_body
                & third_bullish
                & closes_into_first_body
            )

            # Bonus for gap (not required, but increases confidence if present)
            # We'll use this in confidence scoring

            # First two bars cannot have morning star (need 3 bars)
            morning_star_detected.iloc[0] = False
            morning_star_detected.iloc[1] = False

            return morning_star_detected

        except Exception as e:
            raise PatternDetectionError(f"Morning Star detection failed: {e}") from e

    def get_minimum_bars(self) -> int:
        """Morning Star requires 3 bars."""
        return 3

    def calculate_confidence(
        self, data: pd.DataFrame, detection_indices: pd.Index
    ) -> dict[Any, float]:
        """
        Calculate confidence scores for Morning Star detections.

        Confidence based on:
        - Gap presence (gap down between first and middle = bonus)
        - Third candle strength (larger body = higher confidence)
        - Middle candle size (smaller = higher confidence)
        - Third candle closes deep into first body (higher = more confidence)

        Args:
            data: OHLCV DataFrame
            detection_indices: Indices where Morning Star was detected

        Returns:
            Dictionary mapping detection indices to confidence scores (0.6 to 1.0)
        """
        confidence_scores = {}

        body_size = self.calculate_body_size(data)

        for idx in detection_indices:
            # Get index position
            idx_pos = data.index.get_loc(idx)
            if idx_pos < 2:
                continue  # Skip first two bars (need 3 bars)

            first_idx = data.index[idx_pos - 2]
            middle_idx = data.index[idx_pos - 1]

            # Base confidence
            confidence = 0.6

            # Bonus for gap down (middle high < first low)
            if data.loc[middle_idx, "high"] < data.loc[first_idx, "low"]:
                confidence += 0.15

            # Bonus for very small middle candle
            middle_body_ratio = body_size.loc[middle_idx] / (data.loc[first_idx, "high"] - data.loc[first_idx, "low"])
            if middle_body_ratio < 0.2:
                confidence += 0.10

            # Bonus for strong third candle (large bullish body)
            third_body_ratio = body_size.loc[idx] / (data.loc[idx, "high"] - data.loc[idx, "low"])
            if third_body_ratio > 0.7:
                confidence += 0.10

            # Bonus for deep close into first body
            first_body_top = max(data.loc[first_idx, "open"], data.loc[first_idx, "close"])
            first_body_bottom = min(data.loc[first_idx, "open"], data.loc[first_idx, "close"])
            first_body_size = first_body_top - first_body_bottom

            if first_body_size > 0:
                penetration = (data.loc[idx, "close"] - first_body_bottom) / first_body_size
                if penetration > 0.7:  # Closes > 70% into first body
                    confidence += 0.05

            confidence_scores[idx] = round(min(confidence, 1.0), 3)

        return confidence_scores
