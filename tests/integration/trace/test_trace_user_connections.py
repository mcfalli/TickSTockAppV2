#!/usr/bin/env python3
"""
User Connection Analysis
Analyzes user connection timing and its impact on event delivery.
"""
import json
import sys
import os
import io

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def analyze_trace_with_users(filename='trace_all.json', trace_path='./logs/trace/', target_ticker='NVDA'):
    """
    Analyze trace with focus on user connection timing.
    
    Args:
        filename: Full filename including .json extension (default: trace_all.json)
        trace_path: Path to trace directory (default: ./logs/trace/)
        target_ticker: Ticker to analyze (default: NVDA)
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
    
    # Find user connections (SYSTEM ticker)
    user_connections = []
    for trace in traces:
        if trace.get('action') == 'user_connected':
            user_connections.append({
                'timestamp': trace.get('timestamp', 0),
                'user_id': trace.get('data', {}).get('details', {}).get('user_id'),
                'ticker': trace.get('ticker')
            })
    
    if user_connections:
        first_user_time = user_connections[0]['timestamp']
        print(f"[OK] Found {len(user_connections)} user connections")
        print(f"First user connected at: {first_user_time:.3f} (User ID: {user_connections[0]['user_id']})")
    else:
        print("[X] No user connections found")
        first_user_time = float('inf')
    
    # Count target ticker events
    ticker_events = {'before_user': 0, 'after_user': 0}
    event_stages = {}
    
    for trace in traces:
        if trace.get('ticker') == target_ticker:
            action = trace.get('action', '')
            timestamp = trace.get('timestamp', 0)
            
            if action in ['event_detected', 'event_queued', 'event_emitted']:
                if action not in event_stages:
                    event_stages[action] = 0
                event_stages[action] += 1
                
                if action == 'event_detected':
                    if timestamp < first_user_time:
                        ticker_events['before_user'] += 1
                    else:
                        ticker_events['after_user'] += 1
    
    print(f"\n{target_ticker} Event Analysis:")
    print(f"Events before user connection: {ticker_events['before_user']}")
    print(f"Events after user connection: {ticker_events['after_user']}")
    
    if 'event_detected' in event_stages and 'event_emitted' in event_stages:
        detected = event_stages['event_detected']
        emitted = event_stages['event_emitted']
        
        # Calculate adjusted efficiency
        adjusted_detected = ticker_events['after_user']
        if adjusted_detected > 0:
            adjusted_efficiency = (emitted / adjusted_detected) * 100
            print(f"\nRaw efficiency: {emitted}/{detected} = {emitted/detected*100:.1f}%")
            print(f"Adjusted efficiency (after user): {emitted}/{adjusted_detected} = {adjusted_efficiency:.1f}%")
        else:
            print(f"\nAll events occurred before user connection!")

def main():
    """Main entry point with command line argument handling"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Analyze user connection timing and event delivery',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s                           # Use default trace_all.json
  %(prog)s NVDA.json                 # Analyze specific file
  %(prog)s NVDA.json /path/ AAPL     # Custom path, file, and ticker
        '''
    )
    
    parser.add_argument('filename', nargs='?', default='trace_all.json',
                       help='Trace filename with .json extension (default: trace_all.json)')
    parser.add_argument('trace_path', nargs='?', default='./logs/trace/',
                       help='Path to trace directory (default: ./logs/trace/)')
    parser.add_argument('ticker', nargs='?', default='NVDA',
                       help='Target ticker to analyze (default: NVDA)')
    
    args = parser.parse_args()
    
    analyze_trace_with_users(args.filename, args.trace_path, args.ticker)

if __name__ == "__main__":
    main()