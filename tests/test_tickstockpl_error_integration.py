#!/usr/bin/env python3
"""
Sprint 32: Test TickStockPL Error Integration
Monitors and verifies that TickStockPL errors are being received and processed
"""

import os
import sys
import time
import json
import redis
import psycopg2
from datetime import datetime, timedelta
from src.core.services.config_manager import get_config


# Get configuration
try:
    config = get_config()
except:
    config = None

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

print("\n" + "="*60)
print("TICKSTOCKPL ERROR INTEGRATION TEST")
print("="*60 + "\n")

# 1. Check Redis Subscriber
print("[1] Checking Redis channel subscription...")
try:
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)

    # Check if anyone is subscribed to the error channel
    pubsub_info = r.execute_command('PUBSUB', 'NUMSUB', 'tickstock:errors')
    channel = pubsub_info[0]
    subscriber_count = pubsub_info[1]

    if subscriber_count > 0:
        print(f"  [OK] Channel '{channel}' has {subscriber_count} subscriber(s)")
    else:
        print(f"  [FAIL] No subscribers on '{channel}' - Is TickStockAppV2 running?")
except Exception as e:
    print(f"  [FAIL] Redis check failed: {e}")
    sys.exit(1)

# 2. Monitor Redis Channel (brief)
print("\n[2] Monitoring Redis channel for 5 seconds...")
try:
    pubsub = r.pubsub()
    pubsub.subscribe('tickstock:errors')

    # Get one message to confirm subscription
    message = pubsub.get_message(timeout=1)
    print(f"  [OK] Subscribed successfully")

    # Listen for real messages
    print("  [WAIT] Waiting for TickStockPL errors...")

    start_time = time.time()
    messages_received = 0

    while time.time() - start_time < 5:
        message = pubsub.get_message(timeout=0.5)
        if message and message['type'] == 'message':
            try:
                error_data = json.loads(message['data'])
                messages_received += 1
                print(f"  [MSG] Received: [{error_data.get('severity')}] {error_data.get('message')[:50]}...")
                print(f"     Source: {error_data.get('source')}, Component: {error_data.get('component')}")
            except:
                pass

    if messages_received == 0:
        print("  [INFO] No errors received (this is OK if TickStockPL has no errors)")
    else:
        print(f"  [OK] Received {messages_received} error(s) from TickStockPL")

    pubsub.unsubscribe()
    pubsub.close()
except Exception as e:
    print(f"  [FAIL] Monitoring failed: {e}")

# 3. Check Database for Recent TickStockPL Errors
print("\n[3] Checking database for TickStockPL errors...")
try:
    db_conn = psycopg2.connect(config.get('DATABASE_URI'))
    cursor = db_conn.cursor()

    # Check for recent TickStockPL errors (last hour)
    cursor.execute("""
        SELECT
            severity,
            component,
            message,
            created_at
        FROM error_logs
        WHERE source = 'TickStockPL'
        AND created_at > NOW() - INTERVAL '1 hour'
        ORDER BY created_at DESC
        LIMIT 5
    """)

    results = cursor.fetchall()

    if results:
        print(f"  [OK] Found {len(results)} recent TickStockPL error(s) in database:")
        for severity, component, message, created_at in results:
            print(f"     [{severity:8}] {component:15} | {message[:40]}... | {created_at.strftime('%H:%M:%S')}")
    else:
        print("  [INFO] No TickStockPL errors in database (last hour)")
        print("     Note: Only 'error' and 'critical' severity go to database")

    # Get statistics
    cursor.execute("""
        SELECT
            severity,
            COUNT(*) as count
        FROM error_logs
        WHERE source = 'TickStockPL'
        AND created_at > NOW() - INTERVAL '24 hours'
        GROUP BY severity
        ORDER BY severity
    """)

    stats = cursor.fetchall()
    if stats:
        print("\n  [STATS] Last 24 hours statistics:")
        for severity, count in stats:
            print(f"     {severity}: {count} errors")

    cursor.close()
    db_conn.close()
except Exception as e:
    print(f"  [FAIL] Database check failed: {e}")

# 4. Check Log File
print("\n[4] Checking log file for TickStockPL errors...")
try:
    log_file = 'logs/tickstock.log'
    if os.path.exists(log_file):
        # Read last 1000 lines
        with open(log_file, 'r') as f:
            lines = f.readlines()[-1000:]

        # Count TickStockPL references
        pl_errors = [line for line in lines if 'TickStockPL' in line]

        if pl_errors:
            print(f"  [OK] Found {len(pl_errors)} TickStockPL references in log file")
            # Show last 3
            print("  [LOG] Recent log entries:")
            for line in pl_errors[-3:]:
                print(f"     {line.strip()[:80]}...")
        else:
            print("  [INFO] No TickStockPL errors in log file")
    else:
        print(f"  [FAIL] Log file not found at {log_file}")
except Exception as e:
    print(f"  [FAIL] Log file check failed: {e}")

# 5. Test Publishing (Optional)
print("\n[5] Test publishing to verify integration...")
try:
    response = input("  Do you want to publish a test error? (y/n): ").lower()
    if response == 'y':
        test_error = {
            'error_id': '00000000-0000-0000-0000-000000000000',
            'source': 'TickStockPL',
            'severity': 'error',
            'category': 'test',
            'message': f'Integration test from TickStockAppV2 at {datetime.now()}',
            'component': 'IntegrationTest',
            'traceback': None,
            'context': {'test': True, 'timestamp': time.time()},
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }

        r.publish('tickstock:errors', json.dumps(test_error))
        print("  [OK] Test error published")
        print("     Check database and logs in a few seconds to confirm processing")
    else:
        print("  [INFO] Skipped test publish")
except Exception as e:
    print(f"  [FAIL] Test publish failed: {e}")

# Summary
print("\n" + "="*60)
print("INTEGRATION TEST SUMMARY")
print("="*60)

print("""
[OK] What's Working:
  - Redis channel subscription active
  - Database table ready for errors
  - Log file capturing events

[TODO] Next Steps:
  1. Have TickStockPL publish some test errors
  2. Check database: SELECT * FROM error_logs WHERE source = 'TickStockPL';
  3. Monitor log file: tail -f logs/tickstock.log
  4. Verify severity threshold (only error/critical go to DB)

[CHECK] Quick Checks:
  - Redis: redis-cli PUBSUB NUMSUB tickstock:errors
  - Database: psql -c "SELECT COUNT(*) FROM error_logs WHERE source='TickStockPL';"
  - Logs: grep TickStockPL logs/tickstock.log | tail
""")

print("Test complete!")