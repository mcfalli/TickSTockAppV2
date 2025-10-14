"""
Sprint 10 Phase 2 Integration Test Runner
Comprehensive test runner for Redis Event Consumption and WebSocket Broadcasting tests.
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path


class TestRunner:
    """Test runner for Sprint 10 Phase 2 integration tests."""

    def __init__(self, test_dir: str | None = None):
        if test_dir:
            self.test_dir = Path(test_dir)
        else:
            self.test_dir = Path(__file__).parent

        self.test_categories = {
            'fixtures': 'fixtures.py',
            'redis_subscriber': 'test_redis_event_subscriber.py',
            'websocket_broadcaster': 'test_websocket_broadcaster.py',
            'end_to_end': 'test_end_to_end_integration.py',
            'performance': 'test_performance_and_resilience.py',
            'application': 'test_application_integration.py'
        }

    def run_category(self, category: str, verbose: bool = False, markers: str = None) -> dict:
        """Run tests for a specific category."""
        if category not in self.test_categories:
            raise ValueError(f"Unknown category: {category}")

        test_file = self.test_dir / self.test_categories[category]
        if not test_file.exists():
            raise FileNotFoundError(f"Test file not found: {test_file}")

        cmd = ['pytest', str(test_file)]

        if verbose:
            cmd.append('-v')

        if markers:
            cmd.extend(['-m', markers])

        # Add coverage if requested
        cmd.extend(['--tb=short', '--disable-warnings'])

        print(f"\\nRunning {category} tests...")
        print(f"Command: {' '.join(cmd)}")
        print("-" * 60)

        start_time = time.time()

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            elapsed = time.time() - start_time

            return {
                'category': category,
                'success': result.returncode == 0,
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'elapsed': elapsed
            }

        except Exception as e:
            return {
                'category': category,
                'success': False,
                'error': str(e),
                'elapsed': time.time() - start_time
            }

    def run_all_categories(self, verbose: bool = False, fail_fast: bool = False) -> dict:
        """Run all test categories."""
        results = {}
        total_start = time.time()

        for category in self.test_categories.keys():
            if category == 'fixtures':  # Skip fixtures - it's imported by other tests
                continue

            result = self.run_category(category, verbose)
            results[category] = result

            print(f"Category: {category}")
            print(f"Status: {'PASSED' if result['success'] else 'FAILED'}")
            print(f"Time: {result['elapsed']:.2f}s")

            if not result['success']:
                print("STDERR:", result.get('stderr', ''))
                if fail_fast:
                    break

            print("-" * 60)

        total_elapsed = time.time() - total_start

        # Summary
        passed = sum(1 for r in results.values() if r['success'])
        total = len(results)

        print(f"\\n{'='*60}")
        print("TEST SUMMARY")
        print(f"{'='*60}")
        print(f"Categories run: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Total time: {total_elapsed:.2f}s")

        if total > 0:
            print(f"Success rate: {passed/total*100:.1f}%")

        return {
            'results': results,
            'summary': {
                'total': total,
                'passed': passed,
                'failed': total - passed,
                'elapsed': total_elapsed,
                'success_rate': passed/total*100 if total > 0 else 0
            }
        }

    def run_performance_benchmarks(self, verbose: bool = False) -> dict:
        """Run performance-focused tests."""
        return self.run_category('performance', verbose, markers='not slow')

    def run_quick_smoke_tests(self, verbose: bool = False) -> dict:
        """Run quick smoke tests across all categories."""
        results = {}

        # Run a subset of tests from each category for quick validation
        smoke_tests = {
            'redis_subscriber': 'test_subscriber_initialization_and_startup',
            'websocket_broadcaster': 'test_broadcaster_initialization',
            'end_to_end': 'test_complete_pattern_alert_flow',
            'application': 'test_successful_service_initialization_sequence'
        }

        for category, test_name in smoke_tests.items():
            test_file = self.test_dir / self.test_categories[category]
            cmd = ['pytest', str(test_file), '-k', test_name, '-v' if verbose else '', '--tb=short']
            cmd = [c for c in cmd if c]  # Remove empty strings

            print(f"Running smoke test: {category}::{test_name}")

            start_time = time.time()
            result = subprocess.run(cmd, capture_output=True, text=True)
            elapsed = time.time() - start_time

            results[category] = {
                'success': result.returncode == 0,
                'elapsed': elapsed,
                'test': test_name
            }

            status = 'PASSED' if result['success'] else 'FAILED'
            print(f"{status} ({elapsed:.2f}s)")

        return results


def main():
    """Main entry point for test runner."""
    parser = argparse.ArgumentParser(description='Sprint 10 Phase 2 Integration Test Runner')
    parser.add_argument('--category', choices=['redis_subscriber', 'websocket_broadcaster',
                                              'end_to_end', 'performance', 'application'],
                       help='Run specific test category')
    parser.add_argument('--all', action='store_true', help='Run all test categories')
    parser.add_argument('--smoke', action='store_true', help='Run quick smoke tests')
    parser.add_argument('--performance', action='store_true', help='Run performance benchmarks')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--fail-fast', action='store_true', help='Stop on first failure')
    parser.add_argument('--test-dir', help='Test directory path')

    args = parser.parse_args()

    runner = TestRunner(args.test_dir)

    if args.smoke:
        print("Running smoke tests...")
        results = runner.run_quick_smoke_tests(args.verbose)
        success = all(r['success'] for r in results.values())
        sys.exit(0 if success else 1)

    elif args.performance:
        print("Running performance benchmarks...")
        result = runner.run_performance_benchmarks(args.verbose)
        sys.exit(0 if result['success'] else 1)

    elif args.category:
        print(f"Running {args.category} tests...")
        result = runner.run_category(args.category, args.verbose)
        if result['success']:
            print(f"\\n✅ {args.category} tests PASSED")
        else:
            print(f"\\n❌ {args.category} tests FAILED")
            print(result.get('stderr', ''))
        sys.exit(0 if result['success'] else 1)

    elif args.all:
        print("Running all integration tests...")
        results = runner.run_all_categories(args.verbose, args.fail_fast)
        success = results['summary']['failed'] == 0

        if success:
            print("\\n✅ ALL TESTS PASSED")
        else:
            print(f"\\n❌ {results['summary']['failed']} CATEGORIES FAILED")

        sys.exit(0 if success else 1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
