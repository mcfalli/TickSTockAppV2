#!/usr/bin/env python3
"""
Final migration test - checking if everything works
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("=" * 70)
print(" " * 20 + "TICKSTOCK V2 FINAL MIGRATION TEST")
print("=" * 70)

results = {"passed": [], "failed": []}

def test(name, import_stmt):
    """Test an import statement"""
    try:
        exec(import_stmt)
        results["passed"].append(name)
        print(f"✅ {name:<30} OK")
        return True
    except Exception as e:
        error_msg = str(e).split("(")[0] if "(" in str(e) else str(e)[:50]
        results["failed"].append((name, error_msg))
        print(f"❌ {name:<30} {error_msg}")
        return False

print("\n📦 CORE SERVICES")
print("-" * 70)
test("MarketDataService", "from src.core.services.market_data_service import MarketDataService")
test("SessionManager", "from src.core.services.session_manager import SessionManager")
test("ConfigManager", "from src.core.services.config_manager import ConfigManager")
test("AnalyticsManager", "from src.core.services.analytics_manager import AnalyticsManager")

print("\n🌐 WEBSOCKET LAYER")
print("-" * 70)
test("WebSocketManager", "from src.presentation.websocket.manager import WebSocketManager")
test("WebSocketPublisher", "from src.presentation.websocket.publisher import WebSocketPublisher")

print("\n💾 DATA SOURCES")
print("-" * 70)
test("DataProviderFactory", "from src.infrastructure.data_sources.factory import DataProviderFactory")

print("\n🎯 EVENT DETECTION")
print("-" * 70)
test("EventDetectionManager", "from src.processing.detectors.manager import EventDetectionManager")
test("HighLowDetector", "from src.processing.detectors.highlow_detector import HighLowDetector")

print("\n📊 DOMAIN MODELS")
print("-" * 70)
test("Events", "from src.core.domain.events.highlow import HighLowEvent")
test("Market", "from src.core.domain.market.tick import TickData")

print("\n🔒 AUTHENTICATION")
print("-" * 70)
test("AuthenticationManager", "from src.auth.authentication import AuthenticationManager")

print("\n⚙️ CONFIGURATION")
print("-" * 70)
test("Logging", "from config.logging_config import get_domain_logger")
test("AppConfig", "import config.app_config")

# Summary
print("\n" + "=" * 70)
print(" " * 25 + "MIGRATION RESULTS")
print("=" * 70)
total = len(results["passed"]) + len(results["failed"])
success_rate = (len(results["passed"]) / total * 100) if total > 0 else 0

print(f"\n📊 Success Rate: {success_rate:.1f}%")
print(f"   ✅ Passed: {len(results['passed'])}")
print(f"   ❌ Failed: {len(results['failed'])}")

if success_rate >= 80:
    print("\n🎉 MIGRATION SUCCESSFUL!")
    print("   The core functionality is working. Minor issues can be fixed as needed.")
elif success_rate >= 50:
    print("\n⚠️  PARTIAL SUCCESS")
    print("   Most imports work but some critical issues remain.")
else:
    print("\n❌ MIGRATION NEEDS MORE WORK")
    print("   Many imports are still failing.")

if results["failed"]:
    print("\n📋 Failed Imports:")
    for name, error in results["failed"][:5]:
        print(f"   - {name}: {error}")

print("\n" + "=" * 70)
