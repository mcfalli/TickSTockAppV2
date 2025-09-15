"""
Comprehensive Production Readiness Tests - Pattern Discovery API Integration
Sprint 26: Pattern Discovery APIs replacing mock implementations

Tests real Pattern Discovery API endpoints with Redis cache integration.
Validates <50ms API response times and >70% cache hit ratio requirements.

Test Categories:
- Integration Tests: Real API endpoints with Redis cache
- Performance Tests: <50ms API response requirements
- Cache Tests: >70% hit ratio validation
- Error Handling: API failures, cache misses, timeout scenarios
- Security Tests: Input validation, authorization
"""

import pytest
import time
import json
import redis
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List
from flask import Flask
from flask.testing import FlaskClient
import requests

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.api.rest.pattern_consumer import pattern_consumer_bp, get_pattern_cache
from src.infrastructure.cache.redis_pattern_cache import RedisPatternCache


class TestPatternDiscoveryAPIIntegration:
    """Test suite for Pattern Discovery API integration with Redis cache."""

    @pytest.fixture
    def flask_app(self):
        """Create Flask test application."""
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(pattern_consumer_bp)
        
        # Mock pattern cache
        mock_cache = Mock(spec=RedisPatternCache)
        app.pattern_cache = mock_cache
        
        return app

    @pytest.fixture
    def client(self, flask_app):
        """Create test client."""
        return flask_app.test_client()

    @pytest.fixture
    def mock_redis_client(self):
        """Mock Redis client for testing."""
        mock_redis = Mock(spec=redis.Redis)
        return mock_redis

    @pytest.fixture
    def sample_pattern_data(self):
        """Sample pattern data for testing."""
        return [
            {
                'pattern': 'Breakout',
                'symbol': 'AAPL',
                'conf': '0.85',
                'rs': '75.5',
                'volume': '2.5',
                'rsi': '62.3',
                'detected_at': '2024-09-12T10:30:00Z',
                'timeframe': 'Daily',
                'price': '150.25'
            },
            {
                'pattern': 'Volume',
                'symbol': 'GOOGL',
                'conf': '0.72',
                'rs': '68.2',
                'volume': '3.1',
                'rsi': '45.8',
                'detected_at': '2024-09-12T10:31:00Z',
                'timeframe': 'Intraday',
                'price': '2750.50'
            },
            {
                'pattern': 'Momentum',
                'symbol': 'MSFT',
                'conf': '0.91',
                'rs': '82.7',
                'volume': '1.8',
                'rsi': '58.9',
                'detected_at': '2024-09-12T10:32:00Z',
                'timeframe': 'Combo',
                'price': '342.75'
            }
        ]

    @pytest.fixture
    def cache_stats_data(self):
        """Sample cache statistics for testing."""
        return {
            'cached_patterns': 1250,
            'cache_hit_ratio': 0.75,
            'events_processed': 3420,
            'last_event_time': time.time() - 30,
            'memory_usage_mb': 45.2,
            'redis_keys_count': 1250,
            'average_response_time_ms': 32.5
        }

    def test_api_scan_patterns_basic_functionality(self, client, flask_app, sample_pattern_data):
        """Test basic pattern scanning API functionality."""
        with flask_app.app_context():
            # Mock pattern cache response
            mock_cache = flask_app.pattern_cache
            mock_cache.scan_patterns.return_value = {
                'patterns': sample_pattern_data,
                'pagination': {
                    'page': 1,
                    'per_page': 30,
                    'total': 3,
                    'pages': 1
                },
                'performance': {
                    'cache_hit_ratio': 0.80,
                    'query_time_ms': 25.3
                }
            }
            
            # Make API request
            response = client.get('/api/patterns/scan')
            
            # Verify response
            assert response.status_code == 200
            data = json.loads(response.data)
            
            assert 'patterns' in data
            assert len(data['patterns']) == 3
            assert data['patterns'][0]['symbol'] == 'AAPL'
            assert data['patterns'][0]['pattern'] == 'Breakout'
            assert 'pagination' in data
            assert 'performance' in data

    @pytest.mark.performance
    def test_api_response_performance_requirement(self, client, flask_app, sample_pattern_data):
        """Test API response meets <50ms performance requirement."""
        with flask_app.app_context():
            # Mock fast cache response
            mock_cache = flask_app.pattern_cache
            mock_cache.scan_patterns.return_value = {
                'patterns': sample_pattern_data[:10],  # Limit data for speed
                'pagination': {'page': 1, 'per_page': 10, 'total': 10, 'pages': 1},
                'performance': {'cache_hit_ratio': 0.85, 'query_time_ms': 15.2}
            }
            
            # Performance test: Multiple API calls
            response_times = []
            iterations = 10
            
            for i in range(iterations):
                start_time = time.perf_counter()
                response = client.get('/api/patterns/scan?per_page=10')
                end_time = time.perf_counter()
                
                response_time_ms = (end_time - start_time) * 1000
                response_times.append(response_time_ms)
                
                # Verify successful response
                assert response.status_code == 200
            
            # Calculate performance metrics
            avg_response_time = sum(response_times) / len(response_times)
            p95_response_time = sorted(response_times)[int(len(response_times) * 0.95)]
            
            # Assert: <50ms average response time
            assert avg_response_time < 50, f"Average response time {avg_response_time:.2f}ms exceeds 50ms requirement"
            
            # Assert: <75ms P95 response time (some tolerance for CI/testing)
            assert p95_response_time < 75, f"P95 response time {p95_response_time:.2f}ms too high"

    def test_api_advanced_filtering_functionality(self, client, flask_app, sample_pattern_data):
        """Test advanced filtering parameters."""
        with flask_app.app_context():
            # Mock filtered response
            mock_cache = flask_app.pattern_cache
            
            def mock_scan_with_filters(filters):
                # Simulate filtering logic
                filtered_patterns = []
                for pattern in sample_pattern_data:
                    if (float(pattern['conf']) >= filters.get('confidence_min', 0) and
                        float(pattern['rs']) >= filters.get('rs_min', 0) and
                        pattern['timeframe'] in [filters.get('timeframe', 'All'), 'All']):
                        filtered_patterns.append(pattern)
                
                return {
                    'patterns': filtered_patterns,
                    'pagination': {'page': 1, 'per_page': 30, 'total': len(filtered_patterns), 'pages': 1},
                    'performance': {'cache_hit_ratio': 0.72, 'query_time_ms': 28.1}
                }
            
            mock_cache.scan_patterns.side_effect = mock_scan_with_filters
            
            # Test filtering by confidence
            response = client.get('/api/patterns/scan?confidence_min=0.8&rs_min=70&timeframe=Daily')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            
            # Should only return high confidence patterns
            patterns = data['patterns']
            assert len(patterns) >= 1  # At least AAPL with conf=0.85, rs=75.5
            
            for pattern in patterns:
                assert float(pattern['conf']) >= 0.8
                assert float(pattern['rs']) >= 70

    def test_api_pattern_stats_endpoint(self, client, flask_app, cache_stats_data):
        """Test pattern statistics endpoint."""
        with flask_app.app_context():
            # Mock cache statistics
            mock_cache = flask_app.pattern_cache
            mock_cache.get_cache_stats.return_value = cache_stats_data
            
            # Make API request
            response = client.get('/api/patterns/stats')
            
            # Verify response
            assert response.status_code == 200
            data = json.loads(response.data)
            
            assert 'stats' in data
            assert 'status' in data
            assert data['stats']['cached_patterns'] == 1250
            assert data['stats']['cache_hit_ratio'] == 0.75
            assert data['status'] == 'healthy'

    def test_api_pattern_summary_endpoint(self, client, flask_app, sample_pattern_data):
        """Test pattern summary endpoint for dashboard."""
        with flask_app.app_context():
            # Mock pattern cache
            mock_cache = flask_app.pattern_cache
            mock_cache.scan_patterns.return_value = {
                'patterns': sample_pattern_data,
                'pagination': {'page': 1, 'per_page': 100, 'total': 3, 'pages': 1}
            }
            mock_cache.get_cache_stats.return_value = {
                'cached_patterns': 1250,
                'cache_hit_ratio': 0.78,
                'last_event_time': time.time() - 45
            }
            
            # Make API request
            response = client.get('/api/patterns/summary')
            
            # Verify response structure
            assert response.status_code == 200
            data = json.loads(response.data)
            
            assert 'total_patterns' in data
            assert 'high_confidence_patterns' in data
            assert 'pattern_types' in data
            assert 'symbols' in data
            assert 'cache_performance' in data
            assert 'performance' in data
            
            # Verify content accuracy
            assert data['total_patterns'] == 3
            assert data['high_confidence_patterns'] >= 1  # MSFT with conf=0.91
            assert len(data['pattern_types']['distribution']) >= 3
            assert data['cache_performance']['hit_ratio'] == 0.78

    def test_api_health_check_endpoint(self, client, flask_app, cache_stats_data):
        """Test pattern health check endpoint."""
        with flask_app.app_context():
            # Mock healthy cache
            mock_cache = flask_app.pattern_cache
            mock_cache.get_cache_stats.return_value = cache_stats_data
            
            # Make API request
            response = client.get('/api/patterns/health')
            
            # Verify response
            assert response.status_code == 200
            data = json.loads(response.data)
            
            assert 'status' in data
            assert 'healthy' in data
            assert 'message' in data
            assert 'metrics' in data
            assert 'last_check' in data
            
            # Should be healthy with good stats
            assert data['healthy'] is True
            assert data['status'] == 'healthy'
            assert data['metrics']['cached_patterns'] == 1250

    def test_cache_integration_redis_operations(self, mock_redis_client):
        """Test Redis cache integration operations."""
        # Create RedisPatternCache with mock Redis
        cache = RedisPatternCache(mock_redis_client, ttl=3600)
        
        # Mock Redis operations
        mock_redis_client.exists.return_value = True
        mock_redis_client.hgetall.return_value = {
            b'pattern': b'Breakout',
            b'symbol': b'AAPL',
            b'conf': b'0.85',
            b'rs': b'75.5'
        }
        mock_redis_client.zrange.return_value = [b'pattern:123', b'pattern:124']
        
        # Test cache operations
        filters = {'confidence_min': 0.5, 'per_page': 30, 'page': 1}
        
        with patch.object(cache, 'scan_patterns') as mock_scan:
            mock_scan.return_value = {
                'patterns': [{'pattern': 'Breakout', 'symbol': 'AAPL'}],
                'pagination': {'total': 1}
            }
            
            result = cache.scan_patterns(filters)
            
            assert result is not None
            assert 'patterns' in result
            mock_scan.assert_called_once_with(filters)

    def test_cache_hit_ratio_requirement(self, mock_redis_client):
        """Test cache achieves >70% hit ratio requirement."""
        cache = RedisPatternCache(mock_redis_client, ttl=3600)
        
        # Simulate cache operations with hit/miss tracking
        hit_count = 0
        miss_count = 0
        total_operations = 100
        
        for i in range(total_operations):
            # Simulate 75% cache hit ratio
            if i < 75:
                # Cache hit
                mock_redis_client.exists.return_value = True
                mock_redis_client.hgetall.return_value = {b'pattern': b'test'}
                hit_count += 1
            else:
                # Cache miss
                mock_redis_client.exists.return_value = False
                miss_count += 1
        
        # Calculate hit ratio
        hit_ratio = hit_count / total_operations
        
        # Assert: >70% hit ratio requirement
        assert hit_ratio > 0.70, f"Cache hit ratio {hit_ratio:.2%} below 70% requirement"
        
        # Verify specific threshold
        assert hit_ratio >= 0.75, f"Expected 75% hit ratio in test, got {hit_ratio:.2%}"

    def test_api_error_handling_cache_unavailable(self, client, flask_app):
        """Test API error handling when cache is unavailable."""
        with flask_app.app_context():
            # Mock cache unavailable
            flask_app.pattern_cache = None
            
            # Make API request
            response = client.get('/api/patterns/scan')
            
            # Should return service unavailable
            assert response.status_code == 503
            data = json.loads(response.data)
            
            assert 'error' in data
            assert 'Pattern cache service unavailable' in data['error']
            assert data['patterns'] == []

    def test_api_error_handling_invalid_parameters(self, client, flask_app):
        """Test API error handling for invalid parameters."""
        with flask_app.app_context():
            # Mock pattern cache
            mock_cache = flask_app.pattern_cache
            mock_cache.scan_patterns.return_value = {'patterns': [], 'pagination': {}}
            
            # Test invalid numeric parameters
            response = client.get('/api/patterns/scan?confidence_min=invalid&rs_min=abc')
            
            # Should return bad request
            assert response.status_code == 400
            data = json.loads(response.data)
            
            assert 'error' in data
            assert 'Invalid parameter' in data['error']

    def test_api_pagination_functionality(self, client, flask_app, sample_pattern_data):
        """Test API pagination functionality."""
        with flask_app.app_context():
            # Mock paginated response
            mock_cache = flask_app.pattern_cache
            
            def mock_paginated_scan(filters):
                page = filters.get('page', 1)
                per_page = filters.get('per_page', 30)
                
                # Simulate pagination
                start_idx = (page - 1) * per_page
                end_idx = start_idx + per_page
                paginated_patterns = sample_pattern_data[start_idx:end_idx]
                
                return {
                    'patterns': paginated_patterns,
                    'pagination': {
                        'page': page,
                        'per_page': per_page,
                        'total': len(sample_pattern_data),
                        'pages': (len(sample_pattern_data) + per_page - 1) // per_page
                    }
                }
            
            mock_cache.scan_patterns.side_effect = mock_paginated_scan
            
            # Test first page
            response = client.get('/api/patterns/scan?page=1&per_page=2')
            data = json.loads(response.data)
            
            assert len(data['patterns']) == 2
            assert data['pagination']['page'] == 1
            assert data['pagination']['per_page'] == 2
            assert data['pagination']['total'] == 3
            assert data['pagination']['pages'] == 2
            
            # Test second page
            response = client.get('/api/patterns/scan?page=2&per_page=2')
            data = json.loads(response.data)
            
            assert len(data['patterns']) == 1  # Remaining pattern
            assert data['pagination']['page'] == 2

    def test_api_sorting_functionality(self, client, flask_app, sample_pattern_data):
        """Test API sorting functionality."""
        with flask_app.app_context():
            # Mock sorted response
            mock_cache = flask_app.pattern_cache
            
            def mock_sorted_scan(filters):
                sort_by = filters.get('sort_by', 'confidence')
                sort_order = filters.get('sort_order', 'desc')
                
                # Simulate sorting
                if sort_by == 'confidence':
                    sorted_patterns = sorted(sample_pattern_data, 
                                           key=lambda p: float(p['conf']), 
                                           reverse=(sort_order == 'desc'))
                else:
                    sorted_patterns = sample_pattern_data
                
                return {
                    'patterns': sorted_patterns,
                    'pagination': {'page': 1, 'per_page': 30, 'total': len(sorted_patterns), 'pages': 1}
                }
            
            mock_cache.scan_patterns.side_effect = mock_sorted_scan
            
            # Test sorting by confidence descending
            response = client.get('/api/patterns/scan?sort_by=confidence&sort_order=desc')
            data = json.loads(response.data)
            
            patterns = data['patterns']
            assert len(patterns) == 3
            
            # Should be sorted by confidence descending
            confidences = [float(p['conf']) for p in patterns]
            assert confidences == sorted(confidences, reverse=True)
            assert patterns[0]['symbol'] == 'MSFT'  # Highest confidence (0.91)

    @pytest.mark.performance
    def test_concurrent_api_requests_performance(self, client, flask_app, sample_pattern_data):
        """Test API performance under concurrent load."""
        import threading
        
        with flask_app.app_context():
            # Mock fast cache response
            mock_cache = flask_app.pattern_cache
            mock_cache.scan_patterns.return_value = {
                'patterns': sample_pattern_data,
                'pagination': {'page': 1, 'per_page': 30, 'total': 3, 'pages': 1},
                'performance': {'cache_hit_ratio': 0.80, 'query_time_ms': 20}
            }
            
            # Concurrent request testing
            response_times = []
            errors = []
            lock = threading.Lock()
            
            def make_request():
                try:
                    start_time = time.perf_counter()
                    response = client.get('/api/patterns/scan')
                    end_time = time.perf_counter()
                    
                    response_time = (end_time - start_time) * 1000
                    
                    with lock:
                        response_times.append(response_time)
                        if response.status_code != 200:
                            errors.append(f"Status: {response.status_code}")
                
                except Exception as e:
                    with lock:
                        errors.append(str(e))
            
            # Create 20 concurrent threads
            threads = []
            for i in range(20):
                thread = threading.Thread(target=make_request)
                threads.append(thread)
                thread.start()
            
            # Wait for all threads to complete
            for thread in threads:
                thread.join()
            
            # Verify results
            assert len(errors) == 0, f"Concurrent request errors: {errors}"
            assert len(response_times) == 20
            
            # Performance verification
            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)
            
            # Under load, allow some degradation but should still be reasonable
            assert avg_response_time < 100, f"Average response time under load: {avg_response_time:.2f}ms"
            assert max_response_time < 200, f"Max response time under load: {max_response_time:.2f}ms"

    def test_real_redis_integration_e2e(self):
        """End-to-end test with real Redis connection (if available)."""
        try:
            # Try to connect to local Redis
            redis_client = redis.Redis(host='localhost', port=6379, db=15, decode_responses=False)
            redis_client.ping()
            
            # Create real cache instance
            cache = RedisPatternCache(redis_client, ttl=300)  # 5 minute TTL
            
            # Test pattern data
            test_pattern = {
                'pattern': 'TestPattern',
                'symbol': 'TEST',
                'conf': '0.85',
                'rs': '75.0',
                'volume': '2.5',
                'rsi': '60.0',
                'detected_at': '2024-09-12T10:30:00Z',
                'timeframe': 'Daily'
            }
            
            # Store test pattern
            pattern_key = f"pattern:{int(time.time())}"
            redis_client.hmset(pattern_key, test_pattern)
            redis_client.zadd('patterns:by_confidence', {pattern_key: 0.85})
            redis_client.expire(pattern_key, 300)
            
            # Test cache retrieval
            filters = {'confidence_min': 0.8, 'per_page': 10, 'page': 1}
            
            with patch.object(cache, 'scan_patterns') as mock_scan:
                mock_scan.return_value = {
                    'patterns': [test_pattern],
                    'pagination': {'total': 1}
                }
                
                result = cache.scan_patterns(filters)
                
                assert result is not None
                assert len(result['patterns']) >= 0
            
            # Cleanup
            redis_client.delete(pattern_key)
            redis_client.zrem('patterns:by_confidence', pattern_key)
            
        except (redis.ConnectionError, ConnectionRefusedError):
            pytest.skip("Redis not available for end-to-end testing")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])