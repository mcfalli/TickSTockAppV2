"""
Engulfing candlestick pattern detection.

Sprint 68: Core Analysis Migration from TickStockPL
Two-bar pattern where current candle completely engulfs the previous candle.
"""

from typing import Any

import pandas as pd
from pydantic import Field, field_validator

from ..base_pattern import BasePattern, PatternParams
from ...exceptions import PatternDetectionError


class EngulfingParams(PatternParams):
    """Parameters for Engulfing pattern detection."""

    min_body_ratio: float = Field(default=1.0, description="Current body must be >= this ratio of previous")
    require_opposite_colors: bool = Field(default=True, description="Require opposite candle colors")
    min_range: float = Field(default=0.001, description="Min candle range")

    @field_validator("min_body_ratio")
    @classmethod
    def validate_min_body_ratio(cls, value):
        if value < 1.0:
            raise ValueError(f"min_body_ratio must be >= 1.0, got {value}")
        return value

    @field_validator("min_range")
    @classmethod
    def validate_min_range(cls, value):
        if value <= 0:
            raise ValueError(f"min_range must be positive, got {value}")
        return value


class Engulfing(BasePattern):
    """
    Engulfing candlestick pattern detector.

    An Engulfing pattern occurs when the current candle's body completely
    engulfs the previous candle's body. Can be bullish or bearish.

    Bullish Engulfing:
    - Previous candle: bearish (red/down)
    - Current candle: bullish (green/up)
    - Current body engulfs previous body
    - Indicates potential bullish reversal

    Bearish Engulfing:
    - Previous candle: bullish (green/up)
    - Current candle: bearish (red/down)
    - Current body engulfs previous body
    - Indicates potential bearish reversal

    Features:
    - Two-bar pattern (minimum 2 bars required)
    - Sprint 17 confidence scoring support
    - Vectorized detection for efficiency
    - OHLC-consistent validation
    - Supports both bullish and bearish variants
    """

    def __init__(self, params: dict[str, Any] | None = None):
        """
        Initialize Engulfing pattern detector.

        Args:
            params: Dictionary containing:
                - min_body_ratio: Min current/previous body ratio (default: 1.0)
                - require_opposite_colors: Require opposite colors (default: True)
                - min_range: Min candle range (default: 0.001)
                - timeframe: Detection timeframe (default: 'daily')
        """
        super().__init__(params)
        self.enable_confidence_scoring()

    def _validate_and_parse_params(self, params: dict[str, Any]) -> EngulfingParams:
        """Validate and parse Engulfing parameters."""
        return EngulfingParams(**params)

    def detect(self, data: pd.DataFrame) -> pd.Series:
        """
        Detect Engulfing patterns in OHLCV data.

        Args:
            data: DataFrame with columns ['timestamp', 'open', 'high', 'low', 'close', 'volume']

        Returns:
            Boolean Series indexed by timestamp indicating Engulfing detection
            (detection marked at the current/engulfing candle)

        Raises:
            ValueError: If data format is invalid
            PatternDetectionError: If detection logic fails
        """
        try:
            self._validate_data_format(data)

            if len(data) < 2:
                # Need at least 2 bars for engulfing pattern
                return pd.Series(False, index=data.index)

            # Calculate body sizes
            body_size = self.calculate_body_size(data)

            # Calculate body top/bottom for each candle
            body_top = data[["open", "close"]].max(axis=1)
            body_bottom = data[["open", "close"]].min(axis=1)

            # Get previous bar values (shift forward by 1)
            prev_body_size = body_size.shift(1)
            prev_body_top = body_top.shift(1)
            prev_body_bottom = body_bottom.shift(1)

            # Check candle colors
            is_bullish = self.is_bullish_candle(data)
            is_bearish = self.is_bearish_candle(data)
            prev_is_bullish = is_bullish.shift(1)
            prev_is_bearish = is_bearish.shift(1)

            # Filter valid range
            candle_range = self.calculate_candle_range(data)
            valid_range = candle_range >= self.params.min_range

            # Engulfing criteria:
            # 1. Current body top > previous body top
            # 2. Current body bottom < previous body bottom
            # 3. Current body size >= min_body_ratio * previous body size
            # 4. If require_opposite_colors: colors must be opposite
            body_engulfs = (
                (body_top > prev_body_top)
                & (body_bottom < prev_body_bottom)
                & (body_size >= self.params.min_body_ratio * prev_body_size)
            )

            if self.params.require_opposite_colors:
                # Bullish engulfing: prev bearish, current bullish
                # Bearish engulfing: prev bullish, current bearish
                opposite_colors = (prev_is_bearish & is_bullish) | (prev_is_bullish & is_bearish)
                engulfing_detected = body_engulfs & opposite_colors & valid_range
            else:
                engulfing_detected = body_engulfs & valid_range

            # First bar cannot have an engulfing pattern (no previous bar)
            engulfing_detected.iloc[0] = False

            return engulfing_detected

        except Exception as e:
            raise PatternDetectionError(f"Engulfing detection failed: {e}") from e

    def get_minimum_bars(self) -> int:
        """Engulfing requires 2 bars."""
        return 2

    def calculate_confidence(
        self, data: pd.DataFrame, detection_indices: pd.Index
    ) -> dict[Any, float]:
        """
        Calculate confidence scores for Engulfing detections.

        Confidence based on:
        - Body size ratio (larger current/previous = higher confidence)
        - Complete engulfment (current range engulfs previous range = bonus)
        - Volume confirmation (higher current volume = bonus)

        Args:
            data: OHLCV DataFrame
            detection_indices: Indices where Engulfing was detected

        Returns:
            Dictionary mapping detection indices to confidence scores (0.6 to 1.0)
        """
        confidence_scores = {}

        body_size = self.calculate_body_size(data)

        for idx in detection_indices:
            # Get index position
            idx_pos = data.index.get_loc(idx)
            if idx_pos == 0:
                continue  # Skip first bar (no previous)

            prev_idx = data.index[idx_pos - 1]

            # Base confidence
            confidence = 0.6

            # Bonus for strong body size ratio
            if body_size.loc[prev_idx] > 0:
                body_ratio = body_size.loc[idx] / body_size.loc[prev_idx]
                if body_ratio >= 1.5:
                    confidence += 0.15

            # Bonus for complete range engulfment (not just body)
            if (
                data.loc[idx, "high"] > data.loc[prev_idx, "high"]
                and data.loc[idx, "low"] < data.loc[prev_idx, "low"]
            ):
                confidence += 0.10

            # Bonus for volume confirmation
            if "volume" in data.columns:
                if data.loc[idx, "volume"] > data.loc[prev_idx, "volume"]:
                    confidence += 0.10

            # Bonus for strong color contrast
            curr_bullish = data.loc[idx, "close"] > data.loc[idx, "open"]
            prev_bullish = data.loc[prev_idx, "close"] > data.loc[prev_idx, "open"]
            if curr_bullish != prev_bullish:
                confidence += 0.05

            confidence_scores[idx] = round(min(confidence, 1.0), 3)

        return confidence_scores

    def get_engulfing_type(self, data: pd.DataFrame, index: Any) -> str | None:
        """
        Determine Engulfing subtype (bullish or bearish) for a specific index.

        Args:
            data: OHLCV DataFrame
            index: Timestamp index to analyze

        Returns:
            'bullish' if bullish engulfing, 'bearish' if bearish engulfing, None if invalid
        """
        # Get index position
        idx_pos = data.index.get_loc(index)
        if idx_pos == 0:
            return None  # No previous bar

        prev_idx = data.index[idx_pos - 1]

        # Check current and previous candle colors
        curr_bullish = data.loc[index, "close"] > data.loc[index, "open"]
        prev_bearish = data.loc[prev_idx, "close"] < data.loc[prev_idx, "open"]

        if curr_bullish and prev_bearish:
            return "bullish"
        elif not curr_bullish and not prev_bearish:
            return "bearish"
        else:
            return None  # Mixed or neutral
