"""
WebSocket Filter Cache Manager

Manages per-user filter caching for WebSocket operations.
"""

from config.logging_config import get_domain_logger, LogDomain
from typing import Dict, Optional, Any, List
import time
from datetime import datetime

logger = get_domain_logger(LogDomain.USER_SETTINGS, 'websocket_filter_cache')


class WebSocketFilterCache:
    """Manages per-user filter caching for WebSocket operations."""
    
    def __init__(self, user_filters_service=None, app=None):
        """Initialize filter cache manager."""
        self.user_filters_service = user_filters_service
        self.app = app 

        if self.user_filters_service and hasattr(self.user_filters_service, 'app'):
            self.user_filters_service.app = app

        # Per-user filter cache
        self.user_filter_cache = {}  # user_id -> filter_data
        self.cache_initialized = False
        self.last_cache_update = 0
        
        # Cache statistics
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'loads': 0,
            'invalidations': 0,
            'updates': 0
        }
        
    
    def get_or_load_user_filters(self, user_id: int) -> Dict[str, Any]:
        """
        Get user filters from cache or load from src.infrastructure.database.
        
        Args:
            user_id: User ID to get filters for
            
        Returns:
            dict: User filter data or None if no filters
        """
        try:
            # Check cache first
            if user_id in self.user_filter_cache:
                self.cache_stats['hits'] += 1
                logger.debug(f"WEBSOCKET-FILTER: User {user_id}")
                return self.user_filter_cache[user_id]
            
            # Cache miss - load from src.infrastructure.database
            self.cache_stats['misses'] += 1
            
            if not self.user_filters_service:
                logger.debug(f"WEBSOCKET-FILTER: FILTER_CACHE_MISS: No service available for user {user_id}")
                return None
            
            logger.debug(f"WEBSOCKET-FILTER: FILTER_CACHE_MISS: Loading from src.infrastructure.database for user {user_id}")
            user_filters = self.user_filters_service.load_user_filters(user_id, 'default')
            
            if user_filters and user_filters.get('filters'):
                # Store in cache for future use
                complete_filter_data = self._prepare_filter_data(user_filters)
                self.user_filter_cache[user_id] = complete_filter_data
                self.cache_stats['loads'] += 1
                
                logger.debug(f"WEBSOCKET-FILTER: FILTER_CACHE_LOADED: User {user_id} filters loaded and cached")
                return complete_filter_data
            else:
                logger.debug(f"WEBSOCKET-FILTER: FILTER_LOAD_EMPTY: User {user_id} has no saved filters")
                return None
                
        except Exception as e:
            logger.error(f"Error getting/loading filters for user {user_id}: {e}")
            return None
    
    def _prepare_filter_data(self, user_filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare complete filter data structure.
        
        Args:
            user_filters: Raw filter data from src.infrastructure.database
            
        Returns:
            dict: Complete filter data structure
        """
        return {
            'filter_name': 'default',
            'filters': user_filters['filters'],
            'version': user_filters.get('version', '1.0'),
            'timestamp': user_filters.get('timestamp', time.time()),
            'display_preferences': user_filters.get('display_preferences', {})
        }
    
    def update_cache(self, user_id: int, filter_data: Dict[str, Any]) -> bool:
        """
        Update cached filters for a user.
        
        Args:
            user_id: User ID
            filter_data: New filter data to cache
            
        Returns:
            bool: True if cache updated successfully
        """
        try:
            # Prepare complete filter data
            complete_filter_data = self._prepare_filter_data(filter_data)
            
            # Store in cache
            self.user_filter_cache[user_id] = complete_filter_data
            self.last_cache_update = time.time()
            self.cache_stats['updates'] += 1
            
            logger.info(f"FILTER_CACHE_UPDATE: Updated filters for user {user_id}")
            
            # Log filter summary if service available
            if self.user_filters_service:
                try:
                    filter_summary = self.user_filters_service._get_filter_summary(complete_filter_data)
                except Exception as summary_error:
                    logger.debug(f"Could not generate filter summary: {summary_error}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating filter cache for user {user_id}: {e}")
            return False
    
    def invalidate_cache(self, user_id: int) -> bool:
        """
        Invalidate cached filters for a specific user.
        Called when user changes their filter settings.
        
        Args:
            user_id: User ID to invalidate cache for
            
        Returns:
            bool: True if cache invalidated successfully
        """
        try:
            if user_id in self.user_filter_cache:
                del self.user_filter_cache[user_id]
                self.cache_stats['invalidations'] += 1
                return True
            else:
                logger.debug(f"WEBSOCKET-FILTER: FILTER_CACHE_INVALIDATE: No cache found for user {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error invalidating filter cache for user {user_id}: {e}")
            return False
    
    '''
    def initialize_for_all_users(self, user_ids: List[int]) -> bool:
        """
        Initialize filter cache for multiple users.
        
        Args:
            user_ids: List of user IDs to initialize cache for
            
        Returns:
            bool: True if initialization successful
        """
        try:
            if not self.user_filters_service:
                return False
            
            successful_loads = 0
            
            for user_id in user_ids:
                try:
                    user_filters = self.get_or_load_user_filters(user_id)
                    if user_filters:
                        successful_loads += 1
                except Exception as user_error:
                    logger.error(f"Error loading filters for user {user_id}: {user_error}")
                    continue
            
            self.cache_initialized = True
            self.last_cache_update = time.time()
            
            return True
            
        except Exception as e:
            logger.error(f"Error initializing multi-user filter cache: {e}", exc_info=True)
            return False
    '''

    '''
    def get_cache_status(self) -> Dict[str, Any]:
        """
        Get filter cache status for monitoring.
        
        Returns:
            dict: Cache status information
        """
        try:
            total_requests = self.cache_stats['hits'] + self.cache_stats['misses']
            hit_rate = (self.cache_stats['hits'] / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'initialized': self.cache_initialized,
                'cached_users': list(self.user_filter_cache.keys()),
                'cache_size': len(self.user_filter_cache),
                'last_update': self.last_cache_update,
                'statistics': {
                    'hits': self.cache_stats['hits'],
                    'misses': self.cache_stats['misses'],
                    'loads': self.cache_stats['loads'],
                    'updates': self.cache_stats['updates'],
                    'invalidations': self.cache_stats['invalidations'],
                    'hit_rate': hit_rate,
                    'total_requests': total_requests
                },
                'filters_service_available': self.user_filters_service is not None
            }
        except Exception as e:
            logger.error(f"Error getting filter cache status: {e}")
            return {'error': str(e)}
    '''

    '''
    def clear_all_cache(self):
        """Clear all cached filter data."""
        try:
            user_count = len(self.user_filter_cache)
            self.user_filter_cache.clear()
            self.cache_initialized = False
        except Exception as e:
            logger.error(f"Error clearing all filter cache: {e}")
    '''

    '''
    def get_user_breakdown(self) -> Dict[int, Dict[str, Any]]:
        """
        Get breakdown of cached filters by user.
        
        Returns:
            dict: User ID to filter info mapping
        """
        try:
            breakdown = {}
            for user_id, filter_data in self.user_filter_cache.items():
                breakdown[user_id] = {
                    'has_filters': bool(filter_data.get('filters')),
                    'filter_count': len(filter_data.get('filters', {})),
                    'last_updated': filter_data.get('timestamp', 0)
                }
            return breakdown
        except Exception as e:
            logger.error(f"Error getting user breakdown: {e}")
            return {}
    '''