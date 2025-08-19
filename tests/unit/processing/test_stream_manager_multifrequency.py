"""
Unit tests for DataStreamManager multi-frequency functionality - Sprint 101
Tests DataStreamManager for frequency-based data routing.
"""

import pytest
import time
from unittest.mock import Mock, MagicMock, patch
from src.processing.stream_manager import DataStreamManager
from src.shared.types.frequency import FrequencyType


class TestDataStreamManager:
    """Test DataStreamManager multi-frequency routing"""
    
    @pytest.fixture
    def config(self):
        """Stream manager configuration"""
        return {
            'enable_per_minute_events': True,
            'enable_fmv_events': True,
            'routing_enabled': True
        }
    
    @pytest.fixture
    def mock_callbacks(self):
        """Mock processor callbacks"""
        return {
            'per_second_processor': Mock(),
            'per_minute_processor': Mock(),
            'fmv_processor': Mock()
        }
    
    @pytest.fixture
    def stream_manager(self, config, mock_callbacks):
        """Create DataStreamManager instance"""
        return DataStreamManager(
            config=config,
            per_second_processor=mock_callbacks['per_second_processor'],
            per_minute_processor=mock_callbacks['per_minute_processor'],
            fmv_processor=mock_callbacks['fmv_processor']
        )
    
    def test_stream_manager_initialization(self, stream_manager, config):
        """Test stream manager initialization"""
        assert stream_manager.config == config
        assert hasattr(stream_manager, 'per_second_processor')
        assert hasattr(stream_manager, 'per_minute_processor')
        assert hasattr(stream_manager, 'fmv_processor')
        
        # Check enabled frequencies
        assert FrequencyType.PER_SECOND in stream_manager.enabled_frequencies
        if config.get('enable_per_minute_events'):
            assert FrequencyType.PER_MINUTE in stream_manager.enabled_frequencies
        if config.get('enable_fmv_events'):
            assert FrequencyType.FAIR_MARKET_VALUE in stream_manager.enabled_frequencies
    
    def test_route_per_second_event(self, stream_manager, mock_callbacks, event_builder):
        """Test routing per-second tick data"""
        tick_data = {
            'ticker': 'AAPL',
            'price': 150.25,
            'volume': 1000,
            'timestamp': time.time()
        }
        
        # Route per-second event
        result = stream_manager.route_event(tick_data, FrequencyType.PER_SECOND)
        
        # Should call per-second processor
        mock_callbacks['per_second_processor'].assert_called_once_with(tick_data)
        
        # Should not call other processors
        mock_callbacks['per_minute_processor'].assert_not_called()
        mock_callbacks['fmv_processor'].assert_not_called()
        
        assert result is True
    
    def test_route_per_minute_event(self, stream_manager, mock_callbacks, mock_polygon_am_data):
        """Test routing per-minute aggregate data"""
        # Route per-minute event
        result = stream_manager.route_event(mock_polygon_am_data, FrequencyType.PER_MINUTE)
        
        # Should call per-minute processor
        mock_callbacks['per_minute_processor'].assert_called_once_with(mock_polygon_am_data)
        
        # Should not call other processors
        mock_callbacks['per_second_processor'].assert_not_called()
        mock_callbacks['fmv_processor'].assert_not_called()
        
        assert result is True
    
    def test_route_fmv_event(self, stream_manager, mock_callbacks, mock_polygon_fmv_data):
        """Test routing FMV data"""
        # Route FMV event
        result = stream_manager.route_event(mock_polygon_fmv_data, FrequencyType.FAIR_MARKET_VALUE)
        
        # Should call FMV processor
        mock_callbacks['fmv_processor'].assert_called_once_with(mock_polygon_fmv_data)
        
        # Should not call other processors
        mock_callbacks['per_second_processor'].assert_not_called()
        mock_callbacks['per_minute_processor'].assert_not_called()
        
        assert result is True
    
    def test_route_unknown_frequency(self, stream_manager, mock_callbacks):
        """Test routing with unknown frequency type"""
        tick_data = {'ticker': 'AAPL', 'price': 150.0}
        
        # Route with invalid frequency (should handle gracefully)
        result = stream_manager.route_event(tick_data, "invalid_frequency")
        
        # Should not call any processors
        mock_callbacks['per_second_processor'].assert_not_called()
        mock_callbacks['per_minute_processor'].assert_not_called()
        mock_callbacks['fmv_processor'].assert_not_called()
        
        assert result is False
    
    def test_processor_error_handling(self, stream_manager, mock_callbacks):
        """Test error handling when processor fails"""
        tick_data = {'ticker': 'AAPL', 'price': 150.0}
        
        # Make processor raise exception
        mock_callbacks['per_second_processor'].side_effect = Exception("Processor error")
        
        # Should handle error gracefully
        result = stream_manager.route_event(tick_data, FrequencyType.PER_SECOND)
        
        # Should return False on error but not crash
        assert result is False
    
    def test_stream_isolation(self, stream_manager, mock_callbacks):
        """Test that stream processing is isolated"""
        tick_data = {'ticker': 'AAPL', 'price': 150.0}
        am_data = {'sym': 'AAPL', 'c': 150.0}
        fmv_data = {'sym': 'AAPL', 'fmv': 150.75}
        
        # Make per-second processor fail
        mock_callbacks['per_second_processor'].side_effect = Exception("Per-second error")
        
        # Per-second should fail
        result1 = stream_manager.route_event(tick_data, FrequencyType.PER_SECOND)
        assert result1 is False
        
        # But other frequencies should still work
        result2 = stream_manager.route_event(am_data, FrequencyType.PER_MINUTE)
        assert result2 is True
        
        result3 = stream_manager.route_event(fmv_data, FrequencyType.FAIR_MARKET_VALUE)
        assert result3 is True
    
    def test_get_routing_statistics(self, stream_manager, mock_callbacks):
        """Test routing statistics collection"""
        tick_data = {'ticker': 'AAPL', 'price': 150.0}
        am_data = {'sym': 'AAPL', 'c': 150.0}
        
        # Route some events
        stream_manager.route_event(tick_data, FrequencyType.PER_SECOND)
        stream_manager.route_event(am_data, FrequencyType.PER_MINUTE)
        stream_manager.route_event(tick_data, FrequencyType.PER_SECOND)  # Second per-second
        
        # Get statistics
        stats = stream_manager.get_routing_statistics()
        
        # Should track routing counts
        assert stats[FrequencyType.PER_SECOND.value]['routed_count'] == 2
        assert stats[FrequencyType.PER_MINUTE.value]['routed_count'] == 1
        assert stats[FrequencyType.FAIR_MARKET_VALUE.value]['routed_count'] == 0
    
    def test_is_frequency_enabled(self, stream_manager):
        """Test frequency enablement checking"""
        # PER_SECOND should always be enabled
        assert stream_manager.is_frequency_enabled(FrequencyType.PER_SECOND) is True
        
        # Others depend on config
        per_minute_enabled = stream_manager.config.get('enable_per_minute_events', False)
        fmv_enabled = stream_manager.config.get('enable_fmv_events', False)
        
        assert stream_manager.is_frequency_enabled(FrequencyType.PER_MINUTE) is per_minute_enabled
        assert stream_manager.is_frequency_enabled(FrequencyType.FAIR_MARKET_VALUE) is fmv_enabled
    
    def test_enable_disable_frequency_runtime(self, stream_manager):
        """Test enabling/disabling frequencies at runtime"""
        # Initially disable per-minute
        stream_manager.disable_frequency(FrequencyType.PER_MINUTE)
        assert stream_manager.is_frequency_enabled(FrequencyType.PER_MINUTE) is False
        
        # Enable at runtime
        stream_manager.enable_frequency(FrequencyType.PER_MINUTE)
        assert stream_manager.is_frequency_enabled(FrequencyType.PER_MINUTE) is True
        
        # Should be able to route events now
        am_data = {'sym': 'AAPL', 'c': 150.0}
        result = stream_manager.route_event(am_data, FrequencyType.PER_MINUTE)
        assert result is True
    
    def test_health_monitoring(self, stream_manager, mock_callbacks):
        """Test stream health monitoring"""
        # Route some successful events
        stream_manager.route_event({'ticker': 'AAPL'}, FrequencyType.PER_SECOND)
        stream_manager.route_event({'sym': 'AAPL', 'c': 150}, FrequencyType.PER_MINUTE)
        
        # Cause an error
        mock_callbacks['per_second_processor'].side_effect = Exception("Error")
        stream_manager.route_event({'ticker': 'GOOGL'}, FrequencyType.PER_SECOND)
        
        # Get health status
        health = stream_manager.get_stream_health()
        
        # Should report health metrics
        assert 'per_second' in health
        assert 'per_minute' in health
        
        per_second_health = health['per_second']
        assert per_second_health['success_count'] >= 1
        assert per_second_health['error_count'] >= 1
        
        per_minute_health = health['per_minute']
        assert per_minute_health['success_count'] >= 1
        assert per_minute_health['error_count'] == 0
    
    @pytest.mark.performance
    def test_routing_performance(self, stream_manager, mock_callbacks, performance_timer):
        """Test routing performance for high throughput"""
        tick_data = {'ticker': 'AAPL', 'price': 150.0}
        
        performance_timer.start()
        
        # Route many events rapidly
        for _ in range(1000):
            stream_manager.route_event(tick_data, FrequencyType.PER_SECOND)
        
        performance_timer.stop()
        
        # Should route events quickly (< 50ms for 1000 events)
        assert performance_timer.elapsed < 0.05, f"Routing took {performance_timer.elapsed:.3f}s"
        
        # All events should have been processed
        assert mock_callbacks['per_second_processor'].call_count == 1000
    
    def test_concurrent_stream_routing(self, stream_manager, mock_callbacks):
        """Test concurrent routing across different frequencies"""
        import threading
        import time
        
        results = []
        errors = []
        
        def route_events(frequency_type, event_data, count):
            try:
                for _ in range(count):
                    result = stream_manager.route_event(event_data, frequency_type)
                    results.append(result)
                    time.sleep(0.001)  # Small delay
            except Exception as e:
                errors.append(e)
        
        # Start concurrent routing threads
        threads = [
            threading.Thread(target=route_events, args=(FrequencyType.PER_SECOND, {'ticker': 'AAPL'}, 50)),
            threading.Thread(target=route_events, args=(FrequencyType.PER_MINUTE, {'sym': 'AAPL', 'c': 150}, 50)),
            threading.Thread(target=route_events, args=(FrequencyType.FAIR_MARKET_VALUE, {'sym': 'AAPL', 'fmv': 150.75}, 50))
        ]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Should complete without errors
        assert len(errors) == 0, f"Concurrent routing errors: {errors}"
        
        # All routing should succeed
        assert all(results), f"Some routing failed: {results.count(False)} out of {len(results)}"
        
        # All processors should have been called
        assert mock_callbacks['per_second_processor'].call_count == 50
        assert mock_callbacks['per_minute_processor'].call_count == 50
        assert mock_callbacks['fmv_processor'].call_count == 50


class TestDataStreamManagerConfiguration:
    """Test DataStreamManager configuration scenarios"""
    
    def test_minimal_configuration(self):
        """Test with minimal configuration (only per-second)"""
        config = {
            'enable_per_minute_events': False,
            'enable_fmv_events': False
        }
        
        per_second_processor = Mock()
        
        manager = DataStreamManager(
            config=config,
            per_second_processor=per_second_processor
        )
        
        # Only per-second should be enabled
        assert manager.is_frequency_enabled(FrequencyType.PER_SECOND) is True
        assert manager.is_frequency_enabled(FrequencyType.PER_MINUTE) is False
        assert manager.is_frequency_enabled(FrequencyType.FAIR_MARKET_VALUE) is False
    
    def test_full_configuration(self):
        """Test with all frequencies enabled"""
        config = {
            'enable_per_minute_events': True,
            'enable_fmv_events': True
        }
        
        processors = {
            'per_second_processor': Mock(),
            'per_minute_processor': Mock(),
            'fmv_processor': Mock()
        }
        
        manager = DataStreamManager(
            config=config,
            **processors
        )
        
        # All frequencies should be enabled
        assert manager.is_frequency_enabled(FrequencyType.PER_SECOND) is True
        assert manager.is_frequency_enabled(FrequencyType.PER_MINUTE) is True
        assert manager.is_frequency_enabled(FrequencyType.FAIR_MARKET_VALUE) is True
    
    def test_missing_processor_handling(self):
        """Test handling of missing processors"""
        config = {
            'enable_per_minute_events': True,
            'enable_fmv_events': False
        }
        
        # Only provide per-second processor
        manager = DataStreamManager(
            config=config,
            per_second_processor=Mock()
        )
        
        # Should handle missing processors gracefully
        tick_data = {'ticker': 'AAPL'}
        am_data = {'sym': 'AAPL', 'c': 150}
        
        # Per-second should work
        assert manager.route_event(tick_data, FrequencyType.PER_SECOND) is True
        
        # Per-minute should fail gracefully (no processor)
        assert manager.route_event(am_data, FrequencyType.PER_MINUTE) is False