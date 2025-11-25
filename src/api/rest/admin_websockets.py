"""
Admin WebSocket Connections Monitoring Dashboard

Provides real-time monitoring of multi-connection WebSocket architecture.
Displays status, configuration, and live tick data for all three WebSocket connections.

Routes:
    - GET /admin/websockets: Dashboard page (admin only)
    - GET /api/admin/websocket-status: Connection status API (admin only)

WebSocket Namespace:
    - /admin-ws: Real-time updates for admin dashboard (admin only)
"""

import json
import logging
import threading
import time

import redis
from flask import Blueprint, jsonify, render_template
from flask import request as flask_request
from flask_login import current_user, login_required
from flask_socketio import Namespace, emit, join_room, leave_room

from src.app import market_service, socketio
from src.utils.auth_decorators import admin_required

logger = logging.getLogger(__name__)

# Flask Blueprint for admin WebSocket routes
admin_websockets_bp = Blueprint("admin_websockets", __name__, url_prefix="/admin")


@admin_websockets_bp.route("/websockets")
@login_required
@admin_required
def websockets_dashboard():
    """
    Render WebSocket monitoring dashboard.

    Admin users only - displays real-time connection status for all three
    WebSocket connections, including live tick streams and metrics.

    Returns:
        HTML template rendering
    """
    logger.info(f"Admin user {current_user.email} accessing WebSocket dashboard")
    return render_template("admin/websockets_monitor.html")


@admin_websockets_bp.route("/api/admin/websocket-status")
@login_required
@admin_required
def get_websocket_status():
    """
    Get real-time WebSocket connection status and metrics.

    Returns JSON with connection health status from MultiConnectionManager.
    All data is in-memory (no database queries) for <50ms response time.

    Returns:
        JSON response:
        {
            "status": "success",
            "data": {
                "total_connections": int,
                "connected_count": int,
                "total_ticks_received": int,
                "total_errors": int,
                "connections": {
                    "connection_1": {...},
                    "connection_2": {...},
                    "connection_3": {...}
                }
            },
            "timestamp": float
        }
    """
    try:
        # Access MultiConnectionManager via market_service global
        # CRITICAL: market_service is defined in src/app.py line 79
        client = market_service.data_adapter.client

        # Get health status (all in-memory, <50ms)
        health = client.get_health_status()

        return jsonify({"status": "success", "data": health, "timestamp": time.time()})

    except AttributeError as e:
        # Handle case where MultiConnectionManager not available
        logger.error(f"MultiConnectionManager not available: {e}")
        return jsonify(
            {"status": "error", "message": "WebSocket connection manager not available"}
        ), 500

    except Exception as e:
        logger.error(f"Error fetching WebSocket status: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


class AdminWebSocketNamespace(Namespace):
    """
    Admin monitoring namespace at /admin-ws.

    Provides real-time WebSocket connection status and tick data to admin dashboard.
    Admin users only - non-admin connections rejected.

    Events (Client → Server):
        - request_metrics: Client requests current metrics

    Events (Server → Client):
        - connection_status_update: Full connection health status
        - tick_update: Real-time tick with connection_id added
        - metrics_update: Periodic metrics (every 5 seconds)
    """

    def __init__(self, namespace):
        super().__init__(namespace)

        # Redis client for tick subscription
        self.redis_client = redis.Redis(
            host="localhost",
            port=6379,
            db=0,
            decode_responses=True,  # Auto UTF-8 decoding
        )

        # Background threads (started on first client connect)
        self.redis_subscriber_thread = None
        self.metrics_broadcaster_thread = None

        # Thread control
        self.active_clients = 0
        self._lock = threading.Lock()

    def on_connect(self):
        """
        Handle admin connection.

        CRITICAL: Reject non-admin users (return False).
        Join room for admin broadcasts and send initial status.

        Returns:
            bool: True to accept connection, False to reject
        """
        # CRITICAL: Check authentication AND admin role
        if not current_user.is_authenticated:
            logger.warning("Unauthenticated user attempted /admin-ws connection")
            return False  # Reject connection

        if not current_user.is_admin():
            logger.warning(f"Non-admin user {current_user.email} attempted /admin-ws connection")
            return False  # Reject connection

        # Join admin monitoring room
        join_room("admin_monitoring")
        logger.info(f"Admin user {current_user.email} connected to /admin-ws")

        # Track active clients
        with self._lock:
            self.active_clients += 1
            first_client = self.active_clients == 1

        # Start background threads on first client
        if first_client:
            self._start_background_threads()

        # Send initial status to connecting client
        try:
            client = market_service.data_adapter.client
            health = client.get_health_status()

            # PATTERN: emit to specific session (to=request.sid)
            emit("connection_status_update", health, to=flask_request.sid)
        except Exception as e:
            logger.error(f"Error sending initial status: {e}")

        return True  # Accept connection

    def on_disconnect(self):
        """
        Handle admin disconnection and cleanup.
        """
        leave_room("admin_monitoring")

        with self._lock:
            self.active_clients -= 1

        logger.info(f"Admin user disconnected from /admin-ws ({self.active_clients} remaining)")

    def on_request_metrics(self, data):
        """
        Handle metrics request from admin client.

        Responds with current connection status and metrics.

        Args:
            data: Request data (unused, but required by event signature)
        """
        try:
            client = market_service.data_adapter.client
            health = client.get_health_status()

            # PATTERN: Reply only to requester (to=request.sid)
            emit("metrics_update", health, to=flask_request.sid)

        except Exception as e:
            logger.error(f"Error handling metrics request: {e}")
            emit("error", {"message": "Failed to fetch metrics"}, to=flask_request.sid)

    def _start_background_threads(self):
        """
        Start background threads for Redis subscription and metrics broadcasting.

        Called when first admin client connects.
        """
        # Start Redis tick subscriber
        if self.redis_subscriber_thread is None or not self.redis_subscriber_thread.is_alive():
            self.redis_subscriber_thread = threading.Thread(
                target=self._subscribe_to_ticks, daemon=True
            )
            self.redis_subscriber_thread.start()
            logger.info("Started Redis tick subscriber thread")

        # Start metrics broadcaster
        if (
            self.metrics_broadcaster_thread is None
            or not self.metrics_broadcaster_thread.is_alive()
        ):
            self.metrics_broadcaster_thread = threading.Thread(
                target=self._broadcast_metrics, daemon=True
            )
            self.metrics_broadcaster_thread.start()
            logger.info("Started metrics broadcaster thread")

    def _subscribe_to_ticks(self):
        """
        Background thread: Subscribe to tickstock:market:ticks and forward to clients.

        CRITICAL: Runs in daemon thread (exits when main process exits).
        PATTERN: Add connection_id from MultiConnectionManager.get_ticker_assignment().

        Subscribes to Redis channel and forwards ticks to all admin dashboard clients
        with connection_id enrichment to show which WebSocket connection handled the tick.
        """
        pubsub = self.redis_client.pubsub()
        pubsub.subscribe("tickstock:market:ticks")

        logger.info("Subscribed to tickstock:market:ticks for admin dashboard")

        for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    # Parse JSON tick data
                    tick = json.loads(message["data"])

                    # CRITICAL: Add connection_id from MultiConnectionManager
                    # This tells admin dashboard which connection handled this tick
                    symbol = tick.get("symbol")
                    if symbol:
                        # CRITICAL: Check if market_service is initialized
                        # Avoid errors during startup before service is ready
                        if market_service is not None:
                            try:
                                client = market_service.data_adapter.client
                                connection_id = client.get_ticker_assignment(symbol)
                                tick["connection_id"] = connection_id
                            except AttributeError:
                                # market_service not fully initialized yet
                                # Default to connection_1
                                tick["connection_id"] = "connection_1"
                                logger.debug(
                                    f"market_service.data_adapter not ready, "
                                    f"defaulting to connection_1 for {symbol}"
                                )
                        else:
                            # market_service not available yet
                            # Default to connection_1
                            tick["connection_id"] = "connection_1"
                            logger.debug(
                                f"market_service not initialized, "
                                f"defaulting to connection_1 for {symbol}"
                            )

                    # GOTCHA: Must use socketio.emit() (not self.emit())
                    # from background thread
                    # GOTCHA: Must specify namespace='/admin-ws' explicitly
                    # CRITICAL: Check if socketio is initialized
                    if socketio is not None:
                        socketio.emit(
                            "tick_update", tick, namespace="/admin-ws", room="admin_monitoring"
                        )
                    else:
                        # socketio not ready yet, skip this tick
                        logger.debug("socketio not initialized, skipping tick emission")

                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse tick JSON: {e}")
                except Exception as e:
                    logger.error(f"Error processing tick: {e}")

    def _broadcast_metrics(self):
        """
        Background thread: Broadcast metrics every 5 seconds.

        PATTERN: Periodic updates to keep dashboard current.
        Sends connection health status and calculated metrics to all admin clients.
        """
        while True:
            try:
                time.sleep(5)  # Update every 5 seconds

                # Skip if no clients watching
                with self._lock:
                    if self.active_clients == 0:
                        continue

                # Fetch current metrics
                # CRITICAL: Check if market_service is initialized
                if market_service is None:
                    logger.debug("market_service not initialized, skipping metrics broadcast")
                    continue

                try:
                    client = market_service.data_adapter.client
                    health = client.get_health_status()
                except AttributeError:
                    logger.debug(
                        "market_service.data_adapter not ready, skipping metrics broadcast"
                    )
                    continue

                # Calculate messages per second for each connection
                metrics = {}
                connections = health.get("connections", {})
                for conn_id, conn_data in connections.items():
                    msg_count = conn_data.get("message_count", 0)
                    # Simple rate calculation
                    # (could be smoothed with moving average)
                    metrics[conn_id] = {
                        "message_count": msg_count,
                        "messages_per_second": round(msg_count / 5, 1),
                        "error_count": conn_data.get("error_count", 0),
                        "status": conn_data.get("status", "unknown"),
                    }

                # Broadcast to all admin clients
                # CRITICAL: Check if socketio is initialized
                if socketio is not None:
                    socketio.emit(
                        "metrics_update", metrics, namespace="/admin-ws", room="admin_monitoring"
                    )
                else:
                    logger.debug("socketio not initialized, skipping metrics broadcast")

            except Exception as e:
                logger.error(f"Error broadcasting metrics: {e}")
                time.sleep(5)  # Continue even on error
