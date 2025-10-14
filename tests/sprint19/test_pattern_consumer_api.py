"""
Pattern Consumer API Test Suite - Sprint 19 Phase 1
Comprehensive testing of Pattern Consumer API endpoints with performance validation.

Test Coverage:
- /api/patterns/scan endpoint functionality and performance
- Parameter validation and filtering capabilities
- Redis cache consumption (not direct database queries)
- Error handling and edge cases
- Performance benchmarks (<50ms response time target)
- Load testing with concurrent requests
- API response format validation
"""

import json
import time
from unittest.mock import Mock, patch

import pytest

# Sprint 19 imports
from src.api.rest.pattern_consumer import validate_scan_parameters


class TestParameterValidation:
    """Test parameter validation for pattern scan endpoints."""

    def test_validate_scan_parameters_basic(self):
        """Test basic parameter validation."""
        # Mock Flask request args
        mock_args = Mock()
        mock_args.getlist.return_value = []
        mock_args.get.side_effect = lambda key, default=None: {
            'rs_min': '1.5',
            'vol_min': '2.0',
            'confidence_min': '0.8',
            'page': '1',
            'per_page': '20',
            'sort_by': 'confidence',
            'sort_order': 'desc'
        }.get(key, default)

        params = validate_scan_parameters(mock_args)

        assert params['rs_min'] == 1.5
        assert params['vol_min'] == 2.0
        assert params['confidence_min'] == 0.8
        assert params['page'] == 1
        assert params['per_page'] == 20
        assert params['sort_by'] == 'confidence'
        assert params['sort_order'] == 'desc'

    def test_validate_scan_parameters_defaults(self):
        """Test parameter validation with defaults."""
        mock_args = Mock()
        mock_args.getlist.return_value = []
        mock_args.get.return_value = None

        params = validate_scan_parameters(mock_args)

        assert params['rs_min'] == 0
        assert params['vol_min'] == 0
        assert params['confidence_min'] == 0.5
        assert params['page'] == 1
        assert params['per_page'] == 30
        assert params['sort_by'] == 'confidence'
        assert params['sort_order'] == 'desc'
        assert params['timeframe'] == 'All'

    def test_validate_scan_parameters_arrays(self):
        """Test parameter validation with array parameters."""
        mock_args = Mock()
        mock_args.getlist.side_effect = lambda key: {
            'pattern_types': ['Weekly_Breakout', 'Bull_Flag'],
            'symbols': ['AAPL', 'GOOGL', 'MSFT'],
            'sectors': ['Technology']
        }.get(key, [])
        mock_args.get.side_effect = lambda key, default=None: {
            'rsi_range': '20,80'
        }.get(key, default)

        params = validate_scan_parameters(mock_args)

        assert params['pattern_types'] == ['Weekly_Breakout', 'Bull_Flag']
        assert params['symbols'] == ['AAPL', 'GOOGL', 'MSFT']
        assert params['sectors'] == ['Technology']
        assert params['rsi_range'] == [20.0, 80.0]

    def test_validate_scan_parameters_edge_cases(self):
        """Test parameter validation edge cases and boundaries."""
        mock_args = Mock()
        mock_args.getlist.return_value = []
        mock_args.get.side_effect = lambda key, default=None: {
            'rs_min': '-1.0',  # Should be clamped to 0
            'vol_min': '-0.5',  # Should be clamped to 0
            'confidence_min': '1.5',  # Should be clamped to valid range
            'page': '0',  # Should be clamped to 1
            'per_page': '200',  # Should be clamped to max 100
            'sort_by': 'invalid_field',  # Should default to confidence
            'sort_order': 'invalid_order',  # Should default to desc
            'rsi_range': '150,200'  # Should be clamped to 0-100 range
        }.get(key, default)

        params = validate_scan_parameters(mock_args)

        assert params['rs_min'] == 0
        assert params['vol_min'] == 0
        assert params['confidence_min'] == 0.5  # Default due to invalid range
        assert params['page'] == 1
        assert params['per_page'] == 100  # Clamped to max
        assert params['sort_by'] == 'confidence'  # Default due to invalid field
        assert params['sort_order'] == 'desc'  # Default due to invalid order
        assert params['rsi_range'] == [100.0, 100.0]  # Clamped to valid range

    def test_validate_scan_parameters_invalid_types(self):
        """Test parameter validation with invalid data types."""
        mock_args = Mock()
        mock_args.getlist.return_value = []
        mock_args.get.side_effect = lambda key, default=None: {
            'rs_min': 'not_a_number',
            'page': 'not_an_integer',
            'rsi_range': 'invalid,format,too_many'
        }.get(key, default)

        # Should raise BadRequest for invalid types
        from werkzeug.exceptions import BadRequest
        with pytest.raises(BadRequest):
            validate_scan_parameters(mock_args)


class TestPatternScanEndpoint:
    """Test /api/patterns/scan endpoint functionality."""

    def test_scan_patterns_success(self, app_with_mocks, api_response_validator):
        """Test successful pattern scan request."""
        client = app_with_mocks.test_client()

        # Mock pattern cache response
        mock_response = {
            'patterns': [
                {
                    'symbol': 'AAPL',
                    'pattern': 'WeeklyBO',
                    'conf': 0.85,
                    'rs': '1.4x',
                    'vol': '2.1x',
                    'price': '$150.25',
                    'chg': '+2.3%',
                    'time': '5m',
                    'exp': '30m',
                    'source': 'daily'
                }
            ],
            'pagination': {
                'page': 1,
                'per_page': 30,
                'total': 1,
                'pages': 1
            },
            'cache_info': {
                'cached': False,
                'query_time_ms': 25.5
            }
        }

        app_with_mocks.pattern_cache.scan_patterns.return_value = mock_response

        # Make request
        response = client.get('/api/patterns/scan')
        assert response.status_code == 200

        data = json.loads(response.data)
        api_response_validator.validate_pattern_scan_response(data)
        api_response_validator.validate_performance_metrics(data, target_ms=50)

        # Verify pattern cache was called
        app_with_mocks.pattern_cache.scan_patterns.assert_called_once()

    def test_scan_patterns_with_filters(self, app_with_mocks):
        """Test pattern scan with various filters."""
        client = app_with_mocks.test_client()

        mock_response = {
            'patterns': [],
            'pagination': {'page': 1, 'per_page': 20, 'total': 0, 'pages': 0}
        }
        app_with_mocks.pattern_cache.scan_patterns.return_value = mock_response

        # Test with comprehensive filters
        query_params = {
            'pattern_types': ['Weekly_Breakout', 'Bull_Flag'],
            'symbols': ['AAPL', 'GOOGL'],
            'rs_min': '1.5',
            'vol_min': '2.0',
            'confidence_min': '0.8',
            'rsi_range': '30,70',
            'page': '2',
            'per_page': '20',
            'sort_by': 'symbol',
            'sort_order': 'asc',
            'timeframe': 'Daily'
        }

        response = client.get('/api/patterns/scan', query_string=query_params)
        assert response.status_code == 200

        # Verify filters were passed correctly
        call_args = app_with_mocks.pattern_cache.scan_patterns.call_args[0][0]
        assert call_args['pattern_types'] == ['Weekly_Breakout', 'Bull_Flag']
        assert call_args['symbols'] == ['AAPL', 'GOOGL']
        assert call_args['rs_min'] == 1.5
        assert call_args['vol_min'] == 2.0
        assert call_args['confidence_min'] == 0.8
        assert call_args['rsi_range'] == [30.0, 70.0]
        assert call_args['page'] == 2
        assert call_args['per_page'] == 20
        assert call_args['sort_by'] == 'symbol'
        assert call_args['sort_order'] == 'asc'

    @pytest.mark.performance
    def test_scan_patterns_performance(self, app_with_mocks, performance_benchmark):
        """Test pattern scan API performance."""
        client = app_with_mocks.test_client()

        # Mock fast response
        mock_response = {
            'patterns': [{'symbol': 'TEST', 'pattern': 'Test', 'conf': 0.8, 'rs': '1x',
                         'vol': '1x', 'price': '$100', 'chg': '+1%', 'time': '1m',
                         'exp': '30m', 'source': 'test'}],
            'pagination': {'page': 1, 'per_page': 30, 'total': 1, 'pages': 1}
        }
        app_with_mocks.pattern_cache.scan_patterns.return_value = mock_response

        # Benchmark multiple requests
        target_ms = 50

        for _ in range(10):
            def make_request():
                response = client.get('/api/patterns/scan?confidence_min=0.7')
                return response.status_code == 200

            result, elapsed_ms = performance_benchmark.measure(make_request)
            assert result is True
            performance_benchmark.assert_performance(elapsed_ms, "Pattern scan API")

        perf_stats = performance_benchmark.get_statistics()
        assert perf_stats['p95_ms'] < target_ms
        assert perf_stats['avg_ms'] < target_ms

    def test_scan_patterns_pattern_cache_unavailable(self, app):
        """Test behavior when pattern cache is unavailable."""
        # Create app without pattern cache
        client = app.test_client()

        response = client.get('/api/patterns/scan')
        assert response.status_code == 503

        data = json.loads(response.data)
        assert 'error' in data
        assert 'Pattern cache service unavailable' in data['error']
        assert data['patterns'] == []

    def test_scan_patterns_invalid_parameters(self, app_with_mocks):
        """Test pattern scan with invalid parameters."""
        client = app_with_mocks.test_client()

        # Test with invalid numeric parameter
        response = client.get('/api/patterns/scan?rs_min=not_a_number')
        assert response.status_code == 400

        data = json.loads(response.data)
        assert 'error' in data
        assert 'patterns' in data
        assert data['patterns'] == []

    def test_scan_patterns_cache_exception(self, app_with_mocks):
        """Test handling of pattern cache exceptions."""
        client = app_with_mocks.test_client()

        # Mock pattern cache to raise exception
        app_with_mocks.pattern_cache.scan_patterns.side_effect = Exception("Cache error")

        response = client.get('/api/patterns/scan')
        assert response.status_code == 500

        data = json.loads(response.data)
        assert 'error' in data
        assert 'Internal server error' in data['error']


class TestPatternStatsEndpoint:
    """Test /api/patterns/stats endpoint functionality."""

    def test_get_pattern_stats_success(self, app_with_mocks):
        """Test successful pattern stats request."""
        client = app_with_mocks.test_client()

        # Mock pattern cache stats
        mock_stats = {
            'cached_patterns': 150,
            'cache_hits': 75,
            'cache_misses': 25,
            'events_processed': 200,
            'cache_hit_ratio': 0.75,
            'last_event_time': time.time(),
            'expired_patterns_cleaned': 10
        }

        app_with_mocks.pattern_cache.get_cache_stats.return_value = mock_stats

        response = client.get('/api/patterns/stats')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'stats' in data
        assert 'status' in data
        assert data['status'] == 'healthy'  # Should be healthy with cached patterns
        assert data['stats']['cached_patterns'] == 150
        assert data['stats']['cache_hit_ratio'] == 0.75

    def test_get_pattern_stats_no_data(self, app_with_mocks):
        """Test pattern stats with no cached patterns."""
        client = app_with_mocks.test_client()

        mock_stats = {
            'cached_patterns': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'events_processed': 0,
            'cache_hit_ratio': 1.0,
            'last_event_time': None
        }

        app_with_mocks.pattern_cache.get_cache_stats.return_value = mock_stats

        response = client.get('/api/patterns/stats')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['status'] == 'no_data'

    def test_get_pattern_stats_unavailable(self, app):
        """Test pattern stats when cache is unavailable."""
        client = app.test_client()

        response = client.get('/api/patterns/stats')
        assert response.status_code == 503

        data = json.loads(response.data)
        assert 'error' in data
        assert 'Pattern cache service unavailable' in data['error']


class TestPatternSummaryEndpoint:
    """Test /api/patterns/summary endpoint functionality."""

    def test_get_pattern_summary_success(self, app_with_mocks):
        """Test successful pattern summary request."""
        client = app_with_mocks.test_client()

        # Mock pattern cache response with sample patterns
        mock_scan_response = {
            'patterns': [
                {
                    'symbol': 'AAPL',
                    'pattern': 'WeeklyBO',
                    'conf': 0.85,
                    'rs': '1.4x',
                    'vol': '2.1x',
                    'price': '$150.25',
                    'chg': '+2.3%',
                    'time': '5m',
                    'exp': '30m',
                    'source': 'daily'
                },
                {
                    'symbol': 'GOOGL',
                    'pattern': 'BullFlag',
                    'conf': 0.90,
                    'rs': '1.6x',
                    'vol': '1.8x',
                    'price': '$2750.50',
                    'chg': '+1.5%',
                    'time': '10m',
                    'exp': '45m',
                    'source': 'intraday'
                }
            ],
            'pagination': {'page': 1, 'per_page': 100, 'total': 2, 'pages': 1}
        }

        mock_cache_stats = {
            'cache_hit_ratio': 0.75,
            'cached_patterns': 150,
            'last_event_time': time.time()
        }

        app_with_mocks.pattern_cache.scan_patterns.return_value = mock_scan_response
        app_with_mocks.pattern_cache.get_cache_stats.return_value = mock_cache_stats

        response = client.get('/api/patterns/summary')
        assert response.status_code == 200

        data = json.loads(response.data)

        # Verify summary structure
        assert 'total_patterns' in data
        assert 'high_confidence_patterns' in data
        assert 'pattern_types' in data
        assert 'symbols' in data
        assert 'cache_performance' in data
        assert 'performance' in data

        # Verify calculated metrics
        assert data['total_patterns'] == 2
        assert data['high_confidence_patterns'] == 1  # Only GOOGL has conf > 0.8

        # Verify pattern type distribution
        assert 'distribution' in data['pattern_types']
        assert 'top_patterns' in data['pattern_types']

        # Verify symbol analysis
        assert 'active_symbols' in data['symbols']
        assert 'top_symbols' in data['symbols']
        assert data['symbols']['active_symbols'] == 2

    def test_get_pattern_summary_unavailable(self, app):
        """Test pattern summary when cache is unavailable."""
        client = app.test_client()

        response = client.get('/api/patterns/summary')
        assert response.status_code == 503

        data = json.loads(response.data)
        assert 'error' in data


class TestPatternHealthEndpoint:
    """Test /api/patterns/health endpoint functionality."""

    def test_get_pattern_health_healthy(self, app_with_mocks):
        """Test pattern health check - healthy status."""
        client = app_with_mocks.test_client()

        mock_stats = {
            'cached_patterns': 100,
            'cache_hit_ratio': 0.8,
            'last_event_time': time.time() - 60  # 1 minute ago
        }

        app_with_mocks.pattern_cache.get_cache_stats.return_value = mock_stats

        response = client.get('/api/patterns/health')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert data['healthy'] is True
        assert 'Pattern cache operating normally' in data['message']
        assert 'metrics' in data
        assert data['metrics']['cached_patterns'] == 100

    def test_get_pattern_health_degraded(self, app_with_mocks):
        """Test pattern health check - degraded status."""
        client = app_with_mocks.test_client()

        mock_stats = {
            'cached_patterns': 50,
            'cache_hit_ratio': 0.3,  # Low hit ratio
            'last_event_time': time.time() - 60
        }

        app_with_mocks.pattern_cache.get_cache_stats.return_value = mock_stats

        response = client.get('/api/patterns/health')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['status'] == 'degraded'
        assert 'Low cache hit ratio' in data['message']

    def test_get_pattern_health_warning(self, app_with_mocks):
        """Test pattern health check - warning status."""
        client = app_with_mocks.test_client()

        mock_stats = {
            'cached_patterns': 0,  # No patterns
            'cache_hit_ratio': 1.0,
            'last_event_time': time.time() - 400  # No recent events
        }

        app_with_mocks.pattern_cache.get_cache_stats.return_value = mock_stats

        response = client.get('/api/patterns/health')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['status'] == 'warning'
        assert data['healthy'] is False
        assert 'No patterns in cache' in data['message']

    def test_get_pattern_health_unavailable(self, app):
        """Test pattern health when cache is unavailable."""
        client = app.test_client()

        response = client.get('/api/patterns/health')
        assert response.status_code == 503

        data = json.loads(response.data)
        assert data['status'] == 'error'
        assert data['healthy'] is False


class TestPatternConsumerAPIIntegration:
    """Integration tests for Pattern Consumer API."""

    @pytest.mark.integration
    def test_full_workflow_integration(self, app_with_mocks, multiple_pattern_events):
        """Test full workflow from pattern caching to API consumption."""
        client = app_with_mocks.test_client()

        # Simulate pattern caching
        for event in multiple_pattern_events[:10]:
            app_with_mocks.pattern_cache.process_pattern_event(event)

        # Mock scan response based on cached data
        mock_patterns = [
            {
                'symbol': event['data']['symbol'],
                'pattern': event['data']['pattern'][:8],  # Abbreviated
                'conf': event['data']['confidence'],
                'rs': f"{event['data']['indicators'].get('relative_strength', 1.0):.1f}x",
                'vol': f"{event['data']['indicators'].get('relative_volume', 1.0):.1f}x",
                'price': f"${event['data']['current_price']:.2f}",
                'chg': f"{event['data']['price_change']:+.1f}%",
                'time': '5m',
                'exp': '30m',
                'source': event['data']['source']
            }
            for event in multiple_pattern_events[:5]
        ]

        mock_response = {
            'patterns': mock_patterns,
            'pagination': {'page': 1, 'per_page': 30, 'total': 5, 'pages': 1}
        }

        app_with_mocks.pattern_cache.scan_patterns.return_value = mock_response

        # Test API endpoints

        # 1. Scan patterns
        scan_response = client.get('/api/patterns/scan?confidence_min=0.6')
        assert scan_response.status_code == 200
        scan_data = json.loads(scan_response.data)
        assert len(scan_data['patterns']) == 5

        # 2. Get stats
        mock_stats = {'cached_patterns': 10, 'cache_hit_ratio': 0.75}
        app_with_mocks.pattern_cache.get_cache_stats.return_value = mock_stats

        stats_response = client.get('/api/patterns/stats')
        assert stats_response.status_code == 200
        stats_data = json.loads(stats_response.data)
        assert stats_data['stats']['cached_patterns'] == 10

        # 3. Get summary
        summary_response = client.get('/api/patterns/summary')
        assert summary_response.status_code == 200
        summary_data = json.loads(summary_response.data)
        assert 'total_patterns' in summary_data

        # 4. Health check
        health_response = client.get('/api/patterns/health')
        assert health_response.status_code == 200
        health_data = json.loads(health_response.data)
        assert health_data['healthy'] is True

    @pytest.mark.performance
    @pytest.mark.load
    def test_concurrent_api_load(self, app_with_mocks, concurrent_load_tester):
        """Test API performance under concurrent load."""
        client = app_with_mocks.test_client()

        # Mock consistent response
        mock_response = {
            'patterns': [
                {
                    'symbol': 'LOAD_TEST',
                    'pattern': 'LoadTest',
                    'conf': 0.8,
                    'rs': '1.2x',
                    'vol': '1.5x',
                    'price': '$100.00',
                    'chg': '+1.0%',
                    'time': '1m',
                    'exp': '30m',
                    'source': 'test'
                }
            ],
            'pagination': {'page': 1, 'per_page': 30, 'total': 1, 'pages': 1}
        }

        app_with_mocks.pattern_cache.scan_patterns.return_value = mock_response

        def make_api_request():
            response = client.get('/api/patterns/scan?confidence_min=0.7')
            return response.status_code == 200

        # Run concurrent requests
        results = concurrent_load_tester.run_concurrent_requests(
            make_api_request,
            num_requests=100,
            max_concurrent=10
        )

        successful_requests = [r for r in results if r['success']]
        failed_requests = [r for r in results if not r['success']]

        # Verify success rate
        success_rate = len(successful_requests) / len(results) * 100
        assert success_rate >= 95, f"Success rate too low: {success_rate}%"

        # Verify performance
        response_times = [r['elapsed_ms'] for r in successful_requests if r['elapsed_ms']]
        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            p95_response_time = sorted(response_times)[int(len(response_times) * 0.95)]

            print("\nConcurrent Load Test Results:")
            print(f"  Requests: {len(results)}")
            print(f"  Success rate: {success_rate:.1f}%")
            print(f"  Average response time: {avg_response_time:.2f}ms")
            print(f"  P95 response time: {p95_response_time:.2f}ms")

            assert avg_response_time < 100  # Allow higher threshold for concurrent load
            assert p95_response_time < 150

    @pytest.mark.performance
    def test_api_response_caching_effectiveness(self, app_with_mocks):
        """Test effectiveness of API response caching."""
        client = app_with_mocks.test_client()

        # Mock pattern cache responses
        cached_response = {
            'patterns': [{'symbol': 'CACHE_TEST', 'pattern': 'Test', 'conf': 0.8,
                         'rs': '1x', 'vol': '1x', 'price': '$100', 'chg': '+1%',
                         'time': '1m', 'exp': '30m', 'source': 'test'}],
            'pagination': {'page': 1, 'per_page': 30, 'total': 1, 'pages': 1},
            'cache_info': {'cached': False, 'query_time_ms': 25}
        }

        hit_response = {
            **cached_response,
            'cache_info': {'cached': True, 'query_time_ms': 2}  # Much faster for cache hit
        }

        # First request - cache miss
        app_with_mocks.pattern_cache.scan_patterns.return_value = cached_response
        response1 = client.get('/api/patterns/scan?confidence_min=0.7&page=1')
        assert response1.status_code == 200

        # Subsequent requests with same parameters - should be faster
        app_with_mocks.pattern_cache.scan_patterns.return_value = hit_response

        response_times = []
        for _ in range(5):
            start_time = time.perf_counter()
            response = client.get('/api/patterns/scan?confidence_min=0.7&page=1')
            end_time = time.perf_counter()

            assert response.status_code == 200
            response_times.append((end_time - start_time) * 1000)

        # Cache hits should be consistently fast
        avg_cache_hit_time = sum(response_times) / len(response_times)
        print(f"Average cache hit API response time: {avg_cache_hit_time:.2f}ms")

        # All cache hits should be under target
        for rt in response_times:
            assert rt < 50, f"Cache hit response time {rt:.2f}ms exceeds 50ms target"


class TestPatternConsumerErrorHandling:
    """Test error handling in Pattern Consumer API."""

    def test_blueprint_error_handlers(self, app_with_mocks):
        """Test blueprint-level error handlers."""
        client = app_with_mocks.test_client()

        # Test 404 handler
        response = client.get('/api/patterns/nonexistent')
        assert response.status_code == 404

        data = json.loads(response.data)
        assert 'error' in data
        assert 'Endpoint not found' in data['error']

    def test_performance_logging(self, app_with_mocks):
        """Test performance logging for slow responses."""
        client = app_with_mocks.test_client()

        # Mock slow pattern cache response
        slow_response = {
            'patterns': [],
            'pagination': {'page': 1, 'per_page': 30, 'total': 0, 'pages': 0},
            'cache_info': {'cached': False, 'query_time_ms': 75}  # Above 50ms target
        }

        with patch('src.api.rest.pattern_consumer.logger') as mock_logger:
            app_with_mocks.pattern_cache.scan_patterns.return_value = slow_response

            response = client.get('/api/patterns/scan')
            assert response.status_code == 200

            # Verify slow response was logged as warning
            warning_calls = [call for call in mock_logger.warning.call_args_list
                           if 'Slow response' in str(call)]
            assert len(warning_calls) > 0

    def test_exception_handling_in_endpoints(self, app_with_mocks):
        """Test exception handling in API endpoints."""
        client = app_with_mocks.test_client()

        # Mock pattern cache to raise exception
        app_with_mocks.pattern_cache.scan_patterns.side_effect = ValueError("Test error")

        response = client.get('/api/patterns/scan')
        assert response.status_code == 500

        data = json.loads(response.data)
        assert 'error' in data
        assert 'Internal server error' in data['error']
        assert data['patterns'] == []
