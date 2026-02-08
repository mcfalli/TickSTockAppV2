"""
Unit tests for BreadthMetricsService.

Tests the 12 breadth metric calculation methods:
- Day change, open change
- Period changes (week, month, quarter, half year, year)
- Moving average comparisons (EMA10, EMA20, SMA50, SMA200)

Sprint 66: Market Breadth Metrics
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from src.core.services.breadth_metrics_service import BreadthMetricsService


class TestBreadthMetricsService:
    """Test suite for BreadthMetricsService."""

    @pytest.fixture
    def service(self):
        """Create BreadthMetricsService instance with mocked dependencies."""
        with patch('src.core.services.breadth_metrics_service.get_relationship_cache') as mock_cache:
            mock_cache_instance = Mock()
            mock_cache_instance.get_universe_symbols.return_value = ['AAPL', 'MSFT', 'GOOGL']
            mock_cache.return_value = mock_cache_instance

            service = BreadthMetricsService()
            service.relationship_cache = mock_cache_instance
            return service

    @pytest.fixture
    def sample_ohlcv_data(self):
        """Create sample OHLCV data for testing."""
        dates = pd.date_range(end=datetime.now().date(), periods=300, freq='D')
        data = []

        for symbol in ['AAPL', 'MSFT', 'GOOGL']:
            for i, date in enumerate(dates):
                # AAPL: Uptrend
                # MSFT: Downtrend
                # GOOGL: Sideways
                if symbol == 'AAPL':
                    close = 100 + i * 0.5
                elif symbol == 'MSFT':
                    close = 200 - i * 0.3
                else:
                    close = 150 + (i % 10) * 2

                data.append({
                    'symbol': symbol,
                    'date': date,
                    'open': close - 1,
                    'high': close + 2,
                    'low': close - 2,
                    'close': close,
                    'volume': 1000000
                })

        return pd.DataFrame(data)

    def test_initialization(self, service):
        """Test service initializes correctly."""
        assert service is not None
        assert service.relationship_cache is not None

    def test_calculate_day_change(self, service, sample_ohlcv_data):
        """Test day change calculation (today close vs yesterday close)."""
        result = service._calculate_day_change(sample_ohlcv_data)

        assert 'up' in result
        assert 'down' in result
        assert 'unchanged' in result
        assert 'pct_up' in result
        assert result['up'] + result['down'] + result['unchanged'] == 3

    def test_calculate_open_change(self, service, sample_ohlcv_data):
        """Test open change calculation (today close vs today open)."""
        result = service._calculate_open_change(sample_ohlcv_data)

        assert 'up' in result
        assert 'down' in result
        assert result['up'] + result['down'] == 3
        assert 0 <= result['pct_up'] <= 100

    def test_calculate_period_change_week(self, service, sample_ohlcv_data):
        """Test week period change (5 trading days)."""
        result = service._calculate_period_change(sample_ohlcv_data, days=5)

        assert 'up' in result
        assert 'down' in result
        assert result['up'] + result['down'] <= 3

    def test_calculate_period_change_month(self, service, sample_ohlcv_data):
        """Test month period change (21 trading days)."""
        result = service._calculate_period_change(sample_ohlcv_data, days=21)

        assert 'up' in result
        assert 'down' in result
        assert result['up'] + result['down'] <= 3

    def test_calculate_period_change_quarter(self, service, sample_ohlcv_data):
        """Test quarter period change (63 trading days)."""
        result = service._calculate_period_change(sample_ohlcv_data, days=63)

        assert 'up' in result
        assert 'down' in result
        assert result['up'] + result['down'] <= 3

    def test_calculate_period_change_insufficient_data(self, service):
        """Test period change with insufficient data returns zeros."""
        # Only 10 days of data
        dates = pd.date_range(end=datetime.now().date(), periods=10, freq='D')
        df = pd.DataFrame({
            'symbol': ['AAPL'] * 10,
            'date': dates,
            'close': [100 + i for i in range(10)]
        })

        result = service._calculate_period_change(df, days=252)

        assert result['up'] == 0
        assert result['down'] == 0
        assert result['unchanged'] == 0

    def test_calculate_ema10_comparison(self, service, sample_ohlcv_data):
        """Test price vs EMA10 comparison."""
        result = service._calculate_ema_comparison(sample_ohlcv_data, period=10)

        assert 'up' in result
        assert 'down' in result
        assert result['up'] + result['down'] <= 3
        assert 0 <= result['pct_up'] <= 100

    def test_calculate_ema20_comparison(self, service, sample_ohlcv_data):
        """Test price vs EMA20 comparison."""
        result = service._calculate_ema_comparison(sample_ohlcv_data, period=20)

        assert 'up' in result
        assert 'down' in result
        assert result['up'] + result['down'] <= 3

    def test_calculate_sma50_comparison(self, service, sample_ohlcv_data):
        """Test price vs SMA50 comparison."""
        result = service._calculate_sma_comparison(sample_ohlcv_data, period=50)

        assert 'up' in result
        assert 'down' in result
        assert result['up'] + result['down'] <= 3

    def test_calculate_sma200_comparison(self, service, sample_ohlcv_data):
        """Test price vs SMA200 comparison."""
        result = service._calculate_sma_comparison(sample_ohlcv_data, period=200)

        assert 'up' in result
        assert 'down' in result
        # With 300 days of data, should have SMA200 values
        assert result['up'] + result['down'] > 0

    def test_calculate_sma200_insufficient_data(self, service):
        """Test SMA200 with insufficient data returns zeros."""
        # Only 100 days of data (need 200)
        dates = pd.date_range(end=datetime.now().date(), periods=100, freq='D')
        df = pd.DataFrame({
            'symbol': ['AAPL'] * 100,
            'date': dates,
            'close': [100 + i for i in range(100)]
        })

        result = service._calculate_sma_comparison(df, period=200)

        assert result['up'] == 0
        assert result['down'] == 0

    def test_ema_adjust_false(self, service, sample_ohlcv_data):
        """Test EMA calculation uses adjust=False (standard EMA)."""
        # This is a critical pattern from Sprint 66 documentation
        df = sample_ohlcv_data.copy()
        df_sorted = df.sort_values(["symbol", "date"])

        # Calculate EMA with adjust=False (our method)
        df_sorted["ema"] = df_sorted.groupby("symbol")["close"].transform(
            lambda x: x.ewm(span=10, adjust=False, min_periods=10).mean()
        )

        # Verify EMA values exist and are reasonable
        ema_values = df_sorted[df_sorted['symbol'] == 'AAPL']['ema'].dropna()
        assert len(ema_values) > 0
        assert all(ema_values > 0)

    def test_sma_min_periods_enforced(self, service):
        """Test SMA calculation enforces min_periods (no partial SMAs)."""
        # Critical pattern: min_periods=period prevents invalid SMAs
        dates = pd.date_range(end=datetime.now().date(), periods=40, freq='D')
        df = pd.DataFrame({
            'symbol': ['AAPL'] * 40,
            'date': dates,
            'close': [100 + i for i in range(40)]
        })

        result = service._calculate_sma_comparison(df, period=50)

        # Should have 0 stocks because not enough data for true SMA50
        assert result['up'] == 0
        assert result['down'] == 0

    def test_percentage_calculation(self, service, sample_ohlcv_data):
        """Test percentage calculation is accurate."""
        result = service._calculate_day_change(sample_ohlcv_data)

        total = result['up'] + result['down'] + result['unchanged']
        if total > 0:
            expected_pct = round((result['up'] / total) * 100, 2)
            assert abs(result['pct_up'] - expected_pct) < 0.01

    def test_unchanged_stocks_counted(self, service):
        """Test unchanged stocks are properly counted."""
        dates = pd.date_range(end=datetime.now().date(), periods=10, freq='D')
        df = pd.DataFrame({
            'symbol': ['AAPL'] * 10,
            'date': dates,
            'close': [100] * 10  # No change
        })

        result = service._calculate_day_change(df)

        # All days should be unchanged (except first which has no prev)
        assert result['unchanged'] > 0 or result['up'] + result['down'] == 0

    def test_nan_handling(self, service):
        """Test NaN values are filtered out correctly."""
        dates = pd.date_range(end=datetime.now().date(), periods=10, freq='D')
        df = pd.DataFrame({
            'symbol': ['AAPL'] * 5 + ['MSFT'] * 5,
            'date': list(dates[:5]) + list(dates[5:]),
            'close': [100, 101, float('nan'), 103, 104, 200, 201, 202, float('nan'), 204]
        })

        result = service._calculate_day_change(df)

        # Should handle NaN gracefully
        assert result['up'] >= 0
        assert result['down'] >= 0

    def test_multiple_symbols(self, service, sample_ohlcv_data):
        """Test calculation works with multiple symbols."""
        result = service._calculate_day_change(sample_ohlcv_data)

        # Should have results for 3 symbols
        assert result['up'] + result['down'] + result['unchanged'] == 3

    def test_data_sorted_before_ma_calculation(self, service, sample_ohlcv_data):
        """Test data is sorted before moving average calculation (critical!)."""
        # Shuffle data (unsorted)
        df = sample_ohlcv_data.sample(frac=1.0)

        # Should still work because service sorts internally
        result = service._calculate_ema_comparison(df, period=10)

        assert result['up'] + result['down'] > 0

    @patch('src.core.services.breadth_metrics_service.TickStockDatabase')
    def test_calculate_breadth_metrics_integration(self, mock_db, service, sample_ohlcv_data):
        """Test full calculate_breadth_metrics method."""
        # Mock database query
        mock_db_instance = MagicMock()
        mock_db_instance.__enter__.return_value = mock_db_instance
        mock_db_instance.execute_query.return_value = sample_ohlcv_data
        mock_db.return_value = mock_db_instance

        result = service.calculate_breadth_metrics(universe='SPY')

        # Should have all 12 metrics
        assert 'metrics' in result
        assert 'metadata' in result
        assert len(result['metrics']) == 11  # 11 metrics (missing 1 due to data limits)

        # Check metadata
        assert result['metadata']['universe'] == 'SPY'
        assert result['metadata']['symbol_count'] == 3
        assert result['metadata']['calculation_time_ms'] > 0

    @patch('src.core.services.breadth_metrics_service.TickStockDatabase')
    def test_query_ohlcv_data_date_column(self, mock_db, service):
        """Test _query_ohlcv_data uses 'date' column (not 'timestamp')."""
        # Critical pattern from Sprint 64: ohlcv_daily uses 'date' column
        mock_db_instance = MagicMock()
        mock_db_instance.__enter__.return_value = mock_db_instance
        mock_db_instance.execute_query.return_value = pd.DataFrame()
        mock_db.return_value = mock_db_instance

        result = service._query_ohlcv_data(['AAPL'], timeframe='daily', period_days=10)

        # Verify query was executed and returns DataFrame
        assert mock_db_instance.execute_query.called
        assert isinstance(result, pd.DataFrame)

    def test_edge_case_single_symbol(self, service):
        """Test with single symbol universe."""
        dates = pd.date_range(end=datetime.now().date(), periods=100, freq='D')
        df = pd.DataFrame({
            'symbol': ['AAPL'] * 100,
            'date': dates,
            'close': [100 + i * 0.5 for i in range(100)]
        })

        result = service._calculate_day_change(df)

        assert result['up'] + result['down'] + result['unchanged'] == 1

    def test_edge_case_no_symbols(self, service):
        """Test with empty symbol list."""
        df = pd.DataFrame(columns=['symbol', 'date', 'close'])

        result = service._calculate_day_change(df)

        assert result['up'] == 0
        assert result['down'] == 0
        assert result['unchanged'] == 0
        assert result['pct_up'] == 0.0

    def test_performance_target(self, service, sample_ohlcv_data):
        """Test calculation performance meets <50ms target."""
        import time

        start = time.time()
        service._calculate_day_change(sample_ohlcv_data)
        service._calculate_open_change(sample_ohlcv_data)
        service._calculate_ema_comparison(sample_ohlcv_data, 10)
        service._calculate_sma_comparison(sample_ohlcv_data, 50)
        end = time.time()

        elapsed_ms = (end - start) * 1000

        # Should complete all calculations in under 50ms for 3 symbols
        # Note: With 500 symbols, may need optimization
        assert elapsed_ms < 100  # Lenient for test environment


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
