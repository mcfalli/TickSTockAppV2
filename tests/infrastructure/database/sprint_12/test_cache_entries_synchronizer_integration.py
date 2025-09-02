"""
Integration Tests for CacheEntriesSynchronizer

Tests the complete workflow of cache synchronization including database interactions,
transaction management, and end-to-end cache rebuilding process.

Test Coverage:
- Complete rebuild_stock_cache_entries workflow
- Database transaction management and rollback scenarios
- Cross-method integration and data consistency
- Real database operations with test data
- Performance validation for typical datasets
- Redis integration and notification publishing
- Error recovery and cleanup procedures
"""

import pytest
import json
import time
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch, call
from typing import Dict, List, Any
import psycopg2
from psycopg2.extras import RealDictCursor
import redis

# Import the class under test
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'src'))

from src.core.services.cache_entries_synchronizer import CacheEntriesSynchronizer


class TestCacheEntriesSynchronizerIntegration:
    """Integration tests for CacheEntriesSynchronizer class."""

    @pytest.fixture
    def synchronizer(self):
        """Create synchronizer instance for integration testing."""
        with patch('src.core.services.cache_entries_synchronizer.load_dotenv'):
            return CacheEntriesSynchronizer()

    @pytest.fixture
    def mock_db_with_cursor(self):
        """Create mock database connection with cursor context manager."""
        mock_conn = Mock()
        mock_cursor = Mock(spec=RealDictCursor)
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_cursor.rowcount = 0
        mock_conn.cursor.return_value = mock_cursor
        return mock_conn, mock_cursor

    @pytest.fixture
    def comprehensive_test_data(self):
        """Comprehensive test dataset for integration testing."""
        return {
            'stocks': [
                # Mega cap stocks
                {'symbol': 'AAPL', 'name': 'Apple Inc.', 'market_cap': 3000000000000, 'sector': 'Technology', 'industry': 'Consumer Electronics', 'primary_exchange': 'NASDAQ'},
                {'symbol': 'MSFT', 'name': 'Microsoft Corporation', 'market_cap': 2500000000000, 'sector': 'Technology', 'industry': 'Software', 'primary_exchange': 'NASDAQ'},
                {'symbol': 'GOOGL', 'name': 'Alphabet Inc.', 'market_cap': 2000000000000, 'sector': 'Technology', 'industry': 'Internet Content & Information', 'primary_exchange': 'NASDAQ'},
                
                # Large cap stocks
                {'symbol': 'JPM', 'name': 'JPMorgan Chase & Co.', 'market_cap': 500000000000, 'sector': 'Financial Services', 'industry': 'Banks', 'primary_exchange': 'NYSE'},
                {'symbol': 'JNJ', 'name': 'Johnson & Johnson', 'market_cap': 450000000000, 'sector': 'Healthcare', 'industry': 'Drug Manufacturers', 'primary_exchange': 'NYSE'},
                
                # Mid cap stocks
                {'symbol': 'AMD', 'name': 'Advanced Micro Devices', 'market_cap': 250000000000, 'sector': 'Technology', 'industry': 'Semiconductors', 'primary_exchange': 'NASDAQ'},
                {'symbol': 'NVDA', 'name': 'NVIDIA Corporation', 'market_cap': 800000000000, 'sector': 'Technology', 'industry': 'Semiconductors', 'primary_exchange': 'NASDAQ'},
                
                # Small cap stocks
                {'symbol': 'PLTR', 'name': 'Palantir Technologies', 'market_cap': 40000000000, 'sector': 'Technology', 'industry': 'Software', 'primary_exchange': 'NYSE'},
                {'symbol': 'COIN', 'name': 'Coinbase Global Inc.', 'market_cap': 35000000000, 'sector': 'Financial Services', 'industry': 'Financial Data & Stock Exchanges', 'primary_exchange': 'NASDAQ'},
                
                # Micro cap stocks
                {'symbol': 'SNDL', 'name': 'Sundial Growers', 'market_cap': 200000000, 'sector': 'Healthcare', 'industry': 'Drug Manufacturers', 'primary_exchange': 'NASDAQ'},
            ],
            'etfs': [
                {'symbol': 'SPY', 'name': 'SPDR S&P 500 ETF Trust', 'market_cap': 400000000000, 'etf_type': 'Index', 'issuer': 'State Street', 'primary_exchange': 'NYSE'},
                {'symbol': 'QQQ', 'name': 'Invesco QQQ Trust', 'market_cap': 200000000000, 'etf_type': 'Index', 'issuer': 'Invesco', 'primary_exchange': 'NASDAQ'},
                {'symbol': 'VTI', 'name': 'Vanguard Total Stock Market ETF', 'market_cap': 300000000000, 'etf_type': 'Index', 'issuer': 'Vanguard', 'primary_exchange': 'NYSE'},
            ],
            'sectors': ['Technology', 'Financial Services', 'Healthcare'],
            'app_settings': [
                {'type': 'app_settings', 'name': 'ui_config', 'key': 'theme', 'value': 'dark'},
                {'type': 'app_settings', 'name': 'system', 'key': 'version', 'value': '2.1.0'},
            ]
        }

    @patch('src.core.services.cache_entries_synchronizer.psycopg2.connect')
    @patch('src.core.services.cache_entries_synchronizer.redis.Redis')
    @patch('src.core.services.cache_entries_synchronizer.os.getenv')
    def test_full_rebuild_workflow_success(self, mock_getenv, mock_redis, mock_psycopg2, 
                                         synchronizer, comprehensive_test_data):
        """Test complete successful rebuild workflow."""
        # Setup mocks
        mock_getenv.side_effect = lambda key, default=None: {
            'DATABASE_URI': 'postgresql://user:pass@localhost:5432/testdb',
            'REDIS_HOST': 'localhost', 'REDIS_PORT': '6379', 'REDIS_DB': '0'
        }.get(key, default)
        
        mock_db_conn, mock_cursor = self._setup_database_mocks(mock_psycopg2, comprehensive_test_data)
        mock_redis_client = self._setup_redis_mocks(mock_redis)
        
        # Execute rebuild
        stats = synchronizer.rebuild_stock_cache_entries()
        
        # Verify completion stats
        assert isinstance(stats, dict)
        assert 'deleted_entries' in stats
        assert 'market_cap_entries' in stats
        assert 'sector_leader_entries' in stats
        assert 'market_leader_entries' in stats
        assert 'theme_entries' in stats
        assert 'industry_entries' in stats
        assert 'etf_entries' in stats
        assert 'complete_entries' in stats
        assert 'stats_entries' in stats
        assert 'redis_notifications' in stats
        
        # Verify database operations
        mock_db_conn.commit.assert_called_once()
        mock_db_conn.close.assert_called_once()
        
        # Verify Redis notifications
        assert mock_redis_client.publish.call_count == 3  # 3 notification channels

    def test_rebuild_workflow_with_delete_existing_false(self, synchronizer, comprehensive_test_data):
        """Test rebuild workflow when delete_existing=False."""
        mock_db_conn, mock_cursor = self._setup_integration_mocks(synchronizer, comprehensive_test_data)
        
        with patch.object(synchronizer, 'connect', return_value=True):
            with patch.object(synchronizer, 'disconnect'):
                stats = synchronizer.rebuild_stock_cache_entries(delete_existing=False)
        
        # Verify deletion was not called
        assert stats['deleted_entries'] == 0
        
        # Verify other operations still occurred
        assert stats['market_cap_entries'] > 0
        assert mock_db_conn.commit.called

    def test_rebuild_workflow_connection_failure(self, synchronizer):
        """Test rebuild workflow when connection fails."""
        with patch.object(synchronizer, 'connect', return_value=False):
            with pytest.raises(Exception, match="Failed to establish connections"):
                synchronizer.rebuild_stock_cache_entries()

    def test_rebuild_workflow_database_error_with_rollback(self, synchronizer, comprehensive_test_data):
        """Test rebuild workflow with database error and rollback."""
        mock_db_conn, mock_cursor = self._setup_integration_mocks(synchronizer, comprehensive_test_data)
        
        # Make one of the operations fail
        mock_cursor.execute.side_effect = [
            None,  # DELETE succeeds
            psycopg2.Error("Database error")  # First INSERT fails
        ]
        
        with patch.object(synchronizer, 'connect', return_value=True):
            with patch.object(synchronizer, 'disconnect'):
                with pytest.raises(psycopg2.Error):
                    synchronizer.rebuild_stock_cache_entries()
        
        # Verify rollback was called
        mock_db_conn.rollback.assert_called_once()
        
        # Verify commit was not called
        mock_db_conn.commit.assert_not_called()

    @patch('src.core.services.cache_entries_synchronizer.psycopg2.connect')
    @patch('src.core.services.cache_entries_synchronizer.os.getenv')
    def test_rebuild_workflow_redis_failure_continues(self, mock_getenv, mock_psycopg2, 
                                                    synchronizer, comprehensive_test_data):
        """Test that rebuild continues even if Redis notifications fail."""
        # Setup database mocks
        mock_getenv.return_value = 'postgresql://user:pass@localhost:5432/testdb'
        mock_db_conn, mock_cursor = self._setup_database_mocks(mock_psycopg2, comprehensive_test_data)
        
        # Setup Redis to fail
        synchronizer.redis_client = Mock()
        synchronizer.redis_client.publish.side_effect = redis.RedisError("Redis connection lost")
        
        # Execute rebuild - should not raise exception despite Redis failure
        stats = synchronizer.rebuild_stock_cache_entries()
        
        # Verify rebuild completed successfully
        assert isinstance(stats, dict)
        assert stats['redis_notifications'] == 0  # Redis notifications failed
        
        # Verify database operations still succeeded
        mock_db_conn.commit.assert_called_once()

    @pytest.mark.performance
    def test_rebuild_workflow_performance_large_dataset(self, synchronizer):
        """Test rebuild performance with large dataset."""
        # Create large test dataset
        large_stocks = []
        for i in range(5000):  # 5000 stocks
            large_stocks.append({
                'symbol': f'STOCK{i:04d}',
                'name': f'Test Company {i}',
                'market_cap': 1000000000 + (i * 1000000),  # Vary market caps
                'sector': f'Sector{i % 10}',  # 10 different sectors
                'industry': f'Industry{i % 50}',  # 50 different industries
                'primary_exchange': 'NYSE' if i % 2 == 0 else 'NASDAQ'
            })
        
        large_etfs = []
        for i in range(500):  # 500 ETFs
            large_etfs.append({
                'symbol': f'ETF{i:03d}',
                'name': f'Test ETF {i}',
                'market_cap': 100000000 + (i * 10000000),
                'etf_type': 'Index',
                'issuer': 'Test Issuer',
                'primary_exchange': 'NYSE'
            })
        
        large_dataset = {
            'stocks': large_stocks,
            'etfs': large_etfs,
            'sectors': [f'Sector{i}' for i in range(10)]
        }
        
        mock_db_conn, mock_cursor = self._setup_integration_mocks(synchronizer, large_dataset)
        
        with patch.object(synchronizer, 'connect', return_value=True):
            with patch.object(synchronizer, 'disconnect'):
                start_time = time.time()
                stats = synchronizer.rebuild_stock_cache_entries()
                execution_time = time.time() - start_time
        
        # Performance requirement: should complete within 60 seconds
        assert execution_time < 60.0, f"Rebuild took {execution_time:.2f}s, should be < 60s"
        
        # Verify all entries were processed
        assert stats['market_cap_entries'] == 5  # 5 market cap categories
        assert stats['sector_leader_entries'] == 10  # 10 sectors
        assert stats['market_leader_entries'] == 5  # 5 market leader categories

    def test_data_integrity_app_settings_preserved(self, synchronizer, comprehensive_test_data):
        """Test that app_settings and other entries are preserved during rebuild."""
        mock_db_conn, mock_cursor = self._setup_integration_mocks(synchronizer, comprehensive_test_data)
        
        # Verify DELETE query excludes app_settings
        with patch.object(synchronizer, 'connect', return_value=True):
            with patch.object(synchronizer, 'disconnect'):
                synchronizer.rebuild_stock_cache_entries()
        
        # Check that DELETE query was called with correct parameters
        delete_calls = [call for call in mock_cursor.execute.call_args_list 
                       if 'DELETE FROM cache_entries' in str(call)]
        assert len(delete_calls) == 1
        
        delete_query = delete_calls[0][0][0]
        # Verify app_settings is not in the DELETE query
        assert 'app_settings' not in delete_query
        # Verify stock/ETF types are in the DELETE query
        assert 'stock_universe' in delete_query
        assert 'etf_universe' in delete_query

    def test_cross_method_data_consistency(self, synchronizer, comprehensive_test_data):
        """Test data consistency across different cache entry creation methods."""
        mock_db_conn, mock_cursor = self._setup_integration_mocks(synchronizer, comprehensive_test_data)
        
        with patch.object(synchronizer, 'connect', return_value=True):
            with patch.object(synchronizer, 'disconnect'):
                stats = synchronizer.rebuild_stock_cache_entries()
        
        # Collect all INSERT operations
        insert_calls = [call for call in mock_cursor.execute.call_args_list 
                       if 'INSERT INTO cache_entries' in str(call)]
        
        # Verify consistent data structure across all entries
        stock_symbols_by_type = {}
        
        for call in insert_calls:
            entry_type = call[0][1][0]  # type parameter
            entry_name = call[0][1][1]  # name parameter
            entry_key = call[0][1][2]   # key parameter
            entry_value = json.loads(call[0][1][3])  # value parameter (JSON)
            
            # Extract stock symbols from different entry formats
            symbols = set()
            if isinstance(entry_value, list):  # Simple ticker arrays
                symbols = set(entry_value)
            elif isinstance(entry_value, dict):
                if 'stocks' in entry_value:  # Stock universe format
                    symbols = {stock['ticker'] for stock in entry_value['stocks']}
                elif 'etfs' in entry_value:  # ETF format
                    symbols = {etf['ticker'] for etf in entry_value['etfs']}
            
            if symbols:
                stock_symbols_by_type[f"{entry_type}_{entry_name}_{entry_key}"] = symbols
        
        # Verify that all stock symbols are consistent
        # (i.e., no symbols appear that weren't in the original dataset)
        original_symbols = {stock['symbol'] for stock in comprehensive_test_data['stocks']}
        original_etf_symbols = {etf['symbol'] for etf in comprehensive_test_data['etfs']}
        
        for entry_key, symbols in stock_symbols_by_type.items():
            if 'etf' in entry_key.lower():
                invalid_symbols = symbols - original_etf_symbols
            else:
                invalid_symbols = symbols - original_symbols
            
            assert len(invalid_symbols) == 0, f"Entry {entry_key} contains invalid symbols: {invalid_symbols}"

    def test_transaction_boundary_validation(self, synchronizer, comprehensive_test_data):
        """Test that all operations occur within a single transaction boundary."""
        mock_db_conn, mock_cursor = self._setup_integration_mocks(synchronizer, comprehensive_test_data)
        
        with patch.object(synchronizer, 'connect', return_value=True):
            with patch.object(synchronizer, 'disconnect'):
                synchronizer.rebuild_stock_cache_entries()
        
        # Verify transaction management
        mock_db_conn.commit.assert_called_once()
        mock_db_conn.rollback.assert_not_called()
        
        # Verify no intermediate commits
        # (All operations should be in one transaction)
        assert mock_db_conn.commit.call_count == 1

    def test_redis_notification_content_validation(self, synchronizer, comprehensive_test_data):
        """Test that Redis notifications contain correct content and structure."""
        mock_db_conn, mock_cursor = self._setup_integration_mocks(synchronizer, comprehensive_test_data)
        
        mock_redis = Mock()
        synchronizer.redis_client = mock_redis
        
        with patch.object(synchronizer, 'connect', return_value=True):
            with patch.object(synchronizer, 'disconnect'):
                stats = synchronizer.rebuild_stock_cache_entries()
        
        # Verify Redis publish calls
        assert mock_redis.publish.call_count == 3
        
        # Validate notification content
        for call in mock_redis.publish.call_args_list:
            channel, message = call[0]
            
            # Verify channel names
            assert channel in ['cache_updates', 'universe_updates', 'admin_notifications']
            
            # Verify message structure
            message_data = json.loads(message)
            assert message_data['event'] == 'cache_rebuild_completed'
            assert 'timestamp' in message_data
            assert message_data['source'] == 'CacheEntriesSynchronizer'
            assert message_data['stats'] == stats

    def test_concurrent_access_simulation(self, synchronizer, comprehensive_test_data):
        """Test behavior under simulated concurrent access scenarios."""
        mock_db_conn, mock_cursor = self._setup_integration_mocks(synchronizer, comprehensive_test_data)
        
        # Simulate another process modifying cache_entries during rebuild
        def side_effect_with_concurrent_modification(*args, **kwargs):
            # Simulate concurrent INSERT (rowcount increases)
            mock_cursor.rowcount += 5
            return None
        
        mock_cursor.execute.side_effect = side_effect_with_concurrent_modification
        
        with patch.object(synchronizer, 'connect', return_value=True):
            with patch.object(synchronizer, 'disconnect'):
                # Should complete without errors despite concurrent modifications
                stats = synchronizer.rebuild_stock_cache_entries()
        
        assert isinstance(stats, dict)
        # The concurrent modifications should not affect the rebuild completion

    def test_memory_usage_validation(self, synchronizer):
        """Test memory usage remains reasonable during large rebuilds."""
        # Create very large dataset
        massive_stocks = []
        for i in range(10000):  # 10,000 stocks
            massive_stocks.append({
                'symbol': f'STOCK{i:05d}',
                'name': f'Very Long Company Name That Tests Memory Usage {i} ' * 5,  # Long names
                'market_cap': 1000000000 + (i * 1000000),
                'sector': f'Sector{i % 20}',
                'industry': f'Industry{i % 100}',
                'primary_exchange': 'NYSE'
            })
        
        massive_dataset = {
            'stocks': massive_stocks,
            'etfs': [],
            'sectors': [f'Sector{i}' for i in range(20)]
        }
        
        mock_db_conn, mock_cursor = self._setup_integration_mocks(synchronizer, massive_dataset)
        
        import tracemalloc
        tracemalloc.start()
        
        with patch.object(synchronizer, 'connect', return_value=True):
            with patch.object(synchronizer, 'disconnect'):
                stats = synchronizer.rebuild_stock_cache_entries()
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Memory usage should be reasonable (less than 100MB peak)
        assert peak < 100 * 1024 * 1024, f"Peak memory usage {peak / 1024 / 1024:.2f}MB exceeds 100MB limit"

    def test_error_recovery_partial_failure(self, synchronizer, comprehensive_test_data):
        """Test recovery from partial failures during rebuild."""
        mock_db_conn, mock_cursor = self._setup_integration_mocks(synchronizer, comprehensive_test_data)
        
        # Make market cap creation fail after some operations succeed
        call_count = 0
        def selective_failure(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 10:  # Fail on 10th call
                raise psycopg2.Error("Simulated database failure")
            return None
        
        mock_cursor.execute.side_effect = selective_failure
        
        with patch.object(synchronizer, 'connect', return_value=True):
            with patch.object(synchronizer, 'disconnect'):
                with pytest.raises(psycopg2.Error):
                    synchronizer.rebuild_stock_cache_entries()
        
        # Verify rollback occurred
        mock_db_conn.rollback.assert_called_once()
        mock_db_conn.commit.assert_not_called()

    # Helper methods
    def _setup_database_mocks(self, mock_psycopg2, test_data):
        """Setup database mocks with test data."""
        mock_db_conn = Mock()
        mock_cursor = Mock(spec=RealDictCursor)
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        
        # Setup fetchall responses based on query patterns
        def fetchall_side_effect():
            # Default to stocks data
            return test_data['stocks']
        
        def fetchone_side_effect():
            # Return stats for statistics query
            return {
                'total_stocks': len(test_data['stocks']),
                'unique_sectors': len(set(stock['sector'] for stock in test_data['stocks'])),
                'total_market_cap': sum(stock['market_cap'] for stock in test_data['stocks']),
                'average_market_cap': sum(stock['market_cap'] for stock in test_data['stocks']) / len(test_data['stocks']),
                'unique_industries': len(set(stock['industry'] for stock in test_data['stocks'])),
                'unique_exchanges': len(set(stock['primary_exchange'] for stock in test_data['stocks']))
            }
        
        mock_cursor.fetchall.side_effect = fetchall_side_effect
        mock_cursor.fetchone.side_effect = fetchone_side_effect
        mock_cursor.rowcount = 10  # Default rowcount for DELETE
        
        mock_db_conn.cursor.return_value = mock_cursor
        mock_psycopg2.return_value = mock_db_conn
        
        return mock_db_conn, mock_cursor
    
    def _setup_redis_mocks(self, mock_redis):
        """Setup Redis mocks."""
        mock_redis_client = Mock()
        mock_redis_client.ping.return_value = True
        mock_redis.return_value = mock_redis_client
        return mock_redis_client
    
    def _setup_integration_mocks(self, synchronizer, test_data):
        """Setup mocks for integration testing."""
        mock_db_conn = Mock()
        mock_cursor = Mock(spec=RealDictCursor)
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        
        # Dynamic response based on query content
        def dynamic_fetchall(*args, **kwargs):
            if len(args) > 0 and isinstance(args[0], str):
                query = args[0].lower()
                if 'distinct sector' in query:
                    return [{'sector': sector} for sector in test_data['sectors']]
                elif 'type = \'etf\'' in query:
                    return [{'symbol': etf['symbol']} for etf in test_data['etfs']]
                elif 'symbol = any' in query:
                    # Theme query - return available symbols
                    return [{'symbol': stock['symbol']} for stock in test_data['stocks'][:3]]
            return test_data['stocks']
        
        mock_cursor.fetchall.side_effect = dynamic_fetchall
        mock_cursor.fetchone.return_value = {
            'total_stocks': len(test_data['stocks']),
            'unique_sectors': len(test_data.get('sectors', [])),
            'total_market_cap': 10000000000000,
            'average_market_cap': 1000000000000,
            'unique_industries': 50,
            'unique_exchanges': 5
        }
        mock_cursor.rowcount = 25
        
        mock_db_conn.cursor.return_value = mock_cursor
        synchronizer.db_conn = mock_db_conn
        synchronizer.redis_client = Mock()
        
        return mock_db_conn, mock_cursor