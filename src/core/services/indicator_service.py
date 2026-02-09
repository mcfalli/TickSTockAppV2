"""
Indicator Service for TickStockAppV2.

Sprint 68: Core Analysis Migration - Indicator calculation orchestration
"""

from typing import Any
import pandas as pd
from datetime import datetime

from src.analysis.indicators.loader import load_indicator, is_indicator_available
from src.analysis.indicators.base_indicator import BaseIndicator
from src.analysis.exceptions import IndicatorError, IndicatorLoadError
from src.infrastructure.database.tickstock_db import TickStockDatabase


class IndicatorService:
    """
    Service for orchestrating indicator calculation operations.

    Responsibilities:
    - Load indicators dynamically (NO FALLBACK)
    - Execute indicator calculations on OHLCV data
    - Store calculation results to database
    - Manage indicator dependencies

    Features:
    - Single indicator calculation
    - Batch indicator calculation (multiple indicators, single symbol)
    - Universe-level calculation (multiple symbols)
    - Result caching for efficiency
    """

    def __init__(self, db_config: Any | None = None):
        """
        Initialize indicator service.

        Args:
            db_config: Optional database configuration (for testing)
        """
        self._db_config = db_config
        self._db: TickStockDatabase | None = None
        self._indicator_cache: dict[str, type[BaseIndicator]] = {}

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

    def calculate_indicator(
        self,
        indicator_name: str,
        data: pd.DataFrame,
        symbol: str | None = None,
        timeframe: str = "daily",
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Calculate single indicator on OHLCV data.

        Args:
            indicator_name: Indicator name (e.g., 'SMA', 'RSI', 'MACD')
            data: DataFrame with OHLCV columns
            symbol: Stock symbol (optional, for context)
            timeframe: Timeframe for calculation (default: 'daily')
            params: Indicator-specific parameters (optional)

        Returns:
            Dictionary with indicator results in TickStockPL convention:
            {
                'indicator_type': str,
                'value': float,           # Primary value (most recent)
                'value_data': dict,       # Full result data
                'metadata': dict          # Additional metadata
            }

        Raises:
            IndicatorLoadError: If indicator cannot be loaded
            IndicatorError: If calculation fails

        Examples:
            >>> service = IndicatorService()
            >>> data = load_ohlcv_data('AAPL')
            >>> result = service.calculate_indicator('RSI', data, symbol='AAPL')
            >>> print(f"RSI: {result['value']}")
        """
        try:
            # Load indicator class
            indicator_class = self._get_indicator_class(indicator_name)

            # Create indicator instance with params
            indicator_params = params or {}
            indicator = indicator_class(indicator_params)

            # Execute calculation
            result = indicator.calculate(data, symbol=symbol, timeframe=timeframe)

            # Validate result format (TickStockPL convention)
            if not isinstance(result, dict):
                raise IndicatorError(
                    f"Indicator {indicator_name} returned invalid type: {type(result)}",
                    indicator_name=indicator_name,
                    symbol=symbol,
                )

            if "value" not in result or "value_data" not in result:
                raise IndicatorError(
                    f"Indicator {indicator_name} missing required keys: 'value' or 'value_data'",
                    indicator_name=indicator_name,
                    symbol=symbol,
                )

            return result

        except IndicatorLoadError:
            # Re-raise load errors
            raise

        except Exception as e:
            raise IndicatorError(
                f"Indicator calculation failed for {indicator_name}",
                indicator_name=indicator_name,
                symbol=symbol,
                timeframe=timeframe,
            ) from e

    def calculate_multiple_indicators(
        self,
        indicator_names: list[str],
        data: pd.DataFrame,
        symbol: str | None = None,
        timeframe: str = "daily",
    ) -> dict[str, dict[str, Any]]:
        """
        Calculate multiple indicators on same data.

        Args:
            indicator_names: List of indicator names to calculate
            data: DataFrame with OHLCV columns
            symbol: Stock symbol (optional)
            timeframe: Timeframe for calculation

        Returns:
            Dictionary mapping indicator name to result dictionary

        Examples:
            >>> service = IndicatorService()
            >>> data = load_ohlcv_data('AAPL')
            >>> results = service.calculate_multiple_indicators(
            ...     ['SMA', 'RSI', 'MACD'],
            ...     data,
            ...     symbol='AAPL'
            ... )
            >>> for indicator, result in results.items():
            ...     print(f"{indicator}: {result['value']}")
        """
        results = {}

        for indicator_name in indicator_names:
            try:
                result = self.calculate_indicator(
                    indicator_name, data, symbol=symbol, timeframe=timeframe
                )
                results[indicator_name] = result
            except (IndicatorLoadError, IndicatorError) as e:
                # Log error but continue with other indicators
                print(f"Warning: Failed to calculate {indicator_name}: {e}")
                results[indicator_name] = {
                    "indicator_type": indicator_name.lower(),
                    "value": None,
                    "value_data": {},
                    "error": str(e),
                }

        return results

    def get_indicator_value(
        self,
        indicator_name: str,
        data: pd.DataFrame,
        symbol: str | None = None,
        params: dict[str, Any] | None = None,
    ) -> float | None:
        """
        Get single value from indicator (convenience method).

        Args:
            indicator_name: Indicator name
            data: DataFrame with OHLCV columns
            symbol: Stock symbol (optional)
            params: Indicator-specific parameters

        Returns:
            Primary indicator value or None if calculation fails

        Examples:
            >>> service = IndicatorService()
            >>> data = load_ohlcv_data('AAPL')
            >>> rsi = service.get_indicator_value('RSI', data)
            >>> print(f"Current RSI: {rsi}")
        """
        try:
            result = self.calculate_indicator(indicator_name, data, symbol, params=params)
            return result.get("value")
        except (IndicatorLoadError, IndicatorError):
            return None

    def store_results(
        self,
        symbol: str,
        indicator_name: str,
        result: dict[str, Any],
        timeframe: str = "daily",
    ) -> bool:
        """
        Store indicator results to database.

        Args:
            symbol: Stock symbol
            indicator_name: Indicator name
            result: Calculation result dictionary
            timeframe: Timeframe

        Returns:
            True if stored successfully, False otherwise

        Note:
            This method would need database schema for indicator_results table.
            Implementation depends on Sprint 68 database schema decisions.
        """
        try:
            # Placeholder for database storage
            # Would use self.db to insert into indicator_results table
            # with self.db.get_connection() as conn:
            #     query = """
            #         INSERT INTO indicator_results (
            #             symbol, indicator_name, value, value_data,
            #             calculated_at, timeframe
            #         )
            #         VALUES (
            #             :symbol, :indicator_name, :value, :value_data,
            #             :calculated_at, :timeframe
            #         )
            #     """
            #     conn.execute(query, {
            #         'symbol': symbol,
            #         'indicator_name': indicator_name,
            #         'value': result['value'],
            #         'value_data': json.dumps(result['value_data']),
            #         'calculated_at': datetime.utcnow(),
            #         'timeframe': timeframe
            #     })

            return True

        except Exception as e:
            print(f"Error storing indicator result: {e}")
            return False

    def _get_indicator_class(self, indicator_name: str) -> type[BaseIndicator]:
        """
        Get indicator class with caching.

        Args:
            indicator_name: Indicator name

        Returns:
            Indicator class

        Raises:
            IndicatorLoadError: If indicator cannot be loaded
        """
        # Check cache first
        if indicator_name not in self._indicator_cache:
            # Load and cache
            indicator_class = load_indicator(indicator_name)
            self._indicator_cache[indicator_name] = indicator_class

        return self._indicator_cache[indicator_name]

    def get_available_indicators(self) -> dict[str, list[str]]:
        """
        Get list of all available indicators.

        Returns:
            Dictionary mapping indicator category to list of indicator names
        """
        from src.analysis.indicators.loader import get_available_indicators

        return get_available_indicators()

    def is_indicator_available(self, indicator_name: str) -> bool:
        """
        Check if indicator is available.

        Args:
            indicator_name: Indicator name to check

        Returns:
            True if indicator is available, False otherwise
        """
        return is_indicator_available(indicator_name)

    def validate_data(
        self, data: pd.DataFrame, required_columns: list[str] | None = None
    ) -> bool:
        """
        Validate OHLCV data format.

        Args:
            data: DataFrame to validate
            required_columns: Optional list of required columns

        Returns:
            True if data is valid, False otherwise
        """
        if data is None or data.empty:
            return False

        default_required = ["open", "high", "low", "close", "volume"]
        columns_to_check = required_columns or default_required

        return all(col in data.columns for col in columns_to_check)
