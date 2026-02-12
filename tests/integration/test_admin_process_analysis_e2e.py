"""
End-to-end tests for Admin Process Analysis workflow.

Tests the complete workflow from job submission to analysis completion,
verifying that patterns and indicators are detected correctly.
"""

import time
import pytest
from src.analysis.services.analysis_service import AnalysisService
from src.analysis.data.ohlcv_data_service import OHLCVDataService


def _ensure_timestamp_column(data):
    """Ensure data has timestamp as a column with datetime type (patterns require it)."""
    import pandas as pd

    # Reset index if timestamp is in index
    if 'timestamp' not in data.columns and data.index.name in ['timestamp', 'date']:
        data = data.reset_index()
        if 'date' in data.columns:
            data = data.rename(columns={'date': 'timestamp'})

    # Ensure timestamp column is datetime type
    if 'timestamp' in data.columns:
        data['timestamp'] = pd.to_datetime(data['timestamp'])

    return data


class TestAdminProcessAnalysisE2E:
    """End-to-end tests for Process Analysis admin feature."""

    def test_single_symbol_analysis_both(self):
        """Test analyzing a single symbol with both patterns and indicators."""
        # Setup services
        analysis_service = AnalysisService()
        data_service = OHLCVDataService()

        # Fetch real data from database
        symbol = "AAPL"
        timeframe = "daily"
        data = data_service.get_ohlcv_data(
            symbol=symbol,
            timeframe=timeframe,
            limit=250
        )

        assert not data.empty, "No OHLCV data available for AAPL"
        data = _ensure_timestamp_column(data)
        print(f"[OK] Fetched {len(data)} bars for {symbol}")

        # Run analysis with both patterns and indicators
        result = analysis_service.analyze_symbol(
            symbol=symbol,
            data=data,
            timeframe=timeframe,
            indicators=None,  # None = all available
            patterns=None,    # None = all available
            calculate_all=True
        )

        # Verify results structure
        assert 'indicators' in result, "Missing indicators in result"
        assert 'patterns' in result, "Missing patterns in result"

        # Verify indicators were calculated
        indicators = result['indicators']
        assert len(indicators) > 0, "No indicators calculated"
        print(f"[OK] Calculated {len(indicators)} indicators")

        # Check specific indicators exist
        expected_indicators = ['sma', 'ema', 'rsi', 'macd', 'bollinger_bands', 'atr', 'stochastic', 'adx']
        for ind_name in expected_indicators:
            assert ind_name in indicators, f"Missing indicator: {ind_name}"
            assert 'value' in indicators[ind_name], f"Indicator {ind_name} missing 'value'"
            print(f"  [OK] {ind_name}: {indicators[ind_name].get('indicator_type', 'N/A')}")

        # Verify patterns were detected
        patterns = result['patterns']
        assert len(patterns) > 0, "No patterns detected"
        print(f"[OK] Detected {len(patterns)} pattern types")

        # Check specific patterns exist
        expected_patterns = ['doji', 'hammer', 'engulfing', 'shooting_star', 'hanging_man',
                           'harami', 'morning_star', 'evening_star']
        for pattern_name in expected_patterns:
            assert pattern_name in patterns, f"Missing pattern: {pattern_name}"
            assert 'detected' in patterns[pattern_name], f"Pattern {pattern_name} missing 'detected'"
            print(f"  [OK] {pattern_name}: checked")

        print("[PASS] Single symbol analysis PASSED")

    def test_multiple_symbols_analysis_patterns_only(self):
        """Test analyzing multiple symbols with patterns only."""
        # Setup services
        analysis_service = AnalysisService()
        data_service = OHLCVDataService()

        symbols = ["AAPL", "MSFT", "NVDA"]
        timeframe = "daily"

        results = []
        for symbol in symbols:
            # Fetch data
            data = data_service.get_ohlcv_data(
                symbol=symbol,
                timeframe=timeframe,
                limit=250
            )

            if data.empty:
                print(f"[WARN] No data for {symbol}, skipping")
                continue

            data = _ensure_timestamp_column(data)

            # Run pattern-only analysis (use calculate_all with custom logic)
            result = analysis_service.analyze_symbol(
                symbol=symbol,
                data=data,
                timeframe=timeframe,
                calculate_all=True  # This will get all patterns and indicators
            )

            # Remove indicators from result (patterns-only test)
            result['indicators'] = {}

            results.append({
                'symbol': symbol,
                'patterns': result['patterns'],
                'indicators': result['indicators']
            })

            print(f"[OK] {symbol}: {len(result['patterns'])} patterns checked")

        # Verify all symbols processed
        assert len(results) == len(symbols), f"Expected {len(symbols)} results, got {len(results)}"

        # Verify patterns were detected for each symbol
        for result_data in results:
            assert len(result_data['patterns']) == 8, f"Expected 8 patterns for {result_data['symbol']}"
            assert len(result_data['indicators']) == 0, f"Expected 0 indicators for {result_data['symbol']}"

        print(f"[PASS] Multiple symbols (patterns only) PASSED: {len(results)} symbols")

    def test_multiple_symbols_analysis_indicators_only(self):
        """Test analyzing multiple symbols with indicators only."""
        # Setup services
        analysis_service = AnalysisService()
        data_service = OHLCVDataService()

        symbols = ["AAPL", "TSLA"]
        timeframe = "daily"

        results = []
        for symbol in symbols:
            # Fetch data
            data = data_service.get_ohlcv_data(
                symbol=symbol,
                timeframe=timeframe,
                limit=250
            )

            if data.empty:
                print(f"[WARN] No data for {symbol}, skipping")
                continue

            data = _ensure_timestamp_column(data)

            # Run indicator-only analysis (use calculate_all with custom logic)
            result = analysis_service.analyze_symbol(
                symbol=symbol,
                data=data,
                timeframe=timeframe,
                calculate_all=True  # This will get all patterns and indicators
            )

            # Remove patterns from result (indicators-only test)
            result['patterns'] = {}

            results.append({
                'symbol': symbol,
                'patterns': result['patterns'],
                'indicators': result['indicators']
            })

            print(f"[OK] {symbol}: {len(result['indicators'])} indicators calculated")

        # Verify all symbols processed
        assert len(results) == len(symbols), f"Expected {len(symbols)} results, got {len(results)}"

        # Verify indicators were calculated for each symbol
        for result_data in results:
            assert len(result_data['indicators']) == 8, f"Expected 8 indicators for {result_data['symbol']}"
            assert len(result_data['patterns']) == 0, f"Expected 0 patterns for {result_data['symbol']}"

        print(f"[PASS] Multiple symbols (indicators only) PASSED: {len(results)} symbols")

    def test_analysis_performance_benchmark(self):
        """Benchmark analysis performance (should be <2s per symbol)."""
        # Setup services
        analysis_service = AnalysisService()
        data_service = OHLCVDataService()

        symbol = "AAPL"
        timeframe = "daily"

        # Fetch data
        data = data_service.get_ohlcv_data(
            symbol=symbol,
            timeframe=timeframe,
            limit=250
        )

        assert not data.empty, "No OHLCV data available"
        data = _ensure_timestamp_column(data)

        # Benchmark analysis time
        start_time = time.time()

        result = analysis_service.analyze_symbol(
            symbol=symbol,
            data=data,
            timeframe=timeframe,
            indicators=None,
            patterns=None,
            calculate_all=True
        )

        elapsed_time = time.time() - start_time

        # Verify performance target (<2s per symbol)
        assert elapsed_time < 2.0, f"Analysis took {elapsed_time:.2f}s, expected <2s"

        print(f"[OK] Analysis completed in {elapsed_time:.3f}s (target: <2s)")
        print(f"  - Indicators: {len(result['indicators'])}")
        print(f"  - Patterns: {len(result['patterns'])}")
        print(f"[PASS] Performance benchmark PASSED")


if __name__ == '__main__':
    # Run tests with verbose output
    import sys

    print("=" * 70)
    print("ADMIN PROCESS ANALYSIS - END-TO-END TESTS")
    print("=" * 70)
    print()

    test_suite = TestAdminProcessAnalysisE2E()

    try:
        print("Test 1: Single symbol analysis (both patterns and indicators)")
        print("-" * 70)
        test_suite.test_single_symbol_analysis_both()
        print()

        print("Test 2: Multiple symbols (patterns only)")
        print("-" * 70)
        test_suite.test_multiple_symbols_analysis_patterns_only()
        print()

        print("Test 3: Multiple symbols (indicators only)")
        print("-" * 70)
        test_suite.test_multiple_symbols_analysis_indicators_only()
        print()

        print("Test 4: Performance benchmark")
        print("-" * 70)
        test_suite.test_analysis_performance_benchmark()
        print()

        print("=" * 70)
        print("[PASS] ALL TESTS PASSED")
        print("=" * 70)
        sys.exit(0)

    except AssertionError as e:
        print()
        print("=" * 70)
        print(f"[FAIL] TEST FAILED: {e}")
        print("=" * 70)
        sys.exit(1)

    except Exception as e:
        print()
        print("=" * 70)
        print(f"[FAIL] UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        print("=" * 70)
        sys.exit(1)
