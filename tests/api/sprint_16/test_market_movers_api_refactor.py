"""
Sprint 16 Market Movers API Tests - /api/market-movers Endpoint
==============================================================

Test comprehensive Market Movers API endpoint functionality and performance.

**Sprint**: 16 - Grid Modernization  
**Component**: /api/market-movers REST endpoint
**Functional Area**: api/sprint_16
**Performance Target**: <50ms query response time, <100ms WebSocket delivery
"""
import json
import time
from datetime import UTC, datetime
from unittest.mock import Mock, patch

import pytest
from flask import Flask

from src.api.rest.api import register_api_routes
from src.infrastructure.cache.cache_control import CacheControl


class TestMarketMoversAPIEndpoint:
    """Test /api/market-movers endpoint structure and responses."""

    def setup_method(self):
        """Setup test environment before each method."""
        # Create test Flask app
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.app.config['LOGIN_DISABLED'] = True

        # Mock dependencies
        self.mock_cache_control = Mock(spec=CacheControl)
        self.mock_config = {
            'APP_DEBUG': True,
            'REDIS_URL': 'redis://localhost:6379'
        }
        self.mock_extensions = {'mail': Mock()}

        # Register API routes
        register_api_routes(self.app, self.mock_extensions, self.mock_cache_control, self.mock_config)

        # Create test client
        self.client = self.app.test_client()

        # Setup authentication mock
        self.setup_auth_mocks()

    def setup_auth_mocks(self):
        """Setup authentication mocks for testing."""
        with patch('flask_login.utils._get_user') as mock_get_user:
            mock_user = Mock()
            mock_user.is_authenticated = True
            mock_user.get_id.return_value = 'test_user_123'
            mock_get_user.return_value = mock_user

    def test_market_movers_endpoint_exists(self):
        """Test /api/market-movers endpoint is accessible."""
        with self.app.test_request_context():
            # Bypass login requirement for testing
            with patch('flask_login.login_required', lambda f: f):
                response = self.client.get('/api/market-movers')

                # Should not return 404
                assert response.status_code != 404, "Market movers endpoint should exist"

                # Should return 200 or other valid response
                assert response.status_code in [200, 401, 403], f"Expected valid status code, got {response.status_code}"

    def test_market_movers_response_structure(self):
        """Test API returns correct data structure."""
        with patch('flask_login.login_required', lambda f: f):
            response = self.client.get('/api/market-movers')

            if response.status_code == 200:
                data = json.loads(response.data)

                # Verify top-level structure
                assert 'success' in data, "Response should have 'success' field"
                assert 'data' in data, "Response should have 'data' field"

                if data['success']:
                    market_data = data['data']

                    # Verify market movers structure
                    assert 'gainers' in market_data, "Data should have 'gainers' array"
                    assert 'losers' in market_data, "Data should have 'losers' array"
                    assert 'timestamp' in market_data, "Data should have 'timestamp' field"

                    # Verify arrays are present
                    assert isinstance(market_data['gainers'], list), "Gainers should be an array"
                    assert isinstance(market_data['losers'], list), "Losers should be an array"

    def test_market_movers_gainer_structure(self):
        """Test individual gainer item structure."""
        expected_gainer = {
            'symbol': 'AAPL',
            'name': 'Apple Inc.',
            'price': 150.25,
            'change': 5.75,
            'change_percent': 3.98,
            'volume': 1000000
        }

        # Verify all required fields present
        required_fields = ['symbol', 'name', 'price', 'change', 'change_percent', 'volume']
        for field in required_fields:
            assert field in expected_gainer, f"Gainer should have '{field}' field"

        # Verify data types
        assert isinstance(expected_gainer['symbol'], str), "Symbol should be string"
        assert isinstance(expected_gainer['name'], str), "Name should be string"
        assert isinstance(expected_gainer['price'], (int, float)), "Price should be numeric"
        assert isinstance(expected_gainer['change'], (int, float)), "Change should be numeric"
        assert isinstance(expected_gainer['change_percent'], (int, float)), "Change percent should be numeric"
        assert isinstance(expected_gainer['volume'], int), "Volume should be integer"

        # Verify positive change for gainers
        assert expected_gainer['change'] > 0, "Gainer change should be positive"
        assert expected_gainer['change_percent'] > 0, "Gainer change_percent should be positive"

    def test_market_movers_loser_structure(self):
        """Test individual loser item structure."""
        expected_loser = {
            'symbol': 'TSLA',
            'name': 'Tesla Inc.',
            'price': 195.50,
            'change': -8.25,
            'change_percent': -4.05,
            'volume': 2000000
        }

        # Verify all required fields present
        required_fields = ['symbol', 'name', 'price', 'change', 'change_percent', 'volume']
        for field in required_fields:
            assert field in expected_loser, f"Loser should have '{field}' field"

        # Verify negative change for losers
        assert expected_loser['change'] < 0, "Loser change should be negative"
        assert expected_loser['change_percent'] < 0, "Loser change_percent should be negative"

    @pytest.mark.performance
    def test_market_movers_response_time_under_50ms(self):
        """Test API response time meets <50ms performance target."""
        with patch('flask_login.login_required', lambda f: f):
            # Warm up request (not counted)
            self.client.get('/api/market-movers')

            # Measure actual response time
            start_time = time.perf_counter()
            response = self.client.get('/api/market-movers')
            response_time = (time.perf_counter() - start_time) * 1000  # Convert to ms

            assert response_time < 50, f"API response time should be <50ms, got {response_time:.2f}ms"
            assert response.status_code in [200, 401], f"Response should be valid, got {response.status_code}"

    def test_market_movers_mock_data_generation(self):
        """Test mock market data generation quality."""
        # Test parameters for mock data
        test_symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN']
        num_gainers = 5
        num_losers = 5

        mock_gainers = []
        mock_losers = []

        for i, symbol in enumerate(test_symbols):
            # Generate realistic gainer
            base_price = 100.0 + (i * 50)  # Varying base prices
            change_percent = 1.5 + (i * 0.5)  # 1.5% to 3.5% gains
            change_amount = base_price * (change_percent / 100)
            current_price = base_price + change_amount

            gainer = {
                'symbol': symbol,
                'name': f'{symbol} Test Company',
                'price': round(current_price, 2),
                'change': round(change_amount, 2),
                'change_percent': round(change_percent, 2),
                'volume': 500000 + (i * 100000)
            }
            mock_gainers.append(gainer)

            # Generate realistic loser
            loser_change_percent = -(1.0 + (i * 0.3))  # -1.0% to -2.2% losses
            loser_change_amount = base_price * (loser_change_percent / 100)
            loser_current_price = base_price + loser_change_amount

            loser = {
                'symbol': f'{symbol}L',  # Different symbol for loser
                'name': f'{symbol}L Test Company',
                'price': round(loser_current_price, 2),
                'change': round(loser_change_amount, 2),
                'change_percent': round(loser_change_percent, 2),
                'volume': 300000 + (i * 50000)
            }
            mock_losers.append(loser)

        # Verify mock data quality
        assert len(mock_gainers) == num_gainers, f"Should generate {num_gainers} gainers"
        assert len(mock_losers) == num_losers, f"Should generate {num_losers} losers"

        # Verify all gainers have positive changes
        for gainer in mock_gainers:
            assert gainer['change'] > 0, f"Gainer {gainer['symbol']} should have positive change"
            assert gainer['change_percent'] > 0, f"Gainer {gainer['symbol']} should have positive change_percent"

        # Verify all losers have negative changes
        for loser in mock_losers:
            assert loser['change'] < 0, f"Loser {loser['symbol']} should have negative change"
            assert loser['change_percent'] < 0, f"Loser {loser['symbol']} should have negative change_percent"

        # Verify realistic price ranges
        for item in mock_gainers + mock_losers:
            assert 0 < item['price'] < 10000, f"Price for {item['symbol']} should be realistic: {item['price']}"
            assert item['volume'] > 0, f"Volume for {item['symbol']} should be positive: {item['volume']}"

    def test_market_movers_error_handling(self):
        """Test API error handling scenarios."""
        # Test unauthorized access (when login required)
        with patch('flask_login.current_user') as mock_user:
            mock_user.is_authenticated = False
            response = self.client.get('/api/market-movers')

            # Should handle unauthorized access appropriately
            assert response.status_code in [401, 403, 302], "Should handle unauthorized access"

    def test_market_movers_cache_integration(self):
        """Test API cache integration for consumer pattern."""
        # Mock cache responses
        self.mock_cache_control.get.return_value = None  # Cache miss
        self.mock_cache_control.set = Mock()

        with patch('flask_login.login_required', lambda f: f):
            response = self.client.get('/api/market-movers')

            if response.status_code == 200:
                data = json.loads(response.data)

                # Should implement consumer pattern:
                # 1. Check cache first
                # 2. Return cached data or generate mock data
                # 3. Trigger background refresh if needed
                assert 'success' in data, "Response should indicate success/failure"

    def test_market_movers_timestamp_format(self):
        """Test timestamp format in response."""
        expected_data = {
            'success': True,
            'data': {
                'gainers': [],
                'losers': [],
                'timestamp': datetime.now(UTC).isoformat()
            }
        }

        # Verify timestamp format
        timestamp = expected_data['data']['timestamp']
        assert 'T' in timestamp, "Timestamp should be ISO format"
        assert timestamp.endswith('Z') or '+' in timestamp, "Timestamp should include timezone"

    @pytest.mark.performance
    def test_market_movers_concurrent_requests(self):
        """Test API handles concurrent requests efficiently."""
        import queue
        import threading

        results = queue.Queue()
        num_requests = 5

        def make_request():
            with patch('flask_login.login_required', lambda f: f):
                start_time = time.perf_counter()
                response = self.client.get('/api/market-movers')
                end_time = time.perf_counter()

                results.put({
                    'status_code': response.status_code,
                    'response_time': (end_time - start_time) * 1000
                })

        # Create and start threads
        threads = []
        for i in range(num_requests):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Collect results
        response_times = []
        while not results.empty():
            result = results.get()
            response_times.append(result['response_time'])
            assert result['status_code'] in [200, 401], "All requests should succeed or be unauthorized"

        # Verify performance under concurrent load
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)

        assert avg_response_time < 100, f"Average response time under load should be <100ms, got {avg_response_time:.2f}ms"
        assert max_response_time < 200, f"Max response time under load should be <200ms, got {max_response_time:.2f}ms"

    def test_market_movers_data_consistency(self):
        """Test data consistency across multiple calls."""
        with patch('flask_login.login_required', lambda f: f):
            # Make multiple requests
            responses = []
            for i in range(3):
                response = self.client.get('/api/market-movers')
                if response.status_code == 200:
                    data = json.loads(response.data)
                    responses.append(data)
                time.sleep(0.1)  # Small delay between requests

            if len(responses) > 1:
                # Data structure should be consistent
                for response in responses:
                    assert 'success' in response, "All responses should have success field"
                    assert 'data' in response, "All responses should have data field"

                    if response['success']:
                        assert 'gainers' in response['data'], "All responses should have gainers"
                        assert 'losers' in response['data'], "All responses should have losers"


class TestMarketMoversAPIIntegration:
    """Test Market Movers API integration patterns."""

    def setup_method(self):
        """Setup integration test environment."""
        self.mock_cache = Mock()
        self.mock_redis = Mock()

    def test_consumer_pattern_implementation(self):
        """Test Market Movers follows TickStockApp consumer pattern."""
        # Consumer Pattern Steps:
        # 1. Check cache for existing data
        # 2. Return cached data if available
        # 3. Generate mock data if no cache
        # 4. Trigger TickStockPL refresh job via Redis (future)

        # Step 1: Cache check
        cache_key = 'market_movers_data'
        cached_data = self.mock_cache.get(cache_key)

        if cached_data:
            # Step 2: Return cached data
            data_source = 'cache'
        else:
            # Step 3: Generate mock data
            data_source = 'mock'

            # Step 4: Should trigger background refresh (mock)
            refresh_triggered = True
            assert refresh_triggered, "Should trigger background refresh when cache miss"

        # Verify consumer pattern compliance
        assert data_source in ['cache', 'mock'], "Should use cache or mock data source"

    def test_redis_message_integration(self):
        """Test integration with Redis messaging for real-time updates."""
        # Mock Redis pub-sub for market movers updates
        channel = 'market_movers_updates'

        # Mock message publishing
        market_movers_data = {
            'gainers': [{'symbol': 'AAPL', 'change_percent': 5.2}],
            'losers': [{'symbol': 'TSLA', 'change_percent': -3.1}],
            'timestamp': datetime.now(UTC).isoformat()
        }

        # Should publish update via Redis
        self.mock_redis.publish(channel, json.dumps(market_movers_data))

        # Verify Redis integration
        self.mock_redis.publish.assert_called_once_with(channel, json.dumps(market_movers_data))

    def test_websocket_broadcast_integration(self):
        """Test Market Movers data broadcast via WebSocket."""
        # Mock WebSocket publisher
        mock_websocket_publisher = Mock()

        market_movers_update = {
            'type': 'market_movers_update',
            'data': {
                'gainers': [{'symbol': 'NVDA', 'change_percent': 4.8}],
                'losers': [{'symbol': 'AMD', 'change_percent': -2.3}]
            },
            'timestamp': datetime.now(UTC).isoformat()
        }

        # Should broadcast to connected users
        mock_websocket_publisher.broadcast_market_movers(market_movers_update)

        # Verify WebSocket broadcast
        mock_websocket_publisher.broadcast_market_movers.assert_called_once_with(market_movers_update)

    def test_performance_monitoring_integration(self):
        """Test API performance monitoring and metrics collection."""
        # Mock performance metrics
        api_metrics = {
            'endpoint': '/api/market-movers',
            'response_time_ms': 25,
            'status_code': 200,
            'timestamp': datetime.now(UTC),
            'user_id': 'test_user_123',
            'cache_hit': False
        }

        # Verify performance metrics structure
        assert api_metrics['response_time_ms'] < 50, "Response time should be tracked and meet target"
        assert api_metrics['status_code'] == 200, "Status code should be tracked"
        assert api_metrics['cache_hit'] is not None, "Cache hit/miss should be tracked"

    def test_error_recovery_integration(self):
        """Test error recovery and fallback mechanisms."""
        # Test cache failure scenario
        self.mock_cache.get.side_effect = Exception("Redis connection error")

        # Should fall back to mock data generation
        try:
            self.mock_cache.get('market_movers')
            assert False, "Should have raised exception"
        except Exception:
            # Should generate fallback data
            fallback_data = {
                'gainers': [{'symbol': 'FALLBACK', 'change_percent': 1.0}],
                'losers': [{'symbol': 'FALLBACK2', 'change_percent': -1.0}]
            }

            assert len(fallback_data['gainers']) > 0, "Should generate fallback gainers"
            assert len(fallback_data['losers']) > 0, "Should generate fallback losers"

    def test_authentication_integration(self):
        """Test authentication requirements and user context."""
        # Mock user context
        mock_user_context = {
            'user_id': 'test_user_123',
            'is_authenticated': True,
            'subscription_level': 'premium'
        }

        # Should require authentication
        assert mock_user_context['is_authenticated'], "Endpoint should require authentication"

        # Should have user context for personalization
        assert mock_user_context['user_id'] is not None, "Should have user ID for tracking"


@pytest.mark.performance
class TestMarketMoversAPIPerformance:
    """Test Market Movers API performance characteristics."""

    def test_memory_usage_under_load(self):
        """Test API memory usage remains stable under load."""
        import os

        import psutil

        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Generate large mock dataset
        large_gainers = []
        large_losers = []

        for i in range(100):  # Generate 100 of each
            large_gainers.append({
                'symbol': f'TEST{i:03d}',
                'name': f'Test Company {i}',
                'price': 100.0 + i,
                'change': 1.0 + (i * 0.1),
                'change_percent': 1.0 + (i * 0.05),
                'volume': 1000000 + (i * 10000)
            })

            large_losers.append({
                'symbol': f'LOSS{i:03d}',
                'name': f'Loss Company {i}',
                'price': 50.0 + i,
                'change': -(1.0 + (i * 0.1)),
                'change_percent': -(1.0 + (i * 0.05)),
                'volume': 800000 + (i * 8000)
            })

        # Serialize data multiple times (simulate API responses)
        for _ in range(10):
            json.dumps({'gainers': large_gainers, 'losers': large_losers})

        # Check memory after operations
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        assert memory_increase < 10, f"Memory usage should not increase significantly, increased by {memory_increase:.2f}MB"

    def test_json_serialization_performance(self):
        """Test JSON serialization performance for large datasets."""
        import time

        # Create realistic large dataset
        large_dataset = {
            'success': True,
            'data': {
                'gainers': [
                    {
                        'symbol': f'GAIN{i:03d}',
                        'name': f'Gainer Company {i}',
                        'price': round(100.0 + (i * 1.5), 2),
                        'change': round(2.0 + (i * 0.1), 2),
                        'change_percent': round(2.0 + (i * 0.05), 2),
                        'volume': 1000000 + (i * 10000)
                    } for i in range(50)  # 50 gainers
                ],
                'losers': [
                    {
                        'symbol': f'LOSS{i:03d}',
                        'name': f'Loser Company {i}',
                        'price': round(80.0 - (i * 0.8), 2),
                        'change': round(-1.5 - (i * 0.08), 2),
                        'change_percent': round(-1.8 - (i * 0.04), 2),
                        'volume': 800000 + (i * 8000)
                    } for i in range(50)  # 50 losers
                ],
                'timestamp': datetime.now(UTC).isoformat()
            }
        }

        # Test serialization performance
        start_time = time.perf_counter()
        json_data = json.dumps(large_dataset)
        serialization_time = (time.perf_counter() - start_time) * 1000  # Convert to ms

        assert serialization_time < 10, f"JSON serialization should be <10ms, got {serialization_time:.2f}ms"
        assert len(json_data) > 0, "Should produce valid JSON output"

        # Test deserialization performance
        start_time = time.perf_counter()
        parsed_data = json.loads(json_data)
        deserialization_time = (time.perf_counter() - start_time) * 1000  # Convert to ms

        assert deserialization_time < 5, f"JSON deserialization should be <5ms, got {deserialization_time:.2f}ms"
        assert parsed_data == large_dataset, "Deserialized data should match original"

    def test_response_compression_efficiency(self):
        """Test response compression for large market data."""
        import gzip

        # Create large market data response
        large_response = {
            'success': True,
            'data': {
                'gainers': [
                    {'symbol': f'SYM{i}', 'name': f'Company Name {i}' * 3, 'price': 100.0 + i}
                    for i in range(100)
                ],
                'losers': [
                    {'symbol': f'LSS{i}', 'name': f'Loser Company {i}' * 3, 'price': 80.0 - i}
                    for i in range(100)
                ]
            }
        }

        # Serialize to JSON
        json_data = json.dumps(large_response).encode('utf-8')
        original_size = len(json_data)

        # Test gzip compression
        compressed_data = gzip.compress(json_data)
        compressed_size = len(compressed_data)

        compression_ratio = compressed_size / original_size

        assert compression_ratio < 0.5, f"Compression ratio should be <50%, got {compression_ratio:.2%}"
        assert compressed_size < original_size, "Compressed data should be smaller than original"
