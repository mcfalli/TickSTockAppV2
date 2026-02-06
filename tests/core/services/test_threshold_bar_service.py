"""Sprint 64: Threshold Bar Service Unit Tests

Test coverage for ThresholdBarService including:
- Service initialization
- Threshold bar calculations (4-segment and 2-segment)
- Symbol loading from RelationshipCache
- OHLCV data querying
- Percentage change calculations
- Binning logic validation
- Segment percentage aggregation
- Error handling for edge cases
"""

from unittest.mock import Mock, patch

import numpy as np
import pandas as pd
import pytest

from src.core.services.threshold_bar_service import ThresholdBarService


class TestThresholdBarServiceInitialization:
    """Test ThresholdBarService initialization."""

    def test_successful_initialization(self):
        """Test successful service initialization with dependency injection."""
        mock_cache = Mock()
        mock_db = Mock()

        service = ThresholdBarService(relationship_cache=mock_cache, db=mock_db)

        assert service.relationship_cache == mock_cache
        assert service.db == mock_db


class TestLoadSymbolsForDataSource:
    """Test _load_symbols_for_data_source method."""

    def test_load_universe_symbols_success(self):
        """Test loading symbols from universe via RelationshipCache."""
        mock_cache = Mock()
        mock_cache.get_universe_symbols.return_value = ["AAPL", "MSFT", "GOOGL"]
        mock_db = Mock()

        service = ThresholdBarService(relationship_cache=mock_cache, db=mock_db)
        symbols = service._load_symbols_for_data_source("sp500")

        assert symbols == ["AAPL", "MSFT", "GOOGL"]
        mock_cache.get_universe_symbols.assert_called_once_with("sp500")

    def test_load_etf_symbols_success(self):
        """Test loading symbols from ETF via RelationshipCache."""
        mock_cache = Mock()
        mock_cache.get_universe_symbols.return_value = ["AAPL", "MSFT", "NVDA", "TSLA"]
        mock_db = Mock()

        service = ThresholdBarService(relationship_cache=mock_cache, db=mock_db)
        symbols = service._load_symbols_for_data_source("SPY")

        assert len(symbols) == 4
        assert "AAPL" in symbols
        mock_cache.get_universe_symbols.assert_called_once_with("SPY")

    def test_load_multi_universe_join(self):
        """Test loading symbols from multi-universe join."""
        mock_cache = Mock()
        mock_cache.get_universe_symbols.return_value = ["AAPL", "MSFT", "GOOGL", "NVDA"]
        mock_db = Mock()

        service = ThresholdBarService(relationship_cache=mock_cache, db=mock_db)
        symbols = service._load_symbols_for_data_source("sp500:nasdaq100")

        assert len(symbols) == 4
        mock_cache.get_universe_symbols.assert_called_once_with("sp500:nasdaq100")

    def test_fallback_to_direct_symbol(self):
        """Test fallback to direct symbol when universe not found."""
        mock_cache = Mock()
        mock_cache.get_universe_symbols.return_value = []
        mock_db = Mock()

        service = ThresholdBarService(relationship_cache=mock_cache, db=mock_db)
        symbols = service._load_symbols_for_data_source("AAPL")

        assert symbols == ["AAPL"]
        mock_cache.get_universe_symbols.assert_called_once_with("AAPL")

    def test_load_symbols_cache_error(self):
        """Test error handling when RelationshipCache fails."""
        mock_cache = Mock()
        mock_cache.get_universe_symbols.side_effect = Exception("Cache error")
        mock_db = Mock()

        service = ThresholdBarService(relationship_cache=mock_cache, db=mock_db)

        with pytest.raises(RuntimeError, match="Failed to load symbols"):
            service._load_symbols_for_data_source("sp500")


class TestCalculatePercentageChanges:
    """Test _calculate_percentage_changes method."""

    def test_calculate_percentage_changes_basic(self):
        """Test percentage change calculation with basic data."""
        mock_cache = Mock()
        mock_db = Mock()

        service = ThresholdBarService(relationship_cache=mock_cache, db=mock_db)

        # Create sample OHLCV data
        data = pd.DataFrame(
            {
                "symbol": ["AAPL", "AAPL", "MSFT", "MSFT"],
                "timestamp": pd.to_datetime(
                    [
                        "2025-01-01",
                        "2025-01-02",
                        "2025-01-01",
                        "2025-01-02",
                    ]
                ),
                "close": [100.0, 110.0, 200.0, 190.0],
            }
        )

        result = service._calculate_percentage_changes(data, "daily")

        assert len(result) == 2
        assert set(result["symbol"]) == {"AAPL", "MSFT"}
        # AAPL: (110 - 100) / 100 * 100 = 10%
        # MSFT: (190 - 200) / 200 * 100 = -5%
        aapl_pct = result[result["symbol"] == "AAPL"]["pct_change"].values[0]
        msft_pct = result[result["symbol"] == "MSFT"]["pct_change"].values[0]
        assert np.isclose(aapl_pct, 10.0)
        assert np.isclose(msft_pct, -5.0)

    def test_calculate_percentage_changes_single_data_point(self):
        """Test that symbols with only 1 data point are dropped."""
        mock_cache = Mock()
        mock_db = Mock()

        service = ThresholdBarService(relationship_cache=mock_cache, db=mock_db)

        # Single data point per symbol - should be dropped
        data = pd.DataFrame(
            {
                "symbol": ["AAPL", "MSFT"],
                "timestamp": pd.to_datetime(["2025-01-01", "2025-01-01"]),
                "close": [100.0, 200.0],
            }
        )

        result = service._calculate_percentage_changes(data, "daily")

        # All symbols with single data point should be dropped
        assert len(result) == 0


class TestBinIntoSegments:
    """Test _bin_into_segments method."""

    def test_bin_diverging_threshold_bar(self):
        """Test binning for DivergingThresholdBar (4 segments)."""
        mock_cache = Mock()
        mock_db = Mock()

        service = ThresholdBarService(relationship_cache=mock_cache, db=mock_db)

        # Create test data with values in all 4 segments
        # Threshold = 10%
        # -15.0: significant_decline, -5.0: minor_decline
        # 5.0: minor_advance, 15.0: significant_advance
        data = pd.DataFrame(
            {
                "symbol": ["A", "B", "C", "D"],
                "pct_change": [-15.0, -5.0, 5.0, 15.0],
            }
        )

        result = service._bin_into_segments(data, "DivergingThresholdBar", 0.10)

        assert len(result) == 4
        # Convert to list for easier testing
        segments = result.tolist()
        assert segments[0] == "significant_decline"
        assert segments[1] == "minor_decline"
        assert segments[2] == "minor_advance"
        assert segments[3] == "significant_advance"

    def test_bin_simple_diverging_bar(self):
        """Test binning for SimpleDivergingBar (2 segments)."""
        mock_cache = Mock()
        mock_db = Mock()

        service = ThresholdBarService(relationship_cache=mock_cache, db=mock_db)

        # Create test data with positive and negative values
        data = pd.DataFrame(
            {
                "symbol": ["A", "B", "C", "D"],
                "pct_change": [-5.0, -1.0, 1.0, 5.0],
            }
        )

        result = service._bin_into_segments(data, "SimpleDivergingBar", 0.10)

        assert len(result) == 4
        segments = result.tolist()
        assert segments[0] == "decline"
        assert segments[1] == "decline"
        assert segments[2] == "advance"
        assert segments[3] == "advance"

    def test_bin_threshold_boundary_cases(self):
        """Test binning at exact threshold boundaries."""
        mock_cache = Mock()
        mock_db = Mock()

        service = ThresholdBarService(relationship_cache=mock_cache, db=mock_db)

        # Test values at exact boundaries
        # Threshold = 10%
        # -10.0: exactly -threshold, 0.0: exactly 0
        # 10.0: exactly threshold (both values)
        data = pd.DataFrame(
            {
                "symbol": ["A", "B", "C", "D"],
                "pct_change": [-10.0, 0.0, 10.0, 10.0],
            }
        )

        result = service._bin_into_segments(data, "DivergingThresholdBar", 0.10)

        segments = result.tolist()
        # Based on binning: [-inf, -10, 0, 10, +inf] with right=False
        # -10 falls in minor_decline ([-10, 0))
        # 0 falls in minor_advance ([0, 10))
        # 10 falls in significant_advance ([10, +inf))
        assert segments[0] == "minor_decline"  # -10.0
        assert segments[1] == "minor_advance"  # 0.0
        assert segments[2] == "significant_advance"  # 10.0
        assert segments[3] == "significant_advance"  # 10.0


class TestAggregateSegmentPercentages:
    """Test _aggregate_segment_percentages method."""

    def test_aggregate_diverging_threshold_bar(self):
        """Test aggregation for DivergingThresholdBar."""
        mock_cache = Mock()
        mock_db = Mock()

        service = ThresholdBarService(relationship_cache=mock_cache, db=mock_db)

        # Create binned data: 2 in each segment (total 8 symbols)
        binned_data = pd.Series(
            [
                "significant_decline",
                "significant_decline",
                "minor_decline",
                "minor_decline",
                "minor_advance",
                "minor_advance",
                "significant_advance",
                "significant_advance",
            ]
        )

        result = service._aggregate_segment_percentages(
            binned_data, "DivergingThresholdBar"
        )

        assert len(result) == 4
        # Each segment should have 25% (2 out of 8)
        assert np.isclose(result["significant_decline"], 25.0)
        assert np.isclose(result["minor_decline"], 25.0)
        assert np.isclose(result["minor_advance"], 25.0)
        assert np.isclose(result["significant_advance"], 25.0)

        # Verify sum equals 100%
        total = sum(result.values())
        assert np.isclose(total, 100.0)

    def test_aggregate_simple_diverging_bar(self):
        """Test aggregation for SimpleDivergingBar."""
        mock_cache = Mock()
        mock_db = Mock()

        service = ThresholdBarService(relationship_cache=mock_cache, db=mock_db)

        # Create binned data: 3 decline, 7 advance (total 10 symbols)
        binned_data = pd.Series(
            [
                "decline",
                "decline",
                "decline",
                "advance",
                "advance",
                "advance",
                "advance",
                "advance",
                "advance",
                "advance",
            ]
        )

        result = service._aggregate_segment_percentages(
            binned_data, "SimpleDivergingBar"
        )

        assert len(result) == 2
        # 3 out of 10 = 30%, 7 out of 10 = 70%
        assert np.isclose(result["decline"], 30.0)
        assert np.isclose(result["advance"], 70.0)

        # Verify sum equals 100%
        total = sum(result.values())
        assert np.isclose(total, 100.0)

    def test_aggregate_with_missing_segments(self):
        """Test aggregation when some segments have zero count."""
        mock_cache = Mock()
        mock_db = Mock()

        service = ThresholdBarService(relationship_cache=mock_cache, db=mock_db)

        # All symbols in only 2 segments (missing significant_decline and minor_decline)
        binned_data = pd.Series(
            [
                "minor_advance",
                "minor_advance",
                "significant_advance",
                "significant_advance",
            ]
        )

        result = service._aggregate_segment_percentages(
            binned_data, "DivergingThresholdBar"
        )

        assert len(result) == 4
        # Missing segments should have 0.0%
        assert result["significant_decline"] == 0.0
        assert result["minor_decline"] == 0.0
        assert np.isclose(result["minor_advance"], 50.0)
        assert np.isclose(result["significant_advance"], 50.0)

        # Verify sum equals 100%
        total = sum(result.values())
        assert np.isclose(total, 100.0)


class TestCalculateThresholdBarsIntegration:
    """Integration tests for calculate_threshold_bars method."""

    def test_calculate_threshold_bars_input_validation(self):
        """Test input validation in calculate_threshold_bars."""
        mock_cache = Mock()
        mock_db = Mock()

        service = ThresholdBarService(relationship_cache=mock_cache, db=mock_db)

        # Test empty data_source
        with pytest.raises(ValueError, match="data_source must be non-empty string"):
            service.calculate_threshold_bars("", "DivergingThresholdBar", "daily")

        # Test invalid timeframe
        with pytest.raises(ValueError, match="Invalid timeframe"):
            service.calculate_threshold_bars("sp500", "DivergingThresholdBar", "invalid")

        # Test negative threshold
        with pytest.raises(ValueError, match="Threshold must be between 0 and 1"):
            service.calculate_threshold_bars(
                "sp500", "DivergingThresholdBar", "daily", threshold=-0.1
            )

        # Test threshold > 1
        with pytest.raises(ValueError, match="Threshold must be between 0 and 1"):
            service.calculate_threshold_bars(
                "sp500", "DivergingThresholdBar", "daily", threshold=1.5
            )

    def test_calculate_threshold_bars_no_symbols_found(self):
        """Test error when no symbols found for data_source."""
        mock_cache = Mock()
        mock_cache.get_universe_symbols.return_value = []
        mock_db = Mock()

        service = ThresholdBarService(relationship_cache=mock_cache, db=mock_db)

        # Override the fallback behavior for this test
        with (
            patch.object(service, "_load_symbols_for_data_source", return_value=[]),
            pytest.raises(RuntimeError, match="No symbols found"),
        ):
            service.calculate_threshold_bars(
                "invalid_universe", "DivergingThresholdBar", "daily"
            )
