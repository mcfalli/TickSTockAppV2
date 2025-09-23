#!/usr/bin/env python3
"""
TickStock Combined Startup Script
Launches both TickStockAppV2 (Consumer) and TickStockPL (Producer) services
"""

import os
import sys
import time
import signal
import subprocess
import threading
from pathlib import Path

# Service paths
TICKSTOCKAPP_PATH = Path(__file__).parent
TICKSTOCKPL_PATH = Path("C:/Users/McDude/TickStockPL")

# Running processes
processes = []
stop_event = threading.Event()

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
        result = subprocess.run([
            "powershell", "-c",
            f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -First 1"
        ], capture_output=True, text=True)

        if result.stdout.strip():
            pid = result.stdout.strip()
            print(f"Killing process {pid} using port {port}...")
            subprocess.run(["powershell", "-c", f"Stop-Process -Id '{pid}' -Force"], check=False)
            time.sleep(2)
            return True
        return False
    except Exception as e:
        print(f"Error killing process on port {port}: {e}")
        return False

def check_redis():
    """Check if Redis is running (Docker or local)."""
    try:
        # Check Docker first
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=redis", "--format", "{{.Names}}"],
            capture_output=True,
            text=True
        )
        if "redis" in result.stdout.lower():
            return True

        # Check for local redis-server process
        result = subprocess.run(
            ["powershell", "-c", "Get-Process redis-server -ErrorAction SilentlyContinue"],
            capture_output=True,
            text=True
        )
        return len(result.stdout.strip()) > 0
    except:
        return False

def check_postgres():
    """Check if PostgreSQL is running."""
    try:
        result = subprocess.run(
            ["powershell", "-c", "Get-Service postgresql* | Where-Object {$_.Status -eq 'Running'}"],
            capture_output=True,
            text=True
        )
        return len(result.stdout.strip()) > 0
    except:
        return False

def start_tickstockpl():
    """Start TickStockPL pattern detection service."""
    print("\n[TickStockPL] Starting pattern detection service...")

    if not TICKSTOCKPL_PATH.exists():
        print(f"[TickStockPL] ERROR: Path not found: {TICKSTOCKPL_PATH}")
        return None

    # Use the production pattern detection service from src/services
    service_script = TICKSTOCKPL_PATH / "src" / "services" / "pattern_detection_service.py"

    # Fallback to launcher script if main script not found
    if not service_script.exists():
        service_script = TICKSTOCKPL_PATH / "src" / "services" / "launch_pattern_detection_service.py"

    if not service_script.exists():
        print(f"[TickStockPL] ERROR: Service script not found at {service_script}")
        return None

    try:
        process = subprocess.Popen(
            [sys.executable, str(service_script)],
            cwd=str(TICKSTOCKPL_PATH),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )

        # Monitor output in a separate thread
        def monitor_output():
            for line in iter(process.stdout.readline, ''):
                if line:
                    print(f"[TickStockPL] {line.rstrip()}")
                if stop_event.is_set():
                    break

        monitor_thread = threading.Thread(target=monitor_output, daemon=True)
        monitor_thread.start()

        print("[TickStockPL] Service started successfully")
        return process

    except Exception as e:
        print(f"[TickStockPL] ERROR: Failed to start service: {e}")
        return None

def start_tickstockapp():
    """Start TickStockAppV2 web application."""
    print("\n[TickStockAppV2] Starting web application...")

    app_script = TICKSTOCKAPP_PATH / "src" / "app.py"
    if not app_script.exists():
        print(f"[TickStockAppV2] ERROR: app.py not found")
        return None

    try:
        process = subprocess.Popen(
            [sys.executable, str(app_script)],
            cwd=str(TICKSTOCKAPP_PATH),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )

        # Monitor output in a separate thread
        def monitor_output():
            for line in iter(process.stdout.readline, ''):
                if line:
                    # Filter out unicode errors and verbose logs
                    if "UnicodeEncodeError" not in line and "charmap" not in line:
                        print(f"[TickStockAppV2] {line.rstrip()}")
                if stop_event.is_set():
                    break

        monitor_thread = threading.Thread(target=monitor_output, daemon=True)
        monitor_thread.start()

        print("[TickStockAppV2] Service started successfully")
        return process

    except Exception as e:
        print(f"[TickStockAppV2] ERROR: Failed to start service: {e}")
        return None

def shutdown_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    print("\n" + "="*60)
    print("SHUTDOWN: Stopping all services...")
    print("="*60)

    stop_event.set()

    for process in processes:
        if process and process.poll() is None:
            print(f"Terminating process {process.pid}...")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

    print("All services stopped")
    sys.exit(0)

def main():
    """Main startup function."""
    print("="*60)
    print("TICKSTOCK COMBINED SERVICE LAUNCHER")
    print("="*60)
    print("This will start both:")
    print("  1. TickStockAppV2 (Consumer) - Web UI on port 5000")
    print("  2. TickStockPL (Producer) - Pattern detection service")
    print("="*60)

    # Register shutdown handler
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    # Check dependencies
    print("\nChecking dependencies...")

    if not check_redis():
        print("WARNING: Redis not detected. Services may fail to communicate.")
        print("Please ensure Redis is running on localhost:6379")
    else:
        print("[OK] Redis is running")

    if not check_postgres():
        print("WARNING: PostgreSQL not detected. Pattern detection may fail.")
        print("Please ensure PostgreSQL is running on localhost:5432")
    else:
        print("[OK] PostgreSQL is running")

    # Check port availability
    PORT = 5000
    if not check_port_available(PORT):
        print(f"\nWARNING: Port {PORT} is in use. Attempting to free it...")
        if kill_process_on_port(PORT):
            print(f"SUCCESS: Port {PORT} freed successfully")
        else:
            print(f"ERROR: Could not free port {PORT}. Please check manually.")
            return 1

    print(f"[OK] Port {PORT} is available")

    print("\n" + "="*60)
    print("Starting services...")
    print("="*60)

    # Start TickStockAppV2 first (consumer needs to be ready)
    app_process = start_tickstockapp()
    if app_process:
        processes.append(app_process)
        print("[TickStockAppV2] Waiting for initialization...")
        time.sleep(10)  # Give it time to initialize Redis subscribers
    else:
        print("ERROR: Failed to start TickStockAppV2")
        return 1

    # Start TickStockPL pattern detection
    pl_process = start_tickstockpl()
    if pl_process:
        processes.append(pl_process)
    else:
        print("WARNING: TickStockPL not started. Pattern detection will use fallback mode.")

    print("\n" + "="*60)
    print("SERVICES RUNNING")
    print("="*60)
    print("[OK] TickStockAppV2: http://localhost:5000")
    print("[OK] Pattern Detection: Active" if pl_process else "[WARNING] Pattern Detection: Fallback mode")
    print("\nPress Ctrl+C to stop all services")
    print("="*60)

    # Keep running until interrupted
    try:
        while True:
            # Check if processes are still running
            for i, process in enumerate(processes):
                if process and process.poll() is not None:
                    if i == 0:
                        print("\nERROR: TickStockAppV2 stopped unexpectedly")
                    else:
                        print("\nWARNING: TickStockPL stopped unexpectedly")
            time.sleep(5)
    except KeyboardInterrupt:
        shutdown_handler(None, None)

if __name__ == "__main__":
    sys.exit(main())