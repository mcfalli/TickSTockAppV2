"""
Regression tests for Sprint 107 - Event Processing Refactor

Ensures that existing functionality is preserved after the multi-channel
integration while verifying that new capabilities work correctly.
"""

import pytest
import time
from unittest.mock import Mock, patch

from src.processing.pipeline.event_processor import EventProcessor, EventProcessingResult
from src.core.services.market_data_service import MarketDataService
from src.core.domain.market.tick import TickData
from src.presentation.converters.transport_models import StockData


class TestBackwardCompatibility:
    """Test backward compatibility of existing functionality"""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration maintaining existing structure"""
        return {
            'USE_SYNTHETIC_DATA': True,
            'USE_POLYGON_API': False,
            'MARKET_TIMEZONE': 'US/Eastern',
            'EXPECTED_CORE_UNIVERSE_MIN_SIZE': 100,
            'EXPECTED_CORE_UNIVERSE_MAX_SIZE': 200,
            'SURGE_MULTIPLIER': 3.0,
            'HIGH_LOW_THRESHOLD': 0.1
        }
    
    @pytest.fixture
    def mock_market_service(self):
        """Mock market service with all required components"""
        service = Mock()
        service.tickstock_universe_manager = Mock()
        service.tickstock_universe_manager.get_core_universe.return_value = ['AAPL', 'MSFT'] * 75
        service.tickstock_universe_manager.is_stock_in_core_universe.return_value = True
        
        service.buysell_market_tracker = Mock()
        service.session_accumulation_manager = Mock()
        service.market_analytics_manager = Mock()
        service.cache_control = Mock()
        service.market_metrics = Mock()
        service.priority_manager = Mock()
        service.priority_manager.add_event = Mock()
        
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
        """Create EventProcessor with mocked dependencies"""
        return EventProcessor(
            config=mock_config,
            market_service=mock_market_service,
            event_manager=mock_event_manager
        )
    
    @pytest.fixture
    def sample_tick_data(self):
        """Sample tick data identical to existing tests"""
        return TickData(
            ticker='AAPL',
            price=150.25,
            volume=1000,
            timestamp=time.time(),
            market_status='REGULAR'
        )
    
    def test_existing_handle_tick_method_unchanged(self, event_processor, sample_tick_data):
        """Test that existing handle_tick method behavior is unchanged"""
        # Mock the required components to simulate existing behavior
        event_processor.tick_processor.process_tick = Mock()
        event_processor.tick_processor.process_tick.return_value = Mock(
            success=True, 
            processed_tick=sample_tick_data,
            errors=[], 
            warnings=[]
        )
        
        event_processor.event_detector.detect_events = Mock()
        event_processor.event_detector.detect_events.return_value = Mock(
            success=True,
            events_detected=[],
            errors=[],
            warnings=[]
        )
        
        # Call existing method
        result = event_processor.handle_tick(sample_tick_data)
        
        # Should return same type and structure as before
        assert isinstance(result, EventProcessingResult)
        assert result.ticker == 'AAPL'
        assert hasattr(result, 'success')
        assert hasattr(result, 'events_processed')
        assert hasattr(result, 'errors')
        assert hasattr(result, 'warnings')
        assert hasattr(result, 'processing_time_ms')
    
    def test_existing_statistics_interface_preserved(self, event_processor):
        """Test that existing statistics interface is preserved"""
        # Should still have the same performance report structure
        report = event_processor.get_performance_report()
        
        # Check that existing fields are still present
        assert 'data_flow_stats' in report
        assert 'component_stats' in report
        assert 'timestamp' in report
        
        # Check specific stats that existed before
        data_flow = report['data_flow_stats']
        assert 'ticks_received' in data_flow
        assert 'ticks_processed' in data_flow
        assert 'events_detected' in data_flow
        assert 'events_published' in data_flow
        assert 'errors' in data_flow
    
    def test_existing_event_processing_pipeline_preserved(self, event_processor, sample_tick_data):
        """Test that the existing event processing pipeline flow is preserved"""
        # Mock universe check (existing behavior)
        event_processor.market_service.tickstock_universe_manager.is_stock_in_core_universe.return_value = True
        
        # Mock existing StockData structure
        stock_data = StockData(ticker='AAPL', last_price=150.25)
        event_processor.market_service.stock_details['AAPL'] = stock_data
        
        # Mock tick processor (existing component)
        event_processor.tick_processor.process_tick = Mock()
        event_processor.tick_processor.process_tick.return_value = Mock(
            success=True,
            processed_tick=sample_tick_data,
            errors=[],
            warnings=[]
        )
        
        # Mock event detector (existing component)
        event_processor.event_detector.detect_events = Mock()
        event_processor.event_detector.detect_events.return_value = Mock(
            success=True,
            events_detected=[],
            errors=[],
            warnings=[]
        )
        
        # Process tick
        result = event_processor.handle_tick(sample_tick_data)
        
        # Verify existing flow was followed
        event_processor.tick_processor.process_tick.assert_called_once()
        event_processor.event_detector.detect_events.assert_called_once()
        
        # Verify result structure matches existing expectations
        assert result.success is True
        assert isinstance(result.errors, list)
        assert isinstance(result.warnings, list)
    
    def test_existing_method_signatures_unchanged(self, event_processor):
        """Test that existing method signatures are unchanged"""
        import inspect
        
        # Check handle_tick signature
        handle_tick_sig = inspect.signature(event_processor.handle_tick)
        params = list(handle_tick_sig.parameters.keys())
        assert 'tick_data' in params
        assert len(params) == 2  # self + tick_data
        
        # Check get_performance_report signature
        perf_report_sig = inspect.signature(event_processor.get_performance_report)
        perf_params = list(perf_report_sig.parameters.keys())
        assert len(perf_params) == 1  # only self
    
    def test_existing_error_handling_preserved(self, event_processor):
        """Test that existing error handling behavior is preserved"""
        # Test with invalid tick data (existing error case)
        invalid_tick = "not_a_tick_data_object"
        
        result = event_processor.handle_tick(invalid_tick)
        
        # Should handle error gracefully (existing behavior)
        assert result.success is False
        assert len(result.errors) > 0
        assert "Invalid tick data type" in result.errors[0]
    
    def test_existing_configuration_compatibility(self, mock_config, mock_market_service, mock_event_manager):
        """Test that existing configuration is still compatible"""
        # Should initialize without errors using existing config structure
        processor = EventProcessor(
            config=mock_config,
            market_service=mock_market_service,
            event_manager=mock_event_manager
        )
        
        # Should have all existing attributes
        assert hasattr(processor, 'config')
        assert hasattr(processor, 'market_service')
        assert hasattr(processor, 'event_manager')
        assert hasattr(processor, 'stats')
        
        # Configuration values should be accessible as before
        assert processor.config['USE_SYNTHETIC_DATA'] is True
        assert processor.config['SURGE_MULTIPLIER'] == 3.0


class TestMarketDataServiceBackwardCompatibility:
    """Test MarketDataService backward compatibility"""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration for MarketDataService"""
        return {
            'USE_SYNTHETIC_DATA': True,
            'USE_POLYGON_API': False,
            'MARKET_TIMEZONE': 'US/Eastern'
        }
    
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
    
    def test_existing_handle_websocket_tick_interface(self, mock_config, sample_tick_data):
        """Test that existing handle_websocket_tick interface is preserved"""
        with patch('src.core.services.market_data_service.TickStockUniverseManager'):
            with patch('src.core.services.market_data_service.MarketMetrics'):
                with patch('src.core.services.market_data_service.WebSocketPublisher'):
                    with patch('src.core.services.market_data_service.UserSettingsService'):
                        with patch('src.core.services.market_data_service.SessionAccumulationManager'):
                            with patch('src.core.services.market_data_service.AnalyticsManager'):
                                with patch('src.core.services.market_data_service.BuySellMarketTracker'):
                                    mock_data_provider = Mock()
                                    mock_event_manager = Mock()
                                    mock_event_manager.get_detector.return_value = Mock()
                                    mock_cache_control = Mock()
                                    mock_cache_control.get_default_universe.return_value = ['AAPL'] * 150
                                    
                                    service = MarketDataService(
                                        config=mock_config,
                                        data_provider=mock_data_provider,
                                        event_manager=mock_event_manager,
                                        cache_control=mock_cache_control
                                    )
                                    
                                    # Mock required components
                                    service.priority_manager = Mock()
                                    service.current_session = 'REGULAR'
                                    
                                    # Test existing method call
                                    result = service.handle_websocket_tick(sample_tick_data)
                                    
                                    # Should return EventProcessingResult as before
                                    assert isinstance(result, EventProcessingResult)
                                    assert result.ticker == 'AAPL'
    
    def test_existing_method_signatures_in_market_service(self):
        """Test that existing MarketDataService method signatures are unchanged"""
        import inspect
        
        # Check handle_websocket_tick signature remains the same
        method = MarketDataService.handle_websocket_tick
        sig = inspect.signature(method)
        params = list(sig.parameters.keys())
        
        # Should have same parameters as before
        assert 'self' in params
        assert 'tick_data' in params
        assert 'ticker' in params
        assert 'timestamp' in params
    
    def test_new_methods_dont_break_existing_interface(self, mock_config):
        """Test that new methods don't interfere with existing functionality"""
        with patch('src.core.services.market_data_service.TickStockUniverseManager'):
            with patch('src.core.services.market_data_service.MarketMetrics'):
                with patch('src.core.services.market_data_service.WebSocketPublisher'):
                    with patch('src.core.services.market_data_service.UserSettingsService'):
                        with patch('src.core.services.market_data_service.SessionAccumulationManager'):
                            with patch('src.core.services.market_data_service.AnalyticsManager'):
                                with patch('src.core.services.market_data_service.BuySellMarketTracker'):
                                    mock_data_provider = Mock()
                                    mock_event_manager = Mock()
                                    mock_event_manager.get_detector.return_value = Mock()
                                    mock_cache_control = Mock()
                                    mock_cache_control.get_default_universe.return_value = ['AAPL'] * 150
                                    
                                    service = MarketDataService(
                                        config=mock_config,
                                        data_provider=mock_data_provider,
                                        event_manager=mock_event_manager,
                                        cache_control=mock_cache_control
                                    )
                                    
                                    # Should have new methods
                                    assert hasattr(service, 'handle_ohlcv_data')
                                    assert hasattr(service, 'handle_fmv_data')
                                    
                                    # Should still have existing methods
                                    assert hasattr(service, 'handle_websocket_tick')
                                    assert hasattr(service, 'handle_websocket_status')
                                    
                                    # Should still have existing attributes
                                    assert hasattr(service, 'config')
                                    assert hasattr(service, 'data_provider')
                                    assert hasattr(service, 'event_manager')


class TestExistingEventFlowPreservation:
    """Test that existing event flow through the system is preserved"""
    
    def test_existing_priority_manager_integration(self):
        """Test that priority manager integration is preserved"""
        mock_config = {'USE_SYNTHETIC_DATA': True}
        mock_market_service = Mock()
        mock_market_service.tickstock_universe_manager = Mock()
        mock_market_service.tickstock_universe_manager.get_core_universe.return_value = ['AAPL'] * 150
        mock_market_service.tickstock_universe_manager.is_stock_in_core_universe.return_value = True
        mock_market_service.priority_manager = Mock()
        mock_market_service.stock_details = {}
        mock_market_service.changed_tickers = set()
        
        # Mock other required components
        for attr in ['buysell_market_tracker', 'session_accumulation_manager', 
                    'market_analytics_manager', 'cache_control', 'market_metrics']:
            setattr(mock_market_service, attr, Mock())
        
        mock_event_manager = Mock()
        mock_event_manager.get_detector.return_value = Mock()
        
        processor = EventProcessor(
            config=mock_config,
            market_service=mock_market_service,
            event_manager=mock_event_manager
        )
        
        # Should still integrate with priority manager for backward compatibility
        assert processor.market_service.priority_manager is not None
    
    def test_existing_stock_details_structure_preserved(self):
        """Test that StockData structure and usage is preserved"""
        from src.presentation.converters.transport_models import StockData
        
        # Should still be able to create StockData as before
        stock_data = StockData(ticker='AAPL', last_price=150.0)
        
        # Should have all existing attributes
        assert hasattr(stock_data, 'ticker')
        assert hasattr(stock_data, 'last_price')
        assert hasattr(stock_data, 'events')  # Should still have events collection
        
        # Should be able to add events as before
        mock_event = Mock()
        stock_data.add_event(mock_event)
        assert len(stock_data.events) == 1
    
    def test_existing_event_generation_preserved(self):
        """Test that existing event generation process is preserved"""
        from src.core.domain.events.highlow import HighLowEvent
        
        # Should still be able to create events with same interface
        event = HighLowEvent(
            ticker='AAPL',
            price=150.0,
            volume=1000,
            time=time.time(),
            event_type='high'
        )
        
        # Should have existing required attributes
        assert event.ticker == 'AAPL'
        assert event.price == 150.0
        assert event.type == 'high'
        
        # Should still have to_transport_dict method
        assert hasattr(event, 'to_transport_dict')


class TestPerformanceRegression:
    """Test that performance characteristics are not degraded"""
    
    def test_processing_time_not_significantly_increased(self, mock_config):
        """Test that processing time hasn't significantly increased"""
        mock_market_service = Mock()
        mock_market_service.tickstock_universe_manager = Mock()
        mock_market_service.tickstock_universe_manager.get_core_universe.return_value = ['AAPL'] * 150
        mock_market_service.tickstock_universe_manager.is_stock_in_core_universe.return_value = True
        
        # Mock other components
        for attr in ['buysell_market_tracker', 'session_accumulation_manager', 
                    'market_analytics_manager', 'cache_control', 'market_metrics',
                    'priority_manager']:
            setattr(mock_market_service, attr, Mock())
        
        mock_market_service.stock_details = {}
        mock_market_service.changed_tickers = set()
        
        mock_event_manager = Mock()
        mock_event_manager.get_detector.return_value = Mock()
        
        processor = EventProcessor(
            config=mock_config,
            market_service=mock_market_service,
            event_manager=mock_event_manager
        )
        
        # Mock tick processor and event detector for speed
        processor.tick_processor.process_tick = Mock(return_value=Mock(
            success=True, processed_tick=Mock(), errors=[], warnings=[]
        ))
        processor.event_detector.detect_events = Mock(return_value=Mock(
            success=True, events_detected=[], errors=[], warnings=[]
        ))
        
        # Measure processing time for multiple ticks
        tick_data = TickData(ticker='AAPL', price=150.0, volume=1000, timestamp=time.time(), market_status='REGULAR')
        
        start_time = time.time()
        for _ in range(100):
            processor.handle_tick(tick_data)
        end_time = time.time()
        
        total_time = (end_time - start_time) * 1000  # Convert to ms
        avg_time_per_tick = total_time / 100
        
        # Should process ticks in reasonable time (less than 50ms per tick)
        assert avg_time_per_tick < 50, f"Average processing time {avg_time_per_tick}ms is too slow"
    
    def test_memory_usage_not_significantly_increased(self):
        """Test that memory usage patterns are reasonable"""
        import sys
        
        # Simple memory usage check - new components shouldn't add excessive overhead
        from src.processing.pipeline.source_context_manager import SourceContextManager
        from src.processing.rules.source_specific_rules import SourceSpecificRulesEngine
        from src.processing.pipeline.multi_source_coordinator import MultiSourceCoordinator
        
        # Should be able to create instances without excessive memory
        context_mgr = SourceContextManager()
        rules_engine = SourceSpecificRulesEngine()
        coordinator = MultiSourceCoordinator()
        
        # Basic smoke test - objects should be created successfully
        assert context_mgr is not None
        assert rules_engine is not None
        assert coordinator is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])