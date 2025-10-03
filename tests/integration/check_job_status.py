#!/usr/bin/env python3
import redis
import json
from datetime import datetime

r = redis.Redis(host='127.0.0.1', port=6379, decode_responses=True)
status_data = r.get('tickstock.jobs.status:7359250e-85d2-484f-942a-c0d0ebfd5056')

if status_data:
    data = json.loads(status_data)
    print(json.dumps(data, indent=2))

    if data.get('started_at'):
        start = datetime.fromisoformat(data['started_at'])
        elapsed = (datetime.now() - start).total_seconds()
        print(f"\nElapsed: {int(elapsed)} seconds ({int(elapsed/60)} minutes)")

    print(f"Progress: {data.get('processed_symbols', 0)}/{data.get('total_symbols', 0)}")
    print(f"Current: {data.get('current_symbol', 'N/A')}")
    print(f"Status: {data.get('status', 'unknown')}")
else:
    print("No status found")
