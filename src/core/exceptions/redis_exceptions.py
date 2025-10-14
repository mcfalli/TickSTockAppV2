"""
Redis-specific exceptions for TickStockAppV2 startup validation.

These exceptions are used to enforce mandatory Redis connectivity requirements
for TickStockPL integration and real-time market data processing.
"""

class RedisConnectionError(Exception):
    """
    Redis connection is required but not available.
    
    Raised when basic Redis connectivity cannot be established.
    This is a critical startup failure requiring immediate attention.
    """
    pass


class RedisChannelError(Exception):
    """
    Required Redis pub-sub channels not accessible.
    
    Raised when Redis is connected but pub-sub functionality
    required for TickStockPL integration is not working.
    """
    pass


class RedisPerformanceError(Exception):
    """
    Redis performance below acceptable thresholds.
    
    Raised when Redis connectivity is working but response times
    exceed real-time processing requirements (<50ms operations).
    """
    pass


class RedisConfigurationError(Exception):
    """
    Redis configuration is invalid or incomplete.
    
    Raised when required Redis configuration parameters are missing
    or have invalid values.
    """
    pass
