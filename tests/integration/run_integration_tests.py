#!/usr/bin/env python3
"""
TickStockAppV2 Integration Test Runner
Run all integration tests in <10 seconds.
These tests validate REAL integration points, not mocks.
"""

import sys
import os
from pathlib import Path
import time
import subprocess

# Test colors for terminal
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'

def print_header(text):
    """Print formatted header."""
    print(f"\n{BLUE}{'=' * 70}{RESET}")
    print(f"{BLUE}{BOLD}{text:^70}{RESET}")
    print(f"{BLUE}{'=' * 70}{RESET}")

def print_section(text):
    """Print section header."""
    print(f"\n{YELLOW}{text}{RESET}")
    print(f"{YELLOW}{'-' * len(text)}{RESET}")

def run_test_file(filepath, description):
    """Run a single test file and capture results."""
    print(f"\n{description}...")
    start_time = time.time()

    try:
        result = subprocess.run(
            [sys.executable, filepath],
            capture_output=True,
            text=True,
            timeout=30
        )

        elapsed = time.time() - start_time

        if result.returncode == 0:
            print(f"{GREEN}[PASS] PASSED{RESET} ({elapsed:.2f}s)")
            # Show key outputs
            for line in result.stdout.split('\n'):
                if '[OK]' in line or '[PASS]' in line:
                    print(f"  {GREEN}{line.strip()}{RESET}")
            return True, elapsed
        else:
            print(f"{RED}[FAIL] FAILED{RESET} ({elapsed:.2f}s)")
            # Show errors
            for line in result.stderr.split('\n')[-5:]:
                if line.strip():
                    print(f"  {RED}{line.strip()}{RESET}")
            return False, elapsed

    except subprocess.TimeoutExpired:
        print(f"{RED}[FAIL] TIMEOUT{RESET} (>30s)")
        return False, 30.0
    except Exception as e:
        print(f"{RED}[FAIL] ERROR: {e}{RESET}")
        return False, 0.0

def check_prerequisites():
    """Check that required services are running."""
    print_section("Checking Prerequisites")

    checks = []

    # Check Redis
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379)
        r.ping()
        print(f"{GREEN}[OK]{RESET} Redis is running")
        checks.append(True)
    except:
        print(f"{RED}[X]{RESET} Redis is not running - start it first")
        checks.append(False)

    # Check PostgreSQL
    try:
        import psycopg2
        conn = psycopg2.connect(
            host='localhost',
            port=5433,
            database='tickstock',
            user='app_readwrite',
            password='LJI48rUEkUpe6e'
        )
        conn.close()
        print(f"{GREEN}[OK]{RESET} PostgreSQL is running")
        checks.append(True)
    except:
        print(f"{RED}[X]{RESET} PostgreSQL is not running - start it first")
        checks.append(False)

    # Check if TickStockAppV2 is running
    try:
        import requests
        resp = requests.get('http://localhost:5000/health', timeout=1)
        if resp.status_code == 200:
            print(f"{GREEN}[OK]{RESET} TickStockAppV2 is running")
            checks.append(True)
    except:
        print(f"{YELLOW}[!]{RESET} TickStockAppV2 not detected (some tests may fail)")
        checks.append(True)  # Not critical for all tests

    return all(checks)

def main():
    """Run all integration tests."""
    print_header("TICKSTOCKAPPV2 INTEGRATION TEST SUITE")
    print(f"\n{BOLD}Goal: Validate all integration points with TickStockPL{RESET}")
    print("These tests use REAL Redis, Database, and services (no mocks)")

    # Check prerequisites
    if not check_prerequisites():
        print(f"\n{RED}Prerequisites not met. Please start required services.{RESET}")
        return 1

    # Test files to run
    test_dir = Path(__file__).parent
    tests = [
        (test_dir / "test_tickstockpl_integration.py",
         "Core Integration Tests"),
        (test_dir / "test_pattern_flow_complete.py",
         "End-to-End Pattern Flow"),
        (test_dir / "test_integration_monitoring.py",
         "Integration Monitoring") if (test_dir / "test_integration_monitoring.py").exists() else None,
    ]

    # Filter out None values
    tests = [t for t in tests if t]

    print_section("Running Integration Tests")

    total_start = time.time()
    results = []

    for test_file, description in tests:
        if test_file.exists():
            passed, elapsed = run_test_file(str(test_file), description)
            results.append((description, passed, elapsed))
        else:
            print(f"\n{YELLOW}[!] Skipping {description} (file not found){RESET}")

    total_elapsed = time.time() - total_start

    # Summary
    print_header("TEST SUMMARY")

    passed_count = sum(1 for _, passed, _ in results if passed)
    failed_count = len(results) - passed_count

    print(f"\n{BOLD}Results:{RESET}")
    for description, passed, elapsed in results:
        status = f"{GREEN}PASS{RESET}" if passed else f"{RED}FAIL{RESET}"
        print(f"  {status} - {description} ({elapsed:.2f}s)")

    print(f"\n{BOLD}Statistics:{RESET}")
    print(f"  Total Tests: {len(results)}")
    print(f"  Passed: {GREEN}{passed_count}{RESET}")
    print(f"  Failed: {RED}{failed_count}{RESET}")
    print(f"  Total Time: {total_elapsed:.2f}s")

    if total_elapsed < 10:
        print(f"  {GREEN}[PASS] Target met: <10 seconds{RESET}")
    else:
        print(f"  {YELLOW}[!] Target missed: >10 seconds{RESET}")

    # Final verdict
    if failed_count == 0:
        print(f"\n{GREEN}{BOLD}[PASS] ALL INTEGRATION TESTS PASSED!{RESET}")
        print(f"{GREEN}The integration with TickStockPL is working correctly.{RESET}")
        print("\nThese tests validate:")
        print("  • Redis pub/sub consumption")
        print("  • Database integration logging")
        print("  • Pattern flow checkpoints")
        print("  • Event structure compatibility")
        print("  • Performance within targets")
        return 0
    else:
        print(f"\n{RED}{BOLD}[FAIL] {failed_count} TEST(S) FAILED{RESET}")
        print(f"{RED}Review the failures above and check:{RESET}")
        print("  • Is TickStockAppV2 running?")
        print("  • Is TickStockPL sending patterns?")
        print("  • Are all services healthy?")
        return 1

if __name__ == "__main__":
    sys.exit(main())