"""
Backtest Job Manager
Handles backtest job submission, tracking, and management for TickStockPL integration.

Sprint 10 Phase 3: Backtesting UI & Job Management
- Submit backtest jobs to TickStockPL via Redis
- Track job progress and status
- Manage job cancellation and cleanup
- Store job metadata and results
"""

import json
import logging
import time
import uuid
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

import redis

from src.infrastructure.database.tickstock_db import TickStockDatabase

logger = logging.getLogger(__name__)

class JobStatus(Enum):
    """Backtest job status enumeration."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class BacktestJobConfig:
    """Configuration for a backtest job."""
    symbols: list[str]
    start_date: str  # YYYY-MM-DD format
    end_date: str    # YYYY-MM-DD format
    patterns: list[str]
    initial_capital: float = 100000.0
    commission_rate: float = 0.001  # 0.1%
    slippage_rate: float = 0.0005   # 0.05%
    max_position_size: float = 0.1  # 10% of capital
    stop_loss_pct: float = 0.05     # 5% stop loss
    take_profit_pct: float = 0.10   # 10% take profit

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    def validate(self) -> tuple[bool, str]:
        """Validate configuration parameters."""
        if not self.symbols:
            return False, "At least one symbol must be specified"

        if len(self.symbols) > 50:
            return False, "Maximum 50 symbols allowed per backtest"

        if not self.patterns:
            return False, "At least one pattern must be specified"

        if self.initial_capital <= 0:
            return False, "Initial capital must be positive"

        if not (0 <= self.commission_rate <= 0.01):
            return False, "Commission rate must be between 0% and 1%"

        if not (0 <= self.slippage_rate <= 0.01):
            return False, "Slippage rate must be between 0% and 1%"

        try:
            # Validate date format
            from datetime import datetime
            start = datetime.strptime(self.start_date, '%Y-%m-%d')
            end = datetime.strptime(self.end_date, '%Y-%m-%d')

            if start >= end:
                return False, "End date must be after start date"

            # Check reasonable date range (not more than 5 years)
            if (end - start).days > 1825:
                return False, "Date range cannot exceed 5 years"

        except ValueError:
            return False, "Invalid date format. Use YYYY-MM-DD"

        return True, "Configuration valid"

@dataclass
class BacktestJob:
    """Represents a backtest job with metadata and status."""
    job_id: str
    user_id: str
    config: BacktestJobConfig
    status: JobStatus
    created_at: float
    started_at: float | None = None
    completed_at: float | None = None
    progress: float = 0.0
    current_symbol: str | None = None
    estimated_completion: float | None = None
    error_message: str | None = None
    results: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'job_id': self.job_id,
            'user_id': self.user_id,
            'config': self.config.to_dict(),
            'status': self.status.value,
            'created_at': self.created_at,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'progress': self.progress,
            'current_symbol': self.current_symbol,
            'estimated_completion': self.estimated_completion,
            'error_message': self.error_message,
            'results': self.results
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'BacktestJob':
        """Create BacktestJob from dictionary."""
        config_data = data['config']
        config = BacktestJobConfig(**config_data)

        return cls(
            job_id=data['job_id'],
            user_id=data['user_id'],
            config=config,
            status=JobStatus(data['status']),
            created_at=data['created_at'],
            started_at=data.get('started_at'),
            completed_at=data.get('completed_at'),
            progress=data.get('progress', 0.0),
            current_symbol=data.get('current_symbol'),
            estimated_completion=data.get('estimated_completion'),
            error_message=data.get('error_message'),
            results=data.get('results')
        )

class BacktestJobManager:
    """
    Manages backtest jobs for TickStockPL integration.
    
    Handles job submission, progress tracking, results retrieval,
    and job lifecycle management.
    """

    def __init__(self, redis_client: redis.Redis, tickstock_db: TickStockDatabase):
        """Initialize backtest job manager."""
        self.redis_client = redis_client
        self.tickstock_db = tickstock_db

        # Redis key patterns
        self.job_key_pattern = "tickstock:jobs:{job_id}"
        self.user_jobs_key_pattern = "tickstock:user_jobs:{user_id}"
        self.active_jobs_key = "tickstock:active_jobs"

        # Job statistics
        self.stats = {
            'jobs_submitted': 0,
            'jobs_completed': 0,
            'jobs_failed': 0,
            'jobs_cancelled': 0,
            'start_time': time.time()
        }

        logger.info("BACKTEST-JOB-MANAGER: Initialized successfully")

    def submit_job(self, user_id: str, config: BacktestJobConfig) -> tuple[bool, str, str | None]:
        """
        Submit a new backtest job to TickStockPL.
        
        Returns: (success, message, job_id)
        """
        try:
            # Validate configuration
            is_valid, validation_message = config.validate()
            if not is_valid:
                return False, f"Configuration invalid: {validation_message}", None

            # Generate unique job ID
            job_id = f"backtest_{int(time.time())}_{uuid.uuid4().hex[:8]}"

            # Create job object
            job = BacktestJob(
                job_id=job_id,
                user_id=user_id,
                config=config,
                status=JobStatus.QUEUED,
                created_at=time.time()
            )

            # Store job in Redis
            job_key = self.job_key_pattern.format(job_id=job_id)
            job_data = json.dumps(job.to_dict())

            # Use Redis pipeline for atomic operations
            pipe = self.redis_client.pipeline()

            # Store job data
            pipe.setex(job_key, 86400 * 7, job_data)  # 7 days TTL

            # Add to user's job list
            user_jobs_key = self.user_jobs_key_pattern.format(user_id=user_id)
            pipe.zadd(user_jobs_key, {job_id: time.time()})
            pipe.expire(user_jobs_key, 86400 * 30)  # 30 days TTL

            # Add to active jobs set
            pipe.zadd(self.active_jobs_key, {job_id: time.time()})

            # Execute pipeline
            pipe.execute()

            # Submit job to TickStockPL via Redis
            self._submit_to_tickstockpl(job)

            # Update statistics
            self.stats['jobs_submitted'] += 1

            logger.info(f"BACKTEST-JOB-MANAGER: Job {job_id} submitted for user {user_id}")
            return True, f"Backtest job {job_id} submitted successfully", job_id

        except Exception as e:
            logger.error(f"BACKTEST-JOB-MANAGER: Error submitting job: {e}")
            return False, f"Failed to submit job: {str(e)}", None

    def _submit_to_tickstockpl(self, job: BacktestJob):
        """Submit job to TickStockPL via Redis pub-sub."""
        try:
            # Create job message for TickStockPL
            job_message = {
                'type': 'backtest_job',
                'job_id': job.job_id,
                'user_id': job.user_id,
                'symbols': job.config.symbols,
                'start_date': job.config.start_date,
                'end_date': job.config.end_date,
                'patterns': job.config.patterns,
                'parameters': {
                    'initial_capital': job.config.initial_capital,
                    'commission_rate': job.config.commission_rate,
                    'slippage_rate': job.config.slippage_rate,
                    'max_position_size': job.config.max_position_size,
                    'stop_loss_pct': job.config.stop_loss_pct,
                    'take_profit_pct': job.config.take_profit_pct
                },
                'timestamp': time.time(),
                'source': 'tickstock_appv2'
            }

            # Publish to TickStockPL job queue
            message_json = json.dumps(job_message)
            self.redis_client.publish('tickstock.jobs.backtest', message_json)

            logger.info(f"BACKTEST-JOB-MANAGER: Job {job.job_id} published to TickStockPL")

        except Exception as e:
            logger.error(f"BACKTEST-JOB-MANAGER: Error publishing job to TickStockPL: {e}")
            raise

    def get_job(self, job_id: str) -> BacktestJob | None:
        """Retrieve job by ID."""
        try:
            job_key = self.job_key_pattern.format(job_id=job_id)
            job_data = self.redis_client.get(job_key)

            if not job_data:
                return None

            job_dict = json.loads(job_data)
            return BacktestJob.from_dict(job_dict)

        except Exception as e:
            logger.error(f"BACKTEST-JOB-MANAGER: Error retrieving job {job_id}: {e}")
            return None

    def get_user_jobs(self, user_id: str, limit: int = 50) -> list[BacktestJob]:
        """Get jobs for a specific user."""
        try:
            user_jobs_key = self.user_jobs_key_pattern.format(user_id=user_id)

            # Get job IDs ordered by creation time (most recent first)
            job_ids = self.redis_client.zrevrange(user_jobs_key, 0, limit - 1)

            jobs = []
            for job_id in job_ids:
                if isinstance(job_id, bytes):
                    job_id = job_id.decode('utf-8')

                job = self.get_job(job_id)
                if job:
                    jobs.append(job)

            logger.debug(f"BACKTEST-JOB-MANAGER: Retrieved {len(jobs)} jobs for user {user_id}")
            return jobs

        except Exception as e:
            logger.error(f"BACKTEST-JOB-MANAGER: Error retrieving jobs for user {user_id}: {e}")
            return []

    def update_job_progress(self, job_id: str, progress: float, current_symbol: str = None,
                          estimated_completion: float = None):
        """Update job progress from TickStockPL."""
        try:
            job = self.get_job(job_id)
            if not job:
                logger.warning(f"BACKTEST-JOB-MANAGER: Job {job_id} not found for progress update")
                return False

            # Update job status
            if job.status == JobStatus.QUEUED:
                job.status = JobStatus.RUNNING
                job.started_at = time.time()

            job.progress = progress
            if current_symbol:
                job.current_symbol = current_symbol
            if estimated_completion:
                job.estimated_completion = estimated_completion

            # Save updated job
            self._save_job(job)

            logger.debug(f"BACKTEST-JOB-MANAGER: Updated progress for job {job_id}: {progress:.1%}")
            return True

        except Exception as e:
            logger.error(f"BACKTEST-JOB-MANAGER: Error updating job progress: {e}")
            return False

    def complete_job(self, job_id: str, results: dict[str, Any], status: JobStatus = JobStatus.COMPLETED):
        """Mark job as completed with results."""
        try:
            job = self.get_job(job_id)
            if not job:
                logger.warning(f"BACKTEST-JOB-MANAGER: Job {job_id} not found for completion")
                return False

            # Update job status
            job.status = status
            job.completed_at = time.time()
            job.progress = 1.0
            job.results = results

            # Save updated job
            self._save_job(job)

            # Remove from active jobs
            self.redis_client.zrem(self.active_jobs_key, job_id)

            # Update statistics
            if status == JobStatus.COMPLETED:
                self.stats['jobs_completed'] += 1
            elif status == JobStatus.FAILED:
                self.stats['jobs_failed'] += 1

            logger.info(f"BACKTEST-JOB-MANAGER: Job {job_id} completed with status {status.value}")
            return True

        except Exception as e:
            logger.error(f"BACKTEST-JOB-MANAGER: Error completing job: {e}")
            return False

    def cancel_job(self, job_id: str, user_id: str) -> tuple[bool, str]:
        """Cancel a running job."""
        try:
            job = self.get_job(job_id)
            if not job:
                return False, "Job not found"

            # Check user permission
            if job.user_id != user_id:
                return False, "Permission denied"

            # Check if job can be cancelled
            if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                return False, f"Cannot cancel job with status {job.status.value}"

            # Update job status
            job.status = JobStatus.CANCELLED
            job.completed_at = time.time()

            # Save updated job
            self._save_job(job)

            # Remove from active jobs
            self.redis_client.zrem(self.active_jobs_key, job_id)

            # Send cancellation message to TickStockPL
            self._send_cancellation_to_tickstockpl(job_id)

            # Update statistics
            self.stats['jobs_cancelled'] += 1

            logger.info(f"BACKTEST-JOB-MANAGER: Job {job_id} cancelled by user {user_id}")
            return True, "Job cancelled successfully"

        except Exception as e:
            logger.error(f"BACKTEST-JOB-MANAGER: Error cancelling job: {e}")
            return False, f"Failed to cancel job: {str(e)}"

    def _send_cancellation_to_tickstockpl(self, job_id: str):
        """Send job cancellation message to TickStockPL."""
        try:
            cancel_message = {
                'type': 'cancel_job',
                'job_id': job_id,
                'timestamp': time.time(),
                'source': 'tickstock_appv2'
            }

            message_json = json.dumps(cancel_message)
            self.redis_client.publish('tickstock.jobs.cancel', message_json)

            logger.info(f"BACKTEST-JOB-MANAGER: Cancellation sent to TickStockPL for job {job_id}")

        except Exception as e:
            logger.error(f"BACKTEST-JOB-MANAGER: Error sending cancellation: {e}")

    def _save_job(self, job: BacktestJob):
        """Save job to Redis."""
        try:
            job_key = self.job_key_pattern.format(job_id=job.job_id)
            job_data = json.dumps(job.to_dict())
            self.redis_client.setex(job_key, 86400 * 7, job_data)  # 7 days TTL

        except Exception as e:
            logger.error(f"BACKTEST-JOB-MANAGER: Error saving job: {e}")
            raise

    def get_available_symbols(self) -> list[str]:
        """Get available symbols for backtesting."""
        try:
            if self.tickstock_db:
                return self.tickstock_db.get_symbols_for_dropdown()
            # Fallback list if database is not available
            return ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN', 'META', 'NVDA', 'SPY', 'QQQ', 'IWM']

        except Exception as e:
            logger.error(f"BACKTEST-JOB-MANAGER: Error getting symbols: {e}")
            return []

    def get_available_patterns(self) -> list[str]:
        """Get available patterns for backtesting."""
        # These are the patterns from Sprint 5-9 that work with TickStockPL
        return [
            'Doji',
            'Hammer',
            'ShootingStar',
            'Engulfing',
            'Harami',
            'MorningStar',
            'EveningStar',
            'ThreeWhiteSoldiers',
            'ThreeBlackCrows',
            'PiercingLine',
            'DarkCloudCover'
        ]

    def get_active_jobs(self) -> list[BacktestJob]:
        """Get all currently active jobs."""
        try:
            # Get active job IDs
            job_ids = self.redis_client.zrange(self.active_jobs_key, 0, -1)

            active_jobs = []
            for job_id in job_ids:
                if isinstance(job_id, bytes):
                    job_id = job_id.decode('utf-8')

                job = self.get_job(job_id)
                if job and job.status in [JobStatus.QUEUED, JobStatus.RUNNING]:
                    active_jobs.append(job)
                else:
                    # Clean up stale active job reference
                    self.redis_client.zrem(self.active_jobs_key, job_id)

            return active_jobs

        except Exception as e:
            logger.error(f"BACKTEST-JOB-MANAGER: Error getting active jobs: {e}")
            return []

    def cleanup_expired_jobs(self):
        """Clean up expired job references."""
        try:
            # Clean up active jobs that no longer exist
            job_ids = self.redis_client.zrange(self.active_jobs_key, 0, -1)

            for job_id in job_ids:
                if isinstance(job_id, bytes):
                    job_id = job_id.decode('utf-8')

                job_key = self.job_key_pattern.format(job_id=job_id)
                if not self.redis_client.exists(job_key):
                    self.redis_client.zrem(self.active_jobs_key, job_id)

            logger.debug("BACKTEST-JOB-MANAGER: Cleaned up expired job references")

        except Exception as e:
            logger.error(f"BACKTEST-JOB-MANAGER: Error cleaning up expired jobs: {e}")

    def get_stats(self) -> dict[str, Any]:
        """Get job manager statistics."""
        runtime = time.time() - self.stats['start_time']
        active_jobs_count = len(self.get_active_jobs())

        return {
            **self.stats,
            'runtime_seconds': round(runtime, 1),
            'active_jobs': active_jobs_count,
            'jobs_per_hour': round(self.stats['jobs_submitted'] / max(runtime / 3600, 1), 2),
            'success_rate': round(
                self.stats['jobs_completed'] / max(self.stats['jobs_submitted'], 1) * 100, 1
            ) if self.stats['jobs_submitted'] > 0 else 0
        }
