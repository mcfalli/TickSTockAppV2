"""
Massive API ETF Discovery Utility

Discovers available ETFs through Massive API and validates their data availability.
Tests both REST API and WebSocket endpoints for ETF data.

Usage:
    python scripts/dev_tools/util_massive_etf_discovery.py
    python scripts/dev_tools/util_massive_etf_discovery.py --symbols SPY,QQQ,XLF
    python scripts/dev_tools/util_massive_etf_discovery.py --search --verbose
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

import requests

from src.core.services.config_manager import ConfigManager

# Common ETFs to check
COMMON_ETFS = [
    'SPY', 'QQQ', 'DIA', 'IWM',  # Market indices
    'XLF', 'XLE', 'XLK', 'XLV', 'XLI', 'XLB', 'XLRE', 'XLU', 'XLY', 'XLP',  # SPDR Sectors
    'VTI', 'VOO', 'VEA', 'VWO',  # Vanguard broad
    'GLD', 'SLV', 'USO',  # Commodities
    'TLT', 'AGG', 'LQD', 'HYG',  # Bonds
    'ARKK', 'SOXX', 'XBI', 'XRT'  # Specialized
]

def get_api_key():
    """Get Massive API key from configuration"""
    config_manager = ConfigManager()
    config_manager.load_from_env()
    config = config_manager.get_config()
    return config.get('MASSIVE_API_KEY')

def search_etfs(api_key, verbose=False):
    """
    Search for all available ETFs via Massive API

    Args:
        api_key: Massive API key
        verbose: Show detailed output

    Returns:
        List of ETF ticker symbols
    """
    print("\n" + "=" * 60)
    print("SEARCHING FOR ETFS VIA MASSIVE API")
    print("=" * 60)

    base_url = "https://api.massive.com"
    endpoint = "/v3/reference/tickers"

    all_etfs = []
    next_url = None
    page = 1

    while True:
        print(f"\nFetching page {page}...")

        if next_url:
            # Use next_url from pagination
            response = requests.get(next_url, timeout=30)
        else:
            # Initial request
            params = {
                'apiKey': api_key,
                'type': 'ETF',
                'market': 'stocks',
                'active': 'true',
                'limit': 1000,
                'sort': 'ticker'
            }
            response = requests.get(f"{base_url}{endpoint}", params=params, timeout=30)

        if response.status_code != 200:
            print(f"❌ Error: HTTP {response.status_code}")
            print(f"Response: {response.text}")
            break

        data = response.json()

        if 'results' in data:
            etfs_this_page = data['results']
            all_etfs.extend(etfs_this_page)
            print(f"✅ Found {len(etfs_this_page)} ETFs on page {page}")

            if verbose:
                for etf in etfs_this_page[:5]:  # Show first 5
                    print(f"   - {etf.get('ticker')}: {etf.get('name', 'N/A')}")
                if len(etfs_this_page) > 5:
                    print(f"   ... and {len(etfs_this_page) - 5} more")

        # Check for next page
        if 'next_url' in data and data['next_url']:
            next_url = data['next_url']
            page += 1
            time.sleep(0.2)  # Rate limiting
        else:
            break

    print(f"\n✅ Total ETFs discovered: {len(all_etfs)}")
    return [etf.get('ticker') for etf in all_etfs]

def test_etf_data_availability(api_key, symbols, verbose=False):
    """
    Test data availability for specific ETF symbols

    Args:
        api_key: Massive API key
        symbols: List of ticker symbols to test
        verbose: Show detailed output

    Returns:
        Dictionary with test results per symbol
    """
    print("\n" + "=" * 60)
    print(f"TESTING DATA AVAILABILITY FOR {len(symbols)} ETFS")
    print("=" * 60)

    base_url = "https://api.massive.com"
    results = {}

    # Test dates (previous week)
    end_date = datetime.now() - timedelta(days=1)
    start_date = end_date - timedelta(days=7)

    for symbol in symbols:
        print(f"\n{'-' * 60}")
        print(f"Testing: {symbol}")

        result = {
            'symbol': symbol,
            'ticker_info': None,
            'historical_data': None,
            'snapshot': None,
            'aggregates': None,
            'errors': []
        }

        # 1. Get ticker info
        try:
            endpoint = f"/v3/reference/tickers/{symbol}"
            params = {'apiKey': api_key}
            response = requests.get(f"{base_url}{endpoint}", params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if 'results' in data:
                    result['ticker_info'] = {
                        'name': data['results'].get('name'),
                        'market': data['results'].get('market'),
                        'type': data['results'].get('type'),
                        'active': data['results'].get('active'),
                        'currency': data['results'].get('currency_name')
                    }
                    print(f"   ✅ Ticker Info: {result['ticker_info']['name']}")
                else:
                    print(f"   ❌ Ticker Info: No results")
                    result['errors'].append('No ticker info')
            else:
                print(f"   ❌ Ticker Info: HTTP {response.status_code}")
                result['errors'].append(f'Ticker info HTTP {response.status_code}')
        except Exception as e:
            print(f"   ❌ Ticker Info: {str(e)}")
            result['errors'].append(f'Ticker info error: {str(e)}')

        # 2. Get historical aggregates (daily bars)
        try:
            endpoint = f"/v2/aggs/ticker/{symbol}/range/1/day/{start_date.strftime('%Y-%m-%d')}/{end_date.strftime('%Y-%m-%d')}"
            params = {'apiKey': api_key, 'adjusted': 'true'}
            response = requests.get(f"{base_url}{endpoint}", params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get('results') and len(data['results']) > 0:
                    result['historical_data'] = {
                        'bar_count': len(data['results']),
                        'latest_close': data['results'][-1].get('c'),
                        'latest_volume': data['results'][-1].get('v')
                    }
                    print(f"   ✅ Historical Data: {result['historical_data']['bar_count']} bars")
                else:
                    print(f"   ❌ Historical Data: No bars")
                    result['errors'].append('No historical bars')
            else:
                print(f"   ❌ Historical Data: HTTP {response.status_code}")
                result['errors'].append(f'Historical HTTP {response.status_code}')
        except Exception as e:
            print(f"   ❌ Historical Data: {str(e)}")
            result['errors'].append(f'Historical error: {str(e)}')

        # 3. Get snapshot (current data)
        try:
            endpoint = f"/v2/snapshot/locale/us/markets/stocks/tickers/{symbol}"
            params = {'apiKey': api_key}
            response = requests.get(f"{base_url}{endpoint}", params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get('ticker'):
                    ticker_data = data['ticker']
                    result['snapshot'] = {
                        'last_price': ticker_data.get('lastTrade', {}).get('p'),
                        'day_high': ticker_data.get('day', {}).get('h'),
                        'day_low': ticker_data.get('day', {}).get('l'),
                        'volume': ticker_data.get('day', {}).get('v')
                    }
                    print(f"   ✅ Snapshot: Last=${result['snapshot']['last_price']}")
                else:
                    print(f"   ❌ Snapshot: No ticker data")
                    result['errors'].append('No snapshot data')
            else:
                print(f"   ❌ Snapshot: HTTP {response.status_code}")
                result['errors'].append(f'Snapshot HTTP {response.status_code}')
        except Exception as e:
            print(f"   ❌ Snapshot: {str(e)}")
            result['errors'].append(f'Snapshot error: {str(e)}')

        # 4. Get minute aggregates (for WebSocket validation)
        try:
            minute_start = end_date - timedelta(hours=1)
            endpoint = f"/v2/aggs/ticker/{symbol}/range/1/minute/{minute_start.strftime('%Y-%m-%d')}/{end_date.strftime('%Y-%m-%d')}"
            params = {'apiKey': api_key, 'adjusted': 'true', 'limit': 10}
            response = requests.get(f"{base_url}{endpoint}", params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get('results') and len(data['results']) > 0:
                    result['aggregates'] = {
                        'minute_bars': len(data['results']),
                        'websocket_compatible': True
                    }
                    print(f"   ✅ Minute Aggregates: {result['aggregates']['minute_bars']} bars (WebSocket ready)")
                else:
                    print(f"   ⚠️  Minute Aggregates: No recent bars")
                    result['aggregates'] = {'websocket_compatible': False}
            else:
                print(f"   ❌ Minute Aggregates: HTTP {response.status_code}")
                result['errors'].append(f'Minute aggs HTTP {response.status_code}')
        except Exception as e:
            print(f"   ❌ Minute Aggregates: {str(e)}")
            result['errors'].append(f'Minute aggs error: {str(e)}')

        results[symbol] = result
        time.sleep(0.15)  # Rate limiting between symbols

    return results

def print_summary(results):
    """Print summary of ETF data availability"""
    print("\n" + "=" * 60)
    print("SUMMARY - ETF DATA AVAILABILITY")
    print("=" * 60)

    total = len(results)
    with_ticker_info = sum(1 for r in results.values() if r['ticker_info'])
    with_historical = sum(1 for r in results.values() if r['historical_data'])
    with_snapshot = sum(1 for r in results.values() if r['snapshot'])
    with_aggregates = sum(1 for r in results.values() if r['aggregates'] and r['aggregates'].get('websocket_compatible'))

    print(f"\nTotal ETFs Tested: {total}")
    print(f"  ✅ Ticker Info Available:     {with_ticker_info:3d} ({with_ticker_info/total*100:.1f}%)")
    print(f"  ✅ Historical Data Available: {with_historical:3d} ({with_historical/total*100:.1f}%)")
    print(f"  ✅ Snapshot Data Available:   {with_snapshot:3d} ({with_snapshot/total*100:.1f}%)")
    print(f"  ✅ WebSocket Compatible:      {with_aggregates:3d} ({with_aggregates/total*100:.1f}%)")

    # Fully available ETFs
    fully_available = [
        symbol for symbol, data in results.items()
        if data['ticker_info'] and data['historical_data'] and
           data['snapshot'] and data['aggregates'] and
           data['aggregates'].get('websocket_compatible')
    ]

    print(f"\n✅ Fully Available ETFs ({len(fully_available)}):")
    for symbol in fully_available:
        info = results[symbol]['ticker_info']
        print(f"   {symbol:6s} - {info['name']}")

    # Problematic ETFs
    problematic = [
        (symbol, data) for symbol, data in results.items()
        if len(data['errors']) > 0
    ]

    if problematic:
        print(f"\n⚠️  ETFs with Issues ({len(problematic)}):")
        for symbol, data in problematic:
            print(f"   {symbol:6s} - {', '.join(data['errors'])}")

def main():
    parser = argparse.ArgumentParser(
        description='Discover and test ETF data availability via Massive API'
    )
    parser.add_argument(
        '--symbols',
        help='Comma-separated list of ETF symbols to test (default: common ETFs)'
    )
    parser.add_argument(
        '--search',
        action='store_true',
        help='Search for all available ETFs via API'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed output'
    )

    args = parser.parse_args()

    # Get API key
    api_key = get_api_key()
    if not api_key:
        print("❌ ERROR: MASSIVE_API_KEY not found in configuration")
        print("Set MASSIVE_API_KEY in your .env file")
        sys.exit(1)

    print(f"API Key: {'*' * 5}{api_key[-4:]}")

    # Determine which symbols to test
    if args.search:
        # Search for all ETFs
        discovered_etfs = search_etfs(api_key, args.verbose)

        # Test a sample
        print(f"\nTesting sample of {min(10, len(discovered_etfs))} ETFs...")
        symbols = discovered_etfs[:10]
    elif args.symbols:
        # User-specified symbols
        symbols = [s.strip().upper() for s in args.symbols.split(',')]
    else:
        # Default common ETFs
        symbols = COMMON_ETFS

    # Test data availability
    results = test_etf_data_availability(api_key, symbols, args.verbose)

    # Print summary
    print_summary(results)

    # Save results to file
    output_file = 'logs/massive_etf_discovery.json'
    try:
        import os
        os.makedirs('logs', exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n💾 Results saved to: {output_file}")
    except Exception as e:
        print(f"\n⚠️  Could not save results: {e}")

if __name__ == '__main__':
    main()
