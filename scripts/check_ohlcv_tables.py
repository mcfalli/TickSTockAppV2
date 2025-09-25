#!/usr/bin/env python3
"""Check OHLCV table record counts"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text

# Database connection from environment
DATABASE_URI = os.getenv('DATABASE_URI',
                         'postgresql://app_readwrite:LJI48rUEkUpe6e@localhost:5432/tickstock')

def check_ohlcv_tables():
    """Check record counts in all OHLCV tables"""
    try:
        engine = create_engine(DATABASE_URI)

        tables = ['ohlcv_daily', 'ohlcv_hourly', 'ohlcv_weekly', 'ohlcv_monthly', 'ohlcv_1min']

        print("OHLCV Table Record Counts")
        print("=" * 50)

        with engine.connect() as conn:
            for table in tables:
                try:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = result.scalar()
                    print(f"{table:20} : {count:,} records")
                except Exception as e:
                    print(f"{table:20} : Error - {e}")

            # Also check symbols table
            print("\nRelated Tables:")
            print("-" * 50)

            result = conn.execute(text("SELECT COUNT(*) FROM symbols"))
            symbol_count = result.scalar()
            print(f"{'symbols':20} : {symbol_count:,} records")

            # Check for recent data
            print("\nMost Recent Data:")
            print("-" * 50)

            for table in ['ohlcv_daily', 'ohlcv_1min']:
                try:
                    # Use 'date' for ohlcv_daily, 'timestamp' for ohlcv_1min
                    date_col = 'date' if table == 'ohlcv_daily' else 'timestamp'
                    result = conn.execute(text(f"""
                        SELECT symbol, MAX({date_col}) as latest_date
                        FROM {table}
                        GROUP BY symbol
                        ORDER BY latest_date DESC
                        LIMIT 5
                    """))
                    rows = result.fetchall()
                    if rows:
                        print(f"\n{table}:")
                        for row in rows:
                            print(f"  {row.symbol}: {row.latest_date}")
                    else:
                        print(f"\n{table}: No data")
                except Exception as e:
                    print(f"\n{table}: Error - {e}")

        print("\n" + "=" * 50)
        print("Database check complete")

    except Exception as e:
        print(f"Connection error: {e}")
        print("\nTrying alternate connection...")

        # Try with different port if default fails
        try:
            alt_uri = DATABASE_URI.replace(':5432', ':5433')
            engine = create_engine(alt_uri)
            with engine.connect() as conn:
                result = conn.execute(text("SELECT version()"))
                print(f"Connected to: {result.scalar()}")
        except:
            print("Could not connect to database on either port 5432 or 5433")

if __name__ == "__main__":
    check_ohlcv_tables()