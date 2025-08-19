"""
Unit tests for core event classes.
Tests the domain event models in src/core/domain/events/
"""

import pytest
import time
from unittest.mock import patch

from src.core.domain.events.base import BaseEvent
from src.core.domain.events.highlow import HighLowEvent
from src.core.domain.events.surge import SurgeEvent
from src.core.domain.events.trend import TrendEvent


class TestBaseEvent:
    """Test the abstract BaseEvent class behavior"""
    
    def test_base_event_cannot_be_instantiated_directly(self):
        """BaseEvent is abstract and cannot be instantiated"""
        with pytest.raises(TypeError):
            BaseEvent(ticker="AAPL", type="test", price=150.0)
    
    def test_event_id_generation(self, event_builder):
        """Event IDs should be unique and follow expected format"""
        event1 = event_builder.high_low_event()
        event2 = event_builder.high_low_event()
        
        # IDs should be different
        assert event1.event_id != event2.event_id
        
        # ID should contain timestamp and be non-empty
        assert event1.event_id is not None
        assert len(event1.event_id) > 0
        assert "_" in event1.event_id  # timestamp_uuid format
    
    def test_time_defaults_to_current_time(self, event_builder):
        """Event time should default to current timestamp"""
        before = time.time()
        event = event_builder.high_low_event()
        after = time.time()
        
        assert before <= event.time <= after


class TestHighLowEvent:
    """Test HighLowEvent creation and validation"""
    
    def test_create_valid_high_event(self, event_builder):
        """Create a valid high event"""
        event = event_builder.high_low_event(
            ticker="AAPL",
            price=150.25,
            event_type="high"
        )
        
        assert event.ticker == "AAPL"
        assert event.type == "high"
        assert event.price == 150.25
        assert event.direction == "up"
    
    def test_create_valid_low_event(self, event_builder):
        """Create a valid low event"""
        event = event_builder.high_low_event(
            ticker="GOOGL",
            price=2500.75,
            event_type="low"
        )
        
        assert event.ticker == "GOOGL"
        assert event.type == "low"
        assert event.price == 2500.75
        assert event.direction == "down"
    
    def test_validation_requires_positive_price(self):
        """Event validation should reject negative prices"""
        with pytest.raises(ValueError, match="Invalid price"):
            HighLowEvent(
                ticker="AAPL",
                type="high",
                price=-10.0
            )
    
    def test_validation_requires_ticker(self):
        """Event validation should reject empty ticker"""
        with pytest.raises(ValueError, match="Empty ticker"):
            HighLowEvent(
                ticker="",
                type="high",
                price=150.0
            )
    
    def test_validation_requires_event_type(self):
        """Event validation should reject empty event type"""
        with pytest.raises(ValueError, match="Empty event type"):
            HighLowEvent(
                ticker="AAPL",
                type="",
                price=150.0
            )
    
    def test_to_transport_dict_contains_required_fields(self, event_builder):
        """Transport dict should contain all required fields for WebSocket"""
        event = event_builder.high_low_event()
        transport = event.to_transport_dict()
        
        required_fields = ['ticker', 'type', 'price', 'time', 'event_id', 'direction']
        for field in required_fields:
            assert field in transport
    
    def test_to_transport_dict_serializable(self, event_builder):
        """Transport dict should be JSON serializable"""
        import json
        
        event = event_builder.high_low_event()
        transport = event.to_transport_dict()
        
        # Should not raise exception
        json_str = json.dumps(transport)
        assert isinstance(json_str, str)
        assert len(json_str) > 0


class TestSurgeEvent:
    """Test SurgeEvent creation and validation"""
    
    def test_create_valid_surge_event(self, event_builder):
        """Create a valid surge event"""
        event = event_builder.surge_event(
            ticker="TSLA",
            price=800.50,
            volume=5000000.0,
            volume_ratio=4.2
        )
        
        assert event.ticker == "TSLA"
        assert event.type == "surge"
        assert event.price == 800.50
        assert event.volume == 5000000.0
        assert event.volume_ratio == 4.2
    
    def test_volume_ratio_calculated_correctly(self):
        """Volume ratio should be calculated from current vs average volume"""
        current_volume = 1000000.0
        avg_volume = 250000.0
        expected_ratio = current_volume / avg_volume
        
        event = SurgeEvent(
            ticker="AAPL",
            type="surge",
            price=150.0,
            volume=current_volume,
            avg_volume=avg_volume
        )
        
        assert abs(event.volume_ratio - expected_ratio) < 0.01
    
    def test_surge_validation_requires_positive_volume(self):
        """Surge events should reject negative volume"""
        with pytest.raises(ValueError):
            SurgeEvent(
                ticker="AAPL",
                type="surge",
                price=150.0,
                volume=-1000.0
            )
    
    def test_to_transport_dict_includes_volume_data(self, event_builder):
        """Surge transport dict should include volume-specific fields"""
        event = event_builder.surge_event()
        transport = event.to_transport_dict()
        
        volume_fields = ['volume', 'volume_ratio']
        for field in volume_fields:
            assert field in transport


class TestTrendEvent:
    """Test TrendEvent creation and validation"""
    
    def test_create_valid_trend_event(self, event_builder):
        """Create a valid trend event"""
        event = event_builder.trend_event(
            ticker="MSFT",
            price=300.75,
            direction="up",
            period=180
        )
        
        assert event.ticker == "MSFT"
        assert event.type == "trend"
        assert event.price == 300.75
        assert event.direction == "up"
        assert event.period == 180
    
    def test_trend_direction_validation(self):
        """Trend direction should be 'up' or 'down'"""
        # Valid directions
        for direction in ["up", "down"]:
            event = TrendEvent(
                ticker="AAPL",
                type="trend",
                price=150.0,
                direction=direction,
                period=180
            )
            assert event.direction == direction
    
    def test_period_validation(self):
        """Trend period should be positive"""
        with pytest.raises(ValueError):
            TrendEvent(
                ticker="AAPL",
                type="trend",
                price=150.0,
                direction="up",
                period=-60
            )
    
    def test_to_transport_dict_includes_trend_data(self, event_builder):
        """Trend transport dict should include trend-specific fields"""
        event = event_builder.trend_event()
        transport = event.to_transport_dict()
        
        trend_fields = ['direction', 'period']
        for field in trend_fields:
            assert field in transport


class TestEventPerformance:
    """Performance tests for event operations"""
    
    @pytest.mark.performance
    def test_event_creation_performance(self, event_builder, performance_timer):
        """Event creation should be fast (< 1ms per event)"""
        iterations = 1000
        
        performance_timer.start()
        for _ in range(iterations):
            event_builder.high_low_event()
        performance_timer.stop()
        
        avg_time_per_event = performance_timer.elapsed / iterations
        assert avg_time_per_event < 0.001  # Less than 1ms per event
    
    @pytest.mark.performance  
    def test_transport_dict_performance(self, event_builder, performance_timer):
        """Transport dict generation should be fast"""
        events = [event_builder.high_low_event() for _ in range(100)]
        
        performance_timer.start()
        for event in events:
            event.to_transport_dict()
        performance_timer.stop()
        
        avg_time_per_conversion = performance_timer.elapsed / len(events)
        assert avg_time_per_conversion < 0.0001  # Less than 0.1ms per conversion


class TestEventEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_event_with_extreme_values(self):
        """Events should handle extreme but valid values"""
        # Very high price
        high_price_event = HighLowEvent(
            ticker="BRK.A",
            type="high",
            price=500000.0
        )
        assert high_price_event.price == 500000.0
        
        # Very low price (penny stock)
        low_price_event = HighLowEvent(
            ticker="PENNY",
            type="low",
            price=0.01
        )
        assert low_price_event.price == 0.01
    
    def test_event_with_unicode_ticker(self):
        """Events should handle international tickers"""
        event = HighLowEvent(
            ticker="TSM.TW",  # Taiwan Semiconductor
            type="high",
            price=100.0
        )
        assert event.ticker == "TSM.TW"
    
    def test_concurrent_event_creation(self, event_builder):
        """Event IDs should be unique even with concurrent creation"""
        import threading
        import queue
        
        event_ids = queue.Queue()
        
        def create_events():
            for _ in range(10):
                event = event_builder.high_low_event()
                event_ids.put(event.event_id)
        
        # Create events in multiple threads
        threads = [threading.Thread(target=create_events) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        
        # Collect all IDs
        all_ids = []
        while not event_ids.empty():
            all_ids.append(event_ids.get())
        
        # All IDs should be unique
        assert len(all_ids) == len(set(all_ids))