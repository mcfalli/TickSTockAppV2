#!/usr/bin/env python3
"""
Sprint 10 Phase 1 Test Runner
Executes all Sprint 10 database integration tests with comprehensive reporting.

Usage:
    python run_sprint10_tests.py [--performance] [--coverage] [--verbose]
"""

import sys
import subprocess
import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description='Run Sprint 10 Phase 1 tests')
    parser.add_argument('--performance', action='store_true', help='Run performance tests only')
    parser.add_argument('--coverage', action='store_true', help='Generate coverage report')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--component', choices=['database', 'health', 'api', 'integration'], 
                       help='Run specific component tests only')
    
    args = parser.parse_args()
    
    # Base pytest command
    cmd = ['python', '-m', 'pytest']
    
    # Determine test paths based on arguments
    if args.component:
        if args.component == 'database':
            test_paths = ['tests/infrastructure/database/test_tickstock_db_refactor.py']
        elif args.component == 'health':
            test_paths = ['tests/core/services/test_health_monitor_refactor.py']
        elif args.component == 'api':
            test_paths = ['tests/api/rest/test_tickstockpl_api_refactor.py']
        elif args.component == 'integration':
            test_paths = ['tests/functional/sprint10/']
    else:
        # Run all Sprint 10 tests
        test_paths = [
            'tests/infrastructure/database/test_tickstock_db_refactor.py',
            'tests/core/services/test_health_monitor_refactor.py',
            'tests/api/rest/test_tickstockpl_api_refactor.py',
            'tests/functional/sprint10/'
        ]
    
    # Add test paths
    cmd.extend(test_paths)
    
    # Add performance marker if specified
    if args.performance:
        cmd.extend(['-m', 'performance'])
    
    # Add verbose flag
    if args.verbose:
        cmd.append('-v')
    else:
        cmd.extend(['-v', '--tb=short'])
    
    # Add coverage if requested
    if args.coverage:
        cmd.extend([
            '--cov=src.infrastructure.database',
            '--cov=src.core.services.health_monitor', 
            '--cov=src.api.rest.tickstockpl_api',
            '--cov-report=html',
            '--cov-report=term-missing',
            '--cov-fail-under=70'
        ])
    
    # Add other useful options
    cmd.extend([
        '--disable-warnings',
        '--strict-markers'
    ])
    
    print("=" * 80)
    print("TickStock Sprint 10 Phase 1 Database Integration Tests")
    print("=" * 80)
    print(f"Running command: {' '.join(cmd)}")
    print()
    
    # Verify test files exist
    missing_files = []
    for path in test_paths:
        if not Path(path).exists():
            missing_files.append(path)
    
    if missing_files:
        print("ERROR: Missing test files:")
        for file in missing_files:
            print(f"  - {file}")
        return 1
    
    # Run the tests
    try:
        result = subprocess.run(cmd, check=False)
        
        print()
        print("=" * 80)
        if result.returncode == 0:
            print("✅ All Sprint 10 tests PASSED!")
        else:
            print("❌ Some Sprint 10 tests FAILED!")
        print("=" * 80)
        
        if args.coverage and result.returncode == 0:
            print()
            print("📊 Coverage report generated at: htmlcov/index.html")
        
        return result.returncode
        
    except KeyboardInterrupt:
        print()
        print("Test execution interrupted by user")
        return 130
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())