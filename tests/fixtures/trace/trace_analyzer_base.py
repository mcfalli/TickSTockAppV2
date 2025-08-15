#!/usr/bin/env python3
"""
Base trace analyzer framework for TickStock debug traces.
Provides core functionality for analyzing JSON trace files.
Phase 4 Enhanced: Compatible with Phase 2/3 improvements
"""
import json
import os
from datetime import datetime
from collections import defaultdict, Counter
from typing import Dict, List, Any, Optional, Tuple
import statistics


class TraceAnalyzer:
    """Base class for analyzing TickStock trace files - Phase 4 Enhanced."""
    
    def __init__(self, trace_file_path: str):
        """Initialize analyzer with trace file."""
        self.trace_file_path = trace_file_path
        self.trace_data = self._load_trace()
        self.summary = self.trace_data.get('summary', {})
        self.steps = self.trace_data.get('steps', [])
        self.ticker = self.trace_data.get('ticker', 'UNKNOWN')
        self.trace_id = self.trace_data.get('trace_id', 'UNKNOWN')
        
        # Handle both single ticker and multi-ticker traces
        if 'ticker_summary' in self.trace_data:
            # Multi-ticker trace (from export_all)
            self.ticker_summary = self.trace_data.get('ticker_summary', {})
            self.is_multi_ticker = True
        else:
            # Single ticker trace
            self.ticker_summary = {self.ticker: len(self.steps)}
            self.is_multi_ticker = False
        
    def _load_trace(self) -> Dict[str, Any]:
        """Load trace JSON file."""
        if not os.path.exists(self.trace_file_path):
            raise FileNotFoundError(f"Trace file not found: {self.trace_file_path}")
            
        with open(self.trace_file_path, 'r') as f:
            data = json.load(f)
        
        # Handle multi-ticker trace format
        if 'ticker_summary' in data and 'summary' not in data:
            # Create a synthetic summary from the trace steps
            data['summary'] = self._build_summary_from_steps(data.get('steps', []))
        
        return data
    
    def _build_summary_from_steps(self, steps: List[Dict]) -> Dict[str, Any]:
        """Build summary data from trace steps for multi-ticker traces."""
        from collections import defaultdict
        
        summary = {
            'events_generated': defaultdict(int),
            'events_emitted': defaultdict(int),
            'ticks_received': 0,
            'counters': defaultdict(int),
            'component_timings': defaultdict(float),
            'user_connections': {
                'first_user_time': None,
                'events_before_first_user': 0,
                'total_users': 0,
                'raw_efficiency': 0,
                'adjusted_efficiency': 0
            }
        }
        
        first_user_time = None
        events_before_user = defaultdict(int)
        total_events_generated = defaultdict(int)
        
        for step in steps:
            action = step.get('action', '')
            data = step.get('data', {})
            timestamp = step.get('timestamp', 0)
            component = step.get('component', '')
            duration = step.get('duration_to_next_ms', 0)
            
            # Track component timings
            if duration > 0:
                summary['component_timings'][component] += duration / 1000.0  # Convert to seconds
            
            # Track user connections - look for ANY user connection across all tickers
            if action == 'user_connected' and component == 'WebSocketManager':
                user_id = data.get('details', {}).get('user_id')
                if user_id and first_user_time is None:
                    first_user_time = timestamp
                    summary['user_connections']['first_user_time'] = first_user_time
                    summary['user_connections']['total_users'] += 1
            
            # Count events from event_detected actions
            if action == 'event_detected':
                details = data.get('details', {})
                output_count = data.get('output_count', 0)
                
                if 'event_breakdown' in details:
                    for event_type, count in details['event_breakdown'].items():
                        normalized_type = event_type + 's' if not event_type.endswith('s') else event_type
                        total_events_generated[normalized_type] += count
                        summary['counters']['events_detected_total'] += count
                        
                        # Only count as "before user" if no user has connected yet
                        if first_user_time is None or timestamp < first_user_time:
                            events_before_user[normalized_type] += count
                else:
                    # Single event type
                    event_type = details.get('event_type', 'unknown')
                    if event_type != 'unknown':
                        normalized_type = event_type + 's' if not event_type.endswith('s') else event_type
                        total_events_generated[normalized_type] += output_count
                        summary['counters']['events_detected_total'] += output_count
                        
                        if first_user_time is None or timestamp < first_user_time:
                            events_before_user[normalized_type] += output_count
            
            # Count emitted events
            elif action == 'event_emitted':
                output_count = data.get('output_count', 1)
                details = data.get('details', {})
                event_type = details.get('event_type', details.get('type', 'unknown'))
                
                if event_type != 'unknown':
                    normalized_type = event_type + 's' if not event_type.endswith('s') else event_type
                    summary['events_emitted'][normalized_type] += output_count
                    summary['counters']['events_emitted_total'] += output_count
            
            # Track ticks
            elif action == 'tick_received':
                summary['ticks_received'] += 1
                summary['counters']['ticks_received'] = summary['ticks_received']
        
        # Convert events_generated from our tracking
        summary['events_generated'] = dict(total_events_generated)
        
        # Calculate summary metrics
        total_before = sum(events_before_user.values())
        summary['user_connections']['events_before_first_user'] = total_before
        summary['counters']['events_before_first_user'] = total_before
        
        # Calculate efficiencies
        total_gen = sum(summary['events_generated'].values())
        total_emit = sum(summary['events_emitted'].values())
        
        if total_gen > 0:
            summary['user_connections']['raw_efficiency'] = (total_emit / total_gen) * 100
            adjusted_gen = total_gen - total_before
            if adjusted_gen > 0:
                summary['user_connections']['adjusted_efficiency'] = (total_emit / adjusted_gen) * 100
            else:
                # All events were before first user
                summary['user_connections']['adjusted_efficiency'] = 0
        
        # Convert defaultdicts to regular dicts
        summary['events_emitted'] = dict(summary['events_emitted'])
        summary['counters'] = dict(summary['counters'])
        summary['component_timings'] = dict(summary['component_timings'])
        
        return summary

    def get_basic_info(self) -> Dict[str, Any]:
        """Get basic trace information - Phase 4 enhanced with user connection data."""
        # Extract user connection info from summary if available
        user_connections = self.summary.get('user_connections', {})
        
        return {
            'ticker': self.ticker,
            'trace_id': self.trace_id,
            'start_time': self.trace_data.get('start_time', 0),
            'end_time': self.trace_data.get('end_time', 0),
            'duration_seconds': self.trace_data.get('duration_seconds', 0),
            'steps_count': len(self.steps),
            'ticks_received': self.summary.get('ticks_received') or self.summary.get('counters', {}).get('ticks_received', 0),
            'ticks_per_second': self.summary.get('ticks_per_second', 0),
            # Phase 2 additions
            'total_users': user_connections.get('total_users', 0),
            'first_user_time': user_connections.get('first_user_time'),
            'events_before_first_user': user_connections.get('events_before_first_user', 0),
            'adjusted_efficiency': user_connections.get('adjusted_efficiency', 0),
            'raw_efficiency': user_connections.get('raw_efficiency', 0),
            'is_multi_ticker': self.is_multi_ticker,
            'ticker_summary': self.ticker_summary if self.is_multi_ticker else None
        }
    
    def analyze_event_flow(self) -> Dict[str, Any]:
        """Analyze event generation, filtering, and emission with Phase 2/3 improvements."""
        
        # First, check if we have summary data with the authoritative counts from tracer
        if 'events_generated' in self.summary and 'events_emitted' in self.summary:
            # Use the tracer's authoritative counts (already deduplicated)
            events_gen_summary = self.summary['events_generated']
            events_emit_summary = self.summary['events_emitted']
            user_connections = self.summary.get('user_connections', {})
            
            # Build flow analysis from summary
            flow_analysis = {}
            
            for event_type in ['highs', 'lows', 'surges', 'trends']:
                generated = events_gen_summary.get(event_type, 0)
                emitted = events_emit_summary.get(event_type, 0)
                
                # Get intermediate stages from counters if available
                counters = self.summary.get('counters', {})
                event_type_singular = event_type.rstrip('s')  # Convert back to singular for counter keys
                
                queued = counters.get(f'events_queued_{event_type_singular}', 0)
                collected = counters.get(f'events_collected_{event_type_singular}', 0)
                
                # Calculate events before user for this type
                events_before_user = 0
                if user_connections.get('first_user_time'):
                    # Count events of this type before first user from steps
                    for step in self.steps:
                        if step.get('timestamp', 0) < user_connections['first_user_time']:
                            if step.get('action') == 'event_detected':
                                details = step.get('data', {}).get('details', {})
                                if details.get('event_type') == event_type_singular:
                                    events_before_user += step.get('data', {}).get('output_count', 0)
                                elif details.get('event_breakdown', {}).get(event_type_singular):
                                    events_before_user += details['event_breakdown'][event_type_singular]
                
                # Calculate adjusted metrics
                adjusted_generated = generated - events_before_user
                adjusted_efficiency = (emitted / adjusted_generated * 100) if adjusted_generated > 0 else 0
                
                flow_analysis[event_type] = {
                    'generated': generated,
                    'filtered': 0,  # Will be calculated from steps if needed
                    'queued': queued,
                    'collected': collected,
                    'ready_for_emission': 0,  # Will be calculated from steps if needed
                    'emitted': emitted,
                    'dropped': generated - emitted,
                    'drop_rate': ((generated - emitted) / generated * 100) if generated > 0 else 0,
                    'filter_rate': 0,  # Will be calculated if we have filter data
                    'efficiency': (emitted / generated * 100) if generated > 0 else 0,
                    # Phase 2 additions
                    'events_before_user': events_before_user,
                    'adjusted_generated': adjusted_generated,
                    'adjusted_efficiency': adjusted_efficiency,
                    'queue_efficiency': (queued / generated * 100) if generated > 0 else 0,
                    'collection_efficiency': (collected / queued * 100) if queued > 0 else 0
                }
            
            # Add overall user connection analysis
            flow_analysis['user_connection_analysis'] = {
                'first_user_time': user_connections.get('first_user_time'),
                'total_events_before_user': user_connections.get('events_before_first_user', 0),
                'impact_on_efficiency': user_connections.get('raw_efficiency', 0) - user_connections.get('adjusted_efficiency', 0)
            }
            
            # Now scan steps to fill in missing data (filtered, ready_for_emission, etc.)
            for step in self.steps:
                action = step.get('action', '')
                data = step.get('data', {})
                
                # Count filtered events
                if 'filtered' in action and data.get('filtered_out'):
                    details = data.get('details', {})
                    event_type = details.get('event_type', details.get('type', 'unknown'))
                    event_type = self._normalize_event_type_for_summary(event_type)
                    if event_type in flow_analysis and isinstance(flow_analysis[event_type], dict):
                        flow_analysis[event_type]['filtered'] += 1
                
                # Count ready for emission events
                elif action == 'event_ready_for_emission':
                    details = data.get('details', {})
                    for evt_type in ['highs', 'lows', 'trends', 'surges']:
                        if evt_type in details and details[evt_type]:
                            if evt_type in flow_analysis and isinstance(flow_analysis[evt_type], dict):
                                flow_analysis[evt_type]['ready_for_emission'] += len(details[evt_type])
            
            # Update filter rates only for event types (not user_connection_analysis)
            for event_type, stats in flow_analysis.items():
                if isinstance(stats, dict) and 'generated' in stats and stats['generated'] > 0:
                    stats['filter_rate'] = (stats['filtered'] / stats['generated'] * 100)
            
            return flow_analysis
        
        else:
            # Fallback: Count from steps (for older traces or when summary is incomplete)
            # Initialize counters
            events_generated = defaultdict(int)
            events_filtered = defaultdict(int)
            events_emitted = defaultdict(int)
            events_queued = defaultdict(int)
            events_collected = defaultdict(int)
            events_ready = defaultdict(int)
            
            # Track user connection timing
            first_user_time = None
            events_before_user = defaultdict(int)
            
            # Count from trace steps
            for step in self.steps:
                action = step.get('action', '')
                data = step.get('data', {})
                timestamp = step.get('timestamp', 0)
                
                # Track user connections (Phase 2)
                if action == 'user_connected' and first_user_time is None:
                    first_user_time = timestamp
                
                # Handle nested data structure from Phase 2 tracer
                actual_data = self._extract_actual_data(data)
                
                # Count generated events
                if any(x in action for x in ['event_created', 'event_generated', 'event_detected', 
                                            'highlow_event_detected', 'surge_event_detected', 
                                            'trend_event_detected']):
                    event_type = self._extract_and_normalize_event_type(action, actual_data)
                    if event_type:
                        count = self._get_event_count(data, actual_data)
                        events_generated[event_type] += count
                        
                        # Track events before first user
                        if first_user_time is None or timestamp < first_user_time:
                            events_before_user[event_type] += count
                
                # Count queued events
                elif action == 'event_queued':
                    event_type = self._normalize_event_type_for_summary(actual_data.get('event_type', 'unknown'))
                    if event_type and event_type != 'unknown':
                        # Only count if queue_result is not False
                        if actual_data.get('queue_result', True):
                            events_queued[event_type] += 1
                
                # Count collected events
                elif action in ['events_collected', 'display_queue_collected']:
                    output_count = data.get('output_count', 0)
                    if 'event_breakdown' in actual_data:
                        for evt_type, count in actual_data['event_breakdown'].items():
                            normalized_type = self._normalize_event_type_for_summary(evt_type)
                            events_collected[normalized_type] += count
                    else:
                        # Distribute evenly across types if no breakdown
                        if output_count > 0:
                            for event_type in ['highs', 'lows']:
                                events_collected[event_type] += output_count // 2
                
                # Count ready for emission events
                elif action == 'event_ready_for_emission':
                    if 'details' in data:
                        details = data['details']
                        for event_type in ['highs', 'lows', 'trends', 'surges']:
                            if event_type in details:
                                events_ready[event_type] += len(details[event_type])
                
                # Count emitted events
                elif action == 'event_emitted':
                    output_count = data.get('output_count', 1)  # Use output_count!
                    event_type = actual_data.get('event_type', actual_data.get('type', 'unknown'))
                    event_type = self._normalize_event_type_for_summary(event_type)
                    if event_type and event_type != 'unknown':
                        events_emitted[event_type] += output_count
                
                # Count filtered events
                elif 'filtered' in action and data.get('filtered_out'):
                    event_type = actual_data.get('event_type', actual_data.get('type', 'unknown'))
                    event_type = self._normalize_event_type_for_summary(event_type)
                    if event_type and event_type != 'unknown':
                        events_filtered[event_type] += 1
            
            # Calculate flow with actual counts
            flow_analysis = {}
            total_events_before_user = sum(events_before_user.values())
            
            for event_type in ['highs', 'lows', 'surges', 'trends']:
                generated = events_generated.get(event_type, 0)
                filtered = events_filtered.get(event_type, 0)
                queued = events_queued.get(event_type, 0)
                collected = events_collected.get(event_type, 0)
                ready = events_ready.get(event_type, 0)
                emitted = events_emitted.get(event_type, 0)
                
                # Calculate adjusted metrics (Phase 2)
                events_before = events_before_user.get(event_type, 0)
                adjusted_generated = generated - events_before
                
                flow_analysis[event_type] = {
                    'generated': generated,
                    'filtered': filtered,
                    'queued': queued,
                    'collected': collected,
                    'ready_for_emission': ready,
                    'emitted': emitted,
                    'dropped': generated - emitted,
                    'drop_rate': ((generated - emitted) / generated * 100) if generated > 0 else 0,
                    'filter_rate': (filtered / generated * 100) if generated > 0 else 0,
                    'efficiency': (emitted / generated * 100) if generated > 0 else 0,
                    # Phase 2 additions
                    'events_before_user': events_before,
                    'adjusted_generated': adjusted_generated,
                    'adjusted_efficiency': (emitted / adjusted_generated * 100) if adjusted_generated > 0 else 0,
                    'queue_efficiency': (queued / generated * 100) if generated > 0 else 0,
                    'collection_efficiency': (collected / queued * 100) if queued > 0 else 0
                }
            
            # Add overall user connection analysis
            flow_analysis['user_connection_analysis'] = {
                'first_user_time': first_user_time,
                'total_events_before_user': total_events_before_user,
                'impact_on_efficiency': self._calculate_efficiency_impact(flow_analysis)
            }
            
            return flow_analysis
    
    def _extract_actual_data(self, data: Dict) -> Dict:
        """Extract actual data from nested structure (Phase 2 compatibility)."""
        # Handle nested data structure from tracer
        if 'before' in data and isinstance(data['before'], dict):
            return data['before']
        elif 'after' in data and isinstance(data['after'], dict):
            return data['after']
        elif 'details' in data and isinstance(data['details'], dict):
            return data['details']
        return data
    
    def _get_event_count(self, data: Dict, actual_data: Dict) -> int:
        """Get event count from data, handling various formats."""
        # Try output_count first
        if 'output_count' in data:
            return data['output_count']
        
        # Handle multiple event detection
        if actual_data.get('event_type') == 'multiple' and 'event_breakdown' in actual_data:
            return sum(actual_data['event_breakdown'].values())
        
        # Default to 1
        return 1
    
    def _calculate_efficiency_impact(self, flow_analysis: Dict) -> float:
        """Calculate the impact of user connection timing on efficiency."""
        total_generated = sum(f['generated'] for f in flow_analysis.values() if isinstance(f, dict))
        total_before_user = sum(f.get('events_before_user', 0) for f in flow_analysis.values() if isinstance(f, dict))
        
        if total_generated > 0:
            return (total_before_user / total_generated) * 100
        return 0

    def _normalize_event_type_for_summary(self, event_type: str) -> str:
        """Normalize event type to match summary categories (highs, lows, surges, trends)."""
        if not event_type:
            return 'unknown'
        
        event_type = event_type.lower()
        
        # Handle session_high/session_low -> highs/lows
        if event_type in ['high', 'session_high']:
            return 'highs'
        elif event_type in ['low', 'session_low']:
            return 'lows'
        elif event_type in ['surge', 'surge_up', 'surge_down']:
            return 'surges'
        elif event_type in ['trend', 'trend_up', 'trend_down']:
            return 'trends'
        
        # Default: add 's' if not present
        if not event_type.endswith('s'):
            return event_type + 's'
        
        return event_type

    def _extract_and_normalize_event_type(self, action: str, data: Dict) -> Optional[str]:
        """Extract event type from action or data and normalize it."""
        # Try to get from data first
        event_type = data.get('event_type', data.get('type', None))
        
        # If not in data, try to extract from action
        if not event_type:
            if 'surge' in action.lower():
                event_type = 'surge'
            elif 'high' in action.lower():
                event_type = 'high'
            elif 'low' in action.lower():
                event_type = 'low'
            elif 'trend' in action.lower():
                event_type = 'trend'
        
        # Normalize to summary format
        if event_type:
            return self._normalize_event_type_for_summary(event_type)
        
        return None
    
    def analyze_performance(self) -> Dict[str, Any]:
        """Analyze component performance and bottlenecks - Phase 3 enhanced."""
        component_timings = self.summary.get('component_timings', {})
        total_time = sum(component_timings.values())
        
        performance = {
            'total_processing_time': total_time,
            'components': [],
            'bottlenecks': [],
            'optimization_impact': {}  # Phase 3 addition
        }
        
        # Sort by time spent
        sorted_components = sorted(
            component_timings.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        for component, time_spent in sorted_components:
            percentage = (time_spent / total_time * 100) if total_time > 0 else 0
            
            comp_info = {
                'name': component,
                'time_seconds': time_spent,
                'percentage': percentage,
                'avg_ms_per_tick': (time_spent * 1000 / max(self.summary.get('ticks_received', 1), 1))
            }
            
            performance['components'].append(comp_info)
            
            # Mark as bottleneck if > 20% of processing time
            if percentage > 20:
                performance['bottlenecks'].append(comp_info)
        
        # Check for Phase 3 monitoring optimizations
        if 'monitoring_overhead' in self.summary:
            performance['optimization_impact']['monitoring_overhead_before'] = self.summary.get('monitoring_overhead_before', 'N/A')
            performance['optimization_impact']['monitoring_overhead_after'] = self.summary.get('monitoring_overhead', '<0.1%')
            performance['optimization_impact']['improvement'] = 'Achieved <0.1% overhead (Phase 3)'
        
        return performance
    
    def analyze_step_durations(self) -> Dict[str, Any]:
        """Analyze processing step durations with statistical enhancements."""
        step_durations = []
        component_durations = defaultdict(list)
        
        # Track slow operations
        slow_operations = []
        
        for step in self.steps:
            duration = step.get('duration_to_next_ms', 0)
            if duration > 0:
                step_durations.append(duration)
                component_durations[step['component']].append(duration)
                
                # Track slow operations (>100ms)
                if duration > 100:
                    slow_operations.append({
                        'component': step['component'],
                        'action': step['action'],
                        'duration_ms': duration,
                        'timestamp': step['timestamp']
                    })
        
        if not step_durations:
            return {'error': 'No duration data available'}
        
        analysis = {
            'overall': {
                'count': len(step_durations),
                'mean_ms': statistics.mean(step_durations),
                'median_ms': statistics.median(step_durations),
                'min_ms': min(step_durations),
                'max_ms': max(step_durations),
                'stdev_ms': statistics.stdev(step_durations) if len(step_durations) > 1 else 0,
                'p95_ms': self._calculate_percentile(step_durations, 95),
                'p99_ms': self._calculate_percentile(step_durations, 99)
            },
            'by_component': {},
            'slow_operations': slow_operations[:10]  # Top 10 slowest
        }
        
        # Analyze per component
        for component, durations in component_durations.items():
            if durations:
                analysis['by_component'][component] = {
                    'count': len(durations),
                    'mean_ms': statistics.mean(durations),
                    'median_ms': statistics.median(durations),
                    'max_ms': max(durations),
                    'p95_ms': self._calculate_percentile(durations, 95)
                }
        
        return analysis
    
    def _calculate_percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile value."""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    def find_errors(self) -> List[Dict[str, Any]]:
        """Find all errors in the trace."""
        errors = []
        
        for i, step in enumerate(self.steps):
            if step.get('error'):
                errors.append({
                    'step_index': i,
                    'timestamp': step['timestamp'],
                    'component': step['component'],
                    'action': step['action'],
                    'error': step['error']
                })
            
            # Check for error-related actions
            if 'error' in step.get('action', '').lower():
                errors.append({
                    'step_index': i,
                    'timestamp': step['timestamp'],
                    'component': step['component'],
                    'action': step['action'],
                    'data': step.get('data', {})
                })
        
        return errors
    
    def get_component_actions(self, component: str) -> List[Dict[str, Any]]:
        """Get all actions for a specific component."""
        actions = []
        
        for step in self.steps:
            if step['component'] == component:
                actions.append({
                    'timestamp': step['timestamp'],
                    'action': step['action'],
                    'data': step.get('data', {}),
                    'duration_ms': step.get('duration_to_next_ms', 0)
                })
        
        return actions
    
    def calculate_event_latency(self) -> Dict[str, Any]:
        """Calculate latency from event generation to emission."""
        # Track event lifecycle
        event_lifecycle = defaultdict(lambda: {'generated': None, 'emitted': None})
        
        for step in self.steps:
            action = step.get('action', '')
            
            # Track generation
            if 'event_created' in action or 'event_generated' in action:
                event_type = self._extract_event_type(step)
                if event_type:
                    event_lifecycle[event_type]['generated'] = step['timestamp']
            
            # Track emission
            elif 'event_emitted' in action:
                event_type = self._extract_event_type(step)
                if event_type:
                    event_lifecycle[event_type]['emitted'] = step['timestamp']
        
        # Calculate latencies
        latencies = {}
        for event_type, lifecycle in event_lifecycle.items():
            if lifecycle['generated'] and lifecycle['emitted']:
                latency = (lifecycle['emitted'] - lifecycle['generated']) * 1000  # ms
                latencies[event_type] = latency
        
        if latencies:
            return {
                'event_latencies_ms': latencies,
                'average_latency_ms': statistics.mean(latencies.values()),
                'max_latency_ms': max(latencies.values()),
                'min_latency_ms': min(latencies.values())
            }
        else:
            return {'message': 'No complete event lifecycles found'}
    
    def _extract_event_type(self, step: Dict) -> Optional[str]:
        """Extract event type from step data."""
        # Try to get from data
        data = step.get('data', {})
        if isinstance(data, dict):
            # Check nested structures
            actual_data = self._extract_actual_data(data)
            return actual_data.get('event_type') or actual_data.get('type')
        return None
    
    def generate_summary_report(self) -> str:
        """Generate a text summary report with Phase 2/3 enhancements."""
        lines = [
            f"=== Trace Analysis Report ===",
            f"Ticker: {self.ticker}",
            f"Trace ID: {self.trace_id}",
            f"Duration: {self.trace_data.get('duration_seconds', 0):.2f} seconds",
            f"Total Steps: {len(self.steps)}",
            f"Ticks Received: {self.summary.get('ticks_received', 0)}",
            f"Ticks/Second: {self.summary.get('ticks_per_second', 0):.2f}",
            "",
            "=== Event Flow Analysis ===",
        ]
        
        event_flow = self.analyze_event_flow()
        
        # Add user connection analysis (Phase 2)
        user_analysis = event_flow.get('user_connection_analysis', {})
        if user_analysis.get('first_user_time'):
            lines.extend([
                "",
                "=== User Connection Impact ===",
                f"First User Connected: {datetime.fromtimestamp(user_analysis['first_user_time']).strftime('%H:%M:%S')}",
                f"Events Before First User: {user_analysis.get('total_events_before_user', 0)}",
                f"Efficiency Impact: {user_analysis.get('impact_on_efficiency', 0):.1f}%"
            ])
        
        for event_type, stats in event_flow.items():
            if isinstance(stats, dict) and 'generated' in stats:
                lines.extend([
                    f"\n{event_type.upper()}:",
                    f"  Generated: {stats['generated']}",
                    f"  Filtered: {stats['filtered']} ({stats['filter_rate']:.1f}%)",
                    f"  Queued: {stats.get('queued', 0)} ({stats.get('queue_efficiency', 0):.1f}%)",
                    f"  Collected: {stats.get('collected', 0)} ({stats.get('collection_efficiency', 0):.1f}%)",
                    f"  Ready: {stats.get('ready_for_emission', 0)}",
                    f"  Emitted: {stats['emitted']}",
                    f"  Dropped: {stats['dropped']} ({stats['drop_rate']:.1f}%)",
                    f"  Raw Efficiency: {stats['efficiency']:.1f}%",
                    f"  Adjusted Efficiency: {stats.get('adjusted_efficiency', stats['efficiency']):.1f}%"
                ])
        
        lines.extend(["", "=== Performance Analysis ==="])
        performance = self.analyze_performance()
        
        for comp in performance['components']:
            lines.append(
                f"{comp['name']}: {comp['time_seconds']:.2f}s "
                f"({comp['percentage']:.1f}%) - "
                f"{comp['avg_ms_per_tick']:.2f}ms/tick"
            )
        
        if performance['bottlenecks']:
            lines.extend(["", "⚠️  BOTTLENECKS DETECTED:"])
            for bottleneck in performance['bottlenecks']:
                lines.append(
                    f"  - {bottleneck['name']} using {bottleneck['percentage']:.1f}% "
                    f"of processing time"
                )
        
        # Add Phase 3 optimization impact if available
        if 'optimization_impact' in performance and performance['optimization_impact']:
            lines.extend(["", "=== Phase 3 Optimization Impact ==="])
            for key, value in performance['optimization_impact'].items():
                lines.append(f"  {key}: {value}")
        
        errors = self.find_errors()
        if errors:
            lines.extend(["", f"=== ERRORS ({len(errors)}) ==="])
            for error in errors[:5]:  # Show first 5
                lines.append(
                    f"  - {error['component']}.{error['action']} "
                    f"at {error['timestamp']:.3f}"
                )
        
        return "\n".join(lines)
    
    def export_analysis(self, output_path: str):
        """Export complete analysis to JSON file."""
        analysis = {
            'trace_info': self.get_basic_info(),
            'event_flow': self.analyze_event_flow(),
            'performance': self.analyze_performance(),
            'step_durations': self.analyze_step_durations(),
            'errors': self.find_errors(),
            'latency': self.calculate_event_latency(),
            'analysis_timestamp': datetime.now().isoformat(),
            'phase_4_enhanced': True
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        
        print(f"Analysis exported to: {output_path}")


class ComponentAnalyzer:
    """Base class for component-specific analyzers."""
    
    def __init__(self, trace_analyzer: TraceAnalyzer):
        self.analyzer = trace_analyzer
        self.component_name = self.__class__.__name__.replace('Analyzer', '')
        
    def get_component_steps(self) -> List[Dict[str, Any]]:
        """Get all steps for this component."""
        return self.analyzer.get_component_actions(self.component_name)
    
    def analyze(self) -> Dict[str, Any]:
        """Perform component-specific analysis. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement analyze()")