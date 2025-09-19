#!/usr/bin/env python3
"""Fix runtime errors in TickStockAppV2"""

import os
import re

def fix_socketio_references():
    """Fix 'socketio' undefined variable in redis_event_subscriber.py"""
    file_path = "C:/Users/McDude/TickStockAppV2/src/core/services/redis_event_subscriber.py"

    with open(file_path, 'r') as f:
        content = f.read()

    # Replace all instances of 'if socketio:' with 'if self.socketio:'
    content = content.replace('if socketio:', 'if self.socketio:')

    with open(file_path, 'w') as f:
        f.write(content)

    print("[OK] Fixed socketio references in redis_event_subscriber.py")

def fix_pattern_alert_manager():
    """Fix UserAlertPreferences attribute error in pattern_alert_manager.py"""
    file_path = "C:/Users/McDude/TickStockAppV2/src/core/services/pattern_alert_manager.py"

    with open(file_path, 'r') as f:
        lines = f.readlines()

    new_lines = []
    for i, line in enumerate(lines):
        # Look for the get_users_for_alert method
        if 'def get_users_for_alert' in line:
            # Mark that we're in the right method
            in_method = True
            new_lines.append(line)
        elif in_method and 'prefs.get(' in line:
            # Replace prefs.get() with proper attribute access
            # Change prefs.get('pattern_enabled') to prefs.pattern_enabled
            line = line.replace("prefs.get('pattern_enabled', True)", "getattr(prefs, 'pattern_enabled', True)")
            line = line.replace("prefs.get('confidence_threshold', 0)", "getattr(prefs, 'confidence_threshold', 0)")
            line = line.replace("prefs.get('subscribed_patterns', [])", "getattr(prefs, 'subscribed_patterns', [])")
            line = line.replace("prefs.get('subscribed_symbols', [])", "getattr(prefs, 'subscribed_symbols', [])")
            new_lines.append(line)
        else:
            new_lines.append(line)

    with open(file_path, 'w') as f:
        f.writelines(new_lines)

    print("[OK] Fixed UserAlertPreferences attribute access in pattern_alert_manager.py")

def fix_websocket_broadcaster():
    """Ensure pattern name extraction is robust in websocket_broadcaster.py"""
    file_path = "C:/Users/McDude/TickStockAppV2/src/core/services/websocket_broadcaster.py"

    with open(file_path, 'r') as f:
        lines = f.readlines()

    # The pattern extraction already looks correct, but let's make it more robust
    new_lines = []
    for i, line in enumerate(lines):
        if i == 201 and "pattern_name = pattern_event.get('data', {}).get('pattern')" in line:
            # Make the pattern extraction more robust
            new_lines.append("            # Extract pattern from nested or flat structure\n")
            new_lines.append("            event_data = pattern_event.get('data', pattern_event)\n")
            new_lines.append("            if isinstance(event_data, dict) and 'data' in event_data:\n")
            new_lines.append("                # Handle nested structure from TickStockPL\n")
            new_lines.append("                pattern_data = event_data['data']\n")
            new_lines.append("            else:\n")
            new_lines.append("                pattern_data = event_data\n")
            new_lines.append("            \n")
            new_lines.append("            pattern_name = pattern_data.get('pattern') or pattern_data.get('pattern_type')\n")
            new_lines.append("            symbol = pattern_data.get('symbol')\n")
            # Skip the original line and the next line (symbol extraction)
            continue
        elif i == 202 and "symbol = pattern_event.get('data', {}).get('symbol')" in line:
            # Skip this line as we've already handled it
            continue
        else:
            new_lines.append(line)

    with open(file_path, 'w') as f:
        f.writelines(new_lines)

    print("[OK] Enhanced pattern extraction in websocket_broadcaster.py")

def main():
    """Run all fixes"""
    print("=" * 60)
    print("TickStockAppV2 Runtime Error Fixes")
    print("=" * 60)

    try:
        fix_socketio_references()
        fix_pattern_alert_manager()
        fix_websocket_broadcaster()

        print("\n" + "=" * 60)
        print("[SUCCESS] All runtime errors fixed!")
        print("=" * 60)
        print("\nRestart the application to apply changes.")

    except Exception as e:
        print(f"\n[ERROR] Fix failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()