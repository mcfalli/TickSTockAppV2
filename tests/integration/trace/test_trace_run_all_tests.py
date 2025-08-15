#!/usr/bin/env python3
"""
Test All Trace Scripts
Validates that all trace analysis scripts are working correctly with standardized parameters.
"""

import subprocess
import sys
import os
import json
import io

from pathlib import Path

# Fix Windows console encoding if needed (copied from your validator script)
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

class TraceScriptTester:
    def __init__(self):
        # Determine the directory where this script (test_all_trace_scripts.py) resides.
        # This will be 'C:\Users\McDude\TickStockApp\tests' when run from project root.
        self.script_dir = os.path.dirname(os.path.abspath(__file__))

        # Paths for data files relative to the project root (where this tester script is run from).
        # This means logs/trace/ is expected at C:\Users\McDude\TickStockApp\logs\trace\
        self.DEFAULT_LOG_PATH_RELATIVE_TO_CWD = "./logs/trace/"
        self.TEST_FILE = "trace_all.json" # Default file name for sub-scripts
        self.ALT_PATH = "/tmp/test_trace/" # This is a temporary path, often absolute on Linux/macOS

        # List of sub-scripts to test (filenames only, their full path will be constructed)
        self.scripts_to_test = [
            # Core validation tests
            "test_trace_format_validator.py",
            "test_trace_flow_validation.py",
            # Analysis tests
            "test_trace_emission_timing.py",
            "test_trace_emission_gap.py",
            "test_trace_lost_events.py",
            "test_trace_user_connections.py",
            # New comprehensive tests
            "test_trace_coverage.py",
            "test_trace_statistical.py",
            "test_trace_highlow_analysis.py",
            "test_trace_surge_analysis.py",
            "test_trace_trend_analysis.py",
            # Advanced tests
            "test_trace_diagnostics.py",
            "test_trace_system_health.py",
            "test_trace_visualization.py"
        ]
        # Specific script for separate testing due to different argument signature
        self.DIAGNOSTICS_SCRIPT = "test_trace_diagnostics.py"

    def setup(self):
        """Create test directories if needed"""
        # Ensure the alternative path exists for test scenarios (e.g., /tmp/test_trace/)
        Path(self.ALT_PATH).mkdir(parents=True, exist_ok=True)
        
        # Ensure the default log path exists (useful for creating trace_all.json if it doesn't exist)
        Path(self.DEFAULT_LOG_PATH_RELATIVE_TO_CWD).mkdir(parents=True, exist_ok=True)
        
        # Optional: Create a dummy trace_all.json if it doesn't exist for default tests
        dummy_trace_path = os.path.join(self.DEFAULT_LOG_PATH_RELATIVE_TO_CWD, self.TEST_FILE)
        if not os.path.exists(dummy_trace_path):
            print(f"INFO: Creating dummy {self.TEST_FILE} at {dummy_trace_path}")
            dummy_content = {
                "trace_id": "dummy_trace",
                "duration": 0.0,
                "traces": []
            }
            try:
                with open(dummy_trace_path, 'w') as f:
                    json.dump(dummy_content, f, indent=2)
            except Exception as e:
                print(f"WARNING: Could not create dummy trace file: {e}")


    def run_command(self, cmd: str) -> bool:
        """Run a command and return success status. Prints stdout/stderr on failure."""
        print(f"   Running command: {cmd}") # Debug print
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                encoding='utf-8',  # Specify UTF-8 encoding
                timeout=60 # Increased timeout for potentially longer scripts
            )

            if result.returncode == 0:
                return True
            else:
                print(f"   ✗ Command failed with exit code {result.returncode}")
                if result.stdout:
                    print(f"     STDOUT:\n{result.stdout.strip()}")
                if result.stderr:
                    print(f"     STDERR:\n{result.stderr.strip()}")
                return False
        except subprocess.TimeoutExpired:
            print("   ✗ Command timed out")
            return False
        except Exception as e:
            print(f"   ✗ Error running command: {e}")
            return False

    def test_script(self, script_filename: str) -> bool:
        """Test a single script with various parameters"""
        # Construct the full path to the script relative to where this tester script is located.
        # This will be 'tests/script_filename.py'
        full_script_path_for_execution = os.path.join("tests", script_filename) # Path relative to CWD for subprocess.run

        print(f"\n\n=== Testing {script_filename} ===")
        print("-" * (len(script_filename) + 11))

        results = []

        # Test 1: Help command
        print("1. Testing help:")
        if self.run_command(f"python {full_script_path_for_execution} -h"):
            print("   ✓ Help works")
            results.append(True)
        else:
            print("   ✗ Help failed")
            results.append(False)

        # Test 2: Default parameters (script uses its own defaults)
        print("2. Testing defaults:")
        # The sub-script's argparse default for filename (trace_all.json) and trace_path (./logs/trace/)
        # should work correctly when executed from the project root.
        if self.run_command(f"python {full_script_path_for_execution}"):
            print("   ✓ Default parameters work")
            results.append(True)
        else:
            print("   ✗ Default parameters failed")
            results.append(False)

        # Test 3: With specific file parameter and explicit trace_path
        print("3. Testing with file parameter and explicit path:")
        
        # The filename argument passed to the sub-script should be JUST the filename.
        file_arg_to_subscript = self.TEST_FILE # e.g., "trace_all.json"

        # The trace_path argument passed to the sub-script should be the path relative to THIS script's CWD.
        trace_path_arg_to_subscript = self.DEFAULT_LOG_PATH_RELATIVE_TO_CWD # e.g., "./logs/trace/"

        # Construct the command based on the expected arguments of the sub-script
        command = ""
        if script_filename == "test_trace_flow_validation.py":
            # Flow validation takes: filename, ticker (optional), trace_path (optional)
            command = f"python {full_script_path_for_execution} {file_arg_to_subscript} SYSTEM {trace_path_arg_to_subscript}"
        elif script_filename == "test_trace_format_validator.py":
            # Format validator takes: filename, trace_path (optional)
            command = f"python {full_script_path_for_execution} {file_arg_to_subscript} {trace_path_arg_to_subscript}"
        else:
            # For other scripts, assume they primarily take filename and will use their own defaults for path.
            # This is less robust but works if their internal default is correct.
            # A more robust solution would be to check each script's argparse signature.
            command = f"python {full_script_path_for_execution} {file_arg_to_subscript}"
            # Consider adding the trace_path argument explicitly here as well if all scripts support it:
            # command = f"python {full_script_path_for_execution} {file_arg_to_subscript} {trace_path_arg_to_subscript}"
            # If the script has a ticker, it might fail here without it.
            # This is a common point where script argument variations cause issues.
            # If scripts like 'test_trace_emission_timing.py' also accept a ticker, add it here.

        if self.run_command(command):
            print("   ✓ File parameter and explicit path work")
            results.append(True)
        else:
            print("   ✗ File parameter and explicit path failed")
            results.append(False)
            
        return all(results)
    
    def test_diagnostics_special(self) -> bool:
        """Special test for diagnostics script with multiple files"""
        full_diagnostics_script_path_for_execution = os.path.join("tests", self.DIAGNOSTICS_SCRIPT)

        print(f"\n\n=== Testing {self.DIAGNOSTICS_SCRIPT} ===")
        print("-" * (len(self.DIAGNOSTICS_SCRIPT) + 11))
        print("1. Testing with multiple files:")
        
        # Paths to specific JSON files, relative to the current working directory (project root)
        nvda_json_path = os.path.join(self.DEFAULT_LOG_PATH_RELATIVE_TO_CWD, "NVDA.json")
        system_json_path = os.path.join(self.DEFAULT_LOG_PATH_RELATIVE_TO_CWD, "SYSTEM.json")

        # Diagnostics script expects multiple filenames as positional arguments.
        # It also likely has its own default `trace_path` or expects the files to be found
        # relative to the CWD.
        command = f"python {full_diagnostics_script_path_for_execution} {nvda_json_path} {system_json_path}"

        if self.run_command(command):
            print("   ✓ Multiple files work")
            return True
        else:
            print("   ✗ Multiple files failed")
            return False
    
    def run_all_tests(self) -> bool:
        """Run all tests and report results"""
        print("Testing All Trace Scripts")
        print("=" * 25)
        
        self.setup() # Setup creates dummy trace_all.json if missing

        all_results = []
        
        # Test each standard script
        for script_name in self.scripts_to_test:
            # Check if the script file exists in its expected location (inside 'tests/' subdirectory)
            full_path_to_check = os.path.join(self.script_dir, script_name)
            if os.path.exists(full_path_to_check):
                result = self.test_script(script_name)
                all_results.append((script_name, result))
            else:
                print(f"\n\n=== Skipping {script_name} (not found at {full_path_to_check}) ===")
                all_results.append((script_name, None))
        
        # Special test for diagnostics script
        full_path_to_check_diagnostics = os.path.join(self.script_dir, self.DIAGNOSTICS_SCRIPT)
        if os.path.exists(full_path_to_check_diagnostics):
            result = self.test_diagnostics_special()
            all_results.append((self.DIAGNOSTICS_SCRIPT, result))
        else:
            print(f"\n\n=== Skipping {self.DIAGNOSTICS_SCRIPT} (not found at {full_path_to_check_diagnostics}) ===")
            all_results.append((self.DIAGNOSTICS_SCRIPT, None))
        
        # Summary report
        print("\n\n" + "=" * 50)
        print("SUMMARY REPORT")
        print("=" * 50)
        
        passed = 0
        failed = 0
        skipped = 0
        
        for script, result in all_results:
            if result is None:
                status = "SKIPPED"
                skipped += 1
            elif result:
                status = "✓ PASSED"
                passed += 1
            else:
                status = "✗ FAILED"
                failed += 1
            
            print(f"{script:<40} {status}")
        
        print(f"\nTotal: {len(all_results)} scripts")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Skipped: {skipped}")
        
        print("\n\nAll tests completed!")
        
        return failed == 0

def main():
    """Main entry point"""
    tester = TraceScriptTester()
    success = tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()