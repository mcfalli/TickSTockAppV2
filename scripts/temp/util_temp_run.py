#!/usr/bin/env python3
"""
Find any remaining 'from src.infrastructure.database import model' or 'from src.infrastructure.database import' statements
"""

import os
import re
from pathlib import Path

def find_model_imports():
    """Find all remaining references to 'model' module"""
    
    # Patterns to find
    patterns = [
        (re.compile(r'from src.infrastructure.database import', re.MULTILINE), 'from src.infrastructure.database import'),
        (re.compile(r'from src.infrastructure.database import model(?:\s|$)', re.MULTILINE), 'from src.infrastructure.database import model'),
        (re.compile(r'from model\.', re.MULTILINE), 'from src.infrastructure.database.models.base.base.'),
    ]
    
    # Skip these directories
    skip_dirs = {'.git', '__pycache__', 'venv', 'env', '.venv', 'migrations'}
    
    found_imports = []
    
    print("=" * 80)
    print("SEARCHING FOR REMAINING 'model' IMPORTS")
    print("=" * 80)
    print()
    
    for root, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        
        for file in files:
            if file.endswith('.py'):
                filepath = Path(root) / file
                
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        lines = content.splitlines()
                    
                    for pattern, pattern_name in patterns:
                        matches = list(pattern.finditer(content))
                        if matches:
                            relative_path = os.path.relpath(filepath, '.')
                            
                            for match in matches:
                                # Find line number
                                line_num = content[:match.start()].count('\n') + 1
                                line_content = lines[line_num - 1].strip()
                                
                                found_imports.append((relative_path, line_num, line_content))
                
                except Exception as e:
                    pass
    
    if found_imports:
        print(f"Found {len(found_imports)} import(s) to fix:\n")
        
        # Group by file
        by_file = {}
        for filepath, line_num, line_content in found_imports:
            if filepath not in by_file:
                by_file[filepath] = []
            by_file[filepath].append((line_num, line_content))
        
        for filepath, imports in sorted(by_file.items()):
            print(f"📄 {filepath}")
            for line_num, line_content in imports:
                print(f"   Line {line_num}: {line_content}")
            print()
    else:
        print("✅ No remaining 'model' imports found!")
    
    return found_imports

def fix_imports_automatically():
    """Offer to fix the imports automatically"""
    
    found = find_model_imports()
    
    if not found:
        return
    
    print("-" * 80)
    response = input("\nFix these imports automatically? (y/n): ")
    
    if response.lower() != 'y':
        return
    
    # Group by file
    by_file = {}
    for filepath, line_num, line_content in found:
        if filepath not in by_file:
            by_file[filepath] = []
        by_file[filepath].append((line_num, line_content))
    
    files_fixed = 0
    
    for filepath, imports in by_file.items():
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original = content
            
            # Apply fixes
            content = re.sub(r'from src.infrastructure.database import', 'from src.infrastructure.database import', content)
            content = re.sub(r'from src.infrastructure.database import model\b', 'from src.infrastructure.database from src.infrastructure.database import model', content)
            content = re.sub(r'from model\.', 'from src.infrastructure.database.models.base.base.', content)
            
            if content != original:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"✅ Fixed {filepath}")
                files_fixed += 1
        
        except Exception as e:
            print(f"❌ Error fixing {filepath}: {e}")
    
    if files_fixed > 0:
        print(f"\n✅ Fixed {files_fixed} file(s)")
        print("\nTry running the app again:")
        print("  python app.py")

def main():
    fix_imports_automatically()

if __name__ == "__main__":
    main()