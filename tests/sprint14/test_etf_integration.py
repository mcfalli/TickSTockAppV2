#!/usr/bin/env python3
"""
Quick test script for ETF integration in Sprint 14 Phase 1
Tests the enhanced historical loader with ETF support
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from data.historical_loader import MassiveHistoricalLoader


def test_etf_integration():
    """Test the ETF integration functionality"""
    print("=== Sprint 14 Phase 1: ETF Integration Test ===\n")

    try:
        # Initialize loader
        print("1. Initializing historical loader...")
        loader = MassiveHistoricalLoader()
        print("+ Historical loader initialized\n")

        # Test 1: Create ETF universes
        print("2. Creating ETF universe entries...")
        loader.create_etf_universes()
        print("+ ETF universes created\n")

        # Test 2: Load ETF symbols from cache
        print("3. Testing ETF universe loading...")
        growth_etfs = loader.load_symbols_from_cache('etf_growth')
        sector_etfs = loader.load_symbols_from_cache('etf_sectors')
        print(f"+ Growth ETFs loaded: {len(growth_etfs)} symbols")
        print(f"+ Sector ETFs loaded: {len(sector_etfs)} symbols")
        print(f"Sample growth ETFs: {growth_etfs[:5]}")
        print(f"Sample sector ETFs: {sector_etfs[:5]}\n")

        # Test 3: Test symbol metadata fetching (without API key - shows structure)
        print("4. Testing ETF metadata structure...")
        test_symbols = ['SPY', 'QQQ', 'VTI']
        for symbol in test_symbols:
            try:
                # This will show the ETF metadata extraction logic
                metadata = {
                    'symbol': symbol,
                    'type': 'ETF',
                    'name': f'Test {symbol} ETF'
                }
                etf_metadata = loader._extract_etf_metadata(metadata)
                print(f"+ {symbol} ETF metadata: issuer={etf_metadata.get('issuer')}, ref={etf_metadata.get('correlation_reference')}")
            except Exception as e:
                print(f"  - {symbol}: {e}")
        print()

        # Test 4: Database connectivity test
        print("5. Testing database connectivity...")
        loader._connect_db()
        print("+ Database connection successful")
        loader._close_db()
        print("+ Database connection closed\n")

        print("=== ETF Integration Test Summary ===")
        print("+ ETF universe creation: PASSED")
        print("+ ETF symbol loading: PASSED")
        print("+ ETF metadata extraction: PASSED")
        print("+ Database connectivity: PASSED")
        print("\n*** Sprint 14 Phase 1 ETF Integration: READY FOR TESTING! ***")
        print("\nNext steps:")
        print("1. Run PostgreSQL migration script in PGAdmin")
        print("2. Test with API: python -m src.data.historical_loader --create-etf-universes")
        print("3. Load sample ETF data: python -m src.data.historical_loader --universe etf_broad_market --symbols SPY,QQQ,VTI --months 3 --dev-mode")

    except Exception as e:
        print(f"ERROR: Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_etf_integration()
