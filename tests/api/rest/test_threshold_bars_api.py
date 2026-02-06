"""Sprint 64: Threshold Bars API Tests

Test coverage for /api/threshold-bars endpoint including:
- Request parameter validation
- Authentication requirements
- Success responses with valid data
- Error handling for invalid parameters
- Error handling for service failures
- Response structure validation
"""

import json
from unittest.mock import Mock, patch

import pytest
from flask import Flask

from src.api.rest.threshold_bars import threshold_bars_bp


class TestThresholdBarsAPIRegistration:
    """Test API registration and blueprint setup."""

    def test_blueprint_registration(self):
        """Test that threshold_bars blueprint can be registered."""
        app = Flask(__name__)
        app.config["TESTING"] = True

        app.register_blueprint(threshold_bars_bp)

        # Verify blueprint is registered
        assert "threshold_bars" in [bp.name for bp in app.blueprints.values()]

    def test_blueprint_has_routes(self):
        """Test that blueprint has expected routes."""
        # Check that blueprint has deferred functions (routes)
        assert len(threshold_bars_bp.deferred_functions) > 0


class TestThresholdBarsAPIEndpoint:
    """Test /api/threshold-bars endpoint functionality."""

    @pytest.fixture
    def app(self):
        """Create Flask app with threshold_bars blueprint registered."""
        app = Flask(__name__)
        app.config["TESTING"] = True
        app.config["SECRET_KEY"] = "test-secret-key"

        app.register_blueprint(threshold_bars_bp)

        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()

    def test_successful_diverging_threshold_bar_calculation(self, client):
        """Test successful threshold bar calculation with valid parameters."""
        with (
            patch("src.api.rest.threshold_bars.ThresholdBarService") as mock_service_class,
        ):
            # Mock service response
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.calculate_threshold_bars.return_value = {
                "metadata": {
                    "data_source": "sp500",
                    "bar_type": "DivergingThresholdBar",
                    "timeframe": "daily",
                    "threshold": 0.10,
                    "period_days": 1,
                    "symbol_count": 100,
                    "calculated_at": "2025-12-28T10:00:00",
                },
                "segments": {
                    "significant_decline": 15.0,
                    "minor_decline": 35.0,
                    "minor_advance": 30.0,
                    "significant_advance": 20.0,
                },
            }

            response = client.get(
                "/api/threshold-bars"
                "?data_source=sp500"
                "&bar_type=DivergingThresholdBar"
                "&timeframe=daily"
                "&threshold=0.10"
                "&period_days=1"
            )

            assert response.status_code == 200
            assert response.content_type == "application/json"

            data = json.loads(response.data)
            assert data["metadata"]["data_source"] == "sp500"
            assert data["metadata"]["bar_type"] == "DivergingThresholdBar"
            assert data["metadata"]["symbol_count"] == 100
            assert "segments" in data
            assert len(data["segments"]) == 4

            # Verify service was called with correct parameters
            mock_service.calculate_threshold_bars.assert_called_once_with(
                data_source="sp500",
                bar_type="DivergingThresholdBar",
                timeframe="daily",
                threshold=0.10,
                period_days=1,
            )

    def test_successful_simple_diverging_bar_calculation(self, client):
        """Test successful calculation for SimpleDivergingBar."""
        with patch("src.api.rest.threshold_bars.ThresholdBarService") as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.calculate_threshold_bars.return_value = {
                "metadata": {
                    "data_source": "nasdaq100",
                    "bar_type": "SimpleDivergingBar",
                    "timeframe": "weekly",
                    "threshold": 0.10,
                    "period_days": 7,
                    "symbol_count": 102,
                    "calculated_at": "2025-12-28T10:00:00",
                },
                "segments": {"decline": 40.0, "advance": 60.0},
            }

            response = client.get(
                "/api/threshold-bars"
                "?data_source=nasdaq100"
                "&bar_type=SimpleDivergingBar"
                "&timeframe=weekly"
                "&period_days=7"
            )

            assert response.status_code == 200

            data = json.loads(response.data)
            assert data["metadata"]["bar_type"] == "SimpleDivergingBar"
            assert len(data["segments"]) == 2
            assert "decline" in data["segments"]
            assert "advance" in data["segments"]

    def test_default_parameters(self, client):
        """Test that default parameters are applied when not specified."""
        with patch("src.api.rest.threshold_bars.ThresholdBarService") as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.calculate_threshold_bars.return_value = {
                "metadata": {
                    "data_source": "SPY",
                    "bar_type": "DivergingThresholdBar",
                    "timeframe": "daily",
                    "threshold": 0.10,
                    "period_days": 1,
                    "symbol_count": 504,
                    "calculated_at": "2025-12-28T10:00:00",
                },
                "segments": {
                    "significant_decline": 10.0,
                    "minor_decline": 20.0,
                    "minor_advance": 40.0,
                    "significant_advance": 30.0,
                },
            }

            # Only provide data_source, use defaults for others
            response = client.get("/api/threshold-bars?data_source=SPY")

            assert response.status_code == 200

            # Verify defaults were used
            mock_service.calculate_threshold_bars.assert_called_once_with(
                data_source="SPY",
                bar_type="DivergingThresholdBar",  # default
                timeframe="daily",  # default
                threshold=0.10,  # default
                period_days=1,  # default
            )

    def test_missing_required_data_source(self, client):
        """Test error when data_source parameter is missing."""
        response = client.get("/api/threshold-bars")

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["error"] == "ValidationError"
        assert "invalid" in data["message"].lower() or "parameter" in data["message"].lower()

    def test_invalid_timeframe(self, client):
        """Test error for invalid timeframe value."""
        response = client.get("/api/threshold-bars?data_source=sp500&timeframe=invalid")

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["error"] == "ValidationError"

    def test_invalid_threshold_negative(self, client):
        """Test error for negative threshold value."""
        response = client.get("/api/threshold-bars?data_source=sp500&threshold=-0.1")

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["error"] == "ValidationError"

    def test_invalid_threshold_too_large(self, client):
        """Test error for threshold value > 1.0."""
        response = client.get("/api/threshold-bars?data_source=sp500&threshold=1.5")

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["error"] == "ValidationError"

    def test_value_error_from_service(self, client):
        """Test handling of ValueError from service layer."""
        with patch("src.api.rest.threshold_bars.ThresholdBarService") as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.calculate_threshold_bars.side_effect = ValueError("Invalid data_source")

            response = client.get("/api/threshold-bars?data_source=invalid")

            assert response.status_code == 400
            data = json.loads(response.data)
            assert data["error"] == "ValueError"
            assert "Invalid data_source" in data["message"]

    def test_runtime_error_from_service(self, client):
        """Test handling of RuntimeError from service layer."""
        with patch("src.api.rest.threshold_bars.ThresholdBarService") as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.calculate_threshold_bars.side_effect = RuntimeError(
                "No symbols found for data_source: invalid_universe"
            )

            response = client.get("/api/threshold-bars?data_source=invalid_universe")

            assert response.status_code == 500
            data = json.loads(response.data)
            assert data["error"] == "RuntimeError"
            assert "No symbols found" in data["message"]

    def test_unexpected_exception_handling(self, client):
        """Test handling of unexpected exceptions."""
        with patch("src.api.rest.threshold_bars.ThresholdBarService") as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.calculate_threshold_bars.side_effect = Exception("Unexpected error")

            response = client.get("/api/threshold-bars?data_source=sp500")

            assert response.status_code == 500
            data = json.loads(response.data)
            assert data["error"] == "ServerError"
            assert "unexpected error occurred" in data["message"].lower()

    def test_multi_universe_join(self, client):
        """Test threshold bar calculation with multi-universe join."""
        with patch("src.api.rest.threshold_bars.ThresholdBarService") as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.calculate_threshold_bars.return_value = {
                "metadata": {
                    "data_source": "sp500:nasdaq100",
                    "bar_type": "DivergingThresholdBar",
                    "timeframe": "daily",
                    "threshold": 0.15,
                    "period_days": 1,
                    "symbol_count": 518,
                    "calculated_at": "2025-12-28T10:00:00",
                },
                "segments": {
                    "significant_decline": 12.0,
                    "minor_decline": 28.0,
                    "minor_advance": 35.0,
                    "significant_advance": 25.0,
                },
            }

            response = client.get("/api/threshold-bars?data_source=sp500:nasdaq100&threshold=0.15")

            assert response.status_code == 200

            data = json.loads(response.data)
            assert data["metadata"]["data_source"] == "sp500:nasdaq100"
            assert data["metadata"]["symbol_count"] == 518

    def test_response_structure_validation(self, client):
        """Test that response structure matches Pydantic model."""
        with patch("src.api.rest.threshold_bars.ThresholdBarService") as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.calculate_threshold_bars.return_value = {
                "metadata": {
                    "data_source": "sp500",
                    "bar_type": "DivergingThresholdBar",
                    "timeframe": "daily",
                    "threshold": 0.10,
                    "period_days": 1,
                    "symbol_count": 100,
                    "calculated_at": "2025-12-28T10:00:00",
                },
                "segments": {
                    "significant_decline": 25.0,
                    "minor_decline": 25.0,
                    "minor_advance": 25.0,
                    "significant_advance": 25.0,
                },
            }

            response = client.get("/api/threshold-bars?data_source=sp500")

            assert response.status_code == 200

            data = json.loads(response.data)

            # Validate metadata structure
            assert "metadata" in data
            metadata = data["metadata"]
            assert all(
                key in metadata
                for key in [
                    "data_source",
                    "bar_type",
                    "timeframe",
                    "threshold",
                    "period_days",
                    "symbol_count",
                    "calculated_at",
                ]
            )

            # Validate segments structure
            assert "segments" in data
            segments = data["segments"]
            assert sum(segments.values()) == pytest.approx(100.0, abs=0.01)
