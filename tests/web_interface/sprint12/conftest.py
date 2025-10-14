# ==========================================================================
# TICKSTOCK SPRINT 12 DASHBOARD TEST FIXTURES
# ==========================================================================
# PURPOSE: Shared fixtures and utilities for Sprint 12 dashboard testing
# COMPONENTS: Mock data, API clients, WebSocket simulation
# ==========================================================================

import time
from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest

# ==========================================================================
# MOCK DATA FIXTURES
# ==========================================================================

@pytest.fixture
def mock_symbols_data():
    """Mock symbol search data for testing."""
    return [
        {
            "symbol": "AAPL",
            "name": "Apple Inc.",
            "market_cap": 3000000000000,
            "sector": "Technology"
        },
        {
            "symbol": "GOOGL",
            "name": "Alphabet Inc.",
            "market_cap": 1800000000000,
            "sector": "Technology"
        },
        {
            "symbol": "MSFT",
            "name": "Microsoft Corporation",
            "market_cap": 2800000000000,
            "sector": "Technology"
        },
        {
            "symbol": "TSLA",
            "name": "Tesla, Inc.",
            "market_cap": 800000000000,
            "sector": "Consumer Discretionary"
        },
        {
            "symbol": "NVDA",
            "name": "NVIDIA Corporation",
            "market_cap": 1200000000000,
            "sector": "Technology"
        }
    ]

@pytest.fixture
def mock_watchlist_data():
    """Mock watchlist data for testing."""
    return [
        {
            "symbol": "AAPL",
            "name": "Apple Inc.",
            "last_price": 175.50,
            "change": 2.30,
            "change_percent": 1.33,
            "volume": 45000000
        },
        {
            "symbol": "GOOGL",
            "name": "Alphabet Inc.",
            "last_price": 142.80,
            "change": -1.20,
            "change_percent": -0.83,
            "volume": 28000000
        },
        {
            "symbol": "MSFT",
            "name": "Microsoft Corporation",
            "last_price": 420.15,
            "change": 5.45,
            "change_percent": 1.31,
            "volume": 32000000
        }
    ]

@pytest.fixture
def mock_chart_data():
    """Mock OHLCV chart data for testing."""
    base_time = datetime.now() - timedelta(days=30)
    data = []

    for i in range(30):
        timestamp = base_time + timedelta(days=i)
        open_price = 150.0 + (i * 0.5)
        high_price = open_price + 2.5
        low_price = open_price - 1.5
        close_price = open_price + 0.75
        volume = 25000000 + (i * 100000)

        data.append({
            "timestamp": timestamp.isoformat(),
            "open": round(open_price, 2),
            "high": round(high_price, 2),
            "low": round(low_price, 2),
            "close": round(close_price, 2),
            "volume": volume
        })

    return data

@pytest.fixture
def mock_real_time_price():
    """Mock real-time price update data."""
    return {
        "symbol": "AAPL",
        "price": 176.85,
        "change": 3.65,
        "change_percent": 2.11,
        "volume": 47500000,
        "timestamp": datetime.now().isoformat()
    }

# ==========================================================================
# API CLIENT MOCKS
# ==========================================================================

@pytest.fixture
def mock_api_client():
    """Mock API client for testing API interactions."""
    client = Mock()

    # Configure default successful responses
    client.get_watchlist.return_value = {
        "success": True,
        "symbols": []
    }

    client.add_to_watchlist.return_value = {
        "success": True,
        "message": "Symbol added successfully"
    }

    client.remove_from_watchlist.return_value = {
        "success": True,
        "message": "Symbol removed successfully"
    }

    client.get_symbols.return_value = {
        "success": True,
        "symbols": []
    }

    client.get_chart_data.return_value = {
        "success": True,
        "chart_data": []
    }

    return client

@pytest.fixture
def mock_websocket():
    """Mock WebSocket client for testing real-time updates."""
    socket = Mock()
    socket.emit = Mock()
    socket.on = Mock()
    socket.connected = True
    return socket

# ==========================================================================
# PERFORMANCE TESTING UTILITIES
# ==========================================================================

@pytest.fixture
def performance_timer():
    """Timer for measuring performance in tests."""
    class PerformanceTimer:
        def __init__(self):
            self.start_time = None
            self.end_time = None

        def start(self):
            self.start_time = time.perf_counter()

        def stop(self):
            self.end_time = time.perf_counter()

        @property
        def elapsed(self):
            if self.start_time and self.end_time:
                return (self.end_time - self.start_time) * 1000  # Return in milliseconds
            return None

        @property
        def elapsed_seconds(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None

    return PerformanceTimer()

# ==========================================================================
# ERROR SIMULATION FIXTURES
# ==========================================================================

@pytest.fixture
def mock_api_error_responses():
    """Mock API error responses for testing error handling."""
    return {
        "network_error": {"error": "Network connection failed"},
        "server_error": {"error": "Internal server error", "status": 500},
        "validation_error": {"error": "Invalid symbol format", "status": 400},
        "not_found": {"error": "Symbol not found", "status": 404},
        "unauthorized": {"error": "Authentication required", "status": 401}
    }

@pytest.fixture
def mock_slow_api():
    """Mock slow API responses for testing performance degradation."""
    def slow_response(delay_ms=1000):
        def wrapper(*args, **kwargs):
            time.sleep(delay_ms / 1000.0)
            return {"success": True, "data": []}
        return wrapper
    return slow_response

# ==========================================================================
# TEST DATA GENERATION UTILITIES
# ==========================================================================

@pytest.fixture
def watchlist_generator():
    """Generator for creating test watchlist data with various scenarios."""
    def generate_watchlist(count=5, with_changes=True):
        symbols = ["AAPL", "GOOGL", "MSFT", "TSLA", "NVDA", "AMZN", "META", "NFLX", "AMD", "INTC"]
        companies = [
            "Apple Inc.", "Alphabet Inc.", "Microsoft Corporation", "Tesla, Inc.",
            "NVIDIA Corporation", "Amazon.com Inc.", "Meta Platforms Inc.",
            "Netflix Inc.", "Advanced Micro Devices Inc.", "Intel Corporation"
        ]

        watchlist = []
        for i in range(min(count, len(symbols))):
            base_price = 100 + (i * 25)
            change = (i - count//2) * 2.5 if with_changes else 0
            change_percent = (change / base_price) * 100 if base_price > 0 else 0

            watchlist.append({
                "symbol": symbols[i],
                "name": companies[i],
                "last_price": base_price + change,
                "change": change,
                "change_percent": change_percent,
                "volume": 25000000 + (i * 5000000)
            })

        return watchlist

    return generate_watchlist

@pytest.fixture
def chart_data_generator():
    """Generator for creating test chart data with various patterns."""
    def generate_chart_data(days=30, pattern="uptrend", volatility=0.05):
        base_time = datetime.now() - timedelta(days=days)
        data = []
        base_price = 150.0

        for i in range(days):
            timestamp = base_time + timedelta(days=i)

            # Apply pattern
            if pattern == "uptrend":
                trend_factor = 1 + (i * 0.01)
            elif pattern == "downtrend":
                trend_factor = 1 - (i * 0.01)
            else:  # sideways
                trend_factor = 1 + (0.005 * (i % 4 - 2))

            # Add volatility
            import random
            random_factor = 1 + (random.random() - 0.5) * volatility

            open_price = base_price * trend_factor * random_factor
            high_price = open_price * (1 + volatility/2)
            low_price = open_price * (1 - volatility/2)
            close_price = open_price * (1 + (random.random() - 0.5) * volatility/2)
            volume = random.randint(20000000, 80000000)

            data.append({
                "timestamp": timestamp.isoformat(),
                "open": round(open_price, 2),
                "high": round(high_price, 2),
                "low": round(low_price, 2),
                "close": round(close_price, 2),
                "volume": volume
            })

        return data

    return generate_chart_data
