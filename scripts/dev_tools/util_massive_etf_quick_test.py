"""
Quick ETF Test using Massive API open-close endpoint

Simple test to verify ETFs are available using the proven endpoint:
https://api.massive.com/v1/open-close/{SYMBOL}/{DATE}?adjusted=true&apiKey={KEY}

Usage:
    python scripts/dev_tools/util_massive_etf_quick_test.py
    python scripts/dev_tools/util_massive_etf_quick_test.py SPY QQQ XLF XLE GLD
"""

import os
import sys
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

import requests
from src.core.services.config_manager import ConfigManager

# Common ETFs to test
DEFAULT_ETFS = [
    'SPY', 'QQQ', 'DIA', 'IWM',      # Market indices
    'XLF', 'XLE', 'XLK', 'XLV',      # SPDR Sectors
    'XLI', 'XLB', 'XLRE', 'XLU',     # More sectors
    'XLY', 'XLP',                     # Consumer sectors
    'GLD', 'SLV',                     # Commodities
    'TLT', 'AGG'                      # Bonds
]

def test_etf(symbol, api_key, test_date):
    """Test a single ETF using the open-close endpoint"""
    url = f"https://api.massive.com/v1/open-close/{symbol}/{test_date}"
    params = {
        'adjusted': 'true',
        'apiKey': api_key
    }

    try:
        response = requests.get(url, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()
            return {
                'symbol': symbol,
                'status': 'OK',
                'open': data.get('open'),
                'high': data.get('high'),
                'low': data.get('low'),
                'close': data.get('close'),
                'volume': data.get('volume'),
                'date': data.get('from')
            }
        else:
            return {
                'symbol': symbol,
                'status': 'ERROR',
                'error': f"HTTP {response.status_code}",
                'message': response.text[:100]
            }
    except Exception as e:
        return {
            'symbol': symbol,
            'status': 'ERROR',
            'error': str(e)[:100]
        }

def main():
    # Get API key
    config_manager = ConfigManager()
    config_manager.load_from_env()
    config = config_manager.get_config()
    api_key = config.get('MASSIVE_API_KEY')

    if not api_key:
        print("ERROR: MASSIVE_API_KEY not found in .env")
        sys.exit(1)

    # Get symbols to test
    if len(sys.argv) > 1:
        symbols = [s.upper() for s in sys.argv[1:]]
    else:
        symbols = DEFAULT_ETFS

    # Use a recent trading day (few days ago to avoid weekends)
    test_date = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')

    print("=" * 70)
    print("MASSIVE API - ETF QUICK TEST")
    print("=" * 70)
    print(f"API Key: *****{api_key[-4:]}")
    print(f"Test Date: {test_date}")
    print(f"Testing {len(symbols)} ETFs")
    print("=" * 70)

    results = []
    for symbol in symbols:
        print(f"\nTesting {symbol}...", end=' ')
        result = test_etf(symbol, api_key, test_date)
        results.append(result)

        if result['status'] == 'OK':
            print(f"[OK] Close: ${result['close']:.2f}, Volume: {result['volume']:,}")
        else:
            print(f"[X] {result.get('error', 'Unknown error')}")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    ok_count = sum(1 for r in results if r['status'] == 'OK')
    error_count = len(results) - ok_count

    print(f"Total: {len(results)}")
    print(f"Success: {ok_count} ({ok_count/len(results)*100:.1f}%)")
    print(f"Errors: {error_count}")

    if ok_count > 0:
        print(f"\nAvailable ETFs ({ok_count}):")
        for r in results:
            if r['status'] == 'OK':
                print(f"  {r['symbol']:6s} - Close: ${r['close']:8.2f}, Volume: {r['volume']:12,}")

    if error_count > 0:
        print(f"\nUnavailable ETFs ({error_count}):")
        for r in results:
            if r['status'] == 'ERROR':
                print(f"  {r['symbol']:6s} - {r.get('error', 'Unknown')}")

if __name__ == '__main__':
    main()
