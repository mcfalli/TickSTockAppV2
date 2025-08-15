# TickStock Technical Documentation
---

## Version: 6.1
## Last Updated: January 2025
## Architecture: Component-Based with Pull Model Event Distribution
## Status: Production Ready with Sprint 29 Enhancements

---

## Overview
TickStock is a high-performance, real-time market data processing system that handles 4,000+ tickers with sub-millisecond processing times. The system uses a modular component architecture with **17 specialized components** plus dedicated WebSocket components, now featuring a **pull-based event distribution model** for zero event loss.

---

## High-Level Data Flow

Core_service.py – handle_websocket_tick()
↓
Event_processor.py - handle_tick() - process_tick_event()
↓
Event_detector.py – detect_events()
├── detect_highlow_events()
│   └── highlow_detector.py - detect_highlow()
├── detect_trend_events()
│   └── trend_detector.py - detect_trend()
└── detect_surge_events()
└── surge_detector.py - detect_surge()
↓
PriorityManager (event queue)
├── [tick events] → Workers → Processing only
└── [display events] → Workers → Convert to Dict → Display Queue
↓
DataPublisher (collect + buffer)
↓ (Pull Model)
WebSocketPublisher (pull + emit)


---

## Sprint 29: Pull Model Architecture

### Previous Push Model (37% Event Loss)

DataPublisher (timer) → collect → mark ready → push to WebSocketPublisher
↓ (unsynchronized)
WebSocketPublisher (maybe emitting)


### New Pull Model (Zero Event Loss)

DataPublisher → collect → buffer (up to 1000 events/type)
↑
WebSocketPublisher (timer) → pull → mark ready → emit to users


---

## Event Type Standardization

### Event Lifecycle:
1.  **Detection** → Typed Event (HighLowEvent, TrendEvent, SurgeEvent)
2.  **Priority Queue** → Typed Event
3.  **Worker Pool** → Typed Event
4.  **Worker Convert** → Dict (via `to_transport_dict()`) ← **TYPE BOUNDARY**
5.  **Display Queue** → Dict
6.  **DataPublisher** → Dict
7.  **Event Buffer** → Dict
8.  **WebSocketPublisher** → Dict
9.  **Frontend** → Dict

---

## Tracer Architecture

### Events Flow:
Detection → Queueing → Collection → Buffering → Emission
↓         ↓            ↓             ↓           ↓
Traces:  event_detected → event_queued → display_queue_collected → events_buffered → event_ready_for_emission
↓
event_emitted


---

## System Architecture

TickStock Application
├── Flask Application Layer
│   ├── Routes & API Endpoints (app_routes_*.py)
│   └── WebSocket Handlers (app.py with Socket.IO)
├── Market Data Service (CoreService Orchestrator)
│   ├── Core Processing Components (6)
│   ├── Event Processing Components (3)
│   ├── Universe Management Components (4)
│   └── Data Flow Components (4)
├── WebSocket Components (4)
│   ├── WebSocketPublisher (with emission timer)
│   ├── WebSocketUniverseCache
│   ├── WebSocketFilterCache
│   └── WebSocketDataFilter
└── Infrastructure Layer
├── Database (PostgreSQL)
├── Cache (Redis)
└── WebSocket (Socket.IO)


---

## Core Components

### EventProcessor
**Purpose**: Central event processing orchestration
**Key Methods**:
* `handle_tick(tick_data)` - Main entry point
* `_process_tick_event(queue_data)` - Core processing
* `_process_dual_universe(ticker, events, in_core, in_user)` - Universe filtering

### DataPublisher (Sprint 29 Enhanced)
**Purpose**: Event collection and buffering
**New Features**:
* Event buffer with overflow protection (1000 events/type)
* Pull interface: `get_buffered_events(clear_buffer=True)`
* No emission logic - only collection
* Buffer statistics tracking

**Key Methods**:
* `publish_to_users()` - Collects and buffers events
* `get_buffered_events()` - Pull interface for `WebSocketPublisher`
* `get_buffer_status()` - Monitor buffer health

### WebSocketPublisher (Sprint 29 Enhanced)
**Purpose**: Pull-based event emission
**New Features**:
* Independent emission timer
* Pulls from `DataPublisher` when ready
* Synchronous event marking and emission
* Per-user filtering after pull

**Key Methods**:
* `run_emission_cycle()` - Main pull/emit cycle
* `_mark_events_ready()` - Mark within emission cycle
* `set_data_publisher()` - Connect to data source

### Event Detection Components
* **EventDetector** - Orchestrates all detection
* **HighLowDetector** - Price extremes (0.1% threshold)
* **TrendDetector** - Trend analysis (180/360/600s windows)
* **SurgeDetector** - Volume surges (3x average)

### Queue Management
* **PriorityManager** - Priority-based queuing (P0-P4)
* **Display Queue** - Frontend-bound events (dict format)
* **WorkerPool** - Dynamic scaling (2-16 workers)
    * **NEW**: Converts typed events to dict before display queue

---

## Event Types

### Tick Events
* Internal processing only
* No display requirement
* **Examples**: VWAP calculations, state updates

### Display Events
* User-facing events requiring emission
* Converted to dict format at worker level
* **Examples**: High/Low alerts, Trend changes, Volume surges
* **Flow**: Process → Convert → Display Queue → Buffer → Pull → Emit

---

## Memory-First Architecture

```python
# All operations in memory
def record_event(ticker):
    # Step 1: Instant memory update (0.000ms)
    self.memory_handler.increment_count(ticker)

    # Step 2: Mark for database sync
    self.dirty_tickers.add(ticker)

    # Step 3: Database sync every 10-30 seconds
Benefits:
Sub-millisecond operations

500:1 database write reduction

Zero Flask context errors

Thread-safe operations

Zero event loss with pull model

Performance Characteristics
Tick Processing: < 1ms per tick

Event Detection: < 5ms per tick

Event Conversion: < 0.1ms per event

Buffer Operations: < 0.01ms

Pull Cycle: < 10ms for 1000 events

WebSocket Emission: < 5ms per user batch

Database Sync: 10-second intervals

Throughput: 499K operations/second validated

Configuration
Python

# Sprint 29 Pull Model Configuration
COLLECTION_INTERVAL = 0.5    # DataPublisher collection rate
EMISSION_INTERVAL = 1.0      # WebSocketPublisher emission rate
MAX_BUFFER_SIZE = 1000       # Per event type

# Publishing Configuration
UPDATE_INTERVAL = 0.5    # seconds
HEARTBEAT_INTERVAL = 2.0
EVENT_BUFFER_DURATION = 30
DISPLAY_QUEUE_BATCH_SIZE = 100
DISPLAY_QUEUE_COLLECTION_INTERVAL = 0.1    # 100ms

# Worker Configuration
WORKER_POOL_SIZE = 4
MIN_WORKERS = 2
MAX_WORKERS = 16
WORKER_SCALING_THRESHOLD = 100

# Event Detection
HIGH_LOW_THRESHOLD = 0.1    # 0.1% from session high/low
TREND_WINDOWS = [180, 360, 600]    # seconds
SURGE_MULTIPLIER = 3.0    # 3x average volume
Integration Patterns
Sprint 29 Connection
Python

# In core_service.py initialization
if self.websocket_publisher and self.data_publisher:
    self.websocket_publisher.set_data_publisher(self.data_publisher)
    logger.info("✅ SPRINT 29: Pull model enabled")
Direct Component Access
Python

# Direct access through parent
market_service.event_processor.handle_tick(tick_data)
market_service.data_publisher.get_buffer_status()
market_service.websocket_publisher.run_emission_cycle()
Result Objects
Python

@dataclass
class OperationResult:
    success: bool = True
    data: Optional[Any] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    processing_time_ms: float = 0
    operation_type: str = "unknown"
Tracer Points (Sprint 29 Updated)
event_detected - Event detectors (type, ticker, timestamp)

event_queued - PriorityManager (queue position, priority)

event_requeued_for_display - WorkerPool (after conversion)

display_queue_collected - DataPublisher (batch size)

events_buffered - DataPublisher (buffer size)

buffer_pulled - DataPublisher (events delivered)

emission_cycle_start - WebSocketPublisher (cycle begin)

event_ready_for_emission - WebSocketPublisher (within cycle)

event_emitted - WebSocketPublisher (user ID, count)

emission_cycle_complete - WebSocketPublisher (cycle end)

Error Handling
Component-level isolation

Buffer overflow protection

Graceful degradation

Automatic recovery with exponential backoff

Type conversion validation

Pull cycle error recovery

Monitoring & Validation
Key Metrics
Buffer Status: get_buffer_status() - sizes, overflows

Collection Efficiency: events collected vs queued

Emission Efficiency: events emitted vs ready

Pull Cycle Time: should be < emission interval

Type Conversion Success: dict conversion rate

Critical Validations
All event_ready_for_emission traces show in_emission_cycle: True

No events marked ready outside emission cycles

Buffer size remains bounded

Zero orphaned events

Technology Stack
Language: Python 3.8+

Web Framework: Flask with Flask-SocketIO

Real-time: WebSocket via Socket.IO

Database: PostgreSQL 13+

Cache: Redis 6+

Queue: In-memory with overflow protection

Event Buffer: Thread-safe with pull interface

Best Practices
Convert at boundaries - Typed → Dict at display queue

Pull don't push - WebSocketPublisher controls timing

Buffer with limits - Prevent memory overflow

Monitor pull cycles - Ensure timely emission

Validate conversions - Check dict format completeness

Single conversion point - Worker pool only

Troubleshooting
No Events Emitted
Check buffer status

Verify emission timer running

Confirm pull cycle executing

Monitor connected users

Missing Event Fields
Check to_transport_dict() implementation

Verify datetime imports

Validate dict conversion

Buffer Overflow
Increase MAX_BUFFER_SIZE

Reduce COLLECTION_INTERVAL

Increase EMISSION_INTERVAL

Check for emission blockage

High Latency
Monitor pull cycle duration

Check conversion performance

Review user filtering time

Verify emission batch sizes