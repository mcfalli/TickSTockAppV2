# WebSocket Scalability Architecture - TickStockAppV2

**Date**: 2025-09-10  
**Status**: Implementation Ready  
**Scope**: Core real-time communication infrastructure for hundreds to thousands of users

## Architecture Overview

TickStockAppV2 implements a scalable WebSocket architecture using **user-specific room-based subscriptions** with **intelligent event filtering**. This is the industry-standard approach used by professional trading platforms (Bloomberg, Refinitiv) and retail platforms (Robinhood, Webull) for serving hundreds to thousands of concurrent users.

### Core Architecture Principles
- **User-Specific Subscriptions**: Each user subscribes only to data they care about
- **Room-Based Broadcasting**: Users join rooms based on their interests (patterns, symbols, tiers)
- **Intelligent Filtering**: Events only sent to users who match filtering criteria
- **Efficient Batching**: Multiple events batched together to reduce WebSocket overhead
- **Connection Scaling**: Horizontal scaling through connection pooling and load distribution

## System Components

### Core WebSocket Management Services
```python
src/core/services/websocket_subscription_manager.py    # Main WebSocket orchestrator
src/core/services/user_subscription_service.py        # User preference management  
src/infrastructure/websocket/scalable_broadcaster.py  # Broadcasting infrastructure
src/infrastructure/websocket/room_manager.py          # Room/channel management
src/infrastructure/websocket/event_router.py          # Event filtering and routing
src/infrastructure/websocket/connection_pool_manager.py # Connection scaling
```

## Universal WebSocket Manager

### Core Implementation
```python
@dataclass
class UserSubscription:
    """User subscription configuration for any feature"""
    user_id: str
    subscription_type: str      # 'tier_patterns', 'market_insights', 'alerts'
    filters: Dict[str, Any]     # Feature-specific filtering criteria
    room_name: str              # WebSocket room assignment
    active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)

class UniversalWebSocketManager:
    """
    Core WebSocket manager used by all TickStockAppV2 features.
    Implements industry-standard scalable real-time communication.
    """
    
    def __init__(self, socketio: SocketIO, redis_client):
        self.socketio = socketio
        self.redis_client = redis_client
        
        # Subscription management
        self.user_subscriptions: Dict[str, Dict[str, UserSubscription]] = defaultdict(dict)
        self.subscription_indexes: Dict[str, Dict[str, Set[str]]] = defaultdict(lambda: defaultdict(set))
        
        # Room management  
        self.room_manager = RoomManager()
        self.connection_pools = ConnectionPoolManager()
        
        # Event routing
        self.event_router = EventRouter()
        self.broadcaster = ScalableBroadcaster(socketio)
        
        # Performance tracking
        self.metrics = WebSocketMetrics()
        
    def subscribe_user(self, user_id: str, subscription_type: str, 
                      filters: Dict[str, Any]) -> bool:
        """
        Universal user subscription method used by all features.
        
        Args:
            user_id: Unique user identifier
            subscription_type: Feature type ('tier_patterns', 'market_insights', etc.)
            filters: Feature-specific filtering criteria
            
        Returns:
            True if subscription successful
        """
        try:
            # Create subscription
            room_name = f"user_{user_id}"
            subscription = UserSubscription(
                user_id=user_id,
                subscription_type=subscription_type,
                filters=filters,
                room_name=room_name
            )
            
            # Store subscription
            self.user_subscriptions[user_id][subscription_type] = subscription
            
            # Update indexes for fast filtering
            self._update_subscription_indexes(subscription)
            
            # Ensure user room exists
            self.room_manager.ensure_user_room(user_id, room_name)
            
            # Track metrics
            self.metrics.record_subscription(subscription_type)
            
            logger.info(f"WEBSOCKET: User {user_id} subscribed to {subscription_type}")
            return True
            
        except Exception as e:
            logger.error(f"WEBSOCKET: Subscription error for {user_id}: {e}")
            return False
    
    def unsubscribe_user(self, user_id: str, subscription_type: str = None) -> bool:
        """Remove user subscriptions (specific type or all)"""
        try:
            if subscription_type:
                # Remove specific subscription
                if subscription_type in self.user_subscriptions[user_id]:
                    subscription = self.user_subscriptions[user_id][subscription_type]
                    self._remove_from_indexes(subscription)
                    del self.user_subscriptions[user_id][subscription_type]
            else:
                # Remove all subscriptions for user
                for sub_type, subscription in self.user_subscriptions[user_id].items():
                    self._remove_from_indexes(subscription)
                self.user_subscriptions[user_id].clear()
                self.room_manager.remove_user_room(user_id)
                
            return True
            
        except Exception as e:
            logger.error(f"WEBSOCKET: Unsubscription error for {user_id}: {e}")
            return False
    
    def broadcast_event(self, event_type: str, event_data: Dict[str, Any], 
                       targeting_criteria: Dict[str, Any] = None) -> int:
        """
        Universal event broadcasting method used by all features.
        
        Args:
            event_type: Type of event being broadcast
            event_data: Event payload
            targeting_criteria: Filtering criteria to target specific users
            
        Returns:
            Number of users event was sent to
        """
        try:
            start_time = time.time()
            
            # Find users interested in this event
            interested_users = self._find_interested_users(event_type, targeting_criteria)
            
            if not interested_users:
                logger.debug(f"WEBSOCKET: No users interested in {event_type}")
                return 0
            
            # Batch and broadcast to interested users
            delivery_count = self.broadcaster.broadcast_to_users(
                event_type, event_data, interested_users
            )
            
            # Track performance metrics
            broadcast_time = time.time() - start_time
            self.metrics.record_broadcast(event_type, delivery_count, broadcast_time)
            
            logger.debug(f"WEBSOCKET: Broadcast {event_type} to {delivery_count} users in {broadcast_time:.3f}s")
            return delivery_count
            
        except Exception as e:
            logger.error(f"WEBSOCKET: Broadcast error for {event_type}: {e}")
            return 0
```

## Subscription Index System

### Fast User Lookup Implementation
```python
class SubscriptionIndexManager:
    """
    Efficient indexing system for fast user lookup based on event criteria.
    Supports complex filtering across multiple dimensions.
    """
    
    def __init__(self):
        # Multi-dimensional indexes for fast filtering
        self.pattern_type_index: Dict[str, Set[str]] = defaultdict(set)    # pattern -> users
        self.symbol_index: Dict[str, Set[str]] = defaultdict(set)          # symbol -> users  
        self.tier_index: Dict[str, Set[str]] = defaultdict(set)            # tier -> users
        self.market_regime_index: Dict[str, Set[str]] = defaultdict(set)   # regime -> users
        self.subscription_type_index: Dict[str, Set[str]] = defaultdict(set) # type -> users
        
    def add_subscription(self, subscription: UserSubscription):
        """Add subscription to all relevant indexes"""
        user_id = subscription.user_id
        filters = subscription.filters
        sub_type = subscription.subscription_type
        
        # Index by subscription type
        self.subscription_type_index[sub_type].add(user_id)
        
        # Index by feature-specific filters
        if 'pattern_types' in filters:
            for pattern in filters['pattern_types']:
                self.pattern_type_index[pattern].add(user_id)
                
        if 'symbols' in filters:
            for symbol in filters['symbols']:
                self.symbol_index[symbol].add(user_id)
                
        if 'tiers' in filters:
            for tier in filters['tiers']:
                self.tier_index[tier].add(user_id)
                
        if 'market_regimes' in filters:
            for regime in filters['market_regimes']:
                self.market_regime_index[regime].add(user_id)
    
    def find_matching_users(self, criteria: Dict[str, Any]) -> Set[str]:
        """
        Find users matching event criteria using efficient set intersections.
        
        Performance: O(log n) lookup, O(k) intersection where k = matching users
        """
        matching_sets = []
        
        # Build list of matching user sets
        if 'pattern_type' in criteria:
            matching_sets.append(self.pattern_type_index.get(criteria['pattern_type'], set()))
            
        if 'symbol' in criteria:
            matching_sets.append(self.symbol_index.get(criteria['symbol'], set()))
            
        if 'tier' in criteria:
            matching_sets.append(self.tier_index.get(criteria['tier'], set()))
            
        if 'market_regime' in criteria:
            matching_sets.append(self.market_regime_index.get(criteria['market_regime'], set()))
            
        if 'subscription_type' in criteria:
            matching_sets.append(self.subscription_type_index.get(criteria['subscription_type'], set()))
        
        # Return intersection of all matching sets
        if matching_sets:
            result = matching_sets[0]
            for user_set in matching_sets[1:]:
                result = result.intersection(user_set)
            return result
        
        return set()
```

## Scalable Broadcasting System

### Batched Event Delivery
```python
class ScalableBroadcaster:
    """
    Efficient broadcasting system with batching and rate limiting.
    Industry standard for financial real-time applications.
    """
    
    def __init__(self, socketio: SocketIO):
        self.socketio = socketio
        self.event_batches: Dict[str, List[Dict]] = defaultdict(list)  # room -> events
        self.batch_timers: Dict[str, threading.Timer] = {}
        self.user_rate_limits: Dict[str, RateLimiter] = defaultdict(lambda: RateLimiter(100)) # 100 events/sec
        self.batch_delay = 0.1  # 100ms batching window
        
    def broadcast_to_users(self, event_type: str, event_data: Dict, 
                          user_ids: Set[str]) -> int:
        """Broadcast event to specific users with batching and rate limiting"""
        delivery_count = 0
        
        for user_id in user_ids:
            room_name = f"user_{user_id}"
            
            # Check rate limit
            if not self.user_rate_limits[user_id].allow():
                logger.debug(f"WEBSOCKET: Rate limit exceeded for user {user_id}")
                continue
            
            # Add to batch for this room
            event_envelope = {
                'type': event_type,
                'data': event_data,
                'timestamp': time.time()
            }
            
            self.event_batches[room_name].append(event_envelope)
            delivery_count += 1
            
            # Schedule batch delivery if not already scheduled
            if room_name not in self.batch_timers:
                timer = threading.Timer(self.batch_delay, 
                                      lambda r=room_name: self._flush_batch(r))
                self.batch_timers[room_name] = timer
                timer.start()
        
        return delivery_count
    
    def _flush_batch(self, room_name: str):
        """Send batched events to a specific room"""
        try:
            events = self.event_batches[room_name]
            if events:
                # Send batch of events
                if len(events) == 1:
                    # Single event - send directly
                    event = events[0]
                    self.socketio.emit(event['type'], event['data'], room=room_name)
                else:
                    # Multiple events - send as batch
                    self.socketio.emit('event_batch', {'events': events}, room=room_name)
                
                logger.debug(f"WEBSOCKET: Sent {len(events)} events to {room_name}")
            
            # Clean up
            self.event_batches[room_name].clear()
            if room_name in self.batch_timers:
                del self.batch_timers[room_name]
                
        except Exception as e:
            logger.error(f"WEBSOCKET: Batch flush error for {room_name}: {e}")
```

## Connection Scaling Architecture

### Connection Pool Management
```python
class ConnectionPoolManager:
    """
    Manage WebSocket connections across multiple pools for horizontal scaling.
    Required for 1000+ concurrent users.
    """
    
    def __init__(self, pool_size: int = 500):
        self.pool_size = pool_size
        self.connection_pools: Dict[str, Set[str]] = {}  # pool_id -> user_ids
        self.user_pool_mapping: Dict[str, str] = {}     # user_id -> pool_id
        self.pool_load: Dict[str, int] = defaultdict(int) # pool_id -> connection_count
        
    def assign_user_to_pool(self, user_id: str) -> str:
        """Assign user to least loaded connection pool"""
        # Find least loaded pool
        if not self.pool_load:
            pool_id = "pool_0"
        else:
            pool_id = min(self.pool_load.items(), key=lambda x: x[1])[0]
            
            # Create new pool if current pools are at capacity
            if self.pool_load[pool_id] >= self.pool_size:
                pool_id = f"pool_{len(self.connection_pools)}"
        
        # Assign user to pool
        if pool_id not in self.connection_pools:
            self.connection_pools[pool_id] = set()
        
        self.connection_pools[pool_id].add(user_id)
        self.user_pool_mapping[user_id] = pool_id
        self.pool_load[pool_id] += 1
        
        return pool_id
    
    def get_pool_stats(self) -> Dict[str, Dict]:
        """Get connection pool statistics"""
        stats = {}
        for pool_id, users in self.connection_pools.items():
            stats[pool_id] = {
                'user_count': len(users),
                'capacity_utilization': len(users) / self.pool_size,
                'status': 'healthy' if len(users) < self.pool_size * 0.8 else 'near_capacity'
            }
        return stats
```

## Feature Integration Patterns

### Pattern 1: Tier-Specific Patterns (Sprint 25)
```python
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
        """Broadcast tier pattern to interested users"""
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

### Pattern 2: Market Insights (Sprint 26)
```python
class MarketInsightsWebSocketIntegration:
    def __init__(self, websocket_manager: UniversalWebSocketManager):
        self.websocket = websocket_manager
        
    def subscribe_user_to_market_insights(self, user_id: str, preferences: Dict):
        """Subscribe user to market insights updates"""
        filters = {
            'etfs': preferences.get('etfs', ['SPY', 'QQQ', 'IWM']),
            'market_regimes': preferences.get('market_regimes', ['bull', 'bear', 'neutral']),
            'sectors': preferences.get('sectors', []),
            'update_frequency': preferences.get('update_frequency', 30)  # seconds
        }
        
        return self.websocket.subscribe_user(user_id, 'market_insights', filters)
    
    def broadcast_market_state_change(self, market_state: MarketState):
        """Broadcast market state changes to interested users"""
        targeting = {
            'subscription_type': 'market_insights',
            'market_regime': market_state.regime.value
        }
        
        return self.websocket.broadcast_event('market_state_update', 
                                            market_state.to_dict(), 
                                            targeting)
```

## Performance Specifications

### Scalability Targets
| User Count | Architecture Tier | Response Time | Throughput |
|------------|------------------|---------------|------------|
| 100-500    | Basic Room Management | <100ms | 1,000 events/sec |
| 500-1,000  | Indexed Filtering | <100ms | 5,000 events/sec |
| 1,000-2,000| Connection Pooling | <150ms | 10,000 events/sec |
| 2,000+     | Advanced Scaling | <200ms | 20,000+ events/sec |

### Key Performance Metrics
- **Event Filtering Latency**: <5ms to identify interested users per event
- **WebSocket Delivery Time**: <100ms from event generation to user browser
- **Memory Usage**: <1MB per 1,000 active user subscriptions
- **Connection Handling**: Support 5,000+ concurrent WebSocket connections
- **Broadcast Efficiency**: >95% delivery success rate
- **Rate Limiting**: 100 events/second per user maximum

## Implementation Guidelines

### Development Phases
1. **Phase 1 (Sprint 25)**: Implement core Universal WebSocket Manager
2. **Phase 2**: Add subscription indexing and efficient filtering
3. **Phase 3**: Implement batched broadcasting system
4. **Phase 4**: Add connection pooling for scale
5. **Phase 5**: Performance optimization and monitoring

### Feature Integration Steps
1. **Define Event Types**: Create feature-specific event models
2. **Implement Integration Class**: Create WebSocket integration wrapper
3. **Add Subscription Logic**: Define user subscription criteria
4. **Implement Broadcasting**: Add event broadcasting calls
5. **Test Integration**: Verify filtering and delivery accuracy

### Testing Strategy
- **Unit Tests**: Test individual components (indexing, filtering, batching)
- **Integration Tests**: Test feature-specific WebSocket integrations
- **Load Tests**: Validate performance under target user loads
- **Stress Tests**: Test system behavior at 2x expected capacity
- **Failure Tests**: Test graceful degradation and recovery

## Monitoring and Observability

### Key Metrics to Track
```python
@dataclass
class WebSocketMetrics:
    # Connection Metrics
    active_connections: int
    connections_per_pool: Dict[str, int]
    connection_establishment_rate: float
    connection_drop_rate: float
    
    # Subscription Metrics  
    total_subscriptions: int
    subscriptions_by_type: Dict[str, int]
    subscription_churn_rate: float
    
    # Event Metrics
    events_broadcast_per_second: float
    events_delivered_per_second: float
    delivery_success_rate: float
    average_delivery_latency_ms: float
    
    # Performance Metrics
    filtering_latency_ms: float
    batching_efficiency: float  # events per batch
    rate_limit_violations: int
    
    # Error Metrics
    broadcast_errors: int
    connection_errors: int
    subscription_errors: int
```

## Security Considerations

### Authentication and Authorization
- **WebSocket Authentication**: Verify user identity on connection
- **Subscription Authorization**: Validate user permissions for data access
- **Rate Limiting**: Prevent abuse and ensure fair resource usage
- **Input Validation**: Sanitize all subscription criteria and event data

### Data Protection
- **Sensitive Data Filtering**: Ensure users only receive authorized data
- **Connection Encryption**: Use WSS (WebSocket Secure) in production
- **Audit Logging**: Track all subscription and broadcasting activities
- **Privacy Compliance**: Respect user data preferences and regulations

This architecture provides the foundation for all real-time features in TickStockAppV2, ensuring scalable, efficient, and secure WebSocket communication for hundreds to thousands of concurrent users.