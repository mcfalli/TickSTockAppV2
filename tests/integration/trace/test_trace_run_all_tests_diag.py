#!/usr/bin/env python3
"""
Test All Trace Scripts with Debugging
Shows actual errors when tests fail.
"""

import subprocess
import sys
import os
import json
import io

from pathlib import Path
from typing import Tuple, List, Dict, Set, Optional, Any # <--- ADD/ENSURE THIS LINE

# Fix Windows console encoding for proper output display
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

class TraceScriptTesterDebug:
    def __init__(self):
        # Determine the directory where this tester script resides.
        # This will be 'C:\Users\McDude\TickStockApp\tests' when run from project root.
        self.script_dir = os.path.dirname(os.path.abspath(__file__))

        # Paths for data files. These are relative to the Current Working Directory (CWD)
        # from which the main tester script is executed (e.g., TickStockApp/).
        self.DEFAULT_LOG_PATH_RELATIVE_TO_CWD = "./logs/trace/"
        self.TEST_FILE = "trace_all.json" # Default trace file name for sub-scripts
        self.ALT_PATH = "/tmp/test_trace/" # An alternative path, often for temporary files

        # List of sub-scripts to test (filenames only)
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
        
        # Specific script for separate testing due to potentially different argument signatures
        self.DIAGNOSTICS_SCRIPT = "test_trace_diagnostics.py"

    def setup(self):
        """Create test directories and dummy trace file if needed."""
        # Ensure the alternative path exists for test scenarios
        Path(self.ALT_PATH).mkdir(parents=True, exist_ok=True)
        
        # Ensure the default log path exists (where trace files are expected)
        Path(self.DEFAULT_LOG_PATH_RELATIVE_TO_CWD).mkdir(parents=True, exist_ok=True)
        
        # Create a dummy trace_all.json if it doesn't exist, to prevent immediate failures
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

    def run_command(self, cmd: str, show_output: bool = False) -> Tuple[bool, str, str]:
        """
        Run a command and return success status, stdout, and stderr.
        Prints output/error if show_output is True and command fails.
        """
        print(f"   Running command: {cmd}") # Always show the command being run
        try:
            result = subprocess.run(
                cmd, 
                shell=True, 
                capture_output=True, 
                text=True,
                encoding='utf-8',  # Specify UTF-8 encoding
                timeout=60 # Increased timeout for potentially longer scripts
            )
            
            if show_output and result.returncode != 0:
                print(f"   Command failed with exit code {result.returncode}")
                if result.stdout:
                    print(f"   STDOUT:\n{result.stdout.strip()}")
                if result.stderr:
                    print(f"   STDERR:\n{result.stderr.strip()}")
            
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            print("   ✗ Command timed out")
            return False, "", "TimeoutExpired"
        except Exception as e:
            print(f"   ✗ Error running command: {e}")
            return False, "", str(e)
    
    def test_script(self, script_filename: str, debug: bool = True) -> bool:
        """Test a single script with various parameters."""
        # Construct the path to the sub-script relative to the current working directory (project root).
        # This will be 'tests/script_filename.py'
        full_script_path_for_execution = os.path.join("tests", script_filename)

        print(f"\n\n=== Testing {script_filename} ===")
        print("-" * (len(script_filename) + 11)) # Dynamic separator length
        
        results = []
        
        # Test 1: Help command
        print("1. Testing help:")
        success, stdout, stderr = self.run_command(f"python {full_script_path_for_execution} -h", show_output=debug)
        if success:
            print("   ✓ Help works")
            results.append(True)
        else:
            print("   ✗ Help failed")
            if debug: # Only show error if debug is enabled
                print(f"   Error: {stderr[:200]}")
            results.append(False)
        
        # Test 2: Default parameters (sub-script uses its own defaults)
        print("2. Testing defaults:")
        # The sub-script's argparse default for filename ('trace_all.json') and
        # trace_path ('./logs/trace/') should work correctly when executed from the project root.
        success, stdout, stderr = self.run_command(f"python {full_script_path_for_execution}", show_output=debug)
        if success:
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

        # Construct the command based on the expected arguments of the sub-script.
        # This handles the specific argument signatures of your known scripts.
        command = ""
        if script_filename == "test_trace_flow_validation.py":
            # Flow validation takes: filename, ticker (optional), trace_path (optional)
            command = (f"python {full_script_path_for_execution} "
                       f"{file_arg_to_subscript} SYSTEM {trace_path_arg_to_subscript}")
        elif script_filename == "test_trace_format_validator.py":
            # Format validator takes: filename, trace_path (optional)
            command = (f"python {full_script_path_for_execution} "
                       f"{file_arg_to_subscript} {trace_path_arg_to_subscript}")
        else:
            # For other scripts, assume they primarily take filename and will use their own defaults for path.
            # If these scripts also support a trace_path argument, it's safer to pass it explicitly.
            # Adjust this 'else' block if other scripts consistently need trace_path or a ticker.
            command = (f"python {full_script_path_for_execution} "
                       f"{file_arg_to_subscript}")
            # If all scripts accept trace_path as a last optional arg, you could use:
            # command = f"python {full_script_path_for_execution} {file_arg_to_subscript} {trace_path_arg_to_subscript}"

        success, stdout, stderr = self.run_command(command, show_output=debug)
        if success:
            print("   ✓ File parameter and explicit path work")
            results.append(True)
        else:
            print("   ✗ File parameter and explicit path failed")
            results.append(False)
            
        return all(results)
    
    def test_diagnostics_special(self, debug: bool = True) -> bool:
        """Special test for diagnostics script with multiple files."""
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
        command = (f"python {full_diagnostics_script_path_for_execution} "
                   f"{nvda_json_path} {system_json_path}")

        success, stdout, stderr = self.run_command(command, show_output=debug)
        
        if success:
            print("   ✓ Multiple files work")
            return True
        else:
            print("   ✗ Multiple files failed")
            return False
    
    def check_trace_files(self) -> bool:
        """Check if required trace files exist in the default log path."""
        print("\n" + "="*50)
        print("Checking trace files...")
        print("="*50)
        
        files_to_check = [self.TEST_FILE, "NVDA.json", "SYSTEM.json"] # Using self.TEST_FILE here
        missing_files = []
        
        for file in files_to_check:
            full_path = os.path.join(self.DEFAULT_LOG_PATH_RELATIVE_TO_CWD, file)
            if os.path.exists(full_path):
                size = os.path.getsize(full_path)
                print(f"✓ {file:<20} exists ({size:,} bytes)")
            else:
                print(f"✗ {file:<20} MISSING")
                missing_files.append(file)
        
        if missing_files:
            print(f"\n⚠️  Missing files: {', '.join(missing_files)}")
            print(f"   Make sure trace files exist in: {self.DEFAULT_LOG_PATH_RELATIVE_TO_CWD}")
        
        return len(missing_files) == 0
    
    def run_all_tests(self, debug: bool = True) -> bool:
        """Run all tests and report results."""
        print("Testing All Trace Scripts (Debug Mode)")
        print("=" * 40)
        
        # First check if trace files exist
        trace_files_exist = self.check_trace_files()
        
        if not trace_files_exist:
            print("\n⚠️  Some trace files are missing. Tests may fail.")
            response = input("\nContinue anyway? (y/n): ")
            if response.lower() != 'y':
                print("Exiting...")
                return False
        
        self.setup() # Setup creates dummy trace_all.json if missing

        all_results = []
        
        # Test each standard script
        for script_name in self.scripts_to_test:
            # Check if the script file exists in its expected location (inside 'tests/' subdirectory)
            full_path_to_check_script = os.path.join(self.script_dir, script_name)
            if os.path.exists(full_path_to_check_script):
                result = self.test_script(script_name, debug=debug)
                all_results.append((script_name, result))
            else:
                print(f"\n\n=== Skipping {script_name} (not found at {full_path_to_check_script}) ===")
                all_results.append((script_name, None))
        
        # Special test for diagnostics script
        full_path_to_check_diagnostics = os.path.join(self.script_dir, self.DIAGNOSTICS_SCRIPT)
        if os.path.exists(full_path_to_check_diagnostics):
            result = self.test_diagnostics_special(debug=debug)
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
        
        # If there were failures, suggest next steps
        if failed > 0:
            print("\n" + "="*50)
            print("DEBUGGING SUGGESTIONS")
            print("="*50)
            print(f"1. Ensure trace files exist in: {self.DEFAULT_LOG_PATH_RELATIVE_TO_CWD}")
            print("2. Check that trace files contain valid JSON.")
            print("3. Review the STDOUT/STDERR output above for specific error messages from failed tests.")
            print("4. Try running a failing script manually to see its full output (e.g.):")
            print(f"   python {os.path.join('tests', 'test_trace_flow_validation.py')} trace_all.json SYSTEM {self.DEFAULT_LOG_PATH_RELATIVE_TO_CWD}")
            print("5. Verify the argument order and types expected by each sub-script's `ArgumentParser`.")
        
        print("\n\nAll tests completed!")
        
        return failed == 0

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test all trace scripts with debugging')
    parser.add_argument('--no-debug', action='store_true', 
                        help='Disable debug output')
    
    args = parser.parse_args()
    
    tester = TraceScriptTesterDebug()
    success = tester.run_all_tests(debug=not args.no_debug)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()