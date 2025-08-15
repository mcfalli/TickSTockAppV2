"""
User Universe Management - Sprint 6B
Handles per-user universe selections, caching, and preferences.
Extracted from src.core.services.universe_coordinator.py and websocket_publisher.py
"""

import logging
import time
from typing import Dict, List, Any, Optional, Set
from collections import defaultdict

from config.logging_config import get_domain_logger, LogDomain

logger = get_domain_logger(LogDomain.UNIVERSE_TRACKING, 'user_universe_manager')

class DataFlowStats:
    """Track user universe data flow."""
    def __init__(self):
        self.cache_hits = 0
        self.cache_misses = 0
        self.cache_loads = 0
        self.cache_errors = 0
        self.last_log_time = time.time()
        self.log_interval = 60  # seconds
    
    def should_log(self):
        return time.time() - self.last_log_time >= self.log_interval
    
    def log_stats(self, logger):
        hit_rate = 0
        total = self.cache_hits + self.cache_misses
        if total > 0:
            hit_rate = (self.cache_hits / total) * 100
        
        logger.info(
            f"📊USER-UNV: USER UNIVERSE CACHE: Hits:{self.cache_hits} → Misses:{self.cache_misses} → "
            f"Loads:{self.cache_loads} (Hit rate: {hit_rate:.1f}%)"
        )
        self.last_log_time = time.time()

class UserUniverseManager:
    """
    Manages per-user universe selections and caching.
    
    Responsibilities:
    - Store and retrieve user universe selections
    - Handle per-user universe caching
    - Manage cache invalidation
    - Track user universe preferences
    """
    
    def __init__(self, config, cache_control, user_settings_service=None):
        """Initialize user universe manager with dependencies."""
        self.config = config
        self.cache_control = cache_control
        self.user_settings_service = user_settings_service
        
        # Data flow tracking
        self.stats = DataFlowStats()
        
        # User universe cache (moved from src.presentation.websocket.publisher)
        self.user_universe_cache = {}  # user_id -> {market: [...], highlow: [...]}
        
        # Configuration
        self.cache_ttl = config.get('USER_UNIVERSE_CACHE_TTL', 3600)  # 1 hour default
        self.max_cache_size = config.get('MAX_USER_UNIVERSE_CACHE_SIZE', 1000)
        
    
    def get_or_load_user_universes(self, user_id: int) -> Dict[str, List[str]]:
        """
        Get user's universe selections from cache or load from src.infrastructure.database.
        
        Args:
            user_id: User ID to get universes for
            
        Returns:
            Dict containing 'market' and 'highlow' universe lists
        """
        try:
            # Check cache first
            if user_id in self.user_universe_cache:
                self.stats.cache_hits += 1
                return self.user_universe_cache[user_id].copy()
            
            # Cache miss - load from service
            self.stats.cache_misses += 1
            
            # Load from user settings service if available
            if self.user_settings_service:
                try:
                    user_universes = self.user_settings_service.get_user_universe_selections(user_id)
                    if user_universes:
                        # Cache the loaded data
                        self.user_universe_cache[user_id] = user_universes
                        self.stats.cache_loads += 1
                        
                        # Log first load for user
                        if self.stats.cache_loads <= 5:
                            logger.info(
                                f"📥USER-UNV:  USER {user_id} UNIVERSES LOADED: "
                                f"market={user_universes.get('market', [])}, "
                                f"highlow={user_universes.get('highlow', [])}"
                            )
                        
                        return user_universes
                except Exception as e:
                    logger.error(f"❌ Failed to load user {user_id} universes: {e}")
                    self.stats.cache_errors += 1
            
            # Default universes if nothing found
            default_universes = {
                'market': ['DEFAULT_UNIVERSE'],
                'highlow': ['DEFAULT_UNIVERSE']
            }
            
            # Cache the defaults
            self.user_universe_cache[user_id] = default_universes
            
            # Periodic stats logging
            if self.stats.should_log():
                self.stats.log_stats(logger)
            
            return default_universes.copy()
            
        except Exception as e:
            logger.error(f"❌ Critical error getting user universes: {e}")
            self.stats.cache_errors += 1
            return {
                'market': ['DEFAULT_UNIVERSE'],
                'highlow': ['DEFAULT_UNIVERSE']
            }
    
    def update_user_universe_cache(self, user_id: int, universe_selections: Dict[str, List[str]]) -> bool:
        """
        Update user's universe selections in cache.
        
        Args:
            user_id: User ID to update
            universe_selections: New universe selections
            
        Returns:
            bool: True if update successful
        """
        try:
            # Validate input
            if not isinstance(universe_selections, dict):
                logger.error(f"❌ Invalid universe format for user {user_id}")
                return False
            
            # Ensure required keys exist
            if 'market' not in universe_selections:
                universe_selections['market'] = ['DEFAULT_UNIVERSE']
            if 'highlow' not in universe_selections:
                universe_selections['highlow'] = ['DEFAULT_UNIVERSE']
            
            # Update cache
            self.user_universe_cache[user_id] = universe_selections.copy()
            
            logger.info(
                f"📤USER-UNV:  USER {user_id} UNIVERSE UPDATE: "
                f"market={len(universe_selections['market'])} universes, "
                f"highlow={len(universe_selections['highlow'])} universes"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to update user universe cache: {e}")
            return False
    
    def invalidate_user_universe_cache(self, user_id: int) -> bool:
        """
        Invalidate cache for a specific user.
        
        Args:
            user_id: User ID to invalidate
            
        Returns:
            bool: True if cache invalidated
        """
        try:
            if user_id in self.user_universe_cache:
                del self.user_universe_cache[user_id]
            
            return True
                
        except Exception as e:
            logger.error(f"❌ Failed to invalidate cache: {e}")
            return False
    
    def get_all_user_universe_tickers(self, user_id: int) -> Set[str]:
        """
        Get all unique tickers from a user's universe selections.
        
        Args:
            user_id: User ID
            
        Returns:
            Set of all unique tickers across user's universes
        """
        try:
            user_selections = self.get_or_load_user_universes(user_id)
            all_tickers = set()
            
            # Combine all universe selections
            all_universe_keys = set()
            all_universe_keys.update(user_selections.get('market', []))
            all_universe_keys.update(user_selections.get('highlow', []))
            
            # Get tickers for each universe
            for universe_key in all_universe_keys:
                try:
                    universe_tickers = self.cache_control.get_universe_tickers(universe_key)
                    all_tickers.update(universe_tickers)
                except Exception as e:
                    logger.error(f"❌ Failed to get tickers for universe {universe_key}: {e}")
            
            # Log size on first request
            if user_id not in self.user_universe_cache:
                logger.info(f"📊USER-UNV:  USER {user_id} total universe size: {len(all_tickers)} tickers")
            
            return all_tickers
            
        except Exception as e:
            logger.error(f"❌ Failed to get user universe tickers: {e}")
            return set()
    
    def check_data_flow_health(self):
        """Diagnose where data flow is breaking."""
        if self.stats.cache_loads == 0 and self.stats.cache_misses > 0:
            logger.error("🚨USER-UNV:  Cache misses but NO LOADS - Check database connection")
        elif self.stats.cache_errors > 5:
            logger.error(f"🚨USER-UNV:  High cache error rate: {self.stats.cache_errors} errors")
        elif self.stats.cache_hits == 0 and self.stats.cache_loads > 10:
            logger.warning("⚠️USER-UNV:  No cache hits despite loads - Check cache retention")
        
        total = self.stats.cache_hits + self.stats.cache_misses
        if total > 100:
            hit_rate = (self.stats.cache_hits / total) * 100
            if hit_rate < 50:
                logger.warning(f"⚠️USER-UNV:  Low cache hit rate: {hit_rate:.1f}%")

    def save_user_universe_selections(self, user_id: int, tracker_type: str, universes: List[str]) -> bool:
        """
        Save user's universe selections to database and update cache.
        
        Args:
            user_id: User ID
            tracker_type: Type of tracker ('market' or 'highlow')
            universes: List of universe selections
            
        Returns:
            bool: True if save successful
        """
        try:
            # First, save to database through user settings service
            if self.user_settings_service:
                # Load current selections
                current_selections = self.get_or_load_user_universes(user_id)
                
                # Update the specific tracker type
                current_selections[tracker_type] = universes
                
                # Save to database
                success = self.user_settings_service.save_universe_selection(
                    user_id, tracker_type, universes
                )
                
                if success:
                    # Update cache with new selections
                    self.update_user_universe_cache(user_id, current_selections)
                    
                    return True
                else:
                    logger.error(f"❌USER-UNV:  Failed to save universe selections to database")
                    return False
            else:
                logger.error("❌USER-UNV:  No user_settings_service available for saving")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error saving user universe selections: {e}")
            return False
        
    def get_universe_cache_status(self) -> Dict[str, Any]:
        """
        Get cache status information.
        
        Returns:
            dict: Cache status with statistics
        """
        try:
            total_cached = len(self.user_universe_cache)
            cache_entries = []
            
            for user_id, selections in self.user_universe_cache.items():
                cache_entries.append({
                    'user_id': user_id,
                    'market_universes': len(selections.get('market', [])),
                    'highlow_universes': len(selections.get('highlow', []))
                })
            
            # Sort by user_id for consistent output
            cache_entries.sort(key=lambda x: x['user_id'])
            
            hit_rate = 0
            total_requests = self.stats.cache_hits + self.stats.cache_misses
            if total_requests > 0:
                hit_rate = (self.stats.cache_hits / total_requests) * 100
            
            return {
                'total_cached_users': total_cached,
                'cache_entries': cache_entries[:10],  # First 10 for display
                'hit_rate': round(hit_rate, 2),
                'cache_hits': self.stats.cache_hits,
                'cache_misses': self.stats.cache_misses,
                'cache_loads': self.stats.cache_loads,
                'cache_errors': self.stats.cache_errors,
                'max_cache_size': self.max_cache_size
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting cache status: {e}")
            return {'error': str(e)}

    def reset_cache_stats(self):
        """Reset cache statistics."""
        self.stats = DataFlowStats()

    def get_performance_report(self) -> Dict[str, Any]:
        """
        Get performance report for user universe operations.
        
        Returns:
            dict: Performance metrics and statistics
        """
        try:
            cache_status = self.get_universe_cache_status()
            
            return {
                'cache_status': cache_status,
                'performance_stats': {
                    'avg_load_time_ms': 'N/A',  # Would need timing data
                    'cache_memory_usage': 'N/A'  # Would need memory profiling
                },
                'timestamp': time.time()
            }
            
        except Exception as e:
            logger.error(f"❌ Error generating performance report: {e}")
            return {'error': str(e)}