"""
Metrics Collector - Sprint 6C Implementation
Centralizes system metrics gathering and aggregation.
Extracted from health_monitor and various components
"""

import logging
import time
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from collections import defaultdict

from config.logging_config import get_domain_logger, LogDomain

logger = get_domain_logger(LogDomain.CORE, 'metrics_collector')

class DataFlowStats:
    """Track metrics collection flow."""
    def __init__(self):
        self.collections_attempted = 0
        self.metrics_collected = 0
        self.sources_active = 0
        self.last_log_time = time.time()
        self.log_interval = 60  # seconds - less frequent for metrics
        
    def should_log(self):
        return time.time() - self.last_log_time >= self.log_interval
    
    def log_stats(self):
        logger.info(f"📊 METRICS FLOW: Collections:{self.collections_attempted} → "
                   f"Metrics:{self.metrics_collected} from {self.sources_active} sources")
        self.last_log_time = time.time()

@dataclass
class MetricSnapshot:
    """Represents a point-in-time metric snapshot."""
    metric_name: str
    value: Any
    timestamp: float
    source: str
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class MetricsReport:
    """Comprehensive metrics report."""
    snapshots: List[MetricSnapshot]
    aggregated_metrics: Dict[str, Any]
    collection_time_ms: float
    timestamp: float
    errors: List[str] = field(default_factory=list)

class MetricsCollector:
    """
    Centralized metrics collection and aggregation system.
    """
    
    def __init__(self, config):
        """Initialize metrics collector with configuration."""
        self.config = config
        
        # Metrics sources registry
        self.metrics_sources = {}
        
        # Current metrics cache
        self.current_metrics = {}
        self.last_collection_time = 0
        
        # Historical metrics (rolling window)
        self.historical_metrics = defaultdict(list)
        self.max_history_size = self.config.get('MAX_HISTORY_SIZE', 1000)
        
        # Data flow tracking
        self.stats = DataFlowStats()
        
        # CSV writers cache
        self.csv_writers = {}
        
        logger.info("✅ MetricsCollector initialized")

    '''    
    def _extract_metrics_config(self, config: Dict) -> Dict:
        """Extract metrics collector specific configuration."""
        return {
            'METRICS_COLLECTION_INTERVAL': config.get('METRICS_COLLECTION_INTERVAL', 30),
            'MAX_HISTORY_SIZE': config.get('MAX_HISTORY_SIZE', 1000),
            'METRICS_LOG_PATH': config.get('METRICS_LOG_PATH', 'logs'),
            'ENABLE_METRICS_AGGREGATION': config.get('ENABLE_METRICS_AGGREGATION', True),
            'METRICS_RETENTION_HOURS': config.get('METRICS_RETENTION_HOURS', 24)
        }
    '''
    
    def register_metrics_source(self, source_name: str, 
                              metrics_function: Callable[[], Dict[str, Any]]):
        """
        Register a metrics source.
        The metrics_function should return a dict of metric_name: value pairs.
        """
        self.metrics_sources[source_name] = metrics_function
        logger.info(f"📥 Registered metrics source: {source_name}")
    
    def unregister_metrics_source(self, source_name: str):
        """Unregister a metrics source."""
        if source_name in self.metrics_sources:
            del self.metrics_sources[source_name]
    
    def collect_all_metrics(self) -> MetricsReport:
        """
        Collect metrics from all registered sources.
        """
        start_time = time.time()
        snapshots = []
        errors = []
        
        try:
            self.stats.collections_attempted += 1
            active_sources = 0
            
            # Collect from each source
            for source_name, metrics_function in self.metrics_sources.items():
                try:
                    source_metrics = metrics_function()
                    
                    if source_metrics:
                        active_sources += 1
                        # Create snapshots for each metric
                        for metric_name, value in source_metrics.items():
                            snapshot = MetricSnapshot(
                                metric_name=metric_name,
                                value=value,
                                timestamp=time.time(),
                                source=source_name
                            )
                            snapshots.append(snapshot)
                            
                            # Update current metrics cache
                            self.current_metrics[f"{source_name}.{metric_name}"] = value
                            
                            # Add to historical data
                            self._add_to_history(f"{source_name}.{metric_name}", value)
                
                except Exception as e:
                    errors.append(f"Failed to collect from {source_name}: {str(e)}")
            
            # Update stats
            self.stats.metrics_collected += len(snapshots)
            self.stats.sources_active = active_sources
            self.last_collection_time = time.time()
            
            # Log first collection
            if self.stats.collections_attempted == 1:
                logger.info(f"📥 FIRST COLLECTION: {len(snapshots)} metrics from {active_sources} sources")
            
            # Aggregate metrics if enabled
            aggregated = {}
            if self.config.get('ENABLE_METRICS_AGGREGATION', True):
                aggregated = self._aggregate_metrics(snapshots)
            
            # Create report
            collection_time_ms = (time.time() - start_time) * 1000
            report = MetricsReport(
                snapshots=snapshots,
                aggregated_metrics=aggregated,
                collection_time_ms=collection_time_ms,
                timestamp=time.time(),
                errors=errors
            )
            
            
            # Periodic stats
            if self.stats.should_log():
                self.stats.log_stats()
            
            # Health check
            if self.stats.collections_attempted > 10 and self.stats.sources_active == 0:
                logger.error("🚨 NO ACTIVE METRICS SOURCES after 10 collections")
            
            return report
            
        except Exception as e:
            logger.error(f"❌ Error collecting metrics: {e}")
            
            return MetricsReport(
                snapshots=[],
                aggregated_metrics={},
                collection_time_ms=(time.time() - start_time) * 1000,
                timestamp=time.time(),
                errors=[str(e)]
            )
    
    def _add_to_history(self, metric_key: str, value: Any):
        """Add metric value to historical data."""
        history = self.historical_metrics[metric_key]
        history.append({
            'value': value,
            'timestamp': time.time()
        })
        
        # Maintain max history size
        if len(history) > self.max_history_size:
            history.pop(0)
    
    def _aggregate_metrics(self, snapshots: List[MetricSnapshot]) -> Dict[str, Any]:
        """Aggregate metrics for summary statistics."""
        aggregated = {
            'total_metrics': len(snapshots),
            'by_source': defaultdict(int),
            'queue_metrics': {},
            'performance_metrics': {},
            'health_indicators': {}
        }
        
        # Count by source
        for snapshot in snapshots:
            aggregated['by_source'][snapshot.source] += 1
        
        # Queue-related aggregations
        queue_metrics = [s for s in snapshots if 'queue' in s.metric_name.lower()]
        if queue_metrics:
            queue_sizes = [s.value for s in queue_metrics if isinstance(s.value, (int, float))]
            if queue_sizes:
                total_queue_size = sum(queue_sizes)
                aggregated['queue_metrics'] = {
                    'total_queues': len(queue_metrics),
                    'total_queue_size': total_queue_size,
                    'avg_queue_size': total_queue_size / len(queue_sizes),
                    'max_queue_size': max(queue_sizes)
                }
                
                # Warn on high queue sizes
                if total_queue_size > 1000:
                    logger.warning(f"⚠️ High queue load: {total_queue_size} items")
        
        # Performance-related aggregations
        perf_metrics = [s for s in snapshots if any(term in s.metric_name.lower() 
                       for term in ['time', 'latency', 'duration'])]
        if perf_metrics:
            perf_values = [s.value for s in perf_metrics if isinstance(s.value, (int, float))]
            if perf_values:
                max_latency = max(perf_values)
                aggregated['performance_metrics'] = {
                    'avg_latency': sum(perf_values) / len(perf_values),
                    'max_latency': max_latency
                }
                
                # Warn on high latency
                if max_latency > 1000:  # 1 second
                    logger.warning(f"⚠️ High latency detected: {max_latency:.1f}ms")
        
        # Health indicators
        health_metrics = [s for s in snapshots if any(term in s.metric_name.lower() 
                         for term in ['health', 'status', 'error', 'failure'])]
        
        error_count = sum(1 for s in health_metrics if 'error' in str(s.value).lower() or 
                         'failure' in str(s.value).lower())
        
        if error_count > 0:
            logger.warning(f"⚠️ {error_count} error metrics detected")
        
        aggregated['health_indicators'] = {
            'error_metrics_count': error_count,
            'health_metrics_count': len(health_metrics),
            'overall_health': 'healthy' if error_count == 0 else 'warning'
        }
        
        return dict(aggregated)
    
    def get_system_metrics_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive system metrics summary.
        This is the main method other components use to get metrics.
        """
        # Collect fresh metrics if needed
        current_time = time.time()
        if current_time - self.last_collection_time > self.config.get('METRICS_COLLECTION_INTERVAL', 30):
            self.collect_all_metrics()
        
        # Build summary from current metrics
        summary = {
            'timestamp': current_time,
            'metrics': self.current_metrics.copy(),
            'sources': list(self.metrics_sources.keys()),
            'collection_age_seconds': current_time - self.last_collection_time
        }
        
        # Add aggregated queue metrics
        queue_metrics = {k: v for k, v in self.current_metrics.items() if 'queue' in k.lower()}
        if queue_metrics:
            queue_sizes = [v for v in queue_metrics.values() if isinstance(v, (int, float))]
            if queue_sizes:
                summary['queue_summary'] = {
                    'total_queue_size': sum(queue_sizes),
                    'avg_queue_size': sum(queue_sizes) / len(queue_sizes),
                    'active_queues': len(queue_sizes)
                }
        
        # Add health summary
        summary['health_summary'] = self._calculate_health_summary()
        
        return summary
    
    def _calculate_health_summary(self) -> Dict[str, Any]:
        """Calculate overall system health from metrics."""
        health_score = 100
        issues = []
        
        # Check queue health
        queue_metrics = {k: v for k, v in self.current_metrics.items() if 'queue' in k.lower()}
        if queue_metrics:
            avg_queue = sum(v for v in queue_metrics.values() if isinstance(v, (int, float))) / len(queue_metrics)
            if avg_queue > 200:
                health_score -= 20
                issues.append(f"High queue load: {avg_queue:.1f}")
        
        # Check error rates
        error_metrics = {k: v for k, v in self.current_metrics.items() if 'error' in k.lower() or 'failure' in k.lower()}
        error_count = sum(v for v in error_metrics.values() if isinstance(v, (int, float)))
        if error_count > 10:
            health_score -= 15
            issues.append(f"High error rate: {error_count} errors")
        
        # Check API health
        api_health = self.current_metrics.get('api.health', 'unknown')
        if api_health != 'healthy':
            health_score -= 10
            issues.append(f"API health: {api_health}")
        
        # Determine status
        if health_score >= 90:
            status = 'healthy'
        elif health_score >= 70:
            status = 'warning'
        else:
            status = 'critical'
        
        return {
            'status': status,
            'health_score': max(0, health_score),
            'issues': issues,
            'metrics_count': len(self.current_metrics)
        }
    '''
    def get_metric_history(self, metric_key: str, 
                          time_window_seconds: Optional[int] = None) -> List[Dict]:
        """Get historical values for a specific metric."""
        if metric_key not in self.historical_metrics:
            return []
        
        history = self.historical_metrics[metric_key]
        
        if time_window_seconds:
            cutoff_time = time.time() - time_window_seconds
            return [h for h in history if h['timestamp'] > cutoff_time]
        
        return history.copy()
    
    def clear_metrics(self):
        """Clear all current metrics (useful for testing/reset)."""
        self.current_metrics.clear()
        self.historical_metrics.clear()
        self.last_collection_time = 0

    '''
