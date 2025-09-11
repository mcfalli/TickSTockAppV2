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

### 1.1 Core WebSocket Architecture Implementation

**Primary Focus**: Implement the Universal WebSocket Manager as defined in `docs/architecture/websocket-scalability-architecture.md`.

**Core Components**:
```python
src/core/services/websocket_subscription_manager.py    # Universal WebSocket orchestrator  
src/core/services/user_subscription_service.py        # User preference management
src/infrastructure/websocket/scalable_broadcaster.py  # Broadcasting infrastructure
src/infrastructure/websocket/room_manager.py          # Room/channel management
src/infrastructure/websocket/event_router.py          # Event filtering and routing
```

**Tier-Specific Integration**:
```python
src/core/services/tier_pattern_websocket_integration.py # Tier pattern WebSocket wrapper
src/core/domain/events/tier_pattern_events.py           # Tier-specific event models
```

**Features**:
- **Universal WebSocket Manager**: Core scalable architecture for all features
- **User-Specific Subscriptions**: Users subscribe only to their preferred tiers/patterns/symbols
- **Intelligent Event Filtering**: <5ms filtering to identify interested users per event
- **Batched Broadcasting**: 100ms batching window for efficient delivery
- **Connection Scaling**: Support for 500+ concurrent users in Phase 1

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
│  Real-time updates via Universal WebSocket Manager             │
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

## WebSocket Architecture Integration

### Event Processing Flow
1. **TickStockPL Redis Events** → `RedisEventSubscriber`
2. **Event Classification** → `TierPatternWebSocketIntegration`
3. **User Interest Filtering** → `UniversalWebSocketManager.find_interested_users()`
4. **Batched Broadcasting** → `ScalableBroadcaster.broadcast_to_users()`
5. **UI Updates** → Column-specific dashboard updates

### Core WebSocket Implementation
```python
# Phase 1 Sprint 25 - Implement core architecture
class TierPatternWebSocketIntegration:
    def __init__(self, websocket_manager: UniversalWebSocketManager):
        self.websocket = websocket_manager
        
    def subscribe_user_to_tier_patterns(self, user_id: str, preferences: Dict):
        """Subscribe user to tier-specific pattern events"""
        filters = {
            'pattern_types': preferences.get('pattern_types', []),
            'symbols': preferences.get('symbols', []),
            'tiers': preferences.get('tiers', ['daily', 'intraday', 'combo']),
            'confidence_min': preferences.get('confidence_min', 0.6)
        }
        
        return self.websocket.subscribe_user(user_id, 'tier_patterns', filters)
    
    def broadcast_tier_pattern_event(self, pattern_event: TierPatternEvent):
        """Broadcast tier pattern to interested users only"""
        targeting = {
            'subscription_type': 'tier_patterns',
            'pattern_type': pattern_event.pattern_type,
            'symbol': pattern_event.symbol,
            'tier': pattern_event.tier
        }
        
        return self.websocket.broadcast_event('tier_pattern', 
                                            pattern_event.to_dict(), 
                                            targeting)
```

### Performance Requirements  
- **Event Filtering**: <5ms to identify interested users per event
- **WebSocket Delivery**: <100ms from event generation to user browser
- **Dashboard Update Speed**: <50ms from WebSocket message to UI render
- **API Response Time**: <50ms for tier-specific queries
- **Concurrent Users**: Support 500+ users in Phase 1 implementation

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

### Week 1: Core WebSocket Architecture (CRITICAL FOUNDATION)
**🚨 PRIORITY ORDER - These components MUST be built in sequence:**

1. **Day 1**: Implement `UniversalWebSocketManager` core service
   - **CRITICAL**: This is the foundation everything else depends on
   - Must include user subscription management and room assignment
   - **Validation**: Basic WebSocket connection and user room management working

2. **Day 2**: Build `SubscriptionIndexManager` for efficient user filtering
   - **CRITICAL**: Required for <5ms event filtering target
   - Multi-dimensional indexing (pattern, symbol, tier, user)
   - **Validation**: Fast user lookup (<5ms) with 100+ test users

3. **Day 3**: Implement `ScalableBroadcaster` with batching and rate limiting
   - **CRITICAL**: Required for efficient delivery to hundreds of users
   - 100ms batching window, 100 events/sec rate limiting per user
   - **Validation**: Batched delivery working with performance metrics

4. **Day 4**: Create `EventRouter` for intelligent message routing
   - **CRITICAL**: Connects Redis events to user subscriptions
   - Targeting criteria matching and filtering logic
   - **Validation**: Events only reach intended users

5. **Day 5**: Build `TierPatternWebSocketIntegration` wrapper
   - Integration layer for tier-specific patterns
   - **Validation**: End-to-end message flow working
   - **Unit Tests**: 95%+ coverage for all core components

**⚠️ DEPENDENCY ALERT**: Days 2-5 cannot proceed without Day 1 completion

### Week 2: Dashboard UI & Integration  
1. **Day 1-2**: Build multi-tier dashboard layout with WebSocket client integration
2. **Day 3**: Implement tier-specific column components with real-time updates
3. **Day 4**: Add user subscription management UI (pattern/symbol preferences)
4. **Day 5**: Create tier-specific API endpoints
5. **Integration Tests**: End-to-end WebSocket flow testing

### Week 3: Performance Validation & Production Readiness (CRITICAL VALIDATION)
**🧪 COMPREHENSIVE TESTING - Sprint success depends on these validations:**

1. **Day 1**: Load testing with 500+ concurrent users (TARGET VALIDATION)
   - **CRITICAL**: Must demonstrate 500+ concurrent WebSocket connections
   - Performance validation: <5ms filtering, <100ms delivery
   - **Pass/Fail**: If targets not met, sprint cannot be considered complete

2. **Day 2**: Integration testing and Redis failover validation
   - **CRITICAL**: End-to-end TickStockPL → UI message flow validation
   - Redis connection failure and recovery testing
   - **Pass/Fail**: System must handle Redis outages gracefully

3. **Day 3**: Performance optimization and monitoring implementation
   - WebSocket performance metrics collection and dashboard
   - Memory usage optimization and leak prevention
   - **Validation**: System stable under sustained load for 4+ hours

4. **Day 4**: Error handling and graceful degradation testing
   - Connection drop scenarios and automatic reconnection
   - Partial system failure recovery testing
   - **Validation**: User experience remains acceptable during failures

5. **Day 5**: Production readiness validation and sprint handoff
   - Complete integration testing with all TickStockAppV2 components
   - **FINAL VALIDATION**: Ready for Sprint 26 to build upon
   - Sprint review with concrete performance demonstrations

**🚨 CRITICAL SUCCESS GATE**: Week 3 performance validation determines sprint success

## Success Criteria

- [ ] **Core WebSocket Architecture**: `UniversalWebSocketManager` operational for all future features
- [ ] **User-Specific Filtering**: Users receive only events matching their preferences
- [ ] **Multi-Tier Dashboard**: Three-column layout displaying patterns by tier
- [ ] **Real-Time Subscriptions**: Users can subscribe/unsubscribe to pattern types and symbols
- [ ] **Performance Targets**: <5ms event filtering, <100ms WebSocket delivery, <50ms API responses
- [ ] **Scalability Foundation**: Support 500+ concurrent users
- [ ] **Integration Ready**: Architecture ready for Sprints 26-30 feature integration

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