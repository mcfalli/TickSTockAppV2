"""
Unit tests for event creators in Sprint 106: Data Type Handlers

Tests the event creation logic for all channel types including TickEventCreator,
OHLCVEventCreator, and FMVEventCreator with proper validation and transport
compatibility verification.
"""

import pytest
import time
from unittest.mock import Mock, patch
from dataclasses import dataclass
from typing import List

# Test imports
from src.processing.channels.event_creators import (
    TickEventCreator, OHLCVEventCreator, FMVEventCreator,
    create_event_creator, validate_event_transport_format,
    batch_create_transport_dicts
)
from src.shared.models.data_types import TickData, OHLCVData, FMVData
from src.core.domain.events.base import BaseEvent
from src.core.domain.events.highlow import HighLowEvent
from src.core.domain.events.surge import SurgeEvent
from src.core.domain.events.trend import TrendEvent
from src.core.domain.events.aggregate import PerMinuteAggregateEvent
from src.core.domain.events.fmv import FairMarketValueEvent


@pytest.fixture
def sample_tick_data():
    """Sample tick data for testing"""
    return TickData(
        ticker="AAPL",
        timestamp=time.time(),
        price=150.50,
        volume=10000,
        vwap=150.25,
        source="test_source"
    )


@pytest.fixture
def sample_ohlcv_data():
    """Sample OHLCV data for testing"""
    return OHLCVData(
        ticker="AAPL",
        timestamp=time.time(),
        open=149.0,
        high=151.0,
        low=148.5,
        close=150.50,
        volume=1000000,
        avg_volume=800000.0,
        percent_change=1.5
    )


@pytest.fixture
def sample_fmv_data():
    """Sample FMV data for testing"""
    return FMVData(
        ticker="AAPL",
        timestamp=time.time(),
        fmv=155.0,
        market_price=150.50,
        confidence=0.85
    )


class TestTickEventCreator:
    """Test TickEventCreator functionality"""
    
    def test_init(self):
        """Test TickEventCreator initialization"""
        creator = TickEventCreator("test_channel", "test_id")
        assert creator.channel_name == "test_channel"
        assert creator.channel_id == "test_id"
        assert creator.high_low_threshold == 0.05
        assert creator.surge_multiplier == 3.0
    
    def test_create_events_basic(self, sample_tick_data):
        """Test basic event creation from tick data"""
        creator = TickEventCreator("test_channel", "test_id")
        events = creator.create_events(sample_tick_data)
        
        # Should return empty list without historical context
        assert isinstance(events, list)
        assert len(events) == 0
    
    def test_create_events_with_context(self, sample_tick_data):
        """Test event creation with historical context"""
        creator = TickEventCreator("test_channel", "test_id")
        
        # Provide context that should trigger high event
        kwargs = {
            'historical_high': 140.0,  # Current price 150.50 > 140.0 * 1.05
            'historical_low': 100.0,
            'avg_volume': 3000,  # Current volume 10000 > 3000 * 3.0
            'previous_prices': [148.0, 149.0, 150.0]  # Uptrend pattern
        }
        
        events = creator.create_events(sample_tick_data, **kwargs)
        assert len(events) >= 1  # Should create at least one event
    
    def test_generate_unique_event_id(self):
        """Test unique event ID generation"""
        creator = TickEventCreator("test_channel", "test_id")
        
        id1 = creator.generate_unique_event_id("AAPL", "high")
        id2 = creator.generate_unique_event_id("AAPL", "high")
        
        assert id1 != id2
        assert "AAPL" in id1
        assert "high" in id1


class TestOHLCVEventCreator:
    """Test OHLCVEventCreator functionality"""
    
    def test_init(self):
        """Test OHLCVEventCreator initialization"""
        creator = OHLCVEventCreator("ohlcv_channel", "ohlcv_id")
        assert creator.channel_name == "ohlcv_channel"
        assert creator.channel_id == "ohlcv_id"
        assert creator.significant_move_threshold == 2.0
        assert creator.volume_surge_threshold == 3.0
    
    def test_create_events_basic(self, sample_ohlcv_data):
        """Test basic OHLCV event creation"""
        creator = OHLCVEventCreator("ohlcv_channel", "ohlcv_id")
        events = creator.create_events(sample_ohlcv_data)
        
        # Should create aggregate event at minimum
        assert len(events) >= 1
        assert any(isinstance(event, PerMinuteAggregateEvent) for event in events)
    
    def test_create_events_volume_surge(self, sample_ohlcv_data):
        """Test volume surge detection in OHLCV data"""
        creator = OHLCVEventCreator("ohlcv_channel", "ohlcv_id")
        
        # Modify data to trigger volume surge (volume > avg_volume * 3.0)
        sample_ohlcv_data.volume = 2500000  # 2.5M > 800k * 3.0
        events = creator.create_events(sample_ohlcv_data)
        
        # Should include surge event
        surge_events = [e for e in events if isinstance(e, SurgeEvent)]
        assert len(surge_events) >= 1
    
    def test_create_events_significant_move(self, sample_ohlcv_data):
        """Test significant move detection"""
        creator = OHLCVEventCreator("ohlcv_channel", "ohlcv_id")
        
        # Modify data to trigger significant move (>= 2.0%)
        sample_ohlcv_data.percent_change = 2.5
        events = creator.create_events(sample_ohlcv_data)
        
        # Should include trend/move event
        trend_events = [e for e in events if isinstance(e, TrendEvent)]
        assert len(trend_events) >= 1


class TestFMVEventCreator:
    """Test FMVEventCreator functionality"""
    
    def test_init(self):
        """Test FMVEventCreator initialization"""
        creator = FMVEventCreator("fmv_channel", "fmv_id")
        assert creator.channel_name == "fmv_channel"
        assert creator.channel_id == "fmv_id"
        assert creator.confidence_threshold == 0.8
        assert creator.deviation_threshold == 1.0
    
    def test_create_events_high_confidence(self, sample_fmv_data):
        """Test FMV event creation with high confidence"""
        creator = FMVEventCreator("fmv_channel", "fmv_id")
        events = creator.create_events(sample_fmv_data)
        
        # Should create FMV event (confidence 0.85 >= 0.8)
        assert len(events) >= 1
        fmv_events = [e for e in events if isinstance(e, FairMarketValueEvent)]
        assert len(fmv_events) >= 1
    
    def test_create_events_low_confidence(self, sample_fmv_data):
        """Test FMV event creation with low confidence"""
        creator = FMVEventCreator("fmv_channel", "fmv_id")
        
        # Set low confidence
        sample_fmv_data.confidence = 0.7  # Below 0.8 threshold
        events = creator.create_events(sample_fmv_data)
        
        # Should return empty list
        assert len(events) == 0
    
    def test_create_events_significant_deviation(self, sample_fmv_data):
        """Test deviation alert creation"""
        creator = FMVEventCreator("fmv_channel", "fmv_id")
        
        # Set significant deviation (FMV 155.0 vs market 150.50 = ~3% deviation)
        events = creator.create_events(sample_fmv_data)
        
        # Should include deviation event (3% > 1.0% threshold)
        deviation_events = [e for e in events if hasattr(e, 'trend_type')]
        assert len(deviation_events) >= 1


class TestEventCreatorFactory:
    """Test factory function for event creators"""
    
    def test_create_tick_event_creator(self):
        """Test factory creates TickEventCreator"""
        creator = create_event_creator("tick", "test_channel", "test_id")
        assert isinstance(creator, TickEventCreator)
        assert creator.channel_name == "test_channel"
        assert creator.channel_id == "test_id"
    
    def test_create_ohlcv_event_creator(self):
        """Test factory creates OHLCVEventCreator"""
        creator = create_event_creator("ohlcv", "test_channel", "test_id")
        assert isinstance(creator, OHLCVEventCreator)
        assert creator.channel_name == "test_channel"
        assert creator.channel_id == "test_id"
    
    def test_create_fmv_event_creator(self):
        """Test factory creates FMVEventCreator"""
        creator = create_event_creator("fmv", "test_channel", "test_id")
        assert isinstance(creator, FMVEventCreator)
        assert creator.channel_name == "test_channel"
        assert creator.channel_id == "test_id"
    
    def test_create_unknown_type_raises_error(self):
        """Test factory raises error for unknown type"""
        with pytest.raises(ValueError, match="Unknown channel type"):
            create_event_creator("unknown", "test_channel", "test_id")


class TestEventValidationUtilities:
    """Test event validation and transport utilities"""
    
    def test_validate_event_transport_format_valid(self, sample_ohlcv_data):
        """Test validation of valid events"""
        creator = OHLCVEventCreator("test", "test")
        events = creator.create_events(sample_ohlcv_data)
        
        # Mock the to_transport_dict method
        for event in events:
            event.to_transport_dict = Mock(return_value={
                'ticker': 'AAPL',
                'type': 'test',
                'price': 150.0,
                'time': time.time(),
                'event_id': 'test_id'
            })
        
        results = validate_event_transport_format(events)
        assert results['total_events'] == len(events)
        assert results['valid_events'] == len(events)
        assert results['invalid_events'] == 0
    
    def test_validate_event_transport_format_invalid(self, sample_ohlcv_data):
        """Test validation of invalid events"""
        creator = OHLCVEventCreator("test", "test")
        events = creator.create_events(sample_ohlcv_data)
        
        # Mock invalid transport dict (missing required field)
        for event in events:
            event.to_transport_dict = Mock(return_value={
                'ticker': 'AAPL',
                'type': 'test',
                # Missing 'price', 'time', 'event_id'
            })
        
        results = validate_event_transport_format(events)
        assert results['total_events'] == len(events)
        assert results['valid_events'] == 0
        assert results['invalid_events'] == len(events)
        assert len(results['validation_errors']) > 0
    
    def test_batch_create_transport_dicts(self, sample_ohlcv_data):
        """Test batch transport dict creation"""
        creator = OHLCVEventCreator("test", "test")
        events = creator.create_events(sample_ohlcv_data)
        
        # Mock to_transport_dict for all events
        for event in events:
            event.to_transport_dict = Mock(return_value={
                'ticker': 'AAPL',
                'type': 'test',
                'price': 150.0,
                'time': time.time(),
                'event_id': 'test_id'
            })
        
        transport_dicts = batch_create_transport_dicts(events)
        assert len(transport_dicts) == len(events)
        assert all('ticker' in td for td in transport_dicts)


class TestEventCreatorIntegration:
    """Integration tests for event creators with real data models"""
    
    def test_tick_to_ohlcv_to_fmv_pipeline(self):
        """Test event creation through entire data pipeline"""
        # Simulate tick data processing
        tick_creator = TickEventCreator("tick", "tick_1")
        tick_data = TickData(
            ticker="AAPL",
            timestamp=time.time(),
            price=150.0,
            volume=5000,
            vwap=149.8,
            source="polygon"
        )
        
        # Create OHLCV data from multiple ticks (simulated)
        ohlcv_creator = OHLCVEventCreator("ohlcv", "ohlcv_1")
        ohlcv_data = OHLCVData(
            ticker="AAPL",
            timestamp=time.time(),
            open=149.5,
            high=150.5,
            low=149.0,
            close=150.0,
            volume=300000,
            avg_volume=250000.0,
            percent_change=0.33
        )
        
        # Create FMV data
        fmv_creator = FMVEventCreator("fmv", "fmv_1")
        fmv_data = FMVData(
            ticker="AAPL",
            timestamp=time.time(),
            fmv=152.0,
            market_price=150.0,
            confidence=0.9
        )
        
        # Generate events from each creator
        tick_events = tick_creator.create_events(tick_data)
        ohlcv_events = ohlcv_creator.create_events(ohlcv_data)
        fmv_events = fmv_creator.create_events(fmv_data)
        
        # Verify event generation
        assert isinstance(tick_events, list)
        assert isinstance(ohlcv_events, list)
        assert isinstance(fmv_events, list)
        
        # Should have at least aggregate event from OHLCV
        assert len(ohlcv_events) >= 1
        # Should have FMV event with high confidence
        assert len(fmv_events) >= 1
    
    def test_event_id_uniqueness_across_creators(self):
        """Test that event IDs are unique across different creators"""
        creators = [
            TickEventCreator("tick", "tick_1"),
            OHLCVEventCreator("ohlcv", "ohlcv_1"),
            FMVEventCreator("fmv", "fmv_1")
        ]
        
        all_ids = set()
        
        for creator in creators:
            for i in range(10):  # Generate multiple IDs
                event_id = creator.generate_unique_event_id("AAPL", "test")
                assert event_id not in all_ids, f"Duplicate ID found: {event_id}"
                all_ids.add(event_id)
        
        # Should have 30 unique IDs (3 creators * 10 IDs each)
        assert len(all_ids) == 30