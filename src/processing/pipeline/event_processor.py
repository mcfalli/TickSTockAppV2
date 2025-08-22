"""
Event Processing Logic - Sprint 21 Phase 4
Handles all tick processing, event detection, and dual universe logic.
Pure typed event system - no legacy dict handling.
"""

import logging
import time
import traceback  
import src.shared.utils  
from datetime import datetime
import pytz
from typing import Dict, List, Any, Optional  
from dataclasses import dataclass, field

# SPRINT 21 PHASE 4: Only typed classes
from src.core.domain.market.tick import TickData
from src.core.domain.events.base import BaseEvent
from src.core.domain.events.highlow import HighLowEvent
from src.core.domain.events.trend import TrendEvent
from src.core.domain.events.surge import SurgeEvent
from src.presentation.converters.transport_models import StockData, EventCounts, HighLowBar

from config.logging_config import get_domain_logger, LogDomain
from src.processing.pipeline.tick_processor import TickProcessor, TickProcessingResult
from src.processing.pipeline.event_detector import EventDetector, EventDetectionResult


from src.processing.detectors.utils import (
    calculate_vwap_divergence, 
    calculate_relative_volume,
    calculate_percent_change,
    get_base_price,
    map_direction_symbol,
    generate_event_label,
    detect_reversal,
    normalize_timestamp,  
    initialize_ticker_state,
    update_ticker_state,
    handle_market_status_change,
    create_calculation_details
)

from src.shared.utils import (
    generate_event_key,
    get_eastern_time
)

from src.monitoring.tracer import tracer, TraceLevel, normalize_event_type, ensure_int

logger = get_domain_logger(LogDomain.CORE, 'event_processor')

# Data flow tracking
class EventProcessorStats:
    def __init__(self):
        self.ticks_received = 0
        self.ticks_processed = 0
        self.events_detected = 0
        self.events_published = 0
        self.core_universe_hits = 0
        self.trends_processed = 0
        self.surges_processed = 0
        self.high_low_events = 0
        self.errors = 0
        self.last_log_time = time.time()
        self.log_interval = 30  # seconds
        self.first_tick_logged = False
        
    def should_log(self):
        return time.time() - self.last_log_time >= self.log_interval
    
    def log_stats(self, logger):
        filter_rate = 0
        if self.ticks_received > 0:
            filter_rate = ((self.ticks_received - self.ticks_processed) / self.ticks_received) * 100
        
        #logger.debug(f"📊 DIAG-EVENT-PROCESSOR: EVENT PROCESSOR STATS: Ticks:{self.ticks_received} → Processed:{self.ticks_processed} → "
        #           f"Events:{self.events_detected} → "
        #           f"Published:{self.events_published} | "
        #           f"Core:{self.core_universe_hits} | "  
        #           f"H/L:{self.high_low_events} T:{self.trends_processed} S:{self.surges_processed} | "
        #           f"Filter Rate:{filter_rate:.1f}%")
        self.last_log_time = time.time()
    
    def check_health(self, logger):
        """Diagnose common failure modes"""
        if self.ticks_received == 0:
            logger.error("🚨DIAG-EVENT-PROCESSOR:  NO TICKS RECEIVED - Check data source connection")
        elif self.ticks_processed == 0:
            logger.error("🚨DIAG-EVENT-PROCESSOR:  Ticks received but NOT PROCESSED - Check processing logic")
        elif self.events_detected == 0 and self.ticks_processed > 100:
            logger.warning("⚠️DIAG-EVENT-PROCESSOR:  Processing ticks but NO EVENTS detected - Check detection thresholds")
        elif self.events_published == 0 and self.events_detected > 0:
            logger.error("🚨DIAG-EVENT-PROCESSOR:  Events detected but NOT PUBLISHED - Check publishing pipeline")
        
        if self.events_detected > 0:
            h_l_pct = (self.high_low_events / self.events_detected * 100) if self.events_detected > 0 else 0
            trend_pct = (self.trends_processed / self.events_detected * 100) if self.events_detected > 0 else 0
            surge_pct = (self.surges_processed / self.events_detected * 100) if self.events_detected > 0 else 0
            
            #logger.debug(f"📊DIAG-EVENT-PROCESSOR:  Event breakdown: H/L:{self.high_low_events} ({h_l_pct:.1f}%) "
            #        f"Trends:{self.trends_processed} ({trend_pct:.1f}%) "
            #        f"Surges:{self.surges_processed} ({surge_pct:.1f}%)")

@dataclass
class EventProcessingResult:
    """Result object for event processing operations."""
    success: bool = True
    events_processed: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    processing_time_ms: float = 0
    ticker: str = None

class EventProcessor:
    """
    Handles all event processing logic with clean dependency injection.
    PHASE 4: Pure typed event system - no dict handling.
    
    Responsibilities:
    - Coordinate tick processing pipeline
    - Manage dual universe processing
    - Handle ticker state management
    - Orchestrate event detection
    """
    @staticmethod
    def generate_event_key(ticker: str, price: float, event_type: str, timestamp=None) -> str:
        return generate_event_key(ticker, price, event_type, timestamp)

    def __init__(self, config: Dict[str, Any], market_service: Any, event_manager: Any,
            buysell_market_tracker: Optional[Any] = None,
            session_accumulation_manager: Optional[Any] = None, market_analytics_manager: Optional[Any] = None,
            cache_control: Optional[Any] = None, market_metrics: Optional[Any] = None):
        """Initialize event processor with hybrid dependency injection."""
        
        # Core dependencies
        self.market_service = market_service
        self.event_manager = event_manager 
        self.highlow_detector = event_manager.get_detector('highlow')
        self.trend_detector = event_manager.get_detector('trend')
        self.surge_detector = event_manager.get_detector('surge')
        
        # Injected dependencies with fallbacks
        self.buysell_market_tracker = buysell_market_tracker or market_service.buysell_market_tracker
        self.session_accumulation_manager = session_accumulation_manager or market_service.session_accumulation_manager
        self.market_analytics_manager = market_analytics_manager or market_service.market_analytics_manager
        self.cache_control = cache_control or market_service.cache_control
        self.market_metrics = market_metrics or market_service.market_metrics
        
        self.config = config

        # Initialize new extracted components
        self.tick_processor = TickProcessor(config)
        self.event_detector = EventDetector(config, event_manager=event_manager)
        
        # SPRINT 107: Initialize multi-channel integration components
        from src.processing.pipeline.source_context_manager import SourceContextManager
        from src.processing.rules.source_specific_rules import SourceSpecificRulesEngine
        from src.processing.pipeline.multi_source_coordinator import MultiSourceCoordinator
        
        self.source_context_manager = SourceContextManager()
        self.source_rules_engine = SourceSpecificRulesEngine()
        self.multi_source_coordinator = MultiSourceCoordinator()
        
        # Initialize channel router (will be set by market service)
        self.channel_router = None
        
        # Initialize logging
        self.logger = get_domain_logger(LogDomain.CORE, 'event_processor')
        
        # Initialize data flow tracking
        self.stats = EventProcessorStats()

        # SPRINT 27: Validate core universe coverage
        self._validate_core_universe_coverage()
        

    def _validate_core_universe_coverage(self):
        """SPRINT 27 SAFETY: Validate that core universe covers expected tickers post-refactor"""
        try:
            # Get current core universe size
            if hasattr(self.market_service, 'tickstock_universe_manager'):
                core_universe = self.market_service.tickstock_universe_manager.get_core_universe()
                universe_size = len(core_universe) if core_universe else 0
                
                # Expected size from config or default
                expected_min_size = self.config.get('EXPECTED_CORE_UNIVERSE_MIN_SIZE', 2500)
                expected_max_size = self.config.get('EXPECTED_CORE_UNIVERSE_MAX_SIZE', 3000)
                
                if universe_size < expected_min_size:
                    logger.warning(f"⚠️ SPRINT27-SAFETY: Core universe size {universe_size} is below expected minimum {expected_min_size}")
                    return False
                elif universe_size > expected_max_size:
                    logger.warning(f"⚠️ SPRINT27-SAFETY: Core universe size {universe_size} exceeds expected maximum {expected_max_size}")
                
                return True
            else:
                logger.error("❌ SPRINT27-SAFETY: No tickstock_universe_manager available")
                return False
        except Exception as e:
            logger.error(f"❌ SPRINT27-SAFETY: Error validating core universe: {e}")
            return False
    
    def set_channel_router(self, channel_router):
        """Set the channel router for multi-source integration"""
        self.channel_router = channel_router
        self.channel_router.set_event_processor(self)
        logger.info("✅ SPRINT 107: Channel router connected to EventProcessor")
    
    async def handle_multi_source_data(self, data: Any, source: str) -> EventProcessingResult:
        """
        SPRINT 107: New multi-channel entry point for processing data from multiple sources.
        
        Args:
            data: Incoming data (TickData, OHLCVData, FMVData, or dict)
            source: Source identifier string
            
        Returns:
            EventProcessingResult: Processing result with events and metadata
        """
        start_time = time.time()
        result = EventProcessingResult(ticker=getattr(data, 'ticker', 'unknown'))
        
        try:
            # Step 1: Create source context
            from src.processing.pipeline.source_context_manager import DataSource
            source_type = DataSource.CHANNEL if source.startswith('channel') else DataSource.WEBSOCKET
            context = self.source_context_manager.create_context(data, source_type)
            
            # Step 2: Apply source-specific rules
            if not self.source_rules_engine.apply_rules(data, context):
                result.success = False
                result.warnings.append(f"Data filtered by source rules for {source}")
                context.add_warning("filtered_by_source_rules")
                return result
            
            # Step 3: Route through channel system if available
            if self.channel_router:
                channel_result = await self.channel_router.route_data(data)
                
                # Success should not depend on events being generated
                # Router success means data was processed successfully, even if no events were generated
                if channel_result and channel_result.success:
                    # Process events from channel routing if any were generated
                    if channel_result.events:
                        for event in channel_result.events:
                            # Add source context to event
                            self.source_context_manager.add_event_metadata(event, context)
                            
                            # Coordinate with other sources
                            if self.multi_source_coordinator.coordinate_event(event, context):
                                result.events_processed += 1
                            else:
                                result.warnings.append(f"Event coordination failed for {event.type}")
                    
                    # Always mark as successful if router succeeded, regardless of event generation
                    result.success = True
                    context.add_processing_stage("channel_routing_completed")
                    
                    # Add metadata about event generation
                    events_count = len(channel_result.events) if channel_result.events else 0
                    result.metadata = getattr(result, 'metadata', {})
                    result.metadata.update({
                        'router_success': True,
                        'events_generated': events_count,
                        'channel_used': channel_result.metadata.get('channel', 'unknown') if channel_result.metadata else 'unknown'
                    })
                else:
                    result.success = False
                    error_details = channel_result.errors if channel_result and channel_result.errors else ["Channel routing failed - no result or router reported failure"]
                    result.errors.extend(error_details)
                    context.increment_error_count()
            else:
                # Fallback to direct processing if no channel router
                result.warnings.append("No channel router available, using direct processing")
                direct_result = await self._process_data_directly(data, context)
                result.success = direct_result.success
                result.events_processed = direct_result.events_processed
                result.errors.extend(direct_result.errors)
                result.warnings.extend(direct_result.warnings)
            
            # Step 4: Emit coordinated events
            coordinated_events = self.multi_source_coordinator.get_pending_events(max_events=50)
            for event, coordination_metadata, priority in coordinated_events:
                # Forward to priority manager
                if hasattr(self.market_service, 'priority_manager'):
                    self.market_service.priority_manager.add_event(event)
                    self.stats.events_published += 1
            
            return result
            
        except Exception as e:
            error_msg = f"Error in multi-source data handling: {e}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            result.success = False
            result.errors.append(error_msg)
            return result
        finally:
            result.processing_time_ms = (time.time() - start_time) * 1000
            
            # Performance warning
            if result.processing_time_ms > 500:
                logger.warning(f"⚠️ SLOW MULTI-SOURCE PROCESSING > 500ms: {result.processing_time_ms:.0f}ms")
    
    async def _process_data_directly(self, data: Any, context) -> EventProcessingResult:
        """Direct processing fallback when channel router is not available"""
        result = EventProcessingResult()
        
        try:
            # Convert to TickData if possible
            if hasattr(data, 'ticker') and hasattr(data, 'price'):
                # Process as tick data using existing logic
                tick_result = self.handle_tick(data)
                result.success = tick_result.success
                result.events_processed = tick_result.events_processed
                result.errors = tick_result.errors
                result.warnings = tick_result.warnings
                context.add_processing_stage("direct_tick_processing")
            else:
                result.success = False
                result.errors.append("Unable to process data directly - unsupported format")
                context.increment_error_count()
            
            return result
            
        except Exception as e:
            logger.error(f"Error in direct data processing: {e}", exc_info=True)
            result.success = False
            result.errors.append(str(e))
            context.increment_error_count()
            return result
        
    def handle_tick(self, tick_data: TickData) -> EventProcessingResult:
        """
        Main tick processing entry point.
        PHASE 4: Only handles typed TickData.
        """
        
        start_time = time.time()
        result = EventProcessingResult(ticker=tick_data.ticker if tick_data else 'unknown')
        
        # TRACE: Tick received
        if tick_data and tracer.should_trace(tick_data.ticker):
            tracer.trace(
                ticker=tick_data.ticker,
                component='EventProcessor',
                action='process_start',
                data={
                    'input_count': ensure_int(1),
                    'output_count': ensure_int(0),
                    'duration_ms': 0,
                    'details': {
                        'price': tick_data.price,
                        'volume': getattr(tick_data, 'volume', None),
                        'tick_number': self.stats.ticks_received + 1
                    }
                }
            )

        try:

            # Track tick for activity metrics (NEW)
            if hasattr(self.market_service, 'market_metrics'):
                self.market_service.market_metrics.record_tick()            

            # Track received tick
            self.stats.ticks_received += 1
            
            # Log every 100th tick
            if self.stats.ticks_received % 100 == 0:
                logger.info(f"🔍DIAG-EVENT-PROCESSOR-HANDLE-TICK: Processed {self.stats.ticks_received} ticks, last ticker={tick_data.ticker}")
            
            # Log first few ticks to verify data flow
            if self.stats.ticks_received <= 25:
                logger.info(f"📥DIAG-EVENT-PROCESSOR-CONFIRMATION: Tick #{self.stats.ticks_received}: {tick_data.ticker} @ ${tick_data.price}")
            
            # Step 1: Validate TickData
            if not isinstance(tick_data, TickData):
                result.success = False
                result.errors.append(f"Invalid tick data type: {type(tick_data)}")
                return result
            
            # Step 2: Process tick through TickProcessor for validation/enrichment
            tick_result = self.tick_processor.process_tick(tick_data, None)  # Let processor handle last_event_time if needed
            
            if not tick_result.success:
                result.success = False
                result.errors.extend(tick_result.errors)
                result.warnings.extend(tick_result.warnings)
                self.stats.errors += 1
                return result
            
            # Step 3: Process the validated and enriched tick
            processing_result = self._process_tick_event(tick_result.processed_tick)
            
            # TRACE: After event processing
            if tracer.should_trace(tick_data.ticker):
                tracer.trace(
                    ticker=tick_data.ticker,
                    component='EventProcessor',
                    action='process_complete',
                    data={
                        'input_count': ensure_int(1),
                        'output_count': ensure_int(processing_result.events_processed),
                        'duration_ms': (time.time() - start_time) * 1000,
                        'details': {
                            'success': processing_result.success,
                            'errors': len(processing_result.errors)
                        }
                    }
                )

            #if processing_result.success and processing_result.events_processed > 0:
            #    logger.debug(f"🔍DIAG-EVENT-PROCESSOR: Processed {processing_result.events_processed} events for {tick_data.ticker}")

            # Update result based on processing outcome
            result.success = processing_result.success
            result.events_processed = processing_result.events_processed
            result.errors.extend(processing_result.errors)
            result.warnings.extend(processing_result.warnings)
            
            if result.success:
                self.stats.ticks_processed += 1
                if processing_result.events_processed > 0:
                    self.stats.events_detected += processing_result.events_processed
            else:
                self.stats.errors += 1
            
            # Periodic stats logging
            if self.stats.should_log():
                self.stats.log_stats(logger)
            
            return result
            
        except Exception as e:
            error_msg = f"Error in EventProcessor.handle_tick: {e}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            result.success = False
            result.errors.append(error_msg)
            self.stats.errors += 1

            # TRACE: Error
            if tick_data and tracer.should_trace(tick_data.ticker):
                tracer.trace(
                    ticker=tick_data.ticker,
                    component='EventProcessor',
                    action='error',
                    data={
                        'input_count': ensure_int(1),
                        'output_count': ensure_int(0),
                        'duration_ms': (time.time() - start_time) * 1000,
                        'error': str(e),
                        'details': {
                            'error_type': type(e).__name__
                        }
                    }
                )

            return result
        finally:
            result.processing_time_ms = (time.time() - start_time) * 1000
            
            # Performance warning
            if result.processing_time_ms > 300:
                logger.warning(f"⚠️DIAG-EVENT-PROCESSOR: SLOW PROCESSING > 300 ms: {tick_data.ticker} took {result.processing_time_ms:.0f}ms")

    def _process_tick_event(self, queue_data: TickData) -> EventProcessingResult:
        """Core tick processing logic - Pure typed event handling."""
        start_time = time.time()
        result = EventProcessingResult(ticker=queue_data.ticker)
        
        try:
            ticker = queue_data.ticker
            price = queue_data.price
            
            # Check if ticker should be processed
            should_process_core = self._should_process_for_tickstock_universe(ticker)
            
            # ADD TRACE: Track core universe processing decision
            if tracer.should_trace(ticker):
                tracer.trace(
                    ticker=ticker,
                    component='EventProcessor',
                    action='universe_check',
                    data={
                        'input_count': ensure_int(1),
                        'output_count': ensure_int(1 if should_process_core else 0),
                        'duration_ms': 0,
                        'details': {
                            'is_core_universe': should_process_core,
                            'will_process': should_process_core
                        }
                    }
                )

            if not should_process_core:
                # Not in core universe - skip (not subscribed)
                result.warnings.append(f"Ticker {ticker} not in core universe - not subscribed")
                return result
            
            # Track universe hit
            self.stats.core_universe_hits += 1

            # Record activity event
            self.market_metrics.record_tick(time.time())

            # Get or create StockData for ticker
            if ticker not in self.market_service.stock_details:
                self._initialize_ticker_state(ticker, price, queue_data.market_status, 
                                            queue_data.market_open_price)
            
            stock_details = self.market_service.stock_details[ticker]
            
            # PHASE 4: Ensure StockData type (single check)
            if not isinstance(stock_details, StockData):
                stock_details = StockData(ticker=ticker, last_price=price)
                self.market_service.stock_details[ticker] = stock_details
            
            # Update last event time
            stock_details.last_update = time.time()

            # Process tick in buy/sell tracker
            self.buysell_market_tracker.process_tick(
                ticker=ticker,
                price=price,
                volume=getattr(queue_data, 'effective_volume', 0),
                timestamp=time.time()
            )

            # Detect ALL events
            detection_result = self.event_detector.detect_events(ticker, queue_data, stock_details)
            
            if detection_result.success and detection_result.events_detected:
                # Log event types
                event_types = [event.type for event in detection_result.events_detected]
                
                #logger.debug(f"🔍DIAG-EVENT-PROCESSOR: Detection for {ticker} - success={detection_result.success}, "
                #    f"events={len(detection_result.events_detected)} Event types detected: {event_types}")
                
                # Process each detected event
                for event in detection_result.events_detected:
                    self._process_detected_event(ticker, queue_data, event)
                
                result.events_processed = len(detection_result.events_detected)
            else:
                result.errors.extend(detection_result.errors)
                result.warnings.extend(detection_result.warnings)

            # Update stock details with latest tick data
            self._update_stock_details_typed(ticker, queue_data, stock_details)
            
            # Mark ticker as changed
            self.market_service.changed_tickers.add(ticker)
            
            return result
            
        except Exception as e:
            error_msg = f"Error processing tick event for {queue_data.ticker}: {e}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            result.success = False
            result.errors.append(error_msg)
            
            # TRACE: Error
            if tracer.should_trace(queue_data.ticker):
                tracer.trace(
                    ticker=queue_data.ticker,
                    component='EventProcessor',
                    action='process_tick_error',
                    data={
                        'input_count': ensure_int(1),
                        'output_count': ensure_int(0),
                        'duration_ms': (time.time() - start_time) * 1000,
                        'error': str(e),
                        'details': {
                            'error_type': type(e).__name__,
                            'method': '_process_tick_event'
                        }
                    }
                )
            
            return result
        
    def _update_stock_details_typed(self, ticker: str, tick_data: TickData, stock_data: StockData):
        """Update StockData object with latest tick information."""
        try:
            # Update basic fields
            stock_data.last_price = tick_data.price
            stock_data.last_update = normalize_timestamp(tick_data.timestamp)
            stock_data.market_status = tick_data.market_status
            
            # Update VWAP if available
            if hasattr(tick_data, 'effective_vwap') and tick_data.effective_vwap:
                stock_data.vwap = tick_data.effective_vwap
            elif hasattr(tick_data, 'vwap') and tick_data.vwap:
                stock_data.vwap = tick_data.vwap
            
            # Update volume
            if hasattr(tick_data, 'effective_volume') and tick_data.effective_volume:
                stock_data.volume = tick_data.effective_volume
            elif hasattr(tick_data, 'volume') and tick_data.volume:
                stock_data.volume = tick_data.volume
            
            # Update session highs/lows if needed
            if hasattr(tick_data, 'day_high') and tick_data.day_high:
                if stock_data.session_high is None or tick_data.day_high > stock_data.session_high:
                    stock_data.session_high = tick_data.day_high
                    
            if hasattr(tick_data, 'day_low') and tick_data.day_low:
                if stock_data.session_low is None or tick_data.day_low < stock_data.session_low:
                    stock_data.session_low = tick_data.day_low
            
            # Update price tracking
            if stock_data.session_high is None or tick_data.price > stock_data.session_high:
                stock_data.session_high = tick_data.price
            if stock_data.session_low is None or tick_data.price < stock_data.session_low:
                stock_data.session_low = tick_data.price
            
            # Update percent change
            if hasattr(tick_data, 'market_open_price') and tick_data.market_open_price:
                stock_data.percent_change = ((tick_data.price - tick_data.market_open_price) / tick_data.market_open_price) * 100
            
            # Update VWAP divergence
            if stock_data.vwap and stock_data.vwap > 0:
                stock_data.vwap_divergence = ((tick_data.price - stock_data.vwap) / stock_data.vwap) * 100
                stock_data.vwap_position = 'above' if tick_data.price > stock_data.vwap else 'below'
            
        except Exception as e:
            logger.error(f"Error updating StockData for {ticker}: {e}", exc_info=True)
    

    
    def _process_detected_event(self, ticker: str, tick_data: TickData, event: BaseEvent):
        """Process a single detected event - PHASE 4: Only typed events."""
        try:
            # PHASE 4: Direct typed access
            event_type = event.type
            current_time = event.time
            
            #logger.info(f"🔍 DIAG-EVENT_PROCESSOR: PROCESS_EVENT: Processing {event_type} for {ticker}")

            # TRACE: Event processing start
            if tracer.should_trace(ticker):
                tracer.trace(
                    ticker=ticker,
                    component='EventProcessor',
                    action='event_processing',
                    data={
                        'input_count': ensure_int(1),
                        'output_count': ensure_int(1),
                        'duration_ms': 0,
                        'details': {
                            'event_type': event_type,
                            'event_class': type(event).__name__
                        }
                    }
                )


            # QUEUE ROUTE The method routes events based on type
            if event_type in ('high', 'low'):
                self._process_high_low_event(ticker, tick_data, event, event_type, current_time)
                self.stats.high_low_events += 1
            elif event_type == 'trend':
                self._process_trend_event(ticker, tick_data, event)
                self.stats.trends_processed += 1
            elif event_type == 'surge':
                self._process_surge_event(ticker, tick_data, event)
                self.stats.surges_processed += 1
            else:
                logger.warning(f"DIAG-EVENT-PROCESSOR: Unknown event type: {event_type}")
                return
                
            self.stats.events_published += 1



        except Exception as e:
            logger.error(f"Error processing detected event for {ticker}: {e}", exc_info=True)
            self.stats.errors += 1

            # TRACE: Error
            # Standardized error trace
            if tracer.should_trace(ticker):
                tracer.trace(
                    ticker=ticker,
                    component='EventProcessor',
                    action='process_event_error',
                    data={
                        'input_count': ensure_int(1),
                        'output_count': ensure_int(0),
                        'duration_ms': 0,  # No start_time in this method
                        'error': str(e),
                        'details': {
                            'error_type': type(e).__name__,
                            'event_type': event_type if 'event_type' in locals() else 'unknown',
                            'method': '_process_detected_event'
                        }
                    }
                )

    

    def _process_high_low_event(self, ticker: str, tick_data: TickData, event: HighLowEvent, 
                        event_type: str, current_time: float):
        """Process a high/low event - PHASE 4: Only typed events."""
        try:
            stock_details = self.market_service.stock_details.get(ticker)
            if not stock_details:
                logger.error(f"❌DIAG-EVENT-PROCESSOR: No stock_details found for {ticker}")
                return
            
            # PHASE 4: Always StockData
            if not isinstance(stock_details, StockData):
                logger.error(f"❌DIAG-EVENT-PROCESSOR: Invalid stock_details type: {type(stock_details)}")
                return
            
            # PHASE 4: Direct typed access
            price = event.price
            volume = event.volume or tick_data.effective_volume
            count = event.count
            percent_change = event.percent_change
            vwap_distance = event.vwap_divergence
            is_initial = event.is_initial
            
            # Add event to StockData collections
            stock_details.add_event(event)
            
            # Normalize event type
            if event_type in ('high', 'session_high'):
                event_type = 'high'
                event_label = 'high'
            elif event_type in ('low', 'session_low'):
                event_type = 'low'
                event_label = 'low'
            else:
                logger.debug(f"DIAG-EVENT-PROCESSOR: Unknown event type: {event_type}")
                return

            # Update momentum tracking
            window_high_count, window_low_count = self.market_metrics.update_per_ticker_momentum(
                ticker, event_type, tick_data.timestamp
            )
            
            # FIX: Record events to session accumulation manager
            if event_type == "high":
                # Update count tracking
                stock_details.event_counts.highs += 1
                stock_details.highlow_bar.high_count += 1
                count = stock_details.event_counts.highs
                
                self.market_metrics.update_high_low_tracking(ticker, high_count_delta=1)
                
                # RECORD TO ACCUMULATION MANAGER
                if self.session_accumulation_manager:
                    success = self.session_accumulation_manager.record_high_event(ticker)
                    if success:
                        logger.debug(f"📊 Recorded HIGH event for {ticker} to accumulation manager")
                    else:
                        logger.error(f"❌ Failed to record HIGH event for {ticker} to accumulation manager")
                
            elif event_type == "low":
                # Update count tracking
                stock_details.event_counts.lows += 1
                stock_details.highlow_bar.low_count += 1
                count = stock_details.event_counts.lows
                
                self.market_metrics.update_high_low_tracking(ticker, low_count_delta=1)
                
                # RECORD TO ACCUMULATION MANAGER
                if self.session_accumulation_manager:
                    success = self.session_accumulation_manager.record_low_event(ticker)
                    if success:
                        logger.debug(f"📊 Recorded LOW event for {ticker} to accumulation manager")
                    else:
                        logger.error(f"❌ Failed to record LOW event for {ticker} to accumulation manager")
            
            # Get the eastern timezone
            eastern_tz = pytz.timezone('US/Eastern')

            # Convert timestamp to datetime with timezone
            if tick_data.timestamp:
                timestamp_float = normalize_timestamp(tick_data.timestamp)  
                dt = datetime.fromtimestamp(timestamp_float)
                dt_eastern = eastern_tz.localize(dt) if dt.tzinfo is None else dt.astimezone(eastern_tz)
                time_str = dt_eastern.strftime("%H:%M:%S")
            else:
                time_str = ""
            
            # PHASE 4: Pass typed event directly to priority manager
            if hasattr(self.market_service, 'priority_manager'):
                queue_result = self.market_service.priority_manager.add_event(event)

                # TRACE: High/Low event queued
                if tracer.should_trace(ticker):
                    tracer.trace(
                        ticker=ticker,
                        component='EventProcessor',
                        action='event_queued',
                        data={
                            'input_count': ensure_int(1),
                            'output_count': ensure_int(1 if queue_result else 0),
                            'duration_ms': 0,
                            'details': {
                                'event_type': 'high' if event_type == 'high' else 'low' if event_type == 'low' else event_type,
                                'event_label': event_label,
                                'queue_result': queue_result,
                                'price': price,
                                'count': count,
                                'percent_change': percent_change,
                                'vwap_divergence': vwap_distance,
                                'event_id': getattr(event, 'event_id', None)
                            }
                        }
                    )
                
                # Log first few for debugging
                if self.stats.high_low_events <= 5:
                    logger.debug(f"📊 DIAG-EVENT-PROCESSOR: High/Low event queued - {ticker} {event_label} @ ${price:.2f} count={count} - Queue result: {queue_result}")
            else:
                logger.error("❌DIAG-EVENT-PROCESSOR: NO PRIORITY MANAGER AVAILABLE!")
                
        except Exception as e:
            logger.error(f"❌ Error processing {event_type} event for {ticker}: {e}", exc_info=True)

            # Standardized error trace
            if tracer.should_trace(ticker):
                tracer.trace(
                    ticker=ticker,
                    component='EventProcessor',
                    action='process_highlow_error',
                    data={
                        'input_count': ensure_int(1),
                        'output_count': ensure_int(0),
                        'duration_ms': 0,
                        'error': str(e),
                        'details': {
                            'error_type': type(e).__name__,
                            'event_type': 'high' if event_type == 'high' else 'low' if event_type == 'low' else event_type,
                            'method': '_process_high_low_event'
                        }
                    }
                )

    def _process_trend_event(self, ticker: str, tick_data: TickData, event: TrendEvent):
        """Process a trend event - PHASE 4: Only typed events."""
        try:
            #logger.debug(f"🔍DIAG-EVENT-PROCESSOR: Processing trend event for {ticker}")
            
            stock_details = self.market_service.stock_details.get(ticker)
            
            # Always StockData
            if not isinstance(stock_details, StockData):
                logger.error(f"❌DIAG-EVENT-PROCESSOR: Invalid stock_details type: {type(stock_details)}")
                return

            # Just update tracking fields for compatibility
            stock_details.trend_direction = event.direction
            stock_details.trend_strength = event.trend_strength
            stock_details.trend_score = event.trend_score
            stock_details.trend_count = event.count
            stock_details.trend_count_up = event.count_up
            stock_details.trend_count_down = event.count_down
            stock_details.percent_change = event.percent_change
            
            # Add to priority manager - pass typed event
            if hasattr(self.market_service, 'priority_manager'):
                queue_result = self.market_service.priority_manager.add_event(event)
                
                # TRACE: Trend event queued
                if tracer.should_trace(ticker):
                    tracer.trace(
                        ticker=ticker,
                        component='EventProcessor',
                        action='event_queued',
                        data={
                            'input_count': ensure_int(1),
                            'output_count': ensure_int(1 if queue_result else 0),
                            'duration_ms': 0,
                            'details': {
                                'event_type': 'trend',
                                'event_label': 'trend',
                                'queue_result': queue_result,
                                'direction': event.direction,
                                'strength': event.trend_strength,
                                'score': event.trend_score,
                                'count': event.count,
                                'event_id': getattr(event, 'event_id', None)  
                            }
                        }
                    )
                
                # Log first few for debugging
                if self.stats.trends_processed <= 5:
                    logger.debug(f"📈 DIAG-EVENT-PROCESSOR: Trend event queued - {ticker} {event.direction} strength={event.trend_strength} score={event.trend_score:.2f} - Queue result: {queue_result}")
            else:
                logger.error("❌DIAG-EVENT-PROCESSOR: NO PRIORITY MANAGER AVAILABLE!")
            
            # Update stats
            self.stats.trends_processed += 1
            #logger.debug(f"🔍 DIAG-EVENT-PROCESSOR: Total trends processed: {self.stats.trends_processed}")
                        
        except Exception as e:
            logger.error(f"Error processing trend event for {ticker}: {e}", exc_info=True)
            self.stats.errors += 1
            
            # Standardized error trace
            if tracer.should_trace(ticker):
                tracer.trace(
                    ticker=ticker,
                    component='EventProcessor',
                    action='process_trend_error',
                    data={
                        'input_count': ensure_int(1),
                        'output_count': ensure_int(0),
                        'duration_ms': 0,
                        'error': str(e),
                        'details': {
                            'error_type': type(e).__name__,
                            'event_type': 'trend',
                            'method': '_process_trend_event'
                        }
                    }
                )


    def _process_surge_event(self, ticker: str, tick_data: TickData, event: SurgeEvent):
        """Process a surge event - PHASE 4: Only typed events."""
        try:
            #logger.debug(f"🔍DIAG-EVENT-PROCESSOR: Processing surge event for {ticker}")
            
            stock_details = self.market_service.stock_details.get(ticker)
            
            # PHASE 4: Always StockData
            if not isinstance(stock_details, StockData):
                logger.error(f"❌DIAG-EVENT-PROCESSOR: Invalid stock_details type: {type(stock_details)}")
                return
            
            # Add to priority manager - pass typed event
            if hasattr(self.market_service, 'priority_manager'):
                queue_result = self.market_service.priority_manager.add_event(event)
                
                # TRACE: Surge event queued
                if tracer.should_trace(ticker):
                    tracer.trace(
                        ticker=ticker,
                        component='EventProcessor',
                        action='event_queued',
                        data={
                            'input_count': 1,
                            'output_count': 1 if queue_result else 0,
                            'duration_ms': 0,
                            'details': {
                                'event_type': 'surge',
                                'event_label': 'surge',
                                'queue_result': queue_result,
                                'direction': event.direction,
                                'magnitude': event.surge_magnitude,
                                'score': event.surge_score,
                                'event_id': getattr(event, 'event_id', None)  
                            }
                        }
                    )
                
                # Log first few for debugging
                if self.stats.surges_processed <= 5:
                    logger.info(f"🚀 DIAG-EVENT-PROCESSOR: Surge event queued - {ticker} {event.direction} magnitude={event.surge_magnitude:.1f}% score={event.surge_score:.1f} - Queue result: {queue_result}")
            else:
                logger.error("❌DIAG-EVENT-PROCESSOR: NO PRIORITY MANAGER AVAILABLE!")
            
            # Update stats
            self.stats.surges_processed += 1
            #logger.debug(f"🔍 DIAG-EVENT-PROCESSOR: Total surges processed: {self.stats.surges_processed}")
            
        except Exception as e:
            logger.error(f"Error processing surge event for {ticker}: {e}", exc_info=True)
            self.stats.errors += 1
            
            # Standardized error trace
            if tracer.should_trace(ticker):
                tracer.trace(
                    ticker=ticker,
                    component='EventProcessor',
                    action='process_surge_error',
                    data={
                        'input_count': ensure_int(1),
                        'output_count': ensure_int(0),
                        'duration_ms': 0,
                        'error': str(e),
                        'details': {
                            'error_type': type(e).__name__,
                            'event_type': 'surge',
                            'method': '_process_surge_event'
                        }
                    }
                )


    def _initialize_ticker_state(self, ticker: str, price: float, market_status: str, market_open_price: Optional[float]):
        """Initialize new ticker state - PHASE 4: Always creates StockData objects."""
        try:
            # PHASE 4: Always create StockData
            stock_data = StockData(
                ticker=ticker,
                last_price=price,
                market_status=market_status,
                session_high=price,
                session_low=price,
                last_update=time.time()
            )
            
            # Calculate initial percent change if we have market open price
            if market_open_price and market_open_price > 0:
                stock_data.percent_change = ((price - market_open_price) / market_open_price) * 100
            
            self.market_service.stock_details[ticker] = stock_data
            
            # Initialize detector state
            if market_status == "REGULAR" and market_open_price is not None:
                self.highlow_detector.initialize_highlow_event_data(
                    ticker=ticker,
                    session_high=market_open_price,
                    session_low=market_open_price,
                    market_status=market_status,
                    last_price=price,
                    market_open_price=market_open_price
                )
            else:
                self.highlow_detector.initialize_highlow_event_data(
                    ticker=ticker,
                    session_high=price,
                    session_low=price,
                    market_status=market_status,
                    last_price=price,
                    market_open_price=market_open_price
                )
            
        except Exception as e:
            logger.error(f"❌ Error initializing ticker state for {ticker}: {e}", exc_info=True)
    
    def _should_process_for_tickstock_universe(self, ticker: str) -> bool:
        """Check if ticker should be processed for TickStock Core Universe."""
        try:
            return self.market_service.tickstock_universe_manager.is_stock_in_core_universe(ticker)
        except Exception as e:
            self.universe_logger.error(f"❌ Error checking TickStock Core Universe membership for {ticker}: {e}")
            return False
    
        
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report including component stats."""
        try:
            current_time = time.time()
            
            # Check data flow health
            self.stats.check_health(logger)
            
            success_rate = 0
            if self.stats.ticks_received > 0:
                success_rate = (self.stats.ticks_processed / self.stats.ticks_received) * 100
            
            return {
                'data_flow_stats': {
                    'ticks_received': self.stats.ticks_received,
                    'ticks_processed': self.stats.ticks_processed,
                    'events_detected': self.stats.events_detected,
                    'events_published': self.stats.events_published,
                    'core_universe_hits': self.stats.core_universe_hits,
                    'errors': self.stats.errors,
                    'success_rate_percent': round(success_rate, 2)
                },
                'component_stats': {
                    'tick_processor': self.tick_processor.get_statistics() if hasattr(self.tick_processor, 'get_statistics') else {},
                    'event_detector': self.event_detector.get_statistics() if hasattr(self.event_detector, 'get_statistics') else {}
                },
                'timestamp': current_time
            }
            
        except Exception as e:
            logger.error(f"❌ Error generating performance report: {e}")
            return {'error': str(e)}
    

    def _ensure_stock_details_complete(self, ticker: str, stock_details: StockData):
        """PHASE 4: Removed - StockData is always complete by design."""
        pass

