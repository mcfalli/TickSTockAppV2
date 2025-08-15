"""
Event Detection Coordinator
Thin coordination layer for all event detection types.
SPRINT 21 PHASE 4: Pure typed event system - no dict handling
"""

import logging
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from src.core.domain.market.tick import TickData
from src.core.domain.events.base import BaseEvent
from src.core.domain.events.highlow import HighLowEvent
from src.core.domain.events.trend import TrendEvent
from src.core.domain.events.surge import SurgeEvent
from src.presentation.converters.transport_models import StockData

from src.monitoring.tracer import tracer, TraceLevel, normalize_event_type, ensure_int



from config.logging_config import get_domain_logger, LogDomain

logger = get_domain_logger(LogDomain.CORE, 'event_detector')

class DataFlowStats:
    def __init__(self):
        self.ticks_analyzed = 0
        self.events_detected = 0
        self.highs_detected = 0
        self.lows_detected = 0
        self.trends_detected = 0
        self.surges_detected = 0
        self.detection_errors = 0
        self.last_log_time = time.time()
        self.log_interval = 30  # seconds
        
    def should_log(self):
        return time.time() - self.last_log_time >= self.log_interval
        
    def log_stats(self):
        #logger.debug(f"📊 DIAG-EVENT-DETECTOR: EVENT FLOW: Analyzed:{self.ticks_analyzed} → Events:{self.events_detected} (H:{self.highs_detected} L:{self.lows_detected} T:{self.trends_detected} S:{self.surges_detected}) | Err?:{self.detection_errors}")
        self.last_log_time = time.time()

@dataclass
class EventDetectionResult:
    """Result object for event detection operations."""
    success: bool = True
    events_detected: List[BaseEvent] = None  # PHASE 4: Typed events only
    errors: List[str] = None
    warnings: List[str] = None
    detection_time_ms: float = 0
    detectors_run: List[str] = None
    
    def __post_init__(self):
        if self.events_detected is None:
            self.events_detected = []
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if self.detectors_run is None:
            self.detectors_run = []

class EventDetector:
    """
    Coordinates event detection across multiple detector types.
    PHASE 4: Pure typed event handling - no dict compatibility
    """
    
    def __init__(self, config: Dict[str, Any], 
                 event_manager=None,  # Accept event manager
                 highlow_detector=None,  # Keep for backward compatibility
                 trend_detector=None,
                 surge_detector=None):
        """Initialize event detection coordinator."""
        self.config = config
        
        # Use event_manager if provided, otherwise fall back to individual detectors
        if event_manager:
            self.event_manager = event_manager
            self.highlow_detector = event_manager.get_detector('highlow')
            self.trend_detector = event_manager.get_detector('trend')
            self.surge_detector = event_manager.get_detector('surge')
        else:
            # Backward compatibility
            self.event_manager = None
            self.highlow_detector = highlow_detector
            self.trend_detector = trend_detector
            self.surge_detector = surge_detector
        
        # Data flow tracking
        self.stats = DataFlowStats()
        
        logger.info(f"EventDetector initialized with detectors: "
                   f"HighLow={self.highlow_detector is not None}, "
                   f"Trend={self.trend_detector is not None}, "
                   f"Surge={self.surge_detector is not None}")
    
    def detect_events(self, ticker: str, tick_data: TickData, stock_details: StockData) -> EventDetectionResult:
        """
        Coordinate event detection across all detector types.
        """
        start_time = time.time()
        result = EventDetectionResult()
        
        try:
            self.stats.ticks_analyzed += 1
            
            # Log first few ticks for diagnostics
            if self.stats.ticks_analyzed <= 25:
                logger.debug(f"📥 DIAG-EVENT-DETECTOR: Analyzing tick #{self.stats.ticks_analyzed}: {ticker} @ ${tick_data.price}")
            
            # Track events by type for single quality trace
            event_summary = {
                'highs': 0,
                'lows': 0,
                'trends': 0,
                'surges': 0
            }
            
            # Run high/low detection
            if self.highlow_detector:
                highlow_events = self._detect_highlow_events(ticker, tick_data, stock_details)
                
                if highlow_events:
                    #logger.debug(f"🔍DIAG-EVENT-DETECTOR: Found {len(highlow_events)} high/low events for {ticker}")
                    result.events_detected.extend(highlow_events)
                    result.detectors_run.append('highlow')
                    
                    # Count high/low events
                    for event in highlow_events:
                        if event.type in ['session_high', 'high']:
                            self.stats.highs_detected += 1
                            event_summary['highs'] += 1
                            if self.stats.highs_detected <= 25:
                                logger.debug(f"🎯DIAG-EVENT-DETECTOR: HIGH #{self.stats.highs_detected}: {ticker} @ ${event.price}")
                        elif event.type in ['session_low', 'low']:
                            self.stats.lows_detected += 1
                            event_summary['lows'] += 1
                            if self.stats.lows_detected <= 25:
                                logger.debug(f"🎯DIAG-EVENT-DETECTOR: LOW #{self.stats.lows_detected}: {ticker} @ ${event.price}")
            
            # Run trend detection
            if self.trend_detector:
                trend_events = self._detect_trend_events(ticker, tick_data, stock_details)
                if trend_events:
                    #logger.debug(f"🔍DIAG-EVENT-DETECTOR: Found {len(trend_events)} trend events for {ticker}")
                    result.events_detected.extend(trend_events)
                    result.detectors_run.append('trend')
                    self.stats.trends_detected += len(trend_events)
                    event_summary['trends'] = len(trend_events)
                    
                    #if self.stats.trends_detected <= 25:
                    #    for event in trend_events:
                    #        logger.debug(f"🎯DIAG-EVENT-DETECTOR: TREND: {ticker} {event.direction} strength:{event.trend_strength}")
            
            # Run surge detection
            if self.surge_detector:
                surge_events = self._detect_surge_events(ticker, tick_data, stock_details)
                if surge_events:
                    #logger.debug(f"🔍DIAG-EVENT-DETECTOR: Found {len(surge_events)} surge events for {ticker}")
                    result.events_detected.extend(surge_events)
                    result.detectors_run.append('surge')
                    self.stats.surges_detected += len(surge_events)
                    event_summary['surges'] = len(surge_events)
                    
                    #if self.stats.surges_detected <= 25:
                    #    for event in surge_events:
                    #        logger.debug(f"🎯DIAG-EVENT-DETECTOR: SURGE: {ticker} {event.direction} magnitude:{abs(event.surge_magnitude):.1f}%")
            
            # Update total events
            self.stats.events_detected += len(result.events_detected)
            result.success = True
            
            # SINGLE QUALITY TRACE: Only trace if events were detected or on error
            if tracer.should_trace(ticker) and len(result.events_detected) > 0:
                # Don't trace individual events here - let the specific detectors handle it
                # Just trace a summary
                event_summary = {}
                for event in result.events_detected:
                    normalized_type = normalize_event_type(event.type if hasattr(event, 'type') else 'unknown')
                    event_summary[normalized_type] = event_summary.get(normalized_type, 0) + 1
                
                # Single summary trace instead of per-event traces
                tracer.trace(
                    ticker=ticker,
                    component='EventDetector',
                    action='detection_summary',
                    data={
                        'input_count': ensure_int(1),
                        'output_count': ensure_int(len(result.events_detected)),
                        'duration_ms': (time.time() - start_time) * 1000,
                        'details': {
                            'event_breakdown': event_summary,
                            'detectors_run': result.detectors_run,
                            'price': tick_data.price,
                            'volume': getattr(tick_data, 'volume', None)
                        }
                    }
                )
                
                
            
            # Performance warning - only for slow detections
            detection_time = (time.time() - start_time) * 1000
            if detection_time > 100:
                logger.warning(f"⚠️DIAG-EVENT-DETECTOR: SLOW DETECTION > 100ms: {detection_time:.1f}ms for {ticker}")
                
                # Trace slow detection for performance analysis
                if tracer.should_trace(ticker):
                    tracer.trace(
                        ticker=ticker,
                        component='EventDetector',
                        action='detection_slow',
                        data={
                            'input_count': ensure_int(1),
                            'output_count': ensure_int(len(result.events_detected)),
                            'duration_ms': detection_time,
                            'details': {
                                'threshold_ms': 100,
                                'detectors_run': result.detectors_run
                            }
                        }
                    )
            
            # Periodic stats
            if self.stats.should_log():
                self.stats.log_stats()
            
        except Exception as e:
            error_msg = f"Error in event detection for {ticker}: {e}"
            logger.error(f"❌ DETECTION EXCEPTION: {error_msg}", exc_info=True)
            result.success = False
            result.errors.append(error_msg)
            self.stats.detection_errors += 1
            
            # TRACE: Error - always trace errors for debugging
            if tracer.should_trace(ticker):
                tracer.trace(
                    ticker=ticker,
                    component='EventDetector',
                    action='detection_error',
                    data={
                        'input_count': ensure_int(1),
                        'output_count': ensure_int(0),
                        'duration_ms': (time.time() - start_time) * 1000,
                        'error': str(e),
                        'details': {
                            'error_type': type(e).__name__,
                            'price': tick_data.price
                        }
                    }
                )
        
        finally:
            result.detection_time_ms = (time.time() - start_time) * 1000
            
        return result
    
    def _detect_highlow_events(self, ticker: str, tick_data: TickData, stock_details: StockData) -> List[HighLowEvent]:
        """
        Detect high/low events using the stock tick event detector.
        PHASE 4: Returns typed HighLowEvent objects only
        """
        try:
            # Call the main event detection method with BOTH required arguments
            detection_result = self.highlow_detector.detect_highlow(
                tick_data,      # TickData object
                stock_details   # StockData object (passed from detect_events)
            )

            if detection_result and 'events' in detection_result:
                events = detection_result['events']

                typed_events = []
                for event in events:
                    if isinstance(event, HighLowEvent):
                        typed_events.append(event)
                
                return typed_events
            else:
                return []
            
        except Exception as e:
            logger.error(f"❌ High/low detection error for {ticker}: {e}", exc_info=True)
            return []
        
    def _detect_trend_events(self, ticker: str, tick_data: TickData, stock_details: StockData) -> List[TrendEvent]:
        """
        Detect trend events using trend detector.
        PHASE 4: Returns typed TrendEvent objects only
        """
        try:
            # Run trend detection
            trend_result = self.trend_detector.detect_trend(
                stock_data=stock_details,
                ticker=ticker,
                price=tick_data.price,
                vwap=getattr(tick_data, 'vwap', None),
                volume=getattr(tick_data, 'volume', None),
                tick_vwap=getattr(tick_data, 'tick_vwap', None),
                tick_volume=getattr(tick_data, 'tick_volume', None),
                tick_trade_size=getattr(tick_data, 'tick_trade_size', None),
                timestamp=tick_data.timestamp
            )
            
            if trend_result and 'events' in trend_result:
                typed_events = []
                for event in trend_result['events']:
                    if isinstance(event, TrendEvent):
                        typed_events.append(event)
                    else:
                        logger.warning(f"⚠️DIAG-EVENT-DETECTOR: Unexpected non-typed trend event: {type(event)}")
                
                return typed_events
            else:
                return []
            
        except Exception as e:
            logger.error(f"❌ Trend detection error for {ticker}: {e}", exc_info=True)
            return []

    def _detect_surge_events(self, ticker: str, tick_data: TickData, stock_details: StockData) -> List[SurgeEvent]:
        """
        Detect surge events using surge detector.
        PHASE 4: Returns typed SurgeEvent objects only
        """
        try:
            # Add timestamp to debug multiple calls
            call_time = time.time()
            #logger.debug(f"📍 DIAG-EVENT-DETECTOR: Calling detect_surge for {ticker} at {call_time}")
            
            # Run surge detection
            surge_result = self.surge_detector.detect_surge(
                stock_data=stock_details,
                ticker=ticker,
                price=tick_data.price,
                vwap=getattr(tick_data, 'vwap', None),
                volume=getattr(tick_data, 'volume', None),
                tick_vwap=getattr(tick_data, 'tick_vwap', None),
                tick_volume=getattr(tick_data, 'tick_volume', None),
                tick_trade_size=getattr(tick_data, 'tick_trade_size', None)
            )
            
            # Log the actual result
            event_count = len(surge_result.get('events', [])) if surge_result else 0
            #logger.debug(f"📍 DIAG-EVENT-DETECTOR: detect_surge returned {event_count} events for {ticker}")
            
            if surge_result and 'events' in surge_result:
                typed_events = []
                for event in surge_result['events']:
                    if isinstance(event, SurgeEvent):
                        typed_events.append(event)
                        #logger.debug(f"✅ DIAG-EVENT-DETECTOR: Adding surge event for {ticker}: {event.surge_trigger_type}")
                    else:
                        logger.warning(f"⚠️DIAG-EVENT-DETECTOR: Unexpected non-typed surge event: {type(event)}")
                
                return typed_events
            else:
                return []
                
        except Exception as e:
            logger.error(f"❌ Surge detection error for {ticker}: {e}", exc_info=True)
            return []
    
    def check_data_flow_health(self):
        """Diagnose where data flow is breaking."""
        if self.stats.ticks_analyzed == 0:
            logger.error("🚨 DIAG-EVENT-DETECTOR: NO TICKS ANALYZED - Check if events are reaching detector")
        elif self.stats.events_detected == 0:
            logger.warning("⚠️ DIAG-EVENT-DETECTOR: Ticks analyzed but NO EVENTS DETECTED - Normal or check thresholds")
        
        detection_rate = (self.stats.events_detected / max(self.stats.ticks_analyzed, 1)) * 100
        
        #logger.debug(f"🔍DIAG-EVENT-DETECTOR: HEALTH CHECK: Detection rate {detection_rate:.1f}% ({self.stats.events_detected}/{self.stats.ticks_analyzed})")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get detection statistics."""
        return {
            'data_flow': {
                'ticks_analyzed': self.stats.ticks_analyzed,
                'events_detected': self.stats.events_detected,
                'highs': self.stats.highs_detected,
                'lows': self.stats.lows_detected,
                'trends': self.stats.trends_detected,
                'surges': self.stats.surges_detected,
                'errors': self.stats.detection_errors
            },
            'detection_rate': (self.stats.events_detected / max(self.stats.ticks_analyzed, 1)) * 100
        }
        
    
