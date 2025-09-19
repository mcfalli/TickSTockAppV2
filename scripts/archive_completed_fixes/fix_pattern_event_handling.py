#!/usr/bin/env python3
"""
Fix pattern event handling in TickStockAppV2 to correctly process nested event structure.

The pattern events from TickStockPL have the structure:
{
    "event_type": "pattern_detected",
    "source": "TickStockPL",
    "timestamp": 1234567890.123,
    "data": {
        "symbol": "AAPL",
        "pattern": "Bull_Flag",
        "confidence": 0.85,
        ...
    }
}

The handlers need to extract pattern data from event.data.data, not event.data
"""

import os
import sys

def fix_redis_event_subscriber():
    """Fix the pattern event handler in redis_event_subscriber.py"""
    file_path = "src/core/services/redis_event_subscriber.py"

    with open(file_path, 'r') as f:
        content = f.read()

    # Fix the pattern event handler
    old_code = """    def _handle_pattern_event(self, event: TickStockEvent):
        \"\"\"Handle pattern detection events with user filtering.\"\"\"
        pattern_data = event.data
        pattern_name = pattern_data.get('pattern')
        symbol = pattern_data.get('symbol')
        confidence = pattern_data.get('confidence', 0)"""

    new_code = """    def _handle_pattern_event(self, event: TickStockEvent):
        \"\"\"Handle pattern detection events with user filtering.\"\"\"
        # Extract nested pattern data from the event structure
        # Pattern events have data nested inside: event.data.data
        pattern_data = event.data.get('data', event.data)
        pattern_name = pattern_data.get('pattern')
        symbol = pattern_data.get('symbol')
        confidence = pattern_data.get('confidence', 0)"""

    if old_code in content:
        content = content.replace(old_code, new_code)
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"✅ Fixed pattern event handler in {file_path}")
    else:
        print(f"⚠️  Pattern event handler already fixed or different in {file_path}")

def fix_websocket_broadcaster():
    """Fix the pattern event handler in websocket_broadcaster.py"""
    file_path = "src/core/services/websocket_broadcaster.py"

    if not os.path.exists(file_path):
        print(f"⚠️  File not found: {file_path}")
        return

    with open(file_path, 'r') as f:
        content = f.read()

    # Check if it needs the same fix
    if "event.data.get('data'," not in content and "def broadcast_pattern_event" in content:
        lines = content.split('\n')
        new_lines = []
        in_broadcast_function = False

        for line in lines:
            if "def broadcast_pattern_event" in line:
                in_broadcast_function = True
            elif in_broadcast_function and "pattern_data = event.data" in line:
                new_lines.append("        # Extract nested pattern data from the event structure")
                new_lines.append("        pattern_data = event.data.get('data', event.data)")
                in_broadcast_function = False
                continue
            new_lines.append(line)

        content = '\n'.join(new_lines)
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"✅ Fixed pattern event handler in {file_path}")
    else:
        print(f"⚠️  Pattern event handler already fixed or different in {file_path}")

def fix_pattern_discovery_service():
    """Fix the pattern event handler in pattern_discovery_service.py"""
    file_path = "src/core/services/pattern_discovery_service.py"

    with open(file_path, 'r') as f:
        content = f.read()

    # This file already has the fix from the agent, just verify
    if "event.data.get('data', event.data)" in content:
        print(f"✅ Pattern event handler already fixed in {file_path}")
    else:
        # Apply the fix
        lines = content.split('\n')
        new_lines = []

        for i, line in enumerate(lines):
            new_lines.append(line)
            # Look for where pattern_data is extracted
            if "def _handle_pattern_event" in line:
                # Find the pattern_data assignment in the next few lines
                for j in range(i+1, min(i+10, len(lines))):
                    if "pattern_data = event" in lines[j]:
                        # Replace with the fixed version
                        indent = len(lines[j]) - len(lines[j].lstrip())
                        new_lines[j] = " " * indent + "# Extract nested pattern data"
                        new_lines.append(" " * indent + "pattern_data = event.data.get('data', event.data)")
                        break

        content = '\n'.join(new_lines)
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"✅ Fixed pattern event handler in {file_path}")

def main():
    """Main function to fix all pattern event handlers"""
    print("=" * 60)
    print("Fixing Pattern Event Handling in TickStockAppV2")
    print("=" * 60)

    # Change to TickStockAppV2 directory
    os.chdir("C:/Users/McDude/TickStockAppV2")

    # Fix all the files
    fix_redis_event_subscriber()
    fix_websocket_broadcaster()
    fix_pattern_discovery_service()

    print("\n" + "=" * 60)
    print("Pattern Event Handling Fixes Complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Restart the services using start_both_services.py")
    print("2. Pattern events should now be processed correctly")
    print("\nFor TickStockPL fixes, provide these to the TickStockPL developer:")
    print("- Fix Decimal/float conversion in run_pattern_detection_service.py")
    print("- Use pd.to_numeric() for database numeric columns")

if __name__ == "__main__":
    main()