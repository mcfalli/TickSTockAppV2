"""
Manual test script for Sprint 72 Database Integration.

Tests OHLCVDataService and REST API endpoints with real database.
"""

import sys
import time
from datetime import datetime

import pandas as pd
import requests

# Add src to path
sys.path.insert(0, 'C:/Users/McDude/TickStockAppV2')

from src.analysis.data.ohlcv_data_service import OHLCVDataService


def test_ohlcv_service():
    """Test OHLCVDataService with real database."""
    print("\n" + "="*70)
    print("TEST 1: OHLCVDataService - Direct Database Access")
    print("="*70)

    try:
        service = OHLCVDataService()
        print("✅ OHLCVDataService initialized")

        # Test health check
        print("\n📊 Health Check:")
        health = service.health_check()
        print(f"   Status: {health['status']}")
        print(f"   Symbols Available: {health.get('symbols_available', 'N/A')}")

        # Test get_ohlcv_data for a common symbol
        test_symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA']

        for symbol in test_symbols:
            print(f"\n📈 Testing Symbol: {symbol}")

            start_time = time.time()
            df = service.get_ohlcv_data(symbol, timeframe='daily', limit=200)
            query_time = (time.time() - start_time) * 1000

            if df.empty:
                print(f"   ⚠️  No data found")
                continue

            print(f"   ✅ Data fetched: {len(df)} bars")
            print(f"   ⏱️  Query time: {query_time:.2f}ms")
            print(f"   📅 Date range: {df.index[0]} to {df.index[-1]}")
            print(f"   💰 Latest close: ${df['close'].iloc[-1]:.2f}")
            print(f"   📊 Columns: {list(df.columns)}")

            # Performance check
            if query_time > 50:
                print(f"   ⚠️  WARNING: Query time exceeds 50ms target")
            else:
                print(f"   ✅ Performance: Within <50ms target")

            # Test latest bar
            latest = service.get_latest_ohlcv(symbol, 'daily')
            if latest is not None:
                print(f"   📌 Latest bar: O:{latest['open']:.2f} H:{latest['high']:.2f} L:{latest['low']:.2f} C:{latest['close']:.2f}")

            break  # Just test first available symbol

        # Test universe batch query
        print(f"\n📦 Testing Universe Batch Query:")
        batch_symbols = ['AAPL', 'MSFT', 'GOOGL']

        start_time = time.time()
        universe_data = service.get_universe_ohlcv_data(batch_symbols, 'daily', limit=200)
        batch_time = (time.time() - start_time) * 1000

        print(f"   ✅ Batch query completed: {len(universe_data)} symbols")
        print(f"   ⏱️  Query time: {batch_time:.2f}ms")

        for sym, data in universe_data.items():
            if not data.empty:
                print(f"   📊 {sym}: {len(data)} bars")

        if batch_time > 500:
            print(f"   ⚠️  WARNING: Batch query exceeds 500ms target")
        else:
            print(f"   ✅ Performance: Within <500ms target")

        return True

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_endpoints(base_url='http://localhost:5000'):
    """Test REST API endpoints with real database."""
    print("\n" + "="*70)
    print("TEST 2: REST API Endpoints - HTTP Requests")
    print("="*70)

    try:
        # Test 1: Single symbol analysis
        print("\n📡 POST /api/analysis/symbol (AAPL)")

        payload = {
            'symbol': 'AAPL',
            'timeframe': 'daily',
            'indicators': ['sma', 'rsi'],
            'patterns': ['doji', 'hammer'],
            'calculate_all': False
        }

        start_time = time.time()
        response = requests.post(
            f'{base_url}/api/analysis/symbol',
            json=payload,
            timeout=10
        )
        api_time = (time.time() - start_time) * 1000

        print(f"   Status Code: {response.status_code}")
        print(f"   ⏱️  Response time: {api_time:.2f}ms")

        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Success!")
            print(f"   📊 Symbol: {data['symbol']}")
            print(f"   📈 Indicators: {list(data['indicators'].keys())}")
            print(f"   🎯 Patterns: {list(data['patterns'].keys())}")
            print(f"   ⏱️  Calculation time: {data['metadata']['calculation_time_ms']:.2f}ms")
            print(f"   📊 Data points: {data['metadata']['data_points']}")

            # Show sample indicator values
            if 'sma' in data['indicators']:
                sma_value = data['indicators']['sma'].get('value')
                print(f"   💹 SMA: {sma_value}")

            if 'rsi' in data['indicators']:
                rsi_value = data['indicators']['rsi'].get('value')
                print(f"   💹 RSI: {rsi_value}")

            # Show pattern detections
            for pattern_name, pattern_data in data['patterns'].items():
                detected = pattern_data.get('detected', False)
                confidence = pattern_data.get('confidence', 0)
                if detected:
                    print(f"   🎯 {pattern_name.upper()}: Detected (confidence: {confidence:.2f})")

            if api_time > 100:
                print(f"   ⚠️  WARNING: API response exceeds 100ms target")
            else:
                print(f"   ✅ Performance: Within <100ms target")
        else:
            print(f"   ❌ ERROR: {response.text}")
            return False

        # Test 2: Invalid symbol (should return 404)
        print("\n📡 POST /api/analysis/symbol (INVALID_SYM - expect 404)")

        payload = {
            'symbol': 'INVALID_SYM',
            'timeframe': 'daily',
            'indicators': ['sma']
        }

        response = requests.post(
            f'{base_url}/api/analysis/symbol',
            json=payload,
            timeout=10
        )

        print(f"   Status Code: {response.status_code}")
        if response.status_code == 404:
            print(f"   ✅ Correctly returned 404 for invalid symbol")
            error_data = response.json()
            print(f"   📝 Error: {error_data.get('error')}")
            print(f"   💬 Message: {error_data.get('message')}")
        else:
            print(f"   ⚠️  Expected 404, got {response.status_code}")

        # Test 3: Health check
        print("\n📡 GET /api/analysis/health")

        response = requests.get(f'{base_url}/api/analysis/health', timeout=5)
        print(f"   Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Status: {data['status']}")
            print(f"   🔧 Service: {data['service']}")

        # Test 4: Available indicators
        print("\n📡 GET /api/indicators/available")

        response = requests.get(f'{base_url}/api/indicators/available', timeout=5)
        print(f"   Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Total indicators: {data['total_count']}")
            print(f"   📊 Categories: {', '.join(data['categories'])}")
            for category, indicators in data['indicators'].items():
                print(f"      • {category}: {', '.join(indicators)}")

        return True

    except requests.exceptions.ConnectionError:
        print(f"\n❌ ERROR: Could not connect to {base_url}")
        print("   Make sure Flask app is running: python src/app.py")
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all manual tests."""
    print("\n" + "="*70)
    print("Sprint 72: Database Integration - Manual Testing")
    print("="*70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Test 1: Direct database service
    service_ok = test_ohlcv_service()

    # Test 2: REST API endpoints (requires Flask app running)
    print("\n")
    user_input = input("Test REST API endpoints? (requires Flask app running) [y/N]: ")
    if user_input.lower() == 'y':
        api_ok = test_api_endpoints()
    else:
        print("\nℹ️  Skipping API tests")
        print("   To test API: python src/app.py (in another terminal)")
        api_ok = None

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"OHLCVDataService: {'✅ PASS' if service_ok else '❌ FAIL'}")
    if api_ok is not None:
        print(f"REST API Endpoints: {'✅ PASS' if api_ok else '❌ FAIL'}")
    else:
        print(f"REST API Endpoints: ⏭️  SKIPPED")

    if service_ok and (api_ok is None or api_ok):
        print("\n🎉 Sprint 72 Database Integration: WORKING!")
    else:
        print("\n⚠️  Some tests failed - review errors above")


if __name__ == '__main__':
    main()
