#!/usr/bin/env python3
"""
ETF Universe Manager Tests - Sprint 14 Phase 3

Comprehensive tests for the ETF Universe Management System:
- ETF universe expansion across 7 themes with 200+ symbols
- AUM and liquidity-based filtering validation
- Database function integration testing
- Redis pub-sub notification testing
- Performance benchmarks for <2 second query requirements

Test Organization:
- Unit tests: ETF data generation, filtering, metadata processing
- Integration tests: Database operations, Redis messaging
- Performance tests: Query performance, universe update speed
- Regression tests: Existing functionality preservation
"""

import pytest
import asyncio
import json
import os
import sys
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timedelta
import psycopg2
import psycopg2.extras
from decimal import Decimal
import redis.asyncio as redis

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../'))

from src.data.etf_universe_manager import ETFUniverseManager, ETFMetadata

class TestETFUniverseManagerRefactor:
    """Unit tests for ETF Universe Manager refactor functionality"""
    
    @pytest.fixture
    def etf_manager(self):
        """Create ETF Universe Manager instance for testing"""
        return ETFUniverseManager(
            database_uri='postgresql://test:test@localhost/test_db',
            polygon_api_key='test_key',
            redis_host='localhost'
        )
    
    @pytest.fixture
    def sample_etf_metadata(self):
        """Sample ETF metadata for testing"""
        return ETFMetadata(
            symbol='XLF',
            name='Financial Select Sector SPDR Fund',
            aum=40e9,
            expense_ratio=0.12,
            avg_volume=50e6,
            underlying_index='S&P 500 Financial Sector',
            sector_focus='financial',
            inception_date='1998-12-16',
            dividend_yield=1.8
        )
    
    def test_etf_manager_initialization(self, etf_manager):
        """Test ETF manager initialization with proper configuration"""
        assert etf_manager.database_uri is not None
        assert etf_manager.polygon_api_key == 'test_key'
        assert etf_manager.redis_host == 'localhost'
        assert etf_manager.min_aum_threshold == 1e9  # $1B
        assert etf_manager.min_volume_threshold == 5e6  # 5M
        assert etf_manager.max_expense_ratio == 0.75
        
        # Verify Redis channels configuration
        expected_channels = {
            'universe_updated': 'tickstock.universe.updated',
            'etf_correlation_update': 'tickstock.etf.correlation_update',
            'universe_validation': 'tickstock.universe.validation_complete'
        }
        assert etf_manager.channels == expected_channels
    
    def test_sector_etfs_generation(self, etf_manager):
        """Test sector ETF generation with proper filtering"""
        sector_etfs = etf_manager._get_sector_etfs()
        
        # Verify basic requirements
        assert len(sector_etfs) > 0
        assert len(sector_etfs) <= 10  # SPDR sector ETFs
        
        # Verify all ETFs meet filtering criteria
        for etf in sector_etfs:
            assert etf.aum >= etf_manager.min_aum_threshold
            assert etf.avg_volume >= etf_manager.min_volume_threshold
            assert etf.expense_ratio <= etf_manager.max_expense_ratio
            assert etf.symbol.startswith('XL')  # SPDR sector ETFs
    
    def test_growth_etfs_generation(self, etf_manager):
        """Test growth ETF generation with market cap filtering"""
        growth_etfs = etf_manager._get_growth_etfs()
        
        assert len(growth_etfs) > 0
        assert len(growth_etfs) <= 8
        
        # Verify growth characteristics
        for etf in growth_etfs:
            assert etf.aum >= etf_manager.min_aum_threshold
            assert etf.sector_focus in ['growth', 'broad_market', 'low_volatility']
    
    def test_value_etfs_generation(self, etf_manager):
        """Test value ETF generation with dividend focus"""
        value_etfs = etf_manager._get_value_etfs()
        
        assert len(value_etfs) > 0
        assert len(value_etfs) <= 8
        
        # Verify value characteristics
        for etf in value_etfs:
            assert etf.aum >= etf_manager.min_aum_threshold
            assert etf.dividend_yield >= 1.5  # Value/dividend requirement
    
    def test_international_etfs_generation(self, etf_manager):
        """Test international ETF generation with geographic diversity"""
        international_etfs = etf_manager._get_international_etfs()
        
        assert len(international_etfs) > 0
        assert len(international_etfs) <= 8
        
        # Verify international characteristics
        geographic_focuses = [etf.sector_focus for etf in international_etfs]
        expected_regions = ['developed_markets', 'emerging_markets', 'europe', 'asia_pacific']
        
        # At least 3 different geographic regions represented
        represented_regions = set(focus for focus in geographic_focuses if focus in expected_regions)
        assert len(represented_regions) >= 3
    
    def test_commodity_etfs_generation(self, etf_manager):
        """Test commodity ETF generation with lower AUM threshold"""
        commodity_etfs = etf_manager._get_commodity_etfs()
        
        assert len(commodity_etfs) > 0
        assert len(commodity_etfs) <= 8
        
        # Verify commodity characteristics (lower AUM threshold)
        for etf in commodity_etfs:
            assert etf.aum >= 200e6  # $200M minimum for commodities
            assert etf.sector_focus in ['precious_metals', 'energy', 'agriculture', 'broad_commodities', 'natural_resources']
    
    def test_technology_etfs_generation(self, etf_manager):
        """Test technology ETF generation with innovation focus"""
        technology_etfs = etf_manager._get_technology_etfs()
        
        assert len(technology_etfs) > 0
        assert len(technology_etfs) <= 8
        
        # Verify technology characteristics
        for etf in technology_etfs:
            assert etf.aum >= 2e9  # $2B minimum for tech ETFs
            assert etf.sector_focus in ['technology', 'semiconductors', 'innovation', 'cloud_computing', 'robotics_ai']
    
    def test_bond_etfs_generation(self, etf_manager):
        """Test bond ETF generation across duration spectrum"""
        bond_etfs = etf_manager._get_bond_etfs()
        
        assert len(bond_etfs) > 0
        assert len(bond_etfs) <= 8
        
        # Verify bond characteristics
        for etf in bond_etfs:
            assert etf.aum >= 4e9  # $4B minimum for bond ETFs
            assert etf.sector_focus in [
                'aggregate_bonds', 'municipal_bonds', 'corporate_bonds', 
                'high_yield', 'treasury_long', 'treasury_short', 'treasury_intermediate'
            ]
    
    @patch('psycopg2.connect')
    def test_database_connection_success(self, mock_connect, etf_manager):
        """Test successful database connection"""
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        
        conn = etf_manager.get_database_connection()
        
        assert conn == mock_conn
        mock_connect.assert_called_once_with(
            etf_manager.database_uri,
            cursor_factory=psycopg2.extras.RealDictCursor
        )
    
    @patch('psycopg2.connect')
    def test_database_connection_failure(self, mock_connect, etf_manager):
        """Test database connection failure handling"""
        mock_connect.side_effect = Exception("Connection failed")
        
        conn = etf_manager.get_database_connection()
        
        assert conn is None
    
    @pytest.mark.asyncio
    async def test_redis_connection_success(self, etf_manager):
        """Test successful Redis connection"""
        with patch('redis.asyncio.Redis') as mock_redis:
            mock_client = AsyncMock()
            mock_redis.return_value = mock_client
            mock_client.ping.return_value = True
            
            redis_client = await etf_manager.connect_redis()
            
            assert redis_client == mock_client
            mock_client.ping.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_redis_connection_failure(self, etf_manager):
        """Test Redis connection failure handling"""
        with patch('redis.asyncio.Redis') as mock_redis:
            mock_client = AsyncMock()
            mock_redis.return_value = mock_client
            mock_client.ping.side_effect = Exception("Connection failed")
            
            redis_client = await etf_manager.connect_redis()
            
            assert redis_client is None
    
    @patch('psycopg2.connect')
    def test_update_universe_in_db_success(self, mock_connect, etf_manager, sample_etf_metadata):
        """Test successful universe update in database"""
        # Setup mock database connection and cursor
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # Mock database function response
        mock_cursor.fetchone.return_value = [{
            'action': 'updated',
            'cache_key': 'etf_test',
            'symbols_count': 1,
            'timestamp': datetime.now()
        }]
        
        # Test universe update
        etfs = [sample_etf_metadata]
        result = etf_manager._update_universe_in_db('test', etfs)
        
        # Verify database operations
        mock_cursor.execute.assert_called()
        mock_conn.commit.assert_called_once()
        assert result is not None
        assert 'action' in result[0]
    
    @patch('psycopg2.connect')
    def test_update_universe_in_db_failure(self, mock_connect, etf_manager, sample_etf_metadata):
        """Test database update failure handling"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # Simulate database error
        mock_cursor.execute.side_effect = Exception("Database error")
        
        etfs = [sample_etf_metadata]
        result = etf_manager._update_universe_in_db('test', etfs)
        
        # Verify error handling
        mock_conn.rollback.assert_called_once()
        assert result == {'error': 'Database error'}
    
    def test_expand_etf_universes_comprehensive(self, etf_manager):
        """Test comprehensive ETF universe expansion"""
        with patch.object(etf_manager, '_update_universe_in_db') as mock_update:
            mock_update.return_value = {
                'action': 'updated', 
                'symbols_count': 10,
                'cache_key': 'etf_test'
            }
            
            results = etf_manager.expand_etf_universes()
            
            # Verify all themes processed
            assert results['themes_processed'] == 7
            assert results['total_symbols'] > 0
            assert results['success'] > 0
            
            # Verify specific themes
            expected_themes = ['sectors', 'growth', 'value', 'international', 'commodities', 'technology', 'bonds']
            for theme in expected_themes:
                assert theme in results['themes']


class TestETFUniverseManagerIntegration:
    """Integration tests for ETF Universe Manager database and Redis operations"""
    
    @pytest.fixture
    def etf_manager(self):
        """Create ETF Universe Manager for integration testing"""
        return ETFUniverseManager()
    
    @pytest.mark.integration
    @patch('psycopg2.connect')
    async def test_publish_universe_updates_integration(self, mock_connect, etf_manager):
        """Test Redis publishing integration with comprehensive results"""
        expansion_results = {
            'timestamp': datetime.now().isoformat(),
            'themes_processed': 7,
            'total_symbols': 50,
            'success': 7,
            'themes': {
                'sectors': {'action': 'updated', 'symbols_count': 10},
                'growth': {'action': 'updated', 'symbols_count': 8}
            }
        }
        
        with patch.object(etf_manager, 'connect_redis') as mock_redis:
            mock_client = AsyncMock()
            mock_redis.return_value = mock_client
            
            result = await etf_manager.publish_universe_updates(expansion_results)
            
            # Verify successful publishing
            assert result is True
            
            # Verify Redis publish calls
            assert mock_client.publish.call_count >= 2  # Overall + individual themes
            
            # Verify message content
            calls = mock_client.publish.call_args_list
            overall_call = calls[0]
            assert overall_call[0][0] == 'tickstock.universe.updated'
            
            message = json.loads(overall_call[0][1])
            assert message['event_type'] == 'universe_expansion_complete'
            assert message['themes_processed'] == 7
            assert message['total_symbols'] == 50
    
    @pytest.mark.integration
    @patch('psycopg2.connect')
    async def test_validate_universe_symbols_integration(self, mock_connect, etf_manager):
        """Test universe symbol validation against symbols table"""
        # Mock database connection and data
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # Mock validation data
        mock_validation_data = [
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
                'exists_in_symbols': False,
                'symbol_type': 'UNKNOWN',
                'active_status': False
            }
        ]
        
        mock_cursor.fetchall.return_value = mock_validation_data
        
        result = await etf_manager.validate_universe_symbols()
        
        # Verify validation results
        assert 'validation_summary' in result
        assert 'missing_symbols' in result
        assert result['total_missing'] == 1
        
        # Verify specific universe validation
        etf_sectors_summary = result['validation_summary']['etf_sectors']
        assert etf_sectors_summary['total_symbols'] == 2
        assert etf_sectors_summary['found_symbols'] == 1
        assert etf_sectors_summary['found_percentage'] == 50.0
    
    @pytest.mark.integration
    async def test_end_to_end_universe_expansion(self, etf_manager):
        """Test end-to-end universe expansion with all components"""
        with patch.object(etf_manager, 'get_database_connection') as mock_db, \
             patch.object(etf_manager, 'connect_redis') as mock_redis:
            
            # Setup database mock
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_conn.cursor.return_value = mock_cursor
            mock_db.return_value = mock_conn
            
            # Mock successful database updates
            mock_cursor.fetchone.return_value = [{
                'action': 'updated',
                'cache_key': 'etf_test',
                'symbols_count': 10
            }]
            
            # Setup Redis mock
            mock_redis_client = AsyncMock()
            mock_redis.return_value = mock_redis_client
            
            # Execute expansion
            expansion_results = etf_manager.expand_etf_universes()
            await etf_manager.publish_universe_updates(expansion_results)
            
            # Verify comprehensive processing
            assert expansion_results['themes_processed'] == 7
            assert expansion_results['success'] > 0
            
            # Verify database was called for each theme
            assert mock_cursor.execute.call_count >= 7
            
            # Verify Redis publishing
            assert mock_redis_client.publish.call_count >= 7


class TestETFUniverseManagerPerformance:
    """Performance tests for ETF Universe Manager operations"""
    
    @pytest.fixture
    def etf_manager(self):
        """Create ETF manager for performance testing"""
        return ETFUniverseManager()
    
    @pytest.mark.performance
    def test_etf_generation_performance(self, etf_manager):
        """Test ETF data generation performance meets requirements"""
        import time
        
        start_time = time.time()
        
        # Generate all ETF themes
        sectors = etf_manager._get_sector_etfs()
        growth = etf_manager._get_growth_etfs()
        value = etf_manager._get_value_etfs()
        international = etf_manager._get_international_etfs()
        commodities = etf_manager._get_commodity_etfs()
        technology = etf_manager._get_technology_etfs()
        bonds = etf_manager._get_bond_etfs()
        
        generation_time = time.time() - start_time
        
        # Verify performance requirement: <100ms for ETF generation
        assert generation_time < 0.1, f"ETF generation took {generation_time:.3f}s, expected <0.1s"
        
        # Verify comprehensive coverage
        total_etfs = len(sectors) + len(growth) + len(value) + len(international) + len(commodities) + len(technology) + len(bonds)
        assert total_etfs >= 40, f"Expected at least 40 ETFs, got {total_etfs}"
    
    @pytest.mark.performance
    @patch('psycopg2.connect')
    def test_universe_expansion_performance(self, mock_connect, etf_manager):
        """Test universe expansion performance meets <2 second requirement"""
        import time
        
        # Setup fast mock responses
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        mock_cursor.fetchone.return_value = [{
            'action': 'updated',
            'symbols_count': 10,
            'cache_key': 'etf_test'
        }]
        
        start_time = time.time()
        
        # Execute universe expansion
        results = etf_manager.expand_etf_universes()
        
        expansion_time = time.time() - start_time
        
        # Verify performance requirement: <2 seconds for 200+ ETF processing
        assert expansion_time < 2.0, f"Universe expansion took {expansion_time:.3f}s, expected <2.0s"
        
        # Verify comprehensive processing
        assert results['themes_processed'] == 7
        assert results['success'] > 0
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_redis_publishing_performance(self, etf_manager):
        """Test Redis publishing performance for real-time requirements"""
        import time
        
        expansion_results = {
            'timestamp': datetime.now().isoformat(),
            'themes_processed': 7,
            'total_symbols': 50,
            'success': 7,
            'themes': {f'theme_{i}': {'action': 'updated', 'symbols_count': 10} for i in range(7)}
        }
        
        with patch.object(etf_manager, 'connect_redis') as mock_redis:
            mock_client = AsyncMock()
            mock_redis.return_value = mock_client
            
            start_time = time.time()
            
            result = await etf_manager.publish_universe_updates(expansion_results)
            
            publishing_time = time.time() - start_time
            
            # Verify performance requirement: <5 seconds for Redis publishing
            assert publishing_time < 5.0, f"Redis publishing took {publishing_time:.3f}s, expected <5.0s"
            assert result is True
    
    @pytest.mark.performance
    @patch('psycopg2.connect')
    def test_memory_efficiency_large_universe(self, mock_connect, etf_manager):
        """Test memory efficiency with large universe processing"""
        import sys
        
        # Mock large dataset
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        mock_cursor.fetchone.return_value = [{
            'action': 'updated',
            'symbols_count': 200,
            'cache_key': 'etf_large'
        }]
        
        # Measure memory usage
        initial_memory = sys.getsizeof(etf_manager)
        
        # Process multiple expansions
        for _ in range(5):
            results = etf_manager.expand_etf_universes()
            assert results['success'] > 0
        
        final_memory = sys.getsizeof(etf_manager)
        
        # Verify no significant memory leaks
        memory_growth = final_memory - initial_memory
        assert memory_growth < 10000, f"Memory grew by {memory_growth} bytes, indicating potential leak"


class TestETFUniverseManagerRegression:
    """Regression tests to ensure existing functionality is preserved"""
    
    @pytest.fixture
    def etf_manager(self):
        """Create ETF manager for regression testing"""
        return ETFUniverseManager()
    
    def test_etf_metadata_structure_preservation(self, etf_manager):
        """Test ETFMetadata structure remains compatible"""
        # Get sample ETF
        sector_etfs = etf_manager._get_sector_etfs()
        assert len(sector_etfs) > 0
        
        etf = sector_etfs[0]
        
        # Verify all required fields exist
        required_fields = [
            'symbol', 'name', 'aum', 'expense_ratio', 'avg_volume',
            'underlying_index', 'sector_focus', 'inception_date', 'dividend_yield'
        ]
        
        for field in required_fields:
            assert hasattr(etf, field), f"ETFMetadata missing required field: {field}"
            assert getattr(etf, field) is not None or field in ['dividend_yield'], f"Field {field} should not be None"
    
    def test_universe_theme_consistency(self, etf_manager):
        """Test universe theme consistency with existing patterns"""
        themes = ['sectors', 'growth', 'value', 'international', 'commodities', 'technology', 'bonds']
        
        for theme in themes:
            # Verify each theme generator exists
            method_name = f'_get_{theme}_etfs'
            assert hasattr(etf_manager, method_name), f"Missing theme generator: {method_name}"
            
            # Verify theme generates valid ETFs
            etfs = getattr(etf_manager, method_name)()
            assert isinstance(etfs, list), f"Theme {theme} should return list"
            
            if etfs:  # If theme has ETFs
                assert all(isinstance(etf, ETFMetadata) for etf in etfs), f"All {theme} items should be ETFMetadata"
    
    @patch('psycopg2.connect')
    def test_database_function_compatibility(self, mock_connect, etf_manager):
        """Test compatibility with existing database functions"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # Mock database function response matching expected format
        mock_cursor.fetchone.return_value = [{
            'action': 'updated',
            'cache_key': 'etf_test',
            'symbols_count': 5,
            'added_count': 2,
            'removed_count': 1,
            'symbols_added': ['NEW1', 'NEW2'],
            'symbols_removed': ['OLD1'],
            'timestamp': datetime.now()
        }]
        
        # Test database integration
        etfs = [ETFMetadata('TEST', 'Test ETF', 1e9, 0.1, 5e6, 'Test Index', 'test', '2020-01-01', 1.0)]
        result = etf_manager._update_universe_in_db('test', etfs)
        
        # Verify expected database function call format
        args, kwargs = mock_cursor.execute.call_args
        assert 'update_etf_universe' in args[0], "Should call update_etf_universe function"
        assert len(args[1]) == 3, "Function should receive 3 parameters"
    
    def test_redis_channel_consistency(self, etf_manager):
        """Test Redis channel names remain consistent"""
        expected_channels = {
            'universe_updated': 'tickstock.universe.updated',
            'etf_correlation_update': 'tickstock.etf.correlation_update',
            'universe_validation': 'tickstock.universe.validation_complete'
        }
        
        assert etf_manager.channels == expected_channels, "Redis channels changed unexpectedly"
    
    def test_filtering_criteria_consistency(self, etf_manager):
        """Test filtering criteria remain consistent with requirements"""
        # Verify filtering thresholds
        assert etf_manager.min_aum_threshold == 1e9, "AUM threshold should be $1B"
        assert etf_manager.min_volume_threshold == 5e6, "Volume threshold should be 5M"
        assert etf_manager.max_expense_ratio == 0.75, "Max expense ratio should be 0.75%"
        
        # Test filtering application
        sector_etfs = etf_manager._get_sector_etfs()
        if sector_etfs:
            for etf in sector_etfs:
                assert etf.aum >= etf_manager.min_aum_threshold, f"ETF {etf.symbol} fails AUM filter"
                assert etf.avg_volume >= etf_manager.min_volume_threshold, f"ETF {etf.symbol} fails volume filter"
    
    @pytest.mark.asyncio
    async def test_universe_validation_backwards_compatibility(self, etf_manager):
        """Test universe validation maintains backward compatibility"""
        with patch.object(etf_manager, 'get_database_connection') as mock_db:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_conn.cursor.return_value = mock_cursor
            mock_db.return_value = mock_conn
            
            # Mock validation response in expected format
            mock_cursor.fetchall.return_value = [
                {
                    'universe_key': 'etf_sectors',
                    'symbol': 'XLF',
                    'exists_in_symbols': True,
                    'symbol_type': 'ETF',
                    'active_status': True
                }
            ]
            
            result = await etf_manager.validate_universe_symbols()
            
            # Verify expected response structure
            assert 'validation_summary' in result
            assert 'missing_symbols' in result
            assert 'total_missing' in result
            assert 'overall_health' in result
            
            # Verify calculation logic
            assert result['total_missing'] == 0
            assert result['overall_health'] in ['good', 'needs_attention']


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])