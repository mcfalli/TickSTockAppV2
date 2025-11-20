#!/usr/bin/env python3
"""
Test ETF functionality in the historical loader
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from data.historical_loader import MassiveHistoricalLoader


def test_etf_loading():
    """Test loading a few ETF symbols"""
    print("🧪 Testing Enhanced ETF Historical Loader")
    print("=" * 50)

    # Initialize loader
    loader = MassiveHistoricalLoader()

    # Test ETF symbols
    test_symbols = ['SPY', 'QQQ', 'VTI']

    for symbol in test_symbols:
        print(f"\n🔄 Testing ETF: {symbol}")

        # Test symbol metadata fetching
        metadata = loader.fetch_symbol_metadata(symbol)
        if metadata:
            print("   ✅ Metadata fetched:")
            print(f"   - Name: {metadata.get('name', 'N/A')}")
            print(f"   - Type: {metadata.get('type', 'N/A')}")
            print(f"   - ETF Type: {metadata.get('etf_type', 'N/A')}")
            print(f"   - Issuer: {metadata.get('issuer', 'N/A')}")
            print(f"   - AUM (M): ${metadata.get('aum_millions', 'N/A')}")
            print(f"   - Correlation Ref: {metadata.get('correlation_reference', 'N/A')}")
            print(f"   - Underlying Index: {metadata.get('underlying_index', 'N/A')}")
        else:
            print("   ❌ Failed to fetch metadata")

        # Test ensure symbol exists (full database upsert)
        print("   🔄 Testing database upsert...")
        success = loader.ensure_symbol_exists(symbol)
        if success:
            print("   ✅ Database upsert successful")
        else:
            print("   ❌ Database upsert failed")

    print("\n📊 Test completed!")

if __name__ == "__main__":
    test_etf_loading()
