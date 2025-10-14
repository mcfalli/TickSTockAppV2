"""
Sprint 14 Performance Integration Tests

Tests performance requirements across all Sprint 14 phases with
specific focus on <100ms message delivery and system responsiveness
targets for TickStockApp ↔ TickStockPL integration.

Performance Targets:
- Message Delivery: <100ms end-to-end
- Database Queries: <50ms
- Redis Operations: <10ms  
- WebSocket Broadcast: <50ms
- End-to-End Workflows: <500ms
"""
import statistics
import threading
import time

from sqlalchemy import text

from tests.integration.sprint14.conftest import PERFORMANCE_TARGETS, SPRINT14_REDIS_CHANNELS


class TestMessageDeliveryPerformance:
    """Test <100ms message delivery performance requirements"""

    def test_redis_pubsub_message_delivery_latency(
        self,
        redis_client,
        mock_tickstockpl_producer,
        redis_pubsub_listener,
        integration_performance_monitor
    ):
        """
        Test Redis pub-sub message delivery latency <100ms.
        
        Measures end-to-end latency from message publish to
        subscriber receipt across all Sprint 14 event channels.
        """
        listener = redis_pubsub_listener(redis_client)
        all_channels = list(SPRINT14_REDIS_CHANNELS['events'].values())
        listener.subscribe(all_channels)
        listener.start_listening()

        producer = mock_tickstockpl_producer(redis_client)

        # Performance tracking
        class LatencyTracker:
            def __init__(self):
                self.measurements = []

            def start_measurement(self):
                """Start latency measurement"""
                return time.perf_counter()

            def record_latency(self, start_time, operation_type):
                """Record latency measurement"""
                end_time = time.perf_counter()
                latency_ms = (end_time - start_time) * 1000
                self.measurements.append({
                    'operation': operation_type,
                    'latency_ms': latency_ms,
                    'timestamp': start_time
                })
                return latency_ms

            def get_statistics(self):
                """Calculate latency statistics"""
                if not self.measurements:
                    return {}

                latencies = [m['latency_ms'] for m in self.measurements]
                return {
                    'count': len(latencies),
                    'mean': statistics.mean(latencies),
                    'median': statistics.median(latencies),
                    'p95': statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies),
                    'p99': statistics.quantiles(latencies, n=100)[98] if len(latencies) >= 100 else max(latencies),
                    'min': min(latencies),
                    'max': max(latencies)
                }

        latency_tracker = LatencyTracker()

        try:
            # Test different message types for latency
            test_scenarios = [
                # Phase 1: ETF and EOD messages
                {
                    'message_type': 'etf_update',
                    'channel_func': producer.publish_etf_data_update,
                    'channel': SPRINT14_REDIS_CHANNELS['events']['etf_updated'],
                    'data': {
                        'symbol': 'PERF_ETF',
                        'aum_millions': 5000.0,
                        'expense_ratio': 0.0075
                    }
                },
                {
                    'message_type': 'eod_completion',
                    'channel_func': producer.publish_eod_completion,
                    'channel': SPRINT14_REDIS_CHANNELS['events']['eod_complete'],
                    'data': {
                        'symbols_processed': 4200,
                        'success_rate': 0.976,
                        'processing_time_seconds': 3600
                    }
                },

                # Phase 2: IPO and Quality messages
                {
                    'message_type': 'ipo_detection',
                    'channel_func': producer.publish_ipo_detection,
                    'channel': SPRINT14_REDIS_CHANNELS['events']['ipo_detected'],
                    'data': {
                        'symbol': 'PERF_IPO',
                        'market_cap': 8000.0,
                        'sector': 'Technology'
                    }
                },
                {
                    'message_type': 'quality_alert',
                    'channel_func': producer.publish_data_quality_alert,
                    'channel': SPRINT14_REDIS_CHANNELS['events']['quality_alert'],
                    'data': {
                        'symbol': 'PERF_STOCK',
                        'alert_type': 'performance_test',
                        'severity': 'low',
                        'description': 'Performance test alert'
                    }
                },

                # Pattern detection messages
                {
                    'message_type': 'pattern_detection',
                    'channel_func': producer.publish_pattern_event,
                    'channel': SPRINT14_REDIS_CHANNELS['events']['patterns'],
                    'data': {
                        'symbol': 'PERF_PATTERN',
                        'pattern': 'Doji',
                        'confidence': 0.85
                    }
                }
            ]

            # Run latency tests for each scenario
            for scenario in test_scenarios:
                for iteration in range(20):  # 20 measurements per scenario

                    # Add timestamp to message for latency calculation
                    message_data = scenario['data'].copy()
                    message_data['perf_test_timestamp'] = time.perf_counter()

                    # Publish message and measure
                    start_time = latency_tracker.start_measurement()

                    if scenario['message_type'] == 'etf_update':
                        scenario['channel_func'](message_data['symbol'], message_data)
                    elif scenario['message_type'] == 'eod_completion':
                        scenario['channel_func'](message_data)
                    elif scenario['message_type'] == 'ipo_detection':
                        scenario['channel_func'](message_data['symbol'], message_data)
                    elif scenario['message_type'] == 'quality_alert' or scenario['message_type'] == 'pattern_detection':
                        scenario['channel_func'](message_data)

                    # Small delay between messages
                    time.sleep(0.01)

            # Allow processing time
            time.sleep(2.0)

            # Calculate received message latencies
            received_latencies = []

            for channel in all_channels:
                channel_messages = listener.get_messages(channel)
                for msg in channel_messages:
                    data = msg.get('parsed_data', {})
                    if 'perf_test_timestamp' in data:
                        received_time = time.perf_counter()
                        sent_time = data['perf_test_timestamp']
                        latency_ms = (received_time - sent_time) * 1000
                        received_latencies.append(latency_ms)

            # Performance analysis
            if received_latencies:
                latency_stats = {
                    'count': len(received_latencies),
                    'mean': statistics.mean(received_latencies),
                    'median': statistics.median(received_latencies),
                    'p95': statistics.quantiles(received_latencies, n=20)[18] if len(received_latencies) >= 20 else max(received_latencies),
                    'max': max(received_latencies),
                    'min': min(received_latencies)
                }
            else:
                latency_stats = {'count': 0}

            # Validate performance requirements
            assert len(received_latencies) >= 80, f"Expected ≥80 latency measurements, got {len(received_latencies)}"

            # <100ms requirement validation
            assert latency_stats['mean'] < PERFORMANCE_TARGETS['message_delivery_ms'], (
                f"Mean latency {latency_stats['mean']:.2f}ms exceeds {PERFORMANCE_TARGETS['message_delivery_ms']}ms target"
            )

            assert latency_stats['p95'] < PERFORMANCE_TARGETS['message_delivery_ms'] * 1.5, (
                f"P95 latency {latency_stats['p95']:.2f}ms exceeds reasonable bounds"
            )

            # Most messages should be well under target
            under_target_count = sum(1 for lat in received_latencies if lat < PERFORMANCE_TARGETS['message_delivery_ms'])
            under_target_rate = under_target_count / len(received_latencies)

            assert under_target_rate >= 0.85, (
                f"Only {under_target_rate:.1%} of messages under {PERFORMANCE_TARGETS['message_delivery_ms']}ms target"
            )

            print("Message Delivery Performance Results:")
            print(f"  Messages measured: {latency_stats['count']}")
            print(f"  Mean latency: {latency_stats['mean']:.2f}ms")
            print(f"  Median latency: {latency_stats['median']:.2f}ms")
            print(f"  P95 latency: {latency_stats['p95']:.2f}ms")
            print(f"  Max latency: {latency_stats['max']:.2f}ms")
            print(f"  Under target rate: {under_target_rate:.1%}")

        finally:
            listener.stop_listening()

    def test_high_frequency_message_performance(
        self,
        redis_client,
        mock_tickstockpl_producer,
        redis_pubsub_listener,
        integration_performance_monitor
    ):
        """
        Test performance under high message frequency.
        
        Validates that system maintains <100ms latency
        even under high-frequency message loads.
        """
        listener = redis_pubsub_listener(redis_client)
        listener.subscribe([SPRINT14_REDIS_CHANNELS['events']['patterns']])
        listener.start_listening()

        producer = mock_tickstockpl_producer(redis_client)

        # High frequency test parameters
        message_bursts = [
            {'rate_per_second': 50, 'duration_seconds': 2, 'burst_name': 'medium_frequency'},
            {'rate_per_second': 100, 'duration_seconds': 1, 'burst_name': 'high_frequency'},
            {'rate_per_second': 200, 'duration_seconds': 0.5, 'burst_name': 'very_high_frequency'}
        ]

        all_latencies = []

        try:
            for burst_config in message_bursts:
                burst_latencies = []
                messages_sent = 0

                burst_start = time.perf_counter()
                target_interval = 1.0 / burst_config['rate_per_second']

                while (time.perf_counter() - burst_start) < burst_config['duration_seconds']:
                    message_timestamp = time.perf_counter()

                    pattern_data = {
                        'symbol': f'HIGH_FREQ_{messages_sent:04d}',
                        'pattern': ['Doji', 'Hammer', 'Engulfing'][messages_sent % 3],
                        'confidence': 0.8 + (messages_sent * 0.001),
                        'burst_type': burst_config['burst_name'],
                        'perf_test_timestamp': message_timestamp,
                        'sequence_id': messages_sent
                    }

                    with integration_performance_monitor.measure_operation(f"high_freq_{burst_config['burst_name']}"):
                        producer.publish_pattern_event(pattern_data)

                    messages_sent += 1

                    # Maintain target frequency
                    next_send_time = burst_start + (messages_sent * target_interval)
                    sleep_time = next_send_time - time.perf_counter()
                    if sleep_time > 0:
                        time.sleep(sleep_time)

                print(f"Sent {messages_sent} messages for {burst_config['burst_name']} burst")
                time.sleep(0.5)  # Brief pause between bursts

            # Allow processing time
            time.sleep(3.0)

            # Analyze received messages and calculate latencies
            pattern_messages = listener.get_messages(SPRINT14_REDIS_CHANNELS['events']['patterns'])

            burst_performance = {}

            for msg in pattern_messages:
                data = msg.get('parsed_data', {})
                if 'perf_test_timestamp' in data and 'burst_type' in data:
                    received_time = time.perf_counter()
                    sent_time = data['perf_test_timestamp']
                    latency_ms = (received_time - sent_time) * 1000

                    burst_type = data['burst_type']
                    if burst_type not in burst_performance:
                        burst_performance[burst_type] = []

                    burst_performance[burst_type].append(latency_ms)
                    all_latencies.append(latency_ms)

            # Performance validation for each burst type
            for burst_type, latencies in burst_performance.items():
                if latencies:
                    mean_latency = statistics.mean(latencies)
                    max_latency = max(latencies)
                    p95_latency = statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max_latency

                    # Performance requirements under load
                    assert mean_latency < PERFORMANCE_TARGETS['message_delivery_ms'] * 1.5, (
                        f"{burst_type}: Mean latency {mean_latency:.2f}ms too high under load"
                    )

                    assert p95_latency < PERFORMANCE_TARGETS['message_delivery_ms'] * 2.0, (
                        f"{burst_type}: P95 latency {p95_latency:.2f}ms too high under load"
                    )

                    print(f"High Frequency Performance - {burst_type}:")
                    print(f"  Messages: {len(latencies)}")
                    print(f"  Mean latency: {mean_latency:.2f}ms")
                    print(f"  P95 latency: {p95_latency:.2f}ms")
                    print(f"  Max latency: {max_latency:.2f}ms")

            # Overall high frequency performance
            if all_latencies:
                overall_mean = statistics.mean(all_latencies)
                overall_p95 = statistics.quantiles(all_latencies, n=20)[18] if len(all_latencies) >= 20 else max(all_latencies)

                # System should maintain reasonable performance under high load
                assert overall_mean < PERFORMANCE_TARGETS['message_delivery_ms'] * 2.0, (
                    f"Overall high-frequency mean latency {overall_mean:.2f}ms too high"
                )

                under_target_count = sum(1 for lat in all_latencies if lat < PERFORMANCE_TARGETS['message_delivery_ms'])
                under_target_rate = under_target_count / len(all_latencies)

                # Should maintain good performance for substantial portion of messages
                assert under_target_rate >= 0.6, (
                    f"Only {under_target_rate:.1%} of high-frequency messages under target"
                )

                print("Overall High Frequency Results:")
                print(f"  Total messages: {len(all_latencies)}")
                print(f"  Overall mean: {overall_mean:.2f}ms")
                print(f"  Overall P95: {overall_p95:.2f}ms")
                print(f"  Under target rate: {under_target_rate:.1%}")

        finally:
            listener.stop_listening()

    def test_concurrent_channel_performance(
        self,
        redis_client,
        mock_tickstockpl_producer,
        redis_pubsub_listener,
        integration_performance_monitor
    ):
        """
        Test performance with concurrent activity across multiple channels.
        
        Validates that multi-channel publishing doesn't degrade
        individual channel performance below targets.
        """
        listener = redis_pubsub_listener(redis_client)
        test_channels = [
            SPRINT14_REDIS_CHANNELS['events']['patterns'],
            SPRINT14_REDIS_CHANNELS['events']['quality_alert'],
            SPRINT14_REDIS_CHANNELS['events']['etf_updated']
        ]
        listener.subscribe(test_channels)
        listener.start_listening()

        producer = mock_tickstockpl_producer(redis_client)

        # Concurrent publishing threads
        channel_performance = {}
        thread_results = {'errors': 0}

        def publish_patterns(duration_seconds=2.0):
            """Publish pattern messages concurrently"""
            channel_latencies = []
            messages_sent = 0
            start_time = time.perf_counter()

            try:
                while (time.perf_counter() - start_time) < duration_seconds:
                    message_time = time.perf_counter()

                    pattern_data = {
                        'symbol': f'CONCURRENT_PATTERN_{messages_sent:03d}',
                        'pattern': 'Concurrent_Test',
                        'confidence': 0.85,
                        'perf_test_timestamp': message_time,
                        'thread': 'patterns'
                    }

                    producer.publish_pattern_event(pattern_data)
                    messages_sent += 1
                    time.sleep(0.05)  # 20 messages per second

            except Exception as e:
                thread_results['errors'] += 1
                print(f"Pattern thread error: {e}")

            channel_performance['patterns'] = {'sent': messages_sent, 'latencies': []}

        def publish_quality_alerts(duration_seconds=2.0):
            """Publish quality alerts concurrently"""
            messages_sent = 0
            start_time = time.perf_counter()

            try:
                while (time.perf_counter() - start_time) < duration_seconds:
                    message_time = time.perf_counter()

                    alert_data = {
                        'alert_type': 'concurrent_performance_test',
                        'severity': 'low',
                        'symbol': f'CONCURRENT_ALERT_{messages_sent:03d}',
                        'description': 'Concurrent performance test alert',
                        'perf_test_timestamp': message_time,
                        'thread': 'quality_alerts'
                    }

                    producer.publish_data_quality_alert(alert_data)
                    messages_sent += 1
                    time.sleep(0.03)  # ~33 messages per second

            except Exception as e:
                thread_results['errors'] += 1
                print(f"Quality alert thread error: {e}")

            channel_performance['quality_alerts'] = {'sent': messages_sent, 'latencies': []}

        def publish_etf_updates(duration_seconds=2.0):
            """Publish ETF updates concurrently"""
            messages_sent = 0
            start_time = time.perf_counter()

            try:
                while (time.perf_counter() - start_time) < duration_seconds:
                    message_time = time.perf_counter()

                    etf_data = {
                        'symbol': f'CONCURRENT_ETF_{messages_sent:03d}',
                        'aum_millions': 1000.0 + messages_sent * 100,
                        'expense_ratio': 0.005 + (messages_sent * 0.0001),
                        'perf_test_timestamp': message_time,
                        'thread': 'etf_updates'
                    }

                    producer.publish_etf_data_update(etf_data['symbol'], etf_data)
                    messages_sent += 1
                    time.sleep(0.08)  # ~12 messages per second

            except Exception as e:
                thread_results['errors'] += 1
                print(f"ETF update thread error: {e}")

            channel_performance['etf_updates'] = {'sent': messages_sent, 'latencies': []}

        try:
            # Start concurrent publishing
            with integration_performance_monitor.measure_operation('concurrent_multi_channel_publishing'):
                threads = [
                    threading.Thread(target=publish_patterns, name='Patterns'),
                    threading.Thread(target=publish_quality_alerts, name='QualityAlerts'),
                    threading.Thread(target=publish_etf_updates, name='ETFUpdates')
                ]

                # Start all threads
                start_time = time.perf_counter()
                for thread in threads:
                    thread.start()

                # Wait for completion
                for thread in threads:
                    thread.join(timeout=5.0)

                execution_time = time.perf_counter() - start_time

            # Allow processing time
            time.sleep(2.0)

            # Collect and analyze results by channel
            for channel in test_channels:
                channel_messages = listener.get_messages(channel)

                # Calculate latencies for each channel
                for msg in channel_messages:
                    data = msg.get('parsed_data', {})
                    if 'perf_test_timestamp' in data and 'thread' in data:
                        received_time = time.perf_counter()
                        sent_time = data['perf_test_timestamp']
                        latency_ms = (received_time - sent_time) * 1000

                        thread_type = data['thread']
                        if thread_type in channel_performance:
                            channel_performance[thread_type]['latencies'].append(latency_ms)

            # Performance validation for concurrent channels
            overall_latencies = []

            for channel_type, perf_data in channel_performance.items():
                latencies = perf_data['latencies']
                sent_count = perf_data['sent']

                if latencies:
                    mean_latency = statistics.mean(latencies)
                    max_latency = max(latencies)
                    received_count = len(latencies)
                    retention_rate = received_count / sent_count if sent_count > 0 else 0

                    overall_latencies.extend(latencies)

                    # Channel-specific performance validation
                    assert mean_latency < PERFORMANCE_TARGETS['message_delivery_ms'] * 1.2, (
                        f"{channel_type}: Mean latency {mean_latency:.2f}ms too high in concurrent test"
                    )

                    assert retention_rate >= 0.8, (
                        f"{channel_type}: Retention rate {retention_rate:.1%} too low"
                    )

                    print(f"Concurrent Channel Performance - {channel_type}:")
                    print(f"  Messages sent: {sent_count}")
                    print(f"  Messages received: {received_count}")
                    print(f"  Retention rate: {retention_rate:.1%}")
                    print(f"  Mean latency: {mean_latency:.2f}ms")
                    print(f"  Max latency: {max_latency:.2f}ms")

            # Overall concurrent performance validation
            assert thread_results['errors'] == 0, f"Concurrent publishing had {thread_results['errors']} errors"
            assert execution_time < 3.0, f"Concurrent execution took {execution_time:.1f}s, expected <3s"

            if overall_latencies:
                overall_mean = statistics.mean(overall_latencies)
                overall_max = max(overall_latencies)

                assert overall_mean < PERFORMANCE_TARGETS['message_delivery_ms'] * 1.3, (
                    f"Overall concurrent mean latency {overall_mean:.2f}ms too high"
                )

                under_target_count = sum(1 for lat in overall_latencies if lat < PERFORMANCE_TARGETS['message_delivery_ms'])
                under_target_rate = under_target_count / len(overall_latencies)

                assert under_target_rate >= 0.7, (
                    f"Only {under_target_rate:.1%} of concurrent messages under target"
                )

                print("Overall Concurrent Results:")
                print(f"  Total latency measurements: {len(overall_latencies)}")
                print(f"  Overall mean latency: {overall_mean:.2f}ms")
                print(f"  Overall max latency: {overall_max:.2f}ms")
                print(f"  Under target rate: {under_target_rate:.1%}")
                print(f"  Execution time: {execution_time:.2f}s")

        finally:
            listener.stop_listening()


class TestDatabaseQueryPerformance:
    """Test <50ms database query performance requirements"""

    def test_database_integration_query_performance(
        self,
        db_connection,
        integration_performance_monitor
    ):
        """
        Test database query performance <50ms for integration scenarios.
        
        Validates database queries used in Sprint 14 integration
        meet performance targets.
        """
        # Test queries used in Sprint 14 integration scenarios
        test_queries = [
            {
                'name': 'symbol_lookup',
                'query': 'SELECT symbol, name, type FROM symbols WHERE symbol = :symbol',
                'params': {'symbol': 'AAPL'},
                'description': 'Basic symbol lookup for integration'
            },
            {
                'name': 'etf_data_query',
                'query': '''SELECT symbol, etf_type, aum_millions, expense_ratio, correlation_reference 
                           FROM symbols WHERE type = 'ETF' AND aum_millions > :min_aum LIMIT 10''',
                'params': {'min_aum': 1000.0},
                'description': 'ETF data queries for Phase 1 integration'
            },
            {
                'name': 'recent_symbols_query',
                'query': '''SELECT symbol, name, market_cap, sector 
                           FROM symbols WHERE listing_date >= :cutoff_date LIMIT 20''',
                'params': {'cutoff_date': '2024-01-01'},
                'description': 'Recent IPO queries for Phase 2 integration'
            },
            {
                'name': 'symbol_count_by_type',
                'query': 'SELECT type, COUNT(*) as count FROM symbols GROUP BY type',
                'params': {},
                'description': 'Universe management queries for Phase 3'
            },
            {
                'name': 'symbols_with_missing_data',
                'query': '''SELECT symbol FROM symbols s 
                           WHERE NOT EXISTS (
                               SELECT 1 FROM ohlcv_daily o 
                               WHERE o.symbol = s.symbol 
                               AND o.date >= :recent_date
                           ) LIMIT 50''',
                'params': {'recent_date': '2024-01-01'},
                'description': 'Data quality queries for monitoring'
            }
        ]

        query_performance_results = []

        try:
            for query_test in test_queries:
                query_latencies = []

                # Run each query multiple times for statistical analysis
                for iteration in range(10):
                    start_time = time.perf_counter()

                    with integration_performance_monitor.measure_operation(f"db_query_{query_test['name']}"):
                        result = db_connection.execute(
                            text(query_test['query']),
                            query_test['params']
                        )
                        rows = list(result)  # Fetch all results

                    end_time = time.perf_counter()
                    query_latency_ms = (end_time - start_time) * 1000
                    query_latencies.append(query_latency_ms)

                    time.sleep(0.01)  # Small delay between queries

                # Calculate query performance statistics
                if query_latencies:
                    perf_stats = {
                        'query_name': query_test['name'],
                        'description': query_test['description'],
                        'iterations': len(query_latencies),
                        'mean_ms': statistics.mean(query_latencies),
                        'median_ms': statistics.median(query_latencies),
                        'max_ms': max(query_latencies),
                        'min_ms': min(query_latencies),
                        'p95_ms': statistics.quantiles(query_latencies, n=20)[18] if len(query_latencies) >= 20 else max(query_latencies)
                    }

                    query_performance_results.append(perf_stats)

                    # Validate query performance against targets
                    assert perf_stats['mean_ms'] < PERFORMANCE_TARGETS['database_query_ms'], (
                        f"Query '{query_test['name']}': Mean latency {perf_stats['mean_ms']:.2f}ms "
                        f"exceeds {PERFORMANCE_TARGETS['database_query_ms']}ms target"
                    )

                    assert perf_stats['p95_ms'] < PERFORMANCE_TARGETS['database_query_ms'] * 2, (
                        f"Query '{query_test['name']}': P95 latency {perf_stats['p95_ms']:.2f}ms "
                        f"exceeds reasonable bounds"
                    )

                    # All iterations should be reasonably fast
                    slow_queries = sum(1 for lat in query_latencies if lat > PERFORMANCE_TARGETS['database_query_ms'])
                    slow_query_rate = slow_queries / len(query_latencies)

                    assert slow_query_rate <= 0.2, (
                        f"Query '{query_test['name']}': {slow_query_rate:.1%} of queries exceeded target"
                    )

                    print(f"Database Query Performance - {query_test['name']}:")
                    print(f"  Description: {query_test['description']}")
                    print(f"  Mean latency: {perf_stats['mean_ms']:.2f}ms")
                    print(f"  Median latency: {perf_stats['median_ms']:.2f}ms")
                    print(f"  P95 latency: {perf_stats['p95_ms']:.2f}ms")
                    print(f"  Max latency: {perf_stats['max_ms']:.2f}ms")
                    print(f"  Slow query rate: {slow_query_rate:.1%}")
                    print()

            # Overall database performance validation
            all_mean_latencies = [result['mean_ms'] for result in query_performance_results]
            overall_mean = statistics.mean(all_mean_latencies) if all_mean_latencies else 0

            assert overall_mean < PERFORMANCE_TARGETS['database_query_ms'], (
                f"Overall database mean latency {overall_mean:.2f}ms exceeds target"
            )

            print("Overall Database Performance:")
            print(f"  Queries tested: {len(query_performance_results)}")
            print(f"  Overall mean latency: {overall_mean:.2f}ms")
            print(f"  Target: <{PERFORMANCE_TARGETS['database_query_ms']}ms")

        finally:
            # Cleanup - no specific cleanup needed for read queries
            pass


class TestEndToEndWorkflowPerformance:
    """Test <500ms end-to-end workflow performance"""

    def test_complete_integration_workflow_performance(
        self,
        redis_client,
        db_connection,
        mock_tickstockapp_consumer,
        mock_tickstockpl_producer,
        redis_pubsub_listener,
        integration_performance_monitor
    ):
        """
        Test complete integration workflow performance <500ms.
        
        Measures end-to-end performance for typical Sprint 14
        integration scenarios across all phases.
        """
        listener = redis_pubsub_listener(redis_client)
        all_channels = list(SPRINT14_REDIS_CHANNELS['events'].values()) + [SPRINT14_REDIS_CHANNELS['jobs']['historical_load']]
        listener.subscribe(all_channels)
        listener.start_listening()

        consumer = mock_tickstockapp_consumer(redis_client)
        producer = mock_tickstockpl_producer(redis_client)

        workflow_scenarios = [
            {
                'name': 'etf_integration_workflow',
                'description': 'ETF integration: DB insert → Redis notify → UI update'
            },
            {
                'name': 'ipo_detection_workflow',
                'description': 'IPO detection: Scan → DB insert → Quality check → Universe assign'
            },
            {
                'name': 'data_quality_workflow',
                'description': 'Data quality: Alert → Assessment → Remediation → Resolution'
            },
            {
                'name': 'enterprise_job_workflow',
                'description': 'Enterprise job: Submit → Process → Progress → Complete'
            }
        ]

        try:
            workflow_performance_results = []

            for scenario in workflow_scenarios:
                scenario_latencies = []

                # Run workflow scenario multiple times
                for iteration in range(5):
                    workflow_start = time.perf_counter()

                    with integration_performance_monitor.measure_operation(f"e2e_workflow_{scenario['name']}"):

                        if scenario['name'] == 'etf_integration_workflow':
                            # ETF workflow: Database → Redis → Processing

                            # Step 1: Database insertion
                            etf_symbol = f'PERF_ETF_{iteration}'
                            db_connection.execute(text("""
                                INSERT INTO symbols (symbol, name, type, etf_type, aum_millions)
                                VALUES (:symbol, :name, 'ETF', 'equity', 5000.0)
                            """), {'symbol': etf_symbol, 'name': f'Performance Test ETF {iteration}'})
                            db_connection.commit()

                            # Step 2: Redis notification
                            etf_data = {
                                'symbol': etf_symbol,
                                'aum_millions': 5000.0,
                                'workflow_start_time': workflow_start
                            }
                            producer.publish_etf_data_update(etf_symbol, etf_data)

                        elif scenario['name'] == 'ipo_detection_workflow':
                            # IPO workflow: Detection → Database → Quality → Universe

                            ipo_symbol = f'PERF_IPO_{iteration}'

                            # Step 1: Database insertion
                            db_connection.execute(text("""
                                INSERT INTO symbols (symbol, name, type, market_cap, sector)
                                VALUES (:symbol, :name, 'CS', 8000.0, 'Technology')
                            """), {'symbol': ipo_symbol, 'name': f'Performance IPO {iteration}'})
                            db_connection.commit()

                            # Step 2: IPO detection notification
                            ipo_data = {
                                'symbol': ipo_symbol,
                                'market_cap': 8000.0,
                                'sector': 'Technology',
                                'workflow_start_time': workflow_start
                            }
                            producer.publish_ipo_detection(ipo_symbol, ipo_data)

                            # Step 3: Quality assessment
                            quality_data = {
                                'symbol': ipo_symbol,
                                'alert_type': 'new_symbol_assessment',
                                'severity': 'low',
                                'assessment_score': 0.9,
                                'workflow_start_time': workflow_start
                            }
                            producer.publish_data_quality_alert(quality_data)

                        elif scenario['name'] == 'data_quality_workflow':
                            # Data quality workflow: Alert → Assessment → Remediation

                            quality_symbol = f'PERF_QUAL_{iteration}'

                            # Step 1: Quality alert
                            alert_data = {
                                'symbol': quality_symbol,
                                'alert_type': 'data_quality_issue',
                                'severity': 'medium',
                                'description': 'Performance test quality alert',
                                'workflow_start_time': workflow_start
                            }
                            producer.publish_data_quality_alert(alert_data)

                            # Step 2: Assessment completion
                            assessment_data = {
                                'symbol': quality_symbol,
                                'alert_type': 'quality_assessment_complete',
                                'severity': 'low',
                                'resolution_time_ms': 150,
                                'workflow_start_time': workflow_start
                            }
                            producer.publish_data_quality_alert(assessment_data)

                        elif scenario['name'] == 'enterprise_job_workflow':
                            # Enterprise job workflow: Submit → Process → Complete

                            # Step 1: Job submission
                            job_data = {
                                'job_type': 'performance_test_job',
                                'job_id': f'perf_job_{iteration}',
                                'priority': 'high',
                                'workflow_start_time': workflow_start
                            }
                            consumer.submit_data_request(job_data)

                            # Step 2: Job processing progress
                            producer.publish_backtest_progress(f'perf_job_{iteration}', 0.5, 'processing')
                            producer.publish_backtest_progress(f'perf_job_{iteration}', 1.0, 'completed')

                    workflow_end = time.perf_counter()
                    workflow_latency_ms = (workflow_end - workflow_start) * 1000
                    scenario_latencies.append(workflow_latency_ms)

                    time.sleep(0.1)  # Brief pause between workflow runs

                # Calculate workflow performance statistics
                if scenario_latencies:
                    workflow_stats = {
                        'scenario': scenario['name'],
                        'description': scenario['description'],
                        'iterations': len(scenario_latencies),
                        'mean_ms': statistics.mean(scenario_latencies),
                        'median_ms': statistics.median(scenario_latencies),
                        'max_ms': max(scenario_latencies),
                        'min_ms': min(scenario_latencies)
                    }

                    workflow_performance_results.append(workflow_stats)

                    # Validate workflow performance
                    assert workflow_stats['mean_ms'] < PERFORMANCE_TARGETS['end_to_end_workflow_ms'], (
                        f"Workflow '{scenario['name']}': Mean latency {workflow_stats['mean_ms']:.2f}ms "
                        f"exceeds {PERFORMANCE_TARGETS['end_to_end_workflow_ms']}ms target"
                    )

                    assert workflow_stats['max_ms'] < PERFORMANCE_TARGETS['end_to_end_workflow_ms'] * 2, (
                        f"Workflow '{scenario['name']}': Max latency {workflow_stats['max_ms']:.2f}ms "
                        f"exceeds reasonable bounds"
                    )

                    print(f"E2E Workflow Performance - {scenario['name']}:")
                    print(f"  Description: {scenario['description']}")
                    print(f"  Mean latency: {workflow_stats['mean_ms']:.2f}ms")
                    print(f"  Median latency: {workflow_stats['median_ms']:.2f}ms")
                    print(f"  Max latency: {workflow_stats['max_ms']:.2f}ms")
                    print(f"  Min latency: {workflow_stats['min_ms']:.2f}ms")
                    print()

            # Allow processing time
            time.sleep(2.0)

            # Validate message delivery within workflows
            total_messages = 0
            for channel in all_channels:
                channel_messages = listener.get_messages(channel)
                total_messages += len(channel_messages)

            # Should have received substantial messages from workflow operations
            assert total_messages >= 15, f"Expected ≥15 workflow messages, got {total_messages}"

            # Overall workflow performance validation
            if workflow_performance_results:
                all_mean_latencies = [result['mean_ms'] for result in workflow_performance_results]
                overall_workflow_mean = statistics.mean(all_mean_latencies)

                assert overall_workflow_mean < PERFORMANCE_TARGETS['end_to_end_workflow_ms'], (
                    f"Overall workflow mean latency {overall_workflow_mean:.2f}ms exceeds target"
                )

                print("Overall E2E Workflow Performance:")
                print(f"  Workflows tested: {len(workflow_performance_results)}")
                print(f"  Overall mean latency: {overall_workflow_mean:.2f}ms")
                print(f"  Target: <{PERFORMANCE_TARGETS['end_to_end_workflow_ms']}ms")
                print(f"  Total messages processed: {total_messages}")

        finally:
            listener.stop_listening()


class TestSystemPerformanceUnderLoad:
    """Test system performance under various load conditions"""

    def test_performance_degradation_under_load(
        self,
        redis_client,
        mock_tickstockpl_producer,
        redis_pubsub_listener,
        integration_performance_monitor
    ):
        """
        Test performance degradation under increasing load.
        
        Validates that performance degrades gracefully and
        stays within acceptable bounds under load.
        """
        listener = redis_pubsub_listener(redis_client)
        listener.subscribe([SPRINT14_REDIS_CHANNELS['events']['patterns']])
        listener.start_listening()

        producer = mock_tickstockpl_producer(redis_client)

        # Load test scenarios with increasing intensity
        load_scenarios = [
            {'name': 'baseline', 'messages_per_second': 10, 'duration_seconds': 1},
            {'name': 'light_load', 'messages_per_second': 25, 'duration_seconds': 2},
            {'name': 'medium_load', 'messages_per_second': 50, 'duration_seconds': 2},
            {'name': 'heavy_load', 'messages_per_second': 100, 'duration_seconds': 2},
            {'name': 'stress_load', 'messages_per_second': 200, 'duration_seconds': 1}
        ]

        try:
            load_performance_results = {}

            for scenario in load_scenarios:
                scenario_latencies = []
                messages_sent = 0
                errors = 0

                print(f"Running {scenario['name']} scenario...")

                start_time = time.perf_counter()
                target_interval = 1.0 / scenario['messages_per_second']

                with integration_performance_monitor.measure_operation(f"load_test_{scenario['name']}"):

                    while (time.perf_counter() - start_time) < scenario['duration_seconds']:
                        message_timestamp = time.perf_counter()

                        try:
                            pattern_data = {
                                'symbol': f'LOAD_{scenario["name"].upper()}_{messages_sent:04d}',
                                'pattern': 'Load_Test_Pattern',
                                'confidence': 0.8,
                                'load_scenario': scenario['name'],
                                'perf_test_timestamp': message_timestamp,
                                'sequence_id': messages_sent
                            }

                            producer.publish_pattern_event(pattern_data)
                            messages_sent += 1

                        except Exception as e:
                            errors += 1
                            print(f"Error in {scenario['name']}: {e}")

                        # Maintain target rate
                        next_send_time = start_time + (messages_sent * target_interval)
                        sleep_time = next_send_time - time.perf_counter()
                        if sleep_time > 0:
                            time.sleep(sleep_time)

                actual_duration = time.perf_counter() - start_time
                actual_rate = messages_sent / actual_duration

                load_performance_results[scenario['name']] = {
                    'messages_sent': messages_sent,
                    'target_rate': scenario['messages_per_second'],
                    'actual_rate': actual_rate,
                    'duration_seconds': actual_duration,
                    'errors': errors,
                    'latencies': []
                }

                # Brief pause between scenarios
                time.sleep(0.5)

            # Allow processing time
            time.sleep(3.0)

            # Calculate latencies for each scenario
            pattern_messages = listener.get_messages(SPRINT14_REDIS_CHANNELS['events']['patterns'])

            for msg in pattern_messages:
                data = msg.get('parsed_data', {})
                if 'perf_test_timestamp' in data and 'load_scenario' in data:
                    received_time = time.perf_counter()
                    sent_time = data['perf_test_timestamp']
                    latency_ms = (received_time - sent_time) * 1000

                    scenario_name = data['load_scenario']
                    if scenario_name in load_performance_results:
                        load_performance_results[scenario_name]['latencies'].append(latency_ms)

            # Analyze performance degradation
            baseline_performance = None

            for scenario_name, results in load_performance_results.items():
                latencies = results['latencies']

                if latencies:
                    mean_latency = statistics.mean(latencies)
                    p95_latency = statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies)
                    retention_rate = len(latencies) / results['messages_sent'] if results['messages_sent'] > 0 else 0

                    results.update({
                        'mean_latency_ms': mean_latency,
                        'p95_latency_ms': p95_latency,
                        'retention_rate': retention_rate
                    })

                    if scenario_name == 'baseline':
                        baseline_performance = mean_latency

                    # Performance validation under load
                    if scenario_name in ['baseline', 'light_load']:
                        # Should meet normal targets under light load
                        assert mean_latency < PERFORMANCE_TARGETS['message_delivery_ms'], (
                            f"{scenario_name}: Mean latency {mean_latency:.2f}ms exceeds normal target"
                        )
                    else:
                        # Under heavy load, allow some degradation but within bounds
                        max_acceptable = PERFORMANCE_TARGETS['message_delivery_ms'] * (2.0 if scenario_name == 'medium_load' else 3.0)
                        assert mean_latency < max_acceptable, (
                            f"{scenario_name}: Mean latency {mean_latency:.2f}ms exceeds acceptable degradation"
                        )

                    # Retention should be reasonable even under load
                    min_retention = 0.9 if scenario_name in ['baseline', 'light_load'] else 0.6
                    assert retention_rate >= min_retention, (
                        f"{scenario_name}: Retention rate {retention_rate:.1%} too low"
                    )

                    print(f"Load Performance - {scenario_name}:")
                    print(f"  Target rate: {results['target_rate']} msg/s")
                    print(f"  Actual rate: {results['actual_rate']:.1f} msg/s")
                    print(f"  Messages sent: {results['messages_sent']}")
                    print(f"  Messages received: {len(latencies)}")
                    print(f"  Retention rate: {retention_rate:.1%}")
                    print(f"  Mean latency: {mean_latency:.2f}ms")
                    print(f"  P95 latency: {p95_latency:.2f}ms")
                    print(f"  Errors: {results['errors']}")
                    print()

            # Analyze overall performance degradation
            if baseline_performance:
                print("Performance Degradation Analysis:")
                for scenario_name, results in load_performance_results.items():
                    if 'mean_latency_ms' in results and scenario_name != 'baseline':
                        degradation_factor = results['mean_latency_ms'] / baseline_performance
                        print(f"  {scenario_name}: {degradation_factor:.1f}x baseline latency")

                        # Validate reasonable degradation bounds
                        max_degradation = {'light_load': 1.5, 'medium_load': 2.5, 'heavy_load': 4.0, 'stress_load': 6.0}
                        if scenario_name in max_degradation:
                            assert degradation_factor <= max_degradation[scenario_name], (
                                f"{scenario_name}: Performance degraded {degradation_factor:.1f}x, "
                                f"exceeds {max_degradation[scenario_name]}x limit"
                            )

        finally:
            listener.stop_listening()
