#!/usr/bin/env python3
"""
Cache Entries Synchronization System - Sprint 14 Phase 3

This service manages intelligent cache_entries synchronization with market conditions:
- Daily cache synchronization after EOD data updates
- Market cap recalculation and automatic universe membership updates
- IPO universe assignment and delisted stock cleanup
- Real-time synchronization notifications via Redis to TickStockApp
- Theme rebalancing based on market condition changes

Architecture:
- Runs as part of data management pipeline after EOD processing
- Full database access for cache_entries management and updates
- Redis pub-sub notifications for real-time TickStockApp updates
- Integration with EOD completion signals for automated triggering
- 30-minute completion window for daily synchronization operations
"""

import os
import sys
import asyncio
import json
import logging
import redis.asyncio as redis
from datetime import datetime, timedelta, time as dt_time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import psycopg2
import psycopg2.extras
from decimal import Decimal

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

@dataclass
class SynchronizationChange:
    """Synchronization change tracking"""
    change_type: str
    universe: str
    symbol: Optional[str]
    action: str  # added, removed, updated
    reason: str
    timestamp: datetime
    metadata: Dict[str, Any]

class CacheEntriesSynchronizer:
    """
    Cache Entries Synchronization System
    
    Manages intelligent synchronization of cache_entries with market conditions:
    - Automated daily synchronization triggered by EOD completion
    - Market cap-based universe membership updates (top_500, top_1000, etc.)
    - New IPO automatic assignment to appropriate themes
    - Delisted stock cleanup with historical data preservation
    - Real-time change notifications to TickStockApp via Redis
    """
    
    def __init__(self, database_uri: str = None, redis_host: str = None):
        """Initialize cache entries synchronizer"""
        self.database_uri = database_uri or os.getenv(
            'DATABASE_URL',
            'postgresql://app_readwrite:4pp_U$3r_2024!@localhost/tickstock'
        )
        self.redis_host = redis_host or os.getenv('REDIS_HOST', 'localhost')
        self.redis_port = int(os.getenv('REDIS_PORT', '6379'))
        
        # Market cap thresholds for universe classification
        self.market_cap_thresholds = {
            'mega_cap': 200e9,      # $200B+
            'large_cap': 10e9,      # $10B - $200B
            'mid_cap': 2e9,         # $2B - $10B
            'small_cap': 300e6,     # $300M - $2B
            'micro_cap': 50e6       # $50M - $300M
        }
        
        # Universe size limits
        self.universe_limits = {
            'top_100': 100,
            'top_500': 500,
            'top_1000': 1000,
            'top_2000': 2000
        }
        
        # Redis channels for synchronization notifications
        self.channels = {
            'cache_sync_complete': 'tickstock.cache.sync_complete',
            'universe_updated': 'tickstock.universe.updated',
            'ipo_assignment': 'tickstock.cache.ipo_assignment',
            'delisting_cleanup': 'tickstock.cache.delisting_cleanup'
        }
        
        # Synchronization timing
        self.sync_timeout_minutes = 30
        self.eod_wait_timeout_seconds = 3600  # 1 hour max wait for EOD
        
        # Initialize logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
    def get_database_connection(self):
        """Get PostgreSQL database connection"""
        try:
            conn = psycopg2.connect(
                self.database_uri,
                cursor_factory=psycopg2.extras.RealDictCursor
            )
            return conn
        except Exception as e:
            self.logger.error(f"- Database connection failed: {e}")
            return None
    
    async def connect_redis(self) -> Optional[redis.Redis]:
        """Establish Redis connection for pub-sub operations"""
        try:
            redis_client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                decode_responses=True,
                health_check_interval=30
            )
            
            await redis_client.ping()
            self.logger.info(f"+ Redis connected: {self.redis_host}:{self.redis_port}")
            return redis_client
            
        except Exception as e:
            self.logger.error(f"- Redis connection failed: {e}")
            return None
    
    async def wait_for_eod_completion(self) -> bool:
        """
        Wait for EOD processing completion signal via Redis
        
        Returns:
            True if EOD completion received, False if timeout
        """
        redis_client = await self.connect_redis()
        if not redis_client:
            self.logger.warning("- Cannot wait for EOD signal: Redis unavailable, proceeding anyway")
            return True  # Proceed even without Redis
        
        try:
            self.logger.info(f"+ Waiting for EOD completion signal (timeout: {self.eod_wait_timeout_seconds}s)")
            
            # Listen for EOD completion on multiple possible channels
            eod_channels = ['eod_complete', 'tickstock.eod.complete', 'market_data.eod_complete']
            
            # Use blpop to wait for signal with timeout
            result = await redis_client.blpop(eod_channels, timeout=self.eod_wait_timeout_seconds)
            
            if result:
                channel, message = result
                self.logger.info(f"+ EOD completion signal received on channel: {channel}")
                return True
            else:
                self.logger.warning("- EOD completion timeout, proceeding with synchronization")
                return True  # Proceed even on timeout
                
        except Exception as e:
            self.logger.error(f"- Error waiting for EOD signal: {e}")
            return True  # Proceed on error
        finally:
            if redis_client:
                await redis_client.aclose()
    
    async def daily_cache_sync(self) -> Dict[str, Any]:
        """
        Perform daily cache_entries synchronization after EOD completion
        
        Returns:
            Comprehensive synchronization results
        """
        sync_start = datetime.now()
        self.logger.info("=== Starting Daily Cache Synchronization ===")
        
        # Wait for EOD completion signal
        eod_received = await self.wait_for_eod_completion()
        if not eod_received:
            return {'error': 'EOD completion signal timeout'}
        
        # Perform comprehensive synchronization
        sync_results = await self.perform_synchronization()
        
        # Calculate total sync time
        sync_duration = (datetime.now() - sync_start).total_seconds()
        sync_results['total_sync_duration_minutes'] = sync_duration / 60
        
        # Check if within time window
        within_window = sync_duration <= (self.sync_timeout_minutes * 60)
        sync_results['within_time_window'] = within_window
        
        if within_window:
            self.logger.info(f"+ Daily synchronization complete in {sync_duration/60:.1f} minutes")
        else:
            self.logger.warning(f"- Synchronization exceeded {self.sync_timeout_minutes}min window: {sync_duration/60:.1f}min")
        
        return sync_results
    
    async def perform_synchronization(self) -> Dict[str, Any]:
        """
        Execute comprehensive cache_entries synchronization
        
        Returns:
            Detailed synchronization results with change tracking
        """
        self.logger.info("+ Executing comprehensive synchronization tasks")
        
        # Define synchronization tasks
        sync_tasks = [
            ('market_cap_recalculation', self.market_cap_recalculation),
            ('ipo_universe_assignment', self.ipo_universe_assignment),  
            ('delisted_cleanup', self.delisted_cleanup),
            ('theme_rebalancing', self.theme_rebalancing),
            ('etf_universe_maintenance', self.etf_universe_maintenance)
        ]
        
        all_changes = []
        task_results = {}
        
        # Execute each synchronization task
        for task_name, task_func in sync_tasks:
            task_start = datetime.now()
            self.logger.info(f"+ Starting task: {task_name}")
            
            try:
                changes = await task_func()
                task_duration = (datetime.now() - task_start).total_seconds()
                
                task_results[task_name] = {
                    'status': 'completed',
                    'changes_count': len(changes) if changes else 0,
                    'duration_seconds': task_duration,
                    'changes': changes
                }
                
                if changes:
                    all_changes.extend(changes)
                    self.logger.info(f"+ {task_name}: {len(changes)} changes in {task_duration:.1f}s")
                else:
                    self.logger.info(f"+ {task_name}: No changes needed in {task_duration:.1f}s")
                    
            except Exception as e:
                self.logger.error(f"- {task_name} failed: {e}")
                task_results[task_name] = {
                    'status': 'failed',
                    'error': str(e),
                    'duration_seconds': (datetime.now() - task_start).total_seconds()
                }
        
        # Log all changes to database
        await self.log_sync_changes(all_changes)
        
        # Publish synchronization completion notifications
        await self.publish_sync_notifications(all_changes, task_results)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'total_changes': len(all_changes),
            'task_results': task_results,
            'changes_summary': self.generate_change_summary(all_changes),
            'sync_status': 'completed'
        }
    
    async def market_cap_recalculation(self) -> List[SynchronizationChange]:
        """
        Update universe memberships based on market cap changes
        
        Returns:
            List of changes made to market cap-based universes
        """
        changes = []
        conn = self.get_database_connection()
        if not conn:
            return changes
        
        try:
            cursor = conn.cursor()
            
            # Get current market cap rankings
            ranking_query = """
            SELECT s.symbol, s.market_cap, s.sector, s.name,
                   ROW_NUMBER() OVER (ORDER BY s.market_cap DESC NULLS LAST) as rank
            FROM symbols s
            WHERE s.active = true 
            AND s.market_cap > 0
            AND s.type IN ('CS', 'ETF')
            ORDER BY s.market_cap DESC NULLS LAST
            """
            
            cursor.execute(ranking_query)
            current_rankings = cursor.fetchall()
            
            self.logger.info(f"+ Processing market cap updates for {len(current_rankings)} symbols")
            
            # Define universe updates based on rankings
            universes_to_update = []
            
            # Size-based universes
            if len(current_rankings) >= 100:
                universes_to_update.append(('top_100', current_rankings[:100]))
            if len(current_rankings) >= 500:
                universes_to_update.append(('top_500', current_rankings[:500]))
            if len(current_rankings) >= 1000:
                universes_to_update.append(('top_1000', current_rankings[:1000]))
            if len(current_rankings) >= 2000:
                universes_to_update.append(('top_2000', current_rankings[:2000]))
            
            # Market cap category universes
            large_cap = [r for r in current_rankings if r['market_cap'] >= self.market_cap_thresholds['large_cap']]
            mid_cap = [r for r in current_rankings if 
                      self.market_cap_thresholds['mid_cap'] <= r['market_cap'] < self.market_cap_thresholds['large_cap']]
            small_cap = [r for r in current_rankings if 
                        self.market_cap_thresholds['small_cap'] <= r['market_cap'] < self.market_cap_thresholds['mid_cap']]
            
            if large_cap:
                universes_to_update.append(('large_cap', large_cap))
            if mid_cap:
                universes_to_update.append(('mid_cap', mid_cap))
            if small_cap:
                universes_to_update.append(('small_cap', small_cap))
            
            # Process each universe update
            for universe_name, ranked_symbols in universes_to_update:
                old_symbols = self.get_current_universe_symbols(cursor, universe_name)
                new_symbols = [s['symbol'] for s in ranked_symbols]
                
                if set(old_symbols) != set(new_symbols):
                    # Calculate changes
                    added_symbols = set(new_symbols) - set(old_symbols)
                    removed_symbols = set(old_symbols) - set(new_symbols)
                    
                    # Update the universe
                    self.update_universe_symbols(cursor, universe_name, new_symbols, {
                        'update_type': 'market_cap_recalculation',
                        'total_symbols': len(new_symbols),
                        'criteria': f'Market cap ranking, updated {datetime.now().isoformat()}'
                    })
                    
                    # Track changes
                    for symbol in added_symbols:
                        changes.append(SynchronizationChange(
                            change_type='market_cap_update',
                            universe=universe_name,
                            symbol=symbol,
                            action='added',
                            reason=f'Market cap ranking qualified for {universe_name}',
                            timestamp=datetime.now(),
                            metadata={'market_cap_rank': next((r['rank'] for r in ranked_symbols if r['symbol'] == symbol), None)}
                        ))
                    
                    for symbol in removed_symbols:
                        changes.append(SynchronizationChange(
                            change_type='market_cap_update',
                            universe=universe_name,
                            symbol=symbol,
                            action='removed',
                            reason=f'Market cap ranking no longer qualifies for {universe_name}',
                            timestamp=datetime.now(),
                            metadata={'reason': 'market_cap_drop'}
                        ))
            
            conn.commit()
            self.logger.info(f"+ Market cap recalculation complete: {len(changes)} changes")
            
        except Exception as e:
            conn.rollback()
            self.logger.error(f"- Market cap recalculation failed: {e}")
        finally:
            if conn:
                conn.close()
        
        return changes
    
    async def ipo_universe_assignment(self) -> List[SynchronizationChange]:
        """
        Automatically assign new IPOs to appropriate cache_entries themes
        
        Returns:
            List of IPO assignment changes
        """
        changes = []
        conn = self.get_database_connection()
        if not conn:
            return changes
        
        try:
            cursor = conn.cursor()
            
            # Get unassigned IPOs from last 30 days
            ipo_query = """
            SELECT s.symbol, s.sector, s.market_cap, s.industry, s.name, s.type
            FROM symbols s
            WHERE s.initial_load_date >= CURRENT_DATE - INTERVAL '30 days'
            AND s.active = true
            AND s.symbol NOT IN (
                SELECT DISTINCT jsonb_array_elements_text(ce.symbols)
                FROM cache_entries ce
                WHERE ce.symbols IS NOT NULL
            )
            ORDER BY s.market_cap DESC NULLS LAST
            """
            
            cursor.execute(ipo_query)
            new_ipos = cursor.fetchall()
            
            self.logger.info(f"+ Processing IPO assignments for {len(new_ipos)} new symbols")
            
            for ipo in new_ipos:
                assigned_universes = self.determine_universe_assignment(ipo)
                
                for universe in assigned_universes:
                    # Add to universe
                    current_symbols = self.get_current_universe_symbols(cursor, universe)
                    if ipo['symbol'] not in current_symbols:
                        updated_symbols = current_symbols + [ipo['symbol']]
                        
                        self.update_universe_symbols(cursor, universe, updated_symbols, {
                            'update_type': 'ipo_assignment',
                            'ipo_date': datetime.now().isoformat(),
                            'assignment_reason': f"New IPO - {ipo.get('sector', 'Unknown')} sector"
                        })
                        
                        changes.append(SynchronizationChange(
                            change_type='ipo_assignment',
                            universe=universe,
                            symbol=ipo['symbol'],
                            action='added',
                            reason=f"New IPO assigned - Sector: {ipo.get('sector', 'Unknown')}, Market Cap: ${ipo.get('market_cap', 0)/1e9:.1f}B",
                            timestamp=datetime.now(),
                            metadata={
                                'sector': ipo.get('sector'),
                                'industry': ipo.get('industry'),
                                'market_cap': ipo.get('market_cap'),
                                'symbol_type': ipo.get('type')
                            }
                        ))
            
            conn.commit()
            self.logger.info(f"+ IPO assignment complete: {len(changes)} assignments")
            
        except Exception as e:
            conn.rollback()
            self.logger.error(f"- IPO assignment failed: {e}")
        finally:
            if conn:
                conn.close()
        
        return changes
    
    def determine_universe_assignment(self, symbol_data: Dict[str, Any]) -> List[str]:
        """
        Determine appropriate universe assignments for a symbol
        
        Args:
            symbol_data: Symbol information from database
            
        Returns:
            List of universe names to assign the symbol to
        """
        assignments = []
        market_cap = symbol_data.get('market_cap', 0)
        sector = symbol_data.get('sector', '').lower()
        symbol_type = symbol_data.get('type', 'CS')
        
        # Market cap-based assignments
        if market_cap >= self.market_cap_thresholds['large_cap']:
            assignments.extend(['large_cap'])
        elif market_cap >= self.market_cap_thresholds['mid_cap']:
            assignments.extend(['mid_cap'])
        elif market_cap >= self.market_cap_thresholds['small_cap']:
            assignments.extend(['small_cap'])
        
        # Sector-based assignments
        sector_mappings = {
            'technology': ['tech_growth', 'high_growth'],
            'healthcare': ['defensive_growth', 'large_cap'],
            'financial': ['financial_services', 'value_oriented'],
            'energy': ['commodity_related', 'cyclical'],
            'consumer': ['consumer_focused'],
            'industrial': ['industrial_growth'],
            'utilities': ['dividend_focused', 'defensive']
        }
        
        for sector_key, universes in sector_mappings.items():
            if sector_key in sector:
                assignments.extend(universes)
        
        # Type-based assignments
        if symbol_type == 'ETF':
            assignments.append('etf_universe')
        elif symbol_type == 'CS':
            assignments.append('stock_universe')
        
        # Default assignment if no specific matches
        if not assignments:
            if market_cap > 1e9:  # $1B+
                assignments.append('general_market')
            else:
                assignments.append('small_cap_general')
        
        return list(set(assignments))  # Remove duplicates
    
    async def delisted_cleanup(self) -> List[SynchronizationChange]:
        """
        Remove delisted stocks from cache_entries while preserving historical data
        
        Returns:
            List of delisting cleanup changes
        """
        changes = []
        conn = self.get_database_connection()
        if not conn:
            return changes
        
        try:
            cursor = conn.cursor()
            
            # Find delisted symbols in cache_entries
            delisted_query = """
            WITH cache_symbols AS (
                SELECT DISTINCT jsonb_array_elements_text(ce.symbols) as symbol
                FROM cache_entries ce
                WHERE ce.symbols IS NOT NULL
            )
            SELECT cs.symbol
            FROM cache_symbols cs
            LEFT JOIN symbols s ON cs.symbol = s.symbol
            WHERE s.symbol IS NULL OR s.active = false
            """
            
            cursor.execute(delisted_query)
            delisted_symbols = [row['symbol'] for row in cursor.fetchall()]
            
            if delisted_symbols:
                self.logger.info(f"+ Processing delisting cleanup for {len(delisted_symbols)} symbols")
                
                # Remove from all cache_entries
                for symbol in delisted_symbols:
                    universes_updated = self.remove_symbol_from_all_universes(cursor, symbol)
                    
                    for universe in universes_updated:
                        changes.append(SynchronizationChange(
                            change_type='delisting_cleanup',
                            universe=universe,
                            symbol=symbol,
                            action='removed',
                            reason='Symbol delisted or deactivated',
                            timestamp=datetime.now(),
                            metadata={'cleanup_type': 'delisting'}
                        ))
                
                conn.commit()
                self.logger.info(f"+ Delisting cleanup complete: {len(changes)} removals")
            else:
                self.logger.info("+ No delisted symbols found in cache_entries")
                
        except Exception as e:
            conn.rollback()
            self.logger.error(f"- Delisting cleanup failed: {e}")
        finally:
            if conn:
                conn.close()
        
        return changes
    
    async def theme_rebalancing(self) -> List[SynchronizationChange]:
        """
        Perform theme rebalancing based on market condition changes
        
        Returns:
            List of theme rebalancing changes
        """
        changes = []
        
        # Theme rebalancing logic (placeholder for complex market condition analysis)
        # This would typically involve:
        # - Analyzing sector performance trends
        # - Adjusting theme compositions based on market conditions
        # - Rebalancing universe sizes based on liquidity changes
        # - Seasonal adjustments for certain themes
        
        self.logger.info("+ Theme rebalancing: No changes needed (markets stable)")
        
        # Example of how theme rebalancing would work:
        # if market_volatility > threshold:
        #     changes.extend(await self._rebalance_for_high_volatility())
        # if sector_rotation_detected:
        #     changes.extend(await self._rebalance_sector_themes())
        
        return changes
    
    async def etf_universe_maintenance(self) -> List[SynchronizationChange]:
        """
        Maintain ETF universe integrity and update metadata
        
        Returns:
            List of ETF universe maintenance changes
        """
        changes = []
        conn = self.get_database_connection()
        if not conn:
            return changes
        
        try:
            cursor = conn.cursor()
            
            # Update ETF universe metadata with fresh statistics
            etf_universes_query = """
            SELECT cache_key, symbols, universe_metadata
            FROM cache_entries
            WHERE universe_category = 'ETF'
            """
            
            cursor.execute(etf_universes_query)
            etf_universes = cursor.fetchall()
            
            for universe in etf_universes:
                cache_key = universe['cache_key']
                symbols = universe['symbols'] if universe['symbols'] else []
                
                if symbols and len(symbols) > 0:
                    # Update last_universe_update timestamp
                    cursor.execute("""
                        UPDATE cache_entries 
                        SET last_universe_update = CURRENT_TIMESTAMP
                        WHERE cache_key = %s
                    """, (cache_key,))
                    
                    changes.append(SynchronizationChange(
                        change_type='etf_maintenance',
                        universe=cache_key,
                        symbol=None,
                        action='updated',
                        reason='ETF universe metadata refresh',
                        timestamp=datetime.now(),
                        metadata={'symbol_count': len(symbols)}
                    ))
            
            conn.commit()
            self.logger.info(f"+ ETF universe maintenance: {len(changes)} updates")
            
        except Exception as e:
            conn.rollback()
            self.logger.error(f"- ETF universe maintenance failed: {e}")
        finally:
            if conn:
                conn.close()
        
        return changes
    
    def get_current_universe_symbols(self, cursor, universe_name: str) -> List[str]:
        """Get current symbols in a universe"""
        cursor.execute("""
            SELECT symbols
            FROM cache_entries
            WHERE cache_key = %s
        """, (universe_name,))
        
        result = cursor.fetchone()
        if result and result['symbols']:
            return [str(symbol) for symbol in result['symbols']]
        return []
    
    def update_universe_symbols(self, cursor, universe_name: str, symbols: List[str], metadata: Dict[str, Any] = None):
        """Update universe with new symbol list"""
        cursor.execute("""
            INSERT INTO cache_entries (cache_key, symbols, universe_metadata, last_universe_update)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (cache_key) DO UPDATE SET
                symbols = EXCLUDED.symbols,
                universe_metadata = COALESCE(cache_entries.universe_metadata, '{}'::jsonb) || EXCLUDED.universe_metadata,
                last_universe_update = CURRENT_TIMESTAMP
        """, (universe_name, json.dumps(symbols), json.dumps(metadata or {})))
    
    def remove_symbol_from_all_universes(self, cursor, symbol: str) -> List[str]:
        """Remove symbol from all cache_entries and return affected universes"""
        cursor.execute("""
            SELECT cache_key, symbols
            FROM cache_entries
            WHERE symbols ? %s
        """, (symbol,))
        
        affected_universes = []
        
        for row in cursor.fetchall():
            cache_key = row['cache_key']
            current_symbols = row['symbols'] if row['symbols'] else []
            
            if symbol in current_symbols:
                updated_symbols = [s for s in current_symbols if s != symbol]
                
                cursor.execute("""
                    UPDATE cache_entries 
                    SET symbols = %s, last_universe_update = CURRENT_TIMESTAMP
                    WHERE cache_key = %s
                """, (json.dumps(updated_symbols), cache_key))
                
                affected_universes.append(cache_key)
        
        return affected_universes
    
    async def log_sync_changes(self, changes: List[SynchronizationChange]):
        """Log synchronization changes to database for audit trail"""
        if not changes:
            return
        
        conn = self.get_database_connection()
        if not conn:
            return
        
        try:
            cursor = conn.cursor()
            
            # Create sync changes log table if not exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sync_changes_log (
                    id SERIAL PRIMARY KEY,
                    change_type VARCHAR(50),
                    universe VARCHAR(100),
                    symbol VARCHAR(20),
                    action VARCHAR(20),
                    reason TEXT,
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Insert changes
            for change in changes:
                cursor.execute("""
                    INSERT INTO sync_changes_log (change_type, universe, symbol, action, reason, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (change.change_type, change.universe, change.symbol, 
                     change.action, change.reason, json.dumps(change.metadata)))
            
            conn.commit()
            self.logger.info(f"+ Logged {len(changes)} synchronization changes")
            
        except Exception as e:
            conn.rollback()
            self.logger.error(f"- Change logging failed: {e}")
        finally:
            if conn:
                conn.close()
    
    async def publish_sync_notifications(self, changes: List[SynchronizationChange], task_results: Dict[str, Any]):
        """Publish synchronization notifications to Redis for TickStockApp"""
        redis_client = await self.connect_redis()
        if not redis_client:
            return
        
        try:
            # Publish overall sync completion
            sync_message = {
                'timestamp': datetime.now().isoformat(),
                'service': 'cache_entries_synchronizer',
                'event_type': 'daily_sync_complete',
                'total_changes': len(changes),
                'task_summary': {name: result.get('status', 'unknown') for name, result in task_results.items()},
                'changes_by_type': self.generate_change_summary(changes)
            }
            
            await redis_client.publish(
                self.channels['cache_sync_complete'],
                json.dumps(sync_message)
            )
            
            # Publish individual universe updates
            universe_changes = {}
            for change in changes:
                if change.universe not in universe_changes:
                    universe_changes[change.universe] = []
                universe_changes[change.universe].append(change)
            
            for universe, universe_change_list in universe_changes.items():
                universe_message = {
                    'timestamp': datetime.now().isoformat(),
                    'service': 'cache_entries_synchronizer',
                    'event_type': 'universe_synchronized',
                    'universe': universe,
                    'change_count': len(universe_change_list),
                    'actions': [change.action for change in universe_change_list]
                }
                
                await redis_client.publish(
                    self.channels['universe_updated'],
                    json.dumps(universe_message)
                )
            
            self.logger.info(f"+ Published sync notifications: {len(changes)} changes across {len(universe_changes)} universes")
            
        except Exception as e:
            self.logger.error(f"- Sync notification publishing failed: {e}")
        finally:
            if redis_client:
                await redis_client.aclose()
    
    def generate_change_summary(self, changes: List[SynchronizationChange]) -> Dict[str, Any]:
        """Generate summary statistics for synchronization changes"""
        if not changes:
            return {}
        
        summary = {
            'total_changes': len(changes),
            'by_type': {},
            'by_action': {},
            'by_universe': {},
            'most_active_universe': None,
            'change_distribution': {}
        }
        
        # Count by type
        for change in changes:
            summary['by_type'][change.change_type] = summary['by_type'].get(change.change_type, 0) + 1
            summary['by_action'][change.action] = summary['by_action'].get(change.action, 0) + 1
            summary['by_universe'][change.universe] = summary['by_universe'].get(change.universe, 0) + 1
        
        # Find most active universe
        if summary['by_universe']:
            summary['most_active_universe'] = max(summary['by_universe'].items(), key=lambda x: x[1])
        
        return summary

async def main():
    """Main execution function for cache entries synchronization"""
    synchronizer = CacheEntriesSynchronizer()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == '--daily-sync':
            result = await synchronizer.daily_cache_sync()
            if 'error' not in result:
                print(f"Daily synchronization complete:")
                print(f"  Total changes: {result['total_changes']}")
                print(f"  Duration: {result['total_sync_duration_minutes']:.1f} minutes")
                print(f"  Within window: {result['within_time_window']}")
                
                for task_name, task_result in result['task_results'].items():
                    status = task_result['status']
                    changes = task_result.get('changes_count', 0)
                    duration = task_result.get('duration_seconds', 0)
                    print(f"  {task_name}: {status} ({changes} changes in {duration:.1f}s)")
            else:
                print(f"Daily sync failed: {result['error']}")
                
        elif command == '--market-cap-update':
            changes = await synchronizer.market_cap_recalculation()
            print(f"Market cap update complete: {len(changes)} changes")
            for change in changes[:10]:  # Show first 10
                print(f"  {change.action}: {change.symbol} -> {change.universe} ({change.reason})")
                
        elif command == '--ipo-assignment':
            changes = await synchronizer.ipo_universe_assignment()
            print(f"IPO assignment complete: {len(changes)} assignments")
            for change in changes:
                print(f"  Added: {change.symbol} -> {change.universe} ({change.reason})")
                
        elif command == '--test-sync':
            result = await synchronizer.perform_synchronization()
            print(f"Test synchronization complete:")
            print(f"  Total changes: {result['total_changes']}")
            print(f"  Status: {result['sync_status']}")
            
        else:
            print("Usage:")
            print("  --daily-sync: Run complete daily synchronization (waits for EOD)")
            print("  --market-cap-update: Update market cap-based universes only")
            print("  --ipo-assignment: Process new IPO assignments only")
            print("  --test-sync: Run synchronization without waiting for EOD")
    else:
        # Default: daily sync
        result = await synchronizer.daily_cache_sync()
        print(f"Daily synchronization complete: {result.get('total_changes', 0)} changes")

if __name__ == '__main__':
    asyncio.run(main())