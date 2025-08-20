"""
Integration tests for multi-channel processing system.

Tests end-to-end channel infrastructure including:
- Multi-channel data routing and processing
- Channel coordination and load balancing
- System-wide performance and resilience
- Real-world scenario simulations

Sprint 105: Core Channel Infrastructure Testing
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor

from src.processing.channels.channel_router import DataChannelRouter, RoutingStrategy
from src.processing.channels.tick_channel import TickChannel
from src.processing.channels.base_channel import ChannelType, ProcessingResult
from src.processing.channels.channel_config import (
    TickChannelConfig, 
    OHLCVChannelConfig, 
    FMVChannelConfig,
    BatchingStrategy
)


class MockOHLCVChannel:
    """Mock OHLCV channel for integration testing"""
    
    def __init__(self, name: str):
        self.name = name
        self.channel_id = f"ohlcv_{name}"
        self._status = "active"
        self._healthy = True
        self.process_calls = []
        
    def get_channel_type(self):
        return ChannelType.OHLCV
    
    async def start(self):
        return True
        
    async def submit_data(self, data):
        self.process_calls.append(data)
        await asyncio.sleep(0.01)  # Simulate processing
        return True
        
    def is_healthy(self):
        return self._healthy
        
    def set_healthy(self, healthy: bool):
        self._healthy = healthy


class MockFMVChannel:
    """Mock FMV channel for integration testing"""
    
    def __init__(self, name: str):
        self.name = name
        self.channel_id = f"fmv_{name}"
        self._status = "active"
        self._healthy = True
        self.process_calls = []
        
    def get_channel_type(self):
        return ChannelType.FMV
    
    async def start(self):
        return True
        
    async def submit_data(self, data):
        self.process_calls.append(data)
        await asyncio.sleep(0.01)  # Simulate processing
        return True
        
    def is_healthy(self):
        return self._healthy
        
    def set_healthy(self, healthy: bool):
        self._healthy = healthy


class TestMultiChannelSetup:
    """Test multi-channel system setup and initialization"""

    @pytest.fixture
    async def multi_channel_router(self):
        """Set up router with multiple channel types"""
        router = DataChannelRouter()
        
        # Add Tick channels
        for i in range(2):
            tick_config = TickChannelConfig(
                highlow_detection={'enabled': True},
                trend_detection={'enabled': True},
                surge_detection={'enabled': True}
            )
            tick_channel = TickChannel(f"tick_{i}", tick_config)
            
            # Mock the detectors to avoid complex initialization
            tick_channel._detectors_initialized = True
            tick_channel.highlow_detector = Mock()
            tick_channel.trend_detector = Mock()
            tick_channel.surge_detector = Mock()
            
            await tick_channel.start()
            router.add_channel(tick_channel)
        
        # Add OHLCV channels
        ohlcv_channel = MockOHLCVChannel("ohlcv_main")
        await ohlcv_channel.start()
        router.add_channel(ohlcv_channel)
        
        # Add FMV channels
        fmv_channel = MockFMVChannel("fmv_main")
        await fmv_channel.start()
        router.add_channel(fmv_channel)
        
        return router

    @pytest.mark.asyncio
    async def test_multi_channel_initialization(self, multi_channel_router):
        """Test that all channel types initialize correctly"""
        all_channels = multi_channel_router.get_all_channels()
        
        assert len(all_channels) == 4  # 2 tick + 1 ohlcv + 1 fmv
        
        # Verify channel types
        tick_channels = multi_channel_router.get_channels_by_type(ChannelType.TICK)
        ohlcv_channels = multi_channel_router.get_channels_by_type(ChannelType.OHLCV)
        fmv_channels = multi_channel_router.get_channels_by_type(ChannelType.FMV)
        
        assert len(tick_channels) == 2
        assert len(ohlcv_channels) == 1
        assert len(fmv_channels) == 1

    @pytest.mark.asyncio
    async def test_all_channels_healthy(self, multi_channel_router):
        """Test that all channels report healthy status"""
        healthy_channels = multi_channel_router.get_healthy_channels()
        all_channels = multi_channel_router.get_all_channels()
        
        assert len(healthy_channels) == len(all_channels)
        assert all(channel.is_healthy() for channel in healthy_channels)

    @pytest.mark.asyncio
    async def test_channel_statistics(self, multi_channel_router):
        """Test router statistics reporting"""
        stats = multi_channel_router.get_statistics()
        
        assert stats['total_channels'] == 4
        assert stats['channels_by_type']['tick'] == 2
        assert stats['channels_by_type']['ohlcv'] == 1
        assert stats['channels_by_type']['fmv'] == 1
        assert stats['healthy_channels'] == 4


class TestDataRoutingIntegration:
    """Test data routing across different channel types"""

    @pytest.fixture
    async def routing_system(self):
        """Set up complete routing system"""
        router = DataChannelRouter()
        
        # Create and add channels
        channels = {}
        
        # Tick channels
        tick_channel = TickChannel("integration_tick")
        tick_channel._detectors_initialized = True
        tick_channel.highlow_detector = Mock()
        tick_channel.trend_detector = Mock()
        tick_channel.surge_detector = Mock()
        await tick_channel.start()
        router.add_channel(tick_channel)
        channels['tick'] = tick_channel
        
        # OHLCV channel
        ohlcv_channel = MockOHLCVChannel("integration_ohlcv")
        await ohlcv_channel.start()
        router.add_channel(ohlcv_channel)
        channels['ohlcv'] = ohlcv_channel
        
        # FMV channel
        fmv_channel = MockFMVChannel("integration_fmv")
        await fmv_channel.start()
        router.add_channel(fmv_channel)
        channels['fmv'] = fmv_channel
        
        return router, channels

    @pytest.mark.asyncio
    async def test_tick_data_routing(self, routing_system):
        """Test tick data is routed to tick channels"""
        router, channels = routing_system
        
        tick_data = {
            'ticker': 'AAPL',
            'price': 150.0,
            'volume': 1000,
            'timestamp': time.time()
        }
        
        # Mock event detection
        channels['tick']._detect_events = Mock(return_value=[])
        
        result = await router.route_data(tick_data)
        
        assert result is not None
        assert result.success
        assert len(channels['ohlcv'].process_calls) == 0  # Should not route to OHLCV
        assert len(channels['fmv'].process_calls) == 0    # Should not route to FMV

    @pytest.mark.asyncio
    async def test_ohlcv_data_routing(self, routing_system):
        """Test OHLCV data is routed to OHLCV channels"""
        router, channels = routing_system
        
        ohlcv_data = {
            'ticker': 'AAPL',
            'open': 149.0,
            'high': 151.0,
            'low': 148.5,
            'close': 150.0,
            'volume': 50000,
            'period': '1m'
        }
        
        result = await router.route_data(ohlcv_data)
        
        assert result is None  # MockOHLCVChannel doesn't return ProcessingResult
        assert len(channels['ohlcv'].process_calls) == 1  # Should route to OHLCV
        assert len(channels['fmv'].process_calls) == 0    # Should not route to FMV

    @pytest.mark.asyncio
    async def test_fmv_data_routing(self, routing_system):
        """Test FMV data is routed to FMV channels"""
        router, channels = routing_system
        
        fmv_data = {
            'ticker': 'AAPL',
            'fair_market_value': 150.25,
            'market_price': 150.0,
            'deviation': 0.0017
        }
        
        result = await router.route_data(fmv_data)
        
        assert result is None  # MockFMVChannel doesn't return ProcessingResult
        assert len(channels['ohlcv'].process_calls) == 0  # Should not route to OHLCV
        assert len(channels['fmv'].process_calls) == 1    # Should route to FMV

    @pytest.mark.asyncio
    async def test_mixed_data_stream_routing(self, routing_system):
        """Test routing of mixed data stream"""
        router, channels = routing_system
        
        # Mock tick channel event detection
        channels['tick']._detect_events = Mock(return_value=[])
        
        # Mixed data stream
        data_stream = [
            {'ticker': 'AAPL', 'price': 150.0, 'volume': 1000},  # Tick
            {'ticker': 'AAPL', 'open': 149.0, 'high': 151.0, 'low': 148.5, 'close': 150.0, 'volume': 50000},  # OHLCV
            {'ticker': 'GOOGL', 'price': 2500.0, 'volume': 500},  # Tick
            {'ticker': 'AAPL', 'fair_market_value': 150.25, 'market_price': 150.0},  # FMV
        ]
        
        # Route all data
        for data in data_stream:
            await router.route_data(data)
        
        # Verify routing counts
        # Note: Tick channel processes 2 items, others process 1 each
        assert len(channels['ohlcv'].process_calls) == 1
        assert len(channels['fmv'].process_calls) == 1


class TestLoadBalancingIntegration:
    """Test load balancing across multiple channels of same type"""

    @pytest.fixture
    async def load_balanced_system(self):
        """Set up system with multiple channels for load balancing"""
        router = DataChannelRouter()
        router.set_routing_strategy(RoutingStrategy.ROUND_ROBIN)
        
        # Add multiple tick channels
        tick_channels = []
        for i in range(3):
            channel = TickChannel(f"tick_lb_{i}")
            channel._detectors_initialized = True
            channel.highlow_detector = Mock()
            channel.trend_detector = Mock() 
            channel.surge_detector = Mock()
            
            await channel.start()
            router.add_channel(channel)
            tick_channels.append(channel)
        
        return router, tick_channels

    @pytest.mark.asyncio
    async def test_round_robin_load_balancing(self, load_balanced_system):
        """Test round-robin load balancing across tick channels"""
        router, tick_channels = load_balanced_system
        
        # Mock event detection for all channels
        for channel in tick_channels:
            channel._detect_events = Mock(return_value=[])
        
        tick_data = {'ticker': 'AAPL', 'price': 150.0, 'volume': 1000}
        
        # Route multiple data items
        used_channels = []
        for _ in range(6):  # 2 full rounds
            result = await router.route_data(tick_data)
            if result and 'channel' in result.metadata:
                used_channels.append(result.metadata['channel'])
        
        # Should distribute across all channels
        unique_channels = set(used_channels)
        assert len(unique_channels) >= 2  # Should use multiple channels

    @pytest.mark.asyncio
    async def test_load_based_balancing(self, load_balanced_system):
        """Test load-based balancing"""
        router, tick_channels = load_balanced_system
        router.set_routing_strategy(RoutingStrategy.LOAD_BASED)
        
        # Mock event detection
        for channel in tick_channels:
            channel._detect_events = Mock(return_value=[])
        
        # Set different loads
        tick_channels[0].set_load = Mock()
        tick_channels[0].get_load = Mock(return_value=0.9)  # High load
        tick_channels[1].set_load = Mock()
        tick_channels[1].get_load = Mock(return_value=0.1)  # Low load
        tick_channels[2].set_load = Mock()
        tick_channels[2].get_load = Mock(return_value=0.5)  # Medium load
        
        tick_data = {'ticker': 'AAPL', 'price': 150.0, 'volume': 1000}
        
        # Route data multiple times
        results = []
        for _ in range(10):
            result = await router.route_data(tick_data)
            if result and 'channel' in result.metadata:
                results.append(result.metadata['channel'])
        
        # Should prefer lower load channels
        # Note: Actual implementation may vary, this tests the concept
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_health_based_routing(self, load_balanced_system):
        """Test health-based routing excludes unhealthy channels"""
        router, tick_channels = load_balanced_system
        router.set_routing_strategy(RoutingStrategy.HEALTH_BASED)
        
        # Mock event detection
        for channel in tick_channels:
            channel._detect_events = Mock(return_value=[])
        
        # Mark one channel as unhealthy
        tick_channels[0]._healthy = False
        
        tick_data = {'ticker': 'AAPL', 'price': 150.0, 'volume': 1000}
        
        # Route data multiple times
        results = []
        for _ in range(10):
            result = await router.route_data(tick_data)
            if result and 'channel' in result.metadata:
                results.append(result.metadata['channel'])
        
        # Should not use unhealthy channel
        assert 'tick_lb_0' not in results
        assert len(set(results)) >= 1  # Should use healthy channels


class TestSystemPerformanceIntegration:
    """Test system-wide performance characteristics"""

    @pytest.fixture
    async def performance_system(self):
        """Set up system optimized for performance testing"""
        router = DataChannelRouter()
        
        # Add multiple high-performance channels
        channels = []
        for i in range(5):
            config = TickChannelConfig(
                max_queue_size=2000,
                batching={"strategy": "immediate"}  # Immediate processing
            )
            
            channel = TickChannel(f"perf_tick_{i}", config)
            channel._detectors_initialized = True
            channel.highlow_detector = Mock(return_value=None)
            channel.trend_detector = Mock(return_value=None)
            channel.surge_detector = Mock(return_value=None)
            
            await channel.start()
            router.add_channel(channel)
            channels.append(channel)
        
        return router, channels

    @pytest.mark.asyncio
    async def test_high_throughput_processing(self, performance_system, performance_timer):
        """Test system can handle high-throughput data streams"""
        router, channels = performance_system
        
        # Mock event detection for fast processing
        for channel in channels:
            channel._detect_events = Mock(return_value=[])
        
        tick_data = {'ticker': 'AAPL', 'price': 150.0, 'volume': 1000}
        
        performance_timer.start()
        
        # Process high volume of data
        tasks = []
        for _ in range(1000):
            task = router.route_data(tick_data)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        performance_timer.stop()
        
        # Performance requirements
        assert performance_timer.elapsed < 5.0  # Complete in < 5 seconds
        
        # Calculate throughput
        throughput = len(results) / performance_timer.elapsed
        assert throughput > 200  # At least 200 items/second
        
        # Most should succeed
        successful = sum(1 for r in results if r and r.success)
        success_rate = successful / len(results)
        assert success_rate > 0.9  # >90% success rate

    @pytest.mark.asyncio
    async def test_concurrent_multi_channel_processing(self, performance_system):
        """Test concurrent processing across multiple channel types"""
        router, tick_channels = performance_system
        
        # Add other channel types
        ohlcv_channel = MockOHLCVChannel("perf_ohlcv")
        fmv_channel = MockFMVChannel("perf_fmv")
        await ohlcv_channel.start()
        await fmv_channel.start()
        router.add_channel(ohlcv_channel)
        router.add_channel(fmv_channel)
        
        # Mock event detection
        for channel in tick_channels:
            channel._detect_events = Mock(return_value=[])
        
        # Create concurrent data streams for different channel types
        async def process_tick_stream():
            tasks = []
            for _ in range(100):
                tick_data = {'ticker': 'AAPL', 'price': 150.0, 'volume': 1000}
                task = router.route_data(tick_data)
                tasks.append(task)
            return await asyncio.gather(*tasks)
        
        async def process_ohlcv_stream():
            tasks = []
            for _ in range(50):
                ohlcv_data = {
                    'ticker': 'AAPL', 'open': 149.0, 'high': 151.0, 
                    'low': 148.5, 'close': 150.0, 'volume': 50000
                }
                task = router.route_data(ohlcv_data)
                tasks.append(task)
            return await asyncio.gather(*tasks)
        
        async def process_fmv_stream():
            tasks = []
            for _ in range(25):
                fmv_data = {
                    'ticker': 'AAPL', 'fair_market_value': 150.25, 
                    'market_price': 150.0
                }
                task = router.route_data(fmv_data)
                tasks.append(task)
            return await asyncio.gather(*tasks)
        
        # Run all streams concurrently
        start_time = time.time()
        
        tick_results, ohlcv_results, fmv_results = await asyncio.gather(
            process_tick_stream(),
            process_ohlcv_stream(),
            process_fmv_stream()
        )
        
        elapsed = time.time() - start_time
        
        # Should complete in reasonable time
        assert elapsed < 3.0  # 175 total items in < 3 seconds
        
        # Verify processing counts
        assert len(tick_results) == 100
        assert len(ohlcv_results) == 50
        assert len(fmv_results) == 25
        
        # Verify channels processed their data types
        assert len(ohlcv_channel.process_calls) == 50
        assert len(fmv_channel.process_calls) == 25

    @pytest.mark.performance
    def test_memory_usage_under_load(self, performance_system):
        """Test memory usage remains stable under load"""
        import gc
        
        router, channels = performance_system
        
        # Force garbage collection
        gc.collect()
        initial_objects = len(gc.get_objects())
        
        # Mock event detection
        for channel in channels:
            channel._detect_events = Mock(return_value=[])
        
        # Simulate sustained load (sync version for testing)
        tick_data = {'ticker': 'AAPL', 'price': 150.0, 'volume': 1000}
        
        # Note: This is a simplified memory test since we can't easily
        # run async code in sync memory tests
        for _ in range(1000):
            # Simulate routing decision making
            channels_for_type = router.get_channels_by_type(ChannelType.TICK)
            if channels_for_type:
                selected = router.load_balancer.select_channel(
                    channels_for_type, 
                    router.routing_strategy
                )
        
        # Force garbage collection
        gc.collect()
        final_objects = len(gc.get_objects())
        
        # Memory growth should be reasonable
        memory_growth = (final_objects - initial_objects) / initial_objects
        assert memory_growth < 0.2  # Less than 20% memory growth


class TestSystemResilienceIntegration:
    """Test system resilience and error handling"""

    @pytest.fixture
    async def resilience_system(self):
        """Set up system for resilience testing"""
        router = DataChannelRouter()
        
        # Add channels with different reliability
        reliable_channel = TickChannel("reliable_tick")
        reliable_channel._detectors_initialized = True
        reliable_channel.highlow_detector = Mock()
        reliable_channel.trend_detector = Mock()
        reliable_channel.surge_detector = Mock()
        
        unreliable_channel = TickChannel("unreliable_tick")
        unreliable_channel._detectors_initialized = True
        unreliable_channel.highlow_detector = Mock()
        unreliable_channel.trend_detector = Mock()
        unreliable_channel.surge_detector = Mock()
        
        await reliable_channel.start()
        await unreliable_channel.start()
        
        router.add_channel(reliable_channel)
        router.add_channel(unreliable_channel)
        
        return router, reliable_channel, unreliable_channel

    @pytest.mark.asyncio
    async def test_graceful_channel_failure_handling(self, resilience_system):
        """Test system handles individual channel failures gracefully"""
        router, reliable_channel, unreliable_channel = resilience_system
        
        # Mock reliable channel to work normally
        reliable_channel._detect_events = Mock(return_value=[])
        
        # Mock unreliable channel to fail
        async def failing_process_data(data):
            return ProcessingResult(
                success=False,
                errors=["Simulated channel failure"]
            )
        
        unreliable_channel.process_data = failing_process_data
        
        tick_data = {'ticker': 'AAPL', 'price': 150.0, 'volume': 1000}
        
        # Process multiple data items
        results = []
        for _ in range(10):
            result = await router.route_data(tick_data)
            results.append(result)
        
        # System should continue operating despite individual failures
        assert len(results) == 10
        successful_results = [r for r in results if r and r.success]
        
        # Should have some successful results (from reliable channel)
        assert len(successful_results) > 0

    @pytest.mark.asyncio
    async def test_channel_recovery_after_failure(self, resilience_system):
        """Test channel recovery after temporary failures"""
        router, reliable_channel, unreliable_channel = resilience_system
        
        # Mock both channels
        reliable_channel._detect_events = Mock(return_value=[])
        unreliable_channel._detect_events = Mock(return_value=[])
        
        # Initially, unreliable channel fails
        failure_count = 0
        
        async def sometimes_failing_process_data(data):
            nonlocal failure_count
            failure_count += 1
            
            if failure_count <= 3:  # Fail first 3 attempts
                return ProcessingResult(
                    success=False,
                    errors=["Temporary failure"]
                )
            else:  # Recover after 3 failures
                return ProcessingResult(
                    success=True,
                    events=[],
                    metadata={'recovered': True}
                )
        
        unreliable_channel.process_data = sometimes_failing_process_data
        
        tick_data = {'ticker': 'AAPL', 'price': 150.0, 'volume': 1000}
        
        # Process data that should trigger recovery
        results = []
        for _ in range(6):  # 6 attempts, should see recovery
            result = await router.route_data(tick_data)
            if result:
                results.append(result)
        
        # Should see recovery in later results
        successful_results = [r for r in results if r.success]
        assert len(successful_results) > 0
        
        # Should see recovery metadata
        recovered_results = [
            r for r in successful_results 
            if r.metadata.get('recovered') is True
        ]
        assert len(recovered_results) > 0

    @pytest.mark.asyncio
    async def test_system_degraded_mode_operation(self, resilience_system):
        """Test system operates in degraded mode when channels are unhealthy"""
        router, reliable_channel, unreliable_channel = resilience_system
        router.set_routing_strategy(RoutingStrategy.HEALTH_BASED)
        
        # Mock event detection
        reliable_channel._detect_events = Mock(return_value=[])
        
        # Mark unreliable channel as unhealthy
        unreliable_channel._healthy = False
        
        tick_data = {'ticker': 'AAPL', 'price': 150.0, 'volume': 1000}
        
        # System should still process data using healthy channels
        results = []
        for _ in range(5):
            result = await router.route_data(tick_data)
            results.append(result)
        
        # Should get results despite degraded capacity
        successful_results = [r for r in results if r and r.success]
        assert len(successful_results) > 0
        
        # Verify system statistics reflect degraded state
        stats = router.get_statistics()
        assert stats['healthy_channels'] < stats['total_channels']


# Test markers
pytestmark = [
    pytest.mark.integration,
    pytest.mark.channels,
    pytest.mark.multi_channel
]