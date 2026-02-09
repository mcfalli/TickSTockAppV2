"""
Unit tests for discovery API routes.

Sprint 71: REST API Endpoints - Discovery route tests
"""

import json
import unittest
from unittest.mock import Mock, patch, MagicMock

from src.api.routes.discovery_routes import discovery_bp
from src.api.models.analysis_models import (
    IndicatorsListResponse,
    PatternsListResponse,
    CapabilitiesResponse,
)


class TestDiscoveryRoutes(unittest.TestCase):
    """Test discovery API routes."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a minimal Flask app for testing
        from flask import Flask
        self.app = Flask(__name__)
        self.app.register_blueprint(discovery_bp)
        self.client = self.app.test_client()

    def test_health_check(self):
        """Test health check endpoint."""
        response = self.client.get('/api/discovery/health')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertEqual(data['status'], 'healthy')
        self.assertEqual(data['service'], 'discovery')
        self.assertIn('timestamp', data)

    @patch('src.api.routes.discovery_routes.IndicatorLoader')
    def test_list_indicators_success(self, mock_loader_class):
        """Test list indicators endpoint with successful response."""
        # Mock the loader
        mock_loader = MagicMock()
        mock_loader_class.return_value = mock_loader

        mock_loader.get_available_indicators.return_value = {
            'sma': {'category': 'trend', 'name': 'Simple Moving Average'},
            'ema': {'category': 'trend', 'name': 'Exponential Moving Average'},
            'rsi': {'category': 'momentum', 'name': 'Relative Strength Index'},
            'macd': {'category': 'momentum', 'name': 'MACD'},
            'atr': {'category': 'volatility', 'name': 'Average True Range'},
            'bollinger_bands': {'category': 'volatility', 'name': 'Bollinger Bands'},
        }

        response = self.client.get('/api/indicators/available')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertEqual(data['total_count'], 6)
        self.assertIn('trend', data['indicators'])
        self.assertIn('momentum', data['indicators'])
        self.assertIn('volatility', data['indicators'])
        self.assertEqual(len(data['indicators']['trend']), 2)
        self.assertEqual(len(data['indicators']['momentum']), 2)
        self.assertEqual(len(data['indicators']['volatility']), 2)
        self.assertIn('trend', data['categories'])

    @patch('src.api.routes.discovery_routes.IndicatorLoader')
    def test_list_indicators_empty(self, mock_loader_class):
        """Test list indicators endpoint with no indicators."""
        # Mock empty loader
        mock_loader = MagicMock()
        mock_loader_class.return_value = mock_loader
        mock_loader.get_available_indicators.return_value = {}

        response = self.client.get('/api/indicators/available')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertEqual(data['total_count'], 0)
        self.assertEqual(len(data['indicators']), 0)
        self.assertEqual(len(data['categories']), 0)

    @patch('src.api.routes.discovery_routes.IndicatorLoader')
    def test_list_indicators_error(self, mock_loader_class):
        """Test list indicators endpoint with error."""
        # Mock loader that raises exception
        mock_loader = MagicMock()
        mock_loader_class.return_value = mock_loader
        mock_loader.get_available_indicators.side_effect = Exception("Test error")

        response = self.client.get('/api/indicators/available')
        self.assertEqual(response.status_code, 500)

        data = json.loads(response.data)
        self.assertEqual(data['error'], 'InternalServerError')
        self.assertIn('Failed to list indicators', data['message'])

    @patch('src.api.routes.discovery_routes.PatternDetectionService')
    def test_list_patterns_success(self, mock_service_class):
        """Test list patterns endpoint with successful response."""
        # Mock the service
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service

        mock_service.get_available_patterns.return_value = {
            'doji': {'name': 'Doji', 'type': 'candlestick'},
            'hammer': {'name': 'Hammer', 'type': 'candlestick'},
            'engulfing': {'name': 'Engulfing', 'type': 'candlestick'},
            'morning_star': {'name': 'Morning Star', 'type': 'candlestick'},
            'evening_star': {'name': 'Evening Star', 'type': 'candlestick'},
            'three_white_soldiers': {'name': 'Three White Soldiers', 'type': 'candlestick'},
            'three_black_crows': {'name': 'Three Black Crows', 'type': 'candlestick'},
            'harami': {'name': 'Harami', 'type': 'candlestick'},
        }

        response = self.client.get('/api/patterns/available')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertEqual(data['total_count'], 8)
        self.assertIn('candlestick', data['patterns'])
        self.assertEqual(len(data['patterns']['candlestick']), 8)
        self.assertIn('candlestick', data['categories'])
        # Verify sorting
        self.assertEqual(sorted(data['patterns']['candlestick']), data['patterns']['candlestick'])

    @patch('src.api.routes.discovery_routes.PatternDetectionService')
    def test_list_patterns_empty(self, mock_service_class):
        """Test list patterns endpoint with no patterns."""
        # Mock empty service
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        mock_service.get_available_patterns.return_value = {}

        response = self.client.get('/api/patterns/available')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertEqual(data['total_count'], 0)
        # Still should have candlestick category, just empty
        self.assertIn('candlestick', data['patterns'])
        self.assertEqual(len(data['patterns']['candlestick']), 0)

    @patch('src.api.routes.discovery_routes.PatternDetectionService')
    def test_list_patterns_error(self, mock_service_class):
        """Test list patterns endpoint with error."""
        # Mock service that raises exception
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        mock_service.get_available_patterns.side_effect = Exception("Test error")

        response = self.client.get('/api/patterns/available')
        self.assertEqual(response.status_code, 500)

        data = json.loads(response.data)
        self.assertEqual(data['error'], 'InternalServerError')
        self.assertIn('Failed to list patterns', data['message'])

    @patch('src.api.routes.discovery_routes.PatternDetectionService')
    @patch('src.api.routes.discovery_routes.IndicatorLoader')
    def test_get_capabilities_success(self, mock_loader_class, mock_service_class):
        """Test get capabilities endpoint with successful response."""
        # Mock indicator loader
        mock_loader = MagicMock()
        mock_loader_class.return_value = mock_loader
        mock_loader.get_available_indicators.return_value = {
            'sma': {'category': 'trend'},
            'ema': {'category': 'trend'},
            'adx': {'category': 'trend'},
            'rsi': {'category': 'momentum'},
            'macd': {'category': 'momentum'},
            'stochastic': {'category': 'momentum'},
            'atr': {'category': 'volatility'},
            'bollinger_bands': {'category': 'volatility'},
        }

        # Mock pattern service
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        mock_service.get_available_patterns.return_value = {
            'doji': {}, 'hammer': {}, 'engulfing': {},
            'morning_star': {}, 'evening_star': {},
            'three_white_soldiers': {}, 'three_black_crows': {},
            'harami': {},
        }

        response = self.client.get('/api/analysis/capabilities')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertEqual(data['version'], '2.0.0')
        self.assertEqual(data['indicators']['trend'], 3)
        self.assertEqual(data['indicators']['momentum'], 3)
        self.assertEqual(data['indicators']['volatility'], 2)
        self.assertEqual(data['patterns']['candlestick'], 8)
        self.assertIn('daily', data['supported_timeframes'])
        self.assertIn('weekly', data['supported_timeframes'])
        self.assertIn('hourly', data['supported_timeframes'])
        self.assertIn('performance_stats', data)
        self.assertIn('avg_indicator_time_ms', data['performance_stats'])
        self.assertIn('avg_pattern_time_ms', data['performance_stats'])

    @patch('src.api.routes.discovery_routes.PatternDetectionService')
    @patch('src.api.routes.discovery_routes.IndicatorLoader')
    def test_get_capabilities_error(self, mock_loader_class, mock_service_class):
        """Test get capabilities endpoint with error."""
        # Mock loader that raises exception
        mock_loader = MagicMock()
        mock_loader_class.return_value = mock_loader
        mock_loader.get_available_indicators.side_effect = Exception("Test error")

        response = self.client.get('/api/analysis/capabilities')
        self.assertEqual(response.status_code, 500)

        data = json.loads(response.data)
        self.assertEqual(data['error'], 'InternalServerError')
        self.assertIn('Failed to get capabilities', data['message'])


if __name__ == '__main__':
    unittest.main()
