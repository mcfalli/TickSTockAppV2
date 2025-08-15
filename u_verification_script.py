#!/usr/bin/env python3
"""
TickStock Migration Verification Script - Enhanced Version
Verifies that all files were migrated correctly according to the mapping
Includes file size comparison and better binary file handling
"""

import os
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime

class MigrationVerifier:
    def __init__(self, source_dir: str = r"C:\Users\McDude\TickStockApp",
                 dest_dir: str = r"C:\Users\McDude\TickStockAppV2"):
        self.source_dir = Path(source_dir)
        self.dest_dir = Path(dest_dir)
        self.mapping_file = self.dest_dir / "migration_mapping.json"
        self.verification_results = {
            'verified': [],
            'missing': [],
            'different': [],
            'extra': []
        }
        self.stats = {
            'total_mapped': 0,
            'files_verified': 0,
            'files_missing': 0,
            'files_different': 0,
            'extra_files': 0,
            'total_size_source': 0,
            'total_size_dest': 0
        }
    
    def load_mapping(self) -> Dict:
        """Load the migration mapping from JSON"""
        if not self.mapping_file.exists():
            raise FileNotFoundError(f"Mapping file not found: {self.mapping_file}")
        
        with open(self.mapping_file, 'r') as f:
            return json.load(f)
    
    def calculate_file_hash(self, filepath: Path) -> str:
        """Calculate MD5 hash of a file"""
        hash_md5 = hashlib.md5()
        try:
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            return f"ERROR: {e}"
    
    def get_file_info(self, filepath: Path) -> Dict:
        """Get file size and modification time"""
        if filepath.exists():
            stat = filepath.stat()
            return {
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
            }
        return {'size': 0, 'modified': None}
    
    def verify_migration(self) -> Dict:
        """Verify all files were migrated correctly"""
        print("Loading migration mapping...")
        mapping_data = self.load_mapping()
        mappings = mapping_data.get('mappings', [])
        
        self.stats['total_mapped'] = len(mappings)
        
        print(f"Verifying {self.stats['total_mapped']} file mappings...")
        print("=" * 60)
        
        # Verify each mapped file
        for i, mapping in enumerate(mappings, 1):
            source_file = Path(mapping['source'])
            dest_file = Path(mapping['dest'])
            
            # Check if destination file exists
            if not dest_file.exists():
                self.verification_results['missing'].append({
                    'source': str(source_file),
                    'dest': str(dest_file),
                    'relative': mapping['relative_dest']
                })
                self.stats['files_missing'] += 1
                print(f"✗ Missing: {mapping['relative_dest']}")
            else:
                # Get file info
                source_info = self.get_file_info(source_file)
                dest_info = self.get_file_info(dest_file)
                
                # Update size statistics
                self.stats['total_size_source'] += source_info['size']
                self.stats['total_size_dest'] += dest_info['size']
                
                # Compare file contents via hash
                if source_file.exists():
                    source_hash = self.calculate_file_hash(source_file)
                    dest_hash = self.calculate_file_hash(dest_file)
                    
                    if source_hash == dest_hash:
                        self.verification_results['verified'].append({
                            'source': str(source_file),
                            'dest': str(dest_file),
                            'relative': mapping['relative_dest'],
                            'hash': source_hash,
                            'size': dest_info['size']
                        })
                        self.stats['files_verified'] += 1
                        if i % 10 == 0:  # Print progress every 10 files
                            print(f"✓ Verified {i}/{self.stats['total_mapped']} files...")
                    else:
                        # Check if it's just a line ending difference (CRLF vs LF)
                        is_text_file = self._is_text_file(dest_file)
                        
                        self.verification_results['different'].append({
                            'source': str(source_file),
                            'dest': str(dest_file),
                            'relative': mapping['relative_dest'],
                            'source_hash': source_hash,
                            'dest_hash': dest_hash,
                            'source_size': source_info['size'],
                            'dest_size': dest_info['size'],
                            'size_diff': dest_info['size'] - source_info['size'],
                            'is_text': is_text_file,
                            'note': 'May be line ending difference' if is_text_file and abs(dest_info['size'] - source_info['size']) < 100 else None
                        })
                        self.stats['files_different'] += 1
                        print(f"⚠ Different: {mapping['relative_dest']} (size diff: {dest_info['size'] - source_info['size']} bytes)")
                else:
                    # Source doesn't exist but dest does
                    self.verification_results['verified'].append({
                        'source': 'N/A - Source missing',
                        'dest': str(dest_file),
                        'relative': mapping['relative_dest'],
                        'size': dest_info['size']
                    })
                    self.stats['files_verified'] += 1
        
        # Check for extra files in destination (not in mapping)
        self._check_extra_files(mapping_data)
        
        return self._create_report()
    
    def _is_text_file(self, filepath: Path) -> bool:
        """Check if file is likely a text file based on extension"""
        text_extensions = {'.py', '.txt', '.md', '.json', '.yml', '.yaml', 
                          '.ini', '.cfg', '.conf', '.html', '.css', '.js',
                          '.sql', '.sh', '.bat', '.ps1', '.env', '.gitignore'}
        return filepath.suffix.lower() in text_extensions
    
    def _check_extra_files(self, mapping_data: Dict):
        """Check for files in destination that aren't in the mapping"""
        print("\nChecking for extra files in destination...")
        
        # Get all destination files from mapping
        mapped_dest_files = set()
        for mapping in mapping_data.get('mappings', []):
            dest_path = Path(mapping['dest'])
            mapped_dest_files.add(str(dest_path))
        
        # Files we expect to exist that aren't in the mapping
        expected_extra_files = {
            'migration_mapping.json',
            'migration_mapping_readable.txt',
            'migration_report.json',
            'migration_report.txt',
            'folder_creation_summary.json',
            'verification_report.json',
            'verification_report.txt',
            'u_migrate_files.py',
            'u_create_folder_structure.py',
            'u_verify_migration.py',
            'u_create_dependencies.py',
            'u_update_imports.py'
        }
        
        # Walk destination directory
        for root, dirs, files in os.walk(self.dest_dir):
            # Skip certain directories
            skip_dirs = {'.git', '__pycache__', 'venv', '.venv', 'logs', 'node_modules'}
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            
            for file in files:
                if file.endswith('.pyc') or file in expected_extra_files:
                    continue
                    
                file_path = Path(root) / file
                
                # Check if this file is in our mapping
                if str(file_path) not in mapped_dest_files:
                    relative_path = file_path.relative_to(self.dest_dir)
                    
                    # Check if it's an __init__.py or README that we created
                    if file in ['__init__.py', 'README.md', '.env.example'] or \
                       file.endswith('.py') and str(relative_path).startswith('config/environments/'):
                        continue  # These are expected extra files
                    
                    self.verification_results['extra'].append({
                        'path': str(relative_path),
                        'size': file_path.stat().st_size
                    })
                    self.stats['extra_files'] += 1
    
    def _create_report(self) -> Dict:
        """Create verification report"""
        return {
            'summary': {
                'source_dir': str(self.source_dir),
                'dest_dir': str(self.dest_dir),
                'timestamp': datetime.now().isoformat(),
                'success': self.stats['files_missing'] == 0 and self.stats['files_different'] == 0,
                'total_size_source_mb': round(self.stats['total_size_source'] / (1024 * 1024), 2),
                'total_size_dest_mb': round(self.stats['total_size_dest'] / (1024 * 1024), 2)
            },
            'statistics': self.stats,
            'results': self.verification_results
        }
    
    def save_report(self, report: Dict, filename: str = "verification_report.json"):
        """Save verification report"""
        report_path = self.dest_dir / filename
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n✓ Verification report saved to: {report_path}")
        
        # Create human-readable report
        readable_path = self.dest_dir / "verification_report.txt"
        with open(readable_path, 'w') as f:
            f.write("MIGRATION VERIFICATION REPORT\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Timestamp: {report['summary']['timestamp']}\n")
            f.write(f"Source: {report['summary']['source_dir']}\n")
            f.write(f"Destination: {report['summary']['dest_dir']}\n")
            f.write(f"Overall Success: {report['summary']['success']}\n")
            f.write(f"Total Size (Source): {report['summary']['total_size_source_mb']} MB\n")
            f.write(f"Total Size (Dest): {report['summary']['total_size_dest_mb']} MB\n")
            f.write("\n" + "=" * 80 + "\n\n")
            
            f.write("STATISTICS:\n")
            f.write("-" * 40 + "\n")
            for key, value in report['statistics'].items():
                if 'size' not in key:  # Skip raw size stats
                    f.write(f"{key.replace('_', ' ').title()}: {value}\n")
            
            if report['results']['missing']:
                f.write("\n" + "=" * 80 + "\n")
                f.write("MISSING FILES:\n")
                f.write("-" * 40 + "\n")
                for file in report['results']['missing']:
                    f.write(f"  - {file['relative']}\n")
            
            if report['results']['different']:
                f.write("\n" + "=" * 80 + "\n")
                f.write("FILES WITH DIFFERENT CONTENT:\n")
                f.write("-" * 40 + "\n")
                for file in report['results']['different']:
                    f.write(f"  - {file['relative']} (size diff: {file.get('size_diff', 0)} bytes)")
                    if file.get('note'):
                        f.write(f" [{file['note']}]")
                    f.write("\n")
            
            if report['results']['extra']:
                f.write("\n" + "=" * 80 + "\n")
                f.write("EXTRA FILES (not in mapping):\n")
                f.write("-" * 40 + "\n")
                total_extra_size = sum(f['size'] for f in report['results']['extra'])
                f.write(f"Total: {len(report['results']['extra'])} files ({round(total_extra_size / 1024, 2)} KB)\n\n")
                for file in report['results']['extra'][:20]:  # Limit to first 20
                    f.write(f"  - {file['path']} ({file['size']} bytes)\n")
                if len(report['results']['extra']) > 20:
                    f.write(f"  ... and {len(report['results']['extra']) - 20} more\n")
        
        print(f"✓ Readable report saved to: {readable_path}")
        
        return report
    
    def print_summary(self, report: Dict):
        """Print verification summary to console"""
        print("\n" + "=" * 60)
        print("VERIFICATION SUMMARY")
        print("=" * 60)
        
        stats = report['statistics']
        print(f"Total files mapped: {stats['total_mapped']}")
        print(f"Files verified successfully: {stats['files_verified']}")
        print(f"Files missing: {stats['files_missing']}")
        print(f"Files with different content: {stats['files_different']}")
        print(f"Extra files found: {stats['extra_files']}")
        print(f"\nTotal size migrated: {report['summary']['total_size_dest_mb']} MB")
        
        if report['summary']['success']:
            print("\n✅ MIGRATION VERIFIED SUCCESSFULLY!")
            print("All files have been correctly migrated to their new locations.")
        else:
            print("\n⚠ ISSUES FOUND - Please review the report")
            
            if stats['files_missing'] > 0:
                print(f"\n  ❌ {stats['files_missing']} files are missing in destination")
            if stats['files_different'] > 0:
                print(f"  ⚠️  {stats['files_different']} files have different content")
                print("     (This may be due to line ending differences - check the detailed report)")


def main():
    """Main execution"""
    print("TickStock Migration Verifier - Enhanced Version")
    print("=" * 60)
    
    verifier = MigrationVerifier()
    
    try:
        report = verifier.verify_migration()
        verifier.save_report(report)
        verifier.print_summary(report)
    except FileNotFoundError as e:
        print(f"\n✗ Error: {e}")
        print("Please run the migration mapper first to create the mapping file")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0 if report['summary']['success'] else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())