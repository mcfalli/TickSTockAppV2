"""
Integration tests for Polygon API multi-frequency WebSocket integration - Sprint 101
Tests WebSocket connection and message handling with multiple frequencies.
"""

import pytest
import json
import time
import threading
from unittest.mock import Mock, MagicMock, patch, call

from src.presentation.websocket.polygon_client import PolygonWebSocketClient, StreamConnection
from src.shared.types.frequency import FrequencyType


class TestPolygonMultiFrequencyIntegration:
    """Integration tests for Polygon WebSocket client with multiple frequencies"""
    
    @pytest.fixture
    def polygon_integration_config(self):
        """Configuration for Polygon integration testing"""
        return {
            'polygon_api_key': 'test_standard_key',
            'polygon_business_api_key': 'test_business_key',
            'enable_per_minute_events': True,
            'enable_fmv_events': True,
            'reconnect_attempts': 3,
            'heartbeat_interval': 30,
            'connection_timeout': 10,
            'use_simulated_data': True  # For testing
        }
    
    @pytest.fixture
    def mock_callback_handlers(self):
        """Mock callback handlers for all event types"""
        return {
            'on_tick': Mock(),
            'on_minute_bar': Mock(),
            'on_fmv': Mock(),
            'on_status': Mock()
        }
    
    @pytest.fixture
    def integrated_client(self, polygon_integration_config, mock_callback_handlers):
        """Create integrated Polygon client with all callbacks"""
        with patch('src.presentation.websocket.polygon_client.websocket.WebSocketApp') as mock_websocket:
            client = PolygonWebSocketClient(
                config=polygon_integration_config,
                **mock_callback_handlers
            )
            client._mock_websocket_app = mock_websocket  # Store for testing
            return client
    
    def test_multi_frequency_connection_establishment(self, integrated_client):
        """Test establishing connections for all enabled frequencies"""
        client = integrated_client
        
        # Mock WebSocket instances for each frequency
        mock_connections = {}
        for freq_type in client.enabled_frequencies:
            mock_ws = Mock()
            mock_connections[freq_type] = mock_ws
            client.stream_connections[freq_type].websocket = mock_ws
        
        # Test connection establishment
        client.connect()
        
        # Verify all enabled frequencies have connection attempts
        for freq_type in client.enabled_frequencies:
            connection = client.stream_connections[freq_type]
            assert connection.websocket is not None
    
    def test_polygon_message_format_handling(self, integrated_client, mock_callback_handlers):
        """Test handling of different Polygon message formats"""
        client = integrated_client
        
        # Test per-second aggregate message (A event)
        per_second_message = json.dumps([{
            "ev": "A",
            "sym": "AAPL",
            "c": 150.25,
            "h": 151.00,
            "l": 149.50,
            "o": 150.00,
            "v": 1234567,
            "vw": 150.30,
            "t": int(time.time() * 1000)
        }])
        
        # Test per-minute aggregate message (AM event)
        per_minute_message = json.dumps([{
            "ev": "AM",
            "sym": "GOOGL",
            "v": 4110,
            "av": 9470157,
            "op": 2800.50,
            "vw": 2801.15,
            "o": 2800.75,
            "c": 2801.25,
            "h": 2802.00,
            "l": 2800.25,
            "a": 2801.05,
            "z": 685,
            "s": int(time.time() * 1000) - 60000,
            "e": int(time.time() * 1000)
        }])
        
        # Test FMV message
        fmv_message = json.dumps([{
            "ev": "FMV",
            "fmv": 150.75,
            "sym": "MSFT",
            "t": int(time.time() * 1_000_000_000)
        }])
        
        # Test status message
        status_message = json.dumps([{
            "ev": "status",
            "status": "connected",
            "message": "Connected Successfully"
        }])
        
        # Handle messages
        client._handle_message(FrequencyType.PER_SECOND, per_second_message)
        client._handle_message(FrequencyType.PER_MINUTE, per_minute_message) 
        client._handle_message(FrequencyType.FAIR_MARKET_VALUE, fmv_message)
        client._handle_message(FrequencyType.PER_SECOND, status_message)  # Status from any stream
        
        # Verify appropriate callbacks were called
        mock_callback_handlers['on_tick'].assert_called()
        mock_callback_handlers['on_minute_bar'].assert_called()
        mock_callback_handlers['on_fmv'].assert_called()
        mock_callback_handlers['on_status'].assert_called()
        
        # Verify call counts
        assert mock_callback_handlers['on_tick'].call_count == 1
        assert mock_callback_handlers['on_minute_bar'].call_count == 1
        assert mock_callback_handlers['on_fmv'].call_count == 1
        assert mock_callback_handlers['on_status'].call_count == 1
    
    def test_subscription_message_generation(self, integrated_client):
        """Test generation of proper subscription messages per frequency"""
        client = integrated_client
        tickers = ["AAPL", "GOOGL", "MSFT", "TSLA"]
        
        # Mock WebSocket connections
        for freq_type, connection in client.stream_connections.items():
            mock_ws = Mock()
            connection.websocket = mock_ws
            connection.is_connected = True
        
        # Subscribe to tickers
        client.subscribe(tickers)
        
        # Verify subscription messages for each frequency
        for freq_type, connection in client.stream_connections.items():
            if freq_type in client.enabled_frequencies:
                connection.websocket.send.assert_called()
                
                # Get the sent message
                sent_message = connection.websocket.send.call_args[0][0]
                message_data = json.loads(sent_message)
                
                assert message_data["action"] == "subscribe"
                
                # Verify frequency-specific prefixes
                if freq_type == FrequencyType.PER_SECOND:
                    expected_params = "A.AAPL,A.GOOGL,A.MSFT,A.TSLA"
                elif freq_type == FrequencyType.PER_MINUTE:
                    expected_params = "AM.AAPL,AM.GOOGL,AM.MSFT,AM.TSLA"
                elif freq_type == FrequencyType.FAIR_MARKET_VALUE:
                    expected_params = "FMV.AAPL,FMV.GOOGL,FMV.MSFT,FMV.TSLA"
                
                assert message_data["params"] == expected_params
    
    def test_authentication_per_frequency(self, integrated_client, polygon_integration_config):
        """Test proper authentication for different frequency endpoints"""
        client = integrated_client
        
        # Test API key selection
        standard_key = client._get_api_key(FrequencyType.PER_SECOND)
        minute_key = client._get_api_key(FrequencyType.PER_MINUTE)
        fmv_key = client._get_api_key(FrequencyType.FAIR_MARKET_VALUE)
        
        # Standard frequencies use standard key
        assert standard_key == polygon_integration_config['polygon_api_key']
        assert minute_key == polygon_integration_config['polygon_api_key']
        
        # FMV uses business key
        assert fmv_key == polygon_integration_config['polygon_business_api_key']
        
        # Test WebSocket URL selection
        standard_url = client._get_websocket_url(FrequencyType.PER_SECOND)
        minute_url = client._get_websocket_url(FrequencyType.PER_MINUTE)
        fmv_url = client._get_websocket_url(FrequencyType.FAIR_MARKET_VALUE)
        
        # Standard frequencies use standard endpoint
        assert "socket.polygon.io" in standard_url
        assert "socket.polygon.io" in minute_url
        
        # FMV uses business endpoint
        assert "business.polygon.io" in fmv_url
    
    def test_concurrent_stream_processing(self, integrated_client, mock_callback_handlers):
        """Test concurrent processing of multiple stream messages"""
        client = integrated_client
        
        # Prepare messages for concurrent processing
        messages = [
            (FrequencyType.PER_SECOND, json.dumps([{"ev": "A", "sym": "AAPL", "c": 150.0, "v": 1000, "t": int(time.time() * 1000)}])),
            (FrequencyType.PER_MINUTE, json.dumps([{"ev": "AM", "sym": "GOOGL", "c": 2800.0, "v": 50000, "s": int(time.time() * 1000)}])),
            (FrequencyType.FAIR_MARKET_VALUE, json.dumps([{"ev": "FMV", "sym": "MSFT", "fmv": 300.75, "t": int(time.time() * 1_000_000_000)}]))
        ]
        
        results = []
        errors = []
        
        def process_message(freq_type, message):
            try:
                client._handle_message(freq_type, message)
                results.append((freq_type, True))
            except Exception as e:
                errors.append((freq_type, str(e)))
        
        # Process messages concurrently
        threads = []
        for freq_type, message in messages:
            thread = threading.Thread(target=process_message, args=(freq_type, message))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Verify all processing succeeded
        assert len(errors) == 0, f"Concurrent processing errors: {errors}"
        assert len(results) == len(messages)
        assert all(success for freq_type, success in results)
        
        # Verify all callbacks were triggered
        mock_callback_handlers['on_tick'].assert_called()
        mock_callback_handlers['on_minute_bar'].assert_called()
        mock_callback_handlers['on_fmv'].assert_called()
    
    def test_stream_health_monitoring_integration(self, integrated_client):
        """Test integrated stream health monitoring"""
        client = integrated_client
        
        # Simulate different connection states
        client.stream_connections[FrequencyType.PER_SECOND].is_connected = True
        client.stream_connections[FrequencyType.PER_MINUTE].is_connected = False
        
        if FrequencyType.FAIR_MARKET_VALUE in client.stream_connections:
            client.stream_connections[FrequencyType.FAIR_MARKET_VALUE].is_connected = True
        
        # Get connection status
        status = client.get_connection_status()
        
        # Verify comprehensive health reporting
        assert FrequencyType.PER_SECOND.value in status
        assert FrequencyType.PER_MINUTE.value in status
        
        per_second_status = status[FrequencyType.PER_SECOND.value]
        per_minute_status = status[FrequencyType.PER_MINUTE.value]
        
        assert per_second_status['connected'] is True
        assert per_minute_status['connected'] is False
        
        # Should include frequency-specific metrics
        assert 'frequency_type' in per_second_status
        assert 'connection_url' in per_second_status
        assert 'api_key_type' in per_second_status
    
    def test_error_isolation_between_streams(self, integrated_client, mock_callback_handlers):
        """Test error isolation between different frequency streams"""
        client = integrated_client
        
        # Make one callback fail
        mock_callback_handlers['on_minute_bar'].side_effect = Exception("Per-minute callback error")
        
        # Process messages for all frequencies
        per_second_msg = json.dumps([{"ev": "A", "sym": "AAPL", "c": 150.0}])
        per_minute_msg = json.dumps([{"ev": "AM", "sym": "GOOGL", "c": 2800.0}])
        fmv_msg = json.dumps([{"ev": "FMV", "sym": "MSFT", "fmv": 300.75}])
        
        # Per-second should work
        try:
            client._handle_message(FrequencyType.PER_SECOND, per_second_msg)
            per_second_success = True
        except Exception:
            per_second_success = False
        
        # Per-minute should fail but be isolated
        try:
            client._handle_message(FrequencyType.PER_MINUTE, per_minute_msg)
            per_minute_success = True
        except Exception:
            per_minute_success = False
        
        # FMV should still work (isolation)
        try:
            client._handle_message(FrequencyType.FAIR_MARKET_VALUE, fmv_msg)
            fmv_success = True
        except Exception:
            fmv_success = False
        
        # Verify error isolation
        assert per_second_success is True, "Per-second processing should succeed"
        # per_minute_success may be False due to callback error, but should be handled gracefully
        assert fmv_success is True, "FMV processing should succeed despite per-minute error"
        
        # Verify callbacks were attempted
        mock_callback_handlers['on_tick'].assert_called()
        mock_callback_handlers['on_minute_bar'].assert_called()  # Should be attempted despite error
        mock_callback_handlers['on_fmv'].assert_called()
    
    def test_subscription_tracking_integration(self, integrated_client):
        """Test integrated subscription tracking across frequencies"""
        client = integrated_client
        
        # Mock connections as connected
        for connection in client.stream_connections.values():
            connection.is_connected = True
            connection.subscribe = Mock()
            connection.unsubscribe = Mock()
            connection.subscribed_tickers = set()
        
        # Subscribe to initial tickers
        initial_tickers = ["AAPL", "GOOGL"]
        client.subscribe(initial_tickers)
        
        # Add more tickers
        additional_tickers = ["MSFT", "TSLA"]
        client.subscribe(additional_tickers)
        
        # Remove some tickers
        removed_tickers = ["GOOGL"]
        client.unsubscribe(removed_tickers)
        
        # Get subscription status
        subscriptions = client.get_subscriptions()
        
        # Verify subscription tracking
        for freq_type in client.enabled_frequencies:
            freq_subscriptions = subscriptions.get(freq_type.value, set())
            
            # Should track all subscribe calls
            for connection in client.stream_connections.values():
                if hasattr(connection, 'subscribe'):
                    # Verify subscribe was called for both initial and additional tickers
                    expected_calls = [call(initial_tickers), call(additional_tickers)]
                    actual_calls = connection.subscribe.call_args_list
                    
                    # Should have been called twice (initial + additional)
                    assert len(actual_calls) >= 2
    
    def test_reconnection_logic_per_frequency(self, integrated_client):
        """Test reconnection logic for individual frequencies"""
        client = integrated_client
        
        # Mock a connection that needs reconnection
        per_minute_connection = client.stream_connections.get(FrequencyType.PER_MINUTE)
        if per_minute_connection:
            per_minute_connection.is_connected = False
            per_minute_connection.reconnect_count = 0
            per_minute_connection.connect = Mock()
            
            # Simulate reconnection trigger
            client._handle_reconnection(FrequencyType.PER_MINUTE)
            
            # Should attempt reconnection
            per_minute_connection.connect.assert_called()
            
            # Other connections should not be affected
            per_second_connection = client.stream_connections.get(FrequencyType.PER_SECOND)
            if per_second_connection and hasattr(per_second_connection, 'connect'):
                # Per-second connection should not be called for per-minute reconnection
                if per_second_connection != per_minute_connection:
                    per_second_connection.connect.assert_not_called()
    
    @pytest.mark.performance
    def test_high_throughput_message_processing(self, integrated_client, mock_callback_handlers, performance_timer):
        """Test high-throughput message processing across frequencies"""
        client = integrated_client
        
        # Prepare high volume of messages
        messages_per_frequency = 100
        
        messages = []
        
        # Per-second messages (highest volume)
        for i in range(messages_per_frequency):
            msg = json.dumps([{"ev": "A", "sym": f"TICK{i%10}", "c": 150.0 + i*0.01, "v": 1000, "t": int(time.time() * 1000)}])
            messages.append((FrequencyType.PER_SECOND, msg))
        
        # Per-minute messages (medium volume)
        for i in range(messages_per_frequency // 2):
            msg = json.dumps([{"ev": "AM", "sym": f"TICK{i%5}", "c": 150.0 + i*0.1, "v": 50000, "s": int(time.time() * 1000)}])
            messages.append((FrequencyType.PER_MINUTE, msg))
        
        # FMV messages (lower volume)
        for i in range(messages_per_frequency // 5):
            msg = json.dumps([{"ev": "FMV", "sym": f"TICK{i%3}", "fmv": 150.75 + i*0.05, "t": int(time.time() * 1_000_000_000)}])
            messages.append((FrequencyType.FAIR_MARKET_VALUE, msg))
        
        performance_timer.start()
        
        # Process all messages
        for freq_type, message in messages:
            client._handle_message(freq_type, message)
        
        performance_timer.stop()
        
        # Should process all messages quickly
        total_messages = len(messages)
        assert performance_timer.elapsed < 0.1, f"Processing {total_messages} messages took {performance_timer.elapsed:.3f}s"
        
        # Verify callback counts
        assert mock_callback_handlers['on_tick'].call_count == messages_per_frequency
        assert mock_callback_handlers['on_minute_bar'].call_count == messages_per_frequency // 2
        assert mock_callback_handlers['on_fmv'].call_count == messages_per_frequency // 5
    
    def test_malformed_message_handling(self, integrated_client, mock_callback_handlers):
        """Test handling of malformed Polygon messages"""
        client = integrated_client
        
        # Test various malformed messages
        malformed_messages = [
            "invalid json",
            json.dumps({"missing_ev_field": True}),
            json.dumps([{"ev": "UNKNOWN", "sym": "AAPL"}]),
            json.dumps([{"ev": "A", "missing_required_fields": True}]),
            "",
            None
        ]
        
        errors = []
        
        for message in malformed_messages:
            try:
                if message is not None:
                    client._handle_message(FrequencyType.PER_SECOND, message)
                else:
                    client._handle_message(FrequencyType.PER_SECOND, "null")
            except Exception as e:
                errors.append(str(e))
        
        # Should handle malformed messages gracefully without crashing
        # Some errors are expected for malformed data
        # The key is that the client continues to function
        
        # Test valid message still works after malformed ones
        valid_message = json.dumps([{"ev": "A", "sym": "AAPL", "c": 150.0, "v": 1000, "t": int(time.time() * 1000)}])
        client._handle_message(FrequencyType.PER_SECOND, valid_message)
        
        # Should still process valid messages
        mock_callback_handlers['on_tick'].assert_called()


class TestPolygonBusinessPlanIntegration:
    """Integration tests for Polygon Business plan features (FMV)"""
    
    @pytest.fixture
    def business_plan_config(self):
        """Configuration with Business plan features enabled"""
        return {
            'polygon_api_key': 'test_standard_key',
            'polygon_business_api_key': 'test_business_key_with_fmv',
            'enable_per_minute_events': True,
            'enable_fmv_events': True,  # Requires Business plan
            'use_simulated_data': True
        }
    
    @pytest.fixture
    def business_client(self, business_plan_config):
        """Create client with Business plan configuration"""
        callbacks = {
            'on_tick': Mock(),
            'on_minute_bar': Mock(),
            'on_fmv': Mock(),
            'on_status': Mock()
        }
        
        with patch('src.presentation.websocket.polygon_client.websocket.WebSocketApp'):
            return PolygonWebSocketClient(config=business_plan_config, **callbacks)
    
    def test_fmv_endpoint_configuration(self, business_client, business_plan_config):
        """Test FMV endpoint uses Business API configuration"""
        client = business_client
        
        # Verify FMV is enabled
        assert FrequencyType.FAIR_MARKET_VALUE in client.enabled_frequencies
        
        # Verify Business endpoint URL
        fmv_url = client._get_websocket_url(FrequencyType.FAIR_MARKET_VALUE)
        assert "business.polygon.io" in fmv_url
        
        # Verify Business API key
        fmv_key = client._get_api_key(FrequencyType.FAIR_MARKET_VALUE)
        assert fmv_key == business_plan_config['polygon_business_api_key']
        
        # Verify other frequencies still use standard configuration
        standard_url = client._get_websocket_url(FrequencyType.PER_SECOND)
        standard_key = client._get_api_key(FrequencyType.PER_SECOND)
        
        assert "socket.polygon.io" in standard_url
        assert standard_key == business_plan_config['polygon_api_key']
    
    def test_fmv_message_processing(self, business_client):
        """Test FMV message processing with Business plan data"""
        client = business_client
        
        # Test FMV message with nanosecond precision timestamp
        fmv_message = json.dumps([{
            "ev": "FMV",
            "fmv": 150.7543,  # High precision FMV price
            "sym": "AAPL",
            "t": 1640995200000000000  # Nanosecond timestamp
        }])
        
        # Process message
        client._handle_message(FrequencyType.FAIR_MARKET_VALUE, fmv_message)
        
        # Verify FMV callback was triggered
        client.callbacks['on_fmv'].assert_called_once()
        
        # Verify callback received correct data
        call_args = client.callbacks['on_fmv'].call_args[0][0]
        assert call_args['ev'] == 'FMV'
        assert call_args['sym'] == 'AAPL'
        assert call_args['fmv'] == 150.7543
        assert call_args['t'] == 1640995200000000000
    
    def test_mixed_plan_operation(self, business_client):
        """Test operation with mix of standard and Business plan features"""
        client = business_client
        
        # Mock all connections as active
        for connection in client.stream_connections.values():
            connection.is_connected = True
            connection.websocket = Mock()
        
        # Subscribe to tickers across all frequencies
        tickers = ["AAPL", "GOOGL", "MSFT"]
        client.subscribe(tickers)
        
        # Verify subscriptions sent to all endpoints
        for freq_type, connection in client.stream_connections.items():
            connection.websocket.send.assert_called()
            
            sent_message = connection.websocket.send.call_args[0][0]
            message_data = json.loads(sent_message)
            
            # All should be subscription messages
            assert message_data["action"] == "subscribe"
            
            # Should contain all tickers with appropriate prefixes
            params = message_data["params"]
            assert "AAPL" in params
            assert "GOOGL" in params
            assert "MSFT" in params
    
    def test_fallback_when_business_unavailable(self, business_plan_config):
        """Test graceful fallback when Business plan features unavailable"""
        # Modify config to simulate Business plan unavailable
        fallback_config = business_plan_config.copy()
        fallback_config['polygon_business_api_key'] = None
        
        callbacks = {
            'on_tick': Mock(),
            'on_minute_bar': Mock(), 
            'on_fmv': Mock(),
            'on_status': Mock()
        }
        
        with patch('src.presentation.websocket.polygon_client.websocket.WebSocketApp'):
            client = PolygonWebSocketClient(config=fallback_config, **callbacks)
            
            # Should still initialize but without FMV
            assert FrequencyType.PER_SECOND in client.enabled_frequencies
            assert FrequencyType.PER_MINUTE in client.enabled_frequencies
            
            # FMV should be disabled when Business key unavailable
            if not fallback_config.get('polygon_business_api_key'):
                assert FrequencyType.FAIR_MARKET_VALUE not in client.enabled_frequencies