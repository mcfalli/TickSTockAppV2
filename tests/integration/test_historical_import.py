#!/usr/bin/env python3
"""
Test script for TickStockPL historical data import integration
"""

import json
import time
import uuid

import redis

# Connect to Redis
r = redis.Redis(host='127.0.0.1', port=6379, decode_responses=True)

print("="*60)
print("TICKSTOCK HISTORICAL IMPORT TEST")
print("="*60)

# Test 1: Verify Redis connection
print("\n1. Testing Redis connection...")
try:
    pong = r.ping()
    print(f"   ✅ Redis connected: PONG={pong}")
except Exception as e:
    print(f"   ❌ Redis connection failed: {e}")
    exit(1)

# Test 2: Submit a small test job (1 day of data)
print("\n2. Submitting test job to TickStockPL...")
job_id = str(uuid.uuid4())
job = {
    "job_id": job_id,
    "job_type": "csv_universe_load",
    "csv_file": "sp_500.csv",
    "universe_type": "sp_500",
    "years": 0.003,  # 1 day of data for testing
    "include_ohlcv": True,
    "requested_by": "test_script"
}

print(f"   Job ID: {job_id}")
print(f"   Job Data: {json.dumps(job, indent=2)}")

try:
    # Publish to the channel TickStockPL is listening on
    result = r.publish('tickstock.jobs.data_load', json.dumps(job))
    print("   ✅ Job published to tickstock.jobs.data_load")
    print(f"   Subscribers listening: {result}")

    if result == 0:
        print("   ⚠️  WARNING: No subscribers listening on tickstock.jobs.data_load!")
        print("   Make sure TickStockPL data_load_handler.py is running.")
except Exception as e:
    print(f"   ❌ Failed to publish job: {e}")
    exit(1)

# Test 3: Monitor job status
print("\n3. Monitoring job status...")
print("   Checking for updates every 2 seconds (max 30 seconds)...")

for i in range(15):  # Check for 30 seconds
    time.sleep(2)

    status_key = f'tickstock.jobs.status:{job_id}'
    status_data = r.get(status_key)

    if status_data:
        status = json.loads(status_data)
        print(f"\n   [{i*2}s] Status Update:")
        print(f"      Status: {status.get('status', 'unknown')}")
        print(f"      Progress: {status.get('progress', 0)}%")
        print(f"      Message: {status.get('message', 'N/A')}")

        if status.get('status') in ['completed', 'failed', 'error']:
            print(f"\n   ✅ Job finished with status: {status.get('status')}")
            if status.get('status') == 'completed':
                print(f"   Symbols loaded: {status.get('symbols_loaded', 0)}")
                print(f"   OHLCV records: {status.get('ohlcv_records_loaded', 0)}")
            break
    else:
        print(f"   [{i*2}s] No status update yet (waiting for TickStockPL)...")
else:
    print("\n   ⚠️  Timeout: No status update received after 30 seconds")
    print("   Check if TickStockPL data_load_handler is running:")
    print("   cd C:\\Users\\McDude\\TickStockPL")
    print("   python -m src.jobs.data_load_handler")

# Test 4: Summary
print("\n" + "="*60)
print("TEST COMPLETE")
print("="*60)
print("\nDebugging Steps if Job Failed:")
print("1. Check TickStockPL is running:")
print("   cd C:\\Users\\McDude\\TickStockPL")
print("   python -m src.jobs.data_load_handler")
print("\n2. Monitor Redis channel:")
print("   redis-cli")
print("   > SUBSCRIBE tickstock.jobs.data_load")
print("\n3. Check CSV file exists:")
print("   C:\\Users\\McDude\\TickStockAppV2\\data\\sp_500.csv")
print("\n4. View job status manually:")
print(f"   redis-cli GET tickstock.jobs.status:{job_id}")
print("="*60)
