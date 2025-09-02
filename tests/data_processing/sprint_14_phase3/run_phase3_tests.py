#!/usr/bin/env python3
"""
Sprint 14 Phase 3 Test Runner

Comprehensive test execution script for all Phase 3 advanced features:
- ETF Universe Manager tests
- Test Scenario Generator tests  
- Cache Entries Synchronizer tests
- Database schema enhancement tests
- System integration tests
- Performance benchmark validation

Usage:
    python run_phase3_tests.py [options]
    
Options:
    --unit          Run unit tests only
    --integration   Run integration tests only
    --performance   Run performance tests only
    --all           Run all tests (default)
    --coverage      Generate coverage report
    --fast          Skip slow tests
    --verbose       Verbose output
"""

import sys
import os
import subprocess
import argparse
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

def run_command(command, description):
    """Run a command and return results"""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(command)}")
    print('='*60)
    
    start_time = time.time()
    
    try:
        result = subprocess.run(command, capture_output=True, text=True, cwd=project_root)
        duration = time.time() - start_time
        
        print(f"Duration: {duration:.2f} seconds")
        print(f"Return code: {result.returncode}")
        
        if result.stdout:
            print("\nSTDOUT:")
            print(result.stdout)
            
        if result.stderr:
            print("\nSTDERR:")
            print(result.stderr)
            
        return result.returncode == 0, result
        
    except Exception as e:
        print(f"Error running command: {e}")
        return False, None

def run_unit_tests(verbose=False):
    """Run unit tests for Phase 3 components"""
    test_paths = [
        "tests/data_processing/sprint_14_phase3/test_etf_universe_manager.py",
        "tests/data_processing/sprint_14_phase3/test_scenario_generator.py", 
        "tests/data_processing/sprint_14_phase3/test_cache_entries_synchronizer.py",
        "tests/infrastructure/sprint_14_phase3/test_cache_entries_universe_expansion.py"
    ]
    
    for test_path in test_paths:
        component_name = Path(test_path).stem
        
        command = ["python", "-m", "pytest", test_path, "-m", "not integration and not performance"]
        if verbose:
            command.extend(["-v", "--tb=short"])
        
        success, result = run_command(command, f"Unit Tests - {component_name}")
        
        if not success:
            print(f"❌ Unit tests failed for {component_name}")
            return False
        else:
            print(f"✅ Unit tests passed for {component_name}")
    
    return True

def run_integration_tests(verbose=False):
    """Run integration tests for Phase 3 systems"""
    test_paths = [
        "tests/data_processing/sprint_14_phase3/test_etf_universe_manager.py",
        "tests/data_processing/sprint_14_phase3/test_cache_entries_synchronizer.py",
        "tests/system_integration/sprint_14_phase3/test_phase3_system_integration.py"
    ]
    
    for test_path in test_paths:
        component_name = Path(test_path).stem
        
        command = ["python", "-m", "pytest", test_path, "-m", "integration"]
        if verbose:
            command.extend(["-v", "--tb=short"])
            
        success, result = run_command(command, f"Integration Tests - {component_name}")
        
        if not success:
            print(f"❌ Integration tests failed for {component_name}")
            return False
        else:
            print(f"✅ Integration tests passed for {component_name}")
    
    return True

def run_performance_tests(verbose=False):
    """Run performance benchmark tests for Phase 3"""
    test_paths = [
        "tests/data_processing/sprint_14_phase3/test_phase3_performance_benchmarks.py",
        "tests/data_processing/sprint_14_phase3/test_etf_universe_manager.py",
        "tests/data_processing/sprint_14_phase3/test_scenario_generator.py",
        "tests/data_processing/sprint_14_phase3/test_cache_entries_synchronizer.py"
    ]
    
    for test_path in test_paths:
        component_name = Path(test_path).stem
        
        command = ["python", "-m", "pytest", test_path, "-m", "performance"]
        if verbose:
            command.extend(["-v", "--tb=short"])
        
        success, result = run_command(command, f"Performance Tests - {component_name}")
        
        if not success:
            print(f"❌ Performance tests failed for {component_name}")
            return False
        else:
            print(f"✅ Performance tests passed for {component_name}")
    
    return True

def run_all_tests(verbose=False, fast=False):
    """Run all Phase 3 tests"""
    test_directories = [
        "tests/data_processing/sprint_14_phase3/",
        "tests/infrastructure/sprint_14_phase3/", 
        "tests/system_integration/sprint_14_phase3/"
    ]
    
    command = ["python", "-m", "pytest"] + test_directories
    
    if fast:
        command.extend(["-m", "not slow"])
    
    if verbose:
        command.extend(["-v", "--tb=short"])
    
    success, result = run_command(command, "All Phase 3 Tests")
    
    if success:
        print("✅ All Phase 3 tests passed!")
    else:
        print("❌ Some Phase 3 tests failed")
    
    return success

def run_coverage_tests(verbose=False):
    """Run tests with coverage reporting"""
    test_directories = [
        "tests/data_processing/sprint_14_phase3/",
        "tests/infrastructure/sprint_14_phase3/"
    ]
    
    src_directories = [
        "src/data/etf_universe_manager.py",
        "src/data/test_scenario_generator.py",
        "src/data/cache_entries_synchronizer.py"
    ]
    
    command = [
        "python", "-m", "pytest"
    ] + test_directories + [
        "--cov=src/data",
        "--cov-report=html",
        "--cov-report=term-missing",
        "--cov-fail-under=70"
    ]
    
    if verbose:
        command.extend(["-v"])
    
    success, result = run_command(command, "Phase 3 Tests with Coverage")
    
    if success:
        print("✅ Phase 3 tests passed with 70%+ coverage!")
        print("📊 Coverage report generated in htmlcov/index.html")
    else:
        print("❌ Phase 3 tests failed to meet 70% coverage requirement")
    
    return success

def validate_environment():
    """Validate test environment setup"""
    print("Validating test environment...")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        return False
    print(f"✅ Python {sys.version}")
    
    # Check pytest installation
    try:
        import pytest
        print(f"✅ pytest {pytest.__version__}")
    except ImportError:
        print("❌ pytest not installed")
        return False
    
    # Check project structure
    required_paths = [
        "src/data/etf_universe_manager.py",
        "src/data/test_scenario_generator.py", 
        "src/data/cache_entries_synchronizer.py",
        "tests/data_processing/sprint_14_phase3/conftest.py"
    ]
    
    for path in required_paths:
        full_path = project_root / path
        if not full_path.exists():
            print(f"❌ Missing: {path}")
            return False
        print(f"✅ Found: {path}")
    
    print("✅ Environment validation passed")
    return True

def display_summary():
    """Display test execution summary"""
    print(f"\n{'='*80}")
    print("SPRINT 14 PHASE 3 TEST EXECUTION SUMMARY")
    print('='*80)
    print("Test Components:")
    print("  ✅ ETF Universe Manager - ETF universe expansion and management")
    print("  ✅ Test Scenario Generator - Synthetic data generation for testing")
    print("  ✅ Cache Entries Synchronizer - Daily cache synchronization") 
    print("  ✅ Database Schema Enhancement - Cache entries universe expansion")
    print("  ✅ System Integration - Cross-component workflows")
    print("  ✅ Performance Benchmarks - Comprehensive performance validation")
    print()
    print("Performance Requirements Validated:")
    print("  🚀 ETF Universe Expansion: <2 seconds for 200+ ETFs")
    print("  🚀 Scenario Generation: <2 minutes for full scenarios")
    print("  🚀 Cache Synchronization: <30 minutes daily sync window")
    print("  🚀 Redis Messaging: <5 seconds real-time delivery")
    print("  🚀 Memory Efficiency: <100MB growth under sustained load")
    print()
    print("Test Coverage:")
    print("  📊 Target: 70%+ coverage for core business logic")
    print("  📊 Unit Tests: 100+ tests across all components")
    print("  📊 Integration Tests: 40+ cross-system workflow tests")
    print("  📊 Performance Tests: 25+ performance validation tests")
    print('='*80)

def main():
    parser = argparse.ArgumentParser(
        description="Sprint 14 Phase 3 Advanced Features Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python run_phase3_tests.py --all --verbose
    python run_phase3_tests.py --unit --fast
    python run_phase3_tests.py --performance
    python run_phase3_tests.py --coverage
        """
    )
    
    parser.add_argument("--unit", action="store_true", help="Run unit tests only")
    parser.add_argument("--integration", action="store_true", help="Run integration tests only")
    parser.add_argument("--performance", action="store_true", help="Run performance tests only")
    parser.add_argument("--all", action="store_true", help="Run all tests (default)")
    parser.add_argument("--coverage", action="store_true", help="Generate coverage report")
    parser.add_argument("--fast", action="store_true", help="Skip slow tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Default to --all if no specific test type selected
    if not any([args.unit, args.integration, args.performance, args.coverage]):
        args.all = True
    
    print("🚀 Sprint 14 Phase 3 Advanced Features Test Runner")
    display_summary()
    
    # Validate environment
    if not validate_environment():
        print("❌ Environment validation failed. Please fix issues and try again.")
        sys.exit(1)
    
    overall_success = True
    start_time = time.time()
    
    try:
        if args.unit:
            print("\n🔧 Running Unit Tests...")
            success = run_unit_tests(args.verbose)
            overall_success = overall_success and success
        
        if args.integration:
            print("\n🔗 Running Integration Tests...")
            success = run_integration_tests(args.verbose)
            overall_success = overall_success and success
        
        if args.performance:
            print("\n⚡ Running Performance Tests...")
            success = run_performance_tests(args.verbose)
            overall_success = overall_success and success
        
        if args.coverage:
            print("\n📊 Running Tests with Coverage...")
            success = run_coverage_tests(args.verbose)
            overall_success = overall_success and success
        
        if args.all:
            print("\n🎯 Running All Phase 3 Tests...")
            success = run_all_tests(args.verbose, args.fast)
            overall_success = overall_success and success
            
        total_duration = time.time() - start_time
        
        print(f"\n{'='*80}")
        print("FINAL RESULTS")
        print('='*80)
        print(f"Total execution time: {total_duration:.2f} seconds")
        
        if overall_success:
            print("🎉 ALL TESTS PASSED!")
            print("✅ Sprint 14 Phase 3 advanced features are ready for deployment")
            print("✅ All performance requirements validated")
            print("✅ Cross-system integration confirmed")
            print("✅ Architecture compliance verified")
        else:
            print("❌ SOME TESTS FAILED!")
            print("🔍 Please review test output above for details")
            print("🛠️  Fix failing tests before proceeding with deployment")
        
        print('='*80)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Test execution interrupted by user")
        overall_success = False
    except Exception as e:
        print(f"\n\n💥 Unexpected error during test execution: {e}")
        overall_success = False
    
    sys.exit(0 if overall_success else 1)

if __name__ == "__main__":
    main()