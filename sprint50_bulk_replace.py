#!/usr/bin/env python3
"""Sprint 50: Bulk find & replace for Polygon → Massive rebrand."""
import os
import re
from pathlib import Path

# Define replacement patterns in order of execution
REPLACEMENTS = [
    # Class names
    ("PolygonDataProvider", "MassiveDataProvider"),
    ("PolygonAPI", "MassiveAPI"),
    ("PolygonWebSocketClient", "MassiveWebSocketClient"),

    # Environment variables (preserve old as fallback)
    ("POLYGON_API_KEY", "MASSIVE_API_KEY"),
    ("POLYGON_API_URL", "MASSIVE_API_URL"),
    ("POLYGON_WEBSOCKET_URL", "MASSIVE_WEBSOCKET_URL"),
    ("POLYGON_WEBSOCKET_MAX_RETRIES", "MASSIVE_WEBSOCKET_MAX_RETRIES"),
    ("POLYGON_WEBSOCKET_RECONNECT_DELAY", "MASSIVE_WEBSOCKET_RECONNECT_DELAY"),

    # Function names
    ("convert_polygon_tick", "convert_massive_tick"),
    ("from_polygon_ws", "from_massive_ws"),

    # String literals and URLs
    ("https://api.polygon.io", "https://api.massive.com"),
    ("wss://socket.polygon.io", "wss://socket.massive.com"),
    ("polygon.io", "massive.com"),
    ("Polygon.io", "Massive.com"),

    # Logger prefixes
    ("POLYGON-PROVIDER:", "MASSIVE-PROVIDER:"),
    ("POLYGON-API:", "MASSIVE-API:"),
    ("POLYGON-CLIENT:", "MASSIVE-CLIENT:"),

    # General terms in comments/docstrings
    ("Polygon WebSocket", "Massive WebSocket"),
    ("Polygon API", "Massive API"),
    ("Polygon", "Massive"),  # General case
]

# Files to exclude from replacement
EXCLUDE_PATTERNS = [
    "sprint50_",  # Sprint documentation
    "SPRINT50_",
    "__pycache__",
    ".git",
    ".pyc",
    "LAST_TEST_RUN.md",
]

def should_process_file(filepath: Path) -> bool:
    """Check if file should be processed."""
    # Check exclude patterns
    for pattern in EXCLUDE_PATTERNS:
        if pattern in str(filepath):
            return False

    # Process Python files, markdown, YAML, etc.
    valid_extensions = {".py", ".md", ".yml", ".yaml", ".txt", ".env", ".example", ".html", ".js"}
    if filepath.suffix in valid_extensions or filepath.name in {".env.example", "CLAUDE.md", "README.md"}:
        return True

    return False

def process_file(filepath: Path, replacements: list[tuple[str, str]]) -> int:
    """Process a single file with all replacements."""
    try:
        # Read file
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content
        changes = 0

        # Apply all replacements
        for old, new in replacements:
            if old in content:
                content = content.replace(old, new)
                changes += content.count(new) - original_content.count(new)

        # Write back if changed
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return changes

        return 0
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return 0

def main():
    """Execute bulk replacements."""
    root = Path(".")
    total_files = 0
    total_changes = 0

    print("Starting Sprint 50 bulk replacements...")
    print(f"Root directory: {root.absolute()}")
    print()

    # Process all files recursively
    for filepath in root.rglob("*"):
        if filepath.is_file() and should_process_file(filepath):
            changes = process_file(filepath, REPLACEMENTS)
            if changes > 0:
                total_files += 1
                total_changes += changes
                print(f"[OK] {filepath}: {changes} replacements")

    print()
    print("=" * 60)
    print(f"Complete! Modified {total_files} files with {total_changes} replacements")
    print("=" * 60)

if __name__ == "__main__":
    main()
