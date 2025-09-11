"""
Universal WebSocket Subscription Manager
Core scalable WebSocket service for Sprint 25+ multi-feature real-time communication.

Sprint 25 Day 1 Implementation: Foundation WebSocket scalability architecture
- Universal subscription management for all TickStockAppV2 features
- User-specific room-based subscriptions with intelligent filtering
- Industry-standard architecture supporting 500+ concurrent users
- Integration with existing Flask-SocketIO and Redis infrastructure
"""

import logging
import time
import threading
from datetime import datetime
from typing import Dict, Any, Optional, Set, List
from dataclasses import dataclass, field
from collections import defaultdict
from flask_socketio import SocketIO
import redis

# Integration with existing TickStockAppV2 infrastructure
from src.presentation.websocket.manager import WebSocketManager
from src.core.services.websocket_broadcaster import WebSocketBroadcaster
from src.infrastructure.websocket.subscription_index_manager import SubscriptionIndexManager
from src.infrastructure.websocket.scalable_broadcaster import ScalableBroadcaster, DeliveryPriority
from src.infrastructure.websocket.event_router import EventRouter, RoutingStrategy

logger = logging.getLogger(__name__)

# Import shared models
from src.core.models.websocket_models import UserSubscription

@dataclass
class WebSocketMetrics:
    """Performance metrics for WebSocket operations."""
    total_subscriptions: int = 0
    active_subscriptions: int = 0
    subscriptions_by_type: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    
    # Performance metrics
    events_broadcast: int = 0
    events_delivered: int = 0
    broadcast_latency_ms: float = 0.0
    filtering_latency_ms: float = 0.0
    
    # Connection metrics
    active_connections: int = 0
    total_connections: int = 0
    connection_errors: int = 0
    
    # Error tracking
    subscription_errors: int = 0
    broadcast_errors: int = 0
    
    def record_subscription(self, subscription_type: str):
        """Record new subscription."""
        self.total_subscriptions += 1
        self.active_subscriptions += 1
        self.subscriptions_by_type[subscription_type] += 1
    
    def record_unsubscription(self, subscription_type: str):
        """Record subscription removal."""
        self.active_subscriptions = max(0, self.active_subscriptions - 1)
        self.subscriptions_by_type[subscription_type] = max(0, self.subscriptions_by_type[subscription_type] - 1)
    
    def record_broadcast(self, event_type: str, user_count: int, latency_ms: float):
        """Record broadcast performance."""
        self.events_broadcast += 1
        self.events_delivered += user_count
        self.broadcast_latency_ms = latency_ms

class UniversalWebSocketManager:
    """
    Core WebSocket manager used by all TickStockAppV2 features.
    
    Implements industry-standard scalable real-time communication patterns:
    - User-specific room-based subscriptions
    - Efficient event filtering and routing
    - Connection pooling and load distribution
    - Performance monitoring and metrics
    
    Designed to support 500+ concurrent users with <100ms delivery times.
    """
    
    def __init__(self, socketio: SocketIO, redis_client: redis.Redis, 
                 existing_websocket_manager: WebSocketManager,
                 websocket_broadcaster: WebSocketBroadcaster):
        """Initialize Universal WebSocket Manager."""
        
        # Core infrastructure integration
        self.socketio = socketio
        self.redis_client = redis_client
        self.existing_ws_manager = existing_websocket_manager
        self.websocket_broadcaster = websocket_broadcaster
        
        # Subscription management
        self.user_subscriptions: Dict[str, Dict[str, UserSubscription]] = defaultdict(dict)
        
        # High-performance indexing system (Day 2 integration)
        self.index_manager = SubscriptionIndexManager(cache_size=1000, enable_optimization=True)
        
        # Scalable broadcasting system (Day 3 integration)
        self.broadcaster = ScalableBroadcaster(
            socketio=socketio,
            batch_window_ms=100,  # 100ms batching window
            max_events_per_user=100,  # 100 events/sec per user
            max_batch_size=50
        )
        # Alias for backward compatibility
        self.scalable_broadcaster = self.broadcaster
        
        # Intelligent event routing system (Day 4 integration)
        self.event_router = EventRouter(
            scalable_broadcaster=self.broadcaster,
            cache_size=1000,
            enable_caching=True
        )
        
        # Initialize default routing rules
        self._initialize_default_routing_rules()
        
        # Performance metrics
        self.metrics = WebSocketMetrics()
        self.start_time = time.time()
        
        # Thread safety
        self.subscription_lock = threading.RLock()
        
        logger.info("WEBSOCKET-SUBSCRIPTION: Universal WebSocket Manager initialized with indexing, broadcasting, and intelligent routing")
    
    def subscribe_user(self, user_id: str, subscription_type: str, 
                      filters: Dict[str, Any]) -> bool:
        """
        Universal user subscription method used by all TickStockAppV2 features.
        
        Args:
            user_id: Unique user identifier
            subscription_type: Feature type ('tier_patterns', 'market_insights', etc.)
            filters: Feature-specific filtering criteria
            
        Returns:
            True if subscription successful, False otherwise
            
        Example:
            # Tier-specific pattern subscription
            manager.subscribe_user('user123', 'tier_patterns', {
                'pattern_types': ['BreakoutBO', 'TrendReversal'],
                'symbols': ['AAPL', 'TSLA'],
                'tiers': ['daily', 'intraday'],
                'confidence_min': 0.7
            })
        """
        try:
            with self.subscription_lock:
                # Create room name for user-specific delivery
                room_name = f"user_{user_id}"
                
                # Create subscription
                subscription = UserSubscription(
                    user_id=user_id,
                    subscription_type=subscription_type,
                    filters=filters,
                    room_name=room_name
                )
                
                # Store subscription
                self.user_subscriptions[user_id][subscription_type] = subscription
                
                # Add to high-performance index system (Day 2 enhancement)
                self.index_manager.add_subscription(subscription)
                
                # Ensure user is connected via existing WebSocket infrastructure
                if self.existing_ws_manager.is_user_connected(user_id):
                    # Join user to their specific room for targeted delivery
                    user_connections = self.existing_ws_manager.get_user_connections(user_id)
                    for connection_id in user_connections:
                        try:
                            self.socketio.server.enter_room(connection_id, room_name)
                        except Exception as e:
                            logger.warning(f"WEBSOCKET-SUBSCRIPTION: Failed to join room {room_name}: {e}")
                
                # Update metrics
                self.metrics.record_subscription(subscription_type)
                
                logger.info(f"WEBSOCKET-SUBSCRIPTION: User {user_id} subscribed to {subscription_type}")
                return True
                
        except Exception as e:
            logger.error(f"WEBSOCKET-SUBSCRIPTION: Subscription error for {user_id}: {e}")
            self.metrics.subscription_errors += 1
            return False
    
    def unsubscribe_user(self, user_id: str, subscription_type: Optional[str] = None) -> bool:
        """
        Remove user subscriptions (specific type or all).
        
        Args:
            user_id: User to unsubscribe
            subscription_type: Specific subscription to remove, or None for all
            
        Returns:
            True if successful
        """
        try:
            with self.subscription_lock:
                if user_id not in self.user_subscriptions:
                    return True  # Already unsubscribed
                
                if subscription_type:
                    # Remove specific subscription
                    if subscription_type in self.user_subscriptions[user_id]:
                        subscription = self.user_subscriptions[user_id][subscription_type]
                        del self.user_subscriptions[user_id][subscription_type]
                        
                        # Update metrics
                        self.metrics.record_unsubscription(subscription_type)
                        
                        logger.info(f"WEBSOCKET-SUBSCRIPTION: User {user_id} unsubscribed from {subscription_type}")
                else:
                    # Remove all subscriptions for user
                    for sub_type, subscription in self.user_subscriptions[user_id].items():
                        self.metrics.record_unsubscription(sub_type)
                    
                    self.user_subscriptions[user_id].clear()
                    
                    # Leave user room
                    room_name = f"user_{user_id}"
                    if self.existing_ws_manager.is_user_connected(user_id):
                        user_connections = self.existing_ws_manager.get_user_connections(user_id)
                        for connection_id in user_connections:
                            try:
                                self.socketio.server.leave_room(connection_id, room_name)
                            except Exception as e:
                                logger.warning(f"WEBSOCKET-SUBSCRIPTION: Failed to leave room {room_name}: {e}")
                    
                    logger.info(f"WEBSOCKET-SUBSCRIPTION: User {user_id} unsubscribed from all")
                
                # Remove from index system (Day 2 enhancement)
                self.index_manager.remove_subscription(user_id, subscription_type)
                
                # Clean up empty user entries
                if not self.user_subscriptions[user_id]:
                    del self.user_subscriptions[user_id]
                
                return True
                
        except Exception as e:
            logger.error(f"WEBSOCKET-SUBSCRIPTION: Unsubscription error for {user_id}: {e}")
            return False
    
    def broadcast_event(self, event_type: str, event_data: Dict[str, Any], 
                       targeting_criteria: Optional[Dict[str, Any]] = None) -> int:
        """
        Universal event broadcasting method used by all TickStockAppV2 features.
        
        Args:
            event_type: Type of event being broadcast ('tier_pattern', 'market_update', etc.)
            event_data: Event payload to send to users
            targeting_criteria: Filtering criteria to target specific users
            
        Returns:
            Number of users event was delivered to
            
        Example:
            # Broadcast tier pattern event to interested users
            manager.broadcast_event('tier_pattern', {
                'pattern': 'BreakoutBO',
                'symbol': 'AAPL',
                'confidence': 0.85,
                'tier': 'daily'
            }, {
                'subscription_type': 'tier_patterns',
                'pattern_type': 'BreakoutBO',
                'symbol': 'AAPL',
                'tier': 'daily'
            })
        """
        try:
            start_time = time.time()
            
            # Find users interested in this event
            interested_users = self._find_interested_users(targeting_criteria or {})
            
            if not interested_users:
                logger.debug(f"WEBSOCKET-SUBSCRIPTION: No users interested in {event_type}")
                return 0
            
            # Determine message priority based on event type and criteria
            priority = DeliveryPriority.MEDIUM
            if targeting_criteria.get('priority') == 'critical':
                priority = DeliveryPriority.CRITICAL
            elif targeting_criteria.get('priority') == 'high':
                priority = DeliveryPriority.HIGH
            elif targeting_criteria.get('confidence', 0) >= 0.9:
                priority = DeliveryPriority.HIGH
            
            # Prepare event data with enhanced metadata
            enhanced_event_data = {
                **event_data,
                'timestamp': time.time(),
                'server_id': 'tickstock-app-v2',
                'delivery_metadata': {
                    'targeting_criteria': targeting_criteria,
                    'user_count': len(interested_users)
                }
            }
            
            # Use intelligent event router for sophisticated routing (Day 4 enhancement)
            user_context = {
                'interested_users': list(interested_users),
                'targeting_criteria': targeting_criteria,
                'priority': priority.name
            }
            
            routing_result = self.event_router.route_event(
                event_type=event_type,
                event_data=enhanced_event_data,
                user_context=user_context
            )
            
            delivery_count = routing_result.total_users if routing_result.total_users > 0 else len(interested_users)
            
            # Track performance metrics
            broadcast_time_ms = (time.time() - start_time) * 1000
            self.metrics.record_broadcast(event_type, delivery_count, broadcast_time_ms)
            
            logger.debug(f"WEBSOCKET-SUBSCRIPTION: Event {event_type} routed to {delivery_count} users "
                        f"via {len(routing_result.matched_rules)} rules in {broadcast_time_ms:.1f}ms "
                        f"(routing: {routing_result.routing_time_ms:.1f}ms, cache: {routing_result.cache_hit})")
            return delivery_count
            
        except Exception as e:
            logger.error(f"WEBSOCKET-SUBSCRIPTION: Broadcast error for {event_type}: {e}")
            self.metrics.broadcast_errors += 1
            return 0
    
    def _find_interested_users(self, targeting_criteria: Dict[str, Any]) -> Set[str]:
        """
        Find users matching event criteria using high-performance indexing system.
        
        Performance: O(log n) lookup + O(k) intersection where k = matching users
        Target: <5ms for 1000+ subscriptions (Day 2 enhancement with indexing)
        """
        try:
            start_time = time.time()
            
            # Use high-performance index manager for filtering (Day 2 enhancement)
            interested_users = self.index_manager.find_matching_users(targeting_criteria)
            
            # Update activity for matched users (with minimal lock time)
            with self.subscription_lock:
                for user_id in interested_users:
                    if user_id in self.user_subscriptions:
                        for subscription in self.user_subscriptions[user_id].values():
                            if subscription.active:
                                subscription.update_activity()
                                break  # Update once per user
            
            # Track filtering performance
            filtering_time_ms = (time.time() - start_time) * 1000
            self.metrics.filtering_latency_ms = filtering_time_ms
            
            # Performance monitoring with enhanced alerting
            if filtering_time_ms > 5.0:
                logger.warning(f"WEBSOCKET-SUBSCRIPTION: Slow indexing {filtering_time_ms:.1f}ms "
                             f"for {len(self.user_subscriptions)} users - indexing may need optimization")
            elif filtering_time_ms > 2.0:
                logger.debug(f"WEBSOCKET-SUBSCRIPTION: Indexing performance {filtering_time_ms:.1f}ms "
                           f"for {len(interested_users)} matching users")
            
            return interested_users
            
        except Exception as e:
            logger.error(f"WEBSOCKET-SUBSCRIPTION: Error finding interested users: {e}")
            return set()
    
    def handle_user_connection(self, user_id: str, connection_id: str):
        """Handle new user connection - join them to their rooms."""
        try:
            with self.subscription_lock:
                if user_id in self.user_subscriptions:
                    # User has subscriptions, join them to their room
                    room_name = f"user_{user_id}"
                    self.socketio.server.enter_room(connection_id, room_name)
                    
                    # Update connection metrics
                    self.metrics.total_connections += 1
                    self.metrics.active_connections = len(self.existing_ws_manager.get_connected_users())
                    
                    logger.info(f"WEBSOCKET-SUBSCRIPTION: User {user_id} joined room {room_name} (connection: {connection_id})")
                    
                    # Notify user of active subscriptions
                    subscription_types = list(self.user_subscriptions[user_id].keys())
                    self.socketio.emit('subscription_status', {
                        'active_subscriptions': subscription_types,
                        'room': room_name,
                        'timestamp': time.time()
                    }, room=connection_id)
                    
        except Exception as e:
            logger.error(f"WEBSOCKET-SUBSCRIPTION: Error handling connection for {user_id}: {e}")
            self.metrics.connection_errors += 1
    
    def handle_user_disconnection(self, user_id: str, connection_id: str):
        """Handle user disconnection."""
        try:
            # Update connection metrics
            self.metrics.active_connections = len(self.existing_ws_manager.get_connected_users())
            
            logger.info(f"WEBSOCKET-SUBSCRIPTION: User {user_id} disconnected (connection: {connection_id})")
            
        except Exception as e:
            logger.error(f"WEBSOCKET-SUBSCRIPTION: Error handling disconnection for {user_id}: {e}")
    
    def get_user_subscriptions(self, user_id: str) -> Dict[str, UserSubscription]:
        """Get all subscriptions for a specific user."""
        with self.subscription_lock:
            return dict(self.user_subscriptions.get(user_id, {}))
    
    def get_subscription_stats(self) -> Dict[str, Any]:
        """Get subscription statistics and performance metrics."""
        with self.subscription_lock:
            runtime_seconds = time.time() - self.start_time
            
            # Calculate subscription breakdown
            total_users = len(self.user_subscriptions)
            subscription_breakdown = {}
            
            for user_subs in self.user_subscriptions.values():
                for sub_type in user_subs.keys():
                    subscription_breakdown[sub_type] = subscription_breakdown.get(sub_type, 0) + 1
            
            # Get index manager statistics (Day 2 enhancement)
            index_stats = self.index_manager.get_index_stats()
            
            # Get scalable broadcaster statistics (Day 3 enhancement)
            broadcast_stats = self.scalable_broadcaster.get_broadcast_stats()
            
            # Get event router statistics (Day 4 enhancement)
            routing_stats = self.event_router.get_routing_stats()
            
            return {
                # Subscription metrics
                'total_users': total_users,
                'total_subscriptions': self.metrics.total_subscriptions,
                'active_subscriptions': self.metrics.active_subscriptions,
                'subscription_breakdown': subscription_breakdown,
                
                # Performance metrics (enhanced with indexing)
                'events_broadcast': self.metrics.events_broadcast,
                'events_delivered': self.metrics.events_delivered,
                'avg_broadcast_latency_ms': round(self.metrics.broadcast_latency_ms, 2),
                'avg_filtering_latency_ms': round(self.metrics.filtering_latency_ms, 2),
                
                # Indexing performance metrics (Day 2)
                'index_lookup_count': index_stats['lookup_count'],
                'index_avg_lookup_ms': index_stats['avg_lookup_time_ms'],
                'index_cache_hit_rate': index_stats['cache_hit_rate_percent'],
                'index_performance_status': index_stats['performance_status'],
                'total_indexes': index_stats['total_indexes'],
                'index_sizes': index_stats['index_sizes'],
                
                # Broadcasting performance metrics (Day 3)
                'broadcast_events_delivered': broadcast_stats['events_delivered'],
                'broadcast_avg_batch_size': broadcast_stats['avg_batch_size'],
                'broadcast_avg_latency_ms': broadcast_stats['avg_delivery_latency_ms'],
                'broadcast_success_rate': broadcast_stats['delivery_success_rate_percent'],
                'broadcast_pending_batches': broadcast_stats['pending_batches'],
                'broadcast_rate_limited': broadcast_stats['events_rate_limited'],
                
                # Routing performance metrics (Day 4)
                'routing_total_events': routing_stats['total_events'],
                'routing_avg_time_ms': routing_stats['avg_routing_time_ms'],
                'routing_cache_hit_rate': routing_stats['cache_hit_rate_percent'],
                'routing_rules_count': routing_stats['total_rules'],
                'routing_avg_rules_matched': routing_stats['avg_rules_matched_per_event'],
                'routing_errors': routing_stats['routing_errors'],
                
                # Connection metrics
                'active_connections': self.metrics.active_connections,
                'total_connections': self.metrics.total_connections,
                
                # Error tracking
                'subscription_errors': self.metrics.subscription_errors,
                'broadcast_errors': self.metrics.broadcast_errors,
                'connection_errors': self.metrics.connection_errors,
                
                # System metrics
                'runtime_seconds': round(runtime_seconds, 1),
                'uptime_hours': round(runtime_seconds / 3600, 1),
                'last_updated': time.time()
            }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status for monitoring and alerts."""
        stats = self.get_subscription_stats()
        
        # Get broadcaster health status (Day 3 enhancement)
        broadcaster_health = self.scalable_broadcaster.get_health_status()
        
        # Determine overall health status
        if stats['subscription_errors'] > 10 or stats['broadcast_errors'] > 10:
            status = 'error'
            message = f"High error rate: {stats['subscription_errors']} subscription, {stats['broadcast_errors']} broadcast errors"
        elif broadcaster_health['status'] == 'error':
            status = 'error'
            message = f"Broadcaster unhealthy: {broadcaster_health['message']}"
        elif stats['avg_filtering_latency_ms'] > 10.0:
            status = 'warning'
            message = f"Slow filtering performance: {stats['avg_filtering_latency_ms']}ms average"
        elif stats['broadcast_avg_latency_ms'] > 100.0:
            status = 'warning'
            message = f"Slow broadcast performance: {stats['broadcast_avg_latency_ms']}ms average"
        elif broadcaster_health['status'] == 'warning':
            status = 'warning'
            message = f"Broadcaster warning: {broadcaster_health['message']}"
        else:
            status = 'healthy'
            message = f"Service healthy - {stats['active_subscriptions']} subscriptions, {stats['broadcast_avg_latency_ms']:.1f}ms broadcast latency"
        
        return {
            'status': status,
            'message': message,
            'timestamp': time.time(),
            'stats': stats,
            'broadcaster_health': broadcaster_health,
            'performance_targets': {
                'filtering_target_ms': 5.0,
                'broadcast_target_ms': 100.0,
                'target_concurrent_users': 500
            }
        }
    
    def cleanup_inactive_subscriptions(self, max_inactive_hours: int = 24) -> int:
        """Clean up subscriptions that haven't been active recently."""
        try:
            current_time = datetime.now()
            cleaned_count = 0
            
            with self.subscription_lock:
                users_to_remove = []
                
                for user_id, user_subscriptions in self.user_subscriptions.items():
                    subscriptions_to_remove = []
                    
                    for sub_type, subscription in user_subscriptions.items():
                        hours_inactive = (current_time - subscription.last_activity).total_seconds() / 3600
                        
                        if hours_inactive > max_inactive_hours:
                            # Check if user is still connected
                            if not self.existing_ws_manager.is_user_connected(user_id):
                                subscriptions_to_remove.append(sub_type)
                    
                    # Remove inactive subscriptions
                    for sub_type in subscriptions_to_remove:
                        del user_subscriptions[sub_type]
                        self.metrics.record_unsubscription(sub_type)
                        cleaned_count += 1
                    
                    # Mark user for removal if no subscriptions left
                    if not user_subscriptions:
                        users_to_remove.append(user_id)
                
                # Remove users with no subscriptions
                for user_id in users_to_remove:
                    del self.user_subscriptions[user_id]
            
            if cleaned_count > 0:
                logger.info(f"WEBSOCKET-SUBSCRIPTION: Cleaned up {cleaned_count} inactive subscriptions")
            
            # Also cleanup index system (Day 2 enhancement)
            index_cleaned = self.index_manager.cleanup_stale_entries(max_inactive_hours)
            
            return cleaned_count + index_cleaned
            
        except Exception as e:
            logger.error(f"WEBSOCKET-SUBSCRIPTION: Error cleaning up subscriptions: {e}")
            return 0
    
    def optimize_performance(self) -> Dict[str, Any]:
        """Optimize subscription, indexing, and broadcasting performance (Day 3 enhancement)."""
        try:
            # Optimize index system
            index_optimization = self.index_manager.optimize_indexes()
            
            # Optimize broadcasting system (Day 3 enhancement)
            broadcast_optimization = self.scalable_broadcaster.optimize_performance()
            
            # Optimize routing system (Day 4 enhancement)
            routing_optimization = self.event_router.optimize_performance()
            
            # Get updated performance stats
            stats = self.get_subscription_stats()
            
            optimization_results = {
                'index_optimization': index_optimization,
                'broadcast_optimization': broadcast_optimization,
                'routing_optimization': routing_optimization,
                'current_performance': {
                    'avg_filtering_ms': stats['avg_filtering_latency_ms'],
                    'index_avg_lookup_ms': stats['index_avg_lookup_ms'],
                    'cache_hit_rate': stats['index_cache_hit_rate'],
                    'broadcast_avg_latency_ms': stats['broadcast_avg_latency_ms'],
                    'broadcast_success_rate': stats['broadcast_success_rate'],
                    'routing_avg_time_ms': stats.get('routing_avg_time_ms', 0),
                    'routing_cache_hit_rate': stats.get('routing_cache_hit_rate', 0),
                    'total_users': stats['total_users'],
                    'total_indexes': stats['total_indexes']
                },
                'performance_targets_met': {
                    'filtering_under_5ms': stats['avg_filtering_latency_ms'] < 5.0,
                    'index_lookup_under_5ms': stats['index_avg_lookup_ms'] < 5.0,
                    'cache_hit_rate_above_70': stats['index_cache_hit_rate'] > 70.0,
                    'broadcast_under_100ms': stats['broadcast_avg_latency_ms'] < 100.0,
                    'broadcast_success_above_95': stats['broadcast_success_rate'] > 95.0,
                    'routing_under_20ms': stats.get('routing_avg_time_ms', 0) < 20.0
                },
                'optimization_timestamp': time.time()
            }
            
            logger.info(f"WEBSOCKET-SUBSCRIPTION: Performance optimization complete - "
                       f"filtering: {stats['avg_filtering_latency_ms']:.1f}ms, "
                       f"indexing: {stats['index_avg_lookup_ms']:.1f}ms, "
                       f"broadcasting: {stats['broadcast_avg_latency_ms']:.1f}ms, "
                       f"cache: {stats['index_cache_hit_rate']:.1f}%")
            
            return optimization_results
            
        except Exception as e:
            logger.error(f"WEBSOCKET-SUBSCRIPTION: Error optimizing performance: {e}")
            return {'error': str(e), 'timestamp': time.time()}
    
    def _initialize_default_routing_rules(self):
        """Initialize default routing rules for common event types (Day 4 enhancement)."""
        try:
            from src.infrastructure.websocket.event_router import (
                create_pattern_routing_rule, 
                create_tier_routing_rule,
                RoutingRule, RoutingStrategy
            )
            
            # Pattern alert routing rule
            pattern_rule = create_pattern_routing_rule(
                rule_id='default_pattern_routing',
                pattern_types=['BreakoutBO', 'TrendReversal', 'SupportBreak'],
                symbols=None  # All symbols
            )
            self.event_router.add_routing_rule(pattern_rule)
            
            # Tier-specific routing rules
            for tier in ['daily', 'intraday', 'combo']:
                tier_rule = create_tier_routing_rule(
                    rule_id=f'default_tier_{tier}_routing',
                    tier=tier
                )
                self.event_router.add_routing_rule(tier_rule)
            
            # High-priority system health routing
            system_health_rule = RoutingRule(
                rule_id='system_health_routing',
                name='System Health Broadcasting',
                description='Route system health events to all users',
                event_type_patterns=[r'system_health', r'.*health.*'],
                content_filters={},
                user_criteria={},
                strategy=RoutingStrategy.BROADCAST_ALL,
                destinations=['system_health_room'],
                priority=DeliveryPriority.HIGH
            )
            self.event_router.add_routing_rule(system_health_rule)
            
            # Backtest result routing
            backtest_rule = RoutingRule(
                rule_id='backtest_result_routing',
                name='Backtest Result Routing',
                description='Route backtest results to all users',
                event_type_patterns=[r'backtest.*', r'.*result.*'],
                content_filters={},
                user_criteria={},
                strategy=RoutingStrategy.BROADCAST_ALL,
                destinations=['backtest_results_room'],
                priority=DeliveryPriority.MEDIUM
            )
            self.event_router.add_routing_rule(backtest_rule)
            
            logger.info("WEBSOCKET-SUBSCRIPTION: Initialized default routing rules")
            
        except Exception as e:
            logger.error(f"WEBSOCKET-SUBSCRIPTION: Error initializing default routing rules: {e}")
    
    def add_custom_routing_rule(self, rule) -> bool:
        """Add custom routing rule to the event router (Day 4 enhancement)."""
        try:
            return self.event_router.add_routing_rule(rule)
        except Exception as e:
            logger.error(f"WEBSOCKET-SUBSCRIPTION: Error adding custom routing rule: {e}")
            return False
    
    def remove_routing_rule(self, rule_id: str) -> bool:
        """Remove routing rule from the event router (Day 4 enhancement)."""
        try:
            return self.event_router.remove_routing_rule(rule_id)
        except Exception as e:
            logger.error(f"WEBSOCKET-SUBSCRIPTION: Error removing routing rule: {e}")
            return False
    
    def get_routing_stats(self) -> Dict[str, Any]:
        """Get event router statistics (Day 4 enhancement)."""
        try:
            return self.event_router.get_routing_stats()
        except Exception as e:
            logger.error(f"WEBSOCKET-SUBSCRIPTION: Error getting routing stats: {e}")
            return {'error': str(e), 'timestamp': time.time()}