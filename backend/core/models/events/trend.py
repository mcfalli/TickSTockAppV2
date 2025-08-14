# classes/events/trend.py
import time
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, Any, Optional
from .base import BaseEvent

@dataclass
class TrendEvent(BaseEvent):
    """
    Trend event with S18/19/20 standardized structure.
    Fixes the trend_strength field location issue.
    """
    # Trend-specific fields (THESE ARE NOW AT ROOT LEVEL)
    trend_strength: str = 'neutral'  # 'weak', 'moderate', 'strong', 'neutral'
    trend_score: float = 0.0
    trend_short_score: float = 0.0
    trend_medium_score: float = 0.0
    trend_long_score: float = 0.0
    trend_vwap_position: str = 'unknown'  # 'above', 'below', 'unknown'
    trend_age: float = 0.0  # Age in seconds
    trend_calc_transparency: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Set type and validate"""
        self.type = 'trend'
        # Initialize calc transparency if not provided
        if self.trend_calc_transparency is None:
            self.trend_calc_transparency = {}
        super().__post_init__()
        
    def validate(self) -> bool:
        """Validate trend event data"""
        super().validate()
        
        # Validate trend strength
        valid_strengths = ['weak', 'moderate', 'strong', 'neutral']
        if self.trend_strength not in valid_strengths:
            raise ValueError(f"Invalid trend strength: {self.trend_strength}")
            
        # Validate VWAP position
        valid_positions = ['above', 'below', 'unknown']
        if self.trend_vwap_position not in valid_positions:
            raise ValueError(f"Invalid VWAP position: {self.trend_vwap_position}")
            
        # Validate score ranges
        if not -100 <= self.trend_score <= 100:
            raise ValueError(f"Trend score out of range: {self.trend_score}")
            
        return True
        
    def get_event_specific_data(self) -> Dict[str, Any]:
        """Get trend-specific data for S18/19/20 structure"""
        return {
            'trend_strength': self.trend_strength,
            'trend_score': self.trend_score,
            'trend_calc_transparency': self.trend_calc_transparency,
            'trend_short_score': self.trend_short_score,
            'trend_medium_score': self.trend_medium_score,
            'trend_long_score': self.trend_long_score,
            'trend_vwap_position': self.trend_vwap_position,
            'trend_age': self.trend_age
        }
    
    def to_transport_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary format for WebSocket transport.
        Ensures all fields including event_id are preserved.
        """
        # Get base transport dict (includes event_id)
        base_dict = super().to_transport_dict()
        
        # Add trend-specific fields directly to the dict
        base_dict.update({
            'trend_strength': self.trend_strength,
            'trend_score': self.trend_score,
            'trend_short_score': self.trend_short_score,
            'trend_medium_score': self.trend_medium_score,
            'trend_long_score': self.trend_long_score,
            'trend_vwap_position': self.trend_vwap_position,
            'trend_age': self.trend_age,
            'last_trend_update': self.time, 
            'time': datetime.fromtimestamp(self.time).strftime('%H:%M:%S'),
            'event_id': self.event_id
        })
        
        return base_dict

    '''
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TrendEvent':
        """
        Create TrendEvent from external dict data.
        
        PHASE 4: Only use at external boundaries (API responses, file I/O, WebSocket messages)
        DO NOT use for internal component communication - pass typed objects directly.
        
        CRITICAL FIX: This method handles the trend_strength field location issue where
        external sources may provide the field at root level OR in event_specific_data.
        
        Args:
            data: Dictionary containing event data from external source
            
        Returns:
            TrendEvent: Typed event instance
        """
        # Extract event_specific_data if present (for backward compatibility with external sources)
        event_specific = data.get('event_specific_data', {})
        
        # CRITICAL FIX: Check both locations for backward compatibility with external data
        trend_strength = event_specific.get('trend_strength') or data.get('trend_strength', 'neutral')
        trend_score = event_specific.get('trend_score') or data.get('trend_score', 0.0)
        
        return cls(
            # Base fields
            ticker=data['ticker'],
            type=data.get('type', 'trend'),
            price=data['price'],
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
            # Trend specific fields - properly handle both field locations
            trend_strength=trend_strength,
            trend_score=trend_score,
            trend_short_score=event_specific.get('trend_short_score', 0.0),
            trend_medium_score=event_specific.get('trend_medium_score', 0.0),
            trend_long_score=event_specific.get('trend_long_score', 0.0),
            trend_vwap_position=event_specific.get('trend_vwap_position', 'unknown'),
            trend_age=event_specific.get('trend_age', 0.0),
            trend_calc_transparency=event_specific.get('trend_calc_transparency', {})
        )
    '''
    def __str__(self) -> str:
        """Enhanced string representation"""
        return f"TREND {self.ticker} @ ${self.price:.2f} ({self.direction}) strength={self.trend_strength}"