-- Create processing_runs table for Sprint 33 Phase 4
-- This table stores processing run history from TickStockPL

-- Drop table if you need to recreate it
-- DROP TABLE IF EXISTS processing_runs;

-- Create the processing_runs table
CREATE TABLE IF NOT EXISTS processing_runs (
    run_id VARCHAR(64) PRIMARY KEY,
    trigger_type VARCHAR(32),
    status VARCHAR(32),
    phase VARCHAR(64),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds INTEGER,
    symbols_total INTEGER DEFAULT 0,
    symbols_processed INTEGER DEFAULT 0,
    symbols_failed INTEGER DEFAULT 0,
    indicators_total INTEGER DEFAULT 0,
    indicators_processed INTEGER DEFAULT 0,
    indicators_failed INTEGER DEFAULT 0,
    error_message TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_processing_runs_started_at
ON processing_runs(started_at DESC);

CREATE INDEX IF NOT EXISTS idx_processing_runs_status
ON processing_runs(status);

-- Grant permissions to app_readwrite user
GRANT ALL PRIVILEGES ON TABLE processing_runs TO app_readwrite;

-- Verify table was created
SELECT
    'processing_runs table created successfully' as message,
    COUNT(*) as row_count
FROM processing_runs;