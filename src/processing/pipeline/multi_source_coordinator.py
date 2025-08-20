"""
Multi-Source Event Coordination - Sprint 107

Coordinates events from multiple sources (tick, OHLCV, FMV) with conflict
resolution, priority-based emission, and consistent event ordering.

Sprint 107: Event Processing Refactor
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple, Set
from collections import defaultdict, deque
import time
import threading
from enum import Enum

from config.logging_config import get_domain_logger, LogDomain
from src.core.domain.events.base import BaseEvent
from src.processing.pipeline.source_context_manager import SourceContext, DataSource

logger = get_domain_logger(LogDomain.CORE, 'multi_source_coordinator')


class EventPriority(Enum):
    """Event priority levels for multi-source coordination"""
    CRITICAL = 1    # Immediate processing (e.g., real-time tick events)
    HIGH = 2        # High priority (e.g., surge events)
    NORMAL = 3      # Normal priority (e.g., high/low events)
    LOW = 4         # Low priority (e.g., trend events)
    BACKGROUND = 5  # Background processing (e.g., analytics)


class ConflictResolution(Enum):
    """Strategies for resolving conflicts between multiple sources"""
    SOURCE_PRIORITY = "source_priority"     # Use source priority order
    TIMESTAMP_LATEST = "timestamp_latest"   # Use most recent event
    CONFIDENCE_HIGHEST = "confidence_highest"  # Use highest confidence
    EVENT_TYPE_SPECIFIC = "event_type_specific"  # Use event-type specific rules


@dataclass
class EventCoordination:
    """
    Coordination metadata for multi-source events.
    Tracks conflicts, resolution, and emission decisions.
    """
    ticker: str
    event_type: str
    coordination_window_ms: float
    
    # Event sources and conflicts
    source_events: Dict[DataSource, BaseEvent] = field(default_factory=dict)
    conflict_detected: bool = False
    resolution_strategy: ConflictResolution = ConflictResolution.SOURCE_PRIORITY
    
    # Resolution results
    selected_event: Optional[BaseEvent] = None
    selected_source: Optional[DataSource] = None
    rejected_events: List[Tuple[DataSource, BaseEvent, str]] = field(default_factory=list)
    
    # Timing and coordination
    first_event_time: Optional[float] = None
    coordination_deadline: Optional[float] = None
    events_coordinated: int = 0
    
    def add_event(self, source: DataSource, event: BaseEvent, context: SourceContext):
        """Add event from source for coordination"""
        self.source_events[source] = event
        self.events_coordinated += 1
        
        if self.first_event_time is None:
            self.first_event_time = time.time()
            self.coordination_deadline = self.first_event_time + (self.coordination_window_ms / 1000.0)
        
        # Detect conflicts
        if len(self.source_events) > 1:
            self.conflict_detected = True
    
    def is_coordination_complete(self) -> bool:
        """Check if coordination window has expired"""
        if self.coordination_deadline is None:
            return False
        return time.time() >= self.coordination_deadline
    
    def get_coordination_summary(self) -> Dict[str, Any]:
        """Get summary of coordination process"""
        return {
            'ticker': self.ticker,
            'event_type': self.event_type,
            'sources_count': len(self.source_events),
            'conflict_detected': self.conflict_detected,
            'resolution_strategy': self.resolution_strategy.value,
            'selected_source': self.selected_source.value if self.selected_source else None,
            'rejected_count': len(self.rejected_events),
            'coordination_time_ms': (time.time() - self.first_event_time) * 1000 if self.first_event_time else 0
        }


@dataclass
class CoordinationConfig:
    """Configuration for multi-source coordination"""
    # Coordination windows by event type (milliseconds)
    coordination_windows: Dict[str, float] = field(default_factory=lambda: {
        'high': 500,    # 0.5 seconds for high/low events
        'low': 500,
        'trend': 1000,  # 1 second for trend events
        'surge': 200,   # 0.2 seconds for surge events
        'default': 500
    })
    
    # Source priority order (lower number = higher priority)
    source_priorities: Dict[DataSource, int] = field(default_factory=lambda: {
        DataSource.TICK: 1,        # Highest priority - real-time
        DataSource.WEBSOCKET: 2,   # High priority - real-time
        DataSource.OHLCV: 3,       # Medium priority - aggregate
        DataSource.FMV: 4,         # Lower priority - analytical
        DataSource.CHANNEL: 5      # Lowest priority - processed
    })
    
    # Conflict resolution strategies by event type
    resolution_strategies: Dict[str, ConflictResolution] = field(default_factory=lambda: {
        'high': ConflictResolution.TIMESTAMP_LATEST,
        'low': ConflictResolution.TIMESTAMP_LATEST,
        'trend': ConflictResolution.CONFIDENCE_HIGHEST,
        'surge': ConflictResolution.SOURCE_PRIORITY,
        'default': ConflictResolution.SOURCE_PRIORITY
    })
    
    # Performance settings
    max_coordinations_per_ticker: int = 100
    coordination_cleanup_interval: float = 60.0  # seconds
    enable_performance_monitoring: bool = True


class MultiSourceCoordinator:
    """
    Coordinates events from multiple data sources with conflict resolution
    and priority-based emission ordering.
    
    Responsibilities:
    - Aggregate events from multiple sources within time windows
    - Detect and resolve conflicts between sources
    - Apply priority-based event emission coordination
    - Maintain consistent event ordering across sources
    - Monitor coordination performance and conflicts
    """
    
    def __init__(self, config: CoordinationConfig = None):
        self.config = config or CoordinationConfig()
        
        # Active coordinations by ticker and event type
        self._coordinations: Dict[Tuple[str, str], EventCoordination] = {}
        self._lock = threading.RLock()
        
        # Emission queue with priority ordering
        self._emission_queue: deque = deque()
        self._emission_lock = threading.Lock()
        
        # Performance and monitoring
        self._coordination_stats = {
            'total_events_received': 0,
            'conflicts_detected': 0,
            'conflicts_resolved': 0,
            'events_emitted': 0,
            'coordination_timeouts': 0,
            'average_coordination_time_ms': 0.0,
            'events_by_source': defaultdict(int),
            'conflicts_by_event_type': defaultdict(int)
        }
        
        # Cleanup tracking
        self._last_cleanup = time.time()
        
        logger.info("MultiSourceCoordinator initialized")
    
    def coordinate_event(self, event: BaseEvent, context: SourceContext) -> bool:
        """
        Coordinate event from a specific source.
        
        Args:
            event: Event to coordinate
            context: Source context with metadata
            
        Returns:
            True if event was accepted for coordination
        """
        try:
            self._coordination_stats['total_events_received'] += 1
            self._coordination_stats['events_by_source'][context.source_type] += 1
            
            ticker = event.ticker
            event_type = event.type
            coordination_key = (ticker, event_type)
            
            with self._lock:
                # Get or create coordination
                coordination = self._coordinations.get(coordination_key)
                if coordination is None:
                    coordination_window = self.config.coordination_windows.get(
                        event_type, 
                        self.config.coordination_windows['default']
                    )
                    
                    coordination = EventCoordination(
                        ticker=ticker,
                        event_type=event_type,
                        coordination_window_ms=coordination_window,
                        resolution_strategy=self.config.resolution_strategies.get(
                            event_type,
                            self.config.resolution_strategies['default']
                        )
                    )
                    self._coordinations[coordination_key] = coordination
                
                # Add event to coordination
                coordination.add_event(context.source_type, event, context)
                
                # Check if coordination is ready to emit
                if self._should_emit_coordination(coordination):
                    resolved_event = self._resolve_coordination(coordination)
                    if resolved_event:
                        self._queue_for_emission(resolved_event, coordination)
                    
                    # Remove completed coordination
                    del self._coordinations[coordination_key]
                
                # Periodic cleanup
                self._maybe_cleanup_coordinations()
                
                context.add_processing_stage("event_coordinated")
                return True
                
        except Exception as e:
            logger.error(f"Error coordinating event: {e}", exc_info=True)
            context.increment_error_count()
            context.add_warning(f"coordination_error: {e}")
            return False
    
    def get_pending_events(self, max_events: int = 100) -> List[Tuple[BaseEvent, Dict[str, Any]]]:
        """
        Get pending events from emission queue.
        
        Args:
            max_events: Maximum number of events to return
            
        Returns:
            List of (event, coordination_metadata) tuples
        """
        events = []
        
        with self._emission_lock:
            while len(events) < max_events and self._emission_queue:
                event_data = self._emission_queue.popleft()
                events.append(event_data)
        
        if events:
            self._coordination_stats['events_emitted'] += len(events)
            logger.debug(f"Retrieved {len(events)} coordinated events for emission")
        
        return events
    
    def force_emit_pending_coordinations(self, ticker: str = None) -> int:
        """
        Force emission of pending coordinations, optionally for specific ticker.
        
        Args:
            ticker: Optional ticker to force emission for
            
        Returns:
            Number of coordinations forced to emit
        """
        forced_count = 0
        
        with self._lock:
            coordinations_to_emit = []
            
            if ticker:
                # Force specific ticker
                keys_to_remove = []
                for key, coordination in self._coordinations.items():
                    if coordination.ticker == ticker:
                        coordinations_to_emit.append((key, coordination))
                        keys_to_remove.append(key)
                
                for key in keys_to_remove:
                    del self._coordinations[key]
            else:
                # Force all pending
                coordinations_to_emit = list(self._coordinations.items())
                self._coordinations.clear()
            
            # Emit forced coordinations
            for key, coordination in coordinations_to_emit:
                resolved_event = self._resolve_coordination(coordination)
                if resolved_event:
                    self._queue_for_emission(resolved_event, coordination)
                    forced_count += 1
        
        if forced_count > 0:
            logger.info(f"Forced emission of {forced_count} pending coordinations")
        
        return forced_count
    
    def get_coordination_statistics(self) -> Dict[str, Any]:
        """Get comprehensive coordination statistics"""
        with self._lock:
            stats = self._coordination_stats.copy()
            
            # Add current state
            stats['active_coordinations'] = len(self._coordinations)
            stats['pending_emissions'] = len(self._emission_queue)
            
            # Calculate rates
            if stats['total_events_received'] > 0:
                stats['conflict_rate_percent'] = (
                    stats['conflicts_detected'] / stats['total_events_received'] * 100
                )
                stats['resolution_success_rate_percent'] = (
                    stats['conflicts_resolved'] / max(stats['conflicts_detected'], 1) * 100
                )
            
            # Convert defaultdicts to regular dicts for serialization
            stats['events_by_source'] = dict(stats['events_by_source'])
            stats['conflicts_by_event_type'] = dict(stats['conflicts_by_event_type'])
            
            # Add coordination breakdown
            coordination_breakdown = defaultdict(int)
            for coordination in self._coordinations.values():
                coordination_breakdown[coordination.event_type] += 1
            stats['active_coordinations_by_type'] = dict(coordination_breakdown)
            
            return stats
    
    def _should_emit_coordination(self, coordination: EventCoordination) -> bool:
        """Check if coordination should be emitted"""
        # Emit if coordination window has expired
        if coordination.is_coordination_complete():
            return True
        
        # Emit immediately for critical priority events
        if any(self._get_event_priority(event) == EventPriority.CRITICAL 
               for event in coordination.source_events.values()):
            return True
        
        # Emit if we have events from all expected sources
        # (This is a simplified heuristic - could be made more sophisticated)
        expected_sources = self._get_expected_sources(coordination.event_type)
        if expected_sources and len(coordination.source_events) >= len(expected_sources):
            return True
        
        return False
    
    def _resolve_coordination(self, coordination: EventCoordination) -> Optional[BaseEvent]:
        """
        Resolve coordination conflicts and select the best event.
        
        Args:
            coordination: Coordination to resolve
            
        Returns:
            Selected event or None if resolution fails
        """
        try:
            if not coordination.source_events:
                return None
            
            # No conflict - single event
            if len(coordination.source_events) == 1:
                source, event = next(iter(coordination.source_events.items()))
                coordination.selected_event = event
                coordination.selected_source = source
                return event
            
            # Multiple events - conflict resolution needed
            self._coordination_stats['conflicts_detected'] += 1
            self._coordination_stats['conflicts_by_event_type'][coordination.event_type] += 1
            
            selected_event = None
            selected_source = None
            
            if coordination.resolution_strategy == ConflictResolution.SOURCE_PRIORITY:
                selected_event, selected_source = self._resolve_by_source_priority(coordination)
            elif coordination.resolution_strategy == ConflictResolution.TIMESTAMP_LATEST:
                selected_event, selected_source = self._resolve_by_timestamp(coordination)
            elif coordination.resolution_strategy == ConflictResolution.CONFIDENCE_HIGHEST:
                selected_event, selected_source = self._resolve_by_confidence(coordination)
            elif coordination.resolution_strategy == ConflictResolution.EVENT_TYPE_SPECIFIC:
                selected_event, selected_source = self._resolve_by_event_specific_rules(coordination)
            
            if selected_event:
                coordination.selected_event = selected_event
                coordination.selected_source = selected_source
                
                # Track rejected events
                for source, event in coordination.source_events.items():
                    if source != selected_source:
                        reason = f"conflict_resolved_by_{coordination.resolution_strategy.value}"
                        coordination.rejected_events.append((source, event, reason))
                
                self._coordination_stats['conflicts_resolved'] += 1
                
                logger.debug(f"Resolved conflict for {coordination.ticker}:{coordination.event_type} "
                           f"using {coordination.resolution_strategy.value}, "
                           f"selected {selected_source.value} over {len(coordination.rejected_events)} others")
                
                return selected_event
            
            logger.warning(f"Failed to resolve conflict for {coordination.ticker}:{coordination.event_type}")
            return None
            
        except Exception as e:
            logger.error(f"Error resolving coordination: {e}", exc_info=True)
            return None
    
    def _resolve_by_source_priority(self, coordination: EventCoordination) -> Tuple[Optional[BaseEvent], Optional[DataSource]]:
        """Resolve conflict by source priority"""
        best_priority = float('inf')
        selected_event = None
        selected_source = None
        
        for source, event in coordination.source_events.items():
            priority = self.config.source_priorities.get(source, 999)
            if priority < best_priority:
                best_priority = priority
                selected_event = event
                selected_source = source
        
        return selected_event, selected_source
    
    def _resolve_by_timestamp(self, coordination: EventCoordination) -> Tuple[Optional[BaseEvent], Optional[DataSource]]:
        """Resolve conflict by selecting most recent event"""
        latest_time = 0
        selected_event = None
        selected_source = None
        
        for source, event in coordination.source_events.items():
            if event.time > latest_time:
                latest_time = event.time
                selected_event = event
                selected_source = source
        
        return selected_event, selected_source
    
    def _resolve_by_confidence(self, coordination: EventCoordination) -> Tuple[Optional[BaseEvent], Optional[DataSource]]:
        """Resolve conflict by selecting highest confidence event"""
        highest_confidence = 0
        selected_event = None
        selected_source = None
        
        for source, event in coordination.source_events.items():
            confidence = getattr(event, 'confidence', 1.0)
            if confidence > highest_confidence:
                highest_confidence = confidence
                selected_event = event
                selected_source = source
        
        return selected_event, selected_source
    
    def _resolve_by_event_specific_rules(self, coordination: EventCoordination) -> Tuple[Optional[BaseEvent], Optional[DataSource]]:
        """Resolve conflict using event-type specific rules"""
        event_type = coordination.event_type
        
        # Event-specific resolution logic
        if event_type in ['high', 'low']:
            # For high/low events, prefer tick sources for accuracy
            for source in [DataSource.TICK, DataSource.WEBSOCKET]:
                if source in coordination.source_events:
                    return coordination.source_events[source], source
        
        elif event_type == 'trend':
            # For trend events, prefer sources with higher confidence
            return self._resolve_by_confidence(coordination)
        
        elif event_type == 'surge':
            # For surge events, prefer real-time sources
            return self._resolve_by_source_priority(coordination)
        
        # Fallback to source priority
        return self._resolve_by_source_priority(coordination)
    
    def _queue_for_emission(self, event: BaseEvent, coordination: EventCoordination):
        """Queue resolved event for emission with priority ordering"""
        priority = self._get_event_priority(event)
        coordination_metadata = coordination.get_coordination_summary()
        
        event_data = (event, coordination_metadata, priority)
        
        with self._emission_lock:
            # Insert with priority ordering (lower priority number = higher priority)
            inserted = False
            for i, (_, _, existing_priority) in enumerate(self._emission_queue):
                if priority.value < existing_priority.value:
                    self._emission_queue.insert(i, event_data)
                    inserted = True
                    break
            
            if not inserted:
                self._emission_queue.append(event_data)
    
    def _get_event_priority(self, event: BaseEvent) -> EventPriority:
        """Determine event priority for emission ordering"""
        event_type = event.type
        
        # Priority mapping by event type
        priority_map = {
            'surge': EventPriority.HIGH,
            'high': EventPriority.NORMAL,
            'low': EventPriority.NORMAL,
            'trend': EventPriority.LOW
        }
        
        return priority_map.get(event_type, EventPriority.NORMAL)
    
    def _get_expected_sources(self, event_type: str) -> Set[DataSource]:
        """Get expected sources for event type (simplified heuristic)"""
        # This could be made configurable based on system setup
        if event_type in ['high', 'low']:
            return {DataSource.TICK, DataSource.WEBSOCKET}
        elif event_type == 'trend':
            return {DataSource.OHLCV}
        elif event_type == 'surge':
            return {DataSource.TICK, DataSource.OHLCV}
        return set()
    
    def _maybe_cleanup_coordinations(self):
        """Cleanup old coordinations if needed"""
        current_time = time.time()
        if current_time - self._last_cleanup < self.config.coordination_cleanup_interval:
            return
        
        # Clean up expired coordinations
        expired_keys = []
        for key, coordination in self._coordinations.items():
            if coordination.is_coordination_complete():
                expired_keys.append(key)
                # Force emit expired coordinations
                resolved_event = self._resolve_coordination(coordination)
                if resolved_event:
                    self._queue_for_emission(resolved_event, coordination)
                self._coordination_stats['coordination_timeouts'] += 1
        
        for key in expired_keys:
            del self._coordinations[key]
        
        self._last_cleanup = current_time
        
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired coordinations")