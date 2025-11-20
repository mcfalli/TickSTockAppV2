# TickStockPL Integration Response - Complete Specifications

**Date**: 2025-01-26
**Sprint**: 33 Phase 4 Complete
**In Response To**: TickStockAppV2_TickStockPL_Integration_Clarification.md

## Executive Summary

TickStockPL Phase 1-4 is fully implemented and operational. This document provides exact specifications for TickStockAppV2 integration.

## 1. Channel Names and Event Structure

### ✅ **ANSWER: Use Colon Notation**

All TickStockPL channels use **colon notation**: `tickstock:domain:event`

### Complete Channel List

```python
# Processing Control & Status
'tickstock:processing:status'      # Overall processing status
'tickstock:processing:schedule'    # Schedule updates

# Phase-Specific Channels
'tickstock:import:started'         # Phase 2 events
'tickstock:import:progress'
'tickstock:import:completed'

'tickstock:cache:started'          # Phase 2.5 events
'tickstock:cache:progress'
'tickstock:cache:completed'

'tickstock:indicators:started'     # Phase 3 events
'tickstock:indicators:progress'
'tickstock:indicators:completed'
'tickstock:indicators:calculated'  # Individual indicator results

'tickstock:patterns:started'       # Phase 4 events
'tickstock:patterns:progress'
'tickstock:patterns:completed'
'tickstock:patterns:detected'      # Individual pattern detections

# System Channels
'tickstock:monitoring'             # System metrics & health
'tickstock:errors'                # Error events (all severities)
```

## 2. Trigger Commands

### ✅ **ANSWER: TickStockPL Uses HTTP API, NOT Redis Commands**

TickStockPL does **NOT** listen on Redis for commands. It provides HTTP API endpoints:

### API Endpoints for Triggering

```python
# Base URL: http://localhost:8080

# 1. Trigger Manual Processing
POST /api/processing/trigger-manual
Content-Type: application/json

{
    "skip_market_check": false,  # Optional, default false
    "phases": ["all"],           # Optional, default all phases
    "universe": "sp500"          # Optional, default from config
}

# Response:
{
    "run_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "started",
    "message": "Processing started successfully"
}
```

### Available API Endpoints

```python
# Processing Control
POST   /api/processing/trigger-manual    # Start processing
GET    /api/processing/status            # Current status
GET    /api/processing/history           # Historical runs
DELETE /api/processing/cancel            # Cancel current run

# Schedule Management
GET    /api/processing/schedule          # Get schedule
POST   /api/processing/schedule          # Update schedule
```

## 3. Status Event Channels

### ✅ **ANSWER: Subscribe to Specific Channels Based on Need**

For full integration, subscribe to these channels:

```python
class TickStockPLSubscriber:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.pubsub = self.redis.pubsub()

        # Core channels for dashboard
        self.core_channels = [
            'tickstock:processing:status',     # Overall status
            'tickstock:import:completed',      # Phase 2 completion
            'tickstock:indicators:completed',  # Phase 3 completion
            'tickstock:patterns:completed',    # Phase 4 completion
            'tickstock:errors'                 # All errors
        ]

        # Progress channels (optional, for real-time updates)
        self.progress_channels = [
            'tickstock:import:progress',
            'tickstock:indicators:progress',
            'tickstock:patterns:progress'
        ]

        # Detailed channels (optional, for granular tracking)
        self.detailed_channels = [
            'tickstock:indicators:calculated',  # Each indicator
            'tickstock:patterns:detected'       # Each pattern
        ]
```

## 4. Processing History Storage

### ✅ **ANSWER: TickStockPL Stores, TickStockAppV2 Queries via API**

**Storage Location**: TickStockPL PostgreSQL database
**Access Method**: HTTP API

```python
# Query processing history
GET /api/processing/history?days=7

# Response:
{
    "runs": [
        {
            "run_id": "550e8400-e29b-41d4-a716-446655440000",
            "run_date": "2025-01-26",
            "start_time": "2025-01-26T21:10:00Z",
            "end_time": "2025-01-26T21:45:00Z",
            "status": "completed",
            "symbols_processed": 505,
            "patterns_detected": 1250,
            "indicators_calculated": 7575,
            "duration_seconds": 2100
        }
    ]
}
```

## 5. Schedule Management

### ✅ **ANSWER: TickStockPL Has Own Scheduler**

**Primary**: TickStockPL runs APScheduler internally (4:10 PM ET daily)
**Manual**: TickStockAppV2 can trigger via API
**External**: Optional systemd/cron as backup

```python
# Get current schedule
GET /api/processing/schedule

# Response:
{
    "enabled": true,
    "trigger_time": "16:10",
    "timezone": "America/New_York",
    "next_run": "2025-01-27T21:10:00Z",
    "universes": ["sp500", "nasdaq100"]
}

# Update schedule
POST /api/processing/schedule
{
    "enabled": true,
    "trigger_time": "16:15"  # Change to 4:15 PM
}
```

## Complete Event Specifications

### 1. Processing Started Event

**Channel**: `tickstock:processing:status`

```json
{
    "event": "processing_started",
    "timestamp": "2025-01-26T21:10:00Z",
    "source": "daily_scheduler",
    "version": "1.0",
    "payload": {
        "run_id": "550e8400-e29b-41d4-a716-446655440000",
        "run_date": "2025-01-26",
        "phases": ["import", "cache_sync", "indicators", "patterns"],
        "universe": "sp500",
        "trigger_type": "automatic"
    }
}
```

### 2. Phase Progress Event

**Channel**: `tickstock:import:progress` (example for import phase)

```json
{
    "event": "import_progress",
    "timestamp": "2025-01-26T21:15:00Z",
    "source": "daily_import_job",
    "version": "1.0",
    "payload": {
        "run_id": "550e8400-e29b-41d4-a716-446655440000",
        "completed_symbols": 250,
        "total_symbols": 505,
        "percent_complete": 49.5,
        "current_symbol": "GOOGL",
        "eta_seconds": 300
    }
}
```

### 3. Phase Completion Event

**Channel**: `tickstock:patterns:completed` (example for patterns)

```json
{
    "event": "pattern_processing_completed",
    "timestamp": "2025-01-26T21:45:00Z",
    "source": "daily_pattern_job",
    "version": "1.0",
    "payload": {
        "run_id": "550e8400-e29b-41d4-a716-446655440000",
        "total_symbols": 505,
        "patterns_detected": 1250,
        "success_rate": 99.0,
        "duration_seconds": 1200
    }
}
```

### 4. Error Event

**Channel**: `tickstock:errors`

```json
{
    "event": "error",
    "timestamp": "2025-01-26T21:20:00Z",
    "source": "massive_fetcher",
    "version": "1.0",
    "payload": {
        "severity": "error",
        "component": "data_import",
        "error_code": "RATE_LIMIT_EXCEEDED",
        "message": "Massive API rate limit hit",
        "context": {
            "symbol": "AAPL",
            "retry_after": 60
        }
    }
}
```

## Implementation Code for TickStockAppV2

### Complete Redis Subscriber

```python
import redis
import json
import threading

class TickStockPLEventSubscriber:
    """Subscribe to TickStockPL events via Redis"""

    def __init__(self, socketio, redis_config=None):
        self.socketio = socketio
        self.redis_config = redis_config or {
            'host': 'localhost',
            'port': 6379,
            'decode_responses': True
        }
        self.redis = redis.Redis(**self.redis_config)
        self.pubsub = self.redis.pubsub()
        self.thread = None

    def start(self):
        """Start listening to TickStockPL events"""
        # Subscribe to all relevant channels
        channels = [
            'tickstock:processing:status',
            'tickstock:import:*',
            'tickstock:cache:*',
            'tickstock:indicators:*',
            'tickstock:patterns:*',
            'tickstock:errors',
            'tickstock:monitoring'
        ]

        for channel in channels:
            self.pubsub.psubscribe(channel)

        # Start listener thread
        self.thread = threading.Thread(target=self._listen)
        self.thread.daemon = True
        self.thread.start()

    def _listen(self):
        """Process incoming events"""
        for message in self.pubsub.listen():
            if message['type'] in ['message', 'pmessage']:
                try:
                    channel = message['channel']
                    event = json.loads(message['data'])
                    self._handle_event(channel, event)
                except json.JSONDecodeError:
                    pass

    def _handle_event(self, channel, event):
        """Route events to handlers"""
        event_type = event.get('event')
        payload = event.get('payload', {})

        # Route to appropriate handler
        if 'processing:status' in channel:
            self._handle_processing_status(event_type, payload)
        elif 'import:' in channel:
            self._handle_import_event(event_type, payload)
        elif 'indicators:' in channel:
            self._handle_indicator_event(event_type, payload)
        elif 'patterns:' in channel:
            self._handle_pattern_event(event_type, payload)
        elif 'errors' in channel:
            self._handle_error_event(payload)

    def _handle_processing_status(self, event_type, payload):
        """Handle overall processing status"""
        self.socketio.emit('processing_status', {
            'type': event_type,
            'run_id': payload.get('run_id'),
            'status': payload.get('status'),
            'phases': payload.get('phases')
        }, namespace='/admin')

    def _handle_import_event(self, event_type, payload):
        """Handle data import events"""
        if event_type == 'import_progress':
            self.socketio.emit('import_progress', {
                'percent': payload.get('percent_complete'),
                'current': payload.get('current_symbol'),
                'eta': payload.get('eta_seconds')
            }, namespace='/admin')
        elif event_type == 'import_completed':
            self.socketio.emit('import_complete', {
                'symbols': payload.get('successful_symbols'),
                'duration': payload.get('duration_seconds')
            }, namespace='/admin')
```

### API Client for Commands

```python
import requests

class TickStockPLAPIClient:
    """API client for TickStockPL commands"""

    def __init__(self, base_url='http://localhost:8080'):
        self.base_url = base_url

    def trigger_processing(self, skip_market_check=False):
        """Trigger manual processing"""
        response = requests.post(
            f'{self.base_url}/api/processing/trigger-manual',
            json={'skip_market_check': skip_market_check}
        )
        return response.json()

    def get_status(self):
        """Get current processing status"""
        response = requests.get(f'{self.base_url}/api/processing/status')
        return response.json()

    def get_history(self, days=7):
        """Get processing history"""
        response = requests.get(
            f'{self.base_url}/api/processing/history',
            params={'days': days}
        )
        return response.json()

    def cancel_processing(self):
        """Cancel current processing"""
        response = requests.delete(f'{self.base_url}/api/processing/cancel')
        return response.json()
```

## Testing the Integration

### 1. Test Redis Events
```bash
# Subscribe to all TickStockPL events
redis-cli PSUBSCRIBE "tickstock:*"

# In another terminal, trigger processing
curl -X POST http://localhost:8080/api/processing/trigger-manual \
  -H "Content-Type: application/json" \
  -d '{"skip_market_check": true}'
```

### 2. Verify Event Flow
You should see events in this order:
1. `tickstock:processing:status` - processing_started
2. `tickstock:import:started`
3. `tickstock:import:progress` (multiple)
4. `tickstock:import:completed`
5. `tickstock:cache:started`
6. `tickstock:cache:completed`
7. `tickstock:indicators:started`
8. `tickstock:indicators:progress` (multiple)
9. `tickstock:indicators:completed`
10. `tickstock:patterns:started`
11. `tickstock:patterns:progress` (multiple)
12. `tickstock:patterns:completed`
13. `tickstock:processing:status` - processing_completed

## Summary of Key Points

1. **Channels**: Use colon notation (tickstock:domain:event)
2. **Commands**: Use HTTP API, not Redis commands
3. **Storage**: TickStockPL stores all data, access via API
4. **Scheduler**: TickStockPL has internal scheduler (APScheduler)
5. **Events**: Full pub-sub for monitoring, no commands via Redis
6. **Integration**: One-way data flow (TickStockPL → Redis → TickStockAppV2)

## Next Steps for TickStockAppV2

1. Implement `TickStockPLEventSubscriber` class
2. Implement `TickStockPLAPIClient` class
3. Remove all mock data generators
4. Connect Redis subscriber to WebSocket emitters
5. Test with live TickStockPL instance

## Contact

For any additional questions, the complete implementation is in:
- Phase 2: `src/jobs/daily_import_job.py`
- Phase 3: `src/jobs/daily_indicator_job.py`
- Phase 4: `src/jobs/daily_pattern_job.py`
- Scheduler: `src/services/daily_processing_scheduler.py`
- API: `src/api/processing_endpoints.py`

**TickStockPL Phase 4 is COMPLETE and READY for integration!**