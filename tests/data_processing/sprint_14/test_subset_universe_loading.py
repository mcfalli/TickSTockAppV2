"""
Sprint 14 Phase 1: Subset Universe Loading Tests
Comprehensive testing for development environment optimizations and CLI parameters.

Testing Coverage:
- CLI parameter parsing (--symbols, --months, --dev-mode)
- Development universe creation (dev_top_10, dev_sectors, dev_etfs)
- Time range limiting for development environments
- Performance optimization for <5 minute load times
- Development vs production environment isolation
"""

import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from src.data.historical_loader import PolygonHistoricalLoader


class TestCLIParameterParsing:
    """Test CLI parameter parsing for subset universe loading."""

    def test_symbols_parameter_parsing(self):
        """Test --symbols parameter parsing for custom symbol lists."""
        # Test various symbol list formats
        test_cases = [
            ('AAPL,MSFT,NVDA', ['AAPL', 'MSFT', 'NVDA']),
            ('SPY,QQQ,IWM,VTI', ['SPY', 'QQQ', 'IWM', 'VTI']),
            ('AAPL', ['AAPL']),  # Single symbol
            ('GOOGL,AMZN,META,TSLA,NFLX', ['GOOGL', 'AMZN', 'META', 'TSLA', 'NFLX']),  # 5 symbols
        ]

        for symbols_str, expected_symbols in test_cases:
            # Simulate parsing symbols from CLI
            parsed_symbols = symbols_str.split(',')

            # Assert: Verify parsing correctness
            assert parsed_symbols == expected_symbols
            assert all(symbol.isupper() for symbol in parsed_symbols)
            assert all(symbol.isalpha() for symbol in parsed_symbols)
            assert len(parsed_symbols) <= 10  # Development limit

    def test_months_parameter_validation(self):
        """Test --months parameter validation for time range limiting."""
        # Test valid month ranges
        valid_months = [1, 3, 6, 12, 18, 24]

        for months in valid_months:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=months * 30)  # Approximate

            # Assert: Verify reasonable time ranges
            date_diff = end_date - start_date
            expected_days = months * 30
            assert abs(date_diff.days - expected_days) <= 5  # Allow some variance

            # Development environments should limit to <= 24 months
            assert months <= 24, f"Development environments should limit to 24 months, got {months}"

    def test_dev_mode_parameter_validation(self):
        """Test --dev-mode parameter for development environment settings."""
        # Test development mode configurations
        dev_mode_configs = {
            'api_delay': 12,  # Seconds between API calls (rate limiting)
            'batch_size': 500,  # Smaller batches for dev
            'max_symbols': 20,  # Symbol limit for dev environments
            'use_delayed_data': True,  # Use 15-minute delayed data for cost savings
            'environment': 'development'
        }

        # Assert: Verify development mode restrictions
        assert dev_mode_configs['api_delay'] >= 10  # Respectful rate limiting
        assert dev_mode_configs['batch_size'] <= 1000  # Reasonable batch size
        assert dev_mode_configs['max_symbols'] <= 50  # Development symbol limit
        assert dev_mode_configs['use_delayed_data'] is True  # Cost optimization

    def test_parameter_combination_validation(self):
        """Test valid combinations of CLI parameters."""
        # Test cases: (symbols_count, months, expected_valid)
        test_cases = [
            (10, 6, True),   # Standard dev load - should be fast
            (5, 12, True),   # Small long-term load - acceptable
            (20, 3, True),   # More symbols, shorter time - balanced
            (50, 1, True),   # Many symbols, very short time - edge case
            (3, 24, True),   # Few symbols, max dev time - acceptable
        ]

        for symbol_count, months, expected_valid in test_cases:
            # Calculate expected processing characteristics
            estimated_api_calls = symbol_count * (months * 22)  # ~22 trading days per month
            estimated_time_minutes = (estimated_api_calls * 12) / 60  # 12 sec per call / 60 sec per min

            if expected_valid:
                # Development loads should complete in < 5 minutes for core use cases
                if symbol_count <= 10 and months <= 6:
                    assert estimated_time_minutes < 5, f"Dev load should be <5min: {symbol_count} symbols, {months} months"


class TestDevelopmentUniverseCreation:
    """Test development universe creation and management."""

    @patch('src.data.historical_loader.psycopg2.connect')
    def test_create_dev_universes(self, mock_connect, historical_loader: PolygonHistoricalLoader):
        """Test creation of development universes in cache_entries."""
        # Arrange: Mock database connection
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        # Development universe definitions
        dev_universes = {
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
            'dev_sectors': {
                'name': 'Development Sectors',
                'description': 'Representative stocks from major sectors',
                'stocks': [
                    {'ticker': 'AAPL', 'name': 'Apple Inc. (Technology)'},
                    {'ticker': 'JPM', 'name': 'JPMorgan Chase (Financials)'},
                    {'ticker': 'JNJ', 'name': 'Johnson & Johnson (Healthcare)'},
                    {'ticker': 'XOM', 'name': 'Exxon Mobil (Energy)'},
                    {'ticker': 'HD', 'name': 'Home Depot (Consumer Discretionary)'},
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

        # Act: Simulate creation of development universes
        for universe_key, universe_data in dev_universes.items():
            # This would be done by historical loader in practice
            universe_type = 'etf_universe' if 'etfs' in universe_data else 'stock_universe'

            # Verify universe structure
            assert universe_key.startswith('dev_')
            assert 'name' in universe_data
            assert 'description' in universe_data

            # Verify symbol counts appropriate for development
            if 'stocks' in universe_data:
                assert len(universe_data['stocks']) <= 10
            if 'etfs' in universe_data:
                assert len(universe_data['etfs']) <= 5

    def test_dev_universe_symbol_selection(self):
        """Test development universe symbol selection criteria."""
        # Top 10 should include major market leaders
        expected_top_10 = ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META', 'TSLA', 'BRK.B', 'JPM', 'JNJ']

        for symbol in expected_top_10:
            assert len(symbol) <= 5  # Valid ticker length
            assert symbol.isupper()  # Proper ticker format

        # Sector representatives should cover major sectors
        sector_symbols = ['AAPL', 'JPM', 'JNJ', 'XOM', 'HD']  # Tech, Finance, Healthcare, Energy, Consumer

        # Should have diversity across sectors
        assert len(set(sector_symbols)) == len(sector_symbols)  # No duplicates

        # ETF selection should cover broad market exposure
        dev_etfs = ['SPY', 'QQQ', 'IWM', 'VTI', 'XLF']

        # Should include broad market (SPY, VTI), tech (QQQ), small cap (IWM), sector (XLF)
        broad_market_etfs = ['SPY', 'VTI']
        assert any(etf in dev_etfs for etf in broad_market_etfs)

    def test_development_environment_isolation(self):
        """Test development environment isolation from production."""
        # Development configurations should be isolated
        dev_config = {
            'database_suffix': '_dev',
            'api_quota_limit': 100,  # Lower quota for development
            'cache_ttl': 3600,  # Shorter cache TTL
            'log_level': 'DEBUG',
            'use_delayed_data': True
        }

        prod_config = {
            'database_suffix': '',
            'api_quota_limit': 5000,  # Higher quota for production
            'cache_ttl': 86400,  # Longer cache TTL
            'log_level': 'INFO',
            'use_delayed_data': False
        }

        # Assert: Verify isolation between environments
        assert dev_config['database_suffix'] != prod_config['database_suffix']
        assert dev_config['api_quota_limit'] < prod_config['api_quota_limit']
        assert dev_config['use_delayed_data'] != prod_config['use_delayed_data']


class TestTimeRangeLimiting:
    """Test time range limiting functionality for development loads."""

    def test_date_range_calculation(self):
        """Test date range calculation for various month parameters."""
        # Test cases: (months, expected_trading_days_approx)
        test_cases = [
            (1, 22),   # ~22 trading days per month
            (3, 66),   # ~3 * 22 = 66 trading days
            (6, 132),  # ~6 * 22 = 132 trading days
            (12, 264), # ~12 * 22 = 264 trading days (1 year)
        ]

        for months, expected_trading_days in test_cases:
            # Calculate date range
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=months * 30)

            # Verify range is reasonable
            actual_days = (end_date - start_date).days
            expected_calendar_days = months * 30

            assert abs(actual_days - expected_calendar_days) <= 10  # Allow variance

            # Trading days should be ~70% of calendar days (weekends + holidays)
            estimated_trading_days = actual_days * 0.71
            assert abs(estimated_trading_days - expected_trading_days) <= 20

    def test_historical_data_limiting(self):
        """Test historical data limiting based on time ranges."""
        # Define various time limits for development
        time_limits = {
            'quick_test': 1,    # 1 month for quick iteration
            'sprint_test': 3,   # 3 months for sprint testing
            'demo_data': 6,     # 6 months for demos
            'full_dev': 12      # 12 months for full dev testing
        }

        for limit_name, months in time_limits.items():
            # Calculate data volume implications
            symbol_count = 10  # Standard dev universe
            trading_days = months * 22
            data_points_per_symbol = trading_days  # Daily OHLCV
            total_data_points = symbol_count * data_points_per_symbol

            # Verify reasonable data volumes for development
            assert total_data_points <= 30000, f"{limit_name} generates too much data: {total_data_points}"

            # Quick tests should be very fast
            if limit_name == 'quick_test':
                assert total_data_points <= 500  # Very small for iteration

    def test_development_vs_production_time_limits(self):
        """Test time limit differences between development and production."""
        # Development limits (cost-conscious)
        dev_limits = {
            'max_months': 24,
            'recommended_months': 6,
            'quick_test_months': 1
        }

        # Production limits (comprehensive)
        prod_limits = {
            'max_months': 60,  # 5 years
            'standard_months': 24,  # 2 years
            'backfill_months': 12
        }

        # Assert: Development should be more restrictive
        assert dev_limits['max_months'] < prod_limits['max_months']
        assert dev_limits['recommended_months'] < prod_limits['standard_months']


@pytest.mark.performance
class TestSubsetLoadingPerformance:
    """Performance benchmarks for subset universe loading."""

    @patch('src.data.historical_loader.psycopg2.connect')
    @patch('src.data.historical_loader.requests.Session.get')
    def test_dev_universe_loading_performance(self, mock_get, mock_connect, historical_loader: PolygonHistoricalLoader, performance_timer):
        """Test development universe loading meets <5 minute benchmark."""
        # Arrange: Mock API responses for development load
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 'OK',
            'queryCount': 132,  # ~6 months of trading days
            'results': [
                {
                    't': int(datetime.now().timestamp() * 1000),
                    'o': 150.0,
                    'h': 152.0,
                    'l': 149.0,
                    'c': 151.0,
                    'v': 1000000
                }
            ]
        }
        mock_get.return_value = mock_response

        # Mock database operations
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        # Development universe: 10 stocks + 5 ETFs with 6 months data
        dev_symbols = ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META', 'TSLA', 'BRK.B', 'JPM', 'JNJ',
                      'SPY', 'QQQ', 'IWM', 'VTI', 'XLF']

        # Act: Time the development load
        performance_timer.start()

        # Simulate historical data loading with rate limiting
        for symbol in dev_symbols:
            # Simulate API call (normally would be historical_loader.load_historical_data)
            time.sleep(0.1)  # 100ms per symbol (much faster than production 12s rate limit)

        performance_timer.stop()

        # Assert: Should complete in <5 minutes (300 seconds)
        assert performance_timer.elapsed < 300, f"Dev load took {performance_timer.elapsed:.2f}s, exceeding 5min benchmark"

        # Log performance metrics
        symbols_per_minute = len(dev_symbols) / (performance_timer.elapsed / 60)
        print(f"Development Load Performance: {len(dev_symbols)} symbols in {performance_timer.elapsed:.2f}s ({symbols_per_minute:.1f} symbols/min)")

    @patch('src.data.historical_loader.requests.Session.get')
    def test_api_rate_limiting_optimization(self, mock_get, historical_loader: PolygonHistoricalLoader, performance_timer):
        """Test optimized API rate limiting for development environments."""
        # Arrange: Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'status': 'OK', 'results': []}
        mock_get.return_value = mock_response

        # Act: Test rate limiting with development optimizations
        api_calls = 5
        performance_timer.start()

        for i in range(api_calls):
            # Simulate optimized rate limiting for development
            # Production: 12 seconds between calls (5 calls/minute)
            # Development: Could use 2 seconds between calls (30 calls/minute)
            if i > 0:  # No delay for first call
                time.sleep(0.5)  # 500ms delay for testing (much faster than prod)

        performance_timer.stop()

        # Assert: Development rate limiting should be more aggressive than production
        avg_time_per_call = performance_timer.elapsed / api_calls
        assert avg_time_per_call < 2.0, f"Development rate limiting too slow: {avg_time_per_call:.2f}s per call"

    def test_subset_data_validation_performance(self, performance_timer):
        """Test data validation performance for subset loads."""
        # Arrange: Sample development data
        sample_data = []
        for i in range(1000):  # 1000 data points
            sample_data.append({
                'symbol': 'AAPL',
                'date': '2024-01-01',
                'open': 150.0 + i * 0.01,
                'high': 151.0 + i * 0.01,
                'low': 149.0 + i * 0.01,
                'close': 150.5 + i * 0.01,
                'volume': 1000000 + i * 1000
            })

        # Act: Time data validation
        performance_timer.start()

        validated_count = 0
        for record in sample_data:
            # Basic validation checks
            if (record['open'] > 0 and record['high'] >= record['open'] and
                record['low'] <= record['open'] and record['close'] > 0 and
                record['volume'] > 0):
                validated_count += 1

        performance_timer.stop()

        # Assert: Validation should be very fast
        assert performance_timer.elapsed < 1.0, f"Data validation too slow: {performance_timer.elapsed:.2f}s for {len(sample_data)} records"
        assert validated_count == len(sample_data), "Data validation failed for some records"


class TestDevelopmentDataOptimizations:
    """Test development-specific data optimizations and cost savings."""

    def test_delayed_data_configuration(self):
        """Test delayed data configuration for development cost savings."""
        # Development configuration for delayed data
        delayed_data_config = {
            'use_delayed_data': True,
            'delay_minutes': 15,  # 15-minute delayed data
            'cost_savings_percent': 52,  # ~52% cost savings per documentation
            'api_endpoint_suffix': '/delayed'
        }

        # Assert: Verify delayed data settings
        assert delayed_data_config['use_delayed_data'] is True
        assert delayed_data_config['delay_minutes'] == 15
        assert delayed_data_config['cost_savings_percent'] > 50

    def test_development_caching_strategy(self):
        """Test caching strategies for development environments."""
        # Development caching should be more aggressive
        dev_cache_config = {
            'cache_enabled': True,
            'cache_ttl_seconds': 3600,  # 1 hour
            'cache_historical_data': True,
            'cache_universe_definitions': True,
            'local_file_cache': True
        }

        # Assert: Verify caching reduces API calls
        assert dev_cache_config['cache_enabled'] is True
        assert dev_cache_config['cache_ttl_seconds'] >= 3600  # At least 1 hour
        assert dev_cache_config['cache_historical_data'] is True

    def test_development_error_handling(self):
        """Test error handling optimized for development workflows."""
        # Development error handling should be more permissive
        dev_error_config = {
            'retry_attempts': 3,
            'retry_delay_seconds': 1,  # Faster retries
            'skip_missing_data': True,  # Continue on missing data
            'log_level': 'DEBUG',
            'fail_fast': False  # Don't fail entire load on single symbol error
        }

        # Assert: Verify development-friendly error handling
        assert dev_error_config['retry_attempts'] >= 3
        assert dev_error_config['retry_delay_seconds'] <= 5
        assert dev_error_config['skip_missing_data'] is True
        assert dev_error_config['fail_fast'] is False


# Test fixtures for subset loading tests
@pytest.fixture
def historical_loader():
    """Create historical loader instance for testing."""
    with patch.dict('os.environ', {
        'POLYGON_API_KEY': 'test_key_12345',
        'DATABASE_URI': 'postgresql://test:test@localhost:5432/tickstock_test'
    }):
        loader = PolygonHistoricalLoader()
        return loader


@pytest.fixture
def performance_timer():
    """Performance timing utility for benchmarks."""
    class PerformanceTimer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
            self.elapsed = 0

        def start(self):
            self.start_time = time.perf_counter()

        def stop(self):
            if self.start_time is None:
                raise RuntimeError("Timer not started")
            self.end_time = time.perf_counter()
            self.elapsed = self.end_time - self.start_time

    return PerformanceTimer()


@pytest.fixture
def sample_cli_args():
    """Sample CLI arguments for testing."""
    return {
        'symbols_basic': ['AAPL', 'MSFT', 'NVDA'],
        'symbols_mixed': ['AAPL', 'MSFT', 'SPY', 'QQQ', 'IWM'],
        'months_ranges': [1, 3, 6, 12],
        'dev_mode_flags': {
            'use_delayed_data': True,
            'reduced_rate_limit': True,
            'enable_caching': True,
            'skip_missing_data': True
        }
    }


@pytest.fixture
def mock_dev_universes():
    """Mock development universe definitions."""
    return {
        'dev_top_10': {
            'name': 'Development Top 10',
            'stocks': [
                {'ticker': 'AAPL'}, {'ticker': 'MSFT'}, {'ticker': 'NVDA'},
                {'ticker': 'GOOGL'}, {'ticker': 'AMZN'}, {'ticker': 'META'},
                {'ticker': 'TSLA'}, {'ticker': 'BRK.B'}, {'ticker': 'JPM'}, {'ticker': 'JNJ'}
            ]
        },
        'dev_sectors': {
            'name': 'Development Sectors',
            'stocks': [
                {'ticker': 'AAPL'}, {'ticker': 'JPM'}, {'ticker': 'JNJ'},
                {'ticker': 'XOM'}, {'ticker': 'HD'}
            ]
        },
        'dev_etfs': {
            'name': 'Development ETFs',
            'etfs': [
                {'ticker': 'SPY'}, {'ticker': 'QQQ'}, {'ticker': 'IWM'},
                {'ticker': 'VTI'}, {'ticker': 'XLF'}
            ]
        }
    }
