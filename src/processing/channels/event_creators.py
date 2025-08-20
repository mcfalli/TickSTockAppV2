"""
Event Creation Logic for Sprint 106: Data Type Handlers

Provides centralized event creation methods for all channel types with consistent
formatting, transport compatibility, and source identification metadata.

Ensures all events are compatible with existing WebSocket publisher and maintain
proper event ID generation and deduplication logic.
"""

from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
import time
import uuid

from config.logging_config import get_domain_logger, LogDomain

# Import event types
from src.core.domain.events.base import BaseEvent
from src.core.domain.events.highlow import HighLowEvent
from src.core.domain.events.trend import TrendEvent
from src.core.domain.events.surge import SurgeEvent
from src.core.domain.events.aggregate import PerMinuteAggregateEvent
from src.core.domain.events.fmv import FairMarketValueEvent

# Import data types
from src.shared.models.data_types import TickData, OHLCVData, FMVData

logger = get_domain_logger(LogDomain.CORE, 'event_creators')


class BaseEventCreator(ABC):
    """
    Abstract base class for event creators.
    
    Provides common functionality for event creation including:
    - Source identification metadata
    - Event ID generation and deduplication
    - Transport compatibility validation
    """
    
    def __init__(self, channel_name: str, channel_id: str):
        self.channel_name = channel_name
        self.channel_id = channel_id
        self._created_event_ids: set = set()  # Track created events for deduplication
    
    def generate_unique_event_id(self, ticker: str, event_type: str) -> str:
        """Generate unique event ID with deduplication"""
        base_id = f"{time.time():.6f}_{ticker}_{event_type}_{uuid.uuid4().hex[:8]}"
        
        # Ensure uniqueness
        counter = 0
        event_id = base_id
        while event_id in self._created_event_ids:
            counter += 1
            event_id = f"{base_id}_{counter}"
        
        self._created_event_ids.add(event_id)
        
        # Clean up old IDs periodically (keep last 1000)
        if len(self._created_event_ids) > 1000:
            old_ids = list(self._created_event_ids)
            self._created_event_ids = set(old_ids[-500:])  # Keep newest 500
        
        return event_id
    
    @abstractmethod
    def create_events(self, data: Any, **kwargs) -> List[BaseEvent]:
        """Create events from data - implemented by subclasses"""
        pass


class TickEventCreator(BaseEventCreator):
    """
    Event creator for real-time tick data processing.
    
    Creates high/low, trend, and surge events from individual tick data points
    with real-time detection logic and immediate event generation.
    """
    
    def __init__(self, channel_name: str, channel_id: str):
        super().__init__(channel_name, channel_id)
        self.high_low_threshold = 0.05  # 5% threshold for high/low detection
        self.surge_multiplier = 3.0     # 3x volume surge threshold
    
    def create_events(self, data: TickData, **kwargs) -> List[BaseEvent]:
        """Create events from tick data"""
        events = []
        
        # Extract additional context from kwargs
        historical_high = kwargs.get('historical_high', 0.0)
        historical_low = kwargs.get('historical_low', float('inf'))
        avg_volume = kwargs.get('avg_volume', 0.0)
        previous_prices = kwargs.get('previous_prices', [])
        
        try:
            # High/Low Event Detection
            high_low_event = self._detect_high_low_event(
                data, historical_high, historical_low
            )
            if high_low_event:
                events.append(high_low_event)
            
            # Volume Surge Event Detection
            if avg_volume > 0:
                surge_event = self._detect_surge_event(data, avg_volume)
                if surge_event:
                    events.append(surge_event)
            
            # Trend Event Detection
            if len(previous_prices) >= 3:
                trend_event = self._detect_trend_event(data, previous_prices)
                if trend_event:
                    events.append(trend_event)
            
        except Exception as e:
            logger.error(f"Error creating tick events for {data.ticker}: {e}")
        
        return events
    
    def _detect_high_low_event(
        self, 
        data: TickData, 
        historical_high: float, 
        historical_low: float
    ) -> Optional[HighLowEvent]:
        """Detect high/low events from tick data"""
        
        if historical_high == 0.0 or historical_low == float('inf'):
            return None
        
        # Check for new high
        if data.price > historical_high * (1 + self.high_low_threshold):
            return HighLowEvent(
                event_id=self.generate_unique_event_id(data.ticker, "high"),
                ticker=data.ticker,
                price=data.price,
                volume=data.volume,
                timestamp=data.timestamp,
                event_type="high",
                previous_high=historical_high,
                percent_change=((data.price - historical_high) / historical_high) * 100,
                source=f"tick_channel_{self.channel_id}"
            )
        
        # Check for new low
        elif data.price < historical_low * (1 - self.high_low_threshold):
            return HighLowEvent(
                event_id=self.generate_unique_event_id(data.ticker, "low"),
                ticker=data.ticker,
                price=data.price,
                volume=data.volume,
                timestamp=data.timestamp,
                event_type="low",
                previous_low=historical_low,
                percent_change=((historical_low - data.price) / historical_low) * 100,
                source=f"tick_channel_{self.channel_id}"
            )
        
        return None
    
    def _detect_surge_event(self, data: TickData, avg_volume: float) -> Optional[SurgeEvent]:
        """Detect volume surge events from tick data"""
        
        if data.volume > avg_volume * self.surge_multiplier:
            return SurgeEvent(
                event_id=self.generate_unique_event_id(data.ticker, "surge"),
                ticker=data.ticker,
                price=data.price,
                volume=data.volume,
                timestamp=data.timestamp,
                avg_volume=avg_volume,
                surge_multiplier=data.volume / avg_volume,
                source=f"tick_channel_{self.channel_id}"
            )
        
        return None
    
    def _detect_trend_event(
        self, 
        data: TickData, 
        previous_prices: List[float]
    ) -> Optional[TrendEvent]:
        """Detect trend events from price history"""
        
        if len(previous_prices) < 3:
            return None
        
        # Simple trend detection: check last 3 prices
        recent_prices = previous_prices[-3:] + [data.price]
        
        # Check for consistent uptrend
        if all(recent_prices[i] > recent_prices[i-1] for i in range(1, len(recent_prices))):
            return TrendEvent(
                event_id=self.generate_unique_event_id(data.ticker, "uptrend"),
                ticker=data.ticker,
                price=data.price,
                volume=data.volume,
                timestamp=data.timestamp,
                trend_type="uptrend",
                trend_strength=self._calculate_trend_strength(recent_prices),
                source=f"tick_channel_{self.channel_id}"
            )
        
        # Check for consistent downtrend
        elif all(recent_prices[i] < recent_prices[i-1] for i in range(1, len(recent_prices))):
            return TrendEvent(
                event_id=self.generate_unique_event_id(data.ticker, "downtrend"),
                ticker=data.ticker,
                price=data.price,
                volume=data.volume,
                timestamp=data.timestamp,
                trend_type="downtrend",
                trend_strength=self._calculate_trend_strength(recent_prices),
                source=f"tick_channel_{self.channel_id}"
            )
        
        return None
    
    def _calculate_trend_strength(self, prices: List[float]) -> float:
        """Calculate trend strength as percentage change over period"""
        if len(prices) < 2:
            return 0.0
        
        return abs((prices[-1] - prices[0]) / prices[0]) * 100


class OHLCVEventCreator(BaseEventCreator):
    """
    Event creator for OHLCV aggregate data processing.
    
    Creates aggregate events, volume surge detection, and significant move
    events from batched OHLCV data with multi-period analysis capabilities.
    """
    
    def __init__(self, channel_name: str, channel_id: str):
        super().__init__(channel_name, channel_id)
        self.significant_move_threshold = 2.0  # 2% for significant moves
        self.volume_surge_threshold = 3.0      # 3x volume surge
    
    def create_events(self, data: OHLCVData, **kwargs) -> List[BaseEvent]:
        """Create events from OHLCV aggregate data"""
        events = []
        
        try:
            # Aggregate Summary Event
            aggregate_event = self._create_aggregate_event(data)
            if aggregate_event:
                events.append(aggregate_event)
            
            # Volume Surge Detection
            if data.avg_volume > 0:
                surge_event = self._detect_volume_surge(data)
                if surge_event:
                    events.append(surge_event)
            
            # Significant Move Detection
            if abs(data.percent_change) >= self.significant_move_threshold:
                move_event = self._create_significant_move_event(data)
                if move_event:
                    events.append(move_event)
            
        except Exception as e:
            logger.error(f"Error creating OHLCV events for {data.ticker}: {e}")
        
        return events
    
    def _create_aggregate_event(self, data: OHLCVData) -> Optional[PerMinuteAggregateEvent]:
        """Create per-minute aggregate summary event"""
        
        return PerMinuteAggregateEvent(
            event_id=self.generate_unique_event_id(data.ticker, "aggregate"),
            ticker=data.ticker,
            price=data.close,  # Use close price as current price
            volume=data.volume,
            timestamp=data.timestamp,
            open_price=data.open,
            high_price=data.high,
            low_price=data.low,
            close_price=data.close,
            avg_volume=data.avg_volume,
            percent_change=data.percent_change,
            source=f"ohlcv_channel_{self.channel_id}"
        )
    
    def _detect_volume_surge(self, data: OHLCVData) -> Optional[SurgeEvent]:
        """Detect volume surges in OHLCV data"""
        
        surge_multiplier = data.volume / data.avg_volume
        if surge_multiplier >= self.volume_surge_threshold:
            return SurgeEvent(
                event_id=self.generate_unique_event_id(data.ticker, "volume_surge"),
                ticker=data.ticker,
                price=data.close,
                volume=data.volume,
                timestamp=data.timestamp,
                avg_volume=data.avg_volume,
                surge_multiplier=surge_multiplier,
                source=f"ohlcv_channel_{self.channel_id}"
            )
        
        return None
    
    def _create_significant_move_event(self, data: OHLCVData) -> Optional[TrendEvent]:
        """Create event for significant price movements"""
        
        trend_type = "uptrend" if data.percent_change > 0 else "downtrend"
        
        return TrendEvent(
            event_id=self.generate_unique_event_id(data.ticker, f"significant_{trend_type}"),
            ticker=data.ticker,
            price=data.close,
            volume=data.volume,
            timestamp=data.timestamp,
            trend_type=trend_type,
            trend_strength=abs(data.percent_change),
            source=f"ohlcv_channel_{self.channel_id}"
        )


class FMVEventCreator(BaseEventCreator):
    """
    Event creator for Fair Market Value (FMV) data processing.
    
    Creates valuation events, confidence-based filtering, and deviation
    alerts from FMV calculations with market sentiment analysis.
    """
    
    def __init__(self, channel_name: str, channel_id: str):
        super().__init__(channel_name, channel_id)
        self.confidence_threshold = 0.8    # 80% confidence minimum
        self.deviation_threshold = 1.0     # 1% deviation threshold
    
    def create_events(self, data: FMVData, **kwargs) -> List[BaseEvent]:
        """Create events from FMV data"""
        events = []
        
        # Only process high-confidence FMV data
        if data.confidence < self.confidence_threshold:
            logger.debug(f"Skipping low-confidence FMV data for {data.ticker}: {data.confidence}")
            return events
        
        try:
            # Fair Market Value Event
            fmv_event = self._create_fmv_event(data)
            if fmv_event:
                events.append(fmv_event)
            
            # Deviation Alert Event
            if abs(data.calculate_deviation()) >= self.deviation_threshold:
                deviation_event = self._create_deviation_event(data)
                if deviation_event:
                    events.append(deviation_event)
            
        except Exception as e:
            logger.error(f"Error creating FMV events for {data.ticker}: {e}")
        
        return events
    
    def _create_fmv_event(self, data: FMVData) -> Optional[FairMarketValueEvent]:
        """Create fair market value event"""
        
        return FairMarketValueEvent(
            event_id=self.generate_unique_event_id(data.ticker, "fmv"),
            ticker=data.ticker,
            price=data.market_price,  # Use current market price
            volume=0,  # FMV doesn't include volume
            timestamp=data.timestamp,
            fair_market_value=data.fmv,
            confidence=data.confidence,
            deviation_percent=data.calculate_deviation(),
            source=f"fmv_channel_{self.channel_id}"
        )
    
    def _create_deviation_event(self, data: FMVData) -> Optional[TrendEvent]:
        """Create deviation alert event for significant FMV deviations"""
        
        deviation = data.calculate_deviation()
        trend_type = "overvalued" if deviation > 0 else "undervalued"
        
        return TrendEvent(
            event_id=self.generate_unique_event_id(data.ticker, f"fmv_{trend_type}"),
            ticker=data.ticker,
            price=data.market_price,
            volume=0,
            timestamp=data.timestamp,
            trend_type=trend_type,
            trend_strength=abs(deviation),
            source=f"fmv_channel_{self.channel_id}"
        )


# Factory function for creating event creators
def create_event_creator(channel_type: str, channel_name: str, channel_id: str) -> BaseEventCreator:
    """Factory function to create appropriate event creator"""
    
    if channel_type.lower() == 'tick':
        return TickEventCreator(channel_name, channel_id)
    elif channel_type.lower() == 'ohlcv':
        return OHLCVEventCreator(channel_name, channel_id)
    elif channel_type.lower() == 'fmv':
        return FMVEventCreator(channel_name, channel_id)
    else:
        raise ValueError(f"Unknown channel type: {channel_type}")


# Utility functions for event validation and transport
def validate_event_transport_format(events: List[BaseEvent]) -> Dict[str, Any]:
    """Validate multiple events for transport compatibility"""
    results = {
        'total_events': len(events),
        'valid_events': 0,
        'invalid_events': 0,
        'validation_errors': []
    }
    
    for i, event in enumerate(events):
        try:
            transport_dict = event.to_transport_dict()
            
            # Basic validation
            required_fields = ['ticker', 'type', 'price', 'time', 'event_id']
            for field in required_fields:
                if field not in transport_dict:
                    results['validation_errors'].append(f"Event {i}: Missing field '{field}'")
                    results['invalid_events'] += 1
                    continue
            
            results['valid_events'] += 1
            
        except Exception as e:
            results['validation_errors'].append(f"Event {i}: Transport error: {str(e)}")
            results['invalid_events'] += 1
    
    return results


def batch_create_transport_dicts(events: List[BaseEvent]) -> List[Dict[str, Any]]:
    """Batch convert events to transport dictionaries"""
    transport_dicts = []
    
    for event in events:
        try:
            transport_dict = event.to_transport_dict()
            transport_dicts.append(transport_dict)
        except Exception as e:
            logger.error(f"Failed to convert event to transport dict: {e}")
            # Skip invalid events rather than failing entire batch
    
    return transport_dicts