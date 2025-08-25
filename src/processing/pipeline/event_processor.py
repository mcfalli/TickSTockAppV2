"""
Event Processing Logic - HEAVILY SIMPLIFIED (Phase 3 Cleanup)
Maintains core data processing interface but removes event generation logic.
Events now come from TickStockPL via Redis pub-sub.
"""

import logging
import time
from datetime import datetime
from typing import Dict, List, Any, Optional  
from dataclasses import dataclass, field

from src.core.domain.market.tick import TickData
from src.core.domain.events.base import BaseEvent
from src.presentation.converters.transport_models import StockData

from config.logging_config import get_domain_logger, LogDomain
from src.processing.pipeline.tick_processor import TickProcessor, TickProcessingResult

logger = get_domain_logger(LogDomain.PROCESSING, 'event_processor')

@dataclass
class ProcessingStats:
    """Simplified processing statistics"""
    ticks_processed: int = 0
    events_forwarded: int = 0
    processing_errors: int = 0
    last_processing_time: Optional[datetime] = None
    
    def reset(self):
        """Reset all counters"""
        self.ticks_processed = 0
        self.events_forwarded = 0
        self.processing_errors = 0
        self.last_processing_time = None

@dataclass 
class ProcessingResult:
    """Result of tick processing operation"""
    success: bool = True
    stock_data: Optional[StockData] = None
    events: List[BaseEvent] = field(default_factory=list)
    error_message: Optional[str] = None
    processing_time_ms: float = 0.0

class EventProcessor:
    """
    Event Processor - HEAVILY SIMPLIFIED (Phase 3 Cleanup)
    
    Previous functionality:
    - Complex event detection and generation
    - Multi-detector coordination  
    - Event routing and accumulation
    - Pattern analysis and alerting
    
    Current functionality:
    - Basic tick data processing
    - Data forwarding to Redis for TickStockPL
    - Interface compatibility maintenance
    """
    
    def __init__(self, config=None, cache_control=None):
        """Initialize simplified event processor"""
        self.config = config
        self.cache_control = cache_control
        self.stats = ProcessingStats()
        self.tick_processor = TickProcessor() if TickProcessor else None
        logger.info("EventProcessor initialized as simplified version (Phase 3 cleanup)")
    
    def process_tick(self, tick_data: TickData, session_date: str = None) -> ProcessingResult:
        """
        Process single tick data - SIMPLIFIED IMPLEMENTATION
        
        Args:
            tick_data: Market tick data
            session_date: Trading session date
            
        Returns:
            ProcessingResult with basic stock data (no events generated)
        """
        start_time = time.time()
        result = ProcessingResult()
        
        try:
            self.stats.ticks_processed += 1
            self.stats.last_processing_time = datetime.now()
            
            # Basic tick processing (if available)
            if self.tick_processor and tick_data:
                try:
                    tick_result = self.tick_processor.process_tick(tick_data)
                    if hasattr(tick_result, 'stock_data'):
                        result.stock_data = tick_result.stock_data
                except Exception as e:
                    logger.debug(f"Tick processor not available or failed: {e}")
            
            # Create basic stock data if tick processor unavailable
            if not result.stock_data and tick_data:
                result.stock_data = self._create_basic_stock_data(tick_data)
            
            # Phase 3 cleanup: No event generation - events come from TickStockPL
            result.events = []
            
            result.success = True
            result.processing_time_ms = (time.time() - start_time) * 1000
            
        except Exception as e:
            self.stats.processing_errors += 1
            result.success = False
            result.error_message = str(e)
            result.processing_time_ms = (time.time() - start_time) * 1000
            logger.error(f"Error processing tick for {getattr(tick_data, 'ticker', 'unknown')}: {e}")
        
        return result
    
    def _create_basic_stock_data(self, tick_data: TickData) -> StockData:
        """Create basic stock data from tick"""
        return StockData(
            ticker=getattr(tick_data, 'ticker', 'UNKNOWN'),
            timestamp=getattr(tick_data, 'timestamp', datetime.now()),
            price=getattr(tick_data, 'price', 0.0),
            volume=getattr(tick_data, 'volume', 0)
        )
    
    def process_tick_batch(self, tick_batch: List[TickData], session_date: str = None) -> List[ProcessingResult]:
        """
        Process batch of ticks - SIMPLIFIED IMPLEMENTATION
        
        Args:
            tick_batch: List of tick data
            session_date: Trading session date
            
        Returns:
            List of processing results
        """
        results = []
        for tick_data in tick_batch:
            result = self.process_tick(tick_data, session_date)
            results.append(result)
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        return {
            'ticks_processed': self.stats.ticks_processed,
            'events_forwarded': self.stats.events_forwarded,
            'processing_errors': self.stats.processing_errors,
            'last_processing_time': self.stats.last_processing_time,
            'uptime_seconds': time.time() - (self.stats.last_processing_time.timestamp() if self.stats.last_processing_time else time.time())
        }
    
    def reset_stats(self):
        """Reset processing statistics"""
        self.stats.reset()
        logger.debug("EventProcessor stats reset")
    
    def shutdown(self):
        """Cleanup processor resources"""
        logger.info("EventProcessor shutting down (simplified version)")

# Maintain interface compatibility
def create_event_processor(config=None, cache_control=None) -> EventProcessor:
    """Factory function for event processor"""
    return EventProcessor(config=config, cache_control=cache_control)