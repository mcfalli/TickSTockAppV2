"""
Health Monitoring and System Metrics - Phase 4 Implementation
Handles system health monitoring, metrics collection, and performance tracking.
"""

import logging
import time
import threading
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from config.logging_config import get_domain_logger, LogDomain
from src.core.services.session_manager import SessionManager, MarketSession
from src.monitoring.metrics_collector import MetricsCollector

from src.shared.utils import get_eastern_time

logger = get_domain_logger(LogDomain.CORE, 'health_monitor')

@dataclass
class HealthMonitorOperationResult:
    """Result object for health monitor operations."""
    success: bool = True
    metrics_collected: int = 0
    cleanup_items: int = 0
    errors: List[str] = None
    warnings: List[str] = None
    processing_time_ms: float = 0.0
    operation_type: str = "unknown"
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []

class HealthMonitor:
    """
    Monitors system health and collects performance metrics.
    
    Responsibilities:
    - Monitor system performance
    - Collect and log metrics
    - Handle load monitoring  
    - Track API health
    """
    
    def __init__(self, config, market_service, websocket_mgr=None, worker_pool_manager=None):
        """Initialize health monitor with hybrid dependency injection."""
        start_time = time.time()
        
        self.config = config 
        self.market_service = market_service
        
        # 🔧 PHASE 4: Hybrid Dependency Injection Pattern
        self.websocket_mgr = websocket_mgr or market_service.websocket_mgr
        self.worker_pool_manager = worker_pool_manager or getattr(market_service, 'worker_pool_manager', None)
        
        
        # Initialize SessionManager
        self.session_manager = SessionManager(config)
        
        # Register session callback
        self.session_manager.register_session_callback(
            'health_monitor',
            self._handle_session_transition
        )

        # Health monitoring state
        self.monitoring_active = False
        self.load_monitor_thread = None
        
        
        # Performance tracking
        self.performance_stats = {
            'metrics_collections': 0,
            'cleanup_operations': 0,
            'session_changes_detected': 0,
            'monitoring_cycles': 0,
            'total_processing_time_ms': 0.0,
            'avg_processing_time_ms': 0.0,
            'last_operation_time': 0.0,
            'initialization_time_ms': 0.0,
            'last_metrics_time': 0.0,
            'last_cleanup_time': 0.0
        }
        
        # Health tracking
        self.system_health = {
            'status': 'initializing',
            'last_health_check': time.time(),
            'memory_usage_mb': 0,
            'cpu_usage_percent': 0,
            'queue_health': 'unknown',
            'worker_health': 'unknown'
        }
        
        # Validation tracking
        self.validation_enabled = self.config.get('MIGRATION_VALIDATION', False)
        
        # Complete initialization
        initialization_time = (time.time() - start_time) * 1000
        self.performance_stats['initialization_time_ms'] = initialization_time
        

        # Initialize MetricsCollector
        self.metrics_collector = MetricsCollector(config)
        
        # Register this component's metrics
        self.metrics_collector.register_metrics_source(
            'health_monitor',
            self._get_health_metrics
        )
        
        # Register market service metrics
        self.metrics_collector.register_metrics_source(
            'market_service',
            self._get_market_service_metrics
        )
        
        # Register worker pool metrics if available
        if self.worker_pool_manager:
            self.metrics_collector.register_metrics_source(
                'worker_pool',
                self._get_worker_pool_metrics
            )

    
    def _get_health_metrics(self) -> Dict[str, Any]:
        """Provide health monitor's own metrics."""
        return {
            'monitoring_active': self.monitoring_active,
            'monitoring_cycles': self.performance_stats.get('monitoring_cycles', 0),
            'session_changes_detected': self.performance_stats.get('session_changes_detected', 0),
            'health_status': self.system_health.get('status', 'unknown'),
            'health_score': self.system_health.get('health_score', 0)
        }

    def _get_market_service_metrics(self) -> Dict[str, Any]:
        """Collect metrics from market service."""
        metrics = {}
        
        # Event queue metrics
        if hasattr(self.market_service, 'event_queue'):
            metrics['main_queue_size'] = self.market_service.event_queue.qsize()
        
        # API health metrics
        if hasattr(self.market_service, 'api_health'):
            api_health = self.market_service.api_health
            metrics['api_health'] = api_health.get('status', 'unknown')
            metrics['api_connected'] = api_health.get('connected', False)
            metrics['api_failures'] = api_health.get('failures', 0)
            
            response_times = api_health.get('response_times', [])
            if response_times:
                metrics['api_response_time_avg'] = sum(response_times) / len(response_times)
        
        # Processing metrics
        if hasattr(self.market_service, 'total_events_processed'):
            metrics['total_events_processed'] = self.market_service.total_events_processed
        
        if hasattr(self.market_service, 'circuit_breaker_triggers'):
            metrics['circuit_breaker_triggers'] = self.market_service.circuit_breaker_triggers
        
        # Stock tracking
        if hasattr(self.market_service, 'stock_details'):
            metrics['stock_details_count'] = len(self.market_service.stock_details)
        
        return metrics

    def _get_worker_pool_metrics(self) -> Dict[str, Any]:
        """Collect metrics from worker pool manager."""
        try:
            status = self.worker_pool_manager.get_diagnostic_worker_pool_status()
            return {
                'worker_pool_size': status.get('current_pool_size', 0),
                'avg_queue_size': status.get('avg_queue_size', 0),
                'max_queue_size': max(status.get('worker_queue_sizes', [0])),
                'processing_active': status.get('processing_active', False)
            }
        except Exception as e:
            logger.error(f"Error getting worker pool metrics: {e}")
            return {}

    '''
    def _extract_health_monitor_config(self, config: Dict) -> Dict:
        """Extract health monitor specific configuration subset."""
        return {
            'MIGRATION_VALIDATION': config.get('MIGRATION_VALIDATION', False),
            'MIGRATION_PERFORMANCE_LOGGING': config.get('MIGRATION_PERFORMANCE_LOGGING', False),
            'HEALTH_CHECK_INTERVAL': config.get('HEALTH_CHECK_INTERVAL', 30),
            'CLEANUP_INTERVAL': config.get('CLEANUP_INTERVAL', 300),
            'STOCK_DETAILS_MAX_AGE': config.get('STOCK_DETAILS_MAX_AGE', 3600),
            'MARKET_TIMEZONE': config.get('MARKET_TIMEZONE', 'US/Eastern')
        }
    '''

    def _handle_session_transition(self, old_session: str, new_session: str, transition_time: float):
        """Handle session transition callback from SessionManager."""
        try:
            # Update market service session
            if hasattr(self.market_service, 'current_session'):
                self.market_service.current_session = new_session
            
            # Reset all event detection systems through event_manager
            if hasattr(self.market_service, 'event_manager'):
                # Reset all detectors at once
                self.market_service.event_manager.reset_all_for_new_session(new_session)
            else:
                # Backward compatibility - reset individual detectors
                if hasattr(self.market_service, 'highlow_detector'):
                    self.market_service.highlow_detector.reset_for_new_market_session(new_session)
                
                if hasattr(self.market_service, 'surge_detector'):
                    self.market_service.surge_detector.stock_details = getattr(self.market_service, 'stock_details', {})
                    self.market_service.surge_detector.reset_daily_counts()
                
                if hasattr(self.market_service, 'trend_detector'):
                    if hasattr(self.market_service.trend_detector, 'last_sent_trends'):
                        self.market_service.trend_detector.last_sent_trends.clear()
            
            # Reset metrics tracker
            if hasattr(self.market_service, 'market_metrics'):
                self.market_service.market_metrics.reset_session_counts()
            
            # Clear sent events
            for attr in ['sent_high_events', 'sent_low_events', 'sent_trend_events', 'sent_surge_events']:
                if hasattr(self.market_service, attr):
                    getattr(self.market_service, attr).clear()
            
            # Send status update
            if hasattr(self.market_service, '_send_status_update'):
                self.market_service._send_status_update('session_reset', {'new_session': new_session})
            
            self.performance_stats['session_changes_detected'] += 1
                
        except Exception as e:
            logger.error(f"Error handling session transition: {e}", exc_info=True)
            raise

    def start(self) -> HealthMonitorOperationResult:
        """Start health monitoring threads."""
        start_time = time.time()
        operation_result = HealthMonitorOperationResult(operation_type="start_monitoring")
        
        try:
            if self.monitoring_active:
                operation_result.warnings.append("Health monitoring already active")
                return operation_result
            
            self.monitoring_active = True
            threads_started = 0
            
            # Start load monitor thread for dynamic scaling
            self.load_monitor_thread = threading.Thread(
                target=self.monitor_load,
                daemon=True,
                name="health-load-monitor"
            )
            self.load_monitor_thread.start()
            threads_started += 1
            
            # Start session monitor thread
            self.session_monitor_thread = threading.Thread(
                target=self._monitor_session_changes, 
                daemon=True,
                name="health-session-monitor"
            )
            self.session_monitor_thread.start()
            threads_started += 1
            
            operation_result.metrics_collected = threads_started
            self.system_health['status'] = 'monitoring'
            
            
            return operation_result
            
        except Exception as e:
            operation_result.success = False
            operation_result.errors.append(f"Health monitoring startup failed: {str(e)}")
            
            logger.error(f"Error starting health monitoring: {e}", exc_info=True)
            return operation_result
            
        finally:
            processing_time = (time.time() - start_time) * 1000
            operation_result.processing_time_ms = processing_time
            self.performance_stats['total_processing_time_ms'] += processing_time
            self.performance_stats['last_operation_time'] = time.time()
    
    def monitor_load(self):
        """
        Monitor queue sizes and adjust worker pool dynamically.
        Extracted from MarketDataService.monitor_load()
        """
        last_metrics_time = time.time()
        last_cleanup_time = time.time()
        health_check_interval = self.config.get('HEALTH_CHECK_INTERVAL', 30)
        cleanup_interval = self.config.get('CLEANUP_INTERVAL', 300)

        while self.monitoring_active:
            try:
                current_time = time.time()
                self.performance_stats['monitoring_cycles'] += 1
            
                # Log system metrics periodically
                if current_time - last_metrics_time >= health_check_interval:
                    self.log_system_metrics()
                    last_metrics_time = current_time
                    self.performance_stats['last_metrics_time'] = current_time
                                
                # Cleanup operations
                if current_time - last_cleanup_time >= cleanup_interval:
                    self.cleanup_stock_details()
                    last_cleanup_time = current_time
                    self.performance_stats['last_cleanup_time'] = current_time
                
                # Worker pool scaling (if WorkerPoolManager available)
                if self.worker_pool_manager:
                    self._handle_worker_pool_scaling()
                elif hasattr(self.market_service, 'worker_queues'):
                    # Fallback to legacy worker pool scaling
                    self._handle_legacy_worker_pool_scaling()
                
                # Sleep before next check
                time.sleep(5)
                
            except Exception as e:
                logger.error(f"Error in HealthMonitor load monitoring: {e}", exc_info=True)
                time.sleep(5)
        
    
    def _handle_worker_pool_scaling(self):
        """Handle worker pool scaling via WorkerPoolManager."""
        try:
            worker_status = self.worker_pool_manager.get_diagnostic_worker_pool_status()
            
            if not worker_status.get('processing_active', False):
                return
            
            # Calculate average queue size
            queue_sizes = worker_status.get('worker_queue_sizes', [])
            avg_queue_size = worker_status.get('avg_queue_size', 0)
            current_pool_size = worker_status.get('current_pool_size', 0)
            
            # Calculate target worker pool size based on load
            min_size = self.config.get('MIN_WORKER_POOL_SIZE', 2)
            max_size = self.config.get('MAX_WORKER_POOL_SIZE', 16)
            
            # Base formula: 1 worker per 100 items in queues, but within bounds
            target_size = min(max(min_size, int(avg_queue_size / 100) + 1), max_size)
            
            # Adjust worker pool if needed
            if target_size != current_pool_size:
                scaling_result = self.worker_pool_manager.adjust_worker_pool(target_size)
                if scaling_result.success:
                    logger.debug(f"DIAG-HEALTH-MONITOR: HealthMonitor: Worker pool scaled to {target_size} (was {current_pool_size})")
                else:
                    logger.warning(f"DIAG-HEALTH-MONITOR: HealthMonitor: Worker pool scaling failed: {scaling_result.errors}")
            
            # Update health status
            self.system_health['worker_health'] = 'healthy' if avg_queue_size < 200 else 'overloaded'
            self.system_health['queue_health'] = 'healthy' if avg_queue_size < 100 else 'warning'
            
        except Exception as e:
            logger.error(f"Error in worker pool scaling: {e}", exc_info=True)
    
    def _handle_legacy_worker_pool_scaling(self):
        """Handle legacy worker pool scaling for backward compatibility."""
        try:
            if not hasattr(self.market_service, 'worker_queues') or not hasattr(self.market_service, 'adjust_worker_pool'):
                return
            
            # Calculate average queue size
            queue_sizes = [q.qsize() for q in self.market_service.worker_queues]
            avg_queue_size = sum(queue_sizes) / len(queue_sizes) if queue_sizes else 0
            
            # Calculate target worker pool size based on load
            min_size = getattr(self.market_service, 'min_worker_pool_size', 2)
            max_size = getattr(self.market_service, 'max_worker_pool_size', 16)
            target_size = min(max(min_size, int(avg_queue_size / 100) + 1), max_size)
            
            # Adjust worker pool if needed
            current_size = len(getattr(self.market_service, 'worker_pool', []))
            if target_size != current_size:
                self.market_service.adjust_worker_pool(target_size)
            
  
            
        except Exception as e:
            logger.error(f"Error in legacy worker pool scaling: {e}", exc_info=True)
    
    def log_system_metrics(self) -> HealthMonitorOperationResult:
        """
        Log comprehensive system metrics - SIMPLIFIED to use MetricsCollector.
        """
        start_time = time.time()
        operation_result = HealthMonitorOperationResult(operation_type="log_system_metrics")
        
        try:
            self.performance_stats['metrics_collections'] += 1
            
            # Use MetricsCollector to gather all metrics
            metrics_report = self.metrics_collector.collect_all_metrics()
            
            if metrics_report.errors:
                operation_result.warnings.extend(metrics_report.errors)
            
            # Get summary for logging
            metrics_summary = self.metrics_collector.get_system_metrics_summary()
            

            
            # Update health status based on metrics
            health_summary = metrics_summary.get('health_summary', {})
            self.system_health.update({
                'status': health_summary.get('status', 'unknown'),
                'last_health_check': time.time(),
                'health_score': health_summary.get('health_score', 0)
            })
            
            operation_result.metrics_collected = len(metrics_report.snapshots)
            

            
            return operation_result
            
        except Exception as e:
            operation_result.success = False
            operation_result.errors.append(f"Metrics collection failed: {str(e)}")
            logger.error(f"Error logging system metrics: {e}", exc_info=True)
            return operation_result
            
        finally:
            processing_time = (time.time() - start_time) * 1000
            operation_result.processing_time_ms = processing_time
            self.performance_stats['total_processing_time_ms'] += processing_time
            self.performance_stats['last_operation_time'] = time.time()
    
   
    
    def _monitor_session_changes(self):
        """
        Monitor for market session changes - SIMPLIFIED to use SessionManager.
        """
        
        while self.monitoring_active:
            try:
                # Check for session transition
                transition = self.session_manager.check_session_transition()
                

                
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in session monitoring: {e}", exc_info=True)
                time.sleep(60)
        

    def cleanup_stock_details(self) -> HealthMonitorOperationResult:
        """
        Remove stale entries from stock_details and ticker_to_worker.
        Extracted from MarketDataService.cleanup_stock_details()
        """
        start_time = time.time()
        operation_result = HealthMonitorOperationResult(operation_type="cleanup_stock_details")
        
        try:
            self.performance_stats['cleanup_operations'] += 1
            
            current_time = time.time()
            max_age = self.config.get('STOCK_DETAILS_MAX_AGE', 3600)  # 1 hour
            to_remove = []
            
            # Check if stock_details exists
            if not hasattr(self.market_service, 'stock_details'):
                operation_result.warnings.append("No stock_details to clean up")
                return operation_result
            
            stock_details = self.market_service.stock_details
            
            # Find stale entries
            for ticker, details in stock_details.items():
                last_update = getattr(details, 'last_trend_update', None) or getattr(details, 'last_event_time', 0)
                if isinstance(last_update, datetime):
                    last_update = last_update.timestamp()
                if current_time - last_update > max_age:
                    to_remove.append(ticker)
            
            # Remove stale entries
            for ticker in to_remove:
                del stock_details[ticker]
                
                # Also remove from ticker_to_worker mapping
                if hasattr(self.market_service, 'ticker_to_worker') and ticker in self.market_service.ticker_to_worker:
                    del self.market_service.ticker_to_worker[ticker]
            
            operation_result.cleanup_items = len(to_remove)

            return operation_result
            
        except Exception as e:
            operation_result.success = False
            operation_result.errors.append(f"Cleanup failed: {str(e)}")
            
            logger.error(f"Error in stock details cleanup: {e}", exc_info=True)
            return operation_result
            
        finally:
            processing_time = (time.time() - start_time) * 1000
            operation_result.processing_time_ms = processing_time
            self.performance_stats['total_processing_time_ms'] += processing_time
            self.performance_stats['last_operation_time'] = time.time()
    
    def _get_memory_usage(self) -> float:
        """
        Get current memory usage in MB.
        Extracted from MarketDataService._get_memory_usage()
        """
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            return memory_info.rss / (1024 * 1024)  # Convert to MB
        except ImportError:
            return 0  # psutil not available
        except Exception as e:
            logger.error(f"Error getting memory usage: {e}")
            return 0
    
    def _get_cpu_usage(self) -> float:
        """
        Get current CPU usage percentage.
        Extracted from MarketDataService._get_cpu_usage()
        """
        try:
            import psutil
            process = psutil.Process()
            return process.cpu_percent(interval=0.1)
        except ImportError:
            return 0  # psutil not available
        except Exception as e:
            logger.error(f"Error getting CPU usage: {e}")
            return 0
    
    def stop_monitoring(self) -> HealthMonitorOperationResult:
        """Stop all health monitoring threads."""
        start_time = time.time()
        operation_result = HealthMonitorOperationResult(operation_type="stop_monitoring")
        
        try:
            self.monitoring_active = False
            threads_stopped = 0
            
            # Wait for load monitor thread
            if self.load_monitor_thread and self.load_monitor_thread.is_alive():
                self.load_monitor_thread.join(timeout=2)
                if not self.load_monitor_thread.is_alive():
                    threads_stopped += 1
                else:
                    operation_result.warnings.append("Load monitor thread did not stop gracefully")
            
            # Wait for session monitor thread
            if self.session_monitor_thread and self.session_monitor_thread.is_alive():
                self.session_monitor_thread.join(timeout=2)
                if not self.session_monitor_thread.is_alive():
                    threads_stopped += 1
                else:
                    operation_result.warnings.append("Session monitor thread did not stop gracefully")
            
            operation_result.metrics_collected = threads_stopped
            self.system_health['status'] = 'stopped'
            
            logger.info(f"DIAG-HEALTH-MONITOR: HealthMonitor: Stopped {threads_stopped} monitoring threads")
            
            return operation_result
            
        except Exception as e:
            operation_result.success = False
            operation_result.errors.append(f"Monitoring shutdown failed: {str(e)}")
            
            logger.error(f"Error stopping health monitoring: {e}", exc_info=True)
            return operation_result
            
        finally:
            processing_time = (time.time() - start_time) * 1000
            operation_result.processing_time_ms = processing_time
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get current system health status."""
        try:
            current_time = time.time()
            
            # Update health check timestamp
            self.system_health['last_health_check'] = current_time
            
            # Collect current metrics for health assessment
            metrics = self._collect_system_metrics()
            
            # Determine overall health
            health_score = 100
            issues = []
            
            # Check API health
            if metrics.get('api_health') != 'healthy':
                health_score -= 20
                issues.append(f"API health: {metrics.get('api_health', 'unknown')}")
            
            # Check queue sizes
            avg_queue_size = metrics.get('avg_worker_queue_size', 0)
            if avg_queue_size > 200:
                health_score -= 15
                issues.append(f"High queue load: {avg_queue_size:.1f}")
            elif avg_queue_size > 100:
                health_score -= 5
                issues.append(f"Moderate queue load: {avg_queue_size:.1f}")
            
            # Check memory usage
            memory_mb = metrics.get('memory_usage_mb', 0)
            if memory_mb > 1000:  # > 1GB
                health_score -= 10
                issues.append(f"High memory usage: {memory_mb:.1f}MB")
            
            # Check CPU usage
            cpu_percent = metrics.get('cpu_usage_percent', 0)
            if cpu_percent > 80:
                health_score -= 10
                issues.append(f"High CPU usage: {cpu_percent:.1f}%")
            
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
                'monitoring_active': self.monitoring_active,
                'system_metrics': metrics,
                'last_health_check': current_time,
                'uptime_seconds': current_time - (self.performance_stats['initialization_time_ms'] / 1000),
                'health_check_timestamp': current_time
            }
            
        except Exception as e:
            logger.error(f"Error getting health status: {e}")
            return {
                'status': 'error',
                'health_score': 0,
                'error': str(e),
                'health_check_timestamp': time.time()
            }
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report for HealthMonitor."""
        try:
            current_time = time.time()
            
            return {
                'monitoring_performance': {
                    'metrics_collections': self.performance_stats['metrics_collections'],
                    'cleanup_operations': self.performance_stats['cleanup_operations'],
                    'session_changes_detected': self.performance_stats['session_changes_detected'],
                    'monitoring_cycles': self.performance_stats['monitoring_cycles']
                },
                'timing_metrics': {
                    'avg_processing_time_ms': round(self.performance_stats['avg_processing_time_ms'], 2),
                    'total_processing_time_ms': round(self.performance_stats['total_processing_time_ms'], 2),
                    'initialization_time_ms': round(self.performance_stats['initialization_time_ms'], 2),
                    'last_operation_ago': round(current_time - self.performance_stats['last_operation_time'], 2),
                    'last_metrics_ago': round(current_time - self.performance_stats['last_metrics_time'], 2),
                    'last_cleanup_ago': round(current_time - self.performance_stats['last_cleanup_time'], 2)
                },
                'thread_status': {
                    'monitoring_active': self.monitoring_active,
                    'load_monitor_alive': self.load_monitor_thread.is_alive() if self.load_monitor_thread else False,
                    'session_monitor_alive': self.session_monitor_thread.is_alive() if self.session_monitor_thread else False
                },
                'configuration': {
                    'health_check_interval': self.config.get('HEALTH_CHECK_INTERVAL', 30),
                    'cleanup_interval': self.config.get('CLEANUP_INTERVAL', 300),
                    'stock_details_max_age': self.config.get('STOCK_DETAILS_MAX_AGE', 3600),
                    'validation_enabled': self.validation_enabled
                },
                'system_health': self.system_health,
                'report_timestamp': current_time
            }
            
        except Exception as e:
            logger.error(f"Error generating HealthMonitor performance report: {e}")
            return {'error': str(e), 'report_timestamp': time.time()}
    
    def reset_performance_stats(self):
        """Reset performance statistics."""
        initialization_time = self.performance_stats['initialization_time_ms']
        
        self.performance_stats = {
            'metrics_collections': 0,
            'cleanup_operations': 0,
            'session_changes_detected': 0,
            'monitoring_cycles': 0,
            'total_processing_time_ms': 0.0,
            'avg_processing_time_ms': 0.0,
            'last_operation_time': 0.0,
            'initialization_time_ms': initialization_time,  # Preserve initialization time
            'last_metrics_time': 0.0,
            'last_cleanup_time': 0.0
        }
        
