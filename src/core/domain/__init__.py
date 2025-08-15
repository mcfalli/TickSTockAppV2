# classes/__init__.py
"""TickStock type-safe class definitions"""

from src.core.domain.events import BaseEvent, HighLowEvent, TrendEvent, SurgeEvent
from src.core.domain.market import TickData, TickerState
from src.core.domain.transport import StockData, EventCounts, HighLowBar
from src.core.domain.analytics import TickerAnalytics, UniverseAnalytics, GaugeAnalytics
from src.core.domain.processing import QueuedEvent, TypedEventQueue

__all__ = [
    # Events
    'BaseEvent', 'HighLowEvent', 'TrendEvent', 'SurgeEvent',
    # Market
    'TickData', 'TickerState',
    # Transport
    'StockData', 'EventCounts', 'HighLowBar',
    # Analytics
    'TickerAnalytics', 'UniverseAnalytics', 'GaugeAnalytics',
    # Processing
    'QueuedEvent', 'TypedEventQueue'
]