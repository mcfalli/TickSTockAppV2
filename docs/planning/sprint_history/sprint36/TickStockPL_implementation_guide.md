# TickStockPL Cache Sync Implementation Guide

**Sprint**: 36
**Date**: 2025-01-25
**Purpose**: Detailed implementation guide for migrating Cache Synchronization to TickStockPL

## File-by-File Migration Guide

### 1. Create Job Structure in TickStockPL

```python
# src/jobs/daily_cache_sync_job.py

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import asyncpg
from decimal import Decimal

@dataclass
class CacheChange:
    """Track individual cache changes"""
    change_type: str
    universe: str
    symbol: Optional[str]
    action: str  # added, removed, updated
    reason: str
    timestamp: datetime
    metadata: Dict[str, Any]

class DailyCacheSyncJob:
    """
    Daily Cache Synchronization Job for TickStockPL
    Manages cache_entries table with market-based universe organization
    """

    def __init__(self, db_pool: asyncpg.Pool, redis_client, progress_tracker=None):
        self.db_pool = db_pool
        self.redis = redis_client
        self.progress_tracker = progress_tracker
        self.logger = logging.getLogger(__name__)

        # Market cap thresholds (migrate from lines 69-75 of original)
        self.market_cap_thresholds = {
            'mega_cap': 200e9,
            'large_cap': 10e9,
            'mid_cap': 2e9,
            'small_cap': 300e6,
            'micro_cap': 50e6
        }

        # Universe size limits (migrate from lines 77-83)
        self.universe_limits = {
            'top_100': 100,
            'top_500': 500,
            'top_1000': 1000,
            'top_2000': 2000
        }

        # Redis channels for notifications
        self.channels = {
            'cache_sync_complete': 'tickstock:cache:sync_complete',
            'universe_updated': 'tickstock:universe:updated',
            'ipo_assignment': 'tickstock:cache:ipo_assignment',
            'delisting_cleanup': 'tickstock:cache:delisting_cleanup'
        }

    async def execute(self, run_id: str) -> Dict[str, Any]:
        """
        Main execution entry point for the job
        This replaces daily_cache_sync() from line 170
        """
        start_time = datetime.utcnow()
        self.logger.info(f"Starting cache synchronization for run {run_id}")

        try:
            # Initialize progress tracking
            if self.progress_tracker:
                await self.progress_tracker.init_phase(
                    run_id=run_id,
                    phase='cache_sync',
                    total_steps=5
                )

            results = await self.perform_synchronization(run_id)

            # Publish completion event
            await self.publish_completion(results)

            duration = (datetime.utcnow() - start_time).total_seconds()
            self.logger.info(f"Cache sync completed in {duration:.2f} seconds")

            return {
                'success': True,
                'run_id': run_id,
                'duration_seconds': duration,
                'changes': results['total_changes']
            }

        except Exception as e:
            self.logger.error(f"Cache sync failed: {str(e)}")
            return {
                'success': False,
                'run_id': run_id,
                'error': str(e)
            }
```

### 2. Migrate Core Synchronization Logic

Copy these key functions from `cache_entries_synchronizer.py`:

```python
# Continue in daily_cache_sync_job.py

    async def perform_synchronization(self, run_id: str) -> Dict[str, Any]:
        """
        Execute comprehensive cache_entries synchronization
        Migrated from line 203 of original file
        """
        sync_results = {
            'sync_start': datetime.utcnow().isoformat() + 'Z',
            'sync_status': 'in_progress',
            'task_results': {},
            'total_changes': 0,
            'errors': []
        }

        # Task 1: Market cap recalculation
        try:
            if self.progress_tracker:
                await self.progress_tracker.update_step(run_id, 'Market cap recalculation')

            market_changes = await self.market_cap_recalculation()
            sync_results['task_results']['market_cap_recalculation'] = {
                'status': 'success',
                'changes_count': len(market_changes),
                'changes': market_changes
            }
            sync_results['total_changes'] += len(market_changes)

        except Exception as e:
            self.logger.error(f"Market cap recalculation failed: {e}")
            sync_results['errors'].append(str(e))

        # Task 2: IPO universe assignment
        try:
            if self.progress_tracker:
                await self.progress_tracker.update_step(run_id, 'IPO assignment')

            ipo_changes = await self.ipo_universe_assignment()
            sync_results['task_results']['ipo_assignment'] = {
                'status': 'success',
                'changes_count': len(ipo_changes),
                'changes': ipo_changes
            }
            sync_results['total_changes'] += len(ipo_changes)

        except Exception as e:
            self.logger.error(f"IPO assignment failed: {e}")
            sync_results['errors'].append(str(e))

        # Task 3: Delisted stock cleanup
        try:
            if self.progress_tracker:
                await self.progress_tracker.update_step(run_id, 'Delisted cleanup')

            delisted_changes = await self.delisted_cleanup()
            sync_results['task_results']['delisted_cleanup'] = {
                'status': 'success',
                'changes_count': len(delisted_changes),
                'changes': delisted_changes
            }
            sync_results['total_changes'] += len(delisted_changes)

        except Exception as e:
            self.logger.error(f"Delisted cleanup failed: {e}")
            sync_results['errors'].append(str(e))

        sync_results['sync_end'] = datetime.utcnow().isoformat() + 'Z'
        sync_results['sync_status'] = 'completed' if not sync_results['errors'] else 'completed_with_errors'

        return sync_results

    async def market_cap_recalculation(self) -> List[CacheChange]:
        """
        Update universe memberships based on market cap changes
        Migrated from line 268 of original file
        """
        changes = []

        async with self.db_pool.acquire() as conn:
            # Get all active symbols with market caps
            query = """
                SELECT s.symbol, s.market_cap, s.sector
                FROM symbols s
                WHERE s.is_active = true
                  AND s.market_cap IS NOT NULL
                  AND s.market_cap > 0
                ORDER BY s.market_cap DESC
            """
            symbols = await conn.fetch(query)

            # Categorize by market cap
            market_cap_groups = {
                'mega_cap': [],
                'large_cap': [],
                'mid_cap': [],
                'small_cap': [],
                'micro_cap': []
            }

            for symbol in symbols:
                market_cap = float(symbol['market_cap'])
                symbol_name = symbol['symbol']

                if market_cap >= self.market_cap_thresholds['mega_cap']:
                    market_cap_groups['mega_cap'].append(symbol_name)
                elif market_cap >= self.market_cap_thresholds['large_cap']:
                    market_cap_groups['large_cap'].append(symbol_name)
                elif market_cap >= self.market_cap_thresholds['mid_cap']:
                    market_cap_groups['mid_cap'].append(symbol_name)
                elif market_cap >= self.market_cap_thresholds['small_cap']:
                    market_cap_groups['small_cap'].append(symbol_name)
                elif market_cap >= self.market_cap_thresholds['micro_cap']:
                    market_cap_groups['micro_cap'].append(symbol_name)

            # Update cache_entries for each group
            for group_name, group_symbols in market_cap_groups.items():
                if group_symbols:
                    content = {
                        'symbols': group_symbols,
                        'count': len(group_symbols),
                        'last_updated': datetime.utcnow().isoformat() + 'Z',
                        'metadata': {
                            'market_cap_range': group_name,
                            'type': 'market_cap_category'
                        }
                    }

                    # Update or insert cache entry
                    await conn.execute("""
                        INSERT INTO cache_entries (universe, content, cache_type, updated_at)
                        VALUES ($1, $2, 'market_cap', NOW())
                        ON CONFLICT (universe)
                        DO UPDATE SET
                            content = $2,
                            updated_at = NOW()
                    """, group_name, json.dumps(content))

                    changes.append(CacheChange(
                        change_type='market_cap_update',
                        universe=group_name,
                        symbol=None,
                        action='updated',
                        reason=f'Market cap recalculation: {len(group_symbols)} symbols',
                        timestamp=datetime.utcnow(),
                        metadata={'count': len(group_symbols)}
                    ))

            # Create top_N universes
            for limit_name, limit_value in self.universe_limits.items():
                top_symbols = [s['symbol'] for s in symbols[:limit_value]]

                content = {
                    'symbols': top_symbols,
                    'count': len(top_symbols),
                    'last_updated': datetime.utcnow().isoformat() + 'Z',
                    'metadata': {
                        'type': 'market_leader',
                        'rank': limit_name
                    }
                }

                await conn.execute("""
                    INSERT INTO cache_entries (universe, content, cache_type, updated_at)
                    VALUES ($1, $2, 'market_leader', NOW())
                    ON CONFLICT (universe)
                    DO UPDATE SET
                        content = $2,
                        updated_at = NOW()
                """, limit_name, json.dumps(content))

                changes.append(CacheChange(
                    change_type='market_leader_update',
                    universe=limit_name,
                    symbol=None,
                    action='updated',
                    reason=f'Top {limit_value} by market cap',
                    timestamp=datetime.utcnow(),
                    metadata={'count': len(top_symbols)}
                ))

        return changes
```

### 3. Add IPO and Delisting Functions

```python
# Continue in daily_cache_sync_job.py

    async def ipo_universe_assignment(self) -> List[CacheChange]:
        """
        Automatically assign new IPOs to appropriate themes
        Migrated from line 378 of original file
        """
        changes = []

        async with self.db_pool.acquire() as conn:
            # Find new IPOs (listed in last 30 days)
            query = """
                SELECT symbol, company_name, market_cap, sector, listing_date
                FROM symbols
                WHERE is_active = true
                  AND listing_date >= NOW() - INTERVAL '30 days'
                  AND symbol NOT IN (
                      SELECT DISTINCT jsonb_array_elements_text(content->'symbols')
                      FROM cache_entries
                      WHERE cache_type = 'ipo'
                  )
            """
            new_ipos = await conn.fetch(query)

            if new_ipos:
                # Add to IPO universe
                ipo_symbols = [ipo['symbol'] for ipo in new_ipos]

                content = {
                    'symbols': ipo_symbols,
                    'count': len(ipo_symbols),
                    'last_updated': datetime.utcnow().isoformat() + 'Z',
                    'metadata': {
                        'type': 'ipo',
                        'period': 'last_30_days'
                    }
                }

                await conn.execute("""
                    INSERT INTO cache_entries (universe, content, cache_type, updated_at)
                    VALUES ('recent_ipos', $1, 'ipo', NOW())
                    ON CONFLICT (universe)
                    DO UPDATE SET
                        content = $1,
                        updated_at = NOW()
                """, json.dumps(content))

                for ipo in new_ipos:
                    changes.append(CacheChange(
                        change_type='ipo_assignment',
                        universe='recent_ipos',
                        symbol=ipo['symbol'],
                        action='added',
                        reason=f"New IPO: {ipo['company_name']}",
                        timestamp=datetime.utcnow(),
                        metadata={
                            'listing_date': ipo['listing_date'].isoformat(),
                            'sector': ipo['sector']
                        }
                    ))

        return changes

    async def delisted_cleanup(self) -> List[CacheChange]:
        """
        Remove delisted stocks from universes
        Migrated from line 497 of original file
        """
        changes = []

        async with self.db_pool.acquire() as conn:
            # Find delisted stocks
            query = """
                SELECT symbol
                FROM symbols
                WHERE is_active = false
                  OR delisted_date IS NOT NULL
            """
            delisted = await conn.fetch(query)
            delisted_symbols = [d['symbol'] for d in delisted]

            if delisted_symbols:
                # Remove from all cache_entries
                all_universes = await conn.fetch("""
                    SELECT universe, content
                    FROM cache_entries
                    WHERE cache_type IN ('market_cap', 'market_leader', 'sector', 'theme')
                """)

                for universe in all_universes:
                    content = json.loads(universe['content'])
                    original_symbols = content.get('symbols', [])

                    # Remove delisted symbols
                    cleaned_symbols = [s for s in original_symbols if s not in delisted_symbols]

                    if len(cleaned_symbols) < len(original_symbols):
                        content['symbols'] = cleaned_symbols
                        content['count'] = len(cleaned_symbols)
                        content['last_updated'] = datetime.utcnow().isoformat() + 'Z'

                        await conn.execute("""
                            UPDATE cache_entries
                            SET content = $1, updated_at = NOW()
                            WHERE universe = $2
                        """, json.dumps(content), universe['universe'])

                        removed_count = len(original_symbols) - len(cleaned_symbols)
                        changes.append(CacheChange(
                            change_type='delisted_cleanup',
                            universe=universe['universe'],
                            symbol=None,
                            action='cleaned',
                            reason=f'Removed {removed_count} delisted symbols',
                            timestamp=datetime.utcnow(),
                            metadata={'removed_count': removed_count}
                        ))

        return changes
```

### 4. Add Redis Publishing Functions

```python
# Continue in daily_cache_sync_job.py

    async def publish_completion(self, results: Dict[str, Any]):
        """
        Publish sync completion events to Redis for TickStockAppV2
        """
        # Main completion event
        completion_event = {
            'event': 'cache_sync_completed',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'source': 'daily_cache_sync_job',
            'version': '1.0',
            'payload': {
                'total_changes': results.get('total_changes', 0),
                'sync_status': results.get('sync_status', 'unknown'),
                'task_results': {
                    task: {
                        'status': result.get('status'),
                        'changes': result.get('changes_count', 0)
                    }
                    for task, result in results.get('task_results', {}).items()
                }
            }
        }

        await self.redis.publish(
            self.channels['cache_sync_complete'],
            json.dumps(completion_event)
        )

        # Publish individual universe updates
        for task_name, task_result in results.get('task_results', {}).items():
            if task_result.get('changes'):
                for change in task_result['changes'][:10]:  # Limit to 10 notifications
                    universe_event = {
                        'event': 'universe_updated',
                        'timestamp': datetime.utcnow().isoformat() + 'Z',
                        'source': 'daily_cache_sync_job',
                        'version': '1.0',
                        'payload': {
                            'universe': change.universe,
                            'action': change.action,
                            'reason': change.reason,
                            'metadata': change.metadata
                        }
                    }

                    await self.redis.publish(
                        self.channels['universe_updated'],
                        json.dumps(universe_event)
                    )
```

### 5. Integration with Daily Processing

```python
# src/services/daily_processing_coordinator.py (or wherever your coordinator is)

from src.jobs.daily_cache_sync_job import DailyCacheSyncJob

class DailyProcessingCoordinator:

    async def run_phase_2_5_cache_sync(self, run_id: str):
        """
        Phase 2.5: Cache Synchronization
        Runs after data import, before indicator processing
        """
        self.logger.info(f"Starting Phase 2.5: Cache Synchronization for run {run_id}")

        try:
            # Initialize the job
            cache_sync_job = DailyCacheSyncJob(
                db_pool=self.db_pool,
                redis_client=self.redis_client,
                progress_tracker=self.progress_tracker
            )

            # Execute the job
            result = await cache_sync_job.execute(run_id)

            if result['success']:
                self.logger.info(f"Cache sync completed: {result['changes']} changes made")

                # Publish phase completion event
                await self.publish_phase_completion(
                    run_id=run_id,
                    phase='cache_sync',
                    status='completed',
                    stats=result
                )
            else:
                self.logger.error(f"Cache sync failed: {result.get('error')}")
                raise Exception(f"Cache sync failed: {result.get('error')}")

        except Exception as e:
            self.logger.error(f"Phase 2.5 failed: {str(e)}")
            await self.publish_phase_completion(
                run_id=run_id,
                phase='cache_sync',
                status='failed',
                error=str(e)
            )
            raise
```

### 6. Add API Endpoints

```python
# src/api/processing/cache_sync_endpoints.py

from flask import Blueprint, jsonify, request
from src.jobs.daily_cache_sync_job import DailyCacheSyncJob
import asyncio
import uuid

cache_sync_bp = Blueprint('cache_sync', __name__)

@cache_sync_bp.route('/api/processing/cache-sync/trigger', methods=['POST'])
async def trigger_cache_sync():
    """
    Manual trigger for cache synchronization
    Called by TickStockAppV2 admin interface
    """
    try:
        data = request.json or {}

        # Generate run ID
        run_id = f"manual-cache-sync-{uuid.uuid4().hex[:8]}"

        # Get database and redis connections
        db_pool = current_app.db_pool
        redis_client = current_app.redis_client

        # Create and execute job
        job = DailyCacheSyncJob(db_pool, redis_client)

        # Run in background
        asyncio.create_task(job.execute(run_id))

        return jsonify({
            'success': True,
            'run_id': run_id,
            'message': 'Cache synchronization started'
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@cache_sync_bp.route('/api/processing/cache-sync/status/<run_id>', methods=['GET'])
async def get_cache_sync_status(run_id):
    """Get status of a cache sync run"""
    try:
        # Query progress from your tracking system
        status = await get_job_progress(run_id)

        return jsonify({
            'success': True,
            'run_id': run_id,
            'status': status
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
```

## Next Steps

1. Copy the original `cache_entries_synchronizer.py` file for reference
2. Implement the job following this guide
3. Test with a subset of data first
4. Integrate with your daily processing pipeline
5. Add monitoring and alerting
6. Create the callback documentation for TickStockAppV2

## Important Notes

- The job reads from `symbols` and `ohlcv_daily` tables
- It writes to `cache_entries` table
- It publishes to Redis for TickStockAppV2 notifications
- Should run AFTER data import but BEFORE pattern detection
- Expected runtime: 5-30 minutes depending on data size