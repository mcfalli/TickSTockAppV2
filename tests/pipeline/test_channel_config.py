"""
Unit tests for Channel Configuration System.

Tests configuration management including:
- Configuration validation and defaults
- Batching strategy configuration
- Channel-specific configurations
- Integration with ConfigManager

Sprint 105: Core Channel Infrastructure Testing
"""

import pytest
from unittest.mock import Mock, patch
from dataclasses import asdict, replace
from typing import Dict, Any

from src.processing.channels.channel_config import (
    ChannelConfig,
    BatchingConfig,
    BatchingStrategy,
    TickChannelConfig,
    OHLCVChannelConfig,
    FMVChannelConfig,
    ChannelConfigFactory,
    ValidationError
)


class TestBatchingConfig:
    """Test batching configuration functionality"""

    def test_batching_config_defaults(self):
        """Test batching configuration default values"""
        config = BatchingConfig()
        
        assert config.strategy == BatchingStrategy.IMMEDIATE
        assert config.max_batch_size == 10
        assert config.max_wait_time_ms == 1000
        assert config.enable_adaptive_batching is False

    def test_batching_config_custom_values(self):
        """Test batching configuration with custom values"""
        config = BatchingConfig(
            strategy=BatchingStrategy.SIZE_BASED,
            max_batch_size=50,
            max_wait_time_ms=5000,
            enable_adaptive_batching=True
        )
        
        assert config.strategy == BatchingStrategy.SIZE_BASED
        assert config.max_batch_size == 50
        assert config.max_wait_time_ms == 5000
        assert config.enable_adaptive_batching is True

    def test_batching_config_validation(self):
        """Test batching configuration validation"""
        # Valid configuration should not raise
        BatchingConfig(max_batch_size=1, max_wait_time_ms=100)
        
        # Invalid batch size should raise
        with pytest.raises(ValidationError):
            BatchingConfig(max_batch_size=0)
        
        with pytest.raises(ValidationError):
            BatchingConfig(max_batch_size=1001)
        
        # Invalid wait time should raise  
        with pytest.raises(ValidationError):
            BatchingConfig(max_wait_time_ms=0)
        
        with pytest.raises(ValidationError):
            BatchingConfig(max_wait_time_ms=60001)

    def test_batching_config_serialization(self):
        """Test batching configuration serialization"""
        config = BatchingConfig(
            strategy=BatchingStrategy.TIME_BASED,
            max_batch_size=25,
            max_wait_time_ms=2000
        )
        
        config_dict = config.to_dict()
        
        assert config_dict['strategy'] == 'time_based'
        assert config_dict['max_batch_size'] == 25
        assert config_dict['max_wait_time_ms'] == 2000
        assert isinstance(config_dict, dict)

    def test_batching_config_from_dict(self):
        """Test batching configuration from dictionary"""
        config_dict = {
            'strategy': 'size_based',
            'max_batch_size': 75,
            'max_wait_time_ms': 3000,
            'enable_adaptive_batching': True
        }
        
        config = BatchingConfig.from_dict(config_dict)
        
        assert config.strategy == BatchingStrategy.SIZE_BASED
        assert config.max_batch_size == 75
        assert config.max_wait_time_ms == 3000
        assert config.enable_adaptive_batching is True

    def test_batching_strategy_enum_values(self):
        """Test all batching strategy enum values"""
        assert BatchingStrategy.IMMEDIATE.value == "immediate"
        assert BatchingStrategy.SIZE_BASED.value == "size_based"
        assert BatchingStrategy.TIME_BASED.value == "time_based"
        assert BatchingStrategy.ADAPTIVE.value == "adaptive"


class TestChannelConfig:
    """Test base channel configuration"""

    def test_channel_config_defaults(self):
        """Test channel configuration default values"""
        config = ChannelConfig()
        
        assert config.max_queue_size == 1000
        assert config.circuit_breaker_threshold == 10
        assert config.circuit_breaker_timeout == 60.0
        assert config.enable_metrics is True
        assert config.priority == 1
        assert isinstance(config.batching, BatchingConfig)

    def test_channel_config_custom_values(self):
        """Test channel configuration with custom values"""
        batching = BatchingConfig(strategy=BatchingStrategy.SIZE_BASED)
        
        config = ChannelConfig(
            max_queue_size=2000,
            circuit_breaker_threshold=5,
            circuit_breaker_timeout=30.0,
            enable_metrics=False,
            priority=2,
            batching=batching
        )
        
        assert config.max_queue_size == 2000
        assert config.circuit_breaker_threshold == 5
        assert config.circuit_breaker_timeout == 30.0
        assert config.enable_metrics is False
        assert config.priority == 2
        assert config.batching.strategy == BatchingStrategy.SIZE_BASED

    def test_channel_config_validation(self):
        """Test channel configuration validation"""
        # Valid configuration
        ChannelConfig(max_queue_size=100, priority=1)
        
        # Invalid queue size
        with pytest.raises(ValidationError):
            ChannelConfig(max_queue_size=0)
        
        with pytest.raises(ValidationError):
            ChannelConfig(max_queue_size=100001)
        
        # Invalid circuit breaker threshold
        with pytest.raises(ValidationError):
            ChannelConfig(circuit_breaker_threshold=0)
        
        # Invalid priority
        with pytest.raises(ValidationError):
            ChannelConfig(priority=0)
        
        with pytest.raises(ValidationError):
            ChannelConfig(priority=6)

    def test_channel_config_serialization(self):
        """Test channel configuration serialization"""
        config = ChannelConfig(
            max_queue_size=1500,
            circuit_breaker_threshold=8,
            priority=3
        )
        
        config_dict = config.to_dict()
        
        assert config_dict['max_queue_size'] == 1500
        assert config_dict['circuit_breaker_threshold'] == 8
        assert config_dict['priority'] == 3
        assert 'batching' in config_dict
        assert isinstance(config_dict['batching'], dict)

    def test_channel_config_from_dict(self):
        """Test channel configuration from dictionary"""
        config_dict = {
            'max_queue_size': 1200,
            'circuit_breaker_threshold': 15,
            'circuit_breaker_timeout': 45.0,
            'priority': 2,
            'batching': {
                'strategy': 'time_based',
                'max_batch_size': 30
            }
        }
        
        config = ChannelConfig.from_dict(config_dict)
        
        assert config.max_queue_size == 1200
        assert config.circuit_breaker_threshold == 15
        assert config.priority == 2
        assert config.batching.strategy == BatchingStrategy.TIME_BASED
        assert config.batching.max_batch_size == 30


class TestTickChannelConfig:
    """Test tick channel specific configuration"""

    def test_tick_config_defaults(self):
        """Test tick channel configuration defaults"""
        config = TickChannelConfig()
        
        # Base config defaults
        assert config.max_queue_size == 1000
        assert config.priority == 1
        
        # Tick-specific defaults
        assert config.highlow_detection is not None
        assert config.trend_detection is not None
        assert config.surge_detection is not None
        
        assert config.highlow_detection['enabled'] is True
        assert config.trend_detection['enabled'] is True
        assert config.surge_detection['enabled'] is True

    def test_tick_config_custom_detection_settings(self):
        """Test tick channel with custom detection settings"""
        highlow_config = {
            'enabled': True,
            'threshold_percentage': 0.02,
            'min_price_change': 0.50
        }
        
        trend_config = {
            'enabled': False,
            'window_sizes': [120, 300, 900],
            'min_trend_strength': 0.7
        }
        
        surge_config = {
            'enabled': True,
            'volume_multiplier': 4.0,
            'min_volume': 10000
        }
        
        config = TickChannelConfig(
            highlow_detection=highlow_config,
            trend_detection=trend_config,
            surge_detection=surge_config
        )
        
        assert config.highlow_detection['threshold_percentage'] == 0.02
        assert config.trend_detection['enabled'] is False
        assert config.surge_detection['volume_multiplier'] == 4.0

    def test_tick_config_validation(self):
        """Test tick channel configuration validation"""
        # Valid configuration
        TickChannelConfig()
        
        # Invalid detection config (should be dict)
        with pytest.raises(ValidationError):
            TickChannelConfig(highlow_detection="invalid")
        
        with pytest.raises(ValidationError):
            TickChannelConfig(trend_detection=123)
        
        # Missing enabled field in detection config
        with pytest.raises(ValidationError):
            TickChannelConfig(surge_detection={'volume_multiplier': 3.0})

    def test_tick_config_detection_methods(self):
        """Test tick channel detection configuration methods"""
        config = TickChannelConfig()
        
        # Test enable/disable methods
        config.enable_detection('highlow')
        assert config.highlow_detection['enabled'] is True
        
        config.disable_detection('trend')
        assert config.trend_detection['enabled'] is False
        
        # Test invalid detection type
        with pytest.raises(ValueError):
            config.enable_detection('invalid_type')

    def test_tick_config_serialization(self):
        """Test tick channel configuration serialization"""
        config = TickChannelConfig(
            max_queue_size=800,
            highlow_detection={'enabled': False, 'threshold': 0.03}
        )
        
        config_dict = config.to_dict()
        
        assert config_dict['max_queue_size'] == 800
        assert config_dict['highlow_detection']['enabled'] is False
        assert config_dict['highlow_detection']['threshold'] == 0.03


class TestOHLCVChannelConfig:
    """Test OHLCV channel specific configuration"""

    def test_ohlcv_config_defaults(self):
        """Test OHLCV channel configuration defaults"""
        config = OHLCVChannelConfig()
        
        # Should have higher priority for aggregated data
        assert config.priority == 2
        
        # OHLCV-specific settings
        assert config.aggregation_windows == [60, 300, 900]  # 1min, 5min, 15min
        assert config.enable_volume_analysis is True
        assert config.enable_price_momentum is True

    def test_ohlcv_config_custom_settings(self):
        """Test OHLCV channel with custom settings"""
        config = OHLCVChannelConfig(
            aggregation_windows=[30, 60, 180, 600],
            enable_volume_analysis=False,
            enable_price_momentum=False,
            volume_significance_threshold=50000
        )
        
        assert config.aggregation_windows == [30, 60, 180, 600]
        assert config.enable_volume_analysis is False
        assert config.enable_price_momentum is False
        assert config.volume_significance_threshold == 50000

    def test_ohlcv_config_validation(self):
        """Test OHLCV channel configuration validation"""
        # Valid configuration
        OHLCVChannelConfig()
        
        # Invalid aggregation windows
        with pytest.raises(ValidationError):
            OHLCVChannelConfig(aggregation_windows=[])
        
        with pytest.raises(ValidationError):
            OHLCVChannelConfig(aggregation_windows=[0, 60])
        
        # Invalid threshold
        with pytest.raises(ValidationError):
            OHLCVChannelConfig(volume_significance_threshold=-1000)


class TestFMVChannelConfig:
    """Test FMV channel specific configuration"""

    def test_fmv_config_defaults(self):
        """Test FMV channel configuration defaults"""
        config = FMVChannelConfig()
        
        # Lower priority for FMV data
        assert config.priority == 3
        
        # FMV-specific settings
        assert config.price_deviation_threshold == 0.05
        assert config.enable_arbitrage_detection is True
        assert config.min_market_cap == 1000000000  # 1B minimum

    def test_fmv_config_custom_settings(self):
        """Test FMV channel with custom settings"""
        config = FMVChannelConfig(
            price_deviation_threshold=0.03,
            enable_arbitrage_detection=False,
            min_market_cap=500000000,
            arbitrage_opportunity_threshold=0.02
        )
        
        assert config.price_deviation_threshold == 0.03
        assert config.enable_arbitrage_detection is False
        assert config.min_market_cap == 500000000
        assert config.arbitrage_opportunity_threshold == 0.02

    def test_fmv_config_validation(self):
        """Test FMV channel configuration validation"""
        # Valid configuration
        FMVChannelConfig()
        
        # Invalid deviation threshold
        with pytest.raises(ValidationError):
            FMVChannelConfig(price_deviation_threshold=0.0)
        
        with pytest.raises(ValidationError):
            FMVChannelConfig(price_deviation_threshold=1.1)
        
        # Invalid market cap
        with pytest.raises(ValidationError):
            FMVChannelConfig(min_market_cap=-100)


class TestChannelConfigFactory:
    """Test channel configuration factory"""

    def test_create_tick_config(self):
        """Test creating tick channel configuration"""
        config = ChannelConfigFactory.create_tick_config()
        
        assert isinstance(config, TickChannelConfig)
        assert config.priority == 1
        assert 'highlow_detection' in config.__dict__

    def test_create_ohlcv_config(self):
        """Test creating OHLCV channel configuration"""
        config = ChannelConfigFactory.create_ohlcv_config()
        
        assert isinstance(config, OHLCVChannelConfig)
        assert config.priority == 2
        assert hasattr(config, 'aggregation_windows')

    def test_create_fmv_config(self):
        """Test creating FMV channel configuration"""
        config = ChannelConfigFactory.create_fmv_config()
        
        assert isinstance(config, FMVChannelConfig)
        assert config.priority == 3
        assert hasattr(config, 'price_deviation_threshold')

    def test_create_config_with_overrides(self):
        """Test creating configuration with custom overrides"""
        overrides = {
            'max_queue_size': 2000,
            'priority': 4,
            'highlow_detection': {'enabled': False}
        }
        
        config = ChannelConfigFactory.create_tick_config(**overrides)
        
        assert config.max_queue_size == 2000
        assert config.priority == 4
        assert config.highlow_detection['enabled'] is False

    def test_create_config_from_dict(self):
        """Test creating configuration from dictionary"""
        config_dict = {
            'type': 'tick',
            'max_queue_size': 1500,
            'priority': 2,
            'batching': {
                'strategy': 'size_based',
                'max_batch_size': 20
            },
            'highlow_detection': {
                'enabled': True,
                'threshold': 0.025
            }
        }
        
        config = ChannelConfigFactory.from_dict(config_dict)
        
        assert isinstance(config, TickChannelConfig)
        assert config.max_queue_size == 1500
        assert config.batching.strategy == BatchingStrategy.SIZE_BASED
        assert config.highlow_detection['threshold'] == 0.025

    def test_create_config_invalid_type(self):
        """Test creating configuration with invalid type"""
        with pytest.raises(ValueError, match="Unknown channel type"):
            ChannelConfigFactory.from_dict({'type': 'invalid'})


class TestConfigurationIntegration:
    """Test configuration integration with external systems"""

    @patch('src.processing.channels.channel_config.ConfigManager')
    def test_load_from_config_manager(self, mock_config_manager):
        """Test loading configuration from ConfigManager"""
        # Mock ConfigManager response
        mock_config_manager.get_channel_config.return_value = {
            'tick': {
                'max_queue_size': 1200,
                'priority': 1,
                'highlow_detection': {'enabled': True, 'threshold': 0.02}
            }
        }
        
        config = ChannelConfigFactory.load_from_config_manager('tick')
        
        assert isinstance(config, TickChannelConfig)
        assert config.max_queue_size == 1200
        mock_config_manager.get_channel_config.assert_called_once_with('tick')

    def test_config_validation_with_environment(self):
        """Test configuration validation with environment-specific settings"""
        # Production-like config (stricter settings)
        prod_config = TickChannelConfig(
            max_queue_size=5000,
            circuit_breaker_threshold=20,
            circuit_breaker_timeout=120.0
        )
        
        # Development config (more lenient)
        dev_config = TickChannelConfig(
            max_queue_size=100,
            circuit_breaker_threshold=5,
            circuit_breaker_timeout=30.0
        )
        
        # Both should be valid
        assert prod_config.max_queue_size == 5000
        assert dev_config.max_queue_size == 100

    def test_config_immutability(self):
        """Test that configurations are properly immutable where needed"""
        config = TickChannelConfig()
        original_threshold = config.circuit_breaker_threshold
        
        # Create new config with changes (using dataclass replace)
        updated_config = replace(config, circuit_breaker_threshold=15)
        
        # Original should be unchanged
        assert config.circuit_breaker_threshold == original_threshold
        assert updated_config.circuit_breaker_threshold == 15

    def test_config_deep_copy_behavior(self):
        """Test that nested configurations are properly copied"""
        original_detection = {'enabled': True, 'threshold': 0.02}
        config1 = TickChannelConfig(highlow_detection=original_detection)
        config2 = replace(config1)
        
        # Modify nested dict in one config
        config1.highlow_detection['threshold'] = 0.05
        
        # Other config should be unaffected (deep copy)
        assert config2.highlow_detection['threshold'] == 0.02


class TestConfigurationPerformance:
    """Test configuration performance characteristics"""

    def test_config_creation_performance(self, performance_timer):
        """Test configuration creation performance"""
        performance_timer.start()
        
        # Create many configurations
        for _ in range(1000):
            TickChannelConfig()
            OHLCVChannelConfig() 
            FMVChannelConfig()
        
        performance_timer.stop()
        
        # Should be fast (< 0.5 seconds for 3000 configs)
        assert performance_timer.elapsed < 0.5

    def test_config_serialization_performance(self, performance_timer):
        """Test configuration serialization performance"""
        configs = [TickChannelConfig() for _ in range(100)]
        
        performance_timer.start()
        
        # Serialize all configurations
        for config in configs:
            config_dict = config.to_dict()
            ChannelConfigFactory.from_dict({
                'type': 'tick',
                **config_dict
            })
        
        performance_timer.stop()
        
        # Should complete quickly (< 0.1 seconds)
        assert performance_timer.elapsed < 0.1

    @pytest.mark.performance
    def test_config_validation_performance(self):
        """Test that validation doesn't significantly impact performance"""
        import time
        
        start_time = time.time()
        
        # Create many configurations (validation runs each time)
        for i in range(1000):
            TickChannelConfig(
                max_queue_size=500 + i,  # Different values to avoid caching
                circuit_breaker_threshold=5 + (i % 10)
            )
        
        elapsed = time.time() - start_time
        
        # Validation should be fast (< 1 second for 1000 validations)
        assert elapsed < 1.0


# Test markers
pytestmark = [
    pytest.mark.unit,
    pytest.mark.channels,
    pytest.mark.config
]