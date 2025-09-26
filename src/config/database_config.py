"""
Database Configuration Module
Provides database connection management for TickStock services
"""

import psycopg2
from urllib.parse import urlparse
from src.core.services.config_manager import get_config

def get_database_connection():
    """
    Get a database connection using DATABASE_URI from config.

    Returns:
        psycopg2 connection object
    """
    config = get_config()
    database_url = config.get('DATABASE_URI')
    if not database_url:
        raise ValueError("DATABASE_URI not found in configuration")
    
    # Parse the database URL
    parsed = urlparse(database_url)
    
    connection_params = {
        "host": parsed.hostname,
        "port": parsed.port or 5432,
        "database": parsed.path.lstrip('/'),
        "user": parsed.username,
        "password": parsed.password
    }
    
    return psycopg2.connect(**connection_params)

def get_database_config():
    """
    Get database configuration dictionary.

    Returns:
        Dict with database connection parameters
    """
    config = get_config()
    database_url = config.get('DATABASE_URI')
    if not database_url:
        raise ValueError("DATABASE_URI not found in configuration")
    
    parsed = urlparse(database_url)
    
    return {
        "host": parsed.hostname,
        "port": parsed.port or 5432,
        "database": parsed.path.lstrip('/'),
        "user": parsed.username,
        "password": parsed.password
    }