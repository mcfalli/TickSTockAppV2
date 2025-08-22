"""
Source Context Management System - Sprint 107

Manages source identification, tracking, and metadata preservation throughout
the processing pipeline. Provides source-specific processing rules and
context for multi-source event coordination.

Sprint 107: Event Processing Refactor
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Union
import time
import threading
from enum import Enum

from config.logging_config import get_domain_logger, LogDomain
from src.core.domain.events.base import BaseEvent
from src.core.domain.market.tick import TickData
from src.shared.models.data_types import OHLCVData, FMVData

logger = get_domain_logger(LogDomain.CORE, 'source_context')


class DataSource(Enum):
    """Supported data sources"""
    TICK = "tick"
    OHLCV = "ohlcv" 
    FMV = "fmv"
    WEBSOCKET = "websocket"
    CHANNEL = "channel"


@dataclass
class SourceContext:
    """
    Source context information for data processing.
    Tracks source metadata throughout the processing pipeline.
    """
    source_type: DataSource
    source_id: str
    timestamp: float
    ticker: str
    
    # Source-specific metadata
    confidence: float = 1.0
    processing_rules: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Processing tracking
    processing_start_time: Optional[float] = None
    processing_stages: List[str] = field(default_factory=list)
    error_count: int = 0
    warnings: List[str] = field(default_factory=list)
    
    def add_processing_stage(self, stage: str):
        """Add processing stage to tracking"""
        self.processing_stages.append(f"{stage}:{time.time():.3f}")
    
    def add_warning(self, warning: str):
        """Add warning to context"""
        self.warnings.append(f"{time.time():.3f}: {warning}")
    
    def increment_error_count(self):
        """Increment error count"""
        self.error_count += 1
    
    def get_processing_duration(self) -> float:
        """Get total processing duration in milliseconds"""
        if self.processing_start_time:
            return (time.time() - self.processing_start_time) * 1000
        return 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/transport"""
        return {
            'source_type': self.source_type.value,
            'source_id': self.source_id,
            'timestamp': self.timestamp,
            'ticker': self.ticker,
            'confidence': self.confidence,
            'processing_rules': self.processing_rules,
            'metadata': self.metadata,
            'processing_duration_ms': self.get_processing_duration(),
            'processing_stages': self.processing_stages,
            'error_count': self.error_count,
            'warnings': self.warnings
        }


class SourceContextManager:
    """
    Manages source context tracking and source-specific processing rules.
    
    Responsibilities:
    - Create and track source context for all data types
    - Apply source-specific processing rules and filters
    - Maintain source metadata throughout processing pipeline
    - Provide source-based event deduplication
    - Support source context debugging and monitoring
    """
    
    def __init__(self):
        self._context_store: Dict[str, SourceContext] = {}
        self._lock = threading.RLock()
        
        # Source-specific processing rules
        self._source_rules: Dict[DataSource, Dict[str, Any]] = {
            DataSource.TICK: {
                'min_price_move': 0.01,
                'max_processing_delay_ms': 100,
                'enable_real_time_processing': True
            },
            DataSource.OHLCV: {
                'min_percent_change': 1.0,
                'required_volume_multiple': 1.5,
                'enable_batch_processing': True,
                'min_confidence': 0.8
            },
            DataSource.FMV: {
                'min_confidence': 0.7,
                'max_deviation_percent': 5.0,
                'enable_valuation_filtering': True,
                'min_signal_strength': 0.6
            }
        }
        
        # Context cleanup settings
        self._max_context_age_seconds = 3600  # 1 hour
        self._max_contexts = 10000
        self._last_cleanup = time.time()
        self._cleanup_interval = 300  # 5 minutes
        
        logger.info("SourceContextManager initialized")
    
    def create_context(self, data: Any, source_type: DataSource = None) -> SourceContext:
        """
        Create source context from incoming data.
        
        Args:
            data: Incoming data (TickData, OHLCVData, FMVData, or dict)
            source_type: Optional explicit source type
            
        Returns:
            SourceContext with source metadata
        """
        try:
            # Auto-detect source type if not provided
            if source_type is None:
                source_type = self._detect_source_type(data)
            
            # Extract basic information
            ticker, timestamp = self._extract_basic_info(data)
            
            # Generate unique source ID
            source_id = f"{source_type.value}:{ticker}:{timestamp}"
            
            # Create context
            context = SourceContext(
                source_type=source_type,
                source_id=source_id,
                timestamp=timestamp,
                ticker=ticker,
                processing_start_time=time.time()
            )
            
            # Apply source-specific rules
            context.processing_rules = self._source_rules.get(source_type, {}).copy()
            
            # Add source-specific metadata
            self._populate_source_metadata(context, data)
            
            # Store context
            with self._lock:
                self._context_store[source_id] = context
                context.add_processing_stage("context_created")
            
            # Periodic cleanup
            self._maybe_cleanup_contexts()
            
            # Reduced logging: only log context creation for non-routine operations
            verbose_logging = getattr(self, 'verbose_context_logging', False)
            if verbose_logging:
                logger.debug(f"Created source context: {source_id}")
            return context
            
        except Exception as e:
            logger.error(f"Error creating source context: {e}", exc_info=True)
            # Return minimal context on error
            return SourceContext(
                source_type=DataSource.WEBSOCKET,
                source_id=f"error:{time.time()}",
                timestamp=time.time(),
                ticker="UNKNOWN"
            )
    
    def get_context(self, source_id: str) -> Optional[SourceContext]:
        """Get source context by ID"""
        with self._lock:
            return self._context_store.get(source_id)
    
    def update_context(self, source_id: str, **updates) -> bool:
        """Update source context with new information"""
        with self._lock:
            context = self._context_store.get(source_id)
            if context:
                for key, value in updates.items():
                    if hasattr(context, key):
                        setattr(context, key, value)
                context.add_processing_stage(f"updated:{','.join(updates.keys())}")
                return True
            return False
    
    def add_event_metadata(self, event: BaseEvent, context: SourceContext):
        """Add source context metadata to event"""
        try:
            # Add source metadata to event
            if hasattr(event, 'source_metadata'):
                event.source_metadata = {
                    'source_type': context.source_type.value,
                    'source_id': context.source_id,
                    'confidence': context.confidence,
                    'processing_duration_ms': context.get_processing_duration()
                }
            
            # Add to event metadata dict if available
            if hasattr(event, 'metadata'):
                event.metadata.update({
                    'source_context': context.to_dict()
                })
            
            context.add_processing_stage("event_metadata_added")
            
        except Exception as e:
            logger.warning(f"Could not add source metadata to event: {e}")
            context.add_warning(f"metadata_error: {e}")
    
    def apply_source_rules(self, data: Any, context: SourceContext) -> bool:
        """
        Apply source-specific processing rules to determine if data should be processed.
        
        Args:
            data: Data to validate against rules
            context: Source context with rules
            
        Returns:
            True if data passes source-specific rules, False otherwise
        """
        try:
            source_type = context.source_type
            rules = context.processing_rules
            
            if source_type == DataSource.OHLCV:
                return self._apply_ohlcv_rules(data, rules, context)
            elif source_type == DataSource.FMV:
                return self._apply_fmv_rules(data, rules, context)
            elif source_type == DataSource.TICK:
                return self._apply_tick_rules(data, rules, context)
            else:
                # Default: allow processing
                context.add_processing_stage("default_rules_applied")
                return True
                
        except Exception as e:
            logger.error(f"Error applying source rules: {e}", exc_info=True)
            context.increment_error_count()
            context.add_warning(f"rule_error: {e}")
            return False
    
    def should_deduplicate_event(self, event: BaseEvent, context: SourceContext) -> bool:
        """
        Check if event should be deduplicated based on source context.
        
        Args:
            event: Event to check for deduplication
            context: Source context
            
        Returns:
            True if event should be deduplicated (not processed), False otherwise
        """
        try:
            # Create deduplication key
            dedup_key = f"{context.ticker}:{event.type}:{event.time:.0f}"
            
            # Check recent events from same source
            recent_cutoff = time.time() - 60  # 1 minute window
            
            with self._lock:
                for stored_context in self._context_store.values():
                    if (stored_context.ticker == context.ticker and 
                        stored_context.timestamp > recent_cutoff and
                        stored_context.source_id != context.source_id):
                        
                        # Check if same event type was processed recently
                        for stage in stored_context.processing_stages:
                            if f"event_type:{event.type}" in stage:
                                context.add_warning("duplicate_event_detected")
                                return True
            
            # Mark this event type as processed
            context.add_processing_stage(f"event_type:{event.type}")
            return False
            
        except Exception as e:
            logger.warning(f"Error in deduplication check: {e}")
            return False
    
    def get_source_statistics(self) -> Dict[str, Any]:
        """Get statistics about source processing"""
        with self._lock:
            stats = {
                'total_contexts': len(self._context_store),
                'contexts_by_source': {},
                'contexts_by_ticker': {},
                'average_processing_time_ms': 0,
                'total_errors': 0,
                'total_warnings': 0
            }
            
            total_duration = 0
            total_with_duration = 0
            
            for context in self._context_store.values():
                # Count by source type
                source_type = context.source_type.value
                stats['contexts_by_source'][source_type] = stats['contexts_by_source'].get(source_type, 0) + 1
                
                # Count by ticker
                stats['contexts_by_ticker'][context.ticker] = stats['contexts_by_ticker'].get(context.ticker, 0) + 1
                
                # Aggregate metrics
                stats['total_errors'] += context.error_count
                stats['total_warnings'] += len(context.warnings)
                
                duration = context.get_processing_duration()
                if duration > 0:
                    total_duration += duration
                    total_with_duration += 1
            
            if total_with_duration > 0:
                stats['average_processing_time_ms'] = total_duration / total_with_duration
            
            return stats
    
    def cleanup_old_contexts(self, force: bool = False):
        """Clean up old contexts to prevent memory leaks"""
        current_time = time.time()
        
        if not force and current_time - self._last_cleanup < self._cleanup_interval:
            return
        
        with self._lock:
            old_contexts = []
            for source_id, context in self._context_store.items():
                age = current_time - context.timestamp
                if age > self._max_context_age_seconds:
                    old_contexts.append(source_id)
            
            # Remove old contexts
            for source_id in old_contexts:
                del self._context_store[source_id]
            
            # Also remove excess contexts if we're over the limit
            if len(self._context_store) > self._max_contexts:
                # Sort by timestamp and remove oldest
                sorted_contexts = sorted(
                    self._context_store.items(),
                    key=lambda x: x[1].timestamp
                )
                excess_count = len(self._context_store) - self._max_contexts
                for source_id, _ in sorted_contexts[:excess_count]:
                    del self._context_store[source_id]
                    old_contexts.append(source_id)
            
            self._last_cleanup = current_time
            
            if old_contexts:
                logger.info(f"Cleaned up {len(old_contexts)} old source contexts")
    
    def _detect_source_type(self, data: Any) -> DataSource:
        """Detect source type from data"""
        if isinstance(data, TickData):
            return DataSource.TICK
        elif isinstance(data, OHLCVData):
            return DataSource.OHLCV
        elif isinstance(data, FMVData):
            return DataSource.FMV
        elif isinstance(data, dict):
            if 'fmv' in data or 'fmv_price' in data:
                return DataSource.FMV
            elif all(field in data for field in ['open', 'high', 'low', 'close']):
                return DataSource.OHLCV
            else:
                return DataSource.WEBSOCKET
        else:
            return DataSource.WEBSOCKET
    
    def _extract_basic_info(self, data: Any) -> tuple[str, float]:
        """Extract ticker and timestamp from data"""
        ticker = "UNKNOWN"
        timestamp = time.time()
        
        if hasattr(data, 'ticker') and hasattr(data, 'timestamp'):
            ticker = data.ticker
            timestamp = data.timestamp
        elif isinstance(data, dict):
            ticker = data.get('ticker', 'UNKNOWN')
            timestamp = data.get('timestamp', time.time())
        
        return ticker, timestamp
    
    def _populate_source_metadata(self, context: SourceContext, data: Any):
        """Populate source-specific metadata"""
        try:
            if context.source_type == DataSource.OHLCV:
                if hasattr(data, 'volume') and hasattr(data, 'avg_volume'):
                    context.metadata['volume_ratio'] = data.volume / data.avg_volume if data.avg_volume > 0 else 1.0
                if hasattr(data, 'percent_change'):
                    context.metadata['price_change_pct'] = data.percent_change
                    
            elif context.source_type == DataSource.FMV:
                if hasattr(data, 'confidence'):
                    context.confidence = data.confidence
                if hasattr(data, 'deviation_percent'):
                    context.metadata['fmv_deviation_pct'] = data.deviation_percent
                    
            elif context.source_type == DataSource.TICK:
                if hasattr(data, 'volume'):
                    context.metadata['tick_volume'] = data.volume
                if hasattr(data, 'price'):
                    context.metadata['tick_price'] = data.price
                    
        except Exception as e:
            logger.warning(f"Error populating source metadata: {e}")
            context.add_warning(f"metadata_error: {e}")
    
    def _apply_ohlcv_rules(self, data: Any, rules: Dict[str, Any], context: SourceContext) -> bool:
        """Apply OHLCV-specific processing rules"""
        try:
            # Check minimum percent change
            min_change = rules.get('min_percent_change', 1.0)
            if hasattr(data, 'percent_change'):
                if abs(data.percent_change) < min_change:
                    context.add_warning(f"percent_change {data.percent_change:.2f}% below threshold {min_change}%")
                    return False
            
            # Check volume multiple
            volume_multiple = rules.get('required_volume_multiple', 1.5)
            if hasattr(data, 'volume') and hasattr(data, 'avg_volume'):
                if data.avg_volume > 0 and (data.volume / data.avg_volume) < volume_multiple:
                    context.add_warning(f"volume multiple {data.volume/data.avg_volume:.1f}x below threshold {volume_multiple}x")
                    return False
            
            context.add_processing_stage("ohlcv_rules_passed")
            return True
            
        except Exception as e:
            logger.error(f"Error applying OHLCV rules: {e}")
            context.increment_error_count()
            return False
    
    def _apply_fmv_rules(self, data: Any, rules: Dict[str, Any], context: SourceContext) -> bool:
        """Apply FMV-specific processing rules"""
        try:
            # Check confidence threshold
            min_confidence = rules.get('min_confidence', 0.7)
            if hasattr(data, 'confidence'):
                if data.confidence < min_confidence:
                    context.add_warning(f"confidence {data.confidence:.2f} below threshold {min_confidence}")
                    return False
            
            # Check deviation threshold
            max_deviation = rules.get('max_deviation_percent', 5.0)
            if hasattr(data, 'deviation_percent'):
                if abs(data.deviation_percent) > max_deviation:
                    context.add_warning(f"deviation {data.deviation_percent:.2f}% exceeds threshold {max_deviation}%")
                    return False
            
            context.add_processing_stage("fmv_rules_passed")
            return True
            
        except Exception as e:
            logger.error(f"Error applying FMV rules: {e}")
            context.increment_error_count()
            return False
    
    def _apply_tick_rules(self, data: Any, rules: Dict[str, Any], context: SourceContext) -> bool:
        """Apply tick-specific processing rules"""
        try:
            # Check minimum price move
            min_move = rules.get('min_price_move', 0.01)
            if hasattr(data, 'price') and hasattr(data, 'previous_price'):
                if abs(data.price - data.previous_price) < min_move:
                    context.add_warning(f"price move ${abs(data.price - data.previous_price):.4f} below threshold ${min_move}")
                    return False
            
            context.add_processing_stage("tick_rules_passed")
            return True
            
        except Exception as e:
            logger.error(f"Error applying tick rules: {e}")
            context.increment_error_count()
            return False
    
    def _maybe_cleanup_contexts(self):
        """Maybe run cleanup if it's time"""
        current_time = time.time()
        if current_time - self._last_cleanup > self._cleanup_interval:
            self.cleanup_old_contexts()