# classes/events/surge.py
import time
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, Any, Optional
from src.core.domain.events.base import BaseEvent

@dataclass
class SurgeEvent(BaseEvent):
    """
    Surge event with S18/19/20 standardized structure.
    """
    # Surge-specific fields
    surge_magnitude: float = 0.0  # Percentage change that triggered surge
    surge_score: float = 0.0
    surge_strength: str = 'weak'  # 'weak', 'moderate', 'strong'
    surge_trigger_type: str = 'unknown'  # 'price', 'volume', 'price_and_volume'
    surge_volume_multiplier: float = 1.0
    surge_calculation: Optional[Dict[str, Any]] = None
    surge_description: str = ''
    surge_expiration: float = 0.0
    surge_daily_count: int = 0
    surge_age: float = 0.0
    
    def __post_init__(self):
        """Set type and validate"""
        self.type = 'surge'
        # Initialize calc if not provided
        if self.surge_calculation is None:
            self.surge_calculation = {}
        super().__post_init__()
        
    def validate(self) -> bool:
        """Validate surge event data"""
        super().validate()
        
        # Validate surge strength
        valid_strengths = ['weak', 'moderate', 'strong']
        if self.surge_strength not in valid_strengths:
            raise ValueError(f"Invalid surge strength: {self.surge_strength}")
            
        # Validate trigger type
        valid_triggers = ['price', 'volume', 'price_and_volume', 'unknown', 'price_driven', 'volume_driven']
        if self.surge_trigger_type not in valid_triggers:
            raise ValueError(f"Invalid surge trigger type: {self.surge_trigger_type}")
            
        return True
        
    def get_event_specific_data(self) -> Dict[str, Any]:
        """Get surge-specific data for S18/19/20 structure"""
        return {
            'surge_magnitude': self.surge_magnitude,
            'surge_score': self.surge_score,
            'surge_strength': self.surge_strength,
            'surge_trigger_type': self.surge_trigger_type,
            'surge_volume_multiplier': self.surge_volume_multiplier,
            'surge_calculation': self.surge_calculation,
            'surge_description': self.surge_description,
            'surge_expiration': self.surge_expiration,
            'surge_daily_count': self.surge_daily_count,
            'surge_age': self.surge_age
        }
    
    def to_transport_dict(self) -> dict:
        """
        Convert to transport format for WebSocket emission.
        Override base to properly map surge-specific fields.
        """
        # Get base transport dict
        base_dict = super().to_transport_dict()
        
        # Add/override surge-specific mappings
        base_dict.update({
            'magnitude': self.surge_magnitude,  # Map surge_magnitude to magnitude
            'score': self.surge_score,
            'strength': self.surge_strength,
            'trigger_type': self.surge_trigger_type,
            'description': self.surge_description,
            'volume_multiplier': self.surge_volume_multiplier,
            'event_key': f"{self.ticker}_{self.direction}_{self.time}",
            'surge_age': time.time() - self.time,  # Calculate age dynamically
            'expiration': self.surge_expiration,
            'daily_surge_count': self.surge_daily_count,
            'last_surge_timestamp': self.time,
            'time': datetime.fromtimestamp(self.time).strftime('%H:%M:%S'),
            'event_id': self.event_id
        })
        
        return base_dict

    '''
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SurgeEvent':
        """
        Create SurgeEvent from external dict data.
        
        PHASE 4: Only use at external boundaries (API responses, file I/O, WebSocket messages)
        DO NOT use for internal component communication - pass typed objects directly.
        
        Args:
            data: Dictionary containing event data from external source
            
        Returns:
            SurgeEvent: Typed event instance
        """
        # Extract event_specific_data if present (for backward compatibility with external sources)
        event_specific = data.get('event_specific_data', {})
        
        # Check both locations for backward compatibility with external data formats
        surge_strength = event_specific.get('surge_strength') or data.get('strength', 'weak')
        surge_trigger_type = event_specific.get('surge_trigger_type') or data.get('trigger_type', 'unknown')
        
        return cls(
            # Base fields
            ticker=data['ticker'],
            type=data.get('type', 'surge'),
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
            # Surge specific fields - properly handle external data formats
            surge_magnitude=event_specific.get('surge_magnitude', 0.0),
            surge_score=event_specific.get('surge_score', 0.0),
            surge_strength=surge_strength,
            surge_trigger_type=surge_trigger_type,
            surge_volume_multiplier=event_specific.get('surge_volume_multiplier', 1.0),
            surge_calculation=event_specific.get('surge_calculation', {}),
            surge_description=event_specific.get('surge_description', ''),
            surge_expiration=event_specific.get('surge_expiration', 0.0),
            surge_daily_count=event_specific.get('surge_daily_count', 0),
            surge_age=event_specific.get('surge_age', 0.0)
        )
    '''