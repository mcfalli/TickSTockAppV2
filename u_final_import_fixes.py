#!/usr/bin/env python3
"""
Final fixes for remaining import issues
"""

import os
from pathlib import Path
import re

class FinalImportFixer:
    def __init__(self, dest_dir: str = r"C:\Users\McDude\TickStockAppV2"):
        self.dest_dir = Path(dest_dir)
        self.fixes_applied = []
        
    def fix_file_imports(self, filepath: Path, replacements: dict):
        """Apply import replacements to a file"""
        try:
            content = filepath.read_text(encoding='utf-8')
            original = content
            
            for old, new in replacements.items():
                if old in content:
                    content = content.replace(old, new)
                    print(f"  Replaced: {old} -> {new}")
            
            if content != original:
                filepath.write_text(content, encoding='utf-8')
                return True
            return False
        except Exception as e:
            print(f"  Error: {e}")
            return False
    
    def fix_transport_models_imports(self):
        """Fix imports of transport models"""
        print("\nFixing transport_models imports...")
        print("-" * 40)
        
        replacements = {
            'from src.presentation.converters.transport_models import': 'from src.presentation.converters.transport_models import',
            'import src.presentation.converters.transport_models': 'import src.presentation.converters.transport_models',
            'from .transport_models import': 'from .transport_models import',
        }
        
        # Find all Python files that might have this import
        for py_file in self.dest_dir.rglob("*.py"):
            if '__pycache__' in str(py_file) or 'venv' in str(py_file):
                continue
                
            content = py_file.read_text(encoding='utf-8')
            if 'presentation.converters.models' in content or '.models import' in content:
                print(f"Fixing: {py_file.relative_to(self.dest_dir)}")
                if self.fix_file_imports(py_file, replacements):
                    self.fixes_applied.append(str(py_file.relative_to(self.dest_dir)))
    
    def fix_websocket_manager_imports(self):
        """Fix WebSocket manager imports"""
        print("\nFixing WebSocket manager imports...")
        print("-" * 40)
        
        replacements = {
            'from src.presentation.websocket.manager import': 'from src.presentation.websocket.manager import',
            'import src.presentation.websocket.manager': 'import src.presentation.websocket.manager',
            'from .manager import': 'from .manager import',
            'from src.presentation.websocket.manager import': 'from src.presentation.websocket.manager import',
        }
        
        # Find all Python files that might have this import
        for py_file in self.dest_dir.rglob("*.py"):
            if '__pycache__' in str(py_file) or 'venv' in str(py_file):
                continue
                
            content = py_file.read_text(encoding='utf-8')
            if 'web_socket_manager' in content:
                print(f"Fixing: {py_file.relative_to(self.dest_dir)}")
                if self.fix_file_imports(py_file, replacements):
                    self.fixes_applied.append(str(py_file.relative_to(self.dest_dir)))
    
    def check_and_fix_other_common_issues(self):
        """Fix other common import issues"""
        print("\nChecking for other common import issues...")
        print("-" * 40)
        
        common_fixes = {
            # WebSocket related
            'from src.presentation.websocket import': 'from src.presentation.websocket import',
            'import src.presentation.websocket': 'import src.presentation.websocket',
            
            # Services related  
            'from src.core.services import': 'from src.core.services import',
            'import src.core.services': 'import src.core.services',
            
            # Utils related
            'from src.shared.utils import': 'from src.shared.utils import',
            'import src.shared.utils': 'import src.shared.utils',
            
            # Event detection
            'from src.processing.detectors import': 'from src.processing.detectors import',
            'import src.processing.detectors': 'import src.processing.detectors',
            
            # Data providers
            'from src.infrastructure.data_sources import': 'from src.infrastructure.data_sources import',
            'import src.infrastructure.data_sources': 'import src.infrastructure.data_sources',
        }
        
        for py_file in self.dest_dir.rglob("*.py"):
            if '__pycache__' in str(py_file) or 'venv' in str(py_file):
                continue
            
            if self.fix_file_imports(py_file, common_fixes):
                self.fixes_applied.append(str(py_file.relative_to(self.dest_dir)))
    
    def create_enhanced_test_script(self):
        """Create an enhanced test script"""
        test_script = self.dest_dir / "test_all_imports.py"
        
        content = '''#!/usr/bin/env python3
"""
Comprehensive import test for TickStock V2
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("Comprehensive Import Test")
print("=" * 60)

tests_passed = 0
tests_failed = 0

def test_import(description, import_statement):
    global tests_passed, tests_failed
    try:
        exec(import_statement)
        print(f"✓ {description}")
        tests_passed += 1
        return True
    except ImportError as e:
        print(f"✗ {description}: {e}")
        tests_failed += 1
        return False

# Core Services
print("\\nCore Services:")
print("-" * 40)
test_import("MarketDataService", "from src.core.services.market_data_service import MarketDataService")
test_import("SessionManager", "from src.core.services.session_manager import SessionManager")
test_import("ConfigManager", "from src.core.services.config_manager import ConfigManager")
test_import("AnalyticsManager", "from src.core.services.analytics_manager import AnalyticsManager")

# WebSocket Components
print("\\nWebSocket Components:")
print("-" * 40)
test_import("WebSocketManager", "from src.presentation.websocket.manager import WebSocketManager")
test_import("WebSocketPublisher", "from src.presentation.websocket.publisher import WebSocketPublisher")
test_import("DataPublisher", "from src.presentation.websocket.data_publisher import DataPublisher")

# Data Sources
print("\\nData Sources:")
print("-" * 40)
test_import("DataProviderFactory", "from src.infrastructure.data_sources.factory import DataProviderFactory")
test_import("PolygonProvider", "from src.infrastructure.data_sources.polygon.provider import PolygonDataProvider")

# Event Detection
print("\\nEvent Detection:")
print("-" * 40)
test_import("EventDetectionManager", "from src.processing.detectors.manager import EventDetectionManager")
test_import("HighLowDetector", "from src.processing.detectors.highlow_detector import HighLowDetector")

# Domain Models
print("\\nDomain Models:")
print("-" * 40)
test_import("HighLowEvent", "from src.core.domain.events.highlow import HighLowEvent")
test_import("TickData", "from src.core.domain.market.tick import TickData")

# Auth
print("\\nAuthentication:")
print("-" * 40)
test_import("AuthenticationManager", "from src.auth.authentication import AuthenticationManager")

# Config
print("\\nConfiguration:")
print("-" * 40)
test_import("Logging Config", "from config.logging_config import get_domain_logger")
test_import("App Config", "import config.app_config")

# Summary
print("\\n" + "=" * 60)
print(f"RESULTS: {tests_passed} passed, {tests_failed} failed")
if tests_failed == 0:
    print("🎉 ALL IMPORTS WORKING! Migration successful!")
else:
    print(f"⚠️  {tests_failed} imports still need fixing")
print("=" * 60)
'''
        
        try:
            test_script.write_text(content, encoding='utf-8')
            print(f"✓ Created test_all_imports.py")
            return True
        except Exception as e:
            print(f"✗ Error creating test script: {e}")
            return False
    
    def run_all_fixes(self):
        """Run all fixes"""
        print("Final Import Fixes")
        print("=" * 60)
        
        self.fix_transport_models_imports()
        self.fix_websocket_manager_imports()
        self.check_and_fix_other_common_issues()
        self.create_enhanced_test_script()
        
        print("\n" + "=" * 60)
        print("FIXES APPLIED:")
        print("=" * 60)
        if self.fixes_applied:
            for fix in set(self.fixes_applied):  # Remove duplicates
                print(f"  ✓ {fix}")
        else:
            print("  No files needed fixing!")
        
        print("\n" + "=" * 60)
        print("NEXT STEPS:")
        print("=" * 60)
        print("1. Run comprehensive test:")
        print("   python test_all_imports.py")
        print("\n2. If all passes, try running the app:")
        print("   python src/app.py")


def main():
    """Main execution"""
    fixer = FinalImportFixer()
    fixer.run_all_fixes()
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())