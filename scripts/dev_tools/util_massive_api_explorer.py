"""
Massive API Explorer Utility

Interactive tool to explore Massive API endpoints and discover available data.
Focus on ETF discovery and validation.

Usage:
    python scripts/dev_tools/util_massive_api_explorer.py --list-etfs
    python scripts/dev_tools/util_massive_api_explorer.py --ticker-details SPY
    python scripts/dev_tools/util_massive_api_explorer.py --market-snapshot
    python scripts/dev_tools/util_massive_api_explorer.py --test-endpoints
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

class MassiveAPIExplorer:
    """Explore Massive API endpoints and capabilities"""

    def __init__(self, api_key, verbose=False):
        """
        Initialize API explorer

        Args:
            api_key: Massive API key
            verbose: Show detailed output
        """
        self.api_key = api_key
        self.verbose = verbose
        self.base_url = "https://api.massive.com"
        self.session = requests.Session()

    def _make_request(self, endpoint, params=None):
        """
        Make API request with error handling

        Args:
            endpoint: API endpoint path
            params: Query parameters (dict)

        Returns:
            Response JSON or None on error
        """
        params = params or {}
        params['apiKey'] = self.api_key

        try:
            url = f"{self.base_url}{endpoint}"
            if self.verbose:
                print(f"  🔍 GET {endpoint}")

            response = self.session.get(url, params=params, timeout=30)

            if self.verbose:
                print(f"  📡 Status: {response.status_code}")
                print(f"  ⏱️  Time: {response.elapsed.total_seconds():.3f}s")

            if response.status_code == 200:
                return response.json()
            else:
                print(f"  ❌ HTTP {response.status_code}: {response.text[:200]}")
                return None

        except Exception as e:
            print(f"  ❌ Request error: {e}")
            return None

    def list_all_etfs(self, limit=None):
        """
        List all available ETFs via Massive API

        Args:
            limit: Maximum number of ETFs to return (None = all)

        Returns:
            List of ETF dictionaries
        """
        print("\n" + "=" * 70)
        print("LISTING ALL ETFS")
        print("=" * 70)

        endpoint = "/v3/reference/tickers"
        all_etfs = []
        next_url = None
        page = 1

        while True:
            print(f"\nFetching page {page}...")

            if next_url:
                response = self.session.get(next_url, timeout=30)
                data = response.json() if response.status_code == 200 else None
            else:
                params = {
                    'type': 'ETF',
                    'market': 'stocks',
                    'active': 'true',
                    'limit': 1000,
                    'sort': 'ticker'
                }
                data = self._make_request(endpoint, params)

            if not data or 'results' not in data:
                break

            etfs = data['results']
            all_etfs.extend(etfs)

            print(f"  ✅ Found {len(etfs)} ETFs (total: {len(all_etfs)})")

            # Show first few from this page
            for i, etf in enumerate(etfs[:3]):
                print(f"     {etf['ticker']:6s} - {etf.get('name', 'N/A')[:50]}")

            # Check if we've hit the limit
            if limit and len(all_etfs) >= limit:
                all_etfs = all_etfs[:limit]
                break

            # Check for next page
            if 'next_url' in data and data['next_url']:
                next_url = data['next_url']
                page += 1
                time.sleep(0.2)  # Rate limiting
            else:
                break

        print(f"\n✅ Total ETFs found: {len(all_etfs)}")
        return all_etfs

    def get_ticker_details(self, symbol):
        """
        Get detailed information about a ticker

        Args:
            symbol: Ticker symbol

        Returns:
            Ticker details dictionary
        """
        print("\n" + "=" * 70)
        print(f"TICKER DETAILS: {symbol}")
        print("=" * 70)

        endpoint = f"/v3/reference/tickers/{symbol}"
        data = self._make_request(endpoint)

        if data and 'results' in data:
            ticker = data['results']

            print(f"\nBasic Info:")
            print(f"  Symbol:           {ticker.get('ticker')}")
            print(f"  Name:             {ticker.get('name')}")
            print(f"  Type:             {ticker.get('type')}")
            print(f"  Market:           {ticker.get('market')}")
            print(f"  Primary Exchange: {ticker.get('primary_exchange')}")
            print(f"  Currency:         {ticker.get('currency_name')}")
            print(f"  Active:           {ticker.get('active')}")

            if 'description' in ticker:
                print(f"\nDescription:")
                print(f"  {ticker['description'][:300]}...")

            if 'homepage_url' in ticker:
                print(f"\nHomepage: {ticker['homepage_url']}")

            if 'market_cap' in ticker:
                print(f"\nMarket Cap: ${ticker['market_cap']:,.0f}")

            if 'share_class_shares_outstanding' in ticker:
                print(f"Shares Outstanding: {ticker['share_class_shares_outstanding']:,.0f}")

            return ticker

        return None

    def get_market_snapshot(self, symbols):
        """
        Get market snapshot for multiple symbols

        Args:
            symbols: List of ticker symbols

        Returns:
            Dictionary of symbol -> snapshot data
        """
        print("\n" + "=" * 70)
        print(f"MARKET SNAPSHOT FOR {len(symbols)} SYMBOLS")
        print("=" * 70)

        results = {}

        for symbol in symbols:
            endpoint = f"/v2/snapshot/locale/us/markets/stocks/tickers/{symbol}"
            data = self._make_request(endpoint)

            if data and 'ticker' in data:
                ticker_data = data['ticker']

                snapshot = {
                    'symbol': symbol,
                    'last_trade': ticker_data.get('lastTrade', {}),
                    'day': ticker_data.get('day', {}),
                    'prev_day': ticker_data.get('prevDay', {}),
                    'min': ticker_data.get('min', {}),
                    'updated': ticker_data.get('updated')
                }

                results[symbol] = snapshot

                # Print summary
                last_price = snapshot['last_trade'].get('p', 'N/A')
                day_change = snapshot['day'].get('c', 0)
                day_volume = snapshot['day'].get('v', 0)

                print(f"\n{symbol}:")
                print(f"  Last Price:   ${last_price}")
                print(f"  Day Change:   ${day_change:+.2f}" if isinstance(day_change, (int, float)) else f"  Day Change:   {day_change}")
                print(f"  Day Volume:   {day_volume:,}" if isinstance(day_volume, (int, float)) else f"  Day Volume:   {day_volume}")

            else:
                print(f"\n{symbol}: ❌ No data available")

            time.sleep(0.1)  # Rate limiting

        return results

    def test_all_endpoints(self, test_symbol='SPY'):
        """
        Test various API endpoints with a sample symbol

        Args:
            test_symbol: Symbol to use for testing
        """
        print("\n" + "=" * 70)
        print(f"TESTING API ENDPOINTS WITH {test_symbol}")
        print("=" * 70)

        # Calculate test dates
        end_date = datetime.now() - timedelta(days=1)
        start_date = end_date - timedelta(days=7)

        endpoints = [
            {
                'name': 'Market Status',
                'endpoint': '/v1/marketstatus/now',
                'params': {}
            },
            {
                'name': 'Ticker Details',
                'endpoint': f'/v3/reference/tickers/{test_symbol}',
                'params': {}
            },
            {
                'name': 'Daily Aggregates',
                'endpoint': f'/v2/aggs/ticker/{test_symbol}/range/1/day/{start_date.strftime("%Y-%m-%d")}/{end_date.strftime("%Y-%m-%d")}',
                'params': {'adjusted': 'true'}
            },
            {
                'name': 'Minute Aggregates',
                'endpoint': f'/v2/aggs/ticker/{test_symbol}/range/1/minute/{end_date.strftime("%Y-%m-%d")}/{end_date.strftime("%Y-%m-%d")}',
                'params': {'adjusted': 'true', 'limit': 10}
            },
            {
                'name': 'Snapshot',
                'endpoint': f'/v2/snapshot/locale/us/markets/stocks/tickers/{test_symbol}',
                'params': {}
            },
            {
                'name': 'Last Trade',
                'endpoint': f'/v2/last/trade/{test_symbol}',
                'params': {}
            },
            {
                'name': 'Previous Close',
                'endpoint': f'/v2/aggs/ticker/{test_symbol}/prev',
                'params': {'adjusted': 'true'}
            },
            {
                'name': 'Ticker Types',
                'endpoint': '/v3/reference/tickers/types',
                'params': {}
            }
        ]

        results = []

        for test in endpoints:
            print(f"\n{'─' * 70}")
            print(f"Testing: {test['name']}")
            print(f"Endpoint: {test['endpoint']}")

            start_time = time.time()
            data = self._make_request(test['endpoint'], test['params'])
            elapsed = time.time() - start_time

            success = data is not None
            status = "✅ SUCCESS" if success else "❌ FAILED"

            print(f"Result: {status} ({elapsed:.3f}s)")

            if success and self.verbose and data:
                # Show sample data
                if 'results' in data:
                    if isinstance(data['results'], list):
                        print(f"Results count: {len(data['results'])}")
                        if len(data['results']) > 0:
                            print(f"Sample: {json.dumps(data['results'][0], indent=2)[:300]}...")
                    else:
                        print(f"Results: {json.dumps(data['results'], indent=2)[:300]}...")

            results.append({
                'name': test['name'],
                'endpoint': test['endpoint'],
                'success': success,
                'elapsed': elapsed
            })

        # Print summary
        print(f"\n{'═' * 70}")
        print("TEST SUMMARY")
        print(f"{'═' * 70}")

        total = len(results)
        successful = sum(1 for r in results if r['success'])
        failed = total - successful

        print(f"\nTotal Tests:    {total}")
        print(f"Successful:     {successful} ({successful/total*100:.1f}%)")
        print(f"Failed:         {failed}")

        if successful > 0:
            avg_time = sum(r['elapsed'] for r in results if r['success']) / successful
            print(f"Avg Time:       {avg_time:.3f}s")

        return results

def main():
    parser = argparse.ArgumentParser(
        description='Explore Massive API endpoints and discover available data'
    )

    # Mutually exclusive operation modes
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        '--list-etfs',
        action='store_true',
        help='List all available ETFs'
    )
    mode.add_argument(
        '--ticker-details',
        metavar='SYMBOL',
        help='Get detailed info for a specific ticker'
    )
    mode.add_argument(
        '--market-snapshot',
        action='store_true',
        help='Get market snapshot for common ETFs'
    )
    mode.add_argument(
        '--test-endpoints',
        action='store_true',
        help='Test various API endpoints'
    )

    # Additional options
    parser.add_argument(
        '--symbols',
        help='Comma-separated symbols for snapshot mode'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of results'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed output'
    )
    parser.add_argument(
        '--save',
        help='Save results to JSON file'
    )

    args = parser.parse_args()

    # Get API key
    config_manager = ConfigManager()
    config_manager.load_from_env()
    config = config_manager.get_config()
    api_key = config.get('MASSIVE_API_KEY')

    if not api_key:
        print("❌ ERROR: MASSIVE_API_KEY not found in configuration")
        print("Set MASSIVE_API_KEY in your .env file")
        sys.exit(1)

    print(f"API Key: {'*' * 5}{api_key[-4:]}")

    # Create explorer
    explorer = MassiveAPIExplorer(api_key, verbose=args.verbose)

    # Execute operation
    results = None

    if args.list_etfs:
        results = explorer.list_all_etfs(limit=args.limit)

    elif args.ticker_details:
        results = explorer.get_ticker_details(args.ticker_details.upper())

    elif args.market_snapshot:
        if args.symbols:
            symbols = [s.strip().upper() for s in args.symbols.split(',')]
        else:
            # Default common ETFs
            symbols = ['SPY', 'QQQ', 'DIA', 'IWM', 'XLF', 'XLE', 'XLK', 'XLV', 'GLD', 'TLT']

        results = explorer.get_market_snapshot(symbols)

    elif args.test_endpoints:
        test_symbol = args.symbols.split(',')[0].upper() if args.symbols else 'SPY'
        results = explorer.test_all_endpoints(test_symbol)

    else:
        # Default: list ETFs
        print("\nNo operation specified, defaulting to --list-etfs")
        print("Use --help to see all options\n")
        results = explorer.list_all_etfs(limit=args.limit or 50)

    # Save results if requested
    if args.save and results:
        try:
            with open(args.save, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"\n💾 Results saved to: {args.save}")
        except Exception as e:
            print(f"\n⚠️  Could not save results: {e}")

if __name__ == '__main__':
    main()
