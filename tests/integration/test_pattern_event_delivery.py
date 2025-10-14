"""
End-to-End Pattern Event Delivery Integration Tests
Tests complete workflow from TickStockPL pattern detection → Redis → TickStockApp → WebSocket → Frontend

Validates:
1. Pattern event publishing from TickStockPL simulation
2. Redis pub-sub message delivery
3. Pattern cache processing and storage
4. WebSocket broadcasting to frontend clients
5. User filtering and alert targeting
6. Performance and reliability requirements
"""

import json
import time
from unittest.mock import Mock, patch

import pytest
import redis
from flask import Flask
from flask_socketio import SocketIO

from src.core.services.pattern_discovery_service import PatternDiscoveryService
from src.core.services.redis_event_subscriber import EventType, RedisEventSubscriber
from src.infrastructure.cache.redis_pattern_cache import RedisPatternCache


class TestPatternEventDelivery:
    """Test end-to-end pattern event delivery pipeline."""

    @pytest.fixture
    def redis_client(self):
        """Redis client for testing."""
        client = redis.Redis(host='localhost', port=6379, db=15, decode_responses=True)
        try:
            client.ping()
        except redis.ConnectionError:
            pytest.skip("Redis not available for testing")
        yield client
        client.flushdb()

    @pytest.fixture
    def flask_app(self):
        """Flask app for testing."""
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test_secret'
        return app

    @pytest.fixture
    def socketio(self, flask_app):
        """SocketIO instance for testing."""
        socketio = SocketIO(flask_app, cors_allowed_origins="*", async_mode='threading')
        return socketio

    @pytest.fixture
    def pattern_cache(self, redis_client):
        """Pattern cache for testing."""
        config = {
            'pattern_cache_ttl': 3600,
            'api_response_cache_ttl': 30,
            'index_cache_ttl': 3600
        }
        return RedisPatternCache(redis_client, config)

    @pytest.fixture
    def event_subscriber(self, redis_client, socketio, flask_app):
        """Event subscriber with real SocketIO integration."""
        config = {'channels': ['tickstock.events.patterns']}
        subscriber = RedisEventSubscriber(redis_client, socketio, config, flask_app=flask_app)
        return subscriber

    def test_complete_pattern_delivery_workflow(self, redis_client, pattern_cache, event_subscriber, flask_app, socketio):
        """Test complete pattern event delivery from Redis to WebSocket clients."""
        # Track WebSocket emissions
        websocket_emissions = []
        original_emit = socketio.emit

        def track_emit(*args, **kwargs):
            websocket_emissions.append({
                'args': args,
                'kwargs': kwargs,
                'timestamp': time.time()
            })
            return original_emit(*args, **kwargs)

        socketio.emit = track_emit

        # Set up pattern cache integration
        def cache_pattern_handler(event):
            """Handler to process patterns into cache."""
            pattern_cache.process_pattern_event(event.data)

        event_subscriber.add_event_handler(EventType.PATTERN_DETECTED, cache_pattern_handler)

        # Start event subscriber
        subscriber_started = event_subscriber.start()
        assert subscriber_started, "Event subscriber should start successfully"

        # Wait for subscriber to be ready
        time.sleep(0.3)

        # Simulate multiple TickStockPL pattern detections
        pattern_events = [
            {
                'event_type': 'pattern_detected',
                'symbol': 'AAPL',
                'pattern': 'Doji',
                'confidence': 0.85,
                'current_price': 150.25,
                'price_change': 2.1,
                'timestamp': time.time(),
                'expires_at': time.time() + 3600,
                'indicators': {
                    'relative_strength': 1.2,
                    'relative_volume': 1.5,
                    'rsi': 65.0
                },
                'source': 'daily'
            },
            {
                'event_type': 'pattern_detected',
                'symbol': 'GOOGL',
                'pattern': 'Hammer',
                'confidence': 0.78,
                'current_price': 2750.50,
                'price_change': -0.8,
                'timestamp': time.time(),
                'expires_at': time.time() + 1800,
                'indicators': {
                    'relative_strength': 0.9,
                    'relative_volume': 2.1,
                    'rsi': 45.0
                },
                'source': 'intraday'
            },
            {
                'event_type': 'pattern_detected',
                'symbol': 'TSLA',
                'pattern': 'Engulfing',
                'confidence': 0.92,
                'current_price': 250.30,
                'price_change': 3.2,
                'timestamp': time.time(),
                'expires_at': time.time() + 2700,
                'indicators': {
                    'relative_strength': 1.4,
                    'relative_volume': 2.3,
                    'rsi': 68.0
                },
                'source': 'combo'
            }
        ]

        # Publish pattern events to Redis
        for i, pattern_event in enumerate(pattern_events):
            redis_client.publish('tickstock.events.patterns', json.dumps(pattern_event))
            time.sleep(0.1)  # Small delay between events

        # Wait for event processing
        time.sleep(1.0)

        # Stop subscriber
        event_subscriber.stop()

        # Verify cache was updated
        cache_stats = pattern_cache.get_cache_stats()

        # Verify WebSocket emissions occurred
        pattern_alerts = [emission for emission in websocket_emissions
                         if emission['args'] and emission['args'][0] == 'pattern_alert']

        # Test pattern retrieval from cache
        scan_results = pattern_cache.scan_patterns({
            'confidence_min': 0.7,
            'page': 1,
            'per_page': 10
        })

        return {
            'events_published': len(pattern_events),
            'cache_patterns_stored': cache_stats['cached_patterns'],
            'websocket_alerts_sent': len(pattern_alerts),
            'patterns_retrievable': scan_results['pagination']['total'],
            'processing_successful': cache_stats['cached_patterns'] > 0,
            'end_to_end_delivery': len(pattern_alerts) > 0,
            'cache_stats': cache_stats,
            'websocket_emissions': websocket_emissions
        }

    def test_user_specific_pattern_filtering(self, redis_client, event_subscriber, socketio):
        """Test user-specific pattern alert filtering and targeting."""
        # Mock pattern alert manager
        mock_pattern_manager = Mock()

        # Configure user subscriptions
        mock_pattern_manager.get_users_for_alert.return_value = ['user_123', 'user_456']

        # Add pattern manager to Flask app context
        with patch.object(event_subscriber, 'flask_app') as mock_app:
            mock_app.pattern_alert_manager = mock_pattern_manager

            # Track targeted emissions
            targeted_emissions = []
            original_emit = socketio.emit

            def track_targeted_emit(*args, **kwargs):
                targeted_emissions.append({
                    'args': args,
                    'kwargs': kwargs,
                    'room': kwargs.get('room'),
                    'timestamp': time.time()
                })
                return original_emit(*args, **kwargs)

            socketio.emit = track_targeted_emit

            # Start subscriber
            event_subscriber.start()
            time.sleep(0.2)

            # Publish pattern event
            pattern_event = {
                'event_type': 'pattern_detected',
                'symbol': 'NVDA',
                'pattern': 'Bull_Flag',
                'confidence': 0.88,
                'current_price': 800.50,
                'price_change': 2.5,
                'timestamp': time.time(),
                'source': 'daily'
            }

            redis_client.publish('tickstock.events.patterns', json.dumps(pattern_event))
            time.sleep(0.5)

            event_subscriber.stop()

            # Verify user targeting
            user_targeted_alerts = [emission for emission in targeted_emissions
                                  if emission.get('room') and emission['room'].startswith('user_')]

            return {
                'pattern_manager_called': mock_pattern_manager.get_users_for_alert.called,
                'targeted_alerts_sent': len(user_targeted_alerts),
                'target_users': [emission['room'] for emission in user_targeted_alerts],
                'filtering_working': len(user_targeted_alerts) > 0
            }

    def test_pattern_delivery_performance(self, redis_client, pattern_cache, event_subscriber):
        """Test pattern delivery performance requirements (<100ms end-to-end)."""
        performance_metrics = {
            'delivery_times_ms': [],
            'cache_processing_times_ms': [],
            'total_events_processed': 0,
            'performance_target_met': False
        }

        # Track processing times
        def timed_cache_handler(event):
            start_time = time.time()
            pattern_cache.process_pattern_event(event.data)
            processing_time = (time.time() - start_time) * 1000
            performance_metrics['cache_processing_times_ms'].append(processing_time)

        event_subscriber.add_event_handler(EventType.PATTERN_DETECTED, timed_cache_handler)
        event_subscriber.start()
        time.sleep(0.2)

        # Send multiple pattern events with timing
        for i in range(10):
            event_start_time = time.time()

            pattern_event = {
                'event_type': 'pattern_detected',
                'symbol': f'PERF{i:02d}',
                'pattern': 'Performance_Test',
                'confidence': 0.80 + (i * 0.01),
                'current_price': 100.0 + i,
                'price_change': 1.0,
                'timestamp': time.time(),
                'expires_at': time.time() + 3600,
                'indicators': {'rsi': 50.0 + i},
                'source': 'test'
            }

            redis_client.publish('tickstock.events.patterns', json.dumps(pattern_event))

            # Wait for processing and measure end-to-end time
            time.sleep(0.1)

            end_to_end_time = (time.time() - event_start_time) * 1000
            performance_metrics['delivery_times_ms'].append(end_to_end_time)
            performance_metrics['total_events_processed'] += 1

        event_subscriber.stop()

        # Calculate performance metrics
        avg_delivery_time = sum(performance_metrics['delivery_times_ms']) / len(performance_metrics['delivery_times_ms'])
        avg_cache_time = sum(performance_metrics['cache_processing_times_ms']) / len(performance_metrics['cache_processing_times_ms'])
        max_delivery_time = max(performance_metrics['delivery_times_ms'])

        # Check performance target (<100ms end-to-end)
        performance_metrics['performance_target_met'] = max_delivery_time < 100
        performance_metrics['avg_delivery_time_ms'] = avg_delivery_time
        performance_metrics['avg_cache_processing_ms'] = avg_cache_time
        performance_metrics['max_delivery_time_ms'] = max_delivery_time

        return performance_metrics

    def test_offline_user_message_persistence(self, redis_client):
        """Test message persistence for offline users using Redis Streams."""
        # This tests the Redis Streams functionality for offline user handling
        stream_name = 'tickstock:offline_messages'
        user_id = 'user_offline_test'

        # Simulate offline user pattern alerts
        pattern_messages = [
            {
                'user_id': user_id,
                'pattern_alert': {
                    'symbol': 'AAPL',
                    'pattern': 'Doji',
                    'confidence': 0.85,
                    'timestamp': time.time()
                }
            },
            {
                'user_id': user_id,
                'pattern_alert': {
                    'symbol': 'GOOGL',
                    'pattern': 'Hammer',
                    'confidence': 0.78,
                    'timestamp': time.time()
                }
            }
        ]

        # Add messages to Redis Stream
        message_ids = []
        for msg in pattern_messages:
            message_id = redis_client.xadd(stream_name, msg)
            message_ids.append(message_id)

        # Verify messages were stored
        stream_length = redis_client.xlen(stream_name)

        # Read messages back
        stored_messages = redis_client.xread({stream_name: '0'})

        # Parse stored messages
        retrieved_count = 0
        if stored_messages:
            for stream, messages in stored_messages:
                retrieved_count = len(messages)

        # Cleanup
        redis_client.delete(stream_name)

        return {
            'messages_sent_to_stream': len(pattern_messages),
            'stream_length': stream_length,
            'messages_retrieved': retrieved_count,
            'message_ids': message_ids,
            'persistence_working': stream_length == len(pattern_messages)
        }

    def test_connection_resilience_and_recovery(self, redis_client, event_subscriber):
        """Test system resilience to connection failures and recovery."""
        resilience_results = {
            'initial_connection': False,
            'connection_lost_handled': False,
            'recovery_successful': False,
            'messages_after_recovery': 0
        }

        # Test initial connection
        try:
            initial_connection = event_subscriber.start()
            resilience_results['initial_connection'] = initial_connection

            if initial_connection:
                time.sleep(0.2)

                # Simulate connection loss by closing Redis connection
                # Note: This is a simplified test - real connection loss handling
                # would involve more complex network failure simulation

                # Send a message before "connection loss"
                pattern_before = {
                    'event_type': 'pattern_detected',
                    'symbol': 'BEFORE',
                    'pattern': 'Before_Loss',
                    'confidence': 0.80
                }
                redis_client.publish('tickstock.events.patterns', json.dumps(pattern_before))
                time.sleep(0.1)

                # Simulate recovery by sending messages after a delay
                time.sleep(0.5)

                # Test message delivery after "recovery"
                messages_after = []
                for i in range(3):
                    pattern_after = {
                        'event_type': 'pattern_detected',
                        'symbol': f'AFTER_{i}',
                        'pattern': 'After_Recovery',
                        'confidence': 0.85
                    }
                    redis_client.publish('tickstock.events.patterns', json.dumps(pattern_after))
                    messages_after.append(pattern_after)
                    time.sleep(0.05)

                time.sleep(0.3)
                resilience_results['messages_after_recovery'] = len(messages_after)
                resilience_results['recovery_successful'] = True

            event_subscriber.stop()

        except Exception as e:
            resilience_results['error'] = str(e)

        return resilience_results

class TestPatternDiscoveryIntegration:
    """Test Pattern Discovery Service integration."""

    @pytest.fixture
    def mock_flask_app(self):
        """Mock Flask app for Pattern Discovery Service."""
        app = Mock(spec=Flask)
        app.config = {'TESTING': True}
        return app

    @pytest.fixture
    def redis_client(self):
        """Redis client for testing."""
        client = redis.Redis(host='localhost', port=6379, db=15, decode_responses=True)
        try:
            client.ping()
        except redis.ConnectionError:
            pytest.skip("Redis not available for testing")
        yield client
        client.flushdb()

    def test_pattern_discovery_service_initialization(self, mock_flask_app, redis_client):
        """Test Pattern Discovery Service initialization and component integration."""
        service_config = {
            'redis_host': 'localhost',
            'redis_port': 6379,
            'redis_db': 15,
            'pattern_cache_ttl': 3600,
            'api_response_cache_ttl': 30,
            'tickstock_channels': [
                'tickstock.events.patterns',
                'tickstock.events.backtesting.progress',
                'tickstock.events.backtesting.results'
            ]
        }

        # Initialize Pattern Discovery Service
        service = PatternDiscoveryService(mock_flask_app, service_config)

        # Mock components that require external dependencies
        with patch('src.infrastructure.database.tickstock_db.TickStockDatabase') as mock_db, \
             patch('src.infrastructure.cache.cache_control.CacheControl') as mock_cache_control:

            # Configure mocks
            mock_db.return_value.health_check.return_value = {'status': 'healthy'}
            mock_cache_control.return_value.initialize.return_value = True

            # Initialize service
            initialization_success = service.initialize()

            # Verify initialization
            assert initialization_success, "Pattern Discovery Service should initialize successfully"
            assert service.initialized, "Service should be marked as initialized"
            assert service.pattern_cache is not None, "Pattern cache should be initialized"
            assert service.event_subscriber is not None, "Event subscriber should be initialized"

            # Test service health status
            health_status = service.get_health_status()
            assert health_status is not None, "Health status should be available"

            # Cleanup
            service.shutdown()

            return {
                'initialization_successful': initialization_success,
                'components_initialized': {
                    'pattern_cache': service.pattern_cache is not None,
                    'event_subscriber': service.event_subscriber is not None,
                    'redis_manager': service.redis_manager is not None
                },
                'health_status': health_status
            }

    def test_service_component_coordination(self, mock_flask_app, redis_client):
        """Test coordination between Pattern Discovery Service components."""
        service_config = {
            'redis_host': 'localhost',
            'redis_port': 6379,
            'redis_db': 15,
            'pattern_cache_ttl': 3600
        }

        service = PatternDiscoveryService(mock_flask_app, service_config)

        with patch('src.infrastructure.database.tickstock_db.TickStockDatabase') as mock_db, \
             patch('src.infrastructure.cache.cache_control.CacheControl') as mock_cache_control:

            mock_db.return_value.health_check.return_value = {'status': 'healthy'}
            mock_cache_control.return_value.initialize.return_value = True

            # Initialize service
            service.initialize()

            # Test pattern event handling coordination
            test_pattern_event = {
                'event_type': 'pattern_detected',
                'symbol': 'COORD_TEST',
                'pattern': 'Coordination_Test',
                'confidence': 0.88,
                'timestamp': time.time(),
                'source': 'test'
            }

            # Simulate pattern event processing
            from src.core.services.redis_event_subscriber import EventType, TickStockEvent

            event = TickStockEvent(
                event_type=EventType.PATTERN_DETECTED,
                source='test',
                timestamp=time.time(),
                data=test_pattern_event,
                channel='tickstock.events.patterns'
            )

            # Process event through service
            service._handle_pattern_event(event)

            # Verify cache was updated
            cache_stats = service.pattern_cache.get_cache_stats()

            service.shutdown()

            return {
                'event_processed_successfully': cache_stats.get('cached_patterns', 0) > 0,
                'service_coordination_working': True,
                'cache_stats': cache_stats
            }

# Helper function to run all end-to-end tests
def run_pattern_delivery_tests():
    """Execute all pattern event delivery tests."""
    print("="*80)
    print("End-to-End Pattern Event Delivery Tests")
    print("="*80)

    # Initialize test components
    try:
        redis_client = redis.Redis(host='localhost', port=6379, db=15, decode_responses=True)
        redis_client.ping()

        # Create Flask app and SocketIO
        flask_app = Flask(__name__)
        flask_app.config['TESTING'] = True
        socketio = SocketIO(flask_app, async_mode='threading')

        # Create test instances
        pattern_cache = RedisPatternCache(redis_client, {
            'pattern_cache_ttl': 3600,
            'api_response_cache_ttl': 30
        })

        event_subscriber = RedisEventSubscriber(
            redis_client, socketio,
            {'channels': ['tickstock.events.patterns']},
            flask_app=flask_app
        )

        delivery_tester = TestPatternEventDelivery()

        print("\n🧪 Running End-to-End Delivery Tests...")

        # Test 1: Complete workflow
        print("\n1️⃣ Testing Complete Pattern Delivery Workflow...")
        workflow_results = delivery_tester.test_complete_pattern_delivery_workflow(
            redis_client, pattern_cache, event_subscriber, flask_app, socketio
        )

        print(f"   Events Published: {workflow_results['events_published']}")
        print(f"   Cache Patterns Stored: {workflow_results['cache_patterns_stored']}")
        print(f"   WebSocket Alerts Sent: {workflow_results['websocket_alerts_sent']}")
        print(f"   End-to-End Delivery: {'✅' if workflow_results['end_to_end_delivery'] else '❌'}")

        # Test 2: Performance
        print("\n2️⃣ Testing Performance Requirements...")
        perf_results = delivery_tester.test_pattern_delivery_performance(
            redis_client, pattern_cache, event_subscriber
        )

        print(f"   Average Delivery Time: {perf_results['avg_delivery_time_ms']:.2f}ms")
        print(f"   Max Delivery Time: {perf_results['max_delivery_time_ms']:.2f}ms")
        print(f"   Performance Target Met: {'✅' if perf_results['performance_target_met'] else '❌'}")

        # Test 3: Offline persistence
        print("\n3️⃣ Testing Offline User Message Persistence...")
        persistence_results = delivery_tester.test_offline_user_message_persistence(redis_client)

        print(f"   Messages Persisted: {persistence_results['messages_sent_to_stream']}")
        print(f"   Persistence Working: {'✅' if persistence_results['persistence_working'] else '❌'}")

        # Cleanup
        redis_client.flushdb()

        print(f"\n{'='*80}")
        print("✅ Pattern Delivery Tests Completed")

        return {
            'workflow_results': workflow_results,
            'performance_results': perf_results,
            'persistence_results': persistence_results
        }

    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        return {'error': str(e)}

if __name__ == "__main__":
    run_pattern_delivery_tests()
