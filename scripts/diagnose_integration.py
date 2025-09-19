#!/usr/bin/env python3
"""
Diagnose Integration Issues Between TickStockPL and TickStockAppV2
"""

import sys
import os
import time
import json
import redis
import psycopg2
from datetime import datetime, timedelta
from colorama import init, Fore, Style

# Initialize colorama
init()

# Configuration
REDIS_CONFIG = {
    'host': 'localhost',
    'port': 6379,
    'decode_responses': True
}

DB_CONFIG = {
    'host': 'localhost',
    'port': 5433,
    'database': 'tickstock',
    'user': 'app_readwrite',
    'password': 'LJI48rUEkUpe6e'
}

def check_database_events():
    """Check what's in the database."""
    print(f"\n{Fore.CYAN}=== Database Integration Events ==={Style.RESET_ALL}")

    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    # Count events by type
    cursor.execute("""
        SELECT event_type, source_system, COUNT(*) as count
        FROM integration_events
        WHERE timestamp > NOW() - INTERVAL '1 hour'
        GROUP BY event_type, source_system
        ORDER BY count DESC
    """)

    results = cursor.fetchall()
    if results:
        print(f"\n{Fore.GREEN}Events in last hour:{Style.RESET_ALL}")
        for event_type, source, count in results:
            print(f"  {source}: {event_type} ({count} events)")
    else:
        print(f"{Fore.RED}No events in last hour!{Style.RESET_ALL}")

    # Check for pattern events specifically
    cursor.execute("""
        SELECT COUNT(*)
        FROM integration_events
        WHERE event_type = 'pattern_detected'
        AND timestamp > NOW() - INTERVAL '1 hour'
    """)

    pattern_count = cursor.fetchone()[0]
    print(f"\n{Fore.YELLOW}Pattern events in last hour: {pattern_count}{Style.RESET_ALL}")

    if pattern_count == 0:
        print(f"  {Fore.RED}-> No patterns detected! TickStockPL may not be running or detecting patterns{Style.RESET_ALL}")

    cursor.close()
    conn.close()

def check_redis_channels():
    """Check Redis pub/sub channels."""
    print(f"\n{Fore.CYAN}=== Redis Channel Test ==={Style.RESET_ALL}")

    r = redis.Redis(**REDIS_CONFIG)

    # Test publish to pattern channel
    test_pattern = {
        'event_type': 'pattern_detected',
        'source': 'DiagnosticTest',
        'timestamp': time.time(),
        'data': {
            'symbol': 'TEST',
            'pattern': 'Diagnostic_Test',
            'confidence': 0.99,
            'flow_id': 'test-diagnostic-flow'
        }
    }

    channel = 'tickstock.events.patterns'

    # Publish test message
    subscribers = r.publish(channel, json.dumps(test_pattern))
    print(f"\nPublished test pattern to '{channel}'")
    print(f"  {Fore.YELLOW}Subscribers listening: {subscribers}{Style.RESET_ALL}")

    if subscribers == 0:
        print(f"  {Fore.RED}-> No subscribers! TickStockAppV2 may not be subscribed to this channel{Style.RESET_ALL}")
    else:
        print(f"  {Fore.GREEN}-> {subscribers} subscriber(s) should have received the test pattern{Style.RESET_ALL}")

    # Check for TickStockPL heartbeat
    heartbeat_key = 'tickstock:producer:heartbeat'
    heartbeat = r.get(heartbeat_key)

    if heartbeat:
        hb_time = float(heartbeat)
        age = time.time() - hb_time
        if age < 120:
            print(f"\n{Fore.GREEN}TickStockPL heartbeat found: {int(age)}s ago{Style.RESET_ALL}")
        else:
            print(f"\n{Fore.YELLOW}TickStockPL heartbeat is stale: {int(age)}s ago{Style.RESET_ALL}")
    else:
        print(f"\n{Fore.RED}No TickStockPL heartbeat found in Redis{Style.RESET_ALL}")
        print(f"  -> TickStockPL services may not be running")

    # Check for cached patterns
    pattern_keys = r.keys('tickstock:patterns:*')
    print(f"\n{Fore.CYAN}Cached patterns in Redis: {len(pattern_keys)}{Style.RESET_ALL}")

    if pattern_keys:
        # Show sample patterns
        print("  Sample patterns:")
        for key in pattern_keys[:5]:
            ttl = r.ttl(key)
            key_name = key if isinstance(key, str) else key.decode('utf-8')
            print(f"    {key_name} (TTL: {ttl}s)")
    else:
        print(f"  {Fore.RED}-> No cached patterns. TickStockPL may not be detecting patterns{Style.RESET_ALL}")

def check_tickstockpl_logs():
    """Check if TickStockPL is logging to database."""
    print(f"\n{Fore.CYAN}=== TickStockPL Database Activity ==={Style.RESET_ALL}")

    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    # Check for TickStockPL events
    cursor.execute("""
        SELECT checkpoint, COUNT(*), MAX(timestamp) as last_event
        FROM integration_events
        WHERE source_system = 'TickStockPL'
        AND timestamp > NOW() - INTERVAL '1 hour'
        GROUP BY checkpoint
        ORDER BY last_event DESC
    """)

    results = cursor.fetchall()

    if results:
        print(f"\n{Fore.GREEN}TickStockPL activity in last hour:{Style.RESET_ALL}")
        for checkpoint, count, last_event in results:
            age = (datetime.now(last_event.tzinfo) - last_event).total_seconds()
            print(f"  {checkpoint}: {count} events (last: {int(age)}s ago)")
    else:
        print(f"\n{Fore.RED}No TickStockPL events in database!{Style.RESET_ALL}")
        print(f"  Possible issues:")
        print(f"  1. TickStockPL pattern service not running")
        print(f"  2. TickStockPL not configured for database logging")
        print(f"  3. No patterns being detected (check market hours/data)")

    cursor.close()
    conn.close()

def test_pattern_flow():
    """Send a test pattern through the system."""
    print(f"\n{Fore.CYAN}=== Testing Pattern Flow ==={Style.RESET_ALL}")

    # Wait a moment for any subscribers to process
    time.sleep(2)

    # Check if test pattern was received
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT checkpoint, timestamp
        FROM integration_events
        WHERE pattern_name = 'Diagnostic_Test'
        AND timestamp > NOW() - INTERVAL '1 minute'
        ORDER BY timestamp DESC
    """)

    results = cursor.fetchall()

    if results:
        print(f"\n{Fore.GREEN}Test pattern flow:{Style.RESET_ALL}")
        for checkpoint, timestamp in results:
            print(f"  {checkpoint} at {timestamp}")
    else:
        print(f"\n{Fore.YELLOW}Test pattern not found in database{Style.RESET_ALL}")
        print(f"  -> TickStockAppV2 may not be processing Redis messages")

    cursor.close()
    conn.close()

def suggest_fixes():
    """Suggest fixes based on findings."""
    print(f"\n{Fore.MAGENTA}=== Recommended Actions ==={Style.RESET_ALL}")

    print(f"\n1. {Fore.CYAN}Verify TickStockPL is running:{Style.RESET_ALL}")
    print(f"   cd C:/Users/McDude/TickStockPL")
    print(f"   python scripts/services/run_pattern_detection_service.py")

    print(f"\n2. {Fore.CYAN}Check TickStockPL logs for errors:{Style.RESET_ALL}")
    print(f"   Look for pattern detection issues or Redis publish failures")

    print(f"\n3. {Fore.CYAN}Verify market data is flowing:{Style.RESET_ALL}")
    print(f"   TickStockPL needs market data to detect patterns")
    print(f"   Check if market is open or synthetic data is configured")

    print(f"\n4. {Fore.CYAN}Test with synthetic patterns:{Style.RESET_ALL}")
    print(f"   cd C:/Users/McDude/TickStockPL")
    print(f"   python scripts/test_pattern_event.py")

    print(f"\n5. {Fore.CYAN}Monitor both services:{Style.RESET_ALL}")
    print(f"   python scripts/monitor_system_health.py --watch")

def main():
    """Run diagnostics."""
    print(f"{Fore.MAGENTA}{'='*60}")
    print(f"Integration Diagnostics")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}{Style.RESET_ALL}")

    # Run checks
    check_database_events()
    check_redis_channels()
    check_tickstockpl_logs()
    test_pattern_flow()
    suggest_fixes()

    print(f"\n{Fore.MAGENTA}{'='*60}{Style.RESET_ALL}")
    print(f"Diagnostics complete.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Interrupted by user.{Style.RESET_ALL}")
        sys.exit(0)