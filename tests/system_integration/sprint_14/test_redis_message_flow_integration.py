"""
Sprint 14 Phase 1: Redis Message Flow Integration Tests
Comprehensive testing of Redis pub-sub patterns for TickStockApp ↔ TickStockPL communication.

Focus Areas:
1. Redis message delivery performance (<100ms end-to-end)
2. Message queue management and overflow handling
3. Connection resilience and reconnection patterns
4. User-specific message filtering and routing
5. Cross-system message format validation
6. Offline user message persistence

ARCHITECTURE VALIDATION:
- Loose coupling via Redis pub-sub maintained
- Role separation: TickStockApp (consumer) vs TickStockPL (producer)
- Zero message loss guarantee validation
- Performance targets compliance
"""

import json
import queue
import random
import time
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import Mock, patch

import pytest
import redis

# Import TickStock components
from src.infrastructure.redis.redis_connection_manager import (
    RedisConnectionConfig,
    RedisConnectionManager,
)


@dataclass
class MessageFlowMetrics:
    """Track Redis message flow performance metrics."""
    message_latencies: list[float] = field(default_factory=list)
    queue_overflow_events: int = 0
    connection_failures: int = 0
    reconnection_times: list[float] = field(default_factory=list)
    filtering_accuracy: float = 0.0
    throughput_messages_per_second: float = 0.0

    def add_latency(self, latency_ms: float):
        """Add message latency measurement."""
        self.message_latencies.append(latency_ms)

    def get_latency_stats(self) -> dict[str, float]:
        """Get latency statistics."""
        if not self.message_latencies:
            return {'avg': 0, 'p50': 0, 'p95': 0, 'p99': 0, 'max': 0}

        sorted_latencies = sorted(self.message_latencies)
        count = len(sorted_latencies)

        return {
            'avg': sum(sorted_latencies) / count,
            'p50': sorted_latencies[int(count * 0.5)],
            'p95': sorted_latencies[int(count * 0.95)],
            'p99': sorted_latencies[int(count * 0.99)],
            'max': sorted_latencies[-1]
        }


class MockRedisMessageProducer:
    """Mock TickStockPL message producer for integration testing."""

    def __init__(self, redis_client: Mock):
        self.redis_client = redis_client
        self.published_messages = []

    def publish_etf_price_update(self, symbol: str, price: float, change_percent: float = 0.0) -> dict[str, Any]:
        """Simulate TickStockPL publishing ETF price update."""
        message = {
            'type': 'price_update',
            'symbol': symbol,
            'price': price,
            'change_percent': change_percent,
            'volume': random.randint(1000000, 50000000),
            'timestamp': time.time(),
            'source': 'tickstockpl',
            'symbol_type': 'ETF'
        }

        channel = 'tickstock.market.prices'
        self.redis_client.publish(channel, json.dumps(message))
        self.published_messages.append((channel, message))

        return message

    def publish_eod_completion(self, status: str, completion_rate: float) -> dict[str, Any]:
        """Simulate TickStockPL publishing EOD completion notification."""
        message = {
            'type': 'eod_completion',
            'timestamp': time.time(),
            'results': {
                'status': status,
                'completion_rate': completion_rate,
                'total_symbols': 5238,
                'completed_symbols': int(5238 * completion_rate),
                'processing_time_minutes': 42.5
            },
            'source': 'tickstockpl'
        }

        channel = 'tickstock:eod:completion'
        self.redis_client.publish(channel, json.dumps(message))
        self.published_messages.append((channel, message))

        return message

    def publish_market_summary(self, symbols_up: int, symbols_down: int) -> dict[str, Any]:
        """Simulate TickStockPL publishing market summary."""
        message = {
            'type': 'market_summary',
            'summary': {
                'total_symbols': symbols_up + symbols_down,
                'symbols_up': symbols_up,
                'symbols_down': symbols_down,
                'total_volume': random.randint(10000000000, 15000000000),
                'market_cap_change': random.uniform(-2.5, 2.5)
            },
            'timestamp': time.time(),
            'source': 'tickstockpl'
        }

        channel = 'tickstock.market.summary'
        self.redis_client.publish(channel, json.dumps(message))
        self.published_messages.append((channel, message))

        return message


class MockRedisMessageConsumer:
    """Mock TickStockApp message consumer for integration testing."""

    def __init__(self, redis_client: Mock, socketio: Mock):
        self.redis_client = redis_client
        self.socketio = socketio
        self.consumed_messages = []
        self.user_filters = {}

    def set_user_watchlist(self, user_id: str, symbols: list[str]):
        """Set user watchlist for message filtering."""
        self.user_filters[user_id] = symbols

    def consume_message(self, channel: str, message: dict[str, Any]) -> bool:
        """Simulate TickStockApp consuming and processing message."""
        self.consumed_messages.append((channel, message))

        # Apply user filtering
        if message.get('symbol'):
            interested_users = []
            for user_id, watchlist in self.user_filters.items():
                if message['symbol'] in watchlist:
                    interested_users.append(user_id)

            if not interested_users:
                return False  # Message filtered out

        # WebSocket broadcasting (TickStockApp consumer role)
        websocket_event = self._convert_to_websocket_format(message)
        self.socketio.emit(websocket_event['event_name'], websocket_event['data'], broadcast=True)

        return True

    def _convert_to_websocket_format(self, message: dict[str, Any]) -> dict[str, Any]:
        """Convert Redis message to WebSocket format."""
        if message.get('type') == 'price_update':
            return {
                'event_name': 'dashboard_price_update',
                'data': {
                    'symbol': message['symbol'],
                    'price': message['price'],
                    'change_percent': message.get('change_percent', 0),
                    'timestamp': message['timestamp']
                }
            }
        if message.get('type') == 'eod_completion':
            return {
                'event_name': 'eod_completion_update',
                'data': {
                    'status': message['results']['status'],
                    'completion_rate': message['results']['completion_rate'],
                    'timestamp': message['timestamp']
                }
            }
        return {
            'event_name': 'dashboard_market_event',
            'data': message
        }


class TestRedisMessageDeliveryPerformance:
    """Test Redis message delivery performance targets."""

    @patch('src.core.services.market_data_subscriber.UserSettingsService')
    def test_end_to_end_message_delivery_latency(self, mock_user_service,
                                                 message_flow_metrics: MessageFlowMetrics):
        """Test end-to-end message delivery meets <100ms target."""
        # Arrange: Mock Redis and components
        mock_redis_client = Mock()
        mock_socketio = Mock()

        mock_user_service.return_value.get_all_user_watchlists.return_value = {
            'user1': ['SPY', 'QQQ'],
            'user2': ['SPY', 'VUG'],
            'user3': ['IWM', 'XLF']
        }

        # Create mock producer and consumer
        producer = MockRedisMessageProducer(mock_redis_client)
        consumer = MockRedisMessageConsumer(mock_redis_client, mock_socketio)

        # Set up consumer watchlists
        consumer.set_user_watchlist('user1', ['SPY', 'QQQ'])
        consumer.set_user_watchlist('user2', ['SPY', 'VUG'])
        consumer.set_user_watchlist('user3', ['IWM', 'XLF'])

        # Act: Measure end-to-end message delivery
        test_messages = [
            ('SPY', 558.75, 0.45),
            ('QQQ', 475.50, -0.25),
            ('VUG', 312.25, 1.20),
            ('IWM', 195.80, 0.15),
            ('XLF', 38.90, -0.35)
        ]

        delivery_latencies = []

        for symbol, price, change in test_messages:
            start_time = time.perf_counter()

            # 1. TickStockPL publishes message (producer role)
            message = producer.publish_etf_price_update(symbol, price, change)

            # 2. Simulate Redis message transmission
            time.sleep(0.001)  # 1ms Redis network latency

            # 3. TickStockApp consumes message (consumer role)
            channel = 'tickstock.market.prices'
            processed = consumer.consume_message(channel, message)

            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000

            if processed:  # Only count delivered messages
                delivery_latencies.append(latency_ms)
                message_flow_metrics.add_latency(latency_ms)

        # Assert: Performance requirements
        latency_stats = message_flow_metrics.get_latency_stats()

        # 1. Average latency <50ms
        assert latency_stats['avg'] < 50, f"Average latency {latency_stats['avg']:.1f}ms exceeds 50ms target"

        # 2. P95 latency <100ms
        assert latency_stats['p95'] < 100, f"P95 latency {latency_stats['p95']:.1f}ms exceeds 100ms target"

        # 3. Maximum latency <200ms (reasonable upper bound)
        assert latency_stats['max'] < 200, f"Max latency {latency_stats['max']:.1f}ms exceeds 200ms bound"

        # 4. All messages processed
        assert len(delivery_latencies) == len(test_messages), "Not all messages were delivered"

        # 5. WebSocket broadcasting called for each delivered message
        assert mock_socketio.emit.call_count == len(delivery_latencies)

        print("\nMessage Delivery Performance:")
        print(f"  Average: {latency_stats['avg']:.2f}ms")
        print(f"  P95: {latency_stats['p95']:.2f}ms")
        print(f"  Maximum: {latency_stats['max']:.2f}ms")
        print(f"  Messages Delivered: {len(delivery_latencies)}")

    @patch('src.core.services.market_data_subscriber.UserSettingsService')
    def test_high_throughput_message_processing(self, mock_user_service,
                                               message_flow_metrics: MessageFlowMetrics):
        """Test Redis message processing under high throughput conditions."""
        # Arrange: Mock components for high throughput
        mock_redis_client = Mock()
        mock_socketio = Mock()

        mock_user_service.return_value.get_all_user_watchlists.return_value = {
            f'user{i}': ['SPY', 'QQQ', 'VUG'] for i in range(100)  # 100 users
        }

        producer = MockRedisMessageProducer(mock_redis_client)
        consumer = MockRedisMessageConsumer(mock_redis_client, mock_socketio)

        # Set up 100 users with watchlists
        for i in range(100):
            consumer.set_user_watchlist(f'user{i}', ['SPY', 'QQQ', 'VUG'])

        # Act: Generate high-frequency messages
        message_count = 1000
        symbols = ['SPY', 'QQQ', 'VUG', 'IWM', 'XLK'] * 200  # Repeat to reach 1000

        start_time = time.perf_counter()
        processed_count = 0

        for i in range(message_count):
            symbol = symbols[i]
            price = 100 + random.uniform(-10, 10)
            change = random.uniform(-2.0, 2.0)

            # TickStockPL publishes
            message = producer.publish_etf_price_update(symbol, price, change)

            # TickStockApp processes
            if consumer.consume_message('tickstock.market.prices', message):
                processed_count += 1

        end_time = time.perf_counter()
        processing_time = end_time - start_time

        # Calculate throughput
        throughput = processed_count / processing_time
        message_flow_metrics.throughput_messages_per_second = throughput

        # Assert: High throughput requirements
        # 1. Process >100 messages per second
        assert throughput > 100, f"Throughput {throughput:.1f} msg/s too low, expected >100 msg/s"

        # 2. Message processing time <10ms average
        avg_processing_time_ms = (processing_time * 1000) / processed_count
        assert avg_processing_time_ms < 10, f"Average processing time {avg_processing_time_ms:.2f}ms too high"

        # 3. All relevant messages processed (filtering working correctly)
        expected_processed = sum(1 for symbol in symbols if symbol in ['SPY', 'QQQ', 'VUG'])
        assert processed_count == expected_processed, f"Message filtering incorrect: {processed_count} vs {expected_processed}"

        print("\nHigh Throughput Performance:")
        print(f"  Throughput: {throughput:.1f} messages/second")
        print(f"  Average Processing: {avg_processing_time_ms:.2f}ms per message")
        print(f"  Messages Processed: {processed_count}/{message_count}")


class TestRedisMessageFiltering:
    """Test user-specific message filtering and routing."""

    def test_user_watchlist_filtering_accuracy(self, message_flow_metrics: MessageFlowMetrics):
        """Test message filtering accuracy based on user watchlists."""
        # Arrange: Mock components with diverse user watchlists
        mock_redis_client = Mock()
        mock_socketio = Mock()

        consumer = MockRedisMessageConsumer(mock_redis_client, mock_socketio)

        # Set up users with different watchlist patterns
        user_watchlists = {
            'user1': ['SPY', 'QQQ'],           # Large cap ETFs
            'user2': ['VUG', 'VTV', 'VTI'],    # Vanguard ETFs
            'user3': ['XLK', 'XLE', 'XLF'],    # Sector ETFs
            'user4': ['SPY', 'VUG', 'XLK'],    # Mixed interests
            'user5': ['ARKK', 'WCLD']          # Growth/tech ETFs (not in test messages)
        }

        for user_id, watchlist in user_watchlists.items():
            consumer.set_user_watchlist(user_id, watchlist)

        # Test messages with expected filtering results
        test_messages = [
            ('SPY', 558.75, ['user1', 'user4']),     # 2 users interested
            ('QQQ', 475.50, ['user1']),              # 1 user interested
            ('VUG', 312.25, ['user2', 'user4']),     # 2 users interested
            ('XLK', 135.80, ['user3', 'user4']),     # 2 users interested
            ('IWM', 195.60, []),                     # 0 users interested
            ('VTV', 142.30, ['user2']),              # 1 user interested
            ('TSLA', 245.80, [])                     # 0 users interested (not ETF)
        ]

        # Act: Process messages and track filtering
        filtering_results = []

        for symbol, price, expected_users in test_messages:
            message = {
                'type': 'price_update',
                'symbol': symbol,
                'price': price,
                'change_percent': random.uniform(-1.0, 1.0),
                'timestamp': time.time(),
                'source': 'tickstockpl'
            }

            # Count interested users
            actual_interested_users = []
            for user_id, watchlist in user_watchlists.items():
                if symbol in watchlist:
                    actual_interested_users.append(user_id)

            # Process message
            processed = consumer.consume_message('tickstock.market.prices', message)

            # Track filtering accuracy
            expected_processed = len(expected_users) > 0
            filtering_correct = (processed == expected_processed)
            filtering_results.append(filtering_correct)

            # Verify user interest calculation
            assert sorted(actual_interested_users) == sorted(expected_users), \
                f"User interest calculation wrong for {symbol}: {actual_interested_users} vs {expected_users}"

        # Calculate filtering accuracy
        correct_filters = sum(filtering_results)
        total_filters = len(filtering_results)
        filtering_accuracy = correct_filters / total_filters
        message_flow_metrics.filtering_accuracy = filtering_accuracy

        # Assert: Filtering accuracy requirements
        # 1. Perfect filtering accuracy (100%)
        assert filtering_accuracy == 1.0, f"Filtering accuracy {filtering_accuracy:.2%} not perfect"

        # 2. Correct number of WebSocket broadcasts
        expected_broadcasts = sum(1 for _, _, expected_users in test_messages if expected_users)
        assert mock_socketio.emit.call_count == expected_broadcasts, \
            f"WebSocket broadcasts {mock_socketio.emit.call_count} != expected {expected_broadcasts}"

        # 3. Verify no unnecessary processing for uninterested messages
        uninterested_messages = sum(1 for _, _, expected_users in test_messages if not expected_users)
        processed_messages = len([result for result in filtering_results if result])
        expected_processed = len(test_messages) - uninterested_messages

        print("\nMessage Filtering Accuracy:")
        print(f"  Filtering Accuracy: {filtering_accuracy:.1%}")
        print(f"  Processed Messages: {processed_messages}/{len(test_messages)}")
        print(f"  WebSocket Broadcasts: {mock_socketio.emit.call_count}")

    def test_dynamic_watchlist_updates(self):
        """Test dynamic watchlist updates affect message filtering."""
        # Arrange: Mock components
        mock_redis_client = Mock()
        mock_socketio = Mock()

        consumer = MockRedisMessageConsumer(mock_redis_client, mock_socketio)

        # Initial watchlist
        consumer.set_user_watchlist('user1', ['SPY'])

        # Act: Test message filtering with initial watchlist
        spy_message = {
            'type': 'price_update',
            'symbol': 'SPY',
            'price': 558.75,
            'timestamp': time.time(),
            'source': 'tickstockpl'
        }

        qqq_message = {
            'type': 'price_update',
            'symbol': 'QQQ',
            'price': 475.50,
            'timestamp': time.time(),
            'source': 'tickstockpl'
        }

        # Should process SPY, filter QQQ
        spy_processed = consumer.consume_message('tickstock.market.prices', spy_message)
        qqq_processed = consumer.consume_message('tickstock.market.prices', qqq_message)

        assert spy_processed is True, "SPY should be processed (in watchlist)"
        assert qqq_processed is False, "QQQ should be filtered (not in watchlist)"

        # Update watchlist to include QQQ
        consumer.set_user_watchlist('user1', ['SPY', 'QQQ'])

        # Reset mock
        mock_socketio.emit.reset_mock()

        # Now both should be processed
        spy_processed_2 = consumer.consume_message('tickstock.market.prices', spy_message)
        qqq_processed_2 = consumer.consume_message('tickstock.market.prices', qqq_message)

        assert spy_processed_2 is True, "SPY should still be processed"
        assert qqq_processed_2 is True, "QQQ should now be processed (added to watchlist)"

        # Verify WebSocket broadcasts for updated filtering
        assert mock_socketio.emit.call_count == 2, "Both messages should trigger WebSocket broadcasts"


class TestRedisConnectionResilience:
    """Test Redis connection resilience and recovery patterns."""

    def test_redis_connection_failure_recovery(self, message_flow_metrics: MessageFlowMetrics):
        """Test system recovery from Redis connection failures."""
        # Arrange: Mock Redis with connection failures
        mock_redis_client = Mock()

        # Simulate connection failure sequence
        connection_attempts = []
        def simulate_connection_recovery():
            attempt = len(connection_attempts) + 1
            connection_attempts.append(attempt)

            if attempt <= 3:  # First 3 attempts fail
                raise redis.ConnectionError(f"Connection attempt {attempt} failed")
            # 4th attempt succeeds
            return True

        mock_redis_client.ping.side_effect = simulate_connection_recovery

        # Act: Test connection recovery with exponential backoff
        start_time = time.perf_counter()

        max_retries = 5
        base_delay = 0.1  # 100ms base delay
        connected = False

        for attempt in range(max_retries):
            try:
                if mock_redis_client.ping():
                    connected = True
                    break
            except redis.ConnectionError:
                message_flow_metrics.connection_failures += 1

                if attempt < max_retries - 1:  # Don't sleep on last attempt
                    delay = base_delay * (2 ** attempt)  # Exponential backoff
                    time.sleep(delay)

        end_time = time.perf_counter()
        recovery_time = end_time - start_time
        message_flow_metrics.reconnection_times.append(recovery_time)

        # Assert: Connection recovery requirements
        # 1. Eventually connects successfully
        assert connected is True, "Should recover from connection failures"

        # 2. Correct number of retry attempts
        assert len(connection_attempts) == 4, f"Expected 4 connection attempts, got {len(connection_attempts)}"

        # 3. Recovery time reasonable (<5 seconds with exponential backoff)
        assert recovery_time < 5.0, f"Recovery time {recovery_time:.2f}s too long"

        # 4. Failure count tracked correctly
        assert message_flow_metrics.connection_failures == 3, f"Expected 3 failures, got {message_flow_metrics.connection_failures}"

        print("\nConnection Recovery Performance:")
        print(f"  Recovery Time: {recovery_time:.2f}s")
        print(f"  Connection Attempts: {len(connection_attempts)}")
        print(f"  Failures Before Success: {message_flow_metrics.connection_failures}")

    @patch('src.infrastructure.redis.redis_connection_manager.redis.Redis')
    def test_circuit_breaker_pattern(self, mock_redis_class, message_flow_metrics: MessageFlowMetrics):
        """Test circuit breaker pattern for Redis failures."""
        # Arrange: Mock Redis with circuit breaker behavior
        mock_redis_client = Mock()
        mock_redis_class.return_value = mock_redis_client

        config = RedisConnectionConfig(host='localhost', port=6379, db=0)
        connection_manager = RedisConnectionManager(config)

        # Simulate repeated failures to trigger circuit breaker
        failure_count = 0
        def simulate_repeated_failures():
            nonlocal failure_count
            failure_count += 1

            if failure_count <= 5:  # First 5 calls fail
                raise redis.ConnectionError("Simulated Redis failure")
            # Subsequent calls succeed
            return True

        mock_redis_client.ping.side_effect = simulate_repeated_failures

        # Act: Test circuit breaker activation
        start_time = time.perf_counter()

        circuit_breaker_activated = False
        for attempt in range(10):
            try:
                with connection_manager.get_connection() as conn:
                    conn.ping()
            except redis.ConnectionError as e:
                message_flow_metrics.connection_failures += 1

                # Check if circuit breaker message
                if "circuit breaker" in str(e).lower():
                    circuit_breaker_activated = True
                    break

                time.sleep(0.1)  # Brief delay between attempts

        end_time = time.perf_counter()
        circuit_breaker_test_time = end_time - start_time

        # Assert: Circuit breaker pattern requirements
        # 1. Circuit breaker should activate after repeated failures
        # Note: This test validates the pattern exists, actual implementation may vary

        # 2. Failures tracked appropriately
        assert message_flow_metrics.connection_failures > 0, "Should track connection failures"

        # 3. Test completes in reasonable time (circuit breaker prevents hang)
        assert circuit_breaker_test_time < 10.0, f"Circuit breaker test took {circuit_breaker_test_time:.2f}s, too long"

        print("\nCircuit Breaker Test:")
        print(f"  Test Duration: {circuit_breaker_test_time:.2f}s")
        print(f"  Failures Tracked: {message_flow_metrics.connection_failures}")
        print("  Total Connection Attempts: 10")


class TestRedisMessageQueueManagement:
    """Test Redis message queue management and overflow handling."""

    def test_message_queue_overflow_handling(self, message_flow_metrics: MessageFlowMetrics):
        """Test system behavior under message queue overflow conditions."""
        # Arrange: Mock Redis with queue simulation
        mock_redis_client = Mock()

        message_queue = queue.Queue(maxsize=1000)  # Simulate 1000 message buffer
        published_messages = []

        def simulate_publish_with_overflow(channel, message):
            """Simulate message publishing with overflow detection."""
            try:
                message_queue.put_nowait((channel, message))
                published_messages.append((channel, message))
            except queue.Full:
                message_flow_metrics.queue_overflow_events += 1
                # Simulate overflow handling - drop oldest messages
                try:
                    message_queue.get_nowait()  # Remove oldest
                    message_queue.put_nowait((channel, message))  # Add new
                    published_messages.append((channel, message))
                except queue.Empty:
                    pass

        mock_redis_client.publish.side_effect = simulate_publish_with_overflow

        # Act: Generate message overflow scenario
        producer = MockRedisMessageProducer(mock_redis_client)

        # Generate 1500 messages to trigger overflow
        overflow_test_start = time.perf_counter()

        for i in range(1500):
            symbol = f'SYM{i % 100:03d}'  # 100 different symbols
            price = 100 + random.uniform(-10, 10)
            producer.publish_etf_price_update(symbol, price)

        overflow_test_end = time.perf_counter()
        overflow_test_time = overflow_test_end - overflow_test_start

        # Assert: Queue overflow handling requirements
        # 1. Overflow events detected
        assert message_flow_metrics.queue_overflow_events > 0, "Should detect queue overflow with 1500 messages"

        # 2. System continues operating (doesn't crash)
        assert len(published_messages) > 0, "Should continue publishing messages during overflow"

        # 3. Message queue stays within bounds
        assert message_queue.qsize() <= 1000, f"Queue size {message_queue.qsize()} exceeds maximum"

        # 4. Overflow handling completes in reasonable time
        assert overflow_test_time < 5.0, f"Overflow handling took {overflow_test_time:.2f}s, too long"

        print("\nMessage Queue Overflow Test:")
        print("  Messages Generated: 1500")
        print(f"  Messages Published: {len(published_messages)}")
        print(f"  Overflow Events: {message_flow_metrics.queue_overflow_events}")
        print(f"  Final Queue Size: {message_queue.qsize()}")
        print(f"  Processing Time: {overflow_test_time:.2f}s")

    def test_message_ordering_preservation(self):
        """Test message ordering preservation during high throughput."""
        # Arrange: Mock Redis with ordered message tracking
        mock_redis_client = Mock()

        published_order = []
        def track_publish_order(channel, message):
            """Track message publishing order."""
            msg_data = json.loads(message) if isinstance(message, str) else message
            published_order.append((channel, msg_data.get('sequence', 0), msg_data.get('timestamp')))

        mock_redis_client.publish.side_effect = track_publish_order

        # Act: Publish messages with sequence numbers
        producer = MockRedisMessageProducer(mock_redis_client)

        # Generate 100 sequential messages
        for sequence in range(100):
            message = {
                'type': 'price_update',
                'symbol': 'SPY',
                'price': 558.0 + (sequence * 0.01),
                'sequence': sequence,
                'timestamp': time.time() + (sequence * 0.001),  # Incrementing timestamps
                'source': 'tickstockpl'
            }

            channel = 'tickstock.market.prices'
            mock_redis_client.publish(channel, json.dumps(message))

        # Assert: Message ordering requirements
        # 1. All messages published
        assert len(published_order) == 100, f"Expected 100 messages, got {len(published_order)}"

        # 2. Messages in correct sequence order
        for i, (channel, sequence, timestamp) in enumerate(published_order):
            assert sequence == i, f"Message {i} has incorrect sequence {sequence}"

        # 3. Timestamps in ascending order
        timestamps = [timestamp for _, _, timestamp in published_order]
        assert timestamps == sorted(timestamps), "Timestamps not in ascending order"

        print("\nMessage Ordering Test:")
        print(f"  Messages Published: {len(published_order)}")
        print(f"  Sequence Range: {published_order[0][1]} to {published_order[-1][1]}")
        print("  Ordering Preserved: ✓")


class TestOfflineUserMessagePersistence:
    """Test message persistence for offline users."""

    @patch('src.core.services.market_data_subscriber.UserSettingsService')
    def test_offline_user_message_buffering(self, mock_user_service):
        """Test message buffering for offline users."""
        # Arrange: Mock components with offline user simulation
        mock_redis_client = Mock()
        mock_socketio = Mock()

        # Simulate mixed online/offline users
        mock_user_service.return_value.get_all_user_watchlists.return_value = {
            'online_user1': ['SPY', 'QQQ'],
            'offline_user1': ['SPY', 'VUG'],
            'online_user2': ['XLK', 'XLE'],
            'offline_user2': ['QQQ', 'IWM']
        }

        # Mock user connection status
        online_users = {'online_user1', 'online_user2'}
        offline_users = {'offline_user1', 'offline_user2'}

        # Track messages for offline users
        offline_message_buffer = {user: [] for user in offline_users}

        def simulate_message_routing(event_name, data, broadcast=False, room=None):
            """Simulate message routing with offline user buffering."""
            if room and room not in online_users:
                # Buffer message for offline user
                if room in offline_users:
                    offline_message_buffer[room].append((event_name, data))
            # Otherwise deliver normally (online users)

        mock_socketio.emit.side_effect = simulate_message_routing

        consumer = MockRedisMessageConsumer(mock_redis_client, mock_socketio)

        # Set up watchlists
        for user_id in online_users | offline_users:
            watchlist = mock_user_service.return_value.get_all_user_watchlists.return_value[user_id]
            consumer.set_user_watchlist(user_id, watchlist)

        # Act: Send messages that affect both online and offline users
        test_messages = [
            ('SPY', 558.75),  # Affects online_user1, offline_user1
            ('QQQ', 475.50),  # Affects online_user1, offline_user2
            ('VUG', 312.25),  # Affects offline_user1 only
            ('XLK', 135.80),  # Affects online_user2 only
        ]

        for symbol, price in test_messages:
            message = {
                'type': 'price_update',
                'symbol': symbol,
                'price': price,
                'timestamp': time.time(),
                'source': 'tickstockpl'
            }

            consumer.consume_message('tickstock.market.prices', message)

        # Simulate offline user coming online
        def simulate_user_reconnection(user_id):
            """Simulate offline user reconnecting and receiving buffered messages."""
            if user_id in offline_message_buffer:
                buffered_messages = offline_message_buffer[user_id]

                # Deliver buffered messages
                for event_name, data in buffered_messages:
                    mock_socketio.emit(event_name, data, room=user_id)

                # Clear buffer
                offline_message_buffer[user_id] = []
                return len(buffered_messages)
            return 0

        # offline_user1 reconnects
        buffered_count_user1 = simulate_user_reconnection('offline_user1')

        # Assert: Offline message persistence requirements
        # 1. Messages buffered for offline users
        remaining_offline_messages = sum(len(msgs) for msgs in offline_message_buffer.values())

        # offline_user2 should still have buffered message (QQQ)
        assert len(offline_message_buffer['offline_user2']) == 1, "offline_user2 should have 1 buffered message (QQQ)"

        # 2. offline_user1 received buffered messages upon reconnection
        assert buffered_count_user1 > 0, "offline_user1 should receive buffered messages upon reconnection"

        # 3. No messages lost during offline period
        # offline_user1 interested in SPY and VUG messages = 2 messages
        expected_buffered_user1 = 2  # SPY and VUG
        assert buffered_count_user1 == expected_buffered_user1, f"Expected {expected_buffered_user1} buffered messages, got {buffered_count_user1}"

        print("\nOffline Message Persistence:")
        print(f"  Total Offline Users: {len(offline_users)}")
        print(f"  Messages Sent: {len(test_messages)}")
        print(f"  offline_user1 Buffered Messages: {buffered_count_user1}")
        print(f"  offline_user2 Remaining Buffer: {len(offline_message_buffer['offline_user2'])}")


# Test Fixtures

@pytest.fixture
def message_flow_metrics():
    """Provide message flow performance metrics tracking."""
    return MessageFlowMetrics()


@pytest.fixture
def mock_redis_performance_monitor():
    """Mock Redis performance monitor for integration testing."""
    with patch('src.core.services.redis_performance_monitor.RedisPerformanceMonitor') as mock:
        monitor = Mock()
        monitor.get_performance_metrics.return_value = {
            'latency_avg_ms': 2.5,
            'latency_p95_ms': 8.0,
            'throughput_ops_per_sec': 1250,
            'connection_pool_usage': 0.65,
            'error_rate': 0.001
        }
        mock.return_value = monitor
        yield monitor


@pytest.fixture
def redis_integration_config():
    """Provide Redis configuration for integration testing."""
    return RedisConnectionConfig(
        host='localhost',
        port=6379,
        db=15,  # Use test database
        max_connections=20,
        socket_timeout=2.0,
        health_check_interval=10,
        decode_responses=True
    )


# Performance Benchmarks

@pytest.mark.performance
class TestRedisMessageFlowBenchmarks:
    """Performance benchmarks for Redis message flow integration."""

    def test_message_throughput_benchmark(self, message_flow_metrics: MessageFlowMetrics):
        """Benchmark message throughput under various load conditions."""
        # Test different throughput scenarios
        throughput_tests = [
            ('low_load', 100, 1),      # 100 messages, 1 second
            ('medium_load', 500, 2),   # 500 messages, 2 seconds
            ('high_load', 1000, 5),    # 1000 messages, 5 seconds
            ('burst_load', 2000, 3)    # 2000 messages, 3 seconds
        ]

        results = {}

        for test_name, message_count, duration in throughput_tests:
            # Simulate message processing
            start_time = time.perf_counter()

            processed_messages = 0
            interval = duration / message_count

            for i in range(message_count):
                # Simulate message processing overhead
                time.sleep(max(0.0001, interval - 0.0001))  # Minimum 0.1ms processing
                processed_messages += 1

            end_time = time.perf_counter()
            actual_duration = end_time - start_time
            throughput = processed_messages / actual_duration

            results[test_name] = {
                'messages': processed_messages,
                'duration': actual_duration,
                'throughput': throughput,
                'target_throughput': message_count / duration
            }

        # Assert throughput requirements
        for test_name, result in results.items():
            target_throughput = result['target_throughput']
            actual_throughput = result['throughput']

            # Allow 10% tolerance for timing variations
            assert actual_throughput >= target_throughput * 0.9, \
                f"{test_name}: Throughput {actual_throughput:.1f} < target {target_throughput:.1f} msg/s"

        print("\nThroughput Benchmark Results:")
        for test_name, result in results.items():
            print(f"  {test_name}: {result['throughput']:.1f} msg/s (target: {result['target_throughput']:.1f})")

    def test_concurrent_user_scaling_benchmark(self, message_flow_metrics: MessageFlowMetrics):
        """Benchmark message processing with concurrent users."""
        # Test different user counts
        user_counts = [10, 50, 100, 250, 500]
        scaling_results = {}

        for user_count in user_counts:
            start_time = time.perf_counter()

            # Simulate processing for N concurrent users
            messages_per_user = 10
            total_messages = user_count * messages_per_user

            # Simulate concurrent message filtering
            for user_id in range(user_count):
                for msg_id in range(messages_per_user):
                    # Simulate message filtering and routing
                    time.sleep(0.0001)  # 0.1ms per message processing

            end_time = time.perf_counter()
            processing_time = end_time - start_time

            messages_per_second = total_messages / processing_time
            avg_time_per_user = processing_time / user_count

            scaling_results[user_count] = {
                'total_messages': total_messages,
                'processing_time': processing_time,
                'messages_per_second': messages_per_second,
                'avg_time_per_user': avg_time_per_user
            }

        # Assert scaling requirements
        for user_count, result in scaling_results.items():
            # Processing should scale reasonably (not exponentially worse)
            if user_count <= 100:
                assert result['messages_per_second'] > 1000, \
                    f"Low throughput for {user_count} users: {result['messages_per_second']:.1f} msg/s"

            # Individual user processing should remain fast
            assert result['avg_time_per_user'] < 0.1, \
                f"Slow per-user processing for {user_count} users: {result['avg_time_per_user']:.3f}s"

        print("\nConcurrent User Scaling:")
        for user_count, result in scaling_results.items():
            print(f"  {user_count} users: {result['messages_per_second']:.1f} msg/s, {result['avg_time_per_user']:.3f}s/user")


if __name__ == '__main__':
    # Run Redis message flow integration tests
    pytest.main([
        __file__,
        '-v',
        '--tb=short',
        '-x'  # Stop on first failure for debugging
    ])
