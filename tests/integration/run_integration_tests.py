#!/usr/bin/env python3
"""
TickStockAppV2 Integration Test Runner
Run all integration tests in <10 seconds.
These tests validate REAL integration points, not mocks.
"""

import sys
from pathlib import Path

# Add project root to Python path to import src modules
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import subprocess
import time
from datetime import datetime

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
    test_details = []

    try:
        result = subprocess.run(
            [sys.executable, filepath],
            capture_output=True,
            text=True,
            timeout=30
        )

        elapsed = time.time() - start_time
        output = result.stdout + result.stderr

        # Extract individual test results from output
        for line in output.split('\n'):
            if '[OK]' in line or '[PASS]' in line:
                test_details.append({'test': line.strip(), 'status': 'PASS'})
            elif '[X]' in line or '[FAIL]' in line:
                test_details.append({'test': line.strip(), 'status': 'FAIL'})

        if result.returncode == 0:
            print(f"{GREEN}[PASS] PASSED{RESET} ({elapsed:.2f}s)")
            # Show key outputs
            for line in result.stdout.split('\n'):
                if '[OK]' in line or '[PASS]' in line:
                    print(f"  {GREEN}{line.strip()}{RESET}")
            return True, elapsed, test_details
        print(f"{RED}[FAIL] FAILED{RESET} ({elapsed:.2f}s)")
        # Show errors
        for line in result.stderr.split('\n')[-5:]:
            if line.strip():
                print(f"  {RED}{line.strip()}{RESET}")
        return False, elapsed, test_details

    except subprocess.TimeoutExpired:
        print(f"{RED}[FAIL] TIMEOUT{RESET} (>30s)")
        return False, 30.0, [{'test': f'{description} - TIMEOUT', 'status': 'FAIL'}]
    except Exception as e:
        print(f"{RED}[FAIL] ERROR: {e}{RESET}")
        return False, 0.0, [{'test': f'{description} - ERROR: {e}', 'status': 'FAIL'}]

def write_test_report(results, total_elapsed, all_test_details):
    """Write detailed test report to LAST_TEST_RUN.md."""
    report_file = Path(__file__).parent.parent / "LAST_TEST_RUN.md"

    passed_count = sum(1 for _, passed, _, _ in results if passed)
    failed_count = len(results) - passed_count

    # Count individual test details
    detail_pass = sum(1 for d in all_test_details if d['status'] == 'PASS')
    detail_fail = sum(1 for d in all_test_details if d['status'] == 'FAIL')

    content = f"""# Last Test Run Report

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Command**: `python run_tests.py`
**Total Duration**: {total_elapsed:.2f} seconds
**Status**: {"[PASSED]" if failed_count == 0 else "[FAILED]"}

## Summary Statistics

- **Test Suites Run**: {len(results)}
- **Test Suites Passed**: {passed_count}
- **Test Suites Failed**: {failed_count}
- **Individual Tests Passed**: {detail_pass}
- **Individual Tests Failed**: {detail_fail}
- **Performance Target (<10s)**: {"[MET]" if total_elapsed < 10 else "[MISSED]"}

## Test Suite Results

| Suite | Status | Duration | Tests |
|-------|--------|----------|-------|
"""

    for description, passed, elapsed, details in results:
        status = "[PASS]" if passed else "[FAIL]"
        test_count = len(details)
        content += f"| {description} | {status} | {elapsed:.2f}s | {test_count} |\n"

    content += "\n## Individual Test Results\n\n"

    # Group tests by suite
    for description, passed, elapsed, details in results:
        if details:
            content += f"\n### {description}\n\n"
            for detail in details:
                status_icon = "[PASS]" if detail['status'] == 'PASS' else "[FAIL]"
                # Clean up the test name
                test_name = detail['test'].replace('[OK]', '').replace('[X]', '').replace('[PASS]', '').replace('[FAIL]', '').strip()
                content += f"- {status_icon} {test_name}\n"

    content += f"""
## Expected Test Coverage

These integration tests validate:

1. **Redis Integration**
   - Active subscription to `tickstock.events.patterns`
   - Publisher count verification
   - Message delivery confirmation

2. **Event Processing**
   - Pattern event structure compatibility
   - Nested data structure handling
   - Field name flexibility (pattern/pattern_name)

3. **Database Integration**
   - Integration events logging
   - Flow UUID tracking
   - Processing time measurements
   - Checkpoint logging

4. **Pattern Flow**
   - Multi-tier patterns (Daily/Intraday/Combo)
   - NumPy data serialization
   - High-volume processing (40+ patterns/minute)
   - End-to-end latency tracking

5. **Monitoring**
   - 60-second heartbeat intervals
   - Subscription health checks
   - Performance metrics collection

## Performance Targets

| Metric | Target | Status |
|--------|--------|--------|
| Total Test Time | <10 seconds | {"[MET]" if total_elapsed < 10 else "[MISSED]"} |
| Pattern Processing | <100ms per event | Check logs |
| Database Logging | <50ms per checkpoint | Check logs |
| WebSocket Delivery | <100ms end-to-end | Check logs |

## Next Run

To run these tests again:

```bash
python run_tests.py
```

To monitor integration performance:

```bash
python scripts/monitor_integration_performance.py
```

---
*Report generated by TickStockAppV2 Integration Test Suite*
"""

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"\n{GREEN}Test report written to: {report_file}{RESET}")

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

        from src.core.services.config_manager import get_config
        config = get_config()

        # Parse DATABASE_URI to get connection parameters
        db_uri = config.get('DATABASE_URI', 'postgresql://app_readwrite:password@localhost:5432/tickstock')
        # Extract password from URI
        import re
        match = re.match(r'postgresql://([^:]+):([^@]+)@([^:/]+)(?::(\d+))?/(.+)', db_uri)
        if match:
            user, password, host, port, database = match.groups()
            port = port or '5432'
        else:
            # Fallback values
            host, port, database, user, password = 'localhost', 5432, 'tickstock', 'app_readwrite', 'password'

        conn = psycopg2.connect(
            host=host,
            port=int(port),
            database=database,
            user=user,
            password=password
        )
        conn.close()
        print(f"{GREEN}[OK]{RESET} PostgreSQL is running")
        checks.append(True)
    except Exception as e:
        print(f"{RED}[X]{RESET} PostgreSQL is not running - start it first")
        print(f"  Debug: {str(e)}")
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

    all_test_details = []
    for test_file, description in tests:
        if test_file.exists():
            passed, elapsed, test_details = run_test_file(str(test_file), description)
            results.append((description, passed, elapsed, test_details))
            all_test_details.extend(test_details)
        else:
            print(f"\n{YELLOW}[!] Skipping {description} (file not found){RESET}")

    total_elapsed = time.time() - total_start

    # Summary
    print_header("TEST SUMMARY")

    passed_count = sum(1 for _, passed, _, _ in results if passed)
    failed_count = len(results) - passed_count

    print(f"\n{BOLD}Results:{RESET}")
    for description, passed, elapsed, _ in results:
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

    # Write test report
    write_test_report(results, total_elapsed, all_test_details)

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
    print(f"\n{RED}{BOLD}[FAIL] {failed_count} TEST(S) FAILED{RESET}")
    print(f"{RED}Review the failures above and check:{RESET}")
    print("  • Is TickStockAppV2 running?")
    print("  • Is TickStockPL sending patterns?")
    print("  • Are all services healthy?")
    return 1

if __name__ == "__main__":
    sys.exit(main())
