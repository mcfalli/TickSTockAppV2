"""
Unit tests for SimulatedDataProvider - Sprint 111

Tests synthetic data provider implementation for multi-frequency generation,
configuration controls, and data validation.
"""

import time
from unittest.mock import patch

import pytest
from src.infrastructure.data_sources.synthetic.types import DataFrequency

from src.core.domain.market.tick import TickData
from src.infrastructure.data_sources.synthetic.provider import SimulatedDataProvider


class TestSimulatedDataProvider:
    """Unit tests for SimulatedDataProvider functionality."""

    @pytest.fixture
    def base_config(self):
        """Basic configuration for testing."""
        return {
            'ENABLE_MULTI_FREQUENCY': True,
            'WEBSOCKET_PER_SECOND_ENABLED': True,
            'WEBSOCKET_PER_MINUTE_ENABLED': False,
            'WEBSOCKET_FAIR_VALUE_ENABLED': False,
            'MARKET_TIMEZONE': 'US/Eastern',
            'SYNTHETIC_ACTIVITY_LEVEL': 'medium'
        }

    @pytest.fixture
    def full_config(self):
        """Full multi-frequency configuration."""
        return {
            'ENABLE_MULTI_FREQUENCY': True,
            'WEBSOCKET_PER_SECOND_ENABLED': True,
            'WEBSOCKET_PER_MINUTE_ENABLED': True,
            'WEBSOCKET_FAIR_VALUE_ENABLED': True,
            'MARKET_TIMEZONE': 'US/Eastern',
            'SYNTHETIC_ACTIVITY_LEVEL': 'medium'
        }

    def test_provider_initialization_single_frequency(self, base_config):
        """Test provider initializes correctly with single frequency."""
        provider = SimulatedDataProvider(base_config)

        assert provider is not None
        supported_frequencies = provider.get_supported_frequencies()
        assert len(supported_frequencies) == 1
        assert DataFrequency.PER_SECOND in supported_frequencies

    def test_provider_initialization_multi_frequency(self, full_config):
        """Test provider initializes correctly with multiple frequencies."""
        provider = SimulatedDataProvider(full_config)

        assert provider is not None
        supported_frequencies = provider.get_supported_frequencies()
        assert len(supported_frequencies) == 3
        assert DataFrequency.PER_SECOND in supported_frequencies
        assert DataFrequency.PER_MINUTE in supported_frequencies
        assert DataFrequency.FAIR_VALUE in supported_frequencies

    def test_frequency_support_checks(self, full_config):
        """Test frequency support checking methods."""
        provider = SimulatedDataProvider(full_config)

        assert provider.has_frequency_support(DataFrequency.PER_SECOND) is True
        assert provider.has_frequency_support(DataFrequency.PER_MINUTE) is True
        assert provider.has_frequency_support(DataFrequency.FAIR_VALUE) is True

    def test_per_second_data_generation(self, base_config):
        """Test per-second tick data generation."""
        provider = SimulatedDataProvider(base_config)

        tick_data = provider.generate_frequency_data('AAPL', DataFrequency.PER_SECOND)

        assert isinstance(tick_data, TickData)
        assert tick_data.ticker == 'AAPL'
        assert tick_data.price > 0
        assert tick_data.volume > 0
        assert tick_data.source == 'simulated_per_second'
        assert tick_data.event_type == 'A'

    def test_per_minute_data_generation(self, full_config):
        """Test per-minute aggregate data generation."""
        provider = SimulatedDataProvider(full_config)

        minute_data = provider.generate_frequency_data('AAPL', DataFrequency.PER_MINUTE)

        assert isinstance(minute_data, dict)
        assert minute_data.get('ev') == 'AM'
        assert minute_data.get('sym') == 'AAPL'
        assert minute_data.get('o') is not None  # Open
        assert minute_data.get('h') is not None  # High
        assert minute_data.get('l') is not None  # Low
        assert minute_data.get('c') is not None  # Close
        assert minute_data.get('v') > 0  # Volume
        assert minute_data.get('vw') is not None  # VWAP

    def test_fmv_data_generation(self, full_config):
        """Test Fair Market Value data generation."""
        provider = SimulatedDataProvider(full_config)

        fmv_data = provider.generate_frequency_data('AAPL', DataFrequency.FAIR_VALUE)

        assert isinstance(fmv_data, dict)
        assert fmv_data.get('ev') == 'FMV'
        assert fmv_data.get('sym') == 'AAPL'
        assert fmv_data.get('fmv') > 0  # Fair Market Value
        assert fmv_data.get('mp') > 0   # Market Price
        assert fmv_data.get('pd') is not None  # Premium/Discount
        assert 0 <= fmv_data.get('conf') <= 1   # Confidence score

    def test_unsupported_frequency_error(self, base_config):
        """Test error handling for unsupported frequencies."""
        # Configure for per-second only
        provider = SimulatedDataProvider(base_config)

        with pytest.raises(ValueError, match="No generator available for frequency"):
            provider.generate_frequency_data('AAPL', DataFrequency.PER_MINUTE)

    def test_data_validation_enabled(self, full_config):
        """Test data consistency validation when enabled."""
        full_config['ENABLE_SYNTHETIC_DATA_VALIDATION'] = True
        provider = SimulatedDataProvider(full_config)

        assert provider._enable_validation is True
        assert provider._validator is not None

    def test_data_validation_disabled(self, base_config):
        """Test validation system when disabled."""
        base_config['ENABLE_SYNTHETIC_DATA_VALIDATION'] = False
        provider = SimulatedDataProvider(base_config)

        assert provider._enable_validation is False

    def test_generation_statistics(self, full_config):
        """Test generation statistics tracking."""
        provider = SimulatedDataProvider(full_config)

        # Generate some data
        provider.generate_frequency_data('AAPL', DataFrequency.PER_SECOND)
        provider.generate_frequency_data('AAPL', DataFrequency.PER_MINUTE)

        stats = provider.get_generation_statistics()

        assert 'total_legacy_ticks' in stats
        assert 'frequencies' in stats
        assert 'active_generators' in stats
        assert isinstance(stats['frequencies'], dict)

    def test_legacy_fallback(self, base_config):
        """Test legacy tick generation fallback."""
        provider = SimulatedDataProvider(base_config)

        # Test legacy method directly
        tick_data = provider._generate_legacy_tick_data('TSLA')

        assert isinstance(tick_data, TickData)
        assert tick_data.ticker == 'TSLA'
        assert tick_data.source == 'simulated'

    def test_market_status_integration(self, base_config):
        """Test market status affects data generation."""
        provider = SimulatedDataProvider(base_config)

        market_status = provider.get_market_status()
        assert market_status in ['REGULAR', 'PRE', 'AFTER', 'CLOSED']

        tick_data = provider.generate_frequency_data('AAPL', DataFrequency.PER_SECOND)
        assert tick_data.market_status == market_status

    def test_ticker_price_consistency(self, base_config):
        """Test price generation consistency for same ticker."""
        provider = SimulatedDataProvider(base_config)

        price1 = provider.get_ticker_price('AAPL')
        time.sleep(0.1)  # Short delay
        price2 = provider.get_ticker_price('AAPL')

        # Prices should be similar but can vary slightly
        assert abs(price1 - price2) / price1 < 0.1  # Within 10%

    def test_configuration_parameter_usage(self, base_config):
        """Test that configuration parameters are properly used."""
        base_config['SYNTHETIC_ACTIVITY_LEVEL'] = 'high'
        provider = SimulatedDataProvider(base_config)

        tick_data = provider.generate_frequency_data('AAPL', DataFrequency.PER_SECOND)

        # Higher activity should generally result in higher volumes
        assert tick_data.volume > 1000

    @patch('src.infrastructure.data_sources.synthetic.provider.time.time')
    def test_rate_limiting(self, mock_time, base_config):
        """Test price generation rate limiting."""
        provider = SimulatedDataProvider(base_config)

        # Mock time to simulate rapid calls
        mock_time.return_value = 1000.0
        price1 = provider.get_ticker_price('AAPL')

        # Same time - should return cached price
        price2 = provider.get_ticker_price('AAPL')
        assert price1 == price2

        # Later time - should generate new price
        mock_time.return_value = 1000.3  # 0.3 seconds later
        price3 = provider.get_ticker_price('AAPL')
        # Allow for potential same price due to randomness
        # Just verify it completed without error
        assert price3 > 0
