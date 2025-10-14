"""
Sprint 14 Phase 1: Test Configuration and Fixtures
Shared test configuration, fixtures, and utilities for Sprint 14 testing.
"""

import tempfile
from datetime import datetime, timedelta
from typing import Any

import pytest

# Test markers for Sprint 14
pytest.mark.etf = pytest.mark.etf
pytest.mark.eod = pytest.mark.eod
pytest.mark.development = pytest.mark.development
pytest.mark.integration = pytest.mark.integration


@pytest.fixture(scope="session")
def test_database_uri():
    """Test database URI for Sprint 14 tests."""
    return "postgresql://tickstock_test:test_pass@localhost:5432/tickstock_test_sprint14"


@pytest.fixture(scope="session")
def test_redis_config():
    """Test Redis configuration for Sprint 14 tests."""
    return {
        'host': 'localhost',
        'port': 6380,  # Different port for testing
        'db': 15,      # Test database
        'decode_responses': True
    }


@pytest.fixture
def mock_polygon_api_key():
    """Mock Polygon.io API key for testing."""
    return "test_polygon_api_key_sprint14"


@pytest.fixture
def sample_etf_data():
    """Sample ETF data for testing."""
    return {
        'SPY': {
            'ticker': 'SPY',
            'name': 'SPDR S&P 500 ETF Trust',
            'type': 'ETF',
            'composite_figi': 'BBG000BDTBL9',
            'share_class_figi': 'BBG001S5PQL7',
            'cik': '0000884394',
            'list_date': '1993-01-22',
            'market_cap': 450000000000
        },
        'QQQ': {
            'ticker': 'QQQ',
            'name': 'Invesco QQQ Trust ETF',
            'type': 'ETF',
            'composite_figi': 'BBG000BG7MM2',
            'cik': '0000831641',
            'list_date': '1999-03-10',
            'market_cap': 220000000000
        },
        'IWM': {
            'ticker': 'IWM',
            'name': 'iShares Russell 2000 ETF',
            'type': 'ETF',
            'composite_figi': 'BBG000F7RR41',
            'cik': '0001100663',
            'list_date': '2000-05-22',
            'market_cap': 65000000000
        }
    }


@pytest.fixture
def sample_stock_data():
    """Sample stock data for testing."""
    return {
        'AAPL': {
            'ticker': 'AAPL',
            'name': 'Apple Inc.',
            'type': 'CS',  # Common Stock
            'cik': '0000320193',
            'composite_figi': 'BBG000B9XRY4',
            'market_cap': 3000000000000
        },
        'MSFT': {
            'ticker': 'MSFT',
            'name': 'Microsoft Corporation',
            'type': 'CS',
            'cik': '0000789019',
            'composite_figi': 'BBG000BPH459',
            'market_cap': 2800000000000
        },
        'NVDA': {
            'ticker': 'NVDA',
            'name': 'NVIDIA Corporation',
            'type': 'CS',
            'cik': '0001045810',
            'composite_figi': 'BBG000BBJQV0',
            'market_cap': 2200000000000
        }
    }


@pytest.fixture
def sample_ohlcv_data():
    """Sample OHLCV data for testing."""
    base_date = datetime(2024, 9, 1)

    return [
        {
            'symbol': 'SPY',
            'date': base_date - timedelta(days=i),
            'open': 555.00 + i * 0.1,
            'high': 558.00 + i * 0.1,
            'low': 553.00 + i * 0.1,
            'close': 557.00 + i * 0.1,
            'volume': 45000000 + i * 100000,
            'fmv_price': 557.05 + i * 0.1,  # ETF FMV support
            'fmv_supported': True
        } for i in range(30)  # 30 days of data
    ]


@pytest.fixture
def sample_dev_universes():
    """Sample development universes for testing."""
    return {
        'dev_top_10': {
            'name': 'Development Top 10',
            'description': 'Top 10 stocks for development testing',
            'stocks': [
                {'ticker': 'AAPL', 'name': 'Apple Inc.'},
                {'ticker': 'MSFT', 'name': 'Microsoft Corporation'},
                {'ticker': 'NVDA', 'name': 'NVIDIA Corporation'},
                {'ticker': 'GOOGL', 'name': 'Alphabet Inc.'},
                {'ticker': 'AMZN', 'name': 'Amazon.com Inc.'},
                {'ticker': 'META', 'name': 'Meta Platforms Inc.'},
                {'ticker': 'TSLA', 'name': 'Tesla Inc.'},
                {'ticker': 'BRK.B', 'name': 'Berkshire Hathaway Inc.'},
                {'ticker': 'JPM', 'name': 'JPMorgan Chase & Co.'},
                {'ticker': 'JNJ', 'name': 'Johnson & Johnson'}
            ]
        },
        'dev_etfs': {
            'name': 'Development ETFs',
            'description': 'Popular ETFs for development testing',
            'etfs': [
                {'ticker': 'SPY', 'name': 'SPDR S&P 500 ETF Trust'},
                {'ticker': 'QQQ', 'name': 'Invesco QQQ Trust ETF'},
                {'ticker': 'IWM', 'name': 'iShares Russell 2000 ETF'},
                {'ticker': 'VTI', 'name': 'Vanguard Total Stock Market ETF'},
                {'ticker': 'XLF', 'name': 'Financial Select Sector SPDR Fund'}
            ]
        }
    }


@pytest.fixture
def mock_market_holidays_2024():
    """Mock 2024 market holidays for testing."""
    return {
        '2024-01-01',  # New Year's Day
        '2024-01-15',  # MLK Day
        '2024-02-19',  # Presidents Day
        '2024-03-29',  # Good Friday
        '2024-05-27',  # Memorial Day
        '2024-06-19',  # Juneteenth
        '2024-07-04',  # Independence Day
        '2024-09-02',  # Labor Day
        '2024-11-28',  # Thanksgiving
        '2024-12-25'   # Christmas
    }


@pytest.fixture
def temp_test_directory():
    """Temporary directory for test files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


class MockPerformanceTimer:
    """Mock performance timer for consistent testing."""

    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.elapsed = 0
        self.mock_elapsed = 0.1  # Default mock time

    def start(self):
        self.start_time = 0

    def stop(self):
        self.end_time = self.mock_elapsed
        self.elapsed = self.mock_elapsed

    def set_mock_elapsed(self, seconds: float):
        """Set mock elapsed time for testing."""
        self.mock_elapsed = seconds


@pytest.fixture
def mock_performance_timer():
    """Mock performance timer for predictable test results."""
    return MockPerformanceTimer()


# Test data generators
def generate_etf_symbols(count: int = 50) -> list[str]:
    """Generate ETF symbols for testing."""
    etf_prefixes = ['SPY', 'QQQ', 'IWM', 'VTI', 'VOO', 'IVV', 'VEA', 'IEFA', 'VWO', 'EEM']
    symbols = etf_prefixes[:min(count, len(etf_prefixes))]

    # Generate additional symbols if needed
    for i in range(len(symbols), count):
        symbols.append(f'ETF{i:03d}')

    return symbols[:count]


def generate_stock_symbols(count: int = 100) -> list[str]:
    """Generate stock symbols for testing."""
    stock_prefixes = ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META', 'TSLA', 'BRK.B', 'JPM', 'JNJ']
    symbols = stock_prefixes[:min(count, len(stock_prefixes))]

    # Generate additional symbols if needed
    for i in range(len(symbols), count):
        symbols.append(f'STOCK{i:04d}')

    return symbols[:count]


def generate_ohlcv_data(symbol: str, days: int = 30) -> list[dict]:
    """Generate OHLCV data for testing."""
    base_date = datetime.now().date()
    base_price = 100.0

    data = []
    for i in range(days):
        date = base_date - timedelta(days=i)
        price_var = i * 0.1

        data.append({
            'symbol': symbol,
            'date': date.strftime('%Y-%m-%d'),
            'open': base_price + price_var,
            'high': base_price + price_var + 2.0,
            'low': base_price + price_var - 1.5,
            'close': base_price + price_var + 0.5,
            'volume': 1000000 + i * 10000,
            'fmv_price': base_price + price_var + 0.55,
            'fmv_supported': True
        })

    return data


# Test utilities
def assert_etf_metadata_complete(metadata: dict[str, Any]):
    """Assert ETF metadata contains all required fields."""
    required_fields = [
        'etf_type', 'fmv_supported', 'issuer', 'correlation_reference',
        'composite_figi', 'share_class_figi', 'cik', 'inception_date'
    ]

    for field in required_fields:
        assert field in metadata, f"Missing required ETF metadata field: {field}"


def assert_universe_structure_valid(universe_data: dict[str, Any], universe_type: str = 'etf_universe'):
    """Assert universe data structure is valid."""
    assert 'name' in universe_data
    assert 'description' in universe_data

    if universe_type == 'etf_universe':
        assert 'etfs' in universe_data
        assert isinstance(universe_data['etfs'], list)
        assert len(universe_data['etfs']) > 0

        for etf in universe_data['etfs']:
            assert 'ticker' in etf
            assert 'name' in etf

    elif universe_type == 'stock_universe':
        assert 'stocks' in universe_data
        assert isinstance(universe_data['stocks'], list)
        assert len(universe_data['stocks']) > 0

        for stock in universe_data['stocks']:
            assert 'ticker' in stock
            assert 'name' in stock


def assert_performance_benchmark_met(elapsed_time: float, benchmark_seconds: float, operation_name: str):
    """Assert performance benchmark was met."""
    assert elapsed_time < benchmark_seconds, f"{operation_name} took {elapsed_time:.2f}s, exceeding {benchmark_seconds}s benchmark"


# Sprint 14 specific test markers
def pytest_configure(config):
    """Configure pytest markers for Sprint 14 tests."""
    config.addinivalue_line("markers", "etf: ETF integration tests")
    config.addinivalue_line("markers", "eod: End-of-day processing tests")
    config.addinivalue_line("markers", "development: Development environment tests")
    config.addinivalue_line("markers", "integration: Cross-system integration tests")
    config.addinivalue_line("markers", "performance: Performance benchmark tests")
    config.addinivalue_line("markers", "sprint14: Sprint 14 specific tests")


# Collection hooks for Sprint 14 test organization
def pytest_collection_modifyitems(config, items):
    """Modify test collection for Sprint 14 organization."""
    for item in items:
        # Add sprint14 marker to all tests in this directory
        if 'sprint_14' in str(item.fspath):
            item.add_marker(pytest.mark.sprint14)

        # Add specific markers based on test file names
        if 'etf_integration' in str(item.fspath):
            item.add_marker(pytest.mark.etf)

        if 'eod_processing' in str(item.fspath):
            item.add_marker(pytest.mark.eod)

        if 'subset_universe' in str(item.fspath):
            item.add_marker(pytest.mark.development)

        if 'integration' in str(item.fspath):
            item.add_marker(pytest.mark.integration)

        if 'performance_benchmarks' in str(item.fspath):
            item.add_marker(pytest.mark.performance)
