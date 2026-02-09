"""
Hanging Man candlestick pattern detection.

Sprint 69: Pattern Library Extension
Single-bar pattern with same structure as Hammer but appears at uptrend top (bearish reversal).
"""

from typing import Any

import pandas as pd
from pydantic import Field, field_validator

from ..base_pattern import BasePattern, PatternParams
from ...exceptions import PatternDetectionError


class HangingManParams(PatternParams):
    """Parameters for Hanging Man pattern detection."""

    min_shadow_ratio: float = Field(default=2.0, description="Lower shadow must be >= this ratio of body")
    max_upper_shadow_ratio: float = Field(default=0.1, description="Upper shadow max ratio of range")
    min_lower_shadow_ratio: float = Field(default=0.6, description="Lower shadow min ratio of range")
    max_body_ratio: float = Field(default=0.3, description="Body max ratio of range")
    min_range: float = Field(default=0.001, description="Min candle range")
    trend_lookback: int = Field(default=3, description="Bars to look back for uptrend confirmation")

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

    @field_validator("trend_lookback")
    @classmethod
    def validate_trend_lookback(cls, value):
        if value < 1:
            raise ValueError(f"trend_lookback must be >= 1, got {value}")
        return value


class HangingMan(BasePattern):
    """
    Hanging Man candlestick pattern detector.

    A Hanging Man has the same structure as a Hammer (small body at top, long lower shadow)
    but appears at the end of an uptrend, indicating potential bearish reversal.
    The key difference is context: Hammer = bullish (at downtrend bottom),
    Hanging Man = bearish (at uptrend top).

    Characteristics:
    - Small body (any color, but black/red is more bearish)
    - Long lower shadow (≥2x body)
    - Little to no upper shadow
    - Lower shadow ≥60% of total range
    - Appears after uptrend (confirmed by lookback)

    Features:
    - Single-bar pattern (minimum 1 bar + trend lookback)
    - Sprint 17 confidence scoring support
    - Vectorized detection for efficiency
    - OHLC-consistent validation
    - Trend context validation
    """

    def __init__(self, params: dict[str, Any] | None = None):
        """
        Initialize Hanging Man pattern detector.

        Args:
            params: Dictionary containing:
                - min_shadow_ratio: Min lower shadow/body ratio (default: 2.0)
                - max_upper_shadow_ratio: Max upper shadow ratio (default: 0.1)
                - min_lower_shadow_ratio: Min lower shadow ratio (default: 0.6)
                - max_body_ratio: Max body ratio (default: 0.3)
                - min_range: Min candle range (default: 0.001)
                - trend_lookback: Bars to confirm uptrend (default: 3)
                - timeframe: Detection timeframe (default: 'daily')
        """
        super().__init__(params)
        self.enable_confidence_scoring()

    def _validate_and_parse_params(self, params: dict[str, Any]) -> HangingManParams:
        """Validate and parse Hanging Man parameters."""
        return HangingManParams(**params)

    def detect(self, data: pd.DataFrame) -> pd.Series:
        """
        Detect Hanging Man patterns in OHLCV data.

        Args:
            data: DataFrame with columns ['timestamp', 'open', 'high', 'low', 'close', 'volume']

        Returns:
            Boolean Series indexed by timestamp indicating Hanging Man detection

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

            # Detect Hanging Man structure (same as Hammer):
            # 1. Lower shadow >= min_shadow_ratio * body
            # 2. Upper shadow < max_upper_shadow_ratio * range
            # 3. Lower shadow > min_lower_shadow_ratio * range
            # 4. Body < max_body_ratio * range
            structure_match = (
                valid_range
                & (lower_shadow >= self.params.min_shadow_ratio * body_size)
                & (upper_shadow_ratio < self.params.max_upper_shadow_ratio)
                & (lower_shadow_ratio > self.params.min_lower_shadow_ratio)
                & (body_ratio < self.params.max_body_ratio)
            )

            # Check for uptrend context
            uptrend_context = pd.Series(False, index=data.index)
            for i in range(self.params.trend_lookback, len(data)):
                # Simple uptrend check: current close higher than average of previous closes
                lookback_closes = data["close"].iloc[i - self.params.trend_lookback : i]
                if data["close"].iloc[i] > lookback_closes.mean():
                    uptrend_context.iloc[i] = True

            # Hanging Man = structure match + uptrend context
            hanging_man_detected = structure_match & uptrend_context

            return hanging_man_detected

        except Exception as e:
            raise PatternDetectionError(f"Hanging Man detection failed: {e}") from e

    def get_minimum_bars(self) -> int:
        """Hanging Man requires 1 bar + trend lookback."""
        return 1 + self.params.trend_lookback

    def calculate_confidence(
        self, data: pd.DataFrame, detection_indices: pd.Index
    ) -> dict[Any, float]:
        """
        Calculate confidence scores for Hanging Man detections.

        Confidence based on:
        - Shadow/body ratio (higher = more confidence)
        - Upper shadow size (smaller = more confidence)
        - Body position (higher = more confidence)
        - Uptrend strength (stronger = more confidence)

        Args:
            data: OHLCV DataFrame
            detection_indices: Indices where Hanging Man was detected

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

            # Bonus for bearish color (close < open)
            if data.loc[idx, "close"] < data.loc[idx, "open"]:
                confidence += 0.10

            # Bonus for strong uptrend before
            idx_pos = data.index.get_loc(idx)
            if idx_pos >= self.params.trend_lookback:
                lookback_closes = data["close"].iloc[
                    idx_pos - self.params.trend_lookback : idx_pos
                ]
                trend_strength = (data.loc[idx, "close"] - lookback_closes.min()) / (
                    lookback_closes.max() - lookback_closes.min() + 0.0001
                )
                if trend_strength > 0.8:
                    confidence += 0.05

            confidence_scores[idx] = round(min(confidence, 1.0), 3)

        return confidence_scores
