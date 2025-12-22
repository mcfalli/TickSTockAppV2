"""Monitor Redis pub-sub channel for job messages"""
import redis
import json
from datetime import datetime

r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
pubsub = r.pubsub()

channel = 'tickstock.jobs.data_load'
pubsub.subscribe(channel)

print("=" * 70)
print(f"MONITORING CHANNEL: {channel}")
print("=" * 70)
print("Waiting for messages... (Press Ctrl+C to stop)")
print()

try:
    for message in pubsub.listen():
        if message['type'] == 'message':
            timestamp = datetime.now().strftime('%H:%M:%S')
            print(f"\n[{timestamp}] MESSAGE RECEIVED:")
            print("-" * 70)

            try:
                data = json.loads(message['data'])
                print(f"Job ID: {data.get('job_id', 'N/A')}")
                print(f"Job Type: {data.get('job_type', 'N/A')}")
                print(f"Source: {data.get('source', data.get('universe_key', 'N/A'))}")
                print(f"Symbols Count: {len(data.get('symbols', []))}")
                print(f"Symbols: {data.get('symbols', [])}")
                print(f"Years: {data.get('years', 'N/A')}")
                print(f"Full Message:")
                print(json.dumps(data, indent=2))
            except Exception as e:
                print(f"Raw data: {message['data']}")
                print(f"Error parsing: {e}")

            print("-" * 70)

except KeyboardInterrupt:
    print("\n\nStopped monitoring.")
    pubsub.unsubscribe()
