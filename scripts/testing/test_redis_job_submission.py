#!/usr/bin/env python3
"""
Test Redis job submission for historical data loading.
This script tests the integration between TickStockAppV2 and TickStockPL via Redis.
"""

import json
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

import redis

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def test_redis_connection():
    """Test basic Redis connectivity."""
    try:
        client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        client.ping()
        print("[OK] Redis connection successful")
        return client
    except redis.ConnectionError as e:
        print(f"[FAIL] Redis connection failed: {e}")
        print("Make sure Redis is running on localhost:6379")
        return None

def submit_test_job(client):
    """Submit a test job to the Redis queue."""
    job_id = str(uuid.uuid4())

    job_data = {
        'job_id': job_id,
        'job_type': 'historical_load',
        'symbols': ['AAPL', 'MSFT'],
        'years': 1,
        'timespan': 'day',
        'requested_by': 'test_script',
        'timestamp': datetime.now().isoformat()
    }

    try:
        # Publish job to the data load channel
        client.publish('tickstock.jobs.data_load', json.dumps(job_data))
        print(f"[OK] Job submitted successfully: {job_id[:8]}...")

        # Store initial status
        initial_status = {
            'status': 'submitted',
            'progress': 0,
            'message': 'Test job submitted',
            'description': 'Test load for AAPL, MSFT (1 year daily)',
            'submitted_at': datetime.now().isoformat()
        }

        client.setex(
            f'job:status:{job_id}',
            3600,  # 1 hour TTL
            json.dumps(initial_status)
        )
        print("[OK] Job status stored in Redis")

        return job_id
    except Exception as e:
        print(f"[FAIL] Failed to submit job: {e}")
        return None

def check_job_status(client, job_id):
    """Check the status of a submitted job."""
    try:
        status_key = f'job:status:{job_id}'
        status_data = client.get(status_key)

        if status_data:
            status = json.loads(status_data)
            print("[OK] Job status retrieved:")
            print(f"  Status: {status.get('status')}")
            print(f"  Progress: {status.get('progress')}%")
            print(f"  Message: {status.get('message')}")
            return status
        print(f"[FAIL] No status found for job {job_id[:8]}...")
        return None
    except Exception as e:
        print(f"[FAIL] Failed to check job status: {e}")
        return None

def test_tickstockpl_heartbeat(client):
    """Check if TickStockPL is running by checking heartbeat."""
    try:
        heartbeat = client.get('tickstockpl:heartbeat')
        if heartbeat:
            print(f"[OK] TickStockPL heartbeat detected: {heartbeat}")
            return True
        print("[WARN] TickStockPL heartbeat not found (service may not be running)")
        return False
    except Exception as e:
        print(f"[FAIL] Failed to check TickStockPL heartbeat: {e}")
        return False

def monitor_job_progress(client, job_id, max_wait=30):
    """Monitor job progress for a specified time."""
    print(f"\nMonitoring job {job_id[:8]}... for {max_wait} seconds")
    print("-" * 50)

    start_time = time.time()
    last_status = None

    while time.time() - start_time < max_wait:
        status_data = client.get(f'job:status:{job_id}')

        if status_data:
            status = json.loads(status_data)
            current_status = status.get('status')
            progress = status.get('progress', 0)

            # Only print if status changed
            if last_status != current_status or (progress > 0 and progress % 10 == 0):
                print(f"[{int(time.time() - start_time):3d}s] Status: {current_status:12s} Progress: {progress:3d}% - {status.get('message', '')}")
                last_status = current_status

            # Stop if job is complete
            if current_status in ['completed', 'failed', 'cancelled']:
                print(f"\nJob finished with status: {current_status}")
                return status

        time.sleep(1)

    print(f"\nMonitoring timeout after {max_wait} seconds")
    return None

def main():
    """Run the Redis job submission test."""
    print("=" * 60)
    print("Testing Redis Job Submission Integration")
    print("=" * 60)

    # Test Redis connection
    client = test_redis_connection()
    if not client:
        return 1

    # Check TickStockPL status
    test_tickstockpl_heartbeat(client)

    # Submit a test job
    job_id = submit_test_job(client)
    if not job_id:
        return 1

    # Check immediate status
    print("\nChecking immediate job status...")
    check_job_status(client, job_id)

    # Monitor progress (optional)
    print("\n" + "=" * 60)
    choice = input("Monitor job progress? (y/n): ").lower()
    if choice == 'y':
        final_status = monitor_job_progress(client, job_id, max_wait=60)
        if final_status:
            print(f"\nFinal job status: {final_status.get('status')}")

    print("\n" + "=" * 60)
    print("Test complete!")
    print("\nNext steps:")
    print("1. Start TickStockPL data load handler if not running:")
    print("   cd ../TickStockPL && python -m src.jobs.data_load_handler")
    print("2. Access the admin UI at: http://localhost:5000/admin/historical-data")
    print("3. Submit jobs through the web interface")

    return 0

if __name__ == "__main__":
    sys.exit(main())
