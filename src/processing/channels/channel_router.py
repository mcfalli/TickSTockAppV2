"""
Data channel router for intelligent routing of different data types.

Routes incoming data to appropriate processing channels based on data type
identification, load balancing, and channel health monitoring.

Sprint 105: Core Channel Infrastructure Implementation
"""

from typing import Dict, List, Any, Optional, Callable, Protocol, Tuple, TYPE_CHECKING
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import time
import logging
from collections import defaultdict, deque
import hashlib
import random

from config.logging_config import get_domain_logger, LogDomain

# Import from existing domain models
from src.core.domain.market.tick import TickData

# Type-only imports to avoid circular dependencies
if TYPE_CHECKING:
    from .base_channel import ProcessingChannel, ChannelType
    from src.core.domain.events.base import BaseEvent

# Import ProcessingResult for runtime use
from .base_channel import ProcessingResult

logger = get_domain_logger(LogDomain.CORE, 'channel_router')


class RoutingStrategy(Enum):
    """Routing strategies for channel selection"""
    ROUND_ROBIN = "round_robin"
    LOAD_BASED = "load_based"
    HASH_BASED = "hash_based"
    HEALTH_BASED = "health_based"


@dataclass
class RoutingRule:
    """Defines custom routing rules for specific conditions"""
    data_type: str
    channel_type: str
    priority: int = 1
    condition: Optional[Callable[[Any], bool]] = None
    description: str = ""


@dataclass  
class RouterMetrics:
    """Router performance and routing metrics"""
    total_routed: int = 0
    routing_errors: int = 0
    routing_timeouts: int = 0
    last_routing_time_ms: float = 0.0
    avg_routing_time_ms: float = 0.0
    routes_by_type: Dict[str, int] = field(default_factory=dict)
    routes_by_channel: Dict[str, int] = field(default_factory=dict)
    last_activity: float = field(default_factory=time.time)
    
    # Route tracking for analysis
    successful_routes: int = 0
    failed_routes: int = 0
    fallback_routes: int = 0
    
    # Delegation tracking
    delegated_routes: int = 0
    
    # Performance tracking
    _routing_times: deque = field(default_factory=lambda: deque(maxlen=100))
    
    def update_routing_time(self, duration_ms: float):
        """Update routing time metrics"""
        self.last_routing_time_ms = duration_ms
        self._routing_times.append(duration_ms)
        
        # Update average using exponential moving average
        if self.total_routed == 1:
            self.avg_routing_time_ms = duration_ms
        else:
            alpha = 0.1
            self.avg_routing_time_ms = (alpha * duration_ms + 
                                      (1 - alpha) * self.avg_routing_time_ms)
        
        self.last_activity = time.time()
    
    def get_success_rate(self) -> float:
        """Calculate routing success rate as percentage"""
        if self.total_routed == 0:
            return 100.0
        return (self.successful_routes / self.total_routed) * 100.0
    
    def get_error_rate(self) -> float:
        """Calculate routing error rate as percentage"""
        if self.total_routed == 0:
            return 0.0
        return (self.routing_errors / self.total_routed) * 100.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary"""
        return {
            'total_routed': self.total_routed,
            'routing_errors': self.routing_errors,
            'routing_timeouts': self.routing_timeouts,
            'success_rate_percent': self.get_success_rate(),
            'error_rate_percent': self.get_error_rate(),
            'avg_routing_time_ms': self.avg_routing_time_ms,
            'last_routing_time_ms': self.last_routing_time_ms,
            'routes_by_type': dict(self.routes_by_type),
            'routes_by_channel': dict(self.routes_by_channel),
            'successful_routes': self.successful_routes,
            'failed_routes': self.failed_routes,
            'fallback_routes': self.fallback_routes,
            'last_activity': self.last_activity
        }


class DataTypeIdentifier:
    """
    Identifies data type from incoming data structures.
    Supports extensible identification rules.
    """
    
    def __init__(self):
        self._identification_rules: List[Tuple[str, Callable[[Any], bool]]] = []
        self._setup_default_rules()
        
        # Caching for performance
        self._type_cache: Dict[str, str] = {}
        self._cache_max_size = 1000
    
    def _setup_default_rules(self):
        """Setup default data type identification rules"""
        
        # TickData identification (highest priority)
        self.add_identification_rule('tick', self._is_tick_data)
        
        # OHLCV data identification
        self.add_identification_rule('ohlcv', self._is_ohlcv_data)
        
        # FMV data identification
        self.add_identification_rule('fmv', self._is_fmv_data)
    
    def add_identification_rule(self, data_type: str, rule_func: Callable[[Any], bool]):
        """Add custom identification rule"""
        self._identification_rules.append((data_type, rule_func))
        logger.debug(f"Added identification rule for data type: {data_type}")
    
    def identify_data_type(self, data: Any) -> Optional[str]:
        """
        Identify the data type from the incoming data structure.
        Returns data type string or None if unidentifiable.
        """
        
        # Create cache key from data structure
        cache_key = self._create_cache_key(data)
        
        # Check cache first
        if cache_key in self._type_cache:
            return self._type_cache[cache_key]
        
        # Try identification rules in order
        for data_type, rule_func in self._identification_rules:
            try:
                if rule_func(data):
                    # Cache result if cache isn't full
                    if len(self._type_cache) < self._cache_max_size:
                        self._type_cache[cache_key] = data_type
                    return data_type
            except Exception as e:
                logger.warning(f"Error in identification rule for {data_type}: {e}")
                continue
        
        # Unknown data type
        logger.warning(f"Unable to identify data type for: {type(data).__name__}")
        return None
    
    def _create_cache_key(self, data: Any) -> str:
        """Create cache key from data structure"""
        if isinstance(data, dict):
            # Create hash from sorted keys
            keys = sorted(data.keys())
            return f"dict:{':'.join(keys)}"
        else:
            # Use class name and basic attributes
            class_name = type(data).__name__
            if hasattr(data, '__dict__'):
                attrs = sorted(data.__dict__.keys())[:5]  # Limit to first 5 attrs
                return f"{class_name}:{':'.join(attrs)}"
            return class_name
    
    def _is_tick_data(self, data: Any) -> bool:
        """Check if data is tick data"""
        # Direct TickData object
        if isinstance(data, TickData):
            return True
        
        # Dictionary format tick data
        if isinstance(data, dict):
            # Must have ticker, price, timestamp
            required_fields = ['ticker', 'price', 'timestamp']
            if all(field in data for field in required_fields):
                # Additional checks to distinguish from OHLCV
                ohlcv_fields = ['open', 'high', 'low', 'close', 'volume']
                if not any(field in data for field in ohlcv_fields):
                    return True
        
        # Class name check
        type_name = type(data).__name__.lower()
        return 'tick' in type_name and 'ohlcv' not in type_name
    
    def _is_ohlcv_data(self, data: Any) -> bool:
        """Check if data is OHLCV bar data"""
        if isinstance(data, dict):
            # OHLCV data typically has open, high, low, close, volume
            required_fields = ['open', 'high', 'low', 'close', 'volume']
            if all(field in data for field in required_fields):
                return True
            
            # Alternative OHLCV field names
            alt_fields = ['o', 'h', 'l', 'c', 'v']
            if all(field in data for field in alt_fields):
                return True
        
        # Class name check
        type_name = type(data).__name__.lower()
        return any(term in type_name for term in ['ohlcv', 'bar', 'candle'])
    
    def _is_fmv_data(self, data: Any) -> bool:
        """Check if data is Fair Market Value data"""
        if isinstance(data, dict):
            # FMV data typically has fair_market_value or fmv fields
            fmv_fields = ['fair_market_value', 'fmv', 'valuation', 'fair_value']
            if any(field in data for field in fmv_fields):
                return True
        
        # Class name check
        type_name = type(data).__name__.lower()
        return any(term in type_name for term in ['fmv', 'valuation', 'fairvalue'])
    
    def clear_cache(self):
        """Clear identification cache"""
        self._type_cache.clear()
        logger.debug("Data type identification cache cleared")


class ChannelLoadBalancer:
    """
    Manages load balancing across channels of the same type.
    Supports multiple balancing strategies.
    """
    
    def __init__(self):
        self.channel_loads: Dict[str, int] = defaultdict(int)
        self.round_robin_indices: Dict[str, int] = defaultdict(int)
        self._lock = None
    
    def _get_lock(self):
        """Lazily create asyncio lock when needed"""
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock
    
    async def get_best_channel(self, channels: List['ProcessingChannel'], 
                              strategy: RoutingStrategy) -> Optional['ProcessingChannel']:
        """
        Select the best channel based on the routing strategy.
        Returns None if no suitable channel found.
        """
        if not channels:
            return None
        
        if len(channels) == 1:
            return channels[0] if channels[0].is_healthy() else None
        
        async with self._get_lock():
            # Filter only healthy channels first
            healthy_channels = [ch for ch in channels if ch.is_healthy()]
            
            if not healthy_channels:
                # If no healthy channels, log warning and try any available
                logger.warning(f"No healthy channels available, trying any channel")
                healthy_channels = channels
            
            if not healthy_channels:
                return None
            
            # Apply balancing strategy
            if strategy == RoutingStrategy.ROUND_ROBIN:
                return self._round_robin_select(healthy_channels)
            elif strategy == RoutingStrategy.LOAD_BASED:
                return self._load_based_select(healthy_channels)
            elif strategy == RoutingStrategy.HASH_BASED:
                return self._hash_based_select(healthy_channels)
            elif strategy == RoutingStrategy.HEALTH_BASED:
                return self._health_based_select(healthy_channels)
            else:
                # Default to first available
                return healthy_channels[0]
    
    def _round_robin_select(self, channels: List['ProcessingChannel']) -> 'ProcessingChannel':
        """Round-robin channel selection"""
        if not channels:
            return None
        
        # Use channel type for round-robin grouping
        channel_type = channels[0].channel_type.value
        current_index = self.round_robin_indices[channel_type]
        selected_channel = channels[current_index % len(channels)]
        
        self.round_robin_indices[channel_type] = (current_index + 1) % len(channels)
        return selected_channel
    
    def _load_based_select(self, channels: List['ProcessingChannel']) -> 'ProcessingChannel':
        """Load-based channel selection (choose channel with lowest current load)"""
        if not channels:
            return None
        
        # Select channel with lowest processing time + queue size
        def get_load_score(channel):
            queue_size = channel.processing_queue.qsize() if hasattr(channel.processing_queue, 'qsize') else 0
            processing_time = channel.metrics.avg_processing_time_ms
            return queue_size + (processing_time / 100.0)  # Normalize processing time
        
        return min(channels, key=get_load_score)
    
    def _hash_based_select(self, channels: List['ProcessingChannel']) -> 'ProcessingChannel':
        """Hash-based channel selection for consistent routing"""
        if not channels:
            return None
        
        # Use channel names for consistent hashing
        channel_names = sorted([ch.name for ch in channels])
        hash_input = ''.join(channel_names)
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest()[:8], 16)
        
        selected_index = hash_value % len(channels)
        return channels[selected_index]
    
    def _health_based_select(self, channels: List['ProcessingChannel']) -> 'ProcessingChannel':
        """Health-based selection (best overall health score)"""
        if not channels:
            return None
        
        def get_health_score(channel):
            """Calculate health score (higher is better)"""
            score = 100.0
            
            # More lenient health scoring
            # Subtract for error rate (but be more tolerant)
            if channel.metrics.processed_count > 0:
                error_rate = channel.metrics.error_count / channel.metrics.processed_count
                score -= error_rate * 30  # Reduced from 50 to 30 for leniency
            
            # Subtract for slow processing (but be more tolerant)
            if channel.metrics.avg_processing_time_ms > 200:  # Increased threshold from 100 to 200
                score -= min(channel.metrics.avg_processing_time_ms / 200, 20)  # Reduced penalty
            
            # Subtract for queue utilization (but be more tolerant)
            if hasattr(channel.processing_queue, 'qsize') and hasattr(channel.config, 'max_queue_size'):
                if channel.config.max_queue_size > 0:
                    utilization = channel.processing_queue.qsize() / channel.config.max_queue_size
                    score -= utilization * 10  # Reduced from 20 to 10
            
            return max(score, 0)
        
        # Calculate scores for all channels
        channel_scores = []
        for channel in channels:
            score = get_health_score(channel)
            channel_scores.append((channel, score))
        
        # Select channel with highest score
        best_channel = max(channel_scores, key=lambda x: x[1])
        
        return best_channel[0]
    
    def update_channel_load(self, channel_name: str, increment: int = 1):
        """Update channel load tracking"""
        self.channel_loads[channel_name] += increment
    
    def get_load_distribution(self) -> Dict[str, int]:
        """Get current load distribution across channels"""
        return dict(self.channel_loads)


@dataclass
class RouterConfig:
    """Configuration for DataChannelRouter"""
    routing_strategy: RoutingStrategy = RoutingStrategy.HEALTH_BASED
    enable_load_balancing: bool = True
    routing_timeout_ms: float = 100.0
    max_routing_retries: int = 3
    enable_fallback_routing: bool = True
    health_check_interval: float = 30.0
    enable_metrics_collection: bool = True
    
    # Circuit breaker for routing
    circuit_breaker_enabled: bool = True
    circuit_breaker_threshold: int = 10  # consecutive failures
    circuit_breaker_timeout: int = 60     # seconds
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'routing_strategy': self.routing_strategy.value,
            'enable_load_balancing': self.enable_load_balancing,
            'routing_timeout_ms': self.routing_timeout_ms,
            'max_routing_retries': self.max_routing_retries,
            'enable_fallback_routing': self.enable_fallback_routing,
            'health_check_interval': self.health_check_interval,
            'enable_metrics_collection': self.enable_metrics_collection,
            'circuit_breaker': {
                'enabled': self.circuit_breaker_enabled,
                'threshold': self.circuit_breaker_threshold,
                'timeout': self.circuit_breaker_timeout
            }
        }


class DataChannelRouter:
    """
    Routes incoming data to appropriate processing channels based on data type
    identification, channel health, and load balancing strategies.
    """
    
    def __init__(self, config: RouterConfig):
        self.config = config
        
        # Channel registry by type
        from .base_channel import ChannelType, ProcessingChannel
        self.channels: Dict[ChannelType, List[ProcessingChannel]] = {
            ChannelType.TICK: [],
            ChannelType.OHLCV: [],
            ChannelType.FMV: []
        }
        
        # Routing infrastructure
        self.routing_rules: List[RoutingRule] = []
        self.metrics = RouterMetrics()
        self.load_balancer = ChannelLoadBalancer()
        self.data_identifier = DataTypeIdentifier()
        
        # Integration point with existing event system
        self._event_processor = None
        
        # Circuit breaker state
        self._circuit_breaker_open = False
        self._circuit_breaker_failures = 0
        self._circuit_breaker_last_failure = None
        
        # Background tasks
        self._health_check_task = None
        self._running = False
        
        logger.info(f"Initialized DataChannelRouter with strategy: {config.routing_strategy.value}")
    
    async def start(self):
        """Start the router and background tasks"""
        if self._running:
            return
        
        self._running = True
        
        # Start health check task
        if self.config.health_check_interval > 0:
            self._health_check_task = asyncio.create_task(self._health_check_loop())
        
        logger.info("DataChannelRouter started")
    
    async def stop(self):
        """Stop the router and cleanup"""
        self._running = False
        
        # Stop background tasks
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        logger.info("DataChannelRouter stopped")
    
    def register_channel(self, channel: 'ProcessingChannel'):
        """Register a channel for routing"""
        channel_type = channel.channel_type
        if channel_type in self.channels:
            self.channels[channel_type].append(channel)
            logger.info(f"Registered channel {channel.name} for {channel_type.value} data")
        else:
            raise ValueError(f"Unsupported channel type: {channel_type}")
    
    def unregister_channel(self, channel: 'ProcessingChannel'):
        """Unregister a channel"""
        channel_type = channel.channel_type
        if channel_type in self.channels and channel in self.channels[channel_type]:
            self.channels[channel_type].remove(channel)
            logger.info(f"Unregistered channel {channel.name}")
    
    def add_routing_rule(self, rule: RoutingRule):
        """Add custom routing rule"""
        self.routing_rules.append(rule)
        # Sort by priority (lower number = higher priority)
        self.routing_rules.sort(key=lambda r: r.priority)
        logger.info(f"Added routing rule: {rule.description or rule.data_type}")
    
    async def route_data(self, data: Any) -> Optional['ProcessingResult']:
        """
        Route data to appropriate channel and process it.
        Main routing method with comprehensive error handling.
        """
        start_time = time.time()
        self.metrics.total_routed += 1
        
        # Circuit breaker check - TEMPORARILY DISABLED FOR DIAGNOSIS
        if False:  # self._is_circuit_breaker_open():
            self.metrics.routing_errors += 1
            self.metrics.failed_routes += 1
            logger.warning("Router circuit breaker is open, rejecting request")
            return None
        
        try:
            # Step 1: Identify data type
            data_type = self.data_identifier.identify_data_type(data)
            if not data_type:
                self._handle_routing_error("unknown_data_type")
                return None
            
            # Update metrics
            self.metrics.routes_by_type[data_type] = self.metrics.routes_by_type.get(data_type, 0) + 1
            
            # Step 2: Determine target channel type using routing rules
            channel_type = await self._determine_channel_type(data, data_type)
            if not channel_type:
                self._handle_routing_error("no_channel_type_determined")
                return None
            
            # Step 3: Select specific channel instance
            selected_channel = await self._select_channel(channel_type, data)
            if not selected_channel:
                self._handle_routing_error("no_available_channel")
                return None
            
            # Update channel routing metrics
            self.metrics.routes_by_channel[selected_channel.name] = \
                self.metrics.routes_by_channel.get(selected_channel.name, 0) + 1
            
            # Step 4: Route data to selected channel with timeout
            result = await self._route_with_timeout(selected_channel, data)
            
            # Step 5: Handle result and forward events
            if result and result.success:
                await self._forward_to_event_system(result.events, selected_channel)
                self._handle_routing_success()
                self.metrics.successful_routes += 1
            else:
                # Log delegation failures for operational monitoring
                error_details = result.errors if result and result.errors else ["Unknown error"]
                logger.warning(f"Channel delegation failed - channel={selected_channel.name}, errors={error_details}")
                self._handle_routing_error("processing_failed")
                self.metrics.failed_routes += 1
            
            # Update load balancer
            self.load_balancer.update_channel_load(selected_channel.name)
            
            return result
            
        except asyncio.TimeoutError:
            self.metrics.routing_timeouts += 1
            self.metrics.failed_routes += 1
            self._handle_routing_error("routing_timeout")
            logger.warning("Data routing timeout")
            return None
            
        except Exception as e:
            self.metrics.routing_errors += 1
            self.metrics.failed_routes += 1
            self._handle_routing_error("routing_exception")
            logger.error(f"Routing error: {e}", exc_info=True)
            return None
            
        finally:
            # Update timing metrics
            routing_time_ms = (time.time() - start_time) * 1000
            self.metrics.update_routing_time(routing_time_ms)
    
    async def _determine_channel_type(self, data: Any, data_type: str) -> Optional['ChannelType']:
        """
        Apply routing rules to determine which channel type should process the data.
        """
        from .base_channel import ChannelType
        
        # Check custom routing rules first (ordered by priority)
        for rule in self.routing_rules:
            if rule.data_type == data_type:
                # Apply condition if specified
                if rule.condition is None or rule.condition(data):
                    return ChannelType(rule.channel_type)
        
        # Default routing based on data type
        default_routes = {
            "tick": ChannelType.TICK,
            "ohlcv": ChannelType.OHLCV,
            "fmv": ChannelType.FMV
        }
        
        return default_routes.get(data_type)
    
    async def _select_channel(self, channel_type: 'ChannelType', data: Any) -> Optional['ProcessingChannel']:
        """Select specific channel instance using load balancing strategy"""
        available_channels = self.channels.get(channel_type, [])
        
        if not available_channels:
            logger.error(f"No channels registered for type: {channel_type.value}")
            return None
        
        # Use load balancer to select best channel
        selected_channel = await self.load_balancer.get_best_channel(
            available_channels, 
            self.config.routing_strategy
        )
        
        if not selected_channel:
            # SPRINT 109 DIAGNOSTIC: Show why channels are unhealthy  
            if available_channels:
                for ch in available_channels:
                    # Detailed health diagnostics
                    circuit_open = ch.is_circuit_open if hasattr(ch, 'is_circuit_open') else 'unknown'
                    error_rate = (ch.metrics.error_count / max(ch.metrics.processed_count, 1)) if hasattr(ch, 'metrics') else 'unknown'
                    avg_time = ch.metrics.avg_processing_time_ms if hasattr(ch, 'metrics') else 'unknown'
                    logger.warning(f"ROUTING FAILED: Channel {ch.name} (ID: {id(ch)}) status={ch.status.value} healthy={ch.is_healthy()} circuit_open={circuit_open} error_rate={error_rate:.3f} avg_time={avg_time}ms")
            else:
                logger.warning(f"ROUTING FAILED: No channels found for type: {channel_type.value}")
            logger.warning(f"No healthy channels available for type: {channel_type.value}")
            
            # Fallback to any available channel if enabled
            if self.config.enable_fallback_routing:
                selected_channel = available_channels[0]  # First available
                self.metrics.fallback_routes += 1
                logger.info(f"Using fallback channel: {selected_channel.name}")
        
        return selected_channel
    
    async def _route_with_timeout(self, channel: 'ProcessingChannel', data: Any) -> Optional['ProcessingResult']:
        """Route data to channel with timeout protection"""
        try:
            # Use process_with_metrics to get complete ProcessingResult with events
            if self.config.routing_timeout_ms > 0:
                routing_task = asyncio.create_task(channel.process_with_metrics(data))
                result = await asyncio.wait_for(
                    routing_task,
                    timeout=self.config.routing_timeout_ms / 1000.0
                )
                
                # Add channel metadata to result
                if result:
                    result.metadata['channel'] = channel.name
                    result.metadata['routing_method'] = 'timeout_protected'
                return result
            else:
                # No timeout - direct processing
                result = await channel.process_with_metrics(data)
                if result:
                    result.metadata['channel'] = channel.name
                    result.metadata['routing_method'] = 'direct'
                return result
                
        except asyncio.TimeoutError:
            logger.warning(f"Channel {channel.name} routing timeout")
            return ProcessingResult(
                success=False, 
                errors=[f"Channel {channel.name} processing timeout"],
                metadata={'channel': channel.name, 'error_type': 'timeout'}
            )
        except Exception as e:
            logger.error(f"Error routing to channel {channel.name}: {e}")
            return ProcessingResult(
                success=False,
                errors=[f"Channel {channel.name} processing error: {str(e)}"],
                metadata={'channel': channel.name, 'error_type': 'exception', 'exception': str(e)}
            )
    
    async def _forward_to_event_system(self, events: List['BaseEvent'], channel: 'ProcessingChannel'):
        """
        Forward generated events to existing event processing system.
        Maintains compatibility with existing priority_manager workflow.
        """
        if not events or not self._event_processor:
            return
        
        try:
            # Forward events to existing priority manager (from Sprint 103 analysis)
            for event in events:
                if hasattr(self._event_processor, 'market_service') and \
                   hasattr(self._event_processor.market_service, 'priority_manager'):
                    
                    priority_manager = self._event_processor.market_service.priority_manager
                    priority_manager.add_event(event)
                    
                    logger.debug(f"Forwarded {event.type} event from channel {channel.name}")
        except Exception as e:
            logger.error(f"Error forwarding events to existing system: {e}", exc_info=True)
    
    def set_event_processor(self, event_processor):
        """Inject reference to existing EventProcessor for backward compatibility"""
        self._event_processor = event_processor
        logger.info("EventProcessor reference set for event forwarding")
    
    def _handle_routing_success(self):
        """Handle successful routing"""
        # Track delegation success
        self.metrics.delegated_routes += 1
        
        # Reset circuit breaker on success
        if self._circuit_breaker_failures > 0:
            self._circuit_breaker_failures = 0
            if self._circuit_breaker_open:
                self._circuit_breaker_open = False
                logger.info("Router circuit breaker closed after successful routing")
    
    def _handle_routing_error(self, error_type: str):
        """Handle routing errors and circuit breaker logic"""
        if not self.config.circuit_breaker_enabled:
            return
        
        self._circuit_breaker_failures += 1
        self._circuit_breaker_last_failure = time.time()
        
        # Open circuit breaker if threshold exceeded
        if (self._circuit_breaker_failures >= self.config.circuit_breaker_threshold and 
            not self._circuit_breaker_open):
            self._circuit_breaker_open = True
            logger.warning(f"Router circuit breaker opened after {self._circuit_breaker_failures} failures")
    
    def _is_circuit_breaker_open(self) -> bool:
        """Check if router circuit breaker is open"""
        if not self._circuit_breaker_open:
            return False
        
        # Auto-close circuit breaker after timeout
        if (self._circuit_breaker_last_failure and 
            time.time() - self._circuit_breaker_last_failure > self.config.circuit_breaker_timeout):
            self._circuit_breaker_open = False
            self._circuit_breaker_failures = 0
            logger.info("Router circuit breaker auto-closed after timeout")
            return False
        
        return True
    
    async def _health_check_loop(self):
        """Background health check for registered channels"""
        try:
            while self._running:
                await asyncio.sleep(self.config.health_check_interval)
                
                if not self._running:
                    break
                
                # Check health of all registered channels
                unhealthy_channels = []
                for channel_type, channels in self.channels.items():
                    for channel in channels:
                        if not channel.is_healthy():
                            unhealthy_channels.append((channel_type.value, channel.name))
                
                if unhealthy_channels:
                    logger.warning(f"Unhealthy channels detected: {unhealthy_channels}")
                
                # Log routing statistics periodically
                if self.metrics.total_routed > 0:
                    logger.info(f"Router stats: {self.metrics.total_routed} total, "
                              f"{self.metrics.get_success_rate():.1f}% success rate, "
                              f"{self.metrics.avg_routing_time_ms:.1f}ms avg time")
                
        except asyncio.CancelledError:
            logger.info("Health check loop cancelled")
        except Exception as e:
            logger.error(f"Error in health check loop: {e}", exc_info=True)
    
    def get_routing_statistics(self) -> Dict[str, Any]:
        """Get comprehensive routing statistics"""
        total_channels = sum(len(channels) for channels in self.channels.values())
        healthy_channels = sum(
            len([ch for ch in channels if ch.is_healthy()]) 
            for channels in self.channels.values()
        )
        
        return {
            **self.metrics.to_dict(),
            'router_config': self.config.to_dict(),
            'total_channels': total_channels,
            'healthy_channels': healthy_channels,
            'unhealthy_channels': total_channels - healthy_channels,
            'circuit_breaker': {
                'open': self._circuit_breaker_open,
                'failures': self._circuit_breaker_failures,
                'last_failure': self._circuit_breaker_last_failure
            },
            'channel_distribution': {
                channel_type.value: len(channels)
                for channel_type, channels in self.channels.items()
            },
            'load_distribution': self.load_balancer.get_load_distribution()
        }
    
    def get_channel_status(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get detailed status of all registered channels"""
        return {
            channel_type.value: [
                {
                    'name': channel.name,
                    'channel_id': channel.channel_id,
                    'status': channel.status.value,
                    'healthy': channel.is_healthy(),
                    'processed_count': channel.metrics.processed_count,
                    'error_count': channel.metrics.error_count,
                    'avg_processing_time_ms': channel.metrics.avg_processing_time_ms,
                    'queue_size': channel.processing_queue.qsize() 
                                if hasattr(channel.processing_queue, 'qsize') else 0
                }
                for channel in channels
            ]
            for channel_type, channels in self.channels.items()
        }
    
    def clear_metrics(self):
        """Clear routing metrics (useful for testing)"""
        self.metrics = RouterMetrics()
        self.load_balancer.channel_loads.clear()
        logger.info("Router metrics cleared")