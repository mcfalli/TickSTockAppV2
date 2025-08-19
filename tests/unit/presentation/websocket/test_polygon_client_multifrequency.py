"""
Unit tests for multi-frequency PolygonWebSocketClient functionality - Sprint 101
Tests PolygonWebSocketClient enhancements for concurrent stream processing.
"""

import pytest
import json
import threading
import time
from unittest.mock import Mock, MagicMock, patch, call
from src.presentation.websocket.polygon_client import PolygonWebSocketClient, StreamConnection
from src.shared.types.frequency import FrequencyType


class TestStreamConnection:
    """Test StreamConnection class for individual frequency streams"""
    
    @pytest.fixture
    def stream_config(self):
        """Stream connection configuration"""
        return {
            'reconnect_attempts': 3,
            'heartbeat_interval': 30,
            'connection_timeout': 10
        }
    
    @pytest.fixture
    def mock_callbacks(self):
        """Mock callback functions"""
        return {
            'on_message': Mock(),
            'on_status': Mock()
        }
    
    def test_stream_connection_initialization(self, stream_config, mock_callbacks):
        """Test StreamConnection initialization"""
        frequency_type = FrequencyType.PER_SECOND
        url = "wss://socket.polygon.io/stocks"
        api_key = "test_api_key"
        
        connection = StreamConnection(
            frequency_type=frequency_type,
            url=url,
            api_key=api_key,
            on_message_callback=mock_callbacks['on_message'],
            on_status_callback=mock_callbacks['on_status'],
            config=stream_config
        )
        
        assert connection.frequency_type == frequency_type
        assert connection.url == url
        assert connection.api_key == api_key
        assert connection.config == stream_config
        assert connection.is_connected is False
        assert connection.websocket is None
        assert connection.reconnect_count == 0
    
    def test_stream_connection_string_representation(self, stream_config, mock_callbacks):
        """Test StreamConnection string representation"""
        connection = StreamConnection(
            frequency_type=FrequencyType.PER_MINUTE,
            url="wss://socket.polygon.io/stocks",
            api_key="test_key",
            on_message_callback=mock_callbacks['on_message'],
            on_status_callback=mock_callbacks['on_status'],
            config=stream_config
        )
        
        str_repr = str(connection)
        assert "PER_MINUTE" in str_repr
        assert "Connected: False" in str_repr
    
    @patch('src.presentation.websocket.polygon_client.websocket.WebSocketApp')
    def test_stream_connection_connect(self, mock_websocket_app, stream_config, mock_callbacks):
        """Test StreamConnection connect method"""
        mock_ws = Mock()
        mock_websocket_app.return_value = mock_ws
        
        connection = StreamConnection(
            frequency_type=FrequencyType.PER_SECOND,
            url="wss://socket.polygon.io/stocks",
            api_key="test_key",
            on_message_callback=mock_callbacks['on_message'],
            on_status_callback=mock_callbacks['on_status'],
            config=stream_config
        )
        
        # Test connect
        connection.connect()
        
        # Verify WebSocket was created and started
        mock_websocket_app.assert_called_once()
        mock_ws.run_forever.assert_called_once()
        assert connection.websocket == mock_ws
    
    def test_stream_connection_subscribe(self, stream_config, mock_callbacks):
        """Test StreamConnection subscription management"""
        connection = StreamConnection(
            frequency_type=FrequencyType.PER_MINUTE,
            url="wss://socket.polygon.io/stocks",
            api_key="test_key",
            on_message_callback=mock_callbacks['on_message'],
            on_status_callback=mock_callbacks['on_status'],
            config=stream_config
        )
        
        # Mock websocket
        mock_ws = Mock()
        connection.websocket = mock_ws
        connection.is_connected = True
        
        # Test subscription
        tickers = ["AAPL", "GOOGL", "MSFT"]
        connection.subscribe(tickers)
        
        # Verify subscription message was sent
        mock_ws.send.assert_called_once()
        sent_message = json.loads(mock_ws.send.call_args[0][0])
        
        assert sent_message["action"] == "subscribe"
        # For per-minute, should have "AM." prefix
        expected_params = "AM.AAPL,AM.GOOGL,AM.MSFT"
        assert sent_message["params"] == expected_params
    
    def test_stream_connection_unsubscribe(self, stream_config, mock_callbacks):
        """Test StreamConnection unsubscription"""
        connection = StreamConnection(
            frequency_type=FrequencyType.FAIR_MARKET_VALUE,
            url="wss://business.polygon.io/stocks",
            api_key="test_business_key",
            on_message_callback=mock_callbacks['on_message'],
            on_status_callback=mock_callbacks['on_status'],
            config=stream_config
        )
        
        # Mock websocket and connection
        mock_ws = Mock()
        connection.websocket = mock_ws
        connection.is_connected = True
        
        # Test unsubscription
        tickers = ["AAPL", "TSLA"]
        connection.unsubscribe(tickers)
        
        # Verify unsubscription message
        mock_ws.send.assert_called_once()
        sent_message = json.loads(mock_ws.send.call_args[0][0])
        
        assert sent_message["action"] == "unsubscribe"
        # For FMV, should have "FMV." prefix
        expected_params = "FMV.AAPL,FMV.TSLA"
        assert sent_message["params"] == expected_params
    
    def test_stream_connection_disconnect(self, stream_config, mock_callbacks):
        """Test StreamConnection disconnect method"""
        connection = StreamConnection(
            frequency_type=FrequencyType.PER_SECOND,
            url="wss://socket.polygon.io/stocks",
            api_key="test_key",
            on_message_callback=mock_callbacks['on_message'],
            on_status_callback=mock_callbacks['on_status'],
            config=stream_config
        )
        
        # Mock connected websocket
        mock_ws = Mock()
        connection.websocket = mock_ws
        connection.is_connected = True
        
        # Test disconnect
        connection.disconnect()
        
        # Verify disconnect was called
        mock_ws.close.assert_called_once()
        assert connection.is_connected is False


class TestPolygonWebSocketClientMultiFrequency:
    """Test PolygonWebSocketClient multi-frequency functionality"""
    
    @pytest.fixture
    def multi_frequency_client_config(self):
        """Multi-frequency client configuration"""
        return {
            'polygon_api_key': 'test_standard_key',
            'polygon_business_api_key': 'test_business_key',
            'enable_per_minute_events': True,
            'enable_fmv_events': True,
            'reconnect_attempts': 3,
            'heartbeat_interval': 30,
            'connection_timeout': 10
        }
    
    @pytest.fixture
    def mock_callbacks(self):
        """Mock callback functions"""
        return {
            'on_tick': Mock(),
            'on_minute_bar': Mock(), 
            'on_fmv': Mock(),
            'on_status': Mock()
        }
    
    @pytest.fixture
    def client(self, multi_frequency_client_config, mock_callbacks):
        """Create PolygonWebSocketClient with multi-frequency support"""
        return PolygonWebSocketClient(
            config=multi_frequency_client_config,
            on_tick=mock_callbacks['on_tick'],
            on_minute_bar=mock_callbacks['on_minute_bar'],
            on_fmv=mock_callbacks['on_fmv'],
            on_status=mock_callbacks['on_status']
        )
    
    def test_client_initialization(self, client, multi_frequency_client_config):
        """Test client initialization with multi-frequency support"""
        # Check frequency types are configured
        assert FrequencyType.PER_SECOND in client.enabled_frequencies
        
        if multi_frequency_client_config.get('enable_per_minute_events'):
            assert FrequencyType.PER_MINUTE in client.enabled_frequencies
            
        if multi_frequency_client_config.get('enable_fmv_events'):
            assert FrequencyType.FAIR_MARKET_VALUE in client.enabled_frequencies
        
        # Check stream connections initialized
        assert len(client.stream_connections) >= 1  # At least per-second
        
        # Each enabled frequency should have a connection
        for freq_type in client.enabled_frequencies:
            assert freq_type in client.stream_connections
    
    def test_get_websocket_url_per_frequency(self, client):
        """Test WebSocket URL selection based on frequency type"""
        # Standard frequencies use standard endpoint
        per_second_url = client._get_websocket_url(FrequencyType.PER_SECOND)
        per_minute_url = client._get_websocket_url(FrequencyType.PER_MINUTE)
        
        assert "socket.polygon.io" in per_second_url
        assert "socket.polygon.io" in per_minute_url
        assert per_second_url == per_minute_url  # Same endpoint
        
        # FMV uses business endpoint
        fmv_url = client._get_websocket_url(FrequencyType.FAIR_MARKET_VALUE)
        assert "business.polygon.io" in fmv_url
    
    def test_get_api_key_per_frequency(self, client, multi_frequency_client_config):
        """Test API key selection based on frequency type"""
        # Standard frequencies use standard key
        per_second_key = client._get_api_key(FrequencyType.PER_SECOND)
        per_minute_key = client._get_api_key(FrequencyType.PER_MINUTE)
        
        assert per_second_key == multi_frequency_client_config['polygon_api_key']
        assert per_minute_key == multi_frequency_client_config['polygon_api_key']
        
        # FMV uses business key
        fmv_key = client._get_api_key(FrequencyType.FAIR_MARKET_VALUE)
        assert fmv_key == multi_frequency_client_config['polygon_business_api_key']
    
    def test_connect_all_streams(self, client):
        """Test connecting all enabled frequency streams"""
        # Mock StreamConnection.connect for each frequency
        for freq_type, connection in client.stream_connections.items():
            connection.connect = Mock()
        
        # Test connect
        client.connect()
        
        # Verify all connections were started
        for freq_type, connection in client.stream_connections.items():
            connection.connect.assert_called_once()
    
    def test_disconnect_all_streams(self, client):
        """Test disconnecting all frequency streams"""
        # Mock StreamConnection.disconnect for each frequency
        for freq_type, connection in client.stream_connections.items():
            connection.disconnect = Mock()
            connection.is_connected = True
        
        # Test disconnect
        client.disconnect()
        
        # Verify all connections were disconnected
        for freq_type, connection in client.stream_connections.items():
            connection.disconnect.assert_called_once()
    
    def test_subscribe_multi_frequency(self, client):
        """Test subscribing to multiple frequencies"""
        tickers = ["AAPL", "GOOGL", "MSFT"]
        
        # Mock stream connections
        for freq_type, connection in client.stream_connections.items():
            connection.subscribe = Mock()
            connection.is_connected = True
        
        # Test subscription
        client.subscribe(tickers)
        
        # Verify each enabled frequency was subscribed
        for freq_type in client.enabled_frequencies:
            connection = client.stream_connections[freq_type]
            connection.subscribe.assert_called_once_with(tickers)
    
    def test_unsubscribe_multi_frequency(self, client):
        """Test unsubscribing from multiple frequencies"""
        tickers = ["AAPL", "TSLA"]
        
        # Mock stream connections
        for freq_type, connection in client.stream_connections.items():
            connection.unsubscribe = Mock()
            connection.is_connected = True
        
        # Test unsubscription
        client.unsubscribe(tickers)
        
        # Verify each enabled frequency was unsubscribed
        for freq_type in client.enabled_frequencies:
            connection = client.stream_connections[freq_type]
            connection.unsubscribe.assert_called_once_with(tickers)
    
    def test_message_routing_per_second(self, client, mock_callbacks):
        """Test message routing for per-second events"""
        # Mock per-second message (A event)
        per_second_message = json.dumps([{
            "ev": "A",  # Per-second aggregate
            "sym": "AAPL",
            "c": 150.25,
            "v": 1000,
            "t": int(time.time() * 1000)
        }])
        
        # Route message
        client._handle_message(FrequencyType.PER_SECOND, per_second_message)
        
        # Should call on_tick callback
        mock_callbacks['on_tick'].assert_called_once()
        
        # Should not call other frequency callbacks
        mock_callbacks['on_minute_bar'].assert_not_called()
        mock_callbacks['on_fmv'].assert_not_called()
    
    def test_message_routing_per_minute(self, client, mock_callbacks, mock_polygon_am_data):
        """Test message routing for per-minute events"""
        # Mock per-minute message (AM event)
        per_minute_message = json.dumps([mock_polygon_am_data])
        
        # Route message  
        client._handle_message(FrequencyType.PER_MINUTE, per_minute_message)
        
        # Should call on_minute_bar callback
        mock_callbacks['on_minute_bar'].assert_called_once()
        
        # Should not call other frequency callbacks
        mock_callbacks['on_tick'].assert_not_called()
        mock_callbacks['on_fmv'].assert_not_called()
    
    def test_message_routing_fmv(self, client, mock_callbacks, mock_polygon_fmv_data):
        """Test message routing for FMV events"""
        # Mock FMV message
        fmv_message = json.dumps([mock_polygon_fmv_data])
        
        # Route message
        client._handle_message(FrequencyType.FAIR_MARKET_VALUE, fmv_message)
        
        # Should call on_fmv callback
        mock_callbacks['on_fmv'].assert_called_once()
        
        # Should not call other frequency callbacks
        mock_callbacks['on_tick'].assert_not_called()
        mock_callbacks['on_minute_bar'].assert_not_called()
    
    def test_status_message_handling(self, client, mock_callbacks):
        """Test status message handling across frequencies"""
        # Mock status message
        status_message = json.dumps([{
            "ev": "status",
            "status": "connected",
            "message": "Connected Successfully"
        }])
        
        # Route status message from per-second stream
        client._handle_message(FrequencyType.PER_SECOND, status_message)
        
        # Should call status callback
        mock_callbacks['on_status'].assert_called_once()
        
        # Get the call arguments
        call_args = mock_callbacks['on_status'].call_args[0]
        assert call_args[0]["status"] == "connected"
    
    def test_stream_isolation_on_error(self, client):
        """Test that stream errors don't affect other streams"""
        # Mock one stream connection failing
        per_second_connection = client.stream_connections[FrequencyType.PER_SECOND]
        per_second_connection.connect = Mock(side_effect=Exception("Connection failed"))
        
        # Mock other connections succeeding
        for freq_type, connection in client.stream_connections.items():
            if freq_type != FrequencyType.PER_SECOND:
                connection.connect = Mock()
        
        # Attempt to connect (should not raise exception due to isolation)
        try:
            client.connect()
        except Exception:
            pytest.fail("Stream error was not isolated")
        
        # Other connections should still have been attempted
        for freq_type, connection in client.stream_connections.items():
            if freq_type != FrequencyType.PER_SECOND:
                connection.connect.assert_called_once()
    
    def test_health_monitoring(self, client):
        """Test health monitoring for multiple streams"""
        # Mock connections with different health states
        client.stream_connections[FrequencyType.PER_SECOND].is_connected = True
        client.stream_connections[FrequencyType.PER_MINUTE].is_connected = False
        
        if FrequencyType.FAIR_MARKET_VALUE in client.stream_connections:
            client.stream_connections[FrequencyType.FAIR_MARKET_VALUE].is_connected = True
        
        # Get health status
        health_status = client.get_connection_status()
        
        # Should report status for each frequency
        assert FrequencyType.PER_SECOND.value in health_status
        assert FrequencyType.PER_MINUTE.value in health_status
        
        assert health_status[FrequencyType.PER_SECOND.value]['connected'] is True
        assert health_status[FrequencyType.PER_MINUTE.value]['connected'] is False
    
    def test_enable_disable_frequency_runtime(self, client):
        """Test enabling/disabling frequencies at runtime"""
        # Initially disable per-minute
        if FrequencyType.PER_MINUTE in client.enabled_frequencies:
            client.enabled_frequencies.remove(FrequencyType.PER_MINUTE)
        
        # Enable per-minute at runtime
        client.enable_frequency(FrequencyType.PER_MINUTE)
        
        # Should be in enabled frequencies
        assert FrequencyType.PER_MINUTE in client.enabled_frequencies
        
        # Should have stream connection
        assert FrequencyType.PER_MINUTE in client.stream_connections
        
        # Disable per-minute
        client.disable_frequency(FrequencyType.PER_MINUTE)
        
        # Should not be in enabled frequencies
        assert FrequencyType.PER_MINUTE not in client.enabled_frequencies
    
    def test_reconnection_per_frequency(self, client):
        """Test reconnection logic for individual frequencies"""
        # Mock a connection that needs reconnection
        per_minute_connection = client.stream_connections.get(FrequencyType.PER_MINUTE)
        if per_minute_connection:
            per_minute_connection.reconnect = Mock()
            per_minute_connection.is_connected = False
            per_minute_connection.reconnect_count = 1
            
            # Trigger reconnection
            client._handle_reconnection(FrequencyType.PER_MINUTE)
            
            # Should attempt reconnection
            per_minute_connection.reconnect.assert_called_once()
    
    @pytest.mark.performance
    def test_concurrent_stream_performance(self, client, performance_timer):
        """Test performance of concurrent stream processing"""
        # Mock multiple rapid messages
        messages = []
        for freq_type in client.enabled_frequencies:
            if freq_type == FrequencyType.PER_SECOND:
                msg = json.dumps([{"ev": "A", "sym": "AAPL", "c": 150.0, "v": 1000, "t": int(time.time()*1000)}])
            elif freq_type == FrequencyType.PER_MINUTE:
                msg = json.dumps([{"ev": "AM", "sym": "AAPL", "c": 150.0, "v": 50000, "s": int(time.time()*1000)}])
            elif freq_type == FrequencyType.FAIR_MARKET_VALUE:
                msg = json.dumps([{"ev": "FMV", "sym": "AAPL", "fmv": 150.75, "t": int(time.time()*1_000_000_000)}])
            else:
                continue
            
            messages.append((freq_type, msg))
        
        performance_timer.start()
        
        # Process multiple messages rapidly
        for _ in range(100):
            for freq_type, message in messages:
                client._handle_message(freq_type, message)
        
        performance_timer.stop()
        
        # Should process messages quickly (< 50ms for 100 iterations)
        assert performance_timer.elapsed < 0.05, f"Message processing took {performance_timer.elapsed:.3f}s"
    
    def test_subscription_tracking(self, client):
        """Test subscription tracking across frequencies"""
        tickers = ["AAPL", "GOOGL", "MSFT"]
        
        # Mock connected streams
        for connection in client.stream_connections.values():
            connection.is_connected = True
            connection.subscribe = Mock()
            connection.subscribed_tickers = set()
        
        # Subscribe
        client.subscribe(tickers)
        
        # Check subscription tracking
        subscriptions = client.get_subscriptions()
        
        for freq_type in client.enabled_frequencies:
            assert freq_type.value in subscriptions
            # Should track subscribed tickers
            freq_subscriptions = subscriptions[freq_type.value]
            assert all(ticker in freq_subscriptions for ticker in tickers)
    
    def test_thread_safety_multi_stream(self, client):
        """Test thread safety of multi-stream operations"""
        errors = []
        
        def stream_operations():
            try:
                for _ in range(50):
                    client.subscribe(["AAPL"])
                    client.unsubscribe(["AAPL"])
                    status = client.get_connection_status()
                    assert isinstance(status, dict)
            except Exception as e:
                errors.append(e)
        
        # Run operations in multiple threads
        threads = [threading.Thread(target=stream_operations) for _ in range(3)]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Should complete without thread safety errors
        assert len(errors) == 0, f"Thread safety errors: {errors}"