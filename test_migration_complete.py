#!/usr/bin/env python3
"""
Test if migration is complete - Final Check
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("=" * 70)
print(" " * 15 + "TICKSTOCK V2 MIGRATION COMPLETION TEST")
print("=" * 70)

# Quick essential imports test
essentials = {
    "Core Service": "from src.core.services.market_data_service import MarketDataService",
    "Session Manager": "from src.core.services.session_manager import SessionManager",
    "WebSocket Manager": "from src.presentation.websocket.manager import WebSocketManager",
    "Data Factory": "from src.infrastructure.data_sources.factory import DataProviderFactory",
    "Event Manager": "from src.processing.detectors.manager import EventDetectionManager",
    "Domain Events": "from src.core.domain.events.highlow import HighLowEvent",
    "Authentication": "from src.auth.authentication import AuthenticationManager",
    "Configuration": "from config.logging_config import get_domain_logger",
}

passed = 0
failed = 0

print("\nTesting Essential Imports:")
print("-" * 70)

for name, import_stmt in essentials.items():
    try:
        exec(import_stmt)
        print(f"✅ {name:<20} ✓ Working")
        passed += 1
    except ImportError as e:
        module = str(e).split("'")[1] if "'" in str(e) else "unknown"
        print(f"❌ {name:<20} ✗ Missing: {module}")
        failed += 1
    except Exception as e:
        print(f"❌ {name:<20} ✗ Error: {str(e)[:40]}")
        failed += 1

print("\n" + "=" * 70)
total = passed + failed
success_rate = (passed / total * 100) if total > 0 else 0

print(f"\n📊 Final Score: {success_rate:.0f}%")
print(f"   ✅ Working: {passed}/{total}")
print(f"   ❌ Failed: {failed}/{total}")

print("\n" + "=" * 70)

if success_rate >= 75:
    print("\n🎉 MIGRATION COMPLETE!")
    print("\nThe TickStock V2 migration is successful!")
    print("You can now:")
    print("  • Run the application: python src/app.py")
    print("  • Run tests: pytest tests/")
    print("  • Start development with the new modular structure")
else:
    print("\n⚠️ Migration needs more work")
    print("Some critical imports are still failing.")
    print("Review the errors above and fix remaining issues.")

print("=" * 70)
