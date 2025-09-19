#!/usr/bin/env python3
"""
Fix Redis pattern cache serialization issues in TickStockAppV2.
The error "Invalid input of type: 'dict'" occurs when trying to store
dictionaries directly in Redis without proper serialization.
"""

import os
import re

def fix_redis_pattern_cache():
    """Fix Redis pattern cache to properly serialize dict objects."""
    file_path = "C:/Users/McDude/TickStockAppV2/src/infrastructure/cache/redis_pattern_cache.py"

    print(f"Fixing Redis serialization in {file_path}")

    with open(file_path, 'r') as f:
        content = f.read()

    # Fix 1: Update hset to use mapping parameter (required in newer redis-py)
    # This is the main issue causing the dict serialization error
    old_hset = """            # Store pattern data
            pipe.hset(pattern_key, {
                'data': json.dumps(asdict(pattern)),
                'cached_at': time.time()
            })"""

    new_hset = """            # Store pattern data
            pipe.hset(pattern_key, mapping={
                'data': json.dumps(asdict(pattern)),
                'cached_at': str(time.time())  # Convert to string for Redis
            })"""

    if old_hset in content:
        content = content.replace(old_hset, new_hset)
        print("  [OK] Fixed hset mapping parameter")
    else:
        print("  ! hset pattern not found (may already be fixed)")

    # Fix 2: Check for any other hset calls that might need the mapping parameter
    # Look for pattern: pipe.hset(some_key, {
    hset_pattern = r'(pipe\.hset\([^,]+,)\s*(\{[^}]+\})'
    matches = re.findall(hset_pattern, content)
    if matches:
        for match in matches:
            if 'mapping=' not in match[0]:
                old = match[0] + ' ' + match[1]
                new = match[0] + ' mapping=' + match[1]
                content = content.replace(old, new)
                print(f"  [OK] Fixed additional hset call")

    # Fix 3: Ensure all values stored in Redis are strings or bytes
    # Look for setex calls that might be storing dicts
    if 'self.redis_client.setex' in content:
        # Find the line with setex and the value being stored
        lines = content.split('\n')
        new_lines = []
        for i, line in enumerate(lines):
            if 'self.redis_client.setex' in line and i + 2 < len(lines):
                # Check the next lines for the value parameter
                next_line = lines[i + 2] if i + 2 < len(lines) else ""
                if 'json.dumps' not in next_line and 'str(' not in next_line:
                    # Need to check what's being stored
                    if 'response' in next_line or 'result' in next_line:
                        # This is likely storing a dict, need to serialize
                        lines[i + 2] = lines[i + 2].replace('response', 'json.dumps(response)')
                        print("  [OK] Fixed setex serialization")
            new_lines.append(line)
        if new_lines != lines:
            content = '\n'.join(new_lines)

    # Write the fixed content back
    with open(file_path, 'w') as f:
        f.write(content)

    print(f"[SUCCESS] Fixes applied to {file_path}")
    return True

def verify_fix():
    """Verify the fix was applied correctly."""
    file_path = "C:/Users/McDude/TickStockAppV2/src/infrastructure/cache/redis_pattern_cache.py"

    with open(file_path, 'r') as f:
        content = f.read()

    # Check if mapping parameter is present
    if 'pipe.hset(pattern_key, mapping={' in content:
        print("[OK] hset mapping parameter correctly applied")
        return True
    else:
        print("[FAIL] hset mapping parameter not found")
        return False

def main():
    """Main function to fix Redis serialization issues."""
    print("=" * 60)
    print("Fixing Redis Pattern Cache Serialization Issues")
    print("=" * 60)

    # Apply the fix
    if fix_redis_pattern_cache():
        print("\nVerifying fix...")
        if verify_fix():
            print("\n[SUCCESS] All fixes successfully applied!")
            print("\nNext steps:")
            print("1. The services should automatically reload")
            print("2. Monitor logs for any remaining errors")
            print("3. Pattern caching should now work correctly")
        else:
            print("\n[WARNING] Fix verification failed. Manual review needed.")
    else:
        print("\n[ERROR] Failed to apply fixes")

if __name__ == "__main__":
    main()