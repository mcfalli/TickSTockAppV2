#!/usr/bin/env python3
"""
Script to clean up database integration logger references from the codebase.
Sprint 32 Part 1: Remove integration_events table functionality.
"""

import re
import os

def clean_redis_event_subscriber():
    """Remove database integration logger references from redis_event_subscriber.py"""
    file_path = 'src/core/services/redis_event_subscriber.py'

    with open(file_path, 'r') as f:
        content = f.read()

    # Remove all lines containing db_logger references
    lines = content.split('\n')
    cleaned_lines = []
    skip_until_dedent = False
    base_indent = None

    for line in lines:
        # Check if we're in a skip block
        if skip_until_dedent:
            # Get current indent
            current_indent = len(line) - len(line.lstrip())
            # If dedented back to base level or less, stop skipping
            if line.strip() and current_indent <= base_indent:
                skip_until_dedent = False
                cleaned_lines.append(line)
            # Skip this line
            continue

        # Check for db_logger references
        if 'db_logger' in line:
            # If it's an if statement, skip the whole block
            if 'if db_logger' in line:
                skip_until_dedent = True
                base_indent = len(line) - len(line.lstrip())
            # Skip single lines with db_logger
            continue

        # Keep all other lines
        cleaned_lines.append(line)

    # Write back the cleaned content
    with open(file_path, 'w') as f:
        f.write('\n'.join(cleaned_lines))

    print(f"Cleaned {file_path}")

def clean_websocket_broadcaster():
    """Check and clean websocket_broadcaster.py if needed"""
    file_path = 'src/core/services/websocket_broadcaster.py'

    if not os.path.exists(file_path):
        print(f"File {file_path} does not exist")
        return

    with open(file_path, 'r') as f:
        content = f.read()

    if 'database_integration_logger' in content.lower() or 'db_logger' in content:
        # Remove references similar to redis_event_subscriber
        lines = content.split('\n')
        cleaned_lines = []
        skip_until_dedent = False
        base_indent = None

        for line in lines:
            if skip_until_dedent:
                current_indent = len(line) - len(line.lstrip())
                if line.strip() and current_indent <= base_indent:
                    skip_until_dedent = False
                    cleaned_lines.append(line)
                continue

            if 'db_logger' in line or 'DatabaseIntegrationLogger' in line:
                if 'if db_logger' in line:
                    skip_until_dedent = True
                    base_indent = len(line) - len(line.lstrip())
                continue

            cleaned_lines.append(line)

        with open(file_path, 'w') as f:
            f.write('\n'.join(cleaned_lines))

        print(f"Cleaned {file_path}")
    else:
        print(f"No database integration logger references found in {file_path}")

if __name__ == '__main__':
    print("Sprint 32: Removing database integration logger references...")
    clean_redis_event_subscriber()
    clean_websocket_broadcaster()
    print("Cleanup complete!")