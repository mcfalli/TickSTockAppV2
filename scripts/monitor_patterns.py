"""Monitor Redis for pattern events from TickStockPL"""
import redis
import time
import json

def monitor_patterns():
    print("Connecting to Redis...")
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)

    # Test connection
    try:
        r.ping()
        print("[OK] Connected to Redis")
    except Exception as e:
        print(f"[ERROR] Redis connection failed: {e}")
        return

    # Subscribe to pattern channels
    pubsub = r.pubsub()
    channels = [
        'tickstock.events.patterns',
        'tickstock.events.patterns.daily',
        'tickstock.events.patterns.intraday',
        'tickstock.events.patterns.combo'
    ]

    for channel in channels:
        pubsub.subscribe(channel)
        print(f"Subscribed to: {channel}")

    print("\nMonitoring for pattern events (press Ctrl+C to stop)...")
    print("-" * 60)

    event_count = 0
    start_time = time.time()

    try:
        while True:
            message = pubsub.get_message(timeout=1.0)

            if message and message['type'] == 'message':
                event_count += 1
                channel = message['channel']

                try:
                    data = json.loads(message['data'])
                    pattern_data = data.get('data', {})

                    print(f"\n[EVENT #{event_count}] Channel: {channel}")
                    print(f"  Symbol: {pattern_data.get('symbol', 'N/A')}")
                    print(f"  Pattern: {pattern_data.get('pattern', pattern_data.get('pattern_type', 'N/A'))}")
                    print(f"  Confidence: {pattern_data.get('confidence', 'N/A')}")
                    print(f"  Source: {data.get('source', 'N/A')}")
                    print(f"  Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
                except:
                    print(f"\n[EVENT #{event_count}] Raw message from {channel}")
                    print(f"  Data: {message['data'][:100]}...")

            # Print status every 10 seconds
            if int(time.time() - start_time) % 10 == 0:
                elapsed = int(time.time() - start_time)
                if elapsed > 0:
                    print(f"  ... monitoring ({elapsed}s elapsed, {event_count} events received)")

    except KeyboardInterrupt:
        print(f"\n\nMonitoring stopped.")
        print(f"Total events received: {event_count}")
        print(f"Duration: {int(time.time() - start_time)} seconds")

if __name__ == "__main__":
    monitor_patterns()