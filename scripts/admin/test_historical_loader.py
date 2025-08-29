#!/usr/bin/env python3
"""
Test historical loader functionality to diagnose job failures
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import config_manager for proper configuration loading
from src.core.services.config_manager import get_config

def test_historical_loader():
    """Test the historical loader step by step"""
    
    print("=== Historical Loader Diagnostic Test ===\n")
    
    # Step 1: Test imports
    print("1. Testing imports...")
    try:
        from src.data.historical_loader import PolygonHistoricalLoader
        print("   ✅ PolygonHistoricalLoader imported successfully")
    except Exception as e:
        print(f"   ❌ Import failed: {e}")
        return False
    
    # Step 2: Test configuration loading
    print("\n2. Testing configuration...")
    try:
        config = get_config()
        api_key = config.get('POLYGON_API_KEY')
        db_uri = config.get('DATABASE_URI')
        
        print(f"   POLYGON_API_KEY: {'✅ Set' if api_key else '❌ Missing'}")
        print(f"   DATABASE_URI: {'✅ Set' if db_uri else '❌ Missing'}")
        
        if not db_uri:
            print("   ❌ DATABASE_URI is required")
            return False
            
        print("   ✅ Configuration loaded successfully")
    except Exception as e:
        print(f"   ❌ Configuration loading failed: {e}")
        return False
    
    # Step 3: Test loader initialization
    print("\n3. Testing loader initialization...")
    try:
        loader = PolygonHistoricalLoader()
        print("   ✅ Loader initialized successfully")
    except Exception as e:
        print(f"   ❌ Loader initialization failed: {e}")
        return False
    
    # Step 4: Test database connection
    print("\n4. Testing database connection...")
    try:
        loader._connect_db()
        print("   ✅ Database connected successfully")
    except Exception as e:
        print(f"   ❌ Database connection failed: {e}")
        return False
    
    # Step 5: Test universe loading
    print("\n5. Testing universe loading...")
    try:
        symbols = loader.load_symbols_from_cache('top_50')
        print(f"   ✅ Loaded {len(symbols)} symbols from top_50")
        print(f"   First 5 symbols: {symbols[:5]}")
    except Exception as e:
        print(f"   ❌ Universe loading failed: {e}")
        return False
    
    # Step 6: Test API connectivity (if key available)
    if api_key:
        print("\n6. Testing API connectivity...")
        try:
            from datetime import datetime, timedelta
            start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            end_date = datetime.now().strftime('%Y-%m-%d')
            
            test_symbol = symbols[0] if symbols else 'AAPL'
            print(f"   Testing with symbol: {test_symbol}")
            print(f"   Date range: {start_date} to {end_date}")
            
            df = loader.fetch_symbol_data(test_symbol, start_date, end_date, 'day')
            
            if not df.empty:
                print(f"   ✅ API test successful: {len(df)} records retrieved")
                print(f"   Sample data columns: {list(df.columns)}")
            else:
                print("   ⚠️  API returned empty data (might be weekend/holiday)")
                
        except Exception as e:
            print(f"   ❌ API test failed: {e}")
            print("   This could be due to:")
            print("   - Invalid API key")
            print("   - Rate limiting")
            print("   - Network connectivity")
            print("   - Weekend/holiday (no market data)")
    else:
        print("\n6. Skipping API test (no POLYGON_API_KEY)")
    
    print("\n=== Diagnostic Complete ===")
    
    if api_key and db_uri:
        print("\n🎯 RECOMMENDATION:")
        print("   All core components are working.")
        print("   Try submitting a small test job:")
        print("   - Load Type: Universe") 
        print("   - Universe: top_50")
        print("   - Timeframe: 0.1 years (36 days)")
        print("   - Timespan: day")
        print("   Monitor the job status and check server logs for errors.")
    else:
        print("\n⚠️  SETUP REQUIRED:")
        if not api_key:
            print("   - Add POLYGON_API_KEY=your_api_key_here to your .env file")
            print("   - You can get a free API key from https://polygon.io/")
        if not db_uri:
            print("   - DATABASE_URI should be automatically configured")
            print("   - Check your .env file and config_manager settings")
    
    return True

if __name__ == '__main__':
    test_historical_loader()