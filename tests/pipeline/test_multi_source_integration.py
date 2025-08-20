"""
Integration tests for multi-source processing - Sprint 107

Tests end-to-end integration of the multi-source event processing system
including EventProcessor, MarketDataService, and channel integration.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock

from src.core.services.market_data_service import MarketDataService
from src.processing.pipeline.event_processor import EventProcessor, EventProcessingResult
from src.core.domain.market.tick import TickData
from src.shared.models.data_types import OHLCVData, FMVData


class TestMultiSourceIntegration:
    """Integration tests for multi-source processing system"""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing"""
        config = {
            'USE_SYNTHETIC_DATA': True,
            'USE_POLYGON_API': False,
            'MARKET_TIMEZONE': 'US/Eastern',
            'EXPECTED_CORE_UNIVERSE_MIN_SIZE': 100,
            'EXPECTED_CORE_UNIVERSE_MAX_SIZE': 200
        }
        return config
    
    @pytest.fixture
    def mock_data_provider(self):
        """Mock data provider"""
        return Mock()
    
    @pytest.fixture
    def mock_event_manager(self):
        """Mock event manager"""
        manager = Mock()
        manager.get_detector.return_value = Mock()
        return manager
    
    @pytest.fixture
    def mock_cache_control(self):
        """Mock cache control"""
        cache = Mock()
        cache.get_default_universe.return_value = ['AAPL', 'MSFT', 'GOOGL'] * 50  # 150 tickers
        return cache
    
    @pytest.fixture
    def market_data_service(self, mock_config, mock_data_provider, mock_event_manager, mock_cache_control):
        """Create MarketDataService with mocked dependencies"""
        with patch('src.core.services.market_data_service.TickStockUniverseManager'):
            with patch('src.core.services.market_data_service.MarketMetrics'):
                with patch('src.core.services.market_data_service.WebSocketPublisher'):
                    with patch('src.core.services.market_data_service.UserSettingsService'):
                        with patch('src.core.services.market_data_service.SessionAccumulationManager'):
                            with patch('src.core.services.market_data_service.AnalyticsManager'):
                                with patch('src.core.services.market_data_service.BuySellMarketTracker'):
                                    service = MarketDataService(
                                        config=mock_config,
                                        data_provider=mock_data_provider,
                                        event_manager=mock_event_manager,
                                        cache_control=mock_cache_control
                                    )
                                    return service
    
    @pytest.fixture
    def sample_tick_data(self):
        """Sample tick data for testing"""
        return TickData(
            ticker='AAPL',
            price=150.25,
            volume=1000,
            timestamp=time.time(),
            market_status='REGULAR'
        )
    
    @pytest.fixture
    def sample_ohlcv_data(self):
        """Sample OHLCV data for testing"""
        return OHLCVData(
            ticker='AAPL',
            timestamp=time.time(),
            open=150.0,
            high=152.0,
            low=149.0,
            close=151.5,
            volume=50000,
            avg_volume=30000,
            percent_change=1.0
        )
    
    @pytest.fixture
    def sample_fmv_data(self):
        """Sample FMV data for testing"""
        return FMVData(
            ticker='AAPL',
            timestamp=time.time(),
            fmv=155.0,
            market_price=150.0,
            confidence=0.85,
            deviation_percent=3.33
        )
    
    def test_market_service_sprint_107_initialization(self, market_data_service):
        """Test that MarketDataService initializes Sprint 107 components"""
        # Should have channel router
        assert hasattr(market_data_service, 'channel_router')
        assert market_data_service.channel_router is not None
        
        # EventProcessor should have multi-source components
        event_processor = market_data_service.event_processor
        assert hasattr(event_processor, 'source_context_manager')
        assert hasattr(event_processor, 'source_rules_engine')
        assert hasattr(event_processor, 'multi_source_coordinator')
        
        # Channel router should be connected to event processor
        assert event_processor.channel_router is not None
    
    @pytest.mark.asyncio
    async def test_ohlcv_data_processing_integration(self, market_data_service, sample_ohlcv_data):
        """Test end-to-end OHLCV data processing"""
        # Mock priority manager
        market_data_service.priority_manager = Mock()
        
        # Process OHLCV data
        result = await market_data_service.handle_ohlcv_data(sample_ohlcv_data)
        
        assert isinstance(result, EventProcessingResult)
        assert result.ticker == 'AAPL'
    
    @pytest.mark.asyncio
    async def test_fmv_data_processing_integration(self, market_data_service, sample_fmv_data):
        """Test end-to-end FMV data processing"""
        # Mock priority manager
        market_data_service.priority_manager = Mock()
        
        # Process FMV data
        result = await market_data_service.handle_fmv_data(sample_fmv_data)
        
        assert isinstance(result, EventProcessingResult)
        assert result.ticker == 'AAPL'
    
    def test_websocket_tick_backward_compatibility(self, market_data_service, sample_tick_data):
        """Test that existing WebSocket tick processing still works"""
        # Mock required components
        market_data_service.priority_manager = Mock()
        market_data_service.current_session = 'REGULAR'
        
        with patch('datetime') as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = '10:30:00'
            
            result = market_data_service.handle_websocket_tick(sample_tick_data)
            
            assert isinstance(result, EventProcessingResult)
            assert result.ticker == 'AAPL'
    
    @pytest.mark.asyncio
    async def test_multi_source_event_coordination(self, market_data_service, sample_tick_data, sample_ohlcv_data):
        """Test coordination between multiple data sources"""
        # Mock priority manager
        market_data_service.priority_manager = Mock()
        
        # Process data from different sources for same ticker
        tick_result = await market_data_service.event_processor.handle_multi_source_data(
            sample_tick_data, "websocket_tick"
        )
        
        ohlcv_result = await market_data_service.handle_ohlcv_data(sample_ohlcv_data)
        
        # Both should process
        assert tick_result.ticker == 'AAPL'
        assert ohlcv_result.ticker == 'AAPL'
        
        # Check coordination statistics
        coordinator = market_data_service.event_processor.multi_source_coordinator
        stats = coordinator.get_coordination_statistics()
        assert stats['total_events_received'] >= 0
    
    def test_source_specific_rule_filtering(self, market_data_service):
        """Test that source-specific rules filter data appropriately"""
        # Create OHLCV data that should be filtered (low percent change)
        filtered_data = OHLCVData(
            ticker='AAPL',
            timestamp=time.time(),
            open=150.0,
            high=150.1,
            low=149.9,
            close=150.05,
            volume=1000,
            avg_volume=30000,
            percent_change=0.03  # Very small change, should be filtered
        )
        
        async def run_test():
            result = await market_data_service.handle_ohlcv_data(filtered_data)
            # Should be filtered by source rules
            assert not result.success or "filtered" in str(result.warnings)
        
        asyncio.run(run_test())
    
    def test_source_context_tracking(self, market_data_service, sample_tick_data):
        """Test that source context is properly tracked"""
        context_manager = market_data_service.event_processor.source_context_manager
        
        # Create context and check tracking
        context = context_manager.create_context(sample_tick_data)
        
        assert context.ticker == 'AAPL'
        assert context.source_type.value in ['tick', 'websocket']
        
        # Check statistics
        stats = context_manager.get_source_statistics()
        assert stats['total_contexts'] >= 1
    
    def test_performance_monitoring_integration(self, market_data_service, sample_tick_data):
        """Test performance monitoring across the system"""
        # Process some data
        for _ in range(5):
            market_data_service.handle_websocket_tick(sample_tick_data)
        
        # Check EventProcessor performance
        event_processor = market_data_service.event_processor
        perf_report = event_processor.get_performance_report()
        
        assert 'data_flow_stats' in perf_report
        assert perf_report['data_flow_stats']['ticks_received'] >= 5
        
        # Check source rules performance
        rules_engine = event_processor.source_rules_engine
        rules_stats = rules_engine.get_rule_statistics()
        
        assert 'global_stats' in rules_stats
        assert 'rule_performance' in rules_stats
    
    def test_error_handling_across_components(self, market_data_service):
        """Test error handling across the integrated system"""
        # Test with invalid data
        async def run_test():
            result = await market_data_service.handle_ohlcv_data("invalid_data")
            assert not result.success
            assert len(result.errors) > 0
        
        asyncio.run(run_test())
    
    @pytest.mark.asyncio
    async def test_data_type_conversion_integration(self, market_data_service):
        """Test automatic data type conversion"""
        # Test with dictionary data that should be converted to typed data
        ohlcv_dict = {
            'ticker': 'AAPL',
            'timestamp': time.time(),
            'open': 150.0,
            'high': 152.0,
            'low': 149.0,
            'close': 151.5,
            'volume': 50000,
            'avg_volume': 30000,
            'percent_change': 1.0
        }
        
        result = await market_data_service.handle_ohlcv_data(ohlcv_dict)
        
        # Should successfully convert and process
        assert isinstance(result, EventProcessingResult)
        assert result.ticker == 'AAPL'
    
    def test_channel_router_integration(self, market_data_service):
        """Test channel router integration with event processor"""
        channel_router = market_data_service.channel_router
        event_processor = market_data_service.event_processor
        
        # Should be properly connected
        assert event_processor.channel_router == channel_router
        
        # Channel router should have reference to event processor
        assert channel_router._event_processor == event_processor
    
    def test_statistics_aggregation_across_components(self, market_data_service, sample_tick_data):
        """Test statistics aggregation across all components"""
        # Process some data
        for i in range(3):
            market_data_service.handle_websocket_tick(sample_tick_data)
        
        # Gather statistics from all components
        event_processor = market_data_service.event_processor
        
        # EventProcessor stats
        ep_stats = event_processor.get_performance_report()
        assert ep_stats['data_flow_stats']['ticks_received'] >= 3
        
        # Source context stats
        context_stats = event_processor.source_context_manager.get_source_statistics()
        assert context_stats['total_contexts'] >= 0
        
        # Rules engine stats
        rules_stats = event_processor.source_rules_engine.get_rule_statistics()
        assert 'global_stats' in rules_stats
        
        # Coordination stats
        coord_stats = event_processor.multi_source_coordinator.get_coordination_statistics()
        assert 'total_events_received' in coord_stats


class TestChannelIntegration:
    """Test integration with channel infrastructure"""
    
    @pytest.fixture
    def mock_channel(self):
        """Mock processing channel"""
        from src.processing.channels.base_channel import ProcessingChannel, ChannelType, ChannelStatus
        
        channel = Mock(spec=ProcessingChannel)
        channel.name = "test_channel"
        channel.channel_id = "test_id"
        channel.channel_type = ChannelType.TICK
        channel.status = ChannelStatus.ACTIVE
        channel.is_healthy.return_value = True
        channel.submit_data = AsyncMock(return_value=True)
        
        return channel
    
    @pytest.mark.asyncio
    async def test_channel_registration_and_routing(self, mock_channel):
        """Test channel registration and data routing"""
        from src.processing.channels.channel_router import DataChannelRouter, RouterConfig
        
        router = DataChannelRouter(RouterConfig())
        router.register_channel(mock_channel)
        
        # Test routing
        sample_data = TickData(
            ticker='AAPL',
            price=150.0,
            volume=1000,
            timestamp=time.time(),
            market_status='REGULAR'
        )
        
        await router.start()
        result = await router.route_data(sample_data)
        await router.stop()
        
        # Should have attempted to route data
        mock_channel.submit_data.assert_called_once()
    
    def test_channel_health_monitoring(self, mock_channel):
        """Test channel health monitoring integration"""
        from src.processing.channels.channel_router import DataChannelRouter, RouterConfig
        
        router = DataChannelRouter(RouterConfig())
        router.register_channel(mock_channel)
        
        # Get channel status
        status = router.get_channel_status()
        
        assert 'tick' in status
        assert len(status['tick']) == 1
        assert status['tick'][0]['healthy'] is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])