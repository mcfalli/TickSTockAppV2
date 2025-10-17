#!/usr/bin/env python3
"""Quick script to inspect a single indicator event from Redis"""

import json
import redis
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

r = redis.Redis(host='127.0.0.1', port=6379, db=0, decode_responses=True)
pubsub = r.pubsub()
pubsub.subscribe('tickstock:indicators:streaming')

print("Waiting for first indicator event...\n")

for message in pubsub.listen():
    if message['type'] == 'message':
        data = json.loads(message['data'])
        print("Full indicator event structure:")
        print(json.dumps(data, indent=2))
        break

pubsub.close()
