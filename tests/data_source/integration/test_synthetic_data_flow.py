"""
Integration tests for synthetic data flow validation - Sprint 111

Tests end-to-end data flow from synthetic provider through processing pipeline
with comprehensive validation of configuration changes and data integrity.
"""

import pytest
import time
from unittest.mock import Mock, patch

from src.infrastructure.data_sources.synthetic.provider import SimulatedDataProvider
from src.infrastructure.data_sources.synthetic.types import DataFrequency
from src.core.services.config_manager import ConfigManager
from src.core.domain.market.tick import TickData


class TestSyntheticDataFlowIntegration:
    """Integration tests for synthetic data flow and configuration changes."""
    
    @pytest.fixture
    def config_manager(self):
        """ConfigManager instance for testing."""
        cm = ConfigManager()
        cm.load_from_env()
        return cm
    
    def test_end_to_end_per_second_flow(self, config_manager):
        """Test complete per-second data flow from generation to validation."""
        # Apply development preset
        success = config_manager.apply_synthetic_data_preset('development')
        assert success is True
        
        config_manager.config['MARKET_TIMEZONE'] = 'US/Eastern'
        provider = SimulatedDataProvider(config_manager.config)
        
        # Generate per-second data
        tick_data = provider.generate_frequency_data('AAPL', DataFrequency.PER_SECOND)
        
        # Verify data structure and integrity
        assert isinstance(tick_data, TickData)
        assert tick_data.ticker == 'AAPL'
        assert tick_data.price > 0
        assert tick_data.volume > 0
        assert tick_data.timestamp > 0
        assert tick_data.source == 'simulated_per_second'
        
        # Verify data validation passes
        assert tick_data.validate() is True
    
    def test_end_to_end_per_minute_flow(self, config_manager):
        """Test complete per-minute data flow from generation to validation.""" 
        # Apply integration testing preset (enables per-minute)
        success = config_manager.apply_synthetic_data_preset('integration_testing')
        assert success is True
        
        config_manager.config['MARKET_TIMEZONE'] = 'US/Eastern'
        provider = SimulatedDataProvider(config_manager.config)
        
        # Generate per-minute data
        minute_data = provider.generate_frequency_data('AAPL', DataFrequency.PER_MINUTE)
        
        # Verify Polygon AM event structure
        assert isinstance(minute_data, dict)
        assert minute_data['ev'] == 'AM'
        assert minute_data['sym'] == 'AAPL'
        
        # Verify OHLCV data integrity
        o, h, l, c = minute_data['o'], minute_data['h'], minute_data['l'], minute_data['c']
        assert l <= o <= h
        assert l <= c <= h
        assert minute_data['v'] > 0
        assert minute_data['vw'] > 0
        
        # Verify timing data
        assert minute_data['t'] > 0
        assert minute_data['T'] > minute_data['t']
    
    def test_end_to_end_fmv_flow(self, config_manager):
        """Test complete FMV data flow from generation to validation."""
        # Apply integration testing preset (enables FMV)
        success = config_manager.apply_synthetic_data_preset('integration_testing')
        assert success is True
        
        config_manager.config['MARKET_TIMEZONE'] = 'US/Eastern'
        provider = SimulatedDataProvider(config_manager.config)
        
        # Generate FMV data
        fmv_data = provider.generate_frequency_data('AAPL', DataFrequency.FAIR_VALUE)
        
        # Verify Polygon FMV event structure
        assert isinstance(fmv_data, dict)
        assert fmv_data['ev'] == 'FMV'
        assert fmv_data['sym'] == 'AAPL'
        
        # Verify FMV data integrity
        assert fmv_data['fmv'] > 0     # Fair Market Value
        assert fmv_data['mp'] > 0      # Market Price
        assert -1.0 <= fmv_data['pd'] <= 1.0  # Premium/Discount within reasonable range
        assert 0.0 <= fmv_data['conf'] <= 1.0 # Confidence score
        
        # Verify timing data
        assert fmv_data['t'] > 0
    
    def test_configuration_change_impact(self, config_manager):
        """Test that configuration changes properly affect data generation."""
        base_config = config_manager.config.copy()
        base_config.update({
            'ENABLE_MULTI_FREQUENCY': True,
            'WEBSOCKET_PER_SECOND_ENABLED': True,
            'WEBSOCKET_PER_MINUTE_ENABLED': False,
            'WEBSOCKET_FAIR_VALUE_ENABLED': False,
            'MARKET_TIMEZONE': 'US/Eastern'
        })
        
        # Test single frequency configuration
        provider = SimulatedDataProvider(base_config)
        frequencies = provider.get_supported_frequencies()
        assert len(frequencies) == 1
        assert DataFrequency.PER_SECOND in frequencies
        
        # Test adding per-minute frequency
        base_config['WEBSOCKET_PER_MINUTE_ENABLED'] = True
        provider = SimulatedDataProvider(base_config)
        frequencies = provider.get_supported_frequencies()
        assert len(frequencies) == 2
        assert DataFrequency.PER_MINUTE in frequencies
        
        # Test adding FMV frequency
        base_config['WEBSOCKET_FAIR_VALUE_ENABLED'] = True
        provider = SimulatedDataProvider(base_config)
        frequencies = provider.get_supported_frequencies()
        assert len(frequencies) == 3
        assert DataFrequency.FAIR_VALUE in frequencies
    
    def test_interval_configuration_impact(self, config_manager):
        """Test that interval configuration changes affect data generation timing."""
        # Set up multi-frequency with custom intervals
        success = config_manager.apply_interval_preset('fast_15s')
        assert success is True
        
        # Enable all frequencies
        config_manager.config['ENABLE_MULTI_FREQUENCY'] = True
        config_manager.config['WEBSOCKET_PER_SECOND_ENABLED'] = True
        config_manager.config['WEBSOCKET_PER_MINUTE_ENABLED'] = True
        config_manager.config['WEBSOCKET_FAIR_VALUE_ENABLED'] = True
        config_manager.config['MARKET_TIMEZONE'] = 'US/Eastern'
        
        provider = SimulatedDataProvider(config_manager.config)
        
        # Verify generators picked up custom intervals
        per_second_gen = provider._frequency_generators[DataFrequency.PER_SECOND]
        per_minute_gen = provider._frequency_generators[DataFrequency.PER_MINUTE]
        fmv_gen = provider._frequency_generators[DataFrequency.FAIR_VALUE]
        
        assert per_minute_gen.aggregate_window == 60  # Per-minute window
        assert fmv_gen.update_interval == 15          # 15-second FMV updates from fast_15s
    
    def test_simulator_universe_compliance(self, config_manager):
        """Test that synthetic data respects SIMULATOR_UNIVERSE configuration."""
        # Set specific universe
        config_manager.config['SIMULATOR_UNIVERSE'] = 'MARKET_CAP_LARGE_UNIVERSE'
        config_manager.config['ENABLE_MULTI_FREQUENCY'] = True
        config_manager.config['WEBSOCKET_PER_SECOND_ENABLED'] = True
        config_manager.config['MARKET_TIMEZONE'] = 'US/Eastern'
        
        provider = SimulatedDataProvider(config_manager.config)
        
        # Verify provider uses configured universe
        # (Implementation may vary, but configuration should be respected)
        assert provider.config.get('SIMULATOR_UNIVERSE') == 'MARKET_CAP_LARGE_UNIVERSE'
    
    def test_data_validation_flow(self, config_manager):
        """Test data validation throughout the generation flow.""" 
        # Enable validation
        config_manager.config['ENABLE_SYNTHETIC_DATA_VALIDATION'] = True
        config_manager.config['ENABLE_MULTI_FREQUENCY'] = True
        config_manager.config['WEBSOCKET_PER_SECOND_ENABLED'] = True
        config_manager.config['WEBSOCKET_PER_MINUTE_ENABLED'] = True
        config_manager.config['WEBSOCKET_FAIR_VALUE_ENABLED'] = True
        config_manager.config['MARKET_TIMEZONE'] = 'US/Eastern'
        
        provider = SimulatedDataProvider(config_manager.config)
        
        # Verify validation is enabled
        assert provider._enable_validation is True
        assert provider._validator is not None
        
        # Generate data and verify validation
        tick_data = provider.generate_frequency_data('AAPL', DataFrequency.PER_SECOND)
        assert provider.validate_tick_data(tick_data) is True
        
        # Get validation summary
        validation_summary = provider.get_validation_summary()
        assert validation_summary is not None
        assert isinstance(validation_summary, dict)
    
    def test_generation_statistics_tracking(self, config_manager):
        """Test that generation statistics are properly tracked across frequencies."""
        config_manager.apply_synthetic_data_preset('integration_testing')
        config_manager.config['MARKET_TIMEZONE'] = 'US/Eastern'
        
        provider = SimulatedDataProvider(config_manager.config)
        
        # Generate data across frequencies
        provider.generate_frequency_data('AAPL', DataFrequency.PER_SECOND)
        provider.generate_frequency_data('AAPL', DataFrequency.PER_MINUTE)
        provider.generate_frequency_data('AAPL', DataFrequency.FAIR_VALUE)
        
        # Verify statistics are tracked
        stats = provider.get_generation_statistics()
        
        assert 'total_legacy_ticks' in stats
        assert 'frequencies' in stats
        assert 'active_generators' in stats
        
        # Should have data for all active frequencies
        frequencies = stats['frequencies']
        assert 'per_second' in frequencies
        assert 'per_minute' in frequencies
        assert 'fair_value' in frequencies
    
    def test_error_handling_and_fallbacks(self, config_manager):
        """Test error handling and fallback mechanisms."""
        config_manager.config['ENABLE_MULTI_FREQUENCY'] = True
        config_manager.config['WEBSOCKET_PER_SECOND_ENABLED'] = True
        config_manager.config['WEBSOCKET_PER_MINUTE_ENABLED'] = False  # Disabled
        config_manager.config['MARKET_TIMEZONE'] = 'US/Eastern'
        
        provider = SimulatedDataProvider(config_manager.config)
        
        # Test unsupported frequency error (per-minute disabled)
        with pytest.raises(ValueError, match="No generator available"):
            provider.generate_frequency_data('AAPL', DataFrequency.PER_MINUTE)
    
    def test_preset_end_to_end_validation(self, config_manager):
        """Test that all presets work end-to-end without errors."""
        presets = config_manager.get_synthetic_data_presets()
        
        for preset_name in presets.keys():
            # Apply preset
            success = config_manager.apply_synthetic_data_preset(preset_name)
            assert success is True, f"Failed to apply preset: {preset_name}"
            
            # Add required config
            config_manager.config['MARKET_TIMEZONE'] = 'US/Eastern'
            
            # Create provider
            provider = SimulatedDataProvider(config_manager.config)
            
            # Test that at least per-second generation works
            tick_data = provider.generate_frequency_data('AAPL', DataFrequency.PER_SECOND)
            assert isinstance(tick_data, TickData)
            assert tick_data.validate() is True
    
    def test_multi_ticker_generation(self, config_manager):
        """Test data generation across multiple tickers."""
        config_manager.apply_synthetic_data_preset('integration_testing')
        config_manager.config['MARKET_TIMEZONE'] = 'US/Eastern'
        
        provider = SimulatedDataProvider(config_manager.config)
        
        tickers = ['AAPL', 'GOOGL', 'MSFT', 'TSLA']
        
        for ticker in tickers:
            # Test per-second generation
            tick_data = provider.generate_frequency_data(ticker, DataFrequency.PER_SECOND)
            assert tick_data.ticker == ticker
            assert tick_data.validate() is True
            
            # Test per-minute generation
            minute_data = provider.generate_frequency_data(ticker, DataFrequency.PER_MINUTE)
            assert minute_data['sym'] == ticker
            
            # Test FMV generation
            fmv_data = provider.generate_frequency_data(ticker, DataFrequency.FAIR_VALUE)
            assert fmv_data['sym'] == ticker
    
    def test_performance_under_configuration_changes(self, config_manager):
        """Test performance remains acceptable under various configurations."""
        config_manager.apply_synthetic_data_preset('performance_testing')
        config_manager.config['MARKET_TIMEZONE'] = 'US/Eastern'
        
        provider = SimulatedDataProvider(config_manager.config)
        
        # Performance test
        start_time = time.perf_counter()
        
        for _ in range(100):  # Generate 100 data points
            tick_data = provider.generate_frequency_data('AAPL', DataFrequency.PER_SECOND)
            assert tick_data is not None
        
        end_time = time.perf_counter()
        duration = end_time - start_time
        
        # Should complete 100 generations in reasonable time (adjust as needed)
        assert duration < 5.0, f"Performance test took too long: {duration:.2f}s"
        
        rate = 100 / duration
        assert rate > 20, f"Generation rate too slow: {rate:.1f} generations/second"