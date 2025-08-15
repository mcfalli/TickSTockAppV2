#!/usr/bin/env python3
"""
Consolidated Trace Diagnostics Tool
Deep diagnostic capabilities for identifying and resolving trace issues.
Combines emission analysis and cross-system correlation.
"""

import json
import sys
import os
from collections import defaultdict, Counter
from datetime import datetime
from typing import Dict, List, Set, Tuple, Optional, Any
import statistics

class TraceDiagnostics:
    """Advanced trace diagnostics and troubleshooting"""
    
    def __init__(self):
        self.reset()
        
    def reset(self):
        """Reset diagnostic state"""
        self.events_by_id = defaultdict(list)
        self.events_by_ticker = defaultdict(list)
        self.emission_pipeline = defaultdict(list)
        self.stage_metrics = defaultdict(lambda: defaultdict(int))
        self.timing_data = defaultdict(list)
        self.anomalies = []
        self.universe_data = defaultdict(list)
        
    def diagnose_files(self, *filenames):
        """Run diagnostics on multiple trace files"""
        print(f"[TEST] TRACE DIAGNOSTICS")
        print(f"{'='*80}")
        
        all_data = {}
        
        # Load all files
        for filename in filenames:
            try:
                data = self._load_trace_file(filename)
                all_data[filename] = data
                print(f"[OK] Loaded {filename}: {len(data.get('traces', []))} traces")
            except Exception as e:
                print(f"[X] Failed to load {filename}: {e}")
                
        if not all_data:
            print("No files loaded successfully")
            return
            
        # Run comprehensive diagnostics
        self._run_diagnostics(all_data)
        
    def _load_trace_file(self, filename: str) -> Dict:
        """Load trace file with path handling"""
        # If full path not provided, use default trace path
        if not os.path.isabs(filename) and not os.path.exists(filename):
            trace_path = getattr(self, 'trace_path', './logs/trace/')
            filename = os.path.join(trace_path, filename)
        
        if not os.path.exists(filename):
            raise FileNotFoundError(f"Trace file not found: {filename}")
            
        with open(filename, 'r') as f:
            data = json.load(f)
            
        # Handle different formats
        if isinstance(data, dict) and 'steps' in data:
            return {
                'filename': filename,
                'trace_id': data.get('trace_id', 'unknown'),
                'duration': data.get('duration_seconds', 0),
                'traces': data['steps']
            }
        elif isinstance(data, list):
            return {
                'filename': filename,
                'trace_id': 'unknown',
                'duration': 0,
                'traces': data
            }
        else:
            return {
                'filename': filename,
                'trace_id': 'unknown',
                'duration': 0,
                'traces': []
            }
    
    def _run_diagnostics(self, all_data: Dict[str, Dict]):
        """Run comprehensive diagnostics"""
        # Process all traces
        print(f"\n{'='*80}")
        print("[CHART] Processing traces...")
        
        for filename, data in all_data.items():
            self._process_file_traces(data['traces'], filename)
            
        # Run diagnostic modules
        self._diagnose_emission_pipeline()
        self._diagnose_event_loss()
        self._diagnose_timing_issues()
        self._diagnose_universe_filtering()
        self._diagnose_cross_system_correlation()
        self._identify_anomalies()
        
        # Generate recommendations
        self._generate_recommendations()
        
    def _process_file_traces(self, traces: List[dict], source: str):
        """Process traces from a file"""
        for trace in traces:
            ticker = trace.get('ticker', 'UNKNOWN')
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
            
            # Create trace record
            trace_record = {
                'source': source,
                'timestamp': trace.get('timestamp', 0),
                'ticker': ticker,
                'component': trace.get('component', ''),
                'action': action,
                'details': details,
                'data': data
            }
            
            # Store by various keys
            if event_id and event_id != 'None':
                self.events_by_id[event_id].append(trace_record)
                
            self.events_by_ticker[ticker].append(trace_record)
            
            # Track emission pipeline
            if action in ['emission_start', 'emission_complete', 
                         'user_filtering_start', 'user_filtering_complete',
                         'event_ready_for_emission']:
                self.emission_pipeline[action].append(trace_record)
                
            # Track universe data
            if 'universe' in action.lower() or 'universe' in str(details):
                self.universe_data[action].append(trace_record)
                
            # Collect timing data
            if 'duration_ms' in data:
                duration = data['duration_ms']
                # Convert string to float if needed
                try:
                    duration = float(duration)
                    self.timing_data[f"{trace['component']}.{action}"].append(duration)
                except (ValueError, TypeError):
                    pass  # Skip invalid duration values
                
            # Update stage metrics
            self._update_stage_metrics(action, details)
    
    def _update_stage_metrics(self, action: str, details: dict):
        """Update stage-based metrics"""
        if action == 'event_detected':
            if 'event_breakdown' in details:
                for event_type, count in details['event_breakdown'].items():
                    # Handle string counts
                    count = int(count) if isinstance(count, str) else count
                    self.stage_metrics['detected'][event_type] += count
            else:
                event_type = details.get('event_type', 'unknown')
                self.stage_metrics['detected'][event_type] += 1
                
        elif action == 'event_queued':
            event_type = details.get('event_type', 'unknown')
            self.stage_metrics['queued'][event_type] += 1
            
        elif action == 'events_collected':
            # Handle batch collection
            total = details.get('total', 0)
            event_breakdown = details.get('event_breakdown', {})
            
            for event_type, count in event_breakdown.items():
                # Handle string counts
                count = int(count) if isinstance(count, str) else count
                self.stage_metrics['collected'][event_type] += count
                
        elif action == 'event_emitted':
            event_type = details.get('event_type', 'unknown')
            self.stage_metrics['emitted'][event_type] += 1
    
    def _diagnose_emission_pipeline(self):
        """Diagnose emission pipeline issues"""
        print(f"\n[SEARCH] EMISSION PIPELINE DIAGNOSTICS")
        print(f"{'-'*60}")
        
        # Check emission flow
        emission_starts = len(self.emission_pipeline.get('emission_start', []))
        emission_completes = len(self.emission_pipeline.get('emission_complete', []))
        
        print(f"Emission cycles started: {emission_starts}")
        print(f"Emission cycles completed: {emission_completes}")
        
        if emission_starts != emission_completes:
            self.anomalies.append({
                'type': 'emission_mismatch',
                'severity': 'high',
                'details': f"Started {emission_starts} but completed {emission_completes}"
            })
            
        # Analyze filtering impact
        filter_starts = self.emission_pipeline.get('user_filtering_start', [])
        filter_completes = self.emission_pipeline.get('user_filtering_complete', [])
        
        if filter_completes:
            total_filtered = 0
            total_original = 0
            
            for trace in filter_completes[:10]:  # Sample first 10
                details = trace['details']
                original = details.get('original_counts', {})
                filtered = details.get('filtered_counts', {})
                
                # Sum all event types
                for event_type in ['highs', 'lows', 'trends', 'surges']:
                    # Handle string counts
                    orig_val = original.get(event_type, 0)
                    filt_val = filtered.get(event_type, 0)
                    
                    # Convert strings to int
                    orig_val = int(orig_val) if isinstance(orig_val, str) else orig_val
                    filt_val = int(filt_val) if isinstance(filt_val, str) else filt_val
                    
                    total_original += orig_val
                    total_filtered += filt_val
                    
            if total_original > 0:
                filter_efficiency = (total_filtered / total_original) * 100
                print(f"\nFiltering efficiency: {filter_efficiency:.1f}%")
                print(f"  Original events: {total_original}")
                print(f"  After filtering: {total_filtered}")
                print(f"  Dropped: {total_original - total_filtered}")
                
                if filter_efficiency < 50:
                    self.anomalies.append({
                        'type': 'aggressive_filtering',
                        'severity': 'medium',
                        'details': f"Only {filter_efficiency:.1f}% of events pass filtering"
                    })
        
        # Check ready vs emitted
        ready_events = self.emission_pipeline.get('event_ready_for_emission', [])
        print(f"\nEvents marked ready for emission: {len(ready_events)}")
        
        if ready_events:
            # Count by type
            ready_by_type = defaultdict(int)
            for trace in ready_events:
                event_type = trace['details'].get('event_type', 'unknown')
                ready_by_type[event_type] += 1
                
            print("Ready events by type:")
            for event_type, count in sorted(ready_by_type.items()):
                emitted = self.stage_metrics['emitted'].get(event_type, 0)
                efficiency = (emitted / count * 100) if count > 0 else 0
                status = "[OK]" if efficiency >= 90 else "[X]"
                print(f"  {status} {event_type}: {count} ready, {emitted} emitted ({efficiency:.1f}%)")
    
    def _diagnose_event_loss(self):
        """Diagnose where events are being lost"""
        print(f"\n[SEARCH] EVENT LOSS DIAGNOSTICS")
        print(f"{'-'*60}")
        
        # Calculate stage-to-stage loss
        stages = ['detected', 'queued', 'emitted']
        
        print("Event flow by type:")
        print(f"{'Type':<10} {'Detected':>10} {'Queued':>10} {'Emitted':>10} {'Loss':>10}")
        print(f"{'-'*50}")
        
        all_types = set()
        for stage_data in self.stage_metrics.values():
            all_types.update(stage_data.keys())
            
        total_loss = 0
        
        for event_type in sorted(all_types):
            detected = self.stage_metrics['detected'].get(event_type, 0)
            queued = self.stage_metrics['queued'].get(event_type, 0)
            emitted = self.stage_metrics['emitted'].get(event_type, 0)
            
            loss = detected - emitted
            total_loss += loss
            
            status = "[OK]" if loss == 0 else "[!]" if loss < detected * 0.1 else "[X]"
            
            print(f"{event_type:<10} {detected:>10} {queued:>10} {emitted:>10} "
                  f"{status} {loss:>6} ({loss/detected*100 if detected > 0 else 0:.1f}%)")
                  
        # Find specific lost events
        print(f"\nTotal events lost: {total_loss}")
        
        # Trace specific lost events
        lost_events = []
        
        for event_id, traces in self.events_by_id.items():
            stages_hit = set(t['action'] for t in traces)
            
            if 'event_detected' in stages_hit and 'event_emitted' not in stages_hit:
                # Find last stage
                last_stage = None
                last_timestamp = 0
                
                for trace in traces:
                    if trace['timestamp'] > last_timestamp:
                        last_timestamp = trace['timestamp']
                        last_stage = trace['action']
                        
                lost_events.append({
                    'event_id': event_id,
                    'last_stage': last_stage,
                    'ticker': traces[0]['ticker'],
                    'event_type': traces[0]['details'].get('event_type', 'unknown')
                })
                
        if lost_events:
            print(f"\nSample of lost events (showing first 10):")
            for event in lost_events[:10]:
                print(f"  - {event['event_id']} ({event['event_type']}) "
                      f"last seen at: {event['last_stage']}")
                      
            # Group by last stage
            lost_by_stage = Counter(e['last_stage'] for e in lost_events)
            print(f"\nLost events by last stage:")
            for stage, count in lost_by_stage.most_common():
                print(f"  - {stage}: {count} events")
    
    def _diagnose_timing_issues(self):
        """Diagnose performance and timing issues"""
        print(f"\n[TIME]  TIMING DIAGNOSTICS")
        print(f"{'-'*60}")
        
        if not self.timing_data:
            print("No timing data available")
            return
            
        # Analyze operation timings
        slow_operations = []
        
        for operation, timings in self.timing_data.items():
            if timings:
                avg_time = statistics.mean(timings)
                max_time = max(timings)
                p95_time = sorted(timings)[int(len(timings) * 0.95)]
                
                print(f"\n{operation}:")
                print(f"  Average: {avg_time:.1f}ms")
                print(f"  Max: {max_time:.1f}ms")
                print(f"  95th percentile: {p95_time:.1f}ms")
                
                if avg_time > 50:
                    slow_operations.append({
                        'operation': operation,
                        'avg_ms': avg_time,
                        'impact': 'high' if avg_time > 100 else 'medium'
                    })
                    
        if slow_operations:
            self.anomalies.append({
                'type': 'slow_operations',
                'severity': 'medium',
                'details': f"Found {len(slow_operations)} slow operations",
                'operations': slow_operations
            })
            
        # Check for timing gaps in event flow
        print(f"\n[CHART] Event Flow Timing:")
        
        sample_events = list(self.events_by_id.items())[:10]
        
        for event_id, traces in sample_events[:3]:  # Show first 3
            if len(traces) > 1:
                # Sort by timestamp
                sorted_traces = sorted(traces, key=lambda t: t['timestamp'])
                
                print(f"\nEvent {event_id}:")
                
                prev_time = sorted_traces[0]['timestamp']
                
                for trace in sorted_traces:
                    time_gap = trace['timestamp'] - prev_time
                    print(f"  {trace['timestamp']:.3f} (+{time_gap:.3f}s): "
                          f"{trace['action']}")
                    prev_time = trace['timestamp']
                    
                total_time = sorted_traces[-1]['timestamp'] - sorted_traces[0]['timestamp']
                print(f"  Total processing time: {total_time:.3f}s")
                
                if total_time > 5.0:
                    self.anomalies.append({
                        'type': 'slow_event_processing',
                        'severity': 'low',
                        'details': f"Event {event_id} took {total_time:.1f}s to process"
                    })
    
    def _diagnose_universe_filtering(self):
        """Diagnose universe filtering issues"""
        print(f"\n[WORLD] UNIVERSE FILTERING DIAGNOSTICS")
        print(f"{'-'*60}")
        
        if not self.universe_data:
            print("No universe data found")
            return
            
        # Analyze universe checks
        universe_checks = defaultdict(int)
        nvda_found_count = 0
        
        for action, traces in self.universe_data.items():
            print(f"\n{action}: {len(traces)} occurrences")
            
            for trace in traces[:5]:  # Sample
                details = trace['details']
                universe_name = details.get('universe_name', 'unknown')
                universe_checks[universe_name] += 1
                
                # Check NVDA presence
                if 'nvda' in str(details).lower() or trace['ticker'] == 'NVDA':
                    if details.get('nvda_included') or details.get('found'):
                        nvda_found_count += 1
                        
        print(f"\nUniverse check summary:")
        for universe, count in sorted(universe_checks.items()):
            print(f"  - {universe}: {count} checks")
            
        print(f"\nNVDA found in universe: {nvda_found_count} times")
        
        if nvda_found_count == 0:
            self.anomalies.append({
                'type': 'universe_filtering_issue',
                'severity': 'high',
                'details': 'NVDA not found in any universe checks'
            })
    
    def _diagnose_cross_system_correlation(self):
        """Correlate traces across system components"""
        print(f"\n[SYNC] CROSS-SYSTEM CORRELATION")
        print(f"{'-'*60}")
        
        # Find events that appear in multiple files
        events_by_source = defaultdict(set)
        
        for event_id, traces in self.events_by_id.items():
            sources = set(t['source'] for t in traces)
            if len(sources) > 1:
                events_by_source[tuple(sorted(sources))].add(event_id)
                
        if events_by_source:
            print("Events appearing in multiple trace files:")
            for sources, events in events_by_source.items():
                print(f"\n{' + '.join(sources)}: {len(events)} shared events")
                
        # Component interaction analysis
        component_interactions = defaultdict(lambda: defaultdict(int))
        
        for event_id, traces in self.events_by_id.items():
            if len(traces) > 1:
                sorted_traces = sorted(traces, key=lambda t: t['timestamp'])
                
                for i in range(len(sorted_traces) - 1):
                    from_comp = sorted_traces[i]['component']
                    to_comp = sorted_traces[i + 1]['component']
                    component_interactions[from_comp][to_comp] += 1
                    
        if component_interactions:
            print("\nComponent interaction patterns:")
            for from_comp, destinations in sorted(component_interactions.items()):
                print(f"\n{from_comp} ->")
                for to_comp, count in sorted(destinations.items(), 
                                           key=lambda x: x[1], reverse=True):
                    print(f"  -> {to_comp}: {count} transitions")
    
    def _identify_anomalies(self):
        """Identify and categorize anomalies"""
        print(f"\n[ALERT] ANOMALY DETECTION")
        print(f"{'-'*60}")
        
        # Check for missing critical traces
        critical_actions = [
            'event_detected', 'event_queued', 'event_emitted',
            'event_ready_for_emission'
        ]
        
        all_actions = set()
        for traces in self.events_by_ticker.values():
            all_actions.update(t['action'] for t in traces)
            
        missing_critical = set(critical_actions) - all_actions
        
        if missing_critical:
            self.anomalies.append({
                'type': 'missing_critical_traces',
                'severity': 'critical',
                'details': f"Missing traces: {missing_critical}"
            })
            
        # Check for string/int inconsistencies
        string_count_issues = 0
        
        for traces in self.events_by_ticker.values():
            for trace in traces:
                data = trace.get('data', {})
                if isinstance(data, dict):
                    for key, value in data.items():
                        if key.endswith('_count') and isinstance(value, str):
                            string_count_issues += 1
                            
        if string_count_issues > 0:
            self.anomalies.append({
                'type': 'type_inconsistency',
                'severity': 'medium',
                'details': f'Found {string_count_issues} string count values'
            })
            
        # Print all anomalies
        if self.anomalies:
            print(f"Found {len(self.anomalies)} anomalies:")
            
            # Group by severity
            by_severity = defaultdict(list)
            for anomaly in self.anomalies:
                by_severity[anomaly['severity']].append(anomaly)
                
            for severity in ['critical', 'high', 'medium', 'low']:
                if severity in by_severity:
                    print(f"\n{severity.upper()} severity:")
                    for anomaly in by_severity[severity]:
                        print(f"  - {anomaly['type']}: {anomaly['details']}")
        else:
            print("[OK] No significant anomalies detected")
    
    def _generate_recommendations(self):
        """Generate actionable recommendations"""
        print(f"\n[TIP] RECOMMENDATIONS")
        print(f"{'-'*60}")
        
        recommendations = []
        
        # Based on anomalies
        for anomaly in self.anomalies:
            if anomaly['type'] == 'emission_mismatch':
                recommendations.append({
                    'priority': 'HIGH',
                    'action': 'Investigate incomplete emission cycles',
                    'details': 'Check for errors in WebSocketPublisher'
                })
            elif anomaly['type'] == 'aggressive_filtering':
                recommendations.append({
                    'priority': 'MEDIUM',
                    'action': 'Review user filtering logic',
                    'details': 'Current filtering may be too restrictive'
                })
            elif anomaly['type'] == 'universe_filtering_issue':
                recommendations.append({
                    'priority': 'HIGH',
                    'action': 'Verify universe configuration',
                    'details': 'Ensure NVDA is properly included in universes'
                })
            elif anomaly['type'] == 'missing_critical_traces':
                recommendations.append({
                    'priority': 'CRITICAL',
                    'action': 'Add missing trace points',
                    'details': f"Missing: {anomaly['details']}"
                })
                
        # Based on metrics
        total_detected = sum(self.stage_metrics['detected'].values())
        total_emitted = sum(self.stage_metrics['emitted'].values())
        
        if total_detected > 0:
            overall_efficiency = (total_emitted / total_detected) * 100
            
            if overall_efficiency < 85:
                recommendations.append({
                    'priority': 'HIGH',
                    'action': 'Improve event pipeline efficiency',
                    'details': f'Current efficiency: {overall_efficiency:.1f}%'
                })
                
        # Based on timing
        if any(avg > 100 for op, timings in self.timing_data.items() 
               for avg in [statistics.mean(timings)] if timings):
            recommendations.append({
                'priority': 'MEDIUM',
                'action': 'Optimize slow operations',
                'details': 'Multiple operations exceed 100ms average'
            })
            
        # Print recommendations
        if recommendations:
            # Sort by priority
            priority_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
            recommendations.sort(key=lambda r: priority_order.get(r['priority'], 999))
            
            for rec in recommendations:
                print(f"\n[{rec['priority']}] {rec['action']}")
                print(f"  Details: {rec['details']}")
        else:
            print("\n[OK] No critical issues found - system appears healthy")
            
        # Always include general recommendations
        print(f"\n[LIST] General Recommendations:")
        print("  1. Run diagnostics regularly to catch issues early")
        print("  2. Monitor event_ready_for_emission traces closely")
        print("  3. Ensure all count fields use integers, not strings")
        print("  4. Verify universe filtering for all tracked tickers")

def main():
    """Main entry point with standardized argument handling"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Deep diagnostic analysis of trace files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s                           # Use default trace_all.json
  %(prog)s NVDA.json                 # Analyze specific file
  %(prog)s NVDA.json SYSTEM.json     # Multiple files
  %(prog)s *.json /custom/path/      # All JSON files in custom path
        '''
    )
    
    parser.add_argument('filenames', nargs='*', default=['trace_all.json'],
                       help='Trace filenames with .json extension (default: trace_all.json)')
    parser.add_argument('--path', dest='trace_path', default='./logs/trace/',
                       help='Path to trace directory (default: ./logs/trace/)')
    
    args = parser.parse_args()
    
    # Update filenames to include path
    full_paths = [os.path.join(args.trace_path, f) for f in args.filenames]
    
    # Run diagnostics
    diagnostics = TraceDiagnostics()
    diagnostics.trace_path = args.trace_path
    diagnostics.diagnose_files(*full_paths)

if __name__ == "__main__":
    main()