#!/usr/bin/env python3
"""
TickStock Combined Startup Script
Launches both TickStockAppV2 (Consumer) and TickStockPL (Producer) services
"""

import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

# Service paths
TICKSTOCKAPP_PATH = Path(__file__).parent
TICKSTOCKPL_PATH = Path("C:/Users/McDude/TickStockPL")
TICKSTOCKPL_PYTHON = TICKSTOCKPL_PATH / "venv" / "Scripts" / "python.exe"

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

def validate_tickstockpl_venv():
    """Validate TickStockPL virtual environment and critical dependencies."""
    print("\n[VALIDATION] Checking TickStockPL virtual environment...")

    if not TICKSTOCKPL_PYTHON.exists():
        print(f"[VALIDATION] ❌ CRITICAL: TickStockPL Python not found at {TICKSTOCKPL_PYTHON}")
        print("[VALIDATION] Expected: C:/Users/McDude/TickStockPL/venv/Scripts/python.exe")
        print("[VALIDATION] Action: Create TickStockPL virtual environment:")
        print("[VALIDATION]   cd C:/Users/McDude/TickStockPL")
        print("[VALIDATION]   python -m venv venv")
        print("[VALIDATION]   venv\\Scripts\\pip install -r requirements.txt")
        return False

    print(f"[VALIDATION] ✅ TickStockPL Python found: {TICKSTOCKPL_PYTHON}")

    # Check critical dependencies
    critical_deps = {
        "apscheduler": "Required for streaming scheduler",
        "websockets": "Required for WebSocket connections",
        "aiohttp": "Required for HTTP API server",
        "redis": "Required for pub-sub messaging",
        "pandas": "Required for data processing"
    }

    missing_deps = []
    for dep, purpose in critical_deps.items():
        result = subprocess.run(
            [str(TICKSTOCKPL_PYTHON), "-c", f"import {dep}"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            missing_deps.append((dep, purpose))
            print(f"[VALIDATION] ❌ Missing: {dep} - {purpose}")
        else:
            print(f"[VALIDATION] ✅ Found: {dep}")

    if missing_deps:
        print(f"\n[VALIDATION] ❌ CRITICAL: {len(missing_deps)} missing dependencies in TickStockPL venv")
        print("[VALIDATION] Action: Install missing dependencies:")
        print("[VALIDATION]   cd C:/Users/McDude/TickStockPL")
        print("[VALIDATION]   venv\\Scripts\\pip install -r requirements.txt")
        print("\n[VALIDATION] Missing packages:")
        for dep, purpose in missing_deps:
            print(f"[VALIDATION]   - {dep}: {purpose}")
        return False

    print("[VALIDATION] ✅ All critical TickStockPL dependencies verified")
    return True

def validate_service_health(process, service_name, timeout=3):
    """Validate that a service started successfully by checking if it's still running."""
    if not process:
        return False

    time.sleep(timeout)

    if process.poll() is not None:
        exit_code = process.poll()
        print(f"\n[VALIDATION] ❌ CRITICAL: {service_name} crashed immediately (exit code: {exit_code})")
        print("[VALIDATION] Service failed to start - check logs above for error details")
        return False

    print(f"[VALIDATION] ✅ {service_name} running (PID: {process.pid})")
    return True

def start_tickstockpl():
    """Start TickStockPL HTTP API server."""
    print("\n[TickStockPL API] Starting HTTP API server...")

    if not TICKSTOCKPL_PATH.exists():
        print(f"[TickStockPL API] ERROR: Path not found: {TICKSTOCKPL_PATH}")
        return None

    # Use the new HTTP API server (Sprint 33 Phase 4)
    service_script = TICKSTOCKPL_PATH / "start_api_server.py"

    if not service_script.exists():
        print(f"[TickStockPL API] ERROR: API server script not found at {service_script}")
        print("Please ensure TickStockPL has been updated with Sprint 33 Phase 4 HTTP API implementation")
        return None

    try:
        process = subprocess.Popen(
            [str(TICKSTOCKPL_PYTHON), str(service_script)],
            cwd=str(TICKSTOCKPL_PATH),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Merge stderr into stdout
            text=True,
            bufsize=1,
            universal_newlines=True
        )

        # Monitor output in a separate thread
        def monitor_output():
            for line in iter(process.stdout.readline, ''):
                if line:
                    print(f"[TickStockPL API] {line.rstrip()}")
                if stop_event.is_set():
                    break

        monitor_thread = threading.Thread(target=monitor_output, daemon=True)
        monitor_thread.start()

        print("[TickStockPL API] Service started successfully")
        return process

    except Exception as e:
        print(f"[TickStockPL API] ERROR: Failed to start service: {e}")
        return None

def start_data_load_handler():
    """Start TickStockPL Data Load Job Handler (for admin historical imports)."""
    print("\n[TickStockPL DataLoader] Starting Data Load Job Handler...")

    if not TICKSTOCKPL_PATH.exists():
        print(f"[TickStockPL DataLoader] ERROR: Path not found: {TICKSTOCKPL_PATH}")
        return None

    try:
        process = subprocess.Popen(
            [str(TICKSTOCKPL_PYTHON), "-m", "src.jobs.data_load_handler"],
            cwd=str(TICKSTOCKPL_PATH),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Merge stderr into stdout
            text=True,
            bufsize=1,
            universal_newlines=True
        )

        # Monitor output in a separate thread
        def monitor_output():
            for line in iter(process.stdout.readline, ''):
                if line:
                    print(f"[TickStockPL DataLoader] {line.rstrip()}")
                if stop_event.is_set():
                    break

        monitor_thread = threading.Thread(target=monitor_output, daemon=True)
        monitor_thread.start()

        # Wait a moment and check if process started successfully
        time.sleep(0.5)
        if process.poll() is not None:
            print(f"[TickStockPL DataLoader] ERROR: Process exited immediately with code {process.poll()}")
            return None

        print("[TickStockPL DataLoader] Service started successfully")
        return process

    except Exception as e:
        print(f"[TickStockPL DataLoader] ERROR: Failed to start service: {e}")
        return None

def start_streaming_service():
    """Start TickStockPL Streaming Service (intraday real-time processing)."""
    print("\n[TickStockPL Streaming] Starting Streaming Service...")

    if not TICKSTOCKPL_PATH.exists():
        print(f"[TickStockPL Streaming] ERROR: Path not found: {TICKSTOCKPL_PATH}")
        return None

    streaming_script = TICKSTOCKPL_PATH / "streaming_service.py"
    if not streaming_script.exists():
        print(f"[TickStockPL Streaming] ERROR: streaming_service.py not found at {streaming_script}")
        return None

    try:
        process = subprocess.Popen(
            [str(TICKSTOCKPL_PYTHON), str(streaming_script)],
            cwd=str(TICKSTOCKPL_PATH),
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
                    print(f"[TickStockPL Streaming] {line.rstrip()}")
                if stop_event.is_set():
                    break

        monitor_thread = threading.Thread(target=monitor_output, daemon=True)
        monitor_thread.start()

        # Wait a moment and check if process started successfully
        time.sleep(1)
        if process.poll() is not None:
            print(f"[TickStockPL Streaming] ERROR: Process exited immediately with code {process.poll()}")
            return None

        print("[TickStockPL Streaming] Service started successfully")
        return process

    except Exception as e:
        print(f"[TickStockPL Streaming] ERROR: Failed to start service: {e}")
        return None

def start_tickstockapp():
    """Start TickStockAppV2 web application."""
    print("\n[TickStockAppV2] Starting web application...")

    app_script = TICKSTOCKAPP_PATH / "src" / "app.py"
    if not app_script.exists():
        print("[TickStockAppV2] ERROR: app.py not found")
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
    print("This will start all services:")
    print("  1. TickStockAppV2 (Consumer) - Web UI on port 5000")
    print("  2. TickStockPL API (Producer) - HTTP API server on port 8080")
    print("  3. TickStockPL DataLoader - Historical import job handler")
    print("  4. TickStockPL Streaming - Intraday real-time processing")
    print("="*60)

    # Register shutdown handler
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    # CRITICAL: Validate TickStockPL virtual environment FIRST
    if not validate_tickstockpl_venv():
        print("\n" + "="*60)
        print("❌ STARTUP ABORTED: TickStockPL virtual environment validation failed")
        print("="*60)
        print("REASON: Missing Python interpreter or critical dependencies")
        print("ACTION: Follow the instructions above to set up TickStockPL environment")
        print("="*60)
        return 1

    # Check dependencies
    print("\n[VALIDATION] Checking infrastructure dependencies...")

    redis_ok = check_redis()
    postgres_ok = check_postgres()

    if not redis_ok:
        print("\n" + "="*60)
        print("❌ STARTUP ABORTED: Redis not running")
        print("="*60)
        print("REASON: Redis is REQUIRED for pub-sub communication between services")
        print("ACTION: Start Redis server on localhost:6379")
        print("  - Docker: docker run -d -p 6379:6379 --name redis redis:latest")
        print("  - Windows: redis-server.exe")
        print("="*60)
        return 1
    print("[VALIDATION] ✅ Redis is running")

    if not postgres_ok:
        print("\n" + "="*60)
        print("❌ STARTUP ABORTED: PostgreSQL not running")
        print("="*60)
        print("REASON: PostgreSQL is REQUIRED for data storage and pattern detection")
        print("ACTION: Start PostgreSQL service on localhost:5432")
        print("  - Windows: Start-Service postgresql-x64-14")
        print("  - Linux: sudo systemctl start postgresql")
        print("="*60)
        return 1
    print("[VALIDATION] ✅ PostgreSQL is running")

    # Check port availability
    PORT = 5000
    if not check_port_available(PORT):
        print(f"\n[VALIDATION] Port {PORT} is in use. Attempting to free it...")
        if kill_process_on_port(PORT):
            print(f"[VALIDATION] ✅ Port {PORT} freed successfully")
        else:
            print("\n" + "="*60)
            print(f"❌ STARTUP ABORTED: Port {PORT} is in use and could not be freed")
            print("="*60)
            print(f"REASON: Another process is using port {PORT}")
            print("ACTION: Manually kill the process or use a different port")
            print("  - Find process: powershell -c \"Get-NetTCPConnection -LocalPort 5000\"")
            print("  - Kill process: taskkill /F /PID <process_id>")
            print("="*60)
            return 1

    print(f"[VALIDATION] ✅ Port {PORT} is available")

    print("\n" + "="*60)
    print("Starting services...")
    print("="*60)

    # Start TickStockAppV2 first (consumer needs to be ready)
    app_process = start_tickstockapp()
    if not app_process:
        print("\n" + "="*60)
        print("❌ STARTUP ABORTED: TickStockAppV2 failed to start")
        print("="*60)
        print("REASON: Core web application could not be launched")
        print("ACTION: Check error messages above for details")
        print("="*60)
        return 1

    processes.append(app_process)
    print("[TickStockAppV2] Waiting for initialization...")
    time.sleep(7)  # Initial wait for process launch

    if not validate_service_health(app_process, "TickStockAppV2", timeout=3):
        print("\n" + "="*60)
        print("❌ STARTUP ABORTED: TickStockAppV2 crashed during initialization")
        print("="*60)
        print("REASON: Service started but terminated unexpectedly")
        print("ACTION: Check logs above for Python errors or missing dependencies")
        print("="*60)
        shutdown_handler(None, None)
        return 1

    # Start TickStockPL Data Load Handler (for admin historical imports)
    dataloader_process = start_data_load_handler()
    if not dataloader_process:
        print("\n" + "="*60)
        print("❌ STARTUP ABORTED: TickStockPL DataLoader failed to start")
        print("="*60)
        print("REASON: Historical data import handler is REQUIRED")
        print("ACTION: Check error messages above - verify TickStockPL installation")
        print("="*60)
        shutdown_handler(None, None)
        return 1

    processes.append(dataloader_process)
    if not validate_service_health(dataloader_process, "TickStockPL DataLoader", timeout=2):
        print("\n" + "="*60)
        print("❌ STARTUP ABORTED: TickStockPL DataLoader crashed during initialization")
        print("="*60)
        print("REASON: Service started but terminated unexpectedly")
        print("ACTION: Check logs above for import errors or dependency issues")
        print("="*60)
        shutdown_handler(None, None)
        return 1

    # Start TickStockPL API server
    pl_process = start_tickstockpl()
    if not pl_process:
        print("\n" + "="*60)
        print("❌ STARTUP ABORTED: TickStockPL API failed to start")
        print("="*60)
        print("REASON: HTTP API server is REQUIRED for pattern/indicator queries")
        print("ACTION: Check error messages above - verify start_api_server.py exists")
        print("="*60)
        shutdown_handler(None, None)
        return 1

    processes.append(pl_process)
    if not validate_service_health(pl_process, "TickStockPL API", timeout=2):
        print("\n" + "="*60)
        print("❌ STARTUP ABORTED: TickStockPL API crashed during initialization")
        print("="*60)
        print("REASON: Service started but terminated unexpectedly")
        print("ACTION: Check logs above for Flask errors or port conflicts")
        print("="*60)
        shutdown_handler(None, None)
        return 1

    # Start TickStockPL Streaming Service (intraday real-time processing)
    streaming_process = start_streaming_service()
    if not streaming_process:
        print("\n" + "="*60)
        print("❌ STARTUP ABORTED: TickStockPL Streaming failed to start")
        print("="*60)
        print("REASON: Streaming service is REQUIRED for intraday pattern detection")
        print("ACTION: Check error messages above - verify streaming_service.py exists")
        print("="*60)
        shutdown_handler(None, None)
        return 1

    processes.append(streaming_process)
    if not validate_service_health(streaming_process, "TickStockPL Streaming", timeout=2):
        print("\n" + "="*60)
        print("❌ STARTUP ABORTED: TickStockPL Streaming crashed during initialization")
        print("="*60)
        print("REASON: Service started but terminated unexpectedly")
        print("ACTION: Check logs above for scheduler or WebSocket errors")
        print("="*60)
        shutdown_handler(None, None)
        return 1

    print("\n" + "="*60)
    print("SERVICES RUNNING")
    print("="*60)
    print("[OK] TickStockAppV2: http://localhost:5000")
    print("[OK] TickStockPL DataLoader: Listening on tickstock.jobs.data_load" if dataloader_process else "[WARNING] TickStockPL DataLoader: Offline")
    print("[OK] TickStockPL API: http://localhost:8080" if pl_process else "[WARNING] TickStockPL API: Offline (fallback mode)")
    print("[OK] TickStockPL Streaming: Active (9:30 AM - 4:00 PM ET)" if streaming_process else "[WARNING] TickStockPL Streaming: Offline")
    print("\nPress Ctrl+C to stop all services")
    print("="*60)

    # Keep running until interrupted
    try:
        while True:
            # Check if processes are still running
            for i, process in enumerate(processes[:]):  # Copy list to avoid modification during iteration
                if process and process.poll() is not None:
                    # Process has actually stopped (poll() returns exit code)
                    exit_code = process.poll()
                    if i == 0:
                        # TickStockAppV2 (critical) stopped
                        print(f"\nERROR: TickStockAppV2 stopped unexpectedly (exit code: {exit_code})")
                        print("Shutting down remaining services...")
                        shutdown_handler(None, None)
                    elif i == 1:
                        # TickStockPL DataLoader stopped
                        print(f"\nWARNING: TickStockPL DataLoader stopped unexpectedly (exit code: {exit_code})")
                        print("Admin historical imports will not work until restarted")
                        print("Removing from monitoring list...")
                        processes.remove(process)
                        break  # Exit loop after removing to avoid index issues
                    elif i == 2:
                        # TickStockPL API stopped
                        print(f"\nWARNING: TickStockPL API stopped unexpectedly (exit code: {exit_code})")
                        print("Pattern detection will use fallback mode")
                        print("Removing from monitoring list...")
                        processes.remove(process)
                        break  # Exit loop after removing to avoid index issues
                    else:
                        # TickStockPL Streaming stopped
                        print(f"\nWARNING: TickStockPL Streaming stopped unexpectedly (exit code: {exit_code})")
                        print("Intraday real-time processing will not work until restarted")
                        print("Removing from monitoring list...")
                        processes.remove(process)
                        break  # Exit loop after removing to avoid index issues
            time.sleep(5)
    except KeyboardInterrupt:
        shutdown_handler(None, None)

if __name__ == "__main__":
    sys.exit(main())
