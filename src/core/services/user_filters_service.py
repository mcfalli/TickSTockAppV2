"""
User Filters Service - MAJOR SIMPLIFICATION (Phase 4 Cleanup)

Manages user filter preferences with database persistence.
Complex filtering logic removed - filters now used only for TickStockPL configuration.
Maintains database storage and retrieval for user preferences.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Union
from flask import has_app_context

from src.infrastructure.database import db, UserFilters, User
logger = logging.getLogger(__name__)

class UserFiltersService:
    """
    User Filters Service - MAJOR SIMPLIFICATION (Phase 4 Cleanup)
    
    Previous functionality:
    - Complex event filtering application
    - Multi-layer filter validation
    - Statistical filter analysis
    - Real-time filter processing
    
    Current functionality:
    - User preference storage and retrieval
    - Basic filter validation
    - Configuration management for TickStockPL
    - Database persistence
    """
    
    def __init__(self, app=None):
        """Initialize simplified user filters service."""
        self.app = app
        self.default_filters = self._get_default_filters()
        logger.info("UserFiltersService initialized as simplified version (Phase 4 cleanup)")

    def _get_default_filters(self) -> Dict[str, Any]:
        """Get default filter configuration."""
        return {
            'filters': {
                'highlow': {
                    'enabled': True,
                    'min_count': 1,
                    'min_volume': 0
                },
                'trending': {
                    'enabled': True,
                    'min_strength': 0
                },
                'surge': {
                    'enabled': True,
                    'min_strength': 0
                }
            },
            'universes': ['all'],
            'notifications': {
                'enabled': False
            }
        }

    def get_user_filters(self, user_id: int, filter_name: str = 'default') -> Optional[Dict[str, Any]]:
        """
        Get user filter preferences from database.
        
        Args:
            user_id: User ID
            filter_name: Filter configuration name
            
        Returns:
            Dict containing user filters or default if none exist
        """
        try:
            if not has_app_context():
                logger.warning("No Flask app context available")
                return self.default_filters.copy()
            
            user_filter = UserFilters.get_user_filter(user_id, filter_name)
            if user_filter and user_filter.filter_data:
                logger.debug(f"Retrieved filters for user {user_id}")
                return user_filter.filter_data
            else:
                logger.debug(f"No custom filters found for user {user_id}, using defaults")
                return self.default_filters.copy()
                
        except Exception as e:
            logger.error(f"Error retrieving user filters for user {user_id}: {e}")
            return self.default_filters.copy()

    def save_user_filters(self, user_id: int, filters: Dict[str, Any], filter_name: str = 'default') -> bool:
        """
        Save user filter preferences to database.
        
        Args:
            user_id: User ID
            filters: Filter configuration to save
            filter_name: Filter configuration name
            
        Returns:
            bool: True if saved successfully
        """
        try:
            if not has_app_context():
                logger.warning("No Flask app context available for saving")
                return False

            # Basic validation
            if not self._validate_filter_structure(filters):
                logger.error(f"Invalid filter structure for user {user_id}")
                return False

            # Get or create user filter record
            user_filter = UserFilters.get_user_filter(user_id, filter_name)
            if user_filter:
                # Update existing
                user_filter.filter_data = filters
                user_filter.updated_at = datetime.utcnow()
            else:
                # Create new
                user_filter = UserFilters(
                    user_id=user_id,
                    filter_name=filter_name,
                    filter_data=filters
                )
                db.session.add(user_filter)

            db.session.commit()
            logger.info(f"Saved filters for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Error saving user filters for user {user_id}: {e}")
            if has_app_context():
                db.session.rollback()
            return False

    def _validate_filter_structure(self, filters: Dict[str, Any]) -> bool:
        """
        Basic validation of filter structure.
        
        Args:
            filters: Filter configuration to validate
            
        Returns:
            bool: True if structure is valid
        """
        try:
            # Check basic structure
            if not isinstance(filters, dict):
                return False
            
            # Check for required sections
            if 'filters' not in filters:
                return False
            
            filter_config = filters['filters']
            if not isinstance(filter_config, dict):
                return False
            
            # Basic type checking for filter sections
            for section in ['highlow', 'trending', 'surge']:
                if section in filter_config:
                    if not isinstance(filter_config[section], dict):
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating filter structure: {e}")
            return False

    def get_all_user_filters(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Get all filter configurations for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of user filter configurations
        """
        try:
            if not has_app_context():
                logger.warning("No Flask app context available")
                return []
            
            user_filters = UserFilters.get_all_user_filters(user_id)
            return [filter.to_dict() for filter in user_filters]
            
        except Exception as e:
            logger.error(f"Error retrieving all user filters for user {user_id}: {e}")
            return []

    def delete_user_filter(self, user_id: int, filter_name: str) -> bool:
        """
        Delete a user filter configuration.
        
        Args:
            user_id: User ID
            filter_name: Filter configuration name to delete
            
        Returns:
            bool: True if deleted successfully
        """
        try:
            if not has_app_context():
                logger.warning("No Flask app context available")
                return False
            
            user_filter = UserFilters.get_user_filter(user_id, filter_name)
            if user_filter:
                db.session.delete(user_filter)
                db.session.commit()
                logger.info(f"Deleted filter '{filter_name}' for user {user_id}")
                return True
            else:
                logger.warning(f"Filter '{filter_name}' not found for user {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting user filter for user {user_id}: {e}")
            if has_app_context():
                db.session.rollback()
            return False

    def reset_to_defaults(self, user_id: int, filter_name: str = 'default') -> bool:
        """
        Reset user filters to default configuration.
        
        Args:
            user_id: User ID
            filter_name: Filter configuration name
            
        Returns:
            bool: True if reset successfully
        """
        return self.save_user_filters(user_id, self.default_filters.copy(), filter_name)

    def get_filter_summary(self, user_id: int) -> Dict[str, Any]:
        """
        Get summary of user filter configuration.
        
        Args:
            user_id: User ID
            
        Returns:
            Dict containing filter summary
        """
        try:
            filters = self.get_user_filters(user_id)
            filter_config = filters.get('filters', {})
            
            return {
                'user_id': user_id,
                'has_custom_filters': filters != self.default_filters,
                'highlow_enabled': filter_config.get('highlow', {}).get('enabled', False),
                'trending_enabled': filter_config.get('trending', {}).get('enabled', False),
                'surge_enabled': filter_config.get('surge', {}).get('enabled', False),
                'universes': filters.get('universes', ['all']),
                'notifications_enabled': filters.get('notifications', {}).get('enabled', False)
            }
            
        except Exception as e:
            logger.error(f"Error getting filter summary for user {user_id}: {e}")
            return {'user_id': user_id, 'error': 'Unable to retrieve filter summary'}

    def get_filters(self, user_id: int) -> Dict[str, Any]:
        """
        Get user filters (compatibility method).
        
        Args:
            user_id: User ID to get filters for
            
        Returns:
            Dict containing user filters
        """
        try:
            user_filters = UserFilters.query.filter_by(user_id=user_id).first()
            
            if user_filters and user_filters.filter_data:
                try:
                    filters = json.loads(user_filters.filter_data)
                except (json.JSONDecodeError, TypeError):
                    filters = self.default_filters
            else:
                filters = self.default_filters
                
            logger.debug(f"Retrieved filters for user {user_id}")
            return filters
            
        except Exception as e:
            logger.error(f"Failed to get filters for user {user_id}: {e}")
            return self.default_filters

# Maintain interface compatibility
def create_user_filters_service(app=None) -> UserFiltersService:
    """Factory function for user filters service"""
    return UserFiltersService(app=app)