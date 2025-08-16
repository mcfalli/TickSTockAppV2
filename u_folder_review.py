#!/usr/bin/env python3
"""
Folder-by-folder integrity checker for TickStock V2
Reviews each directory systematically for issues
"""

import ast
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict
import json

class FolderIntegrityChecker:
    """Check integrity folder by folder."""
    
    def __init__(self, base_path: str = r"C:\Users\McDude\TickStockAppV2"):
        self.base_path = Path(base_path)
        self.current_folder = None
        self.issues = defaultdict(list)
        
    def check_folder(self, folder_path: str) -> Dict:
        """Check a specific folder for issues."""
        folder = self.base_path / folder_path
        self.current_folder = folder_path
        
        if not folder.exists():
            return {'error': f"Folder {folder_path} does not exist"}
            
        results = {
            'folder': folder_path,
            'files': [],
            'issues': [],
            'imports': {},
            'exports': {},
            'syntax_errors': [],
            'missing_init': False,
            'stats': {}
        }
        
        # Check for __init__.py
        init_file = folder / "__init__.py"
        if not init_file.exists() and not any(folder.glob("*.py")):
            results['missing_init'] = True
            results['issues'].append("Missing __init__.py file")
        
        # Analyze each Python file
        py_files = list(folder.glob("*.py"))
        results['stats']['total_files'] = len(py_files)
        
        for py_file in py_files:
            file_info = self._analyze_file(py_file)
            results['files'].append(file_info)
            
            if file_info['syntax_error']:
                results['syntax_errors'].append(file_info)
            
            # Collect imports and exports
            rel_path = str(py_file.relative_to(self.base_path))
            results['imports'][rel_path] = file_info['imports']
            results['exports'][rel_path] = file_info['exports']
        
        # Check for common issues
        self._check_folder_issues(folder, results)
        
        return results
    
    def _analyze_file(self, file_path: Path) -> Dict:
        """Analyze a single Python file."""
        rel_path = str(file_path.relative_to(self.base_path))
        
        file_info = {
            'name': file_path.name,
            'path': rel_path,
            'size': file_path.stat().st_size,
            'imports': [],
            'exports': [],
            'classes': [],
            'functions': [],
            'syntax_error': None,
            'issues': []
        }
        
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            
            # Check for common issues in content
            if content.strip() == "":
                file_info['issues'].append("Empty file")
            
            if "# TODO" in content or "# FIXME" in content:
                file_info['issues'].append("Contains TODO/FIXME comments")
            
            # Parse AST
            tree = ast.parse(content)
            
            # Extract imports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        file_info['imports'].append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ''
                    if module:
                        file_info['imports'].append(module)
                    for alias in node.names:
                        if alias.name != '*':
                            file_info['imports'].append(f"{module}.{alias.name}")
                elif isinstance(node, ast.ClassDef):
                    file_info['classes'].append(node.name)
                    file_info['exports'].append(node.name)
                elif isinstance(node, ast.FunctionDef):
                    if not node.name.startswith('_'):
                        file_info['functions'].append(node.name)
                        file_info['exports'].append(node.name)
                        
        except SyntaxError as e:
            file_info['syntax_error'] = {
                'line': e.lineno,
                'message': str(e.msg),
                'text': e.text[:80] if e.text else None
            }
            file_info['issues'].append(f"Syntax error at line {e.lineno}: {e.msg}")
            
        except Exception as e:
            file_info['issues'].append(f"Parse error: {str(e)}")
            
        return file_info
    
    def _check_folder_issues(self, folder: Path, results: Dict):
        """Check for folder-level issues."""
        
        # Check if __init__.py properly exports submodules
        init_file = folder / "__init__.py"
        if init_file.exists():
            try:
                init_content = init_file.read_text(encoding='utf-8', errors='ignore')
                
                # Check if it's empty
                if init_content.strip() == "" or init_content.strip() == '""""""':
                    results['issues'].append("__init__.py is empty - modules may not be properly exported")
                
                # Check if it has __all__ defined
                if '__all__' not in init_content and len(results['files']) > 1:
                    results['issues'].append("__init__.py missing __all__ definition")
                    
            except Exception as e:
                results['issues'].append(f"Cannot read __init__.py: {e}")
        
        # Check for test files mixed with source
        has_tests = any(f['name'].startswith('test_') for f in results['files'])
        has_source = any(not f['name'].startswith('test_') and f['name'] != '__init__.py' 
                        for f in results['files'])
        
        if has_tests and has_source:
            results['issues'].append("Test files mixed with source files")
        
        # Check for naming conventions
        for file_info in results['files']:
            if file_info['name'] != '__init__.py':
                # Check for camelCase files (should be snake_case)
                if any(c.isupper() for c in file_info['name'][1:-3]):  # Skip first char and .py
                    file_info['issues'].append("File uses camelCase instead of snake_case")
                    
    def review_all_folders(self) -> Dict:
        """Review all folders in the project."""
        folders_to_check = [
            # Core application
            "src",
            "src/app.py",  # Check the main file specifically
            
            # API layer
            "src/api",
            "src/api/rest",
            "src/api/websocket",
            
            # Authentication
            "src/auth",
            
            # Core domain
            "src/core",
            "src/core/domain",
            "src/core/domain/events", 
            "src/core/domain/market",
            "src/core/services",
            "src/core/interfaces",
            
            # Infrastructure
            "src/infrastructure",
            "src/infrastructure/data_sources",
            "src/infrastructure/data_sources/polygon",
            "src/infrastructure/data_sources/synthetic",
            "src/infrastructure/database",
            "src/infrastructure/database/models",
            "src/infrastructure/cache",
            
            # Processing
            "src/processing",
            "src/processing/detectors",
            "src/processing/workers",
            "src/processing/pipeline",
            
            # Presentation
            "src/presentation",
            "src/presentation/websocket",
            "src/presentation/formatters",
            
            # Shared/Utils
            "src/shared",
            "src/shared/constants",
            "src/shared/utils",
            
            # Configuration
            "config",
            
            # Tests
            "tests"
        ]
        
        all_results = {}
        
        for folder_path in folders_to_check:
            # Handle individual files
            if folder_path.endswith('.py'):
                file_path = self.base_path / folder_path
                if file_path.exists():
                    folder = str(file_path.parent.relative_to(self.base_path))
                    if folder not in all_results:
                        all_results[folder] = self.check_folder(folder)
            else:
                all_results[folder_path] = self.check_folder(folder_path)
                
        return all_results
    
    def print_folder_report(self, folder_results: Dict):
        """Print a detailed report for a single folder."""
        print(f"\n{'='*80}")
        print(f"FOLDER: {folder_results['folder']}")
        print(f"{'='*80}")
        
        stats = folder_results.get('stats', {})
        print(f"📊 Files: {stats.get('total_files', 0)}")
        
        # Show issues
        if folder_results.get('issues'):
            print(f"\n⚠️ FOLDER ISSUES:")
            for issue in folder_results['issues']:
                print(f"  • {issue}")
                
        if folder_results.get('missing_init'):
            print(f"  ❌ Missing __init__.py")
            
        # Show file details
        if folder_results.get('files'):
            print(f"\n📁 FILES:")
            for file_info in folder_results['files']:
                status = "❌" if file_info.get('syntax_error') else "✅"
                print(f"  {status} {file_info['name']}")
                
                if file_info.get('syntax_error'):
                    err = file_info['syntax_error']
                    print(f"      Syntax error at line {err['line']}: {err['message']}")
                    if err.get('text'):
                        print(f"      Line content: {err['text']}")
                        
                if file_info.get('issues'):
                    for issue in file_info['issues']:
                        print(f"      ⚠️ {issue}")
                        
                if file_info.get('classes'):
                    print(f"      Classes: {', '.join(file_info['classes'])}")
                    
                if file_info.get('functions'):
                    print(f"      Functions: {', '.join(file_info['functions'][:5])}")
                    if len(file_info['functions']) > 5:
                        print(f"      ... and {len(file_info['functions'])-5} more")
                        
        print()
        
    def interactive_review(self):
        """Interactive folder-by-folder review."""
        print("=" * 80)
        print("INTERACTIVE FOLDER REVIEW")
        print("=" * 80)
        print("\nThis will review each folder and wait for your input.")
        print("Commands: [n]ext, [s]kip, [f]ix, [q]uit\n")
        
        folders = [
            # Most critical first
            "src",
            "src/core/services",
            "src/infrastructure/data_sources/polygon",
            "src/infrastructure/data_sources/synthetic",
            "src/presentation/websocket",
            "src/processing/detectors",
            "src/api/rest",
            "src/auth",
            "src/core/domain/events",
            "src/core/domain/market",
            "config"
        ]
        
        for folder in folders:
            results = self.check_folder(folder)
            self.print_folder_report(results)
            
            # Check if there are issues
            has_issues = (
                results.get('issues') or 
                results.get('syntax_errors') or
                any(f.get('issues') for f in results.get('files', []))
            )
            
            if has_issues:
                print(f"⚠️ This folder has issues that need review!")
                
            response = input("Action ([n]ext/[s]kip/[f]ix/[q]uit): ").lower()
            
            if response == 'q':
                break
            elif response == 'f':
                print("\nPlease fix the issues manually, then press Enter to continue...")
                input()
                # Re-check the folder
                results = self.check_folder(folder)
                self.print_folder_report(results)
            elif response == 's':
                continue
            else:  # Default to next
                continue
                
        print("\n" + "=" * 80)
        print("REVIEW COMPLETE")
        print("=" * 80)

def main():
    """Main execution."""
    import sys
    
    checker = FolderIntegrityChecker()
    
    if len(sys.argv) > 1:
        # Check specific folder
        folder = sys.argv[1]
        results = checker.check_folder(folder)
        checker.print_folder_report(results)
    else:
        # Interactive review
        checker.interactive_review()

if __name__ == "__main__":
    main()