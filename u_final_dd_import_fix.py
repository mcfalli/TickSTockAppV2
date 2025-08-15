#!/usr/bin/env python3
"""
Fix the final double dot syntax error and any remaining issues
"""

import os
from pathlib import Path

class FinalSyntaxFixer:
    def __init__(self, dest_dir: str = r"C:\Users\McDude\TickStockAppV2"):
        self.dest_dir = Path(dest_dir)
        
    def fix_highlow_detector(self):
        """Fix the specific syntax error in highlow_detector.py"""
        highlow_file = self.dest_dir / "src" / "processing" / "detectors" / "highlow_detector.py"
        
        print(f"Fixing syntax error in highlow_detector.py...")
        
        try:
            content = highlow_file.read_text(encoding='utf-8')
            
            # Fix the double dot issue - the engine is in the engines subdirectory
            content = content.replace(
                "from src.processing.detectors.event_detection_engines import",
                "from src.processing.detectors.highlow_detector import"
            )
            
            # Also check for similar patterns
            content = content.replace(
                "from src.processing.detectors.", 
                "from src.processing.detectors."
            )
            
            highlow_file.write_text(content, encoding='utf-8')
            print(f"✓ Fixed syntax error in highlow_detector.py")
            
        except Exception as e:
            print(f"✗ Error fixing highlow_detector.py: {e}")
    
    def check_all_double_dots(self):
        """Check all files for double dot issues"""
        print("\nChecking all files for double dot syntax errors...")
        
        issues_found = []
        
        for py_file in self.dest_dir.rglob("*.py"):
            if '__pycache__' in str(py_file) or 'venv' in str(py_file):
                continue
            
            try:
                content = py_file.read_text(encoding='utf-8')
                lines = content.split('\n')
                
                for i, line in enumerate(lines, 1):
                    if '..' in line and ('from ' in line or 'import ' in line):
                        # Skip valid relative imports
                        if not line.strip().startswith('from ..'):
                            if 'detectors.' in line or 'services.' in line or 'websocket.' in line:
                                issues_found.append((py_file, i, line.strip()))
                                print(f"Found issue in {py_file.relative_to(self.dest_dir)}:{i}")
                                
                                # Auto-fix
                                fixed_line = line.replace('..', '.')
                                lines[i-1] = fixed_line
                                
                                # Write back
                                fixed_content = '\n'.join(lines)
                                py_file.write_text(fixed_content, encoding='utf-8')
                                print(f"  ✓ Fixed: {line.strip()}")
                                
            except Exception as e:
                pass  # Skip files that can't be read
        
        if not issues_found:
            print("  No double dot issues found")
        
        return len(issues_found)
    
    def run_quick_test(self):
        """Quick test to see if imports work"""
        print("\n" + "=" * 60)
        print("Running quick import test...")
        print("=" * 60)
        
        import sys
        sys.path.insert(0, str(self.dest_dir))
        
        try:
            print("Testing MarketDataService import...")
            from src.core.services.market_data_service import MarketDataService
            print("✓ MarketDataService imports successfully!")
            return True
        except SyntaxError as e:
            print(f"✗ Syntax error still present: {e}")
            return False
        except ImportError as e:
            print(f"✗ Import error: {e}")
            return False
    
    def run(self):
        """Run all fixes"""
        print("Final Syntax Error Fixer")
        print("=" * 60)
        
        # Fix the known issue
        self.fix_highlow_detector()
        
        # Check for other issues
        other_issues = self.check_all_double_dots()
        
        # Test
        success = self.run_quick_test()
        
        if success:
            print("\n" + "=" * 60)
            print("🎉 SUCCESS!")
            print("=" * 60)
            print("The critical import is working!")
            print("\nNext steps:")
            print("1. Run full test: python test_migration_success.py")
            print("2. Try the app: python src/app.py")
        else:
            print("\n" + "=" * 60)
            print("⚠️  Import issues remain")
            print("=" * 60)
            print("Check the error messages above for details")


def main():
    fixer = FinalSyntaxFixer()
    fixer.run()
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())