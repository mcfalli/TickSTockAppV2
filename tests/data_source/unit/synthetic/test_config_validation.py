"""
Unit tests for synthetic data configuration validation - Sprint 111

Tests configuration management, presets, interval controls, and validation
for the synthetic data processing system.
"""


import pytest

from src.core.services.config_manager import ConfigManager


class TestSyntheticDataConfiguration:
    """Unit tests for synthetic data configuration management."""

    @pytest.fixture
    def config_manager(self):
        """Create a ConfigManager instance for testing."""
        cm = ConfigManager()
        cm.load_from_env()
        return cm

    def test_synthetic_data_config_extraction(self, config_manager):
        """Test extraction of synthetic data configuration."""
        config = config_manager.get_synthetic_data_config()

        assert isinstance(config, dict)
        assert 'multi_frequency_enabled' in config
        assert 'per_second_enabled' in config
        assert 'per_minute_enabled' in config
        assert 'fair_value_enabled' in config
        assert 'validation_enabled' in config

    def test_configuration_presets_available(self, config_manager):
        """Test that all expected configuration presets are available."""
        presets = config_manager.get_synthetic_data_presets()

        expected_presets = [
            'development',
            'integration_testing',
            'performance_testing',
            'market_simulation',
            'minimal'
        ]

        for preset_name in expected_presets:
            assert preset_name in presets
            preset = presets[preset_name]
            assert 'description' in preset
            assert isinstance(preset['description'], str)

    def test_preset_application(self, config_manager):
        """Test applying configuration presets."""
        # Apply integration testing preset
        success = config_manager.apply_synthetic_data_preset('integration_testing')
        assert success is True

        # Verify specific settings were applied
        assert config_manager.config['ENABLE_MULTI_FREQUENCY'] is True
        assert config_manager.config['WEBSOCKET_PER_SECOND_ENABLED'] is True
        assert config_manager.config['WEBSOCKET_PER_MINUTE_ENABLED'] is True
        assert config_manager.config['WEBSOCKET_FAIR_VALUE_ENABLED'] is True

    def test_invalid_preset_handling(self, config_manager):
        """Test handling of invalid preset names."""
        success = config_manager.apply_synthetic_data_preset('nonexistent_preset')
        assert success is False

    def test_interval_controls(self, config_manager):
        """Test configurable interval controls."""
        # Test setting custom intervals
        success = config_manager.set_synthetic_data_intervals(
            per_second_interval=15.0,
            per_minute_interval=60,
            fmv_interval=30
        )
        assert success is True

        assert config_manager.config['SYNTHETIC_PER_SECOND_FREQUENCY'] == 15.0
        assert config_manager.config['SYNTHETIC_MINUTE_WINDOW'] == 60
        assert config_manager.config['SYNTHETIC_FMV_UPDATE_INTERVAL'] == 30

    def test_interval_validation(self, config_manager):
        """Test interval validation bounds."""
        # Test invalid per-second interval (too low)
        success = config_manager.set_synthetic_data_intervals(per_second_interval=0.05)
        assert success is False

        # Test invalid per-second interval (too high)
        success = config_manager.set_synthetic_data_intervals(per_second_interval=120.0)
        assert success is False

        # Test invalid FMV interval (too low)
        success = config_manager.set_synthetic_data_intervals(fmv_interval=2)
        assert success is False

        # Test invalid FMV interval (too high)
        success = config_manager.set_synthetic_data_intervals(fmv_interval=500)
        assert success is False

    def test_interval_presets(self, config_manager):
        """Test interval preset functionality."""
        presets = config_manager.get_common_interval_presets()

        expected_interval_presets = [
            'fast_15s',
            'standard_30s',
            'slow_60s',
            'mixed_intervals',
            'high_frequency'
        ]

        for preset_name in expected_interval_presets:
            assert preset_name in presets
            preset = presets[preset_name]
            assert 'description' in preset
            assert 'per_second_interval' in preset
            assert 'fmv_interval' in preset

    def test_interval_preset_application(self, config_manager):
        """Test applying interval presets."""
        success = config_manager.apply_interval_preset('fast_15s')
        assert success is True

        # Verify the 15-second preset was applied
        assert config_manager.config['SYNTHETIC_PER_SECOND_FREQUENCY'] == 15.0
        assert config_manager.config['SYNTHETIC_FMV_UPDATE_INTERVAL'] == 15

    def test_invalid_interval_preset(self, config_manager):
        """Test handling of invalid interval preset names."""
        success = config_manager.apply_interval_preset('nonexistent_interval')
        assert success is False

    def test_synthetic_data_validation_config(self, config_manager):
        """Test synthetic data validation configuration."""
        is_valid, errors = config_manager.validate_synthetic_data_config()

        # With default configuration, should be valid
        assert is_valid is True
        assert isinstance(errors, list)

    def test_validation_with_invalid_config(self, config_manager):
        """Test validation with invalid configuration."""
        # Set invalid frequency interval
        config_manager.config['SYNTHETIC_PER_SECOND_FREQUENCY'] = 100.0  # Too high

        is_valid, errors = config_manager.validate_synthetic_data_config()

        assert is_valid is False
        assert len(errors) > 0
        assert any('frequency' in error.lower() for error in errors)

    def test_multi_frequency_validation_no_active_frequencies(self, config_manager):
        """Test validation when multi-frequency enabled but no frequencies active."""
        # Enable multi-frequency but disable all frequencies
        config_manager.config['ENABLE_MULTI_FREQUENCY'] = True
        config_manager.config['WEBSOCKET_PER_SECOND_ENABLED'] = False
        config_manager.config['WEBSOCKET_PER_MINUTE_ENABLED'] = False
        config_manager.config['WEBSOCKET_FAIR_VALUE_ENABLED'] = False

        is_valid, errors = config_manager.validate_synthetic_data_config()

        assert is_valid is False
        assert any('no frequency streams are active' in error for error in errors)

    def test_correlation_parameter_validation(self, config_manager):
        """Test FMV correlation parameter validation."""
        # Test invalid correlation (too high)
        config_manager.config['SYNTHETIC_FMV_CORRELATION'] = 1.5

        is_valid, errors = config_manager.validate_synthetic_data_config()

        assert is_valid is False
        assert any('correlation' in error.lower() for error in errors)

        # Test invalid correlation (negative)
        config_manager.config['SYNTHETIC_FMV_CORRELATION'] = -0.1

        is_valid, errors = config_manager.validate_synthetic_data_config()

        assert is_valid is False
        assert any('correlation' in error.lower() for error in errors)

    def test_tolerance_parameter_validation(self, config_manager):
        """Test validation tolerance parameter bounds."""
        # Test invalid price tolerance (too high)
        config_manager.config['VALIDATION_PRICE_TOLERANCE'] = 0.5  # 50% is unrealistic

        is_valid, errors = config_manager.validate_synthetic_data_config()

        assert is_valid is False
        assert any('tolerance' in error.lower() for error in errors)

    def test_preset_consistency(self, config_manager):
        """Test that all presets produce valid configurations."""
        presets = config_manager.get_synthetic_data_presets()

        for preset_name in presets.keys():
            # Apply preset
            success = config_manager.apply_synthetic_data_preset(preset_name)
            assert success is True, f"Failed to apply preset: {preset_name}"

            # Validate resulting configuration
            is_valid, errors = config_manager.validate_synthetic_data_config()
            assert is_valid is True, f"Preset {preset_name} produces invalid config: {errors}"

    def test_interval_preset_consistency(self, config_manager):
        """Test that all interval presets produce valid configurations."""
        interval_presets = config_manager.get_common_interval_presets()

        for preset_name in interval_presets.keys():
            # Apply interval preset
            success = config_manager.apply_interval_preset(preset_name)
            assert success is True, f"Failed to apply interval preset: {preset_name}"

            # Validate resulting configuration
            is_valid, errors = config_manager.validate_synthetic_data_config()
            assert is_valid is True, f"Interval preset {preset_name} produces invalid config: {errors}"

    def test_configuration_boundary_conditions(self, config_manager):
        """Test configuration at boundary conditions."""
        # Test minimum valid values
        success = config_manager.set_synthetic_data_intervals(
            per_second_interval=0.1,    # Minimum
            per_minute_interval=30,     # Minimum
            fmv_interval=5              # Minimum
        )
        assert success is True

        is_valid, errors = config_manager.validate_synthetic_data_config()
        assert is_valid is True

        # Test maximum valid values
        success = config_manager.set_synthetic_data_intervals(
            per_second_interval=60.0,   # Maximum
            per_minute_interval=300,    # Maximum
            fmv_interval=300            # Maximum
        )
        assert success is True

        is_valid, errors = config_manager.validate_synthetic_data_config()
        assert is_valid is True

    def test_preset_parameter_coverage(self, config_manager):
        """Test that presets cover all necessary configuration parameters."""
        presets = config_manager.get_synthetic_data_presets()

        required_params = [
            'ENABLE_MULTI_FREQUENCY',
            'WEBSOCKET_PER_SECOND_ENABLED',
            'WEBSOCKET_PER_MINUTE_ENABLED',
            'WEBSOCKET_FAIR_VALUE_ENABLED'
        ]

        for preset_name, preset in presets.items():
            for param in required_params:
                # Skip description field
                if param != 'description':
                    # Either the preset should have the param, or it's optional
                    if param in ['WEBSOCKET_PER_MINUTE_ENABLED', 'WEBSOCKET_FAIR_VALUE_ENABLED']:
                        # These can be omitted for minimal presets
                        continue
                    # Core params should be present
                    assert param in preset, f"Preset {preset_name} missing required param: {param}"
