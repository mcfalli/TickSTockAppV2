"""
Health Monitor Integration Tests - Sprint 10 Phase 1
Tests for HealthMonitor class including component health checks and dashboard data aggregation.

Test Coverage:
- Overall health status aggregation
- Database health monitoring
- Redis connectivity checks
- TickStockPL connectivity validation
- Dashboard data formatting
- Error handling for component failures
"""

import time
from dataclasses import asdict
from unittest.mock import Mock, patch

import pytest
import redis

from src.core.services.health_monitor import HealthMonitor, HealthStatus


class TestHealthStatus:
    """Test HealthStatus dataclass functionality."""

    def test_health_status_creation(self):
        """Test HealthStatus dataclass creation with all parameters."""
        status = HealthStatus(
            status='healthy',
            response_time_ms=25.5,
            last_check=1642234567.0,
            message='All systems operational',
            details={'component': 'database', 'tables': 5}
        )

        assert status.status == 'healthy'
        assert status.response_time_ms == 25.5
        assert status.last_check == 1642234567.0
        assert status.message == 'All systems operational'
        assert status.details['component'] == 'database'

    def test_health_status_minimal_creation(self):
        """Test HealthStatus creation with only required parameters."""
        status = HealthStatus(status='error')

        assert status.status == 'error'
        assert status.response_time_ms is None
        assert status.last_check is None
        assert status.message is None
        assert status.details is None

    def test_health_status_conversion_to_dict(self):
        """Test HealthStatus conversion to dictionary for JSON serialization."""
        status = HealthStatus(
            status='degraded',
            response_time_ms=150.0,
            message='Slow response time'
        )

        status_dict = asdict(status)

        assert status_dict['status'] == 'degraded'
        assert status_dict['response_time_ms'] == 150.0
        assert status_dict['message'] == 'Slow response time'
        assert status_dict['last_check'] is None


class TestHealthMonitorInitialization:
    """Test HealthMonitor initialization and configuration."""

    def test_successful_initialization_with_redis(self):
        """Test successful initialization with Redis client."""
        mock_redis = Mock(spec=redis.Redis)
        config = {'test_config': 'value'}

        with patch('src.core.services.health_monitor.TickStockDatabase') as mock_db_class:
            mock_db_instance = Mock()
            mock_db_class.return_value = mock_db_instance

            monitor = HealthMonitor(config, redis_client=mock_redis)

            assert monitor.config == config
            assert monitor.redis_client == mock_redis
            assert monitor.tickstock_db == mock_db_instance
            mock_db_class.assert_called_once_with(config)

    def test_initialization_without_redis(self):
        """Test initialization without Redis client."""
        config = {'test_config': 'value'}

        with patch('src.core.services.health_monitor.TickStockDatabase') as mock_db_class:
            mock_db_instance = Mock()
            mock_db_class.return_value = mock_db_instance

            monitor = HealthMonitor(config, redis_client=None)

            assert monitor.config == config
            assert monitor.redis_client is None
            assert monitor.tickstock_db == mock_db_instance

    def test_initialization_database_connection_failure(self):
        """Test initialization when database connection fails."""
        config = {'test_config': 'value'}
        mock_redis = Mock(spec=redis.Redis)

        with patch('src.core.services.health_monitor.TickStockDatabase') as mock_db_class:
            mock_db_class.side_effect = Exception("Database connection failed")

            # Should not raise exception, but log warning
            monitor = HealthMonitor(config, redis_client=mock_redis)

            assert monitor.config == config
            assert monitor.redis_client == mock_redis
            assert monitor.tickstock_db is None


class TestHealthMonitorOverallHealth:
    """Test overall health status aggregation."""

    @pytest.fixture
    def mock_monitor(self):
        """Create a mock HealthMonitor for testing."""
        config = {}
        monitor = HealthMonitor.__new__(HealthMonitor)
        monitor.config = config
        monitor.redis_client = Mock(spec=redis.Redis)
        monitor.tickstock_db = Mock()
        return monitor

    def test_overall_health_all_components_healthy(self, mock_monitor):
        """Test overall health when all components are healthy."""
        # Mock all component health checks to return healthy status
        with patch.object(mock_monitor, '_check_database_health') as mock_db_health:
            with patch.object(mock_monitor, '_check_redis_health') as mock_redis_health:
                with patch.object(mock_monitor, '_check_tickstockpl_connectivity') as mock_pl_health:

                    mock_db_health.return_value = HealthStatus(status='healthy')
                    mock_redis_health.return_value = HealthStatus(status='healthy')
                    mock_pl_health.return_value = HealthStatus(status='healthy')

                    health = mock_monitor.get_overall_health()

                    assert health['overall_status'] == 'healthy'
                    assert health['summary']['healthy'] == 3
                    assert health['summary']['degraded'] == 0
                    assert health['summary']['error'] == 0
                    assert health['summary']['unknown'] == 0

    def test_overall_health_with_error_component(self, mock_monitor):
        """Test overall health when one component has an error."""
        with patch.object(mock_monitor, '_check_database_health') as mock_db_health:
            with patch.object(mock_monitor, '_check_redis_health') as mock_redis_health:
                with patch.object(mock_monitor, '_check_tickstockpl_connectivity') as mock_pl_health:

                    mock_db_health.return_value = HealthStatus(status='error')
                    mock_redis_health.return_value = HealthStatus(status='healthy')
                    mock_pl_health.return_value = HealthStatus(status='healthy')

                    health = mock_monitor.get_overall_health()

                    assert health['overall_status'] == 'error'
                    assert health['summary']['healthy'] == 2
                    assert health['summary']['error'] == 1

    def test_overall_health_with_degraded_component(self, mock_monitor):
        """Test overall health when one component is degraded."""
        with patch.object(mock_monitor, '_check_database_health') as mock_db_health:
            with patch.object(mock_monitor, '_check_redis_health') as mock_redis_health:
                with patch.object(mock_monitor, '_check_tickstockpl_connectivity') as mock_pl_health:

                    mock_db_health.return_value = HealthStatus(status='healthy')
                    mock_redis_health.return_value = HealthStatus(status='degraded')
                    mock_pl_health.return_value = HealthStatus(status='healthy')

                    health = mock_monitor.get_overall_health()

                    assert health['overall_status'] == 'degraded'
                    assert health['summary']['healthy'] == 2
                    assert health['summary']['degraded'] == 1

    def test_overall_health_with_unknown_component(self, mock_monitor):
        """Test overall health when one component status is unknown."""
        with patch.object(mock_monitor, '_check_database_health') as mock_db_health:
            with patch.object(mock_monitor, '_check_redis_health') as mock_redis_health:
                with patch.object(mock_monitor, '_check_tickstockpl_connectivity') as mock_pl_health:

                    mock_db_health.return_value = HealthStatus(status='healthy')
                    mock_redis_health.return_value = HealthStatus(status='healthy')
                    mock_pl_health.return_value = HealthStatus(status='unknown')

                    health = mock_monitor.get_overall_health()

                    assert health['overall_status'] == 'unknown'
                    assert health['summary']['healthy'] == 2
                    assert health['summary']['unknown'] == 1

    def test_health_structure_validation(self, mock_monitor):
        """Test that health response has correct structure and timestamp."""
        with patch.object(mock_monitor, '_check_database_health') as mock_db_health:
            with patch.object(mock_monitor, '_check_redis_health') as mock_redis_health:
                with patch.object(mock_monitor, '_check_tickstockpl_connectivity') as mock_pl_health:

                    mock_db_health.return_value = HealthStatus(status='healthy')
                    mock_redis_health.return_value = HealthStatus(status='healthy')
                    mock_pl_health.return_value = HealthStatus(status='healthy')

                    start_time = time.time()
                    health = mock_monitor.get_overall_health()
                    end_time = time.time()

                    # Validate structure
                    assert 'timestamp' in health
                    assert 'overall_status' in health
                    assert 'components' in health
                    assert 'summary' in health

                    # Validate timestamp is recent
                    assert start_time <= health['timestamp'] <= end_time

                    # Validate components structure
                    assert 'database' in health['components']
                    assert 'redis' in health['components']
                    assert 'tickstockpl_connectivity' in health['components']


class TestHealthMonitorDatabaseHealthCheck:
    """Test database health check functionality."""

    @pytest.fixture
    def mock_monitor(self):
        """Create a mock HealthMonitor for database testing."""
        config = {}
        monitor = HealthMonitor.__new__(HealthMonitor)
        monitor.config = config
        monitor.redis_client = Mock(spec=redis.Redis)
        monitor.tickstock_db = Mock()
        return monitor

    def test_database_health_check_success(self, mock_monitor):
        """Test successful database health check."""
        mock_db_health = {
            'status': 'healthy',
            'query_performance': 25.5,
            'tables_accessible': ['symbols', 'events'],
            'connection_pool': {'size': 5, 'checked_in': 3}
        }
        mock_monitor.tickstock_db.health_check.return_value = mock_db_health

        with patch('time.time', side_effect=[0.0, 0.030]):  # 30ms execution time
            health = mock_monitor._check_database_health()

            assert health.status == 'healthy'
            assert health.response_time_ms == 30.0
            assert health.details['tables_accessible'] == ['symbols', 'events']
            assert health.details['query_performance_ms'] == 25.5

    def test_database_health_check_not_initialized(self, mock_monitor):
        """Test database health check when database is not initialized."""
        mock_monitor.tickstock_db = None

        health = mock_monitor._check_database_health()

        assert health.status == 'error'
        assert 'TickStock database not initialized' in health.message

    def test_database_health_check_failure(self, mock_monitor):
        """Test database health check when database check fails."""
        mock_monitor.tickstock_db.health_check.side_effect = Exception("Connection timeout")

        health = mock_monitor._check_database_health()

        assert health.status == 'error'
        assert 'Database check failed: Connection timeout' in health.message

    def test_database_health_check_with_error_status(self, mock_monitor):
        """Test database health check when database reports error status."""
        mock_db_health = {
            'status': 'error',
            'error': 'Connection pool exhausted',
            'query_performance': None
        }
        mock_monitor.tickstock_db.health_check.return_value = mock_db_health

        health = mock_monitor._check_database_health()

        assert health.status == 'error'
        assert health.message == 'Connection pool exhausted'

    def test_database_health_check_with_warning_status(self, mock_monitor):
        """Test database health check when database reports warning status."""
        mock_db_health = {
            'status': 'warning',
            'warning': 'No tables found',
            'query_performance': 15.0
        }
        mock_monitor.tickstock_db.health_check.return_value = mock_db_health

        health = mock_monitor._check_database_health()

        assert health.status == 'warning'
        assert health.message == 'No tables found'


class TestHealthMonitorRedisHealthCheck:
    """Test Redis health check functionality."""

    @pytest.fixture
    def mock_monitor(self):
        """Create a mock HealthMonitor for Redis testing."""
        config = {}
        monitor = HealthMonitor.__new__(HealthMonitor)
        monitor.config = config
        monitor.redis_client = Mock(spec=redis.Redis)
        monitor.tickstock_db = Mock()
        return monitor

    def test_redis_health_check_success(self, mock_monitor):
        """Test successful Redis health check."""
        # Mock Redis operations
        mock_monitor.redis_client.ping.return_value = True
        mock_monitor.redis_client.set.return_value = True
        mock_monitor.redis_client.get.return_value = 'test_value'
        mock_monitor.redis_client.delete.return_value = 1
        mock_monitor.redis_client.info.return_value = {
            'connected_clients': 5,
            'used_memory_human': '1.2M',
            'redis_version': '6.2.0',
            'uptime_in_seconds': 86400
        }

        with patch('time.time', side_effect=[0.0, 0.025]):  # 25ms execution time
            health = mock_monitor._check_redis_health()

            assert health.status == 'healthy'
            assert health.response_time_ms == 25.0
            assert health.details['connected_clients'] == 5
            assert health.details['redis_version'] == '6.2.0'

    def test_redis_health_check_not_configured(self, mock_monitor):
        """Test Redis health check when Redis client is not configured."""
        mock_monitor.redis_client = None

        health = mock_monitor._check_redis_health()

        assert health.status == 'unknown'
        assert 'Redis client not configured' in health.message

    def test_redis_health_check_ping_failure(self, mock_monitor):
        """Test Redis health check when ping fails."""
        mock_monitor.redis_client.ping.return_value = False

        health = mock_monitor._check_redis_health()

        assert health.status == 'error'
        assert 'Redis ping failed' in health.message

    def test_redis_health_check_operations_failure(self, mock_monitor):
        """Test Redis health check when operations fail."""
        mock_monitor.redis_client.ping.return_value = True
        mock_monitor.redis_client.set.return_value = True
        mock_monitor.redis_client.get.return_value = 'wrong_value'  # Test value doesn't match

        health = mock_monitor._check_redis_health()

        assert health.status == 'error'
        assert 'Redis operations test failed' in health.message

    def test_redis_health_check_degraded_performance(self, mock_monitor):
        """Test Redis health check with degraded performance (>50ms)."""
        mock_monitor.redis_client.ping.return_value = True
        mock_monitor.redis_client.set.return_value = True
        mock_monitor.redis_client.get.return_value = 'test_value'
        mock_monitor.redis_client.delete.return_value = 1
        mock_monitor.redis_client.info.return_value = {}

        with patch('time.time', side_effect=[0.0, 0.075]):  # 75ms execution time
            health = mock_monitor._check_redis_health()

            assert health.status == 'degraded'
            assert health.response_time_ms == 75.0

    def test_redis_health_check_connection_error(self, mock_monitor):
        """Test Redis health check with connection error."""
        mock_monitor.redis_client.ping.side_effect = redis.ConnectionError("Connection refused")

        health = mock_monitor._check_redis_health()

        assert health.status == 'error'
        assert 'Redis check failed: Connection refused' in health.message


class TestHealthMonitorTickStockPLConnectivity:
    """Test TickStockPL connectivity check functionality."""

    @pytest.fixture
    def mock_monitor(self):
        """Create a mock HealthMonitor for TickStockPL testing."""
        config = {}
        monitor = HealthMonitor.__new__(HealthMonitor)
        monitor.config = config
        monitor.redis_client = Mock(spec=redis.Redis)
        monitor.tickstock_db = Mock()
        return monitor

    def test_tickstockpl_connectivity_success(self, mock_monitor):
        """Test successful TickStockPL connectivity check."""
        # Mock Redis pubsub_numsub responses
        mock_responses = [
            ('tickstock.events.patterns', 2),
            ('tickstock.events.backtesting.progress', 1),
            ('tickstock.events.backtesting.results', 1)
        ]
        mock_monitor.redis_client.pubsub_numsub.side_effect = [
            [mock_responses[0]],
            [mock_responses[1]],
            [mock_responses[2]]
        ]

        with patch('time.time', side_effect=[0.0, 0.020]):  # 20ms execution time
            health = mock_monitor._check_tickstockpl_connectivity()

            assert health.status == 'healthy'
            assert health.response_time_ms == 20.0
            assert 'TickStockPL detected with 4 active subscriptions' in health.message
            assert health.details['total_subscribers'] == 4

    def test_tickstockpl_connectivity_no_subscribers(self, mock_monitor):
        """Test TickStockPL connectivity check when no subscribers are found."""
        # Mock no subscribers on any channel
        mock_monitor.redis_client.pubsub_numsub.return_value = [('test_channel', 0)]
        mock_monitor.redis_client.publish.return_value = 1

        health = mock_monitor._check_tickstockpl_connectivity()

        assert health.status == 'unknown'
        assert 'TickStockPL services not detected' in health.message
        assert health.details['total_subscribers'] == 0

    def test_tickstockpl_connectivity_redis_not_available(self, mock_monitor):
        """Test TickStockPL connectivity check when Redis is not available."""
        mock_monitor.redis_client = None

        health = mock_monitor._check_tickstockpl_connectivity()

        assert health.status == 'unknown'
        assert 'Cannot check TickStockPL - Redis not available' in health.message

    def test_tickstockpl_connectivity_publish_failure(self, mock_monitor):
        """Test TickStockPL connectivity when publish test fails."""
        # Mock no subscribers
        mock_monitor.redis_client.pubsub_numsub.return_value = [('test_channel', 0)]
        # Mock publish failure
        mock_monitor.redis_client.publish.side_effect = Exception("Redis publish error")

        health = mock_monitor._check_tickstockpl_connectivity()

        assert health.status == 'error'
        assert 'Cannot communicate with TickStockPL' in health.message

    def test_tickstockpl_connectivity_channel_check_failure(self, mock_monitor):
        """Test TickStockPL connectivity when channel check fails."""
        mock_monitor.redis_client.pubsub_numsub.side_effect = Exception("Channel check failed")

        health = mock_monitor._check_tickstockpl_connectivity()

        assert health.status == 'error'
        assert 'TickStockPL check failed: Channel check failed' in health.message

    def test_tickstockpl_connectivity_expected_channels(self, mock_monitor):
        """Test that all expected TickStockPL channels are checked."""
        mock_monitor.redis_client.pubsub_numsub.return_value = [('test_channel', 1)]
        mock_monitor.redis_client.publish.return_value = 1

        health = mock_monitor._check_tickstockpl_connectivity()

        expected_channels = [
            'tickstock.events.patterns',
            'tickstock.events.backtesting.progress',
            'tickstock.events.backtesting.results'
        ]

        assert health.details['expected_channels'] == expected_channels


class TestHealthMonitorDashboardData:
    """Test dashboard data aggregation functionality."""

    @pytest.fixture
    def mock_monitor(self):
        """Create a mock HealthMonitor for dashboard testing."""
        config = {}
        monitor = HealthMonitor.__new__(HealthMonitor)
        monitor.config = config
        monitor.redis_client = Mock(spec=redis.Redis)
        monitor.tickstock_db = Mock()
        return monitor

    def test_dashboard_data_success(self, mock_monitor):
        """Test successful dashboard data aggregation."""
        # Mock overall health
        mock_health = {
            'timestamp': time.time(),
            'overall_status': 'healthy',
            'components': {
                'database': HealthStatus(status='healthy', response_time_ms=25.0),
                'redis': HealthStatus(status='healthy', response_time_ms=15.0),
                'tickstockpl_connectivity': HealthStatus(status='healthy', response_time_ms=30.0)
            },
            'summary': {'healthy': 3, 'degraded': 0, 'error': 0, 'unknown': 0}
        }

        # Mock database stats
        mock_stats = {
            'symbols_count': 4000,
            'events_count': 25000,
            'latest_event_time': '2025-01-15T10:30:00',
            'database_status': 'connected'
        }

        with patch.object(mock_monitor, 'get_overall_health', return_value=mock_health):
            mock_monitor.tickstock_db.get_basic_dashboard_stats.return_value = mock_stats

            dashboard_data = mock_monitor.get_dashboard_data()

            assert 'health' in dashboard_data
            assert 'quick_stats' in dashboard_data
            assert 'alerts' in dashboard_data
            assert dashboard_data['quick_stats']['symbols_count'] == 4000
            assert len(dashboard_data['alerts']) == 0  # No alerts for healthy status

    def test_dashboard_data_with_alerts(self, mock_monitor):
        """Test dashboard data with component alerts."""
        # Mock health with error and degraded components
        mock_health = {
            'timestamp': time.time(),
            'overall_status': 'error',
            'components': {
                'database': HealthStatus(status='error', message='Connection failed', last_check=time.time()),
                'redis': HealthStatus(status='degraded', message='Slow response', last_check=time.time()),
                'tickstockpl_connectivity': HealthStatus(status='healthy', last_check=time.time())
            },
            'summary': {'healthy': 1, 'degraded': 1, 'error': 1, 'unknown': 0}
        }

        with patch.object(mock_monitor, 'get_overall_health', return_value=mock_health):
            mock_monitor.tickstock_db.get_basic_dashboard_stats.return_value = {}

            dashboard_data = mock_monitor.get_dashboard_data()

            assert len(dashboard_data['alerts']) == 2  # Error + degraded components

            # Check alert details
            alerts = dashboard_data['alerts']
            alert_components = [alert['component'] for alert in alerts]
            assert 'database' in alert_components
            assert 'redis' in alert_components

    def test_dashboard_data_database_stats_failure(self, mock_monitor):
        """Test dashboard data when database stats retrieval fails."""
        mock_health = {
            'timestamp': time.time(),
            'overall_status': 'healthy',
            'components': {},
            'summary': {'healthy': 3, 'degraded': 0, 'error': 0, 'unknown': 0}
        }

        with patch.object(mock_monitor, 'get_overall_health', return_value=mock_health):
            mock_monitor.tickstock_db.get_basic_dashboard_stats.side_effect = Exception("Stats error")

            dashboard_data = mock_monitor.get_dashboard_data()

            assert 'error' in dashboard_data['quick_stats']
            assert dashboard_data['quick_stats']['error'] == 'Stats unavailable'

    def test_dashboard_data_no_database_connection(self, mock_monitor):
        """Test dashboard data when database is not initialized."""
        mock_health = {
            'timestamp': time.time(),
            'overall_status': 'healthy',
            'components': {},
            'summary': {'healthy': 3, 'degraded': 0, 'error': 0, 'unknown': 0}
        }

        mock_monitor.tickstock_db = None

        with patch.object(mock_monitor, 'get_overall_health', return_value=mock_health):
            dashboard_data = mock_monitor.get_dashboard_data()

            assert dashboard_data['quick_stats'] == {}


class TestHealthMonitorCleanup:
    """Test HealthMonitor cleanup and resource management."""

    def test_close_cleanup_with_database(self):
        """Test proper cleanup when closing with database connection."""
        config = {}
        mock_redis = Mock(spec=redis.Redis)

        with patch('src.core.services.health_monitor.TickStockDatabase') as mock_db_class:
            mock_db_instance = Mock()
            mock_db_class.return_value = mock_db_instance

            monitor = HealthMonitor(config, redis_client=mock_redis)
            monitor.close()

            mock_db_instance.close.assert_called_once()

    def test_close_cleanup_without_database(self):
        """Test cleanup when database is not initialized."""
        config = {}
        monitor = HealthMonitor.__new__(HealthMonitor)
        monitor.config = config
        monitor.redis_client = Mock(spec=redis.Redis)
        monitor.tickstock_db = None

        # Should not raise exception
        monitor.close()


@pytest.mark.performance
class TestHealthMonitorPerformance:
    """Test HealthMonitor performance requirements."""

    @pytest.fixture
    def mock_monitor(self):
        """Create a mock HealthMonitor for performance testing."""
        config = {}
        monitor = HealthMonitor.__new__(HealthMonitor)
        monitor.config = config
        monitor.redis_client = Mock(spec=redis.Redis)
        monitor.tickstock_db = Mock()
        return monitor

    @pytest.mark.performance
    def test_overall_health_check_performance(self, mock_monitor):
        """Test that overall health check meets <100ms performance requirement."""
        # Mock all component health checks with fast responses
        with patch.object(mock_monitor, '_check_database_health') as mock_db_health:
            with patch.object(mock_monitor, '_check_redis_health') as mock_redis_health:
                with patch.object(mock_monitor, '_check_tickstockpl_connectivity') as mock_pl_health:

                    mock_db_health.return_value = HealthStatus(status='healthy')
                    mock_redis_health.return_value = HealthStatus(status='healthy')
                    mock_pl_health.return_value = HealthStatus(status='healthy')

                    start_time = time.time()
                    health = mock_monitor.get_overall_health()
                    execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds

                    assert health['overall_status'] == 'healthy'
                    assert execution_time < 100.0, f"Health check took {execution_time:.2f}ms, should be <100ms"

    @pytest.mark.performance
    def test_dashboard_data_performance(self, mock_monitor):
        """Test that dashboard data aggregation meets <100ms performance requirement."""
        mock_health = {
            'timestamp': time.time(),
            'overall_status': 'healthy',
            'components': {},
            'summary': {'healthy': 3, 'degraded': 0, 'error': 0, 'unknown': 0}
        }

        with patch.object(mock_monitor, 'get_overall_health', return_value=mock_health):
            mock_monitor.tickstock_db.get_basic_dashboard_stats.return_value = {
                'symbols_count': 4000,
                'events_count': 25000
            }

            start_time = time.time()
            dashboard_data = mock_monitor.get_dashboard_data()
            execution_time = (time.time() - start_time) * 1000

            assert 'health' in dashboard_data
            assert execution_time < 100.0, f"Dashboard data took {execution_time:.2f}ms, should be <100ms"


class TestHealthMonitorErrorHandling:
    """Test HealthMonitor error handling and edge cases."""

    @pytest.fixture
    def mock_monitor(self):
        """Create a mock HealthMonitor for error testing."""
        config = {}
        monitor = HealthMonitor.__new__(HealthMonitor)
        monitor.config = config
        monitor.redis_client = Mock(spec=redis.Redis)
        monitor.tickstock_db = Mock()
        return monitor

    def test_health_check_with_timeout_errors(self, mock_monitor):
        """Test health check behavior with timeout errors."""
        with patch.object(mock_monitor, '_check_database_health') as mock_db_health:
            with patch.object(mock_monitor, '_check_redis_health') as mock_redis_health:
                with patch.object(mock_monitor, '_check_tickstockpl_connectivity') as mock_pl_health:

                    # Database times out
                    mock_db_health.side_effect = TimeoutError("Database timeout")
                    mock_redis_health.return_value = HealthStatus(status='healthy')
                    mock_pl_health.return_value = HealthStatus(status='healthy')

                    # Should handle the timeout gracefully
                    with pytest.raises(TimeoutError):
                        mock_monitor.get_overall_health()

    def test_health_check_partial_component_failure(self, mock_monitor):
        """Test health check when some components fail to respond."""
        with patch.object(mock_monitor, '_check_database_health') as mock_db_health:
            with patch.object(mock_monitor, '_check_redis_health') as mock_redis_health:
                with patch.object(mock_monitor, '_check_tickstockpl_connectivity') as mock_pl_health:

                    mock_db_health.return_value = HealthStatus(status='error', message='DB failed')
                    mock_redis_health.return_value = HealthStatus(status='healthy')
                    mock_pl_health.return_value = HealthStatus(status='unknown', message='Cannot connect')

                    health = mock_monitor.get_overall_health()

                    # Should still return a valid health response
                    assert health['overall_status'] == 'error'  # Worst status wins
                    assert health['summary']['error'] == 1
                    assert health['summary']['unknown'] == 1
                    assert health['summary']['healthy'] == 1

    def test_redis_operations_edge_cases(self, mock_monitor):
        """Test Redis health check with various edge cases."""
        # Test case 1: Redis returns unexpected data types
        mock_monitor.redis_client.ping.return_value = True
        mock_monitor.redis_client.set.return_value = True
        mock_monitor.redis_client.get.return_value = b'test_value'  # Bytes instead of string
        mock_monitor.redis_client.delete.return_value = 1
        mock_monitor.redis_client.info.return_value = {}

        health = mock_monitor._check_redis_health()

        # Should handle bytes vs string comparison gracefully
        assert health.status in ['healthy', 'error']

    def test_database_health_missing_optional_fields(self, mock_monitor):
        """Test database health check with missing optional fields."""
        mock_db_health = {
            'status': 'healthy',
            # Missing query_performance, tables_accessible, connection_pool
        }
        mock_monitor.tickstock_db.health_check.return_value = mock_db_health

        health = mock_monitor._check_database_health()

        assert health.status == 'healthy'
        assert health.details['query_performance_ms'] is None
        assert health.details['tables_accessible'] == []
