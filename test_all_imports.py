#!/usr/bin/env python3
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
print("\nCore Services:")
print("-" * 40)
test_import("MarketDataService", "from src.core.services.market_data_service import MarketDataService")
test_import("SessionManager", "from src.core.services.session_manager import SessionManager")
test_import("ConfigManager", "from src.core.services.config_manager import ConfigManager")
test_import("AnalyticsManager", "from src.core.services.analytics_manager import AnalyticsManager")

# WebSocket Components
print("\nWebSocket Components:")
print("-" * 40)
test_import("WebSocketManager", "from src.presentation.websocket.manager import WebSocketManager")
test_import("WebSocketPublisher", "from src.presentation.websocket.publisher import WebSocketPublisher")
test_import("DataPublisher", "from src.presentation.websocket.data_publisher import DataPublisher")

# Data Sources
print("\nData Sources:")
print("-" * 40)
test_import("DataProviderFactory", "from src.infrastructure.data_sources.factory import DataProviderFactory")
test_import("PolygonProvider", "from src.infrastructure.data_sources.polygon.provider import PolygonDataProvider")

# Event Detection
print("\nEvent Detection:")
print("-" * 40)
test_import("EventDetectionManager", "from src.processing.detectors.manager import EventDetectionManager")
test_import("HighLowDetector", "from src.processing.detectors.highlow_detector import HighLowDetector")

# Domain Models
print("\nDomain Models:")
print("-" * 40)
test_import("HighLowEvent", "from src.core.domain.events.highlow import HighLowEvent")
test_import("TickData", "from src.core.domain.market.tick import TickData")

# Auth
print("\nAuthentication:")
print("-" * 40)
test_import("AuthenticationManager", "from src.auth.authentication import AuthenticationManager")

# Config
print("\nConfiguration:")
print("-" * 40)
test_import("Logging Config", "from config.logging_config import get_domain_logger")
test_import("App Config", "import config.app_config")

# Summary
print("\n" + "=" * 60)
print(f"RESULTS: {tests_passed} passed, {tests_failed} failed")
if tests_failed == 0:
    print("🎉 ALL IMPORTS WORKING! Migration successful!")
else:
    print(f"⚠️  {tests_failed} imports still need fixing")
print("=" * 60)
