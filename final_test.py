#!/usr/bin/env python3
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
print("\nCritical Services:")
print("-" * 40)
test("MarketDataService", lambda: exec("from src.core.services.market_data_service import MarketDataService"))
test("SessionManager", lambda: exec("from src.core.services.session_manager import SessionManager"))
test("ConfigManager", lambda: exec("from src.core.services.config_manager import ConfigManager"))

print("\nWebSocket Layer:")
print("-" * 40)
test("WebSocketManager", lambda: exec("from src.presentation.websocket.manager import WebSocketManager"))
test("WebSocketPublisher", lambda: exec("from src.presentation.websocket.publisher import WebSocketPublisher"))

print("\nData Layer:")
print("-" * 40)
test("DataProviderFactory", lambda: exec("from src.infrastructure.data_sources.factory import DataProviderFactory"))

print("\nDomain Models:")
print("-" * 40)
test("Events", lambda: exec("from src.core.domain.events.highlow import HighLowEvent"))
test("Market", lambda: exec("from src.core.domain.market.tick import TickData"))

print("\nUtilities:")
print("-" * 40)
test("General Utils", lambda: exec("from src.shared.utils.general import *"))
test("Event Factory", lambda: exec("from src.shared.utils.event_factory import EventFactory"))

print("\nConfiguration:")
print("-" * 40)
test("App Config", lambda: exec("import config.app_config"))
test("Logging", lambda: exec("from config.logging_config import get_domain_logger"))

print("\n" + "=" * 60)
print(f"RESULTS: {success_count} passed, {fail_count} failed")

if fail_count > 0:
    print("\nErrors:")
    for name, error in errors[:5]:  # Show first 5 errors
        print(f"  - {name}: {error[:100]}")
    
if success_count > 10:
    print("\n✅ Most critical imports are working!")
    print("The migration is largely successful.")
elif success_count > 5:
    print("\n⚠️ Partial success - some imports still need work")
else:
    print("\n❌ Many imports still failing - needs more fixes")
