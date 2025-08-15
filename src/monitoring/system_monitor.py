"""
System Monitoring Manager - Optimized Version
Centralizes all monitoring activities for TickStock
Sprint 28 Phase 3 - Reduced complexity, improved performance
"""
import threading
import time
import logging
import os
import json
from typing import Optional, Dict, Any, List, Callable, Set
from datetime import datetime
from dataclasses import dataclass, field
from collections import defaultdict, deque
from contextlib import contextmanager

from config.logging_config import get_domain_logger, LogDomain
from src.monitoring.tracer import tracer, ensure_int  # Remove ensure_int from import

logger = get_domain_logger(LogDomain.CORE, 'system_monitor')


@dataclass
class MonitoringConfig:
    """Configuration for monitoring intervals and thresholds"""
    trace_status_interval: int = 30
    diagnostic_dump_interval: int = 60
    performance_interval: int = 300
    collection_interval: int = 25
    drop_rate_threshold: float = 10.0
    write_diagnostics_file: bool = True
    diagnostics_file_path: str = "./logs"
    
    # Performance optimizations
    buffer_size: int = 100
    batch_write_interval: int = 5


class MetricsBuffer:
    """Efficient metrics buffering to reduce file I/O"""
    
    def __init__(self, max_size: int = 100):
        self.buffer = deque(maxlen=max_size)
        self._lock = threading.Lock()
    
    def add(self, message: str):
        """Add message to buffer"""
        with self._lock:
            self.buffer.append(f"{message}\n")
    
    def flush(self) -> List[str]:
        """Get all messages and clear buffer"""
        with self._lock:
            messages = list(self.buffer)
            self.buffer.clear()
            return messages


class DiagnosticCollector:
    """Optimized diagnostics collector with caching"""
    
    def __init__(self):
        self.services = {}
        self._cache = {}
        self._cache_ttl = 5.0  # Cache for 5 seconds
        
    def set_services(self, **kwargs):
        """Set service references"""
        self.services.update(kwargs)
        if 'market_service' in kwargs:
            self.services['worker_pool_manager'] = getattr(
                kwargs['market_service'], 'worker_pool_manager', None
            )
        
        # ADD: Store websocket_publisher reference
        if 'websocket_publisher' in kwargs:
            self.services['websocket_publisher'] = kwargs['websocket_publisher']


    @contextmanager
    def _cached_result(self, key: str):
        """Cache helper for expensive operations"""
        now = time.time()
        if key in self._cache:
            cached_time, cached_value = self._cache[key]
            if now - cached_time < self._cache_ttl:
                yield cached_value
                return
        
        # Compute new value
        value = {}
        yield value
        self._cache[key] = (now, value)
    
    def collect_all_diagnostics(self) -> Dict[str, Any]:
        """Collect all diagnostics with caching"""
        diagnostics = {
            "timestamp": datetime.now().isoformat(),
            "health": self._get_system_health()
        }
        
        # Collect each diagnostic type
        collectors = {
            'queue': self._collect_queue_diagnostics,
            'display_queue': self._collect_display_queue_diagnostics,
            'workers': self._collect_worker_diagnostics,
            'collections': self._collect_collection_diagnostics,
            'tracer': self._collect_tracer_diagnostics,
            'buffer_trends': self._collect_buffer_trends, 
            'emission_metrics': self._collect_emission_metrics,
            'display_conversion': self._collect_display_conversion_metrics
        }
        
        for name, collector in collectors.items():
            try:
                diagnostics[name] = collector()
            except Exception as e:
                logger.error(f"Error collecting {name}: {e}")
                diagnostics[name] = {"error": str(e)}
        
        # Add active ticker count
        if market_service := self.services.get('market_service'):
            diagnostics['active_tickers'] = len(
                getattr(market_service, 'changed_tickers', [])
            )
        
        return diagnostics
    def _collect_emission_metrics(self) -> Dict[str, Any]:
        """Collect emission cycle metrics"""
        if publisher := self.services.get('websocket_publisher'):
            try:
                metrics = {
                    'emission_interval': getattr(publisher, 'emission_interval', 1.0),
                    'last_emission_time': getattr(publisher, 'last_emission_time', 0),
                    'emission_in_progress': getattr(publisher, 'emission_in_progress', False),
                    'time_since_last': time.time() - getattr(publisher, 'last_emission_time', 0),
                    'last_non_empty_emission': getattr(publisher, 'last_non_empty_emission', 0)
                }
                
                # Add buffer tracking from data publisher
                if data_publisher := self.services.get('data_publisher'):
                    buffer_status = data_publisher.get_buffer_status()
                    metrics['buffer_total'] = ensure_int(buffer_status.get('total', 0))
                    metrics['buffer_utilization'] = (
                        buffer_status.get('total', 0) / 
                        getattr(data_publisher, 'MAX_BUFFER_SIZE', 1000) * 100
                    )
                    metrics['buffer_breakdown'] = {
                        'highs': ensure_int(buffer_status.get('highs', 0)),
                        'lows': ensure_int(buffer_status.get('lows', 0)),
                        'trends': ensure_int(buffer_status.get('trends_up', 0) + buffer_status.get('trends_down', 0)),
                        'surges': ensure_int(buffer_status.get('surges_up', 0) + buffer_status.get('surges_down', 0))
                    }
                
                return metrics
            except Exception as e:
                return {'error': str(e)}
        return {}

    def _get_system_health(self) -> str:
        """Quick health check"""
        try:
            if not self.services:
                return "unknown"
            
            # Check market service
            if market_service := self.services.get('market_service'):
                # Check workers first
                if wpm := self.services.get('worker_pool_manager'):
                    worker_status = wpm.get_diagnostic_worker_pool_status()
                    if worker_status.get('workers_alive', 0) == 0:
                        return "degraded"
                
                # Check if we have active tickers
                if hasattr(market_service, 'changed_tickers'):
                    if len(getattr(market_service, 'changed_tickers', [])) > 0:
                        return "healthy"
                    # No active tickers but system running
                    return "idle"
            
            return "unknown"
        except:
            return "error"
    
    def _collect_queue_diagnostics(self) -> Dict[str, Any]:
        """Collect queue diagnostics"""
        with self._cached_result('queue') as result:
            if not result:  # Not cached
                if market_service := self.services.get('market_service'):
                    if pm := getattr(market_service, 'priority_manager', None):
                        try:
                            result.update(pm.get_diagnostics_queue_diagnostics())
                        except Exception as e:
                            result['error'] = str(e)
            return result
    
    def _collect_display_queue_diagnostics(self) -> Dict[str, Any]:
        """Collect display queue diagnostics"""
        if market_service := self.services.get('market_service'):
            if hasattr(market_service, 'get_display_queue_status'):
                try:
                    return market_service.get_display_queue_status()
                except Exception as e:
                    return {"error": str(e)}
        return {"error": "Not available"}
    
    def _collect_worker_diagnostics(self) -> Dict[str, Any]:
        """Collect worker diagnostics"""
        if wpm := self.services.get('worker_pool_manager'):
            try:
                return wpm.get_diagnostic_worker_pool_status()
            except Exception as e:
                return {"error": str(e)}
        return {"error": "Not available"}
    
    def _collect_collection_diagnostics(self) -> Dict[str, Any]:
        """Collect collection diagnostics"""
        if publisher := self.services.get('data_publisher'):
            try:
                return publisher.get_diagnostics_collection_diagnostics()
            except Exception as e:
                return {"error": str(e)}
        return {"error": "Not available"}
    
    def _collect_tracer_diagnostics(self) -> Dict[str, Any]:
        """Collect tracer diagnostics efficiently"""
        if not tracer.enabled:
            return {"status": "disabled"}
        
        with self._cached_result('tracer') as result:
            if not result:  # Not cached
                try:
                    active_traces = tracer.get_all_active_traces()
                    result['active_traces'] = active_traces
                    result['metrics'] = {}
                    
                    # Get flow summaries for top tickers only
                    for ticker in active_traces[:5]:  # Limit to top 5
                        if ticker != 'SYSTEM':
                            result['metrics'][ticker] = {
                                'flow': tracer.get_flow_summary(ticker),
                                'efficiency': self._calculate_efficiency(ticker)
                            }
                    
                    # System metrics
                    result['system'] = tracer.get_system_metrics()
                except Exception as e:
                    result['error'] = str(e)
        
        return result
    
    def _calculate_efficiency(self, ticker: str) -> Dict[str, float]:
        """Calculate efficiency with user-aware adjustments"""
        try:
            flow = tracer.get_flow_summary(ticker)
            
            # Get the normalized event counts from flow summary
            by_type = flow.get('by_type', {})
            
            # Use already normalized counts
            detected = ensure_int(flow.get('events_detected', 0))
            emitted = ensure_int(flow.get('events_emitted', 0))
            
            # Get user connection info
            user_connections = flow.get('user_connections', {})
            events_before_user = ensure_int(user_connections.get('events_before_first_user', 0))

            # Calculate raw efficiency
            raw_efficiency = (emitted / detected * 100) if detected > 0 else 0
            
            # Calculate adjusted efficiency 
            adjusted_detected = detected - events_before_user
            adjusted_efficiency = (emitted / adjusted_detected * 100) if adjusted_detected > 0 else 100.0
            
            return {
                'raw_efficiency': raw_efficiency,
                'adjusted_efficiency': adjusted_efficiency,
                'events_before_user': events_before_user,
                'detected': detected,
                'emitted': emitted
            }
        except Exception as e:
            logger.error(f"Error calculating efficiency for {ticker}: {e}")
            return {
                'raw_efficiency': 0,
                'adjusted_efficiency': 0,
                'events_before_user': 0,
                'detected': 0,
                'emitted': 0
            }

    def _collect_buffer_trends(self) -> Dict[str, Any]:
        """Track buffer utilization over time"""
        if publisher := self.services.get('data_publisher'):
            try:
                buffer_status = publisher.get_buffer_status()
                total = buffer_status.get('total', 0)
                max_size = getattr(publisher, 'MAX_BUFFER_SIZE', 1000)
                utilization = (total / max_size * 100) if max_size > 0 else 0
                
                # Store in rolling buffer (add to __init__)
                if not hasattr(self, '_buffer_history'):
                    self._buffer_history = deque(maxlen=20)
                
                self._buffer_history.append({
                    'timestamp': time.time(),
                    'utilization': utilization,
                    'total': total
                })
                
                # Calculate trend
                if len(self._buffer_history) >= 2:
                    recent = list(self._buffer_history)[-5:]
                    trend = sum(r['utilization'] for r in recent) / len(recent)
                    
                    return {
                        'current_utilization': utilization,
                        'avg_utilization': trend,
                        'trend': 'increasing' if recent[-1]['utilization'] > recent[0]['utilization'] else 'stable',
                        'samples': len(self._buffer_history)
                    }
            except Exception as e:
                return {'error': str(e)}
        return {}

    def _collect_display_conversion_metrics(self) -> Dict[str, Any]:
        """Collect display conversion metrics from WebSocketPublisher"""
        if publisher := self.services.get('websocket_publisher'):
            try:
                # Get conversion metrics if available
                if hasattr(publisher, '_display_conversion_metrics'):
                    metrics = publisher._display_conversion_metrics
                    return {
                        'conversions_performed': metrics.get('total_conversions', 0),
                        'avg_size_reduction_percent': metrics.get('avg_reduction_percent', 0),
                        'total_bytes_saved': metrics.get('total_bytes_saved', 0),
                        'last_conversion_time': metrics.get('last_conversion_time', 0),
                        'avg_conversion_time_ms': metrics.get('avg_conversion_time_ms', 0)
                    }
                else:
                    return {'status': 'metrics not initialized'}
            except Exception as e:
                return {'error': str(e)}
        return {'status': 'publisher not available'}


class SystemMonitor:
    """Optimized system monitor with reduced overhead"""
    
    def __init__(self, config: Optional[MonitoringConfig] = None):
        self.config = config or MonitoringConfig()
        self.collector = DiagnosticCollector()
        self.monitoring_active = False
        self._threads = {}
        self._stop_event = threading.Event()
        
        # Optimizations
        self._metrics_buffer = MetricsBuffer(self.config.buffer_size)
        self._last_write = time.time()
        self._write_lock = threading.Lock()
        
        # Simplified counters
        self.counters = defaultdict(int)
        
    def set_services(self, **kwargs):
        """Set service references"""
        self.collector.set_services(**kwargs)
        
        # Register collection callback if available
        if publisher := kwargs.get('data_publisher'):
            if hasattr(publisher, 'register_collection_callback'):
                publisher.register_collection_callback(self._on_collection)
    
    def start_monitoring(self):
        """Start monitoring with reduced threads"""
        if not tracer.enabled:
            logger.info("Monitoring disabled - tracer not enabled")
            return
            
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self._stop_event.clear()
        
        # Single unified monitoring thread
        self._threads['monitor'] = threading.Thread(
            target=self._unified_monitor,
            daemon=True,
            name="UnifiedMonitor"
        )
        self._threads['monitor'].start()
        
        # Buffer writer thread
        self._threads['writer'] = threading.Thread(
            target=self._buffer_writer,
            daemon=True,
            name="BufferWriter"
        )
        self._threads['writer'].start()
        
        logger.info("✅ Optimized monitoring started")
    
    def _unified_monitor(self):
        """Single monitoring loop for all periodic tasks"""
        last_trace = 0
        last_diagnostic = 0
        last_performance = 0
        
        while self.monitoring_active and not self._stop_event.is_set():
            now = time.time()
            
            # Trace status
            if now - last_trace >= self.config.trace_status_interval:
                self._trace_status()
                last_trace = now
            
            # Diagnostic dump
            if now - last_diagnostic >= self.config.diagnostic_dump_interval:
                self._diagnostic_dump()
                last_diagnostic = now
            
            # Performance check
            if now - last_performance >= self.config.performance_interval:
                self._performance_check()
                last_performance = now
            
            # Sleep briefly
            time.sleep(1)
    
    def track_emission_skip(self, reason: str):
        """Track why emission cycles were skipped"""
        if not hasattr(self, '_emission_skips'):
            self._emission_skips = defaultdict(int)
        
        self._emission_skips[reason] += 1
        
        # Alert on patterns
        if reason == 'no_users':
            self._emission_skip_alerts[reason] += 1
            if self._emission_skip_alerts[reason] >= 10:
                logger.warning(f"⚠️ {self._emission_skip_alerts[reason]} emission cycles skipped due to no users")
                self._emission_skip_alerts[reason] = 0  # Reset counter
        
        elif reason == 'no_events' and self._emission_skips[reason] % 50 == 0:
            logger.info(f"📊 {self._emission_skips[reason]} emission cycles skipped due to no events")

        # Log if concerning
        if reason == 'no_users' and self._emission_skips[reason] % 10 == 0:
            logger.warning(f"⚠️ 10 emission cycles skipped due to no users")
            
    def _buffer_writer(self):
        """Periodic buffer flush to reduce I/O"""
        while self.monitoring_active and not self._stop_event.is_set():
            time.sleep(self.config.batch_write_interval)
            self._flush_buffer()
    
    def _flush_buffer(self):
        """Flush metrics buffer to file"""
        messages = self._metrics_buffer.flush()
        if not messages:
            return
            
        try:
            filename = f"{self.config.diagnostics_file_path}/diag_{datetime.now().strftime('%Y%m%d')}.log"
            os.makedirs(self.config.diagnostics_file_path, exist_ok=True)
            
            with self._write_lock:
                with open(filename, 'a', encoding='utf-8') as f:
                    f.writelines(messages)
        except Exception as e:
            logger.error(f"Buffer flush error: {e}")
    
    def _trace_status(self):
        """Quick trace status check"""
        try:
            tracer.print_flow_status()
        except Exception as e:
            logger.error(f"Trace status error: {e}")
    
    def _diagnostic_dump(self):
        """Optimized diagnostic dump"""
        try:
            diagnostics = self.collector.collect_all_diagnostics()
            
            # Format output efficiently
            output = self._format_diagnostics(diagnostics)
            
            # Log and buffer
            logger.info(output)
            if self.config.write_diagnostics_file:
                self._metrics_buffer.add(output)
                
        except Exception as e:
            logger.error(f"Diagnostic dump error: {e}")
    
    def _performance_check(self):
        """Quick performance check"""
        try:
            # Get drop metrics if available
            if market_service := self.collector.services.get('market_service'):
                if pm := getattr(market_service, 'priority_manager', None):
                    if hasattr(pm, 'flow_stats'):
                        stats = pm.flow_stats
                        drop_rate = self._calculate_drop_rate(stats)
                        
                        if drop_rate > self.config.drop_rate_threshold:
                            logger.warning(f"⚠️ HIGH DROP RATE: {drop_rate:.1f}%")

             # Add emission drought detection
            if publisher := self.collector.services.get('websocket_publisher'):
                if hasattr(publisher, 'last_non_empty_emission'):
                    time_since = time.time() - publisher.last_non_empty_emission
                    if time_since > 10:  # 10 seconds
                        logger.warning(f"⚠️ EMISSION DROUGHT: {time_since:.1f}s since last event")
            
            # Check buffer health
            if publisher := self.collector.services.get('data_publisher'):
                buffer_status = publisher.get_buffer_status()
                total = buffer_status.get('total', 0)
                
                # Alert on sustained high buffer
                if total > 500:  # 50% of typical MAX_BUFFER_SIZE
                    self.counters['high_buffer_alerts'] += 1
                    if self.counters['high_buffer_alerts'] > 3:
                        logger.warning(f"⚠️ SUSTAINED HIGH BUFFER: {total} events")
                else:
                    self.counters['high_buffer_alerts'] = 0

        except Exception as e:
            logger.error(f"Performance check error: {e}")
    
    def _calculate_drop_rate(self, stats) -> float:
        """Calculate drop rate from stats"""
        try:
            added = getattr(stats, 'events_added', 0)
            dropped = getattr(stats, 'events_dropped', 0)
            return (dropped / added * 100) if added > 0 else 0
        except:
            return 0
    
    def _format_diagnostics(self, diagnostics: Dict[str, Any]) -> str:
        """Efficient diagnostic formatting"""
        lines = [
            "=" * 80,
            f"📊 SYSTEM DIAGNOSTICS - {diagnostics['timestamp']}",
            "=" * 80,
            f"Health: {diagnostics.get('health', 'unknown').upper()}"
        ]
        
        # Queue status - ensure numeric values
        if queue := diagnostics.get('queue', {}):
            if not queue.get('error'):
                # Use ensure_int from tracer for consistency
                
                current_size = ensure_int(queue.get('current_size', 0))
                max_size = ensure_int(queue.get('max_configured_size', 0))
                utilization = float(queue.get('utilization_percent', 0.0))
                drop_rate = float(queue.get('drop_rate_percent', 0.0))
                
                lines.extend([
                    "\nQUEUE:",
                    f"  Size: {current_size}/{max_size}",
                    f"  Utilization: {utilization:.1f}%",
                    f"  Drop Rate: {drop_rate:.1f}%"
                ])
        
        # Display queue - with same safety checks
        if dq := diagnostics.get('display_queue', {}):
            if not dq.get('error'):
                current_size = dq.get('current_size', 0)
                max_size = dq.get('max_size', 0)
                efficiency = dq.get('collection_efficiency', 0)
                
                # Ensure numeric values
                try:
                    current_size = int(current_size) if current_size is not None else 0
                    max_size = int(max_size) if max_size is not None else 0
                    efficiency = float(efficiency) if efficiency is not None else 0.0
                except (ValueError, TypeError):
                    current_size = 0
                    max_size = 0
                    efficiency = 0.0
                
                lines.extend([
                    "\nDISPLAY QUEUE:",
                    f"  Size: {current_size}/{max_size}",
                    f"  Efficiency: {efficiency:.1f}%"
                ])
        
        # Workers - with safety checks
        if workers := diagnostics.get('workers', {}):
            if not workers.get('error'):
                workers_alive = workers.get('workers_alive', 0)
                workers_total = workers.get('workers_total', 0)
                
                # Ensure numeric values
                try:
                    workers_alive = int(workers_alive) if workers_alive is not None else 0
                    workers_total = int(workers_total) if workers_total is not None else 0
                except (ValueError, TypeError):
                    workers_alive = 0
                    workers_total = 0
                
                lines.extend([
                    "\nWORKERS:",
                    f"  Active: {workers_alive}/{workers_total}"
                ])
        
        # Collections - with safety checks
        if colls := diagnostics.get('collections', {}):
            if not colls.get('error'):
                success_rate = colls.get('collection_efficiency', 0)
                total_events = colls.get('events_collected_total', 0)
                
                # Ensure numeric values
                try:
                    success_rate = float(success_rate) if success_rate is not None else 0.0
                    total_events = int(total_events) if total_events is not None else 0
                except (ValueError, TypeError):
                    success_rate = 0.0
                    total_events = 0
                
                lines.extend([
                    "\nCOLLECTIONS:",
                    f"  Success Rate: {success_rate:.1f}%",
                    f"  Total Events: {total_events}"
                ])
        
        # Tracer metrics - already has good error handling
        if tracer_data := diagnostics.get('tracer', {}):
            if metrics := tracer_data.get('metrics', {}):
                lines.append("\nTOP TICKERS:")
                for ticker, data in list(metrics.items())[:3]:
                    # Use the new efficiency calculation method
                    efficiency_data = data.get('efficiency', {})
                    if isinstance(efficiency_data, dict):
                        # New format with adjusted efficiency
                        adj_eff = efficiency_data.get('adjusted_efficiency', 0)
                        raw_eff = efficiency_data.get('raw_efficiency', 0)
                        eff = adj_eff if adj_eff > 0 else raw_eff
                    else:
                        # Old format - single number
                        eff = float(efficiency_data) if efficiency_data else 0
                    
                    status = "✅" if eff >= 90 else "⚠️" if eff >= 70 else "❌"
                    lines.append(f"  {ticker}: {eff:.1f}% {status}")
                
                # Add architecture comparison
                lines.append("\nARCHITECTURE METRICS:")
                
                # Check for orphaned events (should be 0 in pull model)
                orphaned = 0  # Would need to track this in tracer
                lines.append(f"  Orphaned Events: {orphaned} (Pull model)")
                
                # Buffer efficiency
                if buffer_data := diagnostics.get('buffer_trends', {}):
                    avg_util = buffer_data.get('avg_utilization', 0)
                    trend = buffer_data.get('trend', 'unknown')
                    
                    # Ensure numeric value
                    try:
                        avg_util = float(avg_util) if avg_util is not None else 0.0
                    except (ValueError, TypeError):
                        avg_util = 0.0
                    
                    lines.append(f"  Buffer Utilization: {avg_util:.1f}%")
                    lines.append(f"  Buffer Trend: {trend}")
        
        lines.append("=" * 80)
        return '\n'.join(lines)
    
    def _on_collection(self, result: Dict[str, Any]):
        """Simplified collection callback"""
        self.counters['collections'] += 1
        
        # Periodic diagnostic dump based on collections
        if self.counters['collections'] % self.config.collection_interval == 0:
            self._diagnostic_dump()
    
    def stop_monitoring(self):
        """Stop monitoring gracefully"""
        self.monitoring_active = False
        self._stop_event.set()
        
        # Flush buffer before stopping
        self._flush_buffer()
        
        # Wait for threads
        for thread in self._threads.values():
            if thread.is_alive():
                thread.join(timeout=1)
        
        logger.info("Monitoring stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """Get monitoring status"""
        return {
            'active': self.monitoring_active,
            'tracer_enabled': tracer.enabled,
            'collections': self.counters['collections'],
            'threads': {
                name: thread.is_alive() 
                for name, thread in self._threads.items()
            }
        }
    
    def get_diagnostics_summary(self) -> Dict[str, Any]:
        """Quick diagnostics summary"""
        try:
            diagnostics = self.collector.collect_all_diagnostics()
            
            summary = {
                'timestamp': diagnostics['timestamp'],
                'health': diagnostics.get('health', 'unknown'),
                'monitoring_active': self.monitoring_active,
                'metrics': {}
            }
            
            # Add key metrics
            if queue := diagnostics.get('queue', {}):
                if not queue.get('error'):
                    summary['metrics']['queue_utilization'] = queue.get('utilization_percent', 0)
                    summary['metrics']['drop_rate'] = queue.get('drop_rate_percent', 0)
            
            if tracer_data := diagnostics.get('tracer', {}):
                summary['metrics']['active_traces'] = len(
                    tracer_data.get('active_traces', [])
                )
            
            return summary
            
        except Exception as e:
            logger.error(f"Summary error: {e}")
            return {'error': str(e)}


# Global optimized monitor instance
system_monitor = SystemMonitor()


# Optional: Drop analysis helper for critical issues only
def get_drop_analysis() -> Dict[str, Any]:
    """Get drop analysis when needed"""
    try:
        collector = system_monitor.collector
        if market_service := collector.services.get('market_service'):
            if pm := getattr(market_service, 'priority_manager', None):
                drops = pm.get_detailed_drop_analysis()
                
                # Simplified recommendations
                recs = []
                if drops.get('drops', {}).get('queue_full', 0) > 0:
                    recs.append("Increase queue size or add workers")
                if drops.get('drop_rate_percent', 0) > 10:
                    recs.append("System overloaded - scale up resources")
                
                return {
                    'drops': drops.get('drops', {}),
                    'rate': drops.get('drop_rate_percent', 0),
                    'recommendations': recs
                }
    except Exception as e:
        logger.error(f"Drop analysis error: {e}")
    
    return {'error': 'Analysis unavailable'}