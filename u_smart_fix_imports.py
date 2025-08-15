#!/usr/bin/env python3
"""
Smart Import Fixer - Detects actual class names in files
"""

import os
import ast
from pathlib import Path
from typing import Dict, List, Optional

class SmartImportFixer:
    def __init__(self, dest_dir: str = r"C:\Users\McDude\TickStockAppV2"):
        self.dest_dir = Path(dest_dir)
        self.class_mappings = {}
        
    def find_classes_in_file(self, filepath: Path) -> List[str]:
        """Find all class names defined in a Python file"""
        classes = []
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())
                
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    classes.append(node.name)
        except Exception as e:
            print(f"Error parsing {filepath.name}: {e}")
        
        return classes
    
    def analyze_services_directory(self):
        """Analyze all files in services directory to find actual class names"""
        services_dir = self.dest_dir / "src" / "core" / "services"
        
        print("Analyzing service files for actual class names...")
        print("=" * 60)
        
        for py_file in services_dir.glob("*.py"):
            if py_file.stem == "__init__":
                continue
                
            classes = self.find_classes_in_file(py_file)
            if classes:
                self.class_mappings[py_file.stem] = classes
                print(f"✓ {py_file.stem}.py contains: {', '.join(classes)}")
            else:
                print(f"⚠ {py_file.stem}.py - No classes found")
    
    def fix_services_init(self):
        """Create correct __init__.py based on actual class names"""
        services_init = self.dest_dir / "src" / "core" / "services" / "__init__.py"
        
        imports = []
        exports = []
        
        # Sort for consistent output
        for module_name in sorted(self.class_mappings.keys()):
            classes = self.class_mappings[module_name]
            for class_name in classes:
                # Skip test classes and private classes
                if not class_name.startswith('_') and not class_name.startswith('Test'):
                    imports.append(f"from .{module_name} import {class_name}")
                    exports.append(f"    '{class_name}'")
        
        # Add try-except for optional imports
        content = '''"""Business Services"""

# Import all available service classes
'''
        
        # Add imports with error handling
        for imp in imports:
            class_name = imp.split()[-1]
            content += '\ntry:\n'
            content += f'    {imp}\n'
            content += 'except ImportError as e:\n'
            content += f'    print(f"Warning: Could not import {class_name}: {{e}}")\n'
        
        content += '\n\n__all__ = [\n'
        content += ',\n'.join(exports)
        content += '\n]\n'
        
        try:
            services_init.write_text(content, encoding='utf-8')
            print(f"\n✓ Updated src/core/services/__init__.py with {len(exports)} exports")
            return True
        except Exception as e:
            print(f"\n✗ Error updating services init: {e}")
            return False
    
    def create_simple_test_script(self):
        """Create a simple test script"""
        test_script = self.dest_dir / "test_imports.py"
        
        content = '''#!/usr/bin/env python3
"""
Test imports after migration
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("Testing imports...")
print("=" * 60)

# Test 1: Direct import of a specific class
try:
    from src.core.services.market_data_service import MarketDataService
    print("✓ Direct import of MarketDataService works!")
except ImportError as e:
    print(f"✗ Failed to import MarketDataService: {e}")

# Test 2: Import from services package
try:
    from src.core.services import SessionManager
    print("✓ Import SessionManager from services package works!")
except ImportError as e:
    print(f"✗ Failed to import SessionManager: {e}")

# Test 3: Import WebSocket components
try:
    from src.presentation.websocket.manager import WebSocketManager
    print("✓ WebSocket manager import works!")
except ImportError as e:
    print(f"✗ Failed to import WebSocketManager: {e}")

# Test 4: Import config
try:
    from config.logging_config import get_domain_logger
    print("✓ Config imports work!")
except ImportError as e:
    print(f"✗ Failed to import from config: {e}")

print("=" * 60)
print("Import test complete!")
'''
        
        try:
            test_script.write_text(content, encoding='utf-8')
            print(f"✓ Created test_imports.py")
            return True
        except Exception as e:
            print(f"✗ Error creating test script: {e}")
            return False
    
    def create_minimal_services_init(self):
        """Create a minimal __init__.py that doesn't import everything"""
        services_init = self.dest_dir / "src" / "core" / "services" / "__init__.py"
        
        content = '''"""Business Services

Import service classes individually as needed:
    from src.core.services.market_data_service import MarketDataService
    from src.core.services.session_manager import SessionManager
    etc.
"""

# Only import the most commonly used services
try:
    from .market_data_service import MarketDataService
except ImportError:
    MarketDataService = None
    
try:
    from .session_manager import SessionManager  
except ImportError:
    SessionManager = None

try:
    from .config_manager import ConfigManager
except ImportError:
    ConfigManager = None

# Export what was successfully imported
__all__ = [
    name for name in ['MarketDataService', 'SessionManager', 'ConfigManager']
    if globals().get(name) is not None
]
'''
        
        try:
            services_init.write_text(content, encoding='utf-8')
            print(f"✓ Created minimal src/core/services/__init__.py")
            return True
        except Exception as e:
            print(f"✗ Error creating minimal init: {e}")
            return False
    
    def run(self):
        """Run the complete fix process"""
        print("Smart Import Fixer")
        print("=" * 60)
        
        # First analyze what we have
        self.analyze_services_directory()
        
        print("\n" + "=" * 60)
        print("Creating minimal services __init__.py...")
        print("=" * 60)
        
        # Create a minimal init that won't fail
        self.create_minimal_services_init()
        
        # Create test script
        self.create_simple_test_script()
        
        print("\n" + "=" * 60)
        print("NEXT STEPS:")
        print("=" * 60)
        print("1. Run the test script:")
        print("   python test_imports.py")
        print("\n2. For direct usage, import specific classes:")
        print("   from src.core.services.market_data_service import MarketDataService")
        print("\n3. Check the class names found above and use the correct ones")


def main():
    """Main execution"""
    fixer = SmartImportFixer()
    fixer.run()
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())