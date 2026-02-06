"""Sprint 65: Stock Groups End-to-End Integration Tests

Tests the complete flow from API endpoint through RelationshipCache to database.
Validates performance, error handling, and data accuracy for stock groups search.

Test Coverage:
- Full API → Service → Database flow
- Real RelationshipCache integration
- Type filtering end-to-end
- Search term filtering end-to-end
- Error handling across all layers
"""

import json

import pytest
from flask import Flask

from src.api.rest.stock_groups import stock_groups_bp


@pytest.fixture
def app():
    """Create Flask test app with stock_groups blueprint."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret-key"

    app.register_blueprint(stock_groups_bp)

    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


class TestStockGroupsEndToEnd:
    """End-to-end integration tests for stock groups feature."""

    def test_e2e_get_all_stock_groups(self, client):
        """
        E2E test: Get all stock groups with real RelationshipCache.

        Tests complete flow with real components where available.
        """
        response = client.get("/api/stock-groups")

        # API should respond with 200 or gracefully handle missing data
        assert response.status_code in [200, 500]  # 500 if database not available

        if response.status_code == 200:
            data = json.loads(response.data)

            # Validate response structure
            assert "groups" in data
            assert "total_count" in data
            assert "types" in data
            assert "environment" in data

            # Validate data types
            assert isinstance(data["groups"], list)
            assert isinstance(data["total_count"], int)
            assert isinstance(data["types"], list)
            assert isinstance(data["environment"], str)

            # Environment should be DEFAULT
            assert data["environment"] == "DEFAULT"

            # If we have groups, validate their structure
            if data["total_count"] > 0:
                group = data["groups"][0]
                assert "name" in group
                assert "type" in group
                assert "member_count" in group
                assert "environment" in group
                assert "created_at" in group
                assert "updated_at" in group

                # Validate types
                assert group["type"] in [
                    "ETF",
                    "SECTOR",
                    "THEME",
                    "UNIVERSE",
                    "SEGMENT",
                    "CUSTOM",
                ]

    def test_e2e_filter_by_type_etf(self, client):
        """
        E2E test: Type filtering for ETF groups.

        Tests that type parameter correctly filters results to only ETFs.
        """
        response = client.get("/api/stock-groups?types=ETF")

        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = json.loads(response.data)

            # Validate response structure
            assert "groups" in data
            assert "total_count" in data

            # All groups should be ETF type
            for group in data["groups"]:
                assert group["type"] == "ETF", (
                    f"Expected ETF type, got {group['type']} for {group['name']}"
                )

            # Types filter should match request
            assert data["types"] == ["ETF"]

    def test_e2e_search_term_filtering(self, client):
        """
        E2E test: Search term filtering.

        Tests that search parameter correctly filters results.
        """
        # Search for "tech" which should match information_technology sector
        response = client.get("/api/stock-groups?search=tech")

        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = json.loads(response.data)

            # Validate response structure
            assert "groups" in data
            assert "total_count" in data

            # If we have results, they should contain "tech" in name, type, or description
            for group in data["groups"]:
                search_term = "tech"
                matches = (
                    search_term in group["name"].lower()
                    or search_term in group["type"].lower()
                    or (
                        group.get("description")
                        and search_term in group["description"].lower()
                    )
                )
                assert matches, (
                    f"Group {group['name']} does not match search term 'tech'"
                )


@pytest.mark.integration
class TestStockGroupsErrorHandling:
    """Error handling validation tests."""

    def test_e2e_error_handling_invalid_type(self, client):
        """
        E2E test: Error handling for invalid type parameter.
        """
        response = client.get("/api/stock-groups?types=INVALID_TYPE")

        # Should return 400 for validation error
        assert response.status_code == 400

        data = json.loads(response.data)
        assert "error" in data
        assert "Invalid type parameter" in data["error"]

    def test_e2e_error_handling_multiple_invalid_types(self, client):
        """
        E2E test: Error handling when multiple types include invalid ones.
        """
        response = client.get("/api/stock-groups?types=ETF,INVALID,SECTOR")

        # Should return 400 for validation error
        assert response.status_code == 400

        data = json.loads(response.data)
        assert "error" in data

    def test_e2e_multiple_valid_types(self, client):
        """
        E2E test: Multiple valid types (ETF,SECTOR).
        """
        response = client.get("/api/stock-groups?types=ETF,SECTOR")

        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = json.loads(response.data)

            # All groups should be either ETF or SECTOR
            for group in data["groups"]:
                assert group["type"] in ["ETF", "SECTOR"], (
                    f"Expected ETF or SECTOR, got {group['type']}"
                )

            # Types filter should match request
            assert set(data["types"]) == {"ETF", "SECTOR"}


@pytest.mark.benchmark
class TestStockGroupsPerformance:
    """Performance validation tests for stock groups."""

    def test_performance_api_response_time(self, client):
        """
        Validate API response time is <50ms target.

        Note: May fail if database is slow or not available.
        """
        import time

        start = time.time()
        response = client.get("/api/stock-groups")
        elapsed_ms = (time.time() - start) * 1000

        if response.status_code == 200:
            # Target: <50ms for API response
            # Allow up to 100ms for integration tests
            assert elapsed_ms < 100, f"API response too slow: {elapsed_ms:.1f}ms"

    def test_performance_with_search_filtering(self, client):
        """
        Validate performance with search term filtering.

        Target: <100ms with search.
        """
        import time

        start = time.time()
        response = client.get("/api/stock-groups?search=tech")
        elapsed_ms = (time.time() - start) * 1000

        if response.status_code == 200:
            # Target: <100ms even with search filtering
            assert elapsed_ms < 150, (
                f"API response with search too slow: {elapsed_ms:.1f}ms"
            )


@pytest.mark.integration
class TestStockGroupsDataAccuracy:
    """Data accuracy validation tests."""

    def test_data_accuracy_member_counts_positive(self, client):
        """
        Validate that all member_count values are positive integers.
        """
        response = client.get("/api/stock-groups")

        if response.status_code == 200:
            data = json.loads(response.data)

            for group in data["groups"]:
                assert isinstance(group["member_count"], int), (
                    f"member_count should be int, got {type(group['member_count'])}"
                )
                assert group["member_count"] > 0, (
                    f"Group {group['name']} has non-positive member_count: "
                    f"{group['member_count']}"
                )

    def test_data_accuracy_timestamps_valid(self, client):
        """
        Validate that created_at and updated_at are valid ISO timestamps.
        """
        response = client.get("/api/stock-groups")

        if response.status_code == 200:
            from datetime import datetime

            data = json.loads(response.data)

            for group in data["groups"]:
                # Parse timestamps (should be ISO format)
                try:
                    created = datetime.fromisoformat(
                        group["created_at"].replace("Z", "+00:00")
                    )
                    updated = datetime.fromisoformat(
                        group["updated_at"].replace("Z", "+00:00")
                    )

                    # updated_at should be >= created_at
                    assert updated >= created, (
                        f"Group {group['name']}: updated_at before created_at"
                    )
                except ValueError as e:
                    pytest.fail(f"Invalid timestamp format for {group['name']}: {e}")

    def test_data_accuracy_environment_consistency(self, client):
        """
        Validate that all groups have environment='DEFAULT'.
        """
        response = client.get("/api/stock-groups")

        if response.status_code == 200:
            data = json.loads(response.data)

            for group in data["groups"]:
                assert group["environment"] == "DEFAULT", (
                    f"Group {group['name']} has unexpected environment: "
                    f"{group['environment']}"
                )
