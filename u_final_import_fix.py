#!/usr/bin/env python3
"""
Final fixes for the last remaining import issues
"""

import os
from pathlib import Path

class FinalImportFixes:
    def __init__(self, dest_dir: str = r"C:\Users\McDude\TickStockAppV2"):
        self.dest_dir = Path(dest_dir)
        self.fixes_applied = []
        
    def apply_final_fixes(self):
        """Apply the final set of import fixes"""
        
        final_fixes = {
            # Fix 1: event_detection_manager is just manager
            'from src.processing.detectors.manager': 'from src.processing.detectors.manager',
            'import src.processing.detectors.manager': 'import src.processing.detectors.manager',
            
            # Fix 2: websocket_filter_cache is just filter_cache
            'from src.presentation.websocket.filter_cache': 'from src.presentation.websocket.filter_cache',
            'import src.presentation.websocket.filter_cache': 'import src.presentation.websocket.filter_cache',
            'from .filter_cache': 'from .filter_cache',
            
            # Fix 3: websocket_universe_cache is just universe_cache
            'from src.presentation.websocket.universe_cache': 'from src.presentation.websocket.universe_cache',
            'from .universe_cache': 'from .universe_cache',
            
            # Fix 4: websocket_analytics is just analytics
            'from src.presentation.websocket.analytics': 'from src.presentation.websocket.analytics',
            'from .analytics': 'from .analytics',
            
            # Fix 5: websocket_data_filter is just data_filter
            'from src.presentation.websocket.data_filter': 'from src.presentation.websocket.data_filter',
            'from .data_filter': 'from .data_filter',
            
            # Fix 6: websocket_statistics is just statistics
            'from src.presentation.websocket.statistics': 'from src.presentation.websocket.statistics',
            'from .statistics': 'from .statistics',
            
            # Fix 7: websocket_display is display_converter
            'from src.presentation.websocket.display_converter': 'from src.presentation.websocket.display_converter',
            'from .display_converter': 'from .display_converter',
            
            # Fix 8: data_sources.base should be core.interfaces
            'from src.core.interfaces': 'from src.core.interfaces',
            'import src.core.interfaces': 'import src.core.interfaces',
            
            # Fix 9: event_detector is in pipeline not root processing
            'from src.processing.pipeline.event_detector': 'from src.processing.pipeline.event_detector',
            'import src.processing.pipeline.event_detector': 'import src.processing.pipeline.event_detector',
            
            # Fix 10: models.bases (typo) should be models.base
            'from src.infrastructure.database.models.base': 'from src.infrastructure.database.models.base',
            
            # Fix 11: More WebSocket related fixes
            'from src.presentation.websocket.filter_cache': 'from src.presentation.websocket.filter_cache',
            'from src.presentation.websocket.analytics': 'from src.presentation.websocket.analytics',
            'from src.presentation.websocket.data_filter': 'from src.presentation.websocket.data_filter',
            'from src.presentation.websocket.universe_cache': 'from src.presentation.websocket.universe_cache',
            'from src.presentation.websocket.statistics': 'from src.presentation.websocket.statistics',
            'from src.presentation.websocket.display_converter': 'from src.presentation.websocket.display_converter',
        }
        
        print("Applying final import fixes...")
        print("=" * 60)
        
        files_fixed = {}
        
        for py_file in self.dest_dir.rglob("*.py"):
            if '__pycache__' in str(py_file) or 'venv' in str(py_file):
                continue
            
            try:
                content = py_file.read_text(encoding='utf-8')
                original = content
                
                for old, new in final_fixes.items():
                    if old in content:
                        content = content.replace(old, new)
                        rel_path = str(py_file.relative_to(self.dest_dir))
                        if rel_path not in files_fixed:
                            files_fixed[rel_path] = []
                        files_fixed[rel_path].append(f"{old} -> {new}")
                
                if content != original:
                    py_file.write_text(content, encoding='utf-8')
                    self.fixes_applied.append(str(py_file.relative_to(self.dest_dir)))
                    
            except Exception as e:
                print(f"Error processing {py_file}: {e}")
        
        # Print results
        if files_fixed:
            print(f"\nFixed {len(files_fixed)} files:")
            for filepath, fixes in sorted(files_fixed.items()):
                print(f"  ✓ {filepath}")
                for fix in fixes[:3]:  # Show first 3 fixes per file
                    print(f"      {fix}")
                if len(fixes) > 3:
                    print(f"      ... and {len(fixes) - 3} more")
        else:
            print("No files needed fixing")
        
        return len(files_fixed)
    
    def create_success_test(self):
        """Create a test to verify everything works"""
        test_script = self.dest_dir / "test_migration_success.py"
        
        content = '''#!/usr/bin/env python3
"""
Test if the migration was successful
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("=" * 60)
print("TICKSTOCK V2 MIGRATION SUCCESS TEST")
print("=" * 60)

passed = []
failed = []

def test_import(name, statement):
    try:
        exec(statement)
        passed.append(name)
        return True
    except Exception as e:
        failed.append((name, str(e)[:50]))
        return False

# Test critical imports
print("\\nTesting critical imports...")
print("-" * 40)

# Core Services
if test_import("MarketDataService", "from src.core.services.market_data_service import MarketDataService"):
    print("✓ MarketDataService imports successfully")

if test_import("SessionManager", "from src.core.services.session_manager import SessionManager"):
    print("✓ SessionManager imports successfully")

if test_import("ConfigManager", "from src.core.services.config_manager import ConfigManager"):
    print("✓ ConfigManager imports successfully")

# WebSocket
if test_import("WebSocketManager", "from src.presentation.websocket.manager import WebSocketManager"):
    print("✓ WebSocketManager imports successfully")

# Data Sources
if test_import("DataProviderFactory", "from src.infrastructure.data_sources.factory import DataProviderFactory"):
    print("✓ DataProviderFactory imports successfully")

# Event Detection
if test_import("EventDetectionManager", "from src.processing.detectors.manager import EventDetectionManager"):
    print("✓ EventDetectionManager imports successfully")

# Domain Models
if test_import("Domain Events", "from src.core.domain.events.highlow import HighLowEvent"):
    print("✓ Domain events import successfully")

# Authentication
if test_import("Authentication", "from src.auth.authentication import AuthenticationManager"):
    print("✓ Authentication imports successfully")

print("\\n" + "=" * 60)
print("MIGRATION TEST RESULTS")
print("=" * 60)
print(f"✅ Passed: {len(passed)}")
print(f"❌ Failed: {len(failed)}")

if failed:
    print("\\nFailed imports:")
    for name, error in failed:
        print(f"  - {name}: {error}")
else:
    print("\\n🎉 SUCCESS! All critical imports are working!")
    print("The TickStock V2 migration is complete!")
    print("\\nYou can now:")
    print("  1. Run the application: python src/app.py")
    print("  2. Run tests: pytest tests/")
    print("  3. Start development with the new modular structure")

print("=" * 60)
'''
        
        try:
            test_script.write_text(content, encoding='utf-8')
            print(f"\n✓ Created test_migration_success.py")
        except Exception as e:
            print(f"\n✗ Error creating test: {e}")
    
    def run(self):
        """Run all fixes"""
        print("Final Import Fixes - Last Mile")
        print("=" * 60)
        
        files_fixed = self.apply_final_fixes()
        self.create_success_test()
        
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Files fixed: {files_fixed}")
        
        print("\n" + "=" * 60)
        print("FINAL TEST")
        print("=" * 60)
        print("Run the migration success test:")
        print("  python test_migration_success.py")
        print("\nThis will tell you if the migration is complete!")


def main():
    fixer = FinalImportFixes()
    fixer.run()
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())