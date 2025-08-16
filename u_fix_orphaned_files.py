#!/usr/bin/env python3
"""
Fix orphaned files by ensuring proper imports in __init__.py files
and updating app.py to use new module structure
"""

from pathlib import Path
import re

def fix_orphaned_files():
    """Fix orphaned files by creating proper import chains."""
    base_path = Path(r"C:\Users\McDude\TickStockAppV2")
    
    print("=" * 60)
    print("FIXING ORPHANED FILES")
    print("=" * 60)
    
    # Step 1: Update __init__.py files to properly export modules
    init_updates = {
        "src/api/rest/__init__.py": [
            "from .api import *",
            "from .auth import *", 
            "from .main import *"
        ],
        "src/auth/__init__.py": [
            "from .authentication import AuthenticationManager",
            "from .registration import RegistrationManager",
            "from .session import SessionManager",
            "__all__ = ['AuthenticationManager', 'RegistrationManager', 'SessionManager']"
        ],
        "src/core/domain/events/__init__.py": [
            "from .base import BaseEvent",
            "from .control import ControlEvent",
            "from .highlow import HighLowEvent",
            "from .surge import SurgeEvent",
            "from .trend import TrendEvent",
            "__all__ = ['BaseEvent', 'ControlEvent', 'HighLowEvent', 'SurgeEvent', 'TrendEvent']"
        ],
        "src/core/domain/market/__init__.py": [
            "from .tick import TickData",
            "from .analytics import MarketAnalytics",
            "__all__ = ['TickData', 'MarketAnalytics']"
        ],
        "src/core/services/__init__.py": [
            "from .market_data_service import MarketDataService",
            "from .session_manager import SessionManager",
            "from .config_manager import ConfigManager",
            "from .analytics_manager import AnalyticsManager",
            "__all__ = ['MarketDataService', 'SessionManager', 'ConfigManager', 'AnalyticsManager']"
        ],
        "src/infrastructure/data_sources/__init__.py": [
            "from .factory import DataProviderFactory",
            "from .base import DataProvider",
            "__all__ = ['DataProviderFactory', 'DataProvider']"
        ],
        "src/presentation/websocket/__init__.py": [
            "from .manager import WebSocketManager",
            "from .publisher import WebSocketPublisher",
            "from .data_publisher import DataPublisher",
            "__all__ = ['WebSocketManager', 'WebSocketPublisher', 'DataPublisher']"
        ],
        "src/processing/detectors/__init__.py": [
            "from .manager import EventDetectionManager",
            "from .highlow_detector import HighLowDetector",
            "from .trend_detector import TrendDetector",
            "from .surge_detector import SurgeDetector",
            "__all__ = ['EventDetectionManager', 'HighLowDetector', 'TrendDetector', 'SurgeDetector']"
        ]
    }
    
    print("\n1. Updating __init__.py files...")
    for init_file, imports in init_updates.items():
        file_path = base_path / init_file
        
        # Create directory if it doesn't exist
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write the imports
        content = "\"\"\"Module initialization.\"\"\"\n\n"
        content += '\n'.join(imports) + '\n'
        
        try:
            file_path.write_text(content, encoding='utf-8')
            print(f"  ✅ Updated {init_file}")
        except Exception as e:
            print(f"  ❌ Failed to update {init_file}: {e}")
    
    # Step 2: Update app.py to import all major modules
    print("\n2. Updating app.py imports...")
    app_path = base_path / "src/app.py"
    
    if app_path.exists():
        try:
            content = app_path.read_text(encoding='utf-8')
            
            # Add imports at the top after existing imports
            new_imports = """
# Import all major modules to prevent orphaning
from src.api.rest import *
from src.auth import AuthenticationManager, RegistrationManager
from src.core.domain.events import *
from src.core.services import *
from src.infrastructure.data_sources import DataProviderFactory
from src.presentation.websocket import WebSocketManager, WebSocketPublisher
from src.processing.detectors import EventDetectionManager
"""
            
            # Find where to insert (after the last import but before any code)
            import_end = 0
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if line.strip() and not line.startswith('import') and not line.startswith('from'):
                    if i > 0 and (lines[i-1].startswith('import') or lines[i-1].startswith('from')):
                        import_end = i
                        break
            
            if import_end > 0:
                lines.insert(import_end, new_imports)
                new_content = '\n'.join(lines)
                app_path.write_text(new_content, encoding='utf-8')
                print(f"  ✅ Updated app.py with comprehensive imports")
            else:
                print(f"  ⚠️ Could not find proper location to add imports in app.py")
                
        except Exception as e:
            print(f"  ❌ Failed to update app.py: {e}")
    
    print("\n" + "=" * 60)
    print("Orphaned files fix complete!")
    print("=" * 60)

if __name__ == "__main__":
    fix_orphaned_files()