#!/usr/bin/env python3
"""
TickStockAppV2 Startup Script
Handles port conflicts and provides clean startup/shutdown
"""

import os
import subprocess
import sys
import time
from pathlib import Path


def check_port_available(port):
    """Check if a port is available."""
    try:
        result = subprocess.run(
            ["powershell", "-c", f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue"],
            capture_output=True,
            text=True
        )
        return len(result.stdout.strip()) == 0
    except:
        return True

def kill_process_on_port(port):
    """Kill any process using the specified port."""
    try:
        # Get process using the port
        result = subprocess.run([
            "powershell", "-c",
            f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -First 1"
        ], capture_output=True, text=True)

        if result.stdout.strip():
            pid = result.stdout.strip()
            print(f"Killing process {pid} using port {port}...")
            subprocess.run(["powershell", "-c", f"Stop-Process -Id '{pid}' -Force"], check=False)
            time.sleep(2)  # Give it time to clean up
            return True
        return False
    except Exception as e:
        print(f"Error killing process on port {port}: {e}")
        return False

def main():
    """Main startup function."""
    print("="*60)
    print("TickStockAppV2 Startup Script")
    print("="*60)

    PORT = 5000

    # Check if port is available
    if not check_port_available(PORT):
        print(f"WARNING: Port {PORT} is in use. Attempting to free it...")
        if kill_process_on_port(PORT):
            print(f"SUCCESS: Port {PORT} freed successfully")
        else:
            print(f"ERROR: Could not free port {PORT}. Please check manually.")
            return 1

    print(f"SUCCESS: Port {PORT} is available")
    print("Starting TickStockAppV2...")
    print("="*60)

    # Change to the correct directory
    os.chdir(Path(__file__).parent)

    try:
        # Start the application
        subprocess.run([sys.executable, "src/app.py"], check=True)
    except KeyboardInterrupt:
        print("\nApplication stopped by user")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"Application exited with error code {e.returncode}")
        return e.returncode
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
