#!/usr/bin/env python3
"""
Redis Integration Fix Test
Tests the fallback pattern detector and improved Redis integration.

This script simulates market data and tests the fallback pattern detection
system when TickStockPL is unavailable.

Author: Redis Integration Specialist
Date: 2025-09-12
"""

import sys
import os
import time
import json
import threading
import random
import redis
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.services.fallback_pattern_detector import FallbackPatternDetector, TickData

def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'='*50}")
    print(f" {title}")
    print(f"{'='*50}")

class MockSocketIO:
    """Mock SocketIO for testing."""
    
    def __init__(self):
        self.emitted_events = []
    
    def emit(self, event, data, namespace=None):
        """Mock emit function."""
        self.emitted_events.append({
            'event': event,
            'data': data,
            'namespace': namespace,
            'timestamp': time.time()
        })
        print(f"WEBSOCKET: Emitted {event} - {data.get('type', 'unknown')}")

class RedisIntegrationTest:
    """Test Redis integration fixes."""
    
    def __init__(self):
        self.redis_client = None
        self.mock_socketio = MockSocketIO()
        self.fallback_detector = None
        
    def setup(self) -> bool:
        """Setup test environment."""
        try:
            # Connect to Redis
            self.redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
            self.redis_client.ping()
            
            print("OK Redis connection established")
            
            # Clear any existing TickStockPL heartbeat
            self.redis_client.delete('tickstock:producer:heartbeat')
            print("OK Cleared TickStockPL heartbeat (simulating offline state)")
            
            # Initialize fallback detector
            config = {'FALLBACK_DETECTION_ENABLED': True}
            self.fallback_detector = FallbackPatternDetector(
                self.redis_client, self.mock_socketio, config
            )
            
            if self.fallback_detector.start():
                print("OK Fallback pattern detector started")
                return True
            else:
                print("ERR Failed to start fallback detector")
                return False
                
        except Exception as e:
            print(f"ERR Setup failed: {e}")
            return False
    
    def test_pattern_detection(self):
        """Test pattern detection with simulated market data."""
        print_section("TESTING FALLBACK PATTERN DETECTION")
        
        # Test symbols
        symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA']
        
        print("Feeding simulated market data...")
        
        # Generate simulated market ticks
        for i in range(100):
            for symbol in symbols:
                # Simulate realistic market data
                base_price = {'AAPL': 150, 'GOOGL': 2800, 'MSFT': 300, 'TSLA': 200}[symbol]
                
                # Add some price variation
                price_change = random.uniform(-2, 2)
                price = base_price + price_change
                
                # Simulate volume patterns
                if i % 10 == 0:  # High volume surge every 10 ticks
                    volume = random.randint(5000, 10000)
                else:
                    volume = random.randint(100, 1000)
                
                # Add tick to fallback detector
                self.fallback_detector.add_market_tick(symbol, price, volume)
            
            time.sleep(0.1)  # Small delay between ticks
            
            # Print progress
            if i % 20 == 0:
                stats = self.fallback_detector.get_stats()
                print(f"   Processed {i} ticks - Patterns detected: {stats['patterns_detected']}")
        
        # Final stats
        final_stats = self.fallback_detector.get_stats()
        print(f"\nTEST COMPLETE:")
        print(f"  Ticks processed: 400")
        print(f"  Patterns detected: {final_stats['patterns_detected']}")
        print(f"  Symbols monitored: {final_stats['symbols_monitored']}")
        print(f"  Average detection latency: {final_stats['detection_latency_ms']:.2f}ms")
        
        # Check WebSocket events
        pattern_events = [e for e in self.mock_socketio.emitted_events if e['event'] == 'pattern_alert']
        print(f"  WebSocket pattern alerts: {len(pattern_events)}")
        
        return final_stats['patterns_detected'] > 0
    
    def test_redis_pub_sub(self):
        """Test Redis pub-sub message flow."""
        print_section("TESTING REDIS PUB-SUB INTEGRATION")
        
        received_messages = []
        
        def redis_subscriber():
            """Background Redis subscriber."""
            pubsub = self.redis_client.pubsub()
            pubsub.subscribe('tickstock.events.patterns')
            
            print("SUBSCRIBER: Listening for Redis messages...")
            
            for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        data = json.loads(message['data'])
                        received_messages.append(data)
                        print(f"REDIS: Received pattern event - {data.get('pattern')} on {data.get('symbol')}")
                    except json.JSONDecodeError:
                        print(f"REDIS: Invalid JSON: {message['data']}")
            
            pubsub.unsubscribe()
            pubsub.close()
        
        # Start Redis subscriber
        subscriber_thread = threading.Thread(target=redis_subscriber, daemon=True)
        subscriber_thread.start()
        
        # Wait for subscriber to be ready
        time.sleep(1)
        
        # Generate some market data to trigger patterns
        print("Generating high-volume market data...")
        
        for i in range(20):
            # Generate high-volume ticks to trigger patterns
            self.fallback_detector.add_market_tick('TEST', 100 + i, 10000)  # High volume
            time.sleep(0.2)
        
        # Wait for processing
        time.sleep(3)
        
        print(f"\nRESULTS:")
        print(f"  Redis messages received: {len(received_messages)}")
        
        if received_messages:
            print(f"  Sample pattern event:")
            sample = received_messages[0]
            print(f"    Pattern: {sample.get('pattern')}")
            print(f"    Symbol: {sample.get('symbol')}")
            print(f"    Confidence: {sample.get('confidence')}")
            print(f"    Source: {sample.get('source')}")
        
        return len(received_messages) > 0
    
    def test_performance(self):
        """Test performance under load."""
        print_section("TESTING PERFORMANCE")
        
        start_time = time.time()
        initial_stats = self.fallback_detector.get_stats()
        
        # Generate high-frequency market data
        print("Generating high-frequency market data (500 ticks/second)...")
        
        total_ticks = 0
        for batch in range(10):  # 10 batches
            batch_start = time.time()
            
            for i in range(50):  # 50 ticks per batch
                symbol = random.choice(['AAPL', 'GOOGL', 'MSFT'])
                price = 100 + random.uniform(-5, 5)
                volume = random.randint(100, 2000)
                
                self.fallback_detector.add_market_tick(symbol, price, volume)
                total_ticks += 1
            
            batch_time = time.time() - batch_start
            time.sleep(max(0, 0.1 - batch_time))  # Target 100ms per batch
        
        total_time = time.time() - start_time
        final_stats = self.fallback_detector.get_stats()
        
        patterns_detected = final_stats['patterns_detected'] - initial_stats['patterns_detected']
        
        print(f"\nPERFORMANCE RESULTS:")
        print(f"  Total ticks processed: {total_ticks}")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Throughput: {total_ticks / total_time:.1f} ticks/second")
        print(f"  Patterns detected: {patterns_detected}")
        print(f"  Detection rate: {patterns_detected / total_ticks * 100:.2f}%")
        print(f"  Average detection latency: {final_stats['detection_latency_ms']:.2f}ms")
        
        # Performance requirements check
        throughput_ok = (total_ticks / total_time) > 100  # >100 ticks/second
        latency_ok = final_stats['detection_latency_ms'] < 10  # <10ms detection
        
        print(f"\nPERFORMANCE EVALUATION:")
        print(f"  Throughput requirement (>100 tps): {'PASS' if throughput_ok else 'FAIL'}")
        print(f"  Latency requirement (<10ms): {'PASS' if latency_ok else 'FAIL'}")
        
        return throughput_ok and latency_ok
    
    def cleanup(self):
        """Cleanup test environment."""
        if self.fallback_detector:
            self.fallback_detector.stop()
            print("OK Fallback detector stopped")
    
    def run_tests(self):
        """Run all integration tests."""
        print_section("REDIS INTEGRATION FIX TESTING")
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if not self.setup():
            print("FATAL: Setup failed")
            return False
        
        try:
            # Test 1: Pattern Detection
            pattern_test_passed = self.test_pattern_detection()
            
            # Test 2: Redis Pub-Sub
            pubsub_test_passed = self.test_redis_pub_sub()
            
            # Test 3: Performance
            performance_test_passed = self.test_performance()
            
            # Results summary
            print_section("TEST RESULTS SUMMARY")
            
            tests = [
                ("Pattern Detection", pattern_test_passed),
                ("Redis Pub-Sub Integration", pubsub_test_passed),
                ("Performance Under Load", performance_test_passed),
            ]
            
            passed_tests = 0
            for test_name, passed in tests:
                status = "PASS" if passed else "FAIL"
                print(f"  {test_name}: {status}")
                if passed:
                    passed_tests += 1
            
            print(f"\nOVERALL RESULT: {passed_tests}/{len(tests)} tests passed")
            
            if passed_tests == len(tests):
                print("OK All tests passed - Redis integration fix successful!")
                return True
            else:
                print("ERR Some tests failed - Redis integration needs attention")
                return False
            
        finally:
            self.cleanup()

def main():
    """Main test execution."""
    test = RedisIntegrationTest()
    
    try:
        success = test.run_tests()
        
        if success:
            print("\nOK REDIS INTEGRATION FIX TESTING COMPLETED SUCCESSFULLY")
            sys.exit(0)
        else:
            print("\nERR REDIS INTEGRATION FIX TESTING FAILED")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\nWARN Tests interrupted by user")
        test.cleanup()
        sys.exit(1)
    except Exception as e:
        print(f"\nERR FATAL ERROR during testing: {e}")
        test.cleanup()
        sys.exit(1)

if __name__ == '__main__':
    main()