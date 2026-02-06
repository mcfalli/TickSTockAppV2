"""Threshold Bar Service for market sentiment visualization.

Implements Diverging Threshold Bar and Simple Diverging Bar calculations
for advance-decline sentiment analysis across stocks, ETFs, and universes.

Sprint 64: Threshold Bars Implementation
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Literal

import numpy as np
import pandas as pd

from src.core.services.relationship_cache import get_relationship_cache
from src.infrastructure.database.tickstock_db import TickStockDatabase

logger = logging.getLogger(__name__)

BarType = Literal["DivergingThresholdBar", "SimpleDivergingBar"]
Timeframe = Literal["1min", "hourly", "daily", "weekly", "monthly"]


class ThresholdBarService:
    """Service for calculating threshold bars from OHLCV data.

    Supports two bar types:
    - DivergingThresholdBar: 4 segments (significant_decline, minor_decline,
      minor_advance, significant_advance)
    - SimpleDivergingBar: 2 segments (decline, advance)

    Performance targets:
    - Single bar calculation: <50ms
    - Multi-bar batch (20 bars): <1000ms
    - Database query: <30ms for 500 symbols
    """

    def __init__(self, relationship_cache=None, db=None, config=None):
        """Initialize the threshold bar service.

        Args:
            relationship_cache: Optional RelationshipCache instance (for testing)
            db: Optional TickStockDatabase instance (for testing)
            config: Optional configuration dict for TickStockDatabase
        """
        self.relationship_cache = relationship_cache or get_relationship_cache()

        # Initialize database
        if db is not None:
            self.db = db
        elif config is not None:
            self.db = TickStockDatabase(config)
        else:
            # Use default config (empty dict for testing)
            try:
                from config.app_config import load_config
                app_config = load_config()
                self.db = TickStockDatabase(app_config)
            except Exception:
                # Fallback for testing - create with minimal config
                self.db = TickStockDatabase({})

        logger.info("ThresholdBarService initialized")

    def calculate_threshold_bars(
        self,
        data_source: str,
        bar_type: BarType,
        timeframe: Timeframe,
        threshold: float = 0.10,
        period_days: int = 1,
    ) -> dict[str, Any]:
        """Calculate threshold bar segments for given parameters.

        Args:
            data_source: Universe key (e.g., 'sp500'), ETF (e.g., 'SPY'),
                        or multi-universe join (e.g., 'sp500:nasdaq100')
            bar_type: Type of bar to calculate
            timeframe: OHLCV data timeframe to use
            threshold: Sensitivity threshold (default 0.10 = 10%)
            period_days: Number of days to look back for % change calculation

        Returns:
            Dictionary with structure:
            {
                "metadata": {
                    "data_source": str,
                    "bar_type": str,
                    "timeframe": str,
                    "threshold": float,
                    "period_days": int,
                    "symbol_count": int,
                    "calculated_at": str (ISO timestamp)
                },
                "segments": {
                    "significant_decline": float,  # Percentage (0-100)
                    "minor_decline": float,
                    "minor_advance": float,
                    "significant_advance": float
                }
            }

            For SimpleDivergingBar, segments only contains:
            {
                "decline": float,
                "advance": float
            }

        Raises:
            ValueError: If data_source is empty, timeframe invalid, or threshold negative
            RuntimeError: If database query fails or no data available
        """
        start_time = datetime.now()

        # Input validation
        if not data_source or not isinstance(data_source, str):
            raise ValueError(f"data_source must be non-empty string, got: {data_source}")

        if timeframe not in ["1min", "hourly", "daily", "weekly", "monthly"]:
            raise ValueError(f"Invalid timeframe: {timeframe}")

        if threshold < 0 or threshold > 1:
            raise ValueError(f"Threshold must be between 0 and 1, got: {threshold}")

        logger.info(
            f"Calculating {bar_type} for {data_source} "
            f"(timeframe={timeframe}, threshold={threshold})"
        )

        # Step 1: Load symbols from RelationshipCache
        symbols = self._load_symbols_for_data_source(data_source)

        if not symbols:
            raise RuntimeError(f"No symbols found for data_source: {data_source}")

        logger.debug(f"Loaded {len(symbols)} symbols for {data_source}")

        # Step 2: Query OHLCV data
        ohlcv_data = self._query_ohlcv_data(symbols, timeframe, period_days)

        if ohlcv_data.empty:
            raise RuntimeError(
                f"No OHLCV data available for {data_source} "
                f"(timeframe={timeframe}, symbols={len(symbols)}, period_days={period_days}). "
                f"Try increasing period_days or check if {timeframe} data exists for these symbols."
            )

        logger.debug(f"Queried {len(ohlcv_data)} OHLCV rows")

        # Step 3: Calculate percentage changes
        percentage_changes = self._calculate_percentage_changes(ohlcv_data, timeframe)

        if percentage_changes.empty:
            raise RuntimeError(f"Failed to calculate percentage changes for {data_source}")

        logger.debug(f"Calculated {len(percentage_changes)} percentage changes")

        # Step 4: Bin into segments
        binned_data = self._bin_into_segments(percentage_changes, bar_type, threshold)

        # Step 5: Aggregate segment percentages
        segments = self._aggregate_segment_percentages(binned_data, bar_type)

        elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
        logger.info(
            f"Calculated {bar_type} for {data_source} in {elapsed_ms:.1f}ms "
            f"({len(symbols)} symbols)"
        )

        return {
            "metadata": {
                "data_source": data_source,
                "bar_type": bar_type,
                "timeframe": timeframe,
                "threshold": threshold,
                "period_days": period_days,
                "symbol_count": len(symbols),
                "calculated_at": datetime.now().isoformat(),
            },
            "segments": segments,
        }

    def _load_symbols_for_data_source(self, data_source: str) -> list[str]:
        """Load symbols from RelationshipCache for given data source.

        Supports:
        - Universe keys: 'sp500', 'nasdaq100', 'dow30', 'russell3000'
        - ETF symbols: 'SPY', 'QQQ', 'IWM', etc.
        - Multi-universe joins: 'sp500:nasdaq100' (distinct union)

        Args:
            data_source: Universe key, ETF symbol, or multi-universe join

        Returns:
            List of symbols (uppercase, deduplicated)

        Raises:
            RuntimeError: If RelationshipCache lookup fails
        """
        try:
            # Try loading as universe/ETF via RelationshipCache
            # This handles both single keys and multi-universe joins
            symbols = self.relationship_cache.get_universe_symbols(data_source)

            if symbols:
                logger.debug(
                    f"Loaded {len(symbols)} symbols from RelationshipCache "
                    f"for data_source: {data_source}"
                )
                return symbols

            # Fallback: treat as direct symbol
            logger.warning(f"No universe/ETF found for '{data_source}', treating as direct symbol")
            return [data_source.upper()]

        except Exception as e:
            logger.error(f"Error loading symbols for {data_source}: {e}")
            raise RuntimeError(f"Failed to load symbols for {data_source}") from e

    def _query_ohlcv_data(
        self, symbols: list[str], timeframe: Timeframe, period_days: int
    ) -> pd.DataFrame:
        """Query OHLCV data from TimescaleDB for given symbols and timeframe.

        Args:
            symbols: List of stock symbols
            timeframe: OHLCV table to query ('1min', 'hourly', 'daily', etc.)
            period_days: Number of days to look back

        Returns:
            DataFrame with columns: symbol, timestamp, open, high, low, close, volume
            Sorted by (symbol, timestamp) ascending

        Raises:
            RuntimeError: If database query fails
        """
        table_map = {
            "1min": "ohlcv_1min",
            "hourly": "ohlcv_hourly",
            "daily": "ohlcv_daily",
            "weekly": "ohlcv_weekly",
            "monthly": "ohlcv_monthly",
        }

        # Map timeframes to correct column names per table schema
        time_column_map = {
            "1min": "timestamp",
            "hourly": "timestamp",
            "daily": "date",
            "weekly": "week_start",
            "monthly": "month_start",
        }

        table_name = table_map[timeframe]
        time_column = time_column_map[timeframe]
        cutoff_datetime = datetime.now() - timedelta(days=period_days)

        # For date columns, cast cutoff to date type; for timestamp columns, use as-is
        if timeframe in ["daily", "weekly", "monthly"]:
            cutoff_value = cutoff_datetime.date()
        else:
            cutoff_value = cutoff_datetime

        # Parameterized query with correct time column based on table
        query = f"""
            SELECT
                symbol,
                {time_column} as timestamp,
                open,
                high,
                low,
                close,
                volume
            FROM {table_name}
            WHERE symbol = ANY(%s)
              AND {time_column} >= %s
            ORDER BY symbol, {time_column}
        """

        try:
            with self.db.get_connection() as conn:
                df = pd.read_sql_query(
                    query,
                    conn,
                    params=(symbols, cutoff_value),
                )

            logger.debug(
                f"Queried {len(df)} rows from {table_name} "
                f"for {len(symbols)} symbols (period_days={period_days})"
            )

            return df

        except Exception as e:
            logger.error(f"Database query failed for {table_name}: {e}")
            raise RuntimeError(f"Failed to query {table_name}") from e

    def _calculate_percentage_changes(
        self, ohlcv_data: pd.DataFrame, timeframe: Timeframe
    ) -> pd.DataFrame:
        """Calculate percentage changes for each symbol.

        Uses vectorized pandas operations for performance.
        Calculates: (current_close - previous_close) / previous_close * 100

        Args:
            ohlcv_data: DataFrame with columns: symbol, timestamp, close
            timeframe: Timeframe being processed (for logging)

        Returns:
            DataFrame with columns: symbol, pct_change
            Only includes latest value per symbol
        """
        # Group by symbol and calculate % change
        ohlcv_data = ohlcv_data.sort_values(["symbol", "timestamp"])

        # Calculate percentage change within each symbol group
        ohlcv_data["pct_change"] = ohlcv_data.groupby("symbol")["close"].transform(
            lambda x: x.pct_change() * 100
        )

        # Get only the latest value per symbol (most recent % change)
        latest_changes = ohlcv_data.groupby("symbol").last().reset_index()[["symbol", "pct_change"]]

        # Drop NaN values (symbols with only 1 data point)
        latest_changes = latest_changes.dropna(subset=["pct_change"])

        dropped_count = len(ohlcv_data["symbol"].unique()) - len(latest_changes)
        logger.debug(
            f"Calculated pct_change for {len(latest_changes)} symbols "
            f"(dropped {dropped_count} with insufficient data)"
        )

        return latest_changes

    def _bin_into_segments(
        self, percentage_changes: pd.DataFrame, bar_type: BarType, threshold: float
    ) -> pd.Series:
        """Bin percentage changes into threshold segments.

        DivergingThresholdBar logic gates:
        - significant_decline: x < -threshold
        - minor_decline: -threshold <= x < 0
        - minor_advance: 0 <= x < threshold
        - significant_advance: x >= threshold

        SimpleDivergingBar logic gates:
        - decline: x < 0
        - advance: x >= 0

        Args:
            percentage_changes: DataFrame with 'pct_change' column
            bar_type: Type of bar to calculate
            threshold: Sensitivity threshold (e.g., 0.10 for 10%)

        Returns:
            Series with segment labels for each symbol
        """
        pct_values = percentage_changes["pct_change"].values

        if bar_type == "DivergingThresholdBar":
            # Define bins: [-inf, -threshold, 0, threshold, +inf]
            bins = [-np.inf, -threshold * 100, 0, threshold * 100, np.inf]
            labels = [
                "significant_decline",
                "minor_decline",
                "minor_advance",
                "significant_advance",
            ]
        else:  # SimpleDivergingBar
            # Define bins: [-inf, 0, +inf]
            bins = [-np.inf, 0, np.inf]
            labels = ["decline", "advance"]

        # Use pd.cut() for efficient binning
        segments = pd.cut(pct_values, bins=bins, labels=labels, right=False)

        logger.debug(
            f"Binned {len(segments)} values into {len(labels)} segments "
            f"(bar_type={bar_type}, threshold={threshold})"
        )

        return segments

    def _aggregate_segment_percentages(
        self, binned_data: pd.Series, bar_type: BarType
    ) -> dict[str, float]:
        """Aggregate binned data into segment percentages.

        Ensures sum of all percentages equals 100.0 (within floating point precision).

        Args:
            binned_data: Series with segment labels
            bar_type: Type of bar (determines expected segments)

        Returns:
            Dictionary mapping segment names to percentages (0-100)
        """
        # Count occurrences of each segment
        value_counts = binned_data.value_counts()
        total_count = len(binned_data)

        # Calculate percentages
        percentages = (value_counts / total_count * 100).to_dict()

        # Ensure all expected segments are present (fill missing with 0.0)
        if bar_type == "DivergingThresholdBar":
            expected_segments = [
                "significant_decline",
                "minor_decline",
                "minor_advance",
                "significant_advance",
            ]
        else:  # SimpleDivergingBar
            expected_segments = ["decline", "advance"]

        result = {seg: percentages.get(seg, 0.0) for seg in expected_segments}

        # Verify sum equals 100% (within floating point tolerance)
        total_pct = sum(result.values())
        if not np.isclose(total_pct, 100.0, atol=0.01):
            logger.warning(f"Segment percentages sum to {total_pct:.2f}% instead of 100.0%")

        logger.debug(f"Aggregated {total_count} values into {len(result)} segment percentages")

        return result
