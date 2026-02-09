"""
Unit tests for analysis API routes.

Sprint 71: REST API Endpoints - Analysis route tests
"""

import json
import unittest
from unittest.mock import Mock, patch, MagicMock

import pandas as pd
from datetime import datetime

from src.api.routes.analysis_routes import analysis_bp
from src.api.models.analysis_models import SymbolAnalysisResponse


class TestAnalysisRoutes(unittest.TestCase):
    """Test analysis API routes."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a minimal Flask app for testing
        from flask import Flask
        self.app = Flask(__name__)
        self.app.register_blueprint(analysis_bp)
        self.client = self.app.test_client()

    def test_health_check(self):
        """Test health check endpoint."""
        response = self.client.get('/api/analysis/health')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertEqual(data['status'], 'healthy')
        self.assertEqual(data['service'], 'analysis')
        self.assertIn('timestamp', data)

    @patch('src.api.routes.analysis_routes.AnalysisService')
    def test_analyze_symbol_valid_request(self, mock_service_class):
        """Test single symbol analysis with valid request."""
        # Mock the analysis service
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service

        mock_service.analyze_symbol.return_value = {
            'indicators': {
                'sma': {'value': 150.5, 'value_data': {'sma_20': 150.5}},
                'rsi': {'value': 65.3, 'value_data': {'rsi_14': 65.3}}
            },
            'patterns': {
                'doji': {'detected': True, 'confidence': 0.85}
            }
        }

        # Make request
        request_data = {
            'symbol': 'AAPL',
            'timeframe': 'daily',
            'indicators': ['sma', 'rsi'],
            'patterns': ['doji'],
            'calculate_all': False
        }

        response = self.client.post(
            '/api/analysis/symbol',
            data=json.dumps(request_data),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertEqual(data['symbol'], 'AAPL')
        self.assertEqual(data['timeframe'], 'daily')
        self.assertIn('indicators', data)
        self.assertIn('patterns', data)
        self.assertIn('metadata', data)

    def test_analyze_symbol_invalid_request(self):
        """Test single symbol analysis with invalid request."""
        # Missing symbol
        request_data = {
            'timeframe': 'daily'
        }

        response = self.client.post(
            '/api/analysis/symbol',
            data=json.dumps(request_data),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['error'], 'ValidationError')

    def test_analyze_symbol_invalid_timeframe(self):
        """Test single symbol analysis with invalid timeframe."""
        request_data = {
            'symbol': 'AAPL',
            'timeframe': 'invalid_timeframe'
        }

        response = self.client.post(
            '/api/analysis/symbol',
            data=json.dumps(request_data),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['error'], 'ValidationError')

    @patch('src.api.routes.analysis_routes.get_relationship_cache')
    @patch('src.api.routes.analysis_routes.AnalysisService')
    def test_analyze_universe_valid_request(self, mock_service_class, mock_cache):
        """Test universe analysis with valid request."""
        # Mock the cache
        mock_cache_instance = MagicMock()
        mock_cache.return_value = mock_cache_instance
        mock_cache_instance.get_universe_symbols.return_value = ['AAPL', 'MSFT', 'GOOGL']

        # Mock the analysis service
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service

        mock_service.analyze_symbol.return_value = {
            'indicators': {'sma': {'value': 150.5}},
            'patterns': {}
        }

        # Make request
        request_data = {
            'universe_key': 'test_universe',
            'timeframe': 'daily',
            'indicators': ['sma'],
            'max_symbols': 10
        }

        response = self.client.post(
            '/api/analysis/universe',
            data=json.dumps(request_data),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertEqual(data['universe_key'], 'test_universe')
        self.assertEqual(data['symbols_analyzed'], 3)
        self.assertIn('results', data)
        self.assertIn('summary', data)

    @patch('src.api.routes.analysis_routes.get_relationship_cache')
    def test_analyze_universe_not_found(self, mock_cache):
        """Test universe analysis with non-existent universe."""
        # Mock empty cache response
        mock_cache_instance = MagicMock()
        mock_cache.return_value = mock_cache_instance
        mock_cache_instance.get_universe_symbols.return_value = []

        request_data = {
            'universe_key': 'nonexistent_universe',
            'timeframe': 'daily'
        }

        response = self.client.post(
            '/api/analysis/universe',
            data=json.dumps(request_data),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertEqual(data['error'], 'NotFoundError')

    def test_validate_data_csv_valid(self):
        """Test data validation with valid CSV."""
        csv_data = """timestamp,open,high,low,close,volume
2025-01-01,100,102,99,101,1000000
2025-01-02,101,103,100,102,1100000
2025-01-03,102,104,101,103,1200000"""

        request_data = {
            'data': csv_data,
            'format': 'csv'
        }

        response = self.client.post(
            '/api/analysis/validate-data',
            data=json.dumps(request_data),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertTrue(data['is_valid'])
        self.assertEqual(data['data_points'], 3)
        self.assertEqual(len(data['errors']), 0)
        self.assertIn('timestamp', data['columns_found'])

    def test_validate_data_missing_columns(self):
        """Test data validation with missing required columns."""
        csv_data = """timestamp,close
2025-01-01,100
2025-01-02,101"""

        request_data = {
            'data': csv_data,
            'format': 'csv'
        }

        response = self.client.post(
            '/api/analysis/validate-data',
            data=json.dumps(request_data),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertFalse(data['is_valid'])
        self.assertGreater(len(data['errors']), 0)

    def test_validate_data_invalid_format(self):
        """Test data validation with invalid format."""
        request_data = {
            'data': 'invalid data',
            'format': 'invalid_format'
        }

        response = self.client.post(
            '/api/analysis/validate-data',
            data=json.dumps(request_data),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)


if __name__ == '__main__':
    unittest.main()
