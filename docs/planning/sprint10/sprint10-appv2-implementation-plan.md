# Sprint 10 TickStockAppV2 Implementation Plan

**Document**: Sprint 10 TickStockAppV2 UI Integration Plan  
**Status**: Ready for Implementation  
**Last Updated**: 2025-08-27  
**Prerequisites**: TickStockPL Phase 3 Complete (Database + Backtesting Framework Ready)

---

## 🎯 Sprint 10 Overview for TickStockAppV2

**Objective**: Transform TickStockAppV2 into the user interface layer that consumes TickStockPL's completed backend services while maintaining its lean ~11,000 line architecture.

**Core Philosophy**: UI-focused event consumer that triggers jobs and displays results. No heavy data processing - purely consumption and visualization.

---

## 🔧 Prerequisites (Already Complete in TickStockPL)

### TickStockPL Ready Services
- ✅ **Database "tickstock"**: TimescaleDB with `symbols`, `ohlcv_daily`, `ohlcv_1min`, `ticks`, `events` tables
- ✅ **Backtesting Framework**: Complete with 11+ patterns, institutional-grade metrics including win rate, ROI, Sharpe ratio, max drawdown, and expectancy ratio, plus realistic trade simulation
- ✅ **Data Loading Pipeline**: Multi-provider (Polygon/Alpha Vantage) with multi-year historical datasets (see [`get_historical_data.md`](../get_historical_data.md) for seeding details)
- ✅ **Redis Architecture**: Ready for pub-sub communication with TickStockAppV2

### Database Connection Details
- **Database Name**: `tickstock` (single shared database)
- **Connection**: TimescaleDB-enabled PostgreSQL on port 5432 (or configured via environment)
- **TickStockAppV2 Role**: Read-only access for UI queries only
- **Schema**: Ready-to-use tables with TimescaleDB optimization (see [`database_architecture.md`](../database_architecture.md))

---

## 📋 Sprint 10 Implementation Plan - TickStockAppV2

### Phase 1: Database Integration & Health Monitoring (Days 1-3)
**Goal**: Connect TickStockAppV2 to shared "tickstock" database with read-only access

**Tasks**:
1. **Database Connection Setup**
   - Configure TimescaleDB connection to existing "tickstock" database
   - Implement read-only connection pool for UI queries
   - Add connection health monitoring

   ```python
   # Example: Database connection setup in AppV2
   from sqlalchemy import create_engine
   import os
   
   # Read-only database connection for UI queries
   DB_URL = f"postgresql://readonly_user:{os.getenv('DB_PASSWORD')}@localhost:5432/tickstock"
   engine = create_engine(DB_URL, pool_size=5, echo=False)
   
   def get_symbols_for_dropdown():
       """Simple query for UI dropdown population"""
       with engine.connect() as conn:
           result = conn.execute("SELECT symbol FROM symbols ORDER BY symbol")
           return [row[0] for row in result]
   ```

2. **UI Data Queries**
   - Simple queries for dropdown population: `SELECT symbol FROM symbols`
   - Basic stats for dashboard: `SELECT COUNT(*) FROM events`
   - User alert history: `SELECT * FROM events WHERE user_id = ?`

3. **Health Monitoring Dashboard**
   - Display TickStockPL service connectivity status
   - Show Redis connection health
   - Basic database metrics (table row counts, last update times)

**Deliverables**:
- Database connection configuration
- Health monitoring UI component
- Basic dashboard with system status

### Phase 2: Enhanced Redis Event Consumption (Days 4-5)
**Goal**: Upgrade TickStockAppV2 to consume TickStockPL's event streams

**Tasks**:
1. **Redis Subscriber Enhancement**
   - Subscribe to `tickstock.events.patterns` (pattern detections from TickStockPL)
   - Subscribe to `tickstock.events.backtesting.progress` (backtest updates)
   - Subscribe to `tickstock.events.backtesting.results` (completed backtests)

   ```python
   # Example: Redis subscriber for TickStockPL events in AppV2
   import redis
   import json
   from flask_socketio import emit
   
   redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
   pubsub = redis_client.pubsub()
   
   # Subscribe to TickStockPL event channels
   pubsub.subscribe([
       'tickstock.events.patterns',
       'tickstock.events.backtesting.progress', 
       'tickstock.events.backtesting.results'
   ])
   
   def listen_to_tickstockpl_events():
       """Background thread listening to TickStockPL events"""
       for message in pubsub.listen():
           if message['type'] == 'message':
               channel = message['channel']
               data = json.loads(message['data'])
               
               if channel == 'tickstock.events.patterns':
                   # Forward pattern alerts to WebSocket clients
                   emit('pattern_alert', data, broadcast=True)
               elif 'backtesting' in channel:
                   # Forward backtest updates to interested clients
                   emit('backtest_update', data, broadcast=True)
   ```

2. **WebSocket Event Broadcasting**
   - Forward TickStockPL pattern events to browser clients via WebSocket
   - Real-time backtest progress updates to UI
   - User notification system for pattern alerts

3. **Event Processing Logic**
   - Simple event filtering based on user subscriptions
   - Message queuing for offline users (using Redis Streams for persistence and scaling)
   - Basic event logging to database
   
   *Note: Redis Streams provide persistent message queuing that aligns with scaling requirements in [`tickstockpl-integration-guide.md`](../tickstockpl-integration-guide.md)*

**Deliverables**:
- Enhanced Redis subscribers
- WebSocket event broadcasting
- Real-time notification system

### Phase 3: Backtesting UI & Job Management (Days 6-8)
**Goal**: Create UI for triggering TickStockPL backtests and displaying results

**Tasks**:
1. **Backtesting Configuration Interface**
   - Form for backtest parameters (symbols, date ranges, patterns to test)
   - Submit backtest jobs to TickStockPL via Redis: `tickstock.jobs.backtest`
   - Progress tracking display with real-time WebSocket updates

2. **Results Visualization**
   - Display TickStockPL-computed metrics (win rate, ROI, Sharpe ratio)
   - Charts/graphs for equity curves using TickStockPL data
   - Export/download functionality for backtest results

3. **Job Management**
   - View active/completed backtests
   - Cancel running backtests (via Redis job status management)
   - Backtest history and comparison tools
   
   *Note: Job cancellation requires Redis-based coordination with TickStockPL for graceful termination*

**Deliverables**:
- Backtesting configuration forms
- Results visualization dashboard
- Job management interface

### Phase 4: Pattern Alert System (Days 9-10)
**Goal**: UI for managing pattern subscriptions and displaying real-time alerts

**Tasks**:
1. **User Alert Preferences**
   - UI for selecting which of the 11+ patterns to subscribe to (see [`user_stories.md`](../user_stories.md) Story 1 for alert details)
   - Notification settings (in-app, email preferences)
   - Alert threshold configuration (confidence levels)
   
   *Cross-reference: Pattern details available in [`patterns_library_patterns.md`](../patterns_library_patterns.md)*

2. **Real-Time Pattern Notifications**
   - WebSocket delivery of TickStockPL pattern events to subscribed users
   - In-browser notifications for detected patterns
   - Alert history and management (mark read, archive)

3. **Pattern Performance Display**
   - Query TickStockPL-generated pattern performance from `events` table
   - Simple charts showing pattern success rates
   - Pattern comparison tools

**Deliverables**:
- User alert preference interface
- Real-time notification system
- Pattern performance dashboard

---

## 🏗️ Technical Architecture - AppV2 Integration

### Redis Communication (AppV2 as Consumer)
```
TickStockPL → Redis → TickStockAppV2
- tickstock.events.patterns (consume pattern alerts)
- tickstock.events.backtesting.progress (consume backtest updates)
- tickstock.events.backtesting.results (consume completed backtests)

TickStockAppV2 → Redis → TickStockPL  
- tickstock.jobs.backtest (publish job requests)
- tickstock.jobs.alerts (publish alert subscriptions)
```

### Database Access (AppV2 Read-Only)
```
TickStockAppV2 Simple Queries (Read-Only):
- SELECT symbol FROM symbols (UI dropdown population)
- SELECT COUNT(*) FROM events (dashboard statistics)
- SELECT * FROM events WHERE user_id = ? (user alert history)
- SELECT * FROM events WHERE pattern = ? (pattern performance)

TickStockPL Owns: All writes, schema management, complex analytics
```

### WebSocket Architecture
```
Redis Events → TickStockAppV2 Subscriber → WebSocket Publisher → Browser
- Pattern alerts: Real-time notifications to subscribed users
- Backtest progress: Live updates during backtesting
- System health: Connection status and performance metrics
```

---

## 📊 Success Metrics - UI-Focused

### Technical Targets
- **UI Responsiveness**: <200ms for form submissions and page loads
- **WebSocket Delivery**: <100ms from Redis event to browser notification  
- **Database Queries**: <50ms for simple read-only queries
- **Job Submission**: <500ms to queue backtest job to TickStockPL

### User Experience Metrics
- **Real-Time Alerts**: Instant delivery of pattern notifications
- **Backtest Workflow**: Seamless job submission and progress tracking
- **System Monitoring**: Clear visibility into TickStockPL service health
- **Data Visualization**: Clear display of TickStockPL-computed results

### Architecture Preservation
- **Code Size**: Maintain ~11,000 lines (no bloat from processing logic)
- **Loose Coupling**: All communication via Redis pub-sub (no direct calls)
- **Clear Boundaries**: Zero overlap with TickStockPL functionality

---

## 🚫 Explicitly NOT Included (TickStockPL Territory)

**Removed from Original Plan**:
- ❌ Schema creation and database models implementation
- ❌ StandardOHLCV implementation and data conversion
- ❌ Multi-provider integration logic 
- ❌ Pattern detection algorithm integration
- ❌ Backtesting engine implementation
- ❌ Historical pattern analysis and performance tracking
- ❌ Data loading and preprocessing logic

**Why Removed**: These belong in TickStockPL to maintain separation of concerns and prevent re-bloating the cleaned AppV2 codebase.

---

## ⏱️ Implementation Timeline

### Week 1: Foundation
**Days 1-3**: Database Connection & Health Monitoring
- Connect to shared "tickstock" database (read-only)
- Build health monitoring dashboard
- Basic UI queries for symbols and stats

**Days 4-5**: Redis Event Consumption  
- Enhanced Redis subscribers for TickStockPL events
- WebSocket broadcasting to browser clients
- Real-time notification system
- Buffer for integration testing
- **Testing**: End-of-phase pytest for Redis integration (targeting 80% coverage per [`project-overview.md`](../project-overview.md))

### Week 2: User Interface
**Days 6-8**: Backtesting UI & Job Management
- Backtest configuration forms
- Results visualization dashboard  
- Job management interface
- Buffer for UI polish and testing
- **Testing**: End-of-phase pytest for UI components and job management

**Days 9-10**: Pattern Alert System
- Alert preference management
- Real-time pattern notifications
- Pattern performance display
- **Testing**: Final pytest suite ensuring 80% overall coverage for Sprint 10 components

## 🔧 Pre-Sprint 10 Setup: Minimal Pydantic v2 Integration

### **Redis Message Models (2-3 Days Before Sprint 10)**

**Goal**: Implement type-safe Redis communication models for TickStockPL integration without disrupting existing architecture.

**Approach**: Create ONLY the essential Pydantic models for Redis pub-sub messages, leaving existing dataclasses untouched.

#### **Implementation Tasks**

**Day 1-2: Core Redis Message Models**

Create `src/shared/models/redis_messages.py`:

```python
from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, Any, Optional, List, Literal
from datetime import datetime
import time

class TickStockRedisMessage(BaseModel):
    """Base Redis message model for TickStock.ai pub-sub"""
    model_config = ConfigDict(
        validate_assignment=True,
        use_enum_values=True,
        extra='forbid',
        str_strip_whitespace=True
    )
    
    timestamp: float = Field(default_factory=time.time)
    source: str = Field(..., description="Message source")

class PatternEventMessage(TickStockRedisMessage):
    """Pattern detection event: TickStockPL → TickStockApp"""
    event_type: Literal["pattern_detected"] = "pattern_detected"
    pattern: str = Field(..., min_length=1, description="Pattern name (Doji, Hammer, etc.)")
    symbol: str = Field(..., pattern=r'^[A-Z]+$', description="Stock symbol")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence")
    timeframe: str = Field(default="1min", pattern=r'^(1min|5min|15min|1h|1d)$')
    direction: Optional[Literal["bullish", "bearish", "reversal"]] = None
    price: float = Field(..., gt=0, description="Price when pattern detected")
    metadata: Dict[str, Any] = Field(default_factory=dict)

class BacktestJobMessage(TickStockRedisMessage):
    """Backtest job request: TickStockApp → TickStockPL"""
    job_type: Literal["backtest"] = "backtest"
    job_id: str = Field(..., min_length=1, description="Unique job identifier")
    user_id: str = Field(..., min_length=1, description="Requesting user ID")
    symbols: List[str] = Field(..., min_items=1, max_items=50, description="Symbols to backtest")
    start_date: str = Field(..., pattern=r'^\d{4}-\d{2}-\d{2}$', description="Start date YYYY-MM-DD")
    end_date: str = Field(..., pattern=r'^\d{4}-\d{2}-\d{2}$', description="End date YYYY-MM-DD")
    patterns: List[str] = Field(..., min_items=1, description="Patterns to test")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Backtest parameters")

class BacktestProgressMessage(TickStockRedisMessage):
    """Backtest progress update: TickStockPL → TickStockApp"""
    job_id: str = Field(..., min_length=1)
    progress: float = Field(..., ge=0.0, le=1.0, description="Progress 0.0-1.0")
    status: Literal["queued", "running", "completed", "failed", "cancelled"]
    current_symbol: Optional[str] = Field(None, description="Currently processing symbol")
    estimated_completion: Optional[float] = Field(None, description="Unix timestamp")
    message: str = Field(default="", description="Status message")

class BacktestResultMessage(TickStockRedisMessage):
    """Backtest results: TickStockPL → TickStockApp"""
    job_id: str = Field(..., min_length=1)
    status: Literal["completed", "failed"] = "completed"
    results: Optional[Dict[str, float]] = Field(None, description="win_rate, roi, sharpe_ratio, max_drawdown")
    error_message: Optional[str] = Field(None, description="Error details if failed")
    completed_at: float = Field(default_factory=time.time)
```

**Day 2-3: Redis Serialization Utils**

Create `src/shared/utils/redis_serializer.py`:

```python
import json
import logging
from typing import Type, TypeVar, Union
from pydantic import ValidationError
from .models.redis_messages import TickStockRedisMessage

T = TypeVar('T', bound=TickStockRedisMessage)
logger = logging.getLogger(__name__)

class RedisMessageSerializer:
    """High-performance Redis message serialization with Pydantic v2"""
    
    @staticmethod
    def serialize(message: TickStockRedisMessage) -> str:
        """Serialize Pydantic message to JSON string for Redis"""
        try:
            return message.model_dump_json()  # Pydantic v2 optimized JSON
        except Exception as e:
            logger.error(f"Failed to serialize {type(message).__name__}: {e}")
            raise
    
    @staticmethod
    def deserialize(data: Union[str, bytes], message_class: Type[T]) -> T:
        """Deserialize Redis data to Pydantic message"""
        try:
            if isinstance(data, bytes):
                data = data.decode('utf-8')
            
            json_data = json.loads(data) if isinstance(data, str) else data
            return message_class.model_validate(json_data)
            
        except (json.JSONDecodeError, ValidationError) as e:
            logger.error(f"Failed to deserialize {message_class.__name__}: {e}")
            logger.error(f"Raw data: {data}")
            raise

# Usage examples for Sprint 10 integration
class RedisPatternPublisher:
    """Example publisher using Pydantic messages"""
    def __init__(self, redis_client):
        self.redis = redis_client
        self.serializer = RedisMessageSerializer()
    
    def publish_pattern_event(self, symbol: str, pattern: str, confidence: float, price: float):
        message = PatternEventMessage(
            source="tickstock_pl",
            symbol=symbol,
            pattern=pattern,
            confidence=confidence,
            price=price
        )
        data = self.serializer.serialize(message)
        self.redis.publish('tickstock.events.patterns', data)

class RedisPatternSubscriber:
    """Example subscriber using Pydantic messages"""
    def __init__(self, redis_client):
        self.redis = redis_client
        self.serializer = RedisMessageSerializer()
    
    def handle_pattern_event(self, raw_data: bytes):
        try:
            message = self.serializer.deserialize(raw_data, PatternEventMessage)
            # Type-safe access to validated data
            print(f"Pattern {message.pattern} detected for {message.symbol} "
                  f"with {message.confidence:.2f} confidence")
        except Exception as e:
            logger.error(f"Failed to handle pattern event: {e}")
```

#### **Integration Benefits for Sprint 10**

1. **Type Safety**: All Redis messages have strict validation
2. **IDE Support**: Full autocomplete and type hints
3. **Error Prevention**: Invalid messages caught at creation time
4. **Documentation**: Self-documenting message contracts
5. **Performance**: Pydantic v2's optimized serialization

#### **Usage in Sprint 10 Phases**

- **Phase 2**: Use `PatternEventMessage` for Redis event consumption
- **Phase 3**: Use `BacktestJobMessage` and `BacktestProgressMessage` for job management
- **Phase 4**: Use validated pattern messages for alert system

#### **Migration Strategy**

- Keep existing `TickData`, `OHLCVData` models unchanged
- Use Pydantic models ONLY for Redis communication
- Adapt existing Redis publishers/subscribers to use new serialization
- Full Pydantic migration planned for post-Sprint 10 (see `pydantic_implementation.md`)

---

## 🎯 Expected Outcome

**Transformed TickStockAppV2**:
- Clean UI layer consuming TickStockPL's powerful backend services
- Real-time pattern alerts and backtesting results
- User-friendly interface for institutional-grade trading analytics
- Maintained lean architecture with clear separation of concerns

**Integration Success**:
- Seamless communication between TickStockPL (producer) and TickStockAppV2 (consumer)
- Real-time user experience with sub-second responsiveness
- Professional trading platform with institutional backtesting capabilities
- Scalable architecture ready for production deployment

---

**Document Status**: Ready for Sprint 10 TickStockAppV2 Implementation  
**Next Action**: Begin Phase 1 implementation with database connection setup