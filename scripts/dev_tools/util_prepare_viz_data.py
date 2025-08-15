#!/usr/bin/env python3
"""
Generate visualization-compatible trace summary
"""
import json
import os
from collections import defaultdict

def generate_summary_from_trace(trace_file_path):
    """Generate summary data from trace file for visualization"""
    
    with open(trace_file_path, 'r') as f:
        data = json.load(f)
    
    traces = data.get('steps', [])
    
    # Initialize counters
    events_generated = defaultdict(int)
    events_emitted = defaultdict(int)
    component_timings = defaultdict(float)
    user_connections = {
        'first_user_time': None,
        'events_before_first_user': 0,
        'total_users': 0,
        'raw_efficiency': 0,
        'adjusted_efficiency': 0
    }
    
    # Process traces
    first_user_time = None
    events_before_user = 0
    
    for trace in traces:
        action = trace.get('action', '')
        component = trace.get('component', '')
        duration = trace.get('duration_to_next_ms', 0)
        
        # Track component timings
        if duration > 0:
            component_timings[component] += duration / 1000.0
        
        # Track user connections
        if action == 'user_connected' and first_user_time is None:
            first_user_time = trace.get('timestamp', 0)
            user_connections['first_user_time'] = first_user_time
            user_connections['total_users'] = 1
        
        # Count events
        if action == 'event_detected':
            details = trace.get('data', {}).get('details', {})
            event_type = details.get('event_type', '')
            if event_type:
                events_generated[event_type + 's'] += 1
                if first_user_time is None or trace.get('timestamp', 0) < first_user_time:
                    events_before_user += 1
        
        elif action == 'event_emitted':
            details = trace.get('data', {}).get('details', {})
            event_type = details.get('event_type', '')
            if event_type:
                events_emitted[event_type + 's'] += 1
    
    # Calculate efficiencies
    total_gen = sum(events_generated.values())
    total_emit = sum(events_emitted.values())
    
    user_connections['events_before_first_user'] = events_before_user
    if total_gen > 0:
        user_connections['raw_efficiency'] = (total_emit / total_gen) * 100
        adjusted_gen = total_gen - events_before_user
        if adjusted_gen > 0:
            user_connections['adjusted_efficiency'] = (total_emit / adjusted_gen) * 100
    
    # Add summary to data
    data['summary'] = {
        'events_generated': dict(events_generated),
        'events_emitted': dict(events_emitted),
        'component_timings': dict(component_timings),
        'user_connections': user_connections,
        'counters': {
            'events_detected_total': total_gen,
            'events_emitted_total': total_emit
        }
    }
    
    # Save enhanced file
    output_path = trace_file_path.replace('.json', '_viz.json')
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"Created visualization-ready file: {output_path}")
    return output_path

# If run directly
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        generate_summary_from_trace(sys.argv[1])
    else:
        generate_summary_from_trace('./logs/trace/trace_all.json')