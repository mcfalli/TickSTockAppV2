"""
Unit tests for ImportAnalysisBridge (Sprint 75 Phase 2)

Tests the automatic analysis triggering when historical imports complete.
"""

import json
import pytest
import time
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock, call

from src.jobs.import_analysis_bridge import ImportAnalysisBridge


class TestImportAnalysisBridge:
    """Test suite for ImportAnalysisBridge functionality."""

    @pytest.fixture
    def mock_app(self):
        """Create mock Flask app."""
        app = Mock()
        app._get_current_object = Mock(return_value=app)
        app.app_context = MagicMock()
        return app

    @pytest.fixture
    def mock_redis_client(self):
        """Create mock Redis client."""
        return Mock()

    @pytest.fixture
    def bridge(self, mock_app, mock_redis_client):
        """Create ImportAnalysisBridge instance."""
        return ImportAnalysisBridge(mock_app, mock_redis_client)

    def test_bridge_initialization(self, bridge, mock_app, mock_redis_client):
        """Test that bridge initializes correctly."""
        assert bridge.app == mock_app
        assert bridge.redis_client == mock_redis_client
        assert bridge.running is False
        assert bridge._thread is None
        assert len(bridge._processed_jobs) == 0
        assert bridge._poll_interval == 5

    def test_bridge_start_stop(self, bridge):
        """Test bridge start/stop lifecycle."""
        # Start bridge
        bridge.start()
        assert bridge.running is True
        assert bridge._thread is not None
        assert bridge._thread.is_alive()

        # Stop bridge
        bridge.stop()
        assert bridge.running is False

        # Wait for thread to finish
        if bridge._thread:
            bridge._thread.join(timeout=2)

    def test_bridge_start_when_already_running(self, bridge):
        """Test that starting already-running bridge logs warning."""
        bridge.start()
        assert bridge.running is True

        # Try to start again
        with patch('src.jobs.import_analysis_bridge.logger') as mock_logger:
            bridge.start()
            mock_logger.warning.assert_called_once()

        bridge.stop()

    def test_get_job_status_string_format(self, bridge, mock_redis_client):
        """Test getting job status from Redis string format (TickStockPL)."""
        job_key = 'tickstock.jobs.status:test-job-123'
        job_status = {
            'status': 'completed',
            'run_analysis_after_import': 'true',
            'symbols': ['AAPL', 'MSFT'],
            'universe_key': 'nasdaq100'
        }

        mock_redis_client.type.return_value = 'string'
        mock_redis_client.get.return_value = json.dumps(job_status)

        result = bridge._get_job_status(job_key)

        assert result == job_status
        mock_redis_client.type.assert_called_once_with(job_key)
        mock_redis_client.get.assert_called_once_with(job_key)

    def test_get_job_status_hash_format(self, bridge, mock_redis_client):
        """Test getting job status from Redis hash format (AppV2)."""
        job_key = 'job:status:test-job-456'
        job_status = {
            'status': 'completed',
            'run_analysis_after_import': 'true',
            'symbols': ['TSLA', 'NVDA']
        }

        mock_redis_client.type.return_value = 'hash'
        mock_redis_client.hgetall.return_value = job_status

        result = bridge._get_job_status(job_key)

        assert result == job_status
        mock_redis_client.type.assert_called_once_with(job_key)
        mock_redis_client.hgetall.assert_called_once_with(job_key)

    def test_get_job_status_bytes_decoding(self, bridge, mock_redis_client):
        """Test that bytes are properly decoded to strings."""
        job_key = 'tickstock.jobs.status:test-job-789'
        job_status_bytes = json.dumps({
            'status': 'completed',
            'run_analysis_after_import': 'true'
        }).encode('utf-8')

        mock_redis_client.type.return_value = b'string'
        mock_redis_client.get.return_value = job_status_bytes

        result = bridge._get_job_status(job_key)

        assert result['status'] == 'completed'
        assert result['run_analysis_after_import'] == 'true'

    def test_should_trigger_analysis_when_completed_and_flag_true(self, bridge):
        """Test analysis triggers when job completed and run_analysis=true."""
        job_status = {
            'status': 'completed',
            'run_analysis_after_import': 'true'
        }

        assert bridge._should_trigger_analysis(job_status) is True

    def test_should_trigger_analysis_when_completed_and_flag_false(self, bridge):
        """Test analysis NOT triggered when run_analysis=false."""
        job_status = {
            'status': 'completed',
            'run_analysis_after_import': 'false'
        }

        assert bridge._should_trigger_analysis(job_status) is False

    def test_should_trigger_analysis_when_not_completed(self, bridge):
        """Test analysis NOT triggered when job not completed."""
        job_status = {
            'status': 'running',
            'run_analysis_after_import': 'true'
        }

        assert bridge._should_trigger_analysis(job_status) is False

    def test_should_trigger_analysis_boolean_flag(self, bridge):
        """Test analysis trigger with boolean flag (not string)."""
        job_status = {
            'status': 'completed',
            'run_analysis_after_import': True  # Boolean, not string
        }

        assert bridge._should_trigger_analysis(job_status) is True

    def test_check_completed_jobs_processes_job(self, bridge, mock_redis_client):
        """Test that completed jobs with flag are processed."""
        job_id = 'test-job-abc123'
        job_key = f'tickstock.jobs.status:{job_id}'

        # Mock Redis scan to return one job
        mock_redis_client.scan_iter.return_value = [job_key]
        mock_redis_client.type.return_value = 'string'
        mock_redis_client.get.return_value = json.dumps({
            'status': 'completed',
            'run_analysis_after_import': 'true',
            'symbols': ['AAPL', 'MSFT'],
            'universe_key': 'nasdaq100'
        })

        # Mock _trigger_analysis_for_job
        with patch.object(bridge, '_trigger_analysis_for_job') as mock_trigger:
            bridge._check_completed_jobs()

            # Verify trigger was called
            mock_trigger.assert_called_once()
            assert job_id in bridge._processed_jobs

    def test_check_completed_jobs_skips_already_processed(self, bridge, mock_redis_client):
        """Test that already-processed jobs are skipped."""
        job_id = 'test-job-xyz789'
        job_key = f'tickstock.jobs.status:{job_id}'

        # Mark job as already processed
        bridge._processed_jobs.add(job_id)

        # Mock Redis scan
        mock_redis_client.scan_iter.return_value = [job_key]

        # Mock _trigger_analysis_for_job
        with patch.object(bridge, '_trigger_analysis_for_job') as mock_trigger:
            bridge._check_completed_jobs()

            # Verify trigger was NOT called
            mock_trigger.assert_not_called()

    def test_trigger_analysis_for_job_success(self, bridge, mock_app, mock_redis_client):
        """Test successful analysis job triggering."""
        job_id = 'import-job-123'
        job_status = {
            'status': 'completed',
            'run_analysis_after_import': 'true',
            'symbols': ['AAPL', 'MSFT', 'GOOGL'],
            'universe_key': 'nasdaq100',
            'timeframe': 'daily'
        }

        # Mock Flask context
        mock_context = MagicMock()
        mock_app.app_context.return_value.__enter__.return_value = mock_context

        # Mock active_jobs dict
        mock_active_jobs = {}

        with patch('src.jobs.import_analysis_bridge.run_analysis_job') as mock_run_analysis, \
             patch('src.jobs.import_analysis_bridge.active_jobs', mock_active_jobs), \
             patch('src.jobs.import_analysis_bridge.threading.Thread') as mock_thread:

            bridge._trigger_analysis_for_job(job_id, job_status)

            # Verify analysis job was created
            assert len(mock_active_jobs) == 1

            # Get the created job
            analysis_job = list(mock_active_jobs.values())[0]
            assert analysis_job['symbols'] == ['AAPL', 'MSFT', 'GOOGL']
            assert analysis_job['analysis_type'] == 'both'
            assert analysis_job['timeframe'] == 'daily'
            assert analysis_job['created_by'] == 'import_analysis_bridge'

            # Verify thread was started
            mock_thread.assert_called_once()
            mock_thread.return_value.start.assert_called_once()

    def test_trigger_analysis_loads_symbols_from_universe(self, bridge, mock_app):
        """Test that symbols are loaded from universe if not in job_status."""
        job_id = 'import-job-456'
        job_status = {
            'status': 'completed',
            'run_analysis_after_import': 'true',
            'universe_key': 'SPY',  # Universe key without symbols
            'timeframe': 'daily'
        }

        # Mock Flask context
        mock_context = MagicMock()
        mock_app.app_context.return_value.__enter__.return_value = mock_context

        # Mock RelationshipCache
        mock_cache = Mock()
        mock_cache.get_universe_symbols.return_value = ['AAPL', 'MSFT', 'GOOGL', 'AMZN']

        mock_active_jobs = {}

        with patch('src.jobs.import_analysis_bridge.get_relationship_cache', return_value=mock_cache), \
             patch('src.jobs.import_analysis_bridge.active_jobs', mock_active_jobs), \
             patch('src.jobs.import_analysis_bridge.threading.Thread'):

            bridge._trigger_analysis_for_job(job_id, job_status)

            # Verify universe was queried
            mock_cache.get_universe_symbols.assert_called_once_with('SPY')

            # Verify job was created with symbols from universe
            assert len(mock_active_jobs) == 1
            analysis_job = list(mock_active_jobs.values())[0]
            assert analysis_job['symbols'] == ['AAPL', 'MSFT', 'GOOGL', 'AMZN']

    def test_trigger_analysis_handles_no_symbols(self, bridge, mock_app):
        """Test graceful handling when no symbols found."""
        job_id = 'import-job-789'
        job_status = {
            'status': 'completed',
            'run_analysis_after_import': 'true',
            'timeframe': 'daily'
            # No symbols, no universe_key
        }

        # Mock Flask context
        mock_context = MagicMock()
        mock_app.app_context.return_value.__enter__.return_value = mock_context

        with patch('src.jobs.import_analysis_bridge.logger') as mock_logger:
            bridge._trigger_analysis_for_job(job_id, job_status)

            # Verify warning was logged
            mock_logger.warning.assert_called_once()
            assert 'No symbols found' in str(mock_logger.warning.call_args)

    def test_trigger_analysis_handles_errors(self, bridge, mock_app):
        """Test error handling in analysis triggering."""
        job_id = 'import-job-error'
        job_status = {
            'status': 'completed',
            'run_analysis_after_import': 'true',
            'symbols': ['AAPL']
        }

        # Mock Flask context to raise exception
        mock_app.app_context.side_effect = Exception("Database error")

        with patch('src.jobs.import_analysis_bridge.logger') as mock_logger:
            bridge._trigger_analysis_for_job(job_id, job_status)

            # Verify error was logged
            mock_logger.error.assert_called_once()
            assert 'Failed to trigger analysis' in str(mock_logger.error.call_args)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
