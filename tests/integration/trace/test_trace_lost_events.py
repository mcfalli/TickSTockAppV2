#!/usr/bin/env python3
"""
Lost Events Analysis
Identifies events that were detected but never emitted.
"""
import json
import sys
import os

def find_lost_events(filename='trace_all.json', trace_path='./logs/trace/'):
    """
    Find events that were lost in the processing pipeline.
    
    Args:
        filename: Full filename including .json extension (default: trace_all.json)
        trace_path: Path to trace directory (default: ./logs/trace/)
    """
    # Construct full path
    full_path = os.path.join(trace_path, filename)
    
    if not os.path.exists(full_path):
        print(f"Error: File not found: {full_path}")
        sys.exit(1)
    
    with open(full_path, 'r') as f:
        data = json.load(f)
    
    print(f"Analyzing: {full_path}")
    
    traces = data.get('steps', [])
    
    # Find user connection time
    user_time = None
    for trace in traces:
        if trace.get('action') == 'user_connected':
            user_time = trace.get('timestamp', 0)
            break
    
    if not user_time:
        print("No user connection found")
        return
    
    # Track emission cycles from SYSTEM ticker
    emission_cycles = []
    for trace in traces:
        if trace.get('ticker') == 'SYSTEM':
            if trace.get('action') == 'emission_cycle_start':
                emission_cycles.append({
                    'start': trace.get('timestamp', 0),
                    'end': None
                })
            elif trace.get('action') == 'emission_cycle_complete' and emission_cycles:
                emission_cycles[-1]['end'] = trace.get('timestamp', 0)
    
    # Track events by ID
    events = {}
    
    for trace in traces:
        if trace.get('ticker') != 'NVDA':
            continue
            
        timestamp = trace.get('timestamp', 0)
        if timestamp < user_time:
            continue  # Skip pre-user events
            
        event_id = trace.get('data', {}).get('details', {}).get('event_id')
        if not event_id or event_id == 'None':
            continue
            
        if event_id not in events:
            events[event_id] = {
                'stages': [],
                'first_seen': timestamp,
                'event_type': trace.get('data', {}).get('details', {}).get('event_type', 'unknown')
            }
        
        events[event_id]['stages'].append({
            'action': trace.get('action'),
            'timestamp': timestamp,
            'component': trace.get('component', '')
        })
    
    # Find events that didn't complete
    lost_events = []
    for event_id, event_data in events.items():
        stages = [s['action'] for s in event_data['stages']]
        if 'event_detected' in stages and 'event_emitted' not in stages:
            last_stage = event_data['stages'][-1]
            
            # Check if event was in an emission cycle
            in_cycle = False
            for stage in event_data['stages']:
                if stage['action'] == 'event_ready_for_emission':
                    # Check if this was during an emission cycle
                    for cycle in emission_cycles:
                        if cycle['start'] <= stage['timestamp'] <= (cycle['end'] or float('inf')):
                            in_cycle = True
                            break
            
            lost_events.append({
                'event_id': event_id,
                'event_type': event_data['event_type'],
                'last_stage': last_stage['action'],
                'last_time': last_stage['timestamp'],
                'stages_hit': stages,
                'in_emission_cycle': in_cycle
            })
    
    print(f"Emission Cycles: {len(emission_cycles)} ({len([c for c in emission_cycles if c['end']])} completed)")
    print(f"Found {len(lost_events)} lost events (after user connection):\n")
    
    for event in lost_events:
        print(f"Event ID: {event['event_id']}")
        print(f"  Type: {event['event_type']}")
        print(f"  Last seen: {event['last_stage']} at {event['last_time']:.3f}")
        print(f"  In emission cycle: {'Yes' if event['in_emission_cycle'] else 'No'}")
        print(f"  Stages: {' -> '.join(event['stages_hit'])}")
        print()

def main():
    """Main entry point with command line argument handling"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Find events lost in the processing pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s                           # Use default trace_all.json
  %(prog)s NVDA.json                 # Analyze specific file
  %(prog)s NVDA.json /custom/path/   # Custom path and file
        '''
    )
    
    parser.add_argument('filename', nargs='?', default='trace_all.json',
                       help='Trace filename with .json extension (default: trace_all.json)')
    parser.add_argument('trace_path', nargs='?', default='./logs/trace/',
                       help='Path to trace directory (default: ./logs/trace/)')
    
    args = parser.parse_args()
    
    find_lost_events(args.filename, args.trace_path)

if __name__ == "__main__":
    main()