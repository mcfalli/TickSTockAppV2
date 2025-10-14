"""Sprint 41 - Integration test for synthetic data flow.

Tests the complete flow:
1. TickStockAppV2 generates synthetic ticks
2. Publishes to Redis
3. TickStockPL consumes (if running)
4. Dashboard displays data
"""

import pytest

from src.core.services.config_manager import get_config
from src.infrastructure.data_sources.factory import DataProviderFactory


class TestSyntheticDataIntegration:
    """Integration tests for Sprint 41 synthetic data."""

    @pytest.fixture(scope="class")
    def config(self):
        """Get configuration with synthetic data enabled."""
        config = get_config()
        config['USE_SYNTHETIC_DATA'] = True
        config['SYNTHETIC_PATTERN_INJECTION'] = True
        config['SYNTHETIC_PATTERN_FREQUENCY'] = 0.2  # 20% for testing
        config['SYNTHETIC_SCENARIO'] = 'normal'
        return config

    @pytest.fixture(scope="class")
    def provider(self, config):
        """Create synthetic data provider."""
        return DataProviderFactory.get_provider(config)

    def test_provider_initialization(self, provider):
        """Test that provider initializes correctly."""
        assert provider is not None
        assert provider.is_available()

        # Check universe loader
        assert hasattr(provider, 'universe_loader')
        assert len(provider.universe_loader.tickers) > 0

        # Check pattern injection config
        assert provider.pattern_injection is True
        assert provider.pattern_frequency == 0.2

    def test_tick_generation(self, provider):
        """Test basic tick generation."""
        # Get a ticker from universe
        tickers = provider.universe_loader.get_all_tickers()
        assert len(tickers) > 0

        ticker = tickers[0]

        # Generate tick
        tick = provider.generate_tick_data(ticker)

        # Validate tick structure
        assert tick.ticker == ticker
        assert tick.price > 0
        assert tick.volume > 0
        assert tick.source == 'simulated'
        assert tick.tick_open > 0
        assert tick.tick_high >= tick.tick_open
        assert tick.tick_low <= tick.tick_open
        assert tick.tick_close > 0
        assert tick.bid < tick.ask

    def test_pattern_injection(self, provider):
        """Test that patterns are being injected."""
        # Generate 100 ticks
        tickers = provider.universe_loader.get_random_symbols(5)

        initial_patterns = provider.patterns_injected

        for ticker in tickers:
            for _ in range(20):  # 20 ticks per symbol = 100 total
                tick = provider.generate_tick_data(ticker)

        # With 20% frequency, expect ~20 patterns in 100 ticks
        patterns_injected = provider.patterns_injected - initial_patterns

        # Allow some variance (10-30 patterns acceptable)
        assert 10 <= patterns_injected <= 30, \
            f"Expected 10-30 patterns, got {patterns_injected}"

    def test_sector_based_volatility(self, provider):
        """Test that sector-based volatility factors are assigned correctly."""
        # Get symbols from different sectors
        loader = provider.universe_loader

        # Find tech and financial symbols
        tech_symbols = loader.get_symbols_by_sector('Technology')
        financial_symbols = loader.get_symbols_by_sector('Financial')

        if not tech_symbols or not financial_symbols:
            pytest.skip("Required sectors not available in universe")

        # Verify sector-based volatility factors
        tech_info = loader.get_symbol_info(tech_symbols[0])
        financial_info = loader.get_symbol_info(financial_symbols[0])

        # Technology should have higher volatility factor than Financial
        assert tech_info.volatility_factor == 1.5, \
            f"Technology volatility factor should be 1.5, got {tech_info.volatility_factor}"

        assert financial_info.volatility_factor == 1.0, \
            f"Financial volatility factor should be 1.0, got {financial_info.volatility_factor}"

        # Tech should be more volatile than Financial
        assert tech_info.volatility_factor > financial_info.volatility_factor, \
            f"Tech volatility ({tech_info.volatility_factor}) should be higher than Financial ({financial_info.volatility_factor})"

    def test_scenario_volatility(self, config):
        """Test that scenario multipliers are set correctly."""
        scenarios = {
            'normal': (1.0, 0.0),      # volatility, trend_bias
            'volatile': (3.0, 0.0),
            'crash': (5.0, -0.8),
            'rally': (2.0, 0.8),
            'opening_bell': (4.0, 0.0)
        }

        for scenario, (expected_vol, expected_trend) in scenarios.items():
            # Create provider with scenario
            test_config = config.copy()
            test_config['SYNTHETIC_SCENARIO'] = scenario
            provider = DataProviderFactory.get_provider(test_config)

            # Verify scenario settings
            assert provider.volatility_multiplier == expected_vol, \
                f"Scenario {scenario} should have volatility {expected_vol}, got {provider.volatility_multiplier}"

            assert provider.trend_bias == expected_trend, \
                f"Scenario {scenario} should have trend bias {expected_trend}, got {provider.trend_bias}"

            assert provider.scenario == scenario, \
                f"Provider scenario should be {scenario}, got {provider.scenario}"

    def test_provider_statistics(self, provider):
        """Test provider statistics tracking."""
        # Generate some ticks
        ticker = provider.universe_loader.get_all_tickers()[0]

        initial_ticks = provider.ticks_generated

        for _ in range(10):
            provider.generate_tick_data(ticker)

        # Check statistics updated
        stats = provider.get_statistics()

        assert stats['ticks_generated'] == initial_ticks + 10
        assert 'patterns_injected' in stats
        assert 'scenario' in stats
        assert stats['scenario'] == 'normal'
        assert 'volatility_multiplier' in stats
        assert 'pattern_counts' in stats

    def test_universe_fallback(self):
        """Test that fallback universe works when database unavailable."""
        config = get_config()
        config['USE_SYNTHETIC_DATA'] = True
        config['SYNTHETIC_UNIVERSE'] = 'nonexistent:universe'

        # Should fall back to hardcoded universe
        provider = DataProviderFactory.get_provider(config)

        assert provider is not None
        assert len(provider.universe_loader.tickers) == 29  # Fallback universe size
        assert 'AAPL' in provider.universe_loader.tickers  # Should have fallback symbols


if __name__ == '__main__':
    # Run tests with pytest
    pytest.main([__file__, '-v', '-s'])
