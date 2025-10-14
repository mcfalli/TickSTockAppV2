#!/usr/bin/env python3
"""
util_extract_documentation.py

Extracts all Markdown documentation from the project into a single file
or directory for easy import into Claude or other documentation systems.
In directory mode, files are placed directly in the output directory with
their immediate parent folder as a prefix.

Usage:
    python util_extract_documentation.py [--output-dir "./extracted_docs"] [--single-file]
"""

import argparse
import json
import re
import shutil
from datetime import datetime
from pathlib import Path


class DocumentationExtractor:
    """Extracts and consolidates project documentation."""

    def __init__(self, project_root='.', output_dir=Path.home() / 'Documents' / 'TickStock' / 'Extracted_Docs'):
        self.project_root = Path(project_root)
        self.output_dir = Path(output_dir)
        self.extracted_files = []
        self.toc_entries = []

        # Directories to always include
        self.include_dirs = ['docs', 'market_data_service', 'processing',
                           'universe', 'data_flow', 'session_accumulation',
                           'market_analytics']

        # Files to always include from root
        self.include_root_files = ['README.md', 'CHANGELOG.md', 'CONTRIBUTING.md']

    def extract_all(self, single_file=False):
        """Extract all documentation based on mode."""
        print(f"🔍 Extracting documentation from: {self.project_root}")

        if single_file:
            self._extract_to_single_file()
        else:
            self._extract_to_directory()

        self._create_manifest()
        print(f"✅ Extraction complete! Files saved to: {self.output_dir}")

    def _extract_to_directory(self):
        """Extract files to a flat directory with renamed files."""
        # Create output directory
        if self.output_dir.exists():
            shutil.rmtree(self.output_dir)
        self.output_dir.mkdir(parents=True)

        # Extract from specific directories
        for dir_name in self.include_dirs:
            dir_path = self.project_root / dir_name
            if dir_path.exists():
                self._extract_directory(dir_path)

        # Extract root documentation files
        for file_name in self.include_root_files:
            file_path = self.project_root / file_name
            if file_path.exists():
                self._copy_file(file_path, self.output_dir / file_name, 'root')

        # Extract any component README files
        self._extract_component_readmes()

    def _extract_to_single_file(self):
        """Extract all documentation into a single markdown file."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        output_file = self.output_dir / 'TickStock_Complete_Documentation.md'

        with open(output_file, 'w', encoding='utf-8') as f:
            # Write header
            f.write("# TickStock Complete Documentation\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("## Table of Contents\n\n")

            # First pass - collect all files and build TOC
            all_md_files = self._find_all_md_files()

            # Write TOC
            for i, (file_path, rel_path) in enumerate(all_md_files):
                anchor = f"doc-{i}"
                self.toc_entries.append(f"- [{rel_path}](#{anchor})\n")
                f.write(f"- [{rel_path}](#{anchor})\n")

            f.write("\n---\n\n")

            # Second pass - write content
            for i, (file_path, rel_path) in enumerate(all_md_files):
                anchor = f"doc-{i}"
                f.write(f'<a id="{anchor}"></a>\n\n')
                f.write(f"# 📄 {rel_path}\n\n")

                try:
                    with open(file_path, encoding='utf-8') as md_file:
                        content = md_file.read()
                        # Adjust heading levels to prevent conflicts
                        content = self._adjust_heading_levels(content)
                        f.write(content)
                        f.write("\n\n---\n\n")

                    self.extracted_files.append(str(rel_path))
                    print(f"  ✓ Extracted: {rel_path}")

                except Exception as e:
                    print(f"  ✗ Error reading {rel_path}: {e}")
                    f.write(f"*Error reading file: {e}*\n\n---\n\n")

    def _find_all_md_files(self):
        """Find all markdown files in the project."""
        md_files = []

        # Search in specified directories
        for dir_name in self.include_dirs:
            dir_path = self.project_root / dir_name
            if dir_path.exists():
                for md_file in dir_path.rglob('*.md'):
                    rel_path = md_file.relative_to(self.project_root)
                    md_files.append((md_file, rel_path))

        # Add root files
        for file_name in self.include_root_files:
            file_path = self.project_root / file_name
            if file_path.exists():
                md_files.append((file_path, Path(file_name)))

        # Find component READMEs
        for item in self.project_root.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                readme = item / 'README.md'
                if readme.exists():
                    rel_path = readme.relative_to(self.project_root)
                    if (readme, rel_path) not in md_files:
                        md_files.append((readme, rel_path))

        return sorted(md_files, key=lambda x: str(x[1]))

    def _adjust_heading_levels(self, content):
        """Adjust heading levels to prevent TOC conflicts."""
        lines = content.split('\n')
        adjusted_lines = []

        for line in lines:
            if line.startswith('#'):
                # Count the number of # symbols
                level = len(line) - len(line.lstrip('#'))
                if level == 1:
                    # Convert # to ##
                    line = '#' + line
                adjusted_lines.append(line)
            else:
                adjusted_lines.append(line)

        return '\n'.join(adjusted_lines)

    def _extract_directory(self, directory):
        """Extract all .md files to a flat directory."""
        for md_file in directory.rglob('*.md'):
            # Use file name directly, ignoring source directory structure
            output_path = self.output_dir / md_file.name
            # Use immediate parent folder as prefix
            parent_folder = md_file.parent.name
            self._copy_file(md_file, output_path, parent_folder)

    def _extract_component_readmes(self):
        """Extract README.md files from component directories to a flat directory."""
        for item in self.project_root.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                readme = item / 'README.md'
                if readme.exists() and item.name not in self.include_dirs:
                    output_path = self.output_dir / 'README.md'
                    self._copy_file(readme, output_path, item.name)

    def _sanitize_prefix(self, prefix):
        """Sanitize folder name to be safe for filenames."""
        # Replace spaces and special characters with underscores, keep alphanumeric
        return re.sub(r'[^a-zA-Z0-9\-]', '_', prefix).strip('_')

    def _copy_file(self, source, destination, parent_folder):
        """Copy a file to a flat directory with folder prefix."""
        # Sanitize the parent folder name for the prefix
        sanitized_prefix = self._sanitize_prefix(parent_folder)

        # Create new filename with parent folder prefix
        new_filename = f"{sanitized_prefix}_{destination.name}"
        final_destination = self.output_dir / new_filename

        # Handle potential filename conflicts
        counter = 1
        while final_destination.exists():
            new_filename = f"{sanitized_prefix}_{counter}_{destination.name}"
            final_destination = self.output_dir / new_filename
            counter += 1

        shutil.copy2(source, final_destination)
        rel_path = final_destination.relative_to(self.output_dir)
        self.extracted_files.append(str(rel_path))
        print(f"  ✓ Copied: {source.relative_to(self.project_root)} -> {rel_path} (prefix: {sanitized_prefix})")

    def _create_manifest(self):
        """Create a manifest of extracted files."""
        manifest = {
            'extraction_date': datetime.now().isoformat(),
            'project_root': str(self.project_root.absolute()),
            'output_directory': str(self.output_dir.absolute()),
            'total_files': len(self.extracted_files),
            'files': sorted(self.extracted_files)
        }

        manifest_path = self.output_dir / 'extraction_manifest.json'
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)

        # Also create a simple index
        index_path = self.output_dir / 'INDEX.md'
        with open(index_path, 'w') as f:
            f.write("# Extracted Documentation Index\n\n")
            f.write(f"Generated: {manifest['extraction_date']}\n\n")
            f.write("## Files\n\n")
            for file in sorted(self.extracted_files):
                f.write(f"- {file}\n")


def main():
    parser = argparse.ArgumentParser(
        description='Extract TickStock documentation for external use'
    )
    parser.add_argument(
        '--output-dir',
        default=str(Path.home() / 'Documents' / 'TickStock' / 'Extracted_Docs'),
        help='Output directory for extracted documentation'
    )
    parser.add_argument(
        '--single-file',
        action='store_true',
        help='Extract all documentation into a single file'
    )
    parser.add_argument(
        '--project-root',
        default='.',
        help='Project root directory'
    )

    args = parser.parse_args()

    extractor = DocumentationExtractor(
        project_root=args.project_root,
        output_dir=args.output_dir
    )

    extractor.extract_all(single_file=args.single_file)

    print("\n📋 Usage for Claude:")
    if args.single_file:
        print(f"Upload: {args.output_dir}/TickStock_Complete_Documentation.md")
    else:
        print(f"Upload the entire '{args.output_dir}' directory")


if __name__ == '__main__':
    main()
