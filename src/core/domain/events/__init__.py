# classes/events/__init__.py
"""Event classes for TickStock type-safe architecture"""

from src.core.domain.events.base import BaseEvent
from src.core.domain.events.highlow import HighLowEvent
from src.core.domain.events.trend import TrendEvent
from src.core.domain.events.surge import SurgeEvent

__all__ = ['BaseEvent', 'HighLowEvent', 'TrendEvent', 'SurgeEvent']