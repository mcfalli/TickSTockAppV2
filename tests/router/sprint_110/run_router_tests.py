"""
Sprint 110: Router Test Runner

Simple test runner for Sprint 110 router delegation fix tests.
Runs both automated pytest tests and manual validation.

Usage:
    python run_router_tests.py [--automated-only] [--manual-only]

Created: 2025-08-22
Sprint: 110
"""

import subprocess
import sys
import os
import argparse
import asyncio

def run_automated_tests():
    """Run automated pytest tests"""
    print("🧪 Running Sprint 110 Automated Router Tests...")
    print("=" * 50)
    
    # Navigate to test directory
    test_dir = os.path.dirname(__file__)
    test_file = os.path.join(test_dir, "test_router_delegation_fix.py")
    
    # Run pytest
    cmd = [
        sys.executable, "-m", "pytest", 
        test_file,
        "-v",
        "--tb=short",
        "--color=yes"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=test_dir)
        
        print("STDOUT:")
        print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        if result.returncode == 0:
            print("✅ Automated tests completed successfully!")
        else:
            print(f"❌ Automated tests failed with return code: {result.returncode}")
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ Error running automated tests: {e}")
        return False

async def run_manual_validation():
    """Run manual validation tests"""
    print("\n🔍 Running Sprint 110 Manual Validation...")
    print("=" * 50)
    
    try:
        # Import and run manual validation
        from manual_router_validation import main as validation_main
        await validation_main()
        return True
        
    except Exception as e:
        print(f"❌ Error running manual validation: {e}")
        return False

def main():
    """Main test runner"""
    parser = argparse.ArgumentParser(description="Sprint 110 Router Test Runner")
    parser.add_argument("--automated-only", action="store_true", 
                       help="Run only automated tests")
    parser.add_argument("--manual-only", action="store_true",
                       help="Run only manual validation")
    
    args = parser.parse_args()
    
    print("🚀 SPRINT 110: Router Delegation Fix Test Suite")
    print("=" * 60)
    
    automated_success = True
    manual_success = True
    
    # Run automated tests
    if not args.manual_only:
        automated_success = run_automated_tests()
    
    # Run manual validation
    if not args.automated_only:
        manual_success = asyncio.run(run_manual_validation())
    
    # Summary
    print("\n" + "=" * 60)
    print("🎯 SPRINT 110 TEST SUITE SUMMARY")
    print("=" * 60)
    
    if not args.manual_only:
        status = "✅ PASSED" if automated_success else "❌ FAILED"
        print(f"Automated Tests: {status}")
    
    if not args.automated_only:
        status = "✅ PASSED" if manual_success else "❌ FAILED"
        print(f"Manual Validation: {status}")
    
    overall_success = automated_success and manual_success
    
    if overall_success:
        print("\n🏆 OVERALL RESULT: ALL TESTS PASSED")
        print("✅ Sprint 110 router delegation fixes are working correctly!")
    else:
        print("\n⚠️ OVERALL RESULT: SOME TESTS FAILED")
        print("❌ Review failed tests and address issues before deployment")
    
    return 0 if overall_success else 1

if __name__ == "__main__":
    sys.exit(main())