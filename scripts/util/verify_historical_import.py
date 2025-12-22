"""Verify historical data import completeness for symbols."""
import sys
from datetime import datetime, timedelta
from src.infrastructure.database.db_connection import get_db_connection

def calculate_expected_bars(days):
    """Calculate expected bars for different timeframes."""
    # Assume 6.5 trading hours per day, 5 days per week
    trading_hours_per_day = 6.5
    minutes_per_day = int(trading_hours_per_day * 60)  # 390 minutes
    hours_per_day = int(trading_hours_per_day)  # 6 hours (rounded)

    return {
        '1min': minutes_per_day * days,
        'hourly': hours_per_day * days,
        'daily': days
    }

def verify_symbol_import(symbol, start_date, end_date, days):
    """Verify data import for a single symbol."""
    print(f"\n{'=' * 70}")
    print(f"Verifying: {symbol}")
    print(f"Date Range: {start_date} to {end_date} ({days} days)")
    print(f"{'=' * 70}")

    expected = calculate_expected_bars(days)
    print(f"\nExpected bars (approximate, excluding market closures):")
    print(f"  1-Minute: ~{expected['1min']} bars")
    print(f"  Hourly:   ~{expected['hourly']} bars")
    print(f"  Daily:    ~{expected['daily']} bars")

    with get_db_connection(read_only=True) as conn:
        cursor = conn.cursor()

        # Check 1-minute data
        print(f"\n1-Minute Data (ohlcv_1min):")
        cursor.execute("""
            SELECT COUNT(*) as total,
                   MIN(timestamp) as earliest,
                   MAX(timestamp) as latest
            FROM ohlcv_1min
            WHERE symbol = %s AND timestamp >= %s AND timestamp <= %s
        """, (symbol, start_date, end_date))
        result = cursor.fetchone()
        if result and result[0] > 0:
            coverage_pct = (result[0] / expected['1min']) * 100
            status = "✓ GOOD" if coverage_pct >= 90 else "⚠ PARTIAL" if coverage_pct >= 50 else "✗ POOR"
            print(f"  Total: {result[0]} bars ({coverage_pct:.1f}% of expected)")
            print(f"  Range: {result[1]} to {result[2]}")
            print(f"  Status: {status}")
        else:
            print(f"  ✗ NO DATA FOUND")

        # Check hourly data
        print(f"\nHourly Data (ohlcv_hourly):")
        cursor.execute("""
            SELECT COUNT(*) as total,
                   MIN(timestamp) as earliest,
                   MAX(timestamp) as latest
            FROM ohlcv_hourly
            WHERE symbol = %s AND timestamp >= %s AND timestamp <= %s
        """, (symbol, start_date, end_date))
        result = cursor.fetchone()
        if result and result[0] > 0:
            coverage_pct = (result[0] / expected['hourly']) * 100
            status = "✓ GOOD" if coverage_pct >= 90 else "⚠ PARTIAL" if coverage_pct >= 50 else "✗ POOR"
            print(f"  Total: {result[0]} bars ({coverage_pct:.1f}% of expected)")
            print(f"  Range: {result[1]} to {result[2]}")
            print(f"  Status: {status}")
        else:
            print(f"  ✗ NO DATA FOUND")

        # Check daily data
        print(f"\nDaily Data (ohlcv_daily):")
        cursor.execute("""
            SELECT COUNT(*) as total,
                   MIN(date) as earliest,
                   MAX(date) as latest
            FROM ohlcv_daily
            WHERE symbol = %s AND date >= %s AND date <= %s
        """, (symbol, start_date, end_date))
        result = cursor.fetchone()
        if result and result[0] > 0:
            coverage_pct = (result[0] / expected['daily']) * 100
            status = "✓ GOOD" if coverage_pct >= 90 else "⚠ PARTIAL" if coverage_pct >= 50 else "✗ POOR"
            print(f"  Total: {result[0]} bars ({coverage_pct:.1f}% of expected)")
            print(f"  Range: {result[1]} to {result[2]}")
            print(f"  Status: {status}")
        else:
            print(f"  ✗ NO DATA FOUND")

        # Check if symbol exists in symbols table
        print(f"\nSymbol Metadata:")
        cursor.execute("""
            SELECT symbol, name, last_updated
            FROM symbols
            WHERE symbol = %s
        """, (symbol,))
        result = cursor.fetchone()
        if result:
            print(f"  ✓ Registered: {result[1]}")
            print(f"  Last Updated: {result[2]}")
        else:
            print(f"  ✗ NOT REGISTERED in symbols table")

        cursor.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python verify_historical_import.py SYMBOL1,SYMBOL2,... [DAYS]")
        print("Example: python verify_historical_import.py SCHG,VUG 2")
        print("Example: python verify_historical_import.py SPY,QQQ,IWM 90")
        sys.exit(1)

    # Parse arguments
    symbols = sys.argv[1].split(',')
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 2

    # Calculate date range
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)

    print("=" * 70)
    print("HISTORICAL DATA IMPORT VERIFICATION")
    print("=" * 70)
    print(f"Symbols: {', '.join(symbols)}")
    print(f"Period: {days} days ({start_date} to {end_date})")
    print("=" * 70)

    # Verify each symbol
    for symbol in symbols:
        verify_symbol_import(symbol.strip().upper(), start_date, end_date, days)

    print(f"\n{'=' * 70}")
    print("VERIFICATION COMPLETE")
    print("=" * 70)
