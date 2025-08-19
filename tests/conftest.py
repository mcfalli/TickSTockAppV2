"""
Pytest configuration and shared fixtures for TickStock tests.
"""

import pytest
import os
import sys
import tempfile
import json
from unittest.mock import Mock, MagicMock
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import time

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Try to import actual classes, use mocks if not available
try:
    from src.core.domain.events.base import BaseEvent
except ImportError:
    BaseEvent = None

try:
    from src.core.domain.events.highlow import HighLowEvent
except ImportError:
    HighLowEvent = None
    
try:
    from src.core.domain.events.surge import SurgeEvent
except ImportError:
    SurgeEvent = None
    
try:
    from src.core.domain.events.trend import TrendEvent
except ImportError:
    TrendEvent = None


@dataclass
class MockTick:
    """Mock tick data for testing"""
    ticker: str
    price: float
    volume: int
    timestamp: float
    bid: float = 0.0
    ask: float = 0.0
    
    @classmethod
    def create(cls, ticker: str = "AAPL", price: float = 150.0, volume: int = 1000) -> 'MockTick':
        return cls(
            ticker=ticker,
            price=price,
            volume=volume,
            timestamp=time.time(),
            bid=price - 0.01,
            ask=price + 0.01
        )


class EventBuilder:
    """Builder pattern for creating test events"""
    
    @staticmethod
    def high_low_event(
        ticker: str = "AAPL",
        price: float = 150.0,
        event_type: str = "high",
        **kwargs
    ):
        """Create a test HighLowEvent"""
        if HighLowEvent is None:
            # Return mock event if class not available
            return {
                'ticker': ticker,
                'type': event_type,
                'price': price,
                'direction': "up" if event_type == "high" else "down",
                **kwargs
            }
        return HighLowEvent(
            ticker=ticker,
            type=event_type,
            price=price,
            direction="up" if event_type == "high" else "down",
            **kwargs
        )
    
    @staticmethod
    def surge_event(
        ticker: str = "AAPL",
        price: float = 150.0,
        volume: float = 1000000.0,
        volume_ratio: float = 3.5,
        **kwargs
    ):
        """Create a test SurgeEvent"""
        if SurgeEvent is None:
            # Return mock event if class not available
            return {
                'ticker': ticker,
                'type': "surge",
                'price': price,
                'volume': volume,
                'volume_ratio': volume_ratio,
                **kwargs
            }
        return SurgeEvent(
            ticker=ticker,
            type="surge",
            price=price,
            volume=volume,
            volume_ratio=volume_ratio,
            **kwargs
        )
    
    @staticmethod
    def trend_event(
        ticker: str = "AAPL",
        price: float = 150.0,
        direction: str = "up",
        period: int = 180,
        **kwargs
    ):
        """Create a test TrendEvent"""
        if TrendEvent is None:
            # Return mock event if class not available
            return {
                'ticker': ticker,
                'type': "trend",
                'price': price,
                'direction': direction,
                'period': period,
                **kwargs
            }
        return TrendEvent(
            ticker=ticker,
            type="trend",
            price=price,
            direction=direction,
            period=period,
            **kwargs
        )


@pytest.fixture
def event_builder():
    """Provide EventBuilder for test methods"""
    return EventBuilder()


@pytest.fixture
def mock_tick():
    """Provide a mock tick for testing"""
    return MockTick.create()


@pytest.fixture
def mock_ticks():
    """Provide multiple mock ticks for testing"""
    tickers = ["AAPL", "GOOGL", "MSFT", "TSLA"]
    return [MockTick.create(ticker=ticker, price=100.0 + i*10) for i, ticker in enumerate(tickers)]


@pytest.fixture
def mock_polygon_data():
    """Mock Polygon API response data"""
    return {
        "results": [
            {
                "T": "AAPL",
                "c": 150.25,
                "h": 152.10,
                "l": 149.80,
                "o": 150.00,
                "v": 1234567,
                "vw": 150.50,
                "t": int(time.time() * 1000)
            }
        ],
        "status": "OK",
        "count": 1
    }


@pytest.fixture
def mock_user_preferences():
    """Mock user preferences for testing"""
    return {
        "user_id": "test_user_123",
        "selected_tickers": ["AAPL", "GOOGL", "MSFT"],
        "event_filters": {
            "high_low": True,
            "surge": True,
            "trend": False
        },
        "notification_settings": {
            "email": True,
            "push": False
        }
    }


@pytest.fixture
def temp_trace_file():
    """Create a temporary trace file for testing"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        trace_data = {
            "trace_id": "test_trace_123",
            "duration_seconds": 5.0,
            "steps": [
                {
                    "timestamp": time.time(),
                    "ticker": "AAPL",
                    "component": "event_detector",
                    "action": "event_detected",
                    "data": {
                        "event_id": "test_event_123",
                        "event_type": "high",
                        "price": 150.25
                    }
                },
                {
                    "timestamp": time.time() + 0.1,
                    "ticker": "AAPL", 
                    "component": "websocket_publisher",
                    "action": "event_emitted",
                    "data": {
                        "event_id": "test_event_123",
                        "user_count": 5
                    }
                }
            ]
        }
        json.dump(trace_data, f)
        temp_file = f.name
    
    yield temp_file
    
    # Cleanup
    if os.path.exists(temp_file):
        os.unlink(temp_file)


@pytest.fixture
def mock_database():
    """Mock database connection for testing"""
    db_mock = Mock()
    db_mock.execute.return_value = Mock()
    db_mock.fetchall.return_value = []
    db_mock.fetchone.return_value = None
    db_mock.commit.return_value = None
    db_mock.rollback.return_value = None
    return db_mock


@pytest.fixture
def mock_redis():
    """Mock Redis connection for testing"""
    redis_mock = Mock()
    redis_mock.get.return_value = None
    redis_mock.set.return_value = True
    redis_mock.delete.return_value = 1
    redis_mock.exists.return_value = False
    redis_mock.expire.return_value = True
    return redis_mock


@pytest.fixture
def mock_websocket_manager():
    """Mock WebSocket manager for testing"""
    ws_mock = Mock()
    ws_mock.emit_to_user.return_value = True
    ws_mock.broadcast_event.return_value = True
    ws_mock.get_connected_users.return_value = ["user1", "user2"]
    ws_mock.is_user_connected.return_value = True
    return ws_mock


@pytest.fixture(scope="session")
def test_config():
    """Test configuration settings"""
    return {
        "TESTING": True,
        "DATABASE_URL": "sqlite:///:memory:",
        "REDIS_URL": "redis://localhost:6379/15",  # Test database
        "POLYGON_API_KEY": "test_api_key",
        "USE_SIMULATED_DATA": True,
        "LOG_LEVEL": "DEBUG"
    }


@pytest.fixture(autouse=True)
def setup_test_environment(test_config):
    """Automatically set up test environment for all tests"""
    # Set environment variables for testing
    for key, value in test_config.items():
        os.environ[key] = str(value)
    
    yield
    
    # Cleanup environment variables
    for key in test_config.keys():
        os.environ.pop(key, None)


# Performance testing utilities
@pytest.fixture
def performance_timer():
    """Timer utility for performance tests"""
    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
        
        def start(self):
            self.start_time = time.perf_counter()
        
        def stop(self):
            self.end_time = time.perf_counter()
        
        @property
        def elapsed(self) -> float:
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return 0.0
    
    return Timer()


# Test data generators
@pytest.fixture
def market_data_generator():
    """Generate realistic market data for testing"""
    class MarketDataGenerator:
        @staticmethod
        def price_series(
            ticker: str,
            base_price: float = 100.0,
            count: int = 100,
            volatility: float = 0.02
        ) -> List[MockTick]:
            """Generate a price series with realistic movement"""
            import random
            
            ticks = []
            current_price = base_price
            
            for i in range(count):
                # Simulate price movement
                change = random.gauss(0, volatility)
                current_price *= (1 + change)
                
                tick = MockTick.create(
                    ticker=ticker,
                    price=round(current_price, 2),
                    volume=random.randint(1000, 10000)
                )
                ticks.append(tick)
            
            return ticks
        
        @staticmethod
        def surge_scenario(ticker: str) -> List[MockTick]:
            """Generate a volume surge scenario"""
            normal_volume = 5000
            surge_volume = 50000
            
            # Normal trading
            ticks = [MockTick.create(ticker=ticker, volume=normal_volume) for _ in range(10)]
            
            # Volume surge
            surge_ticks = [MockTick.create(ticker=ticker, volume=surge_volume) for _ in range(3)]
            
            return ticks + surge_ticks
    
    return MarketDataGenerator()


# Helper functions
def assert_event_valid(event: BaseEvent):
    """Assert that an event meets basic validation requirements"""
    assert event.ticker is not None
    assert event.type is not None
    assert event.price > 0
    assert event.event_id is not None
    assert event.time > 0


def assert_timing_acceptable(duration: float, max_ms: int = 100):
    """Assert that operation completed within acceptable time"""
    max_seconds = max_ms / 1000.0
    assert duration <= max_seconds, f"Operation took {duration:.3f}s, max allowed {max_seconds:.3f}s"


# Pytest hooks for custom behavior
def pytest_configure(config):
    """Configure pytest with custom behavior"""
    # Add custom markers
    config.addinivalue_line("markers", "smoke: Quick smoke tests")
    config.addinivalue_line("markers", "regression: Regression tests")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on path"""
    for item in items:
        # Add unit marker to tests in unit/ directory
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        
        # Add integration marker to tests in integration/ directory
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        
        # Add performance marker to tests in performance/ directory
        elif "performance" in str(item.fspath):
            item.add_marker(pytest.mark.performance)