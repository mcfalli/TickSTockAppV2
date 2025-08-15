#!/usr/bin/env python3
"""
Trace Emission Timing Analysis
Analyzes timing patterns in event emission cycles.
"""
import json
import sys
import os

def analyze_emission_timing(filename='trace_all.json', trace_path='./logs/trace/'):
    """
    Analyze emission timing patterns in trace file.
    
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
    
    # Track emission cycles and ready events with more detail
    emission_timeline = []
    emission_cycles = []
    
    for trace in traces:
        action = trace.get('action', '')
        timestamp = trace.get('timestamp', 0)
        ticker = trace.get('ticker', '')
        
        # Track emission cycles from SYSTEM ticker
        if ticker == 'SYSTEM' and action in ['emission_cycle_start', 'emission_cycle_complete']:
            emission_timeline.append({
                'timestamp': timestamp,
                'action': action,
                'ticker': ticker,
                'component': trace.get('component', '')
            })
            
            if action == 'emission_cycle_start':
                emission_cycles.append({
                    'start': timestamp,
                    'end': None
                })
            elif action == 'emission_cycle_complete' and emission_cycles:
                emission_cycles[-1]['end'] = timestamp
        
        # Track ready and emitted events from all tickers
        elif action in ['event_ready_for_emission', 'event_emitted']:
            emission_timeline.append({
                'timestamp': timestamp,
                'action': action,
                'ticker': ticker,
                'event_id': trace.get('data', {}).get('details', {}).get('event_id'),
                'component': trace.get('component', ''),
                'user_id': trace.get('data', {}).get('details', {}).get('user_id')
            })
    
    # Sort by timestamp
    emission_timeline.sort(key=lambda x: x['timestamp'])
    
    # Analyze patterns
    print("Emission Timeline Analysis")
    print("="*80)
    
    # Look for ready events outside emission cycles
    orphaned_ready = []
    current_cycle = None
    
    for event in emission_timeline:
        if event['action'] == 'emission_cycle_start':
            current_cycle = event['timestamp']
            
        elif event['action'] == 'emission_cycle_complete':
            current_cycle = None
            
        elif event['action'] == 'event_ready_for_emission':
            if current_cycle is None:
                orphaned_ready.append(event)
    
    print(f"Found {len(emission_cycles)} emission cycles (SYSTEM ticker)")
    print(f"Found {len(orphaned_ready)} 'ready' events outside emission cycles")
    
    if orphaned_ready:
        print("\nOrphaned Ready Events (first 10):")
        for event in orphaned_ready[:10]:
            print(f"  {event['timestamp']:.3f}: {event['ticker']} - {event['event_id']}")
    
    # Analyze emission cycles
    print("\nEmission Cycle Analysis:")
    complete_cycles = [c for c in emission_cycles if c['end'] is not None]
    incomplete_cycles = [c for c in emission_cycles if c['end'] is None]
    
    print(f"Complete cycles: {len(complete_cycles)}")
    print(f"Incomplete cycles: {len(incomplete_cycles)}")
    
    if complete_cycles:
        durations = [(c['end'] - c['start']) * 1000 for c in complete_cycles]
        avg_duration = sum(durations) / len(durations)
        print(f"Average cycle duration: {avg_duration:.1f}ms")
        print(f"Min/Max duration: {min(durations):.1f}ms / {max(durations):.1f}ms")
    
    # Check event distribution across cycles
    print("\nEvent Distribution:")
    events_per_cycle = {}
    
    for event in emission_timeline:
        if event['action'] == 'event_ready_for_emission':
            # Find which cycle this belongs to
            for i, cycle in enumerate(emission_cycles):
                if cycle['start'] <= event['timestamp'] <= (cycle['end'] or float('inf')):
                    if i not in events_per_cycle:
                        events_per_cycle[i] = 0
                    events_per_cycle[i] += 1
                    break
    
    if events_per_cycle:
        counts = list(events_per_cycle.values())
        print(f"Events per cycle - Average: {sum(counts)/len(counts):.1f}, "
              f"Min: {min(counts)}, Max: {max(counts)}")
    
    # Component Analysis
    print("\nComponent Analysis:")
    components = {}
    for event in emission_timeline:
        comp = event.get('component', 'Unknown')
        action = event['action']
        if comp not in components:
            components[comp] = {'ready': 0, 'emitted': 0, 'cycles': 0}
        
        if action == 'event_ready_for_emission':
            components[comp]['ready'] += 1
        elif action == 'event_emitted':
            components[comp]['emitted'] += 1
        elif action in ['emission_cycle_start', 'emission_cycle_complete']:
            components[comp]['cycles'] += 1
    
    for comp, stats in components.items():
        if any(stats.values()):
            print(f"  {comp}: {stats['cycles']} cycles, {stats['ready']} ready, {stats['emitted']} emitted")

def main():
    """Main entry point with command line argument handling"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Analyze trace emission timing patterns',
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
    
    analyze_emission_timing(args.filename, args.trace_path)

if __name__ == "__main__":
    main()