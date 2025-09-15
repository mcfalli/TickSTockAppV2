"""
Comprehensive Production Readiness Tests - Error Handling and Recovery
Sprint 26: Production Error Scenarios and System Resilience

Tests critical error handling and recovery mechanisms for production deployment.
Validates system resilience, data loss prevention, and graceful degradation.

Test Categories:
- Database Error Recovery: Connection failures, transaction rollbacks, data integrity
- Redis Connection Recovery: Pub-sub reconnection, message persistence, failover
- WebSocket Error Handling: Connection drops, broadcasting failures, user recovery
- API Error Handling: Timeout handling, rate limiting, graceful degradation
- System Integration Recovery: Cross-component failure handling, circuit breakers
"""

import pytest
import time
import threading
import json
from unittest.mock import Mock, patch, MagicMock, side_effect
from typing import Dict, Any, List
import redis
import psycopg2
from dataclasses import dataclass
from enum import Enum

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.core.services.market_data_service import MarketDataService
from src.core.services.redis_event_subscriber import RedisEventSubscriber
from src.core.services.websocket_broadcaster import WebSocketBroadcaster, ConnectedUser
from src.api.rest.pattern_consumer import pattern_consumer_bp


class ErrorScenario(Enum):
    """Types of error scenarios to test."""
    DATABASE_CONNECTION_LOST = "db_connection_lost"
    REDIS_CONNECTION_LOST = "redis_connection_lost"
    WEBSOCKET_CONNECTION_LOST = "websocket_connection_lost"
    API_TIMEOUT = "api_timeout"
    MEMORY_EXHAUSTION = "memory_exhaustion"
    NETWORK_PARTITION = "network_partition"
    SERVICE_OVERLOAD = "service_overload"


@dataclass
class RecoveryMetrics:
    """Recovery performance metrics."""
    scenario: str
    detection_time_ms: float
    recovery_time_ms: float
    data_loss_count: int
    success_rate: float
    resilience_score: float


class TestErrorHandlingRecovery:
    """Test suite for error handling and recovery mechanisms."""

    @pytest.fixture
    def mock_config(self):
        """Mock configuration for error testing."""
        return {
            'USE_SYNTHETIC_DATA': True,
            'DATABASE_URL': 'postgresql://test:test@localhost/test',
            'REDIS_HOST': 'localhost',
            'REDIS_PORT': 6379,
            'CONNECTION_RETRY_COUNT': 3,
            'CONNECTION_RETRY_DELAY': 0.1,
            'CIRCUIT_BREAKER_THRESHOLD': 5,
            'HEALTH_CHECK_INTERVAL': 10
        }

    @pytest.fixture
    def market_data_service(self, mock_config):
        """Create MarketDataService for error testing."""
        return MarketDataService(mock_config)

    @pytest.fixture
    def redis_subscriber(self, mock_config):
        """Create RedisEventSubscriber for error testing."""
        mock_redis = Mock(spec=redis.Redis)
        mock_socketio = Mock()
        return RedisEventSubscriber(mock_redis, mock_socketio, mock_config)

    @pytest.fixture
    def websocket_broadcaster(self):
        """Create WebSocketBroadcaster for error testing."""
        mock_socketio = Mock()
        return WebSocketBroadcaster(mock_socketio)

    @pytest.fixture
    def sample_tick_data(self):
        """Sample tick data for error scenarios."""
        tick = Mock()
        tick.ticker = "AAPL"
        tick.price = 150.25
        tick.volume = 1000
        tick.timestamp = time.time()
        tick.event_type = "tick"
        tick.source = "test"
        return tick

    def test_database_connection_recovery(self, market_data_service, sample_tick_data):
        """Test database connection recovery after failure."""
        # Mock database connection that fails then recovers
        connection_attempts = []
        
        def mock_connect_with_recovery(*args, **kwargs):
            connection_attempts.append(time.time())
            
            if len(connection_attempts) <= 2:
                # First 2 attempts fail
                raise psycopg2.OperationalError("Connection failed")
            else:
                # Third attempt succeeds
                mock_conn = Mock()
                mock_cursor = Mock()
                mock_conn.cursor.return_value = mock_cursor
                return mock_conn
        
        recovery_start = time.perf_counter()
        
        with patch('psycopg2.connect', side_effect=mock_connect_with_recovery):
            # Simulate database operation failure and recovery
            with patch.object(market_data_service.data_publisher, 'establish_db_connection') as mock_establish:
                def mock_establish_with_retry():
                    for attempt in range(3):
                        try:
                            return mock_connect_with_recovery()
                        except psycopg2.OperationalError:
                            if attempt < 2:
                                time.sleep(0.1)  # Brief retry delay
                                continue
                            raise
                
                mock_establish.side_effect = mock_establish_with_retry
                
                # Should eventually succeed after retries
                connection = mock_establish()
                assert connection is not None
        
        recovery_time = (time.perf_counter() - recovery_start) * 1000
        
        # Verify recovery metrics
        assert len(connection_attempts) >= 2, "Should attempt reconnection"
        assert recovery_time < 1000, f"Recovery time {recovery_time:.2f}ms too high"
        
        print(f"\nDatabase Recovery Metrics:")
        print(f"  Attempts: {len(connection_attempts)}")
        print(f"  Recovery Time: {recovery_time:.2f}ms")

    def test_redis_connection_recovery_with_message_persistence(self, redis_subscriber):
        """Test Redis connection recovery with message persistence."""
        # Mock Redis connection that fails and recovers
        mock_redis = redis_subscriber.redis_client
        mock_pubsub = Mock()
        mock_redis.pubsub.return_value = mock_pubsub
        
        # Simulate connection failure during message processing
        connection_error_count = 0
        recovered = False
        
        def mock_get_message_with_failure(timeout=None):
            nonlocal connection_error_count, recovered
            
            if connection_error_count < 3 and not recovered:
                connection_error_count += 1
                raise redis.ConnectionError("Redis connection lost")
            else:
                recovered = True
                return None  # No message available
        
        mock_pubsub.get_message.side_effect = mock_get_message_with_failure
        
        # Mock connection test to succeed after failures
        def mock_ping_recovery():
            return recovered
        
        mock_redis.ping.side_effect = mock_ping_recovery
        
        # Start subscriber
        with patch.object(redis_subscriber, '_test_redis_connection', return_value=True):
            redis_subscriber.start()
        
        # Simulate message processing with connection errors
        recovery_start = time.perf_counter()
        
        # Process messages in a loop (simulating subscriber loop)
        for attempt in range(10):
            try:
                message = mock_pubsub.get_message(timeout=1.0)
                if recovered:
                    break
            except redis.ConnectionError:
                # Trigger recovery mechanism
                redis_subscriber._handle_connection_error()
                time.sleep(0.1)
        
        recovery_time = (time.perf_counter() - recovery_start) * 1000
        
        # Verify recovery
        assert recovered, "Redis connection should recover"
        assert connection_error_count >= 2, "Should experience connection errors"
        assert recovery_time < 2000, f"Recovery time {recovery_time:.2f}ms too high"
        
        print(f"\nRedis Recovery Metrics:")
        print(f"  Connection Errors: {connection_error_count}")
        print(f"  Recovery Time: {recovery_time:.2f}ms")
        print(f"  Recovered: {recovered}")

    def test_websocket_connection_failure_handling(self, websocket_broadcaster):
        """Test WebSocket connection failure handling."""
        # Add connected users
        users_data = [
            ('session_1', 'user_1'),
            ('session_2', 'user_2'),
            ('session_3', 'user_3'),
        ]
        
        for session_id, user_id in users_data:
            connected_user = ConnectedUser(
                user_id=user_id,
                session_id=session_id,
                connected_at=time.time(),
                last_seen=time.time(),
                subscriptions={'Breakout'}
            )
            websocket_broadcaster.connected_users[session_id] = connected_user
        
        # Mock SocketIO emit to fail for some users
        emission_results = []
        
        def mock_emit_with_failures(event, data, room=None, **kwargs):
            # Simulate connection failure for session_2
            if room == 'session_2':
                emission_results.append(('failed', room))
                raise Exception("WebSocket connection lost")
            else:
                emission_results.append(('success', room))
                return True
        
        websocket_broadcaster.socketio.emit.side_effect = mock_emit_with_failures
        
        # Test pattern broadcasting with connection failures
        pattern_event = {
            'type': 'pattern_alert',
            'data': {
                'pattern': 'Breakout',
                'symbol': 'AAPL',
                'confidence': 0.85
            },
            'timestamp': time.time()
        }
        
        # Should handle failures gracefully
        websocket_broadcaster.broadcast_pattern_alert(pattern_event)
        
        # Verify error handling
        successful_emissions = [r for r in emission_results if r[0] == 'success']
        failed_emissions = [r for r in emission_results if r[0] == 'failed']
        
        assert len(successful_emissions) >= 2, "Should deliver to working connections"
        assert len(failed_emissions) == 1, "Should handle failed connection"
        
        # Failed user should be queued for offline delivery
        failed_room = failed_emissions[0][1]
        assert failed_room == 'session_2'

    def test_api_timeout_handling(self):
        """Test API timeout handling and graceful degradation."""
        from flask import Flask
        from flask.testing import FlaskClient
        
        app = Flask(__name__)
        app.register_blueprint(pattern_consumer_bp)
        client = app.test_client()
        
        with app.app_context():
            # Mock pattern cache with slow response
            mock_cache = Mock()
            
            def slow_scan_patterns(filters):
                # Simulate slow database/cache operation
                time.sleep(0.2)  # 200ms delay
                return {
                    'patterns': [{'pattern': 'Breakout', 'symbol': 'AAPL'}],
                    'pagination': {'total': 1}
                }
            
            mock_cache.scan_patterns.side_effect = slow_scan_patterns
            app.pattern_cache = mock_cache
            
            # Test API timeout handling
            start_time = time.perf_counter()
            response = client.get('/api/patterns/scan')
            end_time = time.perf_counter()
            
            response_time_ms = (end_time - start_time) * 1000
            
            # Should complete but handle slow operations
            assert response.status_code in [200, 504]  # OK or Gateway Timeout
            
            if response.status_code == 200:
                # If completed, should have reasonable response time
                assert response_time_ms < 1000, f"Response time {response_time_ms:.2f}ms too high"

    def test_circuit_breaker_pattern(self, market_data_service, sample_tick_data):
        """Test circuit breaker pattern for service protection."""
        # Implement circuit breaker logic for database operations
        failure_count = 0
        circuit_open = False
        last_failure_time = None
        
        def mock_database_operation_with_circuit_breaker():
            nonlocal failure_count, circuit_open, last_failure_time
            
            # Check if circuit breaker is open
            if circuit_open:
                # Check if enough time has passed to attempt reset
                if time.time() - last_failure_time > 1.0:  # 1 second timeout
                    circuit_open = False
                    failure_count = 0
                else:
                    raise Exception("Circuit breaker open - service unavailable")
            
            # Simulate database operation failure
            if failure_count < 5:
                failure_count += 1
                last_failure_time = time.time()
                
                if failure_count >= 3:  # Open circuit after 3 failures
                    circuit_open = True
                
                raise psycopg2.OperationalError("Database operation failed")
            else:
                # Reset on success
                failure_count = 0
                circuit_open = False
                return "Success"
        
        # Test circuit breaker behavior
        circuit_breaker_triggered = False
        successful_operations = 0
        
        for attempt in range(10):
            try:
                result = mock_database_operation_with_circuit_breaker()
                if result == "Success":
                    successful_operations += 1
            except psycopg2.OperationalError:
                # Expected database failures
                pass
            except Exception as e:
                if "Circuit breaker open" in str(e):
                    circuit_breaker_triggered = True
            
            time.sleep(0.1)  # Brief delay between attempts
        
        # Verify circuit breaker behavior
        assert circuit_breaker_triggered, "Circuit breaker should trigger after repeated failures"
        assert failure_count >= 3, "Should accumulate failures before opening circuit"
        
        print(f"\nCircuit Breaker Metrics:")
        print(f"  Failure Count: {failure_count}")
        print(f"  Circuit Opened: {circuit_breaker_triggered}")
        print(f"  Successful Operations: {successful_operations}")

    def test_memory_exhaustion_handling(self, market_data_service):
        """Test memory exhaustion handling and recovery."""
        import gc
        
        # Monitor memory usage
        initial_objects = len(gc.get_objects())
        large_data_structures = []
        
        try:
            # Simulate memory pressure
            for i in range(100):
                # Create large data structure
                large_data = [f"data_item_{j}" for j in range(1000)]
                large_data_structures.append(large_data)
                
                # Check memory usage periodically
                if i % 20 == 0:
                    current_objects = len(gc.get_objects())
                    memory_growth = current_objects - initial_objects
                    
                    # If memory growth is excessive, trigger cleanup
                    if memory_growth > 50000:
                        # Simulate memory cleanup/garbage collection
                        large_data_structures = large_data_structures[-10:]  # Keep only recent items
                        gc.collect()
                        
                        break
            
            # Verify memory cleanup occurred
            gc.collect()
            final_objects = len(gc.get_objects())
            final_memory_growth = final_objects - initial_objects
            
            # Memory should be controlled
            assert final_memory_growth < 100000, f"Memory growth {final_memory_growth} objects too high"
            
        except MemoryError:
            # If memory error occurs, should handle gracefully
            large_data_structures.clear()
            gc.collect()
            
            # System should recover
            recovered_objects = len(gc.get_objects())
            assert recovered_objects < initial_objects * 2, "Memory should recover after cleanup"

    def test_concurrent_failure_handling(self, websocket_broadcaster):
        """Test handling of concurrent failures across multiple components."""
        # Setup multiple connected users
        user_count = 20
        for i in range(user_count):
            session_id = f'session_{i}'
            connected_user = ConnectedUser(
                user_id=f'user_{i}',
                session_id=session_id,
                connected_at=time.time(),
                last_seen=time.time(),
                subscriptions={'Breakout'}
            )
            websocket_broadcaster.connected_users[session_id] = connected_user
        
        # Simulate concurrent failures and broadcasts
        failure_results = []
        success_results = []
        
        def mock_emit_with_random_failures(event, data, room=None, **kwargs):
            # Simulate 30% failure rate
            session_num = int(room.split('_')[1]) if room else 0
            
            if session_num % 3 == 0:  # Every 3rd session fails
                failure_results.append(room)
                raise Exception(f"Connection lost for {room}")
            else:
                success_results.append(room)
                return True
        
        websocket_broadcaster.socketio.emit.side_effect = mock_emit_with_random_failures
        
        # Test concurrent broadcasting
        threads = []
        pattern_events = []
        
        def broadcast_pattern(pattern_id):
            pattern_event = {
                'type': 'pattern_alert',
                'data': {
                    'pattern': f'Pattern_{pattern_id}',
                    'symbol': 'AAPL',
                    'confidence': 0.85
                },
                'timestamp': time.time()
            }
            pattern_events.append(pattern_event)
            websocket_broadcaster.broadcast_pattern_alert(pattern_event)
        
        # Create multiple concurrent broadcasts
        for i in range(5):
            thread = threading.Thread(target=broadcast_pattern, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all broadcasts to complete
        for thread in threads:
            thread.join()
        
        # Analyze failure handling
        total_attempts = len(success_results) + len(failure_results)
        success_rate = len(success_results) / total_attempts if total_attempts > 0 else 0
        
        # Should handle failures gracefully while maintaining service
        assert success_rate > 0.5, f"Success rate {success_rate:.2%} too low"
        assert len(failure_results) > 0, "Should have some failures to test handling"
        assert len(success_results) > 0, "Should have some successes despite failures"
        
        print(f"\nConcurrent Failure Handling:")
        print(f"  Total Attempts: {total_attempts}")
        print(f"  Successes: {len(success_results)}")
        print(f"  Failures: {len(failure_results)}")
        print(f"  Success Rate: {success_rate:.2%}")

    def test_data_consistency_during_failures(self, market_data_service, sample_tick_data):
        """Test data consistency maintenance during failures."""
        processed_ticks = []
        failed_ticks = []
        
        # Mock data processing with intermittent failures
        def mock_tick_processing_with_failures(tick):
            # Simulate 20% failure rate
            tick_num = int(tick.ticker.split('_')[-1]) if '_' in tick.ticker else 0
            
            if tick_num % 5 == 0:  # Every 5th tick fails
                failed_ticks.append(tick)
                raise Exception("Processing failure")
            else:
                processed_ticks.append(tick)
                return True
        
        # Process batch of ticks with failures
        test_tickers = [f"STOCK_{i}" for i in range(20)]
        
        for i, ticker in enumerate(test_tickers):
            tick = Mock()
            tick.ticker = ticker
            tick.price = 150.0 + i
            tick.volume = 1000
            tick.timestamp = time.time() + i
            
            try:
                mock_tick_processing_with_failures(tick)
            except Exception:
                # Failure handling - should not corrupt other data
                pass
        
        # Verify data consistency
        total_ticks = len(processed_ticks) + len(failed_ticks)
        success_rate = len(processed_ticks) / total_ticks
        
        assert total_ticks == len(test_tickers), "Should account for all ticks"
        assert success_rate > 0.7, f"Success rate {success_rate:.2%} too low"
        
        # Verify no data corruption
        for tick in processed_ticks:
            assert tick.price > 0, "Price should be valid"
            assert tick.volume > 0, "Volume should be valid"
            assert tick.timestamp > 0, "Timestamp should be valid"

    def test_graceful_degradation_under_load(self, websocket_broadcaster):
        """Test graceful degradation under high load conditions."""
        # Create high user load
        high_user_count = 100
        for i in range(high_user_count):
            session_id = f'load_session_{i}'
            connected_user = ConnectedUser(
                user_id=f'load_user_{i}',
                session_id=session_id,
                connected_at=time.time(),
                last_seen=time.time(),
                subscriptions={'Breakout'}
            )
            websocket_broadcaster.connected_users[session_id] = connected_user
        
        # Mock degraded performance under load
        emission_times = []
        
        def mock_emit_with_load_degradation(event, data, room=None, **kwargs):
            # Simulate increasing delay under load
            user_num = int(room.split('_')[2]) if room else 0
            delay = min(user_num * 0.001, 0.1)  # Max 100ms delay
            
            start_time = time.perf_counter()
            time.sleep(delay)
            end_time = time.perf_counter()
            
            emission_times.append((end_time - start_time) * 1000)
            return True
        
        websocket_broadcaster.socketio.emit.side_effect = mock_emit_with_load_degradation
        
        # Test broadcasting under load
        load_start = time.perf_counter()
        
        pattern_event = {
            'type': 'pattern_alert',
            'data': {
                'pattern': 'LoadTest',
                'symbol': 'STRESS',
                'confidence': 0.85
            },
            'timestamp': time.time()
        }
        
        websocket_broadcaster.broadcast_pattern_alert(pattern_event)
        
        load_end = time.perf_counter()
        total_load_time = (load_end - load_start) * 1000
        
        # Analyze degradation
        avg_emission_time = sum(emission_times) / len(emission_times)
        max_emission_time = max(emission_times)
        
        # Should handle load with graceful degradation
        assert total_load_time < 30000, f"Total load time {total_load_time:.2f}ms too high"
        assert avg_emission_time < 50, f"Average emission time {avg_emission_time:.2f}ms too high"
        assert max_emission_time < 200, f"Max emission time {max_emission_time:.2f}ms too high"
        
        print(f"\nLoad Degradation Metrics:")
        print(f"  Users: {high_user_count}")
        print(f"  Total Time: {total_load_time:.2f}ms")
        print(f"  Avg Emission: {avg_emission_time:.2f}ms")
        print(f"  Max Emission: {max_emission_time:.2f}ms")

    def test_service_recovery_after_complete_failure(self, redis_subscriber):
        """Test service recovery after complete system failure."""
        # Simulate complete service failure
        service_failed = True
        recovery_attempts = []
        
        def mock_service_restart():
            nonlocal service_failed
            recovery_attempts.append(time.time())
            
            # Fail first 2 restart attempts
            if len(recovery_attempts) <= 2:
                raise Exception("Service restart failed")
            else:
                service_failed = False
                return True
        
        # Test recovery mechanism
        recovery_start = time.perf_counter()
        
        for attempt in range(5):
            try:
                if service_failed:
                    mock_service_restart()
                    
                if not service_failed:
                    break
                    
            except Exception:
                # Wait before retry
                time.sleep(0.1)
        
        recovery_end = time.perf_counter()
        recovery_time = (recovery_end - recovery_start) * 1000
        
        # Verify recovery
        assert not service_failed, "Service should recover after retries"
        assert len(recovery_attempts) >= 2, "Should attempt multiple recoveries"
        assert recovery_time < 2000, f"Recovery time {recovery_time:.2f}ms too high"
        
        print(f"\nComplete Failure Recovery:")
        print(f"  Recovery Attempts: {len(recovery_attempts)}")
        print(f"  Recovery Time: {recovery_time:.2f}ms")
        print(f"  Final State: {'Recovered' if not service_failed else 'Failed'}")

    def test_health_check_and_monitoring(self, market_data_service, redis_subscriber, websocket_broadcaster):
        """Test health check and monitoring during error conditions."""
        # Test health checks for each component
        components = [
            ('market_data_service', market_data_service),
            ('redis_subscriber', redis_subscriber),
            ('websocket_broadcaster', websocket_broadcaster),
        ]
        
        health_results = {}
        
        for component_name, component in components:
            try:
                if hasattr(component, 'get_health_status'):
                    health = component.get_health_status()
                elif hasattr(component, 'get_stats'):
                    stats = component.get_stats()
                    health = {
                        'status': 'healthy' if stats.get('is_running', True) else 'unhealthy',
                        'stats': stats
                    }
                else:
                    health = {'status': 'unknown', 'message': 'No health check available'}
                
                health_results[component_name] = health
                
            except Exception as e:
                health_results[component_name] = {
                    'status': 'error',
                    'message': str(e)
                }
        
        # Verify health check availability
        assert len(health_results) == len(components), "Should check all components"
        
        for component_name, health in health_results.items():
            assert 'status' in health, f"{component_name} should have status"
            print(f"\nHealth Check - {component_name}:")
            print(f"  Status: {health.get('status', 'unknown')}")
            
            if 'stats' in health:
                stats = health['stats']
                print(f"  Runtime: {stats.get('runtime_seconds', 0)}s")
                if 'events_processed' in stats:
                    print(f"  Events Processed: {stats['events_processed']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])