"""
API tests for /api/breadth-metrics endpoint.

Tests the Flask REST API endpoint for market breadth metrics:
- Success cases (200)
- Validation errors (400)
- Server errors (500)
- Universe parameter handling
- Response schema validation

Sprint 66: Market Breadth Metrics
"""

import pytest
import json
from unittest.mock import Mock, patch
from flask import Flask
from src.api.rest.breadth_metrics import breadth_metrics_bp


class TestBreadthMetricsAPI:
    """Test suite for breadth metrics API endpoint."""

    @pytest.fixture
    def app(self):
        """Create Flask app with breadth_metrics_bp registered."""
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(breadth_metrics_bp)
        return app

    @pytest.fixture
    def client(self, app):
        """Create Flask test client."""
        return app.test_client()

    @pytest.fixture
    def mock_service_success(self):
        """Mock BreadthMetricsService with successful response."""
        mock_result = {
            'metrics': {
                'day_change': {'up': 400, 'down': 103, 'unchanged': 0, 'pct_up': 79.52},
                'open_change': {'up': 364, 'down': 137, 'unchanged': 0, 'pct_up': 72.37},
                'week': {'up': 332, 'down': 170, 'unchanged': 0, 'pct_up': 66.0},
                'month': {'up': 329, 'down': 174, 'unchanged': 0, 'pct_up': 65.41},
                'quarter': {'up': 356, 'down': 146, 'unchanged': 0, 'pct_up': 70.92},
                'half_year': {'up': 333, 'down': 167, 'unchanged': 0, 'pct_up': 66.6},
                'year': {'up': 0, 'down': 0, 'unchanged': 0, 'pct_up': 0.0},
                'price_to_ema10': {'up': 352, 'down': 151, 'unchanged': 0, 'pct_up': 69.98},
                'price_to_ema20': {'up': 348, 'down': 155, 'unchanged': 0, 'pct_up': 69.18},
                'price_to_sma50': {'up': 342, 'down': 161, 'unchanged': 0, 'pct_up': 67.99},
                'price_to_sma200': {'up': 0, 'down': 0, 'unchanged': 0, 'pct_up': 0.0},
            },
            'metadata': {
                'universe': 'SPY',
                'symbol_count': 503,
                'calculation_time_ms': 45.2,
                'calculated_at': '2026-02-07T12:00:00Z'
            }
        }
        return mock_result

    def test_get_breadth_metrics_success_spy(self, client, mock_service_success):
        """Test GET /api/breadth-metrics?universe=SPY returns 200."""
        with patch('src.api.rest.breadth_metrics.BreadthMetricsService') as mock_service:
            mock_service.return_value.calculate_breadth_metrics.return_value = mock_service_success

            response = client.get('/api/breadth-metrics?universe=SPY')

            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'metrics' in data
            assert 'metadata' in data
            assert data['metadata']['universe'] == 'SPY'
            assert data['metadata']['symbol_count'] == 503

    def test_get_breadth_metrics_success_qqq(self, client, mock_service_success):
        """Test GET /api/breadth-metrics?universe=QQQ returns 200."""
        mock_service_success['metadata']['universe'] = 'QQQ'
        mock_service_success['metadata']['symbol_count'] = 102

        with patch('src.api.rest.breadth_metrics.BreadthMetricsService') as mock_service:
            mock_service.return_value.calculate_breadth_metrics.return_value = mock_service_success

            response = client.get('/api/breadth-metrics?universe=QQQ')

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['metadata']['universe'] == 'QQQ'
            assert data['metadata']['symbol_count'] == 102

    def test_get_breadth_metrics_default_universe(self, client, mock_service_success):
        """Test GET /api/breadth-metrics without universe param defaults to SPY."""
        with patch('src.api.rest.breadth_metrics.BreadthMetricsService') as mock_service:
            mock_service.return_value.calculate_breadth_metrics.return_value = mock_service_success

            response = client.get('/api/breadth-metrics')

            assert response.status_code == 200
            # Should use default SPY
            mock_service.return_value.calculate_breadth_metrics.assert_called_with(universe='SPY')

    def test_get_breadth_metrics_response_schema(self, client, mock_service_success):
        """Test response contains all required fields."""
        with patch('src.api.rest.breadth_metrics.BreadthMetricsService') as mock_service:
            mock_service.return_value.calculate_breadth_metrics.return_value = mock_service_success

            response = client.get('/api/breadth-metrics?universe=SPY')
            data = json.loads(response.data)

            # Check metrics structure
            assert 'metrics' in data
            assert len(data['metrics']) >= 7  # At least 7 metrics

            # Check each metric has required fields
            for metric_name, metric_data in data['metrics'].items():
                assert 'up' in metric_data
                assert 'down' in metric_data
                assert 'unchanged' in metric_data
                assert 'pct_up' in metric_data

            # Check metadata structure
            assert 'metadata' in data
            assert 'universe' in data['metadata']
            assert 'symbol_count' in data['metadata']
            assert 'calculation_time_ms' in data['metadata']
            assert 'calculated_at' in data['metadata']

    def test_get_breadth_metrics_invalid_universe_empty(self, client):
        """Test empty universe parameter returns 400."""
        response = client.get('/api/breadth-metrics?universe=')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_get_breadth_metrics_validation_error(self, client):
        """Test Pydantic validation error returns 400."""
        with patch('src.api.rest.breadth_metrics.BreadthMetricsRequest') as mock_request:
            from pydantic import ValidationError
            mock_request.side_effect = ValidationError.from_exception_data(
                'test',
                [{'type': 'value_error', 'loc': ('universe',), 'msg': 'Invalid universe'}]
            )

            response = client.get('/api/breadth-metrics?universe=INVALID')

            assert response.status_code == 400
            data = json.loads(response.data)
            assert 'error' in data
            assert data['error'] == 'ValidationError'

    def test_get_breadth_metrics_value_error(self, client):
        """Test ValueError returns 400."""
        with patch('src.api.rest.breadth_metrics.BreadthMetricsService') as mock_service:
            mock_service.return_value.calculate_breadth_metrics.side_effect = ValueError('Invalid input')

            response = client.get('/api/breadth-metrics?universe=SPY')

            assert response.status_code == 400
            data = json.loads(response.data)
            assert 'error' in data
            assert data['error'] == 'ValueError'
            assert 'Invalid input' in data['message']

    def test_get_breadth_metrics_runtime_error(self, client):
        """Test RuntimeError returns 500."""
        with patch('src.api.rest.breadth_metrics.BreadthMetricsService') as mock_service:
            mock_service.return_value.calculate_breadth_metrics.side_effect = RuntimeError('Database error')

            response = client.get('/api/breadth-metrics?universe=SPY')

            assert response.status_code == 500
            data = json.loads(response.data)
            assert 'error' in data
            assert data['error'] == 'RuntimeError'
            assert 'Database error' in data['message']

    def test_get_breadth_metrics_generic_exception(self, client):
        """Test generic Exception returns 500."""
        with patch('src.api.rest.breadth_metrics.BreadthMetricsService') as mock_service:
            mock_service.return_value.calculate_breadth_metrics.side_effect = Exception('Unexpected error')

            response = client.get('/api/breadth-metrics?universe=SPY')

            assert response.status_code == 500
            data = json.loads(response.data)
            assert 'error' in data

    def test_get_breadth_metrics_content_type(self, client, mock_service_success):
        """Test response Content-Type is application/json."""
        with patch('src.api.rest.breadth_metrics.BreadthMetricsService') as mock_service:
            mock_service.return_value.calculate_breadth_metrics.return_value = mock_service_success

            response = client.get('/api/breadth-metrics?universe=SPY')

            assert response.status_code == 200
            assert 'application/json' in response.content_type

    def test_get_breadth_metrics_calculation_time(self, client, mock_service_success):
        """Test calculation_time_ms is included and reasonable."""
        with patch('src.api.rest.breadth_metrics.BreadthMetricsService') as mock_service:
            mock_service.return_value.calculate_breadth_metrics.return_value = mock_service_success

            response = client.get('/api/breadth-metrics?universe=SPY')
            data = json.loads(response.data)

            assert 'calculation_time_ms' in data['metadata']
            assert data['metadata']['calculation_time_ms'] > 0
            # Should be fast (Sprint 66 target: <50ms)
            assert data['metadata']['calculation_time_ms'] < 200  # Lenient for test

    def test_get_breadth_metrics_universe_case_insensitive(self, client, mock_service_success):
        """Test universe parameter is case-insensitive (uppercase normalization)."""
        with patch('src.api.rest.breadth_metrics.BreadthMetricsService') as mock_service:
            mock_service.return_value.calculate_breadth_metrics.return_value = mock_service_success

            # Test lowercase input
            response = client.get('/api/breadth-metrics?universe=spy')

            assert response.status_code == 200
            # Service should be called with uppercase
            mock_service.return_value.calculate_breadth_metrics.assert_called_with(universe='SPY')

    def test_get_breadth_metrics_dow30_universe(self, client, mock_service_success):
        """Test dow30 universe is supported."""
        mock_service_success['metadata']['universe'] = 'dow30'
        mock_service_success['metadata']['symbol_count'] = 30

        with patch('src.api.rest.breadth_metrics.BreadthMetricsService') as mock_service:
            mock_service.return_value.calculate_breadth_metrics.return_value = mock_service_success

            response = client.get('/api/breadth-metrics?universe=dow30')

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['metadata']['universe'] == 'dow30'

    def test_get_breadth_metrics_nasdaq100_universe(self, client, mock_service_success):
        """Test nasdaq100 universe is supported."""
        mock_service_success['metadata']['universe'] = 'nasdaq100'
        mock_service_success['metadata']['symbol_count'] = 102

        with patch('src.api.rest.breadth_metrics.BreadthMetricsService') as mock_service:
            mock_service.return_value.calculate_breadth_metrics.return_value = mock_service_success

            response = client.get('/api/breadth-metrics?universe=nasdaq100')

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['metadata']['universe'] == 'nasdaq100'

    def test_get_breadth_metrics_percentages_valid_range(self, client, mock_service_success):
        """Test all percentage values are in valid range [0, 100]."""
        with patch('src.api.rest.breadth_metrics.BreadthMetricsService') as mock_service:
            mock_service.return_value.calculate_breadth_metrics.return_value = mock_service_success

            response = client.get('/api/breadth-metrics?universe=SPY')
            data = json.loads(response.data)

            for metric_name, metric_data in data['metrics'].items():
                pct = metric_data['pct_up']
                assert 0 <= pct <= 100, f"{metric_name} pct_up out of range: {pct}"

    def test_get_breadth_metrics_counts_non_negative(self, client, mock_service_success):
        """Test all count values are non-negative."""
        with patch('src.api.rest.breadth_metrics.BreadthMetricsService') as mock_service:
            mock_service.return_value.calculate_breadth_metrics.return_value = mock_service_success

            response = client.get('/api/breadth-metrics?universe=SPY')
            data = json.loads(response.data)

            for metric_name, metric_data in data['metrics'].items():
                assert metric_data['up'] >= 0
                assert metric_data['down'] >= 0
                assert metric_data['unchanged'] >= 0

    def test_method_not_allowed(self, client):
        """Test POST method is not allowed."""
        response = client.post('/api/breadth-metrics')
        assert response.status_code == 405  # Method Not Allowed

    def test_put_method_not_allowed(self, client):
        """Test PUT method is not allowed."""
        response = client.put('/api/breadth-metrics')
        assert response.status_code == 405  # Method Not Allowed


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
