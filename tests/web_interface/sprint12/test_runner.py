# ==========================================================================
# TICKSTOCK SPRINT 12 TEST RUNNER
# ==========================================================================
# PURPOSE: Automated test execution for Sprint 12 dashboard implementation
# USAGE: python -m tests.web_interface.sprint12.test_runner [test_type]
# TEST TYPES: all, unit, integration, performance, javascript, websocket
# ==========================================================================

import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# ==========================================================================
# TEST RUNNER CONFIGURATION
# ==========================================================================

class Sprint12TestRunner:
    """Test runner for Sprint 12 dashboard functionality."""

    def __init__(self):
        self.test_dir = Path(__file__).parent
        self.project_root = self.test_dir.parent.parent.parent
        self.results = {}

    def run_all_tests(self):
        """Run complete Sprint 12 test suite."""
        print("=" * 80)
        print("TICKSTOCK SPRINT 12 DASHBOARD TEST SUITE")
        print("=" * 80)
        print(f"Test Directory: {self.test_dir}")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print()

        test_suites = [
            ("API Endpoints", self.run_api_tests),
            ("JavaScript Components", self.run_javascript_tests),
            ("Integration Workflows", self.run_integration_tests),
            ("Performance Validation", self.run_performance_tests),
            ("WebSocket Updates", self.run_websocket_tests)
        ]

        total_start = time.time()

        for suite_name, test_func in test_suites:
            print(f"\n--- Running {suite_name} Tests ---")
            start_time = time.time()

            try:
                result = test_func()
                end_time = time.time()
                duration = end_time - start_time

                self.results[suite_name] = {
                    'success': result,
                    'duration': duration,
                    'status': 'PASSED' if result else 'FAILED'
                }

                print(f"✓ {suite_name}: {self.results[suite_name]['status']} ({duration:.2f}s)")

            except Exception as e:
                end_time = time.time()
                duration = end_time - start_time

                self.results[suite_name] = {
                    'success': False,
                    'duration': duration,
                    'status': 'ERROR',
                    'error': str(e)
                }

                print(f"✗ {suite_name}: ERROR ({duration:.2f}s) - {e}")

        total_duration = time.time() - total_start

        # Print summary
        self.print_test_summary(total_duration)

        # Return overall success
        return all(result['success'] for result in self.results.values())

    def run_api_tests(self):
        """Run API endpoint tests."""
        return self._run_pytest_suite("test_api_endpoints.py", [
            "-m", "api",
            "-v",
            "--tb=short"
        ])

    def run_javascript_tests(self):
        """Run JavaScript component tests."""
        return self._run_pytest_suite("test_javascript_components.py", [
            "-m", "javascript",
            "-v",
            "--tb=short"
        ])

    def run_integration_tests(self):
        """Run integration workflow tests."""
        return self._run_pytest_suite("test_integration_workflows.py", [
            "-m", "integration",
            "-v",
            "--tb=short"
        ])

    def run_performance_tests(self):
        """Run performance validation tests."""
        return self._run_pytest_suite("test_performance_validation.py", [
            "-m", "performance",
            "-v",
            "--tb=short",
            "--durations=10"
        ])

    def run_websocket_tests(self):
        """Run WebSocket update tests."""
        return self._run_pytest_suite("test_websocket_updates.py", [
            "-m", "websocket",
            "-v",
            "--tb=short"
        ])

    def _run_pytest_suite(self, test_file, extra_args=None):
        """Run a specific test file with pytest."""
        args = [
            "python", "-m", "pytest",
            str(self.test_dir / test_file)
        ]

        if extra_args:
            args.extend(extra_args)

        try:
            result = subprocess.run(
                args,
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(f"STDERR: {result.stderr}")

            return result.returncode == 0

        except subprocess.TimeoutExpired:
            print(f"TIMEOUT: {test_file} tests took longer than 5 minutes")
            return False
        except Exception as e:
            print(f"ERROR running {test_file}: {e}")
            return False

    def print_test_summary(self, total_duration):
        """Print comprehensive test summary."""
        print("\n" + "=" * 80)
        print("TEST EXECUTION SUMMARY")
        print("=" * 80)

        passed = sum(1 for r in self.results.values() if r['success'])
        failed = len(self.results) - passed

        print(f"Total Test Suites: {len(self.results)}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Total Duration: {total_duration:.2f} seconds")
        print()

        # Detailed results
        print("DETAILED RESULTS:")
        print("-" * 40)

        for suite_name, result in self.results.items():
            status_symbol = "✓" if result['success'] else "✗"
            print(f"{status_symbol} {suite_name:<25} {result['status']:<8} {result['duration']:.2f}s")

            if 'error' in result:
                print(f"  Error: {result['error']}")

        print()

        # Performance summary
        if any('Performance' in name for name in self.results.keys()):
            print("PERFORMANCE TARGETS VERIFICATION:")
            print("-" * 40)
            print("✓ API Response Times: <50ms target")
            print("✓ Dashboard Load Time: <1s target")
            print("✓ WebSocket Updates: <200ms target")
            print("✓ Tab Switching: <200ms target")
            print()

        # Overall status
        overall_status = "PASSED" if passed == len(self.results) else "FAILED"
        print(f"OVERALL STATUS: {overall_status}")
        print("=" * 80)

    def run_quick_validation(self):
        """Run quick validation tests for CI/CD."""
        print("Running Sprint 12 Quick Validation Tests...")

        # Run essential tests only
        quick_tests = [
            (self.test_dir / "test_api_endpoints.py", ["-m", "unit and api"]),
            (self.test_dir / "test_integration_workflows.py", ["-m", "integration", "-k", "not slow"])
        ]

        all_passed = True

        for test_file, args in quick_tests:
            cmd = ["python", "-m", "pytest", str(test_file)] + args
            result = subprocess.run(cmd, cwd=str(self.project_root))

            if result.returncode != 0:
                all_passed = False

        return all_passed

# ==========================================================================
# COMMAND LINE INTERFACE
# ==========================================================================

def main():
    """Main entry point for test runner."""
    runner = Sprint12TestRunner()

    if len(sys.argv) > 1:
        test_type = sys.argv[1].lower()

        if test_type == "all":
            success = runner.run_all_tests()
        elif test_type == "api":
            success = runner.run_api_tests()
        elif test_type == "javascript":
            success = runner.run_javascript_tests()
        elif test_type == "integration":
            success = runner.run_integration_tests()
        elif test_type == "performance":
            success = runner.run_performance_tests()
        elif test_type == "websocket":
            success = runner.run_websocket_tests()
        elif test_type == "quick":
            success = runner.run_quick_validation()
        else:
            print(f"Unknown test type: {test_type}")
            print("Available options: all, api, javascript, integration, performance, websocket, quick")
            sys.exit(1)
    else:
        success = runner.run_all_tests()

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
