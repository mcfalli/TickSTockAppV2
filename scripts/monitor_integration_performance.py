#!/usr/bin/env python3
"""
TickStockAppV2 Integration Performance Monitor
Real-time dashboard showing pattern flow from TickStockPL to TickStockAppV2.

Sprint 25A: Comprehensive performance monitoring for integration validation.
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import time
import redis
import psycopg2
from datetime import datetime, timedelta
from collections import deque
import signal

class IntegrationPerformanceMonitor:
    """Real-time integration performance monitoring."""

    def __init__(self):
        self.redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
        self.db_conn = psycopg2.connect(
            host='localhost', port=5433, database='tickstock',
            user='app_readwrite', password='LJI48rUEkUpe6e'
        )
        self.db_conn.autocommit = True

        # Performance tracking
        self.pattern_counts = deque(maxlen=60)  # Last 60 seconds
        self.latencies = deque(maxlen=100)  # Last 100 patterns
        self.running = True

    def get_pattern_metrics(self, interval_minutes=5):
        """Get pattern processing metrics."""
        cursor = self.db_conn.cursor()

        cursor.execute("""
            SELECT
                COUNT(DISTINCT flow_id) as total_patterns,
                COUNT(DISTINCT symbol) as unique_symbols,
                COUNT(DISTINCT pattern_name) as unique_patterns,
                AVG(processing_time_ms) as avg_processing_ms,
                MAX(processing_time_ms) as max_processing_ms,
                MIN(timestamp) as first_pattern,
                MAX(timestamp) as last_pattern
            FROM integration_events
            WHERE event_type = 'PATTERN_RECEIVED'
              AND timestamp > NOW() - INTERVAL '%s minutes'
        """, (interval_minutes,))

        result = cursor.fetchone()
        cursor.close()

        if result and result[0] > 0:
            patterns, symbols, types, avg_ms, max_ms, first, last = result
            time_span = (last - first).total_seconds() if first and last else 0
            rate = patterns / time_span * 60 if time_span > 0 else 0

            return {
                'total_patterns': patterns,
                'unique_symbols': symbols,
                'unique_types': types,
                'avg_processing_ms': avg_ms or 0,
                'max_processing_ms': max_ms or 0,
                'patterns_per_minute': rate,
                'time_span_seconds': time_span
            }
        return None

    def get_flow_analysis(self):
        """Get end-to-end flow analysis."""
        cursor = self.db_conn.cursor()

        cursor.execute("""
            SELECT
                COUNT(*) as complete_flows,
                AVG(end_to_end_latency_ms) as avg_latency,
                MAX(end_to_end_latency_ms) as max_latency,
                MIN(end_to_end_latency_ms) as min_latency,
                AVG(checkpoints_logged) as avg_checkpoints
            FROM pattern_flow_analysis
            WHERE checkpoints_logged >= 3
              AND start_time > NOW() - INTERVAL '5 minutes'
        """)

        result = cursor.fetchone()
        cursor.close()

        if result and result[0] > 0:
            flows, avg_lat, max_lat, min_lat, avg_checks = result
            return {
                'complete_flows': flows,
                'avg_latency_ms': avg_lat or 0,
                'max_latency_ms': max_lat or 0,
                'min_latency_ms': min_lat or 0,
                'avg_checkpoints': avg_checks or 0
            }
        return None

    def get_redis_stats(self):
        """Get Redis cache and subscription stats."""
        pattern_keys = len(self.redis_client.keys('tickstock:patterns:*'))
        api_cache_keys = len(self.redis_client.keys('tickstock:api:*'))

        # Check subscribers
        pubsub_info = self.redis_client.execute_command('PUBSUB', 'NUMSUB', 'tickstock.events.patterns')
        subscriber_count = pubsub_info[1] if len(pubsub_info) > 1 else 0

        return {
            'pattern_cache_entries': pattern_keys,
            'api_cache_entries': api_cache_keys,
            'subscribers': subscriber_count
        }

    def get_heartbeat_status(self):
        """Get heartbeat monitoring status."""
        cursor = self.db_conn.cursor()

        cursor.execute("""
            SELECT
                MAX(timestamp) as last_heartbeat,
                COUNT(*) as total_heartbeats
            FROM integration_events
            WHERE event_type = 'HEARTBEAT'
              AND timestamp > NOW() - INTERVAL '10 minutes'
        """)

        result = cursor.fetchone()
        cursor.close()

        if result and result[0]:
            last_hb, count = result
            age_seconds = (datetime.now() - last_hb.replace(tzinfo=None)).total_seconds()
            return {
                'last_heartbeat_age': age_seconds,
                'heartbeat_count': count,
                'status': 'OK' if age_seconds < 90 else 'STALE'
            }
        return None

    def display_dashboard(self):
        """Display performance dashboard."""
        os.system('cls' if os.name == 'nt' else 'clear')

        print("=" * 70)
        print(" TICKSTOCKAPPV2 INTEGRATION PERFORMANCE MONITOR ".center(70))
        print("=" * 70)
        print(f"  Monitoring Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("  Press Ctrl+C to exit")
        print("=" * 70)

        # Pattern Metrics
        metrics = self.get_pattern_metrics()
        if metrics:
            print("\n[PATTERN PROCESSING]")
            print(f"  Patterns Received: {metrics['total_patterns']:,}")
            print(f"  Rate: {metrics['patterns_per_minute']:.1f} patterns/minute")
            print(f"  Unique Symbols: {metrics['unique_symbols']}")
            print(f"  Pattern Types: {metrics['unique_types']}")
            print(f"  Avg Processing: {metrics['avg_processing_ms']:.1f}ms")
            print(f"  Max Processing: {metrics['max_processing_ms']:.1f}ms")
        else:
            print("\n[PATTERN PROCESSING]")
            print("  No patterns received in last 5 minutes")

        # Flow Analysis
        flow = self.get_flow_analysis()
        if flow:
            print("\n[END-TO-END FLOW]")
            print(f"  Complete Flows: {flow['complete_flows']}")
            print(f"  Avg Latency: {flow['avg_latency_ms']:.1f}ms")
            print(f"  Min/Max: {flow['min_latency_ms']:.1f}ms / {flow['max_latency_ms']:.1f}ms")
            print(f"  Avg Checkpoints: {flow['avg_checkpoints']:.1f}")
        else:
            print("\n[END-TO-END FLOW]")
            print("  No complete flows in last 5 minutes")

        # Redis Stats
        redis_stats = self.get_redis_stats()
        print("\n[REDIS INTEGRATION]")
        print(f"  Active Subscribers: {redis_stats['subscribers']}")
        print(f"  Pattern Cache: {redis_stats['pattern_cache_entries']} entries")
        print(f"  API Cache: {redis_stats['api_cache_entries']} entries")

        # Heartbeat Status
        heartbeat = self.get_heartbeat_status()
        if heartbeat:
            print("\n[HEARTBEAT MONITORING]")
            print(f"  Status: {heartbeat['status']}")
            print(f"  Last Heartbeat: {heartbeat['last_heartbeat_age']:.0f}s ago")
            print(f"  Total (10min): {heartbeat['heartbeat_count']}")
        else:
            print("\n[HEARTBEAT MONITORING]")
            print("  Status: NO HEARTBEATS")

        # Performance Targets
        print("\n[PERFORMANCE TARGETS]")
        if metrics and metrics['avg_processing_ms'] < 100:
            print(f"  [PASS] Processing <100ms: {metrics['avg_processing_ms']:.1f}ms")
        else:
            print(f"  [FAIL] Processing >100ms: {metrics.get('avg_processing_ms', 0):.1f}ms")

        if flow and flow['avg_latency_ms'] < 100:
            print(f"  [PASS] E2E Latency <100ms: {flow['avg_latency_ms']:.1f}ms")
        else:
            print(f"  [FAIL] E2E Latency >100ms: {flow.get('avg_latency_ms', 0):.1f}ms")

        if metrics and metrics['patterns_per_minute'] >= 40:
            print(f"  [PASS] Rate >=40/min: {metrics['patterns_per_minute']:.1f}")
        else:
            rate = metrics['patterns_per_minute'] if metrics else 0
            print(f"  [FAIL] Rate <40/min: {rate:.1f}")

        # Integration Health
        print("\n[INTEGRATION HEALTH]")
        if redis_stats['subscribers'] > 0:
            print(f"  [OK] Redis subscription active")
        else:
            print(f"  [X] No Redis subscribers!")

        if heartbeat and heartbeat['status'] == 'OK':
            print(f"  [OK] Heartbeats healthy")
        else:
            print(f"  [X] Heartbeats missing or stale!")

        if metrics and metrics['total_patterns'] > 0:
            print(f"  [OK] Pattern flow active")
        else:
            print(f"  [X] No pattern flow detected!")

    def run(self):
        """Run continuous monitoring."""
        signal.signal(signal.SIGINT, lambda s, f: setattr(self, 'running', False))

        print("Starting Integration Performance Monitor...")
        print("Connecting to services...")

        while self.running:
            try:
                self.display_dashboard()
                time.sleep(5)  # Update every 5 seconds
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"\nError: {e}")
                time.sleep(5)

        print("\n\nMonitoring stopped.")
        self.cleanup()

    def cleanup(self):
        """Clean up resources."""
        try:
            self.redis_client.close()
            self.db_conn.close()
        except:
            pass


if __name__ == "__main__":
    monitor = IntegrationPerformanceMonitor()
    monitor.run()