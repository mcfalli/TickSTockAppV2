# event_detection_manager.py
from config.logging_config import get_domain_logger, LogDomain
from src.processing.detectors.highlow_detector import HighLowDetector
from src.processing.detectors.surge_detector import SurgeDetector  
from src.processing.detectors.trend_detector import TrendDetector  
from typing import Dict, List, Any
from dataclasses import dataclass

logger = get_domain_logger(LogDomain.CORE, 'event_manager')

@dataclass
class EventDetectionResult:
    """Container for all event detection results"""
    highlow_events: List[Dict[str, Any]]
    surge_events: List[Dict[str, Any]]
    trend_events: List[Dict[str, Any]]
    
    '''
    def has_events(self) -> bool:
        """Check if any events were detected"""
        return bool(self.highlow_events or self.surge_events or self.trend_events)
    def all_events(self) -> List[Dict[str, Any]]:
        """Get all events with type tagging"""
        events = []
        for event in self.highlow_events:
            events.append({**event, 'event_type': 'highlow'})
        for event in self.surge_events:
            events.append({**event, 'event_type': 'surge'})
        for event in self.trend_events:
            events.append({**event, 'event_type': 'trend'})
        return events
    '''


class EventDetectionManager:
    """Unified manager for all event detection types"""
    
    def __init__(self, config, cache_control):
        self.config = config
        self.cache_control = cache_control
        
        # Initialize all detectors
        self.highlow_detector = HighLowDetector(config, cache_control)
        self.surge_detector = SurgeDetector(config, cache_control)
        self.trend_detector = TrendDetector(config, cache_control)
        
        # Track enabled detectors
        self.enabled_detectors = {
            'highlow': config.get('ENABLE_HIGHLOW_DETECTION', True),
            'surge': config.get('ENABLE_SURGE_DETECTION', True),
            'trend': config.get('ENABLE_TREND_DETECTION', True)
        }
        
        logger.info(f"EventDetectionManager initialized with detectors: {self.enabled_detectors}")
    
    def process_tick(self, tick_data: Dict[str, Any]) -> EventDetectionResult:
        """Process a tick through all enabled detectors"""
        results = EventDetectionResult(
            highlow_events=[],
            surge_events=[],
            trend_events=[]
        )
        
        try:
            # Process through each enabled detector
            if self.enabled_detectors['highlow']:
                results.highlow_events = self.highlow_detector.process_tick(tick_data)
            
            if self.enabled_detectors['surge']:
                results.surge_events = self.surge_detector.process_tick(tick_data)
            
            if self.enabled_detectors['trend']:
                results.trend_events = self.trend_detector.process_tick(tick_data)
                
        except Exception as e:
            logger.error(f"Error in event detection for {tick_data.get('symbol', 'UNKNOWN')}: {e}")
            
        return results
    
    def get_detector(self, detector_type: str):
        """Get a specific detector instance"""
        detectors = {
            'highlow': self.highlow_detector,
            'surge': self.surge_detector,
            'trend': self.trend_detector
        }
        return detectors.get(detector_type)
    
    def reset_symbol(self, symbol: str):
        """Reset all detectors for a specific symbol"""
        self.highlow_detector.reset_symbol(symbol)
        self.surge_detector.reset_symbol(symbol)
        self.trend_detector.reset_symbol(symbol)
        logger.debug(f"Reset all detectors for symbol: {symbol}")
    
    def reset_all_for_new_session(self, new_session: str):
        """Reset all detectors for a new market session"""
        self.highlow_detector.reset_for_new_market_session(new_session)
        self.surge_detector.reset_daily_counts()
        if hasattr(self.trend_detector, 'last_sent_trends'):
            self.trend_detector.last_sent_trends.clear()
        logger.info(f"All detectors reset for new session: {new_session}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get status of all detectors"""
        return {
            'enabled': self.enabled_detectors,
            'highlow_status': self.highlow_detector.get_status() if hasattr(self.highlow_detector, 'get_status') else {},
            'surge_status': self.surge_detector.get_status() if hasattr(self.surge_detector, 'get_status') else {},
            'trend_status': self.trend_detector.get_status() if hasattr(self.trend_detector, 'get_status') else {}
        }