"""
Multi-connection WebSocket manager for Massive API.

Manages up to 3 concurrent WebSocket connections with independent ticker subscriptions.
Provides unified interface compatible with MassiveWebSocketClient (drop-in replacement).

Sprint 51: Multi-Connection WebSocket Support
"""

import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from src.presentation.websocket.massive_client import MassiveWebSocketClient

logger = logging.getLogger(__name__)


@dataclass
class ConnectionInfo:
    """Information about a WebSocket connection."""

    connection_id: str
    name: str
    client: MassiveWebSocketClient | None = None
    assigned_tickers: set[str] = field(default_factory=set)
    status: str = "disconnected"  # disconnected, connecting, connected, error
    message_count: int = 0
    error_count: int = 0
    last_message_time: float = 0.0


class MultiConnectionManager:
    """
    Manages multiple Massive API WebSocket connections.

    Drop-in replacement for MassiveWebSocketClient with same interface:
    - connect() -> bool
    - disconnect() -> None
    - subscribe(tickers) -> bool
    - Callbacks: on_tick_callback(TickData), on_status_callback(status, data)

    Features:
    - Up to 3 concurrent connections (Massive API limit)
    - Ticker routing via universe keys or direct symbol lists
    - Aggregated callbacks (all connections -> unified callback)
    - Health monitoring and failover
    """

    def __init__(
        self,
        config: dict,
        on_tick_callback: Callable,
        on_status_callback: Callable,
        max_connections: int = 3,
    ):
        """
        Initialize multi-connection manager using ConfigManager settings.

        Args:
            config: Application configuration (from ConfigManager)
            on_tick_callback: Callback for tick data (aggregated from all connections)
            on_status_callback: Callback for status updates (aggregated)
            max_connections: Maximum number of connections (default: 3)
        """
        self.config = config
        self.max_connections = max_connections
        self.api_key = config.get("MASSIVE_API_KEY")

        # Validate multi-connection is enabled
        if not config.get("USE_MULTI_CONNECTION", False):
            logger.warning("MULTI-CONNECTION-MANAGER: Multi-connection mode disabled in config")

        # Connection management
        self.connections: dict[str, ConnectionInfo] = {}
        self.ticker_to_connection: dict[str, str] = {}  # ticker -> connection_id

        # Callbacks (from RealTimeDataAdapter)
        self._user_tick_callback = on_tick_callback
        self._user_status_callback = on_status_callback

        # Thread safety (for callback aggregation)
        self._lock = threading.RLock()

        # Statistics
        self.total_ticks_received = 0
        self.total_errors = 0

        # Load and initialize enabled connections
        self._initialize_configured_connections()

        logger.info(
            f"MULTI-CONNECTION-MANAGER: Initialized with max {max_connections} connections, "
            f"{len(self.connections)} connections configured"
        )

    def _initialize_configured_connections(self):
        """Initialize connections based on config settings."""
        for conn_num in range(1, self.max_connections + 1):
            enabled_key = f"WEBSOCKET_CONNECTION_{conn_num}_ENABLED"
            name_key = f"WEBSOCKET_CONNECTION_{conn_num}_NAME"

            if self.config.get(enabled_key, False):
                connection_id = f"connection_{conn_num}"
                connection_name = self.config.get(name_key, connection_id)

                # Load tickers for this connection
                tickers = self._load_tickers_for_connection(conn_num)

                if tickers:
                    logger.info(
                        f"MULTI-CONNECTION: Connection {conn_num} ({connection_name}) "
                        f"configured with {len(tickers)} tickers"
                    )
                    # Store configuration (actual connection created in connect())
                    self.connections[connection_id] = ConnectionInfo(
                        connection_id=connection_id,
                        name=connection_name,
                        assigned_tickers=set(tickers),
                    )

                    # Track ticker assignments
                    for ticker in tickers:
                        self.ticker_to_connection[ticker] = connection_id
                else:
                    logger.warning(
                        f"MULTI-CONNECTION: Connection {conn_num} enabled but no tickers configured"
                    )

    def _load_tickers_for_connection(self, connection_num: int) -> list[str]:
        """
        Load ticker list for a connection using SYMBOL_UNIVERSE_KEY approach.

        Follows existing pattern from market_data_service.py:151-178

        Args:
            connection_num: Connection number (1, 2, or 3)

        Returns:
            List of ticker symbols
        """
        # Get universe key from config
        universe_key_config = f"WEBSOCKET_CONNECTION_{connection_num}_UNIVERSE_KEY"
        symbols_config = f"WEBSOCKET_CONNECTION_{connection_num}_SYMBOLS"

        universe_key = self.config.get(universe_key_config, "").strip()
        direct_symbols = self.config.get(symbols_config, "").strip()

        # TRY UNIVERSE KEY FIRST (Preferred Method)
        if universe_key:
            try:
                logger.info(
                    f"MULTI-CONNECTION: Loading tickers for connection {connection_num} "
                    f"from universe: {universe_key}"
                )

                # Sprint 61: Use RelationshipCache instead of CacheControl
                # Supports multi-universe join (e.g., 'sp500:nasdaq100')
                from src.core.services.relationship_cache import get_relationship_cache

                cache = get_relationship_cache()

                # Get tickers from cache (supports multi-universe join with colon separator)
                universe_tickers = cache.get_universe_symbols(universe_key)

                if universe_tickers and len(universe_tickers) > 0:
                    logger.info(
                        f"MULTI-CONNECTION: connection_{connection_num} loaded {len(universe_tickers)} tickers "
                        f"from universe '{universe_key}': "
                        f"{', '.join(universe_tickers[:5])}{'...' if len(universe_tickers) > 5 else ''}"
                    )
                    return universe_tickers
                logger.warning(
                    f"MULTI-CONNECTION: Universe '{universe_key}' not found or empty "
                    f"for connection {connection_num}, trying direct symbols"
                )
            except Exception as e:
                logger.error(
                    f"MULTI-CONNECTION: Error loading universe '{universe_key}': {e}", exc_info=True
                )

        # FALLBACK TO DIRECT SYMBOL LIST
        if direct_symbols:
            tickers = [s.strip() for s in direct_symbols.split(",") if s.strip()]
            logger.info(
                f"MULTI-CONNECTION: connection_{connection_num} using direct symbols: "
                f"{len(tickers)} tickers configured"
            )
            return tickers

        # No configuration found
        logger.warning(
            f"MULTI-CONNECTION: No universe key or symbols configured for connection {connection_num}"
        )
        return []

    def connect(self) -> bool:
        """
        Connect all configured connections.

        Compatible with MassiveWebSocketClient.connect() interface.

        Returns:
            True if at least one connection succeeds, False if all fail
        """
        if not self.connections:
            logger.error("MULTI-CONNECTION-MANAGER: No connections configured")
            return False

        success_count = 0

        for connection_id, conn_info in self.connections.items():
            try:
                logger.info(f"MULTI-CONNECTION: Connecting {connection_id} ({conn_info.name})")

                # Create MassiveWebSocketClient for this connection
                client = MassiveWebSocketClient(
                    api_key=self.api_key,
                    # WRAP CALLBACKS - Add connection_id parameter
                    on_tick_callback=lambda tick, cid=connection_id: self._aggregate_tick_callback(
                        tick, cid
                    ),
                    on_status_callback=lambda status,
                    data,
                    cid=connection_id: self._aggregate_status_callback(status, data, cid),
                    config=self.config,
                )

                # Attempt connection
                conn_info.client = client
                conn_info.status = "connecting"

                if client.connect():
                    conn_info.status = "connected"

                    # Subscribe to assigned tickers
                    if conn_info.assigned_tickers:
                        client.subscribe(list(conn_info.assigned_tickers))
                        logger.info(
                            f"MULTI-CONNECTION: {connection_id} connected and subscribed to "
                            f"{len(conn_info.assigned_tickers)} tickers"
                        )

                    success_count += 1
                else:
                    conn_info.status = "error"
                    logger.error(f"MULTI-CONNECTION: {connection_id} connection failed")

            except Exception as e:
                conn_info.status = "error"
                conn_info.error_count += 1
                logger.error(
                    f"MULTI-CONNECTION: Error connecting {connection_id}: {e}", exc_info=True
                )

        # Success if at least one connection established
        if success_count > 0:
            logger.info(
                f"MULTI-CONNECTION-MANAGER: {success_count}/{len(self.connections)} connections established"
            )
            return True
        logger.error("MULTI-CONNECTION-MANAGER: All connections failed")
        return False

    def disconnect(self):
        """
        Disconnect all connections.

        Compatible with MassiveWebSocketClient.disconnect() interface.
        """
        logger.info("MULTI-CONNECTION-MANAGER: Disconnecting all connections")

        for connection_id, conn_info in self.connections.items():
            if conn_info.client:
                try:
                    conn_info.client.disconnect()
                    conn_info.status = "disconnected"
                    logger.info(f"MULTI-CONNECTION: {connection_id} disconnected")
                except Exception as e:
                    logger.error(f"MULTI-CONNECTION: Error disconnecting {connection_id}: {e}")

    def subscribe(self, tickers: list[str]) -> bool:
        """
        Subscribe to additional tickers (routes across connections).

        Compatible with MassiveWebSocketClient.subscribe() interface.

        Args:
            tickers: List of ticker symbols

        Returns:
            True if at least one subscription succeeds
        """
        # For now, simple strategy: Add to first available connection
        # TODO: Implement routing strategy (round-robin, load-balanced, etc.)

        if not self.connections:
            logger.error("MULTI-CONNECTION-MANAGER: No connections available")
            return False

        # Use first connected client
        for conn_info in self.connections.values():
            if conn_info.status == "connected" and conn_info.client:
                try:
                    conn_info.client.subscribe(tickers)
                    conn_info.assigned_tickers.update(tickers)

                    # Track ticker assignments
                    for ticker in tickers:
                        self.ticker_to_connection[ticker] = conn_info.connection_id

                    logger.info(
                        f"MULTI-CONNECTION: Added {len(tickers)} tickers to {conn_info.connection_id}"
                    )
                    return True
                except Exception as e:
                    logger.error(
                        f"MULTI-CONNECTION: Error subscribing to tickers on {conn_info.connection_id}: {e}"
                    )

        logger.error("MULTI-CONNECTION-MANAGER: No connected clients available for subscription")
        return False

    def _aggregate_tick_callback(self, tick_data, connection_id: str):
        """
        Internal callback that aggregates ticks from all connections.

        Args:
            tick_data: TickData object from MassiveWebSocketClient
            connection_id: Source connection ID
        """
        with self._lock:
            # Update statistics
            self.total_ticks_received += 1

            # Update connection-specific stats
            if connection_id in self.connections:
                conn_info = self.connections[connection_id]
                conn_info.message_count += 1
                conn_info.last_message_time = time.time()

        # Forward to user callback (outside lock to avoid blocking)
        try:
            self._user_tick_callback(tick_data)
        except Exception as e:
            logger.error(
                f"MULTI-CONNECTION: Error in user tick callback from {connection_id}: {e}",
                exc_info=True,
            )
            self.total_errors += 1

    def _aggregate_status_callback(self, status: str, data: dict, connection_id: str):
        """
        Internal callback that aggregates status updates from all connections.

        Args:
            status: Status string (e.g., 'connected', 'disconnected', 'error')
            data: Additional status data
            connection_id: Source connection ID
        """
        with self._lock:
            # Update connection status
            if connection_id in self.connections:
                conn_info = self.connections[connection_id]
                conn_info.status = status

                if status == "error":
                    conn_info.error_count += 1
                    self.total_errors += 1

        # Forward to user callback with connection info
        try:
            # Enhance data with connection_id
            enhanced_data = data.copy() if data else {}
            enhanced_data["connection_id"] = connection_id

            self._user_status_callback(status, enhanced_data)
        except Exception as e:
            logger.error(
                f"MULTI-CONNECTION: Error in user status callback from {connection_id}: {e}",
                exc_info=True,
            )

    def get_health_status(self) -> dict:
        """
        Get health status of all connections.

        Returns:
            Dictionary with connection health information
        """
        with self._lock:
            return {
                "total_connections": len(self.connections),
                "connected_count": sum(
                    1 for c in self.connections.values() if c.status == "connected"
                ),
                "total_ticks_received": self.total_ticks_received,
                "total_errors": self.total_errors,
                "connections": {
                    cid: {
                        "name": info.name,
                        "status": info.status,
                        "assigned_tickers": len(info.assigned_tickers),
                        "message_count": info.message_count,
                        "error_count": info.error_count,
                        "last_message_time": info.last_message_time,
                    }
                    for cid, info in self.connections.items()
                },
            }

    def unsubscribe(self, tickers: list[str]) -> bool:
        """
        Unsubscribe from tickers.

        Args:
            tickers: List of ticker symbols to unsubscribe

        Returns:
            True if at least one unsubscription succeeds
        """
        if not self.connections:
            logger.error("MULTI-CONNECTION-MANAGER: No connections available")
            return False

        success = False

        for ticker in tickers:
            # Find which connection has this ticker
            connection_id = self.ticker_to_connection.get(ticker)

            if connection_id and connection_id in self.connections:
                conn_info = self.connections[connection_id]

                if conn_info.client and conn_info.status == "connected":
                    try:
                        conn_info.client.unsubscribe([ticker])
                        conn_info.assigned_tickers.discard(ticker)
                        del self.ticker_to_connection[ticker]
                        success = True
                        logger.info(f"MULTI-CONNECTION: Unsubscribed {ticker} from {connection_id}")
                    except Exception as e:
                        logger.error(
                            f"MULTI-CONNECTION: Error unsubscribing {ticker} from {connection_id}: {e}"
                        )

        return success

    def get_ticker_assignment(self, ticker: str) -> str | None:
        """
        Get which connection a ticker is assigned to.

        Args:
            ticker: Ticker symbol

        Returns:
            Connection ID or None if not assigned
        """
        return self.ticker_to_connection.get(ticker)

    def get_connection_tickers(self, connection_id: str) -> set[str]:
        """
        Get all tickers assigned to a specific connection.

        Args:
            connection_id: Connection identifier

        Returns:
            Set of ticker symbols
        """
        if connection_id in self.connections:
            return self.connections[connection_id].assigned_tickers.copy()
        return set()
