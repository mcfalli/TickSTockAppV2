#!/usr/bin/env python3
"""
Script to find and fix Unicode characters in Python files that cause encoding issues.
"""

import os
import sys
import re
from pathlib import Path

# Unicode character mappings
UNICODE_REPLACEMENTS = {
    '✓': '[OK]',
    '✗': '[FAIL]',
    '✅': '[SUCCESS]',
    '❌': '[ERROR]',
    '⚠️': '[WARNING]',
    '📊': '[DATA]',
    '🚀': '[START]',
    '🔍': '[SEARCH]',
    '🚨': '[ALERT]',
    '📝': '[NOTE]',
    '📋': '[LIST]',
    '⚠': '[WARNING]',
    '🤖': '[BOT]',
    '📉': '[CHART]',
    '📈': '[TREND]',
    '💾': '[SAVE]',
    '🔄': '[SYNC]',
    '🔐': '[SECURE]',
    '⚡': '[FAST]',
    '🔧': '[CONFIG]',
    '🛠️': '[TOOLS]',
    '📚': '[DOCS]',
    '🎯': '[TARGET]',
    '💡': '[IDEA]',
    '🐛': '[BUG]',
    '🎉': '[CELEBRATE]',
    '👍': '[GOOD]',
    '👎': '[BAD]',
    '⭐': '[STAR]',
    '🌟': '[SPECIAL]',
    '💪': '[STRONG]',
    '🔥': '[HOT]',
    '❄️': '[COLD]',
    '☀️': '[SUNNY]',
    '🌙': '[NIGHT]',
    '🌍': '[WORLD]',
    '🏆': '[WINNER]',
    '🥇': '[FIRST]',
    '🥈': '[SECOND]',
    '🥉': '[THIRD]',
    '🎈': '[BALLOON]',
    '🎁': '[GIFT]',
    '🎪': '[CIRCUS]',
}

def find_unicode_characters(file_path):
    """Find all Unicode characters in a file that might cause encoding issues."""
    unicode_found = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            for line_num, line in enumerate(content.split('\n'), 1):
                for char in line:
                    if ord(char) > 127:  # Non-ASCII character
                        unicode_found.append((line_num, char, line.strip()))
        return unicode_found
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return []

def fix_unicode_in_file(file_path, dry_run=True):
    """Fix Unicode characters in a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content
        changes_made = []

        # Replace known Unicode characters
        for unicode_char, replacement in UNICODE_REPLACEMENTS.items():
            if unicode_char in content:
                count = content.count(unicode_char)
                content = content.replace(unicode_char, replacement)
                changes_made.append(f"  Replaced {count} instances of '{unicode_char}' with '{replacement}'")

        # Check for any remaining non-ASCII characters
        remaining_unicode = []
        for char in content:
            if ord(char) > 127 and char not in ['\n', '\r', '\t']:
                if char not in remaining_unicode:
                    remaining_unicode.append(char)

        if changes_made or remaining_unicode:
            print(f"\n{file_path}:")
            if changes_made:
                for change in changes_made:
                    print(change)
            if remaining_unicode:
                print(f"  [WARNING] Remaining Unicode characters: {remaining_unicode}")

            if not dry_run and changes_made:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print("  [FIXED] File updated")
            elif dry_run and changes_made:
                print("  [DRY RUN] File would be updated")

            return True

        return False

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def scan_directory(directory, file_pattern="*.py", dry_run=True):
    """Scan directory for files with Unicode issues."""
    dir_path = Path(directory)
    files_with_issues = []

    for file_path in dir_path.rglob(file_pattern):
        # Skip certain directories
        if any(skip in str(file_path) for skip in ['.git', '__pycache__', '.pytest_cache', 'node_modules']):
            continue

        if fix_unicode_in_file(file_path, dry_run):
            files_with_issues.append(file_path)

    return files_with_issues

def main():
    """Main function."""
    import argparse
    parser = argparse.ArgumentParser(description='Fix Unicode issues in Python files')
    parser.add_argument('path', nargs='?', default='.', help='Path to scan (file or directory)')
    parser.add_argument('--fix', action='store_true', help='Actually fix the files (default is dry run)')
    parser.add_argument('--pattern', default='*.py', help='File pattern to match (default: *.py)')

    args = parser.parse_args()

    path = Path(args.path)
    dry_run = not args.fix

    print("Unicode Character Fixer")
    print("=" * 50)
    print(f"Mode: {'FIX' if not dry_run else 'DRY RUN'}")
    print(f"Path: {path.absolute()}")
    print(f"Pattern: {args.pattern}")
    print("=" * 50)

    if path.is_file():
        # Single file
        if fix_unicode_in_file(path, dry_run):
            print(f"\n1 file {'would be' if dry_run else 'was'} modified")
    else:
        # Directory
        files_with_issues = scan_directory(path, args.pattern, dry_run)

        print("\n" + "=" * 50)
        print(f"Summary: {len(files_with_issues)} files {'would be' if dry_run else 'were'} modified")

        if dry_run and files_with_issues:
            print("\nTo actually fix these files, run with --fix flag:")
            print(f"  python {sys.argv[0]} --fix")

if __name__ == "__main__":
    main()