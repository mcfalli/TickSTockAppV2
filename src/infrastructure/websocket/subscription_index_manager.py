"""
Subscription Index Manager
Sprint 25 Day 2 Implementation: High-performance subscription indexing for <5ms user filtering.

Efficient indexing system for fast user lookup based on event criteria across multiple dimensions.
Supports complex filtering for tier patterns, market insights, and user preferences with 
O(log n) lookup performance targeting 1000+ active subscriptions.
"""

import logging
import time
import threading
from typing import Dict, Any, Set, List, Optional, Tuple
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum

# Import subscription models
from src.core.models.websocket_models import UserSubscription

logger = logging.getLogger(__name__)

class IndexType(Enum):
    """Types of subscription indexes for efficient filtering."""
    PATTERN_TYPE = "pattern_type"
    SYMBOL = "symbol"
    TIER = "tier"
    MARKET_REGIME = "market_regime"
    SUBSCRIPTION_TYPE = "subscription_type"
    CONFIDENCE_RANGE = "confidence_range"
    PRIORITY_LEVEL = "priority_level"
    USER_TAG = "user_tag"

@dataclass
class IndexStats:
    """Statistics for subscription index performance."""
    total_users: int = 0
    total_indexes: int = 0
    index_sizes: Dict[str, int] = field(default_factory=dict)
    
    # Performance metrics
    lookup_count: int = 0
    total_lookup_time_ms: float = 0.0
    avg_lookup_time_ms: float = 0.0
    max_lookup_time_ms: float = 0.0
    
    # Index efficiency
    cache_hits: int = 0
    cache_misses: int = 0
    index_updates: int = 0
    
    def record_lookup(self, lookup_time_ms: float):
        """Record lookup performance metrics."""
        self.lookup_count += 1
        self.total_lookup_time_ms += lookup_time_ms
        self.avg_lookup_time_ms = self.total_lookup_time_ms / self.lookup_count
        self.max_lookup_time_ms = max(self.max_lookup_time_ms, lookup_time_ms)

@dataclass
class IndexEntry:
    """Individual index entry with metadata."""
    key: str                    # Index key (pattern name, symbol, etc.)
    user_ids: Set[str]         # Users subscribed to this key
    last_access: float         # Last access timestamp for LRU
    access_count: int = 0      # Access frequency for optimization
    
    def record_access(self):
        """Record access for optimization."""
        self.last_access = time.time()
        self.access_count += 1

class SubscriptionIndexManager:
    """
    High-performance subscription indexing system for WebSocket event filtering.
    
    Implements multi-dimensional indexing with O(log n) lookups to achieve <5ms
    user filtering performance for pattern events. Designed for 1000+ active
    subscriptions across multiple filter dimensions.
    
    Key Features:
    - Multi-dimensional indexes (pattern, symbol, tier, confidence, etc.)
    - Efficient set intersections for complex filtering
    - LRU caching for frequently accessed patterns
    - Thread-safe concurrent operations
    - Performance monitoring and optimization
    """
    
    def __init__(self, cache_size: int = 1000, enable_optimization: bool = True):
        """Initialize subscription index manager."""
        
        # Core indexes - each maps index_key -> set of user_ids
        self.pattern_type_index: Dict[str, IndexEntry] = {}      # pattern -> users
        self.symbol_index: Dict[str, IndexEntry] = {}            # symbol -> users
        self.tier_index: Dict[str, IndexEntry] = {}              # tier -> users
        self.market_regime_index: Dict[str, IndexEntry] = {}     # regime -> users
        self.subscription_type_index: Dict[str, IndexEntry] = {} # type -> users
        self.confidence_range_index: Dict[str, IndexEntry] = {}  # range -> users
        self.priority_level_index: Dict[str, IndexEntry] = {}    # priority -> users
        
        # Compound indexes for complex queries
        self.compound_indexes: Dict[str, IndexEntry] = {}        # compound_key -> users
        
        # User reverse mapping for efficient cleanup
        self.user_index_mapping: Dict[str, Dict[str, Set[str]]] = defaultdict(lambda: defaultdict(set))
        
        # Performance optimization
        self.cache_size = cache_size
        self.enable_optimization = enable_optimization
        self.query_cache: Dict[str, Tuple[Set[str], float]] = {}  # query_hash -> (users, timestamp)
        
        # Thread safety
        self.index_lock = threading.RLock()
        
        # Performance tracking
        self.stats = IndexStats()
        
        logger.info(f"SUBSCRIPTION-INDEX: Index manager initialized (cache_size: {cache_size})")
    
    def add_subscription(self, subscription: UserSubscription) -> bool:
        """
        Add subscription to all relevant indexes.
        
        Args:
            subscription: UserSubscription to index
            
        Returns:
            True if successfully added to indexes
        """
        try:
            with self.index_lock:
                user_id = subscription.user_id
                filters = subscription.filters
                sub_type = subscription.subscription_type
                
                # Index by subscription type
                self._add_to_index(self.subscription_type_index, sub_type, user_id)
                self.user_index_mapping[user_id][IndexType.SUBSCRIPTION_TYPE.value].add(sub_type)
                
                # Index by feature-specific filters
                if 'pattern_types' in filters:
                    for pattern in filters['pattern_types']:
                        self._add_to_index(self.pattern_type_index, pattern, user_id)
                        self.user_index_mapping[user_id][IndexType.PATTERN_TYPE.value].add(pattern)
                
                if 'symbols' in filters:
                    for symbol in filters['symbols']:
                        self._add_to_index(self.symbol_index, symbol, user_id)
                        self.user_index_mapping[user_id][IndexType.SYMBOL.value].add(symbol)
                
                if 'tiers' in filters:
                    for tier in filters['tiers']:
                        self._add_to_index(self.tier_index, tier, user_id)
                        self.user_index_mapping[user_id][IndexType.TIER.value].add(tier)
                
                if 'market_regimes' in filters:
                    for regime in filters['market_regimes']:
                        self._add_to_index(self.market_regime_index, regime, user_id)
                        self.user_index_mapping[user_id][IndexType.MARKET_REGIME.value].add(regime)
                
                # Index by confidence ranges
                if 'confidence_min' in filters:
                    confidence_range = self._get_confidence_range(filters['confidence_min'])
                    self._add_to_index(self.confidence_range_index, confidence_range, user_id)
                    self.user_index_mapping[user_id][IndexType.CONFIDENCE_RANGE.value].add(confidence_range)
                
                # Index by priority levels
                if 'priority_min' in filters:
                    priority = filters['priority_min']
                    self._add_to_index(self.priority_level_index, priority, user_id)
                    self.user_index_mapping[user_id][IndexType.PRIORITY_LEVEL.value].add(priority)
                
                # Create compound indexes for common query patterns
                if 'pattern_types' in filters and 'symbols' in filters:
                    for pattern in filters['pattern_types']:
                        for symbol in filters['symbols']:
                            compound_key = f"{pattern}:{symbol}"
                            self._add_to_index(self.compound_indexes, compound_key, user_id)
                
                # Update statistics
                self.stats.total_users = len(self.user_index_mapping)
                self.stats.index_updates += 1
                
                # Clear query cache since indexes changed
                self.query_cache.clear()
                
                logger.debug(f"SUBSCRIPTION-INDEX: Added subscription for user {user_id} to indexes")
                return True
                
        except Exception as e:
            logger.error(f"SUBSCRIPTION-INDEX: Error adding subscription: {e}")
            return False
    
    def remove_subscription(self, user_id: str, subscription_type: Optional[str] = None) -> bool:
        """
        Remove user subscriptions from indexes.
        
        Args:
            user_id: User to remove
            subscription_type: Specific subscription type or None for all
            
        Returns:
            True if successfully removed
        """
        try:
            with self.index_lock:
                if user_id not in self.user_index_mapping:
                    return True  # Already removed
                
                user_indexes = self.user_index_mapping[user_id]
                
                # Remove from all index types
                for index_type, keys in user_indexes.items():
                    index_dict = self._get_index_dict(index_type)
                    if index_dict:
                        for key in keys.copy():
                            self._remove_from_index(index_dict, key, user_id)
                
                # Clean up user mapping
                del self.user_index_mapping[user_id]
                
                # Update statistics
                self.stats.total_users = len(self.user_index_mapping)
                
                # Clear query cache
                self.query_cache.clear()
                
                logger.debug(f"SUBSCRIPTION-INDEX: Removed all indexes for user {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"SUBSCRIPTION-INDEX: Error removing subscription: {e}")
            return False
    
    def find_matching_users(self, criteria: Dict[str, Any]) -> Set[str]:
        """
        Find users matching event criteria using efficient set intersections.
        
        Performance target: <5ms for 1000+ subscriptions
        
        Args:
            criteria: Event criteria to match against subscriptions
            
        Returns:
            Set of user IDs matching the criteria
        """
        try:
            start_time = time.time()
            
            # Check query cache first
            query_hash = self._hash_criteria(criteria)
            if query_hash in self.query_cache:
                cached_result, cache_time = self.query_cache[query_hash]
                if time.time() - cache_time < 30:  # 30 second cache TTL
                    self.stats.cache_hits += 1
                    return cached_result.copy()
            
            with self.index_lock:
                matching_sets = []
                
                # Build list of matching user sets based on criteria
                
                # Check pattern type
                if 'pattern_type' in criteria:
                    pattern_users = self._get_users_from_index(
                        self.pattern_type_index, criteria['pattern_type']
                    )
                    if pattern_users is not None:
                        matching_sets.append(pattern_users)
                
                # Check symbol
                if 'symbol' in criteria:
                    symbol_users = self._get_users_from_index(
                        self.symbol_index, criteria['symbol']
                    )
                    if symbol_users is not None:
                        matching_sets.append(symbol_users)
                
                # Check tier
                if 'tier' in criteria:
                    tier_users = self._get_users_from_index(
                        self.tier_index, criteria['tier']
                    )
                    if tier_users is not None:
                        matching_sets.append(tier_users)
                
                # Check market regime
                if 'market_regime' in criteria:
                    regime_users = self._get_users_from_index(
                        self.market_regime_index, criteria['market_regime']
                    )
                    if regime_users is not None:
                        matching_sets.append(regime_users)
                
                # Check subscription type
                if 'subscription_type' in criteria:
                    sub_type_users = self._get_users_from_index(
                        self.subscription_type_index, criteria['subscription_type']
                    )
                    if sub_type_users is not None:
                        matching_sets.append(sub_type_users)
                
                # Check confidence range
                if 'confidence' in criteria:
                    confidence_range = self._get_confidence_range(criteria['confidence'])
                    confidence_users = self._get_users_from_index(
                        self.confidence_range_index, confidence_range
                    )
                    if confidence_users is not None:
                        matching_sets.append(confidence_users)
                
                # Check priority level
                if 'priority' in criteria:
                    priority_users = self._get_users_from_index(
                        self.priority_level_index, criteria['priority']
                    )
                    if priority_users is not None:
                        matching_sets.append(priority_users)
                
                # Try compound index optimization
                compound_users = self._check_compound_indexes(criteria)
                if compound_users is not None:
                    matching_sets.append(compound_users)
                
                # Compute intersection of all matching sets
                if matching_sets:
                    result = matching_sets[0].copy()
                    for user_set in matching_sets[1:]:
                        result = result.intersection(user_set)
                else:
                    result = set()
                
                # Track performance
                lookup_time_ms = (time.time() - start_time) * 1000
                self.stats.record_lookup(lookup_time_ms)
                
                # Cache result if query took significant time
                if lookup_time_ms > 1.0:  # Cache queries taking >1ms
                    self.query_cache[query_hash] = (result.copy(), time.time())
                    self.stats.cache_misses += 1
                
                # Performance warning for slow queries
                if lookup_time_ms > 5.0:
                    logger.warning(f"SUBSCRIPTION-INDEX: Slow lookup {lookup_time_ms:.1f}ms "
                                 f"for {len(self.user_index_mapping)} users")
                
                logger.debug(f"SUBSCRIPTION-INDEX: Found {len(result)} matching users "
                           f"in {lookup_time_ms:.1f}ms")
                
                return result
                
        except Exception as e:
            logger.error(f"SUBSCRIPTION-INDEX: Error finding matching users: {e}")
            return set()
    
    def _add_to_index(self, index_dict: Dict[str, IndexEntry], key: str, user_id: str):
        """Add user to specific index entry."""
        if key not in index_dict:
            index_dict[key] = IndexEntry(
                key=key,
                user_ids=set(),
                last_access=time.time()
            )
        
        index_dict[key].user_ids.add(user_id)
        index_dict[key].record_access()
    
    def _remove_from_index(self, index_dict: Dict[str, IndexEntry], key: str, user_id: str):
        """Remove user from specific index entry."""
        if key in index_dict:
            index_dict[key].user_ids.discard(user_id)
            # Remove empty entries to keep indexes clean
            if not index_dict[key].user_ids:
                del index_dict[key]
    
    def _get_users_from_index(self, index_dict: Dict[str, IndexEntry], 
                             key: str) -> Optional[Set[str]]:
        """Get users from index with access tracking."""
        if key in index_dict:
            entry = index_dict[key]
            entry.record_access()
            return entry.user_ids
        return None
    
    def _get_index_dict(self, index_type: str) -> Optional[Dict[str, IndexEntry]]:
        """Get index dictionary by type."""
        index_map = {
            IndexType.PATTERN_TYPE.value: self.pattern_type_index,
            IndexType.SYMBOL.value: self.symbol_index,
            IndexType.TIER.value: self.tier_index,
            IndexType.MARKET_REGIME.value: self.market_regime_index,
            IndexType.SUBSCRIPTION_TYPE.value: self.subscription_type_index,
            IndexType.CONFIDENCE_RANGE.value: self.confidence_range_index,
            IndexType.PRIORITY_LEVEL.value: self.priority_level_index
        }
        return index_map.get(index_type)
    
    def _get_confidence_range(self, confidence: float) -> str:
        """Convert confidence to range bucket for indexing."""
        if confidence >= 0.9:
            return "high"
        elif confidence >= 0.7:
            return "medium"
        elif confidence >= 0.5:
            return "low"
        else:
            return "very_low"
    
    def _check_compound_indexes(self, criteria: Dict[str, Any]) -> Optional[Set[str]]:
        """Check compound indexes for optimization."""
        if 'pattern_type' in criteria and 'symbol' in criteria:
            compound_key = f"{criteria['pattern_type']}:{criteria['symbol']}"
            return self._get_users_from_index(self.compound_indexes, compound_key)
        return None
    
    def _hash_criteria(self, criteria: Dict[str, Any]) -> str:
        """Generate hash for criteria caching."""
        # Sort criteria for consistent hashing
        sorted_items = sorted(criteria.items())
        return str(hash(str(sorted_items)))
    
    def optimize_indexes(self) -> Dict[str, Any]:
        """Optimize indexes based on access patterns."""
        try:
            with self.index_lock:
                optimization_stats = {
                    'cache_cleaned': 0,
                    'indexes_optimized': 0,
                    'memory_freed': 0
                }
                
                current_time = time.time()
                
                # Clean old query cache entries
                cache_keys_to_remove = []
                for query_hash, (_, cache_time) in self.query_cache.items():
                    if current_time - cache_time > 300:  # 5 minute TTL
                        cache_keys_to_remove.append(query_hash)
                
                for key in cache_keys_to_remove:
                    del self.query_cache[key]
                    optimization_stats['cache_cleaned'] += 1
                
                # Optimize frequently accessed indexes (placeholder for future optimization)
                all_indexes = [
                    self.pattern_type_index,
                    self.symbol_index,
                    self.tier_index,
                    self.market_regime_index,
                    self.subscription_type_index,
                    self.confidence_range_index,
                    self.priority_level_index,
                    self.compound_indexes
                ]
                
                for index_dict in all_indexes:
                    # Count entries for optimization stats
                    optimization_stats['indexes_optimized'] += len(index_dict)
                
                logger.info(f"SUBSCRIPTION-INDEX: Optimization complete - "
                          f"{optimization_stats['cache_cleaned']} cache entries cleaned, "
                          f"{optimization_stats['indexes_optimized']} index entries processed")
                
                return optimization_stats
                
        except Exception as e:
            logger.error(f"SUBSCRIPTION-INDEX: Error optimizing indexes: {e}")
            return {'error': str(e)}
    
    def get_index_stats(self) -> Dict[str, Any]:
        """Get comprehensive index statistics."""
        with self.index_lock:
            # Calculate index sizes
            index_sizes = {
                'pattern_type': len(self.pattern_type_index),
                'symbol': len(self.symbol_index),
                'tier': len(self.tier_index),
                'market_regime': len(self.market_regime_index),
                'subscription_type': len(self.subscription_type_index),
                'confidence_range': len(self.confidence_range_index),
                'priority_level': len(self.priority_level_index),
                'compound': len(self.compound_indexes)
            }
            
            # Calculate cache efficiency
            total_cache_requests = self.stats.cache_hits + self.stats.cache_misses
            cache_hit_rate = (self.stats.cache_hits / max(total_cache_requests, 1)) * 100
            
            return {
                # Basic stats
                'total_users': self.stats.total_users,
                'total_indexes': sum(index_sizes.values()),
                'index_sizes': index_sizes,
                
                # Performance metrics
                'lookup_count': self.stats.lookup_count,
                'avg_lookup_time_ms': round(self.stats.avg_lookup_time_ms, 2),
                'max_lookup_time_ms': round(self.stats.max_lookup_time_ms, 2),
                'performance_target_ms': 5.0,
                'performance_status': 'good' if self.stats.avg_lookup_time_ms < 5.0 else 'warning',
                
                # Cache metrics
                'cache_size': len(self.query_cache),
                'cache_hits': self.stats.cache_hits,
                'cache_misses': self.stats.cache_misses,
                'cache_hit_rate_percent': round(cache_hit_rate, 1),
                
                # Index efficiency
                'index_updates': self.stats.index_updates,
                'memory_efficiency': 'optimized' if len(self.query_cache) < self.cache_size else 'full',
                'last_updated': time.time()
            }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status for monitoring."""
        stats = self.get_index_stats()
        
        # Determine health status
        if stats['avg_lookup_time_ms'] > 10.0:
            status = 'error'
            message = f"Poor performance: {stats['avg_lookup_time_ms']:.1f}ms average lookup time"
        elif stats['avg_lookup_time_ms'] > 5.0:
            status = 'warning'
            message = f"Slow performance: {stats['avg_lookup_time_ms']:.1f}ms average lookup time"
        elif stats['total_users'] > 1000 and stats['cache_hit_rate_percent'] < 50:
            status = 'warning'
            message = f"Low cache efficiency: {stats['cache_hit_rate_percent']:.1f}% hit rate"
        else:
            status = 'healthy'
            message = f"Index performance healthy: {stats['avg_lookup_time_ms']:.1f}ms average"
        
        return {
            'service': 'subscription_index_manager',
            'status': status,
            'message': message,
            'timestamp': time.time(),
            'stats': stats,
            'performance_targets': {
                'lookup_time_target_ms': 5.0,
                'cache_hit_rate_target_percent': 70.0,
                'max_users_target': 1000
            }
        }
    
    def cleanup_stale_entries(self, max_age_hours: int = 24) -> int:
        """Clean up stale index entries."""
        try:
            with self.index_lock:
                current_time = time.time()
                cleaned_count = 0
                
                all_indexes = [
                    self.pattern_type_index,
                    self.symbol_index,
                    self.tier_index,
                    self.market_regime_index,
                    self.subscription_type_index,
                    self.confidence_range_index,
                    self.priority_level_index,
                    self.compound_indexes
                ]
                
                for index_dict in all_indexes:
                    entries_to_remove = []
                    
                    for key, entry in index_dict.items():
                        age_hours = (current_time - entry.last_access) / 3600
                        if age_hours > max_age_hours and not entry.user_ids:
                            entries_to_remove.append(key)
                    
                    for key in entries_to_remove:
                        del index_dict[key]
                        cleaned_count += 1
                
                if cleaned_count > 0:
                    logger.info(f"SUBSCRIPTION-INDEX: Cleaned {cleaned_count} stale entries")
                
                return cleaned_count
                
        except Exception as e:
            logger.error(f"SUBSCRIPTION-INDEX: Error cleaning stale entries: {e}")
            return 0