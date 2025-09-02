"""
Error Handling and Data Integrity Tests for CacheEntriesSynchronizer

Tests error conditions, failure scenarios, and data integrity validation
for the cache synchronizer service. Ensures robust error handling and
data consistency under various failure conditions.

Test Coverage:
- Database connection failures and recovery
- Transaction rollback scenarios
- Redis connection failures and graceful degradation
- Data validation and integrity checks
- Partial failure recovery mechanisms
- Timeout and resource exhaustion handling
- Concurrent access and locking scenarios
- Data corruption detection and prevention
"""

import pytest
import json
import time
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch, call, side_effect
from typing import Dict, List, Any
import psycopg2
from psycopg2.extras import RealDictCursor
import redis

# Import the class under test
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'src'))

from src.core.services.cache_entries_synchronizer import CacheEntriesSynchronizer


class TestCacheEntriesSynchronizerErrorHandling:
    """Error handling and data integrity tests for CacheEntriesSynchronizer."""

    @pytest.fixture
    def synchronizer(self):
        """Create synchronizer instance for error testing."""
        with patch('src.core.services.cache_entries_synchronizer.load_dotenv'):
            return CacheEntriesSynchronizer()

    @pytest.fixture
    def mock_test_data(self):
        """Standard test data for error scenarios."""
        return {
            'stocks': [
                {'symbol': 'AAPL', 'name': 'Apple Inc.', 'market_cap': 3000000000000, 'sector': 'Technology', 'industry': 'Consumer Electronics', 'primary_exchange': 'NASDAQ'},
                {'symbol': 'MSFT', 'name': 'Microsoft Corporation', 'market_cap': 2500000000000, 'sector': 'Technology', 'industry': 'Software', 'primary_exchange': 'NASDAQ'},
            ],
            'etfs': [
                {'symbol': 'SPY', 'name': 'SPDR S&P 500 ETF Trust', 'market_cap': 400000000000, 'etf_type': 'Index', 'issuer': 'State Street', 'primary_exchange': 'NYSE'}
            ],
            'sectors': ['Technology', 'Healthcare']
        }

    # Database Connection Error Tests
    
    @patch('src.core.services.cache_entries_synchronizer.os.getenv')
    def test_missing_database_uri_error(self, mock_getenv, synchronizer):
        """Test error handling when DATABASE_URI environment variable is missing."""
        mock_getenv.return_value = None
        
        result = synchronizer.connect()
        
        assert result is False
        assert synchronizer.db_conn is None

    @patch('src.core.services.cache_entries_synchronizer.psycopg2.connect')  
    @patch('src.core.services.cache_entries_synchronizer.os.getenv')
    def test_database_connection_failure(self, mock_getenv, mock_connect, synchronizer):
        """Test error handling when database connection fails."""
        mock_getenv.return_value = 'postgresql://user:pass@localhost:5432/testdb'
        mock_connect.side_effect = psycopg2.OperationalError("Connection refused")
        
        result = synchronizer.connect()
        
        assert result is False
        assert synchronizer.db_conn is None

    @patch('src.core.services.cache_entries_synchronizer.psycopg2.connect')
    @patch('src.core.services.cache_entries_synchronizer.os.getenv') 
    def test_database_authentication_failure(self, mock_getenv, mock_connect, synchronizer):
        """Test error handling when database authentication fails."""
        mock_getenv.return_value = 'postgresql://baduser:badpass@localhost:5432/testdb'
        mock_connect.side_effect = psycopg2.OperationalError("FATAL: password authentication failed")
        
        result = synchronizer.connect()
        
        assert result is False
        assert synchronizer.db_conn is None

    def test_database_connection_lost_during_operation(self, synchronizer, mock_test_data):
        """Test handling when database connection is lost during operation."""
        mock_db_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_cursor.execute.side_effect = psycopg2.InterfaceError("Connection lost")
        mock_db_conn.cursor.return_value = mock_cursor
        
        synchronizer.db_conn = mock_db_conn
        
        with pytest.raises(psycopg2.InterfaceError):
            synchronizer._delete_stock_etf_entries()

    # Transaction and Rollback Error Tests
    
    def test_transaction_rollback_on_error(self, synchronizer, mock_test_data):
        """Test that transactions are properly rolled back on errors."""
        mock_db_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        
        # Setup successful operations followed by failure
        mock_cursor.execute.side_effect = [
            None,  # DELETE succeeds
            None,  # First INSERT succeeds  
            psycopg2.Error("Constraint violation")  # Second INSERT fails
        ]
        
        synchronizer.db_conn = mock_db_conn
        
        with patch.object(synchronizer, 'connect', return_value=True):
            with patch.object(synchronizer, 'disconnect'):
                with pytest.raises(psycopg2.Error):
                    synchronizer.rebuild_stock_cache_entries()
        
        # Verify rollback was called
        mock_db_conn.rollback.assert_called_once()
        mock_db_conn.commit.assert_not_called()

    def test_deadlock_detection_and_recovery(self, synchronizer, mock_test_data):
        """Test handling of database deadlock scenarios."""
        mock_db_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_cursor.execute.side_effect = psycopg2.OperationalError("deadlock detected")
        mock_db_conn.cursor.return_value = mock_cursor
        
        synchronizer.db_conn = mock_db_conn
        
        with patch.object(synchronizer, 'connect', return_value=True):
            with patch.object(synchronizer, 'disconnect'):
                with pytest.raises(psycopg2.OperationalError):
                    synchronizer.rebuild_stock_cache_entries()
        
        mock_db_conn.rollback.assert_called_once()

    # Redis Error Handling Tests
    
    @patch('src.core.services.cache_entries_synchronizer.redis.Redis')
    @patch('src.core.services.cache_entries_synchronizer.psycopg2.connect')
    @patch('src.core.services.cache_entries_synchronizer.os.getenv')
    def test_redis_connection_failure_graceful_degradation(self, mock_getenv, mock_connect, mock_redis, synchronizer):
        """Test graceful degradation when Redis connection fails."""
        # Setup successful database connection
        mock_getenv.side_effect = lambda key, default=None: {
            'DATABASE_URI': 'postgresql://user:pass@localhost:5432/testdb',
            'REDIS_HOST': 'localhost', 'REDIS_PORT': '6379', 'REDIS_DB': '0'
        }.get(key, default)
        
        mock_db_conn = Mock()
        mock_connect.return_value = mock_db_conn
        
        # Redis connection fails
        mock_redis_client = Mock()
        mock_redis_client.ping.side_effect = redis.ConnectionError("Redis connection failed")
        mock_redis.return_value = mock_redis_client
        
        result = synchronizer.connect()
        
        # Should still connect successfully despite Redis failure
        assert result is True
        assert synchronizer.db_conn is not None
        assert synchronizer.redis_client is None  # Redis should be disabled

    def test_redis_publish_failure_does_not_affect_rebuild(self, synchronizer, mock_test_data):
        """Test that Redis publish failures don't affect cache rebuild."""
        # Setup working database
        mock_db_conn, mock_cursor = self._setup_working_database_mock(synchronizer, mock_test_data)
        
        # Setup failing Redis
        mock_redis = Mock()
        mock_redis.publish.side_effect = redis.RedisError("Redis publish failed")
        synchronizer.redis_client = mock_redis
        
        with patch.object(synchronizer, 'connect', return_value=True):
            with patch.object(synchronizer, 'disconnect'):
                # Should complete successfully despite Redis failures
                stats = synchronizer.rebuild_stock_cache_entries()
        
        # Verify rebuild completed
        assert isinstance(stats, dict)
        assert stats['redis_notifications'] == 0  # Redis notifications failed
        
        # Verify database operations succeeded
        mock_db_conn.commit.assert_called_once()

    # Data Validation and Integrity Tests
    
    def test_invalid_market_cap_data_handling(self, synchronizer):
        """Test handling of invalid or missing market cap data."""
        invalid_data = [
            {'symbol': 'TEST1', 'name': 'Test 1', 'market_cap': None, 'sector': 'Technology', 'industry': 'Software', 'primary_exchange': 'NYSE'},
            {'symbol': 'TEST2', 'name': 'Test 2', 'market_cap': -1000000, 'sector': 'Technology', 'industry': 'Software', 'primary_exchange': 'NYSE'},
            {'symbol': 'TEST3', 'name': 'Test 3', 'market_cap': 'invalid', 'sector': 'Technology', 'industry': 'Software', 'primary_exchange': 'NYSE'},
        ]
        
        mock_db_conn, mock_cursor = self._setup_working_database_mock(synchronizer, {'stocks': invalid_data})
        mock_cursor.fetchall.return_value = invalid_data
        
        # Should handle invalid data gracefully
        try:
            result = synchronizer._create_market_cap_entries()
            # Method should complete without crashing
            assert isinstance(result, int)
        except (TypeError, ValueError) as e:
            pytest.fail(f"Should handle invalid market cap data gracefully: {e}")

    def test_missing_required_fields_handling(self, synchronizer):
        """Test handling of records with missing required fields."""
        incomplete_data = [
            {'symbol': 'TEST1'},  # Missing required fields
            {'name': 'Test Company'},  # Missing symbol
            {'symbol': 'TEST2', 'name': 'Test 2', 'market_cap': 1000000000},  # Missing sector/industry
        ]
        
        mock_db_conn, mock_cursor = self._setup_working_database_mock(synchronizer, {'stocks': incomplete_data})
        mock_cursor.fetchall.return_value = incomplete_data
        
        # Should handle incomplete data without crashing
        try:
            result = synchronizer._create_market_cap_entries()
            assert isinstance(result, int)
        except KeyError as e:
            # If method expects required fields, should handle gracefully
            pytest.fail(f"Should handle missing fields gracefully: {e}")

    def test_unicode_and_special_characters_handling(self, synchronizer):
        """Test handling of Unicode and special characters in data."""
        special_char_data = [
            {'symbol': 'TEST1', 'name': 'Tëst Çompañy with üñicode', 'market_cap': 1000000000, 'sector': 'Tëchnology', 'industry': 'Sõftware', 'primary_exchange': 'NYSE'},
            {'symbol': 'TEST2', 'name': 'Company "with" quotes & ampersands', 'market_cap': 2000000000, 'sector': 'Tech & Services', 'industry': 'Software & Hardware', 'primary_exchange': 'NASDAQ'},
            {'symbol': 'TEST3', 'name': "Company's name with apostrophe", 'market_cap': 3000000000, 'sector': 'Technology', 'industry': 'Software', 'primary_exchange': 'NYSE'},
        ]
        
        mock_db_conn, mock_cursor = self._setup_working_database_mock(synchronizer, {'stocks': special_char_data})
        mock_cursor.fetchall.return_value = special_char_data
        
        # Should handle special characters without JSON serialization errors
        try:
            result = synchronizer._create_market_cap_entries()
            assert isinstance(result, int)
            
            # Verify INSERT operations succeeded
            insert_calls = [call for call in mock_cursor.execute.call_args_list if 'INSERT' in str(call)]
            assert len(insert_calls) > 0
            
            # Verify JSON in INSERT calls is valid
            for call in insert_calls:
                json_value = call[0][1][3]  # Fourth parameter should be JSON
                parsed = json.loads(json_value)  # Should not raise JSON decode error
                assert isinstance(parsed, dict)
                
        except (UnicodeError, json.JSONDecodeError) as e:
            pytest.fail(f"Should handle special characters in JSON serialization: {e}")

    def test_extremely_large_numbers_handling(self, synchronizer):
        """Test handling of extremely large market cap values."""
        large_number_data = [
            {'symbol': 'HUGE1', 'name': 'Huge Company', 'market_cap': 999999999999999999999, 'sector': 'Technology', 'industry': 'Software', 'primary_exchange': 'NYSE'},  # Very large number
            {'symbol': 'HUGE2', 'name': 'Another Huge Company', 'market_cap': float('inf'), 'sector': 'Technology', 'industry': 'Software', 'primary_exchange': 'NYSE'},  # Infinity
        ]
        
        mock_db_conn, mock_cursor = self._setup_working_database_mock(synchronizer, {'stocks': large_number_data})
        mock_cursor.fetchall.return_value = large_number_data
        
        # Should handle extremely large numbers gracefully
        try:
            result = synchronizer._create_market_cap_entries()
            assert isinstance(result, int)
        except (OverflowError, ValueError) as e:
            pytest.fail(f"Should handle large numbers gracefully: {e}")

    # Resource Exhaustion Tests
    
    def test_memory_exhaustion_simulation(self, synchronizer):
        """Test behavior when system memory is constrained."""
        # Create a dataset that would use significant memory
        memory_intensive_data = []
        for i in range(1000):
            # Large data structures
            memory_intensive_data.append({
                'symbol': f'STOCK{i:04d}',
                'name': f'Very Long Company Name That Uses Lots Of Memory ' * 20,  # Very long names
                'market_cap': 1000000000 + i,
                'sector': f'Sector With Very Long Name {i}' * 10,
                'industry': f'Industry With Extremely Long Name {i}' * 15,
                'primary_exchange': 'NYSE'
            })
        
        mock_db_conn, mock_cursor = self._setup_working_database_mock(synchronizer, {'stocks': memory_intensive_data})
        mock_cursor.fetchall.return_value = memory_intensive_data
        
        # Should complete without memory errors
        try:
            result = synchronizer._create_market_cap_entries()
            assert isinstance(result, int)
        except MemoryError as e:
            # If memory error occurs, should be handled gracefully
            pytest.fail(f"Should handle memory constraints gracefully: {e}")

    def test_database_timeout_handling(self, synchronizer, mock_test_data):
        """Test handling of database query timeouts."""
        mock_db_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_cursor.execute.side_effect = psycopg2.OperationalError("Query timeout")
        mock_db_conn.cursor.return_value = mock_cursor
        
        synchronizer.db_conn = mock_db_conn
        
        with pytest.raises(psycopg2.OperationalError, match="Query timeout"):
            synchronizer._delete_stock_etf_entries()

    # Concurrent Access Error Tests
    
    def test_table_lock_contention_handling(self, synchronizer, mock_test_data):
        """Test handling of table lock contention."""
        mock_db_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_cursor.execute.side_effect = psycopg2.OperationalError("could not obtain lock on relation")
        mock_db_conn.cursor.return_value = mock_cursor
        
        synchronizer.db_conn = mock_db_conn
        
        with pytest.raises(psycopg2.OperationalError):
            synchronizer._delete_stock_etf_entries()

    def test_concurrent_modification_detection(self, synchronizer, mock_test_data):
        """Test detection of concurrent modifications during rebuild."""
        mock_db_conn, mock_cursor = self._setup_working_database_mock(synchronizer, mock_test_data)
        
        # Simulate concurrent modifications by changing rowcount during operations
        original_rowcount = 50
        modified_rowcount = 75  # Someone else modified the table
        
        call_count = 0
        def varying_rowcount():
            nonlocal call_count
            call_count += 1
            return modified_rowcount if call_count > 5 else original_rowcount
        
        type(mock_cursor).rowcount = property(lambda self: varying_rowcount())
        
        with patch.object(synchronizer, 'connect', return_value=True):
            with patch.object(synchronizer, 'disconnect'):
                # Should complete despite concurrent modifications
                stats = synchronizer.rebuild_stock_cache_entries()
        
        assert isinstance(stats, dict)
        # The operation should be resilient to concurrent access

    # Data Corruption Prevention Tests
    
    def test_json_corruption_prevention(self, synchronizer, mock_test_data):
        """Test prevention of JSON corruption in stored values."""
        mock_db_conn, mock_cursor = self._setup_working_database_mock(synchronizer, mock_test_data)
        
        # Track all JSON operations
        json_values = []
        
        def capture_json_execute(*args, **kwargs):
            if len(args) > 1 and len(args[1]) > 3:
                json_value = args[1][3]  # Fourth parameter is JSON
                try:
                    parsed = json.loads(json_value)
                    json_values.append(parsed)
                except (json.JSONDecodeError, TypeError):
                    # Non-JSON parameters are OK
                    pass
        
        mock_cursor.execute.side_effect = capture_json_execute
        
        with patch.object(synchronizer, 'connect', return_value=True):
            with patch.object(synchronizer, 'disconnect'):
                stats = synchronizer.rebuild_stock_cache_entries()
        
        # Verify all JSON values are properly structured
        for json_value in json_values:
            assert isinstance(json_value, (dict, list)), f"Invalid JSON structure: {type(json_value)}"
            
            if isinstance(json_value, dict):
                # Verify expected structure for dict entries
                if 'stocks' in json_value:
                    assert 'count' in json_value
                    assert isinstance(json_value['stocks'], list)
                    for stock in json_value['stocks']:
                        assert 'ticker' in stock
                        assert 'name' in stock

    def test_sql_injection_prevention(self, synchronizer):
        """Test prevention of SQL injection through malicious data."""
        malicious_data = [
            {'symbol': "'; DROP TABLE cache_entries; --", 'name': 'Malicious Company', 'market_cap': 1000000000, 'sector': 'Technology', 'industry': 'Software', 'primary_exchange': 'NYSE'},
            {'symbol': 'TEST', 'name': "Company'; DELETE FROM cache_entries; --", 'market_cap': 2000000000, 'sector': 'Technology', 'industry': 'Software', 'primary_exchange': 'NYSE'},
        ]
        
        mock_db_conn, mock_cursor = self._setup_working_database_mock(synchronizer, {'stocks': malicious_data})
        mock_cursor.fetchall.return_value = malicious_data
        
        # Should handle malicious data safely using parameterized queries
        result = synchronizer._create_market_cap_entries()
        
        # Verify parameterized queries are used (no SQL injection possible)
        execute_calls = mock_cursor.execute.call_args_list
        for call in execute_calls:
            query = call[0][0]
            params = call[0][1] if len(call[0]) > 1 else None
            
            # Verify parameterized queries are used (contains %s placeholders)
            if 'INSERT' in query:
                assert '%s' in query, "Should use parameterized queries for INSERT operations"
                assert params is not None, "Should provide parameters for parameterized query"

    def test_constraint_violation_handling(self, synchronizer, mock_test_data):
        """Test handling of database constraint violations."""
        mock_db_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_cursor.execute.side_effect = psycopg2.IntegrityError("duplicate key violates unique constraint")
        mock_db_conn.cursor.return_value = mock_cursor
        
        synchronizer.db_conn = mock_db_conn
        
        with pytest.raises(psycopg2.IntegrityError):
            synchronizer._delete_stock_etf_entries()

    # Helper Methods
    
    def _setup_working_database_mock(self, synchronizer, test_data):
        """Setup a working database mock for error testing."""
        mock_db_conn = Mock()
        mock_cursor = Mock(spec=RealDictCursor)
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        
        def dynamic_fetchall(*args, **kwargs):
            if len(args) > 0 and isinstance(args[0], str):
                query = args[0].lower()
                if 'distinct sector' in query:
                    return [{'sector': sector} for sector in test_data.get('sectors', [])]
                elif 'type = \'etf\'' in query:
                    return [{'symbol': etf['symbol']} for etf in test_data.get('etfs', [])]
            return test_data.get('stocks', [])
        
        mock_cursor.fetchall.side_effect = dynamic_fetchall
        mock_cursor.fetchone.return_value = {
            'total_stocks': len(test_data.get('stocks', [])),
            'unique_sectors': len(test_data.get('sectors', [])),
            'total_market_cap': 10000000000000,
            'average_market_cap': 1000000000000,
            'unique_industries': 25,
            'unique_exchanges': 3
        }
        mock_cursor.rowcount = 25
        
        mock_db_conn.cursor.return_value = mock_cursor
        synchronizer.db_conn = mock_db_conn
        
        return mock_db_conn, mock_cursor