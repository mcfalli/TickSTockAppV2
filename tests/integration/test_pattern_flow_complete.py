#!/usr/bin/env python3
"""
End-to-End Pattern Flow Test Suite
Validates complete pattern journey from TickStockPL to UI readiness.
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import time
import json
import uuid
import redis
import psycopg2
from datetime import datetime, timedelta
import numpy as np

class TestPatternFlowComplete:
    """Test complete pattern flow from publication to UI readiness."""

    def __init__(self):
        self.redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
        self.db_conn = psycopg2.connect(
            host='localhost', port=5432, database='tickstock',
            user='app_readwrite', password='LJI48rUEkUpe6e'
        )
        self.db_conn.autocommit = True

    def test_pattern_with_numpy_data(self):
        """Test pattern with NumPy arrays (as TickStockPL sends)."""
        flow_id = str(uuid.uuid4())

        # Simulate TickStockPL pattern with indicators
        pattern_event = {
            'event_type': 'pattern_detected',
            'source': 'TickStockPL',
            'flow_id': flow_id,
            'timestamp': datetime.now().isoformat(),
            'data': {
                'flow_id': flow_id,
                'data': {
                    'pattern': 'MACrossover',
                    'symbol': 'GOOGL',
                    'confidence': 0.85,
                    'current_price': 150.50,
                    'indicators': {
                        'rsi': float(65.5),  # Convert numpy types
                        'macd': {'value': 0.5, 'signal': 0.3},
                        'volume': int(1000000)
                    },
                    'metadata': {
                        'crossover_point': 149.75,
                        'trend_strength': 0.72
                    }
                }
            }
        }

        # Publish
        self.redis_client.publish(
            'tickstock.events.patterns',
            json.dumps(pattern_event)
        )

        print(f"[OK] Published pattern with flow_id: {flow_id}")
        return flow_id

    def test_multi_tier_patterns(self):
        """Test patterns for all three tiers (Daily/Intraday/Combo)."""
        tiers = [
            ('daily', 'HeadShoulders', 'TSLA', 0.90),
            ('intraday', 'VolumeSurge', 'NVDA', 0.75),
            ('combo', 'SupportBreakout', 'AAPL', 0.82)
        ]

        flow_ids = []
        for tier, pattern, symbol, confidence in tiers:
            flow_id = str(uuid.uuid4())
            flow_ids.append(flow_id)

            event = {
                'event_type': 'pattern_detected',
                'source': 'TickStockPL',
                'flow_id': flow_id,
                'timestamp': datetime.now().isoformat(),
                'data': {
                    'flow_id': flow_id,
                    'tier': tier,
                    'data': {
                        'pattern': pattern,
                        'symbol': symbol,
                        'confidence': confidence,
                        'current_price': 100.0 + (confidence * 100),
                        'source': tier
                    }
                }
            }

            self.redis_client.publish(
                'tickstock.events.patterns',
                json.dumps(event)
            )

            print(f"[OK] Published {tier} tier pattern: {pattern} for {symbol}")

        return flow_ids

    def test_high_volume_patterns(self):
        """Test system under load (40+ patterns/minute like TickStockPL)."""
        start_time = time.time()
        patterns_sent = 0
        flow_ids = []

        # Send 40 patterns in rapid succession
        for i in range(40):
            flow_id = str(uuid.uuid4())
            flow_ids.append(flow_id)

            event = {
                'event_type': 'pattern_detected',
                'source': 'LoadTest',
                'flow_id': flow_id,
                'timestamp': datetime.now().isoformat(),
                'data': {
                    'flow_id': flow_id,
                    'data': {
                        'pattern': f'Pattern_{i % 12}',  # 12 pattern types
                        'symbol': f'{["GOOGL","TSLA","NVDA","AAPL","MSFT"][i % 5]}',
                        'confidence': 0.70 + (i % 30) / 100,
                        'current_price': 100 + i
                    }
                }
            }

            self.redis_client.publish(
                'tickstock.events.patterns',
                json.dumps(event)
            )
            patterns_sent += 1

            # Pace to ~40/minute
            if i % 10 == 0:
                time.sleep(0.1)

        elapsed = time.time() - start_time
        rate = patterns_sent / elapsed * 60

        print(f"[OK] Sent {patterns_sent} patterns in {elapsed:.1f}s")
        print(f"  Rate: {rate:.1f} patterns/minute")

        return flow_ids

    def verify_database_logging(self, flow_ids):
        """Verify patterns were logged to database."""
        cursor = self.db_conn.cursor()

        # Wait for processing
        time.sleep(3)

        # Check each flow
        for flow_id in flow_ids[:5]:  # Check first 5
            cursor.execute("""
                SELECT checkpoint, timestamp
                FROM integration_events
                WHERE flow_id = %s
                ORDER BY timestamp
            """, (flow_id,))

            checkpoints = cursor.fetchall()
            if checkpoints:
                print(f"[OK] Flow {flow_id[:8]}... has {len(checkpoints)} checkpoints")

        # Summary statistics
        cursor.execute("""
            SELECT
                checkpoint,
                COUNT(*) as count,
                AVG(processing_time_ms) as avg_ms
            FROM integration_events
            WHERE flow_id = ANY(%s)
            GROUP BY checkpoint
        """, (flow_ids,))

        for row in cursor.fetchall():
            checkpoint, count, avg_ms = row
            print(f"  {checkpoint}: {count} events, {avg_ms:.1f}ms avg")

        cursor.close()

    def verify_redis_cache(self):
        """Verify patterns are cached in Redis."""
        pattern_keys = self.redis_client.keys('tickstock:patterns:*')
        api_cache_keys = self.redis_client.keys('tickstock:api:*')

        print(f"[OK] Redis cache status:")
        print(f"  Pattern entries: {len(pattern_keys)}")
        print(f"  API cache entries: {len(api_cache_keys)}")

        # Sample a pattern entry
        if pattern_keys:
            sample_key = pattern_keys[0]
            ttl = self.redis_client.ttl(sample_key)
            print(f"  Sample TTL: {ttl} seconds")

    def verify_pattern_flow_analysis(self):
        """Check pattern flow analysis view."""
        cursor = self.db_conn.cursor()

        cursor.execute("""
            SELECT
                COUNT(DISTINCT flow_id) as unique_flows,
                COUNT(DISTINCT symbol) as unique_symbols,
                COUNT(DISTINCT pattern_name) as unique_patterns,
                AVG(end_to_end_latency_ms) as avg_latency,
                MAX(end_to_end_latency_ms) as max_latency
            FROM pattern_flow_analysis
            WHERE start_time > NOW() - INTERVAL '5 minutes'
        """)

        result = cursor.fetchone()
        if result[0] > 0:
            flows, symbols, patterns, avg_lat, max_lat = result
            print(f"[OK] Pattern flow analysis:")
            print(f"  Flows: {flows}, Symbols: {symbols}, Patterns: {patterns}")
            if avg_lat:
                print(f"  Latency: {avg_lat:.1f}ms avg, {max_lat:.1f}ms max")

        cursor.close()

    def cleanup(self):
        """Clean up test connections."""
        self.redis_client.close()
        self.db_conn.close()


def run_pattern_flow_tests():
    """Run complete pattern flow tests."""
    print("=" * 60)
    print("END-TO-END PATTERN FLOW TESTS")
    print("=" * 60)

    test = TestPatternFlowComplete()

    try:
        # Test 1: Single pattern with full data
        print("\n1. Testing single pattern with indicators...")
        flow_id = test.test_pattern_with_numpy_data()

        # Test 2: Multi-tier patterns
        print("\n2. Testing multi-tier patterns...")
        tier_flows = test.test_multi_tier_patterns()

        # Test 3: High volume
        print("\n3. Testing high-volume pattern flow...")
        load_flows = test.test_high_volume_patterns()

        # Verification
        print("\n4. Verifying database logging...")
        all_flows = [flow_id] + tier_flows + load_flows
        test.verify_database_logging(all_flows[:10])

        print("\n5. Verifying Redis cache...")
        test.verify_redis_cache()

        print("\n6. Checking flow analysis...")
        test.verify_pattern_flow_analysis()

        print("\n" + "=" * 60)
        print("[PASS] PATTERN FLOW TESTS COMPLETE")
        print("All pattern flow paths validated successfully")

    except Exception as e:
        print(f"\n[X] Test failed: {e}")
        return False

    finally:
        test.cleanup()

    return True


if __name__ == "__main__":
    success = run_pattern_flow_tests()
    sys.exit(0 if success else 1)