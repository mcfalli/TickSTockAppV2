#!/usr/bin/env python3
"""
Trace Analysis Orchestrator
Runs multiple trace analyses and generates comprehensive reports.
Part of the test_*trace*.py suite.
"""
import json
import sys
import os
import subprocess
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import io

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

class TraceOrchestrator:
    """Orchestrate multiple trace analyses"""
    
    def __init__(self):
        self.results = {}
        self.start_time = None
        self.end_time = None
        
        # Define analysis modules in execution order
        self.analysis_modules = [
            {
                'name': 'Format Validation',
                'script': 'test_trace_format_validator.py',
                'critical': True
            },
            {
                'name': 'Flow Validation',
                'script': 'test_trace_flow_validation.py',
                'critical': True
            },
            {
                'name': 'Coverage Analysis',
                'script': 'test_trace_coverage.py',
                'critical': False
            },
            {
                'name': 'User Connection Analysis',
                'script': 'test_trace_user_connections.py',
                'critical': False
            },
            {
                'name': 'Emission Timing',
                'script': 'test_trace_emission_timing.py',
                'critical': False
            },
            {
                'name': 'Emission Gap Analysis',
                'script': 'test_trace_emission_gap.py',
                'critical': False
            },
            {
                'name': 'Lost Events',
                'script': 'test_trace_lost_events.py',
                'critical': False
            },
            {
                'name': 'Statistical Analysis',
                'script': 'test_trace_statistical.py',
                'critical': False
            },
            {
                'name': 'HighLow Analysis',
                'script': 'test_trace_highlow_analysis.py',
                'critical': False
            },
            {
                'name': 'Surge Analysis',
                'script': 'test_trace_surge_analysis.py',
                'critical': False
            },
            {
                'name': 'Trend Analysis',
                'script': 'test_trace_trend_analysis.py',
                'critical': False
            },
            {
                'name': 'Diagnostics',
                'script': 'test_trace_diagnostics.py',
                'critical': False
            },
            {
                'name': 'System Health',
                'script': 'test_trace_system_health.py',
                'critical': False,
                'args': ['--no-live']  # Skip live tests in orchestration
            }
        ]
    
    def run_analysis(self, filename: str, trace_path: str = './logs/trace/', 
                    ticker: Optional[str] = None, modules: Optional[List[str]] = None):
        """Run orchestrated analysis"""
        print(f"{'='*80}")
        print("TRACE ANALYSIS ORCHESTRATOR")
        print(f"{'='*80}")
        print(f"Trace file: {filename}")
        print(f"Trace path: {trace_path}")
        if ticker:
            print(f"Ticker filter: {ticker}")
        print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}\n")
        
        self.start_time = datetime.now()
        
        # Filter modules if specified
        modules_to_run = self.analysis_modules
        if modules:
            modules_to_run = [m for m in self.analysis_modules 
                            if any(mod in m['script'] for mod in modules)]
        
        # Run each analysis
        for i, module in enumerate(modules_to_run, 1):
            print(f"\n{'='*80}")
            print(f"[{i}/{len(modules_to_run)}] Running {module['name']}")
            print(f"{'='*80}")
            
            success = self._run_module(module, filename, trace_path, ticker)
            
            self.results[module['name']] = {
                'success': success,
                'script': module['script'],
                'critical': module['critical']
            }
            
            # Stop if critical module fails
            if module['critical'] and not success:
                print(f"\n❌ Critical module '{module['name']}' failed. Stopping orchestration.")
                break
        
        self.end_time = datetime.now()
        
        # Generate final report
        self._generate_report()
        
        # Generate HTML visualization if all critical modules passed
        if all(r['success'] for r in self.results.values() if r['critical']):
            self._generate_visualization(filename, trace_path)
    
    def _run_module(self, module: Dict, filename: str, trace_path: str, 
                   ticker: Optional[str]) -> bool:
        """Run individual analysis module"""
        script_path = os.path.join(os.path.dirname(__file__), module['script'])
        
        # Build command
        cmd = ['python', script_path, filename, trace_path]
        
        # Add ticker for modules that support it
        ticker_aware_modules = [
            'test_trace_flow_validation.py',
            'test_trace_user_connections.py',
            'test_trace_surge_analysis.py'
        ]
        
        if ticker and module['script'] in ticker_aware_modules:
            cmd.append(ticker)
        
        # Add any module-specific args
        if 'args' in module:
            cmd.extend(module['args'])
        
        try:
            # Run the module
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',  # Specify UTF-8 encoding
                timeout=60
            )
            
            # Print output
            if result.stdout:
                print(result.stdout)
            
            if result.stderr:
                print(f"\n⚠️  Errors/Warnings:")
                print(result.stderr)
            
            return result.returncode == 0
            
        except subprocess.TimeoutExpired:
            print(f"\n❌ Module timed out after 60 seconds")
            return False
        except Exception as e:
            print(f"\n❌ Error running module: {e}")
            return False
    
    def _generate_report(self):
        """Generate orchestration report"""
        print(f"\n{'='*80}")
        print("ORCHESTRATION SUMMARY")
        print(f"{'='*80}")
        
        if self.start_time and self.end_time:
            duration = (self.end_time - self.start_time).total_seconds()
            print(f"Total duration: {duration:.1f} seconds")
        
        # Count results
        total = len(self.results)
        passed = sum(1 for r in self.results.values() if r['success'])
        failed = total - passed
        
        print(f"Modules run: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        
        # Success rate
        success_rate = (passed / total * 100) if total > 0 else 0
        print(f"Success rate: {success_rate:.1f}%")
        
        # Detailed results
        print(f"\nDetailed Results:")
        print(f"{'Module':<30} {'Status':<10} {'Type':<10}")
        print("-" * 50)
        
        for name, result in self.results.items():
            status = "✅ PASS" if result['success'] else "❌ FAIL"
            type_str = "Critical" if result['critical'] else "Optional"
            print(f"{name:<30} {status:<10} {type_str:<10}")
        
        # Overall health assessment
        print(f"\n{'='*80}")
        critical_passed = all(r['success'] for r in self.results.values() if r['critical'])
        
        if critical_passed and success_rate >= 90:
            print("🟢 OVERALL HEALTH: EXCELLENT")
        elif critical_passed and success_rate >= 75:
            print("🟡 OVERALL HEALTH: GOOD")
        elif critical_passed:
            print("🟠 OVERALL HEALTH: FAIR")
        else:
            print("🔴 OVERALL HEALTH: POOR")
        
        # Recommendations
        print(f"\nRecommendations:")
        if failed > 0:
            failed_modules = [name for name, r in self.results.items() if not r['success']]
            print(f"  1. Fix failing modules: {', '.join(failed_modules)}")
        
        if success_rate < 100:
            print(f"  2. Review trace quality and completeness")
        
        if not any('Visualization' in name for name in self.results):
            print(f"  3. Generate visualization report for better insights")
    
    def _generate_visualization(self, filename: str, trace_path: str):
        """Generate HTML visualization"""
        print(f"\n{'='*80}")
        print("Generating HTML Visualization...")
        print(f"{'='*80}")
        
        script_path = os.path.join(os.path.dirname(__file__), 'test_trace_visualization.py')
        
        try:
            result = subprocess.run(
                ['python', script_path, filename, trace_path],
                capture_output=True,
                text=True,
                encoding='utf-8',  # Specify UTF-8 encoding
                timeout=30
            )
            
            if result.returncode == 0:
                print("✅ HTML report generated successfully")
                if result.stdout:
                    print(result.stdout)
            else:
                print("❌ Failed to generate HTML report")
                if result.stderr:
                    print(result.stderr)
                    
        except Exception as e:
            print(f"❌ Error generating visualization: {e}")


def main():
    """Main entry point with command line argument handling"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Orchestrate multiple trace analyses',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s                           # Use default trace_all.json
  %(prog)s NVDA.json                 # Analyze specific file
  %(prog)s NVDA.json --ticker NVDA   # Filter by ticker
  %(prog)s --modules flow coverage   # Run specific modules only
        '''
    )
    
    parser.add_argument('filename', nargs='?', default='trace_all.json',
                       help='Trace filename with .json extension (default: trace_all.json)')
    parser.add_argument('trace_path', nargs='?', default='./logs/trace/',
                       help='Path to trace directory (default: ./logs/trace/)')
    parser.add_argument('--ticker', default=None,
                       help='Optional ticker filter')
    parser.add_argument('--modules', nargs='+', default=None,
                       help='Specific modules to run (e.g., flow coverage surge)')
    
    args = parser.parse_args()
    
    # Create orchestrator and run
    orchestrator = TraceOrchestrator()
    orchestrator.run_analysis(
        filename=args.filename,
        trace_path=args.trace_path,
        ticker=args.ticker,
        modules=args.modules
    )

if __name__ == "__main__":
    main()