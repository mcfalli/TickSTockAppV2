"""Kill all jobs and clear all job-related Redis data"""
import redis
import json

r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

print("=" * 70)
print("KILLING ALL JOBS AND CLEARING REDIS")
print("=" * 70)

# 1. Delete all job status keys
print("\n1. Deleting all job status keys...")
status_keys = r.keys('tickstock.jobs.status:*')
print(f"   Found {len(status_keys)} job status keys")
if status_keys:
    deleted = r.delete(*status_keys)
    print(f"   Deleted {deleted} keys")
else:
    print("   No job status keys to delete")

# 2. Check for any job queues (list type)
print("\n2. Checking for job queues...")
queue_patterns = ['tickstock.jobs.queue*', 'tickstock:jobs:queue*', 'job:queue*']
for pattern in queue_patterns:
    keys = r.keys(pattern)
    if keys:
        print(f"   Pattern '{pattern}': {len(keys)} keys")
        for key in keys:
            key_type = r.type(key)
            if key_type == 'list':
                length = r.llen(key)
                print(f"     {key}: {length} items")
                if length > 0:
                    r.delete(key)
                    print(f"     Deleted queue: {key}")
            else:
                r.delete(key)
                print(f"     Deleted {key_type}: {key}")

# 3. Clear active jobs zset if it exists
print("\n3. Clearing active jobs tracking...")
if r.exists('tickstock:active_jobs'):
    count = r.zcard('tickstock:active_jobs')
    print(f"   Found {count} active jobs in zset")
    r.delete('tickstock:active_jobs')
    print("   Cleared active jobs zset")
else:
    print("   No active jobs zset")

# 4. Publish job cancellation for any running jobs
print("\n4. Publishing cancellation message...")
cancel_all = {
    'command': 'cancel_all',
    'reason': 'Manual cleanup - kill all jobs',
    'timestamp': '2025-11-29T21:30:00'
}
try:
    r.publish('tickstock.jobs.control', json.dumps(cancel_all))
    print("   Published cancel_all message to tickstock.jobs.control")
except Exception as e:
    print(f"   Could not publish cancellation: {e}")

# 5. Final verification
print("\n5. Final verification...")
remaining = r.keys('tickstock.jobs.status:*')
print(f"   Remaining job status keys: {len(remaining)}")
if remaining:
    print("   WARNING: Some keys remain:")
    for key in remaining:
        print(f"     - {key}")

print("\n" + "=" * 70)
print("CLEANUP COMPLETE")
print("=" * 70)
print("\nNext steps:")
print("1. Restart TickStockPL to pick up cancellation")
print("2. Restart Flask to apply JavaScript fixes")
print("3. Test with fresh job submission")
