# Documentation Warning
**DISCLAIMER**: This documentation is not current and should not be relied upon. As of August 21, 2025, it requires review to determine its relevance. Content must be evaluated for accuracy and applicability to the project. If found relevant, update and retain; if obsolete or duplicative of content elsewhere, delete.



Architecture Overview
System Design
TickStock is built on a component-based architecture with 17 specialized core components plus 4 dedicated WebSocket components that work together to process real-time market data. The system follows event-driven patterns with a new pull-based event distribution model for zero event loss and a display queue separation for optimized event processing and delivery.

Key Design Principles
Single Responsibility - Each component has one clear purpose

Dependency Injection - Flexible, testable component wiring

Memory-First Processing - Sub-millisecond operations

Event-Driven Architecture - Asynchronous, scalable design

Per-User Isolation - Complete data segregation

Display Queue Separation - Decoupled processing from emission (specifically for display events)

Pull Model Event Distribution - WebSocketPublisher controls data flow from DataPublisher to ensure zero event loss.

Component Categories
Core Processing Components (6)
The heart of the data processing pipeline:

EventProcessor - Orchestrates all tick processing

DataPublisher - Collects from Display Queue and buffers; provides pull interface.

UniverseCoordinator - Handles universe filtering

AnalyticsCoordinator - Manages analytics and persistence

WorkerPoolManager - Controls parallel processing and converts typed events to dictionaries for display.

HealthMonitor - System health and monitoring

Event Processing Components (3)
Specialized event detection and management:

TickProcessor - Validates and enriches tick data (Implicit in Event_processor.py - handle_tick())

EventDetector - Identifies market events with sub-detectors:

HighLowDetector - Price extremes (0.1% threshold)

TrendDetector - Trend analysis (180/360/600s windows)

SurgeDetector - Volume surges (3x average)

PriorityManager - Routes events: tick events (process only) vs display events (process + queue)

Universe Management Components (4)
User preferences and filtering:

UserUniverseManager - Per-user universe selections (~800 stocks)

CoreUniverseManager - System-wide core universe (~2,800 stocks)

SubscriptionManager - WebSocket subscription tracking

UniverseAnalytics - Coverage and efficiency metrics

Data Flow Components (4)
Supporting infrastructure:

SessionManager - Market session tracking

MetricsCollector - System-wide metrics aggregation

PerformanceMonitor - Performance tracking and alerting

WebSocket Components (4)
Dedicated WebSocket handling:

WebSocketPublisher - Pull-based per-user data emission with an independent emission timer.

WebSocketUniverseCache - LRU cache (1-hour TTL)

WebSocketFilterCache - User filter preferences

WebSocketDataFilter - Applies filtering logic (Per-user filtering after pull)

Data Flow Overview
1. Data Ingestion
    WebSocket → CoreService → EventProcessor

2. Event Detection
    EventDetector → HighLow/Trend/Surge Detectors → Typed Events

3. Queue Management
    PriorityManager:
    ├── [tick events] → Workers → Processing only
    └── [display events] → Workers → Convert to Dict → Display Queue

4. Display Queue Collection & Buffering
    Display Queue → DataPublisher (collect + buffer)

5. User Distribution (Pull Model)
    WebSocketPublisher (timer) → pull from DataPublisher → emit to users
Tracer Architecture
Detection → Queueing → Collection → Buffering → Emission
    ↓         ↓            ↓             ↓           ↓
event_detected → event_queued → display_queue_collected → events_buffered → event_ready_for_emission
                                                                                                ↓
                                                                                        event_emitted
Key Architectural Patterns
Memory-First Architecture
All operations performed in memory

Periodic database synchronization (10-second intervals)

500:1 database write reduction

Sub-millisecond processing times

Display Queue Pattern
Separation of Concerns: Processing decoupled from display

Batch Efficiency: Events collected (by DataPublisher)

Improved Throughput: Workers don't block on emission

Better Debugging: Clear trace points

Dual Universe System
Core Universe: ~2,800 stocks for market-wide analytics

User Universe: ~800 stocks for personalized display

Independent processing pipelines

Efficient filtering at emission time

Per-User Data Streams
Authenticated WebSocket connections

Individual universe filtering

Personal filter preferences

Event buffering (up to 1000 events/type for display events)

Worker Pool Architecture
Dynamic scaling (2-16 workers)

Priority-based queue management (P0-P4)

Separate handling for tick vs display events

NEW: Converts typed events to dict before display queue

Load-based auto-scaling

Performance Characteristics
Operation	Target	Typical
Tick Processing	< 1ms	0.5ms
Event Detection	< 5ms	2-3ms
Pull Cycle	< 10ms	5-8ms
WebSocket Emission	< 5ms per user batch	2-4ms
Database Sync	10s interval	10s
End-to-End Latency	< 100ms	50-80ms
Throughput	-	499K operations/second validated

Export to Sheets
Technology Stack
Language: Python 3.8+

Web Framework: Flask + Flask-SocketIO

Real-time: WebSocket via Socket.IO

Database: PostgreSQL 13+

Cache: Redis 6+

Message Format: JSON

Queue: In-memory with Display Queue separation

Deployment: Docker containers

Recent Updates (v6.1 - Sprint 29 Enhancements)
Pull Model Architecture: Shift from push to pull for zero event loss.

DataPublisher Enhancements: Now includes event buffering and a pull interface.

WebSocketPublisher Enhancements: Features an independent emission timer and pulls data when ready.

Worker Pool Conversion: Workers now handle the conversion of typed events to dictionaries for display.

Tracer Points: Updated with events_buffered and buffer_pulled for detailed pull model tracing.

