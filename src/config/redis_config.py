"""
Redis Configuration Module
Provides Redis connection management for TickStock services
"""

import redis
from src.core.services.config_manager import get_config

def get_redis_client():
    """
    Get a Redis client connection.

    Returns:
        redis.Redis client object
    """
    config = get_config()
    redis_host = config.get('REDIS_HOST', 'localhost')
    redis_port = config.get('REDIS_PORT', 6379)
    redis_db = config.get('REDIS_DB', 0)
    redis_password = config.get('REDIS_PASSWORD')
    
    connection_params = {
        'host': redis_host,
        'port': redis_port,
        'db': redis_db,
        'decode_responses': True
    }
    
    if redis_password:
        connection_params['password'] = redis_password
    
    return redis.Redis(**connection_params)

def get_redis_config():
    """
    Get Redis configuration dictionary.

    Returns:
        Dict with Redis connection parameters
    """
    config = get_config()
    return {
        'host': config.get('REDIS_HOST', 'localhost'),
        'port': config.get('REDIS_PORT', 6379),
        'db': config.get('REDIS_DB', 0),
        'password': config.get('REDIS_PASSWORD')
    }