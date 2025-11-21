# Sprint 51: Multi-Connection WebSocket Manager

**Status**: Planning
**Created**: 2025-11-20
**Goal**: Implement support for multiple concurrent Massive API WebSocket connections with independent stock subscriptions

---

## Executive Summary

Implement a multi-connection WebSocket manager that enables TickStockAppV2 to utilize up to 3 concurrent Massive API WebSocket connections (account limit), with each connection handling a different set of stocks. This improves scalability, reduces per-connection load, and enables advanced routing strategies.

---

## Feasibility Analysis

### ✅ FEASIBLE - Architecture Supports Multiple Connections

**Current Architecture Assessment:**

1. **Single Connection Pattern** (Current State):
   - ONE `MassiveWebSocketClient` instance created via `RealTimeDataAdapter`
   - Located: `src/infrastructure/data_sources/adapters/realtime_adapter.py:32`
   - Subscribes to all tickers through single WebSocket connection
   - Connection URL: `wss://socket.massive.com/stocks`

2. **Multi-Connection Capability** (Confirmed):
   - `MassiveWebSocketClient` class is **thread-safe** (uses `threading.Lock()`)
   - Each instance manages **independent connection state**
   - No shared state between instances
   - Callbacks are per-instance
   - **Multiple instances CAN coexist**

3. **External Limit**:
   - Massive API allows **3 concurrent WebSocket connections** per account
   - Currently using **1 connection** (2 available)

**Conclusion**: Architecture is ready for multi-connection support. No fundamental changes required.

---

## Architecture Overview

### Current Architecture
```
┌─────────────────────────────────────────┐
│      TickStockAppV2(Consumer)          │
├─────────────────────────────────────────┤
│  MarketDataService                      │
│    └─> RealTimeDataAdapter              │
│         └─> MassiveWebSocketClient (1)  │ ──> wss://socket.massive.com
│              └─> tickers: [ALL]         │     (subscribes to ALL symbols)
└─────────────────────────────────────────┘
```

### Proposed Architecture (Sprint 51)
```
┌──────────────────────────────────────────────────────────────┐
│           TickStockAppV2 (Consumer)                          │
├──────────────────────────────────────────────────────────────┤
│  MarketDataService                                           │
│    └─> MultiConnectionManager (NEW)                          │
│         ├─> Connection 1 (Primary Watchlist)                │ ──> wss://socket.massive.com
│         │    └─> MassiveWebSocketClient                     │     (tickers: AAPL, NVDA, TSLA...)
│         │         └─> tickers: [Group A]                    │
│         │                                                    │
│         ├─> Connection 2 (Secondary Watchlist)              │ ──> wss://socket.massive.com
│         │    └─> MassiveWebSocketClient                     │     (tickers: AMZN, GOOGL, MSFT...)
│         │         └─> tickers: [Group B]                    │
│         │                                                    │
│         └─> Connection 3 (Tertiary Watchlist)               │ ──> wss://socket.massive.com
│              └─> MassiveWebSocketClient                     │     (tickers: META, NFLX, AMD...)
│                   └─> tickers: [Group C]                    │
│                                                              │
│         Aggregated Callback ──> tick_callback()             │
│         Aggregated Status   ──> status_callback()           │
└──────────────────────────────────────────────────────────────┘
```

---

## Use Cases

### 1. **Segmented Watchlists**
- **Primary Watchlist**: User's top 20 most-watched symbols (Connection 1)
- **Secondary Watchlist**: Next 50 symbols of interest (Connection 2)
- **Discovery List**: Experimental/new symbols (Connection 3)

### 2. **Performance Optimization**
- Distribute symbol load across connections
- Reduce per-connection message rate
- Better handling of high-volume symbols

### 3. **User Tier Routing**
- Premium users: Connection 1 (low latency)
- Standard users: Connection 2 (normal priority)
- Free tier: Connection 3 (rate-limited)

### 4. **Sector-Based Routing**
- Tech stocks: Connection 1
- Finance stocks: Connection 2
- Healthcare/Energy: Connection 3

### 5. **Failover & Redundancy**
- Critical symbols on multiple connections
- Automatic failover if one connection drops
- Health monitoring per connection

---

## Implementation Tasks

### Phase 1: Multi-Connection Manager Core

**File**: `src/infrastructure/websocket/multi_connection_manager.py`

**Responsibilities**:
- Manage up to 3 `MassiveWebSocketClient` instances
- Handle ticker-to-connection routing
- Aggregate callbacks from all connections
- Connection health monitoring
- Automatic reconnection and failover

**Key Methods**:
```python
class MultiConnectionManager:
    def __init__(self, config, max_connections=3)
    def add_connection(self, connection_id, ticker_filter) -> bool
    def remove_connection(self, connection_id) -> bool
    def subscribe_ticker(self, ticker, connection_id=None) -> bool
    def unsubscribe_ticker(self, ticker) -> bool
    def get_connection_for_ticker(self, ticker) -> str
    def rebalance_connections() -> dict
    def get_health_status() -> dict
```

### Phase 2: Connection Routing Strategy

**File**: `src/infrastructure/websocket/connection_router.py`

**Strategies**:
- **Round-Robin**: Distribute tickers evenly across connections
- **Priority-Based**: Route by symbol priority/tier
- **Load-Balanced**: Balance by message volume
- **Manual Assignment**: User-defined routing rules

**Configuration**:
```bash
# Multi-Connection WebSocket Configuration
USE_MULTI_CONNECTION=false  # Enable/disable multi-connection mode
WEBSOCKET_CONNECTIONS_MAX=3  # Maximum connections (Massive API limit)
WEBSOCKET_ROUTING_STRATEGY=manual  # manual, round-robin, load-balanced

# Connection 1: Primary Watchlist
WEBSOCKET_CONNECTION_1_ENABLED=true
WEBSOCKET_CONNECTION_1_NAME=primary
WEBSOCKET_CONNECTION_1_UNIVERSE_KEY=tech_leaders:top_20
# Alternative: Direct symbol list (if universe key not used)
# WEBSOCKET_CONNECTION_1_SYMBOLS=AAPL,NVDA,TSLA,AMZN,GOOGL

# Connection 2: Secondary Watchlist
WEBSOCKET_CONNECTION_2_ENABLED=false
WEBSOCKET_CONNECTION_2_NAME=secondary
WEBSOCKET_CONNECTION_2_UNIVERSE_KEY=finance_sector:large_cap
# WEBSOCKET_CONNECTION_2_SYMBOLS=JPM,BAC,GS,V,MA,AXP

# Connection 3: Tertiary Watchlist
WEBSOCKET_CONNECTION_3_ENABLED=false
WEBSOCKET_CONNECTION_3_NAME=tertiary
WEBSOCKET_CONNECTION_3_UNIVERSE_KEY=healthcare_sector:top_10
# WEBSOCKET_CONNECTION_3_SYMBOLS=UNH,JNJ,PFE,ABBV,TMO

# Connection Health Monitoring
WEBSOCKET_HEALTH_CHECK_INTERVAL=30  # seconds
WEBSOCKET_AUTO_REBALANCE=true
WEBSOCKET_FAILOVER_ENABLED=true
```

### Phase 2.5: Configuration Management Integration

**File**: `src/core/services/config_manager.py`

**Add to DEFAULTS dict** (around line 100):
```python
# Sprint 51: Multi-Connection WebSocket Configuration
'USE_MULTI_CONNECTION': False,
'WEBSOCKET_CONNECTIONS_MAX': 3,
'WEBSOCKET_ROUTING_STRATEGY': 'manual',

# Connection 1 Configuration
'WEBSOCKET_CONNECTION_1_ENABLED': True,
'WEBSOCKET_CONNECTION_1_NAME': 'primary',
'WEBSOCKET_CONNECTION_1_UNIVERSE_KEY': '',  # e.g., 'tech_leaders:top_20'
'WEBSOCKET_CONNECTION_1_SYMBOLS': '',  # Fallback if universe key not set

# Connection 2 Configuration
'WEBSOCKET_CONNECTION_2_ENABLED': False,
'WEBSOCKET_CONNECTION_2_NAME': 'secondary',
'WEBSOCKET_CONNECTION_2_UNIVERSE_KEY': '',
'WEBSOCKET_CONNECTION_2_SYMBOLS': '',

# Connection 3 Configuration
'WEBSOCKET_CONNECTION_3_ENABLED': False,
'WEBSOCKET_CONNECTION_3_NAME': 'tertiary',
'WEBSOCKET_CONNECTION_3_UNIVERSE_KEY': '',
'WEBSOCKET_CONNECTION_3_SYMBOLS': '',

# Connection Health Monitoring
'WEBSOCKET_HEALTH_CHECK_INTERVAL': 30,
'WEBSOCKET_AUTO_REBALANCE': True,
'WEBSOCKET_FAILOVER_ENABLED': True,
```

**Add to VALIDATION_RULES dict** (around line 260):
```python
# Sprint 51: Multi-Connection WebSocket Validation
'USE_MULTI_CONNECTION': bool,
'WEBSOCKET_CONNECTIONS_MAX': int,
'WEBSOCKET_ROUTING_STRATEGY': str,
'WEBSOCKET_CONNECTION_1_ENABLED': bool,
'WEBSOCKET_CONNECTION_1_NAME': str,
'WEBSOCKET_CONNECTION_1_UNIVERSE_KEY': str,
'WEBSOCKET_CONNECTION_1_SYMBOLS': str,
'WEBSOCKET_CONNECTION_2_ENABLED': bool,
'WEBSOCKET_CONNECTION_2_NAME': str,
'WEBSOCKET_CONNECTION_2_UNIVERSE_KEY': str,
'WEBSOCKET_CONNECTION_2_SYMBOLS': str,
'WEBSOCKET_CONNECTION_3_ENABLED': bool,
'WEBSOCKET_CONNECTION_3_NAME': str,
'WEBSOCKET_CONNECTION_3_UNIVERSE_KEY': str,
'WEBSOCKET_CONNECTION_3_SYMBOLS': str,
'WEBSOCKET_HEALTH_CHECK_INTERVAL': int,
'WEBSOCKET_AUTO_REBALANCE': bool,
'WEBSOCKET_FAILOVER_ENABLED': bool,
```

### Phase 3: Integration with RealTimeDataAdapter

**File**: `src/infrastructure/data_sources/adapters/realtime_adapter.py`

**Changes**:
- Replace single `MassiveWebSocketClient` with `MultiConnectionManager`
- Update `connect()` method to initialize multiple connections
- Maintain backward compatibility

**Before**:
```python
self.client = MassiveWebSocketClient(
    api_key=config['MASSIVE_API_KEY'],
    on_tick_callback=self.tick_callback,
    on_status_callback=self.status_callback,
    config=config
)
```

**After**:
```python
use_multi_connection = config.get('USE_MULTI_CONNECTION', False)

if use_multi_connection:
    self.client = MultiConnectionManager(
        config=config,
        on_tick_callback=self.tick_callback,
        on_status_callback=self.status_callback,
        max_connections=config.get('WEBSOCKET_CONNECTIONS_MAX', 3)
    )
else:
    # Legacy single connection (backward compatible)
    self.client = MassiveWebSocketClient(...)
```

### Phase 4: Health Monitoring Dashboard

**File**: `src/api/rest/websocket_health.py` (NEW)

**Endpoints**:
- `GET /api/websocket/connections` - List all connections and status
- `GET /api/websocket/connections/{id}` - Connection details
- `GET /api/websocket/connections/{id}/tickers` - Tickers per connection
- `POST /api/websocket/rebalance` - Trigger connection rebalancing

**Dashboard Widget**:
- Real-time connection status (connected/disconnected)
- Symbol count per connection
- Message rate per connection
- Error counts and latency metrics

### Phase 5: Testing & Validation

**Tests Required**:
1. **Unit Tests**: `tests/unit/test_multi_connection_manager.py`
   - Connection lifecycle (add, remove, reconnect)
   - Ticker routing logic
   - Callback aggregation
   - Error handling

2. **Integration Tests**: `tests/integration/test_multi_connection_integration.py`
   - Multiple connections to Massive API (use test symbols)
   - Failover scenarios
   - Concurrent subscription updates
   - Load distribution validation

3. **Performance Tests**: `tests/performance/test_multi_connection_performance.py`
   - Verify improved throughput with 3 connections vs 1
   - Latency comparison
   - Connection overhead measurement

---

## Technical Specifications

### 1. MultiConnectionManager Class Design

```python
"""
Multi-connection WebSocket manager for Massive API.

Manages up to 3 concurrent WebSocket connections with independent ticker subscriptions.
Provides unified interface for subscription management and callback aggregation.
"""

import logging
import threading
from typing import Callable, Dict, List, Set, Optional
from dataclasses import dataclass, field

from src.presentation.websocket.massive_client import MassiveWebSocketClient

logger = logging.getLogger(__name__)


@dataclass
class ConnectionInfo:
    """Information about a WebSocket connection."""
    connection_id: str
    client: MassiveWebSocketClient
    assigned_tickers: Set[str] = field(default_factory=set)
    status: str = "disconnected"  # disconnected, connecting, connected, error
    message_count: int = 0
    error_count: int = 0
    last_message_time: float = 0.0


class MultiConnectionManager:
    """
    Manages multiple Massive API WebSocket connections.

    Features:
    - Up to 3 concurrent connections (Massive API limit)
    - Intelligent ticker routing
    - Aggregated callbacks
    - Health monitoring and failover
    - Connection rebalancing

    Performance Targets:
    - Connection initialization: <10s for all 3 connections
    - Ticker routing: <1ms lookup time
    - Callback aggregation: <5ms overhead
    """

    def __init__(
        self,
        config: dict,
        on_tick_callback: Callable,
        on_status_callback: Callable,
        max_connections: int = 3
    ):
        """
        Initialize multi-connection manager using ConfigManager settings.

        Args:
            config: Application configuration (from ConfigManager)
            on_tick_callback: Callback for tick data (aggregated from all connections)
            on_status_callback: Callback for status updates
            max_connections: Maximum number of connections (default: 3)
        """
        self.config = config
        self.max_connections = max_connections
        self.api_key = config.get('MASSIVE_API_KEY')

        # Validate multi-connection is enabled
        if not config.get('USE_MULTI_CONNECTION', False):
            logger.warning("MULTI-CONNECTION-MANAGER: Multi-connection mode disabled in config")

        # Connection management
        self.connections: Dict[str, ConnectionInfo] = {}
        self.ticker_to_connection: Dict[str, str] = {}  # ticker -> connection_id

        # Callbacks
        self._user_tick_callback = on_tick_callback
        self._user_status_callback = on_status_callback

        # Thread safety
        self._lock = threading.RLock()

        # Statistics
        self.total_ticks_received = 0
        self.total_errors = 0

        # Load and initialize enabled connections
        self._initialize_configured_connections()

        logger.info(
            f"MULTI-CONNECTION-MANAGER: Initialized with max {max_connections} connections, "
            f"{len(self.connections)} connections configured"
        )

    def _initialize_configured_connections(self):
        """Initialize connections based on config settings."""
        for conn_num in range(1, self.max_connections + 1):
            enabled_key = f'WEBSOCKET_CONNECTION_{conn_num}_ENABLED'
            name_key = f'WEBSOCKET_CONNECTION_{conn_num}_NAME'

            if self.config.get(enabled_key, False):
                connection_id = f'connection_{conn_num}'
                connection_name = self.config.get(name_key, connection_id)

                # Load tickers for this connection
                tickers = self._load_tickers_for_connection(connection_id)

                if tickers:
                    logger.info(
                        f"MULTI-CONNECTION: Connection {conn_num} ({connection_name}) "
                        f"configured with {len(tickers)} tickers"
                    )
                    # Connection will be created when connect_all() is called
                else:
                    logger.warning(
                        f"MULTI-CONNECTION: Connection {conn_num} enabled but no tickers configured"
                    )

    def _load_tickers_for_connection(self, connection_id: str) -> list[str]:
        """
        Load ticker list for a connection using SYMBOL_UNIVERSE_KEY approach.

        Follows existing pattern from market_data_service.py:151-178

        Args:
            connection_id: Connection identifier (e.g., 'connection_1', 'connection_2')

        Returns:
            List of ticker symbols
        """
        connection_num = connection_id.split('_')[-1]  # Extract '1', '2', '3'

        # Get universe key from config
        universe_key_config = f'WEBSOCKET_CONNECTION_{connection_num}_UNIVERSE_KEY'
        symbols_config = f'WEBSOCKET_CONNECTION_{connection_num}_SYMBOLS'

        universe_key = self.config.get(universe_key_config, '').strip()
        direct_symbols = self.config.get(symbols_config, '').strip()

        # Try universe key first (preferred method)
        if universe_key:
            try:
                logger.info(f"MULTI-CONNECTION: Loading tickers for {connection_id} from universe: {universe_key}")

                # Import CacheControl to get universe tickers
                from src.infrastructure.cache.cache_control import CacheControl
                cache = CacheControl()

                # Get tickers from cache
                universe_tickers = cache.get_universe_tickers(universe_key)

                if universe_tickers and len(universe_tickers) > 0:
                    logger.info(
                        f"MULTI-CONNECTION: {connection_id} loaded {len(universe_tickers)} tickers "
                        f"from universe '{universe_key}': "
                        f"{', '.join(universe_tickers[:5])}{'...' if len(universe_tickers) > 5 else ''}"
                    )
                    return universe_tickers
                else:
                    logger.warning(
                        f"MULTI-CONNECTION: Universe '{universe_key}' not found or empty "
                        f"for {connection_id}, trying direct symbols"
                    )
            except Exception as e:
                logger.error(f"MULTI-CONNECTION: Error loading universe '{universe_key}': {e}")

        # Fallback to direct symbol list
        if direct_symbols:
            tickers = [s.strip() for s in direct_symbols.split(',') if s.strip()]
            logger.info(
                f"MULTI-CONNECTION: {connection_id} using direct symbols: "
                f"{len(tickers)} tickers configured"
            )
            return tickers

        # No configuration found
        logger.warning(
            f"MULTI-CONNECTION: No universe key or symbols configured for {connection_id}"
        )
        return []

    def add_connection(
        self,
        connection_id: str,
        ticker_filter: Optional[List[str]] = None
    ) -> bool:
        """
        Add a new WebSocket connection.

        Args:
            connection_id: Unique identifier for this connection
            ticker_filter: List of tickers to assign to this connection (optional)

        Returns:
            True if connection added successfully
        """
        pass  # Implementation in Phase 1

    def connect_all(self, ticker_assignments: Dict[str, List[str]]) -> bool:
        """
        Connect all configured connections with ticker assignments.

        Args:
            ticker_assignments: Dict of connection_id -> [tickers]

        Returns:
            True if all connections established

        Example:
            ticker_assignments = {
                'primary': ['AAPL', 'NVDA', 'TSLA'],
                'secondary': ['AMZN', 'GOOGL', 'MSFT'],
                'tertiary': ['META', 'NFLX', 'AMD']
            }
        """
        pass  # Implementation in Phase 1

    def subscribe_ticker(
        self,
        ticker: str,
        connection_id: Optional[str] = None
    ) -> bool:
        """
        Subscribe to a ticker on specified connection (or auto-assign).

        Args:
            ticker: Symbol to subscribe
            connection_id: Target connection (None = auto-assign)

        Returns:
            True if subscription successful
        """
        pass  # Implementation in Phase 1

    def _aggregate_tick_callback(self, tick_data, connection_id: str):
        """
        Internal callback that aggregates ticks from all connections.

        Args:
            tick_data: TickData object
            connection_id: Source connection ID
        """
        with self._lock:
            self.total_ticks_received += 1

            # Update connection stats
            if connection_id in self.connections:
                conn = self.connections[connection_id]
                conn.message_count += 1
                conn.last_message_time = time.time()

        # Forward to user callback
        self._user_tick_callback(tick_data)

    def get_health_status(self) -> dict:
        """
        Get health status of all connections.

        Returns:
            Dict with connection health metrics
        """
        with self._lock:
            return {
                'total_connections': len(self.connections),
                'connected': sum(1 for c in self.connections.values() if c.status == 'connected'),
                'total_tickers': len(self.ticker_to_connection),
                'total_ticks': self.total_ticks_received,
                'total_errors': self.total_errors,
                'connections': {
                    conn_id: {
                        'status': conn.status,
                        'tickers': len(conn.assigned_tickers),
                        'messages': conn.message_count,
                        'errors': conn.error_count
                    }
                    for conn_id, conn in self.connections.items()
                }
            }
```

### 2. Configuration Format

**File**: `.env` additions

```bash
# Multi-Connection WebSocket Configuration
USE_MULTI_CONNECTION=false  # Enable/disable multi-connection mode
WEBSOCKET_CONNECTIONS_MAX=3  # Maximum connections (Massive API limit)
WEBSOCKET_ROUTING_STRATEGY=manual  # manual, round-robin, load-balanced

# Connection 1: Primary Watchlist
WEBSOCKET_CONNECTION_1_ENABLED=true
WEBSOCKET_CONNECTION_1_NAME=primary
WEBSOCKET_CONNECTION_1_UNIVERSE_KEY=tech_leaders:top_20
# Alternative: Direct symbol list (if universe key not used)
# WEBSOCKET_CONNECTION_1_SYMBOLS=AAPL,NVDA,TSLA,AMZN,GOOGL

# Connection 2: Secondary Watchlist
WEBSOCKET_CONNECTION_2_ENABLED=false
WEBSOCKET_CONNECTION_2_NAME=secondary
WEBSOCKET_CONNECTION_2_UNIVERSE_KEY=finance_sector:large_cap
# WEBSOCKET_CONNECTION_2_SYMBOLS=JPM,BAC,GS,V,MA,AXP

# Connection 3: Tertiary Watchlist
WEBSOCKET_CONNECTION_3_ENABLED=false
WEBSOCKET_CONNECTION_3_NAME=tertiary
WEBSOCKET_CONNECTION_3_UNIVERSE_KEY=healthcare_sector:top_10
# WEBSOCKET_CONNECTION_3_SYMBOLS=UNH,JNJ,PFE,ABBV,TMO

# Connection Health Monitoring
WEBSOCKET_HEALTH_CHECK_INTERVAL=30  # seconds
WEBSOCKET_AUTO_REBALANCE=true
WEBSOCKET_FAILOVER_ENABLED=true
```

**Integration with ConfigManager**:
- All settings automatically loaded via `ConfigManager.DEFAULTS`
- Type validation via `ConfigManager.VALIDATION_RULES`
- Universe keys resolved using `CacheControl.get_universe_tickers()`
- Backward compatible with existing `SYMBOL_UNIVERSE_KEY` for single connection

---

## Success Criteria

### Functional Requirements
- ✅ Support up to 3 concurrent Massive API WebSocket connections
- ✅ Independent ticker subscriptions per connection
- ✅ Unified callback interface (no breaking changes)
- ✅ Automatic reconnection and failover
- ✅ Health monitoring dashboard

### Performance Requirements
- ✅ Connection initialization: <10 seconds for all 3 connections
- ✅ Ticker routing lookup: <1ms
- ✅ Callback aggregation overhead: <5ms
- ✅ No message loss during failover
- ✅ Support 100+ tickers per connection (300+ total)

### Quality Requirements
- ✅ 90%+ test coverage for MultiConnectionManager
- ✅ Integration tests with real Massive API connections
- ✅ Performance benchmarks showing improvement
- ✅ Zero memory leaks during 24-hour test
- ✅ Graceful degradation if connections drop

---

## Risks & Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Massive API rate limits per connection | High | Medium | Monitor message rates, implement backpressure |
| Connection overhead impacts performance | Medium | Low | Benchmark early, optimize callback aggregation |
| Failover causes data loss | High | Low | Buffer messages during reconnection |
| Configuration complexity | Low | Medium | Provide sensible defaults, clear documentation |
| Memory usage with 3 connections | Medium | Low | Monitor memory, implement connection pooling |

---

## Timeline

### Phase 1: Core Implementation (Week 1)
- Day 1-2: Implement `MultiConnectionManager` class
- Day 3: Connection routing logic
- Day 4-5: Unit tests and basic integration

### Phase 2: Integration (Week 2)
- Day 1-2: Update `RealTimeDataAdapter`
- Day 3: Configuration management
- Day 4-5: Integration testing with Massive API

### Phase 3: Monitoring & Polish (Week 3)
- Day 1-2: Health monitoring endpoints
- Day 3: Dashboard UI updates
- Day 4-5: Performance testing and optimization

**Total Duration**: 3 weeks

---

## Backward Compatibility

**CRITICAL**: Maintain full backward compatibility

- Default behavior: Single connection (current behavior)
- Enable multi-connection via `USE_MULTI_CONNECTION=true`
- Fallback to single connection if configuration invalid
- No changes to callback signatures
- Existing tests must pass without modification

---

## References

**Key Files**:
- `src/presentation/websocket/massive_client.py:27` - MassiveWebSocketClient class
- `src/infrastructure/data_sources/adapters/realtime_adapter.py:21` - RealTimeDataAdapter
- `src/core/services/market_data_service.py:41` - MarketDataService

**Related Sprints**:
- Sprint 42: OHLCV aggregation and Redis integration
- Sprint 43: Pattern display delay optimization

**Documentation**:
- Massive API WebSocket documentation: https://polygon.io/docs/websocket/getting-started
- TickStock WebSocket architecture: `docs/architecture/websocket_architecture.md`

---

## Appendix: Example Configurations

### Scenario 1: Tech Watchlist Using Universe Keys (Recommended)

```bash
# .env
USE_MULTI_CONNECTION=true
WEBSOCKET_CONNECTIONS_MAX=3

# Connection 1: Tech leaders from cache
WEBSOCKET_CONNECTION_1_ENABLED=true
WEBSOCKET_CONNECTION_1_NAME=tech_leaders
WEBSOCKET_CONNECTION_1_UNIVERSE_KEY=tech_leaders:top_20

# Connection 2: Finance sector from cache
WEBSOCKET_CONNECTION_2_ENABLED=true
WEBSOCKET_CONNECTION_2_NAME=finance_sector
WEBSOCKET_CONNECTION_2_UNIVERSE_KEY=finance_sector:large_cap

# Connection 3: Healthcare from cache
WEBSOCKET_CONNECTION_3_ENABLED=true
WEBSOCKET_CONNECTION_3_NAME=healthcare
WEBSOCKET_CONNECTION_3_UNIVERSE_KEY=healthcare_sector:top_10
```

### Scenario 2: Direct Symbol Assignment (Legacy/Testing)

```bash
# .env
USE_MULTI_CONNECTION=true

# Connection 1: Manual symbols
WEBSOCKET_CONNECTION_1_ENABLED=true
WEBSOCKET_CONNECTION_1_NAME=primary_watchlist
WEBSOCKET_CONNECTION_1_SYMBOLS=AAPL,NVDA,TSLA,AMZN,GOOGL,MSFT,META

# Connection 2: Disabled
WEBSOCKET_CONNECTION_2_ENABLED=false

# Connection 3: Disabled
WEBSOCKET_CONNECTION_3_ENABLED=false
```

### Scenario 3: Using Existing SYMBOL_UNIVERSE_KEY (Single Connection - Backward Compatible)

```bash
# .env
USE_MULTI_CONNECTION=false
SYMBOL_UNIVERSE_KEY=stock_etf_test:combo_test  # Existing single-connection approach
```

### Scenario 4: Hybrid Approach

```bash
# Connection 1: Use universe key
WEBSOCKET_CONNECTION_1_ENABLED=true
WEBSOCKET_CONNECTION_1_UNIVERSE_KEY=market_leaders:top_50

# Connection 2: Direct symbols (for testing specific stocks)
WEBSOCKET_CONNECTION_2_ENABLED=true
WEBSOCKET_CONNECTION_2_SYMBOLS=TSLA,GME,AMC  # Meme stocks for testing

# Connection 3: Another universe
WEBSOCKET_CONNECTION_3_ENABLED=true
WEBSOCKET_CONNECTION_3_UNIVERSE_KEY=emerging_tech:ai_stocks
```

### Scenario 5: Load-Balanced Distribution

```bash
# .env
USE_MULTI_CONNECTION=true
WEBSOCKET_ROUTING_STRATEGY=round-robin

# When routing_strategy=round-robin, symbols are automatically
# distributed evenly across all enabled connections
WEBSOCKET_CONNECTION_1_ENABLED=true
WEBSOCKET_CONNECTION_1_UNIVERSE_KEY=market_leaders:top_100
# Automatically splits 100 symbols: ~33 per connection

WEBSOCKET_CONNECTION_2_ENABLED=true
WEBSOCKET_CONNECTION_3_ENABLED=true
```

---

**Next Steps**: Review this plan, approve, and begin Phase 1 implementation.
