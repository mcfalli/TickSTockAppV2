#!/usr/bin/env python3
"""
Fix syntax error in redis_event_subscriber.py caused by incorrect indentation.
"""

def fix_indentation():
    """Fix the indentation error in redis_event_subscriber.py"""
    file_path = "C:/Users/McDude/TickStockAppV2/src/core/services/redis_event_subscriber.py"

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Find and fix the incorrectly indented line
    for i, line in enumerate(lines):
        if "log_websocket_delivery(pattern_name, symbol, len(interested_users))" in line:
            # Check if it's the incorrectly indented one (starts with too few spaces)
            if line.startswith("            log_websocket_delivery"):
                # Fix the indentation - should be 24 spaces (6 levels of 4 spaces)
                lines[i] = "                        log_websocket_delivery(pattern_name, symbol, len(interested_users))\n"
                print(f"[OK] Fixed indentation at line {i+1}")

    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)

    print("[SUCCESS] Fixed syntax error in redis_event_subscriber.py")
    return True

def main():
    """Run the fix."""
    print("=" * 60)
    print("Fixing Integration Logging Syntax Error")
    print("=" * 60)

    if fix_indentation():
        print("\nSyntax error fixed! The application should now start correctly.")
        print("Integration logging is now properly configured.")
    else:
        print("\n[ERROR] Failed to fix syntax error")

if __name__ == "__main__":
    main()