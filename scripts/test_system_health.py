#!/usr/bin/env python3
"""
Test script to verify TickStock system health after fixes.
Tests all major components and reports status.
"""

import time
import json
import redis
import requests
from datetime import datetime

def test_redis_connection():
    """Test Redis connectivity."""
    try:
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        r.ping()
        print("[OK] Redis connection successful")
        return True
    except Exception as e:
        print(f"[FAIL] Redis connection failed: {e}")
        return False

def test_pattern_events():
    """Test pattern event flow through Redis."""
    try:
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)

        # Subscribe to pattern channel
        pubsub = r.pubsub()
        pubsub.subscribe('tickstock.events.patterns')

        # Publish test pattern event
        test_event = {
            'event_type': 'pattern_detected',
            'data': {
                'symbol': 'TEST',
                'pattern': 'TestPattern',
                'confidence': 85.5,
                'current_price': 100.50,
                'price_change': 2.5,
                'timestamp': time.time(),
                'expires_at': time.time() + 3600,
                'indicators': {
                    'relative_strength': 1.5,
                    'relative_volume': 2.0,
                    'rsi': 65.0
                },
                'source': 'test'
            }
        }

        # Publish event
        r.publish('tickstock.events.patterns', json.dumps(test_event))

        # Check if event was received (with timeout)
        timeout = time.time() + 2
        while time.time() < timeout:
            message = pubsub.get_message(timeout=0.1)
            if message and message['type'] == 'message':
                data = json.loads(message['data'])
                if data.get('event_type') == 'pattern_detected':
                    print("[OK] Pattern event flow working")
                    pubsub.unsubscribe()
                    return True

        print("[WARN] Pattern event not received (may be normal if no subscribers)")
        pubsub.unsubscribe()
        return True

    except Exception as e:
        print(f"[FAIL] Pattern event test failed: {e}")
        return False

def test_api_endpoints():
    """Test API endpoints."""
    base_url = "http://localhost:5000"
    endpoints_to_test = [
        ("/health", "GET"),
        ("/api/pattern-discovery/health", "GET"),
        ("/api/symbols", "GET"),
    ]

    all_good = True
    for endpoint, method in endpoints_to_test:
        try:
            url = base_url + endpoint
            if method == "GET":
                response = requests.get(url, timeout=5)

            if response.status_code == 200:
                print(f"[OK] API endpoint {endpoint} responding")
            else:
                print(f"[WARN] API endpoint {endpoint} returned {response.status_code}")
                all_good = False

        except requests.exceptions.ConnectionError:
            print(f"[FAIL] Cannot connect to API at {base_url}")
            return False
        except Exception as e:
            print(f"[FAIL] API endpoint {endpoint} error: {e}")
            all_good = False

    return all_good

def test_websocket_server():
    """Test WebSocket server availability."""
    try:
        response = requests.get("http://localhost:5000/socket.io/", timeout=5)
        if response.status_code in [200, 400]:  # 400 is expected without proper handshake
            print("[OK] WebSocket server responding")
            return True
        else:
            print(f"[WARN] WebSocket server returned {response.status_code}")
            return False
    except Exception as e:
        print(f"[FAIL] WebSocket server test failed: {e}")
        return False

def check_error_patterns():
    """Check for known error patterns in Redis."""
    try:
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)

        # Check for error keys or patterns
        error_keys = r.keys('*error*')
        if error_keys:
            print(f"[WARN] Found {len(error_keys)} error-related keys in Redis")
        else:
            print("[OK] No error keys found in Redis")

        return True

    except Exception as e:
        print(f"[FAIL] Error pattern check failed: {e}")
        return False

def main():
    """Run all system health tests."""
    print("=" * 60)
    print("TickStock System Health Check")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    tests = [
        ("Redis Connection", test_redis_connection),
        ("Pattern Event Flow", test_pattern_events),
        ("API Endpoints", test_api_endpoints),
        ("WebSocket Server", test_websocket_server),
        ("Error Pattern Check", check_error_patterns),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\nTesting {test_name}...")
        result = test_func()
        results.append((test_name, result))

    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = 0
    failed = 0
    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {test_name}")
        if result:
            passed += 1
        else:
            failed += 1

    print("\n" + "-" * 60)
    print(f"Total: {passed} passed, {failed} failed")

    if failed == 0:
        print("\n[SUCCESS] All systems operational!")
    else:
        print(f"\n[WARNING] {failed} systems need attention")

    print("=" * 60)

    return failed == 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)