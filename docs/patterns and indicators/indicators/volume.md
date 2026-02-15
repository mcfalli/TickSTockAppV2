### Volume Indicator Calculation Instructions for TickStock.ai

**Created**: February 15, 2026
**Category**: volume
**Display Order**: 60
**Implementation**: `src/analysis/indicators/volume/volume.py`

---

## Overview

**Description**: Volume confirmation indicator that measures trading activity relative to historical averages to validate price moves and identify accumulation/distribution phases.

**Formula**:
```
Relative Volume = Current Volume / SMA(Volume, period)
Signal = High (>1.5x) | Normal (0.5x-1.5x) | Low (<0.5x)
```

**Interpretation**:
- **High Volume** (>1.5x average): Strong conviction in price move, validates breakouts/breakdowns
- **Normal Volume** (0.5x-1.5x): Typical trading activity, no special significance
- **Low Volume** (<0.5x average): Weak conviction, price moves may be unreliable

**Typical Range**: 0 to unbounded (relative ratio), typically 0.1x to 5.0x

**Parameters**:
- `period`: 20 - Lookback period for volume moving average
- `threshold_high`: 1.5 - Multiplier for high volume signal
- `threshold_low`: 0.5 - Multiplier for low volume signal

---

## Storage Schema

**Table**: `daily_indicators`

**Columns**:
- `symbol` — ticker (text)
- `indicator_type` — lowercase with underscore: 'volume'
- `calculation_timestamp` — exact minute (intraday) or day-end timestamp (EOD)
- `timeframe` — '1min' or 'daily'
- `value_data` — JSONB with calculation results:
  ```json
  {
    "volume": 1234567,
    "volume_sma": 987654,
    "relative_volume": 1.25,
    "signal": "normal"
  }
  ```
- `metadata` — JSONB with context:
  ```json
  {
    "source": "batch_eod",
    "period": 20,
    "threshold_high": 1.5,
    "threshold_low": 0.5
  }
  ```
- `expiration_date` — timestamp when data becomes stale (next day at market close)

**Persistence Pattern** (Sprint 74 - TimescaleDB Hypertables):
```sql
-- DELETE existing entry
DELETE FROM daily_indicators
WHERE symbol = :symbol
  AND indicator_type = 'volume'
  AND timeframe = :timeframe;

-- INSERT new entry
INSERT INTO daily_indicators
(symbol, indicator_type, value_data, calculation_timestamp,
 expiration_date, timeframe, metadata)
VALUES (:symbol, 'volume', :value_data, NOW(),
        :expiration_date, :timeframe, :metadata);
```

---

## Calculation Details

### Data Requirements

**Minimum Bars Required**: 20 bars (default period)

**Data Validation**:
- If `len(data) < period`, return `None` and skip storage
- Required columns: `['volume']`
- Check for NaN values in volume column
- Check for negative volume values (invalid)

### Step-by-Step Calculation

**Step 1**: Calculate volume moving average baseline
```python
volume_sma = data['volume'].rolling(window=period).mean()
```

**Step 2**: Calculate relative volume ratio
```python
relative_volume = data['volume'] / volume_sma
```

**Step 3**: Classify volume signal
```python
if relative_volume > threshold_high:
    signal = "high"
elif relative_volume < threshold_low:
    signal = "low"
else:
    signal = "normal"
```

### Pandas Implementation

```python
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Optional

@dataclass
class VolumeParams:
    """Volume indicator parameters."""
    period: int = 20
    threshold_high: float = 1.5
    threshold_low: float = 0.5

class VolumeIndicator:
    """
    Volume confirmation indicator.

    Measures trading activity relative to historical averages to validate
    price moves and identify accumulation/distribution phases.

    Calculation:
    - Volume SMA baseline over period
    - Relative volume ratio (current / SMA)
    - Signal classification (high/normal/low)
    """

    def __init__(self, params: Optional[dict] = None):
        """Initialize Volume indicator."""
        if params is None:
            params = {}
        self.params = VolumeParams(**params)
        self.name = "volume"
        self.category = "volume"

    def calculate(self, data: pd.DataFrame) -> Optional[dict]:
        """
        Calculate Volume indicator.

        Args:
            data: DataFrame with OHLCV columns (volume required)

        Returns:
            Dictionary with indicator_type, value_data, metadata
        """
        # Validate data
        if len(data) < self.params.period:
            return None

        if 'volume' not in data.columns:
            return None

        # Check for invalid volume data
        if (data['volume'] < 0).any():
            return None

        # Calculate volume SMA baseline
        volume_sma = data['volume'].rolling(window=self.params.period).mean()

        # Calculate relative volume ratio
        relative_volume = data['volume'] / volume_sma

        # Extract latest values
        latest_volume = float(data['volume'].iloc[-1])
        latest_volume_sma = float(volume_sma.iloc[-1])
        latest_relative_volume = float(relative_volume.iloc[-1])

        # Skip if any NaN values
        if pd.isna(latest_volume) or pd.isna(latest_volume_sma) or pd.isna(latest_relative_volume):
            return None

        # Classify volume signal
        if latest_relative_volume > self.params.threshold_high:
            signal = "high"
        elif latest_relative_volume < self.params.threshold_low:
            signal = "low"
        else:
            signal = "normal"

        # Return formatted result
        return {
            "indicator_type": "volume",
            "value_data": {
                "volume": latest_volume,
                "volume_sma": latest_volume_sma,
                "relative_volume": latest_relative_volume,
                "signal": signal
            },
            "metadata": {
                "period": self.params.period,
                "threshold_high": self.params.threshold_high,
                "threshold_low": self.params.threshold_low
            }
        }
```

---

## Dependencies

**Requires** (Processing Order):
- None - uses only OHLCV data (volume column)

**Used By** (Downstream Dependencies):
- Pattern confirmation (e.g., breakout patterns require high volume)
- Trend strength analysis (combine with price action)

**Database Definition**:
```sql
-- indicator_definitions table entry
INSERT INTO indicator_definitions
(name, display_order, category, class_name, method_name,
 instantiation_params, min_bars_required, enabled,
 short_description, display_name)
VALUES
('volume', 60, 'volume', 'VolumeIndicator', 'calculate',
 '{"period": 20, "threshold_high": 1.5, "threshold_low": 0.5}', 20, true,
 'Volume confirmation indicator with relative volume signals', 'Volume');
```

---

## Validation Rules

**Data Quality**:
- ✅ No gaps > 5 consecutive trading days
- ✅ No duplicate timestamps
- ✅ All volume values ≥ 0
- ✅ No NaN values in volume column

**Calculation Validation**:
- ✅ Output value in expected range: 0 to unbounded (typically 0.1-5.0)
- ✅ No NaN values unless insufficient data
- ✅ Precision: float64
- ✅ Relative volume = current volume / SMA volume

**Regression Testing**:
- Compare against TradingView volume indicator
- Tolerance: ±0.01 for relative volume ratio

---

## Error Handling & Logging

```python
import logging
logger = logging.getLogger(__name__)

# Insufficient data
if len(data) < self.params.period:
    logger.warning(f"Volume: Insufficient data for {symbol} - need {self.params.period}, have {len(data)}")
    return None

# Missing volume column
if 'volume' not in data.columns:
    logger.error(f"Volume: Missing 'volume' column for {symbol}")
    return None

# Invalid volume values
if (data['volume'] < 0).any():
    logger.warning(f"Volume: Invalid negative volume detected for {symbol}")
    return None

# Calculation error
try:
    volume_sma = data['volume'].rolling(window=self.params.period).mean()
    relative_volume = data['volume'] / volume_sma
except Exception as e:
    logger.error(f"Volume: Calculation failed for {symbol}: {e}", exc_info=True)
    return None

# NaN in results
if pd.isna(latest_relative_volume):
    logger.warning(f"Volume: NaN value in relative volume for {symbol}")
    return None
```

---

## Performance Targets

| Operation | Target | Notes |
|-----------|--------|----------|
| Calculation (single period) | <5ms | Vectorized pandas rolling mean + division |
| Data fetch | <50ms | Database query |
| Persistence (DELETE + INSERT) | <20ms | Two SQL operations |
| **Total: Indicator update** | **<100ms** | End-to-end latency |

---

## Testing

**Unit Tests** (`tests/unit/indicators/test_volume.py`):
```python
import pytest
import pandas as pd
from src.analysis.indicators.volume.volume import VolumeIndicator

def test_volume_calculation():
    """Test Volume calculation with known data."""
    # Test data with clear high volume spike
    data = pd.DataFrame({
        'volume': [100000] * 19 + [300000]  # 3x spike on last bar
    })

    # Calculate
    indicator = VolumeIndicator({'period': 20, 'threshold_high': 1.5})
    result = indicator.calculate(data)

    # Assert
    assert result is not None
    assert result['value_data']['signal'] == 'high'
    assert result['value_data']['relative_volume'] == pytest.approx(3.0, rel=0.01)

def test_volume_low_signal():
    """Test low volume signal detection."""
    data = pd.DataFrame({
        'volume': [100000] * 19 + [30000]  # 0.3x on last bar
    })

    indicator = VolumeIndicator({'period': 20, 'threshold_low': 0.5})
    result = indicator.calculate(data)

    assert result['value_data']['signal'] == 'low'
    assert result['value_data']['relative_volume'] < 0.5

def test_volume_normal_signal():
    """Test normal volume signal."""
    data = pd.DataFrame({
        'volume': [100000] * 20  # Consistent volume
    })

    indicator = VolumeIndicator({'period': 20})
    result = indicator.calculate(data)

    assert result['value_data']['signal'] == 'normal'
    assert result['value_data']['relative_volume'] == pytest.approx(1.0, rel=0.01)

def test_volume_insufficient_data():
    """Test handling of insufficient data."""
    data = pd.DataFrame({'volume': [100000] * 10})  # Only 10 bars

    indicator = VolumeIndicator({'period': 20})
    result = indicator.calculate(data)

    assert result is None

def test_volume_missing_column():
    """Test handling of missing volume column."""
    data = pd.DataFrame({
        'close': [100, 101, 102]
    })

    indicator = VolumeIndicator()
    result = indicator.calculate(data)

    assert result is None

def test_volume_negative_values():
    """Test handling of invalid negative volume."""
    data = pd.DataFrame({
        'volume': [100000] * 19 + [-50000]  # Invalid negative
    })

    indicator = VolumeIndicator({'period': 20})
    result = indicator.calculate(data)

    assert result is None

def test_volume_custom_thresholds():
    """Test custom threshold parameters."""
    data = pd.DataFrame({
        'volume': [100000] * 19 + [220000]  # 2.2x
    })

    # With default threshold (1.5), should be high
    indicator_default = VolumeIndicator({'period': 20})
    result_default = indicator_default.calculate(data)
    assert result_default['value_data']['signal'] == 'high'

    # With custom threshold (2.5), should be normal
    indicator_custom = VolumeIndicator({'period': 20, 'threshold_high': 2.5})
    result_custom = indicator_custom.calculate(data)
    assert result_custom['value_data']['signal'] == 'normal'

def test_volume_different_periods():
    """Test different period values."""
    data = pd.DataFrame({
        'volume': [100000] * 50
    })

    # Period 10
    indicator_10 = VolumeIndicator({'period': 10})
    result_10 = indicator_10.calculate(data)
    assert result_10 is not None
    assert result_10['metadata']['period'] == 10

    # Period 50
    indicator_50 = VolumeIndicator({'period': 50})
    result_50 = indicator_50.calculate(data)
    assert result_50 is not None
    assert result_50['metadata']['period'] == 50
```

**Integration Tests**:
- Verify DELETE + INSERT prevents duplicates
- Verify timeframe separation (1min vs daily)
- Verify metadata tracking

---

## References

**Technical Documentation**:
- [Investopedia: Volume Analysis](https://www.investopedia.com/terms/v/volume.asp)
- [TradingView: Volume Indicator](https://www.tradingview.com/support/solutions/43000502040-volume/)

**Code References**:
- `src/analysis/indicators/volume/volume.py` - Implementation
- `src/analysis/indicators/base_indicator.py` - Base class
- `docs/patterns and indicators/indicators/sma_ema_calculations.md` - Similar moving average logic

---

## Document Status

**Version**: 1.0
**Last Updated**: February 15, 2026
**Status**: ✅ **READY FOR IMPLEMENTATION**
**Sprint**: Sprint 78 - Complete Table 1 Indicators
