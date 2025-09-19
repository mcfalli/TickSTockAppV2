#!/usr/bin/env python3
"""Fix the syntax error in websocket_broadcaster.py"""

def fix_syntax_error():
    file_path = "C:/Users/McDude/TickStockAppV2/src/core/services/websocket_broadcaster.py"

    with open(file_path, 'r') as f:
        lines = f.readlines()

    # Fix the duplicate and malformed if statement around line 205
    new_lines = []
    skip_next = 0

    for i, line in enumerate(lines):
        if skip_next > 0:
            skip_next -= 1
            continue

        # Check for the problematic lines
        if i == 204 and "if not pattern_name:" in line:
            # This is line 205 (0-indexed), fix the indentation issue
            new_lines.append(line)  # Keep the if statement
            # Skip the duplicate lines
            if i + 1 < len(lines) and "# Set default" in lines[i + 1]:
                new_lines.append("                # Set default pattern name if missing\n")
                if i + 2 < len(lines) and "if not pattern_name:" in lines[i + 2]:
                    # Skip the duplicate if statement
                    skip_next = 2
                    # Add the correct indented block
                    new_lines.append("                pattern_name = pattern_event.get('data', {}).get('pattern_type', 'UNKNOWN')\n")
                    new_lines.append("                logger.warning('WEBSOCKET-BROADCASTER: Pattern event missing pattern name')\n")
                    new_lines.append("                if pattern_name == 'UNKNOWN':\n")
                    new_lines.append("                    return\n")
                    skip_next = 4  # Skip the old duplicate lines
        else:
            new_lines.append(line)

    with open(file_path, 'w') as f:
        f.writelines(new_lines)

    print("[OK] Fixed syntax error in websocket_broadcaster.py")

if __name__ == "__main__":
    fix_syntax_error()