"""
Data Publisher - Phase 2 Refactoring - Phase 4 Update
Handles all data publishing, formatting, and user routing logic.
Phase 4: Pure typed events only - no dict compatibility
"""

import logging
import json
import time
import threading
import queue
from datetime import datetime
from typing import Dict, List, Any, Optional
from typing import Callable
from dataclasses import dataclass
from src.core.domain.events.base import BaseEvent
from src.core.domain.events.highlow import HighLowEvent
from src.core.domain.events.trend import TrendEvent
from src.core.domain.events.surge import SurgeEvent
from src.core.domain.events.aggregate import PerMinuteAggregateEvent
from src.core.domain.events.fmv import FairMarketValueEvent
from src.presentation.converters.transport_models import StockData
from src.shared.types import FrequencyType

from src.monitoring.tracer import tracer, TraceLevel, normalize_event_type, ensure_int

from config.logging_config import get_domain_logger, LogDomain

logger = get_domain_logger(LogDomain.CORE, 'data_publisher')


class DataFlowStats:
    """Track data flow through the publisher."""
    def __init__(self):
        self.publish_attempts = 0
        self.publish_successes = 0
        self.users_reached = 0
        self.events_sent = 0
        self.last_log_time = time.time()
        self.log_interval = 30  # seconds
    
    def should_log(self):
        return time.time() - self.last_log_time >= self.log_interval
    
    def log_stats(self):
        success_rate = (self.publish_successes / self.publish_attempts * 100) if self.publish_attempts > 0 else 0
        logger.info(f"📊DATA-PUB: PUBLISH STATS: Attempts:{self.publish_attempts} → Success:{self.publish_successes} ({success_rate:.1f}%) → Users:{self.users_reached} → Events:{self.events_sent}")
        self.last_log_time = time.time()


@dataclass
class PublishingResult:
    """Result object for publishing operations."""
    success: bool = True
    users_reached: int = 0
    events_published: int = 0
    errors: Optional[List[str]] = None
    warnings: Optional[List[str]] = None
    timestamp: float = None
    processing_time_ms: float = 0
    publishing_method: str = "unknown"
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


class DataPublisher:
    """
    Handles all data publishing logic with clean separation of concerns.
    Phase 4: Works exclusively with typed events.
    """
    # Default configuration values
    DEFAULT_COLLECTION_MAX_EVENTS = 1000
    DEFAULT_COLLECTION_TIMEOUT = 0.5
    
    def __init__(self, config, market_service, websocket_publisher=None, 
                 market_metrics=None):
        """Initialize data publisher with hybrid dependency injection."""
        
        # Core dependencies
        self.market_service = market_service
        self.websocket_publisher = websocket_publisher or market_service.websocket_publisher
        self.market_metrics = market_metrics or market_service.market_metrics
        
        # Config subset
        self.config = config
        
        # Initialize logging
        self.logger = get_domain_logger(LogDomain.CORE, 'data_publisher')
        
        # Publishing state management
        self.publishing_active = False
        self.publisher_thread = None
        self.last_publish_time = time.time()
        
        # Data flow tracking
        self.stats = DataFlowStats()
        
        # Event deduplication
        self.sent_high_events = set()
        self.sent_low_events = set()
        self.last_session = None

        self._collection_callbacks = []

        # SPRINT 101: MULTI-FREQUENCY EVENT BUFFER FOR PULL MODEL
        # Enhanced event buffer management with frequency separation
        self.event_buffer = {
            # Per-second frequency events (existing)
            'per_second': {
                'highs': [],
                'lows': [],
                'trending': {'up': [], 'down': []},
                'surging': {'up': [], 'down': []}
            },
            # Per-minute frequency events (new)
            'per_minute': {
                'aggregates': [],  # PerMinuteAggregateEvent objects
                'highs': [],       # High/Low events from minute aggregates
                'lows': [],
                'trending': {'up': [], 'down': []},
                'surging': {'up': [], 'down': []}
            },
            # Fair Market Value events (new)
            'fmv': {
                'fmv_events': [],  # FairMarketValueEvent objects
                'valuation_alerts': []  # Significant valuation deviation alerts
            }
        }
        # SPRINT 101: Multi-frequency buffer stats
        self.buffer_stats = {
            'events_buffered': 0,
            'events_delivered': 0,
            'buffer_overflows': 0,
            'last_buffer_clear': time.time(),
            # Frequency-specific stats
            'per_second_events': 0,
            'per_minute_events': 0,
            'fmv_events': 0,
            'frequency_breakdown': {
                FrequencyType.PER_SECOND.value: {'buffered': 0, 'delivered': 0},
                FrequencyType.PER_MINUTE.value: {'buffered': 0, 'delivered': 0},
                FrequencyType.FAIR_MARKET_VALUE.value: {'buffered': 0, 'delivered': 0}
            }
        }
        self.buffer_lock = threading.Lock()
        self.MAX_BUFFER_SIZE = 1000  # per event type

        # Track connection state
        self._last_user_count = 0
        self._first_user_connected_time = None
        
        # Track delivery status
        self.undelivered_events = set()  # Event keys that haven't been delivered to any user

        try:
            from src.monitoring.system_monitor import system_monitor
            system_monitor.set_services(
                market_service=market_service,
                data_publisher=self
            )
        except ImportError:
            logger.warning("System monitor not available")

        # -----------------------------------------------------
        # DIAGNOSTICS verification tracking
        # DIAGNOSTICS CONTROLLED BY TRACE ENABLED FLAG
        self.collection_diagnostics = {
            'enabled': config.get('TRACE_ENABLED', True),  # Enable via config
            'collections_attempted': 0,
            'events_collected_total': 0,
            'events_lost_in_collection': 0,
            'collection_times_ms': [],
            'empty_collections': 0,
            'collection_sizes': [],
            'queue_sizes_before': [],
            'queue_sizes_after': []
        }
        # DIAGNOSTICS verification tracking
        # DIAGNOSTICS CONTROLLED BY TRACE ENABLED FLAG
        self.process_collection_verification = {
            'enabled': config.get('TRACE_ENABLED', True),  # Enable via config
            'start_time': None,
            'initial_stats': None,
            'verification_duration': 200,  # 2 minutes
            'verification_complete': False,
            'last_check_time': 0,
            'check_interval': 30  # Check every 30 seconds
        }
        # -----------------------------------------------------
        
        self.collection_max_events = config.get('COLLECTION_MAX_EVENTS', self.DEFAULT_COLLECTION_MAX_EVENTS)
        self.collection_timeout = config.get('COLLECTION_TIMEOUT', self.DEFAULT_COLLECTION_TIMEOUT)
        
        # SPRINT 101: Multi-frequency processing support
        self.enabled_frequencies = set([FrequencyType.PER_SECOND])  # Default to per-second only
        self.frequency_event_processors = {}  # Will hold frequency-specific processors
    
    # SPRINT 101: Multi-frequency support methods
    def enable_frequency(self, frequency_type: FrequencyType):
        """Enable processing for a specific frequency type"""
        self.enabled_frequencies.add(frequency_type)
        logger.info(f"DATA-PUB: Enabled frequency processing for {frequency_type.value}")
    
    def disable_frequency(self, frequency_type: FrequencyType):
        """Disable processing for a specific frequency type"""
        self.enabled_frequencies.discard(frequency_type)
        logger.info(f"DATA-PUB: Disabled frequency processing for {frequency_type.value}")
    
    def collect_frequency_event(self, event: BaseEvent, frequency_type: FrequencyType):
        """
        SPRINT 101: Collect event from a specific frequency stream and buffer it.
        This method is called by DataStreamManager for each frequency stream.
        """
        try:
            with self.buffer_lock:
                if frequency_type == FrequencyType.PER_SECOND:
                    self._buffer_per_second_event(event)
                elif frequency_type == FrequencyType.PER_MINUTE:
                    self._buffer_per_minute_event(event)
                elif frequency_type == FrequencyType.FAIR_MARKET_VALUE:
                    self._buffer_fmv_event(event)
                else:
                    logger.warning(f"DATA-PUB: Unsupported frequency type: {frequency_type}")
                    return False
                
                # Update stats
                self.buffer_stats['events_buffered'] += 1
                self.buffer_stats['frequency_breakdown'][frequency_type.value]['buffered'] += 1
                
                if frequency_type == FrequencyType.PER_SECOND:
                    self.buffer_stats['per_second_events'] += 1
                elif frequency_type == FrequencyType.PER_MINUTE:
                    self.buffer_stats['per_minute_events'] += 1
                elif frequency_type == FrequencyType.FAIR_MARKET_VALUE:
                    self.buffer_stats['fmv_events'] += 1
                
                logger.debug(f"DATA-PUB: Buffered {frequency_type.value} event: {event}")
                return True
                
        except Exception as e:
            logger.error(f"DATA-PUB: Error collecting {frequency_type.value} event: {e}", exc_info=True)
            return False
    
    def _buffer_per_second_event(self, event: BaseEvent):
        """Buffer per-second frequency events (existing logic)"""
        event_type = getattr(event, 'type', 'unknown')
        
        # Convert event to dict for compatibility with existing buffer structure
        event_dict = event.to_transport_dict() if hasattr(event, 'to_transport_dict') else event.to_dict()
        
        if event_type in ['high', 'session_high']:
            self._add_to_frequency_buffer('per_second', 'highs', [event_dict])
        elif event_type in ['low', 'session_low']:
            self._add_to_frequency_buffer('per_second', 'lows', [event_dict])
        elif event_type == 'trend':
            direction = 'up' if getattr(event, 'direction', '') in ['↑', 'up'] else 'down'
            self._add_to_frequency_buffer_nested('per_second', 'trending', direction, [event_dict])
        elif event_type == 'surge':
            direction = 'up' if getattr(event, 'direction', '') in ['↑', 'up'] else 'down'
            self._add_to_frequency_buffer_nested('per_second', 'surging', direction, [event_dict])
    
    def _buffer_per_minute_event(self, event: BaseEvent):
        """Buffer per-minute frequency events"""
        if isinstance(event, PerMinuteAggregateEvent):
            # Store the full aggregate event
            event_dict = event.to_transport_dict()
            self._add_to_frequency_buffer('per_minute', 'aggregates', [event_dict])
            
            # Also check if this aggregate represents a significant high/low for the minute
            self._analyze_minute_aggregate_for_events(event)
        else:
            # Handle other per-minute events (high/low/trend/surge derived from minute data)
            event_type = getattr(event, 'type', 'unknown')
            event_dict = event.to_transport_dict() if hasattr(event, 'to_transport_dict') else event.to_dict()
            
            if event_type in ['high', 'session_high']:
                self._add_to_frequency_buffer('per_minute', 'highs', [event_dict])
            elif event_type in ['low', 'session_low']:
                self._add_to_frequency_buffer('per_minute', 'lows', [event_dict])
            elif event_type == 'trend':
                direction = 'up' if getattr(event, 'direction', '') in ['↑', 'up'] else 'down'
                self._add_to_frequency_buffer_nested('per_minute', 'trending', direction, [event_dict])
            elif event_type == 'surge':
                direction = 'up' if getattr(event, 'direction', '') in ['↑', 'up'] else 'down'
                self._add_to_frequency_buffer_nested('per_minute', 'surging', direction, [event_dict])
    
    def _buffer_fmv_event(self, event: BaseEvent):
        """Buffer Fair Market Value events"""
        if isinstance(event, FairMarketValueEvent):
            event_dict = event.to_transport_dict()
            self._add_to_frequency_buffer('fmv', 'fmv_events', [event_dict])
            
            # Check if this is a significant valuation deviation
            if event.is_significant_deviation(threshold_pct=5.0):  # 5% threshold
                valuation_alert = {
                    'ticker': event.ticker,
                    'fmv_price': event.fmv_price,
                    'market_price': event.market_price,
                    'deviation_pct': event.fmv_vs_market_pct,
                    'signal': event._get_valuation_signal(),
                    'timestamp': event.time,
                    'type': 'valuation_alert'
                }
                self._add_to_frequency_buffer('fmv', 'valuation_alerts', [valuation_alert])
                
                logger.info(f"DATA-PUB: Significant FMV deviation detected: {event.ticker} "
                           f"FMV:${event.fmv_price:.2f} vs Market:${event.market_price:.2f} "
                           f"({event.fmv_vs_market_pct:+.1f}%)")
    
    def _analyze_minute_aggregate_for_events(self, aggregate_event: PerMinuteAggregateEvent):
        """Analyze minute aggregate to detect significant events"""
        try:
            # Check for significant price movements in the minute
            if aggregate_event.minute_price_change_pct is not None:
                if abs(aggregate_event.minute_price_change_pct) >= 2.0:  # 2% threshold
                    # Create a trend event for significant minute moves
                    direction = 'up' if aggregate_event.minute_price_change_pct > 0 else 'down'
                    
                    trend_event = {
                        'ticker': aggregate_event.ticker,
                        'type': 'trend',
                        'price': aggregate_event.price,
                        'direction': direction,
                        'percent_change': aggregate_event.minute_price_change_pct,
                        'time': aggregate_event.time,
                        'source': 'minute_aggregate',
                        'minute_volume': aggregate_event.minute_volume,
                        'minute_range': aggregate_event.minute_range
                    }
                    
                    self._add_to_frequency_buffer_nested('per_minute', 'trending', direction, [trend_event])
            
            # Check for volume surges within the minute
            if (aggregate_event.minute_volume is not None and 
                aggregate_event.accumulated_volume is not None and 
                aggregate_event.accumulated_volume > 0):
                
                # Estimate average minute volume (rough approximation)
                # This could be enhanced with historical data
                estimated_avg_minute_volume = aggregate_event.accumulated_volume / 390  # ~6.5 hours of trading
                
                if aggregate_event.minute_volume > estimated_avg_minute_volume * 3:  # 3x volume surge
                    direction = 'up' if aggregate_event.minute_price_change and aggregate_event.minute_price_change > 0 else 'down'
                    
                    surge_event = {
                        'ticker': aggregate_event.ticker,
                        'type': 'surge',
                        'price': aggregate_event.price,
                        'direction': direction,
                        'volume': aggregate_event.minute_volume,
                        'rel_volume': aggregate_event.minute_volume / estimated_avg_minute_volume,
                        'time': aggregate_event.time,
                        'source': 'minute_aggregate'
                    }
                    
                    self._add_to_frequency_buffer_nested('per_minute', 'surging', direction, [surge_event])
                    
                    logger.info(f"DATA-PUB: Volume surge detected in minute aggregate: {aggregate_event.ticker} "
                               f"Vol:{aggregate_event.minute_volume:,} ({aggregate_event.minute_volume / estimated_avg_minute_volume:.1f}x)")
                    
        except Exception as e:
            logger.error(f"DATA-PUB: Error analyzing minute aggregate: {e}", exc_info=True)
    
    def _add_to_frequency_buffer(self, frequency: str, event_type: str, events: List):
        """Add events to frequency-specific buffer with overflow protection"""
        if frequency not in self.event_buffer:
            logger.error(f"DATA-PUB: Unknown frequency buffer: {frequency}")
            return
        
        if event_type not in self.event_buffer[frequency]:
            logger.error(f"DATA-PUB: Unknown event type {event_type} for frequency {frequency}")
            return
        
        current = self.event_buffer[frequency][event_type]
        if len(current) + len(events) > self.MAX_BUFFER_SIZE:
            # Remove oldest events
            remove_count = len(current) + len(events) - self.MAX_BUFFER_SIZE
            removed = current[:remove_count]
            self.event_buffer[frequency][event_type] = current[remove_count:]
            self.buffer_stats['buffer_overflows'] += remove_count
            logger.warning(f"⚠️ Buffer overflow for {frequency}/{event_type}, dropped {remove_count} events")
        
        self.event_buffer[frequency][event_type].extend(events)
    
    def _add_to_frequency_buffer_nested(self, frequency: str, event_type: str, direction: str, events: List):
        """Add events to nested frequency-specific buffer structure"""
        if (frequency not in self.event_buffer or 
            event_type not in self.event_buffer[frequency] or
            direction not in self.event_buffer[frequency][event_type]):
            logger.error(f"DATA-PUB: Invalid buffer path: {frequency}/{event_type}/{direction}")
            return
        
        current = self.event_buffer[frequency][event_type][direction]
        if len(current) + len(events) > self.MAX_BUFFER_SIZE:
            remove_count = len(current) + len(events) - self.MAX_BUFFER_SIZE
            self.event_buffer[frequency][event_type][direction] = current[remove_count:]
            self.buffer_stats['buffer_overflows'] += remove_count
            logger.warning(f"⚠️ Buffer overflow for {frequency}/{event_type}/{direction}, dropped {remove_count} events")
        
        self.event_buffer[frequency][event_type][direction].extend(events)
       
    def start_publishing_loop(self):
        """Start the publishing thread loop."""
        try:
            if self.publishing_active:
                logger.warning("⚠️DATA-PUB:  Publishing loop already active")
                return False
            
            self.publishing_active = True
            self.publisher_thread = threading.Thread(
                target=self._run_publisher_loop,
                daemon=True,
                name="data-publisher-loop"
            )
            self.publisher_thread.start()
            
            logger.info("✅DATA-PUB:  Publisher loop started")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start publishing loop: {e}", exc_info=True)
            self.publishing_active = False
            return False
    
    def stop_publishing_loop(self):
        """Stop the publishing thread loop."""
        try:
            self.publishing_active = False
            
            if self.publisher_thread and self.publisher_thread.is_alive():
                self.publisher_thread.join(timeout=2)
            
            logger.info("✅DATA-PUB:  Publisher loop stopped")
            
        except Exception as e:
            logger.error(f"❌ Error stopping publishing loop: {e}", exc_info=True)
    
    def _run_publisher_loop(self):
        """Main publishing loop."""
        last_publish_time = time.time()
        publish_interval = self.config.get('UPDATE_INTERVAL', 0.5)
        
        # DEBUG: Log loop startup
        logger.info(f"🔍 DATA-PUB-LOOP: Starting collection loop with {publish_interval}s interval")
        
        while self.publishing_active:
            try:
                current_time = time.time()
                time_since_publish = current_time - last_publish_time
                
                # DEBUG: Log timing details every few seconds
                loop_count = getattr(self, '_loop_count', 0)
                if loop_count % 100 == 0:  # Every ~1 second (0.01s * 100)
                    logger.info(f"🔍 DATA-PUB-TIMING: Loop #{loop_count}, time_since_publish={time_since_publish:.3f}s, interval={publish_interval}s")
                self._loop_count = loop_count + 1
                
                # Publish updates at regular intervals
                if time_since_publish >= publish_interval:
                    # DEBUG: Log collection attempt
                    logger.info(f"🔍 DATA-PUB-COLLECT: Starting collection cycle (interval: {publish_interval}s, elapsed: {time_since_publish:.3f}s)")
                    
                    publish_result = self.publish_to_users()
                    
                    if publish_result.success:
                        last_publish_time = time.time()
                        self._update_stats(publish_result)
                        
                        # DEBUG: Log successful collection
                        logger.info(f"🔍 DATA-PUB-COLLECT: Collection completed successfully")
                        
                        # Notify monitors/callbacks about successful collection
                        self._notify_collection_complete(publish_result)
                    else:
                        logger.warning(f"⚠️DATA-PUB: Publishing failed: {publish_result.errors}")
                    
                    # Log periodic stats (keep existing functionality)
                    if self.stats.should_log():
                        self.stats.log_stats()
                        self.check_data_flow_health()
                
                time.sleep(0.01)
                
            except Exception as e:
                logger.error(f"❌ Publisher loop error: {e}", exc_info=True)
                time.sleep(0.5)

    def _notify_collection_complete(self, publish_result):
        """Notify registered callbacks about collection completion"""
        # Increment collection counter for diagnostics
        if hasattr(self, 'collection_diagnostics'):
            self.collection_diagnostics['collections_attempted'] += 1
        
        # Notify all registered callbacks (including system monitor)
        for callback in self._collection_callbacks:
            try:
                callback({
                    'success': True,
                    'timestamp': time.time(),
                    'result': publish_result,
                    'collection_number': self.collection_diagnostics.get('collections_attempted', 0)
                })
            except Exception as e:
                logger.error(f"Collection callback error: {e}")

    def publish_to_users(self) -> PublishingResult:
        """
        SPRINT 29: Collects events from display queue and buffers them.
        No longer triggers emission - WebSocketPublisher will pull when ready.
        """
        start_time = time.time()
        result = PublishingResult(publishing_method="event_collection_only")
        
        try:
            self.stats.publish_attempts += 1

            # KEEP diagnostic logging
            if self.stats.publish_attempts % 10 == 1:
                queue_contents = self.market_service.priority_manager.diagnose_queue_contents()
                logger.info(f"🔍DATA-PUB-TO-USER: Queue contents before collection: {queue_contents}")
            
            # Get current session (KEEP)
            current_session = self.market_service.get_market_status()
            
            # TRACE: Collection start (KEEP but modify)
            if tracer.should_trace('SYSTEM'):
                tracer.trace(
                    ticker='SYSTEM',
                    component='DataPublisher',
                    action='collection_start',
                    data={
                        'timestamp': time.time(),
                        'queue_diagnostics': queue_contents if 'queue_contents' in locals() else {},
                        'location': "publish_to_users"
                    }
                )
            
            # Collect from queue (KEEP)
            recent_events = self._collect_display_events_from_queue()
            
            # DEBUG: Log what we got after collection
            if recent_events:
                highs = recent_events.get("highs", [])
                lows = recent_events.get("lows", [])
                trending = recent_events.get("trending", {'up': [], 'down': []})
                surging = recent_events.get("surging", {'up': [], 'down': []})
                total_collected = len(highs) + len(lows) + len(trending.get('up', [])) + len(trending.get('down', [])) + len(surging.get('up', [])) + len(surging.get('down', []))
                
                if total_collected > 0:
                    logger.info(f"🔍 DATAPUB-DEBUG: After processing collection - highs:{len(highs)}, lows:{len(lows)}, trends:{len(trending.get('up', []))+len(trending.get('down', []))}, surges:{len(surging.get('up', []))+len(surging.get('down', []))}")
                else:
                    logger.warning(f"🔍 DATAPUB-DEBUG: Collection processed but resulted in 0 categorized events")
            
            highs = recent_events.get("highs", [])
            lows = recent_events.get("lows", [])
            trending = recent_events.get("trending", {'up': [], 'down': []})
            surging = recent_events.get("surging", {'up': [], 'down': []})
            other_types = recent_events.get("other_types", {})

            # Calculate counts (KEEP)
            high_count = len(highs)
            low_count = len(lows)
            trend_count = len(trending.get('up', [])) + len(trending.get('down', []))
            surge_count = len(surging.get('up', [])) + len(surging.get('down', []))
            total_event_count = high_count + low_count + trend_count + surge_count

            # TRACE: Events collected (KEEP)
            if tracer.should_trace('SYSTEM') and total_event_count > 0:
                tracer.trace(
                    ticker='SYSTEM',
                    component='DataPublisher',
                    action='events_collected',
                    data={
                        'timestamp': time.time(),
                        'input_count': ensure_int(total_event_count),
                        'output_count': ensure_int(total_event_count),
                        'duration_ms': 0,
                        'details': {
                            'event_breakdown': {
                                'highs': ensure_int(high_count),
                                'lows': ensure_int(low_count),
                                'trends': ensure_int(trend_count),
                                'surges': ensure_int(surge_count)
                            },
                            'source': 'display_queue',
                            'total': ensure_int(total_event_count)
                        }
                    }
                )

            # Add to buffer with overflow protection (KEEP)
            with self.buffer_lock:
                self._add_to_buffer('highs', highs)
                self._add_to_buffer('lows', lows)
                for direction in ['up', 'down']:
                    self._add_to_buffer_nested('trending', direction, trending.get(direction, []))
                    self._add_to_buffer_nested('surging', direction, surging.get(direction, []))
                
                # SPRINT 29: Track events buffered
                self.buffer_stats['events_buffered'] += total_event_count
            
            # Log collection stats (MODIFY)
            if total_event_count > 0:
                logger.info(f"📦 DATA-PUB: Collected {total_event_count} events into buffer "
                        f"(H:{high_count} L:{low_count} T:{trend_count} S:{surge_count})")
                
            # TRACE: Events buffered (KEEP)
            if tracer.should_trace('SYSTEM'):
                tracer.trace(
                    ticker='SYSTEM',
                    component='DataPublisher',
                    action='events_buffered',
                    data={
                        'timestamp': time.time(),
                        'input_count': 0,
                        'output_count': total_event_count,
                        'details': {
                            'highs': high_count,
                            'lows': low_count,
                            'trends': trend_count,
                            'surges': surge_count,
                            'total': total_event_count,
                            'buffer_size_after': self.get_buffer_status()['total']
                        }
                    }
                )
            
            # Update result
            result.success = True
            result.events_published = total_event_count  # Actually buffered, not published
            
            # FIX: Set users_reached based on WebSocket connection status
            # This prevents the "No users connected" warning in pull model
            if self.websocket_publisher and hasattr(self.websocket_publisher, 'get_user_count'):
                result.users_reached = self.websocket_publisher.get_user_count()
            else:
                # Assume users are connected if we're buffering events
                result.users_reached = 1 if total_event_count > 0 else 0
            
            self.stats.publish_successes += 1
            
            return result
            
        except Exception as e:
            error_msg = f"Collection error: {e}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            result.success = False
            result.errors.append(error_msg)
            return result
        finally:
            result.processing_time_ms = (time.time() - start_time) * 1000
            if result.processing_time_ms > 750:  # Lower threshold for collection
                logger.warning(f"⚠️ DATA-PUB: Slow collection (750ms or greater): {result.processing_time_ms:.1f}ms")
    

    def _add_to_buffer(self, event_type: str, events: List):
        """Legacy method - add events to per-second buffer for backward compatibility."""
        self._add_to_frequency_buffer('per_second', event_type, events)

    def _add_to_buffer_nested(self, event_type: str, direction: str, events: List):
        """Legacy method - add events to per-second nested buffer for backward compatibility."""
        self._add_to_frequency_buffer_nested('per_second', event_type, direction, events)

    def get_buffered_events(self, clear_buffer: bool = True, frequencies: Optional[List[FrequencyType]] = None) -> Dict:
        """
        SPRINT 101: Called by WebSocketPublisher to retrieve buffered events.
        Returns events from specified frequencies and optionally clears buffer.
        
        Args:
            clear_buffer: Whether to clear the buffer after retrieval
            frequencies: List of frequencies to retrieve. If None, retrieves all enabled frequencies.
        """
        # FIX: Use timeout lock to prevent deadlock with collection thread
        lock_acquired = self.buffer_lock.acquire(timeout=2.0)  # 2 second timeout
        if not lock_acquired:
            logger.warning("🔍 BUFFER-DEBUG: Failed to acquire buffer lock within 2s, returning empty events")
            return {'frequencies': {}}
            
        try:
            # Determine which frequencies to retrieve
            target_frequencies = frequencies or list(self.enabled_frequencies)
            
            # DEBUG: Log frequency retrieval (avoid double locking - calculate sizes directly)
            per_second_total = (len(self.event_buffer['per_second']['highs']) + 
                              len(self.event_buffer['per_second']['lows']) +
                              len(self.event_buffer['per_second']['trending']['up']) +
                              len(self.event_buffer['per_second']['trending']['down']) +
                              len(self.event_buffer['per_second']['surging']['up']) +
                              len(self.event_buffer['per_second']['surging']['down']))
            
            logger.info(f"🔍 BUFFER-DEBUG: Retrieving {per_second_total} events from buffer")
            
            # Initialize response structure with multi-frequency support
            events = {
                # Maintain backward compatibility - per-second events at root level
                'highs': [],
                'lows': [],
                'trending': {'up': [], 'down': []},
                'surging': {'up': [], 'down': []},
                # New multi-frequency structure
                'frequencies': {}
            }
            
            total_events = 0
            
            for frequency_type in target_frequencies:
                frequency_key = frequency_type.value
                frequency_events = {}
                
                
                if frequency_type == FrequencyType.PER_SECOND:
                    # Copy per-second events to both root level (backward compatibility) and frequency structure
                    per_second_buffer = self.event_buffer['per_second']
                    frequency_events = {
                        'highs': per_second_buffer['highs'][:],
                        'lows': per_second_buffer['lows'][:],
                        'trending': {
                            'up': per_second_buffer['trending']['up'][:],
                            'down': per_second_buffer['trending']['down'][:]
                        },
                        'surging': {
                            'up': per_second_buffer['surging']['up'][:],
                            'down': per_second_buffer['surging']['down'][:]
                        }
                    }
                    
                    # Maintain backward compatibility by copying to root level
                    events['highs'] = frequency_events['highs'][:]
                    events['lows'] = frequency_events['lows'][:]
                    events['trending'] = {
                        'up': frequency_events['trending']['up'][:],
                        'down': frequency_events['trending']['down'][:]
                    }
                    events['surging'] = {
                        'up': frequency_events['surging']['up'][:],
                        'down': frequency_events['surging']['down'][:]
                    }
                
                elif frequency_type == FrequencyType.PER_MINUTE:
                    per_minute_buffer = self.event_buffer['per_minute']
                    frequency_events = {
                        'aggregates': per_minute_buffer['aggregates'][:],
                        'highs': per_minute_buffer['highs'][:],
                        'lows': per_minute_buffer['lows'][:],
                        'trending': {
                            'up': per_minute_buffer['trending']['up'][:],
                            'down': per_minute_buffer['trending']['down'][:]
                        },
                        'surging': {
                            'up': per_minute_buffer['surging']['up'][:],
                            'down': per_minute_buffer['surging']['down'][:]
                        }
                    }
                
                elif frequency_type == FrequencyType.FAIR_MARKET_VALUE:
                    fmv_buffer = self.event_buffer['fmv']
                    frequency_events = {
                        'fmv_events': fmv_buffer['fmv_events'][:],
                        'valuation_alerts': fmv_buffer['valuation_alerts'][:]
                    }
                
                # Add to frequencies structure
                events['frequencies'][frequency_key] = frequency_events
                
                # Count events for this frequency
                frequency_count = self._count_frequency_events(frequency_events)
                total_events += frequency_count
            

            # Clear buffer if requested
            if clear_buffer and total_events > 0:
                for frequency_type in target_frequencies:
                    self._clear_frequency_buffer(frequency_type)
                
                # Update delivery stats
                self.buffer_stats['events_delivered'] += total_events
                self.buffer_stats['last_buffer_clear'] = time.time()
                
                # Update frequency-specific delivery stats
                for frequency_type in target_frequencies:
                    frequency_key = frequency_type.value
                    if frequency_key in events['frequencies']:
                        freq_count = self._count_frequency_events(events['frequencies'][frequency_key])
                        self.buffer_stats['frequency_breakdown'][frequency_key]['delivered'] += freq_count
                
                logger.debug(f"📤 Multi-frequency event buffer cleared: delivered {total_events} events from {len(target_frequencies)} frequencies")
            elif clear_buffer and total_events == 0:
                logger.info("🔍 DATA-PUB-DEBUG: Not clearing buffer because total_events == 0")
                
                # Trace buffer pull with multi-frequency details
                if tracer.should_trace('SYSTEM'):
                    trace_details = {
                        'buffer_cleared': True,
                        'frequencies_retrieved': [f.value for f in target_frequencies],
                        'per_second_events': 0,
                        'per_minute_events': 0,
                        'fmv_events': 0
                    }
                    
                    # Count events by frequency for tracing
                    for freq_key, freq_events in events['frequencies'].items():
                        freq_count = self._count_frequency_events(freq_events)
                        if freq_key == FrequencyType.PER_SECOND.value:
                            trace_details['per_second_events'] = freq_count
                        elif freq_key == FrequencyType.PER_MINUTE.value:
                            trace_details['per_minute_events'] = freq_count
                        elif freq_key == FrequencyType.FAIR_MARKET_VALUE.value:
                            trace_details['fmv_events'] = freq_count
                    
                    tracer.trace(
                        ticker='SYSTEM',
                        component='DataPublisher',
                        action='multi_frequency_buffer_pulled',
                        data={
                            'timestamp': time.time(),
                            'input_count': total_events,
                            'output_count': total_events,
                            'details': trace_details
                        }
                    )
            
            if total_events > 0:
                logger.info(f"🔍 BUFFER-DEBUG: Returning {total_events} events to WebSocket publisher")
            return events
        finally:
            # Always release the lock
            self.buffer_lock.release()
    
    def _count_frequency_events(self, frequency_events: Dict) -> int:
        """Count total events in a frequency-specific event dictionary"""
        count = 0
        for key, value in frequency_events.items():
            if isinstance(value, list):
                count += len(value)
            elif isinstance(value, dict):
                # Handle nested structures like trending/surging
                for nested_key, nested_value in value.items():
                    if isinstance(nested_value, list):
                        count += len(nested_value)
        return count
    
    def _clear_frequency_buffer(self, frequency_type: FrequencyType):
        """Clear buffer for a specific frequency type"""
        frequency_key = frequency_type.value
        
        if frequency_type == FrequencyType.PER_SECOND:
            self.event_buffer['per_second'] = {
                'highs': [],
                'lows': [],
                'trending': {'up': [], 'down': []},
                'surging': {'up': [], 'down': []}
            }
        elif frequency_type == FrequencyType.PER_MINUTE:
            self.event_buffer['per_minute'] = {
                'aggregates': [],
                'highs': [],
                'lows': [],
                'trending': {'up': [], 'down': []},
                'surging': {'up': [], 'down': []}
            }
        elif frequency_type == FrequencyType.FAIR_MARKET_VALUE:
            self.event_buffer['fmv'] = {
                'fmv_events': [],
                'valuation_alerts': []
            }
            
    def get_buffer_status(self) -> Dict:
        """Returns current buffer sizes for monitoring with multi-frequency support."""
        with self.buffer_lock:
            # Calculate per-frequency buffer sizes
            per_second_sizes = {
                'highs': len(self.event_buffer['per_second']['highs']),
                'lows': len(self.event_buffer['per_second']['lows']),
                'trends_up': len(self.event_buffer['per_second']['trending']['up']),
                'trends_down': len(self.event_buffer['per_second']['trending']['down']),
                'surges_up': len(self.event_buffer['per_second']['surging']['up']),
                'surges_down': len(self.event_buffer['per_second']['surging']['down'])
            }
            per_second_total = sum(per_second_sizes.values())
            
            per_minute_sizes = {
                'aggregates': len(self.event_buffer['per_minute']['aggregates']),
                'highs': len(self.event_buffer['per_minute']['highs']),
                'lows': len(self.event_buffer['per_minute']['lows']),
                'trends_up': len(self.event_buffer['per_minute']['trending']['up']),
                'trends_down': len(self.event_buffer['per_minute']['trending']['down']),
                'surges_up': len(self.event_buffer['per_minute']['surging']['up']),
                'surges_down': len(self.event_buffer['per_minute']['surging']['down'])
            }
            per_minute_total = sum(per_minute_sizes.values())
            
            fmv_sizes = {
                'fmv_events': len(self.event_buffer['fmv']['fmv_events']),
                'valuation_alerts': len(self.event_buffer['fmv']['valuation_alerts'])
            }
            fmv_total = sum(fmv_sizes.values())
            
            total_all_frequencies = per_second_total + per_minute_total + fmv_total
            
            # Maintain backward compatibility for existing monitoring
            status = {
                # Legacy format (per-second data for backward compatibility)
                'highs': per_second_sizes['highs'],
                'lows': per_second_sizes['lows'],
                'trends_up': per_second_sizes['trends_up'],
                'trends_down': per_second_sizes['trends_down'],
                'surges_up': per_second_sizes['surges_up'],
                'surges_down': per_second_sizes['surges_down'],
                'total': total_all_frequencies,  # Total across all frequencies
                
                # New multi-frequency detailed breakdown
                'frequencies': {
                    FrequencyType.PER_SECOND.value: {
                        'sizes': per_second_sizes,
                        'total': per_second_total
                    },
                    FrequencyType.PER_MINUTE.value: {
                        'sizes': per_minute_sizes,
                        'total': per_minute_total
                    },
                    FrequencyType.FAIR_MARKET_VALUE.value: {
                        'sizes': fmv_sizes,
                        'total': fmv_total
                    }
                },
                
                # Enhanced statistics
                'stats': self.buffer_stats,
                'enabled_frequencies': [f.value for f in self.enabled_frequencies],
                'max_buffer_size_per_type': self.MAX_BUFFER_SIZE
            }
            
            # Check buffer health AFTER getting status (avoid circular call)
            if tracer.should_trace('SYSTEM'):
                total = status['total']
                usage_percent = (total / self.MAX_BUFFER_SIZE) * 100 if self.MAX_BUFFER_SIZE > 0 else 0
                
                if usage_percent > 80:  # 80% full
                    tracer.trace(
                        ticker='SYSTEM',
                        component='DataPublisher',
                        action='buffer_near_capacity',
                        data={
                            'timestamp': time.time(),
                            'input_count': total,
                            'output_count': total,
                            'details': {
                                'buffer_usage_percent': usage_percent,
                                'buffer_counts': {
                                    'highs': status['highs'],
                                    'lows': status['lows'],
                                    'trends': status['trends_up'] + status['trends_down'],
                                    'surges': status['surges_up'] + status['surges_down']
                                },
                                'max_buffer_size': self.MAX_BUFFER_SIZE
                            }
                        }
                    )
            
            try:
                from src.monitoring.system_monitor import system_monitor
                if status['total'] > self.MAX_BUFFER_SIZE * 0.8:
                    if hasattr(system_monitor, 'track_buffer_warning'):
                        system_monitor.track_buffer_warning(status['total'], self.MAX_BUFFER_SIZE)
            except:
                pass  # Don't break if monitoring not available

            return status

    def _collect_display_events_from_queue(self) -> Dict[str, List]:
        """Collect all display events from display queue (not priority queue)."""
        try:
            collection_start = time.time()
            events = []
            
            # Track collection attempt
            self.collection_diagnostics['collections_attempted'] += 1
            
            # Check if display queue exists
            if not hasattr(self.market_service, 'display_queue'):
                logger.error("❌ Display queue not initialized!")
                return {'highs': [], 'lows': [], 'trending': {'up': [], 'down': []}, 'surging': {'up': [], 'down': []}}
            
            # Get queue size before collection
            queue_size_before = self.market_service.display_queue.qsize()
            
            # DEBUG: Log collection attempt
            if queue_size_before > 0:
                logger.info(f"🔍 DATAPUB-DEBUG: Starting collection from display_queue with {queue_size_before} events")
            
            # Collect with timeout to prevent blocking
            deadline = time.time() + self.collection_timeout
            
            while time.time() < deadline and len(events) < self.collection_max_events:
                try:
                    remaining_timeout = deadline - time.time()
                    if remaining_timeout <= 0:
                        break
                    
                    # Get event with small timeout to check multiple times
                    event = self.market_service.display_queue.get(
                        block=True, 
                        timeout=min(remaining_timeout, 0.01)
                    )
                    events.append(event)
                    
                    # DEBUG: Log collected event
                    if len(events) <= 10:  # Only log first 10 to avoid spam
                        event_type = event[0] if isinstance(event, tuple) and len(event) > 0 else 'unknown'
                        logger.info(f"🔍 DATAPUB-DEBUG: Collected event #{len(events)}: {event_type}")
                    
                    # Update statistics
                    self.market_service.display_queue_stats['events_collected'] += 1
                    
                except Exception as e:
                    # Handle both standard queue.Empty and eventlet's _queue.Empty
                    if e.__class__.__name__ == 'Empty':
                        # No more events available, continue to check until deadline
                        continue
                    else:
                        # Re-raise if it's a different exception
                        raise
            
            # Get queue size after collection
            queue_size_after = self.market_service.display_queue.qsize()
            
            # DEBUG: Log collection completion
            events_collected = len(events)
            if queue_size_before > 0 or events_collected > 0:
                logger.info(f"🔍 DATAPUB-DEBUG: Collection completed - queue_before={queue_size_before}, collected={events_collected}, queue_after={queue_size_after}")
            
            # Update diagnostics
            if events_collected == 0:
                self.collection_diagnostics['empty_collections'] += 1
            
            self.collection_diagnostics['events_collected_total'] += events_collected
            self.collection_diagnostics['collection_sizes'].append(events_collected)
            if len(self.collection_diagnostics['collection_sizes']) > 1000:
                self.collection_diagnostics['collection_sizes'].pop(0)
            
            collection_time = (time.time() - collection_start) * 1000
            self.collection_diagnostics['collection_times_ms'].append(collection_time)
            if len(self.collection_diagnostics['collection_times_ms']) > 1000:
                self.collection_diagnostics['collection_times_ms'].pop(0)
            
            # Log collection results
            logger.info(f"📦 DATA-PUB-COLLECT: Collected {events_collected} events from DISPLAY queue "
                    f"(was {queue_size_before}, now {queue_size_after}, took {collection_time:.1f}ms)")
            
            # Sort events by type
            highs = []
            lows = []
            trending = {'up': [], 'down': []}
            surging = {'up': [], 'down': []}
            
            for event_type, event_data in events:
                # SPRINT 29: All events should now be dicts from worker_pool
                if not isinstance(event_data, dict):
                    logger.warning(f"Expected dict for {event_type}, got {type(event_data)}")
                    continue
                # TRACE: Event prepared for emission
                if hasattr(event_data, 'ticker') and tracer.should_trace(event_data.ticker):
                    tracer.trace(
                        ticker=event_data.ticker,
                        component="DataPublisher",
                        action="display_queue_collected",
                        data={
                            'timestamp': time.time(),
                            'input_count': ensure_int(1),
                            'output_count': ensure_int(1),
                            'duration_ms': ensure_int(0),
                            'details': {
                                "event_type": event_type,
                                "age_seconds": time.time() - event_data.time if hasattr(event_data, 'time') else 0,
                                "collection_batch": self.collection_diagnostics['collections_attempted'],
                                'event_id': getattr(event_data, 'event_id', None)
                            }
                        }
                    )
                
                # Sort by type - all events are dicts now
                if event_type in ['high', 'session_high']:
                    highs.append(event_data)
                elif event_type in ['low', 'session_low']:
                    lows.append(event_data)
                elif event_type == 'trend':
                    direction = 'up' if event_data.get('direction') in ['↑', 'up'] else 'down'
                    trending[direction].append(event_data)  
                elif event_type == 'surge':
                    direction = 'up' if event_data.get('direction') in ['↑', 'up'] else 'down'
                    surging[direction].append(event_data)  
            
            # Log results by type
            if events_collected > 0:
                logger.info(f"📊 Display Queue Collection: {len(highs)}H {len(lows)}L "
                        f"{len(trending['up'])+len(trending['down'])}T "
                        f"{len(surging['up'])+len(surging['down'])}S")
                
                # Special logging for surge events
                if len(surging['up']) + len(surging['down']) > 0:
                    logger.info(f"🚀 DATA-PUB: Collected {len(surging['up'])+len(surging['down'])} "
                            f"surge events from display queue!")
            
            # TRACE: Collection summary
            if tracer.should_trace('SYSTEM'):
                tracer.trace(
                    ticker='SYSTEM',
                    component="DataPublisher",
                    action="display_collection_complete",
                    data={
                        'timestamp': time.time(),
                        'input_count': ensure_int(queue_size_before),
                        'output_count': ensure_int(events_collected),
                        'duration_ms': collection_time,
                        'details': {
                            "highs": ensure_int(len(highs)),
                            "lows": ensure_int(len(lows)),
                            "trends": ensure_int(len(trending['up']) + len(trending['down'])),
                            "surges": ensure_int(len(surging['up']) + len(surging['down'])),
                            "queue_remaining": ensure_int(queue_size_after),
                            "collection_efficiency": f"{(events_collected/queue_size_before*100):.1f}%" if queue_size_before > 0 else "N/A"
                        }
                    }
                )
            
            return {
                'highs': highs,
                'lows': lows,
                'trending': trending,
                'surging': surging
            }
            
        except Exception as e:
            logger.error(f"❌ Error collecting from display queue: {e}", exc_info=True)
            
            # TRACE: Error
            if tracer.should_trace('SYSTEM'):
                tracer.trace(
                    ticker='SYSTEM',
                    component="DataPublisher",
                    action="display_collection_error",
                    data={
                        'timestamp': time.time(),
                        'input_count': ensure_int(0),
                        'output_count': ensure_int(0),
                        'duration_ms': (time.time() - collection_start) * 1000 if 'collection_start' in locals() else 0,
                        'error': str(e),
                        'details': {
                            'error_type': type(e).__name__
                        }
                    }
                )
            
            return {'highs': [], 'lows': [], 'trending': {'up': [], 'down': []}, 'surging': {'up': [], 'down': []}}
        
    def _create_trend_lookups(self, trending_stocks: Dict, surging_stocks: List) -> Dict:
        """Create lookup dictionaries for efficient flag assignment."""
        return {
            'up_trending': {stock['ticker']: stock for stock in trending_stocks.get('up_trending', [])},
            'down_trending': {stock['ticker']: stock for stock in trending_stocks.get('down_trending', [])},
            'up_surging': {stock['ticker']: stock for stock in surging_stocks if stock['direction'] == 'up'},
            'down_surging': {stock['ticker']: stock for stock in surging_stocks if stock['direction'] == 'down'}
        }

    def _update_stats(self, publish_result: PublishingResult):
        """Update flow statistics."""
        if publish_result.success:
            self.stats.users_reached += publish_result.users_reached
            self.stats.events_sent += publish_result.events_published
    
    def check_data_flow_health(self):
        """Diagnose where data flow is breaking."""
        if self.stats.publish_attempts == 0:
            logger.error("🚨 DATA-PUB: NO PUBLISH ATTEMPTS - Check publisher thread")
        elif self.stats.publish_successes == 0:
            logger.error("🚨 DATA-PUB: All publishes failing - Check WebSocket connections")
        elif self.stats.users_reached == 0:
            logger.warning(f"⚠️ DATA-PUB: No users connected after {self.stats.publish_attempts} publish attempts")
        elif self.stats.events_sent == 0:
            logger.error("🚨 DATA-PUB: Publishing but NO EVENTS SENT - Check event detection")
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report including buffer status."""
        try:
            buffer_status = self.get_buffer_status()
            return {
                'publishing_active': self.publishing_active,
                'stats': {
                    'publish_attempts': self.stats.publish_attempts,
                    'publish_successes': self.stats.publish_successes,
                    'users_reached': self.stats.users_reached,
                    'events_sent': self.stats.events_sent
                },
                'buffer': {
                    'current_size': buffer_status['total'],
                    'details': buffer_status,
                    'stats': self.buffer_stats
                },
                'thread_alive': self.publisher_thread.is_alive() if self.publisher_thread else False,
                'last_publish_time': self.last_publish_time,
                'timestamp': time.time()
            }
        except Exception as e:
            logger.error(f"❌ Error generating performance report: {e}")
            return {'error': str(e)}




    
    #----------------------------------------------------------------------------------------------
    # DIAGNOSTICS
    # enabled with tracing valueble collection state and status
    # DIAGNOSTICS CONTROLLED BY TRACE ENABLED FLAG
    #----------------------------------------------------------------------------------------------
    def get_diagnostics_collection_diagnostics(self) -> Dict[str, Any]:
        """Sprint 26: Get detailed collection diagnostics."""
        avg_collection_time = 0
        if self.collection_diagnostics['collection_times_ms']:
            avg_collection_time = sum(self.collection_diagnostics['collection_times_ms']) / len(self.collection_diagnostics['collection_times_ms'])
        
        avg_collection_size = 0
        if self.collection_diagnostics['collection_sizes']:
            avg_collection_size = sum(self.collection_diagnostics['collection_sizes']) / len(self.collection_diagnostics['collection_sizes'])
        
        avg_queue_before = 0
        if self.collection_diagnostics['queue_sizes_before']:
            avg_queue_before = sum(self.collection_diagnostics['queue_sizes_before']) / len(self.collection_diagnostics['queue_sizes_before'])
        
        return {
            'collections_attempted': self.collection_diagnostics['collections_attempted'],
            'events_collected_total': self.collection_diagnostics['events_collected_total'],
            'events_lost_in_collection': self.collection_diagnostics['events_lost_in_collection'],
            'empty_collections': self.collection_diagnostics['empty_collections'],
            'empty_collection_rate': round((self.collection_diagnostics['empty_collections'] / 
                                        self.collection_diagnostics['collections_attempted'] * 100)
                                        if self.collection_diagnostics['collections_attempted'] > 0 else 0, 2),
            'avg_collection_time_ms': round(avg_collection_time, 1),
            'avg_collection_size': round(avg_collection_size, 1),
            'avg_queue_size_before': round(avg_queue_before, 1),
            'collection_efficiency': round((self.collection_diagnostics['events_collected_total'] / 
                                        (self.collection_diagnostics['events_collected_total'] + 
                                        self.collection_diagnostics['events_lost_in_collection']) * 100)
                                        if (self.collection_diagnostics['events_collected_total'] + 
                                            self.collection_diagnostics['events_lost_in_collection']) > 0 else 0, 2)
        }

    def register_collection_callback(self, callback: Callable):
        """Register callback to be called after each collection"""
        self._collection_callbacks.append(callback)

    def _run_publisher_loop(self):
        """Main publishing loop - SIMPLIFIED"""
        last_publish_time = time.time()
        publish_interval = self.config.get('UPDATE_INTERVAL', 0.5)
        
        # DEBUG: Log loop startup
        logger.info(f"🔍 DATA-PUB-LOOP: Starting SIMPLIFIED collection loop with {publish_interval}s interval")
        
        while self.publishing_active:
            try:
                current_time = time.time()
                time_since_publish = current_time - last_publish_time
                
                # DEBUG: Log timing details every few seconds
                loop_count = getattr(self, '_loop_count', 0)
                if loop_count % 100 == 0:  # Every ~1 second (0.01s * 100)
                    logger.info(f"🔍 DATA-PUB-TIMING: SIMPLIFIED Loop #{loop_count}, time_since_publish={time_since_publish:.3f}s, interval={publish_interval}s")
                self._loop_count = loop_count + 1
                
                # Publish updates at regular intervals
                if time_since_publish >= publish_interval:
                    # DEBUG: Log collection attempt
                    logger.info(f"🔍 DATA-PUB-COLLECT: SIMPLIFIED Starting collection cycle (interval: {publish_interval}s, elapsed: {time_since_publish:.3f}s)")
                    
                    publish_result = self.publish_to_users()
                    
                    if publish_result.success:
                        last_publish_time = time.time()
                        self._update_stats(publish_result)
                        
                        # DEBUG: Log successful collection
                        logger.info(f"🔍 DATA-PUB-COLLECT: SIMPLIFIED Collection completed successfully")
                        
                        # Notify callbacks (monitor will handle diagnostics)
                        for callback in self._collection_callbacks:
                            try:
                                callback({
                                    'success': True,
                                    'timestamp': current_time,
                                    'result': publish_result
                                })
                            except Exception as e:
                                logger.error(f"Collection callback error: {e}")
                    else:
                        logger.warning(f"⚠️DATA-PUB: Publishing failed: {publish_result.errors}")
                    
                    # Log periodic stats (keep existing functionality)
                    if self.stats.should_log():
                        self.stats.log_stats()
                        self.check_data_flow_health()
                
                time.sleep(0.01)
                
            except Exception as e:
                logger.error(f"❌ Publisher loop error: {e}", exc_info=True)
                time.sleep(0.5)
    def _log_verbose_collection_initial(self):
        """Initialize Sprint 27 verification tracking"""
        self.process_collection_verification['start_time'] = time.time()
        self.process_collection_verification['initial_stats'] = {
            'queue_size': self.market_service.priority_manager.event_queue.qsize(),
            'events_collected': self.collection_diagnostics['events_collected_total'],
            'collections_attempted': self.collection_diagnostics['collections_attempted'],
            'events_lost': self.collection_diagnostics['events_lost_in_collection']
        }
        
        logger.info(f"🔍 PROCESS-COLLECTION-DIAG: INITIAL STATE CAPTURED: - "
                    f"Queue: {self.process_collection_verification['initial_stats']['queue_size']}, "
                    f"Collected: {self.process_collection_verification['initial_stats']['events_collected']}")

    
    def _log_verbose_collection_efficiency(self):
        """
        enabled with tracing valueble collection state and status
        Check Sprint 27 verification progress
        
        """
        if not self.process_collection_verification['start_time']:
            return
            
        elapsed_time = time.time() - self.process_collection_verification['start_time']
        progress_percent = (elapsed_time / self.process_collection_verification['verification_duration']) * 100
        
        # Calculate current efficiency
        current_stats = {
            'events_collected': self.collection_diagnostics['events_collected_total'],
            'events_lost': self.collection_diagnostics['events_lost_in_collection']
        }
        
        events_collected_delta = current_stats['events_collected'] - self.process_collection_verification['initial_stats']['events_collected']
        events_lost_delta = current_stats['events_lost'] - self.process_collection_verification['initial_stats']['events_lost']
        
        if events_collected_delta + events_lost_delta > 0:
            current_efficiency = (events_collected_delta / (events_collected_delta + events_lost_delta)) * 100
        else:
            current_efficiency = 0
        
        logger.info(f"🔍 PROCESS-COLLECTION-DIAG: PROGRESS UPDATE: {progress_percent:.1f}% complete | "
                    f"Current efficiency: {current_efficiency:.1f}% | "
                    f"Events collected: {events_collected_delta:,} | Lost: {events_lost_delta:,}")
        
        # DIAGNOSTICS CONTROLLED BY TRACE ENABLED FLAG Check if verification period is complete
        if elapsed_time >= self.process_collection_verification['verification_duration']:
            self._log_verbose_collection_verification()

    
    def _log_verbose_collection_verification(self):
        """Complete Sprint 27 verification and report results"""
        if self.process_collection_verification['verification_complete']:
            return
            
        self.process_collection_verification['verification_complete'] = True
        
        # Calculate final results
        initial = self.process_collection_verification['initial_stats']
        final_stats = {
            'events_collected': self.collection_diagnostics['events_collected_total'],
            'collections_attempted': self.collection_diagnostics['collections_attempted'],
            'events_lost': self.collection_diagnostics['events_lost_in_collection']
        }
        
        total_events_collected = final_stats['events_collected'] - initial['events_collected']
        total_collections = final_stats['collections_attempted'] - initial['collections_attempted']
        events_lost = final_stats['events_lost'] - initial['events_lost']
        
        if total_collections > 0:
            avg_collection_size = total_events_collected / total_collections
            efficiency = (total_events_collected / (total_events_collected + events_lost)) * 100 if (total_events_collected + events_lost) > 0 else 0
            
            logger.info("=" * 80)
            logger.info("📊 PROCESS-COLLECTION-DIAG: VERIFICATION RESULTS: ")
            logger.info("=" * 80)
            logger.info(f"Collection Efficiency: {efficiency:.1f}%")
            logger.info(f"Average Collection Size: {avg_collection_size:.1f} events")
            logger.info(f"Total Events Collected: {total_events_collected:,}")
            logger.info(f"Events Lost: {events_lost:,}")
            logger.info("=" * 80)
            
            if efficiency < 70:
                logger.error(f"❌ PROCESS-COLLECTION-DIAG: FAILED: - Expected >70% efficiency, got {efficiency:.1f}%")
            else:
                logger.info(f"✅ PROCESS-COLLECTION-DIAG: SUCCESS: Improved efficiency check >70% actual percent: {efficiency:.1f}%!")
        else:
            logger.error("❌ PROCESS-COLLECTION-DIAG: FAILED: - No collections occurred")
    #----------------------------------------------------------------------------------------------
    #----------------------------------------------------------------------------------------------