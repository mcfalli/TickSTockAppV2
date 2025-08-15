# classes/debug/tracer.py
"""
Production-ready debug tracer for TickStock event pipeline.
Provides comprehensive tracing, monitoring, and diagnostics capabilities.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set, Callable, Tuple
from enum import Enum
import time
import json
import threading
import os
from datetime import datetime
from collections import defaultdict
import statistics
import logging

# Get logger for tracer module
logger = logging.getLogger(__name__)

# Event type normalization mapping
EVENT_TYPE_MAPPING = {
    # Canonical name -> [possible aliases]
    'high': ['high', 'session_high'],
    'low': ['low', 'session_low'],
    'surge': ['surge'],
    'trend': ['trend']
}

def normalize_event_type(event_type: str) -> str:
    """Always return the canonical event type name"""
    if not event_type:
        return 'unknown'
    
    event_type = str(event_type).lower()
    
    for canonical, aliases in EVENT_TYPE_MAPPING.items():
        if event_type in aliases:
            return canonical
    return event_type

def ensure_int(value):
    """
    Convert value to int, handling various input types.
    Used to ensure trace data counts are always integers.
    
    Args:
        value: Any value that should be converted to int
        
    Returns:
        int: Converted integer value, 0 if conversion fails
    """
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        try:
            # Handle strings like "1.0" or "1"
            return int(float(value))
        except (ValueError, TypeError):
            return 0
    # For any other type, try conversion
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0
    
class TraceLevel(Enum):
    """Granularity of tracing"""
    CRITICAL = 1  # Only major events
    NORMAL = 2    # Standard tracing
    VERBOSE = 3   # Everything

@dataclass
class ProcessingStep:
    """Single step in the processing pipeline"""
    timestamp: float
    component: str
    action: str
    ticker: str
    data_snapshot: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp,
            'ticker': self.ticker,
            'component': self.component,
            'action': self.action,
            'data': self.data_snapshot,
            'metadata': self.metadata,
            'error': self.error,
            'duration_to_next_ms': 0
        }

@dataclass
class UserConnectionInfo:
    """Track user connection information"""
    user_id: int
    connection_time: float
    first_event_time: Optional[float] = None
    events_sent: int = 0
    
@dataclass
class TickerTrace:
    """Complete trace of a ticker through the system."""
    ticker: str
    trace_id: str
    start_time: float = field(default_factory=time.time)
    
    # Processing steps
    steps: List[ProcessingStep] = field(default_factory=list)
    
    # Counters for standard metrics
    counters: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    
    # Component timings
    component_timings: Dict[str, float] = field(default_factory=lambda: defaultdict(float))
    
    # Performance metrics
    performance_metrics: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Add event fingerprinting for deduplication
    event_fingerprints: Set[str] = field(default_factory=set)
    
    # Add event ID tracking
    event_ids_seen: Set[str] = field(default_factory=set)
    
    # User connection tracking
    user_connections: Dict[int, UserConnectionInfo] = field(default_factory=dict)
    first_user_connection_time: Optional[float] = None
    events_before_first_user: int = 0

    def _get_event_fingerprint(self, component: str, action: str, data: Dict[str, Any]) -> str:
        """Create unique fingerprint for an event to prevent double counting"""
        details = data.get('details', {})
        ticker = self.ticker
        
        # Normalize event type first
        event_type = normalize_event_type(details.get('event_type', 'unknown'))
        
        # Get identifying features
        timestamp = data.get('timestamp', 0)
        price = details.get('price', 0)
        
        # For emission events, include user_id to allow same event to different users
        user_id = details.get('user_id', '')
        
        # Round timestamp to avoid floating point precision issues
        timestamp_rounded = round(timestamp, 3)
        
        # Create a unique identifier for this event
        if action == 'event_emitted' and user_id:
            # Include user_id for per-user emissions
            return f"{ticker}:{event_type}:{price}:{timestamp_rounded}:{user_id}"
        elif action == 'event_emitted':
            # For emissions without user_id, use component to differentiate
            return f"{ticker}:{event_type}:{price}:{timestamp_rounded}:{component}"
        else:
            # For other actions, simpler fingerprint
            return f"{ticker}:{event_type}:{price}:{timestamp_rounded}"

    def _should_count_event(self, component: str, action: str, data: Dict[str, Any]) -> bool:
        """Check if this event should be counted (not a duplicate)"""
        # Only check for duplicates on specific actions
        if action not in ['event_emitted', 'event_queued', 'event_detected']:
            return True
        
        # For event_detected with multiple events, always count
        details = data.get('details', {})
        if action == 'event_detected' and details.get('event_type') == 'multiple':
            return True
        
        fingerprint = self._get_event_fingerprint(component, action, data)
        
        # Check if we've seen this exact event before
        if fingerprint in self.event_fingerprints:
            # Log duplicate detection for debugging
            if self.ticker in ['TEST_TICKER', 'FLOW_TEST'] and logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"[DEDUP] Skipping duplicate: {fingerprint}")
            return False
        
        # Add to seen events
        self.event_fingerprints.add(fingerprint)
        
        # Also track event IDs if available
        if event_id := details.get('event_id'):
            # For event_emitted, allow same event_id for different users
            if action == 'event_emitted' and details.get('user_id'):
                event_id_key = f"{event_id}:{details['user_id']}"
            else:
                event_id_key = event_id
                
            if event_id_key in self.event_ids_seen:
                if self.ticker in ['TEST_TICKER', 'FLOW_TEST'] and logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"[DEDUP] Skipping duplicate event_id: {event_id_key}")
                return False
            self.event_ids_seen.add(event_id_key)
        
        return True
        
    def _ensure_int(self, value: Any) -> int:
        """Ensure a value is converted to int safely"""
        return ensure_int(value)
    
    def add_step(self, component: str, action: str, data: Dict[str, Any], **metadata):
        """Add a processing step with automatic metric extraction and deduplication"""
        # Normalize event types in details before processing
        if 'details' in data and 'event_type' in data['details']:
            data['details']['event_type'] = normalize_event_type(data['details']['event_type'])
        
        # Track user connections
        if action == 'user_connected' and component == 'WebSocketManager':
            user_id = data.get('details', {}).get('user_id')
            if user_id:
                self._track_user_connection(user_id, data.get('timestamp', time.time()))
        
        # Track events before first user
        if action == 'event_detected' and not self.first_user_connection_time:
            self.events_before_first_user += self._ensure_int(data.get('output_count', 0))
        
        step = ProcessingStep(
            timestamp=time.time(),
            ticker=self.ticker,
            component=component,
            action=action,
            data_snapshot=self._serialize_data(data),
            metadata=metadata,
            error=data.get('error')
        )
        self.steps.append(step)
        
        # Update component timing
        if len(self.steps) > 1:
            time_delta = step.timestamp - self.steps[-2].timestamp
            self.component_timings[component] += time_delta
        
        # Check for duplicates before updating counters
        if self._should_count_event(component, action, data):
            # Extract standard metrics from data
            self._update_counters(component, action, data)
            self._update_performance_metrics(component, action, data)
    
    def _track_user_connection(self, user_id: int, timestamp: float):
        """Track user connection information"""
        if user_id not in self.user_connections:
            self.user_connections[user_id] = UserConnectionInfo(
                user_id=user_id,
                connection_time=timestamp
            )
            
            # Track first user connection time
            if self.first_user_connection_time is None:
                self.first_user_connection_time = timestamp
                logger.info(f"First user connection for {self.ticker} at {timestamp}")
    
    def _update_counters(self, component: str, action: str, data: Dict[str, Any]):
        """Enhanced counter tracking with normalized event naming"""
        details = data.get('details', {})
        
        # ALWAYS normalize event types before counting
        if 'event_type' in details:
            details['event_type'] = normalize_event_type(details['event_type'])
        
        # Tick tracking
        if action in ['tick_received', 'tick_generated', 'tick_created']:
            self.counters['ticks_received'] += 1
        elif action == 'tick_delegated':
            self.counters['ticks_delegated'] += 1
            if details.get('success'):
                self.counters['tick_delegations_success'] += 1
            else:
                self.counters['tick_delegations_failed'] += 1
        
        # Event detection tracking
        elif action == 'event_detected':
            event_type = details.get('event_type', 'unknown')
            output_count = self._ensure_int(data.get('output_count', 0))
            
            # Handle "multiple" event type from EventDetector
            if event_type == 'multiple' and 'event_breakdown' in details:
                # Normalize event types in breakdown
                for evt_type, count in details['event_breakdown'].items():
                    normalized_type = normalize_event_type(evt_type)
                    count = self._ensure_int(count)
                    self.counters[f'events_detected_{normalized_type}'] += count
                    self.counters['events_detected_total'] += count
            else:
                # Single event type - already normalized
                self.counters[f'events_detected_{event_type}'] += output_count
                self.counters['events_detected_total'] += output_count
        
        # Event queueing tracking
        elif action == 'event_queued':
            event_type = details.get('event_type', 'unknown')
            # Only count if queue_result is not False
            if details.get('queue_result', True):
                self.counters[f'events_queued_{event_type}'] += 1
                self.counters['events_queued_total'] += 1
            else:
                self.counters['queue_rejections'] += 1
        
        # Event collection tracking
        elif action == 'events_collected':
            output_count = self._ensure_int(data.get('output_count', 0))
            self.counters['events_collected'] += output_count
            
            # Track empty vs non-empty collections
            if output_count == 0:
                self.counters['empty_collections'] += 1
            else:
                self.counters['non_empty_collections'] += 1
            
            # Track breakdown by type with normalization
            if 'event_breakdown' in details:
                for evt_type, count in details['event_breakdown'].items():
                    normalized_type = normalize_event_type(evt_type)
                    self.counters[f'events_collected_{normalized_type}'] += self._ensure_int(count)
        
        # Event emission tracking - Fixed to use output_count properly
        elif action == 'event_emitted':
            # Use output_count from data, default to 1 if not specified
            output_count = self._ensure_int(data.get('output_count', 1))
            
            # Get and normalize event type
            event_type = details.get('event_type') or data.get('EVENT') or data.get('event_type', 'unknown')
            event_type = normalize_event_type(event_type)
            direction = details.get('direction', '')
            
            # Update counters with actual output_count
            self.counters['events_emitted_total'] += output_count
            
            # Track by type and direction
            if direction:
                self.counters[f'emitted_{event_type}_{direction}'] += output_count
                self.counters[f'events_emitted_{event_type}'] += output_count
            else:
                self.counters[f'emitted_{event_type}'] += output_count
                self.counters[f'events_emitted_{event_type}'] += output_count
            
            # Track tick counts if available
            if event_type == 'high' and 'count_up' in details:
                self.counters['high_ticks_emitted'] += self._ensure_int(details['count_up'])
            elif event_type == 'low' and 'count_down' in details:
                self.counters['low_ticks_emitted'] += self._ensure_int(details['count_down'])
            
            # Track user-specific emissions
            if user_id := details.get('user_id'):
                if user_id in self.user_connections:
                    self.user_connections[user_id].events_sent += output_count
                    if self.user_connections[user_id].first_event_time is None:
                        self.user_connections[user_id].first_event_time = data.get('timestamp', time.time())
        
        # Track collection diagnostics
        elif action == 'collect_events_complete':
            duration_ms = self._ensure_int(data.get('duration_ms', 0))
            self.counters['total_collections'] += 1
            if duration_ms > 500:
                self.counters['slow_collections'] += 1
        
        # Empty update tracking
        elif action == 'emitting_empty_update':
            self.counters['empty_updates'] += 1
        
        # WebSocket specific tracking
        elif component == 'WebSocketPublisher' and action == 'emission_complete':
            events_sent = data.get('output_count', 0)
            self.counters['websocket_total_emissions'] += events_sent
            self.counters['websocket_broadcasts'] += 1
        
        # Error and drop tracking
        if action == 'tick_processing_failed':
            self.counters['processing_errors'] += 1
        elif action == 'event_dropped':
            reason = details.get('reason', 'unknown')
            self.counters[f'drops_{reason}'] += 1
            self.counters['drops_total'] += 1
        elif action == 'circuit_breaker_trip':
            self.counters['circuit_breaker_trips'] += 1
        elif action == 'error':
            self.counters['errors_total'] += 1
            error_type = details.get('error_type', 'unknown')
            self.counters[f'errors_{error_type}'] += 1
        
        # Track emission start/complete tick counts
        if action == 'emission_start' and 'tick_counts' in details:
            tick_counts = details['tick_counts']
            self.counters['emission_start_high_ticks'] = self._ensure_int(tick_counts.get('high_ticks', 0))
            self.counters['emission_start_low_ticks'] = self._ensure_int(tick_counts.get('low_ticks', 0))
        
        if action == 'emission_complete' and 'tick_counts' in details:
            tick_counts = details['tick_counts']
            self.counters['emission_complete_high_ticks'] = self._ensure_int(tick_counts.get('high_ticks_sent', 0))
            self.counters['emission_complete_low_ticks'] = self._ensure_int(tick_counts.get('low_ticks_sent', 0))
            self.counters['emission_complete_total_ticks'] = self._ensure_int(tick_counts.get('ticks_sent_total', 0))
        
        # WebSocketPublisher specific emissions
        if component == 'WebSocketPublisher':
            if action.startswith('emitting_'):
                parts = action.split('_')
                if len(parts) >= 2:
                    event_type = parts[1]
                    self.counters[f'websocket_emitted_{event_type}'] += 1
            elif action == 'emission_complete':
                events_sent = data.get('output_count', 0)
                self.counters['websocket_total_emissions'] += events_sent
        
        # Queue depth tracking
        if 'queue_size_after' in details:
            queue_size = details['queue_size_after']
            self.counters[f'{component}_queue_size_max'] = max(
                self.counters.get(f'{component}_queue_size_max', 0),
                queue_size
            )
            self.counters[f'{component}_queue_size_latest'] = queue_size
        
        # Worker pool tracking
        if component == 'WorkerPool' or component == 'WorkerPoolManager':
            if action == 'worker_started':
                self.counters['workers_started'] += 1
            elif action == 'worker_stopped':
                self.counters['workers_stopped'] += 1
            elif action == 'batch_processed':
                self.counters['batches_processed'] += 1
                batch_size = data.get('input_count', 0)
                self.counters['batch_items_total'] += batch_size
            elif action == 'adjust_pool_complete':
                new_size = details.get('new_size', 0)
                self.counters['worker_pool_size'] = new_size
        
        # User connection tracking
        if component == 'WebSocketManager':
            if action == 'user_connected':
                self.counters['user_connections'] += 1
                self.counters['active_users'] = details.get('total_users', 0)
            elif action == 'user_disconnected':
                self.counters['user_disconnections'] += 1
                self.counters['active_users'] = details.get('total_users', 0)
        
        # Track all input/output for flow analysis
        if 'input_count' in data:
            self.counters[f'{component}_{action}_input'] += data['input_count']
        if 'output_count' in data:
            self.counters[f'{component}_{action}_output'] += data['output_count']
    
    def _update_performance_metrics(self, component: str, action: str, data: Dict[str, Any]):
        """Track performance metrics"""
        duration_ms = data.get('duration_ms', 0)
        details = data.get('details', {})
        
        # Track slow operations
        if action == 'detection_slow':
            threshold = details.get('threshold_ms', 0)
            self.counters['slow_detections'] += 1
            self.counters[f'{component}_slow_operations'] += 1
            
            # Track slowest detection
            if 'slowest_detection_ms' not in self.performance_metrics:
                self.performance_metrics['slowest_detection_ms'] = 0
            self.performance_metrics['slowest_detection_ms'] = max(
                self.performance_metrics['slowest_detection_ms'], 
                duration_ms
            )
        
        # Track average processing times by component/action
        if duration_ms > 0:
            key = f'{component}_{action}'
            if key not in self.performance_metrics:
                self.performance_metrics[key] = {
                    'count': 0,
                    'total_ms': 0,
                    'max_ms': 0,
                    'min_ms': float('inf'),
                    'samples': []  # Keep last N samples for percentiles
                }
            
            metrics = self.performance_metrics[key]
            metrics['count'] += 1
            metrics['total_ms'] += duration_ms
            metrics['max_ms'] = max(metrics['max_ms'], duration_ms)
            metrics['min_ms'] = min(metrics['min_ms'], duration_ms)
            
            # Keep last 100 samples for percentile calculations
            if len(metrics['samples']) >= 100:
                metrics['samples'].pop(0)
            metrics['samples'].append(duration_ms)
        
        # Track batch processing efficiency
        if action == 'batch_processed':
            success_rate = details.get('success_rate', 0)
            if 'batch_efficiency' not in self.performance_metrics:
                self.performance_metrics['batch_efficiency'] = []
            self.performance_metrics['batch_efficiency'].append(success_rate)
            
            # Keep only last 100 efficiency samples
            if len(self.performance_metrics['batch_efficiency']) > 100:
                self.performance_metrics['batch_efficiency'] = \
                    self.performance_metrics['batch_efficiency'][-100:]
        
        # Track emission performance
        if action == 'emission_complete':
            processing_rate = details.get('processing_rate_events_per_sec', 0)
            if 'emission_rates' not in self.performance_metrics:
                self.performance_metrics['emission_rates'] = []
            self.performance_metrics['emission_rates'].append(processing_rate)
            
            # Track cache performance
            cache_hit_rate = details.get('cache_hit_rate', 0)
            if 'cache_hit_rates' not in self.performance_metrics:
                self.performance_metrics['cache_hit_rates'] = []
            self.performance_metrics['cache_hit_rates'].append(cache_hit_rate)
    
    def _serialize_data(self, data: Any) -> Any:
        """Serialize data for storage, preserving numeric types"""
        if isinstance(data, (int, float, bool)):
            # Preserve numeric types - don't convert to string!
            return data
        elif isinstance(data, str):
            return data[:500]  # Limit string length
        elif isinstance(data, type(None)):
            return None
        elif hasattr(data, 'to_dict'):
            return self._serialize_data(data.to_dict())
        elif isinstance(data, dict):
            return {k: self._serialize_data(v) for k, v in data.items()}
        elif isinstance(data, (list, tuple)):
            return [self._serialize_data(item) for item in data[:10]]  # Limit to 10
        else:
            # Only convert to string if we can't handle it any other way
            return str(data)[:500]
    
    def get_summary(self) -> Dict[str, Any]:
        """Get trace summary with flow analysis"""
        duration = time.time() - self.start_time
        
        # Calculate flow efficiency by event type
        flow_analysis = {}
        for event_type in ['high', 'low', 'surge', 'trend']:
            detected = self.counters.get(f'events_detected_{event_type}', 0)
            queued = self.counters.get(f'events_queued_{event_type}', 0)
            collected = self.counters.get(f'events_collected_{event_type}', 0)
            emitted = self.counters.get(f'emitted_{event_type}', 0) + \
                     self.counters.get(f'emitted_{event_type}_up', 0) + \
                     self.counters.get(f'emitted_{event_type}_down', 0)
            
            if detected > 0:
                flow_analysis[event_type] = {
                    'detected': detected,
                    'queued': queued,
                    'collected': collected,
                    'emitted': emitted,
                    'queue_efficiency': (queued / detected * 100) if detected > 0 else 0,
                    'collection_efficiency': (collected / detected * 100) if detected > 0 else 0,
                    'emission_efficiency': (emitted / detected * 100) if detected > 0 else 0
                }
        
        # Calculate performance percentiles
        perf_summary = {}
        for key, metrics in self.performance_metrics.items():
            if isinstance(metrics, dict) and 'samples' in metrics and metrics['samples']:
                samples = metrics['samples']
                perf_summary[key] = {
                    'avg_ms': metrics['total_ms'] / metrics['count'],
                    'min_ms': metrics['min_ms'],
                    'max_ms': metrics['max_ms'],
                    'p50_ms': statistics.median(samples),
                    'p95_ms': statistics.quantiles(samples, n=20)[18] if len(samples) >= 20 else max(samples),
                    'p99_ms': statistics.quantiles(samples, n=100)[98] if len(samples) >= 100 else max(samples)
                }
        
        # Calculate adjusted efficiency
        total_detected = self.counters.get('events_detected_total', 0)
        total_emitted = self.counters.get('events_emitted_total', 0)
        
        # Adjust for events before first user
        if self.first_user_connection_time:
            adjusted_detected = total_detected - self.events_before_first_user
            adjusted_efficiency = (total_emitted / adjusted_detected * 100) if adjusted_detected > 0 else 0
        else:
            adjusted_detected = total_detected
            adjusted_efficiency = (total_emitted / total_detected * 100) if total_detected > 0 else 0
        
        return {
            'ticker': self.ticker,
            'trace_id': self.trace_id,
            'duration_seconds': duration,
            'counters': dict(self.counters),
            'flow_analysis': flow_analysis,
            'component_timings': dict(self.component_timings),
            'performance_summary': perf_summary,
            'steps_count': len(self.steps),
            'ticks_per_second': self.counters.get('ticks_received', 0) / duration if duration > 0 else 0,
            'errors': {
                'total': self.counters.get('errors_total', 0),
                'processing': self.counters.get('processing_errors', 0),
                'drops': self.counters.get('drops_total', 0),
                'circuit_trips': self.counters.get('circuit_breaker_trips', 0)
            },
            'user_connections': {
                'total_users': len(self.user_connections),
                'first_user_time': self.first_user_connection_time,
                'events_before_first_user': self.events_before_first_user,
                'adjusted_efficiency': adjusted_efficiency,
                'raw_efficiency': (total_emitted / total_detected * 100) if total_detected > 0 else 0
            }
        }
    
    def export_json(self) -> Dict[str, Any]:
        """Export full trace as JSON"""
        steps_with_duration = []
        for i, step in enumerate(self.steps):
            step_dict = step.to_dict()
            if i < len(self.steps) - 1:
                step_dict['duration_to_next_ms'] = (
                    (self.steps[i + 1].timestamp - step.timestamp) * 1000
                )
            steps_with_duration.append(step_dict)
        
        return {
            'trace_id': self.trace_id,
            'ticker': self.ticker,
            'start_time': self.start_time,
            'end_time': time.time(),
            'duration_seconds': time.time() - self.start_time,
            'summary': self.get_summary(),
            'steps': steps_with_duration
        }



class DebugTracer:
    """Thread-safe singleton tracer for debugging specific tickers."""
    _instance = None
    _lock = threading.Lock()
    
    # Trace categories for better organization
    TRACE_CATEGORIES = {
        'flow': [
            'tick_created', 'tick_received', 'tick_delegated', 
            'event_detected', 'event_queued', 'events_collected', 
            'event_emitted', 'collection_prepare', 'collect_events_complete',
            'collection_start', 'emitting_empty_update', 'emitting_to_websocket',
            'event_processing', 'process_start', 'process_complete',
            'event_ready_for_emission', 'display_queue_collected',
            'events_buffered', 'buffer_pulled', 'emission_cycle_start', 
            'emission_cycle_complete'
        ],
        'performance': [
            'detection_slow', 'batch_processed', 'processing_slow',
            'slow_buffer_pull', 'emission_drought'
        ],
        'errors': [
            'error', 'tick_processing_failed', 'event_dropped', 
            'circuit_breaker_trip', 'surge_cooldown_blocked',
            'emission_failed_no_manager', 'emission_skipped_no_users'
        ],
        'system': [
            'initialization_complete', 'initialized', 'health_check_performed',
            'worker_started', 'worker_stopped', 'adjust_pool_begin', 
            'adjust_pool_complete', 'start_workers_begin', 'start_workers_complete',
            'stop_workers_begin', 'stop_workers_complete', 'stats_update',
            'no_users_retaining_events', 'daily_counts_reset', 'cleanup_complete',
            'queue_sample'
        ],
        'websocket': [
            'user_connected', 'user_disconnected', 'heartbeat_sent',
            'broadcast_complete', 'status_update_complete', 'market_status_broadcast',
            'emission_start', 'emission_complete', 'user_filtering_start',
            'user_filtering_complete', 'new_user_connection', 'buffered_events_sent',
            'user_emission', 'connection_stats_retrieved', 'generic_client_registered',
            'generic_client_unregistered', 'user_ready_for_events',
            'emission_cycle_start', 'emission_cycle_complete', 'high_events_lost'
        ],
        'data_flow': [
            'buffer_updated', 'buffer_overflow', 'event_stored', 
            'event_bypass_storage', 'surge_event_queued', 'universe_check',
            'ticker_initialized', 'surge_cleanup', 'surge_skipped',
            'window_analysis_start', 'window_analysis_complete',
            'universe_resolution_start', 'universe_name_resolved', 'universe_resolved',
            'events_buffered', 'buffer_pulled', 'buffer_near_capacity'
        ],
        'detection': [
            'detection_start', 'detection_complete', 'detection_slow',
            'ticker_initialized', 'daily_counts_reset'
        ]
    }
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.enabled = False
            self.trace_level = TraceLevel.NORMAL
            self.traced_tickers: Set[str] = set()
            self.traces: Dict[str, TickerTrace] = {}
            self.trace_callbacks: List[Callable] = []
            self._lock = threading.Lock()
            self.initialized = True
            self._ensure_log_directory()
            self._log_file = None
            self._log_lock = threading.Lock()
            
            # System metrics tracking
            self.system_metrics = {
                'initialization_times': {},
                'health_checks': 0,
                'worker_adjustments': 0,
                'market_status_updates': 0,
                'start_time': time.time()
            }
            
            # User connection tracking
            self.user_connection_times: Dict[str, float] = {}  # ticker -> first connection time
            self.events_before_users: Dict[str, int] = {}  # ticker -> count

    def _ensure_log_directory(self):
        """Ensure the logs directory exists"""
        os.makedirs('./logs', exist_ok=True)
    
    def _get_log_filename(self):
        """Generate log filename with date"""
        return f"./logs/trace_{datetime.now().strftime('%Y%m%d')}.log"

    def _get_diagnostics_filename(self):
        """Generate diagnostics filename with date"""
        return f"./logs/diag_{datetime.now().strftime('%Y%m%d')}.log"

    def _write_to_log(self, message: str):
        """Thread-safe write to log file"""
        with self._log_lock:
            try:
                filename = self._get_log_filename()
                with open(filename, 'a', encoding='utf-8') as f:
                    f.write(message)
                    f.flush()
            except Exception as e:
                logger.error(f"Error writing to log file: {e}")

    def enable_for_tickers(self, tickers: List[str], level: TraceLevel = TraceLevel.NORMAL):
        """Enable tracing for specific tickers"""
        self.enabled = True
        self.traced_tickers.update(tickers)
        self.traced_tickers.add('SYSTEM')  # Always trace system events
        self.trace_level = level
        logger.info(f"🔍 Debug tracing enabled for: {', '.join(tickers)} at level {level.name}")
    
    def should_trace(self, ticker: str, level: TraceLevel = TraceLevel.NORMAL) -> bool:
        """Check if we should trace this ticker at this level"""
        return (self.enabled and 
                (ticker in self.traced_tickers or ticker == 'SYSTEM') and 
                level.value <= self.trace_level.value)
    
    def trace(self, ticker: str, component: str, action: str, data: Dict[str, Any] = None):
        """Enhanced trace method with better filtering and categorization"""
        if not self.should_trace(ticker):
            return
        
        if data is None:
            data = {}
        
        # Ensure data has timestamp
        if 'timestamp' not in data:
            data['timestamp'] = time.time()
        
        # Determine trace category
        trace_category = None
        for category, actions in self.TRACE_CATEGORIES.items():
            if action in actions:
                trace_category = category
                break
        
        # Check for pattern matches
        if not trace_category:
            if component == "WebSocketPublisher" and action.startswith("emitting_"):
                trace_category = 'flow'
            elif "error" in action.lower() or "fail" in action.lower():
                trace_category = 'errors'
        
        # Force websocket category for WebSocketPublisher emission actions
        if not trace_category and component == "WebSocketPublisher":
            trace_category = 'websocket'
        
        # Build log message
        details = data.get('details', {})
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        
        log_parts = [
            f"[{timestamp}]",
            "[TRACE]",
            f"{ticker}",
            f"| COMPONENT:{component}",
            f"ACTION:{action}"
        ]
        
        if trace_category:
            log_parts.append(f"| CATEGORY:{trace_category}")
        
        # Add event type for flow events
        if trace_category == 'flow':
            if component == "WebSocketPublisher" and action.startswith("emitting_"):
                # Parse action like "emitting_surge" or "emitting_high_up"
                action_parts = action.split('_')
                if len(action_parts) >= 2:
                    event_type = action_parts[1]
                    log_parts.append(f"| EVENT:{event_type}")
                    if len(action_parts) >= 3:
                        direction = action_parts[2]
                        log_parts.append(f"| DIRECTION:{direction}")
            elif event_type := details.get('event_type'):
                log_parts.append(f"| EVENT:{event_type}")
        
        # Add error info for error category
        if trace_category == 'errors':
            if error := data.get('error'):
                log_parts.append(f"| ERROR:{error[:50]}")
            elif reason := details.get('reason'):
                log_parts.append(f"| REASON:{reason}")
        
        # Add performance info
        if duration_ms := data.get('duration_ms'):
            if duration_ms > 100:  # Flag slow operations
                log_parts.append(f"| DURATION:{duration_ms:.1f}ms ⚠️")
            else:
                log_parts.append(f"| DURATION:{duration_ms:.1f}ms")
        
        log_message = " ".join(log_parts) + "\n"
        
        # Write to log file
        self._write_to_log(log_message)
        
        # Add to trace
        with self._lock:
            trace = self._get_or_create_trace(ticker)
            trace.add_step(component, action, data)
            
            # Update system metrics
            if ticker == 'SYSTEM':
                self._update_system_metrics(component, action, data)
            
            # Track user connections globally
            if action == 'user_connected' and ticker not in self.user_connection_times:
                self.user_connection_times[ticker] = data.get('timestamp', time.time())
            
            # Call any registered callbacks
            for callback in self.trace_callbacks:
                try:
                    callback(ticker, component, action, data)
                except Exception as e:
                    error_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] [ERROR] Trace callback error: {e}\n"
                    self._write_to_log(error_msg)
    
    def _update_system_metrics(self, component: str, action: str, data: Dict[str, Any]):
        """Track system-wide metrics from SYSTEM traces"""
        if action == 'initialization_complete' or action == 'initialized':
            self.system_metrics['initialization_times'][component] = data.get('timestamp', time.time())
        elif action == 'health_check_performed':
            self.system_metrics['health_checks'] += 1
        elif action == 'adjust_pool_complete':
            self.system_metrics['worker_adjustments'] += 1
        elif action == 'market_status_broadcast':
            self.system_metrics['market_status_updates'] += 1
    
    def _ensure_int(self, value: Any) -> int:
        """Ensure a value is converted to int safely"""
        return ensure_int(value)
    
    def get_flow_summary(self, ticker: str = None) -> Dict[str, Any]:
        """Enhanced flow summary with normalized event type tracking and user connection awareness"""
        trace_key = f"{ticker}_active"
        if trace_key not in self.traces:
            return {}
        
        trace = self.traces[trace_key]
        
        # Initialize flow metrics
        flow = {
            # Core flow
            'ticks_created': trace.counters.get('ticks_created', 0),
            'ticks_received': trace.counters.get('ticks_received', 0), 
            'ticks_delegated': trace.counters.get('ticks_delegated', 0),
            
            # Detection
            'detections_started': trace.counters.get('detections_started', 0),
            'events_detected': trace.counters.get('events_detected_total', 0),
            'detection_errors': trace.counters.get('detection_errors', 0),
            
            # Queueing
            'events_queued': trace.counters.get('events_queued_total', 0),
            'queue_drops': trace.counters.get('drops_total', 0),
            'circuit_breaker_trips': trace.counters.get('circuit_breaker_trips', 0),
            
            # Collection
            'events_collected': trace.counters.get('events_collected', 0),
            'empty_collections': trace.counters.get('empty_collections', 0),
            'non_empty_collections': trace.counters.get('non_empty_collections', 0),
            'slow_collections': trace.counters.get('slow_collections', 0),
            
            # Emission
            'events_emitted': trace.counters.get('events_emitted_total', 0),
            'websocket_broadcasts': trace.counters.get('websocket_broadcasts', 0),
            'empty_updates': trace.counters.get('empty_updates', 0),
            
            # Counters (direct from trace)
            'counters': dict(trace.counters),
            
            # By event type - Use normalized names consistently
            'by_type': {},
            
            # Tick flow metrics
            'tick_flow': {
                'high_ticks_start': self._ensure_int(trace.counters.get('emission_start_high_ticks', 0)),
                'low_ticks_start': self._ensure_int(trace.counters.get('emission_start_low_ticks', 0)),
                'high_ticks_emitted': self._ensure_int(trace.counters.get('high_ticks_emitted', 0)),
                'low_ticks_emitted': self._ensure_int(trace.counters.get('low_ticks_emitted', 0)),
                'high_ticks_complete': self._ensure_int(trace.counters.get('emission_complete_high_ticks', 0)),
                'low_ticks_complete': self._ensure_int(trace.counters.get('emission_complete_low_ticks', 0)),
                'total_ticks_complete': self._ensure_int(trace.counters.get('emission_complete_total_ticks', 0))
            },
            
            # Pipeline stages for efficiency tracking
            'pipeline_stages': {},
            
            # User connection info
            'user_connections': {
                'first_user_time': trace.first_user_connection_time,
                'events_before_first_user': trace.events_before_first_user,
                'total_users': len(trace.user_connections),
                'adjusted_efficiency': 96.7,  # Will be calculated below
                'raw_efficiency': 83.1  # Will be calculated below
            }


        }
        
        # Add new metrics
        flow['buffer_metrics'] = {
            'events_buffered': trace.counters.get('events_buffered', 0),
            'buffer_pulls': trace.counters.get('buffer_pulls', 0),
            'buffer_overflows': trace.counters.get('buffer_overflows', 0),
            'max_buffer_size': trace.counters.get('max_buffer_size', 0)
        }
        
        flow['emission_metrics'] = {
            'emission_cycles': trace.counters.get('emission_cycles', 0),
            'empty_cycles': trace.counters.get('empty_emission_cycles', 0),
            'cycles_with_events': trace.counters.get('emission_cycles_with_events', 0)
        }
        
        # Build by_type data using normalized event types
        for event_type in ['high', 'low', 'trend', 'surge']:
            flow['by_type'][event_type] = {
                'detected': trace.counters.get(f'events_detected_{event_type}', 0),
                'queued': trace.counters.get(f'events_queued_{event_type}', 0),
                'collected': trace.counters.get(f'events_collected_{event_type}', 0),
                'emitted': trace.counters.get(f'emitted_{event_type}', 0) + 
                        trace.counters.get(f'emitted_{event_type}_up', 0) + 
                        trace.counters.get(f'emitted_{event_type}_down', 0)
            }
        
        # Calculate pipeline stage efficiency
        stages = [
            ('tick_reception', flow['ticks_created'], flow['ticks_received']),
            ('tick_delegation', flow['ticks_received'], flow['ticks_delegated']),
            ('event_detection', flow['ticks_delegated'], flow['events_detected']),
            ('event_queueing', flow['events_detected'], flow['events_queued']),
            ('event_collection', flow['events_queued'], flow['events_collected']),
            ('event_emission', flow['events_collected'], flow['events_emitted'])
        ]
        
        for stage_name, input_count, output_count in stages:
            if input_count > 0:
                flow['pipeline_stages'][stage_name] = {
                    'input': input_count,
                    'output': output_count,
                    'efficiency': (output_count / input_count * 100)
                }
        
        # Calculate overall efficiency (both raw and adjusted)
        if flow['events_detected'] > 0:
            # Raw efficiency
            flow['overall_efficiency'] = (flow['events_emitted'] / flow['events_detected'] * 100)
            flow['user_connections']['raw_efficiency'] = flow['overall_efficiency']
            
            # Adjusted efficiency (accounting for events before first user)
            adjusted_detected = flow['events_detected'] - trace.events_before_first_user
            if adjusted_detected > 0:
                flow['user_connections']['adjusted_efficiency'] = (flow['events_emitted'] / adjusted_detected * 100)
            else:
                flow['user_connections']['adjusted_efficiency'] = 0
        else:
            flow['overall_efficiency'] = 0
            flow['user_connections']['raw_efficiency'] = 0
            flow['user_connections']['adjusted_efficiency'] = 0
        
        # Add timing information
        duration = time.time() - trace.start_time
        if duration > 0:
            flow['ticks_per_second'] = flow['ticks_received'] / duration
            flow['events_per_second'] = flow['events_detected'] / duration
        
        return flow
    
    def print_flow_status(self):
        """Enhanced flow status with detailed event type breakdown"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        status_lines = []
        
        status_lines.append(f"\n[{timestamp}] TRACE FLOW STATUS")
        status_lines.append("=" * 80)
        
        # System status first
        if 'SYSTEM' in self.traced_tickers:
            status_lines.append("\nSYSTEM STATUS:")
            uptime_minutes = (time.time() - self.system_metrics['start_time']) / 60
            status_lines.append(f"  Uptime: {uptime_minutes:.1f} minutes")
            status_lines.append(f"  Health Checks: {self.system_metrics['health_checks']}")
            status_lines.append(f"  Worker Adjustments: {self.system_metrics['worker_adjustments']}")
            status_lines.append(f"  Market Status Updates: {self.system_metrics['market_status_updates']}")
            
            # Show initialization status
            if self.system_metrics['initialization_times']:
                status_lines.append("\n  Component Initialization:")
                for component, init_time in sorted(self.system_metrics['initialization_times'].items()):
                    status_lines.append(f"    {component}: ✓")
        
        # Process each traced ticker
        for ticker in sorted(self.traced_tickers):
            if ticker == 'SYSTEM':
                continue  # Already handled
                
            flow = self.get_flow_summary(ticker)
            if not flow:
                continue
            
            status_lines.append(f"\n{ticker}:")
            
            # Core flow metrics
            ticks_created = flow.get('ticks_created', 0)
            ticks_received = flow.get('ticks_received', 0)
            ticks_delegated = flow.get('ticks_delegated', 0)
            events_detected = flow.get('events_detected', 0)
            events_queued = flow.get('events_queued', 0)
            events_collected = flow.get('events_collected', 0)
            events_emitted = flow.get('events_emitted', 0)
            
            status_lines.append(f"  Flow Metrics:")
            status_lines.append(f"    Ticks Created:      {ticks_created}")
            status_lines.append(f"    Ticks Received:     {ticks_received}")
            status_lines.append(f"    Ticks Delegated:    {ticks_delegated}")
            status_lines.append(f"    Events Detected:    {events_detected}")
            status_lines.append(f"    Events Queued:      {events_queued}")
            status_lines.append(f"    Events Collected:   {events_collected}")
            status_lines.append(f"    Events Emitted:     {events_emitted}")
            
            # User connection info
            user_info = flow.get('user_connections', {})
            if user_info.get('first_user_time'):
                status_lines.append(f"\n  User Connection Info:")
                status_lines.append(f"    First User Connected: {datetime.fromtimestamp(user_info['first_user_time']).strftime('%H:%M:%S')}")
                status_lines.append(f"    Events Before First User: {user_info.get('events_before_first_user', 0)}")
                status_lines.append(f"    Total Users Connected: {user_info.get('total_users', 0)}")
                status_lines.append(f"    Raw Efficiency: {user_info.get('raw_efficiency', 0):.1f}%")
                status_lines.append(f"    Adjusted Efficiency: {user_info.get('adjusted_efficiency', 0):.1f}%")
            
            # Calculate efficiency percentages
            tick_efficiency = (ticks_received / ticks_created * 100) if ticks_created > 0 else 0
            delegation_rate = (ticks_delegated / ticks_received * 100) if ticks_received > 0 else 0
            queue_rate = (events_queued / events_detected * 100) if events_detected > 0 else 0
            collection_rate = (events_collected / events_detected * 100) if events_detected > 0 else 0
            emission_rate = (events_emitted / events_detected * 100) if events_detected > 0 else 0
            
            status_lines.append(f"\n  Processing Efficiency:")
            status_lines.append(f"    Tick Reception:     {tick_efficiency:.1f}%")
            status_lines.append(f"    Tick Delegation:    {delegation_rate:.1f}%")
            status_lines.append(f"    Event Queue Rate:   {queue_rate:.1f}%")
            status_lines.append(f"    Collection Rate:    {collection_rate:.1f}%")
            status_lines.append(f"    Emission Rate:      {emission_rate:.1f}%")
            
            # Collection efficiency
            empty_collections = flow.get('empty_collections', 0)
            non_empty_collections = flow.get('non_empty_collections', 0)
            total_collections = empty_collections + non_empty_collections
            slow_collections = flow.get('slow_collections', 0)
            
            if total_collections > 0:
                status_lines.append(f"\n  Collection Performance:")
                status_lines.append(f"    Total Collections:  {total_collections}")
                status_lines.append(f"    Empty Collections:  {empty_collections} ({empty_collections/total_collections*100:.1f}%)")
                status_lines.append(f"    Slow Collections:   {slow_collections} ({slow_collections/total_collections*100:.1f}%)")
                status_lines.append(f"    Empty Updates:      {flow.get('empty_updates', 0)}")
            
            # Event type breakdown
            if 'by_type' in flow:
                status_lines.append(f"\n  Event Pipeline by Type:")
                for event_type, metrics in flow['by_type'].items():
                    detected = metrics['detected']
                    if detected > 0:
                        queued = metrics['queued']
                        collected = metrics['collected']
                        emitted = metrics['emitted']
                        
                        queue_rate = (queued / detected * 100) if detected > 0 else 0
                        collect_rate = (collected / detected * 100) if detected > 0 else 0
                        emit_rate = (emitted / detected * 100) if detected > 0 else 0
                        
                        status_lines.append(f"    {event_type.capitalize():8} - Detected: {detected:4}, "
                                          f"Queued: {queued:4} ({queue_rate:5.1f}%), "
                                          f"Collected: {collected:4} ({collect_rate:5.1f}%), "
                                          f"Emitted: {emitted:4} ({emit_rate:5.1f}%)")
            
            # Error summary
            errors = flow.get('detection_errors', 0)
            drops = flow.get('queue_drops', 0)
            circuit_trips = flow.get('circuit_breaker_trips', 0)
            
            if errors > 0 or drops > 0 or circuit_trips > 0:
                status_lines.append(f"\n  ⚠️  Issues Detected:")
                if errors > 0:
                    status_lines.append(f"    Detection Errors:    {errors}")
                if drops > 0:
                    status_lines.append(f"    Queue Drops:         {drops}")
                if circuit_trips > 0:
                    status_lines.append(f"    Circuit Breaker:     {circuit_trips}")
            
            # Add tick flow analysis
            tick_flow = flow.get('tick_flow', {})
            if tick_flow.get('high_ticks_start', 0) > 0 or tick_flow.get('low_ticks_start', 0) > 0:
                status_lines.append(f"\n  Tick Flow Analysis:")
                status_lines.append(f"    High Ticks - Start: {tick_flow.get('high_ticks_start', 0)}, "
                                f"Emitted: {tick_flow.get('high_ticks_emitted', 0)}, "
                                f"Complete: {tick_flow.get('high_ticks_complete', 0)}")
                status_lines.append(f"    Low Ticks - Start: {tick_flow.get('low_ticks_start', 0)}, "
                                f"Emitted: {tick_flow.get('low_ticks_emitted', 0)}, "
                                f"Complete: {tick_flow.get('low_ticks_complete', 0)}")
                
                # Calculate tick efficiency
                total_start_ticks = tick_flow.get('high_ticks_start', 0) + tick_flow.get('low_ticks_start', 0)
                total_complete_ticks = tick_flow.get('total_ticks_complete', 0)
                if total_start_ticks > 0:
                    tick_efficiency = (total_complete_ticks / total_start_ticks * 100)
                    status_lines.append(f"    Tick Efficiency: {tick_efficiency:.1f}%")
            
            # Get trace for performance summary
            trace_key = f"{ticker}_active"
            if trace_key in self.traces:
                trace = self.traces[trace_key]
                
                # Show queue depths
                queue_metrics = []
                for key, value in trace.counters.items():
                    if 'queue_size_max' in key:
                        component = key.replace('_queue_size_max', '')
                        current = trace.counters.get(f'{component}_queue_size_latest', 0)
                        queue_metrics.append((component, value, current))
                
                if queue_metrics:
                    status_lines.append(f"\n  Queue Depths:")
                    for component, max_size, current_size in queue_metrics:
                        status_lines.append(f"    {component}: Current={current_size}, Max={max_size}")
        
        status_lines.append("=" * 80)
        
        # Join all lines
        full_status = '\n'.join(status_lines) + '\n'
        
        # Log using logger instead of print
        logger.info(full_status)
        
        # Write to log file
        self._write_to_log(full_status + '\n')
    
    def get_performance_report(self, ticker: str) -> Dict[str, Any]:
        """Generate detailed performance report for a ticker"""
        trace_key = f"{ticker}_active"
        if trace_key not in self.traces:
            return {}
        
        trace = self.traces[trace_key]
        report = {
            'ticker': ticker,
            'duration_seconds': time.time() - trace.start_time,
            'operations': {},
            'bottlenecks': [],
            'recommendations': [],
            'user_connection_impact': {}
        }
        
        # Add user connection analysis
        if trace.first_user_connection_time:
            report['user_connection_impact'] = {
                'first_connection_time': trace.first_user_connection_time,
                'events_before_connection': trace.events_before_first_user,
                'total_users': len(trace.user_connections),
                'adjusted_efficiency': trace.get_summary()['user_connections']['adjusted_efficiency']
            }
        
        # Analyze each operation's performance
        for key, metrics in trace.performance_metrics.items():
            if isinstance(metrics, dict) and 'samples' in metrics:
                avg_ms = metrics['total_ms'] / metrics['count'] if metrics['count'] > 0 else 0
                
                report['operations'][key] = {
                    'count': metrics['count'],
                    'avg_ms': round(avg_ms, 2),
                    'min_ms': round(metrics['min_ms'], 2),
                    'max_ms': round(metrics['max_ms'], 2)
                }
                
                # Identify bottlenecks
                if avg_ms > 50:  # Operations averaging over 50ms
                    report['bottlenecks'].append({
                        'operation': key,
                        'avg_ms': round(avg_ms, 2),
                        'impact': 'High' if avg_ms > 100 else 'Medium'
                    })
                
                # Flag WorkerPoolManager operations if slow
                if 'WorkerPoolManager' in key and avg_ms > 1000:
                    report['bottlenecks'].append({
                        'operation': key,
                        'avg_ms': round(avg_ms, 2),
                        'impact': 'Critical',
                        'note': 'WorkerPoolManager operations exceeding 1 second'
                    })
        
        # Generate recommendations
        if trace.counters.get('slow_detections', 0) > 10:
            report['recommendations'].append(
                "High number of slow detections. Consider optimizing detection algorithms."
            )
        
        if trace.counters.get('circuit_breaker_trips', 0) > 0:
            report['recommendations'].append(
                "Circuit breaker has been triggered. Check queue capacity and processing speed."
            )
        
        # Check emission efficiency
        events_detected = trace.counters.get('events_detected_total', 0)
        events_emitted = trace.counters.get('events_emitted_total', 0)
        if events_detected > 0:
            efficiency = (events_emitted / events_detected * 100)
            if efficiency < 80:
                report['recommendations'].append(
                    f"Low emission efficiency ({efficiency:.1f}%). Check filtering and queue drops."
                )
        
        # Add user connection recommendations
        if trace.events_before_first_user > 10:
            report['recommendations'].append(
                f"{trace.events_before_first_user} events occurred before first user connection. "
                "Consider implementing event buffering for late-joining users."
            )
        
        return report
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get system-wide metrics"""
        return {
            'uptime_seconds': time.time() - self.system_metrics['start_time'],
            'health_checks': self.system_metrics['health_checks'],
            'worker_adjustments': self.system_metrics['worker_adjustments'],
            'market_status_updates': self.system_metrics['market_status_updates'],
            'components_initialized': list(self.system_metrics['initialization_times'].keys()),
            'traced_tickers': list(self.traced_tickers),
            'user_connection_times': dict(self.user_connection_times)
        }
    
    def _get_or_create_trace(self, ticker: str) -> TickerTrace:
        """Get existing trace or create new one"""
        trace_key = f"{ticker}_active"
        
        if trace_key not in self.traces:
            trace_id = f"{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.traces[trace_key] = TickerTrace(ticker=ticker, trace_id=trace_id)
            
        return self.traces[trace_key]
    
    def get_trace_summary(self, ticker: str) -> Optional[Dict]:
        """Get summary of current trace for ticker"""
        trace_key = f"{ticker}_active"
        if trace_key in self.traces:
            return self.traces[trace_key].get_summary()
        return None
    
    def get_system_emission_traces(self) -> List[Dict]:
        """Get all emission-related traces for SYSTEM ticker"""
        trace_key = "SYSTEM_active"
        if trace_key not in self.traces:
            return []
        
        trace = self.traces[trace_key]
        emission_steps = []
        
        for step in trace.steps:
            if 'emission' in step.action or step.component == 'WebSocketPublisher':
                emission_steps.append({
                    'timestamp': step.timestamp,
                    'action': step.action,
                    'component': step.component,
                    'details': step.data_snapshot.get('details', {})
                })
        
        return emission_steps
    
    def get_traces(self, ticker: str) -> List[ProcessingStep]:
        """Get trace steps for a ticker - fixes test failure"""
        trace_key = f"{ticker}_active"
        if trace_key in self.traces:
            return self.traces[trace_key].steps
        return []

    def export_all(self, filename_prefix: str = "trace_all") -> Dict[str, Any]:
        """Export all traces from all tickers into a single file"""
        if not self.enabled:
            return {"success": False, "error": "Tracer not enabled"}
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"./logs/trace/{filename_prefix}_{timestamp}.json"
        
        all_traces = []
        ticker_summary = {}
        emission_count = 0
        
        try:
            with self._lock:
                # Collect all traces from all tickers
                for trace_key, trace in self.traces.items():
                    ticker = trace_key.replace('_active', '')
                    
                    if hasattr(trace, 'steps'):
                        for step in trace.steps:
                            # Use the to_dict method that ProcessingStep already has!
                            step_dict = step.to_dict()
                            
                            # The to_dict method already includes ticker, but let's ensure it matches our trace_key
                            step_dict['ticker'] = ticker
                            
                            all_traces.append(step_dict)
                            
                            # Count emission traces
                            if step.action == 'event_emitted':
                                emission_count += 1
                        
                        ticker_summary[ticker] = len(trace.steps)
            
            # Sort by timestamp
            all_traces.sort(key=lambda x: x.get('timestamp', 0))
            
            # Calculate duration if we have traces
            duration_seconds = 0
            if all_traces:
                duration_seconds = all_traces[-1]['timestamp'] - all_traces[0]['timestamp']
            
            # Create export data
            export_data = {
                'export_timestamp': datetime.now().isoformat(),
                'trace_id': f"ALL_{timestamp}",
                'ticker_summary': ticker_summary,
                'total_traces': len(all_traces),
                'duration_seconds': duration_seconds,
                'steps': all_traces
            }
            
            # Write to file
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            with open(filename, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            # Get file size
            file_size = os.path.getsize(filename)
            
            return {
                "success": True,
                "filepath": filename,
                "file_size": file_size,
                "trace_steps": len(all_traces),
                "emission_traces": emission_count,
                "tickers": list(ticker_summary.keys()),
                "ticker_counts": ticker_summary
            }
            
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc(),
                "available_traces": list(self.traces.keys()) if hasattr(self, 'traces') else []
            }
    
    def export_trace(self, ticker: str, filepath: Optional[str] = None):
        """Export trace to file for analysis - standardized for both CLI and web usage"""
        if filepath is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            os.makedirs('./logs/trace', exist_ok=True)
            filepath = f"./logs/trace/{ticker}_{timestamp}_trace.json"
        
        trace_key = f"{ticker}_active"
        
        # Write to trace log file for debugging
        self._write_to_log(f"[EXPORT] Attempting export for {ticker} to {filepath}\n")
        self._write_to_log(f"[EXPORT] Available traces: {list(self.traces.keys())}\n")
        
        if trace_key in self.traces:
            trace = self.traces[trace_key]
            
            # Write trace details to log
            self._write_to_log(f"[EXPORT] Exporting {ticker} trace with {len(trace.steps)} steps\n")
            
            # Count emission traces
            emission_traces = [s for s in trace.steps if 'emission' in s.action]
            self._write_to_log(f"[EXPORT] Found {len(emission_traces)} emission traces\n")
            
            # Log first few emission traces
            for i, step in enumerate(emission_traces[:5]):
                self._write_to_log(f"  - {step.action} at {step.timestamp}\n")
            
            # Actually export
            try:
                export_data = trace.export_json()
                
                # Ensure directory exists
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                
                with open(filepath, 'w') as f:
                    json.dump(export_data, f, indent=2)
                
                file_size = os.path.getsize(filepath)
                self._write_to_log(f"[EXPORT] 📁 Trace exported to: {filepath}\n")
                self._write_to_log(f"[EXPORT] File size: {file_size} bytes\n")
                
                # Return success info for programmatic use
                return {
                    'success': True,
                    'filepath': filepath,
                    'file_size': file_size,
                    'trace_steps': len(trace.steps),
                    'emission_traces': len(emission_traces)
                }
                
            except Exception as e:
                error_msg = f"Failed to export trace: {e}"
                self._write_to_log(f"[EXPORT] Error: {error_msg}\n")
                
                # Include traceback in log
                import traceback
                self._write_to_log(f"[EXPORT] Traceback: {traceback.format_exc()}\n")
                
                # Return error info
                return {
                    'success': False,
                    'error': str(e),
                    'filepath': filepath
                }
        else:
            warning_msg = f"No trace found for {ticker} (key: {trace_key})"
            self._write_to_log(f"[EXPORT] Warning: {warning_msg}\n")
            
            # Return not found info
            return {
                'success': False,
                'error': 'Trace not found',
                'available_traces': list(self.traces.keys())
            }
        
    def clear_trace(self, ticker: str):
        """Clear trace data for a ticker"""
        trace_key = f"{ticker}_active"
        if trace_key in self.traces:
            del self.traces[trace_key]
    
    def diagnose_event_loss(self, ticker: str) -> Dict[str, Any]:
        """Diagnose where events are being lost in the pipeline"""
        flow = self.get_flow_summary(ticker)
        if not flow:
            return {'error': 'No trace data available'}
        
        diagnosis = {
            'ticker': ticker,
            'pipeline_stages': {},
            'bottlenecks': [],
            'event_loss_points': [],
            'user_connection_analysis': {}
        }
        
        # Add user connection analysis
        user_info = flow.get('user_connections', {})
        if user_info:
            diagnosis['user_connection_analysis'] = {
                'first_user_time': user_info.get('first_user_time'),
                'events_before_first_user': user_info.get('events_before_first_user', 0),
                'raw_efficiency': user_info.get('raw_efficiency', 0),
                'adjusted_efficiency': user_info.get('adjusted_efficiency', 0),
                'efficiency_impact': user_info.get('raw_efficiency', 0) - user_info.get('adjusted_efficiency', 0)
            }
        
        # Analyze each stage
        stages = [
            ('tick_generation', flow.get('ticks_created', 0), flow.get('ticks_received', 0)),
            ('tick_processing', flow.get('ticks_received', 0), flow.get('ticks_delegated', 0)),
            ('event_detection', flow.get('ticks_delegated', 0), flow.get('events_detected', 0)),
            ('event_queueing', flow.get('events_detected', 0), flow.get('events_queued', 0)),
            ('event_collection', flow.get('events_queued', 0), flow.get('events_collected', 0)),
            ('event_emission', flow.get('events_collected', 0), flow.get('events_emitted', 0))
        ]
        
        for stage_name, input_count, output_count in stages:
            efficiency = (output_count / input_count * 100) if input_count > 0 else 0
            loss = input_count - output_count
            
            diagnosis['pipeline_stages'][stage_name] = {
                'input': input_count,
                'output': output_count,
                'efficiency': efficiency,
                'loss': loss
            }
            
            if loss > 0 and efficiency < 90:
                diagnosis['event_loss_points'].append({
                    'stage': stage_name,
                    'loss_count': loss,
                    'efficiency': efficiency
                })
        
        # Check for specific issues
        if flow.get('queue_drops', 0) > 0:
            diagnosis['bottlenecks'].append({
                'type': 'queue_drops',
                'count': flow['queue_drops'],
                'impact': 'Events lost due to queue overflow'
            })
        
        if flow.get('circuit_breaker_trips', 0) > 0:
            diagnosis['bottlenecks'].append({
                'type': 'circuit_breaker',
                'count': flow['circuit_breaker_trips'],
                'impact': 'Events blocked by circuit breaker'
            })
        
        if flow.get('detection_errors', 0) > 0:
            diagnosis['bottlenecks'].append({
                'type': 'detection_errors',
                'count': flow['detection_errors'],
                'impact': 'Failed event detections'
            })
        
        # Analyze by event type
        diagnosis['by_event_type'] = {}
        for event_type, metrics in flow.get('by_type', {}).items():
            if metrics['detected'] > 0:
                diagnosis['by_event_type'][event_type] = {
                    'detected': metrics['detected'],
                    'queued': metrics['queued'],
                    'collected': metrics['collected'],
                    'emitted': metrics['emitted'],
                    'queue_rate': (metrics['queued'] / metrics['detected'] * 100) if metrics['detected'] > 0 else 0,
                    'emit_rate': (metrics['emitted'] / metrics['detected'] * 100) if metrics['detected'] > 0 else 0
                }
        
        return diagnosis
    
    def get_collection_analysis(self, ticker: str = 'SYSTEM') -> Dict[str, Any]:
        """Analyze collection patterns to identify inefficiencies"""
        trace_key = f"{ticker}_active"
        if trace_key not in self.traces:
            return {}
        
        trace = self.traces[trace_key]
        analysis = {
            'ticker': ticker,
            'collection_stats': {},
            'timing_patterns': [],
            'recommendations': []
        }
        
        # Use the counters we already track
        empty_collections = trace.counters.get('empty_collections', 0)
        non_empty_collections = trace.counters.get('non_empty_collections', 0)
        total_collections = empty_collections + non_empty_collections
        
        if total_collections > 0:
            empty_percentage = (empty_collections / total_collections * 100)
            
            analysis['collection_stats'] = {
                'total_collections': total_collections,
                'empty_collections': empty_collections,
                'non_empty_collections': non_empty_collections,
                'empty_percentage': empty_percentage,
                'avg_events_when_not_empty': (
                    trace.counters.get('events_collected', 0) / non_empty_collections
                    if non_empty_collections > 0 else 0
                )
            }
            
            # Generate recommendations
            if empty_percentage > 90:
                analysis['recommendations'].append(
                    "Over 90% of collections are empty. Consider increasing collection interval."
                )
            
            # Find collection timing patterns from steps
            collections = []
            for i, step in enumerate(trace.steps):
                if step.action == 'events_collected':
                    collection_data = {
                        'timestamp': step.timestamp,
                        'events_found': self._ensure_int(step.data_snapshot.get('output_count', 0)),
                        'empty': step.data_snapshot.get('output_count', 0) == 0
                    }
                    collections.append(collection_data)
            
            if len(collections) > 10:
                # Look at last 10 collections
                recent = collections[-10:]
                recent_empty = sum(1 for c in recent if c['empty'])
                
                analysis['timing_patterns'] = {
                    'recent_empty_rate': (recent_empty / 10 * 100),
                    'total_collections_analyzed': len(collections)
                }
        
        return analysis
    
    def get_all_active_traces(self) -> List[str]:
        """Get list of all tickers with active traces"""
        return [key.replace('_active', '') for key in self.traces.keys()]
    
    def rotate_log_file(self):
        """Rotate log file if it gets too large"""
        try:
            filename = self._get_log_filename()
            if os.path.exists(filename):
                file_size_mb = os.path.getsize(filename) / (1024 * 1024)
                
                # Rotate if larger than 100MB
                if file_size_mb > 100:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    new_filename = f"./logs/trace_{timestamp}_rotated.log"
                    os.rename(filename, new_filename)
                    logger.info(f"Log rotated: {new_filename}")
        except Exception as e:
            logger.error(f"Error rotating log file: {e}")
    
    def get_log_stats(self) -> Dict[str, Any]:
        """Get statistics about the current log file"""
        try:
            filename = self._get_log_filename()
            if os.path.exists(filename):
                size_mb = os.path.getsize(filename) / (1024 * 1024)
                with open(filename, 'r') as f:
                    line_count = sum(1 for _ in f)
                
                return {
                    'filename': filename,
                    'size_mb': round(size_mb, 2),
                    'line_count': line_count,
                    'active_traces': len(self.traces),
                    'traced_tickers': list(self.traced_tickers)
                }
        except Exception as e:
            logger.error(f"Error getting log stats: {e}")
            return {}
    
    def verify_stage_transition(self, from_stage: str, to_stage: str, ticker: str) -> Dict[str, Any]:
        """Verify events between stages and identify losses"""
        trace = self._get_or_create_trace(ticker)
        
        # Map stage names to counter keys
        stage_counter_map = {
            'detected': 'events_detected_total',
            'queued': 'events_queued_total',
            'collected': 'events_collected',
            'emitted': 'events_emitted_total'
        }
        
        from_count = trace.counters.get(stage_counter_map.get(from_stage, f'events_{from_stage}'), 0)
        to_count = trace.counters.get(stage_counter_map.get(to_stage, f'events_{to_stage}'), 0)
        
        verification = {
            'from_stage': from_stage,
            'to_stage': to_stage,
            'from_count': from_count,
            'to_count': to_count,
            'efficiency': (to_count / from_count * 100) if from_count > 0 else 0,
            'lost': from_count - to_count
        }
        
        # Log warnings for significant losses
        if verification['efficiency'] < 90 and verification['lost'] > 5:
            warning_msg = (f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] "
                        f"[WARNING] Stage transition loss: {from_stage} → {to_stage} for {ticker}: "
                        f"{verification['lost']} events lost ({verification['efficiency']:.1f}% efficiency)\n")
            self._write_to_log(warning_msg)
        
        return verification

    def validate_trace_accuracy(self, ticker: str) -> Dict[str, Any]:
        """Validate trace data against known good states"""
        trace = self._get_or_create_trace(ticker)
        validations = {
            'ticker': ticker,
            'issues': [],
            'warnings': []
        }
        
        # Check for impossible efficiencies
        flow = self.get_flow_summary(ticker)
        for event_type, data in flow.get('by_type', {}).items():
            if data['detected'] > 0:
                # Allow small margin for timing differences, but flag clear double counting
                if data['emitted'] > data['detected'] * 1.05:  # 5% margin
                    validations['issues'].append(
                        f"{event_type}: Emitted ({data['emitted']}) > Detected ({data['detected']}) - "
                        f"Possible double counting"
                    )
        
        # Check for missing stages
        if trace.counters.get('events_detected_total', 0) > 0:
            if trace.counters.get('events_queued_total', 0) == 0:
                validations['issues'].append("Events detected but none queued")
        
        # Check for reasonable ratios
        if trace.counters.get('ticks_received', 0) > 0:
            events_per_tick = (trace.counters.get('events_detected_total', 0) / 
                            trace.counters.get('ticks_received', 0))
            if events_per_tick > 1:
                validations['warnings'].append(
                    f"High event rate: {events_per_tick:.2f} events per tick"
                )
        
        # Verify event flow integrity
        for stage_from, stage_to in [
            ('detected', 'queued'),
            ('queued', 'collected'),
            ('collected', 'emitted')
        ]:
            verification = self.verify_stage_transition(stage_from, stage_to, ticker)
            if verification['efficiency'] < 50:
                validations['issues'].append(
                    f"Low efficiency {stage_from}→{stage_to}: {verification['efficiency']:.1f}%"
                )
        
        return validations

    def trace_event_journey(self, ticker: str, event_type: str, price: float) -> List[Dict]:
        """Trace a specific event through the entire pipeline"""
        normalized_type = normalize_event_type(event_type)
        event_key = f"{ticker}:{normalized_type}:{price}"
        journey = []
        
        trace = self._get_or_create_trace(ticker)
        for step in trace.steps:
            details = step.data_snapshot.get('details', {})
            step_event_type = normalize_event_type(details.get('event_type', ''))
            
            if (step_event_type == normalized_type and 
                abs(details.get('price', 0) - price) < 0.01):  # Price match with small tolerance
                journey.append({
                    'timestamp': step.timestamp,
                    'component': step.component,
                    'action': step.action,
                    'details': details
                })
        
        return journey

    def get_quality_metrics(self, ticker: str) -> Dict[str, Any]:
        """Get comprehensive quality metrics for a ticker"""
        flow = self.get_flow_summary(ticker)
        validations = self.validate_trace_accuracy(ticker)
        
        metrics = {
            'ticker': ticker,
            'overall_quality_score': 100,  # Start at 100 and deduct
            'issues': [],
            'metrics': {}
        }
        
        # Only check overall flow, not individual event types for minor differences
        overall_detected = flow.get('events_detected', 0)
        overall_emitted = flow.get('events_emitted', 0)
        
        if overall_detected > 0:
            # Use adjusted efficiency if available
            user_info = flow.get('user_connections', {})
            if user_info and user_info.get('adjusted_efficiency') is not None:
                overall_efficiency = user_info['adjusted_efficiency']
                metrics['metrics']['adjusted_efficiency'] = overall_efficiency
                metrics['metrics']['raw_efficiency'] = user_info.get('raw_efficiency', 0)
                metrics['metrics']['events_before_user'] = user_info.get('events_before_first_user', 0)
            else:
                overall_efficiency = (overall_emitted / overall_detected * 100)
                metrics['metrics']['overall_efficiency'] = overall_efficiency
            
            # Deduct based on overall efficiency
            if overall_efficiency < 50:
                metrics['overall_quality_score'] -= 30
                metrics['issues'].append(f"Low overall efficiency: {overall_efficiency:.1f}%")
            elif overall_efficiency < 80:
                metrics['overall_quality_score'] -= 15
                metrics['issues'].append(f"Moderate efficiency: {overall_efficiency:.1f}%")
            elif overall_efficiency > 105:
                metrics['overall_quality_score'] -= 20
                metrics['issues'].append(f"Over-efficiency: {overall_efficiency:.1f}% (possible double counting)")
        
        # Check validation issues
        for issue in validations['issues']:
            metrics['overall_quality_score'] -= 5
            metrics['issues'].append(issue)
        
        # Check for warnings
        for warning in validations.get('warnings', []):
            metrics['overall_quality_score'] -= 2
        
        # Check collection efficiency
        empty_collections = flow.get('empty_collections', 0)
        non_empty_collections = flow.get('non_empty_collections', 0)
        total_collections = empty_collections + non_empty_collections
        
        # Initialize empty_rate before using it
        empty_rate = 0
        if total_collections > 0:
            empty_rate = (empty_collections / total_collections * 100)
            metrics['metrics']['empty_collection_rate'] = empty_rate
            
            if empty_rate > 95:
                metrics['overall_quality_score'] -= 10
                metrics['issues'].append(f"Very high empty collection rate: {empty_rate:.1f}%")
        
        # Check for drops
        drops = flow.get('queue_drops', 0)
        if drops > 0 and overall_detected > 0:
            drop_rate = (drops / overall_detected * 100)
            if drop_rate > 10:
                metrics['overall_quality_score'] -= 10
                metrics['issues'].append(f"High drop rate: {drop_rate:.1f}%")
        
        metrics['overall_quality_score'] = max(0, metrics['overall_quality_score'])
        
        # Add recommendations
        metrics['recommendations'] = []
        if metrics['overall_quality_score'] < 80:
            if overall_detected > 0 and overall_efficiency < 80:
                metrics['recommendations'].append(
                    "Review event pipeline for losses. Check queue capacity and processing speed."
                )
            
            if empty_rate > 90:
                metrics['recommendations'].append(
                    "High empty collection rate. Consider batching or increasing collection interval."
                )
            
            # Add user connection recommendations
            if flow.get('user_connections', {}).get('events_before_first_user', 0) > 10:
                metrics['recommendations'].append(
                    "Implement event buffering to capture events before users connect."
                )
        
        return metrics

    @staticmethod
    def create_trace_event(ticker: str, 
                        component: str,
                        action: str,
                        start_time: float,
                        input_count: int = 1,
                        output_count: int = 0,
                        details: Optional[Dict[str, Any]] = None,
                        error: Optional[str] = None) -> None:
        """
        Create a standardized trace event if tracing is enabled.
        
        Args:
            ticker: Stock ticker
            component: Component name
            action: Action being traced
            start_time: Start time for duration calculation
            input_count: Number of inputs processed
            output_count: Number of outputs generated
            details: Additional details dict
            error: Error message if applicable
        """
        if not tracer.should_trace(ticker):
            return
            
        duration_ms = (time.time() - start_time) * 1000
        
        trace_data = {
            'timestamp': time.time(),
            'input_count': input_count,
            'output_count': output_count,
            'duration_ms': duration_ms
        }
        
        if details:
            trace_data['details'] = details
            
        if error:
            trace_data['error'] = error
            
        tracer.trace(
            ticker=ticker,
            component=component,
            action=action,
            data=trace_data
        )

# Global singleton
tracer = DebugTracer()

# Decorator for automatic method tracing (optional utility)
def trace_method(component: str):
    """Decorator for automatic method tracing"""
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            # Extract ticker if available
            ticker = None
            if args and hasattr(args[0], 'ticker'):
                ticker = args[0].ticker
            elif 'ticker' in kwargs:
                ticker = kwargs['ticker']
                
            if ticker and tracer.should_trace(ticker):
                start_time = time.time()
                
                try:
                    result = func(self, *args, **kwargs)
                    
                    # Auto-trace successful completion
                    tracer.trace(
                        ticker=ticker,
                        component=component,
                        action=f"{func.__name__}_complete",
                        data={
                            'duration_ms': (time.time() - start_time) * 1000,
                            'success': True
                        }
                    )
                    
                    return result
                    
                except Exception as e:
                    # Auto-trace errors
                    tracer.trace(
                        ticker=ticker,
                        component=component,
                        action=f"{func.__name__}_error",
                        data={
                            'duration_ms': (time.time() - start_time) * 1000,
                            'error': str(e),
                            'error_type': type(e).__name__
                        }
                    )
                    raise
            else:
                return func(self, *args, **kwargs)
                
        return wrapper
    return decorator

# Periodic status reporting thread function
def periodic_trace_status():
    """Function to be run in a thread for periodic status updates"""
    while True:
        time.sleep(30)
        if tracer.enabled:
            tracer.print_flow_status()
            
            # Check if log rotation needed
            tracer.rotate_log_file()