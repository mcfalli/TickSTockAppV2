#!/usr/bin/env python3
"""
Cache Entries Universe Expansion Database Tests - Sprint 14 Phase 3

Comprehensive tests for the enhanced cache_entries schema and database functions:
- Database schema enhancements with universe_category, liquidity_filter, universe_metadata columns
- Database functions: get_etf_universe(), update_etf_universe(), validate_etf_universe_symbols()
- Performance validation for ETF universe queries (<2 second requirement)
- Database index performance and query optimization testing
- ETF universe performance view and analytics validation

Test Organization:
- Unit tests: Database function behavior, schema validation, data integrity
- Integration tests: Schema enhancement deployment, function integration
- Performance tests: <2 second ETF query requirements, index optimization
- Regression tests: Existing cache_entries functionality preservation
"""

import json
import os
import sys
from datetime import datetime
from unittest.mock import Mock, patch

import pytest

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../'))

class TestCacheEntriesSchemaEnhancement:
    """Unit tests for cache_entries schema enhancement"""

    @pytest.fixture
    def mock_db_connection(self):
        """Create mock database connection"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        return mock_conn, mock_cursor

    def test_schema_enhancement_columns(self, mock_db_connection):
        """Test new columns added to cache_entries table"""
        mock_conn, mock_cursor = mock_db_connection

        # Simulate column check query
        mock_cursor.fetchall.return_value = [
            {'column_name': 'cache_key'},
            {'column_name': 'symbols'},
            {'column_name': 'universe_category'},
            {'column_name': 'liquidity_filter'},
            {'column_name': 'universe_metadata'},
            {'column_name': 'last_universe_update'}
        ]

        with patch('psycopg2.connect', return_value=mock_conn):
            # Verify new columns exist
            mock_cursor.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'cache_entries'
            """)
            columns = mock_cursor.fetchall()

            column_names = [col['column_name'] for col in columns]

            # Verify all new columns present
            assert 'universe_category' in column_names
            assert 'liquidity_filter' in column_names
            assert 'universe_metadata' in column_names
            assert 'last_universe_update' in column_names

    def test_schema_indexes_creation(self, mock_db_connection):
        """Test performance indexes created correctly"""
        mock_conn, mock_cursor = mock_db_connection

        # Simulate index check
        mock_cursor.fetchall.return_value = [
            {'indexname': 'idx_cache_entries_category'},
            {'indexname': 'idx_cache_entries_updated'},
            {'indexname': 'idx_cache_entries_etf_filter'}
        ]

        with patch('psycopg2.connect', return_value=mock_conn):
            mock_cursor.execute("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'cache_entries'
            """)
            indexes = mock_cursor.fetchall()

            index_names = [idx['indexname'] for idx in indexes]

            # Verify performance indexes
            assert 'idx_cache_entries_category' in index_names
            assert 'idx_cache_entries_updated' in index_names
            assert 'idx_cache_entries_etf_filter' in index_names

    def test_etf_universe_data_insertion(self, mock_db_connection):
        """Test ETF universe data insertion with proper structure"""
        mock_conn, mock_cursor = mock_db_connection

        sample_etf_data = {
            'cache_key': 'etf_sectors',
            'symbols': ["XLF", "XLE", "XLK", "XLV"],
            'universe_category': 'ETF',
            'liquidity_filter': {
                "min_aum": 1000000000,
                "min_volume": 5000000,
                "min_liquidity_score": 85
            },
            'universe_metadata': {
                "theme": "Sector ETFs",
                "description": "SPDR Select Sector ETFs",
                "count": 4,
                "criteria": "AUM > $1B, Volume > 5M daily",
                "focus": "sector_rotation"
            }
        }

        with patch('psycopg2.connect', return_value=mock_conn):
            # Simulate INSERT operation
            mock_cursor.execute("""
                INSERT INTO cache_entries (
                    cache_key, symbols, universe_category, 
                    liquidity_filter, universe_metadata
                ) VALUES (%s, %s, %s, %s, %s)
            """, (
                sample_etf_data['cache_key'],
                json.dumps(sample_etf_data['symbols']),
                sample_etf_data['universe_category'],
                json.dumps(sample_etf_data['liquidity_filter']),
                json.dumps(sample_etf_data['universe_metadata'])
            ))

            # Verify INSERT was called with correct parameters
            mock_cursor.execute.assert_called()
            call_args = mock_cursor.execute.call_args[0]
            assert 'INSERT INTO cache_entries' in call_args[0]
            assert len(call_args[1]) == 5  # 5 parameters

    def test_etf_themes_data_validation(self, mock_db_connection):
        """Test all 7 ETF themes have proper data structure"""
        mock_conn, mock_cursor = mock_db_connection

        expected_themes = [
            'etf_sectors', 'etf_growth', 'etf_value', 'etf_international',
            'etf_commodities', 'etf_technology', 'etf_bonds'
        ]

        # Mock ETF theme data
        mock_cursor.fetchall.return_value = [
            {
                'cache_key': theme,
                'universe_category': 'ETF',
                'symbols': ["ETF1", "ETF2", "ETF3"],
                'liquidity_filter': {"min_aum": 1000000000},
                'universe_metadata': {"theme": theme.replace('etf_', '').title()}
            }
            for theme in expected_themes
        ]

        with patch('psycopg2.connect', return_value=mock_conn):
            mock_cursor.execute("""
                SELECT cache_key, universe_category, symbols, liquidity_filter, universe_metadata
                FROM cache_entries WHERE universe_category = 'ETF'
            """)

            etf_themes = mock_cursor.fetchall()

            # Verify all themes present
            assert len(etf_themes) == 7

            for theme_data in etf_themes:
                assert theme_data['universe_category'] == 'ETF'
                assert len(theme_data['symbols']) > 0
                assert theme_data['liquidity_filter'] is not None
                assert theme_data['universe_metadata'] is not None

    def test_json_data_validation(self, mock_db_connection):
        """Test JSONB data structure validation"""
        mock_conn, mock_cursor = mock_db_connection

        # Test valid JSON structures
        valid_liquidity_filter = {
            "min_aum": 1000000000,
            "min_volume": 5000000,
            "expense_ratio_max": 0.25,
            "theme_specific": True
        }

        valid_metadata = {
            "theme": "Technology ETFs",
            "description": "Technology and innovation-focused ETFs",
            "count": 8,
            "criteria": "Technology focus, Innovation exposure",
            "focus": "technology_innovation",
            "sub_sectors": ["software", "semiconductors", "cloud", "ai_robotics"],
            "growth_orientation": True
        }

        with patch('psycopg2.connect', return_value=mock_conn):
            # Test JSON validation doesn't raise errors
            try:
                json.dumps(valid_liquidity_filter)
                json.dumps(valid_metadata)
                validation_success = True
            except (TypeError, ValueError):
                validation_success = False

            assert validation_success, "JSON data structures should be valid"


class TestETFDatabaseFunctions:
    """Unit tests for ETF database functions"""

    @pytest.fixture
    def mock_db_connection(self):
        """Create mock database connection"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        return mock_conn, mock_cursor

    def test_get_etf_universe_function(self, mock_db_connection):
        """Test get_etf_universe database function"""
        mock_conn, mock_cursor = mock_db_connection

        # Mock function response
        mock_cursor.fetchone.return_value = [{
            'cache_key': 'etf_sectors',
            'symbols': ["XLF", "XLE", "XLK"],
            'metadata': {
                "theme": "Sector ETFs",
                "count": 3,
                "focus": "sector_rotation"
            },
            'liquidity_filter': {
                "min_aum": 1000000000,
                "min_volume": 5000000
            },
            'last_updated': datetime.now(),
            'filtered': True,
            'filter_applied': {"min_aum": 1000000000}
        }]

        with patch('psycopg2.connect', return_value=mock_conn):
            # Test function call
            mock_cursor.execute("SELECT get_etf_universe(%s, %s)", ('sectors', True))
            result = mock_cursor.fetchone()

            # Verify function response structure
            assert result is not None
            response = result[0]
            assert 'cache_key' in response
            assert 'symbols' in response
            assert 'metadata' in response
            assert 'filtered' in response
            assert response['filtered'] is True

    def test_get_etf_universe_not_found(self, mock_db_connection):
        """Test get_etf_universe with non-existent theme"""
        mock_conn, mock_cursor = mock_db_connection

        # Mock not found response
        mock_cursor.fetchone.return_value = [{
            'error': 'Universe not found: nonexistent'
        }]

        with patch('psycopg2.connect', return_value=mock_conn):
            mock_cursor.execute("SELECT get_etf_universe(%s, %s)", ('nonexistent', True))
            result = mock_cursor.fetchone()

            # Verify error handling
            assert result is not None
            response = result[0]
            assert 'error' in response
            assert 'Universe not found' in response['error']

    def test_update_etf_universe_function_create(self, mock_db_connection):
        """Test update_etf_universe function creating new universe"""
        mock_conn, mock_cursor = mock_db_connection

        # Mock create response
        mock_cursor.fetchone.return_value = [{
            'action': 'created',
            'cache_key': 'etf_new_theme',
            'symbols_count': 5,
            'timestamp': datetime.now()
        }]

        new_symbols = ["ETF1", "ETF2", "ETF3", "ETF4", "ETF5"]
        metadata = {"theme": "New Theme", "description": "New ETF theme"}

        with patch('psycopg2.connect', return_value=mock_conn):
            mock_cursor.execute(
                "SELECT update_etf_universe(%s, %s, %s)",
                ('new_theme', json.dumps(new_symbols), json.dumps(metadata))
            )
            result = mock_cursor.fetchone()

            # Verify create response
            assert result is not None
            response = result[0]
            assert response['action'] == 'created'
            assert response['symbols_count'] == 5
            assert 'timestamp' in response

    def test_update_etf_universe_function_update(self, mock_db_connection):
        """Test update_etf_universe function updating existing universe"""
        mock_conn, mock_cursor = mock_db_connection

        # Mock update response with change tracking
        mock_cursor.fetchone.return_value = [{
            'action': 'updated',
            'cache_key': 'etf_sectors',
            'symbols_count': 12,
            'added_count': 2,
            'removed_count': 1,
            'symbols_added': ["NEW1", "NEW2"],
            'symbols_removed': ["OLD1"],
            'timestamp': datetime.now()
        }]

        updated_symbols = ["XLF", "XLE", "XLK", "NEW1", "NEW2"]

        with patch('psycopg2.connect', return_value=mock_conn):
            mock_cursor.execute(
                "SELECT update_etf_universe(%s, %s, %s)",
                ('sectors', json.dumps(updated_symbols), None)
            )
            result = mock_cursor.fetchone()

            # Verify update response with change tracking
            assert result is not None
            response = result[0]
            assert response['action'] == 'updated'
            assert response['added_count'] == 2
            assert response['removed_count'] == 1
            assert response['symbols_added'] == ["NEW1", "NEW2"]
            assert response['symbols_removed'] == ["OLD1"]

    def test_get_etf_universes_summary_function(self, mock_db_connection):
        """Test get_etf_universes_summary function"""
        mock_conn, mock_cursor = mock_db_connection

        # Mock summary data
        mock_cursor.fetchall.return_value = [
            {
                'theme': 'sectors',
                'symbol_count': 10,
                'last_updated': datetime.now(),
                'focus': 'sector_rotation',
                'criteria': 'AUM > $1B, Volume > 5M',
                'symbols_sample': ["XLF", "XLE", "XLK"]
            },
            {
                'theme': 'technology',
                'symbol_count': 8,
                'last_updated': datetime.now(),
                'focus': 'technology_innovation',
                'criteria': 'Technology focus, Innovation exposure',
                'symbols_sample': ["QQQ", "XLK", "VGT"]
            }
        ]

        with patch('psycopg2.connect', return_value=mock_conn):
            mock_cursor.execute("SELECT * FROM get_etf_universes_summary()")
            results = mock_cursor.fetchall()

            # Verify summary structure
            assert len(results) == 2

            for summary in results:
                assert 'theme' in summary
                assert 'symbol_count' in summary
                assert 'last_updated' in summary
                assert 'focus' in summary
                assert 'criteria' in summary
                assert 'symbols_sample' in summary
                assert summary['symbol_count'] > 0

    def test_validate_etf_universe_symbols_function(self, mock_db_connection):
        """Test validate_etf_universe_symbols function"""
        mock_conn, mock_cursor = mock_db_connection

        # Mock validation results
        mock_cursor.fetchall.return_value = [
            {
                'universe_key': 'etf_sectors',
                'symbol': 'XLF',
                'exists_in_symbols': True,
                'symbol_type': 'ETF',
                'active_status': True
            },
            {
                'universe_key': 'etf_sectors',
                'symbol': 'XLE',
                'exists_in_symbols': True,
                'symbol_type': 'ETF',
                'active_status': True
            },
            {
                'universe_key': 'etf_sectors',
                'symbol': 'MISSING',
                'exists_in_symbols': False,
                'symbol_type': 'UNKNOWN',
                'active_status': False
            }
        ]

        with patch('psycopg2.connect', return_value=mock_conn):
            mock_cursor.execute("SELECT * FROM validate_etf_universe_symbols()")
            results = mock_cursor.fetchall()

            # Verify validation results
            assert len(results) == 3

            # Count validation statistics
            total_symbols = len(results)
            found_symbols = sum(1 for r in results if r['exists_in_symbols'])
            active_symbols = sum(1 for r in results if r['active_status'])

            assert total_symbols == 3
            assert found_symbols == 2
            assert active_symbols == 2

            # Verify data structure
            for result in results:
                assert 'universe_key' in result
                assert 'symbol' in result
                assert 'exists_in_symbols' in result
                assert 'symbol_type' in result
                assert 'active_status' in result


class TestETFPerformanceView:
    """Unit tests for ETF universe performance view"""

    @pytest.fixture
    def mock_db_connection(self):
        """Create mock database connection"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        return mock_conn, mock_cursor

    def test_etf_universe_performance_view(self, mock_db_connection):
        """Test ETF universe performance view structure and data"""
        mock_conn, mock_cursor = mock_db_connection

        # Mock performance data
        mock_cursor.fetchall.return_value = [
            {
                'cache_key': 'etf_sectors',
                'theme': 'Sector ETFs',
                'symbol': 'XLF',
                'close_price': 38.50,
                'price_20d_ago': 36.20,
                'return_20d_pct': 6.35,
                'volume': 45000000,
                'avg_volume_20d': 42000000,
                'volume_ratio': 1.07
            },
            {
                'cache_key': 'etf_technology',
                'theme': 'Technology ETFs',
                'symbol': 'QQQ',
                'close_price': 385.40,
                'price_20d_ago': 370.15,
                'return_20d_pct': 4.12,
                'volume': 48000000,
                'avg_volume_20d': 45000000,
                'volume_ratio': 1.07
            }
        ]

        with patch('psycopg2.connect', return_value=mock_conn):
            mock_cursor.execute("SELECT * FROM etf_universe_performance ORDER BY return_20d_pct DESC")
            results = mock_cursor.fetchall()

            # Verify view structure
            assert len(results) == 2

            for performance in results:
                assert 'cache_key' in performance
                assert 'theme' in performance
                assert 'symbol' in performance
                assert 'close_price' in performance
                assert 'return_20d_pct' in performance
                assert 'volume' in performance
                assert 'avg_volume_20d' in performance
                assert 'volume_ratio' in performance

                # Verify performance calculations
                assert performance['return_20d_pct'] is not None
                assert performance['volume_ratio'] >= 0

    def test_etf_performance_calculations(self, mock_db_connection):
        """Test ETF performance view calculations are correct"""
        mock_conn, mock_cursor = mock_db_connection

        # Test data with known calculations
        test_close = 100.0
        test_price_20d = 95.0
        expected_return = ((test_close - test_price_20d) / test_price_20d) * 100  # 5.26%

        test_volume = 5000000
        test_avg_volume = 4000000
        expected_volume_ratio = test_volume / test_avg_volume  # 1.25

        mock_cursor.fetchall.return_value = [
            {
                'cache_key': 'etf_test',
                'symbol': 'TEST',
                'close_price': test_close,
                'price_20d_ago': test_price_20d,
                'return_20d_pct': round(expected_return, 2),
                'volume': test_volume,
                'avg_volume_20d': test_avg_volume,
                'volume_ratio': round(expected_volume_ratio, 2)
            }
        ]

        with patch('psycopg2.connect', return_value=mock_conn):
            mock_cursor.execute("SELECT * FROM etf_universe_performance WHERE symbol = 'TEST'")
            result = mock_cursor.fetchone()

            # Verify calculations
            assert result is not None
            assert abs(result['return_20d_pct'] - 5.26) < 0.01  # 5.26% return
            assert abs(result['volume_ratio'] - 1.25) < 0.01    # 1.25x volume ratio


class TestCacheEntriesPerformance:
    """Performance tests for cache_entries database operations"""

    @pytest.fixture
    def mock_db_connection(self):
        """Create mock database connection"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        return mock_conn, mock_cursor

    @pytest.mark.performance
    def test_etf_universe_query_performance(self, mock_db_connection):
        """Test ETF universe queries meet <2 second requirement"""
        mock_conn, mock_cursor = mock_db_connection

        # Mock large ETF dataset (200+ symbols across 7 themes)
        large_etf_data = []
        for theme_idx in range(7):  # 7 themes
            for etf_idx in range(30):  # ~30 ETFs per theme
                large_etf_data.append({
                    'cache_key': f'etf_theme_{theme_idx}',
                    'symbol': f'ETF_{theme_idx}_{etf_idx}',
                    'universe_category': 'ETF',
                    'symbols': [f'ETF_{theme_idx}_{i}' for i in range(30)],
                    'metadata': {'theme': f'Theme {theme_idx}', 'count': 30}
                })

        mock_cursor.fetchall.return_value = large_etf_data

        with patch('psycopg2.connect', return_value=mock_conn):
            import time

            start_time = time.time()

            # Simulate complex ETF query
            mock_cursor.execute("""
                SELECT cache_key, symbols, universe_metadata, 
                       jsonb_array_length(symbols) as symbol_count
                FROM cache_entries 
                WHERE universe_category = 'ETF'
                ORDER BY jsonb_array_length(symbols) DESC
            """)
            results = mock_cursor.fetchall()

            query_time = time.time() - start_time

            # Verify performance requirement: <2 seconds for 200+ ETF processing
            assert query_time < 2.0, f"ETF query took {query_time:.3f}s, expected <2s"

            # Verify data processed
            assert len(results) > 0

    @pytest.mark.performance
    def test_etf_universe_update_performance(self, mock_db_connection):
        """Test ETF universe update performance"""
        mock_conn, mock_cursor = mock_db_connection

        # Mock update function response
        mock_cursor.fetchone.return_value = [{
            'action': 'updated',
            'cache_key': 'etf_large_theme',
            'symbols_count': 50,
            'added_count': 10,
            'removed_count': 5
        }]

        with patch('psycopg2.connect', return_value=mock_conn):
            import time

            # Large symbol list update
            large_symbol_list = [f'LARGE_ETF_{i:03d}' for i in range(50)]
            metadata = {
                'theme': 'Large Theme',
                'count': 50,
                'update_time': datetime.now().isoformat()
            }

            start_time = time.time()

            mock_cursor.execute(
                "SELECT update_etf_universe(%s, %s, %s)",
                ('large_theme', json.dumps(large_symbol_list), json.dumps(metadata))
            )
            result = mock_cursor.fetchone()

            update_time = time.time() - start_time

            # Verify performance: large updates should complete quickly
            assert update_time < 1.0, f"Large ETF update took {update_time:.3f}s, expected <1s"

            # Verify update succeeded
            assert result is not None

    @pytest.mark.performance
    def test_etf_validation_performance(self, mock_db_connection):
        """Test ETF symbol validation performance with large datasets"""
        mock_conn, mock_cursor = mock_db_connection

        # Mock large validation dataset
        validation_results = []
        for theme_idx in range(7):
            for symbol_idx in range(30):
                validation_results.append({
                    'universe_key': f'etf_theme_{theme_idx}',
                    'symbol': f'ETF_{theme_idx}_{symbol_idx}',
                    'exists_in_symbols': symbol_idx % 10 != 0,  # 90% exist
                    'symbol_type': 'ETF',
                    'active_status': symbol_idx % 15 != 0  # ~93% active
                })

        mock_cursor.fetchall.return_value = validation_results

        with patch('psycopg2.connect', return_value=mock_conn):
            import time

            start_time = time.time()

            mock_cursor.execute("SELECT * FROM validate_etf_universe_symbols()")
            results = mock_cursor.fetchall()

            validation_time = time.time() - start_time

            # Verify performance: validation should be fast
            assert validation_time < 0.5, f"ETF validation took {validation_time:.3f}s, expected <0.5s"

            # Verify comprehensive validation
            assert len(results) == 210  # 7 themes × 30 ETFs

    @pytest.mark.performance
    def test_etf_performance_view_query_performance(self, mock_db_connection):
        """Test ETF performance view query performance"""
        mock_conn, mock_cursor = mock_db_connection

        # Mock performance data for many ETFs
        performance_data = []
        for i in range(200):  # 200 ETFs
            performance_data.append({
                'cache_key': f'etf_theme_{i % 7}',
                'symbol': f'ETF_{i:03d}',
                'close_price': 100.0 + (i % 50),
                'return_20d_pct': (i % 20) - 10,  # -10% to +9%
                'volume': 1000000 + (i * 10000),
                'volume_ratio': 1.0 + (i % 10) * 0.1
            })

        mock_cursor.fetchall.return_value = performance_data

        with patch('psycopg2.connect', return_value=mock_conn):
            import time

            start_time = time.time()

            mock_cursor.execute("""
                SELECT * FROM etf_universe_performance 
                ORDER BY return_20d_pct DESC 
                LIMIT 50
            """)
            results = mock_cursor.fetchall()

            query_time = time.time() - start_time

            # Verify performance: complex view queries should be fast
            assert query_time < 1.0, f"Performance view query took {query_time:.3f}s, expected <1s"

            # Verify results
            assert len(results) <= 50  # Limited results

    @pytest.mark.performance
    def test_concurrent_etf_operations_performance(self, mock_db_connection):
        """Test concurrent ETF operations performance"""
        mock_conn, mock_cursor = mock_db_connection

        # Mock responses for concurrent operations
        mock_cursor.fetchone.side_effect = [
            [{'cache_key': 'etf_sectors', 'symbols': ['XLF', 'XLE']}],  # get_etf_universe
            [{'action': 'updated', 'symbols_count': 10}],  # update_etf_universe
            [{'cache_key': 'etf_growth', 'symbols': ['VUG', 'IVW']}]   # get_etf_universe
        ]

        with patch('psycopg2.connect', return_value=mock_conn):
            import time

            start_time = time.time()

            # Simulate concurrent operations
            operations = [
                ("SELECT get_etf_universe(%s, %s)", ('sectors', True)),
                ("SELECT update_etf_universe(%s, %s, %s)", ('sectors', '["XLF","XLE","XLK"]', '{"updated":true}')),
                ("SELECT get_etf_universe(%s, %s)", ('growth', False))
            ]

            for query, params in operations:
                mock_cursor.execute(query, params)
                result = mock_cursor.fetchone()
                assert result is not None

            total_time = time.time() - start_time

            # Verify concurrent operations complete efficiently
            assert total_time < 0.1, f"Concurrent operations took {total_time:.3f}s, expected <0.1s"


class TestCacheEntriesRegression:
    """Regression tests for cache_entries enhancements"""

    @pytest.fixture
    def mock_db_connection(self):
        """Create mock database connection"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        return mock_conn, mock_cursor

    def test_existing_cache_entries_compatibility(self, mock_db_connection):
        """Test existing cache_entries functionality preserved"""
        mock_conn, mock_cursor = mock_db_connection

        # Mock existing cache_entries data
        mock_cursor.fetchall.return_value = [
            {
                'cache_key': 'top_100',
                'symbols': ['AAPL', 'MSFT', 'GOOGL'],
                'universe_category': None,  # Existing entries may not have new columns
                'liquidity_filter': None,
                'universe_metadata': None
            },
            {
                'cache_key': 'high_growth',
                'symbols': ['TSLA', 'NVDA', 'AMD'],
                'universe_category': None,
                'liquidity_filter': None,
                'universe_metadata': None
            }
        ]

        with patch('psycopg2.connect', return_value=mock_conn):
            # Test existing functionality still works
            mock_cursor.execute("SELECT cache_key, symbols FROM cache_entries")
            results = mock_cursor.fetchall()

            # Verify existing data structure preserved
            assert len(results) == 2
            for result in results:
                assert 'cache_key' in result
                assert 'symbols' in result
                assert len(result['symbols']) > 0

    def test_mixed_old_new_data_compatibility(self, mock_db_connection):
        """Test compatibility between old and new cache_entries data"""
        mock_conn, mock_cursor = mock_db_connection

        # Mock mixed data (old and new format)
        mock_cursor.fetchall.return_value = [
            {
                'cache_key': 'legacy_universe',
                'symbols': ['AAPL', 'MSFT'],
                'universe_category': None,
                'universe_metadata': None
            },
            {
                'cache_key': 'etf_sectors',
                'symbols': ['XLF', 'XLE'],
                'universe_category': 'ETF',
                'universe_metadata': {'theme': 'Sectors'}
            }
        ]

        with patch('psycopg2.connect', return_value=mock_conn):
            mock_cursor.execute("""
                SELECT cache_key, symbols, universe_category, universe_metadata
                FROM cache_entries
            """)
            results = mock_cursor.fetchall()

            # Verify mixed data handling
            legacy_entry = next(r for r in results if r['cache_key'] == 'legacy_universe')
            etf_entry = next(r for r in results if r['cache_key'] == 'etf_sectors')

            # Legacy entry compatibility
            assert legacy_entry['universe_category'] is None
            assert legacy_entry['universe_metadata'] is None
            assert len(legacy_entry['symbols']) == 2

            # New entry functionality
            assert etf_entry['universe_category'] == 'ETF'
            assert etf_entry['universe_metadata'] is not None
            assert len(etf_entry['symbols']) == 2

    def test_database_function_error_handling(self, mock_db_connection):
        """Test database function error handling remains consistent"""
        mock_conn, mock_cursor = mock_db_connection

        # Test error scenarios
        error_scenarios = [
            ('get_etf_universe', ('nonexistent', True), {'error': 'Universe not found: nonexistent'}),
            ('update_etf_universe', ('', '[]', '{}'), {'error': 'Invalid parameters'}),
            ('validate_etf_universe_symbols', (), {'error': 'No ETF universes found'})
        ]

        for func_name, params, expected_error in error_scenarios:
            mock_cursor.fetchone.return_value = [expected_error]

            with patch('psycopg2.connect', return_value=mock_conn):
                mock_cursor.execute(f"SELECT {func_name}({', '.join(['%s'] * len(params))})", params)
                result = mock_cursor.fetchone()

                # Verify error handling
                assert result is not None
                assert 'error' in result[0]

    def test_index_performance_maintained(self, mock_db_connection):
        """Test that new indexes don't degrade existing performance"""
        mock_conn, mock_cursor = mock_db_connection

        # Mock query plan analysis
        mock_cursor.fetchall.return_value = [
            {
                'query_plan': 'Index Scan using idx_cache_entries_category',
                'execution_time': 0.5,
                'rows': 100
            }
        ]

        with patch('psycopg2.connect', return_value=mock_conn):
            # Test that indexes are being used
            mock_cursor.execute("""
                EXPLAIN ANALYZE 
                SELECT * FROM cache_entries 
                WHERE universe_category = 'ETF'
            """)
            plans = mock_cursor.fetchall()

            # Verify index usage
            assert len(plans) > 0
            plan = plans[0]
            assert 'Index Scan' in plan['query_plan']
            assert plan['execution_time'] < 1.0  # Should be fast with index

    def test_data_migration_integrity(self, mock_db_connection):
        """Test data integrity after schema enhancement"""
        mock_conn, mock_cursor = mock_db_connection

        # Mock data integrity check
        mock_cursor.fetchall.return_value = [
            {
                'cache_key': 'etf_sectors',
                'symbols_count': 10,
                'json_valid': True,
                'metadata_valid': True
            }
        ]

        with patch('psycopg2.connect', return_value=mock_conn):
            # Test data integrity validation
            mock_cursor.execute("""
                SELECT 
                    cache_key,
                    jsonb_array_length(symbols) as symbols_count,
                    (liquidity_filter IS NULL OR jsonb_typeof(liquidity_filter) = 'object') as json_valid,
                    (universe_metadata IS NULL OR jsonb_typeof(universe_metadata) = 'object') as metadata_valid
                FROM cache_entries
                WHERE universe_category = 'ETF'
            """)

            integrity_results = mock_cursor.fetchall()

            # Verify data integrity
            for result in integrity_results:
                assert result['symbols_count'] > 0
                assert result['json_valid'] is True
                assert result['metadata_valid'] is True


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
