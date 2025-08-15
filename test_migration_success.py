#!/usr/bin/env python3
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
print("\nTesting critical imports...")
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

print("\n" + "=" * 60)
print("MIGRATION TEST RESULTS")
print("=" * 60)
print(f"✅ Passed: {len(passed)}")
print(f"❌ Failed: {len(failed)}")

if failed:
    print("\nFailed imports:")
    for name, error in failed:
        print(f"  - {name}: {error}")
else:
    print("\n🎉 SUCCESS! All critical imports are working!")
    print("The TickStock V2 migration is complete!")
    print("\nYou can now:")
    print("  1. Run the application: python src/app.py")
    print("  2. Run tests: pytest tests/")
    print("  3. Start development with the new modular structure")

print("=" * 60)
