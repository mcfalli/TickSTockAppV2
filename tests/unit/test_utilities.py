#!/usr/bin/env python3
"""
Enhanced Test Utilities for Trace Analysis
Provides shared functionality for all trace testing scripts.
"""

import json
import os
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum

class TraceStage(Enum):
    """Standardized trace stages"""
    TICK_CREATED = "tick_created"
    TICK_RECEIVED = "tick_received"
    TICK_DELEGATED = "tick_delegated"
    EVENT_DETECTED = "event_detected"
    EVENT_QUEUED = "event_queued"
    EVENTS_COLLECTED = "events_collected"
    EVENT_READY_FOR_EMISSION = "event_ready_for_emission"
    EVENT_EMITTED = "event_emitted"

class EventType(Enum):
    """Standardized event types"""
    HIGH = "high"
    LOW = "low"
    SURGE = "surge"
    TREND = "trend"
    UNKNOWN = "unknown"

@dataclass
class TraceValidationResult:
    """Result of trace validation"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    metrics: Dict[str, Any]

@dataclass
class FlowAnalysisResult:
    """Result of flow analysis"""
    total_events: int
    complete_flows: int
    incomplete_flows: int
    efficiency: float
    lost_events: List[str]
    bottlenecks: List[Dict[str, Any]]

class TraceAnalyzer:
    """Enhanced trace analysis utilities"""
    
    EXPECTED_FLOW = [
        TraceStage.EVENT_DETECTED,
        TraceStage.EVENT_QUEUED,
        TraceStage.EVENTS_COLLECTED,
        TraceStage.EVENT_READY_FOR_EMISSION,
        TraceStage.EVENT_EMITTED
    ]
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset analyzer state"""
        self.events_by_id = defaultdict(list)
        self.stage_counts = defaultdict(int)
        self.type_counts = defaultdict(lambda: defaultdict(int))
        self.validation_errors = []
        self.validation_warnings = []
    
    def load_trace_file(self, filename: str) -> Dict[str, Any]:
        """Load and parse trace file with error handling"""
        # Handle path resolution
        if not os.path.dirname(filename):
            filename = os.path.join('./logs/trace/', filename)
        
        if not os.path.exists(filename):
            raise FileNotFoundError(f"Trace file not found: {filename}")
        
        with open(filename, 'r') as f:
            data = json.load(f)
        
        # Handle different formats
        if isinstance(data, dict) and 'steps' in data:
            return {
                'trace_id': data.get('trace_id', 'unknown'),
                'duration': data.get('duration_seconds', 0),
                'traces': data['steps']
            }
        elif isinstance(data, list):
            return {
                'trace_id': 'unknown',
                'duration': 0,
                'traces': data
            }
        else:
            raise ValueError("Unknown trace format")
    
    def extract_connection_timing(self, trace_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract user connection timing information"""
        traces = trace_data.get('traces', [])
        connections = []
        
        for trace in traces:
            action = trace.get('action', '')
            if action in ['user_connected', 'user_authenticated', 'client_connected']:
                connections.append({
                    'timestamp': trace.get('timestamp', 0),
                    'action': action,
                    'user_id': trace.get('data', {}).get('details', {}).get('user_id'),
                    'component': trace.get('component', '')
                })
        
        # Sort by timestamp
        connections.sort(key=lambda x: x['timestamp'])
        
        # Find first authenticated user
        first_auth_time = None
        first_user_id = None
        for conn in connections:
            if conn['action'] in ['user_authenticated', 'user_connected'] and conn.get('user_id'):
                first_auth_time = conn['timestamp']
                first_user_id = conn['user_id']
                break
        
        return {
            'connections': connections,
            'first_auth_time': first_auth_time,
            'first_user_id': first_user_id,
            'total_connections': len(connections)
        }

    def calculate_adjusted_efficiency(self, trace_data: Dict[str, Any], ticker: str = None) -> Dict[str, float]:
        """Calculate efficiency adjusted for user connection timing"""
        connection_info = self.extract_connection_timing(trace_data)
        first_user_time = connection_info['first_auth_time']
        
        if not first_user_time:
            # No user connection found, return raw efficiency
            flow = self.extract_flow_metrics(trace_data, ticker)
            return {
                'raw_efficiency': flow.efficiency,
                'adjusted_efficiency': flow.efficiency,
                'events_before_user': 0,
                'warning': 'No user connections found'
            }
        
        # Count events before and after user connection
        self.reset()
        traces = trace_data.get('traces', [])
        
        events_before = 0
        events_after = 0
        
        for trace in traces:
            if ticker and trace.get('ticker') != ticker:
                continue
                
            if trace.get('action') == 'event_detected':
                if trace.get('timestamp', 0) < first_user_time:
                    events_before += 1
                else:
                    events_after += 1
        
        # Get emission counts
        emitted = sum(1 for trace in traces 
                    if trace.get('action') == 'event_emitted' and 
                    (not ticker or trace.get('ticker') == ticker))
        
        raw_efficiency = (emitted / (events_before + events_after) * 100) if (events_before + events_after) > 0 else 0
        adjusted_efficiency = (emitted / events_after * 100) if events_after > 0 else 0
        
        return {
            'raw_efficiency': raw_efficiency,
            'adjusted_efficiency': adjusted_efficiency,
            'events_before_user': events_before,
            'events_after_user': events_after,
            'events_emitted': emitted,
            'first_user_time': first_user_time
        }

    def validate_json_structure(self, trace_data: Dict[str, Any]) -> TraceValidationResult:
        """Validate JSON meets expected schema"""
        errors = []
        warnings = []
        metrics = {}
        
        traces = trace_data.get('traces', [])
        metrics['total_traces'] = len(traces)
        
        # Check required fields
        required_fields = ['timestamp', 'ticker', 'component', 'action']
        optional_fields = ['data', 'category']
        
        for i, trace in enumerate(traces):
            # Check required fields
            for field in required_fields:
                if field not in trace:
                    errors.append(f"Trace {i}: Missing required field '{field}'")
            
            # Validate timestamp
            if 'timestamp' in trace:
                try:
                    ts = float(trace['timestamp'])
                    if ts <= 0:
                        warnings.append(f"Trace {i}: Invalid timestamp {ts}")
                except:
                    errors.append(f"Trace {i}: Timestamp not a number")
            
            # Validate data field
            if 'data' in trace:
                data = trace['data']
                if isinstance(data, str):
                    warnings.append(f"Trace {i}: Data field is string, should be dict")
                elif isinstance(data, dict):
                    # Check for string/int conversion issues
                    if 'output_count' in data:
                        try:
                            int(data['output_count'])
                        except:
                            warnings.append(f"Trace {i}: output_count not convertible to int")
        
        # Check for trace continuity
        if traces:
            timestamps = [t.get('timestamp', 0) for t in traces]
            if timestamps != sorted(timestamps):
                warnings.append("Traces not in chronological order")
        
        is_valid = len(errors) == 0
        return TraceValidationResult(is_valid, errors, warnings, metrics)
    
    def extract_flow_metrics(self, trace_data: Dict[str, Any], ticker: str = None) -> FlowAnalysisResult:
        """Extract key performance indicators from trace data"""
        self.reset()
        traces = trace_data.get('traces', [])
        
        # Process all traces
        for trace in traces:
            if ticker and trace.get('ticker') != ticker:
                continue
            self._process_trace(trace)
        
        # Calculate metrics
        detected = len(self.events_by_id)
        emitted = sum(1 for events in self.events_by_id.values() 
                     if any(e['action'] == TraceStage.EVENT_EMITTED.value for e in events))
        
        efficiency = (emitted / detected * 100) if detected > 0 else 0
        
        # Find incomplete flows
        incomplete = []
        lost = []
        for event_id, events in self.events_by_id.items():
            stages = set(e['action'] for e in events)
            expected = set(s.value for s in self.EXPECTED_FLOW)
            
            if not stages.issuperset({TraceStage.EVENT_DETECTED.value, 
                                     TraceStage.EVENT_QUEUED.value, 
                                     TraceStage.EVENT_EMITTED.value}):
                incomplete.append(event_id)
                
                if TraceStage.EVENT_EMITTED.value not in stages:
                    lost.append(event_id)
        
        # Identify bottlenecks
        bottlenecks = self._identify_bottlenecks()
        
        return FlowAnalysisResult(
            total_events=detected,
            complete_flows=detected - len(incomplete),
            incomplete_flows=len(incomplete),
            efficiency=efficiency,
            lost_events=lost,
            bottlenecks=bottlenecks
        )
    
    def _process_trace(self, trace: dict):
        """Process individual trace entry"""
        action = trace.get('action', '')
        data = trace.get('data', {})
        
        # Handle string data
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except:
                data = {}
        
        details = data.get('details', {})
        event_id = details.get('event_id') or data.get('event_id')
        
        if event_id and event_id != 'None':
            self.events_by_id[event_id].append({
                'timestamp': trace.get('timestamp', 0),
                'ticker': trace.get('ticker', ''),
                'component': trace.get('component', ''),
                'action': action,
                'details': details
            })
        
        # Count stages
        self.stage_counts[action] += 1
        
        # Count by type
        event_type = details.get('event_type', 'unknown')
        self.type_counts[action][event_type] += 1
    
    def _identify_bottlenecks(self) -> List[Dict[str, Any]]:
        """Identify performance bottlenecks"""
        bottlenecks = []
        
        # Check stage transitions
        transitions = [
            ('event_detected', 'event_queued'),
            ('event_queued', 'events_collected'),
            ('events_collected', 'event_emitted')
        ]
        
        for from_stage, to_stage in transitions:
            from_count = self.stage_counts.get(from_stage, 0)
            to_count = self.stage_counts.get(to_stage, 0)
            
            if from_count > 0:
                efficiency = (to_count / from_count) * 100
                if efficiency < 90:  # Threshold for bottleneck
                    bottlenecks.append({
                        'stage': f"{from_stage} → {to_stage}",
                        'efficiency': efficiency,
                        'lost': from_count - to_count,
                        'severity': 'high' if efficiency < 80 else 'medium'
                    })
        
        return bottlenecks
    
    def generate_summary_report(self, trace_data: Dict[str, Any], ticker: str = None) -> str:
        """Create concise analysis report"""
        validation = self.validate_json_structure(trace_data)
        flow = self.extract_flow_metrics(trace_data, ticker)
        
        report = []
        report.append("📊 TRACE ANALYSIS REPORT")
        report.append("=" * 60)
        
        # Validation section
        report.append(f"\n✅ Validation: {'PASSED' if validation.is_valid else 'FAILED'}")
        if validation.errors:
            report.append(f"   Errors: {len(validation.errors)}")
            for error in validation.errors[:3]:
                report.append(f"   - {error}")
        if validation.warnings:
            report.append(f"   Warnings: {len(validation.warnings)}")
            for warning in validation.warnings[:3]:
                report.append(f"   - {warning}")
        
        # Flow analysis section
        report.append(f"\n📈 Flow Analysis:")
        report.append(f"   Total Events: {flow.total_events}")
        report.append(f"   Complete Flows: {flow.complete_flows}")
        report.append(f"   Efficiency: {flow.efficiency:.1f}%")
        
        if flow.bottlenecks:
            report.append(f"\n⚠️  Bottlenecks Found:")
            for bottleneck in flow.bottlenecks:
                report.append(f"   - {bottleneck['stage']}: {bottleneck['efficiency']:.1f}% "
                            f"({bottleneck['severity']} severity)")
        
        if flow.lost_events:
            report.append(f"\n❌ Lost Events: {len(flow.lost_events)}")
            for event_id in flow.lost_events[:5]:
                report.append(f"   - {event_id}")
        
        return "\n".join(report)
    
    def detect_anomalies(self, trace_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify unusual patterns or issues"""
        anomalies = []
        traces = trace_data.get('traces', [])
        
        # Check for string/integer inconsistencies
        string_counts = 0
        for trace in traces:
            data = trace.get('data', {})
            if isinstance(data, dict):
                for key, value in data.items():
                    if key.endswith('_count') and isinstance(value, str):
                        string_counts += 1
        
        if string_counts > 0:
            anomalies.append({
                'type': 'type_inconsistency',
                'severity': 'medium',
                'description': f'Found {string_counts} count fields as strings instead of integers',
                'impact': 'May cause calculation errors'
            })
        
        # Check for missing emission traces
        if 'event_ready_for_emission' not in self.stage_counts:
            anomalies.append({
                'type': 'missing_trace',
                'severity': 'high',
                'description': 'No "event_ready_for_emission" traces found',
                'impact': 'Cannot track emission pipeline'
            })
        
        # Check for event type imbalance
        for event_type in ['high', 'low', 'surge', 'trend']:
            detected = self.type_counts.get('event_detected', {}).get(event_type, 0)
            emitted = self.type_counts.get('event_emitted', {}).get(event_type, 0)
            
            if detected > 0 and emitted == 0:
                anomalies.append({
                    'type': 'event_type_loss',
                    'severity': 'high',
                    'description': f'All {event_type} events lost (detected: {detected}, emitted: 0)',
                    'impact': f'No {event_type} events reaching users'
                })
        
        return anomalies

# Convenience functions
def validate_trace_file(filename: str) -> TraceValidationResult:
    """Quick validation of a trace file"""
    analyzer = TraceAnalyzer()
    trace_data = analyzer.load_trace_file(filename)
    return analyzer.validate_json_structure(trace_data)

def analyze_trace_flow(filename: str, ticker: str = None) -> FlowAnalysisResult:
    """Quick flow analysis of a trace file"""
    analyzer = TraceAnalyzer()
    trace_data = analyzer.load_trace_file(filename)
    return analyzer.extract_flow_metrics(trace_data, ticker)

def generate_trace_report(filename: str, ticker: str = None) -> str:
    """Generate a complete trace report"""
    analyzer = TraceAnalyzer()
    trace_data = analyzer.load_trace_file(filename)
    return analyzer.generate_summary_report(trace_data, ticker)

# Test result helpers
def print_test_header(test_name: str):
    """Print a formatted test header"""
    print(f"\n{'='*60}")
    print(f"🧪 {test_name}")
    print(f"{'='*60}")

def print_test_result(test_name: str, passed: bool, details: str = None):
    """Print test result in standard format"""
    status = "✅ PASSED" if passed else "❌ FAILED"
    print(f"{test_name}: {status}")
    if details:
        print(f"  Details: {details}")