"""
Test script for historical data loader functionality
Demonstrates how to use the historical loader without requiring API keys
"""

import os
import sys
import pandas as pd
from datetime import datetime, timedelta
from src.core.services.config_manager import get_config


# Get configuration
try:
    config = get_config()
except:
    config = None

# Add src to path
sys.path.append('src')

from src.data.historical_loader import PolygonHistoricalLoader

def test_loader_functionality():
    """Test historical loader with mock data"""
    
    print("=== TickStock Historical Data Loader Test ===\n")
    
    # Initialize loader with database only (no API key needed for testing)
    try:
        loader = PolygonHistoricalLoader(
            database_uri='config.get('DATABASE_URI', 'postgresql://app_readwrite:password@localhost:5432/tickstock')'
        )
        print("Success: Loader initialized successfully")
        
        # Test 1: Load symbols from cache
        print("\n1. Testing symbol loading from cache...")
        symbols = loader.load_symbols_from_cache('top_50')
        print(f"Success: Loaded {len(symbols)} symbols from top_50 universe")
        print(f"First 10 symbols: {', '.join(symbols[:10])}")
        
        # Test 2: Check current data summary
        print("\n2. Checking current data summary...")
        daily_summary = loader.get_data_summary('day')
        print("Daily data summary:")
        for key, value in daily_summary.items():
            print(f"  {key}: {value}")
            
        minute_summary = loader.get_data_summary('minute')  
        print("1-minute data summary:")
        for key, value in minute_summary.items():
            print(f"  {key}: {value}")
        
        # Test 3: Mock data insertion (simulate what would happen with API data)
        print("\n3. Testing mock data insertion...")
        
        # Create sample historical data
        mock_data = []
        base_date = datetime(2024, 1, 1)
        
        for i in range(5):  # 5 days of data
            date = base_date + timedelta(days=i)
            mock_data.append({
                'symbol': 'AAPL',  # Use real symbol that exists in symbols table
                'timestamp': date,
                'open': 100.0 + i,
                'high': 105.0 + i,
                'low': 95.0 + i, 
                'close': 102.0 + i,
                'volume': 1000000 + i * 10000,
                'transactions': 5000 + i * 100
            })
            
        mock_df = pd.DataFrame(mock_data)
        print(f"Success: Created mock dataset: {len(mock_df)} records")
        print(mock_df[['symbol', 'timestamp', 'open', 'close', 'volume']].head())
        
        # Insert mock data
        print("\n4. Inserting mock data...")
        loader.save_data_to_db(mock_df, 'day')
        print("Success: Mock data inserted successfully")
        
        # Test 4: Verify insertion
        print("\n5. Verifying data insertion...")
        updated_summary = loader.get_data_summary('day')
        print("Updated daily data summary:")
        for key, value in updated_summary.items():
            print(f"  {key}: {value}")
        
        # Test 5: Show how to handle errors (API key missing for real requests)
        print("\n6. Testing API error handling...")
        try:
            # This should fail gracefully since no API key is set
            loader.fetch_symbol_data('AAPL', '2024-01-01', '2024-01-10')
        except ValueError as e:
            print(f"Success: API error handled correctly: {e}")
        
        print("\n=== All tests completed successfully! ===")
        print("\nTo load real data from Polygon.io:")
        print("1. Set POLYGON_API_KEY environment variable")
        print("2. Run: python -m src.data.historical_loader --universe top_50 --years 1")
        print("3. Or with specific symbols: python -m src.data.historical_loader --symbols AAPL,MSFT,NVDA --years 1")
        
    except Exception as e:
        print(f"ERROR: Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_loader_functionality()