#!/usr/bin/env python3
"""
Complete the integration logging implementation to track pattern event flow.
This adds the missing flow tracking calls to actually log the events.
"""

import re

def fix_redis_event_subscriber():
    """Add complete integration logging to redis_event_subscriber.py"""
    file_path = "C:/Users/McDude/TickStockAppV2/src/core/services/redis_event_subscriber.py"

    with open(file_path, 'r') as f:
        content = f.read()

    # Check if imports are already there
    if "from src.core.services.integration_logger import" not in content:
        # Add imports after other imports
        import_lines = """from src.core.services.integration_logger import (
    flow_logger, IntegrationPoint, log_redis_publish, log_websocket_delivery
)
"""
        content = content.replace(
            "from src.core.models.events import TickStockEvent, EventType",
            f"from src.core.models.events import TickStockEvent, EventType\n{import_lines}"
        )

    # Fix the _process_message method to add complete flow tracking
    # Find the section after event creation and add flow tracking
    old_section = """            event = TickStockEvent(
                event_type=event_type,
                source=event_data.get('source', 'unknown'),
                timestamp=event_data.get('timestamp', time.time()),
                data=event_data,
                channel=channel
            )

            # Process event
            self._handle_event(event)"""

    new_section = """            event = TickStockEvent(
                event_type=event_type,
                source=event_data.get('source', 'unknown'),
                timestamp=event_data.get('timestamp', time.time()),
                data=event_data,
                channel=channel
            )

            # Integration logging for pattern events
            if event_type == EventType.PATTERN_DETECTED:
                flow_id = flow_logger.start_flow(event_data)
                if flow_id:
                    flow_logger.log_checkpoint(flow_id, IntegrationPoint.EVENT_RECEIVED, channel)
                    flow_logger.log_checkpoint(flow_id, IntegrationPoint.EVENT_PARSED,
                                             f"{event_data.get('data', {}).get('pattern', 'unknown')}@{event_data.get('data', {}).get('symbol', 'unknown')}")

            # Process event
            self._handle_event(event)

            # Complete flow tracking
            if event_type == EventType.PATTERN_DETECTED and flow_id:
                flow_logger.complete_flow(flow_id)"""

    if "# Integration logging for pattern events" not in content:
        content = content.replace(old_section, new_section)

    # Also add logging at the beginning of _handle_pattern_event
    old_handler_start = """    def _handle_pattern_event(self, event: TickStockEvent):
        \"\"\"Handle pattern detection events with user filtering.\"\"\"
        pattern_data = event.data
        pattern_name = pattern_data.get('pattern')
        symbol = pattern_data.get('symbol')"""

    new_handler_start = """    def _handle_pattern_event(self, event: TickStockEvent):
        \"\"\"Handle pattern detection events with user filtering.\"\"\"
        pattern_data = event.data.get('data', {}) if 'data' in event.data else event.data
        pattern_name = pattern_data.get('pattern')
        symbol = pattern_data.get('symbol')

        # Log pattern event reception
        if pattern_name and symbol:
            flow_logger.log_checkpoint('', IntegrationPoint.PATTERN_RECEIVED,
                                     f"{pattern_name}@{symbol}")"""

    content = content.replace(old_handler_start, new_handler_start)

    with open(file_path, 'w') as f:
        f.write(content)

    print("[OK] Updated redis_event_subscriber.py with complete integration logging")

def add_database_logging_table():
    """Create a database table for integration logging as a backup/audit trail."""

    sql_script = """-- Integration Event Logging Table for TickStock
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
"""

    # Save the SQL script
    with open("C:/Users/McDude/TickStockAppV2/scripts/database/create_integration_logging_table.sql", 'w') as f:
        f.write(sql_script)

    print("[OK] Created database integration logging table script")
    print("     Run with: PGPASSWORD=LJI48rUEkUpe6e psql -h localhost -p 5433 -U app_readwrite -d tickstock -f scripts/database/create_integration_logging_table.sql")

def create_simple_integration_test():
    """Create a simple test to verify integration logging is working."""

    test_script = """#!/usr/bin/env python3
'''
Simple integration test to verify pattern flow logging.
Sends a test pattern and checks both log file and database.
'''

import redis
import json
import time
from datetime import datetime

def test_integration_logging():
    r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

    # Create properly formatted pattern event
    pattern_event = {
        "event_type": "pattern_detected",
        "source": "TickStockPL",
        "timestamp": time.time(),
        "data": {
            "symbol": "AAPL",
            "pattern": "Hammer",  # This is the correct field name
            "confidence": 0.95,
            "detection_timestamp": datetime.now().isoformat(),
            "timeframe": "5min",
            "price": 185.50
        }
    }

    channel = "tickstock.events.patterns"

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Sending test pattern event...")
    print(f"  Pattern: {pattern_event['data']['pattern']}")
    print(f"  Symbol: {pattern_event['data']['symbol']}")
    print(f"  Confidence: {pattern_event['data']['confidence']}")

    subscribers = r.publish(channel, json.dumps(pattern_event))
    print(f"  Subscribers: {subscribers}")

    print("\\n[CHECK] Integration log file for flow tracking:")
    print("  Look for: EVENT_RECEIVED -> EVENT_PARSED -> PATTERN_RECEIVED -> WEBSOCKET_DELIVERED")

    print("\\n[CHECK] Database for audit trail (if table created):")
    print("  SELECT * FROM integration_events ORDER BY timestamp DESC LIMIT 10;")

if __name__ == "__main__":
    test_integration_logging()
"""

    with open("C:/Users/McDude/TickStockAppV2/scripts/test_integration_logging.py", 'w') as f:
        f.write(test_script)

    print("[OK] Created simple integration test script")

def main():
    """Complete the integration logging implementation."""
    print("=" * 60)
    print("Completing Integration Logging Implementation")
    print("=" * 60)

    try:
        # 1. Fix the code
        fix_redis_event_subscriber()

        # 2. Create database table option
        add_database_logging_table()

        # 3. Create test script
        create_simple_integration_test()

        print("\n" + "=" * 60)
        print("[SUCCESS] Integration logging completed!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Restart TickStockAppV2")
        print("2. Run: python scripts/test_integration_logging.py")
        print("3. Check logs/integration_*.log for flow tracking")
        print("\nOptional: Create database table for permanent audit trail:")
        print("  cd C:/Users/McDude/TickStockAppV2")
        print("  Run the psql command shown above")

    except Exception as e:
        print(f"\n[ERROR] Failed to complete integration logging: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()