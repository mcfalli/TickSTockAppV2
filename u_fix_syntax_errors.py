
#!/usr/bin/env python3
"""
Fix syntax errors in import statements
"""

import os
from pathlib import Path

class SyntaxErrorFixer:
    def __init__(self, dest_dir: str = r"C:\Users\McDude\TickStockAppV2"):
        self.dest_dir = Path(dest_dir)
        self.fixes_applied = []
        
    def fix_double_dots(self):
        """Fix double dots in import statements"""
        print("Fixing double dot syntax errors...")
        print("=" * 60)
        
        # Target file with the syntax error
        transport_models = self.dest_dir / "src" / "presentation" / "converters" / "transport_models.py"
        
        if transport_models.exists():
            try:
                content = transport_models.read_text(encoding='utf-8')
                original = content
                
                # Fix the double dot issue
                content = content.replace(
                    "from src.core.domain.events.base import",
                    "from src.core.domain.events.base import"
                )
                
                # Also check for other potential double dot issues
                content = content.replace("converters..", "converters.")
                content = content.replace("/../", "/")
                content = content.replace("\\..", "\\")
                
                if content != original:
                    transport_models.write_text(content, encoding='utf-8')
                    print(f"✓ Fixed: {transport_models.relative_to(self.dest_dir)}")
                    self.fixes_applied.append(str(transport_models.relative_to(self.dest_dir)))
                else:
                    print(f"⚠ No changes needed in transport_models.py")
                    
            except Exception as e:
                print(f"✗ Error fixing transport_models.py: {e}")
        else:
            print(f"✗ File not found: transport_models.py")
    
    def scan_for_double_dots(self):
        """Scan all Python files for double dot issues"""
        print("\nScanning for other double dot issues...")
        print("-" * 40)
        
        issues_found = []
        
        for py_file in self.dest_dir.rglob("*.py"):
            if '__pycache__' in str(py_file) or 'venv' in str(py_file):
                continue
                
            try:
                content = py_file.read_text(encoding='utf-8')
                
                # Check for various double dot patterns
                if '..' in content and ('from ' in content or 'import ' in content):
                    lines = content.split('\n')
                    for i, line in enumerate(lines, 1):
                        if ('from ' in line or 'import ' in line) and '..' in line:
                            # Skip relative imports (they're supposed to have ..)
                            if not (line.strip().startswith('from ..') or 'from ..' in line):
                                if 'converters..' in line or 'services.' in line or 'domain..' in line:
                                    issues_found.append((py_file, i, line.strip()))
                                    print(f"Found issue in {py_file.relative_to(self.dest_dir)}:{i}")
                                    print(f"  Line: {line.strip()}")
                                    
                                    # Auto-fix the issue
                                    fixed_line = line.replace('..', '.')
                                    lines[i-1] = fixed_line
                                    
                                    # Write back the fixed content
                                    fixed_content = '\n'.join(lines)
                                    py_file.write_text(fixed_content, encoding='utf-8')
                                    print(f"  ✓ Fixed: {line.strip()} -> {fixed_line.strip()}")
                                    self.fixes_applied.append(str(py_file.relative_to(self.dest_dir)))
                                    
            except Exception as e:
                print(f"Error scanning {py_file}: {e}")
        
        if not issues_found:
            print("No double dot issues found in other files")
        
        return issues_found
    
    def create_quick_test(self):
        """Create a quick test to verify the fix"""
        test_script = self.dest_dir / "quick_test.py"
        
        content = '''#!/usr/bin/env python3
"""Quick test after syntax fix"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("Quick Import Test After Syntax Fix")
print("=" * 60)

try:
    # Test the specific import that was failing
    from src.presentation.converters.transport_models import StockData
    print("✓ transport_models import works!")
    
    # Test MarketDataService
    from src.core.services.market_data_service import MarketDataService
    print("✓ MarketDataService import works!")
    
    # Test WebSocketManager
    from src.presentation.websocket.manager import WebSocketManager
    print("✓ WebSocketManager import works!")
    
    print("\\n🎉 All critical imports working!")
    
except ImportError as e:
    print(f"✗ Import still failing: {e}")
except SyntaxError as e:
    print(f"✗ Syntax error still present: {e}")
'''
        
        try:
            test_script.write_text(content, encoding='utf-8')
            print(f"\n✓ Created quick_test.py")
            return True
        except Exception as e:
            print(f"\n✗ Error creating test script: {e}")
            return False
    
    def run_all_fixes(self):
        """Run all fixes"""
        print("Syntax Error Fixer")
        print("=" * 60)
        
        # Fix the known issue
        self.fix_double_dots()
        
        # Scan for other issues
        self.scan_for_double_dots()
        
        # Create test script
        self.create_quick_test()
        
        print("\n" + "=" * 60)
        print("FIXES SUMMARY:")
        print("=" * 60)
        if self.fixes_applied:
            for fix in set(self.fixes_applied):
                print(f"  ✓ {fix}")
        else:
            print("  No fixes were needed")
        
        print("\n" + "=" * 60)
        print("NEXT STEPS:")
        print("=" * 60)
        print("1. Run quick test:")
        print("   python quick_test.py")
        print("\n2. If that works, run comprehensive test:")
        print("   python test_all_imports.py")
        print("\n3. If all passes, try the app:")
        print("   python src/app.py")


def main():
    """Main execution"""
    fixer = SyntaxErrorFixer()
    fixer.run_all_fixes()
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())