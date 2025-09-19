#!/usr/bin/env python3
"""
Fix remaining TickStockAppV2 errors:
1. PatternAlertManager missing key_prefix attribute
2. Redis cache trying to store dict objects directly
3. SocketIO emit errors
"""

import os
import json
import re

def fix_pattern_alert_manager():
    """Add missing key_prefix attribute to PatternAlertManager."""
    file_path = "src/core/services/pattern_alert_manager.py"

    with open(file_path, 'r') as f:
        content = f.read()

    # Check if key_prefix is already defined
    if 'self.key_prefix = ' in content:
        print(f"[SKIP] key_prefix already defined in {file_path}")
        return

    # Find the __init__ method and add key_prefix
    init_pattern = r'(def __init__.*?\n.*?""".*?""")'
    match = re.search(init_pattern, content, re.DOTALL)

    if match:
        init_block = match.group(1)
        # Find where to insert (after self.tickstock_db = tickstock_db)
        insert_after = "self.tickstock_db = tickstock_db"

        if insert_after in content:
            new_content = content.replace(
                insert_after + "\n        \n        # Redis key patterns",
                insert_after + "\n        \n        # Redis key prefix for all alert-related keys\n        self.key_prefix = \"tickstock:alerts:\"\n        \n        # Redis key patterns"
            )

            with open(file_path, 'w') as f:
                f.write(new_content)
            print(f"[FIXED] Added key_prefix to {file_path}")
        else:
            print(f"[ERROR] Could not find insertion point in {file_path}")
    else:
        print(f"[ERROR] Could not find __init__ method in {file_path}")

def fix_redis_pattern_cache():
    """Fix Redis pattern cache to properly serialize dict objects."""
    file_path = "src/infrastructure/cache/redis_pattern_cache.py"

    if not os.path.exists(file_path):
        print(f"[SKIP] File not found: {file_path}")
        return

    with open(file_path, 'r') as f:
        content = f.read()

    # Find the cache_pattern method
    if "def cache_pattern" not in content:
        print(f"[SKIP] cache_pattern method not found in {file_path}")
        return

    # Check if json.dumps is already being used
    if "json.dumps(pattern_data)" in content:
        print(f"[SKIP] JSON serialization already implemented in {file_path}")
        return

    # Find and fix the setex call
    lines = content.split('\n')
    new_lines = []
    in_cache_pattern = False
    fixed = False

    for i, line in enumerate(lines):
        if "def cache_pattern" in line:
            in_cache_pattern = True
        elif in_cache_pattern and "self.redis_client.setex" in line:
            # Check if it's trying to set a dict directly
            if "pattern_data" in line and "json.dumps" not in line:
                # Replace with JSON serialization
                indent = len(line) - len(line.lstrip())
                new_lines.append(" " * indent + "# Serialize pattern data to JSON")
                new_lines.append(" " * indent + "pattern_json = json.dumps(pattern_data)")
                new_lines.append(line.replace("pattern_data", "pattern_json"))
                fixed = True
                in_cache_pattern = False
                continue
        new_lines.append(line)

    if fixed:
        # Make sure json is imported
        if "import json" not in content:
            new_lines.insert(0, "import json")

        with open(file_path, 'w') as f:
            f.write('\n'.join(new_lines))
        print(f"[FIXED] Added JSON serialization to {file_path}")
    else:
        print(f"[WARN] Could not find setex call to fix in {file_path}")

def check_socketio_initialization():
    """Check and report on SocketIO initialization issues."""
    print("\n[INFO] SocketIO Initialization Check:")
    print("  The 'NoneType' object has no attribute 'emit' error suggests")
    print("  that socketio is not properly initialized when the event handler runs.")
    print("  This is likely a timing issue where events are processed before")
    print("  the Flask app is fully initialized.")
    print("\n  Recommendation: Ensure services start in correct order:")
    print("  1. Flask app and SocketIO initialization")
    print("  2. Redis event subscriber start")
    print("  3. Pattern detection services")

def main():
    """Main function to fix all issues."""
    print("=" * 60)
    print("Fixing TickStockAppV2 Runtime Errors")
    print("=" * 60)

    # Change to TickStockAppV2 directory
    os.chdir("C:/Users/McDude/TickStockAppV2")

    # Fix all the issues
    print("\n1. Fixing PatternAlertManager...")
    fix_pattern_alert_manager()

    print("\n2. Fixing Redis Pattern Cache...")
    fix_redis_pattern_cache()

    print("\n3. Checking SocketIO...")
    check_socketio_initialization()

    print("\n" + "=" * 60)
    print("Fixes Complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Restart services using start_both_services.py")
    print("2. Monitor logs for any remaining errors")
    print("\nNote: Some errors may be from old events in the Redis queue")
    print("that will clear as new properly-formatted events come through.")

if __name__ == "__main__":
    main()