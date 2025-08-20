"""
Abstract base class for all processing channels.

Provides standardized interface and functionality for processing different data types
through specialized channels with async processing, metrics, and error handling.

Sprint 105: Core Channel Infrastructure Implementation
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, AsyncGenerator, TYPE_CHECKING
from enum import Enum
import asyncio
import time
import logging
import uuid
from collections import deque

from config.logging_config import get_domain_logger, LogDomain

# Import BaseEvent from existing event system
from src.core.domain.events.base import BaseEvent

# Type-only imports to avoid circular dependencies
if TYPE_CHECKING:
    from .channel_config import ChannelConfig
    from .channel_metrics import ChannelHealthStatus

logger = get_domain_logger(LogDomain.CORE, 'channels')


class ChannelType(Enum):
    """Supported channel types for different data formats"""
    TICK = "tick"
    OHLCV = "ohlcv" 
    FMV = "fmv"


class ChannelStatus(Enum):
    """Channel lifecycle status"""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"
    SHUTDOWN = "shutdown"


@dataclass
class ProcessingResult:
    """
    Result of channel processing operation.
    Contains events generated, processing metadata, and error information.
    """
    success: bool
    events: List[BaseEvent] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    processing_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_error(self, error: str):
        """Add error to result"""
        self.errors.append(error)
        self.success = False
    
    def add_event(self, event: BaseEvent):
        """Add event to result"""
        self.events.append(event)
    
    def merge(self, other: 'ProcessingResult'):
        """Merge another processing result into this one"""
        self.events.extend(other.events)
        self.errors.extend(other.errors)
        self.success = self.success and other.success
        self.metadata.update(other.metadata)


class ProcessingChannel(ABC):
    """
    Abstract base class for all data processing channels.
    
    Provides standardized interface for processing different data types with:
    - Async processing capabilities
    - Comprehensive metrics tracking  
    - Configurable batching and queuing
    - Error handling and recovery
    - Health monitoring
    """
    
    def __init__(self, name: str, config: 'ChannelConfig'):
        self.name = name
        self.config = config
        self.channel_id = str(uuid.uuid4())[:8]
        
        # Channel state
        self._status = ChannelStatus.INITIALIZING
        self._shutdown_event = None
        self._processing_lock = None
        
        # Processing infrastructure
        self.processing_queue = None
        self._max_queue_size = config.max_queue_size
        self.batch_buffer = deque(maxlen=config.batching.max_batch_size * 2)  # 2x buffer
        self.last_batch_time = time.time()
        
        # Metrics (will be properly initialized by metrics system)
        from .channel_metrics import ChannelMetrics
        self.metrics = ChannelMetrics(channel_name=name, channel_id=self.channel_id)
        
        # Circuit breaker state
        self._consecutive_errors = 0
        self._last_error_time = None
        self._circuit_open = False
        self._circuit_open_time = None
        
        # Background tasks
        self._batch_processor_task = None
        self._queue_processor_task = None
        
        logger.info(f"Initialized {self.channel_type.value} channel: {name} [{self.channel_id}]")
    
    @property
    def channel_type(self) -> ChannelType:
        """Return the channel type"""
        return self.get_channel_type()
    
    @property
    def status(self) -> ChannelStatus:
        """Current channel status"""
        return self._status
    
    @property
    def is_circuit_open(self) -> bool:
        """Check if circuit breaker is open"""
        if not self._circuit_open:
            return False
            
        # Auto-close circuit after timeout
        if (self._circuit_open_time and 
            time.time() - self._circuit_open_time > self.config.circuit_breaker_timeout):
            self._circuit_open = False
            self._consecutive_errors = 0
            logger.info(f"Circuit breaker auto-closed for channel {self.name}")
            return False
            
        return True
    
    # Abstract methods that subclasses must implement
    
    @abstractmethod
    def get_channel_type(self) -> ChannelType:
        """Return the specific channel type (TICK, OHLCV, FMV)"""
        pass
    
    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the channel with required resources.
        Returns True if initialization successful.
        """
        pass
    
    @abstractmethod
    def validate_data(self, data: Any) -> bool:
        """
        Validate incoming data format for this channel.
        Returns True if data is valid for processing.
        """
        pass
    
    @abstractmethod
    async def process_data(self, data: Any) -> ProcessingResult:
        """
        Process incoming data and return events.
        Main processing logic for the channel.
        """
        pass
    
    @abstractmethod
    async def shutdown(self) -> bool:
        """
        Gracefully shutdown the channel and cleanup resources.
        Returns True if shutdown successful.
        """
        pass
    
    # Lazy initialization methods for asyncio objects
    
    def _get_shutdown_event(self):
        """Lazily create shutdown event when needed"""
        if self._shutdown_event is None:
            self._shutdown_event = asyncio.Event()
        return self._shutdown_event
    
    def _get_processing_lock(self):
        """Lazily create processing lock when needed"""
        if self._processing_lock is None:
            self._processing_lock = asyncio.Lock()
        return self._processing_lock
    
    def _get_processing_queue(self):
        """Lazily create processing queue when needed"""
        if self.processing_queue is None:
            self.processing_queue = asyncio.Queue(maxsize=self._max_queue_size)
        return self.processing_queue
    
    # Concrete methods with default implementation
    
    async def start(self) -> bool:
        """Start the channel and its background processing tasks"""
        try:
            # Initialize channel
            if not await self.initialize():
                self._status = ChannelStatus.ERROR
                return False
            
            # Start background processors
            await self._start_background_processors()
            
            self._status = ChannelStatus.ACTIVE
            self.metrics.mark_started()
            
            logger.info(f"Started channel {self.name} [{self.channel_id}]")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start channel {self.name}: {e}", exc_info=True)
            self._status = ChannelStatus.ERROR
            return False
    
    async def stop(self) -> bool:
        """Stop the channel and cleanup resources"""
        try:
            self._status = ChannelStatus.SHUTDOWN
            self._get_shutdown_event().set()
            
            # Stop background tasks
            await self._stop_background_processors()
            
            # Process remaining items in queues
            await self._drain_queues()
            
            # Channel-specific shutdown
            await self.shutdown()
            
            self.metrics.mark_stopped()
            logger.info(f"Stopped channel {self.name} [{self.channel_id}]")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping channel {self.name}: {e}", exc_info=True)
            return False
    
    async def submit_data(self, data: Any) -> bool:
        """
        Submit data for processing through the channel.
        Returns True if data was accepted for processing.
        """
        if self._status != ChannelStatus.ACTIVE:
            return False
            
        if self.is_circuit_open:
            self.metrics.increment_circuit_breaker_rejections()
            return False
        
        try:
            # For immediate processing channels (Priority 1)
            if self.config.batching.strategy.value == "immediate":
                # Process immediately without queuing
                result = await self.process_with_metrics(data)
                return result.success
            else:
                # Queue for batch processing
                await self._get_processing_queue().put(data)
                return True
                
        except asyncio.QueueFull:
            logger.warning(f"Queue full for channel {self.name}, dropping data")
            self.metrics.increment_queue_overflows()
            return False
        except Exception as e:
            logger.error(f"Error submitting data to channel {self.name}: {e}", exc_info=True)
            return False
    
    async def process_with_metrics(self, data: Any) -> ProcessingResult:
        """
        Process data with comprehensive metrics tracking.
        Handles circuit breaker logic and error tracking.
        """
        start_time = time.time()
        self.metrics.increment_processed_count()
        
        try:
            # Circuit breaker check
            if self.is_circuit_open:
                return ProcessingResult(
                    success=False,
                    errors=["Circuit breaker is open"],
                    metadata={"circuit_breaker": True}
                )
            
            # Validate data
            if not self.validate_data(data):
                result = ProcessingResult(
                    success=False,
                    errors=[f"Invalid data format for {self.channel_type.value} channel"]
                )
                self._handle_processing_error("data_validation_failed")
                return result
            
            # Process the data
            async with self._get_processing_lock():
                result = await self.process_data(data)
            
            # Update metrics
            processing_time_ms = (time.time() - start_time) * 1000
            result.processing_time_ms = processing_time_ms
            
            self.metrics.update_processing_time(processing_time_ms)
            self.metrics.increment_events_generated(len(result.events))
            
            if result.success:
                self._reset_circuit_breaker()
            else:
                self._handle_processing_error("processing_failed")
                self.metrics.increment_error_count()
                
            return result
            
        except Exception as e:
            processing_time_ms = (time.time() - start_time) * 1000
            
            error_msg = f"Channel processing error: {str(e)}"
            logger.error(f"{error_msg} in channel {self.name}", exc_info=True)
            
            self._handle_processing_error("exception_thrown")
            self.metrics.increment_error_count()
            self.metrics.update_processing_time(processing_time_ms)
            
            return ProcessingResult(
                success=False,
                errors=[error_msg],
                processing_time_ms=processing_time_ms,
                metadata={"exception": str(e)}
            )
    
    def _handle_processing_error(self, error_type: str):
        """Handle processing errors and circuit breaker logic"""
        self._consecutive_errors += 1
        self._last_error_time = time.time()
        
        # Open circuit breaker if too many consecutive errors
        if self._consecutive_errors >= self.config.circuit_breaker_threshold:
            self._circuit_open = True
            self._circuit_open_time = time.time()
            logger.warning(f"Circuit breaker opened for channel {self.name} after {self._consecutive_errors} consecutive errors")
            self.metrics.increment_circuit_breaker_opens()
    
    def _reset_circuit_breaker(self):
        """Reset circuit breaker after successful processing"""
        if self._consecutive_errors > 0:
            self._consecutive_errors = 0
            self._last_error_time = None
            
        if self._circuit_open:
            self._circuit_open = False
            self._circuit_open_time = None
            logger.info(f"Circuit breaker closed for channel {self.name}")
            self.metrics.increment_circuit_breaker_closes()
    
    async def _start_background_processors(self):
        """Start background processing tasks"""
        if self.config.batching.strategy.value != "immediate":
            self._queue_processor_task = asyncio.create_task(self._queue_processor())
            self._batch_processor_task = asyncio.create_task(self._batch_processor())
    
    async def _stop_background_processors(self):
        """Stop background processing tasks"""
        tasks = [self._queue_processor_task, self._batch_processor_task]
        for task in tasks:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
    
    async def _queue_processor(self):
        """Process items from the queue into batches"""
        try:
            while not self._get_shutdown_event().is_set():
                try:
                    # Wait for data with timeout
                    data = await asyncio.wait_for(
                        self._get_processing_queue().get(),
                        timeout=1.0  # Check shutdown every second
                    )
                    
                    # Add to batch buffer
                    self.batch_buffer.append(data)
                    
                    # Check if batch is ready
                    if self._is_batch_ready():
                        await self._process_batch()
                        
                except asyncio.TimeoutError:
                    # Check for timeout-based batch processing
                    if self._is_batch_timeout():
                        await self._process_batch()
                    continue
                    
        except Exception as e:
            logger.error(f"Queue processor error in channel {self.name}: {e}", exc_info=True)
    
    async def _batch_processor(self):
        """Periodic batch processor for timeout-based batching"""
        try:
            while not self._get_shutdown_event().is_set():
                await asyncio.sleep(self.config.batching.max_wait_time_ms / 1000.0)
                
                if self._is_batch_timeout() and len(self.batch_buffer) > 0:
                    await self._process_batch()
                    
        except Exception as e:
            logger.error(f"Batch processor error in channel {self.name}: {e}", exc_info=True)
    
    def _is_batch_ready(self) -> bool:
        """Check if batch is ready for processing"""
        return len(self.batch_buffer) >= self.config.batching.max_batch_size
    
    def _is_batch_timeout(self) -> bool:
        """Check if batch has timed out"""
        return (time.time() - self.last_batch_time) >= (self.config.batching.max_wait_time_ms / 1000.0)
    
    async def _process_batch(self):
        """Process current batch buffer"""
        if not self.batch_buffer:
            return
            
        batch_data = list(self.batch_buffer)
        self.batch_buffer.clear()
        self.last_batch_time = time.time()
        
        logger.debug(f"Processing batch of {len(batch_data)} items in channel {self.name}")
        
        # Process batch items
        results = []
        for data in batch_data:
            result = await self.process_with_metrics(data)
            results.append(result)
        
        # Update batch metrics
        batch_success = all(result.success for result in results)
        self.metrics.increment_batches_processed()
        
        if not batch_success:
            self.metrics.increment_batch_failures()
    
    async def _drain_queues(self):
        """Drain remaining items from queues during shutdown"""
        # Process remaining batched items
        if len(self.batch_buffer) > 0:
            await self._process_batch()
        
        # Process remaining queued items
        while not self._get_processing_queue().empty():
            try:
                data = self._get_processing_queue().get_nowait()
                await self.process_with_metrics(data)
            except asyncio.QueueEmpty:
                break
            except Exception as e:
                logger.error(f"Error draining queue for channel {self.name}: {e}")
    
    def is_healthy(self) -> bool:
        """
        Check if channel is healthy based on metrics and status.
        Used for load balancing and health monitoring.
        """
        # Check basic status
        if self._status not in [ChannelStatus.ACTIVE, ChannelStatus.PAUSED]:
            return False
        
        # Check circuit breaker
        if self.is_circuit_open:
            return False
        
        # Check error rate (>10% is unhealthy)
        if self.metrics.processed_count > 0:
            error_rate = self.metrics.error_count / self.metrics.processed_count
            if error_rate > 0.1:
                return False
        
        # Check processing time (>5 seconds average is unhealthy)
        if self.metrics.avg_processing_time_ms > 5000:
            return False
        
        # Check queue health
        if self.processing_queue and hasattr(self._get_processing_queue(), 'qsize'):
            queue_utilization = self._get_processing_queue().qsize() / self.config.max_queue_size
            if queue_utilization > 0.9:  # >90% full is unhealthy
                return False
        
        return True
    
    def get_health_status(self) -> 'ChannelHealthStatus':
        """Get comprehensive health status"""
        from .channel_metrics import ChannelHealthStatus
        
        return ChannelHealthStatus(
            channel_name=self.name,
            channel_id=self.channel_id,
            status=self._status,
            is_healthy=self.is_healthy(),
            uptime_seconds=time.time() - self.metrics.start_time if self.metrics.start_time else 0,
            processed_count=self.metrics.processed_count,
            error_count=self.metrics.error_count,
            error_rate=self.metrics.error_count / max(self.metrics.processed_count, 1),
            avg_processing_time_ms=self.metrics.avg_processing_time_ms,
            queue_size=self._get_processing_queue().qsize() if self.processing_queue and hasattr(self._get_processing_queue(), 'qsize') else 0,
            queue_utilization=self._get_processing_queue().qsize() / self.config.max_queue_size 
                            if self.processing_queue and hasattr(self._get_processing_queue(), 'qsize') else 0,
            circuit_breaker_open=self.is_circuit_open,
            consecutive_errors=self._consecutive_errors
        )
    
    def get_configuration(self) -> Dict[str, Any]:
        """Get channel configuration as dictionary"""
        return {
            'name': self.name,
            'channel_id': self.channel_id,
            'type': self.channel_type.value,
            'status': self._status.value,
            'config': self.config.to_dict() if hasattr(self.config, 'to_dict') else str(self.config)
        }
    
    def __str__(self) -> str:
        """String representation for logging"""
        return f"{self.channel_type.value.upper()}Channel[{self.name}:{self.channel_id}]"
    
    def __repr__(self) -> str:
        return (f"{self.__class__.__name__}(name='{self.name}', "
                f"type={self.channel_type.value}, status={self._status.value})")