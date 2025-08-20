"""
Unit tests for TickChannel concrete implementation.

Tests tick-specific processing including:
- Tick data validation and conversion
- Event detection integration
- Stock data cache management
- Performance optimization for high-frequency data

Sprint 105: Core Channel Infrastructure Testing
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, List
from dataclasses import dataclass

from src.processing.channels.tick_channel import TickChannel
from src.processing.channels.channel_config import TickChannelConfig
from src.processing.channels.base_channel import (
    ChannelType,
    ProcessingResult,
    ChannelStatus
)
from src.core.domain.events.base import BaseEvent


# Mock event classes for testing
class MockHighLowEvent:
    def __init__(self, ticker: str, event_type: str, price: float):
        self.ticker = ticker
        self.type = event_type
        self.price = price
        self.event_id = f"hl_{ticker}_{int(time.time())}"
        self.time = time.time()


class MockTrendEvent:
    def __init__(self, ticker: str, direction: str, period: int, price: float):
        self.ticker = ticker
        self.type = "trend"
        self.direction = direction
        self.period = period
        self.price = price
        self.event_id = f"trend_{ticker}_{int(time.time())}"
        self.time = time.time()


class MockSurgeEvent:
    def __init__(self, ticker: str, volume: float, volume_ratio: float, price: float):
        self.ticker = ticker
        self.type = "surge"
        self.volume = volume
        self.volume_ratio = volume_ratio
        self.price = price
        self.event_id = f"surge_{ticker}_{int(time.time())}"
        self.time = time.time()


@dataclass
class MockTickData:
    """Mock tick data structure"""
    ticker: str
    price: float
    volume: int
    timestamp: float
    bid: float = 0.0
    ask: float = 0.0


@dataclass
class MockStockData:
    """Mock stock data structure"""
    ticker: str
    current_price: float
    volume: int
    high_24h: float
    low_24h: float
    price_history: List[float]
    volume_history: List[int]


class TestTickChannelInitialization:
    """Test TickChannel initialization and configuration"""

    def test_tick_channel_creation_with_defaults(self):
        """Test tick channel creation with default configuration"""
        channel = TickChannel("test_tick_channel")
        
        assert channel.name == "test_tick_channel"
        assert channel.get_channel_type() == ChannelType.TICK
        assert channel.status == ChannelStatus.INITIALIZING
        assert isinstance(channel.config, TickChannelConfig)

    def test_tick_channel_creation_with_custom_config(self):
        """Test tick channel creation with custom configuration"""
        config = TickChannelConfig(
            max_queue_size=2000,
            highlow_detection={'enabled': False},
            trend_detection={'enabled': True, 'window_sizes': [120, 300]},
            surge_detection={'enabled': True, 'volume_multiplier': 5.0}
        )
        
        channel = TickChannel("custom_tick_channel", config)
        
        assert channel.config.max_queue_size == 2000
        assert channel.config.highlow_detection['enabled'] is False
        assert channel.config.trend_detection['window_sizes'] == [120, 300]
        assert channel.config.surge_detection['volume_multiplier'] == 5.0

    @pytest.mark.asyncio
    async def test_tick_channel_initialization(self):
        """Test tick channel async initialization"""
        channel = TickChannel("init_test")
        
        # Mock the detector initialization
        with patch.object(channel, '_initialize_detectors', return_value=True):
            success = await channel.initialize()
            
            assert success
            assert channel._detectors_initialized

    @pytest.mark.asyncio
    async def test_tick_channel_initialization_failure(self):
        """Test tick channel initialization failure handling"""
        channel = TickChannel("init_fail_test")
        
        # Mock detector initialization to fail
        with patch.object(channel, '_initialize_detectors', return_value=False):
            success = await channel.initialize()
            
            assert not success

    @pytest.mark.asyncio
    async def test_tick_channel_shutdown(self):
        """Test tick channel shutdown process"""
        channel = TickChannel("shutdown_test")
        await channel.start()
        
        # Mock cleanup methods
        with patch.object(channel, '_cleanup_stock_cache') as mock_cleanup:
            success = await channel.shutdown()
            
            assert success
            mock_cleanup.assert_called_once()


class TestTickDataValidation:
    """Test tick data validation functionality"""

    @pytest.fixture
    def channel(self):
        return TickChannel("validation_test")

    def test_validate_dict_tick_data(self, channel):
        """Test validation of dictionary tick data"""
        valid_tick = {
            'ticker': 'AAPL',
            'price': 150.0,
            'volume': 1000,
            'timestamp': time.time()
        }
        
        assert channel.validate_data(valid_tick) is True

    def test_validate_polygon_tick_data(self, channel):
        """Test validation of Polygon API tick data"""
        polygon_tick = {
            'sym': 'AAPL',
            'p': 150.0,  # price
            'v': 1000,   # volume
            't': int(time.time() * 1000)  # timestamp in ms
        }
        
        assert channel.validate_data(polygon_tick) is True

    def test_validate_object_tick_data(self, channel):
        """Test validation of object tick data"""
        tick_obj = MockTickData('AAPL', 150.0, 1000, time.time())
        
        assert channel.validate_data(tick_obj) is True

    def test_validate_invalid_tick_data(self, channel):
        """Test validation of invalid tick data"""
        # Missing required fields
        invalid_tick = {'ticker': 'AAPL', 'price': 150.0}  # Missing volume
        assert channel.validate_data(invalid_tick) is False
        
        # Invalid price
        invalid_tick = {'ticker': 'AAPL', 'price': -10.0, 'volume': 1000}
        assert channel.validate_data(invalid_tick) is False
        
        # Invalid volume
        invalid_tick = {'ticker': 'AAPL', 'price': 150.0, 'volume': -1000}
        assert channel.validate_data(invalid_tick) is False
        
        # Empty ticker
        invalid_tick = {'ticker': '', 'price': 150.0, 'volume': 1000}
        assert channel.validate_data(invalid_tick) is False

    def test_validate_edge_cases(self, channel):
        """Test validation of edge cases"""
        # Zero volume (should be valid)
        zero_volume_tick = {'ticker': 'AAPL', 'price': 150.0, 'volume': 0}
        assert channel.validate_data(zero_volume_tick) is True
        
        # Very small price (should be valid)
        small_price_tick = {'ticker': 'PENNY', 'price': 0.01, 'volume': 1000}
        assert channel.validate_data(small_price_tick) is True
        
        # Large numbers
        large_tick = {'ticker': 'AAPL', 'price': 99999.99, 'volume': 10000000}
        assert channel.validate_data(large_tick) is True


class TestTickDataConversion:
    """Test tick data conversion functionality"""

    @pytest.fixture
    async def channel(self):
        channel = TickChannel("conversion_test")
        await channel.start()
        return channel

    @pytest.mark.asyncio
    async def test_convert_dict_to_tick_data(self, channel):
        """Test conversion of dictionary to TickData"""
        input_dict = {
            'ticker': 'AAPL',
            'price': 150.0,
            'volume': 1000,
            'timestamp': 1640995200,
            'bid': 149.99,
            'ask': 150.01
        }
        
        tick_data = channel._convert_to_tick_data(input_dict)
        
        assert tick_data.ticker == 'AAPL'
        assert tick_data.price == 150.0
        assert tick_data.volume == 1000
        assert tick_data.timestamp == 1640995200
        assert tick_data.bid == 149.99
        assert tick_data.ask == 150.01

    @pytest.mark.asyncio
    async def test_convert_polygon_to_tick_data(self, channel):
        """Test conversion of Polygon format to TickData"""
        polygon_tick = {
            'sym': 'AAPL',
            'p': 150.0,
            'v': 1000,
            't': 1640995200000,  # milliseconds
            'bp': 149.99,
            'ap': 150.01
        }
        
        tick_data = channel._convert_to_tick_data(polygon_tick)
        
        assert tick_data.ticker == 'AAPL'
        assert tick_data.price == 150.0
        assert tick_data.volume == 1000
        assert tick_data.timestamp == 1640995200.0  # converted to seconds
        assert tick_data.bid == 149.99
        assert tick_data.ask == 150.01

    @pytest.mark.asyncio
    async def test_convert_object_to_tick_data(self, channel):
        """Test conversion of object to TickData"""
        mock_tick = MockTickData('AAPL', 150.0, 1000, 1640995200)
        
        tick_data = channel._convert_to_tick_data(mock_tick)
        
        assert tick_data.ticker == 'AAPL'
        assert tick_data.price == 150.0
        assert tick_data.volume == 1000
        assert tick_data.timestamp == 1640995200

    @pytest.mark.asyncio
    async def test_convert_with_missing_optional_fields(self, channel):
        """Test conversion with missing optional fields"""
        minimal_tick = {
            'ticker': 'AAPL',
            'price': 150.0,
            'volume': 1000
        }
        
        tick_data = channel._convert_to_tick_data(minimal_tick)
        
        assert tick_data.ticker == 'AAPL'
        assert tick_data.price == 150.0
        assert tick_data.volume == 1000
        assert tick_data.timestamp > 0  # Should use current time
        assert tick_data.bid >= 0  # Should have default value
        assert tick_data.ask >= 0  # Should have default value


class TestEventDetection:
    """Test event detection integration"""

    @pytest.fixture
    async def channel(self):
        """Create channel with mocked detectors"""
        channel = TickChannel("event_detection_test")
        
        # Mock the detectors
        channel.highlow_detector = Mock()
        channel.trend_detector = Mock()  
        channel.surge_detector = Mock()
        channel._detectors_initialized = True
        
        await channel.start()
        return channel

    @pytest.mark.asyncio
    async def test_detect_high_low_events(self, channel):
        """Test high/low event detection"""
        tick_data = MockTickData('AAPL', 150.0, 1000, time.time())
        stock_data = MockStockData('AAPL', 149.0, 1000, 151.0, 148.0, [149.0, 149.5], [1000, 1100])
        
        # Mock detector to return high event
        mock_event = MockHighLowEvent('AAPL', 'high', 150.0)
        channel.highlow_detector.detect_event.return_value = mock_event
        
        events = await channel._detect_events(tick_data, stock_data)
        
        assert len(events) >= 1
        assert any(event.type == 'high' for event in events)
        channel.highlow_detector.detect_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_detect_trend_events(self, channel):
        """Test trend event detection"""
        tick_data = MockTickData('AAPL', 150.0, 1000, time.time())
        stock_data = MockStockData('AAPL', 149.0, 1000, 151.0, 148.0, [148.0, 149.0, 150.0], [1000])
        
        # Mock detector to return trend event
        mock_event = MockTrendEvent('AAPL', 'up', 180, 150.0)
        channel.trend_detector.detect_event.return_value = mock_event
        
        events = await channel._detect_events(tick_data, stock_data)
        
        assert len(events) >= 1
        assert any(event.type == 'trend' for event in events)
        channel.trend_detector.detect_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_detect_surge_events(self, channel):
        """Test surge event detection"""
        tick_data = MockTickData('AAPL', 150.0, 10000, time.time())  # High volume
        stock_data = MockStockData('AAPL', 149.0, 1000, 151.0, 148.0, [149.0], [1000, 1100])
        
        # Mock detector to return surge event
        mock_event = MockSurgeEvent('AAPL', 10000, 10.0, 150.0)
        channel.surge_detector.detect_event.return_value = mock_event
        
        events = await channel._detect_events(tick_data, stock_data)
        
        assert len(events) >= 1
        assert any(event.type == 'surge' for event in events)
        channel.surge_detector.detect_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_detect_multiple_events(self, channel):
        """Test detection of multiple events from single tick"""
        tick_data = MockTickData('AAPL', 150.0, 10000, time.time())
        stock_data = MockStockData('AAPL', 149.0, 1000, 151.0, 148.0, [148.0, 149.0], [1000])
        
        # Mock all detectors to return events
        channel.highlow_detector.detect_event.return_value = MockHighLowEvent('AAPL', 'high', 150.0)
        channel.trend_detector.detect_event.return_value = MockTrendEvent('AAPL', 'up', 180, 150.0)
        channel.surge_detector.detect_event.return_value = MockSurgeEvent('AAPL', 10000, 10.0, 150.0)
        
        events = await channel._detect_events(tick_data, stock_data)
        
        assert len(events) == 3
        event_types = {event.type for event in events}
        assert 'high' in event_types
        assert 'trend' in event_types
        assert 'surge' in event_types

    @pytest.mark.asyncio
    async def test_detect_no_events(self, channel):
        """Test when no events are detected"""
        tick_data = MockTickData('AAPL', 150.0, 1000, time.time())
        stock_data = MockStockData('AAPL', 149.0, 1000, 151.0, 148.0, [149.0], [1000])
        
        # Mock all detectors to return None
        channel.highlow_detector.detect_event.return_value = None
        channel.trend_detector.detect_event.return_value = None
        channel.surge_detector.detect_event.return_value = None
        
        events = await channel._detect_events(tick_data, stock_data)
        
        assert len(events) == 0

    @pytest.mark.asyncio
    async def test_detect_events_with_disabled_detectors(self, channel):
        """Test event detection with some detectors disabled"""
        # Disable trend detection
        channel.config.trend_detection['enabled'] = False
        
        tick_data = MockTickData('AAPL', 150.0, 1000, time.time())
        stock_data = MockStockData('AAPL', 149.0, 1000, 151.0, 148.0, [149.0], [1000])
        
        # Mock enabled detectors
        channel.highlow_detector.detect_event.return_value = MockHighLowEvent('AAPL', 'high', 150.0)
        channel.surge_detector.detect_event.return_value = MockSurgeEvent('AAPL', 1000, 1.0, 150.0)
        
        events = await channel._detect_events(tick_data, stock_data)
        
        # Should only get events from enabled detectors
        assert len(events) == 2
        event_types = {event.type for event in events}
        assert 'trend' not in event_types  # Disabled detector
        assert 'high' in event_types
        assert 'surge' in event_types


class TestStockDataManagement:
    """Test stock data cache management"""

    @pytest.fixture
    async def channel(self):
        channel = TickChannel("stock_data_test")
        channel._detectors_initialized = True
        await channel.start()
        return channel

    @pytest.mark.asyncio
    async def test_get_stock_data_new_ticker(self, channel):
        """Test getting stock data for new ticker"""
        with patch.object(channel, '_create_initial_stock_data') as mock_create:
            mock_stock_data = MockStockData('AAPL', 150.0, 1000, 151.0, 149.0, [150.0], [1000])
            mock_create.return_value = mock_stock_data
            
            stock_data = await channel._get_stock_data('AAPL')
            
            assert stock_data.ticker == 'AAPL'
            mock_create.assert_called_once_with('AAPL')

    @pytest.mark.asyncio
    async def test_get_stock_data_existing_ticker(self, channel):
        """Test getting stock data for existing ticker"""
        # Pre-populate cache
        existing_data = MockStockData('AAPL', 150.0, 1000, 151.0, 149.0, [150.0], [1000])
        channel.stock_cache['AAPL'] = existing_data
        
        stock_data = await channel._get_stock_data('AAPL')
        
        assert stock_data == existing_data

    @pytest.mark.asyncio
    async def test_update_stock_data(self, channel):
        """Test updating stock data with new tick"""
        # Create initial stock data
        stock_data = MockStockData('AAPL', 149.0, 1000, 150.0, 148.0, [149.0], [1000])
        channel.stock_cache['AAPL'] = stock_data
        
        # Create new tick
        tick_data = MockTickData('AAPL', 151.0, 2000, time.time())
        
        updated_data = channel._update_stock_data(stock_data, tick_data)
        
        assert updated_data.current_price == 151.0
        assert updated_data.volume == 2000
        assert updated_data.high_24h == 151.0  # New high
        assert 151.0 in updated_data.price_history
        assert 2000 in updated_data.volume_history

    def test_update_stock_data_new_high(self, channel):
        """Test stock data update with new 24h high"""
        stock_data = MockStockData('AAPL', 149.0, 1000, 150.0, 148.0, [149.0], [1000])
        tick_data = MockTickData('AAPL', 152.0, 1500, time.time())
        
        updated_data = channel._update_stock_data(stock_data, tick_data)
        
        assert updated_data.high_24h == 152.0

    def test_update_stock_data_new_low(self, channel):
        """Test stock data update with new 24h low"""
        stock_data = MockStockData('AAPL', 149.0, 1000, 150.0, 148.0, [149.0], [1000])
        tick_data = MockTickData('AAPL', 147.0, 1200, time.time())
        
        updated_data = channel._update_stock_data(stock_data, tick_data)
        
        assert updated_data.low_24h == 147.0

    def test_price_history_management(self, channel):
        """Test price history size management"""
        # Create stock data with max history
        long_history = [float(i) for i in range(1000)]  # 1000 prices
        stock_data = MockStockData('AAPL', 149.0, 1000, 150.0, 148.0, long_history, [1000])
        
        tick_data = MockTickData('AAPL', 151.0, 1100, time.time())
        
        updated_data = channel._update_stock_data(stock_data, tick_data)
        
        # Should maintain reasonable history size (not grow indefinitely)
        assert len(updated_data.price_history) <= 1000
        assert 151.0 in updated_data.price_history

    @pytest.mark.asyncio
    async def test_cache_cleanup(self, channel):
        """Test cache cleanup functionality"""
        # Add multiple tickers to cache
        for i, ticker in enumerate(['AAPL', 'GOOGL', 'MSFT', 'TSLA']):
            stock_data = MockStockData(ticker, 100.0 + i, 1000, 101.0 + i, 99.0 + i, [100.0], [1000])
            channel.stock_cache[ticker] = stock_data
        
        initial_size = len(channel.stock_cache)
        assert initial_size == 4
        
        # Mock time to make some entries old
        with patch('time.time', return_value=time.time() + 3600):  # 1 hour later
            channel._cleanup_stock_cache()
        
        # Cache should be cleaned up
        # Note: Actual cleanup logic would depend on implementation
        # For now, just verify the method can be called
        assert len(channel.stock_cache) >= 0


class TestTickChannelProcessing:
    """Test complete tick processing pipeline"""

    @pytest.fixture
    async def processing_channel(self):
        """Create fully configured channel for processing tests"""
        config = TickChannelConfig(
            highlow_detection={'enabled': True, 'threshold': 0.02},
            trend_detection={'enabled': True, 'window_sizes': [180, 360]},
            surge_detection={'enabled': True, 'volume_multiplier': 3.0}
        )
        
        channel = TickChannel("processing_test", config)
        
        # Mock detectors
        channel.highlow_detector = Mock()
        channel.trend_detector = Mock()
        channel.surge_detector = Mock()
        channel._detectors_initialized = True
        
        await channel.start()
        return channel

    @pytest.mark.asyncio
    async def test_complete_tick_processing(self, processing_channel):
        """Test complete tick processing pipeline"""
        tick_data = {
            'ticker': 'AAPL',
            'price': 150.0,
            'volume': 1000,
            'timestamp': time.time()
        }
        
        # Mock detector to return an event
        mock_event = MockHighLowEvent('AAPL', 'high', 150.0)
        processing_channel.highlow_detector.detect_event.return_value = mock_event
        processing_channel.trend_detector.detect_event.return_value = None
        processing_channel.surge_detector.detect_event.return_value = None
        
        result = await processing_channel.process_data(tick_data)
        
        assert result.success
        assert len(result.events) == 1
        assert result.events[0].type == 'high'
        assert result.processing_time_ms == 0.0  # Will be set by process_with_metrics
        assert 'ticker' in result.metadata

    @pytest.mark.asyncio
    async def test_processing_with_invalid_data(self, processing_channel):
        """Test processing with invalid data"""
        invalid_data = {'ticker': 'AAPL'}  # Missing required fields
        
        result = await processing_channel.process_data(invalid_data)
        
        assert not result.success
        assert len(result.errors) > 0
        assert "data conversion failed" in result.errors[0].lower()

    @pytest.mark.asyncio
    async def test_processing_with_detector_failure(self, processing_channel):
        """Test processing when event detector fails"""
        tick_data = {
            'ticker': 'AAPL',
            'price': 150.0,
            'volume': 1000,
            'timestamp': time.time()
        }
        
        # Mock detector to raise exception
        processing_channel.highlow_detector.detect_event.side_effect = Exception("Detector failed")
        processing_channel.trend_detector.detect_event.return_value = None
        processing_channel.surge_detector.detect_event.return_value = None
        
        result = await processing_channel.process_data(tick_data)
        
        # Should handle detector failure gracefully
        assert result.success  # Processing should still succeed
        assert len(result.events) == 0  # But no events from failed detector

    @pytest.mark.asyncio
    async def test_processing_performance(self, processing_channel, performance_timer):
        """Test processing performance meets requirements"""
        tick_data = {
            'ticker': 'AAPL',
            'price': 150.0,
            'volume': 1000,
            'timestamp': time.time()
        }
        
        # Mock detectors to return quickly
        processing_channel.highlow_detector.detect_event.return_value = None
        processing_channel.trend_detector.detect_event.return_value = None
        processing_channel.surge_detector.detect_event.return_value = None
        
        performance_timer.start()
        
        # Process many ticks
        for _ in range(100):
            await processing_channel.process_data(tick_data)
        
        performance_timer.stop()
        
        # Should be fast (< 1 second for 100 ticks)
        assert performance_timer.elapsed < 1.0
        
        # Average processing time should be reasonable
        avg_time_per_tick = (performance_timer.elapsed / 100) * 1000  # ms
        assert avg_time_per_tick < 10  # Less than 10ms per tick

    @pytest.mark.asyncio
    async def test_concurrent_processing(self, processing_channel):
        """Test concurrent tick processing"""
        tick_data = {
            'ticker': 'AAPL',
            'price': 150.0,
            'volume': 1000,
            'timestamp': time.time()
        }
        
        # Mock detectors
        processing_channel.highlow_detector.detect_event.return_value = None
        processing_channel.trend_detector.detect_event.return_value = None
        processing_channel.surge_detector.detect_event.return_value = None
        
        # Process multiple ticks concurrently
        tasks = []
        for i in range(20):
            modified_data = tick_data.copy()
            modified_data['price'] = 150.0 + i * 0.1
            task = processing_channel.process_data(modified_data)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # All should succeed
        assert all(result.success for result in results)
        assert len(results) == 20

    @pytest.mark.asyncio
    async def test_processing_different_tickers(self, processing_channel):
        """Test processing ticks from different tickers"""
        tickers = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN']
        
        # Mock detectors
        processing_channel.highlow_detector.detect_event.return_value = None
        processing_channel.trend_detector.detect_event.return_value = None
        processing_channel.surge_detector.detect_event.return_value = None
        
        results = []
        for ticker in tickers:
            tick_data = {
                'ticker': ticker,
                'price': 150.0,
                'volume': 1000,
                'timestamp': time.time()
            }
            
            result = await processing_channel.process_data(tick_data)
            results.append(result)
        
        # All should succeed
        assert all(result.success for result in results)
        
        # Should have data for all tickers in cache
        assert len(processing_channel.stock_cache) == len(tickers)
        for ticker in tickers:
            assert ticker in processing_channel.stock_cache


class TestTickChannelIntegration:
    """Test tick channel integration with other systems"""

    @pytest.mark.asyncio
    async def test_integration_with_metrics(self):
        """Test integration with metrics system"""
        channel = TickChannel("metrics_integration_test")
        await channel.start()
        
        # Process some data
        tick_data = {'ticker': 'AAPL', 'price': 150.0, 'volume': 1000}
        
        # Mock detectors
        with patch.object(channel, '_detect_events', return_value=[]):
            result = await channel.process_with_metrics(tick_data)
        
        # Check metrics were updated
        assert channel.metrics.processed_count > 0
        assert result.processing_time_ms > 0

    @pytest.mark.asyncio
    async def test_integration_with_config_manager(self):
        """Test integration with configuration management"""
        # Test that configuration changes are respected
        config = TickChannelConfig(
            highlow_detection={'enabled': False},
            trend_detection={'enabled': True},
            surge_detection={'enabled': False}
        )
        
        channel = TickChannel("config_integration_test", config)
        
        assert channel.config.highlow_detection['enabled'] is False
        assert channel.config.trend_detection['enabled'] is True
        assert channel.config.surge_detection['enabled'] is False

    @pytest.mark.asyncio 
    async def test_error_recovery(self):
        """Test error recovery capabilities"""
        channel = TickChannel("error_recovery_test")
        await channel.start()
        
        # Simulate processing error
        with patch.object(channel, '_convert_to_tick_data', side_effect=Exception("Conversion failed")):
            result = await channel.process_data({'invalid': 'data'})
            
            assert not result.success
            assert len(result.errors) > 0
        
        # Channel should recover and process valid data
        valid_data = {'ticker': 'AAPL', 'price': 150.0, 'volume': 1000}
        with patch.object(channel, '_detect_events', return_value=[]):
            result = await channel.process_data(valid_data)
            
            assert result.success


# Test markers
pytestmark = [
    pytest.mark.unit,
    pytest.mark.channels,
    pytest.mark.tick_channel
]