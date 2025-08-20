"""
Unit tests for EventProcessor multi-channel refactor - Sprint 107

Tests the refactored EventProcessor with multi-source integration,
source context management, and channel routing capabilities.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock
from dataclasses import dataclass

from src.processing.pipeline.event_processor import EventProcessor, EventProcessingResult
from src.core.domain.market.tick import TickData
from src.shared.models.data_types import OHLCVData, FMVData
from src.processing.pipeline.source_context_manager import SourceContext, DataSource
from src.core.domain.events.highlow import HighLowEvent


@dataclass
class MockConfig:
    """Mock configuration for testing"""
    def get(self, key, default=None):
        config_values = {
            'EXPECTED_CORE_UNIVERSE_MIN_SIZE': 100,
            'EXPECTED_CORE_UNIVERSE_MAX_SIZE': 200,
            'USE_SYNTHETIC_DATA': True
        }
        return config_values.get(key, default)


class TestEventProcessorRefactor:
    """Test suite for EventProcessor multi-channel integration"""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration"""
        return MockConfig()
    
    @pytest.fixture
    def mock_market_service(self):
        """Mock market service with required dependencies"""
        service = Mock()
        service.tickstock_universe_manager = Mock()
        service.tickstock_universe_manager.get_core_universe.return_value = ['AAPL', 'MSFT', 'GOOGL'] * 50  # 150 tickers
        service.tickstock_universe_manager.is_stock_in_core_universe.return_value = True
        
        service.buysell_market_tracker = Mock()
        service.session_accumulation_manager = Mock()
        service.market_analytics_manager = Mock()
        service.cache_control = Mock()
        service.market_metrics = Mock()
        service.priority_manager = Mock()
        service.stock_details = {}
        service.changed_tickers = set()
        
        return service
    
    @pytest.fixture
    def mock_event_manager(self):
        """Mock event manager"""
        manager = Mock()
        manager.get_detector.return_value = Mock()
        return manager
    
    @pytest.fixture
    def event_processor(self, mock_config, mock_market_service, mock_event_manager):
        """Create EventProcessor instance for testing"""
        return EventProcessor(
            config=mock_config,
            market_service=mock_market_service,
            event_manager=mock_event_manager
        )
    
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
    
    def test_initialization_with_sprint_107_components(self, event_processor):
        """Test that Sprint 107 components are properly initialized"""
        # Check that new components exist
        assert hasattr(event_processor, 'source_context_manager')
        assert hasattr(event_processor, 'source_rules_engine')
        assert hasattr(event_processor, 'multi_source_coordinator')
        
        # Check that components are properly initialized
        assert event_processor.source_context_manager is not None
        assert event_processor.source_rules_engine is not None
        assert event_processor.multi_source_coordinator is not None
        
        # Channel router should be None initially (set by market service)
        assert event_processor.channel_router is None
    
    def test_set_channel_router(self, event_processor):
        """Test setting channel router"""
        mock_router = Mock()
        mock_router.set_event_processor = Mock()
        
        event_processor.set_channel_router(mock_router)
        
        assert event_processor.channel_router == mock_router
        mock_router.set_event_processor.assert_called_once_with(event_processor)
    
    @pytest.mark.asyncio
    async def test_handle_multi_source_data_with_tick_data(self, event_processor, sample_tick_data):
        """Test multi-source data handling with tick data"""
        # Mock the channel router
        mock_router = AsyncMock()
        mock_result = Mock()
        mock_result.success = True
        mock_result.events = [Mock(spec=HighLowEvent)]
        mock_router.route_data.return_value = mock_result
        
        event_processor.set_channel_router(mock_router)
        
        # Test processing
        result = await event_processor.handle_multi_source_data(sample_tick_data, "test_source")
        
        assert isinstance(result, EventProcessingResult)
        assert result.ticker == 'AAPL'
        mock_router.route_data.assert_called_once_with(sample_tick_data)
    
    @pytest.mark.asyncio
    async def test_handle_multi_source_data_without_channel_router(self, event_processor, sample_tick_data):
        """Test multi-source data handling fallback when no channel router"""
        # Mock the handle_tick method for fallback
        with patch.object(event_processor, 'handle_tick') as mock_handle_tick:
            mock_handle_tick.return_value = EventProcessingResult(success=True, events_processed=1)
            
            result = await event_processor.handle_multi_source_data(sample_tick_data, "test_source")
            
            assert result.success
            assert "No channel router available" in result.warnings
            mock_handle_tick.assert_called_once_with(sample_tick_data)
    
    @pytest.mark.asyncio
    async def test_handle_multi_source_data_with_source_rules_filtering(self, event_processor, sample_ohlcv_data):
        """Test that source rules can filter out data"""
        # Mock source rules to return False (filter out)
        event_processor.source_rules_engine.apply_rules = Mock(return_value=False)
        
        result = await event_processor.handle_multi_source_data(sample_ohlcv_data, "ohlcv_source")
        
        assert not result.success
        assert "Data filtered by source rules" in result.warnings[0]
        event_processor.source_rules_engine.apply_rules.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_multi_source_data_with_coordination(self, event_processor, sample_tick_data):
        """Test event coordination in multi-source processing"""
        # Mock components
        mock_router = AsyncMock()
        mock_event = Mock(spec=HighLowEvent)
        mock_event.type = 'high'
        mock_result = Mock()
        mock_result.success = True
        mock_result.events = [mock_event]
        mock_router.route_data.return_value = mock_result
        
        event_processor.set_channel_router(mock_router)
        event_processor.multi_source_coordinator.coordinate_event = Mock(return_value=True)
        event_processor.multi_source_coordinator.get_pending_events = Mock(return_value=[])
        
        result = await event_processor.handle_multi_source_data(sample_tick_data, "test_source")
        
        assert result.success
        assert result.events_processed == 1
        event_processor.multi_source_coordinator.coordinate_event.assert_called_once_with(mock_event, result)
    
    def test_backward_compatibility_handle_tick(self, event_processor, sample_tick_data):
        """Test that existing handle_tick method still works"""
        # Mock required components for tick processing
        event_processor.tick_processor.process_tick = Mock()
        event_processor.tick_processor.process_tick.return_value = Mock(success=True, processed_tick=sample_tick_data)
        
        event_processor.event_detector.detect_events = Mock()
        event_processor.event_detector.detect_events.return_value = Mock(success=True, events_detected=[])
        
        result = event_processor.handle_tick(sample_tick_data)
        
        assert isinstance(result, EventProcessingResult)
        assert result.ticker == 'AAPL'
    
    def test_source_context_creation(self, event_processor, sample_ohlcv_data):
        """Test source context creation"""
        context = event_processor.source_context_manager.create_context(sample_ohlcv_data)
        
        assert isinstance(context, SourceContext)
        assert context.ticker == 'AAPL'
        assert context.source_type == DataSource.OHLCV
        assert context.processing_start_time is not None
    
    def test_source_rules_application(self, event_processor, sample_fmv_data):
        """Test source-specific rules application"""
        context = event_processor.source_context_manager.create_context(sample_fmv_data)
        
        # Should pass with good confidence and reasonable deviation
        result = event_processor.source_rules_engine.apply_rules(sample_fmv_data, context)
        assert result is True
        
        # Should fail with low confidence
        sample_fmv_data.confidence = 0.5  # Below 0.7 threshold
        result = event_processor.source_rules_engine.apply_rules(sample_fmv_data, context)
        assert result is False
    
    def test_performance_monitoring(self, event_processor, sample_tick_data):
        """Test performance monitoring and statistics"""
        initial_stats = event_processor.stats
        initial_count = initial_stats.ticks_received
        
        # Process some ticks
        for _ in range(5):
            event_processor.handle_tick(sample_tick_data)
        
        assert event_processor.stats.ticks_received == initial_count + 5
    
    def test_error_handling_in_multi_source_processing(self, event_processor):
        """Test error handling in multi-source processing"""
        # Test with invalid data
        invalid_data = "not_a_data_object"
        
        async def run_test():
            result = await event_processor.handle_multi_source_data(invalid_data, "test_source")
            assert not result.success
            assert len(result.errors) > 0
        
        asyncio.run(run_test())
    
    def test_statistics_and_monitoring_integration(self, event_processor):
        """Test integration with statistics and monitoring systems"""
        # Test that performance report can be generated
        report = event_processor.get_performance_report()
        
        assert 'data_flow_stats' in report
        assert 'component_stats' in report
        assert 'timestamp' in report
        
        # Check that new components are included
        component_stats = report['component_stats']
        assert 'tick_processor' in component_stats
        assert 'event_detector' in component_stats


class TestSourceContextManager:
    """Test suite for SourceContextManager"""
    
    @pytest.fixture
    def context_manager(self):
        """Create SourceContextManager instance"""
        from src.processing.pipeline.source_context_manager import SourceContextManager
        return SourceContextManager()
    
    @pytest.fixture
    def sample_tick_data(self):
        """Sample tick data"""
        return TickData(
            ticker='AAPL',
            price=150.25,
            volume=1000,
            timestamp=time.time(),
            market_status='REGULAR'
        )
    
    def test_create_context_from_tick_data(self, context_manager, sample_tick_data):
        """Test creating context from tick data"""
        context = context_manager.create_context(sample_tick_data)
        
        assert context.ticker == 'AAPL'
        assert context.source_type == DataSource.TICK
        assert context.timestamp == sample_tick_data.timestamp
        assert context.processing_start_time is not None
    
    def test_source_rules_application(self, context_manager, sample_tick_data):
        """Test applying source-specific rules"""
        context = context_manager.create_context(sample_tick_data)
        
        # Should pass basic validation
        result = context_manager.apply_source_rules(sample_tick_data, context)
        assert result is True
    
    def test_context_cleanup(self, context_manager, sample_tick_data):
        """Test context cleanup functionality"""
        # Create some contexts
        for i in range(5):
            context_manager.create_context(sample_tick_data)
        
        initial_count = len(context_manager._context_store)
        
        # Force cleanup
        context_manager.cleanup_old_contexts(force=True)
        
        # Contexts should still exist (not old enough)
        assert len(context_manager._context_store) == initial_count
    
    def test_statistics_gathering(self, context_manager, sample_tick_data):
        """Test statistics gathering"""
        # Create some contexts
        for i in range(3):
            context_manager.create_context(sample_tick_data)
        
        stats = context_manager.get_source_statistics()
        
        assert stats['total_contexts'] == 3
        assert 'contexts_by_source' in stats
        assert 'contexts_by_ticker' in stats


class TestSourceSpecificRulesEngine:
    """Test suite for SourceSpecificRulesEngine"""
    
    @pytest.fixture
    def rules_engine(self):
        """Create SourceSpecificRulesEngine instance"""
        from src.processing.rules.source_specific_rules import SourceSpecificRulesEngine
        return SourceSpecificRulesEngine()
    
    @pytest.fixture
    def sample_context(self):
        """Sample source context"""
        from src.processing.pipeline.source_context_manager import SourceContext, DataSource
        return SourceContext(
            source_type=DataSource.OHLCV,
            source_id="test_context",
            timestamp=time.time(),
            ticker="AAPL"
        )
    
    def test_default_rules_initialization(self, rules_engine):
        """Test that default rules are properly initialized"""
        stats = rules_engine.get_rule_statistics()
        
        # Should have some rules for each source type
        assert len(stats['rule_performance']) > 0
        assert 'rules_by_source' in stats
    
    def test_ohlcv_rule_application(self, rules_engine, sample_context):
        """Test OHLCV-specific rules"""
        # Create OHLCV data that should pass
        good_data = Mock()
        good_data.percent_change = 2.0  # Above 1% threshold
        good_data.volume = 3000
        good_data.avg_volume = 1000  # 3x multiplier
        
        result = rules_engine.apply_rules(good_data, sample_context)
        assert result is True
        
        # Create OHLCV data that should fail
        bad_data = Mock()
        bad_data.percent_change = 0.5  # Below 1% threshold
        bad_data.volume = 1000
        bad_data.avg_volume = 1000  # 1x multiplier
        
        result = rules_engine.apply_rules(bad_data, sample_context)
        assert result is False
    
    def test_rule_performance_tracking(self, rules_engine, sample_context):
        """Test rule performance tracking"""
        data = Mock()
        data.percent_change = 2.0
        data.volume = 3000
        data.avg_volume = 1000
        
        # Execute rules multiple times
        for _ in range(5):
            rules_engine.apply_rules(data, sample_context)
        
        stats = rules_engine.get_rule_statistics()
        assert stats['global_stats']['total_executions'] >= 5
    
    def test_custom_rule_addition(self, rules_engine):
        """Test adding custom rules"""
        from src.processing.rules.source_specific_rules import ProcessingRule, RuleType
        from src.processing.pipeline.source_context_manager import DataSource
        
        custom_rule = ProcessingRule(
            name="test_custom_rule",
            rule_type=RuleType.FILTER,
            source_types=[DataSource.TICK],
            condition=lambda data, ctx: True,
            description="Test custom rule"
        )
        
        rules_engine.add_rule(custom_rule)
        
        stats = rules_engine.get_rule_statistics()
        rule_names = [rule['name'] for rule in stats['rule_performance']]
        assert "test_custom_rule" in rule_names


class TestMultiSourceCoordinator:
    """Test suite for MultiSourceCoordinator"""
    
    @pytest.fixture
    def coordinator(self):
        """Create MultiSourceCoordinator instance"""
        from src.processing.pipeline.multi_source_coordinator import MultiSourceCoordinator
        return MultiSourceCoordinator()
    
    @pytest.fixture
    def sample_event(self):
        """Sample event for coordination"""
        event = Mock()
        event.ticker = 'AAPL'
        event.type = 'high'
        event.time = time.time()
        return event
    
    @pytest.fixture
    def sample_context(self):
        """Sample source context"""
        from src.processing.pipeline.source_context_manager import SourceContext, DataSource
        return SourceContext(
            source_type=DataSource.TICK,
            source_id="test_context",
            timestamp=time.time(),
            ticker="AAPL"
        )
    
    def test_single_event_coordination(self, coordinator, sample_event, sample_context):
        """Test coordination with single event (no conflict)"""
        result = coordinator.coordinate_event(sample_event, sample_context)
        assert result is True
        
        # Should emit immediately for single event
        pending = coordinator.get_pending_events(max_events=10)
        assert len(pending) == 1
    
    def test_multi_source_conflict_resolution(self, coordinator, sample_context):
        """Test conflict resolution between multiple sources"""
        from src.processing.pipeline.source_context_manager import DataSource
        
        # Create two events from different sources
        event1 = Mock()
        event1.ticker = 'AAPL'
        event1.type = 'high'
        event1.time = time.time()
        
        event2 = Mock()
        event2.ticker = 'AAPL'
        event2.type = 'high'
        event2.time = time.time() + 1  # Slightly later
        
        context1 = sample_context
        context2 = SourceContext(
            source_type=DataSource.OHLCV,
            source_id="test_context_2",
            timestamp=time.time(),
            ticker="AAPL"
        )
        
        # Submit events
        coordinator.coordinate_event(event1, context1)
        coordinator.coordinate_event(event2, context2)
        
        # Force emit
        coordinator.force_emit_pending_coordinations()
        
        # Should have resolved conflict
        stats = coordinator.get_coordination_statistics()
        assert stats['conflicts_detected'] >= 1
    
    def test_coordination_statistics(self, coordinator, sample_event, sample_context):
        """Test coordination statistics collection"""
        # Process some events
        for i in range(3):
            event = Mock()
            event.ticker = f'TICK{i}'
            event.type = 'high'
            event.time = time.time()
            coordinator.coordinate_event(event, sample_context)
        
        stats = coordinator.get_coordination_statistics()
        
        assert stats['total_events_received'] == 3
        assert 'events_by_source' in stats
        assert 'active_coordinations' in stats


if __name__ == '__main__':
    pytest.main([__file__, '-v'])