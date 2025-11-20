#!/usr/bin/env python3
"""Sprint 50 Pass 3: Final cleanup of remaining polygon references in docs"""

import os
from pathlib import Path

# Final replacements for current documentation
REPLACEMENTS = [
    # Current architecture docs - update to reflect current state
    ('("polygon", "synthetic", "tickstock_pl")', '("massive", "synthetic", "tickstock_pl")'),
    ('# polygon | synthetic | csv', '# massive | synthetic | csv'),

    # Recent sprint docs that should reflect current state
    ('(polygon|synthetic)', '(massive|synthetic)'),
    ("tick_data.get('source', 'polygon')", "tick_data.get('source', 'massive')"),
    ('- `source` (string): Always "polygon"', '- `source` (string): Always "massive"'),
    ('"source":"polygon"', '"source":"massive"'),
    ('ConnectionManager(polygon_url)', 'ConnectionManager(massive_url)'),

    # Historical sprint accomplishments - update data source lists in YAML
    ('["polygon",', '["massive",'),
    ('  polygon:', '  massive:'),
]

def should_skip_file(filepath: Path) -> bool:
    """Determine if file should be skipped."""
    # Skip sprint50 documentation
    if 'sprint50' in str(filepath).lower():
        return True
    # Skip if in venv
    if 'venv' in filepath.parts or '.venv' in filepath.parts:
        return True
    return False

def update_file(filepath: Path) -> tuple[bool, int]:
    """Update a single markdown file."""
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
    print(f"Sprint 50 Pass 3: Final polygon reference cleanup\n")

    md_files = list(root.rglob('*.md'))

    updated_count = 0
    total_replacements = 0

    for md_file in sorted(md_files):
        if should_skip_file(md_file):
            continue

        updated, count = update_file(md_file)
        if updated:
            rel_path = md_file.relative_to(root)
            print(f"[OK] {rel_path}: {count} replacements")
            updated_count += 1
            total_replacements += count

    print(f"\n{'='*60}")
    print(f"Pass 3 Complete:")
    print(f"  Files updated: {updated_count}")
    print(f"  Total replacements: {total_replacements}")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()
