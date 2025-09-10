# Sprint 25 - Phase 1: Tier-Specific Event Handling & Multi-Tier Dashboard

**Priority**: CRITICAL  
**Duration**: 2-3 weeks  
**Status**: Ready for Implementation

## Phase Objectives

Implement proper tier-specific event handling and create unified multi-tier dashboard for pattern visualization from TickStockPL's three-tier processing architecture.

## Architecture Overview

```
TickStockPL Three-Tier Output → TickStockAppV2 Consumer Dashboard
├─ Tier 1: Daily Processing → Daily Column Display
├─ Tier 2: Intraday Streaming → Intraday Column Display  
└─ Tier 3: Combo Engine → Combo Column Display
```

## Implementation Components

### 1.1 Tier-Specific Event Processing

**New Components**:
```python
src/core/services/tier_event_processor.py      # Main tier routing service
src/core/domain/events/tier_events.py          # Tier-specific event models
src/core/domain/events/daily_events.py         # Daily tier event handling
src/core/domain/events/intraday_events.py      # Intraday tier event handling
src/core/domain/events/combo_events.py         # Combo tier event handling
```

**Features**:
- Separate event handlers for each TickStockPL tier
- Tier-specific confidence thresholds and filtering logic
- WebSocket routing by tier for targeted UI updates
- Tier-based alert prioritization system

### 1.2 Multi-Tier Dashboard UI Component

**Frontend Components**:
```javascript
web/static/js/components/multi_tier_dashboard.js    # Main dashboard component
web/static/js/services/tier_pattern_service.js      # Tier-specific data service
web/static/js/components/daily_tier_column.js       # Daily patterns display
web/static/js/components/intraday_tier_column.js    # Intraday patterns display
web/static/js/components/combo_tier_column.js       # Combo patterns display
web/static/js/utils/tier_formatters.js              # Tier-specific formatting
```

**Dashboard Layout**:
```
┌─────────────────────────────────────────────────────────────────┐
│                  Multi-Tier Pattern Dashboard                  │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ Daily Tier  │  │Intraday Tier│  │ Combo Tier  │              │
│  │   Patterns  │  │   Patterns  │  │  Patterns   │              │
│  ├─────────────┤  ├─────────────┤  ├─────────────┤              │
│  │ Weekly BO   │  │ Vol Spike   │  │ Setup+Conf  │              │
│  │ Bull Flag   │  │ VWAP Break  │  │ Trend+Break │              │
│  │ Support     │  │ RSI Div     │  │ Daily+Entry │              │
│  │ [More...]   │  │ [More...]   │  │ [More...]   │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
│                                                                 │
│  Real-time updates via tier-specific WebSocket channels        │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 Backend API Enhancements

**New API Endpoints**:
```python
src/api/rest/tier_patterns.py                  # Tier-specific pattern APIs
```

**Endpoints**:
- `GET /api/patterns/daily` - Daily tier patterns with post-market context
- `GET /api/patterns/intraday` - Real-time intraday patterns
- `GET /api/patterns/combo` - Multi-timeframe combo patterns
- `GET /api/patterns/performance` - Performance metrics by tier
- `GET /api/patterns/tiers/health` - Tier-specific system health

## Technical Specifications

### Event Processing Flow
1. **TickStockPL Redis Events** → `RedisEventSubscriber`
2. **Event Classification** → `TierEventProcessor`
3. **Tier-Specific Handling** → Daily/Intraday/Combo handlers
4. **WebSocket Broadcasting** → Tier-specific channels
5. **UI Updates** → Column-specific dashboard updates

### Performance Requirements
- **Tier Routing Latency**: <10ms per event
- **Dashboard Update Speed**: <50ms from event to UI
- **API Response Time**: <50ms for tier-specific queries
- **WebSocket Delivery**: <100ms tier-specific broadcasting

### Data Flow Architecture
```python
# Tier-specific event models
@dataclass
class DailyTierEvent:
    pattern_type: str          # Weekly_Breakout, Bull_Flag, etc.
    timeframe: str = "daily"   # Always "daily"
    market_session: str        # "post_market", "pre_market"
    
@dataclass  
class IntradayTierEvent:
    pattern_type: str          # Volume_Spike, VWAP_Break, etc.
    timeframe: str            # "1min", "5min", "15min"
    real_time: bool = True    # Always True for intraday
    
@dataclass
class ComboTierEvent:
    pattern_type: str          # Setup_Confirmation, Trend_Break, etc.
    daily_context: Dict       # Daily setup information
    intraday_trigger: Dict    # Intraday confirmation trigger
    correlation_strength: float # Multi-timeframe correlation score
```

## User Experience Features

### Dashboard Interaction
- **Column Filtering**: Independent filters for each tier
- **Cross-Tier Highlighting**: Related patterns across tiers
- **Tier Performance Metrics**: Success rates and timing by tier
- **Real-Time Status**: Connection status per tier

### Visual Design Elements
- **Color Coding**: Distinct colors for each tier (Blue/Green/Orange)
- **Pattern Icons**: Tier-specific iconography
- **Confidence Indicators**: Visual confidence scoring per tier
- **Time Stamps**: Tier-appropriate time formatting

## Implementation Steps

### Week 1: Backend Event Processing
1. Create `TierEventProcessor` service
2. Implement tier-specific event models
3. Add tier routing logic to `RedisEventSubscriber`
4. Create tier-specific API endpoints
5. Unit tests for event classification

### Week 2: Frontend Dashboard Components
1. Build multi-tier dashboard layout
2. Implement tier-specific column components
3. Add tier-specific WebSocket handling
4. Create tier formatting utilities
5. Integration testing with backend APIs

### Week 3: Integration & Performance
1. End-to-end tier event flow testing
2. Performance optimization and monitoring
3. UI polish and responsive design
4. Documentation and deployment preparation

## Success Criteria

- [ ] **Tier Event Classification**: 100% accurate routing of TickStockPL events by tier
- [ ] **Multi-Tier Dashboard**: Three-column layout displaying patterns by tier
- [ ] **Real-Time Updates**: WebSocket-driven updates specific to each tier
- [ ] **Performance Targets**: <50ms API responses, <100ms WebSocket delivery
- [ ] **Visual Distinction**: Clear differentiation between tier types in UI
- [ ] **Cross-Tier Integration**: Related patterns highlighted across tiers

## Testing Strategy

### Unit Tests
- Event classification accuracy
- Tier-specific data transformations
- API endpoint functionality

### Integration Tests  
- End-to-end event flow from Redis to UI
- WebSocket broadcasting by tier
- Dashboard component interactions

### Performance Tests
- Event processing latency by volume
- Dashboard rendering with multiple tiers
- WebSocket scalability testing

## Dependencies

### Internal
- `RedisEventSubscriber` - Enhanced for tier routing
- `RedisPatternCache` - Tier-specific caching
- `PatternDiscoveryService` - Tier coordination

### External
- TickStockPL Redis pub-sub channels operational
- WebSocket infrastructure for real-time updates
- Frontend framework for dashboard components

## Risk Mitigation

### Technical Risks
- **Tier Classification Accuracy**: Comprehensive testing with TickStockPL event samples
- **Performance Impact**: Load testing with high-frequency events
- **UI Complexity**: Phased rollout with user feedback

### Integration Risks
- **TickStockPL Compatibility**: Validate event formats before implementation
- **WebSocket Scalability**: Test concurrent user scenarios
- **Browser Performance**: Optimize dashboard rendering for multiple data streams

This phase establishes the foundation for all subsequent consumer-side enhancements by properly organizing and displaying TickStockPL's three-tier processing output.