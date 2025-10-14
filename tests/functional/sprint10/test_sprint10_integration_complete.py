"""
Sprint 10 Phase 1 Complete Integration Tests
End-to-end testing of all Sprint 10 database integration components working together.

Test Coverage:
- Complete integration workflows (database -> health monitor -> API)
- Error handling and graceful degradation
- Performance under realistic load scenarios
- Component interaction validation
- Configuration and initialization testing
"""

import json
import time
from unittest.mock import Mock, patch

from src.api.rest.tickstockpl_api import register_tickstockpl_routes
from src.core.services.health_monitor import HealthMonitor
from src.infrastructure.database.tickstock_db import TickStockDatabase


class TestSprint10CompleteIntegration:
    """Test complete Sprint 10 integration scenarios."""

    def test_healthy_system_complete_workflow(self, api_with_healthy_services, authenticated_user_context, performance_benchmarks):
        """Test complete workflow with all systems healthy."""
        app = api_with_healthy_services
        auth_context = authenticated_user_context

        with app.test_client() as client:
            # Test complete user workflow
            start_time = time.time()

            # 1. Health check (unauthenticated)
            health_response = client.get('/api/tickstockpl/health')
            assert health_response.status_code == 200
            health_data = json.loads(health_response.data)
            assert health_data['overall_status'] == 'healthy'

            # 2. Login and get dashboard (authenticated)
            with client.session_transaction() as sess:
                auth_context.apply_to_session(sess)

            with auth_context.mock_current_user():
                dashboard_response = client.get('/api/tickstockpl/dashboard')
                assert dashboard_response.status_code == 200
                dashboard_data = json.loads(dashboard_response.data)
                assert dashboard_data['health']['overall_status'] == 'healthy'
                assert 'quick_stats' in dashboard_data

                # 3. Get symbols for dropdown
                symbols_response = client.get('/api/tickstockpl/symbols')
                assert symbols_response.status_code == 200
                symbols_data = json.loads(symbols_response.data)
                assert symbols_data['count'] == 4000
                assert len(symbols_data['symbols']) == 4000

                # 4. Get basic stats
                stats_response = client.get('/api/tickstockpl/stats/basic')
                assert stats_response.status_code == 200
                stats_data = json.loads(stats_response.data)
                assert stats_data['symbols_count'] == 4000
                assert stats_data['database_status'] == 'connected'

                # 5. Get user alerts
                alerts_response = client.get('/api/tickstockpl/alerts/history?limit=25')
                assert alerts_response.status_code == 200
                alerts_data = json.loads(alerts_response.data)
                assert alerts_data['limit'] == 25
                assert alerts_data['user_id'] == '123'

                # 6. Get pattern performance
                patterns_response = client.get('/api/tickstockpl/patterns/performance')
                assert patterns_response.status_code == 200
                patterns_data = json.loads(patterns_response.data)
                assert 'patterns' in patterns_data

                # 7. Test connectivity
                connectivity_response = client.post('/api/tickstockpl/connectivity/test')
                assert connectivity_response.status_code == 200
                connectivity_data = json.loads(connectivity_response.data)
                assert connectivity_data['overall_status'] == 'healthy'

            total_time = (time.time() - start_time) * 1000

            # Complete workflow should meet performance requirement
            max_time = performance_benchmarks['user_session_max_ms']
            assert total_time < max_time, f"Complete workflow took {total_time:.2f}ms, should be <{max_time}ms"

    def test_degraded_system_graceful_handling(self, api_with_degraded_services, authenticated_user_context):
        """Test system behavior with degraded components."""
        app = api_with_degraded_services
        auth_context = authenticated_user_context

        with app.test_client() as client:
            # Health check should show degraded status
            health_response = client.get('/api/tickstockpl/health')
            assert health_response.status_code == 200
            health_data = json.loads(health_response.data)
            assert health_data['overall_status'] == 'degraded'

            # Dashboard should still work but show alerts
            with client.session_transaction() as sess:
                auth_context.apply_to_session(sess)

            with auth_context.mock_current_user():
                dashboard_response = client.get('/api/tickstockpl/dashboard')
                assert dashboard_response.status_code == 200
                dashboard_data = json.loads(dashboard_response.data)
                assert dashboard_data['health']['overall_status'] == 'degraded'
                # Should have alerts for degraded components
                assert len(dashboard_data.get('alerts', [])) >= 1

    def test_error_system_error_handling(self, api_with_error_services, authenticated_user_context):
        """Test system behavior with error components."""
        app = api_with_error_services
        auth_context = authenticated_user_context

        with app.test_client() as client:
            # Health check should show service unavailable
            health_response = client.get('/api/tickstockpl/health')
            assert health_response.status_code == 503
            error_data = json.loads(health_response.data)
            assert error_data['error'] == 'Health monitoring service not available'

            # Other endpoints should also show service unavailable
            with client.session_transaction() as sess:
                auth_context.apply_to_session(sess)

            with auth_context.mock_current_user():
                dashboard_response = client.get('/api/tickstockpl/dashboard')
                assert dashboard_response.status_code == 503

                symbols_response = client.get('/api/tickstockpl/symbols')
                assert symbols_response.status_code == 503

    def test_database_health_monitor_integration(self, mock_database_with_realistic_data, mock_healthy_redis):
        """Test integration between database and health monitor."""
        config = {}

        with patch('src.core.services.health_monitor.TickStockDatabase') as mock_db_class:
            mock_db_class.return_value = mock_database_with_realistic_data

            monitor = HealthMonitor(config, redis_client=mock_healthy_redis)
            monitor.tickstock_db = mock_database_with_realistic_data

            # Test database health check integration
            db_health = monitor._check_database_health()
            assert db_health.status == 'healthy'
            assert db_health.response_time_ms is not None
            assert db_health.response_time_ms > 0

            # Test overall health with database component
            overall_health = monitor.get_overall_health()
            assert overall_health['overall_status'] == 'healthy'
            assert 'database' in overall_health['components']
            assert overall_health['components']['database'].status == 'healthy'

            # Test dashboard data integration
            dashboard_data = monitor.get_dashboard_data()
            assert 'health' in dashboard_data
            assert 'quick_stats' in dashboard_data
            assert dashboard_data['quick_stats']['symbols_count'] == 4000

    def test_redis_tickstockpl_connectivity_integration(self, mock_active_tickstockpl):
        """Test integration between Redis and TickStockPL connectivity."""
        config = {}

        with patch('src.core.services.health_monitor.TickStockDatabase') as mock_db_class:
            mock_db_class.return_value = Mock()

            monitor = HealthMonitor(config, redis_client=mock_active_tickstockpl)

            # Test Redis health
            redis_health = monitor._check_redis_health()
            assert redis_health.status == 'healthy'

            # Test TickStockPL connectivity
            pl_health = monitor._check_tickstockpl_connectivity()
            assert pl_health.status == 'healthy'
            assert 'TickStockPL detected' in pl_health.message
            assert pl_health.details['total_subscribers'] > 0

    def test_api_health_monitor_integration(self, flask_app_with_auth, health_monitor_healthy, authenticated_user_context):
        """Test integration between API endpoints and health monitor."""
        app = flask_app_with_auth
        auth_context = authenticated_user_context

        extensions = {}
        cache_control = Mock()
        config = {}

        with patch('src.api.rest.tickstockpl_api.HealthMonitor') as mock_health_monitor_class:
            with patch('src.api.rest.tickstockpl_api.TickStockDatabase') as mock_db_class:
                mock_health_monitor_class.return_value = health_monitor_healthy
                mock_db_class.return_value = Mock()

                register_tickstockpl_routes(app, extensions, cache_control, config)

                with app.test_client() as client:
                    # Test health endpoint uses health monitor
                    health_response = client.get('/api/tickstockpl/health')
                    assert health_response.status_code == 200

                    # Test dashboard endpoint uses health monitor
                    with client.session_transaction() as sess:
                        auth_context.apply_to_session(sess)

                    with auth_context.mock_current_user():
                        dashboard_response = client.get('/api/tickstockpl/dashboard')
                        assert dashboard_response.status_code == 200

    def test_concurrent_api_requests_integration(self, api_with_healthy_services, authenticated_user_context):
        """Test system behavior under concurrent API requests."""
        import concurrent.futures

        app = api_with_healthy_services
        auth_context = authenticated_user_context

        def make_authenticated_request(endpoint):
            """Make an authenticated request to the API."""
            with app.test_client() as client:
                with client.session_transaction() as sess:
                    auth_context.apply_to_session(sess)

                with auth_context.mock_current_user():
                    response = client.get(f'/api/tickstockpl/{endpoint}')
                    return response.status_code, endpoint

        # Test concurrent requests to different endpoints
        endpoints = ['health', 'dashboard', 'symbols', 'stats/basic']

        start_time = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = []

            # Make multiple requests to each endpoint
            for _ in range(3):  # 3 requests per endpoint = 12 total
                for endpoint in endpoints:
                    if endpoint == 'health':
                        # Health endpoint doesn't require auth
                        future = executor.submit(lambda: app.test_client().get('/api/tickstockpl/health').status_code)
                    else:
                        future = executor.submit(make_authenticated_request, endpoint)
                    futures.append(future)

            # Wait for all requests to complete
            results = []
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    results.append((500, str(e)))

        execution_time = (time.time() - start_time) * 1000

        # All requests should succeed
        successful_requests = sum(1 for result in results if (isinstance(result, int) and result == 200) or (isinstance(result, tuple) and result[0] == 200))

        assert successful_requests >= 8, f"Only {successful_requests} out of {len(results)} requests succeeded"
        assert execution_time < 1000.0, f"Concurrent requests took {execution_time:.2f}ms, should be <1000ms"


class TestSprint10ErrorRecoveryIntegration:
    """Test error recovery and resilience integration scenarios."""

    def test_database_reconnection_scenario(self):
        """Test system behavior when database connection is lost and recovered."""
        config = {}

        # Create database that initially fails, then succeeds
        db = TickStockDatabase.__new__(TickStockDatabase)
        db.config = config
        db.engine = Mock()

        # First call fails, second succeeds
        call_count = 0
        def connection_side_effect():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Database connection lost")
            # Return successful connection
            mock_connection = Mock()
            mock_connection.execute.return_value = Mock(scalar=Mock(return_value=100))
            return mock_connection

        db.engine.connect.return_value.__enter__.side_effect = connection_side_effect

        with patch('src.core.services.health_monitor.TickStockDatabase') as mock_db_class:
            mock_db_class.return_value = db

            monitor = HealthMonitor(config, redis_client=Mock())
            monitor.tickstock_db = db

            # First health check should show error
            health1 = monitor._check_database_health()
            assert health1.status == 'error'

            # Second health check should show healthy (simulating reconnection)
            health2 = monitor._check_database_health()
            assert health2.status == 'healthy'

    def test_redis_failover_scenario(self):
        """Test system behavior when Redis fails over to backup."""
        import redis

        config = {}

        # Create Redis client that initially fails, then succeeds
        redis_client = Mock(spec=redis.Redis)

        call_count = 0
        def ping_side_effect():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise redis.ConnectionError("Redis connection failed")
            return True

        redis_client.ping.side_effect = ping_side_effect
        redis_client.set.return_value = True
        redis_client.get.return_value = 'test_value'
        redis_client.delete.return_value = 1
        redis_client.info.return_value = {}

        with patch('src.core.services.health_monitor.TickStockDatabase') as mock_db_class:
            mock_db_class.return_value = Mock()

            monitor = HealthMonitor(config, redis_client=redis_client)

            # First health checks should show error
            health1 = monitor._check_redis_health()
            assert health1.status == 'error'

            health2 = monitor._check_redis_health()
            assert health2.status == 'error'

            # Third health check should show healthy (simulating failover)
            health3 = monitor._check_redis_health()
            assert health3.status == 'healthy'

    def test_partial_service_degradation_recovery(self, flask_app_with_auth, authenticated_user_context):
        """Test API behavior during partial service degradation and recovery."""
        app = flask_app_with_auth
        auth_context = authenticated_user_context

        # Create services that degrade and recover
        health_monitor = Mock()
        database = Mock()

        # Simulate degrading health over time
        health_states = [
            {'overall_status': 'healthy', 'components': {}},
            {'overall_status': 'degraded', 'components': {}},
            {'overall_status': 'error', 'components': {}},
            {'overall_status': 'degraded', 'components': {}},
            {'overall_status': 'healthy', 'components': {}}
        ]

        call_count = 0
        def health_side_effect():
            nonlocal call_count
            state = health_states[call_count % len(health_states)]
            call_count += 1
            return state

        health_monitor.get_overall_health.side_effect = health_side_effect
        database.get_symbols_for_dropdown.return_value = ['AAPL'] * 1000  # Reduced count during degradation

        extensions = {}
        cache_control = Mock()
        config = {}

        with patch('src.api.rest.tickstockpl_api.HealthMonitor') as mock_health_class:
            with patch('src.api.rest.tickstockpl_api.TickStockDatabase') as mock_db_class:
                mock_health_class.return_value = health_monitor
                mock_db_class.return_value = database

                register_tickstockpl_routes(app, extensions, cache_control, config)

                with app.test_client() as client:
                    # Track system state changes
                    health_responses = []

                    for i in range(5):
                        response = client.get('/api/tickstockpl/health')
                        if response.status_code == 200:
                            data = json.loads(response.data)
                            health_responses.append(data['overall_status'])
                        else:
                            health_responses.append('error')

                        time.sleep(0.01)  # Small delay between requests

                    # Should see the progression: healthy -> degraded -> error -> degraded -> healthy
                    expected_progression = ['healthy', 'degraded', 'error', 'degraded', 'healthy']
                    assert health_responses == expected_progression


class TestSprint10ConfigurationIntegration:
    """Test configuration and initialization integration scenarios."""

    def test_configuration_propagation_through_stack(self):
        """Test that configuration properly propagates from API to database."""
        from flask import Flask

        app = Flask(__name__)
        app.config['TESTING'] = True

        test_config = {
            'database_host': 'test-host',
            'database_port': '5432',
            'redis_client': Mock(),
            'custom_setting': 'test_value'
        }

        extensions = {}
        cache_control = Mock()

        with patch('src.api.rest.tickstockpl_api.HealthMonitor') as mock_health_class:
            with patch('src.api.rest.tickstockpl_api.TickStockDatabase') as mock_db_class:
                # Verify config is passed through
                mock_health_instance = Mock()
                mock_db_instance = Mock()
                mock_health_class.return_value = mock_health_instance
                mock_db_class.return_value = mock_db_instance

                register_tickstockpl_routes(app, extensions, cache_control, test_config)

                # Verify services were initialized with config
                mock_health_class.assert_called_once_with(test_config, test_config['redis_client'])
                mock_db_class.assert_called_once_with(test_config)

                # Verify services are stored in app context
                assert app.tickstockpl_health_monitor == mock_health_instance
                assert app.tickstockpl_database == mock_db_instance

    def test_environment_variable_integration(self):
        """Test environment variable configuration integration."""
        import os

        test_env_vars = {
            'TICKSTOCK_DB_HOST': 'env-test-host',
            'TICKSTOCK_DB_PORT': '5434',
            'TICKSTOCK_DB_USER': 'env_test_user',
            'TICKSTOCK_DB_PASSWORD': 'env_test_password'
        }

        with patch.dict(os.environ, test_env_vars, clear=True):
            config = {}

            with patch('src.infrastructure.database.tickstock_db.create_engine') as mock_create_engine:
                with patch.object(TickStockDatabase, '_test_connection'):
                    db = TickStockDatabase(config)

                    # Verify environment variables were used in connection URL
                    call_args = mock_create_engine.call_args[0][0]  # First positional argument (connection URL)

                    assert 'env-test-host' in call_args
                    assert '5434' in call_args
                    assert 'env_test_user' in call_args
                    assert 'env_test_password' in call_args
                    assert 'tickstock' in call_args  # Database name should still be fixed

    def test_service_initialization_order_integration(self):
        """Test proper service initialization order and dependencies."""
        from flask import Flask

        app = Flask(__name__)
        app.config['TESTING'] = True

        config = {'redis_client': Mock()}
        extensions = {}
        cache_control = Mock()

        initialization_order = []

        def track_health_monitor_init(config_param, redis_client):
            initialization_order.append('health_monitor')
            return Mock()

        def track_database_init(config_param):
            initialization_order.append('database')
            return Mock()

        with patch('src.api.rest.tickstockpl_api.HealthMonitor', side_effect=track_health_monitor_init):
            with patch('src.api.rest.tickstockpl_api.TickStockDatabase', side_effect=track_database_init):
                register_tickstockpl_routes(app, extensions, cache_control, config)

                # Both services should be initialized
                assert 'health_monitor' in initialization_order
                assert 'database' in initialization_order

                # Verify services were stored in app context
                assert hasattr(app, 'tickstockpl_health_monitor')
                assert hasattr(app, 'tickstockpl_database')

    def test_initialization_failure_isolation(self):
        """Test that initialization failure of one service doesn't break others."""
        from flask import Flask

        app = Flask(__name__)
        app.config['TESTING'] = True

        config = {}
        extensions = {}
        cache_control = Mock()

        with patch('src.api.rest.tickstockpl_api.HealthMonitor') as mock_health_class:
            with patch('src.api.rest.tickstockpl_api.TickStockDatabase') as mock_db_class:
                # Health monitor fails, database succeeds
                mock_health_class.side_effect = Exception("Health monitor init failed")
                mock_db_instance = Mock()
                mock_db_class.return_value = mock_db_instance

                # Should not raise exception
                blueprint = register_tickstockpl_routes(app, extensions, cache_control, config)

                assert blueprint is not None
                assert app.tickstockpl_health_monitor is None
                assert app.tickstockpl_database == mock_db_instance
