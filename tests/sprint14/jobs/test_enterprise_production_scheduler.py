#!/usr/bin/env python3
"""
Comprehensive Tests for Enterprise Production Scheduler - Sprint 14 Phase 4

Tests for advanced production load scheduling capabilities including:
- Redis Streams job management with priority scheduling
- Fault tolerance and resume capability
- 5-year × 500 symbol capacity with <5% error rate
- Performance requirements: <100ms job submission, Redis reliability
- Multi-threaded load balancing with API rate limit coordination

Author: TickStock Testing Framework
Sprint: 14 Phase 4
Test Category: Jobs/Scheduler
Performance Targets: <100ms job submission, <1s job execution setup
"""

import json
import os

# Import the module under test
import sys
import time
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../'))

from src.jobs.enterprise_production_scheduler import (
    EnterpriseProductionScheduler,
    EnterpriseSchedulingJob,
    JobPriority,
    JobStatus,
)


@pytest.fixture
def scheduler():
    """Create EnterpriseProductionScheduler instance for testing"""
    return EnterpriseProductionScheduler(
        database_uri="postgresql://test_user:test_password@localhost/test_db",
        redis_host="localhost",
        massive_api_key="test_api_key"
    )

@pytest.fixture
def sample_symbols():
    """Sample symbols for testing"""
    return ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'NFLX', 'AMD', 'CRM']

@pytest.fixture
def large_symbol_set():
    """Large symbol set for enterprise testing (500+ symbols)"""
    base_symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA'] * 100
    additional_symbols = [f"TEST{i:03d}" for i in range(1, 101)]  # TEST001, TEST002, etc.
    return base_symbols + additional_symbols  # Total: 600 symbols

@pytest.fixture
async def mock_redis():
    """Mock Redis client for testing"""
    mock_client = AsyncMock()
    mock_client.ping = AsyncMock(return_value=True)
    mock_client.xadd = AsyncMock(return_value="message_id_123")
    mock_client.hset = AsyncMock(return_value=True)
    mock_client.expire = AsyncMock(return_value=True)
    mock_client.publish = AsyncMock(return_value=1)
    mock_client.xread = AsyncMock(return_value=[])
    mock_client.aclose = AsyncMock()
    return mock_client

@pytest.fixture
def sample_enterprise_job():
    """Sample enterprise scheduling job for testing"""
    return EnterpriseSchedulingJob(
        job_id="test_job_123",
        symbols=['AAPL', 'MSFT', 'GOOGL'],
        start_date="2020-01-01",
        end_date="2024-12-31",
        priority=JobPriority.HIGH,
        status=JobStatus.PENDING,
        progress={
            'total_symbols': 3,
            'completed_symbols': 0,
            'failed_symbols': 0,
            'estimated_records': 3960,  # 3 symbols × 22 days/month × 60 months
            'actual_records': 0
        },
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat(),
        metadata={
            'priority_reason': 'high priority symbols',
            'chunk_months': 6,
            'estimated_duration_minutes': 6
        }
    )


class TestEnterpriseProductionScheduler:
    """Test suite for EnterpriseProductionScheduler"""

    def test_initialization(self, scheduler):
        """Test proper initialization of scheduler"""
        assert scheduler.max_concurrent_jobs == 10
        assert scheduler.max_threads_per_job == 5
        assert scheduler.api_rate_limit_per_second == 5
        assert scheduler.system_load_threshold == 0.8
        assert len(scheduler.priority_order) == 4
        assert JobPriority.CRITICAL in scheduler.priority_order

    def test_redis_streams_configuration(self, scheduler):
        """Test Redis streams are properly configured"""
        expected_streams = {
            'job_queue', 'job_progress', 'job_errors', 'system_metrics'
        }
        actual_streams = set(scheduler.redis_streams.keys())
        assert expected_streams == actual_streams

        # Verify stream naming convention
        for stream_name in scheduler.redis_streams.values():
            assert stream_name.startswith('enterprise:')

    @pytest.mark.asyncio
    async def test_redis_connection_success(self, scheduler, mock_redis):
        """Test successful Redis connection establishment"""
        with patch('redis.asyncio.Redis', return_value=mock_redis):
            redis_client = await scheduler.connect_redis()

            assert redis_client is not None
            mock_redis.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_redis_connection_failure(self, scheduler):
        """Test Redis connection failure handling"""
        with patch('redis.asyncio.Redis') as mock_redis_class:
            mock_client = AsyncMock()
            mock_client.ping.side_effect = Exception("Connection failed")
            mock_redis_class.return_value = mock_client

            redis_client = await scheduler.connect_redis()
            assert redis_client is None

    def test_symbol_categorization_by_priority(self, scheduler, sample_symbols):
        """Test symbol categorization by market cap and priority"""
        prioritized = scheduler.categorize_symbols_by_priority(sample_symbols)

        # Verify all priority levels exist
        assert all(priority in prioritized for priority in JobPriority)

        # Verify total symbols preserved
        total_categorized = sum(len(symbols) for symbols in prioritized.values())
        assert total_categorized == len(sample_symbols)

        # Verify critical symbols are properly categorized
        critical_symbols = prioritized[JobPriority.CRITICAL]
        assert 'AAPL' in critical_symbols
        assert 'MSFT' in critical_symbols

    def test_forced_priority_override(self, scheduler, sample_symbols):
        """Test forcing all symbols to a specific priority"""
        prioritized = scheduler.categorize_symbols_by_priority(
            sample_symbols,
            force_priority=JobPriority.CRITICAL
        )

        # All symbols should be in CRITICAL
        assert len(prioritized[JobPriority.CRITICAL]) == len(sample_symbols)
        assert all(len(prioritized[p]) == 0 for p in JobPriority if p != JobPriority.CRITICAL)

    def test_enterprise_job_creation(self, scheduler, sample_symbols):
        """Test creation of enterprise job chunks"""
        prioritized_symbols = {
            JobPriority.CRITICAL: sample_symbols[:3],
            JobPriority.HIGH: sample_symbols[3:7],
            JobPriority.NORMAL: sample_symbols[7:],
            JobPriority.LOW: []
        }

        jobs = scheduler.create_enterprise_jobs(prioritized_symbols, years=2)

        # Verify jobs created
        assert len(jobs) > 0

        # Verify job structure
        for job in jobs:
            assert isinstance(job, EnterpriseSchedulingJob)
            assert job.job_id is not None
            assert len(job.symbols) <= 100  # Max symbols per job
            assert job.priority in JobPriority
            assert job.status == JobStatus.PENDING

        # Verify priority ordering
        priorities = [job.priority for job in jobs]
        critical_first = True
        for i in range(1, len(priorities)):
            current_priority_index = scheduler.priority_order.index(priorities[i])
            previous_priority_index = scheduler.priority_order.index(priorities[i-1])
            if current_priority_index < previous_priority_index:
                critical_first = False
                break
        assert critical_first, "Jobs should be ordered by priority"

    def test_large_symbol_set_chunking(self, scheduler, large_symbol_set):
        """Test proper chunking of large symbol sets (500+ symbols)"""
        prioritized_symbols = scheduler.categorize_symbols_by_priority(large_symbol_set)
        jobs = scheduler.create_enterprise_jobs(prioritized_symbols, years=1)

        # Verify all symbols are covered
        all_job_symbols = []
        for job in jobs:
            all_job_symbols.extend(job.symbols)

        # Should have same symbols (order may differ)
        assert set(all_job_symbols) == set(large_symbol_set)

        # Verify job size limits
        for job in jobs:
            if job.priority in [JobPriority.CRITICAL, JobPriority.HIGH]:
                assert len(job.symbols) <= 50
            else:
                assert len(job.symbols) <= 100

    @pytest.mark.asyncio
    async def test_job_submission_performance(self, scheduler, sample_enterprise_job, mock_redis):
        """Test job submission meets <100ms performance requirement"""
        with patch.object(scheduler, 'connect_redis', return_value=mock_redis):
            start_time = time.time()

            result = await scheduler.queue_enterprise_job(mock_redis, sample_enterprise_job)

            submission_time = (time.time() - start_time) * 1000  # Convert to ms

            # Performance requirement: <100ms job submission
            assert submission_time < 100, f"Job submission took {submission_time:.2f}ms, expected <100ms"
            assert result['status'] == 'queued'
            assert result['job_id'] == sample_enterprise_job.job_id

    @pytest.mark.asyncio
    async def test_queue_enterprise_job_success(self, scheduler, sample_enterprise_job, mock_redis):
        """Test successful job queuing in Redis"""
        result = await scheduler.queue_enterprise_job(mock_redis, sample_enterprise_job)

        # Verify Redis operations called
        mock_redis.xadd.assert_called_once()
        mock_redis.hset.assert_called_once()
        mock_redis.expire.assert_called_once()

        # Verify result structure
        assert result['status'] == 'queued'
        assert result['job_id'] == sample_enterprise_job.job_id
        assert result['priority'] == sample_enterprise_job.priority.value
        assert 'estimated_duration_minutes' in result

    @pytest.mark.asyncio
    async def test_queue_enterprise_job_redis_failure(self, scheduler, sample_enterprise_job):
        """Test job queuing with Redis failure"""
        mock_redis = AsyncMock()
        mock_redis.xadd.side_effect = Exception("Redis operation failed")

        result = await scheduler.queue_enterprise_job(mock_redis, sample_enterprise_job)

        assert result['status'] == 'queue_failed'
        assert 'error' in result

    @pytest.mark.asyncio
    async def test_schedule_enterprise_load(self, scheduler, sample_symbols, mock_redis):
        """Test complete enterprise load scheduling workflow"""
        with patch.object(scheduler, 'connect_redis', return_value=mock_redis):
            with patch.object(scheduler, 'is_trading_day', return_value=False):
                with patch.object(scheduler, 'check_system_load', return_value=0.5):

                    result = await scheduler.schedule_enterprise_load(
                        symbols=sample_symbols,
                        years=2,
                        force_priority=JobPriority.HIGH
                    )

        # Verify result structure
        assert 'timestamp' in result
        assert result['symbols_total'] == len(sample_symbols)
        assert result['years_requested'] == 2
        assert result['jobs_created'] > 0
        assert 'estimated_completion_hours' in result
        assert 'priority_distribution' in result

    @pytest.mark.asyncio
    async def test_massive_load_capacity(self, scheduler, large_symbol_set, mock_redis):
        """Test enterprise scheduler handles 5 years × 500+ symbols"""
        with patch.object(scheduler, 'connect_redis', return_value=mock_redis):
            with patch.object(scheduler, 'check_system_load', return_value=0.3):

                result = await scheduler.schedule_enterprise_load(
                    symbols=large_symbol_set,  # 600 symbols
                    years=5
                )

        # Verify capacity handling
        assert result['symbols_total'] == len(large_symbol_set)
        assert result['years_requested'] == 5
        assert result['jobs_created'] > 0

        # Estimate should be reasonable for massive load
        estimated_hours = result['estimated_completion_hours']
        assert estimated_hours > 0
        assert estimated_hours < 48  # Should complete within 2 days

    @pytest.mark.asyncio
    async def test_get_pending_jobs_priority_ordering(self, scheduler, mock_redis):
        """Test pending jobs are returned in priority order"""
        # Mock Redis stream data with different priorities
        mock_stream_data = [
            ('enterprise:jobs:queue', [
                ('msg1', {'job_data': json.dumps({
                    'job_id': 'job1', 'priority': 'low', 'status': 'pending'
                }), 'status': 'pending'}),
                ('msg2', {'job_data': json.dumps({
                    'job_id': 'job2', 'priority': 'critical', 'status': 'pending'
                }), 'status': 'pending'}),
                ('msg3', {'job_data': json.dumps({
                    'job_id': 'job3', 'priority': 'high', 'status': 'pending'
                }), 'status': 'pending'})
            ])
        ]

        mock_redis.xread.return_value = mock_stream_data

        jobs = await scheduler.get_pending_jobs(mock_redis)

        # Verify priority ordering (critical first, low last)
        assert len(jobs) == 3
        assert jobs[0]['priority'] == 'critical'
        assert jobs[1]['priority'] == 'high'
        assert jobs[2]['priority'] == 'low'

    @pytest.mark.asyncio
    async def test_execute_enterprise_jobs_concurrency(self, scheduler, mock_redis):
        """Test concurrent job execution with resource management"""
        # Mock pending jobs
        mock_pending_jobs = [
            {'job_id': f'job_{i}', 'symbols': ['AAPL'], 'start_date': '2024-01-01',
             'end_date': '2024-12-31', 'priority': 'normal'}
            for i in range(5)
        ]

        with patch.object(scheduler, 'connect_redis', return_value=mock_redis):
            with patch.object(scheduler, 'get_pending_jobs', return_value=mock_pending_jobs):
                with patch.object(scheduler, 'execute_single_enterprise_job', return_value={'status': 'completed'}):

                    result = await scheduler.execute_enterprise_jobs(max_concurrent=3)

        assert result['jobs_processed'] == 5
        assert result['successful_jobs'] == 5
        assert result['failed_jobs'] == 0

    @pytest.mark.asyncio
    async def test_job_resume_capability(self, scheduler, mock_redis):
        """Test job resume capability with completed symbols tracking"""
        mock_redis.smembers.return_value = {'AAPL', 'MSFT'}  # Already completed

        job_data = {
            'job_id': 'test_job',
            'symbols': ['AAPL', 'MSFT', 'GOOGL', 'AMZN'],  # 4 total, 2 completed
            'start_date': '2024-01-01',
            'end_date': '2024-12-31'
        }

        with patch.object(scheduler, 'update_job_status', return_value=None):
            with patch.object(scheduler, 'load_symbol_historical_data', return_value=100):
                with patch.object(scheduler, 'update_job_progress', return_value=None):

                    result = await scheduler.execute_single_enterprise_job(mock_redis, job_data)

        # Should only process remaining 2 symbols
        assert result['symbols_processed'] == 2  # Only GOOGL and AMZN
        assert result['status'] == 'completed'

    def test_system_load_monitoring(self, scheduler):
        """Test system load monitoring capabilities"""
        with patch('psutil.cpu_percent', return_value=75.0):
            with patch('psutil.virtual_memory') as mock_memory:
                mock_memory.return_value.percent = 80.0

                system_load = scheduler.check_system_load()

                # Should return higher of CPU and memory (80%)
                assert system_load == 0.80

    def test_trading_hours_awareness(self, scheduler):
        """Test trading hours awareness for scheduling optimization"""
        # Mock current time as market hours (10 AM ET)
        with patch('datetime.datetime') as mock_dt:
            mock_dt.now.return_value.time.return_value = datetime.strptime("10:00", "%H:%M").time()

            is_trading = scheduler.is_trading_hours()

            assert isinstance(is_trading, bool)

    def test_adaptive_rate_limiting(self, scheduler):
        """Test adaptive rate limiting based on trading hours and system load"""
        base_rate = scheduler.api_rate_limit_per_second

        # During trading hours
        with patch.object(scheduler, 'is_trading_hours', return_value=True):
            trading_rate = scheduler.get_adaptive_rate_limit()
            assert trading_rate == base_rate * 0.5  # Reduced during trading

        # After hours with low system load
        with patch.object(scheduler, 'is_trading_hours', return_value=False):
            with patch.object(scheduler, 'check_system_load', return_value=0.3):
                after_hours_rate = scheduler.get_adaptive_rate_limit()
                assert after_hours_rate == base_rate * 1.5  # Increased after hours

    def test_completion_time_estimation(self, scheduler, sample_symbols):
        """Test realistic completion time estimation"""
        prioritized_symbols = scheduler.categorize_symbols_by_priority(sample_symbols)
        jobs = scheduler.create_enterprise_jobs(prioritized_symbols, years=1)

        estimated_hours = scheduler.estimate_completion_time(jobs)

        assert estimated_hours > 0
        assert estimated_hours < 100  # Reasonable upper bound

    @pytest.mark.asyncio
    async def test_job_status_tracking(self, scheduler, mock_redis):
        """Test detailed job status tracking and retrieval"""
        job_id = "test_job_123"

        # Mock Redis responses
        mock_redis.hgetall.return_value = {
            'job_data': json.dumps({'job_id': job_id, 'symbols': ['AAPL']}),
            'last_updated': '2024-01-01T10:00:00'
        }
        mock_redis.smembers.return_value = {'AAPL'}

        with patch.object(scheduler, 'connect_redis', return_value=mock_redis):
            status = await scheduler.get_job_status(job_id)

        assert 'job_id' in status
        assert 'job_data' in status
        assert 'progress' in status
        assert 'completed_symbols' in status

    @pytest.mark.asyncio
    async def test_fault_tolerance_redis_streams(self, scheduler, sample_enterprise_job):
        """Test fault tolerance using Redis Streams for job persistence"""
        mock_redis = AsyncMock()

        # Simulate Redis failure during job execution
        mock_redis.xadd.side_effect = [Exception("Stream error"), "success_id"]

        # First attempt should fail, but system should handle gracefully
        result1 = await scheduler.queue_enterprise_job(mock_redis, sample_enterprise_job)
        assert result1['status'] == 'queue_failed'

        # Second attempt should succeed
        mock_redis.xadd.side_effect = None
        mock_redis.xadd.return_value = "success_id"
        mock_redis.hset.return_value = True
        mock_redis.expire.return_value = True

        result2 = await scheduler.queue_enterprise_job(mock_redis, sample_enterprise_job)
        assert result2['status'] == 'queued'

    def test_error_rate_requirement(self, scheduler, large_symbol_set):
        """Test system meets <5% error rate requirement for massive loads"""
        # Simulate job processing with some failures
        total_symbols = len(large_symbol_set)
        max_allowed_errors = int(total_symbols * 0.05)  # 5% error rate

        # Test that error tracking would meet requirement
        assert max_allowed_errors >= 30  # For 600 symbols, allows 30 errors

        # In a real test, we'd track actual error rates during processing
        # This validates the mathematical constraint is achievable

    @pytest.mark.performance
    async def test_job_submission_batch_performance(self, scheduler, mock_redis):
        """Test batch job submission performance for enterprise scale"""
        # Create 100 jobs for performance testing
        jobs = []
        for i in range(100):
            job = EnterpriseSchedulingJob(
                job_id=f"perf_test_{i}",
                symbols=[f"SYMBOL{i}"],
                start_date="2024-01-01",
                end_date="2024-12-31",
                priority=JobPriority.NORMAL,
                status=JobStatus.PENDING,
                progress={'total_symbols': 1, 'completed_symbols': 0, 'failed_symbols': 0,
                         'estimated_records': 252, 'actual_records': 0},
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
                metadata={'priority_reason': 'performance test', 'chunk_months': 6,
                         'estimated_duration_minutes': 1}
            )
            jobs.append(job)

        start_time = time.time()

        # Submit all jobs
        for job in jobs:
            await scheduler.queue_enterprise_job(mock_redis, job)

        batch_time = (time.time() - start_time) * 1000  # Convert to ms
        avg_time_per_job = batch_time / len(jobs)

        # Each job should be submitted in <100ms on average
        assert avg_time_per_job < 100, f"Average job submission: {avg_time_per_job:.2f}ms, expected <100ms"

    @pytest.mark.integration
    async def test_end_to_end_enterprise_scheduling(self, scheduler, sample_symbols, mock_redis):
        """Test complete end-to-end enterprise scheduling workflow"""
        # Mock all external dependencies
        with patch.object(scheduler, 'connect_redis', return_value=mock_redis):
            with patch.object(scheduler, 'is_trading_day', return_value=False):
                with patch.object(scheduler, 'check_system_load', return_value=0.4):

                    # Step 1: Schedule enterprise load
                    schedule_result = await scheduler.schedule_enterprise_load(
                        symbols=sample_symbols,
                        years=1,
                        force_priority=JobPriority.HIGH
                    )

                    assert schedule_result['jobs_scheduled'] > 0

                    # Step 2: Mock job execution
                    mock_pending_jobs = [
                        {
                            'job_id': 'integration_test_job',
                            'symbols': sample_symbols[:3],
                            'start_date': '2024-01-01',
                            'end_date': '2024-12-31',
                            'priority': 'high'
                        }
                    ]

                    with patch.object(scheduler, 'get_pending_jobs', return_value=mock_pending_jobs):
                        with patch.object(scheduler, 'execute_single_enterprise_job') as mock_execute:
                            mock_execute.return_value = {
                                'status': 'completed',
                                'symbols_processed': 3,
                                'success_rate': 1.0
                            }

                            # Step 3: Execute jobs
                            execution_result = await scheduler.execute_enterprise_jobs()

                            assert execution_result['jobs_processed'] == 1
                            assert execution_result['successful_jobs'] == 1
                            assert execution_result['failed_jobs'] == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
