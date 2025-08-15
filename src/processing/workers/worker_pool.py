"""
Worker Pool Management - Phase 4 Implementation
Handles worker pool lifecycle, event distribution, and dynamic scaling.
SPRINT 21 PHASE 4: Pure typed event system
"""

import logging
import time
import threading
import queue
from typing import Dict, List, Any, Optional
from collections import defaultdict
from dataclasses import dataclass

from src.core.domain.events.base import BaseEvent
from src.core.domain.events.highlow import HighLowEvent
from src.core.domain.events.trend import TrendEvent
from src.core.domain.events.surge import SurgeEvent
from src.core.domain.market.tick import TickData
from src.presentation.converters.models import StockData

from src.monitoring.tracer import tracer, TraceLevel, normalize_event_type, ensure_int

from config.logging_config import get_domain_logger, LogDomain

logger = get_domain_logger(LogDomain.CORE, 'worker_pool')

class DataFlowStats:
    def __init__(self):
        self.events_received = 0
        self.events_processed = 0
        self.events_failed = 0
        self.workers_active = 0
        self.last_log_time = time.time()
        self.log_interval = 30  # seconds
        
    def should_log(self):
        return time.time() - self.last_log_time >= self.log_interval
        
    def log_stats(self):
        logger.info(f"📊 WORKER FLOW: Workers:{self.workers_active} | "
                   f"Events In:{self.events_received} → Processed:{self.events_processed} → "
                   f"Failed:{self.events_failed}")
        self.last_log_time = time.time()

@dataclass
class WorkerPoolOperationResult:
    """Result object for worker pool operations."""
    success: bool = True
    workers_affected: int = 0
    current_pool_size: int = 0
    queue_sizes: List[int] = None
    errors: List[str] = None
    warnings: List[str] = None
    processing_time_ms: float = 0.0
    operation_type: str = "unknown"
    
    def __post_init__(self):
        if self.queue_sizes is None:
            self.queue_sizes = []
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


class StopEvent(BaseEvent):
    """Event to signal worker shutdown."""
    
    def __init__(self):
        """Initialize stop event with required BaseEvent fields."""
        # Initialize parent class with required fields
        super().__init__(
            ticker='CONTROL',
            type='stop',
            price=0.0  # Stop events don't need a price
        )
        self.time = time.time()
        self.priority = 0  # Highest priority
    
    def validate(self) -> bool:
        """Stop events are always valid."""
        return True
    
    def get_event_specific_data(self) -> Dict[str, Any]:
        """Return stop-specific data."""
        return {
            'command': 'stop',
            'timestamp': self.time
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            'type': self.type,
            'ticker': self.ticker,
            'time': self.time,
            'price': self.price,
            'command': 'stop'
        }
    
    def to_transport_dict(self) -> Dict[str, Any]:
        """Stop events don't need transport formatting."""
        return self.to_dict()
    
class WorkerPoolManager:
    """
    Manages worker pool and event queue distribution.
    PHASE 4: Pure typed event processing
    """
    # Default configuration values
    DEFAULT_WORKER_POOL_SIZE = 12
    DEFAULT_MIN_WORKER_POOL_SIZE = 8  
    DEFAULT_MAX_WORKER_POOL_SIZE = 16
    DEFAULT_WORKER_EVENT_BATCH_SIZE = 500
    DEFAULT_WORKER_COLLECTION_TIMEOUT = 0.5
    DEFAULT_WORKER_SCALING_THRESHOLD = 100
    
    def __init__(self, config, market_service, event_processor=None, priority_manager=None):
        """Initialize worker pool manager."""
        init_start_time = time.time()
        
        self.config = self._extract_worker_pool_config(config)
        self.market_service = market_service
        
        # Dependencies
        self.event_processor = event_processor or market_service.event_processor
        self.priority_manager = priority_manager or market_service.priority_manager
        
        # Worker pool configuration - use extracted config
        self.initial_worker_pool_size = self.config['WORKER_POOL_SIZE']
        self.min_worker_pool_size = self.config['MIN_WORKER_POOL_SIZE']
        self.max_worker_pool_size = self.config['MAX_WORKER_POOL_SIZE']
        self.worker_event_batch_size = self.config['WORKER_EVENT_BATCH_SIZE']
        self.worker_collection_timeout = self.config['WORKER_COLLECTION_TIMEOUT']

        # Sprint 26: Ensure initial size is within bounds and respects config
        self.initial_worker_pool_size = max(self.min_worker_pool_size, 
                                        min(self.initial_worker_pool_size, self.max_worker_pool_size))

        # Worker pool state
        self.worker_pool = []
        self.processing_active = False
        
        # Data flow tracking
        self.stats = DataFlowStats()
        
        # Check critical dependencies
        if not self.priority_manager:
            logger.error("🚨 NO PRIORITY MANAGER - Workers cannot receive events")
        if not self.event_processor:
            logger.error("🚨 NO EVENT PROCESSOR - Workers cannot process events")
            
        # Sprint 26: Enhanced startup logging    
        logger.info(f"🚀 SPRINT 26 - WorkerPoolManager Config: "
               f"initial={self.initial_worker_pool_size}, "
               f"min={self.min_worker_pool_size}, max={self.max_worker_pool_size}, "
               f"batch_size={self.worker_event_batch_size}, timeout={self.worker_collection_timeout}s")
        
        # TRACE: Initialization complete
        if tracer.should_trace('SYSTEM'):
            tracer.trace(
                ticker='SYSTEM',
                component='WorkerPoolManager',
                action='initialization_complete',
                data={
                    'timestamp': time.time(),
                    'input_count': ensure_int(0),
                    'output_count': ensure_int(0),
                    'duration_ms': (time.time() - init_start_time) * 1000,
                    'details': {
                        'initial_pool_size': self.initial_worker_pool_size,
                        'min_pool_size': self.min_worker_pool_size,
                        'max_pool_size': self.max_worker_pool_size,
                        'batch_size': self.worker_event_batch_size,
                        'collection_timeout': self.worker_collection_timeout,
                        'has_priority_manager': self.priority_manager is not None,
                        'has_event_processor': self.event_processor is not None
                    }
                }
            )
    
    def _extract_worker_pool_config(self, config: Dict) -> Dict:
        """Extract worker pool specific configuration subset with class defaults."""
        return {
            'WORKER_POOL_SIZE': config.get('WORKER_POOL_SIZE', self.DEFAULT_WORKER_POOL_SIZE),
            'MIN_WORKER_POOL_SIZE': config.get('MIN_WORKER_POOL_SIZE', self.DEFAULT_MIN_WORKER_POOL_SIZE),
            'MAX_WORKER_POOL_SIZE': config.get('MAX_WORKER_POOL_SIZE', self.DEFAULT_MAX_WORKER_POOL_SIZE),
            'WORKER_EVENT_BATCH_SIZE': config.get('WORKER_EVENT_BATCH_SIZE', self.DEFAULT_WORKER_EVENT_BATCH_SIZE),
            'WORKER_COLLECTION_TIMEOUT': config.get('WORKER_COLLECTION_TIMEOUT', self.DEFAULT_WORKER_COLLECTION_TIMEOUT),
            'WORKER_SCALING_THRESHOLD': config.get('WORKER_SCALING_THRESHOLD', self.DEFAULT_WORKER_SCALING_THRESHOLD)
        }
    
    def start_workers(self, num_workers: Optional[int] = None) -> WorkerPoolOperationResult:
        """Start initial worker threads."""
        start_time = time.time()
        operation_result = WorkerPoolOperationResult(operation_type="start_workers")
        
        try:
            if num_workers is None:
                num_workers = self.initial_worker_pool_size
            
            # Enforce bounds
            num_workers = max(self.min_worker_pool_size, min(num_workers, self.max_worker_pool_size))
            
            # TRACE: Start workers operation beginning
            if tracer.should_trace('SYSTEM'):
                tracer.trace(
                    ticker='SYSTEM',
                    component="WorkerPoolManager",
                    action="start_workers_begin",
                    data={
                        'timestamp': time.time(),
                        'input_count': num_workers,  # Workers to start
                        'output_count': ensure_int(0),  # None started yet
                        'duration_ms': ensure_int(0),
                        'details': {
                            "requested_workers": num_workers,
                            "existing_workers": len(self.worker_pool)
                        }
                    }
                )
            
            self.processing_active = True
            workers_started = 0
            
            # Clear any existing workers
            if self.worker_pool:
                logger.warning("⚠️ Workers already exist, stopping them first")
                self.stop_workers()
            
            # Start worker threads
            for i in range(num_workers):
                worker_thread = threading.Thread(
                    target=self._worker_process_events,
                    args=(i,),
                    daemon=True,
                    name=f"event-worker-{i}"
                )
                self.worker_pool.append(worker_thread)
                worker_thread.start()
                workers_started += 1
                
                # Log first few workers
                if workers_started <= 3:
                    logger.info(f"📥 WORKER #{i} started")
            
            # Update stats
            self.stats.workers_active = len(self.worker_pool)
            
            # Get queue status
            if self.priority_manager:
                queue_status = self.priority_manager.get_queue_status()
                operation_result.queue_sizes = [queue_status['current_size']]
            
            operation_result.success = True
            operation_result.workers_affected = workers_started
            operation_result.current_pool_size = len(self.worker_pool)
            operation_result.processing_time_ms = (time.time() - start_time) * 1000
            
            logger.info(f"✅ WORKERS STARTED: {workers_started} workers active")
            
            # TRACE: Start workers operation complete
            if tracer.should_trace('SYSTEM'):
                tracer.trace(
                    ticker='SYSTEM',
                    component="WorkerPoolManager",
                    action="start_workers_complete",
                    data={
                        'timestamp': time.time(),
                        'input_count': ensure_int(num_workers),
                        'output_count': ensure_int(workers_started),
                        'duration_ms': (time.time() - start_time) * 1000,
                        'details': {
                            "workers_started": workers_started,
                            "pool_size": len(self.worker_pool),
                            "queue_size": operation_result.queue_sizes[0] if operation_result.queue_sizes else 0
                        }
                    }
                )
            
            return operation_result
            
        except Exception as e:
            error_msg = f"Failed to start workers: {e}"
            logger.error(f"❌ WORKER START FAILED: {error_msg}")
            operation_result.success = False
            operation_result.errors.append(error_msg)
            
            # TRACE: Error
            if tracer.should_trace('SYSTEM'):
                tracer.trace(
                    ticker='SYSTEM',
                    component="WorkerPoolManager",
                    action="start_workers_error",
                    data={
                        'timestamp': time.time(),
                        'input_count': ensure_int(num_workers),
                        'output_count': ensure_int(0),
                        'duration_ms': (time.time() - start_time) * 1000,
                        'error': str(e),
                        'details': {
                            "error_type": type(e).__name__
                        }
                    }
                )
            
            return operation_result
        
    def _worker_process_events(self, worker_id: int):
        """Worker thread that processes events from centralized PriorityManager."""
        worker_start_time = time.time()
        events_processed_locally = 0
        first_event_logged = False
        consecutive_empty_collections = 0
        tick_events_seen = 0
        
        # Track performance metrics for batch tracing
        event_type_totals = defaultdict(int)
        slow_events = []
        
        logger.debug(f"🔍 DIAG-WORKER-POOL: Worker-{worker_id} starting")
        
        # TRACE: Worker started (keep this - one time per worker)
        if tracer.should_trace('SYSTEM'):
            tracer.trace(
                ticker='SYSTEM',
                component="WorkerPool",
                action="worker_started",
                data={
                    'timestamp': time.time(),
                    'input_count': ensure_int(0),
                    'output_count': ensure_int(0),
                    'duration_ms': 0,
                    'details': {
                        "worker_id": worker_id,
                        "thread_name": threading.current_thread().name,
                        "batch_size": self.worker_event_batch_size
                    }
                }
            )

        while self.processing_active:
            try:
                # Sprint 26: Log batch size on first collection for this worker
                if events_processed_locally == 0:
                    logger.info(f"📊 SPRINT 26 - Worker-{worker_id} using batch_size={self.worker_event_batch_size}")
                
                # DIAGNOSTIC: Every 100 attempts, check what's available
                if consecutive_empty_collections % 100 == 0 and consecutive_empty_collections > 0:
                    logger.debug(f"🔍 DIAG-WORKER-POOL: Worker-{worker_id}: No events for {consecutive_empty_collections} attempts")
                
                # Workers process ALL events
                batch_start_time = time.time()
                events = self.priority_manager.collect_events(
                    max_events=self.worker_event_batch_size,
                    timeout=self.worker_collection_timeout
                )
                
                if not events:
                    consecutive_empty_collections += 1
                    
                    # Progressive backoff
                    if consecutive_empty_collections < 10:
                        time.sleep(0.01)
                    elif consecutive_empty_collections < 50:
                        time.sleep(0.05)
                    elif consecutive_empty_collections < 100:
                        time.sleep(0.1)
                    else:
                        time.sleep(0.5)
                    
                    continue
                
                # Reset counter when we get events
                consecutive_empty_collections = 0
                
                # Process batch
                batch_processed = 0
                batch_failed = 0
                batch_event_types = defaultdict(int)
                batch_slow_threshold_ms = 50  # Events taking longer than 50ms
                
                for event_type, event_data in events:
                    ticker = None
                    event_start_time = time.time()
                    
                    try:
                        if event_type == 'stop':
                            logger.debug(f"🔍 DIAG-WORKER-POOL: Worker-{worker_id}: Received stop signal")
                            
                            # TRACE: Worker stopping (keep this - important lifecycle event)
                            if tracer.should_trace('SYSTEM'):
                                tracer.trace(
                                    ticker='SYSTEM',
                                    component="WorkerPool",
                                    action="worker_stopped",
                                    data={
                                        'timestamp': time.time(),
                                        'input_count': ensure_int(events_processed_locally),
                                        'output_count': ensure_int(events_processed_locally),
                                        'duration_ms': (time.time() - worker_start_time) * 1000,
                                        'details': {
                                            "worker_id": worker_id,
                                            "total_events_processed": events_processed_locally,
                                            "event_type_breakdown": dict(event_type_totals),
                                            "slow_events_count": len(slow_events)
                                        }
                                    }
                                )
                            return

                        self.stats.events_received += 1
                        
                        # Extract ticker based on event type
                        if event_type == 'tick':
                            ticker = event_data.ticker if hasattr(event_data, 'ticker') else None
                            tick_events_seen += 1
                            if tick_events_seen <= 5:
                                logger.debug(f"🔍 DIAG-WORKER-POOL: Worker-{worker_id}: Processing tick #{tick_events_seen} for {ticker}")
                        elif event_type in ['high', 'low', 'session_high', 'session_low', 'trend', 'surge']:
                            ticker = event_data.ticker if hasattr(event_data, 'ticker') else None
                            if events_processed_locally < 10:  # Only log first few
                                logger.debug(f"🔍 DIAG-WORKER-POOL: Worker-{worker_id}: Processing {event_type} event for {ticker}")
                        else:
                            ticker = getattr(event_data, 'ticker', None)
                        
                        # Process event
                        if event_type in ['high', 'low', 'session_high', 'session_low']:
                            self._process_event_via_market_service(event_type, event_data, worker_id)
                        elif event_type in ['trend', 'surge']:
                            self._process_event_via_market_service(event_type, event_data, worker_id)
                        
                        # Track metrics
                        events_processed_locally += 1
                        batch_processed += 1
                        self.stats.events_processed += 1
                        batch_event_types[event_type] += 1
                        event_type_totals[event_type] += 1
                        
                        # Track slow events
                        event_duration_ms = (time.time() - event_start_time) * 1000
                        if event_duration_ms > batch_slow_threshold_ms:
                            slow_events.append({
                                'ticker': ticker,
                                'event_type': event_type,
                                'duration_ms': event_duration_ms,
                                'worker_id': worker_id
                            })
                            
                            # Log slow events immediately
                            logger.warning(f"⚠️ WORKER-POOL: Slow event processing: {ticker} {event_type} took {event_duration_ms:.1f}ms")

                    except Exception as e:
                        logger.error(f"❌ Worker {worker_id} event processing error: {e}")
                        self.stats.events_failed += 1
                        batch_failed += 1
                        
                        # Only trace critical errors
                        if ticker and tracer.should_trace(ticker):
                            tracer.trace(
                                ticker=ticker,
                                component="WorkerPool",
                                action="processing_error",
                                data={
                                    'timestamp': time.time(),
                                    'input_count': ensure_int(1),
                                    'output_count': ensure_int(0),
                                    'duration_ms': (time.time() - event_start_time) * 1000,
                                    'error': str(e),
                                    'details': {
                                        "worker_id": worker_id,
                                        "event_type": event_type,
                                        "error_type": type(e).__name__
                                    }
                                }
                            )
                
                # SINGLE QUALITY TRACE: Batch complete with meaningful metrics
                batch_duration_ms = (time.time() - batch_start_time) * 1000
                if tracer.should_trace('SYSTEM') and batch_processed > 0:
                    tracer.trace(
                        ticker='SYSTEM',
                        component="WorkerPool",
                        action="batch_processed",
                        data={
                            'timestamp': time.time(),
                            'input_count': ensure_int(len(events)),
                            'output_count': ensure_int(batch_processed),
                            'duration_ms': batch_duration_ms,
                            'details': {
                                "worker_id": worker_id,
                                "success_rate": (batch_processed / len(events) * 100),
                                "failed_count": batch_failed,
                                "event_breakdown": dict(batch_event_types),
                                "avg_event_time_ms": batch_duration_ms / len(events) if events else 0,
                                "queue_depth": self.priority_manager.event_queue.qsize() if self.priority_manager else 0
                            }
                        }
                    )
                
                # Log performance warning for slow batches
                if batch_duration_ms > 1000:  # Batch took over 1 second
                    logger.warning(f"⚠️ WORKER-POOL: Slow batch processing: Worker-{worker_id} took {batch_duration_ms:.0f}ms for {len(events)} events")
                
                # Periodic stats
                if self.stats.should_log():
                    self.stats.log_stats()
                    
                    # Also log worker-specific performance metrics
                    if slow_events:
                        logger.info(f"📊 Worker-{worker_id} performance: {len(slow_events)} slow events detected")
                        
            except Exception as e:
                logger.error(f"❌ Worker {worker_id} exception: {e}", exc_info=True)
                time.sleep(0.5)
        
        logger.debug(f"🔍 DIAG-WORKER-POOL: Worker-{worker_id} exiting, processed {events_processed_locally} events")
    
    def _process_event_via_market_service(self, event_type: str, event_data: BaseEvent, worker_id: int):
        """Process event by routing through the appropriate service component.
        PHASE 4: Only handles typed events
        """
        process_start_time = time.time()
        ticker = None
        
        try:
            # Route based on event type
            if event_type == 'tick':
                # Tick events go through EventProcessor
                if self.event_processor:
                    ticker = event_data.ticker
                    processing_result = self.event_processor.handle_tick(event_data)
                    
                    if not processing_result.success:
                        # TRACE: Tick processing failed
                        if tracer.should_trace(ticker):
                            tracer.trace(
                                ticker=ticker,
                                component="WorkerPool",
                                action="tick_processing_failed",
                                data={
                                    'timestamp': time.time(),
                                    'input_count': ensure_int(1),
                                    'output_count': ensure_int(0),  # Failed
                                    'duration_ms': (time.time() - process_start_time) * 1000,
                                    'details': {
                                        "worker_id": worker_id,
                                        "errors": processing_result.errors
                                    }
                                }
                            )
                    else:
                        # TRACE: Tick processing succeeded
                        if tracer.should_trace(ticker, TraceLevel.VERBOSE):
                            tracer.trace(
                                ticker=ticker,
                                component="WorkerPool",
                                action="tick_processing_success",
                                data={
                                    'timestamp': time.time(),
                                    'input_count': ensure_int(1),
                                    'output_count': ensure_int(1),
                                    'duration_ms': (time.time() - process_start_time) * 1000,
                                    'details': {
                                        "worker_id": worker_id,
                                        "events_generated": processing_result.events_generated
                                    }
                                }
                            )

            elif event_type == 'status':
                # Route status events to market service
                if hasattr(self.market_service, '_process_status_event'):
                    self.market_service._process_status_event(event_data)
                    
            elif event_type in ['high', 'low', 'session_high', 'session_low']:
                # PROCESS HIGH/LOW EVENTS
                if isinstance(event_data, HighLowEvent):
                    ticker = event_data.ticker
                    
                    # Ensure StockData exists for ticker
                    if ticker not in self.market_service.stock_details:
                        self.market_service.stock_details[ticker] = StockData(ticker=ticker)
                    
                    # Get typed StockData
                    stock_data: StockData = self.market_service.stock_details[ticker]
                    
                    # Add typed event
                    stock_data.add_event(event_data)
                    
                    # Mark ticker as changed
                    self.market_service.changed_tickers.add(ticker)
                    
                    # TRACE: Event stored
                    if tracer.should_trace(ticker):
                        tracer.trace(
                            ticker=ticker,
                            component="WorkerPool",
                            action="event_stored",
                            data={
                                'timestamp': time.time(),
                                'input_count': ensure_int(1),
                                'output_count': ensure_int(1),  # Successfully stored
                                'duration_ms': (time.time() - process_start_time) * 1000,
                                'details': {
                                    "worker_id": worker_id,
                                    "event_type": event_type,
                                    "storage": "StockData"
                                }
                            }
                        )

            elif event_type in ['trend', 'surge']:
                # SKIP STORAGE - trends and surges flow directly to frontend
                ticker = event_data.ticker if hasattr(event_data, 'ticker') else None
                
                # TRACE: Event bypass (VERBOSE level to avoid spam)
                if ticker and tracer.should_trace(ticker, TraceLevel.VERBOSE):
                    tracer.trace(
                        ticker=ticker,
                        component="WorkerPool",
                        action="event_bypass_storage",
                        data={
                            'timestamp': time.time(),
                            'input_count': ensure_int(1),
                            'output_count': ensure_int(1),
                            'duration_ms': (time.time() - process_start_time) * 1000,
                            'details': {
                                "worker_id": worker_id,
                                "event_type": event_type,
                                "reason": "direct_to_frontend"
                            }
                        }
                    )
            
            # NEW: Re-queue display events after processing
            if event_type in ['high', 'low', 'session_high', 'session_low', 'trend', 'surge']:
                # Display events need to be sent to frontend
                try:
                    # SPRINT 29: Convert ALL typed events to transport format before queuing
                    if hasattr(event_data, 'to_transport_dict'):
                        # Convert typed event to dict format for frontend
                        transport_data = event_data.to_transport_dict()
                    elif isinstance(event_data, dict):
                        # Already a dict, pass through
                        transport_data = event_data
                    else:
                        logger.warning(f"Unknown event format for {event_type}: {type(event_data)}")
                        transport_data = {'error': 'unknown_format', 'type': event_type}
                    
                    # Queue the converted data
                    self.market_service.display_queue.put(
                        (event_type, transport_data),  # Always queue dicts
                        block=False
                    )
                    
                    # Update statistics
                    self.market_service.display_queue_stats['events_queued'] += 1
                    current_size = self.market_service.display_queue.qsize()
                    if current_size > self.market_service.display_queue_stats['max_depth_seen']:
                        self.market_service.display_queue_stats['max_depth_seen'] = current_size
                    
                    # TRACE: Event re-queued for display
                    if ticker and tracer.should_trace(ticker):
                        tracer.trace(
                            ticker=ticker,
                            component="WorkerPool",
                            action="event_requeued_for_display",
                            data={
                                'timestamp': time.time(),
                                'input_count': ensure_int(1),
                                'output_count': ensure_int(1),
                                'duration_ms': (time.time() - process_start_time) * 1000,
                                'details': {
                                    "worker_id": worker_id,
                                    "event_type": event_type,
                                    "display_queue_size": current_size
                                }
                            }
                        )
                    
                    # Log surge events specifically
                    if event_type == 'surge':
                        logger.info(f"🚀 WORKER: Surge event for {ticker} queued for display (queue size: {current_size})")
                        
                except queue.Full:
                    self.market_service.display_queue_stats['queue_full_drops'] += 1
                    logger.warning(f"⚠️ Display queue FULL, dropping {event_type} for {ticker}")
                    
                    # TRACE: Queue full drop
                    if ticker and tracer.should_trace(ticker):
                        tracer.trace(
                            ticker=ticker,
                            component="WorkerPool",
                            action="display_queue_full",
                            data={
                                'timestamp': time.time(),
                                'input_count': ensure_int(1),
                                'output_count': ensure_int(0),
                                'error': "Display queue full",
                                'details': {
                                    "worker_id": worker_id,
                                    "event_type": event_type,
                                    "queue_size": self.market_service.display_queue.qsize()
                                }
                            }
                        )
            
            # Update counter for all processed events
            if hasattr(self.market_service, 'total_events_processed'):
                self.market_service.total_events_processed += 1
                
        except Exception as e:
            logger.error(f"❌ Event processing exception for {event_type}: {e}", exc_info=True)

            # TRACE: Error
            if ticker and tracer.should_trace(ticker):
                tracer.trace(
                    ticker=ticker,
                    component="WorkerPool",
                    action="process_event_error",
                    data={
                        'timestamp': time.time(),
                        'input_count': ensure_int(1),
                        'output_count': ensure_int(0),  # Failed
                        'duration_ms': (time.time() - process_start_time) * 1000,
                        'error': str(e),
                        'details': {
                            "worker_id": worker_id,
                            "event_type": event_type,
                            "error_type": type(e).__name__
                        }
                    }
                )

    def stop_workers(self) -> WorkerPoolOperationResult:
        """Stop all worker threads."""
        start_time = time.time()
        operation_result = WorkerPoolOperationResult(operation_type="stop_workers")
        
        try:
            initial_worker_count = len(self.worker_pool)
            
            # TRACE: Stop workers operation beginning
            if tracer.should_trace('SYSTEM'):
                tracer.trace(
                    ticker='SYSTEM',
                    component="WorkerPoolManager",
                    action="stop_workers_begin",
                    data={
                        'timestamp': time.time(),
                        'input_count': ensure_int(initial_worker_count),
                        'output_count': ensure_int(0),  # None stopped yet
                        'duration_ms': 0,
                        'details': {
                            "workers_to_stop": initial_worker_count
                        }
                    }
                )
            
            self.processing_active = False
            workers_stopped = 0
            
            # Signal workers to stop
            if self.priority_manager:
                for i in range(len(self.worker_pool)):
                    #self.priority_manager.add_event('stop', 'stop')
                    stop_event = StopEvent()
                    self.priority_manager.add_event(stop_event)

            # Wait for workers to finish
            for worker in self.worker_pool:
                if worker.is_alive():
                    worker.join(timeout=2.0)
                    if not worker.is_alive():
                        workers_stopped += 1
                    else:
                        logger.warning(f"⚠️ Worker {worker.name} failed to stop gracefully")
            
            # Clear worker pool
            self.worker_pool.clear()
            self.stats.workers_active = 0
            
            operation_result.success = True
            operation_result.workers_affected = workers_stopped
            operation_result.processing_time_ms = (time.time() - start_time) * 1000
            
            # TRACE: Stop workers operation complete
            if tracer.should_trace('SYSTEM'):
                tracer.trace(
                    ticker='SYSTEM',
                    component="WorkerPoolManager",
                    action="stop_workers_complete",
                    data={
                        'timestamp': time.time(),
                        'input_count': ensure_int(initial_worker_count),
                        'output_count': ensure_int(workers_stopped),
                        'duration_ms': (time.time() - start_time) * 1000,
                        'details': {
                            "workers_stopped": workers_stopped,
                            "workers_failed_to_stop": initial_worker_count - workers_stopped
                        }
                    }
                )
            
            return operation_result
            
        except Exception as e:
            error_msg = f"Error stopping workers: {e}"
            logger.error(f"❌ WORKER STOP FAILED: {error_msg}")
            operation_result.success = False
            operation_result.errors.append(error_msg)
            
            # TRACE: Error
            if tracer.should_trace('SYSTEM'):
                tracer.trace(
                    ticker='SYSTEM',
                    component="WorkerPoolManager",
                    action="stop_workers_error",
                    data={
                        'timestamp': time.time(),
                        'input_count': ensure_int(len(self.worker_pool)),
                        'output_count': ensure_int(0),
                        'duration_ms': (time.time() - start_time) * 1000,
                        'error': str(e),
                        'details': {
                            "error_type": type(e).__name__
                        }
                    }
                )
            
            return operation_result
    
    def check_data_flow_health(self):
        """Diagnose where data flow is breaking."""
        check_start_time = time.time()
        
        if self.stats.events_received == 0:
            logger.error("🚨 DIAG-WORKER-POOL: NO EVENTS RECEIVED - Check PriorityManager queue")
        elif self.stats.events_processed == 0:
            logger.warning("⚠️  DIAG-WORKER-POOL: Events received but NOT PROCESSED - Check event processor")
        elif self.stats.events_failed > self.stats.events_processed:
            logger.error("🚨  DIAG-WORKER-POOL: More failures than successes - Check processing logic")
            
        # Check worker health
        alive_workers = sum(1 for w in self.worker_pool if w.is_alive())
        if alive_workers < len(self.worker_pool):
            logger.error(f"🚨  DIAG-WORKER-POOL: WORKER HEALTH: Only {alive_workers}/{len(self.worker_pool)} workers alive")
            
        logger.info(f"🔍  DIAG-WORKER-POOL: HEALTH CHECK: Workers {alive_workers}/{len(self.worker_pool)}, Events processed {self.stats.events_processed}/{self.stats.events_received}")
        
        # TRACE: Health check performed
        if tracer.should_trace('SYSTEM'):
            tracer.trace(
                ticker='SYSTEM',
                component="WorkerPoolManager",
                action="health_check_performed",
                data={
                    'timestamp': time.time(),
                    'input_count': ensure_int(self.stats.events_received),
                    'output_count': ensure_int(self.stats.events_processed),
                    'duration_ms': (time.time() - check_start_time) * 1000,
                    'details': {
                        "workers_total": len(self.worker_pool),
                        "workers_alive": alive_workers,
                        "events_received": self.stats.events_received,
                        "events_processed": self.stats.events_processed,
                        "events_failed": self.stats.events_failed,
                        "failure_rate": (self.stats.events_failed / self.stats.events_received * 100) if self.stats.events_received > 0 else 0
                    }
                }
            )
    
    def get_diagnostic_worker_pool_status(self) -> Dict[str, Any]:
        """Get current worker pool status."""
        try:
            queue_status = {}
            if self.priority_manager:
                queue_status = self.priority_manager.get_queue_status()
            
            alive_workers = [w for w in self.worker_pool if w.is_alive()]
            
            return {
                'processing_active': self.processing_active,
                'workers_total': len(self.worker_pool),
                'workers_alive': len(alive_workers),
                'central_queue_size': queue_status.get('current_size', 0),
                'queue_utilization_percent': queue_status.get('utilization_percent', 0),
                'data_flow': {
                    'events_received': self.stats.events_received,
                    'events_processed': self.stats.events_processed,
                    'events_failed': self.stats.events_failed
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Status error: {e}")
            return {'error': str(e)}
        
    def adjust_worker_pool(self, target_size: int) -> WorkerPoolOperationResult:
        """
        Adjust worker pool size dynamically based on load.
        
        Args:
            target_size: Target number of workers
            
        Returns:
            WorkerPoolOperationResult: Operation result
        """
        start_time = time.time()
        operation_result = WorkerPoolOperationResult(operation_type="adjust_worker_pool")
        
        try:
            # Enforce bounds
            original_target = target_size
            target_size = max(self.min_worker_pool_size, min(target_size, self.max_worker_pool_size))
            current_size = len(self.worker_pool)
            
            # TRACE: Adjustment beginning
            if tracer.should_trace('SYSTEM'):
                tracer.trace(
                    ticker='SYSTEM',
                    component="WorkerPoolManager",
                    action="adjust_pool_begin",
                    data={
                        'timestamp': time.time(),
                        'input_count': ensure_int(current_size),
                        'output_count': ensure_int(target_size),
                        'duration_ms': 0,
                        'details': {
                            "current_size": current_size,
                            "requested_size": original_target,
                            "bounded_size": target_size,
                            "adjustment": target_size - current_size
                        }
                    }
                )
            
            if target_size == current_size:
                operation_result.warnings.append(f"Worker pool already at target size: {target_size}")
                operation_result.current_pool_size = current_size
                return operation_result
            
            if target_size > current_size:
                # Need to add workers
                workers_to_add = target_size - current_size
                logger.info(f"📈 DIAG-WORKER-POOL: adjust_worker_pool Scaling UP: Adding {workers_to_add} workers (current: {current_size} → target: {target_size})")
                
                for i in range(workers_to_add):
                    worker_id = current_size + i
                    worker_thread = threading.Thread(
                        target=self._worker_process_events,
                        args=(worker_id,),
                        daemon=True,
                        name=f"event-worker-{worker_id}"
                    )
                    self.worker_pool.append(worker_thread)
                    worker_thread.start()
                    operation_result.workers_affected += 1
                    
            else:
                # Need to remove workers
                workers_to_remove = current_size - target_size
                logger.info(f"📉  DIAG-WORKER-POOL: adjust_worker_pool Scaling DOWN: Removing {workers_to_remove} workers (current: {current_size} → target: {target_size})")
                
                # Signal workers to stop
                for i in range(workers_to_remove):
                    if self.priority_manager:
                        #self.priority_manager.add_event('stop', 'stop')
                        stop_event = StopEvent()
                        self.priority_manager.add_event(stop_event)
                
                # Remove worker threads from pool
                workers_removed = []
                for i in range(workers_to_remove):
                    if self.worker_pool:
                        worker = self.worker_pool.pop()
                        workers_removed.append(worker)
                        operation_result.workers_affected += 1
                
                # Wait for removed workers to finish (with timeout)
                for worker in workers_removed:
                    if worker.is_alive():
                        worker.join(timeout=2.0)
                        if worker.is_alive():
                            operation_result.warnings.append(f"Worker {worker.name} did not stop gracefully")
            
            # Update stats
            self.stats.workers_active = len(self.worker_pool)
            
            # Get queue status
            if self.priority_manager:
                queue_status = self.priority_manager.get_queue_status()
                operation_result.queue_sizes = [queue_status['current_size']]
            
            operation_result.success = True
            operation_result.current_pool_size = len(self.worker_pool)
            operation_result.processing_time_ms = (time.time() - start_time) * 1000
            
            logger.info(f"✅ DIAG-WORKER-POOL: adjust_worker_pool WORKER POOL ADJUSTED: {current_size} → {len(self.worker_pool)} workers")
            
            # TRACE: Adjustment complete
            if tracer.should_trace('SYSTEM'):
                tracer.trace(
                    ticker='SYSTEM',
                    component="WorkerPoolManager",
                    action="adjust_pool_complete",
                    data={
                        'timestamp': time.time(),
                        'input_count': ensure_int(current_size),
                        'output_count': ensure_int(len(self.worker_pool)),
                        'duration_ms': (time.time() - start_time) * 1000,
                        'details': {
                            "previous_size": current_size,
                            "new_size": len(self.worker_pool),
                            "workers_affected": operation_result.workers_affected,
                            "direction": "scale_up" if target_size > current_size else "scale_down"
                        }
                    }
                )
            
            return operation_result
            
        except Exception as e:
            error_msg = f"Failed to adjust worker pool: {e}"
            logger.error(f"❌ WORKER ADJUSTMENT FAILED: {error_msg}")
            operation_result.success = False
            operation_result.errors.append(error_msg)
            
            # TRACE: Error
            if tracer.should_trace('SYSTEM'):
                tracer.trace(
                    ticker='SYSTEM',
                    component="WorkerPoolManager",
                    action="adjust_pool_error",
                    data={
                        'timestamp': time.time(),
                        'input_count': ensure_int(current_size),
                        'output_count': ensure_int(len(self.worker_pool)),
                        'duration_ms': (time.time() - start_time) * 1000,
                        'error': str(e),
                        'details': {
                            "error_type": type(e).__name__,
                            "target_size": target_size
                        }
                    }
                )
            
            return operation_result