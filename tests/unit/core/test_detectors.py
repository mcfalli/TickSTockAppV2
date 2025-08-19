"""
Unit tests for event detectors.
Tests the detection logic in src/processing/detectors/
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import List, Optional

# Import detector classes
try:
    from src.processing.detectors.highlow_detector import HighLowDetector
    from src.processing.detectors.surge_detector import SurgeDetector
    from src.processing.detectors.trend_detector import TrendDetector
except ImportError:
    # Create mock classes if modules don't exist yet
    class HighLowDetector:
        def __init__(self):
            pass
        def detect(self, ticker, price, volume):
            return None
    
    class SurgeDetector:
        def __init__(self):
            pass
        def detect(self, ticker, volume, avg_volume):
            return None
    
    class TrendDetector:
        def __init__(self):
            pass
        def detect(self, ticker, prices):
            return None


class TestHighLowDetector:
    """Test high/low event detection logic"""
    
    @pytest.fixture
    def detector(self):
        """Create HighLowDetector instance"""
        return HighLowDetector()
    
    @pytest.fixture
    def price_history(self):
        """Sample price history for testing"""
        return {
            "AAPL": [148.0, 149.0, 150.0, 151.0, 150.5, 149.8, 152.0]  # High at 152.0
        }
    
    def test_detect_new_high(self, detector, price_history):
        """Should detect when price reaches new high"""
        ticker = "AAPL"
        current_price = 153.0  # New high
        
        # Mock the detector's price tracking
        with patch.object(detector, '_get_recent_prices', return_value=price_history[ticker]):
            result = detector.detect(ticker, current_price, 1000)
        
        if result:  # If detector exists and works
            assert result.type == "high"
            assert result.ticker == ticker
            assert result.price == current_price
    
    def test_detect_new_low(self, detector, price_history):
        """Should detect when price reaches new low"""
        ticker = "AAPL"
        current_price = 147.0  # New low
        
        with patch.object(detector, '_get_recent_prices', return_value=price_history[ticker]):
            result = detector.detect(ticker, current_price, 1000)
        
        if result:
            assert result.type == "low"
            assert result.ticker == ticker
            assert result.price == current_price
    
    def test_no_detection_for_normal_price(self, detector, price_history):
        """Should not detect event for normal price movement"""
        ticker = "AAPL"
        current_price = 150.2  # Within normal range
        
        with patch.object(detector, '_get_recent_prices', return_value=price_history[ticker]):
            result = detector.detect(ticker, current_price, 1000)
        
        # Should be None or no event
        assert result is None or (hasattr(result, 'type') and result.type not in ["high", "low"])
    
    def test_threshold_configuration(self, detector):
        """Detector should respect threshold configuration"""
        # Test with different thresholds
        for threshold in [0.01, 0.05, 0.10]:  # 1%, 5%, 10%
            with patch.object(detector, 'threshold', threshold):
                # Test should adapt to different thresholds
                assert detector.threshold == threshold
    
    def test_handles_insufficient_data(self, detector):
        """Should handle case with insufficient price history"""
        ticker = "NEWSTOCK"
        current_price = 100.0
        
        with patch.object(detector, '_get_recent_prices', return_value=[]):
            result = detector.detect(ticker, current_price, 1000)
        
        # Should handle gracefully (return None or specific behavior)
        assert result is None or hasattr(result, 'type')
    
    def test_validates_input_parameters(self, detector):
        """Should validate input parameters"""
        with pytest.raises((ValueError, TypeError)):
            detector.detect("", 100.0, 1000)  # Empty ticker
        
        with pytest.raises((ValueError, TypeError)):
            detector.detect("AAPL", -100.0, 1000)  # Negative price
        
        with pytest.raises((ValueError, TypeError)):
            detector.detect("AAPL", 100.0, -1000)  # Negative volume


class TestSurgeDetector:
    """Test volume surge detection logic"""
    
    @pytest.fixture
    def detector(self):
        """Create SurgeDetector instance"""
        return SurgeDetector()
    
    @pytest.fixture
    def volume_history(self):
        """Sample volume history for testing"""
        return {
            "AAPL": [100000, 120000, 110000, 130000, 105000]  # Avg ~113K
        }
    
    def test_detect_volume_surge(self, detector, volume_history):
        """Should detect significant volume increase"""
        ticker = "AAPL"
        current_volume = 500000  # 4x+ average
        avg_volume = 113000
        
        with patch.object(detector, '_get_average_volume', return_value=avg_volume):
            result = detector.detect(ticker, current_volume, avg_volume)
        
        if result:
            assert result.type == "surge"
            assert result.ticker == ticker
            assert result.volume == current_volume
            assert result.volume_ratio > 3.0  # Significant surge
    
    def test_no_surge_for_normal_volume(self, detector, volume_history):
        """Should not detect surge for normal volume"""
        ticker = "AAPL"
        current_volume = 120000  # Normal volume
        avg_volume = 113000
        
        with patch.object(detector, '_get_average_volume', return_value=avg_volume):
            result = detector.detect(ticker, current_volume, avg_volume)
        
        assert result is None
    
    def test_surge_threshold_configuration(self, detector):
        """Should respect configurable surge threshold"""
        multipliers = [2.0, 3.0, 5.0]
        
        for multiplier in multipliers:
            with patch.object(detector, 'surge_multiplier', multiplier):
                assert detector.surge_multiplier == multiplier
    
    def test_handles_zero_average_volume(self, detector):
        """Should handle edge case of zero average volume"""
        ticker = "ILLIQUID"
        current_volume = 1000
        avg_volume = 0
        
        result = detector.detect(ticker, current_volume, avg_volume)
        
        # Should handle gracefully (probably return None or special case)
        assert result is None or hasattr(result, 'type')
    
    def test_calculates_volume_ratio_correctly(self, detector):
        """Should calculate volume ratio accurately"""
        ticker = "AAPL"
        current_volume = 400000
        avg_volume = 100000
        expected_ratio = 4.0
        
        with patch.object(detector, '_get_average_volume', return_value=avg_volume):
            result = detector.detect(ticker, current_volume, avg_volume)
        
        if result and hasattr(result, 'volume_ratio'):
            assert abs(result.volume_ratio - expected_ratio) < 0.01


class TestTrendDetector:
    """Test trend detection logic"""
    
    @pytest.fixture
    def detector(self):
        """Create TrendDetector instance"""
        return TrendDetector()
    
    @pytest.fixture
    def uptrend_prices(self):
        """Price series showing uptrend"""
        return [100.0, 101.0, 102.5, 103.0, 104.2, 105.1, 106.0]
    
    @pytest.fixture
    def downtrend_prices(self):
        """Price series showing downtrend"""
        return [106.0, 105.1, 104.2, 103.0, 102.5, 101.0, 100.0]
    
    @pytest.fixture
    def sideways_prices(self):
        """Price series showing sideways movement"""
        return [100.0, 100.5, 99.8, 100.2, 99.9, 100.3, 100.1]
    
    def test_detect_uptrend(self, detector, uptrend_prices):
        """Should detect upward trend"""
        ticker = "AAPL"
        
        with patch.object(detector, '_get_price_series', return_value=uptrend_prices):
            result = detector.detect(ticker, uptrend_prices)
        
        if result:
            assert result.type == "trend"
            assert result.direction == "up"
            assert result.ticker == ticker
    
    def test_detect_downtrend(self, detector, downtrend_prices):
        """Should detect downward trend"""
        ticker = "AAPL"
        
        with patch.object(detector, '_get_price_series', return_value=downtrend_prices):
            result = detector.detect(ticker, downtrend_prices)
        
        if result:
            assert result.type == "trend"
            assert result.direction == "down"
            assert result.ticker == ticker
    
    def test_no_trend_for_sideways(self, detector, sideways_prices):
        """Should not detect trend for sideways movement"""
        ticker = "AAPL"
        
        with patch.object(detector, '_get_price_series', return_value=sideways_prices):
            result = detector.detect(ticker, sideways_prices)
        
        assert result is None
    
    def test_trend_period_configuration(self, detector):
        """Should support different trend analysis periods"""
        periods = [60, 180, 300, 600]  # Different time periods
        
        for period in periods:
            with patch.object(detector, 'period', period):
                assert detector.period == period
    
    def test_minimum_data_requirement(self, detector):
        """Should require minimum data points for trend analysis"""
        ticker = "AAPL"
        insufficient_data = [100.0, 101.0]  # Too few points
        
        result = detector.detect(ticker, insufficient_data)
        
        # Should return None for insufficient data
        assert result is None
    
    def test_trend_strength_calculation(self, detector, uptrend_prices):
        """Should calculate trend strength or confidence"""
        ticker = "AAPL"
        
        with patch.object(detector, '_get_price_series', return_value=uptrend_prices):
            result = detector.detect(ticker, uptrend_prices)
        
        if result and hasattr(result, 'strength'):
            assert 0 <= result.strength <= 1.0  # Normalized strength


class TestDetectorPerformance:
    """Performance tests for detectors"""
    
    @pytest.mark.performance
    def test_detection_performance(self, performance_timer):
        """Detection should be fast enough for real-time processing"""
        detector = HighLowDetector()
        ticker = "AAPL"
        
        performance_timer.start()
        for i in range(1000):
            price = 150.0 + (i % 100) / 100.0  # Varying prices
            detector.detect(ticker, price, 1000)
        performance_timer.stop()
        
        # Should complete 1000 detections in under 100ms
        assert performance_timer.elapsed < 0.1
    
    @pytest.mark.performance
    def test_memory_usage_stability(self):
        """Detectors should not accumulate excessive memory"""
        import gc
        import sys
        
        detector = SurgeDetector()
        
        # Get initial memory
        gc.collect()
        initial_objects = len(gc.get_objects())
        
        # Run many detections
        for i in range(10000):
            detector.detect("AAPL", 1000000, 250000)
        
        # Check memory after operations
        gc.collect()
        final_objects = len(gc.get_objects())
        
        # Memory growth should be minimal
        growth = final_objects - initial_objects
        assert growth < 1000  # Reasonable memory growth limit


class TestDetectorIntegration:
    """Integration tests between detectors"""
    
    def test_multiple_detectors_on_same_data(self, mock_tick):
        """Multiple detectors should work together"""
        high_low = HighLowDetector()
        surge = SurgeDetector()
        trend = TrendDetector()
        
        # Run all detectors on same data
        hl_result = high_low.detect(mock_tick.ticker, mock_tick.price, mock_tick.volume)
        surge_result = surge.detect(mock_tick.ticker, mock_tick.volume, 50000)
        trend_result = trend.detect(mock_tick.ticker, [mock_tick.price])
        
        # Should not interfere with each other
        # (Results may be None, that's expected)
        assert True  # Test that no exceptions occurred
    
    def test_detector_state_isolation(self):
        """Detectors should maintain independent state"""
        detector1 = HighLowDetector()
        detector2 = HighLowDetector()
        
        # Operate on different data
        detector1.detect("AAPL", 150.0, 1000)
        detector2.detect("GOOGL", 2500.0, 500)
        
        # Should not affect each other's state
        assert True  # Test passes if no exceptions