"""Clean up job status keys with wrong type (STRING instead of HASH)"""
import redis

# Connect to Redis
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# Find all job status keys
pattern = "tickstock.jobs.status:*"
all_keys = r.keys(pattern)

print(f"Found {len(all_keys)} job status keys")
print("=" * 60)

string_keys = []
hash_keys = []
other_keys = []

for key in all_keys:
    key_type = r.type(key)

    if key_type == 'string':
        string_keys.append(key)
        print(f"STRING (WRONG): {key}")
    elif key_type == 'hash':
        hash_keys.append(key)
        print(f"HASH (OK):     {key}")
    else:
        other_keys.append(key)
        print(f"{key_type.upper()}: {key}")

print("=" * 60)
print(f"\nSummary:")
print(f"  HASH keys (correct format):  {len(hash_keys)}")
print(f"  STRING keys (wrong format):  {len(string_keys)}")
print(f"  Other types:                 {len(other_keys)}")

if string_keys:
    print(f"\nDeleting {len(string_keys)} STRING keys (wrong format)...")
    for key in string_keys:
        print(f"  Deleting: {key}")
        r.delete(key)
    print("Done!")
else:
    print("\nNo wrong-type keys to delete.")

if other_keys:
    print(f"\nWarning: {len(other_keys)} keys have unexpected types:")
    for key in other_keys:
        print(f"  {key}: {r.type(key)}")
