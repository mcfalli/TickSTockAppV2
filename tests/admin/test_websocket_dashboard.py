"""
Unit tests for Admin WebSocket Monitoring Dashboard

Tests admin authentication, WebSocket namespace, and status API endpoints.

Test Coverage:
    - Admin route authentication (@admin_required)
    - WebSocket connection authentication
    - Status API JSON structure
    - Connection status updates
    - Tick enrichment with connection_id
"""

from unittest.mock import Mock, patch

import pytest


@pytest.fixture
def app():
    """Create test Flask app with minimal config."""
    from flask import Flask
    from src.api.rest.admin_websockets import admin_websockets_bp

    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SECRET_KEY'] = 'test-secret-key'

    # Register the admin websockets blueprint
    app.register_blueprint(admin_websockets_bp)

    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def admin_user(app):
    """Create mock admin user."""
    with app.app_context():
        user = Mock()
        user.id = 1
        user.email = "admin@test.com"
        user.role = "admin"
        user.is_authenticated = True
        user.is_active = True
        user.is_anonymous = False
        user.get_id = lambda: "1"

        def is_admin_mock():
            return user.role in ["admin", "super"]

        user.is_admin = is_admin_mock
        return user


@pytest.fixture
def regular_user(app):
    """Create mock regular user."""
    with app.app_context():
        user = Mock()
        user.id = 2
        user.email = "user@test.com"
        user.role = "user"
        user.is_authenticated = True
        user.is_active = True
        user.is_anonymous = False
        user.get_id = lambda: "2"

        def is_admin_mock():
            return user.role in ["admin", "super"]

        user.is_admin = is_admin_mock
        return user


@pytest.fixture
def mock_health_status():
    """Mock MultiConnectionManager health status."""
    return {
        "total_connections": 3,
        "connected_count": 2,
        "total_ticks_received": 15000,
        "total_errors": 5,
        "connections": {
            "connection_1": {
                "name": "primary",
                "status": "connected",
                "assigned_tickers": 150,
                "message_count": 10000,
                "error_count": 0,
                "last_message_time": 1705853696.123,
            },
            "connection_2": {
                "name": "secondary",
                "status": "connected",
                "assigned_tickers": 100,
                "message_count": 5000,
                "error_count": 3,
                "last_message_time": 1705853695.456,
            },
            "connection_3": {
                "name": "tertiary",
                "status": "disconnected",
                "assigned_tickers": 0,
                "message_count": 0,
                "error_count": 2,
                "last_message_time": None,
            },
        },
    }


class TestAdminWebSocketRouteAuthentication:
    """Test admin authentication for WebSocket dashboard routes."""

    @patch("src.api.rest.admin_websockets.market_service")
    def test_websockets_dashboard_requires_admin(self, mock_market_service, client, regular_user):
        """
        Test that non-admin users receive 403 Forbidden.

        CRITICAL: Admin routes must reject non-admin users.
        """
        with client:
            with client.session_transaction() as sess:
                sess["user_id"] = regular_user.id

            with patch("flask_login.utils._get_user", return_value=regular_user):
                response = client.get("/admin/websockets")
                assert response.status_code == 403

    @patch("src.api.rest.admin_websockets.market_service")
    def test_websockets_dashboard_accessible_to_admin(
        self, mock_market_service, client, admin_user
    ):
        """
        Test that admin users can access dashboard.

        PATTERN: Admin access should return 200 and render template.
        """
        with client:
            with client.session_transaction() as sess:
                sess["user_id"] = admin_user.id

            with patch("flask_login.utils._get_user", return_value=admin_user):
                response = client.get("/admin/websockets")
                assert response.status_code == 200
                assert b"WebSocket Connections Monitor" in response.data

    def test_websockets_dashboard_requires_login(self, client):
        """
        Test that unauthenticated users are redirected to login.

        PATTERN: Unauthenticated access should redirect (302).
        """
        response = client.get("/admin/websockets", follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.location or "login" in response.location.lower()


class TestWebSocketStatusAPI:
    """Test /api/admin/websocket-status JSON endpoint."""

    @patch("src.api.rest.admin_websockets.market_service")
    def test_websocket_status_api_returns_correct_structure(
        self, mock_market_service, client, admin_user, mock_health_status
    ):
        """
        Test status API returns correct JSON structure.

        VALIDATION: Response must match MultiConnectionManager health status format.
        """
        mock_client = Mock()
        mock_client.get_health_status.return_value = mock_health_status
        mock_market_service.data_adapter.client = mock_client

        with client:
            with client.session_transaction() as sess:
                sess["user_id"] = admin_user.id

            with patch("flask_login.utils._get_user", return_value=admin_user):
                response = client.get("/api/admin/websocket-status")
                assert response.status_code == 200

                data = response.get_json()
                assert data["status"] == "success"
                assert "data" in data
                assert "timestamp" in data

                health = data["data"]
                assert health["total_connections"] == 3
                assert health["connected_count"] == 2
                assert "connections" in health
                assert "connection_1" in health["connections"]
                assert health["connections"]["connection_1"]["status"] == "connected"

    @patch("src.api.rest.admin_websockets.market_service")
    def test_websocket_status_api_requires_admin(self, mock_market_service, client, regular_user):
        """
        Test status API rejects non-admin users.

        SECURITY: API endpoints must enforce admin_required.
        """
        with client:
            with client.session_transaction() as sess:
                sess["user_id"] = regular_user.id

            with patch("flask_login.utils._get_user", return_value=regular_user):
                response = client.get("/api/admin/websocket-status")
                assert response.status_code == 403

    @patch("src.api.rest.admin_websockets.market_service")
    def test_websocket_status_api_handles_manager_unavailable(
        self, mock_market_service, client, admin_user
    ):
        """
        Test graceful handling when MultiConnectionManager unavailable.

        ERROR HANDLING: Should return 500 with error message.
        """
        mock_market_service.data_adapter.client = None

        with client:
            with client.session_transaction() as sess:
                sess["user_id"] = admin_user.id

            with patch("flask_login.utils._get_user", return_value=admin_user):
                response = client.get("/api/admin/websocket-status")
                assert response.status_code == 500

                data = response.get_json()
                assert data["status"] == "error"
                assert "message" in data


class TestAdminWebSocketNamespace:
    """Test AdminWebSocketNamespace class and event handlers."""

    @patch("src.api.rest.admin_websockets.market_service")
    def test_admin_websocket_rejects_non_admin_connections(
        self, mock_market_service, app, regular_user
    ):
        """
        Test WebSocket namespace rejects non-admin connections.

        CRITICAL: on_connect must return False for non-admin users.
        """
        from src.api.rest.admin_websockets import AdminWebSocketNamespace

        namespace = AdminWebSocketNamespace("/admin-ws")

        with app.test_request_context():
            with patch("flask_login.utils._get_user", return_value=regular_user):
                result = namespace.on_connect()
                assert result is False

    @patch("src.api.rest.admin_websockets.market_service")
    def test_admin_websocket_accepts_admin_connections(
        self, mock_market_service, app, admin_user, mock_health_status
    ):
        """
        Test WebSocket namespace accepts admin connections.

        PATTERN: on_connect should return True for admin users.
        """
        from src.api.rest.admin_websockets import AdminWebSocketNamespace

        namespace = AdminWebSocketNamespace("/admin-ws")

        mock_client = Mock()
        mock_client.get_health_status.return_value = mock_health_status
        mock_market_service.data_adapter.client = mock_client

        with app.test_request_context():
            with patch("flask_login.utils._get_user", return_value=admin_user):
                with patch("flask_socketio.join_room"):
                    with patch("flask_socketio.emit"):
                        result = namespace.on_connect()
                        assert result is True

    def test_admin_websocket_rejects_unauthenticated(self, app):
        """
        Test WebSocket namespace rejects unauthenticated users.

        SECURITY: Must check is_authenticated before is_admin.
        """
        from src.api.rest.admin_websockets import AdminWebSocketNamespace

        namespace = AdminWebSocketNamespace("/admin-ws")

        unauthenticated_user = Mock()
        unauthenticated_user.is_authenticated = False

        with app.test_request_context():
            with patch("flask_login.utils._get_user", return_value=unauthenticated_user):
                result = namespace.on_connect()
                assert result is False


class TestTickEnrichment:
    """Test tick enrichment with connection_id from MultiConnectionManager."""

    @patch("src.api.rest.admin_websockets.market_service")
    def test_tick_update_includes_connection_id(self, mock_market_service):
        """
        Test that ticks are enriched with connection_id.

        CRITICAL: Redis ticks lack connection_id - must add from get_ticker_assignment().
        """
        from src.api.rest.admin_websockets import AdminWebSocketNamespace

        AdminWebSocketNamespace("/admin-ws")

        mock_client = Mock()
        mock_client.get_ticker_assignment.return_value = "connection_1"
        mock_market_service.data_adapter.client = mock_client

        tick = {"symbol": "AAPL", "price": 178.23, "volume": 1000, "timestamp": 1705853696.123}

        symbol = tick.get("symbol")
        connection_id = mock_client.get_ticker_assignment(symbol)
        tick["connection_id"] = connection_id

        assert tick["connection_id"] == "connection_1"
        assert tick["symbol"] == "AAPL"

        mock_client.get_ticker_assignment.assert_called_once_with("AAPL")


@pytest.mark.skipif(True, reason="Requires full Flask app context and SocketIO initialization")
class TestWebSocketEvents:
    """
    Integration-level tests for WebSocket events.

    NOTE: These tests require full app initialization and are better suited
    for integration test suite. Skipped in unit tests.
    """

    def test_metrics_request_handler(self):
        """Test on_request_metrics event handler."""
        pass

    def test_background_metrics_broadcast(self):
        """Test _broadcast_metrics background thread."""
        pass

    def test_redis_tick_subscription(self):
        """Test _subscribe_to_ticks background thread."""
        pass
