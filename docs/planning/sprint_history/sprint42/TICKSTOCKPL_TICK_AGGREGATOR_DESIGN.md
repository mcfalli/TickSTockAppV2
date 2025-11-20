# TickStockPL: TickAggregator Implementation Design

**Replaces**: `C:\Users\McDude\TickStockPL\docs\planning\sprints\sprint42\TICK_AGGREGATOR_MISSING.md`

**Date**: October 10, 2025
**Sprint**: Sprint 42 - Architectural Realignment
**Status**: 🎯 READY FOR IMPLEMENTATION
**Priority**: P0 - Blocks streaming pattern detection

---

## Executive Summary

**Architectural Decision**: TickStockPL will own ALL OHLCV aggregation logic as the single source of truth, enforcing the documented producer/consumer separation with TickStockAppV2.

**Key Changes from Original Finding**:
1. ✅ **CORRECT**: TickStockPL needs TickAggregator component
2. ✅ **CORRECT**: Missing aggregation blocks pattern detection
3. ✅ **CORRECT**: StreamingPersistenceManager notification system exists but unused
4. ⚠️ **ADDITIONAL CONTEXT**: TickStockAppV2 currently performs aggregation (will be removed in Phase 2)
5. ✅ **CLARIFIED**: This establishes TickStockPL as sole aggregation owner

**Implementation Approach**: Implement TickAggregator in TickStockPL first, then remove duplicate aggregation from TickStockAppV2 once validated.

---

## Problem Statement (Clarified)

### Current State

**TickStockAppV2** (INCORRECT - Violates Architecture):
- ✅ Receives ticks from Polygon/Synthetic sources
- ✅ Forwards raw ticks to Redis `tickstock:market:ticks`
- ❌ **ALSO** aggregates ticks via `OHLCVPersistenceService`
- ❌ **ALSO** writes directly to `ohlcv_1min` table
- ❌ Violates documented "read-only database" and "consumer-only" role

**TickStockPL** (INCOMPLETE):
- ✅ Consumes ticks from Redis `tickstock:market:ticks`
- ❌ No tick aggregation (MISSING COMPONENT)
- ❌ Attempts pattern detection on individual ticks (impossible)
- ✅ Streaming infrastructure exists but not connected

**Result**: Duplicate/missing aggregation creates architectural violations and blocks pattern detection.

---

## Architecture Analysis (Corrected)

### Desired (Correct) Flow

```
[Polygon/Synthetic Data]
    ↓
[TickStockAppV2: Raw Forwarder ONLY]
    └─→ Publishes raw ticks to Redis 'tickstock:market:ticks' ✅
        (NO aggregation, NO database writes)

[Redis: tickstock:market:ticks]
    ↓
[TickStockPL: RedisTickSubscriber._process_tick()]
    ↓
[🆕 TickAggregator] ← NEW COMPONENT
    ├─ Aggregates ticks into 1-minute OHLCV bars
    ├─ Detects minute boundaries
    └─ On minute complete:
        ↓
    StreamingPersistenceManager.add_minute_bar(ohlcv_data)
        ↓
    _notify_minute_bar_subscribers() ← ALREADY EXISTS
        ↓
    ┌─────────────────────────────────┐
    │ StreamingPatternJob             │ ← ALREADY SUBSCRIBED
    │ .process_minute_bar_sequentially│
    │   ├─ Runs pattern detection     │
    │   └─ Stores in intraday_patterns│
    └─────────────────────────────────┘
        ↓
    ┌─────────────────────────────────┐
    │ StreamingIndicatorJob           │ ← ALREADY SUBSCRIBED
    │ .process_minute_bar_sequentially│
    │   ├─ Calculates indicators      │
    │   └─ Stores in intraday_indicators│
    └─────────────────────────────────┘
```

### Key Architectural Principles

1. **Single Source of Truth**: TickStockPL is the ONLY system that aggregates ticks → OHLCV bars
2. **Producer Role**: TickStockPL owns database writes for pattern/indicator data
3. **Consumer Role**: TickStockAppV2 only forwards raw data and displays results
4. **Loose Coupling**: Redis pub-sub ensures independence
5. **No Duplication**: Only ONE aggregation pipeline exists (in TickStockPL)

---

## Component Specification: TickAggregator

### File Location
```
C:\Users\McDude\TickStockPL\src\streaming\tick_aggregator.py
```

### Class Design

```python
"""
TickAggregator - Aggregates individual ticks into 1-minute OHLCV bars.

Responsibilities:
- Subscribe to tick callbacks from RedisTickSubscriber
- Maintain in-memory state of incomplete bars (per symbol)
- Detect minute boundaries (timestamp floor to minute)
- On minute completion: Create OHLCVData and notify persistence manager
- Handle edge cases: gaps, stale data, symbol transitions

Performance Targets:
- Tick processing: <0.1ms per tick
- Memory usage: <10MB for 100 symbols
- No memory leaks over 24-hour operation
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from dataclasses import dataclass

from src.core.data_types import OHLCVData
from src.streaming.persistence_manager import StreamingPersistenceManager

logger = logging.getLogger(__name__)


@dataclass
class IncompleteBar:
    """Represents an incomplete 1-minute OHLCV bar being built from ticks."""
    symbol: str
    timestamp: datetime  # Minute boundary timestamp (seconds=0, microseconds=0)
    open: float
    high: float
    low: float
    close: float
    volume: int
    tick_count: int = 0  # Number of ticks aggregated

    def update_with_tick(self, price: float, volume: int):
        """Update bar with new tick data."""
        self.high = max(self.high, price)
        self.low = min(self.low, price)
        self.close = price
        self.volume += volume
        self.tick_count += 1


class TickAggregator:
    """
    Aggregates individual tick data into 1-minute OHLCV bars.

    This is the PRIMARY aggregation component in the TickStock architecture.
    All OHLCV data originates from this component.
    """

    def __init__(self, persistence_manager: StreamingPersistenceManager):
        """
        Initialize TickAggregator.

        Args:
            persistence_manager: StreamingPersistenceManager for bar storage
        """
        self.persistence_manager = persistence_manager

        # Current incomplete bars (symbol -> IncompleteBar)
        # Only stores ONE bar per symbol (current incomplete minute)
        self._current_bars: Dict[str, IncompleteBar] = {}

        # Statistics
        self._stats = {
            'ticks_processed': 0,
            'bars_completed': 0,
            'symbols_tracked': 0,
            'errors': 0
        }

        logger.info("TICK-AGGREGATOR: Initialized")

    async def on_tick(self, tick_data: Dict[str, Any]) -> None:
        """
        Process incoming tick and aggregate into minute bars.

        This callback is registered with RedisTickSubscriber.

        Args:
            tick_data: Tick data dictionary with keys:
                - symbol (str): Stock symbol
                - price (float): Current price
                - volume (int): Volume for this tick
                - timestamp (float): Unix timestamp
        """
        try:
            # Extract tick fields
            symbol = tick_data['symbol']
            price = tick_data['price']
            volume = tick_data.get('volume', 0)
            tick_timestamp_unix = tick_data['timestamp']

            # Convert to timezone-aware datetime
            tick_time = datetime.fromtimestamp(tick_timestamp_unix, tz=timezone.utc)

            # Floor to minute boundary (e.g., 14:32:45.123 → 14:32:00.000)
            minute_timestamp = tick_time.replace(second=0, microsecond=0)

            # Get current incomplete bar for this symbol
            current_bar = self._current_bars.get(symbol)

            # Check if we've crossed a minute boundary
            if current_bar and current_bar.timestamp < minute_timestamp:
                # Complete the previous bar
                await self._complete_bar(current_bar)
                current_bar = None  # Start fresh

            # Update or create bar
            if current_bar is None:
                # Start new bar at this minute boundary
                self._current_bars[symbol] = IncompleteBar(
                    symbol=symbol,
                    timestamp=minute_timestamp,
                    open=price,
                    high=price,
                    low=price,
                    close=price,
                    volume=volume,
                    tick_count=1
                )
                self._stats['symbols_tracked'] = len(self._current_bars)
            else:
                # Update existing bar
                current_bar.update_with_tick(price, volume)

            self._stats['ticks_processed'] += 1

            # Log progress periodically
            if self._stats['ticks_processed'] % 1000 == 0:
                logger.info(
                    f"TICK-AGGREGATOR: Processed {self._stats['ticks_processed']} ticks, "
                    f"completed {self._stats['bars_completed']} bars, "
                    f"tracking {self._stats['symbols_tracked']} symbols"
                )

        except Exception as e:
            logger.error(f"TICK-AGGREGATOR: Error processing tick: {e}")
            self._stats['errors'] += 1

    async def _complete_bar(self, bar: IncompleteBar) -> None:
        """
        Complete a bar and notify persistence manager.

        This triggers the entire downstream pipeline:
        - StreamingPersistenceManager stores to database
        - StreamingPatternJob runs pattern detection
        - StreamingIndicatorJob calculates indicators

        Args:
            bar: Completed IncompleteBar
        """
        try:
            # Create OHLCVData instance
            ohlcv_data = OHLCVData(
                symbol=bar.symbol,
                timestamp=bar.timestamp,
                open=bar.open,
                high=bar.high,
                low=bar.low,
                close=bar.close,
                volume=bar.volume,
                timeframe='1min',
                source='tickstockpl_aggregator'
            )

            # 🔥 KEY: Notify persistence manager
            # This triggers _notify_minute_bar_subscribers() which calls:
            # - StreamingPatternJob.process_minute_bar_sequentially()
            # - StreamingIndicatorJob.process_minute_bar_sequentially()
            await self.persistence_manager.add_minute_bar(ohlcv_data)

            self._stats['bars_completed'] += 1

            logger.debug(
                f"TICK-AGGREGATOR: Completed bar for {bar.symbol} at {bar.timestamp} "
                f"(OHLC: {bar.open:.2f}/{bar.high:.2f}/{bar.low:.2f}/{bar.close:.2f}, "
                f"V: {bar.volume}, ticks: {bar.tick_count})"
            )

        except Exception as e:
            logger.error(f"TICK-AGGREGATOR: Error completing bar for {bar.symbol}: {e}")
            self._stats['errors'] += 1

    async def flush_incomplete_bars(self) -> None:
        """
        Flush all incomplete bars (e.g., during shutdown).

        Call this during graceful shutdown to ensure no data loss.
        """
        logger.info(f"TICK-AGGREGATOR: Flushing {len(self._current_bars)} incomplete bars")

        for symbol, bar in list(self._current_bars.items()):
            await self._complete_bar(bar)

        self._current_bars.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get aggregator statistics."""
        return {
            'ticks_processed': self._stats['ticks_processed'],
            'bars_completed': self._stats['bars_completed'],
            'symbols_tracked': self._stats['symbols_tracked'],
            'errors': self._stats['errors'],
            'incomplete_bars': len(self._current_bars)
        }
```

---

## Integration Points

### 1. RedisTickSubscriber Integration

**File**: `src/streaming/redis_tick_subscriber.py`

**Modification Required**:

```python
class RedisTickSubscriber:
    def __init__(
        self,
        redis_client,
        channel: str,
        persistence_manager: StreamingPersistenceManager,
        tick_aggregator: 'TickAggregator'  # NEW PARAMETER
    ):
        self.redis_client = redis_client
        self.channel = channel
        self.persistence_manager = persistence_manager
        self.tick_aggregator = tick_aggregator  # NEW

        # Register tick callbacks
        self.tick_callbacks = []

        # 🔥 KEY: Register TickAggregator callback
        if self.tick_aggregator:
            self.register_tick_callback(self.tick_aggregator.on_tick)

        # REMOVE: Direct pattern detection (WRONG approach)
        # self.pattern_detector = None  # ❌ Delete this

    async def _process_tick(self, tick_data: Dict[str, Any]):
        """
        Process validated tick data.

        Args:
            tick_data: Validated tick data dict
        """
        # Notify all callbacks (including TickAggregator)
        for callback in self.tick_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(tick_data)
                else:
                    callback(tick_data)
            except Exception as e:
                logger.error(f"STREAMING: Error in tick callback: {e}")

        # REMOVE: Direct pattern detection attempt
        # if self.pattern_detector:  # ❌ DELETE THIS BLOCK
        #     try:
        #         patterns = await self._detect_patterns(...)
        #         ...
```

**Changes**:
- Add `tick_aggregator` parameter to `__init__`
- Register `tick_aggregator.on_tick` as callback
- Remove direct pattern detection logic (lines 118-124)

---

### 2. StreamingScheduler Integration

**File**: `src/services/streaming_scheduler.py`

**Modification Required**:

```python
class StreamingScheduler:
    async def _start_redis_stream(self):
        """Start Redis tick stream consumption."""
        try:
            # Initialize persistence manager (ALREADY EXISTS)
            self.persistence_manager = StreamingPersistenceManager(
                db_config=self.db_config,
                batch_size=self.config.get('STREAMING_BATCH_SIZE', 100),
                flush_interval=self.config.get('STREAMING_FLUSH_INTERVAL', 5.0)
            )

            # 🔥 NEW: Initialize TickAggregator
            from src.streaming.tick_aggregator import TickAggregator
            self.tick_aggregator = TickAggregator(self.persistence_manager)

            # Initialize Redis subscriber WITH aggregator
            self.redis_subscriber = RedisTickSubscriber(
                redis_client=self.redis_client,
                channel=self.redis_tick_channel,
                persistence_manager=self.persistence_manager,
                tick_aggregator=self.tick_aggregator  # NEW PARAMETER
            )

            # Start consuming ticks
            await self.redis_subscriber.start_consuming()

            logger.info("STREAMING-SCHEDULER: Redis stream started with TickAggregator")

        except Exception as e:
            logger.error(f"STREAMING-SCHEDULER: Failed to start Redis stream: {e}")

    async def _stop_redis_stream(self):
        """Stop Redis stream and flush incomplete bars."""
        try:
            # Flush incomplete bars before shutdown
            if self.tick_aggregator:
                await self.tick_aggregator.flush_incomplete_bars()

            # Stop Redis subscriber
            if self.redis_subscriber:
                await self.redis_subscriber.stop_consuming()

            logger.info("STREAMING-SCHEDULER: Redis stream stopped")

        except Exception as e:
            logger.error(f"STREAMING-SCHEDULER: Error stopping Redis stream: {e}")
```

**Changes**:
- Import `TickAggregator`
- Initialize `tick_aggregator` before `RedisTickSubscriber`
- Pass `tick_aggregator` to subscriber
- Flush incomplete bars during shutdown

---

## Testing Strategy

### Unit Tests

**File**: `tests/unit/streaming/test_tick_aggregator.py`

```python
import pytest
from datetime import datetime, timezone
from src.streaming.tick_aggregator import TickAggregator, IncompleteBar
from src.core.data_types import OHLCVData


@pytest.fixture
def mock_persistence_manager():
    """Mock persistence manager."""
    class MockPersistenceManager:
        def __init__(self):
            self.bars_received = []

        async def add_minute_bar(self, ohlcv_data: OHLCVData):
            self.bars_received.append(ohlcv_data)

    return MockPersistenceManager()


@pytest.mark.asyncio
async def test_single_tick_creates_incomplete_bar(mock_persistence_manager):
    """Test that a single tick creates an incomplete bar."""
    aggregator = TickAggregator(mock_persistence_manager)

    tick_data = {
        'symbol': 'AAPL',
        'price': 150.50,
        'volume': 100,
        'timestamp': datetime(2025, 10, 10, 14, 32, 15, tzinfo=timezone.utc).timestamp()
    }

    await aggregator.on_tick(tick_data)

    # Should create incomplete bar at 14:32:00
    assert 'AAPL' in aggregator._current_bars
    bar = aggregator._current_bars['AAPL']
    assert bar.symbol == 'AAPL'
    assert bar.open == 150.50
    assert bar.high == 150.50
    assert bar.low == 150.50
    assert bar.close == 150.50
    assert bar.volume == 100
    assert bar.tick_count == 1
    assert bar.timestamp.second == 0  # Minute boundary


@pytest.mark.asyncio
async def test_multiple_ticks_same_minute_updates_bar(mock_persistence_manager):
    """Test that multiple ticks in same minute update OHLCV correctly."""
    aggregator = TickAggregator(mock_persistence_manager)

    base_time = datetime(2025, 10, 10, 14, 32, 0, tzinfo=timezone.utc)

    ticks = [
        {'symbol': 'AAPL', 'price': 150.00, 'volume': 100, 'timestamp': base_time.timestamp() + 5},
        {'symbol': 'AAPL', 'price': 151.50, 'volume': 200, 'timestamp': base_time.timestamp() + 15},
        {'symbol': 'AAPL', 'price': 149.00, 'volume': 150, 'timestamp': base_time.timestamp() + 25},
        {'symbol': 'AAPL', 'price': 150.75, 'volume': 250, 'timestamp': base_time.timestamp() + 35},
    ]

    for tick in ticks:
        await aggregator.on_tick(tick)

    bar = aggregator._current_bars['AAPL']
    assert bar.open == 150.00  # First tick
    assert bar.high == 151.50  # Max price
    assert bar.low == 149.00   # Min price
    assert bar.close == 150.75 # Last tick
    assert bar.volume == 700   # Sum of volumes
    assert bar.tick_count == 4


@pytest.mark.asyncio
async def test_minute_boundary_completes_bar(mock_persistence_manager):
    """Test that crossing minute boundary completes bar and starts new one."""
    aggregator = TickAggregator(mock_persistence_manager)

    # Ticks in 14:32:xx minute
    tick1 = {
        'symbol': 'AAPL',
        'price': 150.00,
        'volume': 100,
        'timestamp': datetime(2025, 10, 10, 14, 32, 15, tzinfo=timezone.utc).timestamp()
    }

    # Tick in 14:33:xx minute (new minute)
    tick2 = {
        'symbol': 'AAPL',
        'price': 151.00,
        'volume': 200,
        'timestamp': datetime(2025, 10, 10, 14, 33, 5, tzinfo=timezone.utc).timestamp()
    }

    await aggregator.on_tick(tick1)
    await aggregator.on_tick(tick2)

    # First bar should be completed and sent to persistence manager
    assert len(mock_persistence_manager.bars_received) == 1
    completed_bar = mock_persistence_manager.bars_received[0]
    assert completed_bar.symbol == 'AAPL'
    assert completed_bar.close == 150.00
    assert completed_bar.timestamp.hour == 14
    assert completed_bar.timestamp.minute == 32

    # New incomplete bar should exist for 14:33
    assert 'AAPL' in aggregator._current_bars
    current_bar = aggregator._current_bars['AAPL']
    assert current_bar.open == 151.00
    assert current_bar.timestamp.minute == 33


@pytest.mark.asyncio
async def test_multiple_symbols_independent_bars(mock_persistence_manager):
    """Test that multiple symbols maintain independent bars."""
    aggregator = TickAggregator(mock_persistence_manager)

    base_time = datetime(2025, 10, 10, 14, 32, 0, tzinfo=timezone.utc)

    ticks = [
        {'symbol': 'AAPL', 'price': 150.00, 'volume': 100, 'timestamp': base_time.timestamp() + 5},
        {'symbol': 'GOOGL', 'price': 2800.00, 'volume': 50, 'timestamp': base_time.timestamp() + 10},
        {'symbol': 'AAPL', 'price': 151.00, 'volume': 200, 'timestamp': base_time.timestamp() + 15},
        {'symbol': 'GOOGL', 'price': 2820.00, 'volume': 75, 'timestamp': base_time.timestamp() + 20},
    ]

    for tick in ticks:
        await aggregator.on_tick(tick)

    # Both symbols should have incomplete bars
    assert 'AAPL' in aggregator._current_bars
    assert 'GOOGL' in aggregator._current_bars

    aapl_bar = aggregator._current_bars['AAPL']
    assert aapl_bar.open == 150.00
    assert aapl_bar.close == 151.00
    assert aapl_bar.tick_count == 2

    googl_bar = aggregator._current_bars['GOOGL']
    assert googl_bar.open == 2800.00
    assert googl_bar.close == 2820.00
    assert googl_bar.tick_count == 2


@pytest.mark.asyncio
async def test_flush_incomplete_bars(mock_persistence_manager):
    """Test flushing incomplete bars during shutdown."""
    aggregator = TickAggregator(mock_persistence_manager)

    # Create incomplete bars for multiple symbols
    base_time = datetime(2025, 10, 10, 14, 32, 0, tzinfo=timezone.utc)

    ticks = [
        {'symbol': 'AAPL', 'price': 150.00, 'volume': 100, 'timestamp': base_time.timestamp() + 5},
        {'symbol': 'GOOGL', 'price': 2800.00, 'volume': 50, 'timestamp': base_time.timestamp() + 10},
        {'symbol': 'MSFT', 'price': 380.00, 'volume': 75, 'timestamp': base_time.timestamp() + 15},
    ]

    for tick in ticks:
        await aggregator.on_tick(tick)

    # Should have 3 incomplete bars
    assert len(aggregator._current_bars) == 3

    # Flush incomplete bars
    await aggregator.flush_incomplete_bars()

    # All bars should be completed
    assert len(aggregator._current_bars) == 0
    assert len(mock_persistence_manager.bars_received) == 3

    # Verify symbols
    symbols = {bar.symbol for bar in mock_persistence_manager.bars_received}
    assert symbols == {'AAPL', 'GOOGL', 'MSFT'}


@pytest.mark.asyncio
async def test_performance_1000_ticks(mock_persistence_manager):
    """Test performance with 1000 ticks (should be <100ms)."""
    import time

    aggregator = TickAggregator(mock_persistence_manager)

    base_time = datetime(2025, 10, 10, 14, 32, 0, tzinfo=timezone.utc)

    start = time.time()

    for i in range(1000):
        tick = {
            'symbol': f'SYM{i % 10}',  # 10 symbols
            'price': 100.0 + (i % 100) * 0.1,
            'volume': 100,
            'timestamp': base_time.timestamp() + (i * 0.1)
        }
        await aggregator.on_tick(tick)

    duration = time.time() - start

    # Should process 1000 ticks in <100ms
    assert duration < 0.1, f"Performance degradation: {duration:.3f}s for 1000 ticks"

    # Verify stats
    stats = aggregator.get_stats()
    assert stats['ticks_processed'] == 1000
```

---

### Integration Tests

**File**: `tests/integration/streaming/test_pattern_detection_flow.py`

```python
import pytest
import asyncio
from datetime import datetime, timezone


@pytest.mark.integration
@pytest.mark.asyncio
async def test_end_to_end_tick_to_pattern_flow():
    """
    Test complete flow: Tick → Aggregator → Pattern Detection

    This test verifies:
    1. TickAggregator processes ticks correctly
    2. Completed bars trigger StreamingPatternJob
    3. Patterns are detected and stored in intraday_patterns
    """
    # Initialize components
    from src.streaming.tick_aggregator import TickAggregator
    from src.streaming.persistence_manager import StreamingPersistenceManager
    from src.jobs.streaming_pattern_job import StreamingPatternJob

    # Setup (using test database)
    db_config = get_test_db_config()
    persistence_manager = StreamingPersistenceManager(db_config)
    tick_aggregator = TickAggregator(persistence_manager)

    # Register pattern job as subscriber
    pattern_job = StreamingPatternJob(db_config)
    persistence_manager.add_minute_bar_subscriber(pattern_job.process_minute_bar_sequentially)

    # Generate 5 minutes of ticks (300 seconds, 1 tick per second per symbol)
    symbols = ['AAPL', 'GOOGL', 'MSFT']
    base_time = datetime(2025, 10, 10, 14, 30, 0, tzinfo=timezone.utc)

    tick_count = 0
    for minute in range(5):
        for second in range(60):
            for symbol in symbols:
                tick = {
                    'symbol': symbol,
                    'price': 100.0 + (tick_count % 100) * 0.1,
                    'volume': 100,
                    'timestamp': base_time.timestamp() + (minute * 60) + second
                }
                await tick_aggregator.on_tick(tick)
                tick_count += 1

    # Force completion of last incomplete bars
    await tick_aggregator.flush_incomplete_bars()

    # Verify OHLCV bars created
    # Expected: 5 minutes × 3 symbols = 15 bars
    from sqlalchemy import select
    result = db.execute(
        select(func.count()).select_from(ohlcv_1min_table)
        .where(ohlcv_1min_table.c.timestamp >= base_time)
    )
    bar_count = result.scalar()
    assert bar_count == 15, f"Expected 15 bars, got {bar_count}"

    # Verify pattern detections occurred
    result = db.execute(
        select(func.count()).select_from(intraday_patterns_table)
        .where(intraday_patterns_table.c.detection_timestamp >= base_time)
    )
    pattern_count = result.scalar()
    assert pattern_count > 0, "No patterns detected"

    print(f"✅ Test passed: {bar_count} bars created, {pattern_count} patterns detected")
```

---

## Performance Benchmarks

### Target Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Tick Processing Time | <0.1ms per tick | Time `on_tick()` method |
| Memory Usage | <10MB for 100 symbols | Monitor `_current_bars` size |
| Bar Completion Time | <1ms | Time `_complete_bar()` method |
| Throughput | 10,000 ticks/sec | Stress test with concurrent ticks |
| Memory Leak | 0% growth over 24hrs | Long-running test |

### Benchmark Test

**File**: `tests/performance/test_aggregator_performance.py`

```python
import pytest
import time
from datetime import datetime, timezone


@pytest.mark.performance
@pytest.mark.asyncio
async def test_tick_processing_latency():
    """Measure tick processing latency (<0.1ms target)."""
    from src.streaming.tick_aggregator import TickAggregator

    aggregator = TickAggregator(mock_persistence_manager)

    base_time = datetime.now(timezone.utc)

    # Measure 10,000 ticks
    latencies = []

    for i in range(10000):
        tick = {
            'symbol': f'SYM{i % 100}',
            'price': 100.0 + (i % 100) * 0.1,
            'volume': 100,
            'timestamp': base_time.timestamp() + (i * 0.001)
        }

        start = time.perf_counter()
        await aggregator.on_tick(tick)
        latency = (time.perf_counter() - start) * 1000  # Convert to ms

        latencies.append(latency)

    avg_latency = sum(latencies) / len(latencies)
    p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
    p99_latency = sorted(latencies)[int(len(latencies) * 0.99)]

    print(f"Average latency: {avg_latency:.4f}ms")
    print(f"P95 latency: {p95_latency:.4f}ms")
    print(f"P99 latency: {p99_latency:.4f}ms")

    assert avg_latency < 0.1, f"Average latency too high: {avg_latency:.4f}ms"
    assert p95_latency < 0.2, f"P95 latency too high: {p95_latency:.4f}ms"
```

---

## Success Criteria (TickStockPL Perspective)

### Functional Requirements ✅
- ✅ TickAggregator processes ticks without errors
- ✅ Minute boundaries detected correctly
- ✅ OHLCV bars created with accurate data (OHLCV formula correct)
- ✅ Pattern detection triggered on completed bars
- ✅ Indicator calculations triggered on completed bars
- ✅ Results stored in `intraday_patterns` and `intraday_indicators` tables

### Performance Requirements ⚡
- ✅ Tick processing: <0.1ms per tick
- ✅ Memory usage: <10MB for 100 symbols
- ✅ Throughput: 10,000 ticks/sec sustained
- ✅ No memory leaks over 24-hour operation

### Integration Requirements 🔗
- ✅ Registered as callback with RedisTickSubscriber
- ✅ Initialized in StreamingScheduler
- ✅ Notifies StreamingPersistenceManager correctly
- ✅ Flushed during graceful shutdown

---

## Estimated Effort (TickStockPL Only)

**Component Development**: 4-6 hours
- TickAggregator class: 2 hours
- Integration with RedisTickSubscriber: 1 hour
- Integration with StreamingScheduler: 1 hour
- Unit tests: 2 hours

**Testing & Validation**: 2-3 hours
- Integration testing: 1 hour
- Performance testing: 1 hour
- End-to-end validation: 1 hour

**Total**: 6-9 hours (1-2 development sessions)

---

## Deployment Instructions

### Step 1: Implement TickAggregator
```bash
cd C:\Users\McDude\TickStockPL
# Create new file
# Copy TickAggregator class from this document
```

### Step 2: Modify RedisTickSubscriber
```bash
# Edit src/streaming/redis_tick_subscriber.py
# Add tick_aggregator parameter to __init__
# Register callback
# Remove direct pattern detection logic
```

### Step 3: Modify StreamingScheduler
```bash
# Edit src/services/streaming_scheduler.py
# Initialize TickAggregator
# Pass to RedisTickSubscriber
# Add flush call during shutdown
```

### Step 4: Run Unit Tests
```bash
pytest tests/unit/streaming/test_tick_aggregator.py -v
```

### Step 5: Run Integration Tests
```bash
pytest tests/integration/streaming/test_pattern_detection_flow.py -v
```

### Step 6: Validate with Live Data
```bash
# Start TickStockPL streaming service
python -m src.services.streaming_scheduler

# Monitor logs for:
# - "TICK-AGGREGATOR: Initialized"
# - "TICK-AGGREGATOR: Completed bar for AAPL at ..."
# - "STREAMING-PATTERN-JOB: Processing minute bar for AAPL"
```

---

## Validation Queries (After Deployment)

```sql
-- Check OHLCV bars created in last 10 minutes
SELECT symbol, timestamp, open, high, low, close, volume
FROM ohlcv_1min
WHERE timestamp > NOW() - INTERVAL '10 minutes'
ORDER BY timestamp DESC, symbol
LIMIT 100;

-- Check pattern detections
SELECT pattern_type, COUNT(*) as detections, AVG(confidence) as avg_confidence
FROM intraday_patterns
WHERE detection_timestamp > NOW() - INTERVAL '10 minutes'
GROUP BY pattern_type
ORDER BY detections DESC;

-- Check indicator calculations
SELECT indicator_name, COUNT(*) as calculations
FROM intraday_indicators
WHERE calculation_timestamp > NOW() - INTERVAL '10 minutes'
GROUP BY indicator_name
ORDER BY calculations DESC;

-- Verify bar creation rate (should match tick rate)
SELECT
    DATE_TRUNC('minute', timestamp) as minute,
    COUNT(*) as bars_created
FROM ohlcv_1min
WHERE timestamp > NOW() - INTERVAL '1 hour'
GROUP BY minute
ORDER BY minute DESC;
```

---

## Rollback Plan

If issues detected after deployment:

1. **Disable TickAggregator**:
   ```python
   # In streaming_scheduler.py
   self.tick_aggregator = None  # Temporarily disable
   ```

2. **Revert to Previous State**:
   ```bash
   git revert <commit-hash>
   ```

3. **Fallback to AppV2 Aggregation**:
   - Temporarily re-enable `OHLCVPersistenceService` in TickStockAppV2
   - Coordinate with AppV2 team

4. **Monitor Logs**:
   - Check for errors in TickAggregator
   - Verify no data corruption in `ohlcv_1min` table

---

## Next Steps After Implementation

Once TickStockPL TickAggregator is validated:

1. **Phase 2**: Remove `OHLCVPersistenceService` from TickStockAppV2 (see Sprint 42 plan)
2. **Phase 3**: Change TickStockAppV2 database user to read-only
3. **Phase 4**: Update all documentation
4. **Phase 5**: Sprint 42 closure and retrospective

---

**Document Created**: October 10, 2025
**Target Audience**: TickStockPL Development Team
**Sprint**: Sprint 42 - Architectural Realignment
**Status**: 🎯 READY FOR IMPLEMENTATION
**Priority**: P0 - Critical

---

## Appendix: Comparison with AppV2 Implementation

### AppV2's OHLCVPersistenceService (TO BE REMOVED)

**File**: `C:\Users\McDude\TickStockAppV2\src\infrastructure\database\ohlcv_persistence.py`

**Key Features** (for reference):
- Batching: 100 records before write
- Flush interval: 5 seconds
- Deduplication: Handles duplicate (symbol, timestamp) pairs
- UPSERT logic: ON CONFLICT DO UPDATE

**Differences from TickStockPL TickAggregator**:
1. **AppV2**: Batch-oriented, queue-based
2. **TickStockPL**: Event-driven, immediate notification
3. **AppV2**: Writes directly to DB
4. **TickStockPL**: Notifies subscribers THEN writes

**Why TickStockPL Approach is Better**:
- ✅ Aligns with producer role
- ✅ Enables immediate pattern detection (no batching delay)
- ✅ Single source of truth
- ✅ Loose coupling via events

---

**End of Document**
