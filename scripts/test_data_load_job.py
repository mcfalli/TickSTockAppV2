#!/usr/bin/env python3
"""Test TickStockPL data load integration by submitting a job"""

import redis
import json
import uuid
from datetime import datetime
import time
import sys

def submit_test_job(csv_file='test_symbols.csv', years=0.01):
    """Submit a test data load job to TickStockPL"""

    # Connect to Redis
    redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

    # Generate job ID
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    job_id = f"job_{timestamp}_{uuid.uuid4().hex[:6]}"

    # Create job data
    job_data = {
        'job_id': job_id,
        'job_type': 'csv_universe_load',
        'csv_file': csv_file,
        'universe_type': 'test',
        'years': years,  # Very small timeframe for testing
        'include_ohlcv': True,
        'requested_by': 'test_script',
        'timestamp': datetime.now().isoformat()
    }

    print(f"Submitting job: {job_id}")
    print(f"CSV file: {csv_file}")
    print(f"Years of data: {years}")
    print("-" * 50)

    # Publish job to Redis channel
    subscribers = redis_client.publish('tickstock.jobs.data_load', json.dumps(job_data))

    print(f"Job published to {subscribers} subscriber(s)")

    if subscribers == 0:
        print("WARNING: No subscribers on the channel. TickStockPL may not be running.")
        return None

    # Monitor job status
    print("\nMonitoring job status...")
    print("-" * 50)

    status_key = f"tickstock.jobs.status:{job_id}"
    last_status = None
    no_update_count = 0
    max_wait = 60  # Maximum 60 seconds to wait

    for i in range(max_wait):
        try:
            # Get job status
            status_json = redis_client.get(status_key)

            if status_json:
                status = json.loads(status_json)
                current_status = status.get('status', 'unknown')

                # Print updates only when status changes
                if current_status != last_status:
                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Status: {current_status}")

                    if 'progress' in status:
                        print(f"  Progress: {status['progress']}%")

                    if 'processed_symbols' in status and 'total_symbols' in status:
                        print(f"  Symbols: {status['processed_symbols']}/{status['total_symbols']}")

                    if 'successful_symbols' in status and status['successful_symbols']:
                        print(f"  Successful: {', '.join(status['successful_symbols'][:5])}")
                        if len(status['successful_symbols']) > 5:
                            print(f"    ... and {len(status['successful_symbols']) - 5} more")

                    if 'failed_symbols' in status and status['failed_symbols']:
                        print(f"  Failed: {', '.join(status['failed_symbols'])}")

                    if 'error_message' in status and status['error_message']:
                        print(f"  Error: {status['error_message']}")

                    last_status = current_status
                else:
                    # Print dots to show we're still monitoring
                    sys.stdout.write('.')
                    sys.stdout.flush()

                # Check if job is complete
                if current_status in ['completed', 'failed']:
                    print(f"\n\nJob {current_status}!")

                    if current_status == 'completed':
                        print(f"Successfully processed {status.get('processed_symbols', 0)} symbols")

                        # Check database for new data
                        print("\nChecking database for new records...")
                        check_database_updates()
                    else:
                        print(f"Job failed: {status.get('error_message', 'Unknown error')}")

                    return status

                no_update_count = 0
            else:
                no_update_count += 1
                sys.stdout.write('.')
                sys.stdout.flush()

                if no_update_count > 10:
                    print(f"\nNo status updates for {no_update_count} seconds. Job may not be processing.")

            time.sleep(1)

        except Exception as e:
            print(f"\nError checking status: {e}")
            break

    print(f"\n\nTimeout: Job did not complete within {max_wait} seconds")
    return None

def check_database_updates():
    """Check if new data was added to the database"""
    try:
        import psycopg2
        from datetime import datetime, timedelta

        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            database='tickstock',
            user='app_readwrite',
            password='LJI48rUEkUpe6e'
        )

        cursor = conn.cursor()

        # Check recent data in each table
        tables = ['ohlcv_daily', 'ohlcv_1min', 'ohlcv_hourly', 'ohlcv_weekly', 'ohlcv_monthly']

        for table in tables:
            try:
                # Get count of recent records
                if table == 'ohlcv_daily':
                    cursor.execute(f"""
                        SELECT COUNT(*), MAX(date)
                        FROM {table}
                        WHERE date >= CURRENT_DATE - INTERVAL '7 days'
                    """)
                else:
                    cursor.execute(f"""
                        SELECT COUNT(*), MAX(timestamp)
                        FROM {table}
                        WHERE timestamp >= NOW() - INTERVAL '7 days'
                    """)

                count, max_date = cursor.fetchone()

                if count and count > 0:
                    print(f"  {table}: {count} recent records (latest: {max_date})")
                else:
                    print(f"  {table}: No recent data")

            except Exception as e:
                print(f"  {table}: Error checking - {e}")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Could not check database: {e}")

def create_test_csv():
    """Create a small test CSV file with a few symbols"""
    import os

    # Create data directory if it doesn't exist
    data_dir = 'data'
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    # Create test CSV with just a few symbols
    csv_content = """Symbol,Name,Sector
AAPL,Apple Inc.,Technology
MSFT,Microsoft Corporation,Technology
GOOGL,Alphabet Inc.,Technology
AMZN,Amazon.com Inc.,Consumer Cyclical
TSLA,Tesla Inc.,Consumer Cyclical
"""

    csv_path = os.path.join(data_dir, 'test_symbols.csv')

    with open(csv_path, 'w') as f:
        f.write(csv_content)

    print(f"Created test CSV: {csv_path}")
    return 'test_symbols.csv'

if __name__ == "__main__":
    print("TickStockPL Data Load Integration Test")
    print("=" * 50)

    # Check for subscribers first
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)
    subs = r.pubsub_numsub('tickstock.jobs.data_load')

    print(f"Current subscribers on channel: {subs[0][1]}")

    if subs[0][1] == 0:
        print("\nERROR: No subscribers on tickstock.jobs.data_load")
        print("Make sure TickStockPL data load handler is running!")
        sys.exit(1)

    # Create test CSV file
    csv_file = create_test_csv()

    print("\nSubmitting test job with 5 tech symbols...")
    print("=" * 50)

    # Submit job with minimal data (0.01 years = ~3-4 days)
    result = submit_test_job(csv_file=csv_file, years=0.01)

    if result:
        print("\n" + "=" * 50)
        print("Test complete!")

        if result['status'] == 'completed':
            print("✓ Integration successful - TickStockPL processed the job")
        else:
            print("✗ Job failed - check TickStockPL logs for details")
    else:
        print("\n" + "=" * 50)
        print("✗ Test failed - no response from TickStockPL")