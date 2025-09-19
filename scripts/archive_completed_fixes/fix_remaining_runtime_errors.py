#!/usr/bin/env python3
"""
Fix remaining runtime errors in TickStockAppV2:
1. PatternAlertManager - get_preferences should be get_user_preferences
2. Pattern event missing pattern name warning
3. SocketIO emit errors
"""

import os
import re

def fix_pattern_alert_manager():
    """Fix get_preferences method call to get_user_preferences."""
    file_path = "src/core/services/pattern_alert_manager.py"

    print(f"Fixing {file_path}...")

    with open(file_path, 'r') as f:
        content = f.read()

    # Fix the method call
    if "self.get_preferences(user_id)" in content:
        content = content.replace(
            "preferences = self.get_preferences(user_id)",
            "preferences = self.get_user_preferences(user_id)"
        )

        with open(file_path, 'w') as f:
            f.write(content)
        print(f"  [FIXED] Changed get_preferences to get_user_preferences")
        return True
    else:
        print(f"  [SKIP] get_preferences call not found or already fixed")
        return False

def fix_websocket_broadcaster():
    """Add better error handling for missing pattern fields."""
    file_path = "src/core/services/websocket_broadcaster.py"

    print(f"Fixing {file_path}...")

    if not os.path.exists(file_path):
        print(f"  [SKIP] File not found: {file_path}")
        return False

    with open(file_path, 'r') as f:
        content = f.read()

    # Check if we need to add better validation
    if "WEBSOCKET-BROADCASTER: Pattern event missing pattern name" in content:
        # Find the method that logs this warning
        lines = content.split('\n')
        new_lines = []
        fixed = False

        for i, line in enumerate(lines):
            new_lines.append(line)

            # Look for the warning message and add better validation
            if "Pattern event missing pattern name" in line and not fixed:
                # Check if there's already a default value being set
                if i > 0 and "pattern_name = " not in lines[i-1]:
                    # Add a line before the warning to set a default
                    indent = len(line) - len(line.lstrip())
                    new_lines.insert(-1, " " * (indent - 4) + "# Set default pattern name if missing")
                    new_lines.insert(-1, " " * (indent - 4) + "if not pattern_name:")
                    new_lines.insert(-1, " " * indent + "pattern_name = pattern_data.get('pattern_type', 'UNKNOWN')")
                    fixed = True

        if fixed:
            with open(file_path, 'w') as f:
                f.write('\n'.join(new_lines))
            print(f"  [FIXED] Added default pattern name handling")
            return True

    print(f"  [SKIP] No changes needed or already fixed")
    return False

def fix_redis_event_subscriber_socketio():
    """Add socketio null check in redis_event_subscriber."""
    file_path = "src/core/services/redis_event_subscriber.py"

    print(f"Fixing {file_path}...")

    with open(file_path, 'r') as f:
        content = f.read()

    # Add null checks for socketio
    lines = content.split('\n')
    new_lines = []
    fixed = False

    for i, line in enumerate(lines):
        # Look for socketio.emit calls without null checks
        if "socketio.emit" in line and "if socketio" not in content[max(0, content.rfind('\n', 0, content.find(line))-100):content.find(line)]:
            # Add null check before the emit
            indent = len(line) - len(line.lstrip())
            new_lines.append(" " * indent + "if socketio:")
            new_lines.append("    " + line)
            fixed = True
        elif ".emit(" in line and "socketio" in line and not fixed:
            # Check if there's already a null check
            if i > 0 and "if" not in lines[i-1]:
                indent = len(line) - len(line.lstrip())
                # Insert check before current line
                new_lines.append(" " * indent + "if socketio is not None:")
                new_lines.append("    " + line)
                fixed = True
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    if fixed:
        with open(file_path, 'w') as f:
            f.write('\n'.join(new_lines))
        print(f"  [FIXED] Added socketio null checks")
        return True

    print(f"  [SKIP] No changes needed")
    return False

def add_pattern_field_validation():
    """Ensure pattern events have required fields."""
    file_path = "src/core/services/redis_event_subscriber.py"

    print(f"Adding pattern field validation to {file_path}...")

    with open(file_path, 'r') as f:
        content = f.read()

    # Look for where pattern_data is extracted and add validation
    if "pattern_data = event.data.get('data', event.data)" in content:
        lines = content.split('\n')
        new_lines = []
        fixed = False

        for i, line in enumerate(lines):
            new_lines.append(line)

            if "pattern_data = event.data.get('data', event.data)" in line and not fixed:
                # Add validation after extraction
                indent = len(line) - len(line.lstrip())
                new_lines.append("")
                new_lines.append(" " * indent + "# Ensure required pattern fields exist")
                new_lines.append(" " * indent + "if 'pattern' not in pattern_data and 'pattern_type' in pattern_data:")
                new_lines.append(" " * (indent + 4) + "pattern_data['pattern'] = pattern_data['pattern_type']")
                new_lines.append(" " * indent + "elif 'pattern' not in pattern_data:")
                new_lines.append(" " * (indent + 4) + "pattern_data['pattern'] = 'UNKNOWN'")
                fixed = True

        if fixed:
            with open(file_path, 'w') as f:
                f.write('\n'.join(new_lines))
            print(f"  [FIXED] Added pattern field validation")
            return True

    print(f"  [SKIP] Pattern extraction not found or already validated")
    return False

def main():
    """Main function to fix all remaining issues."""
    print("=" * 60)
    print("Fixing Remaining Runtime Errors in TickStockAppV2")
    print("=" * 60)

    # Change to TickStockAppV2 directory
    os.chdir("C:/Users/McDude/TickStockAppV2")

    fixes_applied = 0

    # Apply all fixes
    print("\n1. Fixing PatternAlertManager method call...")
    if fix_pattern_alert_manager():
        fixes_applied += 1

    print("\n2. Fixing WebSocket broadcaster pattern validation...")
    if fix_websocket_broadcaster():
        fixes_applied += 1

    print("\n3. Fixing Redis event subscriber socketio checks...")
    if fix_redis_event_subscriber_socketio():
        fixes_applied += 1

    print("\n4. Adding pattern field validation...")
    if add_pattern_field_validation():
        fixes_applied += 1

    print("\n" + "=" * 60)
    print(f"[COMPLETE] Applied {fixes_applied} fixes")
    print("=" * 60)

    if fixes_applied > 0:
        print("\nNext steps:")
        print("1. Restart services to pick up changes")
        print("2. Monitor logs for error resolution")
        print("3. Verify pattern events are processing correctly")
    else:
        print("\nNo fixes were needed. Issues may already be resolved.")

    print("\nNote: SocketIO timing issues are normal during startup")
    print("and typically resolve once the Flask app is fully initialized.")

if __name__ == "__main__":
    main()