"""
Sprint 14 Phase 2: Equity Types Integration Test Suite

Tests for enhanced equity_types table with JSONB processing rules,
performance-optimized functions, and processing queue management.

Date: 2025-09-01
Sprint: 14 Phase 2
Status: Comprehensive Test Coverage
"""

import time

import pytest
from src.database.connection import DatabaseConnection


class TestEquityTypesSchemaEnhancement:
    """Test enhanced equity_types table schema and JSONB fields"""

    @pytest.fixture
    def db_connection(self):
        """Database connection fixture for testing"""
        return DatabaseConnection(test_mode=True)

    def test_equity_types_table_structure(self, db_connection):
        """Test enhanced equity_types table has all required columns"""
        cursor = db_connection.cursor()

        # Query table structure
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'equity_types'
            ORDER BY ordinal_position
        """)

        columns = {row[0]: row[1] for row in cursor.fetchall()}

        # Verify enhanced columns exist
        assert 'update_frequency' in columns
        assert 'processing_rules' in columns
        assert 'requires_eod_validation' in columns
        assert 'additional_data_fields' in columns
        assert 'priority_level' in columns
        assert 'batch_size' in columns
        assert 'rate_limit_ms' in columns

        # Verify JSONB columns
        assert columns['processing_rules'] == 'jsonb'
        assert columns['additional_data_fields'] == 'jsonb'

    def test_equity_types_indexes_created(self, db_connection):
        """Test performance indexes are properly created"""
        cursor = db_connection.cursor()

        # Query index information
        cursor.execute("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'equity_types'
        """)

        indexes = {row[0]: row[1] for row in cursor.fetchall()}

        # Verify performance indexes
        assert 'idx_equity_types_frequency' in indexes
        assert 'idx_equity_types_priority' in indexes
        assert 'idx_equity_types_active' in indexes

        # Verify index structure
        frequency_index = indexes['idx_equity_types_frequency']
        assert 'update_frequency' in frequency_index

        priority_index = indexes['idx_equity_types_priority']
        assert 'priority_level DESC' in priority_index

    def test_initial_equity_types_data_loaded(self, db_connection):
        """Test initial equity types configuration is properly loaded"""
        cursor = db_connection.cursor()

        # Query loaded equity types
        cursor.execute("SELECT type_name, priority_level FROM equity_types ORDER BY priority_level DESC")
        equity_types = cursor.fetchall()

        # Verify all expected types are loaded
        type_names = [row[0] for row in equity_types]
        expected_types = ['STOCK_REALTIME', 'ETF', 'ETN', 'STOCK_EOD', 'PENNY_STOCK', 'DEV_TESTING']

        for expected_type in expected_types:
            assert expected_type in type_names

        # Verify priority ordering
        assert equity_types[0][0] == 'STOCK_REALTIME'  # Highest priority
        assert equity_types[0][1] == 100

    def test_processing_rules_jsonb_structure(self, db_connection):
        """Test JSONB processing rules structure and validation"""
        cursor = db_connection.cursor()

        # Query ETF processing rules
        cursor.execute("""
            SELECT processing_rules
            FROM equity_types
            WHERE type_name = 'ETF'
        """)

        rules = cursor.fetchone()[0]

        # Verify JSONB structure
        assert isinstance(rules, dict)
        assert 'aum_required' in rules
        assert 'expense_ratio_required' in rules
        assert 'correlation_tracking' in rules
        assert rules['aum_required'] is True
        assert rules['fmv_support'] is True

    def test_additional_data_fields_jsonb(self, db_connection):
        """Test additional_data_fields JSONB configuration"""
        cursor = db_connection.cursor()

        # Query STOCK_REALTIME additional fields
        cursor.execute("""
            SELECT additional_data_fields
            FROM equity_types
            WHERE type_name = 'STOCK_REALTIME'
        """)

        fields = cursor.fetchone()[0]

        # Verify additional fields structure
        assert isinstance(fields, dict)
        assert 'intraday_priority' in fields
        assert 'pattern_alerts' in fields
        assert fields['intraday_priority'] == 'high'
        assert fields['pattern_alerts'] is True


class TestEquityTypesPerformanceFunctions:
    """Test performance-optimized database functions"""

    @pytest.fixture
    def db_connection(self):
        """Database connection fixture"""
        return DatabaseConnection(test_mode=True)

    def test_get_equity_processing_config_function(self, db_connection):
        """Test get_equity_processing_config function performance and accuracy"""
        cursor = db_connection.cursor()

        # Test function with ETF type
        cursor.execute("SELECT get_equity_processing_config('ETF')")
        config = cursor.fetchone()[0]

        # Verify returned configuration structure
        assert isinstance(config, dict)
        assert 'type_name' in config
        assert 'processing_rules' in config
        assert 'priority_level' in config
        assert 'batch_size' in config
        assert 'rate_limit_ms' in config

        # Verify ETF-specific configuration
        assert config['type_name'] == 'ETF'
        assert config['priority_level'] == 90
        assert config['batch_size'] == 50

    @pytest.mark.performance
    def test_get_equity_processing_config_performance(self, db_connection):
        """Test function performance meets <50ms requirement"""
        cursor = db_connection.cursor()

        # Test performance across multiple equity types
        equity_types = ['ETF', 'STOCK_REALTIME', 'STOCK_EOD', 'PENNY_STOCK']

        start_time = time.perf_counter()

        for equity_type in equity_types * 25:  # 100 function calls
            cursor.execute("SELECT get_equity_processing_config(%s)", (equity_type,))
            result = cursor.fetchone()
            assert result is not None

        elapsed_time = time.perf_counter() - start_time

        # Should complete 100 function calls in <5 seconds (50ms each)
        assert elapsed_time < 5.0
        average_time = elapsed_time / 100
        assert average_time < 0.05  # Less than 50ms per call

    def test_get_symbols_for_processing_function(self, db_connection):
        """Test get_symbols_for_processing function with proper ordering"""
        cursor = db_connection.cursor()

        # Test function with ETF type
        cursor.execute("SELECT * FROM get_symbols_for_processing('ETF', 10)")
        symbols = cursor.fetchall()

        # Verify result structure
        assert len(symbols) <= 10
        for symbol_row in symbols:
            assert len(symbol_row) == 5  # symbol, name, exchange, market_cap, processing_priority
            assert isinstance(symbol_row[0], str)  # symbol
            assert isinstance(symbol_row[4], int)  # processing_priority

        # Verify ordering (priority desc, market cap desc)
        if len(symbols) > 1:
            priorities = [row[4] for row in symbols]
            assert priorities == sorted(priorities, reverse=True)

    def test_update_processing_stats_function(self, db_connection):
        """Test update_processing_stats function updates statistics correctly"""
        cursor = db_connection.cursor()

        # Update statistics for ETF processing
        cursor.execute("""
            SELECT update_processing_stats('ETF', 45, 5, 120)
        """)

        success = cursor.fetchone()[0]
        assert success is True

        # Verify statistics were updated
        cursor.execute("""
            SELECT additional_data_fields
            FROM equity_types
            WHERE type_name = 'ETF'
        """)

        stats = cursor.fetchone()[0]

        # Verify statistics structure
        assert 'last_processing_date' in stats
        assert 'symbols_processed' in stats
        assert 'symbols_failed' in stats
        assert 'processing_duration_seconds' in stats
        assert 'success_rate' in stats

        # Verify calculated values
        assert stats['symbols_processed'] == 45
        assert stats['symbols_failed'] == 5
        assert stats['processing_duration_seconds'] == 120
        assert stats['success_rate'] == 0.9  # 45/50 = 0.9

    @pytest.mark.performance
    def test_function_execution_performance_benchmark(self, db_connection):
        """Test all functions meet performance requirements under load"""
        cursor = db_connection.cursor()

        # Test multiple function executions
        start_time = time.perf_counter()

        for i in range(100):
            # Mix of function calls
            cursor.execute("SELECT get_equity_processing_config('STOCK_REALTIME')")
            cursor.execute("SELECT * FROM get_symbols_for_processing('ETF', 5)")
            cursor.execute("SELECT update_processing_stats('PENNY_STOCK', 10, 1, 30)")

        elapsed_time = time.perf_counter() - start_time

        # 300 function calls should complete in <15 seconds (50ms each)
        assert elapsed_time < 15.0
        average_time = elapsed_time / 300
        assert average_time < 0.05  # Less than 50ms per function call


class TestProcessingQueueManagement:
    """Test processing queue management system"""

    @pytest.fixture
    def db_connection(self):
        """Database connection fixture"""
        return DatabaseConnection(test_mode=True)

    def test_processing_queue_table_structure(self, db_connection):
        """Test equity_processing_queue table structure"""
        cursor = db_connection.cursor()

        # Query table structure
        cursor.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'equity_processing_queue'
            ORDER BY ordinal_position
        """)

        columns = {row[0]: row[1] for row in cursor.fetchall()}

        # Verify queue table columns
        required_columns = [
            'id', 'equity_type', 'symbol', 'processing_priority',
            'scheduled_time', 'status', 'attempts', 'last_attempt',
            'error_message', 'created_at', 'completed_at'
        ]

        for col in required_columns:
            assert col in columns

    def test_queue_symbols_for_processing_function(self, db_connection):
        """Test queue_symbols_for_processing function"""
        cursor = db_connection.cursor()

        # Clear queue for clean test
        cursor.execute("DELETE FROM equity_processing_queue WHERE equity_type = 'ETF'")

        # Test queuing specific symbols
        test_symbols = ['SPY', 'QQQ', 'VTI']
        cursor.execute("""
            SELECT queue_symbols_for_processing('ETF', %s)
        """, (test_symbols,))

        queued_count = cursor.fetchone()[0]
        assert queued_count == len(test_symbols)

        # Verify symbols were queued
        cursor.execute("""
            SELECT symbol, equity_type, status, processing_priority
            FROM equity_processing_queue
            WHERE equity_type = 'ETF'
            ORDER BY symbol
        """)

        queued_symbols = cursor.fetchall()
        assert len(queued_symbols) == len(test_symbols)

        for i, symbol_row in enumerate(queued_symbols):
            assert symbol_row[0] in test_symbols
            assert symbol_row[1] == 'ETF'
            assert symbol_row[2] == 'pending'
            assert symbol_row[3] == 90  # ETF priority level

    def test_queue_all_symbols_for_equity_type(self, db_connection):
        """Test queuing all symbols for an equity type"""
        cursor = db_connection.cursor()

        # Clear queue
        cursor.execute("DELETE FROM equity_processing_queue WHERE equity_type = 'STOCK_REALTIME'")

        # Queue all STOCK_REALTIME symbols
        cursor.execute("""
            SELECT queue_symbols_for_processing('STOCK_REALTIME', NULL)
        """)

        queued_count = cursor.fetchone()[0]

        # Verify some symbols were queued
        assert queued_count > 0

        # Check queue contents
        cursor.execute("""
            SELECT COUNT(*), AVG(processing_priority)
            FROM equity_processing_queue
            WHERE equity_type = 'STOCK_REALTIME' AND status = 'pending'
        """)

        count, avg_priority = cursor.fetchone()
        assert count == queued_count
        assert avg_priority == 100  # STOCK_REALTIME priority

    def test_queue_indexes_performance(self, db_connection):
        """Test queue indexes provide optimal query performance"""
        cursor = db_connection.cursor()

        # Insert test data
        cursor.execute("""
            INSERT INTO equity_processing_queue (equity_type, symbol, processing_priority, status)
            SELECT 
                'STOCK_EOD',
                'TEST' || generate_series(1, 1000),
                50,
                CASE WHEN random() > 0.8 THEN 'completed' ELSE 'pending' END
        """)

        # Test priority-based query performance
        start_time = time.perf_counter()

        cursor.execute("""
            SELECT symbol, processing_priority
            FROM equity_processing_queue
            WHERE status = 'pending'
            ORDER BY processing_priority DESC, scheduled_time
            LIMIT 100
        """)

        results = cursor.fetchall()
        elapsed_time = time.perf_counter() - start_time

        # Query should complete in <50ms even with 1000+ records
        assert elapsed_time < 0.05
        assert len(results) <= 100

        # Verify ordering
        if len(results) > 1:
            priorities = [row[1] for row in results]
            assert priorities == sorted(priorities, reverse=True)

    def test_queue_conflict_handling(self, db_connection):
        """Test queue handles duplicate symbol conflicts"""
        cursor = db_connection.cursor()

        # Clear and insert test symbol
        cursor.execute("DELETE FROM equity_processing_queue WHERE symbol = 'TESTDUP'")
        cursor.execute("""
            INSERT INTO equity_processing_queue (equity_type, symbol, processing_priority)
            VALUES ('ETF', 'TESTDUP', 90)
        """)

        # Try to queue same symbol again
        cursor.execute("""
            SELECT queue_symbols_for_processing('ETF', ARRAY['TESTDUP'])
        """)

        queued_count = cursor.fetchone()[0]

        # Should not create duplicates (ON CONFLICT DO NOTHING)
        cursor.execute("""
            SELECT COUNT(*) FROM equity_processing_queue WHERE symbol = 'TESTDUP'
        """)

        total_count = cursor.fetchone()[0]
        assert total_count == 1  # Only original record remains


class TestEquityTypesConfigurationManagement:
    """Test equity types configuration and rule management"""

    @pytest.fixture
    def db_connection(self):
        """Database connection fixture"""
        return DatabaseConnection(test_mode=True)

    def test_etf_configuration_complete(self, db_connection):
        """Test ETF processing configuration is complete and valid"""
        cursor = db_connection.cursor()

        cursor.execute("""
            SELECT type_name, processing_rules, additional_data_fields, 
                   priority_level, batch_size, rate_limit_ms
            FROM equity_types
            WHERE type_name = 'ETF'
        """)

        config = cursor.fetchone()

        # Verify ETF configuration
        assert config[0] == 'ETF'

        processing_rules = config[1]
        assert processing_rules['aum_required'] is True
        assert processing_rules['expense_ratio_required'] is True
        assert processing_rules['correlation_tracking'] is True
        assert processing_rules['fmv_support'] is True

        additional_fields = config[2]
        assert additional_fields['correlation_tracking'] is True
        assert additional_fields['premium_discount_monitoring'] is True

        # Verify performance settings
        assert config[3] == 90  # priority_level
        assert config[4] == 50  # batch_size
        assert config[5] == 12000  # rate_limit_ms

    def test_realtime_stock_configuration(self, db_connection):
        """Test STOCK_REALTIME configuration for high-priority processing"""
        cursor = db_connection.cursor()

        cursor.execute("""
            SELECT processing_rules, additional_data_fields, 
                   priority_level, batch_size, rate_limit_ms
            FROM equity_types
            WHERE type_name = 'STOCK_REALTIME'
        """)

        config = cursor.fetchone()

        processing_rules = config[0]
        assert processing_rules['eod_validation'] is True
        assert processing_rules['intraday_processing'] is True
        assert processing_rules['pattern_detection'] is True

        additional_fields = config[1]
        assert additional_fields['intraday_priority'] == 'high'
        assert additional_fields['pattern_alerts'] is True

        # Verify highest priority settings
        assert config[2] == 100  # Highest priority
        assert config[3] == 25   # Smaller batches for faster processing
        assert config[4] == 6000  # Faster rate limit

    def test_penny_stock_risk_configuration(self, db_connection):
        """Test PENNY_STOCK risk monitoring configuration"""
        cursor = db_connection.cursor()

        cursor.execute("""
            SELECT processing_rules, additional_data_fields
            FROM equity_types
            WHERE type_name = 'PENNY_STOCK'
        """)

        config = cursor.fetchone()

        processing_rules = config[0]
        assert processing_rules['volatility_monitoring'] is True
        assert processing_rules['volume_validation'] is True
        assert processing_rules['fraud_detection'] is True
        assert processing_rules['spread_monitoring'] is True

        additional_fields = config[1]
        assert additional_fields['volatility_threshold'] == 0.30
        assert additional_fields['minimum_volume'] == 10000
        assert additional_fields['spread_alert_threshold'] == 0.10

    def test_development_testing_configuration(self, db_connection):
        """Test DEV_TESTING minimal processing configuration"""
        cursor = db_connection.cursor()

        cursor.execute("""
            SELECT processing_rules, additional_data_fields, 
                   priority_level, requires_eod_validation
            FROM equity_types
            WHERE type_name = 'DEV_TESTING'
        """)

        config = cursor.fetchone()

        processing_rules = config[0]
        assert processing_rules['minimal_validation'] is True
        assert processing_rules['test_data_acceptable'] is True
        assert processing_rules['fast_processing'] is True

        additional_fields = config[1]
        assert additional_fields['development_mode'] is True
        assert additional_fields['mock_data_allowed'] is True

        # Verify minimal processing settings
        assert config[2] == 10     # Lowest priority
        assert config[3] is False  # No EOD validation required

    def test_configuration_update_mechanism(self, db_connection):
        """Test configuration can be updated with ON CONFLICT handling"""
        cursor = db_connection.cursor()

        # Update existing ETF configuration
        cursor.execute("""
            INSERT INTO equity_types (
                type_name, description, priority_level, batch_size
            ) VALUES (
                'ETF', 'Updated ETF Description', 95, 75
            )
            ON CONFLICT (type_name) DO UPDATE SET
                description = EXCLUDED.description,
                priority_level = EXCLUDED.priority_level,
                batch_size = EXCLUDED.batch_size,
                updated_at = CURRENT_TIMESTAMP
        """)

        # Verify update was applied
        cursor.execute("""
            SELECT description, priority_level, batch_size, updated_at
            FROM equity_types
            WHERE type_name = 'ETF'
        """)

        updated_config = cursor.fetchone()
        assert updated_config[0] == 'Updated ETF Description'
        assert updated_config[1] == 95
        assert updated_config[2] == 75
        assert updated_config[3] is not None  # updated_at timestamp


class TestEquityTypesPerformanceBenchmarks:
    """Performance benchmark tests for equity types system"""

    @pytest.fixture
    def db_connection(self):
        """Database connection fixture"""
        return DatabaseConnection(test_mode=True)

    @pytest.mark.performance
    def test_4000_symbol_processing_capacity(self, db_connection):
        """Test system can handle 4,000+ symbol processing efficiently"""
        cursor = db_connection.cursor()

        # Clear test queue
        cursor.execute("DELETE FROM equity_processing_queue WHERE equity_type = 'PERFORMANCE_TEST'")

        # Create performance test equity type
        cursor.execute("""
            INSERT INTO equity_types (
                type_name, description, priority_level, batch_size, rate_limit_ms
            ) VALUES (
                'PERFORMANCE_TEST', 'Performance testing type', 75, 100, 10000
            ) ON CONFLICT (type_name) DO UPDATE SET
                priority_level = EXCLUDED.priority_level,
                batch_size = EXCLUDED.batch_size
        """)

        # Insert 4000 test symbols in processing queue
        start_time = time.perf_counter()

        cursor.execute("""
            INSERT INTO equity_processing_queue (equity_type, symbol, processing_priority)
            SELECT 
                'PERFORMANCE_TEST',
                'PERF' || LPAD(generate_series(1, 4000)::text, 4, '0'),
                75
        """)

        insert_time = time.perf_counter() - start_time

        # Test batch processing query performance
        start_time = time.perf_counter()

        cursor.execute("""
            SELECT symbol, processing_priority
            FROM equity_processing_queue
            WHERE equity_type = 'PERFORMANCE_TEST' 
            AND status = 'pending'
            ORDER BY processing_priority DESC, scheduled_time
            LIMIT 1000
        """)

        batch = cursor.fetchall()
        query_time = time.perf_counter() - start_time

        # Performance assertions
        assert len(batch) == 1000
        assert insert_time < 10.0    # 4000 inserts in <10 seconds
        assert query_time < 0.1      # 1000 record query in <100ms

        # Test batch update performance
        test_symbols = [row[0] for row in batch[:100]]

        start_time = time.perf_counter()

        cursor.execute("""
            UPDATE equity_processing_queue
            SET status = 'processing', last_attempt = CURRENT_TIMESTAMP
            WHERE symbol = ANY(%s) AND equity_type = 'PERFORMANCE_TEST'
        """, (test_symbols,))

        update_time = time.perf_counter() - start_time

        assert update_time < 0.5  # 100 updates in <500ms

    @pytest.mark.performance
    def test_concurrent_processing_performance(self, db_connection):
        """Test performance under concurrent processing scenarios"""
        cursor = db_connection.cursor()

        # Simulate concurrent function calls
        start_time = time.perf_counter()

        for equity_type in ['ETF', 'STOCK_REALTIME', 'STOCK_EOD', 'PENNY_STOCK']:
            for i in range(25):  # 25 iterations per type = 100 total
                # Mix of configuration retrieval and queue operations
                cursor.execute("SELECT get_equity_processing_config(%s)", (equity_type,))
                cursor.execute("SELECT * FROM get_symbols_for_processing(%s, 5)", (equity_type,))

        elapsed_time = time.perf_counter() - start_time

        # 200 function calls should complete in <10 seconds
        assert elapsed_time < 10.0
        average_time = elapsed_time / 200
        assert average_time < 0.05  # Less than 50ms per function call

    @pytest.mark.performance
    def test_statistics_update_performance(self, db_connection):
        """Test statistics update performance with large processing history"""
        cursor = db_connection.cursor()

        # Build up processing history for performance test
        for i in range(10):
            cursor.execute("""
                SELECT update_processing_stats('ETF', %s, %s, %s)
            """, (100 + i, 5 - (i % 3), 120 + i * 10))

        # Test performance of statistics update with existing history
        start_time = time.perf_counter()

        for i in range(50):  # 50 statistics updates
            cursor.execute("""
                SELECT update_processing_stats('ETF', %s, %s, %s)
            """, (95 + i, 5, 115))

        elapsed_time = time.perf_counter() - start_time

        # 50 statistics updates should complete in <5 seconds
        assert elapsed_time < 5.0
        average_time = elapsed_time / 50
        assert average_time < 0.1  # Less than 100ms per statistics update

        # Verify processing history is maintained efficiently
        cursor.execute("""
            SELECT array_length((additional_data_fields->'processing_history')::json::text[]::json[], 1)
            FROM equity_types
            WHERE type_name = 'ETF'
        """)

        history_length = cursor.fetchone()[0]
        assert history_length == 60  # 10 initial + 50 test updates

    @pytest.mark.performance
    def test_queue_processing_throughput(self, db_connection):
        """Test processing queue throughput for high-volume operations"""
        cursor = db_connection.cursor()

        # Create large processing queue
        cursor.execute("DELETE FROM equity_processing_queue WHERE equity_type = 'THROUGHPUT_TEST'")

        # Insert equity type for throughput testing
        cursor.execute("""
            INSERT INTO equity_types (type_name, priority_level, batch_size)
            VALUES ('THROUGHPUT_TEST', 80, 200)
            ON CONFLICT (type_name) DO UPDATE SET
                priority_level = EXCLUDED.priority_level,
                batch_size = EXCLUDED.batch_size
        """)

        # Queue 2000 symbols
        cursor.execute("""
            SELECT queue_symbols_for_processing('THROUGHPUT_TEST', 
                ARRAY(SELECT 'THRU' || generate_series(1, 2000))
            )
        """)

        # Test batch processing throughput
        processed_count = 0
        start_time = time.perf_counter()

        while processed_count < 2000:
            # Get batch for processing
            cursor.execute("""
                SELECT symbol
                FROM equity_processing_queue
                WHERE equity_type = 'THROUGHPUT_TEST' AND status = 'pending'
                ORDER BY processing_priority DESC, scheduled_time
                LIMIT 200
            """)

            batch = cursor.fetchall()
            if not batch:
                break

            batch_symbols = [row[0] for row in batch]

            # Mark batch as processed
            cursor.execute("""
                UPDATE equity_processing_queue
                SET status = 'completed', completed_at = CURRENT_TIMESTAMP
                WHERE symbol = ANY(%s) AND equity_type = 'THROUGHPUT_TEST'
            """, (batch_symbols,))

            processed_count += len(batch_symbols)

        elapsed_time = time.perf_counter() - start_time

        # Should process 2000 symbols in <30 seconds (batch processing)
        assert elapsed_time < 30.0
        throughput = processed_count / elapsed_time
        assert throughput > 100  # More than 100 symbols per second
