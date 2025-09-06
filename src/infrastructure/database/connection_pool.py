"""
Database Connection Pool for Sprint 23 Analytics
==============================================

Provides async database connection pool for Sprint 23 advanced analytics services.
Wraps the existing TickStockDatabase class with async interface for compatibility
with the analytics services.

Author: TickStock Development Team  
Date: 2025-09-06
Sprint: 23
"""

import logging
import asyncio
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager
import psycopg2
from psycopg2.extras import RealDictCursor

from src.infrastructure.database.tickstock_db import TickStockDatabase

logger = logging.getLogger(__name__)

class AsyncDatabaseConnection:
    """Async wrapper for database connections with cursor management"""
    
    def __init__(self, connection):
        self.connection = connection
        
    def cursor(self):
        """Return async cursor context manager"""
        return AsyncCursor(self.connection.cursor(cursor_factory=RealDictCursor))
    
    async def close(self):
        """Close the database connection"""
        if self.connection:
            self.connection.close()

class AsyncCursor:
    """Async wrapper for database cursor operations"""
    
    def __init__(self, cursor):
        self.cursor = cursor
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.cursor.close()
        
    async def execute(self, query: str, params: Optional[tuple] = None):
        """Execute a database query"""
        if params:
            self.cursor.execute(query, params)
        else:
            self.cursor.execute(query)
            
    async def fetchone(self):
        """Fetch one result row"""
        return self.cursor.fetchone()
        
    async def fetchall(self):
        """Fetch all result rows"""
        return self.cursor.fetchall()

class DatabaseConnectionPool:
    """Async database connection pool for Sprint 23 analytics services"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize async database connection pool
        
        Args:
            config: Database configuration (optional, uses environment if None)
        """
        self.config = config or {}
        self.tickstock_db = TickStockDatabase(self.config)
        self._test_connection()
        
    def _test_connection(self):
        """Test that database connection works"""
        try:
            # Test using direct psycopg2 connection
            with psycopg2.connect(self.tickstock_db.connection_url) as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
            logger.info("ANALYTICS-DB: Connection pool initialized successfully")
        except Exception as e:
            logger.error(f"ANALYTICS-DB: Connection pool initialization failed: {e}")
            raise
    
    @asynccontextmanager
    async def get_connection(self):
        """Get async database connection context manager
        
        Usage:
            async with db_pool.get_connection() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SELECT * FROM table")
                    result = await cursor.fetchone()
        """
        connection = None
        try:
            # Get connection from existing TickStockDatabase pool
            connection = psycopg2.connect(self.tickstock_db.connection_url)
            async_conn = AsyncDatabaseConnection(connection)
            yield async_conn
        except Exception as e:
            logger.error(f"ANALYTICS-DB: Connection error: {e}")
            raise
        finally:
            if connection:
                connection.close()
    
    async def execute_analytics_function(self, function_name: str, params: Optional[tuple] = None) -> list:
        """Execute a Sprint 23 analytics function and return results
        
        Args:
            function_name: Name of the database function to execute
            params: Optional parameters for the function
            
        Returns:
            List of result rows
        """
        try:
            async with self.get_connection() as conn:
                async with conn.cursor() as cursor:
                    query = f"SELECT * FROM {function_name}"
                    if params:
                        query += f"({', '.join(['%s'] * len(params))})"
                    else:
                        query += "()"
                    
                    await cursor.execute(query, params)
                    results = await cursor.fetchall()
                    
                    logger.info(f"ANALYTICS-DB: Executed {function_name}, returned {len(results)} rows")
                    return results
                    
        except Exception as e:
            logger.error(f"ANALYTICS-DB: Error executing {function_name}: {e}")
            raise
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection pool information"""
        return {
            'connection_url_safe': self.tickstock_db.connection_url.replace(
                self.tickstock_db.connection_url.split('@')[0].split('//')[1], 
                '***:***'
            ),
            'status': 'connected',
            'database': 'tickstock'
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on connection pool"""
        try:
            async with self.get_connection() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SELECT 1 as health_check")
                    result = await cursor.fetchone()
                    
            return {
                'status': 'healthy',
                'connection': 'available',
                'database': 'tickstock',
                'timestamp': '2025-09-06'
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': '2025-09-06'
            }