"""
Channel metrics collection and monitoring system.

Provides comprehensive performance tracking, health monitoring, and 
observability for the multi-channel processing system.

Sprint 105: Core Channel Infrastructure Implementation
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable, TYPE_CHECKING
from enum import Enum
import time
import threading
from collections import deque, defaultdict

from config.logging_config import get_domain_logger, LogDomain

# Type-only imports to avoid circular dependencies
if TYPE_CHECKING:
    from .base_channel import ChannelStatus

logger = get_domain_logger(LogDomain.CORE, 'channel_metrics')


@dataclass
class ChannelMetrics:
    """
    Comprehensive metrics tracking for a single channel.
    Thread-safe and high-performance for real-time processing.
    """
    channel_name: str
    channel_id: str
    
    # Processing metrics
    processed_count: int = 0
    error_count: int = 0
    events_generated: int = 0
    
    # Timing metrics
    last_processing_time_ms: float = 0.0
    avg_processing_time_ms: float = 0.0
    min_processing_time_ms: float = float('inf')
    max_processing_time_ms: float = 0.0
    
    # Batch processing metrics
    batches_processed: int = 0
    batch_failures: int = 0
    avg_batch_size: float = 0.0
    
    # Queue metrics
    queue_overflows: int = 0
    queue_max_size_reached: int = 0
    
    # Circuit breaker metrics
    circuit_breaker_opens: int = 0
    circuit_breaker_closes: int = 0
    circuit_breaker_rejections: int = 0
    
    # Timing
    start_time: Optional[float] = None
    stop_time: Optional[float] = None
    last_activity: float = field(default_factory=time.time)
    
    # Thread safety
    _lock: threading.RLock = field(default_factory=threading.RLock)
    
    # Performance tracking (last 100 processing times for percentiles)
    _processing_times: deque = field(default_factory=lambda: deque(maxlen=100))
    
    def mark_started(self):
        """Mark channel as started"""
        with self._lock:
            self.start_time = time.time()
            self.last_activity = self.start_time
    
    def mark_stopped(self):
        """Mark channel as stopped"""
        with self._lock:
            self.stop_time = time.time()
    
    def increment_processed_count(self):
        """Increment processed message count"""
        with self._lock:
            self.processed_count += 1
            self.last_activity = time.time()
    
    def increment_error_count(self):
        """Increment error count"""
        with self._lock:
            self.error_count += 1
            self.last_activity = time.time()
    
    def increment_events_generated(self, count: int = 1):
        """Increment events generated count"""
        with self._lock:
            self.events_generated += count
            self.last_activity = time.time()
    
    def increment_batches_processed(self):
        """Increment batches processed count"""
        with self._lock:
            self.batches_processed += 1
    
    def increment_batch_failures(self):
        """Increment batch failure count"""
        with self._lock:
            self.batch_failures += 1
    
    def increment_queue_overflows(self):
        """Increment queue overflow count"""
        with self._lock:
            self.queue_overflows += 1
    
    def increment_circuit_breaker_opens(self):
        """Increment circuit breaker opens count"""
        with self._lock:
            self.circuit_breaker_opens += 1
    
    def increment_circuit_breaker_closes(self):
        """Increment circuit breaker closes count"""
        with self._lock:
            self.circuit_breaker_closes += 1
    
    def increment_circuit_breaker_rejections(self):
        """Increment circuit breaker rejections count"""
        with self._lock:
            self.circuit_breaker_rejections += 1
    
    def update_processing_time(self, duration_ms: float):
        """Update processing time metrics"""
        with self._lock:
            self.last_processing_time_ms = duration_ms
            self._processing_times.append(duration_ms)
            
            # Update min/max
            self.min_processing_time_ms = min(self.min_processing_time_ms, duration_ms)
            self.max_processing_time_ms = max(self.max_processing_time_ms, duration_ms)
            
            # Update average using exponential moving average
            if self.processed_count == 1:
                self.avg_processing_time_ms = duration_ms
            else:
                alpha = 0.1  # Smoothing factor
                self.avg_processing_time_ms = (alpha * duration_ms + 
                                             (1 - alpha) * self.avg_processing_time_ms)
            
            self.last_activity = time.time()
    
    def update_batch_size(self, batch_size: int):
        """Update average batch size"""
        with self._lock:
            if self.batches_processed == 0:
                self.avg_batch_size = batch_size
            else:
                # Update average batch size
                total_items = self.avg_batch_size * (self.batches_processed - 1) + batch_size
                self.avg_batch_size = total_items / self.batches_processed
    
    def get_error_rate(self) -> float:
        """Calculate error rate as percentage"""
        with self._lock:
            if self.processed_count == 0:
                return 0.0
            return (self.error_count / self.processed_count) * 100.0
    
    def get_uptime_seconds(self) -> float:
        """Get uptime in seconds"""
        with self._lock:
            if not self.start_time:
                return 0.0
            end_time = self.stop_time if self.stop_time else time.time()
            return end_time - self.start_time
    
    def get_processing_percentiles(self) -> Dict[str, float]:
        """Get processing time percentiles from recent samples"""
        with self._lock:
            if not self._processing_times:
                return {'p50': 0.0, 'p95': 0.0, 'p99': 0.0}
            
            sorted_times = sorted(self._processing_times)
            length = len(sorted_times)
            
            return {
                'p50': sorted_times[int(length * 0.5)] if length > 0 else 0.0,
                'p95': sorted_times[int(length * 0.95)] if length > 1 else sorted_times[0] if length > 0 else 0.0,
                'p99': sorted_times[int(length * 0.99)] if length > 1 else sorted_times[0] if length > 0 else 0.0
            }
    
    def get_throughput_per_second(self) -> float:
        """Calculate throughput in events per second"""
        with self._lock:
            uptime = self.get_uptime_seconds()
            if uptime <= 0:
                return 0.0
            return self.processed_count / uptime
    
    def reset_metrics(self):
        """Reset all metrics (useful for testing)"""
        with self._lock:
            self.processed_count = 0
            self.error_count = 0
            self.events_generated = 0
            self.last_processing_time_ms = 0.0
            self.avg_processing_time_ms = 0.0
            self.min_processing_time_ms = float('inf')
            self.max_processing_time_ms = 0.0
            self.batches_processed = 0
            self.batch_failures = 0
            self.avg_batch_size = 0.0
            self.queue_overflows = 0
            self.circuit_breaker_opens = 0
            self.circuit_breaker_closes = 0
            self.circuit_breaker_rejections = 0
            self._processing_times.clear()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for serialization"""
        with self._lock:
            percentiles = self.get_processing_percentiles()
            
            return {
                'channel_name': self.channel_name,
                'channel_id': self.channel_id,
                'processed_count': self.processed_count,
                'error_count': self.error_count,
                'error_rate_percent': self.get_error_rate(),
                'events_generated': self.events_generated,
                'throughput_per_second': self.get_throughput_per_second(),
                'processing_times': {
                    'last_ms': self.last_processing_time_ms,
                    'avg_ms': self.avg_processing_time_ms,
                    'min_ms': self.min_processing_time_ms if self.min_processing_time_ms != float('inf') else 0.0,
                    'max_ms': self.max_processing_time_ms,
                    'percentiles': percentiles
                },
                'batching': {
                    'batches_processed': self.batches_processed,
                    'batch_failures': self.batch_failures,
                    'avg_batch_size': self.avg_batch_size
                },
                'queue_metrics': {
                    'overflows': self.queue_overflows,
                    'max_size_reached': self.queue_max_size_reached
                },
                'circuit_breaker': {
                    'opens': self.circuit_breaker_opens,
                    'closes': self.circuit_breaker_closes,
                    'rejections': self.circuit_breaker_rejections
                },
                'timing': {
                    'uptime_seconds': self.get_uptime_seconds(),
                    'start_time': self.start_time,
                    'stop_time': self.stop_time,
                    'last_activity': self.last_activity
                }
            }


@dataclass
class ChannelHealthStatus:
    """Health status for a channel"""
    channel_name: str
    channel_id: str
    status: 'ChannelStatus'  # Forward reference to avoid circular import
    is_healthy: bool
    uptime_seconds: float
    processed_count: int
    error_count: int
    error_rate: float
    avg_processing_time_ms: float
    queue_size: int
    queue_utilization: float
    circuit_breaker_open: bool
    consecutive_errors: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'channel_name': self.channel_name,
            'channel_id': self.channel_id,
            'status': self.status.value,
            'is_healthy': self.is_healthy,
            'uptime_seconds': self.uptime_seconds,
            'processed_count': self.processed_count,
            'error_count': self.error_count,
            'error_rate': self.error_rate,
            'avg_processing_time_ms': self.avg_processing_time_ms,
            'queue_size': self.queue_size,
            'queue_utilization': self.queue_utilization,
            'circuit_breaker_open': self.circuit_breaker_open,
            'consecutive_errors': self.consecutive_errors
        }


class MetricsAggregator:
    """Aggregates metrics across multiple channels"""
    
    def __init__(self):
        self._channel_metrics: Dict[str, ChannelMetrics] = {}
        self._lock = threading.RLock()
    
    def register_channel_metrics(self, metrics: ChannelMetrics):
        """Register channel metrics for aggregation"""
        with self._lock:
            self._channel_metrics[metrics.channel_name] = metrics
    
    def unregister_channel_metrics(self, channel_name: str):
        """Unregister channel metrics"""
        with self._lock:
            self._channel_metrics.pop(channel_name, None)
    
    def get_aggregate_metrics(self) -> Dict[str, Any]:
        """Get aggregated metrics across all channels"""
        with self._lock:
            if not self._channel_metrics:
                return {}
            
            # Aggregate counts
            total_processed = sum(m.processed_count for m in self._channel_metrics.values())
            total_errors = sum(m.error_count for m in self._channel_metrics.values())
            total_events = sum(m.events_generated for m in self._channel_metrics.values())
            
            # Aggregate processing times (weighted average)
            weighted_avg_time = 0.0
            if total_processed > 0:
                weighted_avg_time = sum(
                    m.avg_processing_time_ms * m.processed_count 
                    for m in self._channel_metrics.values()
                ) / total_processed
            
            # Health status
            healthy_channels = sum(1 for m in self._channel_metrics.values() 
                                 if self._is_metrics_healthy(m))
            
            return {
                'total_channels': len(self._channel_metrics),
                'healthy_channels': healthy_channels,
                'unhealthy_channels': len(self._channel_metrics) - healthy_channels,
                'total_processed': total_processed,
                'total_errors': total_errors,
                'total_events_generated': total_events,
                'overall_error_rate': (total_errors / max(total_processed, 1)) * 100.0,
                'weighted_avg_processing_time_ms': weighted_avg_time,
                'channel_breakdown': {
                    name: metrics.to_dict() 
                    for name, metrics in self._channel_metrics.items()
                }
            }
    
    def _is_metrics_healthy(self, metrics: ChannelMetrics) -> bool:
        """Check if metrics indicate healthy channel"""
        # Error rate check
        if metrics.get_error_rate() > 10.0:  # >10% error rate
            return False
        
        # Processing time check
        if metrics.avg_processing_time_ms > 5000:  # >5 seconds
            return False
        
        # Circuit breaker check
        if metrics.circuit_breaker_opens > metrics.circuit_breaker_closes:
            return False
        
        return True
    
    def get_channel_metrics(self, channel_name: str) -> Optional[ChannelMetrics]:
        """Get metrics for specific channel"""
        with self._lock:
            return self._channel_metrics.get(channel_name)


class MetricsCollector:
    """
    Central metrics collection system for all channels.
    Provides observability and monitoring capabilities.
    """
    
    def __init__(self):
        self.aggregator = MetricsAggregator()
        self._alert_callbacks: List[Callable[[str, Dict[str, Any]], None]] = []
        self._monitoring_enabled = True
        
        # Alert thresholds
        self.error_rate_threshold = 5.0  # 5%
        self.processing_time_threshold = 1000.0  # 1 second
        self.queue_utilization_threshold = 0.8  # 80%
        
    def register_channel(self, metrics: ChannelMetrics):
        """Register channel for metrics collection"""
        self.aggregator.register_channel_metrics(metrics)
        logger.info(f"Registered metrics collection for channel {metrics.channel_name}")
    
    def unregister_channel(self, channel_name: str):
        """Unregister channel from metrics collection"""
        self.aggregator.unregister_channel_metrics(channel_name)
        logger.info(f"Unregistered metrics collection for channel {channel_name}")
    
    def add_alert_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
        """Add callback for metric alerts"""
        self._alert_callbacks.append(callback)
    
    def check_and_alert(self):
        """Check metrics and trigger alerts if thresholds exceeded"""
        if not self._monitoring_enabled:
            return
        
        aggregate = self.aggregator.get_aggregate_metrics()
        
        # Check overall error rate
        if aggregate.get('overall_error_rate', 0) > self.error_rate_threshold:
            self._trigger_alert('high_error_rate', {
                'error_rate': aggregate['overall_error_rate'],
                'threshold': self.error_rate_threshold,
                'total_errors': aggregate.get('total_errors', 0)
            })
        
        # Check individual channel metrics
        for channel_name, channel_metrics in aggregate.get('channel_breakdown', {}).items():
            self._check_channel_alerts(channel_name, channel_metrics)
    
    def _check_channel_alerts(self, channel_name: str, metrics: Dict[str, Any]):
        """Check individual channel metrics for alerts"""
        
        # Processing time alert
        processing_time = metrics.get('processing_times', {}).get('avg_ms', 0)
        if processing_time > self.processing_time_threshold:
            self._trigger_alert(f'high_processing_time_{channel_name}', {
                'channel': channel_name,
                'processing_time_ms': processing_time,
                'threshold': self.processing_time_threshold
            })
        
        # Error rate alert
        error_rate = metrics.get('error_rate_percent', 0)
        if error_rate > self.error_rate_threshold:
            self._trigger_alert(f'high_error_rate_{channel_name}', {
                'channel': channel_name,
                'error_rate': error_rate,
                'threshold': self.error_rate_threshold
            })
    
    def _trigger_alert(self, alert_type: str, alert_data: Dict[str, Any]):
        """Trigger alert to all registered callbacks"""
        for callback in self._alert_callbacks:
            try:
                callback(alert_type, alert_data)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}", exc_info=True)
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get comprehensive system metrics"""
        return self.aggregator.get_aggregate_metrics()
    
    def get_channel_health_report(self) -> List[ChannelHealthStatus]:
        """Get health report for all channels"""
        # This would be populated by channels calling get_health_status()
        # Implementation depends on channel registry
        return []
    
    def enable_monitoring(self):
        """Enable metrics monitoring and alerting"""
        self._monitoring_enabled = True
        logger.info("Channel metrics monitoring enabled")
    
    def disable_monitoring(self):
        """Disable metrics monitoring and alerting"""
        self._monitoring_enabled = False
        logger.info("Channel metrics monitoring disabled")
    
    def export_metrics(self, format_type: str = 'json') -> str:
        """Export metrics in specified format"""
        metrics = self.get_system_metrics()
        
        if format_type == 'json':
            import json
            return json.dumps(metrics, indent=2, default=str)
        elif format_type == 'prometheus':
            # Basic Prometheus format
            lines = []
            for key, value in metrics.items():
                if isinstance(value, (int, float)):
                    lines.append(f'channel_system_{key} {value}')
            return '\n'.join(lines)
        else:
            return str(metrics)