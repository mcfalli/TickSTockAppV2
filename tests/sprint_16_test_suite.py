"""
Sprint 16 Grid Modernization - Complete Test Suite Runner
=========================================================

Comprehensive test suite runner for Sprint 16 grid modernization implementation.

**Sprint**: 16 - Grid Modernization
**Coverage**: All Sprint 16 components and integration workflows
**Performance**: Validates <100ms initialization, <50ms API response, <25ms UI updates
**Organization**: Functional area-based test structure following TickStock standards
"""
import sys
from pathlib import Path

import pytest


def run_sprint_16_test_suite():
    """
    Run complete Sprint 16 test suite with comprehensive coverage.
    
    Test Organization:
    - web_interface/sprint_16/: Frontend JavaScript components
    - api/sprint_16/: API endpoint testing  
    - integration/sprint_16/: End-to-end workflow testing
    - system_integration/sprint_16/: Performance and system testing
    """

    # Define test paths
    test_paths = [
        'tests/web_interface/sprint_16/',
        'tests/api/sprint_16/',
        'tests/integration/sprint_16/',
        'tests/system_integration/sprint_16/'
    ]

    # Test execution configuration
    pytest_args = [
        '-v',  # Verbose output
        '--tb=short',  # Short traceback format
        '--durations=10',  # Show 10 slowest tests
        '--cov=src',  # Coverage for src directory
        '--cov-report=html',  # HTML coverage report
        '--cov-report=term-missing',  # Terminal coverage with missing lines
        '--cov-fail-under=70',  # Minimum 70% coverage
        '-m', 'not slow',  # Skip slow tests by default
    ]

    # Add test paths
    pytest_args.extend(test_paths)

    print("🚀 Starting Sprint 16 Grid Modernization Test Suite")
    print("=" * 60)
    print("Test Coverage:")
    print("  • Grid Configuration (app-gridstack.js)")
    print("  • Market Movers API (/api/market-movers)")
    print("  • Market Movers Widget (market-movers.js)")
    print("  • Dashboard HTML Structure (6 containers)")
    print("  • Integration Workflows")
    print("  • Performance Validation")
    print("=" * 60)

    # Run tests
    exit_code = pytest.main(pytest_args)

    if exit_code == 0:
        print("✅ Sprint 16 Test Suite PASSED")
        print("   All grid modernization components validated")
        print("   Performance targets met")
        print("   Integration workflows confirmed")
    else:
        print("❌ Sprint 16 Test Suite FAILED")
        print("   Check test output for failures")
        print("   Review performance benchmarks")

    return exit_code


def run_performance_tests_only():
    """Run only performance-critical tests for Sprint 16."""

    performance_args = [
        '-v',
        '--tb=short',
        '-m', 'performance',  # Only performance tests
        'tests/web_interface/sprint_16/',
        'tests/api/sprint_16/',
        'tests/integration/sprint_16/',
        'tests/system_integration/sprint_16/'
    ]

    print("⚡ Running Sprint 16 Performance Tests Only")
    print("=" * 50)
    print("Performance Targets:")
    print("  • Grid Initialization: <100ms")
    print("  • API Response Time: <50ms")
    print("  • UI Update Time: <25ms")
    print("  • Layout Save/Load: <10ms")
    print("=" * 50)

    return pytest.main(performance_args)


def run_integration_tests_only():
    """Run only integration tests for Sprint 16."""

    integration_args = [
        '-v',
        '--tb=short',
        'tests/integration/sprint_16/',
        'tests/system_integration/sprint_16/'
    ]

    print("🔗 Running Sprint 16 Integration Tests Only")
    print("=" * 50)
    print("Integration Coverage:")
    print("  • Grid + Market Movers Data Flow")
    print("  • API + Frontend Widget Integration")
    print("  • Layout Persistence Workflow")
    print("  • Responsive Behavior Integration")
    print("  • Error Recovery Scenarios")
    print("=" * 50)

    return pytest.main(integration_args)


def run_component_tests_only():
    """Run only component-level tests for Sprint 16."""

    component_args = [
        '-v',
        '--tb=short',
        'tests/web_interface/sprint_16/',
        'tests/api/sprint_16/'
    ]

    print("🧩 Running Sprint 16 Component Tests Only")
    print("=" * 50)
    print("Component Coverage:")
    print("  • app-gridstack.js (Grid Configuration)")
    print("  • market-movers.js (Frontend Widget)")
    print("  • /api/market-movers (API Endpoint)")
    print("  • Dashboard HTML Structure")
    print("=" * 50)

    return pytest.main(component_args)


def validate_test_structure():
    """Validate that all expected Sprint 16 test files exist."""

    expected_test_files = [
        'tests/web_interface/sprint_16/test_app_gridstack_refactor.py',
        'tests/web_interface/sprint_16/test_market_movers_widget_integration.py',
        'tests/web_interface/sprint_16/test_dashboard_html_structure_preservation.py',
        'tests/api/sprint_16/test_market_movers_api_refactor.py',
        'tests/integration/sprint_16/test_grid_modernization_integration.py',
        'tests/system_integration/sprint_16/test_grid_performance_validation.py'
    ]

    missing_files = []
    existing_files = []

    for test_file in expected_test_files:
        if Path(test_file).exists():
            existing_files.append(test_file)
        else:
            missing_files.append(test_file)

    print("📁 Sprint 16 Test Structure Validation")
    print("=" * 50)
    print(f"✅ Existing Test Files ({len(existing_files)}):")
    for file_path in existing_files:
        print(f"   • {file_path}")

    if missing_files:
        print(f"\n❌ Missing Test Files ({len(missing_files)}):")
        for file_path in missing_files:
            print(f"   • {file_path}")
        return False
    print("\n✅ All expected test files found")
    return True


def generate_test_report():
    """Generate a comprehensive test report for Sprint 16."""

    print("📊 Sprint 16 Test Coverage Report")
    print("=" * 60)

    test_categories = {
        'Grid Configuration Tests': {
            'file': 'tests/web_interface/sprint_16/test_app_gridstack_refactor.py',
            'focus': 'getDefaultLayout(), responsive behavior, layout persistence',
            'target_coverage': '30+ unit tests, 15+ integration tests'
        },
        'Market Movers API Tests': {
            'file': 'tests/api/sprint_16/test_market_movers_api_refactor.py',
            'focus': 'Response structure, performance <50ms, error handling',
            'target_coverage': '25+ API tests, performance validation'
        },
        'Market Movers Widget Tests': {
            'file': 'tests/web_interface/sprint_16/test_market_movers_widget_integration.py',
            'focus': 'Auto-refresh, rendering, WebSocket integration',
            'target_coverage': '20+ widget tests, UI update performance'
        },
        'Dashboard Structure Tests': {
            'file': 'tests/web_interface/sprint_16/test_dashboard_html_structure_preservation.py',
            'focus': '6 grid containers, preserved IDs, removed tabs',
            'target_coverage': '15+ structure tests, accessibility validation'
        },
        'Integration Workflow Tests': {
            'file': 'tests/integration/sprint_16/test_grid_modernization_integration.py',
            'focus': 'End-to-end workflows, error recovery, concurrency',
            'target_coverage': '20+ integration tests, cross-component validation'
        },
        'Performance Validation Tests': {
            'file': 'tests/system_integration/sprint_16/test_grid_performance_validation.py',
            'focus': 'System performance, scalability, regression detection',
            'target_coverage': '15+ performance tests, benchmark validation'
        }
    }

    for category, details in test_categories.items():
        print(f"\n{category}:")
        print(f"  📄 File: {details['file']}")
        print(f"  🎯 Focus: {details['focus']}")
        print(f"  📈 Coverage: {details['target_coverage']}")

    print("\n📋 Total Expected Test Coverage:")
    print("   • Unit Tests: 125+ individual test methods")
    print("   • Integration Tests: 50+ workflow validations")
    print("   • Performance Tests: 25+ benchmark validations")
    print("   • Total Test Files: 6 comprehensive test suites")

    print("\n🎯 Sprint 16 Quality Gates:")
    print("   • Code Coverage: ≥70% for core business logic")
    print("   • Performance: Grid init <100ms, API <50ms, UI <25ms")
    print("   • Integration: All 6 containers functional")
    print("   • Compatibility: Mobile/desktop responsive behavior")
    print("   • Reliability: Error recovery and fallback mechanisms")


if __name__ == '__main__':
    """
    Sprint 16 Test Suite Command Line Interface
    
    Usage:
        python tests/sprint_16_test_suite.py                    # Run full test suite
        python tests/sprint_16_test_suite.py --performance      # Performance tests only
        python tests/sprint_16_test_suite.py --integration      # Integration tests only  
        python tests/sprint_16_test_suite.py --components       # Component tests only
        python tests/sprint_16_test_suite.py --validate         # Validate test structure
        python tests/sprint_16_test_suite.py --report           # Generate test report
    """

    if len(sys.argv) > 1:
        if '--performance' in sys.argv:
            exit_code = run_performance_tests_only()
        elif '--integration' in sys.argv:
            exit_code = run_integration_tests_only()
        elif '--components' in sys.argv:
            exit_code = run_component_tests_only()
        elif '--validate' in sys.argv:
            validation_success = validate_test_structure()
            exit_code = 0 if validation_success else 1
        elif '--report' in sys.argv:
            generate_test_report()
            exit_code = 0
        elif '--help' in sys.argv:
            print(__doc__)
            exit_code = 0
        else:
            print("❌ Unknown argument. Use --help for usage information.")
            exit_code = 1
    else:
        # Run full test suite
        exit_code = run_sprint_16_test_suite()

    sys.exit(exit_code)
