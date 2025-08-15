# utils/event_factory.py
"""
Event Factory for creating typed events.
Phase 4: Pure typed implementation - no dict conversions.
"""

import time
from typing import Optional
from config.logging_config import get_domain_logger, LogDomain

from src.core.domain.events import HighLowEvent, TrendEvent, SurgeEvent

logger = get_domain_logger(LogDomain.CORE, 'event_factory')


class EventFactory:
    """
    Factory class for creating typed events.
    Phase 4: Works exclusively with typed events, no dict compatibility.
    """
    
    '''
    @staticmethod
    def create_high_low_event(
        ticker: str,
        event_type: str,
        price: float,
        time: float,
        count: int,
        period_seconds: int = 0,
        previous_price: float = None,
        percent_change: float = 0.0,
        vwap: Optional[float] = None,
        volume: float = 0,
        **kwargs
    ) -> HighLowEvent:
        """
        Create a high/low event with S18/19/20 structure.
        Phase 4: Returns typed HighLowEvent, not dict.
        """
        # Determine direction based on event type
        direction = 'up' if event_type in ['high', 'session_high'] else 'down'
        
        # Calculate price change if previous price provided
        price_change = 0.0
        if previous_price and previous_price > 0:
            price_change = price - previous_price
        
        # Create typed event
        return HighLowEvent(
            # Required base fields
            ticker=ticker,
            type=event_type,
            price=price,
            time=time,
            
            # Common fields
            correlation_id=kwargs.get('correlation_id'),
            direction=direction,
            reversal=kwargs.get('reversal', False),
            count=count,
            count_up=kwargs.get('count_up', 0),
            count_down=kwargs.get('count_down', 0),
            percent_change=percent_change,
            vwap=vwap,
            vwap_divergence=kwargs.get('vwap_divergence', 0.0),
            volume=volume,
            rel_volume=kwargs.get('rel_volume', 0.0),
            label=kwargs.get('label', ''),
            
            # High/Low specific fields
            period_seconds=period_seconds,
            previous_price=previous_price or price,
            price_change=price_change,
            session_high=kwargs.get('session_high'),
            session_low=kwargs.get('session_low'),
            current_high=kwargs.get('current_high'),
            current_low=kwargs.get('current_low'),
            previous_high=kwargs.get('previous_high'),
            previous_low=kwargs.get('previous_low'),
            period=kwargs.get('period', 'session'),
            is_initial=kwargs.get('is_initial', False),
            last_update=kwargs.get('last_update', time)
        )
    @staticmethod
    def create_trend_event(ticker: str, price: float, direction: str,
                          trend_strength: str, trend_score: float,
                          **kwargs) -> TrendEvent:
        """
        Create a new TrendEvent with proper defaults.
        
        Args:
            ticker: Stock ticker
            price: Current price
            direction: Trend direction symbol
            trend_strength: Strength classification
            trend_score: Numerical trend score
            **kwargs: Additional fields
            
        Returns:
            TrendEvent instance
        """
        return TrendEvent(
            ticker=ticker,
            type='trend',
            price=price,
            time=kwargs.get('time', time.time()),
            direction=direction,
            trend_strength=trend_strength,
            trend_score=trend_score,
            **{k: v for k, v in kwargs.items() if k != 'time'}
        )

    @staticmethod
    def create_surge_event(ticker: str, price: float, direction: str,
                          surge_magnitude: float, surge_strength: str,
                          surge_trigger_type: str, **kwargs) -> SurgeEvent:
        """
        Create a new SurgeEvent with proper defaults.
        
        Args:
            ticker: Stock ticker
            price: Current price
            direction: Surge direction
            surge_magnitude: Percentage change magnitude
            surge_strength: Strength classification
            surge_trigger_type: What triggered the surge
            **kwargs: Additional fields
            
        Returns:
            SurgeEvent instance
        """
        return SurgeEvent(
            ticker=ticker,
            type='surge',
            price=price,
            time=kwargs.get('time', time.time()),
            direction=direction,
            surge_magnitude=surge_magnitude,
            surge_strength=surge_strength,
            surge_trigger_type=surge_trigger_type,
            **{k: v for k, v in kwargs.items() if k != 'time'}
        )
    '''
