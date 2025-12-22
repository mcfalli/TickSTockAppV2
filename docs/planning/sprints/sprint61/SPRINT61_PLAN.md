# Sprint 61: WebSocket Universe Loading via RelationshipCache

**Status**: 🔄 In Progress
**Started**: December 21, 2025
**Target**: December 22, 2025
**Sprint Goal**: Migrate WebSocket universe loading from CacheControl (cache_entries) to RelationshipCache (definition_groups/group_memberships)

---

## Overview

Sprint 61 migrates the WebSocket connection symbol loading from the legacy `cache_entries` table to the new relational `definition_groups`/`group_memberships` structure, leveraging the Sprint 60 RelationshipCache service.

**Key Features**:
- ✅ Support new universe key format: `nasdaq100`, `sp500`, `dow30`, `russell3000`
- ✅ Support multi-universe joining: `sp500:nasdaq100` creates distinct superset (union)
- ✅ Fully migrate stock/universe loading to RelationshipCache
- ✅ CacheControl remains for non-stock types only (app_settings, themes, etc.)
- ✅ Multi-connection mode support (focus on Connection 1 development)

---

## Background

### Current State (Sprint 59-60)
- **Sprint 59**: Migrated ETF-stock relationships from JSONB `cache_entries` to relational tables
- **Sprint 60**: Created `RelationshipCache` service with <1ms in-memory access
- **WebSocket Integration**: Still uses `CacheControl.get_universe_tickers()` from old `cache_entries` table

### Problem
WebSocket connections load symbols from **old** `cache_entries` table via `CacheControl`, but our source of truth is now `definition_groups`/`group_memberships`.

### Solution
Add universe loading to `RelationshipCache` and update WebSocket code to use it.

---

## Architecture

### Data Source Migration

**Before (Sprint 60)**:
```
WebSocket Connection Config
  ↓
WEBSOCKET_CONNECTION_1_UNIVERSE_KEY=market_leaders:top_100
  ↓
CacheControl.get_universe_tickers("market_leaders:top_100")
  ↓
cache_entries table (JSONB)
  ↓
Returns: ['AAPL', 'MSFT', 'NVDA', ...]
```

**After (Sprint 61)**:
```
WebSocket Connection Config
  ↓
WEBSOCKET_CONNECTION_1_UNIVERSE_KEY=sp500:nasdaq100
  ↓
RelationshipCache.get_universe_symbols("sp500:nasdaq100")
  ↓
definition_groups + group_memberships tables (relational)
  ↓
Returns: ['AAPL', 'MSFT', 'NVDA', ...] (distinct union)
```

### Universe Key Format

**Single Universe**:
```bash
WEBSOCKET_CONNECTION_1_UNIVERSE_KEY=nasdaq100
# Loads: 102 symbols from definition_groups WHERE name='nasdaq100' AND type='UNIVERSE'
```

**Multi-Universe Join** (Distinct Superset):
```bash
WEBSOCKET_CONNECTION_1_UNIVERSE_KEY=sp500:nasdaq100:dow30
# Loads: DISTINCT union of all 3 universes
# Example: sp500 (505) + nasdaq100 (102) + dow30 (30) = ~550 distinct symbols
```

**ETF Holdings**:
```bash
WEBSOCKET_CONNECTION_1_UNIVERSE_KEY=SPY
# Loads: ETF holdings from definition_groups WHERE name='SPY' AND type='ETF'
# Returns: 504 symbols
```

**Direct Symbols** (Fallback):
```bash
WEBSOCKET_CONNECTION_1_SYMBOLS=AAPL,NVDA,TSLA,MSFT,GOOGL,META,AMZN
# No database query, uses direct list
# Returns: 7 symbols
```

### Priority Logic

If **both** `UNIVERSE_KEY` and `SYMBOLS` are set:
```python
# Priority: UNIVERSE_KEY > SYMBOLS
if connection_config.get('UNIVERSE_KEY'):
    symbols = relationship_cache.get_universe_symbols(connection_config['UNIVERSE_KEY'])
elif connection_config.get('SYMBOLS'):
    symbols = connection_config['SYMBOLS'].split(',')
else:
    symbols = []  # No symbols configured
```

---

## Implementation Plan

### Phase 1: Extend RelationshipCache (2 hours)

**File**: `src/core/services/relationship_cache.py`

**Add Methods**:

1. **`get_universe_symbols(universe_key: str) -> List[str]`**
   - Parse universe_key (split on colon for multi-universe)
   - For each universe part:
     - Check if ETF: `definition_groups WHERE name=? AND type='ETF'`
     - Check if UNIVERSE: `definition_groups WHERE name=? AND type='UNIVERSE'`
     - Load symbols from `group_memberships WHERE group_id=?`
   - Return distinct union of all symbols
   - Cache result with TTL

2. **`_parse_universe_key(universe_key: str) -> List[str]`**
   - Split on colon: `"sp500:nasdaq100"` → `["sp500", "nasdaq100"]`
   - Return list of individual universe names

3. **`_load_universe_symbols_from_db(universe_name: str) -> List[str]`**
   - Query database for universe/ETF
   - Return symbols for single universe

**Pseudo-code**:
```python
def get_universe_symbols(self, universe_key: str) -> List[str]:
    """
    Get symbols for universe(s). Supports multi-universe join with colon separator.

    Examples:
        'nasdaq100' -> 102 symbols
        'sp500:nasdaq100' -> ~550 distinct symbols (union)
        'SPY' -> 504 ETF holdings
    """
    # Check cache
    cache_key = f"universe_symbols:{universe_key}"
    if cache_key in self._universe_symbols:
        symbols, timestamp = self._universe_symbols[cache_key]
        if not self._is_expired(timestamp):
            self._stats['hits'] += 1
            return symbols.copy()

    # Cache miss - load from DB
    self._stats['misses'] += 1
    universe_parts = self._parse_universe_key(universe_key)

    all_symbols = set()
    for universe_name in universe_parts:
        symbols = self._load_universe_symbols_from_db(universe_name)
        all_symbols.update(symbols)

    symbols_list = sorted(list(all_symbols))

    # Cache result
    with self._lock:
        self._universe_symbols[cache_key] = (symbols_list, datetime.now())
        self._stats['loads'] += 1

    return symbols_list.copy()
```

**Database Query**:
```sql
-- Find universe/ETF
SELECT id FROM definition_groups
WHERE name = %s
  AND type IN ('UNIVERSE', 'ETF')
  AND environment = 'DEFAULT'
LIMIT 1;

-- Get symbols
SELECT DISTINCT symbol
FROM group_memberships
WHERE group_id = %s
ORDER BY symbol;
```

---

### Phase 2: Update WebSocket Integration (1.5 hours)

**Files to Update**:
- `src/infrastructure/websocket/multi_connection_manager.py`
- `src/core/services/market_data_service.py` (if single-connection mode uses it)

**Changes**:

1. **Import RelationshipCache**:
```python
from src.core.services.relationship_cache import get_relationship_cache
```

2. **Update `_load_connection_config()` in MultiConnectionManager**:

**Before**:
```python
from src.infrastructure.cache.cache_control import CacheControl

cache = CacheControl()
cache.initialize()
symbols = cache.get_universe_tickers(universe_key)
```

**After**:
```python
from src.core.services.relationship_cache import get_relationship_cache

cache = get_relationship_cache()
symbols = cache.get_universe_symbols(universe_key)
```

3. **Fallback Logic**:
```python
# Priority: UNIVERSE_KEY > SYMBOLS > Empty
universe_key = config.get(f'WEBSOCKET_CONNECTION_{conn_num}_UNIVERSE_KEY', '').strip()
direct_symbols = config.get(f'WEBSOCKET_CONNECTION_{conn_num}_SYMBOLS', '').strip()

if universe_key:
    # Load from RelationshipCache (supports multi-universe join)
    cache = get_relationship_cache()
    symbols = cache.get_universe_symbols(universe_key)
    logger.info(f"Connection {conn_num}: Loaded {len(symbols)} symbols from universe '{universe_key}'")
elif direct_symbols:
    # Parse direct symbol list
    symbols = [s.strip() for s in direct_symbols.split(',') if s.strip()]
    logger.info(f"Connection {conn_num}: Using {len(symbols)} direct symbols")
else:
    symbols = []
    logger.warning(f"Connection {conn_num}: No symbols configured (UNIVERSE_KEY or SYMBOLS)")
```

---

### Phase 3: Update CacheControl (1 hour)

**File**: `src/infrastructure/cache/cache_control.py`

**Remove Stock Universe Support**:

1. **Deprecate `get_universe_tickers()` for stocks**:
```python
def get_universe_tickers(self, universe_key: str) -> list[str]:
    """
    DEPRECATED for stock/universe loading. Use RelationshipCache.get_universe_symbols() instead.

    This method now only supports non-stock cache types (themes, custom lists).
    Stock universes (NASDAQ-100, S&P 500, etc.) are loaded from definition_groups/group_memberships.
    """
    logger.warning(
        "CacheControl.get_universe_tickers() is deprecated for stock universes. "
        "Use RelationshipCache.get_universe_symbols() instead. "
        f"Attempted to load: {universe_key}"
    )

    # Only support legacy theme-based universes
    if universe_key.startswith('theme_'):
        # ... existing theme loading logic ...
        pass
    else:
        logger.error(
            f"Universe '{universe_key}' not found in CacheControl. "
            "Stock universes must be loaded via RelationshipCache."
        )
        return []
```

2. **Update Documentation**:
```python
class CacheControl:
    """
    Singleton class to manage cached application settings and themes.

    NOTE: As of Sprint 61, stock/ETF/universe loading has migrated to RelationshipCache.
    This class now handles:
    - app_settings (application configuration)
    - cache_config (cache configuration)
    - themes (custom stock groupings)

    For stock universes, ETF holdings, and sectors, use:
        from src.core.services.relationship_cache import get_relationship_cache
        cache = get_relationship_cache()
        symbols = cache.get_universe_symbols('nasdaq100')
    """
```

---

### Phase 4: Testing & Validation (1 hour)

**Test Cases**:

1. **Single Universe Loading**:
```python
# Test: Load NASDAQ-100
cache = get_relationship_cache()
symbols = cache.get_universe_symbols('nasdaq100')
assert len(symbols) == 102
assert 'AAPL' in symbols
```

2. **Multi-Universe Join**:
```python
# Test: Load sp500:nasdaq100 (distinct union)
symbols = cache.get_universe_symbols('sp500:nasdaq100')
assert len(symbols) > 505  # More than sp500 alone
assert len(symbols) < 607  # Less than sp500 + nasdaq100 (overlaps)
# Verify distinct
assert len(symbols) == len(set(symbols))
```

3. **ETF Holdings**:
```python
# Test: Load SPY ETF holdings
symbols = cache.get_universe_symbols('SPY')
assert len(symbols) == 504
assert 'AAPL' in symbols
```

4. **Direct Symbols**:
```python
# Test: Direct symbol list (no database query)
config = {
    'WEBSOCKET_CONNECTION_1_SYMBOLS': 'AAPL,NVDA,TSLA,MSFT'
}
# ... test connection config parsing ...
assert symbols == ['AAPL', 'NVDA', 'TSLA', 'MSFT']
```

5. **Cache Performance**:
```python
# Test: Verify caching works
import time

# First call (cache miss)
start = time.time()
symbols1 = cache.get_universe_symbols('sp500:nasdaq100')
elapsed_miss = time.time() - start

# Second call (cache hit)
start = time.time()
symbols2 = cache.get_universe_symbols('sp500:nasdaq100')
elapsed_hit = time.time() - start

assert symbols1 == symbols2
assert elapsed_hit < 0.001  # <1ms on cache hit
assert elapsed_miss > elapsed_hit  # Miss slower than hit
```

6. **Integration Test - WebSocket Connection 1**:
```bash
# .env configuration
USE_MULTI_CONNECTION=true
WEBSOCKET_CONNECTION_1_ENABLED=true
WEBSOCKET_CONNECTION_1_NAME=tech_primary
WEBSOCKET_CONNECTION_1_UNIVERSE_KEY=nasdaq100

# Expected: Connection 1 subscribes to 102 NASDAQ-100 symbols
# Verify in logs:
# "Connection 1 (tech_primary): Loaded 102 symbols from universe 'nasdaq100'"
```

---

### Phase 5: Documentation (30 minutes)

**Update Files**:

1. **`docs/architecture/websockets-integration.md`**:
   - Update "Symbol Loading Flow" to reference RelationshipCache
   - Add multi-universe join examples
   - Document migration from CacheControl

2. **`CLAUDE.md`**:
   - Add Sprint 61 status
   - Update universe loading examples

3. **`scripts/cache_maintenance/README.md`**:
   - Add note about WebSocket integration using RelationshipCache

---

## Configuration Examples

### Connection 1: Single Universe (NASDAQ-100)
```bash
WEBSOCKET_CONNECTION_1_ENABLED=true
WEBSOCKET_CONNECTION_1_NAME=nasdaq_primary
WEBSOCKET_CONNECTION_1_UNIVERSE_KEY=nasdaq100
# Result: 102 symbols
```

### Connection 1: Multi-Universe Join (S&P 500 + NASDAQ-100)
```bash
WEBSOCKET_CONNECTION_1_ENABLED=true
WEBSOCKET_CONNECTION_1_NAME=large_cap_combo
WEBSOCKET_CONNECTION_1_UNIVERSE_KEY=sp500:nasdaq100
# Result: ~550 distinct symbols (union with overlap removal)
```

### Connection 1: ETF Holdings (SPY)
```bash
WEBSOCKET_CONNECTION_1_ENABLED=true
WEBSOCKET_CONNECTION_1_NAME=spy_holdings
WEBSOCKET_CONNECTION_1_UNIVERSE_KEY=SPY
# Result: 504 symbols (SPY ETF holdings)
```

### Connection 1: Direct Symbols (Testing)
```bash
WEBSOCKET_CONNECTION_1_ENABLED=true
WEBSOCKET_CONNECTION_1_NAME=tech_leaders
WEBSOCKET_CONNECTION_1_SYMBOLS=AAPL,NVDA,TSLA,MSFT,GOOGL,META,AMZN
# Result: 7 symbols (direct list, no DB query)
```

### Multi-Connection Example (All 3 Connections)
```bash
USE_MULTI_CONNECTION=true
WEBSOCKET_CONNECTIONS_MAX=3

# Connection 1: Large cap tech
WEBSOCKET_CONNECTION_1_ENABLED=true
WEBSOCKET_CONNECTION_1_NAME=tech_primary
WEBSOCKET_CONNECTION_1_UNIVERSE_KEY=nasdaq100

# Connection 2: S&P 500
WEBSOCKET_CONNECTION_2_ENABLED=true
WEBSOCKET_CONNECTION_2_NAME=sp500_secondary
WEBSOCKET_CONNECTION_2_UNIVERSE_KEY=sp500

# Connection 3: Custom watchlist
WEBSOCKET_CONNECTION_3_ENABLED=true
WEBSOCKET_CONNECTION_3_NAME=custom_watchlist
WEBSOCKET_CONNECTION_3_SYMBOLS=AAPL,NVDA,TSLA,AMD,INTC
```

---

## Success Criteria

- [ ] RelationshipCache supports `get_universe_symbols(universe_key)`
- [ ] Single universe loading works: `nasdaq100` → 102 symbols
- [ ] Multi-universe join works: `sp500:nasdaq100` → ~550 distinct symbols
- [ ] ETF holdings loading works: `SPY` → 504 symbols
- [ ] Direct symbols loading works: `AAPL,NVDA,TSLA` → 3 symbols
- [ ] Cache performance: <1ms on cache hit
- [ ] WebSocket Connection 1 loads symbols via RelationshipCache
- [ ] CacheControl deprecation warnings added for stock universe methods
- [ ] Integration test passes with Connection 1 using `UNIVERSE_KEY`
- [ ] Documentation updated (websockets-integration.md, CLAUDE.md)
- [ ] Zero regression: Existing WebSocket functionality preserved

---

## Performance Targets

| Operation | Target | Notes |
|-----------|--------|-------|
| Single universe load (cache hit) | <1ms | In-memory cache |
| Single universe load (cache miss) | <50ms | Database query |
| Multi-universe join (cache hit) | <1ms | In-memory cache |
| Multi-universe join (cache miss) | <150ms | Multiple DB queries + union |
| Direct symbols parse | <0.1ms | String split only |

---

## Migration Path

### Week 1 (Sprint 61)
- ✅ Implement RelationshipCache universe loading
- ✅ Test with Connection 1 only
- ✅ Validate multi-universe join logic
- ✅ Update documentation

### Weeks 2-4 (Post-Sprint 61)
- Development and testing on Connection 1
- Refine universe configurations
- Monitor performance and cache hit rates
- Gather feedback for Connection 2/3 patterns

### Week 5+ (Future)
- Enable Connection 2 for sector-specific monitoring
- Enable Connection 3 for custom watchlists
- Full multi-connection deployment

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Universe key format mismatch | HIGH | Validate all existing universe keys in .env before migration |
| Multi-universe join performance | MEDIUM | Cache results, limit to 3 universes max per key |
| Database query overhead | MEDIUM | Use RelationshipCache TTL (1 hour), pre-warm on startup |
| Breaking existing connections | HIGH | Thorough testing, rollback plan, keep CacheControl as fallback |

---

## Rollback Plan

If critical issues arise:
1. Revert `multi_connection_manager.py` to use CacheControl
2. Keep RelationshipCache changes (non-breaking)
3. Re-enable in Sprint 62 after fixes

---

## Dependencies

- ✅ Sprint 59: Relational migration complete
- ✅ Sprint 60: RelationshipCache service available
- ⏳ Sprint 61: WebSocket integration update (this sprint)

---

## Questions for User

Before implementation:
1. ✅ Universe key format confirmed: `nasdaq100` (single), `sp500:nasdaq100` (join)
2. ✅ CacheControl migration confirmed: Fully migrate stocks to RelationshipCache
3. ✅ Scope confirmed: Multi-connection support, focus on Connection 1 development

---

**Ready to implement!**
