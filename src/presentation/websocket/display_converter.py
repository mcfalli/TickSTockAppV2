"""
WebSocket Display Conversion Module
Sprint 32: Centralizes display data formatting and field configuration
"""
from typing import Dict, Any, Set
from config.logging_config import get_domain_logger, LogDomain

logger = get_domain_logger(LogDomain.CORE, 'websocket_display')

# Display field configuration
DISPLAY_FIELDS = {
    'common': {
        'ticker', 'type', 'price', 'time', 'event_id', 'direction', 
        'reversal', 'count', 'count_up', 'count_down', 'percent_change',
        'vwap', 'vwap_divergence', 'volume', 'rel_volume', 'label'
    },
    'highlow': {
        'session_high', 'session_low', 'last_update', 'trend_flag', 'surge_flag',
        'significance_score', 'reversal_info' 
    },
    'trend': {
        'trend_strength', 'trend_score', 'trend_short_score', 
        'trend_medium_score', 'trend_long_score', 'trend_vwap_position',
        'trend_age', 'last_trend_update'
    },
    'surge': {
        'magnitude', 'score', 'strength', 'trigger_type', 'description',
        'volume_multiplier', 'event_key', 'surge_age', 'expiration',
        'daily_surge_count', 'last_surge_timestamp'
    }
}


class WebSocketDisplayConverter:
    """
    Handles conversion of internal event data to display format.
    Sprint 32: Centralizes display formatting logic.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get('CONVERT_TO_DISPLAY_FORMAT', True)
        
        # Allow field overrides from config
        self.display_fields = config.get('DISPLAY_EVENT_FIELDS', DISPLAY_FIELDS)
        
    def convert_event_to_display_format(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert full event data to display format by keeping only UI-relevant fields.
        
        Args:
            event: Full event dictionary
            
        Returns:
            dict: Display-ready event data
        """
        if not self.enabled:
            return event
        
        # Build display event
        display_event = {}
        
        # Get event type
        event_type = event.get('type', '').lower()
        
        # Copy common fields
        for field in self.display_fields.get('common', set()):
            if field in event:
                display_event[field] = event[field]
        
        # Add type-specific fields
        if event_type in ['high', 'low'] and 'highlow' in self.display_fields:
            for field in self.display_fields['highlow']:
                if field in event:
                    display_event[field] = event[field]
        
        elif event_type == 'trend' and 'trend' in self.display_fields:
            for field in self.display_fields['trend']:
                if field in event:
                    display_event[field] = event[field]
        
        elif event_type == 'surge' and 'surge' in self.display_fields:
            for field in self.display_fields['surge']:
                if field in event:
                    display_event[field] = event[field]
        
        return display_event
    
    def convert_to_display_data(self, events_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert full events collection to display format.
        
        Args:
            events_data: Full events data structure
            
        Returns:
            dict: Display-ready data structure
        """
        if not self.enabled:
            return events_data
            
        display_data = {}
        
        # Process highs and lows (simple lists)
        for event_type in ['highs', 'lows']:
            if event_type in events_data:
                display_data[event_type] = [
                    self.convert_event_to_display_format(event) 
                    for event in events_data[event_type]
                ]
        
        # Process trending and surging (nested by direction)
        for event_type in ['trending', 'surging']:
            if event_type in events_data and isinstance(events_data[event_type], dict):
                display_data[event_type] = {}
                for direction in ['up', 'down']:
                    if direction in events_data[event_type]:
                        display_data[event_type][direction] = [
                            self.convert_event_to_display_format(event)
                            for event in events_data[event_type][direction]
                        ]
        
        # Copy all non-event fields (analytics, universe_context, etc.)
        for key, value in events_data.items():
            if key not in ['highs', 'lows', 'trending', 'surging']:
                display_data[key] = value
        
    
        return display_data
    
    '''
    def get_field_configuration(self) -> Dict[str, Set[str]]:
        """Get current field configuration for documentation/debugging."""
        return self.display_fields
    '''