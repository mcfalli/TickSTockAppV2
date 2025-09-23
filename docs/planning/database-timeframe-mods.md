# Database Timeframe Modifications

**Document Type**: Database Schema Change Plan
**Created**: 2025-09-21
**Status**: Ready for Review

## Summary of Changes

- **Add `applicable_timeframes` column** to `pattern_definitions` and `indicator_definitions` tables
- **Add `timeframe` column** to existing pattern and indicator storage tables
- **Create new pattern tables**: `hourly_patterns`, `weekly_patterns`, `monthly_patterns`
- **Drop deprecated table**: `combo_indicators`
- **Standardize timeframe values** across all tables

---

## Modification Scripts

### 1. Add Timeframe Columns to Definition Tables

```sql
-- Add applicable_timeframes to pattern_definitions
ALTER TABLE pattern_definitions
ADD COLUMN applicable_timeframes text[] DEFAULT ARRAY['daily'];

COMMENT ON COLUMN pattern_definitions.applicable_timeframes IS 'Timeframes this pattern can be detected on';

-- Add applicable_timeframes to indicator_definitions
ALTER TABLE indicator_definitions
ADD COLUMN applicable_timeframes text[] DEFAULT ARRAY['daily'];

COMMENT ON COLUMN indicator_definitions.applicable_timeframes IS 'Timeframes this indicator can be calculated on';

-- Update common patterns with their applicable timeframes
UPDATE pattern_definitions SET applicable_timeframes = ARRAY['daily', 'weekly', 'monthly']
WHERE name IN ('Head and Shoulders', 'Double Top', 'Double Bottom');

UPDATE pattern_definitions SET applicable_timeframes = ARRAY['1min', '5min', '15min', '30min', 'hourly']
WHERE name IN ('Volume Surge', 'Momentum Shift');

UPDATE pattern_definitions SET applicable_timeframes = ARRAY['daily', 'weekly']
WHERE name IN ('Bull Flag', 'Bear Flag', 'Breakout');

-- Update common indicators with their applicable timeframes
UPDATE indicator_definitions SET applicable_timeframes = ARRAY['1min', '5min', '15min', '30min', 'hourly', 'daily', 'weekly', 'monthly']
WHERE name IN ('RSI', 'MACD', 'SMA', 'EMA');

UPDATE indicator_definitions SET applicable_timeframes = ARRAY['daily', 'weekly', 'monthly']
WHERE name IN ('Bollinger Bands', 'ATR');

UPDATE indicator_definitions SET applicable_timeframes = ARRAY['1min', '5min', '15min', '30min', 'hourly']
WHERE name IN ('VWAP', 'Volume Profile');
```

### 2. Add Timeframe Column to Existing Storage Tables

```sql
-- Add timeframe to pattern storage tables
ALTER TABLE daily_patterns
ADD COLUMN timeframe text DEFAULT 'daily';

ALTER TABLE intraday_patterns
ADD COLUMN timeframe text DEFAULT '5min';

ALTER TABLE daily_intraday_patterns
ADD COLUMN timeframe text DEFAULT 'combo';

-- Add timeframe to indicator storage tables
ALTER TABLE daily_indicators
ADD COLUMN timeframe text DEFAULT 'daily';

ALTER TABLE intraday_indicators
ADD COLUMN timeframe text DEFAULT '5min';

-- Add comments
COMMENT ON COLUMN daily_patterns.timeframe IS 'Specific timeframe of pattern detection';
COMMENT ON COLUMN intraday_patterns.timeframe IS 'Specific timeframe of pattern detection';
COMMENT ON COLUMN daily_intraday_patterns.timeframe IS 'Specific timeframe of pattern detection';
COMMENT ON COLUMN daily_indicators.timeframe IS 'Specific timeframe of indicator calculation';
COMMENT ON COLUMN intraday_indicators.timeframe IS 'Specific timeframe of indicator calculation';
```

### 3. Create New Pattern Tables

```sql
-- ============================================================================
-- HOURLY PATTERNS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS hourly_patterns (
    id SERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    pattern_type TEXT NOT NULL,
    confidence NUMERIC NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    pattern_data JSONB NOT NULL,
    detection_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expiration_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    levels NUMERIC[] DEFAULT NULL,
    metadata JSONB DEFAULT NULL,
    timeframe TEXT DEFAULT 'hourly'
);

-- Create indexes for hourly_patterns
CREATE INDEX idx_hourly_patterns_symbol_type_exp
ON hourly_patterns(symbol, pattern_type, expiration_timestamp DESC);

CREATE INDEX idx_hourly_patterns_detection_time
ON hourly_patterns(detection_timestamp DESC);

CREATE INDEX idx_hourly_patterns_confidence
ON hourly_patterns(confidence DESC);

CREATE INDEX idx_hourly_patterns_data_gin
ON hourly_patterns USING GIN (pattern_data);

-- Add table comment
COMMENT ON TABLE hourly_patterns IS 'Hourly timeframe pattern detections';

-- ============================================================================
-- WEEKLY PATTERNS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS weekly_patterns (
    id SERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    pattern_type TEXT NOT NULL,
    confidence NUMERIC NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    pattern_data JSONB NOT NULL,
    detection_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expiration_date TIMESTAMP WITH TIME ZONE NOT NULL,
    levels NUMERIC[] DEFAULT NULL,
    metadata JSONB DEFAULT NULL,
    timeframe TEXT DEFAULT 'weekly'
);

-- Create indexes for weekly_patterns
CREATE INDEX idx_weekly_patterns_symbol_type_exp
ON weekly_patterns(symbol, pattern_type, expiration_date DESC);

CREATE INDEX idx_weekly_patterns_detection_time
ON weekly_patterns(detection_timestamp DESC);

CREATE INDEX idx_weekly_patterns_confidence
ON weekly_patterns(confidence DESC);

CREATE INDEX idx_weekly_patterns_data_gin
ON weekly_patterns USING GIN (pattern_data);

-- Add table comment
COMMENT ON TABLE weekly_patterns IS 'Weekly timeframe pattern detections';

-- ============================================================================
-- MONTHLY PATTERNS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS monthly_patterns (
    id SERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    pattern_type TEXT NOT NULL,
    confidence NUMERIC NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    pattern_data JSONB NOT NULL,
    detection_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expiration_date TIMESTAMP WITH TIME ZONE NOT NULL,
    levels NUMERIC[] DEFAULT NULL,
    metadata JSONB DEFAULT NULL,
    timeframe TEXT DEFAULT 'monthly'
);

-- Create indexes for monthly_patterns
CREATE INDEX idx_monthly_patterns_symbol_type_exp
ON monthly_patterns(symbol, pattern_type, expiration_date DESC);

CREATE INDEX idx_monthly_patterns_detection_time
ON monthly_patterns(detection_timestamp DESC);

CREATE INDEX idx_monthly_patterns_confidence
ON monthly_patterns(confidence DESC);

CREATE INDEX idx_monthly_patterns_data_gin
ON monthly_patterns USING GIN (pattern_data);

-- Add table comment
COMMENT ON TABLE monthly_patterns IS 'Monthly timeframe pattern detections';

-- ============================================================================
-- GRANT PERMISSIONS
-- ============================================================================
GRANT SELECT, INSERT, UPDATE, DELETE ON hourly_patterns TO app_readwrite;
GRANT SELECT, INSERT, UPDATE, DELETE ON weekly_patterns TO app_readwrite;
GRANT SELECT, INSERT, UPDATE, DELETE ON monthly_patterns TO app_readwrite;

GRANT USAGE, SELECT ON SEQUENCE hourly_patterns_id_seq TO app_readwrite;
GRANT USAGE, SELECT ON SEQUENCE weekly_patterns_id_seq TO app_readwrite;
GRANT USAGE, SELECT ON SEQUENCE monthly_patterns_id_seq TO app_readwrite;
```

### 4. Drop Deprecated Table

```sql
-- Drop combo_indicators table (deprecated)
DROP TABLE IF EXISTS combo_indicators CASCADE;

-- Note: CASCADE will drop any dependent objects like indexes, constraints, etc.
```

### 5. Create Timeframe Check Constraint Function (Optional)

```sql
-- Create a domain for valid timeframes
CREATE DOMAIN timeframe_type AS TEXT
CHECK (VALUE IN ('1min', '5min', '15min', '30min', 'hourly', 'daily', 'weekly', 'monthly', 'combo', 'all'));

-- Function to validate timeframe values in arrays
CREATE OR REPLACE FUNCTION validate_timeframes(timeframes text[])
RETURNS BOOLEAN AS $$
BEGIN
    RETURN timeframes <@ ARRAY['1min', '5min', '15min', '30min', 'hourly', 'daily', 'weekly', 'monthly', 'all']::text[];
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Add constraint to definition tables
ALTER TABLE pattern_definitions
ADD CONSTRAINT check_valid_timeframes
CHECK (validate_timeframes(applicable_timeframes));

ALTER TABLE indicator_definitions
ADD CONSTRAINT check_valid_timeframes
CHECK (validate_timeframes(applicable_timeframes));
```

---

## Rollback Scripts (If Needed)

```sql
-- Rollback column additions
ALTER TABLE pattern_definitions DROP COLUMN IF EXISTS applicable_timeframes;
ALTER TABLE indicator_definitions DROP COLUMN IF EXISTS applicable_timeframes;

ALTER TABLE daily_patterns DROP COLUMN IF EXISTS timeframe;
ALTER TABLE intraday_patterns DROP COLUMN IF EXISTS timeframe;
ALTER TABLE daily_intraday_patterns DROP COLUMN IF EXISTS timeframe;
ALTER TABLE daily_indicators DROP COLUMN IF EXISTS timeframe;
ALTER TABLE intraday_indicators DROP COLUMN IF EXISTS timeframe;

-- Drop new tables
DROP TABLE IF EXISTS hourly_patterns CASCADE;
DROP TABLE IF EXISTS weekly_patterns CASCADE;
DROP TABLE IF EXISTS monthly_patterns CASCADE;

-- Recreate combo_indicators if needed (backup first!)
```

---

## Standard Timeframe Values Reference

| Value | Description | Typical Use |
|-------|-------------|-------------|
| `1min` | 1-minute bars | High-frequency trading, scalping |
| `5min` | 5-minute bars | Day trading, short-term patterns |
| `15min` | 15-minute bars | Intraday trading |
| `30min` | 30-minute bars | Intraday swing trading |
| `hourly` | 1-hour bars | Day/swing trading |
| `daily` | Daily bars | Position trading, traditional TA |
| `weekly` | Weekly bars | Long-term trends |
| `monthly` | Monthly bars | Investment timeframes |
| `all` | All timeframes | Universal indicators like volume |

---

## Testing Queries

```sql
-- Verify new columns exist
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'pattern_definitions'
AND column_name = 'applicable_timeframes';

-- Check new tables
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('hourly_patterns', 'weekly_patterns', 'monthly_patterns');

-- Verify combo_indicators is dropped
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name = 'combo_indicators';

-- Test inserting a pattern with timeframe
INSERT INTO hourly_patterns (symbol, pattern_type, confidence, pattern_data, expiration_timestamp)
VALUES ('AAPL', 'Breakout', 0.75, '{"level": 150.00}'::jsonb, NOW() + INTERVAL '4 hours');

-- Query patterns by timeframe
SELECT * FROM hourly_patterns WHERE timeframe = 'hourly' LIMIT 1;
```

---

## Notes

1. **Expiration naming**: Notice that hourly uses `expiration_timestamp` while weekly/monthly use `expiration_date` to match the existing daily_patterns convention

2. **Default timeframes**: Each table has a default timeframe value matching its intended use

3. **Index strategy**: Same indexing pattern as existing daily_patterns for consistency

4. **Permissions**: Remember to grant appropriate permissions to database users

5. **Migration order**: Execute in the order presented to avoid dependency issues

---

**END OF MODIFICATION PLAN**