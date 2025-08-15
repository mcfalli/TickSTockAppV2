#!/usr/bin/env python3
"""
Trace High/Low Analysis
Deep analysis of high/low event detection and processing.
Part of the test_*trace*.py suite.
"""
import json
import sys
import os
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Set, Optional, Tuple
import io

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    
def analyze_highlow_behavior(filename='trace_all.json', trace_path='./logs/trace/', ticker='NVDA'):
    """
    Analyze high/low event detection and processing.
    
    Args:
        filename: Full filename including .json extension
        trace_path: Path to trace directory
        ticker: Ticker to analyze (default: NVDA)
    """
    # Construct full path
    full_path = os.path.join(trace_path, filename)
    
    if not os.path.exists(full_path):
        print(f"Error: File not found: {full_path}")
        sys.exit(1)
    
    with open(full_path, 'r') as f:
        data = json.load(f)
    
    print(f"Analyzing: {full_path}")
    print(f"\n{'='*80}")
    print(f"HIGH/LOW ANALYSIS FOR {ticker}")
    print(f"{'='*80}")
    
    traces = data.get('steps', [])
    
    # Initialize analyzer
    analyzer = HighLowAnalyzer(ticker)
    
    # Process traces
    for trace in traces:
        analyzer.process_trace(trace)
    
    # Run analyses
    analyzer.analyze_detection_patterns()
    analyzer.analyze_session_vs_absolute()
    analyzer.analyze_price_movements()
    analyzer.analyze_detection_efficiency()
    analyzer.analyze_timing_patterns()
    analyzer.generate_recommendations()


class HighLowAnalyzer:
    """Comprehensive high/low event analysis"""
    
    def __init__(self, target_ticker: str):
        self.target_ticker = target_ticker
        
        # Event tracking
        self.high_events = []
        self.low_events = []
        self.price_history = []
        
        # Detection tracking
        self.detection_attempts = []
        self.detection_timings = []
        
        # Session tracking
        self.session_boundaries = []
        self.session_highs = defaultdict(list)
        self.session_lows = defaultdict(list)
        
        # Price tracking
        self.actual_highs = defaultdict(float)  # date -> high
        self.actual_lows = defaultdict(lambda: float('inf'))  # date -> low
        
    def process_trace(self, trace: Dict):
        """Process individual trace entry"""
        ticker = trace.get('ticker', '')
        action = trace.get('action', '')
        timestamp = trace.get('timestamp', 0)
        data = trace.get('data', {})
        
        # Handle string data
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except:
                data = {}
        
        details = data.get('details', {})
        
        # Track price ticks
        if ticker == self.target_ticker and action == 'tick_created':
            price = data.get('price', 0)
            if price > 0:
                self.price_history.append({
                    'timestamp': timestamp,
                    'price': price,
                    'volume': data.get('volume', 0)
                })
                
                # Track daily highs/lows
                date = datetime.fromtimestamp(timestamp).date()
                self.actual_highs[date] = max(self.actual_highs[date], price)
                self.actual_lows[date] = min(self.actual_lows[date], price)
        
        # Track high/low detections
        if action == 'event_detected' and details.get('event_type') in ['high', 'low', 'session_high', 'session_low']:
            event_type = self._normalize_event_type(details.get('event_type'))
            event_data = {
                'timestamp': timestamp,
                'event_id': details.get('event_id'),
                'price': details.get('price', 0),
                'ticker': ticker,
                'raw_type': details.get('event_type'),
                'normalized_type': event_type
            }
            
            if event_type == 'high':
                self.high_events.append(event_data)
            else:
                self.low_events.append(event_data)
        
        # Track detection attempts
        if action in ['detection_start', 'new_high_detected', 'new_low_detected']:
            self.detection_attempts.append({
                'timestamp': timestamp,
                'action': action,
                'ticker': ticker,
                'details': details
            })
        
        # Track detection timing
        if action == 'detection_slow':
            duration = data.get('duration_ms', 0)
            self.detection_timings.append({
                'timestamp': timestamp,
                'duration_ms': duration,
                'threshold_ms': details.get('threshold_ms', 50)
            })
        
        # Track session boundaries
        if action in ['session_start', 'session_end', 'market_open', 'market_close']:
            self.session_boundaries.append({
                'timestamp': timestamp,
                'action': action,
                'session_type': details.get('session_type', 'regular')
            })
    
    def _normalize_event_type(self, event_type: str) -> str:
        """Normalize event type"""
        if not event_type:
            return 'unknown'
        
        normalized = str(event_type).lower()
        
        # Map session variants to base types
        if 'high' in normalized:
            return 'high'
        elif 'low' in normalized:
            return 'low'
        
        return normalized
    
    def analyze_detection_patterns(self):
        """Analyze high/low detection patterns"""
        print("\n[CHART] DETECTION PATTERNS")
        print("-" * 60)
        
        total_highs = len(self.high_events)
        total_lows = len(self.low_events)
        
        print(f"High events detected: {total_highs}")
        print(f"Low events detected: {total_lows}")
        print(f"High/Low ratio: {total_highs/total_lows:.2f}" if total_lows > 0 else "N/A")
        
        # Analyze price levels
        if self.high_events:
            high_prices = [e['price'] for e in self.high_events if e['price'] > 0]
            if high_prices:
                avg_high = sum(high_prices) / len(high_prices)
                print(f"\nHigh price statistics:")
                print(f"  Average: ${avg_high:.2f}")
                print(f"  Min: ${min(high_prices):.2f}")
                print(f"  Max: ${max(high_prices):.2f}")
        
        if self.low_events:
            low_prices = [e['price'] for e in self.low_events if e['price'] > 0]
            if low_prices:
                avg_low = sum(low_prices) / len(low_prices)
                print(f"\nLow price statistics:")
                print(f"  Average: ${avg_low:.2f}")
                print(f"  Min: ${min(low_prices):.2f}")
                print(f"  Max: ${max(low_prices):.2f}")
        
        # Time distribution
        self._analyze_time_distribution()
    
    def _analyze_time_distribution(self):
        """Analyze when highs/lows occur"""
        print("\n[TIME] Time Distribution:")
        
        # Group by hour of day
        high_hours = defaultdict(int)
        low_hours = defaultdict(int)
        
        for event in self.high_events:
            hour = datetime.fromtimestamp(event['timestamp']).hour
            high_hours[hour] += 1
        
        for event in self.low_events:
            hour = datetime.fromtimestamp(event['timestamp']).hour
            low_hours[hour] += 1
        
        # Find peak hours
        if high_hours:
            peak_high_hour = max(high_hours.items(), key=lambda x: x[1])
            print(f"  Peak hour for highs: {peak_high_hour[0]:02d}:00 ({peak_high_hour[1]} events)")
        
        if low_hours:
            peak_low_hour = max(low_hours.items(), key=lambda x: x[1])
            print(f"  Peak hour for lows: {peak_low_hour[0]:02d}:00 ({peak_low_hour[1]} events)")
        
        # Market open/close bias
        market_open_highs = sum(high_hours[h] for h in range(9, 11))  # 9-11 AM
        market_close_highs = sum(high_hours[h] for h in range(15, 17))  # 3-5 PM
        
        if market_open_highs + market_close_highs > 0:
            open_bias = market_open_highs / (market_open_highs + market_close_highs) * 100
            print(f"\n  Market open bias for highs: {open_bias:.1f}%")
            print(f"  Market close bias for highs: {100-open_bias:.1f}%")
    
    def analyze_session_vs_absolute(self):
        """Analyze session highs/lows vs absolute"""
        print("\n[SESSION] Session vs Absolute Analysis")
        print("-" * 60)
        
        # Count session-specific events
        session_highs = sum(1 for e in self.high_events if 'session' in e['raw_type'].lower())
        session_lows = sum(1 for e in self.low_events if 'session' in e['raw_type'].lower())
        
        absolute_highs = len(self.high_events) - session_highs
        absolute_lows = len(self.low_events) - session_lows
        
        print(f"Session highs: {session_highs}")
        print(f"Absolute highs: {absolute_highs}")
        print(f"Session lows: {session_lows}")
        print(f"Absolute lows: {absolute_lows}")
        
        # Check for proper session handling
        if session_highs == 0 and session_lows == 0:
            print("\n⚠️  No session-specific events detected")
            print("  Consider implementing session-aware detection")
    
    def analyze_price_movements(self):
        """Analyze price movements around events"""
        print("\n[PRICE] Price Movement Analysis")
        print("-" * 60)
        
        if not self.price_history:
            print("No price history available")
            return
        
        # Sort price history
        self.price_history.sort(key=lambda x: x['timestamp'])
        
        # Analyze movements after high detection
        print("Price movement after high detection:")
        self._analyze_post_event_movement(self.high_events, 'high')
        
        # Analyze movements after low detection
        print("\nPrice movement after low detection:")
        self._analyze_post_event_movement(self.low_events, 'low')
    
    def _analyze_post_event_movement(self, events: List[Dict], event_type: str):
        """Analyze price movement after event detection"""
        if not events or not self.price_history:
            print("  Insufficient data")
            return
        
        reversals = 0
        continuations = 0
        
        for event in events[:20]:  # Sample first 20
            event_time = event['timestamp']
            event_price = event['price']
            
            if event_price <= 0:
                continue
            
            # Find next 10 prices after event
            future_prices = []
            for price_data in self.price_history:
                if price_data['timestamp'] > event_time:
                    future_prices.append(price_data['price'])
                    if len(future_prices) >= 10:
                        break
            
            if len(future_prices) >= 5:
                avg_future = sum(future_prices[:5]) / 5
                
                if event_type == 'high':
                    if avg_future < event_price * 0.995:  # 0.5% reversal
                        reversals += 1
                    else:
                        continuations += 1
                else:  # low
                    if avg_future > event_price * 1.005:  # 0.5% reversal
                        reversals += 1
                    else:
                        continuations += 1
        
        total = reversals + continuations
        if total > 0:
            reversal_rate = reversals / total * 100
            print(f"  Reversal rate: {reversal_rate:.1f}% ({reversals}/{total})")
            
            if reversal_rate > 70:
                print(f"  ✅ Good {event_type} detection - high reversal rate")
            elif reversal_rate < 30:
                print(f"  ⚠️  Poor {event_type} detection - low reversal rate")
    
    def analyze_detection_efficiency(self):
        """Analyze detection efficiency"""
        print("\n[PERF] Detection Efficiency")
        print("-" * 60)
        
        # Compare detected events with actual highs/lows
        if self.actual_highs and self.actual_lows:
            print(f"Trading days analyzed: {len(self.actual_highs)}")
            
            # Check detection accuracy
            detected_dates = set()
            for event in self.high_events + self.low_events:
                date = datetime.fromtimestamp(event['timestamp']).date()
                detected_dates.add(date)
            
            coverage = len(detected_dates) / len(self.actual_highs) * 100 if self.actual_highs else 0
            print(f"Daily coverage: {coverage:.1f}% of trading days had detections")
        
        # Analyze detection timing
        if self.detection_timings:
            durations = [t['duration_ms'] for t in self.detection_timings]
            avg_duration = sum(durations) / len(durations)
            slow_detections = sum(1 for d in durations if d > 50)
            
            print(f"\nDetection performance:")
            print(f"  Average duration: {avg_duration:.1f}ms")
            print(f"  Slow detections: {slow_detections} (>{50}ms)")
            
            if avg_duration > 30:
                print("  ⚠️  Consider optimizing detection algorithm")
    
    def analyze_timing_patterns(self):
        """Analyze detection timing patterns"""
        print("\n[PATTERN] Timing Patterns")
        print("-" * 60)
        
        # Analyze event clustering
        all_events = sorted(self.high_events + self.low_events, key=lambda x: x['timestamp'])
        
        if len(all_events) > 1:
            # Calculate inter-event times
            inter_event_times = []
            for i in range(1, len(all_events)):
                gap = all_events[i]['timestamp'] - all_events[i-1]['timestamp']
                inter_event_times.append(gap)
            
            if inter_event_times:
                avg_gap = sum(inter_event_times) / len(inter_event_times)
                min_gap = min(inter_event_times)
                
                print(f"Inter-event timing:")
                print(f"  Average gap: {avg_gap:.1f}s")
                print(f"  Minimum gap: {min_gap:.1f}s")
                
                # Check for rapid-fire events
                rapid_events = sum(1 for gap in inter_event_times if gap < 1.0)
                if rapid_events > 0:
                    print(f"  ⚠️  Rapid-fire events: {rapid_events} (gap < 1s)")
                    print("  Consider implementing event throttling")
        
        # Analyze by market session
        self._analyze_session_patterns()
    
    def _analyze_session_patterns(self):
        """Analyze patterns by market session"""
        # Define market sessions (EST)
        pre_market = (4, 9.5)    # 4:00 AM - 9:30 AM
        regular = (9.5, 16)      # 9:30 AM - 4:00 PM
        after_hours = (16, 20)   # 4:00 PM - 8:00 PM
        
        session_events = {
            'pre_market': {'highs': 0, 'lows': 0},
            'regular': {'highs': 0, 'lows': 0},
            'after_hours': {'highs': 0, 'lows': 0}
        }
        
        for event in self.high_events + self.low_events:
            hour = datetime.fromtimestamp(event['timestamp']).hour + \
                   datetime.fromtimestamp(event['timestamp']).minute / 60
            
            event_type = 'highs' if event in self.high_events else 'lows'
            
            if pre_market[0] <= hour < pre_market[1]:
                session_events['pre_market'][event_type] += 1
            elif regular[0] <= hour < regular[1]:
                session_events['regular'][event_type] += 1
            elif after_hours[0] <= hour < after_hours[1]:
                session_events['after_hours'][event_type] += 1
        
        print("\nEvents by market session:")
        for session, counts in session_events.items():
            total = counts['highs'] + counts['lows']
            if total > 0:
                print(f"  {session}: {total} events ({counts['highs']} highs, {counts['lows']} lows)")
    
    def generate_recommendations(self):
        """Generate recommendations based on analysis"""
        print("\n[TIP] RECOMMENDATIONS")
        print("-" * 60)
        
        recommendations = []
        
        # Check high/low balance
        if self.high_events and self.low_events:
            ratio = len(self.high_events) / len(self.low_events)
            if ratio > 2 or ratio < 0.5:
                recommendations.append({
                    'priority': 'MEDIUM',
                    'issue': f'Imbalanced high/low ratio: {ratio:.2f}',
                    'action': 'Review detection thresholds for balance'
                })
        
        # Check detection performance
        if self.detection_timings:
            slow_pct = sum(1 for t in self.detection_timings if t['duration_ms'] > 50) / len(self.detection_timings) * 100
            if slow_pct > 10:
                recommendations.append({
                    'priority': 'HIGH',
                    'issue': f'{slow_pct:.1f}% of detections are slow',
                    'action': 'Optimize detection algorithm for speed'
                })
        
        # Check session detection
        session_events = sum(1 for e in self.high_events + self.low_events if 'session' in e['raw_type'].lower())
        if session_events == 0:
            recommendations.append({
                'priority': 'LOW',
                'issue': 'No session-specific high/low detection',
                'action': 'Implement session-aware detection for intraday highs/lows'
            })
        
        # Check rapid-fire events
        if len(self.high_events + self.low_events) > 1:
            all_events = sorted(self.high_events + self.low_events, key=lambda x: x['timestamp'])
            rapid_count = 0
            for i in range(1, len(all_events)):
                if all_events[i]['timestamp'] - all_events[i-1]['timestamp'] < 1.0:
                    rapid_count += 1
            
            if rapid_count > 5:
                recommendations.append({
                    'priority': 'MEDIUM',
                    'issue': f'{rapid_count} rapid-fire detections',
                    'action': 'Implement event throttling or deduplication'
                })
        
        # Print recommendations
        if recommendations:
            # Sort by priority
            priority_order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
            recommendations.sort(key=lambda r: priority_order.get(r['priority'], 999))
            
            for rec in recommendations:
                print(f"\n[{rec['priority']}] {rec['issue']}")
                print(f"  Action: {rec['action']}")
        else:
            print("\n✅ High/low detection is well-balanced and efficient")
        
        # Always include best practices
        print("\n[BEST] Best Practices:")
        print("  1. Track both session and daily highs/lows")
        print("  2. Implement reversal confirmation logic")
        print("  3. Consider volume at high/low points")
        print("  4. Monitor detection latency closely")


def main():
    """Main entry point with command line argument handling"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Analyze high/low event detection and processing',
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
                       help='Ticker to analyze (default: NVDA)')
    
    args = parser.parse_args()
    
    analyze_highlow_behavior(args.filename, args.trace_path, args.ticker)

if __name__ == "__main__":
    main()