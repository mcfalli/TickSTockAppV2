"""
Event Detection Engines
Individual detection engines for different types of market events.
"""

from src.processing.detectors.highlow_detector import HighLowDetector
from src.processing.detectors.engines.surge_detector import SurgeDetector
from src.processing.detectors.engines.trend_detector import TrendDetector
from src.processing.detectors.engines.buysell_tracker import BuySellTracker

__all__ = [
    'HighLowDetector',
    'SurgeDetector',
    'TrendDetector',
    'BuySellTracker'
]