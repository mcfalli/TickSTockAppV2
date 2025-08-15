"""
User Filters Service - Phase 4 Update
Manages user filter preferences with database persistence and validation.
Now works exclusively with typed events - no dict compatibility.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Union
from flask import has_app_context

from src.infrastructure.database import db, UserFilters, User
from config.logging_config import get_domain_logger, LogDomain
from src.core.domain.events import BaseEvent, HighLowEvent, TrendEvent, SurgeEvent

logger = get_domain_logger(LogDomain.USER_SETTINGS, 'user_filters_service')


class UserFiltersService:
    """
    Service layer for managing user filter preferences with database persistence.
    Phase 4: Works exclusively with typed events.
    """
    
    def __init__(self, app=None):
        """Initialize the user filters service."""
        self.app = app
        self.default_filters = self._get_default_filters()

    def _get_default_filters(self) -> Dict[str, Any]:
        """
        Get default filter configuration.
        
        Returns:
            dict: Default filter structure
        """
        return {
            "version": "1.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "filters": {
                "highlow": {
                    "min_count": 0,
                    "min_volume": 0
                },
                "trends": {
                    "strength": "moderate",
                    "vwap_position": "any_vwap_position", 
                    "time_window": "medium",
                    "trend_age": "all",
                    "volume_confirmation": "all_trends"
                },
                "surge": {
                    "magnitude": "moderate",
                    "trigger_type": "price_and_volume",
                    "surge_age": "all",
                    "price_range": ["penny", "low", "mid", "high"]
                }
            },
            "display_preferences": {
                "show_filter_indicators": True,
                "compact_filter_display": False
            }
        }
    
    def save_user_filters(self, user_id: int, filter_data: Dict[str, Any], filter_name: str = "default") -> bool:
        """
        Save user filter preferences to database.
        
        Args:
            user_id: User ID
            filter_data: Filter configuration data
            filter_name: Name for the filter set (default: "default")
            
        Returns:
            bool: True if saved successfully, False otherwise
        """
        try:
            # Validate user exists
            user = User.query.get(user_id)
            if not user:
                return False
            
            # Validate filter data
            if not self.validate_filter_data(filter_data):
                return False
            
            # Add metadata
            filter_data_with_meta = filter_data.copy()
            filter_data_with_meta["timestamp"] = datetime.now(timezone.utc).isoformat()
            filter_data_with_meta["version"] = "1.0"
            
            # Check if filter already exists
            existing_filter = UserFilters.query.filter_by(
                user_id=user_id,
                filter_name=filter_name
            ).first()
            
            if existing_filter:
                # Update existing filter
                existing_filter.filter_data = filter_data_with_meta
                existing_filter.updated_at = datetime.now(timezone.utc)
            else:
                # Create new filter
                new_filter = UserFilters(
                    user_id=user_id,
                    filter_name=filter_name,
                    filter_data=filter_data_with_meta
                )
                db.session.add(new_filter)
            
            db.session.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving user filters for user {user_id}: {e}", exc_info=True)
            try:
                db.session.rollback()
            except Exception as rollback_error:
                logger.error(f"Error during rollback: {rollback_error}")
            return False
    
    def load_user_filters(self, user_id: int, filter_name: str = "default") -> Dict[str, Any]:
        """
        Load user filter preferences with proper value preservation.
        
        Args:
            user_id: User ID
            filter_name: Name of the filter set to load (default: "default")
            
        Returns:
            dict: Filter configuration data or default filters
        """
        try:
            # If we have an app reference and no current context, use app context
            if self.app and not has_app_context():
                with self.app.app_context():
                    return self._load_filters_internal(user_id, filter_name)
            else:
                # Either we have context already or no app reference
                return self._load_filters_internal(user_id, filter_name)
                    
        except RuntimeError as e:
            if "Working outside of application context" in str(e):
                logger.error(f"FILTER_LOAD_FIXED: No Flask app context for user {user_id}")
                return self.default_filters
            raise
        except Exception as e:
            logger.error(f"FILTER_LOAD_FIXED: Error loading user filters for user {user_id}: {e}", exc_info=True)
            return self.default_filters

    def _load_filters_internal(self, user_id: int, filter_name: str) -> Dict[str, Any]:
        """Internal method with existing filter loading logic."""
        # Validate user exists
        user = User.query.get(user_id)
        if not user:
            return self.default_filters
        
        # Get user filter from src.infrastructure.database
        user_filter = UserFilters.query.filter_by(
            user_id=user_id,
            filter_name=filter_name
        ).first()
        
        if user_filter:
            filter_data = user_filter.filter_data
            
            # CRITICAL: Validate the data structure without modification
            if isinstance(filter_data, dict) and 'filters' in filter_data:
                # Check specific values for debugging
                highlow_section = filter_data.get('filters', {}).get('highlow', {})
                min_count = highlow_section.get('min_count', 'NOT_FOUND')
                min_volume = highlow_section.get('min_volume', 'NOT_FOUND')
                
                # CRITICAL: Only validate structure, don't modify values
                if self.validate_filter_data(filter_data):
                    return filter_data
                else:
                    # Don't return defaults immediately - log what's wrong first
                    return self.default_filters
            else:
                return self.default_filters
        else:
            return self.default_filters

    
    def get_all_user_filters(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Get all filter sets for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            list: List of filter sets with metadata
        """
        try:
            user_filters = UserFilters.query.filter_by(user_id=user_id).all()
            
            result = []
            for user_filter in user_filters:
                result.append({
                    'filter_name': user_filter.filter_name,
                    'filter_data': user_filter.filter_data,
                    'created_at': user_filter.created_at.isoformat(),
                    'updated_at': user_filter.updated_at.isoformat()
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting all user filters for user {user_id}: {e}", exc_info=True)
            return []
    
    def delete_user_filters(self, user_id: int, filter_name: str = "default") -> bool:
        """
        Delete user filter preferences.
        
        Args:
            user_id: User ID
            filter_name: Name of the filter set to delete
            
        Returns:
            bool: True if deleted successfully, False otherwise
        """
        try:
            user_filter = UserFilters.query.filter_by(
                user_id=user_id,
                filter_name=filter_name
            ).first()
            
            if user_filter:
                db.session.delete(user_filter)
                db.session.commit()
                
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"Error deleting user filters for user {user_id}: {e}", exc_info=True)
            try:
                db.session.rollback()
            except Exception as rollback_error:
                logger.error(f"Error during rollback: {rollback_error}")
            return False
    
    def validate_filter_data(self, filter_data: Dict[str, Any]) -> bool:
        """
        Validate filter data with detailed logging.
        
        Args:
            filter_data: Filter configuration to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        try:
            if not isinstance(filter_data, dict):
                return False
            
            # Check required top-level structure
            if 'filters' not in filter_data:
                return False
            
            filters = filter_data['filters']
            if not isinstance(filters, dict):
                return False
            
            # Log the filters structure for debugging
            
            # Validate highlow filters with detailed logging
            if 'highlow' in filters:
                highlow_valid = self._validate_highlow_filters(filters['highlow'])
                if not highlow_valid:
                    return False
            
            # Validate trend filters
            if 'trends' in filters:
                trends_valid = self._validate_trend_filters(filters['trends'])
                if not trends_valid:
                    return False
            
            # Validate surge filters
            if 'surge' in filters:
                surge_valid = self._validate_surge_filters(filters['surge'])
                if not surge_valid:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"FILTER_VALIDATION: Error validating filter data: {e}")
            return False
    
    def _validate_highlow_filters(self, highlow_filters: Dict[str, Any]) -> bool:
        """Validate high/low filter configuration with detailed logging."""
        try:
            
            min_count = highlow_filters.get('min_count', 'KEY_MISSING')
            min_volume = highlow_filters.get('min_volume', 'KEY_MISSING')
            
            
            # Validate min_count
            if min_count == 'KEY_MISSING':
                return False
                
            if not isinstance(min_count, (int, float)) or min_count < 0:
                return False
            
            # Validate min_volume
            if min_volume == 'KEY_MISSING':
                return False
                
            if not isinstance(min_volume, (int, float)) or min_volume < 0:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"FILTER_VALIDATION_HIGHLOW: Error validating highlow filters: {e}")
            return False
    
    def _validate_trend_filters(self, trend_filters: Dict[str, Any]) -> bool:
        """Validate trend filter configuration."""
        try:
            valid_strengths = ['weak', 'moderate', 'strong']
            valid_vwap_positions = ['uptrend_above_vwap', 'downtrend_below_vwap', 'any_vwap_position']
            valid_time_windows = ['short', 'medium', 'long']
            valid_trend_ages = ['all', 'fresh', 'recent']
            valid_volume_confirmations = ['volume_confirmed', 'all_trends']
            
            strength = trend_filters.get('strength')
            if strength not in valid_strengths:
                return False
            
            vwap_position = trend_filters.get('vwap_position')
            if vwap_position not in valid_vwap_positions:
                return False
            
            time_window = trend_filters.get('time_window')
            if time_window not in valid_time_windows:
                return False
            
            trend_age = trend_filters.get('trend_age')
            if trend_age not in valid_trend_ages:
                return False
            
            volume_confirmation = trend_filters.get('volume_confirmation')
            if volume_confirmation not in valid_volume_confirmations:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating trend filters: {e}")
            return False
    
    def _validate_surge_filters(self, surge_filters: Dict[str, Any]) -> bool:
        """Validate surge filter configuration."""
        try:
            valid_magnitudes = ['weak', 'moderate', 'strong']
            valid_trigger_types = ["price", "volume", "price_and_volume"]#, "price_driven", "volume_driven"]
            valid_surge_ages = ['all', 'fresh', 'recent']
            valid_price_ranges = ['penny', 'low', 'mid', 'high']
            
            magnitude = surge_filters.get('magnitude')
            if magnitude not in valid_magnitudes:
                return False
            
            trigger_type = surge_filters.get('trigger_type')
            if trigger_type not in valid_trigger_types:
                return False
            
            surge_age = surge_filters.get('surge_age')
            if surge_age not in valid_surge_ages:
                return False
            
            price_range = surge_filters.get('price_range', [])
            if not isinstance(price_range, list):
                return False
            
            for price in price_range:
                if price not in valid_price_ranges:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating surge filters: {e}")
            return False
    
    def apply_filters_to_stock_data(self, stock_data: Dict[str, Any], user_filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply user filters to stock data containing typed events.
        Phase 4: Works exclusively with typed events.
        """
        try:
            if not user_filters or not user_filters.get('filters'):
                return stock_data
            
            # Log filter configuration being applied
            filters = user_filters['filters']
            
            filtered_data = stock_data.copy()
            
            # Apply high/low filters
            if 'highs' in filtered_data:
                original_highs_count = len(filtered_data['highs'])
                filtered_data['highs'] = self._filter_high_low_events(
                    filtered_data['highs'], filters.get('highlow', {}), 'high'
                )
                filtered_highs_count = len(filtered_data['highs'])
            
            if 'lows' in filtered_data:
                original_lows_count = len(filtered_data['lows'])
                filtered_data['lows'] = self._filter_high_low_events(
                    filtered_data['lows'], filters.get('highlow', {}), 'low'
                )
                filtered_lows_count = len(filtered_data['lows'])
            
            # Apply trending filters
            if 'trending' in filtered_data:
                filtered_data['trending'] = self._filter_trending_events(
                    filtered_data['trending'], filters.get('trends', {})
                )
            
            # Apply surge filters
            if 'surging' in filtered_data:
                filtered_data['surging'] = self._filter_surging_events(
                    filtered_data['surging'], filters.get('surge', {})
                )
            
            # Update counts to reflect filtering
            if 'counts' in filtered_data:
                filtered_data['counts']['highs'] = len(filtered_data.get('highs', []))
                filtered_data['counts']['lows'] = len(filtered_data.get('lows', []))
            
            return filtered_data
            
        except Exception as e:
            logger.error(f"FILTER_SERVICE_DEBUG: Error applying filters to stock data: {e}", exc_info=True)
            return stock_data
        
    def _filter_high_low_events(self, events: List[Union[Dict, BaseEvent]], filters: Dict[str, Any], event_type: str) -> List[Union[Dict, BaseEvent]]:
        """Filter high/low events with support for both typed and dict events."""
        try:
            min_count = filters.get('min_count', 0)
            min_volume = filters.get('min_volume', 0)
            
            if min_count == 0 and min_volume == 0:
                return events
            
            filtered_events = []
            count_filtered = 0
            volume_filtered = 0
            
            for event in events:
                # Phase 4: Handle both typed and dict events
                if isinstance(event, BaseEvent):
                    # Typed event - direct attribute access
                    event_count = event.count
                    event_volume = event.volume or 0
                    ticker = event.ticker
                else:
                    # Dict event - use get() method
                    event_count = event.get('count', 0)
                    event_volume = event.get('volume', 0) or 0
                    ticker = event.get('ticker', 'unknown')
                
                # Check count filter
                if min_count > 0 and event_count < min_count:
                    count_filtered += 1
                    continue
                
                # Check volume filter
                if min_volume > 0 and event_volume < min_volume:
                    volume_filtered += 1
                    continue
                
                filtered_events.append(event)
            
            removed_count = len(events) - len(filtered_events)
  
            
            return filtered_events
            
        except Exception as e:
            logger.error(f"FILTER_HIGH_LOW_DEBUG: Error filtering {event_type} events: {e}")
            return events
    
    def _filter_trending_events(self, trending_data: Dict, filters: Dict[str, Any]) -> Dict:
        """
        Filter trending events based on criteria.
        Phase 4: Direct typed event access only.
        """
        try:
            if not isinstance(trending_data, dict):
                return trending_data
            
            filtered_trending = {}
            
            for direction in ['up', 'down']:
                trends = trending_data.get(direction, [])
                filtered_trends = []
                
                for trend in trends:
                    # Phase 4: Direct attribute access for typed events
                    if isinstance(trend, TrendEvent):
                        # Typed event
                        trend_strength = trend.trend_strength
                        ticker = trend.ticker
                    else:
                        # Dict event fallback
                        trend_strength = trend.get('trend_strength', 'moderate')
                        ticker = trend.get('ticker', 'unknown')
                    
                    # Check strength filter
                    if not self._matches_strength_filter(trend_strength, filters.get('strength', 'moderate')):
                        continue
                    
                    # Check VWAP position filter
                    if not self._matches_vwap_filter(trend, direction, filters.get('vwap_position', 'any_vwap_position')):
                        continue
                    
                    # Check time window filter (based on trend age)
                    if not self._matches_time_window_filter(trend, filters.get('time_window', 'medium')):
                        continue
                    
                    # Check trend age filter
                    if not self._matches_trend_age_filter(trend, filters.get('trend_age', 'all')):
                        continue
                    
                    # Check volume confirmation filter
                    if not self._matches_volume_confirmation_filter(trend, filters.get('volume_confirmation', 'all_trends')):
                        continue
                    
                    filtered_trends.append(trend)
                
                filtered_trending[direction] = filtered_trends
            
            return filtered_trending
            
        except Exception as e:
            logger.error(f"Error filtering trending events: {e}")
            return trending_data
    
    def _filter_surging_events(self, surging_data: Dict, filters: Dict[str, Any]) -> Dict:
        """
        Filter surging events based on criteria.
        Phase 4: Direct typed event access only.
        """
        try:
            # Handle both old format (list) and new format (dict with up/down)
            if isinstance(surging_data, list):
                # Old format - convert to new format
                surging_dict = {'up': [], 'down': []}
                for surge in surging_data:
                    if isinstance(surge, SurgeEvent):
                        direction = surge.direction
                    else:
                        direction = surge.get('direction', 'up')
                    
                    if direction in ['up', '↑']:
                        surging_dict['up'].append(surge)
                    else:
                        surging_dict['down'].append(surge)
                surging_data = surging_dict
            
            filtered_surging = {'up': [], 'down': []}
            
            for direction in ['up', 'down']:
                surges = surging_data.get(direction, [])
                
                for surge in surges:
                    # Phase 4: Direct attribute access for typed events
                    if isinstance(surge, SurgeEvent):
                        # Typed event
                        surge_strength = surge.surge_strength
                        trigger_type = surge.surge_trigger_type
                    else:
                        # Dict event fallback
                        surge_strength = surge.get('surge_strength', 'moderate')
                        trigger_type = surge.get('surge_trigger_type', 'price_and_volume')
                    
                    # Check magnitude filter
                    if not self._matches_strength_filter(surge_strength, filters.get('magnitude', 'moderate')):
                        continue
                    
                    # Check trigger type filter
                    if not self._matches_trigger_type_filter(trigger_type, filters.get('trigger_type', 'price_and_volume')):
                        continue
                    
                    # Check surge age filter
                    if not self._matches_surge_age_filter(surge, filters.get('surge_age', 'all')):
                        continue
                    
                    # Check price range filter
                    if not self._matches_price_range_filter(surge, filters.get('price_range', ['penny', 'low', 'mid', 'high'])):
                        continue
                    
                    filtered_surging[direction].append(surge)
            
            return filtered_surging
            
        except Exception as e:
            logger.error(f"Error filtering surging events: {e}")
            return surging_data
    
    def _matches_strength_filter(self, event_strength: str, filter_strength: str) -> bool:
        """Check if event strength matches filter criteria."""
        strength_levels = {
            'weak': 0,
            'moderate': 1,
            'strong': 2,
            'extreme': 3,  # For future use
            'neutral': -1  # Special case for trends
        }
        
        # Get numeric levels
        event_level = strength_levels.get(event_strength, 1)
        filter_level = strength_levels.get(filter_strength, 0)
        
        # Event must be at least as strong as filter
        return event_level >= filter_level
    
    def _matches_vwap_filter(self, trend: Union[Dict, TrendEvent], direction: str, vwap_filter: str) -> bool:
        """
        Check if trend matches VWAP position filter.
        Phase 4: Direct typed event access.
        """
        if vwap_filter == 'any_vwap_position':
            return True
        
        # Get price and VWAP
        if isinstance(trend, TrendEvent):
            price = trend.price
            vwap = trend.vwap or price
            vwap_position = getattr(trend, 'trend_vwap_position', None)
        else:
            price = trend.get('price', 0)
            vwap = trend.get('vwap', price)
            vwap_position = trend.get('trend_vwap_position')
        
        if vwap_filter == 'uptrend_above_vwap':
            if vwap_position:
                return direction == 'up' and vwap_position == 'above'
            return direction == 'up' and price > vwap
        elif vwap_filter == 'downtrend_below_vwap':
            if vwap_position:
                return direction == 'down' and vwap_position == 'below'
            return direction == 'down' and price < vwap
        
        return True
    
    def _matches_time_window_filter(self, trend: Union[Dict, TrendEvent], time_window_filter: str) -> bool:
        """
        Check if trend matches time window filter.
        Phase 4: Direct typed event access.
        """
        # Map time windows to approximate age thresholds
        time_window_mapping = {
            'short': 180,   # 3 minutes
            'medium': 360,  # 6 minutes  
            'long': 600     # 10 minutes
        }
        
        max_age = time_window_mapping.get(time_window_filter, 360)
        
        # Get trend age
        if isinstance(trend, TrendEvent):
            trend_age = getattr(trend, 'trend_age', 0)
        else:
            trend_age = trend.get('trend_age', 0)
        
        return trend_age <= max_age
    
    def _matches_trend_age_filter(self, trend: Union[Dict, TrendEvent], age_filter: str) -> bool:
        """
        Check if trend matches age filter.
        Phase 4: Direct typed event access.
        """
        if age_filter == 'all':
            return True
        
        # Get trend age
        if isinstance(trend, TrendEvent):
            trend_age = getattr(trend, 'trend_age', 0)
        else:
            trend_age = trend.get('trend_age', 0)
        
        if age_filter == 'fresh':
            return trend_age < 120  # Less than 2 minutes
        elif age_filter == 'recent':
            return trend_age < 300  # Less than 5 minutes
        
        return True
    
    def _matches_volume_confirmation_filter(self, trend: Union[Dict, BaseEvent], volume_filter: str) -> bool:
        """Check if trend matches volume confirmation filter."""
        if volume_filter == 'all_trends':
            return True
        elif volume_filter == 'volume_confirmed':
            # Check if trend has volume confirmation
            if isinstance(trend, BaseEvent):
                volume_confirmed = getattr(trend, 'volume_confirmed', False)
                volume_multiplier = getattr(trend, 'volume_multiplier', 1.0)
                rel_volume = trend.rel_volume
            else:
                volume_confirmed = trend.get('volume_confirmed', False)
                volume_multiplier = trend.get('volume_multiplier', 1.0)
                rel_volume = trend.get('rel_volume', 1.0)
            
            return volume_confirmed or volume_multiplier > 1.5 or rel_volume > 1.5
        
        return True
    
    def _matches_trigger_type_filter(self, event_trigger: str, filter_trigger: str) -> bool:
        """Check if surge trigger type matches filter."""
        if filter_trigger == 'price_and_volume':
            return event_trigger in ['price_and_volume', 'price', 'volume']
        elif filter_trigger == 'price':
            return event_trigger in ['price', 'price_and_volume', 'price_only']
        elif filter_trigger == 'volume':
            return event_trigger in ['volume', 'price_and_volume', 'volume_only']
        
        return True
    
    def _matches_surge_age_filter(self, surge: Union[Dict, SurgeEvent], age_filter: str) -> bool:
        """
        Check if surge matches age filter.
        Phase 4: Direct typed event access.
        """
        if age_filter == 'all':
            return True
        
        # Get surge age
        if isinstance(surge, SurgeEvent):
            surge_age = getattr(surge, 'surge_age', 0)
        else:
            surge_age = surge.get('surge_age', 0)
        
        if age_filter == 'fresh':
            return surge_age < 30   # Less than 30 seconds
        elif age_filter == 'recent':
            return surge_age < 120  # Less than 2 minutes
        
        return True
    
    def _matches_price_range_filter(self, surge: Union[Dict, BaseEvent], price_ranges: List[str]) -> bool:
        """Check if surge price matches range filter."""
        if not price_ranges:
            return True
        
        # Get price
        if isinstance(surge, BaseEvent):
            price = surge.price
        else:
            price = surge.get('price', 0)
        
        for price_range in price_ranges:
            if price_range == 'penny' and price < 1.0:
                return True
            elif price_range == 'low' and 1.0 <= price < 25.0:
                return True
            elif price_range == 'mid' and 25.0 <= price < 100.0:
                return True
            elif price_range == 'high' and price >= 100.0:
                return True
        
        return False
    
    def _get_filter_summary(self, user_filters: Dict[str, Any]) -> str:
        """Get a summary description of active filters."""
        try:
            if not user_filters or not user_filters.get('filters'):
                return "No filters active"
            
            filters = user_filters['filters']
            active_filters = []
            
            # Check high/low filters
            highlow = filters.get('highlow', {})
            if highlow.get('min_count', 0) > 0:
                active_filters.append(f"Count≥{highlow['min_count']}")
            if highlow.get('min_volume', 0) > 0:
                vol_text = f"{highlow['min_volume']:,}"
                if highlow['min_volume'] >= 1000000:
                    vol_text = f"{highlow['min_volume'] // 1000000}M"
                elif highlow['min_volume'] >= 1000:
                    vol_text = f"{highlow['min_volume'] // 1000}K"
                active_filters.append(f"Vol≥{vol_text}")
            
            # Check trend filters
            trends = filters.get('trends', {})
            if trends.get('strength') != 'moderate':
                active_filters.append(f"Trend:{trends['strength']}")
            if trends.get('trend_age') != 'all':
                active_filters.append(f"Age:{trends['trend_age']}")
            
            # Check surge filters
            surge = filters.get('surge', {})
            if surge.get('magnitude') != 'moderate':
                active_filters.append(f"Surge:{surge['magnitude']}")
            if len(surge.get('price_range', [])) < 4:
                active_filters.append("PriceRange")
            
            if not active_filters:
                return "Default filters active"
            
            return ', '.join(active_filters[:3])  # Limit to 3 items
            
        except Exception as e:
            logger.error(f"Error generating filter summary: {e}")
            return "Filter summary error"