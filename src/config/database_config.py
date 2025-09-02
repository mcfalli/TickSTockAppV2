"""
Database Configuration Module
Provides database connection management for TickStock services
"""

import os
import psycopg2
from urllib.parse import urlparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_database_connection():
    """
    Get a database connection using DATABASE_URI from environment.
    
    Returns:
        psycopg2 connection object
    """
    database_url = os.getenv('DATABASE_URI')
    if not database_url:
        raise ValueError("DATABASE_URI not found in environment variables")
    
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
    database_url = os.getenv('DATABASE_URI')
    if not database_url:
        raise ValueError("DATABASE_URI not found in environment variables")
    
    parsed = urlparse(database_url)
    
    return {
        "host": parsed.hostname,
        "port": parsed.port or 5432,
        "database": parsed.path.lstrip('/'),
        "user": parsed.username,
        "password": parsed.password
    }