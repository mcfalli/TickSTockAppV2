"""
Unit tests for RealTimeDataAdapter.

Sprint 51: Multi-Connection WebSocket Support
Focus: Backward compatibility and multi-connection mode initialization
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from src.infrastructure.data_sources.adapters.realtime_adapter import RealTimeDataAdapter


class TestRealTimeAdapterBackwardCompatibility:
    """Test backward compatibility (single-connection mode)."""

    def test_init_without_massive_api(self):
        """Test initialization without Massive API configured."""
        config = {
            'USE_MASSIVE_API': False,
            'MASSIVE_API_KEY': ''
        }
        tick_callback = Mock()
        status_callback = Mock()

        adapter = RealTimeDataAdapter(config, tick_callback, status_callback)

        assert adapter.client is None
        assert adapter.config == config
        assert adapter.tick_callback == tick_callback
        assert adapter.status_callback == status_callback

    @patch('src.infrastructure.data_sources.adapters.realtime_adapter.MassiveWebSocketClient')
    def test_init_single_connection_mode_default(self, mock_client_class):
        """Test single-connection mode (default behavior)."""
        config = {
            'USE_MASSIVE_API': True,
            'MASSIVE_API_KEY': 'test_key',
            'USE_MULTI_CONNECTION': False  # Explicit single-connection
        }
        tick_callback = Mock()
        status_callback = Mock()

        adapter = RealTimeDataAdapter(config, tick_callback, status_callback)

        # Should create single MassiveWebSocketClient
        mock_client_class.assert_called_once_with(
            api_key='test_key',
            on_tick_callback=tick_callback,
            on_status_callback=status_callback,
            config=config
        )
        assert adapter.client == mock_client_class.return_value

    @patch('src.infrastructure.data_sources.adapters.realtime_adapter.MassiveWebSocketClient')
    def test_init_single_connection_no_multi_flag(self, mock_client_class):
        """Test single-connection mode when USE_MULTI_CONNECTION not set."""
        config = {
            'USE_MASSIVE_API': True,
            'MASSIVE_API_KEY': 'test_key'
            # No USE_MULTI_CONNECTION key - should default to False
        }
        tick_callback = Mock()
        status_callback = Mock()

        adapter = RealTimeDataAdapter(config, tick_callback, status_callback)

        # Should create single MassiveWebSocketClient
        mock_client_class.assert_called_once()
        assert adapter.client is not None

    def test_connect_no_client(self):
        """Test connect when no client configured."""
        config = {'USE_MASSIVE_API': False}
        adapter = RealTimeDataAdapter(config, Mock(), Mock())

        result = adapter.connect(['AAPL', 'NVDA'])

        assert result is False

    @patch('src.infrastructure.data_sources.adapters.realtime_adapter.MassiveWebSocketClient')
    def test_connect_single_connection_success(self, mock_client_class):
        """Test successful connection in single-connection mode."""
        config = {
            'USE_MASSIVE_API': True,
            'MASSIVE_API_KEY': 'test_key',
            'USE_MULTI_CONNECTION': False
        }
        adapter = RealTimeDataAdapter(config, Mock(), Mock())

        # Mock client connect and subscribe
        mock_client = mock_client_class.return_value
        mock_client.connect.return_value = True

        result = adapter.connect(['AAPL', 'NVDA'])

        assert result is True
        mock_client.connect.assert_called_once()
        mock_client.subscribe.assert_called_once_with(['AAPL', 'NVDA'])

    @patch('src.infrastructure.data_sources.adapters.realtime_adapter.MassiveWebSocketClient')
    def test_connect_single_connection_failure(self, mock_client_class):
        """Test failed connection in single-connection mode."""
        config = {
            'USE_MASSIVE_API': True,
            'MASSIVE_API_KEY': 'test_key',
            'USE_MULTI_CONNECTION': False
        }
        adapter = RealTimeDataAdapter(config, Mock(), Mock())

        # Mock client connect failure
        mock_client = mock_client_class.return_value
        mock_client.connect.return_value = False

        result = adapter.connect(['AAPL', 'NVDA'])

        assert result is False
        mock_client.connect.assert_called_once()
        mock_client.subscribe.assert_not_called()

    @patch('src.infrastructure.data_sources.adapters.realtime_adapter.MassiveWebSocketClient')
    def test_disconnect_single_connection(self, mock_client_class):
        """Test disconnect in single-connection mode."""
        config = {
            'USE_MASSIVE_API': True,
            'MASSIVE_API_KEY': 'test_key',
            'USE_MULTI_CONNECTION': False
        }
        adapter = RealTimeDataAdapter(config, Mock(), Mock())

        mock_client = mock_client_class.return_value

        adapter.disconnect()

        mock_client.disconnect.assert_called_once()


class TestRealTimeAdapterMultiConnection:
    """Test multi-connection mode initialization."""

    @patch('src.infrastructure.websocket.multi_connection_manager.MultiConnectionManager')
    def test_init_multi_connection_mode(self, mock_manager_class):
        """Test multi-connection mode initialization."""
        config = {
            'USE_MASSIVE_API': True,
            'MASSIVE_API_KEY': 'test_key',
            'USE_MULTI_CONNECTION': True,
            'WEBSOCKET_CONNECTIONS_MAX': 3
        }
        tick_callback = Mock()
        status_callback = Mock()

        adapter = RealTimeDataAdapter(config, tick_callback, status_callback)

        # Should create MultiConnectionManager
        mock_manager_class.assert_called_once_with(
            config=config,
            on_tick_callback=tick_callback,
            on_status_callback=status_callback,
            max_connections=3
        )
        assert adapter.client == mock_manager_class.return_value

    @patch('src.infrastructure.websocket.multi_connection_manager.MultiConnectionManager')
    def test_connect_multi_connection_success(self, mock_manager_class):
        """Test successful connection in multi-connection mode."""
        config = {
            'USE_MASSIVE_API': True,
            'MASSIVE_API_KEY': 'test_key',
            'USE_MULTI_CONNECTION': True,
            'WEBSOCKET_CONNECTIONS_MAX': 3
        }
        adapter = RealTimeDataAdapter(config, Mock(), Mock())

        # Mock manager connect
        mock_manager = mock_manager_class.return_value
        mock_manager.connect.return_value = True

        result = adapter.connect(['AAPL', 'NVDA'])

        assert result is True
        mock_manager.connect.assert_called_once()
        mock_manager.subscribe.assert_called_once_with(['AAPL', 'NVDA'])

    @patch('src.infrastructure.websocket.multi_connection_manager.MultiConnectionManager')
    def test_disconnect_multi_connection(self, mock_manager_class):
        """Test disconnect in multi-connection mode."""
        config = {
            'USE_MASSIVE_API': True,
            'MASSIVE_API_KEY': 'test_key',
            'USE_MULTI_CONNECTION': True
        }
        adapter = RealTimeDataAdapter(config, Mock(), Mock())

        mock_manager = mock_manager_class.return_value

        adapter.disconnect()

        mock_manager.disconnect.assert_called_once()


class TestRealTimeAdapterCallbacks:
    """Test callback routing in both modes."""

    @patch('src.infrastructure.data_sources.adapters.realtime_adapter.MassiveWebSocketClient')
    def test_callbacks_passed_to_single_client(self, mock_client_class):
        """Test callbacks properly passed to single client."""
        tick_callback = Mock()
        status_callback = Mock()
        config = {
            'USE_MASSIVE_API': True,
            'MASSIVE_API_KEY': 'test_key',
            'USE_MULTI_CONNECTION': False
        }

        adapter = RealTimeDataAdapter(config, tick_callback, status_callback)

        call_args = mock_client_class.call_args
        assert call_args.kwargs['on_tick_callback'] == tick_callback
        assert call_args.kwargs['on_status_callback'] == status_callback

    @patch('src.infrastructure.websocket.multi_connection_manager.MultiConnectionManager')
    def test_callbacks_passed_to_multi_manager(self, mock_manager_class):
        """Test callbacks properly passed to multi-connection manager."""
        tick_callback = Mock()
        status_callback = Mock()
        config = {
            'USE_MASSIVE_API': True,
            'MASSIVE_API_KEY': 'test_key',
            'USE_MULTI_CONNECTION': True
        }

        adapter = RealTimeDataAdapter(config, tick_callback, status_callback)

        call_args = mock_manager_class.call_args
        assert call_args.kwargs['on_tick_callback'] == tick_callback
        assert call_args.kwargs['on_status_callback'] == status_callback
