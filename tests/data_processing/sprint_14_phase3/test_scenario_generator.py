#!/usr/bin/env python3
"""
Test Scenario Generator Tests - Sprint 14 Phase 3

Comprehensive tests for the Test Scenario Generator System:
- Synthetic OHLCV data generation with controllable patterns
- 5 predefined scenarios with realistic market characteristics
- TA-Lib integration for technical pattern validation
- Performance target: scenario generation and loading in <2 minutes
- CLI integration and database loading functionality

Test Organization:
- Unit tests: Scenario configuration, OHLCV generation, pattern injection
- Integration tests: Database loading, pattern validation, CLI integration
- Performance tests: <2 minute loading requirement, memory efficiency
- Regression tests: Scenario consistency, expected outcome validation
"""

import pytest
import numpy as np
import pandas as pd
import json
import os
import sys
from unittest.mock import Mock, patch, call
from datetime import datetime, timedelta, date
import psycopg2
import psycopg2.extras
from decimal import Decimal
import math
import random

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../'))

from src.data.test_scenario_generator import TestScenarioGenerator, ScenarioConfig

class TestScenarioGeneratorRefactor:
    """Unit tests for Test Scenario Generator refactor functionality"""
    
    @pytest.fixture
    def scenario_generator(self):
        """Create Test Scenario Generator instance for testing"""
        return TestScenarioGenerator(
            database_uri='postgresql://test:test@localhost/test_db'
        )
    
    @pytest.fixture
    def sample_scenario_config(self):
        """Sample scenario configuration for testing"""
        return ScenarioConfig(
            name='test_scenario',
            description='Test scenario for unit testing',
            length=63,
            base_price=100.0,
            volatility_profile='medium',
            trend_direction='up',
            volume_profile='normal',
            pattern_features=['trend_continuation', 'momentum_patterns'],
            expected_outcomes={
                'total_return': 15.0,
                'volatility_periods': 2,
                'trend_strength': 0.7
            }
        )
    
    def test_scenario_generator_initialization(self, scenario_generator):
        """Test scenario generator initialization with proper configuration"""
        assert scenario_generator.database_uri is not None
        assert scenario_generator.random_seed == 42  # Reproducible results
        assert len(scenario_generator.scenarios) == 5  # All predefined scenarios
        
        # Verify all expected scenarios exist
        expected_scenarios = ['crash_2020', 'growth_2021', 'volatility_periods', 'trend_changes', 'high_low_events']
        for scenario_name in expected_scenarios:
            assert scenario_name in scenario_generator.scenarios
    
    def test_scenario_configurations_validity(self, scenario_generator):
        """Test all scenario configurations have valid parameters"""
        for scenario_name, config in scenario_generator.scenarios.items():
            # Verify required fields
            assert config.name == scenario_name
            assert config.description is not None and len(config.description) > 10
            assert config.length > 0 and config.length <= 252  # Max 1 year
            assert config.base_price > 0
            assert config.volatility_profile in ['low', 'medium', 'high', 'extreme']
            assert config.trend_direction in ['up', 'down', 'sideways', 'mixed']
            assert config.volume_profile in ['low', 'normal', 'high', 'spike']
            assert len(config.pattern_features) > 0
            assert len(config.expected_outcomes) > 0
    
    def test_crash_2020_scenario_characteristics(self, scenario_generator):
        """Test crash_2020 scenario has correct characteristics"""
        config = scenario_generator.scenarios['crash_2020']
        
        assert config.length == 252  # Full year
        assert config.volatility_profile == 'extreme'
        assert config.trend_direction == 'mixed'
        assert config.volume_profile == 'spike'
        
        # Verify crash-specific patterns
        assert 'high_low_events' in config.pattern_features
        assert 'volatility_surge' in config.pattern_features
        assert 'volume_spike' in config.pattern_features
        
        # Verify expected outcomes
        assert config.expected_outcomes['max_drawdown'] == -35.0
        assert config.expected_outcomes['volatility_spike_count'] == 15
    
    def test_growth_2021_scenario_characteristics(self, scenario_generator):
        """Test growth_2021 scenario has growth market characteristics"""
        config = scenario_generator.scenarios['growth_2021']
        
        assert config.volatility_profile == 'medium'
        assert config.trend_direction == 'up'
        assert config.volume_profile == 'high'
        
        # Verify growth-specific patterns
        assert 'trend_continuation' in config.pattern_features
        assert 'momentum_patterns' in config.pattern_features
        
        # Verify expected positive outcomes
        assert config.expected_outcomes['total_return'] == 25.0
        assert config.expected_outcomes['trend_strength'] == 0.75
    
    def test_high_low_events_scenario_characteristics(self, scenario_generator):
        """Test high_low_events scenario designed for threshold testing"""
        config = scenario_generator.scenarios['high_low_events']
        
        assert config.length == 63  # 3 months
        assert config.volatility_profile == 'high'
        assert config.volume_profile == 'spike'
        
        # Verify high/low specific patterns
        assert 'high_low_events' in config.pattern_features
        assert 'price_gaps' in config.pattern_features
        
        # Verify expected event counts
        assert config.expected_outcomes['high_events'] == 12
        assert config.expected_outcomes['low_events'] == 10
    
    def test_generate_crash_scenario_data_structure(self, scenario_generator):
        """Test crash scenario generates proper data structure"""
        # Set seed for reproducible testing
        np.random.seed(42)
        random.seed(42)
        
        config = scenario_generator.scenarios['crash_2020']
        ohlcv_data = scenario_generator._generate_crash_scenario(config)
        
        # Verify basic structure
        assert len(ohlcv_data) > 0
        assert len(ohlcv_data) <= config.length  # May be less due to weekend filtering
        
        # Verify OHLCV structure
        for record in ohlcv_data[:5]:  # Check first 5 records
            assert 'date' in record
            assert 'open' in record
            assert 'high' in record
            assert 'low' in record
            assert 'close' in record
            assert 'volume' in record
            
            # Verify OHLC relationships
            assert record['high'] >= record['open']
            assert record['high'] >= record['close']
            assert record['low'] <= record['open']
            assert record['low'] <= record['close']
            
            # Verify volume is reasonable
            assert record['volume'] > 0
    
    def test_generate_growth_scenario_upward_bias(self, scenario_generator):
        """Test growth scenario has proper upward bias"""
        np.random.seed(42)
        random.seed(42)
        
        config = scenario_generator.scenarios['growth_2021']
        ohlcv_data = scenario_generator._generate_growth_scenario(config)
        
        # Verify upward trend
        first_price = ohlcv_data[0]['close']
        last_price = ohlcv_data[-1]['close']
        
        # Should show positive return (allowing some variance)
        total_return = (last_price - first_price) / first_price * 100
        assert total_return > 10.0, f"Growth scenario should show positive return, got {total_return:.2f}%"
        
        # Verify volume characteristics during growth
        volumes = [record['volume'] for record in ohlcv_data]
        avg_volume = np.mean(volumes)
        assert avg_volume >= 3000000, "Growth scenario should have elevated volume"
    
    def test_generate_volatility_scenario_characteristics(self, scenario_generator):
        """Test volatility scenario shows proper mean reversion and clustering"""
        np.random.seed(42)
        random.seed(42)
        
        config = scenario_generator.scenarios['volatility_periods']
        ohlcv_data = scenario_generator._generate_volatility_scenario(config)
        
        # Calculate price returns for volatility analysis
        closes = [record['close'] for record in ohlcv_data]
        returns = np.diff(np.log(closes))
        
        # Verify volatility clustering (high volatility followed by high volatility)
        rolling_vol = pd.Series(returns).rolling(5).std()
        volatility_periods = (rolling_vol > rolling_vol.mean()).sum()
        
        assert volatility_periods > 5, "Should have multiple high volatility periods"
        
        # Verify mean reversion (price shouldn't drift too far from base)
        price_drift = abs(closes[-1] - config.base_price) / config.base_price
        assert price_drift < 0.3, f"Price drift {price_drift:.2f} too high for sideways scenario"
    
    def test_generate_high_low_scenario_events(self, scenario_generator):
        """Test high_low_events scenario generates expected event frequency"""
        np.random.seed(42)
        random.seed(42)
        
        config = scenario_generator.scenarios['high_low_events']
        ohlcv_data = scenario_generator._generate_high_low_scenario(config)
        
        # Calculate daily returns to identify high/low events
        closes = [record['close'] for record in ohlcv_data]
        returns = np.diff(closes) / closes[:-1]
        
        # Count significant events (>5% moves)
        high_events = (returns > 0.05).sum()
        low_events = (returns < -0.05).sum()
        
        # Should have multiple significant events
        assert high_events >= 3, f"Expected multiple high events, got {high_events}"
        assert low_events >= 3, f"Expected multiple low events, got {low_events}"
        
        # Verify exaggerated volume on event days
        high_volume_days = sum(1 for record in ohlcv_data if record['volume'] > 5000000)
        assert high_volume_days >= 5, "Should have multiple high volume event days"
    
    def test_generate_scenario_data_with_symbol_suffix(self, scenario_generator):
        """Test scenario data generation with symbol naming"""
        ohlcv_data = scenario_generator.generate_scenario_data('crash_2020', '_TEST')
        
        assert len(ohlcv_data) > 0
        
        # Verify symbol naming
        for record in ohlcv_data:
            assert record['symbol'] == 'TEST_CRASH_2020_TEST'
        
        # Test without suffix
        ohlcv_data_no_suffix = scenario_generator.generate_scenario_data('growth_2021')
        
        for record in ohlcv_data_no_suffix:
            assert record['symbol'] == 'TEST_GROWTH_2021'
    
    def test_generate_scenario_data_unknown_scenario(self, scenario_generator):
        """Test handling of unknown scenario names"""
        result = scenario_generator.generate_scenario_data('unknown_scenario')
        
        assert result is None
    
    @patch('psycopg2.connect')
    def test_database_connection_success(self, mock_connect, scenario_generator):
        """Test successful database connection"""
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        
        conn = scenario_generator.get_database_connection()
        
        assert conn == mock_conn
        mock_connect.assert_called_once_with(
            scenario_generator.database_uri,
            cursor_factory=psycopg2.extras.RealDictCursor
        )
    
    @patch('psycopg2.connect')
    def test_database_connection_failure(self, mock_connect, scenario_generator):
        """Test database connection failure handling"""
        mock_connect.side_effect = Exception("Connection failed")
        
        conn = scenario_generator.get_database_connection()
        
        assert conn is None
    
    def test_list_scenarios_comprehensive(self, scenario_generator):
        """Test scenarios listing with all details"""
        scenarios_info = scenario_generator.list_scenarios()
        
        assert 'available_scenarios' in scenarios_info
        assert 'total_scenarios' in scenarios_info
        assert scenarios_info['total_scenarios'] == 5
        
        # Verify each scenario has complete information
        for scenario_name, info in scenarios_info['available_scenarios'].items():
            assert 'name' in info
            assert 'description' in info
            assert 'length_days' in info
            assert 'base_price' in info
            assert 'volatility_profile' in info
            assert 'trend_direction' in info
            assert 'volume_profile' in info
            assert 'pattern_features' in info
            assert 'expected_outcomes' in info


class TestScenarioGeneratorIntegration:
    """Integration tests for Test Scenario Generator database operations"""
    
    @pytest.fixture
    def scenario_generator(self):
        """Create scenario generator for integration testing"""
        return TestScenarioGenerator()
    
    @pytest.mark.integration
    @patch('psycopg2.connect')
    def test_load_scenario_database_integration(self, mock_connect, scenario_generator):
        """Test scenario loading integration with database"""
        # Setup mock database connection
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # Mock scenario generation
        with patch.object(scenario_generator, 'generate_scenario_data') as mock_generate:
            mock_ohlcv_data = [
                {
                    'symbol': 'TEST_CRASH_2020',
                    'date': date.today(),
                    'open': 100.0,
                    'high': 105.0,
                    'low': 98.0,
                    'close': 102.0,
                    'volume': 2000000
                }
            ]
            mock_generate.return_value = mock_ohlcv_data
            
            result = scenario_generator.load_scenario('crash_2020')
            
            # Verify successful loading
            assert 'scenario_name' in result
            assert 'symbols_loaded' in result
            assert 'total_records' in result
            assert 'load_duration_seconds' in result
            assert result['scenario_name'] == 'crash_2020'
            assert result['total_records'] == 1
            
            # Verify database operations
            mock_cursor.execute.assert_called()
            mock_conn.commit.assert_called_once()
    
    @pytest.mark.integration
    @patch('psycopg2.connect')
    def test_load_scenario_multiple_symbols(self, mock_connect, scenario_generator):
        """Test loading scenario with multiple symbols"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        with patch.object(scenario_generator, 'generate_scenario_data') as mock_generate:
            mock_ohlcv_data = [
                {
                    'symbol': 'TEST_GROWTH_2021_SYM1',
                    'date': date.today(),
                    'open': 100.0,
                    'high': 102.0,
                    'low': 99.0,
                    'close': 101.5,
                    'volume': 1500000
                }
            ]
            mock_generate.return_value = mock_ohlcv_data
            
            result = scenario_generator.load_scenario('growth_2021', ['SYM1', 'SYM2'])
            
            # Verify multiple symbols processing
            assert result['symbols_loaded'] is not None
            
            # Verify generate_scenario_data called for each symbol
            assert mock_generate.call_count == 2
    
    @pytest.mark.integration
    @patch('psycopg2.connect')  
    def test_validate_scenario_patterns_integration(self, mock_connect, scenario_generator):
        """Test pattern validation integration with TA-Lib"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # Mock OHLCV data for validation
        mock_ohlcv_data = []
        base_price = 100.0
        for i in range(50):  # 50 trading days
            price = base_price * (1 + np.random.normal(0.001, 0.02))
            mock_ohlcv_data.append({
                'date': date.today() - timedelta(days=50-i),
                'open_price': price - np.random.uniform(0, 2),
                'high_price': price + np.random.uniform(0, 3),
                'low_price': price - np.random.uniform(0, 3),
                'close_price': price,
                'volume': 2000000 + int(np.random.uniform(-500000, 1000000))
            })
            base_price = price
        
        mock_cursor.fetchall.return_value = mock_ohlcv_data
        
        result = scenario_generator.validate_scenario_patterns('crash_2020', 'TEST_CRASH_2020')
        
        # Verify validation structure (even without TA-Lib)
        if 'error' not in result:
            assert 'symbol' in result
            assert 'scenario' in result
            assert 'data_points' in result
            assert 'total_return_pct' in result
            assert result['data_points'] == 50
        else:
            # If TA-Lib not available, should get appropriate error
            assert 'TA-Lib not available' in result['error']
    
    @pytest.mark.integration
    @patch('psycopg2.connect')
    def test_database_error_handling(self, mock_connect, scenario_generator):
        """Test database error handling during scenario loading"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # Simulate database error
        mock_cursor.execute.side_effect = Exception("Database error")
        
        with patch.object(scenario_generator, 'generate_scenario_data') as mock_generate:
            mock_generate.return_value = [{'symbol': 'TEST', 'date': date.today(), 'open': 100, 'high': 101, 'low': 99, 'close': 100.5, 'volume': 1000000}]
            
            result = scenario_generator.load_scenario('crash_2020')
            
            # Verify error handling
            assert 'error' in result
            mock_conn.rollback.assert_called_once()


class TestScenarioGeneratorPerformance:
    """Performance tests for Test Scenario Generator operations"""
    
    @pytest.fixture
    def scenario_generator(self):
        """Create scenario generator for performance testing"""
        return TestScenarioGenerator()
    
    @pytest.mark.performance
    def test_scenario_generation_performance(self, scenario_generator):
        """Test scenario generation meets <2 minute requirement"""
        import time
        
        start_time = time.time()
        
        # Generate all 5 scenarios
        for scenario_name in scenario_generator.scenarios.keys():
            ohlcv_data = scenario_generator.generate_scenario_data(scenario_name)
            assert len(ohlcv_data) > 0, f"Scenario {scenario_name} failed to generate data"
        
        generation_time = time.time() - start_time
        
        # Verify performance requirement: <30 seconds for all scenario generation
        assert generation_time < 30.0, f"Scenario generation took {generation_time:.3f}s, expected <30s"
    
    @pytest.mark.performance
    @patch('psycopg2.connect')
    def test_scenario_loading_performance(self, mock_connect, scenario_generator):
        """Test scenario loading meets <2 minute requirement for large datasets"""
        import time
        
        # Setup fast database mock
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        start_time = time.time()
        
        # Load crash_2020 scenario (252 days, largest dataset)
        result = scenario_generator.load_scenario('crash_2020')
        
        loading_time = time.time() - start_time
        
        # Verify performance requirement: <120 seconds for loading
        assert loading_time < 120.0, f"Scenario loading took {loading_time:.3f}s, expected <120s"
        assert 'load_duration_seconds' in result
    
    @pytest.mark.performance
    def test_memory_efficiency_large_scenarios(self, scenario_generator):
        """Test memory efficiency with large scenario generation"""
        import sys
        
        initial_memory = sys.getsizeof(scenario_generator)
        
        # Generate largest scenario multiple times
        for _ in range(3):
            ohlcv_data = scenario_generator.generate_scenario_data('crash_2020')
            assert len(ohlcv_data) > 200  # Should generate substantial data
            
            # Clear data to test memory release
            del ohlcv_data
        
        final_memory = sys.getsizeof(scenario_generator)
        memory_growth = final_memory - initial_memory
        
        # Verify no significant memory leaks
        assert memory_growth < 5000, f"Memory grew by {memory_growth} bytes, indicating potential leak"
    
    @pytest.mark.performance
    def test_reproducibility_performance(self, scenario_generator):
        """Test reproducibility with consistent performance"""
        import time
        
        # Generate same scenario multiple times with same seed
        scenario_generator.random_seed = 42
        
        generation_times = []
        generated_data = []
        
        for _ in range(3):
            start_time = time.time()
            ohlcv_data = scenario_generator.generate_scenario_data('volatility_periods')
            generation_time = time.time() - start_time
            
            generation_times.append(generation_time)
            generated_data.append(ohlcv_data)
            
            # Reset seed for reproducibility
            scenario_generator.random_seed = 42
        
        # Verify consistent performance (within 50% variance)
        avg_time = np.mean(generation_times)
        max_time = max(generation_times)
        assert max_time <= avg_time * 1.5, "Performance should be consistent across runs"
        
        # Verify reproducibility
        assert len(generated_data[0]) == len(generated_data[1]) == len(generated_data[2]), "Should generate same number of records"


class TestScenarioGeneratorRegression:
    """Regression tests to ensure existing functionality is preserved"""
    
    @pytest.fixture
    def scenario_generator(self):
        """Create scenario generator for regression testing"""
        return TestScenarioGenerator()
    
    def test_scenario_config_structure_preservation(self, scenario_generator):
        """Test ScenarioConfig structure remains compatible"""
        # Verify all scenarios have proper ScenarioConfig structure
        for scenario_name, config in scenario_generator.scenarios.items():
            assert isinstance(config, ScenarioConfig), f"Scenario {scenario_name} should be ScenarioConfig"
            
            # Verify all required attributes exist
            required_attrs = [
                'name', 'description', 'length', 'base_price', 'volatility_profile',
                'trend_direction', 'volume_profile', 'pattern_features', 'expected_outcomes'
            ]
            
            for attr in required_attrs:
                assert hasattr(config, attr), f"ScenarioConfig missing required attribute: {attr}"
                assert getattr(config, attr) is not None, f"Attribute {attr} should not be None"
    
    def test_ohlcv_data_structure_consistency(self, scenario_generator):
        """Test OHLCV data structure remains consistent"""
        ohlcv_data = scenario_generator.generate_scenario_data('crash_2020')
        
        # Verify structure consistency
        required_fields = ['date', 'open', 'high', 'low', 'close', 'volume', 'symbol']
        
        for record in ohlcv_data[:10]:  # Check first 10 records
            for field in required_fields:
                assert field in record, f"OHLCV record missing required field: {field}"
            
            # Verify data types
            assert isinstance(record['date'], date), "Date should be date object"
            assert isinstance(record['open'], (int, float)), "Open should be numeric"
            assert isinstance(record['high'], (int, float)), "High should be numeric"
            assert isinstance(record['low'], (int, float)), "Low should be numeric"
            assert isinstance(record['close'], (int, float)), "Close should be numeric"
            assert isinstance(record['volume'], int), "Volume should be integer"
            assert isinstance(record['symbol'], str), "Symbol should be string"
    
    def test_expected_outcomes_consistency(self, scenario_generator):
        """Test expected outcomes structure remains consistent"""
        # Verify crash_2020 expected outcomes
        crash_config = scenario_generator.scenarios['crash_2020']
        crash_outcomes = crash_config.expected_outcomes
        
        assert 'max_drawdown' in crash_outcomes
        assert crash_outcomes['max_drawdown'] == -35.0
        assert 'volatility_spike_count' in crash_outcomes
        assert crash_outcomes['volatility_spike_count'] == 15
        
        # Verify growth_2021 expected outcomes
        growth_config = scenario_generator.scenarios['growth_2021']
        growth_outcomes = growth_config.expected_outcomes
        
        assert 'total_return' in growth_outcomes
        assert growth_outcomes['total_return'] == 25.0
        assert 'trend_strength' in growth_outcomes
        assert growth_outcomes['trend_strength'] == 0.75
    
    def test_database_function_compatibility(self, scenario_generator):
        """Test database function calls remain compatible"""
        with patch.object(scenario_generator, 'get_database_connection') as mock_db:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_conn.cursor.return_value = mock_cursor
            mock_db.return_value = mock_conn
            
            with patch.object(scenario_generator, 'generate_scenario_data') as mock_generate:
                mock_generate.return_value = [{
                    'symbol': 'TEST_REGRESSION',
                    'date': date.today(),
                    'open': 100.0,
                    'high': 101.0,
                    'low': 99.0,
                    'close': 100.5,
                    'volume': 1000000
                }]
                
                result = scenario_generator.load_scenario('crash_2020')
                
                # Verify expected database operations
                mock_cursor.execute.assert_called()
                
                # Check INSERT statement format
                insert_calls = [call for call in mock_cursor.execute.call_args_list 
                              if call[0][0].strip().upper().startswith('INSERT')]
                
                assert len(insert_calls) >= 1, "Should have INSERT statements"
                
                # Verify historical_data table structure
                historical_insert = next((call for call in insert_calls 
                                        if 'historical_data' in call[0][0]), None)
                assert historical_insert is not None, "Should insert into historical_data table"
    
    def test_cli_parameter_compatibility(self, scenario_generator):
        """Test CLI parameter handling remains compatible"""
        # Test list scenarios
        scenarios_info = scenario_generator.list_scenarios()
        assert 'available_scenarios' in scenarios_info
        assert 'total_scenarios' in scenarios_info
        assert 'talib_available' in scenarios_info
        
        # Verify scenario info structure for CLI display
        for scenario_name, info in scenarios_info['available_scenarios'].items():
            # These fields are used by CLI output
            assert 'description' in info
            assert 'length_days' in info
            assert 'volatility_profile' in info
            assert 'trend_direction' in info
            assert 'pattern_features' in info
            
            # Verify field types for CLI formatting
            assert isinstance(info['pattern_features'], list)
            assert isinstance(info['length_days'], int)
    
    def test_random_seed_consistency(self, scenario_generator):
        """Test random seed behavior remains consistent for reproducibility"""
        # Generate with same seed twice
        scenario_generator.random_seed = 42
        data1 = scenario_generator.generate_scenario_data('volatility_periods')
        
        scenario_generator.random_seed = 42
        data2 = scenario_generator.generate_scenario_data('volatility_periods')
        
        # Should be identical
        assert len(data1) == len(data2)
        
        # Check first few records are identical
        for i in range(min(5, len(data1))):
            assert abs(data1[i]['close'] - data2[i]['close']) < 0.001, "Should generate identical data with same seed"
            assert data1[i]['volume'] == data2[i]['volume'], "Volume should be identical with same seed"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])