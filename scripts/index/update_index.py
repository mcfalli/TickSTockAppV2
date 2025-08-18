#!/usr/bin/env python3
"""
PostToolUse hook for PROJECT_INDEX.json incremental updates
This is the DEPLOYMENT VERSION to be placed in ~/.claude/scripts/

Key differences from update_index.py:
- Self-contained with special import handling
- Searches for index_utils.py in project directories
- Falls back to minimal functionality if dependencies not found
- Designed to work from any location
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime

# Try to find and import index_utils from the project or system location
def find_index_utils():
    """Find index_utils.py in the project directory or system location."""
    current_dir = Path(os.getcwd())
    
    # Search for index_utils.py in scripts/index/
    utils_path = current_dir / 'index_utils.py'
    if utils_path.exists():
        return True
    
    # Try project root's scripts/index/
    project_utils_path = current_dir.parent / 'scripts' / 'index' / 'index_utils.py'
    if project_utils_path.exists():
        sys.path.insert(0, str(project_utils_path.parent))
        return True
    
    # Try system location
    system_utils_path = Path.home() / '.claude-code-project-index' / 'scripts' / 'index_utils.py'
    if system_utils_path.exists():
        sys.path.insert(0, str(system_utils_path.parent))
        return True
    
    return False

# Import utilities if found, otherwise define minimal versions
if find_index_utils():
    from index_utils import (
        PARSEABLE_LANGUAGES, MARKDOWN_EXTENSIONS,
        extract_python_signatures, extract_javascript_signatures,
        extract_shell_signatures, extract_markdown_structure, infer_file_purpose
    )
else:
    # Minimal definitions if utils not found
    PARSEABLE_LANGUAGES = {
        '.py': 'python',
        '.js': 'javascript', 
        '.ts': 'typescript',
        '.jsx': 'javascript',
        '.tsx': 'typescript'
    }
    MARKDOWN_EXTENSIONS = {'.md', '.markdown', '.rst'}
    
    # Print warning
    print("Warning: index_utils.py not found. Using minimal update functionality.", file=sys.stderr)


def update_file_in_index(index_path, file_path, project_root):
    """Update a single file's entry in the enhanced index."""
    try:
        # Read existing index
        if not os.path.exists(index_path):
            return
            
        with open(index_path, 'r') as f:
            index = json.load(f)
        
        # Check if index has required structure
        if 'project_structure' not in index:
            index['needs_full_reindex'] = True
            with open(index_path, 'w') as f:
                json.dump(index, f, indent=2)
            return
        
        # Get relative path from project root
        file_path = Path(file_path).resolve()
        try:
            rel_path = file_path.relative_to(project_root)
            rel_path_str = str(rel_path).replace('\\', '/')
            top_level_dir = rel_path.parts[0] if rel_path.parts else ''
            if top_level_dir and top_level_dir not in ALLOWED_DIRS:
                print(f"Skipping {file_path}: Not in allowed directories {ALLOWED_DIRS}", file=sys.stderr)
                return
        except ValueError:
            print(f"Skipping {file_path}: Not under project root", file=sys.stderr)
            return
        
        # Handle markdown files
        if file_path.suffix in MARKDOWN_EXTENSIONS and 'extract_markdown_structure' in globals():
            try:
                doc_structure = extract_markdown_structure(file_path)
                if doc_structure['sections'] or doc_structure['architecture_hints']:
                    if 'documentation_map' not in index:
                        index['documentation_map'] = {}
                    index['documentation_map'][rel_path_str] = doc_structure
                    
                    if 'stats' in index:
                        index['stats']['markdown_files'] = index['stats'].get('markdown_files', 0) + 1
            except Exception as e:
                print(f"Error processing markdown {rel_path_str}: {e}", file=sys.stderr)
            
            with open(index_path, 'w') as f:
                json.dump(index, f, indent=2)
            return
        
        # Check if file is parseable
        file_ext = file_path.suffix
        if file_ext not in PARSEABLE_LANGUAGES:
            if 'files' not in index:
                index['files'] = {}
            if rel_path_str in index['files']:
                index['files'][rel_path_str]['updated'] = True
            else:
                index['files'][rel_path_str] = {
                    'language': file_ext[1:] if file_ext else 'unknown',
                    'parsed': False
                }
            return
        
        # Read file content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"Error reading {file_path}: {e}", file=sys.stderr)
            return
        
        # Extract signatures if we have the functions
        if 'extract_python_signatures' in globals() and 'extract_javascript_signatures' in globals():
            if file_ext == '.py':
                extracted = extract_python_signatures(content)
            elif file_ext in {'.js', '.ts', '.jsx', '.tsx'}:
                extracted = extract_javascript_signatures(content)
            elif file_ext in {'.sh', '.bash'} and 'extract_shell_signatures' in globals():
                extracted = extract_shell_signatures(content)
            else:
                extracted = {'functions': {}, 'classes': {}}
        else:
            extracted = {'functions': {}, 'classes': {}}
        
        # Update index entry
        if 'files' not in index:
            index['files'] = {}
            
        file_info = {
            'language': PARSEABLE_LANGUAGES[file_ext],
            'parsed': bool(extracted['functions'] or extracted['classes']),
            'functions': extracted['functions'],
            'classes': extracted['classes'],
            'updated_by_hook': True,
            'updated_at': datetime.now().isoformat()
        }
        
        # Add file purpose if we can infer it
        if 'infer_file_purpose' in globals():
            file_purpose = infer_file_purpose(file_path)
            if file_purpose:
                file_info['purpose'] = file_purpose
            
        index['files'][rel_path_str] = file_info
        
        # Write updated index
        with open(index_path, 'w') as f:
            json.dump(index, f, indent=2)
            
        print(f"Updated {rel_path_str} in PROJECT_INDEX.json", file=sys.stderr)
        
    except Exception as e:
        print(f"Error updating index: {e}", file=sys.stderr)


def main():
    """Process PostToolUse hook input and update index."""
    try:
        # Read hook input
        input_data = json.load(sys.stdin)
        
        # Check if this is a file modification tool
        tool_name = input_data.get('tool_name', '')
        if tool_name not in ['Write', 'Edit', 'MultiEdit']:
            return
            
        # Get file path(s)
        tool_input = input_data.get('tool_input', {})
        
        # Find project root by looking for PROJECT_INDEX.json
        current_dir = Path.cwd()
        index_path = None
        project_root = current_dir.parent.parent  # Two levels up from scripts/index/
        
        # Search for PROJECT_INDEX.json
        potential_index = project_root / 'scripts' / 'index' / 'PROJECT_INDEX.json'
        if potential_index.exists():
            index_path = str(potential_index)
        
        if not index_path:
            print("No PROJECT_INDEX.json found", file=sys.stderr)
            return
        
        # Update based on tool type
        if tool_name == 'Write' or tool_name == 'Edit':
            file_path = tool_input.get('file_path')
            if file_path:
                update_file_in_index(index_path, file_path, project_root)
        elif tool_name == 'MultiEdit':
            file_path = tool_input.get('file_path')
            if file_path:
                update_file_in_index(index_path, file_path, project_root)
                
    except Exception as e:
        print(f"Hook error: {e}", file=sys.stderr)

if __name__ == '__main__':
    main()