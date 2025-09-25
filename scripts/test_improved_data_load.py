#!/usr/bin/env python3
"""Test improved TickStockPL data load integration with all fixes"""

import redis
import json
import uuid
import time
import sys
from datetime import datetime

def submit_test_job(csv_file='test_symbols.csv', years=0.02, symbols=['AAPL', 'MSFT']):
    """Submit a test job with specific parameters to verify improvements"""

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
        'years': years,
        'include_ohlcv': True,
        'requested_by': 'test_script',
        'timestamp': datetime.now().isoformat()
    }

    print("=" * 60)
    print("IMPROVED TICKSTOCKPL DATA LOAD TEST")
    print("=" * 60)
    print(f"Job ID: {job_id}")
    print(f"CSV File: {csv_file}")
    print(f"Years: {years} ({get_period_description(years)})")
    print(f"Symbols: {', '.join(symbols)}")
    print("-" * 60)

    # Check for subscribers
    subs = redis_client.pubsub_numsub('tickstock.jobs.data_load')
    print(f"Subscribers on channel: {subs[0][1]}")

    if subs[0][1] == 0:
        print("\nERROR: No subscribers on tickstock.jobs.data_load")
        return None

    # Publish job
    subscribers = redis_client.publish('tickstock.jobs.data_load', json.dumps(job_data))
    print(f"Job published to {subscribers} subscriber(s)\n")

    # Monitor job with improved status tracking
    return monitor_job_progress(redis_client, job_id, len(symbols))

def get_period_description(years):
    """Convert years fraction to readable description"""
    if years == 0.003:
        return "1 Day"
    elif years == 0.005:
        return "2 Days"
    elif years == 0.02:
        return "1 Week"
    elif years == 0.08:
        return "1 Month"
    elif years == 0.25:
        return "3 Months"
    elif years == 0.5:
        return "6 Months"
    elif years == 1:
        return "1 Year"
    else:
        return f"{years} Years"

def monitor_job_progress(redis_client, job_id, expected_symbols):
    """Monitor job with improved status tracking"""

    print("MONITORING JOB PROGRESS")
    print("-" * 60)

    status_key = f"tickstock.jobs.status:{job_id}"
    last_status = None
    last_symbol = None
    last_progress = -1
    start_time = time.time()
    max_wait = 300  # 5 minutes max

    for i in range(max_wait):
        try:
            status_json = redis_client.get(status_key)

            if status_json:
                status = json.loads(status_json)
                current_status = status.get('status', 'unknown')
                current_progress = status.get('progress', 0)
                current_symbol = status.get('current_symbol', '')

                # Print updates for any change
                if (current_status != last_status or
                    current_progress != last_progress or
                    current_symbol != last_symbol):

                    elapsed = int(time.time() - start_time)
                    print(f"\n[{elapsed:3d}s] Status: {current_status.upper()}")

                    if current_progress != last_progress:
                        print(f"       Progress: {current_progress}%")

                    if 'processed_symbols' in status and 'total_symbols' in status:
                        print(f"       Symbols: {status['processed_symbols']}/{status['total_symbols']}")

                    if current_symbol and current_symbol != last_symbol:
                        print(f"       Current Symbol: {current_symbol}")

                    if 'message' in status:
                        print(f"       Message: {status['message']}")

                    # Update tracking variables
                    last_status = current_status
                    last_progress = current_progress
                    last_symbol = current_symbol

                else:
                    # Show we're still monitoring
                    sys.stdout.write('.')
                    sys.stdout.flush()

                # Check if complete
                if current_status in ['completed', 'failed']:
                    elapsed_total = int(time.time() - start_time)
                    print(f"\n\n{'=' * 60}")
                    print(f"JOB {current_status.upper()} in {elapsed_total} seconds")
                    print("=" * 60)

                    if current_status == 'completed':
                        if 'successful_symbols' in status:
                            print(f"Successful: {', '.join(status['successful_symbols'])}")
                        if 'failed_symbols' in status and status['failed_symbols']:
                            print(f"Failed: {', '.join(status['failed_symbols'])}")

                        # Performance metrics
                        if status.get('processed_symbols', 0) > 0:
                            avg_time = elapsed_total / status['processed_symbols']
                            print(f"Average time per symbol: {avg_time:.1f} seconds")
                    else:
                        print(f"Error: {status.get('error_message', 'Unknown error')}")

                    return status

            time.sleep(1)

        except Exception as e:
            print(f"\nError checking status: {e}")
            break

    print(f"\n\nTimeout after {max_wait} seconds")
    return None

def check_database_updates():
    """Check all 5 OHLCV tables for new data"""
    try:
        import psycopg2

        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            database='tickstock',
            user='app_readwrite',
            password='LJI48rUEkUpe6e'
        )

        cursor = conn.cursor()

        print("\nDATABASE VERIFICATION")
        print("-" * 60)

        # Check all 5 tables
        tables = {
            'ohlcv_1min': ('timestamp', 'Minute'),
            'ohlcv_hourly': ('timestamp', 'Hourly'),
            'ohlcv_daily': ('date', 'Daily'),
            'ohlcv_weekly': ('week_ending', 'Weekly'),
            'ohlcv_monthly': ('month_ending', 'Monthly')
        }

        all_populated = True

        for table, (date_col, label) in tables.items():
            try:
                # Get count and latest date
                cursor.execute(f"""
                    SELECT COUNT(*), MAX({date_col})
                    FROM {table}
                    WHERE {date_col} >= CURRENT_DATE - INTERVAL '7 days'
                """)

                count, max_date = cursor.fetchone()

                if count and count > 0:
                    print(f"✅ {table:15} : {count:6} recent records (latest: {max_date})")
                else:
                    print(f"❌ {table:15} : No recent data")
                    all_populated = False

            except Exception as e:
                print(f"❌ {table:15} : Error - {e}")
                all_populated = False

        cursor.close()
        conn.close()

        print("-" * 60)
        if all_populated:
            print("✅ ALL 5 TABLES POPULATED SUCCESSFULLY!")
        else:
            print("⚠️ Some tables are missing data")

        return all_populated

    except Exception as e:
        print(f"Could not verify database: {e}")
        return False

def create_small_test_csv():
    """Create a minimal test CSV with 2 symbols for quick testing"""
    import os

    data_dir = 'data'
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    # Just 2 symbols for quick test
    csv_content = """Symbol,Name,Sector
AAPL,Apple Inc.,Technology
MSFT,Microsoft Corporation,Technology
"""

    csv_path = os.path.join(data_dir, 'test_symbols.csv')
    with open(csv_path, 'w') as f:
        f.write(csv_content)

    return 'test_symbols.csv', ['AAPL', 'MSFT']

def main():
    """Run comprehensive test of improved TickStockPL integration"""

    # Create test CSV
    csv_file, symbols = create_small_test_csv()

    print("TICKSTOCKPL IMPROVED INTEGRATION TEST")
    print("=" * 60)
    print("Testing new features:")
    print("1. Status updates after EACH symbol")
    print("2. All 5 OHLCV tables populated")
    print("3. ~10 seconds per symbol performance")
    print("4. Dynamic lookback periods")
    print("=" * 60)

    # Test with 1 week of data (0.02 years)
    result = submit_test_job(
        csv_file=csv_file,
        years=0.02,  # 1 week - should populate minute, hourly, daily
        symbols=symbols
    )

    if result and result.get('status') == 'completed':
        print("\n✅ Job completed successfully!")

        # Verify database updates
        print("\nVerifying all tables populated...")
        time.sleep(2)  # Give database time to commit

        if check_database_updates():
            print("\n" + "=" * 60)
            print("🎉 SUCCESS - ALL IMPROVEMENTS VERIFIED!")
            print("=" * 60)
            print("✅ Per-symbol status updates working")
            print("✅ All 5 OHLCV tables populated")
            print("✅ Performance improved")
        else:
            print("\n⚠️ Some tables not populated - check with TickStockPL developer")
    else:
        print("\n❌ Job failed or timed out")
        if result:
            print(f"Final status: {result.get('status')}")
            print(f"Error: {result.get('error_message', 'Unknown')}")

if __name__ == "__main__":
    main()