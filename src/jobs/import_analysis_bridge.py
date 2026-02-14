"""
Import Analysis Bridge - Sprint 75 Phase 2

Monitors historical data import jobs and automatically triggers pattern/indicator
analysis when imports complete (if run_analysis_after_import flag is set).

Architecture:
- Background thread polls Redis job status every 5 seconds
- Detects completed import jobs with run_analysis_after_import=true
- Auto-submits analysis jobs via admin_process_analysis workflow
- Prevents duplicate analysis job submissions
- Graceful start/stop lifecycle
"""

import json
import logging
import threading
import time
from datetime import datetime

logger = logging.getLogger(__name__)


class ImportAnalysisBridge:
    """
    Background service that monitors historical data import jobs and automatically
    triggers analysis when requested.

    Sprint 75 Phase 2: Historical Import Integration
    """

    def __init__(self, app, redis_client):
        """
        Initialize ImportAnalysisBridge.

        Args:
            app: Flask application instance (for establishing Flask context)
            redis_client: Redis client for monitoring job status
        """
        self.app = app
        self.redis_client = redis_client
        self.running = False
        self._thread = None
        self._processed_jobs = set()  # Track job IDs to prevent duplicate processing
        self._poll_interval = 5  # Poll every 5 seconds

        logger.info("ImportAnalysisBridge initialized")

    def start(self):
        """Start the bridge monitoring thread."""
        if self.running:
            logger.warning("ImportAnalysisBridge already running")
            return

        self.running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True, name="ImportAnalysisBridge")
        self._thread.start()
        logger.info("ImportAnalysisBridge started")

    def stop(self):
        """Stop the bridge monitoring thread."""
        if not self.running:
            return

        logger.info("Stopping ImportAnalysisBridge...")
        self.running = False

        # Wait for thread to finish (with timeout)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=10)

        logger.info("ImportAnalysisBridge stopped")

    def _monitor_loop(self):
        """Main monitoring loop - polls Redis for completed jobs."""
        logger.info("ImportAnalysisBridge monitoring loop started")

        while self.running:
            try:
                self._check_completed_jobs()
            except Exception as e:
                logger.error(f"ImportAnalysisBridge error in monitoring loop: {e}", exc_info=True)

            # Sleep for poll interval (check running flag frequently for quick shutdown)
            for _ in range(self._poll_interval * 10):
                if not self.running:
                    break
                time.sleep(0.1)

        logger.info("ImportAnalysisBridge monitoring loop exited")

    def _check_completed_jobs(self):
        """
        Scan Redis for completed import jobs and trigger analysis if requested.

        Sprint 76 Fix: Only process jobs completed within the last 2 hours
        to prevent analysis flood on app restart.

        Checks both job status key formats:
        - tickstock.jobs.status:{job_id} (TickStockPL format)
        - job:status:{job_id} (AppV2 format)
        """
        try:
            from datetime import datetime, timedelta

            # Only process jobs completed within the last 2 hours
            cutoff_time = datetime.now() - timedelta(hours=2)

            # Scan both key patterns
            for pattern in ['tickstock.jobs.status:*', 'job:status:*']:
                for key in self.redis_client.scan_iter(pattern):
                    # Decode key if bytes
                    key_str = key if isinstance(key, str) else key.decode('utf-8')
                    job_id = key_str.replace('tickstock.jobs.status:', '').replace('job:status:', '')

                    # Skip already processed jobs
                    if job_id in self._processed_jobs:
                        continue

                    # Get job status
                    job_status = self._get_job_status(key_str)
                    if not job_status:
                        continue

                    # Sprint 76: Check job completion time (prevent old jobs from processing)
                    completed_at = job_status.get('completed_at')
                    if completed_at:
                        try:
                            # Parse timestamp (supports both ISO format and Unix timestamp)
                            if isinstance(completed_at, (int, float)):
                                completed_time = datetime.fromtimestamp(completed_at)
                            else:
                                from dateutil.parser import parse
                                completed_time = parse(completed_at)

                            # Skip jobs older than cutoff
                            if completed_time < cutoff_time:
                                logger.debug(f"ImportAnalysisBridge: Skipping old job {job_id[:8]}... (completed {completed_time})")
                                self._processed_jobs.add(job_id)  # Mark as processed to avoid re-checking
                                continue
                        except Exception as e:
                            logger.warning(f"ImportAnalysisBridge: Could not parse completion time for {job_id[:8]}: {e}")
                            # Skip jobs with unparseable timestamps
                            continue

                    # Check if job is completed and has run_analysis flag
                    if self._should_trigger_analysis(job_status, job_id=job_id):
                        logger.info(f"ImportAnalysisBridge: Detected completed import job {job_id[:8]}... with run_analysis=true")
                        self._trigger_analysis_for_job(job_id, job_status)
                        self._processed_jobs.add(job_id)  # Mark as processed

        except Exception as e:
            logger.error(f"ImportAnalysisBridge: Error checking completed jobs: {e}", exc_info=True)

    def _get_job_status(self, job_key):
        """
        Get job status from Redis (supports both hash and string formats).

        Args:
            job_key: Redis key for job status

        Returns:
            dict: Job status data or None if not found/error
        """
        try:
            key_type = self.redis_client.type(job_key)

            if key_type == b'string' or key_type == 'string':
                # TickStockPL format: JSON string
                status_data = self.redis_client.get(job_key)
                if status_data:
                    if isinstance(status_data, bytes):
                        status_data = status_data.decode()
                    return json.loads(status_data)

            elif key_type == b'hash' or key_type == 'hash':
                # AppV2 format: hash
                status_data = self.redis_client.hgetall(job_key)
                if status_data:
                    # Convert bytes keys/values to strings
                    return {
                        (k.decode() if isinstance(k, bytes) else k): (v.decode() if isinstance(v, bytes) else v)
                        for k, v in status_data.items()
                    }

        except Exception as e:
            logger.error(f"ImportAnalysisBridge: Error getting job status for {job_key}: {e}")

        return None

    def _should_trigger_analysis(self, job_status, job_id=None):
        """
        Determine if analysis should be triggered for this job.

        Args:
            job_status: Job status dict
            job_id: Job ID (optional, for metadata lookup)

        Returns:
            bool: True if analysis should be triggered
        """
        # Check status is completed
        status = job_status.get('status', '')
        if status != 'completed':
            return False

        # Sprint 75 Phase 2 Fix: Check metadata key for run_analysis flag
        # (TickStockPL overwrites job status, losing our flag)
        if job_id:
            metadata_key = f'tickstock.jobs.metadata:{job_id}'
            try:
                metadata = self.redis_client.hgetall(metadata_key)
                if metadata:
                    # Convert bytes to strings if needed
                    if isinstance(metadata, dict):
                        metadata = {
                            (k.decode() if isinstance(k, bytes) else k): (v.decode() if isinstance(v, bytes) else v)
                            for k, v in metadata.items()
                        }
                    run_analysis = metadata.get('run_analysis_after_import', 'false')
                    if isinstance(run_analysis, str):
                        run_analysis = run_analysis.lower() in ['true', '1', 'yes']
                    return bool(run_analysis)
            except Exception as e:
                logger.error(f"ImportAnalysisBridge: Error checking metadata for {job_id[:8]}...: {e}")

        # Fallback: Check job_status (for backward compatibility)
        run_analysis = job_status.get('run_analysis_after_import', 'false')
        if isinstance(run_analysis, str):
            run_analysis = run_analysis.lower() in ['true', '1', 'yes']
        return bool(run_analysis)

    def _trigger_analysis_for_job(self, job_id, job_status):
        """
        Auto-submit analysis job for completed import.

        Args:
            job_id: Import job ID
            job_status: Import job status dict
        """
        try:
            # Establish Flask context (CRITICAL for database access)
            with self.app.app_context():
                # Import analysis services
                from src.api.rest.admin_process_analysis import run_analysis_job, active_jobs
                import time

                # Get symbols from completed import job
                # TickStockPL stores them as 'successful_symbols', not 'symbols'
                symbols = job_status.get('successful_symbols', [])

                # Fallback: Try 'symbols' key (for other job types)
                if not symbols:
                    symbols = job_status.get('symbols', [])

                # If symbols not in status, try getting from universe via metadata
                if not symbols:
                    # Check metadata for universe_key
                    metadata_key = f'tickstock.jobs.metadata:{job_id}'
                    try:
                        metadata = self.redis_client.hgetall(metadata_key)
                        if metadata:
                            # Convert bytes to strings if needed
                            if isinstance(metadata, dict):
                                metadata = {
                                    (k.decode() if isinstance(k, bytes) else k): (v.decode() if isinstance(v, bytes) else v)
                                    for k, v in metadata.items()
                                }
                            universe_key = metadata.get('universe_key')
                            if universe_key:
                                # Load symbols from universe using RelationshipCache
                                from src.core.services.relationship_cache import get_relationship_cache
                                cache = get_relationship_cache()
                                symbols = cache.get_universe_symbols(universe_key)
                    except Exception as e:
                        logger.error(f"ImportAnalysisBridge: Error loading symbols from metadata: {e}")

                if not symbols:
                    logger.warning(
                        f"ImportAnalysisBridge: No symbols found for job {job_id[:8]}... "
                        f"(checked: successful_symbols, symbols, universe_key in metadata)"
                    )
                    return

                # Determine timeframe from metadata (default to 'daily')
                timeframe = 'daily'
                try:
                    metadata_key = f'tickstock.jobs.metadata:{job_id}'
                    metadata = self.redis_client.hgetall(metadata_key)
                    if metadata:
                        if isinstance(metadata, dict):
                            metadata = {
                                (k.decode() if isinstance(k, bytes) else k): (v.decode() if isinstance(v, bytes) else v)
                                for k, v in metadata.items()
                            }
                        timeframe = metadata.get('timeframe', 'daily')
                except Exception:
                    pass  # Use default

                # Create analysis job
                analysis_job_id = f"analysis_auto_{int(time.time())}_{job_id[:8]}"
                analysis_job = {
                    'id': analysis_job_id,
                    'status': 'queued',
                    'type': 'analysis',
                    'universe_key': job_status.get('universe_key'),
                    'symbols': symbols,
                    'analysis_type': 'both',  # Run both patterns and indicators
                    'timeframe': timeframe,
                    'created_at': datetime.now(),
                    'created_by': 'import_analysis_bridge',
                    'progress': 0,
                    'current_symbol': None,
                    'symbols_completed': 0,
                    'symbols_total': len(symbols),
                    'patterns_detected': 0,
                    'indicators_calculated': 0,
                    'failed_symbols': [],
                    'log_messages': [
                        f"Auto-triggered by ImportAnalysisBridge for import job {job_id[:8]}..."
                    ],
                    'completed_at': None,
                }

                # Add to active jobs
                active_jobs[analysis_job_id] = analysis_job

                # Start analysis in background thread
                # Note: self.app is already the Flask app object, not a proxy
                thread = threading.Thread(
                    target=run_analysis_job,
                    args=(analysis_job, self.app),
                    daemon=True,
                    name=f"AutoAnalysis-{job_id[:8]}"
                )
                thread.start()

                logger.info(
                    f"ImportAnalysisBridge: Auto-triggered analysis job {analysis_job_id[:8]}... "
                    f"for {len(symbols)} symbols from import job {job_id[:8]}..."
                )

        except Exception as e:
            logger.error(
                f"ImportAnalysisBridge: Failed to trigger analysis for job {job_id[:8]}...: {e}",
                exc_info=True
            )
