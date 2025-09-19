#!/usr/bin/env python3
"""
Continuous Integration Test Monitor for TickStockAppV2
Runs integration tests periodically and monitors for regressions.

Sprint 25A: Automated integration validation for continuous monitoring.
"""

import sys
import os
from pathlib import Path
import time
import subprocess
import json
from datetime import datetime
import signal

class ContinuousIntegrationMonitor:
    """Runs integration tests continuously with configurable intervals."""

    def __init__(self, interval_seconds=300):  # Default 5 minutes
        self.interval = interval_seconds
        self.running = True
        self.test_history = []
        self.consecutive_failures = 0
        self.max_history = 100

    def run_integration_tests(self):
        """Execute the integration test suite."""
        test_script = Path(__file__).parent.parent / "run_tests.py"

        if not test_script.exists():
            return {
                'success': False,
                'error': 'Test script not found',
                'duration': 0
            }

        try:
            start_time = time.time()
            result = subprocess.run(
                [sys.executable, str(test_script)],
                capture_output=True,
                text=True,
                timeout=60  # 1 minute timeout
            )
            duration = time.time() - start_time

            # Parse output for test results
            output = result.stdout + result.stderr
            tests_passed = "[PASS] ALL INTEGRATION TESTS PASSED!" in output

            # Extract metrics
            patterns_detected = False
            redis_active = False
            heartbeat_ok = False

            for line in output.split('\n'):
                if "Redis subscription active" in line:
                    redis_active = True
                if "Pattern event structure compatibility" in line and "[OK]" in line:
                    patterns_detected = True
                if "Heartbeat:" in line and "beats" in line:
                    heartbeat_ok = True

            return {
                'success': tests_passed,
                'duration': duration,
                'redis_active': redis_active,
                'patterns_detected': patterns_detected,
                'heartbeat_ok': heartbeat_ok,
                'output_sample': output[-500:] if not tests_passed else None  # Last 500 chars if failed
            }

        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': 'Test timeout (>60s)',
                'duration': 60
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'duration': 0
            }

    def save_test_result(self, result):
        """Save test result to history."""
        result['timestamp'] = datetime.now().isoformat()
        self.test_history.append(result)

        # Keep only recent history
        if len(self.test_history) > self.max_history:
            self.test_history.pop(0)

        # Update consecutive failure counter
        if result['success']:
            self.consecutive_failures = 0
        else:
            self.consecutive_failures += 1

    def display_status(self):
        """Display current monitoring status."""
        os.system('cls' if os.name == 'nt' else 'clear')

        print("=" * 70)
        print(" CONTINUOUS INTEGRATION MONITOR ".center(70))
        print("=" * 70)
        print(f"  Monitoring Started: {self.test_history[0]['timestamp'] if self.test_history else 'Just started'}")
        print(f"  Test Interval: {self.interval} seconds")
        print(f"  Press Ctrl+C to stop")
        print("=" * 70)

        if self.test_history:
            latest = self.test_history[-1]
            print("\n[LATEST TEST RESULT]")
            print(f"  Time: {latest['timestamp']}")
            print(f"  Status: {'[PASS]' if latest['success'] else '[FAIL]'}")
            print(f"  Duration: {latest['duration']:.2f}s")

            if 'redis_active' in latest:
                print(f"  Redis: {'[OK]' if latest['redis_active'] else '[X]'}")
                print(f"  Patterns: {'[OK]' if latest['patterns_detected'] else '[X]'}")
                print(f"  Heartbeat: {'[OK]' if latest['heartbeat_ok'] else '[X]'}")

            if 'error' in latest:
                print(f"  Error: {latest['error']}")

            # Statistics
            total_tests = len(self.test_history)
            passed = sum(1 for t in self.test_history if t['success'])
            failed = total_tests - passed
            pass_rate = (passed / total_tests * 100) if total_tests > 0 else 0

            print("\n[TEST STATISTICS]")
            print(f"  Total Runs: {total_tests}")
            print(f"  Passed: {passed}")
            print(f"  Failed: {failed}")
            print(f"  Pass Rate: {pass_rate:.1f}%")
            print(f"  Consecutive Failures: {self.consecutive_failures}")

            # Recent history
            print("\n[RECENT HISTORY]")
            for test in self.test_history[-5:]:
                status = "[PASS]" if test['success'] else "[FAIL]"
                time_str = test['timestamp'].split('T')[1][:8]  # Just HH:MM:SS
                print(f"  {time_str}: {status} ({test['duration']:.1f}s)")

            # Alerts
            if self.consecutive_failures >= 3:
                print("\n[ALERT] 3+ CONSECUTIVE FAILURES - INTEGRATION MAY BE DOWN!")
            elif self.consecutive_failures >= 2:
                print("\n[WARNING] Multiple test failures detected")

        print(f"\n  Next test in: {self.get_time_to_next()} seconds")

    def get_time_to_next(self):
        """Calculate seconds until next test."""
        if not self.test_history:
            return 0

        last_time = datetime.fromisoformat(self.test_history[-1]['timestamp'])
        elapsed = (datetime.now() - last_time).total_seconds()
        return max(0, int(self.interval - elapsed))

    def run(self):
        """Run continuous monitoring."""
        signal.signal(signal.SIGINT, lambda s, f: setattr(self, 'running', False))

        print("Starting Continuous Integration Monitor...")
        print(f"Tests will run every {self.interval} seconds")
        print("Press Ctrl+C to stop\n")

        while self.running:
            try:
                # Run test
                self.display_status()
                print("\n[RUNNING] Executing integration tests...")

                result = self.run_integration_tests()
                self.save_test_result(result)

                # Display updated status
                self.display_status()

                # Check for critical failures
                if self.consecutive_failures >= 5:
                    print("\n[CRITICAL] 5+ consecutive failures! Stopping monitor.")
                    print("Please investigate integration issues.")
                    break

                # Wait for next interval
                wait_time = self.interval
                while wait_time > 0 and self.running:
                    time.sleep(min(5, wait_time))  # Update display every 5 seconds
                    wait_time -= 5
                    if wait_time > 0:
                        self.display_status()

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"\nMonitor error: {e}")
                time.sleep(5)

        # Save history before exiting
        self.save_history()
        print("\n\nContinuous monitoring stopped.")
        print(f"Total tests run: {len(self.test_history)}")

    def save_history(self):
        """Save test history to file."""
        history_file = Path(__file__).parent / "integration_test_history.json"
        try:
            with open(history_file, 'w') as f:
                json.dump(self.test_history, f, indent=2)
            print(f"Test history saved to: {history_file}")
        except Exception as e:
            print(f"Could not save history: {e}")


def main():
    """Main entry point."""
    import argparse
    parser = argparse.ArgumentParser(description='Continuous Integration Monitor')
    parser.add_argument(
        '--interval',
        type=int,
        default=300,
        help='Test interval in seconds (default: 300)'
    )
    parser.add_argument(
        '--quick',
        action='store_true',
        help='Quick mode: run every 60 seconds'
    )

    args = parser.parse_args()

    interval = 60 if args.quick else args.interval
    monitor = ContinuousIntegrationMonitor(interval)
    monitor.run()


if __name__ == "__main__":
    main()