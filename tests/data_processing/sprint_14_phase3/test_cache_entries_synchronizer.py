#!/usr/bin/env python3
"""
Cache Entries Synchronizer Tests - Sprint 14 Phase 3

Comprehensive tests for the Cache Entries Synchronization System:
- Daily cache synchronization after EOD completion
- Market cap recalculation and automatic universe membership updates
- IPO universe assignment and delisted stock cleanup
- Real-time synchronization via Redis pub-sub with <5s delivery
- 30-minute completion window for daily cache sync operations

Test Organization:
- Unit tests: Synchronization logic, change tracking, universe updates
- Integration tests: Database operations, Redis messaging, EOD integration
- Performance tests: <30 minute sync window, <5s Redis delivery
- Regression tests: Existing functionality preservation, data integrity
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import psycopg2
import psycopg2.extras
import pytest

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../'))

from src.data.cache_entries_synchronizer import CacheEntriesSynchronizer, SynchronizationChange


class TestCacheEntriesSynchronizerRefactor:
    """Unit tests for Cache Entries Synchronizer refactor functionality"""

    @pytest.fixture
    def synchronizer(self):
        """Create Cache Entries Synchronizer instance for testing"""
        return CacheEntriesSynchronizer(
            database_uri='postgresql://test:test@localhost/test_db',
            redis_host='localhost'
        )

    @pytest.fixture
    def sample_sync_change(self):
        """Sample synchronization change for testing"""
        return SynchronizationChange(
            change_type='market_cap_update',
            universe='top_500',
            symbol='AAPL',
            action='added',
            reason='Market cap ranking qualified for top_500',
            timestamp=datetime.now(),
            metadata={'market_cap_rank': 15}
        )

    def test_synchronizer_initialization(self, synchronizer):
        """Test synchronizer initialization with proper configuration"""
        assert synchronizer.database_uri is not None
        assert synchronizer.redis_host == 'localhost'
        assert synchronizer.redis_port == 6379

        # Verify market cap thresholds
        assert synchronizer.market_cap_thresholds['mega_cap'] == 200e9
        assert synchronizer.market_cap_thresholds['large_cap'] == 10e9
        assert synchronizer.market_cap_thresholds['mid_cap'] == 2e9
        assert synchronizer.market_cap_thresholds['small_cap'] == 300e6
        assert synchronizer.market_cap_thresholds['micro_cap'] == 50e6

        # Verify universe limits
        assert synchronizer.universe_limits['top_100'] == 100
        assert synchronizer.universe_limits['top_500'] == 500
        assert synchronizer.universe_limits['top_1000'] == 1000
        assert synchronizer.universe_limits['top_2000'] == 2000

        # Verify timing configuration
        assert synchronizer.sync_timeout_minutes == 30
        assert synchronizer.eod_wait_timeout_seconds == 3600

    def test_redis_channels_configuration(self, synchronizer):
        """Test Redis channel configuration"""
        expected_channels = {
            'cache_sync_complete': 'tickstock.cache.sync_complete',
            'universe_updated': 'tickstock.universe.updated',
            'ipo_assignment': 'tickstock.cache.ipo_assignment',
            'delisting_cleanup': 'tickstock.cache.delisting_cleanup'
        }

        assert synchronizer.channels == expected_channels

    @patch('psycopg2.connect')
    def test_database_connection_success(self, mock_connect, synchronizer):
        """Test successful database connection"""
        mock_conn = Mock()
        mock_connect.return_value = mock_conn

        conn = synchronizer.get_database_connection()

        assert conn == mock_conn
        mock_connect.assert_called_once_with(
            synchronizer.database_uri,
            cursor_factory=psycopg2.extras.RealDictCursor
        )

    @patch('psycopg2.connect')
    def test_database_connection_failure(self, mock_connect, synchronizer):
        """Test database connection failure handling"""
        mock_connect.side_effect = Exception("Connection failed")

        conn = synchronizer.get_database_connection()

        assert conn is None

    @pytest.mark.asyncio
    async def test_redis_connection_success(self, synchronizer):
        """Test successful Redis connection"""
        with patch('redis.asyncio.Redis') as mock_redis:
            mock_client = AsyncMock()
            mock_redis.return_value = mock_client
            mock_client.ping.return_value = True

            redis_client = await synchronizer.connect_redis()

            assert redis_client == mock_client
            mock_client.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_redis_connection_failure(self, synchronizer):
        """Test Redis connection failure handling"""
        with patch('redis.asyncio.Redis') as mock_redis:
            mock_client = AsyncMock()
            mock_redis.return_value = mock_client
            mock_client.ping.side_effect = Exception("Connection failed")

            redis_client = await synchronizer.connect_redis()

            assert redis_client is None

    @pytest.mark.asyncio
    async def test_wait_for_eod_completion_success(self, synchronizer):
        """Test successful EOD completion wait"""
        with patch.object(synchronizer, 'connect_redis') as mock_redis:
            mock_client = AsyncMock()
            mock_redis.return_value = mock_client
            mock_client.blpop.return_value = ('eod_complete', 'completion_signal')

            result = await synchronizer.wait_for_eod_completion()

            assert result is True
            mock_client.blpop.assert_called_once()

    @pytest.mark.asyncio
    async def test_wait_for_eod_completion_timeout(self, synchronizer):
        """Test EOD completion timeout handling"""
        with patch.object(synchronizer, 'connect_redis') as mock_redis:
            mock_client = AsyncMock()
            mock_redis.return_value = mock_client
            mock_client.blpop.return_value = None  # Timeout

            result = await synchronizer.wait_for_eod_completion()

            assert result is True  # Proceeds even on timeout

    @pytest.mark.asyncio
    async def test_wait_for_eod_no_redis(self, synchronizer):
        """Test EOD wait behavior when Redis is unavailable"""
        with patch.object(synchronizer, 'connect_redis') as mock_redis:
            mock_redis.return_value = None

            result = await synchronizer.wait_for_eod_completion()

            assert result is True  # Proceeds without Redis

    def test_determine_universe_assignment_large_cap(self, synchronizer):
        """Test universe assignment for large cap stocks"""
        symbol_data = {
            'market_cap': 50e9,  # $50B
            'sector': 'technology',
            'type': 'CS'
        }

        assignments = synchronizer.determine_universe_assignment(symbol_data)

        assert 'large_cap' in assignments
        assert 'tech_growth' in assignments
        assert 'high_growth' in assignments
        assert 'stock_universe' in assignments

    def test_determine_universe_assignment_small_cap(self, synchronizer):
        """Test universe assignment for small cap stocks"""
        symbol_data = {
            'market_cap': 500e6,  # $500M
            'sector': 'healthcare',
            'type': 'CS'
        }

        assignments = synchronizer.determine_universe_assignment(symbol_data)

        assert 'small_cap' in assignments
        assert 'defensive_growth' in assignments
        assert 'stock_universe' in assignments

    def test_determine_universe_assignment_etf(self, synchronizer):
        """Test universe assignment for ETFs"""
        symbol_data = {
            'market_cap': 5e9,
            'sector': 'financial',
            'type': 'ETF'
        }

        assignments = synchronizer.determine_universe_assignment(symbol_data)

        assert 'etf_universe' in assignments
        assert 'financial_services' in assignments
        assert 'value_oriented' in assignments

    def test_determine_universe_assignment_default(self, synchronizer):
        """Test default universe assignment"""
        symbol_data = {
            'market_cap': 2e9,  # $2B
            'sector': 'unknown',
            'type': 'CS'
        }

        assignments = synchronizer.determine_universe_assignment(symbol_data)

        assert 'general_market' in assignments
        assert 'stock_universe' in assignments

    @patch('psycopg2.connect')
    async def test_market_cap_recalculation_success(self, mock_connect, synchronizer):
        """Test successful market cap recalculation"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        # Mock market cap ranking data
        mock_rankings = [
            {
                'symbol': 'AAPL',
                'market_cap': 3000e9,
                'sector': 'Technology',
                'name': 'Apple Inc.',
                'rank': 1
            },
            {
                'symbol': 'MSFT',
                'market_cap': 2500e9,
                'sector': 'Technology',
                'name': 'Microsoft Corp.',
                'rank': 2
            }
        ]
        mock_cursor.fetchall.return_value = mock_rankings

        # Mock current universe symbols
        with patch.object(synchronizer, 'get_current_universe_symbols') as mock_current:
            mock_current.return_value = ['GOOGL']  # Different from new ranking

            with patch.object(synchronizer, 'update_universe_symbols') as mock_update:
                changes = await synchronizer.market_cap_recalculation()

                # Verify changes detected
                assert len(changes) > 0

                # Verify database operations
                mock_cursor.execute.assert_called()
                mock_conn.commit.assert_called_once()
                mock_update.assert_called()

    @patch('psycopg2.connect')
    async def test_ipo_universe_assignment_success(self, mock_connect, synchronizer):
        """Test successful IPO universe assignment"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        # Mock new IPO data
        mock_ipos = [
            {
                'symbol': 'NEWIPO',
                'sector': 'Technology',
                'market_cap': 15e9,
                'industry': 'Software',
                'name': 'New IPO Corp.',
                'type': 'CS'
            }
        ]
        mock_cursor.fetchall.return_value = mock_ipos

        with patch.object(synchronizer, 'get_current_universe_symbols') as mock_current:
            mock_current.return_value = ['EXISTING1', 'EXISTING2']

            with patch.object(synchronizer, 'update_universe_symbols') as mock_update:
                changes = await synchronizer.ipo_universe_assignment()

                # Verify IPO assignments created
                assert len(changes) > 0

                # Verify assignment logic
                ipo_changes = [c for c in changes if c.change_type == 'ipo_assignment']
                assert len(ipo_changes) > 0
                assert ipo_changes[0].symbol == 'NEWIPO'
                assert ipo_changes[0].action == 'added'

    @patch('psycopg2.connect')
    async def test_delisted_cleanup_success(self, mock_connect, synchronizer):
        """Test successful delisted stock cleanup"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        # Mock delisted symbols
        mock_delisted = [
            {'symbol': 'DELISTED1'},
            {'symbol': 'DELISTED2'}
        ]
        mock_cursor.fetchall.return_value = mock_delisted

        with patch.object(synchronizer, 'remove_symbol_from_all_universes') as mock_remove:
            mock_remove.return_value = ['universe1', 'universe2']

            changes = await synchronizer.delisted_cleanup()

            # Verify cleanup changes
            assert len(changes) > 0

            # Verify removal operations
            cleanup_changes = [c for c in changes if c.change_type == 'delisting_cleanup']
            assert len(cleanup_changes) >= 2  # At least one per delisted symbol

            mock_remove.assert_called()
            mock_conn.commit.assert_called_once()

    @patch('psycopg2.connect')
    async def test_etf_universe_maintenance_success(self, mock_connect, synchronizer):
        """Test successful ETF universe maintenance"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        # Mock ETF universe data
        mock_etf_universes = [
            {
                'cache_key': 'etf_sectors',
                'symbols': ['XLF', 'XLE', 'XLK'],
                'universe_metadata': {'theme': 'Sectors'}
            },
            {
                'cache_key': 'etf_technology',
                'symbols': ['QQQ', 'XLK', 'VGT'],
                'universe_metadata': {'theme': 'Technology'}
            }
        ]
        mock_cursor.fetchall.return_value = mock_etf_universes

        changes = await synchronizer.etf_universe_maintenance()

        # Verify maintenance changes
        assert len(changes) > 0

        # Verify all universes processed
        maintenance_changes = [c for c in changes if c.change_type == 'etf_maintenance']
        assert len(maintenance_changes) == 2

        # Verify database updates
        mock_cursor.execute.assert_called()
        mock_conn.commit.assert_called_once()

    def test_get_current_universe_symbols_success(self, synchronizer):
        """Test getting current universe symbols"""
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = {
            'symbols': ['AAPL', 'MSFT', 'GOOGL']
        }

        symbols = synchronizer.get_current_universe_symbols(mock_cursor, 'top_100')

        assert symbols == ['AAPL', 'MSFT', 'GOOGL']
        mock_cursor.execute.assert_called_once()

    def test_get_current_universe_symbols_empty(self, synchronizer):
        """Test getting empty universe symbols"""
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = None

        symbols = synchronizer.get_current_universe_symbols(mock_cursor, 'empty_universe')

        assert symbols == []

    def test_update_universe_symbols(self, synchronizer):
        """Test updating universe symbols"""
        mock_cursor = Mock()

        synchronizer.update_universe_symbols(
            mock_cursor,
            'test_universe',
            ['SYM1', 'SYM2'],
            {'update_type': 'test'}
        )

        mock_cursor.execute.assert_called_once()
        args = mock_cursor.execute.call_args[0]
        assert 'INSERT INTO cache_entries' in args[0]
        assert args[1][0] == 'test_universe'

    def test_remove_symbol_from_all_universes(self, synchronizer):
        """Test removing symbol from all universes"""
        mock_cursor = Mock()

        # Mock universes containing the symbol
        mock_cursor.fetchall.return_value = [
            {
                'cache_key': 'universe1',
                'symbols': ['AAPL', 'REMOVE_ME', 'MSFT']
            },
            {
                'cache_key': 'universe2',
                'symbols': ['GOOGL', 'REMOVE_ME']
            }
        ]

        affected_universes = synchronizer.remove_symbol_from_all_universes(mock_cursor, 'REMOVE_ME')

        assert 'universe1' in affected_universes
        assert 'universe2' in affected_universes
        assert len(affected_universes) == 2

        # Verify UPDATE statements called
        assert mock_cursor.execute.call_count >= 3  # SELECT + 2 UPDATEs

    def test_generate_change_summary(self, synchronizer, sample_sync_change):
        """Test change summary generation"""
        changes = [
            sample_sync_change,
            SynchronizationChange(
                'ipo_assignment', 'growth_stocks', 'NEWIPO', 'added',
                'New IPO', datetime.now(), {}
            ),
            SynchronizationChange(
                'market_cap_update', 'top_500', 'MSFT', 'added',
                'Ranking change', datetime.now(), {}
            )
        ]

        summary = synchronizer.generate_change_summary(changes)

        assert summary['total_changes'] == 3
        assert summary['by_type']['market_cap_update'] == 2
        assert summary['by_type']['ipo_assignment'] == 1
        assert summary['by_action']['added'] == 3
        assert summary['by_universe']['top_500'] == 2

        # Most active universe
        most_active = summary['most_active_universe']
        assert most_active[0] == 'top_500'
        assert most_active[1] == 2


class TestCacheEntriesSynchronizerIntegration:
    """Integration tests for Cache Entries Synchronizer with database and Redis"""

    @pytest.fixture
    def synchronizer(self):
        """Create synchronizer for integration testing"""
        return CacheEntriesSynchronizer()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_daily_cache_sync_integration(self, synchronizer):
        """Test complete daily cache synchronization integration"""
        with patch.object(synchronizer, 'wait_for_eod_completion') as mock_eod, \
             patch.object(synchronizer, 'perform_synchronization') as mock_sync:

            mock_eod.return_value = True
            mock_sync.return_value = {
                'total_changes': 15,
                'task_results': {
                    'market_cap_recalculation': {'status': 'completed', 'changes_count': 5},
                    'ipo_universe_assignment': {'status': 'completed', 'changes_count': 3},
                    'delisted_cleanup': {'status': 'completed', 'changes_count': 2}
                }
            }

            result = await synchronizer.daily_cache_sync()

            # Verify integration flow
            mock_eod.assert_called_once()
            mock_sync.assert_called_once()

            # Verify result structure
            assert 'total_sync_duration_minutes' in result
            assert 'within_time_window' in result
            assert result['total_changes'] == 15

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_perform_synchronization_comprehensive(self, synchronizer):
        """Test comprehensive synchronization with all tasks"""
        with patch.object(synchronizer, 'market_cap_recalculation') as mock_market_cap, \
             patch.object(synchronizer, 'ipo_universe_assignment') as mock_ipo, \
             patch.object(synchronizer, 'delisted_cleanup') as mock_delisted, \
             patch.object(synchronizer, 'theme_rebalancing') as mock_theme, \
             patch.object(synchronizer, 'etf_universe_maintenance') as mock_etf, \
             patch.object(synchronizer, 'log_sync_changes') as mock_log, \
             patch.object(synchronizer, 'publish_sync_notifications') as mock_publish:

            # Mock task results
            mock_market_cap.return_value = [
                SynchronizationChange('market_cap_update', 'top_500', 'AAPL', 'added', 'test', datetime.now(), {})
            ]
            mock_ipo.return_value = []
            mock_delisted.return_value = []
            mock_theme.return_value = []
            mock_etf.return_value = []

            result = await synchronizer.perform_synchronization()

            # Verify all tasks executed
            mock_market_cap.assert_called_once()
            mock_ipo.assert_called_once()
            mock_delisted.assert_called_once()
            mock_theme.assert_called_once()
            mock_etf.assert_called_once()

            # Verify post-processing
            mock_log.assert_called_once()
            mock_publish.assert_called_once()

            # Verify result structure
            assert 'total_changes' in result
            assert 'task_results' in result
            assert 'changes_summary' in result
            assert result['sync_status'] == 'completed'

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_log_sync_changes_database_integration(self, synchronizer):
        """Test synchronization change logging to database"""
        changes = [
            SynchronizationChange(
                'market_cap_update', 'top_100', 'AAPL', 'added',
                'Market cap increased', datetime.now(),
                {'previous_rank': 5, 'new_rank': 3}
            )
        ]

        with patch.object(synchronizer, 'get_database_connection') as mock_db:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_conn.cursor.return_value = mock_cursor
            mock_db.return_value = mock_conn

            await synchronizer.log_sync_changes(changes)

            # Verify table creation and insert
            mock_cursor.execute.assert_called()
            mock_conn.commit.assert_called_once()

            # Verify INSERT statement
            insert_calls = [call for call in mock_cursor.execute.call_args_list
                          if 'INSERT INTO sync_changes_log' in str(call)]
            assert len(insert_calls) >= 1

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_publish_sync_notifications_redis_integration(self, synchronizer):
        """Test Redis notification publishing integration"""
        changes = [
            SynchronizationChange(
                'market_cap_update', 'top_500', 'AAPL', 'added',
                'Market cap ranking change', datetime.now(), {}
            ),
            SynchronizationChange(
                'ipo_assignment', 'growth_stocks', 'NEWIPO', 'added',
                'New IPO assignment', datetime.now(), {}
            )
        ]

        task_results = {
            'market_cap_recalculation': {'status': 'completed', 'changes_count': 1},
            'ipo_universe_assignment': {'status': 'completed', 'changes_count': 1}
        }

        with patch.object(synchronizer, 'connect_redis') as mock_redis:
            mock_client = AsyncMock()
            mock_redis.return_value = mock_client

            await synchronizer.publish_sync_notifications(changes, task_results)

            # Verify Redis publishing
            assert mock_client.publish.call_count >= 2  # Overall + individual universes

            # Verify message structure
            calls = mock_client.publish.call_args_list

            # Overall sync completion message
            overall_call = next(call for call in calls if call[0][0] == 'tickstock.cache.sync_complete')
            message = json.loads(overall_call[0][1])

            assert message['event_type'] == 'daily_sync_complete'
            assert message['total_changes'] == 2
            assert 'task_summary' in message

    @pytest.mark.integration
    @patch('psycopg2.connect')
    async def test_end_to_end_synchronization_flow(self, mock_connect, synchronizer):
        """Test complete end-to-end synchronization flow"""
        # Setup database mock
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        # Mock market cap data
        mock_cursor.fetchall.side_effect = [
            # Market cap rankings
            [{'symbol': 'AAPL', 'market_cap': 3000e9, 'sector': 'Technology', 'name': 'Apple', 'rank': 1}],
            # IPO data
            [],
            # Delisted data
            [],
            # ETF universe data
            [{'cache_key': 'etf_sectors', 'symbols': ['XLF'], 'universe_metadata': {}}]
        ]

        with patch.object(synchronizer, 'get_current_universe_symbols') as mock_current, \
             patch.object(synchronizer, 'connect_redis') as mock_redis:

            mock_current.return_value = []  # Empty current universe
            mock_redis_client = AsyncMock()
            mock_redis.return_value = mock_redis_client

            # Execute full synchronization
            result = await synchronizer.perform_synchronization()

            # Verify comprehensive processing
            assert result['sync_status'] == 'completed'
            assert 'total_changes' in result
            assert 'task_results' in result
            assert len(result['task_results']) == 5  # All synchronization tasks

            # Verify database operations
            assert mock_cursor.execute.call_count > 0
            mock_conn.commit.assert_called()

            # Verify Redis publishing
            assert mock_redis_client.publish.call_count >= 1


class TestCacheEntriesSynchronizerPerformance:
    """Performance tests for Cache Entries Synchronizer operations"""

    @pytest.fixture
    def synchronizer(self):
        """Create synchronizer for performance testing"""
        return CacheEntriesSynchronizer()

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_daily_sync_performance_window(self, synchronizer):
        """Test daily sync meets 30-minute performance window"""
        import time

        with patch.object(synchronizer, 'wait_for_eod_completion') as mock_eod, \
             patch.object(synchronizer, 'perform_synchronization') as mock_sync:

            mock_eod.return_value = True

            # Mock fast synchronization response
            mock_sync.return_value = {
                'total_changes': 50,
                'task_results': {
                    'market_cap_recalculation': {'status': 'completed', 'changes_count': 20},
                    'ipo_universe_assignment': {'status': 'completed', 'changes_count': 10}
                }
            }

            start_time = time.time()
            result = await synchronizer.daily_cache_sync()
            sync_duration = time.time() - start_time

            # Verify performance requirement: process under 30 minutes
            # (Note: actual sync would be much longer, this tests the framework)
            assert sync_duration < 1.0, f"Sync framework took {sync_duration:.3f}s, should be <1s for mocked operations"

            # Verify time window calculation
            assert 'within_time_window' in result

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_redis_notification_performance(self, synchronizer):
        """Test Redis notification delivery meets <5 second requirement"""
        import time

        # Create multiple changes for performance testing
        changes = []
        for i in range(100):  # 100 changes across multiple universes
            changes.append(SynchronizationChange(
                'market_cap_update', f'universe_{i % 10}', f'SYM_{i}', 'added',
                f'Change {i}', datetime.now(), {}
            ))

        task_results = {'test_task': {'status': 'completed', 'changes_count': 100}}

        with patch.object(synchronizer, 'connect_redis') as mock_redis:
            mock_client = AsyncMock()
            mock_redis.return_value = mock_client

            start_time = time.time()
            await synchronizer.publish_sync_notifications(changes, task_results)
            publish_duration = time.time() - start_time

            # Verify performance requirement: <5 seconds for Redis delivery
            assert publish_duration < 5.0, f"Redis publishing took {publish_duration:.3f}s, expected <5s"

            # Verify all notifications sent
            assert mock_client.publish.call_count >= 10  # At least one per universe

    @pytest.mark.performance
    @patch('psycopg2.connect')
    async def test_market_cap_recalculation_performance(self, mock_connect, synchronizer):
        """Test market cap recalculation performance with large datasets"""
        import time

        # Setup large dataset mock
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        # Mock 5000 symbols ranking
        large_rankings = []
        for i in range(5000):
            large_rankings.append({
                'symbol': f'SYM_{i:04d}',
                'market_cap': (5000 - i) * 1e9,  # Decreasing market caps
                'sector': 'Technology' if i % 2 == 0 else 'Healthcare',
                'name': f'Company {i}',
                'rank': i + 1
            })

        mock_cursor.fetchall.return_value = large_rankings

        with patch.object(synchronizer, 'get_current_universe_symbols') as mock_current, \
             patch.object(synchronizer, 'update_universe_symbols') as mock_update:

            mock_current.return_value = [f'OLD_SYM_{i}' for i in range(100)]  # Different symbols

            start_time = time.time()
            changes = await synchronizer.market_cap_recalculation()
            calculation_time = time.time() - start_time

            # Verify performance: should handle large datasets efficiently
            assert calculation_time < 10.0, f"Market cap calculation took {calculation_time:.3f}s, expected <10s"

            # Verify processing occurred
            assert len(changes) > 0
            mock_update.assert_called()

    @pytest.mark.performance
    def test_memory_efficiency_large_change_sets(self, synchronizer):
        """Test memory efficiency with large change sets"""
        import sys

        # Create large change set
        changes = []
        for i in range(10000):
            changes.append(SynchronizationChange(
                'market_cap_update', f'universe_{i % 100}', f'SYM_{i}', 'added',
                f'Change {i}', datetime.now(), {'rank': i}
            ))

        # Measure memory before processing
        initial_memory = sys.getsizeof(synchronizer)

        # Process large change summary
        summary = synchronizer.generate_change_summary(changes)

        # Measure memory after processing
        final_memory = sys.getsizeof(synchronizer)
        memory_growth = final_memory - initial_memory

        # Verify efficient processing
        assert summary['total_changes'] == 10000
        assert len(summary['by_universe']) == 100

        # Verify no significant memory leaks
        assert memory_growth < 10000, f"Memory grew by {memory_growth} bytes processing large change set"

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_eod_wait_timeout_performance(self, synchronizer):
        """Test EOD wait timeout doesn't delay sync significantly"""
        import time

        # Configure short timeout for testing
        synchronizer.eod_wait_timeout_seconds = 2  # 2 seconds for testing

        with patch.object(synchronizer, 'connect_redis') as mock_redis:
            mock_client = AsyncMock()
            mock_redis.return_value = mock_client
            mock_client.blpop.return_value = None  # Simulate timeout

            start_time = time.time()
            result = await synchronizer.wait_for_eod_completion()
            wait_time = time.time() - start_time

            # Verify timeout behavior
            assert result is True  # Should proceed
            assert wait_time >= 2.0  # Should wait for timeout
            assert wait_time < 3.0  # Should not wait significantly longer


class TestCacheEntriesSynchronizerRegression:
    """Regression tests to ensure existing functionality is preserved"""

    @pytest.fixture
    def synchronizer(self):
        """Create synchronizer for regression testing"""
        return CacheEntriesSynchronizer()

    def test_synchronization_change_structure_preservation(self, synchronizer):
        """Test SynchronizationChange structure remains compatible"""
        change = SynchronizationChange(
            change_type='market_cap_update',
            universe='top_500',
            symbol='AAPL',
            action='added',
            reason='Market cap increase',
            timestamp=datetime.now(),
            metadata={'rank': 15}
        )

        # Verify all required attributes exist
        required_attrs = [
            'change_type', 'universe', 'symbol', 'action', 'reason', 'timestamp', 'metadata'
        ]

        for attr in required_attrs:
            assert hasattr(change, attr), f"SynchronizationChange missing required attribute: {attr}"
            assert getattr(change, attr) is not None, f"Attribute {attr} should not be None"

    def test_market_cap_thresholds_consistency(self, synchronizer):
        """Test market cap thresholds remain consistent"""
        # These thresholds are critical for universe classification
        expected_thresholds = {
            'mega_cap': 200e9,      # $200B+
            'large_cap': 10e9,      # $10B - $200B
            'mid_cap': 2e9,         # $2B - $10B
            'small_cap': 300e6,     # $300M - $2B
            'micro_cap': 50e6       # $50M - $300M
        }

        assert synchronizer.market_cap_thresholds == expected_thresholds

    def test_universe_limits_consistency(self, synchronizer):
        """Test universe size limits remain consistent"""
        expected_limits = {
            'top_100': 100,
            'top_500': 500,
            'top_1000': 1000,
            'top_2000': 2000
        }

        assert synchronizer.universe_limits == expected_limits

    def test_redis_channel_naming_consistency(self, synchronizer):
        """Test Redis channel names remain consistent"""
        expected_channels = {
            'cache_sync_complete': 'tickstock.cache.sync_complete',
            'universe_updated': 'tickstock.universe.updated',
            'ipo_assignment': 'tickstock.cache.ipo_assignment',
            'delisting_cleanup': 'tickstock.cache.delisting_cleanup'
        }

        assert synchronizer.channels == expected_channels

    def test_synchronization_task_sequence_consistency(self, synchronizer):
        """Test synchronization task sequence remains consistent"""
        # These tasks must be executed in order for proper dependency handling
        expected_task_sequence = [
            'market_cap_recalculation',
            'ipo_universe_assignment',
            'delisted_cleanup',
            'theme_rebalancing',
            'etf_universe_maintenance'
        ]

        # Verify all expected methods exist
        for task_name in expected_task_sequence:
            method_name = task_name
            assert hasattr(synchronizer, method_name), f"Missing synchronization task method: {method_name}"

            # Verify methods are async
            method = getattr(synchronizer, method_name)
            assert asyncio.iscoroutinefunction(method), f"Task method {method_name} should be async"

    @patch('psycopg2.connect')
    def test_database_table_compatibility(self, mock_connect, synchronizer):
        """Test database table structure compatibility"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        # Test cache_entries table operations
        synchronizer.update_universe_symbols(
            mock_cursor, 'test_universe', ['SYM1'], {'test': True}
        )

        # Verify expected table and column names
        args = mock_cursor.execute.call_args[0]
        sql = args[0]

        assert 'cache_entries' in sql
        assert 'cache_key' in sql
        assert 'symbols' in sql
        assert 'universe_metadata' in sql
        assert 'last_universe_update' in sql

    def test_universe_assignment_logic_consistency(self, synchronizer):
        """Test universe assignment logic remains consistent"""
        # Test known assignment patterns
        tech_large_cap = {
            'market_cap': 50e9,
            'sector': 'technology',
            'type': 'CS'
        }

        assignments = synchronizer.determine_universe_assignment(tech_large_cap)

        # Verify expected assignments
        assert 'large_cap' in assignments
        assert 'stock_universe' in assignments
        assert any('tech' in assignment for assignment in assignments)

        # Test ETF assignment
        etf_data = {
            'market_cap': 5e9,
            'sector': 'financial',
            'type': 'ETF'
        }

        etf_assignments = synchronizer.determine_universe_assignment(etf_data)
        assert 'etf_universe' in etf_assignments

    def test_change_summary_format_consistency(self, synchronizer):
        """Test change summary format remains consistent for downstream consumers"""
        changes = [
            SynchronizationChange(
                'market_cap_update', 'top_100', 'AAPL', 'added',
                'test', datetime.now(), {}
            )
        ]

        summary = synchronizer.generate_change_summary(changes)

        # Verify expected summary structure
        required_fields = [
            'total_changes', 'by_type', 'by_action', 'by_universe',
            'most_active_universe', 'change_distribution'
        ]

        for field in required_fields:
            assert field in summary, f"Change summary missing required field: {field}"

    @pytest.mark.asyncio
    async def test_redis_message_format_consistency(self, synchronizer):
        """Test Redis message format remains consistent"""
        changes = [
            SynchronizationChange(
                'market_cap_update', 'top_500', 'AAPL', 'added',
                'test change', datetime.now(), {}
            )
        ]

        task_results = {
            'market_cap_recalculation': {'status': 'completed', 'changes_count': 1}
        }

        with patch.object(synchronizer, 'connect_redis') as mock_redis:
            mock_client = AsyncMock()
            mock_redis.return_value = mock_client

            await synchronizer.publish_sync_notifications(changes, task_results)

            # Verify message structure
            publish_calls = mock_client.publish.call_args_list
            assert len(publish_calls) >= 1

            # Check overall sync message
            sync_message = json.loads(publish_calls[0][0][1])
            required_fields = [
                'timestamp', 'service', 'event_type', 'total_changes', 'task_summary'
            ]

            for field in required_fields:
                assert field in sync_message, f"Redis sync message missing field: {field}"

            assert sync_message['service'] == 'cache_entries_synchronizer'
            assert sync_message['event_type'] == 'daily_sync_complete'


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
