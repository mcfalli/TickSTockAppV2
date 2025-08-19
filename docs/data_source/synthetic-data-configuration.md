# Multi-Frequency Synthetic Data Configuration Guide

Last edited: August 19, 2025 at 3:45 PM
Sprint: 102 - Synthetic Data Documentation

## Overview

The multi-frequency synthetic data system provides comprehensive configuration options for generating realistic market data across multiple frequencies. This system enables testing of complex multi-frequency scenarios without requiring expensive Polygon Business plan access.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Configuration Architecture](#configuration-architecture)
3. [Frequency Configuration](#frequency-configuration)
4. [Generator-Specific Settings](#generator-specific-settings)
5. [Validation Configuration](#validation-configuration)
6. [Configuration Presets](#configuration-presets)
7. [Performance Tuning](#performance-tuning)
8. [Advanced Configuration](#advanced-configuration)
9. [Troubleshooting](#troubleshooting)

## Quick Start

### Enable Multi-Frequency Generation

```python
# Basic multi-frequency setup
config = {
    'ENABLE_MULTI_FREQUENCY': True,
    'WEBSOCKET_PER_SECOND_ENABLED': True,
    'WEBSOCKET_PER_MINUTE_ENABLED': True,
    'WEBSOCKET_FAIR_VALUE_ENABLED': True,
    'ENABLE_SYNTHETIC_DATA_VALIDATION': True
}
```

### Apply a Configuration Preset

```python
from src.core.services.config_manager import ConfigManager

config_manager = ConfigManager()
config_manager.apply_synthetic_data_preset('integration_testing')
```

## Configuration Architecture

The synthetic data configuration system is built on Sprint 100's ConfigManager with specialized helper methods:

- **`get_synthetic_data_config()`** - Retrieve complete synthetic data configuration
- **`get_synthetic_data_presets()`** - Access predefined configuration presets
- **`apply_synthetic_data_preset()`** - Apply preset configurations dynamically
- **`validate_synthetic_data_config()`** - Validate configuration consistency

## Frequency Configuration

### Master Control

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `ENABLE_MULTI_FREQUENCY` | bool | False | Master switch for multi-frequency generation |

### Frequency Enablement

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `WEBSOCKET_PER_SECOND_ENABLED` | bool | True | Enable per-second tick generation |
| `WEBSOCKET_PER_MINUTE_ENABLED` | bool | False | Enable per-minute OHLCV bars |
| `WEBSOCKET_FAIR_VALUE_ENABLED` | bool | False | Enable fair market value updates |

**Example: Enable All Frequencies**
```python
config = {
    'ENABLE_MULTI_FREQUENCY': True,
    'WEBSOCKET_PER_SECOND_ENABLED': True,
    'WEBSOCKET_PER_MINUTE_ENABLED': True,
    'WEBSOCKET_FAIR_VALUE_ENABLED': True
}
```

## Generator-Specific Settings

### Per-Second Generator

Controls the generation of individual tick data points.

| Setting | Type | Default | Range | Description |
|---------|------|---------|-------|-------------|
| `SYNTHETIC_ACTIVITY_LEVEL` | str | 'medium' | low/medium/high/opening_bell | Overall market activity simulation |
| `SYNTHETIC_PER_SECOND_FREQUENCY` | float | 1.0 | 0.1-60.0 | Generation frequency in seconds |
| `SYNTHETIC_PER_SECOND_PRICE_VARIANCE` | float | 0.001 | 0.0001-0.01 | Price variance (0.1% default) |
| `SYNTHETIC_PER_SECOND_VOLUME_RANGE` | list | [10000, 100000] | - | [min, max] volume range |

**Activity Level Effects:**
- `low`: 1K-10K volume, 5% price variance
- `medium`: 10K-100K volume, 10% price variance  
- `high`: 100K-500K volume, 20% price variance
- `opening_bell`: 500K-1M volume, 50% price variance

**Example: High-Frequency Per-Second Configuration**
```python
config = {
    'SYNTHETIC_ACTIVITY_LEVEL': 'high',
    'SYNTHETIC_PER_SECOND_FREQUENCY': 0.5,  # Every 0.5 seconds
    'SYNTHETIC_PER_SECOND_PRICE_VARIANCE': 0.002,  # 0.2% variance
    'SYNTHETIC_PER_SECOND_VOLUME_RANGE': [50000, 200000]
}
```

### Per-Minute Generator

Generates OHLCV bars aggregated from tick-level data.

| Setting | Type | Default | Range | Description |
|---------|------|---------|-------|-------------|
| `SYNTHETIC_PER_MINUTE_WINDOW` | int | 60 | 30-300 | Aggregation window in seconds |
| `SYNTHETIC_PER_MINUTE_MIN_TICKS` | int | 5 | 1-20 | Minimum ticks per minute bar |
| `SYNTHETIC_PER_MINUTE_MAX_TICKS` | int | 30 | 10-100 | Maximum ticks per minute bar |
| `SYNTHETIC_PER_MINUTE_OHLC_VARIANCE` | float | 0.005 | 0.001-0.02 | OHLC price variance (0.5% default) |
| `SYNTHETIC_PER_MINUTE_VOLUME_MULTIPLIER` | float | 5.0 | 1.0-20.0 | Volume scaling vs per-second |

**Example: Conservative Per-Minute Configuration**
```python
config = {
    'SYNTHETIC_PER_MINUTE_WINDOW': 60,
    'SYNTHETIC_PER_MINUTE_MIN_TICKS': 10,
    'SYNTHETIC_PER_MINUTE_MAX_TICKS': 25,
    'SYNTHETIC_PER_MINUTE_OHLC_VARIANCE': 0.003,  # 0.3% variance
    'SYNTHETIC_PER_MINUTE_VOLUME_MULTIPLIER': 3.0
}
```

### Fair Market Value (FMV) Generator

Generates FMV updates that correlate with market price movements.

#### Basic FMV Settings

| Setting | Type | Default | Range | Description |
|---------|------|---------|-------|-------------|
| `SYNTHETIC_FMV_UPDATE_INTERVAL` | int | 30 | 5-300 | Update interval in seconds |
| `SYNTHETIC_FMV_CORRELATION` | float | 0.85 | 0.0-1.0 | Base correlation with market price |
| `SYNTHETIC_FMV_VARIANCE` | float | 0.002 | 0.0001-0.01 | FMV-specific variance (0.2% default) |
| `SYNTHETIC_FMV_PREMIUM_RANGE` | float | 0.01 | 0.001-0.05 | Max premium/discount range (1% default) |

#### Advanced FMV Correlation Settings

| Setting | Type | Default | Range | Description |
|---------|------|---------|-------|-------------|
| `SYNTHETIC_FMV_MOMENTUM_DECAY` | float | 0.7 | 0.1-0.95 | FMV momentum persistence |
| `SYNTHETIC_FMV_LAG_FACTOR` | float | 0.3 | 0.1-0.8 | FMV response lag to price changes |
| `SYNTHETIC_FMV_VOLATILITY_DAMPENING` | float | 0.6 | 0.1-0.9 | FMV volatility vs market volatility |

#### Market Regime-Aware Correlations

| Setting | Type | Default | Range | Description |
|---------|------|---------|-------|-------------|
| `SYNTHETIC_FMV_TRENDING_CORRELATION` | float | 0.90 | 0.5-0.98 | Correlation during trending markets |
| `SYNTHETIC_FMV_SIDEWAYS_CORRELATION` | float | 0.75 | 0.3-0.9 | Correlation during sideways markets |
| `SYNTHETIC_FMV_VOLATILE_CORRELATION` | float | 0.65 | 0.2-0.85 | Correlation during volatile markets |

**Example: Realistic FMV Configuration**
```python
config = {
    'SYNTHETIC_FMV_UPDATE_INTERVAL': 30,
    'SYNTHETIC_FMV_CORRELATION': 0.82,
    'SYNTHETIC_FMV_MOMENTUM_DECAY': 0.75,
    'SYNTHETIC_FMV_LAG_FACTOR': 0.25,
    'SYNTHETIC_FMV_TRENDING_CORRELATION': 0.88,
    'SYNTHETIC_FMV_SIDEWAYS_CORRELATION': 0.70,
    'SYNTHETIC_FMV_VOLATILE_CORRELATION': 0.60
}
```

## Validation Configuration

### Master Validation Control

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `ENABLE_SYNTHETIC_DATA_VALIDATION` | bool | True | Enable cross-frequency data validation |

### Validation Tolerances

| Setting | Type | Default | Range | Description |
|---------|------|---------|-------|-------------|
| `VALIDATION_PRICE_TOLERANCE` | float | 0.001 | 0.0001-0.01 | Price validation tolerance (0.1% default) |
| `VALIDATION_VOLUME_TOLERANCE` | float | 0.05 | 0.001-0.20 | Volume validation tolerance (5% default) |
| `VALIDATION_VWAP_TOLERANCE` | float | 0.002 | 0.0001-0.01 | VWAP validation tolerance (0.2% default) |

**Example: Strict Validation Configuration**
```python
config = {
    'ENABLE_SYNTHETIC_DATA_VALIDATION': True,
    'VALIDATION_PRICE_TOLERANCE': 0.0005,  # 0.05% tolerance
    'VALIDATION_VOLUME_TOLERANCE': 0.02,   # 2% tolerance
    'VALIDATION_VWAP_TOLERANCE': 0.001     # 0.1% tolerance
}
```

## Configuration Presets

The system includes 5 predefined presets for common scenarios:

### 1. Development Preset
**Use Case:** Low-frequency development testing
```python
config_manager.apply_synthetic_data_preset('development')
```
- Single frequency (per-second only)
- Medium activity level
- 2-second generation interval
- Validation enabled

### 2. Integration Testing Preset
**Use Case:** Full multi-frequency integration testing
```python
config_manager.apply_synthetic_data_preset('integration_testing')
```
- All frequencies enabled
- High activity level
- 0.5-second per-second frequency
- 15-second FMV intervals
- Strict validation (0.05% tolerance)

### 3. Performance Testing Preset
**Use Case:** High-frequency performance testing
```python
config_manager.apply_synthetic_data_preset('performance_testing')
```
- All frequencies enabled
- Opening bell activity level
- 0.1-second per-second frequency
- 5-second FMV intervals
- Validation disabled for performance
- Up to 50 ticks per minute bar

### 4. Market Simulation Preset
**Use Case:** Realistic market behavior simulation
```python
config_manager.apply_synthetic_data_preset('market_simulation')
```
- All frequencies enabled
- Medium activity level
- Realistic correlation settings (0.82 base, 0.88 trending, 0.65 volatile)
- 30-second FMV intervals
- Validation enabled

### 5. Minimal Preset
**Use Case:** Basic testing with minimal overhead
```python
config_manager.apply_synthetic_data_preset('minimal')
```
- Single frequency (per-second only)
- Low activity level
- 5-second generation interval
- Validation disabled

### Custom Preset Creation

```python
# Create custom preset
custom_config = {
    'description': 'Custom high-frequency testing',
    'ENABLE_MULTI_FREQUENCY': True,
    'WEBSOCKET_PER_SECOND_ENABLED': True,
    'WEBSOCKET_PER_MINUTE_ENABLED': True,
    'SYNTHETIC_ACTIVITY_LEVEL': 'high',
    'SYNTHETIC_PER_SECOND_FREQUENCY': 0.2,  # 5x per second
    'ENABLE_SYNTHETIC_DATA_VALIDATION': True
}

# Apply custom configuration
config_manager.config.update(custom_config)
```

## Performance Tuning

### High-Frequency Scenarios

For maximum performance with high-frequency generation:

```python
performance_config = {
    'ENABLE_MULTI_FREQUENCY': True,
    'SYNTHETIC_PER_SECOND_FREQUENCY': 0.1,  # 10x per second
    'SYNTHETIC_FMV_UPDATE_INTERVAL': 5,     # Every 5 seconds
    'ENABLE_SYNTHETIC_DATA_VALIDATION': False,  # Disable validation
    'SYNTHETIC_PER_MINUTE_MAX_TICKS': 100   # Allow more ticks per bar
}
```

### Memory Optimization

For sustained generation with memory efficiency:

```python
memory_config = {
    'ENABLE_SYNTHETIC_DATA_VALIDATION': True,  # Keep validation
    'VALIDATION_PRICE_TOLERANCE': 0.002,       # Relaxed tolerance
    'SYNTHETIC_PER_MINUTE_MAX_TICKS': 20,      # Limit ticks per bar
    # Keep buffers smaller by increasing FMV intervals
    'SYNTHETIC_FMV_UPDATE_INTERVAL': 60
}
```

### Accuracy vs Performance Trade-offs

| Scenario | Validation | Tolerances | Performance Impact |
|----------|------------|------------|-------------------|
| Development | Enabled | Standard (0.1%) | Low impact |
| Integration Testing | Enabled | Strict (0.05%) | Medium impact |
| Performance Testing | Disabled | N/A | No impact |
| Production Simulation | Enabled | Relaxed (0.2%) | Minimal impact |

## Advanced Configuration

### Dynamic Configuration Changes

```python
# Runtime configuration changes
config_manager = ConfigManager()

# Check current configuration
current_config = config_manager.get_synthetic_data_config()
print(f"Multi-frequency enabled: {current_config['multi_frequency_enabled']}")

# Validate before applying changes
is_valid, errors = config_manager.validate_synthetic_data_config()
if not is_valid:
    print(f"Configuration errors: {errors}")

# Apply changes with validation
success = config_manager.apply_synthetic_data_preset('performance_testing')
if success:
    print("Configuration updated successfully")
```

### Environment-Specific Configuration

```python
import os

# Development environment
if os.getenv('ENVIRONMENT') == 'development':
    config_manager.apply_synthetic_data_preset('development')
    
# CI/CD testing environment
elif os.getenv('ENVIRONMENT') == 'testing':
    config_manager.apply_synthetic_data_preset('integration_testing')
    
# Performance testing environment
elif os.getenv('ENVIRONMENT') == 'performance':
    config_manager.apply_synthetic_data_preset('performance_testing')
```

### Configuration Monitoring

```python
# Set up configuration change monitoring
def on_config_change():
    print("Synthetic data configuration changed")
    # Optionally restart synthetic data generation
    
config_manager.register_config_change_callback(on_config_change)
```

## Troubleshooting

### Common Configuration Issues

#### Issue: No data generation despite enabled frequencies
**Solution:**
```python
# Check if frequencies are properly enabled
supported_frequencies = provider.get_supported_frequencies()
print(f"Supported frequencies: {[f.value for f in supported_frequencies]}")

# Verify configuration
config = config_manager.get_synthetic_data_config()
print(f"Per-second enabled: {config['per_second_enabled']}")
print(f"Per-minute enabled: {config['per_minute_enabled']}")
print(f"Fair value enabled: {config['fair_value_enabled']}")
```

#### Issue: Validation failures
**Solution:**
```python
# Check validation settings
is_valid, errors = config_manager.validate_synthetic_data_config()
if not is_valid:
    print(f"Configuration errors: {errors}")
    
# Relax validation tolerances
config_manager.config.update({
    'VALIDATION_PRICE_TOLERANCE': 0.005,  # Increase to 0.5%
    'VALIDATION_VOLUME_TOLERANCE': 0.10,  # Increase to 10%
    'VALIDATION_VWAP_TOLERANCE': 0.005    # Increase to 0.5%
})
```

#### Issue: Poor performance with validation enabled
**Solution:**
```python
# Option 1: Disable validation for performance testing
config_manager.config['ENABLE_SYNTHETIC_DATA_VALIDATION'] = False

# Option 2: Use relaxed validation settings
config_manager.apply_synthetic_data_preset('market_simulation')  # Has reasonable validation
```

#### Issue: FMV correlation too weak/strong
**Solution:**
```python
# Adjust correlation based on market regime
config_manager.config.update({
    'SYNTHETIC_FMV_TRENDING_CORRELATION': 0.92,   # Stronger trending correlation
    'SYNTHETIC_FMV_SIDEWAYS_CORRELATION': 0.68,   # Weaker sideways correlation
    'SYNTHETIC_FMV_VOLATILE_CORRELATION': 0.55    # Much weaker volatile correlation
})
```

### Configuration Validation Errors

Common validation errors and solutions:

| Error | Cause | Solution |
|-------|-------|----------|
| "Multi-frequency enabled but no frequency streams are active" | All frequency flags are False | Enable at least one frequency stream |
| "Per-second frequency outside valid range" | Frequency < 0.1 or > 60.0 | Set frequency between 0.1 and 60.0 seconds |
| "FMV update interval outside valid range" | Interval < 5 or > 300 | Set interval between 5 and 300 seconds |
| "Correlation parameter outside valid range" | Correlation < 0.0 or > 1.0 | Set correlation between 0.0 and 1.0 |

### Performance Monitoring

```python
# Monitor generation statistics
provider = SimulatedDataProvider(config_manager.config)
stats = provider.get_generation_statistics()

print(f"Total legacy ticks: {stats['total_legacy_ticks']}")
print(f"Active generators: {stats['active_generators']}")

for freq, freq_stats in stats['frequencies'].items():
    print(f"{freq}: {freq_stats['count']} generated")
    
# Monitor validation if enabled
if provider._validator:
    validation_summary = provider.get_validation_summary()
    print(f"Validation success rate: {validation_summary['success_rate']:.1%}")
```

## Configuration Reference

### Complete Configuration Template

```python
complete_config = {
    # Master controls
    'ENABLE_MULTI_FREQUENCY': True,
    'WEBSOCKET_PER_SECOND_ENABLED': True,
    'WEBSOCKET_PER_MINUTE_ENABLED': True,
    'WEBSOCKET_FAIR_VALUE_ENABLED': True,
    'ENABLE_SYNTHETIC_DATA_VALIDATION': True,
    
    # Per-second generator
    'SYNTHETIC_ACTIVITY_LEVEL': 'medium',
    'SYNTHETIC_PER_SECOND_FREQUENCY': 1.0,
    'SYNTHETIC_PER_SECOND_PRICE_VARIANCE': 0.001,
    'SYNTHETIC_PER_SECOND_VOLUME_RANGE': [10000, 100000],
    
    # Per-minute generator
    'SYNTHETIC_PER_MINUTE_WINDOW': 60,
    'SYNTHETIC_PER_MINUTE_MIN_TICKS': 5,
    'SYNTHETIC_PER_MINUTE_MAX_TICKS': 30,
    'SYNTHETIC_PER_MINUTE_OHLC_VARIANCE': 0.005,
    'SYNTHETIC_PER_MINUTE_VOLUME_MULTIPLIER': 5.0,
    
    # FMV generator - basic
    'SYNTHETIC_FMV_UPDATE_INTERVAL': 30,
    'SYNTHETIC_FMV_CORRELATION': 0.85,
    'SYNTHETIC_FMV_VARIANCE': 0.002,
    'SYNTHETIC_FMV_PREMIUM_RANGE': 0.01,
    
    # FMV generator - advanced correlation
    'SYNTHETIC_FMV_MOMENTUM_DECAY': 0.7,
    'SYNTHETIC_FMV_LAG_FACTOR': 0.3,
    'SYNTHETIC_FMV_VOLATILITY_DAMPENING': 0.6,
    'SYNTHETIC_FMV_TRENDING_CORRELATION': 0.90,
    'SYNTHETIC_FMV_SIDEWAYS_CORRELATION': 0.75,
    'SYNTHETIC_FMV_VOLATILE_CORRELATION': 0.65,
    
    # Validation settings
    'VALIDATION_PRICE_TOLERANCE': 0.001,
    'VALIDATION_VOLUME_TOLERANCE': 0.05,
    'VALIDATION_VWAP_TOLERANCE': 0.002,
    
    # System settings
    'MARKET_TIMEZONE': 'US/Eastern'
}
```

This configuration documentation provides comprehensive guidance for all aspects of the multi-frequency synthetic data system, from quick setup to advanced tuning and troubleshooting.