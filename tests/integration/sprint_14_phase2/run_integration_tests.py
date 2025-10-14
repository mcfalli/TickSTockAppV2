#!/usr/bin/env python3
"""
Sprint 14 Phase 2 Integration Test Runner
Executes comprehensive integration tests for automation services with detailed reporting.

Usage:
    python run_integration_tests.py [--performance] [--full-suite] [--report-file output.json]

Date: 2025-09-01
Sprint: 14 Phase 2
"""

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class TestResult:
    """Individual test result structure"""
    test_name: str
    status: str  # passed, failed, skipped
    duration_ms: float
    error_message: str | None = None
    performance_data: dict[str, Any] | None = None

@dataclass
class IntegrationTestReport:
    """Comprehensive integration test report"""
    execution_timestamp: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    total_duration_seconds: float
    performance_summary: dict[str, Any]
    test_results: list[TestResult]
    environment_info: dict[str, Any]
    compliance_status: dict[str, bool]

class IntegrationTestRunner:
    """Runs and reports on Sprint 14 Phase 2 integration tests"""

    def __init__(self):
        self.test_dir = Path(__file__).parent
        self.results = []
        self.performance_data = {}
        self.start_time = None
        self.end_time = None

    def run_test_suite(self, test_type: str = 'standard') -> IntegrationTestReport:
        """
        Run integration test suite with specified configuration
        
        Args:
            test_type: 'standard', 'performance', or 'full'
            
        Returns:
            Comprehensive test report
        """
        print(f"🚀 Starting Sprint 14 Phase 2 Integration Tests ({test_type} suite)")
        print("=" * 80)

        self.start_time = time.time()

        # Configure test parameters based on type
        test_markers, test_files = self._get_test_configuration(test_type)

        # Run tests
        for test_category in test_files:
            category_results = self._run_test_category(test_category, test_markers.get(test_category, []))
            self.results.extend(category_results)

        self.end_time = time.time()

        # Generate comprehensive report
        report = self._generate_report()

        # Display summary
        self._display_summary(report)

        return report

    def _get_test_configuration(self, test_type: str) -> tuple[dict[str, list[str]], dict[str, str]]:
        """Get test configuration based on suite type"""

        base_files = {
            'redis_messaging': 'test_automation_services_integration_comprehensive.py::TestRedisMessageFlowIntegration',
            'database_integration': 'test_automation_services_integration_comprehensive.py::TestDatabaseIntegrationPatterns',
            'system_resilience': 'test_automation_services_integration_comprehensive.py::TestSystemResilienceAndFailover',
            'end_to_end': 'test_automation_services_integration_comprehensive.py::TestEndToEndWorkflowIntegration'
        }

        performance_files = {
            'performance_benchmarks': 'test_automation_services_integration_comprehensive.py::TestPerformanceBenchmarks'
        }

        markers = {
            'redis_messaging': ['redis', 'integration'],
            'database_integration': ['database', 'integration'],
            'system_resilience': ['resilience', 'integration'],
            'end_to_end': ['integration', 'slow'],
            'performance_benchmarks': ['performance', 'integration']
        }

        if test_type == 'standard':
            return markers, base_files
        if test_type == 'performance' or test_type == 'full':
            return markers, {**base_files, **performance_files}
        return markers, base_files

    def _run_test_category(self, category_name: str, test_markers: list[str]) -> list[TestResult]:
        """Run a specific test category"""
        print(f"\\n📋 Running {category_name} tests...")

        test_file = self._get_test_configuration('standard')[1].get(category_name, '')
        if not test_file:
            return []

        # Build pytest command
        cmd = [
            sys.executable, '-m', 'pytest',
            str(self.test_dir / test_file.split('::')[0]),
            '-v',
            '--tb=short',
            '--durations=10',
            f'-k {test_file.split("::")[-1]}' if '::' in test_file else '',
            '--json-report', '--json-report-file=/tmp/pytest_report.json'
        ]

        # Add markers
        if test_markers:
            cmd.extend(['-m', ' and '.join(test_markers)])

        # Remove empty arguments
        cmd = [arg for arg in cmd if arg.strip()]

        try:
            # Run tests
            result = subprocess.run(
                cmd,
                cwd=self.test_dir,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout per category
            )

            # Parse results
            category_results = self._parse_pytest_output(result, category_name)

            # Display category summary
            passed = len([r for r in category_results if r.status == 'passed'])
            failed = len([r for r in category_results if r.status == 'failed'])
            skipped = len([r for r in category_results if r.status == 'skipped'])

            print(f"  ✓ Passed: {passed}")
            print(f"  ✗ Failed: {failed}")
            print(f"  ⚠ Skipped: {skipped}")

            if result.returncode != 0 and failed > 0:
                print(f"  ⚠ Error output: {result.stderr[:200]}...")

            return category_results

        except subprocess.TimeoutExpired:
            print(f"  ⏰ Test category {category_name} timed out")
            return [TestResult(
                test_name=f"{category_name}_timeout",
                status="failed",
                duration_ms=300000,
                error_message="Test category timed out after 5 minutes"
            )]
        except Exception as e:
            print(f"  ❌ Error running {category_name}: {e}")
            return [TestResult(
                test_name=f"{category_name}_error",
                status="failed",
                duration_ms=0,
                error_message=str(e)
            )]

    def _parse_pytest_output(self, result: subprocess.CompletedProcess, category: str) -> list[TestResult]:
        """Parse pytest output into TestResult objects"""
        test_results = []

        # Try to parse JSON report if available
        json_report_path = '/tmp/pytest_report.json'
        if os.path.exists(json_report_path):
            try:
                with open(json_report_path) as f:
                    report_data = json.load(f)

                for test in report_data.get('tests', []):
                    test_results.append(TestResult(
                        test_name=test.get('nodeid', 'unknown'),
                        status=test.get('outcome', 'unknown'),
                        duration_ms=test.get('duration', 0) * 1000,
                        error_message=test.get('call', {}).get('longrepr')
                    ))

                return test_results
            except Exception as e:
                print(f"  ⚠ Could not parse JSON report: {e}")

        # Fallback: parse text output
        lines = result.stdout.split('\\n')

        for line in lines:
            if '::' in line and any(marker in line for marker in ['PASSED', 'FAILED', 'SKIPPED']):
                parts = line.split(' ')
                test_name = parts[0] if parts else 'unknown'

                if 'PASSED' in line:
                    status = 'passed'
                elif 'FAILED' in line:
                    status = 'failed'
                else:
                    status = 'skipped'

                # Extract duration if available
                duration_ms = 0
                for part in parts:
                    if 's]' in part:
                        try:
                            duration_ms = float(part.replace('[', '').replace('s]', '')) * 1000
                        except:
                            pass

                test_results.append(TestResult(
                    test_name=test_name,
                    status=status,
                    duration_ms=duration_ms
                ))

        # If no tests found, create a placeholder
        if not test_results:
            test_results.append(TestResult(
                test_name=f"{category}_no_results",
                status="skipped" if result.returncode == 0 else "failed",
                duration_ms=0,
                error_message=result.stderr if result.returncode != 0 else "No test results found"
            ))

        return test_results

    def _generate_report(self) -> IntegrationTestReport:
        """Generate comprehensive integration test report"""

        passed = len([r for r in self.results if r.status == 'passed'])
        failed = len([r for r in self.results if r.status == 'failed'])
        skipped = len([r for r in self.results if r.status == 'skipped'])

        # Calculate performance summary
        performance_summary = self._calculate_performance_summary()

        # Assess compliance with integration requirements
        compliance_status = self._assess_compliance()

        # Environment information
        environment_info = {
            'python_version': sys.version,
            'test_directory': str(self.test_dir),
            'execution_host': os.uname().nodename if hasattr(os, 'uname') else 'unknown'
        }

        return IntegrationTestReport(
            execution_timestamp=time.strftime('%Y-%m-%d %H:%M:%S'),
            total_tests=len(self.results),
            passed_tests=passed,
            failed_tests=failed,
            skipped_tests=skipped,
            total_duration_seconds=self.end_time - self.start_time if self.end_time and self.start_time else 0,
            performance_summary=performance_summary,
            test_results=self.results,
            environment_info=environment_info,
            compliance_status=compliance_status
        )

    def _calculate_performance_summary(self) -> dict[str, Any]:
        """Calculate performance metrics summary"""
        durations = [r.duration_ms for r in self.results if r.duration_ms > 0]

        if not durations:
            return {'no_performance_data': True}

        durations.sort()

        return {
            'total_tests_with_timing': len(durations),
            'average_duration_ms': sum(durations) / len(durations),
            'median_duration_ms': durations[len(durations) // 2],
            'p95_duration_ms': durations[int(len(durations) * 0.95)] if len(durations) > 20 else durations[-1],
            'fastest_test_ms': durations[0],
            'slowest_test_ms': durations[-1],
            'tests_under_100ms': len([d for d in durations if d < 100]),
            'tests_over_1000ms': len([d for d in durations if d > 1000])
        }

    def _assess_compliance(self) -> dict[str, bool]:
        """Assess compliance with integration requirements"""

        # Check key integration requirements
        redis_messaging_tests = [r for r in self.results if 'redis' in r.test_name.lower() or 'message' in r.test_name.lower()]
        database_tests = [r for r in self.results if 'database' in r.test_name.lower()]
        performance_tests = [r for r in self.results if 'performance' in r.test_name.lower() or 'latency' in r.test_name.lower()]
        resilience_tests = [r for r in self.results if 'resilience' in r.test_name.lower() or 'failure' in r.test_name.lower()]

        return {
            'redis_pubsub_validation': len([r for r in redis_messaging_tests if r.status == 'passed']) > 0,
            'database_role_separation': len([r for r in database_tests if r.status == 'passed']) > 0,
            'message_delivery_performance': len([r for r in performance_tests if r.status == 'passed']) > 0,
            'system_resilience_validation': len([r for r in resilience_tests if r.status == 'passed']) > 0,
            'overall_integration_success': len([r for r in self.results if r.status == 'failed']) == 0
        }

    def _display_summary(self, report: IntegrationTestReport):
        """Display test execution summary"""

        print("\\n" + "=" * 80)
        print("🎯 SPRINT 14 PHASE 2 INTEGRATION TEST SUMMARY")
        print("=" * 80)

        print("📊 Test Results:")
        print(f"   Total Tests: {report.total_tests}")
        print(f"   ✅ Passed: {report.passed_tests}")
        print(f"   ❌ Failed: {report.failed_tests}")
        print(f"   ⚠️  Skipped: {report.skipped_tests}")
        print(f"   ⏱️  Duration: {report.total_duration_seconds:.1f}s")

        if report.performance_summary.get('total_tests_with_timing', 0) > 0:
            perf = report.performance_summary
            print("\\n⚡ Performance Summary:")
            print(f"   Average Test Duration: {perf['average_duration_ms']:.1f}ms")
            print(f"   95th Percentile: {perf['p95_duration_ms']:.1f}ms")
            print(f"   Tests <100ms: {perf['tests_under_100ms']}")
            print(f"   Tests >1000ms: {perf['tests_over_1000ms']}")

        print("\\n✅ Integration Compliance:")
        compliance = report.compliance_status
        for requirement, status in compliance.items():
            status_icon = "✅" if status else "❌"
            requirement_name = requirement.replace('_', ' ').title()
            print(f"   {status_icon} {requirement_name}")

        # Overall assessment
        overall_success = compliance['overall_integration_success']
        key_requirements_met = all([
            compliance['redis_pubsub_validation'],
            compliance['database_role_separation'],
            compliance['message_delivery_performance']
        ])

        print("\\n🎯 FINAL ASSESSMENT:")
        if overall_success and key_requirements_met:
            print("   🟢 INTEGRATION VALIDATION: PASSED")
            print("   ✅ All critical integration patterns validated")
            print("   ✅ Performance requirements met")
            print("   ✅ System boundaries properly enforced")
        elif key_requirements_met:
            print("   🟡 INTEGRATION VALIDATION: PARTIAL")
            print("   ✅ Core integration patterns validated")
            print("   ⚠️  Some non-critical tests failed")
        else:
            print("   🔴 INTEGRATION VALIDATION: FAILED")
            print("   ❌ Critical integration requirements not met")
            print("   ⚠️  Review failed tests and system configuration")

        print("=" * 80)

def main():
    """Main entry point for integration test runner"""
    parser = argparse.ArgumentParser(description='Sprint 14 Phase 2 Integration Test Runner')
    parser.add_argument('--performance', action='store_true',
                       help='Include performance benchmarks')
    parser.add_argument('--full-suite', action='store_true',
                       help='Run complete test suite including slow tests')
    parser.add_argument('--report-file', type=str,
                       help='Output file for JSON test report')
    parser.add_argument('--test-type', choices=['standard', 'performance', 'full'],
                       default='standard', help='Type of test suite to run')

    args = parser.parse_args()

    # Determine test type
    if args.full_suite:
        test_type = 'full'
    elif args.performance:
        test_type = 'performance'
    else:
        test_type = args.test_type

    # Run integration tests
    runner = IntegrationTestRunner()
    report = runner.run_test_suite(test_type)

    # Save report if requested
    if args.report_file:
        try:
            with open(args.report_file, 'w') as f:
                json.dump(asdict(report), f, indent=2, default=str)
            print(f"\\n📄 Test report saved to: {args.report_file}")
        except Exception as e:
            print(f"\\n⚠️  Failed to save report: {e}")

    # Exit with appropriate code
    exit_code = 0 if report.compliance_status['overall_integration_success'] else 1
    sys.exit(exit_code)

if __name__ == '__main__':
    main()
