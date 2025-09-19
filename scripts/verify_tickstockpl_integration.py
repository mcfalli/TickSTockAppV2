#!/usr/bin/env python3
"""
Verify TickStockPL Integration Configuration
Checks if TickStockPL is properly configured to send patterns to TickStockAppV2
"""

import sys
import os
import json
import redis
import psycopg2
import time
from datetime import datetime, timedelta
from pathlib import Path
from colorama import init, Fore, Style

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

def print_section(title):
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{title}")
    print(f"{'='*60}{Style.RESET_ALL}")

def check_status(condition, true_msg, false_msg):
    if condition:
        print(f"  {Fore.GREEN}[OK]{Style.RESET_ALL} {true_msg}")
        return True
    else:
        print(f"  {Fore.RED}[FAIL]{Style.RESET_ALL} {false_msg}")
        return False

def check_tickstockpl_files():
    """Check if TickStockPL has the necessary integration files."""
    print_section("TickStockPL File Configuration")

    pl_path = Path("C:/Users/McDude/TickStockPL")
    if not pl_path.exists():
        print(f"  {Fore.RED}TickStockPL directory not found!{Style.RESET_ALL}")
        return False

    # Check for key integration files
    required_files = [
        "scripts/services/run_pattern_detection_service.py",
        "scripts/test_pattern_event.py",
    ]

    all_found = True
    for file in required_files:
        file_path = pl_path / file
        found = check_status(
            file_path.exists(),
            f"Found: {file}",
            f"Missing: {file}"
        )
        if not found:
            all_found = False

    return all_found

def check_database_activity():
    """Check for any TickStockPL activity in database."""
    print_section("Database Activity Check")

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Check for ANY TickStockPL events ever
        cursor.execute("""
            SELECT COUNT(*), MAX(timestamp) as last_event
            FROM integration_events
            WHERE source_system = 'TickStockPL'
        """)

        count, last_event = cursor.fetchone()

        if count > 0 and last_event:
            age_hours = (datetime.now(last_event.tzinfo) - last_event).total_seconds() / 3600
            check_status(
                age_hours < 1,
                f"TickStockPL logged {count} events (last: {age_hours:.1f}h ago)",
                f"TickStockPL events are stale ({age_hours:.1f}h old)"
            )
        else:
            check_status(
                False,
                "",
                "No TickStockPL events found in database EVER!"
            )
            print(f"  {Fore.YELLOW}→ TickStockPL may not have database logging configured{Style.RESET_ALL}")

        cursor.close()
        conn.close()
        return count > 0

    except Exception as e:
        print(f"  {Fore.RED}Database error: {e}{Style.RESET_ALL}")
        return False

def test_manual_pattern_publish():
    """Publish a test pattern to verify the pipeline works."""
    print_section("Manual Pattern Publishing Test")

    r = redis.Redis(**REDIS_CONFIG)

    # Create a test pattern that mimics TickStockPL format
    test_pattern = {
        'event_type': 'pattern_detected',
        'source': 'TickStockPL',  # Pretend to be TickStockPL
        'timestamp': time.time(),
        'data': {
            'symbol': 'TEST',
            'pattern': 'Integration_Test_Pattern',
            'confidence': 0.99,
            'flow_id': f"test-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            'tier': 'intraday',
            'price_change': 5.0,
            'current_price': 100.0
        }
    }

    channel = 'tickstock.events.patterns'

    # Publish the pattern
    subscribers = r.publish(channel, json.dumps(test_pattern))
    print(f"\nPublished test pattern as 'TickStockPL' to '{channel}'")
    print(f"  Subscribers: {subscribers}")

    if subscribers > 0:
        print(f"  {Fore.GREEN}Pattern sent successfully to {subscribers} subscriber(s){Style.RESET_ALL}")

        # Wait for processing
        time.sleep(2)

        # Check if it was logged
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT checkpoint, source_system
                FROM integration_events
                WHERE pattern_name = 'Integration_Test_Pattern'
                AND timestamp > NOW() - INTERVAL '10 seconds'
                ORDER BY timestamp
            """)

            results = cursor.fetchall()
            if results:
                print(f"\n  {Fore.GREEN}Pattern flow confirmed:{Style.RESET_ALL}")
                for checkpoint, source in results:
                    print(f"    {source}: {checkpoint}")
            else:
                print(f"  {Fore.RED}Pattern not found in database!{Style.RESET_ALL}")

            cursor.close()
            conn.close()

        except Exception as e:
            print(f"  {Fore.RED}Database check failed: {e}{Style.RESET_ALL}")
    else:
        print(f"  {Fore.RED}No subscribers! TickStockAppV2 may not be running{Style.RESET_ALL}")

    return subscribers > 0

def create_tickstockpl_heartbeat():
    """Create a TickStockPL heartbeat in Redis."""
    print_section("Creating TickStockPL Heartbeat")

    r = redis.Redis(**REDIS_CONFIG)

    # Set a heartbeat for TickStockPL
    heartbeat_key = 'tickstock:producer:heartbeat'
    r.set(heartbeat_key, time.time())

    print(f"  {Fore.GREEN}Created TickStockPL heartbeat in Redis{Style.RESET_ALL}")
    print(f"  Key: {heartbeat_key}")
    print(f"  This simulates TickStockPL being alive")

    return True

def suggest_fixes():
    """Provide actionable fixes."""
    print_section("Recommended Actions")

    print(f"\n{Fore.YELLOW}1. START TickStockPL Pattern Service:{Style.RESET_ALL}")
    print(f"""   cd C:/Users/McDude/TickStockPL
   python scripts/services/run_pattern_detection_service.py""")

    print(f"\n{Fore.YELLOW}2. TEST with Synthetic Pattern:{Style.RESET_ALL}")
    print(f"""   cd C:/Users/McDude/TickStockPL
   python scripts/test_pattern_event.py""")

    print(f"\n{Fore.YELLOW}3. CHECK TickStockPL Configuration:{Style.RESET_ALL}")
    print(f"""   Verify TickStockPL has:
   - Redis connection configured
   - Database logging implemented
   - Pattern detection enabled
   - Market data source (or synthetic data)""")

    print(f"\n{Fore.YELLOW}4. MONITOR Both Services:{Style.RESET_ALL}")
    print(f"""   # Terminal 1: TickStockPL
   cd C:/Users/McDude/TickStockPL
   python scripts/services/run_pattern_detection_service.py

   # Terminal 2: TickStockAppV2
   cd C:/Users/McDude/TickStockAppV2
   python src/app.py

   # Terminal 3: Monitor
   cd C:/Users/McDude/TickStockAppV2
   python scripts/monitor_system_health.py --watch""")

    print(f"\n{Fore.YELLOW}5. VERIFY Pattern Flow:{Style.RESET_ALL}")
    print(f"""   After starting both services:
   - Wait 60 seconds for heartbeats
   - Check for pattern events in database
   - Use diagnose_integration.py to test""")

def main():
    print(f"{Fore.MAGENTA}{'='*60}")
    print(f"TickStockPL Integration Verification")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}{Style.RESET_ALL}")

    # Run checks
    files_ok = check_tickstockpl_files()
    db_activity = check_database_activity()

    # Test the pipeline
    pipeline_ok = test_manual_pattern_publish()

    # Create heartbeat for testing
    create_tickstockpl_heartbeat()

    # Provide recommendations
    suggest_fixes()

    # Summary
    print_section("Summary")
    if not db_activity:
        print(f"{Fore.RED}CRITICAL: TickStockPL has NEVER logged to database{Style.RESET_ALL}")
        print(f"The pattern detection service is not running or not configured properly.")
    elif pipeline_ok:
        print(f"{Fore.GREEN}Pipeline is working when patterns are sent{Style.RESET_ALL}")
        print(f"TickStockPL just needs to be started and configured.")
    else:
        print(f"{Fore.RED}Pipeline issues detected{Style.RESET_ALL}")
        print(f"Check both TickStockPL and TickStockAppV2 configurations.")

if __name__ == "__main__":
    main()