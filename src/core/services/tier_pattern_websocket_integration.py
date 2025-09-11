"""
Tier Pattern WebSocket Integration Service
Sprint 25 Day 5 Implementation: WebSocket integration wrapper for tier-specific patterns.

Integrates tier-specific pattern events with the Universal WebSocket Manager
for efficient delivery to interested users based on subscription criteria.
"""

import logging
import time
from typing import Dict, Any, Set, List, Optional
from dataclasses import dataclass

# Core infrastructure imports
from src.core.services.websocket_subscription_manager import UniversalWebSocketManager
from src.infrastructure.websocket.subscription_index_manager import SubscriptionIndexManager
from src.infrastructure.websocket.scalable_broadcaster import ScalableBroadcaster
from src.infrastructure.websocket.event_router import EventRouter
from src.core.domain.events.tier_events import (
    TierPatternEvent, PatternTier, EventPriority, 
    MarketStateEvent, PatternAlertEvent
)

logger = logging.getLogger(__name__)

@dataclass
class TierSubscriptionPreferences:
    """User preferences for tier-specific pattern subscriptions."""
    
    # Pattern filtering
    pattern_types: List[str]           # Specific patterns to subscribe to
    symbols: List[str]                 # Stock symbols of interest
    tiers: List[PatternTier]          # Which tiers to include
    
    # Quality filtering  
    confidence_min: float = 0.6       # Minimum confidence threshold
    priority_min: EventPriority = EventPriority.MEDIUM  # Minimum priority level
    
    # Delivery preferences
    max_events_per_hour: int = 50      # Rate limiting
    enable_market_hours_only: bool = False  # Filter by market hours
    
    def to_filter_dict(self) -> Dict[str, Any]:
        """Convert preferences to WebSocket manager filter format."""
        return {
            'pattern_types': self.pattern_types,
            'symbols': self.symbols,
            'tiers': [tier.value for tier in self.tiers],
            'confidence_min': self.confidence_min,
            'priority_min': self.priority_min.value,
            'max_events_per_hour': self.max_events_per_hour,
            'market_hours_only': self.enable_market_hours_only
        }

class TierPatternWebSocketIntegration:
    """
    WebSocket integration service for tier-specific pattern events.
    
    Provides high-level interface for tier pattern subscription management
    and event broadcasting while leveraging the complete 4-layer WebSocket
    architecture for maximum scalability and performance.
    
    Architecture Integration:
    - UniversalWebSocketManager: Foundation service for user management
    - SubscriptionIndexManager: <5ms user filtering with multi-dimensional indexing
    - ScalableBroadcaster: Batched delivery with rate limiting (100 events/sec per user)
    - EventRouter: Intelligent routing with content-based analysis and caching
    
    Performance Targets:
    - <5ms user filtering (via SubscriptionIndexManager)
    - <20ms intelligent routing (via EventRouter)
    - <100ms batched delivery (via ScalableBroadcaster)
    - <125ms total end-to-end latency
    - 500+ concurrent users supported
    """
    
    def __init__(self, websocket_manager: UniversalWebSocketManager):
        """Initialize tier pattern WebSocket integration with 4-layer architecture."""
        self.websocket_manager = websocket_manager
        
        # Access integrated 4-layer architecture components
        self.index_manager = websocket_manager.index_manager
        self.broadcaster = websocket_manager.broadcaster
        self.event_router = websocket_manager.event_router
        
        # Tier pattern specific configuration
        self._setup_tier_pattern_routing_rules()
        
        # Event statistics
        self.stats = {
            'tier_subscriptions': 0,
            'patterns_broadcast': 0,
            'market_updates_sent': 0,
            'alerts_generated': 0,
            'high_priority_patterns': 0,
            'critical_alerts': 0,
            'routing_cache_hits': 0,
            'batch_efficiency': 0.0,
            'last_pattern_time': None,
            'start_time': time.time()
        }
        
        logger.info("TIER-PATTERN-WS: Tier pattern WebSocket integration initialized with 4-layer architecture")
        logger.info(f"TIER-PATTERN-WS: Index manager: {type(self.index_manager).__name__}")
        logger.info(f"TIER-PATTERN-WS: Broadcaster: {type(self.broadcaster).__name__}")
        logger.info(f"TIER-PATTERN-WS: Event router: {type(self.event_router).__name__}")
    
    def _setup_tier_pattern_routing_rules(self):
        """Setup intelligent routing rules for tier-specific patterns."""
        try:
            # High-priority pattern routing - escalate to PRIORITY_FIRST strategy
            self.event_router.add_routing_rule(
                event_type='tier_pattern',
                conditions={
                    'confidence': {'min': 0.9},
                    'priority': ['HIGH', 'CRITICAL']
                },
                strategy='PRIORITY_FIRST',
                destinations=['high_confidence_room', 'priority_alerts'],
                description='High-confidence tier patterns get priority routing'
            )
            
            # Symbol-specific routing - content-based distribution
            self.event_router.add_routing_rule(
                event_type='tier_pattern',
                conditions={'pattern_type': ['BreakoutBO', 'TrendReversal', 'SurgeDetection']},
                strategy='CONTENT_BASED',
                destinations=['symbol_rooms', 'pattern_specific_alerts'],
                content_transformation=self._enrich_pattern_with_market_context,
                description='Content-based routing for major pattern types'
            )
            
            # Market state routing - broadcast critical market insights
            self.event_router.add_routing_rule(
                event_type='market_state_update',
                conditions={'regime': ['BEARISH', 'VOLATILE', 'CRISIS']},
                strategy='BROADCAST_ALL',
                destinations=['market_insights_room', 'risk_alerts'],
                description='Broadcast critical market state changes to all users'
            )
            
            # Tier-based load balancing
            self.event_router.add_routing_rule(
                event_type='tier_pattern',
                conditions={'tier': ['INTRADAY']},
                strategy='LOAD_BALANCED',
                destinations=['intraday_room_1', 'intraday_room_2', 'intraday_room_3'],
                description='Load balance high-frequency intraday patterns'
            )
            
            logger.info("TIER-PATTERN-WS: Tier pattern routing rules configured successfully")
            
        except Exception as e:
            logger.error(f"TIER-PATTERN-WS: Error setting up routing rules: {e}")
    
    def _enrich_pattern_with_market_context(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich pattern events with market context for better routing decisions."""
        try:
            # Add market context metadata
            enriched_data = event_data.copy()
            enriched_data['market_context'] = {
                'session': self._get_market_session(),
                'volume_profile': self._analyze_volume_context(event_data.get('symbol')),
                'sector_performance': self._get_sector_context(event_data.get('symbol')),
                'enrichment_timestamp': time.time()
            }
            
            return enriched_data
            
        except Exception as e:
            logger.warning(f"TIER-PATTERN-WS: Error enriching pattern data: {e}")
            return event_data
    
    def _get_market_session(self) -> str:
        """Determine current market session for context."""
        from datetime import datetime, time as dt_time
        
        current_time = datetime.now().time()
        
        # Market sessions (ET)
        premarket = dt_time(4, 0)  # 4:00 AM
        open_time = dt_time(9, 30)  # 9:30 AM
        close_time = dt_time(16, 0)  # 4:00 PM
        afterhours = dt_time(20, 0)  # 8:00 PM
        
        if premarket <= current_time < open_time:
            return 'PRE_MARKET'
        elif open_time <= current_time < close_time:
            return 'REGULAR_HOURS'
        elif close_time <= current_time < afterhours:
            return 'AFTER_HOURS'
        else:
            return 'CLOSED'
    
    def _analyze_volume_context(self, symbol: str) -> str:
        """Analyze volume context for symbol (simplified for integration wrapper)."""
        # In full implementation, this would analyze current vs average volume
        return 'NORMAL'  # Placeholder
    
    def _get_sector_context(self, symbol: str) -> str:
        """Get sector performance context (simplified for integration wrapper)."""
        # In full implementation, this would provide sector-wide performance data
        return 'NEUTRAL'  # Placeholder
    
    def subscribe_user_to_tier_patterns(self, user_id: str, 
                                      preferences: TierSubscriptionPreferences) -> bool:
        """
        Subscribe user to tier-specific pattern events.
        
        Args:
            user_id: User identifier
            preferences: Tier subscription preferences
            
        Returns:
            True if subscription successful
            
        Example:
            preferences = TierSubscriptionPreferences(
                pattern_types=['BreakoutBO', 'TrendReversal'],
                symbols=['AAPL', 'TSLA', 'MSFT'],
                tiers=[PatternTier.DAILY, PatternTier.INTRADAY],
                confidence_min=0.7,
                priority_min=EventPriority.MEDIUM
            )
            integration.subscribe_user_to_tier_patterns('user123', preferences)
        """
        try:
            # Convert preferences to filter format
            filters = preferences.to_filter_dict()
            
            # Subscribe via Universal WebSocket Manager
            success = self.websocket_manager.subscribe_user(
                user_id=user_id,
                subscription_type='tier_patterns',
                filters=filters
            )
            
            if success:
                self.stats['tier_subscriptions'] += 1
                logger.info(f"TIER-PATTERN-WS: User {user_id} subscribed to tier patterns")
                logger.debug(f"TIER-PATTERN-WS: Subscription filters: {filters}")
            
            return success
            
        except Exception as e:
            logger.error(f"TIER-PATTERN-WS: Error subscribing user {user_id}: {e}")
            return False
    
    def unsubscribe_user_from_tier_patterns(self, user_id: str) -> bool:
        """Unsubscribe user from tier pattern events."""
        try:
            success = self.websocket_manager.unsubscribe_user(user_id, 'tier_patterns')
            
            if success:
                logger.info(f"TIER-PATTERN-WS: User {user_id} unsubscribed from tier patterns")
            
            return success
            
        except Exception as e:
            logger.error(f"TIER-PATTERN-WS: Error unsubscribing user {user_id}: {e}")
            return False
    
    def broadcast_tier_pattern_event(self, pattern_event: TierPatternEvent) -> int:
        """
        Broadcast tier pattern event using 4-layer architecture for maximum performance.
        
        Performance Flow:
        1. SubscriptionIndexManager: <5ms user filtering with multi-dimensional indexing
        2. EventRouter: <20ms intelligent routing with content-based analysis
        3. ScalableBroadcaster: <100ms batched delivery with rate limiting
        4. Total: <125ms end-to-end delivery
        
        Args:
            pattern_event: TierPatternEvent to broadcast
            
        Returns:
            Number of users event was delivered to
        """
        try:
            start_time = time.time()
            
            # Create enhanced targeting criteria for multi-dimensional indexing
            targeting_criteria = {
                'subscription_type': 'tier_patterns',
                'pattern_type': pattern_event.pattern_type,
                'symbol': pattern_event.symbol,
                'tier': pattern_event.tier.value,
                'confidence': pattern_event.confidence,
                'priority': pattern_event.priority.value,
                'market_session': self._get_market_session(),
                'requires_enrichment': pattern_event.confidence >= 0.8
            }
            
            # Broadcast using integrated 4-layer architecture
            delivery_count = self.websocket_manager.broadcast_event(
                event_type='tier_pattern',
                event_data=pattern_event.to_websocket_dict(),
                targeting_criteria=targeting_criteria
            )
            
            # Calculate performance metrics
            total_latency = (time.time() - start_time) * 1000  # ms
            
            # Update statistics with performance tracking
            self.stats['patterns_broadcast'] += 1
            self.stats['last_pattern_time'] = time.time()
            
            if pattern_event.priority in [EventPriority.HIGH, EventPriority.CRITICAL]:
                self.stats['high_priority_patterns'] += 1
            
            # Track routing cache efficiency
            if hasattr(self.event_router, 'get_cache_stats'):
                cache_stats = self.event_router.get_cache_stats()
                self.stats['routing_cache_hits'] = cache_stats.get('hit_count', 0)
            
            # Track batch efficiency from broadcaster
            if hasattr(self.broadcaster, 'get_batch_stats'):
                batch_stats = self.broadcaster.get_batch_stats()
                self.stats['batch_efficiency'] = batch_stats.get('efficiency_ratio', 0.0)
            
            logger.info(f"TIER-PATTERN-WS: Tier pattern {pattern_event.pattern_type} on {pattern_event.symbol} "
                       f"delivered to {delivery_count} users in {total_latency:.1f}ms "
                       f"(tier: {pattern_event.tier.value}, confidence: {pattern_event.confidence:.2f})")
            
            if total_latency > 125:  # Exceeds target
                logger.warning(f"TIER-PATTERN-WS: Delivery latency {total_latency:.1f}ms exceeds 125ms target")
            
            return delivery_count
            
        except Exception as e:
            logger.error(f"TIER-PATTERN-WS: Error broadcasting tier pattern: {e}")
            return 0
    
    def broadcast_market_state_update(self, market_event: MarketStateEvent) -> int:
        """
        Broadcast market state update using intelligent routing for maximum impact.
        
        Market state updates use BROADCAST_ALL strategy for critical regime changes
        and CONTENT_BASED routing for sector-specific insights.
        
        Args:
            market_event: MarketStateEvent to broadcast
            
        Returns:
            Number of users event was delivered to
        """
        try:
            start_time = time.time()
            
            # Enhanced targeting with routing intelligence
            targeting_criteria = {
                'subscription_type': 'market_insights',
                'market_regime': market_event.regime.value,
                'volatility_regime': market_event.volatility_regime,
                'session': self._get_market_session(),
                'broadcast_priority': 'high' if market_event.regime.value in ['BEARISH', 'VOLATILE'] else 'normal'
            }
            
            # Use 4-layer architecture for optimized delivery
            delivery_count = self.websocket_manager.broadcast_event(
                event_type='market_state_update',
                event_data=market_event.to_websocket_dict(),
                targeting_criteria=targeting_criteria
            )
            
            delivery_time = (time.time() - start_time) * 1000
            self.stats['market_updates_sent'] += 1
            
            logger.info(f"TIER-PATTERN-WS: Market state update ({market_event.regime.value}) "
                       f"delivered to {delivery_count} users in {delivery_time:.1f}ms")
            
            return delivery_count
            
        except Exception as e:
            logger.error(f"TIER-PATTERN-WS: Error broadcasting market state: {e}")
            return 0
    
    def generate_pattern_alert(self, user_id: str, pattern_event: TierPatternEvent, 
                             user_filters: Dict[str, Any]) -> PatternAlertEvent:
        """
        Generate pattern alert for specific user.
        
        Args:
            user_id: User to alert
            pattern_event: Pattern that triggered alert
            user_filters: User's subscription filters that matched
            
        Returns:
            PatternAlertEvent for the user
        """
        try:
            alert_id = f"alert_{user_id}_{pattern_event.event_id}"
            
            # Determine alert priority based on pattern confidence and user preferences
            if pattern_event.confidence >= 0.9:
                alert_priority = EventPriority.CRITICAL
            elif pattern_event.confidence >= 0.8:
                alert_priority = EventPriority.HIGH
            else:
                alert_priority = pattern_event.priority
            
            alert_event = PatternAlertEvent(
                alert_id=alert_id,
                user_id=user_id,
                timestamp=pattern_event.timestamp,
                pattern_event=pattern_event,
                user_filters=user_filters,
                alert_priority=alert_priority,
                delivery_channels=['websocket']
            )
            
            self.stats['alerts_generated'] += 1
            
            return alert_event
            
        except Exception as e:
            logger.error(f"TIER-PATTERN-WS: Error generating pattern alert: {e}")
            return None
    
    def broadcast_pattern_alert(self, alert_event: PatternAlertEvent) -> bool:
        """
        Broadcast pattern alert with priority routing for immediate delivery.
        
        Critical alerts use PRIORITY_FIRST strategy to bypass normal batching
        for sub-50ms delivery to ensure immediate user notification.
        
        Args:
            alert_event: PatternAlertEvent to deliver
            
        Returns:
            True if delivered successfully
        """
        try:
            start_time = time.time()
            
            # Enhanced targeting for alert-specific routing
            targeting_criteria = {
                'subscription_type': 'pattern_alerts',
                'user_id': alert_event.user_id,
                'alert_priority': alert_event.alert_priority.value,
                'bypass_batching': alert_event.alert_priority == EventPriority.CRITICAL,
                'immediate_delivery': True
            }
            
            # Use priority routing for alerts
            delivery_count = self.websocket_manager.broadcast_event(
                event_type='pattern_alert',
                event_data=alert_event.to_websocket_dict(),
                targeting_criteria=targeting_criteria
            )
            
            delivery_time = (time.time() - start_time) * 1000
            success = delivery_count > 0
            
            if success:
                if alert_event.alert_priority == EventPriority.CRITICAL:
                    self.stats['critical_alerts'] += 1
                
                logger.info(f"TIER-PATTERN-WS: Pattern alert {alert_event.alert_id} "
                           f"({alert_event.alert_priority.value}) delivered to user {alert_event.user_id} "
                           f"in {delivery_time:.1f}ms")
                           
                if delivery_time > 50 and alert_event.alert_priority == EventPriority.CRITICAL:
                    logger.warning(f"TIER-PATTERN-WS: Critical alert delivery took {delivery_time:.1f}ms (target: <50ms)")
                    
            else:
                logger.warning(f"TIER-PATTERN-WS: Pattern alert {alert_event.alert_id} not delivered (user offline?)")
            
            return success
            
        except Exception as e:
            logger.error(f"TIER-PATTERN-WS: Error broadcasting pattern alert: {e}")
            return False
    
    def get_user_tier_subscriptions(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user's tier pattern subscription details."""
        try:
            user_subscriptions = self.websocket_manager.get_user_subscriptions(user_id)
            tier_subscription = user_subscriptions.get('tier_patterns')
            
            if tier_subscription:
                return {
                    'subscription_type': tier_subscription.subscription_type,
                    'filters': tier_subscription.filters,
                    'active': tier_subscription.active,
                    'created_at': tier_subscription.created_at.isoformat(),
                    'last_activity': tier_subscription.last_activity.isoformat()
                }
            
            return None
            
        except Exception as e:
            logger.error(f"TIER-PATTERN-WS: Error getting user subscriptions: {e}")
            return None
    
    def get_tier_pattern_stats(self) -> Dict[str, Any]:
        """Get comprehensive tier pattern integration statistics with 4-layer performance metrics."""
        try:
            # Get base WebSocket manager stats
            ws_stats = self.websocket_manager.get_subscription_stats()
            
            # Get 4-layer architecture component stats
            index_stats = self.index_manager.get_performance_stats() if hasattr(self.index_manager, 'get_performance_stats') else {}
            broadcaster_stats = self.broadcaster.get_performance_stats() if hasattr(self.broadcaster, 'get_performance_stats') else {}
            router_stats = self.event_router.get_performance_stats() if hasattr(self.event_router, 'get_performance_stats') else {}
            
            # Calculate tier-specific metrics
            runtime_seconds = time.time() - self.stats['start_time']
            patterns_per_minute = (self.stats['patterns_broadcast'] / max(runtime_seconds / 60, 1))
            
            # Calculate performance ratios
            high_priority_ratio = (self.stats['high_priority_patterns'] / max(self.stats['patterns_broadcast'], 1)) * 100
            critical_alert_ratio = (self.stats['critical_alerts'] / max(self.stats['alerts_generated'], 1)) * 100
            
            return {
                # Tier-specific stats
                'tier_subscriptions': self.stats['tier_subscriptions'],
                'patterns_broadcast': self.stats['patterns_broadcast'],
                'market_updates_sent': self.stats['market_updates_sent'],
                'alerts_generated': self.stats['alerts_generated'],
                'high_priority_patterns': self.stats['high_priority_patterns'],
                'critical_alerts': self.stats['critical_alerts'],
                'patterns_per_minute': round(patterns_per_minute, 2),
                'last_pattern_time': self.stats['last_pattern_time'],
                
                # Performance metrics
                'high_priority_ratio_percent': round(high_priority_ratio, 1),
                'critical_alert_ratio_percent': round(critical_alert_ratio, 1),
                'routing_cache_hits': self.stats['routing_cache_hits'],
                'batch_efficiency_percent': round(self.stats['batch_efficiency'] * 100, 1),
                
                # 4-layer architecture stats
                'websocket_manager_stats': ws_stats,
                'index_manager_stats': index_stats,
                'broadcaster_stats': broadcaster_stats,
                'event_router_stats': router_stats,
                
                # Service metrics
                'runtime_seconds': round(runtime_seconds, 1),
                'service_uptime_hours': round(runtime_seconds / 3600, 1),
                'architecture_layers': 4,
                'performance_targets': {
                    'filtering_target_ms': 5,
                    'routing_target_ms': 20,
                    'delivery_target_ms': 100,
                    'total_target_ms': 125,
                    'concurrent_users_target': 500
                },
                'last_updated': time.time()
            }
            
        except Exception as e:
            logger.error(f"TIER-PATTERN-WS: Error getting statistics: {e}")
            return {
                'error': str(e),
                'last_updated': time.time()
            }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status for tier pattern integration."""
        try:
            stats = self.get_tier_pattern_stats()
            ws_health = self.websocket_manager.get_health_status()
            
            # Check tier pattern specific health
            current_time = time.time()
            last_pattern_age = (current_time - self.stats['last_pattern_time']) if self.stats['last_pattern_time'] else None
            
            if ws_health['status'] == 'error':
                status = 'error'
                message = f"WebSocket manager unhealthy: {ws_health['message']}"
            elif self.stats['patterns_broadcast'] == 0 and current_time - self.stats['start_time'] > 600:  # 10 minutes
                status = 'warning'
                message = "No patterns broadcast in last 10 minutes"
            elif last_pattern_age and last_pattern_age > 3600:  # 1 hour
                status = 'warning'
                message = f"Last pattern received {last_pattern_age/60:.0f} minutes ago"
            else:
                status = 'healthy'
                message = f"Tier pattern integration healthy with {self.stats['tier_subscriptions']} subscriptions"
            
            return {
                'service': 'tier_pattern_websocket_integration',
                'status': status,
                'message': message,
                'timestamp': current_time,
                'stats': stats,
                'websocket_health': ws_health
            }
            
        except Exception as e:
            logger.error(f"TIER-PATTERN-WS: Error getting health status: {e}")
            return {
                'service': 'tier_pattern_websocket_integration',
                'status': 'error',
                'message': f"Health check failed: {str(e)}",
                'timestamp': time.time()
            }

# Sprint 25+ High-Level API Functions

class TierPatternAPIBuilder:
    """
    Builder pattern for creating tier pattern integrations with 4-layer architecture.
    
    Provides fluent API for Sprint 25+ features to easily configure
    WebSocket integrations with optimal performance settings.
    """
    
    def __init__(self, websocket_manager: UniversalWebSocketManager):
        """Initialize API builder with WebSocket manager."""
        self.websocket_manager = websocket_manager
        self.integration = None
    
    def with_performance_optimization(self) -> 'TierPatternAPIBuilder':
        """Enable performance optimization features."""
        if not self.integration:
            self.integration = TierPatternWebSocketIntegration(self.websocket_manager)
        
        # Configure additional performance routing rules
        try:
            # Ultra-high confidence patterns - immediate delivery
            self.integration.event_router.add_routing_rule(
                event_type='tier_pattern',
                conditions={'confidence': {'min': 0.95}},
                strategy='PRIORITY_FIRST',
                destinations=['ultra_confidence_room'],
                bypass_batching=True,
                description='Ultra-high confidence patterns bypass batching'
            )
            
            # Market hour filtering optimization
            self.integration.event_router.add_routing_rule(
                event_type='tier_pattern',
                conditions={'market_hours_only': True},
                content_transformation=self.integration._enrich_pattern_with_market_context,
                description='Market hours patterns get enhanced context'
            )
            
        except Exception as e:
            logger.warning(f\"TIER-API-BUILDER: Performance optimization setup warning: {e}\")\n            
        return self
    
    def with_real_time_alerts(self) -> 'TierPatternAPIBuilder':
        \"\"\"Enable real-time alert capabilities.\"\"\"
        if not self.integration:
            self.integration = TierPatternWebSocketIntegration(self.websocket_manager)
        
        # Configure alert-specific routing
        try:
            # Critical alert fast-path routing
            self.integration.event_router.add_routing_rule(
                event_type='pattern_alert',
                conditions={'alert_priority': ['CRITICAL']},
                strategy='PRIORITY_FIRST',
                bypass_batching=True,
                max_latency_ms=25,  # Ultra-fast delivery
                description='Critical alerts get sub-25ms delivery'
            )
            
        except Exception as e:
            logger.warning(f\"TIER-API-BUILDER: Real-time alerts setup warning: {e}\")\n            \n        return self
    
    def with_market_insights(self) -> 'TierPatternAPIBuilder':
        \"\"\"Enable market insights and regime change notifications.\"\"\"
        if not self.integration:
            self.integration = TierPatternWebSocketIntegration(self.websocket_manager)
            \n        # Market insights are already configured in _setup_tier_pattern_routing_rules\n        logger.info(\"TIER-API-BUILDER: Market insights enabled\")\n        return self
    
    def build(self) -> TierPatternWebSocketIntegration:
        \"\"\"Build and return the configured tier pattern integration.\"\"\"
        if not self.integration:
            self.integration = TierPatternWebSocketIntegration(self.websocket_manager)
        
        logger.info(\"TIER-API-BUILDER: Tier pattern integration built successfully\")\n        return self.integration

def create_tier_pattern_integration(websocket_manager: UniversalWebSocketManager,
                                   performance_mode: bool = True,
                                   real_time_alerts: bool = True,
                                   market_insights: bool = True) -> TierPatternWebSocketIntegration:
    \"\"\"
    Create fully-configured tier pattern integration for Sprint 25+ features.
    
    Args:
        websocket_manager: UniversalWebSocketManager with 4-layer architecture
        performance_mode: Enable performance optimizations
        real_time_alerts: Enable real-time alert capabilities
        market_insights: Enable market regime insights
        
    Returns:
        Configured TierPatternWebSocketIntegration
        
    Example:
        # Create optimized integration for production use
        integration = create_tier_pattern_integration(
            websocket_manager=universal_ws_manager,
            performance_mode=True,
            real_time_alerts=True,
            market_insights=True
        )
        
        # Subscribe user to high-confidence patterns
        preferences = create_high_confidence_subscription(['AAPL', 'TSLA'])
        integration.subscribe_user_to_tier_patterns('user123', preferences)
    \"\"\"
    builder = TierPatternAPIBuilder(websocket_manager)
    
    if performance_mode:
        builder = builder.with_performance_optimization()
    
    if real_time_alerts:
        builder = builder.with_real_time_alerts()
    
    if market_insights:
        builder = builder.with_market_insights()
    
    return builder.build()

# Convenience functions for easy integration

def create_daily_pattern_subscription(symbols: List[str], 
                                    confidence_min: float = 0.7) -> TierSubscriptionPreferences:
    \"\"\"Create subscription preferences for daily patterns only.\"\"\"
    return TierSubscriptionPreferences(
        pattern_types=[],  # All patterns
        symbols=symbols,
        tiers=[PatternTier.DAILY],
        confidence_min=confidence_min,
        priority_min=EventPriority.MEDIUM
    )

def create_high_confidence_subscription(symbols: List[str]) -> TierSubscriptionPreferences:
    \"\"\"Create subscription for high-confidence patterns across all tiers.\"\"\"
    return TierSubscriptionPreferences(
        pattern_types=[],  # All patterns
        symbols=symbols,
        tiers=[PatternTier.DAILY, PatternTier.INTRADAY, PatternTier.COMBO],
        confidence_min=0.8,
        priority_min=EventPriority.HIGH
    )

def create_specific_pattern_subscription(pattern_types: List[str], 
                                       symbols: List[str]) -> TierSubscriptionPreferences:
    \"\"\"Create subscription for specific patterns and symbols.\"\"\"
    return TierSubscriptionPreferences(
        pattern_types=pattern_types,
        symbols=symbols,
        tiers=[PatternTier.DAILY, PatternTier.INTRADAY, PatternTier.COMBO],
        confidence_min=0.6,
        priority_min=EventPriority.MEDIUM
    )

def create_intraday_scalping_subscription(symbols: List[str]) -> TierSubscriptionPreferences:
    \"\"\"Create high-frequency subscription for intraday scalping patterns.\"\"\"
    return TierSubscriptionPreferences(
        pattern_types=['ScalpingBO', 'MomentumSurge', 'QuickReversal'],
        symbols=symbols,
        tiers=[PatternTier.INTRADAY],
        confidence_min=0.75,
        priority_min=EventPriority.HIGH,
        max_events_per_hour=200,  # Higher frequency for scalping
        enable_market_hours_only=True
    )

def create_swing_trading_subscription(symbols: List[str]) -> TierSubscriptionPreferences:
    \"\"\"Create subscription optimized for swing trading patterns.\"\"\"
    return TierSubscriptionPreferences(
        pattern_types=['BreakoutBO', 'TrendReversal', 'SupportBreak', 'ResistanceBreak'],
        symbols=symbols,
        tiers=[PatternTier.DAILY, PatternTier.COMBO],
        confidence_min=0.7,
        priority_min=EventPriority.MEDIUM,
        max_events_per_hour=25,  # Lower frequency for swing trading
        enable_market_hours_only=False  # Include after-hours moves
    )

def create_risk_monitoring_subscription(symbols: List[str]) -> TierSubscriptionPreferences:
    \"\"\"Create subscription for risk monitoring and market stress patterns.\"\"\"
    return TierSubscriptionPreferences(
        pattern_types=['SurgeDetection', 'VolatilitySpike', 'LiquidityDrop'],
        symbols=symbols,
        tiers=[PatternTier.DAILY, PatternTier.INTRADAY, PatternTier.COMBO],
        confidence_min=0.6,  # Lower threshold for risk detection
        priority_min=EventPriority.HIGH,  # Risk patterns are high priority
        max_events_per_hour=100,
        enable_market_hours_only=False  # Monitor 24/7 for risk
    )