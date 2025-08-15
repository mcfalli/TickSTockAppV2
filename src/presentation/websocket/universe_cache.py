"""
WebSocket Universe Cache Manager

Manages per-user universe caching for WebSocket operations.
"""

from config.logging_config import get_domain_logger, LogDomain
from typing import Dict, List, Optional, Any
import time
from datetime import datetime

logger = get_domain_logger(LogDomain.UNIVERSE_TRACKING, 'websocket_universe_cache')


class WebSocketUniverseCache:
    """Manages per-user universe caching for WebSocket operations."""
    
    def __init__(self, user_settings_service=None, cache_control=None):
        """Initialize universe cache manager."""
        self.user_settings_service = user_settings_service
        self.cache_control = cache_control
        
        # Per-user universe cache structure
        self.user_universe_cache = {}  # user_id -> universe selections
        self.cache_initialized = False
        self.last_cache_update = 0
        
        # Cache statistics
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'loads': 0,
            'invalidations': 0
        }
    
    def get_or_load_user_universes(self, user_id: int) -> Dict[str, List[str]]:
        """
        Get user universe selections from cache or load from src.infrastructure.database.
        
        Args:
            user_id: User ID to get universe selections for
            
        Returns:
            dict: Universe selections for this user {'market': [...], 'highlow': [...]}
        """
        try:
            # Check cache first
            if user_id in self.user_universe_cache:
                self.cache_stats['hits'] += 1
                logger.debug(f"WEBSOCKET-UNI-CACHE: UNIVERSE_CACHE_HIT: User {user_id}")
                return self.user_universe_cache[user_id]
            
            # Cache miss - load from src.infrastructure.database
            self.cache_stats['misses'] += 1
            logger.debug(f"WEBSOCKET-UNI-CACHE: UNIVERSE_CACHE_MISS: Loading from src.infrastructure.database for user {user_id}")
            
            user_selections = self._load_from_database(user_id)
            
            # Store in cache for future use
            self.user_universe_cache[user_id] = user_selections
            self.last_cache_update = time.time()
            
            logger.debug(f"WEBSOCKET-UNI-CACHE: UNIVERSE_CACHE_LOADED: User {user_id} selections cached: {user_selections}")
            
            return user_selections
                
        except Exception as e:
            logger.error(f"Error getting/loading universes for user {user_id}: {e}", exc_info=True)
            
            # Return safe fallback defaults
            return self._get_default_selections()
    
    def _load_from_database(self, user_id: int) -> Dict[str, List[str]]:
        """
        Load user universe selections from src.infrastructure.database using UserSettingsService.
        
        Args:
            user_id: User ID to load selections for
            
        Returns:
            dict: Universe selections or defaults if not found/error
        """
        try:
            if not self.user_settings_service:
                logger.warning(f"WEBSOCKET-UNI-CACHE: No user settings service available for user {user_id}")
                return self._get_default_selections()
            
            logger.debug(f"WEBSOCKET-UNI-CACHE: Loading universe selections for user {user_id}")
            
            # Use existing UserSettingsService method
            selections = self.user_settings_service.get_universe_selections(user_id)
            
            if selections:
                self.cache_stats['loads'] += 1
                logger.info(f"WEBSOCKET-UNI-CACHE: Loaded selections for user {user_id}: {selections}")
                
                # Validate structure and contents
                validated_selections = self._validate_selections(selections)
                logger.debug(f"WEBSOCKET-UNI-CACHE: UNIVERSE_DB_VALIDATED: User {user_id} validated selections: {validated_selections}")
                
                return validated_selections
            else:
                logger.info(f"WEBSOCKET-UNI-CACHE: UNIVERSE_DB_EMPTY: No saved selections found for user {user_id}, using defaults")
                return self._get_default_selections()
                
        except Exception as e:
            logger.error(f"WEBSOCKET-UNI-CACHE: UNIVERSE_DB_ERROR: Error loading selections for user {user_id}: {e}", exc_info=True)
            return self._get_default_selections()
    
    def _validate_selections(self, selections: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """
        Validate universe selections structure and ensure required trackers exist.
        
        Args:
            selections: Universe selections to validate
            
        Returns:
            dict: Validated universe selections
        """
        try:
            if not isinstance(selections, dict):
                logger.warning(f"WEBSOCKET-UNI-CACHE: UNIVERSE_VALIDATE: Invalid selections type: {type(selections)}, using defaults")
                return self._get_default_selections()
            
            validated = {}
            
            # Ensure both tracker types exist with valid lists
            for tracker_type in ['market', 'highlow']:
                if tracker_type in selections and isinstance(selections[tracker_type], list):
                    # Filter out invalid/empty entries
                    valid_universes = [u for u in selections[tracker_type] if u and isinstance(u, str)]
                    
                    if valid_universes:
                        validated[tracker_type] = valid_universes
                        logger.debug(f"WEBSOCKET-UNI-CACHE: UNIVERSE_VALIDATE: {tracker_type} validated: {valid_universes}")
                    else:
                        validated[tracker_type] = ['DEFAULT_UNIVERSE']
                        logger.info(f"WEBSOCKET-UNI-CACHE: UNIVERSE_VALIDATE: {tracker_type} had no valid universes, using DEFAULT_UNIVERSE")
                else:
                    validated[tracker_type] = ['DEFAULT_UNIVERSE']
                    logger.info(f"WEBSOCKET-UNI-CACHE: UNIVERSE_VALIDATE: {tracker_type} missing or invalid, using DEFAULT_UNIVERSE")
            
            return validated
            
        except Exception as e:
            logger.error(f"Error validating selections: {e}", exc_info=True)
            return self._get_default_selections()
    
    def _get_default_selections(self) -> Dict[str, List[str]]:
        """
        Get default universe selections when no user selections exist.
        
        Returns:
            dict: Default universe selections
        """
        return {
            'market': ['DEFAULT_UNIVERSE'],
            'highlow': ['DEFAULT_UNIVERSE']
        }
    
    def update_cache(self, user_id: int, selections: Dict[str, List[str]]) -> bool:
        """
        Update cached universe selections for a user.
        
        Args:
            user_id: User ID
            selections: New universe selections to cache
            
        Returns:
            bool: True if cache updated successfully
        """
        try:
            # Validate selections before caching
            validated_selections = self._validate_selections(selections)
            
            # Store in cache
            self.user_universe_cache[user_id] = validated_selections
            self.last_cache_update = time.time()
            
            return True
            
        except Exception as e:
            logger.error(f"UNIVERSE_CACHE_UPDATE_ERROR: Error updating cache for user {user_id}: {e}", exc_info=True)
            return False
    
    def invalidate_cache(self, user_id: int) -> bool:
        """
        Invalidate cached universe selections for a specific user.
        Called when user changes their universe settings.
        
        Args:
            user_id: User ID to invalidate cache for
            
        Returns:
            bool: True if cache invalidated successfully
        """
        try:
            if user_id in self.user_universe_cache:
                old_selections = self.user_universe_cache[user_id]
                del self.user_universe_cache[user_id]
                
                self.cache_stats['invalidations'] += 1
                
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"UNIVERSE_CACHE_INVALIDATE_ERROR: Error invalidating cache for user {user_id}: {e}")
            return False
    '''
    def get_cache_status(self) -> Dict[str, Any]:
        """
        Get cache status for monitoring.
        
        Returns:
            dict: Cache status information
        """
        try:
            return {
                'initialized': self.cache_initialized,
                'cached_users': list(self.user_universe_cache.keys()),
                'cache_size': len(self.user_universe_cache),
                'last_update': self.last_cache_update,
                'statistics': {
                    'hits': self.cache_stats['hits'],
                    'misses': self.cache_stats['misses'],
                    'loads': self.cache_stats['loads'],
                    'invalidations': self.cache_stats['invalidations'],
                    'hit_rate': (self.cache_stats['hits'] / 
                               (self.cache_stats['hits'] + self.cache_stats['misses']) * 100) 
                               if (self.cache_stats['hits'] + self.cache_stats['misses']) > 0 else 0
                },
                'user_settings_service_available': self.user_settings_service is not None,
                'cache_control_available': self.cache_control is not None
            }
        except Exception as e:
            logger.error(f"Error getting universe cache status: {e}")
            return {'error': str(e)}
    '''

    '''
    def clear_all_cache(self):
        """Clear all cached universe selections."""
        try:
            user_count = len(self.user_universe_cache)
            self.user_universe_cache.clear()
            self.cache_initialized = False
        except Exception as e:
            logger.error(f"Error clearing all universe cache: {e}")
    '''