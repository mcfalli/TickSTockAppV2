"""OHLCV Database Persistence Service.

Handles real-time tick data persistence to TimescaleDB ohlcv_1min table.
Designed for high-performance, low-latency database operations.

Key Features:
- Connection pooling with psycopg2
- Batch processing for optimal TimescaleDB performance
- Async operations to prevent blocking real-time WebSocket delivery
- Robust error handling and connection recovery
- Performance monitoring and health checks
"""

import time
import threading
import queue
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone
import psycopg2
from psycopg2 import pool, sql
from psycopg2.extras import execute_values

from src.core.domain.market.tick import TickData
from src.config.database_config import get_database_config

logger = logging.getLogger(__name__)

@dataclass
class OHLCVRecord:
    """OHLCV record for database persistence."""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    
    @classmethod
    def from_tick_data(cls, tick_data: TickData) -> 'OHLCVRecord':
        """Create OHLCV record from tick data."""
        # Convert Unix timestamp to timezone-aware datetime
        dt = datetime.fromtimestamp(tick_data.timestamp, tz=timezone.utc)
        # Round down to minute boundary for 1-minute aggregation
        minute_timestamp = dt.replace(second=0, microsecond=0)
        
        return cls(
            symbol=tick_data.ticker,
            timestamp=minute_timestamp,
            open=tick_data.tick_open or tick_data.price,
            high=tick_data.tick_high or tick_data.price,
            low=tick_data.tick_low or tick_data.price,
            close=tick_data.tick_close or tick_data.price,
            volume=tick_data.tick_volume or tick_data.volume or 0
        )

@dataclass
class PersistenceStats:
    """Statistics for database persistence operations."""
    records_queued: int = 0
    records_persisted: int = 0
    batch_count: int = 0
    errors: int = 0
    last_persist_time: Optional[float] = None
    avg_batch_time_ms: float = 0.0
    connection_errors: int = 0
    health_check_failures: int = 0

class OHLCVPersistenceService:
    """Service for persisting OHLCV data to TimescaleDB."""
    
    def __init__(self, config: Dict[str, Any], batch_size: int = 100, flush_interval: float = 5.0):
        """Initialize persistence service.
        
        Args:
            config: Database configuration
            batch_size: Number of records to batch before writing
            flush_interval: Maximum seconds to wait before forcing a flush
        """
        self.config = config
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        
        # Connection pool
        self.connection_pool: Optional[psycopg2.pool.ThreadedConnectionPool] = None
        
        # Queue for batching records
        self.record_queue = queue.Queue(maxsize=1000)
        
        # Threading
        self.persistence_thread: Optional[threading.Thread] = None
        self.running = False
        self._shutdown_event = threading.Event()
        
        # Statistics
        self.stats = PersistenceStats()
        
        # Performance monitoring
        self._batch_times = []
        self._last_flush_time = time.time()
        
        logger.info("OHLCV-PERSISTENCE: Service initialized")
    
    def start(self) -> bool:
        """Start the persistence service."""
        try:
            if self.running:
                logger.warning("OHLCV-PERSISTENCE: Service already running")
                return True
            
            logger.info("OHLCV-PERSISTENCE: Starting service...")
            
            # Initialize connection pool
            if not self._init_connection_pool():
                logger.error("OHLCV-PERSISTENCE: Failed to initialize connection pool")
                return False
            
            # Start persistence thread
            self.running = True
            self.persistence_thread = threading.Thread(target=self._persistence_loop, daemon=True)
            self.persistence_thread.start()
            
            logger.info("OHLCV-PERSISTENCE: Service started successfully")
            return True
            
        except Exception as e:
            logger.error(f"OHLCV-PERSISTENCE: Failed to start service: {e}")
            return False
    
    def stop(self):
        """Stop the persistence service."""
        if not self.running:
            return
        
        logger.info("OHLCV-PERSISTENCE: Stopping service...")
        
        self.running = False
        self._shutdown_event.set()
        
        # Wait for persistence thread to finish
        if self.persistence_thread and self.persistence_thread.is_alive():
            self.persistence_thread.join(timeout=10.0)
        
        # Close connection pool
        if self.connection_pool:
            self.connection_pool.closeall()
            self.connection_pool = None
        
        logger.info("OHLCV-PERSISTENCE: Service stopped")
    
    def persist_tick_data(self, tick_data: TickData) -> bool:
        """Queue tick data for persistence.
        
        Args:
            tick_data: Tick data to persist
            
        Returns:
            True if successfully queued, False otherwise
        """
        if not self.running:
            return False
        
        try:
            # Convert to OHLCV record
            ohlcv_record = OHLCVRecord.from_tick_data(tick_data)
            
            # Queue for batch processing (non-blocking)
            self.record_queue.put_nowait(ohlcv_record)
            self.stats.records_queued += 1
            
            return True
            
        except queue.Full:
            logger.warning("OHLCV-PERSISTENCE: Record queue full, dropping tick data")
            return False
        except Exception as e:
            logger.error(f"OHLCV-PERSISTENCE: Error queuing tick data: {e}")
            self.stats.errors += 1
            return False
    
    def _init_connection_pool(self) -> bool:
        """Initialize database connection pool."""
        try:
            db_config = get_database_config()
            
            # Create connection pool
            self.connection_pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=5,
                host=db_config['host'],
                port=db_config['port'],
                database=db_config['database'],
                user=db_config['user'],
                password=db_config['password'],
                connect_timeout=10
            )
            
            # Test connection
            if self._test_connection():
                logger.info("OHLCV-PERSISTENCE: Connection pool initialized successfully")
                return True
            else:
                logger.error("OHLCV-PERSISTENCE: Connection test failed")
                return False
            
        except Exception as e:
            logger.error(f"OHLCV-PERSISTENCE: Failed to initialize connection pool: {e}")
            return False
    
    def _test_connection(self) -> bool:
        """Test database connection."""
        try:
            conn = self.connection_pool.getconn()
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    result = cur.fetchone()
                    return result[0] == 1
            finally:
                self.connection_pool.putconn(conn)
                
        except Exception as e:
            logger.error(f"OHLCV-PERSISTENCE: Connection test failed: {e}")
            self.stats.connection_errors += 1
            return False
    
    def _persistence_loop(self):
        """Main persistence loop - runs in separate thread."""
        logger.info("OHLCV-PERSISTENCE: Persistence loop started")
        
        batch_records = []
        
        while self.running or not self.record_queue.empty():
            try:
                # Check for shutdown with timeout
                if self._shutdown_event.wait(timeout=0.1):
                    break
                
                # Collect records for batch processing
                batch_records.extend(self._collect_batch_records())
                
                # Check if we should flush the batch
                should_flush = (
                    len(batch_records) >= self.batch_size or
                    (batch_records and time.time() - self._last_flush_time >= self.flush_interval) or
                    not self.running  # Flush remaining records during shutdown
                )
                
                if should_flush and batch_records:
                    self._flush_batch(batch_records)
                    batch_records.clear()
                    self._last_flush_time = time.time()
                
            except Exception as e:
                logger.error(f"OHLCV-PERSISTENCE: Error in persistence loop: {e}")
                self.stats.errors += 1
                time.sleep(1.0)  # Prevent tight error loop
        
        # Final flush
        if batch_records:
            self._flush_batch(batch_records)
        
        logger.info("OHLCV-PERSISTENCE: Persistence loop stopped")
    
    def _collect_batch_records(self) -> List[OHLCVRecord]:
        """Collect records from queue for batch processing with deduplication."""
        records_dict = {}  # Use dict to handle duplicates: (symbol, timestamp) -> record
        
        # Collect up to batch_size records without blocking
        collected_count = 0
        while collected_count < self.batch_size:
            try:
                record = self.record_queue.get_nowait()
                
                # Create unique key for deduplication
                key = (record.symbol, record.timestamp)
                
                # Handle duplicate (symbol, timestamp) pairs
                if key in records_dict:
                    # Merge with existing record (aggregate OHLCV data)
                    existing = records_dict[key]
                    records_dict[key] = OHLCVRecord(
                        symbol=record.symbol,
                        timestamp=record.timestamp,
                        open=existing.open if existing.open != 0 else record.open,  # Keep first non-zero open
                        high=max(existing.high, record.high),  # Maximum high
                        low=min(existing.low, record.low),     # Minimum low
                        close=record.close,                    # Latest close
                        volume=existing.volume + record.volume # Sum volumes
                    )
                else:
                    records_dict[key] = record
                
                collected_count += 1
                
            except queue.Empty:
                break
        
        return list(records_dict.values())
    
    def _flush_batch(self, batch_records: List[OHLCVRecord]):
        """Flush batch of records to database."""
        if not batch_records:
            return
        
        start_time = time.time()
        
        try:
            conn = self.connection_pool.getconn()
            try:
                with conn.cursor() as cur:
                    # Process each unique (symbol, timestamp) separately to avoid conflicts
                    # Group by (symbol, timestamp) and aggregate before insertion
                    unique_records = {}
                    for record in batch_records:
                        key = (record.symbol, record.timestamp)
                        if key not in unique_records:
                            unique_records[key] = record
                        else:
                            # Aggregate OHLCV data for same (symbol, timestamp)
                            existing = unique_records[key]
                            unique_records[key] = OHLCVRecord(
                                symbol=record.symbol,
                                timestamp=record.timestamp,
                                open=existing.open if existing.open != 0 else record.open,
                                high=max(existing.high, record.high),
                                low=min(existing.low, record.low),
                                close=record.close,  # Latest close
                                volume=existing.volume + record.volume
                            )
                    
                    # Use final aggregated records
                    batch_records = list(unique_records.values())
                    
                    # Use UPSERT with ON CONFLICT for single aggregated records
                    insert_sql = """
                    INSERT INTO ohlcv_1min (symbol, timestamp, open, high, low, close, volume)
                    VALUES %s
                    ON CONFLICT (symbol, timestamp) DO UPDATE SET
                        high = GREATEST(ohlcv_1min.high, EXCLUDED.high),
                        low = LEAST(ohlcv_1min.low, EXCLUDED.low),
                        close = EXCLUDED.close,
                        volume = ohlcv_1min.volume + EXCLUDED.volume
                    """
                    
                    # Prepare data tuples
                    data_tuples = [
                        (record.symbol, record.timestamp, record.open, record.high, 
                         record.low, record.close, record.volume)
                        for record in batch_records
                    ]
                    
                    # Execute batch insert
                    execute_values(cur, insert_sql, data_tuples, page_size=100)
                    conn.commit()
                    
                    # Update statistics
                    self.stats.records_persisted += len(batch_records)
                    self.stats.batch_count += 1
                    self.stats.last_persist_time = time.time()
                    
                    # Track performance
                    batch_time_ms = (time.time() - start_time) * 1000
                    self._batch_times.append(batch_time_ms)
                    
                    # Keep only last 100 batch times for average calculation
                    if len(self._batch_times) > 100:
                        self._batch_times.pop(0)
                    
                    self.stats.avg_batch_time_ms = sum(self._batch_times) / len(self._batch_times)
                    
                    logger.debug(
                        f"OHLCV-PERSISTENCE: Persisted batch of {len(batch_records)} records "
                        f"in {batch_time_ms:.1f}ms"
                    )
                    
            finally:
                self.connection_pool.putconn(conn)
                
        except Exception as e:
            logger.error(f"OHLCV-PERSISTENCE: Failed to flush batch: {e}")
            self.stats.errors += 1
            
            # Put records back in queue for retry (up to queue capacity)
            for record in batch_records:
                try:
                    self.record_queue.put_nowait(record)
                except queue.Full:
                    logger.warning("OHLCV-PERSISTENCE: Queue full, dropping record during retry")
                    break
    
    def get_stats(self) -> Dict[str, Any]:
        """Get persistence statistics."""
        queue_size = self.record_queue.qsize()
        uptime = time.time() - (self.stats.last_persist_time or time.time())
        
        return {
            'running': self.running,
            'records_queued': self.stats.records_queued,
            'records_persisted': self.stats.records_persisted,
            'batch_count': self.stats.batch_count,
            'queue_size': queue_size,
            'queue_capacity': self.record_queue.maxsize,
            'errors': self.stats.errors,
            'connection_errors': self.stats.connection_errors,
            'avg_batch_time_ms': round(self.stats.avg_batch_time_ms, 1),
            'last_persist_time': self.stats.last_persist_time,
            'persistence_rate': self.stats.records_persisted / uptime if uptime > 0 else 0
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status for monitoring."""
        is_healthy = (
            self.running and
            self.connection_pool is not None and
            self._test_connection() and
            self.stats.errors < 10  # Threshold for too many errors
        )
        
        return {
            'healthy': is_healthy,
            'running': self.running,
            'connection_pool_active': self.connection_pool is not None,
            'connection_test_passed': self._test_connection(),
            'queue_size': self.record_queue.qsize(),
            'error_count': self.stats.errors,
            'last_persist_age_seconds': (
                time.time() - self.stats.last_persist_time 
                if self.stats.last_persist_time else None
            )
        }