#!/usr/bin/env python3
"""
Project Index for Claude Code
Provides spatial-architectural awareness to prevent code duplication and misplacement.

Features:
- Directory tree structure visualization
- Markdown documentation mapping with section headers
- Directory purpose inference
- Full function and class signatures with type annotations
- Multi-language support (parsed vs listed)

Usage: python project_index.py
Output: PROJECT_INDEX.json
"""

__version__ = "0.1.0"

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Import shared utilities from scripts/index/
# Import shared utilities from index_utils
from index_utils import (
    ALLOWED_DIRS, IGNORE_DIRS, PARSEABLE_LANGUAGES, CODE_EXTENSIONS, MARKDOWN_EXTENSIONS,
    DIRECTORY_PURPOSES, extract_python_signatures, extract_javascript_signatures,
    extract_shell_signatures, extract_markdown_structure, infer_file_purpose, 
    infer_directory_purpose, get_language_name, should_index_file
)

# Limits to keep it fast and simple
MAX_FILES = 10000
MAX_INDEX_SIZE = 1024 * 1024  # 1MB
MAX_TREE_DEPTH = 5


def generate_tree_structure(root_path: Path, max_depth: int = MAX_TREE_DEPTH) -> List[str]:
    """Generate a compact ASCII tree representation of the directory structure."""
    tree_lines = []
    
    def should_include_dir(path: Path) -> bool:
        """Check if directory should be included in tree."""
        try:
            rel_path = path.relative_to(root_path)
            top_level_dir = rel_path.parts[0] if rel_path.parts else ''
            return (
                (not top_level_dir or top_level_dir in ALLOWED_DIRS) and
                path.name not in IGNORE_DIRS and
                not path.name.startswith('.') and
                path.is_dir()
            )
        except ValueError:
            return False
    
    def add_tree_level(path: Path, prefix: str = "", depth: int = 0):
        """Recursively build tree structure."""
        if depth > max_depth:
            try:
                if any(should_include_dir(p) for p in path.iterdir() if p.is_dir()) if path.exists() else False:
                    tree_lines.append(prefix + "|-- ...")
                return
            except (PermissionError, OSError):
                return
        
        try:
            items = sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
        except (PermissionError, OSError):
            return  # Skip inaccessible directories
        
        # Filter items
        dirs = [item for item in items if should_include_dir(item)]
        
        # Important files to show in tree
        important_files = [
            item for item in items 
            if item.is_file() and (
                item.name in ['README.md', 'package.json', 'requirements.txt', 
                             'Cargo.toml', 'go.mod', 'pom.xml', 'build.gradle',
                             'setup.py', 'pyproject.toml', 'Makefile']
            ) and (
                not item.relative_to(root_path).parts or 
                item.relative_to(root_path).parts[0] in ALLOWED_DIRS
            )
        ]
        
        all_items = dirs + important_files
        
        for i, item in enumerate(all_items):
            is_last = i == len(all_items) - 1
            current_prefix = "`-- " if is_last else "|-- "
            
            name = item.name
            if item.is_dir():
                name += "/"
                # Add file count for directories
                try:
                    file_count = sum(1 for f in item.rglob('*') if f.is_file() and f.suffix in CODE_EXTENSIONS and
                                    (not f.relative_to(root_path).parts or f.relative_to(root_path).parts[0] in ALLOWED_DIRS))
                    if file_count > 0:
                        name += f" ({file_count} files)"
                except (PermissionError, OSError):
                    pass
            
            tree_lines.append(prefix + current_prefix + name)
            
            if item.is_dir():
                next_prefix = prefix + ("    " if is_last else "|   ")
                add_tree_level(item, next_prefix, depth + 1)
    
    # Start with root
    tree_lines.append(".")
    add_tree_level(root_path, "")
    return tree_lines


def build_index(root_dir: str) -> Tuple[Dict, int]:
    """Build the enhanced index with architectural awareness."""
    root = Path(root_dir).resolve()
    index = {
        'indexed_at': datetime.now().isoformat(),
        'root': str(root).replace('\\', '/'),
        'project_structure': {
            'type': 'tree',
            'root': '.',
            'tree': []
        },
        'documentation_map': {},
        'directory_purposes': {},
        'stats': {
            'total_files': 0,
            'total_directories': 0,
            'fully_parsed': {},
            'listed_only': {},
            'markdown_files': 0
        },
        'files': {},
        'dependency_graph': {}
    }
    
    print("📊 Building directory tree...")
    index['project_structure']['tree'] = generate_tree_structure(root)
    
    file_count = 0
    dir_count = 0
    skipped_count = 0
    directory_files = {}
    
    print("🔍 Indexing files...")
    try:
        import subprocess
        ignore_patterns = ' '.join(f'--iglob "!**/{d}"' for d in IGNORE_DIRS)
        rg_cmd = f'rg --files {ignore_patterns}'
        rg_output = subprocess.run(rg_cmd, cwd=str(root), capture_output=True, text=True, shell=True)
        if rg_output.returncode == 0:
            file_paths = [root / p for p in rg_output.stdout.splitlines()]
            print(f"Ripgrep found {len(file_paths)} files")
        else:
            print(f"Ripgrep failed: {rg_output.stderr}")
            raise Exception("Ripgrep failed")
    except Exception as e:
        print(f"Ripgrep error: {e}, falling back to rglob")
        file_paths = list(root.rglob('*'))
        print(f"Rglob found {len(file_paths)} files")
    
    for file_path in file_paths:
        file_path = Path(file_path).resolve()
        if file_count >= MAX_FILES:
            print(f"⚠️ Stopping at {MAX_FILES} files (project too large)")
            break
            
        if file_path.is_dir():
            if not any(part in IGNORE_DIRS for part in file_path.parts):
                dir_count += 1
                directory_files[file_path] = []
            continue
            
        if not file_path.is_file():
            #print(f"Skipping {file_path}: Not a file (exists: {file_path.exists()})")
            continue
            
        if not should_index_file(file_path, root):
            skipped_count += 1
            continue
        
        parent_dir = file_path.parent.resolve()
        if parent_dir not in directory_files:
            directory_files[parent_dir] = []
        directory_files[parent_dir].append(file_path.name)
        
        try:
            rel_path = file_path.relative_to(root)
            rel_path_str = str(rel_path).replace('\\', '/')
        except ValueError:
            print(f"Skipping {file_path}: Not under project root")
            continue
        print(f"Indexing file: {rel_path_str}")
        
        if file_path.suffix in MARKDOWN_EXTENSIONS:
            doc_structure = extract_markdown_structure(file_path)
            if doc_structure['sections'] or doc_structure['architecture_hints']:
                index['documentation_map'][rel_path_str] = doc_structure
                index['stats']['markdown_files'] += 1
                #print(f"Added to documentation_map: {rel_path_str}")
            #else:
            #    print(f"Skipped Markdown {rel_path_str}: No sections or hints")
            continue
        
        language = get_language_name(file_path.suffix)
        file_info = {
            'language': language,
            'parsed': False
        }
        
        file_purpose = infer_file_purpose(file_path)
        if file_purpose:
            file_info['purpose'] = file_purpose
        
        if file_path.suffix in PARSEABLE_LANGUAGES:
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                if file_path.suffix == '.py':
                    extracted = extract_python_signatures(content)
                elif file_path.suffix in {'.js', '.ts', '.jsx', '.tsx'}:
                    extracted = extract_javascript_signatures(content)
                elif file_path.suffix in {'.sh', '.bash'}:
                    extracted = extract_shell_signatures(content)
                else:
                    extracted = {'functions': {}, 'classes': {}}
                
                if extracted['functions'] or extracted['classes']:
                    file_info.update(extracted)
                    file_info['parsed'] = True
                    lang_key = PARSEABLE_LANGUAGES[file_path.suffix]
                    index['stats']['fully_parsed'][lang_key] = \
                        index['stats']['fully_parsed'].get(lang_key, 0) + 1
                    #print(f"Added to files (parsed: True): {rel_path_str}")
                else:
                    index['stats']['listed_only'][language] = \
                        index['stats']['listed_only'].get(language, 0) + 1
                    #print(f"Added to files (parsed: False, no functions/classes): {rel_path_str}")
            except Exception as e:
                print(f"Error parsing {rel_path_str}: {e}")
                index['stats']['listed_only'][language] = \
                    index['stats']['listed_only'].get(language, 0) + 1
                #print(f"Added to files (parsed: False, error): {rel_path_str}")
        else:
            index['stats']['listed_only'][language] = \
                index['stats']['listed_only'].get(language, 0) + 1
            #print(f"Added to files (listed only): {rel_path_str}")
        
        index['files'][rel_path_str] = file_info
        file_count += 1
        
        if file_count % 100 == 0:
            print(f"  Indexed {file_count} files...")
    
    print("🏗️ Analyzing directory purposes...")
    for dir_path, files in directory_files.items():
        if files:
            purpose = infer_directory_purpose(dir_path, files)
            if purpose:
                try:
                    rel_dir = dir_path.relative_to(root)
                    rel_dir_str = str(rel_dir).replace('\\', '/')
                    if rel_dir_str != '.':
                        index['directory_purposes'][rel_dir_str] = purpose
                except ValueError:
                    print(f"Skipping directory {dir_path}: Not under project root")
    
    index['stats']['total_files'] = file_count
    index['stats']['total_directories'] = len(directory_files)
    
    print("🔗 Building dependency graph...")
    dependency_graph = {}
    
    for file_path, file_info in index['files'].items():
        if file_info.get('imports'):
            file_dir = Path(file_path).parent
            dependencies = []
            
            for imp in file_info['imports']:
                if imp.startswith('.'):
                    if imp.startswith('./'):
                        resolved = str(file_dir / imp[2:]).replace('\\', '/')
                    elif imp.startswith('../'):
                        parts = imp.split('/')
                        up_levels = len([p for p in parts if p == '..'])
                        target_dir = file_dir
                        for _ in range(up_levels):
                            target_dir = target_dir.parent
                        remaining = '/'.join(p for p in parts if p != '..')
                        resolved = str(target_dir / remaining).replace('\\', '/') if remaining else str(target_dir).replace('\\', '/')
                    else:
                        resolved = str(file_dir).replace('\\', '/')
                    
                    for ext in ['.py', '.js', '.ts', '.jsx', '.tsx', '']:
                        potential_file = resolved + ext
                        if potential_file in index['files'] or potential_file.replace('\\', '/') in index['files']:
                            dependencies.append(potential_file.replace('\\', '/'))
                            break
                else:
                    dependencies.append(imp)
            
            if dependencies:
                dependency_graph[file_path] = dependencies
    
    if dependency_graph:
        index['dependency_graph'] = dependency_graph
    
    print("📞 Building call graph...")
    call_graph = {}
    called_by_graph = {}
    
    for file_path, file_info in index['files'].items():
        if not isinstance(file_info, dict):
            continue
            
        if 'functions' in file_info:
            for func_name, func_data in file_info['functions'].items():
                if isinstance(func_data, dict) and 'calls' in func_data:
                    full_func_name = f"{file_path}:{func_name}"
                    call_graph[full_func_name] = func_data['calls']
                    
                    for called in func_data['calls']:
                        if called not in called_by_graph:
                            called_by_graph[called] = []
                        called_by_graph[called].append(func_name)
        
        if 'classes' in file_info:
            for class_name, class_data in file_info['classes'].items():
                if isinstance(class_data, dict) and 'methods' in class_data:
                    for method_name, method_data in class_data['methods'].items():
                        if isinstance(method_data, dict) and 'calls' in method_data:
                            full_method_name = f"{file_path}:{class_name}.{method_name}"
                            call_graph[full_method_name] = method_data['calls']
                            
                            for called in method_data['calls']:
                                if called not in called_by_graph:
                                    called_by_graph[called] = []
                                called_by_graph[called].append(f"{class_name}.{method_name}")
    
    for file_path, file_info in index['files'].items():
        if not isinstance(file_info, dict):
            continue
            
        if 'functions' in file_info:
            for func_name, func_data in file_info['functions'].items():
                if func_name in called_by_graph:
                    if isinstance(func_data, dict):
                        func_data['called_by'] = called_by_graph[func_name]
                    else:
                        index['files'][file_path]['functions'][func_name] = {
                            'signature': func_data,
                            'called_by': called_by_graph[func_name]
                        }
        
        if 'classes' in file_info:
            for class_name, class_data in file_info['classes'].items():
                if isinstance(class_data, dict) and 'methods' in class_data:
                    for method_name, method_data in class_data['methods'].items():
                        full_name = f"{class_name}.{method_name}"
                        if method_name in called_by_graph or full_name in called_by_graph:
                            callers = called_by_graph.get(method_name, []) + called_by_graph.get(full_name, [])
                            if callers:
                                if isinstance(method_data, dict):
                                    type(method_data)
                                else:
                                    class_data['methods'][method_name] = {
                                        'signature': method_data,
                                        'called_by': list(set(callers))
                                    }
    
    index['stats']['total_files'] = file_count
    index['stats']['total_directories'] = len(directory_files)
    index['staleness_check'] = datetime.now().timestamp() - 7 * 24 * 60 * 60
    
    return index, skipped_count

def compress_index_if_needed(index: Dict) -> Dict:
    """Compress index if it exceeds size limit."""
    index_json = json.dumps(index, indent=2)
    
    if len(index_json) <= MAX_INDEX_SIZE:
        return index
    
    print(f"⚠️  Index too large ({len(index_json)} bytes), compressing...")
    
    # First, reduce tree depth
    if len(index['project_structure']['tree']) > 100:
        index['project_structure']['tree'] = index['project_structure']['tree'][:100]
        index['project_structure']['tree'].append("... (truncated)")
    
    # If still too large, remove some listed-only files
    while len(json.dumps(index, indent=2)) > MAX_INDEX_SIZE and index['files']:
        # Find and remove a listed-only file
        for path, info in list(index['files'].items()):
            if not info.get('parsed', False):
                del index['files'][path]
                break
    
    return index


def print_summary(index: Dict, skipped_count: int):
    """Print a helpful summary of what was indexed."""
    stats = index['stats']
    
    # Add warning if no files were found
    if stats['total_files'] == 0:
        print("\n⚠️  WARNING: No files were indexed!")
        print("   This might mean:")
        print("   • You're in the wrong directory")
        print("   • All files are being ignored (check .gitignore)")
        print("   • The project has no supported file types")
        print(f"\n   Current directory: {os.getcwd()}")
        print("   Try running from your project root directory.")
        return
    
    print(f"\n📊 Project Analysis Complete:")
    print(f"   📁 {stats['total_directories']} directories indexed")
    print(f"   📄 {stats['total_files']} code files found")
    print(f"   📝 {stats['markdown_files']} documentation files analyzed")
    
    # Show fully parsed languages
    if stats['fully_parsed']:
        print("\n✅ Languages with full parsing:")
        for lang, count in sorted(stats['fully_parsed'].items()):
            print(f"   • {count} {lang.capitalize()} files (with signatures)")
    
    # Show listed-only languages
    if stats['listed_only']:
        print("\n📋 Languages listed only:")
        for lang, count in sorted(stats['listed_only'].items()):
            print(f"   • {count} {lang.capitalize()} files")
    
    # Show documentation insights
    if index['documentation_map']:
        print(f"\n📚 Documentation insights:")
        for doc_file, info in list(index['documentation_map'].items())[:3]:
            print(f"   • {doc_file}: {len(info['sections'])} sections")
    
    # Show directory purposes
    if index['directory_purposes']:
        print(f"\n🏗️  Directory structure:")
        for dir_path, purpose in list(index['directory_purposes'].items())[:5]:
            print(f"   • {dir_path}/: {purpose}")
    
    if skipped_count > 0:
        print(f"\n   (Skipped {skipped_count} files in ignored directories)")


def main():
    """Run the enhanced indexer."""
    print("🚀 Building Project Index...")
    print("   Analyzing project structure and documentation...")
    
    # Build index for project root (two levels up from scripts/index/)
    index, skipped_count = build_index('../..')
    
    # Compress if needed
    index = compress_index_if_needed(index)
    
    # Save to PROJECT_INDEX.json in current directory
    #output_path = Path('PROJECT_INDEX.json')
    output_path = Path('../../docs/new/PROJECT_INDEX.json')
    output_path.write_text(json.dumps(index, indent=2))
    
    # Print summary
    print_summary(index, skipped_count)
    
    print(f"\n💾 Saved to: {output_path}")
    print("\n✨ Claude now has architectural awareness of your project!")
    print("   • Knows WHERE to place new code")
    print("   • Understands project structure")
    print("   • Can navigate documentation")
    print("\n📌 Benefits:")
    print("   • Prevents code duplication")
    print("   • Ensures proper file placement")
    print("   • Maintains architectural consistency")


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--version':
        print(f"PROJECT_INDEX v{__version__}")
        sys.exit(0)
    main()