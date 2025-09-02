"""
Unit Tests for CacheEntriesSynchronizer

Tests individual methods and functionality of the cache synchronizer service.
Focuses on method-level validation, data transformation, and business logic.

Test Coverage:
- Individual method testing for each cache entry creation method
- Database connection management
- Data transformation and formatting validation
- Market cap categorization logic
- Theme and industry group handling
- Error conditions and edge cases
"""

import pytest
import json
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch, call
from typing import Dict, List, Any
import psycopg2
from psycopg2.extras import RealDictCursor

# Import the class under test
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'src'))

from src.core.services.cache_entries_synchronizer import CacheEntriesSynchronizer


class TestCacheEntriesSynchronizerUnit:
    """Unit tests for CacheEntriesSynchronizer class."""

    @pytest.fixture
    def synchronizer(self):
        """Create synchronizer instance for testing."""
        with patch('src.core.services.cache_entries_synchronizer.load_dotenv'):
            sync = CacheEntriesSynchronizer()
            sync.db_conn = Mock()
            sync.redis_client = Mock()
            return sync

    @pytest.fixture
    def mock_cursor(self):
        """Create mock database cursor."""
        cursor = Mock(spec=RealDictCursor)
        cursor.__enter__ = Mock(return_value=cursor)
        cursor.__exit__ = Mock(return_value=None)
        cursor.rowcount = 0
        return cursor

    @pytest.fixture
    def sample_stock_data(self):
        """Sample stock data for testing."""
        return [
            {
                'symbol': 'AAPL',
                'name': 'Apple Inc.',
                'market_cap': 3000000000000,  # $3T
                'sector': 'Technology',
                'industry': 'Consumer Electronics',
                'primary_exchange': 'NASDAQ'
            },
            {
                'symbol': 'GOOGL',
                'name': 'Alphabet Inc.',
                'market_cap': 2000000000000,  # $2T
                'sector': 'Technology',
                'industry': 'Internet Content & Information',
                'primary_exchange': 'NASDAQ'
            },
            {
                'symbol': 'MSFT',
                'name': 'Microsoft Corporation',
                'market_cap': 2500000000000,  # $2.5T
                'sector': 'Technology',
                'industry': 'Software',
                'primary_exchange': 'NASDAQ'
            }
        ]

    @pytest.fixture
    def sample_etf_data(self):
        """Sample ETF data for testing."""
        return [
            {
                'symbol': 'SPY',
                'name': 'SPDR S&P 500 ETF Trust',
                'market_cap': 400000000000,
                'etf_type': 'Index',
                'issuer': 'State Street',
                'primary_exchange': 'NYSE'
            },
            {
                'symbol': 'QQQ',
                'name': 'Invesco QQQ Trust',
                'market_cap': 200000000000,
                'etf_type': 'Index',
                'issuer': 'Invesco',
                'primary_exchange': 'NASDAQ'
            }
        ]

    def test_initialization(self):
        """Test synchronizer initialization."""
        with patch('src.core.services.cache_entries_synchronizer.load_dotenv'):
            sync = CacheEntriesSynchronizer()
            
        # Check initial state
        assert sync.db_conn is None
        assert sync.redis_client is None
        assert isinstance(sync.sync_timestamp, datetime)
        assert isinstance(sync.market_cap_thresholds, dict)
        assert isinstance(sync.theme_definitions, dict)
        assert isinstance(sync.industry_groups, dict)

    def test_market_cap_thresholds(self):
        """Test market cap threshold definitions."""
        with patch('src.core.services.cache_entries_synchronizer.load_dotenv'):
            sync = CacheEntriesSynchronizer()
        
        expected_thresholds = {
            'mega_cap': 200_000_000_000,
            'large_cap': 10_000_000_000,
            'mid_cap': 2_000_000_000,
            'small_cap': 300_000_000,
            'micro_cap': 0
        }
        
        assert sync.market_cap_thresholds == expected_thresholds

    def test_theme_definitions(self):
        """Test theme definitions structure."""
        with patch('src.core.services.cache_entries_synchronizer.load_dotenv'):
            sync = CacheEntriesSynchronizer()
        
        # Verify key themes exist
        assert 'ai' in sync.theme_definitions
        assert 'biotech' in sync.theme_definitions
        assert 'cloud' in sync.theme_definitions
        assert 'crypto' in sync.theme_definitions
        
        # Verify AI theme has expected stocks
        ai_stocks = sync.theme_definitions['ai']
        assert 'NVDA' in ai_stocks
        assert 'GOOGL' in ai_stocks
        assert 'MSFT' in ai_stocks

    @patch('src.core.services.cache_entries_synchronizer.psycopg2.connect')
    @patch('src.core.services.cache_entries_synchronizer.redis.Redis')
    @patch('src.core.services.cache_entries_synchronizer.os.getenv')
    def test_connect_success(self, mock_getenv, mock_redis, mock_psycopg2, synchronizer):
        """Test successful database and Redis connections."""
        # Mock environment variables
        mock_getenv.side_effect = lambda key, default=None: {
            'DATABASE_URI': 'postgresql://user:pass@localhost:5432/testdb',
            'REDIS_HOST': 'localhost',
            'REDIS_PORT': '6379',
            'REDIS_DB': '0'
        }.get(key, default)
        
        # Mock successful connections
        mock_db_conn = Mock()
        mock_psycopg2.return_value = mock_db_conn
        
        mock_redis_client = Mock()
        mock_redis_client.ping.return_value = True
        mock_redis.return_value = mock_redis_client
        
        # Reset synchronizer connections
        synchronizer.db_conn = None
        synchronizer.redis_client = None
        
        result = synchronizer.connect()
        
        assert result is True
        assert synchronizer.db_conn == mock_db_conn
        assert synchronizer.redis_client == mock_redis_client

    @patch('src.core.services.cache_entries_synchronizer.os.getenv')
    def test_connect_missing_database_uri(self, mock_getenv, synchronizer):
        """Test connection failure when DATABASE_URI is missing."""
        mock_getenv.return_value = None
        
        synchronizer.db_conn = None
        synchronizer.redis_client = None
        
        result = synchronizer.connect()
        
        assert result is False
        assert synchronizer.db_conn is None

    @patch('src.core.services.cache_entries_synchronizer.psycopg2.connect')
    @patch('src.core.services.cache_entries_synchronizer.os.getenv')
    def test_connect_database_failure(self, mock_getenv, mock_psycopg2, synchronizer):
        """Test connection failure when database connection fails."""
        mock_getenv.return_value = 'postgresql://user:pass@localhost:5432/testdb'
        mock_psycopg2.side_effect = psycopg2.Error("Connection failed")
        
        synchronizer.db_conn = None
        synchronizer.redis_client = None
        
        result = synchronizer.connect()
        
        assert result is False
        assert synchronizer.db_conn is None

    def test_disconnect(self, synchronizer):
        """Test disconnection cleans up resources."""
        mock_db_conn = Mock()
        mock_redis_client = Mock()
        
        synchronizer.db_conn = mock_db_conn
        synchronizer.redis_client = mock_redis_client
        
        synchronizer.disconnect()
        
        mock_db_conn.close.assert_called_once()
        mock_redis_client.close.assert_called_once()

    def test_delete_stock_etf_entries(self, synchronizer, mock_cursor):
        """Test deletion of existing stock/ETF entries preserving app_settings."""
        mock_cursor.rowcount = 50
        synchronizer.db_conn.cursor.return_value = mock_cursor
        
        result = synchronizer._delete_stock_etf_entries()
        
        assert result == 50
        mock_cursor.execute.assert_called_once()
        
        # Verify correct SQL is used
        call_args = mock_cursor.execute.call_args[0]
        assert "DELETE FROM cache_entries" in call_args[0]
        assert "stock_universe" in call_args[0]
        assert "etf_universe" in call_args[0]
        assert "themes" in call_args[0]
        assert "priority_stocks" in call_args[0]
        assert "stock_stats" in call_args[0]
        # Verify app_settings is NOT deleted
        assert "app_settings" not in call_args[0]

    def test_create_market_cap_entries_mega_cap(self, synchronizer, mock_cursor, sample_stock_data):
        """Test creation of mega cap entries."""
        # Filter to mega cap stocks only (>= $200B)
        mega_cap_stocks = [stock for stock in sample_stock_data if stock['market_cap'] >= 200_000_000_000]
        
        mock_cursor.fetchall.return_value = mega_cap_stocks
        synchronizer.db_conn.cursor.return_value = mock_cursor
        
        result = synchronizer._create_market_cap_entries()
        
        assert result == 5  # One entry per market cap category
        
        # Verify database calls
        assert mock_cursor.execute.call_count >= 5  # 5 categories
        
        # Check that mega cap query includes correct WHERE clause
        execute_calls = mock_cursor.execute.call_args_list
        mega_cap_call = [call for call in execute_calls if 'market_cap >= 200000000000' in str(call)]
        assert len(mega_cap_call) > 0

    def test_create_sector_leader_entries(self, synchronizer, mock_cursor, sample_stock_data):
        """Test creation of sector leader entries."""
        # Mock distinct sectors
        mock_cursor.fetchall.side_effect = [
            [{'sector': 'Technology'}],  # First call for distinct sectors
            sample_stock_data  # Second call for stocks in Technology sector
        ]
        synchronizer.db_conn.cursor.return_value = mock_cursor
        
        result = synchronizer._create_sector_leader_entries()
        
        assert result == 1  # One sector processed
        
        # Verify two database calls: one for sectors, one for stocks
        assert mock_cursor.execute.call_count == 2
        
        # Check sector key formatting
        execute_calls = mock_cursor.execute.call_args_list
        insert_call = execute_calls[1]
        assert 'top_10_technology' in str(insert_call)

    def test_create_market_leader_entries(self, synchronizer, mock_cursor, sample_stock_data):
        """Test creation of market leader entries."""
        mock_cursor.fetchall.return_value = sample_stock_data
        synchronizer.db_conn.cursor.return_value = mock_cursor
        
        result = synchronizer._create_market_leader_entries()
        
        assert result == 5  # 5 leader categories: 10, 50, 100, 250, 500
        
        # Verify correct number of database calls
        expected_calls = 10  # 5 SELECT + 5 INSERT
        assert mock_cursor.execute.call_count == expected_calls
        
        # Check that top_10_stocks key is used for count=10
        execute_calls = mock_cursor.execute.call_args_list
        top_10_call = [call for call in execute_calls if 'top_10_stocks' in str(call)]
        assert len(top_10_call) > 0

    def test_create_theme_entries(self, synchronizer, mock_cursor):
        """Test creation of theme entries."""
        # Mock available tickers for AI theme
        mock_cursor.fetchall.return_value = [
            {'symbol': 'NVDA'},
            {'symbol': 'GOOGL'},
            {'symbol': 'MSFT'}
        ]
        synchronizer.db_conn.cursor.return_value = mock_cursor
        
        result = synchronizer._create_theme_entries()
        
        # Should create 2 entries per theme (themes + stock_universe)
        # Times number of themes with available stocks
        expected_entries = len(synchronizer.theme_definitions) * 2
        assert result <= expected_entries  # May be less if some themes have no available stocks
        
        # Verify database calls
        assert mock_cursor.execute.call_count >= len(synchronizer.theme_definitions)

    def test_create_industry_entries(self, synchronizer, mock_cursor, sample_stock_data):
        """Test creation of industry group entries."""
        # Filter stocks to match an industry group
        software_stocks = [stock for stock in sample_stock_data if stock['industry'] == 'Software']
        mock_cursor.fetchall.return_value = software_stocks
        synchronizer.db_conn.cursor.return_value = mock_cursor
        
        result = synchronizer._create_industry_entries()
        
        assert result <= len(synchronizer.industry_groups)  # May be less if no stocks found
        
        # Verify database structure
        if result > 0:
            assert mock_cursor.execute.call_count >= len(synchronizer.industry_groups)

    def test_create_etf_entries(self, synchronizer, mock_cursor, sample_etf_data):
        """Test creation of ETF universe entries."""
        mock_cursor.fetchall.return_value = [{'symbol': etf['symbol']} for etf in sample_etf_data]
        synchronizer.db_conn.cursor.return_value = mock_cursor
        
        result = synchronizer._create_etf_entries()
        
        # Should create one entry per ETF category
        expected_categories = 8  # Based on etf_categories in the method
        assert result == expected_categories
        
        # Verify database calls (one per category)
        assert mock_cursor.execute.call_count == expected_categories * 2  # SELECT + INSERT per category

    def test_create_complete_stocks_entries(self, synchronizer, mock_cursor, sample_stock_data):
        """Test creation of complete stock universe entries."""
        mock_cursor.fetchall.return_value = sample_stock_data
        
        result = synchronizer._create_complete_stocks_entries(mock_cursor)
        
        assert result == 2  # top_1000 and all_stocks entries
        
        # Verify both entries are created
        insert_calls = [call for call in mock_cursor.execute.call_args_list if 'INSERT INTO cache_entries' in str(call)]
        assert len(insert_calls) == 2
        
        # Check for correct keys
        calls_str = str(insert_calls)
        assert 'top_1000' in calls_str
        assert 'all_stocks' in calls_str

    def test_create_complete_etf_entries(self, synchronizer, mock_cursor, sample_etf_data):
        """Test creation of complete ETF universe entries."""
        mock_cursor.fetchall.return_value = sample_etf_data
        
        result = synchronizer._create_complete_etf_entries(mock_cursor)
        
        assert result == 2  # top_100 and all_etfs entries
        
        # Verify both entries are created
        insert_calls = [call for call in mock_cursor.execute.call_args_list if 'INSERT INTO cache_entries' in str(call)]
        assert len(insert_calls) == 2

    def test_create_stats_entries(self, synchronizer, mock_cursor):
        """Test creation of statistics summary entries."""
        # Mock statistics data
        stats_data = {
            'total_stocks': 5000,
            'unique_sectors': 11,
            'total_market_cap': 45000000000000,
            'average_market_cap': 9000000000,
            'unique_industries': 150,
            'unique_exchanges': 15
        }
        mock_cursor.fetchone.return_value = stats_data
        synchronizer.db_conn.cursor.return_value = mock_cursor
        
        result = synchronizer._create_stats_entries()
        
        assert result == 1
        
        # Verify database call
        mock_cursor.execute.assert_called()
        
        # Check that INSERT includes the stats
        insert_call = [call for call in mock_cursor.execute.call_args_list if 'INSERT INTO cache_entries' in str(call)]
        assert len(insert_call) == 1

    def test_publish_rebuild_notifications_success(self, synchronizer):
        """Test successful Redis notifications publishing."""
        mock_redis = Mock()
        synchronizer.redis_client = mock_redis
        
        stats = {'market_cap_entries': 5, 'theme_entries': 24}
        
        result = synchronizer._publish_rebuild_notifications(stats)
        
        assert result == 3  # 3 channels: cache_updates, universe_updates, admin_notifications
        
        # Verify Redis publish calls
        assert mock_redis.publish.call_count == 3
        
        # Verify notification content
        publish_calls = mock_redis.publish.call_args_list
        for call in publish_calls:
            channel, message = call[0]
            message_data = json.loads(message)
            assert message_data['event'] == 'cache_rebuild_completed'
            assert message_data['stats'] == stats
            assert 'timestamp' in message_data

    def test_publish_rebuild_notifications_no_redis(self, synchronizer):
        """Test notifications when Redis is not available."""
        synchronizer.redis_client = None
        
        stats = {'market_cap_entries': 5}
        result = synchronizer._publish_rebuild_notifications(stats)
        
        assert result == 0

    def test_publish_rebuild_notifications_redis_error(self, synchronizer):
        """Test notifications when Redis publish fails."""
        mock_redis = Mock()
        mock_redis.publish.side_effect = Exception("Redis connection lost")
        synchronizer.redis_client = mock_redis
        
        stats = {'market_cap_entries': 5}
        result = synchronizer._publish_rebuild_notifications(stats)
        
        assert result == 0  # Should handle error gracefully

    def test_data_structure_validation_market_cap(self, synchronizer, mock_cursor, sample_stock_data):
        """Test that market cap entries have correct data structure."""
        mock_cursor.fetchall.return_value = sample_stock_data
        synchronizer.db_conn.cursor.return_value = mock_cursor
        
        synchronizer._create_market_cap_entries()
        
        # Get the INSERT call with JSON data
        insert_calls = [call for call in mock_cursor.execute.call_args_list if 'INSERT INTO cache_entries' in str(call)]
        
        for call in insert_calls:
            json_data = json.loads(call[0][1][3])  # Extract JSON value from parameters
            
            # Verify structure
            assert 'count' in json_data
            assert 'stocks' in json_data
            assert isinstance(json_data['stocks'], list)
            
            if json_data['stocks']:
                stock = json_data['stocks'][0]
                required_fields = ['name', 'rank', 'sector', 'ticker', 'exchange', 'industry', 'market_cap']
                for field in required_fields:
                    assert field in stock

    def test_error_handling_database_connection_lost(self, synchronizer, mock_cursor):
        """Test error handling when database connection is lost during operation."""
        mock_cursor.execute.side_effect = psycopg2.Error("Connection lost")
        synchronizer.db_conn.cursor.return_value = mock_cursor
        
        with pytest.raises(psycopg2.Error):
            synchronizer._delete_stock_etf_entries()

    def test_market_cap_categorization_logic(self):
        """Test market cap categorization logic for edge cases."""
        with patch('src.core.services.cache_entries_synchronizer.load_dotenv'):
            sync = CacheEntriesSynchronizer()
        
        thresholds = sync.market_cap_thresholds
        
        # Test boundary values
        test_cases = [
            (300_000_000_000, 'mega_cap'),    # Above mega cap threshold
            (200_000_000_000, 'mega_cap'),    # Exactly at mega cap threshold
            (199_999_999_999, 'large_cap'),   # Just below mega cap
            (10_000_000_000, 'large_cap'),    # Exactly at large cap threshold
            (9_999_999_999, 'mid_cap'),       # Just below large cap
            (299_999_999, 'micro_cap'),       # Just below small cap
        ]
        
        for market_cap, expected_category in test_cases:
            # Determine category based on thresholds
            if market_cap >= thresholds['mega_cap']:
                category = 'mega_cap'
            elif market_cap >= thresholds['large_cap']:
                category = 'large_cap'
            elif market_cap >= thresholds['mid_cap']:
                category = 'mid_cap'
            elif market_cap >= thresholds['small_cap']:
                category = 'small_cap'
            else:
                category = 'micro_cap'
            
            assert category == expected_category, f"Market cap {market_cap} should be {expected_category}, got {category}"

    @pytest.mark.performance
    def test_method_performance_benchmarks(self, synchronizer, mock_cursor, sample_stock_data):
        """Test that individual methods meet performance requirements."""
        import time
        
        # Mock large dataset
        large_dataset = sample_stock_data * 1000  # 3000 stocks
        mock_cursor.fetchall.return_value = large_dataset
        synchronizer.db_conn.cursor.return_value = mock_cursor
        
        # Test market cap creation performance
        start_time = time.time()
        synchronizer._create_market_cap_entries()
        market_cap_time = time.time() - start_time
        
        # Should complete in reasonable time even with large datasets
        assert market_cap_time < 10.0  # 10 seconds for 3000 stocks across 5 categories
        
        # Reset mock for next test
        mock_cursor.reset_mock()
        mock_cursor.fetchall.return_value = large_dataset
        
        # Test sector leader creation performance
        mock_cursor.fetchall.side_effect = [
            [{'sector': 'Technology'}] * 20,  # 20 distinct sectors
            large_dataset[:10]  # Top 10 per sector
        ] * 20  # Repeat for each sector call
        
        start_time = time.time()
        synchronizer._create_sector_leader_entries()
        sector_time = time.time() - start_time
        
        assert sector_time < 15.0  # 15 seconds for sector processing

    def test_json_serialization_safety(self, synchronizer, mock_cursor):
        """Test that JSON serialization handles edge cases safely."""
        # Test with None values and special characters
        problematic_data = [
            {
                'symbol': 'TEST',
                'name': 'Test Company "Quotes" & Ampersands',
                'market_cap': None,  # None value
                'sector': 'Technology & Services',  # Ampersand
                'industry': None,
                'primary_exchange': 'NYSE'
            }
        ]
        
        mock_cursor.fetchall.return_value = problematic_data
        synchronizer.db_conn.cursor.return_value = mock_cursor
        
        # Should not raise JSON serialization errors
        try:
            synchronizer._create_market_cap_entries()
        except (TypeError, ValueError) as e:
            pytest.fail(f"JSON serialization failed: {e}")
        
        # Verify INSERT was called (meaning JSON was serializable)
        insert_calls = [call for call in mock_cursor.execute.call_args_list if 'INSERT INTO cache_entries' in str(call)]
        assert len(insert_calls) > 0

    def test_theme_ticker_availability_filtering(self, synchronizer, mock_cursor):
        """Test that theme creation only includes available tickers."""
        # Mock that only some AI theme tickers are available
        available_tickers = [{'symbol': 'NVDA'}, {'symbol': 'MSFT'}]  # Only 2 of 8 AI stocks
        mock_cursor.fetchall.return_value = available_tickers
        synchronizer.db_conn.cursor.return_value = mock_cursor
        
        synchronizer._create_theme_entries()
        
        # Check that INSERT calls only include available tickers
        insert_calls = [call for call in mock_cursor.execute.call_args_list if 'INSERT INTO cache_entries' in str(call)]
        
        for call in insert_calls:
            if isinstance(call[0][1][3], str):  # JSON value parameter
                tickers = json.loads(call[0][1][3])
                # Should only contain available tickers
                assert set(tickers).issubset({'NVDA', 'MSFT'})