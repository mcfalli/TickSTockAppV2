"""Breadth Metrics Service for market participation analysis.

Calculates 12 breadth metrics showing up/down counts across time periods
and moving average relationships for market breadth analysis.

Sprint 66: Market Breadth Metrics Implementation
"""

import logging
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from src.core.services.relationship_cache import get_relationship_cache
from src.infrastructure.database.tickstock_db import TickStockDatabase

logger = logging.getLogger(__name__)


class BreadthMetricsService:
    """Service for calculating market breadth metrics for any stock universe.

    Calculates 12 metrics showing up/down counts across time periods
    and moving average relationships for market breadth analysis.

    Supports any universe: SPY (504 stocks), QQQ (102 stocks), dow30 (30 stocks), etc.

    Performance targets:
    - Full 12-metric calculation: <50ms
    - Database query: <30ms
    - Pandas calculation: <20ms
    """

    def __init__(self, relationship_cache=None, db=None, config=None):
        """Initialize the breadth metrics service.

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

        logger.info("BreadthMetricsService initialized")

    def calculate_breadth_metrics(self, universe: str = "SPY") -> dict:
        """Calculate all 12 breadth metrics in one pass.

        Args:
            universe: Universe key (default: 'SPY' for S&P 500)

        Returns:
            Dictionary with structure:
            {
                "metrics": {
                    "day_change": {"up": 345, "down": 159, "unchanged": 0, "pct_up": 68.5},
                    "open_change": {...},
                    "week": {...},
                    "month": {...},
                    "quarter": {...},
                    "half_year": {...},
                    "year": {...},
                    "price_to_ema10": {...},
                    "price_to_ema20": {...},
                    "price_to_sma50": {...},
                    "price_to_sma200": {...}
                },
                "metadata": {
                    "universe": "SPY",
                    "symbol_count": 504,
                    "calculation_time_ms": 42.3,
                    "calculated_at": "2026-02-07T14:45:00.123456"
                }
            }

        Raises:
            ValueError: If universe empty or invalid
            RuntimeError: If no symbols found or database failure
        """
        start_time = datetime.now()

        # Validation
        if not universe or not isinstance(universe, str):
            raise ValueError(f"universe must be non-empty string, got: {universe}")

        logger.info(f"Calculating breadth metrics for {universe}")

        # Step 1: Load symbols via RelationshipCache
        symbols = self.relationship_cache.get_universe_symbols(universe)

        if not symbols:
            raise RuntimeError(f"No symbols found for universe: {universe}")

        logger.debug(f"Loaded {len(symbols)} symbols for {universe}")

        # Step 2: Fetch 252 days of OHLCV data (covers all periods up to 1 year)
        df = self._query_ohlcv_data(symbols, timeframe="daily", period_days=252)

        if df.empty:
            raise RuntimeError(
                f"No OHLCV data available for {universe} "
                f"(symbols={len(symbols)}, period_days=252). "
                f"Check if daily OHLCV data exists for these symbols."
            )

        logger.debug(f"Queried {len(df)} OHLCV rows")

        # Step 3: Calculate all 12 metrics from same DataFrame
        metrics = {
            "day_change": self._calculate_day_change(df),
            "open_change": self._calculate_open_change(df),
            "week": self._calculate_period_change(df, 5),
            "month": self._calculate_period_change(df, 21),
            "quarter": self._calculate_period_change(df, 63),
            "half_year": self._calculate_period_change(df, 126),
            "year": self._calculate_period_change(df, 252),
            "price_to_ema10": self._calculate_ema_comparison(df, 10),
            "price_to_ema20": self._calculate_ema_comparison(df, 20),
            "price_to_sma50": self._calculate_sma_comparison(df, 50),
            "price_to_sma200": self._calculate_sma_comparison(df, 200),
        }

        elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
        logger.info(
            f"Calculated breadth metrics for {universe} in {elapsed_ms:.1f}ms "
            f"({len(symbols)} symbols)"
        )

        return {
            "metrics": metrics,
            "metadata": {
                "universe": universe,
                "symbol_count": len(symbols),
                "calculation_time_ms": round(elapsed_ms, 2),
                "calculated_at": datetime.now().isoformat(),
            },
        }

    def _calculate_day_change(self, df: pd.DataFrame) -> dict:
        """Calculate day change: Today close vs yesterday close.

        Formula: (close_today - close_yesterday) / close_yesterday
        """
        df_sorted = df.sort_values(["symbol", "date"])

        # Calculate percentage change per symbol
        df_sorted["pct_change"] = df_sorted.groupby("symbol")["close"].transform(
            lambda x: x.pct_change() * 100
        )

        # Get latest change per symbol
        latest = df_sorted.groupby("symbol").last().reset_index()
        latest = latest.dropna(subset=["pct_change"])

        # Count up/down/unchanged
        up_count = (latest["pct_change"] > 0).sum()
        down_count = (latest["pct_change"] < 0).sum()
        unchanged_count = (latest["pct_change"] == 0).sum()

        total = len(latest)
        pct_up = (up_count / total * 100) if total > 0 else 0.0

        return {
            "up": int(up_count),
            "down": int(down_count),
            "unchanged": int(unchanged_count),
            "pct_up": round(pct_up, 2),
        }

    def _calculate_open_change(self, df: pd.DataFrame) -> dict:
        """Calculate open change: Today close vs today open.

        Formula: (close_today - open_today) / open_today
        """
        latest = df.groupby("symbol").last().reset_index()

        # Calculate intraday change
        latest["pct_change"] = (latest["close"] - latest["open"]) / latest["open"] * 100
        latest = latest.dropna(subset=["pct_change"])

        # Count up/down/unchanged
        up_count = (latest["pct_change"] > 0).sum()
        down_count = (latest["pct_change"] < 0).sum()
        unchanged_count = (latest["pct_change"] == 0).sum()

        total = len(latest)
        pct_up = (up_count / total * 100) if total > 0 else 0.0

        return {
            "up": int(up_count),
            "down": int(down_count),
            "unchanged": int(unchanged_count),
            "pct_up": round(pct_up, 2),
        }

    def _calculate_period_change(self, df: pd.DataFrame, days: int) -> dict:
        """Generic period change calculation.

        Args:
            df: OHLCV DataFrame
            days: Lookback period (5=week, 21=month, 63=quarter, 126=half_year, 252=year)

        Formula: (close_latest - close_N_days_ago) / close_N_days_ago
        """
        df_sorted = df.sort_values(["symbol", "date"])

        # Calculate change from N days ago per symbol
        def calc_period_pct_change(x):
            if len(x) >= days:
                return (x.iloc[-1] - x.iloc[-days]) / x.iloc[-days] * 100
            return np.nan

        df_sorted["pct_change"] = df_sorted.groupby("symbol")["close"].transform(
            calc_period_pct_change
        )

        # Get latest value per symbol
        latest = df_sorted.groupby("symbol").last().reset_index()
        latest = latest.dropna(subset=["pct_change"])

        # Count up/down/unchanged
        up_count = (latest["pct_change"] > 0).sum()
        down_count = (latest["pct_change"] < 0).sum()
        unchanged_count = (latest["pct_change"] == 0).sum()

        total = len(latest)
        pct_up = (up_count / total * 100) if total > 0 else 0.0

        return {
            "up": int(up_count),
            "down": int(down_count),
            "unchanged": int(unchanged_count),
            "pct_up": round(pct_up, 2),
        }

    def _calculate_ema_comparison(self, df: pd.DataFrame, period: int) -> dict:
        """Calculate price vs EMA comparison.

        Args:
            df: OHLCV DataFrame
            period: EMA period (10 or 20)

        Formula: close > EMA(period) → above, close < EMA(period) → below
        """
        df_sorted = df.sort_values(["symbol", "date"])

        # Calculate EMA per symbol (adjust=False for standard EMA)
        df_sorted["ema"] = df_sorted.groupby("symbol")["close"].transform(
            lambda x: x.ewm(span=period, adjust=False, min_periods=period).mean()
        )

        # Get latest values
        latest = df_sorted.groupby("symbol").last().reset_index()
        latest = latest.dropna(subset=["ema"])

        # Count above/below EMA
        above_count = (latest["close"] > latest["ema"]).sum()
        below_count = (latest["close"] < latest["ema"]).sum()
        equal_count = (latest["close"] == latest["ema"]).sum()

        total = len(latest)
        pct_above = (above_count / total * 100) if total > 0 else 0.0

        return {
            "up": int(above_count),  # 'up' = above EMA
            "down": int(below_count),  # 'down' = below EMA
            "unchanged": int(equal_count),
            "pct_up": round(pct_above, 2),
        }

    def _calculate_sma_comparison(self, df: pd.DataFrame, period: int) -> dict:
        """Calculate price vs SMA comparison.

        Args:
            df: OHLCV DataFrame
            period: SMA period (50 or 200)

        Formula: close > SMA(period) → above, close < SMA(period) → below
        """
        df_sorted = df.sort_values(["symbol", "date"])

        # Calculate SMA per symbol (min_periods=period for true SMA)
        df_sorted["sma"] = df_sorted.groupby("symbol")["close"].transform(
            lambda x: x.rolling(window=period, min_periods=period).mean()
        )

        # Get latest values
        latest = df_sorted.groupby("symbol").last().reset_index()
        latest = latest.dropna(subset=["sma"])

        # Count above/below SMA
        above_count = (latest["close"] > latest["sma"]).sum()
        below_count = (latest["close"] < latest["sma"]).sum()
        equal_count = (latest["close"] == latest["sma"]).sum()

        total = len(latest)
        pct_above = (above_count / total * 100) if total > 0 else 0.0

        return {
            "up": int(above_count),  # 'up' = above SMA
            "down": int(below_count),  # 'down' = below SMA
            "unchanged": int(equal_count),
            "pct_up": round(pct_above, 2),
        }

    def _query_ohlcv_data(
        self, symbols: list[str], timeframe: str = "daily", period_days: int = 252
    ) -> pd.DataFrame:
        """Query OHLCV data from TimescaleDB.

        CRITICAL: Uses 'date' column for ohlcv_daily (NOT 'timestamp')
        PATTERN: Follow threshold_bar_service.py lines 266-287 exactly

        Args:
            symbols: List of stock symbols to query
            timeframe: Timeframe (only 'daily' supported for now)
            period_days: Number of days to look back

        Returns:
            DataFrame with columns: symbol, date, open, high, low, close, volume
        """
        table_name = "ohlcv_daily"
        time_column = "date"  # CRITICAL: ohlcv_daily uses 'date' column

        cutoff_datetime = datetime.now() - timedelta(days=period_days)
        cutoff_value = cutoff_datetime.date()  # Cast to date for date-based table

        query = f"""
            SELECT
                symbol,
                {time_column} as date,
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
                df = pd.read_sql_query(query, conn, params=(symbols, cutoff_value))

            logger.debug(
                f"Queried {len(df)} rows from {table_name} "
                f"for {len(symbols)} symbols (period_days={period_days})"
            )

            return df

        except Exception as e:
            logger.error(f"Database query failed for {table_name}: {e}")
            raise RuntimeError(f"Failed to query {table_name}") from e
