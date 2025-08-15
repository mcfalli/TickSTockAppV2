"""
Tick Processor - Core tick data processing and validation
Handles tick validation, preprocessing, and normalization.
"""

import logging
import time
from typing import Any, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from src.core.domain.market.tick import TickData 
from config.logging_config import get_domain_logger, LogDomain

from src.monitoring.tracer import tracer, TraceLevel, normalize_event_type, ensure_int

logger = get_domain_logger(LogDomain.CORE, 'tick_processor')

class DataFlowStats:
    def __init__(self):
        self.ticks_received = 0
        self.ticks_validated = 0
        self.ticks_processed = 0
        self.validation_failures = 0
        self.last_log_time = time.time()
        self.log_interval = 30  # seconds
        
    def should_log(self):
        return time.time() - self.last_log_time >= self.log_interval
        
    def log_stats(self):
        logger.debug(f"📊 DIAG-TICK: TICK FLOW: In:{self.ticks_received} → Validated:{self.ticks_validated} → Out:{self.ticks_processed} | Failed:{self.validation_failures}")
        self.last_log_time = time.time()

@dataclass
class TickProcessingResult:
    """Result object for tick processing operations."""
    success: bool = True
    errors: list = None
    warnings: list = None
    processed_tick: TickData = None
    ticker: str = None
    validation_passed: bool = True
    preprocessing_time_ms: float = 0
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []

class TickProcessor:
    """
    Handles core tick processing logic.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize tick processor."""
        self.config = config
        
        # Extract relevant config
        self.rate_limit = config.get('EVENT_RATE_LIMIT', 0.1)
        
        # Data flow tracking
        self.stats = DataFlowStats()
        
    def process_tick(self, tick_data: TickData, last_event_time: float = None) -> TickProcessingResult:
        """Process and validate incoming tick data."""
        start_time = time.time()
        result = TickProcessingResult(ticker=tick_data.ticker if tick_data else 'unknown')
        
        try:
            self.stats.ticks_received += 1
            
            # Step 1: Basic validation
            validation_result = self._validate_tick(tick_data)
            if not validation_result[0]:
                result.success = False
                result.validation_passed = False
                result.errors.append(validation_result[1])
                self.stats.validation_failures += 1
                
                return result
            
            self.stats.ticks_validated += 1
            
            # Step 2: Rate limiting check
            if last_event_time is not None:
                current_time = time.time()
                # Handle different formats of last_event_time
                if isinstance(last_event_time, str):
                    if ':' in last_event_time:
                        last_event_time = None
                    else:
                        try:
                            last_event_time = float(last_event_time)
                        except ValueError:
                            last_event_time = None
                elif isinstance(last_event_time, datetime):  
                    last_event_time = last_event_time.timestamp()
                
                # Only do rate limit check if we have a valid timestamp
                if last_event_time is not None:
                    time_since_last = current_time - last_event_time
                    
                    if time_since_last < self.rate_limit:
                        # TRACE: Rate limit hit
                        if tracer.should_trace(tick_data.ticker):
                            tracer.trace(
                                ticker=tick_data.ticker,
                                component="TickProcessor",
                                action="rate_limit_blocked",
                                data={
                                    'timestamp': current_time,
                                    'input_count': ensure_int(1),
                                    'output_count': ensure_int(0),
                                    'duration_ms': (time.time() - start_time) * 1000,
                                    'details': {
                                        'time_since_last_event': time_since_last,
                                        'rate_limit_threshold': self.rate_limit,
                                        'last_event_time': last_event_time,
                                        'would_have_price': getattr(tick_data, 'price', None)
                                    }
                                }
                            )
                        
                        result.success = False
                        result.warnings.append(f"Rate limited: {time_since_last:.3f}s < {self.rate_limit}s")
                        return result
                    else:
                        # TRACE: Rate limit passed (only trace if close to limit)
                        if time_since_last < self.rate_limit * 2 and tracer.should_trace(tick_data.ticker):
                            tracer.trace(
                                ticker=tick_data.ticker,
                                component="TickProcessor",
                                action="rate_limit_passed",
                                data={
                                    'timestamp': current_time,
                                    'input_count': ensure_int(1),
                                    'output_count': ensure_int(1),
                                    'duration_ms': (time.time() - start_time) * 1000,
                                    'details': {
                                        'time_since_last_event': time_since_last,
                                        'rate_limit_threshold': self.rate_limit,
                                        'margin': time_since_last - self.rate_limit
                                    }
                                }
                            )
            
            # Step 3: Set effective fields for backward compatibility
            processed_tick = self._set_effective_fields(tick_data)
            
            # Success
            result.processed_tick = processed_tick
            result.success = True
            self.stats.ticks_processed += 1
            
            # Log performance warning
            processing_time = (time.time() - start_time) * 1000
            if processing_time > 100:
                logger.debug(f"⚠️ DIAG-TICK-PROCESSOR: SLOW TICK PROCESSING: {processing_time:.1f}ms for {tick_data.ticker}")
            
            # Periodic stats
            if self.stats.should_log():
                self.stats.log_stats()
            
        except Exception as e:
            error_msg = f"Error processing tick for {tick_data.ticker if tick_data else 'unknown'}: {e}"
            logger.error(f"❌ TICK PROCESSING EXCEPTION: {error_msg}")
            result.success = False
            result.errors.append(error_msg)
        
        finally:
            result.preprocessing_time_ms = (time.time() - start_time) * 1000
            
        return result
    
    def _validate_tick(self, tick_data: Any) -> Tuple[bool, Optional[str]]:
        """Validate basic tick data requirements."""
        if not tick_data:
            return False, "Tick data is None"
        
        if not hasattr(tick_data, 'ticker') or not tick_data.ticker:
            return False, "Missing ticker symbol"
        
        if not hasattr(tick_data, 'price') or tick_data.price is None:
            return False, f"Missing price for {tick_data.ticker}"
        
        if tick_data.price <= 0:
            return False, f"Invalid price {tick_data.price} for {tick_data.ticker}"
        
        if not hasattr(tick_data, 'timestamp') or not tick_data.timestamp:
            return False, f"Missing timestamp for {tick_data.ticker}"
        
        return True, None
    
    def _set_effective_fields(self, tick_data: TickData) -> TickData:
        """Set effective fields for backward compatibility."""
        # Set processing timestamp
        tick_data.processed_at = time.time()
        
        # Set effective volume (prefer tick-level over aggregate)
        if tick_data.tick_volume is not None:
            tick_data.effective_volume = tick_data.tick_volume
        elif tick_data.volume is not None:
            tick_data.effective_volume = tick_data.volume
        else:
            tick_data.effective_volume = 0
        
        # Set effective VWAP (prefer tick-level over aggregate)
        if tick_data.tick_vwap is not None:
            tick_data.effective_vwap = tick_data.tick_vwap
        elif tick_data.vwap is not None:
            tick_data.effective_vwap = tick_data.vwap
        else:
            tick_data.effective_vwap = tick_data.price
        
        return tick_data
    

    def check_data_flow_health(self):
        """Diagnose where data flow is breaking."""
        if self.stats.ticks_received == 0:
            logger.error("🚨 DIAG-TICK-PROCESSOR: NO TICKS RECEIVED - Check data source connection")
        elif self.stats.ticks_validated == 0:
            logger.warning("⚠️ DIAG-TICK-PROCESSOR: Ticks received but NONE VALIDATED - Check data quality")
        elif self.stats.ticks_processed == 0:
            logger.error("🚨 DIAG-TICK-PROCESSOR: Ticks validated but NOT PROCESSED - Check processing logic")
            
        validation_rate = (self.stats.ticks_validated / max(self.stats.ticks_received, 1)) * 100
        process_rate = (self.stats.ticks_processed / max(self.stats.ticks_validated, 1)) * 100
        
        logger.debug(f"🔍 DIAG-TICK-PROCESSOR: HEALTH CHECK: Validation rate {validation_rate:.1f}%, Process rate {process_rate:.1f}%")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get processor statistics."""
        #'validate_prices': self.validate_prices,
        #'max_price_change_percent': self.max_price_change_percent

        return {
            'data_flow': {
                'ticks_received': self.stats.ticks_received,
                'ticks_validated': self.stats.ticks_validated,
                'ticks_processed': self.stats.ticks_processed,
                'validation_failures': self.stats.validation_failures
            },
            'success_rate': (self.stats.ticks_processed / max(self.stats.ticks_received, 1)) * 100,
            'config': {
                'rate_limit': self.rate_limit,
            }
        }