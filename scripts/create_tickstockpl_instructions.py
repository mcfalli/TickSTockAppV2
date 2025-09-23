#!/usr/bin/env python3
"""Create integration logging instructions for TickStockPL."""

instructions = """# Integration Logging Instructions for TickStockPL

## Purpose
To enable 100% confirmation of pattern event flow between TickStockPL (producer) and TickStockAppV2 (consumer), we need TickStockPL to log when it publishes pattern events.

## Database Table Already Created
The `integration_events` table has been created in the TickStock database and is ready to receive logs.

## Implementation for TickStockPL

### Step 1: Add Database Connection
Add this to your pattern detection service or wherever you publish patterns:

```python
import psycopg2
import uuid
from datetime import datetime

# Database connection (add to your initialization)
def get_db_connection():
    return psycopg2.connect(
        host='localhost',
        port=5432,
        database='tickstock',
        user='app_readwrite',
        password='LJI48rUEkUpe6e'
    )
```

### Step 2: Add Logging When Publishing Patterns
Wherever TickStockPL publishes pattern events to Redis, add this logging:

```python
def publish_pattern_event(redis_client, symbol, pattern_name, confidence, pattern_data):
    \"\"\"Publish pattern event with integration logging.\"\"\"

    # Your existing Redis publish code
    channel = 'tickstock.events.patterns'
    event = {
        "event_type": "pattern_detected",
        "source": "TickStockPL",
        "timestamp": time.time(),
        "data": {
            "symbol": symbol,
            "pattern": pattern_name,  # Make sure field is "pattern" not "pattern_type"
            "confidence": confidence,
            # ... other pattern data
        }
    }

    # Publish to Redis (your existing code)
    redis_client.publish(channel, json.dumps(event))

    # ADD THIS: Log to integration_events table
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Generate a flow ID for this pattern event
        flow_id = str(uuid.uuid4())

        # Log the publish event
        cur.execute(\"\"\"
            INSERT INTO integration_events (
                flow_id, event_type, source_system, checkpoint,
                channel, symbol, pattern_name, confidence, details
            ) VALUES (
                %s, 'pattern_detected', 'TickStockPL', 'PATTERN_PUBLISHED',
                %s, %s, %s, %s, %s::jsonb
            )
        \"\"\", (
            flow_id,
            channel,
            symbol,
            pattern_name,
            confidence,
            json.dumps({"timestamp": datetime.now().isoformat()})
        ))

        conn.commit()
        cur.close()
        conn.close()

        print(f"[INTEGRATION] Logged pattern publish: {pattern_name}@{symbol} (flow_id: {flow_id})")

    except Exception as e:
        print(f"[WARNING] Failed to log integration event: {e}")
        # Don't fail the pattern publish if logging fails
```

### Step 3: Alternative Simpler Approach (Using Function)
If you prefer, use the stored function instead:

```python
def log_pattern_publish(symbol, pattern_name, confidence):
    \"\"\"Log pattern publish to integration_events table.\"\"\"
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(\"\"\"
            SELECT log_integration_event(
                gen_random_uuid(),
                'pattern_detected',
                'TickStockPL',
                'PATTERN_PUBLISHED',
                'tickstock.events.patterns',
                %s, %s, %s, NULL, NULL
            )
        \"\"\", (symbol, pattern_name, confidence))

        conn.commit()
        cur.close()
        conn.close()

    except Exception as e:
        print(f"[WARNING] Integration logging failed: {e}")
```

## Verification

### Check if Logging is Working
Run this query to see TickStockPL's published patterns:

```bash
PGPASSWORD=LJI48rUEkUpe6e psql -h localhost -p 5432 -U app_readwrite -d tickstock -c "SELECT timestamp, checkpoint, symbol, pattern_name, confidence FROM integration_events WHERE source_system='TickStockPL' ORDER BY timestamp DESC LIMIT 10;"
```

### Check Complete Flow (Both Apps)
To see the complete pattern flow from TickStockPL → TickStockAppV2:

```bash
PGPASSWORD=LJI48rUEkUpe6e psql -h localhost -p 5432 -U app_readwrite -d tickstock -c "SELECT timestamp, source_system, checkpoint, symbol, pattern_name FROM integration_events ORDER BY timestamp DESC LIMIT 20;"
```

### Check Flow Analysis
To see pattern flow with latency measurements:

```bash
PGPASSWORD=LJI48rUEkUpe6e psql -h localhost -p 5432 -U app_readwrite -d tickstock -c "SELECT * FROM pattern_flow_analysis ORDER BY start_time DESC LIMIT 5;"
```

## Expected Flow
When both apps are logging correctly, you'll see:

1. TickStockPL: `PATTERN_PUBLISHED` - When pattern is detected and published
2. TickStockAppV2: `EVENT_RECEIVED` - When Redis message is received
3. TickStockAppV2: `PATTERN_PARSED` - When pattern data is extracted
4. TickStockAppV2: `PATTERN_CACHED` - When stored in Redis cache
5. TickStockAppV2: `WEBSOCKET_DELIVERED` - When sent to users

## Important Field Names
Make sure your pattern events use these exact field names:
- `pattern` (NOT `pattern_type` or `pattern_name`)
- `symbol`
- `confidence`
- `timestamp`

## Testing
After implementing, test by:
1. Run your pattern detection service
2. Wait for a pattern to be detected
3. Check the database table for entries
4. Verify both TickStockPL and TickStockAppV2 entries exist for the same pattern

## Benefits
- Complete audit trail of all pattern events
- Latency measurements between publish and receive
- Easy debugging of integration issues
- Historical analysis of pattern flow
- No complex setup - just database inserts

## Notes
- The table is already created and ready
- Logging failures won't break pattern publishing (wrapped in try/except)
- Each pattern gets a unique flow_id for tracking through the system
- Timestamps are automatic (database handles them)
"""

# Write to file with UTF-8 encoding
with open('C:/Users/McDude/TickStockAppV2/docs/temp.md', 'w', encoding='utf-8') as f:
    f.write(instructions)

print("Created integration logging instructions at: C:/Users/McDude/TickStockAppV2/docs/temp.md")
print("\nInstructions provide complete implementation details for TickStockPL to add database logging.")
print("The integration_events table is already created and ready to use!")