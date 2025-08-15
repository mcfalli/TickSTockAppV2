"""
Performance Monitor - Sprint 6C Implementation
Provides unified performance tracking and alerting across all components.
Extracted from distributed performance tracking in various components
"""

import logging
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum

from config.logging_config import get_domain_logger, LogDomain

logger = get_domain_logger(LogDomain.CORE, 'performance_monitor')

class PerformanceLevel(Enum):
    """Performance level classifications."""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    CRITICAL = "critical"

@dataclass
class PerformanceMetric:
    """Individual performance metric."""
    component: str
    metric_name: str
    value: float
    unit: str  # 'ms', 'ops/sec', 'percent', etc.
    timestamp: float
    threshold_good: Optional[float] = None
    threshold_acceptable: Optional[float] = None
    
    def get_level(self) -> PerformanceLevel:
        """Determine performance level based on thresholds."""
        if self.threshold_good is None:
            return PerformanceLevel.ACCEPTABLE
        
        # For metrics where lower is better (like latency)
        if self.unit in ['ms', 'seconds']:
            if self.value <= self.threshold_good:
                return PerformanceLevel.EXCELLENT
            elif self.value <= self.threshold_acceptable:
                return PerformanceLevel.GOOD
            elif self.value <= self.threshold_acceptable * 2:
                return PerformanceLevel.ACCEPTABLE
            elif self.value <= self.threshold_acceptable * 4:
                return PerformanceLevel.POOR
            else:
                return PerformanceLevel.CRITICAL
        
        # For metrics where higher is better (like throughput)
        else:
            if self.value >= self.threshold_good:
                return PerformanceLevel.EXCELLENT
            elif self.value >= self.threshold_acceptable:
                return PerformanceLevel.GOOD
            elif self.value >= self.threshold_acceptable * 0.5:
                return PerformanceLevel.ACCEPTABLE
            elif self.value >= self.threshold_acceptable * 0.25:
                return PerformanceLevel.POOR
            else:
                return PerformanceLevel.CRITICAL

@dataclass
class PerformanceAlert:
    """Performance alert when thresholds are breached."""
    component: str
    metric_name: str
    current_value: float
    threshold_value: float
    level: PerformanceLevel
    message: str
    timestamp: float
    resolved: bool = False

class PerformanceMonitor:
    """
    Unified performance monitoring and alerting system.
    """
    
    def __init__(self, config):
        """Initialize performance monitor with configuration."""
        self.config = self._extract_performance_config(config)
        
        # Performance metrics storage
        self.current_metrics: Dict[str, PerformanceMetric] = {}
        self.metric_history: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=self.config['HISTORY_SIZE'])
        )
        
        # Alert management
        self.active_alerts: List[PerformanceAlert] = []
        self.alert_history: deque = deque(maxlen=1000)
        self.alert_callbacks: Dict[str, Callable] = {}
        
        # Performance thresholds by metric type
        self.thresholds = self._initialize_thresholds()
        
        # Monitoring state
        self.monitoring_active = False
        self.monitor_thread = None
        self.last_check_time = 0
        
        logger.info("✅ PerformanceMonitor initialized")
    
    def _extract_performance_config(self, config: Dict) -> Dict:
        """Extract performance monitor specific configuration."""
        return {
            'CHECK_INTERVAL': config.get('PERFORMANCE_CHECK_INTERVAL', 10),
            'HISTORY_SIZE': config.get('PERFORMANCE_HISTORY_SIZE', 1000),
            'ALERT_COOLDOWN': config.get('PERFORMANCE_ALERT_COOLDOWN', 300),
            'ENABLE_ALERTS': config.get('ENABLE_PERFORMANCE_ALERTS', True),
            'ALERT_LOG_LEVEL': config.get('PERFORMANCE_ALERT_LOG_LEVEL', 'WARNING'),
            'TREND_WINDOW': config.get('PERFORMANCE_TREND_WINDOW', 300)
        }
    
    def _initialize_thresholds(self) -> Dict[str, Dict[str, float]]:
        """Initialize default performance thresholds."""
        return {
            # Latency metrics (milliseconds) - lower is better
            'processing_time_ms': {'good': 10, 'acceptable': 50},
            'publish_time_ms': {'good': 20, 'acceptable': 100},
            'tick_processing_ms': {'good': 5, 'acceptable': 20},
            'event_detection_ms': {'good': 2, 'acceptable': 10},
            
            # Throughput metrics - higher is better
            'events_per_second': {'good': 1000, 'acceptable': 500},
            'ticks_per_second': {'good': 2000, 'acceptable': 1000},
            'publications_per_second': {'good': 10, 'acceptable': 5},
            
            # Queue metrics - lower is better
            'queue_size': {'good': 100, 'acceptable': 500},
            'avg_queue_size': {'good': 50, 'acceptable': 200},
            
            # Success rate metrics (percent) - higher is better
            'success_rate': {'good': 99, 'acceptable': 95},
            'cache_hit_rate': {'good': 80, 'acceptable': 60},
            
            # Resource metrics
            'memory_usage_mb': {'good': 500, 'acceptable': 1000},
            'cpu_usage_percent': {'good': 50, 'acceptable': 80}
        }
    
    def record_performance(self, component: str, metric_name: str, 
                         value: float, unit: str = 'ms'):
        """
        Record a performance metric.
        This is the main method components use to report performance.
        """
        metric_key = f"{component}.{metric_name}"
        
        # Get thresholds if available
        thresholds = self.thresholds.get(metric_name, {})
        
        # Create metric
        metric = PerformanceMetric(
            component=component,
            metric_name=metric_name,
            value=value,
            unit=unit,
            timestamp=time.time(),
            threshold_good=thresholds.get('good'),
            threshold_acceptable=thresholds.get('acceptable')
        )
        
        # Store current and historical
        self.current_metrics[metric_key] = metric
        self.metric_history[metric_key].append(metric)
        
        # Check for alerts if monitoring active
        if self.monitoring_active and self.config['ENABLE_ALERTS']:
            self._check_metric_alerts(metric)
    
    '''
    def record_operation_time(self, component: str, operation: str, 
                            start_time: float, success: bool = True):
        """Convenience method to record operation timing."""
        elapsed_ms = (time.time() - start_time) * 1000
        metric_name = f"{operation}_time_ms"
        
        self.record_performance(component, metric_name, elapsed_ms, 'ms')
        
        # Log slow operations
        if elapsed_ms > 100:
            logger.warning(f"⚠️ Slow {operation} in {component}: {elapsed_ms:.1f}ms")
    '''

    def start_monitoring(self) -> bool:
        """Start the performance monitoring thread."""
        try:
            if self.monitoring_active:
                return False
            
            self.monitoring_active = True
            self.monitor_thread = threading.Thread(
                target=self._monitoring_loop,
                daemon=True,
                name="performance-monitor"
            )
            self.monitor_thread.start()
            
            logger.info("📊 Performance monitoring started")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error starting performance monitor: {e}")
            self.monitoring_active = False
            return False
    
    def stop_monitoring(self):
        """Stop the performance monitoring thread."""
        self.monitoring_active = False
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2)
    
    def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.monitoring_active:
            try:
                current_time = time.time()
                
                # Periodic checks
                if current_time - self.last_check_time >= self.config['CHECK_INTERVAL']:
                    self._perform_periodic_checks()
                    self.last_check_time = current_time
                
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"❌ Error in performance monitoring loop: {e}")
                time.sleep(5)
    
    def _perform_periodic_checks(self):
        """Perform periodic performance checks."""
        # Calculate aggregate metrics
        self._calculate_aggregate_metrics()
        
        # Check for performance trends
        self._analyze_performance_trends()
        
        # Clean up old alerts
        self._cleanup_old_alerts()
    
    def _check_metric_alerts(self, metric: PerformanceMetric):
        """Check if a metric should generate an alert."""
        level = metric.get_level()
        
        # Only alert on poor or critical performance
        if level not in [PerformanceLevel.POOR, PerformanceLevel.CRITICAL]:
            return
        
        # Check if similar alert already active
        metric_key = f"{metric.component}.{metric.metric_name}"
        active_alert = next(
            (a for a in self.active_alerts 
             if a.component == metric.component and a.metric_name == metric.metric_name),
            None
        )
        
        # Apply cooldown to prevent alert spam
        if active_alert and (metric.timestamp - active_alert.timestamp) < self.config['ALERT_COOLDOWN']:
            return
        
        # Create alert
        threshold = metric.threshold_acceptable or 0
        alert = PerformanceAlert(
            component=metric.component,
            metric_name=metric.metric_name,
            current_value=metric.value,
            threshold_value=threshold,
            level=level,
            message=f"🚨 {metric.component}.{metric.metric_name} = {metric.value:.2f}{metric.unit} (threshold: {threshold})",
            timestamp=metric.timestamp
        )
        
        # Add to active alerts
        if active_alert:
            self.active_alerts.remove(active_alert)
        self.active_alerts.append(alert)
        self.alert_history.append(alert)
        
        # Log alert
        if level == PerformanceLevel.CRITICAL:
            logger.critical(alert.message)
        else:
            logger.warning(alert.message)
        
        # Execute callbacks
        self._execute_alert_callbacks(alert)
    
    def _execute_alert_callbacks(self, alert: PerformanceAlert):
        """Execute registered alert callbacks."""
        for name, callback in self.alert_callbacks.items():
            try:
                callback(alert)
            except Exception as e:
                pass  # Silent fail
    '''
    def register_alert_callback(self, name: str, callback: Callable[[PerformanceAlert], None]):
        """Register a callback for performance alerts."""
        self.alert_callbacks[name] = callback
    '''
    
    def _calculate_aggregate_metrics(self):
        """Calculate aggregate performance metrics."""
        # Calculate success rates
        for component in set(m.component for m in self.current_metrics.values()):
            success_count = 0
            failure_count = 0
            
            for key, metric in self.current_metrics.items():
                if metric.component != component:
                    continue
                    
                if metric.metric_name.endswith('_success'):
                    success_count += metric.value
                elif metric.metric_name.endswith('_failure'):
                    failure_count += metric.value
            
            if success_count + failure_count > 0:
                success_rate = (success_count / (success_count + failure_count)) * 100
                self.record_performance(component, 'success_rate', success_rate, 'percent')
    
    def _analyze_performance_trends(self):
        """Analyze performance trends over time window."""
        current_time = time.time()
        trend_window = self.config['TREND_WINDOW']
        
        for metric_key, history in self.metric_history.items():
            if len(history) < 5:  # Need enough data points
                continue
            
            # Get metrics within trend window
            recent_metrics = [m for m in history if current_time - m.timestamp <= trend_window]
            if len(recent_metrics) < 5:
                continue
            
            # Calculate trend
            values = [m.value for m in recent_metrics]
            first_half_avg = sum(values[:len(values)//2]) / (len(values)//2)
            second_half_avg = sum(values[len(values)//2:]) / (len(values) - len(values)//2)
            
            # Detect significant degradation
            if recent_metrics[-1].unit in ['ms', 'seconds']:  # Lower is better
                if second_half_avg > first_half_avg * 1.5:  # 50% worse
                    logger.warning(f"⚠️ Performance degradation: {metric_key} trending worse")
            else:  # Higher is better
                if second_half_avg < first_half_avg * 0.5:  # 50% worse
                    logger.warning(f"⚠️ Performance degradation: {metric_key} trending worse")
    
    def _cleanup_old_alerts(self):
        """Clean up resolved alerts."""
        resolved_count = 0
        
        # Check if alerts can be resolved
        for alert in self.active_alerts[:]:
            metric_key = f"{alert.component}.{alert.metric_name}"
            current_metric = self.current_metrics.get(metric_key)
            
            if current_metric:
                level = current_metric.get_level()
                if level in [PerformanceLevel.EXCELLENT, PerformanceLevel.GOOD]:
                    alert.resolved = True
                    self.active_alerts.remove(alert)
                    resolved_count += 1
        
        if resolved_count > 0:
            logger.info(f"✅ {resolved_count} performance alerts resolved")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        summary = {
            'overall_status': self._calculate_overall_status(),
            'component_performance': self._get_component_performance(),
            'active_alerts': len(self.active_alerts),
            'monitoring_active': self.monitoring_active,
            'timestamp': time.time()
        }
        
        # Log critical alerts
        critical_alerts = [a for a in self.active_alerts if a.level == PerformanceLevel.CRITICAL]
        if critical_alerts:
            logger.critical(f"🚨 {len(critical_alerts)} CRITICAL performance issues active")
        
        return summary
    
    def _calculate_overall_status(self) -> str:
        """Calculate overall system performance status."""
        if not self.current_metrics:
            return "unknown"
        
        # Count metrics by performance level
        level_counts = defaultdict(int)
        for metric in self.current_metrics.values():
            level = metric.get_level()
            level_counts[level] += 1
        
        # Determine overall status
        if level_counts[PerformanceLevel.CRITICAL] > 0:
            return "critical"
        elif level_counts[PerformanceLevel.POOR] > 2:
            return "poor"
        elif level_counts[PerformanceLevel.POOR] > 0:
            return "degraded"
        elif level_counts[PerformanceLevel.ACCEPTABLE] > len(self.current_metrics) * 0.5:
            return "acceptable"
        elif level_counts[PerformanceLevel.GOOD] > len(self.current_metrics) * 0.7:
            return "good"
        else:
            return "excellent"
    
    def _get_component_performance(self) -> Dict[str, Dict[str, Any]]:
        """Get performance breakdown by component."""
        component_perf = defaultdict(lambda: {
            'metrics': {},
            'overall_level': PerformanceLevel.ACCEPTABLE,
            'alert_count': 0
        })
        
        # Aggregate metrics by component
        for metric_key, metric in self.current_metrics.items():
            comp_data = component_perf[metric.component]
            comp_data['metrics'][metric.metric_name] = {
                'value': metric.value,
                'unit': metric.unit,
                'level': metric.get_level().value
            }
        
        # Calculate overall level per component
        for component, data in component_perf.items():
            levels = [PerformanceLevel[m['level'].upper()] 
                     for m in data['metrics'].values()]
            
            if PerformanceLevel.CRITICAL in levels:
                data['overall_level'] = 'critical'
            elif PerformanceLevel.POOR in levels:
                data['overall_level'] = 'poor'
            elif PerformanceLevel.ACCEPTABLE in levels:
                data['overall_level'] = 'acceptable'
            elif PerformanceLevel.GOOD in levels:
                data['overall_level'] = 'good'
            else:
                data['overall_level'] = 'excellent'
            
            # Count active alerts
            data['alert_count'] = sum(1 for a in self.active_alerts 
                                    if a.component == component)
        
        return dict(component_perf)