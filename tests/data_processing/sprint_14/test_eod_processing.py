"""
Sprint 14 Phase 1: End-of-Day Market Data Processing Tests
Comprehensive testing for automated EOD processing with market timing and Redis notifications.

Testing Coverage:
- EOD processor initialization and configuration
- Market timing and holiday awareness logic
- Symbol discovery from cache_entries (5,238 tracked symbols)
- Data completeness validation with 95% target
- Redis integration for notifications and status updates
- Performance benchmarks and error handling
"""

import json
import time
from datetime import datetime, timedelta
from datetime import time as dt_time
from unittest.mock import Mock, patch

import pytest

from src.data.eod_processor import EODProcessor


class TestEODProcessorInitialization:
    """Test EOD processor initialization and configuration."""

    @patch.dict('os.environ', {'DATABASE_URI': 'postgresql://test:test@localhost:5432/tickstock',
                              'REDIS_HOST': 'localhost', 'REDIS_PORT': '6379'})
    def test_eod_processor_initialization(self):
        """Test EOD processor initializes with correct configuration."""
        # Act: Initialize EOD processor
        processor = EODProcessor()

        # Assert: Verify configuration loaded
        assert processor.database_uri == 'postgresql://test:test@localhost:5432/tickstock'
        assert processor.redis_host == 'localhost'
        assert processor.redis_port == 6379

        # Verify market timing configuration
        assert processor.market_close_time == dt_time(16, 30)  # 4:30 PM ET
        assert processor.eod_start_delay == timedelta(minutes=30)  # 30 min buffer
        assert processor.completion_target == timedelta(hours=1, minutes=30)  # 90 min total

        # Verify holiday calendar exists
        assert len(processor.market_holidays_2024) > 0
        assert '2024-12-25' in processor.market_holidays_2024  # Christmas

    def test_eod_processor_missing_database_uri(self):
        """Test EOD processor raises error when DATABASE_URI missing."""
        # Arrange: Empty environment
        with patch.dict('os.environ', {}, clear=True):
            # Act & Assert: Should raise ValueError
            with pytest.raises(ValueError, match="DATABASE_URI required"):
                EODProcessor()

    @patch.dict('os.environ', {'DATABASE_URI': 'postgresql://test:test@localhost:5432/tickstock'})
    def test_eod_processor_custom_parameters(self):
        """Test EOD processor accepts custom parameters."""
        # Act: Initialize with custom parameters
        custom_db_uri = 'postgresql://custom:custom@localhost:5432/custom_db'
        custom_redis_host = '192.168.1.100'

        processor = EODProcessor(database_uri=custom_db_uri, redis_host=custom_redis_host)

        # Assert: Verify custom parameters used
        assert processor.database_uri == custom_db_uri
        assert processor.redis_host == custom_redis_host


class TestMarketTimingAndHolidays:
    """Test market timing logic and holiday awareness."""

    @patch.dict('os.environ', {'DATABASE_URI': 'test_db'})
    def test_is_market_day_weekdays(self, eod_processor: EODProcessor):
        """Test market day detection for weekdays."""
        # Test cases: (date_str, day_of_week, expected_result)
        test_cases = [
            ('2024-09-02', 0, True),   # Monday
            ('2024-09-03', 1, True),   # Tuesday
            ('2024-09-04', 2, True),   # Wednesday
            ('2024-09-05', 3, True),   # Thursday
            ('2024-09-06', 4, True),   # Friday
        ]

        for date_str, expected_weekday, expected_result in test_cases:
            # Arrange: Create date object
            test_date = datetime.strptime(date_str, '%Y-%m-%d')
            assert test_date.weekday() == expected_weekday

            # Act: Check if market day
            result = eod_processor.is_market_day(test_date)

            # Assert: Verify expected result
            assert result == expected_result, f"Failed for {date_str} (weekday {expected_weekday})"

    @patch.dict('os.environ', {'DATABASE_URI': 'test_db'})
    def test_is_market_day_weekends(self, eod_processor: EODProcessor):
        """Test market day detection for weekends."""
        # Test weekend dates
        weekend_cases = [
            ('2024-09-07', 5, False),  # Saturday
            ('2024-09-08', 6, False),  # Sunday
            ('2024-09-14', 5, False),  # Saturday
            ('2024-09-15', 6, False),  # Sunday
        ]

        for date_str, expected_weekday, expected_result in weekend_cases:
            # Arrange: Create weekend date
            test_date = datetime.strptime(date_str, '%Y-%m-%d')
            assert test_date.weekday() == expected_weekday

            # Act: Check if market day
            result = eod_processor.is_market_day(test_date)

            # Assert: Should be False for weekends
            assert result == expected_result, f"Weekend {date_str} should not be market day"

    @patch.dict('os.environ', {'DATABASE_URI': 'test_db'})
    def test_is_market_day_holidays(self, eod_processor: EODProcessor):
        """Test market day detection for holidays."""
        # Test known holidays from 2024 calendar
        holiday_cases = [
            ('2024-01-01', False),  # New Year's Day
            ('2024-07-04', False),  # Independence Day
            ('2024-11-28', False),  # Thanksgiving
            ('2024-12-25', False),  # Christmas
        ]

        for date_str, expected_result in holiday_cases:
            # Arrange: Create holiday date
            test_date = datetime.strptime(date_str, '%Y-%m-%d')

            # Act: Check if market day
            result = eod_processor.is_market_day(test_date)

            # Assert: Should be False for holidays
            assert result == expected_result, f"Holiday {date_str} should not be market day"

    @patch.dict('os.environ', {'DATABASE_URI': 'test_db'})
    @patch('src.data.eod_processor.datetime')
    def test_get_last_trading_day(self, mock_datetime, eod_processor: EODProcessor):
        """Test last trading day calculation with various scenarios."""
        # Test cases: (current_date, expected_last_trading_day)
        test_cases = [
            # Monday -> Previous Friday
            (datetime(2024, 9, 2), datetime(2024, 8, 30)),  # Monday -> Friday
            # Tuesday -> Previous Monday (if Monday was trading day)
            (datetime(2024, 9, 3), datetime(2024, 9, 2)),   # Tuesday -> Monday
            # After holiday weekend
            (datetime(2024, 7, 8), datetime(2024, 7, 3)),   # After July 4th holiday
        ]

        for current_date, expected_last_trading in test_cases:
            # Arrange: Mock current date
            mock_datetime.now.return_value = current_date
            mock_datetime.combine = datetime.combine

            # Act: Get last trading day
            result = eod_processor.get_last_trading_day()

            # Assert: Verify expected trading day
            assert result.date() == expected_last_trading.date(), f"Failed for {current_date.date()}"


class TestSymbolDiscovery:
    """Test symbol discovery from cache_entries for EOD processing."""

    @patch('src.data.eod_processor.psycopg2.connect')
    @patch.dict('os.environ', {'DATABASE_URI': 'test_db'})
    def test_get_tracked_symbols_success(self, mock_connect, eod_processor: EODProcessor):
        """Test successful symbol discovery from cache_entries."""
        # Arrange: Mock database query results
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        # Mock cache_entries data with stock and ETF universes
        mock_results = [
            {
                'key': 'stock_top_100',
                'type': 'stock_universe',
                'value': {
                    'name': 'Top 100 Stocks',
                    'stocks': [
                        {'ticker': 'AAPL', 'name': 'Apple Inc.'},
                        {'ticker': 'MSFT', 'name': 'Microsoft Corporation'},
                        {'ticker': 'NVDA', 'name': 'NVIDIA Corporation'}
                    ]
                }
            },
            {
                'key': 'etf_broad_market',
                'type': 'etf_universe',
                'value': {
                    'name': 'Broad Market ETFs',
                    'etfs': [
                        {'ticker': 'SPY', 'name': 'SPDR S&P 500 ETF Trust'},
                        {'ticker': 'VTI', 'name': 'Vanguard Total Stock Market ETF'}
                    ]
                }
            }
        ]
        mock_cursor.fetchall.return_value = mock_results

        # Act: Get tracked symbols
        symbols = eod_processor.get_tracked_symbols()

        # Assert: Verify symbols extracted correctly
        expected_symbols = ['AAPL', 'MSFT', 'NVDA', 'SPY', 'VTI']
        assert sorted(symbols) == sorted(expected_symbols)

        # Verify database query
        mock_cursor.execute.assert_called_once()
        query_args = mock_cursor.execute.call_args[0]
        assert 'cache_entries' in query_args[0]
        assert 'stock_universe' in query_args[0]
        assert 'etf_universe' in query_args[0]

    @patch('src.data.eod_processor.psycopg2.connect')
    @patch.dict('os.environ', {'DATABASE_URI': 'test_db'})
    def test_get_tracked_symbols_excludes_dev_universes(self, mock_connect, eod_processor: EODProcessor):
        """Test symbol discovery excludes development universes."""
        # Arrange: Mock results including dev universes
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        mock_results = [
            {
                'key': 'stock_top_100',  # Production universe
                'type': 'stock_universe',
                'value': {
                    'stocks': [{'ticker': 'AAPL'}, {'ticker': 'MSFT'}]
                }
            },
            {
                'key': 'dev_top_10',  # Development universe - should be excluded
                'type': 'stock_universe',
                'value': {
                    'stocks': [{'ticker': 'DEV1'}, {'ticker': 'DEV2'}]
                }
            }
        ]
        mock_cursor.fetchall.return_value = mock_results

        # Act: Get tracked symbols
        symbols = eod_processor.get_tracked_symbols()

        # Assert: Only production symbols included
        assert 'AAPL' in symbols
        assert 'MSFT' in symbols
        assert 'DEV1' not in symbols
        assert 'DEV2' not in symbols

    @patch('src.data.eod_processor.psycopg2.connect')
    @patch.dict('os.environ', {'DATABASE_URI': 'test_db'})
    def test_get_tracked_symbols_large_dataset(self, mock_connect, eod_processor: EODProcessor):
        """Test symbol discovery with large dataset (5,238 symbols target)."""
        # Arrange: Mock large universe data
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        # Create large stock universe
        large_stocks = [{'ticker': f'STOCK{i:04d}'} for i in range(4500)]
        large_etfs = [{'ticker': f'ETF{i:03d}'} for i in range(738)]  # 4500 + 738 = 5238

        mock_results = [
            {
                'key': 'all_stocks',
                'type': 'stock_universe',
                'value': {'stocks': large_stocks}
            },
            {
                'key': 'all_etfs',
                'type': 'etf_universe',
                'value': {'etfs': large_etfs}
            }
        ]
        mock_cursor.fetchall.return_value = mock_results

        # Act: Get tracked symbols
        symbols = eod_processor.get_tracked_symbols()

        # Assert: Verify large symbol count
        assert len(symbols) == 5238
        assert 'STOCK0000' in symbols
        assert 'STOCK4499' in symbols  # Last stock
        assert 'ETF000' in symbols
        assert 'ETF737' in symbols    # Last ETF


class TestDataCompletenessValidation:
    """Test data completeness validation with 95% target."""

    @patch('src.data.eod_processor.psycopg2.connect')
    @patch.dict('os.environ', {'DATABASE_URI': 'test_db'})
    def test_validate_data_completeness_high_completion(self, mock_connect, eod_processor: EODProcessor):
        """Test data completeness validation with >95% completion rate."""
        # Arrange: Mock database with high completion rate
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        # 98% completion: 98 out of 100 symbols have data
        test_symbols = [f'SYM{i:03d}' for i in range(100)]
        target_date = datetime(2024, 9, 1)

        # Mock database responses: first 98 symbols have data (count=1), last 2 don't (count=0)
        def mock_fetchone_side_effect():
            mock_fetchone_side_effect.call_count = getattr(mock_fetchone_side_effect, 'call_count', 0) + 1
            if mock_fetchone_side_effect.call_count <= 98:
                return (1,)  # Has data
            return (0,)  # No data

        mock_cursor.fetchone.side_effect = mock_fetchone_side_effect

        # Act: Validate data completeness
        result = eod_processor.validate_data_completeness(test_symbols, target_date)

        # Assert: Verify high completion rate results
        assert result['total_symbols'] == 100
        assert result['completed_symbols'] == 98
        assert result['missing_symbols'] == 2
        assert result['completion_rate'] == 0.98
        assert result['status'] == 'COMPLETE'  # >95% = COMPLETE
        assert len(result['missing_symbol_list']) <= 10  # Truncated list

    @patch('src.data.eod_processor.psycopg2.connect')
    @patch.dict('os.environ', {'DATABASE_URI': 'test_db'})
    def test_validate_data_completeness_low_completion(self, mock_connect, eod_processor: EODProcessor):
        """Test data completeness validation with <95% completion rate."""
        # Arrange: Mock database with low completion rate
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        # 85% completion: 85 out of 100 symbols have data
        test_symbols = [f'SYM{i:03d}' for i in range(100)]
        target_date = datetime(2024, 9, 1)

        def mock_fetchone_side_effect():
            mock_fetchone_side_effect.call_count = getattr(mock_fetchone_side_effect, 'call_count', 0) + 1
            if mock_fetchone_side_effect.call_count <= 85:
                return (1,)  # Has data
            return (0,)  # No data

        mock_cursor.fetchone.side_effect = mock_fetchone_side_effect

        # Act: Validate data completeness
        result = eod_processor.validate_data_completeness(test_symbols, target_date)

        # Assert: Verify low completion rate results
        assert result['completion_rate'] == 0.85
        assert result['status'] == 'INCOMPLETE'  # <95% = INCOMPLETE
        assert result['missing_symbols'] == 15

    @patch('src.data.eod_processor.psycopg2.connect')
    @patch.dict('os.environ', {'DATABASE_URI': 'test_db'})
    def test_validate_data_completeness_database_error(self, mock_connect, eod_processor: EODProcessor):
        """Test data completeness validation handles database errors."""
        # Arrange: Mock database error
        mock_connect.side_effect = Exception("Database connection failed")

        test_symbols = ['AAPL', 'MSFT', 'NVDA']
        target_date = datetime(2024, 9, 1)

        # Act: Validate data completeness (should not raise)
        result = eod_processor.validate_data_completeness(test_symbols, target_date)

        # Assert: Verify error handling
        assert result['status'] == 'ERROR'
        assert 'error' in result
        assert result['target_date'] == '2024-09-01'


class TestRedisIntegration:
    """Test Redis integration for EOD notifications and status updates."""

    @patch('src.data.eod_processor.redis.Redis')
    @patch.dict('os.environ', {'DATABASE_URI': 'test_db'})
    def test_redis_connection_establishment(self, mock_redis_class, eod_processor: EODProcessor):
        """Test Redis connection establishment."""
        # Arrange: Mock Redis client
        mock_redis_client = Mock()
        mock_redis_class.return_value = mock_redis_client

        # Act: Connect to Redis
        eod_processor._connect_redis()

        # Assert: Verify Redis connection
        mock_redis_class.assert_called_once_with(
            host='localhost',  # Default host
            port=6379,        # Default port
            decode_responses=True
        )
        mock_redis_client.ping.assert_called_once()
        assert eod_processor.redis_client == mock_redis_client

    @patch('src.data.eod_processor.redis.Redis')
    @patch.dict('os.environ', {'DATABASE_URI': 'test_db'})
    def test_send_eod_notification_success(self, mock_redis_class, eod_processor: EODProcessor):
        """Test successful EOD completion notification via Redis."""
        # Arrange: Mock Redis client
        mock_redis_client = Mock()
        mock_redis_class.return_value = mock_redis_client

        # Sample EOD results
        eod_results = {
            'status': 'COMPLETE',
            'target_date': '2024-09-01',
            'total_symbols': 5238,
            'completion_rate': 0.97,
            'validation_status': 'COMPLETE'
        }

        # Act: Send notification
        eod_processor.send_eod_notification(eod_results)

        # Assert: Verify Redis operations
        assert mock_redis_client.publish.called
        assert mock_redis_client.setex.called

        # Verify publish call
        publish_call = mock_redis_client.publish.call_args
        assert publish_call[0][0] == 'tickstock:eod:completion'

        notification_data = json.loads(publish_call[0][1])
        assert notification_data['type'] == 'eod_completion'
        assert notification_data['results'] == eod_results

        # Verify setex call (status caching)
        setex_call = mock_redis_client.setex.call_args
        assert setex_call[0][0] == 'tickstock:eod:latest_status'
        assert setex_call[0][1] == 86400  # 24 hour TTL

    @patch('src.data.eod_processor.redis.Redis')
    @patch.dict('os.environ', {'DATABASE_URI': 'test_db'})
    def test_send_eod_notification_error_handling(self, mock_redis_class, eod_processor: EODProcessor):
        """Test EOD notification handles Redis errors gracefully."""
        # Arrange: Mock Redis client that raises exception
        mock_redis_client = Mock()
        mock_redis_client.publish.side_effect = Exception("Redis connection lost")
        mock_redis_class.return_value = mock_redis_client

        eod_results = {'status': 'COMPLETE', 'target_date': '2024-09-01'}

        # Act: Send notification (should not raise)
        eod_processor.send_eod_notification(eod_results)

        # Assert: Error should be handled gracefully (function completes)
        assert mock_redis_client.publish.called


class TestEODProcessExecution:
    """Test complete EOD process execution and orchestration."""

    @patch('src.data.eod_processor.EODProcessor.get_tracked_symbols')
    @patch('src.data.eod_processor.EODProcessor.validate_data_completeness')
    @patch('src.data.eod_processor.EODProcessor.send_eod_notification')
    @patch('src.data.eod_processor.EODProcessor.get_last_trading_day')
    @patch.dict('os.environ', {'DATABASE_URI': 'test_db'})
    def test_run_eod_update_success(self, mock_get_last_trading_day, mock_send_notification,
                                   mock_validate_completeness, mock_get_symbols, eod_processor: EODProcessor):
        """Test successful complete EOD update process."""
        # Arrange: Mock all dependencies
        mock_get_last_trading_day.return_value = datetime(2024, 9, 1)
        mock_get_symbols.return_value = ['AAPL', 'MSFT', 'NVDA', 'SPY', 'QQQ']
        mock_validate_completeness.return_value = {
            'completion_rate': 0.97,
            'status': 'COMPLETE'
        }

        # Act: Run EOD update
        result = eod_processor.run_eod_update()

        # Assert: Verify successful execution
        assert result['status'] == 'COMPLETE'
        assert result['target_date'] == '2024-09-01'
        assert result['total_symbols'] == 5
        assert result['completion_rate'] == 0.97
        assert 'processing_time_minutes' in result

        # Verify all methods called
        mock_get_symbols.assert_called_once()
        mock_validate_completeness.assert_called_once()
        mock_send_notification.assert_called_once()

    @patch('src.data.eod_processor.EODProcessor.get_tracked_symbols')
    @patch.dict('os.environ', {'DATABASE_URI': 'test_db'})
    def test_run_eod_update_no_symbols(self, mock_get_symbols, eod_processor: EODProcessor):
        """Test EOD update handles no symbols scenario."""
        # Arrange: Mock no symbols found
        mock_get_symbols.return_value = []

        # Act: Run EOD update
        result = eod_processor.run_eod_update()

        # Assert: Verify error handling
        assert result['status'] == 'ERROR'
        assert result['message'] == 'No tracked symbols found'

    @patch('src.data.eod_processor.EODProcessor.get_tracked_symbols')
    @patch('src.data.eod_processor.EODProcessor.send_eod_notification')
    @patch.dict('os.environ', {'DATABASE_URI': 'test_db'})
    def test_run_eod_update_exception_handling(self, mock_send_notification, mock_get_symbols, eod_processor: EODProcessor):
        """Test EOD update handles exceptions gracefully."""
        # Arrange: Mock exception during processing
        mock_get_symbols.side_effect = Exception("Database connection failed")

        # Act: Run EOD update (should not raise)
        result = eod_processor.run_eod_update()

        # Assert: Verify error handling
        assert result['status'] == 'ERROR'
        assert 'error' in result
        assert 'Database connection failed' in result['error']

        # Verify error notification sent
        mock_send_notification.assert_called_once()


@pytest.mark.performance
class TestEODProcessingPerformance:
    """Performance benchmarks for EOD processing operations."""

    @patch('src.data.eod_processor.EODProcessor.get_tracked_symbols')
    @patch('src.data.eod_processor.EODProcessor.validate_data_completeness')
    @patch.dict('os.environ', {'DATABASE_URI': 'test_db'})
    def test_eod_processing_time_benchmark(self, mock_validate_completeness, mock_get_symbols,
                                          eod_processor: EODProcessor, performance_timer):
        """Test EOD processing meets time benchmarks."""
        # Arrange: Mock large symbol set (5,238 symbols)
        large_symbol_set = [f'SYM{i:04d}' for i in range(5238)]
        mock_get_symbols.return_value = large_symbol_set

        # Mock validation with realistic performance
        def mock_validation_with_delay(symbols, target_date):
            time.sleep(0.1)  # Simulate validation time
            return {
                'completion_rate': 0.95,
                'status': 'COMPLETE',
                'total_symbols': len(symbols),
                'completed_symbols': int(len(symbols) * 0.95)
            }

        mock_validate_completeness.side_effect = mock_validation_with_delay

        # Act: Time the EOD processing
        performance_timer.start()
        result = eod_processor.run_eod_update()
        performance_timer.stop()

        # Assert: Should complete within reasonable time for 5,238 symbols
        # Processing 5,238 symbols should take < 2 minutes for validation
        assert performance_timer.elapsed < 120, f"EOD processing took {performance_timer.elapsed:.2f}s for 5,238 symbols"

        # Log performance metrics
        symbols_per_second = len(large_symbol_set) / performance_timer.elapsed
        print(f"EOD Performance: {len(large_symbol_set)} symbols in {performance_timer.elapsed:.2f}s ({symbols_per_second:.1f} symbols/sec)")

    @patch('src.data.eod_processor.psycopg2.connect')
    @patch.dict('os.environ', {'DATABASE_URI': 'test_db'})
    def test_symbol_discovery_performance(self, mock_connect, eod_processor: EODProcessor, performance_timer):
        """Test symbol discovery performance for large datasets."""
        # Arrange: Mock database with large universe data
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        # Large dataset simulation
        large_stock_universe = {
            'stocks': [{'ticker': f'STOCK{i:04d}'} for i in range(4500)]
        }
        large_etf_universe = {
            'etfs': [{'ticker': f'ETF{i:03d}'} for i in range(738)]
        }

        mock_cursor.fetchall.return_value = [
            {'key': 'all_stocks', 'type': 'stock_universe', 'value': large_stock_universe},
            {'key': 'all_etfs', 'type': 'etf_universe', 'value': large_etf_universe}
        ]

        # Act: Time symbol discovery
        performance_timer.start()
        symbols = eod_processor.get_tracked_symbols()
        performance_timer.stop()

        # Assert: Should discover 5,238 symbols quickly
        assert len(symbols) == 5238
        assert performance_timer.elapsed < 5.0, f"Symbol discovery took {performance_timer.elapsed:.2f}s, too slow"

    @patch('src.data.eod_processor.psycopg2.connect')
    @patch.dict('os.environ', {'DATABASE_URI': 'test_db'})
    def test_data_validation_performance(self, mock_connect, eod_processor: EODProcessor, performance_timer):
        """Test data validation performance for 95% target completion."""
        # Arrange: Mock database for validation queries
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        # Mock fast database responses
        mock_cursor.fetchone.return_value = (1,)  # Has data

        # Large symbol set
        test_symbols = [f'SYM{i:04d}' for i in range(1000)]  # 1000 symbols for performance test
        target_date = datetime(2024, 9, 1)

        # Act: Time data validation
        performance_timer.start()
        result = eod_processor.validate_data_completeness(test_symbols, target_date)
        performance_timer.stop()

        # Assert: Should validate 1000 symbols quickly
        assert performance_timer.elapsed < 10.0, f"Data validation took {performance_timer.elapsed:.2f}s for 1000 symbols"
        assert result['total_symbols'] == 1000


# Test fixtures for EOD processing tests
@pytest.fixture
@patch.dict('os.environ', {'DATABASE_URI': 'postgresql://test:test@localhost:5432/tickstock_test'})
def eod_processor():
    """Create EOD processor instance for testing."""
    return EODProcessor()


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
def sample_eod_results():
    """Sample EOD processing results for testing."""
    return {
        'status': 'COMPLETE',
        'target_date': '2024-09-01',
        'processing_time_minutes': 45.2,
        'total_symbols': 5238,
        'completion_rate': 0.97,
        'validation_status': 'COMPLETE'
    }


@pytest.fixture
def sample_cache_entries_data():
    """Sample cache_entries data representing tracked universes."""
    return [
        {
            'key': 'stock_sp500',
            'type': 'stock_universe',
            'value': {
                'name': 'S&P 500 Stocks',
                'stocks': [
                    {'ticker': 'AAPL', 'name': 'Apple Inc.'},
                    {'ticker': 'MSFT', 'name': 'Microsoft Corporation'},
                    {'ticker': 'NVDA', 'name': 'NVIDIA Corporation'}
                ]
            }
        },
        {
            'key': 'etf_broad_market',
            'type': 'etf_universe',
            'value': {
                'name': 'Broad Market ETFs',
                'etfs': [
                    {'ticker': 'SPY', 'name': 'SPDR S&P 500 ETF Trust'},
                    {'ticker': 'VTI', 'name': 'Vanguard Total Stock Market ETF'}
                ]
            }
        }
    ]


@pytest.fixture
def mock_market_holidays():
    """Mock market holidays for testing."""
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
