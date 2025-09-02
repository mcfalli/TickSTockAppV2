#!/usr/bin/env python3
"""
Test Runner for CacheEntriesSynchronizer Test Suite

Provides convenient test execution with different modes and reporting options.
Follows TickStock testing standards and performance benchmarking requirements.

Usage:
    python run_tests.py --mode all          # Run all tests
    python run_tests.py --mode unit         # Run only unit tests
    python run_tests.py --mode integration  # Run only integration tests
    python run_tests.py --mode performance  # Run only performance tests
    python run_tests.py --mode errors       # Run only error handling tests
    python run_tests.py --coverage          # Run with coverage reporting
    python run_tests.py --benchmark         # Run performance benchmarks with detailed output
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path

# Add src to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'src'))

def run_command(cmd, description=""):
    """Run a command and display results."""
    print(f"\n{'='*60}")
    if description:
        print(f"🧪 {description}")
    print(f"{'='*60}")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 60)
    
    try:
        result = subprocess.run(cmd, capture_output=False, text=True, check=False)
        return result.returncode == 0
    except FileNotFoundError:
        print("❌ Error: pytest not found. Please install pytest: pip install pytest")
        return False
    except Exception as e:
        print(f"❌ Error running command: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Run CacheEntriesSynchronizer tests")
    parser.add_argument('--mode', choices=['all', 'unit', 'integration', 'performance', 'errors'], 
                       default='all', help='Test mode to run')
    parser.add_argument('--coverage', action='store_true', help='Run with coverage reporting')
    parser.add_argument('--benchmark', action='store_true', help='Run performance benchmarks with timing')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--fast', action='store_true', help='Skip performance tests for faster execution')
    
    args = parser.parse_args()
    
    # Base directory for tests
    test_dir = Path(__file__).parent
    
    # Build pytest command
    pytest_cmd = ['pytest']
    
    if args.verbose:
        pytest_cmd.append('-v')
    
    if args.coverage:
        pytest_cmd.extend([
            '--cov=src.core.services.cache_entries_synchronizer',
            '--cov-report=html',
            '--cov-report=term-missing'
        ])
    
    # Determine test files to run based on mode
    test_files = []
    descriptions = []
    
    if args.mode == 'all':
        if not args.fast:
            test_files = [
                str(test_dir / 'test_cache_entries_synchronizer_unit.py'),
                str(test_dir / 'test_cache_entries_synchronizer_integration.py'),
                str(test_dir / 'test_cache_entries_synchronizer_performance.py'),
                str(test_dir / 'test_cache_entries_synchronizer_error_handling.py')
            ]
            descriptions = [
                "Unit Tests - Individual method testing",
                "Integration Tests - Complete workflow testing", 
                "Performance Tests - Benchmark validation",
                "Error Handling Tests - Failure scenario testing"
            ]
        else:
            test_files = [
                str(test_dir / 'test_cache_entries_synchronizer_unit.py'),
                str(test_dir / 'test_cache_entries_synchronizer_integration.py'),
                str(test_dir / 'test_cache_entries_synchronizer_error_handling.py')
            ]
            descriptions = [
                "Unit Tests - Individual method testing",
                "Integration Tests - Complete workflow testing",
                "Error Handling Tests - Failure scenario testing (Performance tests skipped)"
            ]
            
    elif args.mode == 'unit':
        test_files = [str(test_dir / 'test_cache_entries_synchronizer_unit.py')]
        descriptions = ["Unit Tests - Individual method testing"]
        
    elif args.mode == 'integration':
        test_files = [str(test_dir / 'test_cache_entries_synchronizer_integration.py')]
        descriptions = ["Integration Tests - Complete workflow testing"]
        
    elif args.mode == 'performance':
        test_files = [str(test_dir / 'test_cache_entries_synchronizer_performance.py')]
        descriptions = ["Performance Tests - Benchmark validation"]
        if args.benchmark:
            pytest_cmd.extend(['-s', '-m', 'performance'])
            
    elif args.mode == 'errors':
        test_files = [str(test_dir / 'test_cache_entries_synchronizer_error_handling.py')]
        descriptions = ["Error Handling Tests - Failure scenario testing"]
    
    # Performance-specific options
    if args.benchmark and args.mode in ['performance', 'all']:
        pytest_cmd.extend(['-s', '--tb=short'])
    
    # Run tests
    all_passed = True
    
    print("🚀 CacheEntriesSynchronizer Test Suite")
    print(f"📁 Test Directory: {test_dir}")
    print(f"🎯 Mode: {args.mode}")
    if args.coverage:
        print("📊 Coverage reporting enabled")
    if args.benchmark:
        print("⏱️  Performance benchmarking enabled")
    
    for i, (test_file, description) in enumerate(zip(test_files, descriptions)):
        cmd = pytest_cmd + [test_file]
        success = run_command(cmd, f"{i+1}/{len(test_files)} - {description}")
        
        if not success:
            all_passed = False
            print(f"❌ Test failed: {description}")
        else:
            print(f"✅ Test passed: {description}")
    
    # Summary
    print(f"\n{'='*60}")
    print("📋 TEST SUMMARY")
    print(f"{'='*60}")
    
    if all_passed:
        print("🎉 All tests PASSED!")
        print("\n✅ CacheEntriesSynchronizer meets TickStock quality standards:")
        print("   • Unit test coverage complete")
        print("   • Integration workflow validated") 
        if not args.fast:
            print("   • Performance benchmarks satisfied")
        print("   • Error handling robust")
        print("   • Data integrity preserved")
        
        if args.coverage:
            print(f"\n📊 Coverage report generated: {test_dir.parent.parent.parent.parent / 'htmlcov' / 'index.html'}")
        
        return 0
    else:
        print("❌ Some tests FAILED!")
        print("\n🚨 Issues detected - review test output above")
        print("   • Fix failing tests before production deployment")
        print("   • Ensure all performance requirements are met")
        print("   • Validate error handling coverage")
        
        return 1

if __name__ == '__main__':
    sys.exit(main())