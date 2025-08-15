# HighLow Detection System Overview

## Purpose
Track and detect new session highs and lows for stocks, providing real-time alerts when prices break through established ranges. Enriches events with trend and surge context flags, significance scoring, and reversal pattern detection.

## Core Detection Mechanism

### Session Tracking
- **Session High**: Highest price seen in current market session
- **Session Low**: Lowest price seen in current market session
- **Session Types**: REGULAR, PRE, POST market sessions
- **Reset Logic**: Sessions reset on market status changes

### State Management
- **Per-Ticker Storage**: Dictionary tracking each ticker's state
- **Initial Values**: Market open price or first tick price
- **Continuous Updates**: Every tick evaluated against session bounds

## Detection Logic

### High Detection
```python
if price > session_high:
    # Check dynamic thresholds based on price
    if should_check_thresholds():
        # Check cooldown
        if cooldown_passed():
            # Calculate significance
            # Detect reversal patterns
            # Create HIGH event with enrichment
```

### Low Detection
```python
if price < session_low:
    # Check dynamic thresholds based on price
    if should_check_thresholds():
        # Check cooldown
        if cooldown_passed():
            # Calculate significance
            # Detect reversal patterns
            # Create LOW event with enrichment
```

### Context Enrichment
- **Trend Flag**: Obtained from lightweight trend check
- **Surge Flag**: Obtained from lightweight surge check
- **Purpose**: Provides market context without creating separate events

## Enhanced Features

### Price-Based Dynamic Thresholds
| Price Range | Min % Change | Min $ Change |
|-------------|--------------|--------------|
| < $1.00     | 0.2%         | $0.005       |
| < $5.00     | 0.15%        | $0.01        |
| < $25.00    | 0.1%         | $0.02        |
| < $100.00   | 0.08%        | $0.05        |
| ≥ $100.00   | 0.05%        | $0.10        |

### Significance Scoring
- **Purpose**: Quantify how significant each high/low event is
- **Score Range**: 0-100
- **Components**:
  - Price Change Component: 0-50 points (5% change = 50 points)
  - Volume Component: 0-50 points (2x average volume = 50 points)
- **Weighting**: Configurable volume weight (default 0.5)

### Reversal Pattern Detection
- **V-bottom**: Low followed by high within reversal window
- **V-top**: High followed by low within reversal window
- **M-top**: High-low-high-low pattern
- **W-bottom**: Low-high-low-high pattern
- **Rapid Reversal**: Reversal within 60 seconds flagged as rapid

### Market-Aware Detection
- **Extended Hours**: 2x multiplier on thresholds
- **Market Opening**: 1.5x multiplier on thresholds
- **Regular Hours**: Base thresholds

## Session Management

### Market Status Changes
- **PRE → REGULAR**: Reset highs/lows to market open price
- **REGULAR → POST**: Reset highs/lows to current price
- **Any Change**: Previous values saved as previous_high/low

### Initial Seeding
- **Regular Hours**: Uses market_open_price if available
- **Extended Hours**: Uses first tick price
- **Fallback**: Current price if no historical data

## Event Counting

### Tracking System
- **High Count**: Number of new highs in session
- **Low Count**: Number of new lows in session
- **Total Events**: Combined high + low count
- **Per Session**: Counts reset on session change

## Integration with Other Detectors

### Trend Integration
```python
# Lightweight check - no event creation
trend_result = check_trend_conditions(
    stock_data=internal_state,
    price=price,
    vwap=vwap,
    volume=volume,
    config=self.config
)
# Extract flag: 'up', 'down', or None
# Direction symbols (↑, ↓) are converted to words for flags
```

**Important**: The trend check now includes:
- Warm-up period validation (180 seconds default)
- Minimum history requirements (30 points default)
- Timestamp format matching with existing price history

### Surge Integration
```python
# Lightweight check - no event creation
surge_result = check_surge_conditions(
    stock_data=internal_state,
    price=price,
    volume=volume,
    tick_volume=tick_volume,
    config=self.config
)
# Extract flag: 'up', 'down', or None
# Direction symbols (↑, ↓) are converted to words for flags
```

## Configuration Parameters
```yaml
# Detection Parameters
HIGHLOW_MIN_PRICE_CHANGE: 0.01      # Base minimum dollar change
HIGHLOW_MIN_PERCENT_CHANGE: 0.1     # Base minimum percent change
HIGHLOW_COOLDOWN_SECONDS: 1         # Cooldown between events

# Market Awareness
HIGHLOW_MARKET_AWARE: true           # Enable market-aware thresholds
HIGHLOW_EXTENDED_HOURS_MULTIPLIER: 2.0
HIGHLOW_OPENING_MULTIPLIER: 1.5

# Significance Scoring
HIGHLOW_SIGNIFICANCE_SCORING: true   # Enable significance calculation
HIGHLOW_SIGNIFICANCE_VOLUME_WEIGHT: 0.5

# Reversal Detection
HIGHLOW_TRACK_REVERSALS: true        # Enable reversal patterns
HIGHLOW_REVERSAL_WINDOW: 300         # 5-minute window for reversals
```

## Event Output
Each high/low event includes:

**Basic Info**: Ticker, price, time, type (high/low)
**Session Data**: Current high/low, previous high/low
**Counts**: Session totals, individual counts
**Context Flags**: Trend direction, surge direction
**Calculations**: Percent change, VWAP divergence
**Metadata**: Is initial, period type, timestamps

**Enhanced Fields**:
- `significance_score`: 0-100 importance score
- `reversal_info`: Reversal pattern details if detected
- `thresholds_used`: Applied detection thresholds
- `highlow_calc_transparency`: Full calculation breakdown
- `trend_flag`: 'up', 'down', or null (shows as T↑ or T↓ in UI)
- `surge_flag`: 'up', 'down', or null (shows as S↑ or S↓ in UI)

## Quality Assurance
The detector ensures quality through:

- **Dynamic Thresholds**: Price-appropriate sensitivity
- **Cooldown Management**: Prevents event spam
- **Market Context**: Adjusts for market conditions
- **Pattern Recognition**: Identifies reversal patterns
- **Significance Scoring**: Prioritizes important events
- **Timing Validation**: Respects trend/surge warm-up periods

This comprehensive approach ensures high-quality event detection that adapts to different price levels, market conditions, and trading patterns while providing rich context about concurrent market dynamics.