"""
Hammer candlestick pattern detection.

Sprint 68: Core Analysis Migration from TickStockPL
Single-bar pattern with small body at top and long lower shadow (bullish reversal).
"""

from typing import Any

import pandas as pd
from pydantic import Field, field_validator

from ..base_pattern import BasePattern, PatternParams
from ...exceptions import PatternDetectionError


class HammerParams(PatternParams):
    """Parameters for Hammer pattern detection."""

    min_shadow_ratio: float = Field(default=2.0, description="Lower shadow must be >= this ratio of body")
    max_upper_shadow_ratio: float = Field(default=0.1, description="Upper shadow max ratio of range")
    min_lower_shadow_ratio: float = Field(default=0.6, description="Lower shadow min ratio of range")
    max_body_ratio: float = Field(default=0.3, description="Body max ratio of range")
    min_range: float = Field(default=0.001, description="Min candle range")

    @field_validator("min_shadow_ratio")
    @classmethod
    def validate_min_shadow_ratio(cls, value):
        if value <= 0:
            raise ValueError(f"min_shadow_ratio must be positive, got {value}")
        return value

    @field_validator("max_upper_shadow_ratio", "min_lower_shadow_ratio", "max_body_ratio")
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


class Hammer(BasePattern):
    """
    Hammer candlestick pattern detector.

    A Hammer forms at the end of a downtrend with a small body near the top
    and a long lower shadow (at least 2x the body size). Indicates potential
    bullish reversal as buyers pushed price back up from lows.

    Characteristics:
    - Small body (any color, but white/green is more bullish)
    - Long lower shadow (≥2x body)
    - Little to no upper shadow
    - Lower shadow ≥60% of total range

    Features:
    - Single-bar pattern (minimum 1 bar required)
    - Sprint 17 confidence scoring support
    - Vectorized detection for efficiency
    - OHLC-consistent validation
    """

    def __init__(self, params: dict[str, Any] | None = None):
        """
        Initialize Hammer pattern detector.

        Args:
            params: Dictionary containing:
                - min_shadow_ratio: Min lower shadow/body ratio (default: 2.0)
                - max_upper_shadow_ratio: Max upper shadow ratio (default: 0.1)
                - min_lower_shadow_ratio: Min lower shadow ratio (default: 0.6)
                - max_body_ratio: Max body ratio (default: 0.3)
                - min_range: Min candle range (default: 0.001)
                - timeframe: Detection timeframe (default: 'daily')
        """
        super().__init__(params)
        self.enable_confidence_scoring()

    def _validate_and_parse_params(self, params: dict[str, Any]) -> HammerParams:
        """Validate and parse Hammer parameters."""
        return HammerParams(**params)

    def detect(self, data: pd.DataFrame) -> pd.Series:
        """
        Detect Hammer patterns in OHLCV data.

        Args:
            data: DataFrame with columns ['timestamp', 'open', 'high', 'low', 'close', 'volume']

        Returns:
            Boolean Series indexed by timestamp indicating Hammer detection

        Raises:
            ValueError: If data format is invalid
            PatternDetectionError: If detection logic fails
        """
        try:
            self._validate_data_format(data)

            # Calculate metrics
            body_size = self.calculate_body_size(data)
            candle_range = self.calculate_candle_range(data)

            # Calculate body positions
            body_top = data[["open", "close"]].max(axis=1)
            body_bottom = data[["open", "close"]].min(axis=1)

            # Calculate shadows
            upper_shadow = data["high"] - body_top
            lower_shadow = body_bottom - data["low"]

            # Filter valid range
            valid_range = candle_range >= self.params.min_range

            # Calculate ratios (avoiding division by zero)
            body_ratio = pd.Series(0.0, index=data.index)
            upper_shadow_ratio = pd.Series(0.0, index=data.index)
            lower_shadow_ratio = pd.Series(0.0, index=data.index)

            body_ratio[valid_range] = body_size[valid_range] / candle_range[valid_range]
            upper_shadow_ratio[valid_range] = upper_shadow[valid_range] / candle_range[valid_range]
            lower_shadow_ratio[valid_range] = lower_shadow[valid_range] / candle_range[valid_range]

            # Detect Hammer criteria:
            # 1. Lower shadow >= min_shadow_ratio * body
            # 2. Upper shadow < max_upper_shadow_ratio * range
            # 3. Lower shadow > min_lower_shadow_ratio * range
            # 4. Body < max_body_ratio * range
            hammer_detected = (
                valid_range
                & (lower_shadow >= self.params.min_shadow_ratio * body_size)
                & (upper_shadow_ratio < self.params.max_upper_shadow_ratio)
                & (lower_shadow_ratio > self.params.min_lower_shadow_ratio)
                & (body_ratio < self.params.max_body_ratio)
            )

            return hammer_detected

        except Exception as e:
            raise PatternDetectionError(f"Hammer detection failed: {e}") from e

    def get_minimum_bars(self) -> int:
        """Hammer requires only 1 bar."""
        return 1

    def calculate_confidence(
        self, data: pd.DataFrame, detection_indices: pd.Index
    ) -> dict[Any, float]:
        """
        Calculate confidence scores for Hammer detections.

        Confidence based on:
        - Shadow/body ratio (higher = more confidence)
        - Upper shadow size (smaller = more confidence)
        - Body position (higher = more confidence)

        Args:
            data: OHLCV DataFrame
            detection_indices: Indices where Hammer was detected

        Returns:
            Dictionary mapping detection indices to confidence scores (0.6 to 1.0)
        """
        confidence_scores = {}

        body_size = self.calculate_body_size(data)
        candle_range = self.calculate_candle_range(data)

        for idx in detection_indices:
            # Base confidence
            confidence = 0.6

            # Calculate shadows
            body_top = max(data.loc[idx, "open"], data.loc[idx, "close"])
            body_bottom = min(data.loc[idx, "open"], data.loc[idx, "close"])
            lower_shadow = body_bottom - data.loc[idx, "low"]

            # Bonus for strong shadow/body ratio
            if body_size.loc[idx] > 0:
                shadow_body_ratio = lower_shadow / body_size.loc[idx]
                if shadow_body_ratio >= 3.0:
                    confidence += 0.15

            # Bonus for minimal upper shadow
            upper_shadow = data.loc[idx, "high"] - body_top
            if candle_range.loc[idx] > 0:
                upper_ratio = upper_shadow / candle_range.loc[idx]
                if upper_ratio < 0.05:
                    confidence += 0.10

            # Bonus for bullish color (close > open)
            if data.loc[idx, "close"] > data.loc[idx, "open"]:
                confidence += 0.10

            confidence_scores[idx] = round(min(confidence, 1.0), 3)

        return confidence_scores
