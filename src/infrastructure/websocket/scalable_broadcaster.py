"""
Scalable Broadcaster
Sprint 25 Day 3 Implementation: High-performance WebSocket broadcasting with batching and rate limiting.

Efficient broadcasting system for real-time financial data delivery supporting 500+ concurrent users.
Implements industry-standard patterns used by professional trading platforms (Bloomberg, Refinitiv)
for sub-100ms message delivery with batching optimization and user-level rate limiting.
"""

import logging
import time
import threading
from typing import Dict, Any, Set, List, Optional, Tuple
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
import asyncio
from concurrent.futures import ThreadPoolExecutor
from flask_socketio import SocketIO

logger = logging.getLogger(__name__)

class DeliveryPriority(Enum):
    """Message delivery priority levels."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class EventMessage:
    """Individual event message for broadcasting."""
    event_type: str
    event_data: Dict[str, Any]
    target_users: Set[str]
    priority: DeliveryPriority
    timestamp: float
    message_id: str
    
    # Delivery tracking
    attempts: int = 0
    delivered_users: Set[str] = field(default_factory=set)
    failed_users: Set[str] = field(default_factory=set)

@dataclass
class EventBatch:
    """Batched events for efficient delivery."""
    room_name: str
    events: List[EventMessage]
    batch_id: str
    created_at: float
    priority: DeliveryPriority
    
    def get_total_size(self) -> int:
        """Get total size of batch for memory management."""
        return sum(len(str(event.event_data)) for event in self.events)

@dataclass
class RateLimiter:
    """Per-user rate limiter for event delivery."""
    max_events_per_second: int
    window_size_seconds: int = 1
    
    def __post_init__(self):
        self.event_timestamps = deque()
        self.lock = threading.Lock()
    
    def allow_event(self) -> bool:
        """Check if event is allowed within rate limit."""
        with self.lock:
            current_time = time.time()
            
            # Remove expired timestamps
            while (self.event_timestamps and 
                   current_time - self.event_timestamps[0] > self.window_size_seconds):
                self.event_timestamps.popleft()
            
            # Check rate limit
            if len(self.event_timestamps) >= self.max_events_per_second:
                return False
            
            # Allow event and record timestamp
            self.event_timestamps.append(current_time)
            return True
    
    def get_current_rate(self) -> int:
        """Get current events per second rate."""
        with self.lock:
            current_time = time.time()
            # Clean expired timestamps
            while (self.event_timestamps and 
                   current_time - self.event_timestamps[0] > self.window_size_seconds):
                self.event_timestamps.popleft()
            return len(self.event_timestamps)

@dataclass
class BroadcastStats:
    """Performance statistics for broadcasting operations."""
    total_events: int = 0
    events_delivered: int = 0
    events_dropped: int = 0
    events_rate_limited: int = 0
    
    # Performance metrics
    avg_batch_size: float = 0.0
    avg_delivery_latency_ms: float = 0.0
    max_delivery_latency_ms: float = 0.0
    
    # Batching metrics
    batches_created: int = 0
    batches_delivered: int = 0
    batch_efficiency: float = 0.0  # events per batch
    
    # Rate limiting metrics
    rate_limit_violations: int = 0
    users_rate_limited: int = 0
    
    # Error tracking
    delivery_errors: int = 0
    batch_errors: int = 0
    
    def record_delivery(self, batch_size: int, latency_ms: float):
        """Record successful delivery metrics."""
        self.events_delivered += batch_size
        self.batches_delivered += 1
        
        # Update latency metrics
        if self.batches_delivered == 1:
            self.avg_delivery_latency_ms = latency_ms
        else:
            self.avg_delivery_latency_ms = (
                (self.avg_delivery_latency_ms * (self.batches_delivered - 1) + latency_ms) /
                self.batches_delivered
            )
        
        self.max_delivery_latency_ms = max(self.max_delivery_latency_ms, latency_ms)
        
        # Update batch efficiency
        self.batch_efficiency = self.events_delivered / max(self.batches_delivered, 1)

class ScalableBroadcaster:
    """
    High-performance WebSocket broadcasting system with batching and rate limiting.
    
    Implements scalable real-time communication patterns for financial data delivery:
    - Event batching with configurable time windows (100ms default)
    - Per-user rate limiting (100 events/sec default)
    - Priority-based delivery queuing
    - Efficient room-based broadcasting
    - Connection pool management
    - Performance monitoring and optimization
    
    Designed to support 500+ concurrent users with <100ms delivery latency.
    """
    
    def __init__(self, socketio: SocketIO, 
                 batch_window_ms: int = 100,
                 max_events_per_user: int = 100,
                 max_batch_size: int = 50):
        """Initialize Scalable Broadcaster."""
        
        self.socketio = socketio
        self.batch_window_ms = batch_window_ms
        self.max_events_per_user = max_events_per_user
        self.max_batch_size = max_batch_size
        
        # Event batching system
        self.pending_batches: Dict[str, EventBatch] = {}  # room -> batch
        self.batch_timers: Dict[str, threading.Timer] = {}  # room -> timer
        self.event_queue: Dict[DeliveryPriority, deque] = {
            priority: deque() for priority in DeliveryPriority
        }
        
        # Rate limiting system
        self.user_rate_limiters: Dict[str, RateLimiter] = {}
        self.rate_limit_lock = threading.Lock()
        
        # Threading and async handling
        self.batch_executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="broadcast-batch")
        self.delivery_executor = ThreadPoolExecutor(max_workers=20, thread_name_prefix="broadcast-delivery")
        
        # Performance tracking
        self.stats = BroadcastStats()
        self.start_time = time.time()
        
        # Thread safety
        self.broadcast_lock = threading.RLock()
        
        # Configuration
        self.enable_batching = True
        self.enable_rate_limiting = True
        self.enable_priority_queuing = True
        
        logger.info(f"SCALABLE-BROADCASTER: Initialized with {batch_window_ms}ms batching, "
                   f"{max_events_per_user} events/sec rate limit")
    
    def broadcast_to_users(self, event_type: str, event_data: Dict[str, Any], 
                          user_ids: Set[str], priority: DeliveryPriority = DeliveryPriority.MEDIUM) -> int:
        """
        Broadcast event to specific users with batching and rate limiting.
        
        Args:
            event_type: Type of event to broadcast
            event_data: Event payload
            user_ids: Target user IDs
            priority: Message delivery priority
            
        Returns:
            Number of users event was queued for delivery to
        """
        try:
            if not user_ids:
                return 0
            
            start_time = time.time()
            
            # Create event message
            message_id = f"{event_type}_{int(time.time() * 1000)}"
            event_message = EventMessage(
                event_type=event_type,
                event_data=event_data,
                target_users=user_ids.copy(),
                priority=priority,
                timestamp=start_time,
                message_id=message_id
            )
            
            # Apply rate limiting filtering
            if self.enable_rate_limiting:
                filtered_users = self._apply_rate_limiting(user_ids)
                rate_limited_count = len(user_ids) - len(filtered_users)
                
                if rate_limited_count > 0:
                    self.stats.events_rate_limited += rate_limited_count
                    self.stats.rate_limit_violations += 1
                    logger.debug(f"SCALABLE-BROADCASTER: Rate limited {rate_limited_count} users for {event_type}")
                
                event_message.target_users = filtered_users
            
            if not event_message.target_users:
                return 0
            
            # Queue for batched delivery
            queued_count = self._queue_for_delivery(event_message)
            
            # Update statistics
            self.stats.total_events += 1
            
            logger.debug(f"SCALABLE-BROADCASTER: Queued {event_type} for {queued_count} users "
                        f"(priority: {priority.name})")
            
            return queued_count
            
        except Exception as e:
            logger.error(f"SCALABLE-BROADCASTER: Error broadcasting to users: {e}")
            self.stats.delivery_errors += 1
            return 0
    
    def broadcast_to_room(self, room_name: str, event_type: str, event_data: Dict[str, Any],
                         priority: DeliveryPriority = DeliveryPriority.MEDIUM) -> bool:
        """
        Broadcast event directly to room with batching.
        
        Args:
            room_name: Target room name
            event_type: Type of event to broadcast
            event_data: Event payload
            priority: Message delivery priority
            
        Returns:
            True if successfully queued for delivery
        """
        try:
            # Create event for room broadcasting
            event_message = EventMessage(
                event_type=event_type,
                event_data=event_data,
                target_users=set(),  # Room-based delivery
                priority=priority,
                timestamp=time.time(),
                message_id=f"{event_type}_room_{int(time.time() * 1000)}"
            )
            
            # Queue for batched room delivery
            success = self._queue_room_delivery(room_name, event_message)
            
            if success:
                self.stats.total_events += 1
                logger.debug(f"SCALABLE-BROADCASTER: Queued room broadcast {event_type} to {room_name}")
            
            return success
            
        except Exception as e:
            logger.error(f"SCALABLE-BROADCASTER: Error broadcasting to room {room_name}: {e}")
            self.stats.delivery_errors += 1
            return False
    
    def _apply_rate_limiting(self, user_ids: Set[str]) -> Set[str]:
        """Apply rate limiting to user set."""
        try:
            with self.rate_limit_lock:
                filtered_users = set()
                
                for user_id in user_ids:
                    # Get or create rate limiter for user
                    if user_id not in self.user_rate_limiters:
                        self.user_rate_limiters[user_id] = RateLimiter(
                            max_events_per_second=self.max_events_per_user
                        )
                    
                    rate_limiter = self.user_rate_limiters[user_id]
                    
                    # Check if user can receive event
                    if rate_limiter.allow_event():
                        filtered_users.add(user_id)
                    else:
                        logger.debug(f"SCALABLE-BROADCASTER: Rate limited user {user_id}")
                
                return filtered_users
                
        except Exception as e:
            logger.error(f"SCALABLE-BROADCASTER: Error applying rate limiting: {e}")
            return user_ids  # Return all users on error to ensure delivery
    
    def _queue_for_delivery(self, event_message: EventMessage) -> int:
        """Queue event message for batched delivery."""
        try:
            with self.broadcast_lock:
                queued_count = 0
                
                # Group users by rooms for efficient delivery
                user_rooms = {}
                for user_id in event_message.target_users:
                    room_name = f"user_{user_id}"
                    if room_name not in user_rooms:
                        user_rooms[room_name] = set()
                    user_rooms[room_name].add(user_id)
                
                # Create batches for each room
                for room_name, room_users in user_rooms.items():
                    # Create room-specific event message
                    room_event = EventMessage(
                        event_type=event_message.event_type,
                        event_data=event_message.event_data,
                        target_users=room_users,
                        priority=event_message.priority,
                        timestamp=event_message.timestamp,
                        message_id=f"{event_message.message_id}_{room_name}"
                    )
                    
                    # Add to existing batch or create new one
                    if room_name in self.pending_batches:
                        batch = self.pending_batches[room_name]
                        
                        # Check if batch can accommodate new event
                        if (len(batch.events) < self.max_batch_size and
                            batch.get_total_size() < 64 * 1024):  # 64KB max batch size
                            batch.events.append(room_event)
                        else:
                            # Flush current batch and start new one
                            self._flush_batch(room_name)
                            self._create_new_batch(room_name, room_event)
                    else:
                        # Create new batch
                        self._create_new_batch(room_name, room_event)
                    
                    queued_count += len(room_users)
                
                return queued_count
                
        except Exception as e:
            logger.error(f"SCALABLE-BROADCASTER: Error queuing for delivery: {e}")
            return 0
    
    def _queue_room_delivery(self, room_name: str, event_message: EventMessage) -> bool:
        """Queue event for direct room delivery."""
        try:
            with self.broadcast_lock:
                # Add to existing batch or create new one
                if room_name in self.pending_batches:
                    batch = self.pending_batches[room_name]
                    
                    # Check batch capacity
                    if (len(batch.events) < self.max_batch_size and
                        batch.get_total_size() < 64 * 1024):
                        batch.events.append(event_message)
                    else:
                        # Flush and create new batch
                        self._flush_batch(room_name)
                        self._create_new_batch(room_name, event_message)
                else:
                    # Create new batch
                    self._create_new_batch(room_name, event_message)
                
                return True
                
        except Exception as e:
            logger.error(f"SCALABLE-BROADCASTER: Error queuing room delivery: {e}")
            return False
    
    def _create_new_batch(self, room_name: str, event_message: EventMessage):
        """Create new batch for room."""
        try:
            batch_id = f"{room_name}_{int(time.time() * 1000)}"
            
            batch = EventBatch(
                room_name=room_name,
                events=[event_message],
                batch_id=batch_id,
                created_at=time.time(),
                priority=event_message.priority
            )
            
            self.pending_batches[room_name] = batch
            self.stats.batches_created += 1
            
            # Schedule batch delivery
            timer = threading.Timer(
                self.batch_window_ms / 1000.0,  # Convert to seconds
                lambda: self._flush_batch(room_name)
            )
            
            self.batch_timers[room_name] = timer
            timer.start()
            
            logger.debug(f"SCALABLE-BROADCASTER: Created batch {batch_id} for room {room_name}")
            
        except Exception as e:
            logger.error(f"SCALABLE-BROADCASTER: Error creating batch for room {room_name}: {e}")
    
    def _flush_batch(self, room_name: str):
        """Flush and deliver batch for room."""
        try:
            with self.broadcast_lock:
                if room_name not in self.pending_batches:
                    return
                
                batch = self.pending_batches[room_name]
                del self.pending_batches[room_name]
                
                # Cancel timer if exists
                if room_name in self.batch_timers:
                    timer = self.batch_timers[room_name]
                    timer.cancel()
                    del self.batch_timers[room_name]
            
            # Deliver batch asynchronously
            self.delivery_executor.submit(self._deliver_batch, batch)
            
        except Exception as e:
            logger.error(f"SCALABLE-BROADCASTER: Error flushing batch for room {room_name}: {e}")
    
    def _deliver_batch(self, batch: EventBatch):
        """Deliver batch of events to room."""
        try:
            start_time = time.time()
            
            if not batch.events:
                return
            
            # Sort events by priority
            sorted_events = sorted(batch.events, key=lambda e: e.priority.value, reverse=True)
            
            # Prepare batch payload
            if len(sorted_events) == 1:
                # Single event delivery
                event = sorted_events[0]
                self.socketio.emit(
                    event.event_type,
                    event.event_data,
                    room=batch.room_name
                )
            else:
                # Batch delivery
                batch_payload = {
                    'type': 'event_batch',
                    'batch_id': batch.batch_id,
                    'events': [
                        {
                            'type': event.event_type,
                            'data': event.event_data,
                            'timestamp': event.timestamp,
                            'priority': event.priority.name.lower()
                        }
                        for event in sorted_events
                    ],
                    'batch_timestamp': time.time()
                }
                
                self.socketio.emit('event_batch', batch_payload, room=batch.room_name)
            
            # Record delivery metrics
            delivery_time_ms = (time.time() - start_time) * 1000
            self.stats.record_delivery(len(sorted_events), delivery_time_ms)
            
            logger.debug(f"SCALABLE-BROADCASTER: Delivered batch {batch.batch_id} "
                        f"with {len(sorted_events)} events in {delivery_time_ms:.1f}ms")
            
        except Exception as e:
            logger.error(f"SCALABLE-BROADCASTER: Error delivering batch {batch.batch_id}: {e}")
            self.stats.batch_errors += 1
    
    def flush_all_batches(self):
        """Flush all pending batches immediately."""
        try:
            with self.broadcast_lock:
                rooms_to_flush = list(self.pending_batches.keys())
            
            for room_name in rooms_to_flush:
                self._flush_batch(room_name)
            
            logger.info(f"SCALABLE-BROADCASTER: Flushed {len(rooms_to_flush)} pending batches")
            
        except Exception as e:
            logger.error(f"SCALABLE-BROADCASTER: Error flushing all batches: {e}")
    
    def get_user_rate_status(self, user_id: str) -> Dict[str, Any]:
        """Get rate limiting status for user."""
        try:
            with self.rate_limit_lock:
                if user_id not in self.user_rate_limiters:
                    return {
                        'user_id': user_id,
                        'current_rate': 0,
                        'max_rate': self.max_events_per_user,
                        'rate_limited': False
                    }
                
                rate_limiter = self.user_rate_limiters[user_id]
                current_rate = rate_limiter.get_current_rate()
                
                return {
                    'user_id': user_id,
                    'current_rate': current_rate,
                    'max_rate': self.max_events_per_user,
                    'rate_limited': current_rate >= self.max_events_per_user,
                    'utilization_percent': (current_rate / self.max_events_per_user) * 100
                }
                
        except Exception as e:
            logger.error(f"SCALABLE-BROADCASTER: Error getting rate status for {user_id}: {e}")
            return {'user_id': user_id, 'error': str(e)}
    
    def get_broadcast_stats(self) -> Dict[str, Any]:
        """Get comprehensive broadcasting statistics."""
        try:
            with self.broadcast_lock:
                runtime_seconds = time.time() - self.start_time
                
                # Calculate rates
                events_per_second = self.stats.total_events / max(runtime_seconds, 1)
                delivery_success_rate = (self.stats.events_delivered / max(self.stats.total_events, 1)) * 100
                
                return {
                    # Event metrics
                    'total_events': self.stats.total_events,
                    'events_delivered': self.stats.events_delivered,
                    'events_dropped': self.stats.events_dropped,
                    'events_rate_limited': self.stats.events_rate_limited,
                    'events_per_second': round(events_per_second, 2),
                    'delivery_success_rate_percent': round(delivery_success_rate, 1),
                    
                    # Performance metrics
                    'avg_batch_size': round(self.stats.batch_efficiency, 1),
                    'avg_delivery_latency_ms': round(self.stats.avg_delivery_latency_ms, 2),
                    'max_delivery_latency_ms': round(self.stats.max_delivery_latency_ms, 2),
                    
                    # Batching metrics
                    'batches_created': self.stats.batches_created,
                    'batches_delivered': self.stats.batches_delivered,
                    'pending_batches': len(self.pending_batches),
                    'batch_efficiency': round(self.stats.batch_efficiency, 1),
                    
                    # Rate limiting metrics
                    'rate_limit_violations': self.stats.rate_limit_violations,
                    'users_with_rate_limiters': len(self.user_rate_limiters),
                    
                    # Configuration
                    'batch_window_ms': self.batch_window_ms,
                    'max_events_per_user': self.max_events_per_user,
                    'max_batch_size': self.max_batch_size,
                    
                    # System metrics
                    'runtime_seconds': round(runtime_seconds, 1),
                    'uptime_hours': round(runtime_seconds / 3600, 1),
                    'last_updated': time.time()
                }
                
        except Exception as e:
            logger.error(f"SCALABLE-BROADCASTER: Error getting broadcast stats: {e}")
            return {'error': str(e), 'timestamp': time.time()}
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status for monitoring."""
        try:
            stats = self.get_broadcast_stats()
            
            # Determine health status
            if stats.get('avg_delivery_latency_ms', 0) > 200:
                status = 'error'
                message = f"High delivery latency: {stats['avg_delivery_latency_ms']:.1f}ms"
            elif stats.get('delivery_success_rate_percent', 100) < 95:
                status = 'warning'
                message = f"Low delivery success rate: {stats['delivery_success_rate_percent']:.1f}%"
            elif stats.get('avg_delivery_latency_ms', 0) > 100:
                status = 'warning'
                message = f"Elevated delivery latency: {stats['avg_delivery_latency_ms']:.1f}ms"
            elif stats.get('pending_batches', 0) > 50:
                status = 'warning'
                message = f"High pending batch count: {stats['pending_batches']}"
            else:
                status = 'healthy'
                message = f"Broadcasting healthy - {stats['avg_delivery_latency_ms']:.1f}ms avg latency"
            
            return {
                'service': 'scalable_broadcaster',
                'status': status,
                'message': message,
                'timestamp': time.time(),
                'stats': stats,
                'performance_targets': {
                    'delivery_latency_target_ms': 100.0,
                    'batch_efficiency_target': 10.0,
                    'success_rate_target_percent': 95.0
                }
            }
            
        except Exception as e:
            logger.error(f"SCALABLE-BROADCASTER: Error getting health status: {e}")
            return {
                'service': 'scalable_broadcaster',
                'status': 'error',
                'message': f"Health check failed: {str(e)}",
                'timestamp': time.time()
            }
    
    def optimize_performance(self) -> Dict[str, Any]:
        """Optimize broadcasting performance."""
        try:
            optimization_results = {
                'batches_flushed': 0,
                'rate_limiters_cleaned': 0,
                'memory_freed': 0,
                'optimization_timestamp': time.time()
            }
            
            # Flush all pending batches
            with self.broadcast_lock:
                pending_count = len(self.pending_batches)
            
            self.flush_all_batches()
            optimization_results['batches_flushed'] = pending_count
            
            # Clean up inactive rate limiters
            current_time = time.time()
            with self.rate_limit_lock:
                inactive_users = []
                
                for user_id, rate_limiter in self.user_rate_limiters.items():
                    # Remove rate limiter if no recent activity
                    if (rate_limiter.event_timestamps and 
                        current_time - rate_limiter.event_timestamps[-1] > 3600):  # 1 hour
                        inactive_users.append(user_id)
                
                for user_id in inactive_users:
                    del self.user_rate_limiters[user_id]
                
                optimization_results['rate_limiters_cleaned'] = len(inactive_users)
            
            logger.info(f"SCALABLE-BROADCASTER: Performance optimization complete - "
                       f"{optimization_results['batches_flushed']} batches flushed, "
                       f"{optimization_results['rate_limiters_cleaned']} rate limiters cleaned")
            
            return optimization_results
            
        except Exception as e:
            logger.error(f"SCALABLE-BROADCASTER: Error optimizing performance: {e}")
            return {'error': str(e), 'timestamp': time.time()}
    
    def shutdown(self):
        """Graceful shutdown of broadcaster."""
        try:
            logger.info("SCALABLE-BROADCASTER: Starting graceful shutdown...")
            
            # Flush all pending batches
            self.flush_all_batches()
            
            # Shutdown thread pools
            self.batch_executor.shutdown(wait=True, timeout=5)
            self.delivery_executor.shutdown(wait=True, timeout=5)
            
            # Cancel all timers
            with self.broadcast_lock:
                for timer in self.batch_timers.values():
                    timer.cancel()
                self.batch_timers.clear()
            
            logger.info("SCALABLE-BROADCASTER: Graceful shutdown complete")
            
        except Exception as e:
            logger.error(f"SCALABLE-BROADCASTER: Error during shutdown: {e}")