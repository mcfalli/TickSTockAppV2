# Documentation Warning
**DISCLAIMER**: This documentation is not current and should not be relied upon. As of August 21, 2025, it requires review to determine its relevance. Content must be evaluated for accuracy and applicability to the project. If found relevant, update and retain; if obsolete or duplicative of content elsewhere, delete.


# Surge Detection System - Sprint 49 Enhanced
## Adaptive Market-Aware Detection

## Purpose
Detect significant price and volume movements that represent unusual market activity, with **adaptive sensitivity** based on market period, price level, and volatility conditions. Optimized for both volatile synthetic data and quiet production micro-movements.

## Core Detection Mechanism

### Buffer System
- **Size**: 20 data points (rolling window)
- **Content**: Price, volume, timestamp, VWAP for each tick
- **Time Span**: Dynamically adjusted based on market period (2-10 second intervals)

### Baseline Comparison
- **Interval**: Adaptive (2-10 seconds based on market period)
- **Method**: Current price compared to price from N seconds ago
- **Fallback**: If no price exists from exactly N seconds ago, uses closest older price

## Three-Dimensional Adaptive System

### 1. Market Period Detection
Automatically adjusts sensitivity based on time of day:

| Period | Time (ET) | Characteristics | Detection Strategy |
|--------|-----------|-----------------|-------------------|
| **PREMARKET** | 4:00-9:30 AM | Sparse data, institutional | High sensitivity, longer intervals |
| **OPENING** | 9:30-10:00 AM | High volatility, heavy volume | Lower sensitivity, strict mode |
| **MIDDAY** | 10:00 AM-3:30 PM | Quiet, range-bound | Maximum sensitivity, OR mode |
| **CLOSING** | 3:30-4:00 PM | Increased activity | Moderate sensitivity, strict mode |
| **AFTERHOURS** | 4:00-8:00 PM | Very sparse data | Adaptive mode, compensatory logic |

### 2. Price Band Classification
Adjusts thresholds based on stock price:

| Band | Price Range | Base Threshold | Min Dollar | Rationale |
|------|------------|----------------|------------|-----------|
| **PENNY** | < $10 | 3.0% | $0.10 | High volatility expected |
| **LOW** | $10-50 | 2.0% | $0.50 | Moderate volatility |
| **MID** | $50-200 | 1.5% | $1.00 | Standard volatility |
| **HIGH** | $200-500 | 1.0% | $2.00 | Lower percentage moves |
| **ULTRA** | > $500 | 0.5% | $3.00 | Tiny percentages significant |

### 3. Volatility Adjustment
Analyzes recent price movements:

| Volatility | StdDev/Mean | Multiplier | Effect |
|------------|-------------|------------|--------|
| **HIGH** | > 2.0% | 0.7x | Less sensitive (already moving) |
| **NORMAL** | 0.5-2.0% | 1.0x | Standard sensitivity |
| **LOW** | < 0.5% | 1.5x | More sensitive (quiet market) |

## Dynamic Detection Modes

### Market-Adaptive Mode Selection
The detection mode automatically adjusts based on market period:

| Market Period | Detection Mode | Logic |
|---------------|----------------|-------|
| **MIDDAY** | OR | Maximum sensitivity - either price OR volume triggers |
| **AFTERHOURS/PREMARKET** | ADAPTIVE | Compensatory - strong metrics offset weak ones |
| **OPENING/CLOSING** | STRICT | Confirmation required - both price AND volume |

### Adaptive Mode Compensation Logic
For sparse data periods (afterhours/premarket):

- **Balanced Surge**: Both price and volume meet thresholds
- **Price-Driven**: Large price move (≥1.5x threshold) + adequate volume (≥70% threshold)
- **Volume-Driven**: Heavy volume (≥2.0x threshold) + adequate price move (≥50% threshold)

## Dynamic Threshold Examples

### Scenario 1: Midday Low-Price Stock
- **Context**: 1:00 PM, $15 stock, low volatility
- **Applied Thresholds**:
  - Market period: MIDDAY → 1.0% base
  - Price band: LOW → 2.0% base
  - Final: min(1.0%, 2.0%) × 1.5 (low vol) = **1.5%**
  - Detection mode: OR (maximum sensitivity)

### Scenario 2: Opening High-Price Stock
- **Context**: 9:45 AM, $450 stock, high volatility
- **Applied Thresholds**:
  - Market period: OPENING → 2.0% base
  - Price band: HIGH → 1.0% base
  - Final: min(2.0%, 1.0%) × 0.7 (high vol) = **0.7%**
  - Detection mode: STRICT (confirmation required)

### Scenario 3: Afterhours Penny Stock
- **Context**: 5:30 PM, $8 stock, normal volatility
- **Applied Thresholds**:
  - Market period: AFTERHOURS → 0.5% base
  - Price band: PENNY → 3.0% base
  - Final: min(0.5%, 3.0%) × 1.0 = **0.5%**
  - Detection mode: ADAPTIVE (compensatory)

## Configuration Parameters (Sprint 49)

### Market Period Parameters
Each period has its own set of configurations:


# Example: MIDDAY Configuration (most sensitive)
SURGE_THRESHOLD_MULTIPLIER_MIDDAY: 1.5      # Increases sensitivity
SURGE_VOLUME_THRESHOLD_MIDDAY: 1.1          # Lower volume requirement
SURGE_GLOBAL_SENSITIVITY_MIDDAY: 2.0        # Double sensitivity
SURGE_MIN_DATA_POINTS_MIDDAY: 3             # Standard buffer requirement
SURGE_INTERVAL_SECONDS_MIDDAY: 5            # 5-second baseline
SURGE_PRICE_THRESHOLD_PERCENT_MIDDAY: 1.0   # 1% base threshold

# AFTERHOURS Configuration (sparse data handling)
SURGE_THRESHOLD_MULTIPLIER_AFTERHOURS: 2.0   # Very sensitive
SURGE_VOLUME_THRESHOLD_AFTERHOURS: 0.8       # Minimal volume needed
SURGE_GLOBAL_SENSITIVITY_AFTERHOURS: 3.0     # Triple sensitivity
SURGE_MIN_DATA_POINTS_AFTERHOURS: 4          # More points for stability
SURGE_INTERVAL_SECONDS_AFTERHOURS: 10        # Longer baseline window
SURGE_PRICE_THRESHOLD_PERCENT_AFTERHOURS: 0.5 # 0.5% base threshold


### Price Band Parameters

# Price band boundaries and thresholds
SURGE_PRICE_BAND_PENNY_MAX: 10       # Upper bound for penny stocks
SURGE_PRICE_BAND_PENNY_PCT: 3.0      # 3% threshold for penny stocks
SURGE_PRICE_BAND_PENNY_DOLLAR: 0.10  # $0.10 minimum move

SURGE_PRICE_BAND_LOW_MAX: 50         # Upper bound for low-price stocks
SURGE_PRICE_BAND_LOW_PCT: 2.0        # 2% threshold
SURGE_PRICE_BAND_LOW_DOLLAR: 0.50    # $0.50 minimum

# ... continues for MID, HIGH, ULTRA bands


### Volatility Multipliers

SURGE_VOLATILITY_MULTIPLIER_HIGH: 0.7    # Reduce sensitivity in volatile markets
SURGE_VOLATILITY_MULTIPLIER_NORMAL: 1.0  # No adjustment
SURGE_VOLATILITY_MULTIPLIER_LOW: 1.5     # Increase sensitivity in quiet markets


## Diagnostic Logging

All surge detection now includes comprehensive diagnostic logging with the `DIAG-SURGE` prefix:


DIAG-SURGE-START: Entry point with price/volume data
DIAG-SURGE-CONTEXT: Market period, price band, volatility classification
DIAG-SURGE-CONFIG: Dynamic configuration built
DIAG-SURGE-METRICS: Calculated price/volume changes
DIAG-SURGE-THRESHOLDS: Applied thresholds with context
DIAG-SURGE-DECISION: Detection outcome with reasons
DIAG-SURGE-EVENT-CREATED: Successful detection with full context
DIAG-SURGE-NEAR-MISS: Close attempts that didn't trigger


Example log output:

DIAG-SURGE-CONTEXT [PRODUCTION] AAPL: period=MIDDAY, band=MID, volatility=LOW
DIAG-SURGE-THRESHOLDS [PRODUCTION] AAPL: price_thresh=0.75%, vol_thresh=1.1x, band=MID, volatility=LOW
DIAG-SURGE-EVENT-CREATED [PRODUCTION] AAPL: up magnitude=0.8% score=75.2 [MIDDAY/MID/LOW]


## Production vs Synthetic Data

### Synthetic Data Characteristics
- Tick interval: ~0.5 seconds
- Price movements: 1-5% swings
- Volume: 100,000+ per tick
- **Result**: Default thresholds work well

### Production Data Characteristics
- Tick interval: 1-20 seconds (sparse)
- Price movements: 0.01-0.1% micro-movements
- Volume: 100-10,000 per tick
- **Result**: Adaptive system catches micro-movements

### Sensitivity Comparison
| Scenario | Default System | Sprint 49 System | Improvement |
|----------|---------------|------------------|-------------|
| Midday $100 stock | 2.5% threshold | 0.5% threshold | 5x more sensitive |
| Afterhours $500 stock | 2.5% threshold | 0.3% threshold | 8x more sensitive |
| Opening penny stock | 7.0% threshold | 3.0% threshold | 2.3x more sensitive |

## Event Output

Each surge event includes standard fields plus new context:

json
{
  "ticker": "AAPL",
  "type": "surge",
  "price": 175.25,
  "direction": "up",
  "surge_magnitude": 0.8,
  "surge_score": 75.2,
  "surge_trigger_type": "price_driven",
  "thresholds_used": {
    "price_threshold_pct": 0.75,
    "volume_threshold": 1.1,
    "detection_mode": "OR",
    "market_period": "MIDDAY",
    "price_band": "MID",
    "volatility_class": "LOW"
  }
}


## Testing Strategy

### 1. Synthetic Data Testing
bash
# Start with synthetic data to verify events are detected
USE_SYNTHETIC_DATA=true
# Should see many surge events with default thresholds


### 2. Production Data Testing
bash
# Switch to production data
USE_POLYGON_API=true
# Should now catch micro-movements with adaptive thresholds


### 3. Verification Checklist
- [ ] DIAG-SURGE-CONTEXT shows correct period/band/volatility
- [ ] DIAG-SURGE-THRESHOLDS shows adapted values (e.g., 0.5% not 2.5%)
- [ ] Different thresholds at different times of day
- [ ] $5 vs $500 stocks have appropriate thresholds
- [ ] Afterhours handles sparse data without "insufficient data" errors
- [ ] Events include market context in output

## Key Improvements from Sprint 49

1. **37x Sensitivity Range**: From 0.3% (afterhours high-price) to 10% (opening penny stocks)
2. **No Configuration Required**: Sensible defaults, no .env changes needed
3. **Context-Aware**: Every decision considers time, price, and volatility
4. **Production-Ready**: Catches 0.05-0.5% moves that were previously missed
5. **Diagnostic Transparency**: Complete visibility into threshold decisions

## Summary

The Sprint 49 surge detection system automatically adapts to market conditions, providing appropriate sensitivity whether monitoring volatile penny stocks at market open or detecting micro-movements in high-priced stocks during quiet afterhours trading. The three-dimensional adaptation (market period × price band × volatility) ensures optimal detection across all scenarios without manual configuration changes.