"""
Performance and scalability tests for Sprint 25 WebSocket infrastructure.

Sprint 25 Day 1 Performance Testing:
- Scalability validation for 500+ concurrent users
- <100ms WebSocket delivery times
- <5ms user filtering performance
- Memory usage validation (<1MB per 100 subscriptions)
- Concurrent connection handling
"""

import pytest
import time
import threading
import asyncio
import statistics
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, Any, List, Set
import sys
import gc
import redis
from flask_socketio import SocketIO

# Import components under test
from src.core.services.websocket_subscription_manager import UniversalWebSocketManager, UserSubscription, WebSocketMetrics
from src.core.services.tier_pattern_websocket_integration import TierPatternWebSocketIntegration, TierSubscriptionPreferences
from src.core.domain.events.tier_events import TierPatternEvent, MarketStateEvent, PatternTier, MarketRegime, EventPriority
from src.presentation.websocket.manager import WebSocketManager
from src.core.services.websocket_broadcaster import WebSocketBroadcaster


class PerformanceMetrics:
    """Helper class to track performance metrics during tests."""
    
    def __init__(self):
        self.subscription_times = []
        self.broadcast_times = []
        self.filtering_times = []
        self.delivery_counts = []
        self.memory_usage = []
        self.error_counts = 0
        self.start_time = time.time()
    
    def record_subscription_time(self, duration_ms: float):
        """Record subscription operation time."""
        self.subscription_times.append(duration_ms)
    
    def record_broadcast_time(self, duration_ms: float, delivery_count: int):
        """Record broadcast operation time and delivery count."""
        self.broadcast_times.append(duration_ms)
        self.delivery_counts.append(delivery_count)
    
    def record_filtering_time(self, duration_ms: float):
        """Record filtering operation time."""
        self.filtering_times.append(duration_ms)
    
    def record_memory_usage(self):
        """Record current memory usage."""
        self.memory_usage.append(sys.getsizeof(gc.get_objects()))
    
    def increment_errors(self):
        """Increment error count."""
        self.error_counts += 1
    
    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary statistics."""
        total_time = time.time() - self.start_time
        
        return {
            "total_duration_seconds": round(total_time, 2),
            "subscription_stats": {
                "count": len(self.subscription_times),
                "avg_ms": round(statistics.mean(self.subscription_times) if self.subscription_times else 0, 2),
                "p95_ms": round(statistics.quantiles(self.subscription_times, n=20)[18] if len(self.subscription_times) > 20 else 0, 2),
                "p99_ms": round(statistics.quantiles(self.subscription_times, n=100)[98] if len(self.subscription_times) > 100 else 0, 2),
                "max_ms": round(max(self.subscription_times) if self.subscription_times else 0, 2)
            },
            "broadcast_stats": {
                "count": len(self.broadcast_times),
                "avg_ms": round(statistics.mean(self.broadcast_times) if self.broadcast_times else 0, 2),
                "p95_ms": round(statistics.quantiles(self.broadcast_times, n=20)[18] if len(self.broadcast_times) > 20 else 0, 2),
                "p99_ms": round(statistics.quantiles(self.broadcast_times, n=100)[98] if len(self.broadcast_times) > 100 else 0, 2),
                "max_ms": round(max(self.broadcast_times) if self.broadcast_times else 0, 2),
                "total_deliveries": sum(self.delivery_counts)
            },
            "filtering_stats": {
                "count": len(self.filtering_times),
                "avg_ms": round(statistics.mean(self.filtering_times) if self.filtering_times else 0, 2),
                "max_ms": round(max(self.filtering_times) if self.filtering_times else 0, 2)
            },
            "error_count": self.error_counts,
            "throughput": {
                "subscriptions_per_second": round(len(self.subscription_times) / max(total_time, 1), 2),
                "broadcasts_per_second": round(len(self.broadcast_times) / max(total_time, 1), 2)
            }
        }


@pytest.mark.performance
class TestScalabilityTargets:
    """Test Sprint 25 scalability targets with realistic loads."""
    
    @pytest.fixture
    def performance_setup(self):
        """Set up components for performance testing with realistic mocking."""
        mock_socketio = Mock(spec=SocketIO)
        mock_socketio.server = Mock()
        mock_socketio.server.enter_room = Mock()
        mock_socketio.server.leave_room = Mock()
        
        # Mock emit to be fast but track calls
        emit_calls = []
        def mock_emit(*args, **kwargs):
            emit_calls.append((args, kwargs))
            return None
        mock_socketio.emit = Mock(side_effect=mock_emit)
        
        mock_redis = Mock(spec=redis.Redis)
        
        # Mock existing WebSocket manager to simulate real connections
        mock_existing_ws = Mock(spec=WebSocketManager)
        mock_existing_ws.is_user_connected.return_value = True
        mock_existing_ws.get_user_connections.return_value = {"conn1", "conn2"}
        mock_existing_ws.get_connected_users.return_value = set()
        
        mock_broadcaster = Mock(spec=WebSocketBroadcaster)
        
        # Create performance-optimized components
        ws_manager = UniversalWebSocketManager(
            socketio=mock_socketio,
            redis_client=mock_redis,
            existing_websocket_manager=mock_existing_ws,
            websocket_broadcaster=mock_broadcaster
        )
        
        tier_integration = TierPatternWebSocketIntegration(websocket_manager=ws_manager)
        
        return {
            "ws_manager": ws_manager,
            "tier_integration": tier_integration,
            "socketio": mock_socketio,
            "emit_calls": emit_calls,
            "metrics": PerformanceMetrics()
        }
    
    def test_500_concurrent_user_subscriptions(self, performance_setup):
        """Test target: Support 500+ concurrent user subscriptions."""
        setup = performance_setup
        ws_manager = setup["ws_manager"]
        metrics = setup["metrics"]
        
        user_count = 500
        symbols = ["AAPL", "TSLA", "MSFT", "GOOGL", "AMZN", "NFLX", "META", "NVDA", "AMD", "CRM"]
        patterns = ["BreakoutBO", "TrendReversal", "SurgePattern", "FlagPattern", "WedgePattern"]
        
        print(f"\nTesting {user_count} concurrent user subscriptions...")
        
        def subscribe_batch(start_idx: int, end_idx: int, results: List):
            """Subscribe a batch of users and record performance."""
            try:
                for i in range(start_idx, end_idx):
                    start_time = time.time()
                    
                    result = ws_manager.subscribe_user(
                        user_id=f"perf_user_{i}",
                        subscription_type="tier_patterns",
                        filters={
                            "symbols": [symbols[i % len(symbols)], symbols[(i + 1) % len(symbols)]],
                            "pattern_types": [patterns[i % len(patterns)]],
                            "confidence_min": 0.6 + (i % 4) * 0.1,
                            "tiers": ["daily", "intraday"][i % 2:i % 2 + 1]
                        }
                    )
                    
                    duration_ms = (time.time() - start_time) * 1000
                    results.append((result, duration_ms))
                    
            except Exception as e:
                results.append((False, f"Error: {e}"))
        
        # Use concurrent threads to simulate realistic load
        batch_size = 50
        threads = []
        all_results = []
        
        start_time = time.time()
        
        for start_idx in range(0, user_count, batch_size):
            end_idx = min(start_idx + batch_size, user_count)
            batch_results = []
            all_results.append(batch_results)
            
            thread = threading.Thread(
                target=subscribe_batch, 
                args=(start_idx, end_idx, batch_results)
            )
            threads.append(thread)
            thread.start()
        
        # Wait for all subscriptions to complete
        for thread in threads:
            thread.join()
        
        total_time = time.time() - start_time
        
        # Flatten results and analyze
        flat_results = [item for batch in all_results for item in batch]
        successful_subscriptions = [r for r in flat_results if isinstance(r[0], bool) and r[0]]
        failed_subscriptions = [r for r in flat_results if not (isinstance(r[0], bool) and r[0])]
        
        subscription_times = [r[1] for r in successful_subscriptions]
        
        # Performance assertions
        assert len(successful_subscriptions) >= 495, f"Only {len(successful_subscriptions)} subscriptions succeeded, target ≥495"
        assert len(failed_subscriptions) <= 5, f"Too many failed subscriptions: {len(failed_subscriptions)}, target ≤5"
        
        # Time performance
        avg_subscription_time = statistics.mean(subscription_times) if subscription_times else 0
        p99_subscription_time = statistics.quantiles(subscription_times, n=100)[98] if len(subscription_times) > 100 else 0
        
        assert total_time < 30.0, f"Total subscription time {total_time:.2f}s exceeded 30s limit"
        assert avg_subscription_time < 10.0, f"Average subscription time {avg_subscription_time:.2f}ms exceeded 10ms target"
        assert p99_subscription_time < 50.0, f"P99 subscription time {p99_subscription_time:.2f}ms exceeded 50ms target"
        
        # Memory efficiency
        final_user_count = len(ws_manager.user_subscriptions)
        memory_per_user = sys.getsizeof(ws_manager.user_subscriptions) / max(final_user_count, 1)
        
        assert memory_per_user < 10000, f"Memory per user {memory_per_user:.0f} bytes exceeded 10KB target"
        
        # System health
        health = ws_manager.get_health_status()
        assert health["status"] in ["healthy", "warning"], f"System unhealthy with {user_count} users: {health['status']}"
        
        print(f"✓ Successfully handled {len(successful_subscriptions)} subscriptions in {total_time:.2f}s")
        print(f"  Average subscription time: {avg_subscription_time:.2f}ms")
        print(f"  P99 subscription time: {p99_subscription_time:.2f}ms")
        print(f"  Memory per user: {memory_per_user:.0f} bytes")
    
    def test_sub_100ms_websocket_delivery(self, performance_setup):
        """Test target: <100ms WebSocket delivery times."""
        setup = performance_setup
        ws_manager = setup["ws_manager"]
        tier_integration = setup["tier_integration"]
        
        # Set up realistic number of subscribers
        user_count = 200
        symbols = ["AAPL", "TSLA", "MSFT", "GOOGL", "AMZN"]
        
        print(f"\nSetting up {user_count} users for delivery performance testing...")
        
        # Subscribe users with varying interests
        for i in range(user_count):
            preferences = TierSubscriptionPreferences(
                pattern_types=["BreakoutBO", "TrendReversal", "SurgePattern"][i % 3],
                symbols=[symbols[i % len(symbols)]],
                tiers=[PatternTier.DAILY, PatternTier.INTRADAY][i % 2:i % 2 + 1],
                confidence_min=0.6 + (i % 4) * 0.1
            )
            tier_integration.subscribe_user_to_tier_patterns(f"delivery_user_{i}", preferences)
        
        # Test broadcast performance with various event types
        test_events = []
        for i in range(50):  # 50 test events
            test_events.append(TierPatternEvent(
                pattern_type=["BreakoutBO", "TrendReversal", "SurgePattern"][i % 3],
                symbol=symbols[i % len(symbols)],
                tier=[PatternTier.DAILY, PatternTier.INTRADAY][i % 2],
                confidence=0.6 + (i % 4) * 0.1,
                event_id=f"delivery_perf_test_{i}",
                timestamp=datetime.now(),
                priority=[EventPriority.MEDIUM, EventPriority.HIGH, EventPriority.CRITICAL][i % 3]
            ))
        
        delivery_times = []
        delivery_counts = []
        
        print("Testing broadcast performance...")
        
        for i, event in enumerate(test_events):
            start_time = time.time()
            
            delivery_count = tier_integration.broadcast_tier_pattern_event(event)
            
            delivery_time_ms = (time.time() - start_time) * 1000
            delivery_times.append(delivery_time_ms)
            delivery_counts.append(delivery_count)
            
            # Add small delay to simulate realistic timing
            time.sleep(0.001)
        
        # Performance analysis
        avg_delivery_time = statistics.mean(delivery_times)
        p95_delivery_time = statistics.quantiles(delivery_times, n=20)[18] if len(delivery_times) >= 20 else max(delivery_times)
        p99_delivery_time = statistics.quantiles(delivery_times, n=100)[98] if len(delivery_times) >= 100 else max(delivery_times)
        max_delivery_time = max(delivery_times)
        total_deliveries = sum(delivery_counts)
        
        # Performance assertions
        assert avg_delivery_time < 100.0, f"Average delivery time {avg_delivery_time:.2f}ms exceeded 100ms target"
        assert p95_delivery_time < 100.0, f"P95 delivery time {p95_delivery_time:.2f}ms exceeded 100ms target"
        assert p99_delivery_time < 200.0, f"P99 delivery time {p99_delivery_time:.2f}ms exceeded 200ms limit"
        assert max_delivery_time < 500.0, f"Max delivery time {max_delivery_time:.2f}ms exceeded 500ms limit"
        
        # Delivery effectiveness
        assert total_deliveries > 0, "No events were delivered"
        avg_delivery_count = statistics.mean(delivery_counts)
        assert avg_delivery_count > 0.1, f"Very low average delivery count: {avg_delivery_count}"
        
        print(f"✓ Broadcast performance results:")
        print(f"  Average delivery time: {avg_delivery_time:.2f}ms")
        print(f"  P95 delivery time: {p95_delivery_time:.2f}ms")
        print(f"  P99 delivery time: {p99_delivery_time:.2f}ms")
        print(f"  Total events delivered: {total_deliveries}")
        print(f"  Average deliveries per event: {avg_delivery_count:.1f}")
    
    def test_sub_5ms_user_filtering(self, performance_setup):
        """Test target: <5ms user filtering for pattern events."""
        setup = performance_setup
        ws_manager = setup["ws_manager"]
        
        # Set up large number of diverse subscriptions for filtering test
        user_count = 1000
        symbols = [f"SYMBOL_{i}" for i in range(100)]  # 100 different symbols
        patterns = ["BreakoutBO", "TrendReversal", "SurgePattern", "FlagPattern", "WedgePattern"]
        
        print(f"\nSetting up {user_count} users for filtering performance testing...")
        
        # Create diverse subscription patterns
        for i in range(user_count):
            filters = {
                "symbols": [
                    symbols[i % len(symbols)],
                    symbols[(i + 1) % len(symbols)],
                    symbols[(i + 2) % len(symbols)]
                ],
                "pattern_types": [patterns[i % len(patterns)], patterns[(i + 1) % len(patterns)]],
                "confidence_min": 0.5 + (i % 5) * 0.1,
                "tiers": [["daily"], ["intraday"], ["daily", "intraday"]][i % 3],
                "priority_min": ["low", "medium", "high"][i % 3]
            }
            
            ws_manager.subscribe_user(f"filter_user_{i}", "tier_patterns", filters)
        
        # Test filtering performance with various criteria
        test_criteria = []
        for i in range(100):  # 100 different filtering scenarios
            test_criteria.append({
                "subscription_type": "tier_patterns",
                "symbol": symbols[i % len(symbols)],
                "pattern_type": patterns[i % len(patterns)],
                "tier": ["daily", "intraday"][i % 2],
                "confidence": 0.6 + (i % 4) * 0.1,
                "priority": ["medium", "high", "critical"][i % 3]
            })
        
        filtering_times = []
        match_counts = []
        
        print("Testing filtering performance...")
        
        for criteria in test_criteria:
            start_time = time.time()
            
            interested_users = ws_manager._find_interested_users(criteria)
            
            filtering_time_ms = (time.time() - start_time) * 1000
            filtering_times.append(filtering_time_ms)
            match_counts.append(len(interested_users))
        
        # Performance analysis
        avg_filtering_time = statistics.mean(filtering_times)
        p95_filtering_time = statistics.quantiles(filtering_times, n=20)[18] if len(filtering_times) >= 20 else max(filtering_times)
        p99_filtering_time = statistics.quantiles(filtering_times, n=100)[98] if len(filtering_times) >= 100 else max(filtering_times)
        max_filtering_time = max(filtering_times)
        
        # Performance assertions
        assert avg_filtering_time < 5.0, f"Average filtering time {avg_filtering_time:.3f}ms exceeded 5ms target"
        assert p95_filtering_time < 5.0, f"P95 filtering time {p95_filtering_time:.3f}ms exceeded 5ms target"
        assert p99_filtering_time < 10.0, f"P99 filtering time {p99_filtering_time:.3f}ms exceeded 10ms limit"
        assert max_filtering_time < 50.0, f"Max filtering time {max_filtering_time:.3f}ms exceeded 50ms limit"
        
        # Filtering effectiveness
        avg_matches = statistics.mean(match_counts)
        assert avg_matches > 0.1, f"Very low average match count: {avg_matches}"
        
        print(f"✓ Filtering performance results:")
        print(f"  Average filtering time: {avg_filtering_time:.3f}ms")
        print(f"  P95 filtering time: {p95_filtering_time:.3f}ms")
        print(f"  P99 filtering time: {p99_filtering_time:.3f}ms")
        print(f"  Average matches per criteria: {avg_matches:.1f}")
    
    def test_memory_usage_scalability(self, performance_setup):
        """Test target: <1MB memory per 100 active subscriptions."""
        setup = performance_setup
        ws_manager = setup["ws_manager"]
        tier_integration = setup["tier_integration"]
        
        print("\nTesting memory usage scalability...")
        
        # Measure initial memory footprint
        gc.collect()
        initial_memory = sys.getsizeof(ws_manager.user_subscriptions)
        initial_tier_memory = sys.getsizeof(tier_integration.stats)
        
        # Add subscriptions in batches and measure memory growth
        batch_sizes = [100, 200, 300, 400, 500]
        memory_measurements = []
        
        for target_users in batch_sizes:
            current_users = len(ws_manager.user_subscriptions)
            users_to_add = target_users - current_users
            
            if users_to_add > 0:
                for i in range(current_users, target_users):
                    preferences = TierSubscriptionPreferences(
                        pattern_types=[f"Pattern_{i % 10}"],
                        symbols=[f"SYMBOL_{i % 50}"],
                        tiers=[PatternTier.DAILY, PatternTier.INTRADAY][i % 2:i % 2 + 1],
                        confidence_min=0.7,
                        max_events_per_hour=25 + i % 100
                    )
                    tier_integration.subscribe_user_to_tier_patterns(f"memory_user_{i}", preferences)
            
            # Force garbage collection and measure memory
            gc.collect()
            current_memory = sys.getsizeof(ws_manager.user_subscriptions)
            current_tier_memory = sys.getsizeof(tier_integration.stats)
            
            memory_measurements.append({
                "user_count": target_users,
                "ws_manager_memory": current_memory,
                "tier_integration_memory": current_tier_memory,
                "total_memory": current_memory + current_tier_memory
            })
        
        # Analyze memory growth
        for measurement in memory_measurements:
            user_count = measurement["user_count"]
            total_memory = measurement["total_memory"]
            memory_per_100_users = (total_memory / user_count) * 100
            
            print(f"  {user_count} users: {total_memory:,} bytes total, {memory_per_100_users:,.0f} bytes per 100 users")
            
            # Memory efficiency target: <1MB (1,048,576 bytes) per 100 users
            assert memory_per_100_users < 1048576, (
                f"Memory usage {memory_per_100_users:,.0f} bytes per 100 users "
                f"exceeded 1MB target at {user_count} users"
            )
        
        # Test memory stability under load
        print("  Testing memory stability under broadcast load...")
        
        initial_total = memory_measurements[-1]["total_memory"]
        
        # Broadcast many events
        for i in range(100):
            event = TierPatternEvent(
                pattern_type=f"Pattern_{i % 10}",
                symbol=f"SYMBOL_{i % 50}",
                tier=PatternTier.DAILY,
                confidence=0.8,
                event_id=f"memory_test_{i}",
                timestamp=datetime.now()
            )
            tier_integration.broadcast_tier_pattern_event(event)
        
        # Check memory after broadcasts
        gc.collect()
        final_ws_memory = sys.getsizeof(ws_manager.user_subscriptions)
        final_tier_memory = sys.getsizeof(tier_integration.stats)
        final_total = final_ws_memory + final_tier_memory
        
        memory_growth = final_total - initial_total
        memory_growth_percent = (memory_growth / initial_total) * 100 if initial_total > 0 else 0
        
        # Memory growth should be minimal after broadcasts
        assert memory_growth < 1048576, f"Memory grew by {memory_growth:,} bytes after broadcasts, should be <1MB"
        assert memory_growth_percent < 10, f"Memory grew by {memory_growth_percent:.1f}%, should be <10%"
        
        print(f"✓ Memory usage validation passed")
        print(f"  Final memory usage: {final_total:,} bytes for {len(ws_manager.user_subscriptions)} users")
        print(f"  Memory growth after broadcasts: {memory_growth:,} bytes ({memory_growth_percent:.1f}%)")
    
    def test_concurrent_connection_handling(self, performance_setup):
        """Test concurrent connection handling under load."""
        setup = performance_setup
        ws_manager = setup["ws_manager"]
        
        print("\nTesting concurrent connection handling...")
        
        connection_results = []
        errors = []
        
        def connection_worker(worker_id: int, connection_count: int):
            """Worker thread for handling connections."""
            worker_results = []
            try:
                for i in range(connection_count):
                    user_id = f"conn_worker_{worker_id}_user_{i}"
                    connection_id = f"conn_{worker_id}_{i}"
                    
                    # Connection lifecycle
                    start_time = time.time()
                    
                    # Subscribe
                    subscribe_success = ws_manager.subscribe_user(user_id, "tier_patterns", {
                        "symbols": [f"SYMBOL_{i % 10}"],
                        "confidence_min": 0.7
                    })
                    
                    # Handle connection
                    ws_manager.handle_user_connection(user_id, connection_id)
                    
                    # Simulate some activity time
                    time.sleep(0.001)
                    
                    # Handle disconnection
                    ws_manager.handle_user_disconnection(user_id, connection_id)
                    
                    # Unsubscribe
                    unsubscribe_success = ws_manager.unsubscribe_user(user_id)
                    
                    duration_ms = (time.time() - start_time) * 1000
                    
                    worker_results.append({
                        "user_id": user_id,
                        "subscribe_success": subscribe_success,
                        "unsubscribe_success": unsubscribe_success,
                        "duration_ms": duration_ms
                    })
                    
            except Exception as e:
                errors.append(f"Worker {worker_id}: {str(e)}")
            
            connection_results.append(worker_results)
        
        # Test with multiple concurrent workers
        worker_count = 10
        connections_per_worker = 20
        total_connections = worker_count * connections_per_worker
        
        print(f"  Testing {total_connections} concurrent connections across {worker_count} workers...")
        
        start_time = time.time()
        
        threads = []
        for worker_id in range(worker_count):
            thread = threading.Thread(
                target=connection_worker,
                args=(worker_id, connections_per_worker)
            )
            threads.append(thread)
            thread.start()
        
        # Wait for all workers to complete
        for thread in threads:
            thread.join()
        
        total_time = time.time() - start_time
        
        # Analyze results
        all_results = [result for worker_results in connection_results for result in worker_results]
        successful_operations = [r for r in all_results if r["subscribe_success"] and r["unsubscribe_success"]]
        failed_operations = [r for r in all_results if not (r["subscribe_success"] and r["unsubscribe_success"])]
        
        operation_times = [r["duration_ms"] for r in successful_operations]
        
        # Performance assertions
        assert len(errors) == 0, f"Errors during concurrent connections: {errors}"
        
        success_rate = len(successful_operations) / len(all_results) * 100 if all_results else 0
        assert success_rate >= 95.0, f"Success rate {success_rate:.1f}% below 95% target"
        
        avg_operation_time = statistics.mean(operation_times) if operation_times else 0
        max_operation_time = max(operation_times) if operation_times else 0
        
        assert total_time < 30.0, f"Total concurrent connection test took {total_time:.2f}s, should be <30s"
        assert avg_operation_time < 100.0, f"Average operation time {avg_operation_time:.2f}ms exceeded 100ms target"
        assert max_operation_time < 1000.0, f"Max operation time {max_operation_time:.2f}ms exceeded 1s limit"
        
        # System should be clean after all operations
        remaining_subscriptions = len(ws_manager.user_subscriptions)
        assert remaining_subscriptions <= 5, f"Too many remaining subscriptions: {remaining_subscriptions}"
        
        print(f"✓ Concurrent connection handling results:")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Success rate: {success_rate:.1f}%")
        print(f"  Average operation time: {avg_operation_time:.2f}ms")
        print(f"  Remaining subscriptions: {remaining_subscriptions}")
    
    def test_sustained_load_performance(self, performance_setup):
        """Test system performance under sustained load."""
        setup = performance_setup
        ws_manager = setup["ws_manager"]
        tier_integration = setup["tier_integration"]
        
        print("\nTesting sustained load performance...")
        
        # Set up baseline users
        baseline_users = 100
        for i in range(baseline_users):
            preferences = TierSubscriptionPreferences(
                pattern_types=["BreakoutBO", "TrendReversal"][i % 2],
                symbols=[f"SUSTAINED_SYMBOL_{i % 20}"],
                tiers=[PatternTier.DAILY],
                confidence_min=0.7
            )
            tier_integration.subscribe_user_to_tier_patterns(f"sustained_user_{i}", preferences)
        
        # Sustained load test parameters
        test_duration_seconds = 60  # 1 minute test
        events_per_second = 10
        total_events = test_duration_seconds * events_per_second
        
        print(f"  Running sustained load: {events_per_second} events/sec for {test_duration_seconds}s...")
        
        performance_samples = []
        start_time = time.time()
        
        for i in range(total_events):
            sample_start = time.time()
            
            # Create and broadcast event
            event = TierPatternEvent(
                pattern_type=["BreakoutBO", "TrendReversal"][i % 2],
                symbol=f"SUSTAINED_SYMBOL_{i % 20}",
                tier=PatternTier.DAILY,
                confidence=0.7 + (i % 3) * 0.1,
                event_id=f"sustained_test_{i}",
                timestamp=datetime.now()
            )
            
            delivery_count = tier_integration.broadcast_tier_pattern_event(event)
            
            broadcast_time = (time.time() - sample_start) * 1000
            
            performance_samples.append({
                "event_index": i,
                "broadcast_time_ms": broadcast_time,
                "delivery_count": delivery_count,
                "filtering_time_ms": ws_manager.metrics.filtering_latency_ms
            })
            
            # Maintain target rate
            elapsed_time = time.time() - start_time
            expected_time = (i + 1) / events_per_second
            sleep_time = expected_time - elapsed_time
            if sleep_time > 0:
                time.sleep(sleep_time)
        
        total_test_time = time.time() - start_time
        
        # Analyze sustained performance
        broadcast_times = [s["broadcast_time_ms"] for s in performance_samples]
        delivery_counts = [s["delivery_count"] for s in performance_samples]
        filtering_times = [s["filtering_time_ms"] for s in performance_samples]
        
        # Performance degradation analysis
        first_quarter = performance_samples[:total_events//4]
        last_quarter = performance_samples[-total_events//4:]
        
        first_quarter_avg = statistics.mean([s["broadcast_time_ms"] for s in first_quarter])
        last_quarter_avg = statistics.mean([s["broadcast_time_ms"] for s in last_quarter])
        
        performance_degradation = ((last_quarter_avg - first_quarter_avg) / first_quarter_avg * 100 
                                 if first_quarter_avg > 0 else 0)
        
        # Performance assertions
        avg_broadcast_time = statistics.mean(broadcast_times)
        p95_broadcast_time = statistics.quantiles(broadcast_times, n=20)[18] if len(broadcast_times) >= 20 else max(broadcast_times)
        total_deliveries = sum(delivery_counts)
        avg_filtering_time = statistics.mean(filtering_times)
        
        assert total_test_time < test_duration_seconds * 1.2, f"Test took {total_test_time:.1f}s, should be ≤{test_duration_seconds * 1.2}s"
        assert avg_broadcast_time < 100.0, f"Average broadcast time {avg_broadcast_time:.2f}ms exceeded 100ms during sustained load"
        assert p95_broadcast_time < 200.0, f"P95 broadcast time {p95_broadcast_time:.2f}ms exceeded 200ms during sustained load"
        assert avg_filtering_time < 10.0, f"Average filtering time {avg_filtering_time:.3f}ms exceeded 10ms during sustained load"
        assert performance_degradation < 50.0, f"Performance degraded by {performance_degradation:.1f}%, should be <50%"
        assert total_deliveries > total_events * 0.5, f"Low delivery rate: {total_deliveries} deliveries for {total_events} events"
        
        # System health after sustained load
        final_health = tier_integration.get_health_status()
        assert final_health["status"] in ["healthy", "warning"], f"System unhealthy after sustained load: {final_health['status']}"
        
        print(f"✓ Sustained load performance results:")
        print(f"  Test duration: {total_test_time:.1f}s")
        print(f"  Average broadcast time: {avg_broadcast_time:.2f}ms")
        print(f"  P95 broadcast time: {p95_broadcast_time:.2f}ms")
        print(f"  Performance degradation: {performance_degradation:.1f}%")
        print(f"  Total deliveries: {total_deliveries:,}")
        print(f"  Final system status: {final_health['status']}")


@pytest.mark.performance
class TestPerformanceBenchmarks:
    """Additional performance benchmarks and stress tests."""
    
    def test_memory_leak_detection(self):
        """Test for memory leaks over extended operation."""
        mock_socketio = Mock(spec=SocketIO)
        mock_socketio.server = Mock()
        mock_socketio.emit = Mock()
        
        mock_redis = Mock(spec=redis.Redis)
        mock_existing_ws = Mock(spec=WebSocketManager)
        mock_existing_ws.is_user_connected.return_value = True
        mock_existing_ws.get_user_connections.return_value = {"conn1"}
        mock_existing_ws.get_connected_users.return_value = set()
        mock_broadcaster = Mock(spec=WebSocketBroadcaster)
        
        ws_manager = UniversalWebSocketManager(
            socketio=mock_socketio, redis_client=mock_redis,
            existing_websocket_manager=mock_existing_ws, websocket_broadcaster=mock_broadcaster
        )
        
        print("\nTesting for memory leaks...")
        
        # Baseline memory measurement
        gc.collect()
        baseline_memory = sys.getsizeof(ws_manager.user_subscriptions)
        
        memory_measurements = []
        cycles = 10
        operations_per_cycle = 100
        
        for cycle in range(cycles):
            cycle_start_memory = sys.getsizeof(ws_manager.user_subscriptions)
            
            # Perform many subscribe/unsubscribe operations
            for i in range(operations_per_cycle):
                user_id = f"leak_test_user_{i}"
                
                # Subscribe
                ws_manager.subscribe_user(user_id, "tier_patterns", {
                    "symbols": [f"SYMBOL_{i % 10}"],
                    "confidence_min": 0.7
                })
                
                # Immediate unsubscribe
                ws_manager.unsubscribe_user(user_id)
            
            # Force garbage collection and measure
            gc.collect()
            cycle_end_memory = sys.getsizeof(ws_manager.user_subscriptions)
            
            memory_measurements.append({
                "cycle": cycle,
                "start_memory": cycle_start_memory,
                "end_memory": cycle_end_memory,
                "growth": cycle_end_memory - cycle_start_memory
            })
        
        # Analyze memory growth trend
        total_growth = memory_measurements[-1]["end_memory"] - baseline_memory
        max_cycle_growth = max(m["growth"] for m in memory_measurements)
        avg_cycle_growth = statistics.mean(m["growth"] for m in memory_measurements)
        
        print(f"  Memory leak analysis over {cycles} cycles:")
        print(f"  Baseline memory: {baseline_memory:,} bytes")
        print(f"  Final memory: {memory_measurements[-1]['end_memory']:,} bytes")
        print(f"  Total growth: {total_growth:,} bytes")
        print(f"  Max cycle growth: {max_cycle_growth:,} bytes")
        print(f"  Average cycle growth: {avg_cycle_growth:,.0f} bytes")
        
        # Memory leak assertions
        assert total_growth < 100000, f"Possible memory leak: {total_growth:,} bytes total growth"
        assert max_cycle_growth < 50000, f"Excessive cycle growth: {max_cycle_growth:,} bytes in single cycle"
        assert abs(avg_cycle_growth) < 1000, f"Consistent memory growth: {avg_cycle_growth:.0f} bytes per cycle"
        
        print("✓ No significant memory leaks detected")
    
    def test_extreme_filtering_scenarios(self):
        """Test filtering performance with extreme scenarios."""
        mock_socketio = Mock(spec=SocketIO)
        mock_socketio.server = Mock()
        mock_socketio.emit = Mock()
        
        mock_redis = Mock(spec=redis.Redis)
        mock_existing_ws = Mock(spec=WebSocketManager)
        mock_existing_ws.is_user_connected.return_value = True
        mock_existing_ws.get_user_connections.return_value = {"conn1"}
        mock_existing_ws.get_connected_users.return_value = set()
        mock_broadcaster = Mock(spec=WebSocketBroadcaster)
        
        ws_manager = UniversalWebSocketManager(
            socketio=mock_socketio, redis_client=mock_redis,
            existing_websocket_manager=mock_existing_ws, websocket_broadcaster=mock_broadcaster
        )
        
        print("\nTesting extreme filtering scenarios...")
        
        # Scenario 1: Many users with very specific filters
        specific_filter_users = 500
        for i in range(specific_filter_users):
            ws_manager.subscribe_user(f"specific_user_{i}", "tier_patterns", {
                "symbols": [f"VERY_SPECIFIC_SYMBOL_{i}"],  # Each user has unique symbol
                "pattern_types": [f"VERY_SPECIFIC_PATTERN_{i}"],  # Each user has unique pattern
                "confidence_min": 0.95,  # Very high confidence
                "priority_min": "critical"
            })
        
        # Scenario 2: Many users with very broad filters  
        broad_filter_users = 200
        for i in range(broad_filter_users):
            ws_manager.subscribe_user(f"broad_user_{i}", "tier_patterns", {
                # No symbol filter - accepts all
                # No pattern filter - accepts all
                "confidence_min": 0.1,  # Very low confidence - accepts most
                "priority_min": "low"   # Low priority - accepts all
            })
        
        # Test filtering performance with no matches (specific scenario)
        start_time = time.time()
        no_match_users = ws_manager._find_interested_users({
            "subscription_type": "tier_patterns",
            "symbol": "NONEXISTENT_SYMBOL",
            "pattern_type": "NONEXISTENT_PATTERN"
        })
        no_match_time = (time.time() - start_time) * 1000
        
        # Test filtering performance with all matches (broad scenario)  
        start_time = time.time()
        all_match_users = ws_manager._find_interested_users({
            "subscription_type": "tier_patterns",
            # Minimal criteria - should match broad users
        })
        all_match_time = (time.time() - start_time) * 1000
        
        # Test filtering performance with complex criteria
        start_time = time.time()
        complex_match_users = ws_manager._find_interested_users({
            "subscription_type": "tier_patterns",
            "symbol": "VERY_SPECIFIC_SYMBOL_100",  # Should match one specific user
            "pattern_type": "VERY_SPECIFIC_PATTERN_100",
            "confidence": 0.99,
            "priority": "critical"
        })
        complex_match_time = (time.time() - start_time) * 1000
        
        total_users = specific_filter_users + broad_filter_users
        
        print(f"  Filtering performance with {total_users} users:")
        print(f"  No match scenario: {no_match_time:.3f}ms, found {len(no_match_users)} users")
        print(f"  All match scenario: {all_match_time:.3f}ms, found {len(all_match_users)} users")
        print(f"  Complex match scenario: {complex_match_time:.3f}ms, found {len(complex_match_users)} users")
        
        # Performance assertions even with extreme scenarios
        assert no_match_time < 20.0, f"No-match filtering took {no_match_time:.3f}ms, should be <20ms"
        assert all_match_time < 50.0, f"All-match filtering took {all_match_time:.3f}ms, should be <50ms"
        assert complex_match_time < 20.0, f"Complex-match filtering took {complex_match_time:.3f}ms, should be <20ms"
        
        # Correctness assertions
        assert len(no_match_users) == 0, "Should have no matches for nonexistent criteria"
        assert len(all_match_users) >= broad_filter_users, "Should match at least all broad filter users"
        assert len(complex_match_users) <= 1 + broad_filter_users, "Should match specific user + broad users"
        
        print("✓ Extreme filtering scenarios passed performance targets")