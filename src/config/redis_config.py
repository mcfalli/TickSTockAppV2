"""
Redis Configuration Module
Provides Redis connection management for TickStock services
"""

import os
import redis
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_redis_client():
    """
    Get a Redis client connection.
    
    Returns:
        redis.Redis client object
    """
    redis_host = os.getenv('REDIS_HOST', 'localhost')
    redis_port = int(os.getenv('REDIS_PORT', 6379))
    redis_db = int(os.getenv('REDIS_DB', 0))
    redis_password = os.getenv('REDIS_PASSWORD')
    
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
    return {
        'host': os.getenv('REDIS_HOST', 'localhost'),
        'port': int(os.getenv('REDIS_PORT', 6379)),
        'db': int(os.getenv('REDIS_DB', 0)),
        'password': os.getenv('REDIS_PASSWORD')
    }