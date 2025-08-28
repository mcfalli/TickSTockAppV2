"""
Sprint 10 Phase 1 Test Fixtures and Configuration
Provides comprehensive mock fixtures for database scenarios and Redis connection states.

Test Fixtures:
- Database connection mocks (healthy, degraded, error states)
- Redis connection mocks (available, unavailable, slow response)
- TickStockPL connectivity mocks (active, inactive, partial)
- Performance monitoring utilities
- Realistic test data generators
"""

import pytest
import time
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import redis
from flask import Flask
from flask_login import LoginManager

# Import the classes we're testing
from src.infrastructure.database.tickstock_db import TickStockDatabase
from src.core.services.health_monitor import HealthMonitor, HealthStatus
from src.api.rest.tickstockpl_api import register_tickstockpl_routes


@pytest.fixture
def performance_timer():
    """Utility fixture for measuring test execution time."""
    class PerformanceTimer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
            self.elapsed = None
            
        def start(self):
            self.start_time = time.time()
            
        def stop(self):
            self.end_time = time.time()
            if self.start_time:
                self.elapsed = self.end_time - self.start_time
            
        def elapsed_ms(self):
            return (self.elapsed * 1000) if self.elapsed else None
    
    return PerformanceTimer()


# Database Fixtures

@pytest.fixture
def mock_healthy_database():
    """Mock TickStockDatabase in healthy state with fast responses."""
    db = TickStockDatabase.__new__(TickStockDatabase)
    db.config = {}
    db.engine = Mock()
    
    # Mock connection context manager
    mock_connection = Mock()
    db.engine.connect.return_value.__enter__ = Mock(return_value=mock_connection)
    db.engine.connect.return_value.__exit__ = Mock(return_value=None)
    
    # Mock healthy query responses
    mock_connection.execute.return_value = Mock()
    
    # Mock engine pool for health checks
    db.engine.pool = Mock()
    db.engine.pool.status.return_value = "Pool: size=5 checked_in=3 checked_out=2 invalid=0"
    db.engine.pool.size.return_value = 5
    db.engine.pool.checkedin.return_value = 3
    db.engine.pool.checkedout.return_value = 2
    db.engine.pool.invalid.return_value = 0
    
    return db


@pytest.fixture
def mock_degraded_database():
    """Mock TickStockDatabase in degraded state with slow responses."""
    db = TickStockDatabase.__new__(TickStockDatabase)
    db.config = {}
    db.engine = Mock()
    
    # Mock slow connection
    mock_connection = Mock()
    
    def slow_execute(*args, **kwargs):
        time.sleep(0.120)  # 120ms - degraded performance
        result = Mock()
        result.scalar.return_value = 1000
        result.__iter__ = Mock(return_value=iter([('SLOW_SYMBOL',)]))
        return result
    
    mock_connection.execute = slow_execute
    db.engine.connect.return_value.__enter__ = Mock(return_value=mock_connection)
    db.engine.connect.return_value.__exit__ = Mock(return_value=None)
    
    # Mock degraded pool status
    db.engine.pool = Mock()
    db.engine.pool.status.return_value = "Pool: size=5 checked_in=1 checked_out=4 invalid=0"
    db.engine.pool.size.return_value = 5
    db.engine.pool.checkedin.return_value = 1
    db.engine.pool.checkedout.return_value = 4
    db.engine.pool.invalid.return_value = 0
    
    return db


@pytest.fixture
def mock_error_database():
    """Mock TickStockDatabase in error state with connection failures."""
    db = TickStockDatabase.__new__(TickStockDatabase)
    db.config = {}
    db.engine = None  # Simulate uninitialized engine
    
    return db


@pytest.fixture
def mock_database_with_realistic_data():
    """Mock database with realistic TickStock data."""
    db = TickStockDatabase.__new__(TickStockDatabase)
    db.config = {}
    db.engine = Mock()
    
    # Generate realistic symbols (4000 symbols like production)
    symbols_data = []
    major_symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN', 'META', 'NVDA', 'AMD']
    
    # Add major symbols
    symbols_data.extend([(symbol,) for symbol in major_symbols])
    
    # Add generated symbols
    for i in range(3992):
        symbols_data.append((f'SYM{i:04d}',))
    
    # Mock connection with realistic query responses
    mock_connection = Mock()
    
    def realistic_execute(query, *args, **kwargs):
        query_str = str(query)
        
        if "DISTINCT symbol FROM symbols" in query_str:
            # Symbols query
            result = Mock()
            result.__iter__ = Mock(return_value=iter(symbols_data))
            return result
            
        elif "COUNT(*) FROM symbols" in query_str:
            # Symbols count
            result = Mock()
            result.scalar.return_value = len(symbols_data)
            return result
            
        elif "COUNT(*) FROM events" in query_str:
            # Events count
            result = Mock()
            result.scalar.return_value = 25000
            return result
            
        elif "MAX(created_at) FROM events" in query_str:
            # Latest event time
            result = Mock()
            result.scalar.return_value = datetime.now() - timedelta(minutes=5)
            return result
            
        elif "FROM events WHERE user_id" in query_str:
            # User alerts
            test_alerts = []
            for i in range(10):
                test_time = datetime.now() - timedelta(hours=i)
                test_alerts.append((
                    major_symbols[i % len(major_symbols)],
                    'high_low' if i % 2 == 0 else 'trend',
                    0.75 + (i % 25) * 0.01,
                    test_time,
                    {'price': 150.0 + i}
                ))
            
            result = Mock()
            result.__iter__ = Mock(return_value=iter(test_alerts))
            return result
            
        elif "GROUP BY pattern" in query_str:
            # Pattern performance
            patterns_data = [
                ('high_low', 5000, 0.78, 0.95, 0.45),
                ('trend', 3000, 0.82, 0.98, 0.52),
                ('surge', 2000, 0.75, 0.92, 0.48),
                ('breakout', 1500, 0.80, 0.94, 0.50)
            ]
            result = Mock()
            result.__iter__ = Mock(return_value=iter(patterns_data))
            return result
            
        elif "table_name FROM information_schema.tables" in query_str:
            # Health check tables
            tables_data = [('symbols',), ('events',), ('ohlcv_daily',), ('ohlcv_1min',), ('ticks',)]
            result = Mock()
            result.__iter__ = Mock(return_value=iter(tables_data))
            return result
            
        else:
            # Default response
            result = Mock()
            result.scalar.return_value = 1
            return result
    
    mock_connection.execute = realistic_execute
    db.engine.connect.return_value.__enter__ = Mock(return_value=mock_connection)
    db.engine.connect.return_value.__exit__ = Mock(return_value=None)
    
    # Mock healthy pool
    db.engine.pool = Mock()
    db.engine.pool.status.return_value = "Pool: healthy"
    db.engine.pool.size.return_value = 5
    db.engine.pool.checkedin.return_value = 3
    db.engine.pool.checkedout.return_value = 2
    db.engine.pool.invalid.return_value = 0
    
    return db


# Redis Fixtures

@pytest.fixture
def mock_healthy_redis():
    """Mock Redis client in healthy state with fast responses."""
    redis_mock = Mock(spec=redis.Redis)
    
    # Mock successful Redis operations
    redis_mock.ping.return_value = True
    redis_mock.set.return_value = True
    redis_mock.get.return_value = 'test_value'
    redis_mock.delete.return_value = 1
    redis_mock.info.return_value = {
        'connected_clients': 5,
        'used_memory_human': '1.2M',
        'redis_version': '6.2.0',
        'uptime_in_seconds': 86400,
        'total_connections_received': 1000,
        'instantaneous_ops_per_sec': 50
    }
    
    # Mock pubsub for TickStockPL connectivity
    redis_mock.pubsub_numsub.side_effect = [
        [('tickstock.events.patterns', 2)],
        [('tickstock.events.backtesting.progress', 1)],
        [('tickstock.events.backtesting.results', 1)]
    ]
    redis_mock.publish.return_value = 1
    
    return redis_mock


@pytest.fixture
def mock_degraded_redis():
    """Mock Redis client in degraded state with slow responses."""
    redis_mock = Mock(spec=redis.Redis)
    
    # Mock slow but successful operations
    def slow_ping():
        time.sleep(0.060)  # 60ms - degraded performance
        return True
    
    def slow_set(key, value, **kwargs):
        time.sleep(0.055)
        return True
    
    def slow_get(key):
        time.sleep(0.050)
        return 'test_value'
    
    redis_mock.ping = slow_ping
    redis_mock.set = slow_set
    redis_mock.get = slow_get
    redis_mock.delete.return_value = 1
    redis_mock.info.return_value = {
        'connected_clients': 20,  # High client count
        'used_memory_human': '512M',  # High memory usage
        'redis_version': '6.2.0',
        'uptime_in_seconds': 86400
    }
    
    # Mock reduced TickStockPL connectivity
    redis_mock.pubsub_numsub.side_effect = [
        [('tickstock.events.patterns', 1)],  # Reduced subscribers
        [('tickstock.events.backtesting.progress', 0)],
        [('tickstock.events.backtesting.results', 0)]
    ]
    redis_mock.publish.return_value = 1
    
    return redis_mock


@pytest.fixture
def mock_error_redis():
    """Mock Redis client in error state with connection failures."""
    redis_mock = Mock(spec=redis.Redis)
    
    # Mock Redis connection errors
    redis_mock.ping.side_effect = redis.ConnectionError("Connection refused")
    redis_mock.set.side_effect = redis.ConnectionError("Connection refused")
    redis_mock.get.side_effect = redis.ConnectionError("Connection refused")
    redis_mock.delete.side_effect = redis.ConnectionError("Connection refused")
    redis_mock.info.side_effect = redis.ConnectionError("Connection refused")
    redis_mock.pubsub_numsub.side_effect = redis.ConnectionError("Connection refused")
    redis_mock.publish.side_effect = redis.ConnectionError("Connection refused")
    
    return redis_mock


@pytest.fixture
def mock_unavailable_redis():
    """Mock scenario where Redis client is not configured/available."""
    return None


# TickStockPL Connectivity Fixtures

@pytest.fixture
def mock_active_tickstockpl(mock_healthy_redis):
    """Mock active TickStockPL connectivity with all services running."""
    redis_mock = mock_healthy_redis
    
    # Mock active subscribers on all TickStockPL channels
    redis_mock.pubsub_numsub.side_effect = [
        [('tickstock.events.patterns', 3)],
        [('tickstock.events.backtesting.progress', 2)],
        [('tickstock.events.backtesting.results', 2)]
    ]
    
    return redis_mock


@pytest.fixture
def mock_inactive_tickstockpl(mock_healthy_redis):
    """Mock inactive TickStockPL connectivity with no services running."""
    redis_mock = mock_healthy_redis
    
    # Mock no subscribers on TickStockPL channels
    redis_mock.pubsub_numsub.side_effect = [
        [('tickstock.events.patterns', 0)],
        [('tickstock.events.backtesting.progress', 0)],
        [('tickstock.events.backtesting.results', 0)]
    ]
    
    return redis_mock


@pytest.fixture
def mock_partial_tickstockpl(mock_healthy_redis):
    """Mock partial TickStockPL connectivity with some services running."""
    redis_mock = mock_healthy_redis
    
    # Mock partial subscribers on TickStockPL channels
    redis_mock.pubsub_numsub.side_effect = [
        [('tickstock.events.patterns', 2)],  # Active
        [('tickstock.events.backtesting.progress', 0)],  # Inactive
        [('tickstock.events.backtesting.results', 1)]  # Partially active
    ]
    
    return redis_mock


# HealthMonitor Fixtures

@pytest.fixture
def health_monitor_healthy(mock_healthy_database, mock_healthy_redis):
    """HealthMonitor with all components healthy."""
    config = {}
    
    with patch('src.core.services.health_monitor.TickStockDatabase') as mock_db_class:
        mock_db_class.return_value = mock_healthy_database
        
        monitor = HealthMonitor(config, redis_client=mock_healthy_redis)
        monitor.tickstock_db = mock_healthy_database
        
        return monitor


@pytest.fixture
def health_monitor_degraded(mock_degraded_database, mock_degraded_redis):
    """HealthMonitor with degraded components."""
    config = {}
    
    with patch('src.core.services.health_monitor.TickStockDatabase') as mock_db_class:
        mock_db_class.return_value = mock_degraded_database
        
        monitor = HealthMonitor(config, redis_client=mock_degraded_redis)
        monitor.tickstock_db = mock_degraded_database
        
        return monitor


@pytest.fixture
def health_monitor_error(mock_error_database, mock_error_redis):
    """HealthMonitor with error components."""
    config = {}
    
    monitor = HealthMonitor.__new__(HealthMonitor)
    monitor.config = config
    monitor.redis_client = mock_error_redis
    monitor.tickstock_db = mock_error_database
    
    return monitor


# Flask App Fixtures

@pytest.fixture
def flask_app_with_auth():
    """Flask application with authentication configured for API testing."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key-sprint10'
    
    # Configure Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    
    @login_manager.user_loader
    def load_user(user_id):
        user = Mock()
        user.id = user_id
        user.is_authenticated = True
        user.is_active = True
        user.is_anonymous = False
        user.get_id = Mock(return_value=str(user_id))
        return user
    
    return app


@pytest.fixture
def api_with_healthy_services(flask_app_with_auth, mock_healthy_database, mock_healthy_redis):
    """Flask app with TickStockPL API and healthy services."""
    app = flask_app_with_auth
    
    extensions = {}
    cache_control = Mock()
    config = {'redis_client': mock_healthy_redis}
    
    with patch('src.api.rest.tickstockpl_api.HealthMonitor') as mock_health_monitor:
        with patch('src.api.rest.tickstockpl_api.TickStockDatabase') as mock_db:
            # Configure healthy services
            mock_health_instance = Mock()
            mock_health_instance.get_overall_health.return_value = {
                'timestamp': time.time(),
                'overall_status': 'healthy',
                'components': {
                    'database': HealthStatus(status='healthy', response_time_ms=25.0),
                    'redis': HealthStatus(status='healthy', response_time_ms=15.0),
                    'tickstockpl_connectivity': HealthStatus(status='healthy', response_time_ms=30.0)
                },
                'summary': {'healthy': 3, 'degraded': 0, 'error': 0, 'unknown': 0}
            }
            mock_health_instance.get_dashboard_data.return_value = {
                'health': {'overall_status': 'healthy'},
                'quick_stats': {'symbols_count': 4000, 'events_count': 25000},
                'alerts': []
            }
            
            mock_db_instance = mock_healthy_database
            mock_db_instance.get_symbols_for_dropdown.return_value = ['AAPL', 'GOOGL', 'MSFT', 'TSLA'] + [f'SYM{i:04d}' for i in range(3996)]
            mock_db_instance.get_basic_dashboard_stats.return_value = {
                'symbols_count': 4000,
                'events_count': 25000,
                'latest_event_time': '2025-01-15T10:30:00',
                'database_status': 'connected'
            }
            mock_db_instance.get_user_alert_history.return_value = []
            mock_db_instance.get_pattern_performance.return_value = []
            
            mock_health_monitor.return_value = mock_health_instance
            mock_db.return_value = mock_db_instance
            
            register_tickstockpl_routes(app, extensions, cache_control, config)
            
            return app


@pytest.fixture
def api_with_degraded_services(flask_app_with_auth, mock_degraded_database, mock_degraded_redis):
    """Flask app with TickStockPL API and degraded services."""
    app = flask_app_with_auth
    
    extensions = {}
    cache_control = Mock()
    config = {'redis_client': mock_degraded_redis}
    
    with patch('src.api.rest.tickstockpl_api.HealthMonitor') as mock_health_monitor:
        with patch('src.api.rest.tickstockpl_api.TickStockDatabase') as mock_db:
            # Configure degraded services
            mock_health_instance = Mock()
            mock_health_instance.get_overall_health.return_value = {
                'timestamp': time.time(),
                'overall_status': 'degraded',
                'components': {
                    'database': HealthStatus(status='degraded', response_time_ms=125.0),
                    'redis': HealthStatus(status='degraded', response_time_ms=65.0),
                    'tickstockpl_connectivity': HealthStatus(status='unknown', response_time_ms=45.0)
                },
                'summary': {'healthy': 0, 'degraded': 2, 'error': 0, 'unknown': 1}
            }
            
            mock_db_instance = mock_degraded_database
            mock_health_monitor.return_value = mock_health_instance
            mock_db.return_value = mock_db_instance
            
            register_tickstockpl_routes(app, extensions, cache_control, config)
            
            return app


@pytest.fixture
def api_with_error_services(flask_app_with_auth):
    """Flask app with TickStockPL API and error services."""
    app = flask_app_with_auth
    
    extensions = {}
    cache_control = Mock()
    config = {}
    
    with patch('src.api.rest.tickstockpl_api.HealthMonitor') as mock_health_monitor:
        with patch('src.api.rest.tickstockpl_api.TickStockDatabase') as mock_db:
            # Simulate service initialization failures
            mock_health_monitor.side_effect = Exception("Health monitor initialization failed")
            mock_db.side_effect = Exception("Database initialization failed")
            
            register_tickstockpl_routes(app, extensions, cache_control, config)
            
            return app


# Utility Fixtures

@pytest.fixture
def authenticated_user_context():
    """Context manager for authenticated user in Flask tests."""
    class AuthContext:
        def __init__(self):
            self.user_id = '123'
            self.user = Mock()
            self.user.id = self.user_id
            self.user.is_authenticated = True
            self.user.is_active = True
            self.user.is_anonymous = False
            self.user.get_id = Mock(return_value=self.user_id)
        
        def apply_to_session(self, session):
            """Apply authentication to Flask test session."""
            session['_user_id'] = self.user_id
            session['_fresh'] = True
            return session
            
        def mock_current_user(self):
            """Return mock for flask_login.current_user."""
            return patch('flask_login.utils._get_user', return_value=self.user)
    
    return AuthContext()


@pytest.fixture
def test_data_generator():
    """Generate realistic test data for TickStock scenarios."""
    class TestDataGenerator:
        
        def generate_symbols(self, count=4000):
            """Generate realistic stock symbols."""
            major_symbols = [
                'AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN', 'META', 'NVDA', 'AMD',
                'SPY', 'QQQ', 'IWM', 'GLD', 'BTCUSD', 'ETHUSD', 'ADBE', 'CRM',
                'NFLX', 'TWTR', 'UBER', 'LYFT', 'SNAP', 'SQ', 'PYPL', 'ZM'
            ]
            
            symbols = major_symbols.copy()
            
            # Generate additional symbols
            for i in range(count - len(major_symbols)):
                symbols.append(f'SYM{i:04d}')
            
            return symbols[:count]
        
        def generate_alerts(self, user_id, count=50):
            """Generate realistic user alerts."""
            symbols = self.generate_symbols(20)
            patterns = ['high_low', 'trend', 'surge', 'breakout']
            alerts = []
            
            for i in range(count):
                alert_time = datetime.now() - timedelta(hours=i, minutes=i*2)
                alerts.append({
                    'symbol': symbols[i % len(symbols)],
                    'pattern': patterns[i % len(patterns)],
                    'confidence': 0.6 + (i % 40) * 0.01,  # 0.6 to 1.0
                    'created_at': alert_time.isoformat(),
                    'metadata': {
                        'price': 100.0 + i * 0.5,
                        'volume': 1000 + i * 10
                    }
                })
            
            return alerts
        
        def generate_pattern_performance(self):
            """Generate realistic pattern performance data."""
            return [
                {
                    'pattern': 'high_low',
                    'detection_count': 5000,
                    'avg_confidence': 0.78,
                    'max_confidence': 0.95,
                    'min_confidence': 0.45
                },
                {
                    'pattern': 'trend',
                    'detection_count': 3000,
                    'avg_confidence': 0.82,
                    'max_confidence': 0.98,
                    'min_confidence': 0.52
                },
                {
                    'pattern': 'surge', 
                    'detection_count': 2000,
                    'avg_confidence': 0.75,
                    'max_confidence': 0.92,
                    'min_confidence': 0.48
                },
                {
                    'pattern': 'breakout',
                    'detection_count': 1500,
                    'avg_confidence': 0.80,
                    'max_confidence': 0.94,
                    'min_confidence': 0.50
                }
            ]
    
    return TestDataGenerator()


# Performance Testing Utilities

@pytest.fixture
def performance_benchmarks():
    """Define performance benchmarks for Sprint 10."""
    return {
        'database_query_max_ms': 50.0,
        'health_check_max_ms': 100.0,
        'api_endpoint_max_ms': 100.0,
        'redis_operation_max_ms': 50.0,
        'dashboard_refresh_max_ms': 200.0,
        'user_session_max_ms': 300.0
    }


# Cleanup Fixtures

@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Automatic cleanup after each test."""
    yield
    # Any cleanup code here would run after each test
    # This is useful for ensuring no test pollution