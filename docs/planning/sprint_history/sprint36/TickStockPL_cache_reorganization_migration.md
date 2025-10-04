# TickStockPL Cache Reorganization Migration Instructions

**Sprint**: 36
**Date**: 2025-01-25
**Purpose**: Migrate Cache Entries Synchronization job from TickStockAppV2 to TickStockPL

## Overview

The Cache Entries Synchronization system currently resides in TickStockAppV2 but belongs in TickStockPL as it's a data processing job that manages database tables. This migration will move the functionality to TickStockPL's daily processing pipeline.

## Current Location in TickStockAppV2

| Component | Path | Description |
|-----------|------|-------------|
| Core Service | `src/data/cache_entries_synchronizer.py` | Main synchronization class (881 lines) |
| Run Script | `scripts/cache_management/run_cache_synchronization.py` | Execution wrapper |
| Admin Integration | `src/api/rest/admin_historical_data.py` (Lines 645-685) | Admin UI trigger |
| Documentation | `docs/operations/cache-synchronization-guide.md` | Operations guide |

## What This Job Does

The Cache Entries Synchronizer manages the `cache_entries` table which organizes stocks into logical universes:

1. **Market Cap Categories**: mega_cap, large_cap, mid_cap, small_cap, micro_cap
2. **Top Rankings**: top_100, top_500, top_1000, top_2000
3. **Sector Leaders**: Top 10 stocks per sector
4. **Themes**: AI, Biotech, Cloud, Crypto, Dividend Aristocrats, etc.
5. **IPO Management**: Auto-assigns new IPOs to appropriate themes
6. **Delisted Cleanup**: Removes inactive stocks while preserving history

## Migration Steps

### Step 1: Copy Core Implementation

Copy the main synchronizer to TickStockPL:

```bash
# Source (TickStockAppV2)
src/data/cache_entries_synchronizer.py

# Destination (TickStockPL)
src/jobs/daily_cache_sync_job.py
```

### Step 2: Refactor for TickStockPL Architecture

#### 2.1 Update Class Name and Structure

```python
# Original (TickStockAppV2)
class CacheEntriesSynchronizer:
    def __init__(self, database_uri: str = None, redis_host: str = None):
        ...

# New (TickStockPL)
class DailyCacheSyncJob:
    def __init__(self, db_pool, redis_client, progress_tracker=None):
        self.db_pool = db_pool
        self.redis = redis_client
        self.progress_tracker = progress_tracker
        ...
```

#### 2.2 Integration Points

The job should integrate with your existing daily processing pipeline:

```python
# In your daily_processing_coordinator.py or similar

async def run_daily_processing(run_id: str):
    # Phase 1: Schedule & Monitor
    await run_scheduling_phase(run_id)

    # Phase 2: Data Import
    await run_data_import(run_id)

    # Phase 2.5: Cache Synchronization (NEW)
    await run_cache_synchronization(run_id)

    # Phase 3: Indicators
    await run_indicator_processing(run_id)

    # Phase 4: Patterns
    await run_pattern_detection(run_id)
```

### Step 3: Key Functions to Migrate

#### 3.1 Main Entry Points

| Function | Line | Purpose |
|----------|------|---------|
| `daily_cache_sync()` | 170 | Main daily synchronization after EOD |
| `perform_synchronization()` | 203 | Execute comprehensive sync |
| `market_cap_recalculation()` | 268 | Update universe memberships |
| `ipo_universe_assignment()` | 378 | Assign new IPOs to themes |
| `delisted_cleanup()` | 497 | Remove inactive stocks |
| `theme_rebalancing()` | 596 | Rebalance theme universes |

#### 3.2 Database Operations

The job needs these database operations:

```python
# Read operations
- SELECT from symbols (market cap, sector, listing date)
- SELECT from ohlcv_daily (latest close prices)

# Write operations
- DELETE from cache_entries (cleanup)
- INSERT into cache_entries (new universes)
- UPDATE cache_entries_metadata (statistics)
```

### Step 4: Configuration Migration

Add these configurations to TickStockPL's config:

```python
# config/cache_sync_config.py

CACHE_SYNC_CONFIG = {
    'market_cap_thresholds': {
        'mega_cap': 200e9,      # $200B+
        'large_cap': 10e9,      # $10B - $200B
        'mid_cap': 2e9,         # $2B - $10B
        'small_cap': 300e6,     # $300M - $2B
        'micro_cap': 50e6       # $50M - $300M
    },

    'universe_limits': {
        'top_100': 100,
        'top_500': 500,
        'top_1000': 1000,
        'top_2000': 2000
    },

    'sync_settings': {
        'timeout_minutes': 30,
        'eod_wait_timeout_seconds': 3600,
        'batch_size': 1000,
        'enable_notifications': True
    },

    'themes': [
        'ai_ml_leaders',
        'biotech_innovators',
        'cloud_computing',
        'crypto_blockchain',
        'dividend_aristocrats',
        'esg_leaders',
        'fintech_disruptors',
        'green_energy',
        'technology_leaders'
    ]
}
```

### Step 5: Redis Event Publishing

Maintain these Redis channels for TickStockAppV2 notifications:

```python
# Redis channels to publish to
CACHE_SYNC_CHANNELS = {
    'sync_complete': 'tickstock:cache:sync_complete',
    'universe_updated': 'tickstock:universe:updated',
    'ipo_assignment': 'tickstock:cache:ipo_assignment',
    'delisting_cleanup': 'tickstock:cache:delisting_cleanup'
}

# Example event publishing
async def publish_sync_complete(redis_client, stats):
    event = {
        'event': 'cache_sync_completed',
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'source': 'daily_cache_sync_job',
        'version': '1.0',
        'payload': {
            'total_changes': stats['total_changes'],
            'universes_updated': stats['universes_updated'],
            'duration_seconds': stats['duration_seconds']
        }
    }
    await redis_client.publish(CACHE_SYNC_CHANNELS['sync_complete'], json.dumps(event))
```

### Step 6: Progress Tracking Integration

Integrate with TickStockPL's job progress tracking:

```python
async def run_with_progress(self, run_id: str):
    """Run cache sync with progress tracking"""

    # Report start
    await self.progress_tracker.update(
        run_id=run_id,
        phase='cache_sync',
        status='started',
        total_items=5,  # 5 sub-tasks
        completed=0
    )

    # Market cap recalculation
    await self.progress_tracker.update(
        run_id=run_id,
        phase='cache_sync',
        current_task='market_cap_recalculation',
        completed=1
    )
    changes = await self.market_cap_recalculation()

    # IPO assignment
    await self.progress_tracker.update(
        run_id=run_id,
        phase='cache_sync',
        current_task='ipo_assignment',
        completed=2
    )
    ipo_changes = await self.ipo_universe_assignment()

    # Continue for other tasks...
```

### Step 7: Create API Endpoint for Manual Trigger

Add to TickStockPL's API:

```python
# src/api/cache_sync_api.py

@app.route('/api/processing/cache-sync/trigger', methods=['POST'])
@require_api_key
async def trigger_cache_sync():
    """Manual trigger for cache synchronization"""

    data = request.json or {}

    # Create job
    job_id = str(uuid.uuid4())
    job = DailyCacheSyncJob(db_pool, redis_client)

    # Run async
    asyncio.create_task(job.run_with_progress(job_id))

    return jsonify({
        'success': True,
        'job_id': job_id,
        'message': 'Cache synchronization started'
    })

@app.route('/api/processing/cache-sync/status/<job_id>')
@require_api_key
async def get_cache_sync_status(job_id):
    """Get status of cache sync job"""

    status = await get_job_status(job_id)
    return jsonify(status)
```

### Step 8: Testing Considerations

Reference test files are being moved to the sprint36 folder for your reference:
- `tests/sprint36/reference/test_cache_entries_synchronizer.py`
- `tests/sprint36/reference/test_cache_sync_integration.py`

Create new tests in TickStockPL:
```python
# tests/jobs/test_daily_cache_sync_job.py

async def test_market_cap_recalculation():
    """Test market cap-based universe updates"""
    ...

async def test_ipo_assignment():
    """Test new IPO detection and assignment"""
    ...

async def test_delisted_cleanup():
    """Test removal of delisted stocks"""
    ...
```

### Step 9: Database Schema Reference

The `cache_entries` table structure:

```sql
CREATE TABLE cache_entries (
    id SERIAL PRIMARY KEY,
    universe VARCHAR(100) NOT NULL,
    content JSONB NOT NULL,
    cache_type VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(universe)
);

-- Content structure for stock universes:
{
    "symbols": ["AAPL", "GOOGL", "MSFT", ...],
    "count": 100,
    "last_updated": "2025-01-25T10:00:00Z",
    "metadata": {
        "market_cap_range": "mega_cap",
        "sector": "Technology",
        ...
    }
}
```

## Step 10: IMPORTANT - Return Integration Instructions

**After completing the migration to TickStockPL, you MUST provide:**

### 10.1 Integration Instructions for TickStockAppV2

Create a file named `TickStockAppV2_integration_callback.md` with:

1. **New API Endpoints** in TickStockPL:
   - Endpoint URL for manual trigger
   - Required headers/authentication
   - Request/response format

2. **Updated Admin Page Integration**:
   ```python
   # Example code for admin_historical_data.py
   def trigger_cache_sync():
       """Call TickStockPL's cache sync API"""
       response = requests.post(
           'http://tickstockpl:8080/api/processing/cache-sync/trigger',
           headers={'X-API-Key': API_KEY},
           json={'mode': 'full'}
       )
       return response.json()
   ```

3. **Redis Events to Subscribe**:
   - New event formats
   - Channel names
   - How to display progress in admin UI

### 10.2 Cleanup Instructions for TickStockAppV2

Files to DELETE after successful migration:
- `src/data/cache_entries_synchronizer.py`
- `src/core/services/cache_entries_synchronizer.py` (if exists)
- `scripts/cache_management/run_cache_synchronization.py`
- Remove cache sync button/logic from `src/api/rest/admin_historical_data.py` (Lines 645-685)

Files to UPDATE:
- `src/api/rest/admin_historical_data.py` - Replace local call with API call to TickStockPL
- `web/templates/admin/historical_data_dashboard.html` - Update button to call new endpoint

### 10.3 Testing Checklist

Before marking migration complete:
- [ ] Cache sync runs successfully in TickStockPL
- [ ] Redis events are published and received by TickStockAppV2
- [ ] Manual trigger from admin page works
- [ ] All universes are correctly populated
- [ ] Performance is acceptable (<30 minutes for full sync)
- [ ] Logs are properly captured in TickStockPL
- [ ] Old code can be safely removed from TickStockAppV2

## Timeline Expectations

- **Migration to TickStockPL**: 2-3 days
- **Testing & Validation**: 1-2 days
- **Integration with TickStockAppV2**: 1 day
- **Cleanup & Documentation**: 1 day

Total: ~1 week

## Questions for TickStockPL Developer

1. Should this run as Phase 2.5 or be merged into Phase 2?
2. Do you want to keep the 30-minute timeout or adjust?
3. Should we add this to the scheduler for automatic daily runs?
4. Any specific logging format requirements?

## Contact

When complete, provide the `TickStockAppV2_integration_callback.md` file so we can:
1. Update the admin interface to use the new API
2. Remove the old code from TickStockAppV2
3. Test the complete integration