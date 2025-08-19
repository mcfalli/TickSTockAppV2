# Multi-Frequency Synthetic Data Developer Guide

Last edited: August 19, 2025 at 3:45 PM
Sprint: 102 - Synthetic Data Documentation

## Overview

This developer guide provides practical guidance for working with the multi-frequency synthetic data system. It covers common development scenarios, best practices, troubleshooting, and extension patterns for developers working on TickStock's synthetic data capabilities.

## Table of Contents

1. [Quick Start for Developers](#quick-start-for-developers)
2. [Development Workflow](#development-workflow)
3. [Common Development Scenarios](#common-development-scenarios)
4. [Best Practices](#best-practices)
5. [Testing Guidelines](#testing-guidelines)
6. [Performance Optimization](#performance-optimization)
7. [Extending the System](#extending-the-system)
8. [Debugging and Troubleshooting](#debugging-and-troubleshooting)
9. [Code Examples](#code-examples)
10. [Migration Guide](#migration-guide)

## Quick Start for Developers

### Setting Up Development Environment

1. **Install Dependencies**:
```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-mock

# Install performance monitoring
pip install psutil memory-profiler
```

2. **Configure Development Settings**:
```python
# config/development.py
DEVELOPMENT_CONFIG = {
    'ENABLE_MULTI_FREQUENCY': True,
    'WEBSOCKET_PER_SECOND_ENABLED': True,
    'WEBSOCKET_PER_MINUTE_ENABLED': True,
    'WEBSOCKET_FAIR_VALUE_ENABLED': False,  # Start simple
    'SYNTHETIC_ACTIVITY_LEVEL': 'medium',
    'ENABLE_SYNTHETIC_DATA_VALIDATION': True,
    'SYNTHETIC_PER_SECOND_FREQUENCY': 2.0,  # Slower for development
}
```

3. **Initialize Provider**:
```python
from src.infrastructure.data_sources.synthetic.provider import SimulatedDataProvider
from src.core.services.config_manager import ConfigManager

# Quick setup
config_manager = ConfigManager()
config_manager.apply_synthetic_data_preset('development')
provider = SimulatedDataProvider(config_manager.config)

# Generate test data
ticker = "AAPL"
tick_data = provider.generate_tick_data(ticker)
print(f"Generated tick: {tick_data.ticker} @ ${tick_data.price}")
```

### First Development Task

Try generating data for all frequencies:

```python
from src.infrastructure.data_sources.synthetic.types import DataFrequency

def test_all_frequencies():
    provider = SimulatedDataProvider(config_manager.config)
    
    for frequency in [DataFrequency.PER_SECOND, DataFrequency.PER_MINUTE, DataFrequency.FAIR_VALUE]:
        if provider.has_frequency_support(frequency):
            data = provider.generate_frequency_data("AAPL", frequency)
            print(f"{frequency.value}: {type(data).__name__}")
        else:
            print(f"{frequency.value}: Not supported")
```

## Development Workflow

### 1. Feature Development Workflow

```mermaid
graph LR
    A[Write Tests] --> B[Implement Feature]
    B --> C[Run Unit Tests]
    C --> D[Run Integration Tests]
    D --> E[Performance Testing]
    E --> F[Documentation Update]
    F --> G[Code Review]
```

### 2. Configuration-First Development

Always start with configuration before implementing features:

```python
# Step 1: Define configuration schema
NEW_FEATURE_CONFIG = {
    'SYNTHETIC_NEW_FEATURE_ENABLED': bool,
    'SYNTHETIC_NEW_FEATURE_PARAMETER': float,
    'SYNTHETIC_NEW_FEATURE_TOLERANCE': float
}

# Step 2: Add to ConfigManager validation
def validate_new_feature_config(self) -> Tuple[bool, List[str]]:
    errors = []
    if self.config.get('SYNTHETIC_NEW_FEATURE_PARAMETER', 0) < 0:
        errors.append("New feature parameter must be positive")
    return len(errors) == 0, errors

# Step 3: Implement feature with configuration
class NewFeatureGenerator:
    def __init__(self, config: Dict[str, Any]):
        self.enabled = config.get('SYNTHETIC_NEW_FEATURE_ENABLED', False)
        self.parameter = config.get('SYNTHETIC_NEW_FEATURE_PARAMETER', 1.0)
```

### 3. Test-Driven Development Pattern

```python
# Step 1: Write failing test
def test_new_feature_generation():
    config = {'SYNTHETIC_NEW_FEATURE_ENABLED': True}
    generator = NewFeatureGenerator(config)
    
    result = generator.generate_new_feature_data("AAPL")
    
    assert result is not None
    assert result.meets_requirements()

# Step 2: Implement minimal code to pass test
class NewFeatureGenerator:
    def generate_new_feature_data(self, ticker: str):
        if not self.enabled:
            return None
        return NewFeatureData(ticker=ticker)

# Step 3: Refactor and optimize
```

## Common Development Scenarios

### Scenario 1: Adding New Configuration Parameter

**Problem**: Need to add a new tuning parameter for FMV correlation.

**Solution**:
```python
# 1. Add to configuration schema
FMV_CONFIG_ADDITIONS = {
    'SYNTHETIC_FMV_REGIME_SENSITIVITY': float,  # New parameter
}

# 2. Update ConfigManager validation
def validate_synthetic_data_config(self) -> Tuple[bool, List[str]]:
    # ... existing validation ...
    
    sensitivity = self.config.get('SYNTHETIC_FMV_REGIME_SENSITIVITY', 0.5)
    if not (0.1 <= sensitivity <= 2.0):
        errors.append(f"FMV regime sensitivity {sensitivity} outside valid range (0.1-2.0)")

# 3. Update generator to use new parameter
class FMVGenerator:
    def __init__(self, config: Dict[str, Any], provider):
        # ... existing initialization ...
        self.regime_sensitivity = config.get('SYNTHETIC_FMV_REGIME_SENSITIVITY', 0.5)
    
    def _detect_market_regime(self, ticker: str) -> str:
        # Use self.regime_sensitivity in regime detection logic
        pass

# 4. Add to configuration presets
'integration_testing': {
    'SYNTHETIC_FMV_REGIME_SENSITIVITY': 0.8,  # Higher sensitivity for testing
    # ... other preset settings
}

# 5. Write tests
def test_regime_sensitivity_parameter():
    config = {'SYNTHETIC_FMV_REGIME_SENSITIVITY': 1.5}
    generator = FMVGenerator(config, mock_provider)
    
    assert generator.regime_sensitivity == 1.5
```

### Scenario 2: Optimizing Generator Performance

**Problem**: PerSecondGenerator is too slow for high-frequency testing.

**Solution**:
```python
# 1. Profile current performance
import cProfile
import time

def profile_generator_performance():
    config = {'SYNTHETIC_ACTIVITY_LEVEL': 'opening_bell'}
    generator = PerSecondGenerator(config, mock_provider)
    
    def generate_many():
        for _ in range(1000):
            generator.generate_data("AAPL", config)
    
    cProfile.run('generate_many()', 'performance_profile.txt')

# 2. Identify bottlenecks and optimize
class OptimizedPerSecondGenerator:
    def __init__(self, config: Dict[str, Any], provider):
        # ... existing initialization ...
        
        # Add caching for expensive operations
        self._price_cache = {}
        self._volume_cache = {}
        self._last_cache_time = 0
        self._cache_ttl = 0.1  # 100ms cache TTL
    
    def generate_data(self, ticker: str, config: Dict[str, Any]) -> TickData:
        current_time = time.time()
        
        # Use cached values if within TTL
        if (current_time - self._last_cache_time) < self._cache_ttl:
            if ticker in self._price_cache:
                cached_price = self._price_cache[ticker]
                # Use cached price with small variance
                price = cached_price * (1 + random.uniform(-0.0001, 0.0001))
            else:
                price = self.provider.get_ticker_price(ticker)
                self._price_cache[ticker] = price
        else:
            # Cache expired, refresh
            price = self.provider.get_ticker_price(ticker)
            self._price_cache[ticker] = price
            self._last_cache_time = current_time
        
        # Continue with optimized generation logic
        return self._create_tick_data(ticker, price)

# 3. Measure improvement
def measure_performance_improvement():
    # Test original vs optimized
    original_time = time_generator_performance(PerSecondGenerator)
    optimized_time = time_generator_performance(OptimizedPerSecondGenerator)
    
    improvement = (original_time - optimized_time) / original_time
    print(f"Performance improvement: {improvement:.1%}")
```

### Scenario 3: Adding Cross-Frequency Validation Rule

**Problem**: Need to validate that FMV premium/discount doesn't exceed reasonable bounds.

**Solution**:
```python
# 1. Extend DataConsistencyValidator
class DataConsistencyValidator:
    def validate_fmv_premium_bounds(
        self, 
        ticker: str, 
        fmv_update: Dict[str, Any]
    ) -> ValidationResult:
        """Validate FMV premium/discount is within reasonable bounds."""
        errors = []
        warnings = []
        metrics = {}
        
        fmv_price = fmv_update.get('fmv', 0)
        market_price = fmv_update.get('mp', 0)
        
        if fmv_price > 0 and market_price > 0:
            premium_discount = (fmv_price - market_price) / market_price
            metrics['premium_discount'] = premium_discount
            
            # Check against configured bounds
            max_premium = self.config.get('VALIDATION_MAX_FMV_PREMIUM', 0.05)  # 5%
            max_discount = self.config.get('VALIDATION_MAX_FMV_DISCOUNT', 0.05)  # 5%
            
            if premium_discount > max_premium:
                errors.append(f"FMV premium too high: {premium_discount:.2%} > {max_premium:.2%}")
            elif premium_discount < -max_discount:
                errors.append(f"FMV discount too high: {abs(premium_discount):.2%} > {max_discount:.2%}")
            elif abs(premium_discount) > max_premium * 0.8:
                warnings.append(f"FMV premium/discount approaching limits: {premium_discount:.2%}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            metrics=metrics,
            validation_time=0.001  # Assume fast validation
        )

# 2. Integrate into main validation flow
def validate_fmv_correlation(self, ticker: str, fmv_update: Dict[str, Any]) -> ValidationResult:
    # ... existing validation ...
    
    # Add premium bounds validation
    bounds_result = self.validate_fmv_premium_bounds(ticker, fmv_update)
    
    # Combine results
    combined_result = ValidationResult(
        is_valid=existing_result.is_valid and bounds_result.is_valid,
        errors=existing_result.errors + bounds_result.errors,
        warnings=existing_result.warnings + bounds_result.warnings,
        metrics={**existing_result.metrics, **bounds_result.metrics},
        validation_time=existing_result.validation_time + bounds_result.validation_time
    )
    
    return combined_result

# 3. Add configuration for new validation
VALIDATION_CONFIG_ADDITIONS = {
    'VALIDATION_MAX_FMV_PREMIUM': 0.05,
    'VALIDATION_MAX_FMV_DISCOUNT': 0.05,
    'ENABLE_FMV_PREMIUM_VALIDATION': True
}

# 4. Write tests
def test_fmv_premium_bounds_validation():
    config = {
        'VALIDATION_MAX_FMV_PREMIUM': 0.03,  # 3% limit
        'VALIDATION_MAX_FMV_DISCOUNT': 0.03
    }
    validator = DataConsistencyValidator(config)
    
    # Test valid premium
    valid_fmv = {'fmv': 100.02, 'mp': 100.00}  # 0.02% premium
    result = validator.validate_fmv_premium_bounds("AAPL", valid_fmv)
    assert result.is_valid
    
    # Test excessive premium
    invalid_fmv = {'fmv': 105.00, 'mp': 100.00}  # 5% premium (exceeds 3% limit)
    result = validator.validate_fmv_premium_bounds("AAPL", invalid_fmv)
    assert not result.is_valid
    assert "premium too high" in result.errors[0]
```

## Best Practices

### 1. Configuration Management

**DO:**
```python
# Use ConfigManager for all configuration access
config_manager = ConfigManager()
config = config_manager.get_synthetic_data_config()

# Apply presets for consistent configurations
config_manager.apply_synthetic_data_preset('integration_testing')

# Validate configuration before use
is_valid, errors = config_manager.validate_synthetic_data_config()
if not is_valid:
    raise ValueError(f"Invalid configuration: {errors}")
```

**DON'T:**
```python
# Don't hardcode configuration values
HARDCODED_FREQUENCY = 0.5  # BAD

# Don't access config directly without validation
provider = SimulatedDataProvider(random_config_dict)  # BAD

# Don't ignore configuration validation
config_manager.apply_synthetic_data_preset('invalid_preset')  # BAD - no error checking
```

### 2. Generator Implementation

**DO:**
```python
class WellDesignedGenerator:
    def __init__(self, config: Dict[str, Any], provider):
        # Validate required configuration
        self._validate_config(config)
        
        # Store configuration with defaults
        self.config = config
        self.update_interval = config.get('GENERATOR_UPDATE_INTERVAL', 1.0)
        
        # Initialize state
        self.generation_count = 0
        self.last_generation_time = {}
        
        # Store provider reference for market data
        self.provider = provider
    
    def _validate_config(self, config: Dict[str, Any]):
        """Validate generator-specific configuration."""
        required_keys = ['GENERATOR_ENABLED']
        for key in required_keys:
            if key not in config:
                raise ValueError(f"Missing required configuration: {key}")
    
    def generate_data(self, ticker: str, config: Dict[str, Any]) -> Any:
        """Generate data with proper error handling."""
        try:
            # Check rate limiting
            if not self._should_generate(ticker):
                return None
            
            # Generate data
            data = self._do_generate_data(ticker, config)
            
            # Update statistics
            self.generation_count += 1
            self.last_generation_time[ticker] = time.time()
            
            return data
            
        except Exception as e:
            logger.error(f"Generation failed for {ticker}: {e}")
            return None
    
    def supports_frequency(self, frequency: DataFrequency) -> bool:
        """Clearly specify supported frequency."""
        return frequency == DataFrequency.MY_FREQUENCY
    
    def get_generation_stats(self) -> Dict[str, Any]:
        """Provide comprehensive statistics."""
        return {
            'type': 'my_generator',
            'total_generated': self.generation_count,
            'tickers_tracked': len(self.last_generation_time),
            'config_summary': {
                'enabled': self.config.get('GENERATOR_ENABLED', False),
                'update_interval': self.update_interval
            }
        }
```

**DON'T:**
```python
class PoorlyDesignedGenerator:
    def __init__(self, config, provider):
        # Don't assume configuration is valid
        self.frequency = config['SOME_KEY']  # BAD - might not exist
        
        # Don't ignore provider reference
        # self.provider = provider  # MISSING
    
    def generate_data(self, ticker, config):
        # Don't ignore error handling
        data = some_complex_calculation()  # BAD - no try/except
        
        # Don't skip validation
        return data  # BAD - no validation of generated data
    
    def supports_frequency(self, frequency):
        # Don't be ambiguous about support
        return True  # BAD - claims to support all frequencies
```

### 3. Testing Patterns

**DO:**
```python
class TestNewGenerator:
    @pytest.fixture
    def valid_config(self):
        """Provide valid configuration for testing."""
        return {
            'GENERATOR_ENABLED': True,
            'GENERATOR_UPDATE_INTERVAL': 1.0,
            'GENERATOR_TOLERANCE': 0.01
        }
    
    @pytest.fixture
    def mock_provider(self):
        """Provide controlled mock provider."""
        provider = Mock()
        provider.get_ticker_price.return_value = 150.0
        provider.get_market_status.return_value = 'REGULAR'
        return provider
    
    def test_generator_initialization(self, valid_config, mock_provider):
        """Test generator initializes correctly with valid config."""
        generator = NewGenerator(valid_config, mock_provider)
        
        assert generator.config == valid_config
        assert generator.update_interval == 1.0
        assert generator.generation_count == 0
    
    def test_data_generation_success(self, valid_config, mock_provider):
        """Test successful data generation."""
        generator = NewGenerator(valid_config, mock_provider)
        
        data = generator.generate_data("AAPL", valid_config)
        
        assert data is not None
        assert hasattr(data, 'ticker')
        assert data.ticker == "AAPL"
        assert generator.generation_count == 1
    
    def test_error_handling(self, valid_config):
        """Test generator handles errors gracefully."""
        # Create provider that will cause errors
        error_provider = Mock()
        error_provider.get_ticker_price.side_effect = Exception("Market data unavailable")
        
        generator = NewGenerator(valid_config, error_provider)
        
        data = generator.generate_data("AAPL", valid_config)
        
        # Should return None on error, not raise exception
        assert data is None
        assert generator.generation_count == 0
    
    @pytest.mark.performance
    def test_generation_performance(self, valid_config, mock_provider):
        """Test generation meets performance requirements."""
        generator = NewGenerator(valid_config, mock_provider)
        
        start_time = time.perf_counter()
        
        for _ in range(1000):
            generator.generate_data("AAPL", valid_config)
        
        end_time = time.perf_counter()
        
        duration = end_time - start_time
        rate = 1000 / duration
        
        assert rate > 100, f"Generation too slow: {rate:.1f} gen/sec"
```

**DON'T:**
```python
class PoorTestingExamples:
    def test_everything_in_one_test(self):
        """DON'T test multiple concerns in one test."""
        generator = NewGenerator(config, provider)
        
        # Testing initialization AND generation AND error handling
        assert generator.config is not None  # Initialization
        data = generator.generate_data("AAPL", config)  # Generation
        assert data is not None
        # ... 50 more assertions testing different things
    
    def test_with_hardcoded_values(self):
        """DON'T use hardcoded test values."""
        config = {'SOME_HARDCODED_KEY': 123.456}  # BAD
        data = generator.generate_data("HARDCODED_TICKER", config)  # BAD
        assert data.price == 150.123  # BAD - hardcoded expectation
    
    def test_without_error_cases(self):
        """DON'T only test happy path."""
        # Only tests successful generation
        data = generator.generate_data("AAPL", config)
        assert data is not None
        # MISSING: error cases, edge cases, boundary conditions
```

### 4. Performance Considerations

**Memory Management:**
```python
class MemoryEfficientGenerator:
    def __init__(self, config: Dict[str, Any], provider):
        # Use bounded collections to prevent memory leaks
        from collections import deque
        
        self.price_history = deque(maxlen=100)  # Bounded history
        self.generation_cache = {}
        
        # Set up periodic cleanup
        self.cleanup_interval = 300  # 5 minutes
        self.last_cleanup = time.time()
    
    def generate_data(self, ticker: str, config: Dict[str, Any]) -> Any:
        # Perform periodic cleanup
        if time.time() - self.last_cleanup > self.cleanup_interval:
            self._cleanup_old_data()
        
        # Use memory-efficient data structures
        data = self._generate_with_limited_history(ticker)
        
        return data
    
    def _cleanup_old_data(self):
        """Clean up old cached data to prevent memory leaks."""
        current_time = time.time()
        
        # Remove old cache entries
        expired_keys = [
            key for key, (timestamp, _) in self.generation_cache.items()
            if current_time - timestamp > 300  # 5 minutes
        ]
        
        for key in expired_keys:
            del self.generation_cache[key]
        
        self.last_cleanup = current_time
```

**Performance Monitoring:**
```python
class PerformanceAwareGenerator:
    def __init__(self, config: Dict[str, Any], provider):
        self.config = config
        self.provider = provider
        
        # Performance tracking
        self.generation_times = deque(maxlen=1000)  # Last 1000 generation times
        self.performance_stats = {
            'total_generations': 0,
            'total_time': 0.0,
            'slow_generations': 0  # Generations taking > 10ms
        }
    
    def generate_data(self, ticker: str, config: Dict[str, Any]) -> Any:
        start_time = time.perf_counter()
        
        try:
            data = self._do_generate_data(ticker, config)
            return data
        finally:
            # Always track performance, even on errors
            end_time = time.perf_counter()
            duration = end_time - start_time
            
            self.generation_times.append(duration)
            self.performance_stats['total_generations'] += 1
            self.performance_stats['total_time'] += duration
            
            if duration > 0.01:  # 10ms threshold
                self.performance_stats['slow_generations'] += 1
                logger.warning(f"Slow generation for {ticker}: {duration:.3f}s")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get detailed performance statistics."""
        if not self.generation_times:
            return {'status': 'no_data'}
        
        times = list(self.generation_times)
        
        return {
            'total_generations': self.performance_stats['total_generations'],
            'avg_time_ms': (self.performance_stats['total_time'] / 
                           self.performance_stats['total_generations']) * 1000,
            'recent_avg_time_ms': (sum(times) / len(times)) * 1000,
            'p95_time_ms': sorted(times)[int(len(times) * 0.95)] * 1000,
            'slow_generation_rate': (self.performance_stats['slow_generations'] / 
                                   self.performance_stats['total_generations']),
            'generations_per_second': len(times) / sum(times) if sum(times) > 0 else 0
        }
```

## Testing Guidelines

### Unit Test Structure

```python
class TestGeneratorUnit:
    """Unit tests focus on individual generator functionality."""
    
    def test_initialization_with_valid_config(self):
        """Test generator initializes correctly with valid configuration."""
        config = {'GENERATOR_ENABLED': True, 'GENERATOR_PARAM': 1.0}
        provider = Mock()
        
        generator = MyGenerator(config, provider)
        
        assert generator.enabled is True
        assert generator.param == 1.0
    
    def test_initialization_with_invalid_config(self):
        """Test generator handles invalid configuration gracefully."""
        invalid_config = {'GENERATOR_PARAM': -1.0}  # Invalid negative value
        provider = Mock()
        
        with pytest.raises(ValueError, match="Invalid configuration"):
            MyGenerator(invalid_config, provider)
    
    def test_generate_data_returns_correct_type(self):
        """Test generation returns expected data type."""
        config = self._get_valid_config()
        provider = self._get_mock_provider()
        generator = MyGenerator(config, provider)
        
        data = generator.generate_data("AAPL", config)
        
        assert isinstance(data, ExpectedDataType)
        assert data.ticker == "AAPL"
    
    def test_rate_limiting_behavior(self):
        """Test generator respects rate limiting."""
        config = {'GENERATOR_UPDATE_INTERVAL': 1.0}  # 1 second interval
        provider = Mock()
        generator = MyGenerator(config, provider)
        
        # First generation should succeed
        data1 = generator.generate_data("AAPL", config)
        assert data1 is not None
        
        # Immediate second generation should be skipped
        data2 = generator.generate_data("AAPL", config)
        assert data2 is None  # Rate limited
    
    def test_statistics_tracking(self):
        """Test generator tracks statistics correctly."""
        config = self._get_valid_config()
        provider = Mock()
        generator = MyGenerator(config, provider)
        
        # Generate some data
        for _ in range(5):
            generator.generate_data("AAPL", config)
        
        stats = generator.get_generation_stats()
        assert stats['total_generated'] == 5
        assert stats['type'] == 'my_generator'
```

### Integration Test Structure

```python
class TestGeneratorIntegration:
    """Integration tests focus on generator interaction with other components."""
    
    def test_integration_with_real_provider(self):
        """Test generator works with actual SimulatedDataProvider."""
        config_manager = ConfigManager()
        config_manager.apply_synthetic_data_preset('development')
        
        provider = SimulatedDataProvider(config_manager.config)
        
        # Test generation through provider interface
        data = provider.generate_frequency_data("AAPL", DataFrequency.MY_FREQUENCY)
        
        assert data is not None
        assert provider.has_frequency_support(DataFrequency.MY_FREQUENCY)
    
    def test_integration_with_validation_system(self):
        """Test generator data passes validation."""
        config = {
            'ENABLE_SYNTHETIC_DATA_VALIDATION': True,
            'VALIDATION_STRICT_MODE': True
        }
        provider = SimulatedDataProvider(config)
        validator = DataConsistencyValidator(config)
        
        # Generate data and validate
        data = provider.generate_frequency_data("AAPL", DataFrequency.MY_FREQUENCY)
        validator.add_my_frequency_data("AAPL", data)
        
        validation_result = validator.validate_my_frequency_consistency("AAPL", data)
        assert validation_result.is_valid
    
    def test_configuration_change_integration(self):
        """Test generator responds to configuration changes."""
        config_manager = ConfigManager()
        config_manager.apply_synthetic_data_preset('minimal')
        
        provider = SimulatedDataProvider(config_manager.config)
        
        # Change configuration
        config_manager.apply_synthetic_data_preset('performance_testing')
        
        # Verify generator behavior changed
        # (In real implementation, would need configuration change notification)
        new_provider = SimulatedDataProvider(config_manager.config)
        
        # Performance preset should generate data faster
        old_stats = provider.get_generation_statistics()
        new_stats = new_provider.get_generation_statistics()
        
        # Verify different behavior (specific assertions depend on implementation)
```

### Performance Test Structure

```python
class TestGeneratorPerformance:
    """Performance tests verify generation speed and resource usage."""
    
    @pytest.mark.performance
    def test_single_ticker_generation_speed(self, performance_timer):
        """Test generation speed for single ticker."""
        config = {'SYNTHETIC_ACTIVITY_LEVEL': 'high'}
        provider = SimulatedDataProvider(config)
        
        performance_timer.start()
        
        generation_count = 0
        for _ in range(1000):
            data = provider.generate_frequency_data("AAPL", DataFrequency.MY_FREQUENCY)
            if data:
                generation_count += 1
        
        performance_timer.stop()
        
        rate = generation_count / performance_timer.elapsed
        assert rate > 100, f"Generation too slow: {rate:.1f} gen/sec"
    
    @pytest.mark.performance
    def test_memory_usage_stability(self):
        """Test memory usage remains stable during extended generation."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        config = {'SYNTHETIC_ACTIVITY_LEVEL': 'opening_bell'}
        provider = SimulatedDataProvider(config)
        
        # Generate data for extended period
        for _ in range(5000):
            provider.generate_frequency_data("AAPL", DataFrequency.MY_FREQUENCY)
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        assert memory_increase < 50, f"Excessive memory usage: {memory_increase:.1f} MB"
    
    @pytest.mark.performance
    def test_concurrent_generation_performance(self):
        """Test performance under concurrent access."""
        import concurrent.futures
        import threading
        
        config = {'SYNTHETIC_ACTIVITY_LEVEL': 'high'}
        provider = SimulatedDataProvider(config)
        
        def generate_data_worker(ticker: str, iterations: int) -> int:
            count = 0
            for _ in range(iterations):
                data = provider.generate_frequency_data(ticker, DataFrequency.MY_FREQUENCY)
                if data:
                    count += 1
            return count
        
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(generate_data_worker, f"TICKER{i}", 250)
                for i in range(4)
            ]
            
            total_generated = sum(future.result() for future in futures)
        
        end_time = time.time()
        
        concurrent_rate = total_generated / (end_time - start_time)
        assert concurrent_rate > 200, f"Poor concurrent performance: {concurrent_rate:.1f} gen/sec"
```

## Performance Optimization

### Profiling Generator Performance

```python
import cProfile
import pstats
from memory_profiler import profile

def profile_generator_performance():
    """Profile generator performance to identify bottlenecks."""
    config = {'SYNTHETIC_ACTIVITY_LEVEL': 'opening_bell'}
    provider = SimulatedDataProvider(config)
    
    def generate_test_data():
        for _ in range(1000):
            provider.generate_frequency_data("AAPL", DataFrequency.PER_SECOND)
    
    # Profile CPU usage
    profiler = cProfile.Profile()
    profiler.enable()
    generate_test_data()
    profiler.disable()
    
    # Analyze results
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(10)  # Top 10 functions by cumulative time

@profile  # Memory profiler decorator
def profile_memory_usage():
    """Profile memory usage during generation."""
    config = {'SYNTHETIC_ACTIVITY_LEVEL': 'opening_bell'}
    provider = SimulatedDataProvider(config)
    
    data_list = []
    for i in range(1000):
        data = provider.generate_frequency_data("AAPL", DataFrequency.PER_SECOND)
        if i % 100 == 0:  # Keep some data to see memory growth
            data_list.append(data)
    
    return data_list

# Run profiling
if __name__ == "__main__":
    print("CPU Profiling:")
    profile_generator_performance()
    
    print("\nMemory Profiling:")
    profile_memory_usage()
```

### Common Performance Optimizations

1. **Caching Expensive Calculations**:
```python
class OptimizedGenerator:
    def __init__(self, config: Dict[str, Any], provider):
        self.config = config
        self.provider = provider
        
        # Cache expensive calculations
        self._calculation_cache = {}
        self._cache_expiry = {}
        self._cache_ttl = 1.0  # 1 second TTL
    
    def _get_cached_calculation(self, key: str, calculation_func):
        """Get cached result or calculate and cache."""
        current_time = time.time()
        
        if (key in self._calculation_cache and 
            current_time - self._cache_expiry.get(key, 0) < self._cache_ttl):
            return self._calculation_cache[key]
        
        # Calculate and cache
        result = calculation_func()
        self._calculation_cache[key] = result
        self._cache_expiry[key] = current_time
        
        return result
```

2. **Batch Processing**:
```python
class BatchOptimizedGenerator:
    def __init__(self, config: Dict[str, Any], provider):
        self.config = config
        self.provider = provider
        self.batch_size = config.get('GENERATOR_BATCH_SIZE', 10)
        self.batch_buffer = []
    
    def generate_data_batch(self, tickers: List[str], config: Dict[str, Any]) -> List[Any]:
        """Generate data for multiple tickers efficiently."""
        # Pre-fetch market data for all tickers
        market_prices = {
            ticker: self.provider.get_ticker_price(ticker) 
            for ticker in tickers
        }
        
        # Generate data using pre-fetched prices
        results = []
        for ticker in tickers:
            data = self._generate_with_cached_price(ticker, market_prices[ticker])
            results.append(data)
        
        return results
```

3. **Memory Pool Usage**:
```python
class MemoryPoolGenerator:
    def __init__(self, config: Dict[str, Any], provider):
        self.config = config
        self.provider = provider
        
        # Pre-allocate object pool
        self.tick_data_pool = [TickData() for _ in range(100)]
        self.pool_index = 0
    
    def generate_data(self, ticker: str, config: Dict[str, Any]) -> TickData:
        """Generate data using object pool to reduce allocations."""
        # Get pre-allocated object
        tick_data = self.tick_data_pool[self.pool_index]
        self.pool_index = (self.pool_index + 1) % len(self.tick_data_pool)
        
        # Reset and populate object
        tick_data.reset()  # Clear previous data
        tick_data.ticker = ticker
        tick_data.price = self.provider.get_ticker_price(ticker)
        # ... populate other fields
        
        return tick_data
```

## Extending the System

### Adding New Frequency Type

Complete example of adding a new "HOURLY" frequency:

```python
# Step 1: Add to DataFrequency enum
# src/infrastructure/data_sources/synthetic/types.py
class DataFrequency(Enum):
    PER_SECOND = "per_second"
    PER_MINUTE = "per_minute"
    FAIR_VALUE = "fair_value"
    HOURLY = "hourly"  # New frequency

# Step 2: Create HourlyGenerator
# src/infrastructure/data_sources/synthetic/generators/hourly_generator.py
class HourlyGenerator:
    """Generates hourly OHLCV data aggregated from minute bars."""
    
    def __init__(self, config: Dict[str, Any], provider):
        self.config = config
        self.provider = provider
        self.generation_count = 0
        
        # Hourly-specific configuration
        self.aggregation_window = config.get('SYNTHETIC_HOURLY_WINDOW', 3600)  # 1 hour
        self.min_minutes_per_hour = config.get('SYNTHETIC_HOURLY_MIN_MINUTES', 50)
        
        # Track hourly state
        self._hourly_buffers: Dict[str, List[Dict[str, Any]]] = {}
        self._last_hourly_update: Dict[str, float] = {}
    
    def generate_data(self, ticker: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate hourly OHLCV bar."""
        current_time = time.time()
        
        # Check if enough time has passed for hourly update
        if ticker in self._last_hourly_update:
            time_since_last = current_time - self._last_hourly_update[ticker]
            if time_since_last < self.aggregation_window:
                return None  # Too soon for next hourly bar
        
        # Generate minute bars for the hour
        minute_bars = self._generate_hour_of_minute_bars(ticker, current_time)
        
        if len(minute_bars) < self.min_minutes_per_hour:
            return None  # Not enough data for reliable hourly bar
        
        # Aggregate minutes into hourly bar
        hourly_bar = self._aggregate_minutes_to_hourly(minute_bars)
        
        # Update state
        self._last_hourly_update[ticker] = current_time
        self.generation_count += 1
        
        return self._format_as_hourly_event(ticker, hourly_bar, current_time)
    
    def supports_frequency(self, frequency: DataFrequency) -> bool:
        """Check if generator supports the given frequency."""
        return frequency == DataFrequency.HOURLY
    
    def get_generation_stats(self) -> Dict[str, Any]:
        """Get generation statistics."""
        return {
            'type': 'hourly',
            'total_generated': self.generation_count,
            'tickers_tracked': len(self._last_hourly_update),
            'config': {
                'aggregation_window': self.aggregation_window,
                'min_minutes_per_hour': self.min_minutes_per_hour
            }
        }

# Step 3: Register in SimulatedDataProvider
# src/infrastructure/data_sources/synthetic/provider.py
def _setup_frequency_generators(self):
    """Initialize frequency-specific generators."""
    for frequency in self._active_frequencies:
        try:
            # ... existing generators ...
            elif frequency == DataFrequency.HOURLY:
                from src.infrastructure.data_sources.synthetic.generators.hourly_generator import HourlyGenerator
                self._frequency_generators[frequency] = HourlyGenerator(self.config, self)
            # ... rest of initialization

# Step 4: Add configuration options
# src/core/services/config_manager.py - add to DEFAULT_CONFIG
HOURLY_CONFIG = {
    'WEBSOCKET_HOURLY_ENABLED': bool,
    'SYNTHETIC_HOURLY_WINDOW': int,
    'SYNTHETIC_HOURLY_MIN_MINUTES': int,
}

# Step 5: Add to configuration presets
def get_synthetic_data_presets(self) -> Dict[str, Dict[str, Any]]:
    return {
        'market_simulation': {
            # ... existing preset ...
            'WEBSOCKET_HOURLY_ENABLED': True,
            'SYNTHETIC_HOURLY_WINDOW': 3600,
            'SYNTHETIC_HOURLY_MIN_MINUTES': 45  # Allow some missing minutes
        }
        # ... other presets
    }

# Step 6: Write comprehensive tests
# tests/unit/infrastructure/test_hourly_generator.py
class TestHourlyGenerator:
    def test_hourly_generation(self):
        config = {
            'WEBSOCKET_HOURLY_ENABLED': True,
            'SYNTHETIC_HOURLY_WINDOW': 3600,
            'SYNTHETIC_HOURLY_MIN_MINUTES': 50
        }
        provider = Mock()
        generator = HourlyGenerator(config, provider)
        
        data = generator.generate_data("AAPL", config)
        
        assert data is not None
        assert data['ev'] == 'AH'
        assert 'o' in data and 'h' in data and 'l' in data and 'c' in data
```

## Debugging and Troubleshooting

### Common Issues and Solutions

1. **No Data Generated**:
```python
def debug_no_data_generation():
    """Debug why no data is being generated."""
    config_manager = ConfigManager()
    config = config_manager.get_synthetic_data_config()
    
    print("Configuration Debug:")
    print(f"  Multi-frequency enabled: {config['multi_frequency_enabled']}")
    print(f"  Per-second enabled: {config['per_second_enabled']}")
    print(f"  Per-minute enabled: {config['per_minute_enabled']}")
    print(f"  Fair value enabled: {config['fair_value_enabled']}")
    
    provider = SimulatedDataProvider(config_manager.config)
    
    print(f"\nProvider Debug:")
    print(f"  Supported frequencies: {[f.value for f in provider.get_supported_frequencies()]}")
    print(f"  Active generators: {list(provider._frequency_generators.keys())}")
    
    # Test generation for each frequency
    for frequency in [DataFrequency.PER_SECOND, DataFrequency.PER_MINUTE, DataFrequency.FAIR_VALUE]:
        if provider.has_frequency_support(frequency):
            try:
                data = provider.generate_frequency_data("AAPL", frequency)
                print(f"  {frequency.value}: Generated {type(data).__name__}")
            except Exception as e:
                print(f"  {frequency.value}: Error - {e}")
        else:
            print(f"  {frequency.value}: Not supported")
```

2. **Validation Failures**:
```python
def debug_validation_failures():
    """Debug validation failures."""
    config = {
        'ENABLE_SYNTHETIC_DATA_VALIDATION': True,
        'VALIDATION_PRICE_TOLERANCE': 0.001,  # Very strict for debugging
    }
    
    provider = SimulatedDataProvider(config)
    validator = provider._validator
    
    if not validator:
        print("Validation not enabled")
        return
    
    # Generate and validate data
    ticker = "AAPL"
    tick_data = provider.generate_frequency_data(ticker, DataFrequency.PER_SECOND)
    minute_bar = provider.generate_frequency_data(ticker, DataFrequency.PER_MINUTE)
    
    if tick_data:
        validator.add_tick_data(ticker, tick_data)
        print(f"Added tick data: {tick_data.ticker} @ ${tick_data.price}")
    
    if minute_bar:
        validator.add_minute_bar(ticker, minute_bar)
        result = validator.validate_minute_bar_consistency(ticker, minute_bar)
        
        print(f"\nValidation Result:")
        print(f"  Valid: {result.is_valid}")
        print(f"  Errors: {result.errors}")
        print(f"  Warnings: {result.warnings}")
        print(f"  Metrics: {result.metrics}")
        
        if not result.is_valid:
            print("\nDebugging Validation Failure:")
            print(f"  Minute bar: O={minute_bar.get('o')}, H={minute_bar.get('h')}, "
                  f"L={minute_bar.get('l')}, C={minute_bar.get('c')}")
            
            # Check tick buffer
            tick_buffer = validator._tick_buffers.get(ticker, [])
            print(f"  Tick buffer size: {len(tick_buffer)}")
            if tick_buffer:
                prices = [t.price for t in tick_buffer[-10:]]  # Last 10 prices
                print(f"  Recent tick prices: {prices}")
```

3. **Performance Issues**:
```python
def debug_performance_issues():
    """Debug performance bottlenecks."""
    import time
    import psutil
    import os
    
    config = {'SYNTHETIC_ACTIVITY_LEVEL': 'opening_bell'}
    provider = SimulatedDataProvider(config)
    
    # Measure memory and CPU usage
    process = psutil.Process(os.getpid())
    
    print("Performance Debug:")
    print(f"  Initial memory: {process.memory_info().rss / 1024 / 1024:.1f} MB")
    
    # Test generation speed
    start_time = time.perf_counter()
    generation_count = 0
    
    for i in range(1000):
        data = provider.generate_frequency_data("AAPL", DataFrequency.PER_SECOND)
        if data:
            generation_count += 1
        
        if i % 100 == 0:  # Check every 100 iterations
            current_memory = process.memory_info().rss / 1024 / 1024
            elapsed = time.perf_counter() - start_time
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            print(f"  Iteration {i + 1}: {rate:.1f} gen/sec, {current_memory:.1f} MB")
    
    end_time = time.perf_counter()
    final_memory = process.memory_info().rss / 1024 / 1024
    
    total_time = end_time - start_time
    final_rate = generation_count / total_time
    memory_increase = final_memory - (process.memory_info().rss / 1024 / 1024)
    
    print(f"\nFinal Results:")
    print(f"  Total time: {total_time:.3f} seconds")
    print(f"  Generation rate: {final_rate:.1f} gen/sec")
    print(f"  Memory increase: {memory_increase:.1f} MB")
    print(f"  Generated count: {generation_count}")
    
    # Check provider statistics
    stats = provider.get_generation_statistics()
    print(f"\nProvider Statistics:")
    for freq, freq_stats in stats.get('frequencies', {}).items():
        print(f"  {freq}: {freq_stats.get('count', 0)} generated")
```

### Logging Best Practices

```python
# Use structured logging for debugging
import logging
from config.logging_config import get_domain_logger, LogDomain

logger = get_domain_logger(LogDomain.CORE, 'synthetic_generator')

class DebuggableGenerator:
    def generate_data(self, ticker: str, config: Dict[str, Any]) -> Any:
        logger.debug(f"Generating data for {ticker}", extra={
            'ticker': ticker,
            'config_hash': hash(str(config)),
            'generator_type': self.__class__.__name__
        })
        
        try:
            start_time = time.perf_counter()
            data = self._do_generate_data(ticker, config)
            generation_time = time.perf_counter() - start_time
            
            if data:
                logger.info(f"Generated data for {ticker}", extra={
                    'ticker': ticker,
                    'generation_time_ms': generation_time * 1000,
                    'data_type': type(data).__name__,
                    'success': True
                })
            else:
                logger.warning(f"No data generated for {ticker}", extra={
                    'ticker': ticker,
                    'generation_time_ms': generation_time * 1000,
                    'success': False
                })
            
            return data
            
        except Exception as e:
            logger.error(f"Generation failed for {ticker}: {e}", extra={
                'ticker': ticker,
                'error_type': type(e).__name__,
                'error_message': str(e),
                'success': False
            }, exc_info=True)
            return None
```

## Migration Guide

### Migrating from Single-Frequency to Multi-Frequency

If you have existing code using single-frequency synthetic data:

**Old Code:**
```python
# Old single-frequency approach
provider = SimulatedDataProvider(config)
tick_data = provider.generate_tick_data("AAPL")  # Always per-second
```

**New Code:**
```python
# New multi-frequency approach
provider = SimulatedDataProvider(config)

# Explicit frequency specification
tick_data = provider.generate_tick_data("AAPL", DataFrequency.PER_SECOND)
minute_bar = provider.generate_tick_data("AAPL", DataFrequency.PER_MINUTE)
fmv_data = provider.generate_tick_data("AAPL", DataFrequency.FAIR_VALUE)

# Or use the new frequency-specific method
tick_data = provider.generate_frequency_data("AAPL", DataFrequency.PER_SECOND)
```

**Migration Steps:**

1. **Update Configuration**:
```python
# Old configuration
config = {
    'USE_SIMULATED_DATA': True,
    'SYNTHETIC_ACTIVITY_LEVEL': 'medium'
}

# New configuration
config = {
    'ENABLE_MULTI_FREQUENCY': True,  # Enable new system
    'WEBSOCKET_PER_SECOND_ENABLED': True,  # Maintain backward compatibility
    'WEBSOCKET_PER_MINUTE_ENABLED': False,  # Add new frequencies as needed
    'WEBSOCKET_FAIR_VALUE_ENABLED': False,
    'SYNTHETIC_ACTIVITY_LEVEL': 'medium'
}
```

2. **Update Generation Calls**:
```python
# Instead of
data = provider.generate_tick_data(ticker)

# Use
data = provider.generate_tick_data(ticker, DataFrequency.PER_SECOND)
# or maintain backward compatibility (defaults to PER_SECOND)
data = provider.generate_tick_data(ticker)
```

3. **Add Multi-Frequency Support Gradually**:
```python
def migrate_to_multi_frequency():
    """Gradual migration to multi-frequency support."""
    # Phase 1: Enable multi-frequency but only use per-second
    config = {
        'ENABLE_MULTI_FREQUENCY': True,
        'WEBSOCKET_PER_SECOND_ENABLED': True,
        'WEBSOCKET_PER_MINUTE_ENABLED': False,  # Enable in Phase 2
        'WEBSOCKET_FAIR_VALUE_ENABLED': False   # Enable in Phase 3
    }
    
    provider = SimulatedDataProvider(config)
    
    # Existing code continues to work
    tick_data = provider.generate_tick_data("AAPL")  # Defaults to PER_SECOND
    
    # Phase 2: Add per-minute support
    # config['WEBSOCKET_PER_MINUTE_ENABLED'] = True
    # minute_data = provider.generate_frequency_data("AAPL", DataFrequency.PER_MINUTE)
    
    # Phase 3: Add FMV support
    # config['WEBSOCKET_FAIR_VALUE_ENABLED'] = True
    # fmv_data = provider.generate_frequency_data("AAPL", DataFrequency.FAIR_VALUE)
```

This developer guide provides comprehensive guidance for working with the multi-frequency synthetic data system, covering everything from initial setup through advanced extension scenarios.