"""Sprint 65: Stock Groups API Tests

Test coverage for /api/stock-groups endpoint including:
- Request parameter validation
- Authentication requirements
- Success responses with valid data
- Error handling for invalid parameters
- Response structure validation
"""

import json
from unittest.mock import Mock, patch

import pytest
from flask import Flask

from src.api.rest.stock_groups import stock_groups_bp


class TestStockGroupsAPIRegistration:
    """Test API registration and blueprint setup."""

    def test_blueprint_registration(self):
        """Test that stock_groups blueprint can be registered."""
        app = Flask(__name__)
        app.config["TESTING"] = True

        app.register_blueprint(stock_groups_bp)

        # Verify blueprint is registered
        assert "stock_groups" in [bp.name for bp in app.blueprints.values()]

    def test_blueprint_has_routes(self):
        """Test that blueprint has expected routes."""
        # Check that blueprint has deferred functions (routes)
        assert len(stock_groups_bp.deferred_functions) > 0


class TestStockGroupsAPIEndpoint:
    """Test /api/stock-groups endpoint functionality."""

    @pytest.fixture
    def app(self):
        """Create Flask app with stock_groups blueprint registered."""
        app = Flask(__name__)
        app.config["TESTING"] = True
        app.config["SECRET_KEY"] = "test-secret-key"

        app.register_blueprint(stock_groups_bp)

        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()

    @pytest.fixture
    def sample_groups_data(self):
        """Sample groups data for testing."""
        return [
            {
                "name": "SPY",
                "type": "ETF",
                "description": "SPDR S&P 500 ETF Trust",
                "member_count": 504,
                "environment": "DEFAULT",
                "created_at": "2025-12-20T10:00:00",
                "updated_at": "2025-12-28T10:00:00",
            },
            {
                "name": "information_technology",
                "type": "SECTOR",
                "description": "Information Technology Sector",
                "member_count": 549,
                "environment": "DEFAULT",
                "created_at": "2025-12-20T10:00:00",
                "updated_at": "2025-12-28T10:00:00",
            },
            {
                "name": "crypto_miners",
                "type": "THEME",
                "description": "Cryptocurrency Mining Companies",
                "member_count": 9,
                "environment": "DEFAULT",
                "created_at": "2025-12-20T10:00:00",
                "updated_at": "2025-12-28T10:00:00",
            },
            {
                "name": "nasdaq100",
                "type": "UNIVERSE",
                "description": "NASDAQ-100 Index Components",
                "member_count": 102,
                "environment": "DEFAULT",
                "created_at": "2025-12-20T10:00:00",
                "updated_at": "2025-12-28T10:00:00",
            },
        ]

    def test_successful_get_all_groups(self, client, sample_groups_data):
        """Test successful retrieval of all stock groups."""
        with patch(
            "src.api.rest.stock_groups.get_relationship_cache"
        ) as mock_cache_factory:
            # Mock RelationshipCache
            mock_cache = Mock()
            mock_cache_factory.return_value = mock_cache
            mock_cache.get_available_universes.return_value = sample_groups_data

            response = client.get("/api/stock-groups")

            assert response.status_code == 200
            assert response.content_type == "application/json"

            data = json.loads(response.data)
            assert "groups" in data
            assert "total_count" in data
            assert data["total_count"] == 4
            assert len(data["groups"]) == 4
            assert data["groups"][0]["name"] == "SPY"

    def test_successful_get_filtered_by_type(self, client, sample_groups_data):
        """Test filtering by single type (ETF)."""
        with patch(
            "src.api.rest.stock_groups.get_relationship_cache"
        ) as mock_cache_factory:
            mock_cache = Mock()
            mock_cache_factory.return_value = mock_cache
            mock_cache.get_available_universes.return_value = [
                sample_groups_data[0]
            ]  # Only ETF

            response = client.get("/api/stock-groups?types=ETF")

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["total_count"] == 1
            assert data["groups"][0]["type"] == "ETF"

    def test_successful_get_multiple_types(self, client, sample_groups_data):
        """Test filtering by multiple types (ETF,SECTOR)."""
        with patch(
            "src.api.rest.stock_groups.get_relationship_cache"
        ) as mock_cache_factory:
            mock_cache = Mock()
            mock_cache_factory.return_value = mock_cache
            mock_cache.get_available_universes.return_value = sample_groups_data[:2]

            response = client.get("/api/stock-groups?types=ETF,SECTOR")

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["total_count"] == 2
            assert data["groups"][0]["type"] in ["ETF", "SECTOR"]
            assert data["groups"][1]["type"] in ["ETF", "SECTOR"]

    def test_successful_get_with_search(self, client, sample_groups_data):
        """Test search term filters results."""
        with patch(
            "src.api.rest.stock_groups.get_relationship_cache"
        ) as mock_cache_factory:
            mock_cache = Mock()
            mock_cache_factory.return_value = mock_cache
            mock_cache.get_available_universes.return_value = sample_groups_data

            # Search for "tech" should match information_technology
            response = client.get("/api/stock-groups?search=tech")

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["total_count"] == 1
            assert data["groups"][0]["name"] == "information_technology"

    def test_empty_result_set(self, client):
        """Test no groups match criteria returns empty list."""
        with patch(
            "src.api.rest.stock_groups.get_relationship_cache"
        ) as mock_cache_factory:
            mock_cache = Mock()
            mock_cache_factory.return_value = mock_cache
            mock_cache.get_available_universes.return_value = []

            response = client.get("/api/stock-groups")

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["total_count"] == 0
            assert len(data["groups"]) == 0

    def test_invalid_type_parameter(self, client):
        """Test invalid type parameter returns 400."""
        response = client.get("/api/stock-groups?types=INVALID_TYPE")

        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data
        assert "Invalid type parameter" in data["error"]

    def test_service_error_handling(self, client):
        """Test service exception returns 500."""
        with patch(
            "src.api.rest.stock_groups.get_relationship_cache"
        ) as mock_cache_factory:
            mock_cache = Mock()
            mock_cache_factory.return_value = mock_cache
            mock_cache.get_available_universes.side_effect = RuntimeError(
                "Database connection failed"
            )

            response = client.get("/api/stock-groups")

            assert response.status_code == 500
            data = json.loads(response.data)
            assert "error" in data

    def test_response_structure_validation(self, client, sample_groups_data):
        """Test response matches expected structure."""
        with patch(
            "src.api.rest.stock_groups.get_relationship_cache"
        ) as mock_cache_factory:
            mock_cache = Mock()
            mock_cache_factory.return_value = mock_cache
            mock_cache.get_available_universes.return_value = sample_groups_data

            response = client.get("/api/stock-groups")

            assert response.status_code == 200
            data = json.loads(response.data)

            # Validate response structure
            assert "groups" in data
            assert "total_count" in data
            assert "types" in data
            assert "environment" in data

            # Validate each group has required fields
            for group in data["groups"]:
                assert "name" in group
                assert "type" in group
                assert "member_count" in group
                assert "environment" in group
                assert "created_at" in group
                assert "updated_at" in group

    def test_member_count_accuracy(self, client, sample_groups_data):
        """Test member counts match expected values."""
        with patch(
            "src.api.rest.stock_groups.get_relationship_cache"
        ) as mock_cache_factory:
            mock_cache = Mock()
            mock_cache_factory.return_value = mock_cache
            mock_cache.get_available_universes.return_value = sample_groups_data

            response = client.get("/api/stock-groups")

            assert response.status_code == 200
            data = json.loads(response.data)

            # Verify specific member counts
            spy_group = next((g for g in data["groups"] if g["name"] == "SPY"), None)
            assert spy_group is not None
            assert spy_group["member_count"] == 504

    def test_environment_filtering(self, client, sample_groups_data):
        """Test only DEFAULT environment returned."""
        with patch(
            "src.api.rest.stock_groups.get_relationship_cache"
        ) as mock_cache_factory:
            mock_cache = Mock()
            mock_cache_factory.return_value = mock_cache
            mock_cache.get_available_universes.return_value = sample_groups_data

            response = client.get("/api/stock-groups")

            assert response.status_code == 200
            data = json.loads(response.data)

            # All groups should be DEFAULT environment
            for group in data["groups"]:
                assert group["environment"] == "DEFAULT"

    def test_performance_under_50ms(self, client, sample_groups_data):
        """Test response time <50ms (mocked)."""
        import time

        with patch(
            "src.api.rest.stock_groups.get_relationship_cache"
        ) as mock_cache_factory:
            mock_cache = Mock()
            mock_cache_factory.return_value = mock_cache
            mock_cache.get_available_universes.return_value = sample_groups_data

            start = time.time()
            response = client.get("/api/stock-groups")
            elapsed = (time.time() - start) * 1000  # Convert to ms

            assert response.status_code == 200
            # With mocking, should be very fast (<10ms typically)
            assert elapsed < 50

    def test_case_insensitive_types(self, client, sample_groups_data):
        """Test type parameters are case-insensitive."""
        with patch(
            "src.api.rest.stock_groups.get_relationship_cache"
        ) as mock_cache_factory:
            mock_cache = Mock()
            mock_cache_factory.return_value = mock_cache
            mock_cache.get_available_universes.return_value = [sample_groups_data[0]]

            # Test lowercase types
            response = client.get("/api/stock-groups?types=etf")

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["total_count"] == 1
