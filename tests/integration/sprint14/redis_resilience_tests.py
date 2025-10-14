"""
Sprint 14 Redis Resilience Integration Tests

Tests Redis pub-sub resilience and failure/recovery scenarios for
the TickStockApp ↔ TickStockPL loose coupling architecture.

Validates:
- Redis connection failure and recovery
- Message queue overflow handling
- Network partition scenarios
- Service restart resilience
- Message delivery guarantees
- Performance degradation under stress
"""
import json
import threading
import time

import pytest
import redis

from tests.integration.sprint14.conftest import PERFORMANCE_TARGETS, SPRINT14_REDIS_CHANNELS


class TestRedisConnectionResilience:
    """Test Redis connection resilience and recovery scenarios"""

    @pytest.fixture
    def unstable_redis_client(self, redis_client):
        """Redis client that can simulate connection failures"""
        class UnstableRedisClient:
            def __init__(self, stable_client):
                self.stable_client = stable_client
                self.connection_failures = 0
                self.max_failures = 0
                self.failure_probability = 0.0
                self.simulate_failures = False

            def enable_failures(self, max_failures=3, probability=0.1):
                """Enable connection failure simulation"""
                self.simulate_failures = True
                self.max_failures = max_failures
                self.failure_probability = probability
                self.connection_failures = 0

            def disable_failures(self):
                """Disable connection failure simulation"""
                self.simulate_failures = False
                self.connection_failures = 0

            def _should_fail(self):
                """Determine if operation should fail"""
                if not self.simulate_failures:
                    return False
                if self.connection_failures >= self.max_failures:
                    return False
                import random
                return random.random() < self.failure_probability

            def publish(self, channel, message):
                """Publish with potential failure"""
                if self._should_fail():
                    self.connection_failures += 1
                    raise redis.ConnectionError(f"Simulated connection failure #{self.connection_failures}")
                return self.stable_client.publish(channel, message)

            def pubsub(self):
                """Get pubsub with potential failure"""
                if self._should_fail():
                    self.connection_failures += 1
                    raise redis.ConnectionError(f"Simulated pubsub connection failure #{self.connection_failures}")
                return self.stable_client.pubsub()

            def __getattr__(self, name):
                """Delegate other operations to stable client"""
                return getattr(self.stable_client, name)

        return UnstableRedisClient(redis_client)

    def test_connection_failure_and_recovery(
        self,
        unstable_redis_client,
        mock_tickstockpl_producer,
        redis_pubsub_listener,
        integration_performance_monitor
    ):
        """
        Test Redis connection failure and automatic recovery.
        
        Scenario:
        1. System operating normally
        2. Redis connection failures occur
        3. System detects failures and implements retry logic
        4. Connection recovers
        5. Message flow resumes normally
        """
        listener = redis_pubsub_listener(unstable_redis_client)
        listener.subscribe([SPRINT14_REDIS_CHANNELS['events']['quality_alert']])
        listener.start_listening()

        producer = mock_tickstockpl_producer(unstable_redis_client)

        try:
            # Phase 1: Normal operation
            normal_messages = []
            for i in range(5):
                message = {
                    'alert_type': 'connection_test',
                    'severity': 'low',
                    'description': f'Normal operation message {i}',
                    'phase': 'normal_operation',
                    'message_id': i
                }

                with integration_performance_monitor.measure_operation('normal_redis_operation'):
                    producer.publish_data_quality_alert(message)
                    normal_messages.append(message)
                time.sleep(0.05)

            # Phase 2: Enable connection failures
            unstable_redis_client.enable_failures(max_failures=3, probability=0.3)

            # Phase 3: Attempt operations during failures with retry logic
            failure_messages = []
            successful_retries = 0
            total_attempts = 0

            for i in range(10):
                message = {
                    'alert_type': 'connection_test',
                    'severity': 'medium',
                    'description': f'Failure scenario message {i}',
                    'phase': 'failure_testing',
                    'message_id': i + 100
                }

                # Implement retry logic
                retry_count = 0
                max_retries = 5
                success = False

                while retry_count < max_retries and not success:
                    try:
                        with integration_performance_monitor.measure_operation('redis_failure_retry'):
                            producer.publish_data_quality_alert(message)
                            success = True
                            successful_retries += 1
                            failure_messages.append(message)
                    except redis.ConnectionError as e:
                        retry_count += 1
                        total_attempts += 1
                        time.sleep(0.1 * retry_count)  # Exponential backoff

                        if retry_count >= max_retries:
                            print(f"Failed to send message {i} after {max_retries} retries: {e}")

                time.sleep(0.02)

            # Phase 4: Disable failures and test recovery
            unstable_redis_client.disable_failures()

            recovery_messages = []
            for i in range(5):
                message = {
                    'alert_type': 'connection_test',
                    'severity': 'low',
                    'description': f'Recovery message {i}',
                    'phase': 'recovery_testing',
                    'message_id': i + 200
                }

                with integration_performance_monitor.measure_operation('redis_recovery_operation'):
                    producer.publish_data_quality_alert(message)
                    recovery_messages.append(message)
                time.sleep(0.05)

            # Allow processing time
            time.sleep(2.0)

            # Validate resilience results
            all_messages = listener.get_messages(SPRINT14_REDIS_CHANNELS['events']['quality_alert'])

            # Filter messages by phase
            normal_received = [msg for msg in all_messages if msg['parsed_data']['phase'] == 'normal_operation']
            failure_received = [msg for msg in all_messages if msg['parsed_data']['phase'] == 'failure_testing']
            recovery_received = [msg for msg in all_messages if msg['parsed_data']['phase'] == 'recovery_testing']

            # Validate normal operation (should be perfect)
            assert len(normal_received) == 5, f"Expected 5 normal messages, got {len(normal_received)}"

            # Validate failure scenario (should have some success with retries)
            assert len(failure_received) >= 3, f"Expected ≥3 failure messages with retries, got {len(failure_received)}"
            assert successful_retries >= 3, f"Expected ≥3 successful retries, got {successful_retries}"

            # Validate recovery (should be perfect again)
            assert len(recovery_received) == 5, f"Expected 5 recovery messages, got {len(recovery_received)}"

            # Validate retry effectiveness
            retry_success_rate = successful_retries / 10 if successful_retries > 0 else 0
            assert retry_success_rate >= 0.7, f"Retry success rate {retry_success_rate:.1%} too low"

            # Performance validation
            integration_performance_monitor.assert_performance_target(
                'normal_redis_operation',
                PERFORMANCE_TARGETS['message_delivery_ms']
            )

            # Recovery should be fast
            integration_performance_monitor.assert_performance_target(
                'redis_recovery_operation',
                PERFORMANCE_TARGETS['message_delivery_ms']
            )

            print("Connection Resilience Results:")
            print(f"  Normal messages: {len(normal_received)}/5")
            print(f"  Failure messages: {len(failure_received)}/10")
            print(f"  Recovery messages: {len(recovery_received)}/5")
            print(f"  Successful retries: {successful_retries}")
            print(f"  Connection failures simulated: {unstable_redis_client.connection_failures}")

        finally:
            listener.stop_listening()
            unstable_redis_client.disable_failures()

    def test_pubsub_subscription_resilience(
        self,
        unstable_redis_client,
        mock_tickstockpl_producer,
        integration_performance_monitor
    ):
        """
        Test pub-sub subscription resilience during connection issues.
        
        Validates that subscribers can recover from connection drops
        and resume receiving messages.
        """
        producer = mock_tickstockpl_producer(unstable_redis_client)

        # Custom resilient listener
        class ResilientPubSubListener:
            def __init__(self, redis_client):
                self.redis_client = redis_client
                self.subscriptions = []
                self.received_messages = []
                self.reconnection_attempts = 0
                self.max_reconnections = 5

            def subscribe_with_resilience(self, channels):
                """Subscribe with automatic reconnection"""
                self.subscriptions = channels
                self._establish_subscription()

            def _establish_subscription(self):
                """Establish subscription with retry logic"""
                retry_count = 0
                while retry_count < self.max_reconnections:
                    try:
                        self.pubsub = self.redis_client.pubsub()
                        for channel in self.subscriptions:
                            self.pubsub.subscribe(channel)
                        return True
                    except redis.ConnectionError as e:
                        retry_count += 1
                        self.reconnection_attempts += 1
                        print(f"Subscription attempt {retry_count} failed: {e}")
                        time.sleep(0.5 * retry_count)  # Exponential backoff

                return False

            def listen_with_resilience(self, duration_seconds=3.0):
                """Listen with resilience to connection drops"""
                start_time = time.time()

                while time.time() - start_time < duration_seconds:
                    try:
                        # Try to get message with timeout
                        message = self.pubsub.get_message(timeout=0.1)
                        if message and message['type'] == 'message':
                            parsed_data = json.loads(message['data'])
                            self.received_messages.append({
                                'channel': message['channel'],
                                'data': parsed_data,
                                'timestamp': time.time()
                            })
                    except redis.ConnectionError as e:
                        print(f"Connection error during listen: {e}")
                        # Attempt to re-establish subscription
                        if self._establish_subscription():
                            print("Successfully re-established subscription")
                        else:
                            print("Failed to re-establish subscription")

                    except json.JSONDecodeError:
                        pass  # Ignore malformed messages

                    time.sleep(0.01)

        try:
            # Create resilient listener
            resilient_listener = ResilientPubSubListener(unstable_redis_client)

            with integration_performance_monitor.measure_operation('resilient_subscription_setup'):
                resilient_listener.subscribe_with_resilience([
                    SPRINT14_REDIS_CHANNELS['events']['quality_alert']
                ])

            # Phase 1: Normal publishing
            normal_messages = []
            for i in range(3):
                message = {
                    'alert_type': 'subscription_resilience_test',
                    'severity': 'low',
                    'description': f'Pre-failure message {i}',
                    'phase': 'pre_failure',
                    'message_id': i
                }
                producer.publish_data_quality_alert(message)
                normal_messages.append(message)
                time.sleep(0.1)

            # Start resilient listening
            listening_thread = threading.Thread(
                target=resilient_listener.listen_with_resilience,
                args=(5.0,),
                daemon=True
            )
            listening_thread.start()

            # Phase 2: Enable failures and continue publishing
            time.sleep(0.5)  # Let initial messages be received
            unstable_redis_client.enable_failures(max_failures=2, probability=0.4)

            failure_messages = []
            for i in range(5):
                message = {
                    'alert_type': 'subscription_resilience_test',
                    'severity': 'medium',
                    'description': f'During-failure message {i}',
                    'phase': 'during_failure',
                    'message_id': i + 100
                }

                try:
                    producer.publish_data_quality_alert(message)
                    failure_messages.append(message)
                except redis.ConnectionError:
                    pass  # Expected during failure simulation

                time.sleep(0.2)

            # Phase 3: Disable failures and continue
            unstable_redis_client.disable_failures()

            recovery_messages = []
            for i in range(3):
                message = {
                    'alert_type': 'subscription_resilience_test',
                    'severity': 'low',
                    'description': f'Post-failure message {i}',
                    'phase': 'post_failure',
                    'message_id': i + 200
                }
                producer.publish_data_quality_alert(message)
                recovery_messages.append(message)
                time.sleep(0.1)

            # Wait for listening to complete
            listening_thread.join(timeout=6.0)

            # Validate subscription resilience
            received_messages = resilient_listener.received_messages

            # Group messages by phase
            pre_failure = [msg for msg in received_messages if msg['data']['phase'] == 'pre_failure']
            during_failure = [msg for msg in received_messages if msg['data']['phase'] == 'during_failure']
            post_failure = [msg for msg in received_messages if msg['data']['phase'] == 'post_failure']

            # Validate message reception
            assert len(pre_failure) >= 2, f"Expected ≥2 pre-failure messages, got {len(pre_failure)}"
            assert len(during_failure) >= 1, f"Expected ≥1 during-failure messages, got {len(during_failure)}"
            assert len(post_failure) >= 2, f"Expected ≥2 post-failure messages, got {len(post_failure)}"

            # Validate reconnection attempts occurred
            assert resilient_listener.reconnection_attempts >= 1, "Expected reconnection attempts during failures"

            total_received = len(received_messages)
            assert total_received >= 5, f"Expected ≥5 total messages, got {total_received}"

            print("Subscription Resilience Results:")
            print(f"  Pre-failure messages: {len(pre_failure)}")
            print(f"  During-failure messages: {len(during_failure)}")
            print(f"  Post-failure messages: {len(post_failure)}")
            print(f"  Total received: {total_received}")
            print(f"  Reconnection attempts: {resilient_listener.reconnection_attempts}")

        finally:
            unstable_redis_client.disable_failures()


class TestRedisOverflowHandling:
    """Test Redis message queue overflow and backpressure scenarios"""

    def test_message_queue_overflow_handling(
        self,
        redis_client,
        mock_tickstockpl_producer,
        redis_pubsub_listener,
        integration_performance_monitor
    ):
        """
        Test handling of message queue overflow scenarios.
        
        Simulates high-volume message bursts that could overflow
        Redis message buffers and validates graceful degradation.
        """
        listener = redis_pubsub_listener(redis_client)
        listener.subscribe([SPRINT14_REDIS_CHANNELS['events']['quality_alert']])
        listener.start_listening()

        producer = mock_tickstockpl_producer(redis_client)

        try:
            # Phase 1: Baseline performance
            baseline_messages = []
            baseline_start = time.time()

            for i in range(10):
                message = {
                    'alert_type': 'overflow_test',
                    'severity': 'low',
                    'description': f'Baseline message {i}',
                    'phase': 'baseline',
                    'message_id': i
                }

                with integration_performance_monitor.measure_operation('baseline_message_publish'):
                    producer.publish_data_quality_alert(message)
                    baseline_messages.append(message)
                time.sleep(0.01)

            baseline_duration = time.time() - baseline_start

            # Phase 2: High-volume burst (potential overflow)
            burst_messages = []
            burst_start = time.time()
            burst_size = 500  # Large burst

            with integration_performance_monitor.measure_operation('burst_message_flood'):
                for i in range(burst_size):
                    message = {
                        'alert_type': 'overflow_test',
                        'severity': 'medium',
                        'description': f'Burst message {i}',
                        'phase': 'burst',
                        'message_id': i + 1000,
                        'burst_index': i
                    }

                    producer.publish_data_quality_alert(message)
                    burst_messages.append(message)

                    # No delay - maximum throughput test

            burst_duration = time.time() - burst_start

            # Phase 3: Recovery validation
            recovery_start = time.time()
            recovery_messages = []

            # Wait briefly for queue to settle
            time.sleep(0.5)

            for i in range(10):
                message = {
                    'alert_type': 'overflow_test',
                    'severity': 'low',
                    'description': f'Recovery message {i}',
                    'phase': 'recovery',
                    'message_id': i + 2000
                }

                with integration_performance_monitor.measure_operation('recovery_message_publish'):
                    producer.publish_data_quality_alert(message)
                    recovery_messages.append(message)
                time.sleep(0.01)

            recovery_duration = time.time() - recovery_start

            # Allow substantial processing time for burst
            time.sleep(3.0)

            # Collect and analyze results
            all_received = listener.get_messages(SPRINT14_REDIS_CHANNELS['events']['quality_alert'])

            baseline_received = [msg for msg in all_received if msg['parsed_data']['phase'] == 'baseline']
            burst_received = [msg for msg in all_received if msg['parsed_data']['phase'] == 'burst']
            recovery_received = [msg for msg in all_received if msg['parsed_data']['phase'] == 'recovery']

            # Calculate performance metrics
            baseline_retention = len(baseline_received) / len(baseline_messages)
            burst_retention = len(burst_received) / len(burst_messages)
            recovery_retention = len(recovery_received) / len(recovery_messages)

            # Validate overflow handling
            assert baseline_retention >= 0.9, f"Baseline retention {baseline_retention:.1%} too low"
            assert recovery_retention >= 0.9, f"Recovery retention {recovery_retention:.1%} too low"

            # Burst may have some loss but should retain substantial messages
            assert burst_retention >= 0.6, f"Burst retention {burst_retention:.1%} too low for overflow handling"

            # System should remain responsive after burst
            assert len(recovery_received) >= 8, f"System not responsive after burst: {len(recovery_received)}/10"

            # Performance degradation should be bounded
            performance_degradation = burst_duration / baseline_duration if baseline_duration > 0 else 1
            assert performance_degradation < 10.0, f"Performance degraded {performance_degradation:.1f}x during burst"

            print("Queue Overflow Results:")
            print(f"  Baseline: {len(baseline_received)}/{len(baseline_messages)} ({baseline_retention:.1%})")
            print(f"  Burst: {len(burst_received)}/{len(burst_messages)} ({burst_retention:.1%})")
            print(f"  Recovery: {len(recovery_received)}/{len(recovery_messages)} ({recovery_retention:.1%})")
            print(f"  Performance degradation: {performance_degradation:.1f}x")
            print(f"  Burst duration: {burst_duration:.2f}s ({burst_size/burst_duration:.0f} msg/s)")

        finally:
            listener.stop_listening()

    def test_memory_pressure_resilience(
        self,
        redis_client,
        mock_tickstockpl_producer,
        redis_pubsub_listener,
        integration_performance_monitor
    ):
        """
        Test system resilience under Redis memory pressure.
        
        Simulates memory pressure scenarios and validates
        that the system degrades gracefully without crashing.
        """
        listener = redis_pubsub_listener(redis_client)
        listener.subscribe([
            SPRINT14_REDIS_CHANNELS['events']['quality_alert'],
            SPRINT14_REDIS_CHANNELS['events']['patterns']
        ])
        listener.start_listening()

        producer = mock_tickstockpl_producer(redis_client)

        try:
            # Phase 1: Fill Redis with large messages to create memory pressure
            memory_pressure_messages = []
            large_payload_size = 1000  # Characters per message

            with integration_performance_monitor.measure_operation('memory_pressure_creation'):
                for i in range(100):
                    # Create large message payload
                    large_payload = "X" * large_payload_size

                    message = {
                        'alert_type': 'memory_pressure_test',
                        'severity': 'high',
                        'description': f'Large payload message {i}',
                        'phase': 'memory_pressure',
                        'message_id': i,
                        'large_data': large_payload,
                        'additional_data': {
                            'field1': large_payload[:100],
                            'field2': large_payload[100:200],
                            'field3': large_payload[200:300],
                            'metadata': {'size': len(large_payload)}
                        }
                    }

                    producer.publish_data_quality_alert(message)
                    memory_pressure_messages.append(message)

                    # Also publish patterns to increase memory usage
                    if i % 5 == 0:
                        pattern_message = {
                            'symbol': f'MEMORY_TEST_{i:03d}',
                            'pattern': 'Memory_Test_Pattern',
                            'confidence': 0.8,
                            'large_context': large_payload[:500]
                        }
                        producer.publish_pattern_event(pattern_message)

                    time.sleep(0.02)  # Slight delay to allow processing

            # Phase 2: Test normal operation under memory pressure
            normal_under_pressure = []

            for i in range(20):
                message = {
                    'alert_type': 'normal_under_pressure',
                    'severity': 'low',
                    'description': f'Normal message under pressure {i}',
                    'phase': 'normal_under_pressure',
                    'message_id': i + 3000
                }

                with integration_performance_monitor.measure_operation('normal_under_memory_pressure'):
                    producer.publish_data_quality_alert(message)
                    normal_under_pressure.append(message)
                time.sleep(0.05)

            # Phase 3: Memory cleanup and recovery test
            # Stop sending large messages and test recovery
            time.sleep(1.0)  # Allow Redis memory management

            recovery_messages = []
            for i in range(15):
                message = {
                    'alert_type': 'memory_recovery_test',
                    'severity': 'low',
                    'description': f'Memory recovery message {i}',
                    'phase': 'memory_recovery',
                    'message_id': i + 4000
                }

                with integration_performance_monitor.measure_operation('memory_recovery_operation'):
                    producer.publish_data_quality_alert(message)
                    recovery_messages.append(message)
                time.sleep(0.03)

            # Allow processing under memory pressure
            time.sleep(4.0)

            # Analyze memory pressure resilience
            all_received = listener.get_messages(SPRINT14_REDIS_CHANNELS['events']['quality_alert'])
            pattern_received = listener.get_messages(SPRINT14_REDIS_CHANNELS['events']['patterns'])

            pressure_received = [msg for msg in all_received if msg['parsed_data']['phase'] == 'memory_pressure']
            normal_received = [msg for msg in all_received if msg['parsed_data']['phase'] == 'normal_under_pressure']
            recovery_received = [msg for msg in all_received if msg['parsed_data']['phase'] == 'memory_recovery']

            # Calculate retention rates
            pressure_retention = len(pressure_received) / len(memory_pressure_messages)
            normal_retention = len(normal_received) / len(normal_under_pressure)
            recovery_retention = len(recovery_received) / len(recovery_messages)

            # Validate memory pressure handling
            # Large messages may have some loss due to memory constraints
            assert pressure_retention >= 0.5, f"Memory pressure retention {pressure_retention:.1%} too low"

            # Normal messages should still get through reasonably well
            assert normal_retention >= 0.7, f"Normal message retention {normal_retention:.1%} too low under pressure"

            # Recovery should be strong
            assert recovery_retention >= 0.8, f"Recovery retention {recovery_retention:.1%} indicates poor recovery"

            # Pattern messages should also have reasonable retention
            pattern_retention = len(pattern_received) / 20 if pattern_received else 0
            assert pattern_retention >= 0.6, f"Pattern retention {pattern_retention:.1%} too low under memory pressure"

            # System should maintain basic functionality
            total_received = len(all_received)
            assert total_received >= 50, f"System appears non-functional: only {total_received} total messages"

            print("Memory Pressure Resilience Results:")
            print(f"  Large message retention: {pressure_retention:.1%}")
            print(f"  Normal under pressure: {normal_retention:.1%}")
            print(f"  Recovery retention: {recovery_retention:.1%}")
            print(f"  Pattern retention: {pattern_retention:.1%}")
            print(f"  Total messages processed: {total_received}")

        finally:
            listener.stop_listening()


class TestNetworkPartitionScenarios:
    """Test network partition and split-brain scenarios"""

    def test_network_partition_resilience(
        self,
        redis_client,
        mock_tickstockpl_producer,
        redis_pubsub_listener,
        integration_performance_monitor
    ):
        """
        Test resilience during network partition scenarios.
        
        Simulates network partitions between Redis and clients,
        validates message buffering and recovery behavior.
        """
        listener = redis_pubsub_listener(redis_client)
        listener.subscribe([SPRINT14_REDIS_CHANNELS['events']['quality_alert']])
        listener.start_listening()

        producer = mock_tickstockpl_producer(redis_client)

        # Network partition simulator
        class NetworkPartitionSimulator:
            def __init__(self):
                self.partition_active = False
                self.buffered_messages = []

            def enable_partition(self):
                """Simulate network partition"""
                self.partition_active = True
                self.buffered_messages = []

            def disable_partition(self):
                """Simulate network recovery"""
                self.partition_active = False

            def simulate_publish(self, producer_func, *args, **kwargs):
                """Simulate publish with partition handling"""
                if self.partition_active:
                    # Buffer message during partition
                    self.buffered_messages.append(('publish', args, kwargs))
                    raise redis.ConnectionError("Simulated network partition")
                # Normal publish
                return producer_func(*args, **kwargs)

            def replay_buffered_messages(self, producer_func):
                """Replay buffered messages after partition recovery"""
                replayed = 0
                for msg_type, args, kwargs in self.buffered_messages:
                    try:
                        producer_func(*args, **kwargs)
                        replayed += 1
                    except Exception as e:
                        print(f"Failed to replay message: {e}")

                self.buffered_messages = []
                return replayed

        partition_sim = NetworkPartitionSimulator()

        try:
            # Phase 1: Normal operation before partition
            pre_partition_messages = []

            for i in range(5):
                message = {
                    'alert_type': 'partition_test',
                    'severity': 'low',
                    'description': f'Pre-partition message {i}',
                    'phase': 'pre_partition',
                    'message_id': i
                }

                with integration_performance_monitor.measure_operation('pre_partition_publish'):
                    producer.publish_data_quality_alert(message)
                    pre_partition_messages.append(message)
                time.sleep(0.05)

            # Phase 2: Simulate network partition
            partition_sim.enable_partition()

            partition_messages = []
            partition_failures = 0

            for i in range(8):
                message = {
                    'alert_type': 'partition_test',
                    'severity': 'medium',
                    'description': f'During-partition message {i}',
                    'phase': 'during_partition',
                    'message_id': i + 100
                }

                try:
                    partition_sim.simulate_publish(
                        producer.publish_data_quality_alert,
                        message
                    )
                    partition_messages.append(message)
                except redis.ConnectionError:
                    partition_failures += 1
                    partition_messages.append(message)  # Still track for replay

                time.sleep(0.03)

            # Phase 3: Network recovery and message replay
            time.sleep(0.5)  # Partition duration
            partition_sim.disable_partition()

            with integration_performance_monitor.measure_operation('partition_recovery'):
                # Replay buffered messages
                replayed_count = partition_sim.replay_buffered_messages(
                    producer.publish_data_quality_alert
                )

            # Phase 4: Normal operation after recovery
            post_recovery_messages = []

            for i in range(5):
                message = {
                    'alert_type': 'partition_test',
                    'severity': 'low',
                    'description': f'Post-recovery message {i}',
                    'phase': 'post_recovery',
                    'message_id': i + 200
                }

                with integration_performance_monitor.measure_operation('post_recovery_publish'):
                    producer.publish_data_quality_alert(message)
                    post_recovery_messages.append(message)
                time.sleep(0.05)

            # Allow processing time
            time.sleep(2.0)

            # Analyze partition resilience
            all_received = listener.get_messages(SPRINT14_REDIS_CHANNELS['events']['quality_alert'])

            pre_partition_received = [msg for msg in all_received if msg['parsed_data']['phase'] == 'pre_partition']
            during_partition_received = [msg for msg in all_received if msg['parsed_data']['phase'] == 'during_partition']
            post_recovery_received = [msg for msg in all_received if msg['parsed_data']['phase'] == 'post_recovery']

            # Calculate resilience metrics
            pre_retention = len(pre_partition_received) / len(pre_partition_messages)
            during_retention = len(during_partition_received) / len(partition_messages)
            post_retention = len(post_recovery_received) / len(post_recovery_messages)

            # Validate partition handling
            assert pre_retention >= 0.9, f"Pre-partition retention {pre_retention:.1%} too low"
            assert post_retention >= 0.9, f"Post-recovery retention {post_retention:.1%} too low"

            # During partition, messages should be buffered and replayed
            assert during_retention >= 0.6, f"Partition recovery {during_retention:.1%} indicates poor buffering"

            # Validate failure detection
            assert partition_failures >= 5, f"Expected partition failures, got {partition_failures}"

            # Validate message replay
            assert replayed_count >= 5, f"Expected message replay, got {replayed_count}"

            # System should recover completely
            total_expected = len(pre_partition_messages) + len(partition_messages) + len(post_recovery_messages)
            total_received = len(all_received)
            overall_retention = total_received / total_expected

            assert overall_retention >= 0.8, f"Overall partition resilience {overall_retention:.1%} too low"

            print("Network Partition Resilience Results:")
            print(f"  Pre-partition: {len(pre_partition_received)}/{len(pre_partition_messages)} ({pre_retention:.1%})")
            print(f"  During partition: {len(during_partition_received)}/{len(partition_messages)} ({during_retention:.1%})")
            print(f"  Post-recovery: {len(post_recovery_received)}/{len(post_recovery_messages)} ({post_retention:.1%})")
            print(f"  Partition failures: {partition_failures}")
            print(f"  Messages replayed: {replayed_count}")
            print(f"  Overall retention: {overall_retention:.1%}")

        finally:
            listener.stop_listening()


class TestServiceRestartResilience:
    """Test service restart and recovery scenarios"""

    def test_service_restart_message_continuity(
        self,
        redis_client,
        mock_tickstockpl_producer,
        redis_pubsub_listener,
        integration_performance_monitor
    ):
        """
        Test message continuity across service restarts.
        
        Simulates TickStockApp and TickStockPL service restarts
        and validates that message flow resumes properly.
        """
        # First listener instance (before restart)
        listener1 = redis_pubsub_listener(redis_client)
        listener1.subscribe([SPRINT14_REDIS_CHANNELS['events']['quality_alert']])
        listener1.start_listening()

        producer = mock_tickstockpl_producer(redis_client)

        try:
            # Phase 1: Normal operation before restart
            pre_restart_messages = []

            for i in range(5):
                message = {
                    'alert_type': 'service_restart_test',
                    'severity': 'low',
                    'description': f'Pre-restart message {i}',
                    'phase': 'pre_restart',
                    'service_instance': 'instance_1',
                    'message_id': i
                }

                with integration_performance_monitor.measure_operation('pre_restart_publish'):
                    producer.publish_data_quality_alert(message)
                    pre_restart_messages.append(message)
                time.sleep(0.05)

            # Allow processing
            time.sleep(0.5)
            pre_restart_received = listener1.get_messages(SPRINT14_REDIS_CHANNELS['events']['quality_alert'])

            # Phase 2: Simulate service restart (disconnect first listener)
            listener1.stop_listening()

            # Messages published during "service down" period
            during_restart_messages = []

            for i in range(3):
                message = {
                    'alert_type': 'service_restart_test',
                    'severity': 'medium',
                    'description': f'During-restart message {i}',
                    'phase': 'during_restart',
                    'service_instance': 'transitioning',
                    'message_id': i + 100
                }

                producer.publish_data_quality_alert(message)
                during_restart_messages.append(message)
                time.sleep(0.1)

            # Phase 3: Service restart complete (new listener instance)
            time.sleep(0.3)  # Restart delay

            listener2 = redis_pubsub_listener(redis_client)
            listener2.subscribe([SPRINT14_REDIS_CHANNELS['events']['quality_alert']])
            listener2.start_listening()

            # Phase 4: Normal operation after restart
            post_restart_messages = []

            for i in range(7):
                message = {
                    'alert_type': 'service_restart_test',
                    'severity': 'low',
                    'description': f'Post-restart message {i}',
                    'phase': 'post_restart',
                    'service_instance': 'instance_2',
                    'message_id': i + 200
                }

                with integration_performance_monitor.measure_operation('post_restart_publish'):
                    producer.publish_data_quality_alert(message)
                    post_restart_messages.append(message)
                time.sleep(0.05)

            # Allow processing
            time.sleep(1.0)
            post_restart_received = listener2.get_messages(SPRINT14_REDIS_CHANNELS['events']['quality_alert'])

            # Analyze restart resilience
            pre_restart_filtered = [
                msg for msg in pre_restart_received
                if msg['parsed_data']['phase'] == 'pre_restart'
            ]

            post_restart_filtered = [
                msg for msg in post_restart_received
                if msg['parsed_data']['phase'] == 'post_restart'
            ]

            # During restart messages might be lost (acceptable)
            # but service should recover completely

            # Validate pre-restart operation
            pre_retention = len(pre_restart_filtered) / len(pre_restart_messages)
            assert pre_retention >= 0.8, f"Pre-restart retention {pre_retention:.1%} too low"

            # Validate post-restart recovery
            post_retention = len(post_restart_filtered) / len(post_restart_messages)
            assert post_retention >= 0.8, f"Post-restart retention {post_retention:.1%} indicates poor recovery"

            # Service should be fully functional after restart
            assert len(post_restart_filtered) >= 5, f"Service not fully recovered: {len(post_restart_filtered)}/7"

            # Validate service instance tracking
            pre_instances = set(msg['parsed_data']['service_instance'] for msg in pre_restart_filtered)
            post_instances = set(msg['parsed_data']['service_instance'] for msg in post_restart_filtered)

            assert 'instance_1' in pre_instances, "Pre-restart instance not tracked"
            assert 'instance_2' in post_instances, "Post-restart instance not tracked"

            print("Service Restart Resilience Results:")
            print(f"  Pre-restart: {len(pre_restart_filtered)}/{len(pre_restart_messages)} ({pre_retention:.1%})")
            print(f"  Post-restart: {len(post_restart_filtered)}/{len(post_restart_messages)} ({post_retention:.1%})")
            print(f"  During restart: {len(during_restart_messages)} messages (expected loss)")
            print(f"  Service instances: {pre_instances} → {post_instances}")

            # Performance validation
            integration_performance_monitor.assert_performance_target(
                'pre_restart_publish',
                PERFORMANCE_TARGETS['message_delivery_ms']
            )

            integration_performance_monitor.assert_performance_target(
                'post_restart_publish',
                PERFORMANCE_TARGETS['message_delivery_ms']
            )

        finally:
            if 'listener2' in locals():
                listener2.stop_listening()


class TestRedisClusterResilience:
    """Test Redis cluster and high availability scenarios"""

    def test_redis_failover_simulation(
        self,
        redis_client,
        mock_tickstockpl_producer,
        redis_pubsub_listener,
        integration_performance_monitor
    ):
        """
        Test Redis failover scenarios and automatic recovery.
        
        Simulates Redis master failover and validates that the system
        can handle primary/replica transitions gracefully.
        """
        listener = redis_pubsub_listener(redis_client)
        listener.subscribe([
            SPRINT14_REDIS_CHANNELS['events']['quality_alert'],
            SPRINT14_REDIS_CHANNELS['events']['patterns']
        ])
        listener.start_listening()

        producer = mock_tickstockpl_producer(redis_client)

        # Failover simulator
        class RedisFailoverSimulator:
            def __init__(self):
                self.master_active = True
                self.failover_in_progress = False
                self.operations_during_failover = []

            def trigger_failover(self):
                """Simulate master failover"""
                self.master_active = False
                self.failover_in_progress = True

            def complete_failover(self):
                """Complete failover to new master"""
                self.failover_in_progress = False
                self.master_active = True

            def simulate_operation(self, operation_func, *args, **kwargs):
                """Simulate operation during potential failover"""
                if self.failover_in_progress:
                    self.operations_during_failover.append((operation_func.__name__, args, kwargs))
                    raise redis.ConnectionError("Redis failover in progress")
                if not self.master_active:
                    raise redis.ReadOnlyError("Redis master unavailable")
                return operation_func(*args, **kwargs)

        failover_sim = RedisFailoverSimulator()

        try:
            # Phase 1: Normal operation before failover
            pre_failover_messages = []

            for i in range(5):
                message = {
                    'alert_type': 'redis_failover_test',
                    'severity': 'low',
                    'description': f'Pre-failover message {i}',
                    'phase': 'pre_failover',
                    'redis_master': 'original',
                    'message_id': i
                }

                with integration_performance_monitor.measure_operation('pre_failover_operation'):
                    producer.publish_data_quality_alert(message)
                    pre_failover_messages.append(message)
                time.sleep(0.05)

            # Phase 2: Trigger Redis failover
            failover_sim.trigger_failover()

            # Operations during failover (should fail gracefully)
            failover_messages = []
            failover_errors = 0

            for i in range(6):
                message = {
                    'alert_type': 'redis_failover_test',
                    'severity': 'high',
                    'description': f'During-failover message {i}',
                    'phase': 'during_failover',
                    'redis_master': 'failing_over',
                    'message_id': i + 100
                }

                try:
                    failover_sim.simulate_operation(
                        producer.publish_data_quality_alert,
                        message
                    )
                    failover_messages.append(message)
                except (redis.ConnectionError, redis.ReadOnlyError):
                    failover_errors += 1
                    failover_messages.append(message)  # Track for retry

                time.sleep(0.08)

            # Phase 3: Complete failover (new master active)
            time.sleep(0.4)  # Failover duration
            failover_sim.complete_failover()

            # Phase 4: Retry failed operations and normal operation
            post_failover_messages = []
            retry_successes = 0

            # Retry operations that failed during failover
            for i, message in enumerate(failover_messages):
                if message['phase'] == 'during_failover':
                    try:
                        with integration_performance_monitor.measure_operation('failover_retry'):
                            producer.publish_data_quality_alert(message)
                        retry_successes += 1
                    except Exception as e:
                        print(f"Retry failed for message {i}: {e}")

            # Normal operation with new master
            for i in range(6):
                message = {
                    'alert_type': 'redis_failover_test',
                    'severity': 'low',
                    'description': f'Post-failover message {i}',
                    'phase': 'post_failover',
                    'redis_master': 'new_master',
                    'message_id': i + 200
                }

                with integration_performance_monitor.measure_operation('post_failover_operation'):
                    producer.publish_data_quality_alert(message)
                    post_failover_messages.append(message)
                time.sleep(0.05)

            # Publish some patterns to test different message types
            for i in range(3):
                pattern_data = {
                    'symbol': f'FAILOVER_STOCK_{i}',
                    'pattern': 'Failover_Recovery_Pattern',
                    'confidence': 0.9,
                    'redis_master': 'new_master'
                }
                producer.publish_pattern_event(pattern_data)

            # Allow processing
            time.sleep(1.5)

            # Analyze failover resilience
            all_received = listener.get_messages(SPRINT14_REDIS_CHANNELS['events']['quality_alert'])
            pattern_received = listener.get_messages(SPRINT14_REDIS_CHANNELS['events']['patterns'])

            pre_failover_received = [msg for msg in all_received if msg['parsed_data']['phase'] == 'pre_failover']
            during_failover_received = [msg for msg in all_received if msg['parsed_data']['phase'] == 'during_failover']
            post_failover_received = [msg for msg in all_received if msg['parsed_data']['phase'] == 'post_failover']

            # Calculate failover resilience metrics
            pre_retention = len(pre_failover_received) / len(pre_failover_messages)
            during_retention = len(during_failover_received) / len(failover_messages)
            post_retention = len(post_failover_received) / len(post_failover_messages)

            # Validate failover handling
            assert pre_retention >= 0.8, f"Pre-failover retention {pre_retention:.1%} too low"
            assert post_retention >= 0.8, f"Post-failover retention {post_retention:.1%} indicates poor recovery"

            # During failover should have errors but eventual delivery through retries
            assert failover_errors >= 3, f"Expected failover errors, got {failover_errors}"
            assert during_retention >= 0.5, f"Failover recovery {during_retention:.1%} too low"

            # Retry mechanism should be effective
            retry_success_rate = retry_successes / failover_errors if failover_errors > 0 else 0
            assert retry_success_rate >= 0.7, f"Retry success rate {retry_success_rate:.1%} too low"

            # Pattern messages should also recover
            assert len(pattern_received) >= 2, f"Pattern messages not recovered: {len(pattern_received)}/3"

            # System should be fully operational after failover
            total_expected = len(pre_failover_messages) + len(post_failover_messages)
            total_core_received = len(pre_failover_received) + len(post_failover_received)
            core_system_health = total_core_received / total_expected

            assert core_system_health >= 0.85, f"Core system health {core_system_health:.1%} after failover"

            print("Redis Failover Resilience Results:")
            print(f"  Pre-failover: {len(pre_failover_received)}/{len(pre_failover_messages)} ({pre_retention:.1%})")
            print(f"  During failover: {len(during_failover_received)}/{len(failover_messages)} ({during_retention:.1%})")
            print(f"  Post-failover: {len(post_failover_received)}/{len(post_failover_messages)} ({post_retention:.1%})")
            print(f"  Failover errors: {failover_errors}")
            print(f"  Retry successes: {retry_successes}")
            print(f"  pattern discovery: {len(pattern_received)}/3")
            print(f"  Core system health: {core_system_health:.1%}")

        finally:
            listener.stop_listening()
