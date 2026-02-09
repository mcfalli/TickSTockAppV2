"""
Analysis Service for orchestrating pattern detection and indicator calculation.

Sprint 71: REST API Endpoints
Coordinates between PatternDetectionService, IndicatorLoader, and data validation.
"""

from datetime import datetime
from typing import Any

import pandas as pd

from src.analysis.exceptions import (
    AnalysisError,
    DataValidationError,
    InvalidIndicatorError,
    InvalidPatternError,
)
from src.analysis.indicators.loader import IndicatorLoader
from src.analysis.patterns.pattern_detection_service import PatternDetectionService


class AnalysisService:
    """
    Service for coordinating technical analysis operations.

    Orchestrates:
    - Pattern detection via PatternDetectionService
    - Indicator calculation via IndicatorLoader
    - Data validation for OHLCV format
    - Result aggregation and formatting
    """

    def __init__(self):
        """Initialize analysis service with loaders."""
        self.pattern_service = PatternDetectionService()
        self.indicator_loader = IndicatorLoader()

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
        Perform comprehensive analysis on a single symbol.

        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            data: OHLCV DataFrame with columns [open, high, low, close, volume]
            timeframe: Timeframe for analysis (daily, weekly, hourly, etc.)
            indicators: List of indicator names to calculate (None = none)
            patterns: List of pattern names to detect (None = none)
            calculate_all: If True, calculate all available indicators/patterns

        Returns:
            Dictionary with analysis results:
            {
                'indicators': {
                    'sma': {'value': 150.5, 'value_data': {...}},
                    'rsi': {'value': 65.3, 'value_data': {...}}
                },
                'patterns': {
                    'doji': {'detected': True, 'confidence': 0.85},
                    'hammer': {'detected': False, 'confidence': 0.0}
                }
            }

        Raises:
            DataValidationError: If data format is invalid
            InvalidIndicatorError: If requested indicator doesn't exist
            InvalidPatternError: If requested pattern doesn't exist
            AnalysisError: For other analysis failures
        """
        # Validate data format
        self._validate_ohlcv_data(data)

        result = {
            'indicators': {},
            'patterns': {},
        }

        # Calculate indicators
        if calculate_all:
            # Get all available indicators
            all_indicators = self.indicator_loader.get_available_indicators()
            indicators = list(all_indicators.keys())

        if indicators:
            result['indicators'] = self._calculate_indicators(
                data, indicators, timeframe
            )

        # Detect patterns
        if calculate_all:
            # Get all available patterns
            all_patterns = self.pattern_service.get_available_patterns()
            patterns = list(all_patterns.keys())

        if patterns:
            result['patterns'] = self._detect_patterns(
                data, patterns, timeframe
            )

        return result

    def validate_data(
        self,
        data_str: str,
        data_format: str = "csv",
    ) -> dict[str, Any]:
        """
        Validate OHLCV data format and return validation results.

        Args:
            data_str: Raw data string (CSV, JSON, etc.)
            data_format: Format of the data ('csv' or 'json')

        Returns:
            Dictionary with validation results:
            {
                'is_valid': bool,
                'errors': list[str],
                'warnings': list[str],
                'data_points': int,
                'columns_found': list[str],
                'date_range': {'start': str, 'end': str} or None
            }

        Raises:
            DataValidationError: If data format is unrecognized
        """
        errors = []
        warnings = []
        columns_found = []
        data_points = 0
        date_range = None

        try:
            # Parse data based on format
            if data_format.lower() == "csv":
                import io
                df = pd.read_csv(io.StringIO(data_str))
            elif data_format.lower() == "json":
                df = pd.read_json(data_str)
            else:
                raise DataValidationError(
                    f"Unsupported data format: {data_format}. "
                    "Supported formats: csv, json"
                )

            data_points = len(df)
            columns_found = df.columns.tolist()

            # Check for required OHLCV columns
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            missing_columns = [
                col for col in required_columns
                if col not in df.columns
            ]

            if missing_columns:
                errors.append(
                    f"Missing required columns: {', '.join(missing_columns)}"
                )

            # Check for timestamp/date column
            timestamp_cols = ['timestamp', 'date', 'datetime', 'time']
            has_timestamp = any(col in df.columns for col in timestamp_cols)

            if not has_timestamp:
                warnings.append(
                    "No timestamp column found. "
                    f"Expected one of: {', '.join(timestamp_cols)}"
                )

            # Validate OHLC relationships if columns present
            if not missing_columns:
                try:
                    self._validate_ohlcv_data(df)
                except DataValidationError as e:
                    errors.append(str(e))

            # Extract date range if timestamp available
            if has_timestamp and data_points > 0:
                for ts_col in timestamp_cols:
                    if ts_col in df.columns:
                        try:
                            df[ts_col] = pd.to_datetime(df[ts_col])
                            date_range = {
                                'start': df[ts_col].min().isoformat(),
                                'end': df[ts_col].max().isoformat(),
                            }
                            break
                        except Exception:
                            warnings.append(
                                f"Could not parse {ts_col} as datetime"
                            )

            # Check for minimum data points
            if data_points < 2:
                warnings.append(
                    "Less than 2 data points. "
                    "Most indicators require at least 20-50 bars."
                )
            elif data_points < 20:
                warnings.append(
                    "Less than 20 data points. "
                    "Some indicators may not calculate correctly."
                )

        except Exception as e:
            errors.append(f"Failed to parse data: {str(e)}")

        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'data_points': data_points,
            'columns_found': columns_found,
            'date_range': date_range,
        }

    def _calculate_indicators(
        self,
        data: pd.DataFrame,
        indicators: list[str],
        timeframe: str,
    ) -> dict[str, dict[str, Any]]:
        """
        Calculate requested indicators.

        Args:
            data: OHLCV DataFrame
            indicators: List of indicator names
            timeframe: Timeframe string

        Returns:
            Dictionary mapping indicator names to results

        Raises:
            InvalidIndicatorError: If indicator doesn't exist
        """
        results = {}

        for indicator_name in indicators:
            try:
                # Get indicator instance
                indicator = self.indicator_loader.get_indicator(indicator_name)

                # Calculate indicator (pass full DataFrame)
                result = indicator.calculate(data)

                # Store result
                results[indicator_name] = result

            except KeyError:
                raise InvalidIndicatorError(
                    f"Indicator '{indicator_name}' not found. "
                    f"Available indicators: "
                    f"{', '.join(self.indicator_loader.get_available_indicators().keys())}"
                )
            except Exception as e:
                raise AnalysisError(
                    f"Failed to calculate indicator '{indicator_name}': {str(e)}"
                )

        return results

    def _detect_patterns(
        self,
        data: pd.DataFrame,
        patterns: list[str],
        timeframe: str,
    ) -> dict[str, dict[str, Any]]:
        """
        Detect requested patterns.

        Args:
            data: OHLCV DataFrame
            patterns: List of pattern names
            timeframe: Timeframe string

        Returns:
            Dictionary mapping pattern names to detection results

        Raises:
            InvalidPatternError: If pattern doesn't exist
        """
        results = {}

        for pattern_name in patterns:
            try:
                # Detect pattern
                detection = self.pattern_service.detect_pattern(
                    pattern_name=pattern_name,
                    data=data,
                    timeframe=timeframe,
                )

                # Convert to dict format
                results[pattern_name] = {
                    'detected': bool(detection['detected'].iloc[-1] if len(detection['detected']) > 0 else False),
                    'confidence': float(detection['confidence'].iloc[-1] if len(detection['confidence']) > 0 else 0.0),
                }

            except KeyError:
                raise InvalidPatternError(
                    f"Pattern '{pattern_name}' not found. "
                    f"Available patterns: "
                    f"{', '.join(self.pattern_service.get_available_patterns().keys())}"
                )
            except Exception as e:
                raise AnalysisError(
                    f"Failed to detect pattern '{pattern_name}': {str(e)}"
                )

        return results

    def _validate_ohlcv_data(self, data: pd.DataFrame) -> None:
        """
        Validate OHLCV data format and relationships.

        Args:
            data: DataFrame to validate

        Raises:
            DataValidationError: If data is invalid
        """
        # Check for required columns
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        missing = [col for col in required_columns if col not in data.columns]

        if missing:
            raise DataValidationError(
                f"Missing required columns: {', '.join(missing)}"
            )

        # Check for minimum rows
        if len(data) == 0:
            raise DataValidationError("Data contains no rows")

        # Validate OHLC relationships: high >= low, high >= open/close, low <= open/close
        if len(data) > 0:
            invalid_high_low = (data['high'] < data['low']).any()
            if invalid_high_low:
                raise DataValidationError(
                    "Invalid OHLC: high must be >= low for all bars"
                )

            invalid_high = (
                (data['high'] < data['open']) |
                (data['high'] < data['close'])
            ).any()
            if invalid_high:
                raise DataValidationError(
                    "Invalid OHLC: high must be >= open and close for all bars"
                )

            invalid_low = (
                (data['low'] > data['open']) |
                (data['low'] > data['close'])
            ).any()
            if invalid_low:
                raise DataValidationError(
                    "Invalid OHLC: low must be <= open and close for all bars"
                )

        # Check for negative values
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_cols:
            if (data[col] < 0).any():
                raise DataValidationError(
                    f"Invalid data: {col} contains negative values"
                )
