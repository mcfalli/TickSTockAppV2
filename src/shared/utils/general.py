import time
import random
import logging
from datetime import datetime
import pytz
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)

def detect_market_status(timestamp: datetime) -> str:
    """
    Determines market status based on a timestamp.
    
    Args:
        timestamp: datetime in Eastern timezone
        
    Returns:
        str: Market status - "PRE", "REGULAR", "AFTER", or "CLOSED"
    """
    # Default to closed
    market_status = "CLOSED"
    
    # Skip if timestamp is None
    if timestamp is None:
        return market_status
        
    # Handle if timestamp is not timezone-aware
    if timestamp.tzinfo is None:
        eastern_tz = pytz.timezone('US/Eastern')
        timestamp = eastern_tz.localize(timestamp)
    elif timestamp.tzinfo != pytz.timezone('US/Eastern'):
        # Convert to Eastern time if in different timezone
        eastern_tz = pytz.timezone('US/Eastern')
        timestamp = timestamp.astimezone(eastern_tz)
    
    # Get day of week (0=Monday, 6=Sunday)
    day_of_week = timestamp.weekday()
    hour = timestamp.hour
    minute = timestamp.minute
    
    # Determine market status based on time and day
    if day_of_week < 5:  # Monday to Friday
        if (hour == 9 and minute >= 30) or (hour > 9 and hour < 16):
            market_status = "REGULAR"
        elif (hour >= 4 and hour < 9) or (hour == 9 and minute < 30):
            market_status = "PRE"
        elif hour >= 16 and hour < 20:
            market_status = "AFTER"
    
    return market_status

def get_eastern_time() -> datetime:
    """
    Get current time in Eastern timezone.
    
    Returns:
        datetime: Current time in Eastern timezone
    """
    eastern_tz = pytz.timezone('US/Eastern')
    utc_now = datetime.now(pytz.utc)
    return utc_now.astimezone(eastern_tz)

def format_price(price: float, include_dollar_sign: bool = True) -> str:
    """
    Format a price value with appropriate precision.
    
    Args:
        price: Price value to format
        include_dollar_sign: Whether to include dollar sign
        
    Returns:
        str: Formatted price string
    """
    if price is None:
        return "N/A"
        
    if price < 1:
        # For sub-dollar prices, show 4 decimal places
        formatted = f"{price:.4f}"
    elif price < 10:
        # For prices under $10, show 3 decimal places
        formatted = f"{price:.3f}"
    elif price < 1000:
        # For regular prices, show 2 decimal places
        formatted = f"{price:.2f}"
    else:
        # For large prices, show no decimal places
        formatted = f"{price:.0f}"
        
    if include_dollar_sign:
        return f"${formatted}"
    return formatted

def calculate_percentage_change(old_value: float, new_value: float) -> float:
    """
    Calculate percentage change between two values.
    
    Args:
        old_value: Original value
        new_value: New value
        
    Returns:
        float: Percentage change
    """
    if old_value == 0:
        return 0  # Avoid division by zero
        
    return ((new_value - old_value) / abs(old_value)) * 100

def safe_divide(numerator: float, denominator: float, default: float = 0) -> float:
    """
    Safely divide two numbers, returning default if denominator is zero.
    
    Args:
        numerator: Value to divide
        denominator: Value to divide by
        default: Value to return if denominator is zero
        
    Returns:
        float: Result of division or default
    """
    return numerator / denominator if denominator != 0 else default

def exponential_moving_average(values: List[float], alpha: float = 0.3) -> List[float]:
    """
    Calculate exponential moving average of a list of values.
    
    Args:
        values: List of values to average
        alpha: Smoothing factor (0-1), higher values give more weight to recent data
        
    Returns:
        List[float]: EMA values
    """
    if not values:
        return []
        
    ema_values = [values[0]]  # Start with first value
    
    for i in range(1, len(values)):
        ema = alpha * values[i] + (1 - alpha) * ema_values[-1]
        ema_values.append(ema)
        
    return ema_values

def rate_limiter(max_calls: int, period: float):
    """
    Decorator to rate limit function calls.
    
    Args:
        max_calls: Maximum number of calls allowed in the period
        period: Time period in seconds
        
    Returns:
        Function: Decorated function
    """
    calls = []
    
    def decorator(func):
        def wrapper(*args, **kwargs):
            current_time = time.time()
            
            # Remove calls older than the period
            nonlocal calls
            calls = [call_time for call_time in calls if current_time - call_time <= period]
            
            # Check if we've exceeded the rate limit
            if len(calls) >= max_calls:
                sleep_time = calls[0] + period - current_time
                if sleep_time > 0:
                    logger.info(f"Rate limit reached, sleeping for {sleep_time:.2f}s")
                    time.sleep(sleep_time)
                    
            # Add current call time
            calls.append(time.time())
            
            # Call the original function
            return func(*args, **kwargs)
        return wrapper
    return decorator

def retry_with_backoff(max_retries: int = 3, initial_backoff: float = 1, max_backoff: float = 60):
    """
    Decorator to retry a function with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_backoff: Initial backoff time in seconds
        max_backoff: Maximum backoff time in seconds
        
    Returns:
        Function: Decorated function
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            retries = 0
            backoff = initial_backoff
            
            while True:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries > max_retries:
                        raise
                        
                    logger.warning(f"Retry {retries}/{max_retries} for {func.__name__} after error: {e}")
                    
                    # Calculate backoff with jitter
                    jitter = backoff * 0.1 * (2 * random.random() - 1)
                    sleep_time = min(backoff + jitter, max_backoff)
                    
                    logger.info(f"Backing off for {sleep_time:.2f}s")
                    time.sleep(sleep_time)
                    
                    # Exponential backoff
                    backoff = min(backoff * 2, max_backoff)
        return wrapper
    return decorator

def sanitize_float(value):
    """Convert special float values (inf, -inf, NaN) to None."""
    if isinstance(value, float) and (value == float('inf') or value == float('-inf') or value != value):
        return None
    return value

def sanitize_dict(data):
    """Clean dictionary data for JSON serialization by handling special float values."""
    if isinstance(data, dict):
        return {k: sanitize_dict(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_dict(v) for v in data]
    elif isinstance(data, float):
        return sanitize_float(data)
    return data

def generate_event_key(ticker: str, price: float, event_type: str, 
                      timestamp=None, price_fallback: str = "0.00") -> str:
    """
    Generate a unique key for event deduplication.
    
    Args:
        ticker: Stock ticker symbol
        price: Event price
        event_type: Type of event (high/low)
        timestamp: Optional timestamp
        price_fallback: Fallback value if price is None
        
    Returns:
        Unique event key string
    """
    formatted_price = f"{float(price):.2f}" if price else price_fallback
    
    if timestamp:
        time_part = timestamp.strftime("%H%M%S")
        return f"{ticker}_{formatted_price}_{event_type}_{time_part}"
    
    return f"{ticker}_{formatted_price}_{event_type}"