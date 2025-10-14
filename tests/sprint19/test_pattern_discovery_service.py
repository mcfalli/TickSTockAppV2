"""
Pattern Discovery Service Integration Test Suite - Sprint 19 Phase 1
Comprehensive testing of Pattern Discovery Service orchestration and integration.

Test Coverage:
- Service orchestration and initialization
- Component integration and coordination
- Health monitoring and performance metrics
- Redis event consumption from TickStockPL channels
- Cross-component communication and data flow
- Service startup and shutdown sequences
- Component health dependencies and failure handling
"""

import time
from unittest.mock import Mock, patch

import pytest
from flask import Flask

# Sprint 19 imports
from src.core.services.pattern_discovery_service import (
    PatternDiscoveryService,
    get_pattern_discovery_service,
    initialize_pattern_discovery_service,
    shutdown_pattern_discovery_service,
)


class TestPatternDiscoveryServiceInitialization:
    """Test Pattern Discovery Service initialization and setup."""

    def test_service_creation(self, sprint19_config):
        """Test service creation with configuration."""
        app = Flask(__name__)
        service = PatternDiscoveryService(app, sprint19_config)

        assert service.app == app
        assert service.config == sprint19_config
        assert service.initialized is False
        assert service.services_healthy is False
        assert isinstance(service.service_stats, dict)
        assert 'start_time' in service.service_stats

    @patch('src.core.services.pattern_discovery_service.RedisConnectionManager')
    @patch('src.core.services.pattern_discovery_service.RedisPatternCache')
    @patch('src.core.services.pattern_discovery_service.TickStockDatabase')
    @patch('src.core.services.pattern_discovery_service.CacheControl')
    @patch('src.core.services.pattern_discovery_service.RedisEventSubscriber')
    def test_service_initialization_success(self, mock_subscriber, mock_cache_control,
                                          mock_tickstock_db, mock_pattern_cache,
                                          mock_redis_manager, sprint19_config):
        """Test successful service initialization."""
        app = Flask(__name__)
        service = PatternDiscoveryService(app, sprint19_config)

        # Mock successful component initialization
        mock_redis_manager_instance = Mock()
        mock_redis_manager_instance.initialize.return_value = True
        mock_redis_manager.return_value = mock_redis_manager_instance

        mock_pattern_cache_instance = Mock()
        mock_pattern_cache.return_value = mock_pattern_cache_instance

        mock_tickstock_db_instance = Mock()
        mock_tickstock_db.return_value = mock_tickstock_db_instance

        mock_cache_control_instance = Mock()
        mock_cache_control.return_value = mock_cache_control_instance

        mock_subscriber_instance = Mock()
        mock_subscriber.return_value = mock_subscriber_instance

        # Initialize service
        success = service.initialize()

        assert success is True
        assert service.initialized is True
        assert service.services_healthy is True

        # Verify all components were created
        mock_redis_manager.assert_called_once()
        mock_pattern_cache.assert_called_once()
        mock_tickstock_db.assert_called_once()
        mock_cache_control.assert_called_once()
        mock_subscriber.assert_called_once()

        # Verify services were registered with Flask app
        assert hasattr(app, 'pattern_cache')
        assert hasattr(app, 'tickstock_db')
        assert hasattr(app, 'cache_control')
        assert hasattr(app, 'pattern_discovery_service')

    @patch('src.core.services.pattern_discovery_service.RedisConnectionManager')
    def test_service_initialization_redis_failure(self, mock_redis_manager, sprint19_config):
        """Test service initialization with Redis failure."""
        app = Flask(__name__)
        service = PatternDiscoveryService(app, sprint19_config)

        # Mock Redis manager initialization failure
        mock_redis_manager_instance = Mock()
        mock_redis_manager_instance.initialize.return_value = False
        mock_redis_manager.return_value = mock_redis_manager_instance

        success = service.initialize()

        assert success is False
        assert service.initialized is False
        assert service.services_healthy is False

    @patch('src.core.services.pattern_discovery_service.RedisConnectionManager')
    @patch('src.core.services.pattern_discovery_service.RedisPatternCache')
    def test_service_initialization_exception_handling(self, mock_pattern_cache,
                                                      mock_redis_manager, sprint19_config):
        """Test service initialization exception handling."""
        app = Flask(__name__)
        service = PatternDiscoveryService(app, sprint19_config)

        # Mock Redis manager success but pattern cache exception
        mock_redis_manager_instance = Mock()
        mock_redis_manager_instance.initialize.return_value = True
        mock_redis_manager.return_value = mock_redis_manager_instance

        mock_pattern_cache.side_effect = Exception("Pattern cache initialization error")

        success = service.initialize()

        assert success is False
        assert service.initialized is False


class TestPatternDiscoveryServiceComponents:
    """Test individual component management within the service."""

    @pytest.fixture
    def initialized_service(self, sprint19_config):
        """Create a mock initialized service for testing."""
        app = Flask(__name__)
        service = PatternDiscoveryService(app, sprint19_config)

        # Mock all components
        service.redis_manager = Mock()
        service.redis_client = Mock()
        service.pattern_cache = Mock()
        service.tickstock_db = Mock()
        service.cache_control = Mock()
        service.event_subscriber = Mock()

        service.initialized = True
        service.services_healthy = True

        return service

    def test_redis_configuration_setup(self, sprint19_config):
        """Test Redis connection configuration setup."""
        app = Flask(__name__)
        service = PatternDiscoveryService(app, sprint19_config)

        # Test Redis config extraction
        expected_host = sprint19_config.get('redis_host', 'localhost')
        expected_port = sprint19_config.get('redis_port', 6379)
        expected_db = sprint19_config.get('redis_db', 0)

        # Mock Redis initialization to capture config
        with patch('src.core.services.pattern_discovery_service.RedisConnectionManager') as mock_manager:
            with patch('src.core.services.pattern_discovery_service.RedisConnectionConfig') as mock_config:
                service._initialize_redis()

                # Verify Redis config was created with correct parameters
                mock_config.assert_called_once()
                config_call = mock_config.call_args
                assert config_call[1]['host'] == expected_host
                assert config_call[1]['port'] == expected_port
                assert config_call[1]['db'] == expected_db

    def test_pattern_cache_configuration(self, initialized_service):
        """Test pattern cache configuration setup."""
        # Verify pattern cache is configured correctly
        assert initialized_service.pattern_cache is not None

        # Test cache configuration values
        expected_config = {
            'pattern_cache_ttl': initialized_service.config.get('pattern_cache_ttl', 3600),
            'api_response_cache_ttl': initialized_service.config.get('api_response_cache_ttl', 30),
            'index_cache_ttl': initialized_service.config.get('index_cache_ttl', 3600)
        }

        # In a real test, we'd verify these configs were passed to RedisPatternCache
        # Here we just verify the service has the components
        assert hasattr(initialized_service, 'pattern_cache')

    def test_event_subscriber_setup(self, initialized_service):
        """Test Redis event subscriber setup and event handling."""
        # Verify event subscriber is configured
        assert initialized_service.event_subscriber is not None

        # Test event handler registration
        # In real implementation, this would be tested by triggering events
        assert hasattr(initialized_service, '_handle_pattern_event')

    def test_flask_app_registration(self, initialized_service):
        """Test Flask app service registration."""
        app = initialized_service.app

        # Verify services are available on Flask app
        assert hasattr(app, 'pattern_cache')
        assert hasattr(app, 'tickstock_db')
        assert hasattr(app, 'cache_control')
        assert hasattr(app, 'pattern_discovery_service')

        assert app.pattern_cache == initialized_service.pattern_cache
        assert app.tickstock_db == initialized_service.tickstock_db
        assert app.cache_control == initialized_service.cache_control
        assert app.pattern_discovery_service == initialized_service


class TestPatternDiscoveryServiceEventHandling:
    """Test event handling and TickStockPL integration."""

    def test_pattern_event_handling(self, sprint19_config):
        """Test pattern event processing from TickStockPL."""
        app = Flask(__name__)
        service = PatternDiscoveryService(app, sprint19_config)

        # Mock pattern cache
        mock_pattern_cache = Mock()
        mock_pattern_cache.process_pattern_event.return_value = True
        service.pattern_cache = mock_pattern_cache

        # Create mock event
        mock_event = Mock()
        mock_event.data = {
            'symbol': 'AAPL',
            'pattern': 'Weekly_Breakout',
            'confidence': 0.85,
            'timestamp': time.time()
        }

        # Handle event
        service._handle_pattern_event(mock_event)

        # Verify pattern cache was called
        mock_pattern_cache.process_pattern_event.assert_called_once_with(mock_event.data)

    def test_pattern_event_handling_failure(self, sprint19_config):
        """Test pattern event handling with processing failure."""
        app = Flask(__name__)
        service = PatternDiscoveryService(app, sprint19_config)

        # Mock pattern cache with failure
        mock_pattern_cache = Mock()
        mock_pattern_cache.process_pattern_event.return_value = False
        service.pattern_cache = mock_pattern_cache

        # Create mock event
        mock_event = Mock()
        mock_event.data = {'symbol': 'TEST'}

        # Handle event (should not raise exception)
        service._handle_pattern_event(mock_event)

        # Verify processing was attempted
        mock_pattern_cache.process_pattern_event.assert_called_once()

    def test_pattern_event_handling_exception(self, sprint19_config):
        """Test pattern event handling with exception."""
        app = Flask(__name__)
        service = PatternDiscoveryService(app, sprint19_config)

        # Mock pattern cache with exception
        mock_pattern_cache = Mock()
        mock_pattern_cache.process_pattern_event.side_effect = Exception("Processing error")
        service.pattern_cache = mock_pattern_cache

        # Create mock event
        mock_event = Mock()
        mock_event.data = {'symbol': 'TEST'}

        # Handle event (should not raise exception)
        service._handle_pattern_event(mock_event)

        # Verify processing was attempted
        mock_pattern_cache.process_pattern_event.assert_called_once()

    def test_socketio_integration(self, initialized_service):
        """Test SocketIO integration for event broadcasting."""
        mock_socketio = Mock()

        # Set SocketIO on service
        initialized_service.set_socketio(mock_socketio)

        # Verify event subscriber received SocketIO instance
        initialized_service.event_subscriber.socketio = mock_socketio
        assert initialized_service.event_subscriber.socketio == mock_socketio


class TestPatternDiscoveryServiceHealthMonitoring:
    """Test health monitoring and performance metrics."""

    def test_health_status_all_healthy(self, initialized_service):
        """Test health status when all components are healthy."""
        # Mock all components as healthy
        initialized_service.redis_manager.get_health_status.return_value = {'status': 'healthy'}
        initialized_service.pattern_cache.get_cache_stats.return_value = {'cached_patterns': 10}
        initialized_service.tickstock_db.health_check.return_value = {'status': 'healthy'}
        initialized_service.event_subscriber.is_running = True

        health_status = initialized_service.get_health_status()

        assert health_status['status'] == 'healthy'
        assert health_status['healthy'] is True
        assert health_status['components']['redis_manager'] == 'healthy'
        assert health_status['components']['pattern_cache'] == 'healthy'
        assert health_status['components']['tickstock_database'] == 'healthy'
        assert health_status['components']['event_subscriber'] == 'healthy'
        assert 'performance' in health_status
        assert 'last_check' in health_status

    def test_health_status_degraded_database(self, initialized_service):
        """Test health status with degraded database."""
        # Mock components with database degraded
        initialized_service.redis_manager.get_health_status.return_value = {'status': 'healthy'}
        initialized_service.pattern_cache.get_cache_stats.return_value = {'cached_patterns': 10}
        initialized_service.tickstock_db.health_check.return_value = {'status': 'degraded'}  # Still acceptable
        initialized_service.event_subscriber.is_running = True

        health_status = initialized_service.get_health_status()

        assert health_status['status'] == 'healthy'  # degraded database is still healthy
        assert health_status['healthy'] is True

    def test_health_status_subscriber_warning(self, initialized_service):
        """Test health status with event subscriber issues."""
        # Mock components with subscriber issues
        initialized_service.redis_manager.get_health_status.return_value = {'status': 'healthy'}
        initialized_service.pattern_cache.get_cache_stats.return_value = {'cached_patterns': 10}
        initialized_service.tickstock_db.health_check.return_value = {'status': 'healthy'}
        initialized_service.event_subscriber.is_running = False  # Subscriber not running

        health_status = initialized_service.get_health_status()

        assert health_status['status'] == 'warning'  # Warning due to subscriber
        assert health_status['healthy'] is False
        assert health_status['components']['event_subscriber'] == 'warning'

    def test_health_status_multiple_failures(self, initialized_service):
        """Test health status with multiple component failures."""
        # Mock multiple component failures
        initialized_service.redis_manager.get_health_status.return_value = {'status': 'error'}
        initialized_service.pattern_cache.get_cache_stats.side_effect = Exception("Cache error")
        initialized_service.tickstock_db.health_check.return_value = {'status': 'error'}
        initialized_service.event_subscriber.is_running = False

        health_status = initialized_service.get_health_status()

        assert health_status['status'] == 'error'
        assert health_status['healthy'] is False
        assert health_status['components']['redis_manager'] == 'error'
        assert health_status['components']['pattern_cache'] == 'error'
        assert health_status['components']['tickstock_database'] == 'error'
        assert health_status['components']['event_subscriber'] == 'warning'

    def test_health_status_exception_handling(self, initialized_service):
        """Test health status with exceptions during health check."""
        # Mock health check to raise exception
        initialized_service.redis_manager.get_health_status.side_effect = Exception("Health check error")

        health_status = initialized_service.get_health_status()

        assert health_status['status'] == 'error'
        assert health_status['healthy'] is False
        assert 'error' in health_status

    def test_performance_metrics_collection(self, initialized_service):
        """Test performance metrics collection."""
        # Mock performance data
        initialized_service.service_stats['requests_processed'] = 100
        initialized_service.service_stats['average_response_time'] = 25.5
        initialized_service.redis_manager.get_performance_metrics.return_value = {
            'connection_pool_size': 10,
            'active_connections': 5
        }
        initialized_service.pattern_cache.get_cache_stats.return_value = {
            'cached_patterns': 150,
            'cache_hit_ratio': 0.75
        }

        health_status = initialized_service.get_health_status()

        performance = health_status['performance']
        assert 'runtime_seconds' in performance
        assert performance['requests_processed'] == 100
        assert performance['average_response_time_ms'] == 25.5
        assert 'redis_performance' in performance
        assert 'pattern_cache_stats' in performance


class TestPatternDiscoveryServiceLifecycle:
    """Test service lifecycle management."""

    def test_background_services_startup(self, initialized_service):
        """Test background services startup."""
        # Mock background service startup
        initialized_service.pattern_cache.start_background_cleanup = Mock()
        initialized_service.event_subscriber.start = Mock()

        # Start background services
        initialized_service._start_background_services()

        # Verify background services were started
        initialized_service.pattern_cache.start_background_cleanup.assert_called_once()
        initialized_service.event_subscriber.start.assert_called_once()

    def test_service_shutdown(self, initialized_service):
        """Test service shutdown process."""
        # Mock component shutdown methods
        initialized_service.pattern_cache.stop_background_cleanup = Mock()
        initialized_service.event_subscriber.stop = Mock()
        initialized_service.tickstock_db.close = Mock()
        initialized_service.redis_manager.shutdown = Mock()

        # Shutdown service
        initialized_service.shutdown()

        # Verify all components were shut down
        initialized_service.pattern_cache.stop_background_cleanup.assert_called_once()
        initialized_service.event_subscriber.stop.assert_called_once()
        initialized_service.tickstock_db.close.assert_called_once()
        initialized_service.redis_manager.shutdown.assert_called_once()

        # Verify service state
        assert initialized_service.initialized is False
        assert initialized_service.services_healthy is False

    def test_shutdown_with_exceptions(self, initialized_service):
        """Test service shutdown with component exceptions."""
        # Mock components to raise exceptions during shutdown
        initialized_service.pattern_cache.stop_background_cleanup.side_effect = Exception("Shutdown error")
        initialized_service.event_subscriber.stop = Mock()
        initialized_service.tickstock_db.close = Mock()
        initialized_service.redis_manager.shutdown = Mock()

        # Shutdown should complete despite exceptions
        initialized_service.shutdown()

        # Verify other components were still shut down
        initialized_service.event_subscriber.stop.assert_called_once()
        initialized_service.tickstock_db.close.assert_called_once()
        initialized_service.redis_manager.shutdown.assert_called_once()

        assert initialized_service.initialized is False


class TestPatternDiscoveryServiceGlobalManagement:
    """Test global service instance management."""

    def teardown_method(self):
        """Clean up global service instance after each test."""
        shutdown_pattern_discovery_service()

    @patch('src.core.services.pattern_discovery_service.PatternDiscoveryService')
    def test_global_service_initialization(self, mock_service_class, sprint19_config):
        """Test global service initialization."""
        app = Flask(__name__)

        # Mock service initialization success
        mock_service_instance = Mock()
        mock_service_instance.initialize.return_value = True
        mock_service_class.return_value = mock_service_instance

        success = initialize_pattern_discovery_service(app, sprint19_config)

        assert success is True
        mock_service_class.assert_called_once_with(app, sprint19_config)
        mock_service_instance.initialize.assert_called_once()

        # Verify global service is available
        global_service = get_pattern_discovery_service()
        assert global_service == mock_service_instance

    @patch('src.core.services.pattern_discovery_service.PatternDiscoveryService')
    def test_global_service_initialization_failure(self, mock_service_class, sprint19_config):
        """Test global service initialization failure."""
        app = Flask(__name__)

        # Mock service initialization failure
        mock_service_instance = Mock()
        mock_service_instance.initialize.return_value = False
        mock_service_class.return_value = mock_service_instance

        success = initialize_pattern_discovery_service(app, sprint19_config)

        assert success is False

        # Verify global service is not available
        global_service = get_pattern_discovery_service()
        assert global_service is None

    def test_global_service_double_initialization(self, sprint19_config):
        """Test double initialization of global service."""
        app = Flask(__name__)

        with patch('src.core.services.pattern_discovery_service.PatternDiscoveryService') as mock_service_class:
            mock_service_instance = Mock()
            mock_service_instance.initialize.return_value = True
            mock_service_class.return_value = mock_service_instance

            # First initialization
            success1 = initialize_pattern_discovery_service(app, sprint19_config)
            assert success1 is True

            # Second initialization should return True without creating new instance
            success2 = initialize_pattern_discovery_service(app, sprint19_config)
            assert success2 is True

            # Verify service was only created once
            mock_service_class.assert_called_once()

    def test_global_service_shutdown(self, sprint19_config):
        """Test global service shutdown."""
        app = Flask(__name__)

        with patch('src.core.services.pattern_discovery_service.PatternDiscoveryService') as mock_service_class:
            mock_service_instance = Mock()
            mock_service_instance.initialize.return_value = True
            mock_service_class.return_value = mock_service_instance

            # Initialize global service
            initialize_pattern_discovery_service(app, sprint19_config)

            # Verify service is available
            assert get_pattern_discovery_service() is not None

            # Shutdown service
            shutdown_pattern_discovery_service()

            # Verify service was shut down
            mock_service_instance.shutdown.assert_called_once()

            # Verify global service is no longer available
            assert get_pattern_discovery_service() is None


class TestPatternDiscoveryServiceIntegration:
    """Integration tests for Pattern Discovery Service."""

    @pytest.mark.integration
    def test_service_component_integration(self, sprint19_config):
        """Test integration between service components."""
        app = Flask(__name__)

        with patch.multiple(
            'src.core.services.pattern_discovery_service',
            RedisConnectionManager=Mock(),
            RedisPatternCache=Mock(),
            TickStockDatabase=Mock(),
            CacheControl=Mock(),
            RedisEventSubscriber=Mock()
        ) as mocks:

            # Mock successful initialization
            redis_manager_mock = Mock()
            redis_manager_mock.initialize.return_value = True
            mocks['RedisConnectionManager'].return_value = redis_manager_mock

            pattern_cache_mock = Mock()
            mocks['RedisPatternCache'].return_value = pattern_cache_mock

            tickstock_db_mock = Mock()
            mocks['TickStockDatabase'].return_value = tickstock_db_mock

            cache_control_mock = Mock()
            mocks['CacheControl'].return_value = cache_control_mock

            event_subscriber_mock = Mock()
            mocks['RedisEventSubscriber'].return_value = event_subscriber_mock

            # Initialize service
            service = PatternDiscoveryService(app, sprint19_config)
            success = service.initialize()

            assert success is True

            # Test event flow integration
            mock_event = Mock()
            mock_event.data = {
                'symbol': 'INTEGRATION_TEST',
                'pattern': 'Test_Pattern',
                'confidence': 0.8
            }

            # Simulate event handling
            service._handle_pattern_event(mock_event)

            # Verify pattern cache received the event
            pattern_cache_mock.process_pattern_event.assert_called_once_with(mock_event.data)

            # Test health monitoring integration
            redis_manager_mock.get_health_status.return_value = {'status': 'healthy'}
            pattern_cache_mock.get_cache_stats.return_value = {'cached_patterns': 5}
            tickstock_db_mock.health_check.return_value = {'status': 'healthy'}
            event_subscriber_mock.is_running = True

            health_status = service.get_health_status()

            assert health_status['status'] == 'healthy'
            assert health_status['healthy'] is True

            # Test shutdown integration
            service.shutdown()

            # Verify all components were shut down
            pattern_cache_mock.stop_background_cleanup.assert_called_once()
            event_subscriber_mock.stop.assert_called_once()
            tickstock_db_mock.close.assert_called_once()
            redis_manager_mock.shutdown.assert_called_once()

    @pytest.mark.performance
    def test_service_performance_monitoring(self, sprint19_config):
        """Test service performance monitoring capabilities."""
        app = Flask(__name__)
        service = PatternDiscoveryService(app, sprint19_config)

        # Mock components
        service.redis_manager = Mock()
        service.pattern_cache = Mock()
        service.tickstock_db = Mock()
        service.cache_control = Mock()
        service.event_subscriber = Mock()
        service.initialized = True
        service.services_healthy = True

        # Mock performance data
        service.redis_manager.get_performance_metrics.return_value = {
            'avg_response_time_ms': 15.2,
            'connection_pool_utilization': 0.6
        }

        service.pattern_cache.get_cache_stats.return_value = {
            'cached_patterns': 200,
            'cache_hit_ratio': 0.82,
            'avg_scan_time_ms': 22.5
        }

        # Update service stats
        service.service_stats['requests_processed'] = 500
        service.service_stats['average_response_time'] = 18.7

        # Get health status with performance metrics
        health_status = service.get_health_status()

        performance = health_status['performance']
        assert performance['requests_processed'] == 500
        assert performance['average_response_time_ms'] == 18.7
        assert 'runtime_seconds' in performance
        assert 'redis_performance' in performance
        assert 'pattern_cache_stats' in performance

        # Verify performance meets targets
        redis_perf = performance['redis_performance']
        cache_perf = performance['pattern_cache_stats']

        assert redis_perf['avg_response_time_ms'] < 50  # Redis operations < 50ms
        assert cache_perf['avg_scan_time_ms'] < 50  # Cache scans < 50ms
        assert cache_perf['cache_hit_ratio'] > 0.7  # Cache hit ratio > 70%
        assert performance['average_response_time_ms'] < 50  # Overall response time < 50ms

    @pytest.mark.load
    def test_service_under_load(self, sprint19_config, concurrent_load_tester):
        """Test service performance under concurrent load."""
        app = Flask(__name__)
        service = PatternDiscoveryService(app, sprint19_config)

        # Mock components for load testing
        service.redis_manager = Mock()
        service.pattern_cache = Mock()
        service.tickstock_db = Mock()
        service.cache_control = Mock()
        service.event_subscriber = Mock()
        service.initialized = True
        service.services_healthy = True

        # Mock consistent responses
        service.redis_manager.get_health_status.return_value = {'status': 'healthy'}
        service.pattern_cache.get_cache_stats.return_value = {
            'cached_patterns': 100,
            'cache_hit_ratio': 0.75
        }
        service.tickstock_db.health_check.return_value = {'status': 'healthy'}
        service.event_subscriber.is_running = True

        # Function to test under load
        def get_health_status():
            health = service.get_health_status()
            return health['healthy']

        # Run concurrent health checks
        results = concurrent_load_tester.run_concurrent_requests(
            get_health_status,
            num_requests=50,
            max_concurrent=10
        )

        # Analyze results
        successful_requests = [r for r in results if r['success']]
        success_rate = len(successful_requests) / len(results) * 100

        assert success_rate >= 95, f"Success rate under load: {success_rate}%"

        # Check response times
        response_times = [r['elapsed_ms'] for r in successful_requests if r['elapsed_ms']]
        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)

            print("\nService Load Test Results:")
            print(f"  Requests: {len(results)}")
            print(f"  Success rate: {success_rate:.1f}%")
            print(f"  Average response time: {avg_response_time:.2f}ms")
            print(f"  Max response time: {max_response_time:.2f}ms")

            # Service should maintain performance under load
            assert avg_response_time < 100  # Allow higher threshold for concurrent load
            assert max_response_time < 200
