
-- Index for correlation analysis (time-bucketed)
CREATE INDEX IF NOT EXISTS idx_pattern_detections_correlation
ON pattern_detections (DATE_TRUNC('hour', detected_at), pattern_id, confidence)
WHERE detected_at >= CURRENT_TIMESTAMP - INTERVAL '90 days';

CREATE INDEX IF NOT EXISTS idx_pattern_detections_correlation
ON pattern_detections (DATE_TRUNC('hour', detected_at), pattern_id, confidence);

-- Index for market context correlation
CREATE INDEX IF NOT EXISTS idx_pattern_detections_market_context
ON pattern_detections (pattern_id, detected_at, outcome_1d, confidence)
WHERE detected_at >= CURRENT_TIMESTAMP - INTERVAL '60 days';

CREATE INDEX IF NOT EXISTS idx_pattern_detections_market_context
ON pattern_detections (pattern_id, detected_at, outcome_1d, confidence);

-- ==============================================================
-- Cache Table Performance Indexes
-- ==============================================================

-- Indexes for pattern_correlations_cache
CREATE INDEX IF NOT EXISTS idx_correlations_cache_lookup
ON pattern_correlations_cache (pattern_a_id, pattern_b_id, valid_until)
WHERE valid_until > CURRENT_TIMESTAMP;

CREATE INDEX IF NOT EXISTS idx_correlations_cache_lookup
ON pattern_correlations_cache (pattern_a_id, pattern_b_id, valid_until);


CREATE INDEX IF NOT EXISTS idx_correlations_cache_strength
ON pattern_correlations_cache (ABS(correlation_coefficient) DESC, statistical_significance)
WHERE valid_until > CURRENT_TIMESTAMP;

CREATE INDEX IF NOT EXISTS idx_correlations_cache_pattern_names
ON pattern_correlations_cache (pattern_a_name, pattern_b_name, valid_until)
WHERE valid_until > CURRENT_TIMESTAMP;

-- Indexes for temporal_performance_cache
CREATE INDEX IF NOT EXISTS idx_temporal_cache_lookup
ON temporal_performance_cache (pattern_id, bucket_type, valid_until)
WHERE valid_until > CURRENT_TIMESTAMP;

CREATE INDEX IF NOT EXISTS idx_temporal_cache_performance
ON temporal_performance_cache (pattern_name, success_rate DESC, bucket_type)
WHERE valid_until > CURRENT_TIMESTAMP;

CREATE INDEX IF NOT EXISTS idx_temporal_cache_time_bucket
ON temporal_performance_cache (time_bucket, bucket_type, success_rate DESC)
WHERE valid_until > CURRENT_TIMESTAMP;

-- Indexes for advanced_metrics_cache
CREATE INDEX IF NOT EXISTS idx_advanced_cache_lookup
ON advanced_metrics_cache (pattern_id, valid_until)
WHERE valid_until > CURRENT_TIMESTAMP;

CREATE INDEX IF NOT EXISTS idx_advanced_cache_performance  
ON advanced_metrics_cache (success_rate DESC, sharpe_ratio DESC, statistical_significance)
WHERE valid_until > CURRENT_TIMESTAMP;


-- Fixed indexes for pattern_correlations_cache
CREATE INDEX IF NOT EXISTS idx_correlations_cache_strength
ON pattern_correlations_cache (ABS(correlation_coefficient) DESC, statistical_significance);

CREATE INDEX IF NOT EXISTS idx_correlations_cache_pattern_names
ON pattern_correlations_cache (pattern_a_name, pattern_b_name, valid_until);

-- Fixed indexes for temporal_performance_cache
CREATE INDEX IF NOT EXISTS idx_temporal_cache_lookup
ON temporal_performance_cache (pattern_id, bucket_type, valid_until);

CREATE INDEX IF NOT EXISTS idx_temporal_cache_performance
ON temporal_performance_cache (pattern_name, success_rate DESC, bucket_type);

CREATE INDEX IF NOT EXISTS idx_temporal_cache_time_bucket
ON temporal_performance_cache (time_bucket, bucket_type, success_rate DESC);

-- Fixed indexes for advanced_metrics_cache
CREATE INDEX IF NOT EXISTS idx_advanced_cache_lookup
ON advanced_metrics_cache (pattern_id, valid_until);

CREATE INDEX IF NOT EXISTS idx_advanced_cache_performance
ON advanced_metrics_cache (success_rate DESC, sharpe_ratio DESC, statistical_significance);


Suggestions from these altered sql do we apply these?  
-- Retention policies to mimic time-based filtering
SELECT add_retention_policy('pattern_correlations_cache', INTERVAL '60 days');
SELECT add_retention_policy('temporal_performance_cache', INTERVAL '60 days');
SELECT add_retention_policy('advanced_metrics_cache', INTERVAL '60 days');

-- Compression policies for storage optimization
ALTER TABLE pattern_correlations_cache SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'pattern_a_id',
    timescaledb.compress_orderby = 'valid_until DESC'
);
SELECT add_compression_policy('pattern_correlations_cache', INTERVAL '7 days');

ALTER TABLE temporal_performance_cache SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'pattern_id',
    timescaledb.compress_orderby = 'valid_until DESC'
);
SELECT add_compression_policy('temporal_performance_cache', INTERVAL '7 days');

ALTER TABLE advanced_metrics_cache SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'pattern_id',
    timescaledb.compress_orderby = 'valid_until DESC'
);
SELECT add_compression_policy('advanced_metrics_cache', INTERVAL '7 days');


Error:
-- Test materialized view refresh
\timing on
SELECT refresh_analytics_views();
\timing off
ERROR:  cannot refresh materialized view "public.mv_pattern_correlation_summary" concurrently
HINT:  Create a unique index with no WHERE clause on one or more columns of the materialized view.
CONTEXT:  SQL statement "REFRESH MATERIALIZED VIEW CONCURRENTLY mv_pattern_correlation_summary"
PL/pgSQL function refresh_analytics_views() line 4 at SQL statement 
SQL state: 55000



