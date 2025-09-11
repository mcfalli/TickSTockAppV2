"""
Event Router
Sprint 25 Day 4 Implementation: Intelligent message routing for sophisticated WebSocket event distribution.

Advanced routing system for real-time financial data that provides:
- Content-based routing with pattern analysis
- Multi-destination routing with transformation
- Route optimization and caching
- Event enrichment and filtering
- Performance monitoring and adaptive routing

Designed to work with ScalableBroadcaster (Day 3) and SubscriptionIndexManager (Day 2)
for enterprise-grade event distribution supporting 500+ concurrent users.
"""

import logging
import time
import threading
from typing import Dict, Any, Set, List, Optional, Callable, Tuple
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
import json
import hashlib
from concurrent.futures import ThreadPoolExecutor

# Import Day 3 broadcasting infrastructure
from src.infrastructure.websocket.scalable_broadcaster import ScalableBroadcaster, DeliveryPriority

logger = logging.getLogger(__name__)

class RoutingStrategy(Enum):
    """Event routing strategies."""
    BROADCAST_ALL = "broadcast_all"          # Send to all matching users
    ROUND_ROBIN = "round_robin"              # Distribute across users
    PRIORITY_FIRST = "priority_first"        # Send to highest priority users first
    LOAD_BALANCED = "load_balanced"          # Balance based on user load
    CONTENT_BASED = "content_based"          # Route based on content analysis

class EventCategory(Enum):
    """Event categories for intelligent routing."""
    PATTERN_ALERT = "pattern_alert"          # Pattern detection events
    MARKET_DATA = "market_data"              # Real-time market updates
    SYSTEM_HEALTH = "system_health"          # System status events
    USER_ACTION = "user_action"              # User-triggered events
    BACKTEST_RESULT = "backtest_result"      # Backtesting results
    TIER_SPECIFIC = "tier_specific"          # Tier-based pattern events

@dataclass
class RoutingRule:
    """Individual routing rule configuration."""
    rule_id: str
    name: str
    description: str
    
    # Matching criteria
    event_type_patterns: List[str]           # Event type regex patterns
    content_filters: Dict[str, Any]          # Content-based filters
    user_criteria: Dict[str, Any]            # User-based criteria
    
    # Routing configuration
    strategy: RoutingStrategy
    destinations: List[str]                  # Target destinations/rooms
    priority: DeliveryPriority
    
    # Transformation rules
    content_transformer: Optional[Callable] = None
    user_filter: Optional[Callable] = None
    
    # Performance settings
    max_users_per_route: int = 1000
    cache_ttl_seconds: int = 300
    enabled: bool = True
    
    # Statistics
    messages_routed: int = 0
    last_used: float = field(default_factory=time.time)
    
    def matches_event(self, event_type: str, event_data: Dict[str, Any]) -> bool:
        """Check if routing rule matches the event."""
        try:
            if not self.enabled:
                return False
            
            # Check event type patterns
            import re
            type_match = any(re.match(pattern, event_type) for pattern in self.event_type_patterns)
            if not type_match:
                return False
            
            # Check content filters
            for key, expected_value in self.content_filters.items():
                if key not in event_data:
                    return False
                
                actual_value = event_data[key]
                
                # Support different matching types
                if isinstance(expected_value, dict):
                    if 'min' in expected_value and actual_value < expected_value['min']:
                        return False
                    if 'max' in expected_value and actual_value > expected_value['max']:
                        return False
                    if 'equals' in expected_value and actual_value != expected_value['equals']:
                        return False
                    if 'contains' in expected_value and expected_value['contains'] not in str(actual_value):
                        return False
                elif actual_value != expected_value:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"EVENT-ROUTER: Error matching rule {self.rule_id}: {e}")
            return False
    
    def record_usage(self):
        """Record usage statistics."""
        self.messages_routed += 1
        self.last_used = time.time()

@dataclass
class RoutingResult:
    """Result of event routing operation."""
    event_id: str
    matched_rules: List[str]                 # Rule IDs that matched
    destinations: Dict[str, Set[str]]        # destination -> user_ids
    transformations_applied: List[str]       # Transformation functions applied
    routing_time_ms: float                   # Time taken for routing
    total_users: int                         # Total users routed to
    cache_hit: bool = False                  # Whether route was cached

@dataclass
class RouterStats:
    """Performance statistics for event routing."""
    total_events: int = 0
    events_routed: int = 0
    events_dropped: int = 0
    
    # Performance metrics
    avg_routing_time_ms: float = 0.0
    max_routing_time_ms: float = 0.0
    cache_hit_rate_percent: float = 0.0
    
    # Rule effectiveness
    rules_matched_per_event: float = 0.0
    most_used_rule: str = ""
    
    # Error tracking
    routing_errors: int = 0
    transformation_errors: int = 0
    
    def record_routing(self, routing_time_ms: float, rules_matched: int, cache_hit: bool):
        """Record routing performance metrics."""
        self.total_events += 1
        self.events_routed += 1
        
        # Update timing metrics
        if self.total_events == 1:
            self.avg_routing_time_ms = routing_time_ms
        else:
            self.avg_routing_time_ms = (
                (self.avg_routing_time_ms * (self.total_events - 1) + routing_time_ms) /
                self.total_events
            )
        
        self.max_routing_time_ms = max(self.max_routing_time_ms, routing_time_ms)
        
        # Update rule matching
        if self.total_events == 1:
            self.rules_matched_per_event = rules_matched
        else:
            self.rules_matched_per_event = (
                (self.rules_matched_per_event * (self.total_events - 1) + rules_matched) /
                self.total_events
            )
        
        # Update cache hit rate
        current_hits = self.cache_hit_rate_percent * (self.total_events - 1) / 100.0
        if cache_hit:
            current_hits += 1
        self.cache_hit_rate_percent = (current_hits / self.total_events) * 100.0

class EventRouter:
    """
    Intelligent event routing system for sophisticated WebSocket event distribution.
    
    Provides advanced routing capabilities for real-time financial data:
    - Content-based routing with pattern analysis
    - Multi-destination routing with user targeting
    - Route optimization and intelligent caching
    - Event transformation and enrichment
    - Performance monitoring and adaptive routing
    
    Integrates with ScalableBroadcaster for efficient delivery and SubscriptionIndexManager
    for high-performance user filtering.
    """
    
    def __init__(self, scalable_broadcaster: ScalableBroadcaster,
                 cache_size: int = 1000, enable_caching: bool = True):
        """Initialize Event Router."""
        
        self.scalable_broadcaster = scalable_broadcaster
        self.cache_size = cache_size
        self.enable_caching = enable_caching
        
        # Routing configuration
        self.routing_rules: Dict[str, RoutingRule] = {}
        self.rule_categories: Dict[EventCategory, List[str]] = defaultdict(list)
        
        # Route caching system
        self.route_cache: Dict[str, Tuple[RoutingResult, float]] = {}  # cache_key -> (result, timestamp)
        self.cache_access_order: deque = deque()  # LRU tracking
        
        # Performance optimization
        self.routing_executor = ThreadPoolExecutor(max_workers=5, thread_name_prefix="event-router")
        
        # Statistics and monitoring
        self.stats = RouterStats()
        self.start_time = time.time()
        
        # Thread safety
        self.routing_lock = threading.RLock()
        self.cache_lock = threading.Lock()
        
        # Built-in transformers
        self._register_built_in_transformers()
        
        logger.info("EVENT-ROUTER: Intelligent event router initialized")
    
    def add_routing_rule(self, rule: RoutingRule) -> bool:
        """Add routing rule to the router."""
        try:
            with self.routing_lock:
                self.routing_rules[rule.rule_id] = rule
                
                # Categorize rule for optimization
                self._categorize_rule(rule)
                
                logger.info(f"EVENT-ROUTER: Added routing rule {rule.rule_id}: {rule.name}")
                return True
                
        except Exception as e:
            logger.error(f"EVENT-ROUTER: Error adding routing rule {rule.rule_id}: {e}")
            return False
    
    def remove_routing_rule(self, rule_id: str) -> bool:
        """Remove routing rule from router."""
        try:
            with self.routing_lock:
                if rule_id in self.routing_rules:
                    rule = self.routing_rules[rule_id]
                    del self.routing_rules[rule_id]
                    
                    # Remove from categories
                    self._remove_from_categories(rule_id)
                    
                    # Clear related cache entries
                    self._clear_cache_for_rule(rule_id)
                    
                    logger.info(f"EVENT-ROUTER: Removed routing rule {rule_id}")
                    return True
                
                return False
                
        except Exception as e:
            logger.error(f"EVENT-ROUTER: Error removing routing rule {rule_id}: {e}")
            return False
    
    def route_event(self, event_type: str, event_data: Dict[str, Any], 
                   user_context: Dict[str, Any] = None) -> RoutingResult:
        """
        Route event to appropriate destinations with intelligent routing.
        
        Args:
            event_type: Type of event to route
            event_data: Event payload
            user_context: Optional user context for routing decisions
            
        Returns:
            RoutingResult with routing details and performance metrics
        """
        try:
            start_time = time.time()
            event_id = f"{event_type}_{int(time.time() * 1000)}"
            
            # Check route cache first
            cache_key = self._generate_cache_key(event_type, event_data, user_context)
            cached_result = self._get_cached_route(cache_key)
            
            if cached_result:
                # Use cached routing result
                routing_time_ms = (time.time() - start_time) * 1000
                self.stats.record_routing(routing_time_ms, len(cached_result.matched_rules), True)
                
                # Execute cached routing
                self._execute_routing(cached_result, event_type, event_data)
                
                return cached_result
            
            # Perform intelligent routing
            routing_result = self._perform_intelligent_routing(
                event_id, event_type, event_data, user_context
            )
            
            # Cache routing result if beneficial
            if self.enable_caching and routing_result.total_users > 5:
                self._cache_routing_result(cache_key, routing_result)
            
            # Execute routing
            self._execute_routing(routing_result, event_type, event_data)
            
            # Record performance metrics
            routing_time_ms = (time.time() - start_time) * 1000
            self.stats.record_routing(routing_time_ms, len(routing_result.matched_rules), False)
            
            routing_result.routing_time_ms = routing_time_ms
            
            logger.debug(f"EVENT-ROUTER: Routed {event_type} to {routing_result.total_users} users "
                        f"via {len(routing_result.matched_rules)} rules in {routing_time_ms:.1f}ms")
            
            return routing_result
            
        except Exception as e:
            logger.error(f"EVENT-ROUTER: Error routing event {event_type}: {e}")
            self.stats.routing_errors += 1
            
            # Return empty routing result on error
            return RoutingResult(
                event_id=f"error_{int(time.time() * 1000)}",
                matched_rules=[],
                destinations={},
                transformations_applied=[],
                routing_time_ms=(time.time() - start_time) * 1000,
                total_users=0
            )
    
    def _perform_intelligent_routing(self, event_id: str, event_type: str, 
                                   event_data: Dict[str, Any], 
                                   user_context: Dict[str, Any]) -> RoutingResult:
        """Perform intelligent routing analysis."""
        try:
            with self.routing_lock:
                matched_rules = []
                destinations = defaultdict(set)
                transformations_applied = []
                
                # Find matching routing rules
                for rule_id, rule in self.routing_rules.items():
                    if rule.matches_event(event_type, event_data):
                        matched_rules.append(rule_id)
                        rule.record_usage()
                        
                        # Apply content transformation if configured
                        transformed_data = event_data
                        if rule.content_transformer:
                            try:
                                transformed_data = rule.content_transformer(event_data)
                                transformations_applied.append(f"{rule_id}_content_transform")
                            except Exception as e:
                                logger.error(f"EVENT-ROUTER: Content transformation error in rule {rule_id}: {e}")
                                self.stats.transformation_errors += 1
                        
                        # Apply routing strategy
                        rule_destinations = self._apply_routing_strategy(
                            rule, event_type, transformed_data, user_context
                        )
                        
                        # Merge destinations
                        for dest, users in rule_destinations.items():
                            destinations[dest].update(users)
                
                # Calculate total users
                total_users = sum(len(users) for users in destinations.values())
                
                return RoutingResult(
                    event_id=event_id,
                    matched_rules=matched_rules,
                    destinations=dict(destinations),
                    transformations_applied=transformations_applied,
                    routing_time_ms=0,  # Set by caller
                    total_users=total_users
                )
                
        except Exception as e:
            logger.error(f"EVENT-ROUTER: Error in intelligent routing: {e}")
            return RoutingResult(
                event_id=event_id,
                matched_rules=[],
                destinations={},
                transformations_applied=[],
                routing_time_ms=0,
                total_users=0
            )
    
    def _apply_routing_strategy(self, rule: RoutingRule, event_type: str,
                              event_data: Dict[str, Any], 
                              user_context: Dict[str, Any]) -> Dict[str, Set[str]]:
        """Apply specific routing strategy for a rule."""
        try:
            destinations = {}
            
            if rule.strategy == RoutingStrategy.BROADCAST_ALL:
                # Broadcast to all matching users (default behavior)
                destinations = self._get_broadcast_destinations(rule, event_type, event_data)
            
            elif rule.strategy == RoutingStrategy.CONTENT_BASED:
                # Route based on content analysis
                destinations = self._get_content_based_destinations(rule, event_type, event_data)
            
            elif rule.strategy == RoutingStrategy.PRIORITY_FIRST:
                # Send to highest priority users first
                destinations = self._get_priority_destinations(rule, event_type, event_data)
            
            elif rule.strategy == RoutingStrategy.LOAD_BALANCED:
                # Balance load across users
                destinations = self._get_load_balanced_destinations(rule, event_type, event_data)
            
            else:
                # Default to broadcast
                destinations = self._get_broadcast_destinations(rule, event_type, event_data)
            
            return destinations
            
        except Exception as e:
            logger.error(f"EVENT-ROUTER: Error applying routing strategy {rule.strategy}: {e}")
            return {}
    
    def _get_broadcast_destinations(self, rule: RoutingRule, event_type: str, 
                                  event_data: Dict[str, Any]) -> Dict[str, Set[str]]:
        """Get destinations for broadcast routing."""
        destinations = {}
        
        # Use rule destinations or derive from event data
        if rule.destinations:
            for dest in rule.destinations:
                if dest.startswith('room_'):
                    destinations[dest] = set()  # Room-based broadcast
                elif dest.startswith('user_'):
                    user_id = dest[5:]  # Extract user ID
                    destinations[f"user_{user_id}"] = {user_id}
        else:
            # Default room-based broadcasting
            destinations['default_room'] = set()
        
        return destinations
    
    def _get_content_based_destinations(self, rule: RoutingRule, event_type: str,
                                      event_data: Dict[str, Any]) -> Dict[str, Set[str]]:
        """Get destinations based on content analysis."""
        destinations = {}
        
        # Analyze content for routing decisions
        if 'symbol' in event_data and 'pattern_type' in event_data:
            # Pattern-based routing
            symbol = event_data['symbol']
            pattern = event_data['pattern_type']
            room_name = f"pattern_{pattern}_{symbol}"
            destinations[room_name] = set()
        
        elif 'tier' in event_data:
            # Tier-based routing
            tier = event_data['tier']
            room_name = f"tier_{tier}"
            destinations[room_name] = set()
        
        else:
            # Default content routing
            content_hash = hashlib.md5(str(event_data).encode()).hexdigest()[:8]
            room_name = f"content_{content_hash}"
            destinations[room_name] = set()
        
        return destinations
    
    def _get_priority_destinations(self, rule: RoutingRule, event_type: str,
                                 event_data: Dict[str, Any]) -> Dict[str, Set[str]]:
        """Get destinations with priority-based routing."""
        # For now, implement as broadcast with priority
        # Future enhancement: integrate with user priority systems
        return self._get_broadcast_destinations(rule, event_type, event_data)
    
    def _get_load_balanced_destinations(self, rule: RoutingRule, event_type: str,
                                      event_data: Dict[str, Any]) -> Dict[str, Set[str]]:
        """Get destinations with load balancing."""
        # For now, implement as broadcast
        # Future enhancement: integrate with load balancing metrics
        return self._get_broadcast_destinations(rule, event_type, event_data)
    
    def _execute_routing(self, routing_result: RoutingResult, event_type: str, 
                        event_data: Dict[str, Any]):
        """Execute the routing result through ScalableBroadcaster."""
        try:
            for destination, user_ids in routing_result.destinations.items():
                if user_ids:
                    # Route to specific users
                    self.scalable_broadcaster.broadcast_to_users(
                        event_type=event_type,
                        event_data=event_data,
                        user_ids=user_ids,
                        priority=DeliveryPriority.MEDIUM  # Default priority
                    )
                else:
                    # Route to room
                    self.scalable_broadcaster.broadcast_to_room(
                        room_name=destination,
                        event_type=event_type,
                        event_data=event_data,
                        priority=DeliveryPriority.MEDIUM
                    )
                    
        except Exception as e:
            logger.error(f"EVENT-ROUTER: Error executing routing: {e}")
    
    def _generate_cache_key(self, event_type: str, event_data: Dict[str, Any],
                           user_context: Dict[str, Any]) -> str:
        """Generate cache key for routing result."""
        # Create deterministic cache key
        key_data = {
            'event_type': event_type,
            'content_hash': hashlib.md5(str(sorted(event_data.items())).encode()).hexdigest()[:16],
            'context_hash': hashlib.md5(str(sorted((user_context or {}).items())).encode()).hexdigest()[:8]
        }
        
        return f"route_{key_data['event_type']}_{key_data['content_hash']}_{key_data['context_hash']}"
    
    def _get_cached_route(self, cache_key: str) -> Optional[RoutingResult]:
        """Get cached routing result if available and valid."""
        try:
            with self.cache_lock:
                if cache_key in self.route_cache:
                    result, timestamp = self.route_cache[cache_key]
                    
                    # Check if cache entry is still valid
                    if time.time() - timestamp < 300:  # 5 minute TTL
                        # Update LRU order
                        if cache_key in self.cache_access_order:
                            self.cache_access_order.remove(cache_key)
                        self.cache_access_order.append(cache_key)
                        
                        # Mark as cache hit
                        result.cache_hit = True
                        return result
                    else:
                        # Remove expired entry
                        del self.route_cache[cache_key]
                        if cache_key in self.cache_access_order:
                            self.cache_access_order.remove(cache_key)
                
                return None
                
        except Exception as e:
            logger.error(f"EVENT-ROUTER: Error getting cached route: {e}")
            return None
    
    def _cache_routing_result(self, cache_key: str, routing_result: RoutingResult):
        """Cache routing result for future use."""
        try:
            with self.cache_lock:
                # Implement LRU cache with size limit
                while len(self.route_cache) >= self.cache_size:
                    oldest_key = self.cache_access_order.popleft()
                    if oldest_key in self.route_cache:
                        del self.route_cache[oldest_key]
                
                # Cache the result
                self.route_cache[cache_key] = (routing_result, time.time())
                self.cache_access_order.append(cache_key)
                
        except Exception as e:
            logger.error(f"EVENT-ROUTER: Error caching routing result: {e}")
    
    def _categorize_rule(self, rule: RoutingRule):
        """Categorize rule for optimization."""
        # Simple categorization based on event type patterns
        for pattern in rule.event_type_patterns:
            if 'pattern' in pattern.lower():
                self.rule_categories[EventCategory.PATTERN_ALERT].append(rule.rule_id)
            elif 'market' in pattern.lower():
                self.rule_categories[EventCategory.MARKET_DATA].append(rule.rule_id)
            elif 'health' in pattern.lower():
                self.rule_categories[EventCategory.SYSTEM_HEALTH].append(rule.rule_id)
            elif 'tier' in pattern.lower():
                self.rule_categories[EventCategory.TIER_SPECIFIC].append(rule.rule_id)
    
    def _remove_from_categories(self, rule_id: str):
        """Remove rule from all categories."""
        for category_rules in self.rule_categories.values():
            if rule_id in category_rules:
                category_rules.remove(rule_id)
    
    def _clear_cache_for_rule(self, rule_id: str):
        """Clear cache entries that might be affected by rule removal."""
        # For simplicity, clear entire cache when rules change
        with self.cache_lock:
            self.route_cache.clear()
            self.cache_access_order.clear()
    
    def _register_built_in_transformers(self):
        """Register built-in content transformers."""
        # Built-in transformers can be added here
        pass
    
    def get_routing_stats(self) -> Dict[str, Any]:
        """Get comprehensive routing statistics."""
        try:
            with self.routing_lock:
                runtime_seconds = time.time() - self.start_time
                
                # Calculate rule usage statistics
                rule_usage = {}
                most_used_rule = ""
                max_usage = 0
                
                for rule_id, rule in self.routing_rules.items():
                    rule_usage[rule_id] = rule.messages_routed
                    if rule.messages_routed > max_usage:
                        max_usage = rule.messages_routed
                        most_used_rule = rule_id
                
                return {
                    # Event metrics
                    'total_events': self.stats.total_events,
                    'events_routed': self.stats.events_routed,
                    'events_dropped': self.stats.events_dropped,
                    'events_per_second': round(self.stats.total_events / max(runtime_seconds, 1), 2),
                    
                    # Performance metrics
                    'avg_routing_time_ms': round(self.stats.avg_routing_time_ms, 2),
                    'max_routing_time_ms': round(self.stats.max_routing_time_ms, 2),
                    'cache_hit_rate_percent': round(self.stats.cache_hit_rate_percent, 1),
                    
                    # Rule effectiveness
                    'total_rules': len(self.routing_rules),
                    'avg_rules_matched_per_event': round(self.stats.rules_matched_per_event, 1),
                    'most_used_rule': most_used_rule,
                    'rule_usage': rule_usage,
                    
                    # Cache metrics
                    'cache_size': len(self.route_cache),
                    'cache_capacity': self.cache_size,
                    'cache_utilization_percent': round((len(self.route_cache) / self.cache_size) * 100, 1),
                    
                    # Error tracking
                    'routing_errors': self.stats.routing_errors,
                    'transformation_errors': self.stats.transformation_errors,
                    
                    # System metrics
                    'runtime_seconds': round(runtime_seconds, 1),
                    'uptime_hours': round(runtime_seconds / 3600, 1),
                    'last_updated': time.time()
                }
                
        except Exception as e:
            logger.error(f"EVENT-ROUTER: Error getting routing stats: {e}")
            return {'error': str(e), 'timestamp': time.time()}
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status for monitoring."""
        try:
            stats = self.get_routing_stats()
            
            # Determine health status
            if stats.get('routing_errors', 0) > 10:
                status = 'error'
                message = f"High routing error rate: {stats['routing_errors']} errors"
            elif stats.get('avg_routing_time_ms', 0) > 50:
                status = 'warning'
                message = f"Slow routing performance: {stats['avg_routing_time_ms']:.1f}ms average"
            elif stats.get('cache_hit_rate_percent', 100) < 30 and stats.get('total_events', 0) > 100:
                status = 'warning'
                message = f"Low cache effectiveness: {stats['cache_hit_rate_percent']:.1f}% hit rate"
            else:
                status = 'healthy'
                message = f"Routing healthy - {stats['avg_routing_time_ms']:.1f}ms avg, {stats['total_rules']} rules"
            
            return {
                'service': 'event_router',
                'status': status,
                'message': message,
                'timestamp': time.time(),
                'stats': stats,
                'performance_targets': {
                    'routing_time_target_ms': 20.0,
                    'cache_hit_rate_target_percent': 50.0,
                    'error_rate_target': 5
                }
            }
            
        except Exception as e:
            logger.error(f"EVENT-ROUTER: Error getting health status: {e}")
            return {
                'service': 'event_router',
                'status': 'error',
                'message': f"Health check failed: {str(e)}",
                'timestamp': time.time()
            }
    
    def optimize_performance(self) -> Dict[str, Any]:
        """Optimize routing performance."""
        try:
            optimization_results = {
                'cache_cleaned': 0,
                'rules_optimized': 0,
                'performance_improved': False,
                'optimization_timestamp': time.time()
            }
            
            # Clean expired cache entries
            current_time = time.time()
            with self.cache_lock:
                expired_keys = []
                for cache_key, (result, timestamp) in self.route_cache.items():
                    if current_time - timestamp > 300:  # 5 minutes
                        expired_keys.append(cache_key)
                
                for key in expired_keys:
                    del self.route_cache[key]
                    if key in self.cache_access_order:
                        self.cache_access_order.remove(key)
                
                optimization_results['cache_cleaned'] = len(expired_keys)
            
            # Optimize rule ordering (most used rules first)
            with self.routing_lock:
                rules_by_usage = sorted(
                    self.routing_rules.items(),
                    key=lambda x: x[1].messages_routed,
                    reverse=True
                )
                
                optimized_rules = {}
                for rule_id, rule in rules_by_usage:
                    optimized_rules[rule_id] = rule
                
                self.routing_rules = optimized_rules
                optimization_results['rules_optimized'] = len(optimized_rules)
            
            logger.info(f"EVENT-ROUTER: Performance optimization complete - "
                       f"{optimization_results['cache_cleaned']} cache entries cleaned, "
                       f"{optimization_results['rules_optimized']} rules optimized")
            
            return optimization_results
            
        except Exception as e:
            logger.error(f"EVENT-ROUTER: Error optimizing performance: {e}")
            return {'error': str(e), 'timestamp': time.time()}
    
    def shutdown(self):
        """Graceful shutdown of event router."""
        try:
            logger.info("EVENT-ROUTER: Starting graceful shutdown...")
            
            # Shutdown routing executor
            self.routing_executor.shutdown(wait=True, timeout=5)
            
            # Clear caches
            with self.cache_lock:
                self.route_cache.clear()
                self.cache_access_order.clear()
            
            logger.info("EVENT-ROUTER: Graceful shutdown complete")
            
        except Exception as e:
            logger.error(f"EVENT-ROUTER: Error during shutdown: {e}")

# Convenience functions for creating common routing rules

def create_pattern_routing_rule(rule_id: str, pattern_types: List[str], 
                               symbols: List[str] = None) -> RoutingRule:
    """Create routing rule for pattern events."""
    return RoutingRule(
        rule_id=rule_id,
        name=f"Pattern routing: {', '.join(pattern_types)}",
        description=f"Routes pattern events for types: {pattern_types}",
        event_type_patterns=[r".*pattern.*", r"tier_pattern"],
        content_filters={
            'pattern_type': {'contains': '|'.join(pattern_types)} if len(pattern_types) > 1 else pattern_types[0]
        } if pattern_types else {},
        user_criteria={},
        strategy=RoutingStrategy.CONTENT_BASED,
        destinations=[],
        priority=DeliveryPriority.HIGH
    )

def create_market_data_routing_rule(rule_id: str, symbols: List[str]) -> RoutingRule:
    """Create routing rule for market data events."""
    return RoutingRule(
        rule_id=rule_id,
        name=f"Market data routing: {', '.join(symbols)}",
        description=f"Routes market data for symbols: {symbols}",
        event_type_patterns=[r"market.*", r".*data.*"],
        content_filters={
            'symbol': {'contains': '|'.join(symbols)} if len(symbols) > 1 else symbols[0]
        } if symbols else {},
        user_criteria={},
        strategy=RoutingStrategy.BROADCAST_ALL,
        destinations=[],
        priority=DeliveryPriority.MEDIUM
    )

def create_tier_routing_rule(rule_id: str, tier: str) -> RoutingRule:
    """Create routing rule for tier-specific events."""
    return RoutingRule(
        rule_id=rule_id,
        name=f"Tier routing: {tier}",
        description=f"Routes tier-specific events for tier: {tier}",
        event_type_patterns=[r"tier.*", r".*tier.*"],
        content_filters={'tier': tier},
        user_criteria={},
        strategy=RoutingStrategy.CONTENT_BASED,
        destinations=[f"tier_{tier}"],
        priority=DeliveryPriority.MEDIUM
    )