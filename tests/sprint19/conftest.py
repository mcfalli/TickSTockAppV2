"""
Sprint 19 Phase 1 Test Configuration and Fixtures
Shared fixtures and utilities for Pattern Discovery API component testing.

Focus Areas:
- RedisPatternCache testing with mock Redis
- Pattern Consumer API endpoint testing
- User Universe API testing with database mocks
- Pattern Discovery Service integration testing
- Performance benchmarking fixtures for <50ms targets
"""

import threading
import time
from unittest.mock import Mock

import pytest
from fakeredis import FakeRedis
from flask import Flask

# Import Sprint 19 components
try:
    from src.api.rest.pattern_consumer import pattern_consumer_bp
    from src.api.rest.user_universe import user_universe_bp
    from src.core.services.pattern_discovery_service import PatternDiscoveryService
    from src.infrastructure.cache.redis_pattern_cache import (
        CachedPattern,
        PatternCacheEventType,
        PatternCacheStats,
        RedisPatternCache,
    )
except ImportError as e:
    pytest.skip(f"Sprint 19 components not available: {e}", allow_module_level=True)

# ==========================================================================
# SPRINT 19 TEST CONFIGURATION
# ==========================================================================

@pytest.fixture(scope="session")
def sprint19_config():
    """Sprint 19 test configuration."""
    return {
        'redis_host': 'localhost',
        'redis_port': 6379,
        'redis_db': 1,  # Use test database
        'redis_max_connections': 5,
        'pattern_cache_ttl': 1800,  # 30 minutes for testing
        'api_response_cache_ttl': 15,  # 15 seconds for testing
        'index_cache_ttl': 900,  # 15 minutes for testing
        'database_host': 'localhost',
        'database_port': 5432,
        'database_name': 'tickstock_test',
        'database_user': 'test_user',
        'database_password': 'test_password',
        'performance_target_ms': 50,
        'cache_hit_ratio_target': 0.70
    }

# ==========================================================================
# REDIS AND CACHE FIXTURES
# ==========================================================================

@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    fake_redis = FakeRedis(decode_responses=True)
    return fake_redis

@pytest.fixture
def pattern_cache_config():
    """Configuration for pattern cache testing."""
    return {
        'pattern_cache_ttl': 3600,
        'api_response_cache_ttl': 30,
        'index_cache_ttl': 3600
    }

@pytest.fixture
def redis_pattern_cache(mock_redis, pattern_cache_config):
    """RedisPatternCache instance for testing."""
    cache = RedisPatternCache(mock_redis, pattern_cache_config)
    return cache

@pytest.fixture
def sample_pattern_data():
    """Sample pattern detection data for testing."""
    return {
        'symbol': 'AAPL',
        'pattern': 'Weekly_Breakout',
        'confidence': 0.85,
        'current_price': 150.25,
        'price_change': 2.3,
        'timestamp': time.time(),
        'expires_at': time.time() + 3600,
        'indicators': {
            'relative_strength': 1.4,
            'relative_volume': 2.1,
            'rsi': 65.5,
            'sma_20': 148.50,
            'sma_50': 145.00
        },
        'source': 'daily'
    }

@pytest.fixture
def sample_pattern_event(sample_pattern_data):
    """Sample pattern event for testing."""
    return {
        'event_type': 'pattern_detected',
        'data': sample_pattern_data
    }

@pytest.fixture
def multiple_pattern_events():
    """Multiple pattern events for bulk testing."""
    patterns = []
    symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'NVDA']
    pattern_types = ['Weekly_Breakout', 'Bull_Flag', 'Volume_Spike', 'Support_Test', 'Momentum_Shift']

    for i in range(20):
        symbol = symbols[i % len(symbols)]
        pattern_type = pattern_types[i % len(pattern_types)]

        pattern_data = {
            'symbol': symbol,
            'pattern': pattern_type,
            'confidence': 0.6 + (i % 4) * 0.1,  # Vary confidence
            'current_price': 100 + i * 5,
            'price_change': -2 + i * 0.2,
            'timestamp': time.time() - i * 60,  # Spread over time
            'expires_at': time.time() + 3600 - i * 60,
            'indicators': {
                'relative_strength': 0.8 + i * 0.05,
                'relative_volume': 1.0 + i * 0.1,
                'rsi': 40 + i * 2
            },
            'source': 'daily' if i % 2 == 0 else 'intraday'
        }

        patterns.append({
            'event_type': 'pattern_detected',
            'data': pattern_data
        })

    return patterns

# ==========================================================================
# FLASK APPLICATION FIXTURES
# ==========================================================================

@pytest.fixture
def app():
    """Flask application for testing Sprint 19 APIs."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False

    # Register Sprint 19 blueprints
    app.register_blueprint(pattern_consumer_bp)
    app.register_blueprint(user_universe_bp)

    return app

@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()

@pytest.fixture
def app_with_mocks(app, redis_pattern_cache, mock_tickstock_db, mock_cache_control):
    """Flask app with mocked dependencies."""
    app.pattern_cache = redis_pattern_cache
    app.tickstock_db = mock_tickstock_db
    app.cache_control = mock_cache_control
    return app

# ==========================================================================
# DATABASE FIXTURES
# ==========================================================================

@pytest.fixture
def mock_tickstock_db():
    """Mock TickStock database for testing."""
    mock_db = Mock()

    # Mock symbol data
    sample_symbols = [
        {'symbol': 'AAPL', 'name': 'Apple Inc.', 'market': 'stocks', 'sector': 'Technology'},
        {'symbol': 'GOOGL', 'name': 'Alphabet Inc.', 'market': 'stocks', 'sector': 'Technology'},
        {'symbol': 'MSFT', 'name': 'Microsoft Corp.', 'market': 'stocks', 'sector': 'Technology'},
        {'symbol': 'TSLA', 'name': 'Tesla Inc.', 'market': 'stocks', 'sector': 'Automotive'},
        {'symbol': 'NVDA', 'name': 'NVIDIA Corp.', 'market': 'stocks', 'sector': 'Technology'}
    ]

    mock_db.get_symbols_for_dropdown.return_value = sample_symbols
    mock_db.get_symbol_details.return_value = sample_symbols[0]
    mock_db.get_basic_dashboard_stats.return_value = {
        'total_symbols': len(sample_symbols),
        'active_sessions': 5,
        'patterns_detected_today': 42
    }
    mock_db.health_check.return_value = {'status': 'healthy', 'response_time_ms': 12.5}

    return mock_db

@pytest.fixture
def mock_cache_control():
    """Mock cache control service for testing."""
    mock_cache = Mock()
    mock_cache._initialized = True

    # Mock universe data
    mock_universes = {
        'sp500_large': {
            'description': 'S&P 500 Large Cap',
            'criteria': 'Market cap > $10B',
            'count': 150
        },
        'tech_growth': {
            'description': 'Technology Growth Stocks',
            'criteria': 'Tech sector with growth metrics',
            'count': 85
        }
    }

    mock_cache.get_available_universes.return_value = mock_universes
    mock_cache.get_universe_tickers.return_value = ['AAPL', 'GOOGL', 'MSFT']
    mock_cache.get_universe_metadata.return_value = mock_universes['sp500_large']

    return mock_cache

# ==========================================================================
# PERFORMANCE TESTING FIXTURES
# ==========================================================================

@pytest.fixture
def performance_timer():
    """High-resolution performance timer for benchmarking."""
    class PerformanceTimer:
        def __init__(self):
            self.start_time = None
            self.end_time = None

        def start(self):
            self.start_time = time.perf_counter()

        def stop(self):
            self.end_time = time.perf_counter()

        @property
        def elapsed_ms(self):
            if self.start_time and self.end_time:
                return (self.end_time - self.start_time) * 1000
            return None

        @property
        def elapsed_seconds(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None

    return PerformanceTimer()

@pytest.fixture
def performance_benchmark():
    """Performance benchmark utilities."""
    class PerformanceBenchmark:
        def __init__(self, target_ms=50):
            self.target_ms = target_ms
            self.measurements = []

        def measure(self, func, *args, **kwargs):
            """Measure function execution time."""
            start_time = time.perf_counter()
            result = func(*args, **kwargs)
            end_time = time.perf_counter()

            elapsed_ms = (end_time - start_time) * 1000
            self.measurements.append(elapsed_ms)

            return result, elapsed_ms

        def assert_performance(self, elapsed_ms, context=""):
            """Assert that performance meets target."""
            assert elapsed_ms <= self.target_ms, (
                f"Performance target exceeded: {elapsed_ms:.2f}ms > {self.target_ms}ms {context}"
            )

        def get_statistics(self):
            """Get performance statistics."""
            if not self.measurements:
                return None

            return {
                'count': len(self.measurements),
                'min_ms': min(self.measurements),
                'max_ms': max(self.measurements),
                'avg_ms': sum(self.measurements) / len(self.measurements),
                'p95_ms': sorted(self.measurements)[int(len(self.measurements) * 0.95)],
                'p99_ms': sorted(self.measurements)[int(len(self.measurements) * 0.99)],
                'target_ms': self.target_ms,
                'target_met_pct': len([m for m in self.measurements if m <= self.target_ms]) / len(self.measurements) * 100
            }

    return PerformanceBenchmark()

# ==========================================================================
# LOAD TESTING FIXTURES
# ==========================================================================

@pytest.fixture
def concurrent_load_tester():
    """Concurrent load testing utilities."""
    class ConcurrentLoadTester:
        def __init__(self, max_threads=20):
            self.max_threads = max_threads
            self.results = []
            self.errors = []

        def run_concurrent_requests(self, request_func, num_requests=100, max_concurrent=10):
            """Run concurrent requests and measure performance."""
            import queue

            work_queue = queue.Queue()
            result_queue = queue.Queue()

            # Add work items
            for i in range(num_requests):
                work_queue.put(i)

            def worker():
                while not work_queue.empty():
                    try:
                        work_item = work_queue.get(timeout=1)
                        start_time = time.perf_counter()

                        # Execute the request
                        result = request_func()

                        end_time = time.perf_counter()
                        elapsed_ms = (end_time - start_time) * 1000

                        result_queue.put({
                            'work_item': work_item,
                            'elapsed_ms': elapsed_ms,
                            'success': True,
                            'result': result
                        })

                    except queue.Empty:
                        break
                    except Exception as e:
                        result_queue.put({
                            'work_item': work_item,
                            'elapsed_ms': None,
                            'success': False,
                            'error': str(e)
                        })

            # Start worker threads
            threads = []
            for _ in range(min(max_concurrent, num_requests)):
                thread = threading.Thread(target=worker)
                thread.start()
                threads.append(thread)

            # Wait for completion
            for thread in threads:
                thread.join()

            # Collect results
            results = []
            while not result_queue.empty():
                results.append(result_queue.get())

            return results

    return ConcurrentLoadTester()

# ==========================================================================
# PATTERN DISCOVERY SERVICE FIXTURES
# ==========================================================================

@pytest.fixture
def mock_pattern_discovery_service():
    """Mock Pattern Discovery Service for testing."""
    mock_service = Mock()
    mock_service.initialized = True
    mock_service.services_healthy = True

    mock_service.get_health_status.return_value = {
        'status': 'healthy',
        'healthy': True,
        'components': {
            'redis_manager': 'healthy',
            'pattern_cache': 'healthy',
            'tickstock_database': 'healthy',
            'event_subscriber': 'healthy'
        },
        'performance': {
            'runtime_seconds': 300.5,
            'requests_processed': 150,
            'average_response_time_ms': 25.3
        },
        'last_check': time.time()
    }

    return mock_service

# ==========================================================================
# UTILITY FIXTURES
# ==========================================================================

@pytest.fixture
def pattern_data_generator():
    """Utility for generating test pattern data."""
    class PatternDataGenerator:
        def __init__(self):
            self.symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'NVDA', 'AMZN', 'META', 'CRM', 'NFLX', 'AMD']
            self.pattern_types = [
                'Weekly_Breakout', 'Bull_Flag', 'Volume_Spike', 'Support_Test',
                'Momentum_Shift', 'Trendline_Hold', 'Gap_Fill', 'Resistance_Break',
                'Ascending_Triangle', 'Reversal_Signal', 'Doji', 'Hammer', 'Engulfing'
            ]

        def generate_pattern(self, symbol=None, pattern_type=None, confidence=None):
            """Generate a single pattern."""
            import random

            return {
                'symbol': symbol or random.choice(self.symbols),
                'pattern': pattern_type or random.choice(self.pattern_types),
                'confidence': confidence or round(random.uniform(0.5, 0.95), 2),
                'current_price': round(random.uniform(50, 300), 2),
                'price_change': round(random.uniform(-5, 10), 1),
                'timestamp': time.time() - random.randint(0, 3600),
                'expires_at': time.time() + random.randint(1800, 7200),
                'indicators': {
                    'relative_strength': round(random.uniform(0.5, 2.5), 1),
                    'relative_volume': round(random.uniform(0.8, 4.0), 1),
                    'rsi': round(random.uniform(20, 80), 1)
                },
                'source': random.choice(['daily', 'intraday', 'combo'])
            }

        def generate_patterns(self, count=10, **kwargs):
            """Generate multiple patterns."""
            return [self.generate_pattern(**kwargs) for _ in range(count)]

    return PatternDataGenerator()

@pytest.fixture
def api_response_validator():
    """Utility for validating API responses."""
    class APIResponseValidator:
        def validate_pattern_scan_response(self, response):
            """Validate pattern scan API response structure."""
            assert 'patterns' in response
            assert 'pagination' in response
            assert isinstance(response['patterns'], list)

            pagination = response['pagination']
            assert 'page' in pagination
            assert 'per_page' in pagination
            assert 'total' in pagination
            assert 'pages' in pagination

            if response['patterns']:
                pattern = response['patterns'][0]
                required_fields = ['symbol', 'pattern', 'conf', 'price', 'chg', 'time', 'exp', 'source']
                for field in required_fields:
                    assert field in pattern, f"Missing required field: {field}"

        def validate_performance_metrics(self, response, target_ms=50):
            """Validate performance metrics in API response."""
            if 'performance' in response:
                perf = response['performance']
                if 'api_response_time_ms' in perf:
                    assert perf['api_response_time_ms'] <= target_ms, (
                        f"Performance target exceeded: {perf['api_response_time_ms']}ms > {target_ms}ms"
                    )

        def validate_health_response(self, response):
            """Validate health check API response."""
            assert 'status' in response
            assert 'healthy' in response
            assert response['status'] in ['healthy', 'degraded', 'warning', 'error']
            assert isinstance(response['healthy'], bool)

    return APIResponseValidator()

# ==========================================================================
# PYTEST MARKERS AND CONFIGURATION
# ==========================================================================

# Performance test marker
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "performance: mark test as performance benchmark")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "redis: mark test as requiring Redis")
    config.addinivalue_line("markers", "database: mark test as requiring database")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "load: mark test as load/stress test")
