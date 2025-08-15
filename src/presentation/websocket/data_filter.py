"""
WebSocket Data Filter - Phase 4 Update

Handles all data filtering operations for WebSocket emissions.
Phase 4: Pure typed events only - no dict compatibility
"""

from config.logging_config import get_domain_logger, LogDomain
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime  
import time
from src.core.domain.events.base import BaseEvent
from src.core.domain.events.trend import TrendEvent
from src.core.domain.events.surge import SurgeEvent
from src.core.domain.events.highlow import HighLowEvent

logger = get_domain_logger(LogDomain.CORE, 'websocket_data_filter')


class WebSocketDataFilter:
    """
    Handles all data filtering operations for WebSocket emissions.
    Phase 4: Works exclusively with typed events.
    """
    
    def __init__(self, cache_control=None):
        """Initialize data filter."""
        self.cache_control = cache_control
        
        # Filtering statistics
        self.filter_stats = {
            'universe_filtering_time_ms': 0,
            'user_filtering_time_ms': 0,
            'total_events_filtered': 0,
            'filter_operations': 0
        }

    '''
    def apply_universe_filtering(self, data: Dict, user_id: int, 
                           universes: List[str]) -> Dict:
        """
        Apply universe filtering to stock data.
        
        Args:
            data: Stock data to filter
            user_id: User ID for context
            universes: List of universe keys to filter by
            
        Returns:
            dict: Universe-filtered stock data
        """
        try:
            start_time = time.time()
            
            logger.debug(f"WEBSOCKET-FILTER: USER_UNIVERSE_FILTER_{user_id}: Applying filtering with universes: {universes}")
            
            # Copy data for filtering
            filtered_data = data.copy()
            
            # Get all tickers in the user's universes
            user_universe_tickers = set()
            if self.cache_control:
                for universe_name in universes:
                    universe_tickers = self.cache_control.get_universe_tickers(universe_name)
                    if universe_tickers:
                        user_universe_tickers.update(universe_tickers)
            
            logger.debug(f"WEBSOCKET-FILTER: USER_UNIVERSE_FILTER_{user_id}: Total tickers in universes: {len(user_universe_tickers)}")
            
            # Filter each data category
            filtered_highs, filtered_lows = self._filter_high_low_events(
                data.get('highs', []), 
                data.get('lows', []), 
                universes
            )
            
            filtered_trending = self._filter_trending_events(
                data.get('trending', {}), 
                universes
            )
            
            # Pass user_universe_tickers instead of universes
            filtered_surging = self._filter_surging_events(
                data.get('surging', {}),
                user_universe_tickers
            )
            
            # Update the filtered data
            filtered_data['highs'] = filtered_highs['in_universe']
            filtered_data['lows'] = filtered_lows['in_universe']
            filtered_data['trending'] = filtered_trending['in_universe']
            filtered_data['surging'] = filtered_surging
            
            # Update counts
            if 'counts' in filtered_data:
                filtered_data['counts']['highs'] = len(filtered_highs['in_universe'])
                filtered_data['counts']['lows'] = len(filtered_lows['in_universe'])
            
            # Log results
            self._log_filtering_results(data, filtered_data, user_id)
            
            # Update statistics
            elapsed_ms = (time.time() - start_time) * 1000
            self.filter_stats['universe_filtering_time_ms'] += elapsed_ms
            self.filter_stats['filter_operations'] += 1
            
            if elapsed_ms > 10:
                logger.warning(f"WEBSOCKET-FILTER: USER_UNIVERSE_FILTER_{user_id}: Slow filtering: {elapsed_ms:.1f}ms")
            
            return filtered_data
            
        except Exception as e:
            logger.error(f"Error applying universe filtering for user {user_id}: {e}", exc_info=True)
            return data
    '''    

    '''
    def apply_user_filters(self, data: Dict, user_id: int, 
                          filters: Dict) -> Dict:
        """
        Apply user-specific filters to stock data.
        
        Args:
            data: Stock data to filter
            user_id: User ID for context
            filters: User filter settings
            
        Returns:
            dict: Filtered stock data
        """
        try:
            if not filters or not filters.get('filters'):
                logger.debug(f"WEBSOCKET-FILTER: USER_FILTER_NONE: No filters for user {user_id}")
                return data
            
            start_time = time.time()
            
            # Apply filters based on type
            filtered_data = data.copy()
            
            # Apply high/low filters
            if 'highlow' in filters['filters']:
                filtered_data = self._apply_highlow_filters(filtered_data, filters['filters']['highlow'])
            
            # Apply trend filters
            if 'trends' in filters['filters']:
                filtered_data = self._apply_trend_filters(filtered_data, filters['filters']['trends'])
            
            # Apply surge filters
            if 'surges' in filters['filters']:
                filtered_data = self._apply_surge_filters(filtered_data, filters['filters']['surges'])
            
            # Update statistics
            elapsed_ms = (time.time() - start_time) * 1000
            self.filter_stats['user_filtering_time_ms'] += elapsed_ms
            
            logger.debug(f"WEBSOCKET-FILTER: USER_FILTERING_{user_id}: Applied filters in {elapsed_ms:.1f}ms")
            
            return filtered_data
            
        except Exception as e:
            logger.error(f"Error applying user filters for user {user_id}: {e}")
            return data
    '''
    def _filter_high_low_events(self, highs: List, lows: List, 
                           universes: List[str]) -> Tuple[Dict, Dict]:
        """
        Filter high and low events based on universe membership.
        Phase 4: Handle dict data at transport boundary.
        """
        highs_in_universe = []
        highs_filtered_out = []
        lows_in_universe = []
        lows_filtered_out = []
        
        # Process high events - handle as dicts at transport boundary
        for high_event in highs:
            # Handle both typed events and dicts
            if isinstance(high_event, dict):
                ticker = high_event.get('ticker')
            else:
                ticker = high_event.ticker
            
            if ticker and self.cache_control:
                membership = self.cache_control.log_universe_membership(ticker, universes)
                if membership['is_in_any_user_universe']:
                    highs_in_universe.append(high_event)
                else:
                    highs_filtered_out.append(high_event)
            else:
                highs_in_universe.append(high_event)
        
        # Process low events - handle as dicts at transport boundary
        for low_event in lows:
            # Handle both typed events and dicts
            if isinstance(low_event, dict):
                ticker = low_event.get('ticker')
            else:
                ticker = low_event.ticker
            
            if ticker and self.cache_control:
                membership = self.cache_control.log_universe_membership(ticker, universes)
                if membership['is_in_any_user_universe']:
                    lows_in_universe.append(low_event)
                else:
                    lows_filtered_out.append(low_event)
            else:
                lows_in_universe.append(low_event)
        
        return (
            {'in_universe': highs_in_universe, 'filtered_out': highs_filtered_out},
            {'in_universe': lows_in_universe, 'filtered_out': lows_filtered_out}
        )
    
    def _filter_trending_events(self, trending: Dict, universes: List[str]) -> Dict[str, Any]:
        """Filter trending events based on universe membership."""
        trending_up = trending.get('up', [])
        trending_down = trending.get('down', [])
        
        trending_up_in_universe = []
        trending_up_filtered = []
        trending_down_in_universe = []
        trending_down_filtered = []
        
        # Process up trending
        for trend_stock in trending_up:
            ticker = trend_stock.get('ticker')
            if ticker and self.cache_control:
                membership = self.cache_control.log_universe_membership(ticker, universes)
                if membership['is_in_any_user_universe']:
                    trending_up_in_universe.append(trend_stock)
                else:
                    trending_up_filtered.append(trend_stock)
            else:
                trending_up_in_universe.append(trend_stock)
        
        # Process down trending
        for trend_stock in trending_down:
            ticker = trend_stock.get('ticker')
            if ticker and self.cache_control:
                membership = self.cache_control.log_universe_membership(ticker, universes)
                if membership['is_in_any_user_universe']:
                    trending_down_in_universe.append(trend_stock)
                else:
                    trending_down_filtered.append(trend_stock)
            else:
                trending_down_in_universe.append(trend_stock)
        
        return {
            'in_universe': {
                'up': trending_up_in_universe,
                'down': trending_down_in_universe
            },
            'filtered_out': {
                'up': trending_up_filtered,
                'down': trending_down_filtered
            }
        }
    
    def _filter_surging_events(self, surging_data, user_universe_tickers):
        """Filter surging events based on user universe membership."""
        if not surging_data:
            return {'up': [], 'down': []}
        
        # Handle new grouped structure
        if isinstance(surging_data, dict) and 'up' in surging_data and 'down' in surging_data:
            filtered_surging = {
                'up': [],
                'down': []
            }
            
            # Filter up surges
            for surge_stock in surging_data.get('up', []):
                ticker = surge_stock.get('ticker')
                if ticker and ticker in user_universe_tickers:
                    filtered_surging['up'].append(surge_stock)
                
            # Filter down surges
            for surge_stock in surging_data.get('down', []):
                ticker = surge_stock.get('ticker')
                if ticker and ticker in user_universe_tickers:
                    filtered_surging['down'].append(surge_stock)
            
            return filtered_surging
        else:
            logger.error(f"Unexpected surging data structure: {type(surging_data)}")
            return {'up': [], 'down': []}
    
    def _apply_highlow_filters(self, data: Dict, highlow_filters: Dict) -> Dict:
        """
        Apply high/low event filters.
        Phase 4: Handle dict data at transport boundary.
        """
        # Get filter settings with defaults
        min_count = highlow_filters.get('min_count', 0)
        min_volume = highlow_filters.get('min_volume', 0)
        
        # Only apply filters if there are actual criteria set
        if min_count > 0 or min_volume > 0:
            # Filter highs - handle as dicts
            filtered_highs = []
            for event in data.get('highs', []):
                # Handle both typed events and dicts
                if isinstance(event, dict):
                    count = event.get('count', 0)
                    volume = event.get('volume', 0)
                    ticker = event.get('ticker')
                else:
                    count = event.count
                    volume = event.volume
                    ticker = event.ticker
                
                if count >= min_count and volume >= min_volume:
                    filtered_highs.append(event)
                else:
                    logger.debug(f"WEBSOCKET-FILTER: High filtered out: {ticker} count={count} (min={min_count}) volume={volume} (min={min_volume})")
            
            data['highs'] = filtered_highs
            
            # Filter lows - handle as dicts
            filtered_lows = []
            for event in data.get('lows', []):
                # Handle both typed events and dicts
                if isinstance(event, dict):
                    count = event.get('count', 0)
                    volume = event.get('volume', 0)
                    ticker = event.get('ticker')
                else:
                    count = event.count
                    volume = event.volume
                    ticker = event.ticker
                
                if count >= min_count and volume >= min_volume:
                    filtered_lows.append(event)
                else:
                    logger.debug(f"WEBSOCKET-FILTER: Low filtered out: {ticker} count={count} (min={min_count}) volume={volume} (min={min_volume})")
            
            data['lows'] = filtered_lows
            
            # Log filtering summary
            logger.debug(f"WEBSOCKET-FILTER: High/Low filter applied: {len(filtered_highs)} highs, {len(filtered_lows)} lows passed")
        
        return data
    
    def _apply_trend_filters(self, data: Dict, trend_filters: Dict) -> Dict:
        """
        Apply trend filters.
        Phase 4: Handle dict data at transport boundary.
        """
        # Get filter settings with defaults
        strength_filter = trend_filters.get('strength', 'weak')
        vwap_filter = trend_filters.get('vwap_position', 'any')
        
        # Get the trending data
        trending = data.get('trending', {})
        filtered_trending = {'up': [], 'down': []}
        
        # Define strength levels for comparison
        strength_levels = {'weak': 0, 'moderate': 1, 'strong': 2}
        min_strength = strength_levels.get(strength_filter, 0)
        
        # Process each direction (up/down)
        for direction in ['up', 'down']:
            for stock in trending.get(direction, []):
                # Handle both typed events and dicts
                if isinstance(stock, dict):
                    stock_strength = stock.get('trend_strength', 'moderate')
                    vwap_position = stock.get('vwap_position', 'above')
                    ticker = stock.get('ticker')
                else:
                    stock_strength = stock.trend_strength
                    vwap_position = stock.vwap_position
                    ticker = stock.ticker
                
                # Apply strength filter
                if strength_levels.get(stock_strength, 1) >= min_strength:
                    # Apply VWAP position filter
                    if vwap_filter == 'any':
                        filtered_trending[direction].append(stock)
                    else:
                        if (vwap_filter == 'above_vwap' and vwap_position == 'above') or \
                        (vwap_filter == 'below_vwap' and vwap_position == 'below'):
                            filtered_trending[direction].append(stock)
                        elif vwap_filter == 'any_vwap_position':
                            filtered_trending[direction].append(stock)
                else:
                    logger.debug(f"WEBSOCKET-FILTER: Trend filtered out: {ticker} strength={stock_strength} (min={strength_filter})")
        
        # Update data with filtered results
        data['trending'] = filtered_trending
        return data

    def _apply_surge_filters(self, data: Dict, surge_filters: Dict) -> Dict:
        """
        Apply surge filters.
        Phase 4: Handle dict data at transport boundary.
        """
        # Get filter settings with defaults
        strength_filter = surge_filters.get('strength', 'weak')
        trigger_filter = surge_filters.get('trigger_type', 'any')
        
        # Get the surging data
        surging = data.get('surging', {})
        filtered_surging = {'up': [], 'down': []}
        
        # Define strength levels
        strength_levels = {'weak': 0, 'moderate': 1, 'strong': 2}
        min_strength = strength_levels.get(strength_filter, 0)
        
        # Process both up and down surges
        for direction in ['up', 'down']:
            for surge in surging.get(direction, []):
                # Handle both typed events and dicts
                if isinstance(surge, dict):
                    surge_strength = surge.get('strength', 'moderate')
                    surge_trigger = surge.get('trigger_type', 'price_and_volume')
                    ticker = surge.get('ticker')
                else:
                    surge_strength = surge.surge_strength
                    surge_trigger = surge.surge_trigger_type
                    ticker = surge.ticker
                
                # Apply strength filter
                if strength_levels.get(surge_strength, 1) >= min_strength:
                    # Apply trigger type filter
                    if trigger_filter == 'any' or trigger_filter == 'price_and_volume':
                        filtered_surging[direction].append(surge)
                    elif trigger_filter == surge_trigger:
                        filtered_surging[direction].append(surge)
                    elif trigger_filter == 'price' and surge_trigger in ['price', 'price_only']:
                        filtered_surging[direction].append(surge)
                    elif trigger_filter == 'volume' and surge_trigger in ['volume', 'volume_only']:
                        filtered_surging[direction].append(surge)
                    else:
                        logger.debug(f"WEBSOCKET-FILTER: Surge filtered out: {ticker} trigger={surge_trigger} (filter={trigger_filter})")
                else:
                    logger.debug(f"WEBSOCKET-FILTER: Surge filtered out: {ticker} strength={surge_strength} (min={strength_filter})")
        
        # Update data with filtered results
        data['surging'] = filtered_surging
        return data
    
    def _matches_strength_filter(self, event_strength: str, filter_strength: str) -> bool:
        """
        Check if event strength matches filter criteria.
        Phase 4: Direct comparison only.
        """
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

    def _get_universe_tickers_from_cache(self, universe_names: List[str]) -> set:
        """Get all tickers from specified universes."""
        all_tickers = set()
        
        if not self.cache_control:
            return all_tickers
        
        for universe_name in universe_names:
            # Try different methods to get universe tickers
            if hasattr(self.cache_control, 'get_universe_tickers'):
                tickers = self.cache_control.get_universe_tickers(universe_name)
                if tickers:
                    all_tickers.update(tickers)
            elif hasattr(self.cache_control, 'get_universe'):
                # Fallback method
                universe_data = self.cache_control.get_universe(universe_name)
                if universe_data and isinstance(universe_data, list):
                    all_tickers.update(universe_data)
        
        return all_tickers
    
    def _count_events(self, data: Dict, detailed: bool = False) -> Dict[str, int]:
        """
        Count events in data structure.
        Phase 4: Works with typed events in lists.
        """
        trending = data.get('trending', {})
        surging = data.get('surging', {})
        
        # Count events
        highs_count = len(data.get('highs', []))
        lows_count = len(data.get('lows', []))
        
        # Handle trending structure
        if isinstance(trending, dict):
            trending_up_count = len(trending.get('up', []))
            trending_down_count = len(trending.get('down', []))
            trending_total = trending_up_count + trending_down_count
        else:
            trending_up_count = trending_down_count = trending_total = 0
        
        # Handle surging structure
        if isinstance(surging, dict) and 'up' in surging and 'down' in surging:
            surging_up_count = len(surging.get('up', []))
            surging_down_count = len(surging.get('down', []))
            surging_total = surging_up_count + surging_down_count
        else:
            surging_up_count = surging_down_count = surging_total = 0
        
        counts = {
            'highs': highs_count,
            'lows': lows_count,
            'trending': trending_total,
            'surging': surging_total
        }
        
        if detailed:
            counts.update({
                'trending_up': trending_up_count,
                'trending_down': trending_down_count,
                'surging_up': surging_up_count,
                'surging_down': surging_down_count
            })
        
        return counts
    
    def _log_filtering_results(self, original_data: Dict, filtered_data: Dict, user_id: int):
        """Log filtering results for analysis."""
        try:
            original_counts = self._count_events(original_data, detailed=True)
            filtered_counts = self._count_events(filtered_data, detailed=True)
            
            events_filtered = sum(original_counts.values()) - sum(filtered_counts.values())
            
            if events_filtered > 0:
                logger.info(
                    f"WEBSOCKET-FILTER: USER_FILTER_RESULTS_{user_id}: Filtered {events_filtered} events - "
                    f"H:{original_counts['highs']}->{filtered_counts['highs']}, "
                    f"L:{original_counts['lows']}->{filtered_counts['lows']}, "
                    f"T:{original_counts['trending']}->{filtered_counts['trending']}, "
                    f"S:{original_counts['surging']}->{filtered_counts['surging']}"
                )
                
            self.filter_stats['total_events_filtered'] += events_filtered
            
        except Exception as e:
            logger.error(f"Error logging filtering results: {e}")

    '''
    def get_filter_statistics(self) -> Dict[str, Any]:
        """Get filtering statistics."""
        return {
            'universe_filtering_avg_ms': (
                self.filter_stats['universe_filtering_time_ms'] / 
                self.filter_stats['filter_operations']
            ) if self.filter_stats['filter_operations'] > 0 else 0,
            'user_filtering_avg_ms': (
                self.filter_stats['user_filtering_time_ms'] / 
                self.filter_stats['filter_operations']
            ) if self.filter_stats['filter_operations'] > 0 else 0,
            'total_events_filtered': self.filter_stats['total_events_filtered'],
            'filter_operations': self.filter_stats['filter_operations']
        }
    '''
    def _normalize_trend_direction(self, trend_direction):
        """
        Normalize Unicode arrow characters to ASCII for CSV compatibility.
        
        Args:
            trend_direction: Original trend direction character/string
            
        Returns:
            str: Normalized direction string
        """
        if trend_direction is None:
            return None
            
        if trend_direction == "→":
            return "->"
        elif trend_direction == "↑" or trend_direction == "up":
            return "up"
        elif trend_direction == "↓" or trend_direction == "down":
            return "down"
        return trend_direction
    
    def sanitize_for_json(self, data):
        return self._sanitize_for_json(data)
                    
    def _sanitize_for_json(self, data):
        """
        Clean data structure for JSON serialization.
        
        Args:
            data: Data structure to sanitize
            
        Returns:
            dict: JSON-serializable data structure
        """
        if isinstance(data, dict):
            return {k: self._sanitize_for_json(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._sanitize_for_json(item) for item in data]
        elif isinstance(data, datetime):
            return data.isoformat()
        elif isinstance(data, float):
            # Handle special float values
            if data != data or data == float('inf') or data == float('-inf'):
                return None
            return data
        else:
            return data