"""
Redis Pattern Cache Manager - Sprint 19 Phase 1
Manages pattern data caching from TickStockPL events for high-performance API consumption.

Architecture:
- Consumer role: Consumes pattern events from TickStockPL via Redis pub-sub
- Redis caching: Multi-layer caching (pattern entries, API responses, sorted indexes)
- Performance: <50ms API response targets through in-memory Redis operations
- Zero database load: Pattern queries served from Redis cache only
"""

import logging
import json
import time
import threading
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import redis

logger = logging.getLogger(__name__)

class PatternCacheEventType(Enum):
    """Pattern cache event types from TickStockPL."""
    PATTERN_DETECTED = "pattern_detected"
    PATTERN_EXPIRED = "pattern_expired" 
    PATTERN_UPDATED = "pattern_updated"

@dataclass
class CachedPattern:
    """Cached pattern data structure optimized for UI consumption."""
    symbol: str
    pattern_type: str
    confidence: float
    current_price: float
    price_change: float
    detected_at: float  # Unix timestamp
    expires_at: float   # Unix timestamp
    indicators: Dict[str, Any]
    source_tier: str    # daily, intraday, combo
    
    def to_api_dict(self) -> Dict[str, Any]:
        """Convert to API response format."""
        return {
            'symbol': self.symbol,
            'pattern': self._abbreviate_pattern_name(self.pattern_type),
            'conf': round(self.confidence, 2),
            'rs': f"{self.indicators.get('relative_strength', 1.0):.1f}x",
            'vol': f"{self.indicators.get('relative_volume', 1.0):.1f}x",
            'price': f"${self.current_price:.2f}",
            'chg': f"{self.price_change:+.1f}%",
            'time': self._format_time_ago(time.time() - self.detected_at),
            'exp': self._format_expiration(self.expires_at - time.time()),
            'source': self.source_tier
        }
    
    def _abbreviate_pattern_name(self, pattern_type: str) -> str:
        """Convert pattern names to abbreviated forms for UI."""
        abbreviations = {
            'Weekly_Breakout': 'WeeklyBO',
            'Bull_Flag': 'BullFlag', 
            'Trendline_Hold': 'TrendHold',
            'Volume_Spike': 'VolSpike',
            'Gap_Fill': 'GapFill',
            'Momentum_Shift': 'MomShift',
            'Support_Test': 'Support',
            'Resistance_Break': 'ResBreak',
            'Ascending_Triangle': 'AscTri',
            'Reversal_Signal': 'Reversal',
            'Doji': 'Doji',
            'Hammer': 'Hammer',
            'Engulfing': 'Engulfing'
        }
        return abbreviations.get(pattern_type, pattern_type[:8])
    
    def _format_time_ago(self, seconds_ago: float) -> str:
        """Format seconds into human-readable time ago."""
        if seconds_ago < 60:
            return f"{int(seconds_ago)}s"
        elif seconds_ago < 3600:
            return f"{int(seconds_ago/60)}m"
        elif seconds_ago < 86400:
            return f"{int(seconds_ago/3600)}h"
        else:
            return f"{int(seconds_ago/86400)}d"
    
    def _format_expiration(self, expires_in_seconds: float) -> str:
        """Format expiration time remaining."""
        if expires_in_seconds <= 0:
            return "Expired"
        elif expires_in_seconds < 3600:
            return f"{int(expires_in_seconds/60)}m"
        elif expires_in_seconds < 86400:
            return f"{int(expires_in_seconds/3600)}h"
        else:
            return f"{int(expires_in_seconds/86400)}d"

@dataclass
class PatternCacheStats:
    """Pattern cache statistics for monitoring."""
    cached_patterns: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    events_processed: int = 0
    last_event_time: Optional[float] = None
    expired_patterns_cleaned: int = 0
    api_response_cache_size: int = 0
    index_cache_size: int = 0
    
    def hit_ratio(self) -> float:
        """Calculate cache hit ratio."""
        total = self.cache_hits + self.cache_misses
        return self.cache_hits / total if total > 0 else 1.0

class RedisPatternCache:
    """
    Redis-based pattern cache manager for TickStockPL event consumption.
    
    Features:
    - Pattern event consumption from TickStockPL Redis channels
    - Multi-layer caching: pattern entries, API responses, sorted indexes
    - Performance optimization for <50ms API response targets
    - Automatic expiration and cleanup of stale patterns
    - Query filtering and sorting through Redis operations
    """
    
    def __init__(self, redis_client: redis.Redis, config: Dict[str, Any]):
        """Initialize Redis pattern cache manager."""
        self.redis_client = redis_client
        self.config = config
        
        # Cache configuration
        self.pattern_cache_ttl = config.get('pattern_cache_ttl', 3600)  # 1 hour
        self.api_response_cache_ttl = config.get('api_response_cache_ttl', 30)  # 30 seconds
        self.index_cache_ttl = config.get('index_cache_ttl', 3600)  # 1 hour
        
        # Redis key prefixes
        self.pattern_key_prefix = "tickstock:patterns:"
        self.api_cache_key_prefix = "tickstock:api_cache:"
        self.index_key_prefix = "tickstock:indexes:"
        
        # Sorted set keys for indexes
        self.confidence_index_key = f"{self.index_key_prefix}confidence"
        self.symbol_index_key = f"{self.index_key_prefix}symbol"
        self.pattern_type_index_key = f"{self.index_key_prefix}pattern_type"
        self.time_index_key = f"{self.index_key_prefix}time"
        
        # Statistics
        self.stats = PatternCacheStats()
        
        # Background cleanup
        self._cleanup_thread: Optional[threading.Thread] = None
        self._cleanup_running = False
        
        # Thread safety
        self._lock = threading.RLock()
        
        logger.info("PATTERN-CACHE: Initialized with TTL - patterns: %ds, API: %ds", 
                   self.pattern_cache_ttl, self.api_response_cache_ttl)
    
    def start_background_cleanup(self):
        """Start background thread for cache cleanup."""
        if self._cleanup_running:
            return
            
        self._cleanup_running = True
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_loop,
            name="PatternCacheCleanup",
            daemon=True
        )
        self._cleanup_thread.start()
        logger.info("PATTERN-CACHE: Background cleanup started")
    
    def stop_background_cleanup(self):
        """Stop background cleanup thread."""
        if not self._cleanup_running:
            return
            
        self._cleanup_running = False
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=5)
        logger.info("PATTERN-CACHE: Background cleanup stopped")
    
    def _cleanup_loop(self):
        """Background cleanup loop for expired patterns."""
        while self._cleanup_running:
            try:
                self._cleanup_expired_patterns()
                time.sleep(60)  # Cleanup every minute
            except Exception as e:
                logger.error("PATTERN-CACHE: Cleanup error: %s", e)
                time.sleep(5)  # Shorter sleep on error
    
    def _cleanup_expired_patterns(self):
        """Remove expired patterns from cache and indexes."""
        try:
            current_time = time.time()
            cleanup_count = 0
            
            # Get all pattern keys
            pattern_keys = self.redis_client.keys(f"{self.pattern_key_prefix}*")
            
            pipe = self.redis_client.pipeline()
            
            for pattern_key in pattern_keys:
                # Get pattern data
                pattern_data = self.redis_client.hget(pattern_key, 'data')
                if not pattern_data:
                    continue
                
                try:
                    pattern = json.loads(pattern_data)
                    expires_at = pattern.get('expires_at', 0)
                    
                    if expires_at <= current_time:
                        # Pattern expired - remove from cache and indexes
                        pattern_id = pattern_key.split(':')[-1]
                        symbol = pattern.get('symbol', '')
                        pattern_type = pattern.get('pattern_type', '')
                        confidence = pattern.get('confidence', 0)
                        detected_at = pattern.get('detected_at', 0)
                        
                        # Remove from main cache
                        pipe.delete(pattern_key)
                        
                        # Remove from sorted set indexes
                        pipe.zrem(self.confidence_index_key, pattern_id)
                        pipe.zrem(self.symbol_index_key, f"{symbol}:{pattern_id}")
                        pipe.zrem(self.pattern_type_index_key, f"{pattern_type}:{pattern_id}")
                        pipe.zrem(self.time_index_key, pattern_id)
                        
                        cleanup_count += 1
                        
                except json.JSONDecodeError:
                    continue
            
            # Execute cleanup pipeline
            if cleanup_count > 0:
                pipe.execute()
                self.stats.expired_patterns_cleaned += cleanup_count
                logger.debug("PATTERN-CACHE: Cleaned up %d expired patterns", cleanup_count)
                
        except Exception as e:
            logger.error("PATTERN-CACHE: Error during cleanup: %s", e)
    
    def process_pattern_event(self, event_data: Dict[str, Any]) -> bool:
        """Process incoming pattern event from TickStockPL."""
        try:
            event_type = event_data.get('event_type')
            pattern_data = event_data.get('data', {})
            
            if event_type == 'pattern_detected':
                return self._cache_new_pattern(pattern_data)
            elif event_type == 'pattern_expired':
                return self._remove_pattern(pattern_data)
            elif event_type == 'pattern_updated':
                return self._update_pattern(pattern_data)
            else:
                logger.warning("PATTERN-CACHE: Unknown event type: %s", event_type)
                return False
                
        except Exception as e:
            logger.error("PATTERN-CACHE: Error processing event: %s", e)
            return False
    
    def _cache_new_pattern(self, pattern_data: Dict[str, Any]) -> bool:
        """Cache new pattern detection."""
        try:
            # Create cached pattern object
            pattern = CachedPattern(
                symbol=pattern_data['symbol'],
                pattern_type=pattern_data['pattern'],
                confidence=float(pattern_data['confidence']),
                current_price=float(pattern_data.get('current_price', 0)),
                price_change=float(pattern_data.get('price_change', 0)),
                detected_at=pattern_data.get('timestamp', time.time()),
                expires_at=pattern_data.get('expires_at', time.time() + self.pattern_cache_ttl),
                indicators=pattern_data.get('indicators', {}),
                source_tier=pattern_data.get('source', 'unknown')
            )
            
            # Generate pattern ID
            pattern_id = f"{pattern.symbol}:{pattern.pattern_type}:{int(pattern.detected_at)}"
            pattern_key = f"{self.pattern_key_prefix}{pattern_id}"
            
            # Store pattern in Redis
            pipe = self.redis_client.pipeline()
            
            # Store pattern data
            pipe.hset(pattern_key, mapping={
                'data': json.dumps(asdict(pattern)),
                'cached_at': str(time.time())  # Convert to string for Redis
            })
            pipe.expire(pattern_key, self.pattern_cache_ttl)
            
            # Add to sorted set indexes for fast queries
            pipe.zadd(self.confidence_index_key, {pattern_id: pattern.confidence})
            pipe.zadd(self.symbol_index_key, {f"{pattern.symbol}:{pattern_id}": pattern.detected_at})
            pipe.zadd(self.pattern_type_index_key, {f"{pattern.pattern_type}:{pattern_id}": pattern.detected_at})
            pipe.zadd(self.time_index_key, {pattern_id: pattern.detected_at})
            
            # Set TTL on indexes
            pipe.expire(self.confidence_index_key, self.index_cache_ttl)
            pipe.expire(self.symbol_index_key, self.index_cache_ttl)
            pipe.expire(self.pattern_type_index_key, self.index_cache_ttl)
            pipe.expire(self.time_index_key, self.index_cache_ttl)
            
            # Execute pipeline
            pipe.execute()
            
            # Update statistics
            with self._lock:
                self.stats.cached_patterns += 1
                self.stats.events_processed += 1
                self.stats.last_event_time = time.time()
            
            # Clear API response cache (patterns changed)
            self._invalidate_api_cache()
            
            logger.debug("PATTERN-CACHE: Cached pattern %s on %s (conf: %.2f)", 
                        pattern.pattern_type, pattern.symbol, pattern.confidence)
            return True
            
        except Exception as e:
            logger.error("PATTERN-CACHE: Error caching pattern: %s", e)
            return False
    
    def _remove_pattern(self, pattern_data: Dict[str, Any]) -> bool:
        """Remove expired pattern from cache."""
        # Implementation for explicit pattern removal
        # For now, rely on automatic TTL expiration and cleanup
        return True
    
    def _update_pattern(self, pattern_data: Dict[str, Any]) -> bool:
        """Update existing pattern in cache."""
        # Implementation for pattern updates
        # For now, treat as new pattern (overwrite)
        return self._cache_new_pattern(pattern_data)
    
    def _invalidate_api_cache(self):
        """Invalidate API response cache when patterns change."""
        try:
            api_cache_keys = self.redis_client.keys(f"{self.api_cache_key_prefix}*")
            if api_cache_keys:
                self.redis_client.delete(*api_cache_keys)
                logger.debug("PATTERN-CACHE: Invalidated %d API cache entries", len(api_cache_keys))
        except Exception as e:
            logger.error("PATTERN-CACHE: Error invalidating API cache: %s", e)
    
    def scan_patterns(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Scan cached patterns with filtering and pagination."""
        try:
            start_time = time.time()
            
            # Generate cache key for this query
            cache_key = self._generate_api_cache_key(filters)
            
            # Try API response cache first
            cached_response = self.redis_client.get(cache_key)
            if cached_response:
                self.stats.cache_hits += 1
                response_time = (time.time() - start_time) * 1000
                logger.debug("PATTERN-CACHE: API cache hit - %.2f ms", response_time)
                return json.loads(cached_response)
            
            # Cache miss - perform query
            self.stats.cache_misses += 1
            
            # Extract filter parameters
            pattern_types = filters.get('pattern_types', [])
            rs_min = float(filters.get('rs_min', 0))
            vol_min = float(filters.get('vol_min', 0))
            rsi_range = filters.get('rsi_range', [0, 100])
            rsi_min, rsi_max = float(rsi_range[0]), float(rsi_range[1])
            confidence_min = float(filters.get('confidence_min', 0.5))
            symbols = filters.get('symbols', [])
            page = int(filters.get('page', 1))
            per_page = min(int(filters.get('per_page', 30)), 100)
            sort_by = filters.get('sort_by', 'confidence')
            sort_order = filters.get('sort_order', 'desc')
            
            # Build pattern list from Redis indexes
            patterns = self._query_patterns_from_redis(
                pattern_types, symbols, confidence_min,
                rs_min, vol_min, rsi_min, rsi_max,
                sort_by, sort_order
            )
            
            # Apply pagination
            total = len(patterns)
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            paginated_patterns = patterns[start_idx:end_idx]
            
            # Convert to API format
            api_patterns = [pattern.to_api_dict() for pattern in paginated_patterns]
            
            response = {
                'patterns': api_patterns,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'pages': (total + per_page - 1) // per_page
                },
                'cache_info': {
                    'cached': False,
                    'query_time_ms': round((time.time() - start_time) * 1000, 2)
                }
            }
            
            # Cache the response
            self.redis_client.setex(
                cache_key, 
                self.api_response_cache_ttl,
                json.dumps(response)
            )
            
            response_time = (time.time() - start_time) * 1000
            logger.debug("PATTERN-CACHE: Query completed - %.2f ms, %d patterns", 
                        response_time, len(api_patterns))
            
            return response
            
        except Exception as e:
            logger.error("PATTERN-CACHE: Error scanning patterns: %s", e)
            return {
                'patterns': [],
                'pagination': {'page': 1, 'per_page': 30, 'total': 0, 'pages': 0},
                'error': str(e)
            }
    
    def _query_patterns_from_redis(self, pattern_types: List[str], symbols: List[str],
                                  confidence_min: float, rs_min: float, vol_min: float,
                                  rsi_min: float, rsi_max: float,
                                  sort_by: str, sort_order: str) -> List[CachedPattern]:
        """Query patterns from Redis using sorted set indexes."""
        try:
            # Start with confidence filtering (most selective)
            if sort_by == 'confidence':
                # Use confidence index directly
                if sort_order == 'desc':
                    pattern_ids = self.redis_client.zrevrangebyscore(
                        self.confidence_index_key, '+inf', confidence_min
                    )
                else:
                    pattern_ids = self.redis_client.zrangebyscore(
                        self.confidence_index_key, confidence_min, '+inf'
                    )
            else:
                # Get all patterns above confidence threshold
                pattern_ids = self.redis_client.zrangebyscore(
                    self.confidence_index_key, confidence_min, '+inf'
                )
            
            # Load pattern data and apply additional filters
            filtered_patterns = []
            
            for pattern_id in pattern_ids:
                pattern_key = f"{self.pattern_key_prefix}{pattern_id}"
                pattern_data = self.redis_client.hget(pattern_key, 'data')
                
                if not pattern_data:
                    continue
                
                try:
                    pattern_dict = json.loads(pattern_data)
                    pattern = CachedPattern(**pattern_dict)
                    
                    # Apply filters
                    if pattern_types and pattern.pattern_type not in pattern_types:
                        continue
                    
                    if symbols and pattern.symbol not in symbols:
                        continue
                    
                    rs = pattern.indicators.get('relative_strength', 1.0)
                    if rs < rs_min:
                        continue
                    
                    vol = pattern.indicators.get('relative_volume', 1.0) 
                    if vol < vol_min:
                        continue
                    
                    rsi = pattern.indicators.get('rsi', 50.0)
                    if rsi < rsi_min or rsi > rsi_max:
                        continue
                    
                    # Check if pattern is still valid (not expired)
                    if pattern.expires_at <= time.time():
                        continue
                    
                    filtered_patterns.append(pattern)
                    
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning("PATTERN-CACHE: Invalid pattern data for %s: %s", pattern_id, e)
                    continue
            
            # Sort patterns if not already sorted by confidence
            if sort_by != 'confidence':
                reverse = (sort_order == 'desc')
                
                if sort_by == 'detected_at':
                    filtered_patterns.sort(key=lambda p: p.detected_at, reverse=reverse)
                elif sort_by == 'symbol':
                    filtered_patterns.sort(key=lambda p: p.symbol, reverse=reverse)
                elif sort_by == 'rs':
                    filtered_patterns.sort(key=lambda p: p.indicators.get('relative_strength', 1.0), reverse=reverse)
                elif sort_by == 'volume':
                    filtered_patterns.sort(key=lambda p: p.indicators.get('relative_volume', 1.0), reverse=reverse)
            
            return filtered_patterns
            
        except Exception as e:
            logger.error("PATTERN-CACHE: Error querying Redis patterns: %s", e)
            return []
    
    def _generate_api_cache_key(self, filters: Dict[str, Any]) -> str:
        """Generate cache key for API response."""
        import hashlib
        
        # Create sorted filter string for consistent cache keys
        filter_str = json.dumps(filters, sort_keys=True)
        filter_hash = hashlib.md5(filter_str.encode()).hexdigest()
        
        return f"{self.api_cache_key_prefix}scan:{filter_hash}"
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics and health metrics."""
        try:
            # Get Redis cache sizes
            pattern_keys = self.redis_client.keys(f"{self.pattern_key_prefix}*")
            api_cache_keys = self.redis_client.keys(f"{self.api_cache_key_prefix}*")
            
            self.stats.cached_patterns = len(pattern_keys)
            self.stats.api_response_cache_size = len(api_cache_keys)
            
            # Get index sizes
            self.stats.index_cache_size = (
                self.redis_client.zcard(self.confidence_index_key) +
                self.redis_client.zcard(self.symbol_index_key) +
                self.redis_client.zcard(self.pattern_type_index_key) +
                self.redis_client.zcard(self.time_index_key)
            )
            
            return {
                **asdict(self.stats),
                'cache_hit_ratio': self.stats.hit_ratio(),
                'last_check': time.time()
            }
            
        except Exception as e:
            logger.error("PATTERN-CACHE: Error getting stats: %s", e)
            return asdict(self.stats)
    
    def clear_cache(self) -> bool:
        """Clear all pattern cache data."""
        try:
            # Get all cache keys
            pattern_keys = self.redis_client.keys(f"{self.pattern_key_prefix}*")
            api_cache_keys = self.redis_client.keys(f"{self.api_cache_key_prefix}*")
            index_keys = [
                self.confidence_index_key,
                self.symbol_index_key, 
                self.pattern_type_index_key,
                self.time_index_key
            ]
            
            all_keys = pattern_keys + api_cache_keys + index_keys
            
            if all_keys:
                self.redis_client.delete(*all_keys)
                logger.info("PATTERN-CACHE: Cleared %d cache entries", len(all_keys))
            
            # Reset statistics
            self.stats = PatternCacheStats()
            
            return True
            
        except Exception as e:
            logger.error("PATTERN-CACHE: Error clearing cache: %s", e)
            return False