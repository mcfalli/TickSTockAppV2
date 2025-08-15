#!/usr/bin/env python3
"""
Trace Trend Analysis
Deep analysis of trend detection and processing.
Part of the test_*trace*.py suite.
"""
import json
import sys
import os
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional, Tuple
import statistics
import io

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def analyze_trend_behavior(filename='trace_all.json', trace_path='./logs/trace/', ticker='NVDA'):
    """
    Analyze trend detection and processing behavior.
    
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
    print(f"TREND ANALYSIS FOR {ticker}")
    print(f"{'='*80}")
    
    traces = data.get('steps', [])
    
    # Initialize analyzer
    analyzer = TrendAnalyzer(ticker)
    
    # Process traces
    for trace in traces:
        analyzer.process_trace(trace)
    
    # Run analyses
    analyzer.analyze_trend_patterns()
    analyzer.analyze_window_effectiveness()
    analyzer.analyze_trend_accuracy()
    analyzer.analyze_momentum_patterns()
    analyzer.analyze_performance_metrics()
    analyzer.generate_recommendations()


class TrendAnalyzer:
    """Comprehensive trend analysis"""
    
    def __init__(self, target_ticker: str):
        self.target_ticker = target_ticker
        
        # Trend tracking
        self.trend_events = []
        self.trend_detections = []
        self.window_analyses = []
        
        # Price and volume tracking
        self.price_history = []
        self.volume_history = []
        self.momentum_data = []
        
        # Performance tracking
        self.detection_timings = []
        self.initialization_events = []
        self.cleanup_events = []
        
        # Window tracking
        self.window_states = defaultdict(dict)
        self.daily_resets = []
        
    def process_trace(self, trace: Dict):
        """Process individual trace entry"""
        ticker = trace.get('ticker', '')
        action = trace.get('action', '')
        timestamp = trace.get('timestamp', 0)
        data = trace.get('data', {})
        component = trace.get('component', '')
        
        # Handle string data
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except:
                data = {}
        
        details = data.get('details', {})
        
        # Track price/volume data
        if ticker == self.target_ticker and action == 'tick_created':
            price = data.get('price', 0)
            volume = data.get('volume', 0)
            if price > 0:
                self.price_history.append({
                    'timestamp': timestamp,
                    'price': price,
                    'volume': volume
                })
        
        # Track trend-specific actions
        if 'trend' in action.lower() or details.get('event_type') == 'trend':
            if action == 'event_detected' and details.get('event_type') == 'trend':
                self.trend_events.append({
                    'timestamp': timestamp,
                    'event_id': details.get('event_id'),
                    'ticker': ticker,
                    'direction': details.get('direction', 'unknown'),
                    'strength': details.get('strength', 0),
                    'confidence': details.get('confidence', 0),
                    'window_size': details.get('window_size', 0)
                })
            
            elif action == 'trend_detected':
                self.trend_detections.append({
                    'timestamp': timestamp,
                    'ticker': ticker,
                    'details': details
                })
            
            elif action == 'window_analysis_start':
                self.window_analyses.append({
                    'start_time': timestamp,
                    'window_size': details.get('window_size', 0),
                    'ticker': ticker,
                    'type': 'start'
                })
            
            elif action == 'window_analysis_complete':
                self.window_analyses.append({
                    'end_time': timestamp,
                    'duration_ms': data.get('duration_ms', 0),
                    'ticker': ticker,
                    'type': 'complete',
                    'result': details
                })
            
            elif action == 'initialization_complete' and component == 'TrendDetector':
                self.initialization_events.append({
                    'timestamp': timestamp,
                    'settings': details
                })
            
            elif action == 'daily_counts_reset':
                self.daily_resets.append({
                    'timestamp': timestamp,
                    'counts_before': details.get('counts_before', {}),
                    'ticker': ticker
                })
            
            elif action == 'cleanup_complete':
                self.cleanup_events.append({
                    'timestamp': timestamp,
                    'cleaned': details.get('cleaned_count', 0)
                })
            
            elif action == 'detection_slow':
                self.detection_timings.append({
                    'timestamp': timestamp,
                    'duration_ms': data.get('duration_ms', 0),
                    'threshold_ms': details.get('threshold_ms', 50)
                })
        
        # Track momentum calculations
        if 'momentum' in str(details).lower():
            self.momentum_data.append({
                'timestamp': timestamp,
                'momentum': details.get('momentum', 0),
                'ticker': ticker
            })
    
    def analyze_trend_patterns(self):
        """Analyze trend detection patterns"""
        print("\n[TREND] TREND DETECTION PATTERNS")
        print("-" * 60)
        
        if not self.trend_events:
            print("No trend events detected")
            return
        
        print(f"Total trend events: {len(self.trend_events)}")
        
        # Analyze by direction
        direction_counts = defaultdict(int)
        strength_by_direction = defaultdict(list)
        
        for event in self.trend_events:
            direction = event['direction']
            direction_counts[direction] += 1
            
            if event['strength'] > 0:
                strength_by_direction[direction].append(event['strength'])
        
        print("\nTrend directions:")
        for direction, count in sorted(direction_counts.items()):
            pct = count / len(self.trend_events) * 100
            print(f"  {direction}: {count} ({pct:.1f}%)")
            
            # Show average strength
            if direction in strength_by_direction:
                strengths = strength_by_direction[direction]
                avg_strength = sum(strengths) / len(strengths)
                print(f"    Average strength: {avg_strength:.2f}")
        
        # Analyze confidence levels
        confidences = [e['confidence'] for e in self.trend_events if e['confidence'] > 0]
        if confidences:
            avg_confidence = sum(confidences) / len(confidences)
            high_confidence = sum(1 for c in confidences if c > 0.8)
            
            print(f"\nConfidence analysis:")
            print(f"  Average confidence: {avg_confidence:.2f}")
            print(f"  High confidence (>0.8): {high_confidence}/{len(confidences)}")
        
        # Trend duration analysis
        self._analyze_trend_durations()
    
    def _analyze_trend_durations(self):
        """Analyze how long trends last"""
        if len(self.trend_events) < 2:
            return
        
        print("\n[DURATION] Trend Duration Analysis:")
        
        # Sort by timestamp
        sorted_events = sorted(self.trend_events, key=lambda x: x['timestamp'])
        
        # Group consecutive trends by direction
        trend_segments = []
        current_segment = {
            'direction': sorted_events[0]['direction'],
            'start': sorted_events[0]['timestamp'],
            'end': sorted_events[0]['timestamp'],
            'count': 1
        }
        
        for i in range(1, len(sorted_events)):
            event = sorted_events[i]
            
            if event['direction'] == current_segment['direction']:
                # Continue current trend
                current_segment['end'] = event['timestamp']
                current_segment['count'] += 1
            else:
                # New trend direction
                if current_segment['count'] > 1:
                    trend_segments.append(current_segment)
                
                current_segment = {
                    'direction': event['direction'],
                    'start': event['timestamp'],
                    'end': event['timestamp'],
                    'count': 1
                }
        
        # Add last segment
        if current_segment['count'] > 1:
            trend_segments.append(current_segment)
        
        if trend_segments:
            # Calculate durations
            durations_by_direction = defaultdict(list)
            
            for segment in trend_segments:
                duration = segment['end'] - segment['start']
                durations_by_direction[segment['direction']].append(duration)
            
            # Print statistics
            for direction, durations in durations_by_direction.items():
                if durations:
                    avg_duration = sum(durations) / len(durations)
                    max_duration = max(durations)
                    
                    print(f"\n  {direction} trends:")
                    print(f"    Count: {len(durations)}")
                    print(f"    Avg duration: {avg_duration:.1f}s")
                    print(f"    Max duration: {max_duration:.1f}s")
    
    def analyze_window_effectiveness(self):
        """Analyze sliding window effectiveness"""
        print("\n[WINDOW] SLIDING WINDOW ANALYSIS")
        print("-" * 60)
        
        if not self.window_analyses:
            print("No window analysis data found")
            return
        
        # Match start/complete pairs
        complete_analyses = []
        starts = [w for w in self.window_analyses if w['type'] == 'start']
        completes = [w for w in self.window_analyses if w['type'] == 'complete']
        
        print(f"Window analyses started: {len(starts)}")
        print(f"Window analyses completed: {len(completes)}")
        
        # Analyze completion times
        if completes:
            durations = [w['duration_ms'] for w in completes if w['duration_ms'] > 0]
            if durations:
                avg_duration = sum(durations) / len(durations)
                print(f"\nWindow analysis performance:")
                print(f"  Average duration: {avg_duration:.1f}ms")
                print(f"  Min: {min(durations):.1f}ms")
                print(f"  Max: {max(durations):.1f}ms")
                
                slow_windows = sum(1 for d in durations if d > 100)
                if slow_windows > 0:
                    print(f"  ⚠️  Slow analyses: {slow_windows} (>100ms)")
        
        # Analyze window sizes used
        window_sizes = defaultdict(int)
        for start in starts:
            size = start.get('window_size', 0)
            if size > 0:
                window_sizes[size] += 1
        
        if window_sizes:
            print("\nWindow sizes used:")
            for size, count in sorted(window_sizes.items()):
                print(f"  {size} ticks: {count} times")
        
        # Check daily resets
        if self.daily_resets:
            print(f"\nDaily resets: {len(self.daily_resets)}")
            
            # Analyze data lost in resets
            total_lost = 0
            for reset in self.daily_resets:
                counts = reset.get('counts_before', {})
                total_lost += sum(counts.values())
            
            if total_lost > 0:
                print(f"  Total data points reset: {total_lost}")
    
    def analyze_trend_accuracy(self):
        """Analyze trend detection accuracy"""
        print("\n[ACCURACY] TREND ACCURACY ANALYSIS")
        print("-" * 60)
        
        if not self.trend_events or not self.price_history:
            print("Insufficient data for accuracy analysis")
            return
        
        # Sort price history
        self.price_history.sort(key=lambda x: x['timestamp'])
        
        # For each trend event, check if trend continued
        correct_predictions = 0
        total_checked = 0
        
        for event in self.trend_events[:20]:  # Sample first 20
            trend_time = event['timestamp']
            direction = event['direction']
            
            if direction not in ['up', 'down', 'bullish', 'bearish']:
                continue
            
            # Find price at trend detection
            trend_price = None
            for i, price_data in enumerate(self.price_history):
                if price_data['timestamp'] >= trend_time:
                    trend_price = price_data['price']
                    
                    # Look ahead 50 ticks
                    future_prices = []
                    for j in range(i + 1, min(i + 51, len(self.price_history))):
                        future_prices.append(self.price_history[j]['price'])
                    
                    if len(future_prices) >= 10:
                        avg_future = sum(future_prices[:10]) / 10
                        
                        # Check if prediction was correct
                        if direction in ['up', 'bullish']:
                            if avg_future > trend_price * 1.001:  # 0.1% up
                                correct_predictions += 1
                        else:  # down/bearish
                            if avg_future < trend_price * 0.999:  # 0.1% down
                                correct_predictions += 1
                        
                        total_checked += 1
                    break
        
        if total_checked > 0:
            accuracy = correct_predictions / total_checked * 100
            print(f"Trend prediction accuracy: {accuracy:.1f}% ({correct_predictions}/{total_checked})")
            
            if accuracy < 60:
                print("  ⚠️  Low accuracy - review trend detection algorithm")
            elif accuracy > 80:
                print("  ✅ High accuracy - trend detection is effective")
        
        # Analyze false signals
        self._analyze_false_signals()
    
    def _analyze_false_signals(self):
        """Analyze potential false trend signals"""
        if len(self.trend_events) < 10:
            return
        
        print("\n[SIGNAL] Signal Quality Analysis:")
        
        # Check for trend reversals (rapid direction changes)
        sorted_events = sorted(self.trend_events, key=lambda x: x['timestamp'])
        
        rapid_reversals = 0
        for i in range(1, len(sorted_events)):
            time_gap = sorted_events[i]['timestamp'] - sorted_events[i-1]['timestamp']
            
            if time_gap < 60:  # Within 1 minute
                prev_dir = sorted_events[i-1]['direction']
                curr_dir = sorted_events[i]['direction']
                
                # Check if opposite directions
                if ((prev_dir in ['up', 'bullish'] and curr_dir in ['down', 'bearish']) or
                    (prev_dir in ['down', 'bearish'] and curr_dir in ['up', 'bullish'])):
                    rapid_reversals += 1
        
        if rapid_reversals > 0:
            reversal_rate = rapid_reversals / (len(sorted_events) - 1) * 100
            print(f"  Rapid reversals: {rapid_reversals} ({reversal_rate:.1f}%)")
            
            if reversal_rate > 20:
                print("  ⚠️  High reversal rate - possible noise in detection")
    
    def analyze_momentum_patterns(self):
        """Analyze momentum calculations"""
        print("\n[MOMENTUM] MOMENTUM ANALYSIS")
        print("-" * 60)
        
        if not self.momentum_data:
            print("No momentum data found")
            return
        
        momentums = [m['momentum'] for m in self.momentum_data if m['momentum'] != 0]
        
        if momentums:
            avg_momentum = sum(momentums) / len(momentums)
            positive = sum(1 for m in momentums if m > 0)
            negative = sum(1 for m in momentums if m < 0)
            
            print(f"Momentum calculations: {len(momentums)}")
            print(f"Average momentum: {avg_momentum:.4f}")
            print(f"Positive: {positive} ({positive/len(momentums)*100:.1f}%)")
            print(f"Negative: {negative} ({negative/len(momentums)*100:.1f}%)")
            
            # Check momentum distribution
            if momentums:
                abs_momentums = [abs(m) for m in momentums]
                high_momentum = sum(1 for m in abs_momentums if m > 0.01)
                
                print(f"\nMomentum strength:")
                print(f"  High momentum (>1%): {high_momentum}")
                print(f"  Max momentum: {max(abs_momentums):.4f}")
    
    def analyze_performance_metrics(self):
        """Analyze trend detection performance"""
        print("\n[PERF] PERFORMANCE METRICS")
        print("-" * 60)
        
        # Initialization analysis
        if self.initialization_events:
            print(f"Trend detector initializations: {len(self.initialization_events)}")
            
            for init in self.initialization_events[:1]:  # Show first
                settings = init.get('settings', {})
                if settings:
                    print("  Settings:")
                    for key, value in settings.items():
                        print(f"    {key}: {value}")
        
        # Detection timing
        if self.detection_timings:
            durations = [t['duration_ms'] for t in self.detection_timings]
            avg_duration = sum(durations) / len(durations)
            
            print(f"\nDetection performance:")
            print(f"  Slow detections: {len(durations)}")
            print(f"  Average duration: {avg_duration:.1f}ms")
            
            if avg_duration > 100:
                print("  ⚠️  Consider optimizing trend calculations")
        
        # Cleanup effectiveness
        if self.cleanup_events:
            total_cleaned = sum(e['cleaned'] for e in self.cleanup_events)
            print(f"\nMemory management:")
            print(f"  Cleanup events: {len(self.cleanup_events)}")
            print(f"  Total entries cleaned: {total_cleaned}")
    
    def generate_recommendations(self):
        """Generate recommendations based on analysis"""
        print("\n[TIP] RECOMMENDATIONS")
        print("-" * 60)
        
        recommendations = []
        
        # Check trend balance
        if self.trend_events:
            direction_counts = defaultdict(int)
            for event in self.trend_events:
                direction_counts[event['direction']] += 1
            
            # Check for imbalance
            if 'up' in direction_counts and 'down' in direction_counts:
                ratio = direction_counts['up'] / direction_counts['down']
                if ratio > 2 or ratio < 0.5:
                    recommendations.append({
                        'priority': 'MEDIUM',
                        'issue': f'Biased trend detection (up/down ratio: {ratio:.2f})',
                        'action': 'Review trend detection thresholds'
                    })
        
        # Check window performance
        if self.window_analyses:
            completes = [w for w in self.window_analyses if w['type'] == 'complete']
            if completes:
                slow_pct = sum(1 for w in completes if w.get('duration_ms', 0) > 100) / len(completes) * 100
                if slow_pct > 20:
                    recommendations.append({
                        'priority': 'HIGH',
                        'issue': f'{slow_pct:.1f}% of window analyses are slow',
                        'action': 'Optimize sliding window calculations'
                    })
        
        # Check rapid reversals
        if len(self.trend_events) > 10:
            sorted_events = sorted(self.trend_events, key=lambda x: x['timestamp'])
            rapid_reversals = 0
            
            for i in range(1, len(sorted_events)):
                if sorted_events[i]['timestamp'] - sorted_events[i-1]['timestamp'] < 60:
                    prev_dir = sorted_events[i-1]['direction']
                    curr_dir = sorted_events[i]['direction']
                    if ((prev_dir in ['up', 'bullish'] and curr_dir in ['down', 'bearish']) or
                        (prev_dir in ['down', 'bearish'] and curr_dir in ['up', 'bullish'])):
                        rapid_reversals += 1
            
            if rapid_reversals > 5:
                recommendations.append({
                    'priority': 'MEDIUM',
                    'issue': f'{rapid_reversals} rapid trend reversals detected',
                    'action': 'Implement trend confirmation logic or increase window size'
                })
        
        # Check confidence levels
        if self.trend_events:
            low_confidence = sum(1 for e in self.trend_events if 0 < e['confidence'] < 0.5)
            if low_confidence > len(self.trend_events) * 0.3:
                recommendations.append({
                    'priority': 'LOW',
                    'issue': 'Many low-confidence trend detections',
                    'action': 'Consider filtering out low-confidence trends'
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
            print("\n✅ Trend detection is well-configured and performing efficiently")
        
        # Always include best practices
        print("\n[BEST] Best Practices:")
        print("  1. Use multiple timeframes for trend confirmation")
        print("  2. Combine price and volume for trend strength")
        print("  3. Implement adaptive window sizes based on volatility")
        print("  4. Consider market hours when analyzing trends")
        print("  5. Filter out noise with minimum trend duration")


def main():
    """Main entry point with command line argument handling"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Analyze trend detection and processing behavior',
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
    
    analyze_trend_behavior(args.filename, args.trace_path, args.ticker)

if __name__ == "__main__":
    main()