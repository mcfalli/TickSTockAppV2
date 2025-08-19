"""
Test fixtures for multi-frequency synthetic data generation.

Provides comprehensive fixtures for testing the Sprint 102 synthetic data system,
including frequency-specific generators, validation systems, and configuration presets.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

# Import synthetic data types
try:
    from src.infrastructure.data_sources.synthetic.types import DataFrequency, FrequencyGenerator
except ImportError:
    # Mock types if not available
    from enum import Enum
    
    class DataFrequency(Enum):
        PER_SECOND = "per_second"
        PER_MINUTE = "per_minute"
        FAIR_VALUE = "fair_value"
    
    class FrequencyGenerator:
        pass

# Import synthetic data components
try:
    from src.infrastructure.data_sources.synthetic.provider import SimulatedDataProvider
    from src.infrastructure.data_sources.synthetic.generators.per_second_generator import PerSecondGenerator
    from src.infrastructure.data_sources.synthetic.generators.per_minute_generator import PerMinuteGenerator
    from src.infrastructure.data_sources.synthetic.generators.fmv_generator import FMVGenerator
    from src.infrastructure.data_sources.synthetic.validators.data_consistency import DataConsistencyValidator
except ImportError:
    # Mock components if not available
    SimulatedDataProvider = Mock
    PerSecondGenerator = Mock
    PerMinuteGenerator = Mock
    FMVGenerator = Mock
    DataConsistencyValidator = Mock

try:
    from src.core.domain.market.tick import TickData
except ImportError:
    TickData = Mock


@dataclass
class SyntheticTestScenario:
    """Represents a test scenario with specific configuration and expected behavior."""
    name: str
    description: str
    config: Dict[str, Any]
    expected_frequencies: List[DataFrequency]
    expected_generation_count: int
    expected_validation_enabled: bool
    test_duration_seconds: float = 5.0


class SyntheticDataBuilder:
    """Builder for creating synthetic data test scenarios."""
    
    @staticmethod
    def create_per_second_tick(
        ticker: str = "AAPL",
        price: float = 150.0,
        volume: int = 10000,
        timestamp: Optional[float] = None
    ) -> Dict[str, Any]:
        """Create mock per-second tick data."""
        if timestamp is None:
            timestamp = time.time()
        
        return {
            'ticker': ticker,
            'price': price,
            'volume': volume,
            'timestamp': timestamp,
            'source': 'simulated',
            'event_type': 'A',
            'market_status': 'REGULAR',
            'bid': round(price * 0.999, 2),
            'ask': round(price * 1.001, 2),
            'tick_open': round(price * 0.999, 2),
            'tick_high': round(price * 1.002, 2),
            'tick_low': round(price * 0.998, 2),
            'tick_close': price,
            'tick_volume': volume,
            'tick_vwap': round(price * 1.0005, 2),
            'vwap': round(price * 1.0005, 2),
            'tick_start_timestamp': timestamp - 1,
            'tick_end_timestamp': timestamp
        }
    
    @staticmethod
    def create_per_minute_bar(
        ticker: str = "AAPL",
        open_price: float = 149.5,
        high_price: float = 150.5,
        low_price: float = 149.0,
        close_price: float = 150.0,
        volume: int = 50000,
        timestamp: Optional[float] = None
    ) -> Dict[str, Any]:
        """Create mock per-minute OHLCV bar."""
        if timestamp is None:
            timestamp = time.time()
        
        # Calculate VWAP (simple approximation)
        vwap = (open_price + high_price + low_price + close_price) / 4
        
        return {
            'ev': 'AM',  # Polygon aggregate minute event
            'sym': ticker,
            'o': open_price,
            'h': high_price,
            'l': low_price,
            'c': close_price,
            'v': volume,
            'vw': round(vwap, 2),
            'av': volume * 5,  # Accumulated volume
            'op': open_price - 1.0,  # Daily open (approximate)
            'a': round(vwap * 1.001, 2),  # Daily VWAP
            'z': volume // 100,  # Average trade size
            's': int((timestamp - 60) * 1000),  # Start timestamp (ms)
            'e': int(timestamp * 1000),  # End timestamp (ms)
            'timestamp': timestamp,
            'source': 'synthetic_per_minute'
        }
    
    @staticmethod
    def create_fmv_update(
        ticker: str = "AAPL",
        fmv_price: float = 150.25,
        market_price: float = 150.00,
        confidence: float = 0.85,
        timestamp: Optional[float] = None
    ) -> Dict[str, Any]:
        """Create mock Fair Market Value update."""
        if timestamp is None:
            timestamp = time.time()
        
        premium_discount = (fmv_price - market_price) / market_price
        
        return {
            'ev': 'FMV',
            'sym': ticker,
            'fmv': round(fmv_price, 4),
            'mp': round(market_price, 4),
            'pd': round(premium_discount, 6),
            'conf': round(confidence, 4),
            't': int(timestamp * 1000),
            'source': 'simulated_fmv',
            'market_status': 'REGULAR',
            'session_adj': 0.0,
            'trend_momentum': 0.0,
            'update_interval': 30
        }
    
    @staticmethod
    def create_validation_result(
        is_valid: bool = True,
        errors: Optional[List[str]] = None,
        warnings: Optional[List[str]] = None,
        metrics: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """Create mock validation result."""
        return {
            'is_valid': is_valid,
            'errors': errors or [],
            'warnings': warnings or [],
            'metrics': metrics or {},
            'validation_time': 0.001
        }


@pytest.fixture
def synthetic_data_builder():
    """Provide SyntheticDataBuilder for test methods."""
    return SyntheticDataBuilder()


@pytest.fixture
def basic_synthetic_config():
    """Basic configuration for synthetic data generation."""
    return {
        'ENABLE_MULTI_FREQUENCY': False,
        'WEBSOCKET_PER_SECOND_ENABLED': True,
        'WEBSOCKET_PER_MINUTE_ENABLED': False,
        'WEBSOCKET_FAIR_VALUE_ENABLED': False,
        'SYNTHETIC_ACTIVITY_LEVEL': 'medium',
        'ENABLE_SYNTHETIC_DATA_VALIDATION': True,
        'MARKET_TIMEZONE': 'US/Eastern'
    }


@pytest.fixture
def multi_frequency_synthetic_config():
    """Multi-frequency configuration for comprehensive testing."""
    return {
        'ENABLE_MULTI_FREQUENCY': True,
        'WEBSOCKET_PER_SECOND_ENABLED': True,
        'WEBSOCKET_PER_MINUTE_ENABLED': True,
        'WEBSOCKET_FAIR_VALUE_ENABLED': True,
        'SYNTHETIC_ACTIVITY_LEVEL': 'high',
        'ENABLE_SYNTHETIC_DATA_VALIDATION': True,
        'MARKET_TIMEZONE': 'US/Eastern',
        
        # Per-second settings
        'SYNTHETIC_PER_SECOND_FREQUENCY': 1.0,
        'SYNTHETIC_PER_SECOND_PRICE_VARIANCE': 0.001,
        'SYNTHETIC_PER_SECOND_VOLUME_RANGE': [10000, 100000],
        
        # Per-minute settings
        'SYNTHETIC_PER_MINUTE_WINDOW': 60,
        'SYNTHETIC_PER_MINUTE_MIN_TICKS': 5,
        'SYNTHETIC_PER_MINUTE_MAX_TICKS': 30,
        'SYNTHETIC_PER_MINUTE_OHLC_VARIANCE': 0.005,
        'SYNTHETIC_PER_MINUTE_VOLUME_MULTIPLIER': 5.0,
        
        # FMV settings
        'SYNTHETIC_FMV_UPDATE_INTERVAL': 30,
        'SYNTHETIC_FMV_CORRELATION': 0.85,
        'SYNTHETIC_FMV_VARIANCE': 0.002,
        'SYNTHETIC_FMV_PREMIUM_RANGE': 0.01,
        'SYNTHETIC_FMV_MOMENTUM_DECAY': 0.7,
        'SYNTHETIC_FMV_LAG_FACTOR': 0.3,
        'SYNTHETIC_FMV_VOLATILITY_DAMPENING': 0.6,
        'SYNTHETIC_FMV_TRENDING_CORRELATION': 0.90,
        'SYNTHETIC_FMV_SIDEWAYS_CORRELATION': 0.75,
        'SYNTHETIC_FMV_VOLATILE_CORRELATION': 0.65,
        
        # Validation settings
        'VALIDATION_PRICE_TOLERANCE': 0.001,
        'VALIDATION_VOLUME_TOLERANCE': 0.05,
        'VALIDATION_VWAP_TOLERANCE': 0.002
    }


@pytest.fixture
def performance_test_config():
    """High-frequency configuration for performance testing."""
    return {
        'ENABLE_MULTI_FREQUENCY': True,
        'WEBSOCKET_PER_SECOND_ENABLED': True,
        'WEBSOCKET_PER_MINUTE_ENABLED': True,
        'WEBSOCKET_FAIR_VALUE_ENABLED': True,
        'SYNTHETIC_ACTIVITY_LEVEL': 'opening_bell',
        'ENABLE_SYNTHETIC_DATA_VALIDATION': False,  # Disable for performance
        'MARKET_TIMEZONE': 'US/Eastern',
        'SYNTHETIC_PER_SECOND_FREQUENCY': 0.1,  # 10x per second
        'SYNTHETIC_FMV_UPDATE_INTERVAL': 5,  # Every 5 seconds
        'SYNTHETIC_PER_MINUTE_MAX_TICKS': 50
    }


@pytest.fixture
def test_scenarios():
    """Predefined test scenarios for comprehensive coverage."""
    return [
        SyntheticTestScenario(
            name="single_frequency_basic",
            description="Basic single-frequency per-second generation",
            config={
                'ENABLE_MULTI_FREQUENCY': False,
                'WEBSOCKET_PER_SECOND_ENABLED': True,
                'SYNTHETIC_ACTIVITY_LEVEL': 'low',
                'ENABLE_SYNTHETIC_DATA_VALIDATION': False
            },
            expected_frequencies=[DataFrequency.PER_SECOND],
            expected_generation_count=5,
            expected_validation_enabled=False
        ),
        SyntheticTestScenario(
            name="multi_frequency_full",
            description="Full multi-frequency generation with validation",
            config={
                'ENABLE_MULTI_FREQUENCY': True,
                'WEBSOCKET_PER_SECOND_ENABLED': True,
                'WEBSOCKET_PER_MINUTE_ENABLED': True,
                'WEBSOCKET_FAIR_VALUE_ENABLED': True,
                'SYNTHETIC_ACTIVITY_LEVEL': 'high',
                'ENABLE_SYNTHETIC_DATA_VALIDATION': True,
                'SYNTHETIC_PER_SECOND_FREQUENCY': 0.5,
                'SYNTHETIC_FMV_UPDATE_INTERVAL': 2.0
            },
            expected_frequencies=[
                DataFrequency.PER_SECOND,
                DataFrequency.PER_MINUTE,
                DataFrequency.FAIR_VALUE
            ],
            expected_generation_count=15,  # Higher due to multiple frequencies
            expected_validation_enabled=True
        ),
        SyntheticTestScenario(
            name="validation_focused",
            description="Multi-frequency with strict validation settings",
            config={
                'ENABLE_MULTI_FREQUENCY': True,
                'WEBSOCKET_PER_SECOND_ENABLED': True,
                'WEBSOCKET_PER_MINUTE_ENABLED': True,
                'ENABLE_SYNTHETIC_DATA_VALIDATION': True,
                'VALIDATION_PRICE_TOLERANCE': 0.0005,  # Stricter
                'VALIDATION_VOLUME_TOLERANCE': 0.02,   # Stricter
                'SYNTHETIC_ACTIVITY_LEVEL': 'medium'
            },
            expected_frequencies=[DataFrequency.PER_SECOND, DataFrequency.PER_MINUTE],
            expected_generation_count=8,
            expected_validation_enabled=True,
            test_duration_seconds=3.0
        )
    ]


@pytest.fixture
def mock_synthetic_provider(multi_frequency_synthetic_config):
    """Mock SimulatedDataProvider with controlled behavior."""
    provider = Mock(spec=SimulatedDataProvider)
    provider.config = multi_frequency_synthetic_config
    provider.generation_stats = {
        'per_second': {'count': 0, 'last_log': time.time()},
        'per_minute': {'count': 0, 'last_log': time.time()},
        'fair_value': {'count': 0, 'last_log': time.time()}
    }
    provider.ticks_generated = 0
    provider.last_price = {'AAPL': 150.0, 'GOOGL': 2500.0, 'MSFT': 300.0}
    provider.get_market_status.return_value = 'REGULAR'
    provider.get_ticker_price.return_value = 150.0
    provider.validate_tick_data.return_value = True
    provider.is_available.return_value = True
    return provider


@pytest.fixture
def mock_per_second_generator(basic_synthetic_config, synthetic_data_builder):
    """Mock PerSecondGenerator with controlled tick generation."""
    generator = Mock(spec=PerSecondGenerator)
    generator.config = basic_synthetic_config
    generator.generation_count = 0
    generator.supports_frequency.return_value = True
    
    def generate_data(ticker: str, config: Dict[str, Any]):
        generator.generation_count += 1
        return synthetic_data_builder.create_per_second_tick(ticker=ticker)
    
    generator.generate_data.side_effect = generate_data
    generator.get_generation_stats.return_value = {
        'type': 'per_second',
        'total_generated': generator.generation_count
    }
    return generator


@pytest.fixture
def mock_per_minute_generator(multi_frequency_synthetic_config, synthetic_data_builder):
    """Mock PerMinuteGenerator with controlled bar generation."""
    generator = Mock(spec=PerMinuteGenerator)
    generator.config = multi_frequency_synthetic_config
    generator.generation_count = 0
    generator.supports_frequency.return_value = True
    
    def generate_data(ticker: str, config: Dict[str, Any]):
        generator.generation_count += 1
        return synthetic_data_builder.create_per_minute_bar(ticker=ticker)
    
    generator.generate_data.side_effect = generate_data
    generator.get_generation_stats.return_value = {
        'type': 'per_minute',
        'total_generated': generator.generation_count
    }
    return generator


@pytest.fixture
def mock_fmv_generator(multi_frequency_synthetic_config, synthetic_data_builder):
    """Mock FMVGenerator with controlled FMV generation."""
    generator = Mock(spec=FMVGenerator)
    generator.config = multi_frequency_synthetic_config
    generator.generation_count = 0
    generator.supports_frequency.return_value = True
    
    def generate_data(ticker: str, config: Dict[str, Any]):
        generator.generation_count += 1
        return synthetic_data_builder.create_fmv_update(ticker=ticker)
    
    generator.generate_data.side_effect = generate_data
    generator.get_current_fmv.return_value = 150.25
    generator.get_generation_stats.return_value = {
        'type': 'fair_market_value',
        'total_generated': generator.generation_count,
        'enhanced_correlation': {
            'trending_correlation': 0.90,
            'sideways_correlation': 0.75,
            'volatile_correlation': 0.65
        }
    }
    generator.get_correlation_analysis.return_value = {
        'ticker': 'AAPL',
        'current_fmv': 150.25,
        'market_regime': 'sideways',
        'adjusted_correlation': 0.75,
        'realized_correlation': 0.73
    }
    return generator


@pytest.fixture
def mock_data_validator(synthetic_data_builder):
    """Mock DataConsistencyValidator with controlled validation behavior."""
    validator = Mock(spec=DataConsistencyValidator)
    validator.validation_count = 0
    
    def validate_minute_bar(ticker: str, minute_bar: Dict[str, Any]):
        validator.validation_count += 1
        # Return valid by default, can be overridden in tests
        return synthetic_data_builder.create_validation_result(is_valid=True)
    
    def validate_fmv_correlation(ticker: str, fmv_update: Dict[str, Any]):
        validator.validation_count += 1
        return synthetic_data_builder.create_validation_result(is_valid=True)
    
    validator.validate_minute_bar_consistency.side_effect = validate_minute_bar
    validator.validate_fmv_correlation.side_effect = validate_fmv_correlation
    validator.add_tick_data.return_value = None
    validator.add_minute_bar.return_value = None
    validator.add_fmv_update.return_value = None
    validator.get_validation_summary.return_value = {
        'total_validations': validator.validation_count,
        'success_rate': 1.0,
        'average_validation_time': 0.001,
        'common_errors': []
    }
    return validator


@pytest.fixture
def synthetic_test_tickers():
    """Standard set of tickers for synthetic data testing."""
    return ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN"]


@pytest.fixture
def multi_frequency_test_runner(mock_synthetic_provider):
    """Test runner for multi-frequency scenarios."""
    class TestRunner:
        def __init__(self, provider):
            self.provider = provider
            self.results = []
        
        def run_scenario(self, scenario: SyntheticTestScenario, tickers: List[str]):
            """Run a test scenario and collect results."""
            start_time = time.time()
            generation_count = 0
            
            # Apply scenario configuration
            self.provider.config.update(scenario.config)
            
            # Simulate data generation for the scenario duration
            while time.time() - start_time < scenario.test_duration_seconds:
                for ticker in tickers:
                    for frequency in scenario.expected_frequencies:
                        try:
                            data = self.provider.generate_frequency_data(ticker, frequency)
                            if data:
                                generation_count += 1
                        except Exception as e:
                            pass  # Continue testing even if some generation fails
                time.sleep(0.1)  # Small delay between generations
            
            result = {
                'scenario': scenario,
                'duration': time.time() - start_time,
                'generation_count': generation_count,
                'success': generation_count >= scenario.expected_generation_count
            }
            self.results.append(result)
            return result
        
        def get_summary(self):
            """Get summary of all test runs."""
            if not self.results:
                return {'total_scenarios': 0, 'success_rate': 0.0}
            
            successful = sum(1 for r in self.results if r['success'])
            return {
                'total_scenarios': len(self.results),
                'successful_scenarios': successful,
                'success_rate': successful / len(self.results),
                'total_generations': sum(r['generation_count'] for r in self.results)
            }
    
    return TestRunner(mock_synthetic_provider)


# Utility fixtures for specific test needs
@pytest.fixture
def rapid_generation_config():
    """Configuration for rapid data generation testing."""
    return {
        'ENABLE_MULTI_FREQUENCY': True,
        'WEBSOCKET_PER_SECOND_ENABLED': True,
        'WEBSOCKET_PER_MINUTE_ENABLED': True,
        'WEBSOCKET_FAIR_VALUE_ENABLED': True,
        'SYNTHETIC_PER_SECOND_FREQUENCY': 0.01,  # 100x per second
        'SYNTHETIC_FMV_UPDATE_INTERVAL': 0.5,    # Every 0.5 seconds
        'ENABLE_SYNTHETIC_DATA_VALIDATION': False  # Disable for performance
    }


@pytest.fixture
def strict_validation_config():
    """Configuration with very strict validation settings."""
    return {
        'ENABLE_MULTI_FREQUENCY': True,
        'WEBSOCKET_PER_SECOND_ENABLED': True,
        'WEBSOCKET_PER_MINUTE_ENABLED': True,
        'ENABLE_SYNTHETIC_DATA_VALIDATION': True,
        'VALIDATION_PRICE_TOLERANCE': 0.0001,  # 0.01% tolerance
        'VALIDATION_VOLUME_TOLERANCE': 0.001,   # 0.1% tolerance
        'VALIDATION_VWAP_TOLERANCE': 0.0001     # 0.01% tolerance
    }


@pytest.fixture
def correlation_test_data():
    """Test data for FMV correlation validation."""
    return {
        'price_movements': [
            {'ticker': 'AAPL', 'price': 150.0, 'timestamp': time.time() - 60},
            {'ticker': 'AAPL', 'price': 151.0, 'timestamp': time.time() - 50},
            {'ticker': 'AAPL', 'price': 150.5, 'timestamp': time.time() - 40},
            {'ticker': 'AAPL', 'price': 152.0, 'timestamp': time.time() - 30},
            {'ticker': 'AAPL', 'price': 151.8, 'timestamp': time.time() - 20},
        ],
        'expected_correlation_range': (0.7, 0.9),
        'expected_regimes': ['trending', 'sideways', 'volatile']
    }


# Test assertion helpers
def assert_frequency_support(generator, expected_frequency: DataFrequency):
    """Assert that a generator supports the expected frequency."""
    assert hasattr(generator, 'supports_frequency')
    assert generator.supports_frequency(expected_frequency)


def assert_generation_statistics(generator, min_count: int = 1):
    """Assert that a generator has meaningful statistics."""
    stats = generator.get_generation_stats()
    assert isinstance(stats, dict)
    assert 'total_generated' in stats or 'count' in stats
    if 'total_generated' in stats:
        assert stats['total_generated'] >= min_count
    elif 'count' in stats:
        assert stats['count'] >= min_count


def assert_validation_result(result, should_be_valid: bool = True):
    """Assert that a validation result meets expectations."""
    assert isinstance(result, dict)
    assert 'is_valid' in result
    assert result['is_valid'] == should_be_valid
    assert 'errors' in result
    assert 'warnings' in result
    assert isinstance(result['errors'], list)
    assert isinstance(result['warnings'], list)