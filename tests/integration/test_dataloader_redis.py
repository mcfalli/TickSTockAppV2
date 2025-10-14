#!/usr/bin/env python3
"""
DataLoader Redis Test Script
Tests if TickStockPL DataLoader is receiving and processing jobs from Redis
"""

import json
import sys
import time
import uuid

import redis


def test_dataloader():
    """Test if DataLoader is processing jobs."""
    print("="*80)
    print("DATALOADER REDIS TEST")
    print("="*80)

    try:
        # Connect to Redis
        print("\n1. Connecting to Redis...")
        r = redis.Redis(host='127.0.0.1', port=6379, decode_responses=True)

        # Test Redis connection
        if r.ping():
            print("   ✅ Redis connection: OK")
        else:
            print("   ❌ Redis connection: FAILED")
            return False

    except Exception as e:
        print(f"   ❌ Redis connection error: {e}")
        return False

    # Check subscribers
    print("\n2. Checking Redis subscribers...")
    try:
        numsub = r.execute_command('PUBSUB', 'NUMSUB', 'tickstock.jobs.data_load')
        subscriber_count = numsub[1] if len(numsub) > 1 else 0

        if subscriber_count > 0:
            print(f"   ✅ DataLoader subscribed: {subscriber_count} subscriber(s)")
        else:
            print("   ❌ DataLoader NOT subscribed: 0 subscribers")
            print("\n   ISSUE: DataLoader service is not listening to Redis!")
            print("   FIX: Restart start_all_services.py and check for:")
            print("        '[TickStockPL DataLoader] Subscribed to tickstock.jobs.data_load'")
            return False

    except Exception as e:
        print(f"   ❌ Error checking subscribers: {e}")
        return False

    # Create and publish test job
    print("\n3. Publishing test job...")
    job_id = str(uuid.uuid4())
    test_job = {
        "job_id": job_id,
        "job_type": "csv_universe_load",
        "csv_file": "sp_500.csv",
        "universe_type": "test",
        "years": 0.003,  # 1 day only - very quick test
        "include_ohlcv": True,
        "requested_by": "test_script"
    }

    print(f"   Job ID: {job_id}")
    print("   Type: csv_universe_load")
    print("   Data: 1 day (very small test)")

    try:
        r.publish('tickstock.jobs.data_load', json.dumps(test_job))
        print("   ✅ Job published to tickstock.jobs.data_load")
    except Exception as e:
        print(f"   ❌ Failed to publish job: {e}")
        return False

    # Monitor status
    print("\n4. Monitoring job status (30 seconds max)...")
    print("   Watching: tickstock.jobs.status:{job_id}")
    print()

    status_updates = []
    for i in range(31):
        status_key = f'tickstock.jobs.status:{job_id}'
        status = r.get(status_key)

        if status:
            status_data = json.loads(status)
            status_msg = status_data.get('status', 'unknown')
            message = status_data.get('message', 'No message')
            progress = status_data.get('progress', 0)

            # Only print if status changed
            current_update = f"{status_msg}|{message}"
            if current_update not in status_updates:
                status_updates.append(current_update)
                timestamp = time.strftime('%H:%M:%S')
                print(f"   [{timestamp}] {status_msg} ({progress}%) - {message}")

            # Check if finished
            if status_msg in ['completed', 'failed', 'completed_with_errors']:
                print(f"\n   ✅ Job finished: {status_msg}")
                if status_msg == 'failed':
                    error = status_data.get('error_message', 'Unknown error')
                    print(f"   ❌ Error: {error}")
                    return False
                return True
        else:
            if i % 5 == 0:  # Print every 5 seconds
                print(f"   [{i}s] Waiting for status...", end='\r')

        time.sleep(1)

    # Timeout
    print("\n\n   ❌ TIMEOUT: Job did not complete in 30 seconds")
    print("\n   DIAGNOSIS:")
    print("   - Job was published to Redis ✅")
    print(f"   - DataLoader has {subscriber_count} subscriber(s)")
    print("   - No status updates received ❌")
    print("\n   LIKELY CAUSE: DataLoader received job but crashed/hung during processing")
    print("\n   CHECK:")
    print("   1. DataLoader console output for errors")
    print("   2. Python processes: tasklist | findstr python")
    print("   3. Restart services: python start_all_services.py")

    return False


def check_processes():
    """Check if DataLoader process is running."""
    print("\n5. Checking running processes...")
    import subprocess

    try:
        result = subprocess.run(
            ['powershell', '-Command',
             'Get-Process python | Select-Object Id, @{Name="CommandLine";Expression={(Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine}} | Format-Table -AutoSize'],
            capture_output=True,
            text=True
        )

        output = result.stdout
        lines = output.strip().split('\n')

        found_app = False
        found_dataloader = False
        found_api = False

        for line in lines:
            if 'app.py' in line or 'src\\app.py' in line:
                found_app = True
                print("   ✅ TickStockAppV2: Running")
            if 'data_load_handler' in line:
                found_dataloader = True
                print("   ✅ DataLoader: Running")
            if 'start_api_server' in line or 'api_server.py' in line:
                found_api = True
                print("   ✅ TickStockPL API: Running")

        if not found_dataloader:
            print("   ❌ DataLoader: NOT RUNNING")
            print("\n   FIX: Restart start_all_services.py")

        print("\n   Summary:")
        print(f"   - TickStockAppV2: {'✅' if found_app else '❌'}")
        print(f"   - DataLoader: {'✅' if found_dataloader else '❌'}")
        print(f"   - TickStockPL API: {'✅' if found_api else '❌'}")

    except Exception as e:
        print(f"   ⚠️  Could not check processes: {e}")


if __name__ == '__main__':
    print("\n" + "="*80)
    print("TICKSTOCKPL DATALOADER DIAGNOSTIC TEST")
    print("="*80)
    print("This script tests if the DataLoader service is receiving and processing jobs")
    print("="*80 + "\n")

    # Run test
    success = test_dataloader()

    # Check processes regardless
    check_processes()

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    if success:
        print("✅ PASS: DataLoader is working correctly!")
        print("\nThe admin historical load should work now.")
    else:
        print("❌ FAIL: DataLoader is NOT processing jobs")
        print("\nRECOMMENDED ACTIONS:")
        print("1. Stop all services (Ctrl+C on start_all_services.py)")
        print("2. Restart: python start_all_services.py")
        print("3. Look for: '[TickStockPL DataLoader] Subscribed to tickstock.jobs.data_load'")
        print("4. Run this test again")

    print("="*80 + "\n")

    sys.exit(0 if success else 1)
