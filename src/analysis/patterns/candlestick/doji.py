"""
Doji candlestick pattern detection.

Sprint 68: Core Analysis Migration from TickStockPL
Single-bar pattern with very small body indicating indecision.
"""

from typing import Any

import pandas as pd
from pydantic import Field, field_validator

from ..base_pattern import BasePattern, PatternParams
from ...exceptions import PatternDetectionError


class DojiParams(PatternParams):
    """Parameters for Doji pattern detection."""

    body_threshold: float = Field(default=0.1, description="Max body/range ratio for doji")
    min_range: float = Field(default=0.001, description="Min candle range to avoid zero-division")

    @field_validator("body_threshold")
    @classmethod
    def validate_body_threshold(cls, value):
        if not 0 < value < 1:
            raise ValueError(f"body_threshold must be between 0 and 1, got {value}")
        return value

    @field_validator("min_range")
    @classmethod
    def validate_min_range(cls, value):
        if value <= 0:
            raise ValueError(f"min_range must be positive, got {value}")
        return value


class Doji(BasePattern):
    """
    Doji candlestick pattern detector.

    A Doji forms when the open and close prices are virtually equal,
    creating a cross or plus sign shape. Indicates market indecision.

    Subtypes:
    - Standard: Equal upper and lower shadows
    - Gravestone: Long upper shadow, minimal lower shadow
    - Dragonfly: Long lower shadow, minimal upper shadow
    - Long-legged: Both shadows are long

    Features:
    - Single-bar pattern (minimum 1 bar required)
    - Sprint 17 confidence scoring support
    - Vectorized detection for efficiency
    - OHLC-consistent validation
    """

    def __init__(self, params: dict[str, Any] | None = None):
        """
        Initialize Doji pattern detector.

        Args:
            params: Dictionary containing:
                - body_threshold: Max body/range ratio (default: 0.1)
                - min_range: Min candle range (default: 0.001)
                - timeframe: Detection timeframe (default: 'daily')
        """
        super().__init__(params)
        self.enable_confidence_scoring()

    def _validate_and_parse_params(self, params: dict[str, Any]) -> DojiParams:
        """Validate and parse Doji parameters."""
        return DojiParams(**params)

    def detect(self, data: pd.DataFrame) -> pd.Series:
        """
        Detect Doji patterns in OHLCV data.

        Args:
            data: DataFrame with columns ['timestamp', 'open', 'high', 'low', 'close', 'volume']

        Returns:
            Boolean Series indexed by timestamp indicating Doji detection

        Raises:
            ValueError: If data format is invalid
            PatternDetectionError: If detection logic fails
        """
        try:
            self._validate_data_format(data)

            # Calculate body size and candle range
            body_size = self.calculate_body_size(data)
            candle_range = self.calculate_candle_range(data)

            # Filter out candles with insufficient range
            valid_range = candle_range >= self.params.min_range

            # Calculate body ratio (avoiding division by zero)
            body_ratio = pd.Series(0.0, index=data.index)
            body_ratio[valid_range] = body_size[valid_range] / candle_range[valid_range]

            # Detect Doji: body ratio below threshold
            doji_detected = (body_ratio < self.params.body_threshold) & valid_range

            return doji_detected

        except Exception as e:
            raise PatternDetectionError(f"Doji detection failed: {e}") from e

    def get_minimum_bars(self) -> int:
        """Doji requires only 1 bar."""
        return 1

    def calculate_confidence(
        self, data: pd.DataFrame, detection_indices: pd.Index
    ) -> dict[Any, float]:
        """
        Calculate confidence scores for Doji detections.

        Confidence based on:
        - Body ratio (smaller = higher confidence)
        - Shadow symmetry (more symmetric = higher confidence)

        Args:
            data: OHLCV DataFrame
            detection_indices: Indices where Doji was detected

        Returns:
            Dictionary mapping detection indices to confidence scores (0.6 to 1.0)
        """
        confidence_scores = {}

        body_size = self.calculate_body_size(data)
        candle_range = self.calculate_candle_range(data)

        for idx in detection_indices:
            # Base confidence from body ratio
            body_ratio = body_size.loc[idx] / candle_range.loc[idx]
            base_confidence = 1.0 - (body_ratio / self.params.body_threshold)

            # Calculate shadow symmetry bonus
            body_top = max(data.loc[idx, "open"], data.loc[idx, "close"])
            body_bottom = min(data.loc[idx, "open"], data.loc[idx, "close"])
            upper_shadow = data.loc[idx, "high"] - body_top
            lower_shadow = body_bottom - data.loc[idx, "low"]

            # Symmetric shadows increase confidence
            if candle_range.loc[idx] > 0:
                shadow_diff = abs(upper_shadow - lower_shadow)
                symmetry_ratio = shadow_diff / candle_range.loc[idx]
                symmetry_bonus = (1.0 - symmetry_ratio) * 0.15  # Up to +0.15
            else:
                symmetry_bonus = 0

            confidence = base_confidence + symmetry_bonus
            confidence_scores[idx] = round(min(confidence, 1.0), 3)

        return confidence_scores

    def get_doji_subtype(self, data: pd.DataFrame, index: Any) -> str:
        """
        Determine Doji subtype for a specific index.

        Args:
            data: OHLCV DataFrame
            index: Timestamp index to analyze

        Returns:
            Subtype: 'standard', 'gravestone', 'dragonfly', or 'long-legged'
        """
        body_top = max(data.loc[index, "open"], data.loc[index, "close"])
        body_bottom = min(data.loc[index, "open"], data.loc[index, "close"])
        upper_shadow = data.loc[index, "high"] - body_top
        lower_shadow = body_bottom - data.loc[index, "low"]
        candle_range = data.loc[index, "high"] - data.loc[index, "low"]

        if candle_range == 0:
            return "standard"

        # Determine subtype based on shadow proportions
        if abs(upper_shadow - lower_shadow) < candle_range * 0.1:
            return "standard"
        elif upper_shadow > lower_shadow * 2:
            return "gravestone"
        elif lower_shadow > upper_shadow * 2:
            return "dragonfly"
        else:
            return "long-legged"
