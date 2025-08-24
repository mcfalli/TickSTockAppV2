# classes/processing/queue.py
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Union
from queue import PriorityQueue, Queue, Empty, Full  # Added Empty and Full
import threading
import time
import logging

logger = logging.getLogger(__name__)

from src.core.domain.events.base import BaseEvent

@dataclass
class QueuedEvent:
    """
    Wrapper for events in the processing queue.
    Provides priority and metadata for processing.
    """
    event: BaseEvent
    priority: int
    queued_at: float = field(default_factory=time.time)
    retry_count: int = 0
    processing_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __lt__(self, other: 'QueuedEvent') -> bool:
        """For priority queue ordering (lower priority number = higher priority)"""
        return self.priority < other.priority
        
    
    @property
    def age_seconds(self) -> float:
        """How long has this been in queue"""
        return time.time() - self.queued_at
        
    
    def should_expire(self, max_age: float = 60.0) -> bool:
        """Check if event is too old to process"""
        return self.age_seconds > max_age

class TypedEventQueue:
    """
    Thread-safe, type-safe event queue with priority support.
    Replaces tuple-based queue system.
    """
    
    def __init__(self, maxsize: int = 0, use_priority: bool = True):
        self.use_priority = use_priority
        self._queue: Union[PriorityQueue, Queue] = (
            PriorityQueue(maxsize) if use_priority else Queue(maxsize)
        )
        self._lock = threading.Lock()
        self._stats = {
            'events_queued': 0,
            'events_processed': 0,
            'events_expired': 0,
            'events_failed': 0,
            'by_type': {}
        }
        
    def put(self, event: BaseEvent, priority: int = 5) -> bool:
        """
        Add event to queue with type safety.
        Priority: 1=highest, 10=lowest
        """
        try:
            # Create queued event
            queued = QueuedEvent(event=event, priority=priority)
            
            # DEBUG: Log event being added
            logger.info(f"🔍 QUEUE-DEBUG: Adding {event.type} event for {event.ticker} with priority {priority}")
            
            # Add to queue
            if self.use_priority:
                self._queue.put(queued, block=False)
            else:
                self._queue.put(queued, block=False)
                
            # Update stats
            with self._lock:
                self._stats['events_queued'] += 1
                event_type = event.type
                if event_type not in self._stats['by_type']:
                    self._stats['by_type'][event_type] = {
                        'queued': 0, 'processed': 0, 'failed': 0
                    }
                self._stats['by_type'][event_type]['queued'] += 1
            
            # DEBUG: Log queue state after adding
            new_size = self.qsize()
            logger.info(f"🔍 QUEUE-DEBUG: Queue size after adding {event.type}: {new_size}")
                
            return True
            
        except Full:
            logger.warning(f"Queue full, dropping event: {event.ticker} {event.type}")
            return False
            
    def get(self, timeout: Optional[float] = None) -> Optional[QueuedEvent]:
        """Get next event from queue"""
        try:
            queued = self._queue.get(timeout=timeout)
            
            # Check expiration
            if queued.should_expire():
                with self._lock:
                    self._stats['events_expired'] += 1
                # DEBUG: Log expired event
                logger.warning(f"🔍 QUEUE-DEBUG: Event expired in get(): {queued.event.type} for {queued.event.ticker}, age={queued.age_seconds:.1f}s")
                # Call task_done to prevent queue from getting stuck
                self._queue.task_done()
                return None
                
            return queued
            
        except Empty:
            return None
            
    '''       
    def get_batch(self, max_items: int = 10, 
                  timeout: float = 0.1) -> List[QueuedEvent]:
        """Get multiple events at once for batch processing"""
        batch = []
        deadline = time.time() + timeout
        
        while len(batch) < max_items and time.time() < deadline:
            event = self.get(timeout=0.01)
            if event:
                batch.append(event)
            else:
                break
                
        return batch
        
    def mark_processed(self, queued_event: QueuedEvent, success: bool = True):
        """Mark event as processed for statistics"""
        with self._lock:
            if success:
                self._stats['events_processed'] += 1
                event_type = queued_event.event.type
                if event_type in self._stats['by_type']:
                    self._stats['by_type'][event_type]['processed'] += 1
            else:
                self._stats['events_failed'] += 1
                event_type = queued_event.event.type
                if event_type in self._stats['by_type']:
                    self._stats['by_type'][event_type]['failed'] += 1
                    
    def requeue(self, queued_event: QueuedEvent, new_priority: Optional[int] = None):
        """Requeue an event (e.g., after temporary failure)"""
        queued_event.retry_count += 1
        if new_priority:
            queued_event.priority = new_priority
            
        # Add small delay based on retry count
        time.sleep(0.1 * queued_event.retry_count)
        
        return self.put(queued_event.event, queued_event.priority)
    '''       
        
    def qsize(self) -> int:
        """Current queue size"""
        return self._queue.qsize()
        
    @property
    def empty(self) -> bool:
        """Is queue empty"""
        return self._queue.empty()
        
    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        with self._lock:
            return {
                'current_size': self.qsize,
                'total_queued': self._stats['events_queued'],
                'total_processed': self._stats['events_processed'],
                'total_expired': self._stats['events_expired'],
                'total_failed': self._stats['events_failed'],
                'by_type': dict(self._stats['by_type']),
                'success_rate': (
                    self._stats['events_processed'] / 
                    max(1, self._stats['events_queued'])
                )
            }
    def get_typed_batch(self, max_items: int = 10, 
                   timeout: float = 0.1,
                   event_types: Optional[List[type]] = None) -> List[BaseEvent]:
        """Get batch of specific event types"""
        batch = []
        deadline = time.time() + timeout
        
        # DEBUG: Log queue state before retrieval
        queue_size_before = self.qsize()
        if queue_size_before > 0:
            logger.info(f"🔍 QUEUE-DEBUG: get_typed_batch starting with {queue_size_before} events in queue")
        
        attempts = 0
        expired_events = 0
        
        while len(batch) < max_items and time.time() < deadline:
            attempts += 1
            queued_event = self.get(timeout=0.01)
            
            if queued_event:
                # Check if event expired
                if queued_event.should_expire():
                    expired_events += 1
                    logger.warning(f"🔍 QUEUE-DEBUG: Event expired during retrieval: {queued_event.event.type} age={queued_event.age_seconds:.1f}s")
                    continue
                
                # Filter by type if specified
                if event_types is None or type(queued_event.event) in event_types:
                    batch.append(queued_event.event)
                    logger.info(f"🔍 QUEUE-DEBUG: Retrieved {queued_event.event.type} event for {queued_event.event.ticker}")
            else:
                # No event available
                break
        
        # DEBUG: Log results
        if queue_size_before > 0 or len(batch) > 0:
            logger.info(f"🔍 QUEUE-DEBUG: get_typed_batch completed - queue_before={queue_size_before}, batch_size={len(batch)}, attempts={attempts}, expired={expired_events}")
                    
        return batch

    '''       
    def get_events_by_ticker(self, ticker: str, max_items: int = 10) -> List[BaseEvent]:
        """Get all events for a specific ticker"""
        events = []
        temp_storage = []
        
        # This is expensive but sometimes necessary
        while not self.empty and len(events) < max_items:
            queued = self.get(timeout=0)
            if queued:
                if queued.event.ticker == ticker:
                    events.append(queued.event)
                else:
                    temp_storage.append(queued)
        
        # Re-queue non-matching events
        for queued in temp_storage:
            self.put(queued.event, queued.priority)
            
        return events

    '''       
