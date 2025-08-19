"""
Integration tests for cross-frequency validation in synthetic data system.

Tests ensure mathematical consistency and correlation between different 
data frequencies (per-second, per-minute, fair market value).
"""

import pytest
import time
import asyncio
from unittest.mock import patch, Mock
from typing import List, Dict, Any

# Import fixtures
from tests.data_source.fixtures.synthetic_data_fixtures import (
    SyntheticTestScenario,
    assert_frequency_support,
    assert_generation_statistics,
    assert_validation_result
)

# Import synthetic data types
try:
    from src.infrastructure.data_sources.synthetic.types import DataFrequency
    from src.infrastructure.data_sources.synthetic.provider import SimulatedDataProvider
    from src.infrastructure.data_sources.synthetic.validators.data_consistency import (
        DataConsistencyValidator,
        ValidationResult,
        TickWindow
    )
    from src.core.domain.market.tick import TickData
    from src.core.services.config_manager import ConfigManager
except ImportError:
    # Mock imports for test environment
    from enum import Enum
    
    class DataFrequency(Enum):
        PER_SECOND = "per_second"
        PER_MINUTE = "per_minute" 
        FAIR_VALUE = "fair_value"
    
    SimulatedDataProvider = Mock
    DataConsistencyValidator = Mock
    ValidationResult = Mock
    TickWindow = Mock
    TickData = Mock
    ConfigManager = Mock


class TestCrossFrequencyValidation:
    """Test cross-frequency validation functionality."""
    
    @pytest.mark.integration
    def test_per_minute_aggregation_consistency(
        self,
        multi_frequency_synthetic_config,
        synthetic_test_tickers,
        synthetic_data_builder
    ):
        """Test that per-minute bars mathematically align with per-second ticks."""
        # Create provider with multi-frequency configuration
        provider = SimulatedDataProvider(multi_frequency_synthetic_config)
        
        # Generate per-second ticks for one minute window
        ticker = "AAPL"
        base_timestamp = time.time()
        ticks = []
        
        for i in range(60):  # 60 ticks over 1 minute
            tick_timestamp = base_timestamp + i
            tick_data = provider.generate_tick_data(ticker, DataFrequency.PER_SECOND)
            
            if tick_data:
                ticks.append(tick_data)
        
        # Generate corresponding per-minute bar
        minute_bar = provider.generate_tick_data(ticker, DataFrequency.PER_MINUTE)
        
        assert minute_bar is not None
        assert isinstance(minute_bar, dict)
        
        # Validate bar structure
        required_fields = ['o', 'h', 'l', 'c', 'v', 'vw']
        for field in required_fields:
            assert field in minute_bar, f"Missing required field: {field}"
        
        # Validate price relationships
        assert minute_bar['l'] <= minute_bar['o'] <= minute_bar['h']
        assert minute_bar['l'] <= minute_bar['c'] <= minute_bar['h']
        assert minute_bar['v'] > 0
        
        # If we have tick data, validate mathematical consistency
        if ticks and len(ticks) > 0:
            tick_prices = [t.price if hasattr(t, 'price') else t.get('price', 0) for t in ticks if t]
            tick_volumes = [t.volume if hasattr(t, 'volume') else t.get('volume', 0) for t in ticks if t]
            
            if tick_prices and tick_volumes:
                # Check that minute bar high/low are within tick range
                tick_high = max(tick_prices)
                tick_low = min(tick_prices)
                
                # Allow small tolerance for synthetic data generation
                price_tolerance = 0.01  # 1% tolerance
                
                assert abs(minute_bar['h'] - tick_high) / tick_high <= price_tolerance
                assert abs(minute_bar['l'] - tick_low) / tick_low <= price_tolerance
    
    @pytest.mark.integration
    def test_fmv_price_correlation(
        self,
        multi_frequency_synthetic_config,
        synthetic_test_tickers,
        correlation_test_data
    ):
        """Test that FMV updates correlate appropriately with market price movements."""
        # Create provider with FMV enabled
        config = multi_frequency_synthetic_config.copy()
        config['SYNTHETIC_FMV_UPDATE_INTERVAL'] = 1  # Update every second for testing
        
        provider = SimulatedDataProvider(config)
        
        ticker = "AAPL"
        price_movements = []
        fmv_updates = []
        
        # Generate a series of price movements and FMV updates
        base_price = 150.0
        for i in range(10):
            # Simulate price movement
            price_change = (-1) ** i * 0.5  # Alternating up/down movements
            current_price = base_price + i * price_change
            
            # Update provider's internal price
            provider.last_price[ticker] = current_price
            
            # Generate FMV update
            fmv_update = provider.generate_tick_data(ticker, DataFrequency.FAIR_VALUE)
            
            if fmv_update:
                price_movements.append(current_price)
                fmv_updates.append(fmv_update)
            
            time.sleep(0.1)  # Small delay to ensure different timestamps
        
        assert len(fmv_updates) > 0, "No FMV updates generated"
        
        # Analyze correlation
        if len(fmv_updates) >= 2:
            # Check that FMV generally follows market price direction
            price_changes = []
            fmv_changes = []
            
            for i in range(1, min(len(price_movements), len(fmv_updates))):
                price_change = price_movements[i] - price_movements[i-1]
                fmv_price = fmv_updates[i].get('fmv', fmv_updates[i].get('price', 0))
                prev_fmv_price = fmv_updates[i-1].get('fmv', fmv_updates[i-1].get('price', 0))
                
                if fmv_price and prev_fmv_price:
                    fmv_change = fmv_price - prev_fmv_price
                    price_changes.append(price_change)
                    fmv_changes.append(fmv_change)
            
            # Check that FMV changes have some correlation with price changes
            if len(price_changes) >= 3:
                same_direction_count = sum(
                    1 for pc, fc in zip(price_changes, fmv_changes)
                    if (pc > 0 and fc > 0) or (pc < 0 and fc < 0) or (pc == 0 and abs(fc) < 0.01)
                )
                correlation_ratio = same_direction_count / len(price_changes)
                
                # FMV should follow price direction at least 60% of the time
                assert correlation_ratio >= 0.6, f"Poor FMV correlation: {correlation_ratio:.2%}"
    
    @pytest.mark.integration
    def test_data_consistency_validator_integration(
        self,
        multi_frequency_synthetic_config,
        synthetic_data_builder
    ):
        """Test integration of DataConsistencyValidator with synthetic data generators."""
        # Enable validation in config
        config = multi_frequency_synthetic_config.copy()
        config['ENABLE_SYNTHETIC_DATA_VALIDATION'] = True
        config['VALIDATION_PRICE_TOLERANCE'] = 0.01  # 1% tolerance for testing
        
        validator = DataConsistencyValidator(config)
        provider = SimulatedDataProvider(config)
        
        ticker = "AAPL"
        
        # Generate and validate per-second ticks
        ticks = []
        for _ in range(30):  # Generate 30 seconds of tick data
            tick_data = provider.generate_tick_data(ticker, DataFrequency.PER_SECOND)
            if tick_data:
                validator.add_tick_data(ticker, tick_data)
                ticks.append(tick_data)
            time.sleep(0.05)  # Small delay
        
        # Generate per-minute bar
        minute_bar = provider.generate_tick_data(ticker, DataFrequency.PER_MINUTE)
        if minute_bar:
            validator.add_minute_bar(ticker, minute_bar)
            
            # Validate minute bar consistency
            validation_result = validator.validate_minute_bar_consistency(ticker, minute_bar)
            assert_validation_result(validation_result, should_be_valid=True)
        
        # Generate FMV update
        fmv_update = provider.generate_tick_data(ticker, DataFrequency.FAIR_VALUE)
        if fmv_update:
            validator.add_fmv_update(ticker, fmv_update)
            
            # Validate FMV correlation
            fmv_validation = validator.validate_fmv_correlation(ticker, fmv_update)
            assert_validation_result(fmv_validation, should_be_valid=True)
        
        # Check validation summary
        summary = validator.get_validation_summary()
        assert isinstance(summary, dict)
        assert summary['total_validations'] > 0
        assert summary['success_rate'] > 0.0
    
    @pytest.mark.integration
    def test_configuration_preset_integration(
        self,
        synthetic_test_tickers
    ):
        """Test that configuration presets work correctly with synthetic data generation."""
        config_manager = ConfigManager()
        
        # Test each preset
        presets = config_manager.get_synthetic_data_presets()
        
        for preset_name, preset_config in presets.items():
            # Apply preset
            success = config_manager.apply_synthetic_data_preset(preset_name)
            assert success, f"Failed to apply preset: {preset_name}"
            
            # Validate the applied configuration
            is_valid, errors = config_manager.validate_synthetic_data_config()
            assert is_valid, f"Preset {preset_name} resulted in invalid config: {errors}"
            
            # Test synthetic data generation with this preset
            provider = SimulatedDataProvider(config_manager.config)
            
            # Generate data for each supported frequency
            ticker = "AAPL"
            generation_successful = False
            
            for frequency in [DataFrequency.PER_SECOND, DataFrequency.PER_MINUTE, DataFrequency.FAIR_VALUE]:
                try:
                    if provider.has_frequency_support(frequency):
                        data = provider.generate_tick_data(ticker, frequency)
                        if data:
                            generation_successful = True
                except Exception as e:
                    # Some presets may not support all frequencies
                    continue
            
            assert generation_successful, f"No data generated for preset: {preset_name}"
    
    @pytest.mark.integration
    def test_multi_ticker_cross_frequency_generation(
        self,
        multi_frequency_synthetic_config,
        synthetic_test_tickers
    ):
        """Test cross-frequency generation for multiple tickers simultaneously."""
        provider = SimulatedDataProvider(multi_frequency_synthetic_config)
        
        # Test data generation for multiple tickers across all frequencies
        results = {}
        
        for ticker in synthetic_test_tickers[:3]:  # Test with first 3 tickers
            results[ticker] = {}
            
            for frequency in [DataFrequency.PER_SECOND, DataFrequency.PER_MINUTE, DataFrequency.FAIR_VALUE]:
                if provider.has_frequency_support(frequency):
                    data = provider.generate_tick_data(ticker, frequency)
                    results[ticker][frequency.value] = data
        
        # Validate that data was generated for each ticker/frequency combination
        for ticker, ticker_data in results.items():
            assert len(ticker_data) > 0, f"No data generated for ticker: {ticker}"
            
            for frequency_name, data in ticker_data.items():
                assert data is not None, f"No data for {ticker} {frequency_name}"
                
                # Basic data validation
                if frequency_name == DataFrequency.PER_SECOND.value:
                    assert hasattr(data, 'ticker') or 'ticker' in data
                elif frequency_name == DataFrequency.PER_MINUTE.value:
                    assert isinstance(data, dict)
                    assert 'o' in data and 'h' in data and 'l' in data and 'c' in data
                elif frequency_name == DataFrequency.FAIR_VALUE.value:
                    assert isinstance(data, dict)
                    assert 'fmv' in data and 'mp' in data
        
        # Check generation statistics
        stats = provider.get_generation_statistics()
        assert stats['total_legacy_ticks'] >= 0
        assert len(stats['frequencies']) > 0
    
    @pytest.mark.integration
    @pytest.mark.slow
    def test_sustained_multi_frequency_generation(
        self,
        multi_frequency_synthetic_config,
        synthetic_test_tickers
    ):
        """Test sustained multi-frequency data generation over time."""
        # Configure for sustained testing
        config = multi_frequency_synthetic_config.copy()
        config['SYNTHETIC_PER_SECOND_FREQUENCY'] = 0.5  # Every 0.5 seconds
        config['SYNTHETIC_FMV_UPDATE_INTERVAL'] = 5     # Every 5 seconds
        
        provider = SimulatedDataProvider(config)
        
        ticker = "AAPL"
        test_duration = 10.0  # 10 second test
        start_time = time.time()
        
        generation_counts = {
            DataFrequency.PER_SECOND: 0,
            DataFrequency.PER_MINUTE: 0,
            DataFrequency.FAIR_VALUE: 0
        }
        
        # Sustained generation loop
        while time.time() - start_time < test_duration:
            for frequency in generation_counts.keys():
                if provider.has_frequency_support(frequency):
                    try:
                        data = provider.generate_tick_data(ticker, frequency)
                        if data:
                            generation_counts[frequency] += 1
                    except Exception as e:
                        # Continue testing even if some generations fail
                        pass
            
            time.sleep(0.1)  # Brief pause between generation cycles
        
        # Validate sustained generation
        total_generated = sum(generation_counts.values())
        assert total_generated > 0, "No data generated during sustained test"
        
        # Check that per-second data was generated most frequently
        if generation_counts[DataFrequency.PER_SECOND] > 0:
            assert generation_counts[DataFrequency.PER_SECOND] >= generation_counts.get(DataFrequency.PER_MINUTE, 0)
            
        # If FMV is enabled, it should generate less frequently
        if generation_counts[DataFrequency.FAIR_VALUE] > 0:
            assert generation_counts[DataFrequency.FAIR_VALUE] <= generation_counts[DataFrequency.PER_SECOND]
    
    @pytest.mark.integration
    def test_validation_error_handling(
        self,
        strict_validation_config,
        synthetic_data_builder
    ):
        """Test how the system handles validation errors and edge cases."""
        # Create validator with strict settings
        validator = DataConsistencyValidator(strict_validation_config)
        provider = SimulatedDataProvider(strict_validation_config)
        
        ticker = "TEST"
        
        # Test 1: Validation with no tick data
        empty_minute_bar = synthetic_data_builder.create_per_minute_bar(ticker=ticker)
        result = validator.validate_minute_bar_consistency(ticker, empty_minute_bar)
        
        # Should warn about no tick data but not fail
        assert len(result.warnings) > 0 or result.is_valid
        
        # Test 2: Invalid FMV data
        invalid_fmv = {
            'ev': 'FMV',
            'sym': ticker,
            'fmv': -10.0,  # Invalid negative price
            'mp': 150.0,
            'conf': 1.5    # Invalid confidence > 1.0
        }
        
        fmv_result = validator.validate_fmv_correlation(ticker, invalid_fmv)
        assert not fmv_result.is_valid
        assert len(fmv_result.errors) > 0
        
        # Test 3: Provider with invalid configuration
        invalid_config = strict_validation_config.copy()
        invalid_config['SYNTHETIC_FMV_CORRELATION'] = 1.5  # Invalid correlation > 1.0
        
        config_manager = ConfigManager()
        config_manager.config.update(invalid_config)
        
        is_valid, errors = config_manager.validate_synthetic_data_config()
        assert not is_valid
        assert len(errors) > 0
    
    @pytest.mark.integration
    def test_frequency_switching_and_reconfiguration(
        self,
        basic_synthetic_config,
        multi_frequency_synthetic_config
    ):
        """Test switching between different frequency configurations."""
        # Start with basic single-frequency configuration
        provider = SimulatedDataProvider(basic_synthetic_config)
        
        # Verify initial configuration
        supported_frequencies = provider.get_supported_frequencies()
        assert DataFrequency.PER_SECOND in supported_frequencies
        assert len(supported_frequencies) == 1
        
        # Generate some single-frequency data
        ticker = "AAPL"
        single_freq_data = provider.generate_tick_data(ticker, DataFrequency.PER_SECOND)
        assert single_freq_data is not None
        
        # Switch to multi-frequency configuration
        # (In real implementation, this would require provider recreation)
        provider_multi = SimulatedDataProvider(multi_frequency_synthetic_config)
        
        # Verify multi-frequency configuration
        supported_multi = provider_multi.get_supported_frequencies()
        assert len(supported_multi) > 1
        assert DataFrequency.PER_SECOND in supported_multi
        assert DataFrequency.PER_MINUTE in supported_multi or DataFrequency.FAIR_VALUE in supported_multi
        
        # Generate multi-frequency data
        multi_freq_data = {}
        for frequency in supported_multi:
            data = provider_multi.generate_tick_data(ticker, frequency)
            if data:
                multi_freq_data[frequency] = data
        
        assert len(multi_freq_data) > 1, "Multi-frequency provider should generate multiple data types"


class TestSyntheticDataScenarios:
    """Test predefined synthetic data scenarios."""
    
    @pytest.mark.integration
    def test_scenario_execution(
        self,
        test_scenarios,
        multi_frequency_test_runner,
        synthetic_test_tickers
    ):
        """Test execution of predefined synthetic data scenarios."""
        tickers = synthetic_test_tickers[:2]  # Use first 2 tickers for testing
        
        for scenario in test_scenarios:
            result = multi_frequency_test_runner.run_scenario(scenario, tickers)
            
            assert result['success'], f"Scenario {scenario.name} failed: {result}"
            assert result['generation_count'] >= scenario.expected_generation_count
            assert result['duration'] >= scenario.test_duration_seconds * 0.9  # Allow 10% variance
        
        # Check overall test runner summary
        summary = multi_frequency_test_runner.get_summary()
        assert summary['success_rate'] > 0.8  # At least 80% success rate
        assert summary['total_generations'] > 0
    
    @pytest.mark.integration
    def test_scenario_performance_characteristics(
        self,
        test_scenarios,
        performance_test_config,
        performance_timer
    ):
        """Test performance characteristics of different scenarios."""
        # Use performance configuration for more demanding testing
        provider = SimulatedDataProvider(performance_test_config)
        
        ticker = "AAPL"
        performance_results = {}
        
        for scenario in test_scenarios[:2]:  # Test first 2 scenarios for performance
            performance_timer.start()
            
            # Apply scenario configuration
            test_config = performance_test_config.copy()
            test_config.update(scenario.config)
            scenario_provider = SimulatedDataProvider(test_config)
            
            # Generate data rapidly
            generation_count = 0
            for _ in range(100):  # 100 rapid generations
                for frequency in scenario.expected_frequencies:
                    if scenario_provider.has_frequency_support(frequency):
                        data = scenario_provider.generate_tick_data(ticker, frequency)
                        if data:
                            generation_count += 1
            
            performance_timer.stop()
            
            performance_results[scenario.name] = {
                'duration': performance_timer.elapsed,
                'generation_count': generation_count,
                'generations_per_second': generation_count / performance_timer.elapsed if performance_timer.elapsed > 0 else 0
            }
        
        # Validate performance results
        for scenario_name, perf_data in performance_results.items():
            assert perf_data['generation_count'] > 0, f"No data generated for {scenario_name}"
            assert perf_data['generations_per_second'] > 10, f"Poor performance for {scenario_name}: {perf_data['generations_per_second']:.1f} gen/sec"


# Test data validation helpers specific to cross-frequency testing
def validate_cross_frequency_data_integrity(per_second_data, per_minute_data, fmv_data):
    """Validate data integrity across frequencies."""
    # Check timestamp alignment
    if hasattr(per_second_data, 'timestamp'):
        second_timestamp = per_second_data.timestamp
    elif isinstance(per_second_data, dict) and 'timestamp' in per_second_data:
        second_timestamp = per_second_data['timestamp']
    else:
        second_timestamp = None
    
    if per_minute_data and 'timestamp' in per_minute_data:
        minute_timestamp = per_minute_data['timestamp']
    else:
        minute_timestamp = None
    
    if fmv_data and 't' in fmv_data:
        fmv_timestamp = fmv_data['t'] / 1000  # Convert from ms
    else:
        fmv_timestamp = None
    
    # Timestamps should be reasonably close (within 60 seconds)
    timestamps = [t for t in [second_timestamp, minute_timestamp, fmv_timestamp] if t is not None]
    if len(timestamps) > 1:
        max_diff = max(timestamps) - min(timestamps)
        assert max_diff <= 60, f"Timestamp differences too large: {max_diff} seconds"
    
    return True


def assert_market_regime_consistency(fmv_generator, expected_regimes):
    """Assert that FMV generator produces expected market regimes."""
    if hasattr(fmv_generator, 'get_correlation_analysis'):
        analysis = fmv_generator.get_correlation_analysis('AAPL')
        if 'market_regime' in analysis:
            assert analysis['market_regime'] in expected_regimes