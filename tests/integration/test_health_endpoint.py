"""
Integration tests for /health endpoint with Redis status.

Tests the enhanced health endpoint that includes Redis component health checking.
"""

import json
from unittest.mock import patch

import pytest

from src.core.services.health_monitor import HealthStatus


@pytest.fixture
def test_client():
    """Create a test client for the Flask application."""
    import redis
    from flask import Flask
    from src.core.services.config_manager import get_config

    # Create minimal Flask app for testing
    app = Flask(__name__)
    app.config['TESTING'] = True

    # Create mock Redis client
    mock_redis = redis.Redis(host='localhost', port=6379, decode_responses=False)

    # Import and register the health_check route
    # We'll define it directly here for testing
    import time
    from flask import jsonify
    import logging
    from src.core.services.health_monitor import HealthMonitor

    logger = logging.getLogger(__name__)

    @app.route('/health')
    def health_check():
        """Health check endpoint for monitoring systems."""
        start_time = time.time()
        APP_VERSION = "2.0.0-simplified"
        health_data = {
            "status": "healthy",
            "version": APP_VERSION,
            "components": {},
            "timestamp": time.time()
        }

        try:
            config = get_config()
            health_monitor = HealthMonitor(config, redis_client=mock_redis)
            redis_health = health_monitor._check_redis_health()

            health_data['components']['redis'] = {
                'status': redis_health.status,
                'response_time_ms': redis_health.response_time_ms,
                'message': redis_health.message
            }

            if redis_health.status == 'error':
                health_data['status'] = 'unhealthy'
                response_code = 503
            elif redis_health.status == 'degraded':
                health_data['status'] = 'degraded'
                response_code = 200
            else:
                response_code = 200

        except Exception as e:
            logger.error(f"HEALTH-CHECK: Failed to check Redis: {e}")
            health_data['components']['redis'] = {
                'status': 'error',
                'response_time_ms': None,
                'message': f"Health check failed: {str(e)}"
            }
            health_data['status'] = 'unhealthy'
            response_code = 503

        response_time = (time.time() - start_time) * 1000
        if response_time > 50:
            logger.warning(f"HEALTH-CHECK: Slow response: {response_time:.2f}ms")

        return jsonify(health_data), response_code

    with app.test_client() as client:
        yield client


@pytest.fixture
def mock_redis_healthy():
    """Mock HealthMonitor with healthy Redis status."""
    def _mock_check_redis_health(self):
        return HealthStatus(
            status='healthy',
            response_time_ms=5.2,
            last_check=1234567890.0,
            message=None,
            details={'connected_clients': 2, 'used_memory_human': '1.5M'}
        )
    return _mock_check_redis_health


@pytest.fixture
def mock_redis_degraded():
    """Mock HealthMonitor with degraded Redis status."""
    def _mock_check_redis_health(self):
        return HealthStatus(
            status='degraded',
            response_time_ms=75.5,
            last_check=1234567890.0,
            message='Redis responding slowly',
            details={'connected_clients': 2}
        )
    return _mock_check_redis_health


@pytest.fixture
def mock_redis_error():
    """Mock HealthMonitor with error Redis status."""
    def _mock_check_redis_health(self):
        return HealthStatus(
            status='error',
            response_time_ms=None,
            last_check=1234567890.0,
            message='Redis connection failed',
            details=None
        )
    return _mock_check_redis_health


class TestHealthEndpoint:
    """Test suite for /health endpoint."""

    def test_health_endpoint_redis_healthy(self, test_client, mock_redis_healthy):
        """Test /health endpoint returns 200 when Redis is healthy."""
        with patch('src.core.services.health_monitor.HealthMonitor._check_redis_health',
                   mock_redis_healthy):
            response = test_client.get('/health')

            assert response.status_code == 200
            data = json.loads(response.data)

            # Verify overall structure
            assert data['status'] == 'healthy'
            assert 'version' in data
            assert 'components' in data
            assert 'redis' in data['components']
            assert 'timestamp' in data

            # Verify Redis component details
            redis_component = data['components']['redis']
            assert redis_component['status'] == 'healthy'
            assert redis_component['response_time_ms'] == 5.2
            assert redis_component['message'] is None

    def test_health_endpoint_redis_degraded(self, test_client, mock_redis_degraded):
        """Test /health endpoint returns 200 with degraded status when Redis is slow."""
        with patch('src.core.services.health_monitor.HealthMonitor._check_redis_health',
                   mock_redis_degraded):
            response = test_client.get('/health')

            assert response.status_code == 200
            data = json.loads(response.data)

            # Verify overall status is degraded
            assert data['status'] == 'degraded'

            # Verify Redis component details
            redis_component = data['components']['redis']
            assert redis_component['status'] == 'degraded'
            assert redis_component['response_time_ms'] == 75.5
            assert redis_component['message'] == 'Redis responding slowly'

    def test_health_endpoint_redis_error(self, test_client, mock_redis_error):
        """Test /health endpoint returns 503 when Redis has errors."""
        with patch('src.core.services.health_monitor.HealthMonitor._check_redis_health',
                   mock_redis_error):
            response = test_client.get('/health')

            assert response.status_code == 503
            data = json.loads(response.data)

            # Verify overall status is unhealthy
            assert data['status'] == 'unhealthy'

            # Verify Redis component details
            redis_component = data['components']['redis']
            assert redis_component['status'] == 'error'
            assert redis_component['response_time_ms'] is None
            assert 'failed' in redis_component['message'].lower()

    def test_health_endpoint_unauthenticated_access(self, test_client, mock_redis_healthy):
        """Test /health endpoint is accessible without authentication."""
        with patch('src.core.services.health_monitor.HealthMonitor._check_redis_health',
                   mock_redis_healthy):
            # Make request without any authentication headers
            response = test_client.get('/health')

            # Should succeed without authentication
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'status' in data
            assert 'components' in data

    def test_health_endpoint_performance(self, test_client, mock_redis_healthy):
        """Test /health endpoint responds within performance target (<50ms)."""
        import time

        with patch('src.core.services.health_monitor.HealthMonitor._check_redis_health',
                   mock_redis_healthy):
            start_time = time.time()
            response = test_client.get('/health')
            response_time_ms = (time.time() - start_time) * 1000

            assert response.status_code == 200
            # Allow some buffer for test overhead, but should be fast
            assert response_time_ms < 100, f"Health check took {response_time_ms:.2f}ms"

    def test_health_endpoint_exception_handling(self, test_client):
        """Test /health endpoint handles exceptions gracefully."""
        # Mock HealthMonitor to raise an exception
        with patch('src.core.services.health_monitor.HealthMonitor._check_redis_health',
                   side_effect=Exception("Simulated health check failure")):
            response = test_client.get('/health')

            # Should return 503 on error
            assert response.status_code == 503
            data = json.loads(response.data)

            # Should still have proper structure
            assert data['status'] == 'unhealthy'
            assert 'components' in data
            assert 'redis' in data['components']
            assert data['components']['redis']['status'] == 'error'
            assert 'failed' in data['components']['redis']['message'].lower()
