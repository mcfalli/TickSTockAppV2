#!/usr/bin/env python3
"""
System Health Monitor for TickStock Integration
Checks if all components are connected and listening properly.
"""

import sys
import os
import time
import psycopg2
from datetime import datetime, timedelta
from colorama import init, Fore, Style

# Initialize colorama for Windows
init()

# Database connection
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'tickstock',
    'user': 'app_readwrite',
    'password': 'LJI48rUEkUpe6e'
}

def connect_db():
    """Connect to the database."""
    try:
        return psycopg2.connect(**DB_CONFIG)
    except Exception as e:
        print(f"{Fore.RED}Failed to connect to database: {e}{Style.RESET_ALL}")
        sys.exit(1)

def check_subscriptions(conn):
    """Check Redis subscription status."""
    print(f"\n{Fore.CYAN}=== Redis Subscriptions ==={Style.RESET_ALL}")

    with conn.cursor() as cursor:
        # Check for subscription confirmations in last 5 minutes
        cursor.execute("""
            SELECT channel, MAX(timestamp) as last_confirmed, COUNT(*) as confirm_count
            FROM integration_events
            WHERE event_type IN ('subscription_active', 'subscription_confirmed')
            AND timestamp > NOW() - INTERVAL '5 minutes'
            GROUP BY channel
            ORDER BY channel
        """)

        subscriptions = cursor.fetchall()

        if subscriptions:
            print(f"{Fore.GREEN}✓ Active Subscriptions:{Style.RESET_ALL}")
            for channel, last_confirmed, count in subscriptions:
                age = (datetime.now(last_confirmed.tzinfo) - last_confirmed).total_seconds()
                status = f"{Fore.GREEN}Active{Style.RESET_ALL}" if age < 120 else f"{Fore.YELLOW}Stale{Style.RESET_ALL}"
                print(f"  • {channel}: {status} (last: {int(age)}s ago, confirmations: {count})")
        else:
            print(f"{Fore.RED}✗ No active subscriptions found!{Style.RESET_ALL}")
            print(f"  {Fore.YELLOW}Make sure TickStockAppV2 is running{Style.RESET_ALL}")

def check_heartbeats(conn):
    """Check system heartbeats."""
    print(f"\n{Fore.CYAN}=== System Heartbeats ==={Style.RESET_ALL}")

    with conn.cursor() as cursor:
        # Check for recent heartbeats
        cursor.execute("""
            SELECT source_system, MAX(timestamp) as last_heartbeat, COUNT(*) as heartbeat_count
            FROM integration_events
            WHERE event_type = 'heartbeat'
            AND timestamp > NOW() - INTERVAL '10 minutes'
            GROUP BY source_system
            ORDER BY source_system
        """)

        heartbeats = cursor.fetchall()

        if heartbeats:
            print(f"{Fore.GREEN}✓ Active Heartbeats:{Style.RESET_ALL}")
            for system, last_hb, count in heartbeats:
                age = (datetime.now(last_hb.tzinfo) - last_hb).total_seconds()
                if age < 90:
                    status = f"{Fore.GREEN}Alive{Style.RESET_ALL}"
                elif age < 180:
                    status = f"{Fore.YELLOW}Delayed{Style.RESET_ALL}"
                else:
                    status = f"{Fore.RED}Stale{Style.RESET_ALL}"
                print(f"  • {system}: {status} (last: {int(age)}s ago, count: {count})")
        else:
            print(f"{Fore.RED}✗ No heartbeats detected!{Style.RESET_ALL}")
            print(f"  {Fore.YELLOW}Services may not be running or heartbeat logging not active{Style.RESET_ALL}")

def check_pattern_flow(conn):
    """Check pattern event flow."""
    print(f"\n{Fore.CYAN}=== Pattern Event Flow ==={Style.RESET_ALL}")

    with conn.cursor() as cursor:
        # Check for complete pattern flows in last hour
        cursor.execute("""
            SELECT * FROM pattern_flow_analysis
            WHERE start_time > NOW() - INTERVAL '1 hour'
            ORDER BY start_time DESC
            LIMIT 5
        """)

        flows = cursor.fetchall()

        if flows:
            print(f"{Fore.GREEN}✓ Recent Pattern Flows:{Style.RESET_ALL}")
            for flow in flows:
                flow_id, start_time, end_time, latency, symbol, pattern, confidence, users, checkpoints, path = flow
                latency_ms = float(latency) if latency else 0

                if latency_ms < 100:
                    latency_color = Fore.GREEN
                elif latency_ms < 500:
                    latency_color = Fore.YELLOW
                else:
                    latency_color = Fore.RED

                print(f"  • {pattern} @ {symbol}: {latency_color}{latency_ms:.1f}ms{Style.RESET_ALL} "
                      f"({checkpoints} checkpoints)")
                print(f"    Path: {' → '.join(path)}")
        else:
            print(f"{Fore.YELLOW}⚠ No complete pattern flows in last hour{Style.RESET_ALL}")

        # Check for incomplete flows (only PATTERN_PUBLISHED)
        cursor.execute("""
            SELECT symbol, pattern_name, COUNT(*) as orphan_count
            FROM integration_events
            WHERE event_type = 'pattern_detected'
            AND checkpoint = 'PATTERN_PUBLISHED'
            AND timestamp > NOW() - INTERVAL '1 hour'
            AND flow_id NOT IN (
                SELECT flow_id FROM integration_events
                WHERE checkpoint IN ('EVENT_RECEIVED', 'EVENT_PARSED')
                AND timestamp > NOW() - INTERVAL '1 hour'
            )
            GROUP BY symbol, pattern_name
            LIMIT 5
        """)

        orphans = cursor.fetchall()

        if orphans:
            print(f"\n{Fore.YELLOW}⚠ Unprocessed Patterns (TickStockAppV2 may not be receiving):{Style.RESET_ALL}")
            for symbol, pattern, count in orphans:
                print(f"  • {pattern} @ {symbol}: {count} events not received by TickStockAppV2")

def check_integration_status(conn):
    """Check overall integration status."""
    print(f"\n{Fore.CYAN}=== Integration Summary ==={Style.RESET_ALL}")

    with conn.cursor() as cursor:
        # Get event counts by checkpoint
        cursor.execute("""
            SELECT checkpoint, COUNT(*) as event_count
            FROM integration_events
            WHERE timestamp > NOW() - INTERVAL '10 minutes'
            GROUP BY checkpoint
            ORDER BY event_count DESC
        """)

        checkpoints = cursor.fetchall()

        if checkpoints:
            print(f"{Fore.GREEN}✓ Recent Activity (last 10 minutes):{Style.RESET_ALL}")
            for checkpoint, count in checkpoints:
                print(f"  • {checkpoint}: {count} events")
        else:
            print(f"{Fore.RED}✗ No integration activity in last 10 minutes!{Style.RESET_ALL}")

        # Check both systems
        cursor.execute("""
            SELECT source_system, COUNT(*) as events,
                   MAX(timestamp) as last_event
            FROM integration_events
            WHERE timestamp > NOW() - INTERVAL '10 minutes'
            GROUP BY source_system
        """)

        systems = cursor.fetchall()

        print(f"\n{Fore.CYAN}System Activity:{Style.RESET_ALL}")
        expected_systems = {'TickStockPL', 'TickStockAppV2'}
        active_systems = set()

        for system, count, last_event in systems:
            active_systems.add(system)
            age = (datetime.now(last_event.tzinfo) - last_event).total_seconds()
            print(f"  • {system}: {Fore.GREEN}Active{Style.RESET_ALL} "
                  f"({count} events, last: {int(age)}s ago)")

        missing_systems = expected_systems - active_systems
        for system in missing_systems:
            print(f"  • {system}: {Fore.RED}No Activity{Style.RESET_ALL}")

def main():
    """Main monitoring function."""
    print(f"{Fore.MAGENTA}{'='*60}")
    print(f"TickStock Integration Health Monitor")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}{Style.RESET_ALL}")

    conn = connect_db()

    try:
        check_subscriptions(conn)
        check_heartbeats(conn)
        check_pattern_flow(conn)
        check_integration_status(conn)

        print(f"\n{Fore.MAGENTA}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Monitor complete. Press Ctrl+C to exit.{Style.RESET_ALL}")

        # Optional: continuous monitoring
        if len(sys.argv) > 1 and sys.argv[1] == '--watch':
            print(f"{Fore.YELLOW}Watching mode: Refreshing every 30 seconds...{Style.RESET_ALL}")
            while True:
                time.sleep(30)
                os.system('cls' if os.name == 'nt' else 'clear')
                main()

    finally:
        conn.close()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Monitor stopped by user.{Style.RESET_ALL}")
        sys.exit(0)