"""
Enhanced Polygon API diagnostic tool to verify API key and connection.
This tool uses the application's ConfigManager for consistent configuration handling.
"""
import argparse
import json
import sys
import time
from datetime import datetime, timedelta

import requests

# Import the application's configuration manager
from src.core.services.config_manager import ConfigManager
from src.shared.utils import format_price, retry_with_backoff

# Set up command line arguments
parser = argparse.ArgumentParser(description='Test Polygon API connectivity')
parser.add_argument('--config-file', help='Path to config file')
parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed output')
parser.add_argument('--ticker', default='AAPL', help='Ticker to use for testing (default: AAPL)')
args = parser.parse_args()

# Configure output verbosity
VERBOSE = args.verbose
test_ticker = args.ticker.upper()

# Initialize configuration
config_manager = ConfigManager()
if args.config_file:
    config_manager.load_config(args.config_file)
else:
    config_manager.load_from_env()
config = config_manager.get_config()
is_valid = config_manager.validate_config()

# Get API key from config
api_key = config.get('POLYGON_API_KEY')

print(f"\n{'=' * 50}")
print("POLYGON API CONNECTION TEST")
print(f"{'=' * 50}")
print(f"Date/Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"API Key: {'*****' + api_key[-4:] if api_key and len(api_key) > 4 else 'Not found or invalid'}")
print(f"Test Ticker: {test_ticker}")
print(f"Config Valid: {is_valid}")

if not api_key:
    print("\n❌ ERROR: No API key found in configuration")
    print("Make sure POLYGON_API_KEY is set in your .env file")
    sys.exit(1)

# Calculate dates for historical data (previous month)
today = datetime.now()
prev_month = today - timedelta(days=30)
start_date = prev_month.strftime("%Y-%m-%d")
end_date = (prev_month + timedelta(days=7)).strftime("%Y-%m-%d")

# Test endpoints with descriptions
endpoints = [
    ("/v1/marketstatus/now", "Market Status", {}),
    (f"/v2/aggs/ticker/{test_ticker}/range/1/day/{start_date}/{end_date}", f"Historical Data ({test_ticker})", {}),
    (f"/v2/last/trade/{test_ticker}", f"Last Trade ({test_ticker})", {}),
    ("/v3/reference/tickers", "Ticker List", {"active": "true", "limit": 5, "market": "stocks"})
]

# Base URL
base_url = "https://api.polygon.io"

# Track results
results = {
    "total": len(endpoints),
    "success": 0,
    "failed": 0,
    "response_times": []
}

# Test each endpoint with retry logic
for endpoint, description, extra_params in endpoints:
    print(f"\n{'-' * 50}")
    print(f"Testing: {description}")
    print(f"Endpoint: {endpoint}")

    # Add API key to params
    params = {'apiKey': api_key, **extra_params}

    # Use retry decorator
    @retry_with_backoff(max_retries=2, initial_backoff=1)
    def test_endpoint():
        start_time = time.time()
        response = requests.get(f"{base_url}{endpoint}", params=params, timeout=10)
        elapsed = time.time() - start_time
        results["response_times"].append(elapsed)

        print(f"Status code: {response.status_code}")
        print(f"Response time: {elapsed:.3f} seconds")

        if VERBOSE:
            print(f"Rate limit remaining: {response.headers.get('X-Ratelimit-Remaining', 'N/A')}")
            print(f"Rate limit reset: {response.headers.get('X-Ratelimit-Reset', 'N/A')}")

        response_data = response.json()

        if response.status_code == 200:
            results["success"] += 1
            print("✅ SUCCESS: API call completed successfully")

            # Print sample of the data
            if VERBOSE:
                if 'results' in response_data and isinstance(response_data['results'], list):
                    sample = response_data['results'][:1]  # First item only
                    print(f"Sample data: {json.dumps(sample, indent=2)}")
                elif 'results' in response_data:
                    print(f"Response: {json.dumps(response_data['results'], indent=2)}")
                else:
                    print(f"Response: {json.dumps(response_data, indent=2)}")
        else:
            results["failed"] += 1
            print(f"❌ ERROR: {response_data.get('error', 'Unknown error')}")
            if VERBOSE:
                print(f"Full response: {json.dumps(response_data, indent=2)}")

        return response

    try:
        response = test_endpoint()
    except Exception as e:
        results["failed"] += 1
        print(f"❌ EXCEPTION: {str(e)}")
        if VERBOSE and hasattr(e, '__traceback__'):
            import traceback
            traceback.print_tb(e.__traceback__)

# Print summary
print(f"\n{'-' * 50}")
print("TEST SUMMARY")
print(f"{'-' * 50}")
print(f"Total tests: {results['total']}")
print(f"Successful: {results['success']}")
print(f"Failed: {results['failed']}")

if results['response_times']:
    avg_time = sum(results['response_times']) / len(results['response_times'])
    print(f"Average response time: {avg_time:.3f} seconds")

# Check subscription status if possible
print(f"\n{'-' * 50}")
print("SUBSCRIPTION STATUS CHECK")
try:
    url = f"{base_url}/v1/reference/status"
    params = {'apiKey': api_key}
    response = requests.get(url, params=params, timeout=10)
    if response.status_code == 200:
        status_data = response.json()
        if VERBOSE:
            print(f"Full status: {json.dumps(status_data, indent=2)}")
        else:
            print(f"Status: {status_data.get('status')}")

        if 'sip' in status_data:
            print(f"Market status: {status_data['sip'].get('updated')}")
    else:
        print(f"Unable to retrieve subscription status: {response.status_code}")
except Exception as e:
    print(f"Error checking subscription status: {str(e)}")

# Check connection to main application components
print(f"\n{'-' * 50}")
print("POLYGON PROVIDER CHECK")
try:
    from src.infrastructure.data_sources.polygon.provider import PolygonDataProvider

    provider = PolygonDataProvider(config)
    print("Testing PolygonDataProvider.is_available()...")

    start_time = time.time()
    available = provider.is_available()
    elapsed = time.time() - start_time

    if available:
        print(f"✅ Provider available (took {elapsed:.3f}s)")

        # Test a real data method
        print(f"\nTesting get_ticker_price() for {test_ticker}...")
        try:
            price = provider.get_ticker_price(test_ticker)
            if price:
                print(f"✅ Current price: {format_price(price)}")
            else:
                print("❌ Could not retrieve price")
        except Exception as e:
            print(f"❌ Error getting price: {str(e)}")

    else:
        print(f"❌ Provider NOT available (took {elapsed:.3f}s)")

except ImportError:
    print("❌ Could not import PolygonDataProvider")
except Exception as e:
    print(f"❌ Error testing provider: {str(e)}")

print(f"\n{'=' * 50}")
print(f"TEST COMPLETE - {'SUCCESS' if results['failed'] == 0 else f'FAILED ({results['failed']}/{results['total']} tests failed)'}")
print(f"{'=' * 50}")

# Provide recommendations based on results
if results['failed'] > 0:
    print("\nRECOMMENDATIONS:")
    print("- Check your API key and subscription status")
    print("- Verify network connectivity")
    print("- Ensure your Polygon.io subscription includes the endpoints you're testing")
    print("- Run with --verbose flag for more detailed error information")
