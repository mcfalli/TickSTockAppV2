"""
Unit tests for MultiConnectionManager.

Sprint 51: Multi-Connection WebSocket Support
Focus: Connection initialization, ticker routing, callback aggregation
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
import threading

from src.infrastructure.websocket.multi_connection_manager import (
    MultiConnectionManager,
    ConnectionInfo
)


class TestMultiConnectionManagerInit:
    """Test manager initialization and configuration."""

    def test_init_no_connections_enabled(self):
        """Test initialization when no connections enabled."""
        config = {
            'USE_MULTI_CONNECTION': True,
            'MASSIVE_API_KEY': 'test_key',
            'WEBSOCKET_CONNECTION_1_ENABLED': False,
            'WEBSOCKET_CONNECTION_2_ENABLED': False,
            'WEBSOCKET_CONNECTION_3_ENABLED': False
        }

        manager = MultiConnectionManager(config, Mock(), Mock())

        assert len(manager.connections) == 0
        assert manager.max_connections == 3

    @patch('src.infrastructure.cache.cache_control.CacheControl')
    def test_init_one_connection_with_universe(self, mock_cache_class):
        """Test initialization with one connection using universe key."""
        mock_cache = mock_cache_class.return_value
        mock_cache.get_universe_tickers.return_value = ['AAPL', 'NVDA', 'TSLA']

        config = {
            'USE_MULTI_CONNECTION': True,
            'MASSIVE_API_KEY': 'test_key',
            'WEBSOCKET_CONNECTION_1_ENABLED': True,
            'WEBSOCKET_CONNECTION_1_NAME': 'primary',
            'WEBSOCKET_CONNECTION_1_UNIVERSE_KEY': 'tech_leaders:top_3',
            'WEBSOCKET_CONNECTION_2_ENABLED': False,
            'WEBSOCKET_CONNECTION_3_ENABLED': False
        }

        manager = MultiConnectionManager(config, Mock(), Mock())

        assert len(manager.connections) == 1
        assert 'connection_1' in manager.connections
        conn = manager.connections['connection_1']
        assert conn.name == 'primary'
        assert conn.assigned_tickers == {'AAPL', 'NVDA', 'TSLA'}

    def test_init_with_direct_symbols(self):
        """Test initialization with direct symbol list."""
        config = {
            'USE_MULTI_CONNECTION': True,
            'MASSIVE_API_KEY': 'test_key',
            'WEBSOCKET_CONNECTION_1_ENABLED': True,
            'WEBSOCKET_CONNECTION_1_NAME': 'test',
            'WEBSOCKET_CONNECTION_1_SYMBOLS': 'AAPL,NVDA,TSLA',
            'WEBSOCKET_CONNECTION_2_ENABLED': False,
            'WEBSOCKET_CONNECTION_3_ENABLED': False
        }

        manager = MultiConnectionManager(config, Mock(), Mock())

        assert len(manager.connections) == 1
        conn = manager.connections['connection_1']
        assert conn.assigned_tickers == {'AAPL', 'NVDA', 'TSLA'}

    @patch('src.infrastructure.cache.cache_control.CacheControl')
    def test_init_multiple_connections(self, mock_cache_class):
        """Test initialization with multiple connections."""
        mock_cache = mock_cache_class.return_value
        mock_cache.get_universe_tickers.side_effect = [
            ['AAPL', 'NVDA'],
            ['JPM', 'BAC']
        ]

        config = {
            'USE_MULTI_CONNECTION': True,
            'MASSIVE_API_KEY': 'test_key',
            'WEBSOCKET_CONNECTION_1_ENABLED': True,
            'WEBSOCKET_CONNECTION_1_UNIVERSE_KEY': 'tech',
            'WEBSOCKET_CONNECTION_2_ENABLED': True,
            'WEBSOCKET_CONNECTION_2_UNIVERSE_KEY': 'finance',
            'WEBSOCKET_CONNECTION_3_ENABLED': False
        }

        manager = MultiConnectionManager(config, Mock(), Mock())

        assert len(manager.connections) == 2
        assert 'connection_1' in manager.connections
        assert 'connection_2' in manager.connections


class TestMultiConnectionManagerConnect:
    """Test connection management."""

    @patch('src.infrastructure.websocket.multi_connection_manager.MassiveWebSocketClient')
    def test_connect_no_connections_configured(self, mock_client_class):
        """Test connect when no connections configured."""
        config = {
            'USE_MULTI_CONNECTION': True,
            'MASSIVE_API_KEY': 'test_key',
            'WEBSOCKET_CONNECTION_1_ENABLED': False,
            'WEBSOCKET_CONNECTION_2_ENABLED': False,
            'WEBSOCKET_CONNECTION_3_ENABLED': False
        }

        manager = MultiConnectionManager(config, Mock(), Mock())
        result = manager.connect()

        assert result is False
        mock_client_class.assert_not_called()

    @patch('src.infrastructure.websocket.multi_connection_manager.MassiveWebSocketClient')
    def test_connect_single_connection_success(self, mock_client_class):
        """Test successful connection with one connection."""
        config = {
            'USE_MULTI_CONNECTION': True,
            'MASSIVE_API_KEY': 'test_key',
            'WEBSOCKET_CONNECTION_1_ENABLED': True,
            'WEBSOCKET_CONNECTION_1_SYMBOLS': 'AAPL,NVDA',
            'WEBSOCKET_CONNECTION_2_ENABLED': False,
            'WEBSOCKET_CONNECTION_3_ENABLED': False
        }

        # Mock client success
        mock_client = Mock()
        mock_client.connect.return_value = True
        mock_client_class.return_value = mock_client

        manager = MultiConnectionManager(config, Mock(), Mock())
        result = manager.connect()

        assert result is True
        assert manager.connections['connection_1'].status == 'connected'
        mock_client.connect.assert_called_once()
        mock_client.subscribe.assert_called_once()

    @patch('src.infrastructure.websocket.multi_connection_manager.MassiveWebSocketClient')
    def test_connect_partial_success(self, mock_client_class):
        """Test connect with some connections failing."""
        config = {
            'USE_MULTI_CONNECTION': True,
            'MASSIVE_API_KEY': 'test_key',
            'WEBSOCKET_CONNECTION_1_ENABLED': True,
            'WEBSOCKET_CONNECTION_1_SYMBOLS': 'AAPL',
            'WEBSOCKET_CONNECTION_2_ENABLED': True,
            'WEBSOCKET_CONNECTION_2_SYMBOLS': 'NVDA',
            'WEBSOCKET_CONNECTION_3_ENABLED': False
        }

        # Mock first client success, second failure
        mock_client_1 = Mock()
        mock_client_1.connect.return_value = True
        mock_client_2 = Mock()
        mock_client_2.connect.return_value = False
        mock_client_class.side_effect = [mock_client_1, mock_client_2]

        manager = MultiConnectionManager(config, Mock(), Mock())
        result = manager.connect()

        # Should return True if at least one succeeds
        assert result is True
        assert manager.connections['connection_1'].status == 'connected'
        assert manager.connections['connection_2'].status == 'error'


class TestMultiConnectionManagerCallbacks:
    """Test callback aggregation."""

    @patch('src.infrastructure.websocket.multi_connection_manager.MassiveWebSocketClient')
    def test_tick_callback_aggregation(self, mock_client_class):
        """Test tick callbacks aggregated from multiple connections."""
        tick_callback = Mock()
        mock_client = Mock()
        mock_client.connect.return_value = True
        mock_client_class.return_value = mock_client

        config = {
            'USE_MULTI_CONNECTION': True,
            'MASSIVE_API_KEY': 'test_key',
            'WEBSOCKET_CONNECTION_1_ENABLED': True,
            'WEBSOCKET_CONNECTION_1_SYMBOLS': 'AAPL',
            'WEBSOCKET_CONNECTION_2_ENABLED': False,
            'WEBSOCKET_CONNECTION_3_ENABLED': False
        }

        manager = MultiConnectionManager(config, tick_callback, Mock())
        manager.connect()  # Clients created during connect

        # Get the callback that was passed to the client
        client_tick_callback = mock_client_class.call_args.kwargs['on_tick_callback']

        # Simulate tick from connection
        mock_tick = Mock()
        client_tick_callback(mock_tick)

        # User callback should be invoked
        tick_callback.assert_called_once_with(mock_tick)
        assert manager.total_ticks_received == 1

    @patch('src.infrastructure.websocket.multi_connection_manager.MassiveWebSocketClient')
    def test_status_callback_aggregation(self, mock_client_class):
        """Test status callbacks aggregated with connection info."""
        status_callback = Mock()
        mock_client = Mock()
        mock_client.connect.return_value = True
        mock_client_class.return_value = mock_client

        config = {
            'USE_MULTI_CONNECTION': True,
            'MASSIVE_API_KEY': 'test_key',
            'WEBSOCKET_CONNECTION_1_ENABLED': True,
            'WEBSOCKET_CONNECTION_1_SYMBOLS': 'AAPL',
            'WEBSOCKET_CONNECTION_2_ENABLED': False,
            'WEBSOCKET_CONNECTION_3_ENABLED': False
        }

        manager = MultiConnectionManager(config, Mock(), status_callback)
        manager.connect()  # Clients created during connect

        # Get the callback that was passed to the client
        client_status_callback = mock_client_class.call_args.kwargs['on_status_callback']

        # Simulate status update from connection
        client_status_callback('connected', {'message': 'test'})

        # User callback should be invoked with enhanced data
        assert status_callback.called
        call_args = status_callback.call_args
        assert call_args[0][0] == 'connected'
        assert 'connection_id' in call_args[0][1]


class TestMultiConnectionManagerSubscription:
    """Test ticker subscription and routing."""

    @patch('src.infrastructure.websocket.multi_connection_manager.MassiveWebSocketClient')
    def test_subscribe_to_connected_client(self, mock_client_class):
        """Test subscribing additional tickers."""
        mock_client = Mock()
        mock_client.connect.return_value = True
        mock_client_class.return_value = mock_client

        config = {
            'USE_MULTI_CONNECTION': True,
            'MASSIVE_API_KEY': 'test_key',
            'WEBSOCKET_CONNECTION_1_ENABLED': True,
            'WEBSOCKET_CONNECTION_1_SYMBOLS': 'AAPL',
            'WEBSOCKET_CONNECTION_2_ENABLED': False,
            'WEBSOCKET_CONNECTION_3_ENABLED': False
        }

        manager = MultiConnectionManager(config, Mock(), Mock())
        manager.connect()

        result = manager.subscribe(['TSLA', 'NVDA'])

        assert result is True
        # Check that subscribe was called (initial + additional)
        assert mock_client.subscribe.call_count >= 2

    def test_subscribe_no_connected_clients(self):
        """Test subscribe when no clients connected."""
        config = {
            'USE_MULTI_CONNECTION': True,
            'MASSIVE_API_KEY': 'test_key',
            'WEBSOCKET_CONNECTION_1_ENABLED': False,
            'WEBSOCKET_CONNECTION_2_ENABLED': False,
            'WEBSOCKET_CONNECTION_3_ENABLED': False
        }

        manager = MultiConnectionManager(config, Mock(), Mock())
        result = manager.subscribe(['AAPL'])

        assert result is False


class TestMultiConnectionManagerHealth:
    """Test health monitoring."""

    def test_get_health_status_no_connections(self):
        """Test health status with no connections."""
        config = {
            'USE_MULTI_CONNECTION': True,
            'MASSIVE_API_KEY': 'test_key',
            'WEBSOCKET_CONNECTION_1_ENABLED': False,
            'WEBSOCKET_CONNECTION_2_ENABLED': False,
            'WEBSOCKET_CONNECTION_3_ENABLED': False
        }

        manager = MultiConnectionManager(config, Mock(), Mock())
        health = manager.get_health_status()

        assert health['total_connections'] == 0
        assert health['connected_count'] == 0
        assert health['total_ticks_received'] == 0

    @patch('src.infrastructure.websocket.multi_connection_manager.MassiveWebSocketClient')
    def test_get_health_status_with_connections(self, mock_client_class):
        """Test health status with active connections."""
        mock_client = Mock()
        mock_client.connect.return_value = True
        mock_client_class.return_value = mock_client

        config = {
            'USE_MULTI_CONNECTION': True,
            'MASSIVE_API_KEY': 'test_key',
            'WEBSOCKET_CONNECTION_1_ENABLED': True,
            'WEBSOCKET_CONNECTION_1_SYMBOLS': 'AAPL,NVDA',
            'WEBSOCKET_CONNECTION_2_ENABLED': False,
            'WEBSOCKET_CONNECTION_3_ENABLED': False
        }

        manager = MultiConnectionManager(config, Mock(), Mock())
        manager.connect()

        health = manager.get_health_status()

        assert health['total_connections'] == 1
        assert health['connected_count'] == 1
        assert 'connection_1' in health['connections']
        assert health['connections']['connection_1']['assigned_tickers'] == 2
