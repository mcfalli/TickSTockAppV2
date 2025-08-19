"""
End-to-end integration tests for multi-frequency data flow - Sprint 101
Tests complete data pipeline from WebSocket to frontend emission.
"""

import pytest
import time
import json
import threading
from unittest.mock import Mock, MagicMock, patch, call
import asyncio
from concurrent.futures import ThreadPoolExecutor

from src.presentation.websocket.polygon_client import PolygonWebSocketClient
from src.processing.stream_manager import DataStreamManager
from src.presentation.websocket.data_publisher import DataPublisher
from src.presentation.websocket.publisher import WebSocketPublisher
from src.shared.types.frequency import FrequencyType


class TestEndToEndMultiFrequencyDataFlow:
    """End-to-end tests for multi-frequency data pipeline"""
    
    @pytest.fixture
    def complete_multifrequency_config(self):
        """Complete configuration for end-to-end testing"""
        return {
            # Polygon API configuration
            'polygon_api_key': 'test_standard_key',
            'polygon_business_api_key': 'test_business_key',
            
            # Multi-frequency enablement
            'enable_per_minute_events': True,
            'enable_fmv_events': True,
            
            # Pull Model configuration
            'COLLECTION_INTERVAL': 0.5,
            'EMISSION_INTERVAL': 1.0,
            'MAX_BUFFER_SIZE': 1000,
            
            # Performance settings
            'websocket_port': 5000,
            'max_connections': 100,
            'heartbeat_interval': 30,
            
            # Testing flags
            'use_simulated_data': True,
            'testing': True
        }
    
    @pytest.fixture
    def mock_websocket_manager(self):
        """Mock WebSocket manager for testing"""
        manager = Mock()
        manager.emit_to_user = Mock(return_value=True)
        manager.emit_to_all = Mock(return_value=True)
        manager.get_connected_users = Mock(return_value=['user1', 'user2', 'user3'])
        manager.is_user_connected = Mock(return_value=True)
        return manager
    
    @pytest.fixture
    def integrated_pipeline(self, complete_multifrequency_config, mock_websocket_manager):
        """Create complete integrated multi-frequency pipeline"""
        # Mock external dependencies
        with patch('src.presentation.websocket.polygon_client.websocket.WebSocketApp'), \
             patch('src.presentation.websocket.publisher.UserFiltersService'), \
             patch('src.presentation.websocket.publisher.UserSettingsService'), \
             patch('src.presentation.websocket.publisher.WebSocketFilterCache'), \
             patch('src.presentation.websocket.publisher.WebSocketDataFilter'), \
             patch('src.presentation.websocket.publisher.WebSocketAnalytics'), \
             patch('src.presentation.websocket.publisher.WebSocketDisplayConverter'), \
             patch('src.presentation.websocket.publisher.WebSocketUniverseCache'), \
             patch('src.presentation.websocket.publisher.WebSocketStatistics'), \
             patch('src.presentation.websocket.data_publisher.UserFiltersService'), \
             patch('src.presentation.websocket.data_publisher.UserSettingsService'):
            
            # Create pipeline components
            pipeline = {}
            
            # 1. PolygonWebSocketClient (multi-frequency)
            pipeline['polygon_client'] = PolygonWebSocketClient(
                config=complete_multifrequency_config,
                on_tick=Mock(),
                on_minute_bar=Mock(),
                on_fmv=Mock(),
                on_status=Mock()
            )
            
            # 2. DataStreamManager (frequency routing)
            pipeline['stream_manager'] = DataStreamManager(
                config=complete_multifrequency_config,
                per_second_processor=Mock(),
                per_minute_processor=Mock(),
                fmv_processor=Mock()
            )
            
            # 3. DataPublisher (Pull Model event collection)
            pipeline['data_publisher'] = DataPublisher(
                config=complete_multifrequency_config
            )
            
            # 4. WebSocketPublisher (Pull Model emission)
            pipeline['websocket_publisher'] = WebSocketPublisher(
                websocket_mgr=mock_websocket_manager,
                config=complete_multifrequency_config,
                cache_control=Mock()
            )
            
            # Connect data publisher to websocket publisher
            pipeline['websocket_publisher'].data_publisher = pipeline['data_publisher']
            
            return pipeline
    
    def test_complete_data_flow_per_second(self, integrated_pipeline, event_builder):
        """Test complete data flow for per-second events"""
        pipeline = integrated_pipeline
        
        # Simulate per-second tick from Polygon
        tick_data = {
            "ev": "A",  # Per-second aggregate
            "sym": "AAPL",
            "c": 150.25,
            "v": 1000,
            "t": int(time.time() * 1000)
        }
        
        # 1. Simulate WebSocket message reception
        message = json.dumps([tick_data])
        pipeline['polygon_client']._handle_message(FrequencyType.PER_SECOND, message)
        
        # 2. Route through stream manager
        routing_result = pipeline['stream_manager'].route_event(tick_data, FrequencyType.PER_SECOND)
        assert routing_result is True
        
        # 3. Create high/low event for testing
        high_event = event_builder.high_low_event(ticker="AAPL", price=150.25)
        
        # 4. Publish to DataPublisher
        pipeline['data_publisher'].publish_high_low_event(high_event)
        
        # 5. Collect data from DataPublisher
        collected_data = pipeline['data_publisher'].get_collected_data()
        
        # Verify data structure includes multi-frequency format
        assert 'frequencies' in collected_data
        per_second_data = collected_data['frequencies'].get(FrequencyType.PER_SECOND.value, {})
        assert len(per_second_data.get('highs', [])) > 0
        
        # 6. Process through WebSocketPublisher
        user_id = 123
        with patch.object(pipeline['websocket_publisher'], 'universe_cache') as mock_cache, \
             patch.object(pipeline['websocket_publisher'], '_resolve_user_universes_to_tickers') as mock_resolve, \
             patch.object(pipeline['websocket_publisher'], 'analytics') as mock_analytics:
            
            mock_cache.get_or_load_user_universes.return_value = ['universe1']
            mock_resolve.return_value = {'AAPL'}
            mock_analytics.prepare_enhanced_dual_universe_data.return_value = {'processed': True}
            
            user_prefs = {FrequencyType.PER_SECOND.value: True}
            result = pipeline['websocket_publisher']._process_user_data_multifrequency(
                user_id, collected_data, None, user_prefs
            )
            
            assert result is not None
    
    def test_complete_data_flow_per_minute(self, integrated_pipeline, event_builder, mock_polygon_am_data):
        """Test complete data flow for per-minute events"""
        pipeline = integrated_pipeline
        
        # 1. Simulate per-minute WebSocket message
        message = json.dumps([mock_polygon_am_data])
        pipeline['polygon_client']._handle_message(FrequencyType.PER_MINUTE, message)
        
        # 2. Route through stream manager
        routing_result = pipeline['stream_manager'].route_event(mock_polygon_am_data, FrequencyType.PER_MINUTE)
        assert routing_result is True
        
        # 3. Create per-minute aggregate event
        am_event = event_builder.per_minute_aggregate_event(
            ticker="AAPL",
            minute_close=150.25,
            minute_volume=50000
        )
        
        # 4. Publish to DataPublisher (simulate AM event processing)
        pipeline['data_publisher'].publish_per_minute_event(am_event)
        
        # 5. Collect data
        collected_data = pipeline['data_publisher'].get_collected_data()
        
        # Verify per-minute data is collected
        per_minute_data = collected_data['frequencies'].get(FrequencyType.PER_MINUTE.value, {})
        assert len(per_minute_data.get('aggregates', [])) > 0
        
        # 6. Process through WebSocketPublisher
        user_id = 123
        with patch.object(pipeline['websocket_publisher'], 'universe_cache') as mock_cache, \
             patch.object(pipeline['websocket_publisher'], '_resolve_user_universes_to_tickers') as mock_resolve, \
             patch.object(pipeline['websocket_publisher'], 'analytics') as mock_analytics:
            
            mock_cache.get_or_load_user_universes.return_value = ['universe1']
            mock_resolve.return_value = {'AAPL'}
            mock_analytics.prepare_enhanced_dual_universe_data.return_value = {'processed': True}
            
            user_prefs = {FrequencyType.PER_MINUTE.value: True}
            result = pipeline['websocket_publisher']._process_user_data_multifrequency(
                user_id, collected_data, None, user_prefs
            )
            
            assert result is not None
    
    def test_complete_data_flow_fmv(self, integrated_pipeline, event_builder, mock_polygon_fmv_data):
        """Test complete data flow for FMV events"""
        pipeline = integrated_pipeline
        
        # 1. Simulate FMV WebSocket message
        message = json.dumps([mock_polygon_fmv_data])
        pipeline['polygon_client']._handle_message(FrequencyType.FAIR_MARKET_VALUE, message)
        
        # 2. Route through stream manager
        routing_result = pipeline['stream_manager'].route_event(mock_polygon_fmv_data, FrequencyType.FAIR_MARKET_VALUE)
        assert routing_result is True
        
        # 3. Create FMV event
        fmv_event = event_builder.fair_market_value_event(
            ticker="AAPL",
            fmv_price=150.75,
            market_price=150.25
        )
        
        # 4. Publish to DataPublisher
        pipeline['data_publisher'].publish_fmv_event(fmv_event)
        
        # 5. Collect data
        collected_data = pipeline['data_publisher'].get_collected_data()
        
        # Verify FMV data is collected
        fmv_data = collected_data['frequencies'].get(FrequencyType.FAIR_MARKET_VALUE.value, {})
        assert len(fmv_data.get('fmv_events', [])) > 0
        
        # 6. Process through WebSocketPublisher
        user_id = 123
        with patch.object(pipeline['websocket_publisher'], 'universe_cache') as mock_cache, \
             patch.object(pipeline['websocket_publisher'], '_resolve_user_universes_to_tickers') as mock_resolve, \
             patch.object(pipeline['websocket_publisher'], 'analytics') as mock_analytics:
            
            mock_cache.get_or_load_user_universes.return_value = ['universe1']
            mock_resolve.return_value = {'AAPL'}
            mock_analytics.prepare_enhanced_dual_universe_data.return_value = {'processed': True}
            
            user_prefs = {FrequencyType.FAIR_MARKET_VALUE.value: True}
            result = pipeline['websocket_publisher']._process_user_data_multifrequency(
                user_id, collected_data, None, user_prefs
            )
            
            assert result is not None
    
    def test_concurrent_multi_frequency_processing(self, integrated_pipeline, event_builder, 
                                                 mock_polygon_am_data, mock_polygon_fmv_data):
        """Test concurrent processing of multiple frequency types"""
        pipeline = integrated_pipeline
        
        # Prepare events for all frequencies
        events_data = [
            (FrequencyType.PER_SECOND, {"ev": "A", "sym": "AAPL", "c": 150.0, "v": 1000}),
            (FrequencyType.PER_MINUTE, mock_polygon_am_data),
            (FrequencyType.FAIR_MARKET_VALUE, mock_polygon_fmv_data)
        ]
        
        results = []
        errors = []
        
        def process_frequency(freq_type, event_data):
            try:
                # Simulate WebSocket reception
                message = json.dumps([event_data])
                pipeline['polygon_client']._handle_message(freq_type, message)
                
                # Route through stream manager
                result = pipeline['stream_manager'].route_event(event_data, freq_type)
                results.append((freq_type, result))
                
                # Publish corresponding events
                if freq_type == FrequencyType.PER_SECOND:
                    event = event_builder.high_low_event(ticker="AAPL")
                    pipeline['data_publisher'].publish_high_low_event(event)
                elif freq_type == FrequencyType.PER_MINUTE:
                    event = event_builder.per_minute_aggregate_event(ticker="AAPL")
                    pipeline['data_publisher'].publish_per_minute_event(event)
                elif freq_type == FrequencyType.FAIR_MARKET_VALUE:
                    event = event_builder.fair_market_value_event(ticker="AAPL")
                    pipeline['data_publisher'].publish_fmv_event(event)
                
            except Exception as e:
                errors.append((freq_type, str(e)))
        
        # Process all frequencies concurrently
        threads = []
        for freq_type, event_data in events_data:
            thread = threading.Thread(target=process_frequency, args=(freq_type, event_data))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all processing succeeded
        assert len(errors) == 0, f"Concurrent processing errors: {errors}"
        assert len(results) == 3, f"Expected 3 results, got {len(results)}"
        assert all(result for freq_type, result in results), f"Some processing failed: {results}"
        
        # Verify data was collected for all frequencies
        collected_data = pipeline['data_publisher'].get_collected_data()
        frequencies_data = collected_data.get('frequencies', {})
        
        assert FrequencyType.PER_SECOND.value in frequencies_data
        assert FrequencyType.PER_MINUTE.value in frequencies_data
        assert FrequencyType.FAIR_MARKET_VALUE.value in frequencies_data
    
    def test_pull_model_emission_timing(self, integrated_pipeline, event_builder):
        """Test Pull Model emission timing with multi-frequency data"""
        pipeline = integrated_pipeline
        
        # Publish events to different frequency buffers
        events = [
            (event_builder.high_low_event(ticker="AAPL"), 'publish_high_low_event'),
            (event_builder.per_minute_aggregate_event(ticker="GOOGL"), 'publish_per_minute_event'),
            (event_builder.fair_market_value_event(ticker="MSFT"), 'publish_fmv_event')
        ]
        
        # Publish all events
        for event, method_name in events:
            method = getattr(pipeline['data_publisher'], method_name)
            method(event)
        
        # Simulate emission timing
        emission_start = time.time()
        
        # Get collected data (Pull Model - Publisher pulls when ready)
        collected_data = pipeline['data_publisher'].get_collected_data()
        
        emission_duration = time.time() - emission_start
        
        # Verify emission is fast (Pull Model should be sub-millisecond)
        assert emission_duration < 0.01, f"Pull Model emission took {emission_duration:.3f}s"
        
        # Verify all frequency data is available
        frequencies = collected_data.get('frequencies', {})
        assert len(frequencies) >= 3  # Should have all frequency types
        
        # Verify buffer structure maintained
        for freq_key, freq_data in frequencies.items():
            assert isinstance(freq_data, dict), f"Invalid frequency data structure for {freq_key}"
    
    def test_user_frequency_filtering_end_to_end(self, integrated_pipeline, event_builder):
        """Test end-to-end user frequency preference filtering"""
        pipeline = integrated_pipeline
        
        # Prepare multi-frequency data
        events = [
            event_builder.high_low_event(ticker="AAPL"),
            event_builder.per_minute_aggregate_event(ticker="AAPL"),
            event_builder.fair_market_value_event(ticker="AAPL")
        ]
        
        # Publish all events
        pipeline['data_publisher'].publish_high_low_event(events[0])
        pipeline['data_publisher'].publish_per_minute_event(events[1])
        pipeline['data_publisher'].publish_fmv_event(events[2])
        
        # Get collected data
        collected_data = pipeline['data_publisher'].get_collected_data()
        
        # Test different user preferences
        user_scenarios = [
            # User 1: Only per-second events
            (1, {FrequencyType.PER_SECOND.value: True, FrequencyType.PER_MINUTE.value: False, FrequencyType.FAIR_MARKET_VALUE.value: False}),
            # User 2: Per-second and per-minute
            (2, {FrequencyType.PER_SECOND.value: True, FrequencyType.PER_MINUTE.value: True, FrequencyType.FAIR_MARKET_VALUE.value: False}),
            # User 3: All frequencies
            (3, {FrequencyType.PER_SECOND.value: True, FrequencyType.PER_MINUTE.value: True, FrequencyType.FAIR_MARKET_VALUE.value: True})
        ]
        
        for user_id, user_prefs in user_scenarios:
            with patch.object(pipeline['websocket_publisher'], 'universe_cache') as mock_cache, \
                 patch.object(pipeline['websocket_publisher'], '_resolve_user_universes_to_tickers') as mock_resolve, \
                 patch.object(pipeline['websocket_publisher'], 'analytics') as mock_analytics:
                
                mock_cache.get_or_load_user_universes.return_value = ['universe1']
                mock_resolve.return_value = {'AAPL'}
                mock_analytics.prepare_enhanced_dual_universe_data.return_value = {'filtered_data': True}
                
                result = pipeline['websocket_publisher']._process_user_data_multifrequency(
                    user_id, collected_data, None, user_prefs
                )
                
                # Verify filtering worked
                assert result is not None
                
                # Verify analytics was called (indicating processing completed)
                mock_analytics.prepare_enhanced_dual_universe_data.assert_called()
    
    def test_stream_isolation_and_recovery(self, integrated_pipeline, event_builder):
        """Test stream isolation and error recovery"""
        pipeline = integrated_pipeline
        
        # Simulate error in per-minute processor
        pipeline['stream_manager'].per_minute_processor.side_effect = Exception("Per-minute processor error")
        
        # Process events for all frequencies
        per_second_data = {"ev": "A", "sym": "AAPL", "c": 150.0}
        per_minute_data = {"ev": "AM", "sym": "AAPL", "c": 150.0}
        fmv_data = {"ev": "FMV", "sym": "AAPL", "fmv": 150.75}
        
        # Per-second should work
        result1 = pipeline['stream_manager'].route_event(per_second_data, FrequencyType.PER_SECOND)
        assert result1 is True
        
        # Per-minute should fail (processor error)
        result2 = pipeline['stream_manager'].route_event(per_minute_data, FrequencyType.PER_MINUTE)
        assert result2 is False
        
        # FMV should still work (isolation)
        result3 = pipeline['stream_manager'].route_event(fmv_data, FrequencyType.FAIR_MARKET_VALUE)
        assert result3 is True
        
        # Verify stream health shows the error
        health = pipeline['stream_manager'].get_stream_health()
        assert health['per_minute']['error_count'] > 0
        assert health['per_second']['error_count'] == 0
        assert health['fmv']['error_count'] == 0
        
        # Test recovery - fix the processor
        pipeline['stream_manager'].per_minute_processor.side_effect = None
        pipeline['stream_manager'].per_minute_processor.return_value = True
        
        # Per-minute should work again
        result4 = pipeline['stream_manager'].route_event(per_minute_data, FrequencyType.PER_MINUTE)
        assert result4 is True
    
    @pytest.mark.performance
    def test_end_to_end_performance_multifrequency(self, integrated_pipeline, event_builder, performance_timer):
        """Test end-to-end performance with multi-frequency processing"""
        pipeline = integrated_pipeline
        
        # Prepare large dataset
        events_per_frequency = 100
        
        performance_timer.start()
        
        # Process events for all frequencies
        for i in range(events_per_frequency):
            # Per-second events
            per_second_event = event_builder.high_low_event(ticker=f"TICK{i % 10}")
            pipeline['data_publisher'].publish_high_low_event(per_second_event)
            
            # Per-minute events (less frequent)
            if i % 5 == 0:
                per_minute_event = event_builder.per_minute_aggregate_event(ticker=f"TICK{i % 10}")
                pipeline['data_publisher'].publish_per_minute_event(per_minute_event)
            
            # FMV events (even less frequent)
            if i % 10 == 0:
                fmv_event = event_builder.fair_market_value_event(ticker=f"TICK{i % 10}")
                pipeline['data_publisher'].publish_fmv_event(fmv_event)
        
        # Collect all data (Pull Model operation)
        collected_data = pipeline['data_publisher'].get_collected_data()
        
        # Process for multiple users
        user_prefs = {
            FrequencyType.PER_SECOND.value: True,
            FrequencyType.PER_MINUTE.value: True,
            FrequencyType.FAIR_MARKET_VALUE.value: True
        }
        
        with patch.object(pipeline['websocket_publisher'], 'universe_cache') as mock_cache, \
             patch.object(pipeline['websocket_publisher'], '_resolve_user_universes_to_tickers') as mock_resolve, \
             patch.object(pipeline['websocket_publisher'], 'analytics') as mock_analytics:
            
            mock_cache.get_or_load_user_universes.return_value = ['universe1']
            mock_resolve.return_value = {f"TICK{i}" for i in range(10)}
            mock_analytics.prepare_enhanced_dual_universe_data.return_value = {'processed': True}
            
            # Process for 10 users
            for user_id in range(10):
                result = pipeline['websocket_publisher']._process_user_data_multifrequency(
                    user_id, collected_data, None, user_prefs
                )
                assert result is not None
        
        performance_timer.stop()
        
        # Should complete end-to-end processing in under 100ms
        assert performance_timer.elapsed < 0.1, f"End-to-end processing took {performance_timer.elapsed:.3f}s"
        
        # Verify data integrity
        frequencies = collected_data.get('frequencies', {})
        assert len(frequencies) == 3  # All frequencies processed
        
        per_second_events = frequencies.get(FrequencyType.PER_SECOND.value, {}).get('highs', [])
        assert len(per_second_events) == events_per_frequency
        
        per_minute_events = frequencies.get(FrequencyType.PER_MINUTE.value, {}).get('aggregates', [])
        assert len(per_minute_events) == events_per_frequency // 5
        
        fmv_events = frequencies.get(FrequencyType.FAIR_MARKET_VALUE.value, {}).get('fmv_events', [])
        assert len(fmv_events) == events_per_frequency // 10
    
    def test_backward_compatibility_with_legacy_structure(self, integrated_pipeline, event_builder):
        """Test backward compatibility with existing per-second structure"""
        pipeline = integrated_pipeline
        
        # Publish traditional per-second events
        high_event = event_builder.high_low_event(ticker="AAPL", event_type="high")
        low_event = event_builder.high_low_event(ticker="GOOGL", event_type="low")
        trend_event = event_builder.trend_event(ticker="MSFT", direction="up")
        surge_event = event_builder.surge_event(ticker="TSLA")
        
        pipeline['data_publisher'].publish_high_low_event(high_event)
        pipeline['data_publisher'].publish_high_low_event(low_event)
        pipeline['data_publisher'].publish_trend_event(trend_event)
        pipeline['data_publisher'].publish_surge_event(surge_event)
        
        # Get collected data
        collected_data = pipeline['data_publisher'].get_collected_data()
        
        # Verify legacy structure is maintained
        assert 'highs' in collected_data
        assert 'lows' in collected_data
        assert 'trending' in collected_data
        assert 'surging' in collected_data
        
        # Verify new multi-frequency structure is also available
        assert 'frequencies' in collected_data
        per_second_data = collected_data['frequencies'].get(FrequencyType.PER_SECOND.value, {})
        assert 'highs' in per_second_data
        assert 'lows' in per_second_data
        assert 'trending' in per_second_data
        assert 'surging' in per_second_data
        
        # Verify data consistency between legacy and new structure
        assert len(collected_data['highs']) == len(per_second_data['highs'])
        assert len(collected_data['lows']) == len(per_second_data['lows'])
    
    def test_configuration_driven_frequency_enablement(self, complete_multifrequency_config, mock_websocket_manager):
        """Test that frequency enablement is driven by configuration"""
        # Test with only per-second enabled
        config_per_second_only = complete_multifrequency_config.copy()
        config_per_second_only.update({
            'enable_per_minute_events': False,
            'enable_fmv_events': False
        })
        
        with patch('src.presentation.websocket.polygon_client.websocket.WebSocketApp'), \
             patch('src.presentation.websocket.publisher.UserFiltersService'), \
             patch('src.presentation.websocket.publisher.UserSettingsService'), \
             patch('src.presentation.websocket.publisher.WebSocketFilterCache'), \
             patch('src.presentation.websocket.publisher.WebSocketDataFilter'), \
             patch('src.presentation.websocket.publisher.WebSocketAnalytics'), \
             patch('src.presentation.websocket.publisher.WebSocketDisplayConverter'), \
             patch('src.presentation.websocket.publisher.WebSocketUniverseCache'), \
             patch('src.presentation.websocket.publisher.WebSocketStatistics'):
            
            # Create components with limited config
            polygon_client = PolygonWebSocketClient(
                config=config_per_second_only,
                on_tick=Mock(), on_minute_bar=Mock(), on_fmv=Mock(), on_status=Mock()
            )
            
            stream_manager = DataStreamManager(
                config=config_per_second_only,
                per_second_processor=Mock()
            )
            
            websocket_publisher = WebSocketPublisher(
                websocket_mgr=mock_websocket_manager,
                config=config_per_second_only,
                cache_control=Mock()
            )
            
            # Verify only per-second is enabled
            assert FrequencyType.PER_SECOND in polygon_client.enabled_frequencies
            assert FrequencyType.PER_MINUTE not in polygon_client.enabled_frequencies
            assert FrequencyType.FAIR_MARKET_VALUE not in polygon_client.enabled_frequencies
            
            assert stream_manager.is_frequency_enabled(FrequencyType.PER_SECOND) is True
            assert stream_manager.is_frequency_enabled(FrequencyType.PER_MINUTE) is False
            assert stream_manager.is_frequency_enabled(FrequencyType.FAIR_MARKET_VALUE) is False
            
            assert websocket_publisher.is_frequency_enabled(FrequencyType.PER_SECOND) is True
            assert websocket_publisher.is_frequency_enabled(FrequencyType.PER_MINUTE) is False
            assert websocket_publisher.is_frequency_enabled(FrequencyType.FAIR_MARKET_VALUE) is False


class TestMultiFrequencyPullModelIntegration:
    """Integration tests specifically for Pull Model architecture with multi-frequency"""
    
    @pytest.fixture
    def pull_model_setup(self, complete_multifrequency_config, mock_websocket_manager):
        """Set up Pull Model components with multi-frequency support"""
        with patch('src.presentation.websocket.data_publisher.UserFiltersService'), \
             patch('src.presentation.websocket.data_publisher.UserSettingsService'), \
             patch('src.presentation.websocket.publisher.UserFiltersService'), \
             patch('src.presentation.websocket.publisher.UserSettingsService'), \
             patch('src.presentation.websocket.publisher.WebSocketFilterCache'), \
             patch('src.presentation.websocket.publisher.WebSocketDataFilter'), \
             patch('src.presentation.websocket.publisher.WebSocketAnalytics'), \
             patch('src.presentation.websocket.publisher.WebSocketDisplayConverter'), \
             patch('src.presentation.websocket.publisher.WebSocketUniverseCache'), \
             patch('src.presentation.websocket.publisher.WebSocketStatistics'):
            
            data_publisher = DataPublisher(config=complete_multifrequency_config)
            websocket_publisher = WebSocketPublisher(
                websocket_mgr=mock_websocket_manager,
                config=complete_multifrequency_config,
                cache_control=Mock()
            )
            
            # Connect components
            websocket_publisher.data_publisher = data_publisher
            
            return {
                'data_publisher': data_publisher,
                'websocket_publisher': websocket_publisher,
                'config': complete_multifrequency_config
            }
    
    def test_pull_model_buffer_limits_per_frequency(self, pull_model_setup, event_builder):
        """Test Pull Model buffer limits are maintained per frequency"""
        setup = pull_model_setup
        data_publisher = setup['data_publisher']
        
        # Test buffer limits for each frequency
        max_buffer_size = setup['config'].get('MAX_BUFFER_SIZE', 1000)
        
        # Fill per-second buffer beyond limit
        for i in range(max_buffer_size + 100):
            event = event_builder.high_low_event(ticker=f"TICK{i}")
            data_publisher.publish_high_low_event(event)
        
        # Fill per-minute buffer beyond limit  
        for i in range(max_buffer_size + 50):
            event = event_builder.per_minute_aggregate_event(ticker=f"TICK{i}")
            data_publisher.publish_per_minute_event(event)
        
        # Get collected data
        collected_data = data_publisher.get_collected_data()
        frequencies = collected_data.get('frequencies', {})
        
        # Verify buffer limits are respected per frequency
        per_second_data = frequencies.get(FrequencyType.PER_SECOND.value, {})
        per_minute_data = frequencies.get(FrequencyType.PER_MINUTE.value, {})
        
        per_second_total = len(per_second_data.get('highs', [])) + len(per_second_data.get('lows', []))
        per_minute_total = len(per_minute_data.get('aggregates', []))
        
        # Should not exceed buffer limits
        assert per_second_total <= max_buffer_size
        assert per_minute_total <= max_buffer_size
    
    def test_pull_model_zero_event_loss_multifrequency(self, pull_model_setup, event_builder):
        """Test Pull Model maintains zero event loss across frequencies"""
        setup = pull_model_setup
        data_publisher = setup['data_publisher']
        
        # Publish events rapidly to simulate high throughput
        event_counts = {
            'per_second': 500,
            'per_minute': 100, 
            'fmv': 50
        }
        
        published_events = {}
        
        # Publish per-second events
        published_events['per_second'] = []
        for i in range(event_counts['per_second']):
            event = event_builder.high_low_event(ticker=f"TICK{i % 10}")
            published_events['per_second'].append(event.event_id)
            data_publisher.publish_high_low_event(event)
        
        # Publish per-minute events
        published_events['per_minute'] = []
        for i in range(event_counts['per_minute']):
            event = event_builder.per_minute_aggregate_event(ticker=f"TICK{i % 10}")
            published_events['per_minute'].append(event.event_id)
            data_publisher.publish_per_minute_event(event)
        
        # Publish FMV events
        published_events['fmv'] = []
        for i in range(event_counts['fmv']):
            event = event_builder.fair_market_value_event(ticker=f"TICK{i % 10}")
            published_events['fmv'].append(event.event_id)
            data_publisher.publish_fmv_event(event)
        
        # Pull data (simulating WebSocketPublisher pull)
        collected_data = data_publisher.get_collected_data()
        frequencies = collected_data.get('frequencies', {})
        
        # Verify all events are present (zero event loss)
        per_second_data = frequencies.get(FrequencyType.PER_SECOND.value, {})
        per_minute_data = frequencies.get(FrequencyType.PER_MINUTE.value, {})
        fmv_data = frequencies.get(FrequencyType.FAIR_MARKET_VALUE.value, {})
        
        # Count collected events
        collected_per_second = len(per_second_data.get('highs', [])) + len(per_second_data.get('lows', []))
        collected_per_minute = len(per_minute_data.get('aggregates', []))
        collected_fmv = len(fmv_data.get('fmv_events', []))
        
        # Verify counts match (within buffer limits)
        max_buffer = setup['config'].get('MAX_BUFFER_SIZE', 1000)
        assert collected_per_second == min(event_counts['per_second'], max_buffer)
        assert collected_per_minute == min(event_counts['per_minute'], max_buffer)
        assert collected_fmv == min(event_counts['fmv'], max_buffer)
    
    def test_pull_model_emission_control_multifrequency(self, pull_model_setup, event_builder):
        """Test Pull Model emission control with multi-frequency data"""
        setup = pull_model_setup
        websocket_publisher = setup['websocket_publisher']
        data_publisher = setup['data_publisher']
        
        # Publish events to all frequencies
        events = [
            event_builder.high_low_event(ticker="AAPL"),
            event_builder.per_minute_aggregate_event(ticker="GOOGL"),
            event_builder.fair_market_value_event(ticker="MSFT")
        ]
        
        data_publisher.publish_high_low_event(events[0])
        data_publisher.publish_per_minute_event(events[1])
        data_publisher.publish_fmv_event(events[2])
        
        # Test emission control - WebSocketPublisher pulls when ready
        collected_data = data_publisher.get_collected_data()
        
        # Verify Publisher controls timing (Pull Model)
        assert hasattr(websocket_publisher, 'emission_interval')
        assert hasattr(websocket_publisher, 'emission_lock')
        assert hasattr(websocket_publisher, 'last_emission_time')
        
        # Verify data is available for pulling
        frequencies = collected_data.get('frequencies', {})
        assert len(frequencies) >= 3
        
        # Simulate emission control
        emission_start = time.time()
        
        user_prefs = {freq.value: True for freq in FrequencyType}
        
        with patch.object(websocket_publisher, 'universe_cache') as mock_cache, \
             patch.object(websocket_publisher, '_resolve_user_universes_to_tickers') as mock_resolve, \
             patch.object(websocket_publisher, 'analytics') as mock_analytics:
            
            mock_cache.get_or_load_user_universes.return_value = ['universe1']
            mock_resolve.return_value = {'AAPL', 'GOOGL', 'MSFT'}
            mock_analytics.prepare_enhanced_dual_universe_data.return_value = {'controlled_emission': True}
            
            result = websocket_publisher._process_user_data_multifrequency(
                123, collected_data, None, user_prefs
            )
            
            assert result is not None
        
        emission_duration = time.time() - emission_start
        
        # Pull Model should enable fast emission
        assert emission_duration < 0.01, f"Emission control took {emission_duration:.3f}s"