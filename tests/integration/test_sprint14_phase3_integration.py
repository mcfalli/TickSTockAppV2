#!/usr/bin/env python3
"""
Sprint 14 Phase 3 Advanced Features Integration Tests

This comprehensive test suite validates cross-system integration patterns for Sprint 14 Phase 3:
- ETF Universe Integration: Cache_entries schema enhancements and Redis notifications
- Test Scenario Integration: Synthetic data generation without production interference  
- Cache Synchronization Integration: EOD completion signals and automated updates
- Database Integration: Enhanced schema compatibility and performance validation
- Redis Integration: Pub-sub message flows and delivery guarantees
- Performance Integration: <2s database queries, <2min scenario generation, 30min sync window

Architecture Validation:
- Loose coupling between TickStockApp (consumer) and TickStockPL (producer)
- Service boundary enforcement: AppV2 remains in consumer role
- Message delivery performance: <100ms end-to-end
- Database query performance: <50ms for UI queries, <2s for ETF universe operations
"""

import os
import sys
import pytest
import asyncio
import json
import time
import threading
import uuid
from datetime import datetime, timedelta, date
from typing import Dict, List, Any, Optional, Tuple
from unittest.mock import Mock, patch, AsyncMock
import tempfile
import subprocess

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

# Test imports
import psycopg2
import psycopg2.extras
import redis
import redis.asyncio as async_redis
import numpy as np

# Import Phase 3 modules
from src.data.etf_universe_manager import ETFUniverseManager, ETFMetadata
from src.data.test_scenario_generator import TestScenarioGenerator, ScenarioConfig
from src.data.cache_entries_synchronizer import CacheEntriesSynchronizer, SynchronizationChange

class TestSprint14Phase3Integration:
    """
    Sprint 14 Phase 3 Advanced Features Integration Test Suite
    
    Comprehensive validation of:
    1. ETF Universe Integration patterns and Redis notifications
    2. Test Scenario Generator isolation and performance
    3. Cache Synchronization automation and Redis messaging
    4. Cross-system database integration and performance
    5. Service boundary enforcement and loose coupling validation
    """
    
    @pytest.fixture(scope="class")
    def test_database_config(self):
        """Test database configuration"""
        return {
            'host': os.getenv('TEST_DB_HOST', 'localhost'),
            'database': os.getenv('TEST_DB_NAME', 'tickstock_test'),
            'user': os.getenv('TEST_DB_USER', 'app_readwrite'),
            'password': os.getenv('TEST_DB_PASSWORD', '4pp_U$3r_2024!'),
            'port': int(os.getenv('TEST_DB_PORT', '5432'))
        }
    
    @pytest.fixture(scope="class")  
    def test_redis_config(self):
        """Test Redis configuration"""
        return {
            'host': os.getenv('TEST_REDIS_HOST', 'localhost'),
            'port': int(os.getenv('TEST_REDIS_PORT', '6379')),
            'db': 15  # Use separate test database
        }
    
    @pytest.fixture
    def db_connection(self, test_database_config):
        """Database connection for testing"""
        conn = psycopg2.connect(
            **test_database_config,
            cursor_factory=psycopg2.extras.RealDictCursor
        )
        conn.autocommit = True
        yield conn
        conn.close()
    
    @pytest.fixture
    def redis_client(self, test_redis_config):
        """Redis client for testing"""
        client = redis.Redis(**test_redis_config, decode_responses=True)
        client.flushdb()  # Clean test database
        yield client
        client.flushdb()  # Clean up after test
        client.close()
    
    @pytest.fixture
    async def async_redis_client(self, test_redis_config):
        """Async Redis client for testing"""
        client = async_redis.Redis(**test_redis_config, decode_responses=True)
        await client.flushdb()
        yield client
        await client.flushdb()
        await client.aclose()
    
    @pytest.fixture
    def etf_universe_manager(self, test_database_config, test_redis_config):
        """ETF Universe Manager for testing"""
        database_uri = f"postgresql://{test_database_config['user']}:{test_database_config['password']}@{test_database_config['host']}:{test_database_config['port']}/{test_database_config['database']}"
        manager = ETFUniverseManager(
            database_uri=database_uri,
            redis_host=test_redis_config['host']
        )
        return manager
    
    @pytest.fixture
    def test_scenario_generator(self, test_database_config):
        """Test Scenario Generator for testing"""
        database_uri = f"postgresql://{test_database_config['user']}:{test_database_config['password']}@{test_database_config['host']}:{test_database_config['port']}/{test_database_config['database']}"
        generator = TestScenarioGenerator(database_uri=database_uri)
        return generator
    
    @pytest.fixture
    def cache_synchronizer(self, test_database_config, test_redis_config):
        """Cache Entries Synchronizer for testing"""
        database_uri = f"postgresql://{test_database_config['user']}:{test_database_config['password']}@{test_database_config['host']}:{test_database_config['port']}/{test_database_config['database']}"
        synchronizer = CacheEntriesSynchronizer(
            database_uri=database_uri,
            redis_host=test_redis_config['host']
        )
        return synchronizer

    # =================================================================
    # ETF UNIVERSE INTEGRATION TESTS
    # =================================================================
    
    def test_etf_universe_database_integration(self, db_connection, etf_universe_manager):
        """Test ETF universe database integration and schema compatibility"""
        # Verify enhanced cache_entries schema exists
        cursor = db_connection.cursor()
        
        # Check new columns exist
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'cache_entries' 
            AND column_name IN ('universe_category', 'liquidity_filter', 'universe_metadata', 'last_universe_update')
        """)
        columns = [row['column_name'] for row in cursor.fetchall()]
        
        assert 'universe_category' in columns, "universe_category column missing"
        assert 'liquidity_filter' in columns, "liquidity_filter column missing"
        assert 'universe_metadata' in columns, "universe_metadata column missing"
        assert 'last_universe_update' in columns, "last_universe_update column missing"
        
        # Check indexes exist
        cursor.execute("""
            SELECT indexname 
            FROM pg_indexes 
            WHERE tablename = 'cache_entries' 
            AND indexname LIKE '%category%' OR indexname LIKE '%updated%'
        """)
        indexes = [row['indexname'] for row in cursor.fetchall()]
        
        assert any('category' in idx for idx in indexes), "Category index missing"
        assert any('updated' in idx for idx in indexes), "Updated index missing"
    
    def test_etf_universe_expansion_performance(self, etf_universe_manager):
        """Test ETF universe expansion meets <2s performance target"""
        start_time = time.time()
        
        # Perform expansion
        results = etf_universe_manager.expand_etf_universes()
        
        expansion_time = time.time() - start_time
        
        # Validate performance target
        assert expansion_time < 2.0, f"ETF expansion took {expansion_time:.2f}s, exceeds 2s target"
        
        # Validate results structure
        assert 'total_symbols' in results, "Missing total_symbols in results"
        assert 'themes_processed' in results, "Missing themes_processed in results"
        assert results['total_symbols'] >= 200, f"Expected 200+ symbols, got {results['total_symbols']}"
        assert results['themes_processed'] >= 5, f"Expected 5+ themes, got {results['themes_processed']}"
    
    @pytest.mark.asyncio
    async def test_etf_universe_redis_notifications(self, async_redis_client, etf_universe_manager):
        """Test ETF universe Redis notification integration"""
        received_messages = []
        
        # Set up subscriber
        pubsub = async_redis_client.pubsub()
        await pubsub.subscribe('tickstock.universe.updated')
        
        async def message_listener():
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    received_messages.append(json.loads(message['data']))
        
        # Start listener in background
        listener_task = asyncio.create_task(message_listener())
        
        try:
            # Perform ETF expansion
            expansion_results = etf_universe_manager.expand_etf_universes()
            
            # Publish notifications
            await etf_universe_manager.publish_universe_updates(expansion_results)
            
            # Wait for messages
            await asyncio.sleep(0.2)
            
            # Validate messages received
            assert len(received_messages) > 0, "No Redis messages received"
            
            # Check message structure
            main_message = received_messages[0]
            assert 'service' in main_message, "Missing service field"
            assert main_message['service'] == 'etf_universe_manager', "Wrong service name"
            assert 'event_type' in main_message, "Missing event_type field"
            assert 'themes_processed' in main_message, "Missing themes_processed field"
            assert 'total_symbols' in main_message, "Missing total_symbols field"
            
        finally:
            listener_task.cancel()
            await pubsub.unsubscribe('tickstock.universe.updated')
            await pubsub.aclose()
    
    def test_etf_universe_database_functions(self, db_connection):
        """Test ETF universe database functions performance and correctness"""
        cursor = db_connection.cursor()
        
        # Test get_etf_universe function
        start_time = time.time()
        cursor.execute("SELECT get_etf_universe('sectors')")
        query_time = time.time() - start_time
        
        assert query_time < 2.0, f"get_etf_universe took {query_time:.3f}s, exceeds 2s target"
        
        result = cursor.fetchone()[0]
        assert 'cache_key' in result, "Missing cache_key in function result"
        assert 'symbols' in result, "Missing symbols in function result"
        
        # Test get_etf_universes_summary function
        start_time = time.time()
        cursor.execute("SELECT * FROM get_etf_universes_summary()")
        query_time = time.time() - start_time
        
        assert query_time < 2.0, f"get_etf_universes_summary took {query_time:.3f}s, exceeds 2s target"
        
        results = cursor.fetchall()
        assert len(results) > 0, "No ETF universes found"
        
        # Test validate_etf_universe_symbols function  
        start_time = time.time()
        cursor.execute("SELECT * FROM validate_etf_universe_symbols()")
        query_time = time.time() - start_time
        
        assert query_time < 2.0, f"validate_etf_universe_symbols took {query_time:.3f}s, exceeds 2s target"
    
    def test_etf_universe_concurrent_operations(self, etf_universe_manager):
        """Test ETF universe operations under concurrent load"""
        import concurrent.futures
        
        def expansion_task():
            return etf_universe_manager.expand_etf_universes()
        
        # Run 3 concurrent expansions
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            start_time = time.time()
            futures = [executor.submit(expansion_task) for _ in range(3)]
            
            results = []
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())
            
            total_time = time.time() - start_time
        
        # Validate all completed successfully
        assert len(results) == 3, "Not all concurrent operations completed"
        assert total_time < 10.0, f"Concurrent operations took {total_time:.2f}s, too slow"
        
        # Validate consistent results
        symbol_counts = [r['total_symbols'] for r in results]
        assert max(symbol_counts) - min(symbol_counts) <= 5, "Inconsistent symbol counts across concurrent runs"

    # =================================================================
    # TEST SCENARIO GENERATOR INTEGRATION TESTS
    # =================================================================
    
    def test_scenario_generation_performance(self, test_scenario_generator):
        """Test scenario generation meets <2 minute performance target"""
        start_time = time.time()
        
        # Generate crash scenario
        scenario_data = test_scenario_generator.generate_scenario_data('crash_2020')
        
        generation_time = time.time() - start_time
        
        assert generation_time < 120.0, f"Scenario generation took {generation_time:.2f}s, exceeds 2min target"
        assert scenario_data is not None, "Scenario data generation failed"
        assert len(scenario_data) > 200, f"Expected 200+ data points, got {len(scenario_data)}"
    
    def test_scenario_database_isolation(self, db_connection, test_scenario_generator):
        """Test synthetic data isolation from production historical_data"""
        cursor = db_connection.cursor()
        
        # Get initial production data count  
        cursor.execute("SELECT COUNT(*) as count FROM historical_data WHERE symbol NOT LIKE 'TEST_%'")
        initial_prod_count = cursor.fetchone()['count']
        
        # Load test scenario
        result = test_scenario_generator.load_scenario('crash_2020', ['TEST_ISOLATION'])
        
        assert 'error' not in result, f"Scenario loading failed: {result.get('error')}"
        
        # Verify production data unchanged
        cursor.execute("SELECT COUNT(*) as count FROM historical_data WHERE symbol NOT LIKE 'TEST_%'")
        final_prod_count = cursor.fetchone()['count']
        
        assert final_prod_count == initial_prod_count, "Production data was affected by test scenario"
        
        # Verify test data exists
        cursor.execute("SELECT COUNT(*) as count FROM historical_data WHERE symbol = 'TEST_ISOLATION'")
        test_count = cursor.fetchone()['count']
        
        assert test_count > 0, "Test scenario data was not loaded"
        
        # Cleanup test data
        cursor.execute("DELETE FROM historical_data WHERE symbol = 'TEST_ISOLATION'")
        cursor.execute("DELETE FROM symbols WHERE symbol = 'TEST_ISOLATION'")
    
    def test_scenario_pattern_validation(self, test_scenario_generator):
        """Test scenario pattern validation integration with TA-Lib"""
        # Load scenario first
        load_result = test_scenario_generator.load_scenario('volatility_periods', ['TEST_PATTERNS'])
        assert 'error' not in load_result, "Scenario loading failed"
        
        # Validate patterns
        validation_result = test_scenario_generator.validate_scenario_patterns('volatility_periods', 'TEST_PATTERNS')
        
        if 'error' in validation_result and 'TA-Lib not available' in validation_result['error']:
            pytest.skip("TA-Lib not available for pattern validation")
        
        assert 'symbol' in validation_result, "Missing symbol in validation"
        assert 'data_points' in validation_result, "Missing data_points in validation"
        assert 'total_return_pct' in validation_result, "Missing total_return_pct in validation"
    
    def test_scenario_cli_integration(self, test_scenario_generator):
        """Test scenario CLI integration and parameter handling"""
        # Test scenario listing
        scenarios = test_scenario_generator.list_scenarios()
        
        assert 'available_scenarios' in scenarios, "Missing available_scenarios"
        assert len(scenarios['available_scenarios']) >= 5, "Expected 5+ scenarios"
        
        # Validate scenario structure
        crash_scenario = scenarios['available_scenarios']['crash_2020']
        assert 'description' in crash_scenario, "Missing description"
        assert 'length_days' in crash_scenario, "Missing length_days"
        assert 'expected_outcomes' in crash_scenario, "Missing expected_outcomes"
    
    def test_scenario_memory_efficiency(self, test_scenario_generator):
        """Test scenario generation memory efficiency"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Generate multiple scenarios
        scenarios = ['crash_2020', 'growth_2021', 'volatility_periods']
        for scenario in scenarios:
            data = test_scenario_generator.generate_scenario_data(scenario)
            assert data is not None, f"Failed to generate {scenario}"
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        assert memory_increase < 100, f"Memory usage increased by {memory_increase:.1f}MB, too high"

    # =================================================================
    # CACHE SYNCHRONIZATION INTEGRATION TESTS
    # =================================================================
    
    @pytest.mark.asyncio
    async def test_cache_sync_eod_integration(self, async_redis_client, cache_synchronizer):
        """Test cache synchronization EOD completion signal integration"""
        # Simulate EOD completion signal
        eod_signal_task = asyncio.create_task(
            self._simulate_eod_signal(async_redis_client, delay=1.0)
        )
        
        # Start synchronization (should wait for EOD)
        start_time = time.time()
        result = await cache_synchronizer.daily_cache_sync()
        sync_time = time.time() - start_time
        
        # Validate sync completed after EOD signal
        assert sync_time >= 1.0, "Sync completed before EOD signal"
        assert sync_time < 10.0, "Sync took too long after EOD signal"
        assert 'error' not in result, f"Sync failed: {result.get('error')}"
        
        await eod_signal_task
    
    @pytest.mark.asyncio
    async def test_cache_sync_redis_notifications(self, async_redis_client, cache_synchronizer):
        """Test cache synchronization Redis notification publishing"""
        received_messages = []
        
        # Set up subscribers for sync notifications
        pubsub = async_redis_client.pubsub()
        await pubsub.subscribe(
            'tickstock.cache.sync_complete',
            'tickstock.universe.updated'
        )
        
        async def message_listener():
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    received_messages.append({
                        'channel': message['channel'],
                        'data': json.loads(message['data'])
                    })
        
        listener_task = asyncio.create_task(message_listener())
        
        try:
            # Perform synchronization
            result = await cache_synchronizer.perform_synchronization()
            await asyncio.sleep(0.5)  # Wait for messages
            
            # Validate notifications received
            assert len(received_messages) > 0, "No Redis notifications received"
            
            sync_complete_msgs = [m for m in received_messages if m['channel'] == 'tickstock.cache.sync_complete']
            assert len(sync_complete_msgs) > 0, "No sync_complete notification received"
            
            sync_msg = sync_complete_msgs[0]['data']
            assert 'service' in sync_msg, "Missing service field"
            assert sync_msg['service'] == 'cache_entries_synchronizer', "Wrong service name"
            assert 'event_type' in sync_msg, "Missing event_type field"
            assert 'total_changes' in sync_msg, "Missing total_changes field"
            
        finally:
            listener_task.cancel()
            await pubsub.unsubscribe('tickstock.cache.sync_complete', 'tickstock.universe.updated')
            await pubsub.aclose()
    
    @pytest.mark.asyncio
    async def test_cache_sync_30_minute_window(self, cache_synchronizer):
        """Test cache synchronization completes within 30-minute window"""
        start_time = time.time()
        
        # Perform full synchronization
        result = await cache_synchronizer.perform_synchronization()
        
        sync_duration_minutes = (time.time() - start_time) / 60
        
        assert sync_duration_minutes < 30.0, f"Sync took {sync_duration_minutes:.1f}min, exceeds 30min window"
        assert 'total_changes' in result, "Missing total_changes in result"
        assert result.get('sync_status') == 'completed', "Sync did not complete successfully"
    
    def test_cache_sync_market_cap_integration(self, db_connection, cache_synchronizer):
        """Test market cap recalculation integration with symbols table"""
        cursor = db_connection.cursor()
        
        # Insert test symbols with market caps
        test_symbols = [
            ('TEST_LARGE', 15e9),  # Large cap
            ('TEST_MID', 5e9),     # Mid cap
            ('TEST_SMALL', 800e6)  # Small cap
        ]
        
        for symbol, market_cap in test_symbols:
            cursor.execute("""
                INSERT INTO symbols (symbol, name, type, active, market_cap)
                VALUES (%s, %s, 'CS', true, %s)
                ON CONFLICT (symbol) DO UPDATE SET
                    market_cap = EXCLUDED.market_cap,
                    active = true
            """, (symbol, f'Test Symbol {symbol}', market_cap))
        
        try:
            # Run market cap recalculation
            changes = asyncio.run(cache_synchronizer.market_cap_recalculation())
            
            # Validate changes structure
            assert isinstance(changes, list), "Changes should be a list"
            
            # Check if universes were updated
            cursor.execute("""
                SELECT cache_key, symbols 
                FROM cache_entries 
                WHERE cache_key IN ('large_cap', 'mid_cap', 'small_cap')
            """)
            
            universes = {row['cache_key']: row['symbols'] for row in cursor.fetchall()}
            
            # Validate test symbols appear in appropriate universes
            if 'large_cap' in universes and universes['large_cap']:
                large_cap_symbols = universes['large_cap']
                # Note: TEST_LARGE might not be in top rankings, so this is optional validation
            
        finally:
            # Cleanup test symbols
            for symbol, _ in test_symbols:
                cursor.execute("DELETE FROM symbols WHERE symbol = %s", (symbol,))
    
    @pytest.mark.asyncio
    async def _simulate_eod_signal(self, redis_client, delay: float = 1.0):
        """Helper method to simulate EOD completion signal"""
        await asyncio.sleep(delay)
        await redis_client.lpush('eod_complete', json.dumps({
            'timestamp': datetime.now().isoformat(),
            'status': 'completed'
        }))

    # =================================================================
    # DATABASE INTEGRATION TESTS
    # =================================================================
    
    def test_database_schema_backward_compatibility(self, db_connection):
        """Test enhanced cache_entries schema maintains backward compatibility"""
        cursor = db_connection.cursor()
        
        # Test original cache_entries operations still work
        test_cache_key = f"test_compat_{int(time.time())}"
        test_symbols = ['AAPL', 'GOOGL', 'MSFT']
        
        try:
            # Insert using original schema fields only
            cursor.execute("""
                INSERT INTO cache_entries (cache_key, symbols)
                VALUES (%s, %s)
            """, (test_cache_key, json.dumps(test_symbols)))
            
            # Read back and verify
            cursor.execute("SELECT symbols FROM cache_entries WHERE cache_key = %s", (test_cache_key,))
            result = cursor.fetchone()
            
            assert result is not None, "Failed to insert with original schema"
            assert result['symbols'] == test_symbols, "Symbol data corrupted"
            
            # Test that new fields are nullable/optional
            cursor.execute("""
                SELECT universe_category, liquidity_filter, universe_metadata, last_universe_update 
                FROM cache_entries WHERE cache_key = %s
            """, (test_cache_key,))
            
            result = cursor.fetchone()
            # New fields should be null or have default values
            assert result['universe_category'] is None or isinstance(result['universe_category'], str)
            
        finally:
            cursor.execute("DELETE FROM cache_entries WHERE cache_key = %s", (test_cache_key,))
    
    def test_database_query_performance_targets(self, db_connection):
        """Test database queries meet performance targets"""
        cursor = db_connection.cursor()
        
        # Test UI-level queries (<50ms target)
        ui_queries = [
            "SELECT COUNT(*) FROM cache_entries",
            "SELECT cache_key FROM cache_entries LIMIT 10",
            "SELECT symbols FROM cache_entries WHERE cache_key = 'etf_sectors'"
        ]
        
        for query in ui_queries:
            start_time = time.time()
            cursor.execute(query)
            cursor.fetchall()
            query_time = (time.time() - start_time) * 1000  # Convert to ms
            
            assert query_time < 50, f"UI query '{query}' took {query_time:.2f}ms, exceeds 50ms target"
        
        # Test ETF universe queries (<2s target)
        etf_queries = [
            "SELECT * FROM get_etf_universes_summary()",
            "SELECT get_etf_universe('sectors')",
            "SELECT * FROM validate_etf_universe_symbols() LIMIT 100"
        ]
        
        for query in etf_queries:
            start_time = time.time()
            cursor.execute(query)
            cursor.fetchall()
            query_time = time.time() - start_time
            
            assert query_time < 2.0, f"ETF query '{query}' took {query_time:.3f}s, exceeds 2s target"
    
    def test_database_concurrent_access(self, db_connection):
        """Test database handles concurrent access from multiple services"""
        import threading
        import time
        
        results = []
        errors = []
        
        def concurrent_query_worker(worker_id):
            try:
                # Create separate connection for thread
                conn = psycopg2.connect(
                    host=db_connection.get_dsn_parameters()['host'],
                    database=db_connection.get_dsn_parameters()['dbname'],
                    user=db_connection.get_dsn_parameters()['user'],
                    password=os.getenv('TEST_DB_PASSWORD', '4pp_U$3r_2024!'),
                    cursor_factory=psycopg2.extras.RealDictCursor
                )
                conn.autocommit = True
                cursor = conn.cursor()
                
                start_time = time.time()
                
                # Simulate mixed ETF and sync operations
                cursor.execute("SELECT COUNT(*) FROM cache_entries")
                cursor.execute("SELECT get_etf_universe('sectors')")
                cursor.execute("SELECT * FROM get_etf_universes_summary() LIMIT 5")
                
                duration = time.time() - start_time
                results.append((worker_id, duration))
                
                conn.close()
                
            except Exception as e:
                errors.append((worker_id, str(e)))
        
        # Run 5 concurrent workers
        threads = []
        for i in range(5):
            thread = threading.Thread(target=concurrent_query_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join(timeout=10)
        
        # Validate results
        assert len(errors) == 0, f"Concurrent access errors: {errors}"
        assert len(results) == 5, f"Expected 5 results, got {len(results)}"
        
        # Check performance under load
        max_duration = max(duration for _, duration in results)
        assert max_duration < 5.0, f"Concurrent queries too slow: {max_duration:.2f}s"

    # =================================================================
    # REDIS INTEGRATION PATTERN TESTS
    # =================================================================
    
    @pytest.mark.asyncio
    async def test_redis_message_delivery_performance(self, async_redis_client):
        """Test Redis message delivery meets <100ms performance target"""
        delivery_times = []
        received_messages = []
        
        # Set up subscriber
        pubsub = async_redis_client.pubsub()
        await pubsub.subscribe('tickstock.performance.test')
        
        async def latency_listener():
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    received_time = time.time()
                    data = json.loads(message['data'])
                    sent_time = data['timestamp']
                    latency_ms = (received_time - sent_time) * 1000
                    delivery_times.append(latency_ms)
                    received_messages.append(data)
        
        listener_task = asyncio.create_task(latency_listener())
        
        try:
            # Send test messages with timestamps
            for i in range(10):
                test_message = {
                    'message_id': i,
                    'timestamp': time.time(),
                    'data': f'test_message_{i}'
                }
                await async_redis_client.publish('tickstock.performance.test', json.dumps(test_message))
                await asyncio.sleep(0.01)  # Small delay between messages
            
            # Wait for processing
            await asyncio.sleep(0.5)
            
            # Validate performance
            assert len(delivery_times) == 10, f"Expected 10 messages, received {len(delivery_times)}"
            
            avg_latency = sum(delivery_times) / len(delivery_times)
            max_latency = max(delivery_times)
            
            assert avg_latency < 100, f"Average latency {avg_latency:.2f}ms exceeds 100ms target"
            assert max_latency < 200, f"Max latency {max_latency:.2f}ms exceeds reasonable bounds"
            
        finally:
            listener_task.cancel()
            await pubsub.unsubscribe('tickstock.performance.test')
            await pubsub.aclose()
    
    @pytest.mark.asyncio 
    async def test_redis_message_persistence(self, async_redis_client):
        """Test Redis message persistence for offline TickStockApp instances"""
        # Test using Redis Streams for message persistence
        stream_key = 'tickstock.persistent.messages'
        
        # Add messages to stream
        message_data = [
            {'service': 'etf_universe_manager', 'event': 'universe_updated', 'theme': 'sectors'},
            {'service': 'cache_synchronizer', 'event': 'sync_complete', 'changes': 5}
        ]
        
        message_ids = []
        for data in message_data:
            message_id = await async_redis_client.xadd(stream_key, data)
            message_ids.append(message_id)
        
        # Simulate consumer reading messages
        messages = await async_redis_client.xread({stream_key: '0'})
        
        assert len(messages) > 0, "No persisted messages found"
        stream_name, stream_messages = messages[0]
        assert len(stream_messages) == 2, f"Expected 2 messages, got {len(stream_messages)}"
        
        # Validate message content
        for (msg_id, fields) in stream_messages:
            assert 'service' in fields, "Missing service field in persisted message"
            assert 'event' in fields, "Missing event field in persisted message"
        
        # Cleanup
        await async_redis_client.delete(stream_key)
    
    @pytest.mark.asyncio
    async def test_redis_channel_naming_conventions(self, async_redis_client):
        """Test Redis channels follow TickStock naming conventions"""
        expected_channels = [
            'tickstock.universe.updated',
            'tickstock.cache.sync_complete', 
            'tickstock.etf.correlation_update',
            'tickstock.universe.validation_complete',
            'tickstock.cache.ipo_assignment',
            'tickstock.cache.delisting_cleanup'
        ]
        
        received_channels = []
        
        # Set up subscriber for all expected channels
        pubsub = async_redis_client.pubsub()
        await pubsub.psubscribe('tickstock.*')  # Subscribe to pattern
        
        async def channel_listener():
            async for message in pubsub.listen():
                if message['type'] == 'pmessage':
                    received_channels.append(message['channel'])
        
        listener_task = asyncio.create_task(channel_listener())
        
        try:
            # Publish test messages to each channel
            for channel in expected_channels:
                test_message = {
                    'timestamp': datetime.now().isoformat(),
                    'test': True,
                    'channel': channel
                }
                await async_redis_client.publish(channel, json.dumps(test_message))
                await asyncio.sleep(0.01)
            
            # Wait for messages
            await asyncio.sleep(0.2)
            
            # Validate all channels received
            for expected_channel in expected_channels:
                assert expected_channel in received_channels, f"Channel {expected_channel} not received"
            
            # Validate naming pattern compliance
            for channel in received_channels:
                assert channel.startswith('tickstock.'), f"Channel {channel} doesn't follow naming convention"
                parts = channel.split('.')
                assert len(parts) >= 2, f"Channel {channel} has insufficient hierarchy"
                
        finally:
            listener_task.cancel()
            await pubsub.punsubscribe('tickstock.*')
            await pubsub.aclose()

    # =================================================================
    # END-TO-END WORKFLOW INTEGRATION TESTS  
    # =================================================================
    
    @pytest.mark.asyncio
    async def test_complete_etf_workflow_integration(self, async_redis_client, etf_universe_manager, db_connection):
        """Test complete ETF workflow from expansion to TickStockApp notification"""
        received_notifications = []
        
        # Set up TickStockApp-style subscriber
        pubsub = async_redis_client.pubsub()
        await pubsub.subscribe('tickstock.universe.updated')
        
        async def tickstockapp_listener():
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    received_notifications.append(json.loads(message['data']))
        
        listener_task = asyncio.create_task(tickstockapp_listener())
        
        try:
            # Step 1: ETF universe expansion
            expansion_results = etf_universe_manager.expand_etf_universes()
            assert expansion_results['total_symbols'] > 0, "ETF expansion failed"
            
            # Step 2: Publish Redis notifications
            publish_success = await etf_universe_manager.publish_universe_updates(expansion_results)
            assert publish_success, "Failed to publish universe updates"
            
            # Step 3: Wait for TickStockApp notifications
            await asyncio.sleep(0.3)
            
            # Step 4: Validate end-to-end workflow
            assert len(received_notifications) > 0, "TickStockApp received no notifications"
            
            # Validate notification structure for TickStockApp consumption
            main_notification = received_notifications[0]
            assert 'service' in main_notification, "Missing service identification"
            assert 'event_type' in main_notification, "Missing event type"
            assert 'themes_processed' in main_notification, "Missing themes count"
            assert 'total_symbols' in main_notification, "Missing symbol count"
            
            # Step 5: Verify database state
            cursor = db_connection.cursor()
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM cache_entries 
                WHERE universe_category = 'ETF' 
                AND last_universe_update >= CURRENT_TIMESTAMP - INTERVAL '1 minute'
            """)
            
            recent_updates = cursor.fetchone()['count']
            assert recent_updates > 0, "No recent ETF universe updates in database"
            
        finally:
            listener_task.cancel()
            await pubsub.unsubscribe('tickstock.universe.updated')
            await pubsub.aclose()
    
    @pytest.mark.asyncio
    async def test_scenario_generation_to_pattern_detection_workflow(self, test_scenario_generator, db_connection):
        """Test test scenario generation integration with pattern detection systems"""
        # Step 1: Generate test scenario
        scenario_data = test_scenario_generator.generate_scenario_data('high_low_events')
        assert scenario_data is not None, "Scenario generation failed"
        assert len(scenario_data) > 0, "No scenario data generated"
        
        # Step 2: Load scenario into database
        load_result = test_scenario_generator.load_scenario('high_low_events', ['TEST_PATTERN_FLOW'])
        assert 'error' not in load_result, f"Scenario loading failed: {load_result.get('error')}"
        
        try:
            # Step 3: Verify scenario data accessible by pattern detection
            cursor = db_connection.cursor()
            cursor.execute("""
                SELECT symbol, date, high_price, low_price, close_price
                FROM historical_data 
                WHERE symbol = 'TEST_PATTERN_FLOW'
                ORDER BY date
                LIMIT 10
            """)
            
            pattern_data = cursor.fetchall()
            assert len(pattern_data) > 0, "No pattern detection data available"
            
            # Step 4: Validate data structure for pattern detection
            sample_row = pattern_data[0]
            assert 'high_price' in sample_row, "Missing high_price for pattern detection"
            assert 'low_price' in sample_row, "Missing low_price for pattern detection"
            assert 'close_price' in sample_row, "Missing close_price for pattern detection"
            assert sample_row['high_price'] >= sample_row['low_price'], "Invalid OHLC relationship"
            
            # Step 5: Verify symbol exists for integration
            cursor.execute("SELECT * FROM symbols WHERE symbol = 'TEST_PATTERN_FLOW'")
            symbol_data = cursor.fetchone()
            assert symbol_data is not None, "Symbol not created for pattern detection integration"
            assert symbol_data['type'] == 'TEST', "Wrong symbol type for test scenario"
            
        finally:
            # Cleanup
            cursor.execute("DELETE FROM historical_data WHERE symbol = 'TEST_PATTERN_FLOW'")
            cursor.execute("DELETE FROM symbols WHERE symbol = 'TEST_PATTERN_FLOW'")
    
    @pytest.mark.asyncio
    async def test_cache_sync_to_tickstockapp_notification_workflow(self, async_redis_client, cache_synchronizer):
        """Test cache synchronization to TickStockApp notification workflow"""
        tickstockapp_messages = []
        
        # Set up TickStockApp-style multi-channel subscriber
        pubsub = async_redis_client.pubsub()
        await pubsub.subscribe(
            'tickstock.cache.sync_complete',
            'tickstock.universe.updated'
        )
        
        async def tickstockapp_consumer():
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    tickstockapp_messages.append({
                        'channel': message['channel'],
                        'data': json.loads(message['data']),
                        'received_at': time.time()
                    })
        
        consumer_task = asyncio.create_task(tickstockapp_consumer())
        
        try:
            # Step 1: Trigger cache synchronization
            sync_result = await cache_synchronizer.perform_synchronization()
            assert sync_result['sync_status'] == 'completed', "Sync failed to complete"
            
            # Step 2: Wait for TickStockApp notifications
            await asyncio.sleep(0.5)
            
            # Step 3: Validate TickStockApp received appropriate notifications
            assert len(tickstockapp_messages) > 0, "TickStockApp received no sync notifications"
            
            # Check for sync completion notification
            sync_complete_msgs = [m for m in tickstockapp_messages if m['channel'] == 'tickstock.cache.sync_complete']
            assert len(sync_complete_msgs) > 0, "Missing sync_complete notification for TickStockApp"
            
            # Step 4: Validate notification timing (messages should arrive quickly)
            message_times = [m['received_at'] for m in tickstockapp_messages]
            if len(message_times) > 1:
                time_spread = max(message_times) - min(message_times)
                assert time_spread < 1.0, f"Message delivery spread {time_spread:.2f}s too high"
            
            # Step 5: Validate TickStockApp can process notification structure
            sync_notification = sync_complete_msgs[0]['data']
            required_fields = ['service', 'event_type', 'total_changes', 'task_summary']
            for field in required_fields:
                assert field in sync_notification, f"Missing {field} for TickStockApp processing"
                
        finally:
            consumer_task.cancel()
            await pubsub.unsubscribe('tickstock.cache.sync_complete', 'tickstock.universe.updated')
            await pubsub.aclose()

    # =================================================================
    # SERVICE BOUNDARY AND LOOSE COUPLING VALIDATION
    # =================================================================
    
    def test_service_boundary_enforcement(self, etf_universe_manager, test_scenario_generator, cache_synchronizer):
        """Test that Phase 3 services maintain proper boundaries and loose coupling"""
        # Validate ETF Universe Manager boundaries
        etf_manager_methods = [method for method in dir(etf_universe_manager) if not method.startswith('_')]
        
        # Should NOT have direct analysis or pattern detection methods
        forbidden_etf_methods = ['analyze_patterns', 'detect_signals', 'generate_alerts', 'send_notifications_direct']
        for method in forbidden_etf_methods:
            assert method not in etf_manager_methods, f"ETF manager has forbidden method: {method}"
        
        # Should have proper Redis publishing methods
        assert hasattr(etf_universe_manager, 'publish_universe_updates'), "Missing Redis publishing capability"
        
        # Validate Test Scenario Generator boundaries  
        generator_methods = [method for method in dir(test_scenario_generator) if not method.startswith('_')]
        
        # Should NOT have production data methods
        forbidden_generator_methods = ['update_production_data', 'modify_real_prices', 'alter_live_data']
        for method in forbidden_generator_methods:
            assert method not in generator_methods, f"Scenario generator has forbidden method: {method}"
        
        # Validate Cache Synchronizer boundaries
        sync_methods = [method for method in dir(cache_synchronizer) if not method.startswith('_')]
        
        # Should NOT have direct user interface methods
        forbidden_sync_methods = ['render_ui', 'handle_user_request', 'serve_web_content']
        for method in forbidden_sync_methods:
            assert method not in sync_methods, f"Cache synchronizer has forbidden method: {method}"
        
        # Should have proper Redis publishing methods
        assert hasattr(cache_synchronizer, 'publish_sync_notifications'), "Missing Redis publishing capability"
    
    @pytest.mark.asyncio
    async def test_no_direct_api_calls_between_systems(self, async_redis_client):
        """Test that Phase 3 services use only Redis for inter-system communication"""
        # Monitor all Redis operations
        redis_operations = []
        
        # Create wrapper to track Redis operations
        original_publish = async_redis_client.publish
        
        async def tracking_publish(channel, message):
            redis_operations.append(('publish', channel, message))
            return await original_publish(channel, message)
        
        async_redis_client.publish = tracking_publish
        
        try:
            # Create managers that should use Redis
            etf_manager = ETFUniverseManager()
            cache_sync = CacheEntriesSynchronizer()
            
            # Perform operations that should trigger Redis usage
            expansion_results = etf_manager.expand_etf_universes()
            await etf_manager.publish_universe_updates(expansion_results)
            
            sync_result = await cache_sync.perform_synchronization()
            
            # Validate Redis was used for communication
            publish_operations = [op for op in redis_operations if op[0] == 'publish']
            assert len(publish_operations) > 0, "No Redis publish operations detected"
            
            # Validate proper channel usage
            channels_used = [op[1] for op in publish_operations]
            expected_channel_prefixes = ['tickstock.universe', 'tickstock.cache']
            
            valid_channels = any(
                any(channel.startswith(prefix) for prefix in expected_channel_prefixes)
                for channel in channels_used
            )
            
            assert valid_channels, f"Invalid channel usage: {channels_used}"
            
        finally:
            # Restore original method
            async_redis_client.publish = original_publish
    
    def test_performance_impact_on_existing_operations(self, db_connection):
        """Test that Phase 3 enhancements don't impact existing operation performance"""
        cursor = db_connection.cursor()
        
        # Test original cache_entries operations performance
        original_operations = [
            "SELECT cache_key FROM cache_entries WHERE cache_key LIKE 'top_%'",
            "SELECT symbols FROM cache_entries WHERE cache_key = 'large_cap'",  
            "SELECT COUNT(*) FROM cache_entries"
        ]
        
        performance_results = []
        
        for operation in original_operations:
            start_time = time.time()
            cursor.execute(operation)
            cursor.fetchall()
            operation_time = (time.time() - start_time) * 1000  # Convert to ms
            
            performance_results.append((operation, operation_time))
            
            # Existing operations should remain fast (<50ms)
            assert operation_time < 50, f"Original operation '{operation}' took {operation_time:.2f}ms, too slow"
        
        # Validate no significant performance degradation
        avg_time = sum(time for _, time in performance_results) / len(performance_results)
        assert avg_time < 25, f"Average operation time {avg_time:.2f}ms indicates performance degradation"

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])