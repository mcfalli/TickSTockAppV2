#!/usr/bin/env python3
"""
Emission Gap Analysis
Identifies gaps between events being marked ready and actually emitted.
"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from trace_component_definitions import COMPONENT_REQUIREMENTS, get_all_expected_actions_for_component


def analyze_emission_gap(filename='trace_all.json', trace_path='./logs/trace/'):
    """
    Analyze gaps in the emission pipeline.
    
    Args:
        filename: Full filename including .json extension (default: trace_all.json)
        trace_path: Path to trace directory (default: ./logs/trace/)
    """
    # Get emission-related actions from centralized definitions
    websocket_publisher_actions = get_all_expected_actions_for_component('WebSocketPublisher')
    
    # Extract specific emission cycle actions
    emission_start_action = next((a for a in websocket_publisher_actions if 'emission' in a and 'start' in a), 'emission_cycle_start')
    emission_complete_action = next((a for a in websocket_publisher_actions if 'emission' in a and 'complete' in a), 'emission_cycle_complete')
    ready_action = 'event_ready_for_emission'  # This is consistent across tests
    emitted_action = 'event_emitted'  # This is the critical action
    
    # Construct full path
    full_path = os.path.join(trace_path, filename)
    
    if not os.path.exists(full_path):
        print(f"Error: File not found: {full_path}")
        sys.exit(1)
    
    with open(full_path, 'r') as f:
        data = json.load(f)
    
    print(f"Analyzing: {full_path}")
    
    traces = data.get('steps', [])
    
    # Find emission cycles using centralized action names
    emission_cycles = []
    ready_events = {}
    emitted_events = set()
    
    for trace in traces:
        action = trace.get('action', '')
        timestamp = trace.get('timestamp', 0)
        
        if action == emission_start_action:
            emission_cycles.append({
                'start': timestamp,
                'end': None,
                'ready_count': 0,
                'emitted_count': 0
            })
        
        elif action == emission_complete_action and emission_cycles:
            emission_cycles[-1]['end'] = timestamp
            
        elif action == ready_action:
            event_id = trace.get('data', {}).get('details', {}).get('event_id')
            if event_id:
                ready_events[event_id] = {
                    'timestamp': timestamp,
                    'ticker': trace.get('ticker', ''),
                    'event_type': trace.get('data', {}).get('details', {}).get('event_type', '')
                }
                if emission_cycles:
                    emission_cycles[-1]['ready_count'] += 1
                    
        elif action == emitted_action:
            event_id = trace.get('data', {}).get('details', {}).get('event_id')
            if event_id:
                emitted_events.add(event_id)
                if emission_cycles:
                    emission_cycles[-1]['emitted_count'] += 1
    
    # Find events marked ready but not emitted
    lost_after_ready = []
    for event_id, info in ready_events.items():
        if event_id not in emitted_events:
            lost_after_ready.append({
                'event_id': event_id,
                'timestamp': info['timestamp'],
                'ticker': info['ticker'],
                'event_type': info['event_type']
            })
    
    print(f"Emission Cycle Analysis:")
    print(f"{'='*60}")
    print(f"Found {len(emission_cycles)} emission cycles")
    print(f"Total events marked ready: {len(ready_events)}")
    print(f"Total events emitted: {len(emitted_events)}")
    print(f"Lost after ready: {len(lost_after_ready)}")
    
    # Check for patterns in emission cycles
    print(f"\nEmission Cycles with Losses:")
    cycles_with_losses = 0
    for i, cycle in enumerate(emission_cycles):
        if cycle['ready_count'] > cycle['emitted_count']:
            cycles_with_losses += 1
            duration = (cycle['end'] - cycle['start']) * 1000 if cycle['end'] else 0
            print(f"\nCycle {i+1} at {cycle['start']:.3f}:")
            print(f"  Duration: {duration:.1f}ms")
            print(f"  Ready: {cycle['ready_count']}, Emitted: {cycle['emitted_count']}")
            print(f"  Lost: {cycle['ready_count'] - cycle['emitted_count']}")
    
    if cycles_with_losses == 0:
        print("  [OK] No cycles with losses detected")
    
    # Show the specific lost events
    if lost_after_ready:
        print(f"\nEvents Lost After Being Marked Ready:")
        for event in lost_after_ready:
            # Find which emission cycle this was in
            cycle_num = None
            for i, cycle in enumerate(emission_cycles):
                if cycle['start'] <= event['timestamp'] <= (cycle['end'] or float('inf')):
                    cycle_num = i + 1
                    break
            
            print(f"\n{event['event_id']}:")
            print(f"  Type: {event['event_type']}")
            print(f"  Ticker: {event['ticker']}")
            print(f"  Ready at: {event['timestamp']:.3f}")
            print(f"  In cycle: {cycle_num if cycle_num else 'Unknown'}")
            
            # Check for universe filtering
            if event['ticker'] == 'NVDA':
                print(f"  [!] NVDA event lost despite being in universe")
    else:
        print(f"\n[OK] No events lost after being marked ready")

def main():
    """Main entry point with command line argument handling"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Analyze gaps between ready and emitted events',
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
    
    analyze_emission_gap(args.filename, args.trace_path)

if __name__ == "__main__":
    main()