"""
Sprint 14 Phase 2: Automation Services Test Configuration

Shared fixtures and configuration for automation services testing including
IPO monitoring, data quality monitoring, and equity types processing.

Date: 2025-09-01
Sprint: 14 Phase 2
Status: Comprehensive Test Configuration
"""

import pytest
import redis
import psycopg2
from unittest.mock import Mock, MagicMock
from datetime import datetime, timedelta
from typing import Dict, List, Any
import json
import time

from src.database.connection import DatabaseConnection
from src.automation.services.ipo_monitor import IPOMonitor
from src.automation.services.data_quality_monitor import DataQualityMonitor


# =============================================================================
# Database Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def test_database_connection():
    """Session-scoped database connection for testing"""
    connection = DatabaseConnection(test_mode=True)
    yield connection
    connection.close()


@pytest.fixture
def db_cursor(test_database_connection):
    """Database cursor with automatic rollback"""
    cursor = test_database_connection.cursor()
    
    # Start transaction
    test_database_connection.begin()
    
    yield cursor
    
    # Rollback transaction to clean up test data
    test_database_connection.rollback()
    cursor.close()


@pytest.fixture
def clean_equity_types_table(db_cursor):
    """Clean equity types table for testing"""
    # Store existing data
    db_cursor.execute("SELECT * FROM equity_types")
    existing_data = db_cursor.fetchall()
    
    # Clear table for clean test
    db_cursor.execute("DELETE FROM equity_types")
    
    yield db_cursor
    
    # Restore original data
    if existing_data:
        columns = [desc[0] for desc in db_cursor.description]
        placeholders = ','.join(['%s'] * len(columns))
        db_cursor.execute(
            f"INSERT INTO equity_types ({','.join(columns)}) VALUES ({placeholders})",
            existing_data
        )


@pytest.fixture
def clean_processing_queue(db_cursor):
    """Clean processing queue table for testing"""
    db_cursor.execute("DELETE FROM equity_processing_queue WHERE equity_type LIKE 'TEST_%'")
    yield db_cursor


# =============================================================================
# Redis Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def redis_client():
    """Redis client for testing"""
    client = redis.Redis(
        host='localhost',
        port=6379,
        db=15,  # Use test database
        decode_responses=True
    )
    
    # Clear test database
    client.flushdb()
    
    yield client
    
    # Clean up
    client.flushdb()
    client.close()


@pytest.fixture
def mock_redis_client():
    """Mock Redis client for unit testing"""
    mock_client = Mock()
    mock_client.ping = Mock(return_value=True)
    mock_client.publish = Mock(return_value=1)
    mock_client.xadd = Mock(return_value='1234567890123-0')
    mock_client.xread = Mock(return_value=[])
    mock_client.flushdb = Mock(return_value=True)
    
    return mock_client


@pytest.fixture
def redis_subscriber(redis_client):
    """Redis pub-sub subscriber for testing message flow"""
    subscriber = redis_client.pubsub()
    
    yield subscriber
    
    subscriber.close()


# =============================================================================
# Service Fixtures
# =============================================================================

@pytest.fixture
def ipo_monitor():
    """IPO Monitor service instance for testing"""
    config = {
        'scan_frequency': 'daily',
        'backfill_days': 90,
        'redis_channel': 'test:ipo:notifications',
        'batch_size': 100,
        'rate_limit_ms': 1000  # Faster for testing
    }
    
    monitor = IPOMonitor(config)
    return monitor


@pytest.fixture
def ipo_monitor_with_mocks(mock_redis_client):
    """IPO Monitor with mocked dependencies"""
    monitor = IPOMonitor()
    monitor.redis_client = mock_redis_client
    monitor.db_connection = Mock()
    monitor.polygon_client = Mock()
    
    return monitor


@pytest.fixture
def data_quality_monitor():
    """Data Quality Monitor service instance for testing"""
    config = {
        'price_anomaly_threshold': 0.20,
        'volume_spike_threshold': 5.0,
        'volume_drought_threshold': 0.2,
        'max_data_gap_hours': 24,
        'staleness_threshold_hours': 2,
        'redis_channel': 'test:quality:alerts'
    }
    
    monitor = DataQualityMonitor(config)
    return monitor


@pytest.fixture
def quality_monitor_with_mocks(mock_redis_client):
    """Data Quality Monitor with mocked dependencies"""
    monitor = DataQualityMonitor()
    monitor.redis_client = mock_redis_client
    monitor.db_connection = Mock()
    
    return monitor


# =============================================================================
# Test Data Fixtures
# =============================================================================

@pytest.fixture
def sample_ipo_data():
    """Sample IPO data for testing"""
    return [
        {
            'ticker': 'TESTIPO1',
            'name': 'Test IPO Company 1 Inc',
            'market': 'stocks',
            'type': 'CS',
            'active': True,
            'currency_name': 'usd',
            'cik': '0001234567',
            'composite_figi': 'BBG123456789',
            'share_class_figi': 'BBG987654321',
            'market_cap': 1500000000,
            'primary_exchange': 'XNAS',
            'listing_date': '2025-09-01'
        },
        {
            'ticker': 'TESTIPO2',
            'name': 'Test IPO Company 2 Corp',
            'market': 'stocks',
            'type': 'CS',
            'active': True,
            'currency_name': 'usd',
            'market_cap': 800000000,
            'primary_exchange': 'XNYS',
            'listing_date': '2025-09-01'
        }
    ]


@pytest.fixture
def sample_price_data():
    """Sample price data with anomalies for testing"""
    return [
        {'date': '2025-08-25', 'close': 100.00},
        {'date': '2025-08-26', 'close': 102.00},  # 2% normal
        {'date': '2025-08-27', 'close': 125.00},  # 22.5% spike - anomaly
        {'date': '2025-08-28', 'close': 95.00},   # 24% drop - anomaly  
        {'date': '2025-08-29', 'close': 97.00},   # 2.1% recovery - normal
        {'date': '2025-08-30', 'close': 99.00},   # 2.1% gain - normal
    ]


@pytest.fixture
def sample_volume_data():
    """Sample volume data with spikes and droughts"""
    base_volume = 1000000
    return [
        {'date': f'2025-08-{i+1:02d}', 'volume': base_volume + (i * 50000)}
        for i in range(20)
    ] + [
        {'date': '2025-08-21', 'volume': base_volume * 6},    # 6x spike
        {'date': '2025-08-22', 'volume': base_volume * 0.15}, # 15% drought
        {'date': '2025-08-23', 'volume': base_volume},        # Normal
    ]


@pytest.fixture
def sample_historical_data():
    """Sample 90-day historical data for backfill testing"""
    base_date = datetime.now() - timedelta(days=90)
    data = []
    
    base_price = 100.0
    
    for i in range(90):
        date = base_date + timedelta(days=i)
        
        # Add small daily variations
        daily_change = 0.01 * (i % 5 - 2)  # -2% to +2% variation
        base_price *= (1 + daily_change)
        
        data.append({
            'o': round(base_price * 0.99, 2),
            'h': round(base_price * 1.02, 2), 
            'l': round(base_price * 0.97, 2),
            'c': round(base_price, 2),
            'v': 1000000 + (i * 10000),
            't': int(date.timestamp() * 1000)
        })
        
    return data


@pytest.fixture
def equity_types_test_data():
    """Test data for equity types configuration"""
    return [
        {
            'type_name': 'TEST_ETF',
            'description': 'Test ETF type',
            'update_frequency': 'daily',
            'processing_rules': {
                'aum_required': True,
                'expense_ratio_required': True,
                'correlation_tracking': True
            },
            'requires_eod_validation': True,
            'additional_data_fields': {
                'correlation_tracking': True,
                'premium_discount_monitoring': True
            },
            'priority_level': 90,
            'batch_size': 50,
            'rate_limit_ms': 12000
        },
        {
            'type_name': 'TEST_STOCK',
            'description': 'Test stock type',
            'update_frequency': 'realtime',
            'processing_rules': {
                'eod_validation': True,
                'intraday_processing': True,
                'pattern_detection': True
            },
            'requires_eod_validation': True,
            'additional_data_fields': {
                'intraday_priority': 'high',
                'pattern_alerts': True
            },
            'priority_level': 100,
            'batch_size': 25,
            'rate_limit_ms': 6000
        }
    ]


# =============================================================================
# Performance Testing Fixtures
# =============================================================================

@pytest.fixture
def performance_timer():
    """Performance timing utility for tests"""
    class PerformanceTimer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
            
        def start(self):
            self.start_time = time.perf_counter()
            
        def stop(self):
            self.end_time = time.perf_counter()
            
        @property
        def elapsed(self):
            if self.start_time is None or self.end_time is None:
                return 0
            return self.end_time - self.start_time
            
        def reset(self):
            self.start_time = None
            self.end_time = None
            
    return PerformanceTimer()


@pytest.fixture
def large_symbol_dataset():
    """Large dataset for performance testing"""
    return [f'PERF{i:04d}' for i in range(5000)]


@pytest.fixture
def memory_monitor():
    """Memory usage monitoring utility"""
    import psutil
    
    class MemoryMonitor:
        def __init__(self):
            self.initial_memory = None
            self.peak_memory = None
            self.final_memory = None
            
        def start(self):
            self.initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
            self.peak_memory = self.initial_memory
            
        def update(self):
            current_memory = psutil.Process().memory_info().rss / 1024 / 1024
            self.peak_memory = max(self.peak_memory or 0, current_memory)
            
        def stop(self):
            self.final_memory = psutil.Process().memory_info().rss / 1024 / 1024
            
        @property
        def memory_growth(self):
            if self.initial_memory is None or self.final_memory is None:
                return 0
            return self.final_memory - self.initial_memory
            
        @property
        def peak_memory_usage(self):
            if self.initial_memory is None or self.peak_memory is None:
                return 0
            return self.peak_memory - self.initial_memory
            
    return MemoryMonitor()


# =============================================================================
# Message Testing Fixtures
# =============================================================================

@pytest.fixture
def message_collector():
    """Collects messages for verification in tests"""
    class MessageCollector:
        def __init__(self):
            self.messages = []
            self.channels = {}
            
        def add_message(self, channel, message):
            self.messages.append({
                'channel': channel,
                'message': message,
                'timestamp': datetime.now()
            })
            
            if channel not in self.channels:
                self.channels[channel] = []
            self.channels[channel].append(message)
            
        def get_messages_for_channel(self, channel):
            return self.channels.get(channel, [])
            
        def clear(self):
            self.messages.clear()
            self.channels.clear()
            
        @property
        def message_count(self):
            return len(self.messages)
            
    return MessageCollector()


@pytest.fixture
def mock_polygon_api():
    """Mock Polygon.io API responses"""
    class MockPolygonAPI:
        def __init__(self):
            self.responses = {}
            
        def set_response(self, endpoint, response_data):
            self.responses[endpoint] = response_data
            
        def get_response(self, endpoint):
            return self.responses.get(endpoint, {'status': 'ERROR', 'error': 'No mock data'})
            
        def set_ticker_list_response(self, tickers):
            self.set_response('tickers', {
                'status': 'OK',
                'results': [
                    {
                        'ticker': ticker,
                        'name': f'{ticker} Test Company',
                        'market': 'stocks',
                        'type': 'CS',
                        'active': True,
                        'listing_date': '2025-09-01'
                    }
                    for ticker in tickers
                ]
            })
            
        def set_historical_response(self, ticker, data):
            self.set_response(f'aggs/{ticker}', {
                'status': 'OK',
                'results': data
            })
            
    return MockPolygonAPI()


# =============================================================================
# Integration Testing Fixtures
# =============================================================================

@pytest.fixture
def integration_test_setup(redis_client, test_database_connection):
    """Complete setup for integration testing"""
    class IntegrationSetup:
        def __init__(self):
            self.redis_client = redis_client
            self.db_connection = test_database_connection
            self.ipo_monitor = IPOMonitor()
            self.quality_monitor = DataQualityMonitor()
            
            # Configure services with test clients
            self.ipo_monitor.redis_client = redis_client
            self.ipo_monitor.db_connection = test_database_connection
            self.quality_monitor.redis_client = redis_client
            self.quality_monitor.db_connection = test_database_connection
            
        def cleanup(self):
            # Clean up test data
            self.redis_client.flushdb()
            
            # Clean up database
            cursor = self.db_connection.cursor()
            cursor.execute("DELETE FROM equity_processing_queue WHERE equity_type LIKE 'TEST_%'")
            cursor.execute("DELETE FROM symbols WHERE symbol LIKE 'TEST%'")
            self.db_connection.commit()
            cursor.close()
            
    setup = IntegrationSetup()
    yield setup
    setup.cleanup()


# =============================================================================
# Test Configuration
# =============================================================================

def pytest_configure(config):
    """Configure pytest markers"""
    config.addinivalue_line("markers", "performance: Performance benchmark tests")
    config.addinivalue_line("markers", "integration: Integration tests requiring external services")
    config.addinivalue_line("markers", "slow: Slow-running tests")
    config.addinivalue_line("markers", "database: Tests requiring database access")
    config.addinivalue_line("markers", "redis: Tests requiring Redis access")


def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on naming patterns"""
    for item in items:
        # Mark performance tests
        if "performance" in item.nodeid.lower():
            item.add_marker(pytest.mark.performance)
            
        # Mark integration tests
        if "integration" in item.nodeid.lower():
            item.add_marker(pytest.mark.integration)
            
        # Mark slow tests
        if any(keyword in item.nodeid.lower() for keyword in ['4000', '5000', 'large', 'concurrent']):
            item.add_marker(pytest.mark.slow)
            
        # Mark database tests
        if any(keyword in item.nodeid.lower() for keyword in ['database', 'db_', 'equity_types', 'queue']):
            item.add_marker(pytest.mark.database)
            
        # Mark Redis tests  
        if any(keyword in item.nodeid.lower() for keyword in ['redis', 'message', 'notification', 'alert']):
            item.add_marker(pytest.mark.redis)