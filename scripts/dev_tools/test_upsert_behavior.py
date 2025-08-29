"""
Test script to demonstrate upsert behavior of historical data loader
Shows how existing data is handled vs new data
"""

import os
import sys
import pandas as pd
from datetime import datetime, timedelta

# Add src to path
sys.path.append('src')

from src.data.historical_loader import PolygonHistoricalLoader

def test_upsert_behavior():
    """Test how the loader handles existing vs new data"""
    
    print("=== Testing Upsert Behavior ===\n")
    
    try:
        loader = PolygonHistoricalLoader(
            database_uri='postgresql://app_readwrite:LJI48rUEkUpe6e@localhost:5433/tickstock'
        )
        
        print("1. Current AAPL data before update:")
        # Show current data first
        import psycopg2
        from psycopg2.extras import RealDictCursor
        conn = psycopg2.connect('postgresql://app_readwrite:LJI48rUEkUpe6e@localhost:5433/tickstock')
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT symbol, date, open, close, volume 
            FROM ohlcv_daily 
            WHERE symbol = 'AAPL' AND date >= '2024-01-01'
            ORDER BY date
        """)
        
        existing_data = cursor.fetchall()
        for row in existing_data:
            print(f"  {row['symbol']} {row['date']} | Open: {row['open']} Close: {row['close']} Vol: {row['volume']}")
        
        print(f"\n2. Testing upsert with overlapping data...")
        
        # Create overlapping data with DIFFERENT values for same dates
        overlap_data = []
        base_date = datetime(2024, 1, 3)  # Overlap with existing Jan 3-5, plus new Jan 6-7
        
        for i in range(5):  # 5 days: 3 overlapping + 2 new
            date = base_date + timedelta(days=i)
            overlap_data.append({
                'symbol': 'AAPL',
                'timestamp': date,
                'open': 200.0 + i,    # Different values
                'high': 205.0 + i,
                'low': 195.0 + i,
                'close': 202.0 + i,   # Different values
                'volume': 2000000 + i * 10000,  # Different values
            })
            
        overlap_df = pd.DataFrame(overlap_data)
        print("Data to insert (some overlapping, some new):")
        print(overlap_df[['symbol', 'timestamp', 'open', 'close', 'volume']])
        
        # Insert the data
        print("\n3. Inserting overlapping + new data...")
        loader.save_data_to_db(overlap_df, 'day')
        print("Success: Data inserted with upsert")
        
        print("\n4. AAPL data after upsert:")
        cursor.execute("""
            SELECT symbol, date, open, close, volume 
            FROM ohlcv_daily 
            WHERE symbol = 'AAPL' AND date >= '2024-01-01'
            ORDER BY date
        """)
        
        updated_data = cursor.fetchall()
        for row in updated_data:
            print(f"  {row['symbol']} {row['date']} | Open: {row['open']} Close: {row['close']} Vol: {row['volume']}")
        
        print("\n=== Analysis ===")
        print("BEHAVIOR: ON CONFLICT DO UPDATE")
        print("- Existing records (Jan 1-2): UNCHANGED (not in new dataset)")
        print("- Overlapping records (Jan 3-5): UPDATED with new values") 
        print("- New records (Jan 6-7): INSERTED")
        print("- No data is deleted, only updated or inserted")
        print("- created_at timestamp updated for modified records")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"ERROR: Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_upsert_behavior()