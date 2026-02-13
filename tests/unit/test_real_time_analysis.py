"""
Unit tests for Sprint 75 Phase 1: Real-Time Pattern/Indicator Analysis

Tests the integration between WebSocket bar updates and automatic analysis triggering.
"""

import pytest
import time
from datetime import datetime, UTC
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock
import pandas as pd

from src.core.services.market_data_service import MarketDataService
from src.core.domain.market.tick import TickData


class TestRealTimeAnalysis:
    """Test suite for real-time bar analysis triggering."""

    @pytest.fixture
    def config(self):
        """Mock configuration."""
        return Mock()

    @pytest.fixture
    def market_data_service(self, config):
        """Create MarketDataService instance."""
        return MarketDataService(config=config, socketio=None)

    @pytest.fixture
    def sample_tick_data(self):
        """Create sample tick data for testing."""
        return TickData(
            ticker='AAPL',
            price=150.50,
            volume=1000,
            timestamp=datetime.now(UTC).timestamp(),
            tick_open=150.00,
            tick_high=151.00,
            tick_low=149.50,
            tick_close=150.50,
            tick_volume=1000,
            tick_vwap=150.25,
            tick_start_timestamp=datetime.now(UTC).timestamp() - 60,
            tick_end_timestamp=datetime.now(UTC).timestamp()
        )

    @pytest.fixture
    def sample_ohlcv_data(self):
        """Create sample OHLCV DataFrame."""
        return pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=200, freq='1min'),
            'open': [150.0] * 200,
            'high': [151.0] * 200,
            'low': [149.5] * 200,
            'close': [150.5] * 200,
            'volume': [1000] * 200,
        })

    def test_trigger_bar_analysis_spawns_thread(self, market_data_service):
        """Test that _trigger_bar_analysis_async spawns a background thread."""
        symbol = 'AAPL'
        timestamp = datetime.now(UTC)

        # Mock threading to capture thread creation
        with patch('src.core.services.market_data_service.threading.Thread') as mock_thread:
            market_data_service._trigger_bar_analysis_async(symbol, timestamp)

            # Verify thread was created
            mock_thread.assert_called_once()
            call_kwargs = mock_thread.call_args[1]
            assert call_kwargs['daemon'] is True
            assert 'BarAnalysis' in call_kwargs['name']

            # Verify thread was started
            mock_thread.return_value.start.assert_called_once()

    def test_bar_analysis_fetches_ohlcv_data(self, market_data_service, sample_ohlcv_data):
        """Test that analysis fetches OHLCV data from database."""
        symbol = 'AAPL'
        timestamp = datetime.now(UTC)

        with patch('src.core.services.market_data_service.OHLCVDataService') as mock_ohlcv_service:
            # Setup mock
            mock_ohlcv_service.return_value.get_ohlcv_data.return_value = sample_ohlcv_data

            # Trigger analysis (in same thread for testing)
            market_data_service._trigger_bar_analysis_async(symbol, timestamp)

            # Wait for thread to complete (max 2 seconds)
            time.sleep(2)

            # Verify OHLCV data was fetched
            mock_ohlcv_service.return_value.get_ohlcv_data.assert_called_with(
                symbol=symbol,
                timeframe='1min',
                limit=200
            )

    def test_bar_analysis_runs_analysis_service(self, market_data_service, sample_ohlcv_data):
        """Test that AnalysisService is called with correct parameters."""
        symbol = 'AAPL'
        timestamp = datetime.now(UTC)

        with patch('src.core.services.market_data_service.OHLCVDataService') as mock_ohlcv_service, \
             patch('src.core.services.market_data_service.AnalysisService') as mock_analysis_service:

            # Setup mocks
            mock_ohlcv_service.return_value.get_ohlcv_data.return_value = sample_ohlcv_data
            mock_analysis_service.return_value.analyze_symbol.return_value = {
                'patterns': {'doji': {'detected': True, 'confidence': 0.8}},
                'indicators': {'sma': {'value': 150.5, 'value_data': {}}}
            }

            # Trigger analysis
            market_data_service._trigger_bar_analysis_async(symbol, timestamp)
            time.sleep(2)

            # Verify AnalysisService was called
            mock_analysis_service.return_value.analyze_symbol.assert_called_with(
                symbol=symbol,
                data=sample_ohlcv_data,
                timeframe='1min',
                indicators=None,
                patterns=None,
                calculate_all=True
            )

    def test_bar_analysis_persists_results(self, market_data_service, sample_ohlcv_data):
        """Test that analysis results are persisted to database."""
        symbol = 'AAPL'
        timestamp = datetime.now(UTC)

        with patch('src.core.services.market_data_service.OHLCVDataService') as mock_ohlcv_service, \
             patch('src.core.services.market_data_service.AnalysisService') as mock_analysis_service, \
             patch('src.core.services.market_data_service._persist_pattern_results') as mock_persist_patterns, \
             patch('src.core.services.market_data_service._persist_indicator_results') as mock_persist_indicators:

            # Setup mocks
            mock_ohlcv_service.return_value.get_ohlcv_data.return_value = sample_ohlcv_data
            pattern_results = {'doji': {'detected': True, 'confidence': 0.8}}
            indicator_results = {'sma': {'value': 150.5, 'value_data': {}}}
            mock_analysis_service.return_value.analyze_symbol.return_value = {
                'patterns': pattern_results,
                'indicators': indicator_results
            }

            # Trigger analysis
            market_data_service._trigger_bar_analysis_async(symbol, timestamp)
            time.sleep(2)

            # Verify persistence functions called
            mock_persist_patterns.assert_called_with(symbol, '1min', pattern_results)
            mock_persist_indicators.assert_called_with(symbol, '1min', indicator_results)

    def test_bar_analysis_publishes_redis_event(self, market_data_service, sample_ohlcv_data):
        """Test that Redis event is published after successful analysis."""
        symbol = 'AAPL'
        timestamp = datetime.now(UTC)

        with patch('src.core.services.market_data_service.OHLCVDataService') as mock_ohlcv_service, \
             patch('src.core.services.market_data_service.AnalysisService') as mock_analysis_service, \
             patch('src.core.services.market_data_service.get_redis_manager') as mock_get_redis:

            # Setup mocks
            mock_redis_manager = Mock()
            mock_get_redis.return_value = mock_redis_manager
            mock_ohlcv_service.return_value.get_ohlcv_data.return_value = sample_ohlcv_data
            mock_analysis_service.return_value.analyze_symbol.return_value = {
                'patterns': {'doji': {'detected': True, 'confidence': 0.8}},
                'indicators': {'sma': {'value': 150.5, 'value_data': {}}}
            }

            # Trigger analysis
            market_data_service._trigger_bar_analysis_async(symbol, timestamp)
            time.sleep(2)

            # Verify Redis event published
            mock_redis_manager.publish_message.assert_called()
            call_args = mock_redis_manager.publish_message.call_args
            assert call_args[0][0] == 'tickstock:events:analysis_complete'
            event_data = call_args[0][1]
            assert event_data['symbol'] == symbol
            assert event_data['timeframe'] == '1min'
            assert event_data['patterns_detected'] == 1
            assert event_data['indicators_calculated'] == 1

    def test_bar_analysis_handles_no_ohlcv_data(self, market_data_service):
        """Test graceful handling when no OHLCV data available."""
        symbol = 'NEWSTOCK'
        timestamp = datetime.now(UTC)

        with patch('src.core.services.market_data_service.OHLCVDataService') as mock_ohlcv_service, \
             patch('src.core.services.market_data_service.AnalysisService') as mock_analysis_service:

            # Setup mock to return None (no data)
            mock_ohlcv_service.return_value.get_ohlcv_data.return_value = None

            # Trigger analysis
            market_data_service._trigger_bar_analysis_async(symbol, timestamp)
            time.sleep(2)

            # Verify AnalysisService was NOT called
            mock_analysis_service.return_value.analyze_symbol.assert_not_called()

    def test_bar_analysis_handles_errors_gracefully(self, market_data_service):
        """Test that errors in analysis don't crash the system."""
        symbol = 'AAPL'
        timestamp = datetime.now(UTC)

        with patch('src.core.services.market_data_service.OHLCVDataService') as mock_ohlcv_service:
            # Setup mock to raise exception
            mock_ohlcv_service.return_value.get_ohlcv_data.side_effect = Exception("Database error")

            # Trigger analysis (should not raise exception)
            try:
                market_data_service._trigger_bar_analysis_async(symbol, timestamp)
                time.sleep(2)
                # If we get here, error was handled gracefully
                assert True
            except Exception:
                pytest.fail("Analysis should handle errors gracefully")

    def test_database_write_triggers_analysis(self, market_data_service, sample_tick_data):
        """Test that successful database write triggers analysis."""
        with patch.object(market_data_service, '_db') as mock_db, \
             patch.object(market_data_service, '_trigger_bar_analysis_async') as mock_trigger:

            # Setup mock for successful database write
            mock_db.write_ohlcv_1min.return_value = True

            # Handle tick data
            market_data_service._handle_tick_data(sample_tick_data)

            # Verify analysis was triggered
            mock_trigger.assert_called_once()
            call_args = mock_trigger.call_args[0]
            assert call_args[0] == sample_tick_data.ticker

    def test_database_write_failure_does_not_trigger_analysis(self, market_data_service, sample_tick_data):
        """Test that failed database write does NOT trigger analysis."""
        with patch.object(market_data_service, '_db') as mock_db, \
             patch.object(market_data_service, '_trigger_bar_analysis_async') as mock_trigger:

            # Setup mock for failed database write
            mock_db.write_ohlcv_1min.return_value = False

            # Handle tick data
            market_data_service._handle_tick_data(sample_tick_data)

            # Verify analysis was NOT triggered
            mock_trigger.assert_not_called()

    def test_analysis_is_non_blocking(self, market_data_service):
        """Test that analysis trigger returns immediately (non-blocking)."""
        symbol = 'AAPL'
        timestamp = datetime.now(UTC)

        # Measure execution time
        start_time = time.time()
        market_data_service._trigger_bar_analysis_async(symbol, timestamp)
        execution_time = time.time() - start_time

        # Verify returns in <10ms (non-blocking)
        assert execution_time < 0.01, f"Analysis trigger took {execution_time*1000:.2f}ms (should be <10ms)"

    def test_cleanup_old_patterns_called(self, market_data_service, sample_ohlcv_data):
        """Test that old pattern cleanup is called during analysis."""
        symbol = 'AAPL'
        timestamp = datetime.now(UTC)

        with patch('src.core.services.market_data_service.OHLCVDataService') as mock_ohlcv_service, \
             patch('src.core.services.market_data_service.AnalysisService') as mock_analysis_service, \
             patch('src.core.services.market_data_service._cleanup_old_patterns') as mock_cleanup:

            # Setup mocks
            mock_ohlcv_service.return_value.get_ohlcv_data.return_value = sample_ohlcv_data
            mock_analysis_service.return_value.analyze_symbol.return_value = {
                'patterns': {},
                'indicators': {}
            }

            # Trigger analysis
            market_data_service._trigger_bar_analysis_async(symbol, timestamp)
            time.sleep(2)

            # Verify cleanup was called
            mock_cleanup.assert_called_once()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
