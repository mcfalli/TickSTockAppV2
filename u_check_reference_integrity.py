#!/usr/bin/env python3
"""
Master script to fix all reference integrity issues
"""

import subprocess
import sys
from pathlib import Path

def run_all_fixes():
    """Run all fix scripts in sequence."""
    print("=" * 80)
    print("TICKSTOCK V2 - REFERENCE INTEGRITY AUTO-FIX")
    print("=" * 80)
    
    base_path = Path(r"C:\Users\McDude\TickStockAppV2")
    
    # Save the individual fix scripts first
    scripts = {
        "u_fix_syntax_errors.py": fix_syntax_errors_code,
        "u_fix_orphaned_files.py": fix_orphaned_files_code,
        "u_fix_websocket_handlers.py": fix_websocket_handlers_code
    }
    
    print("\n📝 Creating fix scripts...")
    for filename, code in scripts.items():
        script_path = base_path / filename
        script_path.write_text(code, encoding='utf-8')
        print(f"  ✅ Created {filename}")
    
    # Run each fix script
    print("\n🔧 Running fixes...")
    for filename in scripts.keys():
        print(f"\n--- Running {filename} ---")
        try:
            result = subprocess.run(
                [sys.executable, str(base_path / filename)],
                capture_output=True,
                text=True,
                cwd=base_path
            )
            print(result.stdout)
            if result.stderr:
                print(f"Errors: {result.stderr}")
        except Exception as e:
            print(f"  ❌ Failed to run {filename}: {e}")
    
    # Re-run the integrity check
    print("\n🔍 Re-running integrity check...")
    try:
        result = subprocess.run(
            [sys.executable, "u_check_reference_integrity.py"],
            capture_output=True,
            text=True,
            cwd=base_path
        )
        
        # Parse the new score from output
        for line in result.stdout.split('\n'):
            if 'REFERENCE INTEGRITY SCORE:' in line:
                print(f"\n{line}")
                break
                
    except Exception as e:
        print(f"  ❌ Failed to run integrity check: {e}")
    
    print("\n" + "=" * 80)
    print("AUTO-FIX COMPLETE!")
    print("=" * 80)
    print("\nNext steps:")
    print("1. Run 'python u_check_reference_integrity.py' to verify fixes")
    print("2. Test the application: 'python src/app.py'")
    print("3. Run unit tests: 'pytest tests/'")

if __name__ == "__main__":
    # Include the fix script code here (abbreviated for space)
    fix_syntax_errors_code = open('u_fix_syntax_errors.py').read()
    fix_orphaned_files_code = open('u_fix_orphaned_files.py').read()
    fix_websocket_handlers_code = open('u_fix_websocket_handlers.py').read()
    
    run_all_fixes()