"""
Redis Performance Monitor - Sprint 12 Phase 2
Comprehensive monitoring for Redis integration performance and health.

Tracks message delivery latency, throughput, error rates, and system health
to ensure <100ms end-to-end performance targets are maintained.
"""

import logging
import time
import threading
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from collections import deque, defaultdict
from enum import Enum
import json
import statistics

logger = logging.getLogger(__name__)

class HealthStatus(Enum):
    """System health status levels."""
    HEALTHY = "healthy"
    WARNING = "warning"
    DEGRADED = "degraded"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class PerformanceMetrics:
    """Performance metrics for Redis operations."""
    # Latency metrics
    avg_latency_ms: float = 0.0
    median_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    
    # Throughput metrics
    messages_per_second: float = 0.0
    total_messages: int = 0
    successful_messages: int = 0
    failed_messages: int = 0
    
    # Error metrics
    error_rate: float = 0.0
    consecutive_errors: int = 0
    last_error_time: Optional[float] = None
    
    # Timing
    measurement_period_seconds: float = 60.0
    last_updated: float = field(default_factory=time.time)

@dataclass
class ChannelMetrics:
    """Per-channel performance metrics."""
    channel_name: str
    message_count: int = 0
    total_processing_time_ms: float = 0.0
    avg_processing_time_ms: float = 0.0
    error_count: int = 0
    last_message_time: Optional[float] = None
    
    def update_processing_time(self, processing_time_ms: float):
        """Update processing time metrics."""
        self.total_processing_time_ms += processing_time_ms
        self.message_count += 1
        self.avg_processing_time_ms = self.total_processing_time_ms / self.message_count
        self.last_message_time = time.time()

class RedisPerformanceMonitor:
    """
    Comprehensive performance monitor for Redis integration.
    
    Tracks:
    - Message delivery latency (target: <100ms end-to-end)
    - Channel throughput and processing times
    - Connection health and error rates
    - User filtering performance
    - Dashboard update responsiveness
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize performance monitor."""
        self.config = config
        
        # Performance tracking
        self._latency_samples = deque(maxlen=1000)
        self._throughput_window = deque(maxlen=60)  # 60 seconds of data
        self._channel_metrics: Dict[str, ChannelMetrics] = {}
        
        # Health status
        self._health_status = HealthStatus.HEALTHY
        self._health_issues: List[str] = []
        
        # Alert thresholds
        self._latency_warning_threshold = 50.0  # 50ms warning
        self._latency_critical_threshold = 100.0  # 100ms critical
        self._error_rate_warning_threshold = 0.05  # 5% error rate
        self._error_rate_critical_threshold = 0.10  # 10% error rate
        
        # Monitoring state
        self._monitoring_active = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._stats_lock = threading.RLock()
        
        # Performance counters
        self._counters = defaultdict(int)
        self._timers = defaultdict(list)
        
        logger.info("RedisPerformanceMonitor initialized")
    
    def start_monitoring(self):
        """Start background performance monitoring."""
        if self._monitoring_active:
            logger.warning("Performance monitoring already active")
            return
        
        self._monitoring_active = True
        self._monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            name="RedisPerformanceMonitor",
            daemon=True
        )
        self._monitor_thread.start()
        
        logger.info("REDIS-PERFORMANCE-MONITOR: Monitoring started")
    
    def stop_monitoring(self):
        """Stop background monitoring."""
        if not self._monitoring_active:
            return
        
        self._monitoring_active = False
        
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5)
        
        logger.info("REDIS-PERFORMANCE-MONITOR: Monitoring stopped")
    
    def _monitoring_loop(self):
        """Background monitoring loop."""
        while self._monitoring_active:
            try:
                # Update performance metrics
                self._update_performance_metrics()
                
                # Check health status
                self._assess_health_status()
                
                # Log performance summary
                if logger.isEnabledFor(logging.DEBUG):
                    self._log_performance_summary()
                
                # Sleep until next monitoring cycle
                time.sleep(5)  # 5-second monitoring interval
                
            except Exception as e:
                logger.error("REDIS-PERFORMANCE-MONITOR: Error in monitoring loop: %s", e)
                time.sleep(10)  # Longer sleep on error
    
    def record_message_latency(self, channel: str, start_time: float, end_time: float):
        """Record end-to-end message latency."""
        latency_ms = (end_time - start_time) * 1000
        
        with self._stats_lock:
            self._latency_samples.append(latency_ms)
            self._counters['total_messages'] += 1
            
            # Update channel metrics
            if channel not in self._channel_metrics:
                self._channel_metrics[channel] = ChannelMetrics(channel_name=channel)
            
            self._channel_metrics[channel].update_processing_time(latency_ms)
            
            # Record in throughput window
            self._throughput_window.append(time.time())
        
        # Log slow messages
        if latency_ms > self._latency_warning_threshold:
            logger.warning("REDIS-PERFORMANCE-MONITOR: Slow message processing - %s: %.1fms", 
                          channel, latency_ms)
    
    def record_processing_error(self, channel: str, error: Exception):
        """Record processing error for health tracking."""
        with self._stats_lock:
            self._counters['total_errors'] += 1
            self._counters['consecutive_errors'] += 1
            
            # Update channel error count
            if channel in self._channel_metrics:
                self._channel_metrics[channel].error_count += 1
            
            # Reset consecutive success counter
            self._counters['consecutive_successes'] = 0
        
        logger.error("REDIS-PERFORMANCE-MONITOR: Processing error in %s: %s", channel, error)
    
    def record_processing_success(self, channel: str):
        """Record successful message processing."""
        with self._stats_lock:
            self._counters['successful_messages'] += 1
            self._counters['consecutive_successes'] += 1
            
            # Reset consecutive error counter
            self._counters['consecutive_errors'] = 0
    
    def record_user_filter_performance(self, filter_type: str, processing_time_ms: float, 
                                     filtered_count: int, total_count: int):
        """Record user filtering performance metrics."""
        with self._stats_lock:
            filter_key = f'filter_{filter_type}'
            self._timers[f'{filter_key}_times'].append(processing_time_ms)
            self._counters[f'{filter_key}_filtered'] += filtered_count
            self._counters[f'{filter_key}_total'] += total_count
            
            # Keep only recent samples
            if len(self._timers[f'{filter_key}_times']) > 100:
                self._timers[f'{filter_key}_times'] = self._timers[f'{filter_key}_times'][-50:]
    
    def record_websocket_broadcast(self, event_type: str, user_count: int, broadcast_time_ms: float):
        """Record WebSocket broadcast performance."""
        with self._stats_lock:
            broadcast_key = f'websocket_{event_type}'
            self._counters[f'{broadcast_key}_broadcasts'] += 1
            self._counters[f'{broadcast_key}_users'] += user_count
            self._timers[f'{broadcast_key}_times'].append(broadcast_time_ms)
            
            # Keep only recent samples
            if len(self._timers[f'{broadcast_key}_times']) > 100:
                self._timers[f'{broadcast_key}_times'] = self._timers[f'{broadcast_key}_times'][-50:]
    
    def _update_performance_metrics(self):
        """Update aggregated performance metrics."""
        with self._stats_lock:
            # Calculate latency metrics
            if self._latency_samples:
                latencies = list(self._latency_samples)
                self._performance_metrics = PerformanceMetrics(
                    avg_latency_ms=statistics.mean(latencies),
                    median_latency_ms=statistics.median(latencies),
                    p95_latency_ms=self._calculate_percentile(latencies, 0.95),
                    p99_latency_ms=self._calculate_percentile(latencies, 0.99),
                    max_latency_ms=max(latencies),
                    total_messages=self._counters['total_messages'],
                    successful_messages=self._counters['successful_messages'],
                    failed_messages=self._counters['total_errors'],
                    error_rate=self._calculate_error_rate(),
                    consecutive_errors=self._counters['consecutive_errors']
                )
            
            # Calculate throughput
            self._calculate_throughput_metrics()
    
    def _calculate_percentile(self, data: List[float], percentile: float) -> float:
        """Calculate percentile of data."""
        if not data:
            return 0.0
        
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile)
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    def _calculate_error_rate(self) -> float:
        """Calculate current error rate."""
        total = self._counters['total_messages']
        if total == 0:
            return 0.0
        
        errors = self._counters['total_errors']
        return errors / total
    
    def _calculate_throughput_metrics(self):
        """Calculate messages per second throughput."""
        current_time = time.time()
        
        # Remove old entries from throughput window
        while (self._throughput_window and 
               current_time - self._throughput_window[0] > 60):
            self._throughput_window.popleft()
        
        # Calculate messages per second
        if len(self._throughput_window) > 0:
            time_span = current_time - self._throughput_window[0]
            if time_span > 0:
                self._performance_metrics.messages_per_second = len(self._throughput_window) / time_span
    
    def _assess_health_status(self):
        """Assess overall system health status."""
        issues = []
        status = HealthStatus.HEALTHY
        
        if hasattr(self, '_performance_metrics'):
            metrics = self._performance_metrics
            
            # Check latency thresholds
            if metrics.avg_latency_ms > self._latency_critical_threshold:
                issues.append(f"Critical latency: {metrics.avg_latency_ms:.1f}ms avg")
                status = HealthStatus.CRITICAL
            elif metrics.avg_latency_ms > self._latency_warning_threshold:
                issues.append(f"High latency: {metrics.avg_latency_ms:.1f}ms avg")
                status = max(status, HealthStatus.WARNING)
            
            # Check error rates
            if metrics.error_rate > self._error_rate_critical_threshold:
                issues.append(f"Critical error rate: {metrics.error_rate:.1%}")
                status = HealthStatus.CRITICAL
            elif metrics.error_rate > self._error_rate_warning_threshold:
                issues.append(f"High error rate: {metrics.error_rate:.1%}")
                status = max(status, HealthStatus.WARNING)
            
            # Check consecutive errors
            if metrics.consecutive_errors > 10:
                issues.append(f"Consecutive errors: {metrics.consecutive_errors}")
                status = max(status, HealthStatus.DEGRADED)
            elif metrics.consecutive_errors > 5:
                issues.append(f"Recent errors: {metrics.consecutive_errors}")
                status = max(status, HealthStatus.WARNING)
        
        # Update health status
        self._health_status = status
        self._health_issues = issues
        
        # Log health changes
        if status != HealthStatus.HEALTHY and issues:
            logger.warning("REDIS-PERFORMANCE-MONITOR: Health status %s - %s", 
                          status.value, '; '.join(issues))
    
    def _log_performance_summary(self):
        """Log performance summary for debugging."""
        if hasattr(self, '_performance_metrics'):
            metrics = self._performance_metrics
            logger.debug(
                "REDIS-PERFORMANCE-MONITOR: Avg latency: %.1fms, Throughput: %.1f msg/s, "
                "Error rate: %.1%%, Status: %s",
                metrics.avg_latency_ms, metrics.messages_per_second,
                metrics.error_rate * 100, self._health_status.value
            )
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report."""
        with self._stats_lock:
            # Base metrics
            report = {
                'health_status': self._health_status.value,
                'health_issues': self._health_issues,
                'timestamp': time.time()
            }
            
            # Add performance metrics if available
            if hasattr(self, '_performance_metrics'):
                report['performance'] = asdict(self._performance_metrics)
            
            # Add channel metrics
            report['channels'] = {}
            for channel, metrics in self._channel_metrics.items():
                report['channels'][channel] = asdict(metrics)
            
            # Add filter performance
            filter_performance = {}
            for key, times in self._timers.items():
                if 'filter_' in key and times:
                    filter_type = key.replace('_times', '')
                    filter_performance[filter_type] = {
                        'avg_time_ms': statistics.mean(times),
                        'max_time_ms': max(times),
                        'sample_count': len(times)
                    }
            
            if filter_performance:
                report['filter_performance'] = filter_performance
            
            # Add WebSocket broadcast performance
            broadcast_performance = {}
            for key, times in self._timers.items():
                if 'websocket_' in key and times:
                    event_type = key.replace('websocket_', '').replace('_times', '')
                    broadcast_performance[event_type] = {
                        'avg_broadcast_time_ms': statistics.mean(times),
                        'max_broadcast_time_ms': max(times),
                        'total_broadcasts': self._counters.get(f'websocket_{event_type}_broadcasts', 0),
                        'total_users_reached': self._counters.get(f'websocket_{event_type}_users', 0)
                    }
            
            if broadcast_performance:
                report['websocket_performance'] = broadcast_performance
            
            # Add system counters
            report['counters'] = dict(self._counters)
            
            return report
    
    def get_health_status(self) -> Tuple[HealthStatus, List[str]]:
        """Get current health status and issues."""
        return self._health_status, self._health_issues.copy()
    
    def get_realtime_metrics(self) -> Dict[str, Any]:
        """Get real-time metrics for dashboard display."""
        with self._stats_lock:
            metrics = {}
            
            if hasattr(self, '_performance_metrics'):
                perf = self._performance_metrics
                metrics.update({
                    'avg_latency_ms': round(perf.avg_latency_ms, 1),
                    'messages_per_second': round(perf.messages_per_second, 1),
                    'error_rate_percent': round(perf.error_rate * 100, 2),
                    'total_messages': perf.total_messages,
                    'health_status': self._health_status.value
                })
            
            # Recent channel activity
            active_channels = []
            for channel, ch_metrics in self._channel_metrics.items():
                if ch_metrics.last_message_time and time.time() - ch_metrics.last_message_time < 60:
                    active_channels.append({
                        'channel': channel,
                        'message_count': ch_metrics.message_count,
                        'avg_processing_ms': round(ch_metrics.avg_processing_time_ms, 1)
                    })
            
            metrics['active_channels'] = active_channels
            
            return metrics
    
    def reset_metrics(self):
        """Reset all performance metrics."""
        with self._stats_lock:
            self._latency_samples.clear()
            self._throughput_window.clear()
            self._channel_metrics.clear()
            self._counters.clear()
            self._timers.clear()
            self._health_issues.clear()
            self._health_status = HealthStatus.HEALTHY
            
            logger.info("REDIS-PERFORMANCE-MONITOR: Metrics reset")
    
    def create_performance_alert(self, threshold_type: str, current_value: float, 
                               threshold_value: float) -> Dict[str, Any]:
        """Create performance alert for external notification."""
        return {
            'alert_type': 'performance_threshold',
            'threshold_type': threshold_type,
            'current_value': current_value,
            'threshold_value': threshold_value,
            'severity': self._health_status.value,
            'timestamp': time.time(),
            'health_issues': self._health_issues,
            'suggested_actions': self._get_suggested_actions(threshold_type)
        }
    
    def _get_suggested_actions(self, threshold_type: str) -> List[str]:
        """Get suggested actions for performance issues."""
        actions = []
        
        if threshold_type == 'latency':
            actions.extend([
                "Check Redis connection pool settings",
                "Verify network latency to Redis server",
                "Review message filtering efficiency",
                "Consider scaling Redis infrastructure"
            ])
        elif threshold_type == 'error_rate':
            actions.extend([
                "Check Redis server logs",
                "Verify connection pool health",
                "Review error handling in message processing",
                "Check for resource constraints"
            ])
        elif threshold_type == 'throughput':
            actions.extend([
                "Review message processing logic",
                "Check for message backlog",
                "Consider increasing worker threads",
                "Verify Redis server performance"
            ])
        
        return actions

# Global performance monitor instance
_global_performance_monitor: Optional[RedisPerformanceMonitor] = None

def get_performance_monitor() -> Optional[RedisPerformanceMonitor]:
    """Get global performance monitor instance."""
    return _global_performance_monitor

def initialize_performance_monitor(config: Dict[str, Any]) -> RedisPerformanceMonitor:
    """Initialize global performance monitor."""
    global _global_performance_monitor
    
    if _global_performance_monitor is None:
        _global_performance_monitor = RedisPerformanceMonitor(config)
        _global_performance_monitor.start_monitoring()
        logger.info("Global Redis performance monitor initialized")
    
    return _global_performance_monitor