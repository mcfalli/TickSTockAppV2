#!/usr/bin/env python3
"""
Consolidated Trace Flow Validation Script
Combines functionality from test_trace_analysis.py and test_trace_flow.py
Validates event flow integrity and calculates true efficiency metrics.
"""

import json
import sys
import os

# Add the parent directory (e.g., 'tests/') to sys.path
# This allows importing test_utilities directly when running from project root
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir) # Add the directory where test_trace_flow_validation.py resides

from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Set, Tuple, Optional

# This import should now work!
from test_utilities import TraceAnalyzer, TraceStage, EventType, generate_trace_report



class FlowValidator:
    def __init__(self):
        self.analyzer = TraceAnalyzer()
        self.events_by_id = defaultdict(list)
        self.stage_event_ids = defaultdict(set)
        self.event_types = defaultdict(lambda: defaultdict(set))
        self.universe_checks = []
        self.user_connections = []  # NEW: Track user connections
        self.trace_path = '' # <--- Add this line
        
    def validate_trace_file(self, filename: str, ticker: str = None):
        """Comprehensive flow validation of trace file"""
        print(f"[SEARCH] TRACE FLOW VALIDATION")
        print(f"{'='*80}")
        
        try:
            # Construct full path
            #full_path = os.path.join(getattr(self, 'trace_path', './logs/trace/'), filename)
            full_path = os.path.join(self.trace_path, filename)

            if not os.path.exists(full_path):
                print(f"[X] Error: File not found: {full_path}")
                sys.exit(1)
            
            # Load and validate structure
            trace_data = self.analyzer.load_trace_file(full_path)
            print(f"[FILE] File: {full_path}")
            print(f"[ID] Trace ID: {trace_data.get('trace_id', 'Unknown')}")
            print(f"[TIME] Duration: {trace_data.get('duration', 0):.2f} seconds")
            print(f"[CHART] Total traces: {len(trace_data.get('traces', []))}")
            
            # Validate JSON structure
            validation_result = self.analyzer.validate_json_structure(trace_data)
            self._print_validation_results(validation_result)
            
            # Process traces
            self._process_all_traces(trace_data.get('traces', []), ticker)
            
            # NEW: Check user connections
            self._analyze_user_connections()
            
            # Run analyses
            print(f"\n{'='*80}")
            self._analyze_event_flows(ticker)
            self._analyze_stage_transitions(ticker)
            self._analyze_true_efficiency(ticker)
            self._analyze_event_types()
            self._analyze_universe_filtering()
            
            # Generate summary
            print(f"\n{'='*80}")
            self._print_executive_summary(ticker)
            
        except Exception as e:
            print(f"[X] Error: {e}")
            import traceback
            traceback.print_exc()
    
    def _print_validation_results(self, result):
        """Print JSON validation results"""
        status = "[OK] PASSED" if result.is_valid else "[X] FAILED"
        print(f"\n[LIST] JSON Validation: {status}")
        
        if result.errors:
            print(f"   Errors ({len(result.errors)}):")
            for error in result.errors[:5]:
                print(f"   [X] {error}")
                
        if result.warnings:
            print(f"   Warnings ({len(result.warnings)}):")
            for warning in result.warnings[:5]:
                print(f"   [!] {warning}")
    
    def _process_all_traces(self, traces: List[dict], filter_ticker: str = None):
        """Process all trace entries"""
        for trace in traces:
            ticker = trace.get('ticker', '')
            action = trace.get('action', '')
            
            # ALWAYS process user-related traces regardless of ticker filter
            # These are typically on SYSTEM ticker
            user_actions = [
                'user_connected', 'user_authenticated', 'client_connected',
                'new_user_connection', 'user_ready_for_events', 'buffered_events_sent',
                'user_disconnected', 'user_emission', 'generic_client_registered',
                'generic_client_unregistered'
            ]
            
            if action in user_actions:
                self._process_trace_entry(trace)
                continue
            
            # For all other traces, apply ticker filter if specified
            if filter_ticker and ticker != filter_ticker:
                continue
                
            self._process_trace_entry(trace)

    def _process_trace_entry(self, trace: dict):
        """Process single trace entry"""
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
        
        # Track user connections - UPDATED to include actual actions from your system
        if action in ['user_connected', 'user_authenticated', 'client_connected', 
                    'new_user_connection', 'user_ready_for_events', 'buffered_events_sent',
                    'user_disconnected', 'user_emission', 'generic_client_registered', 
                    'generic_client_unregistered']:
            self.user_connections.append({
                'timestamp': trace.get('timestamp', 0),
                'action': action,
                'user_id': details.get('user_id'),
                'component': trace.get('component', ''),
                'details': details
            })
        
        # Handle events_collected specially - it's a batch operation
        if action == 'events_collected':
            total = details.get('total', 0)
            event_breakdown = details.get('event_breakdown', {})
            
            # Track batch collections
            if 'batch_collections' not in self.__dict__:
                self.batch_collections = defaultdict(lambda: {'count': 0, 'total_events': 0})
            
            # Store with the trace's ticker (could be SYSTEM or specific ticker)
            self.batch_collections[ticker]['count'] += 1
            self.batch_collections[ticker]['total_events'] += total
            
            # Also track events collected by type
            for event_type, count in event_breakdown.items():
                # Ensure count is int
                count = int(count) if isinstance(count, str) else count
                if event_type not in self.event_types[action]:
                    self.event_types[action][event_type] = set()
                # For batch operations, we track count rather than individual IDs
                self.event_types[action][event_type].add(f"batch_{ticker}_{len(self.event_types[action][event_type])}")
            
            return  # Don't process batch operations as individual events
        
        # Regular individual event processing
        if event_id and event_id != 'None':
            trace_info = {
                'timestamp': trace.get('timestamp', 0),
                'ticker': ticker,
                'component': trace.get('component', ''),
                'action': action,
                'event_type': details.get('event_type', 'unknown'),
                'details': details
            }
            
            self.events_by_id[event_id].append(trace_info)
            self.stage_event_ids[action].add(event_id)
            
            # Track by type
            event_type = self._normalize_event_type(details.get('event_type', 'unknown'))
            self.event_types[action][event_type].add(event_id)
        
        # Track universe checks
        if action in ['found_in_universe', 'universe_resolution_complete', 'universe_resolved']:
            self.universe_checks.append({
                'action': action,
                'ticker': ticker,
                'details': details,
                'timestamp': trace.get('timestamp', 0)
            })

    def _normalize_event_type(self, event_type: str) -> str:
        """Normalize event type strings"""
        if not event_type:
            return 'unknown'
        
        event_type = str(event_type).lower()
        
        # Map variations to standard types
        mappings = {
            'session_high': 'high',
            'session_low': 'low',
            '_low': 'low'
        }
        
        return mappings.get(event_type, event_type)
    
    def _analyze_event_flows(self, ticker: str = None):
        """Analyze individual event flows"""
        print(f"\n[CHART] EVENT FLOW ANALYSIS")
        print(f"{'-'*60}")
        
        # Filter events by ticker
        ticker_events = []
        for event_id, traces in self.events_by_id.items():
            if not ticker or any(t['ticker'] == ticker for t in traces):
                ticker_events.append((event_id, traces))
        
        if not ticker_events:
            print(f"No events found for {ticker or 'any ticker'}")
            return
        
        print(f"Analyzing {len(ticker_events)} unique events...")
        
        # Categorize flows
        complete_flows = 0
        incomplete_flows = defaultdict(list)
        
        for event_id, traces in ticker_events:
            stages = set(t['action'] for t in traces)
            
            # Check for complete flow
            required_stages = {'event_detected', 'event_queued', 'event_emitted'}
            if required_stages.issubset(stages):
                complete_flows += 1
            else:
                # Identify missing stages
                missing = required_stages - stages
                for stage in missing:
                    incomplete_flows[stage].append(event_id)
        
        # Print results
        total = len(ticker_events)
        complete_pct = (complete_flows / total * 100) if total > 0 else 0
        
        print(f"\n[OK] Complete flows: {complete_flows}/{total} ({complete_pct:.1f}%)")
        print(f"[X] Incomplete flows: {total - complete_flows}")
        
        if incomplete_flows:
            print(f"\nMissing stages breakdown:")
            for stage, events in sorted(incomplete_flows.items()):
                print(f"  - {stage}: {len(events)} events missing this stage")
                # Show sample event IDs
                for event_id in events[:3]:
                    print(f"    * {event_id}")
                if len(events) > 3:
                    print(f"    * ... and {len(events) - 3} more")
                    
    def _analyze_user_connections(self):
        """Analyze user connection timing"""
        if not self.user_connections:
            print(f"\n[!] NO USER CONNECTIONS FOUND - Events may be lost!")
            print(f"    Note: User connections are traced on SYSTEM ticker")
            return
        
        print(f"\n[USERS] USER CONNECTION ANALYSIS")
        print(f"{'-'*60}")
        
        # Sort by timestamp
        self.user_connections.sort(key=lambda x: x['timestamp'])
        
        # Find first connection
        first_conn = self.user_connections[0]
        self.first_user_time = first_conn['timestamp']  # Store for later use
        
        print(f"First user connected at: {self.first_user_time:.3f}")
        print(f"User ID: {first_conn.get('user_id', 'Unknown')}")
        print(f"Connection type: {first_conn['action']}")
        
        # Count events before user connection
        events_before_user = 0
        for event_id, traces in self.events_by_id.items():
            first_trace = min(traces, key=lambda t: t['timestamp'])
            if first_trace['timestamp'] < self.first_user_time:
                events_before_user += 1
        
        if events_before_user > 0:
            print(f"\n[!] {events_before_user} events detected before first user connection!")
            print(f"These events were lost due to no connected users.")
        
        # Show connection activity
        connection_types = defaultdict(int)
        for conn in self.user_connections:
            connection_types[conn['action']] += 1
        
        print(f"\nConnection activity:")
        for action, count in sorted(connection_types.items()):
            print(f"  - {action}: {count}")
    
    def _analyze_stage_transitions(self, ticker: str = None):
        """Analyze stage-to-stage transitions"""
        print(f"\n[CHART] STAGE TRANSITION ANALYSIS")
        print(f"{'-'*60}")
        
        # Count events at each stage
        stage_counts = defaultdict(int)
        type_counts = defaultdict(lambda: defaultdict(int))
        
        for action, event_ids in self.stage_event_ids.items():
            stage_counts[action] = len(event_ids)
            
            # Count by type
            for event_type, type_event_ids in self.event_types[action].items():
                type_counts[action][event_type] = len(type_event_ids)
        
        # Handle batch collections - CHECK SYSTEM TICKER TOO
        if hasattr(self, 'batch_collections'):
            # Include collections from filtered ticker AND SYSTEM
            total_collected = 0
            relevant_collections = {}
            
            for ticker_name, stats in self.batch_collections.items():
                # Include if no filter, matches filter, or is SYSTEM
                if not ticker or ticker_name == ticker or ticker_name == 'SYSTEM':
                    total_collected += stats['total_events']
                    relevant_collections[ticker_name] = stats
            
            stage_counts['events_collected'] = total_collected
            
            if relevant_collections:
                print(f"\n[BOX] BATCH COLLECTIONS:")
                print(f"{'-'*60}")
                for ticker_name, stats in relevant_collections.items():
                    print(f"{ticker_name}: {stats['count']} collections, {stats['total_events']} total events")
        
        # Print stage counts
        print("\nEvent counts by stage:")
        key_stages = ['event_detected', 'event_queued', 'events_collected', 
                    'event_ready_for_emission', 'event_emitted']
        
        for stage in key_stages:
            count = stage_counts.get(stage, 0)
            print(f"  {stage:25} : {count}")
            
            # Show type breakdown if available
            if stage in type_counts and stage != 'events_collected':  # Skip type breakdown for collections
                for event_type in sorted(type_counts[stage].keys()):
                    type_count = type_counts[stage][event_type]
                    print(f"    - {event_type:8} : {type_count}")
        
        # Calculate transition efficiencies
        print("\nStage-to-stage efficiency:")
        transitions = [
            ('event_detected', 'event_queued', '[SEARCH]->[IN]'),
            ('event_queued', 'events_collected', '[IN]->[BOX]'),
            ('events_collected', 'event_emitted', '[BOX]->[OUT]'),
            ('event_queued', 'event_emitted', '[IN]->[OUT]')  # Overall
        ]
        
        for from_stage, to_stage, icon in transitions:
            from_count = stage_counts.get(from_stage, 0)
            to_count = stage_counts.get(to_stage, 0)
            
            if from_count > 0:
                efficiency = (to_count / from_count) * 100
                lost = from_count - to_count
                
                # Special handling for events_collected which might be on SYSTEM
                if to_stage == 'events_collected' and to_count == 0:
                    # This is expected in pull model - collections happen on SYSTEM
                    print(f"  [i] {icon} {from_stage:20} -> {to_stage:20} : "
                        f"N/A (collected on SYSTEM ticker)")
                else:
                    status = "[OK]" if efficiency >= 90 else "[!]" if efficiency >= 80 else "[X]"
                    print(f"  {status} {icon} {from_stage:20} -> {to_stage:20} : "
                        f"{efficiency:5.1f}% ({from_count} -> {to_count})")
                    
                    if lost > 0:
                        print(f"     Lost: {lost} events")
    
    def _analyze_true_efficiency(self, ticker: str = None):
        """Calculate true efficiency based on unique event IDs"""
        print(f"\n[CHART] TRUE EFFICIENCY ANALYSIS (by Event ID)")
        print(f"{'-'*60}")
        
        # Use the stored first user time if available
        first_user_time = getattr(self, 'first_user_time', None)
        
        if first_user_time:
            print(f"[PIN] Analyzing events after first user connection ({first_user_time:.3f}s)")
            
            # Count events by timing
            events_before = 0
            events_after = 0
            
            for event_id in self.stage_event_ids.get('event_detected', set()):
                if event_id in self.events_by_id:
                    traces = self.events_by_id[event_id]
                    
                    # Apply ticker filter if specified
                    if ticker and not any(t['ticker'] == ticker for t in traces):
                        continue
                        
                    event_time = min(t['timestamp'] for t in traces)
                    if event_time < first_user_time:
                        events_before += 1
                    else:
                        events_after += 1
            
            print(f"\nTiming breakdown:")
            print(f"  Events before user: {events_before} (excluded)")
            print(f"  Events after user: {events_after}")
            
            # Calculate adjusted efficiency - also apply ticker filter to emitted
            if ticker:
                emitted_event_ids = [
                    eid for eid in self.stage_event_ids.get('event_emitted', set())
                    if eid in self.events_by_id and 
                    any(t['ticker'] == ticker for t in self.events_by_id[eid])
                ]
                emitted = len(emitted_event_ids)
            else:
                emitted = len(self.stage_event_ids.get('event_emitted', set()))
            
            if events_after > 0:
                adjusted_efficiency = (emitted / events_after) * 100
                print(f"\n[OK] Adjusted efficiency: {adjusted_efficiency:.1f}% ({emitted}/{events_after})")
            
            # Show raw for comparison
            total_detected = events_before + events_after
            if total_detected > 0:
                raw_efficiency = (emitted / total_detected) * 100
                print(f"[CHART] Raw efficiency: {raw_efficiency:.1f}% ({emitted}/{total_detected})")
                
        else:
            print(f"\n[!] No user connections found - showing raw efficiency")
            
        # Continue with original analysis for comparison
        stages = ['event_detected', 'event_queued', 'events_collected', 
                'event_ready_for_emission', 'event_emitted']
        
        print("\nRaw event counts (all events):")
        stage_counts = {}
        for stage in stages:
            count = len(self.stage_event_ids.get(stage, set()))
            stage_counts[stage] = count
            print(f"  {stage:25} : {count}")
        
        # Original efficiency calculations...
        detected = stage_counts.get('event_detected', 0)
        emitted = stage_counts.get('event_emitted', 0)
        if detected > 0:
            raw_efficiency = (emitted / detected) * 100
            print(f"\nRaw efficiency (all events): {raw_efficiency:.1f}%")
    
    def _analyze_event_types(self):
        """Analyze efficiency by event type"""
        print(f"\n[CHART] EFFICIENCY BY EVENT TYPE")
        print(f"{'-'*60}")
        
        # Get all event types
        all_types = set()
        for type_dict in self.event_types.values():
            all_types.update(type_dict.keys())
        
        # Calculate efficiency for each type
        print(f"{'Type':<10} {'Detected':>10} {'Queued':>10} {'Emitted':>10} {'Efficiency':>10}")
        print(f"{'-'*50}")
        
        for event_type in sorted(all_types):
            detected = len(self.event_types.get('event_detected', {}).get(event_type, set()))
            queued = len(self.event_types.get('event_queued', {}).get(event_type, set()))
            emitted = len(self.event_types.get('event_emitted', {}).get(event_type, set()))
            
            efficiency = (emitted / detected * 100) if detected > 0 else 0
            status = "[OK]" if efficiency >= 90 else "[!]" if efficiency >= 70 else "[X]"
            
            print(f"{event_type:<10} {detected:>10} {queued:>10} {emitted:>10} "
                  f"{status} {efficiency:>6.1f}%")
    
    def _analyze_universe_filtering(self):
        """Analyze universe filtering impact"""
        print(f"\n[SEARCH] UNIVERSE FILTERING ANALYSIS")
        print(f"{'-'*60}")
        
        if not self.universe_checks:
            print("No universe checks found in trace")
            return
        
        print(f"Total universe checks: {len(self.universe_checks)}")
        
        # Group by action type
        by_action = defaultdict(list)
        for check in self.universe_checks:
            by_action[check['action']].append(check)
        
        # Analyze each type
        for action, checks in sorted(by_action.items()):
            print(f"\n{action}: {len(checks)} occurrences")
            
            # Sample first few
            for check in checks[:3]:
                details = check['details']
                universe_name = details.get('universe_name', 'N/A')
                nvda_included = details.get('nvda_included', 'N/A')
                print(f"  - Universe: {universe_name}, NVDA included: {nvda_included}")
    
    def _print_executive_summary(self, ticker: str = None):
        """Print executive summary"""
        print(f"\n[LIST] EXECUTIVE SUMMARY")
        print(f"{'-'*60}")
        
        # NEW: Check for user connection timing issues
        first_user_time = None
        if self.user_connections:
            for conn in self.user_connections:
                if conn['action'] in ['user_authenticated', 'user_connected'] and conn.get('user_id'):
                    first_user_time = conn['timestamp']
                    break
        
        # Calculate metrics considering user connection
        total_detected = len(self.stage_event_ids.get('event_detected', set()))
        total_emitted = len(self.stage_event_ids.get('event_emitted', set()))
        
        # Count events before user connection
        events_before_user = 0
        if first_user_time:
            for event_id in self.stage_event_ids.get('event_detected', set()):
                if event_id in self.events_by_id:
                    traces = self.events_by_id[event_id]
                    event_time = min(t['timestamp'] for t in traces)
                    if event_time < first_user_time:
                        events_before_user += 1
        
        adjusted_detected = total_detected - events_before_user
        overall_efficiency = (total_emitted / adjusted_detected * 100) if adjusted_detected > 0 else 0
        
        # Determine health status
        if overall_efficiency >= 95:
            status = "[GREEN] EXCELLENT"
        elif overall_efficiency >= 90:
            status = "[YELLOW] GOOD"
        elif overall_efficiency >= 80:
            status = "[ORANGE] FAIR"
        else:
            status = "[RED] POOR"
        
        print(f"Overall System Health: {status}")
        print(f"Overall Efficiency: {overall_efficiency:.1f}% (adjusted for user connection)")
        print(f"Events Processed: {total_detected} ({events_before_user} before user connection)")
        print(f"Events Delivered: {total_emitted}")
        print(f"Events Lost: {adjusted_detected - total_emitted}")
        
        # Key findings
        print(f"\nKey Findings:")
        
        # NEW: User connection warning
        if events_before_user > 0:
            print(f"  [!] {events_before_user} events generated before user connection (excluded from efficiency)")
        
        if not self.user_connections:
            print(f"  [!] No user connection traces found - add user_connected trace!")
        
        # Find worst performing event type
        worst_type = None
        worst_efficiency = 100
        for event_type in self.event_types.get('event_detected', {}).keys():
            detected = len(self.event_types['event_detected'].get(event_type, set()))
            emitted = len(self.event_types.get('event_emitted', {}).get(event_type, set()))
            if detected > 0:
                efficiency = (emitted / detected) * 100
                if efficiency < worst_efficiency:
                    worst_efficiency = efficiency
                    worst_type = event_type
        
        if worst_type and worst_efficiency < 90:
            print(f"  [!] Worst performing type: {worst_type} ({worst_efficiency:.1f}% efficiency)")
        
        # Check for bottlenecks
        bottlenecks = []
        transitions = [
            ('event_detected', 'event_queued'),
            # Removed event_queued -> events_collected since collections happen on SYSTEM ticker
            ('events_collected', 'event_emitted')
        ]
        
        for from_stage, to_stage in transitions:
            from_count = len(self.stage_event_ids.get(from_stage, set()))
            to_count = len(self.stage_event_ids.get(to_stage, set()))
            
            # Skip if we're checking collections and count is 0 (expected in pull model)
            if to_stage == 'events_collected' and to_count == 0:
                continue
                
            if from_count > 0:
                efficiency = (to_count / from_count) * 100
                if efficiency < 90:
                    bottlenecks.append(f"{from_stage} -> {to_stage}")
        
        if bottlenecks:
            print(f"  [!] Bottlenecks detected at: {', '.join(bottlenecks)}")
        else:
            print(f"  [OK] No significant bottlenecks detected")
        
        # Recommendations
        print(f"\nRecommendations:")
        if overall_efficiency < 90:
            print(f"  1. Investigate event loss between collection and emission")
        if worst_type and worst_efficiency < 80:
            print(f"  2. Focus on improving {worst_type} event processing")
        if len(self.universe_checks) == 0:
            print(f"  3. Verify universe filtering traces are being generated")
        
        # If everything is perfect, say so!
        if overall_efficiency >= 95 and not bottlenecks and worst_efficiency >= 90:
            print(f"  [OK] System is operating at peak efficiency - no action needed!")

def main():
    """Main entry point with standardized argument handling"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Validate trace flow integrity and calculate efficiency metrics',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s                           # Use default trace_all.json
  %(prog)s NVDA.json                 # Analyze specific file
  %(prog)s NVDA.json NVDA            # Filter by ticker
  %(prog)s trace.json NVDA /path/    # Custom path, file, and ticker filter
        '''
    )
    
    parser.add_argument('filename', nargs='?', default='trace_all.json',
                       help='Trace filename with .json extension (default: trace_all.json)')
    parser.add_argument('ticker', nargs='?', default=None,
                       help='Optional ticker filter (e.g., NVDA)')
    parser.add_argument('trace_path', nargs='?', default='./logs/trace/',
                       help='Path to trace directory (default: ./logs/trace/)')
    
    args = parser.parse_args()
    
    # Update the file loading in validate_trace_file method
    validator = FlowValidator()
    validator.trace_path = args.trace_path  # Add this attribute
    validator.validate_trace_file(args.filename, args.ticker)

if __name__ == "__main__":
    main()