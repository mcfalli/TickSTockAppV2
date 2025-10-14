"""
Sprint 14 Integration Test Configuration

Provides shared fixtures and configuration for all Sprint 14 
cross-system integration tests.
"""
import json
import threading
import time
from contextlib import contextmanager

import pytest
import redis
from sqlalchemy import create_engine, text

from src.core.services.config_manager import get_config

# Test Database Configuration
config = get_config()
TEST_DB_URL = config.get('TEST_DATABASE_URL', 'postgresql://app_readwrite:password@localhost:5432/tickstock_test')
TEST_REDIS_DB = 15  # Use dedicated test Redis database


@pytest.fixture(scope='session')
def redis_client():
    """
    Redis client for integration testing.
    Uses dedicated test database to avoid conflicts.
    """
    client = redis.Redis(
        host='localhost',
        port=6379,
        db=TEST_REDIS_DB,
        decode_responses=True
    )

    # Clean up any existing test data
    client.flushdb()

    yield client

    # Cleanup after all tests
    client.flushdb()
    client.close()


@pytest.fixture(scope='session')
def db_engine():
    """
    Database engine for integration testing.
    Uses test database to avoid production conflicts.
    """
    engine = create_engine(TEST_DB_URL, pool_pre_ping=True)

    # Verify connection
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        assert result.scalar() == 1

    yield engine

    engine.dispose()


@pytest.fixture
def db_connection(db_engine):
    """
    Database connection for individual tests.
    Automatically rolls back transactions.
    """
    connection = db_engine.connect()
    transaction = connection.begin()

    yield connection

    transaction.rollback()
    connection.close()


@pytest.fixture
def redis_pubsub_listener():
    """
    Redis pub-sub listener for integration testing.
    Provides message collection and verification capabilities.
    """
    class PubSubListener:
        def __init__(self, redis_client):
            self.redis_client = redis_client
            self.received_messages = []
            self.pubsub = redis_client.pubsub()
            self.listener_thread = None
            self.listening = False

        def subscribe(self, channels: list[str]):
            """Subscribe to multiple Redis channels"""
            for channel in channels:
                self.pubsub.subscribe(channel)

        def start_listening(self):
            """Start background listener thread"""
            self.listening = True
            self.listener_thread = threading.Thread(
                target=self._listen_loop,
                daemon=True
            )
            self.listener_thread.start()

        def stop_listening(self):
            """Stop listener and cleanup"""
            self.listening = False
            if self.listener_thread:
                self.listener_thread.join(timeout=1.0)
            self.pubsub.close()

        def _listen_loop(self):
            """Background message listening loop"""
            try:
                for message in self.pubsub.listen():
                    if not self.listening:
                        break
                    if message['type'] == 'message':
                        self.received_messages.append({
                            'channel': message['channel'],
                            'data': message['data'],
                            'timestamp': time.time(),
                            'parsed_data': self._try_parse_json(message['data'])
                        })
            except Exception as e:
                print(f"PubSub listener error: {e}")

        def _try_parse_json(self, data):
            """Attempt to parse message data as JSON"""
            try:
                return json.loads(data)
            except (json.JSONDecodeError, TypeError):
                return data

        def get_messages(self, channel: str = None) -> list[dict]:
            """Get received messages, optionally filtered by channel"""
            if channel:
                return [msg for msg in self.received_messages if msg['channel'] == channel]
            return self.received_messages.copy()

        def wait_for_message(self, channel: str, timeout: float = 5.0) -> dict | None:
            """Wait for specific message on channel with timeout"""
            start_time = time.time()
            while time.time() - start_time < timeout:
                messages = self.get_messages(channel)
                if messages:
                    return messages[-1]  # Return most recent
                time.sleep(0.01)
            return None

        def clear_messages(self):
            """Clear message history"""
            self.received_messages.clear()

    return PubSubListener


@pytest.fixture
def mock_tickstockpl_producer():
    """
    Mock TickStockPL producer for integration testing.
    Simulates TickStockPL publishing events and consuming jobs.
    """
    class MockTickStockPLProducer:
        def __init__(self, redis_client):
            self.redis = redis_client

        def publish_pattern_event(self, pattern_data: dict):
            """Simulate TickStockPL publishing pattern detection event"""
            event = {
                'event_type': 'pattern_detected',
                'timestamp': time.time(),
                'source': 'tickstock_pl',
                **pattern_data
            }
            message = json.dumps(event)
            self.redis.publish('tickstock.events.patterns', message)

        def publish_backtest_progress(self, job_id: str, progress: float, status: str):
            """Simulate TickStockPL publishing backtest progress"""
            progress_data = {
                'job_id': job_id,
                'progress': progress,
                'status': status,
                'timestamp': time.time(),
                'source': 'tickstock_pl'
            }
            message = json.dumps(progress_data)
            self.redis.publish('tickstock.events.backtesting.progress', message)

        def publish_backtest_results(self, job_id: str, results: dict):
            """Simulate TickStockPL publishing backtest completion"""
            result_data = {
                'job_id': job_id,
                'results': results,
                'completed_at': time.time(),
                'source': 'tickstock_pl'
            }
            message = json.dumps(result_data)
            self.redis.publish('tickstock.events.backtesting.results', message)

        def publish_ipo_detection(self, symbol: str, listing_data: dict):
            """Simulate TickStockPL IPO detection notification"""
            ipo_event = {
                'event_type': 'ipo_detected',
                'symbol': symbol,
                'listing_date': listing_data.get('listing_date'),
                'market_cap': listing_data.get('market_cap'),
                'sector': listing_data.get('sector'),
                'timestamp': time.time(),
                'source': 'tickstock_pl'
            }
            message = json.dumps(ipo_event)
            self.redis.publish('tickstock.events.symbols.ipo_detected', message)

        def publish_etf_data_update(self, etf_symbol: str, update_data: dict):
            """Simulate TickStockPL ETF data update notification"""
            etf_event = {
                'event_type': 'etf_data_updated',
                'symbol': etf_symbol,
                'aum_millions': update_data.get('aum_millions'),
                'expense_ratio': update_data.get('expense_ratio'),
                'underlying_index': update_data.get('underlying_index'),
                'timestamp': time.time(),
                'source': 'tickstock_pl'
            }
            message = json.dumps(etf_event)
            self.redis.publish('tickstock.events.symbols.etf_updated', message)

        def publish_eod_completion(self, processing_summary: dict):
            """Simulate TickStockPL EOD processing completion"""
            eod_event = {
                'event_type': 'eod_processing_complete',
                'symbols_processed': processing_summary.get('symbols_processed', 0),
                'success_rate': processing_summary.get('success_rate', 0.0),
                'failed_symbols': processing_summary.get('failed_symbols', []),
                'processing_time_seconds': processing_summary.get('processing_time_seconds', 0),
                'timestamp': time.time(),
                'source': 'tickstock_pl'
            }
            message = json.dumps(eod_event)
            self.redis.publish('tickstock.events.data.eod_complete', message)

        def publish_data_quality_alert(self, alert_data: dict):
            """Simulate TickStockPL data quality alert"""
            alert_event = {
                'event_type': 'data_quality_alert',
                'alert_type': alert_data.get('alert_type', 'anomaly'),
                'symbol': alert_data.get('symbol'),
                'severity': alert_data.get('severity', 'medium'),
                'description': alert_data.get('description', ''),
                'timestamp': time.time(),
                'source': 'tickstock_pl'
            }
            message = json.dumps(alert_event)
            self.redis.publish('tickstock.events.data.quality_alert', message)

    return MockTickStockPLProducer


@pytest.fixture
def mock_tickstockapp_consumer():
    """
    Mock TickStockApp consumer for integration testing.
    Simulates TickStockApp job submissions and event consumption.
    """
    class MockTickStockAppConsumer:
        def __init__(self, redis_client):
            self.redis = redis_client

        def submit_backtest_job(self, job_data: dict) -> str:
            """Simulate TickStockApp submitting backtest job"""
            job_id = f"job_{int(time.time() * 1000)}"
            job_request = {
                'job_type': 'backtest',
                'job_id': job_id,
                'timestamp': time.time(),
                'source': 'tickstock_app',
                **job_data
            }
            message = json.dumps(job_request)
            self.redis.publish('tickstock.jobs.backtest', message)
            return job_id

        def submit_alert_subscription(self, subscription_data: dict):
            """Simulate TickStockApp alert subscription"""
            subscription = {
                'subscription_type': 'pattern_alert',
                'timestamp': time.time(),
                'source': 'tickstock_app',
                **subscription_data
            }
            message = json.dumps(subscription)
            self.redis.publish('tickstock.jobs.alerts', message)

        def submit_data_request(self, request_data: dict):
            """Simulate TickStockApp data request"""
            request = {
                'request_type': 'historical_data',
                'timestamp': time.time(),
                'source': 'tickstock_app',
                **request_data
            }
            message = json.dumps(request)
            self.redis.publish('tickstock.jobs.data_request', message)

    return MockTickStockAppConsumer


@pytest.fixture
def integration_performance_monitor():
    """
    Performance monitoring fixture for integration tests.
    Tracks message delivery times and system responsiveness.
    """
    class PerformanceMonitor:
        def __init__(self):
            self.measurements = []

        @contextmanager
        def measure_operation(self, operation_name: str):
            """Context manager for measuring operation performance"""
            start_time = time.time()
            yield
            end_time = time.time()

            duration_ms = (end_time - start_time) * 1000
            self.measurements.append({
                'operation': operation_name,
                'duration_ms': duration_ms,
                'timestamp': start_time
            })

        def get_measurements(self, operation: str = None) -> list[dict]:
            """Get performance measurements, optionally filtered"""
            if operation:
                return [m for m in self.measurements if m['operation'] == operation]
            return self.measurements.copy()

        def assert_performance_target(self, operation: str, max_duration_ms: float):
            """Assert that operation meets performance target"""
            measurements = self.get_measurements(operation)
            if not measurements:
                pytest.fail(f"No measurements found for operation: {operation}")

            avg_duration = sum(m['duration_ms'] for m in measurements) / len(measurements)
            max_duration = max(m['duration_ms'] for m in measurements)

            assert avg_duration < max_duration_ms, (
                f"Average {operation} duration {avg_duration:.2f}ms exceeds "
                f"target {max_duration_ms}ms"
            )

            assert max_duration < max_duration_ms * 2, (
                f"Max {operation} duration {max_duration:.2f}ms exceeds "
                f"reasonable bounds ({max_duration_ms * 2}ms)"
            )

        def clear_measurements(self):
            """Clear measurement history"""
            self.measurements.clear()

    return PerformanceMonitor


@pytest.fixture
def sprint14_test_data():
    """
    Test data factory for Sprint 14 integration scenarios.
    """
    class TestDataFactory:
        @staticmethod
        def etf_symbol_data():
            return {
                'symbol': 'TEST_ETF',
                'name': 'Test ETF Fund',
                'etf_type': 'equity',
                'aum_millions': 1000.5,
                'expense_ratio': 0.0075,
                'underlying_index': 'S&P 500',
                'correlation_reference': 'SPY'
            }

        @staticmethod
        def ipo_listing_data():
            return {
                'symbol': 'NEWIPO',
                'name': 'New IPO Company',
                'listing_date': '2024-01-15',
                'market_cap': 5000.0,
                'sector': 'Technology',
                'exchange': 'NASDAQ'
            }

        @staticmethod
        def backtest_job_data():
            return {
                'user_id': 'test_user_123',
                'symbols': ['AAPL', 'MSFT', 'GOOGL'],
                'start_date': '2024-01-01',
                'end_date': '2024-03-31',
                'patterns': ['Doji', 'Hammer', 'Engulfing'],
                'strategy_params': {
                    'confidence_threshold': 0.8,
                    'position_size': 0.02,
                    'stop_loss': 0.05
                }
            }

        @staticmethod
        def pattern_detection_data():
            return {
                'symbol': 'AAPL',
                'pattern': 'Doji',
                'confidence': 0.85,
                'timeframe': '1D',
                'price': 150.25,
                'volume': 50000000,
                'market_context': 'uptrend'
            }

        @staticmethod
        def data_quality_alert():
            return {
                'symbol': 'TSLA',
                'alert_type': 'price_anomaly',
                'severity': 'high',
                'description': 'Price gap >10% without news catalyst',
                'current_price': 250.00,
                'previous_price': 220.00,
                'gap_percentage': 13.6
            }

    return TestDataFactory


# Integration Test Categories
SPRINT14_INTEGRATION_CATEGORIES = {
    'phase1': ['etf_integration', 'eod_processing', 'historical_loading'],
    'phase2': ['ipo_monitoring', 'data_quality', 'equity_types'],
    'phase3': ['cache_sync', 'universe_management', 'test_scenarios'],
    'phase4': ['enterprise_scheduling', 'dev_refresh', 'market_calendar']
}

# Redis Channel Mapping for Sprint 14
SPRINT14_REDIS_CHANNELS = {
    'events': {
        'patterns': 'tickstock.events.patterns',
        'backtesting_progress': 'tickstock.events.backtesting.progress',
        'backtesting_results': 'tickstock.events.backtesting.results',
        'ipo_detected': 'tickstock.events.symbols.ipo_detected',
        'etf_updated': 'tickstock.events.symbols.etf_updated',
        'eod_complete': 'tickstock.events.data.eod_complete',
        'quality_alert': 'tickstock.events.data.quality_alert'
    },
    'jobs': {
        'backtest': 'tickstock.jobs.backtest',
        'alerts': 'tickstock.jobs.alerts',
        'data_request': 'tickstock.jobs.data_request',
        'historical_load': 'tickstock.jobs.historical_load'
    }
}

# Performance Targets for Sprint 14
PERFORMANCE_TARGETS = {
    'message_delivery_ms': 100,
    'database_query_ms': 50,
    'redis_response_ms': 10,
    'websocket_broadcast_ms': 50,
    'end_to_end_workflow_ms': 500
}
