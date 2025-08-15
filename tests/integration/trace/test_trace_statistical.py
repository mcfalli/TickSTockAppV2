#!/usr/bin/env python3
"""
Trace Statistical Analysis
Performs statistical anomaly detection and pattern recognition.
Part of the test_*trace*.py suite.
"""
import json
import sys
import os
from collections import defaultdict, Counter
from datetime import datetime
import statistics
from typing import Dict, List, Set, Optional, Tuple

import io

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    
def analyze_statistical_patterns(filename='trace_all.json', trace_path='./logs/trace/'):
    """
    Perform statistical analysis on trace data.
    
    Args:
        filename: Full filename including .json extension
        trace_path: Path to trace directory
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
    print("STATISTICAL TRACE ANALYSIS")
    print(f"{'='*80}")
    
    traces = data.get('steps', [])
    
    # Initialize analyzers
    timing_analyzer = TimingAnomalyDetector()
    pattern_detector = PatternDetector()
    trend_analyzer = TrendAnalyzer()
    
    # Process traces
    for trace in traces:
        timing_analyzer.add_trace(trace)
        pattern_detector.add_trace(trace)
        trend_analyzer.add_trace(trace)
    
    # Run analyses
    print("\n[STATS] TIMING ANOMALY DETECTION")
    print("-" * 60)
    timing_analyzer.detect_anomalies()
    
    print("\n[PATTERN] PATTERN RECOGNITION")
    print("-" * 60)
    pattern_detector.detect_patterns()
    
    print("\n[TREND] TREND ANALYSIS")
    print("-" * 60)
    trend_analyzer.analyze_trends()


class TimingAnomalyDetector:
    """Detect timing anomalies using statistical methods"""
    
    def __init__(self):
        self.timing_data = defaultdict(list)
        self.interval_data = defaultdict(list)
        self.last_timestamp = {}
        
    def add_trace(self, trace):
        """Add trace for timing analysis"""
        action = trace.get('action', '')
        timestamp = trace.get('timestamp', 0)
        ticker = trace.get('ticker', '')
        component = trace.get('component', '')
        
        # Track timing for each action
        key = f"{component}.{action}"
        
        # Store intervals between same actions
        if key in self.last_timestamp:
            interval = timestamp - self.last_timestamp[key]
            self.interval_data[key].append(interval)
        
        self.last_timestamp[key] = timestamp
        
        # Track duration if available
        data = trace.get('data', {})
        if isinstance(data, dict) and 'duration_ms' in data:
            try:
                duration = float(data['duration_ms'])
                self.timing_data[key].append(duration)
            except (ValueError, TypeError):
                pass
    
    def detect_anomalies(self):
        """Detect timing anomalies using Z-score"""
        # Analyze durations
        print("Duration anomalies (Z-score > 3):")
        anomaly_count = 0
        
        for action, durations in self.timing_data.items():
            if len(durations) > 3:
                mean_duration = statistics.mean(durations)
                stdev = statistics.stdev(durations)
                
                if stdev > 0:
                    anomalies = []
                    for i, duration in enumerate(durations):
                        z_score = (duration - mean_duration) / stdev
                        if abs(z_score) > 3:
                            anomalies.append((i, duration, z_score))
                    
                    if anomalies:
                        anomaly_count += len(anomalies)
                        print(f"\n{action}:")
                        print(f"  Mean: {mean_duration:.1f}ms, StdDev: {stdev:.1f}ms")
                        for idx, duration, z in anomalies[:3]:
                            print(f"  - Index {idx}: {duration:.1f}ms (Z={z:.2f})")
        
        if anomaly_count == 0:
            print("  No significant duration anomalies detected")
        
        # Analyze intervals
        print("\n\nInterval anomalies (irregular timing):")
        irregular_count = 0
        
        for action, intervals in self.interval_data.items():
            if len(intervals) > 5:
                mean_interval = statistics.mean(intervals)
                stdev = statistics.stdev(intervals) if len(intervals) > 1 else 0
                
                if stdev > 0 and mean_interval > 0:
                    cv = stdev / mean_interval  # Coefficient of variation
                    
                    if cv > 0.5:  # High variability
                        irregular_count += 1
                        print(f"\n{action}:")
                        print(f"  Mean interval: {mean_interval:.2f}s")
                        print(f"  Coefficient of variation: {cv:.2f} (>0.5 indicates high variability)")
                        
                        # Show sample intervals
                        print(f"  Sample intervals: {[f'{i:.2f}s' for i in intervals[:5]]}")
        
        if irregular_count == 0:
            print("  No significant interval anomalies detected")


class PatternDetector:
    """Detect common patterns in trace sequences"""
    
    def __init__(self):
        self.action_sequences = []
        self.component_transitions = defaultdict(Counter)
        self.error_patterns = defaultdict(list)
        
    def add_trace(self, trace):
        """Add trace for pattern analysis"""
        action = trace.get('action', '')
        component = trace.get('component', '')
        timestamp = trace.get('timestamp', 0)
        
        # Track action sequences
        self.action_sequences.append({
            'action': action,
            'component': component,
            'timestamp': timestamp
        })
        
        # Track error patterns
        if any(err in action.lower() for err in ['error', 'failed', 'timeout', 'exception']):
            self.error_patterns[action].append({
                'timestamp': timestamp,
                'component': component,
                'data': trace.get('data', {})
            })
    
    def detect_patterns(self):
        """Detect patterns in trace data"""
        # Pattern 1: Common action sequences
        print("Common action sequences (3-grams):")
        sequences = []
        
        for i in range(len(self.action_sequences) - 2):
            seq = tuple(s['action'] for s in self.action_sequences[i:i+3])
            sequences.append(seq)
        
        seq_counter = Counter(sequences)
        common_sequences = seq_counter.most_common(5)
        
        for seq, count in common_sequences:
            if count > 2:
                print(f"  {' -> '.join(seq)}: {count} occurrences")
        
        # Pattern 2: Component interaction patterns
        print("\n\nComponent interaction patterns:")
        for i in range(1, len(self.action_sequences)):
            prev = self.action_sequences[i-1]
            curr = self.action_sequences[i]
            
            if prev['component'] != curr['component']:
                self.component_transitions[prev['component']][curr['component']] += 1
        
        # Show top transitions
        all_transitions = []
        for from_comp, to_comps in self.component_transitions.items():
            for to_comp, count in to_comps.items():
                all_transitions.append((from_comp, to_comp, count))
        
        all_transitions.sort(key=lambda x: x[2], reverse=True)
        
        for from_comp, to_comp, count in all_transitions[:5]:
            print(f"  {from_comp} -> {to_comp}: {count} transitions")
        
        # Pattern 3: Error clustering
        print("\n\nError patterns:")
        if self.error_patterns:
            for error_type, occurrences in self.error_patterns.items():
                print(f"\n{error_type}: {len(occurrences)} occurrences")
                
                # Check for temporal clustering
                if len(occurrences) > 1:
                    timestamps = [o['timestamp'] for o in occurrences]
                    intervals = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
                    
                    if intervals:
                        avg_interval = statistics.mean(intervals)
                        if avg_interval < 1.0:  # Errors within 1 second
                            print(f"  ⚠️  Clustered errors detected (avg interval: {avg_interval:.3f}s)")
        else:
            print("  No error patterns detected")
        
        # Pattern 4: Throughput patterns
        print("\n\nThroughput patterns:")
        self._analyze_throughput_patterns()
    
    def _analyze_throughput_patterns(self):
        """Analyze throughput patterns"""
        # Group actions by time windows (1 second buckets)
        time_buckets = defaultdict(int)
        
        if self.action_sequences:
            start_time = self.action_sequences[0]['timestamp']
            
            for seq in self.action_sequences:
                bucket = int(seq['timestamp'] - start_time)
                time_buckets[bucket] += 1
            
            # Find high/low throughput periods
            if time_buckets:
                throughputs = list(time_buckets.values())
                avg_throughput = statistics.mean(throughputs)
                
                high_periods = sum(1 for t in throughputs if t > avg_throughput * 1.5)
                low_periods = sum(1 for t in throughputs if t < avg_throughput * 0.5)
                
                print(f"  Average throughput: {avg_throughput:.1f} events/second")
                print(f"  High throughput periods: {high_periods}")
                print(f"  Low throughput periods: {low_periods}")
                
                # Check for periodic patterns
                if len(throughputs) > 10:
                    self._check_periodicity(throughputs)
    
    def _check_periodicity(self, values):
        """Check for periodic patterns in values"""
        # Simple autocorrelation check for common periods
        periods_to_check = [5, 10, 20, 30, 60]  # seconds
        
        for period in periods_to_check:
            if len(values) > period * 2:
                correlation = self._autocorrelation(values, period)
                if correlation > 0.5:
                    print(f"  📊 Potential {period}s periodic pattern detected (correlation: {correlation:.2f})")
    
    def _autocorrelation(self, values, lag):
        """Calculate autocorrelation at given lag"""
        n = len(values)
        if n <= lag:
            return 0
        
        mean = statistics.mean(values)
        
        c0 = sum((x - mean) ** 2 for x in values) / n
        ct = sum((values[i] - mean) * (values[i - lag] - mean) for i in range(lag, n)) / n
        
        return ct / c0 if c0 > 0 else 0


class TrendAnalyzer:
    """Analyze trends over time"""
    
    def __init__(self):
        self.metrics_over_time = defaultdict(list)
        self.event_counts = defaultdict(lambda: defaultdict(int))
        
    def add_trace(self, trace):
        """Add trace for trend analysis"""
        timestamp = trace.get('timestamp', 0)
        action = trace.get('action', '')
        
        # Track event counts over time (1-minute buckets)
        minute_bucket = int(timestamp / 60)
        self.event_counts[minute_bucket][action] += 1
        
        # Track specific metrics
        data = trace.get('data', {})
        if isinstance(data, dict):
            # Track queue sizes
            if 'queue_size' in data:
                self.metrics_over_time['queue_size'].append((timestamp, data['queue_size']))
            
            # Track processing times
            if 'duration_ms' in data:
                try:
                    duration = float(data['duration_ms'])
                    self.metrics_over_time['duration_ms'].append((timestamp, duration))
                except (ValueError, TypeError):
                    pass
            
            # Track event counts
            if 'output_count' in data:
                try:
                    count = int(data['output_count'])
                    self.metrics_over_time['output_count'].append((timestamp, count))
                except (ValueError, TypeError):
                    pass
    
    def analyze_trends(self):
        """Analyze trends in the data"""
        # Analyze event volume trends
        print("Event volume trends:")
        if self.event_counts:
            minutes = sorted(self.event_counts.keys())
            total_events_per_minute = [
                sum(self.event_counts[m].values()) for m in minutes
            ]
            
            if len(total_events_per_minute) > 2:
                # Calculate trend
                trend = self._calculate_trend(total_events_per_minute)
                
                print(f"  Total minutes analyzed: {len(minutes)}")
                print(f"  Average events/minute: {statistics.mean(total_events_per_minute):.1f}")
                print(f"  Trend: {trend}")
                
                # Check for significant changes
                self._detect_volume_changes(total_events_per_minute)
        
        # Analyze metric trends
        print("\n\nMetric trends:")
        for metric_name, values in self.metrics_over_time.items():
            if len(values) > 5:
                print(f"\n{metric_name}:")
                
                # Sort by timestamp
                values.sort(key=lambda x: x[0])
                metric_values = [v[1] for v in values]
                
                # Calculate statistics
                mean_val = statistics.mean(metric_values)
                median_val = statistics.median(metric_values)
                
                print(f"  Samples: {len(values)}")
                print(f"  Mean: {mean_val:.2f}")
                print(f"  Median: {median_val:.2f}")
                
                # Detect trend
                trend = self._calculate_trend(metric_values)
                print(f"  Trend: {trend}")
                
                # Check for outliers
                if len(metric_values) > 10:
                    outliers = self._detect_outliers(metric_values)
                    if outliers:
                        print(f"  Outliers detected: {len(outliers)} values")
    
    def _calculate_trend(self, values):
        """Calculate trend direction"""
        if len(values) < 3:
            return "insufficient data"
        
        # Simple linear regression
        n = len(values)
        x_values = list(range(n))
        
        x_mean = sum(x_values) / n
        y_mean = sum(values) / n
        
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, values))
        denominator = sum((x - x_mean) ** 2 for x in x_values)
        
        if denominator == 0:
            return "stable"
        
        slope = numerator / denominator
        
        # Determine trend based on slope
        if abs(slope) < 0.01:
            return "stable"
        elif slope > 0:
            return f"increasing (slope: {slope:.3f})"
        else:
            return f"decreasing (slope: {slope:.3f})"
    
    def _detect_volume_changes(self, volumes):
        """Detect significant changes in volume"""
        if len(volumes) < 3:
            return
        
        # Use rolling window to detect changes
        window_size = min(5, len(volumes) // 2)
        
        for i in range(window_size, len(volumes) - window_size):
            before = statistics.mean(volumes[i-window_size:i])
            after = statistics.mean(volumes[i:i+window_size])
            
            if before > 0:
                change_pct = ((after - before) / before) * 100
                
                if abs(change_pct) > 50:
                    direction = "increase" if change_pct > 0 else "decrease"
                    print(f"  ⚠️  Significant {direction} at minute {i}: {abs(change_pct):.1f}%")
    
    def _detect_outliers(self, values):
        """Detect outliers using IQR method"""
        sorted_values = sorted(values)
        q1 = sorted_values[len(sorted_values) // 4]
        q3 = sorted_values[3 * len(sorted_values) // 4]
        iqr = q3 - q1
        
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        outliers = [v for v in values if v < lower_bound or v > upper_bound]
        return outliers


def main():
    """Main entry point with command line argument handling"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Perform statistical analysis on trace data',
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
    
    analyze_statistical_patterns(args.filename, args.trace_path)

if __name__ == "__main__":
    main()