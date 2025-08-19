"""
Per-Minute Aggregate Event Model - Sprint 101
Handles Polygon AM (per-minute aggregate) events with OHLCV data.
"""

import time
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from src.core.domain.events.base import BaseEvent


@dataclass
class PerMinuteAggregateEvent(BaseEvent):
    """
    Per-minute aggregate event containing OHLCV data for a 1-minute window.
    Maps to Polygon's AM (per-minute aggregate) event structure.
    
    Based on Polygon AM event schema:
    - ev: "AM"
    - sym: ticker symbol
    - v: volume for this minute
    - av: accumulated volume for the day
    - op: official opening price for the day
    - vw: volume weighted average price for this minute
    - o: opening price for this minute
    - c: closing price for this minute
    - h: highest price for this minute
    - l: lowest price for this minute
    - a: volume weighted average price for the day
    - z: average trade size for this minute
    - s: start timestamp (Unix milliseconds)
    - e: end timestamp (Unix milliseconds)
    - otc: whether ticker is OTC (omitted if false)
    """
    
    # Per-minute aggregate specific fields
    minute_open: Optional[float] = None          # 'o' - Opening price for this minute
    minute_high: Optional[float] = None          # 'h' - Highest price for this minute
    minute_low: Optional[float] = None           # 'l' - Lowest price for this minute
    minute_close: Optional[float] = None         # 'c' - Closing price for this minute (same as price)
    minute_volume: Optional[int] = None          # 'v' - Volume for this minute
    minute_vwap: Optional[float] = None          # 'vw' - VWAP for this minute
    
    # Daily context fields
    daily_open: Optional[float] = None           # 'op' - Official opening price for the day
    accumulated_volume: Optional[int] = None     # 'av' - Total accumulated volume for the day
    daily_vwap: Optional[float] = None          # 'a' - Daily VWAP
    
    # Additional metrics
    average_trade_size: Optional[int] = None     # 'z' - Average trade size for this minute
    start_timestamp: Optional[float] = None      # 's' - Start timestamp (Unix milliseconds -> seconds)
    end_timestamp: Optional[float] = None        # 'e' - End timestamp (Unix milliseconds -> seconds)
    is_otc: bool = False                        # 'otc' - Whether ticker is OTC
    
    # Calculated fields
    minute_range: Optional[float] = None         # High - Low for this minute
    minute_price_change: Optional[float] = None  # Close - Open for this minute
    minute_price_change_pct: Optional[float] = None  # (Close - Open) / Open * 100
    vwap_deviation: Optional[float] = None       # Price deviation from minute VWAP
    
    # Market session context
    market_session: str = 'REGULAR'             # REGULAR, PRE, POST
    
    def __post_init__(self):
        """Set type and calculate derived fields"""
        if not self.type:
            self.type = 'aggregate_minute'
        
        # Calculate derived fields
        self._calculate_derived_fields()
        
        super().__post_init__()
    
    def _calculate_derived_fields(self):
        """Calculate derived metrics from aggregate data"""
        try:
            # Calculate minute range
            if self.minute_high is not None and self.minute_low is not None:
                self.minute_range = self.minute_high - self.minute_low
            
            # Calculate minute price change
            if self.minute_open is not None and self.minute_close is not None:
                self.minute_price_change = self.minute_close - self.minute_open
                
                # Calculate percentage change
                if self.minute_open > 0:
                    self.minute_price_change_pct = (self.minute_price_change / self.minute_open) * 100
            
            # Calculate VWAP deviation
            if self.minute_vwap is not None and self.price > 0:
                self.vwap_deviation = ((self.price - self.minute_vwap) / self.minute_vwap) * 100
                
        except Exception as e:
            # Don't fail initialization on calculation errors
            pass
    
    def validate(self) -> bool:
        """Validate per-minute aggregate event data"""
        # Call parent validation first
        super().validate()
        
        # Validate aggregate-specific fields
        if self.minute_volume is not None and self.minute_volume < 0:
            raise ValueError(f"Invalid minute volume: {self.minute_volume}")
        
        if self.accumulated_volume is not None and self.accumulated_volume < 0:
            raise ValueError(f"Invalid accumulated volume: {self.accumulated_volume}")
        
        # Validate OHLC relationships
        if all(x is not None for x in [self.minute_open, self.minute_high, self.minute_low, self.minute_close]):
            if self.minute_high < max(self.minute_open, self.minute_close):
                raise ValueError(f"High {self.minute_high} must be >= max(open {self.minute_open}, close {self.minute_close})")
            
            if self.minute_low > min(self.minute_open, self.minute_close):
                raise ValueError(f"Low {self.minute_low} must be <= min(open {self.minute_open}, close {self.minute_close})")
        
        # Validate timestamps
        if self.start_timestamp is not None and self.end_timestamp is not None:
            if self.start_timestamp >= self.end_timestamp:
                raise ValueError(f"Start timestamp {self.start_timestamp} must be < end timestamp {self.end_timestamp}")
        
        return True
    
    def get_event_specific_data(self) -> Dict[str, Any]:
        """Get per-minute aggregate specific data for transport"""
        return {
            'minute_open': self.minute_open,
            'minute_high': self.minute_high,
            'minute_low': self.minute_low,
            'minute_close': self.minute_close,
            'minute_volume': self.minute_volume,
            'minute_vwap': self.minute_vwap,
            'daily_open': self.daily_open,
            'accumulated_volume': self.accumulated_volume,
            'daily_vwap': self.daily_vwap,
            'average_trade_size': self.average_trade_size,
            'start_timestamp': self.start_timestamp,
            'end_timestamp': self.end_timestamp,
            'is_otc': self.is_otc,
            'minute_range': self.minute_range,
            'minute_price_change': self.minute_price_change,
            'minute_price_change_pct': self.minute_price_change_pct,
            'vwap_deviation': self.vwap_deviation,
            'market_session': self.market_session
        }
    
    @classmethod
    def from_polygon_am_event(cls, polygon_data: Dict[str, Any]) -> 'PerMinuteAggregateEvent':
        """
        Create PerMinuteAggregateEvent from Polygon AM event data.
        
        Args:
            polygon_data: Raw Polygon AM event dict
            
        Returns:
            PerMinuteAggregateEvent instance
            
        Raises:
            ValueError: If required fields are missing
            KeyError: If essential polygon fields are missing
        """
        try:
            # Required fields
            ticker = polygon_data['sym']
            minute_close = polygon_data['c']
            
            # Convert timestamps from milliseconds to seconds
            start_timestamp = polygon_data.get('s')
            end_timestamp = polygon_data.get('e')
            start_timestamp_sec = start_timestamp / 1000.0 if start_timestamp else None
            end_timestamp_sec = end_timestamp / 1000.0 if end_timestamp else None
            
            # Determine market session based on timestamp
            market_session = 'REGULAR'  # Default - could be enhanced with session detection
            
            return cls(
                ticker=ticker,
                type='aggregate_minute',
                price=minute_close,
                time=end_timestamp_sec or time.time(),
                
                # OHLC data
                minute_open=polygon_data.get('o'),
                minute_high=polygon_data.get('h'),
                minute_low=polygon_data.get('l'),
                minute_close=minute_close,
                
                # Volume data  
                minute_volume=polygon_data.get('v'),
                accumulated_volume=polygon_data.get('av'),
                volume=polygon_data.get('v', 0),  # Set base volume field
                
                # VWAP data
                minute_vwap=polygon_data.get('vw'),
                daily_vwap=polygon_data.get('a'),
                vwap=polygon_data.get('vw'),  # Set base vwap field
                
                # Additional fields
                daily_open=polygon_data.get('op'),
                average_trade_size=polygon_data.get('z'),
                start_timestamp=start_timestamp_sec,
                end_timestamp=end_timestamp_sec,
                is_otc=polygon_data.get('otc', False),
                market_session=market_session
            )
            
        except KeyError as e:
            raise ValueError(f"Missing required field in Polygon AM event: {e}")
        except Exception as e:
            raise ValueError(f"Error creating PerMinuteAggregateEvent from Polygon data: {e}")
    
    def get_ohlcv_summary(self) -> Dict[str, Any]:
        """Get OHLCV summary for this minute"""
        return {
            'open': self.minute_open,
            'high': self.minute_high,
            'low': self.minute_low,
            'close': self.minute_close,
            'volume': self.minute_volume,
            'vwap': self.minute_vwap,
            'range': self.minute_range,
            'price_change': self.minute_price_change,
            'price_change_pct': self.minute_price_change_pct
        }
    
    def __str__(self) -> str:
        """Enhanced string representation for logging"""
        ohlc = f"O:{self.minute_open:.2f} H:{self.minute_high:.2f} L:{self.minute_low:.2f} C:{self.minute_close:.2f}" if all(
            x is not None for x in [self.minute_open, self.minute_high, self.minute_low, self.minute_close]
        ) else f"@{self.price:.2f}"
        
        vol = f" Vol:{self.minute_volume:,}" if self.minute_volume else ""
        
        return f"MINUTE-AGG {self.ticker} {ohlc}{vol}"