# Sprint 5: Prescriptive Coding Standards

**Sprint:** Sprint 5 - Core Pattern Library & Event Publisher  
**Phase:** Pre-Sprint Foundation (Complete Before Day 1)  
**Purpose:** Prescriptive coding patterns for clean, manageable Sprint 5 implementation  
**Last Updated:** 2025-08-25

## Overview

This document provides specific, prescriptive coding standards for Sprint 5 pattern library implementation. These standards ensure consistent, maintainable code that follows TickStock principles while establishing clean architectural patterns for future sprints.

## Pattern Module Architecture

### Base Pattern Class Standard

**File:** `src/patterns/base.py`

```python
"""Base pattern class for all TickStock pattern implementations."""
from abc import ABC, abstractmethod
import pandas as pd
from typing import Dict, Any, Optional, Union
from pydantic import BaseModel, Field, validator

class PatternParams(BaseModel):
    """Base parameter model for pattern configuration."""
    timeframe: str = Field(default='daily', regex=r'^(1min|5min|15min|30min|1H|4H|daily)$')
    
    @validator('timeframe')
    def validate_timeframe(cls, v):
        valid_timeframes = ['1min', '5min', '15min', '30min', '1H', '4H', 'daily']
        if v not in valid_timeframes:
            raise ValueError(f'Timeframe must be one of: {valid_timeframes}')
        return v

class BasePattern(ABC):
    """
    Abstract base class for all pattern implementations.
    
    Enforces consistent interface and parameter handling across all patterns.
    Supports multi-timeframe detection with parameter validation.
    """
    
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """
        Initialize pattern with validated parameters.
        
        Args:
            params: Dictionary of pattern-specific parameters
            
        Raises:
            ValueError: If parameters fail validation
        """
        self.params = self._validate_and_parse_params(params or {})
        self.pattern_name = self.__class__.__name__
        self.timeframe = self.params.timeframe
    
    @abstractmethod
    def detect(self, data: pd.DataFrame) -> pd.Series:
        """
        Detect pattern occurrences in OHLCV data.
        
        Args:
            data: DataFrame with columns ['timestamp', 'open', 'high', 'low', 'close', 'volume']
                 Indexed by timestamp, sorted ascending
                 
        Returns:
            Boolean Series indexed by timestamp indicating pattern detection
            
        Raises:
            ValueError: If data format is invalid
            PatternDetectionError: If detection logic fails
        """
        pass
    
    def _validate_and_parse_params(self, params: Dict[str, Any]) -> PatternParams:
        """
        Validate and parse pattern parameters using Pydantic.
        
        Args:
            params: Raw parameter dictionary
            
        Returns:
            Validated PatternParams instance
            
        Raises:
            ValueError: If parameter validation fails
        """
        try:
            return PatternParams(**params)
        except Exception as e:
            raise ValueError(f"Parameter validation failed for {self.__class__.__name__}: {e}")
    
    def _validate_data_format(self, data: pd.DataFrame) -> None:
        """
        Validate OHLCV data format and structure.
        
        Args:
            data: Input DataFrame to validate
            
        Raises:
            ValueError: If data format is invalid
        """
        required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in data.columns]
        
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        if data.empty:
            raise ValueError("Input data is empty")
        
        if not pd.api.types.is_datetime64_any_dtype(data['timestamp']):
            raise ValueError("Timestamp column must be datetime type")
    
    def get_event_metadata(self, symbol: str, timestamp: str, price: float, **kwargs) -> Dict[str, Any]:
        """
        Generate standardized event metadata for pattern detection.
        
        Args:
            symbol: Stock symbol (e.g., "AAPL")
            timestamp: Detection timestamp (ISO format)
            price: Detection price
            **kwargs: Additional pattern-specific metadata
            
        Returns:
            Standardized event metadata dictionary
        """
        return {
            'pattern': self.pattern_name,
            'symbol': symbol,
            'timestamp': timestamp,
            'price': price,
            'timeframe': self.timeframe,
            'metadata': {
                'params': self.params.dict(),
                **kwargs
            }
        }
```

### Candlestick Pattern Implementation Standard

**File:** `src/patterns/candlestick.py`

```python
"""Candlestick pattern implementations following TickStock standards."""
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from pydantic import Field, validator

from .base import BasePattern, PatternParams
from ..exceptions import PatternDetectionError

class CandlestickParams(PatternParams):
    """Base parameters for candlestick patterns."""
    pass

class DojiParams(CandlestickParams):
    """Parameters for Doji pattern detection."""
    tolerance: float = Field(default=0.01, ge=0.001, le=0.1)
    
    @validator('tolerance')
    def validate_tolerance(cls, v):
        if not 0.001 <= v <= 0.1:
            raise ValueError('Tolerance must be between 0.001 and 0.1')
        return v

class DojiPattern(BasePattern):
    """
    Doji candlestick pattern detector.
    
    Detects neutral reversal patterns where open ≈ close within tolerance,
    indicating market indecision. Commonly precedes trend reversals.
    
    Pattern Criteria:
    - Body size (|close - open|) <= tolerance * candle range (high - low)
    - Minimum candle range to avoid false positives on flat periods
    
    Event Output:
    {"pattern": "DojiPattern", "symbol": "AAPL", "timestamp": "...", 
     "price": close, "timeframe": "1min", "direction": "neutral"}
    """
    
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """Initialize Doji pattern with validated parameters."""
        super().__init__(params)
        # Override base params with Doji-specific validation
        self.params = DojiParams(**params) if params else DojiParams()
    
    def detect(self, data: pd.DataFrame) -> pd.Series:
        """
        Detect Doji patterns in OHLCV data.
        
        Args:
            data: OHLCV DataFrame with required columns
            
        Returns:
            Boolean Series indicating Doji detection at each timestamp
            
        Raises:
            PatternDetectionError: If detection logic encounters errors
        """
        try:
            self._validate_data_format(data)
            
            # Calculate pattern components with vectorized operations
            body = np.abs(data['close'] - data['open'])
            candle_range = data['high'] - data['low']
            
            # Avoid division by zero - set minimum range threshold
            min_range_threshold = 0.01  # $0.01 minimum range
            valid_range = candle_range >= min_range_threshold
            
            # Apply Doji criteria: body <= tolerance * range
            tolerance_threshold = self.params.tolerance * candle_range
            is_doji = (body <= tolerance_threshold) & valid_range
            
            return pd.Series(is_doji, index=data.index, name='doji_detected')
            
        except Exception as e:
            raise PatternDetectionError(f"Doji detection failed: {e}")
    
    def get_event_metadata(self, symbol: str, timestamp: str, price: float, **kwargs) -> Dict[str, Any]:
        """Generate Doji-specific event metadata."""
        base_metadata = super().get_event_metadata(symbol, timestamp, price, **kwargs)
        base_metadata.update({
            'direction': 'neutral',
            'signal_strength': kwargs.get('signal_strength', 'medium')
        })
        return base_metadata

# Utility functions for candlestick calculations
def calculate_body_size(data: pd.DataFrame) -> pd.Series:
    """Calculate candlestick body size."""
    return np.abs(data['close'] - data['open'])

def calculate_upper_shadow(data: pd.DataFrame) -> pd.Series:
    """Calculate upper shadow length."""
    return data['high'] - np.maximum(data['open'], data['close'])

def calculate_lower_shadow(data: pd.DataFrame) -> pd.Series:
    """Calculate lower shadow length."""
    return np.minimum(data['open'], data['close']) - data['low']

def calculate_candle_range(data: pd.DataFrame) -> pd.Series:
    """Calculate total candle range (high - low)."""
    return data['high'] - data['low']
```

## Event Publishing Architecture

### EventPublisher Standard

**File:** `src/analysis/events.py`

```python
"""Event publishing system for pattern detection results."""
import json
import logging
import redis
from typing import Dict, Any, Optional, Protocol
from contextlib import contextmanager
from datetime import datetime

from ..exceptions import EventPublishingError

# Protocol for event publishers (enables dependency injection)
class EventPublisher(Protocol):
    """Protocol defining event publisher interface."""
    
    def publish(self, event: Dict[str, Any]) -> bool:
        """Publish event and return success status."""
        ...
    
    def close(self) -> None:
        """Clean up publisher resources."""
        ...

class RedisEventPublisher:
    """
    Redis-based event publisher for pattern detection events.
    
    Publishes JSON events to Redis pub-sub channel with fallback logging.
    Handles connection failures gracefully with exponential backoff retry.
    """
    
    CHANNEL_NAME = "tickstock_patterns"
    MAX_RETRIES = 3
    RETRY_BACKOFF = 1.5  # Exponential backoff multiplier
    
    def __init__(self, redis_url: str = "redis://localhost:6379", logger: Optional[logging.Logger] = None):
        """
        Initialize Redis event publisher.
        
        Args:
            redis_url: Redis connection URL
            logger: Optional logger instance (creates default if None)
            
        Raises:
            EventPublishingError: If Redis connection fails during initialization
        """
        self.redis_url = redis_url
        self.logger = logger or logging.getLogger(__name__)
        self._redis_client: Optional[redis.Redis] = None
        self._connect()
    
    def _connect(self) -> None:
        """Establish Redis connection with error handling."""
        try:
            self._redis_client = redis.Redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            # Test connection
            self._redis_client.ping()
            self.logger.info(f"Connected to Redis at {self.redis_url}")
            
        except redis.ConnectionError as e:
            self.logger.error(f"Failed to connect to Redis: {e}")
            self._redis_client = None
            # Don't raise - allow fallback to console logging
    
    @contextmanager
    def _redis_operation(self):
        """Context manager for Redis operations with retry logic."""
        last_exception = None
        
        for attempt in range(self.MAX_RETRIES):
            try:
                if self._redis_client is None:
                    self._connect()
                
                if self._redis_client is not None:
                    yield self._redis_client
                    return
                    
            except redis.ConnectionError as e:
                last_exception = e
                self.logger.warning(f"Redis operation failed (attempt {attempt + 1}): {e}")
                self._redis_client = None
                
                if attempt < self.MAX_RETRIES - 1:
                    import time
                    time.sleep(self.RETRY_BACKOFF ** attempt)
        
        # All retries failed
        if last_exception:
            raise EventPublishingError(f"Redis operation failed after {self.MAX_RETRIES} attempts: {last_exception}")
    
    def publish(self, event: Dict[str, Any]) -> bool:
        """
        Publish event to Redis channel with fallback logging.
        
        Args:
            event: Event dictionary to publish
            
        Returns:
            True if successfully published, False if fell back to logging
            
        Raises:
            EventPublishingError: If event serialization fails
        """
        try:
            # Validate and serialize event
            event_json = self._serialize_event(event)
            
            # Attempt Redis publish
            try:
                with self._redis_operation() as redis_client:
                    subscribers = redis_client.publish(self.CHANNEL_NAME, event_json)
                    self.logger.debug(f"Published event to {subscribers} subscribers: {event['pattern']}")
                    return True
                    
            except EventPublishingError:
                # Fallback to console logging
                self._fallback_log_event(event)
                return False
                
        except Exception as e:
            raise EventPublishingError(f"Event publishing failed: {e}")
    
    def _serialize_event(self, event: Dict[str, Any]) -> str:
        """
        Serialize event to JSON with validation.
        
        Args:
            event: Event dictionary to serialize
            
        Returns:
            JSON string representation
            
        Raises:
            EventPublishingError: If serialization fails or required fields missing
        """
        required_fields = ['pattern', 'symbol', 'timestamp', 'price']
        missing_fields = [field for field in required_fields if field not in event]
        
        if missing_fields:
            raise EventPublishingError(f"Event missing required fields: {missing_fields}")
        
        try:
            # Add publishing metadata
            enriched_event = {
                **event,
                'published_at': datetime.utcnow().isoformat(),
                'publisher_version': '1.0.0'
            }
            return json.dumps(enriched_event, ensure_ascii=False)
            
        except (TypeError, ValueError) as e:
            raise EventPublishingError(f"Event serialization failed: {e}")
    
    def _fallback_log_event(self, event: Dict[str, Any]) -> None:
        """Log event to console when Redis is unavailable."""
        self.logger.info(f"EVENT (fallback): {event['pattern']} - {event['symbol']} @ {event['timestamp']}")
    
    def close(self) -> None:
        """Close Redis connection and clean up resources."""
        if self._redis_client:
            try:
                self._redis_client.close()
                self.logger.info("Redis connection closed")
            except Exception as e:
                self.logger.warning(f"Error closing Redis connection: {e}")
            finally:
                self._redis_client = None

class ConsoleEventPublisher:
    """Console-only event publisher for development/testing."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
    
    def publish(self, event: Dict[str, Any]) -> bool:
        """Log event to console."""
        self.logger.info(f"PATTERN EVENT: {event}")
        return True
    
    def close(self) -> None:
        """No-op for console publisher."""
        pass

# Factory function for dependency injection
def create_event_publisher(redis_url: Optional[str] = None) -> EventPublisher:
    """
    Create appropriate event publisher based on configuration.
    
    Args:
        redis_url: Redis URL (None for console-only publisher)
        
    Returns:
        EventPublisher implementation
    """
    if redis_url:
        return RedisEventPublisher(redis_url)
    else:
        return ConsoleEventPublisher()
```

## Pattern Scanner Architecture

### PatternScanner Standard

**File:** `src/analysis/scanner.py`

```python
"""Pattern scanner for batch and real-time pattern detection."""
import pandas as pd
import logging
from typing import Dict, List, Type, Any, Optional, Callable
from datetime import datetime

from ..patterns.base import BasePattern
from .events import EventPublisher, create_event_publisher
from ..exceptions import PatternScanningError

class PatternScanner:
    """
    Extensible pattern scanner supporting multiple patterns and event publishing.
    
    Manages pattern registration, batch scanning, and event publishing with
    performance monitoring and error handling.
    """
    
    def __init__(self, event_publisher: Optional[EventPublisher] = None, logger: Optional[logging.Logger] = None):
        """
        Initialize pattern scanner.
        
        Args:
            event_publisher: Event publisher instance (creates default if None)
            logger: Logger instance (creates default if None)
        """
        self.event_publisher = event_publisher or create_event_publisher()
        self.logger = logger or logging.getLogger(__name__)
        self._registered_patterns: Dict[str, BasePattern] = {}
        self._pattern_stats: Dict[str, Dict[str, int]] = {}
    
    def add_pattern(self, pattern_class: Type[BasePattern], params: Optional[Dict[str, Any]] = None, name: Optional[str] = None) -> str:
        """
        Register pattern for scanning with optional custom parameters.
        
        Args:
            pattern_class: Pattern class to instantiate
            params: Optional parameters for pattern initialization
            name: Optional custom name (uses class name if None)
            
        Returns:
            Pattern registration name
            
        Raises:
            PatternScanningError: If pattern registration fails
        """
        try:
            pattern_instance = pattern_class(params)
            registration_name = name or pattern_class.__name__
            
            self._registered_patterns[registration_name] = pattern_instance
            self._pattern_stats[registration_name] = {'detections': 0, 'scans': 0, 'errors': 0}
            
            self.logger.info(f"Registered pattern: {registration_name} with params: {params}")
            return registration_name
            
        except Exception as e:
            raise PatternScanningError(f"Failed to register pattern {pattern_class.__name__}: {e}")
    
    def remove_pattern(self, name: str) -> bool:
        """Remove registered pattern by name."""
        if name in self._registered_patterns:
            del self._registered_patterns[name]
            del self._pattern_stats[name]
            self.logger.info(f"Removed pattern: {name}")
            return True
        return False
    
    def scan(self, data: pd.DataFrame, symbol: str, publish_events: bool = True) -> Dict[str, pd.Series]:
        """
        Scan data for all registered patterns.
        
        Args:
            data: OHLCV DataFrame to scan
            symbol: Stock symbol for event metadata
            publish_events: Whether to publish detection events
            
        Returns:
            Dictionary mapping pattern names to detection Series
            
        Raises:
            PatternScanningError: If scanning fails
        """
        if not self._registered_patterns:
            self.logger.warning("No patterns registered for scanning")
            return {}
        
        results = {}
        scan_start = datetime.utcnow()
        
        try:
            for pattern_name, pattern_instance in self._registered_patterns.items():
                try:
                    # Run pattern detection
                    detection_start = datetime.utcnow()
                    detections = pattern_instance.detect(data)
                    detection_time = (datetime.utcnow() - detection_start).total_seconds() * 1000
                    
                    # Update statistics
                    self._pattern_stats[pattern_name]['scans'] += 1
                    detection_count = detections.sum()
                    self._pattern_stats[pattern_name]['detections'] += detection_count
                    
                    results[pattern_name] = detections
                    
                    # Publish events if requested and detections found
                    if publish_events and detection_count > 0:
                        self._publish_pattern_events(pattern_instance, detections, data, symbol)
                    
                    self.logger.debug(f"Pattern {pattern_name}: {detection_count} detections in {detection_time:.2f}ms")
                    
                except Exception as e:
                    self._pattern_stats[pattern_name]['errors'] += 1
                    self.logger.error(f"Pattern {pattern_name} scan failed: {e}")
                    results[pattern_name] = pd.Series(False, index=data.index)
            
            scan_time = (datetime.utcnow() - scan_start).total_seconds() * 1000
            total_detections = sum(series.sum() for series in results.values())
            
            self.logger.info(f"Scanned {len(data)} bars with {len(self._registered_patterns)} patterns: "
                           f"{total_detections} detections in {scan_time:.2f}ms")
            
            return results
            
        except Exception as e:
            raise PatternScanningError(f"Pattern scanning failed: {e}")
    
    def _publish_pattern_events(self, pattern: BasePattern, detections: pd.Series, data: pd.DataFrame, symbol: str) -> None:
        """Publish events for detected patterns."""
        detection_indices = detections[detections].index
        
        for idx in detection_indices:
            try:
                row = data.loc[idx]
                event_data = pattern.get_event_metadata(
                    symbol=symbol,
                    timestamp=row['timestamp'].isoformat(),
                    price=float(row['close']),
                    volume=int(row['volume']),
                    signal_strength=self._calculate_signal_strength(row)
                )
                
                self.event_publisher.publish(event_data)
                
            except Exception as e:
                self.logger.error(f"Failed to publish event for {pattern.pattern_name}: {e}")
    
    def _calculate_signal_strength(self, row: pd.Series) -> str:
        """Calculate signal strength based on volume and price action."""
        # Simple heuristic - can be enhanced in future sprints
        volume = row.get('volume', 0)
        if volume > 50000:
            return 'high'
        elif volume > 20000:
            return 'medium'
        else:
            return 'low'
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get scanning statistics for all registered patterns."""
        return {
            'registered_patterns': len(self._registered_patterns),
            'pattern_stats': self._pattern_stats.copy(),
            'total_scans': sum(stats['scans'] for stats in self._pattern_stats.values()),
            'total_detections': sum(stats['detections'] for stats in self._pattern_stats.values()),
            'total_errors': sum(stats['errors'] for stats in self._pattern_stats.values())
        }
    
    def close(self) -> None:
        """Clean up scanner resources."""
        if self.event_publisher:
            self.event_publisher.close()
        self.logger.info("Pattern scanner closed")
```

## Exception Handling Standards

### Custom Exceptions

**File:** `src/exceptions.py`

```python
"""Custom exceptions for TickStock pattern library."""

class TickStockPatternError(Exception):
    """Base exception for TickStock pattern library errors."""
    pass

class PatternDetectionError(TickStockPatternError):
    """Raised when pattern detection logic fails."""
    
    def __init__(self, pattern_name: str, reason: str, data_info: str = ""):
        self.pattern_name = pattern_name
        self.reason = reason
        self.data_info = data_info
        super().__init__(f"Pattern detection failed for {pattern_name}: {reason} {data_info}")

class EventPublishingError(TickStockPatternError):
    """Raised when event publishing fails."""
    pass

class PatternScanningError(TickStockPatternError):
    """Raised when pattern scanning fails."""
    pass

class DataValidationError(TickStockPatternError):
    """Raised when OHLCV data validation fails."""
    pass
```

## Parameter Validation Standards

### Pydantic Models for Type Safety

```python
"""Parameter models for type-safe pattern configuration."""
from pydantic import BaseModel, Field, validator
from typing import Union, List, Optional
from enum import Enum

class TimeFrame(str, Enum):
    """Supported timeframes for pattern detection."""
    ONE_MIN = "1min"
    FIVE_MIN = "5min" 
    FIFTEEN_MIN = "15min"
    THIRTY_MIN = "30min"
    ONE_HOUR = "1H"
    FOUR_HOUR = "4H"
    DAILY = "daily"

class PatternDirection(str, Enum):
    """Pattern direction indicators."""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"

class BasePatternParams(BaseModel):
    """Base parameters for all patterns."""
    timeframe: TimeFrame = Field(default=TimeFrame.DAILY)
    
    class Config:
        use_enum_values = True
        validate_assignment = True

class CandlestickPatternParams(BasePatternParams):
    """Base parameters for candlestick patterns."""
    min_volume: int = Field(default=1000, ge=0)
    
    @validator('min_volume')
    def validate_min_volume(cls, v):
        if v < 0:
            raise ValueError('Minimum volume must be non-negative')
        return v
```

## Code Quality Standards

### Required Code Patterns

1. **All public methods must have type hints**
2. **All classes must have comprehensive docstrings**  
3. **Use Pydantic for parameter validation**
4. **Implement proper exception handling with custom exceptions**
5. **Log all significant operations with appropriate levels**
6. **Use context managers for resource management**
7. **Validate inputs at method boundaries**
8. **Return structured data (not mixed types)**

### Performance Requirements

1. **Pattern detection must complete in <50ms per pattern**
2. **Use vectorized pandas operations (avoid loops)**
3. **Validate data format once per scan, not per pattern**
4. **Cache expensive calculations where possible**
5. **Use appropriate data types (float64 for prices)**

### Testing Requirements

1. **Each pattern class must have dedicated test file**
2. **Test edge cases: empty data, invalid data, zero ranges**
3. **Test parameter validation with invalid inputs**
4. **Mock external dependencies (Redis, file I/O)**
5. **Benchmark critical paths with pytest-benchmark**

## Import Standards

### Organized Import Structure

```python
"""Module docstring explaining purpose and functionality."""
# Standard library imports (grouped)
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

# Third-party imports (grouped)
import pandas as pd
import numpy as np
import redis
from pydantic import BaseModel, Field

# Local imports (grouped)
from .base import BasePattern
from ..exceptions import PatternDetectionError
from ..utils import calculate_technical_indicators
```

## Documentation Standards

### Class Documentation Template

```python
class PatternName(BasePattern):
    """
    Brief one-line description of pattern.
    
    Detailed description of what the pattern detects, market conditions,
    and trading significance. Include references to user stories.
    
    Pattern Criteria:
    - Specific mathematical conditions for detection
    - Minimum data requirements
    - Edge case handling approach
    
    Example:
        >>> pattern = PatternName({'tolerance': 0.02})
        >>> detections = pattern.detect(ohlcv_data)
        >>> assert detections.dtype == bool
    
    Attributes:
        params: Validated pattern parameters
        pattern_name: String identifier for events
        
    Raises:
        PatternDetectionError: If detection logic fails
        ValueError: If parameters are invalid
    """
```

This prescriptive coding standard ensures Sprint 5 produces consistent, maintainable, and extensible code that follows TickStock principles while establishing clean architectural foundations for future development.