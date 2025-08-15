#!/usr/bin/env python3
"""
Trace Data Dump Utility
Provides comprehensive trace data analysis and dumping capabilities.
Can be used standalone or imported by other test scripts.
"""
import json
import sys
import os
from collections import defaultdict
from typing import Dict, List, Set, Optional
from datetime import datetime
import argparse

class TraceDumper:
    """Utility class for dumping and analyzing trace data"""
    
    def __init__(self, trace_file_path: str):
        self.trace_file_path = trace_file_path
        self.data = None
        self.traces = []
        self.load_trace_file()
    
    def load_trace_file(self):
        """Load trace file and extract traces"""
        if not os.path.exists(self.trace_file_path):
            raise FileNotFoundError(f"Trace file not found: {self.trace_file_path}")
        
        with open(self.trace_file_path, 'r') as f:
            self.data = json.load(f)
        
        # Handle both formats: steps and traces
        self.traces = self.data.get('steps', self.data.get('traces', []))
    
    def get_unique_components(self) -> Set[str]:
        """Get all unique component names in traces"""
        return set(trace.get('component', 'Unknown') for trace in self.traces)
    
    def get_unique_actions(self) -> Set[str]:
        """Get all unique action names in traces"""
        return set(trace.get('action', 'unknown') for trace in self.traces)
    
    def get_unique_tickers(self) -> Set[str]:
        """Get all unique tickers in traces"""
        return set(trace.get('ticker', 'UNKNOWN') for trace in self.traces)
    
    def get_component_actions(self) -> Dict[str, Set[str]]:
        """Get all actions grouped by component"""
        component_actions = defaultdict(set)
        for trace in self.traces:
            component = trace.get('component', 'Unknown')
            action = trace.get('action', 'unknown')
            component_actions[component].add(action)
        return dict(component_actions)
    
    def get_component_trace_counts(self) -> Dict[str, int]:
        """Get trace count for each component"""
        counts = defaultdict(int)
        for trace in self.traces:
            component = trace.get('component', 'Unknown')
            counts[component] += 1
        return dict(counts)
    
    def find_traces_by_component(self, component: str) -> List[dict]:
        """Find all traces for a specific component"""
        return [t for t in self.traces if t.get('component') == component]
    
    def find_traces_by_action(self, action: str) -> List[dict]:
        """Find all traces for a specific action"""
        return [t for t in self.traces if t.get('action') == action]
    
    def find_traces_by_ticker(self, ticker: str) -> List[dict]:
        """Find all traces for a specific ticker"""
        return [t for t in self.traces if t.get('ticker') == ticker]
    
    def dump_component_summary(self):
        """Dump summary of all components and their actions"""
        print("\n" + "="*80)
        print("COMPONENT SUMMARY")
        print("="*80)
        
        component_actions = self.get_component_actions()
        component_counts = self.get_component_trace_counts()
        
        # Sort by trace count descending
        sorted_components = sorted(component_counts.items(), key=lambda x: x[1], reverse=True)
        
        print(f"\nTotal Components: {len(sorted_components)}")
        print(f"Total Traces: {len(self.traces)}")
        
        for component, count in sorted_components:
            actions = sorted(component_actions.get(component, set()))
            print(f"\n📁 {component} ({count} traces)")
            print(f"   Actions: {', '.join(actions[:5])}")
            if len(actions) > 5:
                print(f"   ... and {len(actions) - 5} more actions")
    
    def dump_action_frequency(self):
        """Dump frequency of each action across all components"""
        action_counts = defaultdict(int)
        action_components = defaultdict(set)
        
        for trace in self.traces:
            action = trace.get('action', 'unknown')
            component = trace.get('component', 'Unknown')
            action_counts[action] += 1
            action_components[action].add(component)
        
        print("\n" + "="*80)
        print("ACTION FREQUENCY")
        print("="*80)
        
        sorted_actions = sorted(action_counts.items(), key=lambda x: x[1], reverse=True)
        
        print(f"\n{'Action':<40} {'Count':>10} {'Components'}")
        print("-" * 80)
        
        for action, count in sorted_actions[:20]:  # Top 20 actions
            components = list(action_components[action])[:3]
            comp_str = ', '.join(components)
            if len(action_components[action]) > 3:
                comp_str += f" +{len(action_components[action]) - 3}"
            print(f"{action:<40} {count:>10} {comp_str}")
    
    def dump_ticker_summary(self):
        """Dump summary by ticker"""
        ticker_counts = defaultdict(int)
        ticker_components = defaultdict(set)
        
        for trace in self.traces:
            ticker = trace.get('ticker', 'UNKNOWN')
            component = trace.get('component', 'Unknown')
            ticker_counts[ticker] += 1
            ticker_components[ticker].add(component)
        
        print("\n" + "="*80)
        print("TICKER SUMMARY")
        print("="*80)
        
        sorted_tickers = sorted(ticker_counts.items(), key=lambda x: x[1], reverse=True)
        
        print(f"\n{'Ticker':<20} {'Traces':>10} {'Components'}")
        print("-" * 80)
        
        for ticker, count in sorted_tickers:
            comp_count = len(ticker_components[ticker])
            print(f"{ticker:<20} {count:>10} {comp_count} components")
    
    def find_missing_expected_traces(self, expected_traces: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """Find which expected traces are missing"""
        component_actions = self.get_component_actions()
        missing = {}
        
        for component, expected_actions in expected_traces.items():
            actual_actions = component_actions.get(component, set())
            missing_actions = [a for a in expected_actions if a not in actual_actions]
            if missing_actions:
                missing[component] = missing_actions
        
        return missing
    
    def dump_raw_traces(self, limit: int = 10, component: str = None, action: str = None):
        """Dump raw trace data with optional filtering"""
        print("\n" + "="*80)
        print("RAW TRACE DATA")
        print("="*80)
        
        # Filter traces
        filtered_traces = self.traces
        if component:
            filtered_traces = [t for t in filtered_traces if t.get('component') == component]
        if action:
            filtered_traces = [t for t in filtered_traces if t.get('action') == action]
        
        print(f"\nShowing {min(limit, len(filtered_traces))} of {len(filtered_traces)} traces")
        if component:
            print(f"Filtered by component: {component}")
        if action:
            print(f"Filtered by action: {action}")
        
        for i, trace in enumerate(filtered_traces[:limit]):
            print(f"\n--- Trace {i+1} ---")
            print(f"Timestamp: {trace.get('timestamp', 'N/A')}")
            print(f"Component: {trace.get('component', 'Unknown')}")
            print(f"Action: {trace.get('action', 'unknown')}")
            print(f"Ticker: {trace.get('ticker', 'UNKNOWN')}")
            
            data = trace.get('data', {})
            if isinstance(data, dict):
                details = data.get('details', {})
                if details:
                    print(f"Details: {json.dumps(details, indent=2)}")
    
    def export_component_action_map(self, output_file: str = 'component_actions.json'):
        """Export component-action mapping to JSON file"""
        component_actions = self.get_component_actions()
        
        # Convert sets to lists for JSON serialization
        export_data = {
            'generated_at': datetime.now().isoformat(),
            'trace_file': self.trace_file_path,
            'total_traces': len(self.traces),
            'components': {}
        }
        
        for component, actions in component_actions.items():
            export_data['components'][component] = {
                'actions': sorted(list(actions)),
                'trace_count': len(self.find_traces_by_component(component))
            }
        
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"\nExported component-action map to: {output_file}")

def main():
    """Main entry point for standalone usage"""
    parser = argparse.ArgumentParser(
        description='Dump and analyze trace file data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s trace_all.json                    # Basic summary
  %(prog)s trace_all.json --actions          # Show action frequency
  %(prog)s trace_all.json --raw              # Show raw traces
  %(prog)s trace_all.json --raw --limit 50   # Show more raw traces
  %(prog)s trace_all.json --component WorkerPool  # Filter by component
  %(prog)s trace_all.json --export           # Export component-action map
        '''
    )
    
    parser.add_argument('trace_file', help='Path to trace JSON file')
    parser.add_argument('--actions', action='store_true', help='Show action frequency analysis')
    parser.add_argument('--tickers', action='store_true', help='Show ticker summary')
    parser.add_argument('--raw', action='store_true', help='Show raw trace data')
    parser.add_argument('--limit', type=int, default=10, help='Limit for raw trace output')
    parser.add_argument('--component', help='Filter by component name')
    parser.add_argument('--action', help='Filter by action name')
    parser.add_argument('--export', action='store_true', help='Export component-action map')
    parser.add_argument('--export-file', default='component_actions.json', help='Export filename')
    
    args = parser.parse_args()
    
    try:
        dumper = TraceDumper(args.trace_file)
        
        # Always show component summary
        dumper.dump_component_summary()
        
        if args.actions:
            dumper.dump_action_frequency()
        
        if args.tickers:
            dumper.dump_ticker_summary()
        
        if args.raw:
            dumper.dump_raw_traces(
                limit=args.limit,
                component=args.component,
                action=args.action
            )
        
        if args.export:
            dumper.export_component_action_map(args.export_file)
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()