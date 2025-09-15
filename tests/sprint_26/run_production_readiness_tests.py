"""
Production Readiness Test Suite Runner - Sprint 26
Comprehensive testing for critical production readiness components.

This test runner executes all production readiness tests with proper organization
and reporting for deployment validation.

Test Suite Coverage:
1. OHLCV Database Persistence Tests
2. Pattern Discovery API Integration Tests  
3. TickStockPL Redis Pub-Sub Integration Tests
4. WebSocket Real-Time Broadcasting Tests
5. Performance Benchmark Tests
6. Security and Authorization Tests
7. Error Handling and Recovery Tests

Usage:
    python tests/sprint_26/run_production_readiness_tests.py
    python tests/sprint_26/run_production_readiness_tests.py --performance-only
    python tests/sprint_26/run_production_readiness_tests.py --security-only
    python tests/sprint_26/run_production_readiness_tests.py --integration-only
"""

import sys
import os
import time
import argparse
import subprocess
from typing import List, Dict, Any
from dataclasses import dataclass
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))


@dataclass
class TestSuiteResult:
    """Test suite execution result."""
    suite_name: str
    test_file: str
    passed: int
    failed: int
    skipped: int
    duration: float
    exit_code: int
    output: str


class ProductionReadinessTestRunner:
    """Production readiness test suite runner."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.test_suites = {
            'database_persistence': {
                'name': 'OHLCV Database Persistence Tests',
                'file': 'tests/data_processing/sprint_26/test_market_data_service_persistence.py',
                'critical': True,
                'categories': ['database', 'persistence', 'performance']
            },
            'pattern_api_integration': {
                'name': 'Pattern Discovery API Integration Tests',
                'file': 'tests/api/rest/sprint_26/test_pattern_discovery_api_integration.py',
                'critical': True,
                'categories': ['api', 'integration', 'performance']
            },
            'redis_integration': {
                'name': 'TickStockPL Redis Pub-Sub Integration Tests',
                'file': 'tests/system_integration/sprint_26/test_tickstockpl_redis_integration.py',
                'critical': True,
                'categories': ['redis', 'integration', 'performance']
            },
            'websocket_broadcasting': {
                'name': 'WebSocket Real-Time Broadcasting Tests',
                'file': 'tests/websocket_communication/sprint_26/test_websocket_pattern_broadcasting.py',
                'critical': True,
                'categories': ['websocket', 'realtime', 'performance']
            },
            'performance_benchmarks': {
                'name': 'Performance Benchmark Tests',
                'file': 'tests/data_processing/sprint_26/test_performance_benchmarks.py',
                'critical': True,
                'categories': ['performance', 'benchmarks']
            },
            'security_tests': {
                'name': 'Security and Authorization Tests',
                'file': 'tests/websocket_communication/sprint_26/test_websocket_security.py',
                'critical': True,
                'categories': ['security', 'authentication', 'authorization']
            },
            'error_handling': {
                'name': 'Error Handling and Recovery Tests',
                'file': 'tests/system_integration/sprint_26/test_error_handling_recovery.py',
                'critical': True,
                'categories': ['error_handling', 'recovery', 'resilience']
            }
        }
        
        self.results = []
    
    def run_test_suite(self, suite_key: str, verbose: bool = True) -> TestSuiteResult:
        """Run a single test suite."""
        suite = self.test_suites[suite_key]
        test_file = self.project_root / suite['file']
        
        if not test_file.exists():
            print(f"❌ Test file not found: {test_file}")
            return TestSuiteResult(
                suite_name=suite['name'],
                test_file=str(test_file),
                passed=0,
                failed=1,
                skipped=0,
                duration=0,
                exit_code=1,
                output=f"Test file not found: {test_file}"
            )
        
        print(f"\n🧪 Running: {suite['name']}")
        print(f"📁 File: {suite['file']}")
        print("=" * 80)
        
        # Prepare pytest command
        cmd = [
            sys.executable, '-m', 'pytest',
            str(test_file),
            '-v',
            '--tb=short',
            '--disable-warnings',
            '--color=yes'
        ]
        
        if verbose:
            cmd.append('-s')
        
        # Run test suite
        start_time = time.time()
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout per suite
            )
            
            duration = time.time() - start_time
            
            # Parse pytest output
            output_lines = result.stdout.split('\n')
            passed, failed, skipped = self._parse_pytest_output(output_lines)
            
            # Create result
            test_result = TestSuiteResult(
                suite_name=suite['name'],
                test_file=suite['file'],
                passed=passed,
                failed=failed,
                skipped=skipped,
                duration=duration,
                exit_code=result.returncode,
                output=result.stdout + result.stderr
            )
            
            # Print summary
            status_icon = "✅" if result.returncode == 0 else "❌"
            print(f"\n{status_icon} {suite['name']}")
            print(f"   Passed: {passed}, Failed: {failed}, Skipped: {skipped}")
            print(f"   Duration: {duration:.2f}s")
            
            if result.returncode != 0 and verbose:
                print(f"\n📋 Error Output:")
                print(result.stderr)
            
            return test_result
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return TestSuiteResult(
                suite_name=suite['name'],
                test_file=suite['file'],
                passed=0,
                failed=1,
                skipped=0,
                duration=duration,
                exit_code=1,
                output=f"Test suite timed out after {duration:.2f}s"
            )
        
        except Exception as e:
            duration = time.time() - start_time
            return TestSuiteResult(
                suite_name=suite['name'],
                test_file=suite['file'],
                passed=0,
                failed=1,
                skipped=0,
                duration=duration,
                exit_code=1,
                output=f"Error running test suite: {str(e)}"
            )
    
    def _parse_pytest_output(self, output_lines: List[str]) -> tuple:
        """Parse pytest output to extract test counts."""
        passed, failed, skipped = 0, 0, 0
        
        for line in output_lines:
            if 'passed' in line and 'failed' in line:
                # Look for summary line like "5 failed, 10 passed, 2 skipped"
                parts = line.split()
                for i, part in enumerate(parts):
                    try:
                        count = int(part)
                        if i + 1 < len(parts):
                            next_word = parts[i + 1].lower()
                            if 'passed' in next_word:
                                passed = count
                            elif 'failed' in next_word:
                                failed = count
                            elif 'skipped' in next_word:
                                skipped = count
                    except ValueError:
                        continue
                break
            elif 'passed in' in line:
                # Look for line like "10 passed in 2.5s"
                parts = line.split()
                if len(parts) >= 1:
                    try:
                        passed = int(parts[0])
                    except ValueError:
                        pass
        
        return passed, failed, skipped
    
    def run_category_tests(self, category: str) -> List[TestSuiteResult]:
        """Run all test suites in a specific category."""
        category_results = []
        
        print(f"\n🏷️  Running {category.upper()} Tests")
        print("=" * 80)
        
        for suite_key, suite_config in self.test_suites.items():
            if category in suite_config['categories']:
                result = self.run_test_suite(suite_key)
                category_results.append(result)
        
        return category_results
    
    def run_all_tests(self, verbose: bool = True) -> List[TestSuiteResult]:
        """Run all production readiness test suites."""
        print("🚀 TICKSTOCK PRODUCTION READINESS TEST SUITE")
        print("=" * 80)
        print("Testing critical components for production deployment")
        print(f"Project Root: {self.project_root}")
        print(f"Test Suites: {len(self.test_suites)}")
        
        all_results = []
        
        for suite_key in self.test_suites.keys():
            result = self.run_test_suite(suite_key, verbose)
            all_results.append(result)
        
        return all_results
    
    def print_summary_report(self, results: List[TestSuiteResult]):
        """Print comprehensive test summary report."""
        print("\n" + "=" * 80)
        print("🏁 PRODUCTION READINESS TEST SUMMARY REPORT")
        print("=" * 80)
        
        total_passed = sum(r.passed for r in results)
        total_failed = sum(r.failed for r in results)
        total_skipped = sum(r.skipped for r in results)
        total_duration = sum(r.duration for r in results)
        
        # Overall status
        all_passed = all(r.exit_code == 0 for r in results)
        critical_failed = any(r.exit_code != 0 for r in results if self._is_critical_suite(r.suite_name))
        
        status_icon = "✅" if all_passed else "❌"
        readiness_status = "READY" if all_passed else ("CRITICAL ISSUES" if critical_failed else "WARNINGS")
        
        print(f"\n{status_icon} PRODUCTION READINESS STATUS: {readiness_status}")
        print(f"📊 OVERALL RESULTS: {total_passed} passed, {total_failed} failed, {total_skipped} skipped")
        print(f"⏱️  TOTAL DURATION: {total_duration:.2f}s")
        print(f"🧪 TEST SUITES RUN: {len(results)}")
        
        # Detailed results by category
        categories = ['performance', 'integration', 'security', 'database', 'error_handling']
        
        for category in categories:
            category_results = [r for r in results if self._suite_in_category(r.suite_name, category)]
            if category_results:
                category_passed = all(r.exit_code == 0 for r in category_results)
                category_icon = "✅" if category_passed else "❌"
                category_count = len(category_results)
                
                print(f"\n{category_icon} {category.upper()} TESTS ({category_count} suites)")
                for result in category_results:
                    suite_icon = "✅" if result.exit_code == 0 else "❌"
                    print(f"   {suite_icon} {result.suite_name}: {result.passed}P/{result.failed}F/{result.skipped}S ({result.duration:.1f}s)")
        
        # Critical Issues
        failed_results = [r for r in results if r.exit_code != 0]
        if failed_results:
            print(f"\n❌ CRITICAL ISSUES ({len(failed_results)} suites):")
            for result in failed_results:
                print(f"   • {result.suite_name}")
                if result.failed > 0:
                    print(f"     └─ {result.failed} test(s) failed")
        
        # Performance Summary
        perf_results = [r for r in results if 'performance' in self._get_suite_categories(r.suite_name)]
        if perf_results:
            print(f"\n⚡ PERFORMANCE VALIDATION:")
            for result in perf_results:
                perf_icon = "✅" if result.exit_code == 0 else "❌"
                print(f"   {perf_icon} {result.suite_name}: {result.duration:.2f}s")
        
        # Deployment Recommendations
        print(f"\n📋 DEPLOYMENT RECOMMENDATIONS:")
        if all_passed:
            print("   ✅ All tests passed - System ready for production deployment")
            print("   ✅ Performance requirements validated")
            print("   ✅ Security measures verified")
            print("   ✅ Error handling tested")
        else:
            if critical_failed:
                print("   ❌ CRITICAL: Do not deploy - Critical test failures detected")
                print("   🔧 Action Required: Fix failing tests before deployment")
            else:
                print("   ⚠️  WARNING: Minor issues detected - Review before deployment")
                print("   📝 Action Recommended: Address warnings for optimal performance")
        
        # Test Coverage Summary
        print(f"\n📈 TEST COVERAGE SUMMARY:")
        print(f"   🗄️  Database Persistence: {'✅ Tested' if any('database' in self._get_suite_categories(r.suite_name) for r in results) else '❌ Missing'}")
        print(f"   🔌 API Integration: {'✅ Tested' if any('api' in self._get_suite_categories(r.suite_name) for r in results) else '❌ Missing'}")
        print(f"   📡 WebSocket Communication: {'✅ Tested' if any('websocket' in self._get_suite_categories(r.suite_name) for r in results) else '❌ Missing'}")
        print(f"   🚀 Performance Benchmarks: {'✅ Tested' if any('performance' in self._get_suite_categories(r.suite_name) for r in results) else '❌ Missing'}")
        print(f"   🔒 Security Validation: {'✅ Tested' if any('security' in self._get_suite_categories(r.suite_name) for r in results) else '❌ Missing'}")
        print(f"   🛡️  Error Recovery: {'✅ Tested' if any('error_handling' in self._get_suite_categories(r.suite_name) for r in results) else '❌ Missing'}")
        
        return all_passed
    
    def _is_critical_suite(self, suite_name: str) -> bool:
        """Check if a test suite is marked as critical."""
        for suite_config in self.test_suites.values():
            if suite_config['name'] == suite_name:
                return suite_config.get('critical', False)
        return False
    
    def _suite_in_category(self, suite_name: str, category: str) -> bool:
        """Check if a suite belongs to a specific category."""
        for suite_config in self.test_suites.values():
            if suite_config['name'] == suite_name:
                return category in suite_config.get('categories', [])
        return False
    
    def _get_suite_categories(self, suite_name: str) -> List[str]:
        """Get categories for a test suite."""
        for suite_config in self.test_suites.values():
            if suite_config['name'] == suite_name:
                return suite_config.get('categories', [])
        return []


def main():
    """Main test runner entry point."""
    parser = argparse.ArgumentParser(description='TickStock Production Readiness Test Suite')
    parser.add_argument('--performance-only', action='store_true', help='Run only performance tests')
    parser.add_argument('--security-only', action='store_true', help='Run only security tests')
    parser.add_argument('--integration-only', action='store_true', help='Run only integration tests')
    parser.add_argument('--database-only', action='store_true', help='Run only database tests')
    parser.add_argument('--suite', type=str, help='Run specific test suite by key')
    parser.add_argument('--list-suites', action='store_true', help='List all available test suites')
    parser.add_argument('--quiet', action='store_true', help='Quiet output mode')
    
    args = parser.parse_args()
    
    runner = ProductionReadinessTestRunner()
    
    if args.list_suites:
        print("📋 Available Test Suites:")
        for key, suite in runner.test_suites.items():
            critical_marker = "🔴" if suite.get('critical') else "🟡"
            categories = ', '.join(suite['categories'])
            print(f"   {critical_marker} {key}: {suite['name']}")
            print(f"      Categories: {categories}")
            print(f"      File: {suite['file']}")
        return
    
    # Run specific category or suite
    if args.performance_only:
        results = runner.run_category_tests('performance')
    elif args.security_only:
        results = runner.run_category_tests('security')
    elif args.integration_only:
        results = runner.run_category_tests('integration')
    elif args.database_only:
        results = runner.run_category_tests('database')
    elif args.suite:
        if args.suite in runner.test_suites:
            result = runner.run_test_suite(args.suite, not args.quiet)
            results = [result]
        else:
            print(f"❌ Unknown test suite: {args.suite}")
            print("Use --list-suites to see available suites")
            return 1
    else:
        # Run all tests
        results = runner.run_all_tests(not args.quiet)
    
    # Print summary report
    all_passed = runner.print_summary_report(results)
    
    # Exit with appropriate code
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)