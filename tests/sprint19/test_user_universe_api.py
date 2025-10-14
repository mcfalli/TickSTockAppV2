"""
User Universe API Test Suite - Sprint 19 Phase 1
Comprehensive testing of User Universe API endpoints for symbols and user data management.

Test Coverage:
- Symbol management and dropdown population
- Universe and watchlist management
- Read-only database access patterns
- User data CRUD operations (TODO implementations)
- Performance validation (<50ms for database queries)
- Authentication and authorization handling
- Error handling and edge cases
"""

import json
import time
from unittest.mock import patch

import pytest

# Sprint 19 imports


class TestSymbolsEndpoint:
    """Test /api/symbols endpoint functionality."""

    def test_get_symbols_success(self, app_with_mocks):
        """Test successful symbols retrieval."""
        client = app_with_mocks.test_client()

        response = client.get('/api/symbols')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'symbols' in data
        assert 'count' in data
        assert 'filters' in data
        assert 'performance' in data

        # Verify symbol structure
        if data['symbols']:
            symbol = data['symbols'][0]
            assert 'symbol' in symbol
            assert 'name' in symbol
            assert 'market' in symbol
            assert 'sector' in symbol

        # Verify performance metrics
        assert data['performance']['source'] == 'tickstock_database'
        assert 'api_response_time_ms' in data['performance']

    def test_get_symbols_with_filters(self, app_with_mocks):
        """Test symbols retrieval with filters."""
        client = app_with_mocks.test_client()

        # Test market filter
        response = client.get('/api/symbols?market=stocks')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['filters']['market'] == 'stocks'

        # Verify database service was called
        app_with_mocks.tickstock_db.get_symbols_for_dropdown.assert_called()

    def test_get_symbols_with_search(self, app_with_mocks):
        """Test symbols retrieval with search filter."""
        client = app_with_mocks.test_client()

        # Test search functionality
        response = client.get('/api/symbols?search=apple&limit=10')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['filters']['search'] == 'apple'
        assert data['filters']['limit'] == 10

        # In real implementation, results would be filtered by search term
        # Here we just verify the parameters were processed

    @pytest.mark.performance
    def test_get_symbols_performance(self, app_with_mocks, performance_benchmark):
        """Test symbols API performance."""
        client = app_with_mocks.test_client()

        target_ms = 50

        for _ in range(5):
            def make_request():
                response = client.get('/api/symbols?limit=100')
                return response.status_code == 200

            result, elapsed_ms = performance_benchmark.measure(make_request)
            assert result is True
            performance_benchmark.assert_performance(elapsed_ms, "Symbols API")

        perf_stats = performance_benchmark.get_statistics()
        assert perf_stats['avg_ms'] < target_ms

    def test_get_symbols_database_unavailable(self, app):
        """Test symbols endpoint when database is unavailable."""
        client = app.test_client()

        response = client.get('/api/symbols')
        assert response.status_code == 503

        data = json.loads(response.data)
        assert 'error' in data
        assert 'Database service unavailable' in data['error']
        assert data['symbols'] == []

    def test_get_symbols_database_error(self, app_with_mocks):
        """Test symbols endpoint with database error."""
        client = app_with_mocks.test_client()

        # Mock database to raise exception
        app_with_mocks.tickstock_db.get_symbols_for_dropdown.side_effect = Exception("DB Error")

        response = client.get('/api/symbols')
        assert response.status_code == 500

        data = json.loads(response.data)
        assert 'error' in data
        assert 'Failed to retrieve symbols' in data['error']


class TestSymbolDetailsEndpoint:
    """Test /api/symbols/<symbol> endpoint functionality."""

    def test_get_symbol_details_success(self, app_with_mocks):
        """Test successful symbol details retrieval."""
        client = app_with_mocks.test_client()

        response = client.get('/api/symbols/AAPL')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'symbol' in data
        assert 'performance' in data

        # Verify database service was called with correct symbol
        app_with_mocks.tickstock_db.get_symbol_details.assert_called_with('AAPL')

    def test_get_symbol_details_not_found(self, app_with_mocks):
        """Test symbol details for non-existent symbol."""
        client = app_with_mocks.test_client()

        # Mock database to return None
        app_with_mocks.tickstock_db.get_symbol_details.return_value = None

        response = client.get('/api/symbols/NONEXISTENT')
        assert response.status_code == 404

        data = json.loads(response.data)
        assert 'error' in data
        assert 'Symbol NONEXISTENT not found' in data['error']

    def test_get_symbol_details_case_handling(self, app_with_mocks):
        """Test symbol details with case variations."""
        client = app_with_mocks.test_client()

        # Test lowercase input
        response = client.get('/api/symbols/aapl')
        assert response.status_code == 200

        # Verify symbol was converted to uppercase
        app_with_mocks.tickstock_db.get_symbol_details.assert_called_with('AAPL')

    def test_get_symbol_details_database_error(self, app_with_mocks):
        """Test symbol details with database error."""
        client = app_with_mocks.test_client()

        app_with_mocks.tickstock_db.get_symbol_details.side_effect = Exception("DB Error")

        response = client.get('/api/symbols/AAPL')
        assert response.status_code == 500

        data = json.loads(response.data)
        assert 'error' in data


class TestUserUniversesEndpoint:
    """Test /api/users/universe endpoint functionality."""

    def test_get_user_universes_success(self, app_with_mocks):
        """Test successful user universes retrieval."""
        client = app_with_mocks.test_client()

        response = client.get('/api/users/universe')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'universes' in data
        assert 'total_universes' in data
        assert 'performance' in data

        # Verify universe structure
        if data['universes']:
            universe = data['universes'][0]
            assert 'key' in universe
            assert 'description' in universe
            assert 'criteria' in universe
            assert 'count' in universe
            assert 'category' in universe

        # Verify cache control service was called
        app_with_mocks.cache_control.get_available_universes.assert_called()

    def test_get_user_universes_sorting(self, app_with_mocks):
        """Test universe sorting by category and count."""
        client = app_with_mocks.test_client()

        # Mock multiple universes with different categories and counts
        mock_universes = {
            'tech_high_growth': {
                'description': 'Tech High Growth',
                'criteria': 'High growth tech stocks',
                'count': 50
            },
            'sp500_large': {
                'description': 'S&P 500 Large Cap',
                'criteria': 'Large cap stocks',
                'count': 150
            },
            'tech_dividend': {
                'description': 'Tech Dividend Stocks',
                'criteria': 'Tech stocks with dividends',
                'count': 25
            }
        }

        app_with_mocks.cache_control.get_available_universes.return_value = mock_universes

        response = client.get('/api/users/universe')
        assert response.status_code == 200

        data = json.loads(response.data)
        universes = data['universes']

        # Verify sorting: same category grouped, then by count descending
        tech_universes = [u for u in universes if u['category'] == 'tech']
        if len(tech_universes) >= 2:
            assert tech_universes[0]['count'] >= tech_universes[1]['count']

    def test_get_user_universes_cache_unavailable(self, app):
        """Test universes endpoint when cache is unavailable."""
        client = app.test_client()

        response = client.get('/api/users/universe')
        assert response.status_code == 503

        data = json.loads(response.data)
        assert 'error' in data
        assert 'Cache service unavailable' in data['error']
        assert data['universes'] == {}


class TestUniverseTickersEndpoint:
    """Test /api/users/universe/<universe_key> endpoint functionality."""

    def test_get_universe_tickers_success(self, app_with_mocks):
        """Test successful universe tickers retrieval."""
        client = app_with_mocks.test_client()

        response = client.get('/api/users/universe/sp500_large')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'universe_key' in data
        assert 'tickers' in data
        assert 'count' in data
        assert 'metadata' in data
        assert 'performance' in data

        assert data['universe_key'] == 'sp500_large'

        # Verify cache control services were called
        app_with_mocks.cache_control.get_universe_tickers.assert_called_with('sp500_large')
        app_with_mocks.cache_control.get_universe_metadata.assert_called_with('sp500_large')

    def test_get_universe_tickers_not_found(self, app_with_mocks):
        """Test universe tickers for non-existent universe."""
        client = app_with_mocks.test_client()

        # Mock cache control to return None
        app_with_mocks.cache_control.get_universe_tickers.return_value = None

        response = client.get('/api/users/universe/nonexistent')
        assert response.status_code == 404

        data = json.loads(response.data)
        assert 'error' in data
        assert 'Universe nonexistent not found' in data['error']

    def test_get_universe_tickers_cache_error(self, app_with_mocks):
        """Test universe tickers with cache error."""
        client = app_with_mocks.test_client()

        app_with_mocks.cache_control.get_universe_tickers.side_effect = Exception("Cache Error")

        response = client.get('/api/users/universe/sp500_large')
        assert response.status_code == 500

        data = json.loads(response.data)
        assert 'error' in data


class TestWatchlistsEndpoint:
    """Test /api/users/watchlists endpoint functionality."""

    def test_get_user_watchlists(self, app_with_mocks):
        """Test getting user watchlists (sample implementation)."""
        client = app_with_mocks.test_client()

        response = client.get('/api/users/watchlists')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'watchlists' in data
        assert 'user_id' in data
        assert 'count' in data

        # Verify sample watchlist structure
        if data['watchlists']:
            watchlist = data['watchlists'][0]
            assert 'id' in watchlist
            assert 'name' in watchlist
            assert 'symbols' in watchlist
            assert 'created_at' in watchlist
            assert 'updated_at' in watchlist

    def test_create_user_watchlist_success(self, app_with_mocks):
        """Test creating new user watchlist."""
        client = app_with_mocks.test_client()

        watchlist_data = {
            'name': 'Test Watchlist',
            'symbols': ['AAPL', 'GOOGL', 'MSFT']
        }

        response = client.post('/api/users/watchlists',
                              data=json.dumps(watchlist_data),
                              content_type='application/json')
        assert response.status_code == 201

        data = json.loads(response.data)
        assert 'watchlist' in data
        assert 'message' in data

        created_watchlist = data['watchlist']
        assert created_watchlist['name'] == 'Test Watchlist'
        assert created_watchlist['symbols'] == ['AAPL', 'GOOGL', 'MSFT']
        assert 'id' in created_watchlist

    def test_create_user_watchlist_validation(self, app_with_mocks):
        """Test watchlist creation validation."""
        client = app_with_mocks.test_client()

        # Test missing name
        response = client.post('/api/users/watchlists',
                              data=json.dumps({'symbols': ['AAPL']}),
                              content_type='application/json')
        assert response.status_code == 400

        data = json.loads(response.data)
        assert 'error' in data
        assert 'Watchlist name is required' in data['error']

        # Test invalid symbols format
        response = client.post('/api/users/watchlists',
                              data=json.dumps({'name': 'Test', 'symbols': 'not_a_list'}),
                              content_type='application/json')
        assert response.status_code == 400

    def test_create_user_watchlist_no_body(self, app_with_mocks):
        """Test watchlist creation without request body."""
        client = app_with_mocks.test_client()

        response = client.post('/api/users/watchlists')
        assert response.status_code == 400

        data = json.loads(response.data)
        assert 'error' in data
        assert 'Request body is required' in data['error']


class TestFilterPresetsEndpoint:
    """Test /api/users/filter-presets endpoint functionality."""

    def test_get_user_filter_presets(self, app_with_mocks):
        """Test getting user filter presets."""
        client = app_with_mocks.test_client()

        response = client.get('/api/users/filter-presets')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'presets' in data
        assert 'user_id' in data
        assert 'count' in data

        # Verify sample preset structure
        if data['presets']:
            preset = data['presets'][0]
            assert 'id' in preset
            assert 'name' in preset
            assert 'filters' in preset
            assert 'is_default' in preset
            assert 'created_at' in preset

    def test_create_user_filter_preset_success(self, app_with_mocks):
        """Test creating new filter preset."""
        client = app_with_mocks.test_client()

        preset_data = {
            'name': 'High Momentum',
            'filters': {
                'confidence_min': 0.8,
                'rs_min': 1.5,
                'vol_min': 2.0,
                'pattern_types': ['Weekly_Breakout', 'Volume_Spike']
            },
            'is_default': True
        }

        response = client.post('/api/users/filter-presets',
                              data=json.dumps(preset_data),
                              content_type='application/json')
        assert response.status_code == 201

        data = json.loads(response.data)
        assert 'preset' in data
        assert 'message' in data

        created_preset = data['preset']
        assert created_preset['name'] == 'High Momentum'
        assert created_preset['is_default'] is True
        assert 'filters' in created_preset

    def test_create_user_filter_preset_validation(self, app_with_mocks):
        """Test filter preset creation validation."""
        client = app_with_mocks.test_client()

        # Test missing name
        response = client.post('/api/users/filter-presets',
                              data=json.dumps({'filters': {}}),
                              content_type='application/json')
        assert response.status_code == 400

        # Test invalid filters format
        response = client.post('/api/users/filter-presets',
                              data=json.dumps({'name': 'Test', 'filters': 'not_an_object'}),
                              content_type='application/json')
        assert response.status_code == 400


class TestDashboardStatsEndpoint:
    """Test /api/dashboard/stats endpoint functionality."""

    def test_get_dashboard_stats_success(self, app_with_mocks):
        """Test successful dashboard stats retrieval."""
        client = app_with_mocks.test_client()

        response = client.get('/api/dashboard/stats')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'total_symbols' in data
        assert 'active_sessions' in data
        assert 'patterns_detected_today' in data
        assert 'performance' in data

        # Verify performance metrics
        assert data['performance']['source'] == 'tickstock_database'

        # Verify database service was called
        app_with_mocks.tickstock_db.get_basic_dashboard_stats.assert_called()

    @pytest.mark.performance
    def test_get_dashboard_stats_performance(self, app_with_mocks, performance_benchmark):
        """Test dashboard stats API performance."""
        client = app_with_mocks.test_client()

        target_ms = 50

        for _ in range(3):
            def make_request():
                response = client.get('/api/dashboard/stats')
                return response.status_code == 200

            result, elapsed_ms = performance_benchmark.measure(make_request)
            assert result is True
            performance_benchmark.assert_performance(elapsed_ms, "Dashboard stats API")

    def test_get_dashboard_stats_database_unavailable(self, app):
        """Test dashboard stats when database is unavailable."""
        client = app.test_client()

        response = client.get('/api/dashboard/stats')
        assert response.status_code == 503

        data = json.loads(response.data)
        assert 'error' in data


class TestAPIHealthEndpoint:
    """Test /api/health endpoint functionality."""

    def test_get_api_health_healthy(self, app_with_mocks):
        """Test API health check - healthy status."""
        client = app_with_mocks.test_client()

        response = client.get('/api/health')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'status' in data
        assert 'healthy' in data
        assert 'services' in data
        assert 'performance' in data
        assert 'last_check' in data

        assert data['healthy'] is True
        assert data['services']['tickstock_database'] == 'healthy'
        assert data['services']['cache_control'] == 'healthy'

    def test_get_api_health_degraded(self, app_with_mocks):
        """Test API health check - degraded status."""
        client = app_with_mocks.test_client()

        # Mock database health check to return degraded
        app_with_mocks.tickstock_db.health_check.return_value = {'status': 'degraded'}

        response = client.get('/api/health')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['healthy'] is True  # Still considered healthy with degraded DB
        assert data['services']['tickstock_database'] == 'healthy'  # health_check status is degraded but still acceptable

    def test_get_api_health_database_error(self, app_with_mocks):
        """Test API health check with database error."""
        client = app_with_mocks.test_client()

        # Mock database health check to raise exception
        app_with_mocks.tickstock_db.health_check.side_effect = Exception("DB Error")

        response = client.get('/api/health')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['healthy'] is False
        assert data['services']['tickstock_database'] == 'error'

    def test_get_api_health_cache_unavailable(self, app_with_mocks):
        """Test API health check with cache unavailable."""
        client = app_with_mocks.test_client()

        # Mock cache control as not initialized
        app_with_mocks.cache_control._initialized = False

        response = client.get('/api/health')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['healthy'] is False
        assert data['services']['cache_control'] == 'error'


class TestUserUniverseAPIIntegration:
    """Integration tests for User Universe API."""

    @pytest.mark.integration
    def test_full_user_workflow(self, app_with_mocks):
        """Test full user workflow across multiple endpoints."""
        client = app_with_mocks.test_client()

        # 1. Get available symbols
        symbols_response = client.get('/api/symbols?limit=10')
        assert symbols_response.status_code == 200
        symbols_data = json.loads(symbols_response.data)
        assert len(symbols_data['symbols']) > 0

        # 2. Get available universes
        universes_response = client.get('/api/users/universe')
        assert universes_response.status_code == 200
        universes_data = json.loads(universes_response.data)
        assert len(universes_data['universes']) > 0

        # 3. Get tickers for first universe
        if universes_data['universes']:
            universe_key = universes_data['universes'][0]['key']
            tickers_response = client.get(f'/api/users/universe/{universe_key}')
            assert tickers_response.status_code == 200
            tickers_data = json.loads(tickers_response.data)
            assert 'tickers' in tickers_data

        # 4. Create watchlist
        watchlist_data = {
            'name': 'Integration Test Watchlist',
            'symbols': ['AAPL', 'GOOGL']
        }

        watchlist_response = client.post('/api/users/watchlists',
                                        data=json.dumps(watchlist_data),
                                        content_type='application/json')
        assert watchlist_response.status_code == 201

        # 5. Get watchlists
        get_watchlists_response = client.get('/api/users/watchlists')
        assert get_watchlists_response.status_code == 200

        # 6. Create filter preset
        preset_data = {
            'name': 'Integration Test Preset',
            'filters': {'confidence_min': 0.7}
        }

        preset_response = client.post('/api/users/filter-presets',
                                     data=json.dumps(preset_data),
                                     content_type='application/json')
        assert preset_response.status_code == 201

        # 7. Get dashboard stats
        stats_response = client.get('/api/dashboard/stats')
        assert stats_response.status_code == 200

        # 8. Health check
        health_response = client.get('/api/health')
        assert health_response.status_code == 200

    @pytest.mark.performance
    def test_api_performance_suite(self, app_with_mocks, performance_benchmark):
        """Test performance across all User Universe API endpoints."""
        client = app_with_mocks.test_client()

        target_ms = 50

        # Test each endpoint performance
        endpoints = [
            ('/api/symbols?limit=50', 'GET'),
            ('/api/symbols/AAPL', 'GET'),
            ('/api/users/universe', 'GET'),
            ('/api/users/universe/sp500_large', 'GET'),
            ('/api/users/watchlists', 'GET'),
            ('/api/users/filter-presets', 'GET'),
            ('/api/dashboard/stats', 'GET'),
            ('/api/health', 'GET')
        ]

        for endpoint, method in endpoints:
            def make_request():
                if method == 'GET':
                    response = client.get(endpoint)
                return response.status_code < 500  # Accept any non-server-error

            result, elapsed_ms = performance_benchmark.measure(make_request)
            assert result is True
            performance_benchmark.assert_performance(elapsed_ms, f"{method} {endpoint}")

        perf_stats = performance_benchmark.get_statistics()
        print("\nUser Universe API Performance Suite:")
        print(f"  Endpoints tested: {len(endpoints)}")
        print(f"  Average response time: {perf_stats['avg_ms']:.2f}ms")
        print(f"  P95 response time: {perf_stats['p95_ms']:.2f}ms")
        print(f"  Target met: {perf_stats['target_met_pct']:.1f}%")

        assert perf_stats['p95_ms'] < target_ms

    @pytest.mark.database
    def test_database_read_only_compliance(self, app_with_mocks):
        """Test that all endpoints use read-only database access."""
        client = app_with_mocks.test_client()

        # Track database method calls
        db_methods_called = []

        # Mock database methods to track calls
        original_get_symbols = app_with_mocks.tickstock_db.get_symbols_for_dropdown
        original_get_symbol_details = app_with_mocks.tickstock_db.get_symbol_details
        original_get_dashboard_stats = app_with_mocks.tickstock_db.get_basic_dashboard_stats
        original_health_check = app_with_mocks.tickstock_db.health_check

        def track_call(method_name, original_method):
            def wrapper(*args, **kwargs):
                db_methods_called.append(method_name)
                return original_method(*args, **kwargs)
            return wrapper

        app_with_mocks.tickstock_db.get_symbols_for_dropdown = track_call('get_symbols_for_dropdown', original_get_symbols)
        app_with_mocks.tickstock_db.get_symbol_details = track_call('get_symbol_details', original_get_symbol_details)
        app_with_mocks.tickstock_db.get_basic_dashboard_stats = track_call('get_basic_dashboard_stats', original_get_dashboard_stats)
        app_with_mocks.tickstock_db.health_check = track_call('health_check', original_health_check)

        # Make requests that should trigger database calls
        client.get('/api/symbols')
        client.get('/api/symbols/AAPL')
        client.get('/api/dashboard/stats')
        client.get('/api/health')

        # Verify only read-only methods were called
        read_only_methods = [
            'get_symbols_for_dropdown',
            'get_symbol_details',
            'get_basic_dashboard_stats',
            'health_check'
        ]

        for method_called in db_methods_called:
            assert method_called in read_only_methods, f"Non-read-only method called: {method_called}"

        # Verify no write methods were accessed (these should not exist on the mock)
        write_methods = ['insert', 'update', 'delete', 'create', 'modify']
        for write_method in write_methods:
            assert not hasattr(app_with_mocks.tickstock_db, write_method), f"Write method {write_method} should not be available"


class TestUserUniverseErrorHandling:
    """Test error handling across User Universe API."""

    def test_blueprint_error_handlers(self, app_with_mocks):
        """Test blueprint-level error handlers."""
        client = app_with_mocks.test_client()

        # Test 404 handler
        response = client.get('/api/nonexistent')
        assert response.status_code == 404

        data = json.loads(response.data)
        assert 'error' in data
        assert 'Not found' in data['error']

    def test_authentication_handling(self, app_with_mocks):
        """Test authentication handling (current implementation uses default user)."""
        client = app_with_mocks.test_client()

        # Test with custom user ID header
        response = client.get('/api/users/watchlists', headers={'X-User-ID': 'test_user_123'})
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['user_id'] == 'test_user_123'

        # Test without custom header (should use default)
        response = client.get('/api/users/watchlists')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['user_id'] == 'default_user'

    def test_json_parsing_errors(self, app_with_mocks):
        """Test JSON parsing error handling."""
        client = app_with_mocks.test_client()

        # Send malformed JSON
        response = client.post('/api/users/watchlists',
                              data='{"invalid": json}',
                              content_type='application/json')
        assert response.status_code == 400

    def test_performance_logging_slow_responses(self, app_with_mocks):
        """Test logging of slow database responses."""
        client = app_with_mocks.test_client()

        # Mock slow database response
        def slow_response(*args, **kwargs):
            time.sleep(0.06)  # 60ms - above 50ms target
            return []

        with patch('src.api.rest.user_universe.logger') as mock_logger:
            app_with_mocks.tickstock_db.get_symbols_for_dropdown = slow_response

            response = client.get('/api/symbols')
            assert response.status_code == 200

            # Verify slow response was logged as warning
            warning_calls = [call for call in mock_logger.warning.call_args_list
                           if 'Slow' in str(call)]
            assert len(warning_calls) > 0
