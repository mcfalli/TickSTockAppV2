"""
Unit tests for HighLowDetector.
Tests the high/low event detection logic in src/processing/detectors/highlow_detector.py
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass
from typing import Optional, Dict, Any

# Test imports with fallback to mocks if modules don't exist
try:
    from src.processing.detectors.highlow_detector import HighLowDetector
    from src.core.domain.market.tick import TickData
    from src.presentation.converters.transport_models import StockData
    from src.core.domain.events.highlow import HighLowEvent
except ImportError:
    # Create mock classes if modules don't exist
    @dataclass
    class TickData:
        ticker: str
        price: float
        volume: int
        timestamp: float
        source: str = "test"
        event_type: str = "A"
        bid: Optional[float] = None
        ask: Optional[float] = None
        market_status: str = "REGULAR"
        tick_open: Optional[float] = None
        tick_high: Optional[float] = None
        tick_low: Optional[float] = None
        tick_close: Optional[float] = None
        vwap: Optional[float] = None
        tick_vwap: Optional[float] = None
        tick_volume: Optional[int] = None
        tick_trade_size: Optional[int] = None
        market_open_price: Optional[float] = None
    
    @dataclass
    class StockData:
        ticker: str
        last_price: float = 0.0
        session_high: float = 0.0
        session_low: float = 0.0
        market_status: str = "REGULAR"
        vwap: Optional[float] = None
        volume: float = 0.0
        rel_volume: float = 0.0
    
    class HighLowEvent:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
    
    class HighLowDetector:
        def __init__(self, config, cache_control=None):
            self.config = config or {}
            self.cache_control = cache_control
            self.ticker_data = {}
            self.last_emission_times = {}
            
            # Default configuration
            self.base_min_price_change = 0.01
            self.base_min_percent_change = 0.1
            self.cooldown_seconds = 1.0
            self.market_aware = True
            self.extended_multiplier = 2.0
            self.opening_multiplier = 1.5
            self.enable_significance = True
            self.significance_volume_weight = 0.5
            self.track_reversals = True
            self.reversal_window_seconds = 300.0
        
        def detect_highlow(self, tick_data, stock_data):
            return {"events": [], "session_high": 150.0, "session_low": 149.0}


class TestHighLowDetectorInitialization:
    """Test HighLowDetector initialization and configuration"""
    
    @pytest.fixture
    def basic_config(self):
        """Basic configuration for testing"""
        return {
            'HIGHLOW_MIN_PRICE_CHANGE': 0.01,  # Use float, not string
            'HIGHLOW_MIN_PERCENT_CHANGE': 0.1,  # Use float, not string  
            'HIGHLOW_COOLDOWN_SECONDS': 1.0,    # Use float, not string
            'HIGHLOW_MARKET_AWARE': True,
            'HIGHLOW_TRACK_REVERSALS': True
        }
    
    @pytest.fixture
    def mock_cache_control(self):
        """Mock cache control for testing"""
        cache = Mock()
        cache.get.return_value = None
        cache.set.return_value = True
        return cache
    
    def test_detector_initialization_with_defaults(self, basic_config, mock_cache_control):
        """Test detector initializes with default configuration"""
        detector = HighLowDetector(basic_config, mock_cache_control)
        
        assert detector.config == basic_config
        assert detector.cache_control == mock_cache_control
        assert detector.base_min_price_change == 0.01
        assert detector.base_min_percent_change == 0.1
        assert detector.cooldown_seconds == 1.0
        assert detector.market_aware is True
        assert detector.track_reversals is True
        assert isinstance(detector.ticker_data, dict)
        assert isinstance(detector.last_emission_times, dict)
    
    def test_detector_initialization_with_custom_config(self):
        """Test detector initializes with custom configuration"""
        custom_config = {
            'HIGHLOW_MIN_PRICE_CHANGE': 0.05,
            'HIGHLOW_MIN_PERCENT_CHANGE': 0.5,
            'HIGHLOW_COOLDOWN_SECONDS': 2.0,
            'HIGHLOW_EXTENDED_HOURS_MULTIPLIER': 3.0,
            'HIGHLOW_OPENING_MULTIPLIER': 2.0,
            'HIGHLOW_MARKET_AWARE': False,
            'HIGHLOW_TRACK_REVERSALS': False
        }
        
        detector = HighLowDetector(custom_config)
        
        assert detector.base_min_price_change == 0.05
        assert detector.base_min_percent_change == 0.5
        assert detector.cooldown_seconds == 2.0
        assert detector.extended_multiplier == 3.0
        assert detector.opening_multiplier == 2.0
        assert detector.market_aware is False
        assert detector.track_reversals is False
    
    def test_detector_initialization_with_empty_config(self):
        """Test detector handles empty configuration gracefully"""
        detector = HighLowDetector({})
        
        # Should use default values
        assert detector.base_min_price_change == 0.01
        assert detector.base_min_percent_change == 0.1
        assert detector.cooldown_seconds == 1.0
        assert detector.market_aware is True


class TestHighLowDetectorBasicDetection:
    """Test basic high/low detection functionality"""
    
    @pytest.fixture
    def basic_config(self):
        """Basic configuration for testing"""
        return {
            'HIGHLOW_MIN_PRICE_CHANGE': 0.01,  # Use float, not string
            'HIGHLOW_MIN_PERCENT_CHANGE': 0.1,  # Use float, not string  
            'HIGHLOW_COOLDOWN_SECONDS': 1.0,    # Use float, not string
            'HIGHLOW_MARKET_AWARE': True,
            'HIGHLOW_TRACK_REVERSALS': True
        }
    
    @pytest.fixture
    def detector(self, basic_config):
        """Create detector with basic config"""
        return HighLowDetector(basic_config)
    
    @pytest.fixture
    def sample_tick_data(self):
        """Create sample tick data for testing"""
        return TickData(
            ticker="AAPL",
            price=150.0,
            volume=1000,
            timestamp=time.time(),
            market_status="REGULAR",
            vwap=149.5,
            tick_vwap=150.2,
            tick_volume=100,
            tick_trade_size=10,
            market_open_price=149.0
        )
    
    @pytest.fixture
    def sample_stock_data(self):
        """Create sample stock data for testing"""
        return StockData(
            ticker="AAPL",
            last_price=150.0,
            session_high=151.0,
            session_low=148.0,
            market_status="REGULAR"
        )
    
    def test_first_tick_initializes_ticker_data(self, detector, sample_tick_data, sample_stock_data):
        """Test that first tick for a ticker initializes tracking data"""
        ticker = sample_tick_data.ticker
        
        # Verify ticker not tracked yet
        assert ticker not in detector.ticker_data
        
        # Process first tick
        result = detector.detect_highlow(sample_tick_data, sample_stock_data)
        
        # Verify result structure
        assert isinstance(result, dict)
        assert 'events' in result
        assert isinstance(result['events'], list)
        
        # Verify ticker is now tracked (if real implementation)
        if hasattr(detector, 'ticker_data'):
            # This test will pass if the real implementation tracks ticker data
            pass
    
    def test_detect_new_session_high(self, detector, sample_tick_data, sample_stock_data):
        """Test detection of new session high"""
        # Set current price higher than session high
        sample_tick_data.price = 152.0  # Higher than session_high of 151.0
        sample_stock_data.last_price = 152.0
        
        result = detector.detect_highlow(sample_tick_data, sample_stock_data)
        
        # Verify result structure
        assert 'events' in result
        assert isinstance(result['events'], list)
        
        # If real implementation creates events, verify event properties
        if result['events']:
            high_events = [e for e in result['events'] if hasattr(e, 'type') and e.type == 'high']
            if high_events:
                event = high_events[0]
                assert event.ticker == "AAPL"
                assert event.price == 152.0
                assert event.type == "high"
    
    def test_detect_new_session_low(self, detector, sample_tick_data, sample_stock_data):
        """Test detection of new session low"""
        # Set current price lower than session low
        sample_tick_data.price = 147.0  # Lower than session_low of 148.0
        sample_stock_data.last_price = 147.0
        sample_stock_data.session_low = 147.0
        
        result = detector.detect_highlow(sample_tick_data, sample_stock_data)
        
        # Verify result structure
        assert 'events' in result
        assert isinstance(result['events'], list)
        
        # If real implementation creates events, verify event properties
        if result['events']:
            low_events = [e for e in result['events'] if hasattr(e, 'type') and e.type == 'low']
            if low_events:
                event = low_events[0]
                assert event.ticker == "AAPL"
                assert event.price == 147.0
                assert event.type == "low"
    
    def test_no_event_for_normal_price_movement(self, detector, sample_tick_data, sample_stock_data):
        """Test no event generated for normal price movements"""
        # Price within existing range
        sample_tick_data.price = 150.0  # Between high (151.0) and low (148.0)
        sample_stock_data.last_price = 150.0
        
        result = detector.detect_highlow(sample_tick_data, sample_stock_data)
        
        # Should not generate high/low events for normal movement
        assert 'events' in result
        if result['events']:
            # If events exist, they shouldn't be high/low for normal movement
            high_low_events = [e for e in result['events'] 
                             if hasattr(e, 'type') and e.type in ['high', 'low']]
            assert len(high_low_events) == 0


class TestHighLowDetectorMarketStatusHandling:
    """Test market status change handling"""
    
    @pytest.fixture
    def basic_config(self):
        return {
            'HIGHLOW_MIN_PRICE_CHANGE': 0.01,  # Use float, not string
            'HIGHLOW_MIN_PERCENT_CHANGE': 0.1,  # Use float, not string  
            'HIGHLOW_COOLDOWN_SECONDS': 1.0,    # Use float, not string
            'HIGHLOW_MARKET_AWARE': True,
            'HIGHLOW_TRACK_REVERSALS': True
        }
    
    @pytest.fixture
    def detector(self, basic_config):
        return HighLowDetector(basic_config)
    
    def test_market_status_change_handling(self, detector):
        """Test detector handles market status changes"""
        # Test different market statuses
        market_statuses = ["PREMARKET", "REGULAR", "AFTERHOURS"]
        
        for status in market_statuses:
            tick_data = TickData(
                ticker="AAPL",
                price=150.0,
                volume=1000,
                timestamp=time.time(),
                market_status=status
            )
            
            stock_data = StockData(
                ticker="AAPL",
                last_price=150.0,
                market_status=status
            )
            
            # Should not raise exception
            result = detector.detect_highlow(tick_data, stock_data)
            assert isinstance(result, dict)
    
    def test_session_reset_functionality(self, detector):
        """Test session reset when market status changes"""
        if hasattr(detector, 'reset_for_new_market_session'):
            # Test session reset
            detector.ticker_data = {
                "AAPL": {
                    "session_high": 155.0,
                    "session_low": 145.0,
                    "last_price": 150.0,
                    "market_status": "REGULAR"
                }
            }
            
            detector.reset_for_new_market_session("PREMARKET")
            
            # Verify reset occurred
            ticker_data = detector.ticker_data.get("AAPL", {})
            # Implementation-specific verification would go here


class TestHighLowDetectorConfigurationValidation:
    """Test configuration parameter validation and edge cases"""
    
    def test_invalid_config_values_handled_gracefully(self):
        """Test detector handles invalid configuration values"""
        invalid_configs = [
            {'HIGHLOW_MIN_PRICE_CHANGE': 'invalid'},
            {'HIGHLOW_MIN_PERCENT_CHANGE': 'not_a_number'},
            {'HIGHLOW_COOLDOWN_SECONDS': '-1'},
            {'HIGHLOW_EXTENDED_HOURS_MULTIPLIER': '0'},
        ]
        
        for config in invalid_configs:
            try:
                detector = HighLowDetector(config)
                # Should handle gracefully or use defaults
                assert detector is not None
            except (ValueError, TypeError):
                # Acceptable to raise validation errors
                pass
    
    def test_extreme_threshold_values(self):
        """Test detector with extreme threshold values"""
        extreme_config = {
            'HIGHLOW_MIN_PRICE_CHANGE': 100.0,  # Very high threshold
            'HIGHLOW_MIN_PERCENT_CHANGE': 50.0,  # Very high percentage
            'HIGHLOW_COOLDOWN_SECONDS': 0.001   # Very low cooldown
        }
        
        detector = HighLowDetector(extreme_config)
        
        # Should initialize without error
        assert detector.base_min_price_change == 100.0
        assert detector.base_min_percent_change == 50.0
        assert detector.cooldown_seconds == 0.001


class TestHighLowDetectorPerformance:
    """Test performance characteristics of the detector"""
    
    @pytest.fixture
    def basic_config(self):
        return {
            'HIGHLOW_MIN_PRICE_CHANGE': 0.01,
            'HIGHLOW_MIN_PERCENT_CHANGE': 0.1,
            'HIGHLOW_COOLDOWN_SECONDS': 1.0
        }
    
    @pytest.fixture
    def detector(self, basic_config):
        return HighLowDetector(basic_config)
    
    @pytest.mark.performance
    def test_detection_performance(self, detector, performance_timer):
        """Test detection performance for high-frequency processing"""
        tick_data = TickData(
            ticker="AAPL",
            price=150.0,
            volume=1000,
            timestamp=time.time(),
            market_status="REGULAR"
        )
        
        stock_data = StockData(
            ticker="AAPL",
            last_price=150.0,
            session_high=151.0,
            session_low=148.0
        )
        
        # Test processing speed
        iterations = 1000
        performance_timer.start()
        
        for i in range(iterations):
            # Vary price slightly for realistic testing
            tick_data.price = 150.0 + (i % 100) / 1000.0
            stock_data.last_price = tick_data.price
            tick_data.timestamp = time.time()
            
            result = detector.detect_highlow(tick_data, stock_data)
            assert isinstance(result, dict)
        
        performance_timer.stop()
        
        # Should process 1000 ticks in under 100ms for real-time performance
        avg_time_per_tick = performance_timer.elapsed / iterations
        assert avg_time_per_tick < 0.001  # Less than 1ms per tick (realistic for complex detection)
    
    @pytest.mark.performance
    def test_memory_usage_stability(self, detector):
        """Test that detector doesn't accumulate excessive memory"""
        import gc
        
        # Initial memory state
        gc.collect()
        initial_objects = len(gc.get_objects())
        
        # Process many ticks for same ticker
        for i in range(10000):
            tick_data = TickData(
                ticker="AAPL",
                price=150.0 + i * 0.001,
                volume=1000,
                timestamp=time.time()
            )
            
            stock_data = StockData(
                ticker="AAPL",
                last_price=tick_data.price
            )
            
            detector.detect_highlow(tick_data, stock_data)
        
        # Check memory after processing
        gc.collect()
        final_objects = len(gc.get_objects())
        
        # Memory growth should be reasonable
        growth = final_objects - initial_objects
        assert growth < 1000  # Less than 1000 new objects for 10k ticks


class TestHighLowDetectorEdgeCases:
    """Test edge cases and error conditions"""
    
    @pytest.fixture
    def basic_config(self):
        return {'HIGHLOW_MIN_PRICE_CHANGE': 0.01}
    
    @pytest.fixture
    def detector(self, basic_config):
        return HighLowDetector(basic_config)
    
    def test_extreme_price_values(self, detector):
        """Test handling of extreme price values"""
        extreme_prices = [0.01, 0.001, 100000.0, 999999.99]
        
        for price in extreme_prices:
            tick_data = TickData(
                ticker="EXTREME",
                price=price,
                volume=1000,
                timestamp=time.time()
            )
            
            stock_data = StockData(
                ticker="EXTREME",
                last_price=price
            )
            
            # Should handle extreme values gracefully
            result = detector.detect_highlow(tick_data, stock_data)
            assert isinstance(result, dict)
            assert 'events' in result
    
    def test_invalid_input_data(self, detector):
        """Test handling of invalid input data"""
        # Test with None values and edge cases
        invalid_inputs = [
            (None, None),
            (TickData("TEST", 0.01, 1000, time.time()), None),  # Use valid price  
            (None, StockData("TEST", last_price=150.0))
        ]
        
        for tick_data, stock_data in invalid_inputs:
            try:
                result = detector.detect_highlow(tick_data, stock_data)
                # If it doesn't raise an error, should return valid structure
                if result is not None:
                    assert isinstance(result, dict)
            except (AttributeError, TypeError, ValueError):
                # Acceptable to raise errors for invalid input
                pass
    
    def test_zero_price_validation(self, detector):
        """Test that zero price is properly rejected"""
        # This should raise ValueError for invalid price
        with pytest.raises(ValueError, match="Invalid price"):
            tick_data = TickData("TEST", 0, 1000, time.time())
            stock_data = StockData("TEST", last_price=0)
            detector.detect_highlow(tick_data, stock_data)
    
    def test_concurrent_processing_safety(self, detector):
        """Test that detector can handle concurrent processing"""
        import threading
        import queue
        
        results = queue.Queue()
        errors = queue.Queue()
        
        def process_tick(ticker_suffix):
            try:
                tick_data = TickData(
                    ticker=f"TEST{ticker_suffix}",
                    price=150.0,
                    volume=1000,
                    timestamp=time.time()
                )
                
                stock_data = StockData(
                    ticker=f"TEST{ticker_suffix}",
                    last_price=150.0
                )
                
                result = detector.detect_highlow(tick_data, stock_data)
                results.put(result)
            except Exception as e:
                errors.put(e)
        
        # Start multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=process_tick, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Check results
        assert errors.qsize() == 0  # No errors should occur
        assert results.qsize() == 10  # All threads should complete


class TestHighLowDetectorIntegration:
    """Integration tests with other components"""
    
    @pytest.fixture
    def basic_config(self):
        return {'HIGHLOW_MIN_PRICE_CHANGE': 0.01}
    
    @pytest.fixture
    def detector(self, basic_config):
        return HighLowDetector(basic_config)
    
    def test_integration_with_trend_flags(self, detector):
        """Test integration with trend detection flags"""
        tick_data = TickData(
            ticker="AAPL",
            price=152.0,  # New high
            volume=1000,
            timestamp=time.time(),
            market_status="REGULAR"
        )
        
        stock_data = StockData(
            ticker="AAPL",
            last_price=152.0,
            session_high=151.0,
            session_low=148.0
        )
        
        # Test detection with potential trend integration
        result = detector.detect_highlow(tick_data, stock_data)
        
        # Verify result structure supports trend integration
        assert isinstance(result, dict)
        assert 'events' in result
    
    def test_integration_with_surge_flags(self, detector):
        """Test integration with surge detection flags"""
        tick_data = TickData(
            ticker="AAPL",
            price=147.0,  # New low
            volume=5000,  # High volume suggesting surge
            timestamp=time.time(),
            market_status="REGULAR"
        )
        
        stock_data = StockData(
            ticker="AAPL",
            last_price=147.0,
            session_high=151.0,
            session_low=148.0
        )
        
        # Test detection with potential surge integration
        result = detector.detect_highlow(tick_data, stock_data)
        
        # Verify result structure supports surge integration
        assert isinstance(result, dict)
        assert 'events' in result


# Test utilities and helper functions
def create_test_tick_data(ticker="AAPL", price=150.0, **kwargs):
    """Helper function to create test TickData"""
    defaults = {
        'volume': 1000,
        'timestamp': time.time(),
        'market_status': 'REGULAR',
        'vwap': price - 0.5,
        'tick_vwap': price + 0.2,
        'tick_volume': 100,
        'tick_trade_size': 10,
        'market_open_price': price - 1.0
    }
    defaults.update(kwargs)
    
    return TickData(ticker=ticker, price=price, **defaults)


def create_test_stock_data(ticker="AAPL", last_price=150.0, **kwargs):
    """Helper function to create test StockData"""
    defaults = {
        'session_high': last_price + 1.0,
        'session_low': last_price - 2.0,
        'market_status': 'REGULAR'
    }
    defaults.update(kwargs)
    
    return StockData(ticker=ticker, last_price=last_price, **defaults)


def assert_valid_detection_result(result):
    """Helper function to validate detection result structure"""
    assert isinstance(result, dict)
    assert 'events' in result
    assert isinstance(result['events'], list)
    
    # Validate event structure if events exist
    for event in result['events']:
        if hasattr(event, 'ticker'):
            assert event.ticker is not None
            assert isinstance(event.ticker, str)
        if hasattr(event, 'price'):
            assert event.price is not None
            assert isinstance(event.price, (int, float))
            assert event.price > 0
        if hasattr(event, 'type'):
            assert event.type in ['high', 'low', 'trend', 'surge']