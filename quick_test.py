#!/usr/bin/env python3
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
    
    print("\n🎉 All critical imports working!")
    
except ImportError as e:
    print(f"✗ Import still failing: {e}")
except SyntaxError as e:
    print(f"✗ Syntax error still present: {e}")
