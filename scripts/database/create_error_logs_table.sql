-- Sprint 32: Error Management System Database Schema
-- Created: 2025-09-25
-- Purpose: Create error_logs table for unified error handling system

CREATE TABLE IF NOT EXISTS error_logs (
    id SERIAL PRIMARY KEY,
    error_id VARCHAR(255) UNIQUE NOT NULL,
    source VARCHAR(50) NOT NULL,  -- 'TickStockAppV2' or 'TickStockPL'
    severity VARCHAR(20) NOT NULL,  -- critical|error|warning|info|debug
    category VARCHAR(50),  -- pattern|database|network|validation|performance|security|configuration
    message TEXT NOT NULL,
    component VARCHAR(100),
    traceback TEXT,
    context JSONB,
    timestamp TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for performance and common queries
CREATE INDEX IF NOT EXISTS idx_error_logs_timestamp ON error_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_error_logs_severity ON error_logs(severity);
CREATE INDEX IF NOT EXISTS idx_error_logs_source ON error_logs(source);
CREATE INDEX IF NOT EXISTS idx_error_logs_category ON error_logs(category);
CREATE INDEX IF NOT EXISTS idx_error_logs_component ON error_logs(component);
CREATE INDEX IF NOT EXISTS idx_error_logs_created_at ON error_logs(created_at DESC);

-- Add JSONB index for context queries
CREATE INDEX IF NOT EXISTS idx_error_logs_context_gin ON error_logs USING GIN (context);

-- Grant proper permissions to app_readwrite user
GRANT SELECT, INSERT, UPDATE, DELETE ON error_logs TO app_readwrite;
GRANT USAGE, SELECT ON SEQUENCE error_logs_id_seq TO app_readwrite;

-- Add comments for documentation
COMMENT ON TABLE error_logs IS 'Sprint 32: Unified error logging for TickStockAppV2 and TickStockPL systems';
COMMENT ON COLUMN error_logs.error_id IS 'UUID for tracking errors across systems';
COMMENT ON COLUMN error_logs.source IS 'System that generated the error: TickStockAppV2 or TickStockPL';
COMMENT ON COLUMN error_logs.severity IS 'Error severity level for filtering and alerting';
COMMENT ON COLUMN error_logs.category IS 'Error category for grouping and analysis';
COMMENT ON COLUMN error_logs.context IS 'JSON context data (symbol, user_id, etc.)';
COMMENT ON COLUMN error_logs.timestamp IS 'When the error occurred';
COMMENT ON COLUMN error_logs.created_at IS 'When the error was logged to database';