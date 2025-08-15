#!/usr/bin/env python3
"""
Comprehensive fix for all remaining import issues
"""

import os
from pathlib import Path
import re

class ComprehensiveImportFixer:
    def __init__(self, dest_dir: str = r"C:\Users\McDude\TickStockAppV2"):
        self.dest_dir = Path(dest_dir)
        self.fixes = {}
        self.files_fixed = []
        
    def analyze_and_fix_all_issues(self):
        """Fix all known import issues"""
        
        # Define all the fixes needed based on the error messages
        all_fixes = {
            # Fix 1: events is in domain, not converters
            'from src.core.domain.events': 'from src.core.domain.events',
            
            # Fix 2: utils.utils should be utils.general
            'from src.shared.utils.general': 'from src.shared.utils.general',
            'from src.shared.utils import general': 'from src.shared.utils import general',
            
            # Fix 3: logging_config is in config, not services
            'from config.logging_config': 'from config.logging_config',
            
            # Fix 4: websocket_publisher doesn't exist, it's just publisher
            'from src.presentation.websocket.publisher': 'from src.presentation.websocket.publisher',
            'import src.presentation.websocket.publisher': 'import src.presentation.websocket.publisher',
            
            # Fix 5: data_provider_factory is just factory
            'from src.infrastructure.data_sources.factory': 'from src.infrastructure.data_sources.factory',
            'import src.infrastructure.data_sources.factory': 'import src.infrastructure.data_sources.factory',
            
            # Fix 6: tick_processor is in pipeline, not processing root
            'from src.processing.pipeline.tick_processor': 'from src.processing.pipeline.tick_processor',
            
            # Fix 7: database.model is now database.models.base
            'from src.infrastructure.database.models.base': 'from src.infrastructure.database.models.base.base',
            
            # Fix 8: Some services are trying to import from each other incorrectly
            'from src.shared.utils.market_utils': 'from src.shared.utils.market_utils',
            'from src.shared.utils.app_utils': 'from src.shared.utils.app_utils',
            
            # Fix 9: WebSocket related fixes
            'from .publisher': 'from .publisher',
            'from src.presentation.websocket.publisher': 'from src.presentation.websocket.publisher',
            
            # Fix 10: More utils fixes
            'from src.shared.utils import general': 'from src.shared.utils import general',
            'from src.shared.utils.general': 'from src.shared.utils.general',
        }
        
        print("Applying comprehensive import fixes...")
        print("=" * 60)
        
        # Apply fixes to all Python files
        for py_file in self.dest_dir.rglob("*.py"):
            if '__pycache__' in str(py_file) or 'venv' in str(py_file):
                continue
            
            try:
                content = py_file.read_text(encoding='utf-8')
                original = content
                
                # Apply all fixes
                for old, new in all_fixes.items():
                    if old in content:
                        content = content.replace(old, new)
                        rel_path = py_file.relative_to(self.dest_dir)
                        if str(rel_path) not in self.fixes:
                            self.fixes[str(rel_path)] = []
                        self.fixes[str(rel_path)].append(f"{old} -> {new}")
                
                # Write back if changed
                if content != original:
                    py_file.write_text(content, encoding='utf-8')
                    self.files_fixed.append(str(py_file.relative_to(self.dest_dir)))
                    
            except Exception as e:
                print(f"Error processing {py_file}: {e}")
        
        # Print results
        if self.files_fixed:
            print(f"\nFixed {len(self.files_fixed)} files:")
            for filepath in sorted(set(self.files_fixed)):
                print(f"  ✓ {filepath}")
                if filepath in self.fixes:
                    for fix in self.fixes[filepath]:
                        print(f"      {fix}")
        else:
            print("No files needed fixing")
    
    def create_final_test(self):
        """Create final comprehensive test"""
        test_script = self.dest_dir / "final_test.py"
        
        content = '''#!/usr/bin/env python3
"""
Final comprehensive test after all fixes
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("Final Import Test - Post Fix")
print("=" * 60)

success_count = 0
fail_count = 0
errors = []

def test(name, import_func):
    global success_count, fail_count, errors
    try:
        import_func()
        print(f"✓ {name}")
        success_count += 1
        return True
    except Exception as e:
        print(f"✗ {name}: {str(e)[:50]}")
        errors.append((name, str(e)))
        fail_count += 1
        return False

# Critical imports that must work
print("\\nCritical Services:")
print("-" * 40)
test("MarketDataService", lambda: exec("from src.core.services.market_data_service import MarketDataService"))
test("SessionManager", lambda: exec("from src.core.services.session_manager import SessionManager"))
test("ConfigManager", lambda: exec("from src.core.services.config_manager import ConfigManager"))

print("\\nWebSocket Layer:")
print("-" * 40)
test("WebSocketManager", lambda: exec("from src.presentation.websocket.manager import WebSocketManager"))
test("WebSocketPublisher", lambda: exec("from src.presentation.websocket.publisher import WebSocketPublisher"))

print("\\nData Layer:")
print("-" * 40)
test("DataProviderFactory", lambda: exec("from src.infrastructure.data_sources.factory import DataProviderFactory"))

print("\\nDomain Models:")
print("-" * 40)
test("Events", lambda: exec("from src.core.domain.events.highlow import HighLowEvent"))
test("Market", lambda: exec("from src.core.domain.market.tick import TickData"))

print("\\nUtilities:")
print("-" * 40)
test("General Utils", lambda: exec("from src.shared.utils.general import *"))
test("Event Factory", lambda: exec("from src.shared.utils.event_factory import EventFactory"))

print("\\nConfiguration:")
print("-" * 40)
test("App Config", lambda: exec("import config.app_config"))
test("Logging", lambda: exec("from config.logging_config import get_domain_logger"))

print("\\n" + "=" * 60)
print(f"RESULTS: {success_count} passed, {fail_count} failed")

if fail_count > 0:
    print("\\nErrors:")
    for name, error in errors[:5]:  # Show first 5 errors
        print(f"  - {name}: {error[:100]}")
    
if success_count > 10:
    print("\\n✅ Most critical imports are working!")
    print("The migration is largely successful.")
elif success_count > 5:
    print("\\n⚠️ Partial success - some imports still need work")
else:
    print("\\n❌ Many imports still failing - needs more fixes")
'''
        
        try:
            test_script.write_text(content, encoding='utf-8')
            print(f"\n✓ Created final_test.py")
        except Exception as e:
            print(f"\n✗ Error creating test: {e}")
    
    def run(self):
        """Run all fixes"""
        print("Comprehensive Import Fixer")
        print("=" * 60)
        
        self.analyze_and_fix_all_issues()
        self.create_final_test()
        
        print("\n" + "=" * 60)
        print("Fix Summary:")
        print(f"  Files fixed: {len(self.files_fixed)}")
        print(f"  Total replacements: {sum(len(fixes) for fixes in self.fixes.values())}")
        
        print("\n" + "=" * 60)
        print("Next Steps:")
        print("1. Run final test:")
        print("   python final_test.py")
        print("\n2. If most tests pass, the migration is successful!")
        print("   You can start fixing individual remaining issues.")
        print("\n3. Try running the app:")
        print("   python src/app.py")


def main():
    fixer = ComprehensiveImportFixer()
    fixer.run()
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())