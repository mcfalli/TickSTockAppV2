#!/usr/bin/env python3
"""
TickStock Test Runner
Provides convenient commands for running different types of tests.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestRunner:
    """Manages test execution for TickStock"""
    
    def __init__(self):
        self.project_root = project_root
        self.test_dir = self.project_root / "tests"
    
    def run_unit_tests(self, coverage=True, verbose=False):
        """Run unit tests"""
        cmd = ["python", "-m", "pytest", "tests/unit/"]
        
        if coverage:
            cmd.extend(["--cov=src", "--cov-report=html", "--cov-report=term-missing"])
        
        if verbose:
            cmd.append("-v")
        
        cmd.append("-m")
        cmd.append("unit")
        
        return self._execute_command(cmd)
    
    def run_integration_tests(self, verbose=False):
        """Run integration tests"""
        cmd = ["python", "-m", "pytest", "tests/integration/"]
        
        if verbose:
            cmd.append("-v")
        
        cmd.append("-m")
        cmd.append("integration")
        
        return self._execute_command(cmd)
    
    def run_performance_tests(self, verbose=False):
        """Run performance tests"""
        cmd = ["python", "-m", "pytest", "tests/"]
        
        if verbose:
            cmd.append("-v")
        
        cmd.extend(["-m", "performance"])
        
        return self._execute_command(cmd)
    
    def run_all_tests(self, coverage=True, verbose=False):
        """Run all tests"""
        cmd = ["python", "-m", "pytest", "tests/"]
        
        if coverage:
            cmd.extend(["--cov=src", "--cov-report=html", "--cov-report=term-missing"])
        
        if verbose:
            cmd.append("-v")
        
        return self._execute_command(cmd)
    
    def run_quick_tests(self):
        """Run fast tests only (exclude slow/api/database tests)"""
        cmd = [
            "python", "-m", "pytest", "tests/",
            "-m", "not slow and not api and not database",
            "-x",  # Stop on first failure
            "--tb=short"
        ]
        
        return self._execute_command(cmd)
    
    def run_specific_test(self, test_path, verbose=True):
        """Run a specific test file or function"""
        cmd = ["python", "-m", "pytest", test_path]
        
        if verbose:
            cmd.append("-v")
        
        return self._execute_command(cmd)
    
    def check_test_coverage(self):
        """Generate detailed coverage report"""
        print("🔍 Generating test coverage report...")
        
        cmd = [
            "python", "-m", "pytest", "tests/unit/",
            "--cov=src",
            "--cov-report=html:htmlcov",
            "--cov-report=term-missing",
            "--cov-fail-under=70"
        ]
        
        result = self._execute_command(cmd)
        
        if result == 0:
            print("📊 Coverage report generated in htmlcov/index.html")
        
        return result
    
    def lint_tests(self):
        """Run linting on test files"""
        print("🔍 Linting test files...")
        
        # Check if ruff is available
        try:
            subprocess.run(["ruff", "--version"], check=True, capture_output=True)
            cmd = ["ruff", "check", "tests/"]
            return self._execute_command(cmd)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("⚠️  ruff not found, skipping lint check")
            return 0
    
    def run_smoke_tests(self):
        """Run smoke tests to verify basic functionality"""
        cmd = [
            "python", "-m", "pytest", "tests/",
            "-m", "smoke",
            "-v",
            "--tb=short"
        ]
        
        return self._execute_command(cmd)
    
    def _execute_command(self, cmd):
        """Execute command and return exit code"""
        print(f"🚀 Running: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(cmd, cwd=self.project_root, check=False)
            return result.returncode
        except KeyboardInterrupt:
            print("\n⚠️  Test execution interrupted")
            return 1
        except Exception as e:
            print(f"❌ Error executing command: {e}")
            return 1


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description="TickStock Test Runner")
    parser.add_argument(
        "command",
        choices=[
            "unit", "integration", "performance", "all", "quick", "coverage",
            "lint", "smoke", "specific"
        ],
        help="Type of tests to run"
    )
    parser.add_argument("--no-coverage", action="store_true", help="Skip coverage reporting")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--test", help="Specific test file/function to run (for 'specific' command)")
    
    args = parser.parse_args()
    
    runner = TestRunner()
    
    # Map commands to methods
    command_map = {
        "unit": lambda: runner.run_unit_tests(
            coverage=not args.no_coverage,
            verbose=args.verbose
        ),
        "integration": lambda: runner.run_integration_tests(verbose=args.verbose),
        "performance": lambda: runner.run_performance_tests(verbose=args.verbose),
        "all": lambda: runner.run_all_tests(
            coverage=not args.no_coverage,
            verbose=args.verbose
        ),
        "quick": runner.run_quick_tests,
        "coverage": runner.check_test_coverage,
        "lint": runner.lint_tests,
        "smoke": runner.run_smoke_tests,
        "specific": lambda: runner.run_specific_test(
            args.test or "tests/",
            verbose=args.verbose
        )
    }
    
    if args.command == "specific" and not args.test:
        print("❌ --test argument required for 'specific' command")
        return 1
    
    # Execute command
    exit_code = command_map[args.command]()
    
    if exit_code == 0:
        print("✅ Tests completed successfully")
    else:
        print(f"❌ Tests failed with exit code {exit_code}")
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())