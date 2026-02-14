### Moving Averages Calculation Instructions for TickStock.ai (Updated – February 14, 2026)

These instructions standardize SMA and EMA computations for periods 5, 10, 20, 50, 100, 200. All calculations use **closing prices** only. Daily timeframe data is the standard anchor for accuracy and comparability.

- **Data Sources**: TimescaleDB hypertables (`ohlcv_daily`, `ohlcv_1min`), Massive API WebSocket → 1-min bars (via memory/Redis aggregation)
- **Periods Covered**: 5, 10, 20, 50, 100, 200
- **General Rules**:
  - Return NaN or skip if fewer than N periods available
  - Use float64 precision
  - Prefer vectorized operations (NumPy / pandas)
  - Log warnings on data gaps; fallback to last known value if real-time data stalls
  - **Processing Order**: Moving averages computed FIRST (display_order 10-25) before other indicators that may depend on them

---

## Storage Schema

**Table**: `daily_indicators`

**Columns**:
- `symbol` — ticker (text)
- `indicator_type` — lowercase with underscore: 'sma_5', 'sma_10', 'ema_20', etc.
- `calculation_timestamp` — exact minute (intraday) or day-end timestamp (EOD)
- `timeframe` — '1min' or 'daily'
- `value_data` — JSONB with calculation results: `{"sma_20": 142.37}` or `{"ema_10": 138.45}`
- `metadata` — JSONB with context: `{"source": "hybrid_intraday", "daily_bars": 19, "intraday_bars": 1, "periods_used": 20}`
- `expiration_date` — timestamp when data becomes stale (next day at market close)

**Persistence Pattern** (Sprint 74 - TimescaleDB Hypertables):
```sql
-- DELETE existing entry
DELETE FROM daily_indicators
WHERE symbol = :symbol
  AND indicator_type = :indicator_type
  AND timeframe = :timeframe;

-- INSERT new entry
INSERT INTO daily_indicators
(symbol, indicator_type, value_data, calculation_timestamp,
 expiration_date, timeframe, metadata)
VALUES (:symbol, :indicator_type, :value_data, NOW(),
        :expiration_date, :timeframe, :metadata);
```

**Rationale**: TimescaleDB hypertables cannot use unique constraints without timestamp column, so we use DELETE + INSERT instead of ON CONFLICT UPSERT.

---

## 1. Simple Moving Average (SMA)

**Formula**: Arithmetic mean of the last N closing prices

**Implementation**: `src/analysis/indicators/sma.py`

### Intraday Processing (Real-Time, Per-Minute Events)

**Trigger**: New OHLCV bar completion via Redis pub-sub (`tickstock:market:ohlcv:complete`)

**Hybrid Data Approach** (N-1 daily + 1 intraday):
1. Fetch the last **(N-1)** daily closing prices from `ohlcv_daily` (ordered by date DESC, limit N-1)
2. Append the **most recent 1-min bar close** (from memory/Redis aggregate)
3. If intraday close unavailable → use previous day's close as fallback + log warning + flag for review
4. Compute SMA = `mean(hybrid_series)` where `hybrid_series = [daily_closes..., intraday_close]`
5. Store in `daily_indicators`:
   - `timeframe='1min'`
   - `calculation_timestamp` = minute bar timestamp
   - `indicator_type='sma_{N}'` (lowercase)
   - `value_data={"sma_{N}": computed_value}`
   - `metadata={"source": "hybrid_intraday", "daily_bars": N-1, "intraday_bars": 1}`

**Pandas Implementation**:
```python
# Hybrid series: N-1 daily + 1 intraday
daily_closes = fetch_daily_closes(symbol, limit=N-1)  # pandas Series
intraday_close = get_latest_1min_close(symbol)        # float

hybrid_series = pd.concat([daily_closes, pd.Series([intraday_close])])
sma_value = hybrid_series.mean()  # Simple arithmetic mean
```

**Critical**: Use `min_periods=N` in pandas rolling window to prevent partial calculations with insufficient data.

### End-of-Day (EOD) Processing (Batch Import)

**Trigger**: Historical data import completion OR nightly batch job

**Pure Daily Data Approach**:
1. Fetch last **N daily closing prices** from `ohlcv_daily` (ordered DESC, limit N)
2. Compute SMA = `mean(daily_closes)`
3. Store in `daily_indicators`:
   - `timeframe='daily'`
   - `calculation_timestamp` = EOD timestamp (typically market close)
   - `indicator_type='sma_{N}'` (lowercase)
   - `value_data={"sma_{N}": computed_value}`
   - `metadata={"source": "batch_eod", "daily_bars": N}`

**Pandas Implementation**:
```python
# Pure daily data
daily_closes = fetch_daily_closes(symbol, limit=N)  # pandas Series
sma_series = daily_closes.rolling(window=N, min_periods=N).mean()
sma_value = sma_series.iloc[-1]  # Latest SMA value
```

### Data Validation Rules

- **Insufficient Data**: If `len(data) < N`, return `None` and skip storage
- **NaN Handling**: If `pd.isna(sma_value)`, return `None`
- **Precision**: Store as float64, round to 2 decimal places in UI only
- **Gaps**: If more than 5 consecutive trading days missing, log warning and skip calculation

---

## 2. Exponential Moving Average (EMA)

**Formula**: Recursive exponential smoothing with α = 2 / (N + 1)

**Recursive Form**: `EMA_t = Close_t × α + EMA_{t-1} × (1 - α)`

**Initial Seed**: When no prior EMA exists, seed with SMA of first N closes

**Implementation**: `src/analysis/indicators/ema.py`

**State Management**: **STATELESS** (Option B) - Recalculate full series each time using pandas `.ewm()` method

### Intraday Processing (Real-Time, Per-Minute Events)

**Trigger**: New OHLCV bar completion via Redis pub-sub

**Hybrid Data Approach** (N-1 daily + 1 intraday):
1. Fetch the last **(N-1)** daily closing prices from `ohlcv_daily` (ordered DESC, limit N-1)
2. Append the **most recent 1-min bar close**
3. If intraday close unavailable → fallback to previous day's close + log + flag
4. Compute EMA using **stateless pandas method**:
   - Calculate full EMA series over hybrid data: `hybrid_series.ewm(span=N, adjust=False).mean()`
   - Extract latest value: `ema_value = ema_series.iloc[-1]`
5. Store in `daily_indicators`:
   - `timeframe='1min'`
   - `calculation_timestamp` = minute bar timestamp
   - `indicator_type='ema_{N}'` (lowercase)
   - `value_data={"ema_{N}": computed_value}`
   - `metadata={"source": "hybrid_intraday", "daily_bars": N-1, "intraday_bars": 1, "alpha": 2/(N+1)}`

**Pandas Implementation** (Stateless):
```python
# Hybrid series: N-1 daily + 1 intraday
daily_closes = fetch_daily_closes(symbol, limit=N-1)  # pandas Series
intraday_close = get_latest_1min_close(symbol)        # float

hybrid_series = pd.concat([daily_closes, pd.Series([intraday_close])])

# Calculate EMA using pandas (stateless - recalculates full series)
alpha = 2 / (N + 1)
ema_series = hybrid_series.ewm(span=N, adjust=False, min_periods=N).mean()
ema_value = ema_series.iloc[-1]
```

**Critical**: Use `adjust=False` to match traditional EMA formula. Use `min_periods=N` to ensure sufficient data.

### End-of-Day (EOD) Processing (Batch Import)

**Trigger**: Historical data import completion OR nightly batch job

**Pure Daily Data Approach** (Stateless):
1. Fetch last **N daily closing prices** from `ohlcv_daily` (ordered DESC, limit N)
2. Compute EMA using **stateless pandas method**:
   - Calculate full EMA series: `daily_closes.ewm(span=N, adjust=False).mean()`
   - Extract latest value: `ema_value = ema_series.iloc[-1]`
3. Store in `daily_indicators`:
   - `timeframe='daily'`
   - `calculation_timestamp` = EOD timestamp
   - `indicator_type='ema_{N}'` (lowercase)
   - `value_data={"ema_{N}": computed_value}`
   - `metadata={"source": "batch_eod", "daily_bars": N, "alpha": 2/(N+1)}`

**Pandas Implementation** (Stateless):
```python
# Pure daily data
daily_closes = fetch_daily_closes(symbol, limit=N)  # pandas Series

# Calculate EMA using pandas (stateless)
alpha = 2 / (N + 1)
ema_series = daily_closes.ewm(span=N, adjust=False, min_periods=N).mean()
ema_value = ema_series.iloc[-1]
```

**Rationale for Stateless Approach**:
- ✅ **Correctness**: Recalculating from scratch prevents drift errors
- ✅ **Simplicity**: No need to retrieve prior EMA from database
- ✅ **Consistency**: Same logic for batch and real-time
- ⚠️ **Performance**: Slightly slower, but acceptable for N ≤ 200 bars

**Future Optimization** (Sprint 77+):
- For real-time updates, can implement stateful EMA: retrieve last `ema_daily`, apply recursive formula to intraday close
- Requires additional validation to prevent drift (periodic full recalculation)

### Data Validation Rules

- **Insufficient Data**: If `len(data) < N`, return `None` and skip storage
- **NaN Handling**: If `pd.isna(ema_value)`, return `None`
- **Alpha Validation**: Always verify `alpha = 2 / (N + 1)` is applied correctly
- **Precision**: Store as float64, round to 2 decimal places in UI only
- **Gaps**: If more than 5 consecutive trading days missing, log warning and skip calculation

---

## Processing Order & Dependencies

**Display Order Values** (from `indicator_definitions` table):
- `sma_5`: 10
- `sma_10`: 11
- `sma_20`: 12
- `sma_50`: 13
- `sma_100`: 14
- `sma_200`: 15
- `ema_5`: 20
- `ema_10`: 21
- `ema_20`: 22
- `ema_50`: 23
- `ema_100`: 24
- `ema_200`: 25

**Processing Logic**:
1. Load indicators from `indicator_definitions` ordered by `display_order ASC`
2. Execute calculations in sequence (SMA first, then EMA)
3. Other indicators (RSI, MACD, etc.) start at display_order 30+

**Dependencies**:
- SMA/EMA have NO dependencies (only require OHLCV data)
- Other indicators MAY reference SMA/EMA values (e.g., MACD uses EMA internally)

---

## Error Handling & Logging

**Insufficient Data**:
```python
if len(data) < period:
    logger.warning(f"SMA_{period}: Insufficient data for {symbol} - need {period}, have {len(data)}")
    return None  # Skip storage
```

**Data Gaps**:
```python
if has_gap(data, threshold_days=5):
    logger.warning(f"SMA_{period}: Data gap detected for {symbol} - {gap_days} days missing")
    # Continue calculation but flag in metadata
    metadata['data_gap_warning'] = True
```

**Calculation Errors**:
```python
try:
    sma_value = hybrid_series.mean()
except Exception as e:
    logger.error(f"SMA_{period}: Calculation failed for {symbol}: {e}", exc_info=True)
    return None  # Skip storage
```

**Fallback for Stalled Real-Time Data**:
```python
if intraday_close is None:
    logger.warning(f"SMA_{period}: Intraday close unavailable for {symbol}, using last daily close")
    intraday_close = daily_closes.iloc[-1]  # Use most recent daily close
    metadata['fallback_used'] = True
```

---

## Performance Targets

| Operation | Target | Notes |
|-----------|--------|-------|
| SMA Calculation (single period) | <10ms | Vectorized pandas operation |
| EMA Calculation (single period) | <10ms | Vectorized pandas operation |
| Hybrid data fetch (N-1 daily + 1 intraday) | <50ms | Database query + Redis lookup |
| Database persistence (DELETE + INSERT) | <20ms | Two simple SQL operations |
| **Total: Intraday SMA/EMA update** | **<100ms** | End-to-end latency target |

---

## Testing & Validation

**Unit Tests**:
- Verify SMA calculation accuracy (known test data)
- Verify EMA calculation accuracy with α = 2 / (N + 1)
- Test insufficient data handling (len < N)
- Test NaN handling
- Test hybrid series construction (N-1 daily + 1 intraday)

**Integration Tests**:
- Verify DELETE + INSERT pattern prevents duplicates
- Verify timeframe separation (1min vs daily)
- Verify metadata tracking (source, bar counts)
- Verify expiration_date calculation

**Regression Tests**:
- Compare SMA values against known financial data providers (Yahoo Finance, TradingView)
- Compare EMA values with tolerance ±0.01 (floating point precision)
- Verify consistency: `EMA_daily[T]` should match `EMA_intraday[T+1 day]` within tolerance

---

## Migration from Current Implementation

**Current Issues** (Sprint 76 Discovery):
1. ❌ `market_data_service.py` line 288 fetches `timeframe='1min'` but runs 'daily' analysis
2. ❌ Result: SMA calculated over 3.3 hours of 1-min data (200 bars) instead of 200 daily bars
3. ❌ All SMAs converge to ~46.6x (insufficient data)

**Fix** (Task #3):
- Change line 288: `timeframe='daily'` for batch/EOD analysis
- Implement hybrid approach for real-time intraday analysis (Task #4)

**Database State**:
- After fix, DELETE stale '1min' entries with incorrect SMA values
- Re-run analysis with correct data sources

---

## Document Status

**Version**: 2.0 (Perfected for Sprint 76)
**Last Updated**: February 14, 2026
**Status**: ✅ **GOLD STANDARD** - Aligned with existing schema and Sprint 74 patterns
**Next Sprint**: Use this document as template for other indicators (RSI, MACD, ATR, etc.)
