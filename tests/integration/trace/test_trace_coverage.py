#!/usr/bin/env python3
"""
Trace Coverage Analyzer
Analyzes trace coverage across all components and identifies gaps.
Part of the test_*trace*.py suite.
"""
import json
import sys
import os
from collections import defaultdict
from typing import Dict, List, Set, Optional
from datetime import datetime
import io

from trace_component_definitions import COMPONENT_REQUIREMENTS, get_actual_component_name

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def analyze_coverage(filename='trace_all.json', trace_path='./logs/trace/'):
    """
    Analyze component coverage in trace file.
    
    Args:
        filename: Full filename including .json extension
        trace_path: Path to trace directory
    """
    # Define expected components and their critical actions

    
    # Construct full path
    full_path = os.path.join(trace_path, filename)
    
    if not os.path.exists(full_path):
        print(f"Error: File not found: {full_path}")
        sys.exit(1)
    
    with open(full_path, 'r') as f:
        data = json.load(f)
    
    print(f"Analyzing: {full_path}")
    print(f"\n{'='*80}")
    print("TRACE COVERAGE ANALYSIS")
    print(f"{'='*80}")
    
    traces = data.get('steps', [])
    
    # Track component coverage
    coverage_data = defaultdict(lambda: {
        'traced_actions': set(),
        'trace_count': 0,
        'first_seen': None,
        'last_seen': None
    })
    
    # Process traces
    for trace in traces:
        component = trace.get('component', 'Unknown')
        action = trace.get('action', 'unknown')
        timestamp = trace.get('timestamp', 0)
        
        comp_data = coverage_data[component]
        comp_data['traced_actions'].add(action)
        comp_data['trace_count'] += 1
        
        if comp_data['first_seen'] is None or timestamp < comp_data['first_seen']:
            comp_data['first_seen'] = timestamp
        
        if comp_data['last_seen'] is None or timestamp > comp_data['last_seen']:
            comp_data['last_seen'] = timestamp
    
    # Analyze coverage
    total_expected = len(COMPONENT_REQUIREMENTS)
    total_traced = 0
    missing_components = []
    incomplete_components = []
    
    print(f"\nExpected Components: {total_expected}")
    print(f"Traced Components: {len(coverage_data)}")
    
    # Check each expected component
    print(f"\n{'Component':<25} {'Coverage':<10} {'Critical':<15} {'Status':<20}")
    print("-" * 70)
    
    for component, requirements in COMPONENT_REQUIREMENTS.items():
        if component in coverage_data:
            total_traced += 1
            comp_data = coverage_data[component]
            traced_actions = comp_data['traced_actions']
            
            # Check critical actions
            critical_actions = set(requirements['critical'])
            critical_traced = critical_actions.intersection(traced_actions)
            critical_coverage = (len(critical_traced) / len(critical_actions) * 100) if critical_actions else 100
            
            # Check all expected actions
            all_expected = critical_actions.union(set(requirements.get('expected', [])))
            total_coverage = (len(traced_actions.intersection(all_expected)) / len(all_expected) * 100) if all_expected else 0
            
            # Determine status
            if critical_coverage == 100:
                status = "✅ Complete"
            elif critical_coverage > 0:
                status = "⚠️  Partial"
                incomplete_components.append({
                    'component': component,
                    'missing_critical': list(critical_actions - traced_actions),
                    'coverage': critical_coverage
                })
            else:
                status = "❌ No Critical"
                incomplete_components.append({
                    'component': component,
                    'missing_critical': list(critical_actions),
                    'coverage': 0
                })
            
            print(f"{component:<25} {total_coverage:>6.1f}% {critical_coverage:>12.1f}% {status}")
            
        else:
            missing_components.append(component)
            print(f"{component:<25} {'0.0%':>6} {'0.0%':>12} ❌ Missing")
    
    # Summary
    print(f"\n{'='*80}")
    print("COVERAGE SUMMARY")
    print(f"{'='*80}")
    
    overall_coverage = (total_traced / total_expected * 100) if total_expected > 0 else 0
    print(f"\nOverall Coverage Score: {overall_coverage:.1f}%")
    print(f"Components with traces: {total_traced}/{total_expected}")
    
    if missing_components:
        print(f"\n⚠️  Missing Components ({len(missing_components)}):")
        for comp in missing_components:
            print(f"  - {comp}")
    
    if incomplete_components:
        print(f"\n⚠️  Incomplete Components ({len(incomplete_components)}):")
        for comp_info in incomplete_components:
            print(f"  - {comp_info['component']} ({comp_info['coverage']:.0f}% critical coverage)")
            for action in comp_info['missing_critical'][:3]:
                print(f"    Missing: {action}")
    
    # Unexpected components
    unexpected = []
    for component in coverage_data:
        if component not in COMPONENT_REQUIREMENTS and component != 'SYSTEM':
            unexpected.append(component)
    
    if unexpected:
        print(f"\n📝 Unexpected Components ({len(unexpected)}):")
        for comp in unexpected:
            print(f"  - {comp} ({coverage_data[comp]['trace_count']} traces)")
    
    # Recommendations
    print(f"\n💡 RECOMMENDATIONS")
    print("-" * 40)
    
    if missing_components:
        print(f"1. Add tracing to {len(missing_components)} missing components")
    
    if incomplete_components:
        critical_missing = sum(len(c['missing_critical']) for c in incomplete_components)
        print(f"2. Implement {critical_missing} missing critical trace points")
    
    if overall_coverage < 80:
        print("3. Aim for at least 80% component coverage")
    
    if not missing_components and not incomplete_components:
        print("✅ Excellent coverage! All critical components are traced.")
    
    # Coverage grade
    if overall_coverage >= 90:
        grade = "A"
    elif overall_coverage >= 80:
        grade = "B"
    elif overall_coverage >= 70:
        grade = "C"
    elif overall_coverage >= 60:
        grade = "D"
    else:
        grade = "F"
    
    print(f"\nCoverage Grade: {grade} ({overall_coverage:.1f}%)")

def main():
    """Main entry point with command line argument handling"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Analyze trace coverage across components',
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
    
    analyze_coverage(args.filename, args.trace_path)

if __name__ == "__main__":
    main()