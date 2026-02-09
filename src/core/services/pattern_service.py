"""
Pattern Service for TickStockAppV2.

Sprint 68: Core Analysis Migration - Pattern detection orchestration
"""

from typing import Any
import pandas as pd
from datetime import datetime

from src.analysis.patterns.loader import load_pattern, is_pattern_available
from src.analysis.patterns.base_pattern import BasePattern
from src.analysis.exceptions import PatternDetectionError, PatternLoadError
from src.infrastructure.database.tickstock_db import TickStockDatabase


class PatternService:
    """
    Service for orchestrating pattern detection operations.

    Responsibilities:
    - Load patterns dynamically (NO FALLBACK)
    - Execute pattern detection on OHLCV data
    - Store detection results to database
    - Manage pattern registry integration

    Features:
    - Single pattern detection
    - Batch pattern detection (multiple patterns, single symbol)
    - Universe-level detection (multiple symbols)
    - Sprint 17 registry integration (confidence filtering)
    """

    def __init__(self, db_config: Any | None = None):
        """
        Initialize pattern service.

        Args:
            db_config: Optional database configuration (for testing)
        """
        self._db_config = db_config
        self._db: TickStockDatabase | None = None
        self._pattern_cache: dict[str, type[BasePattern]] = {}

    @property
    def db(self) -> TickStockDatabase:
        """Lazy-load database connection."""
        if self._db is None:
            if self._db_config is not None:
                self._db = TickStockDatabase(self._db_config)
            else:
                # Use default config (will be loaded from environment)
                from src.config.database_config import get_database_config

                self._db = TickStockDatabase(get_database_config())
        return self._db

    def detect_pattern(
        self,
        pattern_name: str,
        data: pd.DataFrame,
        symbol: str | None = None,
        timeframe: str = "daily",
        params: dict[str, Any] | None = None,
    ) -> pd.Series:
        """
        Detect single pattern in OHLCV data.

        Args:
            pattern_name: Pattern name (e.g., 'Doji', 'Hammer')
            data: DataFrame with OHLCV columns
            symbol: Stock symbol (optional, for context)
            timeframe: Timeframe for detection (default: 'daily')
            params: Pattern-specific parameters (optional)

        Returns:
            Boolean Series indexed by timestamp indicating pattern detection

        Raises:
            PatternLoadError: If pattern cannot be loaded
            PatternDetectionError: If detection fails

        Examples:
            >>> service = PatternService()
            >>> data = load_ohlcv_data('AAPL')
            >>> detections = service.detect_pattern('Doji', data, symbol='AAPL')
            >>> print(f"Detected {detections.sum()} Doji patterns")
        """
        try:
            # Load pattern class
            pattern_class = self._get_pattern_class(pattern_name)

            # Create pattern instance with params
            pattern_params = params or {}
            if timeframe:
                pattern_params["timeframe"] = timeframe

            pattern = pattern_class(pattern_params)

            # Execute detection
            detections = pattern.detect(data)

            return detections

        except PatternLoadError:
            # Re-raise load errors
            raise

        except Exception as e:
            raise PatternDetectionError(
                f"Pattern detection failed for {pattern_name}",
                pattern_name=pattern_name,
                symbol=symbol,
                timeframe=timeframe,
            ) from e

    def detect_multiple_patterns(
        self,
        pattern_names: list[str],
        data: pd.DataFrame,
        symbol: str | None = None,
        timeframe: str = "daily",
    ) -> dict[str, pd.Series]:
        """
        Detect multiple patterns on same data.

        Args:
            pattern_names: List of pattern names to detect
            data: DataFrame with OHLCV columns
            symbol: Stock symbol (optional)
            timeframe: Timeframe for detection

        Returns:
            Dictionary mapping pattern name to detection Series

        Examples:
            >>> service = PatternService()
            >>> data = load_ohlcv_data('AAPL')
            >>> results = service.detect_multiple_patterns(
            ...     ['Doji', 'Hammer', 'Engulfing'],
            ...     data,
            ...     symbol='AAPL'
            ... )
            >>> for pattern, detections in results.items():
            ...     print(f"{pattern}: {detections.sum()} detections")
        """
        results = {}

        for pattern_name in pattern_names:
            try:
                detections = self.detect_pattern(
                    pattern_name, data, symbol=symbol, timeframe=timeframe
                )
                results[pattern_name] = detections
            except (PatternLoadError, PatternDetectionError) as e:
                # Log error but continue with other patterns
                print(f"Warning: Failed to detect {pattern_name}: {e}")
                results[pattern_name] = pd.Series(False, index=data.index)

        return results

    def detect_with_confidence_filter(
        self,
        pattern_name: str,
        data: pd.DataFrame,
        confidence_threshold: float,
        symbol: str | None = None,
        timeframe: str = "daily",
        params: dict[str, Any] | None = None,
    ) -> tuple[pd.Series, dict[Any, float]]:
        """
        Detect pattern with confidence threshold filtering (Sprint 17).

        Args:
            pattern_name: Pattern name
            data: DataFrame with OHLCV columns
            confidence_threshold: Minimum confidence score (0.0 to 1.0)
            symbol: Stock symbol (optional)
            timeframe: Timeframe for detection
            params: Pattern-specific parameters

        Returns:
            Tuple of (filtered_detections, confidence_scores)

        Examples:
            >>> service = PatternService()
            >>> data = load_ohlcv_data('AAPL')
            >>> detections, scores = service.detect_with_confidence_filter(
            ...     'Doji', data, confidence_threshold=0.8, symbol='AAPL'
            ... )
            >>> print(f"High-confidence detections: {detections.sum()}")
        """
        # Load pattern class
        pattern_class = self._get_pattern_class(pattern_name)

        # Create pattern instance
        pattern_params = params or {}
        if timeframe:
            pattern_params["timeframe"] = timeframe

        pattern = pattern_class(pattern_params)

        # Set confidence threshold (Sprint 17)
        pattern.set_pattern_registry_info(
            pattern_id=0,  # Placeholder - would come from database
            confidence_threshold=confidence_threshold,
        )

        # Execute detection
        raw_detections = pattern.detect(data)

        # Calculate confidence scores
        detection_indices = raw_detections[raw_detections].index
        confidence_scores = {}

        if len(detection_indices) > 0 and pattern.supports_confidence_scoring():
            confidence_scores = pattern.calculate_confidence(data, detection_indices)

            # Filter by threshold
            filtered_detections = raw_detections.copy()
            for idx in detection_indices:
                if confidence_scores.get(idx, 0.0) < confidence_threshold:
                    filtered_detections.loc[idx] = False
        else:
            filtered_detections = raw_detections
            # Default confidence for patterns without scoring
            confidence_scores = dict.fromkeys(detection_indices, 1.0)

        return filtered_detections, confidence_scores

    def store_detections(
        self,
        symbol: str,
        pattern_name: str,
        detections: pd.Series,
        confidence_scores: dict[Any, float] | None = None,
        timeframe: str = "daily",
    ) -> int:
        """
        Store pattern detections to database.

        Args:
            symbol: Stock symbol
            pattern_name: Pattern name
            detections: Detection results (boolean Series)
            confidence_scores: Optional confidence scores for each detection
            timeframe: Timeframe

        Returns:
            Number of detections stored

        Note:
            This method would need database schema for daily_patterns table.
            Implementation depends on Sprint 68 database schema decisions.
        """
        detection_indices = detections[detections].index
        stored_count = 0

        for timestamp in detection_indices:
            confidence = (
                confidence_scores.get(timestamp, 1.0) if confidence_scores else 1.0
            )

            # Placeholder for database storage
            # Would use self.db to insert into daily_patterns table
            # with self.db.get_connection() as conn:
            #     query = """
            #         INSERT INTO daily_patterns (
            #             symbol, pattern_name, detected_at, confidence, timeframe
            #         )
            #         VALUES (:symbol, :pattern_name, :detected_at, :confidence, :timeframe)
            #     """
            #     conn.execute(query, {
            #         'symbol': symbol,
            #         'pattern_name': pattern_name,
            #         'detected_at': timestamp,
            #         'confidence': confidence,
            #         'timeframe': timeframe
            #     })

            stored_count += 1

        return stored_count

    def _get_pattern_class(self, pattern_name: str) -> type[BasePattern]:
        """
        Get pattern class with caching.

        Args:
            pattern_name: Pattern name

        Returns:
            Pattern class

        Raises:
            PatternLoadError: If pattern cannot be loaded
        """
        # Check cache first
        if pattern_name not in self._pattern_cache:
            # Load and cache
            pattern_class = load_pattern(pattern_name)
            self._pattern_cache[pattern_name] = pattern_class

        return self._pattern_cache[pattern_name]

    def get_available_patterns(self) -> dict[str, list[str]]:
        """
        Get list of all available patterns.

        Returns:
            Dictionary mapping pattern type to list of pattern names
        """
        from src.analysis.patterns.loader import get_available_patterns

        return get_available_patterns()

    def is_pattern_available(self, pattern_name: str) -> bool:
        """
        Check if pattern is available.

        Args:
            pattern_name: Pattern name to check

        Returns:
            True if pattern is available, False otherwise
        """
        return is_pattern_available(pattern_name)
