### VWAP (Volume Weighted Average Price) Calculation Instructions for TickStock.ai

**Created**: February 15, 2026
**Category**: volume
**Display Order**: 61
**Implementation**: `src/analysis/indicators/volume/vwap.py`

---

## Overview

**Description**: Volume Weighted Average Price (VWAP) is an intra-day fair-value benchmark that represents the average price weighted by volume. It resets at market open and provides deviation bands for overbought/oversold signals.

**Formula**:
```
Typical Price = (High + Low + Close) / 3
VWAP = Σ(Typical Price × Volume) / Σ(Volume)
Session reset: Daily (at date change or first bar of new day)
Deviation Bands:
  Upper 1σ = VWAP + (1 × Standard Deviation)
  Upper 2σ = VWAP + (2 × Standard Deviation)
  Lower 1σ = VWAP - (1 × Standard Deviation)
  Lower 2σ = VWAP - (2 × Standard Deviation)
```

**Interpretation**:
- **Price > VWAP**: Bullish, buying pressure above average
- **Price < VWAP**: Bearish, selling pressure below average
- **Price at VWAP**: Fair value, equilibrium
- **Price > Upper 2σ**: Overbought, potential reversal
- **Price < Lower 2σ**: Oversold, potential reversal

**Typical Range**: Same scale as price (e.g., $100-$200 for a $150 stock)

**Parameters**:
- None - VWAP is calculated cumulatively from session start

**Session Behavior**:
- Resets daily at date change (first bar of new day)
- Cumulative calculation throughout the day
- Includes all available bars (regular hours, pre-market, after-hours)
- Most meaningful during active trading periods

---

## Storage Schema

**Table**: `daily_indicators`

**Columns**:
- `symbol` — ticker (text)
- `indicator_type` — lowercase with underscore: 'vwap'
- `calculation_timestamp` — exact minute timestamp
- `timeframe` — '1min' (intra-day only)
- `value_data` — JSONB with calculation results:
  ```json
  {
    "vwap": 150.25,
    "vwap_upper_1sd": 151.00,
    "vwap_upper_2sd": 151.75,
    "vwap_lower_1sd": 149.50,
    "vwap_lower_2sd": 148.75,
    "position": "above"
  }
  ```
- `metadata` — JSONB with context:
  ```json
  {
    "source": "websocket_1min",
    "calculation_date": "2026-02-15",
    "bars_in_day": 390
  }
  ```
- `expiration_date` — timestamp when data becomes stale (next day)

**Persistence Pattern** (Sprint 74 - TimescaleDB Hypertables):
```sql
-- DELETE existing entry (per-minute updates)
DELETE FROM daily_indicators
WHERE symbol = :symbol
  AND indicator_type = 'vwap'
  AND timeframe = '1min'
  AND calculation_timestamp::date = CURRENT_DATE;

-- INSERT new entry
INSERT INTO daily_indicators
(symbol, indicator_type, value_data, calculation_timestamp,
 expiration_date, timeframe, metadata)
VALUES (:symbol, 'vwap', :value_data, NOW(),
        :expiration_date, '1min', :metadata);
```

---

## Calculation Details

### Data Requirements

**Minimum Bars Required**: 1 bar (calculates from first bar of session)

**Data Validation**:
- Required columns: `['high', 'low', 'close', 'volume', 'date']` or `['high', 'low', 'close', 'volume', 'timestamp']`
- Check for NaN values in required columns
- Check for valid date/timestamps (detect day boundaries)
- No market hours restriction - includes pre-market, regular hours, after-hours

### Step-by-Step Calculation

**Step 1**: Extract date for daily grouping
```python
# Use date column if available, otherwise extract from timestamp
if 'date' in data.columns:
    data['day'] = pd.to_datetime(data['date']).dt.date
else:
    data['day'] = pd.to_datetime(data['timestamp']).dt.date
```

**Step 2**: Calculate typical price
```python
typical_price = (data['high'] + data['low'] + data['close']) / 3
```

**Step 3**: Calculate cumulative VWAP (resets daily)
```python
# Calculate cumulative sums per day
data['pv'] = typical_price * data['volume']
cumulative_pv = data.groupby('day')['pv'].cumsum()
cumulative_volume = data.groupby('day')['volume'].cumsum()

# VWAP = Cumulative (Price × Volume) / Cumulative Volume
vwap = cumulative_pv / cumulative_volume
```

**Step 4**: Calculate deviation bands
```python
# Calculate squared deviations
squared_diff = (typical_price - vwap) ** 2
cumulative_squared_diff = (squared_diff * data['volume']).groupby('day').cumsum()

# Standard deviation
variance = cumulative_squared_diff / cumulative_volume
std_dev = np.sqrt(variance)

# Deviation bands
vwap_upper_1sd = vwap + std_dev
vwap_upper_2sd = vwap + (2 * std_dev)
vwap_lower_1sd = vwap - std_dev
vwap_lower_2sd = vwap - (2 * std_dev)
```

**Step 5**: Determine price position relative to VWAP
```python
current_price = data['close'].iloc[-1]
current_vwap = vwap.iloc[-1]

if current_price > current_vwap:
    position = "above"
elif current_price < current_vwap:
    position = "below"
else:
    position = "at"
```

### Pandas Implementation

```python
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Optional

@dataclass
class VWAPParams:
    """VWAP indicator parameters."""
    # No parameters - VWAP is calculated cumulatively from day start
    pass

class VWAPIndicator:
    """
    Volume Weighted Average Price (VWAP) indicator.

    Fair-value benchmark that resets daily at date change.
    Provides cumulative VWAP with deviation bands for overbought/oversold signals.

    Calculation:
    - Typical Price = (High + Low + Close) / 3
    - VWAP = Σ(Typical Price × Volume) / Σ(Volume)
    - Daily reset (first bar of new day)
    - Deviation bands (1σ, 2σ) for volatility context
    - Includes all trading hours (pre-market, regular, after-hours)
    """

    def __init__(self, params: Optional[dict] = None):
        """Initialize VWAP indicator."""
        self.params = VWAPParams()
        self.name = "vwap"
        self.category = "volume"

    def calculate(self, data: pd.DataFrame) -> Optional[dict]:
        """
        Calculate VWAP indicator with deviation bands.

        Args:
            data: DataFrame with OHLCV columns and date/timestamp

        Returns:
            Dictionary with indicator_type, value_data, metadata
        """
        # Validate data
        required_cols = ['high', 'low', 'close', 'volume']
        if not all(col in data.columns for col in required_cols):
            return None

        if len(data) < 1:
            return None

        # Check for NaN values
        if data[['high', 'low', 'close', 'volume']].isna().any().any():
            return None

        # Extract date for daily grouping
        data_copy = data.copy()
        if 'date' in data_copy.columns:
            data_copy['day'] = pd.to_datetime(data_copy['date']).dt.date
        elif 'timestamp' in data_copy.columns:
            if not pd.api.types.is_datetime64_any_dtype(data_copy['timestamp']):
                data_copy['timestamp'] = pd.to_datetime(data_copy['timestamp'])
            data_copy['day'] = data_copy['timestamp'].dt.date
        else:
            return None

        # Calculate typical price
        typical_price = (data_copy['high'] + data_copy['low'] + data_copy['close']) / 3

        # Calculate cumulative sums per day
        data_copy['pv'] = typical_price * data_copy['volume']
        cumulative_pv = data_copy.groupby('day')['pv'].cumsum()
        cumulative_volume = data_copy.groupby('day')['volume'].cumsum()

        # VWAP = Cumulative (Price × Volume) / Cumulative Volume
        vwap = cumulative_pv / cumulative_volume

        # Calculate deviation bands
        squared_diff = (typical_price - vwap) ** 2
        data_copy['squared_diff_pv'] = squared_diff * data_copy['volume']
        cumulative_squared_diff = data_copy.groupby('day')['squared_diff_pv'].cumsum()

        # Standard deviation
        variance = cumulative_squared_diff / cumulative_volume
        std_dev = np.sqrt(variance)

        # Deviation bands
        vwap_upper_1sd = vwap + std_dev
        vwap_upper_2sd = vwap + (2 * std_dev)
        vwap_lower_1sd = vwap - std_dev
        vwap_lower_2sd = vwap - (2 * std_dev)

        # Extract latest values
        latest_vwap = float(vwap.iloc[-1])
        latest_upper_1sd = float(vwap_upper_1sd.iloc[-1])
        latest_upper_2sd = float(vwap_upper_2sd.iloc[-1])
        latest_lower_1sd = float(vwap_lower_1sd.iloc[-1])
        latest_lower_2sd = float(vwap_lower_2sd.iloc[-1])
        current_price = float(data_copy['close'].iloc[-1])

        # Skip if any NaN values
        if any(pd.isna(val) for val in [latest_vwap, latest_upper_1sd, latest_upper_2sd,
                                         latest_lower_1sd, latest_lower_2sd, current_price]):
            return None

        # Determine price position relative to VWAP
        if current_price > latest_vwap:
            position = "above"
        elif current_price < latest_vwap:
            position = "below"
        else:
            position = "at"

        # Get day metadata
        current_day = data_copy['day'].iloc[-1]
        bars_in_day = int((data_copy['day'] == current_day).sum())

        # Return formatted result
        return {
            "indicator_type": "vwap",
            "value_data": {
                "vwap": latest_vwap,
                "vwap_upper_1sd": latest_upper_1sd,
                "vwap_upper_2sd": latest_upper_2sd,
                "vwap_lower_1sd": latest_lower_1sd,
                "vwap_lower_2sd": latest_lower_2sd,
                "position": position
            },
            "metadata": {
                "calculation_date": str(current_day),
                "bars_in_day": bars_in_day
            }
        }
```

---

## Dependencies

**Requires** (Processing Order):
- None - uses only OHLCV data with timestamps

**Used By** (Downstream Dependencies):
- Intra-day mean reversion strategies
- Institutional order flow analysis
- Fair value benchmarking

**External Libraries**:
- None - uses standard pandas datetime handling

**Database Definition**:
```sql
-- indicator_definitions table entry
INSERT INTO indicator_definitions
(name, display_order, category, class_name, method_name,
 instantiation_params, min_bars_required, enabled,
 short_description, display_name)
VALUES
('vwap', 61, 'volume', 'VWAPIndicator', 'calculate',
 '{}', 1, true,
 'Volume Weighted Average Price with deviation bands', 'VWAP');
```

---

## Validation Rules

**Data Quality**:
- ✅ No duplicate timestamps
- ✅ All OHLC values positive
- ✅ Volume ≥ 0
- ✅ Valid date or timestamp column available

**Calculation Validation**:
- ✅ VWAP in reasonable range (near current price)
- ✅ Deviation bands symmetric around VWAP
- ✅ Upper bands > VWAP > Lower bands
- ✅ No NaN values unless insufficient data
- ✅ Precision: float64

**Regression Testing**:
- Compare against TradingView VWAP indicator
- Tolerance: ±$0.01 for typical stock prices

---

## Error Handling & Logging

```python
import logging
logger = logging.getLogger(__name__)

# Missing columns
required_cols = ['high', 'low', 'close', 'volume']
if not all(col in data.columns for col in required_cols):
    logger.error(f"VWAP: Missing required columns for {symbol}")
    return None

# Missing date column
if 'date' not in data.columns and 'timestamp' not in data.columns:
    logger.error(f"VWAP: Missing date or timestamp column for {symbol}")
    return None

# Insufficient data
if len(data) < 1:
    logger.warning(f"VWAP: No data available for {symbol}")
    return None

# NaN values
if data[['high', 'low', 'close', 'volume']].isna().any().any():
    logger.warning(f"VWAP: NaN values detected for {symbol}")
    return None

# Calculation error
try:
    vwap = cumulative_pv / cumulative_volume
except Exception as e:
    logger.error(f"VWAP: Calculation failed for {symbol}: {e}", exc_info=True)
    return None

# Data gap warning
if bars_in_day > 1440:  # More than 24 hours of 1-minute bars
    logger.warning(f"VWAP: Unexpected bar count for {symbol} - {bars_in_day} bars in single day")
    metadata['bar_count_warning'] = True
```

---

## Performance Targets

| Operation | Target | Notes |
|-----------|--------|-------|
| Calculation (1min bar) | <10ms | Vectorized pandas groupby + cumsum |
| Session boundary detection | <2ms | Timezone conversion + comparison |
| Data fetch | <50ms | Database query |
| Persistence (DELETE + INSERT) | <20ms | Two SQL operations |
| **Total: Indicator update** | **<100ms** | End-to-end latency |

---

## Testing

**Unit Tests** (`tests/unit/indicators/test_vwap.py`):
```python
import pytest
import pandas as pd
from datetime import date, datetime, timedelta
from src.analysis.indicators.volume.vwap import VWAPIndicator

def test_vwap_calculation():
    """Test VWAP calculation with known data."""
    # Test data: Single day with 6 bars
    data = pd.DataFrame({
        'date': [date(2026, 2, 15)] * 6,
        'high': [100.5, 101.0, 101.5, 102.0, 102.5, 103.0],
        'low': [100.0, 100.5, 101.0, 101.5, 102.0, 102.5],
        'close': [100.2, 100.7, 101.2, 101.7, 102.2, 102.7],
        'volume': [1000, 1500, 2000, 1800, 1200, 1000]
    })

    # Calculate
    indicator = VWAPIndicator()
    result = indicator.calculate(data)

    # Assert
    assert result is not None
    assert 'vwap' in result['value_data']
    assert result['value_data']['vwap'] > 100.0
    assert result['value_data']['vwap'] < 103.0
    assert result['metadata']['bars_in_day'] == 6

def test_vwap_daily_reset():
    """Test VWAP daily reset at date change."""
    # Day 1: 3 bars
    day1_data = pd.DataFrame({
        'date': [date(2026, 2, 14)] * 3,
        'high': [100, 101, 102],
        'low': [99, 100, 101],
        'close': [99.5, 100.5, 101.5],
        'volume': [1000, 1000, 1000]
    })

    # Day 2: 3 bars (should reset)
    day2_data = pd.DataFrame({
        'date': [date(2026, 2, 15)] * 3,
        'high': [200, 201, 202],
        'low': [199, 200, 201],
        'close': [199.5, 200.5, 201.5],
        'volume': [1000, 1000, 1000]
    })

    # Concatenate
    data = pd.concat([day1_data, day2_data], ignore_index=True)

    indicator = VWAPIndicator()
    result = indicator.calculate(data)

    # VWAP should be near day 2 prices (daily reset)
    assert result['value_data']['vwap'] > 199.0
    assert result['value_data']['vwap'] < 203.0
    assert result['metadata']['bars_in_day'] == 3  # Only day 2 bars

def test_vwap_deviation_bands():
    """Test VWAP deviation band calculation."""
    data = pd.DataFrame({
        'date': [date(2026, 2, 15)] * 10,
        'high': [100 + i for i in range(10)],
        'low': [100 + i - 0.5 for i in range(10)],
        'close': [100 + i for i in range(10)],
        'volume': [1000] * 10
    })

    indicator = VWAPIndicator()
    result = indicator.calculate(data)

    # Assert band structure
    assert result['value_data']['vwap_upper_2sd'] > result['value_data']['vwap_upper_1sd']
    assert result['value_data']['vwap_upper_1sd'] > result['value_data']['vwap']
    assert result['value_data']['vwap'] > result['value_data']['vwap_lower_1sd']
    assert result['value_data']['vwap_lower_1sd'] > result['value_data']['vwap_lower_2sd']

def test_vwap_position_above():
    """Test price position detection (above VWAP)."""
    # Price increasing above VWAP
    data = pd.DataFrame({
        'date': [date(2026, 2, 15)] * 5,
        'high': [100, 100, 100, 105, 105],
        'low': [100, 100, 100, 105, 105],
        'close': [100, 100, 100, 105, 105],
        'volume': [1000] * 5
    })

    indicator = VWAPIndicator()
    result = indicator.calculate(data)

    assert result['value_data']['position'] == 'above'

def test_vwap_position_below():
    """Test price position detection (below VWAP)."""
    # Price decreasing below VWAP
    data = pd.DataFrame({
        'date': [date(2026, 2, 15)] * 5,
        'high': [100, 100, 100, 95, 95],
        'low': [100, 100, 100, 95, 95],
        'close': [100, 100, 100, 95, 95],
        'volume': [1000] * 5
    })

    indicator = VWAPIndicator()
    result = indicator.calculate(data)

    assert result['value_data']['position'] == 'below'

def test_vwap_insufficient_data():
    """Test handling of empty data."""
    data = pd.DataFrame()

    indicator = VWAPIndicator()
    result = indicator.calculate(data)

    assert result is None

def test_vwap_missing_columns():
    """Test handling of missing required columns."""
    data = pd.DataFrame({
        'close': [100, 101, 102]
    })

    indicator = VWAPIndicator()
    result = indicator.calculate(data)

    assert result is None

def test_vwap_nan_values():
    """Test handling of NaN values in data."""
    data = pd.DataFrame({
        'date': [date(2026, 2, 15)] * 5,
        'high': [100, 101, None, 103, 104],  # NaN in middle
        'low': [99, 100, 101, 102, 103],
        'close': [99.5, 100.5, 101.5, 102.5, 103.5],
        'volume': [1000] * 5
    })

    indicator = VWAPIndicator()
    result = indicator.calculate(data)

    assert result is None
```

**Integration Tests**:
- Verify DELETE + INSERT prevents duplicates
- Verify 1min timeframe storage
- Verify session metadata tracking
- Verify real-time WebSocket updates

---

## References

**Technical Documentation**:
- [Investopedia: VWAP](https://www.investopedia.com/terms/v/vwap.asp)
- [TradingView: VWAP Indicator](https://www.tradingview.com/support/solutions/43000502040-vwap/)
- [CME Group: VWAP Trading](https://www.cmegroup.com/education/courses/introduction-to-algorithmic-trading/vwap-trading.html)

**Code References**:
- `src/analysis/indicators/volume/vwap.py` - Implementation
- `src/analysis/indicators/base_indicator.py` - Base class
- `docs/patterns and indicators/indicators/volume.md` - Related volume indicator

---

## Document Status

**Version**: 1.0
**Last Updated**: February 15, 2026
**Status**: ✅ **READY FOR IMPLEMENTATION**
**Sprint**: Sprint 78 - Complete Table 1 Indicators
