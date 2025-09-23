# TickStock Database Table Definitions

## Table of Contents

- **OHLCV Data Tables** (5 tables)
- **Symbol & Universe Tables** (8 tables)
- **Pattern Tables** (10 tables) - Updated: Added hourly, weekly, monthly patterns
- **Indicator Tables** (6 tables) - Updated: Removed combo_indicators
- **User & Authentication Tables** (8 tables)
- **Billing & Subscription Tables** (3 tables)
- **Integration & Monitoring Tables** (2 tables)
- **Analytics & Cache Tables** (2 tables)
- **System Tables** (2 tables)
- **Deprecated/Unused Tables** (6 tables) - Updated: Added combo_indicators

---

## OHLCV Data Tables

### ohlcv_1min
- **Purpose**: Minute-level OHLCV data storage (TimescaleDB hypertable)
- **Fields**:
  - symbol: varchar(20) - Stock ticker symbol
  - timestamp: timestamptz - Minute timestamp
  - open: numeric - Opening price
  - high: numeric - Highest price in minute
  - low: numeric - Lowest price in minute
  - close: numeric - Closing price
  - volume: bigint - Trading volume
- **Usage**: Real-time tick aggregation and historical minute data

### ohlcv_daily
- **Purpose**: Daily OHLCV data storage
- **Fields**:
  - symbol: varchar(20) - Stock ticker symbol
  - date: date - Trading date
  - open: numeric - Opening price
  - high: numeric - Daily high
  - low: numeric - Daily low
  - close: numeric - Closing price
  - volume: bigint - Daily volume
  - created_at: timestamptz (nullable) - Record creation timestamp
- **Usage**: Daily aggregations and historical daily data

### ohlcv_hourly
- **Purpose**: Hourly OHLCV data storage (TimescaleDB hypertable)
- **Fields**:
  - symbol: varchar(20) - Stock ticker symbol
  - timestamp: timestamptz - Hour boundary timestamp
  - open: numeric (nullable) - Opening price
  - high: numeric (nullable) - Hourly high
  - low: numeric (nullable) - Hourly low
  - close: numeric (nullable) - Closing price
  - volume: bigint (nullable) - Hourly volume
- **Usage**: Hourly aggregations for medium-term analysis

### ohlcv_weekly
- **Purpose**: Weekly OHLCV data storage
- **Fields**:
  - symbol: varchar(20) - Stock ticker symbol
  - week_start: date - Monday of the week
  - open: numeric (nullable) - Weekly opening price
  - high: numeric (nullable) - Weekly high
  - low: numeric (nullable) - Weekly low
  - close: numeric (nullable) - Weekly closing price
  - volume: bigint (nullable) - Weekly volume
- **Usage**: Weekly aggregations for trend analysis

### ohlcv_monthly
- **Purpose**: Monthly OHLCV data storage
- **Fields**:
  - symbol: varchar(20) - Stock ticker symbol
  - month_start: date - First day of month
  - open: numeric (nullable) - Monthly opening price
  - high: numeric (nullable) - Monthly high
  - low: numeric (nullable) - Monthly low
  - close: numeric (nullable) - Monthly closing price
  - volume: bigint (nullable) - Monthly volume
- **Usage**: Monthly aggregations for long-term analysis

## Symbol & Universe Tables

### symbols
- **Purpose**: Master symbol registry with comprehensive metadata
- **Fields**:
  - symbol: varchar(20) - Primary key ticker symbol
  - name: varchar(100) - Company/ETF name
  - exchange: varchar(20) - Primary exchange
  - last_updated: timestamp - Last metadata update
  - market: varchar(20) - Market type (stocks/crypto/fx)
  - locale: varchar(10) - Geographic locale
  - currency_name: varchar(10) - Trading currency
  - currency_symbol: varchar(5) - Currency symbol
  - type: varchar(20) - Security type (CS/ETF/ADRC)
  - active: boolean - Currently trading
  - cik: varchar(20) - SEC CIK number
  - composite_figi: varchar(50) - FIGI identifier
  - share_class_figi: varchar(50) - Share class FIGI
  - last_updated_utc: timestamptz - UTC update timestamp
  - market_cap: bigint - Market capitalization
  - weighted_shares_outstanding: bigint - Weighted shares
  - etf_type: varchar(50) - ETF classification
  - aum_millions: numeric - Assets under management
  - expense_ratio: numeric - ETF expense ratio
  - underlying_index: varchar(100) - Tracking index
  - correlation_reference: varchar(10) - Correlation symbol
  - fmv_supported: boolean - Fair market value support
  - creation_unit_size: integer - ETF creation units
  - dividend_frequency: varchar(20) - Dividend schedule
  - inception_date: date - Fund inception date
  - net_assets: bigint - Total net assets
  - primary_exchange: varchar(20) - Primary listing
  - issuer: varchar(100) - ETF issuer
  - average_spread: numeric - Bid-ask spread
  - daily_volume_avg: bigint - Average daily volume
  - premium_discount_avg: numeric - ETF premium/discount
  - tracking_error: numeric - Index tracking error
  - sic_code: varchar(10) - SIC industry code
  - sic_description: text - SIC description
  - sector: varchar(50) - Business sector
  - industry: varchar(100) - Industry classification
  - country: varchar(5) - Country code
  - total_employees: integer - Employee count
  - list_date: date - IPO/listing date
  - sic_updated_at: timestamp - SIC update timestamp
- **Usage**: Central symbol metadata and ETF information

### cache_entries
- **Purpose**: Universe definitions and cached symbol groups
- **Fields**:
  - id: integer - Primary key
  - type: varchar(50) - Cache type
  - name: varchar(100) - Universe name
  - key: varchar(100) - Cache key
  - value: jsonb - Cached data
  - environment: varchar(10) - Environment (dev/prod)
  - created_at: timestamp - Creation time
  - updated_at: timestamp - Last update
  - universe_category: varchar(50) - Category classification
  - liquidity_filter: jsonb - Liquidity criteria
  - universe_metadata: jsonb - Additional metadata
  - last_universe_update: timestamp - Universe refresh time
- **Usage**: Symbol universe management and caching

### symbols_related_tickers
- **Purpose**: Symbol relationships from Polygon API
- **Fields**:
  - id: integer - Primary key
  - symbol: varchar(20) - Primary symbol
  - related_symbol: varchar(20) - Related ticker
  - created_at: timestamp - Creation time
  - updated_at: timestamp - Last update
- **Usage**: Track related symbols for correlation analysis

### symbol_load_log
- **Purpose**: CSV universe file loading history
- **Fields**:
  - id: integer - Primary key
  - csv_filename: varchar(255) - Source file name
  - loaded_at: timestamp - Load timestamp
  - symbol_count: integer - Total symbols in file
  - symbols_loaded: integer - Successfully loaded
  - symbols_updated: integer - Updated records
  - symbols_skipped: integer - Skipped records
  - ohlcv_records_loaded: integer - OHLCV records added
  - load_status: varchar(50) - Load status
  - error_message: text - Error details
  - load_duration_seconds: double precision - Processing time
  - created_at: timestamp - Creation time
  - updated_at: timestamp - Last update
- **Usage**: Track bulk symbol loading operations

### etf_classifications
- **Purpose**: ETF sector/style classifications
- **Fields**:
  - symbol: varchar(20) - ETF symbol
  - classification_type: varchar(50) - Classification type
  - classification_value: varchar(100) - Classification value
  - weight_percentage: numeric - Weight in category
  - source: varchar(50) - Data source
  - last_updated: timestamptz - Update timestamp
- **Usage**: ETF categorization for universe creation (Future)

### etf_fmv_cache
- **Purpose**: ETF fair market value calculations
- **Fields**:
  - symbol: varchar(20) - ETF symbol
  - timestamp: timestamptz - Calculation time
  - nav_estimate: numeric - NAV estimate
  - premium_discount: numeric - Premium/discount
  - confidence_score: numeric - Calculation confidence
  - component_symbols: array - Component stocks
  - calculation_method: varchar(50) - Calc method
  - created_at: timestamptz - Creation time
- **Usage**: ETF valuation caching (Future)

### equity_types
- **Purpose**: Equity type definitions and processing rules
- **Fields**:
  - category: varchar(50) - Category name
  - code: varchar(10) - Type code
  - description: varchar(100) - Description
  - why_include: text - Inclusion rationale
  - update_frequency: varchar(20) - Update schedule
  - processing_rules: jsonb - Processing config
  - requires_eod_validation: boolean - EOD check required
  - additional_data_fields: jsonb - Extra fields
  - priority_level: integer - Processing priority
  - batch_size: integer - Batch size
  - rate_limit_ms: integer - Rate limit delay
- **Usage**: Define equity types and their processing rules

## Pattern Tables

### pattern_definitions
- **Purpose**: Registry of all pattern types with metadata
- **Fields**:
  - id: integer - Primary key
  - name: varchar(100) - Pattern name
  - short_description: varchar(255) - Brief description
  - long_description: text - Detailed description
  - basic_logic_description: text - Detection logic
  - code_reference: varchar(255) - Implementation reference
  - category: varchar(50) - Pattern category
  - created_date: timestamp - Creation date
  - updated_date: timestamp - Last update
  - enabled: boolean - Active flag
  - display_order: integer - UI display order
  - confidence_threshold: numeric - Min confidence
  - risk_level: varchar(20) - Risk classification
  - typical_success_rate: numeric - Historical success rate
  - created_by: varchar(100) - Creator
  - applicable_timeframes: text[] - Timeframes pattern can be detected on (NEW)
- **Usage**: Master pattern reference

### daily_patterns
- **Purpose**: Daily timeframe pattern detections
- **Fields**:
  - id: integer - Primary key
  - symbol: text - Stock symbol
  - pattern_type: text - Pattern name
  - confidence: numeric - Confidence score
  - pattern_data: jsonb - Pattern details
  - detection_timestamp: timestamptz - Detection time
  - expiration_date: timestamptz - Pattern expiration
  - levels: array - Support/resistance levels
  - metadata: jsonb - Additional metadata
  - timeframe: text - Specific timeframe (default 'daily') (NEW)
- **Usage**: Store daily pattern detections from TickStockPL

### intraday_patterns
- **Purpose**: Real-time intraday pattern detections
- **Fields**:
  - id: integer - Primary key
  - symbol: text - Stock symbol
  - pattern_type: text - Pattern name
  - confidence: numeric - Confidence score
  - pattern_data: jsonb - Pattern details
  - detection_timestamp: timestamptz - Detection time
  - expiration_timestamp: timestamptz - Pattern expiration
  - levels: array - Support/resistance levels
  - metadata: jsonb - Additional metadata
  - timeframe: text - Specific timeframe (default '5min') (NEW)
- **Usage**: Store intraday patterns from TickStockPL streaming

### daily_intraday_patterns
- **Purpose**: Combo patterns combining daily and intraday signals
- **Fields**:
  - id: integer - Primary key
  - symbol: text - Stock symbol
  - pattern_type: text - Pattern name
  - confidence: numeric - Confidence score
  - pattern_data: jsonb - Combined pattern data
  - daily_pattern_id: integer - Reference to daily pattern
  - daily_pattern_timestamp: timestamptz - Daily pattern time
  - intraday_signal: jsonb - Intraday component
  - detection_timestamp: timestamptz - Detection time
  - expiration_timestamp: timestamptz - Pattern expiration
  - levels: array - Combined levels
  - metadata: jsonb - Additional metadata
  - timeframe: text - Specific timeframe (default 'combo') (NEW)
- **Usage**: Multi-timeframe pattern confirmations

### hourly_patterns (NEW)
- **Purpose**: Hourly timeframe pattern detections
- **Fields**:
  - id: integer - Primary key
  - symbol: text - Stock symbol
  - pattern_type: text - Pattern name
  - confidence: numeric - Confidence score
  - pattern_data: jsonb - Pattern details
  - detection_timestamp: timestamptz - Detection time
  - expiration_timestamp: timestamptz - Pattern expiration
  - levels: array - Support/resistance levels
  - metadata: jsonb - Additional metadata
  - timeframe: text - Specific timeframe (default 'hourly')
- **Usage**: Store hourly pattern detections from TickStockPL

### weekly_patterns (NEW)
- **Purpose**: Weekly timeframe pattern detections
- **Fields**:
  - id: integer - Primary key
  - symbol: text - Stock symbol
  - pattern_type: text - Pattern name
  - confidence: numeric - Confidence score
  - pattern_data: jsonb - Pattern details
  - detection_timestamp: timestamptz - Detection time
  - expiration_date: timestamptz - Pattern expiration
  - levels: array - Support/resistance levels
  - metadata: jsonb - Additional metadata
  - timeframe: text - Specific timeframe (default 'weekly')
- **Usage**: Store weekly pattern detections from TickStockPL

### monthly_patterns (NEW)
- **Purpose**: Monthly timeframe pattern detections
- **Fields**:
  - id: integer - Primary key
  - symbol: text - Stock symbol
  - pattern_type: text - Pattern name
  - confidence: numeric - Confidence score
  - pattern_data: jsonb - Pattern details
  - detection_timestamp: timestamptz - Detection time
  - expiration_date: timestamptz - Pattern expiration
  - levels: array - Support/resistance levels
  - metadata: jsonb - Additional metadata
  - timeframe: text - Specific timeframe (default 'monthly')
- **Usage**: Store monthly pattern detections from TickStockPL

### pattern_detections
- **Purpose**: Historical pattern detection tracking with outcomes
- **Fields**:
  - id: bigint - Primary key
  - pattern_id: integer - Reference to pattern_definitions
  - symbol: varchar(10) - Stock symbol
  - detected_at: timestamp - Detection timestamp
  - confidence: numeric - Confidence score
  - price_at_detection: numeric - Price when detected
  - volume_at_detection: bigint - Volume when detected
  - pattern_data: jsonb - Pattern specifics
  - outcome_1d: numeric - 1-day return
  - outcome_5d: numeric - 5-day return
  - outcome_30d: numeric - 30-day return
  - outcome_evaluated_at: timestamp - Evaluation time
- **Usage**: Track pattern performance for backtesting

### pattern_performance_metrics
- **Purpose**: Pattern processing performance statistics
- **Fields**:
  - id: integer - Primary key
  - pattern_table: text - Source table
  - symbol: text - Stock symbol
  - detection_count: integer - Total detections
  - avg_processing_time_ms: numeric - Average processing time
  - last_cleanup: timestamptz - Last cleanup run
  - created_at: timestamptz - Creation time
  - updated_at: timestamptz - Last update
- **Usage**: Monitor pattern detection performance

### pattern_statistics
- **Purpose**: Aggregate pattern statistics by type and tier
- **Fields**:
  - id: integer - Primary key
  - pattern_type: text - Pattern name
  - tier: text - Detection tier (daily/intraday/combo)
  - total_detections: integer - Total count
  - avg_confidence: numeric - Average confidence
  - last_detection: timestamptz - Most recent detection
  - created_at: timestamptz - Creation time
  - updated_at: timestamptz - Last update
- **Usage**: Pattern detection analytics

### pattern_correlations_cache
- **Purpose**: Pattern correlation analysis cache
- **Fields**:
  - id: bigint - Primary key
  - pattern_a_id: integer - First pattern ID
  - pattern_b_id: integer - Second pattern ID
  - pattern_a_name: varchar(100) - First pattern name
  - pattern_b_name: varchar(100) - Second pattern name
  - correlation_coefficient: numeric - Correlation value
  - co_occurrence_count: integer - Co-occurrence count
  - temporal_relationship: varchar(20) - Time relationship
  - statistical_significance: boolean - Significant flag
  - p_value: numeric - Statistical p-value
  - calculated_for_period: integer - Period in days
  - calculated_at: timestamp - Calculation time
  - valid_until: timestamp - Cache expiration
- **Usage**: Store pattern correlation analysis results

## Indicator Tables

### indicator_definitions
- **Purpose**: Registry of all indicator types with configuration
- **Fields**:
  - id: integer - Primary key
  - name: varchar(100) - Indicator name
  - short_description: varchar(255) - Brief description
  - long_description: text - Detailed description
  - basic_logic_description: text - Calculation logic
  - code_reference: varchar(255) - Implementation reference
  - category: varchar(50) - Indicator category
  - created_date: timestamp - Creation date
  - updated_date: timestamp - Last update
  - enabled: boolean - Active flag
  - display_order: integer - UI display order
  - period: integer - Default period
  - parameters: jsonb - Configuration parameters
  - output_type: varchar(50) - Output data type
  - typical_range: varchar(100) - Typical value range
  - created_by: varchar(100) - Creator
  - applicable_timeframes: text[] - Timeframes indicator can be calculated on (NEW)
- **Usage**: Master indicator reference

### daily_indicators
- **Purpose**: Daily-calculated technical indicators
- **Fields**:
  - id: integer - Primary key
  - symbol: text - Stock symbol
  - indicator_type: text - Indicator name
  - value_data: jsonb - Indicator values
  - calculation_timestamp: timestamptz - Calculation time
  - expiration_date: timestamptz - Data expiration
  - metadata: jsonb - Additional metadata
  - timeframe: text - Specific timeframe (default 'daily') (NEW)
- **Usage**: Store daily indicator calculations

### intraday_indicators
- **Purpose**: Real-time streaming indicators
- **Fields**:
  - id: integer - Primary key
  - symbol: text - Stock symbol
  - indicator_type: text - Indicator name
  - value_data: jsonb - Indicator values
  - calculation_timestamp: timestamptz - Calculation time
  - expiration_timestamp: timestamptz - Data expiration
  - metadata: jsonb - Additional metadata
  - timeframe: text - Specific timeframe (default '5min') (NEW)
- **Usage**: Store real-time indicator calculations

### indicator_calculation_cache
- **Purpose**: Indicator calculation result caching
- **Fields**:
  - id: integer - Primary key
  - symbol: text - Stock symbol
  - indicator_type: text - Indicator name
  - tier: text - Calculation tier
  - cache_key: text - Cache identifier
  - cached_data: jsonb - Cached results
  - created_at: timestamptz - Creation time
  - expires_at: timestamptz - Expiration time
  - access_count: integer - Access counter
  - last_accessed: timestamptz - Last access time
- **Usage**: Cache frequently accessed indicator calculations

### indicator_dependencies
- **Purpose**: Define indicator calculation dependencies
- **Fields**:
  - id: integer - Primary key
  - indicator_type: text - Dependent indicator
  - depends_on_indicator: text - Required indicator
  - dependency_type: text - Dependency type
  - calculation_order: integer - Calculation sequence
  - created_at: timestamptz - Creation time
- **Usage**: Manage indicator calculation order

### indicator_statistics
- **Purpose**: Indicator calculation performance metrics
- **Fields**:
  - id: integer - Primary key
  - indicator_type: text - Indicator name
  - tier: text - Calculation tier
  - total_calculations: integer - Total calculations
  - avg_calculation_time_ms: numeric - Average calc time
  - cache_hit_rate: numeric - Cache effectiveness
  - last_calculation: timestamptz - Last calculation
  - created_at: timestamptz - Creation time
  - updated_at: timestamptz - Last update
- **Usage**: Monitor indicator calculation performance

## User & Authentication Tables

### users
- **Purpose**: User account management
- **Fields**:
  - id: integer - Primary key
  - email: varchar(120) - Email address
  - username: varchar(50) - Username
  - phone: varchar(20) - Phone number
  - password_hash: varchar(128) - Hashed password
  - subscription_tier: varchar(50) - Subscription level
  - created_at: timestamp - Account creation
  - updated_at: timestamp - Last update
  - is_verified: boolean - Email verified
  - is_active: boolean - Account active
  - last_login_at: timestamp - Last login time
  - failed_login_attempts: integer - Failed login count
  - account_locked_until: timestamp - Lock expiration
  - lockout_count: integer - Total lockouts
  - is_disabled: boolean - Account disabled
  - first_name: varchar(100) - First name
  - last_name: varchar(100) - Last name
  - terms_accepted: boolean - Terms accepted
  - terms_accepted_at: timestamptz - Terms acceptance time
  - terms_version: varchar(20) - Terms version
  - role: varchar(20) - User role
- **Usage**: Core user authentication and profile

### sessions
- **Purpose**: User session management
- **Fields**:
  - session_id: varchar(36) - Session identifier
  - user_id: integer - User reference
  - ip_address: varchar(45) - Client IP
  - user_agent: varchar(255) - Browser info
  - fingerprint: jsonb - Device fingerprint
  - refresh_token_hash: varchar(128) - Refresh token
  - status: varchar(20) - Session status
  - created_at: timestamp - Session start
  - last_active_at: timestamp - Last activity
  - expires_at: timestamp - Session expiration
- **Usage**: Track active user sessions

### user_settings
- **Purpose**: User preferences and configuration
- **Fields**:
  - id: integer - Primary key
  - user_id: integer - User reference
  - key: varchar(100) - Setting key
  - value: jsonb - Setting value
  - created_at: timestamp - Creation time
  - updated_at: timestamp - Last update
- **Usage**: Store user preferences

### user_filters
- **Purpose**: User filter configurations
- **Fields**:
  - id: integer - Primary key
  - user_id: integer - User reference
  - filter_name: varchar(100) - Filter name
  - filter_data: jsonb - Filter configuration
  - created_at: timestamp - Creation time
  - updated_at: timestamp - Last update
- **Usage**: Save user-defined filters

### user_history
- **Purpose**: User activity audit log
- **Fields**:
  - id: integer - Primary key
  - user_id: integer - User reference
  - field: varchar(50) - Changed field
  - old_value: varchar(255) - Previous value
  - new_value: varchar(255) - New value
  - change_type: varchar(50) - Change type
  - changed_at: timestamp - Change timestamp
- **Usage**: Track user account changes

### verification_codes
- **Purpose**: Email/phone verification codes
- **Fields**:
  - id: integer - Primary key
  - user_id: integer - User reference
  - code: varchar(10) - Verification code
  - verification_type: varchar(50) - Code type
  - created_at: timestamp - Creation time
  - expires_at: timestamp - Expiration time
- **Usage**: Temporary verification codes

### communication_log
- **Purpose**: User communication tracking
- **Fields**:
  - id: integer - Primary key
  - user_id: integer - User reference
  - communication_type: varchar(50) - Message type
  - status: varchar(20) - Delivery status
  - error_message: text - Error details
  - created_at: timestamp - Send time
- **Usage**: Track email/SMS communications

### tagged_stocks
- **Purpose**: User stock tagging (Future feature)
- **Fields**:
  - id: integer - Primary key
  - user_id: integer - User reference
  - ticker: varchar(10) - Stock symbol
  - tag_name: varchar(50) - Tag name
  - created_at: timestamp - Creation time
  - updated_at: timestamp - Last update
- **Usage**: User-defined stock tags (Future)

## Billing & Subscription Tables

### subscriptions
- **Purpose**: User subscription management
- **Fields**:
  - id: integer - Primary key
  - user_id: integer - User reference
  - subscription_type: varchar(50) - Subscription type
  - subscription_tier: varchar(50) - Tier level
  - status: varchar(50) - Subscription status
  - start_date: timestamptz - Start date
  - end_date: timestamptz - End date
  - next_billing_date: timestamptz - Next billing
  - canceled_at: timestamptz - Cancellation date
  - created_at: timestamptz - Creation time
  - updated_at: timestamptz - Last update
- **Usage**: Manage user subscriptions

### billing_info
- **Purpose**: User billing information
- **Fields**:
  - id: integer - Primary key
  - user_id: integer - User reference
  - address_line1: varchar(255) - Street address
  - address_line2: varchar(255) - Address line 2
  - city: varchar(100) - City
  - state_province: varchar(100) - State/Province
  - postal_code: varchar(20) - ZIP/Postal code
  - country: varchar(100) - Country
  - payment_processor: varchar(50) - Payment processor
  - payment_method_id: varchar(255) - Method ID
  - last_four: varchar(4) - Card last 4 digits
  - card_type: varchar(50) - Card type
  - expiry_month: integer - Expiration month
  - expiry_year: integer - Expiration year
  - is_default: boolean - Default payment method
  - created_at: timestamptz - Creation time
  - updated_at: timestamptz - Last update
- **Usage**: Store billing information

### payment_history
- **Purpose**: Payment transaction history
- **Fields**:
  - id: integer - Primary key
  - user_id: integer - User reference
  - subscription_id: integer - Subscription reference
  - amount: numeric - Payment amount
  - currency: varchar(3) - Currency code
  - status: varchar(50) - Payment status
  - payment_processor: varchar(50) - Processor used
  - transaction_id: varchar(255) - Transaction ID
  - payment_date: timestamptz - Payment date
  - billing_period_start: timestamptz - Period start
  - billing_period_end: timestamptz - Period end
  - error_message: text - Error details
  - created_at: timestamptz - Creation time
- **Usage**: Track payment transactions

## Integration & Monitoring Tables

### integration_events
- **Purpose**: TickStockPL integration event logging
- **Fields**:
  - id: integer - Primary key
  - flow_id: uuid - Flow identifier
  - timestamp: timestamptz - Event time
  - event_type: varchar(50) - Event type
  - source_system: varchar(50) - Source system
  - checkpoint: varchar(100) - Processing checkpoint
  - channel: varchar(100) - Redis channel
  - symbol: varchar(20) - Stock symbol
  - pattern_name: varchar(50) - Pattern name
  - confidence: numeric - Confidence score
  - user_count: integer - Affected users
  - details: jsonb - Event details
  - latency_ms: numeric - Processing latency
  - created_at: timestamptz - Creation time
- **Usage**: Track TickStockPL integration events

### market_conditions
- **Purpose**: Market environment tracking
- **Fields**:
  - id: bigint - Primary key
  - timestamp: timestamp - Measurement time
  - market_volatility: numeric - Volatility index
  - volatility_percentile: numeric - Volatility percentile
  - overall_volume: bigint - Total market volume
  - volume_vs_average: numeric - Volume ratio
  - market_trend: varchar(20) - Trend direction
  - trend_strength: numeric - Trend strength
  - session_type: varchar(20) - Session type
  - day_of_week: integer - Day of week
  - advancing_count: integer - Advancing stocks
  - declining_count: integer - Declining stocks
  - advance_decline_ratio: numeric - A/D ratio
  - sp500_change: numeric - S&P 500 change
  - nasdaq_change: numeric - NASDAQ change
  - dow_change: numeric - DOW change
  - calculated_at: timestamp - Calculation time
  - data_source: varchar(50) - Data source
- **Usage**: Market context for pattern correlation

## Analytics & Cache Tables

### advanced_metrics_cache
- **Purpose**: Advanced pattern metrics caching
- **Fields**:
  - id: bigint - Primary key
  - pattern_id: integer - Pattern reference
  - pattern_name: varchar(100) - Pattern name
  - success_rate: numeric - Success percentage
  - confidence_interval_95: numeric - 95% CI
  - max_win_streak: integer - Max winning streak
  - max_loss_streak: integer - Max losing streak
  - sharpe_ratio: numeric - Risk-adjusted return
  - max_drawdown: numeric - Maximum drawdown
  - avg_recovery_time: numeric - Recovery time
  - statistical_significance: boolean - Significant flag
  - total_detections: integer - Total count
  - calculated_for_period: integer - Period in days
  - calculated_at: timestamp - Calculation time
  - valid_until: timestamp - Cache expiration
- **Usage**: Cache complex analytics calculations

### temporal_performance_cache
- **Purpose**: Time-based performance metrics cache
- **Fields**:
  - id: bigint - Primary key
  - pattern_id: integer - Pattern reference
  - pattern_name: varchar(100) - Pattern name
  - time_bucket: varchar(20) - Time period
  - bucket_type: varchar(10) - Bucket type
  - detection_count: integer - Detection count
  - success_count: integer - Success count
  - success_rate: numeric - Success rate
  - avg_return: numeric - Average return
  - avg_confidence: numeric - Average confidence
  - statistical_significance: boolean - Significant flag
  - calculated_for_period: integer - Period in days
  - calculated_at: timestamp - Calculation time
  - valid_until: timestamp - Cache expiration
- **Usage**: Cache temporal performance analysis

## System Tables

### app_settings
- **Purpose**: Application configuration storage
- **Fields**:
  - id: integer - Primary key
  - key: varchar(100) - Setting key
  - value: jsonb - Setting value
  - created_at: timestamp - Creation time
  - updated_at: timestamp - Last update
- **Usage**: Store application-wide settings

### alembic_version
- **Purpose**: Database migration tracking
- **Fields**:
  - version_num: varchar(32) - Migration version
- **Usage**: Track applied database migrations

## Deprecated/Unused Tables

### stock_main
- **Purpose**: OLD - Replaced by symbols table
- **Status**: DEPRECATED - Use symbols table instead

### stock_related_tickers
- **Purpose**: OLD - Replaced by symbols_related_tickers
- **Status**: DEPRECATED - Use symbols_related_tickers instead

### stock_data
- **Purpose**: OLD - Early event detection storage
- **Status**: DEPRECATED - Replaced by pattern tables

### ticks
- **Purpose**: OLD - Raw tick data storage
- **Status**: DEPRECATED - Using OHLCV aggregations instead

### events
- **Purpose**: OLD - Event detection storage
- **Status**: DEPRECATED - Replaced by pattern detection tables

### combo_indicators
- **Purpose**: OLD - Multi-timeframe indicator combinations
- **Status**: DEPRECATED - Use separate timeframe-specific indicator tables instead
- **Replacement**: Store indicators in timeframe-specific tables (daily_indicators, intraday_indicators, etc.)