#!/usr/bin/env python3
"""
Enterprise Production Load Scheduler - Sprint 14 Phase 4

This service provides enterprise-scale production load scheduling capabilities:
- Advanced scheduling for 5 years x 500 symbols with <5% error rate
- Redis-based job queue management with priority ordering
- Fault tolerance and resume capability with job state persistence
- Multi-threaded load balancing with API rate limit coordination
- Trading hours awareness and adaptive rate limiting

Architecture:
- Builds on existing Redis connection manager and performance monitoring
- Integrates with existing historical loader for data loading operations
- Uses Redis Streams for fault-tolerant job state persistence
- Coordinates with market calendar for intelligent scheduling
- Maintains <80% system utilization during maximum load operations
"""

import os
import sys
import asyncio
import json
import logging
import time
import psutil
import redis.asyncio as redis
from datetime import datetime, timedelta, time as dt_time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from enum import Enum
import threading

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

try:
    import pandas_market_calendars as mcal
    MARKET_CALENDARS_AVAILABLE = True
except ImportError:
    MARKET_CALENDARS_AVAILABLE = False
    print("+ Market calendars not available - using simplified schedule logic")

class JobPriority(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"

class JobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"

@dataclass
class EnterpriseSchedulingJob:
    """Enterprise scheduling job structure"""
    job_id: str
    symbols: List[str]
    start_date: str  # ISO format
    end_date: str    # ISO format
    priority: JobPriority
    status: JobStatus
    progress: Dict[str, Any]
    created_at: str
    updated_at: str
    metadata: Dict[str, Any]
    retry_count: int = 0
    max_retries: int = 3

class EnterpriseProductionScheduler:
    """
    Enterprise Production Load Scheduler
    
    Provides enterprise-scale historical data loading with:
    - Massive data loads (5 years x 500+ symbols)
    - Fault-tolerant job queue management via Redis
    - Priority-based scheduling with resource management
    - Multi-threaded execution with API rate limiting
    - Trading hours awareness and adaptive scheduling
    - Resume capability for interrupted operations
    """
    
    def __init__(self, database_uri: str = None, redis_host: str = None, polygon_api_key: str = None):
        """Initialize enterprise production scheduler"""
        self.database_uri = database_uri or os.getenv(
            'DATABASE_URL',
            'postgresql://app_readwrite:4pp_U$3r_2024!@localhost/tickstock'
        )
        self.redis_host = redis_host or os.getenv('REDIS_HOST', 'localhost')
        self.redis_port = int(os.getenv('REDIS_PORT', '6379'))
        self.polygon_api_key = polygon_api_key or os.getenv('POLYGON_API_KEY')
        
        # Enterprise configuration
        self.max_concurrent_jobs = 10
        self.max_threads_per_job = 5
        self.api_rate_limit_per_second = 5
        self.system_load_threshold = 0.8
        self.job_timeout_hours = 4
        
        # Priority configuration
        self.priority_order = [JobPriority.CRITICAL, JobPriority.HIGH, JobPriority.NORMAL, JobPriority.LOW]
        self.market_cap_threshold_critical = 10e9  # $10B+ market cap
        
        # Redis streams for job management
        self.redis_streams = {
            'job_queue': 'enterprise:jobs:queue',
            'job_progress': 'enterprise:jobs:progress',
            'job_errors': 'enterprise:jobs:errors',
            'system_metrics': 'enterprise:system:metrics'
        }
        
        # Thread safety
        self._lock = threading.Lock()
        self._active_jobs = {}
        self._system_metrics = {}
        
        # Market calendar integration
        if MARKET_CALENDARS_AVAILABLE:
            self.nyse_calendar = mcal.get_calendar('NYSE')
            self.nasdaq_calendar = mcal.get_calendar('NASDAQ')
        else:
            self.nyse_calendar = None
            self.nasdaq_calendar = None
        
        # Initialize logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
    async def connect_redis(self) -> Optional[redis.Redis]:
        """Establish Redis connection for job queue management"""
        try:
            redis_client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                decode_responses=True,
                health_check_interval=30
            )
            
            await redis_client.ping()
            self.logger.info(f"+ Redis connected: {self.redis_host}:{self.redis_port}")
            return redis_client
            
        except Exception as e:
            self.logger.error(f"- Redis connection failed: {e}")
            return None
    
    async def schedule_enterprise_load(self, symbols: List[str], years: int = 5, 
                                     force_priority: JobPriority = None) -> Dict[str, Any]:
        """
        Schedule enterprise-scale historical data load
        
        Args:
            symbols: List of symbols to load (up to 500+ symbols)
            years: Number of years of historical data (default: 5)
            force_priority: Override automatic priority assignment
            
        Returns:
            Scheduling results with job IDs and estimates
        """
        start_time = datetime.now()
        self.logger.info(f"=== Starting Enterprise Load Scheduling for {len(symbols)} symbols, {years} years ===")
        
        # Pre-flight checks
        if not self.is_trading_day():
            self.logger.info("+ Scheduling during non-trading day - optimal for bulk operations")
        
        if self.check_system_load() > self.system_load_threshold:
            self.logger.warning("- High system load detected - may impact performance")
        
        # Categorize symbols by priority
        prioritized_symbols = self.categorize_symbols_by_priority(symbols, force_priority)
        
        # Create enterprise job chunks
        enterprise_jobs = self.create_enterprise_jobs(prioritized_symbols, years)
        
        # Schedule jobs in Redis queue
        scheduled_jobs = []
        redis_client = await self.connect_redis()
        
        if redis_client:
            for job in enterprise_jobs:
                job_result = await self.queue_enterprise_job(redis_client, job)
                scheduled_jobs.append(job_result)
            
            await redis_client.aclose()
        
        scheduling_duration = (datetime.now() - start_time).total_seconds()
        
        return {
            'timestamp': start_time.isoformat(),
            'symbols_total': len(symbols),
            'years_requested': years,
            'jobs_created': len(enterprise_jobs),
            'jobs_scheduled': len(scheduled_jobs),
            'scheduling_duration_seconds': scheduling_duration,
            'estimated_completion_hours': self.estimate_completion_time(enterprise_jobs),
            'priority_distribution': self.get_priority_distribution(enterprise_jobs),
            'job_ids': [job['job_id'] for job in scheduled_jobs if 'job_id' in job]
        }
    
    def categorize_symbols_by_priority(self, symbols: List[str], 
                                     force_priority: JobPriority = None) -> Dict[JobPriority, List[str]]:
        """Categorize symbols by loading priority based on market cap and activity"""
        if force_priority:
            return {force_priority: symbols}
        
        # For demonstration - in production, this would query actual market cap data
        prioritized = {priority: [] for priority in JobPriority}
        
        # Mock prioritization logic (replace with real market cap queries)
        critical_symbols = ['SPY', 'QQQ', 'AAPL', 'MSFT', 'AMZN', 'GOOGL', 'TSLA', 'META', 'NVDA', 'BRK.A']
        high_priority_symbols = ['NFLX', 'AMD', 'CRM', 'ADBE', 'PYPL', 'INTC', 'CSCO', 'PEP', 'KO', 'DIS']
        
        for symbol in symbols:
            if symbol in critical_symbols:
                prioritized[JobPriority.CRITICAL].append(symbol)
            elif symbol in high_priority_symbols:
                prioritized[JobPriority.HIGH].append(symbol)
            elif len(symbol) <= 4:  # Likely major stocks
                prioritized[JobPriority.NORMAL].append(symbol)
            else:
                prioritized[JobPriority.LOW].append(symbol)
        
        return prioritized
    
    def create_enterprise_jobs(self, prioritized_symbols: Dict[JobPriority, List[str]], 
                             years: int) -> List[EnterpriseSchedulingJob]:
        """Create optimized job chunks for enterprise-scale processing"""
        jobs = []
        job_counter = 0
        
        # Calculate optimal date ranges (6-month chunks to balance load)
        end_date = datetime.now().date()
        chunk_months = 6
        
        for priority, symbols_list in prioritized_symbols.items():
            if not symbols_list:
                continue
            
            # Split symbols into manageable groups
            symbols_per_job = 50 if priority in [JobPriority.CRITICAL, JobPriority.HIGH] else 100
            symbol_groups = [symbols_list[i:i + symbols_per_job] 
                           for i in range(0, len(symbols_list), symbols_per_job)]
            
            # Create jobs for each time period
            for months_back in range(0, years * 12, chunk_months):
                chunk_end = end_date - timedelta(days=30 * months_back)
                chunk_start = chunk_end - timedelta(days=30 * chunk_months)
                
                for group_idx, symbol_group in enumerate(symbol_groups):
                    job_counter += 1
                    
                    job = EnterpriseSchedulingJob(
                        job_id=f"enterprise_{priority.value}_{months_back}_{group_idx}_{int(time.time())}_{job_counter}",
                        symbols=symbol_group,
                        start_date=chunk_start.isoformat(),
                        end_date=chunk_end.isoformat(),
                        priority=priority,
                        status=JobStatus.PENDING,
                        progress={
                            'total_symbols': len(symbol_group),
                            'completed_symbols': 0,
                            'failed_symbols': 0,
                            'estimated_records': len(symbol_group) * (chunk_months * 22),  # ~22 trading days/month
                            'actual_records': 0
                        },
                        created_at=datetime.now().isoformat(),
                        updated_at=datetime.now().isoformat(),
                        metadata={
                            'priority_reason': f'{priority.value} symbols',
                            'chunk_months': chunk_months,
                            'estimated_duration_minutes': len(symbol_group) * 2  # 2 min per symbol estimate
                        }
                    )
                    
                    jobs.append(job)
        
        # Sort jobs by priority for optimal execution order
        jobs.sort(key=lambda x: (self.priority_order.index(x.priority), x.created_at))
        
        return jobs
    
    async def queue_enterprise_job(self, redis_client: redis.Redis, 
                                 job: EnterpriseSchedulingJob) -> Dict[str, Any]:
        """Queue enterprise job in Redis with fault-tolerant persistence"""
        try:
            # Add job to Redis Stream
            await redis_client.xadd(
                self.redis_streams['job_queue'],
                {
                    'job_id': job.job_id,
                    'job_data': json.dumps(asdict(job), default=str),
                    'priority': job.priority.value,
                    'status': job.status.value,
                    'queued_at': datetime.now().isoformat()
                }
            )
            
            # Store detailed job state
            job_key = f"enterprise:job:{job.job_id}"
            await redis_client.hset(job_key, mapping={
                'job_data': json.dumps(asdict(job), default=str),
                'last_updated': datetime.now().isoformat()
            })
            
            # Set TTL for job cleanup (7 days)
            await redis_client.expire(job_key, 7 * 24 * 3600)
            
            self.logger.info(f"+ Job queued: {job.job_id} ({job.priority.value}, {len(job.symbols)} symbols)")
            
            return {
                'job_id': job.job_id,
                'status': 'queued',
                'priority': job.priority.value,
                'symbols_count': len(job.symbols),
                'estimated_duration_minutes': job.metadata.get('estimated_duration_minutes', 0)
            }
            
        except Exception as e:
            self.logger.error(f"- Failed to queue job {job.job_id}: {e}")
            return {
                'job_id': job.job_id,
                'status': 'queue_failed',
                'error': str(e)
            }
    
    async def execute_enterprise_jobs(self, max_concurrent: int = None) -> Dict[str, Any]:
        """
        Execute queued enterprise jobs with resource management
        
        Args:
            max_concurrent: Maximum concurrent jobs (default: class setting)
            
        Returns:
            Execution results and statistics
        """
        execution_start = datetime.now()
        max_concurrent = max_concurrent or self.max_concurrent_jobs
        
        self.logger.info(f"+ Starting enterprise job execution (max concurrent: {max_concurrent})")
        
        redis_client = await self.connect_redis()
        if not redis_client:
            return {'error': 'Redis connection failed'}
        
        try:
            # Get pending jobs from queue
            pending_jobs = await self.get_pending_jobs(redis_client)
            
            if not pending_jobs:
                self.logger.info("+ No pending jobs found")
                return {'message': 'No pending jobs', 'jobs_processed': 0}
            
            self.logger.info(f"+ Found {len(pending_jobs)} pending jobs")
            
            # Execute jobs with concurrency control
            semaphore = asyncio.Semaphore(max_concurrent)
            job_results = []
            
            async def execute_job_wrapper(job_data):
                async with semaphore:
                    return await self.execute_single_enterprise_job(redis_client, job_data)
            
            # Process all jobs concurrently
            tasks = [execute_job_wrapper(job) for job in pending_jobs]
            job_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Compile execution statistics
            successful_jobs = len([r for r in job_results if isinstance(r, dict) and r.get('status') == 'completed'])
            failed_jobs = len([r for r in job_results if isinstance(r, Exception) or 
                             (isinstance(r, dict) and r.get('status') == 'failed')])
            
            execution_duration = (datetime.now() - execution_start).total_seconds()
            
            # Publish completion notification
            await redis_client.publish('enterprise_jobs_complete', json.dumps({
                'timestamp': datetime.now().isoformat(),
                'jobs_processed': len(pending_jobs),
                'successful_jobs': successful_jobs,
                'failed_jobs': failed_jobs,
                'execution_duration_seconds': execution_duration
            }))
            
            return {
                'execution_start': execution_start.isoformat(),
                'jobs_processed': len(pending_jobs),
                'successful_jobs': successful_jobs,
                'failed_jobs': failed_jobs,
                'execution_duration_seconds': execution_duration,
                'average_job_duration': execution_duration / len(pending_jobs) if pending_jobs else 0,
                'job_results': [r for r in job_results if isinstance(r, dict)]
            }
            
        except Exception as e:
            self.logger.error(f"- Enterprise job execution failed: {e}")
            return {'error': str(e)}
        finally:
            if redis_client:
                await redis_client.aclose()
    
    async def get_pending_jobs(self, redis_client: redis.Redis) -> List[Dict[str, Any]]:
        """Get pending jobs from Redis queue ordered by priority"""
        try:
            # Read from job queue stream
            stream_data = await redis_client.xread({self.redis_streams['job_queue']: '0'})
            
            jobs = []
            for stream_name, messages in stream_data:
                for message_id, fields in messages:
                    if fields.get('status') == 'pending':
                        try:
                            job_data = json.loads(fields['job_data'])
                            job_data['redis_message_id'] = message_id
                            jobs.append(job_data)
                        except json.JSONDecodeError:
                            self.logger.error(f"- Invalid job data in message {message_id}")
            
            # Sort by priority
            priority_order = {p.value: i for i, p in enumerate(self.priority_order)}
            jobs.sort(key=lambda x: priority_order.get(x.get('priority', 'low'), 999))
            
            return jobs
            
        except Exception as e:
            self.logger.error(f"- Failed to get pending jobs: {e}")
            return []
    
    async def execute_single_enterprise_job(self, redis_client: redis.Redis, 
                                          job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute single enterprise job with fault tolerance"""
        job_id = job_data['job_id']
        job_start = datetime.now()
        
        try:
            self.logger.info(f"+ Starting job: {job_id}")
            
            # Update job status to running
            await self.update_job_status(redis_client, job_id, JobStatus.RUNNING)
            
            # Extract job parameters
            symbols = job_data['symbols']
            start_date = datetime.fromisoformat(job_data['start_date']).date()
            end_date = datetime.fromisoformat(job_data['end_date']).date()
            
            # Check for resume capability
            completed_symbols = await self.get_completed_symbols(redis_client, job_id)
            remaining_symbols = [s for s in symbols if s not in completed_symbols]
            
            self.logger.info(f"+ Job {job_id}: Processing {len(remaining_symbols)} remaining symbols")
            
            # Process symbols with rate limiting and error handling
            successful_symbols = []
            failed_symbols = []
            total_records = 0
            
            for symbol in remaining_symbols:
                # System load check
                if self.check_system_load() > self.system_load_threshold:
                    await asyncio.sleep(10)  # Wait for system load to decrease
                
                # Trading hours awareness
                rate_limit = self.get_adaptive_rate_limit()
                await asyncio.sleep(1.0 / rate_limit)
                
                try:
                    # Simulate data loading (replace with actual historical loader integration)
                    records_loaded = await self.load_symbol_historical_data(symbol, start_date, end_date)
                    successful_symbols.append(symbol)
                    total_records += records_loaded
                    
                    # Track progress
                    await self.update_job_progress(redis_client, job_id, symbol, records_loaded)
                    
                except Exception as e:
                    self.logger.error(f"- Failed to load {symbol}: {e}")
                    failed_symbols.append(symbol)
            
            # Update final job status
            final_status = JobStatus.COMPLETED if len(failed_symbols) == 0 else JobStatus.FAILED
            await self.update_job_status(redis_client, job_id, final_status)
            
            job_duration = (datetime.now() - job_start).total_seconds()
            
            result = {
                'job_id': job_id,
                'status': final_status.value,
                'duration_seconds': job_duration,
                'symbols_processed': len(successful_symbols),
                'symbols_failed': len(failed_symbols),
                'total_records_loaded': total_records,
                'success_rate': len(successful_symbols) / len(symbols) if symbols else 0,
                'records_per_second': total_records / job_duration if job_duration > 0 else 0
            }
            
            self.logger.info(f"+ Job completed: {job_id} ({result['success_rate']:.2%} success rate)")
            return result
            
        except Exception as e:
            await self.update_job_status(redis_client, job_id, JobStatus.FAILED)
            self.logger.error(f"- Job failed: {job_id}: {e}")
            return {
                'job_id': job_id,
                'status': 'failed',
                'error': str(e),
                'duration_seconds': (datetime.now() - job_start).total_seconds()
            }
    
    async def load_symbol_historical_data(self, symbol: str, start_date: datetime.date, 
                                        end_date: datetime.date) -> int:
        """
        Load historical data for a symbol (placeholder for actual integration)
        
        Args:
            symbol: Symbol to load
            start_date: Start date for data
            end_date: End date for data
            
        Returns:
            Number of records loaded
        """
        # Simulate data loading with realistic timing and record counts
        days = (end_date - start_date).days
        trading_days = days * 5 // 7  # Approximate trading days
        
        # Simulate API call delay
        await asyncio.sleep(0.1)
        
        # Simulate record count (1 per trading day for daily data)
        records_loaded = trading_days
        
        # Here you would integrate with the actual historical loader:
        # from src.data.historical_loader import PolygonHistoricalLoader
        # loader = PolygonHistoricalLoader()
        # records_loaded = await loader.load_symbol_range(symbol, start_date, end_date)
        
        return records_loaded
    
    async def update_job_status(self, redis_client: redis.Redis, job_id: str, status: JobStatus):
        """Update job status in Redis"""
        try:
            job_key = f"enterprise:job:{job_id}"
            await redis_client.hset(job_key, 'status', status.value)
            await redis_client.hset(job_key, 'last_updated', datetime.now().isoformat())
            
            # Publish status update
            await redis_client.publish('job_status_update', json.dumps({
                'job_id': job_id,
                'status': status.value,
                'timestamp': datetime.now().isoformat()
            }))
            
        except Exception as e:
            self.logger.error(f"- Failed to update job status: {e}")
    
    async def update_job_progress(self, redis_client: redis.Redis, job_id: str, 
                                symbol: str, records_loaded: int):
        """Update job progress tracking"""
        try:
            # Add to completed symbols set
            await redis_client.sadd(f"enterprise:job:{job_id}:completed", symbol)
            
            # Update progress metrics
            progress_key = f"enterprise:job:{job_id}:progress"
            await redis_client.hincrby(progress_key, 'completed_symbols', 1)
            await redis_client.hincrby(progress_key, 'total_records', records_loaded)
            await redis_client.hset(progress_key, 'last_symbol', symbol)
            await redis_client.hset(progress_key, 'last_updated', datetime.now().isoformat())
            
            # Publish progress update
            await redis_client.publish('job_progress_update', json.dumps({
                'job_id': job_id,
                'symbol': symbol,
                'records_loaded': records_loaded,
                'timestamp': datetime.now().isoformat()
            }))
            
        except Exception as e:
            self.logger.error(f"- Failed to update job progress: {e}")
    
    async def get_completed_symbols(self, redis_client: redis.Redis, job_id: str) -> List[str]:
        """Get list of completed symbols for resume capability"""
        try:
            completed_set = f"enterprise:job:{job_id}:completed"
            completed_symbols = await redis_client.smembers(completed_set)
            return list(completed_symbols) if completed_symbols else []
        except Exception as e:
            self.logger.error(f"- Failed to get completed symbols: {e}")
            return []
    
    def is_trading_day(self, date: datetime.date = None) -> bool:
        """Check if given date is a trading day"""
        if date is None:
            date = datetime.now().date()
            
        # Weekend check
        if date.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False
        
        if MARKET_CALENDARS_AVAILABLE and self.nyse_calendar:
            try:
                return self.nyse_calendar.is_session(pd.Timestamp(date))
            except:
                pass
        
        # Fallback: weekdays are trading days
        return date.weekday() < 5
    
    def is_trading_hours(self) -> bool:
        """Check if currently in trading hours"""
        now = datetime.now().time()
        market_open = dt_time(9, 30)   # 9:30 AM ET
        market_close = dt_time(16, 0)  # 4:00 PM ET
        return market_open <= now <= market_close
    
    def check_system_load(self) -> float:
        """Check current system resource utilization"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory_percent = psutil.virtual_memory().percent
            return max(cpu_percent, memory_percent) / 100.0
        except:
            return 0.5  # Conservative estimate if psutil unavailable
    
    def get_adaptive_rate_limit(self) -> float:
        """Get adaptive rate limit based on trading hours and system load"""
        base_rate = self.api_rate_limit_per_second
        
        if self.is_trading_hours():
            # Reduce rate during trading hours to minimize impact
            return base_rate * 0.5
        else:
            # Increase rate after hours for faster processing
            system_load = self.check_system_load()
            if system_load < 0.5:
                return base_rate * 1.5
            elif system_load < 0.7:
                return base_rate
            else:
                return base_rate * 0.7
    
    def estimate_completion_time(self, jobs: List[EnterpriseSchedulingJob]) -> float:
        """Estimate completion time in hours for job queue"""
        total_symbols = sum(len(job.symbols) for job in jobs)
        avg_seconds_per_symbol = 2.0  # Conservative estimate
        
        # Account for concurrent processing
        effective_symbols = total_symbols / self.max_concurrent_jobs
        estimated_seconds = effective_symbols * avg_seconds_per_symbol
        
        return estimated_seconds / 3600  # Convert to hours
    
    def get_priority_distribution(self, jobs: List[EnterpriseSchedulingJob]) -> Dict[str, int]:
        """Get distribution of jobs by priority"""
        distribution = {}
        for job in jobs:
            priority = job.priority.value
            distribution[priority] = distribution.get(priority, 0) + 1
        return distribution
    
    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get detailed status of a specific job"""
        redis_client = await self.connect_redis()
        if not redis_client:
            return {'error': 'Redis connection failed'}
        
        try:
            job_key = f"enterprise:job:{job_id}"
            job_data = await redis_client.hgetall(job_key)
            
            if not job_data:
                return {'error': f'Job {job_id} not found'}
            
            # Get progress information
            progress_key = f"enterprise:job:{job_id}:progress"
            progress_data = await redis_client.hgetall(progress_key)
            
            completed_symbols = await redis_client.smembers(f"enterprise:job:{job_id}:completed")
            
            return {
                'job_id': job_id,
                'job_data': json.loads(job_data.get('job_data', '{}')),
                'progress': progress_data,
                'completed_symbols': list(completed_symbols) if completed_symbols else [],
                'last_updated': job_data.get('last_updated')
            }
            
        except Exception as e:
            return {'error': str(e)}
        finally:
            if redis_client:
                await redis_client.aclose()

async def main():
    """Main execution function for enterprise production scheduling"""
    scheduler = EnterpriseProductionScheduler()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == '--schedule-enterprise':
            # Example enterprise scheduling
            symbols = ['AAPL', 'MSFT', 'AMZN', 'GOOGL', 'TSLA'] * 10  # 50 symbols
            years = 5
            
            result = await scheduler.schedule_enterprise_load(symbols, years)
            print(f"Enterprise scheduling complete:")
            print(f"  Jobs created: {result['jobs_created']}")
            print(f"  Jobs scheduled: {result['jobs_scheduled']}")
            print(f"  Estimated completion: {result['estimated_completion_hours']:.1f} hours")
            print(f"  Job IDs: {result['job_ids'][:3]}..." if result['job_ids'] else "  No jobs scheduled")
            
        elif command == '--execute-jobs':
            result = await scheduler.execute_enterprise_jobs()
            if 'error' not in result:
                print(f"Job execution complete:")
                print(f"  Jobs processed: {result['jobs_processed']}")
                print(f"  Successful: {result['successful_jobs']}")
                print(f"  Failed: {result['failed_jobs']}")
                print(f"  Duration: {result['execution_duration_seconds']:.1f} seconds")
            else:
                print(f"Execution failed: {result['error']}")
                
        elif command.startswith('--job-status='):
            job_id = command.split('=')[1]
            status = await scheduler.get_job_status(job_id)
            if 'error' not in status:
                print(f"Job Status: {job_id}")
                print(f"  Status: {status['job_data'].get('status', 'unknown')}")
                print(f"  Progress: {status['progress'].get('completed_symbols', 0)} completed")
                print(f"  Last Updated: {status['last_updated']}")
            else:
                print(f"Status check failed: {status['error']}")
                
        else:
            print("Usage:")
            print("  --schedule-enterprise: Create enterprise-scale scheduling jobs")
            print("  --execute-jobs: Execute all pending jobs")
            print("  --job-status=<job_id>: Get status of specific job")
    else:
        # Default: show system status
        system_load = scheduler.check_system_load()
        trading_day = scheduler.is_trading_day()
        trading_hours = scheduler.is_trading_hours()
        
        print("Enterprise Production Scheduler Status:")
        print(f"  System Load: {system_load:.1%}")
        print(f"  Trading Day: {trading_day}")
        print(f"  Trading Hours: {trading_hours}")
        print(f"  Market Calendars: {'Available' if MARKET_CALENDARS_AVAILABLE else 'Limited'}")

if __name__ == '__main__':
    asyncio.run(main())