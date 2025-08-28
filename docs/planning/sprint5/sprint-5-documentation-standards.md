# Sprint 5: Documentation Standards

**Sprint:** Sprint 5 - Core Pattern Library & Event Publisher  
**Phase:** Pre-Sprint Foundation (Complete Before Day 1)  
**Purpose:** Clear, low-clutter documentation standards for executable implementation  
**Last Updated:** 2025-08-25

## Overview

This document establishes documentation standards for Sprint 5 that prioritize clarity, executability, and low clutter. Documentation must enable you, me, and future developers to clearly understand and execute implementation without ambiguity.

## Core Documentation Principles

### 1. Executable Documentation
- **Code Examples Must Work:** All code examples must be runnable without modification
- **Complete Examples:** Show full context, not just fragments
- **Testable Examples:** Include assertions or expected outputs where applicable

### 2. Low-Clutter Clarity
- **Essential Information Only:** Include only what's needed for execution
- **Structured Hierarchy:** Use consistent heading structure for navigation
- **Visual Separation:** Clear separation between concepts using formatting

### 3. Developer-Centric
- **Assumption Documentation:** Clearly state what we assume vs. what we verify
- **Error Scenarios:** Document failure modes and troubleshooting steps
- **Integration Points:** Clear interfaces between components

## Code Documentation Standards

### Class Documentation Template

```python
class DojiPattern(BasePattern):
    """
    Doji candlestick pattern detector for market indecision signals.
    
    Detects neutral reversal patterns where open ≈ close within tolerance.
    Commonly precedes trend reversals in volatile markets.
    
    Usage:
        >>> pattern = DojiPattern({'tolerance': 0.01})
        >>> detections = pattern.detect(ohlcv_data)
        >>> event_count = detections.sum()
    
    Parameters:
        tolerance (float): Max body size as % of candle range (0.001-0.1)
        timeframe (str): Target timeframe ('1min', 'daily', etc.)
    
    Returns:
        Boolean Series indexed by timestamp indicating detections
        
    Raises:
        ValueError: Invalid parameters or data format
        PatternDetectionError: Detection logic failure
    """
```

### Function Documentation Template

```python
def detect(self, data: pd.DataFrame) -> pd.Series:
    """
    Detect Doji patterns in OHLCV data using vectorized operations.
    
    Algorithm:
        1. Calculate body = |close - open|
        2. Calculate range = high - low  
        3. Apply criteria: body <= tolerance * range
        4. Filter out zero-range candles
    
    Args:
        data: DataFrame with columns ['timestamp', 'open', 'high', 'low', 'close', 'volume']
              Must be sorted by timestamp ascending
              
    Returns:
        Boolean Series with same index as input data
        True indicates Doji pattern detected
        
    Example:
        >>> data = pd.DataFrame({
        ...     'timestamp': pd.date_range('2025-01-01', periods=3, freq='1min'),
        ...     'open': [100.0, 101.0, 102.0],
        ...     'high': [100.5, 101.5, 102.5], 
        ...     'low': [99.5, 100.5, 101.5],
        ...     'close': [100.1, 101.0, 101.9],  # Second candle is Doji
        ...     'volume': [1000, 1000, 1000]
        ... })
        >>> pattern = DojiPattern({'tolerance': 0.02})
        >>> result = pattern.detect(data)
        >>> assert result.iloc[1] == True  # Doji detected
        >>> assert result.sum() == 1       # Only one detection
    """
```

### Module Documentation Template

```python
"""
TickStock candlestick pattern implementations.

This module provides concrete implementations of candlestick patterns
following the BasePattern interface. All patterns support multi-timeframe
detection with parameter validation.

Available Patterns:
    - DojiPattern: Neutral reversal (open ≈ close)
    - HammerPattern: Bullish reversal (long lower shadow)
    - [Future patterns in Sprint 7]

Integration:
    >>> from src.patterns.candlestick import DojiPattern
    >>> from src.analysis.scanner import PatternScanner
    >>> 
    >>> scanner = PatternScanner()
    >>> scanner.add_pattern(DojiPattern, {'tolerance': 0.01})
    >>> results = scanner.scan(ohlcv_data, symbol='AAPL')

Dependencies:
    - pandas>=2.0.0: DataFrame operations
    - numpy>=1.24.0: Vectorized calculations  
    - pydantic>=2.0.0: Parameter validation
"""
```

## API Documentation Standards

### Event Structure Documentation

```python
# Event JSON Schema (Published to Redis 'tickstock_patterns' channel)
{
    "pattern": str,           # Pattern class name (e.g., "DojiPattern")
    "symbol": str,            # Stock symbol (e.g., "AAPL") 
    "timestamp": str,         # ISO format: "2025-08-25T14:30:00Z"
    "price": float,           # Detection price (close price)
    "timeframe": str,         # Detection timeframe ("1min", "daily")
    "direction": str,         # "bullish", "bearish", "neutral"
    "metadata": {             # Pattern-specific details
        "params": {},         # Pattern parameters used
        "signal_strength": str, # "low", "medium", "high"
        "volume": int,        # Volume at detection
        "candle_range": float # Optional: candle high-low range
    },
    "published_at": str,      # Publisher timestamp (ISO format)
    "publisher_version": str  # Version for compatibility tracking
}

# Example Doji Event:
{
    "pattern": "DojiPattern",
    "symbol": "AAPL",
    "timestamp": "2025-08-25T14:30:00Z", 
    "price": 150.25,
    "timeframe": "1min",
    "direction": "neutral",
    "metadata": {
        "params": {"tolerance": 0.01, "timeframe": "1min"},
        "signal_strength": "medium",
        "volume": 15000,
        "candle_range": 2.50,
        "body_size": 0.15
    },
    "published_at": "2025-08-25T14:30:05.123Z",
    "publisher_version": "1.0.0"
}
```

### Interface Documentation

```python
# PatternScanner Interface
class PatternScanner:
    """
    Multi-pattern scanner with event publishing.
    
    Registration:
        scanner.add_pattern(PatternClass, params_dict, optional_name)
        
    Scanning:
        results = scanner.scan(dataframe, symbol, publish_events=True)
        
    Results Format:
        {
            "DojiPattern": pd.Series([False, True, False, ...]),
            "HammerPattern": pd.Series([False, False, True, ...])
        }
    """
    
    def add_pattern(self, pattern_class: Type[BasePattern], 
                   params: Dict[str, Any] = None, 
                   name: str = None) -> str:
        """Register pattern for scanning."""
        pass
    
    def scan(self, data: pd.DataFrame, symbol: str, 
             publish_events: bool = True) -> Dict[str, pd.Series]:
        """Scan data with all registered patterns."""
        pass
```

## Testing Documentation Standards

### Test Documentation Template

```python
class TestDojiPattern:
    """
    Test suite for Doji pattern detection.
    
    Test Categories:
        - Parameter validation (invalid inputs)
        - Data format validation (missing columns, empty data)
        - Detection accuracy (known patterns)
        - Edge cases (zero range, flat markets)
        - Performance (benchmark <50ms requirement)
    """
    
    def test_valid_doji_detection(self, sample_doji_data):
        """
        Test detection of valid Doji pattern in sample data.
        
        Given: OHLCV data with known Doji at timestamp index 1
        When: DojiPattern.detect() is called with default parameters
        Then: Returns True only for the Doji candle
        """
        # Arrange
        pattern = DojiPattern()
        
        # Act  
        results = pattern.detect(sample_doji_data)
        
        # Assert
        assert results.iloc[1] == True, "Should detect Doji at index 1"
        assert results.sum() == 1, "Should detect exactly one Doji"
        assert results.dtype == bool, "Should return boolean Series"
```

### Fixture Documentation

```python
@pytest.fixture
def sample_doji_data():
    """
    Generate OHLCV DataFrame with clear Doji pattern at index 1.
    
    Data Structure:
        - 3 candles (indices 0, 1, 2)
        - Index 1 contains Doji: open=100.0, close=100.05 (small body)
        - Range at index 1: high=101.0, low=99.0 (sufficient range)
        - Body/range ratio: 0.05/2.0 = 0.025 (< default tolerance 0.01)
    
    Returns:
        pd.DataFrame with columns ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    """
    return pd.DataFrame({
        'timestamp': pd.date_range('2025-01-01 09:30', periods=3, freq='1min'),
        'open':      [99.5,  100.0, 101.0],
        'high':      [99.8,  101.0, 101.5], 
        'low':       [99.2,   99.0, 100.5],
        'close':     [100.0, 100.05, 101.2],  # Index 1 is Doji
        'volume':    [10000, 15000, 12000]
    })
```

## README Documentation Standards

### Project README Template

```markdown
# TickStock Pattern Library - Sprint 5

Core pattern detection library with Redis event publishing.

## Quick Start

```bash
# Setup environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
pip install -r requirements.txt

# Start Redis (Docker)
docker run -d --name tickstock-redis -p 6379:6379 redis:7-alpine

# Run basic pattern detection
python examples/basic_pattern_demo.py
```

## Usage

```python
from src.patterns.candlestick import DojiPattern
from src.analysis.scanner import PatternScanner

# Create scanner with event publishing
scanner = PatternScanner()
scanner.add_pattern(DojiPattern, {'tolerance': 0.01})

# Scan data and publish events
results = scanner.scan(ohlcv_data, symbol='AAPL')
print(f"Detected {results['DojiPattern'].sum()} Doji patterns")
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific pattern tests  
pytest tests/unit/patterns/test_doji.py -v
```

## Architecture

- `src/patterns/`: Pattern implementations
- `src/analysis/`: Scanner and event publishing
- `tests/`: Comprehensive test suite
- `examples/`: Demo scripts and usage examples
```

## Integration Documentation Standards

### Redis Integration Documentation

```markdown
# Redis Event Integration

## Channel Configuration
- **Channel Name:** `tickstock_patterns`
- **Message Format:** JSON (UTF-8 encoded)
- **Connection:** Redis URL via environment variable `REDIS_URL`

## Event Publishing Flow
1. Pattern detected in scanner
2. Event metadata generated with pattern.get_event_metadata()
3. JSON serialization with validation
4. Redis PUBLISH to 'tickstock_patterns' channel
5. Fallback to console logging if Redis unavailable

## Consumer Integration (TickStockApp)
```python
import redis
import json

r = redis.Redis(host='localhost', port=6379, decode_responses=True)
pubsub = r.pubsub()
pubsub.subscribe('tickstock_patterns')

for message in pubsub.listen():
    if message['type'] == 'message':
        event = json.loads(message['data'])
        print(f"Pattern: {event['pattern']} - {event['symbol']}")
```

## Error Handling
- **Connection Failures:** Exponential backoff retry (3 attempts)
- **Serialization Errors:** EventPublishingError raised
- **Fallback Mode:** Console logging when Redis unavailable
```

## Performance Documentation Standards

### Benchmarking Documentation

```python
def test_doji_detection_performance(benchmark, large_ohlcv_dataset):
    """
    Benchmark Doji pattern detection performance.
    
    Requirements:
        - Must complete in <50ms for 1000 candles
        - Memory usage should be reasonable (<100MB)
        - Vectorized operations only (no Python loops)
    
    Test Data:
        - 1000 1-minute candles (typical trading day)
        - Realistic price/volume distribution  
        - Mix of pattern occurrences (~2-5% detection rate)
    """
    pattern = DojiPattern()
    
    # Benchmark the detection
    result = benchmark(pattern.detect, large_ohlcv_dataset)
    
    # Verify performance requirements
    assert benchmark.stats['mean'] < 0.05, "Detection must complete in <50ms"
    assert result.sum() > 0, "Should detect some patterns in realistic data"
```

## Error Documentation Standards

### Exception Documentation

```python
class PatternDetectionError(TickStockPatternError):
    """
    Raised when pattern detection logic encounters unrecoverable errors.
    
    Common Causes:
        - Malformed OHLCV data (missing columns, wrong types)
        - Mathematical errors (division by zero, invalid calculations)
        - Memory/performance issues with large datasets
    
    Recovery Actions:
        - Validate input data format before detection
        - Check for empty/null data conditions
        - Monitor memory usage for large datasets
        
    Example:
        try:
            detections = pattern.detect(data)
        except PatternDetectionError as e:
            logger.error(f"Detection failed: {e}")
            # Return empty results or fallback logic
            detections = pd.Series(False, index=data.index)
    """
```

## Sprint-Specific Documentation Requirements

### Daily Progress Documentation

Each implementation day should update:

1. **Implementation Log** (`docs/sprint-5-implementation-log.md`):
   - What was completed
   - Issues encountered and resolved
   - Performance metrics achieved
   - Next day priorities

2. **API Changes** (`docs/sprint-5-api-changes.md`):
   - Interface modifications
   - Breaking changes
   - Migration notes

3. **Testing Results** (`docs/sprint-5-testing-results.md`):
   - Coverage reports
   - Performance benchmarks
   - Failed test analysis

### Completion Documentation

Sprint 5 completion requires:

1. **Implementation Summary** with working examples
2. **Performance Report** with benchmark results
3. **Integration Guide** for Sprint 6 handoff
4. **Known Issues** and recommended fixes

## Documentation Quality Checklist

**Before committing documentation:**
- [ ] All code examples are executable without modification
- [ ] Examples include expected outputs or assertions
- [ ] Error scenarios are documented with recovery actions
- [ ] Interface contracts are clearly specified
- [ ] Performance requirements are stated and testable
- [ ] Integration points are documented with examples
- [ ] Troubleshooting information is provided

**Documentation Success Criteria:**
- Any developer can execute examples without clarification
- Integration interfaces are unambiguous
- Error handling is predictable and documented
- Performance expectations are clear and measurable

This documentation standard ensures Sprint 5 produces clear, executable documentation that supports immediate implementation and long-term maintainability.