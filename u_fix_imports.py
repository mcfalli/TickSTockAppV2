#!/usr/bin/env python3
"""
Fix remaining import issues after migration
"""

import os
from pathlib import Path
from typing import Dict, List

class ImportFixer:
    def __init__(self, dest_dir: str = r"C:\Users\McDude\TickStockAppV2"):
        self.dest_dir = Path(dest_dir)
        self.fixes_applied = []
        
    def fix_config_init(self):
        """Fix config/__init__.py"""
        config_init = self.dest_dir / "config" / "__init__.py"
        
        new_content = '''"""
Config package initialization
Only import what's actually in the config folder
"""

# Only import what exists in config/
from .app_config import *
from .logging_config import *

# ConfigManager was moved to src.core.services
# If you need ConfigManager, import it as:
# from src.core.services import ConfigManager

__all__ = []
'''
        
        try:
            config_init.write_text(new_content, encoding='utf-8')
            self.fixes_applied.append("Fixed config/__init__.py")
            print("✓ Fixed config/__init__.py")
        except Exception as e:
            print(f"✗ Error fixing config/__init__.py: {e}")
    
    def fix_memory_accumulation_imports(self):
        """Fix imports in memory_accumulation.py"""
        file_path = self.dest_dir / "src" / "core" / "services" / "memory_accumulation.py"
        
        if file_path.exists():
            try:
                content = file_path.read_text(encoding='utf-8')
                
                # Fix the import
                content = content.replace(
                    "from config.logging_config import",
                    "from config.logging_config import"
                )
                
                # This file might not exist yet, so let's check other imports too
                if "from session_accumulation" in content:
                    content = content.replace(
                        "from session_accumulation",
                        "from src.core.services"
                    )
                
                file_path.write_text(content, encoding='utf-8')
                self.fixes_applied.append("Fixed memory_accumulation.py imports")
                print("✓ Fixed memory_accumulation.py imports")
            except Exception as e:
                print(f"✗ Error fixing memory_accumulation.py: {e}")
    
    def fix_core_services_init(self):
        """Fix src/core/services/__init__.py to handle missing imports"""
        services_init = self.dest_dir / "src" / "core" / "services" / "__init__.py"
        
        # First, let's check what files actually exist
        services_dir = self.dest_dir / "src" / "core" / "services"
        existing_files = [f.stem for f in services_dir.glob("*.py") if f.stem != "__init__"]
        
        print(f"Found service files: {existing_files}")
        
        # Build new init content based on what exists
        imports = []
        exports = []
        
        # Map of expected imports to actual file names
        import_map = {
            "market_data_service": ("MarketDataService", "market_data_service"),
            "session_manager": ("SessionManager", "session_manager"),
            "analytics_manager": ("AnalyticsManager", "analytics_manager"),
            "config_manager": ("ConfigManager", "config_manager"),
            "startup_service": ("StartupService", "startup_service"),
            "universe_service": ("TickStockUniverseManager", "universe_service"),
            "user_filters_service": ("UserFiltersService", "user_filters_service"),
            "user_settings_service": ("UserSettingsService", "user_settings_service"),
            "accumulation_manager": ("AccumulationManager", "accumulation_manager"),
            "analytics_coordinator": ("AnalyticsCoordinator", "analytics_coordinator"),
            "universe_coordinator": ("UniverseCoordinator", "universe_coordinator"),
            "analytics_sync": ("AnalyticsSync", "analytics_sync"),
            "database_sync": ("DatabaseSync", "database_sync"),
            "market_metrics": ("MarketMetrics", "market_metrics"),
            "memory_analytics": ("MemoryAnalytics", "memory_analytics"),
            "memory_accumulation": ("InMemorySessionAccumulation", "memory_accumulation"),
        }
        
        for file_stem in existing_files:
            if file_stem in import_map:
                class_name, module_name = import_map[file_stem]
                imports.append(f"from .{module_name} import {class_name}")
                exports.append(f"    '{class_name}'")
        
        # Build the imports string
        imports_str = '\n'.join(imports)
        exports_str = ',\n'.join(exports)
        
        new_content = f'''"""Business Services"""

# Import only what exists
{imports_str}

__all__ = [
{exports_str}
]
'''
        
        try:
            services_init.write_text(new_content, encoding='utf-8')
            self.fixes_applied.append("Fixed src/core/services/__init__.py")
            print("✓ Fixed src/core/services/__init__.py")
        except Exception as e:
            print(f"✗ Error fixing services init: {e}")
    
    def add_pythonpath_support(self):
        """Create a script to set PYTHONPATH for imports"""
        setup_script = self.dest_dir / "setup_env.py"
        
        content = '''#!/usr/bin/env python3
"""
Setup environment for TickStock V2
Run this before starting the application
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

print(f"✓ Added {project_root} to PYTHONPATH")
print("You can now import modules with:")
print("  from src.core.services import MarketDataService")
print("  from config.logging_config import get_domain_logger")
'''
        
        try:
            setup_script.write_text(content, encoding='utf-8')
            self.fixes_applied.append("Created setup_env.py")
            print("✓ Created setup_env.py for PYTHONPATH setup")
        except Exception as e:
            print(f"✗ Error creating setup_env.py: {e}")
        
        # Also create a .env addition suggestion
        env_addition = self.dest_dir / "pythonpath_setup.txt"
        env_content = '''# Add this to your .env file or set as environment variable:

PYTHONPATH=C:\\Users\\McDude\\TickStockAppV2

# Or in PowerShell:
$env:PYTHONPATH = "C:\\Users\\McDude\\TickStockAppV2"

# Or in Command Prompt:
set PYTHONPATH=C:\\Users\\McDude\\TickStockAppV2
'''
        
        try:
            env_addition.write_text(env_content)
            print("✓ Created pythonpath_setup.txt with environment instructions")
        except Exception as e:
            print(f"✗ Error creating pythonpath_setup.txt: {e}")
    
    def apply_all_fixes(self):
        """Apply all fixes"""
        print("Applying import fixes...")
        print("=" * 60)
        
        self.fix_config_init()
        self.fix_memory_accumulation_imports()
        self.fix_core_services_init()
        self.add_pythonpath_support()
        
        print("\n" + "=" * 60)
        print("FIXES APPLIED:")
        print("=" * 60)
        for fix in self.fixes_applied:
            print(f"  - {fix}")
        
        print("\n" + "=" * 60)
        print("NEXT STEPS:")
        print("=" * 60)
        print("1. Set PYTHONPATH environment variable:")
        print('   $env:PYTHONPATH = "C:\\Users\\McDude\\TickStockAppV2"')
        print("\n2. Test imports again:")
        print('   python -c "from src.core.services import MarketDataService"')
        print("\n3. If still issues, check pythonpath_setup.txt for more options")


def main():
    """Main execution"""
    print("TickStock Import Issue Fixer")
    print("=" * 60)
    
    fixer = ImportFixer()
    fixer.apply_all_fixes()
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())