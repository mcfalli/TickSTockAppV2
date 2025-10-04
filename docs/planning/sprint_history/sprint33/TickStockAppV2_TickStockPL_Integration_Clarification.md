# TickStockAppV2 ↔ TickStockPL Integration Clarification

**Date**: 2025-09-26
**Sprint**: 33 Phase 4
**Purpose**: Clarify integration points and responsibilities between TickStockAppV2 and TickStockPL

## Current Understanding

### Architecture Roles
- **TickStockPL**: Producer - Runs all processing (data import, indicators, patterns)
- **TickStockAppV2**: Consumer - Displays status, triggers jobs, shows results

### Communication Pattern
All communication via Redis pub-sub (loose coupling):
- TickStockAppV2 → TickStockPL: Publishes trigger commands
- TickStockPL → TickStockAppV2: Publishes status events

## Questions for TickStockPL Team

### 1. Channel Names and Event Structure

**Current Documentation Shows Multiple Patterns:**
- Phase 1: `tickstock:processing:status`, `tickstock:processing:schedule`
- Phase 2: `tickstock:monitoring` (with source filtering)
- Phase 3: `tickstock:indicators:started`, `tickstock:indicators:progress`, `tickstock:indicators:completed`
- Existing: `tickstock.events.patterns` (dot notation)

**Question**: Which channel naming convention should we use?
- Colon notation: `tickstock:domain:event`
- Dot notation: `tickstock.domain.event`
- Mixed based on phase?

### 2. Trigger Commands

**Question**: What Redis channels/events does TickStockPL listen for to trigger processing?

**Our Assumption:**
```json
// Channel: tickstock:commands:trigger (or similar?)
{
    "command": "trigger_daily_processing",
    "parameters": {
        "skip_market_check": false,
        "phases": ["data_import", "indicators", "patterns"],
        "run_id": "uuid-here"
    },
    "source": "TickStockAppV2",
    "timestamp": "2025-09-26T16:00:00Z"
}
```

**Please confirm:**
- Exact channel name for commands
- Event structure for triggers
- Available command types
- Required vs optional parameters

### 3. Status Event Channels

**From Documentation We See:**
```javascript
// Multiple channels mentioned:
'tickstock:processing:status'     // Phase 1
'tickstock:processing:schedule'   // Phase 1
'tickstock:monitoring'            // Phase 2
'tickstock:indicators:started'    // Phase 3
'tickstock:indicators:progress'   // Phase 3
'tickstock:indicators:completed'  // Phase 3
'tickstock:errors'               // Error events
```

**Question**: Should TickStockAppV2 subscribe to ALL these channels or is there a consolidated channel?

### 4. Processing History Storage

**Question**: Where should processing run history be stored?
- TickStockPL database (producer owns data)?
- TickStockAppV2 database (consumer stores what it displays)?
- Redis with TTL (temporary shared state)?

**Our Preference**: TickStockPL stores, TickStockAppV2 queries via Redis request/response pattern

### 5. Schedule Management

**Question**: Who manages the daily processing schedule?
- TickStockPL has its own scheduler?
- TickStockAppV2 triggers at scheduled times?
- External scheduler (cron/systemd)?

**Current Implementation**: Dashboard shows schedule controls but unclear who enforces it

## Current TickStockAppV2 Status

### ✅ Completed
- Dashboard UI for all 3 phases
- Frontend JavaScript event handling
- Progress bars and status displays
- Manual trigger buttons
- Schedule control interface

### ⚠️ Needs Implementation
1. **Redis Subscriber**: Not listening to TickStockPL events
2. **Command Publisher**: Not sending trigger commands to TickStockPL
3. **History Storage**: Using in-memory storage (lost on restart)
4. **Real Integration**: All backend using mock data

### 🔧 Ready to Implement (Pending Clarification)
```python
class ProcessingEventSubscriber:
    """Subscribe to TickStockPL processing events"""

    def __init__(self, redis_client, socketio):
        self.channels = [
            # NEED CONFIRMATION OF EXACT CHANNELS
            'tickstock:processing:status',
            'tickstock:indicators:*',
            # ...
        ]

class ProcessingCommandPublisher:
    """Publish commands to TickStockPL"""

    def trigger_processing(self, parameters):
        # NEED CONFIRMATION OF CHANNEL AND FORMAT
        channel = 'tickstock:commands:trigger'  # ???
        self.redis.publish(channel, json.dumps({...}))
```

## Specific Redis Events We Need

Please provide exact Redis event specifications for:

### 1. Trigger Daily Processing
- Channel name
- Event structure
- Response/acknowledgment pattern

### 2. Cancel Processing
- Channel name
- Event structure
- Expected behavior

### 3. Query Processing Status
- Request channel/pattern
- Response format
- Polling vs subscription model

### 4. Query Processing History
- Request pattern
- Response format
- Pagination support?

### 5. Retry Failed Imports
- Channel name
- Event structure
- Symbol list format

### 6. Manual Indicator Trigger
- Channel name
- Event structure
- Symbol/indicator filtering

## Proposed Integration Timeline

1. **Immediate** (Today): Remove all mock code, prepare subscriber framework
2. **Upon Clarification**: Implement exact Redis patterns
3. **Testing**: Validate with actual TickStockPL instance
4. **Phase 4 Completion**: Full bidirectional integration

## Contact

Please respond with clarifications via:
- Update this document with answers
- Create response document in sprint33 folder
- Or provide working example code

**TickStockAppV2 Team Ready to Integrate!**