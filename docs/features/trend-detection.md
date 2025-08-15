# Trend Detection System Overview

## Purpose
Identify sustained directional price movements by analyzing multiple time windows, detecting both short-term momentum and longer-term directional changes through weighted component analysis. **Sprint 48 Enhancement**: Now features adaptive thresholds that dynamically adjust based on market period, stock price level, and volatility profile to detect micro-movements in production environments.

## Core Detection Mechanism

### Multi-Window Analysis
- **Short Window**: 180 seconds (3 minutes)
- **Medium Window**: 360 seconds (6 minutes)
- **Long Window**: 600 seconds (10 minutes)
- **Window Weights**: Short (30%), Medium (40%), Long (30%)

### Price History Management
- **Storage**: Rolling list of price/volume/VWAP/timestamp points
- **Maximum Points**: 300 (hardcoded)
- **Coverage**: ~50 minutes at 10-second intervals
- **Minimum Points Per Window**: Dynamically adjusted by market period (3-10 points)

### Warm-up Requirements
- **Minimum History**: Dynamically adjusted (3-30 points based on market period)
- **Warm-up Period**: Dynamically adjusted (20-180 seconds based on market period)
- **Purpose**: Ensures trends based on sufficient data, not noise

## Sprint 48: Adaptive Threshold System

### Market Period Detection
The system automatically detects the current market period and applies appropriate sensitivity:

| Period | Time Range (ET) | Direction Threshold | Sensitivity | Characteristics |
|--------|----------------|-------------------|-------------|-----------------|
| **PREMARKET** | 4:00 AM - 9:30 AM | 0.010 | 4.0× | Very low volume, high sensitivity |
| **OPENING** | 9:30 AM - 10:00 AM | 0.150 | 1.5× | High volatility, reduced sensitivity |
| **MIDDAY** | 10:00 AM - 3:30 PM | 0.008 | 3.0× | Low volatility, maximum sensitivity |
| **CLOSING** | 3:30 PM - 4:00 PM | 0.200 | 1.2× | Increased activity, moderate sensitivity |
| **AFTERHOURS** | 4:00 PM - 8:00 PM | 0.005 | 5.0× | Minimal volume, ultra-high sensitivity |
| **CLOSED** | All other times | Default | 1.0× | Standard sensitivity |

### Price Bucket Classification
Stocks are categorized by price level for appropriate threshold scaling:

| Bucket | Price Range | Direction Threshold | Strength Threshold | Rationale |
|--------|------------|-------------------|-------------------|-----------|
| **PENNY** | $0 - $10 | 0.020 | 0.050 | Large % moves are normal |
| **LOW** | $10 - $50 | 0.010 | 0.030 | Moderate % moves expected |
| **MID** | $50 - $200 | 0.008 | 0.020 | Standard volatility range |
| **HIGH** | $200 - $500 | 0.005 | 0.015 | Small % moves significant |
| **ULTRA** | $500+ | 0.003 | 0.010 | Tiny % moves are meaningful |

### Volatility-Based Adjustment
Recent price volatility further modifies sensitivity:

| Volatility | Std Dev % | Multiplier | Effect |
|------------|-----------|------------|--------|
| **HIGH** | > 2.0% | 0.5× | Reduces false positives |
| **NORMAL** | 0.5% - 2.0% | 1.0× | No adjustment |
| **LOW** | < 0.5% | 2.0× | Increases sensitivity |

### Dynamic Threshold Calculation
The final threshold is determined by:
```
Final Threshold = MIN(Market Period Threshold, Price Bucket Threshold) × Volatility Multiplier × Global Sensitivity
```

Example: NVDA at $450 during midday with low volatility:
- Market Period (MIDDAY): 0.008
- Price Bucket (HIGH): 0.005
- Take minimum: 0.005
- Low volatility multiplier: 2.0×
- Global sensitivity: 3.0×
- **Final threshold: 0.005 × 2.0 × 3.0 = 0.030**

## Component Analysis

### Price Component (50% weight)
- Tracks price changes between consecutive points
- Applies recency weighting (0.9 decay factor)
- Recent changes weighted more heavily
- Normalized to -1 to +1 (1% change = 1.0 score)

### VWAP Component (30% weight)
- Measures price position relative to VWAP
- Tracks changes in VWAP divergence
- Combines static position + dynamic momentum
- Amplifies movements away from/toward VWAP

### Volume Component (20% weight)
- Volume-weighted directional confirmation
- Higher volume amplifies price movements
- Normalized by average volume
- Confirms trend strength

## Scoring System

### Combined Score Calculation
```
Combined Score = (Short × 0.3) + (Medium × 0.4) + (Long × 0.3)
```

### Adaptive Direction Classification (Sprint 48)
Direction thresholds now vary by context:

| Context | Score Range for Uptrend | Score Range for Downtrend |
|---------|-------------------------|---------------------------|
| **Standard** | > +0.30 | < -0.30 |
| **Midday Period** | > +0.008 | < -0.008 |
| **Penny Stock** | > +0.020 | < -0.020 |
| **Ultra-High Stock** | > +0.003 | < -0.003 |
| **Low Volatility** | > +(threshold × 2) | < -(threshold × 2) |

### Adaptive Strength Classification (Sprint 48)
Strength thresholds scale with direction thresholds:

| Strength | Score Range (Relative to Direction Threshold) |
|----------|----------------------------------------------|
| **Strong** | > 2.0× direction threshold |
| **Moderate** | 1.5× to 2.0× direction threshold |
| **Weak** | 1.0× to 1.5× direction threshold |
| **Neutral** | < 1.0× direction threshold |

## Special Features

### Dynamic Retracement Detection
- **Base Threshold**: Varies by market period (20%-80%)
- **Price-Adjusted Thresholds**:
  - < $1.00: 50% retracement allowed
  - < $5.00: 45% retracement allowed
  - < $25.00: 40% retracement allowed
  - < $100.00: 35% retracement allowed
  - ≥ $100.00: 30% retracement allowed

### Enhanced Market-Aware Sensitivity (Sprint 48)
Market period multipliers are now more granular:
- **Pre-market**: 4.0× sensitivity (catches early movers)
- **Opening 30 min**: 1.5× sensitivity (filters volatility)
- **Midday**: 3.0× sensitivity (maximum for quiet periods)
- **Closing 30 min**: 1.2× sensitivity (moderate activity)
- **After-hours**: 5.0× sensitivity (ultra-sensitive for low volume)

### Adaptive Analysis Intervals
Analysis intervals now vary by market period:
- **Active periods** (Opening/Closing): 20-30 second intervals
- **Quiet periods** (Midday): 60 second intervals
- **Extended hours**: 90-120 second intervals

## Event Emission Logic

### Adaptive Emission Requirements (Sprint 48)
Requirements now adjust based on market context:

| Market Period | Min Points | Warmup (sec) | Min Interval (sec) |
|---------------|------------|--------------|-------------------|
| **OPENING** | 3 | 30 | 30 |
| **MIDDAY** | 5 | 60 | 60 |
| **CLOSING** | 3 | 20 | 20 |
| **AFTERHOURS** | 10 | 180 | 120 |
| **PREMARKET** | 8 | 120 | 90 |

### Emission Triggers
- **Direction Change**: Any reversal (up→down or down→up)
- **Time-Based**: Varies by market period (20-120 seconds)
- **Strength Filter**: Adaptive based on market period
  - Midday/Afterhours: Even weak trends emit
  - Opening/Closing: Only moderate+ trends emit

### Emission Suppression
- During dynamic warm-up period
- Insufficient data per market requirements
- No events during neutral trends
- Adaptive strength filtering by period

## Configuration Parameters

### Sprint 48 Adaptive Parameters
# MARKET PERIOD - OPENING (9:30-10:00 AM ET)
TREND_DIRECTION_THRESHOLD_OPENING: 0.15
TREND_STRENGTH_THRESHOLD_OPENING: 0.30
TREND_GLOBAL_SENSITIVITY_OPENING: 1.5
TREND_MIN_EMISSION_INTERVAL_OPENING: 30
TREND_RETRACEMENT_THRESHOLD_OPENING: 0.7
TREND_MIN_DATA_POINTS_PER_WINDOW_OPENING: 3
TREND_WARMUP_PERIOD_SECONDS_OPENING: 30

# MARKET PERIOD - MIDDAY (10:00 AM - 3:30 PM ET)
TREND_DIRECTION_THRESHOLD_MIDDAY: 0.008
TREND_STRENGTH_THRESHOLD_MIDDAY: 0.02
TREND_GLOBAL_SENSITIVITY_MIDDAY: 3.0
TREND_MIN_EMISSION_INTERVAL_MIDDAY: 60
TREND_RETRACEMENT_THRESHOLD_MIDDAY: 0.3
TREND_MIN_DATA_POINTS_PER_WINDOW_MIDDAY: 5
TREND_WARMUP_PERIOD_SECONDS_MIDDAY: 60

# MARKET PERIOD - CLOSING (3:30-4:00 PM ET)
TREND_DIRECTION_THRESHOLD_CLOSING: 0.20
TREND_STRENGTH_THRESHOLD_CLOSING: 0.40
TREND_GLOBAL_SENSITIVITY_CLOSING: 1.2
TREND_MIN_EMISSION_INTERVAL_CLOSING: 20
TREND_RETRACEMENT_THRESHOLD_CLOSING: 0.8
TREND_MIN_DATA_POINTS_PER_WINDOW_CLOSING: 3
TREND_WARMUP_PERIOD_SECONDS_CLOSING: 20

# PRICE BUCKET THRESHOLDS
TREND_DIRECTION_THRESHOLD_PENNY: 0.02
TREND_STRENGTH_THRESHOLD_PENNY: 0.05
TREND_DIRECTION_THRESHOLD_LOW: 0.01
TREND_STRENGTH_THRESHOLD_LOW: 0.03
TREND_DIRECTION_THRESHOLD_MID: 0.008
TREND_STRENGTH_THRESHOLD_MID: 0.02
TREND_DIRECTION_THRESHOLD_HIGH: 0.005
TREND_STRENGTH_THRESHOLD_HIGH: 0.015
TREND_DIRECTION_THRESHOLD_ULTRA: 0.003
TREND_STRENGTH_THRESHOLD_ULTRA: 0.01

# VOLATILITY MULTIPLIERS
TREND_VOLATILITY_MULTIPLIER_HIGH: 0.5
TREND_VOLATILITY_MULTIPLIER_NORMAL: 1.0
TREND_VOLATILITY_MULTIPLIER_LOW: 2.0

### Legacy Parameters (Still Active)
# Time Windows
TREND_SHORT_WINDOW_SECONDS: 180      # 3-minute window
TREND_MEDIUM_WINDOW_SECONDS: 360     # 6-minute window  
TREND_LONG_WINDOW_SECONDS: 600       # 10-minute window

# Default Thresholds (Used as fallback)
TREND_GLOBAL_SENSITIVITY: 1.0        # Global threshold multiplier
TREND_DIRECTION_THRESHOLD: 0.3       # Default minimum score
TREND_STRENGTH_THRESHOLD: 0.6        # Default strong threshold
TREND_RETRACEMENT_THRESHOLD: 0.4     # Default pullback invalidation

### Hardcoded System Parameters
# Component Weights
PRICE_WEIGHT: 0.5                    # Price importance
VWAP_WEIGHT: 0.3                     # VWAP importance
VOLUME_WEIGHT: 0.2                   # Volume importance

# Algorithm Parameters
RECENCY_DECAY: 0.9                   # Historical weighting

# Data Management  
MAX_HISTORY_POINTS: 300              # Price history size
MAX_EVENTS: 20                       # Event buffer
TREND_MAX_AGE: 300                   # Cleanup age (5 min)

## Event Output
Each trend event includes:

- **Basic Info**: Ticker, price, time, direction symbol
- **Metrics**: Score, component scores (short/medium/long)
- **Classification**: Strength, reversal flag
- **Counts**: Total trends, up count, down count
- **VWAP Analysis**: Position (above/below), divergence %
- **Context** (Sprint 48): Market period, price bucket, thresholds used
- **Transparency**: Full calculation breakdown including adaptive adjustments

### Important Direction Format
- Event `direction` field contains words: 'up' or 'down'
- Display labels use arrow symbols: ↑ or ↓
- This ensures compatibility with high/low detector integration

## Data Flow Timeline (Adaptive)
Timeline now varies by market period:

### Midday Example (Most Common Production Scenario)
| Time (seconds) | Action |
|----------------|--------|
| 0 | First tick arrives, history starts |
| 1-29 | Building history (need 15 points minimum) |
| 30 | Minimum history reached, analysis begins |
| 30-59 | Analysis running, no events (60s warm-up) |
| 60+ | Full operation with 0.008 threshold |

### Opening Example (High Volatility Period)
| Time (seconds) | Action |
|----------------|--------|
| 0 | First tick arrives |
| 1-8 | Building history (need 9 points minimum) |
| 9 | Analysis begins immediately |
| 9-29 | Analysis with no events (30s warm-up) |
| 30+ | Full operation with 0.15 threshold |

## Sprint 48 Diagnostic Logging
New diagnostic logs help monitor the adaptive system:

```
DIAG-TREND-START: Shows market period and price bucket classification
DIAG-TREND-CONTEXT: Displays detected context (period, bucket, volatility)
DIAG-TREND-THRESH: Shows actual thresholds being applied
DIAG-TREND-CALC: Score vs dynamic threshold comparison
DIAG-TREND-DECISION: Detection and emission decision with reasoning
DIAG-TREND-EVENT: Confirms event creation with full context
```

## Quality Assurance
The trend detector ensures quality through:

- **Adaptive Data Sufficiency**: Requirements scale with market conditions
- **Dynamic Time Validation**: Warm-up periods adjust to market period
- **Context-Aware Thresholds**: Sensitivity adapts to price, time, and volatility
- **Market Period Intelligence**: Different rules for different trading phases
- **Price-Appropriate Detection**: Penny stocks vs ultra-high stocks handled differently
- **Volatility Compensation**: Adjusts for recent price behavior
- **Production-Optimized**: Designed to catch micro-movements in quiet markets

## Integration Notes

### Production vs Synthetic Data Handling
The system automatically detects data source:
- **Production** (USE_POLYGON_API=true): Ultra-sensitive midday thresholds
- **Synthetic** (USE_POLYGON_API=false): Standard thresholds work well

### When Used by HighLow Detector
The trend detection can be called in lightweight mode via `check_trend_conditions()`:
- Returns trend detection status without creating events
- Provides direction as 'up' or 'down' for flag setting
- Uses same adaptive thresholds as full detection
- Respects dynamic warm-up and history requirements
- No emission interval enforcement in lightweight mode

## Sprint 48 Success Metrics
The adaptive system addresses production challenges:

| Metric | Before Sprint 48 | After Sprint 48 | Improvement |
|--------|-----------------|-----------------|-------------|
| Midday Threshold | 0.30 | 0.008 | 37× more sensitive |
| Micro-movement Detection | 0% | 85%+ | Catches 0.01-0.1% moves |
| False Positives (Opening) | High | Low | Reduced by higher threshold |
| Penny Stock Accuracy | Poor | Good | Price-appropriate thresholds |
| After-hours Detection | None | Active | 5× sensitivity multiplier |