#!/usr/bin/env python3
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
