"""
Test UniversalWebSocketManager and ScalableBroadcaster Integration Performance
Sprint 25 Day 3 Tests: Integration performance validation for complete broadcasting system.

Tests integration performance including:
- End-to-end delivery from UniversalWebSocketManager to ScalableBroadcaster to SocketIO
- Index → Broadcast flow with efficient user filtering and batched delivery  
- 500+ concurrent users with full system performance validation
- Pattern event broadcasting with real-time batching optimization
- Performance optimization effectiveness across integrated systems
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import Mock

import pytest

from src.core.services.websocket_subscription_manager import (
    UniversalWebSocketManager,
)


class TestIntegrationSetup:
    """Test setup and fixtures for integration testing."""

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client."""
        redis_mock = Mock()
        redis_mock.get = Mock(return_value=None)
        redis_mock.set = Mock(return_value=True)
        redis_mock.publish = Mock(return_value=1)
        return redis_mock

    @pytest.fixture
    def mock_socketio(self):
        """Mock SocketIO with call tracking."""
        socketio = Mock()
        socketio.emit = Mock()
        socketio.server = Mock()
        socketio.server.enter_room = Mock()
        socketio.server.leave_room = Mock()
        return socketio

    @pytest.fixture
    def mock_existing_ws_manager(self):
        """Mock existing WebSocket manager."""
        ws_manager = Mock()
        ws_manager.is_user_connected = Mock(return_value=True)
        ws_manager.get_user_connections = Mock(return_value=['conn_123'])
        ws_manager.get_connected_users = Mock(return_value=['user1', 'user2', 'user3'])
        return ws_manager

    @pytest.fixture
    def mock_ws_broadcaster(self):
        """Mock WebSocket broadcaster."""
        broadcaster = Mock()
        broadcaster.broadcast_to_users = Mock(return_value=True)
        return broadcaster

    @pytest.fixture
    def universal_ws_manager(self, mock_socketio, mock_redis,
                           mock_existing_ws_manager, mock_ws_broadcaster):
        """Create UniversalWebSocketManager for testing."""
        return UniversalWebSocketManager(
            socketio=mock_socketio,
            redis_client=mock_redis,
            existing_websocket_manager=mock_existing_ws_manager,
            websocket_broadcaster=mock_ws_broadcaster
        )


class TestEndToEndIntegrationPerformance:
    """Test end-to-end integration performance."""

    def test_subscription_to_broadcast_workflow(self, universal_ws_manager):
        """Test complete workflow from subscription to broadcast delivery."""
        # Phase 1: Create user subscriptions
        users = [f'integration_user_{i}' for i in range(20)]
        subscription_times = []

        for user_id in users:
            start_time = time.time()

            success = universal_ws_manager.subscribe_user(
                user_id=user_id,
                subscription_type='tier_patterns',
                filters={
                    'pattern_types': ['BreakoutBO', 'TrendReversal'],
                    'symbols': ['AAPL', 'TSLA', 'GOOGL'],
                    'confidence_min': 0.7
                }
            )

            subscription_time = time.time() - start_time
            subscription_times.append(subscription_time)
            assert success == True

        # Subscription performance validation
        avg_subscription_time = sum(subscription_times) / len(subscription_times)
        max_subscription_time = max(subscription_times)

        assert avg_subscription_time < 0.010  # Less than 10ms average
        assert max_subscription_time < 0.050  # Less than 50ms maximum

        # Phase 2: Broadcast events to subscribers
        broadcast_times = []
        event_scenarios = [
            ('tier_pattern', {'pattern': 'BreakoutBO', 'symbol': 'AAPL', 'confidence': 0.85}),
            ('tier_pattern', {'pattern': 'TrendReversal', 'symbol': 'TSLA', 'confidence': 0.92}),
            ('tier_pattern', {'pattern': 'BreakoutBO', 'symbol': 'GOOGL', 'confidence': 0.78}),
        ]

        for event_type, event_data in event_scenarios:
            start_time = time.time()

            delivered_count = universal_ws_manager.broadcast_event(
                event_type=event_type,
                event_data=event_data,
                targeting_criteria={
                    'subscription_type': 'tier_patterns',
                    'pattern_type': event_data.get('pattern'),
                    'symbol': event_data.get('symbol')
                }
            )

            broadcast_time = time.time() - start_time
            broadcast_times.append(broadcast_time)

            assert delivered_count > 0  # Should deliver to some users

        # Broadcast performance validation
        avg_broadcast_time = sum(broadcast_times) / len(broadcast_times)
        max_broadcast_time = max(broadcast_times)

        assert avg_broadcast_time < 0.050  # Less than 50ms average
        assert max_broadcast_time < 0.100  # Less than 100ms maximum

        # Phase 3: Verify integration statistics
        stats = universal_ws_manager.get_subscription_stats()

        assert stats['total_users'] == len(users)
        assert stats['events_broadcast'] == len(event_scenarios)
        assert stats['avg_broadcast_latency_ms'] < 100.0
        assert stats['broadcast_success_rate'] > 90.0

    def test_index_to_broadcast_flow_efficiency(self, universal_ws_manager):
        """Test efficiency of indexing system to broadcast system flow."""
        # Create diverse subscription base
        subscription_patterns = [
            ('tier_patterns', {'pattern_types': ['BreakoutBO'], 'symbols': ['AAPL'], 'confidence_min': 0.8}),
            ('tier_patterns', {'pattern_types': ['TrendReversal'], 'symbols': ['TSLA'], 'confidence_min': 0.7}),
            ('market_insights', {'symbols': ['AAPL', 'TSLA'], 'event_types': ['earnings', 'splits']}),
            ('price_alerts', {'symbols': ['GOOGL'], 'price_thresholds': [2800.0, 2900.0]}),
        ]

        # Create 100 users with varying subscriptions
        for i in range(100):
            user_id = f'flow_user_{i}'
            sub_type, filters = subscription_patterns[i % len(subscription_patterns)]

            universal_ws_manager.subscribe_user(user_id, sub_type, filters)

        # Benchmark filtering and broadcasting flow
        test_events = [
            ('tier_pattern', {'pattern': 'BreakoutBO', 'symbol': 'AAPL', 'confidence': 0.85},
             {'subscription_type': 'tier_patterns', 'pattern_type': 'BreakoutBO', 'symbol': 'AAPL'}),
            ('market_insight', {'symbol': 'TSLA', 'event_type': 'earnings', 'impact': 'high'},
             {'subscription_type': 'market_insights', 'symbol': 'TSLA', 'event_type': 'earnings'}),
            ('price_alert', {'symbol': 'GOOGL', 'price': 2850.0, 'threshold_crossed': 2800.0},
             {'subscription_type': 'price_alerts', 'symbol': 'GOOGL'}),
        ]

        flow_performance = []

        for event_type, event_data, criteria in test_events:
            start_time = time.time()

            # This triggers: indexing lookup → user filtering → batch creation → delivery queuing
            delivered_count = universal_ws_manager.broadcast_event(event_type, event_data, criteria)

            flow_time = time.time() - start_time
            flow_performance.append((flow_time, delivered_count))

        # Analyze flow performance
        avg_flow_time = sum(time for time, _ in flow_performance) / len(flow_performance)
        total_deliveries = sum(count for _, count in flow_performance)

        # Performance targets
        assert avg_flow_time < 0.020  # Less than 20ms average for complete flow
        assert total_deliveries > 0  # Should deliver to relevant users

        # Check integration statistics
        stats = universal_ws_manager.get_subscription_stats()
        assert stats['index_avg_lookup_ms'] < 5.0  # Indexing under 5ms
        assert stats['broadcast_avg_latency_ms'] < 100.0  # Broadcasting under 100ms
        assert stats['avg_filtering_latency_ms'] < 10.0  # Filtering under 10ms

    def test_concurrent_subscription_and_broadcast_performance(self, universal_ws_manager):
        """Test performance under concurrent subscription and broadcast operations."""

        def subscription_worker(user_base_start: int, user_count: int) -> list[float]:
            """Worker for creating subscriptions."""
            subscription_times = []

            for i in range(user_count):
                user_id = f'concurrent_user_{user_base_start + i}'
                start_time = time.time()

                success = universal_ws_manager.subscribe_user(
                    user_id=user_id,
                    subscription_type='tier_patterns',
                    filters={
                        'pattern_types': ['BreakoutBO', 'Support', 'Resistance'],
                        'symbols': ['AAPL', 'TSLA', 'GOOGL', 'MSFT', 'AMZN'],
                        'confidence_min': 0.6
                    }
                )

                subscription_times.append(time.time() - start_time)
                assert success == True

            return subscription_times

        def broadcast_worker(event_count: int) -> list[float]:
            """Worker for broadcasting events."""
            broadcast_times = []

            symbols = ['AAPL', 'TSLA', 'GOOGL', 'MSFT', 'AMZN']
            patterns = ['BreakoutBO', 'Support', 'Resistance', 'TrendReversal']

            for i in range(event_count):
                symbol = symbols[i % len(symbols)]
                pattern = patterns[i % len(patterns)]

                start_time = time.time()

                delivered_count = universal_ws_manager.broadcast_event(
                    event_type='tier_pattern',
                    event_data={
                        'pattern': pattern,
                        'symbol': symbol,
                        'confidence': 0.7 + (i % 3) * 0.1,
                        'timestamp': time.time()
                    },
                    targeting_criteria={
                        'subscription_type': 'tier_patterns',
                        'pattern_type': pattern,
                        'symbol': symbol
                    }
                )

                broadcast_times.append(time.time() - start_time)

            return broadcast_times

        # Run concurrent operations
        with ThreadPoolExecutor(max_workers=8) as executor:
            # Start subscription workers
            subscription_futures = [
                executor.submit(subscription_worker, i * 25, 25)
                for i in range(4)
            ]  # 4 workers × 25 users = 100 users

            # Start broadcast workers
            broadcast_futures = [
                executor.submit(broadcast_worker, 20)
                for _ in range(2)
            ]  # 2 workers × 20 events = 40 events

            # Collect results
            all_subscription_times = []
            all_broadcast_times = []

            for future in as_completed(subscription_futures):
                all_subscription_times.extend(future.result())

            for future in as_completed(broadcast_futures):
                all_broadcast_times.extend(future.result())

        # Analyze concurrent performance
        avg_subscription_time = sum(all_subscription_times) / len(all_subscription_times)
        max_subscription_time = max(all_subscription_times)

        avg_broadcast_time = sum(all_broadcast_times) / len(all_broadcast_times)
        max_broadcast_time = max(all_broadcast_times)

        # Performance assertions under concurrency
        assert avg_subscription_time < 0.020  # Less than 20ms average
        assert max_subscription_time < 0.100  # Less than 100ms maximum
        assert avg_broadcast_time < 0.050   # Less than 50ms average
        assert max_broadcast_time < 0.200   # Less than 200ms maximum

        # Verify final state
        stats = universal_ws_manager.get_subscription_stats()
        assert stats['total_users'] == 100
        assert stats['events_broadcast'] == 40


class TestHighVolumeIntegrationPerformance:
    """Test high-volume integration performance scenarios."""

    def test_500_concurrent_users_broadcasting(self, universal_ws_manager):
        """Test system performance with 500+ concurrent users."""
        # Phase 1: Create 500 user subscriptions
        print("Creating 500 user subscriptions...")
        subscription_start = time.time()

        # Batch subscription creation for efficiency
        batch_size = 50
        total_users = 500

        def create_user_batch(batch_start: int, batch_size: int):
            """Create a batch of user subscriptions."""
            batch_times = []

            for i in range(batch_size):
                user_id = f'scale_user_{batch_start + i}'

                # Vary subscription types for realism
                sub_types = ['tier_patterns', 'market_insights', 'price_alerts', 'trend_analysis']
                sub_type = sub_types[i % len(sub_types)]

                filters = {
                    'symbols': ['AAPL', 'TSLA', 'GOOGL', 'MSFT', 'AMZN'][:(i % 5) + 1],
                    'confidence_min': 0.5 + (i % 5) * 0.1
                }

                start_time = time.time()
                success = universal_ws_manager.subscribe_user(user_id, sub_type, filters)
                batch_times.append(time.time() - start_time)

                assert success == True

            return batch_times

        # Create subscriptions in parallel batches
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(create_user_batch, i, batch_size)
                for i in range(0, total_users, batch_size)
            ]

            all_subscription_times = []
            for future in as_completed(futures):
                all_subscription_times.extend(future.result())

        subscription_duration = time.time() - subscription_start

        # Phase 2: High-volume broadcasting
        print("Starting high-volume broadcasting...")
        broadcast_start = time.time()

        def broadcast_batch(event_count: int, batch_id: int):
            """Broadcast a batch of events."""
            batch_times = []
            delivered_counts = []

            symbols = ['AAPL', 'TSLA', 'GOOGL', 'MSFT', 'AMZN']
            event_types = ['tier_pattern', 'market_insight', 'price_alert', 'trend_analysis']

            for i in range(event_count):
                event_type = event_types[i % len(event_types)]
                symbol = symbols[i % len(symbols)]

                start_time = time.time()

                delivered_count = universal_ws_manager.broadcast_event(
                    event_type=event_type,
                    event_data={
                        'symbol': symbol,
                        'batch_id': batch_id,
                        'sequence': i,
                        'confidence': 0.6 + (i % 4) * 0.1,
                        'timestamp': time.time()
                    },
                    targeting_criteria={
                        'subscription_type': event_type.replace('_', '_'),
                        'symbol': symbol
                    }
                )

                batch_times.append(time.time() - start_time)
                delivered_counts.append(delivered_count)

            return batch_times, delivered_counts

        # Broadcast events in parallel
        events_per_batch = 25
        num_broadcast_batches = 8  # 8 × 25 = 200 events total

        with ThreadPoolExecutor(max_workers=8) as executor:
            broadcast_futures = [
                executor.submit(broadcast_batch, events_per_batch, i)
                for i in range(num_broadcast_batches)
            ]

            all_broadcast_times = []
            all_delivered_counts = []

            for future in as_completed(broadcast_futures):
                times, counts = future.result()
                all_broadcast_times.extend(times)
                all_delivered_counts.extend(counts)

        broadcast_duration = time.time() - broadcast_start

        # Phase 3: Performance analysis
        print("Analyzing performance results...")

        # Subscription performance
        avg_subscription_time = sum(all_subscription_times) / len(all_subscription_times)
        max_subscription_time = max(all_subscription_times)
        subscriptions_per_second = len(all_subscription_times) / subscription_duration

        # Broadcasting performance
        avg_broadcast_time = sum(all_broadcast_times) / len(all_broadcast_times)
        max_broadcast_time = max(all_broadcast_times)
        events_per_second = len(all_broadcast_times) / broadcast_duration
        total_deliveries = sum(all_delivered_counts)
        avg_deliveries_per_event = total_deliveries / len(all_delivered_counts) if all_delivered_counts else 0

        # Performance assertions for 500+ users
        assert avg_subscription_time < 0.050  # Less than 50ms average subscription time
        assert max_subscription_time < 0.200  # Less than 200ms maximum subscription time
        assert subscriptions_per_second > 100  # More than 100 subscriptions/sec

        assert avg_broadcast_time < 0.100     # Less than 100ms average broadcast time
        assert max_broadcast_time < 0.500     # Less than 500ms maximum broadcast time
        assert events_per_second > 20         # More than 20 events/sec
        assert avg_deliveries_per_event > 10  # Average delivery to 10+ users per event

        # System statistics validation
        stats = universal_ws_manager.get_subscription_stats()
        assert stats['total_users'] >= 500
        assert stats['events_broadcast'] >= 200
        assert stats['broadcast_avg_latency_ms'] < 200.0

        print("Performance Results:")
        print(f"  Subscriptions: {avg_subscription_time*1000:.1f}ms avg, {subscriptions_per_second:.0f}/sec")
        print(f"  Broadcasting: {avg_broadcast_time*1000:.1f}ms avg, {events_per_second:.0f}/sec")
        print(f"  Deliveries: {avg_deliveries_per_event:.1f} users/event, {total_deliveries} total")

    def test_sustained_load_performance_degradation(self, universal_ws_manager):
        """Test performance degradation under sustained load."""
        # Create baseline user set
        baseline_users = 100
        for i in range(baseline_users):
            universal_ws_manager.subscribe_user(
                user_id=f'sustained_user_{i}',
                subscription_type='tier_patterns',
                filters={'symbols': ['AAPL', 'TSLA'], 'confidence_min': 0.7}
            )

        # Measure performance across multiple phases
        phases = [
            (50, "Low load"),      # 50 events
            (150, "Medium load"),  # 150 events
            (300, "High load"),    # 300 events
            (100, "Recovery")      # 100 events
        ]

        phase_results = []

        for event_count, phase_name in phases:
            print(f"Testing {phase_name} phase with {event_count} events...")

            phase_start = time.time()
            broadcast_times = []
            delivered_counts = []

            for i in range(event_count):
                start_time = time.time()

                delivered_count = universal_ws_manager.broadcast_event(
                    event_type='tier_pattern',
                    event_data={
                        'pattern': 'BreakoutBO',
                        'symbol': 'AAPL' if i % 2 == 0 else 'TSLA',
                        'confidence': 0.75 + (i % 20) * 0.01,
                        'phase': phase_name,
                        'sequence': i
                    },
                    targeting_criteria={
                        'subscription_type': 'tier_patterns',
                        'symbol': 'AAPL' if i % 2 == 0 else 'TSLA'
                    }
                )

                broadcast_time = time.time() - start_time
                broadcast_times.append(broadcast_time)
                delivered_counts.append(delivered_count)

                # Small delay to simulate realistic load
                time.sleep(0.001)

            phase_duration = time.time() - phase_start

            # Calculate phase metrics
            avg_broadcast_time = sum(broadcast_times) / len(broadcast_times)
            max_broadcast_time = max(broadcast_times)
            events_per_second = event_count / phase_duration
            total_deliveries = sum(delivered_counts)

            phase_results.append({
                'phase': phase_name,
                'avg_broadcast_time': avg_broadcast_time,
                'max_broadcast_time': max_broadcast_time,
                'events_per_second': events_per_second,
                'total_deliveries': total_deliveries
            })

            print(f"  {phase_name}: {avg_broadcast_time*1000:.1f}ms avg, {events_per_second:.0f} events/sec")

        # Analyze performance degradation
        baseline_performance = phase_results[0]['avg_broadcast_time']

        for phase_result in phase_results[1:]:
            performance_ratio = phase_result['avg_broadcast_time'] / baseline_performance

            # Performance should not degrade significantly
            if phase_result['phase'] != 'Recovery':
                assert performance_ratio < 3.0  # Less than 3x degradation
            else:
                assert performance_ratio < 2.0  # Recovery should be better

        # System should handle sustained load without failures
        for phase_result in phase_results:
            assert phase_result['avg_broadcast_time'] < 0.200  # Less than 200ms
            assert phase_result['total_deliveries'] > 0       # Should deliver events


class TestIntegrationOptimizationPerformance:
    """Test performance optimization effectiveness in integrated system."""

    def test_integrated_system_optimization_impact(self, universal_ws_manager):
        """Test performance optimization impact across integrated systems."""
        # Create realistic load
        for i in range(200):
            user_id = f'optimization_user_{i}'
            sub_type = ['tier_patterns', 'market_insights'][i % 2]

            universal_ws_manager.subscribe_user(
                user_id=user_id,
                subscription_type=sub_type,
                filters={
                    'symbols': ['AAPL', 'TSLA', 'GOOGL', 'MSFT'][:(i % 4) + 1],
                    'confidence_min': 0.6 + (i % 4) * 0.1
                }
            )

        # Generate load before optimization
        pre_optimization_times = []
        for i in range(50):
            start_time = time.time()

            universal_ws_manager.broadcast_event(
                event_type='tier_pattern',
                event_data={
                    'pattern': 'BreakoutBO',
                    'symbol': ['AAPL', 'TSLA'][i % 2],
                    'confidence': 0.8,
                    'pre_optimization': True
                },
                targeting_criteria={'subscription_type': 'tier_patterns'}
            )

            pre_optimization_times.append(time.time() - start_time)

        pre_optimization_avg = sum(pre_optimization_times) / len(pre_optimization_times)

        # Run system optimization
        optimization_start = time.time()
        optimization_result = universal_ws_manager.optimize_performance()
        optimization_duration = time.time() - optimization_start

        # Generate load after optimization
        time.sleep(0.1)  # Brief delay for optimization effects

        post_optimization_times = []
        for i in range(50):
            start_time = time.time()

            universal_ws_manager.broadcast_event(
                event_type='tier_pattern',
                event_data={
                    'pattern': 'BreakoutBO',
                    'symbol': ['AAPL', 'TSLA'][i % 2],
                    'confidence': 0.8,
                    'post_optimization': True
                },
                targeting_criteria={'subscription_type': 'tier_patterns'}
            )

            post_optimization_times.append(time.time() - start_time)

        post_optimization_avg = sum(post_optimization_times) / len(post_optimization_times)

        # Analyze optimization effectiveness
        performance_improvement = (pre_optimization_avg - post_optimization_avg) / pre_optimization_avg

        # Optimization should complete quickly
        assert optimization_duration < 1.0  # Less than 1 second

        # Should have valid optimization results
        assert isinstance(optimization_result, dict)
        assert 'index_optimization' in optimization_result
        assert 'broadcast_optimization' in optimization_result
        assert 'current_performance' in optimization_result

        # Performance should improve or at least not degrade significantly
        assert performance_improvement > -0.5  # No more than 50% performance loss

        # Ideally, we'd see improvement, but system may already be optimized
        if performance_improvement > 0:
            print(f"Performance improved by {performance_improvement*100:.1f}%")
        else:
            print(f"Performance maintained within {abs(performance_improvement)*100:.1f}% of baseline")

        # Check final system health
        health = universal_ws_manager.get_health_status()
        assert health['status'] in ['healthy', 'warning']  # Should not be in error state
        assert health['stats']['broadcast_avg_latency_ms'] < 200.0


if __name__ == '__main__':
    # Example of running integration performance tests
    pytest.main([__file__ + "::TestHighVolumeIntegrationPerformance::test_500_concurrent_users_broadcasting", "-v", "-s"])
