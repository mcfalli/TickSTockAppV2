#!/usr/bin/env python3
"""
Verify EMA_200 calculation for TSLA to diagnose discrepancy with Massive API.

Sprint 76: Investigating why our EMA_200 (398.53) differs from Massive API (394.17)
"""

import pandas as pd
from sqlalchemy import create_engine, text
import sys
sys.path.insert(0, 'C:/Users/McDude/TickStockAppV2')

from config.config import get_config

def verify_ema_200():
    """Calculate EMA_200 for TSLA using multiple methods."""

    print("=" * 70)
    print("EMA_200 Verification for TSLA")
    print("=" * 70)

    # Get database connection
    config = get_config()
    engine = create_engine(config.DATABASE_URI)

    # Fetch TSLA close prices
    query = text("""
        SELECT date, close
        FROM ohlcv_daily
        WHERE symbol = 'TSLA'
        ORDER BY date ASC
    """)

    with engine.connect() as conn:
        df = pd.read_sql(query, conn)

    print(f"\nTotal bars: {len(df)}")
    print(f"Date range: {df['date'].min()} to {df['date'].max()}")
    print(f"Latest close: ${df['close'].iloc[-1]}")

    # Calculate EMA_200 using different methods
    closes = df['close'].astype(float)

    # Method 1: pandas ewm with adjust=False (our current method)
    ema_adjust_false = closes.ewm(span=200, adjust=False, min_periods=200).mean()

    # Method 2: pandas ewm with adjust=True (alternative)
    ema_adjust_true = closes.ewm(span=200, adjust=True, min_periods=200).mean()

    # Method 3: Manual calculation with SMA seed
    def manual_ema(closes, period=200):
        """Manually calculate EMA with SMA as initial seed."""
        alpha = 2 / (period + 1)
        ema_values = [None] * len(closes)

        # Seed with SMA of first N values
        if len(closes) >= period:
            ema_values[period - 1] = closes[:period].mean()

            # Calculate remaining EMA values
            for i in range(period, len(closes)):
                ema_values[i] = alpha * closes[i] + (1 - alpha) * ema_values[i - 1]

        return pd.Series(ema_values, index=closes.index)

    ema_manual = manual_ema(closes.values, 200)

    # Get latest values
    latest_idx = len(df) - 1

    print("\n" + "=" * 70)
    print("EMA_200 Results (as of Feb 12, 2026):")
    print("=" * 70)
    print(f"Method 1 (adjust=False): ${ema_adjust_false.iloc[latest_idx]:.2f}")
    print(f"Method 2 (adjust=True):  ${ema_adjust_true.iloc[latest_idx]:.2f}")
    print(f"Method 3 (manual calc):  ${ema_manual.iloc[latest_idx]:.2f}")
    print(f"\nMassive API reports:     $394.17")
    print(f"Our database value:      $398.53")

    # Calculate alpha
    alpha = 2 / 201
    print(f"\nAlpha (smoothing factor): {alpha:.6f}")
    print(f"Formula: EMA_t = α × Close_t + (1-α) × EMA_(t-1)")

    # Show last 10 EMA values for debugging
    print("\n" + "=" * 70)
    print("Last 10 EMA_200 values (Method 1):")
    print("=" * 70)
    for i in range(latest_idx - 9, latest_idx + 1):
        date = df['date'].iloc[i]
        close = df['close'].iloc[i]
        ema = ema_adjust_false.iloc[i]
        print(f"{date.strftime('%Y-%m-%d')}: Close=${close:7.2f}, EMA_200=${ema:7.2f}")

    # Check for data gaps
    print("\n" + "=" * 70)
    print("Checking for data gaps:")
    print("=" * 70)
    df['date_diff'] = df['date'].diff().dt.days
    gaps = df[df['date_diff'] > 3]  # More than 3 days (weekend + 1)
    if len(gaps) > 0:
        print(f"Found {len(gaps)} potential gaps:")
        print(gaps[['date', 'date_diff']].head(10))
    else:
        print("No significant gaps found")

    return ema_adjust_false.iloc[latest_idx]

if __name__ == '__main__':
    result = verify_ema_200()
    print(f"\n✅ Verification complete. Our EMA_200 = ${result:.2f}")
