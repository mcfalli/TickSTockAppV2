#!/usr/bin/env python3
"""
Fix all remaining Unicode encoding issues in TickStockAppV2.
Replaces all Unicode emojis and special characters with ASCII equivalents.
"""

import os
import re
from pathlib import Path

# Mapping of Unicode characters to ASCII replacements
UNICODE_REPLACEMENTS = {
    '✅': '[SUCCESS]',
    '❌': '[ERROR]',
    '⚠️': '[WARNING]',
    '✓': '[OK]',
    '✗': '[FAIL]',
    '🚀': '[START]',
    '🔄': '[SYNC]',
    '📊': '[STATS]',
    '⚡': '[FAST]',
    '🎯': '[TARGET]',
    '💾': '[SAVE]',
    '🔐': '[SECURE]',
    '📋': '[LIST]',
    '🚨': '[ALERT]',
    '🤖': '[BOT]',
    '⏰': '[TIME]',
    '📈': '[UP]',
    '📉': '[DOWN]',
    '🔥': '[HOT]',
    '❄️': '[COLD]',
    '🌟': '[STAR]',
    '💡': '[IDEA]',
    '🔔': '[NOTIFY]',
    '🛑': '[STOP]',
    '✔️': '[CHECK]',
    '❓': '[QUESTION]',
    '❗': '[IMPORTANT]',
    '➡️': '->',
    '⬅️': '<-',
    '⬆️': '^',
    '⬇️': 'v',
    '•': '*',
    '→': '->',
    '←': '<-',
    '↑': '^',
    '↓': 'v',
    '—': '-',
    '–': '-',
    '"': '"',
    '"': '"',
    ''': "'",
    ''': "'",
    '…': '...',
    '©': '(c)',
    '®': '(R)',
    '™': '(TM)',
    '°': 'deg',
    '±': '+/-',
    '×': 'x',
    '÷': '/',
    '≈': '~',
    '≠': '!=',
    '≤': '<=',
    '≥': '>=',
    '∞': 'inf',
    'µ': 'u',
    'π': 'pi',
    'Σ': 'sum',
    '√': 'sqrt',
    '∫': 'int',
    '∂': 'd',
    '∆': 'delta',
    'α': 'alpha',
    'β': 'beta',
    'γ': 'gamma',
    'δ': 'delta',
    'ε': 'epsilon',
    'θ': 'theta',
    'λ': 'lambda',
    'μ': 'mu',
    'σ': 'sigma',
    'τ': 'tau',
    'φ': 'phi',
    'ω': 'omega',
}

def fix_unicode_in_file(file_path):
    """Fix Unicode characters in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        print(f"  [SKIP] Cannot read {file_path} - encoding issue")
        return False

    original_content = content
    changes_made = []

    # Replace each Unicode character
    for unicode_char, ascii_replacement in UNICODE_REPLACEMENTS.items():
        if unicode_char in content:
            content = content.replace(unicode_char, ascii_replacement)
            changes_made.append(f"{unicode_char} -> {ascii_replacement}")

    # Check if any changes were made
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  [FIXED] {file_path}")
        print(f"    Replaced {len(changes_made)} Unicode characters")
        return True

    return False

def find_python_files(directory):
    """Find all Python files in the directory."""
    python_files = []
    for root, dirs, files in os.walk(directory):
        # Skip virtual environment and cache directories
        dirs[:] = [d for d in dirs if d not in ['venv', '__pycache__', '.git', 'node_modules']]

        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))

    return python_files

def main():
    """Main function to fix all Unicode issues."""
    print("=" * 60)
    print("Fixing All Unicode Issues in TickStockAppV2")
    print("=" * 60)

    # Change to TickStockAppV2 directory
    base_dir = "C:/Users/McDude/TickStockAppV2"
    os.chdir(base_dir)

    # Specific files we know have issues
    priority_files = [
        "src/presentation/websocket/polygon_client.py",
        "src/core/services/redis_event_subscriber.py",
        "src/core/services/pattern_alert_manager.py",
        "src/infrastructure/cache/redis_pattern_cache.py",
        "src/core/services/fallback_pattern_detector.py",
        "src/core/services/pattern_discovery_service.py",
        "src/presentation/websocket/data_publisher.py",
        "src/presentation/websocket/publisher.py",
        "src/api/rest/pattern_consumer.py",
        "src/api/rest/pattern_discovery.py"
    ]

    print("\n1. Fixing priority files...")
    fixed_count = 0
    for file_path in priority_files:
        if os.path.exists(file_path):
            if fix_unicode_in_file(file_path):
                fixed_count += 1
        else:
            print(f"  [SKIP] File not found: {file_path}")

    print(f"\n2. Scanning all Python files in src/...")
    src_files = find_python_files("src")

    for file_path in src_files:
        # Skip if already processed
        if file_path.replace('\\', '/') not in [p.replace('\\', '/') for p in priority_files]:
            if fix_unicode_in_file(file_path):
                fixed_count += 1

    print("\n" + "=" * 60)
    print(f"[COMPLETE] Fixed {fixed_count} files")
    print("=" * 60)

    if fixed_count > 0:
        print("\nNext steps:")
        print("1. Restart services to pick up changes")
        print("2. Monitor logs for any remaining Unicode errors")
        print("3. All Unicode characters have been replaced with ASCII equivalents")
    else:
        print("\nNo Unicode issues found in Python files.")

if __name__ == "__main__":
    main()