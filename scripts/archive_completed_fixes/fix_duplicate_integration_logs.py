#!/usr/bin/env python3
"""
Fix duplicate integration log files issue.
Removes the hardcoded file handler that creates integration_flow.log
"""

def fix_duplicate_logs():
    """Remove hardcoded file handler from integration_logger.py."""

    file_path = "C:/Users/McDude/TickStockAppV2/src/core/services/integration_logger.py"

    # Read the file
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Find and remove the hardcoded file handler lines
    new_lines = []
    skip_next = 0

    for i, line in enumerate(lines):
        if skip_next > 0:
            skip_next -= 1
            continue

        # Check if this is the hardcoded file handler section
        if "# Optionally write to separate file" in line:
            # Replace the next 4 lines with a comment
            new_lines.append("# File handler will be added dynamically by configure_integration_logging()\n")
            new_lines.append("# when INTEGRATION_LOG_FILE=true in .env\n")
            new_lines.append("# This prevents duplicate log files (integration_flow.log and integration_[timestamp].log)\n")
            skip_next = 3  # Skip the next 3 lines
        else:
            new_lines.append(line)

    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

    print("[SUCCESS] Fixed duplicate integration log files issue")
    print("Now only timestamped integration logs will be created when INTEGRATION_LOG_FILE=true")

    return True


def main():
    """Run the fix."""
    print("=" * 60)
    print("Fixing Duplicate Integration Log Files")
    print("=" * 60)

    if fix_duplicate_logs():
        print("\nDuplicate log file issue resolved!")
        print("The system will now create only timestamped integration logs.")


if __name__ == "__main__":
    main()