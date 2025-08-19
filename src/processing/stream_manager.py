"""
DataStreamManager - Sprint 101 Multi-Frequency Processing
Handles routing and processing of data from multiple frequency streams.
Ensures thread-safe stream isolation and frequency-based processing.
"""

import threading
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable, Set
from enum import Enum
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import queue

from src.core.domain.market.tick import TickData
from src.core.domain.events.base import BaseEvent
from src.shared.types import FrequencyType
from config.logging_config import get_domain_logger, LogDomain

logger = get_domain_logger(LogDomain.CORE, 'data_stream_manager')


@dataclass
class StreamMetrics:
    """Metrics for monitoring stream health and performance"""
    stream_id: str
    frequency_type: str
    events_processed: int = 0
    events_failed: int = 0
    last_event_time: Optional[datetime] = None
    processing_errors: List[str] = None
    avg_processing_time_ms: float = 0.0
    
    def __post_init__(self):
        if self.processing_errors is None:
            self.processing_errors = []


class StreamProcessor:
    """
    Processes events for a specific frequency stream with isolated state.
    Each frequency type has its own processor to prevent cross-stream interference.
    """
    
    def __init__(self, frequency_type: FrequencyType, processor_callback: Callable, config: Dict):
        self.frequency_type = frequency_type
        self.processor_callback = processor_callback
        self.config = config
        
        # Stream-specific state (isolated from other frequencies)
        self.is_active = False
        self.event_queue = queue.Queue(maxsize=config.get('stream_queue_size', 1000))
        self.processing_thread = None
        self.metrics = StreamMetrics(
            stream_id=f"stream_{frequency_type.value}",
            frequency_type=frequency_type.value
        )
        
        # Thread safety
        self._lock = threading.Lock()
        
    def start(self):
        """Start the stream processor"""
        with self._lock:
            if self.is_active:
                logger.warning(f"STREAM-PROCESSOR-{self.frequency_type.value.upper()}: Already active")
                return
            
            self.is_active = True
            self.processing_thread = threading.Thread(
                target=self._process_events,
                name=f"StreamProcessor-{self.frequency_type.value}",
                daemon=True
            )
            self.processing_thread.start()
            logger.info(f"STREAM-PROCESSOR-{self.frequency_type.value.upper()}: Started")
    
    def stop(self):
        """Stop the stream processor"""
        with self._lock:
            if not self.is_active:
                return
            
            self.is_active = False
            # Add poison pill to wake up processing thread
            try:
                self.event_queue.put_nowait(None)
            except queue.Full:
                pass
            
            # Wait for thread to finish
            if self.processing_thread and self.processing_thread.is_alive():
                self.processing_thread.join(timeout=5.0)
            
            logger.info(f"STREAM-PROCESSOR-{self.frequency_type.value.upper()}: Stopped")
    
    def process_event(self, tick_data: TickData) -> bool:
        """
        Queue an event for processing by this stream.
        Returns True if queued successfully, False if queue is full.
        """
        try:
            self.event_queue.put_nowait(tick_data)
            return True
        except queue.Full:
            logger.warning(f"STREAM-PROCESSOR-{self.frequency_type.value.upper()}: Queue full, dropping event")
            self.metrics.events_failed += 1
            return False
    
    def _process_events(self):
        """Main processing loop for this stream (runs in separate thread)"""
        logger.info(f"STREAM-PROCESSOR-{self.frequency_type.value.upper()}: Processing loop started")
        
        while self.is_active:
            try:
                # Get event with timeout
                tick_data = self.event_queue.get(timeout=1.0)
                
                # Check for poison pill (shutdown signal)
                if tick_data is None:
                    break
                
                # Process the event
                start_time = time.time()
                try:
                    self.processor_callback(tick_data, self.frequency_type)
                    self.metrics.events_processed += 1
                    self.metrics.last_event_time = datetime.utcnow()
                except Exception as e:
                    logger.error(f"STREAM-PROCESSOR-{self.frequency_type.value.upper()}: Error processing event: {e}")
                    self.metrics.events_failed += 1
                    self.metrics.processing_errors.append(str(e))
                    
                    # Keep only last 10 errors
                    if len(self.metrics.processing_errors) > 10:
                        self.metrics.processing_errors.pop(0)
                
                # Update average processing time
                processing_time_ms = (time.time() - start_time) * 1000
                if self.metrics.avg_processing_time_ms == 0:
                    self.metrics.avg_processing_time_ms = processing_time_ms
                else:
                    # Exponential moving average
                    alpha = 0.1
                    self.metrics.avg_processing_time_ms = (
                        alpha * processing_time_ms + 
                        (1 - alpha) * self.metrics.avg_processing_time_ms
                    )
                
                self.event_queue.task_done()
                
            except queue.Empty:
                # Timeout - continue loop
                continue
            except Exception as e:
                logger.error(f"STREAM-PROCESSOR-{self.frequency_type.value.upper()}: Unexpected error in processing loop: {e}")
                break
        
        logger.info(f"STREAM-PROCESSOR-{self.frequency_type.value.upper()}: Processing loop ended")
    
    def get_metrics(self) -> StreamMetrics:
        """Get current stream metrics"""
        return self.metrics


class DataStreamManager:
    """
    Central coordinator for multi-frequency data stream processing.
    
    Responsibilities:
    - Route events to appropriate frequency-specific processors
    - Maintain stream isolation and thread safety
    - Monitor stream health and performance
    - Handle dynamic stream start/stop
    - Implement backpressure handling
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        
        # Stream management
        self.processors: Dict[FrequencyType, StreamProcessor] = {}
        self.enabled_frequencies: Set[FrequencyType] = set()
        self.is_running = False
        
        # Event routing callbacks
        self.event_processor_callback: Optional[Callable] = None
        
        # Monitoring
        self.start_time = None
        self.total_events_routed = 0
        self.routing_errors = 0
        
        # Thread safety
        self._lock = threading.Lock()
        
        logger.info("DATA-STREAM-MANAGER: Initialized")
    
    def initialize(self, enabled_frequencies: List[FrequencyType], 
                   event_processor_callback: Callable):
        """
        Initialize the stream manager with enabled frequencies and processing callback.
        
        Args:
            enabled_frequencies: List of frequency types to enable
            event_processor_callback: Function to call for processing events
        """
        with self._lock:
            if self.is_running:
                raise RuntimeError("Cannot initialize while running")
            
            self.enabled_frequencies = set(enabled_frequencies)
            self.event_processor_callback = event_processor_callback
            
            # Create processors for each enabled frequency
            for frequency_type in enabled_frequencies:
                if frequency_type not in self.processors:
                    processor = StreamProcessor(
                        frequency_type=frequency_type,
                        processor_callback=self._process_frequency_event,
                        config=self.config
                    )
                    self.processors[frequency_type] = processor
            
            logger.info(f"DATA-STREAM-MANAGER: Initialized with frequencies: {[f.value for f in enabled_frequencies]}")
    
    def start(self):
        """Start all stream processors"""
        with self._lock:
            if self.is_running:
                logger.warning("DATA-STREAM-MANAGER: Already running")
                return
            
            if not self.event_processor_callback:
                raise RuntimeError("Must call initialize() before start()")
            
            # Start all processors
            for frequency_type, processor in self.processors.items():
                if frequency_type in self.enabled_frequencies:
                    processor.start()
            
            self.is_running = True
            self.start_time = datetime.utcnow()
            logger.info("DATA-STREAM-MANAGER: Started all stream processors")
    
    def stop(self):
        """Stop all stream processors"""
        with self._lock:
            if not self.is_running:
                return
            
            logger.info("DATA-STREAM-MANAGER: Stopping all stream processors")
            
            # Stop all processors
            for processor in self.processors.values():
                processor.stop()
            
            self.is_running = False
            logger.info("DATA-STREAM-MANAGER: Stopped all stream processors")
    
    def route_event(self, tick_data: TickData, frequency_type: FrequencyType) -> bool:
        """
        Route an event to the appropriate frequency stream for processing.
        
        Args:
            tick_data: The tick data to process
            frequency_type: The frequency stream this event belongs to
        
        Returns:
            True if routed successfully, False if failed
        """
        if not self.is_running:
            logger.warning("DATA-STREAM-MANAGER: Cannot route event - not running")
            return False
        
        if frequency_type not in self.enabled_frequencies:
            logger.warning(f"DATA-STREAM-MANAGER: Frequency {frequency_type.value} not enabled")
            return False
        
        if frequency_type not in self.processors:
            logger.error(f"DATA-STREAM-MANAGER: No processor for frequency {frequency_type.value}")
            self.routing_errors += 1
            return False
        
        try:
            # Route to the appropriate processor
            success = self.processors[frequency_type].process_event(tick_data)
            
            if success:
                self.total_events_routed += 1
            else:
                self.routing_errors += 1
            
            return success
            
        except Exception as e:
            logger.error(f"DATA-STREAM-MANAGER: Error routing event to {frequency_type.value}: {e}")
            self.routing_errors += 1
            return False
    
    def _process_frequency_event(self, tick_data: TickData, frequency_type: FrequencyType):
        """
        Internal callback for processing events from specific frequency streams.
        This is called by StreamProcessor instances in their own threads.
        """
        try:
            # Add frequency context to the tick data if needed
            if hasattr(tick_data, 'frequency_type'):
                tick_data.frequency_type = frequency_type.value
            
            # Call the main event processor
            self.event_processor_callback(tick_data)
            
        except Exception as e:
            logger.error(f"DATA-STREAM-MANAGER: Error in frequency event processing for {frequency_type.value}: {e}")
            raise
    
    def add_frequency(self, frequency_type: FrequencyType) -> bool:
        """
        Dynamically add a new frequency stream (if not already enabled).
        Returns True if added, False if already exists or error.
        """
        with self._lock:
            if frequency_type in self.enabled_frequencies:
                logger.info(f"DATA-STREAM-MANAGER: Frequency {frequency_type.value} already enabled")
                return False
            
            try:
                # Create and start processor
                processor = StreamProcessor(
                    frequency_type=frequency_type,
                    processor_callback=self._process_frequency_event,
                    config=self.config
                )
                
                self.processors[frequency_type] = processor
                self.enabled_frequencies.add(frequency_type)
                
                # Start if manager is running
                if self.is_running:
                    processor.start()
                
                logger.info(f"DATA-STREAM-MANAGER: Added frequency {frequency_type.value}")
                return True
                
            except Exception as e:
                logger.error(f"DATA-STREAM-MANAGER: Error adding frequency {frequency_type.value}: {e}")
                return False
    
    def remove_frequency(self, frequency_type: FrequencyType) -> bool:
        """
        Dynamically remove a frequency stream.
        Returns True if removed, False if not found or error.
        """
        with self._lock:
            if frequency_type not in self.enabled_frequencies:
                logger.info(f"DATA-STREAM-MANAGER: Frequency {frequency_type.value} not enabled")
                return False
            
            try:
                # Stop and remove processor
                if frequency_type in self.processors:
                    self.processors[frequency_type].stop()
                    del self.processors[frequency_type]
                
                self.enabled_frequencies.remove(frequency_type)
                
                logger.info(f"DATA-STREAM-MANAGER: Removed frequency {frequency_type.value}")
                return True
                
            except Exception as e:
                logger.error(f"DATA-STREAM-MANAGER: Error removing frequency {frequency_type.value}: {e}")
                return False
    
    def get_stream_metrics(self) -> Dict[str, StreamMetrics]:
        """Get metrics for all active streams"""
        metrics = {}
        for frequency_type, processor in self.processors.items():
            if frequency_type in self.enabled_frequencies:
                metrics[frequency_type.value] = processor.get_metrics()
        return metrics
    
    def get_manager_metrics(self) -> Dict[str, Any]:
        """Get overall manager metrics"""
        uptime_seconds = 0
        if self.start_time:
            uptime_seconds = (datetime.utcnow() - self.start_time).total_seconds()
        
        return {
            'is_running': self.is_running,
            'enabled_frequencies': [f.value for f in self.enabled_frequencies],
            'total_events_routed': self.total_events_routed,
            'routing_errors': self.routing_errors,
            'uptime_seconds': uptime_seconds,
            'active_processors': len([p for p in self.processors.values() if p.is_active])
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status of the stream manager"""
        stream_metrics = self.get_stream_metrics()
        manager_metrics = self.get_manager_metrics()
        
        # Calculate health indicators
        total_events = sum(m.events_processed for m in stream_metrics.values())
        total_failures = sum(m.events_failed for m in stream_metrics.values())
        
        failure_rate = 0.0
        if total_events + total_failures > 0:
            failure_rate = total_failures / (total_events + total_failures)
        
        # Determine overall health
        health_status = "healthy"
        if failure_rate > 0.1:  # More than 10% failure rate
            health_status = "degraded"
        if failure_rate > 0.5:  # More than 50% failure rate
            health_status = "unhealthy"
        if not manager_metrics['is_running']:
            health_status = "stopped"
        
        return {
            'status': health_status,
            'failure_rate': failure_rate,
            'total_events_processed': total_events,
            'total_events_failed': total_failures,
            'stream_count': len(stream_metrics),
            'manager_metrics': manager_metrics,
            'stream_metrics': {k: {
                'events_processed': v.events_processed,
                'events_failed': v.events_failed,
                'avg_processing_time_ms': v.avg_processing_time_ms,
                'last_event_time': v.last_event_time.isoformat() if v.last_event_time else None
            } for k, v in stream_metrics.items()}
        }