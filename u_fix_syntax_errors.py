#!/usr/bin/env python3
"""
Fix syntax errors in identified files
"""

import sys
from pathlib import Path
import ast

def fix_syntax_errors():
    """Fix known syntax errors in Python files."""
    base_path = Path(r"C:\Users\McDude\TickStockAppV2")
    
    files_to_check = [
        base_path / "src/infrastructure/data_sources/polygon/api.py",
        base_path / "src/infrastructure/data_sources/synthetic/loader.py", 
        base_path / "src/processing/pipeline/__init__.py"
    ]
    
    print("=" * 60)
    print("FIXING SYNTAX ERRORS")
    print("=" * 60)
    
    for file_path in files_to_check:
        if not file_path.exists():
            print(f"⚠️ File not found: {file_path}")
            continue
            
        print(f"\nChecking: {file_path.name}")
        try:
            content = file_path.read_text(encoding='utf-8')
            
            # Try to parse to find the exact error
            try:
                ast.parse(content)
                print(f"  ✅ No syntax errors found")
            except SyntaxError as e:
                print(f"  ❌ Syntax error at line {e.lineno}: {e.msg}")
                
                # Show the problematic line
                lines = content.split('\n')
                if e.lineno and e.lineno <= len(lines):
                    problem_line = lines[e.lineno - 1]
                    print(f"  Line {e.lineno}: {problem_line.strip()}")
                    
                    # Common fixes
                    fixed = False
                    
                    # Fix 1: Missing colons
                    if 'expected' in str(e.msg).lower() and ':' in str(e.msg):
                        lines[e.lineno - 1] = problem_line.rstrip() + ':'
                        fixed = True
                        print(f"  🔧 Added missing colon")
                    
                    # Fix 2: Incomplete imports
                    elif 'import' in problem_line and problem_line.strip().endswith('import'):
                        lines[e.lineno - 1] = '# ' + problem_line  # Comment out incomplete import
                        fixed = True
                        print(f"  🔧 Commented out incomplete import")
                    
                    # Fix 3: Unclosed brackets/parentheses
                    elif problem_line.count('(') > problem_line.count(')'):
                        lines[e.lineno - 1] = problem_line.rstrip() + ')'
                        fixed = True
                        print(f"  🔧 Added missing closing parenthesis")
                    
                    # Fix 4: Unclosed quotes
                    elif (problem_line.count('"') % 2 != 0 or 
                          problem_line.count("'") % 2 != 0):
                        if problem_line.count('"') % 2 != 0:
                            lines[e.lineno - 1] = problem_line.rstrip() + '"'
                        else:
                            lines[e.lineno - 1] = problem_line.rstrip() + "'"
                        fixed = True
                        print(f"  🔧 Added missing quote")
                    
                    if fixed:
                        # Write the fixed content
                        new_content = '\n'.join(lines)
                        file_path.write_text(new_content, encoding='utf-8')
                        print(f"  ✅ Fix applied")
                        
                        # Verify the fix
                        try:
                            ast.parse(new_content)
                            print(f"  ✅ File now parses correctly!")
                        except SyntaxError as e2:
                            print(f"  ⚠️ Still has errors: {e2.msg} at line {e2.lineno}")
                    else:
                        print(f"  ⚠️ Could not auto-fix, manual intervention needed")
                        
        except Exception as e:
            print(f"  ❌ Error processing file: {e}")
    
    print("\n" + "=" * 60)
    print("Syntax error fixing complete!")
    print("=" * 60)

if __name__ == "__main__":
    fix_syntax_errors()