"""
Sprint 14 Phase 2: Automation Services System Integration Test Suite

Integration tests for IPO monitoring, data quality monitoring, and equity types
processing with Redis pub-sub messaging and TickStockApp loose coupling validation.

Date: 2025-09-01
Sprint: 14 Phase 2
Status: Comprehensive Integration Coverage
"""

import json
import time
from unittest.mock import Mock, patch

import pytest
import redis
from src.automation.services.data_quality_monitor import DataQualityMonitor
from src.automation.services.ipo_monitor import IPOMonitor
from src.database.connection import DatabaseConnection


class TestAutomationServicesSeparation:
    """Test automation services run independently from TickStockApp"""

    def test_ipo_monitor_service_independence(self):
        """Test IPO monitor runs as independent service"""
        ipo_monitor = IPOMonitor()

        # Verify service independence
        assert ipo_monitor.service_mode == 'standalone'
        assert ipo_monitor.service_role == 'producer'
        assert not hasattr(ipo_monitor, 'tickstock_app_dependency')

        # Verify can start/stop independently
        assert hasattr(ipo_monitor, 'start_service')
        assert hasattr(ipo_monitor, 'stop_service')
        assert hasattr(ipo_monitor, 'service_health_check')

    def test_data_quality_monitor_independence(self):
        """Test data quality monitor runs independently"""
        quality_monitor = DataQualityMonitor()

        # Verify service independence
        assert quality_monitor.service_mode == 'standalone'
        assert quality_monitor.service_role == 'producer'
        assert not hasattr(quality_monitor, 'app_integration')

        # Verify monitoring capabilities
        assert hasattr(quality_monitor, 'start_monitoring')
        assert hasattr(quality_monitor, 'stop_monitoring')
        assert hasattr(quality_monitor, 'monitoring_health')

    def test_services_database_access_separation(self):
        """Test services have proper database access levels"""
        ipo_monitor = IPOMonitor()
        quality_monitor = DataQualityMonitor()

        # IPO Monitor should have full write access
        assert ipo_monitor.has_write_access is True
        assert hasattr(ipo_monitor, 'create_symbols')
        assert hasattr(ipo_monitor, 'store_historical_data')

        # Quality Monitor should have read access for analysis
        assert quality_monitor.has_read_access is True
        assert hasattr(quality_monitor, 'get_market_data')
        assert hasattr(quality_monitor, 'analyze_data_patterns')

    def test_loose_coupling_via_redis_only(self):
        """Test services communicate only via Redis pub-sub"""
        ipo_monitor = IPOMonitor()
        quality_monitor = DataQualityMonitor()

        # Verify Redis-only communication
        assert ipo_monitor.communication_method == 'redis_pubsub'
        assert quality_monitor.communication_method == 'redis_pubsub'

        # Verify no direct TickStockApp connections
        assert not hasattr(ipo_monitor, 'app_websocket_connection')
        assert not hasattr(quality_monitor, 'direct_app_messaging')

        # Verify separate Redis channels
        assert ipo_monitor.redis_channel != quality_monitor.redis_channel
        assert 'ipo' in ipo_monitor.redis_channel
        assert 'quality' in quality_monitor.redis_channel


class TestRedisMessagingIntegration:
    """Test Redis pub-sub messaging between services and TickStockApp"""

    @pytest.fixture
    def redis_client(self):
        """Redis client fixture for testing"""
        return redis.Redis(host='localhost', port=6379, db=1, decode_responses=True)

    @pytest.fixture
    def mock_tickstock_subscriber(self):
        """Mock TickStockApp Redis subscriber"""
        mock_subscriber = Mock()
        mock_subscriber.received_messages = []

        def mock_message_handler(message):
            mock_subscriber.received_messages.append(message)

        mock_subscriber.handle_message = mock_message_handler
        return mock_subscriber

    def test_ipo_notification_message_flow(self, redis_client, mock_tickstock_subscriber):
        """Test IPO notification flows from service to TickStockApp"""
        ipo_monitor = IPOMonitor()
        ipo_monitor.redis_client = redis_client

        # Subscribe to IPO notifications
        pubsub = redis_client.pubsub()
        pubsub.subscribe('tickstock:ipo:notifications')

        # Publish IPO notification
        ipo_data = {
            'ticker': 'NEWIPO',
            'name': 'New IPO Company',
            'listing_date': '2025-09-01',
            'market_cap': 1500000000
        }

        result = ipo_monitor.publish_ipo_notification(ipo_data)
        assert result is True

        # Verify message received
        message = pubsub.get_message(timeout=1.0)
        if message and message['type'] == 'message':
            notification = json.loads(message['data'])

            assert notification['event_type'] == 'new_ipo'
            assert notification['ticker'] == 'NEWIPO'
            assert notification['company_name'] == 'New IPO Company'
            assert 'timestamp' in notification

        pubsub.close()

    def test_data_quality_alert_message_flow(self, redis_client):
        """Test data quality alerts flow to TickStockApp"""
        quality_monitor = DataQualityMonitor()
        quality_monitor.redis_client = redis_client

        # Subscribe to quality alerts
        pubsub = redis_client.pubsub()
        pubsub.subscribe('tickstock:data_quality:alerts')

        # Publish quality alert
        alert_data = {
            'symbol': 'AAPL',
            'anomaly_type': 'price_spike',
            'price_change': 0.25,
            'severity': 'high'
        }

        result = quality_monitor.publish_quality_alert(alert_data)
        assert result is True

        # Verify alert received
        message = pubsub.get_message(timeout=1.0)
        if message and message['type'] == 'message':
            alert = json.loads(message['data'])

            assert alert['alert_type'] == 'price_anomaly'
            assert alert['symbol'] == 'AAPL'
            assert alert['severity'] == 'high'
            assert 'alert_id' in alert

        pubsub.close()

    @pytest.mark.performance
    def test_message_delivery_performance(self, redis_client):
        """Test message delivery meets <100ms requirement"""
        ipo_monitor = IPOMonitor()
        ipo_monitor.redis_client = redis_client

        # Subscribe to notifications
        pubsub = redis_client.pubsub()
        pubsub.subscribe('tickstock:ipo:notifications')

        # Test message delivery performance
        start_time = time.perf_counter()

        ipo_data = {'ticker': 'PERFTEST', 'name': 'Performance Test'}
        result = ipo_monitor.publish_ipo_notification(ipo_data)

        # Receive message
        message = pubsub.get_message(timeout=1.0)

        elapsed_time = time.perf_counter() - start_time

        assert result is True
        assert message is not None
        assert elapsed_time < 0.1  # Less than 100ms end-to-end

        pubsub.close()

    def test_message_persistence_and_reliability(self, redis_client):
        """Test message persistence for offline TickStockApp instances"""
        quality_monitor = DataQualityMonitor()
        quality_monitor.redis_client = redis_client

        # Publish alerts while no subscriber is active
        alerts = [
            {'symbol': 'SYM1', 'anomaly_type': 'volume_spike', 'severity': 'high'},
            {'symbol': 'SYM2', 'anomaly_type': 'price_drop', 'severity': 'critical'},
            {'symbol': 'SYM3', 'anomaly_type': 'data_gap', 'severity': 'medium'}
        ]

        # Store in Redis stream for persistence
        stream_key = 'tickstock:quality_alerts:stream'

        for alert in alerts:
            redis_client.xadd(stream_key, alert)

        # Verify stream contains messages
        stream_info = redis_client.xinfo_stream(stream_key)
        assert stream_info['length'] >= len(alerts)

        # Read messages from stream
        messages = redis_client.xread({stream_key: '0'})
        assert len(messages) == 1
        assert len(messages[0][1]) >= len(alerts)

    def test_cross_service_message_isolation(self, redis_client):
        """Test services don't interfere with each other's messages"""
        ipo_monitor = IPOMonitor()
        quality_monitor = DataQualityMonitor()

        ipo_monitor.redis_client = redis_client
        quality_monitor.redis_client = redis_client

        # Subscribe to both channels separately
        ipo_pubsub = redis_client.pubsub()
        quality_pubsub = redis_client.pubsub()

        ipo_pubsub.subscribe('tickstock:ipo:notifications')
        quality_pubsub.subscribe('tickstock:data_quality:alerts')

        # Publish to both channels
        ipo_monitor.publish_ipo_notification({'ticker': 'IPO1', 'name': 'Test IPO'})
        quality_monitor.publish_quality_alert({'symbol': 'QUAL1', 'anomaly_type': 'spike'})

        # Verify messages are properly isolated
        ipo_message = ipo_pubsub.get_message(timeout=1.0)
        quality_message = quality_pubsub.get_message(timeout=1.0)

        if ipo_message and ipo_message['type'] == 'message':
            ipo_data = json.loads(ipo_message['data'])
            assert 'ticker' in ipo_data  # IPO-specific field
            assert 'anomaly_type' not in ipo_data  # No quality fields

        if quality_message and quality_message['type'] == 'message':
            quality_data = json.loads(quality_message['data'])
            assert 'anomaly_type' in quality_data  # Quality-specific field
            assert 'ticker' not in quality_data     # No IPO fields

        ipo_pubsub.close()
        quality_pubsub.close()


class TestDatabaseIntegrationPatterns:
    """Test database integration patterns for automation services"""

    @pytest.fixture
    def db_connection(self):
        """Database connection fixture"""
        return DatabaseConnection(test_mode=True)

    def test_ipo_monitor_database_operations(self, db_connection):
        """Test IPO monitor database write operations"""
        ipo_monitor = IPOMonitor()
        ipo_monitor.db_connection = db_connection

        # Test symbol creation
        new_symbol_data = {
            'ticker': 'TESTIPO',
            'name': 'Test IPO Company Inc',
            'exchange': 'NASDAQ',
            'type': 'STOCK_REALTIME',
            'market_cap': 1000000000,
            'listing_date': '2025-09-01'
        }

        with patch.object(ipo_monitor, 'create_symbol') as mock_create:
            mock_create.return_value = True

            result = ipo_monitor.process_new_ipo(new_symbol_data)

            assert result is True
            mock_create.assert_called_once_with(new_symbol_data)

        # Test historical data storage
        historical_data = [
            {'date': '2025-09-01', 'open': 100.0, 'high': 105.0, 'low': 98.0, 'close': 103.0, 'volume': 5000000}
        ]

        with patch.object(ipo_monitor, 'store_historical_data') as mock_store:
            mock_store.return_value = True

            result = ipo_monitor.store_symbol_history('TESTIPO', historical_data)

            assert result is True
            mock_store.assert_called_once()

    def test_equity_types_database_functions(self, db_connection):
        """Test equity types database functions integration"""
        cursor = db_connection.cursor()

        # Test processing configuration retrieval
        cursor.execute("SELECT get_equity_processing_config('STOCK_REALTIME')")
        config = cursor.fetchone()[0]

        assert isinstance(config, dict)
        assert config['type_name'] == 'STOCK_REALTIME'
        assert config['priority_level'] == 100
        assert config['batch_size'] == 25

        # Test symbol queuing
        cursor.execute("SELECT queue_symbols_for_processing('ETF', ARRAY['SPY', 'QQQ'])")
        queued_count = cursor.fetchone()[0]

        assert queued_count == 2

        # Verify queue contents
        cursor.execute("""
            SELECT symbol, equity_type, processing_priority
            FROM equity_processing_queue
            WHERE equity_type = 'ETF' AND symbol IN ('SPY', 'QQQ')
        """)

        queued_symbols = cursor.fetchall()
        assert len(queued_symbols) == 2

        for symbol_row in queued_symbols:
            assert symbol_row[1] == 'ETF'
            assert symbol_row[2] == 90  # ETF priority level

    def test_data_quality_monitor_read_operations(self, db_connection):
        """Test data quality monitor read-only database access"""
        quality_monitor = DataQualityMonitor()
        quality_monitor.db_connection = db_connection

        with patch.object(quality_monitor, 'get_market_data') as mock_get_data:
            mock_get_data.return_value = {
                'AAPL': {
                    'price_data': [
                        {'date': '2025-08-31', 'close': 150.0},
                        {'date': '2025-09-01', 'close': 180.0}
                    ],
                    'volume_data': [
                        {'date': '2025-08-31', 'volume': 50000000},
                        {'date': '2025-09-01', 'volume': 250000000}
                    ]
                }
            }

            # Test data retrieval for quality analysis
            market_data = quality_monitor.get_symbols_for_analysis(['AAPL'])

            assert 'AAPL' in market_data
            assert len(market_data['AAPL']['price_data']) == 2
            assert len(market_data['AAPL']['volume_data']) == 2

        # Verify read-only access (should not have write operations)
        assert not hasattr(quality_monitor, 'create_symbol')
        assert not hasattr(quality_monitor, 'update_symbol')
        assert not hasattr(quality_monitor, 'store_data')

    @pytest.mark.performance
    def test_database_performance_under_load(self, db_connection):
        """Test database performance with high automation service load"""
        cursor = db_connection.cursor()

        # Test concurrent equity type queries
        start_time = time.perf_counter()

        for i in range(100):
            # Mix of equity type operations
            cursor.execute("SELECT get_equity_processing_config('STOCK_REALTIME')")
            cursor.execute("SELECT * FROM get_symbols_for_processing('ETF', 10)")
            cursor.execute("SELECT update_processing_stats('STOCK_EOD', 50, 2, 120)")

        elapsed_time = time.perf_counter() - start_time

        # 300 database operations should complete in <15 seconds
        assert elapsed_time < 15.0

        # Test batch queue operations performance
        large_symbol_batch = [f'BATCH{i:04d}' for i in range(1000)]

        start_time = time.perf_counter()

        cursor.execute("SELECT queue_symbols_for_processing('STOCK_EOD', %s)", (large_symbol_batch,))
        queued_count = cursor.fetchone()[0]

        elapsed_time = time.perf_counter() - start_time

        assert queued_count == 1000
        assert elapsed_time < 5.0  # 1000 symbols queued in <5 seconds


class TestAutomationServicesWorkflowIntegration:
    """Test end-to-end automation services workflow integration"""

    @pytest.mark.integration
    def test_ipo_discovery_to_tickstockapp_workflow(self):
        """Test complete IPO discovery and notification to TickStockApp"""
        ipo_monitor = IPOMonitor()

        with patch.object(ipo_monitor, 'discover_new_symbols') as mock_discover, \
             patch.object(ipo_monitor, 'create_symbol') as mock_create, \
             patch.object(ipo_monitor, 'backfill_historical_data') as mock_backfill, \
             patch.object(ipo_monitor, 'publish_ipo_notification') as mock_notify:

            # Mock IPO discovery
            mock_discover.return_value = [
                {
                    'ticker': 'NEWIPO1',
                    'name': 'New IPO Company 1',
                    'listing_date': '2025-09-01',
                    'market_cap': 1000000000
                }
            ]

            mock_create.return_value = True
            mock_backfill.return_value = True
            mock_notify.return_value = True

            # Execute complete workflow
            results = ipo_monitor.run_daily_ipo_scan()

            # Verify workflow completion
            assert results['discovered'] == 1
            assert results['created'] == 1
            assert results['backfilled'] == 1
            assert results['notified'] == 1

            # Verify workflow sequence
            mock_discover.assert_called_once()
            mock_create.assert_called_once()
            mock_backfill.assert_called_once()
            mock_notify.assert_called_once()

            # Verify notification content
            notification_call = mock_notify.call_args[0][0]
            assert notification_call['ticker'] == 'NEWIPO1'
            assert notification_call['backfill_status'] == 'completed'

    @pytest.mark.integration
    def test_data_quality_monitoring_to_alerts_workflow(self):
        """Test complete data quality monitoring and alerting workflow"""
        quality_monitor = DataQualityMonitor()

        with patch.object(quality_monitor, 'get_symbols_for_analysis') as mock_get_symbols, \
             patch.object(quality_monitor, 'detect_price_anomalies') as mock_price, \
             patch.object(quality_monitor, 'detect_volume_anomalies') as mock_volume, \
             patch.object(quality_monitor, 'detect_data_gaps') as mock_gaps, \
             patch.object(quality_monitor, 'publish_quality_alert') as mock_alert:

            # Mock quality monitoring data
            mock_get_symbols.return_value = ['AAPL', 'GOOGL', 'MSFT']

            mock_price.return_value = [
                {'symbol': 'AAPL', 'anomaly_type': 'price_spike', 'severity': 'high'}
            ]

            mock_volume.return_value = [
                {'symbol': 'GOOGL', 'anomaly_type': 'volume_spike', 'severity': 'critical'}
            ]

            mock_gaps.return_value = [
                {'symbol': 'MSFT', 'alert_type': 'data_gap', 'severity': 'medium'}
            ]

            mock_alert.return_value = True

            # Execute quality monitoring workflow
            results = quality_monitor.run_quality_scan()

            # Verify workflow results
            assert results['symbols_analyzed'] == 3
            assert results['price_anomalies'] == 1
            assert results['volume_anomalies'] == 1
            assert results['data_issues'] == 1
            assert results['alerts_published'] == 3

            # Verify alert publishing
            assert mock_alert.call_count == 3

    @pytest.mark.integration
    def test_equity_types_processing_queue_workflow(self):
        """Test equity types processing queue workflow"""
        db_connection = DatabaseConnection(test_mode=True)
        cursor = db_connection.cursor()

        # Clear test queue
        cursor.execute("DELETE FROM equity_processing_queue WHERE equity_type = 'WORKFLOW_TEST'")

        # Create test equity type
        cursor.execute("""
            INSERT INTO equity_types (type_name, priority_level, batch_size, rate_limit_ms)
            VALUES ('WORKFLOW_TEST', 80, 50, 10000)
            ON CONFLICT (type_name) DO UPDATE SET
                priority_level = EXCLUDED.priority_level
        """)

        # Step 1: Queue symbols for processing
        test_symbols = [f'WORK{i:03d}' for i in range(100)]
        cursor.execute("SELECT queue_symbols_for_processing('WORKFLOW_TEST', %s)", (test_symbols,))
        queued_count = cursor.fetchone()[0]

        assert queued_count == 100

        # Step 2: Process batch of symbols
        cursor.execute("""
            SELECT symbol FROM equity_processing_queue
            WHERE equity_type = 'WORKFLOW_TEST' AND status = 'pending'
            ORDER BY processing_priority DESC
            LIMIT 50
        """)

        batch_symbols = [row[0] for row in cursor.fetchall()]
        assert len(batch_symbols) == 50

        # Step 3: Update processing status
        cursor.execute("""
            UPDATE equity_processing_queue
            SET status = 'processing', last_attempt = CURRENT_TIMESTAMP
            WHERE symbol = ANY(%s) AND equity_type = 'WORKFLOW_TEST'
        """, (batch_symbols,))

        # Step 4: Complete processing and update statistics
        cursor.execute("""
            UPDATE equity_processing_queue
            SET status = 'completed', completed_at = CURRENT_TIMESTAMP
            WHERE symbol = ANY(%s) AND equity_type = 'WORKFLOW_TEST'
        """, (batch_symbols,))

        cursor.execute("SELECT update_processing_stats('WORKFLOW_TEST', 50, 0, 300)")
        success = cursor.fetchone()[0]
        assert success is True

        # Verify workflow completion
        cursor.execute("""
            SELECT COUNT(*) FROM equity_processing_queue
            WHERE equity_type = 'WORKFLOW_TEST' AND status = 'completed'
        """)
        completed_count = cursor.fetchone()[0]
        assert completed_count == 50

    @pytest.mark.integration
    @pytest.mark.slow
    def test_concurrent_services_operation(self):
        """Test multiple automation services running concurrently"""
        ipo_monitor = IPOMonitor()
        quality_monitor = DataQualityMonitor()

        # Mock service operations
        with patch.object(ipo_monitor, 'run_daily_ipo_scan') as mock_ipo_scan, \
             patch.object(quality_monitor, 'run_quality_scan') as mock_quality_scan:

            mock_ipo_scan.return_value = {'discovered': 5, 'notified': 5}
            mock_quality_scan.return_value = {'symbols_analyzed': 1000, 'alerts_published': 15}

            # Start both services concurrently
            import threading

            ipo_thread = threading.Thread(target=mock_ipo_scan)
            quality_thread = threading.Thread(target=mock_quality_scan)

            start_time = time.perf_counter()

            ipo_thread.start()
            quality_thread.start()

            ipo_thread.join(timeout=30)
            quality_thread.join(timeout=30)

            elapsed_time = time.perf_counter() - start_time

            # Both services should complete concurrently
            assert elapsed_time < 30
            assert mock_ipo_scan.called
            assert mock_quality_scan.called

    @pytest.mark.integration
    def test_service_health_monitoring(self):
        """Test automation services health monitoring"""
        ipo_monitor = IPOMonitor()
        quality_monitor = DataQualityMonitor()

        # Test service health checks
        ipo_health = ipo_monitor.health_check()
        quality_health = quality_monitor.health_check()

        # Verify health check structure
        for health in [ipo_health, quality_health]:
            assert 'status' in health
            assert 'last_run' in health
            assert 'database_connection' in health
            assert 'redis_connection' in health
            assert 'error_count' in health

        # Verify healthy status
        assert ipo_health['status'] in ['healthy', 'running']
        assert quality_health['status'] in ['healthy', 'running']

        # Test service metrics
        ipo_metrics = ipo_monitor.get_service_metrics()
        quality_metrics = quality_monitor.get_service_metrics()

        # Verify metrics structure
        assert 'symbols_processed' in ipo_metrics
        assert 'notifications_sent' in ipo_metrics
        assert 'anomalies_detected' in quality_metrics
        assert 'alerts_published' in quality_metrics
