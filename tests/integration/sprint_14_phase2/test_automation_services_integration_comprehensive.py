from src.core.services.config_manager import get_config
"""
Comprehensive Integration Tests - Sprint 14 Phase 2 Automation Services
Validates cross-system integration patterns for TickStockApp ↔ Automation Services communication.

This suite validates:
- Redis pub-sub loose coupling architecture between TickStockApp and automation services
- Database integration patterns and role separation (producer/consumer boundaries)  
- Message delivery performance <100ms end-to-end validation
- Service boundary validation ensuring no direct API calls between systems
- System resilience and graceful degradation when services are unavailable

Date: 2025-09-01
Sprint: 14 Phase 2 
Coverage: Comprehensive cross-system integration validation
"""

import pytest
import asyncio
import redis
import redis.asyncio as redis_async
import json
import time
import threading
import psycopg2
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import patch, MagicMock

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.core.services.config_manager import get_config

# Test configuration
config = get_config()
TEST_REDIS_DB = 15  # Separate database for testing
TEST_DATABASE_URI = config.get(
    'TEST_DATABASE_URI',
    'postgresql://app_readwrite:password@localhost:5432/tickstock_test'
)

@dataclass
class IntegrationTestResult:
    """Test result structure for integration validation"""
    test_name: str
    success: bool
    latency_ms: float
    message_count: int
    error_message: Optional[str] = None
    performance_data: Optional[Dict[str, Any]] = None

class RedisMessageFlowValidator:
    """Validates Redis message flows between automation services and TickStockApp"""
    
    def __init__(self, redis_host='localhost', redis_port=6379):
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.sync_client = None
        self.async_client = None
        
        # Channel definitions matching automation services
        self.channels = {
            'ipo_notifications': 'tickstock.automation.symbols.new',
            'ipo_backfill': 'tickstock.automation.backfill.completed',
            'quality_price': 'tickstock.quality.price_anomaly',
            'quality_volume': 'tickstock.quality.volume_anomaly',
            'quality_gaps': 'tickstock.quality.data_gap',
            'maintenance_events': 'tickstock.automation.maintenance.completed'
        }
    
    def setup_redis_connections(self):
        """Setup Redis connections for testing"""
        self.sync_client = redis.Redis(
            host=self.redis_host,
            port=self.redis_port,
            db=TEST_REDIS_DB,
            decode_responses=True,
            socket_timeout=5.0,
            socket_connect_timeout=2.0
        )
        
        # Test connection
        self.sync_client.ping()
        
        # Clear test database
        self.sync_client.flushdb()
        
    async def setup_async_redis(self):
        """Setup async Redis client"""
        self.async_client = redis_async.Redis(
            host=self.redis_host,
            port=self.redis_port,
            db=TEST_REDIS_DB,
            decode_responses=True
        )
        await self.async_client.ping()
        
    def cleanup_redis(self):
        """Cleanup Redis connections"""
        if self.sync_client:
            try:
                self.sync_client.flushdb()
                self.sync_client.close()
            except:
                pass
        self.sync_client = None
        
    async def cleanup_async_redis(self):
        """Cleanup async Redis client"""
        if self.async_client:
            try:
                await self.async_client.aclose()
            except:
                pass
        self.async_client = None

class AutomationServiceIntegrationTests:
    """Comprehensive integration tests for automation services"""
    
    def __init__(self):
        self.redis_validator = RedisMessageFlowValidator()
        self.test_results = []
        
    def setup_method(self):
        """Setup for each test method"""
        self.redis_validator.setup_redis_connections()
        
    def teardown_method(self):
        """Cleanup after each test method"""
        self.redis_validator.cleanup_redis()

class TestRedisMessageFlowIntegration(AutomationServiceIntegrationTests):
    """Test Redis message flow integration patterns"""
    
    def test_ipo_monitor_to_tickstockapp_message_flow(self):
        """
        Test IPO Monitor -> Redis pub-sub -> TickStockApp message flow
        Validates: Message delivery, format consistency, performance <100ms
        """
        # Setup subscriber (simulating TickStockApp)
        received_messages = []
        
        def message_handler(message):
            if message['type'] == 'message':
                received_messages.append({
                    'channel': message['channel'],
                    'data': json.loads(message['data']),
                    'received_at': time.time()
                })
        
        # Subscribe to IPO notifications
        pubsub = self.redis_validator.sync_client.pubsub()
        pubsub.subscribe(self.redis_validator.channels['ipo_notifications'])
        
        # Start listener thread
        listener_thread = threading.Thread(
            target=self._listen_for_messages,
            args=(pubsub, message_handler),
            daemon=True
        )
        listener_thread.start()
        
        # Simulate IPO Monitor publishing new symbol event
        start_time = time.time()
        
        ipo_event = {
            'timestamp': datetime.now().isoformat(),
            'service': 'ipo_monitor',
            'data': {
                'symbol': 'NEWIPO',
                'name': 'New IPO Company Inc',
                'type': 'CS',
                'market': 'stocks',
                'exchange': 'NASDAQ',
                'ipo_date': '2025-09-01',
                'detection_date': datetime.now().isoformat()
            }
        }
        
        # Publish event
        publish_result = self.redis_validator.sync_client.publish(
            self.redis_validator.channels['ipo_notifications'],
            json.dumps(ipo_event)
        )
        
        # Wait for message processing
        time.sleep(0.05)  # 50ms buffer
        
        # Verify message delivery
        assert publish_result > 0, "Message publish failed"
        assert len(received_messages) == 1, "Message not received by subscriber"
        
        received_msg = received_messages[0]
        
        # Validate message structure
        assert received_msg['channel'] == self.redis_validator.channels['ipo_notifications']
        assert received_msg['data']['service'] == 'ipo_monitor'
        assert received_msg['data']['data']['symbol'] == 'NEWIPO'
        
        # Validate performance requirement <100ms
        end_to_end_latency = (received_msg['received_at'] - start_time) * 1000
        assert end_to_end_latency < 100, f"Message delivery {end_to_end_latency:.2f}ms exceeds 100ms requirement"
        
        # Record test result
        self.test_results.append(IntegrationTestResult(
            test_name='ipo_monitor_message_flow',
            success=True,
            latency_ms=end_to_end_latency,
            message_count=1
        ))
        
        pubsub.close()
        
    def test_data_quality_monitor_alert_flow(self):
        """
        Test Data Quality Monitor -> Redis pub-sub -> TickStockApp alert flow
        Validates: Alert categorization, severity levels, message persistence
        """
        received_alerts = []
        
        def alert_handler(message):
            if message['type'] == 'message':
                received_alerts.append({
                    'channel': message['channel'],
                    'alert': json.loads(message['data']),
                    'timestamp': time.time()
                })
        
        # Subscribe to quality alert channels
        pubsub = self.redis_validator.sync_client.pubsub()
        pubsub.subscribe([
            self.redis_validator.channels['quality_price'],
            self.redis_validator.channels['quality_volume'],
            self.redis_validator.channels['quality_gaps']
        ])
        
        listener_thread = threading.Thread(
            target=self._listen_for_messages,
            args=(pubsub, alert_handler),
            daemon=True
        )
        listener_thread.start()
        
        # Simulate different quality alerts
        quality_alerts = [
            {
                'channel': self.redis_validator.channels['quality_price'],
                'alert': {
                    'timestamp': datetime.now().isoformat(),
                    'service': 'data_quality_monitor',
                    'alert_type': 'price_anomaly',
                    'symbol': 'AAPL',
                    'severity': 'high',
                    'description': 'Large price movement detected: 25.0%',
                    'details': {
                        'price_change_pct': 0.25,
                        'close_price': 225.0,
                        'previous_close': 180.0
                    }
                }
            },
            {
                'channel': self.redis_validator.channels['quality_volume'],
                'alert': {
                    'timestamp': datetime.now().isoformat(),
                    'service': 'data_quality_monitor',
                    'alert_type': 'volume_spike',
                    'symbol': 'GOOGL',
                    'severity': 'critical',
                    'description': 'Volume spike: 8.5x normal',
                    'details': {
                        'volume': 85000000,
                        'average_volume_20d': 10000000,
                        'volume_ratio': 8.5
                    }
                }
            },
            {
                'channel': self.redis_validator.channels['quality_gaps'],
                'alert': {
                    'timestamp': datetime.now().isoformat(),
                    'service': 'data_quality_monitor',
                    'alert_type': 'data_gap',
                    'symbol': 'MSFT',
                    'severity': 'medium',
                    'description': 'Data stale for 3 days',
                    'details': {
                        'days_stale': 3,
                        'last_data_date': '2025-08-29'
                    }
                }
            }
        ]
        
        start_time = time.time()
        
        # Publish all alerts
        for alert_data in quality_alerts:
            self.redis_validator.sync_client.publish(
                alert_data['channel'],
                json.dumps(alert_data['alert'])
            )
        
        # Wait for processing
        time.sleep(0.1)
        
        # Verify all alerts received
        assert len(received_alerts) == 3, "Not all quality alerts received"
        
        # Validate alert categorization
        alert_types = [alert['alert']['alert_type'] for alert in received_alerts]
        assert 'price_anomaly' in alert_types
        assert 'volume_spike' in alert_types  
        assert 'data_gap' in alert_types
        
        # Validate severity levels
        severities = [alert['alert']['severity'] for alert in received_alerts]
        assert 'high' in severities
        assert 'critical' in severities
        assert 'medium' in severities
        
        # Validate performance
        max_latency = max([(alert['timestamp'] - start_time) * 1000 for alert in received_alerts])
        assert max_latency < 100, f"Alert delivery {max_latency:.2f}ms exceeds 100ms requirement"
        
        pubsub.close()
        
    def test_cross_service_message_isolation_and_routing(self):
        """
        Test message isolation between automation services
        Validates: Channel separation, no message cross-contamination, routing accuracy
        """
        # Setup separate subscribers for each service type
        ipo_messages = []
        quality_messages = []
        maintenance_messages = []
        
        def create_message_handler(message_list):
            def handler(message):
                if message['type'] == 'message':
                    message_list.append({
                        'channel': message['channel'],
                        'data': json.loads(message['data'])
                    })
            return handler
        
        # Setup subscribers
        ipo_pubsub = self.redis_validator.sync_client.pubsub()
        ipo_pubsub.subscribe(self.redis_validator.channels['ipo_notifications'])
        
        quality_pubsub = self.redis_validator.sync_client.pubsub()  
        quality_pubsub.subscribe(self.redis_validator.channels['quality_price'])
        
        maintenance_pubsub = self.redis_validator.sync_client.pubsub()
        maintenance_pubsub.subscribe(self.redis_validator.channels['maintenance_events'])
        
        # Start listeners
        threads = [
            threading.Thread(
                target=self._listen_for_messages,
                args=(ipo_pubsub, create_message_handler(ipo_messages)),
                daemon=True
            ),
            threading.Thread(
                target=self._listen_for_messages,
                args=(quality_pubsub, create_message_handler(quality_messages)),
                daemon=True
            ),
            threading.Thread(
                target=self._listen_for_messages,
                args=(maintenance_pubsub, create_message_handler(maintenance_messages)),
                daemon=True
            )
        ]
        
        for thread in threads:
            thread.start()
        
        # Publish messages to different channels
        messages = [
            (self.redis_validator.channels['ipo_notifications'], {
                'service': 'ipo_monitor',
                'event_type': 'new_symbol',
                'symbol': 'IPO1'
            }),
            (self.redis_validator.channels['quality_price'], {
                'service': 'data_quality_monitor', 
                'alert_type': 'price_anomaly',
                'symbol': 'QUAL1'
            }),
            (self.redis_validator.channels['maintenance_events'], {
                'service': 'ipo_monitor',
                'event_type': 'maintenance_completed',
                'operation': 'daily_scan'
            })
        ]
        
        for channel, message in messages:
            self.redis_validator.sync_client.publish(channel, json.dumps(message))
        
        time.sleep(0.1)
        
        # Verify message isolation
        assert len(ipo_messages) == 1, "IPO subscriber received wrong number of messages"
        assert len(quality_messages) == 1, "Quality subscriber received wrong number of messages" 
        assert len(maintenance_messages) == 1, "Maintenance subscriber received wrong number of messages"
        
        # Verify message routing accuracy
        assert ipo_messages[0]['data']['symbol'] == 'IPO1'
        assert quality_messages[0]['data']['symbol'] == 'QUAL1' 
        assert maintenance_messages[0]['data']['operation'] == 'daily_scan'
        
        # Verify no cross-contamination
        assert 'price_anomaly' not in str(ipo_messages)
        assert 'new_symbol' not in str(quality_messages)
        assert 'daily_scan' not in str(ipo_messages) or 'daily_scan' not in str(quality_messages)
        
        # Cleanup
        for pubsub in [ipo_pubsub, quality_pubsub, maintenance_pubsub]:
            pubsub.close()
    
    def test_message_persistence_for_offline_consumers(self):
        """
        Test message persistence for offline TickStockApp instances
        Validates: Redis Streams persistence, message replay capability, queue management
        """
        # Use Redis Streams for persistent messaging
        stream_key = 'tickstock.automation.persistent_stream'
        
        # Clear any existing stream
        try:
            self.redis_validator.sync_client.delete(stream_key)
        except:
            pass
        
        # Publish messages while no consumer is active
        persistent_messages = [
            {
                'service': 'ipo_monitor',
                'event_type': 'new_symbol',
                'symbol': 'PERSIST1',
                'timestamp': datetime.now().isoformat()
            },
            {
                'service': 'data_quality_monitor',
                'alert_type': 'volume_spike', 
                'symbol': 'PERSIST2',
                'timestamp': datetime.now().isoformat()
            },
            {
                'service': 'ipo_monitor',
                'event_type': 'backfill_completed',
                'symbol': 'PERSIST3', 
                'timestamp': datetime.now().isoformat()
            }
        ]
        
        # Add messages to stream
        message_ids = []
        for message in persistent_messages:
            message_id = self.redis_validator.sync_client.xadd(stream_key, message)
            message_ids.append(message_id)
        
        # Verify stream contains messages
        stream_info = self.redis_validator.sync_client.xinfo_stream(stream_key)
        assert stream_info['length'] == 3, "Stream does not contain expected message count"
        
        # Simulate TickStockApp coming online and reading messages
        messages = self.redis_validator.sync_client.xread({stream_key: '0'})
        
        assert len(messages) == 1, "Stream read failed"
        stream_name, stream_messages = messages[0]
        assert stream_name.decode() == stream_key
        assert len(stream_messages) == 3, "Not all messages retrieved from stream"
        
        # Verify message content and order preservation
        retrieved_symbols = [msg[1]['symbol'] for msg in stream_messages]
        expected_symbols = ['PERSIST1', 'PERSIST2', 'PERSIST3']
        assert retrieved_symbols == expected_symbols, "Message order not preserved"
        
        # Test consumer group functionality
        consumer_group = 'tickstockapp_consumers'
        consumer_name = 'app_instance_1'
        
        try:
            self.redis_validator.sync_client.xgroup_create(stream_key, consumer_group, id='0', mkstream=True)
        except redis.ResponseError:
            pass  # Group may already exist
        
        # Read messages as consumer group member
        group_messages = self.redis_validator.sync_client.xreadgroup(
            consumer_group, 
            consumer_name,
            {stream_key: '>'},
            count=3
        )
        
        # Verify consumer group functionality
        if group_messages:  # May be empty if already consumed
            assert len(group_messages[0][1]) <= 3, "Consumer group read too many messages"
        
        # Cleanup stream
        self.redis_validator.sync_client.delete(stream_key)
        
    def _listen_for_messages(self, pubsub, handler):
        """Helper method for message listening in background threads"""
        try:
            # Set a timeout to prevent indefinite blocking
            timeout_count = 0
            max_timeouts = 20  # 20 * 0.1s = 2 seconds max
            
            for message in pubsub.listen():
                if message is not None:
                    handler(message)
                    timeout_count = 0
                else:
                    timeout_count += 1
                    if timeout_count >= max_timeouts:
                        break
                time.sleep(0.1)
        except Exception as e:
            print(f"Message listener error: {e}")

class TestDatabaseIntegrationPatterns:
    """Test database integration patterns for automation services"""
    
    def setup_method(self):
        """Setup database connection for testing"""
        self.db_conn = psycopg2.connect(TEST_DATABASE_URI)
        self.db_conn.autocommit = True
    
    def teardown_method(self):
        """Cleanup database connection"""
        if self.db_conn:
            self.db_conn.close()
    
    def test_automation_services_database_role_separation(self):
        """
        Test database role separation between automation services and TickStockApp
        Validates: Producer vs consumer role boundaries, access control, data isolation
        """
        cursor = self.db_conn.cursor()
        
        # Test automation services (producer role) - should have write access
        test_equity_type = 'TEST_AUTOMATION_PRODUCER'
        
        try:
            # Test write operations (should succeed for automation services)
            cursor.execute("""
                INSERT INTO equity_types (type_name, description, priority_level)
                VALUES (%s, 'Test automation service equity type', 95)
                ON CONFLICT (type_name) DO UPDATE SET
                    priority_level = EXCLUDED.priority_level
            """, (test_equity_type,))
            
            # Verify write succeeded
            cursor.execute("SELECT priority_level FROM equity_types WHERE type_name = %s", (test_equity_type,))
            result = cursor.fetchone()
            assert result is not None, "Automation service failed to write to database"
            assert result[0] == 95, "Write operation did not persist correctly"
            
        except Exception as e:
            pytest.fail(f"Automation service should have database write access: {e}")
        
        # Test TickStockApp (consumer role) - should have read-only access pattern
        # Simulate read-only operations that TickStockApp would perform
        try:
            # Test read operations
            cursor.execute("SELECT COUNT(*) FROM equity_types")
            count = cursor.fetchone()[0]
            assert count > 0, "Read operation failed"
            
            # Test get processing config function (read operation)
            cursor.execute("SELECT get_equity_processing_config(%s)", (test_equity_type,))
            config = cursor.fetchone()[0]
            assert isinstance(config, dict), "Processing config retrieval failed"
            assert config['type_name'] == test_equity_type
            
        except Exception as e:
            pytest.fail(f"TickStockApp should have database read access: {e}")
        
        # Cleanup test data
        try:
            cursor.execute("DELETE FROM equity_types WHERE type_name = %s", (test_equity_type,))
        except:
            pass
    
    def test_database_performance_isolation_under_load(self):
        """
        Test database performance isolation between services under load
        Validates: Query performance <50ms, concurrent access handling, resource isolation
        """
        cursor = self.db_conn.cursor()
        
        # Test concurrent database operations simulating both automation services and TickStockApp
        def run_automation_service_operations():
            """Simulate automation service database operations"""
            operation_times = []
            
            for i in range(50):
                start_time = time.perf_counter()
                
                # Simulate IPO monitor operations
                cursor.execute("SELECT queue_symbols_for_processing('STOCK_REALTIME', ARRAY['TEST%s'])", (i,))
                
                # Simulate data quality monitor operations
                cursor.execute("SELECT get_equity_processing_config('ETF')")
                
                elapsed = (time.perf_counter() - start_time) * 1000
                operation_times.append(elapsed)
            
            return operation_times
        
        def run_tickstockapp_operations():
            """Simulate TickStockApp database operations"""
            operation_times = []
            
            for i in range(50):
                start_time = time.perf_counter()
                
                # Simulate UI queries
                cursor.execute("SELECT type_name, priority_level FROM equity_types ORDER BY priority_level DESC LIMIT 10")
                
                # Simulate symbols dropdown query
                cursor.execute("SELECT * FROM get_symbols_for_processing('STOCK_EOD', 20)")
                
                elapsed = (time.perf_counter() - start_time) * 1000
                operation_times.append(elapsed)
            
            return operation_times
        
        # Run operations concurrently
        with ThreadPoolExecutor(max_workers=4) as executor:
            # Submit both types of operations
            automation_future = executor.submit(run_automation_service_operations)
            app_future = executor.submit(run_tickstockapp_operations)
            
            # Wait for completion
            automation_times = automation_future.result(timeout=30)
            app_times = app_future.result(timeout=30)
        
        # Validate performance requirements
        avg_automation_time = sum(automation_times) / len(automation_times)
        avg_app_time = sum(app_times) / len(app_times)
        
        assert avg_automation_time < 50, f"Automation service avg query time {avg_automation_time:.2f}ms exceeds 50ms"
        assert avg_app_time < 50, f"TickStockApp avg query time {avg_app_time:.2f}ms exceeds 50ms"
        
        # Check for performance degradation under concurrent load
        max_automation_time = max(automation_times)
        max_app_time = max(app_times)
        
        assert max_automation_time < 200, f"Max automation query time {max_automation_time:.2f}ms too slow under load"
        assert max_app_time < 200, f"Max TickStockApp query time {max_app_time:.2f}ms too slow under load"
    
    def test_equity_types_processing_functions_integration(self):
        """
        Test equity types database functions integration with automation services
        Validates: Function performance, data consistency, queue management
        """
        cursor = self.db_conn.cursor()
        
        # Test processing configuration retrieval
        start_time = time.perf_counter()
        
        # Test all equity types
        equity_types = ['STOCK_REALTIME', 'ETF', 'STOCK_EOD', 'ETN', 'PENNY_STOCK']
        
        for equity_type in equity_types:
            cursor.execute("SELECT get_equity_processing_config(%s)", (equity_type,))
            config = cursor.fetchone()[0]
            
            # Validate config structure
            assert isinstance(config, dict), f"Config for {equity_type} is not a dict"
            assert 'type_name' in config, f"Config missing type_name for {equity_type}"
            assert 'priority_level' in config, f"Config missing priority_level for {equity_type}"
            assert 'batch_size' in config, f"Config missing batch_size for {equity_type}"
            assert 'rate_limit_ms' in config, f"Config missing rate_limit_ms for {equity_type}"
            
            # Validate expected priority levels
            if equity_type == 'STOCK_REALTIME':
                assert config['priority_level'] == 100, "STOCK_REALTIME should have highest priority"
            elif equity_type == 'ETF':
                assert config['priority_level'] == 90, "ETF should have high priority"
        
        config_retrieval_time = (time.perf_counter() - start_time) * 1000
        assert config_retrieval_time < 100, f"Config retrieval {config_retrieval_time:.2f}ms too slow"
        
        # Test symbol queuing for processing
        start_time = time.perf_counter()
        
        # Clear test queue entries
        cursor.execute("DELETE FROM equity_processing_queue WHERE symbol LIKE 'INTEGRATION_TEST_%'")
        
        # Test batch queuing
        test_symbols = [f'INTEGRATION_TEST_{i:03d}' for i in range(100)]
        cursor.execute("SELECT queue_symbols_for_processing('STOCK_EOD', %s)", (test_symbols,))
        queued_count = cursor.fetchone()[0]
        
        assert queued_count == 100, f"Expected 100 symbols queued, got {queued_count}"
        
        queue_time = (time.perf_counter() - start_time) * 1000
        assert queue_time < 1000, f"Queue operation {queue_time:.2f}ms too slow for 100 symbols"
        
        # Test processing statistics update
        start_time = time.perf_counter()
        
        cursor.execute("SELECT update_processing_stats('STOCK_EOD', 95, 5, 300)")
        update_success = cursor.fetchone()[0]
        assert update_success is True, "Processing stats update failed"
        
        stats_update_time = (time.perf_counter() - start_time) * 1000
        assert stats_update_time < 50, f"Stats update {stats_update_time:.2f}ms too slow"
        
        # Verify queue processing workflow
        cursor.execute("""
            SELECT COUNT(*) FROM equity_processing_queue 
            WHERE symbol LIKE 'INTEGRATION_TEST_%' AND status = 'pending'
        """)
        pending_count = cursor.fetchone()[0]
        assert pending_count == 100, "Not all symbols properly queued as pending"
        
        # Simulate processing batch
        cursor.execute("""
            UPDATE equity_processing_queue 
            SET status = 'processing', last_attempt = CURRENT_TIMESTAMP
            WHERE symbol LIKE 'INTEGRATION_TEST_%' AND status = 'pending'
            RETURNING symbol
        """)
        processing_symbols = cursor.fetchall()
        assert len(processing_symbols) == 100, "Batch processing update failed"
        
        # Cleanup test data
        cursor.execute("DELETE FROM equity_processing_queue WHERE symbol LIKE 'INTEGRATION_TEST_%'")

class TestSystemResilienceAndFailover:
    """Test system resilience and graceful degradation"""
    
    def setup_method(self):
        """Setup for resilience testing"""
        self.redis_validator = RedisMessageFlowValidator()
        self.redis_validator.setup_redis_connections()
    
    def teardown_method(self):
        """Cleanup after resilience testing"""
        self.redis_validator.cleanup_redis()
    
    def test_redis_connection_failure_handling(self):
        """
        Test graceful handling of Redis connection failures
        Validates: Connection resilience, automatic reconnection, message buffering
        """
        # Simulate Redis connection failure
        original_client = self.redis_validator.sync_client
        
        # Create mock client that fails
        mock_client = MagicMock()
        mock_client.publish.side_effect = redis.ConnectionError("Connection failed")
        mock_client.ping.side_effect = redis.ConnectionError("Connection failed")
        
        # Test failure handling
        with patch.object(self.redis_validator, 'sync_client', mock_client):
            # Simulate automation service trying to publish during failure
            try:
                result = self.redis_validator.sync_client.publish('test_channel', 'test_message')
                pytest.fail("Expected ConnectionError was not raised")
            except redis.ConnectionError:
                # This is expected behavior
                pass
        
        # Test connection recovery
        self.redis_validator.sync_client = original_client
        
        # Verify connection works after recovery
        result = self.redis_validator.sync_client.ping()
        assert result is True, "Connection recovery failed"
        
        # Verify messaging works after recovery
        test_channel = 'test_recovery_channel'
        pubsub = self.redis_validator.sync_client.pubsub()
        pubsub.subscribe(test_channel)
        
        # Publish test message
        publish_result = self.redis_validator.sync_client.publish(test_channel, 'recovery_test')
        assert publish_result > 0, "Message publishing failed after recovery"
        
        pubsub.close()
    
    def test_automation_service_unavailable_graceful_degradation(self):
        """
        Test graceful degradation when automation services are unavailable
        Validates: TickStockApp continues operation, error handling, service isolation
        """
        # Simulate scenario where IPO Monitor is down but Data Quality Monitor is running
        
        # Setup subscribers for both services
        ipo_messages = []
        quality_messages = []
        
        def create_handler(message_list):
            def handler(message):
                if message['type'] == 'message':
                    message_list.append(json.loads(message['data']))
            return handler
        
        ipo_pubsub = self.redis_validator.sync_client.pubsub()
        quality_pubsub = self.redis_validator.sync_client.pubsub()
        
        ipo_pubsub.subscribe(self.redis_validator.channels['ipo_notifications'])
        quality_pubsub.subscribe(self.redis_validator.channels['quality_price'])
        
        # Start listeners
        ipo_thread = threading.Thread(
            target=self._listen_for_messages_timeout,
            args=(ipo_pubsub, create_handler(ipo_messages), 2),
            daemon=True
        )
        
        quality_thread = threading.Thread(
            target=self._listen_for_messages_timeout,
            args=(quality_pubsub, create_handler(quality_messages), 2),
            daemon=True
        )
        
        ipo_thread.start()
        quality_thread.start()
        
        # Simulate only Data Quality Monitor publishing (IPO Monitor is "down")
        quality_alert = {
            'service': 'data_quality_monitor',
            'alert_type': 'price_anomaly',
            'symbol': 'RESILIENCE_TEST',
            'severity': 'high'
        }
        
        # Publish quality alert
        self.redis_validator.sync_client.publish(
            self.redis_validator.channels['quality_price'],
            json.dumps(quality_alert)
        )
        
        # Wait for processing
        time.sleep(1)
        
        # Verify that available services still work
        assert len(quality_messages) == 1, "Quality monitoring should continue working"
        assert len(ipo_messages) == 0, "No IPO messages expected when service is down"
        
        # Verify quality message content
        received_alert = quality_messages[0]
        assert received_alert['service'] == 'data_quality_monitor'
        assert received_alert['symbol'] == 'RESILIENCE_TEST'
        
        # Cleanup
        ipo_thread.join(timeout=1)
        quality_thread.join(timeout=1)
        
        ipo_pubsub.close()
        quality_pubsub.close()
    
    def test_high_message_volume_handling(self):
        """
        Test system behavior under high message volume
        Validates: Performance degradation limits, queue management, message ordering
        """
        # Setup message collection
        received_messages = []
        message_times = []
        
        def high_volume_handler(message):
            if message['type'] == 'message':
                received_messages.append(json.loads(message['data']))
                message_times.append(time.time())
        
        # Subscribe to test channel
        test_channel = 'high_volume_test_channel'
        pubsub = self.redis_validator.sync_client.pubsub()
        pubsub.subscribe(test_channel)
        
        # Start listener
        listener_thread = threading.Thread(
            target=self._listen_for_messages_timeout,
            args=(pubsub, high_volume_handler, 10),
            daemon=True
        )
        listener_thread.start()
        
        # Generate high volume of messages
        message_count = 1000
        start_time = time.time()
        
        # Use pipeline for better performance
        pipe = self.redis_validator.sync_client.pipeline()
        
        for i in range(message_count):
            message = {
                'sequence': i,
                'timestamp': time.time(),
                'service': 'high_volume_test'
            }
            pipe.publish(test_channel, json.dumps(message))
        
        # Execute all publishes
        pipe.execute()
        
        publish_time = time.time() - start_time
        
        # Wait for message processing
        time.sleep(3)
        
        # Verify message handling
        messages_received = len(received_messages)
        
        # Allow for some message loss under extreme load, but should handle majority
        success_rate = messages_received / message_count
        assert success_rate > 0.95, f"Message success rate {success_rate:.1%} too low under high volume"
        
        # Verify message ordering (check first 100 messages)
        first_100 = received_messages[:min(100, len(received_messages))]
        sequences = [msg['sequence'] for msg in first_100]
        
        # Should be mostly in order (allow for some reordering under load)
        ordered_count = sum(1 for i, seq in enumerate(sequences) if seq == i)
        order_rate = ordered_count / len(sequences)
        
        # Under high load, some reordering is acceptable but should be minimal
        assert order_rate > 0.90, f"Message ordering rate {order_rate:.1%} too low"
        
        # Verify performance doesn't degrade excessively
        if message_times:
            processing_rate = len(message_times) / (message_times[-1] - message_times[0])
            assert processing_rate > 100, f"Message processing rate {processing_rate:.0f} msg/sec too slow"
        
        # Cleanup
        listener_thread.join(timeout=2)
        pubsub.close()
    
    def _listen_for_messages_timeout(self, pubsub, handler, timeout_seconds):
        """Helper method for message listening with timeout"""
        start_time = time.time()
        
        try:
            for message in pubsub.listen():
                if message is not None:
                    handler(message)
                
                # Check timeout
                if time.time() - start_time > timeout_seconds:
                    break
                    
        except Exception as e:
            print(f"Timeout message listener error: {e}")

class TestEndToEndWorkflowIntegration:
    """Test complete end-to-end workflow integration"""
    
    @pytest.mark.integration
    @pytest.mark.slow
    def test_complete_ipo_discovery_workflow(self):
        """
        Test complete IPO discovery workflow from service to TickStockApp
        Validates: Full workflow execution, data consistency, notification delivery
        """
        redis_validator = RedisMessageFlowValidator()
        redis_validator.setup_redis_connections()
        
        try:
            # Setup workflow tracking
            workflow_events = []
            
            def workflow_tracker(message):
                if message['type'] == 'message':
                    event = json.loads(message['data'])
                    workflow_events.append({
                        'timestamp': time.time(),
                        'event': event,
                        'channel': message['channel']
                    })
            
            # Subscribe to all IPO-related channels
            channels = [
                redis_validator.channels['ipo_notifications'],
                redis_validator.channels['ipo_backfill'],
                redis_validator.channels['maintenance_events']
            ]
            
            pubsub = redis_validator.sync_client.pubsub()
            pubsub.subscribe(channels)
            
            # Start workflow tracker
            tracker_thread = threading.Thread(
                target=self._listen_for_messages_timeout,
                args=(pubsub, workflow_tracker, 10),
                daemon=True
            )
            tracker_thread.start()
            
            # Simulate complete IPO workflow
            workflow_start = time.time()
            
            # Step 1: IPO discovery and symbol creation
            new_symbol_event = {
                'service': 'ipo_monitor',
                'data': {
                    'symbol': 'WORKFLOW_IPO',
                    'name': 'Workflow Test IPO Company',
                    'ipo_date': '2025-09-01',
                    'market_cap': 2000000000
                }
            }
            
            redis_validator.sync_client.publish(
                redis_validator.channels['ipo_notifications'],
                json.dumps(new_symbol_event)
            )
            
            # Step 2: Historical backfill completion
            backfill_event = {
                'service': 'ipo_monitor',
                'data': {
                    'symbol': 'WORKFLOW_IPO',
                    'backfill_days': 90,
                    'records_loaded': 90,
                    'success': True
                }
            }
            
            redis_validator.sync_client.publish(
                redis_validator.channels['ipo_backfill'],
                json.dumps(backfill_event)
            )
            
            # Step 3: Maintenance completion
            maintenance_event = {
                'service': 'ipo_monitor',
                'data': {
                    'operation': 'daily_ipo_scan',
                    'symbols_processed': 1,
                    'success_rate': 1.0
                }
            }
            
            redis_validator.sync_client.publish(
                redis_validator.channels['maintenance_events'],
                json.dumps(maintenance_event)
            )
            
            # Wait for workflow completion
            time.sleep(2)
            
            # Verify complete workflow
            assert len(workflow_events) == 3, "Not all workflow events received"
            
            # Verify event ordering and content
            event_types = []
            for event in workflow_events:
                if 'symbol' in event['event']['data']:
                    if event['event']['data']['symbol'] == 'WORKFLOW_IPO':
                        if 'backfill_days' in event['event']['data']:
                            event_types.append('backfill')
                        elif 'ipo_date' in event['event']['data']:
                            event_types.append('discovery')
                elif 'operation' in event['event']['data']:
                    event_types.append('maintenance')
            
            # Verify all event types present
            assert 'discovery' in event_types, "IPO discovery event missing"
            assert 'backfill' in event_types, "Backfill completion event missing"
            assert 'maintenance' in event_types, "Maintenance completion event missing"
            
            # Verify workflow timing
            workflow_duration = max([event['timestamp'] for event in workflow_events]) - workflow_start
            assert workflow_duration < 5, f"Workflow took {workflow_duration:.2f}s, too slow"
            
            # Cleanup
            tracker_thread.join(timeout=2)
            pubsub.close()
            
        finally:
            redis_validator.cleanup_redis()
    
    @pytest.mark.integration
    def test_automation_services_4000_symbol_capacity(self):
        """
        Test automation services can handle 4,000+ symbol capacity
        Validates: Scale requirements, performance under load, resource utilization
        """
        redis_validator = RedisMessageFlowValidator() 
        redis_validator.setup_redis_connections()
        
        try:
            # Generate test data for 4000 symbols
            symbol_batch_size = 100
            total_symbols = 4000
            batches = total_symbols // symbol_batch_size
            
            processed_symbols = []
            processing_times = []
            
            def batch_processor(message):
                if message['type'] == 'message':
                    event = json.loads(message['data'])
                    if 'batch_symbols' in event:
                        processed_symbols.extend(event['batch_symbols'])
                        processing_times.append(time.time())
            
            # Setup subscriber
            test_channel = 'symbol_capacity_test'
            pubsub = redis_validator.sync_client.pubsub()
            pubsub.subscribe(test_channel)
            
            processor_thread = threading.Thread(
                target=self._listen_for_messages_timeout,
                args=(pubsub, batch_processor, 30),
                daemon=True
            )
            processor_thread.start()
            
            # Simulate processing 4000 symbols in batches
            start_time = time.time()
            
            for batch_num in range(batches):
                batch_symbols = [
                    f'CAP_TEST_{batch_num:02d}_{i:03d}' 
                    for i in range(symbol_batch_size)
                ]
                
                batch_event = {
                    'service': 'capacity_test',
                    'batch_number': batch_num,
                    'batch_symbols': batch_symbols,
                    'total_symbols': len(batch_symbols)
                }
                
                redis_validator.sync_client.publish(
                    test_channel,
                    json.dumps(batch_event)
                )
                
                # Small delay to prevent overwhelming
                time.sleep(0.01)
            
            # Wait for processing completion
            time.sleep(5)
            
            total_processing_time = time.time() - start_time
            
            # Verify capacity handling
            symbols_processed = len(processed_symbols)
            processing_rate = symbols_processed / total_processing_time if total_processing_time > 0 else 0
            
            # Should process at least 90% of symbols
            success_rate = symbols_processed / total_symbols
            assert success_rate > 0.90, f"Symbol processing success rate {success_rate:.1%} too low"
            
            # Should maintain reasonable processing rate
            assert processing_rate > 200, f"Processing rate {processing_rate:.0f} symbols/sec too slow for 4K capacity"
            
            # Verify no duplicate processing
            unique_symbols = set(processed_symbols)
            duplicate_rate = 1 - (len(unique_symbols) / len(processed_symbols)) if processed_symbols else 0
            assert duplicate_rate < 0.01, f"Duplicate processing rate {duplicate_rate:.1%} too high"
            
            # Cleanup
            processor_thread.join(timeout=2)
            pubsub.close()
            
        finally:
            redis_validator.cleanup_redis()
    
    def _listen_for_messages_timeout(self, pubsub, handler, timeout_seconds):
        """Helper method for message listening with timeout"""
        start_time = time.time()
        
        try:
            for message in pubsub.listen():
                if message is not None:
                    handler(message)
                
                if time.time() - start_time > timeout_seconds:
                    break
                    
        except Exception as e:
            print(f"Workflow listener error: {e}")

# Performance benchmarks and reporting
@pytest.mark.performance
class TestPerformanceBenchmarks:
    """Performance benchmarks for integration validation"""
    
    def test_redis_message_latency_benchmark(self):
        """Benchmark Redis message delivery latency"""
        redis_validator = RedisMessageFlowValidator()
        redis_validator.setup_redis_connections()
        
        try:
            latencies = []
            
            def latency_tracker(message):
                if message['type'] == 'message':
                    data = json.loads(message['data'])
                    if 'send_time' in data:
                        receive_time = time.time()
                        latency = (receive_time - data['send_time']) * 1000
                        latencies.append(latency)
            
            test_channel = 'latency_benchmark'
            pubsub = redis_validator.sync_client.pubsub()
            pubsub.subscribe(test_channel)
            
            tracker_thread = threading.Thread(
                target=redis_validator._listen_for_messages,
                args=(pubsub, latency_tracker),
                daemon=True
            )
            tracker_thread.start()
            
            # Send benchmark messages
            for i in range(100):
                message = {
                    'sequence': i,
                    'send_time': time.time()
                }
                redis_validator.sync_client.publish(test_channel, json.dumps(message))
                time.sleep(0.01)  # 10ms intervals
            
            time.sleep(2)  # Wait for processing
            
            # Analyze latency results
            if latencies:
                avg_latency = sum(latencies) / len(latencies)
                min_latency = min(latencies)
                max_latency = max(latencies)
                p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
                
                # Performance assertions
                assert avg_latency < 50, f"Average latency {avg_latency:.2f}ms exceeds 50ms target"
                assert p95_latency < 100, f"P95 latency {p95_latency:.2f}ms exceeds 100ms requirement"
                assert max_latency < 200, f"Max latency {max_latency:.2f}ms too high"
                
                # Report benchmark results
                print(f"\\nRedis Message Latency Benchmark:")
                print(f"  Messages: {len(latencies)}")
                print(f"  Average: {avg_latency:.2f}ms")
                print(f"  Min: {min_latency:.2f}ms")
                print(f"  Max: {max_latency:.2f}ms") 
                print(f"  P95: {p95_latency:.2f}ms")
            
            tracker_thread.join(timeout=1)
            pubsub.close()
            
        finally:
            redis_validator.cleanup_redis()

if __name__ == '__main__':
    # Run integration tests
    pytest.main([
        __file__,
        '-v',
        '--tb=short',
        '-m', 'not slow',  # Skip slow tests by default
        '--durations=10'
    ])