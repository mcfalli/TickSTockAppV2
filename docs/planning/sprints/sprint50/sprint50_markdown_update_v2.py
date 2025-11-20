#!/usr/bin/env python3
"""Sprint 50: Update markdown files from Polygon to Massive (excluding sprint50 docs)"""

import os
import re
from pathlib import Path

# Replacements to apply
REPLACEMENTS = [
    # Directory and file paths
    ('polygon/', 'massive/'),
    ('polygon_client', 'massive_client'),

    # Config keys (but preserve as documentation of deprecated names)
    ("MASSIVE_API_KEY=your_polygon_key", "MASSIVE_API_KEY=your_massive_key"),

    # Source field values
    ('"source": "polygon"', '"source": "massive"'),
    ("'source': 'polygon'", "'source': 'massive'"),
    ("source: 'polygon'", "source: 'massive'"),
    ('- Real data: `source: \'polygon\'`', '- Real data: `source: \'massive\'`'),

    # Mock/test references
    ('mock_polygon', 'mock_massive'),
    ('fetch_polygon_', 'fetch_massive_'),

    # Provider lists and config
    ("['polygon']", "['massive']"),
    ('provider: "polygon"', 'provider: "massive"'),
    ('"provider": "polygon"', '"provider": "massive"'),

    # URLs and references
    ('Polygon.io', 'Massive.com'),

    # Comments and text (case-sensitive for precision)
    ('from polygon import', 'from massive import'),
    ('@mock.patch(\'src.data.polygon_client.', '@mock.patch(\'src.data.massive_client.'),

    # Data source type
    ('DATA_SOURCE_TYPE=polygon', 'DATA_SOURCE_TYPE=massive'),
]

def should_skip_file(filepath: Path) -> bool:
    """Determine if file should be skipped."""
    # Skip sprint50 documentation (it's documenting the rebrand)
    if 'sprint50' in str(filepath).lower():
        return True
    # Skip if in venv
    if 'venv' in filepath.parts or '.venv' in filepath.parts:
        return True
    return False

def update_file(filepath: Path) -> tuple[bool, int]:
    """Update a single markdown file with replacements."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content
        replacement_count = 0

        for old, new in REPLACEMENTS:
            if old in content:
                count = content.count(old)
                content = content.replace(old, new)
                replacement_count += count

        if content != original_content:
            with open(filepath, 'w', encoding='utf-8', newline='\n') as f:
                f.write(content)
            return True, replacement_count

        return False, 0

    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return False, 0

def main():
    """Main execution."""
    root = Path(__file__).parent
    print(f"Starting Sprint 50 markdown updates...")
    print(f"Root directory: {root}\n")

    # Find all markdown files
    md_files = list(root.rglob('*.md'))

    updated_count = 0
    total_replacements = 0
    skipped_count = 0

    for md_file in sorted(md_files):
        if should_skip_file(md_file):
            skipped_count += 1
            continue

        updated, count = update_file(md_file)
        if updated:
            rel_path = md_file.relative_to(root)
            print(f"[OK] {rel_path}: {count} replacements")
            updated_count += 1
            total_replacements += count

    print(f"\n{'='*60}")
    print(f"Markdown Update Complete:")
    print(f"  Files updated: {updated_count}")
    print(f"  Files skipped: {skipped_count} (sprint50 docs + venv)")
    print(f"  Total replacements: {total_replacements}")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()
