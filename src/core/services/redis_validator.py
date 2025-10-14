"""
Redis connectivity validation and mandatory startup checks.

This module provides comprehensive Redis validation for TickStockAppV2 startup,
ensuring all TickStockPL integration requirements are met before proceeding.
"""

import json
import logging
import time
from typing import Any

import redis

from src.core.exceptions.redis_exceptions import (
    RedisChannelError,
    RedisConfigurationError,
    RedisConnectionError,
    RedisPerformanceError,
)

logger = logging.getLogger(__name__)


def validate_redis_config(config: dict[str, Any]) -> None:
    """
    Validate Redis configuration before attempting connection.
    
    Args:
        config: Configuration dictionary
        
    Raises:
        RedisConfigurationError: If configuration is invalid or incomplete
    """
    # Check for Redis URL or individual settings
    redis_url = config.get('REDIS_URL')

    if redis_url:
        if not redis_url.strip():
            raise RedisConfigurationError("REDIS_URL is configured but empty")
        return

    # Check individual Redis settings
    required_keys = ['REDIS_HOST', 'REDIS_PORT', 'REDIS_DB']
    missing_keys = []

    for key in required_keys:
        value = config.get(key)
        if value is None:
            missing_keys.append(key)

    if missing_keys:
        raise RedisConfigurationError(
            f"Missing required Redis configuration: {missing_keys}. "
            f"Either provide REDIS_URL or individual settings (REDIS_HOST, REDIS_PORT, REDIS_DB)"
        )

    # Validate values
    try:
        port = int(config['REDIS_PORT'])
        if not (1 <= port <= 65535):
            raise RedisConfigurationError(f"Invalid Redis port: {port} (must be 1-65535)")
    except (ValueError, TypeError):
        raise RedisConfigurationError(f"Redis port must be integer: {config['REDIS_PORT']}")

    try:
        db = int(config['REDIS_DB'])
        if not (0 <= db <= 15):
            raise RedisConfigurationError(f"Invalid Redis database: {db} (must be 0-15)")
    except (ValueError, TypeError):
        raise RedisConfigurationError(f"Redis database must be integer: {config['REDIS_DB']}")


def create_redis_client(config: dict[str, Any]) -> redis.Redis:
    """
    Create Redis client from configuration.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Configured Redis client
        
    Raises:
        RedisConfigurationError: If configuration is invalid
    """
    validate_redis_config(config)

    redis_url = config.get('REDIS_URL')

    if redis_url:
        try:
            return redis.Redis.from_url(
                redis_url,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
                health_check_interval=30
            )
        except Exception as e:
            raise RedisConfigurationError(f"Invalid REDIS_URL: {e}")

    # Use individual settings
    redis_host = config.get('REDIS_HOST', 'localhost')
    redis_port = int(config['REDIS_PORT'])
    redis_db = int(config['REDIS_DB'])

    return redis.Redis(
        host=redis_host,
        port=redis_port,
        db=redis_db,
        decode_responses=True,
        socket_timeout=5,
        socket_connect_timeout=5,
        health_check_interval=30
    )


def test_basic_connectivity(redis_client: redis.Redis, timeout: float = 5.0, environment: str = 'PRODUCTION') -> dict[str, Any]:
    """
    Test basic Redis connectivity with performance validation.
    
    Args:
        redis_client: Redis client instance
        timeout: Maximum time to wait for response
        environment: Environment (DEVELOPMENT/PRODUCTION) for performance thresholds
        
    Returns:
        Dictionary with connectivity test results
        
    Raises:
        RedisConnectionError: If basic connectivity fails
        RedisPerformanceError: If performance is below requirements
    """
    try:
        start_time = time.time()
        result = redis_client.ping()
        response_time = (time.time() - start_time) * 1000

        if not result:
            raise RedisConnectionError("Redis ping returned False - connection invalid")

        # Performance validation with environment-aware thresholds
        # PRODUCTION: <50ms for real-time processing
        # DEVELOPMENT: <5000ms for local development with Docker
        max_latency = 50 if environment == 'PRODUCTION' else 5000
        target_desc = '50ms' if environment == 'PRODUCTION' else '5000ms'

        if response_time > max_latency:
            raise RedisPerformanceError(
                f"Redis ping latency too high: {response_time:.2f}ms (target: <{target_desc}). "
                f"This will impact real-time market data processing in {environment} environment."
            )

        # Get server info for diagnostics
        info = redis_client.info('server')

        logger.info(f"REDIS: Basic connectivity validated - ping: {response_time:.2f}ms")
        logger.info(f"REDIS: Server info - version: {info.get('redis_version', 'unknown')}, "
                   f"uptime: {info.get('uptime_in_seconds', 0)}s")

        return {
            'ping_success': True,
            'response_time_ms': round(response_time, 2),
            'redis_version': info.get('redis_version'),
            'uptime_seconds': info.get('uptime_in_seconds'),
            'used_memory_human': info.get('used_memory_human')
        }

    except redis.ConnectionError as e:
        raise RedisConnectionError(f"Redis connection failed: {e}")
    except redis.TimeoutError as e:
        raise RedisConnectionError(f"Redis connection timeout: {e}")
    except (RedisConnectionError, RedisPerformanceError):
        raise
    except Exception as e:
        raise RedisConnectionError(f"Unexpected Redis connectivity error: {e}")


def validate_pubsub_channels(redis_client: redis.Redis) -> dict[str, Any]:
    """
    Validate Redis pub-sub functionality and required channels.
    
    Args:
        redis_client: Redis client instance
        
    Returns:
        Dictionary with pub-sub validation results
        
    Raises:
        RedisChannelError: If pub-sub functionality is not working
    """
    required_channels = [
        'tickstock.events.patterns',
        'tickstock.events.backtesting.progress',
        'tickstock.events.backtesting.results',
        'tickstock.health.status'
    ]

    try:
        # Test pub-sub subscription capability
        pubsub = redis_client.pubsub()
        test_channel = "tickstock.test.connectivity"

        # Test subscription
        pubsub.subscribe(test_channel)

        # Validate subscription worked - get the subscription confirmation message
        message = pubsub.get_message(timeout=2.0)
        if not message or message['type'] != 'subscribe':
            raise RedisChannelError("Redis pub-sub subscription test failed - no confirmation message")

        # Test publishing capability
        test_payload = {"test": "connectivity", "timestamp": time.time()}
        publish_result = redis_client.publish(test_channel, json.dumps(test_payload))

        # Check if we can receive the published message
        published_message = pubsub.get_message(timeout=2.0)
        if not published_message or published_message['type'] != 'message':
            logger.warning("REDIS: Pub-sub message delivery test failed - message not received")

        # Cleanup test subscription
        pubsub.unsubscribe(test_channel)
        pubsub.close()

        # Check channel permissions for required channels
        channel_status = {}
        for channel in required_channels:
            try:
                # Test if we can publish to the channel (validates permissions)
                test_result = redis_client.publish(channel, '{"test": "permission_check"}')
                channel_status[channel] = "accessible"
            except Exception as e:
                channel_status[channel] = f"error: {e}"

        # Check if any channels are inaccessible
        failed_channels = [ch for ch, status in channel_status.items() if status.startswith("error:")]
        if failed_channels:
            raise RedisChannelError(
                f"Required Redis channels inaccessible: {failed_channels}. "
                f"TickStockPL integration requires pub-sub access to these channels."
            )

        logger.info(f"REDIS: Pub-sub validation successful for {len(required_channels)} channels")

        return {
            'pubsub_functional': True,
            'test_publish_result': publish_result,
            'required_channels': required_channels,
            'channel_status': channel_status
        }

    except redis.ConnectionError as e:
        raise RedisChannelError(f"Redis connection lost during pub-sub test: {e}")
    except RedisChannelError:
        raise
    except Exception as e:
        raise RedisChannelError(f"Redis pub-sub validation failed: {e}")


def validate_redis_performance(redis_client: redis.Redis, test_count: int = 5, environment: str = 'PRODUCTION') -> dict[str, Any]:
    """
    Validate Redis performance meets TickStock real-time requirements.
    
    Args:
        redis_client: Redis client instance
        test_count: Number of performance tests to run
        environment: Environment (DEVELOPMENT/PRODUCTION) for performance thresholds
        
    Returns:
        Dictionary with performance test results
        
    Raises:
        RedisPerformanceError: If performance is below requirements
    """
    performance_tests = []

    try:
        # Test ping latency multiple times for statistical accuracy
        for i in range(test_count):
            start_time = time.time()
            redis_client.ping()
            latency = (time.time() - start_time) * 1000
            performance_tests.append(latency)

        avg_latency = sum(performance_tests) / len(performance_tests)
        max_latency = max(performance_tests)
        min_latency = min(performance_tests)

        # Performance requirements with environment-aware thresholds
        # PRODUCTION: Average <10ms, Maximum <50ms for real-time processing
        # DEVELOPMENT: Relaxed thresholds for local Docker development
        warnings = []

        if environment == 'PRODUCTION':
            avg_threshold = 10
            max_threshold = 50
            warning_threshold = 25
        else:  # DEVELOPMENT
            avg_threshold = 100  # More relaxed for development
            max_threshold = 5000  # Allow Docker container startup delays
            warning_threshold = 1000

        if avg_latency > avg_threshold:
            warnings.append(f"High average latency: {avg_latency:.2f}ms (target: <{avg_threshold}ms in {environment})")

        if max_latency > max_threshold:
            raise RedisPerformanceError(
                f"Redis maximum latency too high: {max_latency:.2f}ms (target: <{max_threshold}ms). "
                f"This will cause processing delays in {environment} environment."
            )

        if max_latency > warning_threshold:
            warnings.append(f"High maximum latency: {max_latency:.2f}ms (target: <{warning_threshold}ms in {environment})")

        if warnings:
            for warning in warnings:
                logger.warning(f"REDIS: Performance warning - {warning}")

        logger.info(f"REDIS: Performance validation passed - "
                   f"avg: {avg_latency:.2f}ms, max: {max_latency:.2f}ms, min: {min_latency:.2f}ms")

        return {
            'performance_acceptable': True,
            'avg_latency_ms': round(avg_latency, 2),
            'max_latency_ms': round(max_latency, 2),
            'min_latency_ms': round(min_latency, 2),
            'test_count': test_count,
            'warnings': warnings
        }

    except RedisPerformanceError:
        raise
    except Exception as e:
        raise RedisPerformanceError(f"Redis performance validation failed: {e}")


def initialize_redis_mandatory(config: dict[str, Any], environment: str = 'PRODUCTION') -> redis.Redis:
    """
    Initialize Redis with mandatory connectivity validation for TickStockPL integration.
    
    This function performs comprehensive validation of Redis connectivity, pub-sub functionality,
    and performance requirements. If any validation fails, the function raises appropriate
    exceptions to fail the startup process.
    
    Args:
        config: Configuration dictionary
        environment: Environment (DEVELOPMENT/PRODUCTION) for performance thresholds
        
    Returns:
        Validated Redis client instance
        
    Raises:
        RedisConfigurationError: If Redis configuration is invalid
        RedisConnectionError: If basic Redis connectivity fails
        RedisChannelError: If pub-sub functionality is not working
        RedisPerformanceError: If performance is below requirements
    """
    logger.info("REDIS: Starting mandatory connectivity validation...")

    # Step 1: Configuration validation
    logger.info("REDIS: Validating configuration...")
    validate_redis_config(config)

    # Step 2: Create Redis client
    logger.info("REDIS: Creating Redis client...")
    redis_client = create_redis_client(config)

    # Step 3: Basic connectivity test
    logger.info(f"REDIS: Testing basic connectivity ({environment} environment)...")
    connectivity_results = test_basic_connectivity(redis_client, environment=environment)

    # Step 4: Pub-sub validation
    logger.info("REDIS: Validating pub-sub functionality...")
    pubsub_results = validate_pubsub_channels(redis_client)

    # Step 5: Performance validation
    logger.info(f"REDIS: Validating performance requirements ({environment} environment)...")
    performance_results = validate_redis_performance(redis_client, environment=environment)

    # All validations passed
    logger.info("REDIS: [SUCCESS] All mandatory validations passed successfully")
    logger.info(f"REDIS: Ready for TickStockPL integration - "
               f"ping: {connectivity_results['response_time_ms']}ms, "
               f"channels: {len(pubsub_results['required_channels'])}, "
               f"performance: avg {performance_results['avg_latency_ms']}ms")

    return redis_client


def generate_redis_failure_report(error_type: str, error_details: str) -> str:
    """
    Generate user-friendly Redis failure diagnostics with troubleshooting guidance.
    
    Args:
        error_type: Type of Redis error ('connection', 'channels', 'performance', 'config')
        error_details: Detailed error information
        
    Returns:
        Formatted error report string
    """
    reports = {
        'connection': {
            'title': 'Redis Connection Failed',
            'message': 'TickStockAppV2 cannot establish connection to Redis server',
            'solutions': [
                'Verify Redis server is running and accessible',
                'Check Redis connection settings (host, port, database)',
                'Verify network connectivity between TickStockApp and Redis',
                'Check Redis server logs for connection errors',
                'Ensure Redis server is not overloaded or out of memory'
            ]
        },
        'channels': {
            'title': 'Redis Pub-Sub Channels Unavailable',
            'message': 'TickStockPL integration requires Redis pub-sub functionality',
            'solutions': [
                'Verify Redis pub-sub is enabled in server configuration',
                'Check Redis ACL permissions for pub-sub operations',
                'Ensure sufficient Redis memory for pub-sub message storage',
                'Verify Redis CLIENT commands are not disabled',
                'Check for Redis MAXMEMORY policy conflicts with pub-sub'
            ]
        },
        'performance': {
            'title': 'Redis Performance Below Requirements',
            'message': 'Redis response times exceed real-time processing thresholds',
            'solutions': [
                'Check Redis server CPU and memory utilization',
                'Verify network latency between TickStockApp and Redis',
                'Review Redis configuration for performance optimization',
                'Check for competing Redis workloads or slow queries',
                'Consider Redis server hardware upgrade or optimization'
            ]
        },
        'config': {
            'title': 'Redis Configuration Invalid',
            'message': 'Redis connection configuration is missing or invalid',
            'solutions': [
                'Verify REDIS_URL environment variable is set correctly',
                'Check individual Redis settings (REDIS_HOST, REDIS_PORT, REDIS_DB)',
                'Ensure Redis configuration values are valid (port 1-65535, db 0-15)',
                'Verify .env file contains proper Redis configuration',
                'Check for typos in Redis configuration variable names'
            ]
        }
    }

    report = reports.get(error_type, {
        'title': 'Redis Error',
        'message': 'Unknown Redis connectivity issue',
        'solutions': ['Check Redis server status and TickStockAppV2 configuration']
    })

    separator = "=" * 80
    output = []

    output.append(separator)
    output.append(f"STARTUP FAILURE: {report['title']}")
    output.append(separator)
    output.append(f"Problem: {report['message']}")
    output.append(f"Details: {error_details}")
    output.append("")
    output.append("Troubleshooting Steps:")
    for i, solution in enumerate(report['solutions'], 1):
        output.append(f"  {i}. {solution}")
    output.append("")
    output.append("Redis is mandatory for TickStockPL integration:")
    output.append("  - Pattern discovery and real-time alerts")
    output.append("  - Backtesting job submission and results")
    output.append("  - Real-time market data event processing")
    output.append("  - System health monitoring and diagnostics")
    output.append("")
    output.append("TickStockAppV2 cannot function without Redis connectivity.")
    output.append(separator)

    return "\n".join(output)
