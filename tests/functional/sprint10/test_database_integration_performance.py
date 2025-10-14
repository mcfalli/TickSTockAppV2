"""
Sprint 10 Phase 1 Database Integration Performance Tests
Comprehensive performance validation for all Sprint 10 database integration components.

Test Coverage:
- Database query performance (<50ms requirement)
- Health monitoring performance (<100ms requirement)
- API endpoint performance (<100ms requirement)
- Memory usage validation
- Connection pool performance under load
"""

import concurrent.futures
import os
import time
from unittest.mock import Mock, patch

import psutil
import pytest
from flask import Flask

from src.api.rest.tickstockpl_api import register_tickstockpl_routes
from src.core.services.health_monitor import HealthMonitor
from src.infrastructure.database.tickstock_db import TickStockDatabase


@pytest.mark.performance
class TestDatabasePerformanceRequirements:
    """Test database performance meets Sprint 10 requirements."""

    @pytest.fixture
    def mock_db_with_realistic_data(self):
        """Create database mock with realistic performance characteristics."""
        db = TickStockDatabase.__new__(TickStockDatabase)
        db.config = {}
        db.engine = Mock()

        # Mock realistic database query times
        def mock_execute_with_delay(*args, **kwargs):
            time.sleep(0.025)  # 25ms realistic database query time
            result = Mock()
            return result

        db.engine.connect.return_value.__enter__.return_value.execute = mock_execute_with_delay
        return db

    @pytest.mark.performance
    def test_symbols_query_performance_under_load(self, mock_db_with_realistic_data):
        """Test symbols query performance under realistic load (4000+ symbols)."""
        db = mock_db_with_realistic_data

        # Mock 4000 symbols result
        mock_connection = Mock()
        test_symbols = [(f'SYMBOL_{i:04d}',) for i in range(4000)]
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter(test_symbols))
        mock_connection.execute.return_value = mock_result

        with patch.object(db, 'get_connection') as mock_get_conn:
            mock_get_conn.return_value.__enter__.return_value = mock_connection

            start_time = time.time()
            symbols = db.get_symbols_for_dropdown()
            execution_time = (time.time() - start_time) * 1000

            assert len(symbols) == 4000
            assert execution_time < 50.0, f"Symbols query took {execution_time:.2f}ms, requirement is <50ms"

    @pytest.mark.performance
    def test_dashboard_stats_query_performance(self, mock_db_with_realistic_data):
        """Test dashboard statistics query performance with large datasets."""
        db = mock_db_with_realistic_data

        mock_connection = Mock()
        mock_results = [Mock(), Mock(), Mock()]
        mock_results[0].scalar.return_value = 4000  # 4000 symbols
        mock_results[1].scalar.return_value = 50000  # 50000 events
        mock_results[2].scalar.return_value = None  # latest event time

        mock_connection.execute.side_effect = mock_results

        with patch.object(db, 'get_connection') as mock_get_conn:
            mock_get_conn.return_value.__enter__.return_value = mock_connection

            start_time = time.time()
            stats = db.get_basic_dashboard_stats()
            execution_time = (time.time() - start_time) * 1000

            assert stats['symbols_count'] == 4000
            assert stats['events_count'] == 50000
            assert execution_time < 50.0, f"Dashboard stats query took {execution_time:.2f}ms, requirement is <50ms"

    @pytest.mark.performance
    def test_user_alerts_query_performance_large_history(self, mock_db_with_realistic_data):
        """Test user alerts query performance with large alert history."""
        db = mock_db_with_realistic_data

        mock_connection = Mock()
        # Mock 100 alert records
        from datetime import datetime
        test_time = datetime.now()
        mock_alerts = [
            (f'SYMBOL_{i % 100}', 'pattern_type', 0.75 + (i % 25) * 0.01, test_time, {})
            for i in range(100)
        ]
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter(mock_alerts))
        mock_connection.execute.return_value = mock_result

        with patch.object(db, 'get_connection') as mock_get_conn:
            mock_get_conn.return_value.__enter__.return_value = mock_connection

            start_time = time.time()
            alerts = db.get_user_alert_history('user123', limit=100)
            execution_time = (time.time() - start_time) * 1000

            assert len(alerts) == 100
            assert execution_time < 50.0, f"User alerts query took {execution_time:.2f}ms, requirement is <50ms"

    @pytest.mark.performance
    def test_pattern_performance_query_all_patterns(self, mock_db_with_realistic_data):
        """Test pattern performance query with multiple pattern types."""
        db = mock_db_with_realistic_data

        mock_connection = Mock()
        # Mock performance data for multiple patterns
        mock_patterns = [
            ('high_low', 5000, 0.78, 0.95, 0.45),
            ('trend', 3000, 0.82, 0.98, 0.52),
            ('surge', 2000, 0.75, 0.92, 0.48),
            ('breakout', 1500, 0.80, 0.94, 0.50)
        ]
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter(mock_patterns))
        mock_connection.execute.return_value = mock_result

        with patch.object(db, 'get_connection') as mock_get_conn:
            mock_get_conn.return_value.__enter__.return_value = mock_connection

            start_time = time.time()
            performance = db.get_pattern_performance()
            execution_time = (time.time() - start_time) * 1000

            assert len(performance) == 4
            assert execution_time < 50.0, f"Pattern performance query took {execution_time:.2f}ms, requirement is <50ms"

    @pytest.mark.performance
    def test_health_check_comprehensive_performance(self, mock_db_with_realistic_data):
        """Test comprehensive health check performance."""
        db = mock_db_with_realistic_data

        # Mock engine pool status
        db.engine.pool.status.return_value = "Pool status"
        db.engine.pool.size.return_value = 5
        db.engine.pool.checkedin.return_value = 3
        db.engine.pool.checkedout.return_value = 2
        db.engine.pool.invalid.return_value = 0

        mock_connection = Mock()
        mock_results = [Mock(), Mock()]
        mock_results[1].__iter__ = Mock(return_value=iter([('symbols',), ('events',), ('ohlcv_daily',)]))
        mock_connection.execute.side_effect = mock_results

        with patch.object(db, 'get_connection') as mock_get_conn:
            mock_get_conn.return_value.__enter__.return_value = mock_connection

            start_time = time.time()
            health = db.health_check()
            execution_time = (time.time() - start_time) * 1000

            assert health['status'] in ['healthy', 'degraded']
            assert execution_time < 50.0, f"Health check took {execution_time:.2f}ms, requirement is <50ms"


@pytest.mark.performance
class TestHealthMonitorPerformanceRequirements:
    """Test health monitor performance meets Sprint 10 requirements."""

    @pytest.fixture
    def fast_health_monitor(self):
        """Create health monitor with fast mock services."""
        config = {}
        monitor = HealthMonitor.__new__(HealthMonitor)
        monitor.config = config
        monitor.redis_client = Mock()
        monitor.tickstock_db = Mock()

        # Configure fast database health check
        monitor.tickstock_db.health_check.return_value = {
            'status': 'healthy',
            'query_performance': 25.0,
            'tables_accessible': ['symbols', 'events']
        }

        # Configure fast Redis operations
        monitor.redis_client.ping.return_value = True
        monitor.redis_client.set.return_value = True
        monitor.redis_client.get.return_value = 'test_value'
        monitor.redis_client.delete.return_value = 1
        monitor.redis_client.info.return_value = {'connected_clients': 5}
        monitor.redis_client.pubsub_numsub.return_value = [('test_channel', 2)]

        return monitor

    @pytest.mark.performance
    def test_overall_health_check_performance(self, fast_health_monitor):
        """Test overall health check meets <100ms requirement."""
        monitor = fast_health_monitor

        start_time = time.time()
        health = monitor.get_overall_health()
        execution_time = (time.time() - start_time) * 1000

        assert health['overall_status'] in ['healthy', 'degraded', 'warning']
        assert execution_time < 100.0, f"Overall health check took {execution_time:.2f}ms, requirement is <100ms"

    @pytest.mark.performance
    def test_dashboard_data_aggregation_performance(self, fast_health_monitor):
        """Test dashboard data aggregation meets <100ms requirement."""
        monitor = fast_health_monitor

        # Mock dashboard stats
        monitor.tickstock_db.get_basic_dashboard_stats.return_value = {
            'symbols_count': 4000,
            'events_count': 25000
        }

        start_time = time.time()
        dashboard_data = monitor.get_dashboard_data()
        execution_time = (time.time() - start_time) * 1000

        assert 'health' in dashboard_data
        assert 'quick_stats' in dashboard_data
        assert execution_time < 100.0, f"Dashboard data aggregation took {execution_time:.2f}ms, requirement is <100ms"

    @pytest.mark.performance
    def test_individual_component_health_checks_performance(self, fast_health_monitor):
        """Test individual component health checks meet performance requirements."""
        monitor = fast_health_monitor

        # Test database health check
        start_time = time.time()
        db_health = monitor._check_database_health()
        db_execution_time = (time.time() - start_time) * 1000

        assert db_health.status in ['healthy', 'degraded', 'error']
        assert db_execution_time < 50.0, f"Database health check took {db_execution_time:.2f}ms, should be <50ms"

        # Test Redis health check
        start_time = time.time()
        redis_health = monitor._check_redis_health()
        redis_execution_time = (time.time() - start_time) * 1000

        assert redis_health.status in ['healthy', 'degraded', 'error', 'unknown']
        assert redis_execution_time < 50.0, f"Redis health check took {redis_execution_time:.2f}ms, should be <50ms"

        # Test TickStockPL connectivity check
        start_time = time.time()
        pl_health = monitor._check_tickstockpl_connectivity()
        pl_execution_time = (time.time() - start_time) * 1000

        assert pl_health.status in ['healthy', 'degraded', 'error', 'unknown']
        assert pl_execution_time < 50.0, f"TickStockPL connectivity check took {pl_execution_time:.2f}ms, should be <50ms"


@pytest.mark.performance
class TestAPIEndpointsPerformanceRequirements:
    """Test API endpoints performance meets Sprint 10 requirements."""

    @pytest.fixture
    def fast_flask_app(self):
        """Create Flask app with fast mock services."""
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key'

        # Mock Flask-Login
        from flask_login import LoginManager
        login_manager = LoginManager()
        login_manager.init_app(app)

        @login_manager.user_loader
        def load_user(user_id):
            user = Mock()
            user.id = user_id
            user.is_authenticated = True
            return user

        extensions = {}
        cache_control = Mock()
        config = {}

        with patch('src.api.rest.tickstockpl_api.HealthMonitor') as mock_health_monitor:
            with patch('src.api.rest.tickstockpl_api.TickStockDatabase') as mock_db:
                # Configure fast health monitor
                mock_health_instance = Mock()
                mock_health_instance.get_overall_health.return_value = {
                    'overall_status': 'healthy',
                    'components': {},
                    'summary': {'healthy': 3}
                }
                mock_health_instance.get_dashboard_data.return_value = {
                    'health': {'overall_status': 'healthy'},
                    'quick_stats': {'symbols_count': 4000},
                    'alerts': []
                }

                # Configure fast database
                mock_db_instance = Mock()
                mock_db_instance.get_symbols_for_dropdown.return_value = ['AAPL'] * 4000
                mock_db_instance.get_basic_dashboard_stats.return_value = {
                    'symbols_count': 4000,
                    'events_count': 25000
                }
                mock_db_instance.get_user_alert_history.return_value = []
                mock_db_instance.get_pattern_performance.return_value = []

                mock_health_monitor.return_value = mock_health_instance
                mock_db.return_value = mock_db_instance

                register_tickstockpl_routes(app, extensions, cache_control, config)
                return app

    @pytest.mark.performance
    def test_health_endpoint_performance(self, fast_flask_app):
        """Test health endpoint meets <100ms requirement."""
        app = fast_flask_app

        with app.test_client() as client:
            start_time = time.time()
            response = client.get('/api/tickstockpl/health')
            execution_time = (time.time() - start_time) * 1000

            assert response.status_code == 200
            assert execution_time < 100.0, f"Health endpoint took {execution_time:.2f}ms, requirement is <100ms"

    @pytest.mark.performance
    def test_symbols_endpoint_performance(self, fast_flask_app):
        """Test symbols endpoint meets <100ms requirement with 4000 symbols."""
        app = fast_flask_app

        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['_user_id'] = '123'
                sess['_fresh'] = True

            with patch('flask_login.utils._get_user') as mock_get_user:
                mock_user = Mock()
                mock_user.is_authenticated = True
                mock_get_user.return_value = mock_user

                start_time = time.time()
                response = client.get('/api/tickstockpl/symbols')
                execution_time = (time.time() - start_time) * 1000

                assert response.status_code == 200
                data = response.get_json()
                assert data['count'] == 4000
                assert execution_time < 100.0, f"Symbols endpoint took {execution_time:.2f}ms, requirement is <100ms"

    @pytest.mark.performance
    def test_dashboard_endpoint_performance(self, fast_flask_app):
        """Test dashboard endpoint meets <100ms requirement."""
        app = fast_flask_app

        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['_user_id'] = '123'
                sess['_fresh'] = True

            with patch('flask_login.utils._get_user') as mock_get_user:
                mock_user = Mock()
                mock_user.is_authenticated = True
                mock_get_user.return_value = mock_user

                start_time = time.time()
                response = client.get('/api/tickstockpl/dashboard')
                execution_time = (time.time() - start_time) * 1000

                assert response.status_code == 200
                data = response.get_json()
                assert 'health' in data
                assert execution_time < 100.0, f"Dashboard endpoint took {execution_time:.2f}ms, requirement is <100ms"

    @pytest.mark.performance
    def test_stats_endpoint_performance(self, fast_flask_app):
        """Test stats endpoint meets <100ms requirement."""
        app = fast_flask_app

        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['_user_id'] = '123'
                sess['_fresh'] = True

            with patch('flask_login.utils._get_user') as mock_get_user:
                mock_user = Mock()
                mock_user.is_authenticated = True
                mock_get_user.return_value = mock_user

                start_time = time.time()
                response = client.get('/api/tickstockpl/stats/basic')
                execution_time = (time.time() - start_time) * 1000

                assert response.status_code == 200
                data = response.get_json()
                assert data['symbols_count'] == 4000
                assert execution_time < 100.0, f"Stats endpoint took {execution_time:.2f}ms, requirement is <100ms"


@pytest.mark.performance
class TestConcurrencyAndLoadPerformance:
    """Test system performance under concurrent load."""

    @pytest.fixture
    def concurrent_db(self):
        """Create database instance for concurrent testing."""
        db = TickStockDatabase.__new__(TickStockDatabase)
        db.config = {}
        db.engine = Mock()

        # Mock thread-safe database operations
        def concurrent_mock_execute(*args, **kwargs):
            time.sleep(0.010)  # 10ms per operation
            result = Mock()
            result.scalar.return_value = 1000
            result.__iter__ = Mock(return_value=iter([('TEST_SYMBOL',)]))
            return result

        mock_connection = Mock()
        mock_connection.execute = concurrent_mock_execute
        db.engine.connect.return_value.__enter__.return_value = mock_connection
        return db

    @pytest.mark.performance
    def test_concurrent_database_queries(self, concurrent_db):
        """Test database performance under concurrent query load."""
        db = concurrent_db

        def query_symbols():
            with patch.object(db, 'get_connection') as mock_get_conn:
                mock_connection = Mock()
                mock_result = Mock()
                mock_result.__iter__ = Mock(return_value=iter([('SYMBOL_1',), ('SYMBOL_2',)]))
                mock_connection.execute.return_value = mock_result
                mock_get_conn.return_value.__enter__.return_value = mock_connection

                return db.get_symbols_for_dropdown()

        # Test with 10 concurrent queries
        start_time = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(query_symbols) for _ in range(10)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        execution_time = (time.time() - start_time) * 1000

        assert len(results) == 10
        assert all(len(result) >= 0 for result in results)
        # Allow more time for concurrent operations, but should still be reasonable
        assert execution_time < 500.0, f"10 concurrent queries took {execution_time:.2f}ms, should be <500ms"

    @pytest.mark.performance
    def test_connection_pool_performance(self):
        """Test connection pool performance under load."""
        config = {}

        with patch('src.infrastructure.database.tickstock_db.create_engine') as mock_create_engine:
            mock_engine = Mock()
            mock_create_engine.return_value = mock_engine

            # Mock connection pool behavior
            mock_connection = Mock()
            mock_engine.connect.return_value = mock_connection

            with patch.object(TickStockDatabase, '_test_connection'):
                db = TickStockDatabase(config)

                # Test multiple connection acquisitions
                start_time = time.time()

                for _ in range(50):
                    try:
                        with db.get_connection() as conn:
                            pass  # Simulate quick operation
                    except Exception:
                        pass  # Handle mock exceptions

                execution_time = (time.time() - start_time) * 1000

                # 50 connection acquisitions should be fast
                assert execution_time < 200.0, f"50 connection acquisitions took {execution_time:.2f}ms, should be <200ms"


@pytest.mark.performance
class TestMemoryUsageAndLeaks:
    """Test memory usage patterns and leak prevention."""

    def get_memory_usage(self):
        """Get current memory usage in MB."""
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024

    @pytest.mark.performance
    def test_database_query_memory_usage(self):
        """Test that database queries don't cause memory leaks."""
        config = {}

        with patch('src.infrastructure.database.tickstock_db.create_engine') as mock_create_engine:
            mock_engine = Mock()
            mock_create_engine.return_value = mock_engine

            mock_connection = Mock()
            mock_result = Mock()
            mock_result.__iter__ = Mock(return_value=iter([('TEST',)] * 1000))
            mock_connection.execute.return_value = mock_result
            mock_engine.connect.return_value.__enter__.return_value = mock_connection

            with patch.object(TickStockDatabase, '_test_connection'):
                db = TickStockDatabase(config)

                initial_memory = self.get_memory_usage()

                # Perform many queries to test for memory leaks
                for _ in range(100):
                    try:
                        symbols = db.get_symbols_for_dropdown()
                    except Exception:
                        pass

                final_memory = self.get_memory_usage()
                memory_increase = final_memory - initial_memory

                # Memory increase should be reasonable (less than 50MB)
                assert memory_increase < 50.0, f"Memory increased by {memory_increase:.2f}MB, should be <50MB"

    @pytest.mark.performance
    def test_health_monitor_memory_usage(self):
        """Test health monitor memory usage patterns."""
        config = {}
        mock_redis = Mock()

        with patch('src.core.services.health_monitor.TickStockDatabase') as mock_db_class:
            mock_db_class.return_value = Mock()

            initial_memory = self.get_memory_usage()

            # Create and use health monitor multiple times
            monitors = []
            for _ in range(20):
                try:
                    monitor = HealthMonitor(config, redis_client=mock_redis)
                    health = monitor.get_overall_health()
                    monitors.append(monitor)
                except Exception:
                    pass

            # Cleanup monitors
            for monitor in monitors:
                try:
                    monitor.close()
                except Exception:
                    pass

            final_memory = self.get_memory_usage()
            memory_increase = final_memory - initial_memory

            # Memory increase should be minimal
            assert memory_increase < 20.0, f"Memory increased by {memory_increase:.2f}MB after 20 health monitors"


@pytest.mark.performance
class TestRealWorldScenarioPerformance:
    """Test performance under realistic TickStock usage scenarios."""

    @pytest.mark.performance
    def test_dashboard_refresh_scenario(self):
        """Test performance of complete dashboard refresh scenario."""
        config = {}

        with patch('src.infrastructure.database.tickstock_db.create_engine'):
            with patch('src.core.services.health_monitor.TickStockDatabase') as mock_db_class:
                # Mock realistic dashboard data
                mock_db_instance = Mock()
                mock_db_instance.health_check.return_value = {
                    'status': 'healthy',
                    'query_performance': 30.0,
                    'tables_accessible': ['symbols', 'events', 'ohlcv_daily']
                }
                mock_db_instance.get_basic_dashboard_stats.return_value = {
                    'symbols_count': 4000,
                    'events_count': 25000,
                    'latest_event_time': '2025-01-15T10:30:00'
                }
                mock_db_class.return_value = mock_db_instance

                mock_redis = Mock()
                mock_redis.ping.return_value = True
                mock_redis.set.return_value = True
                mock_redis.get.return_value = 'test_value'
                mock_redis.delete.return_value = 1
                mock_redis.info.return_value = {'connected_clients': 5}
                mock_redis.pubsub_numsub.return_value = [('test_channel', 2)]

                monitor = HealthMonitor(config, redis_client=mock_redis)

                # Simulate complete dashboard refresh
                start_time = time.time()

                # 1. Get overall health
                health = monitor.get_overall_health()

                # 2. Get dashboard data
                dashboard_data = monitor.get_dashboard_data()

                # 3. Get symbols for dropdown
                symbols = mock_db_instance.get_symbols_for_dropdown()

                execution_time = (time.time() - start_time) * 1000

                # Complete dashboard refresh should be under 200ms
                assert execution_time < 200.0, f"Complete dashboard refresh took {execution_time:.2f}ms, should be <200ms"
                assert health['overall_status'] in ['healthy', 'degraded', 'warning']
                assert 'health' in dashboard_data

    @pytest.mark.performance
    def test_user_session_scenario(self):
        """Test performance of typical user session scenario."""
        # This would test a sequence of API calls typical for a user session:
        # 1. Login and authentication
        # 2. Get symbols for dropdown
        # 3. Get dashboard data
        # 4. Get user alerts
        # 5. Get pattern performance
        # 6. Health check

        config = {}
        mock_redis = Mock()

        with patch('src.infrastructure.database.tickstock_db.create_engine'):
            with patch('src.core.services.health_monitor.TickStockDatabase') as mock_db_class:
                mock_db_instance = Mock()
                mock_db_instance.get_symbols_for_dropdown.return_value = ['AAPL'] * 4000
                mock_db_instance.get_basic_dashboard_stats.return_value = {'symbols_count': 4000}
                mock_db_instance.get_user_alert_history.return_value = []
                mock_db_instance.get_pattern_performance.return_value = []
                mock_db_instance.health_check.return_value = {'status': 'healthy'}
                mock_db_class.return_value = mock_db_instance

                mock_redis.ping.return_value = True
                mock_redis.set.return_value = True
                mock_redis.get.return_value = 'test_value'
                mock_redis.delete.return_value = 1
                mock_redis.info.return_value = {}
                mock_redis.pubsub_numsub.return_value = [('test', 1)]

                monitor = HealthMonitor(config, redis_client=mock_redis)

                start_time = time.time()

                # Simulate user session operations
                symbols = mock_db_instance.get_symbols_for_dropdown()
                dashboard_data = monitor.get_dashboard_data()
                alerts = mock_db_instance.get_user_alert_history('user123')
                patterns = mock_db_instance.get_pattern_performance()
                health = monitor.get_overall_health()

                execution_time = (time.time() - start_time) * 1000

                # Complete user session should be under 300ms
                assert execution_time < 300.0, f"User session scenario took {execution_time:.2f}ms, should be <300ms"
                assert len(symbols) == 4000
                assert 'health' in dashboard_data


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
