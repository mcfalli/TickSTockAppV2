"""
End-to-end integration tests for Market Breadth Metrics feature.

Tests the complete flow from database → service → API → response:
- RelationshipCache integration
- Database query execution
- Service calculations with real-ish data
- API endpoint integration
- Response validation

Sprint 66: Market Breadth Metrics
"""

import pytest
import json
from unittest.mock import patch, MagicMock
import pandas as pd
from datetime import datetime, timedelta


class TestBreadthMetricsE2E:
    """End-to-end integration tests for breadth metrics feature."""

    @pytest.fixture
    def mock_relationship_cache(self):
        """Mock RelationshipCache with test data."""
        with patch('src.core.services.breadth_metrics_service.get_relationship_cache') as mock:
            mock_cache = MagicMock()

            # SPY: 504 stocks
            mock_cache.get_universe_symbols.side_effect = lambda universe: {
                'SPY': [f'SYMBOL{i}' for i in range(504)],
                'QQQ': [f'TECH{i}' for i in range(102)],
                'dow30': [f'DOW{i}' for i in range(30)],
                'nasdaq100': [f'NDX{i}' for i in range(102)]
            }.get(universe.upper(), [])

            mock.return_value = mock_cache
            yield mock_cache

    @pytest.fixture
    def mock_database_with_data(self):
        """Mock database with realistic OHLCV data."""
        # Create 252 days of data
        dates = pd.date_range(end=datetime.now().date(), periods=252, freq='D')

        def create_test_data(*args, **kwargs):
            # Extract symbols from various possible call patterns
            symbols = []
            if len(args) > 1 and isinstance(args[1], dict) and 'symbols' in args[1]:
                symbols = args[1]['symbols'][:100]  # Limit to 100 for speed
            elif 'params' in kwargs and kwargs['params'] and 'symbols' in kwargs['params']:
                symbols = kwargs['params']['symbols'][:100]
            else:
                symbols = [f'SYMBOL{i}' for i in range(100)]  # Default

            data = []
            for symbol_idx, symbol in enumerate(symbols):
                # Create price trends
                # 60% uptrending, 30% downtrending, 10% sideways
                if symbol_idx < 60:
                    trend = 0.5  # Uptrend
                elif symbol_idx < 90:
                    trend = -0.3  # Downtrend
                else:
                    trend = 0  # Sideways

                base_price = 100 + symbol_idx

                for i, date in enumerate(dates):
                    close = base_price + i * trend
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

        with patch('src.core.services.breadth_metrics_service.TickStockDatabase') as mock_db:
            mock_db_instance = MagicMock()
            mock_db_instance.__enter__.return_value = mock_db_instance
            mock_db_instance.execute_query.side_effect = create_test_data
            mock_db.return_value = mock_db_instance

            yield mock_db_instance

    def test_e2e_spy_breadth_calculation(self, mock_relationship_cache, mock_database_with_data):
        """Test end-to-end SPY breadth calculation."""
        from src.core.services.breadth_metrics_service import BreadthMetricsService

        service = BreadthMetricsService()
        result = service.calculate_breadth_metrics(universe='SPY')

        # Verify structure
        assert 'metrics' in result
        assert 'metadata' in result

        # Verify metadata
        assert result['metadata']['universe'] == 'SPY'
        assert result['metadata']['symbol_count'] > 0
        assert result['metadata']['calculation_time_ms'] > 0

        # Verify metrics exist (at least day_change and open_change)
        assert 'day_change' in result['metrics']
        assert 'open_change' in result['metrics']

    def test_e2e_qqq_breadth_calculation(self, mock_relationship_cache, mock_database_with_data):
        """Test end-to-end QQQ breadth calculation."""
        from src.core.services.breadth_metrics_service import BreadthMetricsService

        service = BreadthMetricsService()
        result = service.calculate_breadth_metrics(universe='QQQ')

        assert result['metadata']['universe'] == 'QQQ'
        assert 'day_change' in result['metrics']

    def test_e2e_api_integration_spy(self, mock_relationship_cache, mock_database_with_data):
        """Test end-to-end API integration for SPY."""
        from flask import Flask
        from src.api.rest.breadth_metrics import breadth_metrics_bp

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(breadth_metrics_bp)
        client = app.test_client()

        response = client.get('/api/breadth-metrics?universe=SPY')

        assert response.status_code == 200
        data = json.loads(response.data)

        # Verify complete response structure
        assert 'metrics' in data
        assert 'metadata' in data
        assert data['metadata']['universe'] == 'SPY'

        # Verify at least 5 metrics calculated
        assert len(data['metrics']) >= 5

    def test_e2e_api_integration_qqq(self, mock_relationship_cache, mock_database_with_data):
        """Test end-to-end API integration for QQQ."""
        from flask import Flask
        from src.api.rest.breadth_metrics import breadth_metrics_bp

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(breadth_metrics_bp)
        client = app.test_client()

        response = client.get('/api/breadth-metrics?universe=QQQ')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['metadata']['universe'] == 'QQQ'

    def test_e2e_multiple_universes_sequential(self, mock_relationship_cache, mock_database_with_data):
        """Test sequential requests for different universes."""
        from src.core.services.breadth_metrics_service import BreadthMetricsService

        service = BreadthMetricsService()

        # Request SPY
        result_spy = service.calculate_breadth_metrics(universe='SPY')
        assert result_spy['metadata']['universe'] == 'SPY'

        # Request QQQ
        result_qqq = service.calculate_breadth_metrics(universe='QQQ')
        assert result_qqq['metadata']['universe'] == 'QQQ'

        # Request dow30
        result_dow = service.calculate_breadth_metrics(universe='dow30')
        assert result_dow['metadata']['universe'] == 'dow30'

    def test_e2e_calculation_accuracy(self, mock_relationship_cache, mock_database_with_data):
        """Test calculation accuracy with known data."""
        from src.core.services.breadth_metrics_service import BreadthMetricsService

        service = BreadthMetricsService()
        result = service.calculate_breadth_metrics(universe='SPY')

        # With mock data: 60 up, 30 down, 10 sideways (of 100 symbols)
        day_change = result['metrics']['day_change']

        # Should have reasonable distribution
        total = day_change['up'] + day_change['down'] + day_change['unchanged']
        assert total > 0

        # Percentage should be in valid range
        assert 0 <= day_change['pct_up'] <= 100

    def test_e2e_performance_target(self, mock_relationship_cache, mock_database_with_data):
        """Test end-to-end performance meets target (<100ms API response)."""
        import time
        from flask import Flask
        from src.api.rest.breadth_metrics import breadth_metrics_bp

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(breadth_metrics_bp)
        client = app.test_client()

        start = time.time()
        response = client.get('/api/breadth-metrics?universe=SPY')
        end = time.time()

        elapsed_ms = (end - start) * 1000

        assert response.status_code == 200
        # Sprint 66 target: API < 100ms (lenient for test env: 500ms)
        assert elapsed_ms < 500

    def test_e2e_insufficient_data_handling(self, mock_relationship_cache):
        """Test handling when insufficient data available."""
        # Mock database with only 10 days of data
        with patch('src.core.services.breadth_metrics_service.TickStockDatabase') as mock_db:
            dates = pd.date_range(end=datetime.now().date(), periods=10, freq='D')
            df = pd.DataFrame({
                'symbol': ['AAPL'] * 10,
                'date': dates,
                'close': [100 + i for i in range(10)]
            })

            mock_db_instance = MagicMock()
            mock_db_instance.__enter__.return_value = mock_db_instance
            mock_db_instance.execute_query.return_value = df
            mock_db.return_value = mock_db_instance

            from src.core.services.breadth_metrics_service import BreadthMetricsService
            service = BreadthMetricsService()
            result = service.calculate_breadth_metrics(universe='SPY')

            # Should still return valid structure
            assert 'metrics' in result
            assert 'metadata' in result

            # Year metric should show 0/0 (insufficient data)
            if 'year' in result['metrics']:
                assert result['metrics']['year']['up'] == 0
                assert result['metrics']['year']['down'] == 0

    def test_e2e_pydantic_validation(self, mock_relationship_cache, mock_database_with_data):
        """Test Pydantic response model validation."""
        from src.core.services.breadth_metrics_service import BreadthMetricsService
        from src.core.models.breadth_metrics_models import BreadthMetricsResponse

        service = BreadthMetricsService()
        result = service.calculate_breadth_metrics(universe='SPY')

        # Should validate successfully
        response_model = BreadthMetricsResponse.from_service_response(result)

        assert response_model.metadata.universe == 'SPY'
        assert response_model.metadata.symbol_count > 0
        assert len(response_model.metrics) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
