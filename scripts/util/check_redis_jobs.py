"""Check what's in Redis related to jobs"""
import redis
import json

r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

print("=" * 70)
print("CHECKING REDIS JOB-RELATED DATA")
print("=" * 70)

# Check job status keys
print("\n1. JOB STATUS KEYS:")
print("-" * 70)
status_keys = r.keys('tickstock.jobs.status:*')
print(f"Found {len(status_keys)} job status keys:")
for key in status_keys:
    key_type = r.type(key)
    print(f"\n  {key}")
    print(f"    Type: {key_type}")

    if key_type == 'string':
        data = r.get(key)
        if data:
            try:
                parsed = json.loads(data)
                print(f"    Data: {parsed}")
            except:
                print(f"    Data: {data}")
    elif key_type == 'hash':
        data = r.hgetall(key)
        print(f"    Data: {data}")

# Check if there are any queued messages (list type)
print("\n\n2. CHECKING FOR QUEUED MESSAGES:")
print("-" * 70)
queue_patterns = ['tickstock.jobs.*', 'tickstock:jobs:*', 'job:*']
for pattern in queue_patterns:
    keys = r.keys(pattern)
    if keys:
        print(f"\nPattern '{pattern}': {len(keys)} keys")
        for key in keys:
            key_type = r.type(key)
            print(f"  {key} ({key_type})")

            if key_type == 'list':
                length = r.llen(key)
                print(f"    Length: {length}")
                if length > 0:
                    items = r.lrange(key, 0, min(length-1, 5))
                    print(f"    First {min(length, 5)} items:")
                    for item in items:
                        try:
                            parsed = json.loads(item)
                            print(f"      {parsed}")
                        except:
                            print(f"      {item}")

# Check all keys to see if there's anything unexpected
print("\n\n3. ALL KEYS MATCHING 'tickstock*' or 'job*':")
print("-" * 70)
all_patterns = ['tickstock*', 'job*']
for pattern in all_patterns:
    keys = r.keys(pattern)
    if keys:
        print(f"\nPattern '{pattern}': {len(keys)} keys")
        for key in keys:
            print(f"  {key} ({r.type(key)})")

print("\n" + "=" * 70)
print("DONE")
print("=" * 70)
