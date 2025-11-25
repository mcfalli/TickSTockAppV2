"""
Diagnostic script to check admin WebSocket dashboard data flow.

This script checks:
1. Is market_service initialized?
2. Does the client have get_health_status()?
3. What data does get_health_status() return?
4. Is USE_MULTI_CONNECTION enabled?
"""

import sys
import os

# Add project root to path (go up two directories from scripts/dev_tools/)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

print("=" * 80)
print("Admin WebSocket Dashboard Diagnostic")
print("=" * 80)

# Check 1: Import market_service
print("\n[1] Checking market_service import...")
try:
    from src.app import market_service
    print(f"[OK] market_service imported: {market_service}")
    print(f"     Type: {type(market_service)}")
except Exception as e:
    print(f"[FAIL] Failed to import market_service: {e}")
    sys.exit(1)

# Check 2: Access data_adapter
print("\n[2] Checking market_service.data_adapter...")
try:
    data_adapter = market_service.data_adapter
    print(f"[OK] data_adapter exists: {data_adapter}")
    print(f"     Type: {type(data_adapter)}")
except Exception as e:
    print(f"[FAIL] Failed to access data_adapter: {e}")
    sys.exit(1)

# Check 3: Access client
print("\n[3] Checking market_service.data_adapter.client...")
try:
    client = market_service.data_adapter.client
    print(f"[OK] client exists: {client}")
    print(f"     Type: {type(client)}")
    print(f"     Class name: {client.__class__.__name__}")
except Exception as e:
    print(f"[FAIL] Failed to access client: {e}")
    sys.exit(1)

# Check 4: Does client have get_health_status?
print("\n[4] Checking for get_health_status() method...")
if hasattr(client, 'get_health_status'):
    print("[OK] get_health_status() method exists")

    # Check 5: Call get_health_status()
    print("\n[5] Calling get_health_status()...")
    try:
        health = client.get_health_status()
        print(f"[OK] get_health_status() returned data:")
        print(f"     Type: {type(health)}")

        # Pretty print the health data
        import json
        print(f"\n     Data:\n{json.dumps(health, indent=6)}")

    except Exception as e:
        print(f"[FAIL] get_health_status() raised exception: {e}")
        import traceback
        traceback.print_exc()
else:
    print("[FAIL] get_health_status() method NOT FOUND")
    print(f"       Available methods: {[m for m in dir(client) if not m.startswith('_')]}")

# Check 6: Environment variable
print("\n[6] Checking USE_MULTI_CONNECTION environment variable...")
try:
    from dotenv import load_dotenv
    load_dotenv()
    use_multi = os.getenv('USE_MULTI_CONNECTION', 'false')
    print(f"     USE_MULTI_CONNECTION = {use_multi}")

    if use_multi.lower() == 'true':
        print("[OK] Multi-connection mode ENABLED")
    else:
        print("[WARN] Multi-connection mode DISABLED (single connection mode)")
        print("       This might be why get_health_status() doesn't return expected data")
except Exception as e:
    print(f"[FAIL] Failed to check environment: {e}")

# Check 7: Redis connection
print("\n[7] Checking Redis connection...")
try:
    import redis
    redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    redis_client.ping()
    print("[OK] Redis connection successful")

    # Check for recent ticks
    pubsub = redis_client.pubsub()
    print("     Checking tickstock:market:ticks channel...")
    print("     (waiting 2 seconds for messages...)")
    pubsub.subscribe('tickstock:market:ticks')

    import time
    tick_count = 0
    start_time = time.time()
    for message in pubsub.listen():
        if time.time() - start_time > 2:
            break
        if message['type'] == 'message':
            tick_count += 1
            if tick_count == 1:
                print(f"     Sample tick: {message['data'][:100]}...")

    print(f"     Received {tick_count} ticks in 2 seconds")
    pubsub.close()

except Exception as e:
    print(f"[FAIL] Redis check failed: {e}")

print("\n" + "=" * 80)
print("Diagnostic Complete")
print("=" * 80)
