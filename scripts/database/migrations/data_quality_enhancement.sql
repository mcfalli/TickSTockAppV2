-- TickStock Data Quality Enhancement - Sprint 14 Phase 2
-- Data quality monitoring tables and functions for anomaly detection
-- Execute in PGAdmin connected to 'tickstock' database

-- ==============================================================
-- PHASE 1: Data Quality Tables
-- ==============================================================

-- Create data quality alerts table
CREATE TABLE IF NOT EXISTS data_quality_alerts (
    id SERIAL PRIMARY KEY,
    alert_type VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    description TEXT NOT NULL,
    details JSONB,
    remediation_suggestion TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    resolved_by VARCHAR(100),
    resolution_notes TEXT
);

-- Create data quality metrics table
CREATE TABLE IF NOT EXISTS data_quality_metrics (
    id SERIAL PRIMARY KEY,
    metric_date DATE NOT NULL,
    symbol_count INTEGER,
    total_alerts INTEGER,
    price_anomalies INTEGER DEFAULT 0,
    volume_anomalies INTEGER DEFAULT 0,
    data_gaps INTEGER DEFAULT 0,
    avg_data_completeness NUMERIC(5,2),
    quality_score NUMERIC(5,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create data quality summary view
CREATE OR REPLACE VIEW data_quality_summary AS
SELECT 
    alert_type,
    severity,
    COUNT(*) as alert_count,
    COUNT(CASE WHEN resolved_at IS NULL THEN 1 END) as open_alerts,
    COUNT(CASE WHEN resolved_at IS NOT NULL THEN 1 END) as resolved_alerts,
    AVG(CASE WHEN resolved_at IS NOT NULL THEN 
        EXTRACT(epoch FROM resolved_at - created_at) / 3600 
    END) as avg_resolution_hours
FROM data_quality_alerts 
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY alert_type, severity;

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_data_quality_alerts_type ON data_quality_alerts (alert_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_data_quality_alerts_symbol ON data_quality_alerts (symbol, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_data_quality_alerts_severity ON data_quality_alerts (severity, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_data_quality_alerts_unresolved ON data_quality_alerts (created_at DESC) 
WHERE resolved_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_data_quality_metrics_date ON data_quality_metrics (metric_date DESC);

-- ==============================================================
-- PHASE 2: Data Quality Functions
-- ==============================================================

-- Function to log data quality alerts
CREATE OR REPLACE FUNCTION log_data_quality_alert(
    p_alert_type VARCHAR(50),
    p_symbol VARCHAR(20),
    p_severity VARCHAR(20),
    p_description TEXT,
    p_details JSONB DEFAULT NULL,
    p_remediation TEXT DEFAULT NULL
)
RETURNS INTEGER AS $$
DECLARE
    alert_id INTEGER;
BEGIN
    INSERT INTO data_quality_alerts (
        alert_type,
        symbol,
        severity,
        description,
        details,
        remediation_suggestion
    ) VALUES (
        p_alert_type,
        p_symbol,
        p_severity,
        p_description,
        p_details,
        p_remediation
    )
    RETURNING id INTO alert_id;
    
    RETURN alert_id;
END;
$$ LANGUAGE plpgsql;

-- Function to resolve data quality alert
CREATE OR REPLACE FUNCTION resolve_data_quality_alert(
    p_alert_id INTEGER,
    p_resolved_by VARCHAR(100),
    p_resolution_notes TEXT DEFAULT NULL
)
RETURNS BOOLEAN AS $$
BEGIN
    UPDATE data_quality_alerts 
    SET resolved_at = CURRENT_TIMESTAMP,
        resolved_by = p_resolved_by,
        resolution_notes = p_resolution_notes
    WHERE id = p_alert_id
    AND resolved_at IS NULL;
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- Function to calculate data completeness for a symbol
CREATE OR REPLACE FUNCTION calculate_data_completeness(
    p_symbol VARCHAR(20),
    p_days_back INTEGER DEFAULT 30
)
RETURNS JSONB AS $$
DECLARE
    result JSONB;
    total_trading_days INTEGER;
    actual_records INTEGER;
    completeness_pct NUMERIC(5,2);
    last_data_date DATE;
    days_stale INTEGER;
BEGIN
    -- Calculate expected trading days (weekdays)
    SELECT COUNT(*) INTO total_trading_days
    FROM generate_series(
        CURRENT_DATE - (p_days_back || ' days')::interval, 
        CURRENT_DATE - INTERVAL '1 day', 
        '1 day'::interval
    ) as d
    WHERE EXTRACT(dow FROM d) BETWEEN 1 AND 5;
    
    -- Get actual record count and last data date
    SELECT 
        COUNT(*),
        MAX(date)
    INTO actual_records, last_data_date
    FROM historical_data 
    WHERE symbol = p_symbol
    AND date >= CURRENT_DATE - (p_days_back || ' days')::interval;
    
    -- Calculate metrics
    completeness_pct := CASE 
        WHEN total_trading_days > 0 THEN (actual_records::numeric / total_trading_days) * 100
        ELSE 0 
    END;
    
    days_stale := CASE 
        WHEN last_data_date IS NOT NULL THEN CURRENT_DATE - last_data_date
        ELSE 9999
    END;
    
    -- Build result JSON
    result := jsonb_build_object(
        'symbol', p_symbol,
        'analysis_period_days', p_days_back,
        'expected_trading_days', total_trading_days,
        'actual_records', actual_records,
        'completeness_pct', completeness_pct,
        'last_data_date', last_data_date,
        'days_stale', days_stale,
        'quality_grade', 
        CASE 
            WHEN completeness_pct >= 95 AND days_stale <= 1 THEN 'A'
            WHEN completeness_pct >= 85 AND days_stale <= 2 THEN 'B'
            WHEN completeness_pct >= 70 AND days_stale <= 5 THEN 'C'
            WHEN completeness_pct >= 50 AND days_stale <= 10 THEN 'D'
            ELSE 'F'
        END
    );
    
    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- Function to detect price anomalies for a specific symbol
CREATE OR REPLACE FUNCTION detect_symbol_price_anomalies(
    p_symbol VARCHAR(20),
    p_days_back INTEGER DEFAULT 7,
    p_threshold NUMERIC DEFAULT 0.20
)
RETURNS TABLE (
    symbol VARCHAR(20),
    anomaly_date DATE,
    close_price NUMERIC,
    previous_close NUMERIC,
    price_change_pct NUMERIC,
    volume BIGINT,
    anomaly_type VARCHAR(50)
) AS $$
BEGIN
    RETURN QUERY
    WITH daily_changes AS (
        SELECT 
            hd.symbol,
            hd.date,
            hd.close_price,
            LAG(hd.close_price) OVER (ORDER BY hd.date) as prev_close,
            hd.volume,
            hd.high_price,
            hd.low_price
        FROM historical_data hd
        WHERE hd.symbol = p_symbol
        AND hd.date >= CURRENT_DATE - (p_days_back || ' days')::interval
        AND hd.close_price > 0
        ORDER BY hd.date
    ),
    anomalies AS (
        SELECT 
            dc.symbol,
            dc.date,
            dc.close_price,
            dc.prev_close,
            dc.volume,
            CASE 
                WHEN dc.prev_close > 0 THEN 
                    ABS(dc.close_price - dc.prev_close) / dc.prev_close 
                ELSE 0 
            END as price_change_pct,
            CASE 
                WHEN dc.prev_close > 0 AND dc.close_price > dc.prev_close THEN 'price_spike_up'
                WHEN dc.prev_close > 0 AND dc.close_price < dc.prev_close THEN 'price_spike_down'
                ELSE 'price_anomaly'
            END as anomaly_type
        FROM daily_changes dc
        WHERE dc.prev_close IS NOT NULL
        AND dc.prev_close > 0
        AND ABS(dc.close_price - dc.prev_close) / dc.prev_close >= p_threshold
    )
    SELECT 
        a.symbol::VARCHAR(20),
        a.date,
        a.close_price,
        a.prev_close,
        a.price_change_pct,
        a.volume,
        a.anomaly_type::VARCHAR(50)
    FROM anomalies a
    ORDER BY a.date DESC;
END;
$$ LANGUAGE plpgsql;

-- Function to generate daily data quality metrics
CREATE OR REPLACE FUNCTION generate_daily_quality_metrics(
    p_target_date DATE DEFAULT CURRENT_DATE
)
RETURNS JSONB AS $$
DECLARE
    result JSONB;
    total_symbols INTEGER;
    symbols_with_data INTEGER;
    avg_completeness NUMERIC(5,2);
    alert_counts JSONB;
BEGIN
    -- Count total active symbols
    SELECT COUNT(*) INTO total_symbols
    FROM symbols 
    WHERE active = true;
    
    -- Count symbols with recent data
    SELECT COUNT(DISTINCT symbol) INTO symbols_with_data
    FROM historical_data 
    WHERE date >= p_target_date - INTERVAL '3 days';
    
    -- Calculate average completeness
    WITH completeness AS (
        SELECT 
            s.symbol,
            COUNT(hd.date) as records,
            CASE 
                WHEN COUNT(hd.date) >= 5 THEN 100.0
                WHEN COUNT(hd.date) >= 3 THEN 80.0
                WHEN COUNT(hd.date) >= 1 THEN 60.0
                ELSE 0.0
            END as completeness_score
        FROM symbols s
        LEFT JOIN historical_data hd ON s.symbol = hd.symbol 
            AND hd.date >= p_target_date - INTERVAL '7 days'
        WHERE s.active = true
        GROUP BY s.symbol
    )
    SELECT AVG(completeness_score) INTO avg_completeness
    FROM completeness;
    
    -- Get alert counts by type
    SELECT jsonb_object_agg(alert_type, alert_count) INTO alert_counts
    FROM (
        SELECT 
            alert_type,
            COUNT(*) as alert_count
        FROM data_quality_alerts 
        WHERE DATE(created_at) = p_target_date
        GROUP BY alert_type
    ) alert_summary;
    
    -- Insert metrics record
    INSERT INTO data_quality_metrics (
        metric_date,
        symbol_count,
        total_alerts,
        price_anomalies,
        volume_anomalies,
        data_gaps,
        avg_data_completeness,
        quality_score
    ) VALUES (
        p_target_date,
        total_symbols,
        COALESCE((alert_counts->>'price_anomaly')::integer, 0) + 
        COALESCE((alert_counts->>'volume_anomaly')::integer, 0) + 
        COALESCE((alert_counts->>'data_gap')::integer, 0),
        COALESCE((alert_counts->>'price_anomaly')::integer, 0),
        COALESCE((alert_counts->>'volume_anomaly')::integer, 0),
        COALESCE((alert_counts->>'data_gap')::integer, 0),
        COALESCE(avg_completeness, 0),
        CASE 
            WHEN avg_completeness >= 95 THEN 95.0
            WHEN avg_completeness >= 85 THEN 85.0
            WHEN avg_completeness >= 70 THEN 70.0
            ELSE 50.0
        END
    )
    ON CONFLICT (metric_date) DO UPDATE SET
        symbol_count = EXCLUDED.symbol_count,
        total_alerts = EXCLUDED.total_alerts,
        price_anomalies = EXCLUDED.price_anomalies,
        volume_anomalies = EXCLUDED.volume_anomalies,
        data_gaps = EXCLUDED.data_gaps,
        avg_data_completeness = EXCLUDED.avg_data_completeness,
        quality_score = EXCLUDED.quality_score;
    
    -- Build result JSON
    result := jsonb_build_object(
        'date', p_target_date,
        'total_symbols', total_symbols,
        'symbols_with_recent_data', symbols_with_data,
        'data_coverage_pct', ROUND((symbols_with_data::numeric / total_symbols) * 100, 2),
        'avg_completeness', COALESCE(avg_completeness, 0),
        'alert_counts', COALESCE(alert_counts, '{}'::jsonb),
        'quality_score', CASE 
            WHEN avg_completeness >= 95 THEN 95.0
            WHEN avg_completeness >= 85 THEN 85.0
            WHEN avg_completeness >= 70 THEN 70.0
            ELSE 50.0
        END
    );
    
    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- ==============================================================
-- PHASE 3: Data Quality Views and Reports
-- ==============================================================

-- View for top data quality issues
CREATE OR REPLACE VIEW top_data_quality_issues AS
SELECT 
    symbol,
    alert_type,
    COUNT(*) as issue_count,
    MAX(severity) as max_severity,
    MIN(created_at) as first_occurrence,
    MAX(created_at) as last_occurrence,
    COUNT(CASE WHEN resolved_at IS NULL THEN 1 END) as open_issues
FROM data_quality_alerts 
WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY symbol, alert_type
HAVING COUNT(*) > 1
ORDER BY issue_count DESC, max_severity DESC;

-- View for daily quality trends
CREATE OR REPLACE VIEW daily_quality_trends AS
SELECT 
    metric_date,
    symbol_count,
    total_alerts,
    avg_data_completeness,
    quality_score,
    LAG(quality_score) OVER (ORDER BY metric_date) as prev_quality_score,
    quality_score - LAG(quality_score) OVER (ORDER BY metric_date) as quality_change
FROM data_quality_metrics 
WHERE metric_date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY metric_date DESC;

-- View for symbols requiring attention
CREATE OR REPLACE VIEW symbols_requiring_attention AS
WITH recent_issues AS (
    SELECT 
        symbol,
        COUNT(*) as recent_alert_count,
        COUNT(CASE WHEN severity IN ('high', 'critical') THEN 1 END) as critical_alerts,
        MAX(created_at) as last_alert
    FROM data_quality_alerts 
    WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
    AND resolved_at IS NULL
    GROUP BY symbol
),
data_stats AS (
    SELECT 
        symbol,
        MAX(date) as last_data_date,
        COUNT(*) as records_last_7d,
        CURRENT_DATE - MAX(date) as days_stale
    FROM historical_data 
    WHERE date >= CURRENT_DATE - INTERVAL '7 days'
    GROUP BY symbol
)
SELECT 
    COALESCE(ri.symbol, ds.symbol) as symbol,
    COALESCE(ri.recent_alert_count, 0) as recent_alerts,
    COALESCE(ri.critical_alerts, 0) as critical_alerts,
    ds.last_data_date,
    COALESCE(ds.days_stale, 999) as days_stale,
    COALESCE(ds.records_last_7d, 0) as records_last_7d,
    CASE 
        WHEN ri.critical_alerts > 0 THEN 'critical'
        WHEN ds.days_stale > 5 THEN 'high'
        WHEN ri.recent_alert_count > 2 THEN 'medium'
        WHEN ds.days_stale > 2 THEN 'medium'
        ELSE 'low'
    END as priority_level
FROM recent_issues ri
FULL OUTER JOIN data_stats ds ON ri.symbol = ds.symbol
WHERE (ri.recent_alert_count > 0 OR ds.days_stale > 2 OR ds.records_last_7d < 3)
ORDER BY 
    CASE 
        WHEN ri.critical_alerts > 0 THEN 1
        WHEN ds.days_stale > 5 THEN 2
        WHEN ri.recent_alert_count > 2 THEN 3
        ELSE 4
    END,
    COALESCE(ri.recent_alert_count, 0) DESC,
    COALESCE(ds.days_stale, 0) DESC;

-- ==============================================================
-- PHASE 4: Grant Permissions
-- ==============================================================

-- Grant permissions to app_readwrite user
GRANT ALL PRIVILEGES ON TABLE data_quality_alerts TO app_readwrite;
GRANT ALL PRIVILEGES ON TABLE data_quality_metrics TO app_readwrite;
GRANT USAGE, SELECT ON SEQUENCE data_quality_alerts_id_seq TO app_readwrite;
GRANT USAGE, SELECT ON SEQUENCE data_quality_metrics_id_seq TO app_readwrite;

-- Grant view permissions
GRANT SELECT ON data_quality_summary TO app_readwrite;
GRANT SELECT ON top_data_quality_issues TO app_readwrite;
GRANT SELECT ON daily_quality_trends TO app_readwrite;
GRANT SELECT ON symbols_requiring_attention TO app_readwrite;

-- Grant function execution permissions
GRANT EXECUTE ON FUNCTION log_data_quality_alert(VARCHAR, VARCHAR, VARCHAR, TEXT, JSONB, TEXT) TO app_readwrite;
GRANT EXECUTE ON FUNCTION resolve_data_quality_alert(INTEGER, VARCHAR, TEXT) TO app_readwrite;
GRANT EXECUTE ON FUNCTION calculate_data_completeness(VARCHAR, INTEGER) TO app_readwrite;
GRANT EXECUTE ON FUNCTION detect_symbol_price_anomalies(VARCHAR, INTEGER, NUMERIC) TO app_readwrite;
GRANT EXECUTE ON FUNCTION generate_daily_quality_metrics(DATE) TO app_readwrite;

-- ==============================================================
-- PHASE 5: Verification and Sample Data
-- ==============================================================

-- Test data quality functions
SELECT generate_daily_quality_metrics(CURRENT_DATE);

-- Sample quality check for a few symbols
DO $$ 
DECLARE
    test_symbol VARCHAR(20);
    completeness_result JSONB;
BEGIN
    -- Test completeness calculation for a few symbols
    FOR test_symbol IN 
        SELECT symbol FROM symbols WHERE active = true LIMIT 5
    LOOP
        SELECT calculate_data_completeness(test_symbol, 30) INTO completeness_result;
        
        RAISE NOTICE 'Symbol: %, Completeness: %', 
            test_symbol, 
            completeness_result->>'completeness_pct';
            
        -- Log sample alert if completeness is low
        IF (completeness_result->>'completeness_pct')::numeric < 80 THEN
            PERFORM log_data_quality_alert(
                'data_gap',
                test_symbol,
                'medium',
                'Low data completeness detected: ' || (completeness_result->>'completeness_pct') || '%',
                completeness_result,
                'Schedule historical data backfill'
            );
        END IF;
    END LOOP;
END $$;

-- Show verification queries
SELECT 'Data Quality Tables Created' as status;

SELECT * FROM data_quality_summary LIMIT 10;

SELECT * FROM top_data_quality_issues LIMIT 5;

SELECT * FROM symbols_requiring_attention LIMIT 10;

-- Show recent metrics
SELECT 
    metric_date,
    symbol_count,
    total_alerts,
    avg_data_completeness,
    quality_score
FROM data_quality_metrics 
ORDER BY metric_date DESC 
LIMIT 7;