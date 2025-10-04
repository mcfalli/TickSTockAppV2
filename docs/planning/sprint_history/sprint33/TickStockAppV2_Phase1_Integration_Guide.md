# TickStockAppV2 Phase 1 Integration Guide

**Sprint**: 33 - Phase 1
**Date**: 2025-01-25
**Purpose**: Step-by-step integration guide for TickStockAppV2 to consume Phase 1 processing engine events

## Quick Start Checklist

- [ ] Verify Redis connection to TickStockPL Redis instance
- [ ] Subscribe to new processing channels
- [ ] Add UI components for processing status
- [ ] Implement event handlers
- [ ] Test with sample events
- [ ] Add error handling

## 1. Redis Channel Subscription

### Channels to Subscribe

```javascript
// Add these channels to your existing Redis subscription
const PROCESSING_CHANNELS = [
    'tickstock:processing:status',     // Processing status events
    'tickstock:processing:schedule',   // Schedule updates
    'tickstock:monitoring',            // System monitoring (filter for processing)
    'tickstock:errors'                // Error events (filter for processing)
];
```

### Implementation Example

```javascript
// Assuming you have a Redis subscriber setup
class ProcessingEventHandler {
    constructor(redisClient) {
        this.redis = redisClient;
        this.currentRunId = null;
        this.processingStatus = {
            isRunning: false,
            progress: 0,
            phase: null,
            estimatedCompletion: null
        };
    }

    subscribe() {
        // Subscribe to processing channels
        this.redis.subscribe(PROCESSING_CHANNELS);

        // Handle incoming messages
        this.redis.on('message', (channel, message) => {
            try {
                const event = JSON.parse(message);
                this.handleEvent(channel, event);
            } catch (error) {
                console.error('Failed to parse message:', error);
            }
        });
    }

    handleEvent(channel, event) {
        switch(channel) {
            case 'tickstock:processing:status':
                this.handleProcessingStatus(event);
                break;
            case 'tickstock:errors':
                if (event.payload?.component?.includes('processing')) {
                    this.handleProcessingError(event);
                }
                break;
            case 'tickstock:monitoring':
                if (event.source?.includes('processing') ||
                    event.source?.includes('scheduler')) {
                    this.handleMonitoringEvent(event);
                }
                break;
        }
    }

    handleProcessingStatus(event) {
        switch(event.event) {
            case 'daily_processing_started':
                this.onProcessingStarted(event.payload);
                break;
            case 'daily_processing_progress':
                this.onProcessingProgress(event.payload);
                break;
            case 'daily_processing_completed':
                this.onProcessingCompleted(event.payload);
                break;
        }
    }

    onProcessingStarted(payload) {
        this.currentRunId = payload.run_id;
        this.processingStatus = {
            isRunning: true,
            progress: 0,
            phase: 'Starting',
            estimatedCompletion: null,
            symbolsTotal: payload.symbols_count,
            triggerType: payload.trigger_type
        };

        // Update UI
        this.updateUI();

        // Show notification
        this.showNotification('Processing Started',
            `Processing ${payload.symbols_count} symbols`, 'info');
    }

    onProcessingProgress(payload) {
        this.processingStatus = {
            ...this.processingStatus,
            progress: payload.percent_complete,
            phase: payload.phase,
            estimatedCompletion: payload.estimated_completion,
            currentSymbol: payload.current_symbol,
            symbolsCompleted: payload.symbols_completed
        };

        // Update UI
        this.updateProgressBar(payload.percent_complete);
        this.updateStatusText(payload.phase, payload.current_symbol);
    }

    onProcessingCompleted(payload) {
        this.processingStatus = {
            isRunning: false,
            progress: 100,
            phase: 'Completed',
            lastRun: new Date().toISOString()
        };

        // Show completion notification
        const message = `Processed: ${payload.symbols_processed}, ` +
                       `Failed: ${payload.symbols_failed}, ` +
                       `Duration: ${Math.round(payload.duration_seconds / 60)} minutes`;

        this.showNotification(
            payload.status === 'success' ? 'Processing Complete' : 'Processing Failed',
            message,
            payload.status === 'success' ? 'success' : 'error'
        );

        // Clear progress UI after delay
        setTimeout(() => this.clearProgressUI(), 5000);
    }

    handleProcessingError(event) {
        const { severity, component, message } = event.payload;

        // Log error
        console.error(`Processing Error [${severity}]: ${message}`);

        // Show error notification for critical/error severity
        if (severity === 'critical' || severity === 'error') {
            this.showNotification('Processing Error', message, 'error');
        }
    }

    // UI Update Methods (implement based on your framework)
    updateUI() {
        // Update your React/Vue/Angular components
        // Example: dispatch Redux action, emit event, etc.
    }

    updateProgressBar(percent) {
        // Update progress bar component
    }

    updateStatusText(phase, currentSymbol) {
        // Update status display
    }

    showNotification(title, message, type) {
        // Show toast/notification
    }

    clearProgressUI() {
        // Clear progress indicators
    }
}
```

## 2. UI Components to Add

### Processing Status Widget

```jsx
// React component example
const ProcessingStatus = () => {
    const [status, setStatus] = useState({
        isRunning: false,
        progress: 0,
        phase: '',
        estimatedCompletion: null
    });

    return (
        <div className="processing-status-widget">
            <h3>Daily Processing</h3>

            {status.isRunning ? (
                <>
                    <div className="progress-bar">
                        <div
                            className="progress-fill"
                            style={{width: `${status.progress}%`}}
                        />
                    </div>
                    <div className="status-text">
                        Phase: {status.phase} ({status.progress.toFixed(1)}%)
                    </div>
                    {status.estimatedCompletion && (
                        <div className="eta">
                            ETA: {new Date(status.estimatedCompletion).toLocaleTimeString()}
                        </div>
                    )}
                </>
            ) : (
                <div className="idle-status">
                    Next run: {/* Get from API */}
                </div>
            )}
        </div>
    );
};
```

### Schedule Control Panel (Admin)

```jsx
const ScheduleControl = () => {
    const [schedule, setSchedule] = useState(null);

    const triggerManual = async () => {
        try {
            const response = await fetch('/api/processing/daily/trigger', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-API-Key': API_KEY
                },
                body: JSON.stringify({ skip_market_check: false })
            });

            const data = await response.json();
            if (data.status === 'triggered') {
                showNotification('Processing triggered', 'success');
            }
        } catch (error) {
            showNotification('Failed to trigger processing', 'error');
        }
    };

    return (
        <div className="schedule-control">
            <h3>Processing Schedule</h3>
            <div>Status: {schedule?.enabled ? 'Enabled' : 'Disabled'}</div>
            <div>Trigger Time: {schedule?.trigger_time} ET</div>
            <div>Next Run: {schedule?.next_run}</div>

            <button onClick={triggerManual} className="btn-primary">
                Trigger Manual Run
            </button>
        </div>
    );
};
```

## 3. API Integration

### Fetch Processing Status

```javascript
async function getProcessingStatus() {
    try {
        const response = await fetch('/api/processing/daily/status');
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Failed to fetch processing status:', error);
        return null;
    }
}

// Poll status periodically when processing is active
let statusPoller = null;

function startStatusPolling() {
    statusPoller = setInterval(async () => {
        const status = await getProcessingStatus();
        if (status?.is_processing) {
            updateUIWithStatus(status);
        } else {
            stopStatusPolling();
        }
    }, 5000); // Poll every 5 seconds
}

function stopStatusPolling() {
    if (statusPoller) {
        clearInterval(statusPoller);
        statusPoller = null;
    }
}
```

### Get Processing History

```javascript
async function getProcessingHistory(days = 7) {
    try {
        const response = await fetch(`/api/processing/daily/history?days=${days}`);
        const data = await response.json();
        return data.history;
    } catch (error) {
        console.error('Failed to fetch processing history:', error);
        return [];
    }
}

// Display history in table
function displayHistory(history) {
    return history.map(run => ({
        date: new Date(run.run_date).toLocaleDateString(),
        status: run.status,
        duration: `${Math.round(run.processing_time_seconds / 60)} min`,
        processed: run.symbols_processed,
        failed: run.symbols_failed,
        trigger: run.trigger_type
    }));
}
```

## 4. Testing Your Integration

### Test Event Publisher

Create this test script to verify your integration:

```python
# test_processing_events.py
import redis
import json
from datetime import datetime, timedelta

r = redis.Redis(host='localhost', port=6379)

# Test events
events = [
    {
        'channel': 'tickstock:processing:status',
        'event': {
            'event': 'daily_processing_started',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'source': 'test',
            'version': '1.0',
            'payload': {
                'run_id': 'test-001',
                'symbols_count': 100,
                'trigger_type': 'manual'
            }
        }
    },
    {
        'channel': 'tickstock:processing:status',
        'event': {
            'event': 'daily_processing_progress',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'source': 'test',
            'version': '1.0',
            'payload': {
                'run_id': 'test-001',
                'phase': 'data_import',
                'symbols_completed': 50,
                'symbols_total': 100,
                'percent_complete': 50.0,
                'current_symbol': 'AAPL',
                'estimated_completion': (datetime.utcnow() + timedelta(minutes=10)).isoformat() + 'Z'
            }
        }
    },
    {
        'channel': 'tickstock:processing:status',
        'event': {
            'event': 'daily_processing_completed',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'source': 'test',
            'version': '1.0',
            'payload': {
                'run_id': 'test-001',
                'status': 'success',
                'duration_seconds': 600,
                'symbols_processed': 100,
                'symbols_failed': 0
            }
        }
    }
]

# Publish events with delays
import time
for item in events:
    r.publish(item['channel'], json.dumps(item['event']))
    print(f"Published: {item['event']['event']}")
    time.sleep(2)
```

### Verify Events in Browser Console

```javascript
// Add this to your browser console to monitor events
window.processingEvents = [];

// Assuming your event handler is accessible
eventHandler.on('processingEvent', (event) => {
    window.processingEvents.push(event);
    console.log('Processing Event:', event);
});

// Check captured events
console.table(window.processingEvents);
```

## 5. Error Handling

### Connection Recovery

```javascript
class RobustEventHandler extends ProcessingEventHandler {
    constructor(redisClient) {
        super(redisClient);
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
    }

    handleConnectionError(error) {
        console.error('Redis connection error:', error);

        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);

            setTimeout(() => {
                console.log(`Reconnection attempt ${this.reconnectAttempts}`);
                this.reconnect();
            }, delay);
        } else {
            this.showNotification(
                'Connection Lost',
                'Unable to connect to processing service',
                'error'
            );
        }
    }

    reconnect() {
        try {
            this.subscribe();
            this.reconnectAttempts = 0;
            this.showNotification('Reconnected', 'Connection restored', 'success');
        } catch (error) {
            this.handleConnectionError(error);
        }
    }
}
```

## 6. Performance Considerations

### Event Throttling

```javascript
// Throttle progress updates to prevent UI lag
const throttledProgressUpdate = _.throttle((payload) => {
    updateProgressBar(payload.percent_complete);
    updateStatusText(payload.phase, payload.current_symbol);
}, 500); // Update max every 500ms

// Use in event handler
onProcessingProgress(payload) {
    throttledProgressUpdate(payload);
}
```

### Memory Management

```javascript
// Clear old events periodically
const MAX_EVENT_HISTORY = 100;

class EventStore {
    constructor() {
        this.events = [];
    }

    addEvent(event) {
        this.events.push(event);

        // Keep only recent events
        if (this.events.length > MAX_EVENT_HISTORY) {
            this.events = this.events.slice(-MAX_EVENT_HISTORY);
        }
    }

    getRecentEvents(count = 10) {
        return this.events.slice(-count);
    }

    clear() {
        this.events = [];
    }
}
```

## 7. Monitoring Dashboard

### Metrics to Display

```javascript
const ProcessingMetrics = () => {
    const [metrics, setMetrics] = useState({
        todayRuns: 0,
        successRate: 100,
        avgDuration: 0,
        lastRun: null,
        nextRun: null
    });

    useEffect(() => {
        // Fetch and calculate metrics
        fetchMetrics();
    }, []);

    return (
        <div className="metrics-dashboard">
            <div className="metric-card">
                <span className="metric-value">{metrics.todayRuns}</span>
                <span className="metric-label">Today's Runs</span>
            </div>
            <div className="metric-card">
                <span className="metric-value">{metrics.successRate}%</span>
                <span className="metric-label">Success Rate</span>
            </div>
            <div className="metric-card">
                <span className="metric-value">{metrics.avgDuration} min</span>
                <span className="metric-label">Avg Duration</span>
            </div>
        </div>
    );
};
```

## 8. Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| No events received | Check Redis connection, verify channel names |
| Progress stuck | Check TickStockPL logs, verify processing is running |
| Missing notifications | Ensure event handlers are registered |
| Incorrect timezone | Events use UTC, convert for display |

### Debug Mode

```javascript
// Enable debug logging
const DEBUG = true;

if (DEBUG) {
    // Log all events
    redis.on('message', (channel, message) => {
        console.log(`[DEBUG] Channel: ${channel}`);
        console.log(`[DEBUG] Message:`, JSON.parse(message));
    });
}
```

## 9. Phase 1 Limitations

**Important**: Phase 1 provides the scheduling and monitoring infrastructure, but:

- Actual data import is placeholder (Phase 2)
- Indicator calculation not implemented (Phase 3)
- Pattern detection not implemented (Phase 4)
- Progress events show test data only

## 10. Support Resources

- Redis Protocol: `/docs/api/redis_protocol.md`
- API Documentation: `/docs/api/processing/phase1_app_integration.md`
- Test Scripts: `/tests/integration/processing/`
- Sample Events: Above test publisher script

## Questions?

Contact the TickStockPL team or check the Sprint 33 documentation for updates.