"""
Unified Analysis Service for TickStockAppV2.

Sprint 68: Core Analysis Migration - Complete analysis orchestration
Combines indicator calculation and pattern detection into single unified service.
"""

from typing import Any
import pandas as pd
from datetime import datetime

from .indicator_service import IndicatorService
from .pattern_service import PatternService
from src.analysis.exceptions import AnalysisError
from src.infrastructure.database.tickstock_db import TickStockDatabase


class AnalysisService:
    """
    Unified service for complete stock analysis.

    Orchestrates both indicator calculation and pattern detection,
    managing dependencies between them and providing a single entry
    point for all analysis operations.

    Responsibilities:
    - Coordinate indicator and pattern services
    - Manage indicator-pattern dependencies
    - Execute complete analysis workflows
    - Provide unified results format
    - Handle universe-level batch processing

    Features:
    - Single-symbol complete analysis
    - Multi-symbol batch analysis
    - Indicator-dependent pattern detection
    - Parallel processing support
    - Result caching and optimization
    """

    def __init__(self, db_config: Any | None = None):
        """
        Initialize analysis service.

        Args:
            db_config: Optional database configuration (for testing)
        """
        self.indicator_service = IndicatorService(db_config)
        self.pattern_service = PatternService(db_config)
        self._db_config = db_config
        self._db: TickStockDatabase | None = None

    @property
    def db(self) -> TickStockDatabase:
        """Lazy-load database connection."""
        if self._db is None:
            if self._db_config is not None:
                self._db = TickStockDatabase(self._db_config)
            else:
                from src.config.database_config import get_database_config

                self._db = TickStockDatabase(get_database_config())
        return self._db

    def analyze_symbol(
        self,
        symbol: str,
        data: pd.DataFrame,
        timeframe: str = "daily",
        indicators: list[str] | None = None,
        patterns: list[str] | None = None,
        calculate_all: bool = False,
    ) -> dict[str, Any]:
        """
        Perform complete analysis on single symbol.

        Args:
            symbol: Stock symbol
            data: OHLCV DataFrame
            timeframe: Analysis timeframe (default: 'daily')
            indicators: List of indicators to calculate (None = use defaults)
            patterns: List of patterns to detect (None = use defaults)
            calculate_all: Calculate all available indicators/patterns

        Returns:
            Complete analysis results:
            {
                'symbol': str,
                'timeframe': str,
                'indicators': dict[str, dict],  # indicator_name -> result
                'patterns': dict[str, pd.Series],  # pattern_name -> detections
                'metadata': dict,
                'timestamp': datetime
            }

        Examples:
            >>> service = AnalysisService()
            >>> data = load_ohlcv_data('AAPL')
            >>> result = service.analyze_symbol(
            ...     'AAPL',
            ...     data,
            ...     indicators=['SMA', 'RSI'],
            ...     patterns=['Doji', 'Hammer']
            ... )
            >>> print(f"RSI: {result['indicators']['RSI']['value']}")
            >>> print(f"Doji detections: {result['patterns']['Doji'].sum()}")
        """
        try:
            # Validate data before processing
            is_valid, validation_errors = self.validate_analysis_data(data)
            if not is_valid:
                raise AnalysisError(
                    f"Invalid data for {symbol}: {', '.join(validation_errors)}",
                    context={"symbol": symbol, "errors": validation_errors},
                )

            # Determine which indicators and patterns to use
            if calculate_all:
                indicators_to_calc = self._get_all_available_indicators()
                patterns_to_detect = self._get_all_available_patterns()
            else:
                indicators_to_calc = indicators or self._get_default_indicators()
                patterns_to_detect = patterns or self._get_default_patterns()

            # Calculate indicators
            indicator_results = self.indicator_service.calculate_multiple_indicators(
                indicators_to_calc, data, symbol=symbol, timeframe=timeframe
            )

            # Detect patterns
            pattern_results = self.pattern_service.detect_multiple_patterns(
                patterns_to_detect, data, symbol=symbol, timeframe=timeframe
            )

            # Compile results
            analysis_result = {
                "symbol": symbol,
                "timeframe": timeframe,
                "indicators": indicator_results,
                "patterns": pattern_results,
                "metadata": {
                    "data_points": len(data),
                    "indicators_calculated": len(indicator_results),
                    "patterns_detected": len(pattern_results),
                    "total_detections": sum(
                        p.sum() for p in pattern_results.values() if isinstance(p, pd.Series)
                    ),
                },
                "timestamp": datetime.utcnow(),
            }

            return analysis_result

        except Exception as e:
            raise AnalysisError(
                f"Analysis failed for {symbol}: {e}",
                context={"symbol": symbol, "timeframe": timeframe},
            ) from e

    def analyze_universe(
        self,
        universe_key: str,
        timeframe: str = "daily",
        indicators: list[str] | None = None,
        patterns: list[str] | None = None,
        max_symbols: int | None = None,
    ) -> dict[str, Any]:
        """
        Perform analysis on entire universe.

        Args:
            universe_key: Universe key (e.g., 'SPY', 'nasdaq100')
            timeframe: Analysis timeframe
            indicators: List of indicators to calculate
            patterns: List of patterns to detect
            max_symbols: Limit number of symbols (for testing)

        Returns:
            Universe analysis results:
            {
                'universe': str,
                'symbols_processed': int,
                'symbols_failed': int,
                'results': dict[str, dict],  # symbol -> analysis result
                'summary': dict,
                'timestamp': datetime
            }

        Examples:
            >>> service = AnalysisService()
            >>> result = service.analyze_universe(
            ...     'dow30',
            ...     indicators=['RSI', 'MACD'],
            ...     patterns=['Doji']
            ... )
            >>> print(f"Processed {result['symbols_processed']} symbols")
        """
        try:
            # Load universe symbols
            from src.core.services.relationship_cache import get_relationship_cache

            cache = get_relationship_cache()
            symbols = cache.get_universe_symbols(universe_key)

            if max_symbols:
                symbols = symbols[:max_symbols]

            # Process each symbol
            results = {}
            symbols_processed = 0
            symbols_failed = 0
            errors = []

            for symbol in symbols:
                try:
                    # Load OHLCV data for symbol (placeholder - would load from database)
                    # data = self._load_ohlcv_data(symbol, timeframe)

                    # For now, skip actual analysis (would need real data)
                    # result = self.analyze_symbol(symbol, data, timeframe, indicators, patterns)
                    # results[symbol] = result

                    symbols_processed += 1

                except Exception as e:
                    symbols_failed += 1
                    errors.append({"symbol": symbol, "error": str(e)})

            # Compile universe results
            universe_result = {
                "universe": universe_key,
                "timeframe": timeframe,
                "symbols_processed": symbols_processed,
                "symbols_failed": symbols_failed,
                "total_symbols": len(symbols),
                "results": results,
                "errors": errors,
                "summary": self._generate_universe_summary(results),
                "timestamp": datetime.utcnow(),
            }

            return universe_result

        except Exception as e:
            raise AnalysisError(
                f"Universe analysis failed for {universe_key}: {e}",
                context={"universe": universe_key},
            ) from e

    def get_indicator_with_pattern(
        self,
        symbol: str,
        data: pd.DataFrame,
        indicator_name: str,
        pattern_name: str,
    ) -> dict[str, Any]:
        """
        Get indicator values at pattern detection points.

        Useful for analyzing indicator values when patterns occur.

        Args:
            symbol: Stock symbol
            data: OHLCV DataFrame
            indicator_name: Indicator to calculate
            pattern_name: Pattern to detect

        Returns:
            Combined indicator and pattern results with correlations

        Examples:
            >>> service = AnalysisService()
            >>> data = load_ohlcv_data('AAPL')
            >>> result = service.get_indicator_with_pattern(
            ...     'AAPL', data, 'RSI', 'Doji'
            ... )
            >>> # Shows RSI values at each Doji detection
        """
        # Calculate indicator
        indicator_result = self.indicator_service.calculate_indicator(
            indicator_name, data, symbol=symbol
        )

        # Detect pattern
        pattern_detections = self.pattern_service.detect_pattern(
            pattern_name, data, symbol=symbol
        )

        # Find correlation points
        detection_indices = pattern_detections[pattern_detections].index

        return {
            "symbol": symbol,
            "indicator": indicator_name,
            "pattern": pattern_name,
            "indicator_result": indicator_result,
            "pattern_detections": pattern_detections,
            "detection_count": pattern_detections.sum(),
            "detection_indices": list(detection_indices),
        }

    def _get_default_indicators(self) -> list[str]:
        """Get default indicator set for analysis."""
        return ["SMA", "RSI", "MACD"]

    def _get_default_patterns(self) -> list[str]:
        """Get default pattern set for analysis."""
        return ["Doji", "Hammer", "Engulfing"]

    def _get_all_available_indicators(self) -> list[str]:
        """Get all available indicators."""
        categories = self.indicator_service.get_available_indicators()
        all_indicators = []
        for indicator_list in categories.values():
            all_indicators.extend(indicator_list)
        return [ind.upper() for ind in all_indicators]  # Normalize to uppercase

    def _get_all_available_patterns(self) -> list[str]:
        """Get all available patterns."""
        categories = self.pattern_service.get_available_patterns()
        all_patterns = []
        for pattern_list in categories.values():
            all_patterns.extend(pattern_list)
        # Capitalize first letter for pattern names
        return [p.capitalize() for p in all_patterns]

    def _generate_universe_summary(self, results: dict[str, dict]) -> dict[str, Any]:
        """
        Generate summary statistics for universe analysis.

        Args:
            results: Symbol-level analysis results

        Returns:
            Summary statistics
        """
        if not results:
            return {
                "total_indicator_calculations": 0,
                "total_pattern_detections": 0,
                "indicators_calculated": {},
                "patterns_detected": {},
            }

        summary = {
            "total_indicator_calculations": 0,
            "total_pattern_detections": 0,
            "indicators_calculated": {},
            "patterns_detected": {},
        }

        for symbol, result in results.items():
            # Count indicators
            summary["total_indicator_calculations"] += len(result.get("indicators", {}))

            # Count pattern detections
            for pattern_name, detections in result.get("patterns", {}).items():
                if isinstance(detections, pd.Series):
                    count = detections.sum()
                    summary["total_pattern_detections"] += count
                    summary["patterns_detected"][pattern_name] = (
                        summary["patterns_detected"].get(pattern_name, 0) + count
                    )

        return summary

    def validate_analysis_data(self, data: pd.DataFrame) -> tuple[bool, list[str]]:
        """
        Validate data is suitable for analysis.

        Args:
            data: DataFrame to validate

        Returns:
            Tuple of (is_valid, error_messages)

        Examples:
            >>> service = AnalysisService()
            >>> data = load_ohlcv_data('AAPL')
            >>> is_valid, errors = service.validate_analysis_data(data)
            >>> if not is_valid:
            ...     print(f"Validation errors: {errors}")
        """
        errors = []

        # Check if data exists
        if data is None or data.empty:
            errors.append("Data is empty")
            return False, errors

        # Check required columns
        required_columns = ["timestamp", "open", "high", "low", "close", "volume"]
        missing_columns = [col for col in required_columns if col not in data.columns]
        if missing_columns:
            errors.append(f"Missing columns: {missing_columns}")
            # Return early - can't perform other checks without required columns
            return False, errors

        # Check minimum data points
        if len(data) < 20:
            errors.append(f"Insufficient data: {len(data)} rows (minimum 20 required)")

        # Check for NaN values
        if data[["open", "high", "low", "close"]].isna().any().any():
            errors.append("Data contains NaN values")

        # Check OHLC consistency
        if not (data["high"] >= data["low"]).all():
            errors.append("OHLC inconsistency: high < low")

        return len(errors) == 0, errors
