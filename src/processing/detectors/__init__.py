"""
Event Detection System
Handles market event detection including high/low, surge, and trend detection.
"""

from src.processing.detectors.event_detection_manager import EventDetectionManager
from src.processing.detectors.buysell_market_tracker import BuySellMarketTracker

# Import engine classes for convenience
from src.processing.detectors.engines import (
    HighLowDetector,
    SurgeDetector,
    TrendDetector,
    BuySellTracker
)

# Also expose the detection engine classes from src.processing.detectors_engines
from src.processing.detectors.event_detection_engines import (
    HighLowDetectionEngine,
    SurgeDetectionEngine,
    TrendDetectionEngine
)

# Import utility functions from event_detector_util
from . import event_detector_util

__all__ = [
    'EventDetectionManager',
    'BuySellMarketTracker',
    'HighLowDetector',
    'SurgeDetector',
    'TrendDetector',
    'BuySellTracker',
    'HighLowDetectionEngine',
    'SurgeDetectionEngine',
    'TrendDetectionEngine',
    'event_detector_util'  # Export the module itself
]
