"""
Configuration for Sprint 14 Phase 2 Automation Services Integration Tests

This configuration module provides fixtures and setup for comprehensive
integration testing of automation services with TickStockApp.

Date: 2025-09-01
Sprint: 14 Phase 2
"""

import pytest
import redis
import psycopg2
import os
import time
import asyncio
from typing import Dict, Any, Optional
from dataclasses import dataclass

# Test environment configuration
TEST_REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
TEST_REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
TEST_REDIS_DB = 15  # Dedicated test database
TEST_DATABASE_URI = os.getenv(
    'TEST_DATABASE_URI',
    'postgresql://app_readwrite:4pp_U$3r_2024!@localhost/tickstock'
)

@dataclass
class IntegrationTestEnvironment:
    """Test environment configuration and state"""
    redis_client: Optional[redis.Redis] = None
    db_connection: Optional[psycopg2.extensions.connection] = None
    test_channels: Dict[str, str] = None
    test_data_prefix: str = 'INTEGRATION_TEST'
    
    def __post_init__(self):
        if self.test_channels is None:
            self.test_channels = {
                'ipo_notifications': 'tickstock.automation.symbols.new',
                'ipo_backfill': 'tickstock.automation.backfill.completed',
                'quality_price': 'tickstock.quality.price_anomaly',
                'quality_volume': 'tickstock.quality.volume_anomaly',
                'quality_gaps': 'tickstock.quality.data_gap',
                'maintenance_events': 'tickstock.automation.maintenance.completed'
            }

@pytest.fixture(scope="session")
def integration_test_env():
    """Session-scoped integration test environment"""
    env = IntegrationTestEnvironment()
    
    # Setup Redis connection
    try:
        env.redis_client = redis.Redis(
            host=TEST_REDIS_HOST,
            port=TEST_REDIS_PORT, 
            db=TEST_REDIS_DB,
            decode_responses=True,
            socket_timeout=5.0
        )
        env.redis_client.ping()
        print(f"✓ Redis connected: {TEST_REDIS_HOST}:{TEST_REDIS_PORT}/{TEST_REDIS_DB}")
    except Exception as e:
        pytest.skip(f"Redis connection failed: {e}")
    
    # Setup database connection
    try:
        env.db_connection = psycopg2.connect(TEST_DATABASE_URI)
        env.db_connection.autocommit = True
        print(f"✓ Database connected: {TEST_DATABASE_URI.split('@')[1] if '@' in TEST_DATABASE_URI else 'localhost'}")
    except Exception as e:
        pytest.skip(f"Database connection failed: {e}")
    
    yield env
    
    # Cleanup
    if env.redis_client:
        try:
            env.redis_client.flushdb()
            env.redis_client.close()
        except:
            pass
    
    if env.db_connection:
        try:
            env.db_connection.close()
        except:
            pass

@pytest.fixture(scope="function")
def clean_redis(integration_test_env):
    """Function-scoped Redis cleanup"""
    # Clear test database before test
    integration_test_env.redis_client.flushdb()
    
    yield integration_test_env.redis_client
    
    # Clear test database after test
    try:
        integration_test_env.redis_client.flushdb()
    except:
        pass

@pytest.fixture(scope="function")
def clean_database(integration_test_env):
    """Function-scoped database cleanup"""
    cursor = integration_test_env.db_connection.cursor()
    
    # Clean up any test data before test
    try:
        cursor.execute("DELETE FROM equity_processing_queue WHERE symbol LIKE %s", 
                      (f"{integration_test_env.test_data_prefix}_%",))
        cursor.execute("DELETE FROM equity_types WHERE type_name LIKE %s",
                      (f"{integration_test_env.test_data_prefix}_%",))
    except:
        pass
    
    yield cursor
    
    # Clean up test data after test
    try:
        cursor.execute("DELETE FROM equity_processing_queue WHERE symbol LIKE %s", 
                      (f"{integration_test_env.test_data_prefix}_%",))
        cursor.execute("DELETE FROM equity_types WHERE type_name LIKE %s",
                      (f"{integration_test_env.test_data_prefix}_%",))
    except:
        pass

@pytest.fixture(scope="function") 
def redis_message_collector():
    """Utility fixture for collecting Redis messages during tests"""
    
    class MessageCollector:
        def __init__(self):
            self.messages = []
            self.channels = {}
            self.start_time = time.time()
            
        def add_subscriber(self, redis_client, channels):
            """Add subscriber for specified channels"""
            pubsub = redis_client.pubsub()
            pubsub.subscribe(channels)
            self.channels.update({ch: pubsub for ch in channels})
            return pubsub
            
        def collect_message(self, message):
            """Collect a message with timestamp"""
            if message['type'] == 'message':
                self.messages.append({
                    'channel': message['channel'],
                    'data': message['data'],
                    'timestamp': time.time() - self.start_time
                })
                
        def get_messages_for_channel(self, channel):
            """Get all messages for a specific channel"""
            return [msg for msg in self.messages if msg['channel'] == channel]
            
        def get_latest_message(self, channel):
            """Get the most recent message for a channel"""
            channel_messages = self.get_messages_for_channel(channel)
            return channel_messages[-1] if channel_messages else None
            
        def cleanup(self):
            """Cleanup all subscriptions"""
            for pubsub in self.channels.values():
                try:
                    pubsub.close()
                except:
                    pass
    
    collector = MessageCollector()
    yield collector
    collector.cleanup()

@pytest.fixture(scope="function")
def performance_monitor():
    """Performance monitoring fixture for integration tests"""
    
    class PerformanceMonitor:
        def __init__(self):
            self.metrics = {}
            self.start_times = {}
            
        def start_timer(self, operation_name):
            """Start timing an operation"""
            self.start_times[operation_name] = time.perf_counter()
            
        def end_timer(self, operation_name):
            """End timing and record duration"""
            if operation_name in self.start_times:
                duration = time.perf_counter() - self.start_times[operation_name]
                self.metrics[operation_name] = duration * 1000  # Convert to milliseconds
                return self.metrics[operation_name]
            return None
            
        def get_metric(self, operation_name):
            """Get recorded metric"""
            return self.metrics.get(operation_name)
            
        def assert_performance(self, operation_name, max_duration_ms):
            """Assert performance requirement"""
            duration = self.get_metric(operation_name)
            if duration is None:
                raise AssertionError(f"No metric recorded for {operation_name}")
            if duration > max_duration_ms:
                raise AssertionError(
                    f"{operation_name} took {duration:.2f}ms, exceeds {max_duration_ms}ms requirement"
                )
                
        def get_summary(self):
            """Get performance summary"""
            return {
                'metrics': self.metrics,
                'total_operations': len(self.metrics),
                'avg_duration_ms': sum(self.metrics.values()) / len(self.metrics) if self.metrics else 0
            }
    
    return PerformanceMonitor()

@pytest.fixture(scope="function")
def mock_automation_services():
    """Mock automation services for testing"""
    
    class MockAutomationServices:
        def __init__(self, redis_client):
            self.redis_client = redis_client
            self.published_messages = []
            
        def publish_ipo_notification(self, symbol_data):
            """Mock IPO monitor notification"""
            event = {
                'timestamp': time.time(),
                'service': 'ipo_monitor',
                'event_type': 'new_symbol',
                'data': symbol_data
            }
            
            channel = 'tickstock.automation.symbols.new'
            result = self.redis_client.publish(channel, json.dumps(event))
            
            self.published_messages.append({
                'channel': channel,
                'event': event
            })
            
            return result > 0
            
        def publish_quality_alert(self, alert_data):
            """Mock data quality monitor alert"""
            event = {
                'timestamp': time.time(),
                'service': 'data_quality_monitor',
                'alert_type': alert_data.get('alert_type', 'unknown'),
                'data': alert_data
            }
            
            # Route to appropriate channel based on alert type
            channel_map = {
                'price_anomaly': 'tickstock.quality.price_anomaly',
                'volume_spike': 'tickstock.quality.volume_anomaly',
                'volume_drought': 'tickstock.quality.volume_anomaly',
                'data_gap': 'tickstock.quality.data_gap'
            }
            
            channel = channel_map.get(alert_data.get('alert_type'), 'tickstock.quality.price_anomaly')
            result = self.redis_client.publish(channel, json.dumps(event))
            
            self.published_messages.append({
                'channel': channel,
                'event': event
            })
            
            return result > 0
            
        def publish_maintenance_event(self, maintenance_data):
            """Mock maintenance completion event"""
            event = {
                'timestamp': time.time(),
                'service': maintenance_data.get('service', 'ipo_monitor'),
                'event_type': 'maintenance_completed',
                'data': maintenance_data
            }
            
            channel = 'tickstock.automation.maintenance.completed'
            result = self.redis_client.publish(channel, json.dumps(event))
            
            self.published_messages.append({
                'channel': channel,
                'event': event
            })
            
            return result > 0
            
        def get_published_count(self):
            """Get count of published messages"""
            return len(self.published_messages)
            
        def get_messages_for_channel(self, channel):
            """Get published messages for specific channel"""
            return [msg for msg in self.published_messages if msg['channel'] == channel]
    
    def _create_mock_services(redis_client):
        return MockAutomationServices(redis_client)
        
    return _create_mock_services

# Test markers for different integration test categories
def pytest_configure(config):
    """Configure custom pytest markers"""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "performance: marks tests as performance benchmarks"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running"
    )
    config.addinivalue_line(
        "markers", "redis: marks tests that require Redis"
    )
    config.addinivalue_line(
        "markers", "database: marks tests that require database"
    )
    config.addinivalue_line(
        "markers", "resilience: marks tests for system resilience"
    )

# Custom assertion helpers for integration testing
def assert_message_delivery_performance(start_time, end_time, max_latency_ms=100):
    """Assert message delivery meets performance requirements"""
    latency_ms = (end_time - start_time) * 1000
    if latency_ms > max_latency_ms:
        raise AssertionError(
            f"Message delivery latency {latency_ms:.2f}ms exceeds {max_latency_ms}ms requirement"
        )
    return latency_ms

def assert_database_performance(start_time, end_time, max_duration_ms=50):
    """Assert database operation meets performance requirements"""
    duration_ms = (end_time - start_time) * 1000
    if duration_ms > max_duration_ms:
        raise AssertionError(
            f"Database operation took {duration_ms:.2f}ms, exceeds {max_duration_ms}ms requirement"
        )
    return duration_ms

def assert_service_isolation(service_messages, expected_service, unexpected_services):
    """Assert proper service message isolation"""
    for message in service_messages:
        service_name = message.get('service', 'unknown')
        if service_name != expected_service and service_name in unexpected_services:
            raise AssertionError(
                f"Message contamination: {service_name} message found in {expected_service} channel"
            )

# Integration test data generators
def generate_test_symbols(count=100, prefix="TEST"):
    """Generate test symbols for capacity testing"""
    return [f"{prefix}_{i:04d}" for i in range(count)]

def generate_ipo_event_data(symbol, **kwargs):
    """Generate IPO event test data"""
    return {
        'symbol': symbol,
        'name': kwargs.get('name', f'{symbol} Test Company'),
        'type': kwargs.get('type', 'CS'),
        'market': kwargs.get('market', 'stocks'),
        'exchange': kwargs.get('exchange', 'NASDAQ'),
        'ipo_date': kwargs.get('ipo_date', '2025-09-01'),
        'market_cap': kwargs.get('market_cap', 1000000000)
    }

def generate_quality_alert_data(symbol, alert_type, **kwargs):
    """Generate quality alert test data"""
    base_data = {
        'symbol': symbol,
        'alert_type': alert_type,
        'severity': kwargs.get('severity', 'medium'),
        'timestamp': kwargs.get('timestamp', time.time())
    }
    
    if alert_type == 'price_anomaly':
        base_data.update({
            'price_change_pct': kwargs.get('price_change_pct', 0.25),
            'close_price': kwargs.get('close_price', 150.0),
            'previous_close': kwargs.get('previous_close', 120.0)
        })
    elif alert_type in ['volume_spike', 'volume_drought']:
        base_data.update({
            'volume': kwargs.get('volume', 50000000),
            'average_volume_20d': kwargs.get('average_volume_20d', 10000000),
            'volume_ratio': kwargs.get('volume_ratio', 5.0)
        })
    elif alert_type == 'data_gap':
        base_data.update({
            'days_stale': kwargs.get('days_stale', 3),
            'last_data_date': kwargs.get('last_data_date', '2025-08-29')
        })
    
    return base_data