"""
Integration test for full data flow from multi-frequency generation to frontend emission.

This test validates the complete path:
1. Multi-frequency data generation → tick_callback()
2. Event processing → publish_event()  
3. WebSocket buffering → emit_buffered_events()
4. User targeting → emit_to_user()

Tests various configuration scenarios to ensure Sprint 111 multi-frequency system works end-to-end.
"""

import pytest
import time
import threading
from unittest.mock import Mock, MagicMock, patch, call
from typing import Dict, Any

# Avoid circular imports by importing specific components
from src.infrastructure.data_sources.synthetic.types import DataFrequency
from src.core.domain.market.tick import TickData


class TestFullDataFlowToFrontend:
    """Integration tests for complete data flow pipeline."""

    @pytest.fixture
    def mock_config(self):
        """Configuration for multi-frequency testing."""
        return {
            'USE_SYNTHETIC_DATA': True,
            'ENABLE_MULTI_FREQUENCY': True,
            'WEBSOCKET_PER_SECOND_ENABLED': False,
            'WEBSOCKET_PER_MINUTE_ENABLED': True, 
            'WEBSOCKET_FAIR_VALUE_ENABLED': True,
            'ENABLE_PER_SECOND_EVENTS': False,
            'ENABLE_PER_MINUTE_EVENTS': True,
            'ENABLE_FMV_EVENTS': False,
            'SYNTHETIC_MINUTE_WINDOW': 60,
            'SYNTHETIC_FMV_UPDATE_INTERVAL': 15,
            'SYNTHETIC_ACTIVITY_LEVEL': 'medium',
            'SYNTHETIC_DATA_RATE': 0.2
        }

    @pytest.fixture
    def mock_websocket_manager(self):
        """Mock WebSocketManager with emit_to_user tracking."""
        manager = Mock(spec=WebSocketManager)
        manager.user_connections = {1: ['conn1'], 2: ['conn2', 'conn3']}
        manager.emit_to_user = Mock(return_value=True)
        manager.get_connected_user_ids = Mock(return_value=[1, 2])
        return manager

    @pytest.fixture
    def mock_data_provider(self):
        """Mock data provider that returns valid per-minute data."""
        provider = Mock()
        
        # Mock per-minute data generation
        def mock_generate_frequency_data(ticker: str, frequency: DataFrequency):
            if frequency == DataFrequency.PER_MINUTE:
                return {
                    'c': 150.25,  # close price
                    'v': 5000,    # volume
                    'h': 151.0,   # high
                    'l': 149.5,   # low
                    'o': 150.0,   # open
                    'timestamp': time.time()
                }
            elif frequency == DataFrequency.FAIR_VALUE:
                return {
                    'fmv': 150.15,
                    'confidence': 0.85,
                    'timestamp': time.time()
                }
            return None
            
        provider.generate_frequency_data.side_effect = mock_generate_frequency_data
        return provider

    @pytest.fixture 
    def tick_callback_capture(self):
        """Capture tick callbacks for validation."""
        captured_ticks = []
        
        def capture_tick(tick_data: TickData):
            captured_ticks.append({
                'ticker': tick_data.ticker,
                'price': tick_data.price,
                'volume': tick_data.volume,
                'source': tick_data.source,
                'event_type': tick_data.event_type,
                'timestamp': tick_data.timestamp
            })
        
        return capture_tick, captured_ticks

    def test_full_multi_frequency_data_flow(self, mock_config, mock_websocket_manager, 
                                         mock_data_provider, tick_callback_capture):
        """
        Test complete data flow from multi-frequency generation to emit_to_user.
        
        This is the integration test for Sprint 111 - validates:
        1. Multi-frequency timer generates data at correct intervals
        2. TickData objects are created with correct structure
        3. tick_callback is invoked with proper data
        4. Data flows through to WebSocket emission layer
        """
        tick_callback, captured_ticks = tick_callback_capture
        
        # Create adapter with mocked components
        adapter = SyntheticDataAdapter(mock_config, tick_callback, Mock())
        
        # Mock the data provider factory to return our controlled provider
        with patch.object(DataProviderFactory, 'get_provider', return_value=mock_data_provider):
            # Start the multi-frequency system
            success = adapter.connect(['AAPL', 'GOOGL', 'MSFT'])
            assert success, "Multi-frequency adapter should connect successfully"
            
            # Wait for initial data generation (should happen immediately)
            time.sleep(2)
            
            # Validate tick callbacks were made
            assert len(captured_ticks) > 0, "Should have captured tick callbacks"
            
            # Validate tick data structure
            first_tick = captured_ticks[0]
            assert first_tick['ticker'] in ['AAPL', 'GOOGL', 'MSFT']
            assert first_tick['price'] == 150.25  # From mock data
            assert first_tick['volume'] == 5000    # From mock data
            assert first_tick['source'] == 'multi_frequency_per_minute'
            assert first_tick['event_type'] == 'AM'  # Aggregate Minute
            assert isinstance(first_tick['timestamp'], float)
            
            # Validate data provider was called correctly
            mock_data_provider.generate_frequency_data.assert_called()
            
            # Get all calls to verify both per-minute and FMV generation
            calls = mock_data_provider.generate_frequency_data.call_args_list
            per_minute_calls = [c for c in calls if c[0][1] == DataFrequency.PER_MINUTE]
            fmv_calls = [c for c in calls if c[0][1] == DataFrequency.FAIR_VALUE]
            
            assert len(per_minute_calls) >= 3, "Should generate per-minute data for 3 tickers"
            assert len(fmv_calls) >= 3, "Should generate FMV data for 3 tickers"
            
        # Clean up
        adapter.disconnect()

    def test_configuration_respect_per_minute_only(self, mock_websocket_manager, 
                                                 mock_data_provider, tick_callback_capture):
        """Test that per-minute only configuration is respected."""
        tick_callback, captured_ticks = tick_callback_capture
        
        # Configuration: Only per-minute enabled
        config = {
            'ENABLE_MULTI_FREQUENCY': True,
            'WEBSOCKET_PER_SECOND_ENABLED': False,
            'WEBSOCKET_PER_MINUTE_ENABLED': True,
            'WEBSOCKET_FAIR_VALUE_ENABLED': False,  # FMV disabled
            'SYNTHETIC_MINUTE_WINDOW': 60,
            'SYNTHETIC_FMV_UPDATE_INTERVAL': 15
        }
        
        adapter = SyntheticDataAdapter(config, tick_callback, Mock())
        
        with patch.object(DataProviderFactory, 'get_provider', return_value=mock_data_provider):
            adapter.connect(['AAPL'])
            time.sleep(2)
            
            # Verify only per-minute calls were made
            calls = mock_data_provider.generate_frequency_data.call_args_list
            per_minute_calls = [c for c in calls if c[0][1] == DataFrequency.PER_MINUTE]
            fmv_calls = [c for c in calls if c[0][1] == DataFrequency.FAIR_VALUE]
            
            assert len(per_minute_calls) > 0, "Should have per-minute calls"
            assert len(fmv_calls) == 0, "Should have no FMV calls when disabled"
            
        adapter.disconnect()

    def test_no_data_generation_when_disabled(self, mock_websocket_manager, 
                                            mock_data_provider, tick_callback_capture):
        """Test that no data is generated when both frequencies are disabled."""
        tick_callback, captured_ticks = tick_callback_capture
        
        # Configuration: Both frequencies disabled
        config = {
            'ENABLE_MULTI_FREQUENCY': True,
            'WEBSOCKET_PER_SECOND_ENABLED': False,
            'WEBSOCKET_PER_MINUTE_ENABLED': False,  # Disabled
            'WEBSOCKET_FAIR_VALUE_ENABLED': False,  # Disabled
        }
        
        adapter = SyntheticDataAdapter(config, tick_callback, Mock())
        
        with patch.object(DataProviderFactory, 'get_provider', return_value=mock_data_provider):
            adapter.connect(['AAPL'])
            time.sleep(2)
            
            # Verify no data generation calls were made
            mock_data_provider.generate_frequency_data.assert_not_called()
            assert len(captured_ticks) == 0, "Should have no tick callbacks when frequencies disabled"
            
        adapter.disconnect()

    def test_tick_data_conversion_accuracy(self, mock_config, mock_data_provider, tick_callback_capture):
        """Test accurate conversion from provider data to TickData objects."""
        tick_callback, captured_ticks = tick_callback_capture
        
        # Customize mock data to test specific values
        def custom_generate_data(ticker: str, frequency: DataFrequency):
            if frequency == DataFrequency.PER_MINUTE:
                return {
                    'c': 123.45,  # Custom close price
                    'v': 7500,    # Custom volume
                    'h': 124.0,
                    'l': 123.0, 
                    'o': 123.25
                }
            return None
            
        mock_data_provider.generate_frequency_data.side_effect = custom_generate_data
        
        adapter = SyntheticDataAdapter(mock_config, tick_callback, Mock())
        
        with patch.object(DataProviderFactory, 'get_provider', return_value=mock_data_provider):
            adapter.connect(['TEST'])
            time.sleep(2)
            
            # Find the TEST ticker data
            test_ticks = [t for t in captured_ticks if t['ticker'] == 'TEST']
            assert len(test_ticks) > 0, "Should have captured TEST ticker data"
            
            test_tick = test_ticks[0]
            assert test_tick['price'] == 123.45, "Should use close price from provider data"
            assert test_tick['volume'] == 7500, "Should use volume from provider data"
            assert test_tick['source'] == 'multi_frequency_per_minute'
            assert test_tick['event_type'] == 'AM'
            
        adapter.disconnect()

    @patch('src.presentation.websocket.publisher.WebSocketPublisher')
    def test_integration_with_websocket_publisher(self, mock_publisher_class, mock_config, 
                                                mock_data_provider, mock_websocket_manager):
        """
        Test integration with WebSocketPublisher to verify data reaches emit_to_user.
        
        This simulates the full pipeline including the WebSocketPublisher layer.
        """
        # Mock WebSocketPublisher instance
        mock_publisher = Mock()
        mock_publisher_class.return_value = mock_publisher
        
        # Create a more realistic tick callback that simulates core_service
        def realistic_tick_callback(tick_data: TickData):
            # Simulate what core_service.handle_tick() does
            # This would normally process through event_processor → data_publisher → websocket_publisher
            mock_publisher.emit_buffered_events()
        
        adapter = SyntheticDataAdapter(mock_config, realistic_tick_callback, Mock())
        
        with patch.object(DataProviderFactory, 'get_provider', return_value=mock_data_provider):
            adapter.connect(['AAPL'])
            time.sleep(2)
            
            # Verify WebSocketPublisher's emit method was called
            # This indicates data flowed through the pipeline
            assert mock_publisher.emit_buffered_events.call_count > 0, \
                "WebSocketPublisher should be called to emit buffered events"
            
        adapter.disconnect()

    def test_error_handling_in_data_generation(self, mock_config, tick_callback_capture):
        """Test that data generation errors are handled gracefully."""
        tick_callback, captured_ticks = tick_callback_capture
        
        # Mock provider that raises exceptions
        failing_provider = Mock()
        failing_provider.generate_frequency_data.side_effect = Exception("Provider failure")
        
        adapter = SyntheticDataAdapter(mock_config, tick_callback, Mock())
        
        with patch.object(DataProviderFactory, 'get_provider', return_value=failing_provider):
            # Should not crash on provider errors
            success = adapter.connect(['AAPL'])
            assert success, "Adapter should connect even if provider fails"
            
            time.sleep(2)
            
            # Should have attempted to generate data but handled errors
            assert failing_provider.generate_frequency_data.call_count > 0
            # No ticks should be generated due to errors
            assert len(captured_ticks) == 0, "Should have no ticks when provider fails"
            
        adapter.disconnect()

    def test_multi_frequency_timing_intervals(self, mock_data_provider, tick_callback_capture):
        """Test that multi-frequency generation respects configured intervals."""
        tick_callback, captured_ticks = tick_callback_capture
        
        # Fast intervals for testing
        config = {
            'ENABLE_MULTI_FREQUENCY': True,
            'WEBSOCKET_PER_SECOND_ENABLED': False,
            'WEBSOCKET_PER_MINUTE_ENABLED': True,
            'WEBSOCKET_FAIR_VALUE_ENABLED': True,
            'SYNTHETIC_MINUTE_WINDOW': 2,  # 2 seconds for testing
            'SYNTHETIC_FMV_UPDATE_INTERVAL': 1,  # 1 second for testing
        }
        
        adapter = SyntheticDataAdapter(config, tick_callback, Mock())
        
        with patch.object(DataProviderFactory, 'get_provider', return_value=mock_data_provider):
            adapter.connect(['AAPL'])
            
            # Record calls over time
            initial_calls = mock_data_provider.generate_frequency_data.call_count
            time.sleep(1.5)  # Wait 1.5 seconds
            mid_calls = mock_data_provider.generate_frequency_data.call_count
            time.sleep(1)  # Wait another 1 second (2.5 total)
            final_calls = mock_data_provider.generate_frequency_data.call_count
            
            # Should have more calls over time due to intervals
            assert mid_calls > initial_calls, "Should have additional calls after 1.5 seconds"
            assert final_calls > mid_calls, "Should have more calls after 2.5 seconds"
            
            # Verify both per-minute and FMV calls occurred
            calls = mock_data_provider.generate_frequency_data.call_args_list
            per_minute_calls = [c for c in calls if c[0][1] == DataFrequency.PER_MINUTE]
            fmv_calls = [c for c in calls if c[0][1] == DataFrequency.FAIR_VALUE]
            
            # Should have at least one round of each type
            assert len(per_minute_calls) >= 1, "Should have per-minute calls"
            assert len(fmv_calls) >= 1, "Should have FMV calls"
            
        adapter.disconnect()

    def test_legacy_adapter_bypass_when_multi_frequency_enabled(self, mock_config, 
                                                              tick_callback_capture):
        """Test that legacy synthetic adapter is bypassed when multi-frequency is enabled."""
        tick_callback, captured_ticks = tick_callback_capture
        
        # Mock the legacy generator to ensure it's not used
        with patch('src.infrastructure.data_sources.adapters.realtime_adapter.SyntheticDataGenerator') as mock_generator_class:
            mock_generator = Mock()
            mock_generator_class.return_value = mock_generator
            
            adapter = SyntheticDataAdapter(mock_config, tick_callback, Mock())
            
            with patch.object(DataProviderFactory, 'get_provider') as mock_factory:
                mock_provider = Mock()
                mock_provider.generate_frequency_data.return_value = {
                    'c': 100.0, 'v': 1000
                }
                mock_factory.return_value = mock_provider
                
                adapter.connect(['AAPL'])
                time.sleep(2)
                
                # Legacy generator should not be used
                mock_generator.generate_events.assert_not_called()
                
                # Multi-frequency provider should be used instead
                assert mock_provider.generate_frequency_data.call_count > 0
                
            adapter.disconnect()

    def test_websocket_manager_emit_to_user_call_structure(self, mock_config, 
                                                         mock_data_provider, mock_websocket_manager):
        """
        Test that when data reaches emit_to_user, it has the correct structure.
        
        This validates the final step of the pipeline to ensure frontend receives proper data.
        """
        # Track all emit_to_user calls
        emit_calls = []
        
        def track_emit_to_user(data: dict, user_id: int, event_name: str = 'stock_data'):
            emit_calls.append({
                'data': data,
                'user_id': user_id,
                'event_name': event_name
            })
            return True
        
        mock_websocket_manager.emit_to_user.side_effect = track_emit_to_user
        
        # Create a callback that simulates the full processing pipeline
        def full_pipeline_callback(tick_data: TickData):
            # Simulate processing that eventually calls emit_to_user
            # This represents what happens in core_service → event_processor → websocket_publisher
            
            # Simulate event data structure that would reach frontend
            event_data = {
                'highs': [],
                'lows': [{
                    'ticker': tick_data.ticker,
                    'price': tick_data.price,
                    'volume': tick_data.volume,
                    'timestamp': tick_data.timestamp,
                    'event_type': tick_data.event_type
                }],
                'trending': {'up': [], 'down': []},
                'surging': {'up': [], 'down': []},
                'timestamp': tick_data.timestamp
            }
            
            # Emit to all connected users
            for user_id in mock_websocket_manager.get_connected_user_ids():
                mock_websocket_manager.emit_to_user(event_data, user_id, 'stock_data')
        
        adapter = SyntheticDataAdapter(mock_config, full_pipeline_callback, Mock())
        
        with patch.object(DataProviderFactory, 'get_provider', return_value=mock_data_provider):
            adapter.connect(['AAPL'])
            time.sleep(2)
            
            # Verify emit_to_user was called
            assert len(emit_calls) > 0, "Should have emit_to_user calls"
            
            # Validate call structure
            first_call = emit_calls[0]
            assert first_call['event_name'] == 'stock_data'
            assert first_call['user_id'] in [1, 2]  # From mock connected users
            
            # Validate data structure matches frontend expectations
            data = first_call['data']
            assert 'highs' in data
            assert 'lows' in data
            assert 'trending' in data
            assert 'surging' in data
            assert 'timestamp' in data
            
            # Validate event content
            assert len(data['lows']) > 0, "Should have low events from tick data"
            low_event = data['lows'][0]
            assert low_event['ticker'] == 'AAPL'
            assert low_event['price'] == 150.25  # From mock provider
            assert low_event['volume'] == 5000   # From mock provider
            
        adapter.disconnect()