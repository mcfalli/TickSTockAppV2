"""Fix corrupted Redis job status key"""
import redis

# Connect to Redis
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# Delete ALL universe_load job keys to start fresh
pattern = "tickstock.jobs.status:universe_load_*"
all_keys = r.keys(pattern)
print(f"Found {len(all_keys)} job status keys")

if all_keys:
    for k in all_keys:
        print(f"Deleting: {k}")
    deleted = r.delete(*all_keys)
    print(f"Deleted {deleted} keys")
else:
    print("No keys to delete")

print("Done!")
