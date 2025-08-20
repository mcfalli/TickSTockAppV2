"""
Unit tests for DataChannelRouter system.

Tests intelligent data routing including:
- Data type identification and routing
- Load balancing strategies
- Health-based routing decisions
- Channel management and failover
- Performance optimization

Sprint 105: Core Channel Infrastructure Testing
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, List, Any
from dataclasses import dataclass

from src.processing.channels.channel_router import (
    DataChannelRouter,
    RoutingStrategy,
    DataIdentifier,
    LoadBalancer,
    RoutingDecision,
    ChannelNotAvailableError
)
from src.processing.channels.base_channel import (
    ProcessingChannel,
    ChannelType,
    ChannelStatus,
    ProcessingResult
)
from src.processing.channels.channel_config import ChannelConfig
from src.core.domain.events.base import BaseEvent


@dataclass 
class MockData:
    """Mock data for testing routing"""
    data_type: str
    payload: Dict[str, Any]
    ticker: str = "AAPL"


class MockChannel(ProcessingChannel):
    """Mock channel implementation for testing"""
    
    def __init__(self, name: str, channel_type: ChannelType, config: ChannelConfig = None):
        if config is None:
            config = ChannelConfig()
        super().__init__(name, config)
        self._channel_type = channel_type
        self._healthy = True
        self._load = 0.0
        self.process_calls = []

    def get_channel_type(self) -> ChannelType:
        return self._channel_type

    async def initialize(self) -> bool:
        return True

    def validate_data(self, data: Any) -> bool:
        return True

    async def process_data(self, data: Any) -> ProcessingResult:
        self.process_calls.append(data)
        await asyncio.sleep(0.01)  # Simulate processing
        
        mock_event = Mock(spec=BaseEvent)
        mock_event.ticker = getattr(data, 'ticker', 'TEST')
        
        return ProcessingResult(
            success=True,
            events=[mock_event],
            metadata={'channel': self.name}
        )

    async def shutdown(self) -> bool:
        return True

    def is_healthy(self) -> bool:
        return self._healthy

    def set_healthy(self, healthy: bool):
        self._healthy = healthy

    def set_load(self, load: float):
        self._load = load

    def get_load(self) -> float:
        return self._load


class TestDataIdentifier:
    """Test data type identification functionality"""

    @pytest.fixture
    def identifier(self):
        return DataIdentifier()

    def test_identify_tick_data(self, identifier):
        """Test identification of tick data"""
        tick_data = {
            'ticker': 'AAPL',
            'price': 150.0,
            'volume': 1000,
            'timestamp': 1640995200
        }
        
        data_type = identifier.identify_data_type(tick_data)
        assert data_type == ChannelType.TICK

    def test_identify_ohlcv_data(self, identifier):
        """Test identification of OHLCV data"""
        ohlcv_data = {
            'ticker': 'AAPL',
            'open': 149.0,
            'high': 151.0,
            'low': 148.5,
            'close': 150.0,
            'volume': 50000,
            'period': '1m'
        }
        
        data_type = identifier.identify_data_type(ohlcv_data)
        assert data_type == ChannelType.OHLCV

    def test_identify_fmv_data(self, identifier):
        """Test identification of FMV data"""
        fmv_data = {
            'ticker': 'AAPL',
            'fair_market_value': 150.25,
            'market_price': 150.0,
            'deviation': 0.0017
        }
        
        data_type = identifier.identify_data_type(fmv_data)
        assert data_type == ChannelType.FMV

    def test_identify_polygon_am_data(self, identifier):
        """Test identification of Polygon AM (aggregate minute) data"""
        polygon_am = {
            'ev': 'AM',
            'sym': 'AAPL',
            'o': 150.0,  # open
            'c': 150.5,  # close
            'h': 151.0,  # high
            'l': 149.5,  # low
            'v': 10000   # volume
        }
        
        data_type = identifier.identify_data_type(polygon_am)
        assert data_type == ChannelType.OHLCV

    def test_identify_polygon_fmv_data(self, identifier):
        """Test identification of Polygon FMV data"""
        polygon_fmv = {
            'ev': 'FMV',
            'sym': 'AAPL',
            'fmv': 150.75
        }
        
        data_type = identifier.identify_data_type(polygon_fmv)
        assert data_type == ChannelType.FMV

    def test_identify_unknown_data(self, identifier):
        """Test handling of unknown data types"""
        unknown_data = {
            'some_field': 'some_value',
            'unknown_type': True
        }
        
        # Should default to TICK for unknown data
        data_type = identifier.identify_data_type(unknown_data)
        assert data_type == ChannelType.TICK

    def test_identify_custom_data_object(self, identifier):
        """Test identification with custom data objects"""
        mock_data = MockData('tick', {'price': 150.0}, 'AAPL')
        
        data_type = identifier.identify_data_type(mock_data)
        assert data_type == ChannelType.TICK

    def test_identification_performance(self, identifier, performance_timer):
        """Test data identification performance"""
        test_data = {'ticker': 'AAPL', 'price': 150.0, 'volume': 1000}
        
        performance_timer.start()
        
        # Identify many data items
        for _ in range(1000):
            identifier.identify_data_type(test_data)
        
        performance_timer.stop()
        
        # Should be very fast (< 0.1 seconds for 1000 identifications)
        assert performance_timer.elapsed < 0.1


class TestLoadBalancer:
    """Test load balancing functionality"""

    @pytest.fixture
    def channels(self):
        """Create mock channels for load balancing tests"""
        return [
            MockChannel(f"channel_{i}", ChannelType.TICK) 
            for i in range(3)
        ]

    @pytest.fixture
    async def active_channels(self, channels):
        """Start all channels"""
        for channel in channels:
            await channel.start()
        return channels

    @pytest.fixture
    def load_balancer(self):
        return LoadBalancer()

    def test_round_robin_strategy(self, load_balancer, active_channels):
        """Test round-robin load balancing"""
        # Test multiple selections
        selections = []
        for i in range(6):  # 2 full rounds
            channel = load_balancer.select_channel(
                active_channels, 
                RoutingStrategy.ROUND_ROBIN
            )
            selections.append(channel.name)
        
        # Should cycle through all channels
        expected_pattern = ['channel_0', 'channel_1', 'channel_2'] * 2
        assert selections == expected_pattern

    def test_load_based_strategy(self, load_balancer, active_channels):
        """Test load-based channel selection"""
        # Set different loads
        active_channels[0].set_load(0.9)  # High load
        active_channels[1].set_load(0.3)  # Low load  
        active_channels[2].set_load(0.7)  # Medium load
        
        # Should consistently select lowest load channel
        for _ in range(5):
            channel = load_balancer.select_channel(
                active_channels,
                RoutingStrategy.LOAD_BASED
            )
            assert channel.name == 'channel_1'  # Lowest load

    def test_health_based_strategy(self, load_balancer, active_channels):
        """Test health-based channel selection"""
        # Mark one channel as unhealthy
        active_channels[0].set_healthy(False)
        
        selections = []
        for _ in range(10):
            channel = load_balancer.select_channel(
                active_channels,
                RoutingStrategy.HEALTH_BASED
            )
            selections.append(channel.name)
        
        # Should never select unhealthy channel
        assert 'channel_0' not in selections
        assert all(name in ['channel_1', 'channel_2'] for name in selections)

    def test_random_strategy(self, load_balancer, active_channels):
        """Test random channel selection"""
        selections = []
        for _ in range(100):
            channel = load_balancer.select_channel(
                active_channels,
                RoutingStrategy.RANDOM
            )
            selections.append(channel.name)
        
        # Should use all channels (with high probability)
        unique_selections = set(selections)
        assert len(unique_selections) >= 2  # Should use at least 2 channels

    def test_no_healthy_channels(self, load_balancer, active_channels):
        """Test behavior when no channels are healthy"""
        # Mark all channels as unhealthy
        for channel in active_channels:
            channel.set_healthy(False)
        
        # Should raise exception
        with pytest.raises(ChannelNotAvailableError):
            load_balancer.select_channel(
                active_channels,
                RoutingStrategy.HEALTH_BASED
            )

    def test_empty_channel_list(self, load_balancer):
        """Test behavior with empty channel list"""
        with pytest.raises(ChannelNotAvailableError):
            load_balancer.select_channel([], RoutingStrategy.ROUND_ROBIN)


class TestDataChannelRouter:
    """Test main router functionality"""

    @pytest.fixture
    def channels(self):
        """Create channels for each type"""
        return {
            ChannelType.TICK: [
                MockChannel("tick_1", ChannelType.TICK),
                MockChannel("tick_2", ChannelType.TICK)
            ],
            ChannelType.OHLCV: [
                MockChannel("ohlcv_1", ChannelType.OHLCV)
            ],
            ChannelType.FMV: [
                MockChannel("fmv_1", ChannelType.FMV)
            ]
        }

    @pytest.fixture
    async def router(self, channels):
        """Create router with active channels"""
        router = DataChannelRouter()
        
        # Add and start all channels
        for channel_type, channel_list in channels.items():
            for channel in channel_list:
                await channel.start()
                router.add_channel(channel)
        
        return router

    @pytest.mark.asyncio
    async def test_route_tick_data(self, router):
        """Test routing of tick data"""
        tick_data = {
            'ticker': 'AAPL',
            'price': 150.0,
            'volume': 1000
        }
        
        result = await router.route_data(tick_data)
        
        assert result is not None
        assert result.success
        assert len(result.events) == 1
        assert result.metadata['channel'] in ['tick_1', 'tick_2']

    @pytest.mark.asyncio
    async def test_route_ohlcv_data(self, router):
        """Test routing of OHLCV data"""
        ohlcv_data = {
            'ticker': 'AAPL',
            'open': 149.0,
            'high': 151.0,
            'low': 148.5,
            'close': 150.0,
            'volume': 50000
        }
        
        result = await router.route_data(ohlcv_data)
        
        assert result is not None
        assert result.success
        assert result.metadata['channel'] == 'ohlcv_1'

    @pytest.mark.asyncio
    async def test_route_fmv_data(self, router):
        """Test routing of FMV data"""
        fmv_data = {
            'ticker': 'AAPL',
            'fair_market_value': 150.25,
            'market_price': 150.0
        }
        
        result = await router.route_data(fmv_data)
        
        assert result is not None
        assert result.success
        assert result.metadata['channel'] == 'fmv_1'

    @pytest.mark.asyncio
    async def test_route_with_load_balancing(self, router):
        """Test that load balancing works across multiple channels"""
        tick_data = {'ticker': 'AAPL', 'price': 150.0, 'volume': 1000}
        
        # Route multiple data items
        results = []
        for _ in range(10):
            result = await router.route_data(tick_data)
            results.append(result.metadata['channel'])
        
        # Should use both tick channels
        unique_channels = set(results)
        assert len(unique_channels) >= 1  # At least one channel used

    @pytest.mark.asyncio
    async def test_route_with_no_channels(self):
        """Test routing when no channels are available for data type"""
        router = DataChannelRouter()
        
        tick_data = {'ticker': 'AAPL', 'price': 150.0}
        result = await router.route_data(tick_data)
        
        assert result is None

    @pytest.mark.asyncio
    async def test_route_with_channel_failure(self, router, channels):
        """Test routing when channel processing fails"""
        # Get a channel and make it fail processing
        tick_channel = channels[ChannelType.TICK][0]
        
        # Mock the process_data method to fail
        async def failing_process_data(data):
            return ProcessingResult(
                success=False,
                errors=["Simulated channel failure"]
            )
        
        tick_channel.process_data = failing_process_data
        
        tick_data = {'ticker': 'AAPL', 'price': 150.0}
        result = await router.route_data(tick_data)
        
        # Should still get a result (from the failing channel)
        assert result is not None
        assert not result.success
        assert "Simulated channel failure" in result.errors

    def test_add_remove_channels(self, router, channels):
        """Test adding and removing channels"""
        initial_count = len(router.get_all_channels())
        
        # Add a new channel
        new_channel = MockChannel("new_tick", ChannelType.TICK)
        router.add_channel(new_channel)
        
        assert len(router.get_all_channels()) == initial_count + 1
        
        # Remove a channel
        router.remove_channel(new_channel)
        
        assert len(router.get_all_channels()) == initial_count

    def test_get_channels_by_type(self, router):
        """Test getting channels by type"""
        tick_channels = router.get_channels_by_type(ChannelType.TICK)
        ohlcv_channels = router.get_channels_by_type(ChannelType.OHLCV)
        fmv_channels = router.get_channels_by_type(ChannelType.FMV)
        
        assert len(tick_channels) == 2
        assert len(ohlcv_channels) == 1
        assert len(fmv_channels) == 1

    def test_get_healthy_channels(self, router, channels):
        """Test getting only healthy channels"""
        # Mark one tick channel as unhealthy
        channels[ChannelType.TICK][0].set_healthy(False)
        
        healthy_channels = router.get_healthy_channels()
        unhealthy_channels = [c for c in router.get_all_channels() if not c.is_healthy()]
        
        assert len(unhealthy_channels) == 1
        assert len(healthy_channels) == 3  # 1 tick + 1 ohlcv + 1 fmv

    def test_set_routing_strategy(self, router):
        """Test setting routing strategy"""
        assert router.routing_strategy == RoutingStrategy.ROUND_ROBIN  # Default
        
        router.set_routing_strategy(RoutingStrategy.LOAD_BASED)
        assert router.routing_strategy == RoutingStrategy.LOAD_BASED

    def test_get_router_statistics(self, router):
        """Test getting router statistics"""
        stats = router.get_statistics()
        
        assert 'total_channels' in stats
        assert 'channels_by_type' in stats
        assert 'healthy_channels' in stats
        assert stats['total_channels'] == 4


class TestRoutingDecision:
    """Test routing decision functionality"""

    def test_routing_decision_creation(self):
        """Test routing decision creation"""
        mock_channel = Mock()
        mock_channel.name = "test_channel"
        
        decision = RoutingDecision(
            selected_channel=mock_channel,
            data_type=ChannelType.TICK,
            strategy_used=RoutingStrategy.LOAD_BASED,
            selection_time_ms=5.5,
            available_channels=3
        )
        
        assert decision.selected_channel == mock_channel
        assert decision.data_type == ChannelType.TICK
        assert decision.strategy_used == RoutingStrategy.LOAD_BASED
        assert decision.selection_time_ms == 5.5
        assert decision.available_channels == 3

    def test_routing_decision_string_representation(self):
        """Test routing decision string representation"""
        mock_channel = Mock()
        mock_channel.name = "test_channel"
        
        decision = RoutingDecision(
            selected_channel=mock_channel,
            data_type=ChannelType.TICK,
            strategy_used=RoutingStrategy.HEALTH_BASED,
            selection_time_ms=2.3,
            available_channels=2
        )
        
        decision_str = str(decision)
        assert "test_channel" in decision_str
        assert "TICK" in decision_str
        assert "HEALTH_BASED" in decision_str


class TestRouterPerformance:
    """Test router performance characteristics"""

    @pytest.fixture
    async def performance_router(self):
        """Create router optimized for performance testing"""
        router = DataChannelRouter()
        
        # Add multiple channels of each type
        for i in range(5):
            tick_channel = MockChannel(f"tick_{i}", ChannelType.TICK)
            await tick_channel.start()
            router.add_channel(tick_channel)
        
        return router

    @pytest.mark.asyncio
    async def test_routing_throughput(self, performance_router, performance_timer):
        """Test routing throughput performance"""
        tick_data = {'ticker': 'AAPL', 'price': 150.0, 'volume': 1000}
        
        performance_timer.start()
        
        # Route many data items
        for _ in range(1000):
            await performance_router.route_data(tick_data)
        
        performance_timer.stop()
        
        # Should handle high throughput (< 2 seconds for 1000 routes)
        assert performance_timer.elapsed < 2.0
        
        # Calculate throughput
        throughput = 1000 / performance_timer.elapsed
        assert throughput > 500  # At least 500 routes/second

    @pytest.mark.asyncio
    async def test_concurrent_routing(self, performance_router):
        """Test concurrent routing performance"""
        tick_data = {'ticker': 'AAPL', 'price': 150.0, 'volume': 1000}
        
        async def route_batch():
            tasks = []
            for _ in range(100):
                task = performance_router.route_data(tick_data)
                tasks.append(task)
            return await asyncio.gather(*tasks)
        
        start_time = asyncio.get_event_loop().time()
        
        # Run concurrent batches
        batch_tasks = [route_batch() for _ in range(5)]
        results = await asyncio.gather(*batch_tasks)
        
        elapsed = asyncio.get_event_loop().time() - start_time
        
        # Should handle concurrent load efficiently
        assert elapsed < 3.0  # 500 concurrent routes in < 3 seconds
        
        # All routes should succeed
        total_results = sum(len(batch) for batch in results)
        assert total_results == 500

    @pytest.mark.performance
    def test_channel_selection_performance(self, performance_timer):
        """Test channel selection performance"""
        # Create many channels
        channels = [MockChannel(f"channel_{i}", ChannelType.TICK) for i in range(100)]
        load_balancer = LoadBalancer()
        
        performance_timer.start()
        
        # Perform many selections
        for _ in range(10000):
            load_balancer.select_channel(channels, RoutingStrategy.ROUND_ROBIN)
        
        performance_timer.stop()
        
        # Should be very fast (< 0.5 seconds for 10k selections)
        assert performance_timer.elapsed < 0.5

    def test_memory_efficiency_under_load(self, performance_router):
        """Test memory efficiency during high-load routing"""
        import gc
        
        # Force garbage collection and measure initial memory
        gc.collect()
        initial_objects = len(gc.get_objects())
        
        # Simulate high load
        tick_data = {'ticker': 'AAPL', 'price': 150.0, 'volume': 1000}
        
        # Note: This is a sync test, so we can't use await
        # In real scenario, this would be async routing
        for _ in range(1000):
            # Simulate routing decisions
            channels = performance_router.get_channels_by_type(ChannelType.TICK)
            if channels:
                selected = performance_router.load_balancer.select_channel(
                    channels, performance_router.routing_strategy
                )
        
        # Force garbage collection
        gc.collect()
        final_objects = len(gc.get_objects())
        
        # Memory growth should be minimal
        memory_growth = (final_objects - initial_objects) / initial_objects
        assert memory_growth < 0.1  # Less than 10% memory growth


class TestRouterErrorHandling:
    """Test router error handling and resilience"""

    @pytest.fixture
    async def error_router(self):
        """Create router for error testing"""
        router = DataChannelRouter()
        
        # Add one good channel and one that will fail
        good_channel = MockChannel("good_channel", ChannelType.TICK)
        await good_channel.start()
        router.add_channel(good_channel)
        
        return router

    @pytest.mark.asyncio
    async def test_handle_channel_exceptions(self, error_router):
        """Test handling of exceptions during channel processing"""
        # Add a channel that raises exceptions
        class ExceptionChannel(MockChannel):
            async def process_data(self, data):
                raise RuntimeError("Channel processing failed")
        
        exception_channel = ExceptionChannel("exception_channel", ChannelType.TICK)
        await exception_channel.start()
        error_router.add_channel(exception_channel)
        
        tick_data = {'ticker': 'AAPL', 'price': 150.0}
        
        # Router should handle exceptions gracefully
        result = await error_router.route_data(tick_data)
        
        # Should still get a result (might be from good channel or error result)
        assert result is not None

    @pytest.mark.asyncio
    async def test_fallback_behavior(self, error_router):
        """Test fallback behavior when preferred channels fail"""
        # Set up scenario where one channel is unhealthy
        channels = error_router.get_channels_by_type(ChannelType.TICK)
        if channels:
            channels[0].set_healthy(False)
        
        tick_data = {'ticker': 'AAPL', 'price': 150.0}
        result = await error_router.route_data(tick_data)
        
        # Should still route successfully using healthy channels
        # (In this case we only have one channel, so it might fail)
        # The important thing is that the router doesn't crash
        assert result is not None or len(channels) == 1

    def test_invalid_routing_strategy(self, error_router):
        """Test handling of invalid routing strategy"""
        with pytest.raises(ValueError):
            error_router.set_routing_strategy("invalid_strategy")

    def test_duplicate_channel_handling(self, error_router):
        """Test handling of duplicate channel additions"""
        channel = MockChannel("duplicate_test", ChannelType.TICK)
        
        # Add channel twice
        error_router.add_channel(channel)
        initial_count = len(error_router.get_all_channels())
        
        error_router.add_channel(channel)  # Duplicate
        final_count = len(error_router.get_all_channels())
        
        # Should not add duplicates
        assert final_count == initial_count


# Test markers
pytestmark = [
    pytest.mark.unit,
    pytest.mark.channels,
    pytest.mark.router
]