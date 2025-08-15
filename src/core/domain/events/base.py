# classes/events/base.py
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
import time
import uuid
from datetime import datetime

@dataclass
class BaseEvent(ABC):
    """
    Abstract base class for all market events.
    Implements S18/19/20 standardized structure.
    """
    # Required fields
    ticker: str
    type: str
    price: float
    time: float = field(default_factory=time.time)
    event_id: str = field(default_factory=lambda: f"{time.time():.6f}_{uuid.uuid4().hex[:8]}")
    
    # Common fields with defaults
    direction: str = '→'  # 'up', 'down', '↑', '↓', '→'
    reversal: bool = False
    count: int = 0
    count_up: int = 0
    count_down: int = 0
    percent_change: float = 0.0
    vwap: Optional[float] = None
    vwap_divergence: float = 0.0
    volume: float = 0
    rel_volume: float = 0.0
    label: str = ''
    
    def __post_init__(self):
        """Validate on instantiation"""
        self.validate()
        
    @abstractmethod
    def validate(self) -> bool:
        """Validate event data integrity"""
        if self.price <= 0:
            raise ValueError(f"Invalid price: {self.price}")
        if not self.ticker:
            raise ValueError("Empty ticker")
        if not self.type:
            raise ValueError("Empty event type")
        return True
        
    @abstractmethod
    def get_event_specific_data(self) -> Dict[str, Any]:
        """Get event-specific data for S18/19/20 structure"""
        pass
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for transport (backward compatible)"""
        return {
            'ticker': self.ticker,
            'type': self.type,
            'price': self.price,
            'time': self.time,
            'event_id': self.event_id, 
            'direction': self.direction,
            'reversal': self.reversal,
            'count': self.count,
            'count_up': self.count_up,
            'count_down': self.count_down,
            'percent_change': self.percent_change,
            'vwap': self.vwap,
            'vwap_divergence': self.vwap_divergence,
            'volume': self.volume,
            'rel_volume': self.rel_volume,
            'label': self.label,
            'event_specific_data': self.get_event_specific_data()
        }
        
    def to_transport_dict(self) -> Dict[str, Any]:
        """Alias for to_dict() - S18/19/20 compliant transport structure"""
        return self.to_dict()
    '''
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseEvent':
        """Create event from dictionary - must be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement from_dict()")
    '''
        
    def __str__(self) -> str:
        """String representation for logging"""
        return f"{self.type.upper()} {self.ticker} @ ${self.price:.2f} ({self.direction})"
