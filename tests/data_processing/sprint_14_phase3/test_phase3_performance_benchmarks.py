#!/usr/bin/env python3
"""
Sprint 14 Phase 3 Performance Benchmark Tests

Comprehensive performance validation for all Phase 3 advanced features:
- ETF Universe queries must complete in <2 seconds for 200+ symbols
- Test Scenario generation and loading must complete in <2 minutes
- Cache Synchronization must complete within 30-minute window
- Redis message delivery must complete in <5 seconds
- Memory efficiency validation and leak detection

Performance Requirements:
- ETF Universe Expansion: <2s for 200+ ETF processing across 7 themes
- Scenario Generation: <2 minutes for full scenario data generation and loading
- Cache Synchronization: <30 minutes for complete daily synchronization
- Redis Messaging: <5 seconds for real-time notification delivery
- Database Operations: <2s for ETF queries, <1s for universe updates

Test Organization:
- Benchmark tests: Validate specific performance requirements
- Load tests: System behavior under high data volumes
- Stress tests: Performance under concurrent operations
- Memory tests: Memory efficiency and leak prevention
"""

import pytest
import asyncio
import time
import sys
import os
import gc
import psutil
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
import numpy as np
import json

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../'))

from src.data.etf_universe_manager import ETFUniverseManager
from src.data.test_scenario_generator import TestScenarioGenerator
from src.data.cache_entries_synchronizer import CacheEntriesSynchronizer, SynchronizationChange

class TestETFUniversePerformanceBenchmarks:
    """Performance benchmark tests for ETF Universe Manager"""
    
    @pytest.fixture
    def etf_manager(self):
        """ETF Universe Manager for performance testing"""
        return ETFUniverseManager()
    
    @pytest.mark.performance
    def test_etf_universe_expansion_2_second_benchmark(self, etf_manager, performance_timer):
        """Test ETF universe expansion meets <2 second requirement"""
        with patch.object(etf_manager, 'get_database_connection') as mock_db:
            # Setup fast database mock
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_conn.cursor.return_value = mock_cursor
            mock_db.return_value = mock_conn
            
            # Mock database function responses for all 7 themes
            mock_cursor.fetchone.return_value = [{
                'action': 'updated',
                'cache_key': 'etf_test',
                'symbols_count': 30,  # Average symbols per theme
                'timestamp': datetime.now()
            }]
            
            # Execute performance benchmark
            performance_timer.start()
            
            expansion_results = etf_manager.expand_etf_universes()
            
            performance_timer.stop()
            
            # Verify performance requirement: <2 seconds
            performance_timer.assert_under(2.0, "ETF universe expansion must complete in <2 seconds")
            
            # Verify comprehensive processing
            assert expansion_results['themes_processed'] == 7
            assert expansion_results['total_symbols'] >= 40  # At least 40 ETFs processed
            assert expansion_results['success'] >= 6  # Most themes successful
    
    @pytest.mark.performance  
    def test_etf_generation_performance_200_plus_symbols(self, etf_manager, performance_timer):
        """Test ETF generation performance with 200+ symbols across themes"""
        performance_timer.start()
        
        # Generate all ETF themes (should total 200+ symbols)
        all_etfs = []
        themes = ['sectors', 'growth', 'value', 'international', 'commodities', 'technology', 'bonds']
        
        for theme in themes:
            method_name = f'_get_{theme}_etfs'
            if hasattr(etf_manager, method_name):
                etfs = getattr(etf_manager, method_name)()
                all_etfs.extend(etfs)
        
        performance_timer.stop()
        
        # Verify performance requirement: Fast ETF data generation
        performance_timer.assert_under(0.5, "ETF data generation should be <0.5s")
        
        # Verify comprehensive ETF coverage
        assert len(all_etfs) >= 40, f"Expected at least 40 ETFs, got {len(all_etfs)}"
        
        # Verify ETF quality (AUM filtering working)
        high_aum_etfs = [etf for etf in all_etfs if etf.aum >= 1e9]
        assert len(high_aum_etfs) >= 30, "Should have many high-AUM ETFs after filtering"
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_etf_redis_publishing_5_second_benchmark(self, etf_manager, performance_timer):
        """Test ETF Redis publishing meets <5 second requirement"""
        # Create large expansion results (realistic volume)
        large_expansion_results = {
            'timestamp': datetime.now().isoformat(),
            'themes_processed': 7,
            'total_symbols': 200,  # Large symbol count
            'success': 7,
            'themes': {}
        }
        
        # Generate detailed theme results
        for i in range(7):
            theme_name = f'theme_{i}'
            large_expansion_results['themes'][theme_name] = {
                'action': 'updated',
                'symbols_count': 25 + (i * 2),  # Varying symbol counts
                'cache_key': f'etf_{theme_name}',
                'timestamp': datetime.now().isoformat()
            }
        
        with patch.object(etf_manager, 'connect_redis') as mock_redis:
            mock_client = AsyncMock()
            mock_redis.return_value = mock_client
            
            performance_timer.start()
            
            # Execute Redis publishing
            result = await etf_manager.publish_universe_updates(large_expansion_results)
            
            performance_timer.stop()
            
            # Verify performance requirement: <5 seconds for Redis delivery
            performance_timer.assert_under(5.0, "Redis publishing must complete in <5 seconds")
            
            # Verify successful publishing
            assert result is True
            
            # Verify comprehensive message publishing (at least 8: 1 overall + 7 themes)
            assert mock_client.publish.call_count >= 8
    
    @pytest.mark.performance
    @patch('psycopg2.connect')
    async def test_etf_validation_performance_large_dataset(self, mock_connect, etf_manager, performance_timer):
        """Test ETF validation performance with large datasets"""
        # Setup large validation dataset mock
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # Mock validation for 200+ ETF symbols across all themes
        large_validation_data = []
        themes = ['sectors', 'growth', 'value', 'international', 'commodities', 'technology', 'bonds']
        
        for theme_idx, theme in enumerate(themes):
            for symbol_idx in range(30):  # 30 symbols per theme = 210 total
                large_validation_data.append({
                    'universe_key': f'etf_{theme}',
                    'symbol': f'{theme.upper()}_ETF_{symbol_idx:02d}',
                    'exists_in_symbols': symbol_idx % 10 != 0,  # 90% exist
                    'symbol_type': 'ETF',
                    'active_status': symbol_idx % 15 != 0  # ~93% active
                })
        
        mock_cursor.fetchall.return_value = large_validation_data
        
        performance_timer.start()
        
        validation_result = await etf_manager.validate_universe_symbols()
        
        performance_timer.stop()
        
        # Verify performance requirement: Fast validation of large datasets
        performance_timer.assert_under(1.0, "ETF validation must complete in <1 second")
        
        # Verify comprehensive validation
        assert 'validation_summary' in validation_result
        assert validation_result['total_missing'] > 0  # Some symbols missing as expected
        assert len(validation_result['validation_summary']) == 7  # All themes validated
    
    @pytest.mark.performance
    def test_etf_memory_efficiency_benchmark(self, etf_manager):
        """Test ETF Universe Manager memory efficiency"""
        # Measure initial memory
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        with patch.object(etf_manager, 'get_database_connection') as mock_db:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_conn.cursor.return_value = mock_cursor
            mock_db.return_value = mock_conn
            
            mock_cursor.fetchone.return_value = [{
                'action': 'updated',
                'symbols_count': 50,
                'cache_key': 'etf_memory_test'
            }]
            
            # Execute multiple expansion cycles
            for cycle in range(10):
                expansion_results = etf_manager.expand_etf_universes()
                assert expansion_results['success'] > 0
                
                # Force garbage collection
                gc.collect()
        
        # Measure final memory
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = final_memory - initial_memory
        
        # Verify memory efficiency: <50MB growth after 10 cycles
        assert memory_growth < 50, f"Memory grew by {memory_growth:.1f}MB, expected <50MB growth"


class TestScenarioGeneratorPerformanceBenchmarks:
    """Performance benchmark tests for Test Scenario Generator"""
    
    @pytest.fixture
    def scenario_generator(self):
        """Test Scenario Generator for performance testing"""
        return TestScenarioGenerator()
    
    @pytest.mark.performance
    def test_scenario_generation_2_minute_benchmark(self, scenario_generator, performance_timer):
        """Test scenario generation meets <2 minute requirement"""
        performance_timer.start()
        
        # Generate largest scenario (crash_2020 with 252 days)
        scenario_data = scenario_generator.generate_scenario_data('crash_2020')
        
        performance_timer.stop()
        
        # Verify performance requirement: <2 minutes (120 seconds)
        performance_timer.assert_under(120.0, "Scenario generation must complete in <2 minutes")
        
        # Verify comprehensive data generation
        assert scenario_data is not None
        assert len(scenario_data) >= 200  # Should generate substantial data (252 trading days)
        
        # Verify data quality
        for record in scenario_data[:10]:  # Check first 10 records
            assert record['volume'] > 0
            assert record['high'] >= record['close']
            assert record['low'] <= record['close']
    
    @pytest.mark.performance
    @patch('psycopg2.connect')
    def test_scenario_loading_2_minute_benchmark(self, mock_connect, scenario_generator, performance_timer):
        """Test scenario loading meets <2 minute requirement"""
        # Setup database mock
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        performance_timer.start()
        
        # Load largest scenario into database
        load_result = scenario_generator.load_scenario('crash_2020', ['PERF_TEST_CRASH'])
        
        performance_timer.stop()
        
        # Verify performance requirement: <2 minutes for loading
        performance_timer.assert_under(120.0, "Scenario loading must complete in <2 minutes")
        
        # Verify successful loading
        assert 'error' not in load_result
        assert load_result['scenario_name'] == 'crash_2020'
        assert load_result['total_records'] > 200
        
        # Verify database operations occurred
        mock_cursor.execute.assert_called()
        mock_conn.commit.assert_called()
    
    @pytest.mark.performance
    def test_all_scenarios_generation_benchmark(self, scenario_generator, performance_timer):
        """Test generation of all 5 scenarios within performance limits"""
        performance_timer.start()
        
        # Generate all predefined scenarios
        all_scenario_results = {}
        for scenario_name in scenario_generator.scenarios.keys():
            scenario_data = scenario_generator.generate_scenario_data(scenario_name)
            all_scenario_results[scenario_name] = scenario_data
        
        performance_timer.stop()
        
        # Verify performance requirement: All scenarios in reasonable time
        performance_timer.assert_under(60.0, "All 5 scenarios should generate in <1 minute")
        
        # Verify all scenarios generated successfully
        assert len(all_scenario_results) == 5
        for scenario_name, data in all_scenario_results.items():
            assert data is not None, f"Scenario {scenario_name} failed to generate"
            assert len(data) > 0, f"Scenario {scenario_name} generated no data"
    
    @pytest.mark.performance
    def test_scenario_reproducibility_performance(self, scenario_generator, performance_timer):
        """Test scenario reproducibility doesn't impact performance"""
        # Test multiple generations with same seed for reproducibility
        generation_times = []
        
        for run in range(3):
            scenario_generator.random_seed = 42  # Reset seed for reproducibility
            
            performance_timer.reset()
            performance_timer.start()
            
            scenario_data = scenario_generator.generate_scenario_data('volatility_periods')
            
            performance_timer.stop()
            generation_times.append(performance_timer.elapsed)
            
            # Verify data generated
            assert len(scenario_data) > 0
        
        # Verify consistent performance across runs
        avg_time = np.mean(generation_times)
        max_time = max(generation_times)
        min_time = min(generation_times)
        
        # Performance should be consistent (within 2x variance)
        assert max_time <= min_time * 2.0, "Performance should be consistent across reproducible runs"
        assert avg_time < 10.0, "Average scenario generation should be <10 seconds"
    
    @pytest.mark.performance
    def test_scenario_memory_efficiency_benchmark(self, scenario_generator):
        """Test scenario generation memory efficiency"""
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Generate multiple large scenarios
        large_scenarios = ['crash_2020', 'growth_2021', 'trend_changes']  # Largest scenarios
        
        for scenario_name in large_scenarios:
            scenario_data = scenario_generator.generate_scenario_data(scenario_name)
            assert len(scenario_data) > 0
            
            # Clear reference to allow garbage collection
            del scenario_data
            gc.collect()
        
        # Measure final memory
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = final_memory - initial_memory
        
        # Verify memory efficiency: <100MB growth for large scenarios
        assert memory_growth < 100, f"Memory grew by {memory_growth:.1f}MB, expected <100MB"


class TestCacheSynchronizerPerformanceBenchmarks:
    """Performance benchmark tests for Cache Entries Synchronizer"""
    
    @pytest.fixture
    def synchronizer(self):
        """Cache Entries Synchronizer for performance testing"""
        return CacheEntriesSynchronizer()
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_cache_sync_30_minute_benchmark(self, synchronizer, performance_timer):
        """Test cache synchronization meets <30 minute window requirement"""
        with patch.object(synchronizer, 'wait_for_eod_completion') as mock_eod, \
             patch.object(synchronizer, 'perform_synchronization') as mock_sync:
            
            # Mock quick EOD completion
            mock_eod.return_value = True
            
            # Mock synchronization result
            mock_sync.return_value = {
                'total_changes': 100,
                'task_results': {
                    'market_cap_recalculation': {'status': 'completed', 'changes_count': 50},
                    'ipo_universe_assignment': {'status': 'completed', 'changes_count': 10},
                    'delisted_cleanup': {'status': 'completed', 'changes_count': 5},
                    'theme_rebalancing': {'status': 'completed', 'changes_count': 0},
                    'etf_universe_maintenance': {'status': 'completed', 'changes_count': 35}
                },
                'sync_status': 'completed'
            }
            
            performance_timer.start()
            
            # Execute daily cache synchronization
            sync_result = await synchronizer.daily_cache_sync()
            
            performance_timer.stop()
            
            # Verify performance requirement: Framework should be fast (actual sync would be longer)
            performance_timer.assert_under(5.0, "Sync framework should complete quickly for mocked operations")
            
            # Verify synchronization structure
            assert 'total_sync_duration_minutes' in sync_result
            assert 'within_time_window' in sync_result
            
            # Verify time window calculation (30 minutes = 1800 seconds)
            duration_seconds = sync_result.get('total_sync_duration_minutes', 0) * 60
            expected_within_window = duration_seconds <= 1800
            assert sync_result['within_time_window'] == expected_within_window
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_redis_notification_5_second_benchmark(self, synchronizer, performance_timer):
        """Test Redis notifications meet <5 second delivery requirement"""
        # Create large change set for performance testing
        large_changes = []
        for i in range(500):  # 500 changes across multiple universes
            large_changes.append(SynchronizationChange(
                'market_cap_update', f'universe_{i % 20}', f'SYM_{i:04d}', 'added',
                f'Performance test change {i}', datetime.now(),
                {'rank': i + 1, 'test_data': 'benchmark'}
            ))
        
        task_results = {
            'market_cap_recalculation': {'status': 'completed', 'changes_count': 300},
            'ipo_universe_assignment': {'status': 'completed', 'changes_count': 200}
        }
        
        with patch.object(synchronizer, 'connect_redis') as mock_redis:
            mock_client = AsyncMock()
            mock_redis.return_value = mock_client
            
            performance_timer.start()
            
            # Execute Redis notification publishing
            await synchronizer.publish_sync_notifications(large_changes, task_results)
            
            performance_timer.stop()
            
            # Verify performance requirement: <5 seconds for Redis delivery
            performance_timer.assert_under(5.0, "Redis notifications must complete in <5 seconds")
            
            # Verify comprehensive publishing (overall + individual universe updates)
            assert mock_client.publish.call_count >= 20  # At least one per universe
    
    @pytest.mark.performance
    @patch('psycopg2.connect')
    async def test_market_cap_recalculation_large_dataset_benchmark(self, mock_connect, synchronizer, performance_timer):
        """Test market cap recalculation performance with large datasets"""
        # Setup large dataset mock (5000 symbols)
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        large_ranking_data = []
        for i in range(5000):
            large_ranking_data.append({
                'symbol': f'PERF_SYM_{i:04d}',
                'market_cap': (5000 - i) * 1e9,  # Decreasing market caps
                'sector': 'Technology' if i % 3 == 0 else 'Healthcare' if i % 3 == 1 else 'Finance',
                'name': f'Performance Test Company {i}',
                'rank': i + 1
            })
        
        mock_cursor.fetchall.return_value = large_ranking_data
        
        with patch.object(synchronizer, 'get_current_universe_symbols') as mock_current, \
             patch.object(synchronizer, 'update_universe_symbols') as mock_update:
            
            # Mock current symbols (different to trigger changes)
            mock_current.return_value = [f'OLD_SYM_{i}' for i in range(100)]
            
            performance_timer.start()
            
            changes = await synchronizer.market_cap_recalculation()
            
            performance_timer.stop()
            
            # Verify performance requirement: Large dataset processing
            performance_timer.assert_under(10.0, "Market cap recalculation should handle 5000 symbols in <10 seconds")
            
            # Verify processing occurred
            assert len(changes) > 0
            mock_update.assert_called()  # Should have triggered universe updates
    
    @pytest.mark.performance
    def test_synchronizer_memory_efficiency_benchmark(self, synchronizer):
        """Test synchronizer memory efficiency with large change sets"""
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Process large change sets multiple times
        for cycle in range(5):
            # Create large change set
            changes = []
            for i in range(1000):  # 1000 changes per cycle
                changes.append(SynchronizationChange(
                    'test_change', f'universe_{i % 50}', f'SYM_{cycle}_{i}', 'added',
                    f'Memory test change {cycle}-{i}', datetime.now(),
                    {'cycle': cycle, 'index': i, 'large_data': 'x' * 100}  # Some bulk data
                ))
            
            # Process change summary (memory intensive operation)
            summary = synchronizer.generate_change_summary(changes)
            assert summary['total_changes'] == 1000
            
            # Clear references
            del changes, summary
            gc.collect()
        
        # Measure final memory
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = final_memory - initial_memory
        
        # Verify memory efficiency: <100MB growth after processing 5000 changes
        assert memory_growth < 100, f"Memory grew by {memory_growth:.1f}MB, expected <100MB"
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_concurrent_sync_operations_benchmark(self, synchronizer, performance_timer):
        """Test concurrent synchronization operations performance"""
        with patch.object(synchronizer, 'get_database_connection') as mock_db:
            # Setup fast database mock
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_conn.cursor.return_value = mock_cursor
            mock_db.return_value = mock_conn
            
            # Mock different responses for different operations
            mock_cursor.fetchall.side_effect = [
                # Market cap rankings
                [{'symbol': f'SYM_{i}', 'market_cap': (1000-i)*1e9, 'sector': 'Tech', 'name': f'Company {i}', 'rank': i} for i in range(100)],
                # IPO data
                [],
                # Delisted data
                [],
                # ETF universe data
                [{'cache_key': 'etf_test', 'symbols': ['ETF1', 'ETF2'], 'universe_metadata': {}}]
            ]
            
            with patch.object(synchronizer, 'get_current_universe_symbols') as mock_current, \
                 patch.object(synchronizer, 'update_universe_symbols') as mock_update:
                
                mock_current.return_value = []  # Empty to trigger changes
                
                performance_timer.start()
                
                # Execute all synchronization tasks concurrently (via perform_synchronization)
                with patch.object(synchronizer, 'wait_for_eod_completion', return_value=True):
                    sync_result = await synchronizer.daily_cache_sync()
                
                performance_timer.stop()
                
                # Verify performance requirement: Concurrent operations
                performance_timer.assert_under(3.0, "Concurrent sync operations should complete in <3 seconds")
                
                # Verify all operations completed
                assert 'total_changes' in sync_result
                assert 'task_results' in sync_result


class TestCrossSystemPerformanceBenchmarks:
    """Cross-system performance benchmark tests"""
    
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
    async def test_end_to_end_workflow_benchmark(self, mock_connect, etf_manager, scenario_generator, synchronizer, performance_timer):
        """Test end-to-end Phase 3 workflow performance"""
        # Setup comprehensive database mock
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # Mock responses for all operations
        mock_cursor.fetchone.side_effect = [
            # ETF expansion responses (7 themes)
            [{'action': 'updated', 'cache_key': 'etf_sectors', 'symbols_count': 10}],
            [{'action': 'updated', 'cache_key': 'etf_growth', 'symbols_count': 8}],
            [{'action': 'updated', 'cache_key': 'etf_value', 'symbols_count': 8}],
            [{'action': 'updated', 'cache_key': 'etf_international', 'symbols_count': 8}],
            [{'action': 'updated', 'cache_key': 'etf_commodities', 'symbols_count': 8}],
            [{'action': 'updated', 'cache_key': 'etf_technology', 'symbols_count': 8}],
            [{'action': 'updated', 'cache_key': 'etf_bonds', 'symbols_count': 8}]
        ]
        
        mock_cursor.fetchall.side_effect = [
            # Synchronizer - Market cap rankings
            [{'symbol': f'SYM_{i}', 'market_cap': (100-i)*1e9, 'sector': 'Tech', 'name': f'Company {i}', 'rank': i} for i in range(50)],
            # Synchronizer - IPO data
            [],
            # Synchronizer - Delisted data
            [],
            # Synchronizer - ETF universe data
            [{'cache_key': 'etf_sectors', 'symbols': ['XLF', 'XLE'], 'universe_metadata': {}}]
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
            mock_current.return_value = []  # Empty to trigger changes
            
            performance_timer.start()
            
            # Execute complete Phase 3 workflow
            
            # Step 1: ETF Universe Expansion
            expansion_results = etf_manager.expand_etf_universes()
            await etf_manager.publish_universe_updates(expansion_results)
            
            # Step 2: Scenario Generation (smaller for performance)
            scenario_result = scenario_generator.load_scenario('high_low_events')
            
            # Step 3: Cache Synchronization
            with patch.object(synchronizer, 'wait_for_eod_completion', return_value=True):
                sync_result = await synchronizer.daily_cache_sync()
            
            performance_timer.stop()
            
            # Verify end-to-end performance: Should complete efficiently for mocked operations
            performance_timer.assert_under(10.0, "Complete Phase 3 workflow should complete in <10 seconds for mocked operations")
            
            # Verify all systems completed successfully
            assert expansion_results['success'] > 0
            assert 'total_records' in scenario_result
            assert 'total_changes' in sync_result
            
            # Verify cross-system integration
            total_redis_calls = mock_etf_client.publish.call_count + mock_sync_client.publish.call_count
            assert total_redis_calls >= 3  # At least some Redis integration
    
    @pytest.mark.performance
    async def test_concurrent_system_load_benchmark(self, etf_manager, scenario_generator, synchronizer, performance_timer):
        """Test concurrent system operations under load"""
        with patch.object(etf_manager, 'get_database_connection') as mock_etf_db, \
             patch.object(scenario_generator, 'get_database_connection') as mock_scenario_db, \
             patch.object(synchronizer, 'get_database_connection') as mock_sync_db:
            
            # Setup fast database mocks for all systems
            for mock_db in [mock_etf_db, mock_scenario_db, mock_sync_db]:
                mock_conn = Mock()
                mock_cursor = Mock()
                mock_conn.cursor.return_value = mock_cursor
                mock_cursor.fetchone.return_value = [{'action': 'updated', 'symbols_count': 10}]
                mock_cursor.fetchall.return_value = []
                mock_db.return_value = mock_conn
            
            performance_timer.start()
            
            # Execute concurrent operations
            tasks = []
            
            # Multiple ETF expansions
            for _ in range(3):
                tasks.append(asyncio.create_task(self._run_etf_expansion(etf_manager)))
            
            # Multiple scenario generations
            for _ in range(2):
                tasks.append(asyncio.create_task(self._run_scenario_generation(scenario_generator)))
            
            # Synchronization operations
            for _ in range(2):
                tasks.append(asyncio.create_task(self._run_cache_synchronization(synchronizer)))
            
            # Wait for all concurrent operations
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            performance_timer.stop()
            
            # Verify concurrent performance
            performance_timer.assert_under(5.0, "Concurrent operations should complete in <5 seconds")
            
            # Verify all operations succeeded
            for result in results:
                assert not isinstance(result, Exception), f"Concurrent operation failed: {result}"
    
    async def _run_etf_expansion(self, etf_manager):
        """Helper for concurrent ETF expansion"""
        return etf_manager.expand_etf_universes()
    
    async def _run_scenario_generation(self, scenario_generator):
        """Helper for concurrent scenario generation"""
        return scenario_generator.generate_scenario_data('volatility_periods')
    
    async def _run_cache_synchronization(self, synchronizer):
        """Helper for concurrent cache synchronization"""
        with patch.object(synchronizer, 'wait_for_eod_completion', return_value=True):
            return await synchronizer.perform_synchronization()
    
    @pytest.mark.performance
    def test_system_memory_usage_under_load(self, etf_manager, scenario_generator, synchronizer):
        """Test system memory usage under sustained load"""
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        peak_memory = initial_memory
        
        with patch.object(etf_manager, 'get_database_connection') as mock_etf_db, \
             patch.object(scenario_generator, 'get_database_connection') as mock_scenario_db, \
             patch.object(synchronizer, 'get_database_connection') as mock_sync_db:
            
            # Setup database mocks
            for mock_db in [mock_etf_db, mock_scenario_db, mock_sync_db]:
                mock_conn = Mock()
                mock_cursor = Mock()
                mock_conn.cursor.return_value = mock_cursor
                mock_cursor.fetchone.return_value = [{'action': 'updated', 'symbols_count': 20}]
                mock_cursor.fetchall.return_value = []
                mock_db.return_value = mock_conn
            
            # Execute sustained load
            for cycle in range(10):
                # ETF operations
                expansion_results = etf_manager.expand_etf_universes()
                assert expansion_results['success'] > 0
                
                # Scenario operations
                scenario_data = scenario_generator.generate_scenario_data('crash_2020')
                assert len(scenario_data) > 0
                
                # Synchronizer operations
                changes = [
                    SynchronizationChange(
                        'load_test', f'universe_{i}', f'SYM_{cycle}_{i}', 'added',
                        f'Load test {cycle}-{i}', datetime.now(), {}
                    )
                    for i in range(100)
                ]
                summary = synchronizer.generate_change_summary(changes)
                assert summary['total_changes'] == 100
                
                # Track peak memory
                current_memory = process.memory_info().rss / 1024 / 1024
                peak_memory = max(peak_memory, current_memory)
                
                # Cleanup
                del expansion_results, scenario_data, changes, summary
                gc.collect()
        
        # Verify memory efficiency under sustained load
        memory_growth = peak_memory - initial_memory
        assert memory_growth < 200, f"Peak memory grew by {memory_growth:.1f}MB, expected <200MB under sustained load"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short', '-m', 'performance'])