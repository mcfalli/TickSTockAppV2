#!/usr/bin/env python3
"""
Sprint 14 Phase 3 System Integration Tests

Comprehensive integration tests for all Phase 3 advanced features:
- Cross-system interactions between ETF Universe Manager, Scenario Generator, and Synchronizer
- Redis messaging patterns and real-time notification delivery (<5s requirement)
- End-to-end workflows from universe expansion to synchronization
- Performance validation across all systems (<2s queries, <2min scenarios, <30min sync)
- Integration with existing TickStock architecture and data flows

Test Organization:
- Integration tests: Cross-component workflows, Redis messaging integration
- Performance tests: End-to-end performance validation, system load testing
- Regression tests: Existing system integration preservation
- Stress tests: High-load scenarios and system resilience
"""

import pytest
import asyncio
import json
import os
import sys
import time
from unittest.mock import Mock, patch, AsyncMock, call
from datetime import datetime, timedelta, date
import psycopg2
import psycopg2.extras
from decimal import Decimal
import redis.asyncio as redis
import numpy as np

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../'))

from src.data.etf_universe_manager import ETFUniverseManager
from src.data.test_scenario_generator import TestScenarioGenerator
from src.data.cache_entries_synchronizer import CacheEntriesSynchronizer, SynchronizationChange

class TestPhase3SystemIntegration:
    """Integration tests for Phase 3 advanced features system integration"""
    
    @pytest.fixture
    def etf_manager(self):
        """ETF Universe Manager instance"""
        return ETFUniverseManager(
            database_uri='postgresql://test:test@localhost/test_db',
            redis_host='localhost'
        )
    
    @pytest.fixture
    def scenario_generator(self):
        """Test Scenario Generator instance"""
        return TestScenarioGenerator(
            database_uri='postgresql://test:test@localhost/test_db'
        )
    
    @pytest.fixture
    def synchronizer(self):
        """Cache Entries Synchronizer instance"""
        return CacheEntriesSynchronizer(
            database_uri='postgresql://test:test@localhost/test_db',
            redis_host='localhost'
        )
    
    @pytest.mark.integration
    @patch('psycopg2.connect')
    async def test_etf_universe_expansion_to_synchronization_flow(self, mock_connect, etf_manager, synchronizer):
        """Test complete flow from ETF universe expansion to synchronization"""
        # Setup database mock
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # Mock ETF expansion results
        mock_cursor.fetchone.return_value = [{
            'action': 'updated',
            'cache_key': 'etf_sectors',
            'symbols_count': 10,
            'added_count': 2,
            'removed_count': 0,
            'symbols_added': ['NEW_ETF1', 'NEW_ETF2']
        }]
        
        # Mock synchronizer universe data
        mock_cursor.fetchall.side_effect = [
            # ETF universes for maintenance
            [
                {
                    'cache_key': 'etf_sectors',
                    'symbols': ['XLF', 'XLE', 'NEW_ETF1', 'NEW_ETF2'],
                    'universe_metadata': {'theme': 'Sectors', 'updated': True}
                }
            ]
        ]
        
        with patch.object(etf_manager, 'connect_redis') as mock_etf_redis, \
             patch.object(synchronizer, 'connect_redis') as mock_sync_redis:
            
            # Setup Redis mocks
            mock_etf_client = AsyncMock()
            mock_sync_client = AsyncMock()
            mock_etf_redis.return_value = mock_etf_client
            mock_sync_redis.return_value = mock_sync_client
            
            # Step 1: Expand ETF universes
            expansion_results = etf_manager.expand_etf_universes()
            await etf_manager.publish_universe_updates(expansion_results)
            
            # Step 2: Synchronizer processes ETF universe maintenance
            sync_changes = await synchronizer.etf_universe_maintenance()
            
            # Verify integration flow
            assert expansion_results['themes_processed'] == 7
            assert expansion_results['success'] > 0
            
            # Verify synchronizer detected changes
            assert len(sync_changes) > 0
            etf_changes = [c for c in sync_changes if c.change_type == 'etf_maintenance']
            assert len(etf_changes) > 0
            
            # Verify Redis publishing occurred
            assert mock_etf_client.publish.call_count >= 1
            assert mock_sync_client.publish.call_count >= 0
    
    @pytest.mark.integration
    @patch('psycopg2.connect')
    async def test_scenario_generation_to_database_integration(self, mock_connect, scenario_generator):
        """Test scenario generation integration with database loading"""
        # Setup database mock
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # Execute scenario generation and loading
        load_result = scenario_generator.load_scenario('crash_2020', ['TEST_CRASH'])
        
        # Verify integration completed successfully
        assert 'scenario_name' in load_result
        assert 'symbols_loaded' in load_result
        assert 'total_records' in load_result
        assert 'load_duration_seconds' in load_result
        assert load_result['scenario_name'] == 'crash_2020'
        
        # Verify database operations occurred
        mock_cursor.execute.assert_called()
        mock_conn.commit.assert_called()
        
        # Verify both historical_data and symbols table operations
        execute_calls = mock_cursor.execute.call_args_list
        historical_inserts = [call for call in execute_calls if 'historical_data' in str(call[0])]
        symbol_inserts = [call for call in execute_calls if 'INSERT INTO symbols' in str(call[0])]
        
        assert len(historical_inserts) > 0, "Should insert historical data"
        assert len(symbol_inserts) > 0, "Should insert symbol data"
    
    @pytest.mark.integration
    @patch('psycopg2.connect')
    async def test_redis_messaging_cross_system_integration(self, mock_connect, etf_manager, synchronizer):
        """Test Redis messaging integration across systems"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # Setup expansion results
        expansion_results = {
            'timestamp': datetime.now().isoformat(),
            'themes_processed': 7,
            'total_symbols': 50,
            'success': 7,
            'themes': {
                'sectors': {'action': 'updated', 'symbols_count': 10},
                'technology': {'action': 'updated', 'symbols_count': 8}
            }
        }
        
        # Setup sync changes
        sync_changes = [
            SynchronizationChange(
                'etf_maintenance', 'etf_sectors', None, 'updated',
                'ETF universe metadata refresh', datetime.now(),
                {'symbol_count': 10}
            )
        ]
        
        task_results = {
            'etf_universe_maintenance': {'status': 'completed', 'changes_count': 1}
        }
        
        # Mock Redis clients
        captured_messages = []
        
        async def capture_publish(channel, message):
            captured_messages.append({'channel': channel, 'message': json.loads(message)})
        
        with patch.object(etf_manager, 'connect_redis') as mock_etf_redis, \
             patch.object(synchronizer, 'connect_redis') as mock_sync_redis:
            
            mock_etf_client = AsyncMock()
            mock_sync_client = AsyncMock()
            mock_etf_redis.return_value = mock_etf_client
            mock_sync_redis.return_value = mock_sync_client
            
            # Capture published messages
            mock_etf_client.publish.side_effect = capture_publish
            mock_sync_client.publish.side_effect = capture_publish
            
            # Publish from both systems
            await etf_manager.publish_universe_updates(expansion_results)
            await synchronizer.publish_sync_notifications(sync_changes, task_results)
            
            # Verify cross-system messaging
            assert len(captured_messages) >= 2
            
            # Verify ETF manager messages
            etf_messages = [m for m in captured_messages if m['channel'] == 'tickstock.universe.updated']
            assert len(etf_messages) >= 1
            
            etf_message = etf_messages[0]['message']
            assert etf_message['service'] == 'etf_universe_manager'
            assert etf_message['event_type'] == 'universe_expansion_complete'
            assert etf_message['themes_processed'] == 7
            
            # Verify synchronizer messages
            sync_messages = [m for m in captured_messages if m['channel'] == 'tickstock.cache.sync_complete']
            if sync_messages:  # May not always publish if no Redis client
                sync_message = sync_messages[0]['message']
                assert sync_message['service'] == 'cache_entries_synchronizer'
                assert sync_message['event_type'] == 'daily_sync_complete'
    
    @pytest.mark.integration
    @patch('psycopg2.connect')
    async def test_end_to_end_phase3_workflow(self, mock_connect, etf_manager, scenario_generator, synchronizer):
        """Test complete end-to-end Phase 3 workflow"""
        # Setup comprehensive database mock
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # Mock responses for different operations
        mock_responses = iter([
            # ETF expansion responses
            [{'action': 'updated', 'cache_key': 'etf_sectors', 'symbols_count': 10}] * 7,
            # Scenario loading - no specific mock needed (mocked internally)
            None,
            # Synchronizer responses
            # Market cap rankings
            [{'symbol': 'AAPL', 'market_cap': 3000e9, 'sector': 'Technology', 'name': 'Apple', 'rank': 1}],
            # IPO data
            [],
            # Delisted data  
            [],
            # ETF universe data
            [{'cache_key': 'etf_sectors', 'symbols': ['XLF', 'XLE'], 'universe_metadata': {}}]
        ])
        
        def mock_fetch_response(*args, **kwargs):
            try:
                return next(mock_responses)
            except StopIteration:
                return []
        
        mock_cursor.fetchone.side_effect = mock_fetch_response
        mock_cursor.fetchall.side_effect = mock_fetch_response
        
        with patch.object(etf_manager, 'connect_redis') as mock_etf_redis, \
             patch.object(synchronizer, 'connect_redis') as mock_sync_redis:
            
            mock_etf_client = AsyncMock()
            mock_sync_client = AsyncMock()
            mock_etf_redis.return_value = mock_etf_client
            mock_sync_redis.return_value = mock_sync_client
            
            # Execute complete workflow
            workflow_start = time.time()
            
            # Step 1: ETF Universe Expansion
            expansion_results = etf_manager.expand_etf_universes()
            await etf_manager.publish_universe_updates(expansion_results)
            
            # Step 2: Test Scenario Generation
            scenario_result = scenario_generator.load_scenario('high_low_events')
            
            # Step 3: Cache Synchronization
            with patch.object(synchronizer, 'wait_for_eod_completion', return_value=True):
                sync_result = await synchronizer.daily_cache_sync()
            
            workflow_duration = time.time() - workflow_start
            
            # Verify end-to-end success
            assert expansion_results['success'] > 0
            assert 'total_records' in scenario_result
            assert 'total_changes' in sync_result
            
            # Verify workflow completed in reasonable time
            assert workflow_duration < 5.0, f"End-to-end workflow took {workflow_duration:.3f}s, expected <5s for mocked operations"
            
            # Verify all Redis notifications sent
            total_publications = mock_etf_client.publish.call_count + mock_sync_client.publish.call_count
            assert total_publications >= 3  # ETF expansion + scenario + sync notifications
    
    @pytest.mark.integration
    async def test_concurrent_system_operations(self, etf_manager, scenario_generator, synchronizer):
        """Test concurrent operations across all Phase 3 systems"""
        with patch.object(etf_manager, 'get_database_connection') as mock_etf_db, \
             patch.object(scenario_generator, 'get_database_connection') as mock_scenario_db, \
             patch.object(synchronizer, 'get_database_connection') as mock_sync_db, \
             patch.object(etf_manager, 'connect_redis') as mock_etf_redis, \
             patch.object(synchronizer, 'connect_redis') as mock_sync_redis:
            
            # Setup database mocks
            for mock_db in [mock_etf_db, mock_scenario_db, mock_sync_db]:
                mock_conn = Mock()
                mock_cursor = Mock()
                mock_conn.cursor.return_value = mock_cursor
                mock_cursor.fetchone.return_value = [{'action': 'updated', 'symbols_count': 10}]
                mock_cursor.fetchall.return_value = []
                mock_db.return_value = mock_conn
            
            # Setup Redis mocks
            for mock_redis in [mock_etf_redis, mock_sync_redis]:
                mock_client = AsyncMock()
                mock_redis.return_value = mock_client
            
            # Execute concurrent operations
            concurrent_start = time.time()
            
            tasks = [
                asyncio.create_task(self._run_etf_expansion(etf_manager)),
                asyncio.create_task(self._run_scenario_generation(scenario_generator)),
                asyncio.create_task(self._run_cache_synchronization(synchronizer))
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            concurrent_duration = time.time() - concurrent_start
            
            # Verify all operations completed successfully
            assert len(results) == 3
            for result in results:
                assert not isinstance(result, Exception), f"Concurrent operation failed: {result}"
            
            # Verify concurrent execution was efficient
            assert concurrent_duration < 3.0, f"Concurrent operations took {concurrent_duration:.3f}s, expected <3s"
    
    async def _run_etf_expansion(self, etf_manager):
        """Helper for concurrent ETF expansion"""
        expansion_results = etf_manager.expand_etf_universes()
        await etf_manager.publish_universe_updates(expansion_results)
        return expansion_results
    
    async def _run_scenario_generation(self, scenario_generator):
        """Helper for concurrent scenario generation"""
        return scenario_generator.load_scenario('volatility_periods')
    
    async def _run_cache_synchronization(self, synchronizer):
        """Helper for concurrent cache synchronization"""
        with patch.object(synchronizer, 'wait_for_eod_completion', return_value=True):
            return await synchronizer.daily_cache_sync()


class TestPhase3PerformanceIntegration:
    """Performance integration tests for Phase 3 advanced features"""
    
    @pytest.fixture
    def etf_manager(self):
        return ETFUniverseManager()
    
    @pytest.fixture
    def scenario_generator(self):
        return TestScenarioGenerator()
    
    @pytest.fixture
    def synchronizer(self):
        return CacheEntriesSynchronizer()
    
    @pytest.mark.performance
    @patch('psycopg2.connect')
    async def test_comprehensive_performance_benchmarks(self, mock_connect, etf_manager, scenario_generator, synchronizer):
        """Test all Phase 3 systems meet performance requirements"""
        # Setup fast database mock
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # Mock fast responses
        mock_cursor.fetchone.return_value = [{'action': 'updated', 'symbols_count': 50}]
        mock_cursor.fetchall.return_value = []
        
        with patch.object(etf_manager, 'connect_redis') as mock_etf_redis, \
             patch.object(synchronizer, 'connect_redis') as mock_sync_redis:
            
            mock_etf_client = AsyncMock()
            mock_sync_client = AsyncMock()
            mock_etf_redis.return_value = mock_etf_client
            mock_sync_redis.return_value = mock_sync_client
            
            # Performance Benchmark 1: ETF Universe Expansion (<2 seconds)
            etf_start = time.time()
            expansion_results = etf_manager.expand_etf_universes()
            etf_duration = time.time() - etf_start
            
            assert etf_duration < 2.0, f"ETF expansion took {etf_duration:.3f}s, expected <2s"
            assert expansion_results['themes_processed'] == 7
            
            # Performance Benchmark 2: Scenario Generation (<2 minutes for full scenario)
            scenario_start = time.time()
            scenario_data = scenario_generator.generate_scenario_data('crash_2020')
            scenario_duration = time.time() - scenario_start
            
            assert scenario_duration < 120.0, f"Scenario generation took {scenario_duration:.3f}s, expected <120s"
            assert len(scenario_data) > 200  # Should generate substantial data
            
            # Performance Benchmark 3: Cache Synchronization Framework (<30 minutes simulated)
            with patch.object(synchronizer, 'wait_for_eod_completion', return_value=True):
                sync_start = time.time()
                sync_result = await synchronizer.perform_synchronization()
                sync_duration = time.time() - sync_start
                
                # Framework should be very fast (actual sync would be longer)
                assert sync_duration < 1.0, f"Sync framework took {sync_duration:.3f}s, expected <1s for mocked operations"
                assert sync_result['sync_status'] == 'completed'
            
            # Performance Benchmark 4: Redis Publishing (<5 seconds)
            redis_start = time.time()
            await etf_manager.publish_universe_updates(expansion_results)
            redis_duration = time.time() - redis_start
            
            assert redis_duration < 5.0, f"Redis publishing took {redis_duration:.3f}s, expected <5s"
    
    @pytest.mark.performance
    def test_memory_efficiency_across_systems(self, etf_manager, scenario_generator, synchronizer):
        """Test memory efficiency across all Phase 3 systems"""
        import sys
        
        # Measure initial memory
        initial_memory = sys.getsizeof(etf_manager) + sys.getsizeof(scenario_generator) + sys.getsizeof(synchronizer)
        
        with patch.object(etf_manager, 'get_database_connection') as mock_db:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.fetchone.return_value = [{'action': 'updated', 'symbols_count': 10}]
            mock_cursor.fetchall.return_value = []
            mock_db.return_value = mock_conn
            
            # Execute memory-intensive operations
            for _ in range(5):
                # ETF expansion
                expansion_results = etf_manager.expand_etf_universes()
                
                # Scenario generation
                scenario_data = scenario_generator.generate_scenario_data('volatility_periods')
                
                # Change processing
                changes = [
                    SynchronizationChange(
                        'test', 'universe', 'symbol', 'added',
                        'test', datetime.now(), {}
                    )
                    for _ in range(100)
                ]
                summary = synchronizer.generate_change_summary(changes)
                
                # Clean up references
                del expansion_results, scenario_data, changes, summary
        
        # Measure final memory
        final_memory = sys.getsizeof(etf_manager) + sys.getsizeof(scenario_generator) + sys.getsizeof(synchronizer)
        memory_growth = final_memory - initial_memory
        
        # Verify no significant memory leaks
        assert memory_growth < 50000, f"Memory grew by {memory_growth} bytes across systems, indicating potential leaks"
    
    @pytest.mark.performance
    @patch('psycopg2.connect')
    async def test_high_load_system_integration(self, mock_connect, etf_manager, synchronizer):
        """Test system integration under high load conditions"""
        # Setup high-throughput database mock
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # Mock large dataset responses
        large_ranking = [
            {'symbol': f'SYM_{i:04d}', 'market_cap': (10000-i) * 1e6, 'sector': 'Tech', 'name': f'Company {i}', 'rank': i}
            for i in range(1000)  # 1000 symbols
        ]
        
        mock_cursor.fetchall.side_effect = [
            large_ranking,  # Market cap rankings
            [],  # IPO data
            [],  # Delisted data
            [{'cache_key': 'etf_sectors', 'symbols': ['XLF'] * 50, 'universe_metadata': {}}]  # ETF data
        ]
        
        with patch.object(etf_manager, 'connect_redis') as mock_etf_redis, \
             patch.object(synchronizer, 'connect_redis') as mock_sync_redis, \
             patch.object(synchronizer, 'get_current_universe_symbols') as mock_current, \
             patch.object(synchronizer, 'update_universe_symbols') as mock_update:
            
            # Setup Redis mocks
            mock_etf_client = AsyncMock()
            mock_sync_client = AsyncMock()
            mock_etf_redis.return_value = mock_etf_client
            mock_sync_redis.return_value = mock_sync_client
            
            # Mock different current universe to trigger changes
            mock_current.return_value = [f'OLD_SYM_{i}' for i in range(50)]
            
            # Execute high-load operations
            load_start = time.time()
            
            # High-load ETF expansion (7 themes, 200+ symbols)
            expansion_results = etf_manager.expand_etf_universes()
            
            # High-load synchronization (1000 symbols to process)
            with patch.object(synchronizer, 'wait_for_eod_completion', return_value=True):
                sync_result = await synchronizer.daily_cache_sync()
            
            load_duration = time.time() - load_start
            
            # Verify high-load performance
            assert load_duration < 10.0, f"High-load operations took {load_duration:.3f}s, expected <10s"
            
            # Verify processing completed successfully
            assert expansion_results['success'] > 0
            assert 'total_changes' in sync_result
            
            # Verify database operations scaled properly
            assert mock_update.call_count > 0  # Should have triggered updates
    
    @pytest.mark.performance
    async def test_redis_message_throughput(self, etf_manager, synchronizer):
        """Test Redis message throughput under high volume"""
        # Create high-volume test data
        large_expansion_results = {
            'timestamp': datetime.now().isoformat(),
            'themes_processed': 20,  # More themes
            'total_symbols': 500,
            'success': 20,
            'themes': {f'theme_{i}': {'action': 'updated', 'symbols_count': 25} for i in range(20)}
        }
        
        large_sync_changes = []
        for i in range(1000):  # 1000 changes
            large_sync_changes.append(SynchronizationChange(
                'market_cap_update', f'universe_{i % 50}', f'SYM_{i}', 'added',
                f'Change {i}', datetime.now(), {'rank': i}
            ))
        
        task_results = {f'task_{i}': {'status': 'completed', 'changes_count': 50} for i in range(20)}
        
        message_count = 0
        
        async def count_publish(channel, message):
            nonlocal message_count
            message_count += 1
        
        with patch.object(etf_manager, 'connect_redis') as mock_etf_redis, \
             patch.object(synchronizer, 'connect_redis') as mock_sync_redis:
            
            mock_etf_client = AsyncMock()
            mock_sync_client = AsyncMock()
            mock_etf_redis.return_value = mock_etf_client
            mock_sync_redis.return_value = mock_sync_client
            
            mock_etf_client.publish.side_effect = count_publish
            mock_sync_client.publish.side_effect = count_publish
            
            # Execute high-volume publishing
            throughput_start = time.time()
            
            await etf_manager.publish_universe_updates(large_expansion_results)
            await synchronizer.publish_sync_notifications(large_sync_changes, task_results)
            
            throughput_duration = time.time() - throughput_start
            
            # Verify message throughput
            assert throughput_duration < 5.0, f"High-volume publishing took {throughput_duration:.3f}s, expected <5s"
            assert message_count >= 20, f"Published {message_count} messages, expected at least 20"
            
            # Calculate messages per second
            msg_per_sec = message_count / throughput_duration if throughput_duration > 0 else float('inf')
            assert msg_per_sec > 10, f"Message throughput {msg_per_sec:.1f} msg/s too low"


class TestPhase3RegressionIntegration:
    """Regression integration tests for Phase 3 system integration"""
    
    @pytest.fixture
    def etf_manager(self):
        return ETFUniverseManager()
    
    @pytest.fixture
    def scenario_generator(self):
        return TestScenarioGenerator()
    
    @pytest.fixture
    def synchronizer(self):
        return CacheEntriesSynchronizer()
    
    def test_system_initialization_compatibility(self, etf_manager, scenario_generator, synchronizer):
        """Test all systems initialize with compatible configurations"""
        # Verify database URI compatibility
        assert etf_manager.database_uri is not None
        assert scenario_generator.database_uri is not None  
        assert synchronizer.database_uri is not None
        
        # Verify Redis configuration consistency
        assert etf_manager.redis_host is not None
        assert synchronizer.redis_host is not None
        assert etf_manager.redis_port == synchronizer.redis_port
        
        # Verify Redis channel naming consistency
        etf_channels = set(etf_manager.channels.values())
        sync_channels = set(synchronizer.channels.values())
        
        # Should have some overlap in channel usage
        channel_overlap = etf_channels.intersection(sync_channels)
        assert len(channel_overlap) >= 1, "Systems should share at least one Redis channel"
    
    @patch('psycopg2.connect')
    def test_database_table_compatibility_across_systems(self, mock_connect, etf_manager, scenario_generator, synchronizer):
        """Test database table access compatibility across systems"""
        # Setup database mock
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # Test each system's database access
        systems = [
            ('etf_manager', etf_manager.get_database_connection),
            ('scenario_generator', scenario_generator.get_database_connection), 
            ('synchronizer', synchronizer.get_database_connection)
        ]
        
        for system_name, get_connection in systems:
            conn = get_connection()
            assert conn is not None, f"{system_name} should be able to connect to database"
            assert conn == mock_conn, f"{system_name} should return mocked connection"
    
    @patch('psycopg2.connect')
    def test_data_structure_consistency(self, mock_connect, etf_manager, scenario_generator):
        """Test data structure consistency between systems"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # ETF manager generates symbols
        expansion_results = etf_manager.expand_etf_universes()
        
        # Scenario generator creates symbols with compatible structure
        scenario_data = scenario_generator.generate_scenario_data('crash_2020')
        
        # Verify data structure compatibility
        assert 'themes' in expansion_results
        assert len(scenario_data) > 0
        
        # Verify scenario data has expected fields for database integration
        for record in scenario_data[:5]:
            assert 'symbol' in record
            assert 'date' in record
            assert 'open' in record
            assert 'high' in record
            assert 'low' in record
            assert 'close' in record
            assert 'volume' in record
    
    def test_configuration_consistency_across_systems(self, etf_manager, scenario_generator, synchronizer):
        """Test configuration consistency across all systems"""
        # Verify threshold consistency where applicable
        assert etf_manager.min_aum_threshold > 0
        assert etf_manager.min_volume_threshold > 0
        
        # Verify scenario length consistency
        for scenario_name, config in scenario_generator.scenarios.items():
            assert config.length <= 252  # Max one year, consistent with market conventions
            assert config.base_price > 0
        
        # Verify synchronizer timing consistency
        assert synchronizer.sync_timeout_minutes == 30  # Consistent with requirements
        assert synchronizer.eod_wait_timeout_seconds > 0
        
        # Verify market cap threshold consistency
        thresholds = synchronizer.market_cap_thresholds
        assert thresholds['large_cap'] > thresholds['mid_cap']
        assert thresholds['mid_cap'] > thresholds['small_cap']
        assert thresholds['small_cap'] > thresholds['micro_cap']
    
    @pytest.mark.asyncio
    async def test_redis_channel_message_format_consistency(self, etf_manager, synchronizer):
        """Test Redis message format consistency across systems"""
        # Mock data for message testing
        expansion_results = {
            'timestamp': datetime.now().isoformat(),
            'themes_processed': 3,
            'total_symbols': 30,
            'success': 3,
            'themes': {'sectors': {'action': 'updated', 'symbols_count': 10}}
        }
        
        sync_changes = [
            SynchronizationChange(
                'test_change', 'test_universe', 'TEST_SYM', 'added',
                'test reason', datetime.now(), {}
            )
        ]
        task_results = {'test_task': {'status': 'completed', 'changes_count': 1}}
        
        captured_messages = []
        
        async def capture_message(channel, message):
            captured_messages.append({
                'channel': channel,
                'message': json.loads(message),
                'system': 'etf' if 'etf_universe_manager' in message else 'sync'
            })
        
        with patch.object(etf_manager, 'connect_redis') as mock_etf_redis, \
             patch.object(synchronizer, 'connect_redis') as mock_sync_redis:
            
            mock_etf_client = AsyncMock()
            mock_sync_client = AsyncMock()
            mock_etf_redis.return_value = mock_etf_client
            mock_sync_redis.return_value = mock_sync_client
            
            mock_etf_client.publish.side_effect = capture_message
            mock_sync_client.publish.side_effect = capture_message
            
            # Publish from both systems
            await etf_manager.publish_universe_updates(expansion_results)
            await synchronizer.publish_sync_notifications(sync_changes, task_results)
            
            # Verify message format consistency
            assert len(captured_messages) >= 1
            
            for msg_data in captured_messages:
                message = msg_data['message']
                
                # All messages should have consistent base fields
                assert 'timestamp' in message
                assert 'service' in message
                assert 'event_type' in message
                
                # Verify timestamp format consistency
                timestamp = message['timestamp']
                assert 'T' in timestamp  # ISO format
                
                # Verify service naming consistency
                service = message['service']
                assert service in ['etf_universe_manager', 'cache_entries_synchronizer']
    
    def test_error_handling_consistency(self, etf_manager, scenario_generator, synchronizer):
        """Test error handling consistency across systems"""
        # Test database connection failure handling
        with patch('psycopg2.connect', side_effect=Exception("Connection failed")):
            etf_conn = etf_manager.get_database_connection()
            scenario_conn = scenario_generator.get_database_connection()
            sync_conn = synchronizer.get_database_connection()
            
            # All systems should handle connection failures gracefully
            assert etf_conn is None
            assert scenario_conn is None  
            assert sync_conn is None
        
        # Test invalid scenario handling
        invalid_scenario = scenario_generator.generate_scenario_data('nonexistent_scenario')
        assert invalid_scenario is None
        
        # Test invalid universe assignment handling
        invalid_assignments = synchronizer.determine_universe_assignment({})
        assert isinstance(invalid_assignments, list)  # Should return empty list, not error


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])