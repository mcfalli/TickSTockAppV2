"""
Sprint 108: Channel-Specific Monitoring and Alerting System

This module provides comprehensive monitoring and alerting capabilities 
specifically designed for the multi-channel architecture. It integrates 
with existing TickStock monitoring while adding channel-specific metrics,
performance tracking, and alerting.

Features:
1. Channel-specific metrics collection and aggregation
2. Performance monitoring with target thresholds
3. Alerting for channel failures and performance degradation
4. Integration with existing monitoring dashboard
5. Health checks for all channel components
6. Debugging tools for multi-channel troubleshooting
"""

import logging
import time
import asyncio
from typing import Dict, List, Any, Optional, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import psutil
import statistics

from config.logging_config import get_domain_logger, LogDomain

# Import channel types for monitoring
try:
    from src.processing.channels.base_channel import ChannelStatus, ChannelType
    from src.processing.channels.channel_metrics import ChannelMetrics
except ImportError:
    # Fallback if imports not available
    ChannelStatus = None
    ChannelType = None
    ChannelMetrics = None

logger = get_domain_logger(LogDomain.CORE, 'channel_monitoring')


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertType(Enum):
    """Types of alerts"""
    CHANNEL_FAILURE = "channel_failure"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    HIGH_LATENCY = "high_latency"
    LOW_SUCCESS_RATE = "low_success_rate"
    MEMORY_USAGE = "memory_usage"
    QUEUE_OVERFLOW = "queue_overflow"
    ROUTING_ERRORS = "routing_errors"
    SYSTEM_HEALTH = "system_health"


@dataclass
class Alert:
    """Represents a monitoring alert"""
    alert_type: AlertType
    severity: AlertSeverity
    message: str
    details: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    channel_name: Optional[str] = None
    resolved: bool = False
    resolution_time: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.alert_type.value,
            'severity': self.severity.value,
            'message': self.message,
            'details': self.details,
            'timestamp': self.timestamp,
            'datetime': datetime.fromtimestamp(self.timestamp).isoformat(),
            'channel_name': self.channel_name,
            'resolved': self.resolved,
            'resolution_time': self.resolution_time,
            'duration_seconds': (
                (self.resolution_time - self.timestamp) 
                if self.resolved and self.resolution_time 
                else (time.time() - self.timestamp)
            )
        }


@dataclass
class PerformanceThresholds:
    """Performance thresholds for alerting"""
    max_latency_ms: float = 50.0
    min_success_rate_percent: float = 95.0
    max_memory_usage_gb: float = 2.0
    max_queue_utilization_percent: float = 80.0
    max_error_rate_percent: float = 5.0
    max_processing_time_ms: float = 100.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'max_latency_ms': self.max_latency_ms,
            'min_success_rate_percent': self.min_success_rate_percent,
            'max_memory_usage_gb': self.max_memory_usage_gb,
            'max_queue_utilization_percent': self.max_queue_utilization_percent,
            'max_error_rate_percent': self.max_error_rate_percent,
            'max_processing_time_ms': self.max_processing_time_ms
        }


@dataclass
class ChannelHealthMetrics:
    """Health metrics for a specific channel"""
    channel_name: str
    channel_type: str
    status: str
    is_healthy: bool
    
    # Processing metrics
    processed_count: int = 0
    error_count: int = 0
    success_rate_percent: float = 100.0
    avg_processing_time_ms: float = 0.0
    
    # Queue metrics
    queue_size: int = 0
    max_queue_size: int = 0
    queue_utilization_percent: float = 0.0
    
    # Performance metrics
    throughput_per_second: float = 0.0
    latency_p50_ms: float = 0.0
    latency_p95_ms: float = 0.0
    latency_p99_ms: float = 0.0
    
    # Timing
    last_update: float = field(default_factory=time.time)
    last_processed_time: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'channel_name': self.channel_name,
            'channel_type': self.channel_type,
            'status': self.status,
            'is_healthy': self.is_healthy,
            'processing': {
                'processed_count': self.processed_count,
                'error_count': self.error_count,
                'success_rate_percent': self.success_rate_percent,
                'avg_processing_time_ms': self.avg_processing_time_ms
            },
            'queue': {
                'current_size': self.queue_size,
                'max_size': self.max_queue_size,
                'utilization_percent': self.queue_utilization_percent
            },
            'performance': {
                'throughput_per_second': self.throughput_per_second,
                'latency_p50_ms': self.latency_p50_ms,
                'latency_p95_ms': self.latency_p95_ms,
                'latency_p99_ms': self.latency_p99_ms
            },
            'timing': {
                'last_update': self.last_update,
                'last_processed_time': self.last_processed_time,
                'time_since_last_activity': (
                    time.time() - self.last_processed_time 
                    if self.last_processed_time 
                    else None
                )
            }
        }


@dataclass
class SystemHealthMetrics:
    """Overall system health metrics"""
    total_channels: int = 0
    healthy_channels: int = 0
    unhealthy_channels: int = 0
    
    # Overall performance
    total_processed: int = 0
    total_errors: int = 0
    overall_success_rate: float = 100.0
    avg_system_latency_ms: float = 0.0
    
    # Resource usage
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    
    # Router metrics
    routing_success_rate: float = 100.0
    routing_errors: int = 0
    
    # Active alerts
    active_alerts: int = 0
    critical_alerts: int = 0
    
    last_update: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'channels': {
                'total': self.total_channels,
                'healthy': self.healthy_channels,
                'unhealthy': self.unhealthy_channels,
                'health_percent': (
                    (self.healthy_channels / self.total_channels * 100.0) 
                    if self.total_channels > 0 else 0.0
                )
            },
            'performance': {
                'total_processed': self.total_processed,
                'total_errors': self.total_errors,
                'success_rate_percent': self.overall_success_rate,
                'avg_latency_ms': self.avg_system_latency_ms
            },
            'resources': {
                'memory_usage_mb': self.memory_usage_mb,
                'cpu_usage_percent': self.cpu_usage_percent
            },
            'routing': {
                'success_rate_percent': self.routing_success_rate,
                'errors': self.routing_errors
            },
            'alerts': {
                'active': self.active_alerts,
                'critical': self.critical_alerts
            },
            'last_update': self.last_update
        }


class ChannelMonitor:
    """
    Comprehensive monitoring system for multi-channel architecture.
    
    Provides real-time monitoring, alerting, and health checking for all
    channel components with integration to existing TickStock monitoring.
    """
    
    def __init__(self, thresholds: Optional[PerformanceThresholds] = None):
        """
        Initialize the channel monitoring system.
        
        Args:
            thresholds: Performance thresholds for alerting
        """
        self.thresholds = thresholds or PerformanceThresholds()
        
        # Monitoring state
        self.channel_metrics: Dict[str, ChannelHealthMetrics] = {}
        self.system_metrics = SystemHealthMetrics()
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        
        # Alert handlers
        self.alert_handlers: List[Callable[[Alert], None]] = []
        
        # Monitoring configuration
        self.monitoring_enabled = True
        self.alert_cooldown_seconds = 300  # 5 minutes between same alerts
        self.metrics_retention_hours = 24
        self.health_check_interval = 10.0
        
        # Background tasks
        self._monitoring_task = None
        self._running = False
        
        # Performance tracking
        self._latency_samples: Dict[str, List[float]] = {}
        self._throughput_trackers: Dict[str, Dict[str, Any]] = {}
        
        logger.info("ChannelMonitor initialized with performance thresholds")
        logger.info(f"Thresholds: {self.thresholds.to_dict()}")
    
    async def start_monitoring(self):
        """Start the monitoring system"""
        if self._running:
            return
        
        self._running = True
        self.monitoring_enabled = True
        
        # Start background monitoring task
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        logger.info("✅ Channel monitoring started")
    
    async def stop_monitoring(self):
        """Stop the monitoring system"""
        self._running = False
        self.monitoring_enabled = False
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("🛑 Channel monitoring stopped")
    
    def register_channel(self, channel_name: str, channel_type: str, channel_ref: Any = None):
        """
        Register a channel for monitoring.
        
        Args:
            channel_name: Unique channel name
            channel_type: Type of channel (tick, ohlcv, fmv)
            channel_ref: Optional reference to channel object
        """
        if channel_name not in self.channel_metrics:
            self.channel_metrics[channel_name] = ChannelHealthMetrics(
                channel_name=channel_name,
                channel_type=channel_type,
                status="unknown",
                is_healthy=False
            )
            
            # Initialize performance tracking
            self._latency_samples[channel_name] = []
            self._throughput_trackers[channel_name] = {
                'start_time': time.time(),
                'count': 0,
                'last_throughput': 0.0
            }
            
            logger.info(f"📊 Registered channel for monitoring: {channel_name} ({channel_type})")
    
    def unregister_channel(self, channel_name: str):
        """Unregister a channel from monitoring"""
        if channel_name in self.channel_metrics:
            del self.channel_metrics[channel_name]
            
            # Clean up tracking data
            if channel_name in self._latency_samples:
                del self._latency_samples[channel_name]
            if channel_name in self._throughput_trackers:
                del self._throughput_trackers[channel_name]
            
            logger.info(f"📊 Unregistered channel from monitoring: {channel_name}")
    
    def update_channel_metrics(self, channel_name: str, **metrics):
        """
        Update metrics for a specific channel.
        
        Args:
            channel_name: Channel to update
            **metrics: Metric values to update
        """
        if channel_name not in self.channel_metrics:
            logger.warning(f"Channel {channel_name} not registered for monitoring")
            return
        
        channel_metrics = self.channel_metrics[channel_name]
        
        # Update provided metrics
        for key, value in metrics.items():
            if hasattr(channel_metrics, key):
                setattr(channel_metrics, key, value)
        
        # Update timestamp
        channel_metrics.last_update = time.time()
        
        # Check for alerts
        self._check_channel_alerts(channel_name, channel_metrics)
    
    def record_processing_latency(self, channel_name: str, latency_ms: float):
        """Record processing latency for a channel"""
        if channel_name not in self._latency_samples:
            return
        
        # Add sample
        self._latency_samples[channel_name].append(latency_ms)
        
        # Keep only last 1000 samples
        if len(self._latency_samples[channel_name]) > 1000:
            self._latency_samples[channel_name] = self._latency_samples[channel_name][-1000:]
        
        # Update latency percentiles
        if channel_name in self.channel_metrics:
            samples = self._latency_samples[channel_name]
            if len(samples) >= 10:  # Need minimum samples for reliable percentiles
                self.channel_metrics[channel_name].latency_p50_ms = statistics.median(samples)
                self.channel_metrics[channel_name].latency_p95_ms = statistics.quantiles(samples, n=20)[18]  # 95th percentile
                self.channel_metrics[channel_name].latency_p99_ms = statistics.quantiles(samples, n=100)[98]  # 99th percentile
    
    def record_processing_event(self, channel_name: str, success: bool, processing_time_ms: float = 0):
        """Record a processing event for throughput and success rate tracking"""
        if channel_name not in self.channel_metrics:
            return
        
        channel_metrics = self.channel_metrics[channel_name]
        
        # Update processing counts
        channel_metrics.processed_count += 1
        if not success:
            channel_metrics.error_count += 1
        
        # Update success rate
        if channel_metrics.processed_count > 0:
            channel_metrics.success_rate_percent = (
                (channel_metrics.processed_count - channel_metrics.error_count) / 
                channel_metrics.processed_count * 100.0
            )
        
        # Update processing time
        if processing_time_ms > 0:
            # Simple exponential moving average
            if channel_metrics.avg_processing_time_ms == 0:
                channel_metrics.avg_processing_time_ms = processing_time_ms
            else:
                alpha = 0.1
                channel_metrics.avg_processing_time_ms = (
                    alpha * processing_time_ms + 
                    (1 - alpha) * channel_metrics.avg_processing_time_ms
                )
        
        # Update throughput
        self._update_throughput(channel_name)
        
        # Record activity time
        channel_metrics.last_processed_time = time.time()
    
    def _update_throughput(self, channel_name: str):
        """Update throughput calculation for a channel"""
        if channel_name not in self._throughput_trackers:
            return
        
        tracker = self._throughput_trackers[channel_name]
        current_time = time.time()
        
        tracker['count'] += 1
        
        # Calculate throughput every second
        time_elapsed = current_time - tracker['start_time']
        if time_elapsed >= 1.0:
            throughput = tracker['count'] / time_elapsed
            
            # Update channel metrics
            if channel_name in self.channel_metrics:
                self.channel_metrics[channel_name].throughput_per_second = throughput
            
            # Reset tracker
            tracker['start_time'] = current_time
            tracker['count'] = 0
            tracker['last_throughput'] = throughput
    
    def _check_channel_alerts(self, channel_name: str, metrics: ChannelHealthMetrics):
        """Check if channel metrics exceed thresholds and generate alerts"""
        if not self.monitoring_enabled:
            return
        
        # Check latency
        if metrics.latency_p99_ms > self.thresholds.max_latency_ms:
            self._create_alert(
                AlertType.HIGH_LATENCY,
                AlertSeverity.WARNING,
                f"High latency detected in {channel_name}",
                {
                    'channel': channel_name,
                    'current_latency_p99': metrics.latency_p99_ms,
                    'threshold': self.thresholds.max_latency_ms
                },
                channel_name
            )
        
        # Check success rate
        if metrics.success_rate_percent < self.thresholds.min_success_rate_percent:
            severity = AlertSeverity.ERROR if metrics.success_rate_percent < 90.0 else AlertSeverity.WARNING
            self._create_alert(
                AlertType.LOW_SUCCESS_RATE,
                severity,
                f"Low success rate in {channel_name}",
                {
                    'channel': channel_name,
                    'current_success_rate': metrics.success_rate_percent,
                    'threshold': self.thresholds.min_success_rate_percent,
                    'error_count': metrics.error_count,
                    'processed_count': metrics.processed_count
                },
                channel_name
            )
        
        # Check queue utilization
        if metrics.queue_utilization_percent > self.thresholds.max_queue_utilization_percent:
            severity = AlertSeverity.ERROR if metrics.queue_utilization_percent > 95.0 else AlertSeverity.WARNING
            self._create_alert(
                AlertType.QUEUE_OVERFLOW,
                severity,
                f"High queue utilization in {channel_name}",
                {
                    'channel': channel_name,
                    'current_utilization': metrics.queue_utilization_percent,
                    'threshold': self.thresholds.max_queue_utilization_percent,
                    'queue_size': metrics.queue_size,
                    'max_queue_size': metrics.max_queue_size
                },
                channel_name
            )
        
        # Check if channel is unhealthy
        if not metrics.is_healthy:
            self._create_alert(
                AlertType.CHANNEL_FAILURE,
                AlertSeverity.CRITICAL,
                f"Channel {channel_name} is unhealthy",
                {
                    'channel': channel_name,
                    'status': metrics.status,
                    'last_processed_time': metrics.last_processed_time
                },
                channel_name
            )
    
    def _create_alert(self, alert_type: AlertType, severity: AlertSeverity, message: str, 
                     details: Dict[str, Any], channel_name: Optional[str] = None):
        """Create and handle a new alert"""
        
        # Check cooldown to prevent alert spam
        alert_key = f"{alert_type.value}_{channel_name or 'system'}"
        current_time = time.time()
        
        # Skip if same alert was recently created
        if alert_key in self.active_alerts:
            last_alert_time = self.active_alerts[alert_key].timestamp
            if current_time - last_alert_time < self.alert_cooldown_seconds:
                return
        
        # Create alert
        alert = Alert(
            alert_type=alert_type,
            severity=severity,
            message=message,
            details=details,
            channel_name=channel_name,
            timestamp=current_time
        )
        
        # Store alert
        self.active_alerts[alert_key] = alert
        self.alert_history.append(alert)
        
        # Trigger alert handlers
        for handler in self.alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Error in alert handler: {e}")
        
        # Log alert
        log_level = {
            AlertSeverity.INFO: logger.info,
            AlertSeverity.WARNING: logger.warning,
            AlertSeverity.ERROR: logger.error,
            AlertSeverity.CRITICAL: logger.critical
        }.get(severity, logger.info)
        
        log_level(f"🚨 ALERT [{severity.value.upper()}]: {message} | Details: {details}")
    
    def resolve_alert(self, alert_type: AlertType, channel_name: Optional[str] = None):
        """Resolve an active alert"""
        alert_key = f"{alert_type.value}_{channel_name or 'system'}"
        
        if alert_key in self.active_alerts:
            alert = self.active_alerts[alert_key]
            alert.resolved = True
            alert.resolution_time = time.time()
            
            del self.active_alerts[alert_key]
            
            logger.info(f"✅ Alert resolved: {alert.message}")
    
    def add_alert_handler(self, handler: Callable[[Alert], None]):
        """Add a custom alert handler"""
        self.alert_handlers.append(handler)
        logger.info("Alert handler registered")
    
    async def _monitoring_loop(self):
        """Background monitoring loop"""
        try:
            while self._running:
                await asyncio.sleep(self.health_check_interval)
                
                if not self._running:
                    break
                
                # Update system metrics
                self._update_system_metrics()
                
                # Check system-level alerts
                self._check_system_alerts()
                
                # Clean up old alerts
                self._cleanup_alert_history()
                
                # Log monitoring status periodically
                if len(self.channel_metrics) > 0:
                    healthy_channels = sum(1 for m in self.channel_metrics.values() if m.is_healthy)
                    total_channels = len(self.channel_metrics)
                    active_alerts = len(self.active_alerts)
                    
                    logger.debug(f"📊 Monitoring Status: {healthy_channels}/{total_channels} channels healthy, "
                               f"{active_alerts} active alerts")
                
        except asyncio.CancelledError:
            logger.info("Monitoring loop cancelled")
        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}", exc_info=True)
    
    def _update_system_metrics(self):
        """Update overall system metrics"""
        # Channel health summary
        self.system_metrics.total_channels = len(self.channel_metrics)
        self.system_metrics.healthy_channels = sum(
            1 for m in self.channel_metrics.values() if m.is_healthy
        )
        self.system_metrics.unhealthy_channels = (
            self.system_metrics.total_channels - self.system_metrics.healthy_channels
        )
        
        # Overall performance
        total_processed = sum(m.processed_count for m in self.channel_metrics.values())
        total_errors = sum(m.error_count for m in self.channel_metrics.values())
        
        self.system_metrics.total_processed = total_processed
        self.system_metrics.total_errors = total_errors
        
        if total_processed > 0:
            self.system_metrics.overall_success_rate = (
                (total_processed - total_errors) / total_processed * 100.0
            )
        
        # Average latency across channels
        latencies = [m.latency_p99_ms for m in self.channel_metrics.values() if m.latency_p99_ms > 0]
        if latencies:
            self.system_metrics.avg_system_latency_ms = statistics.mean(latencies)
        
        # Resource usage
        try:
            process = psutil.Process()
            self.system_metrics.memory_usage_mb = process.memory_info().rss / 1024 / 1024
            self.system_metrics.cpu_usage_percent = process.cpu_percent()
        except Exception as e:
            logger.debug(f"Could not get system resource usage: {e}")
        
        # Alert counts
        self.system_metrics.active_alerts = len(self.active_alerts)
        self.system_metrics.critical_alerts = sum(
            1 for alert in self.active_alerts.values() 
            if alert.severity == AlertSeverity.CRITICAL
        )
        
        self.system_metrics.last_update = time.time()
    
    def _check_system_alerts(self):
        """Check for system-level alerts"""
        # Memory usage alert
        memory_gb = self.system_metrics.memory_usage_mb / 1024
        if memory_gb > self.thresholds.max_memory_usage_gb:
            self._create_alert(
                AlertType.MEMORY_USAGE,
                AlertSeverity.WARNING,
                f"High memory usage: {memory_gb:.2f}GB",
                {
                    'current_memory_gb': memory_gb,
                    'threshold_gb': self.thresholds.max_memory_usage_gb,
                    'memory_mb': self.system_metrics.memory_usage_mb
                }
            )
        
        # System health alert
        if self.system_metrics.unhealthy_channels > 0:
            severity = (AlertSeverity.CRITICAL 
                       if self.system_metrics.unhealthy_channels > self.system_metrics.healthy_channels
                       else AlertSeverity.ERROR)
            
            self._create_alert(
                AlertType.SYSTEM_HEALTH,
                severity,
                f"System health degraded: {self.system_metrics.unhealthy_channels} unhealthy channels",
                {
                    'healthy_channels': self.system_metrics.healthy_channels,
                    'unhealthy_channels': self.system_metrics.unhealthy_channels,
                    'total_channels': self.system_metrics.total_channels
                }
            )
    
    def _cleanup_alert_history(self):
        """Clean up old alerts from history"""
        cutoff_time = time.time() - (self.metrics_retention_hours * 3600)
        self.alert_history = [
            alert for alert in self.alert_history 
            if alert.timestamp > cutoff_time
        ]
    
    def get_monitoring_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive monitoring data for dashboard display"""
        return {
            'system_overview': self.system_metrics.to_dict(),
            'channel_details': {
                name: metrics.to_dict() 
                for name, metrics in self.channel_metrics.items()
            },
            'active_alerts': [
                alert.to_dict() for alert in self.active_alerts.values()
            ],
            'recent_alerts': [
                alert.to_dict() for alert in self.alert_history[-50:]  # Last 50 alerts
            ],
            'performance_thresholds': self.thresholds.to_dict(),
            'monitoring_config': {
                'enabled': self.monitoring_enabled,
                'health_check_interval': self.health_check_interval,
                'alert_cooldown_seconds': self.alert_cooldown_seconds,
                'total_channels_monitored': len(self.channel_metrics)
            },
            'timestamp': time.time()
        }
    
    def get_channel_debug_info(self, channel_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed debug information for a specific channel"""
        if channel_name not in self.channel_metrics:
            return None
        
        metrics = self.channel_metrics[channel_name]
        latency_samples = self._latency_samples.get(channel_name, [])
        throughput_tracker = self._throughput_trackers.get(channel_name, {})
        
        # Get alerts for this channel
        channel_alerts = [
            alert.to_dict() for alert in self.active_alerts.values()
            if alert.channel_name == channel_name
        ]
        
        return {
            'channel_metrics': metrics.to_dict(),
            'latency_analysis': {
                'sample_count': len(latency_samples),
                'recent_samples': latency_samples[-20:] if latency_samples else [],
                'min_latency': min(latency_samples) if latency_samples else 0,
                'max_latency': max(latency_samples) if latency_samples else 0
            },
            'throughput_analysis': {
                'current_throughput': throughput_tracker.get('last_throughput', 0),
                'tracking_start': throughput_tracker.get('start_time', 0),
                'current_count': throughput_tracker.get('count', 0)
            },
            'active_alerts': channel_alerts,
            'health_summary': {
                'is_healthy': metrics.is_healthy,
                'status': metrics.status,
                'time_since_last_activity': (
                    time.time() - metrics.last_processed_time
                    if metrics.last_processed_time
                    else None
                ),
                'performance_issues': self._get_channel_performance_issues(metrics)
            }
        }
    
    def _get_channel_performance_issues(self, metrics: ChannelHealthMetrics) -> List[str]:
        """Get list of performance issues for a channel"""
        issues = []
        
        if metrics.latency_p99_ms > self.thresholds.max_latency_ms:
            issues.append(f"High latency: {metrics.latency_p99_ms:.1f}ms")
        
        if metrics.success_rate_percent < self.thresholds.min_success_rate_percent:
            issues.append(f"Low success rate: {metrics.success_rate_percent:.1f}%")
        
        if metrics.queue_utilization_percent > self.thresholds.max_queue_utilization_percent:
            issues.append(f"High queue utilization: {metrics.queue_utilization_percent:.1f}%")
        
        if metrics.avg_processing_time_ms > self.thresholds.max_processing_time_ms:
            issues.append(f"Slow processing: {metrics.avg_processing_time_ms:.1f}ms")
        
        if not metrics.is_healthy:
            issues.append(f"Channel unhealthy: {metrics.status}")
        
        return issues