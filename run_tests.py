#!/usr/bin/env python3
"""
TickStockAppV2 Integration Test Suite Runner
Run this to execute ALL integration tests.

Usage:
    python run_tests.py
"""

import sys
import os
from pathlib import Path

# Simply run the integration test suite
test_runner = Path(__file__).parent / "tests" / "integration" / "run_integration_tests.py"

if test_runner.exists():
    print("Running TickStockAppV2 Integration Test Suite...")
    os.system(f"{sys.executable} {test_runner}")
else:
    print("ERROR: Integration test runner not found at:")
    print(f"  {test_runner}")
    sys.exit(1)