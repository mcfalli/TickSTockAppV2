"""
Priority and Queue Management
Handles event prioritization and queue operations.
SPRINT 54: Integration with cache-based priority stocks
"""
from collections import defaultdict, deque
from typing import List, Dict, Union, Tuple, Any, Optional, Set
import queue
import threading
import time
import pybreaker
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import pytz

from src.core.domain.events.base import BaseEvent
from src.core.domain.events.highlow import HighLowEvent
from src.core.domain.events.trend import TrendEvent
from src.core.domain.events.surge import SurgeEvent
from src.core.domain.events.control import ControlEvent
from src.processing.queues.queue import TypedEventQueue, QueuedEvent
from src.core.domain.market.tick import TickData

from src.monitoring.tracer import tracer, TraceLevel, normalize_event_type, ensure_int
from config.logging_config import get_domain_logger, LogDomain

logger = get_domain_logger(LogDomain.CORE, 'priority_manager')


@dataclass
class QueueDiagnostics:
    """Centralized queue diagnostics tracking."""
    total_attempts: int = 0
    queue_full_drops: int = 0
    age_expired_drops: int = 0
    priority_drops: int = 0
    circuit_breaker_drops: int = 0
    invalid_type_drops: int = 0
    max_queue_depth: int = 0
    queue_depth_samples: deque = field(default_factory=lambda: deque(maxlen=1000))
    event_ages_ms: deque = field(default_factory=lambda: deque(maxlen=1000))
    drop_reasons: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    
    def record_drop(self, reason: str):
        """Record a drop event with reason."""
        self.drop_reasons[reason] += 1
        
        # Update specific counters
        if reason == 'queue_full':
            self.queue_full_drops += 1
        elif reason == 'age_expired':
            self.age_expired_drops += 1
        elif reason == 'low_priority':
            self.priority_drops += 1
        elif reason == 'circuit_breaker':
            self.circuit_breaker_drops += 1
        elif reason == 'invalid_type':
            self.invalid_type_drops += 1
    
    def record_queue_depth(self, depth: int):
        """Record queue depth sample."""
        if depth > self.max_queue_depth:
            self.max_queue_depth = depth
        
        # Sample periodically
        if self.total_attempts % 100 == 0:
            self.queue_depth_samples.append(depth)
    
    def record_event_age(self, age_ms: float):
        """Record event age."""
        self.event_ages_ms.append(age_ms)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get diagnostic statistics."""
        avg_depth = sum(self.queue_depth_samples) / len(self.queue_depth_samples) if self.queue_depth_samples else 0
        avg_age = sum(self.event_ages_ms) / len(self.event_ages_ms) if self.event_ages_ms else 0
        
        total_drops = (self.queue_full_drops + self.priority_drops + 
                      self.circuit_breaker_drops + self.age_expired_drops + 
                      self.invalid_type_drops)
        
        return {
            'max_depth_seen': self.max_queue_depth,
            'avg_queue_depth': round(avg_depth, 1),
            'avg_event_age_ms': round(avg_age, 1),
            'total_add_attempts': self.total_attempts,
            'drops': {
                'queue_full': self.queue_full_drops,
                'priority': self.priority_drops,
                'circuit_breaker': self.circuit_breaker_drops,
                'age_expired': self.age_expired_drops,
                'invalid_type': self.invalid_type_drops,
                'total': total_drops
            },
            'drop_rate_percent': round((total_drops / self.total_attempts * 100) 
                                    if self.total_attempts > 0 else 0, 2),
            'drop_reasons': dict(self.drop_reasons)
        }


class DataFlowStats:
    """Track data flow through the priority manager."""
    def __init__(self):
        self.events_added = 0
        self.events_collected = 0
        self.events_dropped = 0
        self.circuit_trips = 0
        self.high_priority_events = 0
        self.event_type_counts = defaultdict(int)
        self.last_log_time = time.time()
        self.log_interval = 30  # seconds
        
    def should_log(self):
        return time.time() - self.last_log_time >= self.log_interval
        
    def log_stats(self):
        efficiency = (self.events_collected / self.events_added * 100) if self.events_added > 0 else 0
        logger.debug(f"📊 PRIORITY QUEUE FLOW: In:{self.events_added} → Out:{self.events_collected} → "
                    f"Dropped:{self.events_dropped} | Efficiency:{efficiency:.1f}% | "
                    f"HighPri:{self.high_priority_events} CircuitTrips:{self.circuit_trips}")
        
        # Log event type breakdown
        if self.event_type_counts:
            type_summary = ", ".join([f"{k}:{v}" for k, v in self.event_type_counts.items()])
            logger.debug(f"📊 Event Types: {type_summary}")
            
        self.last_log_time = time.time()


class PriorityManager:
    """
    Manages event prioritization and queue operations.
    SPRINT 54: Cache-based priority stock integration
    """
    
    # Configuration constants
    DEFAULT_EVENT_BATCH_SIZE = 1000
    DEFAULT_MAX_QUEUE_SIZE = 100000
    DEFAULT_OVERFLOW_THRESHOLD = 0.98
    DEFAULT_MAX_EVENT_AGE_MS = 120000
    
    # Event type priorities (lower number = higher priority)
    EVENT_PRIORITIES = {
        'control': 1,      # System control events
        'tick': 1,         # Raw tick data
        'high': 2,         # High events
        'low': 2,          # Low events
        'surge': 3,        # Market surge events
        'trend': 3,        # Trend events
        'status': 4        # Status updates
    }
    
    # Display event types for UI
    DISPLAY_EVENT_TYPES = [HighLowEvent, TrendEvent, SurgeEvent]

    def __init__(self, config: Dict[str, Any], cache_control=None):
        """
        Initialize priority manager with cache-based priority configuration.
        
        Args:
            config: Configuration dictionary
            cache_control: Optional CacheControl instance (will be lazily loaded if not provided)
        """
        init_start_time = time.time()
        
        self.config = config
        self.cache_control = cache_control
        self._cache_initialized = False
        self._priority_cache_refresh_time = 0
        self._priority_cache_refresh_interval = 300  # Refresh every 5 minutes
        
        # Configuration with defaults
        self.circuit_breaker_fail_max = config.get('CIRCUIT_BREAKER_FAIL_MAX', 5)
        self.circuit_breaker_timeout = config.get('CIRCUIT_BREAKER_TIMEOUT', 30)
        self.max_queue_size = config.get('MAX_QUEUE_SIZE', self.DEFAULT_MAX_QUEUE_SIZE)
        self.overflow_drop_threshold = config.get('QUEUE_OVERFLOW_DROP_THRESHOLD', self.DEFAULT_OVERFLOW_THRESHOLD)
        self.batch_size = config.get('EVENT_BATCH_SIZE', self.DEFAULT_EVENT_BATCH_SIZE)
        self.max_event_age_ms = config.get('MAX_EVENT_AGE_MS', self.DEFAULT_MAX_EVENT_AGE_MS)
        
        # Validate configuration
        self._validate_configuration()
        
        # SPRINT 54: Cache-based priority ticker sets
        # Initialize with empty sets - will be populated from cache
        self.priority_tickers = set()  # Will be populated from cache 'top_priority'
        self.important_tickers = set()  # Will be populated from cache 'secondary_priority'
        self._priority_ticker_set = set()  # Fast lookup combining both sets
        
        # Market open tickers remain hardcoded (special ETFs for market open)
        self.market_open_tickers = {'SPY', 'QQQ', 'IWM', 'DIA'}
        
        # Attempt to initialize cache if provided
        if self.cache_control:
            self._initialize_priority_cache()
        
        # Log configuration
        logger.info(f"🔧 PriorityManager initialized: "
                   f"max_size={self.max_queue_size}, "
                   f"overflow_threshold={self.overflow_drop_threshold}, "
                   f"batch_size={self.batch_size}, "
                   f"max_age={self.max_event_age_ms}ms, "
                   f"cache_based_priority={self._cache_initialized}")

        # Initialize typed event queue
        self.event_queue = TypedEventQueue(
            maxsize=self.max_queue_size,
            use_priority=True
        )
        
        # Thread safety
        self.sequence_counter = 0
        self.sequence_lock = threading.Lock()
        self._shutdown = False
        self._shutdown_lock = threading.Lock()
        
        # Circuit breaker for queue protection
        self.queue_breaker = pybreaker.CircuitBreaker(
            fail_max=self.circuit_breaker_fail_max,
            reset_timeout=self.circuit_breaker_timeout,
            name="PriorityQueueBreaker"
        )
        
        # Statistics tracking
        self.flow_stats = DataFlowStats()
        self.diagnostics = QueueDiagnostics()
        
        self.drops_by_type = defaultdict(lambda: defaultdict(int))

        # Queue monitoring
        self.queue_high_water_mark = 0
        self.last_overflow_time = 0
        self.overflow_events = deque(maxlen=100)  # Track recent overflows
        
        # Trace initialization
        self._trace_initialization(init_start_time)
    
    def _initialize_priority_cache(self):
        """Initialize priority ticker sets from cache."""
        try:
            if not self.cache_control:
                logger.warning("Cache control not available for priority initialization")
                return
            
            # Get top priority tickers
            top_priority_tickers = self.cache_control.get_priority_tickers('TOP')
            if top_priority_tickers:
                self.priority_tickers = set(top_priority_tickers)
                logger.info(f"Loaded {len(self.priority_tickers)} top priority tickers from cache")
            
            # Get secondary priority tickers
            secondary_priority_tickers = self.cache_control.get_priority_tickers('SECONDARY')
            if secondary_priority_tickers:
                self.important_tickers = set(secondary_priority_tickers)
                logger.info(f"Loaded {len(self.important_tickers)} secondary priority tickers from cache")
            
            # Build combined fast lookup set
            self._priority_ticker_set = self.cache_control.get_processing_priority_set()
            if not self._priority_ticker_set:
                # Fallback to building it ourselves
                self._priority_ticker_set = self.priority_tickers | self.important_tickers
            
            # Get priority stats for logging
            priority_stats = self.cache_control.get_priority_stats()
            logger.info(f"Priority cache stats: {priority_stats}")
            
            self._cache_initialized = True
            self._priority_cache_refresh_time = time.time()
            
        except Exception as e:
            logger.error(f"Error initializing priority cache: {e}", exc_info=True)
            self._cache_initialized = False
    
    def _refresh_priority_cache_if_needed(self):
        """Refresh priority cache if stale."""
        if not self.cache_control:
            return
        
        current_time = time.time()
        if current_time - self._priority_cache_refresh_time > self._priority_cache_refresh_interval:
            self._initialize_priority_cache()
    
    '''
    def set_cache_control(self, cache_control):
        """Set cache control instance (for lazy initialization)."""
        self.cache_control = cache_control
        self._initialize_priority_cache()
    '''
    def _validate_configuration(self):
        """Validate configuration parameters."""
        if self.max_queue_size <= 0:
            raise ValueError(f"Invalid max_queue_size: {self.max_queue_size}")
        
        if not 0 < self.overflow_drop_threshold <= 1:
            raise ValueError(f"Invalid overflow_drop_threshold: {self.overflow_drop_threshold}")
        
        if self.batch_size <= 0:
            raise ValueError(f"Invalid batch_size: {self.batch_size}")
        
        if self.max_event_age_ms <= 0:
            raise ValueError(f"Invalid max_event_age_ms: {self.max_event_age_ms}")
    
    def _trace_initialization(self, start_time: float):
        """Trace initialization completion."""
        if tracer.should_trace('SYSTEM'):
            # Get priority counts (may be 0 if cache not ready yet)
            priority_count = len(self.priority_tickers) if self.priority_tickers else 0
            important_count = len(self.important_tickers) if self.important_tickers else 0
            
            tracer.trace(
                ticker='SYSTEM',
                component='PriorityManager',
                action='initialization_complete',
                data={
                    'timestamp': time.time(),
                    'input_count': ensure_int(0),
                    'output_count': ensure_int(0),
                    'duration_ms': (time.time() - start_time) * 1000,
                    'details': {
                        'max_queue_size': self.max_queue_size,
                        'overflow_threshold': self.overflow_drop_threshold,
                        'batch_size': self.batch_size,
                        'max_event_age_ms': self.max_event_age_ms,
                        'priority_tickers': priority_count,
                        'important_tickers': important_count,
                        'cache_initialized': self._cache_initialized,
                        'cache_source': 'database' if self._cache_initialized else 'none'
                    }
                }
            )
    
    def _determine_priority_safe(self, ticker: str, event_type: str) -> int:
        """
        Safely determine event priority with cache-based priority checks.
        SPRINT 54: Now uses cache methods for priority determination.
        """
        try:
            # Refresh cache if needed
            self._refresh_priority_cache_if_needed()
            
            # Base priority from event type
            base_priority = self.EVENT_PRIORITIES.get(event_type, 4)
            
            # Check market open period for special handling
            if self._is_market_open_period():
                if ticker in self.market_open_tickers:
                    return 1  # Highest priority for market ETFs
            
            # SPRINT 54: Use cache-based priority checking
            if self.cache_control and self._cache_initialized:
                priority_info = self.cache_control.is_priority_stock(ticker)
                
                if priority_info.get('is_priority'):
                    priority_level = priority_info.get('priority_level', 'UNKNOWN')
                    
                    if priority_level == 'TOP':
                        return 1  # Highest priority
                    elif priority_level == 'SECONDARY':
                        return min(2, base_priority)  # Secondary priority
                    else:
                        # Unknown priority level but still marked as priority
                        return min(3, base_priority)
            else:
                # Fallback to in-memory sets if cache not available
                if ticker in self.priority_tickers:
                    return 1
                elif ticker in self.important_tickers:
                    return min(2, base_priority)
            
            return base_priority
            
        except Exception as e:
            logger.error(f"Error determining priority for {ticker}: {e}")
            return 4  # Default to lowest priority on error
    
    def _should_drop_for_overflow(self, queue_size: int, priority: int, event_type: str, ticker: str = None) -> bool:
        """
        Determine if event should be dropped due to overflow conditions.
        SPRINT 54: Integrates cache throttle level logic for smart dropping.
        """
        drop_threshold = int(self.max_queue_size * self.overflow_drop_threshold)
        
        # Never drop control or surge events
        if event_type in ('control', 'surge'):
            return False
        
        # Calculate throttle level based on queue pressure
        throttle_level = 0
        queue_utilization = queue_size / self.max_queue_size
        
        if queue_utilization > 0.98:
            throttle_level = 3  # Severe
        elif queue_utilization > 0.95:
            throttle_level = 2  # Moderate  
        elif queue_utilization > 0.90:
            throttle_level = 1  # Mild
        
        # Use cache's smart throttling if available
        if ticker and self.cache_control and self._cache_initialized and throttle_level > 0:
            # Cache control determines if this ticker should be processed under current throttle
            should_process = self.cache_control.should_prioritize_processing(ticker, throttle_level)
            if not should_process:
                return True  # Drop it
        
        # Fallback to simple priority-based dropping
        if queue_size > drop_threshold and priority > 2:
            return True
        
        # Extreme overflow - drop everything except highest priority
        if queue_size > self.max_queue_size * 0.98 and priority > 1:
            return True
        
        return False
    
    '''
    def get_priority_status(self) -> Dict[str, Any]:
        """
        Get current priority configuration status.
        SPRINT 54: New method to check priority cache status.
        """
        status = {
            'cache_initialized': self._cache_initialized,
            'top_priority_count': len(self.priority_tickers),
            'secondary_priority_count': len(self.important_tickers),
            'total_priority_stocks': len(self._priority_ticker_set),
            'market_open_tickers': list(self.market_open_tickers),
            'last_cache_refresh': self._priority_cache_refresh_time,
            'cache_age_seconds': time.time() - self._priority_cache_refresh_time if self._priority_cache_refresh_time else None
        }
        
        # Add cache stats if available
        if self.cache_control and self._cache_initialized:
            priority_stats = self.cache_control.get_priority_stats()
            status['cache_stats'] = priority_stats
        
        return status
    '''
    def add_event(self, event: BaseEvent) -> bool:
        """
        Add typed event to queue with bulletproof validation and protection.
        
        Args:
            event: BaseEvent instance to add to queue
            
        Returns:
            bool: True if event was successfully queued, False otherwise
        """
        start_time = time.time()
        
        # Check shutdown state
        with self._shutdown_lock:
            if self._shutdown:
                logger.debug("Priority manager is shutting down, rejecting event")
                logger.warning(f"⚠️ Event rejected - shutdown: {event.type if hasattr(event, 'type') else 'unknown'}")
                return False
        
        try:
            # Track attempt
            self.diagnostics.total_attempts += 1
            
            # PHASE 4: Strict type validation
            if not isinstance(event, BaseEvent):
                logger.error(f"❌ Invalid event type: {type(event)}. Only BaseEvent instances accepted.")
                self.diagnostics.record_drop('invalid_type')
                self._trace_event_dropped(None, 'invalid_type', start_time)
                logger.warning(f"⚠️ Event rejected - invalid type: {type(event)}")
                return False
            
            # Extract event information - no overrides allowed
            ticker = event.ticker
            event_type = event.type
            
            # Validate event has required fields
            if not ticker or not event_type:
                logger.error(f"❌ Event missing required fields: ticker={ticker}, type={event_type}")
                self.diagnostics.record_drop('invalid_event')
                return False
            
            # Check event age immediately
            if hasattr(event, 'time') and event.time:
                age_ms = (time.time() - event.time) * 1000
                self.diagnostics.record_event_age(age_ms)
                
                if age_ms > self.max_event_age_ms:
                    logger.warning(f"⏰ Dropping aged event on arrival: {event_type} for {ticker}, age={age_ms:.0f}ms")
                    self.diagnostics.record_drop('age_expired')
                    self.drops_by_type[event_type]['age_expired'] += 1
                    self._trace_event_dropped(ticker, 'age_expired', start_time, age_ms=age_ms)
                    return False
                
                # Warn about very old events
                if age_ms > 5000:  # 5 seconds
                    logger.warning(f"⚠️ Old event detected: {event_type} for {ticker}, age={age_ms:.0f}ms")
            
            # Special logging for important events
            #if isinstance(event, SurgeEvent):
            #    logger.info(f"🚀 SURGE EVENT RECEIVED: {ticker} {event.direction} "
            #            f"magnitude={event.surge_magnitude:.1f}% score={event.surge_score:.1f}")
            
            # Track event type
            self.flow_stats.event_type_counts[event_type] += 1
            
            # Determine priority
            priority = self._determine_priority_safe(ticker, event_type)
            
            # Check queue state
            current_size = self.event_queue.qsize()
            self.diagnostics.record_queue_depth(current_size)
            
            # Update high water mark
            if current_size > self.queue_high_water_mark:
                self.queue_high_water_mark = current_size
                if current_size > self.max_queue_size * 0.8:
                    logger.warning(f"⚠️ Queue approaching capacity: {current_size}/{self.max_queue_size}")
            
            # Check if queue is full
            if current_size >= self.max_queue_size:
                logger.error(f"🚨 Queue FULL: {current_size}/{self.max_queue_size} - dropping {event_type}")
                self.diagnostics.record_drop('queue_full')
                self.drops_by_type[event_type]['queue_full'] += 1

                self.flow_stats.events_dropped += 1
                self._record_overflow(ticker, event_type, priority)
                self._trace_event_dropped(ticker, 'queue_full', start_time, queue_size=current_size)
                return False
            
            # Apply overflow protection with smart throttling
            if self._should_drop_for_overflow(current_size, priority, event_type, ticker):
                logger.debug(f"⚠️ Queue overload protection: dropping {event_type} for {ticker} (priority={priority})")
                self.diagnostics.record_drop('low_priority')
                self.drops_by_type[event_type]['low_priority'] += 1
                self.flow_stats.events_dropped += 1
                self.last_overflow_time = time.time()
                self._trace_event_dropped(ticker, 'low_priority_overflow', start_time, 
                                        queue_size=current_size, priority=priority)
                return False
            
            # Add to queue with circuit breaker protection
            success = self._add_to_queue_safe(event, priority, ticker, event_type, start_time)
            
            if success:
                self._handle_successful_add(priority, ticker, event_type, event, start_time)
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Unexpected error in add_event: {e}", exc_info=True)
            self.diagnostics.record_drop('exception')
            self.flow_stats.events_dropped += 1
            self._trace_event_error(ticker if 'ticker' in locals() else 'UNKNOWN', 
                                  'add_event', e, start_time)
            logger.warning(f"⚠️ Event rejected - exception: {e} for {event.type if hasattr(event, 'type') else 'unknown'}")
            return False
    
    def _determine_priority_safe(self, ticker: str, event_type: str) -> int:
        """
        Safely determine event priority with cache-based priority checks.
        SPRINT 54: Now uses cache methods for priority determination.
        """
        try:
            # Refresh cache if needed
            self._refresh_priority_cache_if_needed()
            
            # Base priority from event type
            base_priority = self.EVENT_PRIORITIES.get(event_type, 4)
            
            # Check market open period for special handling
            if self._is_market_open_period():
                if ticker in self.market_open_tickers:
                    return 1  # Highest priority for market ETFs
            
            # SPRINT 54: Use cache-based priority checking
            if self.cache_control and self._cache_initialized:
                priority_info = self.cache_control.is_priority_stock(ticker)
                
                if priority_info.get('is_priority'):
                    priority_level = priority_info.get('priority_level', 'UNKNOWN')
                    
                    if priority_level == 'TOP':
                        return 1  # Highest priority
                    elif priority_level == 'SECONDARY':
                        return min(2, base_priority)  # Secondary priority
                    else:
                        # Unknown priority level but still marked as priority
                        return min(3, base_priority)
            else:
                # Fallback to in-memory sets if cache not available
                if ticker in self.priority_tickers:
                    return 1
                elif ticker in self.important_tickers:
                    return min(2, base_priority)
            
            return base_priority
            
        except Exception as e:
            logger.error(f"Error determining priority for {ticker}: {e}")
            return 4  # Default to lowest priority on error
    
    def _should_drop_for_overflow(self, queue_size: int, priority: int, event_type: str, ticker: str = None) -> bool:
        """
        Determine if event should be dropped due to overflow conditions.
        SPRINT 54: Integrates cache throttle level logic for smart dropping.
        """
        drop_threshold = int(self.max_queue_size * self.overflow_drop_threshold)
        
        # Never drop control or surge events
        if event_type in ('control', 'surge'):
            return False
        
        # Calculate throttle level based on queue pressure
        throttle_level = 0
        queue_utilization = queue_size / self.max_queue_size
        
        if queue_utilization > 0.98:
            throttle_level = 3  # Severe
        elif queue_utilization > 0.95:
            throttle_level = 2  # Moderate  
        elif queue_utilization > 0.90:
            throttle_level = 1  # Mild
        
        # Use cache's smart throttling if available
        if ticker and self.cache_control and self._cache_initialized and throttle_level > 0:
            # Cache control determines if this ticker should be processed under current throttle
            should_process = self.cache_control.should_prioritize_processing(ticker, throttle_level)
            if not should_process:
                return True  # Drop it
        
        # Fallback to simple priority-based dropping
        if queue_size > drop_threshold and priority > 2:
            return True
        
        # Extreme overflow - drop everything except highest priority
        if queue_size > self.max_queue_size * 0.98 and priority > 1:
            return True
        
        return False
    
    def _add_to_queue_safe(self, event: BaseEvent, priority: int, ticker: str, 
                          event_type: str, start_time: float) -> bool:
        """Safely add event to queue with circuit breaker protection."""
        try:
            def queue_put():
                return self.event_queue.put(event, priority)
            
            return self.queue_breaker.call(queue_put)
            
        except pybreaker.CircuitBreakerError:
            logger.error(f"🚨 CIRCUIT BREAKER OPEN: dropping {event_type} for {ticker}")
            self.diagnostics.record_drop('circuit_breaker')
            self.flow_stats.circuit_trips += 1
            self.flow_stats.events_dropped += 1
            self._trace_circuit_breaker_trip(ticker, event_type, start_time)
            return False
    
    def _handle_successful_add(self, priority: int, ticker: str, event_type: str, 
                              event: BaseEvent, start_time: float):
        """
        Handle successful event addition.
        SPRINT 54: Still tracks high priority events (priority == 1) which now come from cache.
        """
        self.flow_stats.events_added += 1
        
        # Track high priority events (priority == 1)
        if priority == 1:
            self.flow_stats.high_priority_events += 1
        
        # Log important events
        if event_type == 'surge':
            #logger.info(f"✅ SURGE EVENT QUEUED: {ticker} - Queue size: {self.event_queue.qsize()}")
            self._trace_surge_queued(ticker, event, start_time)
        
        # Periodic flow stats logging
        if self.flow_stats.should_log():
            self.flow_stats.log_stats()
        
        # Trace periodic samples
        if self.flow_stats.events_added % 100 == 0:
            self._trace_queue_sample(start_time)

    def collect_typed_events(self, 
                           max_events: Optional[int] = None,
                           timeout: float = 0.1,
                           event_types: Optional[List[type]] = None,
                           check_age: bool = True) -> List[BaseEvent]:
        """
        Collect typed events from queue with age validation.
        
        Args:
            max_events: Maximum events to collect
            timeout: Timeout for collection
            event_types: Optional list of event types to filter
            check_age: Whether to check and drop aged events
            
        Returns:
            List of BaseEvent instances
        """
        if max_events is None:
            max_events = self.batch_size
        
        start_time = time.time()
        collected_events = []
        dropped_for_age = 0
        
        # Use TypedEventQueue's get_typed_batch method
        typed_events = self.event_queue.get_typed_batch(
            max_items=max_events,
            timeout=timeout,
            event_types=event_types
        )
        
        current_time = time.time()
        
        for event in typed_events:
            # Age validation if requested
            if check_age and hasattr(event, 'time') and event.time:
                age_ms = (current_time - event.time) * 1000
                
                if age_ms > self.max_event_age_ms:
                    logger.debug(f"⏰ Dropping aged event during collection: "
                               f"{event.type} for {event.ticker}, age={age_ms:.0f}ms")
                    dropped_for_age += 1
                    self.diagnostics.record_drop('age_expired_collection')
                    continue
            
            collected_events.append(event)
        
        # Update statistics
        self.flow_stats.events_collected += len(collected_events)
        
        # Log if events were dropped
        if dropped_for_age > 0:
            logger.warning(f"⏰ Dropped {dropped_for_age} aged events during collection")
        
        return collected_events
    
    def collect_events(self, max_events: int = None, timeout: float = 0.1) -> List[Tuple[str, BaseEvent]]:
        """
        Collect typed events from queue - backward compatibility method.
        PHASE 4: Returns tuples of (event_type, BaseEvent)
        """
        if max_events is None:
            max_events = self.batch_size
        
        start_time = time.time()
        events = []
        
        # Use the core typed collection method
        typed_events = self.collect_typed_events(
            max_events=max_events,
            timeout=timeout,
            check_age=True
        )
        
        # Convert to tuple format for backward compatibility
        for event in typed_events:
            # Handle control events
            if isinstance(event, ControlEvent):
                if event.command == 'shutdown':
                    events.append(('stop', None))
                else:
                    events.append((event.type, event))
            else:
                # Regular typed events
                events.append((event.type, event))
        
        # Log collection summary
        if events:
            event_summary = defaultdict(int)
            for event_type, _ in events:
                event_summary[event_type] += 1
            
        
        # Trace collection if significant
        if len(events) >= 10 and tracer.should_trace('SYSTEM'):
            tracer.trace(
                ticker='SYSTEM',
                component="PriorityManager",
                action="events_collected",
                data={
                    'timestamp': time.time(),
                    'input_count': ensure_int(self.event_queue.qsize() + len(events)),  # Approximate queue size before
                    'output_count': ensure_int(len(events)),
                    'duration_ms': (time.time() - start_time) * 1000,
                    'details': {
                        "events_collected": ensure_int(len(events)),
                        "event_breakdown": dict(event_summary) if 'event_summary' in locals() else {},
                        "queue_size_after": ensure_int(self.event_queue.qsize())
                    }
                }
            )
        
        return events

    '''
    def collect_display_events(self, 
                             max_events: Optional[int] = None,
                             timeout: float = 0.1) -> List[Tuple[str, BaseEvent]]:
        """
        Collect display events (high/low/trend/surge) for UI.
        Returns tuples of (event_type, event) for compatibility.
        """
        if max_events is None:
            max_events = 200
        
        start_time = time.time()
        
        # Collect only display event types
        typed_events = self.collect_typed_events(
            max_events=max_events,
            timeout=timeout,
            event_types=self.DISPLAY_EVENT_TYPES,
            check_age=True
        )
        
        # Convert to tuple format for compatibility
        display_events = []
        for event in typed_events:
            display_events.append((event.type, event))
        
        # Log summary if events collected
        if display_events:
            event_summary = defaultdict(int)
            for event_type, _ in display_events:
                event_summary[event_type] += 1
            logger.debug(f"🖥️ Display events collected: {dict(event_summary)}")
        
        return display_events
    '''
    def get_queue_status(self) -> Dict[str, Any]:
        """Get comprehensive queue status."""
        current_size = self.event_queue.qsize()
        
        return {
            'current_size': current_size,
            'max_size': self.max_queue_size,
            'utilization_percent': round((current_size / self.max_queue_size) * 100, 2),
            'high_water_mark': self.queue_high_water_mark,
            'circuit_breaker_state': str(self.queue_breaker.state),
            'last_overflow_time': self.last_overflow_time,
            'is_healthy': self._is_queue_healthy(),
            'data_flow': {
                'events_added': self.flow_stats.events_added,
                'events_collected': self.flow_stats.events_collected,
                'events_dropped': self.flow_stats.events_dropped,
                'high_priority_events': self.flow_stats.high_priority_events,
                'circuit_trips': self.flow_stats.circuit_trips,
                'efficiency_percent': round(
                    (self.flow_stats.events_collected / self.flow_stats.events_added * 100)
                    if self.flow_stats.events_added > 0 else 0, 2
                )
            },
            'diagnostics': self.diagnostics.get_stats()
        }
    
    def _is_queue_healthy(self) -> bool:
        """Check if queue is in healthy state."""
        current_size = self.event_queue.qsize()
        
        # Check various health indicators
        if self.queue_breaker.state == pybreaker.STATE_OPEN:
            return False
        
        if current_size > self.max_queue_size * 0.9:
            return False
        
        if self.flow_stats.events_added > 0:
            drop_rate = self.flow_stats.events_dropped / self.flow_stats.events_added
            if drop_rate > 0.1:  # More than 10% drops
                return False
        
        return True
    
    def _is_market_open_period(self) -> bool:
        """Check if within first 30 minutes of market open."""
        try:
            now = datetime.now(pytz.timezone('US/Eastern'))
            market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
            market_open_end = market_open + timedelta(minutes=30)
            
            return market_open <= now <= market_open_end
        except Exception as e:
            logger.error(f"Error checking market open period: {e}")
            return False
    
    def _record_overflow(self, ticker: str, event_type: str, priority: int):
        """Record overflow event for analysis."""
        overflow_info = {
            'timestamp': time.time(),
            'ticker': ticker,
            'event_type': event_type,
            'priority': priority,
            'queue_size': self.event_queue.qsize()
        }
        self.overflow_events.append(overflow_info)
    
    def shutdown(self):
        """Gracefully shutdown the priority manager."""
        with self._shutdown_lock:
            self._shutdown = True
        
        # Add control event to signal shutdown
        try:
            control_event = ControlEvent(command='shutdown')
            self.add_event(control_event)
        except Exception as e:
            logger.error(f"Error adding shutdown event: {e}")
        
        logger.info("Priority manager shutdown initiated")
    
    '''
    def reset_statistics(self):
        """Reset all statistics."""
        self.flow_stats = DataFlowStats()
        self.diagnostics = QueueDiagnostics()
        self.queue_high_water_mark = 0
        self.last_overflow_time = 0
        self.overflow_events.clear()
        
        logger.info("✅ Priority manager statistics reset")
    '''
    # Tracing helper methods
    def _trace_event_dropped(self, ticker: Optional[str], reason: str, 
                           start_time: float, **details):
        """Trace event drop with reason."""
        if ticker and ticker != 'CONTROL' and tracer.should_trace(ticker):
            tracer.trace(
                ticker=ticker,
                component="PriorityManager",
                action="event_dropped",
                data={
                    'timestamp': time.time(),
                    'input_count': ensure_int(1),
                    'output_count': ensure_int(0),
                    'duration_ms': (time.time() - start_time) * 1000,
                    'details': {
                        "reason": reason,
                        **details
                    }
                }
            )
    
    def _trace_event_error(self, ticker: str, method: str, error: Exception, start_time: float):
        """Trace event processing error."""
        if tracer.should_trace(ticker):
            tracer.trace(
                ticker=ticker,
                component="PriorityManager",
                action="error",
                data={
                    'timestamp': time.time(),
                    'input_count': ensure_int(1),
                    'output_count': ensure_int(0),
                    'duration_ms': (time.time() - start_time) * 1000,
                    'error': str(error),
                    'details': {
                        "error_type": type(error).__name__,
                        "method": method
                    }
                }
            )
    
    def _trace_circuit_breaker_trip(self, ticker: str, event_type: str, start_time: float):
        """Trace circuit breaker trip."""
        if tracer.should_trace(ticker):
            tracer.trace(
                ticker=ticker,
                component="PriorityManager",
                action="circuit_breaker_trip",
                data={
                    'timestamp': time.time(),
                    'input_count': ensure_int(1),
                    'output_count': ensure_int(0),
                    'duration_ms': (time.time() - start_time) * 1000,
                    'error': 'Circuit breaker open',
                    'details': {
                        "event_type": event_type,
                        "breaker_state": str(self.queue_breaker.state),
                        "total_trips": self.flow_stats.circuit_trips
                    }
                }
            )
    
    def _trace_surge_queued(self, ticker: str, event: SurgeEvent, start_time: float):
        """Trace surge event queued."""
        if tracer.should_trace(ticker):
            tracer.trace(
                ticker=ticker,
                component="PriorityManager",
                action="surge_event_queued",
                data={
                    'timestamp': time.time(),
                    'input_count': ensure_int(1),
                    'output_count': ensure_int(1),
                    'duration_ms': (time.time() - start_time) * 1000,
                    'details': {
                        "event_type": "surge",
                        "direction": event.direction,
                        "surge_magnitude": event.surge_magnitude,
                        "surge_score": event.surge_score,
                        "queue_size_after": ensure_int(self.event_queue.qsize())
                    }
                }
            )
    
    def _trace_queue_sample(self, start_time: float):
        """Trace periodic queue sample."""
        if tracer.should_trace('SYSTEM'):
            tracer.trace(
                ticker='SYSTEM',
                component="PriorityManager",
                action="queue_sample",
                data={
                    'timestamp': time.time(),
                    'input_count': ensure_int(100),  # Sample represents 100 events
                    'output_count': ensure_int(100),
                    'duration_ms': (time.time() - start_time) * 1000,
                    'details': {
                        "queue_size": ensure_int(self.event_queue.qsize()),
                        "queue_utilization": (self.event_queue.qsize() / self.max_queue_size) * 100,
                        "high_priority_ratio": (self.flow_stats.high_priority_events / 
                                              self.flow_stats.events_added * 100)
                                              if self.flow_stats.events_added > 0 else 0,
                        "total_events_queued": self.flow_stats.events_added
                    }
                }
            )

    def get_drop_analysis(self) -> Dict[str, Any]:
        """Analyze drop patterns to identify bottlenecks."""
        stats = self.diagnostics.get_stats()
        
        # Calculate drop percentages by reason
        total_attempts = self.diagnostics.total_attempts
        if total_attempts == 0:
            return {"error": "No events processed yet"}
        
        drop_analysis = {
            'total_attempts': total_attempts,
            'total_drops': stats['drops']['total'],
            'overall_drop_rate': stats['drop_rate_percent'],
            'drop_breakdown': {},
            'recommendations': []
        }
        
        # Analyze each drop reason
        for reason, count in self.diagnostics.drop_reasons.items():
            percentage = (count / total_attempts) * 100
            drop_analysis['drop_breakdown'][reason] = {
                'count': count,
                'percentage': round(percentage, 2)
            }
        
        # Generate recommendations based on drop patterns
        if self.diagnostics.queue_full_drops > 0:
            drop_analysis['recommendations'].append(
                f"Queue full drops detected ({self.diagnostics.queue_full_drops}). "
                f"Consider increasing MAX_QUEUE_SIZE from {self.max_queue_size}"
            )
        
        if self.diagnostics.age_expired_drops > 0:
            avg_age = sum(self.diagnostics.event_ages_ms) / len(self.diagnostics.event_ages_ms) if self.diagnostics.event_ages_ms else 0
            drop_analysis['recommendations'].append(
                f"Age expired drops detected ({self.diagnostics.age_expired_drops}). "
                f"Average event age: {avg_age:.0f}ms. Consider faster processing or increasing MAX_EVENT_AGE_MS"
            )
        
        if self.diagnostics.priority_drops > 0:
            drop_analysis['recommendations'].append(
                f"Priority drops detected ({self.diagnostics.priority_drops}). "
                f"Queue is under pressure. Consider batch processing or filtering upstream"
            )
        
        return drop_analysis

    '''
    def get_flow_bottleneck_analysis(self) -> Dict[str, Any]:
        """Identify where events are getting stuck in the pipeline."""
        current_queue_size = self.event_queue.qsize()
        
        analysis = {
            'pipeline_stages': {
                'detected': self.flow_stats.events_added,
                'in_queue': current_queue_size,
                'collected': self.flow_stats.events_collected,
                'dropped': self.flow_stats.events_dropped
            },
            'bottlenecks': []
        }
        
        # Check for queue backup
        if current_queue_size > self.max_queue_size * 0.5:
            analysis['bottlenecks'].append({
                'stage': 'queue_processing',
                'severity': 'high' if current_queue_size > self.max_queue_size * 0.8 else 'medium',
                'message': f'Queue is {(current_queue_size/self.max_queue_size)*100:.1f}% full',
                'recommendation': 'Increase worker processing rate or add more workers'
            })
        
        # Check collection rate
        if self.flow_stats.events_added > 0:
            collection_rate = self.flow_stats.events_collected / self.flow_stats.events_added
            if collection_rate < 0.9:
                analysis['bottlenecks'].append({
                    'stage': 'collection',
                    'severity': 'high' if collection_rate < 0.7 else 'medium',
                    'message': f'Only {collection_rate*100:.1f}% of events are being collected',
                    'recommendation': 'Check worker health and collection timeout settings'
                })
        
        # Check drop patterns
        if self.flow_stats.events_dropped > self.flow_stats.events_collected * 0.1:
            analysis['bottlenecks'].append({
                'stage': 'queue_ingestion',
                'severity': 'critical',
                'message': f'Dropping {self.flow_stats.events_dropped} events (more than 10% of collected)',
                'recommendation': 'System overloaded - need to scale up or filter events upstream'
            })
        
        return analysis
    '''
    def diagnose_queue_contents(self) -> Dict[str, Any]:
        """
        Diagnostic method to peek at queue contents without removing items.
        Backward compatibility method.
        """
        try:
            queue_size = self.event_queue.qsize()
            
            # Get additional diagnostic info
            diagnostics = {
                "queue_size": queue_size,
                "max_size": self.max_queue_size,
                "utilization_percent": round((queue_size / self.max_queue_size) * 100, 2),
                "circuit_breaker_state": str(self.queue_breaker.state),
                "high_water_mark": self.queue_high_water_mark,
                "events_added": self.flow_stats.events_added,
                "events_collected": self.flow_stats.events_collected,
                "events_dropped": self.flow_stats.events_dropped,
                "drop_rate": round((self.flow_stats.events_dropped / self.flow_stats.events_added * 100) 
                                if self.flow_stats.events_added > 0 else 0, 2)
            }
            
            # Add event type breakdown if available
            if self.flow_stats.event_type_counts:
                diagnostics["event_types"] = dict(self.flow_stats.event_type_counts)
            
            logger.debug(f"🔍 DIAG-PRIORITY: QUEUE DIAGNOSTIC: Current queue size: {queue_size}")
            
            return diagnostics
            
        except Exception as e:
            logger.error(f"❌ Queue diagnostic error: {e}", exc_info=True)
            return {"error": str(e), "queue_size": 0}

    def get_diagnostics_queue_diagnostics(self) -> Dict[str, Any]:
        """
        Get detailed queue diagnostics.
        Note: This method name suggests it was auto-generated or has a typo.
        Maintaining for backward compatibility.
        """
        # Get the comprehensive diagnostics
        detailed_stats = self.diagnostics.get_stats()
        
        # Add current queue state
        current_size = self.event_queue.qsize()
        detailed_stats.update({
            'current_size': current_size,
            'max_configured_size': self.max_queue_size,
            'utilization_percent': round((current_size / self.max_queue_size) * 100, 2),
            'high_water_mark': self.queue_high_water_mark,
            'circuit_breaker_state': str(self.queue_breaker.state),
            'is_healthy': self._is_queue_healthy(),
            'flow_efficiency_percent': round(
                (self.flow_stats.events_collected / self.flow_stats.events_added * 100)
                if self.flow_stats.events_added > 0 else 0, 2
            )
        })
        
        # Add event type breakdown
        if self.flow_stats.event_type_counts:
            detailed_stats['event_type_counts'] = dict(self.flow_stats.event_type_counts)
        
        return detailed_stats
    
    def get_detailed_drop_analysis(self) -> Dict[str, Any]:
        """Get detailed drop analysis including by event type."""
        base_analysis = self.get_drop_analysis()
        
        # Add drops by event type
        base_analysis['drops_by_event_type'] = {}
        
        for event_type, drops in self.drops_by_type.items():
            total_attempts = self.flow_stats.event_type_counts.get(event_type, 0)
            total_drops = sum(drops.values())
            
            base_analysis['drops_by_event_type'][event_type] = {
                'total_attempts': total_attempts,
                'total_drops': total_drops,
                'drop_rate': (total_drops / total_attempts * 100) if total_attempts > 0 else 0,
                'drop_reasons': dict(drops)
            }
        
        # Add queue pressure analysis
        base_analysis['queue_pressure'] = {
            'current_size': self.event_queue.qsize(),
            'overflow_threshold_size': int(self.max_queue_size * self.overflow_drop_threshold),
            'is_under_pressure': self.event_queue.qsize() > (self.max_queue_size * 0.8),
            'pressure_percentage': (self.event_queue.qsize() / self.max_queue_size * 100)
        }
        
        return base_analysis