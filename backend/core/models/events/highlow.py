# classes/events/highlow.py
import time
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, Any, Optional
from .base import BaseEvent

@dataclass
class HighLowEvent(BaseEvent):
    """
    High/Low event with S18/19/20 standardized structure.
    """
    # High/Low specific fields
    current_high: Optional[float] = None
    current_low: Optional[float] = None
    previous_high: Optional[float] = None
    previous_low: Optional[float] = None
    session_high: Optional[float] = None
    session_low: Optional[float] = None
    period: str = 'session'  # 'session', '52week', 'alltime'
    is_initial: bool = False
    last_update: Optional[float] = None
    
    trend_flag: Optional[str] = None  # 'up', 'down', or None
    surge_flag: Optional[str] = None  # 'up', 'down', or None

    # NEW: Enhanced fields from refactoring
    significance_score: float = 0.0  # 0-100 score of event significance
    reversal_info: Optional[Dict[str, Any]] = None  # Reversal pattern details
    thresholds_used: Optional[Dict[str, Any]] = None  # Detection thresholds applied


    def __post_init__(self):
        """Set type based on direction and validate"""
        # Normalize event types to 'high' or 'low'
        if self.type in ['session_high', 'high']:
            self.type = 'high'
        elif self.type in ['session_low', 'low']:
            self.type = 'low'
        elif self.type not in ['high', 'low']:
            # Auto-detect type from direction
            if self.direction in ['up', '↑']:
                self.type = 'high'
            else:
                self.type = 'low'
        
        super().__post_init__()
        
    def validate(self) -> bool:
        """Validate high/low event data"""
        super().validate()
        
        # Validate period
        valid_periods = ['session', '52week', 'alltime', 'day']
        if self.period not in valid_periods:
            raise ValueError(f"Invalid period: {self.period}")
            
        return True
        
    def get_event_specific_data(self) -> Dict[str, Any]:
        """Get high/low specific data for S18/19/20 structure"""
        return {
            'highlow_current_high': self.current_high,
            'highlow_current_low': self.current_low,
            'highlow_previous_high': self.previous_high,
            'highlow_previous_low': self.previous_low,
            'highlow_session_high': self.session_high,
            'highlow_session_low': self.session_low,
            'highlow_period': self.period,
            'highlow_is_initial': self.is_initial,
            'highlow_last_update': self.last_update,
            'highlow_vwap_distance': self.vwap_divergence,
            'highlow_trend_flag': self.trend_flag,  
            'highlow_surge_flag': self.surge_flag,
            # NEW: Add enhanced fields
            'highlow_significance_score': self.significance_score,
            'highlow_reversal_info': self.reversal_info,
            'highlow_thresholds_used': self.thresholds_used,              
            'highlow_calc_transparency': {
                'session_open_price': None,  # Will be populated by detector
                'base_price_source': None,
                'price_change_amount': self.price - (self.previous_high or self.previous_low or self.price),
                'percent_change_formula': f"percent_change = {self.percent_change:.2f}%",
                'threshold_type': 'price_comparison',
                'threshold_value': self.previous_high if self.type == 'high' else self.previous_low,
                'detection_logic': f"{self.price} > {self.previous_high}" if self.type == 'high' else f"{self.price} < {self.previous_low}",
                'session_start': None,
                'session_end': None,
                'events_in_session': self.count,
                'vwap_at_detection': self.vwap,
                'significance_score': self.significance_score,  # Include here too
                'vwap_distance_formula': f"(({self.price} - {self.vwap}) / {self.vwap}) * 100" if self.vwap else None
            }
        }
    
    def to_transport_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary format for WebSocket transport.
        Ensures all fields including event_id are preserved.
        """
        # Get base transport dict (includes event_id)
        base_dict = super().to_transport_dict()
        # Add high/low specific fields directly to the dict (not nested)
        base_dict.update({
            'current_high': self.current_high,
            'current_low': self.current_low,
            'previous_high': self.previous_high,
            'previous_low': self.previous_low,
            'session_high': self.session_high,
            'session_low': self.session_low,
            'period': self.period,
            'is_initial': self.is_initial,
            'last_update': self.last_update,
            'trend_flag': self.trend_flag,
            'surge_flag': self.surge_flag,
            # NEW: Add enhanced fields to transport
            'significance_score': self.significance_score,
            'reversal_info': self.reversal_info,
            'time': datetime.fromtimestamp(self.time).strftime('%H:%M:%S'),
            # Ensure event_id is explicitly included
            'event_id': self.event_id
        })
        
        return base_dict

    '''
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HighLowEvent':
        """
        Create HighLowEvent from external dict data.
        
        PHASE 4: Only use at external boundaries (API responses, file I/O, WebSocket messages)
        DO NOT use for internal component communication - pass typed objects directly.
        
        Args:
            data: Dictionary containing event data from external source
            
        Returns:
            HighLowEvent: Typed event instance
        """
        # Extract event_specific_data if present (for backward compatibility with external sources)
        event_specific = data.get('event_specific_data', {})
        
        # Extract type - normalize at creation
        event_type = data.get('type') or data.get('label', '')
        
        # Normalize the type immediately
        if 'high' in str(event_type).lower():
            event_type = 'high'
        elif 'low' in str(event_type).lower():
            event_type = 'low'
        else:
            # Default based on direction
            direction = data.get('direction', 'up')
            event_type = 'high' if direction in ['up', '↑'] else 'low'
        
        return cls(
            # Base fields with defaults for missing values
            ticker=data.get('ticker', ''),
            type=event_type,
            price=data.get('price', 0.0),
            time=data.get('time', time.time()),
            direction=data.get('direction', '→'),
            reversal=data.get('reversal', False),
            count=data.get('count', 0),
            count_up=data.get('count_up', 0),
            count_down=data.get('count_down', 0),
            percent_change=data.get('percent_change', 0.0),
            vwap=data.get('vwap'),
            vwap_divergence=data.get('vwap_divergence', 0.0),
            volume=data.get('volume', 0),
            rel_volume=data.get('rel_volume', 0.0),
            label=data.get('label', ''),
            # High/Low specific fields - check both locations for external compatibility
            current_high=event_specific.get('highlow_current_high') or data.get('current_high'),
            current_low=event_specific.get('highlow_current_low') or data.get('current_low'),
            previous_high=event_specific.get('highlow_previous_high') or data.get('previous_high'),
            previous_low=event_specific.get('highlow_previous_low') or data.get('previous_low'),
            session_high=event_specific.get('highlow_session_high') or data.get('session_high'),
            session_low=event_specific.get('highlow_session_low') or data.get('session_low'),
            period=event_specific.get('highlow_period', data.get('period', 'session')),
            is_initial=event_specific.get('highlow_is_initial', data.get('is_initial', False)),
            last_update=event_specific.get('highlow_last_update') or data.get('last_update'),
            trend_flag=event_specific.get('highlow_trend_flag') or data.get('trend_flag'),
            surge_flag=event_specific.get('highlow_surge_flag') or data.get('surge_flag'),
             # NEW: Handle enhanced fields
            significance_score=event_specific.get('highlow_significance_score', data.get('significance_score', 0.0)),
            reversal_info=event_specific.get('highlow_reversal_info') or data.get('reversal_info'),
            thresholds_used=event_specific.get('highlow_thresholds_used') or data.get('thresholds_used')
        )
    '''