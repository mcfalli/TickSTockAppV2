"""Clear corrupted Redis job status keys"""
import redis

# Connect to Redis
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# Find all job status keys
pattern = "tickstock.jobs.status:universe_load_*"
keys = r.keys(pattern)

print(f"Found {len(keys)} job status keys")

if keys:
    deleted = r.delete(*keys)
    print(f"Deleted {deleted} keys")
else:
    print("No keys to delete")

print("\nDone!")
