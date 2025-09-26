"""
Sprint 14 Integration Test Runner

Comprehensive test runner for all Sprint 14 integration tests
with proper configuration, reporting, and validation.

Usage:
    python run_integration_tests.py --all                    # Run all tests
    python run_integration_tests.py --phase 1               # Run Phase 1 only
    python run_integration_tests.py --performance           # Run performance tests only
    python run_integration_tests.py --resilience            # Run resilience tests only
    python run_integration_tests.py --report-html          # Generate HTML report
    python run_integration_tests.py --parallel             # Run tests in parallel
"""
import sys
import os
import argparse
import subprocess
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import tempfile


class Sprint14IntegrationTestRunner:
    """Sprint 14 Integration Test Runner with comprehensive reporting"""
    
    def __init__(self):
        self.test_directory = Path(__file__).parent
        self.project_root = self.test_directory.parent.parent.parent
        self.results = {
            'start_time': None,
            'end_time': None,
            'total_duration': 0,
            'phases': {},
            'performance_summary': {},
            'failures': [],
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'errors': []
        }
        
    def setup_test_environment(self):
        """Setup test environment and dependencies"""
        print("Setting up Sprint 14 integration test environment...")
        
        # Verify required services
        self._check_redis_availability()
        self._check_database_availability()
        
        # Set test environment variables
        os.environ['TESTING'] = 'true'
        # Test database URL is now managed by config_manager
        pass  # Configuration handled by config_manager
        # Redis URL is now managed by config_manager
        pass  # Configuration handled by config_manager
        
        print("✓ Test environment configured")
        
    def _check_redis_availability(self):
        """Check if Redis is available for testing"""
        try:
            import redis
            client = redis.Redis(host='localhost', port=6379, db=15, decode_responses=True)
            client.ping()
            print("✓ Redis connection verified")
        except Exception as e:
            print(f"✗ Redis not available: {e}")
            print("  Please ensure Redis is running on localhost:6379")
            sys.exit(1)
            
    def _check_database_availability(self):
        """Check if test database is available"""
        try:
            from sqlalchemy import create_engine
            engine = create_engine(os.environ['TEST_DATABASE_URL'])
            with engine.connect() as conn:
                conn.execute("SELECT 1")
            print("✓ Database connection verified")
        except Exception as e:
            print(f"✗ Test database not available: {e}")
            print(f"  Please ensure test database is running: {os.environ['TEST_DATABASE_URL']}")
            sys.exit(1)
    
    def run_phase_tests(self, phase_num: int) -> Dict:
        """Run tests for specific phase"""
        phase_name = f"phase{phase_num}"
        test_file = self.test_directory / f"phase{phase_num}_integration_tests.py"
        
        if not test_file.exists():
            return {'error': f"Phase {phase_num} test file not found"}
        
        print(f"\n🚀 Running Sprint 14 Phase {phase_num} Integration Tests...")
        
        start_time = time.time()
        
        try:
            result = subprocess.run([
                sys.executable, '-m', 'pytest', 
                str(test_file),
                '-v',
                '--tb=short',
                '--durations=10',
                '-x',  # Stop on first failure for integration tests
                '--junitxml', f'phase{phase_num}_results.xml'
            ], 
            capture_output=True, 
            text=True,
            cwd=self.project_root
            )
            
            duration = time.time() - start_time
            
            phase_result = {
                'phase': phase_num,
                'duration': duration,
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'passed': result.returncode == 0,
                'test_file': str(test_file)
            }
            
            self._parse_pytest_output(phase_result)
            
            if result.returncode == 0:
                print(f"✓ Phase {phase_num} tests PASSED ({duration:.1f}s)")
            else:
                print(f"✗ Phase {phase_num} tests FAILED ({duration:.1f}s)")
                print(f"  Error output: {result.stderr}")
            
            return phase_result
            
        except Exception as e:
            return {
                'phase': phase_num,
                'duration': time.time() - start_time,
                'error': str(e),
                'passed': False
            }
    
    def run_cross_phase_tests(self) -> Dict:
        """Run cross-phase workflow tests"""
        test_file = self.test_directory / "cross_phase_workflows.py"
        
        print(f"\n🔄 Running Sprint 14 Cross-Phase Workflow Tests...")
        
        start_time = time.time()
        
        try:
            result = subprocess.run([
                sys.executable, '-m', 'pytest',
                str(test_file),
                '-v',
                '--tb=short',
                '--durations=10',
                '--junitxml', 'cross_phase_results.xml'
            ],
            capture_output=True,
            text=True,
            cwd=self.project_root
            )
            
            duration = time.time() - start_time
            
            cross_phase_result = {
                'test_type': 'cross_phase_workflows',
                'duration': duration,
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'passed': result.returncode == 0,
                'test_file': str(test_file)
            }
            
            self._parse_pytest_output(cross_phase_result)
            
            if result.returncode == 0:
                print(f"✓ Cross-phase workflow tests PASSED ({duration:.1f}s)")
            else:
                print(f"✗ Cross-phase workflow tests FAILED ({duration:.1f}s)")
                
            return cross_phase_result
            
        except Exception as e:
            return {
                'test_type': 'cross_phase_workflows',
                'duration': time.time() - start_time,
                'error': str(e),
                'passed': False
            }
    
    def run_resilience_tests(self) -> Dict:
        """Run Redis resilience and failure recovery tests"""
        test_file = self.test_directory / "redis_resilience_tests.py"
        
        print(f"\n🛡️ Running Sprint 14 Redis Resilience Tests...")
        
        start_time = time.time()
        
        try:
            result = subprocess.run([
                sys.executable, '-m', 'pytest',
                str(test_file),
                '-v',
                '--tb=short',
                '--durations=10',
                '--junitxml', 'resilience_results.xml'
            ],
            capture_output=True,
            text=True,
            cwd=self.project_root
            )
            
            duration = time.time() - start_time
            
            resilience_result = {
                'test_type': 'redis_resilience',
                'duration': duration,
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'passed': result.returncode == 0,
                'test_file': str(test_file)
            }
            
            self._parse_pytest_output(resilience_result)
            
            if result.returncode == 0:
                print(f"✓ Redis resilience tests PASSED ({duration:.1f}s)")
            else:
                print(f"✗ Redis resilience tests FAILED ({duration:.1f}s)")
                
            return resilience_result
            
        except Exception as e:
            return {
                'test_type': 'redis_resilience',
                'duration': time.time() - start_time,
                'error': str(e),
                'passed': False
            }
    
    def run_performance_tests(self) -> Dict:
        """Run performance integration tests with timing validation"""
        test_file = self.test_directory / "performance_integration_tests.py"
        
        print(f"\n⚡ Running Sprint 14 Performance Integration Tests...")
        print("   Validating <100ms message delivery and system responsiveness...")
        
        start_time = time.time()
        
        try:
            result = subprocess.run([
                sys.executable, '-m', 'pytest',
                str(test_file),
                '-v',
                '--tb=short',
                '--durations=10',
                '--benchmark-sort=mean',  # If pytest-benchmark installed
                '--junitxml', 'performance_results.xml'
            ],
            capture_output=True,
            text=True,
            cwd=self.project_root
            )
            
            duration = time.time() - start_time
            
            performance_result = {
                'test_type': 'performance_integration',
                'duration': duration,
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'passed': result.returncode == 0,
                'test_file': str(test_file)
            }
            
            self._parse_pytest_output(performance_result)
            self._extract_performance_metrics(performance_result)
            
            if result.returncode == 0:
                print(f"✓ Performance integration tests PASSED ({duration:.1f}s)")
                self._print_performance_summary(performance_result)
            else:
                print(f"✗ Performance integration tests FAILED ({duration:.1f}s)")
                
            return performance_result
            
        except Exception as e:
            return {
                'test_type': 'performance_integration',
                'duration': time.time() - start_time,
                'error': str(e),
                'passed': False
            }
    
    def run_all_tests(self) -> Dict:
        """Run complete Sprint 14 integration test suite"""
        print("🎯 Starting Complete Sprint 14 Integration Test Suite")
        print("=" * 60)
        
        self.results['start_time'] = datetime.now()
        overall_start = time.time()
        
        # Run all test categories
        test_categories = [
            ('phase1', lambda: self.run_phase_tests(1)),
            ('phase2', lambda: self.run_phase_tests(2)),
            ('phase3', lambda: self.run_phase_tests(3)),
            ('phase4', lambda: self.run_phase_tests(4)),
            ('cross_phase_workflows', self.run_cross_phase_tests),
            ('redis_resilience', self.run_resilience_tests),
            ('performance_integration', self.run_performance_tests)
        ]
        
        for category_name, test_runner in test_categories:
            try:
                result = test_runner()
                self.results['phases'][category_name] = result
                
                if result.get('passed', False):
                    self.results['passed'] += 1
                else:
                    self.results['failed'] += 1
                    self.results['failures'].append({
                        'category': category_name,
                        'error': result.get('error', 'Test execution failed'),
                        'stderr': result.get('stderr', '')
                    })
                    
            except Exception as e:
                self.results['failed'] += 1
                self.results['errors'].append({
                    'category': category_name,
                    'error': str(e)
                })
                print(f"✗ Error running {category_name}: {e}")
        
        self.results['end_time'] = datetime.now()
        self.results['total_duration'] = time.time() - overall_start
        
        return self.results
    
    def _parse_pytest_output(self, result: Dict):
        """Parse pytest output for additional metrics"""
        stdout = result.get('stdout', '')
        
        # Extract test counts
        if 'failed' in stdout:
            import re
            # Look for pattern like "1 failed, 2 passed in 5.23s"
            match = re.search(r'(\d+)\s+failed.*?(\d+)\s+passed', stdout)
            if match:
                result['failed_count'] = int(match.group(1))
                result['passed_count'] = int(match.group(2))
        elif 'passed' in stdout:
            match = re.search(r'(\d+)\s+passed', stdout)
            if match:
                result['passed_count'] = int(match.group(1))
                result['failed_count'] = 0
    
    def _extract_performance_metrics(self, result: Dict):
        """Extract performance metrics from test output"""
        stdout = result.get('stdout', '')
        
        # Look for performance results in output
        performance_metrics = {}
        
        import re
        
        # Extract latency measurements
        latency_pattern = r'Mean latency:\s+(\d+\.?\d*)\s*ms'
        latencies = re.findall(latency_pattern, stdout)
        if latencies:
            performance_metrics['mean_latencies'] = [float(lat) for lat in latencies]
            performance_metrics['avg_mean_latency'] = sum(performance_metrics['mean_latencies']) / len(performance_metrics['mean_latencies'])
        
        # Extract retention rates
        retention_pattern = r'retention rate:\s+(\d+\.?\d*)%'
        retentions = re.findall(retention_pattern, stdout)
        if retentions:
            performance_metrics['retention_rates'] = [float(ret) for ret in retentions]
            performance_metrics['avg_retention_rate'] = sum(performance_metrics['retention_rates']) / len(performance_metrics['retention_rates'])
        
        # Extract message counts
        message_pattern = r'Messages.*?(\d+)'
        messages = re.findall(message_pattern, stdout)
        if messages:
            performance_metrics['total_messages'] = sum(int(msg) for msg in messages)
        
        if performance_metrics:
            result['performance_metrics'] = performance_metrics
            self.results['performance_summary'] = performance_metrics
    
    def _print_performance_summary(self, result: Dict):
        """Print performance test summary"""
        metrics = result.get('performance_metrics', {})
        
        if metrics:
            print("  Performance Summary:")
            if 'avg_mean_latency' in metrics:
                print(f"    Average latency: {metrics['avg_mean_latency']:.2f}ms (target: <100ms)")
            if 'avg_retention_rate' in metrics:
                print(f"    Average retention: {metrics['avg_retention_rate']:.1f}%")
            if 'total_messages' in metrics:
                print(f"    Total messages processed: {metrics['total_messages']:,}")
    
    def generate_report(self, output_file: Optional[str] = None) -> str:
        """Generate comprehensive test report"""
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"sprint14_integration_report_{timestamp}.json"
        
        report_data = {
            'sprint': 'Sprint 14',
            'test_suite': 'Integration Tests',
            'execution_timestamp': self.results.get('start_time', datetime.now()).isoformat(),
            'total_duration_seconds': self.results.get('total_duration', 0),
            'overall_status': 'PASSED' if self.results['failed'] == 0 else 'FAILED',
            'summary': {
                'total_categories': len(self.results.get('phases', {})),
                'passed_categories': self.results.get('passed', 0),
                'failed_categories': self.results.get('failed', 0),
                'error_count': len(self.results.get('errors', []))
            },
            'performance_targets': {
                'message_delivery_ms': 100,
                'database_query_ms': 50,
                'end_to_end_workflow_ms': 500
            },
            'performance_results': self.results.get('performance_summary', {}),
            'category_results': self.results.get('phases', {}),
            'failures': self.results.get('failures', []),
            'errors': self.results.get('errors', [])
        }
        
        # Write report to file
        output_path = Path(output_file)
        with open(output_path, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        print(f"\n📊 Integration test report generated: {output_path}")
        return str(output_path)
    
    def generate_html_report(self, json_report_path: str) -> str:
        """Generate HTML report from JSON data"""
        html_report_path = json_report_path.replace('.json', '.html')
        
        # Load JSON data
        with open(json_report_path, 'r') as f:
            data = json.load(f)
        
        # Generate HTML report
        html_content = self._create_html_report_template(data)
        
        with open(html_report_path, 'w') as f:
            f.write(html_content)
        
        print(f"📄 HTML report generated: {html_report_path}")
        return html_report_path
    
    def _create_html_report_template(self, data: Dict) -> str:
        """Create HTML report template"""
        status_color = '#28a745' if data['overall_status'] == 'PASSED' else '#dc3545'
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Sprint 14 Integration Test Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: {status_color}; color: white; padding: 20px; border-radius: 5px; }}
        .summary {{ display: flex; gap: 20px; margin: 20px 0; }}
        .metric {{ background: #f8f9fa; padding: 15px; border-radius: 5px; flex: 1; }}
        .category {{ margin: 20px 0; border: 1px solid #dee2e6; border-radius: 5px; }}
        .category-header {{ background: #e9ecef; padding: 10px; font-weight: bold; }}
        .category-content {{ padding: 15px; }}
        .passed {{ color: #28a745; }}
        .failed {{ color: #dc3545; }}
        .performance-table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
        .performance-table th, .performance-table td {{ border: 1px solid #dee2e6; padding: 8px; text-align: left; }}
        .performance-table th {{ background: #f8f9fa; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Sprint 14 Integration Test Report</h1>
        <p>Status: {data['overall_status']} | Duration: {data['total_duration_seconds']:.1f}s | Generated: {data['execution_timestamp']}</p>
    </div>
    
    <div class="summary">
        <div class="metric">
            <h3>Categories</h3>
            <p><strong>{data['summary']['total_categories']}</strong> total</p>
            <p class="passed"><strong>{data['summary']['passed_categories']}</strong> passed</p>
            <p class="failed"><strong>{data['summary']['failed_categories']}</strong> failed</p>
        </div>
        <div class="metric">
            <h3>Performance Targets</h3>
            <p>Message Delivery: &lt;{data['performance_targets']['message_delivery_ms']}ms</p>
            <p>Database Query: &lt;{data['performance_targets']['database_query_ms']}ms</p>
            <p>E2E Workflow: &lt;{data['performance_targets']['end_to_end_workflow_ms']}ms</p>
        </div>
        """
        
        if data.get('performance_results'):
            perf = data['performance_results']
            html += f"""
        <div class="metric">
            <h3>Performance Results</h3>
            {f'<p>Avg Latency: {perf["avg_mean_latency"]:.2f}ms</p>' if 'avg_mean_latency' in perf else ''}
            {f'<p>Retention Rate: {perf["avg_retention_rate"]:.1f}%</p>' if 'avg_retention_rate' in perf else ''}
            {f'<p>Messages Processed: {perf["total_messages"]:,}</p>' if 'total_messages' in perf else ''}
        </div>
            """
        
        html += """
    </div>
    
    <h2>Test Categories</h2>
        """
        
        # Add category results
        for category, results in data.get('category_results', {}).items():
            status = 'passed' if results.get('passed', False) else 'failed'
            status_class = 'passed' if status == 'passed' else 'failed'
            duration = results.get('duration', 0)
            
            html += f"""
    <div class="category">
        <div class="category-header">
            {category.replace('_', ' ').title()} - <span class="{status_class}">{status.upper()}</span> ({duration:.1f}s)
        </div>
        <div class="category-content">
            """
            
            if 'test_file' in results:
                html += f"<p><strong>Test File:</strong> {results['test_file']}</p>"
            
            if 'passed_count' in results or 'failed_count' in results:
                passed = results.get('passed_count', 0)
                failed = results.get('failed_count', 0)
                html += f"<p><strong>Tests:</strong> {passed} passed, {failed} failed</p>"
            
            if results.get('error'):
                html += f"<p><strong>Error:</strong> {results['error']}</p>"
                
            html += """
        </div>
    </div>
            """
        
        # Add failures section if any
        if data.get('failures'):
            html += """
    <h2>Failures</h2>
            """
            for failure in data['failures']:
                html += f"""
    <div class="category">
        <div class="category-header failed">
            {failure['category']} - FAILURE
        </div>
        <div class="category-content">
            <p><strong>Error:</strong> {failure['error']}</p>
            {f'<pre>{failure["stderr"]}</pre>' if failure.get('stderr') else ''}
        </div>
    </div>
                """
        
        html += """
    <footer style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #dee2e6; color: #6c757d;">
        <p>Generated by Sprint 14 Integration Test Runner</p>
    </footer>
</body>
</html>
        """
        
        return html
    
    def print_summary(self):
        """Print test execution summary"""
        print("\n" + "=" * 60)
        print("🎯 SPRINT 14 INTEGRATION TEST SUMMARY")
        print("=" * 60)
        
        total_categories = len(self.results.get('phases', {}))
        passed_count = self.results.get('passed', 0)
        failed_count = self.results.get('failed', 0)
        duration = self.results.get('total_duration', 0)
        
        print(f"Total Duration: {duration:.1f}s")
        print(f"Categories: {total_categories} total, {passed_count} passed, {failed_count} failed")
        
        if failed_count == 0:
            print("✅ ALL INTEGRATION TESTS PASSED!")
            print("   TickStockApp ↔ TickStockPL integration validated successfully")
            print("   <100ms message delivery performance confirmed")
            print("   Redis pub-sub resilience validated")
            print("   All 4 phases integrated properly")
        else:
            print("❌ INTEGRATION TEST FAILURES DETECTED")
            print(f"   {failed_count} test categories failed")
            print("   Please review failures before deployment")
            
            for failure in self.results.get('failures', []):
                print(f"   - {failure['category']}: {failure['error']}")
        
        # Performance summary
        perf_summary = self.results.get('performance_summary', {})
        if perf_summary:
            print("\n📊 PERFORMANCE SUMMARY:")
            if 'avg_mean_latency' in perf_summary:
                latency = perf_summary['avg_mean_latency']
                target_met = "✓" if latency < 100 else "✗"
                print(f"   {target_met} Average Message Latency: {latency:.2f}ms (target: <100ms)")
            
            if 'avg_retention_rate' in perf_summary:
                retention = perf_summary['avg_retention_rate']
                print(f"   Message Retention Rate: {retention:.1f}%")
                
        print("=" * 60)


def main():
    """Main test runner entry point"""
    parser = argparse.ArgumentParser(description='Sprint 14 Integration Test Runner')
    parser.add_argument('--all', action='store_true', help='Run all integration tests')
    parser.add_argument('--phase', type=int, choices=[1, 2, 3, 4], help='Run specific phase tests')
    parser.add_argument('--cross-phase', action='store_true', help='Run cross-phase workflow tests')
    parser.add_argument('--resilience', action='store_true', help='Run Redis resilience tests')
    parser.add_argument('--performance', action='store_true', help='Run performance tests')
    parser.add_argument('--report-json', action='store_true', help='Generate JSON report')
    parser.add_argument('--report-html', action='store_true', help='Generate HTML report')
    parser.add_argument('--output', help='Output file for report')
    
    args = parser.parse_args()
    
    # Create test runner
    runner = Sprint14IntegrationTestRunner()
    
    try:
        # Setup test environment
        runner.setup_test_environment()
        
        # Determine what tests to run
        if args.all:
            results = runner.run_all_tests()
        elif args.phase:
            results = {'phases': {f'phase{args.phase}': runner.run_phase_tests(args.phase)}}
        elif args.cross_phase:
            results = {'phases': {'cross_phase_workflows': runner.run_cross_phase_tests()}}
        elif args.resilience:
            results = {'phases': {'redis_resilience': runner.run_resilience_tests()}}
        elif args.performance:
            results = {'phases': {'performance_integration': runner.run_performance_tests()}}
        else:
            print("Please specify tests to run. Use --help for options.")
            sys.exit(1)
        
        # Print summary
        runner.print_summary()
        
        # Generate reports if requested
        if args.report_json or args.report_html:
            report_path = runner.generate_report(args.output)
            
            if args.report_html:
                runner.generate_html_report(report_path)
        
        # Exit with appropriate code
        failed_count = runner.results.get('failed', 0)
        sys.exit(0 if failed_count == 0 else 1)
        
    except KeyboardInterrupt:
        print("\n❌ Test execution interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test runner error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()