-- Integration Event Logging Table for TickStock
-- Provides audit trail for pattern event flow between TickStockPL and TickStockAppV2

CREATE TABLE IF NOT EXISTS integration_events (
    id SERIAL PRIMARY KEY,
    flow_id UUID,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    event_type VARCHAR(50) NOT NULL,
    source_system VARCHAR(50) NOT NULL,  -- 'TickStockPL' or 'TickStockAppV2'
    checkpoint VARCHAR(100) NOT NULL,     -- 'EVENT_RECEIVED', 'PATTERN_PARSED', etc.
    channel VARCHAR(100),
    symbol VARCHAR(20),
    pattern_name VARCHAR(50),
    confidence DECIMAL(3,2),
    user_count INTEGER,
    details JSONB,
    latency_ms DECIMAL(10,2),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for fast queries
CREATE INDEX idx_integration_events_flow_id ON integration_events(flow_id);
CREATE INDEX idx_integration_events_timestamp ON integration_events(timestamp DESC);
CREATE INDEX idx_integration_events_symbol ON integration_events(symbol);
CREATE INDEX idx_integration_events_pattern ON integration_events(pattern_name);

-- View for pattern flow analysis
CREATE OR REPLACE VIEW pattern_flow_analysis AS
SELECT
    flow_id,
    MIN(timestamp) as start_time,
    MAX(timestamp) as end_time,
    EXTRACT(EPOCH FROM (MAX(timestamp) - MIN(timestamp))) * 1000 as total_latency_ms,
    symbol,
    pattern_name,
    MAX(confidence) as confidence,
    MAX(user_count) as users_notified,
    COUNT(*) as checkpoints_logged,
    ARRAY_AGG(checkpoint ORDER BY timestamp) as flow_path
FROM integration_events
WHERE flow_id IS NOT NULL
GROUP BY flow_id, symbol, pattern_name;

-- Function to log integration events from Python
CREATE OR REPLACE FUNCTION log_integration_event(
    p_flow_id UUID,
    p_event_type VARCHAR(50),
    p_source VARCHAR(50),
    p_checkpoint VARCHAR(100),
    p_channel VARCHAR(100) DEFAULT NULL,
    p_symbol VARCHAR(20) DEFAULT NULL,
    p_pattern VARCHAR(50) DEFAULT NULL,
    p_confidence DECIMAL(3,2) DEFAULT NULL,
    p_user_count INTEGER DEFAULT NULL,
    p_details JSONB DEFAULT NULL
) RETURNS VOID AS $$
BEGIN
    INSERT INTO integration_events (
        flow_id, event_type, source_system, checkpoint,
        channel, symbol, pattern_name, confidence,
        user_count, details
    ) VALUES (
        p_flow_id, p_event_type, p_source, p_checkpoint,
        p_channel, p_symbol, p_pattern, p_confidence,
        p_user_count, p_details
    );
END;
$$ LANGUAGE plpgsql;

-- Grant permissions
GRANT ALL ON integration_events TO app_readwrite;
GRANT ALL ON pattern_flow_analysis TO app_readwrite;
GRANT EXECUTE ON FUNCTION log_integration_event TO app_readwrite;
