"""Module initialization."""

from .manager import EventDetectionManager
from .highlow_detector import HighLowDetector
from .trend_detector import TrendDetector
from .surge_detector import SurgeDetector
__all__ = ['EventDetectionManager', 'HighLowDetector', 'TrendDetector', 'SurgeDetector']
