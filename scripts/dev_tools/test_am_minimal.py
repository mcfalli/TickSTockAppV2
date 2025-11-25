"""
Minimal AM Aggregate Test - Outputs to file to avoid encoding issues
"""
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

def load_api_key():
    """Load API key from .env file"""
    env_path = Path(__file__).parent.parent.parent / '.env'

    if not env_path.exists():
        return None

    api_key = None
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('MASSIVE_API_KEY='):
                api_key = line.split('=', 1)[1].strip()
                break

    return api_key

def test_am_websocket():
    """Test AM websocket and log results to file"""
    import websocket
    import threading

    api_key = load_api_key()
    if not api_key:
        print("ERROR: No API key found")
        return

    log_file = Path(__file__).parent / 'test_am_output.txt'

    def log(msg):
        """Write to both console and file"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        line = f"{timestamp} - {msg}"
        print(line)
        with open(log_file, 'a') as f:
            f.write(line + '\n')

    # Clear log file
    with open(log_file, 'w') as f:
        f.write(f"=== AM Aggregate Test Started at {datetime.now()} ===\n\n")

    stats = {
        'connected': False,
        'authenticated': False,
        'messages_received': 0,
        'am_bars_received': 0,
        'other_events': 0
    }

    def on_open(ws):
        log("[1/3] Connected to WebSocket")
        stats['connected'] = True

        log("[2/3] Sending authentication...")
        auth_msg = {"action": "auth", "params": api_key}
        ws.send(json.dumps(auth_msg))

    def on_message(ws, message):
        stats['messages_received'] += 1
        log(f"Message #{stats['messages_received']} received (len={len(message)})")

        try:
            data = json.loads(message)

            if isinstance(data, list):
                for msg in data:
                    process_message(msg, ws)
            else:
                process_message(data, ws)
        except Exception as e:
            log(f"ERROR parsing message: {e}")

    def process_message(msg, ws):
        if msg.get('ev') == 'status':
            if msg.get('status') == 'auth_success':
                stats['authenticated'] = True
                log("[2/3] Authentication SUCCESS")

                # Subscribe to 3 tickers with AM prefix
                log("[3/3] Subscribing to AM.SPY,AM.AAPL,AM.NVDA...")
                subscribe_msg = {
                    "action": "subscribe",
                    "params": "AM.SPY,AM.AAPL,AM.NVDA"
                }
                ws.send(json.dumps(subscribe_msg))
                log("[3/3] Subscription sent")
            else:
                status = msg.get('status')
                message = msg.get('message', '')
                log(f"Status: {status} - {message}")

        elif msg.get('ev') == 'AM':
            stats['am_bars_received'] += 1
            sym = msg.get('sym')
            close = msg.get('c')
            vol = msg.get('v')
            log(f"AM BAR #{stats['am_bars_received']}: {sym} close={close} vol={vol}")

        else:
            stats['other_events'] += 1
            ev_type = msg.get('ev', 'unknown')
            log(f"Other event: {ev_type}")

    def on_error(ws, error):
        log(f"ERROR: {error}")

    def on_close(ws, close_status_code, close_msg):
        log(f"Connection closed: {close_status_code} - {close_msg}")

    # Create and run WebSocket
    log("Creating WebSocket connection...")
    ws = websocket.WebSocketApp(
        "wss://socket.massive.com/stocks",
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )

    ws_thread = threading.Thread(
        target=ws.run_forever,
        kwargs={'ping_interval': 30, 'ping_timeout': 10}
    )
    ws_thread.daemon = True
    ws_thread.start()

    # Wait for auth
    log("Waiting for authentication...")
    timeout = 10
    start = time.time()
    while time.time() - start < timeout:
        if stats['authenticated']:
            break
        time.sleep(0.5)

    if not stats['authenticated']:
        log("FAILED: Authentication timeout")
        return

    # Listen for 90 seconds to catch at least one minute boundary
    log("Listening for 90 seconds...")
    time.sleep(90)

    ws.close()
    time.sleep(1)

    # Final results
    log("\n=== RESULTS ===")
    log(f"Connected: {stats['connected']}")
    log(f"Authenticated: {stats['authenticated']}")
    log(f"Total messages: {stats['messages_received']}")
    log(f"AM bars received: {stats['am_bars_received']}")
    log(f"Other events: {stats['other_events']}")

    if stats['am_bars_received'] > 0:
        log("SUCCESS: Received AM aggregates")
    else:
        log("FAILED: No AM aggregates received")

    log(f"\nFull log saved to: {log_file}")

if __name__ == '__main__':
    test_am_websocket()
